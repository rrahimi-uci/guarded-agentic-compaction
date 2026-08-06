"""Algorithm 2 — canonical-window region mining.

Agent traces are linearizations, so any recurring region appears as a contiguous
window in a canonical order. Enumerating bounded windows and hashing their
value-free shape costs ``O(N·L)`` and avoids general subgraph isomorphism.

Beyond the published listing, three things are implemented because the demos
require them and because leaving them out would silently exclude the dominant
real patterns:

* **Support is counted by group *and* principal *and* day** (proposal §6.2 row 2).
  Production has no scenario ids and one automated caller hammering the same
  request otherwise looks like broad support. Both conditions, not either.
* **Runs of the same signature are collapsed** into a single step with observed
  run lengths, which is how the bounded ``ForEach`` of proposal §4.4 is
  discovered rather than hard-coded.
* **Prefix-extension families are merged into branch candidates**, which is how
  the ``if sub.tier == "enterprise"`` arm of use-cases §1 can exist at all: the
  two arms have different canonical hashes and would otherwise never meet.

Every rejected window is counted by reason. "Do not compact" is the common and
correct output, and the estimator's blocked-window breakdown is built from these
counters.
"""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from ..schema.effects import EffectCatalog, EffectClass
from ..schema.traces import Episode, EventKind, EventNode
from .normalize import signature
from .provenance import PATG, Producer, Slot, SlotMark

__all__ = [
    "WindowStep",
    "Window",
    "Family",
    "MiningResult",
    "enumerate_windows",
    "mine",
    "BlockReason",
]


class BlockReason:
    EFFECT_UNKNOWN = "effect_unknown"
    EFFECT_WRITE = "effect_write"
    EFFECT_CAPABILITY = "effect_capability"
    BARRIER_EVENT = "barrier_event"
    TOO_FEW_BOUNDARIES = "too_few_boundaries"
    UNGROUNDED_SLOT = "ungrounded_slot"
    AMBIGUOUS_SLOT = "ambiguous_slot"
    LIVE_IN_NOT_ENTRY = "live_in_not_in_entry_schema"
    SIZE = "size_out_of_bounds"
    ERROR_EVENT = "error_event"
    LOW_SUPPORT = "low_support"
    PARTIAL_RUN = "partial_run"
    NON_PREFIX_RUNTIME = "non_prefix_runtime"


@dataclass(slots=True)
class WindowStep:
    """One canonicalised step: a tool and the positions where it ran."""

    tool: str
    sig: str
    positions: list[int]
    result_positions: list[int]
    slots: dict[str, Slot] = field(default_factory=dict)

    @property
    def run_length(self) -> int:
        return len(self.positions)


@dataclass(slots=True)
class Window:
    """A candidate region of one episode."""

    patg: PATG
    a: int
    b: int
    steps: list[WindowStep]
    interior_boundaries: int
    live_in: tuple[str, ...]
    live_out: tuple[str, ...]
    canon_hash: str = ""
    group_id: str = ""
    principal: str = ""
    day: str = ""

    @property
    def episode(self) -> Episode:
        return self.patg.episode

    @property
    def n_tool_events(self) -> int:
        return sum(s.run_length for s in self.steps)

    @property
    def removed_requests(self) -> int:
        return self.interior_boundaries

    def tools(self) -> tuple[str, ...]:
        return tuple(s.tool for s in self.steps)


def _hole(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return "none"


def canon_hash(window: Window) -> str:
    """Signature sequence + data-edge topology + live-in/out shape, values held."""

    parts: list[str] = []
    for step in window.steps:
        slot_shape = ",".join(
            f"{path}:{_hole(slot.value)}:{_edge_shape(slot, window)}"
            for path, slot in sorted(step.slots.items())
        )
        parts.append(f"{step.tool}|{slot_shape}|run{'+' if step.run_length > 1 else '1'}")
    li = ",".join(sorted(window.live_in))
    lo = ",".join(sorted(window.live_out))
    blob = ";".join(parts) + f"#LI[{li}]#LO[{lo}]#B{window.interior_boundaries}"
    return hashlib.sha1(blob.encode()).hexdigest()[:12]


def _edge_shape(slot: Slot, window: Window) -> str:
    if slot.mark in (SlotMark.LITERAL, SlotMark.NOT_GROUNDABLE):
        return "const"
    kinds = set()
    for edge in slot.candidates:
        if edge.producer.is_entry_state:
            kinds.add("z" + ("*" if edge.ops else ""))
        elif window.a <= edge.producer.event_index <= window.b:
            kinds.add("in" + ("*" if edge.ops else ""))
        else:
            kinds.add("out" + ("*" if edge.ops else ""))
    return "/".join(sorted(kinds)) or "none"


# ---------------------------------------------------------------------------
# window enumeration
# ---------------------------------------------------------------------------


def enumerate_windows(
    patg: PATG,
    catalog: EffectCatalog,
    *,
    entry_schema: Sequence[str],
    w_min: int = 2,
    w_max: int = 8,
    b_min: int = 2,
    blocked: Counter | None = None,
    blocked_by_tool: Counter | None = None,
) -> list[Window]:
    blocked = blocked if blocked is not None else Counter()
    blocked_by_tool = blocked_by_tool if blocked_by_tool is not None else Counter()
    order = patg.order
    n = len(order)
    out: list[Window] = []
    entry_paths = {f"z.{p}" for p in entry_schema}

    # positions of tool calls, used to bound the double loop
    call_positions = [i for i, e in enumerate(order) if e.kind is EventKind.TOOL_CALL]
    if len(call_positions) < w_min:
        return out

    for a in range(n):
        if order[a].kind is not EventKind.MODEL_REQ:
            continue  # the dispatching boundary is the window's first event
        for b in range(a + 1, n):
            span = order[a : b + 1]
            n_calls = sum(1 for e in span if e.kind is EventKind.TOOL_CALL)
            if n_calls > w_max:
                break
            if n_calls < w_min:
                continue
            if order[b].kind is not EventKind.TOOL_RESULT:
                continue  # regions end on an observation, never mid-call

            reason = _span_block_reason(span, catalog, blocked_by_tool)
            if reason:
                blocked[reason] += 1
                continue

            interior = sum(1 for e in span if e.kind is EventKind.MODEL_REQ)
            if interior < b_min:
                blocked[BlockReason.TOO_FEW_BOUNDARIES] += 1
                continue

            steps = _collapse_steps(patg, a, b)
            if _cuts_a_run(patg, b, steps):
                # A window that ends in the middle of a repeated call has an
                # incoherent loop: its last iteration looks like a termination even
                # though the episode continued. No termination predicate can be
                # consistent with that, so the window is not a candidate at all.
                blocked[BlockReason.PARTIAL_RUN] += 1
                continue
            bad_slot = _slot_block_reason(steps)
            if bad_slot:
                blocked[bad_slot] += 1
                continue

            live_in, live_out, li_ok = _live_in_out(patg, a, b, steps, entry_paths)
            if not li_ok:
                blocked[BlockReason.LIVE_IN_NOT_ENTRY] += 1
                continue

            env = patg.episode.envelope
            w = Window(
                patg=patg,
                a=a,
                b=b,
                steps=steps,
                interior_boundaries=interior,
                live_in=live_in,
                live_out=live_out,
                group_id=env.group_id,
                principal=env.principal,
                day=env.day,
            )
            w.canon_hash = canon_hash(w)
            out.append(w)
    return out


def _cuts_a_run(patg: PATG, b: int, steps: Sequence[WindowStep]) -> bool:
    if not steps:
        return False
    last_tool = steps[-1].tool
    for pos in range(b + 1, len(patg.order)):
        ev = patg.order[pos]
        if ev.kind is EventKind.TOOL_CALL:
            return ev.tool == last_tool
        if ev.kind in (EventKind.HANDOFF, EventKind.APPROVAL):
            return False
    return False


def _span_block_reason(span: Sequence[EventNode], catalog: EffectCatalog, by_tool: Counter) -> str | None:
    for e in span:
        if e.kind in (EventKind.HANDOFF, EventKind.APPROVAL, EventKind.GUARDRAIL):
            return BlockReason.BARRIER_EVENT
        if e.kind is EventKind.TOOL_RESULT and e.status != "ok":
            return BlockReason.ERROR_EVENT
        if e.kind is EventKind.TOOL_CALL:
            spec = catalog.get(e.tool)
            if not spec.compilable:
                by_tool[e.tool or "?"] += 1
                if spec.effect is EffectClass.UNKNOWN:
                    return BlockReason.EFFECT_UNKNOWN
                if not spec.effect.is_read_like:
                    return BlockReason.EFFECT_WRITE
                return BlockReason.EFFECT_CAPABILITY
    return None


def _collapse_steps(patg: PATG, a: int, b: int) -> list[WindowStep]:
    """Collapse consecutive identical tool signatures into one step."""

    steps: list[WindowStep] = []
    by_call_id: dict[str, int] = {}
    unpaired: list[int] = []
    for pos in range(a, b + 1):
        ev = patg.order[pos]
        if ev.kind is EventKind.TOOL_CALL:
            slots = {s.path: s for s in patg.slots_of(pos)}
            sig = f"{ev.tool}|{','.join(sorted(slots))}"
            if steps and steps[-1].sig == sig and steps[-1].tool == ev.tool:
                steps[-1].positions.append(pos)
                for path, slot in slots.items():
                    steps[-1].slots.setdefault(path, slot)
                step_index = len(steps) - 1
            else:
                steps.append(
                    WindowStep(tool=ev.tool or "", sig=sig, positions=[pos], result_positions=[], slots=dict(slots))
                )
                step_index = len(steps) - 1
            if ev.call_id:
                by_call_id[ev.call_id] = step_index
            else:
                unpaired.append(step_index)
        elif ev.kind is EventKind.TOOL_RESULT and steps:
            step_index = by_call_id.pop(ev.call_id, None) if ev.call_id else None
            if step_index is None and unpaired:
                step_index = unpaired.pop(0)
            if step_index is not None:
                steps[step_index].result_positions.append(pos)
    return steps


def _slot_block_reason(steps: Sequence[WindowStep]) -> str | None:
    for step in steps:
        for slot in step.slots.values():
            if slot.mark == SlotMark.UNGROUNDED:
                return BlockReason.UNGROUNDED_SLOT
            if slot.mark == SlotMark.AMBIGUOUS:
                return BlockReason.AMBIGUOUS_SLOT
    return None


def _live_in_out(
    patg: PATG,
    a: int,
    b: int,
    steps: Sequence[WindowStep],
    entry_paths: set[str],
) -> tuple[tuple[str, ...], tuple[str, ...], bool]:
    """Equation (3) plus the Eq. (4) entry-schema admissibility test."""

    live_in: set[str] = set()
    ok = True
    for step in steps:
        for slot in step.slots.values():
            if slot.mark in (SlotMark.LITERAL, SlotMark.NOT_GROUNDABLE):
                continue
            in_region = [e for e in slot.candidates if a <= e.producer.event_index <= b]
            if in_region:
                continue
            entry = [e for e in slot.candidates if e.producer.is_entry_state]
            if not entry:
                ok = False  # produced before the region by a non-entry-state event
                continue
            for edge in entry:
                path = f"z.{edge.producer.path}" if not edge.producer.path.startswith("z") else edge.producer.path
                base = _allowlist_base(path, entry_paths)
                if base is None:
                    ok = False
                else:
                    live_in.add(base)

    live_out: set[str] = set()
    for step in steps:
        live_out.add(step.tool)
    for (idx, path), slot in patg.slots.items():
        if idx <= b:
            continue
        for edge in slot.candidates:
            if a <= edge.producer.event_index <= b and edge.producer.tool:
                live_out.add(edge.producer.tool)
    return tuple(sorted(live_in)), tuple(sorted(live_out)), ok


def _allowlist_base(path: str, entry_paths: set[str]) -> str | None:
    """Longest allowlisted prefix of an entry-state path, or ``None``."""

    if path in entry_paths:
        return path
    for allowed in entry_paths:
        if path.startswith(allowed + ".") or path.startswith(allowed + "["):
            return allowed
    return None


# ---------------------------------------------------------------------------
# families
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Family:
    """A set of windows sharing a canonical shape (or a merged branch pair)."""

    canon_hash: str
    windows: list[Window] = field(default_factory=list)
    variant_hashes: tuple[str, ...] = ()
    divergence_step: int | None = None
    loop_step: int | None = None

    # -- support ---------------------------------------------------------
    @property
    def groups(self) -> set[str]:
        return {w.group_id for w in self.windows}

    @property
    def principals(self) -> set[str]:
        return {w.principal for w in self.windows}

    @property
    def days(self) -> set[str]:
        return {w.day for w in self.windows}

    @property
    def support(self) -> int:
        return len(self.groups)

    @property
    def mean_removed(self) -> float:
        return sum(w.removed_requests for w in self.windows) / max(1, len(self.windows))

    @property
    def tools(self) -> tuple[str, ...]:
        """Longest observed tool sequence: for a merged family, the taken arm."""

        if not self.windows:
            return ()
        return max((w.tools() for w in self.windows), key=len)

    @property
    def base_window(self) -> Window:
        """The window whose shape the program is built from (longest arm)."""

        return max(self.windows, key=lambda w: (len(w.steps), w.n_tool_events))

    def branch_entropy(self) -> float:
        import math

        if not self.variant_hashes:
            return 0.0
        counts = Counter(w.canon_hash for w in self.windows)
        n = sum(counts.values())
        return -sum((c / n) * math.log2(c / n) for c in counts.values())

    def risk(self) -> float:
        """Effect risk proxy: fraction of steps that are external reads."""

        if not self.windows:
            return 0.0
        tools = self.windows[0].tools()
        return sum(1 for t in tools if "." in t) / max(1, len(tools))

    def score(self, *, c_m: float = 1.0, l1: float = 1.0, l2: float = 0.5, l3: float = 0.05) -> float:
        """Equation (16)."""

        size = sum(len(s.slots) + 1 for s in self.windows[0].steps) if self.windows else 0
        return self.support * self.mean_removed * c_m - l1 * self.branch_entropy() - l2 * self.risk() - l3 * size

    def by_group(self) -> dict[str, list[Window]]:
        out: dict[str, list[Window]] = defaultdict(list)
        for w in self.windows:
            out[w.group_id].append(w)
        return dict(out)


@dataclass(slots=True)
class MiningResult:
    families: list[Family] = field(default_factory=list)
    rejected_families: list[tuple[Family, str]] = field(default_factory=list)
    blocked: Counter = field(default_factory=Counter)
    blocked_by_tool: Counter = field(default_factory=Counter)
    n_windows: int = 0
    n_episodes: int = 0

    @property
    def blocked_total(self) -> int:
        return sum(self.blocked.values())

    def blocked_shares(self) -> dict[str, float]:
        total = self.blocked_total + self.n_windows
        if not total:
            return {}
        return {k: v / total for k, v in self.blocked.most_common()}


def mine(
    graphs: Sequence[PATG],
    catalog: EffectCatalog,
    *,
    entry_schema: Sequence[str],
    w_min: int = 2,
    w_max: int = 8,
    b_min: int = 2,
    s_min: int = 5,
    min_principals: int = 1,
    min_days: int = 1,
    merge_branches: bool = True,
    prefix_only: bool = False,
) -> MiningResult:
    res = MiningResult(n_episodes=len(graphs))
    by_hash: dict[str, Family] = {}
    for patg in graphs:
        wins = enumerate_windows(
            patg,
            catalog,
            entry_schema=entry_schema,
            w_min=w_min,
            w_max=w_max,
            b_min=b_min,
            blocked=res.blocked,
            blocked_by_tool=res.blocked_by_tool,
        )
        if prefix_only:
            suffixes = [window for window in wins if window.a != 0]
            if suffixes:
                res.blocked[BlockReason.NON_PREFIX_RUNTIME] += len(suffixes)
            wins = [window for window in wins if window.a == 0]
        res.n_windows += len(wins)
        # keep at most one window per (episode, hash): the largest
        best: dict[str, Window] = {}
        for w in wins:
            cur = best.get(w.canon_hash)
            if cur is None or w.n_tool_events > cur.n_tool_events:
                best[w.canon_hash] = w
        for h, w in best.items():
            fam = by_hash.setdefault(h, Family(canon_hash=h))
            fam.windows.append(w)

    families = list(by_hash.values())
    for fam in families:
        lengths = {tuple(s.run_length for s in w.steps) for w in fam.windows}
        if any(any(n > 1 for n in L) for L in lengths):
            for i, step in enumerate(fam.windows[0].steps):
                if step.run_length > 1:
                    fam.loop_step = i
                    break

    if merge_branches:
        families = _merge_branch_families(families)

    accepted: list[Family] = []
    for fam in families:
        if fam.support < s_min:
            res.rejected_families.append((fam, f"{BlockReason.LOW_SUPPORT}:groups={fam.support}"))
        elif len(fam.principals) < min_principals:
            res.rejected_families.append((fam, f"{BlockReason.LOW_SUPPORT}:principals={len(fam.principals)}"))
        elif len(fam.days) < min_days:
            res.rejected_families.append((fam, f"{BlockReason.LOW_SUPPORT}:days={len(fam.days)}"))
        else:
            accepted.append(fam)

    accepted.sort(key=lambda f: f.score(), reverse=True)
    res.families = accepted
    return res


def _called_after(window: Window, tool: str) -> bool:
    """Did the episode call ``tool`` after this window ended?

    The branch label must come from the baseline's observable behaviour, not from
    window admissibility. An episode that *did* take the long arm but whose long-arm
    window was blocked (an extra candidate producer pushed a slot over κ, a tool
    errored) would otherwise be labelled as the short arm, and that label noise
    makes every divergence look unexplainable. Such episodes are excluded from the
    family rather than mislabelled — support drops, correctness does not.
    """

    for pos in range(window.b + 1, len(window.patg.order)):
        ev = window.patg.order[pos]
        if ev.kind is EventKind.TOOL_CALL and ev.tool == tool:
            return True
    return False


def _merge_branch_families(families: Sequence[Family]) -> list[Family]:
    """Merge windows whose tool sequence extends another's by one step.

    ``AddControlEdges`` in the published listing adds a control edge when a slot's
    signature covaries within a family. The observable form of that in a linearised
    trace is one window sequence being a one-step extension of another; merging
    them creates the divergence point that Algorithm 4 then tries to explain. If it
    cannot, the merged candidate is dropped and the prefix family survives alone.

    Merging works on *tool sequences*, not on canonical hashes. Hash fragmentation
    (the same arm appearing under two hashes because one episode had an extra
    candidate producer) would otherwise leave an episode in the short arm even
    though it took the long one, and that label noise makes every divergence look
    unexplainable.
    """

    windows_by_seq: dict[tuple[str, ...], list[Window]] = defaultdict(list)
    for fam in families:
        for w in fam.windows:
            windows_by_seq[w.tools()].append(w)

    merged: list[Family] = []
    for long_seq, long_ws in windows_by_seq.items():
        if len(long_seq) < 2:
            continue
        short_seq = long_seq[:-1]
        short_ws = windows_by_seq.get(short_seq)
        if not short_ws:
            continue
        long_eps = {w.episode.episode_id for w in long_ws}
        short_only = [
            w
            for w in short_ws
            if w.episode.episode_id not in long_eps and not _called_after(w, long_seq[-1])
        ]
        if not short_only or len(long_ws) < 2:
            continue
        per_episode: dict[str, Window] = {}
        for w in list(long_ws) + short_only:
            cur = per_episode.get(w.episode.episode_id)
            if cur is None or len(w.steps) > len(cur.steps):
                per_episode[w.episode.episode_id] = w
        combined = list(per_episode.values())
        if len({len(w.steps) for w in combined}) < 2:
            continue
        merged.append(
            Family(
                canon_hash="merge:" + hashlib.sha1(("|".join(long_seq)).encode()).hexdigest()[:10],
                windows=combined,
                variant_hashes=tuple(sorted({w.canon_hash for w in combined}))[:8],
                divergence_step=len(short_seq),
            )
        )

    extra = sorted(merged, key=lambda f: f.support, reverse=True)[:24]
    return list(families) + extra
