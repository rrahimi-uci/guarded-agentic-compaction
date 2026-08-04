"""CLI handlers for provider-free protocol validation and freezing."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Sequence

from ..evaluation.domains import BenchmarkRole
from .preflight import PreflightError, load_study_manifest, preflight_study
from .protocol import ProtocolError, freeze_protocol, load_case_jsonl


_STUDY_SCRIPTS = frozenset(
    {
        "multidomain_study.py",
        "compile_multidomain.py",
        "prepare_macro_review.py",
        "calibrate_grc_artifacts.py",
        "freeze_multidomain_actions.py",
        "calibrate_multidomain.py",
        "analyze_multidomain.py",
    }
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _execution_contract(pricing_path: str | Path, model: str) -> dict[str, str]:
    path = Path(pricing_path)
    try:
        pricing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProtocolError("pricing manifest cannot be loaded") from exc
    if (
        pricing.get("schema") != "agent-compaction-pricing/v1"
        or pricing.get("model") != model
    ):
        raise ProtocolError("pricing manifest does not match the frozen model")
    expected = {
        "schema",
        "model",
        "input_usd_per_million",
        "cached_input_usd_per_million",
        "output_usd_per_million",
        "maximum_billable_input_tokens_per_request",
        "output_token_limit_per_request",
        "service_tier",
        "revision",
        "source_url",
        "retrieved_at",
    }
    if set(pricing) != expected:
        raise ProtocolError("pricing manifest fields do not match pricing.schema.json")
    for field in (
        "input_usd_per_million",
        "cached_input_usd_per_million",
        "output_usd_per_million",
    ):
        value = pricing[field]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise ProtocolError(f"pricing manifest {field} is invalid")
    for field in (
        "maximum_billable_input_tokens_per_request",
        "output_token_limit_per_request",
    ):
        if type(pricing[field]) is not int or pricing[field] < 1:
            raise ProtocolError(f"pricing manifest {field} is invalid")
    tier = pricing.get("service_tier")
    if tier not in {"auto", "default", "flex", "priority"}:
        raise ProtocolError("pricing manifest service_tier is invalid")
    if not str(pricing.get("revision", "")).strip():
        raise ProtocolError("pricing manifest revision is required")
    if not str(pricing.get("source_url", "")).startswith("https://"):
        raise ProtocolError("pricing manifest source_url must use HTTPS")
    try:
        retrieved = datetime.fromisoformat(
            str(pricing.get("retrieved_at", "")).replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ProtocolError("pricing manifest retrieved_at must be ISO-8601") from exc
    if retrieved.tzinfo is None:
        raise ProtocolError("pricing manifest retrieved_at must include a timezone")
    try:
        agents_version = version("openai-agents")
        openai_version = version("openai")
    except PackageNotFoundError as exc:
        raise ProtocolError("freezing a live study requires the agents optional extra") from exc
    return {
        "model": model,
        "pricing_digest": _sha256(path),
        "pricing_revision": str(pricing["revision"]),
        "service_tier": str(tier),
        "maximum_billable_input_tokens_per_request": str(
            pricing["maximum_billable_input_tokens_per_request"]
        ),
        "output_token_limit_per_request": str(
            pricing["output_token_limit_per_request"]
        ),
        "openai_agents_version": agents_version,
        "openai_version": openai_version,
    }


def benchmark_script(args: argparse.Namespace) -> int:
    """Execute a repository study entry point without a shell or secret arguments."""

    if args.script_name not in _STUDY_SCRIPTS:
        print(json.dumps({"executed": False, "error": "unknown study script"}))
        return 2
    package_checkout = Path(__file__).resolve().parents[3]
    roots = (Path.cwd().resolve(), package_checkout)
    root = next(
        (
            candidate
            for candidate in roots
            if (candidate / "paper/scripts").is_dir()
            and (candidate / "benchmarks").is_dir()
        ),
        package_checkout,
    )
    script = root / "paper" / "scripts" / args.script_name
    if not script.is_file():
        print(json.dumps({"executed": False, "error": f"study script unavailable: {script}"}))
        return 2
    command = [sys.executable, str(script), *args.forwarded]
    return int(subprocess.run(command, cwd=root, check=False).returncode)


def _case_arguments(
    values: Sequence[str],
) -> tuple[dict[str, tuple], dict[str, Path]]:
    result: dict[str, tuple] = {}
    paths: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ProtocolError("case pools must use DOMAIN=JSONL")
        domain, path = value.split("=", 1)
        if domain in result:
            raise ProtocolError(f"duplicate case pool for {domain!r}")
        case_path = Path(path)
        result[domain] = load_case_jsonl(case_path)
        paths[domain] = case_path
    return result, paths


def benchmark_preflight(args: argparse.Namespace) -> int:
    try:
        cases, case_paths = _case_arguments(args.cases)
        report = preflight_study(
            args.manifest,
            cases_by_domain=cases or None,
            case_paths_by_domain=case_paths or None,
            require_source_configuration=args.require_source_configuration,
            require_normalized_artifacts=bool(cases),
        )
    except (PreflightError, ProtocolError) as exc:
        print(json.dumps({"eligible": False, "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    if report.errors:
        return 2
    return 0 if report.eligible else 1


def benchmark_freeze(args: argparse.Namespace) -> int:
    try:
        cases, case_paths = _case_arguments(args.cases)
        report = preflight_study(
            args.manifest,
            cases_by_domain=cases,
            case_paths_by_domain=case_paths,
            require_normalized_artifacts=True,
        )
        if not report.eligible:
            raise ProtocolError(
                "study is not eligible for freezing; run benchmark preflight for details"
            )
        payload = load_study_manifest(args.manifest)
        manifest_bytes = Path(args.manifest).read_bytes()
        source_digests: dict[str, str] = {}
        for domain, domain_cases in cases.items():
            snapshots = {case.source_snapshot for case in domain_cases}
            if len(snapshots) != 1:
                raise ProtocolError(
                    f"domain {domain!r} must use one frozen source snapshot, observed {len(snapshots)}"
                )
            source_digests[domain] = next(iter(snapshots))
        role_names = {
            "discovery": BenchmarkRole.DISCOVERY,
            "development": BenchmarkRole.DEVELOPMENT,
            "artifact_calibration": BenchmarkRole.ARTIFACT_CALIBRATION,
            "portfolio_calibration": BenchmarkRole.PORTFOLIO_CALIBRATION,
            "test": BenchmarkRole.TEST,
        }
        protocol = freeze_protocol(
            study_id=payload["study_id"],
            seed=int(payload["seed"]),
            config_digest=hashlib.sha256(manifest_bytes).hexdigest(),
            source_digests=source_digests,
            cases_by_domain=cases,
            role_counts={role_names[name]: count for name, count in payload["roles"].items()},
            reserve_groups=int(payload["reserve_groups"]),
            model=args.model,
            execution_contract=_execution_contract(args.pricing, args.model),
        )
        destination = protocol.write(args.out)
    except (KeyError, OSError, PreflightError, ProtocolError, ValueError) as exc:
        print(json.dumps({"frozen": False, "error": str(exc)}, sort_keys=True))
        return 2
    print(
        json.dumps(
            {
                "frozen": True,
                "path": str(destination),
                "protocol_digest": protocol.digest,
                "lineage_digest": protocol.lineage_digest,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0
