"""Prospective end-to-end gate on a frozen public-issue cohort.

The fixed prior program is evaluated on disjoint development/calibration cases.
Task-contract failures, not replay mismatches, train and calibrate the new gate.
The test set is reached only after the model and threshold are frozen. Every arm
pays for the same declared pre-dispatch source read used to compute risk features.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src", ROOT / "paper/scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import gate_frontier_pilot_preflight as prior  # noqa: E402
import graded_issue_gate_preflight as cohort  # noqa: E402
import github_live_study as fixed  # noqa: E402
import github_natural_workflow_study as natural  # noqa: E402
from guarded_agentic_compaction.capture.agents_sdk import AgentsTraceProcessor  # noqa: E402
from guarded_agentic_compaction.grc.calibrate import CalibrationSample, calibrate_gate, fit_gate_model  # noqa: E402
from guarded_agentic_compaction.registry.store import Registry  # noqa: E402

OUT = ROOT / "paper/results/graded_issue_gate"
CHECKPOINT = OUT / "checkpoint_v2.json"
RESULT = OUT / "results_v2.json"
REGISTRY = OUT / "candidate_v2/registry/registry.json"
RECOMPILE_SUMMARY = OUT / "candidate_v2/summary.json"
ABORT = OUT / "abort_v1.json"
MODEL = "gpt-5.6-luna"
FEATURE_NAMES = ("markdown_link", "bare_url", "log_comments", "label_count", "title_length", "age_years")
MAX_RESERVED_USD_PER_EPISODE = 1.0
MAX_BATCH_SIZE = 8


def risk_read(store: dict[int, dict[str, Any]], issue_number: int) -> tuple[dict[str, float], float]:
    """Declared READ_LOCAL lookup; the measured read is shared by all study arms.

    This is source content, not a model answer or gold label. Text is reduced to
    six entry-visible descriptors; no comment body is passed to the gate model.
    """
    started = time.perf_counter()
    row = store[issue_number]
    stratum = prior._risk_stratum(row["comments"])
    created = date.fromisoformat(str(row["day"])[:10])
    cutoff = date.fromisoformat("2025-06-13")  # pinned snapshot's last day
    features = {
        "markdown_link": float(stratum == "markdown_link"),
        "bare_url": float(stratum == "bare_url"),
        "log_comments": math.log1p(len(row["comments"])),
        "label_count": float(len(row["labels"])),
        "title_length": float(len(row["title"])) / 100.0,
        "age_years": max(0, (cutoff - created).days) / 365.25,
    }
    return features, (time.perf_counter() - started) * 1000.0


def scenario(store: dict[int, dict[str, Any]], number: int) -> fixed.Scenario:
    row = store[number]
    return fixed.Scenario(issue_number=number, category=fixed.category_for(row["labels"]),
                          labels=tuple(row["labels"]), html_url=row["html_url"],
                          day=row["day"], state=row["state"])


def group_samples(rows: list[dict], store: dict[int, dict[str, Any]]) -> list[CalibrationSample]:
    samples = []
    for row in rows:
        number = int(row["issue_number"])
        features, _ = risk_read(store, number)
        graded = natural.grade_factual(scenario(store, number), row["answer"], row["tool_sequence"], store)
        if bool(graded["overall"]) != bool(row["quality"]["overall"]):
            raise ValueError(f"quality changed on issue {number}")
        dispatched = int(row.get("dispatch", {}).get("compacted", 0)) > 0
        samples.append(CalibrationSample(
            group=f"issue:{number}", episode_id=f"issue:{number}", features=features,
            unproductive=not bool(graded["overall"]) if dispatched else False,
            violation=not bool(graded["overall"]) if dispatched else False,
            eligible=dispatched,
            reason="end_to_end_task_contract" if dispatched and not graded["overall"] else "",
        ))
    return samples


def selector(model: Any, threshold: float, store: dict[int, dict[str, Any]], numbers: list[int]) -> dict[int, bool]:
    return {number: model.score(risk_read(store, number)[0]) <= threshold for number in numbers}


def _cost(rows: list[dict]) -> float:
    return sum(float(row.get("metrics", {}).get("estimated_cost_usd") or 0.0) for row in rows)


def _checkpoint(preflight_sha: str, candidate_sha: str, cap: float) -> dict:
    if CHECKPOINT.exists():
        data = json.loads(CHECKPOINT.read_text())
        if (data.get("preflight_sha256") != preflight_sha or data.get("candidate_sha256") != candidate_sha
                or data.get("model") != MODEL or data.get("approved_spend_usd") != cap):
            raise ValueError("checkpoint does not match frozen preflight, candidate, model, or spend cap")
        if data.get("failures") or data.get("pending_batch"):
            raise ValueError("prior failed or interrupted provider batch requires a protocol amendment before retry")
        return data
    return {"schema": "gac-graded-issue-gate-checkpoint/v2", "preflight_sha256": preflight_sha,
            "candidate_sha256": candidate_sha,
            "model": MODEL, "approved_spend_usd": cap, "runs": {}, "failures": [],
            "estimated_spend_usd": 0.0, "failed_run_reserve_usd": 0.0,
            "provider_episodes_attempted": 0, "pending_batch": None}


async def run_phase(
    phase: str, numbers: list[int], *, compiled: bool, store: dict[int, dict[str, Any]],
    checkpoint: dict, args: argparse.Namespace, processor: AgentsTraceProcessor,
    tools: list[Any], catalog: Any, base_manifest: Any, compiled_manifest: Any,
    registry: Registry,
) -> list[dict]:
    saved = checkpoint["runs"].setdefault(phase, [])
    saved_ids = [int(row["issue_number"]) for row in saved]
    if len(saved_ids) != len(set(saved_ids)) or not set(saved_ids).issubset(numbers):
        raise ValueError(f"invalid saved rows for {phase}")
    remaining = [number for number in numbers if number not in set(saved_ids)]
    for index in range(0, len(remaining), args.batch_size):
        batch = remaining[index:index + args.batch_size]
        prereads = {number: risk_read(store, number)[1] for number in batch}
        reserve = len(batch) * MAX_RESERVED_USD_PER_EPISODE
        aborted = json.loads(ABORT.read_text())
        candidate = json.loads(RECOMPILE_SUMMARY.read_text())
        counted = (checkpoint["estimated_spend_usd"] + checkpoint["failed_run_reserve_usd"]
                   + aborted["estimated_cost_usd"] + aborted["interrupted_batch_reserve_usd"]
                   + candidate["estimated_cost_usd"])
        if counted + reserve > args.approved_spend_usd:
            raise RuntimeError(f"budget gate stopped before {phase}; counted={counted:.4f}, reserve={reserve:.2f}")
        checkpoint["pending_batch"] = {"phase": phase, "issue_numbers": batch}
        CHECKPOINT.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n")
        manifest = compiled_manifest if compiled else base_manifest
        results, failures = await natural.run_batch(
            [scenario(store, number) for number in batch],
            condition=phase, repeat=0, model_name=MODEL, tools=tools,
            processor=processor, manifest=manifest, catalog=catalog, store=store,
            registry=registry if compiled else None, concurrency=args.concurrency,
        )
        for result in results:
            row = result.public_dict()
            preread_ms = prereads[int(row["issue_number"])]
            row["metrics"]["study_preread_calls"] = 1
            row["metrics"]["study_preread_ms"] = preread_ms
            row["metrics"]["study_total_tool_calls"] = int(row["metrics"].get("tool_calls") or 0) + 1
            row["metrics"]["study_total_wall_ms"] = float(row["metrics"].get("wall_latency_ms") or 0.0) + preread_ms
            saved.append(row)
        checkpoint["failures"].extend(failures)
        checkpoint["estimated_spend_usd"] = _cost([row for rows in checkpoint["runs"].values() for row in rows])
        checkpoint["failed_run_reserve_usd"] = len(checkpoint["failures"]) * MAX_RESERVED_USD_PER_EPISODE
        checkpoint["provider_episodes_attempted"] += len(batch)
        checkpoint["pending_batch"] = None
        if compiled and not any(int(row.get("dispatch", {}).get("compacted", 0)) > 0 for row in saved):
            checkpoint["failures"].append({"phase": phase, "error": "no actual compiled dispatch; stop before further batches"})
        CHECKPOINT.write_text(json.dumps(checkpoint, indent=2, sort_keys=True, default=str) + "\n")
        print(f"{phase}: {len(saved)}/{len(numbers)}; estimated spend ${checkpoint['estimated_spend_usd']:.4f}", flush=True)
        if failures or len(results) != len(batch):
            raise RuntimeError(f"{phase}: {len(failures)} failures; no retry without protocol amendment")
    return saved


async def run(args: argparse.Namespace) -> dict:
    load_dotenv(ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY unavailable")
    if args.approved_spend_usd <= 0 or args.approved_spend_usd > 200:
        raise ValueError("approved spend must be positive and at most the authorized $200 cap")
    if not 1 <= args.batch_size <= MAX_BATCH_SIZE or not 1 <= args.concurrency <= args.batch_size:
        raise ValueError("batch size or concurrency outside registered limits")
    preflight_sha = cohort.sha256(cohort.OUT)
    frozen = json.loads(cohort.OUT.read_text())
    if frozen != cohort.build() or frozen["status"] != "sealed_not_run":
        raise ValueError("cohort/source drift; no provider call")
    if RESULT.exists():
        raise ValueError("retained result exists; refusing to overwrite")
    if not REGISTRY.exists() or not RECOMPILE_SUMMARY.exists() or not ABORT.exists():
        raise ValueError("v2 candidate and v1 abort record are required before provider calls")
    candidate_sha = cohort.sha256(REGISTRY)
    store, _ = fixed.build_store(pd.read_parquet(prior.SNAPSHOT))
    registry = Registry.load(REGISTRY)
    tools = fixed.make_tools(store)
    catalog = natural.make_catalog()
    base_manifest = natural.make_manifest(MODEL, tools, catalog, "base")
    compiled_manifest = base_manifest
    if json.loads(RECOMPILE_SUMMARY.read_text())["compatibility_key"] != compiled_manifest.compatibility_key():
        raise ValueError("v2 candidate summary does not match live manifest")
    if not registry.resolve(compiled_manifest.compatibility_key(), {}, kind="grc"):
        raise ValueError("v2 candidate does not resolve under the live manifest; no provider call")
    from agents import add_trace_processor
    processor = AgentsTraceProcessor(include_sensitive_data=True, max_completed=4000)
    add_trace_processor(processor)
    OUT.mkdir(parents=True, exist_ok=True)
    checkpoint = _checkpoint(preflight_sha, candidate_sha, args.approved_spend_usd)
    async def phase(name: str, numbers: list[int], compiled: bool) -> list[dict]:
        return await run_phase(name, numbers, compiled=compiled, store=store,
                               checkpoint=checkpoint, args=args, processor=processor,
                               tools=tools, catalog=catalog, base_manifest=base_manifest,
                               compiled_manifest=compiled_manifest, registry=registry)

    dev_ids = [r["issue_number"] for r in frozen["selected"]["development"]]
    cal_ids = [r["issue_number"] for r in frozen["selected"]["calibration"]]
    test_ids = [r["issue_number"] for r in frozen["selected"]["test"]]
    dev = await phase("development_compiled", dev_ids, True)
    dev_samples = group_samples(dev, store)
    model, _ = fit_gate_model(dev_samples, seed=frozen["seed"], feature_names=FEATURE_NAMES)
    calibration = await phase("calibration_compiled", cal_ids, True)
    samples = group_samples(calibration, store)
    learned = calibrate_gate(samples, model=model, alpha=.05, delta=.10, seed=frozen["seed"])
    support_only = calibrate_gate(samples, model=model, alpha=1.0, delta=.10, seed=frozen["seed"])
    gate_record = {"learned": learned.to_dict(), "support_only": support_only.to_dict(),
                   "frozen_model": model.to_dict(),
                   "development": {"groups": len(dev_samples), "admitted": sum(s.eligible for s in dev_samples),
                                   "task_errors": sum(s.violation for s in dev_samples)},
                   "calibration": {"groups": len(samples), "admitted": sum(s.eligible for s in samples),
                                     "task_errors": sum(s.violation for s in samples)}}
    (OUT / "frozen_gate_v2.json").write_text(json.dumps(gate_record, indent=2, sort_keys=True) + "\n")
    if learned.retire:
        payload = {"schema": "gac-graded-issue-gate-result/v1", "status": "retired_before_test",
                   "preflight_sha256": preflight_sha, "gate": gate_record,
                   "checkpoint": checkpoint, "provider_episodes_attempted": checkpoint["provider_episodes_attempted"]}
        RESULT.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")
        return payload

    decisions = selector(model, learned.threshold, store, test_ids)
    support = selector(model, support_only.threshold, store, test_ids)
    await phase("test_baseline", test_ids, False)
    await phase("test_learned_compiled", [n for n in test_ids if decisions[n]], True)
    await phase("test_learned_fallback", [n for n in test_ids if not decisions[n]], False)
    await phase("test_support_compiled", [n for n in test_ids if support[n]], True)
    await phase("test_support_fallback", [n for n in test_ids if not support[n]], False)
    by_phase = checkpoint["runs"]
    def quality(rows: list[dict]) -> dict:
        return {"attempted": len(rows), "correct": sum(bool(r["quality"]["overall"]) for r in rows),
                "compacted": sum(int(r.get("dispatch", {}).get("compacted", 0)) > 0 for r in rows),
                "provider_requests": sum(int(r["metrics"].get("requests") or 0) for r in rows),
                "study_total_tool_calls": sum(int(r["metrics"]["study_total_tool_calls"]) for r in rows),
                "study_total_wall_ms": sum(float(r["metrics"]["study_total_wall_ms"]) for r in rows),
                "estimated_cost_usd": _cost(rows)}
    outcomes = {"baseline": quality(by_phase["test_baseline"]),
                "learned": quality(by_phase["test_learned_compiled"] + by_phase["test_learned_fallback"]),
                "support_only": quality(by_phase["test_support_compiled"] + by_phase["test_support_fallback"])}
    payload = {
        "schema": "gac-graded-issue-gate-result/v1", "status": "completed",
        "run_at_utc": datetime.now(UTC).isoformat(), "model": MODEL,
        "preflight_sha256": preflight_sha, "gate": gate_record, "outcomes": outcomes,
        "decisions": {str(k): v for k, v in decisions.items()},
        "support_decisions": {str(k): v for k, v in support.items()},
        "checkpoint": checkpoint, "provider_episodes_attempted": checkpoint["provider_episodes_attempted"],
        "spend": {"approved_cap_usd": args.approved_spend_usd,
                  "estimated_usd": checkpoint["estimated_spend_usd"],
                  "candidate_estimated_usd": json.loads(RECOMPILE_SUMMARY.read_text())["estimated_cost_usd"],
                  "aborted_v1_estimated_usd": json.loads(ABORT.read_text())["estimated_cost_usd"],
                  "aborted_v1_interrupted_reserve_usd": json.loads(ABORT.read_text())["interrupted_batch_reserve_usd"],
                  "failed_run_reserve_usd": checkpoint["failed_run_reserve_usd"],
                  "invoice_verified": False},
        "limitations": ["one selected public issue snapshot", "stratified target mixture",
                        "historical artifact with existing guard and gate", "pre-dispatch read counted for every arm"],
    }
    RESULT.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-spend-usd", type=float, required=True)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()
    payload = asyncio.run(run(args))
    print(json.dumps({"status": payload["status"], "outcomes": payload.get("outcomes"),
                      "provider_episodes_attempted": payload["provider_episodes_attempted"]}, indent=2))


if __name__ == "__main__":
    main()
