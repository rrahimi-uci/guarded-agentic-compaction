from __future__ import annotations

import pytest

from guarded_agentic_compaction.benchmarking import build_role_schedule, freeze_protocol, schedule_summary
from guarded_agentic_compaction.benchmarking import ProtocolError
from guarded_agentic_compaction.evaluation import BenchmarkCase, BenchmarkRole


def _cases(n: int = 12) -> tuple[BenchmarkCase, ...]:
    return tuple(
        BenchmarkCase(
            case_id=f"c-{i}", group_id=f"g-{i}", domain="d",
            source_snapshot="sha256:" + "a" * 64,
            inputs={"i": i}, metadata={"lineage_ids": [f"l-{i}"]},
        )
        for i in range(n)
    )


def _protocol(cases: tuple[BenchmarkCase, ...], seed: int = 7):
    return freeze_protocol(
        study_id="s", seed=seed, config_digest="config",
        source_digests={"d": "sha256:" + "a" * 64},
        cases_by_domain={"d": cases},
        role_counts={BenchmarkRole.TEST: 6}, reserve_groups=6,
    )


def test_counterbalanced_schedule_is_deterministic_complete_and_bounded() -> None:
    cases = _cases(); protocol = _protocol(cases)
    schedule = build_role_schedule(protocol, {"d": cases}, role="test", repeats=3)
    assert schedule == build_role_schedule(protocol, {"d": cases}, role="test", repeats=3)
    assert len(schedule) == 6 * 3 * 3
    assert len({(x.case_id, x.action, x.repeat) for x in schedule}) == len(schedule)
    summary = schedule_summary(schedule, max_model_requests_per_execution=8, retries=1)
    assert summary["maximum_provider_requests"] == len(schedule) * 16


def test_schedule_cycles_all_six_three_action_orders() -> None:
    cases = _cases(); protocol = _protocol(cases, seed=9)
    schedule = build_role_schedule(protocol, {"d": cases}, role="test")
    orders: dict[str, list[tuple[int, str]]] = {}
    for item in schedule:
        orders.setdefault(item.group_id, []).append((item.stage, item.action))
    observed = {tuple(action for _, action in sorted(value)) for value in orders.values()}
    assert len(observed) == 6


def test_schedule_rejects_case_payload_drift_after_freeze() -> None:
    cases = _cases()
    protocol = _protocol(cases)
    drifted = (
        BenchmarkCase(
            case_id=cases[0].case_id,
            group_id=cases[0].group_id,
            domain=cases[0].domain,
            source_snapshot=cases[0].source_snapshot,
            inputs={"i": "changed"},
            metadata=cases[0].metadata,
        ),
        *cases[1:],
    )
    with pytest.raises(ProtocolError, match="case pool drifted"):
        build_role_schedule(protocol, {"d": drifted}, role="test")
