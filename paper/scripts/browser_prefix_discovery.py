"""Posthoc typed-prefix discovery from all six retained development traces.

The historical browser tool had unknown effects. Reclassifying its opening
Submit action is a new representation hypothesis, not historical attestation.
The live boundary controls and fresh calibration are separate requirements.
"""
from dataclasses import asdict
import json
import tarfile
from urllib.parse import urlparse

from adaptive_benchmark_screen import ROOT, sha
from browser_staging_boundary import TOOL, POLICY, OUT, catalog
from guarded_agentic_compaction.capture.manifests import build_manifest
from guarded_agentic_compaction.evaluation.splits import Splits
from guarded_agentic_compaction.grc.compile import GrcConfig, compile_grc
from guarded_agentic_compaction.schema.traces import Episode, EventKind, EventNode, OutcomeLabels, TraceEnvelope, Usage
from webarena_verified_development import SYSTEM, write

PRIOR = ROOT / "paper/results/adaptive_benchmark_screen/webarena_development"


def convert(raw, manifest):
    events, index = [], 0
    def emit(kind, **kwargs):
        n = len(events)
        events.append(EventNode(node_id=f"n{n}", index=n, kind=kind, **kwargs))
    for response in raw["provider_trace"]:
        rid = response["id"]
        emit(EventKind.MODEL_REQ, request_id=rid)
        u = response.get("usage") or {}
        emit(EventKind.MODEL_RESP, request_id=rid, output=response["choices"],
            usage=Usage(input_tokens=u.get("prompt_tokens", 0), output_tokens=u.get("completion_tokens", 0),
                cached_input_tokens=(u.get("prompt_tokens_details") or {}).get("cached_tokens", 0)))
        for call in response["choices"][0]["message"].get("tool_calls") or []:
            args = json.loads(call["function"]["arguments"])
            name = call["function"]["name"]
            if name == "browser":
                result = raw["actions"][index]
                if result["command"] != args:
                    raise ValueError("trace arguments disagree; never invent an observation")
                output = result["observation"]  # preserve full snapshot and errors
                if (index == 0 and args == {"action": "click", "role": "link", "name": "Submit"}
                        and urlparse(raw["input"]["start_urls"][0]).path in {"", "/"}):
                    name, args = TOOL, {"name": "Submit"}
                index += 1
            elif name == "finish":
                if args != raw["answer"]:
                    raise ValueError("final response mismatch")
                output = {"status": "terminal_response_recorded"}
            else:
                raise ValueError("unrecognized historical tool")
            emit(EventKind.TOOL_CALL, tool=name, input=args, call_id=call["id"])
            emit(EventKind.TOOL_RESULT, tool=name, output=output, call_id=call["id"],
                 status="error" if "error" in output else "ok")
    if index != len(raw["actions"]):
        raise ValueError("unmatched action observations")
    group = "webarena-template:" + str(raw["input"]["intent_template_id"])
    envelope = TraceEnvelope(trace_id=str(raw["task_id"]), episode_id=str(raw["task_id"]), group_id=group,
        manifest_id=manifest.manifest_id, principal="public-simulation", tenant_partition="reddit",
        day="2026-11-06", policy_version=POLICY, external_state_version="historical-state-not-attested")
    return Episode(envelope, manifest, {"site": "reddit"}, events,
        OutcomeLabels(task_success=raw.get("evaluation", {}).get("status") == "success"),
        attributes={"attempt_status": raw["status"], "state_attestation": "unavailable",
                    "scope": "posthoc representation diagnostic; no timing or state equality inferred"})


def build():
    seal = json.loads((PRIOR / "seal.json").read_text())
    previous = json.loads((PRIOR / "report.json").read_text())
    archive = PRIOR / "raw_evidence.tar.gz"
    if sha(archive) != previous["raw_archive_sha256"]:
        raise ValueError("prior evidence archive changed")
    effects = catalog()
    manifest = build_manifest(commit=sha(__file__), model=seal["model"], prompt=SYSTEM,
        tools={"typed_prefix": TOOL, "other_browser_actions": "UNKNOWN"}, policy=POLICY,
        guardrails="posthoc historical representation only; no admission", catalog=effects,
        entry_contract_version="fresh-reddit-root-research-v1")
    with tarfile.open(archive) as tar:
        raws = [json.load(tar.extractfile(f"development-v2/{task}/attempt.json")) for task in seal["tasks"]]
    episodes = [convert(raw, manifest) for raw in raws]
    splits = Splits(train=frozenset(ep.group_id for ep in episodes), seed=20261106)
    config = GrcConfig(entry_schema=("site",), partition_by=(), w_min=1, w_max=1, b_min=1, s_min=3,
        min_days=1, max_candidates=1, max_artifacts=1, freeze_one_candidate_before_calibration=True,
        synthesize_composites=False, mode="replay", seed=20261106, owner="browser-representation-development")
    result = compile_grc(episodes, effects, splits, manifest, config, sandbox=None, perturbations=())
    if result.artifacts:
        raise AssertionError("empty calibration must not emit an artifact")
    candidates = []
    for candidate in result.candidates:
        item = candidate.as_dict()
        if candidate.synthesis and candidate.synthesis.ok:
            item["program"] = candidate.synthesis.program.to_dict()
        candidates.append(item)
    return {"schema": "browser-prefix-discovery-v1", "status": "RESEARCH_ONLY_NO_ADMISSION",
        "provider_calls": 0, "artifacts_emitted": len(result.artifacts), "scheduled": len(raws), "converted": len(episodes),
        "archive_sha256": sha(archive), "source_sha256": sha(__file__), "config": asdict(config),
        "splits": splits.manifest(), "report": result.report(), "candidates": candidates,
        "historical_requests": sum(ep.n_requests() for ep in episodes),
        "historical_actions": sum(len(r["actions"]) for r in raws),
        "historical_action_errors_retained": sum("error" in a["observation"] for r in raws for a in r["actions"]),
        "typed_prefix_tasks": [int(ep.episode_id) for ep in episodes if any(e.tool == TOOL for e in ep.tool_calls())],
        "limitations": ["All six development tasks retained, including nonmatching actions and errors; no outcome filtering.",
            "One template per development task; template distinctions are not evidence of independent workflow families.",
            "Historical calls lack server-state attestation. Typed mapping is a posthoc hypothesis, not original read-effect evidence.",
            "Root-page guard alone cannot distinguish posting from retrieval intents; automatic dispatch is not justified.",
            "No calibration, fresh test set, adaptive GAC continuation, matched compiler comparator, or net efficiency result.",
            "A handwritten shortcut can implement the same one-call action; no compiler necessity demonstrated."]}


if __name__ == "__main__":
    result = build()
    write(OUT / "discovery.json", result)
    print(json.dumps({k: result[k] for k in ("scheduled", "converted", "typed_prefix_tasks", "artifacts_emitted", "report")}))
