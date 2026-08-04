#!/usr/bin/env python3
"""Provider-free validation of real pools, exact oracles, protocols, and ledgers."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[2]
for candidate in (ROOT, ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from agent_compaction.benchmarking import FrozenProtocol, load_case_jsonl  # noqa: E402
from agent_compaction.evaluation import RunLedger  # noqa: E402
from benchmarks.adapters.hmda_public_lar import hmda_macro  # noqa: E402
from benchmarks.adapters.sec_filing_facts import sec_macro  # noqa: E402
from benchmarks.adapters.vulnerability_evidence import vulnerability_macro  # noqa: E402
from benchmarks.build.hmda_pool import SAFE_ROW_FIELDS  # noqa: E402
from benchmarks.gold import (  # noqa: E402
    hmda_gold_from_records,
    sec_gold_from_records,
    vulnerability_gold_from_records,
)
from benchmarks.runtime import load_domain_runtime  # noqa: E402


def validate_pool(domain: str, pool: Path) -> dict[str, Any]:
    cases = load_case_jsonl(pool / "cases.jsonl")
    snapshot = json.loads((pool / "snapshot.json").read_text(encoding="utf-8"))
    records = snapshot.get("records")
    if not isinstance(records, dict):
        raise ValueError(f"{domain} snapshot records must be an object")
    retained_gold = {
        row["case_id"]: row["output"]
        for row in map(
            json.loads,
            (pool / "gold.jsonl").read_text(encoding="utf-8").splitlines(),
        )
    }
    gold_builder = {
        "vulnerability": vulnerability_gold_from_records,
        "hmda": hmda_gold_from_records,
        "sec": sec_gold_from_records,
    }[domain]
    independent_gold_passes = 0
    independent_gold_errors: list[str] = []
    for case in cases:
        try:
            observed = gold_builder(case, records)
        except Exception as exc:
            independent_gold_errors.append(
                f"{case.case_id}: independent gold raised {type(exc).__name__}"
            )
            continue
        if observed == retained_gold.get(case.case_id):
            independent_gold_passes += 1
        else:
            independent_gold_errors.append(
                f"{case.case_id}: retained gold differs from independent construction"
            )
    runtime = load_domain_runtime(
        domain=domain, pool_dir=pool, cases=cases, repository_root=ROOT
    )
    macro = {
        "vulnerability": vulnerability_macro,
        "hmda": hmda_macro,
        "sec": sec_macro,
    }[domain]
    results = [
        runtime.evaluate(
            case,
            macro(case, runtime.facade),
            [runtime.macro_tool_name],
            action="macro",
        )
        for case in cases
    ]
    groups = {case.group_id for case in cases}
    report = json.loads((pool / "report.json").read_text(encoding="utf-8"))
    errors = []
    if len(cases) != 420 or len(groups) != 420:
        errors.append(f"expected 420 independent groups, got {len(cases)}/{len(groups)}")
    if not all(result.passed for result in results):
        errors.append(f"{sum(not result.passed for result in results)} exact oracle failures")
    if independent_gold_errors:
        errors.append(
            f"{len(independent_gold_errors)} independent gold construction failures"
        )
    construction = report.get("gold_construction")
    expected_implementation = (
        f"benchmarks/gold.py:{gold_builder.__name__}"
    )
    gold_path = ROOT / "benchmarks/gold.py"
    if not isinstance(construction, dict):
        errors.append("gold construction attestation is missing")
    else:
        if construction.get("implementation") != expected_implementation:
            errors.append("gold construction implementation identity is incorrect")
        if construction.get("independent_from_macro") is not True:
            errors.append("gold construction is not attested independent from the macro")
        if construction.get("cases") != len(cases) or len(cases) < 50:
            errors.append("gold construction audit does not cover at least 50 cases")
        current_gold_digest = hashlib.sha256(gold_path.read_bytes()).hexdigest()
        if construction.get("implementation_sha256") != current_gold_digest:
            errors.append("gold construction implementation digest is stale")
    if report.get("provider_calls_executed") != 0:
        errors.append("pool acquisition report contains provider calls")
    if report.get("real_public_records") is not True:
        errors.append("pool is not attested as real public records")
    if report.get("variable_path_fraction", 0.0) < 0.10:
        errors.append("variable path fraction is below 10%")
    if domain == "hmda":
        allowed_schema = list(SAFE_ROW_FIELDS)
        schemas = records.get("schemas", {})
        if not schemas or any(
            schema.get("fields") != allowed_schema for schema in schemas.values()
        ):
            errors.append("HMDA agent-visible schema exceeds the safe field allowlist")
        allowed_row_fields = {*SAFE_ROW_FIELDS, "raw_row_digest", "sources"}
        if any(
            set(row) - allowed_row_fields for row in records.get("rows", {}).values()
        ):
            errors.append("HMDA agent-visible row exposes a non-allowlisted field")
        if report.get("agent_visible_schema_fields") != allowed_schema:
            errors.append("HMDA report does not bind the agent-visible schema allowlist")
    expected_snapshot = str(report.get("snapshot_digest", "")).removeprefix("sha256:")
    observed_snapshot = str(snapshot.get("snapshot_digest", "")).removeprefix("sha256:")
    if not expected_snapshot or observed_snapshot != expected_snapshot:
        errors.append("snapshot identity differs from the pool report")
    if any(
        case.source_snapshot.removeprefix("sha256:") != expected_snapshot
        for case in cases
    ):
        errors.append("one or more cases reference a different snapshot")
    expected_hashes = dict(report.get("normalized_artifact_sha256", {}))
    for name, report_field in (
        ("cases.jsonl", "case_file_sha256"),
        ("gold.jsonl", "gold_file_sha256"),
        ("snapshot.json", "snapshot_file_sha256"),
    ):
        if report_field in report:
            expected_hashes[name] = report[report_field]
    for name in ("cases.jsonl", "gold.jsonl", "snapshot.json"):
        expected = expected_hashes.get(name)
        if not isinstance(expected, str):
            errors.append(f"normalized artifact hash missing for {name}")
            continue
        observed = hashlib.sha256((pool / name).read_bytes()).hexdigest()
        if observed != expected:
            errors.append(f"normalized artifact hash mismatch for {name}")
    return {
        "domain": domain,
        "available": True,
        "real_public_records": report.get("real_public_records") is True,
        "cases": len(cases),
        "independent_groups": len(groups),
        "exact_oracle_passes": sum(result.passed for result in results),
        "independent_gold_passes": independent_gold_passes,
        "independent_gold_errors": independent_gold_errors,
        "variable_path_fraction": report.get("variable_path_fraction"),
        "snapshot_digest": report.get("snapshot_digest"),
        "errors": errors,
    }


def validate_ledger(path: Path, protocol: FrozenProtocol | None) -> dict[str, Any]:
    ledger = RunLedger(path)
    integrity = ledger.validate()
    records = ledger.records()
    errors: list[str] = []
    if protocol is not None and any(record.run_id != protocol.digest for record in records):
        errors.append("ledger contains a run outside the frozen protocol")
    starts = {
        str(record.payload["budget_event_id"])
        for record in records
        if record.event_type == "execution_started"
    }
    terminals = {
        str(record.payload["budget_event_id"])
        for record in records
        if record.event_type in {"execution_complete", "execution_failed"}
    }
    ambiguous = sorted(starts - terminals)
    if ambiguous:
        errors.append(f"{len(ambiguous)} provider attempts have unknown terminal state")
    completed_calls = 0
    for record in records:
        if record.event_type == "execution_unavailable":
            if record.payload.get("provider_calls_executed") != 0:
                errors.append("unavailable execution does not record zero provider calls")
        if record.event_type != "execution_complete":
            continue
        completed_calls += int(record.payload["metrics"]["model_requests"])
        raw_path = Path(str(record.payload["episode_path"]))
        if raw_path.is_absolute():
            errors.append("episode path is not repository-relative")
            continue
        episode_path = (ROOT / raw_path).resolve()
        try:
            episode_path.relative_to(ROOT.resolve())
        except ValueError:
            errors.append("episode path escapes the repository")
            continue
        if not episode_path.is_file():
            errors.append("retained episode is unavailable")
            continue
        observed = hashlib.sha256(episode_path.read_bytes()).hexdigest()
        if observed != record.payload.get("episode_digest"):
            errors.append("retained episode digest mismatch")
    unknown_failed = sum(
        record.event_type == "execution_failed"
        and not record.payload.get("provider_request_count_known", False)
        for record in records
    )
    return {
        **integrity,
        "path": str(path),
        "completed_executions": sum(
            record.event_type == "execution_complete" for record in records
        ),
        "unavailable_executions": sum(
            record.event_type == "execution_unavailable" for record in records
        ),
        "failed_attempts": sum(
            record.event_type == "execution_failed" for record in records
        ),
        "provider_calls_observed_completed": completed_calls,
        "failed_attempts_with_unknown_provider_requests": unknown_failed,
        "provider_calls_executed": completed_calls if unknown_failed == 0 else None,
        "errors": errors,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", action="append", default=[], metavar="DOMAIN=DIR")
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--ledger", action="append", default=[], type=Path)
    parser.add_argument("--require-all-domains", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    pools = {}
    for value in args.pool:
        domain, path = value.split("=", 1)
        pools[domain] = Path(path)
    domains = []
    for domain in ("vulnerability", "sec", "hmda"):
        path = pools.get(domain)
        if path is None or not (path / "cases.jsonl").exists():
            domains.append(
                {
                    "domain": domain,
                    "available": False,
                    "errors": ["real normalized pool unavailable"],
                }
            )
        else:
            domains.append(validate_pool(domain, path))
    protocol: FrozenProtocol | None = None
    protocol_result: dict[str, Any] | None = None
    if args.protocol:
        protocol = FrozenProtocol.load(args.protocol)
        protocol_result = {
            "digest": protocol.digest,
            "domains": sorted(protocol.group_roles),
            "groups": {domain: len(roles) for domain, roles in protocol.group_roles.items()},
            "model": protocol.model,
            "execution_contract": dict(protocol.execution_contract),
        }
    ledgers = [validate_ledger(path, protocol) for path in args.ledger]
    errors = [
        f"{item['domain']}: {error}"
        for item in domains
        for error in item["errors"]
        if args.require_all_domains or item["available"]
    ]
    errors.extend(
        f"ledger {item['path']}: {error}"
        for item in ledgers
        for error in item["errors"]
    )
    completed_calls = sum(item["provider_calls_observed_completed"] for item in ledgers)
    unknown_failed = sum(
        item["failed_attempts_with_unknown_provider_requests"] for item in ledgers
    )
    result = {
        "schema": "agent-compaction-multidomain-validation/v1",
        "valid": not errors,
        "provider_calls_observed_completed": completed_calls,
        "failed_attempts_with_unknown_provider_requests": unknown_failed,
        "provider_calls_executed": completed_calls if unknown_failed == 0 else None,
        "domains": domains,
        "protocol": protocol_result,
        "ledgers": ledgers,
        "errors": errors,
    }
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
