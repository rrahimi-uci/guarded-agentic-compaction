"""Time-forward PR-outcome study: re-derived artifact, end-to-end calibration labels, evaluation.

Protocol: ``paper/supplementary/time-forward-end-to-end-protocol.md`` (pre-registered
2026-10-07, amended before execution). Phases, each checkpointed under ``--out``:

  selection   write the three disjoint fresh splits (test 60, discovery 132, calibration 132)
  discovery   live: unchanged agent on the discovery records; compile with one frozen candidate
  calibrate   live: dispatch the re-derived artifact on each calibration group, run the
              continuation once, grade the exact contract; single-rule end-to-end certificate
  test        live: baseline, re-derived artifact, retained artifact under its pins, manual
              program on the 60 test records

Live phases refuse to run without ``--approved-spend-usd``; every result's estimated cost is
ledgered and the run stops when the cap would be exceeded. ``--pilot N`` runs the first N
calibration groups and stops. Everything the family study does (tools, prompts, grader,
manifests, compiler) is reused unchanged; only the snapshot identity differs.
"""

from __future__ import annotations

import argparse
import asyncio
import functools
import hashlib
import json
import os
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from scipy.stats import beta  # noqa: E402

SNAPSHOT_DIR = ROOT / "paper/results/datasets/github_time_forward/huggingface__datasets"
RETAINED_REGISTRY = ROOT / "paper/results/github_workflow_families/pr_outcome/final/registry"
FAMILY = "pr_outcome"
MODEL = "gpt-5.6-luna"
SPLITS = {"test_per_class": 20, "discovery": 132, "calibration": 132}
ALPHA, DELTA = 0.05, 0.10


def cp_upper(k: int, n: int, conf: float) -> float | None:
    if n == 0:
        return None
    if k >= n:
        return 1.0
    if k == 0:
        return 1.0 - (1.0 - conf) ** (1.0 / n)
    return float(beta.ppf(conf, k + 1, n - k))


def _rank(number: int) -> str:
    return hashlib.sha256(f"time-forward:{FAMILY}:{number}".encode()).hexdigest()


def _digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def bind_snapshot():
    """Point the family study at the time-forward snapshot and its identity."""
    import github_live_study as fixed
    import github_workflow_family_study as fam

    manifest = json.loads((SNAPSHOT_DIR / "source_manifest.json").read_text())
    fam.DATA_PATH = SNAPSHOT_DIR / "snapshot.parquet"
    fixed.DATA_PATH = SNAPSHOT_DIR / "snapshot.parquet"
    fixed.HF_REVISION = manifest["parquet_sha256"]
    fixed.HF_PARQUET_SHA256 = manifest["parquet_sha256"]
    fixed.HF_DATASET = f"github-api:{manifest['repository']}:created-after-{manifest['created_after_utc_day']}"
    return fam, fixed, manifest


def select(fam, store: dict[int, dict[str, Any]], used: set[int]) -> dict[str, Any]:
    spec = fam.FAMILIES[FAMILY]
    fresh = sorted((n for n, row in store.items() if row.get("pull_request") and n not in used), key=_rank)
    by_class: dict[str, list[int]] = {}
    for n in fresh:
        by_class.setdefault(spec.class_for(store[n]), []).append(n)
    test: list[int] = []
    for cls in spec.classes:
        pool = by_class.get(cls, [])
        if len(pool) < SPLITS["test_per_class"]:
            raise RuntimeError(f"class {cls} has {len(pool)} fresh records; need {SPLITS['test_per_class']}")
        test.extend(pool[: SPLITS["test_per_class"]])
    remaining = {cls: [n for n in by_class.get(cls, []) if n not in set(test)] for cls in spec.classes}
    discovery: list[int] = []
    while len(discovery) < SPLITS["discovery"]:
        progressed = False
        for cls in spec.classes:
            if remaining[cls] and len(discovery) < SPLITS["discovery"]:
                discovery.append(remaining[cls].pop(0))
                progressed = True
        if not progressed:
            raise RuntimeError("fresh pool exhausted before the discovery split was filled")
    taken = set(test) | set(discovery)
    calibration = [n for n in fresh if n not in taken][: SPLITS["calibration"]]
    if len(calibration) < SPLITS["calibration"]:
        raise RuntimeError(f"only {len(calibration)} calibration records available")
    sel = {
        "schema": "agent-compaction-time-forward-selection/v1", "family": FAMILY, "rule": "stable sha256 rank; test 20 per class; discovery round-robin over classes; calibration next in rank order",
        "fresh_pool": len(fresh), "test": test, "discovery": discovery, "calibration": calibration,
        "test_class_counts": dict(Counter(spec.class_for(store[n]) for n in test)),
        "discovery_class_counts": dict(Counter(spec.class_for(store[n]) for n in discovery)),
        "calibration_class_counts": dict(Counter(spec.class_for(store[n]) for n in calibration)),
        "disjoint": not (set(test) & set(discovery) or set(test) & set(calibration) or set(discovery) & set(calibration)),
    }
    sel["digest"] = _digest({k: sel[k] for k in ("test", "discovery", "calibration")})
    return sel


class Ledger:
    def __init__(self, path: Path, cap: float | None) -> None:
        self.path, self.cap = path, cap
        self.state = json.loads(path.read_text()) if path.exists() else {"spent_usd": 0.0, "entries": []}

    def charge(self, phase: str, results: Sequence[Any]) -> None:
        cost = float(sum(float(r.metrics.get("estimated_cost_usd", 0.0)) for r in results))
        self.state["spent_usd"] = round(self.state["spent_usd"] + cost, 6)
        self.state["entries"].append({"phase": phase, "results": len(results), "estimated_cost_usd": round(cost, 6),
                                      "cumulative_usd": self.state["spent_usd"], "at": datetime.now(UTC).isoformat(timespec="seconds")})
        self.path.write_text(json.dumps(self.state, indent=2) + "\n")

    def reserve(self, n_records: int, per_record: float = 0.01) -> None:
        if self.cap is None:
            raise RuntimeError("live phase without --approved-spend-usd")
        if self.state["spent_usd"] + n_records * per_record > self.cap:
            raise RuntimeError(f"reservation {n_records}x{per_record} would exceed cap {self.cap} (spent {self.state['spent_usd']})")


def _public(results: Sequence[Any]) -> list[dict[str, Any]]:
    return [r.public_dict() for r in results]


async def main_async(args: argparse.Namespace) -> int:
    fam, fixed, snap = bind_snapshot()
    import github_time_forward_preflight as pre
    from guarded_agentic_compaction.grc.compile import GrcConfig
    from guarded_agentic_compaction.registry.store import Registry
    from guarded_agentic_compaction.runtime.manual import ManualPreModelRunner

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    spec = fam.FAMILIES[FAMILY]
    store, store_audit = fam.load_store()
    used, _ = pre.used_records()
    sel_path = out / "selection.json"
    if sel_path.exists():
        selection = json.loads(sel_path.read_text())
    else:
        selection = select(fam, store, used)
        sel_path.write_text(json.dumps(selection, indent=2) + "\n")
    print(f"[tf] selection digest {selection['digest']} test={len(selection['test'])} discovery={len(selection['discovery'])} calibration={len(selection['calibration'])}")
    if args.phase == "selection":
        return 0

    ledger = Ledger(out / "ledger.json", args.approved_spend_usd)
    if args.dry_run:
        print(json.dumps({"dry_run": True, "phase": args.phase, "records": {k: len(selection[k]) for k in ("test", "discovery", "calibration")},
                          "cap": args.approved_spend_usd, "spent": ledger.state["spent_usd"]}))
        return 0
    fam.load_dotenv(ROOT / ".env")
    key_env = fixed.provider_api_key_env(MODEL)
    if not os.getenv(key_env):
        raise RuntimeError(f"{key_env} is not set")
    from agents import add_trace_processor

    processor = fam.AgentsTraceProcessor(include_sensitive_data=True, max_completed=8_000)
    add_trace_processor(processor)
    catalog = fam.make_catalog(spec)
    tools = fam.make_tools(spec, store)
    source_manifest = fam.make_manifest(spec, MODEL, tools, catalog, "source", instructions=spec.discovery_prompt)
    baseline_manifest = fam.make_manifest(spec, MODEL, tools, catalog, "baseline", instructions=spec.prompt)
    continuation_manifest = fam.make_manifest(spec, MODEL, (), catalog, "pre-model", instructions=spec.prompt)
    run_meta = {"timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"), "family": FAMILY, "model": MODEL, "provider_backed": True,
                "real_public_records": True, "simulated": False, "openai_api_key_used": True, "secrets_serialized": False,
                "snapshot": snap, "store_audit": store_audit, "selection_digest": selection["digest"], "protocol": "paper/supplementary/time-forward-end-to-end-protocol.md"}
    rows_of = lambda numbers: [store[n] for n in numbers]  # noqa: E731

    # ---- discovery + re-derivation ------------------------------------------
    disc_path = out / "discovery_checkpoint.json"
    if args.phase in ("discovery", "all") or not disc_path.exists():
        if disc_path.exists():
            checkpoint = json.loads(disc_path.read_text())
            discovery = fam.reconstruct_discovery(spec, checkpoint, store=store, manifest=source_manifest)
        else:
            ledger.reserve(len(selection["discovery"]))
            discovery, failures = await fam.run_batch(spec, rows_of(selection["discovery"]), condition="discovery", model_name=MODEL, tools=tools,
                                                      processor=processor, manifest=source_manifest, catalog=catalog, store=store,
                                                      concurrency=args.concurrency, instructions=spec.discovery_prompt)
            ledger.charge("discovery", discovery)
            disc_path.write_text(json.dumps({"schema": "agent-compaction-time-forward-discovery/v1", "run": run_meta, "failures": failures,
                                             "selection": selection, "results": _public(discovery)}, indent=2, sort_keys=True, default=str) + "\n")
        exact = sum(1 for r in discovery if r.quality["overall"])
        print(f"[tf] discovery: {len(discovery)} traces, {exact} exact; spent {ledger.state['spent_usd']:.4f}")
        fam.GrcConfig = functools.partial(GrcConfig, freeze_one_candidate_before_calibration=True)
        try:
            registry, compilation = fam.compile_artifact(spec, discovery, catalog=catalog, source_manifest=source_manifest, continuation_manifest=continuation_manifest)
        except RuntimeError as exc:
            (out / "compile.json").write_text(json.dumps({"status": "retired", "error": str(exc), "run": run_meta}, indent=2, default=str) + "\n")
            print(f"[tf] compile retired: {exc}")
            return 0
        registry.save(out / "registry")
        compilation["frozen_single_candidate"] = True
        (out / "compile.json").write_text(json.dumps({"status": "admitted" if registry.artifacts else "retired", "compilation": compilation, "run": run_meta}, indent=2, sort_keys=True, default=str) + "\n")
        print(f"[tf] compile: {len(registry.artifacts)} artifact(s): {[a.artifact_id for a in registry.artifacts]}")
        if args.phase == "discovery":
            return 0
    registry = Registry.load(out / "registry")
    if not registry.artifacts:
        print("[tf] no re-derived artifact; A2 retires at compilation")
        return 0

    # ---- A2: end-to-end calibration labels -----------------------------------
    cal_path = out / "calibration_checkpoint.json"
    if args.phase in ("calibrate", "all"):
        done = json.loads(cal_path.read_text()) if cal_path.exists() else {"results": [], "failures": []}
        completed = {int(r["issue_number"]) for r in done["results"]}
        todo = [n for n in selection["calibration"] if n not in completed]
        if args.pilot:
            todo = todo[: args.pilot]
        if todo:
            ledger.reserve(len(todo), per_record=0.02)
            results, failures = await fam.run_batch(spec, rows_of(todo), condition="compiled", model_name=MODEL, tools=(), processor=processor,
                                                    manifest=continuation_manifest, catalog=catalog, store=store, concurrency=args.concurrency,
                                                    registry=registry, artifact_manifest=source_manifest, fallback_tools=tools,
                                                    fallback_manifest=baseline_manifest, instructions=spec.prompt)
            ledger.charge("calibrate", results)
            done["results"].extend(_public(results)); done["failures"].extend(failures)
            done.update({"schema": "agent-compaction-time-forward-calibration/v1", "run": run_meta, "selection_digest": selection["digest"]})
            cal_path.write_text(json.dumps(done, indent=2, sort_keys=True, default=str) + "\n")
        summary = certificate(done["results"])
        (out / "certificate.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        print(f"[tf] calibration: {json.dumps({k: summary[k] for k in ('n_eligible', 'attempted', 'abstained', 'violations', 'upper_90', 'admits')})}; spent {ledger.state['spent_usd']:.4f}")
        if args.pilot or args.phase == "calibrate":
            return 0

    # ---- C2: time-forward evaluation ------------------------------------------
    if args.phase in ("test", "all"):
        eval_path = out / "evaluation_checkpoint.json"
        done = json.loads(eval_path.read_text()) if eval_path.exists() else {"results": [], "failures": []}
        completed = {(r["condition"], int(r["issue_number"])) for r in done["results"]}
        retained = None
        try:
            retained = Registry.load(RETAINED_REGISTRY)
        except Exception as exc:  # noqa: BLE001
            done["retained_registry_error"] = str(exc)
        manual_runner = ManualPreModelRunner(fam.make_manual_plan(spec, catalog=catalog, source_manifest=source_manifest, continuation_manifest=continuation_manifest), catalog, source_manifest)
        conditions = ["baseline", "compiled", "manual_pre_model"] + (["compiled_retained"] if retained is not None else [])
        for index, n in enumerate(selection["test"]):
            order = conditions[index % len(conditions):] + conditions[: index % len(conditions)]
            for condition in order:
                if (condition, n) in completed:
                    continue
                kwargs: dict[str, Any] = {"tools": tools, "manifest": baseline_manifest, "instructions": spec.prompt}
                label = condition
                if condition == "compiled":
                    kwargs = {"tools": (), "manifest": continuation_manifest, "registry": registry, "artifact_manifest": source_manifest,
                              "fallback_tools": tools, "fallback_manifest": baseline_manifest, "instructions": spec.prompt}
                elif condition == "compiled_retained":
                    kwargs = {"tools": (), "manifest": continuation_manifest, "registry": retained, "artifact_manifest": source_manifest,
                              "fallback_tools": tools, "fallback_manifest": baseline_manifest, "instructions": spec.prompt}
                    label = "compiled"
                elif condition == "manual_pre_model":
                    kwargs = {"tools": (), "manifest": continuation_manifest, "pre_model_runner": manual_runner,
                              "fallback_tools": tools, "fallback_manifest": baseline_manifest, "instructions": spec.prompt}
                ledger.reserve(1, per_record=0.02)
                results, failures = await fam.run_batch(spec, [store[n]], condition=label, model_name=MODEL, processor=processor, catalog=catalog,
                                                        store=store, concurrency=1, **kwargs)
                ledger.charge(f"test:{condition}", results)
                for r in results:
                    d = r.public_dict(); d["condition"] = condition; done["results"].append(d)
                done["failures"].extend(failures)
                done.update({"schema": "agent-compaction-time-forward-evaluation/v1", "run": run_meta, "selection_digest": selection["digest"], "conditions": conditions})
                eval_path.write_text(json.dumps(done, indent=2, sort_keys=True, default=str) + "\n")
        summary = evaluation_summary(done["results"], conditions)
        (out / "evaluation.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        print(f"[tf] evaluation: {json.dumps(summary['exact'])}; spent {ledger.state['spent_usd']:.4f}")
    return 0


def classify_dispatch(row: dict[str, Any]) -> str:
    d = row.get("dispatch") or {}
    outcome = str(d.get("outcome") or "")
    if outcome in ("REPLAYED", "COMPACTED", "EXECUTED"):  # completed dispatch (compiled or manual plan)
        return "attempted"
    reasons = " ".join(str(x) for x in (d.get("reasons") or [])) + " " + json.dumps(d, default=str)
    if "manifest" in reasons or "guard" in reasons.lower() and "verifier" not in reasons.lower():
        return "ineligible"
    return "abstained"


def certificate(results: Sequence[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[int, dict[str, Any]] = {}
    for r in results:
        groups[int(r["issue_number"])] = {"class": classify_dispatch(r), "exact": bool(r["quality"].get("overall")), "dispatch": r.get("dispatch")}
    attempted = [g for g in groups.values() if g["class"] == "attempted"]
    abstained = [g for g in groups.values() if g["class"] == "abstained"]
    violations = sum(1 for g in attempted if not g["exact"])
    n = len(attempted) + len(abstained)
    upper = cp_upper(violations, n, 1 - DELTA)
    return {"rule": "single pre-registered acceptance rule; gamma = delta = 0.10; m = 1; violation = contract miss after a completed dispatch; abstention stays in n",
            "n_eligible": n, "attempted": len(attempted), "abstained": len(abstained), "ineligible": sum(1 for g in groups.values() if g["class"] == "ineligible"),
            "violations": violations, "violation_records": sorted(k for k, g in groups.items() if g["class"] == "attempted" and not g["exact"]),
            "upper_90": upper, "admits": bool(upper is not None and upper <= ALPHA), "alpha": ALPHA, "delta": DELTA,
            "floors_at_k": {str(k): next(nn for nn in range(k + 1, 2000) if cp_upper(k, nn, 1 - DELTA) <= ALPHA) for k in range(5)},
            "per_record": {str(k): v for k, v in sorted(groups.items())}}


def evaluation_summary(results: Sequence[dict[str, Any]], conditions: Sequence[str]) -> dict[str, Any]:
    by = {c: {int(r["issue_number"]): r for r in results if r["condition"] == c} for c in conditions}
    out: dict[str, Any] = {"n": {c: len(v) for c, v in by.items()}, "exact": {c: sum(bool(r["quality"].get("overall")) for r in v.values()) for c, v in by.items()},
                           "dispatch": {c: dict(Counter(classify_dispatch(r) for r in v.values())) for c, v in by.items() if c != "baseline"},
                           "mean_metrics": {}}
    for c, v in by.items():
        if v:
            out["mean_metrics"][c] = {k: round(sum(float(r["metrics"].get(k, 0)) for r in v.values()) / len(v), 6) for k in ("requests", "total_tokens", "wall_latency_ms", "estimated_cost_usd")}
    base = by.get("baseline", {})
    if "baseline" in out["mean_metrics"]:
        b = out["mean_metrics"]["baseline"]
        out["reduction_vs_baseline_pct"] = {c: {k: round(100 * (1 - v[k] / b[k]), 1) for k in b if b[k]} for c, v in out["mean_metrics"].items() if c != "baseline"}
    out["compiled_only_misses"] = {c: sorted(k for k, r in v.items() if k in base and base[k]["quality"].get("overall") and not r["quality"].get("overall")) for c, v in by.items() if c != "baseline"}
    return out


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--phase", choices=("selection", "discovery", "calibrate", "test", "all"), default="selection")
    ap.add_argument("--approved-spend-usd", type=float, default=None)
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", type=Path, default=ROOT / "paper/results/time_forward/pr_outcome")
    args = ap.parse_args(argv)
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
