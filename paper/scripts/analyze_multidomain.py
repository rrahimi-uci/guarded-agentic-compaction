#!/usr/bin/env python3
"""Reproduce confirmatory multidomain quality, efficiency, and determinism analyses."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Sequence

from scipy.stats import wilcoxon


ROOT = Path(__file__).resolve().parents[2]
for candidate in (ROOT, ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from agent_compaction.benchmarking import (  # noqa: E402
    FrozenProtocol,
    frozen_artifact_digest,
)
from agent_compaction.benchmarking.preflight import STATISTICAL_CONTRACT  # noqa: E402
from agent_compaction.evaluation import (  # noqa: E402
    BinaryPair,
    CanonicalMetrics,
    PairedSample,
    RunLedger,
    exact_paired_binary_noninferiority,
    holm_adjust,
    paired_group_bootstrap_diff,
    paired_ratio,
)
from agent_compaction.portfolio import PortfolioPolicy  # noqa: E402


ENDPOINTS = tuple(str(item) for item in STATISTICAL_CONTRACT["endpoints"])


def _load_ledgers(paths: Sequence[Path]) -> tuple[list[Any], list[dict[str, Any]]]:
    records = []
    rows = []
    for path in paths:
        ledger = RunLedger(path)
        ledger.validate()
        for record in ledger.records():
            records.append(record)
            if record.event_type == "execution_complete":
                rows.append(dict(record.payload))
    return records, rows


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _validate_test_bindings(
    policy_payload: dict[str, Any],
    policy: PortfolioPolicy,
    test_records: Sequence[Any],
) -> None:
    """Reject sealed records produced under any other frozen action/policy identity."""

    expected_lock = str(policy_payload.get("action_lock_digest", ""))
    if not expected_lock:
        raise ValueError("frozen portfolio lacks an action-lock identity")
    observed_locks = {
        str(record.payload.get("action_lock_digest", "")) for record in test_records
    }
    if observed_locks != {expected_lock}:
        raise ValueError("sealed-test records do not share the frozen action lock")
    observed_policies = {
        str(record.payload.get("portfolio_policy_digest", ""))
        for record in test_records
    }
    if observed_policies != {policy.digest}:
        raise ValueError("sealed-test records do not share the frozen portfolio policy")

    expected_actions = policy_payload.get("action_digests")
    if not isinstance(expected_actions, dict):
        raise ValueError("frozen portfolio lacks action identities")
    for record in test_records:
        if record.event_type != "execution_complete":
            continue
        schedule = record.payload["schedule"]
        domain = str(schedule["domain"])
        action = str(schedule["action"])
        expected = expected_actions.get(domain, {}).get(action)
        observed = record.payload.get("action_spec", {}).get("action_digest")
        if not expected or observed != expected:
            raise ValueError(
                f"sealed-test action identity differs from calibration: {domain}:{action}"
            )


def _pvalue(samples: Sequence[PairedSample]) -> float:
    differences = [sample.diff for sample in samples]
    if not differences or all(value == 0 for value in differences):
        return 1.0
    return float(wilcoxon(differences, alternative="two-sided").pvalue)


def _metric(row: dict[str, Any], endpoint: str) -> float:
    value = getattr(CanonicalMetrics.from_live_mapping(row["metrics"]), endpoint)
    if value is None or not math.isfinite(float(value)):
        raise ValueError(f"missing/non-finite endpoint {endpoint}")
    return float(value)


def _finite_or_none(value: float) -> float | None:
    return float(value) if math.isfinite(float(value)) else None


def _write_csv(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _load_effort(path: Path) -> tuple[dict[str, Any], str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "schema",
        "revision",
        "hourly_rate_usd",
        "recurring_cost_usd_per_1000_executions",
        "traffic_horizons",
        "components",
        "recorded_by",
        "recorded_at",
    }
    if set(payload) != expected or payload.get("schema") != "agent-compaction-construction-effort/v1":
        raise ValueError("effort manifest fields do not match construction-effort.schema.json")
    for name in ("hourly_rate_usd", "recurring_cost_usd_per_1000_executions"):
        value = payload[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"effort manifest {name} is invalid")
    horizons = payload["traffic_horizons"]
    if (
        not isinstance(horizons, list)
        or not horizons
        or any(type(value) is not int or value < 1 for value in horizons)
        or len(set(horizons)) != len(horizons)
    ):
        raise ValueError("effort manifest traffic_horizons are invalid")
    allowed_names = {
        "baseline_discovery",
        "grc_compilation_and_calibration",
        "macro_authoring",
        "macro_independent_review",
        "source_acquisition_and_normalization",
        "evaluation_and_monitoring_setup",
        "other",
    }
    allowed_domains = {"all", "vulnerability", "sec", "hmda"}
    components = payload["components"]
    if not isinstance(components, list) or not components:
        raise ValueError("effort manifest components are required")
    for component in components:
        if set(component) != {"name", "domain", "hours", "direct_cost_usd", "notes"}:
            raise ValueError("effort component fields are invalid")
        if component["name"] not in allowed_names or component["domain"] not in allowed_domains:
            raise ValueError("effort component category is invalid")
        for name in ("hours", "direct_cost_usd"):
            value = component[name]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError(f"effort component {name} is invalid")
        if not isinstance(component["notes"], str):
            raise ValueError("effort component notes must be a string")
    try:
        recorded = datetime.fromisoformat(str(payload["recorded_at"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("effort recorded_at must be ISO-8601") from exc
    if recorded.tzinfo is None or not str(payload["recorded_by"]).strip() or not str(payload["revision"]).strip():
        raise ValueError("effort identity and timezone are required")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return payload, digest


def _amortization(
    effort: dict[str, Any],
    effort_digest: str,
    baseline: dict[str, Any],
    family_policy: dict[str, Any],
) -> dict[str, Any]:
    total_hours = sum(float(item["hours"]) for item in effort["components"])
    direct = sum(float(item["direct_cost_usd"]) for item in effort["components"])
    labor = total_hours * float(effort["hourly_rate_usd"])
    fixed = labor + direct
    savings = (
        float(baseline["mean_estimated_cost_usd"])
        - float(family_policy["mean_estimated_cost_usd"])
    )
    recurring_per_execution = float(
        effort["recurring_cost_usd_per_1000_executions"]
    ) / 1000.0
    net_per_execution = savings - recurring_per_execution
    break_even = math.ceil(fixed / net_per_execution) if net_per_execution > 0 else None
    return {
        "effort_manifest_digest": effort_digest,
        "effort_revision": effort["revision"],
        "total_engineering_and_review_hours": total_hours,
        "hourly_rate_usd": effort["hourly_rate_usd"],
        "labor_cost_usd": labor,
        "direct_construction_cost_usd": direct,
        "fixed_construction_cost_usd": fixed,
        "recurring_cost_usd_per_1000_executions": effort[
            "recurring_cost_usd_per_1000_executions"
        ],
        "observed_inference_savings_usd_per_execution": savings,
        "net_savings_usd_per_execution_after_recurring_cost": net_per_execution,
        "break_even_executions": break_even,
        "traffic_horizons": [
            {
                "executions": count,
                "net_value_usd": net_per_execution * count - fixed,
            }
            for count in sorted(effort["traffic_horizons"])
        ],
        "components": effort["components"],
    }


def analyze(
    protocol: FrozenProtocol,
    policy_payload: dict[str, Any],
    ledger_records: Sequence[Any],
    rows: Sequence[dict[str, Any]],
    effort: dict[str, Any],
    effort_digest: str,
) -> dict[str, Any]:
    mismatched_runs = sorted(
        {record.run_id for record in ledger_records if record.run_id != protocol.digest}
    )
    if mismatched_runs:
        raise ValueError("ledger run does not match the frozen protocol")
    if policy_payload.get("protocol_digest") != protocol.digest:
        raise ValueError("frozen portfolio and protocol disagree")
    if policy_payload.get("portfolio_artifact_digest") != frozen_artifact_digest(
        policy_payload, digest_field="portfolio_artifact_digest"
    ):
        raise ValueError("frozen portfolio artifact digest mismatch")
    policy = PortfolioPolicy.from_dict(policy_payload["policy"])
    if policy_payload.get("policy_digest") != policy.digest:
        raise ValueError("frozen portfolio digest mismatch")
    test_records = [
        record
        for record in ledger_records
        if record.event_type in {"execution_complete", "execution_unavailable"}
        and record.payload["schedule"]["role"] == "test"
    ]
    if not test_records:
        raise ValueError("no completed sealed-test executions")
    _validate_test_bindings(policy_payload, policy, test_records)
    if _parse_time(policy_payload["frozen_at"]) >= min(
        _parse_time(record.created_at) for record in test_records
    ):
        raise ValueError("portfolio policy was not frozen before the first test execution")
    test_rows = [
        dict(record.payload)
        for record in test_records
        if record.event_type == "execution_complete"
    ]
    unavailable_rows = [
        dict(record.payload)
        for record in test_records
        if record.event_type == "execution_unavailable"
    ]
    indexed: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for row in test_rows:
        key = (
            row["schedule"]["domain"],
            row["schedule"]["group_id"],
            row["schedule"]["action"],
            int(row["schedule"]["repeat"]),
        )
        if key in indexed:
            raise ValueError(f"duplicate sealed-test execution {key!r}")
        indexed[key] = row
    unavailable_index: dict[tuple[str, str, str, int], dict[str, Any]] = {}
    for row in unavailable_rows:
        key = (
            row["schedule"]["domain"],
            row["schedule"]["group_id"],
            row["schedule"]["action"],
            int(row["schedule"]["repeat"]),
        )
        if key in unavailable_index or key in indexed:
            raise ValueError(f"duplicate/unsettled sealed-test execution {key!r}")
        unavailable_index[key] = row
    endpoint_rows: list[dict[str, Any]] = []
    quality_rows: list[dict[str, Any]] = []
    determinism_rows: list[dict[str, Any]] = []
    per_domain: dict[str, Any] = {}
    for domain in sorted(protocol.group_roles):
        groups = sorted(
            group
            for group, role in protocol.group_roles[domain].items()
            if role.value == "test"
        )
        if len(groups) != 100:
            raise ValueError(f"{domain} does not have 100 frozen test groups")
        domain_result: dict[str, Any] = {}
        for action in ("grc", "macro"):
            primary_keys = [(domain, group, action, 0) for group in groups]
            completed_keys = {key for key in primary_keys if key in indexed}
            unavailable_keys = {key for key in primary_keys if key in unavailable_index}
            if unavailable_keys and not completed_keys and len(unavailable_keys) == len(groups):
                reasons = sorted(
                    {str(unavailable_index[key]["reason"]) for key in unavailable_keys}
                )
                domain_result[action] = {
                    "available": False,
                    "reason": reasons,
                    "quality": None,
                    "endpoints": {},
                    "holm": {},
                }
                continue
            if unavailable_keys or len(completed_keys) != len(groups):
                raise ValueError(f"partially unavailable test action {domain}:{action}")
            baseline_rows = []
            candidate_rows = []
            binary = []
            for group in groups:
                baseline = indexed.get((domain, group, "baseline", 0))
                candidate = indexed.get((domain, group, action, 0))
                if baseline is None or candidate is None:
                    raise ValueError(f"incomplete test pair {domain}:{group}:{action}")
                baseline_rows.append(baseline)
                candidate_rows.append(candidate)
                binary.append(
                    BinaryPair(
                        group_id=group,
                        baseline_success=bool(baseline["metrics"]["quality_contract_pass"]),
                        candidate_success=bool(candidate["metrics"]["quality_contract_pass"]),
                    )
                )
            quality = exact_paired_binary_noninferiority(
                binary,
                margin=float(STATISTICAL_CONTRACT["quality_noninferiority_margin"]),
                confidence=float(STATISTICAL_CONTRACT["per_domain_confidence"]),
            )
            quality_rows.append(
                {"domain": domain, "action": action, **quality.as_dict()}
            )
            endpoint_pvalues: dict[str, float] = {}
            action_endpoints: dict[str, Any] = {}
            for endpoint in ENDPOINTS:
                samples = [
                    PairedSample(
                        group=group,
                        baseline=_metric(baseline, endpoint),
                        candidate=_metric(candidate, endpoint),
                    )
                    for group, baseline, candidate in zip(groups, baseline_rows, candidate_rows)
                ]
                interval = paired_group_bootstrap_diff(
                    samples,
                    n_boot=int(STATISTICAL_CONTRACT["bootstrap_resamples"]),
                    level=float(STATISTICAL_CONTRACT["per_domain_confidence"]),
                    seed=protocol.seed + sum(map(ord, domain + action + endpoint)),
                )
                ratio = paired_ratio(
                    samples,
                    n_boot=int(STATISTICAL_CONTRACT["bootstrap_resamples"]),
                    level=float(STATISTICAL_CONTRACT["per_domain_confidence"]),
                    seed=protocol.seed + 1 + sum(map(ord, domain + action + endpoint)),
                )
                endpoint_pvalues[endpoint] = _pvalue(samples)
                row = {
                    "domain": domain,
                    "action": action,
                    "endpoint": endpoint,
                    "n_groups": len(groups),
                    "baseline_mean": mean(sample.baseline for sample in samples),
                    "candidate_mean": mean(sample.candidate for sample in samples),
                    "mean_difference": interval.point,
                    "difference_ci_low": interval.low,
                    "difference_ci_high": interval.high,
                    "ratio_of_means": _finite_or_none(ratio.point),
                    "ratio_ci_low": _finite_or_none(ratio.low),
                    "ratio_ci_high": _finite_or_none(ratio.high),
                    "bootstrap_resamples": STATISTICAL_CONTRACT["bootstrap_resamples"],
                    "confidence": STATISTICAL_CONTRACT["per_domain_confidence"],
                }
                endpoint_rows.append(row)
                action_endpoints[endpoint] = row
            adjusted = holm_adjust(
                endpoint_pvalues,
                alpha=1.0 - float(STATISTICAL_CONTRACT["per_domain_confidence"]),
            )
            for row in endpoint_rows:
                if row["domain"] == domain and row["action"] == action:
                    row.update(adjusted[row["endpoint"]])
            domain_result[action] = {
                "available": True,
                "quality": quality.as_dict(),
                "endpoints": action_endpoints,
                "holm": adjusted,
            }
        repeat_groups = groups[:20]
        # The scheduler chooses the repeated cohort by hash rank, not lexicographic ID.
        observed_repeat_groups = sorted(
            {
                row["schedule"]["group_id"]
                for row in test_rows
                if row["schedule"]["domain"] == domain
                and int(row["schedule"]["repeat"]) > 0
            }
        )
        if len(observed_repeat_groups) != int(STATISTICAL_CONTRACT["repeat_groups"]):
            raise ValueError(f"{domain} repeat cohort has {len(observed_repeat_groups)} groups")
        repeat_groups = observed_repeat_groups
        for action in ("baseline", "grc", "macro"):
            repeat_keys = [
                (domain, group, action, repeat)
                for group in repeat_groups
                for repeat in range(int(STATISTICAL_CONTRACT["repeats_per_group"]))
            ]
            unavailable_repeat_keys = {
                key for key in repeat_keys if key in unavailable_index
            }
            if unavailable_repeat_keys:
                if len(unavailable_repeat_keys) != len(repeat_keys):
                    raise ValueError(f"partially unavailable repeat action {domain}:{action}")
                determinism_rows.append(
                    {
                        "domain": domain,
                        "action": action,
                        "groups": STATISTICAL_CONTRACT["repeat_groups"],
                        "repeats": STATISTICAL_CONTRACT["repeats_per_group"],
                        "available": False,
                        "exact_output_agreement": None,
                        "tool_trace_agreement": None,
                        "quality_agreement": None,
                        "mean_latency_cv": None,
                    }
                )
                continue
            output_agreement = 0
            tool_agreement = 0
            quality_agreement = 0
            latency_cvs = []
            for group in repeat_groups:
                values = [
                    indexed.get((domain, group, action, repeat))
                    for repeat in range(int(STATISTICAL_CONTRACT["repeats_per_group"]))
                ]
                if any(value is None for value in values):
                    raise ValueError(f"incomplete repeat set {domain}:{group}:{action}")
                output_agreement += len({_canonical(value["answer"]) for value in values}) == 1
                tool_agreement += len({tuple(value["tool_sequence"]) for value in values}) == 1
                quality_agreement += len(
                    {bool(value["metrics"]["quality_contract_pass"]) for value in values}
                ) == 1
                latencies = [_metric(value, "wall_latency_ms") for value in values]
                latency_cvs.append(pstdev(latencies) / mean(latencies) if mean(latencies) else 0.0)
            determinism_rows.append(
                {
                    "domain": domain,
                    "action": action,
                    "groups": STATISTICAL_CONTRACT["repeat_groups"],
                    "repeats": STATISTICAL_CONTRACT["repeats_per_group"],
                    "available": True,
                    "exact_output_agreement": output_agreement / len(repeat_groups),
                    "tool_trace_agreement": tool_agreement / len(repeat_groups),
                    "quality_agreement": quality_agreement / len(repeat_groups),
                    "mean_latency_cv": mean(latency_cvs),
                }
            )
        family_key = protocol.family_key(domain)
        selected_action = policy.select(family_key).selected_action
        if domain_result.get(selected_action, {}).get("available") is False:
            raise ValueError(f"portfolio selected unavailable test action {domain}:{selected_action}")
        domain_result["selected_action"] = selected_action
        per_domain[domain] = domain_result

    global_action = policy_payload["best_global_fixed_decision"]["selected_action"]
    portfolio_rows = []
    global_rows = []
    baseline_rows = []
    for domain in sorted(protocol.group_roles):
        selected = policy.select(protocol.family_key(domain)).selected_action
        for group, role in protocol.group_roles[domain].items():
            if role.value != "test":
                continue
            baseline_rows.append(indexed[(domain, group, "baseline", 0)])
            portfolio_rows.append(indexed.get((domain, group, selected, 0), indexed[(domain, group, "baseline", 0)]))
            global_rows.append(indexed.get((domain, group, global_action, 0), indexed[(domain, group, "baseline", 0)]))

    def aggregate(selected_rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
        return {
            "groups": len(selected_rows),
            "quality_pass_rate": mean(
                bool(row["metrics"]["quality_contract_pass"]) for row in selected_rows
            ),
            **{
                f"mean_{endpoint}": mean(_metric(row, endpoint) for row in selected_rows)
                for endpoint in ENDPOINTS
            },
        }

    baseline_aggregate = aggregate(baseline_rows)
    family_aggregate = aggregate(portfolio_rows)
    global_aggregate = aggregate(global_rows)
    return {
        "schema": "agent-compaction-multidomain-analysis/v1",
        "protocol_digest": protocol.digest,
        "policy_digest": policy.digest,
        "policy_frozen_at": policy_payload["frozen_at"],
        "statistical_contract": {
            "binary": "exact paired conservative loss bound",
            "noninferiority_margin": STATISTICAL_CONTRACT["quality_noninferiority_margin"],
            "confidence": STATISTICAL_CONTRACT["per_domain_confidence"],
            "bootstrap_resamples": STATISTICAL_CONTRACT["bootstrap_resamples"],
            "secondary_correction": "Holm within domain/action endpoint family",
        },
        "per_domain": per_domain,
        "portfolio_comparison": {
            "selected_family_actions": {
                domain: policy.select(protocol.family_key(domain)).selected_action
                for domain in sorted(protocol.group_roles)
            },
            "best_global_fixed_action": global_action,
            "baseline": baseline_aggregate,
            "family_policy": family_aggregate,
            "global_fixed_policy": global_aggregate,
        },
        "construction_and_amortization": _amortization(
            effort,
            effort_digest,
            baseline_aggregate,
            family_aggregate,
        ),
        "quality_rows": quality_rows,
        "endpoint_rows": endpoint_rows,
        "determinism_rows": determinism_rows,
        "unavailable_test_executions": len(unavailable_rows),
        "provider_calls_executed_in_analysis": 0,
    }


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--ledger", action="append", required=True, type=Path)
    parser.add_argument("--effort", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    protocol = FrozenProtocol.load(args.protocol)
    policy_payload = json.loads(args.policy.read_text(encoding="utf-8"))
    effort, effort_digest = _load_effort(args.effort)
    ledger_records, rows = _load_ledgers(args.ledger)
    result = analyze(
        protocol,
        policy_payload,
        ledger_records,
        rows,
        effort,
        effort_digest,
    )
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "analysis.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    _write_csv(args.out / "paired_endpoints.csv", result["endpoint_rows"])
    _write_csv(args.out / "quality.csv", result["quality_rows"])
    _write_csv(args.out / "determinism.csv", result["determinism_rows"])
    print(
        json.dumps(
            {
                "protocol_digest": result["protocol_digest"],
                "portfolio_comparison": result["portfolio_comparison"],
                "outputs": [
                    "analysis.json",
                    "paired_endpoints.csv",
                    "quality.csv",
                    "determinism.csv",
                ],
            },
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
