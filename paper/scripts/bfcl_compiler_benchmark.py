#!/usr/bin/env python3
"""Provider-free BFCL v4 multi-turn-base compiler evaluation with observed results.

The pinned BFCL multi-turn categories ship an executable stateful backend: each task
carries an ``initial_config`` snapshot and a list of involved Python API classes, and the
official ``execute_multi_turn_func_call`` helper runs a turn's calls against instances
loaded from that snapshot.  Executing the *official gold plan* through that helper turns
BFCL's reference calls into complete observed traces, which is the one thing the read-only
compiler requires and the structural row in ``bfcl_structural_benchmark.py`` cannot supply.

This script therefore (1) executes every gold plan and retains each call's observed
result, (2) runs two mechanical safety audits against the signed effect catalog, (3) checks
that a second independent execution pass reproduces every result byte for byte, and
(4) runs the same provenance/window/synthesis/held-out-replay pipeline used for API-Bank.

The predeclared expectation, decision rule, and claim boundary are in
``paper/supplementary/bfcl-compiler-protocol.md``; this script records whether the observed
gate outcome matched the prediction it was written against.  No provider call is made.
Prompts, arguments, observed results, and scenario state are never serialized: the report
retains counts, hashes, structural field names, and per-family aggregates only.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import inspect
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from benchmarks.external.compiler_eval import (  # noqa: E402
    evaluate_compiler,
    required_zero_violation_groups,
)
from guarded_agentic_compaction.benchmarking.external import (  # noqa: E402
    EvidenceSubstrate,
    ReferenceAction,
    ReferenceTask,
    reference_task_to_episode,
)
from guarded_agentic_compaction.schema.effects import EffectCatalog  # noqa: E402
from guarded_agentic_compaction.schema.traces import (  # noqa: E402
    Episode,
    ExecutionManifest,
    OutcomeLabels,
    flatten,
)


REVISION = "6ea57973c7a6097fd7c5915698c54c17c5b1b6c8"
CATALOG_PATH = ROOT / "benchmarks" / "contracts" / "effects" / "bfcl.yaml"
PROTOCOL_PATH = ROOT / "paper" / "supplementary" / "bfcl-compiler-protocol.md"
DEFAULT_OUT = (
    ROOT / "paper" / "results" / "external_benchmarks" / "bfcl_compiler_execution.json"
)
CATEGORY = "multi_turn_base"
ERROR_PREFIX = "Error during execution:"

# Predeclared in the protocol before the compiler was run on this corpus.
PREDECLARED_GATE_OUTCOME = "RETIRE"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _display(path: Path) -> str:
    """Repository-relative when possible; a smoke run may write outside the tree."""

    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


# ---------------------------------------------------------------------------
# upstream backend
# ---------------------------------------------------------------------------


class Backend:
    """Thin, explicit wrapper over the pinned BFCL executable backend."""

    def __init__(self, checkout: Path) -> None:
        if not checkout.is_dir():
            raise SystemExit(f"pinned BFCL checkout is unavailable at {checkout}")
        sys.path.insert(0, str(checkout))
        from bfcl_eval.constants.executable_backend_config import (  # noqa: PLC0415
            CLASS_FILE_PATH_MAPPING,
            STATELESS_CLASSES,
        )
        from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils import (  # noqa: PLC0415
            execute_multi_turn_func_call,
        )

        self.checkout = checkout
        self.class_file_mapping = dict(CLASS_FILE_PATH_MAPPING)
        self.stateless_classes = frozenset(STATELESS_CLASSES)
        self._execute = execute_multi_turn_func_call
        self._signatures: dict[str, inspect.Signature] = {}
        self._owner: dict[str, str] = {}

    def bind_classes(self, class_names: Iterable[str]) -> None:
        """Record the method -> class map, rejecting any cross-class name collision."""

        for class_name in sorted(set(class_names)):
            module = importlib.import_module(self.class_file_mapping[class_name])
            cls = getattr(module, class_name)
            for method_name, method in inspect.getmembers(cls, inspect.isfunction):
                if method_name.startswith("_"):
                    continue
                owner = self._owner.setdefault(method_name, class_name)
                if owner != class_name:
                    raise RuntimeError(
                        f"method name {method_name} is not unique across involved classes"
                    )
                self._signatures[f"{class_name}.{method_name}"] = inspect.signature(method)

    def qualified(self, method_name: str) -> str:
        owner = self._owner.get(method_name)
        if owner is None:
            raise RuntimeError(f"gold plan calls undeclared method {method_name}")
        return f"{owner}.{method_name}"

    def signature(self, qualified_name: str) -> inspect.Signature:
        return self._signatures[qualified_name]

    def run(
        self,
        calls: Sequence[str],
        question: Mapping[str, Any],
        *,
        namespace: str,
    ) -> list[str]:
        """Execute calls in order against this namespace's persistent instances."""

        results, _instances = self._execute(
            func_call_list=list(calls),
            initial_config=question["initial_config"],
            involved_classes=question["involved_classes"],
            model_name=namespace,
            test_entry_id=str(question["id"]),
            long_context=False,
            is_evaL_run=False,
        )
        return list(results)

    def instances(
        self, question: Mapping[str, Any], *, namespace: str
    ) -> dict[str, Any]:
        _results, instances = self._execute(
            func_call_list=[],
            initial_config=question["initial_config"],
            involved_classes=question["involved_classes"],
            model_name=namespace,
            test_entry_id=str(question["id"]),
            long_context=False,
            is_evaL_run=False,
        )
        return dict(instances)


def _snapshot(instances: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    """Serialize observable instance state for mutation detection only."""

    out: dict[str, dict[str, str]] = {}
    for class_name, instance in instances.items():
        state: dict[str, str] = {}
        for field, value in vars(instance).items():
            if field == "_random":
                state[field] = repr(value.getstate())
                continue
            try:
                state[field] = json.dumps(value, sort_keys=True, default=repr)
            except (TypeError, ValueError):
                state[field] = repr(value)
        out[class_name] = state
    return out


def _call_name_and_arguments(
    call: str, backend: Backend
) -> tuple[str, dict[str, Any]]:
    """Parse one gold call string into a qualified name and named arguments."""

    node = ast.parse(call.strip(), mode="eval").body
    if not isinstance(node, ast.Call):
        raise RuntimeError("gold reference entry is not a call expression")
    func = node.func
    method_name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
    qualified = backend.qualified(method_name)
    arguments: dict[str, Any] = {}
    for keyword in node.keywords:
        if keyword.arg is None:
            raise RuntimeError("gold reference call uses argument unpacking")
        arguments[keyword.arg] = ast.literal_eval(keyword.value)
    if node.args:
        parameters = [
            name
            for name in backend.signature(qualified).parameters
            if name != "self"
        ]
        for position, value in enumerate(node.args):
            arguments[parameters[position]] = ast.literal_eval(value)
    return qualified, arguments


def _parse_observed(result: str) -> tuple[Any, str]:
    """Return the structured observed value and how it was recovered.

    The string is exactly what the upstream harness would have shown the model, so an
    unparseable payload is retained verbatim rather than dropped or reshaped.
    """

    try:
        return json.loads(result), "json"
    except (TypeError, ValueError):
        pass
    try:
        return ast.literal_eval(result), "literal"
    except (SyntaxError, ValueError):
        return result, "raw_string"


# ---------------------------------------------------------------------------
# corpus construction
# ---------------------------------------------------------------------------


def _build_corpus(
    backend: Backend,
    questions: Sequence[Mapping[str, Any]],
    answers: Mapping[str, list[list[str]]],
    catalog: EffectCatalog,
) -> tuple[tuple[ReferenceTask, ...], dict[str, Any]]:
    """Execute every gold plan, retaining observed results and both safety audits."""

    tasks: list[ReferenceTask] = []
    parse_kinds: Counter[str] = Counter()
    errors: Counter[str] = Counter()
    mutating: Counter[str] = Counter()
    rng_advancing: Counter[str] = Counter()
    mutated_fields: dict[str, set[str]] = defaultdict(set)
    calls_by_tool: Counter[str] = Counter()
    started = time.perf_counter()

    for question in questions:
        task_id = str(question["id"])
        namespace = "gac_observe"
        actions: list[ReferenceAction] = []
        instances = backend.instances(question, namespace=namespace)
        before = _snapshot(instances)
        for turn_index, turn_calls in enumerate(answers[task_id]):
            for call in turn_calls:
                qualified, arguments = _call_name_and_arguments(call, backend)
                calls_by_tool[qualified] += 1
                observed = backend.run([call], question, namespace=namespace)[0]
                if observed.startswith(ERROR_PREFIX):
                    errors[qualified] += 1
                after = _snapshot(backend.instances(question, namespace=namespace))
                for class_name, fields in after.items():
                    for field, value in fields.items():
                        if before.get(class_name, {}).get(field) == value:
                            continue
                        if field == "_random":
                            rng_advancing[qualified] += 1
                        else:
                            mutating[qualified] += 1
                            mutated_fields[qualified].add(f"{class_name}.{field}")
                before = after
                value, parse_kind = _parse_observed(observed)
                parse_kinds[parse_kind] += 1
                actions.append(
                    ReferenceAction(
                        name=qualified,
                        arguments=arguments,
                        output=value,
                        output_observed=True,
                        effect=catalog.effect_of(qualified),
                        turn=turn_index,
                        metadata={"observed_output_parse": parse_kind},
                    )
                )
        tasks.append(
            ReferenceTask(
                benchmark="bfcl_v4_multi_turn_base_executed",
                task_id=task_id,
                group_id=f"bfcl:{task_id}",
                source_revision=REVISION,
                substrate=EvidenceSubstrate.EXECUTABLE_PUBLIC_BENCHMARK,
                actions=tuple(actions),
                prompt="\n".join(
                    str(message.get("content", ""))
                    for turn in question.get("question", [])
                    for message in turn
                    if isinstance(message, Mapping) and message.get("role") == "user"
                ),
                metadata={
                    "involved_classes": list(question.get("involved_classes", [])),
                    "excluded_function": list(question.get("excluded_function", [])),
                    "official_category": CATEGORY,
                    "reference_calls_have_results": True,
                    "results_source": "official gold plan executed on the pinned backend",
                },
            )
        )

    audit = {
        "execution_seconds": time.perf_counter() - started,
        "executed_calls": sum(calls_by_tool.values()),
        "error_results": sum(errors.values()),
        "error_results_by_tool": dict(sorted(errors.items())),
        "observed_output_parse": dict(sorted(parse_kinds.items())),
        "state_mutation_audit": {
            "mutating_calls": sum(mutating.values()),
            "rng_advancing_calls": sum(rng_advancing.values()),
            "tools_observed_mutating": len(mutating),
            "by_tool": {
                name: {
                    "calls": calls_by_tool[name],
                    "mutating_calls": mutating[name],
                    "rng_advancing_calls": rng_advancing[name],
                    "mutated_fields": sorted(mutated_fields[name]),
                    "declared_effect": catalog.get(name).effect.value,
                    "declared_compilable": catalog.get(name).compilable,
                }
                for name in sorted(calls_by_tool)
            },
        },
    }
    return tuple(tasks), audit


def _assert_effect_audits(
    catalog: EffectCatalog, audit: Mapping[str, Any]
) -> dict[str, Any]:
    """Fail closed if the signed catalog is looser than the observed behaviour."""

    read_like_mutations: list[str] = []
    compilable_rng: list[str] = []
    for name, row in audit["state_mutation_audit"]["by_tool"].items():
        spec = catalog.get(name)
        if row["mutating_calls"] and spec.effect.is_read_like:
            read_like_mutations.append(name)
        if row["rng_advancing_calls"] and spec.compilable:
            compilable_rng.append(name)
    if read_like_mutations:
        raise RuntimeError(
            "tools declared read-like were observed mutating state: "
            + ", ".join(sorted(read_like_mutations))
        )
    if compilable_rng:
        raise RuntimeError(
            "tools declared compilable were observed advancing the scenario RNG: "
            + ", ".join(sorted(compilable_rng))
        )
    return {
        "read_like_declarations_observed_mutating": len(read_like_mutations),
        "compilable_declarations_observed_advancing_rng": len(compilable_rng),
    }


def _assert_pure_matches_upstream(catalog: EffectCatalog, backend: Backend) -> int:
    """PURE is only licensed for classes upstream itself lists as stateless."""

    offenders = [
        name
        for name, spec in catalog.tools.items()
        if spec.effect.value == "PURE"
        and name.split(".", 1)[0] not in backend.stateless_classes
    ]
    if offenders:
        raise RuntimeError(
            "PURE declared for a stateful upstream class: " + ", ".join(sorted(offenders))
        )
    return sum(
        1
        for name, spec in catalog.tools.items()
        if spec.effect.value == "PURE" and name.split(".", 1)[0] in backend.stateless_classes
    )


def _replay_matches(
    backend: Backend,
    questions: Sequence[Mapping[str, Any]],
    answers: Mapping[str, list[list[str]]],
    tasks: Sequence[ReferenceTask],
) -> dict[str, Any]:
    """Re-execute every plan in a fresh namespace, whole turn at a time.

    Pass one executes call by call; this pass executes each turn as one list.  Byte
    equality therefore checks two things at once: the backend is deterministic given the
    same entry snapshot, and the per-call invocation shape is equivalent to the per-turn
    shape the official checker uses.
    """

    by_task = {task.task_id: task for task in tasks}
    compared = mismatched = 0
    mismatched_tools: Counter[str] = Counter()
    started = time.perf_counter()
    for question in questions:
        task_id = str(question["id"])
        expected = [action for action in by_task[task_id].actions]
        index = 0
        for turn_calls in answers[task_id]:
            observed = backend.run(turn_calls, question, namespace="gac_replay")
            for call, result in zip(turn_calls, observed):
                action = expected[index]
                index += 1
                compared += 1
                value, parse_kind = _parse_observed(result)
                if (
                    _plain(action.output) != _plain(value)
                    or action.metadata["observed_output_parse"] != parse_kind
                ):
                    mismatched += 1
                    mismatched_tools[action.name] += 1
    return {
        "compared_calls": compared,
        "mismatched_calls": mismatched,
        "mismatched_by_tool": dict(sorted(mismatched_tools.items())),
        "exact_replay_rate": (compared - mismatched) / compared if compared else None,
        "replay_seconds": time.perf_counter() - started,
        "checks": [
            "second independent execution pass reproduces every observed result",
            "per-call and per-turn invocation shapes agree",
        ],
    }


def _entry_state(
    task: ReferenceTask, question: Mapping[str, Any]
) -> tuple[dict[str, Any], int]:
    """Entry snapshot: the task's own initial_config plus first-appearance literals.

    ``environment`` is the benchmark's real entry state.  ``inputs`` follows the
    API-Bank convention: a gold-plan literal counts as user-supplied input the first time
    it appears, and is excluded once an earlier observed result has produced that value.
    """

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
        for _path, value in flatten(_plain(action.output)):
            if not isinstance(value, (dict, list)):
                prior_values.add(json.dumps(value, sort_keys=True, default=str))
    entry = {
        "inputs": inputs,
        "environment": _plain(question.get("initial_config") or {}),
    }
    return entry, reused_slots


def _manifest(catalog: EffectCatalog, tools: Sequence[str]) -> ExecutionManifest:
    return ExecutionManifest(
        manifest_id="bfcl-v4-multi-turn-base-gold-plan-executed",
        commit=REVISION,
        model="gold-reference-plan-no-model-inference",
        prompt_hash="withheld-public-benchmark-user-turns",
        tools_hash=hashlib.sha256("|".join(sorted(tools)).encode()).hexdigest()[:16],
        policy_hash="public-benchmark-executed-gold-plan",
        guardrail_hash="none-recorded-replay-only",
        effect_catalog_version=catalog.catalog_version,
        entry_contract_version="initial-config-plus-first-appearance-literals-v1",
        sdk_version="not-applicable",
        tracer_version="paper-bfcl-execution-adapter-v1",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="smoke-test switch: evaluate only the first N tasks (never used for the sealed run)",
    )
    args = parser.parse_args()

    checkout = args.source_root / "gorilla" / "berkeley-function-call-leaderboard"
    backend = Backend(checkout)
    data = checkout / "bfcl_eval" / "data"
    questions = _read_jsonl(data / f"BFCL_v4_{CATEGORY}.json")
    answers = {
        str(row["id"]): row["ground_truth"]
        for row in _read_jsonl(data / "possible_answer" / f"BFCL_v4_{CATEGORY}.json")
    }
    if args.limit is not None:
        questions = questions[: args.limit]
    missing = [str(row["id"]) for row in questions if str(row["id"]) not in answers]
    if missing:
        raise SystemExit(f"{len(missing)} pinned tasks have no gold plan")

    catalog = EffectCatalog.from_yaml(CATALOG_PATH)
    backend.bind_classes(
        name for question in questions for name in question.get("involved_classes", [])
    )
    pure_declarations = _assert_pure_matches_upstream(catalog, backend)

    tasks, audit = _build_corpus(backend, questions, answers, catalog)
    tool_names = sorted({action.name for task in tasks for action in task.actions})
    coverage = catalog.validate_coverage(tool_names)
    if coverage["undeclared"]:
        raise RuntimeError(f"effect catalog is incomplete: {coverage['undeclared']}")
    if audit["error_results"]:
        raise RuntimeError(
            f"{audit['error_results']} gold calls returned an execution error; "
            "the corpus is not a clean observed trace set"
        )
    catalog_audits = _assert_effect_audits(catalog, audit)
    catalog_audits["pure_declarations"] = pure_declarations
    replay = _replay_matches(backend, questions, answers, tasks)
    if replay["mismatched_calls"]:
        raise RuntimeError(
            f"{replay['mismatched_calls']} calls did not reproduce exactly; "
            "the replay oracle precondition failed"
        )

    manifest = _manifest(catalog, tool_names)
    by_task = {str(question["id"]): question for question in questions}
    episodes: list[Episode] = []
    reused_slots = 0
    for task in tasks:
        entry_state, reused = _entry_state(task, by_task[task.task_id])
        reused_slots += reused
        episodes.append(
            reference_task_to_episode(
                task,
                manifest=manifest,
                outcome=OutcomeLabels(task_success=True, semantic_score=1.0),
                entry_state=entry_state,
            )
        )

    compiler = evaluate_compiler(
        episodes,
        catalog,
        manifest,
        entry_schema=("inputs", "environment"),
    )
    observed_outcome = compiler["exact_gate"]["outcome"]
    lengths = [len(task.actions) for task in tasks]
    effect_mix = Counter(catalog.get(name).effect.value for name in tool_names)
    report = {
        "schema": "agent-compaction-external-execution/v1",
        "benchmark": "BFCL v4 multi_turn_base gold plans executed on the pinned backend",
        "source_revision": REVISION,
        "source_license": "Apache-2.0",
        "source_license_sha256": _sha256(checkout.parent / "LICENSE"),
        "effect_catalog": catalog.catalog_version,
        "effect_catalog_sha256": _sha256(CATALOG_PATH),
        "protocol": str(PROTOCOL_PATH.relative_to(ROOT)),
        "dataset": {
            "tasks": len(tasks),
            "observed_calls": sum(lengths),
            "unique_tools": len(tool_names),
            "involved_classes": sorted(
                {
                    name
                    for task in tasks
                    for name in task.metadata["involved_classes"]
                }
            ),
            "turns": sum(len(answers[task.task_id]) for task in tasks),
            "calls_per_task_min": min(lengths),
            "calls_per_task_median": statistics.median(lengths),
            "calls_per_task_max": max(lengths),
            "observed_cross_call_value_reuse_slots": reused_slots,
            "complete_observed_traces": sum(
                all(action.output_observed for action in task.actions) for task in tasks
            ),
            "independent_groups": len({task.group_id for task in tasks}),
            "declared_effect_mix": dict(sorted(effect_mix.items())),
            "compilable_tools": sum(catalog.get(name).compilable for name in tool_names),
        },
        "catalog_coverage": coverage,
        "execution_audit": audit,
        "catalog_audits": catalog_audits,
        "replay_oracle": replay,
        "compiler": compiler,
        "preregistration": {
            "protocol": str(PROTOCOL_PATH.relative_to(ROOT)),
            "predeclared_gate_outcome": PREDECLARED_GATE_OUTCOME,
            "observed_gate_outcome": observed_outcome,
            "prediction_held": observed_outcome == PREDECLARED_GATE_OUTCOME,
            "required_zero_violation_groups": required_zero_violation_groups(),
            "maximum_available_independent_groups": len(tasks),
            "note": (
                "A retirement here is the predeclared outcome, not a failed measurement: "
                "200 single-episode tasks over eight scenario classes cannot supply the "
                "exact zero-violation group count the promotion gate requires."
            ),
        },
        "evidence": {
            "class": "public executable simulator with gold plans executed for observed results",
            "compiler_execution": True,
            "provider_calls": 0,
            "prompts_arguments_outputs_serialized": False,
            "is_real_world_demo": False,
            "is_live_provider_evaluation": False,
            "licenses_end_to_end_planning_quality_claim": False,
            "licenses_function_calling_accuracy_claim": False,
            "licenses_production_safety_claim": False,
            "measures": [
                "gold-plan execution on the pinned stateful backend",
                "signed effect-catalog audit against observed state mutation",
                "exact re-execution replay oracle",
                "provenance and candidate mining",
                "synthesis and held-out recorded replay where support permits",
            ],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "output": _display(args.output),
                "dataset": report["dataset"],
                "replay_oracle": {
                    key: replay[key]
                    for key in ("compared_calls", "mismatched_calls", "exact_replay_rate")
                },
                "compiler": {
                    key: compiler[key]
                    for key in (
                        "candidate_windows",
                        "candidate_families",
                        "families_support_ge_3",
                        "maximum_family_support",
                        "held_out_recorded_replay",
                        "exact_gate",
                    )
                },
                "preregistration": report["preregistration"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
