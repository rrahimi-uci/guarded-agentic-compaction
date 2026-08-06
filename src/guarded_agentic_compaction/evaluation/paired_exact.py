"""Exact one-sided paired inference for binary task contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

from ..grc.calibrate import clopper_pearson_upper

__all__ = ["BinaryPair", "ExactPairedNonInferiority", "exact_paired_binary_noninferiority"]


@dataclass(frozen=True, slots=True)
class BinaryPair:
    """One independent scenario group's baseline/candidate contract outcomes."""

    group_id: str
    baseline_success: bool
    candidate_success: bool

    def __post_init__(self) -> None:
        if not isinstance(self.group_id, str) or not self.group_id.strip():
            raise ValueError("group_id must be a non-empty string")
        if type(self.baseline_success) is not bool or type(self.candidate_success) is not bool:
            raise ValueError("binary outcomes must be booleans")


@dataclass(frozen=True, slots=True)
class ExactPairedNonInferiority:
    n_groups: int
    baseline_successes: int
    candidate_successes: int
    candidate_losses: int
    candidate_gains: int
    point_difference: float
    lower_bound: float
    loss_rate_upper: float
    margin: float
    confidence: float
    passed: bool
    method: str = "paired_loss_clopper_pearson"

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def exact_paired_binary_noninferiority(
    pairs: Sequence[BinaryPair],
    *,
    margin: float,
    confidence: float = 0.99,
) -> ExactPairedNonInferiority:
    """Conservative exact lower bound for candidate minus baseline success.

    A candidate can be worse only on groups where the baseline succeeds and the
    candidate fails.  If that loss probability is :math:`p_L`, then the paired
    difference satisfies ``p_gain - p_loss >= -p_L``.  A one-sided exact upper
    bound for ``p_L`` therefore yields a valid one-sided lower bound for the paired
    quality difference without treating repeat runs as independent observations.

    Gains are reported but deliberately do not tighten the safety certificate.
    Absolute candidate failures remain governed by the portfolio quality-risk gate.
    """

    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be between zero and one")
    if not 0.0 <= margin < 1.0:
        raise ValueError("margin must be in [0, 1)")
    if not pairs:
        raise ValueError("at least one independent pair is required")
    group_ids = [pair.group_id for pair in pairs]
    if len(set(group_ids)) != len(group_ids):
        raise ValueError("duplicate group_id values would create pseudo-replication")

    n = len(pairs)
    baseline_successes = sum(pair.baseline_success for pair in pairs)
    candidate_successes = sum(pair.candidate_success for pair in pairs)
    losses = sum(pair.baseline_success and not pair.candidate_success for pair in pairs)
    gains = sum(not pair.baseline_success and pair.candidate_success for pair in pairs)
    point = (candidate_successes - baseline_successes) / n
    loss_upper = clopper_pearson_upper(losses, n, confidence)
    lower = -loss_upper
    return ExactPairedNonInferiority(
        n_groups=n,
        baseline_successes=baseline_successes,
        candidate_successes=candidate_successes,
        candidate_losses=losses,
        candidate_gains=gains,
        point_difference=point,
        lower_bound=lower,
        loss_rate_upper=loss_upper,
        margin=margin,
        confidence=confidence,
        passed=lower >= -margin,
    )
