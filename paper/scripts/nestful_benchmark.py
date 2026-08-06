#!/usr/bin/env python3
"""Reproducible external validation on the pinned NESTFUL benchmark.

This script deliberately evaluates two different questions:

1. Does the repository recover and re-execute value dependencies on executable,
   public nested tool sequences?
2. Would the default exact risk gate certify any NESTFUL family for dispatch?

The first is a structural compiler test.  The second is a deployment-readiness
test.  They must not be conflated: NESTFUL is not production traffic, and recorded
replay is not a live-system safety claim.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import importlib.util
import json
import math
import statistics
import sys
import time
import tracemalloc
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable

import requests


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from guarded_agentic_compaction.graph.provenance import build_all  # noqa: E402
from guarded_agentic_compaction.graph.windows import Family, enumerate_windows  # noqa: E402
from guarded_agentic_compaction.grc.calibrate import GRID, clopper_pearson_upper  # noqa: E402
from guarded_agentic_compaction.grc.contracts import (  # noqa: E402
    grouped_recorded_replay,
    induce_guard,
    induce_verifier,
)
from guarded_agentic_compaction.grc.synthesize import synthesize_program  # noqa: E402
from guarded_agentic_compaction.schema.effects import EffectCatalog  # noqa: E402
from guarded_agentic_compaction.schema.traces import (  # noqa: E402
    Episode,
    EventKind,
    EventNode,
    ExecutionManifest,
    OutcomeLabels,
    TraceEnvelope,
)


NESTFUL_COMMIT = "fc2c4123e73500a56185a5fb354f05d1c8b4890c"
BASE_URL = f"https://raw.githubusercontent.com/IBM/NESTFUL/{NESTFUL_COMMIT}"
FILES = {
    "nestful_data.jsonl": (
        "data_v2/nestful_data.jsonl",
        "e7c9999e2eaaa2bea87776bc55e2b0913a0cf089f4b6817c7644554547df22c1",
    ),
    "basic_functions.py": (
        "data_v2/executable_functions/basic_functions.py",
        "db8048658f7ccd930c691a36dd0831a7d46dbffa2a275932f60af43792128212",
    ),
    "NESTFUL-LICENSE": (
        "LICENSE",
        "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4",
    ),
}

DATA_DIR = ROOT / "paper" / "results" / "datasets" / "nestful"
OUT_DIR = ROOT / "paper" / "results" / "nestful"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch_inputs(force: bool = False) -> dict[str, Any]:
    """Download only the three pinned upstream files used by the experiment."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "dataset": "IBM/NESTFUL",
        "repository": "https://github.com/IBM/NESTFUL",
        "commit": NESTFUL_COMMIT,
        "license": "Apache-2.0",
        "files": {},
    }
    for local_name, (remote_path, expected) in FILES.items():
        target = DATA_DIR / local_name
        if force or not target.exists() or sha256(target) != expected:
            response = requests.get(f"{BASE_URL}/{remote_path}", timeout=120)
            response.raise_for_status()
            target.write_bytes(response.content)
        observed = sha256(target)
        if observed != expected:
            raise RuntimeError(f"checksum mismatch for {local_name}: {observed}")
        manifest["files"][local_name] = {
            "source_path": remote_path,
            "sha256": observed,
            "bytes": target.stat().st_size,
        }
    (DATA_DIR / "source_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest


def load_rows() -> list[dict[str, Any]]:
    with (DATA_DIR / "nestful_data.jsonl").open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def basic_function_names() -> set[str]:
    tree = ast.parse((DATA_DIR / "basic_functions.py").read_text())
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


def load_basic_module() -> Any:
    path = DATA_DIR / "basic_functions.py"
    spec = importlib.util.spec_from_file_location("nestful_basic_functions", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load NESTFUL basic functions")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reference(value: Any) -> tuple[int, str] | None:
    if not isinstance(value, str) or not value.startswith("$var_"):
        return None
    token = value.strip("$")
    head, _, field = token.partition(".")
    try:
        return int(head.removeprefix("var_")) - 1, field or "result"
    except ValueError:
        return None


def dependency_signature(row: dict[str, Any]) -> str:
    steps: list[str] = []
    for index, call in enumerate(row["output"]):
        args: list[str] = []
        for name, value in call["arguments"].items():
            ref = reference(value)
            if ref is None:
                args.append(f"{name}:entry:{type(value).__name__}")
            else:
                args.append(f"{name}:step{index-ref[0]}:{ref[1]}")
        steps.append(f"{call['name']}({','.join(args)})")
    return " -> ".join(steps)


def sequence_signature(row: dict[str, Any]) -> str:
    return " -> ".join(call["name"] for call in row["output"])


def _tool_spec(row: dict[str, Any], name: str) -> dict[str, Any]:
    for spec in row["tools"]:
        if spec["name"] == name:
            return spec
    raise KeyError(name)


def execute_row(row: dict[str, Any], module: Any) -> tuple[list[dict[str, Any]], list[Any]]:
    """Execute a NESTFUL gold sequence using the benchmark's positional convention."""

    outputs: list[dict[str, Any]] = []
    resolved_arguments: list[dict[str, Any]] = []
    for index, call in enumerate(row["output"]):
        resolved: dict[str, Any] = {}
        for name, value in call["arguments"].items():
            ref = reference(value)
            if ref is None:
                resolved[name] = value
            else:
                source, field = ref
                resolved[name] = outputs[source][field]
        fn = getattr(module, call["name"])
        result = fn(*resolved.values())
        fields = list(_tool_spec(row, call["name"])["output_parameters"])
        if len(fields) != 1:
            raise ValueError(f"multi-output basic function: {call['name']}")
        outputs.append({fields[0]: result})
        resolved_arguments.append(resolved)
    return resolved_arguments, outputs


def _entry_state(row: dict[str, Any]) -> dict[str, Any]:
    """Stable paths by call and slot; references are intentionally omitted."""

    entry: dict[str, Any] = {}
    for index, call in enumerate(row["output"]):
        step: dict[str, Any] = {}
        for name, value in call["arguments"].items():
            if reference(value) is None:
                step[name] = value
        if step:
            entry[f"s{index}"] = step
    return {"inputs": entry}


def build_episode(
    row: dict[str, Any],
    resolved: list[dict[str, Any]],
    outputs: list[Any],
    manifest: ExecutionManifest,
    ordinal: int,
) -> Episode:
    events: list[EventNode] = []
    cursor = 0
    for step, (call, args, result) in enumerate(zip(row["output"], resolved, outputs)):
        call_id = f"{row['sample_id']}-c{step}"
        events.extend(
            [
                EventNode(
                    node_id=f"{row['sample_id']}-e{cursor}",
                    kind=EventKind.MODEL_REQ,
                    index=cursor,
                    input={"tools": [spec["name"] for spec in row["tools"]]},
                ),
                EventNode(
                    node_id=f"{row['sample_id']}-e{cursor+1}",
                    kind=EventKind.MODEL_RESP,
                    index=cursor + 1,
                    output={"name": call["name"], "arguments": args},
                ),
                EventNode(
                    node_id=f"{row['sample_id']}-e{cursor+2}",
                    kind=EventKind.TOOL_CALL,
                    index=cursor + 2,
                    tool=call["name"],
                    input=args,
                    call_id=call_id,
                    declared_effect="PURE",
                ),
                EventNode(
                    node_id=f"{row['sample_id']}-e{cursor+3}",
                    kind=EventKind.TOOL_RESULT,
                    index=cursor + 3,
                    tool=call["name"],
                    output=result,
                    call_id=call_id,
                    declared_effect="PURE",
                ),
            ]
        )
        cursor += 4
    day = date(2025, 1, 1) + timedelta(days=ordinal % 180)
    envelope = TraceEnvelope(
        trace_id=f"nestful-{row['sample_id']}",
        episode_id=row["sample_id"],
        group_id=row["sample_id"],
        manifest_id=manifest.manifest_id,
        principal="nestful-public-benchmark",
        tenant_partition="public",
        policy_version="nestful-v2",
        day=day.isoformat(),
        privacy_class="public",
        external_state_version=NESTFUL_COMMIT,
    )
    return Episode(
        envelope=envelope,
        manifest=manifest,
        entry_state=_entry_state(row),
        events=events,
        outcome=OutcomeLabels(task_success=True, semantic_score=1.0),
        attributes={
            "source": "NESTFUL-v2",
            "dependency_signature": dependency_signature(row),
            "n_calls": len(row["output"]),
        },
    )


def count_support(signatures: Iterable[str]) -> dict[str, Any]:
    counts = Counter(signatures)
    support_hist = Counter(counts.values())
    return {
        "n_unique": len(counts),
        "n_families_support_ge_2": sum(n for support, n in support_hist.items() if support >= 2),
        "n_families_support_ge_5": sum(n for support, n in support_hist.items() if support >= 5),
        "n_families_support_ge_10": sum(n for support, n in support_hist.items() if support >= 10),
        "max_support": max(counts.values(), default=0),
        "covered_samples_support_ge_5": sum(
            support for support in counts.values() if support >= 5
        ),
        "top": [{"signature": sig, "support": n} for sig, n in counts.most_common(12)],
    }


def required_zero_violation_groups(alpha: float = 0.05, delta: float = 0.10) -> int:
    conf = 1.0 - delta / len(GRID)
    n = 1
    while clopper_pearson_upper(0, n, conf) > alpha:
        n += 1
    return n


def split_windows(windows: list[Any]) -> tuple[list[Any], list[Any], list[Any]]:
    ordered = sorted(windows, key=lambda w: w.episode.episode_id)
    n = len(ordered)
    n_train = max(3, int(math.floor(0.60 * n)))
    n_dev = max(1, int(math.floor(0.20 * n)))
    if n_train + n_dev >= n:
        n_train = max(2, n - 2)
        n_dev = 1
    return ordered[:n_train], ordered[n_train : n_train + n_dev], ordered[n_train + n_dev :]


def evaluate_compiler(
    episodes: list[Episode],
    rows_by_id: dict[str, dict[str, Any]],
    catalog: EffectCatalog,
    manifest: ExecutionManifest,
) -> dict[str, Any]:
    tracemalloc.start()
    started = time.perf_counter()
    graphs, policy = build_all(episodes, catalog, max_depth=2, kappa=3)
    graph_seconds = time.perf_counter() - started

    provenance = Counter()
    full_windows: list[Any] = []
    blocked = Counter()
    blocked_by_tool = Counter()
    no_full_window = Counter()

    for graph in graphs:
        row = rows_by_id[graph.episode.episode_id]
        for step, call in enumerate(row["output"]):
            call_pos = 4 * step + 2
            for arg, raw in call["arguments"].items():
                ref = reference(raw)
                if ref is None:
                    continue
                provenance["dependency_slots"] += 1
                slot = graph.slots.get((call_pos, arg))
                if slot is None:
                    provenance["missing_slot"] += 1
                    continue
                provenance[f"mark_{slot.mark.lower()}"] += 1
                expected_result_pos = 4 * ref[0] + 3
                producers = {edge.producer.event_index for edge in slot.candidates}
                # Distinguish three outcomes that a single "recovered" counter conflates.
                # Counting a slot as recovered whenever the truth appears anywhere in the
                # candidate set measures *candidate recall*, not dependency
                # reconstruction: a slot with the right producer among five candidates is
                # not resolved. Report resolution and ambiguity separately.
                provenance["candidate_edges"] += len(slot.candidates)
                if expected_result_pos in producers:
                    provenance["expected_producer_recovered"] += 1
                    if len(producers) == 1:
                        provenance["expected_producer_unique"] += 1
                    else:
                        provenance["expected_producer_ambiguous"] += 1
                elif slot.candidates:
                    provenance["expected_producer_absent"] += 1
                if slot.candidates:
                    provenance["has_any_candidate"] += 1
                else:
                    provenance["no_candidate"] += 1

        windows = enumerate_windows(
            graph,
            catalog,
            entry_schema=("inputs",),
            w_min=2,
            w_max=53,
            b_min=2,
            blocked=blocked,
            blocked_by_tool=blocked_by_tool,
        )
        expected_calls = int(graph.episode.attributes["n_calls"])
        candidates = [w for w in windows if w.a == 0 and w.n_tool_events == expected_calls]
        if candidates:
            full_windows.append(max(candidates, key=lambda w: (w.b, len(w.steps))))
        else:
            marks = [slot.mark for slot in graph.slots.values()]
            if "UNGROUNDED" in marks:
                no_full_window["ungrounded_slot"] += 1
            elif "AMBIGUOUS" in marks:
                no_full_window["ambiguous_slot"] += 1
            else:
                no_full_window["other_window_rejection"] += 1

    by_hash: dict[str, list[Any]] = defaultdict(list)
    for window in full_windows:
        by_hash[window.canon_hash].append(window)

    family_rows: list[dict[str, Any]] = []
    test_totals = Counter()
    synth_failures = Counter()
    programs = []
    for family_hash, windows in sorted(by_hash.items()):
        if len({w.group_id for w in windows}) < 5:
            continue
        family = Family(canon_hash=family_hash, windows=windows)
        train, dev, test = split_windows(windows)
        if not test:
            synth_failures["no_test_split"] += 1
            continue
        synth = synthesize_program(family, train, catalog, policy, n_permutations=100)
        row: dict[str, Any] = {
            "family_hash": family_hash,
            "support": family.support,
            "tools": " -> ".join(family.tools),
            "train": len(train),
            "dev": len(dev),
            "test": len(test),
            "synthesis": "ok" if synth.ok else synth.reason,
            "replay_passed": 0,
            "replay_wrong": 0,
            "replay_abstained": 0,
        }
        test_totals["families_attempted"] += 1
        if not synth.ok or synth.program is None:
            synth_failures[synth.reason.split(":", 1)[0]] += 1
            family_rows.append(row)
            continue
        guard = induce_guard(synth.program, train, manifest, catalog, partition_by=())
        verifier = induce_verifier(synth.program, train, synth.names, catalog)
        replay = grouped_recorded_replay(
            synth.program, guard, verifier, test, synth.names, catalog
        )
        row.update(
            {
                "program_size": synth.program.size,
                "program_steps": len(synth.program.steps),
                "replay_passed": replay.passed,
                "replay_wrong": replay.wrong,
                "replay_abstained": replay.abstained,
                "replay_effect_mismatch": replay.effect_mismatch,
            }
        )
        test_totals["families_synthesized"] += 1
        test_totals["test_windows"] += replay.n
        test_totals["test_passed"] += replay.passed
        test_totals["test_wrong"] += replay.wrong
        test_totals["test_abstained"] += replay.abstained
        programs.append(
            {
                "family_hash": family_hash,
                "support": family.support,
                "program": synth.program.to_dict(),
                "pretty": synth.program.pretty(),
                "synthesis_stats": synth.stats,
            }
        )
        family_rows.append(row)

    total_seconds = time.perf_counter() - started
    _current, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in family_rows for key in row})
    with (OUT_DIR / "family_results.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(family_rows)
    (OUT_DIR / "synthesized_programs.json").write_text(
        json.dumps(programs, indent=2, sort_keys=True, default=str) + "\n"
    )

    max_support = max((len(windows) for windows in by_hash.values()), default=0)
    required = required_zero_violation_groups()
    return {
        "n_episodes": len(episodes),
        "n_graphs": len(graphs),
        "n_full_windows": len(full_windows),
        "full_window_rate": len(full_windows) / len(episodes) if episodes else 0.0,
        "no_full_window": dict(no_full_window),
        "blocked_window_candidates": dict(blocked),
        "blocked_by_tool": dict(blocked_by_tool),
        "provenance": {
            **dict(provenance),
            "expected_producer_recall": provenance["expected_producer_recovered"]
            / provenance["dependency_slots"]
            if provenance["dependency_slots"]
            else 0.0,
            "unique_resolution_rate": provenance["expected_producer_unique"]
            / provenance["dependency_slots"]
            if provenance["dependency_slots"]
            else 0.0,
            "ambiguous_containing_truth_rate": provenance["expected_producer_ambiguous"]
            / provenance["dependency_slots"]
            if provenance["dependency_slots"]
            else 0.0,
            "candidate_edge_precision": provenance["expected_producer_recovered"]
            / provenance["candidate_edges"]
            if provenance["candidate_edges"]
            else 0.0,
            "candidate_coverage": provenance["has_any_candidate"]
            / provenance["dependency_slots"]
            if provenance["dependency_slots"]
            else 0.0,
        },
        "compiler_families": {
            "n_unique": len(by_hash),
            "n_support_ge_5": sum(1 for windows in by_hash.values() if len(windows) >= 5),
            "max_support": max_support,
        },
        "synthesis_failures": dict(synth_failures),
        "held_out_replay": {
            **dict(test_totals),
            "pass_rate": test_totals["test_passed"] / test_totals["test_windows"]
            if test_totals["test_windows"]
            else 0.0,
            "wrong_rate": test_totals["test_wrong"] / test_totals["test_windows"]
            if test_totals["test_windows"]
            else 0.0,
        },
        "exact_gate": {
            "alpha": 0.05,
            "delta": 0.10,
            "threshold_grid_size": len(GRID),
            "minimum_zero_violation_groups": required,
            "max_observed_family_support": max_support,
            "families_certifiable_even_with_zero_violations": sum(
                1 for windows in by_hash.values() if len(windows) >= required
            ),
            "default_gate_outcome": "RETIRE" if max_support < required else "candidate_present",
        },
        "runtime": {
            "patg_seconds": graph_seconds,
            "total_seconds": total_seconds,
            "peak_memory_mib": peak_bytes / (1024 * 1024),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-download", action="store_true")
    args = parser.parse_args()

    source_manifest = fetch_inputs(args.force_download)
    rows = load_rows()
    basic_names = basic_function_names()
    module = load_basic_module()

    lengths = [len(row["output"]) for row in rows]
    basic_rows = [
        row for row in rows if all(call["name"] in basic_names for call in row["output"])
    ]
    seq_support = count_support(sequence_signature(row) for row in rows)
    dep_support = count_support(dependency_signature(row) for row in rows)
    basic_dep_support = count_support(dependency_signature(row) for row in basic_rows)

    catalog = EffectCatalog.from_dict(
        {
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
        }
    )
    manifest = ExecutionManifest(
        manifest_id="nestful-v2-pinned-basic-functions",
        commit=NESTFUL_COMMIT,
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
    execution_failures: list[dict[str, str]] = []
    rows_by_id: dict[str, dict[str, Any]] = {}
    for ordinal, row in enumerate(basic_rows):
        try:
            resolved, outputs = execute_row(row, module)
            episode = build_episode(row, resolved, outputs, manifest, ordinal)
        except Exception as exc:
            execution_failures.append(
                {"sample_id": row["sample_id"], "error": f"{type(exc).__name__}: {exc}"}
            )
            continue
        episodes.append(episode)
        rows_by_id[row["sample_id"]] = row

    compiler = evaluate_compiler(episodes, rows_by_id, catalog, manifest)
    result = {
        "run": {
            "script": "paper/scripts/nestful_benchmark.py",
            "source_commit": NESTFUL_COMMIT,
            "source_manifest_sha256": sha256(DATA_DIR / "source_manifest.json"),
            "python": sys.version,
            "evidence_class": "public executable structural benchmark; recorded replay",
            "not_evidence_for": [
                "live provider behavior",
                "production traffic",
                "canary safety",
                "end-to-end task planning quality",
            ],
        },
        "dataset": {
            "n_rows": len(rows),
            "n_basic_function_rows": len(basic_rows),
            "n_executed_basic_rows": len(episodes),
            "n_execution_failures": len(execution_failures),
            "sequence_length": {
                "min": min(lengths),
                "median": statistics.median(lengths),
                "mean": statistics.mean(lengths),
                "max": max(lengths),
            },
            "exact_tool_sequence_support": seq_support,
            "dependency_shape_support": dep_support,
            "basic_subset_dependency_shape_support": basic_dep_support,
        },
        "compiler": compiler,
        "execution_failures": execution_failures[:30],
        "source_manifest": source_manifest,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "results.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str) + "\n"
    )
    print(json.dumps(result, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
