"""Fail-closed validation for the real-record multidomain study.

The preflight is provider-free.  It validates protocol structure, immutable case
identity, source/effect/schema paths, and independent-group sufficiency.  It never
downloads data or invokes an LLM.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from ..evaluation import BenchmarkCase
from ..schema.effects import EffectCatalog, EffectClass


STATISTICAL_CONTRACT: dict[str, Any] = {
    "quality_noninferiority_margin": 0.05,
    "per_domain_confidence": 0.99,
    "portfolio_overall_confidence": 0.99,
    "portfolio_quality_risk_limit": 0.10,
    "portfolio_regret_risk_limit": 0.10,
    "artifact_quality_risk_limit": 0.10,
    "bootstrap_resamples": 10_000,
    "secondary_correction": "holm",
    "repeat_groups": 20,
    "repeats_per_group": 3,
    "endpoints": [
        "model_requests",
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "total_tokens",
        "estimated_cost_usd",
        "wall_latency_ms",
        "critical_path_ms",
        "tool_calls",
    ],
}


class PreflightError(ValueError):
    """A manifest or case pool violates the prospective protocol."""


@dataclass(frozen=True, slots=True)
class PreflightReport:
    study_id: str
    eligible: bool
    provider_calls_executed: int
    required_groups_per_domain: int
    role_groups_per_domain: int
    domain_group_counts: Mapping[str, int]
    domain_case_counts: Mapping[str, int]
    source_configuration_available: Mapping[str, bool]
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["domain_group_counts"] = dict(self.domain_group_counts)
        result["domain_case_counts"] = dict(self.domain_case_counts)
        result["source_configuration_available"] = dict(
            self.source_configuration_available
        )
        result["errors"] = list(self.errors)
        result["warnings"] = list(self.warnings)
        return result


def load_study_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    try:
        payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PreflightError(f"cannot load study manifest {manifest_path}") from exc
    if not isinstance(payload, dict):
        raise PreflightError("study manifest must contain a mapping")
    return payload


def _mapping(value: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PreflightError(f"{label} must be a mapping")
    return value


def _positive_int(value: Any, *, label: str, allow_zero: bool = False) -> int:
    if type(value) is not int:
        raise PreflightError(f"{label} must be an integer")
    result = value
    if result < (0 if allow_zero else 1):
        raise PreflightError(f"{label} must be {'non-negative' if allow_zero else 'positive'}")
    return result


def _resolve_artifact(root: Path, relative: Any, *, label: str) -> Path:
    if not isinstance(relative, str) or not relative.strip():
        raise PreflightError(f"{label} must be a non-empty relative path")
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise PreflightError(f"{label} escapes the benchmark root") from exc
    if not candidate.is_file():
        raise PreflightError(f"{label} does not exist: {relative}")
    return candidate


def _validate_json_schema(path: Path, *, domain: str) -> None:
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PreflightError(f"{domain} output schema is invalid JSON") from exc
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise PreflightError(f"{domain} output schema must describe an object")
    if not isinstance(schema.get("required"), list) or not schema["required"]:
        raise PreflightError(f"{domain} output schema must declare required fields")
    properties = schema.get("properties")
    if not isinstance(properties, dict) or not set(schema["required"]).issubset(properties):
        raise PreflightError(f"{domain} output schema required fields must have properties")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_normalized_artifacts(
    *,
    domain: str,
    report_path: Path,
    report_payload: Mapping[str, Any],
    cases_digest: str,
    gold_digest: str,
    snapshot_file_digest: str,
    repository_root: Path,
    groups: int,
) -> None:
    """Bind a source attestation to the exact retained artifacts and oracle code."""

    for filename, expected in (
        ("cases.jsonl", cases_digest),
        ("gold.jsonl", gold_digest),
        ("snapshot.json", snapshot_file_digest),
    ):
        artifact_path = report_path.parent / filename
        if not artifact_path.is_file():
            raise PreflightError(
                f"{domain} normalized pool artifact is unavailable: {filename}"
            )
        if _sha256(artifact_path) != expected:
            raise PreflightError(
                f"{domain} normalized pool {filename} checksum mismatch"
            )

    construction = report_payload.get("gold_construction")
    expected_constructor = {
        "vulnerability": "vulnerability_gold_from_records",
        "sec": "sec_gold_from_records",
        "hmda": "hmda_gold_from_records",
    }[domain]
    gold_implementation = repository_root / "benchmarks" / "gold.py"
    if not gold_implementation.is_file():
        raise PreflightError(f"{domain} independent gold implementation is unavailable")
    if (
        not isinstance(construction, Mapping)
        or construction.get("independent_from_macro") is not True
        or construction.get("cases") != groups
        or construction.get("implementation")
        != f"benchmarks/gold.py:{expected_constructor}"
        or construction.get("implementation_sha256") != _sha256(gold_implementation)
    ):
        raise PreflightError(
            f"{domain} normalized pool lacks current independent gold construction"
        )

    try:
        snapshot = json.loads(
            (report_path.parent / "snapshot.json").read_text(encoding="utf-8")
        )
        case_rows = [
            json.loads(line)
            for line in (report_path.parent / "cases.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        gold_rows = [
            json.loads(line)
            for line in (report_path.parent / "gold.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        records = _mapping(snapshot.get("records"), label=f"{domain} snapshot records")
        observed_snapshot = hashlib.sha256(
            json.dumps(
                records,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise PreflightError(f"{domain} normalized artifacts are invalid") from exc
    case_ids = [row.get("case_id") for row in case_rows if isinstance(row, Mapping)]
    gold_ids = [row.get("case_id") for row in gold_rows if isinstance(row, Mapping)]
    if (
        snapshot.get("snapshot_digest") != f"sha256:{observed_snapshot}"
        or observed_snapshot != str(report_payload.get("snapshot_digest", "")).removeprefix(
            "sha256:"
        )
        or len(case_rows) != groups
        or len(gold_rows) != groups
        or len(case_ids) != groups
        or len(set(case_ids)) != groups
        or set(gold_ids) != set(case_ids)
        or any(
            not isinstance(row, Mapping)
            or row.get("domain") != domain
            or row.get("source_snapshot") != f"sha256:{observed_snapshot}"
            for row in case_rows
        )
    ):
        raise PreflightError(
            f"{domain} normalized pool artifact identities are inconsistent"
        )

    if domain != "hmda":
        return
    if report_payload.get("protected_demographic_fields_exposed_to_tools") is not False:
        raise PreflightError("hmda normalized pool does not attest protected-field exclusion")
    visible_fields = report_payload.get("agent_visible_schema_fields")
    if (
        not isinstance(visible_fields, list)
        or not visible_fields
        or any(not isinstance(field, str) or not field for field in visible_fields)
        or len(set(visible_fields)) != len(visible_fields)
    ):
        raise PreflightError("hmda agent-visible schema allowlist is invalid")
    try:
        records = _mapping(snapshot.get("records"), label="hmda snapshot records")
        schemas = _mapping(records.get("schemas"), label="hmda snapshot schemas")
        rows = _mapping(records.get("rows"), label="hmda snapshot rows")
    except (OSError, json.JSONDecodeError) as exc:
        raise PreflightError("hmda normalized snapshot is invalid") from exc
    allowed = set(visible_fields)
    for schema in schemas.values():
        schema_record = _mapping(schema, label="hmda agent-visible schema")
        if schema_record.get("fields") != visible_fields:
            raise PreflightError("hmda snapshot schema differs from the privacy allowlist")
    metadata_fields = {"raw_row_digest", "sources"}
    for row in rows.values():
        row_record = _mapping(row, label="hmda agent-visible row")
        unexpected = set(row_record) - allowed - metadata_fields
        if unexpected:
            raise PreflightError(
                "hmda snapshot exposes fields outside the privacy allowlist: "
                + ", ".join(sorted(unexpected))
            )


def _validate_source_manifest(
    path: Path,
    *,
    domain: str,
    repository_root: Path,
) -> tuple[tuple[str, ...], dict[str, Any]]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise PreflightError(f"{domain} source manifest cannot be loaded") from exc
    source = _mapping(payload, label=f"{domain} source manifest")
    if source.get("schema") != "agent-compaction-source-manifest/v1":
        raise PreflightError(f"{domain} source manifest schema is unsupported")
    if not isinstance(source.get("status"), str) or not source["status"].strip():
        raise PreflightError(f"{domain} source manifest status is missing")
    entries = source.get("sources")
    if not isinstance(entries, list) or not entries:
        raise PreflightError(f"{domain} source manifest must list sources")
    required_configuration = source.get("required_configuration", [])
    if not isinstance(required_configuration, list) or any(
        not isinstance(name, str) or not name.strip() for name in required_configuration
    ):
        raise PreflightError(f"{domain} required_configuration must be a list of names")
    for index, entry in enumerate(entries):
        item = _mapping(entry, label=f"{domain} source {index}")
        for field in ("name", "url", "authority", "access"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise PreflightError(f"{domain} source {index} is missing {field}")
    pool_facts: dict[str, Any] = {"groups": 0}
    normalized = source.get("normalized_pool")
    if normalized is not None:
        pool = _mapping(normalized, label=f"{domain} normalized_pool")
        groups = _positive_int(
            pool.get("groups"), label=f"{domain} normalized_pool groups", allow_zero=True
        )
        calls = _positive_int(
            pool.get("provider_calls_executed"),
            label=f"{domain} normalized_pool provider_calls_executed",
            allow_zero=True,
        )
        if calls != 0:
            raise PreflightError(f"{domain} source acquisition must be provider-free")
        if groups:
            passes = _positive_int(
                pool.get("exact_oracle_passes"),
                label=f"{domain} normalized_pool exact_oracle_passes",
                allow_zero=True,
            )
            if passes != groups:
                raise PreflightError(f"{domain} normalized pool oracle audit is incomplete")
            independent_passes = _positive_int(
                pool.get("independent_gold_passes"),
                label=f"{domain} normalized_pool independent_gold_passes",
                allow_zero=True,
            )
            if independent_passes != groups:
                raise PreflightError(
                    f"{domain} normalized pool independent-gold audit is incomplete"
                )
            digest = str(pool.get("snapshot_digest", ""))
            if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                raise PreflightError(f"{domain} normalized pool digest is invalid")
            report = pool.get("report")
            if (
                not isinstance(report, str)
                or not report.strip()
                or Path(report).is_absolute()
            ):
                raise PreflightError(f"{domain} normalized pool report is unavailable")
            report_path = (path.parent / report).resolve()
            try:
                report_path.relative_to(repository_root.resolve())
            except ValueError as exc:
                raise PreflightError(
                    f"{domain} normalized pool report escapes the repository"
                ) from exc
            if not report_path.is_file():
                raise PreflightError(f"{domain} normalized pool report is unavailable")
            try:
                report_payload = json.loads(report_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise PreflightError(
                    f"{domain} normalized pool report is invalid"
                ) from exc
            if (
                not isinstance(report_payload, dict)
                or report_payload.get("real_public_records") is not True
                or report_payload.get("provider_calls_executed") != 0
                or report_payload.get("selected_groups") != groups
                or str(report_payload.get("snapshot_digest", "")).removeprefix(
                    "sha256:"
                )
                != digest
            ):
                raise PreflightError(
                    f"{domain} normalized pool report contradicts the source manifest"
                )
            hashes = report_payload.get("normalized_artifact_sha256", {})
            if not isinstance(hashes, Mapping):
                hashes = {}
            cases_digest = hashes.get("cases.jsonl") or report_payload.get(
                "case_file_sha256"
            )
            gold_digest = hashes.get("gold.jsonl") or report_payload.get(
                "gold_file_sha256"
            )
            snapshot_file_digest = hashes.get("snapshot.json") or report_payload.get(
                "snapshot_file_sha256"
            )
            for label, value in (
                ("cases", cases_digest),
                ("gold", gold_digest),
                ("snapshot", snapshot_file_digest),
            ):
                if not isinstance(value, str) or len(value) != 64 or any(
                    character not in "0123456789abcdef" for character in value
                ):
                    raise PreflightError(
                        f"{domain} normalized pool {label} digest is invalid"
                    )
            _validate_normalized_artifacts(
                domain=domain,
                report_path=report_path,
                report_payload=report_payload,
                cases_digest=cases_digest,
                gold_digest=gold_digest,
                snapshot_file_digest=snapshot_file_digest,
                repository_root=repository_root,
                groups=groups,
            )
            pool_facts = {
                "groups": groups,
                "snapshot_digest": digest,
                "cases_sha256": cases_digest,
                "gold_sha256": gold_digest,
                "snapshot_file_sha256": snapshot_file_digest,
                "report_path": str(report_path),
                "report_sha256": _sha256(report_path),
            }
    return tuple(required_configuration), pool_facts


def validate_study_manifest(
    payload: Mapping[str, Any],
    *,
    benchmark_root: str | Path,
) -> dict[str, Any]:
    """Validate a manifest and return normalized protocol facts."""

    if payload.get("schema") != "agent-compaction-multidomain-study/v1":
        raise PreflightError("unsupported study manifest schema")
    if payload.get("status") != "proposed_unrun":
        raise PreflightError("initial study status must be proposed_unrun")
    study_id = payload.get("study_id")
    if not isinstance(study_id, str) or not study_id.strip():
        raise PreflightError("study_id must not be empty")
    provider_calls = _positive_int(
        payload.get("provider_calls_executed"),
        label="provider_calls_executed",
        allow_zero=True,
    )
    if provider_calls != 0:
        raise PreflightError("provider-free protocol lock must record zero provider calls")
    if payload.get("statistical_contract") != STATISTICAL_CONTRACT:
        raise PreflightError("statistical_contract differs from the implemented frozen contract")

    roles = _mapping(payload.get("roles"), label="roles")
    expected_roles = {
        "discovery": 40,
        "development": 30,
        "artifact_calibration": 100,
        "portfolio_calibration": 75,
        "test": 100,
    }
    normalized_roles = {
        str(name): _positive_int(count, label=f"role {name}")
        for name, count in roles.items()
    }
    if normalized_roles != expected_roles:
        raise PreflightError(f"roles must equal the frozen allocation {expected_roles}")
    role_groups = sum(normalized_roles.values())
    reserve = _positive_int(payload.get("reserve_groups"), label="reserve_groups")
    minimum_pool = _positive_int(
        payload.get("minimum_pool_groups"), label="minimum_pool_groups"
    )
    if minimum_pool < role_groups + reserve:
        raise PreflightError("minimum pool cannot cover frozen roles plus reserve")

    actions = payload.get("actions")
    if not isinstance(actions, list) or actions != ["baseline", "grc", "macro"]:
        raise PreflightError("actions must remain frozen as baseline, grc, macro")
    domains = _mapping(payload.get("domains"), label="domains")
    canonical_domains = ("vulnerability", "sec", "hmda")
    if set(domains) != set(canonical_domains):
        raise PreflightError("domains must be vulnerability, sec, and hmda")

    root = Path(benchmark_root).resolve()
    required_config: dict[str, tuple[str, ...]] = {}
    normalized_pools: dict[str, dict[str, Any]] = {}
    for domain, raw in domains.items():
        config = _mapping(raw, label=f"domain {domain}")
        source_path = _resolve_artifact(
            root, config.get("source_manifest"), label=f"{domain} source_manifest"
        )
        effect_path = _resolve_artifact(
            root, config.get("effect_catalog"), label=f"{domain} effect_catalog"
        )
        schema_path = _resolve_artifact(
            root, config.get("output_schema"), label=f"{domain} output_schema"
        )
        required_config[domain], normalized_pools[domain] = _validate_source_manifest(
            source_path,
            domain=domain,
            repository_root=root.parent,
        )
        catalog = EffectCatalog.from_yaml(effect_path)
        if not catalog.tools or any(
            spec.effect is not EffectClass.READ_LOCAL or not spec.compilable
            for spec in catalog.tools.values()
        ):
            raise PreflightError(
                f"{domain} measured tools must all be qualified READ_LOCAL operations"
            )
        _validate_json_schema(schema_path, domain=domain)
        identity = config.get("group_identity")
        if not isinstance(identity, list) or not identity or any(
            not isinstance(field, str) or not field.strip() for field in identity
        ):
            raise PreflightError(f"{domain} group_identity must list fields")

    return {
        "study_id": study_id,
        "provider_calls_executed": provider_calls,
        "minimum_pool_groups": minimum_pool,
        "role_groups": role_groups,
        "domains": canonical_domains,
        "required_configuration": required_config,
        "normalized_pools": normalized_pools,
    }


def preflight_study(
    manifest_path: str | Path,
    *,
    cases_by_domain: Mapping[str, Sequence[BenchmarkCase]] | None = None,
    case_paths_by_domain: Mapping[str, str | Path] | None = None,
    require_source_configuration: bool = False,
    require_normalized_artifacts: bool = True,
) -> PreflightReport:
    path = Path(manifest_path).resolve()
    payload = load_study_manifest(path)
    facts = validate_study_manifest(payload, benchmark_root=path.parents[1])
    errors: list[str] = []
    warnings: list[str] = []
    counts: dict[str, int] = {}
    case_counts: dict[str, int] = {}
    all_case_ids: set[str] = set()
    supplied = cases_by_domain or {}
    supplied_paths = case_paths_by_domain or {}
    unknown_domains = sorted(set(supplied) - set(facts["domains"]))
    if unknown_domains:
        errors.append(f"case pools contain unknown domains: {', '.join(unknown_domains)}")
    unknown_path_domains = sorted(set(supplied_paths) - set(facts["domains"]))
    if unknown_path_domains:
        errors.append(
            "case paths contain unknown domains: " + ", ".join(unknown_path_domains)
        )
    for domain in facts["domains"]:
        cases = tuple(supplied.get(domain, ()))
        case_counts[domain] = len(cases)
        groups: set[str] = set()
        lineage_groups: dict[str, str] = {}
        pool_facts = facts["normalized_pools"][domain]
        expected_snapshot = str(pool_facts.get("snapshot_digest", ""))
        for case in cases:
            if not isinstance(case, BenchmarkCase):
                errors.append(f"{domain}: case pool contains a non-BenchmarkCase value")
                continue
            if case.domain != domain:
                errors.append(f"{domain}: case {case.case_id} declares domain {case.domain}")
            snapshot = case.source_snapshot.removeprefix("sha256:")
            if len(snapshot) != 64 or any(
                character not in "0123456789abcdef" for character in snapshot
            ):
                errors.append(
                    f"{domain}: case {case.case_id} has an invalid source snapshot digest"
                )
            elif expected_snapshot and snapshot != expected_snapshot:
                errors.append(
                    f"{domain}: case {case.case_id} differs from the attested snapshot"
                )
            if case.metadata.get("real_public_record") is not True:
                errors.append(
                    f"{domain}: case {case.case_id} lacks real-public-record attestation"
                )
            lineage_value = case.metadata.get("lineage_ids")
            if isinstance(lineage_value, str):
                lineage_ids = (lineage_value,)
            elif isinstance(lineage_value, (list, tuple)):
                lineage_ids = tuple(lineage_value)
            else:
                lineage_ids = ()
            if not lineage_ids or any(
                not isinstance(lineage, str) or not lineage.strip()
                for lineage in lineage_ids
            ):
                errors.append(
                    f"{domain}: case {case.case_id} lacks valid lineage identifiers"
                )
            else:
                for lineage in set(lineage_ids):
                    previous_group = lineage_groups.setdefault(lineage, case.group_id)
                    if previous_group != case.group_id:
                        errors.append(
                            f"{domain}: lineage {lineage!r} crosses groups "
                            f"{previous_group!r} and {case.group_id!r}"
                        )
            if (
                domain == "hmda"
                and case.metadata.get("protected_demographic_fields_exposed") is not False
            ):
                errors.append(
                    f"{domain}: case {case.case_id} lacks the protected-field exclusion"
                )
            if case.case_id in all_case_ids:
                errors.append(f"duplicate case_id across study: {case.case_id}")
            all_case_ids.add(case.case_id)
            groups.add(case.group_id)
        counts[domain] = len(groups)
        if cases and len(cases) != len(groups):
            errors.append(
                f"{domain}: normalized pool must contain exactly one case per group"
            )
        if cases and len(groups) < facts["minimum_pool_groups"]:
            errors.append(
                f"{domain}: {len(groups)} independent groups "
                f"< {facts['minimum_pool_groups']} required"
            )
        if not cases:
            warnings.append(f"{domain}: no normalized cases supplied; pool size is unverified")
        pool_groups = int(pool_facts.get("groups", 0))
        case_path = supplied_paths.get(domain)
        if require_normalized_artifacts and cases and pool_groups == 0:
            errors.append(
                f"{domain}: source manifest has no attested normalized real-record pool"
            )
        if case_path is not None:
            path_value = Path(case_path)
            if not path_value.is_file():
                errors.append(f"{domain}: normalized case file is unavailable")
            elif not pool_facts.get("cases_sha256"):
                errors.append(f"{domain}: source manifest has no normalized case digest")
            elif _sha256(path_value) != pool_facts["cases_sha256"]:
                errors.append(f"{domain}: normalized case file checksum mismatch")
        elif require_normalized_artifacts and cases:
            errors.append(f"{domain}: normalized case path is required")

    config_available: dict[str, bool] = {}
    for domain, names in facts["required_configuration"].items():
        for name in names:
            value = os.environ.get(name, "").strip()
            available = bool(value)
            if name == "SEC_USER_AGENT":
                # SEC asks automated clients to identify the project/entity and a
                # contact address.  Validate only shape and never serialize the value.
                available = available and "@" in value and len(value.split()) >= 2
            config_available[f"{domain}:{name}"] = available
            if not available:
                message = f"{domain}: required fetch configuration {name} is unavailable"
                (errors if require_source_configuration else warnings).append(message)

    eligible = (
        not errors
        and bool(cases_by_domain)
        and all(
            counts[domain] >= facts["minimum_pool_groups"]
            for domain in facts["domains"]
        )
    )
    return PreflightReport(
        study_id=facts["study_id"],
        eligible=eligible,
        provider_calls_executed=facts["provider_calls_executed"],
        required_groups_per_domain=facts["minimum_pool_groups"],
        role_groups_per_domain=facts["role_groups"],
        domain_group_counts=counts,
        domain_case_counts=case_counts,
        source_configuration_available=config_available,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def _load_cases(path: Path) -> tuple[BenchmarkCase, ...]:
    cases: list[BenchmarkCase] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            cases.append(
                BenchmarkCase(
                    case_id=raw["case_id"],
                    group_id=raw["group_id"],
                    domain=raw["domain"],
                    source_snapshot=raw["source_snapshot"],
                    inputs=raw["inputs"],
                    metadata=raw.get("metadata", {}),
                )
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise PreflightError(f"invalid case at {path}:{line_number}") from exc
    return tuple(cases)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--cases",
        action="append",
        default=[],
        metavar="DOMAIN=JSONL",
        help="normalized case pool; repeat once per domain",
    )
    parser.add_argument("--require-source-configuration", action="store_true")
    args = parser.parse_args(argv)
    cases_by_domain: dict[str, tuple[BenchmarkCase, ...]] = {}
    case_paths_by_domain: dict[str, Path] = {}
    for item in args.cases:
        if "=" not in item:
            parser.error("--cases must use DOMAIN=JSONL")
        domain, case_path = item.split("=", 1)
        resolved_case_path = Path(case_path)
        cases_by_domain[domain] = _load_cases(resolved_case_path)
        case_paths_by_domain[domain] = resolved_case_path
    try:
        report = preflight_study(
            args.manifest,
            cases_by_domain=cases_by_domain or None,
            case_paths_by_domain=case_paths_by_domain or None,
            require_source_configuration=args.require_source_configuration,
            require_normalized_artifacts=bool(cases_by_domain),
        )
    except PreflightError as exc:
        print(json.dumps({"eligible": False, "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(report.as_dict(), sort_keys=True, indent=2))
    if report.errors:
        return 2
    return 0 if report.eligible else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
