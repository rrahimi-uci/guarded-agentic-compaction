"""Exact-risk selector over competing agent optimization mechanisms."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Mapping, Sequence

from ..grc.calibrate import clopper_pearson_upper
from .model import (
    CandidateEvidence,
    DeploymentMode,
    OptimizationAction,
    PortfolioDecision,
    PortfolioObservation,
    SelectionConfig,
)

__all__ = ["select_portfolio_action"]


def _action_name(value: str | OptimizationAction) -> str:
    return value.value if isinstance(value, OptimizationAction) else str(value)


def _deployment_mode(
    action: str,
    deployment_modes: Mapping[str, DeploymentMode] | None,
) -> DeploymentMode:
    if deployment_modes and action in deployment_modes:
        return deployment_modes[action]
    if action == OptimizationAction.MACRO.value:
        return DeploymentMode.HUMAN_REVIEW
    return DeploymentMode.AUTOMATIC


def select_portfolio_action(
    observations: Sequence[PortfolioObservation],
    *,
    config: SelectionConfig | None = None,
    deployment_modes: Mapping[str, DeploymentMode] | None = None,
) -> PortfolioDecision:
    """Select the highest-utility action that passes both exact risk gates.

    Candidate comparisons are grouped by ``group_id``.  Duplicate observations for
    one action/group are averaged for utility and combined conservatively for risk:
    any quality failure is a group violation and a group is a regret event when its
    mean utility does not exceed ``minimum_utility``.

    The confidence error budget is Bonferroni-split across observed non-baseline
    actions and the two gates.  This controls selection multiplicity without treating
    repeated executions of one workflow group as independent evidence.
    """

    cfg = config or SelectionConfig()
    cfg.validate()
    by_action_group: dict[str, dict[str, list[PortfolioObservation]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for observation in observations:
        action = _action_name(observation.action)
        if action == OptimizationAction.BASELINE.value:
            continue
        by_action_group[action][observation.group_id].append(observation)

    n_actions = max(1, len(by_action_group))
    familywise_error = 1.0 - cfg.confidence
    per_bound_error = familywise_error / (2 * n_actions)
    bound_confidence = 1.0 - per_bound_error
    evidence: list[CandidateEvidence] = []

    for action in sorted(by_action_group):
        groups = by_action_group[action]
        utilities: list[float] = []
        reductions: dict[str, list[float]] = defaultdict(list)
        quality_violations = 0
        regret_events = 0
        compatibility_keys: set[str] = set()
        invalid_metrics = False
        for items in groups.values():
            group_invalid = False
            try:
                group_utilities = [item.utility(cfg.weights) for item in items]
                group_utility = mean(group_utilities)
                utilities.append(group_utility)
                group_regret = group_utility <= cfg.minimum_utility
            except (TypeError, ValueError):
                # Incomplete, non-finite, or negative measurements cannot justify an
                # optimization.  Count the group conservatively and reject the action
                # explicitly below rather than silently changing the objective.
                invalid_metrics = True
                group_invalid = True
                group_regret = True
            if group_regret:
                regret_events += 1
            if group_invalid or any(item.quality_violation for item in items):
                quality_violations += 1
            for item in items:
                if item.compatibility_key:
                    compatibility_keys.add(item.compatibility_key)
                try:
                    # Retain every valid measured reduction for auditability while
                    # utility itself remains strict over the complete declared objective.
                    for name, value in item.reductions().items():
                        reductions[name].append(value)
                except (TypeError, ValueError):
                    invalid_metrics = True

        support = len(groups)
        quality_upper = clopper_pearson_upper(
            quality_violations, support, bound_confidence
        )
        regret_upper = clopper_pearson_upper(regret_events, support, bound_confidence)
        compatible = len(compatibility_keys) <= 1
        if cfg.expected_compatibility_key:
            compatible = compatible and compatibility_keys == {cfg.expected_compatibility_key}
        reasons: list[str] = []
        if support < cfg.minimum_groups:
            reasons.append(f"support:{support}<{cfg.minimum_groups}")
        if quality_upper > cfg.quality_risk_limit:
            reasons.append(
                f"quality_risk:{quality_upper:.6f}>{cfg.quality_risk_limit:.6f}"
            )
        if regret_upper > cfg.regret_risk_limit:
            reasons.append(
                f"regret_risk:{regret_upper:.6f}>{cfg.regret_risk_limit:.6f}"
            )
        if not compatible:
            reasons.append("compatibility:mixed_or_unexpected")
        if invalid_metrics:
            reasons.append("metrics:missing_or_invalid")
        evidence.append(
            CandidateEvidence(
                action=action,
                support_groups=support,
                quality_violations=quality_violations,
                quality_risk_upper=quality_upper,
                regret_events=regret_events,
                regret_risk_upper=regret_upper,
                mean_utility=mean(utilities) if utilities else 0.0,
                mean_reductions={name: mean(values) for name, values in sorted(reductions.items())},
                compatible=compatible,
                admitted=not reasons,
                rejection_reasons=tuple(reasons),
                deployment_mode=_deployment_mode(action, deployment_modes),
            )
        )

    admitted = [item for item in evidence if item.admitted]
    if not admitted:
        return PortfolioDecision(
            selected_action=OptimizationAction.BASELINE.value,
            evidence=tuple(evidence),
            expected_compatibility_key=cfg.expected_compatibility_key,
            rationale="no measured candidate passed support, quality-risk, regret-risk, and compatibility gates",
        )
    selected = max(admitted, key=lambda item: (item.mean_utility, item.action))
    return PortfolioDecision(
        selected_action=selected.action,
        evidence=tuple(evidence),
        expected_compatibility_key=cfg.expected_compatibility_key,
        requires_review=selected.deployment_mode is DeploymentMode.HUMAN_REVIEW,
        rationale=(
            f"{selected.action} had the largest admitted mean utility "
            f"({selected.mean_utility:.6f}) under exact group-level risk bounds"
        ),
    )
