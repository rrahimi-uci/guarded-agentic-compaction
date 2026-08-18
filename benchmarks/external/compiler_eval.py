"""Shared read-only compiler evaluation for external benchmark episodes.

This is the same provenance -> window-mining -> synthesis -> held-out recorded-replay
pipeline the API-Bank evaluation runs, lifted into one place so a second external
substrate cannot silently diverge from it.  It reports the exact zero-violation group
requirement alongside the observed maximum family support, so a corpus that cannot
certify a family is recorded as a retirement rather than as a missing measurement.

``paper/scripts/api_bank_benchmark.py`` keeps its own inlined copy: that artifact is
already sealed and is intentionally not re-derived here.  The defaults below match it
exactly (``max_depth=2``, ``kappa=3``, ``w_min=2``, ``w_max=12``, ``b_min=2``, support
of at least three independent groups, and a held-out split of at most a quarter).
"""

from __future__ import annotations

import time
import tracemalloc
from collections import Counter, defaultdict
from typing import Any, Sequence

from guarded_agentic_compaction.graph.provenance import build_all
from guarded_agentic_compaction.graph.windows import Family, enumerate_windows
from guarded_agentic_compaction.grc.calibrate import GRID, clopper_pearson_upper
from guarded_agentic_compaction.grc.contracts import (
    grouped_recorded_replay,
    induce_guard,
    induce_verifier,
)
from guarded_agentic_compaction.grc.synthesize import synthesize_program
from guarded_agentic_compaction.schema.effects import EffectCatalog
from guarded_agentic_compaction.schema.traces import Episode, ExecutionManifest

__all__ = ["required_zero_violation_groups", "evaluate_compiler"]


def required_zero_violation_groups(alpha: float = 0.05, delta: float = 0.10) -> int:
    """Smallest zero-violation group count whose exact upper bound clears alpha."""

    confidence = 1.0 - delta / len(GRID)
    groups = 1
    while clopper_pearson_upper(0, groups, confidence) > alpha:
        groups += 1
    return groups


def evaluate_compiler(
    episodes: Sequence[Episode],
    catalog: EffectCatalog,
    manifest: ExecutionManifest,
    *,
    entry_schema: tuple[str, ...] = ("inputs",),
    max_depth: int = 2,
    kappa: int = 3,
    w_min: int = 2,
    w_max: int = 12,
    b_min: int = 2,
    min_support_groups: int = 3,
    n_permutations: int = 25,
    alpha: float = 0.05,
    delta: float = 0.10,
) -> dict[str, Any]:
    """Run the compiler over normalized episodes and return publication aggregates."""

    tracemalloc.start()
    started = time.perf_counter()
    graphs, policy = build_all(episodes, catalog, max_depth=max_depth, kappa=kappa)
    graph_seconds = time.perf_counter() - started
    diagnostics: Counter[str] = Counter()
    blocked: Counter[str] = Counter()
    blocked_by_tool: Counter[str] = Counter()
    windows = []
    episodes_with_windows: set[str] = set()
    for graph in graphs:
        diagnostics.update(graph.diagnostics)
        retained = enumerate_windows(
            graph,
            catalog,
            entry_schema=entry_schema,
            w_min=w_min,
            w_max=w_max,
            b_min=b_min,
            blocked=blocked,
            blocked_by_tool=blocked_by_tool,
        )
        if retained:
            episodes_with_windows.add(graph.episode.episode_id)
            windows.extend(retained)

    by_hash: dict[str, list[Any]] = defaultdict(list)
    for window in windows:
        by_hash[window.canon_hash].append(window)

    family_rows: list[dict[str, Any]] = []
    replay_totals: Counter[str] = Counter()
    for family_hash, members in sorted(by_hash.items()):
        independent = sorted(members, key=lambda item: item.group_id)
        if len({item.group_id for item in independent}) < min_support_groups:
            continue
        split = max(2, len(independent) - max(1, len(independent) // 4))
        train, test = independent[:split], independent[split:]
        if not test:
            continue
        family = Family(canon_hash=family_hash, windows=independent)
        synthesis = synthesize_program(
            family, train, catalog, policy, n_permutations=n_permutations
        )
        row: dict[str, Any] = {
            "family_hash": family_hash,
            "support": family.support,
            "train_groups": len({item.group_id for item in train}),
            "test_groups": len({item.group_id for item in test}),
            "tool_count": len(family.tools),
            "synthesis": "ok" if synthesis.ok else synthesis.reason.split(":", 1)[0],
        }
        replay_totals["families_attempted"] += 1
        if synthesis.ok and synthesis.program is not None:
            guard = induce_guard(
                synthesis.program, train, manifest, catalog, partition_by=()
            )
            verifier = induce_verifier(
                synthesis.program, train, synthesis.names, catalog
            )
            replay = grouped_recorded_replay(
                synthesis.program,
                guard,
                verifier,
                test,
                synthesis.names,
                catalog,
            )
            row.update(
                {
                    "program_steps": len(synthesis.program.steps),
                    "program_size": synthesis.program.size,
                    "replay_passed": replay.passed,
                    "replay_wrong": replay.wrong,
                    "replay_abstained": replay.abstained,
                }
            )
            replay_totals["families_synthesized"] += 1
            replay_totals["test_windows"] += replay.n
            replay_totals["test_passed"] += replay.passed
            replay_totals["test_wrong"] += replay.wrong
            replay_totals["test_abstained"] += replay.abstained
        family_rows.append(row)

    _current, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    elapsed = time.perf_counter() - started
    max_support = max(
        (len({item.group_id for item in members}) for members in by_hash.values()),
        default=0,
    )
    required = required_zero_violation_groups(alpha, delta)
    n_test = replay_totals["test_windows"]
    return {
        "episodes": len(episodes),
        "graphs": len(graphs),
        "episodes_with_candidate_window": len(episodes_with_windows),
        "candidate_windows": len(windows),
        "candidate_families": len(by_hash),
        "families_support_ge_3": sum(
            len({item.group_id for item in members}) >= 3
            for members in by_hash.values()
        ),
        "maximum_family_support": max_support,
        "graph_diagnostics": dict(sorted(diagnostics.items())),
        "blocked_window_candidates": dict(sorted(blocked.items())),
        "blocked_by_tool": dict(sorted(blocked_by_tool.items())),
        "held_out_recorded_replay": {
            **dict(replay_totals),
            "pass_rate": replay_totals["test_passed"] / n_test if n_test else None,
            "wrong_rate": replay_totals["test_wrong"] / n_test if n_test else None,
        },
        "family_results": family_rows,
        "exact_gate": {
            "alpha": alpha,
            "delta": delta,
            "minimum_zero_violation_groups": required,
            "max_observed_family_support": max_support,
            "certifiable_families_even_if_zero_violations": sum(
                len({item.group_id for item in members}) >= required
                for members in by_hash.values()
            ),
            "outcome": "RETIRE" if max_support < required else "candidate_present",
        },
        "mining_parameters": {
            "entry_schema": list(entry_schema),
            "max_depth": max_depth,
            "kappa": kappa,
            "w_min": w_min,
            "w_max": w_max,
            "b_min": b_min,
            "min_support_groups": min_support_groups,
            "n_permutations": n_permutations,
        },
        "runtime": {
            "patg_seconds": graph_seconds,
            "total_seconds": elapsed,
            "peak_memory_mib": peak_bytes / (1024 * 1024),
        },
    }
