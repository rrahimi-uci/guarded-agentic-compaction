#!/usr/bin/env python3
"""Provider-free census of *interior* read-only regions in released agent trajectories.

P0 of ``gac-expansion.md`` (hypothesis H1), registered in
``paper/supplementary/interior-region-census-protocol.md``.  The prefix census
(``prefix_census.py``) asks how often trajectories *open* with a groundable read-only prefix;
this script asks how often they contain one *later*: at a model boundary after the opening,
and in particular beyond the first barrier (write, unknown effect, user turn or error) that
ends the read-only opening, which is the population the shipped prefix-only compiler can
never reach.

Same corpora, pinned revisions, signed catalogs, mining parameters and grounding rule as the
prefix census.  Two deliberate extensions, both declared in the protocol: trajectories are
ingested up to ``MAX_CALLS_INTERIOR`` calls with no barrier stop, and windows may start at any
boundary.  Each window is tested under two live-in policies: ``strict`` (entry schema only,
the shipped ``_live_in_out`` rule) and ``projected`` (live-ins may also be earlier tool
results outside the window, recorded as ``prior:<tool>``).

Usage::

    python paper/scripts/interior_census.py smoke --source-root <dir> [--corpora ...]
    python paper/scripts/interior_census.py run   --source-root <dir> [--corpora ...]
    python paper/scripts/interior_census.py table
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from benchmarks.external import trajectories as traj  # noqa: E402
from guarded_agentic_compaction.graph.provenance import (  # noqa: E402
    PATG,
    GroundabilityPolicy,
    SlotMark,
    build_patg,
)
from guarded_agentic_compaction.graph import windows as win  # noqa: E402
from guarded_agentic_compaction.grc.dsl import SynthContext  # noqa: E402
from guarded_agentic_compaction.schema.effects import EffectCatalog, EffectClass  # noqa: E402
from guarded_agentic_compaction.schema.traces import Episode, EventKind  # noqa: E402


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


pc = _load_script("prefix_census")

OUT_DIR = ROOT / "paper" / "results" / "interior_census"
RESULTS_PATH = OUT_DIR / "results.json"
TABLE_PATH = ROOT / "paper" / "iclr" / "tables" / "interior_census.tex"
PROTOCOL_PATH = ROOT / "paper" / "supplementary" / "interior-region-census-protocol.md"
DECOMPOSITION_PATH = OUT_DIR / "decomposition.json"
DECOMPOSITION_NOTE_PATH = ROOT / "paper" / "supplementary" / "interior-region-census-decomposition.md"
#: Post-hoc decomposition sample divisors (descriptive; see the decomposition note).
DECOMPOSE_K = {"taubench": 1, "openhands": 16, "sweagent": 64}

MINING = dict(pc.MINING)
MAX_CALLS_INTERIOR = 60
SMOKE_TRAJECTORIES = 200
RUNTIME_BUDGET_SECONDS = 90 * 60
#: H1 thresholds, copied from gac-expansion.md section 0.
H1_SHARE = 0.20
H1_FLOOR = 92
POLICIES = ("strict", "projected")
SNAPSHOT_DATE = "2026-11-08"


# ---------------------------------------------------------------------------
# sampling and verification
# ---------------------------------------------------------------------------


def keep(episode_id: str, k: int) -> bool:
    """Deterministic 1-in-k sample on the SHA-1 of the episode id (k = 1 keeps all)."""

    if k <= 1:
        return True
    return int(hashlib.sha1(episode_id.encode()).hexdigest(), 16) % k == 0


def verify_sources(name: str, source_root: Path) -> dict[str, Any]:
    """Every file named in the pinned source manifest must be present with its SHA-256."""

    manifest = json.loads((pc.DATASETS_DIR / name / "source_manifest.json").read_text(encoding="utf-8"))
    root = source_root / name
    checked: dict[str, str] = {}
    for rel, meta in manifest["files"].items():
        path = root / rel
        if not path.exists():
            raise SystemExit(f"{name}: missing {rel} under {root}")
        digest = pc._sha256(path)
        if digest != meta["sha256"]:
            raise SystemExit(f"{name}: SHA-256 mismatch for {rel}: {digest} != {meta['sha256']}")
        checked[rel] = digest
    return {"revision": manifest["revision"], "files_verified": len(checked), "sha256": checked}


# ---------------------------------------------------------------------------
# frontier and interior read-only runs (catalog only)
# ---------------------------------------------------------------------------


def frontier_position(patg: PATG, catalog: EffectCatalog, *, pass_through_pure: bool = False) -> int | None:
    """Index in canonical order of the first event that ends the read-only opening.

    A non-compilable call, a HANDOFF/APPROVAL/GUARDRAIL, or a failed result.  ``None`` when
    the whole ingested trajectory is read-only.  With ``pass_through_pure`` (the post-hoc
    decomposition only), a call whose catalogued effect is ``PURE`` and its result do not end
    the opening; the registered census never sets it.
    """

    for pos, ev in enumerate(patg.order):
        if ev.kind in (EventKind.HANDOFF, EventKind.APPROVAL, EventKind.GUARDRAIL):
            return pos
        if ev.kind in (EventKind.TOOL_CALL, EventKind.TOOL_RESULT) and pass_through_pure \
                and catalog.effect_of(ev.tool) is EffectClass.PURE:
            continue
        if ev.kind is EventKind.TOOL_CALL and not catalog.compilable(ev.tool):
            return pos
        if ev.kind is EventKind.TOOL_RESULT and ev.status != "ok":
            return pos
    return None


def _frontier_label(patg: PATG, frontier: int | None) -> str:
    if frontier is None:
        return "none"
    ev = patg.order[frontier]
    if ev.kind is EventKind.TOOL_CALL:
        return ev.tool or "?"
    if ev.kind is EventKind.TOOL_RESULT:
        return f"failed:{ev.tool or '?'}"
    return ev.kind.name


def interior_read_only_runs(patg: PATG, catalog: EffectCatalog) -> list[tuple[int, int]]:
    """``(boundary_position, run_length)`` for every interior boundary.

    The run counts consecutive compilable calls from the boundary until a barrier event, a
    non-compilable call or a failed result.
    """

    order = patg.order
    runs: list[tuple[int, int]] = []
    for a in patg.boundaries[1:]:
        depth = 0
        for pos in range(a + 1, len(order)):
            ev = order[pos]
            if ev.kind in (EventKind.HANDOFF, EventKind.APPROVAL, EventKind.GUARDRAIL):
                break
            if ev.kind is EventKind.TOOL_CALL:
                if not catalog.compilable(ev.tool):
                    break
                depth += 1
            elif ev.kind is EventKind.TOOL_RESULT and ev.status != "ok":
                break
        runs.append((a, depth))
    return runs


# ---------------------------------------------------------------------------
# interior windows under two live-in policies
# ---------------------------------------------------------------------------


def _live_ins(
    patg: PATG, a: int, b: int, steps, entry_paths: set[str], policy: str
) -> tuple[tuple[str, ...], bool]:
    """Live-ins of a window under ``strict`` (entry only) or ``projected`` (entry or prior result)."""

    live_in: set[str] = set()
    ok = True
    for step in steps:
        for slot in step.slots.values():
            if slot.mark in (SlotMark.LITERAL, SlotMark.NOT_GROUNDABLE):
                continue
            if any(a <= e.producer.event_index <= b for e in slot.candidates):
                continue
            entry = [e for e in slot.candidates if e.producer.is_entry_state]
            prior = [e for e in slot.candidates if not e.producer.is_entry_state and e.producer.event_index < a]
            resolved = False
            for edge in entry:
                path = f"z.{edge.producer.path}" if not edge.producer.path.startswith("z") else edge.producer.path
                base = win._allowlist_base(path, entry_paths)
                if base is not None:
                    live_in.add(base)
                    resolved = True
            if not resolved and policy == "projected":
                for edge in prior:
                    live_in.add(f"prior:{edge.producer.tool or '?'}")
                    resolved = True
            if not resolved:
                ok = False
    return tuple(sorted(live_in)), ok


def enumerate_interior_windows(
    patg: PATG,
    catalog: EffectCatalog,
    *,
    entry_schema: Iterable[str],
    policy: str,
    w_min: int,
    w_max: int,
    b_min: int,
    blocked: Counter,
) -> list[win.Window]:
    """Algorithm 2's window enumeration restricted to interior boundaries, with a live-in policy.

    Mirrors :func:`graph.windows.enumerate_windows` step for step (span block reasons,
    boundary count, partial-run rule, slot marks) and differs only in (i) skipping the first
    boundary and (ii) the live-in rule.
    """

    order = patg.order
    n = len(order)
    entry_paths = {f"z.{p}" for p in entry_schema}
    out: list[win.Window] = []
    call_positions = [i for i, e in enumerate(order) if e.kind is EventKind.TOOL_CALL]
    if len(call_positions) < w_min:
        return out
    for a in patg.boundaries[1:]:
        for b in range(a + 1, n):
            span = order[a : b + 1]
            n_calls = sum(1 for e in span if e.kind is EventKind.TOOL_CALL)
            if n_calls > w_max:
                break
            if n_calls < w_min:
                continue
            if order[b].kind is not EventKind.TOOL_RESULT:
                continue
            reason = win._span_block_reason(span, catalog, Counter())
            if reason:
                blocked[reason] += 1
                if reason in (win.BlockReason.BARRIER_EVENT, win.BlockReason.EFFECT_WRITE,
                              win.BlockReason.EFFECT_UNKNOWN, win.BlockReason.EFFECT_CAPABILITY):
                    break  # every longer span from this boundary contains the same barrier
                continue
            interior = sum(1 for e in span if e.kind is EventKind.MODEL_REQ)
            if interior < b_min:
                blocked[win.BlockReason.TOO_FEW_BOUNDARIES] += 1
                continue
            steps = win._collapse_steps(patg, a, b)
            if win._cuts_a_run(patg, b, steps):
                blocked[win.BlockReason.PARTIAL_RUN] += 1
                continue
            bad = win._slot_block_reason(steps)
            if bad:
                blocked[bad] += 1
                continue
            live_in, ok = _live_ins(patg, a, b, steps, entry_paths, policy)
            if not ok:
                blocked[win.BlockReason.LIVE_IN_NOT_ENTRY] += 1
                continue
            env = patg.episode.envelope
            window = win.Window(
                patg=patg, a=a, b=b, steps=steps, interior_boundaries=interior,
                live_in=live_in, live_out=tuple(sorted(s.tool for s in steps)),
                group_id=env.group_id, principal=env.principal, day=env.day,
            )
            window.canon_hash = win.canon_hash(window)
            out.append(window)
    return out


# ---------------------------------------------------------------------------
# the census over one corpus, one catalog, both policies
# ---------------------------------------------------------------------------


def census(
    episodes: Callable[[], Iterator[Episode]],
    catalog: EffectCatalog,
    *,
    corpus: str,
    arm: str,
    sample: dict[str, Any],
) -> dict[str, Any]:
    started = time.perf_counter()
    stats = pc.HashedFieldStats()
    n_pass1 = 0
    for episode in episodes():
        pc.observe_episode(stats, episode)
        n_pass1 += 1
    policy = GroundabilityPolicy.from_catalog(catalog, stats=stats)
    ctx = SynthContext(max_depth=MINING["max_depth"])

    traces = 0
    groups: set[str] = set()
    stopped_by: Counter = Counter()
    calls_total: list[int] = []
    calls_ingested: list[int] = []
    boundaries_per_trace: list[int] = []
    frontier_at_call: list[int | None] = []
    all_read_only = 0
    ro_max_run: list[int] = []
    ro_runs_ge2: list[int] = []
    ro_beyond_max_run: list[int] = []
    per_policy: dict[str, dict[str, Any]] = {}
    for pol in POLICIES:
        per_policy[pol] = {
            "blocked": Counter(),
            "gr_any_len": [],        # longest interior groundable window per trace (0 if none)
            "gr_beyond_len": [],     # longest beyond-frontier groundable window per trace
            "removed": [],           # interior_boundaries of the best beyond-frontier window
            "start_call_index": [],  # call index (0-based) at which the best beyond-frontier window starts
            "fam_groups_any": defaultdict(set),
            "fam_groups_beyond": defaultdict(set),
            "fam_episodes_beyond": Counter(),
            "fam_shape": {},
            "live_in_kinds": Counter(),
        }

    for episode in episodes():
        traces += 1
        groups.add(episode.group_id)
        stopped_by[str(episode.attributes.get("ingestion_stopped_by"))] += 1
        calls_total.append(int(episode.attributes.get("n_calls_total", 0)))
        calls_ingested.append(int(episode.attributes.get("n_calls_ingested", 0)))
        graph = build_patg(episode, catalog, policy, max_depth=MINING["max_depth"], kappa=MINING["kappa"], ctx=ctx)
        boundaries_per_trace.append(len(graph.boundaries))
        frontier = frontier_position(graph, catalog)
        if frontier is None:
            all_read_only += 1
            frontier_at_call.append(None)
        else:
            frontier_at_call.append(sum(1 for e in graph.order[:frontier] if e.kind is EventKind.TOOL_CALL))
        runs = interior_read_only_runs(graph, catalog)
        ro_max_run.append(max((d for _, d in runs), default=0))
        ro_runs_ge2.append(sum(1 for _, d in runs if d >= 2))
        ro_beyond_max_run.append(max((d for a, d in runs if frontier is not None and a > frontier), default=0))
        call_index_of = {pos: i for i, pos in enumerate(p for p, e in enumerate(graph.order) if e.kind is EventKind.TOOL_CALL)}
        for pol in POLICIES:
            acc = per_policy[pol]
            wins = enumerate_interior_windows(
                graph, catalog, entry_schema=MINING["entry_schema"], policy=pol,
                w_min=MINING["w_min"], w_max=MINING["w_max"], b_min=MINING["b_min"], blocked=acc["blocked"],
            )
            beyond = [w for w in wins if frontier is not None and w.a > frontier]
            acc["gr_any_len"].append(max((w.n_tool_events for w in wins), default=0))
            acc["gr_beyond_len"].append(max((w.n_tool_events for w in beyond), default=0))
            if beyond:
                best_w = max(beyond, key=lambda w: (w.n_tool_events, w.interior_boundaries))
                acc["removed"].append(best_w.interior_boundaries)
                first_call = next(p for p in range(best_w.a, best_w.b + 1) if graph.order[p].kind is EventKind.TOOL_CALL)
                acc["start_call_index"].append(call_index_of[first_call])
                for li in best_w.live_in:
                    acc["live_in_kinds"]["prior" if li.startswith("prior:") else "entry"] += 1
            best_any: dict[str, win.Window] = {}
            for w in wins:
                cur = best_any.get(w.canon_hash)
                if cur is None or w.n_tool_events > cur.n_tool_events:
                    best_any[w.canon_hash] = w
            for canon, w in best_any.items():
                acc["fam_groups_any"][canon].add(w.group_id)
            best_beyond: dict[str, win.Window] = {}
            for w in beyond:
                cur = best_beyond.get(w.canon_hash)
                if cur is None or w.n_tool_events > cur.n_tool_events:
                    best_beyond[w.canon_hash] = w
            for canon, w in best_beyond.items():
                acc["fam_groups_beyond"][canon].add(w.group_id)
                acc["fam_episodes_beyond"][canon] += 1
                acc["fam_shape"].setdefault(canon, {
                    "tools": list(w.tools()),
                    "run_lengths": [s.run_length for s in w.steps],
                    "length": w.n_tool_events,
                    "live_in": list(w.live_in),
                    "removed_requests": w.interior_boundaries,
                })

    def share(values: list[int], threshold: int = 2) -> float | None:
        return (sum(1 for v in values if v >= threshold) / traces) if traces else None

    policies_out: dict[str, Any] = {}
    for pol in POLICIES:
        acc = per_policy[pol]
        sup_any = {c: len(g) for c, g in acc["fam_groups_any"].items()}
        sup_beyond = {c: len(g) for c, g in acc["fam_groups_beyond"].items()}
        n_max_beyond = max(sup_beyond.values(), default=0)
        top = sorted(sup_beyond.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
        beyond_share = share(acc["gr_beyond_len"])
        policies_out[pol] = {
            "interior_groundable_ge2": {
                "share": share(acc["gr_any_len"]),
                "count": sum(1 for v in acc["gr_any_len"] if v >= 2),
                "histogram": pc._histogram(acc["gr_any_len"]),
            },
            "beyond_frontier_groundable_ge2": {
                "share": beyond_share,
                "count": sum(1 for v in acc["gr_beyond_len"] if v >= 2),
                "histogram": pc._histogram(acc["gr_beyond_len"]),
                "length_among_ge2": pc._distribution([v for v in acc["gr_beyond_len"] if v >= 2]),
                "removed_requests": pc._distribution(acc["removed"]),
                "start_call_index": pc._distribution(acc["start_call_index"]),
                "live_in_kinds": dict(acc["live_in_kinds"]),
            },
            "blocked_window_candidates": pc._sorted_counter(acc["blocked"]),
            "families_any_interior": {"n": len(sup_any), "n_max": max(sup_any.values(), default=0)},
            "families_beyond_frontier": {
                "n": len(sup_beyond),
                "at_floor_ge3": sum(1 for v in sup_beyond.values() if v >= 3),
                "at_or_above_92": sum(1 for v in sup_beyond.values() if v >= H1_FLOOR),
                "n_max": n_max_beyond,
                "top": [
                    {"family_hash": c, "support": s, "episodes": acc["fam_episodes_beyond"][c], **acc["fam_shape"][c]}
                    for c, s in top
                ],
            },
            "h1": {
                "share_threshold": H1_SHARE,
                "floor": H1_FLOOR,
                "share_ok": (beyond_share or 0.0) >= H1_SHARE,
                "floor_ok": n_max_beyond >= H1_FLOOR,
                "pass": ((beyond_share or 0.0) >= H1_SHARE) and n_max_beyond >= H1_FLOOR,
            },
        }

    return {
        "corpus": corpus,
        "arm": arm,
        "catalog_version": catalog.catalog_version,
        "sample": sample,
        "traces": traces,
        "groups": len(groups),
        "calls_per_trace": pc._distribution(calls_total),
        "calls_ingested_per_trace": pc._distribution(calls_ingested),
        "boundaries_per_trace": pc._distribution(boundaries_per_trace),
        "ingestion": {"max_calls": MAX_CALLS_INTERIOR, "stopped_by": pc._sorted_counter(stopped_by), "pass1_episodes": n_pass1},
        "frontier": {
            "all_read_only_within_ingested": all_read_only,
            "share_all_read_only": all_read_only / traces if traces else None,
            "frontier_call_index": pc._distribution([v for v in frontier_at_call if v is not None]),
        },
        "interior_read_only_runs": {
            "share_any_run_ge2": share(ro_max_run),
            "share_beyond_frontier_run_ge2": share(ro_beyond_max_run),
            "runs_ge2_per_trace": pc._distribution(ro_runs_ge2),
            "max_run_histogram": pc._histogram(ro_max_run),
        },
        "policies": policies_out,
        "runtime_seconds": round(time.perf_counter() - started, 1),
    }


# ---------------------------------------------------------------------------
# post-hoc frontier decomposition (descriptive; does not decide H1)
# ---------------------------------------------------------------------------


def _capped_histogram(values: list[int], cap: int = 20) -> dict[str, int]:
    counts: Counter = Counter()
    for v in values:
        counts[str(v) if v < cap else f"{cap}+"] += 1
    return {k: counts[k] for k in sorted(counts, key=lambda x: (x.endswith("+"), int(x.rstrip("+"))))}


def decompose(
    episodes: Callable[[], Iterator[Episode]],
    catalog: EffectCatalog,
    *,
    corpus: str,
    sample: dict[str, Any],
) -> dict[str, Any]:
    """Frontier decomposition under the projected policy: which event ends the opening, how far
    beyond it the best groundable region starts, and the share/family support when ``PURE``
    model-side calls do not end the opening."""

    started = time.perf_counter()
    stats = pc.HashedFieldStats()
    for episode in episodes():
        pc.observe_episode(stats, episode)
    policy = GroundabilityPolicy.from_catalog(catalog, stats=stats)
    ctx = SynthContext(max_depth=MINING["max_depth"])

    traces = 0
    groups: set[str] = set()
    frontier_events: Counter = Counter()
    frontier_events_pt: Counter = Counter()
    frontier_call_std: list[int] = []
    frontier_call_pt: list[int] = []
    distance: list[int] = []
    start_std: list[int] = []
    start_pt: list[int] = []
    beyond_std: list[int] = []
    beyond_pt: list[int] = []
    fam_std: dict[str, set[str]] = defaultdict(set)
    fam_pt: dict[str, set[str]] = defaultdict(set)
    blocked: Counter = Counter()
    for episode in episodes():
        traces += 1
        groups.add(episode.group_id)
        graph = build_patg(episode, catalog, policy, max_depth=MINING["max_depth"], kappa=MINING["kappa"], ctx=ctx)
        call_index_of = {pos: i for i, pos in enumerate(p for p, e in enumerate(graph.order) if e.kind is EventKind.TOOL_CALL)}
        wins = enumerate_interior_windows(
            graph, catalog, entry_schema=MINING["entry_schema"], policy="projected",
            w_min=MINING["w_min"], w_max=MINING["w_max"], b_min=MINING["b_min"], blocked=blocked,
        )

        def first_call(w: win.Window) -> int:
            return call_index_of[next(p for p in range(w.a, w.b + 1) if graph.order[p].kind is EventKind.TOOL_CALL)]

        def calls_before(pos: int) -> int:
            return sum(1 for e in graph.order[:pos] if e.kind is EventKind.TOOL_CALL)

        for pt, events, fcalls, starts, beyond_len, fams in (
            (False, frontier_events, frontier_call_std, start_std, beyond_std, fam_std),
            (True, frontier_events_pt, frontier_call_pt, start_pt, beyond_pt, fam_pt),
        ):
            frontier = frontier_position(graph, catalog, pass_through_pure=pt)
            events[_frontier_label(graph, frontier)] += 1
            beyond = [w for w in wins if frontier is not None and w.a > frontier]
            beyond_len.append(max((w.n_tool_events for w in beyond), default=0))
            if frontier is not None:
                fcalls.append(calls_before(frontier))
            if beyond:
                best = max(beyond, key=lambda w: (w.n_tool_events, w.interior_boundaries))
                starts.append(first_call(best))
                if not pt:
                    # calls strictly between the frontier call and the region's first call, plus one
                    distance.append(first_call(best) - calls_before(frontier))
            best_by_hash: dict[str, win.Window] = {}
            for w in beyond:
                cur = best_by_hash.get(w.canon_hash)
                if cur is None or w.n_tool_events > cur.n_tool_events:
                    best_by_hash[w.canon_hash] = w
            for canon, w in best_by_hash.items():
                fams[canon].add(w.group_id)

    def summary(beyond_len: list[int], fams: dict[str, set[str]], starts: list[int]) -> dict[str, Any]:
        count = sum(1 for v in beyond_len if v >= 2)
        sup = {c: len(g) for c, g in fams.items()}
        n_max = max(sup.values(), default=0)
        share = count / traces if traces else None
        return {
            "beyond_frontier_groundable_ge2": {"count": count, "share": share},
            "families_beyond_frontier": {"n": len(sup), "n_max": n_max,
                                         "at_or_above_92": sum(1 for v in sup.values() if v >= H1_FLOOR)},
            "start_call_index_histogram": _capped_histogram(starts),
            "h1_flags_descriptive": {"share_ok": (share or 0.0) >= H1_SHARE, "floor_ok": n_max >= H1_FLOOR},
        }

    std = summary(beyond_std, fam_std, start_std)
    pt = summary(beyond_pt, fam_pt, start_pt)
    n_std = std["beyond_frontier_groundable_ge2"]["count"]
    n_pt = pt["beyond_frontier_groundable_ge2"]["count"]
    return {
        "corpus": corpus,
        "policy": "projected",
        "catalog_version": catalog.catalog_version,
        "sample": sample,
        "traces": traces,
        "groups": len(groups),
        "frontier_event": pc._sorted_counter(frontier_events),
        "frontier_call_index_histogram": _capped_histogram(frontier_call_std),
        "registered_frontier": std,
        "distance_from_frontier_histogram": _capped_histogram(distance),
        "distance_from_frontier_le1_share_among_ge2": (sum(1 for d in distance if d <= 1) / n_std) if n_std else None,
        "pass_through_pure_frontier": {
            **pt,
            "frontier_event": pc._sorted_counter(frontier_events_pt),
            "frontier_call_index_histogram": _capped_histogram(frontier_call_pt),
        },
        "attributable_to_pure_calls": {
            "traces": n_std - n_pt,
            "share_points": ((n_std - n_pt) / traces) if traces else None,
        },
        "runtime_seconds": round(time.perf_counter() - started, 1),
    }


# ---------------------------------------------------------------------------
# corpus wiring
# ---------------------------------------------------------------------------


def _episode_factory(
    name: str, source_root: Path, catalog: EffectCatalog, *, k: int, limit: int | None, folded: bool = False
) -> Callable[[], Iterator[Episode]]:
    spec = pc.CORPORA[name]
    manifest = traj.census_manifest(
        name, revision=spec["revision"], catalog_version=catalog.catalog_version, tools=spec["tools"],
        scaffold=spec["scaffold"], entry_contract=spec["entry_contract"] + ("-folded" if folded else "") + "-interior",
    )

    def factory() -> Iterator[Episode]:
        kept = 0
        for record in pc._records(name, source_root, limit=None, folded=folded):
            if not keep(record.episode_id, k):
                continue
            kept += 1
            if limit is not None and kept > limit:
                return
            yield traj.build_episode(record, manifest, tools=spec["tools"], max_calls=MAX_CALLS_INTERIOR, barrier=None)

    return factory


def smoke(name: str, source_root: Path) -> dict[str, Any]:
    """Seconds per trajectory on the first SMOKE_TRAJECTORIES records (primary catalog, both policies)."""

    spec = pc.CORPORA[name]
    catalog = pc.load_catalog(spec["catalog"])
    started = time.perf_counter()
    row = census(_episode_factory(name, source_root, catalog, k=1, limit=SMOKE_TRAJECTORIES), catalog,
                 corpus=name, arm="smoke", sample={"k": 1, "limit": SMOKE_TRAJECTORIES})
    seconds = time.perf_counter() - started
    total = count_records(name, source_root)
    per = seconds / max(1, row["traces"])
    k = 1
    arms = 2  # primary and sensitivity arm
    while per * (total / k) * arms > RUNTIME_BUDGET_SECONDS:
        k *= 2
    return {"corpus": name, "smoke_traces": row["traces"], "smoke_seconds": round(seconds, 1),
            "seconds_per_trace": round(per, 4), "total_records": total, "budget_seconds": RUNTIME_BUDGET_SECONDS,
            "arms": arms, "k": k, "expected_sample": total // k}


def count_records(name: str, source_root: Path) -> int:
    return sum(1 for _ in pc._records(name, source_root, limit=None))


def run_corpus(name: str, source_root: Path, *, k: int, smoke_row: dict[str, Any] | None) -> list[dict[str, Any]]:
    spec = pc.CORPORA[name]
    sources = verify_sources(name, source_root)
    primary = pc.load_catalog(spec["catalog"])
    sample = {"rule": "keep iff sha1(episode_id) mod k == 0", "k": k, "smoke": smoke_row}
    rows = [census(_episode_factory(name, source_root, primary, k=k, limit=None), primary,
                   corpus=name, arm="primary", sample=sample)]
    arm = spec["arm"]
    if "flip_to_read" in arm:
        arm_catalog = pc.load_catalog(spec["catalog"], flip_to_read=arm["flip_to_read"])
        rows.append(census(_episode_factory(name, source_root, arm_catalog, k=k, limit=None), arm_catalog,
                           corpus=name, arm=arm["name"], sample=sample))
    else:
        rows.append(census(_episode_factory(name, source_root, primary, k=k, limit=None, folded=True), primary,
                           corpus=name, arm=arm["name"], sample=sample))
    catalog_path = pc.CATALOG_DIR / f"{spec['catalog']}.yaml"
    for row in rows:
        row.update({
            "label": spec["label"], "scaffold": spec["scaffold"], "dataset": spec["dataset"],
            "revision": spec["revision"], "license": spec["license"],
            "catalog": {"path": pc._display(catalog_path), "sha256": pc._sha256(catalog_path)},
            "sources": sources,
        })
    return rows


# ---------------------------------------------------------------------------
# table
# ---------------------------------------------------------------------------

TABLE_ORDER = pc.TABLE_ORDER[:6]
TABLE_LABELS = pc.TABLE_LABELS


def _pct(value: float | None) -> str:
    return "--" if value is None else f"{100 * value:.1f}\\%"


def table(results: dict[str, Any] | None = None) -> str:
    results = results or json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    rows = {(r["corpus"], r["arm"]): r for r in results["corpora"]}
    lines = [
        r"\begin{tabular}{@{}lrrrrrrr@{}}",
        r"\toprule",
        r"Corpus & Traces & Groups & RO run$\ge$2 & Ground.\ strict & Ground.\ proj. & Fam.\ / floor & $n_{\max}$ \\",
        r"\midrule",
    ]
    for key in TABLE_ORDER:
        r = rows.get(key)
        if r is None:
            continue
        strict = r["policies"]["strict"]["beyond_frontier_groundable_ge2"]["share"]
        proj = r["policies"]["projected"]
        fam = proj["families_beyond_frontier"]
        n_max = f"{pc._num(fam['n_max'])}" + (r"$^\dagger$" if fam["n_max"] >= H1_FLOOR else "")
        lines.append(
            f"{TABLE_LABELS[key]} & {pc._num(r['traces'])} & {pc._num(r['groups'])} & "
            f"{_pct(r['interior_read_only_runs']['share_beyond_frontier_run_ge2'])} & {_pct(strict)} & "
            f"{_pct(proj['beyond_frontier_groundable_ge2']['share'])} & "
            f"{pc._num(fam['n'])} / {pc._num(fam['at_floor_ge3'])} & {n_max} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "% generated by paper/scripts/interior_census.py table; do not edit\n" + "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("smoke", "run", "table", "decompose"))
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--corpora", default=",".join(pc.CORPORA))
    parser.add_argument("--k", type=int, default=None, help="override the sampling divisor (recorded)")
    parser.add_argument("--smoke-file", type=Path, default=OUT_DIR / "smoke.json")
    parser.add_argument("--output", type=Path, default=RESULTS_PATH)
    args = parser.parse_args(argv)

    if args.command == "table":
        text = table()
        TABLE_PATH.write_text(text, encoding="utf-8")
        print(text)
        return
    if args.source_root is None:
        parser.error("--source-root is required")
    names = [n.strip() for n in args.corpora.split(",") if n.strip()]

    if args.command == "smoke":
        rows = []
        for name in names:
            verify_sources(name, args.source_root)
            print(f"smoke: {name} ...", flush=True)
            rows.append(smoke(name, args.source_root))
            print(f"  {rows[-1]}", flush=True)
        args.smoke_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema": "gac-interior-census-smoke/v1", "smoke_trajectories": SMOKE_TRAJECTORIES,
                   "budget_seconds": RUNTIME_BUDGET_SECONDS, "rows": rows}
        args.smoke_file.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {pc._display(args.smoke_file)}")
        return

    if args.command == "decompose":
        rows = []
        for name in names:
            sources = verify_sources(name, args.source_root)
            k = args.k if args.k is not None else DECOMPOSE_K[name]
            spec = pc.CORPORA[name]
            catalog = pc.load_catalog(spec["catalog"])
            print(f"decompose: {name} (k={k}) ...", flush=True)
            row = decompose(_episode_factory(name, args.source_root, catalog, k=k, limit=None), catalog,
                            corpus=name, sample={"rule": "keep iff sha1(episode_id) mod k == 0", "k": k})
            catalog_path = pc.CATALOG_DIR / f"{spec['catalog']}.yaml"
            row.update({"revision": spec["revision"], "sources": sources,
                        "catalog": {"path": pc._display(catalog_path), "sha256": pc._sha256(catalog_path)}})
            rows.append(row)
            print(f"  done ({row['runtime_seconds']} s): frontier={list(row['frontier_event'].items())[:3]} "
                  f"share std={row['registered_frontier']['beyond_frontier_groundable_ge2']['share']} "
                  f"pt={row['pass_through_pure_frontier']['beyond_frontier_groundable_ge2']['share']} "
                  f"n_max pt={row['pass_through_pure_frontier']['families_beyond_frontier']['n_max']}", flush=True)
        payload = {
            "schema": "gac-interior-census-decomposition/v1",
            "script": "paper/scripts/interior_census.py decompose",
            "status": "post hoc, descriptive; does not decide H1",
            "note": {"path": pc._display(DECOMPOSITION_NOTE_PATH), "sha256": pc._sha256(DECOMPOSITION_NOTE_PATH)},
            "registered_results": {"path": pc._display(RESULTS_PATH), "sha256": pc._sha256(RESULTS_PATH)},
            "snapshot_date": SNAPSHOT_DATE,
            "definitions": {
                "frontier_event": "the tool (or event kind) at the registered prefix frontier; 'none' when the ingested trajectory is all read-only",
                "distance_from_frontier": "calls from the frontier call to the first call of the best beyond-frontier groundable region (1 = the call right after the frontier)",
                "pass_through_pure_frontier": "the registered frontier recomputed so that a PURE-effect tool call and its result do not end the opening; windows are unchanged",
                "attributable_to_pure_calls": "traces with a beyond-frontier groundable region under the registered frontier but not under the pass-through frontier",
            },
            "mining_parameters": MINING,
            "corpora": rows,
        }
        DECOMPOSITION_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        print(f"wrote {pc._display(DECOMPOSITION_PATH)}")
        return

    smoke_rows: dict[str, Any] = {}
    if args.smoke_file.exists():
        smoke_rows = {r["corpus"]: r for r in json.loads(args.smoke_file.read_text(encoding="utf-8"))["rows"]}
    started = time.perf_counter()
    corpora: list[dict[str, Any]] = []
    for name in names:
        srow = smoke_rows.get(name)
        k = args.k if args.k is not None else (srow["k"] if srow else 1)
        print(f"census: {name} (k={k}) ...", flush=True)
        corpora.extend(run_corpus(name, args.source_root, k=k, smoke_row=srow))
        print(f"  done ({corpora[-1]['runtime_seconds']} s for the arm)", flush=True)
    verdict = {
        row["corpus"]: row["policies"]["projected"]["h1"]
        for row in corpora if row["arm"] == "primary"
    }
    result = {
        "schema": "gac-interior-census/v1",
        "script": "paper/scripts/interior_census.py",
        "protocol": {"path": pc._display(PROTOCOL_PATH), "sha256": pc._sha256(PROTOCOL_PATH)},
        "snapshot_date": SNAPSHOT_DATE,
        "definitions": {
            "interior_boundary": "a MODEL_REQ that is not the first boundary of the trajectory",
            "prefix_frontier": "the first event that ends the read-only opening: a non-compilable call, a HANDOFF/APPROVAL/GUARDRAIL, or a failed tool result",
            "beyond_frontier": "a window whose boundary comes after the prefix frontier; the population the prefix-only compiler cannot reach",
            "interior_read_only_run": "consecutive compilable calls from an interior boundary to the next barrier",
            "interior_groundable_region": "an Algorithm 2 window starting at an interior boundary with every slot LITERAL, NOT_GROUNDABLE or GROUNDED, under the strict (entry-schema) or projected (entry or prior-result) live-in policy",
            "families": "canonical hashes of interior windows (one per episode and hash, the largest); support in distinct groups",
            "h1": "pass iff, under the primary catalog and the projected policy, beyond-frontier groundable share >= 0.20 and some beyond-frontier family has support >= 92",
        },
        "mining_parameters": MINING,
        "max_calls_ingested": MAX_CALLS_INTERIOR,
        "evidence_class": "provider-free trace analysis of released benchmark trajectories; descriptive, not admission",
        "not_evidence_for": [
            "prevalence in deployed (non-benchmark) agents",
            "admission, calibration, or dispatch of any artifact",
            "unchanged continuation after a compiled interior region",
            "savings in cost (removed requests are counted, not priced)",
        ],
        "h1_verdict": {"per_corpus": verdict, "any_corpus_passes": any(v["pass"] for v in verdict.values())},
        "corpora": corpora,
        "runtime_seconds": round(time.perf_counter() - started, 1),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(f"wrote {pc._display(args.output)}")
    for row in corpora:
        p = row["policies"]
        print(
            f"  {row['corpus']:10s} {row['arm']:28s} traces={row['traces']:6d} "
            f"RO-run>=2 beyond={_pct(row['interior_read_only_runs']['share_beyond_frontier_run_ge2']):8s} "
            f"strict={_pct(p['strict']['beyond_frontier_groundable_ge2']['share']):8s} "
            f"proj={_pct(p['projected']['beyond_frontier_groundable_ge2']['share']):8s} "
            f"n_max={p['projected']['families_beyond_frontier']['n_max']}"
        )
    if args.output == RESULTS_PATH:
        TABLE_PATH.write_text(table(result), encoding="utf-8")
        print(f"wrote {pc._display(TABLE_PATH)}")


if __name__ == "__main__":
    main()
