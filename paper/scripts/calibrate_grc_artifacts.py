#!/usr/bin/env python3
"""Calibrate shadow GRC artifacts on frozen groups and emit active study registries."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[2]
for candidate in (ROOT, ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from agent_compaction.benchmarking import FrozenProtocol  # noqa: E402
from agent_compaction.benchmarking.preflight import STATISTICAL_CONTRACT  # noqa: E402
from agent_compaction.evaluation import (  # noqa: E402
    BinaryPair,
    RunLedger,
    exact_paired_binary_noninferiority,
)
from agent_compaction.grc.calibrate import clopper_pearson_upper  # noqa: E402
from agent_compaction.registry.lifecycle import promote, retire  # noqa: E402
from agent_compaction.registry.store import Registry  # noqa: E402
from agent_compaction.schema.artifacts import Lifecycle  # noqa: E402


def _pairs(values: Sequence[str], label: str) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"{label} must use DOMAIN=PATH")
        domain, raw = value.split("=", 1)
        if domain in result:
            raise ValueError(f"duplicate {label} for {domain}")
        result[domain] = Path(raw)
    return result


def _records(
    paths: Sequence[Path], protocol_digest: str, domain: str
) -> tuple[dict[tuple[str, str], dict[str, Any]], list[dict[str, Any]], int]:
    completed: dict[tuple[str, str], dict[str, Any]] = {}
    unavailable: list[dict[str, Any]] = []
    failed = 0
    for path in paths:
        ledger = RunLedger(path)
        ledger.validate()
        for record in ledger.records():
            if record.run_id != protocol_digest:
                raise ValueError("artifact-calibration ledger uses a different protocol")
            schedule = record.payload.get("schedule", {})
            if (
                schedule.get("domain") != domain
                or schedule.get("role") != "artifact_calibration"
                or int(schedule.get("repeat", 0)) != 0
            ):
                continue
            if record.event_type == "execution_failed":
                failed += 1
                continue
            if record.event_type not in {"execution_complete", "execution_unavailable"}:
                continue
            key = (str(schedule["group_id"]), str(schedule["action"]))
            if key in completed or any(
                (item["schedule"]["group_id"], item["schedule"]["action"]) == key
                for item in unavailable
            ):
                raise ValueError(f"duplicate artifact-calibration result {domain}:{key}")
            if record.event_type == "execution_complete":
                completed[key] = dict(record.payload)
            else:
                unavailable.append(dict(record.payload))
    return completed, unavailable, failed


def calibrate_domain(
    *,
    domain: str,
    protocol: FrozenProtocol,
    ledger_paths: Sequence[Path],
    registry_path: Path,
    output_dir: Path,
    approved_by: str,
    job_identity: str,
    expiry_day: str,
) -> dict[str, Any]:
    groups = {
        group
        for group, role in protocol.group_roles[domain].items()
        if role.value == "artifact_calibration"
    }
    if len(groups) != 100:
        raise ValueError(f"{domain} protocol does not contain 100 artifact groups")
    source_registry_digest = hashlib.sha256(
        (registry_path / "registry.json" if registry_path.is_dir() else registry_path).read_bytes()
    ).hexdigest()
    registry = Registry.load(registry_path)
    if any(artifact.lifecycle is not Lifecycle.SHADOW for artifact in registry.artifacts):
        raise ValueError(f"{domain} calibration input must contain only shadow artifacts")
    completed, unavailable, failed_attempts = _records(
        ledger_paths, protocol.digest, domain
    )
    settled = [*completed.values(), *unavailable]
    action_locks = {
        str(row.get("action_lock_digest", "")) for row in settled
    }
    if len(action_locks) != 1 or not next(iter(action_locks), ""):
        raise ValueError(
            f"{domain} artifact-calibration records do not share one action lock"
        )
    action_lock_digest = next(iter(action_locks))
    action_digests: dict[str, str] = {}
    for action in ("baseline", "grc"):
        values = {
            str(row.get("action_spec", {}).get("action_digest", ""))
            for (group, candidate), row in completed.items()
            if candidate == action
        }
        values.discard("")
        if action == "grc" and not values:
            continue
        if len(values) != 1:
            raise ValueError(
                f"{domain}:{action} artifact-calibration identity is absent or drifted"
            )
        action_digests[action] = next(iter(values))
    baseline_groups = {
        group for group in groups if (group, "baseline") in completed
    }
    if baseline_groups != groups:
        raise ValueError(f"{domain} does not have 100 completed calibration baselines")

    grc_completed = {group for group in groups if (group, "grc") in completed}
    grc_unavailable = {
        str(item["schedule"]["group_id"])
        for item in unavailable
        if item["schedule"]["action"] == "grc"
    }
    if not registry.artifacts:
        if grc_unavailable != groups or grc_completed:
            raise ValueError(f"{domain} empty registry was not explicitly unavailable")
        output_registry = Registry(
            name=f"multidomain-{domain}-grc-calibrated",
            active_stages=(Lifecycle.ACTIVE,),
        )
        registry_file = output_registry.save(output_dir / domain)
        report = {
            "schema": "agent-compaction-grc-artifact-calibration/v1",
            "domain": domain,
            "protocol_digest": protocol.digest,
            "source_registry_digest": source_registry_digest,
            "action_lock_digest": action_lock_digest,
            "action_digests": action_digests,
            "quality": None,
            "artifacts": [],
            "active_artifacts": 0,
            "unavailable": True,
            "unavailable_reason": "registry_contains_no_compiled_artifacts",
            "failed_attempts_retained": failed_attempts,
            "provider_calls_executed_in_calibration": 0,
            "registry_path": registry_file.name,
        }
    else:
        if grc_completed != groups or grc_unavailable:
            raise ValueError(f"{domain} GRC calibration pairs are incomplete")
        quality = exact_paired_binary_noninferiority(
            [
                BinaryPair(
                    group_id=group,
                    baseline_success=bool(
                        completed[(group, "baseline")]["metrics"]["quality_contract_pass"]
                    ),
                    candidate_success=bool(
                        completed[(group, "grc")]["metrics"]["quality_contract_pass"]
                    ),
                )
                for group in sorted(groups)
            ],
            margin=float(STATISTICAL_CONTRACT["quality_noninferiority_margin"]),
            confidence=float(STATISTICAL_CONTRACT["per_domain_confidence"]),
        )
        selected_groups: dict[str, set[str]] = {
            artifact.artifact_id: set() for artifact in registry.artifacts
        }
        failure_groups: dict[str, set[str]] = {
            artifact.artifact_id: set() for artifact in registry.artifacts
        }
        for group in sorted(groups):
            row = completed[(group, "grc")]
            selected = {
                str(item.get("artifact"))
                for item in row.get("dispatch", {}).get("records", [])
                if item.get("artifact")
            }
            unknown = selected - set(selected_groups)
            if unknown:
                raise ValueError(f"{domain} dispatch references unknown artifacts: {sorted(unknown)}")
            for artifact_id in selected:
                selected_groups[artifact_id].add(group)
                if not bool(row["metrics"]["quality_contract_pass"]):
                    failure_groups[artifact_id].add(group)
        artifact_confidence = 1.0 - (
            1.0 - float(STATISTICAL_CONTRACT["per_domain_confidence"])
        ) / max(1, len(registry.artifacts))
        artifact_rows = []
        for artifact in registry.artifacts:
            support = len(selected_groups[artifact.artifact_id])
            failures = len(failure_groups[artifact.artifact_id])
            risk_upper = (
                clopper_pearson_upper(failures, support, artifact_confidence)
                if support
                else 1.0
            )
            risk_limit = float(STATISTICAL_CONTRACT["artifact_quality_risk_limit"])
            admitted = quality.passed and risk_upper <= risk_limit
            if admitted:
                promote(
                    artifact,
                    Lifecycle.APPROVED,
                    approved_by=approved_by,
                    job_identity=job_identity,
                    evaluation_split="artifact_calibration",
                    expiry_day=expiry_day,
                )
                promote(
                    artifact,
                    Lifecycle.ACTIVE,
                    approved_by=approved_by,
                    job_identity=job_identity,
                    evaluation_split="artifact_calibration",
                    expiry_day=expiry_day,
                )
            else:
                reason = (
                    "action_quality_noninferiority_failed"
                    if not quality.passed
                    else "artifact_calibration_risk_or_support_failed"
                )
                retire(artifact, actor=job_identity, reason=reason)
            artifact_rows.append(
                {
                    "artifact_id": artifact.artifact_id,
                    "support_groups": support,
                    "quality_failures": failures,
                    "familywise_confidence": artifact_confidence,
                    "quality_risk_upper": risk_upper,
                    "risk_limit": risk_limit,
                    "admitted": admitted,
                    "lifecycle": artifact.lifecycle.value,
                }
            )
        registry.active_stages = (Lifecycle.ACTIVE,)
        registry.name = f"multidomain-{domain}-grc-calibrated"
        registry_file = registry.save(output_dir / domain)
        report = {
            "schema": "agent-compaction-grc-artifact-calibration/v1",
            "domain": domain,
            "protocol_digest": protocol.digest,
            "source_registry_digest": source_registry_digest,
            "action_lock_digest": action_lock_digest,
            "action_digests": action_digests,
            "quality": quality.as_dict(),
            "artifacts": artifact_rows,
            "active_artifacts": sum(item["admitted"] for item in artifact_rows),
            "unavailable": not any(item["admitted"] for item in artifact_rows),
            "unavailable_reason": (
                "no_artifact_passed_independent_calibration"
                if not any(item["admitted"] for item in artifact_rows)
                else None
            ),
            "artifact_multiplicity_control": (
                "99% per-domain Bonferroni confidence across registry artifacts"
            ),
            "approved_by": approved_by,
            "expiry_day": expiry_day,
            "failed_attempts_retained": failed_attempts,
            "provider_calls_executed_in_calibration": 0,
            "registry_path": registry_file.name,
        }
    report_path = output_dir / domain / "artifact-calibration-report.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--ledger", action="append", required=True, metavar="DOMAIN=PATH")
    parser.add_argument("--registry", action="append", required=True, metavar="DOMAIN=PATH")
    parser.add_argument("--approved-by", required=True)
    parser.add_argument("--job-identity", default="multidomain-optimizer")
    parser.add_argument("--expiry-day", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    protocol = FrozenProtocol.load(args.protocol)
    ledgers: dict[str, list[Path]] = {}
    for value in args.ledger:
        domain, raw = value.split("=", 1)
        ledgers.setdefault(domain, []).append(Path(raw))
    registries = _pairs(args.registry, "registry")
    if set(ledgers) != set(protocol.group_roles) or set(registries) != set(protocol.group_roles):
        raise ValueError("ledger, registry, and protocol domain sets differ")
    if not args.approved_by.strip() or args.approved_by == args.job_identity:
        raise ValueError("GRC approval requires a distinct non-empty human identity")
    try:
        expiry = date.fromisoformat(args.expiry_day)
    except ValueError as exc:
        raise ValueError("expiry-day must be YYYY-MM-DD") from exc
    if expiry <= datetime.now(UTC).date():
        raise ValueError("expiry-day must be in the future")
    reports = [
        calibrate_domain(
            domain=domain,
            protocol=protocol,
            ledger_paths=ledgers[domain],
            registry_path=registries[domain],
            output_dir=args.out,
            approved_by=args.approved_by,
            job_identity=args.job_identity,
            expiry_day=args.expiry_day,
        )
        for domain in sorted(protocol.group_roles)
    ]
    print(json.dumps(reports, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
