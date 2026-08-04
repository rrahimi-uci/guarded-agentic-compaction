"""Canonical evidence records shared by traces, live runs, and portfolio selection."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any, Mapping, TYPE_CHECKING

from ..portfolio.model import PortfolioObservation

if TYPE_CHECKING:  # pragma: no cover
    from .metrics import EpisodeMetrics

__all__ = ["CanonicalMetrics", "paired_portfolio_observation"]


_MISSING = object()


def _pick(mapping: Mapping[str, Any], *names: str, default: Any = _MISSING) -> Any:
    present = [(name, mapping[name]) for name in names if name in mapping]
    if not present:
        if default is _MISSING:
            raise ValueError(f"missing required metric; expected one of {', '.join(names)}")
        return default
    first = present[0][1]
    if any(value != first for _, value in present[1:]):
        labels = ", ".join(name for name, _ in present)
        raise ValueError(f"conflicting aliases for canonical metric: {labels}")
    return first


def _count(value: Any, *, name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a non-negative integer")
    try:
        numeric = int(value)
        exact = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a non-negative integer") from exc
    if numeric < 0 or not isfinite(exact) or exact != numeric:
        raise ValueError(f"{name} must be a non-negative integer")
    return numeric


def _number(value: Any, *, name: str, nullable: bool = False) -> float | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite non-negative number")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite non-negative number") from exc
    if not isfinite(numeric) or numeric < 0:
        raise ValueError(f"{name} must be a finite non-negative number")
    return numeric


@dataclass(frozen=True, slots=True)
class CanonicalMetrics:
    """Strict measured record; unavailable cost remains ``None`` rather than zero."""

    model_requests: int
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float | None
    wall_latency_ms: float
    critical_path_ms: float
    tool_calls: int
    quality_contract_pass: bool
    provider_trace_id: str = ""
    run_status: str = "complete"

    def __post_init__(self) -> None:
        for name in (
            "model_requests",
            "input_tokens",
            "cached_input_tokens",
            "output_tokens",
            "total_tokens",
            "tool_calls",
        ):
            object.__setattr__(self, name, _count(getattr(self, name), name=name))
        for name in ("wall_latency_ms", "critical_path_ms"):
            object.__setattr__(self, name, _number(getattr(self, name), name=name))
        object.__setattr__(
            self,
            "estimated_cost_usd",
            _number(self.estimated_cost_usd, name="estimated_cost_usd", nullable=True),
        )
        if type(self.quality_contract_pass) is not bool:
            raise ValueError("quality_contract_pass must be a boolean")
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("cached_input_tokens cannot exceed input_tokens")
        if self.total_tokens != self.input_tokens + self.output_tokens:
            raise ValueError("total_tokens must equal input_tokens plus output_tokens")
        if not self.run_status.strip():
            raise ValueError("run_status must not be empty")

    @classmethod
    def from_episode_metrics(
        cls,
        metrics: "EpisodeMetrics",
        *,
        quality_contract_pass: bool | None = None,
        provider_trace_id: str = "",
        run_status: str = "complete",
    ) -> "CanonicalMetrics":
        quality = (
            bool(metrics.success)
            if quality_contract_pass is None
            else quality_contract_pass
        )
        return cls(
            model_requests=metrics.requests,
            input_tokens=metrics.input_tokens,
            cached_input_tokens=metrics.cached_input_tokens,
            output_tokens=metrics.output_tokens,
            total_tokens=metrics.input_tokens + metrics.output_tokens,
            estimated_cost_usd=metrics.dollars,
            wall_latency_ms=metrics.latency_ms,
            critical_path_ms=metrics.critical_path_ms,
            tool_calls=metrics.tool_calls,
            quality_contract_pass=quality,
            provider_trace_id=provider_trace_id,
            run_status=run_status,
        )

    @classmethod
    def from_live_mapping(
        cls,
        values: Mapping[str, Any],
        *,
        require_critical_path: bool = True,
    ) -> "CanonicalMetrics":
        wall = _pick(values, "wall_latency_ms", "latency_ms")
        critical = _pick(
            values,
            "critical_path_ms",
            default=_MISSING if require_critical_path else wall,
        )
        quality = _pick(values, "quality_contract_pass", "quality_pass", "exact_pass")
        if type(quality) is not bool:
            raise ValueError("quality_contract_pass must be a boolean")
        return cls(
            model_requests=_pick(values, "model_requests", "requests", "provider_requests"),
            input_tokens=_pick(values, "input_tokens"),
            cached_input_tokens=_pick(values, "cached_input_tokens", default=0),
            output_tokens=_pick(values, "output_tokens"),
            total_tokens=_pick(values, "total_tokens"),
            estimated_cost_usd=_pick(values, "estimated_cost_usd", "dollars", default=None),
            wall_latency_ms=wall,
            critical_path_ms=critical,
            tool_calls=_pick(values, "tool_calls"),
            quality_contract_pass=quality,
            provider_trace_id=str(
                _pick(values, "provider_trace_id", "native_trace_id", "trace_id", default="")
            ),
            run_status=str(_pick(values, "run_status", "status", default="complete")),
        )

    def portfolio_metrics(self) -> dict[str, float]:
        metrics = {
            "wall_latency_ms": self.wall_latency_ms,
            "total_tokens": float(self.total_tokens),
            "tool_calls": float(self.tool_calls),
        }
        if self.estimated_cost_usd is not None:
            metrics["estimated_cost_usd"] = self.estimated_cost_usd
        return metrics

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def paired_portfolio_observation(
    *,
    group_id: str,
    action: str,
    baseline: CanonicalMetrics,
    candidate: CanonicalMetrics,
    compatibility_key: str,
    metadata: Mapping[str, Any] | None = None,
) -> PortfolioObservation:
    """Map one strict measured pair into the existing selector contract."""

    if baseline.run_status != "complete" or candidate.run_status != "complete":
        raise ValueError("portfolio observations require complete baseline and candidate runs")
    return PortfolioObservation(
        group_id=group_id,
        action=action,
        baseline_quality=baseline.quality_contract_pass,
        candidate_quality=candidate.quality_contract_pass,
        baseline_metrics=baseline.portfolio_metrics(),
        candidate_metrics=candidate.portfolio_metrics(),
        compatibility_key=compatibility_key,
        metadata=dict(metadata or {}),
    )
