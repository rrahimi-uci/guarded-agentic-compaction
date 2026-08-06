"""Protocol freezing, leakage isolation, and provider budget tests."""

from __future__ import annotations

import json

import pytest

from guarded_agentic_compaction.benchmarking import (
    BudgetExceeded,
    FrozenProtocol,
    ProtocolError,
    ProviderBudget,
    freeze_protocol,
)
from guarded_agentic_compaction.evaluation import BenchmarkCase, BenchmarkRole


def _case(index: int, *, lineage: str | None = None) -> BenchmarkCase:
    return BenchmarkCase(
        case_id=f"case-{index}",
        group_id=f"group-{index}",
        domain="vulnerability",
        source_snapshot="sha256:" + "a" * 64,
        inputs={"record": index},
        metadata={"lineage_ids": [lineage or f"advisory-{index}"]},
    )


def test_protocol_freeze_is_deterministic_roundtrippable_and_disjoint(tmp_path) -> None:
    cases = tuple(_case(index) for index in range(12))
    kwargs = dict(
        study_id="study",
        seed=7,
        config_digest="config",
        source_digests={"vulnerability": "sha256:" + "a" * 64},
        cases_by_domain={"vulnerability": cases},
        role_counts={
            BenchmarkRole.DISCOVERY: 2,
            BenchmarkRole.DEVELOPMENT: 2,
            BenchmarkRole.ARTIFACT_CALIBRATION: 2,
            BenchmarkRole.PORTFOLIO_CALIBRATION: 2,
            BenchmarkRole.TEST: 2,
        },
        reserve_groups=2,
        model="gpt-test",
        execution_contract={"pricing_digest": "price-a", "service_tier": "default"},
    )
    first = freeze_protocol(**kwargs)
    second = freeze_protocol(**kwargs)
    assert first.digest == second.digest
    reordered = freeze_protocol(
        **{
            **kwargs,
            "role_counts": dict(reversed(list(kwargs["role_counts"].items()))),
        }
    )
    assert reordered.digest == first.digest
    assert reordered.group_roles == first.group_roles
    roles = first.group_roles["vulnerability"]
    assert len(roles) == 12
    assert sum(role is BenchmarkRole.TEST for role in roles.values()) == 2
    assert sum(role is BenchmarkRole.RESERVE for role in roles.values()) == 2
    destination = first.write(tmp_path / "frozen.json")
    restored = FrozenProtocol.load(destination)
    assert restored.digest == first.digest
    assert restored.execution_contract == {
        "pricing_digest": "price-a",
        "service_tier": "default",
    }
    assert restored.case_pool_digests == first.case_pool_digests
    changed_cases = (*cases[:-1], _case(11))
    changed_cases = (
        *changed_cases[:-1],
        BenchmarkCase(
            case_id="case-11",
            group_id="group-11",
            domain="vulnerability",
            source_snapshot="sha256:" + "a" * 64,
            inputs={"record": "post-freeze-drift"},
            metadata={"lineage_ids": ["advisory-11"]},
        ),
    )
    drifted = freeze_protocol(**{**kwargs, "cases_by_domain": {"vulnerability": changed_cases}})
    assert drifted.case_pool_digests != first.case_pool_digests
    assert drifted.digest != first.digest
    assert restored.study_for("vulnerability").metadata["protocol_digest"] == first.digest

    raw = json.loads(destination.read_text())
    raw["seed"] = 8
    with pytest.raises(ProtocolError, match="digest mismatch"):
        FrozenProtocol.from_dict(raw)


def test_protocol_rejects_lineage_crossing_roles() -> None:
    cases = tuple(_case(index, lineage="same-advisory") for index in range(6))
    with pytest.raises(ProtocolError, match="crosses"):
        freeze_protocol(
            study_id="study",
            seed=1,
            config_digest="config",
            source_digests={"vulnerability": "source"},
            cases_by_domain={"vulnerability": cases},
            role_counts={BenchmarkRole.DISCOVERY: 2, BenchmarkRole.TEST: 2},
            reserve_groups=2,
        )


def test_provider_budget_requires_reservation_and_never_overruns_cap() -> None:
    budget = ProviderBudget(1.0)
    assert budget.reserve("case-1", 0.4).estimated_usd == 0.4
    assert budget.reserve("case-1", 0.4).estimated_usd == 0.4
    with pytest.raises(BudgetExceeded, match="different estimate"):
        budget.reserve("case-1", 0.3)
    budget.reconcile("case-1", 0.5)
    budget.reserve("case-2", 0.5)
    assert budget.remaining_usd == pytest.approx(0.0)
    with pytest.raises(BudgetExceeded, match="exceeded"):
        budget.reserve("case-3", 0.01)
    with pytest.raises(BudgetExceeded, match="no prior reservation"):
        budget.reconcile("missing", 0.1)
