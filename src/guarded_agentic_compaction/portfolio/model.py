"""Typed contracts for risk-bounded optimization portfolio selection.

The portfolio layer does not synthesize or execute transformations.  It compares
already measured candidates (cache, compiler, macro, or third-party strategies)
against the unchanged agent and returns either an admitted action or the baseline.
This separation keeps the statistical decision framework-neutral and makes missing
evidence an explicit abstention rather than an implicit estimate.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Mapping

__all__ = [
    "OptimizationAction",
    "DeploymentMode",
    "ObjectiveWeights",
    "PortfolioObservation",
    "CandidateEvidence",
    "PortfolioDecision",
    "SelectionConfig",
]


class OptimizationAction(str, Enum):
    """Built-in action names; applications may use additional string actions."""

    BASELINE = "baseline"
    CACHE = "cache"
    COMPILE = "compile"
    MACRO = "macro"


class DeploymentMode(str, Enum):
    """How an admitted action may leave the optimization pipeline."""

    AUTOMATIC = "automatic"
    HUMAN_REVIEW = "human_review"


@dataclass(frozen=True, slots=True)
class ObjectiveWeights:
    """Weights over dimensionless paired reductions.

    For each metric, reduction is ``1 - candidate / baseline``.  Positive values
    are improvements.  Weights are normalized at evaluation time, so callers may
    use any non-negative scale.  An objective with no positive weight is rejected.
    """

    cost: float = 0.35
    latency: float = 0.25
    tokens: float = 0.20
    tool_calls: float = 0.20

    def normalized(self) -> dict[str, float]:
        raw = {
            "estimated_cost_usd": self.cost,
            "wall_latency_ms": self.latency,
            "total_tokens": self.tokens,
            "tool_calls": self.tool_calls,
        }
        if any(value < 0 for value in raw.values()):
            raise ValueError("objective weights must be non-negative")
        total = sum(raw.values())
        if total <= 0:
            raise ValueError("at least one objective weight must be positive")
        return {name: value / total for name, value in raw.items() if value > 0}


@dataclass(frozen=True, slots=True)
class PortfolioObservation:
    """One independent workflow-group comparison against the baseline."""

    group_id: str
    action: str
    baseline_quality: bool
    candidate_quality: bool
    baseline_metrics: Mapping[str, float]
    candidate_metrics: Mapping[str, float]
    compatibility_key: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def reductions(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for name, baseline in self.baseline_metrics.items():
            candidate = self.candidate_metrics.get(name)
            if candidate is None:
                continue
            baseline_value = float(baseline)
            candidate_value = float(candidate)
            if not isfinite(baseline_value) or not isfinite(candidate_value) or candidate_value < 0:
                raise ValueError(f"observation {self.group_id!r} has invalid metric {name!r}")
            if baseline_value <= 0:
                continue
            out[name] = 1.0 - candidate_value / baseline_value
        return out

    def objective_reductions(self, weights: ObjectiveWeights) -> dict[str, float]:
        """Return every predeclared objective or reject incomplete evidence.

        Renormalizing over whichever metrics happen to be present would make actions
        incomparable and reward missing measurements.  Portfolio admission therefore
        requires all positively weighted dimensions for every paired observation.
        """

        required = weights.normalized()
        missing = sorted(
            name
            for name in required
            if name not in self.baseline_metrics or name not in self.candidate_metrics
        )
        if missing:
            raise ValueError(
                f"observation {self.group_id!r} is missing objective metrics: {', '.join(missing)}"
            )
        reductions: dict[str, float] = {}
        for name in required:
            baseline = float(self.baseline_metrics[name])
            candidate = float(self.candidate_metrics[name])
            if (
                not isfinite(baseline)
                or not isfinite(candidate)
                or baseline <= 0
                or candidate < 0
            ):
                raise ValueError(
                    f"observation {self.group_id!r} has invalid objective metric {name!r}"
                )
            reductions[name] = 1.0 - candidate / baseline
        return reductions

    def utility(self, weights: ObjectiveWeights) -> float:
        reductions = self.objective_reductions(weights)
        normalized = weights.normalized()
        return sum(reductions[name] * weight for name, weight in normalized.items())

    @property
    def quality_violation(self) -> bool:
        """A candidate violates quality whenever its task contract fails.

        ``baseline_quality`` remains available for paired non-inferiority analyses,
        but a failing baseline must never excuse a failing optimization at admission.
        """

        return not self.candidate_quality


@dataclass(frozen=True, slots=True)
class SelectionConfig:
    """Predeclared portfolio admission and multiplicity controls."""

    quality_risk_limit: float = 0.10
    regret_risk_limit: float = 0.10
    confidence: float = 0.95
    minimum_groups: int = 20
    minimum_utility: float = 0.0
    weights: ObjectiveWeights = field(default_factory=ObjectiveWeights)
    expected_compatibility_key: str = ""

    def validate(self) -> None:
        for name, value in (
            ("quality_risk_limit", self.quality_risk_limit),
            ("regret_risk_limit", self.regret_risk_limit),
            ("confidence", self.confidence),
        ):
            if not 0 < value < 1:
                raise ValueError(f"{name} must be between zero and one")
        if self.minimum_groups < 1:
            raise ValueError("minimum_groups must be positive")
        self.weights.normalized()


@dataclass(frozen=True, slots=True)
class CandidateEvidence:
    """Auditable evidence used for one portfolio action."""

    action: str
    support_groups: int
    quality_violations: int
    quality_risk_upper: float
    regret_events: int
    regret_risk_upper: float
    mean_utility: float
    mean_reductions: Mapping[str, float]
    compatible: bool
    admitted: bool
    rejection_reasons: tuple[str, ...] = ()
    deployment_mode: DeploymentMode = DeploymentMode.AUTOMATIC

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["deployment_mode"] = self.deployment_mode.value
        payload["mean_reductions"] = dict(self.mean_reductions)
        payload["rejection_reasons"] = list(self.rejection_reasons)
        return payload


@dataclass(frozen=True, slots=True)
class PortfolioDecision:
    """Selected action plus enough state for fail-closed runtime use."""

    selected_action: str
    evidence: tuple[CandidateEvidence, ...]
    expected_compatibility_key: str = ""
    requires_review: bool = False
    rationale: str = ""

    @property
    def abstained(self) -> bool:
        return self.selected_action == OptimizationAction.BASELINE.value

    def permits(self, compatibility_key: str, *, review_approved: bool = False) -> bool:
        """Fail closed on abstention, review omission, or manifest drift."""

        compatible = (
            not self.expected_compatibility_key
            or compatibility_key == self.expected_compatibility_key
        )
        return (
            not self.abstained
            and compatible
            and (not self.requires_review or review_approved)
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "selected_action": self.selected_action,
            "abstained": self.abstained,
            "requires_review": self.requires_review,
            "expected_compatibility_key": self.expected_compatibility_key,
            "rationale": self.rationale,
            "evidence": [item.as_dict() for item in self.evidence],
        }
