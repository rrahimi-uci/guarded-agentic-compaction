#!/usr/bin/env python3
"""Provider-free prefix census over released multi-step tool-using agent trajectories.

The introduction admits that the prevalence of compilable openings across deployed agents
is unmeasured.  This script measures the nearest public proxy: over released corpora of
*executed* agent trajectories, what fraction of episodes open, from the first model
boundary, with a read-only prefix of two or more tool calls under a signed effect catalog,
and what fraction of those openings are groundable under Eq. (1) (every argument slot a
literal invariant across traces, or a bounded transform of the entry state or of a prior
result), as decided by the paper's own provenance graph (Algorithm 1) and window mining
(Algorithm 2) at the registered parameters.  It also reports how large the largest
recurrent opening family is against the 92-group zero-violation floor of Eq. (cp).

Three released corpora are ingested through ``benchmarks/external/trajectories.py``
(OpenHands on SWE-rebench, legacy SWE-agent, tau-bench historical runs), and the two
substrates the paper already ingests (NESTFUL gold sequences; AppWorld's released
baseline trajectories) are re-measured with the identical definitions so one table holds
all of them.  Each corpus has a primary measure under its signed catalog and one clearly
labelled sensitivity arm.

What this is not: released trajectories come from benchmark runs, not deployments; the
catalog classification is ours and conservative (shell execution and every unknown effect
is never a read); and prefix eligibility is not admission -- nothing here is synthesized,
calibrated or dispatched.  No model provider is called.

Usage::

    python paper/scripts/prefix_census.py manifest --source-root <dir>
    python paper/scripts/prefix_census.py run --source-root <dir> [--limit N]
    python paper/scripts/prefix_census.py table
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
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
from guarded_agentic_compaction.graph.normalize import FieldStats, _normalise_path  # noqa: E402
from guarded_agentic_compaction.graph.provenance import (  # noqa: E402
    GroundabilityPolicy,
    SlotMark,
    build_patg,
)
from guarded_agentic_compaction.graph.windows import enumerate_windows  # noqa: E402
from guarded_agentic_compaction.grc.calibrate import GRID, clopper_pearson_upper  # noqa: E402
from guarded_agentic_compaction.grc.dsl import SynthContext  # noqa: E402
from guarded_agentic_compaction.schema.effects import EffectCatalog, EffectClass  # noqa: E402
from guarded_agentic_compaction.schema.traces import Episode, EventKind  # noqa: E402

OUT_DIR = ROOT / "paper" / "results" / "prefix_census"
RESULTS_PATH = OUT_DIR / "results.json"
TABLE_PATH = ROOT / "paper" / "iclr" / "tables" / "prefix_census.tex"
DATASETS_DIR = ROOT / "paper" / "results" / "datasets"
CATALOG_DIR = ROOT / "benchmarks" / "contracts" / "effects"

#: Registered mining parameters (Table 3 / app:config); identical for every corpus.
MINING = {"max_depth": 2, "kappa": 3, "w_min": 2, "w_max": 12, "b_min": 2, "entry_schema": ["inputs"]}
MAX_CALLS = traj.DEFAULT_MAX_CALLS
SNAPSHOT_DATE = "2026-10-28"

#: The shell utilities the sensitivity arm admits as reads (and nothing else).
SHELL_READ_ARM = (
    "shell.ls", "shell.cat", "shell.pwd", "shell.find", "shell.grep", "shell.head",
    "shell.tail", "shell.wc", "shell.tree", "shell.stat", "shell.file", "shell.which",
    "shell.git_status", "shell.git_log", "shell.git_diff", "shell.git_show",
    "shell.git_ls_files", "shell.git_blame", "shell.git_grep", "shell.git_rev_parse",
)

CORPORA: dict[str, dict[str, Any]] = {
    "openhands": {
        "label": "OpenHands / SWE-rebench",
        "scaffold": "OpenHands v0.54.0, CodeAct, native function calling",
        "architecture": "codeact_function_calling",
        "dataset": "nebius/SWE-rebench-openhands-trajectories",
        "url": "https://huggingface.co/datasets/nebius/SWE-rebench-openhands-trajectories",
        "revision": "35455389ab51bf5e2306bfd436ef72d0f98bf882",
        "license": "CC-BY-4.0",
        "files": ["trajectories.parquet", "tools.json", "config.toml", "README.md", "LICENSE"],
        "catalog": "openhands_swe_rebench",
        "tools": traj.OPENHANDS_TOOLS,
        "entry_contract": "openhands-task-record-v1",
        "arm": {"name": "shell_reads_admitted", "flip_to_read": SHELL_READ_ARM},
    },
    "sweagent": {
        "label": "SWE-agent (nebius)",
        "scaffold": "SWE-agent legacy text-action ReAct",
        "architecture": "react_text_actions",
        "dataset": "nebius/SWE-agent-trajectories",
        "url": "https://huggingface.co/datasets/nebius/SWE-agent-trajectories",
        "revision": "68195a1450865274106246d0d0296a1d6807b88e",
        "license": "CC-BY-4.0",
        "files": ["README.md"] + [f"data/train-{i:05d}-of-00012.parquet" for i in range(12)],
        "catalog": "sweagent_nebius",
        "tools": traj.SWEAGENT_TOOLS,
        "entry_contract": "sweagent-issue-record-v1",
        "arm": {"name": "shell_reads_admitted", "flip_to_read": SHELL_READ_ARM},
    },
    "taubench": {
        "label": "tau-bench historical runs",
        "scaffold": "tau-bench function-calling ReAct, conversational",
        "architecture": "react_function_calling_conversational",
        "dataset": "sierra-research/tau-bench historical_trajectories",
        "url": "https://github.com/sierra-research/tau-bench/tree/59a200c6d575d595120f1cb70fea53cef0632f6b/historical_trajectories",
        "revision": "59a200c6d575d595120f1cb70fea53cef0632f6b",
        "license": "MIT",
        "files": ["gpt-4o-airline.json", "gpt-4o-retail.json", "sonnet-35-new-airline.json",
                  "sonnet-35-new-retail.json", "LICENSE"],
        "catalog": "taubench",
        "tools": traj.TAUBENCH_TOOLS,
        "entry_contract": "taubench-first-user-utterance-v1",
        "arm": {"name": "pre_tool_user_turns_folded"},
    },
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _display(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _sorted_counter(counter: Counter, top: int | None = None) -> dict[str, int]:
    items = sorted(counter.items(), key=lambda kv: (-kv[1], str(kv[0])))
    if top is not None:
        items = items[:top]
    return {str(key): value for key, value in items}


def _histogram(values: Iterable[int]) -> dict[str, int]:
    counts = Counter(int(v) for v in values)
    return {str(key): counts[key] for key in sorted(counts)}


def _distribution(values: list[int]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    return {
        "n": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "mean": round(statistics.fmean(values), 3),
        "max": max(values),
    }


def required_zero_violation_groups(alpha: float = 0.05, delta: float = 0.10) -> int:
    confidence = 1.0 - delta / len(GRID)
    groups = 1
    while clopper_pearson_upper(0, groups, confidence) > alpha:
        groups += 1
    return groups


class HashedFieldStats(FieldStats):
    """``FieldStats`` with long values keyed by digest, so a corpus of file views fits."""

    def observe(self, path: str, value: Any) -> None:  # type: ignore[override]
        if isinstance(value, (dict, list)):
            return
        key = f"{type(value).__name__}:{value}"
        if len(key) > 64:
            key = hashlib.sha1(key.encode()).hexdigest()
        self.counts[_normalise_path(path)][key] += 1


def observe_episode(stats: FieldStats, episode: Episode) -> None:
    """Exactly ``graph.normalize.field_statistics``, one episode at a time."""

    from guarded_agentic_compaction.schema.traces import flatten

    for path, value in flatten(episode.entry_state, prefix="z"):
        stats.observe(path, value)
    for event in episode.events:
        if event.kind is EventKind.TOOL_RESULT and event.output is not None:
            for path, value in flatten(event.output, prefix=f"{event.tool}"):
                stats.observe(path, value)
        elif event.kind is EventKind.TOOL_CALL and isinstance(event.input, dict):
            for path, value in flatten(event.input, prefix=f"{event.tool}#in"):
                stats.observe(path, value)


def load_catalog(name: str, *, flip_to_read: Iterable[str] = ()) -> EffectCatalog:
    """Load a signed catalog; the sensitivity arm flips listed entries to READ_LOCAL."""

    path = CATALOG_DIR / f"{name}.yaml"
    catalog = EffectCatalog.from_yaml(path)
    flips = tuple(flip_to_read)
    if not flips:
        return catalog
    payload = catalog.model_dump(mode="json")
    for tool in flips:
        if tool not in payload["tools"]:
            raise SystemExit(f"sensitivity arm names an undeclared tool {tool!r} in {path.name}")
        payload["tools"][tool].update(
            {"effect": "READ_LOCAL", "capabilities": ["speculatable", "replayable", "cacheable"]}
        )
    payload["name"] = f"{payload['name']}-arm-shell-reads"
    return EffectCatalog.from_dict(payload)


def read_only_opening_length(episode: Episode, catalog: EffectCatalog) -> tuple[int, str | None]:
    """Consecutive compilable calls from position 0 and the tool that ended the run."""

    depth = 0
    for event in episode.events:
        if event.kind is EventKind.HANDOFF:
            return depth, "user_turn"
        if event.kind is not EventKind.TOOL_CALL:
            continue
        if not catalog.compilable(event.tool):
            return depth, event.tool or "?"
        depth += 1
    return depth, None


# ---------------------------------------------------------------------------
# the census over one corpus and one catalog
# ---------------------------------------------------------------------------


def census(
    episodes: Callable[[], Iterator[Episode]],
    catalog: EffectCatalog,
    *,
    corpus: str,
    arm: str,
) -> dict[str, Any]:
    """Two passes: corpus field statistics, then Algorithm 1 + 2 on every opening."""

    started = time.perf_counter()
    stats = HashedFieldStats()
    n_pass1 = 0
    for episode in episodes():
        observe_episode(stats, episode)
        n_pass1 += 1
    policy = GroundabilityPolicy.from_catalog(catalog, stats=stats)
    ctx = SynthContext(max_depth=MINING["max_depth"])

    traces = 0
    groups: set[str] = set()
    models: Counter = Counter()
    architectures: Counter = Counter()
    first_call: Counter = Counter()
    first_barrier: Counter = Counter()
    ro_lengths: list[int] = []
    gr_lengths: list[int] = []
    block_reasons: Counter = Counter()
    ungrounded_slots: Counter = Counter()
    diagnostics: Counter = Counter()
    blocked: Counter = Counter()
    blocked_by_tool: Counter = Counter()
    stopped_by: Counter = Counter()
    user_barriers = 0
    calls_total: list[int] = []
    by_model: dict[str, Counter] = defaultdict(Counter)
    family_groups: dict[str, set[str]] = defaultdict(set)
    family_episodes: Counter = Counter()
    family_shape: dict[str, dict[str, Any]] = {}

    for episode in episodes():
        traces += 1
        groups.add(episode.group_id)
        model = str(episode.attributes.get("model", "unknown"))
        models[model] += 1
        architectures[str(episode.attributes.get("architecture", "unknown"))] += 1
        stopped_by[str(episode.attributes.get("ingestion_stopped_by"))] += 1
        calls_total.append(int(episode.attributes.get("n_calls_total", 0)))
        user_barriers += sum(1 for e in episode.events if e.kind is EventKind.HANDOFF)
        calls = [e for e in episode.events if e.kind is EventKind.TOOL_CALL]
        first_call[calls[0].tool if calls else "<no tool call>"] += 1
        ro_len, barrier = read_only_opening_length(episode, catalog)
        ro_lengths.append(ro_len)
        first_barrier[barrier or "<none within ingested opening>"] += 1
        by_model[model]["traces"] += 1
        by_model[model]["read_only_ge2"] += int(ro_len >= 2)

        graph = build_patg(
            episode, catalog, policy, max_depth=MINING["max_depth"], kappa=MINING["kappa"], ctx=ctx
        )
        diagnostics.update(graph.diagnostics)
        windows = enumerate_windows(
            graph,
            catalog,
            entry_schema=tuple(MINING["entry_schema"]),
            w_min=MINING["w_min"],
            w_max=MINING["w_max"],
            b_min=MINING["b_min"],
            blocked=blocked,
            blocked_by_tool=blocked_by_tool,
        )
        opening = [w for w in windows if w.a == 0]
        gr_len = max((w.n_tool_events for w in opening), default=0)
        gr_lengths.append(gr_len)
        by_model[model]["groundable_ge2"] += int(gr_len >= 2)
        best: dict[str, Any] = {}
        for window in opening:
            current = best.get(window.canon_hash)
            if current is None or window.n_tool_events > current.n_tool_events:
                best[window.canon_hash] = window
        for canon, window in best.items():
            family_groups[canon].add(window.group_id)
            family_episodes[canon] += 1
            family_shape.setdefault(canon, {
                "tools": list(window.tools()),
                "run_lengths": [step.run_length for step in window.steps],
                "length": window.n_tool_events,
                "live_in": list(window.live_in),
            })
        if ro_len >= 2 and gr_len < 2:
            call_positions = [i for i, e in enumerate(graph.order) if e.kind is EventKind.TOOL_CALL]
            positions = call_positions[:2]
            marks = [(slot, i) for i in positions for slot in graph.slots_of(i)]
            if any(s.mark == SlotMark.UNGROUNDED for s, _ in marks):
                block_reasons["ungrounded_slot"] += 1
                for slot, _ in marks:
                    if slot.mark == SlotMark.UNGROUNDED:
                        ungrounded_slots[f"{slot.tool}#{slot.path}"] += 1
            elif any(s.mark == SlotMark.AMBIGUOUS for s, _ in marks):
                block_reasons["ambiguous_slot"] += 1
            else:
                last = positions[-1]
                boundaries = sum(1 for e in graph.order[: last + 1] if e.kind is EventKind.MODEL_REQ)
                if boundaries < MINING["b_min"]:
                    block_reasons["too_few_boundaries"] += 1
                elif (
                    len(call_positions) > 2
                    and graph.order[call_positions[2]].tool == graph.order[last].tool
                ):
                    # The two-call window ends inside a run of the same tool whose
                    # continuation is not groundable: Algorithm 2's partial-run rule.
                    block_reasons["partial_run_into_ungroundable_call"] += 1
                else:
                    block_reasons["other"] += 1

    required = required_zero_violation_groups()
    supports = {canon: len(members) for canon, members in family_groups.items()}
    n_max = max(supports.values(), default=0)
    top = sorted(supports.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
    ro_ge2 = sum(1 for v in ro_lengths if v >= 2)
    gr_ge2 = sum(1 for v in gr_lengths if v >= 2)
    ro_ge1 = sum(1 for v in ro_lengths if v >= 1)
    mark_total = sum(diagnostics[k] for k in ("grounded", "ambiguous", "ungrounded"))
    return {
        "corpus": corpus,
        "arm": arm,
        "catalog_version": catalog.catalog_version,
        "traces": traces,
        "groups": len(groups),
        "models": _sorted_counter(models),
        "architectures": _sorted_counter(architectures),
        "calls_per_trace": _distribution(calls_total),
        "first_call": _sorted_counter(first_call, top=10),
        "first_barrier": _sorted_counter(first_barrier, top=10),
        "read_only_opening": {
            "histogram": _histogram(ro_lengths),
            "ge1": ro_ge1,
            "ge2": ro_ge2,
            "share_ge1": ro_ge1 / traces if traces else None,
            "share_ge2": ro_ge2 / traces if traces else None,
        },
        "groundable_opening": {
            "histogram": _histogram(gr_lengths),
            "ge2": gr_ge2,
            "share_ge2": gr_ge2 / traces if traces else None,
            "share_of_read_only_ge2": gr_ge2 / ro_ge2 if ro_ge2 else None,
            "length_among_ge2": _distribution([v for v in gr_lengths if v >= 2]),
        },
        "opening_block_reasons": _sorted_counter(block_reasons),
        "ungrounded_opening_slots": _sorted_counter(ungrounded_slots, top=10),
        "slot_marks": {
            "grounded": diagnostics["grounded"],
            "ambiguous": diagnostics["ambiguous"],
            "ungrounded": diagnostics["ungrounded"],
            "model_originated": diagnostics["model_originated"],
            "not_groundable": diagnostics["not_groundable"],
            "literal_only": diagnostics["literal_only"],
            "grounded_share": diagnostics["grounded"] / mark_total if mark_total else None,
        },
        "blocked_window_candidates": _sorted_counter(blocked),
        "blocked_by_tool": _sorted_counter(blocked_by_tool, top=12),
        "families": {
            "n": len(supports),
            "at_floor_ge3": sum(1 for v in supports.values() if v >= 3),
            "n_max": n_max,
            "top": [
                {"family_hash": canon, "support": support, "episodes": family_episodes[canon], **family_shape[canon]}
                for canon, support in top
            ],
        },
        "exact_gate": {
            "alpha": 0.05,
            "delta": 0.10,
            "minimum_zero_violation_groups": required,
            "max_observed_family_support": n_max,
            "families_at_or_above_floor": sum(1 for v in supports.values() if v >= required),
            "outcome": "RETIRE" if n_max < required else "candidate_present",
        },
        "ingestion": {
            "max_calls": MAX_CALLS,
            "stopped_by": _sorted_counter(stopped_by),
            "user_turn_barriers": user_barriers,
            "pass1_episodes": n_pass1,
        },
        "by_model": {
            model: {
                "traces": row["traces"],
                "read_only_ge2": row["read_only_ge2"],
                "groundable_ge2": row["groundable_ge2"],
                "share_read_only_ge2": row["read_only_ge2"] / row["traces"],
                "share_groundable_ge2": row["groundable_ge2"] / row["traces"],
            }
            for model, row in sorted(by_model.items())
        },
        "runtime_seconds": round(time.perf_counter() - started, 1),
    }


# ---------------------------------------------------------------------------
# corpus wiring
# ---------------------------------------------------------------------------


def _records(name: str, source_root: Path, *, limit: int | None, folded: bool = False) -> Iterator[traj.TrajectoryRecord]:
    root = source_root / name
    if name == "openhands":
        return traj.iter_openhands(root / "trajectories.parquet", limit=limit)
    if name == "sweagent":
        return traj.iter_sweagent(root, limit=limit)
    if name == "taubench":
        return traj.iter_taubench(root, fold_pre_tool_user_turns=folded, limit=limit)
    raise KeyError(name)


def _episode_factory(
    name: str, source_root: Path, catalog: EffectCatalog, *, limit: int | None, folded: bool = False
) -> Callable[[], Iterator[Episode]]:
    spec = CORPORA[name]
    manifest = traj.census_manifest(
        name,
        revision=spec["revision"],
        catalog_version=catalog.catalog_version,
        tools=spec["tools"],
        scaffold=spec["scaffold"],
        entry_contract=spec["entry_contract"] + ("-folded" if folded else ""),
    )

    def factory() -> Iterator[Episode]:
        for record in _records(name, source_root, limit=limit, folded=folded):
            yield traj.build_episode(
                record,
                manifest,
                tools=spec["tools"],
                max_calls=MAX_CALLS,
                barrier=lambda tool: not catalog.compilable(tool),
            )

    return factory


def run_corpus(name: str, source_root: Path, *, limit: int | None) -> list[dict[str, Any]]:
    spec = CORPORA[name]
    catalog_path = CATALOG_DIR / f"{spec['catalog']}.yaml"
    primary_catalog = load_catalog(spec["catalog"])
    rows = [
        census(_episode_factory(name, source_root, primary_catalog, limit=limit), primary_catalog,
               corpus=name, arm="primary")
    ]
    arm = spec["arm"]
    if "flip_to_read" in arm:
        arm_catalog = load_catalog(spec["catalog"], flip_to_read=arm["flip_to_read"])
        rows.append(census(_episode_factory(name, source_root, arm_catalog, limit=limit), arm_catalog,
                           corpus=name, arm=arm["name"]))
    else:
        rows.append(census(_episode_factory(name, source_root, primary_catalog, limit=limit, folded=True),
                           primary_catalog, corpus=name, arm=arm["name"]))
    for row in rows:
        row.update({
            "label": spec["label"],
            "scaffold": spec["scaffold"],
            "dataset": spec["dataset"],
            "revision": spec["revision"],
            "license": spec["license"],
            "catalog": {"path": _display(catalog_path), "sha256": _sha256(catalog_path)},
            "limit": limit,
        })
    return rows


# --- NESTFUL: the paper's gold-sequence substrate, re-measured ---------------------------


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def run_nestful() -> dict[str, Any]:
    nb = _load_script("nestful_benchmark")
    if not (nb.DATA_DIR / "nestful_data.jsonl").exists():
        raise SystemExit("NESTFUL inputs are missing; run paper/scripts/nestful_benchmark.py first")
    rows = nb.load_rows()
    basic_names = nb.basic_function_names()
    module = nb.load_basic_module()
    basic_rows = [row for row in rows if all(call["name"] in basic_names for call in row["output"])]
    catalog = EffectCatalog.from_dict({
        "version": 1,
        "name": "nestful-basic-pure-audit",
        "tools": {
            name: {
                "effect": "PURE",
                "capabilities": ["speculatable", "replayable", "cacheable"],
                "resource": "nestful-basic-functions",
                "notes": "Audited deterministic function in pinned NESTFUL basic_functions.py",
            }
            for name in sorted(basic_names)
        },
    })
    manifest = nb.ExecutionManifest(
        manifest_id="nestful-v2-pinned-basic-functions",
        commit=nb.NESTFUL_COMMIT,
        model="gold-sequence-no-model-inference",
        prompt_hash="nestful-v2-gold",
        tools_hash=hashlib.sha256("|".join(sorted(basic_names)).encode()).hexdigest()[:16],
        policy_hash="public-benchmark-structural-evaluation",
        guardrail_hash="none-recorded-replay-only",
        effect_catalog_version=catalog.catalog_version,
        entry_contract_version="nestful-v2-literals-by-call-slot",
        sdk_version="not-applicable",
        tracer_version="paper-nestful-adapter-v1",
    )
    episodes: list[Episode] = []
    for ordinal, row in enumerate(basic_rows):
        try:
            resolved, outputs = nb.execute_row(row, module)
        except Exception:
            continue
        episode = nb.build_episode(row, resolved, outputs, manifest, ordinal)
        episode.attributes.update({
            "architecture": "gold_sequence_no_agent",
            "model": "gold-sequence",
            "n_calls_total": len(row["output"]),
            "ingestion_stopped_by": None,
        })
        episodes.append(episode)
    result = census(lambda: iter(episodes), catalog, corpus="nestful", arm="primary")
    result.update({
        "label": "NESTFUL (gold sequences)",
        "scaffold": "gold tool sequences, no agent",
        "dataset": "IBM/NESTFUL",
        "revision": nb.NESTFUL_COMMIT,
        "license": "Apache-2.0",
        "catalog": {"path": "constructed in paper/scripts/nestful_benchmark.py", "sha256": None},
        "limit": None,
        "note": "Every NESTFUL function is PURE and compilable, so the read-only opening is the whole "
                "sequence; the census uses w_max=12 where the retained substrate run used 53.",
    })
    return result


# --- AppWorld: released baseline trajectories, re-measured where the logs allow -------------


def run_appworld(source_root: Path) -> dict[str, Any] | None:
    """Read-only opening lengths over the 8,190 released trajectories.

    The released logs retain method, url and request data but no responses and no model
    boundaries, so Eq. (1) grounding against prior results cannot be evaluated and the
    groundable column is reported as not measurable; the read-only opening is measured with
    the same catalog rule as the retained dispatch preflight (an undeclared route such as
    the API-documentation call is UNKNOWN and therefore not a read).
    """

    checkout = source_root / "appworld"
    outputs = checkout / "experiments" / "outputs"
    api_docs = checkout / "data" / "api_docs" / "standard"
    if not outputs.is_dir() or not api_docs.is_dir():
        return None
    pre = _load_script("appworld_dispatch_preflight")
    catalog = EffectCatalog.from_yaml(pre.CATALOG_PATH)
    routes = pre._load_route_table(api_docs)
    traces = 0
    groups: set[str] = set()
    architectures: Counter = Counter()
    first_call: Counter = Counter()
    first_barrier: Counter = Counter()
    ro_lengths: list[int] = []
    calls_total: list[int] = []
    by_family: dict[str, Counter] = defaultdict(Counter)
    for run in sorted(outputs.glob("*_test_*")):
        if not (run / "tasks").is_dir():
            continue
        family = pre._family_of(run.name)
        for log in sorted(run.glob("tasks/*/logs/api_calls.jsonl")):
            calls = pre._trajectory(log)
            traces += 1
            groups.add(log.parents[1].name)
            architectures[family] += 1
            calls_total.append(len(calls))
            first_call[f"{calls[0][0]} {calls[0][1]}" if calls else "<no call>"] += 1
            depth, barrier = pre._maximal_read_prefix(calls, routes, catalog)
            depth = min(depth, MAX_CALLS)
            ro_lengths.append(depth)
            first_barrier[barrier or "<none>"] += 1
            by_family[family]["traces"] += 1
            by_family[family]["read_only_ge2"] += int(depth >= 2)
    ro_ge2 = sum(1 for v in ro_lengths if v >= 2)
    ro_ge1 = sum(1 for v in ro_lengths if v >= 1)
    return {
        "corpus": "appworld_released",
        "arm": "primary",
        "label": "AppWorld released baselines",
        "scaffold": "four official baseline architectures (ReAct, plan-and-execute, iterative parallel function calling, full code + reflection)",
        "dataset": "StonyBrookNLP/appworld experiment-outputs-0.1.0 (28 released test runs)",
        "revision": "appworld 0.1.3.post1; experiment-outputs-0.1.0.bundle",
        "license": "Apache-2.0",
        "catalog": {"path": _display(pre.CATALOG_PATH), "sha256": _sha256(pre.CATALOG_PATH)},
        "catalog_version": catalog.catalog_version,
        "traces": traces,
        "groups": len(groups),
        "models": {},
        "architectures": _sorted_counter(architectures),
        "calls_per_trace": _distribution(calls_total),
        "first_call": _sorted_counter(first_call, top=10),
        "first_barrier": _sorted_counter(first_barrier, top=10),
        "read_only_opening": {
            "histogram": _histogram(ro_lengths),
            "ge1": ro_ge1,
            "ge2": ro_ge2,
            "share_ge1": ro_ge1 / traces if traces else None,
            "share_ge2": ro_ge2 / traces if traces else None,
        },
        "groundable_opening": None,
        "families": None,
        "exact_gate": None,
        "by_architecture": {
            family: {
                "traces": row["traces"],
                "read_only_ge2": row["read_only_ge2"],
                "share_read_only_ge2": row["read_only_ge2"] / row["traces"],
            }
            for family, row in sorted(by_family.items())
        },
        "not_measurable": [
            "groundable opening: the released logs retain no tool responses and no entry snapshot",
            "families and n_max: no argument slots can be grounded, so no canonical window exists",
        ],
        "retained_reference": {
            "gold_solution_substrate_n_max": 136,
            "admitted_program_eligible_at_position_0": "3,102/8,190 (paper/results/external_benchmarks/appworld_dispatch_preflight.json)",
        },
        "limit": None,
    }


# ---------------------------------------------------------------------------
# manifests
# ---------------------------------------------------------------------------


def write_manifests(source_root: Path, names: Iterable[str]) -> None:
    for name in names:
        spec = CORPORA[name]
        root = source_root / name
        files: dict[str, Any] = {}
        for rel in spec["files"]:
            path = root / rel
            if not path.exists():
                raise SystemExit(f"{name}: expected file {rel} under {root}")
            files[rel] = {"sha256": _sha256(path), "bytes": path.stat().st_size}
        manifest = {
            "dataset": spec["dataset"],
            "url": spec["url"],
            "revision": spec["revision"],
            "license": spec["license"],
            "snapshot_date": SNAPSHOT_DATE,
            "files": files,
            "raw_corpus_committed": False,
            "note": "Downloaded into an isolated directory and parsed only; never executed. "
                    "Raw files are not committed; the derived aggregates live in paper/results/prefix_census/.",
        }
        target = DATASETS_DIR / name / "source_manifest.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {_display(target)}")


# ---------------------------------------------------------------------------
# table
# ---------------------------------------------------------------------------

TABLE_ORDER = (
    ("openhands", "primary"), ("openhands", "shell_reads_admitted"),
    ("sweagent", "primary"), ("sweagent", "shell_reads_admitted"),
    ("taubench", "primary"), ("taubench", "pre_tool_user_turns_folded"),
    ("nestful", "primary"), ("appworld_released", "primary"),
)
TABLE_LABELS = {
    ("openhands", "primary"): r"OpenHands / SWE-rebench",
    ("openhands", "shell_reads_admitted"): r"\quad + shell reads admitted",
    ("sweagent", "primary"): r"SWE-agent (legacy)",
    ("sweagent", "shell_reads_admitted"): r"\quad + shell reads admitted",
    ("taubench", "primary"): r"$\tau$-bench runs",
    ("taubench", "pre_tool_user_turns_folded"): r"\quad + pre-tool user turns folded",
    ("nestful", "primary"): r"NESTFUL (gold)",
    ("appworld_released", "primary"): r"AppWorld released",
}
TABLE_ARCH = {
    "openhands": "CodeAct, FC",
    "sweagent": "ReAct, text",
    "taubench": "ReAct, FC, conv.",
    "nestful": "no agent",
    "appworld_released": "4 archs",
}


def _num(value: int) -> str:
    return f"{value:,}".replace(",", "{,}")


def _pct(value: float | None) -> str:
    return "--" if value is None else f"{100 * value:.1f}\\%"


def table(results: dict[str, Any] | None = None) -> str:
    """Rows in registered order; every number from results.json; byte-deterministic."""

    results = results or json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    rows = {(row["corpus"], row["arm"]): row for row in results["corpora"]}
    floor = results["exact_gate_floor"]
    lines = [
        r"\begin{tabular}{@{}llrrrrrrr@{}}",
        r"\toprule",
        r"Corpus & Agent & Traces & Groups & RO$\ge$2 & Ground.\ $\ge$2 & Med.\ len & Fam.\ / floor & $n_{\max}$ \\",
        r"\midrule",
    ]
    for key in TABLE_ORDER:
        row = rows.get(key)
        if row is None:
            continue
        label = TABLE_LABELS[key]
        arch = TABLE_ARCH[key[0]] if key[1] == "primary" else ""
        ro = _pct(row["read_only_opening"]["share_ge2"])
        gr = row.get("groundable_opening")
        fam = row.get("families")
        if gr is None:
            ground, med, families, n_max = "--", "--", "--", "--"
        else:
            ground = _pct(gr["share_ge2"])
            med = "--" if gr["length_among_ge2"]["n"] == 0 else f"{gr['length_among_ge2']['median']:g}"
            families = f"{_num(fam['n'])} / {_num(fam['at_floor_ge3'])}"
            n_max = f"{_num(fam['n_max'])}" + (r"$^\dagger$" if fam["n_max"] >= floor else "")
        lines.append(
            f"{label} & {arch} & {_num(row['traces'])} & {_num(row['groups'])} & {ro} & {ground} & {med} & {families} & {n_max} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    text = "% generated by paper/scripts/prefix_census.py table; do not edit\n" + "\n".join(lines) + "\n"
    return text


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("manifest", "run", "table"))
    parser.add_argument("--source-root", type=Path, help="directory holding one sub-directory per corpus")
    parser.add_argument("--corpora", default=",".join(CORPORA), help="comma-separated subset of the released corpora")
    parser.add_argument("--limit", type=int, default=None, help="ingest only the first N records per corpus (smoke runs)")
    parser.add_argument("--skip-nestful", action="store_true")
    parser.add_argument("--skip-appworld", action="store_true")
    parser.add_argument("--output", type=Path, default=RESULTS_PATH)
    args = parser.parse_args(argv)

    if args.command == "table":
        text = table()
        TABLE_PATH.write_text(text, encoding="utf-8")
        print(text)
        return
    if args.source_root is None:
        parser.error("--source-root is required")
    names = [name.strip() for name in args.corpora.split(",") if name.strip()]
    if args.command == "manifest":
        write_manifests(args.source_root, names)
        return

    started = time.perf_counter()
    corpora: list[dict[str, Any]] = []
    for name in names:
        print(f"census: {name} ...", flush=True)
        corpora.extend(run_corpus(name, args.source_root, limit=args.limit))
        print(f"  done ({corpora[-1]['runtime_seconds']} s for the arm)", flush=True)
    if not args.skip_nestful:
        print("census: nestful ...", flush=True)
        corpora.append(run_nestful())
    if not args.skip_appworld:
        appworld = run_appworld(args.source_root)
        if appworld is not None:
            corpora.append(appworld)
        else:
            print("census: appworld released outputs not available under --source-root; row omitted")
    result = {
        "schema": "gac-prefix-census/v1",
        "script": "paper/scripts/prefix_census.py",
        "snapshot_date": SNAPSHOT_DATE,
        "definitions": {
            "first_model_boundary": "the first agent turn after the task prompt; normalized position 0 is the first tool call",
            "read_only_opening": "consecutive calls from position 0 whose catalog entry is compilable (read-like with speculatable+replayable capabilities); a new user utterance, an unknown effect, a write, an approval-gated tool or a missing capability ends it",
            "groundable_opening": "the longest Algorithm 2 window starting at the first boundary with every slot LITERAL, NOT_GROUNDABLE or GROUNDED (entry state or prior result, depth<=2, kappa=3) and live-ins within the entry schema; share counts episodes whose longest such window has >=2 calls",
            "families": "canonical hashes of opening windows (one per episode and hash, the largest); support is the number of distinct groups (tasks); at floor = >=3 groups as in Table 4",
            "n_max_vs_floor": "largest family support against the 92 zero-violation groups Eq. (cp) requires",
            "arms": "each released corpus carries one labelled sensitivity arm: shell reads admitted (allowlisted single-utility invocations flipped to READ_LOCAL) for the coding corpora; pre-tool user turns folded into entry state for tau-bench",
        },
        "mining_parameters": MINING,
        "max_calls_ingested": MAX_CALLS,
        "exact_gate_floor": required_zero_violation_groups(),
        "evidence_class": "provider-free trace analysis of released benchmark trajectories; descriptive, not admission",
        "not_evidence_for": [
            "prevalence in deployed (non-benchmark) agents",
            "admission, calibration, or dispatch of any artifact",
            "quality of any compiled program (nothing is synthesized or replayed here)",
        ],
        "corpora": corpora,
        "runtime_seconds": round(time.perf_counter() - started, 1),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(f"wrote {_display(args.output)}")
    for row in corpora:
        gr = row.get("groundable_opening")
        print(
            f"  {row['corpus']:18s} {row['arm']:28s} traces={row['traces']:6d} "
            f"RO>=2={_pct(row['read_only_opening']['share_ge2']):8s} "
            f"groundable>=2={_pct(gr['share_ge2']) if gr else '--':8s} "
            f"n_max={row['families']['n_max'] if row.get('families') else '--'}"
        )
    if args.output == RESULTS_PATH:
        TABLE_PATH.write_text(table(result), encoding="utf-8")
        print(f"wrote {_display(TABLE_PATH)}")


if __name__ == "__main__":
    main()
