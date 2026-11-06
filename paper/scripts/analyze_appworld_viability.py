"""Aggregate every scheduled arm and retain compiler refusal; no inferential claim."""
from collections import Counter
from dataclasses import asdict
import json

from appworld_adaptive_viability import BASE, CACHE, OUT, NAMESPACE, READS, catalog, verify_records
from adaptive_pilot import ROOT, LOCAL as CAMPAIGN, digest, write
from guarded_agentic_compaction.capture.manifests import build_manifest
from guarded_agentic_compaction.evaluation.splits import Splits
from guarded_agentic_compaction.grc.compile import GrcConfig, compile_grc
from guarded_agentic_compaction.schema.traces import Episode, EventKind, EventNode, TraceEnvelope, OutcomeLabels, Usage


def convert(raw, manifest):
    events, index = [], 0
    def emit(kind, **kwargs):
        n = len(events)
        events.append(EventNode(node_id=f"n{n}", index=n, kind=kind, **kwargs))
    for response in raw.get("provider_trace", []):
        rid = response["id"]
        emit(EventKind.MODEL_REQ, request_id=rid)
        usage = response.get("usage") or {}
        emit(EventKind.MODEL_RESP, request_id=rid, output=response["choices"],
             usage=Usage(input_tokens=usage.get("prompt_tokens", 0), output_tokens=usage.get("completion_tokens", 0)))
        for call in response["choices"][0]["message"].get("tool_calls") or []:
            args = json.loads(call["function"]["arguments"])
            name = args["app"] + "." + args["api"]
            emit(EventKind.TOOL_CALL, tool=name, input=args["arguments"], call_id=call["id"])
            if index >= len(raw.get("calls", [])):
                emit(EventKind.TOOL_RESULT, tool=name, call_id=call["id"], status="error",
                     output={"error": "unobserved_terminal_result", "synthetic_missingness_marker": True})
                continue
            result = raw["calls"][index]
            if result["tool"] != name or result["arguments"] != args["arguments"] or result["call_id"] != call["id"]:
                raise ValueError("trace mismatch; do not repair observable history")
            index += 1
            output = result["result"]
            emit(EventKind.TOOL_RESULT, tool=name, output=output, call_id=call["id"],
                 status="error" if isinstance(output, dict) and "error" in output else "ok")
    if index != len(raw.get("calls", [])):
        raise ValueError("unmatched tool observations")
    group = raw["task_id"].rsplit("_", 1)[0]
    envelope = TraceEnvelope(trace_id=raw["task_id"], episode_id=raw["task_id"], group_id=group,
        manifest_id=manifest.manifest_id, principal="public-simulation", tenant_partition="appworld-development",
        day="2026-11-06", policy_version="appworld-viability-v2", external_state_version="per-task-simulator")
    return Episode(envelope, manifest, {"task": raw.get("context", {})}, events,
        OutcomeLabels(task_success=None),
        attributes={"status": raw["status"], "prior_exposure": "development_only", "outcome_validity": "original on-disk grade invalid; diagnostic repair is separate"})


def summarize(seal, rows):
    expected = {(task, arm) for task in seal["tasks"] for arm in seal["arms"]}
    keys = [(r["task_id"], r["arm"]) for r in rows]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError("one disposition required for every scheduled arm")
    if any(r["status"] in {"started", "running"} for r in rows):
        raise ValueError("unfinished run cannot become final evidence")
    success = lambda r: r["status"] == "completed" and r.get("evaluation", {}).get("success") is True
    totals = {}
    for arm in seal["arms"]:
        subset = [r for r in rows if r["arm"] == arm]
        totals[arm] = {"scheduled": len(subset), "attempted": sum(r["status"] != "unstarted" for r in subset),
            "successes": sum(success(r) for r in subset), "statuses": dict(Counter(r["status"] for r in subset)),
            "model_requests": sum(len(r.get("provider_trace", [])) for r in subset),
            "api_calls": sum(len(r.get("calls", [])) for r in subset),
            "model_api_calls": sum(c["origin"] == "model" for r in subset for c in r.get("calls", [])),
            "seconds_including_setup_grading": sum(r.get("seconds", 0) for r in subset),
            "request_cap_terminations": sum(r.get("termination") == "request_cap" for r in subset)}
    lookup = dict(zip(keys, rows))
    pairs = Counter((success(lookup[t, "baseline"]), success(lookup[t, "manual_prefix"])) for t in seal["tasks"])
    return {"arms": totals, "paired_success": {"both": pairs[True, True], "baseline_only": pairs[True, False],
        "manual_only": pairs[False, True], "neither": pairs[False, False]},
        "interpretation": "One descriptive run per arm and exposed training scenario. No population inference or GAC efficiency claim."}


def build():
    seal = verify_records()
    rows = []
    for task in seal["tasks"]:
        for arm in seal["arms"]:
            path = CACHE / "episodes" / task / (arm + ".json")
            rows.append(json.loads(path.read_text()) if path.exists() else {"task_id": task, "arm": arm, "status": "unstarted"})
    summary = summarize(seal, rows)
    summary["invalid_recorded_paired_success"] = summary.pop("paired_success")
    for values in summary["arms"].values():
        values["invalid_recorded_successes"] = values.pop("successes")
    summary["interpretation"] = "Interrupted due to a confirmed state-persistence measurement defect. Original task grades are invalid; do not interpret these counts as task performance. Separate deterministic regrades are diagnostic, not fresh adaptive trials."
    repair_base = BASE / "persistence_repair"
    repair_plan = json.loads((repair_base / "plan.json").read_text())
    repair_controls = [json.loads(p.read_text()) for p in sorted((repair_base / "controls").glob("*.json"))]
    regrades = []
    for rel in repair_plan["completed_records"]:
        original = json.loads((BASE / rel).read_text())
        p = repair_base / "regrades" / original["task_id"] / (original["arm"] + ".json")
        repaired = json.loads(p.read_text())
        regrades.append({"task_id": original["task_id"], "arm": original["arm"],
            "status": repaired["status"], "diagnostic_valid": repaired.get("diagnostic_valid", False),
            "observations_match": repaired.get("observations_match", False), "context_matches": repaired.get("context_matches", False),
            "success": repaired.get("evaluation", {}).get("success"), "tests": repaired.get("evaluation", {}).get("tests"),
            "passed_tests": repaired.get("evaluation", {}).get("passed_tests")})
    effects = catalog()
    manifest = build_manifest(commit=digest(CACHE / "seal.json"), model=seal["model"], prompt=seal["instructions"],
        tools=seal["tool"], catalog=effects, policy="appworld-development-no-admission",
        guardrails="Audited read-only public API prefixes; login/write/unknown barriers", entry_contract_version="appworld-public-context-v2")
    episodes, dispositions = [], []
    for raw in rows:
        if raw["arm"] != "baseline":
            continue
        try:
            episodes.append(convert(raw, manifest))
        except (ValueError, KeyError, IndexError) as exc:
            dispositions.append({"task_id": raw["task_id"], "reason": type(exc).__name__})
    splits = Splits(train=frozenset(t.rsplit("_", 1)[0] for t in seal["discovery_groups"]),
        dev=frozenset(t.rsplit("_", 1)[0] for t in seal["challenge_groups"]), seed=20261106)
    config = GrcConfig(entry_schema=("task",), partition_by=(), w_min=2, w_max=4, b_min=2, s_min=3,
        min_days=1, max_candidates=8, max_artifacts=1, freeze_one_candidate_before_calibration=True,
        synthesize_composites=False, mode="replay", seed=20261106, owner="appworld-development")
    result = compile_grc(episodes, effects, splits, manifest, config, sandbox=None, perturbations=())
    if result.artifacts:
        raise AssertionError("no calibration means no admitted artifact")
    candidates = [c.as_dict() for c in result.candidates]
    for candidate in candidates:
        candidate["trivial_for_target_claim"] = all(t in READS for t in candidate.get("tools", []))
    ledger = json.loads((CAMPAIGN / "ledger.json").read_text())
    charges = [r for r in ledger["requests"] if r["task"].startswith(NAMESPACE)]
    for arm, values in summary["arms"].items():
        values["accounted_upper_usd"] = sum(r.get("accounted_upper_usd", r["reserved_usd"]) for r in charges if r["arm"] == arm)
    controls = []
    for version, base in (("v1", BASE), ("v2", CACHE)):
        checks = [json.loads((base / "controls" / task / (mode + ".json")).read_text())
                  for task in seal["tasks"] for mode in seal["oracle_controls"]]
        controls.append({"version": version, "scheduled": len(checks), "passed": sum(bool(r.get("passed")) for r in checks),
            "reference_successes": sum(bool(r.get("passed")) for r in checks if r["mode"] == "reference"),
            "negative_controls_passed": sum(bool(r.get("passed")) for r in checks if r["mode"] != "reference")})
    # Actual task strings, API arguments/results and programs derived from them are
    # protected and stay inside the encrypted bundle; public discovery is structural.
    write(CACHE / "analysis" / "normalized_episodes.json", [e.to_dict() for e in episodes])
    write(CACHE / "analysis" / "candidate_details.json", [c.as_dict() | {
        "program": c.synthesis.program.to_dict() if c.synthesis and c.synthesis.ok else None} for c in result.candidates])
    report = {"schema": "appworld-viability-report-v2-interrupted", "decision": "NO_GO_FOR_CONFIRMATORY_EXECUTION",
        "summary": summary, "controls": controls,
        "measurement_validity": "INVALID_ORIGINAL_GRADES_PERSISTENCE_DEFECT",
        "execution_stop": json.loads((CACHE / "execution_stop.json").read_text()),
        "episode_dispositions": [{"task_id": r["task_id"], "arm": r["arm"], "status": r["status"],
            "model_requests": len(r.get("provider_trace", [])), "api_calls": len(r.get("calls", [])),
            "termination": r.get("termination"), "error": r.get("error"),
            "original_grade_valid": False} for r in rows],
        "persistence_repair": {"plan_sha256": digest(repair_base / "plan.json"),
            "direct_path_controls": len(repair_controls), "controls_passed": sum(r.get("diagnostic_valid", False) for r in repair_controls),
            "regrades": regrades, "interpretation": "No new model calls. Exact context/response parity required. Regrades are diagnostic only; interrupted and unstarted cases are not replaced."}, "source_sha256": digest(__file__), "seal_sha256": digest(CACHE / "seal.json"),
        "compiler": {"converted": len(episodes), "dispositions": dispositions,
            "baselines_with_unknown_outcome_retained": sum(e.outcome.task_success is None for e in episodes),
            "splits": splits.manifest(), "config": asdict(config), "report": result.report(),
            "candidates": candidates, "artifacts_emitted": 0,
            "structural_limit": "Current catalog permits documentation/profile/password reads only. Therefore it cannot establish two nontrivial families. This is a scope limitation, not an empirical failure rate or a justified loosening of authentication effects."},
        "budget": {"new_accounted_upper_usd": sum(r.get("accounted_upper_usd", r["reserved_usd"]) for r in charges),
            "campaign_accounted_upper_usd": ledger["accounted_upper_usd"],
            "remaining_cap_usd": ledger["cap_usd"] - ledger["accounted_upper_usd"], "requests": len(charges),
            "cost_scope": "Conservative model/API accounting; local compute and engineering are unpriced."},
        "limitations": ["Interrupted two-arm pilot has invalid original grades; no comparative performance estimate is justified.",
            "All 12 scenarios are development-only and previously exposed; variants do not add independent groups.",
            "One run per arm; no noninferiority, superiority, risk certificate or learned-gate claim.",
            "Authentication remains a write barrier. The available initial read region is structurally narrow.",
            "Compatibility change and all earlier failed controls are retained; no task, reference answer or official test changed."]}
    # Candidate notes may contain inferred literals; publish only safe scalar structure.
    report["compiler"]["candidates"] = [{k: c.get(k) for k in ("candidate_id", "stage", "rejected", "support_groups", "removed_requests", "tools", "trivial_for_target_claim")} for c in candidates]
    write(OUT / "report.json", report)
    write(OUT / "ledger_excerpt.json", {"requests": charges})
    print(json.dumps({"decision": report["decision"], "summary": summary, "candidates": len(candidates), "budget": report["budget"]}))


if __name__ == "__main__":
    build()
