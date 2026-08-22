#!/usr/bin/env python3
"""Provider-free AppWorld compiler evaluation over executed gold solutions.

AppWorld ships 750 tasks over nine simulated apps and 457 typed APIs with a resettable
per-task application database.  Its public ``minimal`` data mode carries gold solution
programs for the ``train`` and ``dev`` splits.  The shipped ``ground_truth/api_calls.json``
records method, url, and request data but no responses, so ``reference_task_to_episode``
fails closed on the artifact as distributed.  Executing the official solution against the
pinned backend supplies the missing field, exactly as the BFCL substrate does for its gold
plans.

This script therefore (1) executes every gold solution twice in a dedicated AppWorld
interpreter and retains each call's observed result and a per-call database-mutation audit,
(2) runs three mechanical safety audits against the signed effect catalog, (3) checks that
the second pass reproduces every result byte for byte, and (4) runs the same
provenance/window/synthesis/held-out-replay pipeline used for API-Bank and BFCL, in two
pre-registered arms over the one contestable effect declaration.

The predeclared expectation, decision rule, and claim boundary are in
``paper/supplementary/appworld-compiler-protocol.md``; this script records whether the
observed gate outcome matched the prediction it was written against.  No provider call is
made.  Instructions, arguments, observed results, credentials, and application state are
never serialized: the report retains counts, hashes, structural field names, and per-family
aggregates only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence


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
from guarded_agentic_compaction.evaluation.splits import Splits  # noqa: E402
from guarded_agentic_compaction.grc.compile import GrcConfig, compile_grc  # noqa: E402
from guarded_agentic_compaction.schema.effects import (  # noqa: E402
    Capability,
    EffectCatalog,
    EffectClass,
)
from guarded_agentic_compaction.schema.traces import (  # noqa: E402
    Episode,
    ExecutionManifest,
    OutcomeLabels,
    flatten,
)


PACKAGE_VERSION = "0.1.3.post1"
CATALOG_PATH = ROOT / "benchmarks" / "contracts" / "effects" / "appworld.yaml"
PROTOCOL_PATH = ROOT / "paper" / "supplementary" / "appworld-compiler-protocol.md"
DEFAULT_OUT = (
    ROOT / "paper" / "results" / "external_benchmarks" / "appworld_compiler_execution.json"
)
SPLITS = ("train", "dev")

# Predeclared in the protocol before the compiler was run on this corpus.
PREDECLARED_GATE_OUTCOME = "candidate_present"

# The five entries Arm B flips, and nothing else in the catalog moves.
LOGIN_TOOLS = (
    "file_system.login",
    "phone.login",
    "simple_note.login",
    "spotify.login",
    "venmo.login",
)

# Executed inside the dedicated AppWorld interpreter.  Kept here rather than in a separate
# file so the collection contract and the audit that consumes it cannot drift apart.
COLLECTOR = r'''
import json, sys
from pathlib import Path
from sqlalchemy import event
from sqlalchemy.engine import Engine
from appworld import AppWorld
from appworld.requester import Requester

MUTATING = ("INSERT", "UPDATE", "DELETE", "DROP", "CREATE")
_pending = []


@event.listens_for(Engine, "after_cursor_execute")
def _listen(conn, cursor, statement, parameters, context, executemany):
    head = statement.strip()[:10].upper()
    for op in MUTATING:
        if head.startswith(op):
            _pending.append(op)
            return


_original = Requester.request
_sink = []


def _patched(self, _app_name, _api_name, client=None, raise_on_failure=None,
             show=False, track=True, **kwargs):
    del _pending[:]
    result = _original(self, _app_name=_app_name, _api_name=_api_name, client=client,
                       raise_on_failure=raise_on_failure, show=show, track=track, **kwargs)
    if track:
        _sink.append({
            "tool": "%s.%s" % (_app_name, _api_name),
            "args": json.loads(json.dumps(kwargs, default=str)),
            "result": json.loads(json.dumps(result, default=str)),
            "mutations": sorted(set(_pending)),
        })
    del _pending[:]
    return result


Requester.request = _patched


def run_once(task_id, tag):
    del _sink[:]
    with AppWorld(task_id=task_id, experiment_name="gac_appworld_" + tag,
                  remote_environment_url=None, ground_truth_mode="full",
                  load_ground_truth=True) as world:
        code = world.task.ground_truth.compiled_solution_code
        output = world.execute(code + "\nsolution(apis, requester)")
    return list(_sink), output


out_dir = Path(sys.argv[1])
out_dir.mkdir(parents=True, exist_ok=True)
splits = sys.argv[2].split(",")
limit = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] != "none" else None

pairs = []
for split in splits:
    for task_id in Path("data/datasets/%s.txt" % split).read_text().split():
        pairs.append((split, task_id))
if limit:
    pairs = pairs[:limit]

for index, (split, task_id) in enumerate(pairs, 1):
    target = out_dir / (task_id + ".json")
    if target.is_file():
        continue
    try:
        calls, output = run_once(task_id, "p1")
        replay, _ = run_once(task_id, "p2")
    except Exception as exc:
        target.write_text(json.dumps({
            "task_id": task_id, "split": split,
            "scenario_id": task_id.rsplit("_", 1)[0],
            "error": "%s: %s" % (type(exc).__name__, exc)}))
        continue
    specs = json.loads(Path("data/tasks/%s/specs.json" % task_id).read_text())
    target.write_text(json.dumps({
        "task_id": task_id, "split": split,
        "scenario_id": task_id.rsplit("_", 1)[0],
        "execution_failed": "Execution failed" in output,
        "specs": {key: specs[key] for key in ("supervisor", "datetime") if key in specs},
        "calls": calls,
        "replay": [{"tool": c["tool"], "args": c["args"], "result": c["result"]}
                   for c in replay],
    }))
print(json.dumps({"tasks_requested": len(pairs)}))
'''


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


def _distribution(values: Sequence[int]) -> dict[str, Any]:
    """Reported so the efficiency claim boundary can be checked, not asserted."""

    if not values:
        return {}
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "min": ordered[0],
        "median": ordered[len(ordered) // 2],
        "max": ordered[-1],
        "total": sum(ordered),
    }


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


# ---------------------------------------------------------------------------
# substrate acquisition
# ---------------------------------------------------------------------------


def collect(
    checkout: Path, interpreter: Path, cache: Path, limit: int | None
) -> list[dict[str, Any]]:
    """Execute every gold solution twice in the dedicated AppWorld interpreter."""

    if not checkout.is_dir():
        raise SystemExit(f"pinned AppWorld checkout is unavailable at {checkout}")
    if not (checkout / "data" / "datasets").is_dir():
        raise SystemExit(
            f"AppWorld data is not installed under {checkout}; "
            "run `appworld install` and `appworld download data` there first"
        )
    if not interpreter.is_file():
        raise SystemExit(f"AppWorld interpreter is unavailable at {interpreter}")
    cache.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [str(interpreter), "-c", COLLECTOR, str(cache), ",".join(SPLITS),
         str(limit) if limit else "none"],
        cwd=checkout,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "PYTHONWARNINGS": "ignore"},
    )
    if result.returncode:
        tail = (result.stderr or "").strip().splitlines()[-3:]
        raise SystemExit("AppWorld collection failed: " + " | ".join(tail))
    records = [json.loads(path.read_text()) for path in sorted(cache.glob("*.json"))]
    if not records:
        raise SystemExit("AppWorld collection produced no records")
    return records


# ---------------------------------------------------------------------------
# fail-closed preconditions
# ---------------------------------------------------------------------------


def _assert_catalog_completeness(
    catalog: EffectCatalog, records: Sequence[Mapping[str, Any]]
) -> int:
    """Every API a gold solution calls must carry a declaration (precondition 1)."""

    observed = {call["tool"] for record in records for call in record.get("calls", ())}
    undeclared = sorted(name for name in observed if name not in catalog.tools)
    if undeclared:
        raise RuntimeError(
            "gold solutions call APIs with no signed declaration: " + ", ".join(undeclared)
        )
    return len(observed)


def _assert_no_pure(catalog: EffectCatalog) -> None:
    """No AppWorld API is a function of its arguments alone (precondition 4)."""

    offenders = sorted(
        name for name, spec in catalog.tools.items() if spec.effect is EffectClass.PURE
    )
    if offenders:
        raise RuntimeError("PURE is not licensed on this substrate: " + ", ".join(offenders))


def _audit_effects(
    catalog: EffectCatalog, records: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Read-like declarations may never be observed mutating the database (precondition 3)."""

    per_tool: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        for call in record.get("calls", ()):
            counter = per_tool[call["tool"]]
            counter["calls"] += 1
            if call["mutations"]:
                counter["mutating"] += 1
                counter.update(Counter(call["mutations"]))
    violations = sorted(
        name
        for name, counter in per_tool.items()
        if counter["mutating"] and catalog.get(name).effect.is_read_like
    )
    if violations:
        raise RuntimeError(
            "APIs declared read-like were observed mutating the database: "
            + ", ".join(violations)
        )
    mutating = {name for name, counter in per_tool.items() if counter["mutating"]}
    partial = sorted(
        name
        for name, counter in per_tool.items()
        if 0 < counter["mutating"] < counter["calls"]
    )
    stricter_than_observed = sorted(
        name
        for name in per_tool
        if name not in mutating and not catalog.get(name).effect.is_read_like
    )
    return {
        "tools_observed": len(per_tool),
        "observed_calls": sum(counter["calls"] for counter in per_tool.values()),
        "mutating_calls": sum(counter["mutating"] for counter in per_tool.values()),
        "tools_ever_mutating": len(mutating),
        "tools_never_mutating": len(per_tool) - len(mutating),
        "tools_mutating_on_some_but_not_all_calls": partial,
        "read_like_declarations_observed_mutating": 0,
        "declared_stricter_than_observed": stricter_than_observed,
        "checks": [
            "every observed API carries a signed declaration",
            "no read-like declaration was observed mutating the application database",
            "PURE is not licensed on this substrate",
        ],
    }


def _replay_matches(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """A second independent execution must reproduce every result byte for byte."""

    compared = mismatched = 0
    shape_mismatches: list[str] = []
    mismatched_tools: Counter[str] = Counter()
    for record in records:
        first, second = record.get("calls", ()), record.get("replay", ())
        if len(first) != len(second):
            shape_mismatches.append(record["task_id"])
            continue
        for one, two in zip(first, second):
            compared += 1
            if one["args"] != two["args"] or one["result"] != two["result"]:
                mismatched += 1
                mismatched_tools[one["tool"]] += 1
    if shape_mismatches or mismatched:
        raise RuntimeError(
            "re-execution did not reproduce the observed corpus: "
            f"{mismatched} differing calls, "
            f"{len(shape_mismatches)} tasks with a differing call count"
        )
    return {
        "compared_calls": compared,
        "mismatched_calls": mismatched,
        "mismatched_by_tool": dict(sorted(mismatched_tools.items())),
        "exact_replay_rate": (compared - mismatched) / compared if compared else None,
        "checks": [
            "second independent execution reproduces every observed result",
            "minted access tokens are byte-identical under re-execution",
        ],
    }


# ---------------------------------------------------------------------------
# normalization
# ---------------------------------------------------------------------------


def _entry_state(record: Mapping[str, Any]) -> tuple[dict[str, Any], int]:
    """Entry snapshot: the task's own specs plus first-appearance literals.

    ``environment`` is the benchmark's real entry state -- the supervisor profile the task
    is issued to, and the frozen clock.  ``inputs`` follows the API-Bank and BFCL
    convention: a gold literal counts as user-supplied input the first time it appears, and
    is excluded once an earlier observed result has produced that value.
    """

    prior_values: set[str] = set()
    inputs: dict[str, Any] = {}
    reused_slots = 0
    for index, call in enumerate(record["calls"]):
        retained: dict[str, Any] = {}
        for path, value in flatten(_plain(call["args"])):
            if isinstance(value, (dict, list)):
                continue
            key = json.dumps(value, sort_keys=True, default=str)
            if key in prior_values:
                reused_slots += 1
            else:
                retained[path] = value
        if retained:
            inputs[f"s{index}"] = retained
        for _path, value in flatten(_plain(call["result"])):
            if not isinstance(value, (dict, list)):
                prior_values.add(json.dumps(value, sort_keys=True, default=str))
    entry = {"inputs": inputs, "environment": _plain(record.get("specs") or {})}
    return entry, reused_slots


def _reference_task(record: Mapping[str, Any], catalog: EffectCatalog) -> ReferenceTask:
    actions = tuple(
        ReferenceAction(
            name=call["tool"],
            arguments=_plain(call["args"]),
            output=_plain(call["result"]),
            output_observed=True,
            effect=catalog.get(call["tool"]).effect,
            requestor="gold-solution",
            turn=index,
        )
        for index, call in enumerate(record["calls"])
    )
    return ReferenceTask(
        benchmark="appworld",
        task_id=record["task_id"],
        group_id=record["task_id"],
        source_revision=PACKAGE_VERSION,
        substrate=EvidenceSubstrate.PUBLIC_SIMULATION,
        actions=actions,
        prompt="",
        metadata={"split": record["split"], "scenario_id": record["scenario_id"]},
    )


def _manifest(catalog: EffectCatalog, tools: Sequence[str], arm: str) -> ExecutionManifest:
    return ExecutionManifest(
        manifest_id=f"appworld-train-dev-gold-solution-executed-{arm}",
        commit=PACKAGE_VERSION,
        model="gold-reference-solution-no-model-inference",
        prompt_hash="withheld-public-benchmark-instructions",
        tools_hash=hashlib.sha256("|".join(sorted(tools)).encode()).hexdigest()[:16],
        policy_hash="public-benchmark-executed-gold-solution",
        guardrail_hash="none-recorded-replay-only",
        effect_catalog_version=catalog.catalog_version,
        entry_contract_version="entry-snapshot-plus-first-appearance-literals-v1",
        sdk_version="not-applicable",
        tracer_version="paper-appworld-execution-adapter-v1",
    )


def _episodes(
    records: Sequence[Mapping[str, Any]], catalog: EffectCatalog, manifest: ExecutionManifest
) -> tuple[list[Episode], int]:
    episodes: list[Episode] = []
    reused = 0
    for record in records:
        task = _reference_task(record, catalog)
        entry, reused_slots = _entry_state(record)
        reused += reused_slots
        episodes.append(
            reference_task_to_episode(
                task,
                manifest=manifest,
                outcome=OutcomeLabels(task_success=True, semantic_score=1.0),
                entry_state=entry,
            )
        )
    return episodes, reused


def _arm_catalog(arm: str) -> EffectCatalog:
    """Arm A is the file as signed.  Arm B flips exactly the five login entries."""

    catalog = EffectCatalog.from_yaml(CATALOG_PATH)
    if arm == "A":
        return catalog
    tools = dict(catalog.tools)
    for name in LOGIN_TOOLS:
        if name not in tools:
            raise RuntimeError(f"sensitivity arm expects {name} in the signed catalog")
        tools[name] = tools[name].model_copy(
            update={
                "effect": EffectClass.READ_EXTERNAL,
                "capabilities": (
                    Capability.SPECULATABLE,
                    Capability.REPLAYABLE,
                    Capability.CACHEABLE,
                ),
            }
        )
    return EffectCatalog.from_dict(
        {"version": catalog.version, "name": catalog.name + "-login-as-read",
         "tools": {name: spec.model_dump(mode="json") for name, spec in tools.items()}}
    )


def _run_arm(arm: str, records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    catalog = _arm_catalog(arm)
    tools = sorted({call["tool"] for record in records for call in record["calls"]})
    manifest = _manifest(catalog, tools, arm)
    episodes, reused = _episodes(records, catalog, manifest)
    report = evaluate_compiler(
        episodes,
        catalog,
        manifest,
        entry_schema=("inputs", "environment"),
    )
    report["arm"] = arm
    report["login_declared"] = catalog.get("spotify.login").effect.value
    report["tools_compilable"] = sum(
        1 for name in tools if catalog.get(name).compilable
    )
    report["tools_effect_blocked"] = len(tools) - report["tools_compilable"]
    report["reused_argument_slots_excluded_from_entry_inputs"] = reused
    return report


# ---------------------------------------------------------------------------
# admission
# ---------------------------------------------------------------------------

SPLIT_SEED = 20260821
CALIBRATION_GROUPS = 92  # the exact zero-violation requirement at alpha=.05 over 11 points


def _split(episodes: Sequence[Episode]) -> tuple[Splits, dict[str, int]]:
    """Deterministic seeded split reserving exactly the required calibration count.

    The calibration share is fixed at the 92 groups the exact bound needs rather than at a
    fraction, because a larger calibration set would make the bound easier and a smaller
    one would make it unreachable.  92 of 136 is the tightest allocation under which the
    gate can clear at all, so the remaining 44 groups are what train, development, and
    held-out test have to share.
    """

    import random

    groups = sorted(episode.envelope.group_id for episode in episodes)
    random.Random(SPLIT_SEED).shuffle(groups)
    calibration = groups[:CALIBRATION_GROUPS]
    rest = groups[CALIBRATION_GROUPS:]
    train = rest[: max(1, len(rest) // 2)]
    dev = rest[len(train) : len(train) + max(1, len(rest) // 4)]
    test = rest[len(train) + len(dev) :]
    sizes = {"train": len(train), "dev": len(dev),
             "calibration": len(calibration), "test": len(test)}
    return (
        Splits(
            train=frozenset(train),
            dev=frozenset(dev),
            calibration=frozenset(calibration),
            test=frozenset(test),
            seed=SPLIT_SEED,
        ),
        sizes,
    )


def _admission(arm: str, records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Run the deployable compile pipeline, including the real calibration gate."""

    catalog = _arm_catalog(arm)
    tools = sorted({call["tool"] for record in records for call in record["calls"]})
    manifest = _manifest(catalog, tools, arm)
    episodes, _ = _episodes(records, catalog, manifest)
    splits, sizes = _split(episodes)
    config = GrcConfig(
        entry_schema=("inputs", "environment"),
        partition_by=(),
        w_min=2,
        w_max=12,
        b_min=2,
        s_min=5,
        min_principals=1,
        min_days=1,
        max_transform_depth=2,
        kappa=3,
        alpha=0.05,
        delta=0.10,
        phi_min=0.02,
        max_candidates=24,
        max_artifacts=8,
        max_calibration_windows=CALIBRATION_GROUPS,
        mode="replay",
        owner=f"paper-appworld-substrate-arm-{arm}",
        seed=SPLIT_SEED,
        synthesize_composites=False,
    )
    result = compile_grc(
        episodes, catalog, splits, manifest, config, sandbox=None, perturbations=()
    )
    admitted = [artifact for artifact in result.artifacts if not artifact.gate.retire]
    rows = []
    for artifact in result.artifacts:
        gate = artifact.gate
        rows.append({
            "artifact_id": artifact.artifact_id,
            "program_steps": len(artifact.program.steps),
            "program_tools": [step.tool for step in artifact.program.steps],
            "support_groups": artifact.evidence.support_groups,
            "support_principals": artifact.evidence.support_principals,
            "removed_requests": artifact.evidence.removed_requests,
            "retire": gate.retire,
            "threshold": gate.threshold,
            "calibration_groups": gate.n_calibration_groups,
            "accepted_groups": gate.n_accepted,
            "observed_violations": gate.observed_violations,
            "risk_upper_bound": gate.risk_upper_bound,
            "coverage": gate.coverage,
            "admissible_thresholds": list(gate.admissible),
            "replay": artifact.evidence.replay,
            "notes": gate.notes,
        })
    candidates = []
    for record in result.candidates:
        row = {
            "candidate_id": record.candidate_id,
            "tools": list(record.tools),
            "support_groups": record.support_groups,
            "removed_requests": record.removed_requests,
            "stage": record.stage,
            "rejected": record.rejected,
        }
        if record.gate is not None:
            row["gate"] = {
                "retire": record.gate.retire,
                "threshold": record.gate.threshold,
                "calibration_groups": record.gate.n_calibration_groups,
                "accepted_groups": record.gate.n_accepted,
                "observed_violations": record.gate.observed_violations,
                "risk_upper_bound": record.gate.risk_upper_bound,
                "coverage": record.gate.coverage,
            }
        candidates.append(row)
    return {
        "arm": arm,
        "split_sizes": sizes,
        "split_seed": SPLIT_SEED,
        "candidates": len(result.candidates),
        "candidate_records": candidates,
        "artifacts_emitted": len(result.artifacts),
        "artifacts_admitted": len(admitted),
        "rejection_by_stage": dict(sorted(result.rejection_by_stage.items())),
        "gates": rows,
        "outcome": "ADMITTED" if admitted else "RETIRE",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--appworld-python", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="smoke-test switch: collect only the first N tasks (never used for a sealed run)",
    )
    args = parser.parse_args()

    started = time.perf_counter()
    checkout = args.source_root / "appworld"
    cache = args.cache or (args.source_root / "appworld-gac-corpus")
    records = collect(checkout, args.appworld_python, cache, args.limit)

    excluded = [
        {"task_id": record["task_id"], "split": record["split"],
         "reason": record.get("error", "gold solution raised during execution")}
        for record in records
        if "error" in record or record.get("execution_failed")
    ]
    clean = [record for record in records if record not in excluded and "calls" in record
             and not record.get("error") and not record.get("execution_failed")]

    catalog = EffectCatalog.from_yaml(CATALOG_PATH)
    _assert_no_pure(catalog)
    tools_observed = _assert_catalog_completeness(catalog, clean)
    effect_audit = _audit_effects(catalog, clean)
    replay = _replay_matches(clean)

    required = required_zero_violation_groups()
    if len(clean) < required:
        raise SystemExit(
            f"only {len(clean)} tasks executed cleanly, below the {required} the "
            "protocol requires before this substrate is worth running"
        )

    arms = {arm: _run_arm(arm, clean) for arm in ("A", "B")}
    outcomes = {arm: report["exact_gate"]["outcome"] for arm, report in arms.items()}
    admission = {arm: _admission(arm, clean) for arm in ("A", "B")}

    payload = {
        "schema": "gac-appworld-compiler-execution/v1",
        "benchmark": "appworld",
        "package_version": PACKAGE_VERSION,
        "substrate": EvidenceSubstrate.PUBLIC_SIMULATION.value,
        "splits": list(SPLITS),
        "protocol": {
            "path": _display(PROTOCOL_PATH),
            "sha256": _sha256(PROTOCOL_PATH),
            "predeclared_gate_outcome": PREDECLARED_GATE_OUTCOME,
            "observed_gate_outcome": outcomes,
            "prediction_held": all(
                outcome == PREDECLARED_GATE_OUTCOME for outcome in outcomes.values()
            ),
        },
        "effect_catalog": {
            "path": _display(CATALOG_PATH),
            "sha256": _sha256(CATALOG_PATH),
            "declared_tools": len(catalog.tools),
            "tools_observed": tools_observed,
        },
        "corpus": {
            "tasks_collected": len(records),
            "tasks_clean": len(clean),
            "scenarios_clean": len({record["scenario_id"] for record in clean}),
            "distinct_supervisors": len({
                json.dumps((record.get("specs") or {}).get("supervisor"), sort_keys=True)
                for record in clean
            }),
            "tasks_excluded": excluded,
            "observed_calls": effect_audit["observed_calls"],
            "calls_per_task": _distribution(
                [len(record["calls"]) for record in clean]
            ),
            "note": (
                "an excluded task is an upstream gold-solution/data compatibility outcome, "
                "reported rather than dropped; it is not a compiler error"
            ),
        },
        "effect_audit": effect_audit,
        "exact_replay": replay,
        "arms": arms,
        "admission": admission,
        "claim_boundary": [
            "no model runs; the gold solution is supplied, not predicted",
            "no function-calling accuracy, planning, quality, or efficiency claim",
            "groups are tasks, not scenarios; task-level independence is assumed, not established",
            "not a leaderboard submission; only the public train and dev splits are touched",
            "never pooled with the real-record GitHub workflow families or any other substrate",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    print(f"wrote {_display(args.output)}")
    print(f"  tasks {len(clean)} clean / {len(records)} collected"
          f" ({len(excluded)} upstream exclusions)")
    print(f"  observed calls {effect_audit['observed_calls']}"
          f" over {tools_observed} declared APIs")
    print(f"  exact replay {replay['compared_calls'] - replay['mismatched_calls']}"
          f"/{replay['compared_calls']}")
    for arm, report in arms.items():
        gate = report["exact_gate"]
        held = report["held_out_recorded_replay"]
        print(f"  arm {arm} (login={report['login_declared']}):"
              f" families {report['candidate_families']}"
              f", support>=3 {report['families_support_ge_3']}"
              f", n_max {gate['max_observed_family_support']}/{gate['minimum_zero_violation_groups']}"
              f", synthesized {held.get('families_synthesized', 0)}"
              f", held-out {held.get('test_passed', 0)}/{held.get('test_abstained', 0)}"
              f"/{held.get('test_wrong', 0)} (pass/abstain/wrong)"
              f" -> {gate['outcome']}")
    print(f"  predeclared {PREDECLARED_GATE_OUTCOME}; prediction_held="
          f"{payload['protocol']['prediction_held']}")
    for arm, report in admission.items():
        print(f"  admission arm {arm}: candidates {report['candidates']}"
              f", emitted {report['artifacts_emitted']}"
              f", admitted {report['artifacts_admitted']} -> {report['outcome']}")
        for row in report["gates"]:
            print(f"      {'RETIRE' if row['retire'] else 'ADMIT '}"
                  f" steps={row['program_steps']}"
                  f" support={row['support_groups']}"
                  f" cal={row['accepted_groups']}/{row['calibration_groups']}"
                  f" viol={row['observed_violations']}"
                  f" eta={row['threshold']:.2f}"
                  f" U={row['risk_upper_bound']:.4f}"
                  f" tools={row['program_tools']}")


if __name__ == "__main__":
    main()
