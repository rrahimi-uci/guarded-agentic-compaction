"""Qualification, canonical ordering, and data-quality reporting.

Two jobs:

1. **Qualification** (execution-plan §6, "compiler-eligible"): an episode may only
   inform an equivalence claim if its boundaries and manifest are complete, its
   order is reconstructable, its tool I/O is typed, its candidate effects are
   declared, its group id resists leakage, and nothing is truncated. Everything
   else may inform operations but not compilation.
2. **Canonical order** (Algorithm 2 line 3): a topological order in which
   mutually independent events are broken by signature, so that permuted parallel
   reads hash to the same window.

The per-field cardinality table computed here is what replaces the static
stoplist in the groundability policy (proposal §6.2 row 1 / §6.5 row 4).
"""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from ..schema.effects import EffectCatalog, EffectClass
from ..schema.traces import Episode, EventKind, EventNode, flatten

__all__ = [
    "QualificationResult",
    "qualify",
    "qualify_all",
    "signature",
    "canonical_order",
    "FieldStats",
    "field_statistics",
    "DataQualityReport",
    "data_quality",
]


# ---------------------------------------------------------------------------
# qualification
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class QualificationResult:
    episode_id: str
    eligible: bool
    reasons: list[str] = field(default_factory=list)


def qualify(episode: Episode, catalog: EffectCatalog) -> QualificationResult:
    reasons: list[str] = []
    ev = episode.events
    if not ev:
        reasons.append("no_events")
    if not episode.boundaries():
        reasons.append("no_model_boundaries")
    if any(e.truncated for e in ev):
        reasons.append("truncated_payload")
    if not episode.envelope.group_id or episode.envelope.group_id == "unknown":
        reasons.append("missing_group_id")
    if not episode.manifest or episode.manifest.manifest_id == "":
        reasons.append("missing_manifest")
    elif episode.envelope.manifest_id != episode.manifest.manifest_id:
        reasons.append("manifest_envelope_mismatch")
    if episode.manifest:
        required_manifest_fields = (
            "commit",
            "model",
            "prompt_hash",
            "tools_hash",
            "policy_hash",
            "guardrail_hash",
            "effect_catalog_version",
            "entry_contract_version",
        )
        incomplete = [
            name
            for name in required_manifest_fields
            if getattr(episode.manifest, name, "unknown") in {"", "unknown"}
        ]
        if incomplete:
            reasons.append("incomplete_manifest:" + ",".join(incomplete))
    if episode.outcome.task_success is None and episode.outcome.semantic_score is None:
        reasons.append("missing_outcome")
    # order reconstructable: indices strictly increasing, no gaps in call/result pairing
    indices = [e.index for e in ev]
    if indices != sorted(indices):
        reasons.append("unordered_events")
    if len(indices) != len(set(indices)):
        reasons.append("duplicate_event_index")
    if indices and indices != list(range(len(indices))):
        reasons.append("noncontiguous_event_index")
    node_ids = [e.node_id for e in ev]
    if len(node_ids) != len(set(node_ids)):
        reasons.append("duplicate_node_id")
    open_calls: list[str] = []
    open_by_id: set[str] = set()
    for e in ev:
        if (
            e.kind in (EventKind.TOOL_CALL, EventKind.TOOL_RESULT)
            and e.attributes.get("parallel_group") is not None
            and not e.call_id
        ):
            reasons.append("parallel_missing_call_id")
        if e.kind is EventKind.TOOL_CALL:
            if e.call_id:
                if e.call_id in open_by_id:
                    reasons.append("duplicate_call_id")
                open_by_id.add(e.call_id)
            else:
                open_calls.append(e.tool or "")
        elif e.kind is EventKind.TOOL_RESULT:
            if e.call_id:
                if e.call_id not in open_by_id:
                    reasons.append("orphan_tool_result")
                else:
                    open_by_id.remove(e.call_id)
            else:
                if not open_calls:
                    reasons.append("orphan_tool_result")
                else:
                    open_calls.pop(0)
    if open_calls or open_by_id:
        reasons.append("missing_tool_result")
    # typed tool IO
    for e in ev:
        if e.kind is EventKind.TOOL_CALL and not isinstance(e.input, dict):
            reasons.append(f"untyped_tool_input:{e.tool}")
            break
    # declared effects for tools that appear
    undeclared = catalog.undeclared(episode.tools_used())
    if undeclared:
        reasons.append("undeclared_tools:" + ",".join(undeclared[:4]))
    for event in ev:
        if not event.tool or not event.declared_effect or event.tool in undeclared:
            continue
        expected = catalog.effect_of(event.tool).value
        if event.declared_effect != expected:
            reasons.append(
                f"effect_declaration_mismatch:{event.tool}:{event.declared_effect}!={expected}"
            )
            break
    reasons = list(dict.fromkeys(reasons))
    return QualificationResult(episode.episode_id, not reasons, reasons)


def qualify_all(
    episodes: Sequence[Episode], catalog: EffectCatalog, *, require_declared: bool = False
) -> tuple[list[Episode], list[QualificationResult]]:
    """Split a snapshot into compiler-eligible and rejected episodes.

    ``require_declared`` is off by default: an undeclared tool blocks the *window*
    that contains it (Algorithm 2 line 8), not the whole episode. Turning it on
    reproduces the stricter reading of execution-plan §6.
    """

    results = [qualify(ep, catalog) for ep in episodes]
    keep: list[Episode] = []
    for ep, res in zip(episodes, results):
        blocking = [r for r in res.reasons if require_declared or not r.startswith("undeclared_tools")]
        if not blocking:
            keep.append(ep)
    return keep, results


# ---------------------------------------------------------------------------
# canonical order + signatures
# ---------------------------------------------------------------------------


def signature(event: EventNode, catalog: EffectCatalog) -> str:
    """Value-free signature: tool, schema hash, argument-path shape, effect class."""

    if event.kind in (EventKind.TOOL_CALL, EventKind.TOOL_RESULT):
        paths = sorted(p for p, _ in flatten(event.input if event.kind is EventKind.TOOL_CALL else {}))
        shape = ",".join(paths)
        eff = catalog.effect_of(event.tool).value
        return f"{event.kind.value}:{event.tool}:{event.schema_version or 'v0'}:{eff}:{_h(shape)}"
    if event.kind is EventKind.MODEL_REQ:
        tools = event.input.get("tools") if isinstance(event.input, dict) else None
        return f"MODEL_REQ:{_h(','.join(tools or []))}"
    if event.kind is EventKind.HANDOFF:
        target = event.output.get("target") if isinstance(event.output, dict) else ""
        return f"HANDOFF:{target}"
    return event.kind.value


def _h(s: str) -> str:
    return hashlib.sha1(s.encode()).hexdigest()[:8]


def canonical_order(episode: Episode, catalog: EffectCatalog) -> list[EventNode]:
    """Topological order; ties among mutually independent events by signature.

    Independence here is declared by ``attributes['parallel_group']``: events in
    the same parallel group have no order edge between them, so they are sorted by
    signature to make permuted parallel reads canonical.
    """

    out: list[EventNode] = []
    buffer: list[EventNode] = []
    current_group: str | None = None

    def flush() -> None:
        nonlocal buffer, current_group
        if buffer:
            out.extend(sorted(buffer, key=lambda e: (signature(e, catalog), e.index)))
            buffer = []
        current_group = None

    for e in episode.events:
        pg = e.attributes.get("parallel_group")
        if pg is None:
            flush()
            out.append(e)
            continue
        if pg != current_group:
            flush()
            current_group = pg
        buffer.append(e)
    flush()
    return out


# ---------------------------------------------------------------------------
# field statistics (corpus-derived groundability)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class FieldStats:
    """Per-field cardinality/entropy over a snapshot."""

    counts: dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))

    def observe(self, path: str, value: Any) -> None:
        if isinstance(value, (dict, list)):
            return
        self.counts[_normalise_path(path)][_key(value)] += 1

    def cardinality(self, path: str) -> int:
        return len(self.counts.get(_normalise_path(path), ()))

    def total(self, path: str) -> int:
        return sum(self.counts.get(_normalise_path(path), Counter()).values())

    def entropy_bits(self, path: str) -> float:
        import math

        c = self.counts.get(_normalise_path(path))
        if not c:
            return 0.0
        n = sum(c.values())
        return -sum((v / n) * math.log2(v / n) for v in c.values())

    def top_share(self, path: str) -> float:
        c = self.counts.get(_normalise_path(path))
        if not c:
            return 1.0
        n = sum(c.values())
        return max(c.values()) / n if n else 1.0


def _normalise_path(path: str) -> str:
    """Collapse list indices so that ``recs[0].id`` and ``recs[3].id`` share stats."""

    out = []
    i = 0
    while i < len(path):
        if path[i] == "[":
            j = path.find("]", i)
            if j < 0:
                return path
            out.append("[]")
            i = j + 1
        else:
            out.append(path[i])
            i += 1
    return "".join(out)


def _key(value: Any) -> str:
    return f"{type(value).__name__}:{value}"


def field_statistics(episodes: Iterable[Episode]) -> FieldStats:
    stats = FieldStats()
    for ep in episodes:
        for path, value in flatten(ep.entry_state, prefix="z"):
            stats.observe(path, value)
        for e in ep.events:
            if e.kind is EventKind.TOOL_RESULT and e.output is not None:
                for path, value in flatten(e.output, prefix=f"{e.tool}"):
                    stats.observe(path, value)
            elif e.kind is EventKind.TOOL_CALL and isinstance(e.input, dict):
                for path, value in flatten(e.input, prefix=f"{e.tool}#in"):
                    stats.observe(path, value)
    return stats


# ---------------------------------------------------------------------------
# data-quality report
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class DataQualityReport:
    n_episodes: int = 0
    n_eligible: int = 0
    n_eligible_strict: int = 0
    n_groups: int = 0
    n_principals: int = 0
    n_days: int = 0
    span_completeness: float = 0.0
    manifest_coverage: float = 0.0
    effect_coverage: float = 0.0
    outcome_coverage: float = 0.0
    outcome_label_latency_s: float = 0.0
    duplicate_rate: float = 0.0
    schema_drift: dict[str, int] = field(default_factory=dict)
    scope_coverage: dict[str, int] = field(default_factory=dict)
    rejection_reasons: dict[str, int] = field(default_factory=dict)
    undeclared_tools: list[str] = field(default_factory=list)
    gate0_pass: bool = False

    def render(self) -> str:
        lines = [
            "data-quality report",
            "───────────────────",
            f"episodes                {self.n_episodes}",
            f"compiler-eligible       {self.n_eligible} ({_pct(self.n_eligible, self.n_episodes)})",
            f"  of which fully declared {self.n_eligible_strict} "
            f"({_pct(self.n_eligible_strict, self.n_episodes)})",
            f"independent groups      {self.n_groups}",
            f"principals / days       {self.n_principals} / {self.n_days}",
            f"span completeness       {self.span_completeness:.3f}",
            f"manifest coverage       {self.manifest_coverage:.3f}",
            f"effect coverage         {self.effect_coverage:.3f}",
            f"outcome coverage        {self.outcome_coverage:.3f}",
            f"duplicate rate          {self.duplicate_rate:.3f}",
            f"undeclared tools        {', '.join(self.undeclared_tools) or '-'}",
            f"schema drift            {self.schema_drift or '-'}",
            f"rejections              {self.rejection_reasons or '-'}",
            f"Gate 0 (data)           {'PASS' if self.gate0_pass else 'FAIL'}",
        ]
        return "\n".join(lines)


def _pct(a: int, b: int) -> str:
    return f"{(100.0 * a / b):.1f}%" if b else "n/a"


def data_quality(episodes: Sequence[Episode], catalog: EffectCatalog, *, min_groups: int = 20) -> DataQualityReport:
    rep = DataQualityReport(n_episodes=len(episodes))
    if not episodes:
        return rep
    results = [qualify(ep, catalog) for ep in episodes]
    # An undeclared tool blocks the *window* that contains it (Algorithm 2 line
    # 8), not the whole episode, so it is reported separately rather than as an
    # eligibility failure.
    rep.n_eligible = sum(
        1 for r in results if not [x for x in r.reasons if not x.startswith("undeclared_tools")]
    )
    rep.n_eligible_strict = sum(1 for r in results if r.eligible)
    reasons: Counter = Counter()
    for r in results:
        for reason in r.reasons:
            reasons[reason.split(":")[0]] += 1
    rep.rejection_reasons = dict(reasons)
    rep.n_groups = len({ep.group_id for ep in episodes})
    rep.n_principals = len({ep.envelope.principal for ep in episodes})
    rep.n_days = len({ep.envelope.day for ep in episodes})
    # Gate 0's "required-span completeness" is not just the truncation flag: a dropped
    # tool result is a missing span even when nothing was marked truncated, and it is
    # the failure mode a capture pipeline actually produces.
    span_defects = {"truncated_payload", "missing_tool_result", "orphan_tool_result", "no_model_boundaries"}
    rep.span_completeness = sum(
        1 for r in results if not (span_defects & {x.split(":")[0] for x in r.reasons})
    ) / len(episodes)
    rep.manifest_coverage = sum(1 for ep in episodes if ep.manifest.manifest_id) / len(episodes)
    all_tools = sorted({t for ep in episodes for t in ep.tools_used()})
    cov = catalog.validate_coverage(all_tools)
    rep.effect_coverage = cov["coverage"]
    rep.undeclared_tools = cov["undeclared"]
    rep.outcome_coverage = sum(
        1 for ep in episodes if ep.outcome.task_success is not None or ep.outcome.semantic_score is not None
    ) / len(episodes)
    rep.outcome_label_latency_s = sum(ep.outcome.label_latency_s for ep in episodes) / len(episodes)
    seen: Counter = Counter(ep.envelope.entry_state_ref or ep.episode_id for ep in episodes)
    rep.duplicate_rate = 1.0 - len(seen) / len(episodes)
    rep.schema_drift = dict(Counter(ep.manifest.entry_contract_version for ep in episodes))
    rep.scope_coverage = dict(Counter(ep.envelope.tenant_partition for ep in episodes))
    # Gate 0: >=95% span completeness, 100% effect classification of candidate
    # tools, enough independent groups, usable outcomes (execution-plan §16.2).
    rep.gate0_pass = (
        rep.span_completeness >= 0.95
        and rep.effect_coverage == 1.0
        and rep.outcome_coverage >= 0.95
        and rep.n_groups >= min_groups
    )
    return rep
