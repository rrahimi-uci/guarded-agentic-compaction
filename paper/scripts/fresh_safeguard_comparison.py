"""Frozen-artifact, fresh-record comparison; preflight is entirely provider-free.

See experiments/fresh_safeguards/README.md. No paper result is overwritten.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import math
import os
import re
import sys
import time
from collections import Counter
from dataclasses import asdict
from importlib.metadata import version
from itertools import permutations
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "paper/scripts"))

ARMS = ("baseline", "gac", "support_only", "recurrence_only")
MODEL = "gpt-5.6-luna"
TASK = "natural-extractive-v2"
SEED = 20261015
RESERVE_USD = 1.0
DEFAULT_OUT = ROOT / "experiments/fresh_safeguards/artifacts"
PROTOCOL = ROOT / "experiments/fresh_safeguards/README.md"
REGISTRY = ROOT / "paper/results/github_natural_replication/registry/registry.json"
METRICS = ("requests", "total_tokens", "wall_latency_ms", "estimated_cost_usd", "tool_calls")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def object_digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    """Replace one checkpoint atomically; a pending call is written before execution."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def used_ids(value: Any, *, selection: bool = False) -> set[int]:
    """Conservatively collect named record IDs and integer selection arrays.

    Numeric namespaces from other GitHub repositories may over-exclude. This is
    intentional; dataset tables themselves are never scanned as prior studies.
    """
    found: set[int] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"issue_number", "record_number"} and type(item) is int:
                found.add(item)
            if isinstance(item, str):
                found.update(int(n) for n in re.findall(r"(?:github[-\w]*issue:|issue:)(\d+)", item))
            nested_selection = selection or key in {"selection", "selected", "cohort", "splits"} or key.endswith(("_numbers", "_ids"))
            found.update(used_ids(item, selection=nested_selection))
    elif isinstance(value, list):
        for item in value:
            if selection and type(item) is int:
                found.add(item)
            else:
                found.update(used_ids(item, selection=selection))
    return found


def exclusion_audit(results_root: Path) -> tuple[set[int], dict[str, str]]:
    excluded: set[int] = set()
    sources: dict[str, str] = {}
    for path in sorted(results_root.rglob("*.json")):
        relative = path.relative_to(results_root)
        if relative.parts[0] in {"datasets", "bird", "external_benchmarks", "nestful", "multidomain"}:
            continue
        ids = used_ids(json.loads(path.read_text()))
        if ids:
            excluded.update(ids)
            sources[str(path.relative_to(ROOT))] = digest(path)
    return excluded, sources


def select_records(store: dict, excluded: set[int], n: int, seed: int) -> list[int]:
    if n < 24 or n % 24:
        raise ValueError("record count must be a positive multiple of 24 (balanced arm orders)")
    eligible = [number for number, row in store.items()
                if number not in excluded and not row.get("pull_request")]
    eligible.sort(key=lambda number: hashlib.sha256(f"fresh-safeguards:{seed}:{number}".encode()).hexdigest())
    if len(eligible) < n:
        raise ValueError(f"only {len(eligible)} unused issues remain; requested {n}; no automatic reuse")
    return eligible[:n]


def schedule(numbers: list[int]) -> list[dict]:
    orders = list(permutations(ARMS))
    return [{"issue_number": number, "arm": arm}
            for index, number in enumerate(numbers) for arm in orders[index % len(orders)]]


def support_registry(original: Any) -> Any:
    """Disable only score/admission on a deep copy, retaining program/H/V/effects.

    This is an uncertified research ablation on an already admitted candidate,
    not a second compiler and not a new statistical certificate.
    """
    from guarded_agentic_compaction.schema.artifacts import Gate

    result = copy.deepcopy(original)
    for artifact in result.artifacts:
        if artifact.gate.n_calibration_groups < 92:
            raise ValueError("support-only arm requires the registered 92-group floor")
        artifact.gate = Gate(threshold=1.0, alpha=1.0, delta=0.10,
                             n_calibration_groups=artifact.gate.n_calibration_groups,
                             risk_upper_bound=1.0, retire=False,
                             notes="UNCERTIFIED support-only ablation; score and risk admission disabled")
    result._reindex()
    return result


def runtime() -> tuple:
    import github_live_study as fixed
    import recurrence_only_ablation as shared
    import second_model_replication as reconstruction

    store, source = shared.load_store()
    tools, catalog = fixed.make_tools(store), fixed.make_catalog()
    manifest = fixed.make_manifest(MODEL, tools, catalog, TASK)
    retained = shared.load_retained()
    checkpoint = json.loads(reconstruction.CHECKPOINT.read_text())
    discovery = reconstruction.reconstruct_discovery(checkpoint, store=store, manifest=manifest)
    original, record, _ = reconstruction.compile_for_model(discovery, model=MODEL, catalog=catalog, tools=tools)
    if (reconstruction.artifact_fingerprint(record["artifact"]) !=
            reconstruction.artifact_fingerprint(retained["compiler"]["artifact"])
            or record["splits"]["digest"] != retained["compiler"]["splits"]["digest"]):
        raise ValueError("current compiler does not reproduce the retained program/gate/splits")
    source["candidate_reproduction"] = {
        "method": "provider-free reconstruction of historical discovery",
        "historical_compatibility_key": retained["compiler"]["artifact"]["compatibility_key"],
        "runtime_compatibility_key": manifest.compatibility_key(),
        "program_admission_counts_splits_identical": True,
        "changed_contract_components": [key for key in ("guard", "verifier", "gate")
                                        if record["artifact"][key] != retained["compiler"]["artifact"][key]],
    }
    if len(original.artifacts) != 1 or not original.resolve(manifest.compatibility_key(), {}, kind="grc"):
        raise ValueError("retained artifact does not resolve under current runtime; do not silently repin or fall back")
    return store, source, tools, catalog, manifest, original, support_registry(original)


def code_hashes() -> dict[str, str]:
    paths = list((ROOT / "src/guarded_agentic_compaction").rglob("*.py"))
    paths += [Path(__file__), ROOT / "paper/scripts/github_live_study.py",
              ROOT / "paper/scripts/recurrence_only_ablation.py",
              ROOT / "demos/live_runtime.py", PROTOCOL, REGISTRY,
              ROOT / "paper/scripts/second_model_replication.py",
              ROOT / "paper/scripts/gate_frontier_pilot_preflight.py",
              ROOT / "paper/results/github_natural_replication/discovery_checkpoint.json",
              ROOT / "paper/results/github_natural_replication/results.json"]
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted(set(paths))}


def probe(numbers: list[int], store: dict, catalog: Any, manifest: Any, registries: dict) -> dict:
    """Execute the real dispatcher and snapshot tools, without any answer model."""
    import recurrence_only_ablation as shared
    from guarded_agentic_compaction.runtime.dispatch import Dispatcher

    rows = []
    for number in numbers:
        entry = {"issue_number": number, "arms": {}}
        for arm, registry in registries.items():
            decision = Dispatcher(registry, catalog, mode="live").decide(
                compatibility_key=manifest.compatibility_key(), partition={},
                entry_state={"issue_number": number}, context={
                    **{key: getattr(manifest, key) for key in
                       ("model", "prompt_hash", "tools_hash", "policy_hash", "guardrail_hash", "entry_contract_version")},
                    "effect_catalog_version": catalog.catalog_version,
                    "day": "",  # same entry-only context as CompactingModel
                },
                executor=lambda tool, arguments: shared.execute_issue_snapshot(store, tool, arguments),
            )
            entry["arms"][arm] = {"outcome": decision.outcome.value, "reasons": list(decision.reasons),
                                  "tools_executed": [tool for tool, _ in decision.calls],
                                  "output_sha256": object_digest(decision.results)}
        sequence, _, evidence = shared.replay_three_reads(store, number)
        entry["arms"]["recurrence_only"] = {"outcome": "REPLAYED", "tools_executed": sequence,
                                            "output_sha256": object_digest(evidence)}
        rows.append(entry)
    configuration_failures = [reason for row in rows for arm in registries
                              for reason in row["arms"][arm]["reasons"]
                              if reason.startswith(("manifest_missing:", "manifest_mismatch:", "no_artifact"))]
    if configuration_failures:
        raise ValueError(f"invalid dispatcher setup: {configuration_failures[:3]}")
    return {"provider_calls_executed": 0, "end_to_end_quality_measured": False,
            "outcomes": {arm: dict(Counter(r["arms"][arm]["outcome"] for r in rows))
                         for arm in (*registries, "recurrence_only")}, "records": rows}


def preflight(out: Path, n: int = 120, seed: int = SEED) -> dict:
    if (out / "preflight.json").exists() or (out / "checkpoint.json").exists():
        raise ValueError("output already sealed; use verify, not reselection")
    store, source, _, catalog, manifest, original, support = runtime()
    excluded, exclusion_sources = exclusion_audit(ROOT / "paper/results")
    numbers = select_records(store, excluded, n, seed)
    import gate_frontier_pilot_preflight as strata
    from demos.live_runtime import MODEL_PRICES

    payload = {
        "schema": "gac-fresh-safeguards-preflight/v1", "status": "sealed_not_run",
        "provider_calls_executed": 0, "model": MODEL, "task": TASK,
        "seed": seed, "source": source, "test_ids": numbers,
        "excluded_ids": sorted(excluded), "exclusion_source_hashes": exclusion_sources,
        "source_code_hashes": code_hashes(), "manifest_compatibility_key": manifest.compatibility_key(),
        "dependency_versions": {p: version(p) for p in ("openai", "openai-agents", "pydantic", "numpy", "scipy")},
        "frozen_rate_card": asdict(MODEL_PRICES[MODEL]),
        "arm_artifacts": {"gac": original.artifacts[0].to_dict(), "support_only": support.artifacts[0].to_dict()},
        "schedule": schedule(numbers),
        "stratum_counts": dict(Counter(strata._risk_stratum(store[n]["comments"]) for n in numbers)),
        "probe": probe(numbers, store, catalog, manifest, {"gac": original, "support_only": support}),
        "limitations": ["fresh records from the same historical snapshot, not time-forward",
                        "fixed previously admitted artifact; no new discovery or calibration",
                        "one workflow; 120-record default is exploratory, not powered noninferiority",
                        "support-only is conditional on prior candidate admission",
                        "recurrence comparison changes context and prefix length as well as safeguards"],
    }
    write_json(out / "preflight.json", payload)
    return payload


def verify(out: Path) -> tuple[dict, tuple]:
    frozen = json.loads((out / "preflight.json").read_text())
    if frozen["source_code_hashes"] != code_hashes():
        raise ValueError("source/protocol/artifact changed after sealing")
    for path, expected in frozen["exclusion_source_hashes"].items():
        if digest(ROOT / path) != expected:
            raise ValueError(f"prior evidence changed: {path}")
    actual = {p: version(p) for p in frozen["dependency_versions"]}
    if actual != frozen["dependency_versions"]:
        raise ValueError("dependency versions changed after sealing")
    current = runtime()
    store, source, _, _, manifest, original, support = current
    from demos.live_runtime import MODEL_PRICES
    if source != frozen["source"] or asdict(MODEL_PRICES[MODEL]) != frozen["frozen_rate_card"]:
        raise ValueError("source or frozen price changed")
    if manifest.compatibility_key() != frozen["manifest_compatibility_key"]:
        raise ValueError("runtime manifest changed")
    if {"gac": original.artifacts[0].to_dict(), "support_only": support.artifacts[0].to_dict()} != frozen["arm_artifacts"]:
        raise ValueError("arm definitions changed")
    ids = frozen["test_ids"]
    latest_excluded, _ = exclusion_audit(ROOT / "paper/results")
    if set(ids) & latest_excluded:
        raise ValueError("another study has used a sealed test record; amendment required")
    if (len(ids) != len(set(ids)) or set(ids) & set(frozen["excluded_ids"])
            or not set(ids).issubset(store) or frozen["schedule"] != schedule(ids)
            or ids != select_records(store, set(frozen["excluded_ids"]), len(ids), frozen["seed"])):
        raise ValueError("invalid frozen selection or schedule")
    return frozen, current


def summarize(frozen: dict, rows: list[dict]) -> dict:
    """All scheduled records remain visible, including failed and unattempted runs."""
    expected = {(r["issue_number"], r["arm"]) for r in frozen["schedule"]}
    indexed = {}
    for row in rows:
        key = (row["issue_number"], row["arm"])
        if key not in expected or key in indexed:
            raise ValueError("unexpected or duplicate outcome")
        indexed[key] = row
    arms = {}
    for arm in ARMS:
        values = [indexed[(n, arm)] for n in frozen["test_ids"] if (n, arm) in indexed]
        completed = [r for r in values if r["status"] == "completed"]
        sums = {metric: sum(float(r["metrics"][metric]) for r in completed) for metric in METRICS}
        arms[arm] = {"scheduled": len(frozen["test_ids"]), "attempted": len(values),
                     "completed": len(completed), "failed": len(values) - len(completed),
                     "not_attempted": len(frozen["test_ids"]) - len(values),
                     "correct": sum(r["quality"]["factuality_exact"] is True for r in completed),
                     "dispatched": sum(r.get("dispatched") is True for r in values),
                     "wrong_after_dispatch": sum(r.get("dispatched") is True and not r["quality"]["factuality_exact"]
                                                 for r in completed),
                     "recorded_resource_totals": sums,
                     "resource_accounting_complete": len(completed) == len(frozen["test_ids"])}
    comparisons = {}
    for arm in ARMS[1:]:
        paired = []
        for number in frozen["test_ids"]:
            base, candidate = indexed.get((number, "baseline")), indexed.get((number, arm))
            # A recorded failure is a task failure; an unattempted run is not an observed answer.
            if base is not None and candidate is not None:
                correct = lambda r: r["status"] == "completed" and r["quality"]["factuality_exact"] is True
                paired.append((correct(base), correct(candidate)))
        comparisons[arm] = {"attempted_pairs": len(paired),
                            "baseline_only_correct": sum(b and not c for b, c in paired),
                            "candidate_only_correct": sum(c and not b for b, c in paired)}
    return {"schema": "gac-fresh-safeguards-summary/v1",
            "status": "completed" if len(indexed) == len(expected) else "incomplete",
            "comparative_claim_allowed": len(indexed) == len(expected),
            "arms": arms, "paired_vs_baseline": comparisons,
            "end_to_end_risk_certified": False,
            "interpretation": "Descriptive fixed-artifact comparison; no causal attribution or noninferiority claim."}


def open_checkpoint(out: Path, frozen: dict, cap: float) -> dict:
    if not math.isfinite(cap) or cap < RESERVE_USD:
        raise ValueError("a finite approved spend cap of at least $1 is required")
    identity = {"preflight_sha256": object_digest(frozen), "approved_spend_usd": cap}
    path = out / "checkpoint.json"
    if path.exists():
        state = json.loads(path.read_text())
        if any(state.get(k) != v for k, v in identity.items()):
            raise ValueError("checkpoint does not match preflight or spend cap")
        if state["pending"] or any(row["status"] != "completed" for row in state["rows"]):
            raise ValueError("interrupted/failed call requires review; automatic retry refused")
        summarize(frozen, state["rows"])
        if [{"issue_number": r["issue_number"], "arm": r["arm"]} for r in state["rows"]] != frozen["schedule"][:len(state["rows"])]:
            raise ValueError("checkpoint order differs from frozen schedule")
        return state
    return {"schema": "gac-fresh-safeguards-checkpoint/v1", **identity,
            "rows": [], "pending": None, "unknown_cost_reserve_usd": 0.0}


async def recurrence_run(number: int, current: tuple, processor: Any) -> dict:
    from agents import RunConfig, Runner
    import github_live_study as fixed
    import recurrence_only_ablation as shared
    from demos.live_runtime import observations_from_trace

    store, _, _, catalog, _, _, _ = current
    item = store[number]
    scenario = fixed.Scenario(number, fixed.category_for(item["labels"]), tuple(item["labels"]),
                              item["html_url"], item["day"], item["state"])
    manifest = fixed.make_manifest(MODEL, [], catalog, TASK)
    trace_id = "trace_" + object_digest(["fresh-safeguards", number, "recurrence_only"])[:32]
    started = time.perf_counter()
    sequence, arguments, evidence = shared.replay_three_reads(store, number)
    result = await asyncio.wait_for(Runner.run(
        fixed.make_agent(MODEL, [], TASK), shared.evidence_prompt(number, evidence), max_turns=8,
        run_config=RunConfig(trace_id=trace_id, workflow_name="fresh-safeguards:recurrence-only",
                             trace_include_sensitive_data=True)), timeout=120)
    wall_ms = (time.perf_counter() - started) * 1000
    records = {record.trace_id: record for record in processor.drain()}
    trace = records.get(trace_id)
    if trace is None or observations_from_trace(trace, {}):
        raise ValueError("missing trace or unexpected provider tool call")
    row = shared.materialize(scenario, model=MODEL, trace=trace, final_output=result.final_output,
                             wall_ms=wall_ms, manifest=manifest, sequence=sequence, arguments=arguments,
                             source_record=item, attempt=0).public_dict()
    row["dispatched"] = True
    return row


async def execute(number: int, arm: str, current: tuple, processor: Any) -> dict:
    import github_live_study as fixed
    if arm == "recurrence_only":
        return await recurrence_run(number, current, processor)
    store, _, tools, catalog, manifest, original, support = current
    item = store[number]
    scenario = fixed.Scenario(number, fixed.category_for(item["labels"]), tuple(item["labels"]),
                              item["html_url"], item["day"], item["state"])
    registry = {"baseline": None, "gac": original, "support_only": support}[arm]
    values, failures = await fixed.run_agents_batch(
        [scenario], condition=f"fresh_{arm}", repeat=0, model_name=MODEL, tools=tools,
        processor=processor, manifest=manifest, catalog=catalog, registry=registry,
        concurrency=1, task_design=TASK, source_store=store)
    if failures or len(values) != 1:
        raise RuntimeError(json.dumps(failures))
    row = values[0].public_dict()
    row["dispatched"] = bool(row.get("dispatch", {}).get("compacted", 0))
    return row


async def _run(out: Path, cap: float, env_file: Path | None = None) -> dict:
    frozen, current = verify(out)
    state = open_checkpoint(out, frozen, cap)
    if len(state["rows"]) == len(frozen["schedule"]):
        return summarize(frozen, state["rows"])
    from dotenv import load_dotenv
    if env_file is not None:
        load_dotenv(env_file)
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY unavailable; no provider call")
    from agents import set_default_openai_client
    from openai import AsyncOpenAI
    from guarded_agentic_compaction.capture.agents_sdk import AgentsTraceProcessor
    # Local capture only; no trace uploads and no SDK transport retries.
    from agents import set_trace_processors
    client = AsyncOpenAI(max_retries=0)
    set_default_openai_client(client, use_for_tracing=False)
    processor = AgentsTraceProcessor(include_sensitive_data=True, max_completed=32)
    set_trace_processors([processor])
    try:
        for planned in frozen["schedule"][len(state["rows"]):]:
            spent = sum(float(r.get("metrics", {}).get("estimated_cost_usd", 0.0)) for r in state["rows"])
            if spent + state["unknown_cost_reserve_usd"] + RESERVE_USD > cap:
                break
            state["pending"] = planned
            write_json(out / "checkpoint.json", state)
            started = time.perf_counter()
            try:
                result = await execute(planned["issue_number"], planned["arm"], current, processor)
                for metric in METRICS:
                    value = result["metrics"].get(metric)
                    if value is None or not math.isfinite(float(value)) or value < 0:
                        raise ValueError(f"missing/invalid {metric}; cost completeness unknown")
                row = {**planned, "status": "completed", "quality": result["quality"],
                       "answer": result["answer"], "metrics": result["metrics"],
                       "tool_sequence": result["tool_sequence"], "tool_arguments": result["tool_arguments"],
                       "dispatch": result.get("dispatch", {}), "dispatched": result["dispatched"],
                       "trace_id": result["trace_id"]}
            except Exception as exc:
                processor.drain()
                row = {**planned, "status": "failed", "error": f"{type(exc).__name__}: {exc}",
                       "elapsed_ms": (time.perf_counter() - started) * 1000}
                state["unknown_cost_reserve_usd"] += RESERVE_USD
            state["rows"].append(row)
            state["pending"] = None
            write_json(out / "checkpoint.json", state)
            report = summarize(frozen, state["rows"])
            write_json(out / "summary.json", report)
            print(f"{len(state['rows'])}/{len(frozen['schedule'])}: {planned['arm']} {row['status']}", flush=True)
            if row["status"] == "failed":
                break
    finally:
        await client.close()
    write_json(out / "checkpoint.json", state)
    report = summarize(frozen, state["rows"])
    write_json(out / "summary.json", report)
    return report


async def run(out: Path, cap: float, env_file: Path | None = None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    lock = out / "run.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError("run already active or interrupted; inspect run.lock before resuming") from exc
    try:
        os.close(descriptor)
        return await _run(out, cap, env_file)
    finally:
        lock.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("preflight", "verify", "run", "summarize"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--records", type=int, default=120)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--approved-spend-usd", type=float)
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    if args.phase == "preflight":
        frozen = preflight(args.output, args.records, args.seed)
        print(json.dumps({"status": frozen["status"], "records": len(frozen["test_ids"]),
                          "probe": frozen["probe"]["outcomes"], "provider_calls_executed": 0}, indent=2))
    elif args.phase == "verify":
        frozen, _ = verify(args.output)
        print(json.dumps({"verified": True, "records": len(frozen["test_ids"]), "provider_calls_executed": 0}))
    elif args.phase == "run":
        if args.approved_spend_usd is None:
            parser.error("run requires --approved-spend-usd")
        print(json.dumps(asyncio.run(run(args.output, args.approved_spend_usd, args.env_file)), indent=2))
    else:
        frozen = json.loads((args.output / "preflight.json").read_text())
        state = json.loads((args.output / "checkpoint.json").read_text())
        if state["preflight_sha256"] != object_digest(frozen):
            raise ValueError("checkpoint identity mismatch")
        print(json.dumps(summarize(frozen, state["rows"]), indent=2))


if __name__ == "__main__":
    main()
