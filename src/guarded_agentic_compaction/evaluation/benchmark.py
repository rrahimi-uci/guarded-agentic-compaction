"""Framework-neutral efficiency, quality, and determinism comparisons."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Sequence

from ..paths import content_digest
from ..schema.effects import EffectCatalog
from ..schema.traces import Episode
from .metrics import condition_metrics

__all__ = ["BenchmarkComparison", "compare_episodes", "repeat_agreement"]


@dataclass(slots=True)
class BenchmarkComparison:
    """One paired baseline/candidate comparison with explicit denominators."""

    n_pairs: int
    n_groups: int
    ratios: dict[str, float] = field(default_factory=dict)
    deltas: dict[str, float] = field(default_factory=dict)
    determinism: dict[str, float] = field(default_factory=dict)
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "n_pairs": self.n_pairs,
            "n_groups": self.n_groups,
            "ratios": self.ratios,
            "deltas": self.deltas,
            "determinism": self.determinism,
            "notes": list(self.notes),
        }


def _ratio(candidate: float, baseline: float) -> float:
    return candidate / baseline if baseline else float("nan")


def compare_episodes(
    baseline: Sequence[Episode],
    candidate: Sequence[Episode],
    catalog: EffectCatalog,
) -> BenchmarkComparison:
    """Compare the intersection of episode IDs; never compare unpaired traffic."""

    base_by_id = {episode.episode_id: episode for episode in baseline}
    cand_by_id = {episode.episode_id: episode for episode in candidate}
    ids = sorted(set(base_by_id) & set(cand_by_id))
    paired_base = [base_by_id[key] for key in ids]
    paired_cand = [cand_by_id[key] for key in ids]
    b = condition_metrics("baseline", paired_base, catalog).aggregate
    c = condition_metrics("candidate", paired_cand, catalog).aggregate
    ratios = {
        "model_requests": _ratio(c.get("requests", 0.0), b.get("requests", 0.0)),
        "input_tokens": _ratio(c.get("input_tokens", 0.0), b.get("input_tokens", 0.0)),
        "output_tokens": _ratio(c.get("output_tokens", 0.0), b.get("output_tokens", 0.0)),
        "latency_mean": _ratio(c.get("latency_ms_mean", 0.0), b.get("latency_ms_mean", 0.0)),
        "cost": _ratio(c.get("dollars", 0.0), b.get("dollars", 0.0)),
        "tool_calls": _ratio(c.get("tool_calls", 0.0), b.get("tool_calls", 0.0)),
        "tool_surface": _ratio(
            c.get("tool_surface_tokens", 0.0), b.get("tool_surface_tokens", 0.0)
        ),
    }
    deltas = {
        "quality": c.get("quality", 0.0) - b.get("quality", 0.0),
        "success_rate": c.get("success_rate", 0.0) - b.get("success_rate", 0.0),
        "safety_events_rate": c.get("safety_events_rate", 0.0)
        - b.get("safety_events_rate", 0.0),
        "workflow_steps": c.get("requests", 0.0)
        + c.get("tool_calls", 0.0)
        - b.get("requests", 0.0)
        - b.get("tool_calls", 0.0),
    }
    notes: list[str] = []
    if len(ids) < max(len(base_by_id), len(cand_by_id)):
        notes.append("unpaired episode IDs were excluded")
    return BenchmarkComparison(
        n_pairs=len(ids),
        n_groups=len({episode.group_id for episode in paired_base}),
        ratios=ratios,
        deltas=deltas,
        determinism={
            "baseline_repeat_agreement": repeat_agreement(paired_base),
            "candidate_repeat_agreement": repeat_agreement(paired_cand),
        },
        notes=tuple(notes),
    )


def repeat_agreement(episodes: Sequence[Episode], *, output_key: str = "answer") -> float:
    """Mean within-group exact agreement for groups with repeated executions."""

    by_group: dict[str, list[str]] = defaultdict(list)
    for episode in episodes:
        if output_key not in episode.attributes:
            continue
        by_group[episode.group_id].append(content_digest(episode.attributes[output_key]))
    scores: list[float] = []
    for values in by_group.values():
        if len(values) < 2:
            continue
        scores.append(max(Counter(values).values()) / len(values))
    return sum(scores) / len(scores) if scores else float("nan")
