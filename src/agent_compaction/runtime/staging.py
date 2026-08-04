"""Staging and the reversibility attestation (proposal §4.7).

``stage.reversible()`` is an attestation, not a hope: it returns true only when
every component it claims to cover equals the entry snapshot. The set is explicit —
business state, model-visible history, interaction budget, quota/billing/audit
counters, permission context — and anything the deployment cannot observe must be
*declared unobservable*, which makes the attestation false rather than optimistic.

Proposal §6.2 row 7 is blunt about the consequence: in a distributed system the
attestation cannot be made truthfully, so dispatch must be restricted to
pre-commit read-only regions where reversibility is vacuous because nothing was
committed. :class:`Staging` enforces exactly that: a commit is refused if the
staged effect multiset contains anything the catalog does not mark pre-commit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from ..schema.effects import EffectCatalog

__all__ = ["Snapshot", "Staging", "StagingViolation"]


class StagingViolation(Exception):
    """A commit was attempted with a non-stageable effect in the multiset."""


@dataclass(frozen=True, slots=True)
class Snapshot:
    """Everything the attestation covers."""

    state_digest: str
    history_digest: str
    quota: tuple[tuple[str, int], ...]
    budget: int
    permission_context: str
    unobservable: tuple[str, ...] = ()

    def equals(self, other: "Snapshot") -> tuple[bool, list[str]]:
        diffs: list[str] = []
        if self.state_digest != other.state_digest:
            diffs.append("state")
        if self.history_digest != other.history_digest:
            diffs.append("history")
        if self.quota != other.quota:
            diffs.append("quota")
        if self.budget != other.budget:
            diffs.append("budget")
        if self.permission_context != other.permission_context:
            diffs.append("permission")
        unobservable = tuple(sorted(set(self.unobservable) | set(other.unobservable)))
        if unobservable:
            diffs.append("unobservable:" + ",".join(unobservable))
        return (not diffs), diffs


@dataclass(slots=True)
class Staging:
    """One staged attempt."""

    snapshot_fn: Callable[[], Snapshot]
    catalog: EffectCatalog
    entry: Snapshot | None = None
    committed: bool = False
    aborted: bool = False
    frozen: bool = False
    reasons: list[str] = field(default_factory=list)

    def begin(self) -> "Staging":
        self.entry = self.snapshot_fn()
        return self

    def reversible(self) -> bool:
        if self.entry is None:
            return False
        now = self.snapshot_fn()
        ok, diffs = self.entry.equals(now)
        if not ok:
            self.reasons.extend(diffs)
        return ok

    def abort(self) -> bool:
        """Abort the attempt. Returns whether the abort was clean."""

        clean = self.reversible()
        self.aborted = True
        return clean

    def freeze(self) -> None:
        self.frozen = True

    def commit(self, effects: Sequence[str]) -> None:
        for eff in effects:
            if eff not in {"PURE", "READ_LOCAL", "READ_EXTERNAL"}:
                raise StagingViolation(f"non-stageable effect in staged run: {eff}")
        self.committed = True
