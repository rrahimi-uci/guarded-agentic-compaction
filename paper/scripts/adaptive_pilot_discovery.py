"""Exploratory GAC discovery from every attempted baseline trace; no calibration."""
from collections import Counter
from dataclasses import asdict
import json
import subprocess

from adaptive_pilot import ROOT, OUT, LOCAL, digest, write
from adaptive_pilot_runtime import INSTRUCTIONS, registry
from adaptive_campaign_budget import MODEL
from guarded_agentic_compaction.capture.manifests import build_manifest
from guarded_agentic_compaction.evaluation.splits import Splits
from guarded_agentic_compaction.grc.compile import GrcConfig, compile_grc
from guarded_agentic_compaction.schema.effects import EffectCatalog
from guarded_agentic_compaction.schema.traces import Episode, EventKind, EventNode, OutcomeLabels, TraceEnvelope, Usage


def convert(raw, manifest, db_sha):
    """Preserve observable calls/results; never reconstruct hidden reasoning."""
    events = []
    remaining = iter(raw.get("tool_calls", []))
    def event(kind, **kwargs):
        idx = len(events)
        events.append(EventNode(node_id=f"n{idx}", kind=kind, index=idx, **kwargs))
    for turn in raw.get("provider_trace", []):
        response = turn["response"]
        rid = response["id"]
        event(EventKind.MODEL_REQ, request_id=rid)
        usage = response.get("usage") or {}
        event(EventKind.MODEL_RESP, request_id=rid, output=response["choices"],
              usage=Usage(input_tokens=usage.get("prompt_tokens", 0), output_tokens=usage.get("completion_tokens", 0),
                          cached_input_tokens=(usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)))
        for call in response["choices"][0]["message"].get("tool_calls") or []:
            args = json.loads(call["function"]["arguments"])
            name = call["function"]["name"]
            result = next(remaining, None)
            if result is None or result["tool"] != name or result["arguments"] != args:
                raise ValueError("observable tool trace mismatch; do not invent a result")
            event(EventKind.TOOL_CALL, tool=name, input=args, call_id=call["id"])
            payload = json.loads(result["result"]["payload"])
            status = "error" if "error" in payload or payload.get("status", "ok") != "ok" else "ok"
            event(EventKind.TOOL_RESULT, tool=name, output=result["result"], call_id=call["id"], status=status)
    if next(remaining, None) is not None:
        raise ValueError("unmatched tool result")
    gid = f"bird-corrected:{raw['question_id']}"
    envelope = TraceEnvelope(trace_id=gid, episode_id=gid, group_id=gid,
        manifest_id=manifest.manifest_id, principal="public-pilot", tenant_partition="pooled-public-bird",
        day="2026-11-06", policy_version="exploratory-pilot", external_state_version=db_sha)
    return Episode(envelope, manifest, {"database": raw["db_id"]}, events,
        OutcomeLabels(task_success=raw["execution_correct"]), final_state_digest=db_sha,
        attributes={"attempt_status": raw["status"], "timing": "not reconstructed; use raw pilot wall time"})


def main():
    seal = json.loads((OUT / "seal.json").read_text())
    results = LOCAL / seal.get("attempt_namespace", "")
    catalog = EffectCatalog.from_dict({"version": 1, "name": "pooled-pinned-readonly-bird", "tools": {
        name: {"effect": "READ_LOCAL", "capabilities": ["speculatable", "replayable", "cacheable"],
               "key": keys, "resource": "pinned-bird-database-at-entry"}
        for name, keys in {"list_tables": [], "get_schema": ["table_names"], "run_query": ["sql"]}.items()}})
    manifest = build_manifest(commit=seal["source_hashes"]["paper/scripts/adaptive_pilot.py"], model=MODEL,
        prompt=INSTRUCTIONS, tools=registry()["tools"], policy="exploratory-pilot-no-admission",
        guardrails="read-only immutable SQLite", catalog=catalog, entry_contract_version="pooled-bird-database-v1")
    episodes, rejected = [], []
    for task in seal["tasks"]:
        path = results / f"{task['question_id']}-baseline/result.json"
        if not path.exists():
            rejected.append({"question_id": task["question_id"], "reason": "unstarted"})
            continue
        raw = json.loads(path.read_text())
        try:
            episodes.append(convert(raw, manifest, seal["database_sha256"][task["db_id"]]))
        except (ValueError, KeyError) as exc:
            rejected.append({"question_id": task["question_id"], "reason": str(exc)})
    groups = lambda role: frozenset(f"bird-corrected:{t['question_id']}" for t in seal["tasks"] if t["discovery_split"] == role)
    splits = Splits(train=groups("train"), dev=groups("dev"), seed=20261106)
    config = GrcConfig(entry_schema=("database",), partition_by=(), w_min=2, w_max=3, b_min=2, s_min=5,
        min_days=1, max_candidates=8, max_artifacts=1, freeze_one_candidate_before_calibration=True,
        synthesize_composites=False, mode="replay", seed=20261106, owner="exploratory-pilot")
    result = compile_grc(episodes, catalog, splits, manifest, config, sandbox=None, perturbations=())
    if result.artifacts:
        raise AssertionError("no calibrated artifact permitted with empty calibration")
    record = {"schema": "gac-adaptive-pilot-discovery-v1", "seal_sha256": digest(OUT / "seal.json"),
        "analysis_source_sha256": digest(__file__), "scheduled_baselines": len(seal["tasks"]),
        "converted": len(episodes), "conversion_dispositions": rejected,
        "filter": "no filtering on answer correctness or completed status; compiler qualification reported separately",
        "splits": splits.manifest(), "config": asdict(config), "report": result.report(),
        "candidates": [c.as_dict() for c in result.candidates], "rejection_by_stage": dict(result.rejection_by_stage),
        "opening_sequences": dict(Counter(" -> ".join(e.tool or "" for e in ep.tool_calls()[:3]) for ep in episodes)),
        "status": "EXPLORATORY_ONLY_NO_CALIBRATION_NO_ADMISSION",
        "limitations": ["Fixed pilot train/dev split; analysis code finalized during operational pilot.",
            "Tasks pooled across nine databases; no new independence or population guarantee.",
            "No timing inferred from normalized event indices; raw episode timing is authoritative."]}
    write(OUT / "gac_discovery.json", record)
    write(results / "normalized_baseline_episodes.json", [ep.to_dict() for ep in episodes])
    print(json.dumps({"episodes": len(episodes), "candidates": len(result.candidates), "artifacts": 0}))


if __name__ == "__main__":
    main()
