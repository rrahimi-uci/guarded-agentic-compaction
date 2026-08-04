"""Fail-closed family policy over already calibrated portfolio decisions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from .model import (
    CandidateEvidence,
    DeploymentMode,
    OptimizationAction,
    PortfolioDecision,
)

__all__ = ["PortfolioPolicy"]


def _required_bool(value: Any, *, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a boolean")
    return value


def _baseline(reason: str) -> PortfolioDecision:
    return PortfolioDecision(
        selected_action=OptimizationAction.BASELINE.value,
        evidence=(),
        rationale=reason,
    )


@dataclass(frozen=True, slots=True)
class PortfolioPolicy:
    """One frozen decision per registered family; unknown inputs always abstain."""

    decisions: Mapping[str, PortfolioDecision]
    registered_families: tuple[str, ...]
    overall_confidence: float
    manifest_digest: str

    def __post_init__(self) -> None:
        families = tuple(self.registered_families)
        if not families or any(not item.strip() for item in families):
            raise ValueError("registered_families must contain non-empty names")
        if len(set(families)) != len(families):
            raise ValueError("registered_families must be unique")
        decisions = dict(self.decisions)
        if set(decisions) != set(families):
            missing = sorted(set(families) - set(decisions))
            extra = sorted(set(decisions) - set(families))
            raise ValueError(f"policy decision families mismatch; missing={missing}, extra={extra}")
        if not 0.0 < self.overall_confidence < 1.0:
            raise ValueError("overall_confidence must be between zero and one")
        if not self.manifest_digest.strip():
            raise ValueError("manifest_digest must not be empty")
        for family, decision in decisions.items():
            if not isinstance(decision, PortfolioDecision):
                raise ValueError(f"decision {family!r} must be a PortfolioDecision")
            if decision.abstained:
                continue
            admitted = [
                item
                for item in decision.evidence
                if item.action == decision.selected_action and item.admitted
            ]
            if len(admitted) != 1:
                raise ValueError(
                    f"decision {family!r} selected an action without one admitted certificate"
                )
            if (
                admitted[0].deployment_mode is DeploymentMode.HUMAN_REVIEW
                and not decision.requires_review
            ):
                raise ValueError(
                    f"decision {family!r} omitted the selected action review requirement"
                )
        object.__setattr__(self, "registered_families", families)
        object.__setattr__(self, "decisions", MappingProxyType(decisions))

    def select(self, family_key: str) -> PortfolioDecision:
        if family_key not in self.decisions:
            return _baseline(f"unknown family {family_key!r}; baseline is mandatory")
        return self.decisions[family_key]

    def permits(
        self,
        family_key: str,
        compatibility_key: str,
        *,
        review_approved: bool = False,
    ) -> bool:
        return self.select(family_key).permits(
            compatibility_key, review_approved=review_approved
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "agent-compaction-portfolio-policy/v1",
            "registered_families": list(self.registered_families),
            "overall_confidence": self.overall_confidence,
            "manifest_digest": self.manifest_digest,
            "decisions": {
                family: self.decisions[family].as_dict()
                for family in self.registered_families
            },
        }

    @property
    def digest(self) -> str:
        blob = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PortfolioPolicy":
        if payload.get("schema") != "agent-compaction-portfolio-policy/v1":
            raise ValueError("unsupported portfolio policy schema")
        decisions: dict[str, PortfolioDecision] = {}
        for family, raw in dict(payload.get("decisions", {})).items():
            if not isinstance(raw, Mapping):
                raise ValueError(f"decision {family!r} must be a mapping")
            evidence = tuple(
                CandidateEvidence(
                    action=item["action"],
                    support_groups=int(item["support_groups"]),
                    quality_violations=int(item["quality_violations"]),
                    quality_risk_upper=float(item["quality_risk_upper"]),
                    regret_events=int(item["regret_events"]),
                    regret_risk_upper=float(item["regret_risk_upper"]),
                    mean_utility=float(item["mean_utility"]),
                    mean_reductions=dict(item.get("mean_reductions", {})),
                    compatible=_required_bool(
                        item["compatible"], label="candidate compatible"
                    ),
                    admitted=_required_bool(item["admitted"], label="candidate admitted"),
                    rejection_reasons=tuple(item.get("rejection_reasons", ())),
                    deployment_mode=DeploymentMode(item["deployment_mode"]),
                )
                for item in raw.get("evidence", ())
            )
            decisions[str(family)] = PortfolioDecision(
                selected_action=str(raw["selected_action"]),
                evidence=evidence,
                expected_compatibility_key=str(raw.get("expected_compatibility_key", "")),
                requires_review=_required_bool(
                    raw.get("requires_review", False), label="requires_review"
                ),
                rationale=str(raw.get("rationale", "")),
            )
        return cls(
            decisions=decisions,
            registered_families=tuple(payload.get("registered_families", ())),
            overall_confidence=float(payload["overall_confidence"]),
            manifest_digest=str(payload["manifest_digest"]),
        )
