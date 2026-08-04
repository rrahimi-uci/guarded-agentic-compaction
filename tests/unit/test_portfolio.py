"""Risk-bounded portfolio selection tests."""

from __future__ import annotations

import pytest

from agent_compaction.portfolio import (
    OptimizationAction,
    PortfolioObservation,
    SelectionConfig,
    select_portfolio_action,
)


def _observation(
    group: int,
    action: str,
    *,
    quality: bool = True,
    ratio: float = 0.5,
    compatibility: str = "manifest-a",
) -> PortfolioObservation:
    baseline = {
        "estimated_cost_usd": 10.0,
        "wall_latency_ms": 10.0,
        "total_tokens": 10.0,
        "tool_calls": 10.0,
    }
    return PortfolioObservation(
        group_id=f"g{group}",
        action=action,
        baseline_quality=True,
        candidate_quality=quality,
        baseline_metrics=baseline,
        candidate_metrics={name: value * ratio for name, value in baseline.items()},
        compatibility_key=compatibility,
    )


def test_selects_best_admitted_action_and_requires_macro_review() -> None:
    observations = [
        *[_observation(i, "compile", ratio=0.65) for i in range(80)],
        *[_observation(i, "macro", ratio=0.40) for i in range(80)],
    ]
    decision = select_portfolio_action(observations)
    assert decision.selected_action == OptimizationAction.MACRO.value
    assert decision.requires_review is True
    assert all(item.admitted for item in decision.evidence)


def test_quality_failure_can_reject_faster_candidate() -> None:
    observations = [
        *[_observation(i, "compile", quality=i >= 8, ratio=0.2) for i in range(80)],
        *[_observation(i, "macro", ratio=0.5) for i in range(80)],
    ]
    decision = select_portfolio_action(observations)
    assert decision.selected_action == "macro"
    compiler = next(item for item in decision.evidence if item.action == "compile")
    assert compiler.admitted is False
    assert any(reason.startswith("quality_risk:") for reason in compiler.rejection_reasons)


def test_baseline_failure_does_not_excuse_candidate_failure() -> None:
    observation = _observation(0, "compile", quality=False)
    object.__setattr__(observation, "baseline_quality", False)
    assert observation.quality_violation is True


def test_no_measured_candidate_means_fail_closed_baseline() -> None:
    decision = select_portfolio_action([])
    assert decision.abstained
    assert decision.selected_action == "baseline"
    assert not decision.permits("")


def test_insufficient_support_and_negative_utility_abstain() -> None:
    observations = [_observation(i, "cache", ratio=1.1) for i in range(10)]
    decision = select_portfolio_action(observations)
    assert decision.abstained
    evidence = decision.evidence[0]
    assert evidence.regret_events == 10
    assert any(reason.startswith("support:") for reason in evidence.rejection_reasons)


def test_repeated_executions_are_not_counted_as_independent_groups() -> None:
    observations = [_observation(0, "compile") for _ in range(50)]
    decision = select_portfolio_action(
        observations,
        config=SelectionConfig(minimum_groups=2, quality_risk_limit=0.99, regret_risk_limit=0.99),
    )
    assert decision.abstained
    assert decision.evidence[0].support_groups == 1


def test_manifest_drift_rejects_candidate_and_runtime_permission() -> None:
    observations = [_observation(i, "compile") for i in range(80)]
    decision = select_portfolio_action(
        observations,
        config=SelectionConfig(expected_compatibility_key="manifest-b"),
    )
    assert decision.abstained
    assert not decision.permits("manifest-b")
    assert not decision.permits("manifest-a")


def test_reviewed_macro_requires_explicit_runtime_approval() -> None:
    observations = [_observation(i, "macro") for i in range(80)]
    decision = select_portfolio_action(observations)
    assert decision.requires_review
    assert not decision.permits("manifest-a")
    assert decision.permits("manifest-a", review_approved=True)


@pytest.mark.parametrize("invalid", [{}, {"estimated_cost_usd": float("nan")}])
def test_incomplete_or_invalid_objective_metrics_reject_action(invalid: dict[str, float]) -> None:
    observations = [_observation(i, "compile") for i in range(80)]
    broken = observations[0]
    object.__setattr__(broken, "candidate_metrics", invalid)
    decision = select_portfolio_action(observations)
    assert decision.abstained
    assert "metrics:missing_or_invalid" in decision.evidence[0].rejection_reasons


def test_invalid_objective_weights_raise() -> None:
    observation = _observation(0, "compile")
    bad = SelectionConfig()
    object.__setattr__(bad.weights, "cost", -1.0)
    with pytest.raises(ValueError, match="non-negative"):
        select_portfolio_action([observation], config=bad)
