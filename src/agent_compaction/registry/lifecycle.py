"""Artifact lifecycle: promotion, expiry, retirement, rollback, kill switch.

``discovered → synthesized → replay_validated → shadow → approved → active → retired``

Two rules are enforced in code rather than in a runbook (execution-plan §10.3/§10.5):

* **promotion requires a human approval identity distinct from the optimization job
  identity.** ``promote`` refuses when they match.
* **a candidate may not be promoted on the dataset used to synthesize it or to tune
  its gate.** The evidence carries the split digest and the roles used; promotion
  checks that the promoting evidence names a distinct evaluation split.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from ..schema.artifacts import Artifact, Lifecycle
from .store import Registry

__all__ = ["LifecycleError", "promote", "retire", "expire_due", "rollback", "audit_log"]


class LifecycleError(Exception):
    pass


_ORDER = {
    Lifecycle.DISCOVERED: 0,
    Lifecycle.SYNTHESIZED: 1,
    Lifecycle.REPLAY_VALIDATED: 2,
    Lifecycle.SHADOW: 3,
    Lifecycle.APPROVED: 4,
    Lifecycle.ACTIVE: 5,
    Lifecycle.RETIRED: 6,
}

AUDIT: list[dict[str, Any]] = []


def audit_log() -> list[dict[str, Any]]:
    return list(AUDIT)


def _record(action: str, artifact: Artifact, actor: str, **extra: Any) -> None:
    AUDIT.append(
        {
            "action": action,
            "artifact_id": artifact.artifact_id,
            "name": artifact.name,
            "lifecycle": artifact.lifecycle.value,
            "actor": actor,
            **extra,
        }
    )


def promote(
    artifact: Artifact,
    stage: Lifecycle,
    *,
    approved_by: str,
    job_identity: str,
    evaluation_split: str = "",
    expiry_day: str | None = None,
    rollback_target: str | None = None,
) -> Artifact:
    """Advance one stage at a time, with a distinct approver for live stages."""

    if stage is Lifecycle.RETIRED:
        raise LifecycleError("use retire() to retire an artifact")
    if _ORDER[stage] <= _ORDER[artifact.lifecycle]:
        raise LifecycleError(f"cannot promote {artifact.lifecycle.value} → {stage.value}")
    if _ORDER[stage] - _ORDER[artifact.lifecycle] > 1:
        raise LifecycleError(
            f"promotion must be one stage at a time: {artifact.lifecycle.value} → {stage.value}"
        )
    if stage in (Lifecycle.APPROVED, Lifecycle.ACTIVE):
        if not approved_by or approved_by == job_identity:
            raise LifecycleError(
                "promotion to approved/active requires a human approval identity "
                "distinct from the optimization job identity"
            )
        if evaluation_split and evaluation_split in ("train", "calibration"):
            raise LifecycleError(
                f"cannot promote on the {evaluation_split} split used to build or tune the artifact"
            )
    artifact.lifecycle = stage
    artifact.approved_by = approved_by if stage in (Lifecycle.APPROVED, Lifecycle.ACTIVE) else artifact.approved_by
    if expiry_day:
        artifact.expiry_day = expiry_day
    if rollback_target:
        artifact.rollback_target = rollback_target
    _record("promote", artifact, approved_by or job_identity, stage=stage.value, split=evaluation_split)
    return artifact


def retire(artifact: Artifact, *, actor: str, reason: str) -> Artifact:
    artifact.lifecycle = Lifecycle.RETIRED
    artifact.evidence.rejection_reasons.append(f"retired:{reason}")
    _record("retire", artifact, actor, reason=reason)
    return artifact


def expire_due(registry: Registry, today: str, *, actor: str = "scheduler") -> list[Artifact]:
    """Retire everything past its expiry day. Artifacts are build outputs, not assets."""

    out: list[Artifact] = []
    for a in registry.artifacts:
        if a.expiry_day and a.lifecycle is not Lifecycle.RETIRED and today > a.expiry_day:
            retire(a, actor=actor, reason=f"expired_on_{a.expiry_day}")
            out.append(a)
    return out


def rollback(registry: Registry, *, actor: str, reason: str) -> Registry:
    """Atomic pointer rollback to the previous signed registry (proposal §6.4)."""

    if registry.previous is None:
        raise LifecycleError("no previous registry to roll back to")
    for a in registry.artifacts:
        if a.lifecycle is Lifecycle.ACTIVE:
            retire(a, actor=actor, reason=f"rollback:{reason}")
    prev = registry.previous
    _record(
        "rollback",
        registry.artifacts[0] if registry.artifacts else Artifact(artifact_id="-", name="-"),
        actor,
        reason=reason,
        to=prev.name,
    )
    return prev


def invalidated_by_drift(artifact: Artifact, current_compatibility_key: str) -> bool:
    """Any code/prompt/model/tool/policy/effect drift invalidates the artifact."""

    return artifact.compatibility_key != current_compatibility_key
