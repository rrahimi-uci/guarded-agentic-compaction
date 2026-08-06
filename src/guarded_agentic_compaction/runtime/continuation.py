"""Fail-closed validation and recovery for post-compaction model continuations.

The compiled program verifier proves properties of the deterministic tool region.  It
cannot, by itself, prove that a later model response faithfully uses those observations.
This module provides the separate boundary needed for that second claim:

``candidate -> validate -> accept | checked render | validated baseline | reject``.

The validator and optional renderer are application supplied because factuality and
output ownership are task contracts, not properties a generic optimizer can infer.  No
path emits an unvalidated recovery, and exception text is not serialized into telemetry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Sequence

__all__ = [
    "BaselineContinuation",
    "ContinuationContract",
    "ContinuationDecision",
    "ContinuationEvidence",
    "ContinuationGuard",
    "ContinuationOutcome",
    "ContinuationRenderer",
    "ContinuationTelemetry",
]


@dataclass(frozen=True, slots=True)
class ContinuationEvidence:
    """Evidence visible to an application-defined continuation contract."""

    entry_state: Mapping[str, Any]
    observations: tuple[Any, ...] = ()
    artifact_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


ContinuationContract = Callable[[Any, ContinuationEvidence], Sequence[str]]
ContinuationRenderer = Callable[[ContinuationEvidence], Any]
BaselineContinuation = Callable[[ContinuationEvidence], Any]


class ContinuationOutcome(str, Enum):
    """Terminal result of one continuation check."""

    ACCEPTED = "ACCEPTED"
    RENDERED = "RENDERED"
    BASELINE = "BASELINE"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class ContinuationDecision:
    """Validated output or an explicit refusal to emit one."""

    outcome: ContinuationOutcome
    output: Any = None
    candidate_violations: tuple[str, ...] = ()
    recovery_violations: tuple[str, ...] = ()

    @property
    def accepted(self) -> bool:
        return self.outcome is not ContinuationOutcome.REJECTED

    @property
    def recovered(self) -> bool:
        return self.outcome in {ContinuationOutcome.RENDERED, ContinuationOutcome.BASELINE}

    @property
    def record(self) -> dict[str, Any]:
        """Secret-safe telemetry; model output and exception messages are excluded."""

        return {
            "outcome": self.outcome.value,
            "accepted": self.accepted,
            "recovered": self.recovered,
            "candidate_violations": list(self.candidate_violations[:8]),
            "recovery_violations": list(self.recovery_violations[:8]),
        }


@dataclass(slots=True)
class ContinuationTelemetry:
    checks: int = 0
    accepted: int = 0
    rendered: int = 0
    baseline: int = 0
    rejected: int = 0
    validator_errors: int = 0
    renderer_errors: int = 0
    baseline_errors: int = 0
    violations: dict[str, int] = field(default_factory=dict)

    def bump_violation(self, reason: str) -> None:
        key = reason.split(":", 1)[0][:80] or "unspecified"
        self.violations[key] = self.violations.get(key, 0) + 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "checks": self.checks,
            "accepted": self.accepted,
            "rendered": self.rendered,
            "baseline": self.baseline,
            "rejected": self.rejected,
            "validator_errors": self.validator_errors,
            "renderer_errors": self.renderer_errors,
            "baseline_errors": self.baseline_errors,
            "violations": dict(sorted(self.violations.items())),
        }


@dataclass(slots=True)
class ContinuationGuard:
    """Validate a candidate and recover only through another validated path.

    Recovery order is deterministic: a checked renderer is attempted first, followed by
    a baseline continuation.  A renderer is appropriate when the output can be derived
    mechanically from observations; the baseline remains useful for open-ended tasks.
    Both outputs are re-checked by the same contract before release.
    """

    contract: ContinuationContract
    renderer: ContinuationRenderer | None = None
    telemetry: ContinuationTelemetry = field(default_factory=ContinuationTelemetry)

    def decide(
        self,
        candidate: Any,
        evidence: ContinuationEvidence,
        *,
        baseline: BaselineContinuation | None = None,
    ) -> ContinuationDecision:
        self.telemetry.checks += 1
        candidate_bad = self._validate(candidate, evidence)
        if not candidate_bad:
            self.telemetry.accepted += 1
            return ContinuationDecision(ContinuationOutcome.ACCEPTED, output=candidate)
        for reason in candidate_bad:
            self.telemetry.bump_violation(reason)

        recovery_bad: tuple[str, ...] = ()
        if self.renderer is not None:
            try:
                rendered = self.renderer(evidence)
            except Exception as exc:
                self.telemetry.renderer_errors += 1
                recovery_bad = (f"renderer_error:{type(exc).__name__}",)
            else:
                recovery_bad = self._validate(rendered, evidence)
                if not recovery_bad:
                    self.telemetry.rendered += 1
                    return ContinuationDecision(
                        ContinuationOutcome.RENDERED,
                        output=rendered,
                        candidate_violations=candidate_bad,
                    )

        if baseline is not None:
            try:
                baseline_output = baseline(evidence)
            except Exception as exc:
                self.telemetry.baseline_errors += 1
                recovery_bad = recovery_bad + (f"baseline_error:{type(exc).__name__}",)
            else:
                baseline_bad = self._validate(baseline_output, evidence)
                if not baseline_bad:
                    self.telemetry.baseline += 1
                    return ContinuationDecision(
                        ContinuationOutcome.BASELINE,
                        output=baseline_output,
                        candidate_violations=candidate_bad,
                        recovery_violations=recovery_bad,
                    )
                recovery_bad = recovery_bad + baseline_bad

        self.telemetry.rejected += 1
        return ContinuationDecision(
            ContinuationOutcome.REJECTED,
            candidate_violations=candidate_bad,
            recovery_violations=recovery_bad,
        )

    def _validate(self, output: Any, evidence: ContinuationEvidence) -> tuple[str, ...]:
        try:
            reasons = self.contract(output, evidence)
        except Exception as exc:
            self.telemetry.validator_errors += 1
            return (f"validator_error:{type(exc).__name__}",)
        if isinstance(reasons, str):
            reasons = (reasons,)
        return tuple(str(reason)[:160] for reason in reasons if str(reason))
