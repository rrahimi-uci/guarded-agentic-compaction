#!/usr/bin/env python3
"""Sealed AgentHop baseline-competence and dependent-prefix discovery pilot.

The official AgentHop harness, tools, prompts and exact answer grader execute
each scheduled case. Only its OpenAI transport is replaced to enforce the
shared campaign ledger. This is development evidence, not a leaderboard run.
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import sys

from agenthop_campaign_budget import (
    AgentHopBudgetClient, INPUT_UPPER, MAX_OUTPUT, MODEL, OUTPUT_UPPER,
    PRICE_SOURCE, TASK_PREFIX,
)
from agenthop_source_feasibility import (
    CODE_REVISION, DATA_REVISION, Components, build as source_build, digest,
)


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/results/agenthop_baseline_trace_pilot"
N_CASES = 24
COMPETENCE_SUCCESSES = 17  # Development engineering gate, not an inferential test.
SELECTION_SALT = "gac-agenthop-st2-baseline-pilot-v1"
CONFIG = {"budget": 30, "max_turns": 20, "max_tokens": MAX_OUTPUT,
          "max_total_tokens": 200000, "strategy": "direct", "backend": "responses",
          "reasoning_effort": "medium", "temperature": None}


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def selected_ids(rows: list[dict]) -> list[str]:
    """Choose path-component-separated cases without reading outcomes."""
    selected = [r for r in rows if r["question_type"] == "single-target" and r["depth"] == 2]
    if len(selected) != 478:
        raise ValueError("AgentHop fixed subtype denominator changed")
    components = Components(len(selected))
    for i, row in enumerate(selected):
        components.add(i, {row["seed_paper_id"], *row["bridge_paper_ids"],
                           *row["gold_paper_ids"]})
    groups: dict[int, list[str]] = {}
    for i, row in enumerate(selected):
        groups.setdefault(components.root(i), []).append(row["id"])
    ranked = []
    for ids in groups.values():
        group_key = stable_hash(SELECTION_SALT + "|group|" + "|".join(sorted(ids)))
        case_id = min(ids, key=lambda sid: stable_hash(SELECTION_SALT + "|case|" + sid))
        ranked.append((group_key, case_id))
    if len(ranked) != 280:
        raise ValueError("path-overlap component count changed")
    return [sid for _, sid in sorted(ranked)[:N_CASES]]


def read_qa(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def source_check(args) -> list[dict]:
    report = source_build(args.qa, args.graphs, args.papers, args.code_root)
    if report["selected"]["tasks"] != 478 or report["source"]["code_revision"] != CODE_REVISION:
        raise ValueError("pinned source preflight failed")
    return read_qa(args.qa)


def ledger_totals(path: Path) -> dict:
    if not path.exists():
        raise ValueError("shared campaign ledger missing; refusing to reset")
    data = json.loads(path.read_text())
    charged = lambda row: row.get("accounted_upper_usd", row["reserved_usd"])
    cohort_rows = [row for row in data["requests"] if row["task"].startswith(TASK_PREFIX)]
    return {"sha256": digest(path), "accounted_upper_usd": data["accounted_upper_usd"],
            "pilot_accounted_upper_usd": math.fsum(charged(row) for row in data["requests"]
                if row["stage"] == "pilot"), "requests": len(data["requests"]),
            "agenthop_requests": len(cohort_rows),
            "agenthop_accounted_upper_usd": math.fsum(charged(row) for row in cohort_rows)}


def seal(args) -> None:
    rows = source_check(args)
    ids = selected_ids(rows)
    if OUT.exists() and any(OUT.iterdir()):
        raise ValueError("seal output already exists")
    before = ledger_totals(args.ledger)
    payload = {
        "schema": "gac-agenthop-baseline-trace-seal-v1",
        "decision_stage": "development_baseline_competence_and_recurrence_only",
        "code_revision": CODE_REVISION, "dataset_revision": DATA_REVISION,
        "source_audit_sha256": digest(ROOT / "paper/results/agenthop_source_feasibility/report.json"),
        "pilot_script_sha256": digest(Path(__file__)),
        "budget_script_sha256": digest(ROOT / "paper/scripts/agenthop_campaign_budget.py"),
        "official_harness_sha256": digest(args.code_root / "testbed/harness.py"),
        "official_tools_sha256": digest(args.code_root / "testbed/tools.py"),
        "selection_salt": SELECTION_SALT,
        "selection_rule": "24 lowest-hash path-overlap components; one lowest-hash ID per component; IDs, seed, annotated bridge and gold IDs only; no correctness or answer-based selection",
        "case_ids": ids, "scheduled_cases": N_CASES,
        "competence_gate": {"minimum_correct": COMPETENCE_SUCCESSES,
            "denominator": N_CASES, "interpretation": "engineering gate only"},
        "model": MODEL, "model_snapshot": True, "config": CONFIG,
        "price_upper_per_million": {"input": INPUT_UPPER, "output": OUTPUT_UPPER,
            "source": PRICE_SOURCE},
        "shared_campaign_ledger_before": before,
        "stop_rules": ["Do not exceed shared $300 or pilot $30 stage cap",
            "Retain every scheduled case, provider failure and incomplete outcome",
            "Do not rerun a case after observing its outcome",
            "No matched GAC arm unless baseline competence and a dependent grounded region are established"],
        "claim_boundary": "No GAC candidate, comparative result, independent calibration or final test is sealed here",
    }
    OUT.mkdir(parents=True)
    (OUT / "seal.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"sealed_cases": ids, "ledger_before": before}, sort_keys=True))


def load_fixed_samples(args, ids: list[str], rows: list[dict]) -> dict[str, dict]:
    wanted = set(ids)
    qa = {row["id"]: row for row in rows if row["id"] in wanted}
    if set(qa) != wanted:
        raise ValueError("missing fixed QA case")
    graphs = {}
    needed_papers = set()
    with args.graphs.open(encoding="utf-8") as source:
        for line in source:
            graph = json.loads(line)
            if graph["sample_id"] not in wanted:
                continue
            sid = graph["sample_id"]
            if sid in graphs:
                raise ValueError("duplicate fixed graph")
            graphs[sid] = graph
            needed_papers.update(node.get("arxivId", "") for node in graph["nodes"].values())
    if set(graphs) != wanted:
        raise ValueError("missing fixed graph")
    paper_pool = {}
    with args.papers.open(encoding="utf-8") as source:
        for line in source:
            paper = json.loads(line)
            if paper["arxiv_id"] in needed_papers:
                paper_pool[paper["arxiv_id"]] = {
                    "title": paper.get("title", ""), "sections": paper.get("sections", [])}
    samples = {}
    for sid in ids:
        graph = graphs[sid]
        sample_pool = {node["arxivId"]: paper_pool[node["arxivId"]]
                       for node in graph["nodes"].values()
                       if node.get("arxivId") in paper_pool}
        samples[sid] = {**qa[sid], "graph": {"nodes": graph["nodes"],
            "edges": graph["edges"]}, "paper_pool": sample_pool}
    return samples


def public_tool_calls(trajectory) -> list[dict]:
    calls = []
    for turn in trajectory.turns:
        for tc in turn.tool_calls:
            name = tc.get("name", "")
            args = tc.get("args", {})
            if not isinstance(args, dict):
                args = {}
            safe = {key: args[key] for key in ("paper_id", "section", "top_k", "answer")
                    if key in args and name not in ("think",)}
            if name == "search_papers" and "query" in args:
                safe["query_sha256"] = stable_hash(str(args["query"]))
            calls.append({"turn": turn.turn, "name": name, "arguments": safe})
    return calls


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")
    tmp.replace(path)


async def run_one(sample, args, harness, config, raw_dir: Path) -> dict:
    sid = sample["id"]
    client = AgentHopBudgetClient(args.ledger, task=TASK_PREFIX + sid)
    official_call = harness.call_responses_async

    async def budgeted_call(input_data, official_config, instructions=None,
                            previous_response_id=None):
        if (official_config.model != MODEL or official_config.reasoning_effort != "medium"
                or official_config.backend != "responses"):
            raise ValueError("official harness config drift")
        payload = {"model": MODEL, "input": input_data,
            "max_output_tokens": MAX_OUTPUT,
            "tools": harness._make_responses_tools(official_config.strategy,
                                                     official_config.disabled_tools),
            "reasoning": {"effort": "medium"}}
        if instructions:
            payload["instructions"] = instructions
        if previous_response_id:
            payload["previous_response_id"] = previous_response_id
        return await client.create(**payload)

    harness.call_responses_async = budgeted_call
    try:
        trajectory = await harness.run_sample(sample, config)
        raw = asdict(trajectory)
        raw_path = raw_dir / (sid + ".json")
        write_json(raw_path, raw)
        status = ("provider_error" if trajectory.terminated_by == "error"
                  and (trajectory.api_error_count or trajectory.transient_retry_count)
                  else "completed")
        result = {"case_id": sid, "status": status, "correct": trajectory.is_correct,
            "predicted_index": trajectory.predicted_index,
            "terminated_by": trajectory.terminated_by, "turns": trajectory.total_turns,
            "api_error_count": trajectory.api_error_count,
            "transient_retry_count": trajectory.transient_retry_count,
            "budget_used": trajectory.budget_used,
            "prompt_tokens": trajectory.total_prompt_tokens,
            "completion_tokens": trajectory.total_completion_tokens,
            "tool_calls": public_tool_calls(trajectory), "raw_trace_sha256": digest(raw_path)}
    except Exception as error:
        result = {"case_id": sid, "status": "infrastructure_error",
                  "error_class": type(error).__name__, "correct": False,
                  "tool_calls": []}
    finally:
        harness.call_responses_async = official_call
        await client.close()
    return result


def summarize(args, ids: list[str]) -> dict:
    obs = []
    for sid in ids:
        path = OUT / "observations" / (sid + ".json")
        if path.exists():
            obs.append(json.loads(path.read_text()))
    after = ledger_totals(args.ledger)
    complete = len(obs) == len(ids)
    successes = sum(row.get("correct") is True for row in obs)
    campaign_charge = after["accounted_upper_usd"]
    before = json.loads((OUT / "seal.json").read_text())["shared_campaign_ledger_before"]
    return {"schema": "gac-agenthop-baseline-trace-report-v1",
        "seal_sha256": digest(OUT / "seal.json"),
        "scheduled_cases": len(ids), "recorded_cases": len(obs),
        "correct": successes, "competence_gate_minimum": COMPETENCE_SUCCESSES,
        "competence_gate_passed": complete and successes >= COMPETENCE_SUCCESSES,
        "termination_counts": {key: sum(row.get("terminated_by") == key for row in obs)
            for key in sorted({row.get("terminated_by") for row in obs if row.get("terminated_by")})},
        "provider_requests": after["agenthop_requests"] - before["agenthop_requests"],
        "campaign_accounted_upper_usd": campaign_charge,
        "pilot_increment_upper_usd": after["agenthop_accounted_upper_usd"] - before["agenthop_accounted_upper_usd"],
        "remaining_campaign_usd": 300.0 - campaign_charge,
        "provider_calls_before_study": before["requests"],
        "gac_candidates": 0, "matched_arms": 0, "calibration_groups": 0,
        "independent_test_groups": 0,
        "decision": ("INCOMPLETE_RETAIN_ALL_ATTEMPTS" if not complete else
            "BASELINE_COMPETENT_TRACE_AUDIT_REQUIRED" if successes >= COMPETENCE_SUCCESSES else
            "NO_GO_BASELINE_COMPETENCE"),
        "limitations": ["Public benchmark and internal development split",
            "Full citation neighborhoods overlap across all 478 subtype questions",
            "Competence gate is an engineering threshold, not a confidence interval",
            "No observed trace has yet been certified as a GAC candidate"],
        "observations": obs}


async def run(args) -> None:
    rows = source_check(args)
    seal_record = json.loads((OUT / "seal.json").read_text())
    if (digest(Path(__file__)) != seal_record["pilot_script_sha256"]
            or digest(ROOT / "paper/scripts/agenthop_campaign_budget.py")
            != seal_record["budget_script_sha256"]
            or selected_ids(rows) != seal_record["case_ids"]
            or digest(args.code_root / "testbed/harness.py")
            != seal_record["official_harness_sha256"]):
        raise ValueError("sealed pilot source or case list drift")
    ids = seal_record["case_ids"]
    before = ledger_totals(args.ledger)
    if before["sha256"] != seal_record["shared_campaign_ledger_before"]["sha256"]:
        raise ValueError("shared ledger changed after sealing; amend before any run")
    if any((OUT / "observations" / (sid + ".json")).exists() for sid in ids):
        raise ValueError("scheduled case already attempted; no outcome-based reruns")
    if args.env_file:
        from dotenv import load_dotenv
        load_dotenv(args.env_file)
    import os
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OpenAI key unavailable in process environment")
    sys.path.insert(0, str(args.code_root / "testbed"))
    import harness

    config = harness.HarnessConfig(model=MODEL, **CONFIG)
    samples = load_fixed_samples(args, ids, rows)
    raw_dir = args.raw_dir
    if raw_dir is None or raw_dir.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("raw trace directory must be explicitly outside this PR worktree")
    raw_dir.mkdir(parents=True, exist_ok=True)
    for sid in ids:
        result = await run_one(samples[sid], args, harness, config, raw_dir)
        write_json(OUT / "observations" / (sid + ".json"), result)
        print(json.dumps({"case_id": sid, "correct": result["correct"],
                          "status": result["status"], "calls": len(result["tool_calls"])}), flush=True)
        if result["status"] != "completed":
            break
    write_json(OUT / "report.json", summarize(args, ids))
    print(json.dumps({"decision": json.loads((OUT / "report.json").read_text())["decision"]}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("seal", "run", "summarize"))
    parser.add_argument("--qa", type=Path, required=True)
    parser.add_argument("--graphs", type=Path, required=True)
    parser.add_argument("--papers", type=Path, required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    if args.mode == "seal":
        seal(args)
    elif args.mode == "run":
        asyncio.run(run(args))
    else:
        write_json(OUT / "report.json", summarize(args,
            json.loads((OUT / "seal.json").read_text())["case_ids"]))


if __name__ == "__main__":
    main()
