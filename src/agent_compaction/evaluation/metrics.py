"""Metric families (execution-plan §13), reported separately and never composited.

No single score is allowed to hide a quality or safety regression, so the report is
a set of families:

* **efficiency** — request ratio (primary), tokens with cache decomposition, dollars,
  latency quantiles, critical path, tool calls by effect class, tool-surface size,
  gate/deopt overhead;
* **quality and safety** — task score, success, business outcomes, artifact effect
  divergence, downstream write-rate shift, fallback rate;
* **determinism and robustness** — repeat agreement, coefficient of variation,
  abstention behaviour by stratum;
* **maintainability** — active artifacts, leaves, DSL nodes, contract predicates;
* **discovery** — candidate frequency, groundability, rejection reasons by stage.

The distinction between *artifact effect divergence* (the compiled region performing
an effect the baseline did not: a hard gate, must be zero) and *downstream write-rate
shift* (the host agent's own later writes changing because evidence gathering became
deterministic: reported with its mechanism, never silently averaged) is deliberate.
Conflating them either hides a real regression or fails a candidate for something it
did not do.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from ..schema.artifacts import Artifact
from ..schema.effects import EffectCatalog, EffectClass
from ..schema.traces import Episode, EventKind

__all__ = ["EpisodeMetrics", "episode_metrics", "ConditionMetrics", "condition_metrics", "maintenance_metrics"]


@dataclass(slots=True)
class EpisodeMetrics:
    episode_id: str
    group_id: str
    requests: int = 0
    tool_calls: int = 0
    read_calls: int = 0
    write_calls: int = 0
    unknown_calls: int = 0
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    dollars: float = 0.0
    latency_ms: float = 0.0
    critical_path_ms: float = 0.0
    schema_tokens: int = 0
    prompt_tokens: int = 0
    quality: float = 0.0
    success: float = 0.0
    safety_events: int = 0
    dispatches: int = 0
    compacted: int = 0
    incidents: int = 0
    fallbacks: int = 0
    overhead_ms: float = 0.0
    artifact_write_effects: int = 0
    business: dict[str, float] = field(default_factory=dict)


def episode_metrics(episode: Episode, catalog: EffectCatalog) -> EpisodeMetrics:
    usage = episode.usage()
    m = EpisodeMetrics(
        episode_id=episode.episode_id,
        group_id=episode.group_id,
        requests=episode.n_requests(),
        input_tokens=usage.input_tokens,
        cached_input_tokens=usage.cached_input_tokens,
        output_tokens=usage.output_tokens,
        dollars=float(episode.attributes.get("dollars", 0.0)),
        latency_ms=episode.latency_ms(),
        critical_path_ms=episode.critical_path_ms(),
        quality=float(episode.outcome.semantic_score or 0.0),
        success=1.0 if episode.outcome.task_success else 0.0,
        safety_events=episode.outcome.safety_events,
        business=dict(episode.outcome.business_metrics),
    )
    for ev in episode.events:
        if ev.kind is EventKind.TOOL_CALL:
            m.tool_calls += 1
            eff = catalog.effect_of(ev.tool)
            if eff.is_read_like:
                m.read_calls += 1
            elif eff is EffectClass.UNKNOWN:
                m.unknown_calls += 1
            else:
                m.write_calls += 1
            if ev.attributes.get("compacted") and not eff.is_read_like:
                m.artifact_write_effects += 1
    boundaries = episode.boundaries()
    if boundaries:
        m.schema_tokens = int(boundaries[0].attributes.get("schema_tokens", 0))
        m.prompt_tokens = int(boundaries[0].attributes.get("prompt_tokens", 0))
    for rec in episode.attributes.get("dispatch_records", []):
        m.dispatches += 1
        m.overhead_ms += float(rec.get("overhead_ms", 0.0))
        outcome = rec.get("outcome")
        if outcome == "COMPACTED" and not rec.get("shadow"):
            m.compacted += 1
        elif outcome == "INCIDENT":
            m.incidents += 1
        elif rec.get("artifact") and outcome == "BASELINE" and not rec.get("shadow"):
            m.fallbacks += 1
    return m


@dataclass(slots=True)
class ConditionMetrics:
    """Per-condition aggregate. Denominators are always published."""

    condition: str
    n_episodes: int = 0
    n_groups: int = 0
    per_episode: list[EpisodeMetrics] = field(default_factory=list)
    aggregate: dict[str, float] = field(default_factory=dict)
    dispatch: dict[str, Any] = field(default_factory=dict)

    def values(self, field_name: str) -> list[float]:
        return [float(getattr(m, field_name)) for m in self.per_episode]

    def groups(self) -> list[str]:
        return [m.group_id for m in self.per_episode]

    def by_id(self) -> dict[str, EpisodeMetrics]:
        return {m.episode_id: m for m in self.per_episode}


def condition_metrics(
    condition: str,
    episodes: Sequence[Episode],
    catalog: EffectCatalog,
    *,
    dispatch_telemetry: dict[str, Any] | None = None,
) -> ConditionMetrics:
    per = [episode_metrics(ep, catalog) for ep in episodes]
    cm = ConditionMetrics(
        condition=condition,
        n_episodes=len(per),
        n_groups=len({m.group_id for m in per}),
        per_episode=per,
        dispatch=dispatch_telemetry or {},
    )
    if not per:
        return cm
    n = len(per)

    def mean(name: str) -> float:
        return sum(float(getattr(m, name)) for m in per) / n

    lat = sorted(m.latency_ms for m in per)
    cm.aggregate = {
        "requests": mean("requests"),
        "tool_calls": mean("tool_calls"),
        "read_calls": mean("read_calls"),
        "write_calls": mean("write_calls"),
        "unknown_calls": mean("unknown_calls"),
        "input_tokens": mean("input_tokens"),
        "cached_input_tokens": mean("cached_input_tokens"),
        "output_tokens": mean("output_tokens"),
        "dollars": mean("dollars"),
        "latency_ms_mean": mean("latency_ms"),
        "latency_ms_p50": lat[int(0.50 * n)],
        "latency_ms_p95": lat[min(n - 1, int(0.95 * n))],
        "latency_ms_p99": lat[min(n - 1, int(0.99 * n))],
        "critical_path_ms": mean("critical_path_ms"),
        "schema_tokens": mean("schema_tokens"),
        "prompt_tokens": mean("prompt_tokens"),
        "tool_surface_tokens": mean("schema_tokens") + mean("prompt_tokens"),
        "quality": mean("quality"),
        "success_rate": mean("success"),
        "safety_events_total": float(sum(m.safety_events for m in per)),
        "safety_events_rate": mean("safety_events"),
        "artifact_write_effects_total": float(sum(m.artifact_write_effects for m in per)),
        "episodes_compacted": float(sum(1 for m in per if m.compacted)),
        # Dispatch *executions*, not episodes: one episode may execute a region more
        # than once, and an incident is an execution that went wrong. This is the
        # only correct denominator for an unsafe-dispatch rate; ``episodes_compacted``
        # undercounts it and can be exceeded by the numerator.
        "artifact_executions_total": float(sum(m.compacted + m.incidents for m in per)),
        "coverage_phi": sum(1.0 for m in per if m.compacted) / n,
        "fallbacks_total": float(sum(m.fallbacks for m in per)),
        "incidents_total": float(sum(m.incidents for m in per)),
        "overhead_ms_per_episode": mean("overhead_ms"),
    }
    for key in sorted({k for m in per for k in m.business}):
        cm.aggregate[f"business.{key}"] = sum(m.business.get(key, 0.0) for m in per) / n
    return cm


def maintenance_metrics(artifacts: Sequence[Artifact]) -> dict[str, Any]:
    """The ``M(A)`` term: what an operator has to keep alive (execution-plan §13.4)."""

    dsl_nodes = 0
    predicates = 0
    prompt_variants = 0
    tool_allowlists = 0
    for a in artifacts:
        if a.program is not None:
            dsl_nodes += a.program.size
            predicates += a.program.branch_count
        if a.route is not None:
            prompt_variants += 1
            tool_allowlists += 1
            predicates += len(a.route.predicates)
        predicates += len(a.guard.clauses) + len(a.verifier.clauses)
    return {
        "active_artifacts": len(artifacts),
        "grc_artifacts": sum(1 for a in artifacts if a.kind == "grc"),
        "tgws_leaves": sum(1 for a in artifacts if a.kind == "tgws"),
        "dsl_nodes": dsl_nodes,
        "contract_predicates": predicates,
        "prompt_variants": prompt_variants,
        "tool_allowlists": tool_allowlists,
        "compatibility_dependencies": len({a.compatibility_key for a in artifacts}),
    }
