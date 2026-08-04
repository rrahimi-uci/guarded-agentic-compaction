"""Multiplicity and zero-event sample helpers for family portfolio studies."""

from __future__ import annotations

from dataclasses import dataclass

from ..grc.calibrate import clopper_pearson_upper

__all__ = [
    "RiskAllocation",
    "bonferroni_family_confidence",
    "portfolio_risk_upper",
    "required_portfolio_groups",
]


@dataclass(frozen=True, slots=True)
class RiskAllocation:
    overall_confidence: float
    family_confidence: float
    n_families: int
    n_actions: int
    n_bounds: int
    per_bound_confidence: float

    def as_dict(self) -> dict[str, float | int]:
        return {
            "overall_confidence": self.overall_confidence,
            "family_confidence": self.family_confidence,
            "n_families": self.n_families,
            "n_actions": self.n_actions,
            "n_bounds": self.n_bounds,
            "per_bound_confidence": self.per_bound_confidence,
        }


def _probability(value: float, *, name: str) -> float:
    if not 0.0 < value < 1.0:
        raise ValueError(f"{name} must be between zero and one")
    return float(value)


def bonferroni_family_confidence(
    overall_confidence: float,
    *,
    n_families: int,
    minimum_family_confidence: float | None = None,
) -> float:
    """Per-family confidence controlling the union error across families."""

    overall = _probability(overall_confidence, name="overall_confidence")
    if n_families < 1:
        raise ValueError("n_families must be positive")
    family = 1.0 - (1.0 - overall) / n_families
    if minimum_family_confidence is not None:
        minimum = _probability(
            minimum_family_confidence, name="minimum_family_confidence"
        )
        family = max(family, minimum)
    return family


def _per_bound_confidence(
    selection_confidence: float,
    *,
    n_actions: int,
    n_bounds: int,
) -> float:
    selection = _probability(selection_confidence, name="selection_confidence")
    if n_actions < 1 or n_bounds < 1:
        raise ValueError("n_actions and n_bounds must be positive")
    return 1.0 - (1.0 - selection) / (n_actions * n_bounds)


def portfolio_risk_upper(
    events: int,
    groups: int,
    *,
    selection_confidence: float,
    n_actions: int,
    n_bounds: int = 2,
) -> float:
    """Recompute the exact bound used by ``select_portfolio_action``."""

    if type(events) is not int or type(groups) is not int:
        raise ValueError("events and groups must be integers")
    if groups < 1 or events < 0 or events > groups:
        raise ValueError("expected 0 <= events <= groups with groups positive")
    bound_confidence = _per_bound_confidence(
        selection_confidence, n_actions=n_actions, n_bounds=n_bounds
    )
    return clopper_pearson_upper(events, groups, bound_confidence)


def required_portfolio_groups(
    *,
    risk_limit: float,
    selection_confidence: float,
    n_actions: int,
    n_bounds: int = 2,
    max_groups: int = 1_000_000,
) -> int:
    """Smallest zero-event support whose exact upper bound clears ``risk_limit``."""

    limit = _probability(risk_limit, name="risk_limit")
    if max_groups < 1:
        raise ValueError("max_groups must be positive")
    for groups in range(1, max_groups + 1):
        if portfolio_risk_upper(
            0,
            groups,
            selection_confidence=selection_confidence,
            n_actions=n_actions,
            n_bounds=n_bounds,
        ) <= limit:
            return groups
    raise ValueError("max_groups is too small for the requested risk certificate")
