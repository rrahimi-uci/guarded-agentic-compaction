#!/usr/bin/env python3
"""Executable, privacy-preserving API-Bank compiler evaluation.

The pinned API-Bank level-1/2 corpus contains complete reference calls and retained
results.  This script (1) normalizes them into the framework-neutral Episode IR,
(2) runs PATG/window mining and held-out recorded replay, and (3) independently
re-executes the pinned upstream API classes where their declared dependencies are
available.  Only aggregates and hashes are written: prompts, arguments, passwords,
tokens, tool outputs, and exception messages are intentionally excluded.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib
import json
import os
import statistics
import sys
import time
import tracemalloc
from collections import Counter, defaultdict
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from benchmarks.external.adapters import load_api_bank  # noqa: E402
from guarded_agentic_compaction.benchmarking.external import (  # noqa: E402
    ReferenceAction,
    ReferenceTask,
    reference_task_to_episode,
)
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
    ExecutionManifest,
    OutcomeLabels,
    flatten,
)


REVISION = "483554eae102996f5ec1f4feab4e78ef29c2a394"
CATALOG_PATH = ROOT / "benchmarks" / "contracts" / "effects" / "api_bank.yaml"
DEFAULT_OUT = ROOT / "paper" / "results" / "external_benchmarks" / "api_bank_execution.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


def _audit_tasks(
    tasks: Sequence[ReferenceTask], catalog: EffectCatalog
) -> tuple[ReferenceTask, ...]:
    audited: list[ReferenceTask] = []
    for task in tasks:
        actions = tuple(
            ReferenceAction(
                name=action.name,
                arguments=_plain(action.arguments),
                output=_plain(action.output),
                output_observed=action.output_observed,
                effect=catalog.effect_of(action.name),
                requestor=action.requestor,
                turn=action.turn,
                metadata=_plain(action.metadata),
            )
            for action in task.actions
        )
        audited.append(
            ReferenceTask(
                benchmark=task.benchmark,
                task_id=task.task_id,
                group_id=task.group_id,
                source_revision=task.source_revision,
                substrate=task.substrate,
                actions=actions,
                prompt=task.prompt,
                metadata=_plain(task.metadata),
            )
        )
    return tuple(audited)


def _entry_state(task: ReferenceTask) -> tuple[dict[str, Any], int]:
    """Retain gold-plan literals while excluding values observed in prior results."""

    prior_values: set[str] = set()
    inputs: dict[str, Any] = {}
    reused_slots = 0
    for index, action in enumerate(task.actions):
        retained: dict[str, Any] = {}
        for path, value in flatten(_plain(action.arguments)):
            if isinstance(value, (dict, list)):
                continue
            key = json.dumps(value, sort_keys=True, default=str)
            if key in prior_values:
                reused_slots += 1
            else:
                retained[path] = value
        if retained:
            inputs[f"s{index}"] = retained
        for _, value in flatten(_plain(action.output)):
            if not isinstance(value, (dict, list)):
                prior_values.add(json.dumps(value, sort_keys=True, default=str))
    return {"inputs": inputs}, reused_slots


def _manifest(catalog: EffectCatalog, tools: Sequence[str]) -> ExecutionManifest:
    return ExecutionManifest(
        manifest_id="api-bank-pinned-level1-level2-recorded",
        commit=REVISION,
        model="gold-reference-plan-no-model-inference",
        prompt_hash="withheld-sensitive-synthetic-dialogues",
        tools_hash=hashlib.sha256("|".join(sorted(tools)).encode()).hexdigest()[:16],
        policy_hash="public-benchmark-structural-evaluation",
        guardrail_hash="none-recorded-replay-only",
        effect_catalog_version=catalog.catalog_version,
        entry_contract_version="gold-plan-literals-by-call-slot-v1",
        sdk_version="not-applicable",
        tracer_version="paper-api-bank-adapter-v1",
    )


def _required_zero_violation_groups(alpha: float = 0.05, delta: float = 0.10) -> int:
    confidence = 1.0 - delta / len(GRID)
    groups = 1
    while clopper_pearson_upper(0, groups, confidence) > alpha:
        groups += 1
    return groups


def _evaluate_compiler(
    episodes: Sequence[Episode], catalog: EffectCatalog, manifest: ExecutionManifest
) -> dict[str, Any]:
    tracemalloc.start()
    started = time.perf_counter()
    graphs, policy = build_all(episodes, catalog, max_depth=2, kappa=3)
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
            entry_schema=("inputs",),
            w_min=2,
            w_max=12,
            b_min=2,
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
        if len({item.group_id for item in independent}) < 3:
            continue
        split = max(2, len(independent) - max(1, len(independent) // 4))
        train, test = independent[:split], independent[split:]
        if not test:
            continue
        family = Family(canon_hash=family_hash, windows=independent)
        synthesis = synthesize_program(
            family, train, catalog, policy, n_permutations=25
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
    required = _required_zero_violation_groups()
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
            "alpha": 0.05,
            "delta": 0.10,
            "minimum_zero_violation_groups": required,
            "max_observed_family_support": max_support,
            "certifiable_families_even_if_zero_violations": sum(
                len({item.group_id for item in members}) >= required
                for members in by_hash.values()
            ),
            "outcome": "RETIRE" if max_support < required else "candidate_present",
        },
        "runtime": {
            "patg_seconds": graph_seconds,
            "total_seconds": elapsed,
            "peak_memory_mib": peak_bytes / (1024 * 1024),
        },
    }


def _class_modules(api_root: Path) -> dict[str, str]:
    modules: dict[str, str] = {}
    for source in sorted((api_root / "apis").glob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                modules[node.name] = source.stem
    return modules


@contextmanager
def _upstream_imports(api_root: Path) -> Iterator[None]:
    before = list(sys.path)
    previous = Path.cwd()
    sys.path.insert(0, str(api_root))
    os.chdir(api_root)
    try:
        yield
    finally:
        os.chdir(previous)
        sys.path[:] = before
        for name in tuple(sys.modules):
            if name == "apis" or name.startswith("apis."):
                sys.modules.pop(name, None)


def _load_databases(api_root: Path) -> dict[str, Any]:
    return {
        source.stem: json.loads(source.read_text(encoding="utf-8"))
        for source in sorted((api_root / "init_database").glob("*.json"))
    }


def _execute_upstream(
    tasks: Sequence[ReferenceTask], api_root: Path
) -> dict[str, Any]:
    """Re-run official API class methods, preserving only aggregate outcomes."""

    modules = _class_modules(api_root)
    action_totals: Counter[str] = Counter()
    task_totals: Counter[str] = Counter()
    by_tool: dict[str, Counter[str]] = defaultdict(Counter)
    start = time.perf_counter()
    with _upstream_imports(api_root):
        for task in tasks:
            databases = _load_databases(api_root)
            instances: dict[str, Any] = {}
            task_ok = True

            def instance(name: str) -> Any:
                if name in instances:
                    return instances[name]
                module_name = modules[name]
                cls = getattr(importlib.import_module(f"apis.{module_name}"), name)
                arguments: list[Any] = []
                database_name = getattr(cls, "database_name", None)
                if database_name in databases:
                    arguments.append(databases[database_name])
                if name != "CheckToken" and "token" in getattr(
                    cls, "input_parameters", {}
                ):
                    arguments.append(instance("CheckToken"))
                instances[name] = cls(*arguments)
                return instances[name]

            for action in task.actions:
                action_totals["attempted"] += 1
                by_tool[action.name]["attempted"] += 1
                try:
                    tool = instance(action.name)
                    declared = getattr(tool, "input_parameters", {})
                    processed: dict[str, Any] = {}
                    for key, value in _plain(action.arguments).items():
                        kind = declared[key]["type"]
                        if kind == "int":
                            processed[key] = int(value)
                        elif kind == "float":
                            processed[key] = float(value)
                        elif kind == "bool":
                            # Preserve the pinned ToolManager's exact conversion.
                            processed[key] = value == "True"
                        else:
                            processed[key] = value
                    observed = tool.call(**processed)
                    correct = bool(
                        tool.check_api_call_correctness(observed, _plain(action.output))
                    )
                except ModuleNotFoundError:
                    action_totals["dependency_unavailable"] += 1
                    by_tool[action.name]["dependency_unavailable"] += 1
                    task_ok = False
                    continue
                except Exception as exc:
                    category = f"execution_error:{type(exc).__name__}"
                    action_totals[category] += 1
                    by_tool[action.name][category] += 1
                    task_ok = False
                    continue
                outcome = "passed" if correct else "mismatch"
                action_totals[outcome] += 1
                by_tool[action.name][outcome] += 1
                task_ok = task_ok and correct
            task_totals["passed" if task_ok else "not_fully_replayed"] += 1
    attempted = action_totals["attempted"]
    return {
        "tasks": len(tasks),
        "task_outcomes": dict(task_totals),
        "action_outcomes": dict(action_totals),
        "exact_action_pass_rate": (
            action_totals["passed"] / attempted if attempted else None
        ),
        "by_tool": {name: dict(counts) for name, counts in sorted(by_tool.items())},
        "runtime_seconds": time.perf_counter() - start,
        "execution_kind": "pinned upstream Python API methods with fresh task fixtures",
        "provider_calls": 0,
        "serialized_values": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--skip-upstream-execution", action="store_true")
    args = parser.parse_args()

    api_root = args.source_root / "damo" / "api-bank"
    if not api_root.is_dir():
        raise SystemExit(f"pinned API-Bank checkout not found under {args.source_root}")
    catalog = EffectCatalog.from_yaml(CATALOG_PATH)
    tasks = _audit_tasks(load_api_bank(api_root.parent, REVISION), catalog)
    tool_names = sorted({action.name for task in tasks for action in task.actions})
    coverage = catalog.validate_coverage(tool_names)
    if coverage["undeclared"]:
        raise RuntimeError(f"effect catalog is incomplete: {coverage['undeclared']}")
    manifest = _manifest(catalog, tool_names)
    episodes: list[Episode] = []
    reused_slots = 0
    for task in tasks:
        entry_state, reused = _entry_state(task)
        reused_slots += reused
        episodes.append(
            reference_task_to_episode(
                task,
                manifest=manifest,
                outcome=OutcomeLabels(task_success=True, semantic_score=1.0),
                entry_state=entry_state,
            )
        )

    lengths = [len(task.actions) for task in tasks]
    report = {
        "schema": "agent-compaction-external-execution/v1",
        "benchmark": "API-Bank level-1/2 given-description dialogues",
        "source_revision": REVISION,
        "source_license": "Apache-2.0",
        "source_license_sha256": _sha256(api_root / "LICENSE"),
        "effect_catalog": catalog.catalog_version,
        "effect_catalog_sha256": _sha256(CATALOG_PATH),
        "dataset": {
            "tasks": len(tasks),
            "observed_calls": sum(lengths),
            "unique_tools": len(tool_names),
            "calls_per_task_min": min(lengths),
            "calls_per_task_median": statistics.median(lengths),
            "calls_per_task_max": max(lengths),
            "observed_cross_call_value_reuse_slots": reused_slots,
            "complete_observed_traces": sum(
                all(action.output_observed for action in task.actions) for task in tasks
            ),
        },
        "catalog_coverage": coverage,
        "compiler": _evaluate_compiler(episodes, catalog, manifest),
        "upstream_execution": (
            {"status": "not_run_by_request"}
            if args.skip_upstream_execution
            else _execute_upstream(tasks, api_root)
        ),
        "evidence": {
            "class": "public executable simulator plus complete recorded traces",
            "compiler_execution": True,
            "provider_calls": 0,
            "prompts_arguments_outputs_serialized": False,
            "is_real_world_demo": False,
            "is_live_provider_evaluation": False,
            "licenses_end_to_end_planning_quality_claim": False,
            "licenses_production_safety_claim": False,
            "measures": [
                "trace normalization",
                "provenance and candidate mining",
                "held-out recorded replay where support permits",
                "pinned upstream API execution compatibility",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "output": str(args.output.relative_to(ROOT)),
                "tasks": len(tasks),
                "compiler": report["compiler"],
                "upstream_execution": report["upstream_execution"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
