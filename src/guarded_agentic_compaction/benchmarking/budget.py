"""Explicit provider-spend authorization and fail-closed accounting."""

from __future__ import annotations

import math
import threading
from dataclasses import asdict, dataclass

__all__ = ["BudgetExceeded", "ProviderBudget", "ProviderCharge"]


class BudgetExceeded(RuntimeError):
    """A provider request was not authorized by the remaining explicit cap."""


@dataclass(frozen=True, slots=True)
class ProviderCharge:
    event_id: str
    estimated_usd: float
    actual_usd: float | None = None

    def __post_init__(self) -> None:
        for name in ("estimated_usd", "actual_usd"):
            value = getattr(self, name)
            if value is None:
                continue
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")
        if not self.event_id.strip():
            raise ValueError("event_id must not be empty")


class ProviderBudget:
    """Thread-safe reservation ledger requiring a positive user-supplied cap."""

    def __init__(self, max_usd: float) -> None:
        if not math.isfinite(max_usd) or max_usd <= 0:
            raise ValueError("max_usd must be a positive finite explicit cap")
        self.max_usd = float(max_usd)
        self._lock = threading.RLock()
        self._charges: dict[str, ProviderCharge] = {}

    @property
    def committed_usd(self) -> float:
        with self._lock:
            return sum(
                charge.actual_usd
                if charge.actual_usd is not None
                else charge.estimated_usd
                for charge in self._charges.values()
            )

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.max_usd - self.committed_usd)

    def reserve(self, event_id: str, estimated_usd: float) -> ProviderCharge:
        charge = ProviderCharge(event_id=event_id, estimated_usd=estimated_usd)
        with self._lock:
            existing = self._charges.get(event_id)
            if existing is not None:
                if existing.estimated_usd != charge.estimated_usd:
                    raise BudgetExceeded(
                        f"event {event_id!r} was reserved with a different estimate"
                    )
                return existing
            if self.committed_usd + estimated_usd > self.max_usd + 1e-12:
                raise BudgetExceeded(
                    f"provider cap would be exceeded: remaining ${self.remaining_usd:.6f}"
                )
            self._charges[event_id] = charge
            return charge

    def reconcile(self, event_id: str, actual_usd: float) -> ProviderCharge:
        with self._lock:
            existing = self._charges.get(event_id)
            if existing is None:
                raise BudgetExceeded(f"event {event_id!r} has no prior reservation")
            updated = ProviderCharge(
                event_id=event_id,
                estimated_usd=existing.estimated_usd,
                actual_usd=actual_usd,
            )
            projected = self.committed_usd - (
                existing.actual_usd
                if existing.actual_usd is not None
                else existing.estimated_usd
            ) + actual_usd
            if projected > self.max_usd + 1e-12:
                raise BudgetExceeded(
                    f"actual provider cost would exceed cap by ${projected - self.max_usd:.6f}"
                )
            self._charges[event_id] = updated
            return updated

    def as_dict(self) -> dict[str, object]:
        with self._lock:
            return {
                "schema": "agent-compaction-provider-budget/v1",
                "max_usd": self.max_usd,
                "committed_usd": self.committed_usd,
                "remaining_usd": self.remaining_usd,
                "charges": [
                    asdict(self._charges[key]) for key in sorted(self._charges)
                ],
            }
