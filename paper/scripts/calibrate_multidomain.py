#!/usr/bin/env python3
"""Freeze exact-risk per-domain portfolio decisions from calibration ledgers."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[2]
for candidate in (ROOT, ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from guarded_agentic_compaction.benchmarking import (  # noqa: E402
    FrozenProtocol,
    frozen_artifact_digest,
)
from guarded_agentic_compaction.benchmarking.preflight import STATISTICAL_CONTRACT  # noqa: E402
from guarded_agentic_compaction.evaluation import (  # noqa: E402
    CanonicalMetrics,
    RunLedger,
    paired_portfolio_observation,
)
from guarded_agentic_compaction.portfolio import (  # noqa: E402
    PortfolioPolicy,
    SelectionConfig,
    bonferroni_family_confidence,
    select_portfolio_action,
)


def _records(
    paths: Sequence[Path], protocol_digest: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    unavailable: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, int]] = set()
    for path in paths:
        for record in RunLedger(path).records():
            if record.run_id != protocol_digest:
                raise ValueError("ledger run does not match the frozen protocol")
            if record.event_type not in {"execution_complete", "execution_unavailable"}:
                continue
            schedule = record.payload["schedule"]
            if schedule["role"] != "portfolio_calibration" or schedule["repeat"] != 0:
                continue
            key = (
                str(schedule["domain"]),
                str(schedule["group_id"]),
                str(schedule["action"]),
                int(schedule["repeat"]),
            )
            if key in seen:
                raise ValueError(f"duplicate calibration execution {key!r}")
            seen.add(key)
            target = rows if record.event_type == "execution_complete" else unavailable
            target.append(dict(record.payload))
    return rows, unavailable


def _paths(values: Sequence[str]) -> list[Path]:
    return [Path(value) for value in values]


def _observations(
    protocol: FrozenProtocol,
    records: Sequence[dict[str, Any]],
    domain: str,
    compatibility_key: str,
    actions: Sequence[str],
) -> list[Any]:
    rows = [row for row in records if row["schedule"]["domain"] == domain]
    indexed = {
        (row["schedule"]["group_id"], row["schedule"]["action"]): row
        for row in rows
    }
    groups = {
        group
        for group, role in protocol.group_roles[domain].items()
        if role.value == "portfolio_calibration"
    }
    if len(groups) != 75:
        raise ValueError(f"{domain} protocol does not contain 75 portfolio groups")
    observations = []
    for group in sorted(groups):
        baseline_row = indexed.get((group, "baseline"))
        if baseline_row is None:
            raise ValueError(f"{domain}:{group} has no complete baseline")
        baseline = CanonicalMetrics.from_live_mapping(baseline_row["metrics"])
        for action in actions:
            candidate_row = indexed.get((group, action))
            if candidate_row is None:
                raise ValueError(f"{domain}:{group} has no complete {action} result")
            candidate = CanonicalMetrics.from_live_mapping(candidate_row["metrics"])
            observations.append(
                paired_portfolio_observation(
                    group_id=f"{domain}:{group}" if compatibility_key.startswith("global:") else group,
                    action=action,
                    baseline=baseline,
                    candidate=candidate,
                    compatibility_key=compatibility_key,
                    metadata={"domain": domain},
                )
            )
    return observations


def _availability(
    protocol: FrozenProtocol,
    records: Sequence[dict[str, Any]],
    unavailable: Sequence[dict[str, Any]],
    domain: str,
) -> tuple[str, ...]:
    groups = {
        group
        for group, role in protocol.group_roles[domain].items()
        if role.value == "portfolio_calibration"
    }
    completed = {
        (row["schedule"]["action"], row["schedule"]["group_id"])
        for row in records
        if row["schedule"]["domain"] == domain
    }
    explicit_unavailable = {
        (row["schedule"]["action"], row["schedule"]["group_id"])
        for row in unavailable
        if row["schedule"]["domain"] == domain
    }
    if {group for action, group in completed if action == "baseline"} != groups:
        raise ValueError(f"{domain} requires 75 complete calibration baselines")
    available: list[str] = []
    for action in ("grc", "macro"):
        complete_groups = {group for candidate, group in completed if candidate == action}
        unavailable_groups = {
            group for candidate, group in explicit_unavailable if candidate == action
        }
        if complete_groups == groups and not unavailable_groups:
            available.append(action)
        elif unavailable_groups == groups and not complete_groups:
            continue
        else:
            raise ValueError(
                f"{domain}:{action} is partially complete/unavailable on calibration groups"
            )
    return tuple(available)


def calibrate(
    protocol: FrozenProtocol,
    records: Sequence[dict[str, Any]],
    unavailable: Sequence[dict[str, Any]] = (),
) -> tuple[PortfolioPolicy, Any]:
    decisions = {}
    global_observations = []
    family_confidence = bonferroni_family_confidence(
        float(STATISTICAL_CONTRACT["portfolio_overall_confidence"]),
        n_families=len(protocol.group_roles),
    )
    availability: dict[str, tuple[str, ...]] = {}
    for domain in sorted(protocol.group_roles):
        availability[domain] = _availability(
            protocol, records, unavailable, domain
        )
        observations = _observations(
            protocol,
            records,
            domain,
            protocol.family_key(domain),
            availability[domain],
        )
        config = SelectionConfig(
            quality_risk_limit=float(STATISTICAL_CONTRACT["portfolio_quality_risk_limit"]),
            regret_risk_limit=float(STATISTICAL_CONTRACT["portfolio_regret_risk_limit"]),
            confidence=family_confidence,
            minimum_groups=75,
            minimum_utility=0.0,
            expected_compatibility_key=protocol.family_key(domain),
        )
        decisions[protocol.family_key(domain)] = select_portfolio_action(
            observations, config=config
        )
    global_actions = tuple(
        sorted(
            set.intersection(
                *(set(availability[domain]) for domain in sorted(protocol.group_roles))
            )
        )
    )
    for domain in sorted(protocol.group_roles):
        global_observations.extend(
            _observations(
                protocol,
                records,
                domain,
                f"global:{protocol.digest}",
                global_actions,
            )
        )
    policy = PortfolioPolicy(
        decisions=decisions,
        registered_families=tuple(protocol.family_key(domain) for domain in sorted(protocol.group_roles)),
        overall_confidence=float(STATISTICAL_CONTRACT["portfolio_overall_confidence"]),
        manifest_digest=protocol.digest,
    )
    global_decision = select_portfolio_action(
        global_observations,
        config=SelectionConfig(
            quality_risk_limit=float(STATISTICAL_CONTRACT["portfolio_quality_risk_limit"]),
            regret_risk_limit=float(STATISTICAL_CONTRACT["portfolio_regret_risk_limit"]),
            confidence=float(STATISTICAL_CONTRACT["portfolio_overall_confidence"]),
            minimum_groups=225,
            minimum_utility=0.0,
            expected_compatibility_key=f"global:{protocol.digest}",
        ),
    )
    return policy, global_decision


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--ledger", action="append", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    protocol = FrozenProtocol.load(args.protocol)
    records, unavailable = _records(_paths(args.ledger), protocol.digest)
    action_locks = {
        str(row.get("action_lock_digest", ""))
        for row in [*records, *unavailable]
        if str(row.get("action_lock_digest", ""))
    }
    if len(action_locks) != 1:
        raise ValueError("portfolio calibration records do not share one frozen action lock")
    action_lock_digest = next(iter(action_locks))
    action_digests: dict[str, dict[str, str]] = {}
    for domain in sorted(protocol.group_roles):
        action_digests[domain] = {}
        for action in ("baseline", "grc", "macro"):
            values = {
                str(row.get("action_spec", {}).get("action_digest", ""))
                for row in records
                if row["schedule"]["domain"] == domain
                and row["schedule"]["action"] == action
            }
            values.discard("")
            if len(values) > 1:
                raise ValueError(f"{domain}:{action} action identity drifted during calibration")
            if values:
                action_digests[domain][action] = next(iter(values))
    policy, global_decision = calibrate(protocol, records, unavailable)
    frozen_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    output = {
        "schema": "agent-compaction-frozen-portfolio/v1",
        "frozen_at": frozen_at,
        "protocol_digest": protocol.digest,
        "policy_digest": policy.digest,
        "action_lock_digest": action_lock_digest,
        "action_digests": action_digests,
        "policy": policy.as_dict(),
        "best_global_fixed_decision": global_decision.as_dict(),
        "global_fixed_eligible_actions": sorted(
            set.intersection(
                *(
                    set(_availability(protocol, records, unavailable, domain))
                    for domain in sorted(protocol.group_roles)
                )
            )
        ),
        "risk_allocation": {
            "overall_family_policy_confidence": STATISTICAL_CONTRACT["portfolio_overall_confidence"],
            "registered_families": len(protocol.group_roles),
            "per_family_confidence": bonferroni_family_confidence(
                float(STATISTICAL_CONTRACT["portfolio_overall_confidence"]),
                n_families=len(protocol.group_roles),
            ),
            "actions_per_family": 2,
            "bounds_per_action": 2,
        },
        "unavailable_actions_by_domain": {
            domain: sorted(
                {
                    row["schedule"]["action"]
                    for row in unavailable
                    if row["schedule"]["domain"] == domain
                }
            )
            for domain in sorted(protocol.group_roles)
        },
    }
    output["portfolio_artifact_digest"] = frozen_artifact_digest(
        output, digest_field="portfolio_artifact_digest"
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
