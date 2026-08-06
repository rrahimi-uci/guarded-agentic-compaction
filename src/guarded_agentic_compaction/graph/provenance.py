"""Algorithm 1 — the provenance-annotated trace graph (PATG).

Recovers dataflow from traces alone by typed content matching against a producer
index, then by bounded transform search on exact-match misses.

Two load-bearing corrections from proposal §4.1 are implemented, not deferred:

* **Entry state is seeded as pseudo-producer 0** (lines 2-3). Without it every
  slot whose value comes from the entry state is ``UNGROUNDED``, Algorithm 2
  line 10 discards the window, and the reference use case has no artifact at all.
* **Every candidate producer is kept**, capped at ``κ`` (lines 13-14). Collapsing
  to the nearest producer binds the wrong source consistently enough that no
  single trace reveals the error; Algorithm 3 commits to one source using
  stability across the whole family.

The groundability policy ``Θ`` is corpus-derived rather than a static stoplist
(proposal §6.2 row 1): a value is groundable only if its field's observed
cardinality clears a threshold, which is what keeps status enums, region codes and
tenant ids echoed in every response from manufacturing spurious dependencies.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from ..grc.dsl import Op, SynthContext, search_chains
from ..schema.effects import EffectCatalog
from ..schema.traces import Episode, EventKind, EventNode, flatten
from .normalize import FieldStats, canonical_order, signature

__all__ = [
    "GroundabilityPolicy",
    "SlotMark",
    "Slot",
    "Producer",
    "DataEdge",
    "PATG",
    "build_patg",
    "build_all",
]

_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")

DEFAULT_STOPLIST = frozenset(
    {
        "true",
        "false",
        "none",
        "null",
        "ok",
        "error",
        "yes",
        "no",
        "active",
        "closed",
        "open",
        "paid",
        "usd",
        "eur",
        "en",
        "en-us",
        "asc",
        "desc",
    }
)


@dataclass(slots=True)
class GroundabilityPolicy:
    """``Θ``: which observed values may act as provenance sources or targets."""

    stoplist: frozenset[str] = DEFAULT_STOPLIST
    min_str_len: int = 3
    min_field_cardinality: int = 4
    max_top_share: float = 0.80
    stats: FieldStats | None = None
    literal_only: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def groundable(self, value: Any, path: str | None = None) -> bool:
        if isinstance(value, bool) or value is None:
            return False
        if isinstance(value, str):
            if len(value) < self.min_str_len or value.strip().lower() in self.stoplist:
                return False
        elif isinstance(value, int):
            if abs(value) <= 1:
                return False
        elif isinstance(value, float):
            pass
        elif isinstance(value, (list, dict)):
            return bool(value)
        else:
            return False
        if path is not None and self.stats is not None:
            # corpus-derived entropy filter: a value drawn from a near-constant
            # field cannot establish a dependency
            card = self.stats.cardinality(path)
            if card and card < self.min_field_cardinality:
                return False
            if card and self.stats.top_share(path) > self.max_top_share:
                return False
        return True

    def is_literal_only(self, tool: str | None, slot_path: str) -> bool:
        if tool is None:
            return False
        return slot_path in self.literal_only.get(tool, ())

    @classmethod
    def from_catalog(
        cls,
        catalog: EffectCatalog,
        stats: FieldStats | None = None,
        **kwargs: Any,
    ) -> "GroundabilityPolicy":
        lit = {name: spec.literal_only for name, spec in catalog.tools.items() if spec.literal_only}
        return cls(stats=stats, literal_only=lit, **kwargs)


class SlotMark:
    GROUNDED = "GROUNDED"
    UNGROUNDED = "UNGROUNDED"
    AMBIGUOUS = "AMBIGUOUS"
    LITERAL = "LITERAL"
    NOT_GROUNDABLE = "NOT_GROUNDABLE"


@dataclass(frozen=True, slots=True)
class Producer:
    """Where a value came from. ``event_index == -1`` is the entry state."""

    event_index: int
    path: str
    tool: str | None = None

    @property
    def is_entry_state(self) -> bool:
        return self.event_index == -1


@dataclass(frozen=True, slots=True)
class DataEdge:
    producer: Producer
    consumer_index: int
    consumer_path: str
    ops: tuple[Op, ...] = ()

    @property
    def is_identity(self) -> bool:
        return not self.ops

    def pretty(self) -> str:
        chain = " |> ".join(str(o) for o in self.ops)
        src = self.producer.path
        return f"{src}{' |> ' + chain if chain else ''} → [{self.consumer_index}].{self.consumer_path}"


@dataclass(slots=True)
class Slot:
    """One argument slot of one event."""

    event_index: int
    path: str
    value: Any
    tool: str | None
    mark: str = SlotMark.UNGROUNDED
    candidates: tuple[DataEdge, ...] = ()

    @property
    def key(self) -> tuple[int, str]:
        return (self.event_index, self.path)


@dataclass(slots=True)
class PATG:
    """Provenance-annotated trace graph for one episode."""

    episode: Episode
    order: list[EventNode]
    boundaries: list[int]
    slots: dict[tuple[int, str], Slot] = field(default_factory=dict)
    data_edges: list[DataEdge] = field(default_factory=list)
    order_edges: list[tuple[int, int]] = field(default_factory=list)
    diagnostics: dict[str, int] = field(default_factory=dict)
    index_of: dict[int, int] = field(default_factory=dict)

    def slots_of(self, event_index: int) -> list[Slot]:
        return [s for (i, _), s in self.slots.items() if i == event_index]

    def event_at(self, position: int) -> EventNode:
        return self.order[position]


def build_patg(
    episode: Episode,
    catalog: EffectCatalog,
    policy: GroundabilityPolicy,
    *,
    max_depth: int = 2,
    kappa: int = 3,
    ctx: SynthContext | None = None,
) -> PATG:
    order = canonical_order(episode, catalog)
    boundaries = [i for i, e in enumerate(order) if e.kind is EventKind.MODEL_REQ]
    patg = PATG(episode=episode, order=order, boundaries=boundaries)
    patg.index_of = {e.index: i for i, e in enumerate(order)}
    diag = defaultdict(int)

    # value index: canonical value key -> list[Producer]
    index: dict[str, list[Producer]] = defaultdict(list)
    # ordered list of (producer, value) for transform search
    sources: list[tuple[Producer, Any]] = []
    # values that first appear in a model response: decisions, not dataflow
    model_origin: dict[str, list[Producer]] = defaultdict(list)

    def add_producer(prod: Producer, path: str, value: Any) -> None:
        if not policy.groundable(value, path):
            return
        index[_vkey(value)].append(prod)
        sources.append((prod, value))

    # ---- lines 2-3: seed the entry state as pseudo-producer 0 -------------
    for path, value in flatten(episode.entry_state, prefix="z"):
        add_producer(Producer(-1, path), path, value)

    synth_ctx = ctx or SynthContext(max_depth=max_depth)
    cache_hits_before = synth_ctx.cache_hits
    cache_misses_before = synth_ctx.cache_misses

    for pos, ev in enumerate(order):
        # ---- lines 5-14: consumers ---------------------------------------
        if ev.kind is EventKind.TOOL_CALL and isinstance(ev.input, dict):
            for path, value in flatten(ev.input):
                if isinstance(value, (dict, list)):
                    continue  # containers are bound leaf-by-leaf
                slot = Slot(pos, path, value, ev.tool)
                stats_path = f"{ev.tool}#in.{path}"
                if policy.is_literal_only(ev.tool, path):
                    slot.mark = SlotMark.LITERAL
                    patg.slots[slot.key] = slot
                    diag["literal_only"] += 1
                    continue
                if not policy.groundable(value, stats_path):
                    slot.mark = SlotMark.NOT_GROUNDABLE
                    patg.slots[slot.key] = slot
                    diag["not_groundable"] += 1
                    continue
                cands = [p for p in index.get(_vkey(value), []) if _before(p, pos)]
                ops_by_prod: list[DataEdge] = _dedupe_edges(
                    [DataEdge(p, pos, path, ()) for p in cands]
                )
                if not ops_by_prod:
                    diag["transform_search"] += 1
                    ops_by_prod = _transform_search(
                        value, sources, pos, path, synth_ctx, kappa=kappa
                    )
                if not ops_by_prod:
                    slot.mark = SlotMark.UNGROUNDED
                    diag["ungrounded"] += 1
                    if _vkey(value) in model_origin:
                        diag["model_originated"] += 1
                elif len({(e.producer.event_index, e.producer.path) for e in ops_by_prod}) > kappa:
                    slot.mark = SlotMark.AMBIGUOUS
                    diag["ambiguous"] += 1
                else:
                    slot.mark = SlotMark.GROUNDED
                    slot.candidates = tuple(ops_by_prod)
                    patg.data_edges.extend(ops_by_prod)
                    diag["grounded"] += 1
                patg.slots[slot.key] = slot

        # ---- lines 15-17: producers --------------------------------------
        if ev.kind is EventKind.TOOL_RESULT and ev.output is not None and ev.status == "ok":
            for path, value in flatten(ev.output):
                add_producer(Producer(pos, path, ev.tool), f"{ev.tool}.{path}", value)
            if isinstance(ev.output, (dict, list)):
                add_producer(Producer(pos, "", ev.tool), f"{ev.tool}", ev.output)
        elif ev.kind is EventKind.MODEL_RESP and isinstance(ev.output, dict):
            # Model responses are recorded in a *separate* index. They are not
            # grounding sources: the response that emits a tool call trivially
            # "produces" that call's own arguments, so indexing it as a producer
            # would make every slot self-grounded and defeat Eq. (4). Their only
            # role is to mark a value as model-originated, which is admissible
            # solely as a Const (Algorithm 3 line 1).
            args = ev.output.get("arguments")
            if isinstance(args, dict):
                for path, value in flatten(args):
                    model_origin[_vkey(value)].append(Producer(pos, f"$resp.{path}", None))

    # ---- line 18: order edges from effect conflicts ------------------------
    for i, a in enumerate(order):
        if a.kind is not EventKind.TOOL_CALL:
            continue
        for j in range(i + 1, len(order)):
            b = order[j]
            if b.kind is not EventKind.TOOL_CALL:
                continue
            if catalog.conflicts_on_resource(a.tool, b.tool):
                patg.order_edges.append((i, j))

    diag["transform_cache_hits"] = synth_ctx.cache_hits - cache_hits_before
    diag["transform_cache_misses"] = synth_ctx.cache_misses - cache_misses_before
    patg.diagnostics = dict(diag)
    return patg


def _before(prod: Producer, pos: int) -> bool:
    return prod.event_index < pos


def _vkey(value: Any) -> str:
    if isinstance(value, (dict, list)):
        import json

        return "J:" + json.dumps(value, sort_keys=True, default=str)[:512]
    return f"{type(value).__name__}:{value}"


def _transform_search(
    target: Any,
    sources: Sequence[tuple[Producer, Any]],
    pos: int,
    consumer_path: str,
    ctx: SynthContext,
    *,
    kappa: int,
    max_sources: int = 48,
) -> list[DataEdge]:
    """``TransformSearch``: bounded, prefiltered, and capped.

    The prefilter is what makes this affordable: only sources with a plausible
    relation to the target are searched. Containers are always plausible (they
    carry the select-then-project pattern); scalars must pass a cheap string or
    numeric relation test.
    """

    out: list[DataEdge] = []
    considered = 0
    for prod, value in reversed(sources):
        if not _before(prod, pos):
            continue
        if not _plausible(value, target):
            continue
        considered += 1
        if considered > max_sources:
            break
        chains = search_chains(value, target, ctx, max_results=2)
        for chain in chains:
            if chain:
                out.append(_fold_projections(DataEdge(prod, pos, consumer_path, chain), value))
        if len({(e.producer.event_index, e.producer.path) for e in out}) > kappa:
            break
    return _dedupe_edges(out)


def _fold_projections(edge: DataEdge, source_value: Any) -> DataEdge:
    """Rewrite ``dict |> project(f) |> rest`` as the path ``dict.f`` plus ``rest``.

    Without this, a container source produces edges whose producer path is an
    ancestor (``z``, ``z.ticket``) rather than the field actually read, and the
    entry-schema admissibility test of Algorithm 2 line 11 rejects the window even
    though the field is allowlisted. Only ``project`` on a *dict* is folded:
    ``project`` on a list is a map over items and is not a path extension.
    """

    path = edge.producer.path
    ops = list(edge.ops)
    value = source_value
    while ops and ops[0].name == "project" and isinstance(value, dict):
        sub = ops[0].params[0]
        try:
            value = ops[0].apply(value)
        except Exception:  # pragma: no cover - defensive
            break
        path = f"{path}.{sub}" if path else sub
        ops.pop(0)
    if path == edge.producer.path and len(ops) == len(edge.ops):
        return edge
    return DataEdge(
        Producer(edge.producer.event_index, path, edge.producer.tool),
        edge.consumer_index,
        edge.consumer_path,
        tuple(ops),
    )


def _dedupe_edges(edges: Sequence[DataEdge]) -> list[DataEdge]:
    """One edge per (producer event, source path): the minimum-description one."""

    best: dict[tuple[int, str], DataEdge] = {}
    for e in edges:
        key = (e.producer.event_index, e.producer.path)
        cur = best.get(key)
        cost = (len(e.ops), sum(o.cost for o in e.ops))
        if cur is None or cost < (len(cur.ops), sum(o.cost for o in cur.ops)):
            best[key] = e
    return list(best.values())


def _plausible(value: Any, target: Any) -> bool:
    if isinstance(value, (dict, list)):
        return bool(value)
    if isinstance(target, str) and isinstance(value, str):
        lv, lt = value.lower(), target.lower()
        return (
            lv == lt
            or value.strip() == target
            or lt in lv
            or lv in lt
            or any(part.lower() == lt for part in re.split(r"[@._\-/: ,]", value))
        )
    if isinstance(target, (int, float)) and isinstance(value, (int, float)):
        return True
    if isinstance(target, (int, float)) and isinstance(value, str):
        return value.strip().lstrip("-").replace(".", "", 1).isdigit()
    if isinstance(target, str) and isinstance(value, (int, float)):
        return str(value) in target or target.isdigit()
    return False


def build_all(
    episodes: Sequence[Episode],
    catalog: EffectCatalog,
    policy: GroundabilityPolicy | None = None,
    *,
    max_depth: int = 2,
    kappa: int = 3,
) -> tuple[list[PATG], GroundabilityPolicy]:
    from .normalize import field_statistics

    if policy is None:
        policy = GroundabilityPolicy.from_catalog(catalog, stats=field_statistics(episodes))
    ctx = SynthContext(max_depth=max_depth)
    graphs = [
        build_patg(ep, catalog, policy, max_depth=max_depth, kappa=kappa, ctx=ctx) for ep in episodes
    ]
    return graphs, policy
