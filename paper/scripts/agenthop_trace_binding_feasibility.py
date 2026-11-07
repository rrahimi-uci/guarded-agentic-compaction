#!/usr/bin/env python3
"""Provider-free posthoc binding audit of every sealed AgentHop baseline trace.

Uses only model-visible question/options, the entry seed, official tool output
and model-selected paper IDs for candidate synthesis. Gold/bridge IDs and
correct answers are used by the separate grader audit, never here.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

from agenthop_baseline_trace_pilot import OUT, ROOT
from agenthop_source_feasibility import build as source_build, digest
from guarded_agentic_compaction.grc.dsl import SynthContext
from guarded_agentic_compaction.grc.synthesize import synthesize_binding


def synthesis(envs: list[dict], targets: list[str], groups: list[str]) -> dict:
    if len(envs) < 5:
        return {"support": len(envs), "attempted": False, "reason": "support_below_five"}
    ctx = SynthContext.from_observations([*envs, *targets], max_depth=2)
    result = synthesize_binding("paper_id", envs, targets, groups,
                                ctx=ctx, max_sources=40)
    return {"support": len(envs), "attempted": True, "binding_found": result.ok,
            "binding": result.binding.to_dict() if result.binding else None,
            "reason": result.reason,
            "ambiguous_alternatives": result.ambiguous_alternatives,
            "search_cache_misses": ctx.cache_misses}


def run(args) -> dict:
    source_build(args.qa, args.graphs, args.papers, args.code_root)
    seal = json.loads((OUT / "seal.json").read_text())
    report = json.loads((OUT / "report.json").read_text())
    grade_audit = json.loads((OUT / "audit.json").read_text())
    if (report["seal_sha256"] != digest(OUT / "seal.json")
            or grade_audit["report_sha256"] != digest(OUT / "report.json")
            or report["recorded_cases"] != seal["scheduled_cases"] != 24):
        raise ValueError("pilot or grade audit drift")
    observed = {row["case_id"]: row for row in report["observations"]}
    qa = {}
    with args.qa.open(encoding="utf-8") as source:
        for line in source:
            row = json.loads(line)
            if row["id"] in observed:
                qa[row["id"]] = {key: row[key] for key in
                    ("id", "seed_paper_id", "question", "options")}
    graphs = {}
    with args.graphs.open(encoding="utf-8") as source:
        for line in source:
            graph = json.loads(line)
            if graph["sample_id"] in observed:
                graphs[graph["sample_id"]] = graph
    pool_ids = {paper["arxiv_id"] for paper in
        (json.loads(line) for line in args.papers.open(encoding="utf-8"))}
    if set(observed) != set(qa) or set(observed) != set(graphs):
        raise ValueError("missing source for fixed pilot case")
    sys.path.insert(0, str(args.code_root / "testbed"))
    from tools import AgentHopTools

    rows = []
    families: dict[tuple[str, ...], list[tuple[dict, dict, str, str]]] = defaultdict(list)
    exact_envs, typed_envs, targets, groups = [], [], [], []
    for sid in seal["case_ids"]:
        row, graph, case = qa[sid], graphs[sid], observed[sid]
        seed = row["seed_paper_id"]
        calls = [call for call in case["tool_calls"]
                 if call["name"] not in ("think", "submit_answer")]
        first_turn = tuple(call["name"] for call in calls if call["turn"] == 0)
        if not (first_turn[:2] == ("get_paper_info", "get_references")
                or first_turn == ("get_paper_info", "list_sections", "get_references")):
            raise ValueError("opening batch changed")
        seed_refs = next((call for call in calls if call["name"] == "get_references"
                          and call["arguments"].get("paper_id") == seed), None)
        child = next((call for call in calls if call["arguments"].get("paper_id")
                      and call["arguments"]["paper_id"] != seed), None)
        if seed_refs is None or child is None or seed_refs["turn"] >= child["turn"]:
            raise ValueError("no prior seed references before first non-seed read")
        child_id = child["arguments"]["paper_id"]
        refs = graph["edges"].get(seed, [])
        source_relation = "seed_reference" if child_id in refs else "other_route"
        rank = refs.index(child_id) + 1 if child_id in refs else None
        following = [call for call in calls[calls.index(child) + 1:]
                     if call["arguments"].get("paper_id") == child_id]
        followup = ("none" if not following else
                    "same_turn" if following[0]["turn"] == child["turn"] else "later_turn")
        parity = None
        if source_relation == "seed_reference":
            available = {node["arxivId"]: {} for node in graph["nodes"].values()
                         if node.get("arxivId") in pool_ids}
            tool = AgentHopTools({"graph": {"nodes": graph["nodes"],
                "edges": graph["edges"]}, "paper_pool": available})
            output = tool.get_references(seed)
            raw_path = args.raw_dir / (sid + ".json")
            if digest(raw_path) != case["raw_trace_sha256"]:
                raise ValueError("protected raw trace hash changed")
            raw = json.loads(raw_path.read_text())
            recorded = next((result["output"] for turn in raw["turns"]
                for result in turn["tool_results"] if result["name"] == "get_references"
                and result["args"].get("paper_id") == seed), None)
            parity = recorded == (output[:500] + "..." if len(output) > 500 else output)
            if not parity:
                raise ValueError("official seed-reference output does not match retained trace")
            entry = {"seed_paper_id": seed, "question": row["question"],
                     "options": row["options"]}
            exact = {"entry": entry, "z0": {"reference_text": output}}
            typed = {"entry": entry, "z0": {"references": [
                {"paper_id": paper_id,
                 "title": graph["nodes"].get(paper_id, {}).get("title", "")}
                for paper_id in refs]}}
            exact_envs.append(exact)
            typed_envs.append(typed)
            targets.append(child_id)
            groups.append(sid)
            families[first_turn].append((exact, typed, child_id, sid))
        rows.append({"case_id": sid, "opening_batch": list(first_turn),
            "seed_reference_count": len(refs), "first_nonseed_tool": child["name"],
            "first_nonseed_relation": source_relation, "first_nonseed_reference_rank": rank,
            "seed_reference_turn": seed_refs["turn"], "first_nonseed_turn": child["turn"],
            "first_nonseed_followup": followup,
            "official_reference_output_prefix_equal": parity})
    by_family = []
    for names, group in sorted(families.items()):
        by_family.append({"opening_batch": list(names), "support": len(group),
            "exact_text": synthesis([x[0] for x in group], [x[2] for x in group],
                                    [x[3] for x in group]),
            "typed_sensitivity": synthesis([x[1] for x in group], [x[2] for x in group],
                                           [x[3] for x in group])})
    exact_result = synthesis(exact_envs, targets, groups)
    typed_result = synthesis(typed_envs, targets, groups)
    any_binding = exact_result.get("binding_found") or any(
        family["exact_text"].get("binding_found") for family in by_family)
    return {"schema": "gac-agenthop-trace-binding-feasibility-v1",
        "scope": "posthoc developmental first-nonseed reference-binding diagnostic; not an exhaustive compiler search",
        "provider_calls": 0, "gac_artifacts_admitted": 0,
        "seal_sha256": digest(OUT / "seal.json"),
        "baseline_report_sha256": digest(OUT / "report.json"),
        "grade_audit_sha256": digest(OUT / "audit.json"),
        "analysis_source_sha256": digest(Path(__file__)),
        "scheduled_cases": len(seal["case_ids"]), "analyzed_cases": len(rows),
        "opening_calls_already_batched": sum(len(row["opening_batch"]) >= 2 for row in rows),
        "initial_three_call_batches": sum(len(row["opening_batch"]) == 3 for row in rows),
        "first_child_from_seed_references": sum(row["first_nonseed_relation"] == "seed_reference" for row in rows),
        "first_child_other_route": sum(row["first_nonseed_relation"] == "other_route" for row in rows),
        "first_child_reference_rank_range": [min(row["first_nonseed_reference_rank"] for row in rows
            if row["first_nonseed_reference_rank"] is not None),
            max(row["first_nonseed_reference_rank"] for row in rows
            if row["first_nonseed_reference_rank"] is not None)],
        "first_child_followup": dict(Counter(row["first_nonseed_followup"] for row in rows)),
        "official_reference_output_prefix_parity": sum(row["official_reference_output_prefix_equal"] is True
            for row in rows),
        "exact_text_binding": exact_result,
        "typed_reference_sensitivity": typed_result,
        "opening_batch_families": by_family,
        "decision": "RESEARCH_BINDING_FOUND_NEEDS_LIVE_AND_MATCHED_CHECKS" if any_binding
            else "NO_QUALIFYING_BINDING_IN_TESTED_FAMILIES_NO_MATCHED_GAC_RUN",
        "limitations": [
            "The first-nonseed reference family and opening-batch subfamilies are a posthoc development diagnostic, not an exhaustive search of all later tool patterns.",
            "The typed-reference sensitivity changes the official text output representation and is not deployable without a matched runtime port.",
            "No consistent binding result cannot establish that every possible future selector or compiler will fail.",
            "The opening seed reads were already batched by the unchanged agent, so their recurrence alone cannot save a provider turn.",
            "No final-answer GAC arm, handwritten arm, calibration or independent test was run."],
        "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qa", type=Path, required=True)
    parser.add_argument("--graphs", type=Path, required=True)
    parser.add_argument("--papers", type=Path, required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    args = parser.parse_args()
    record = run(args)
    (OUT / "binding_feasibility.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: record[key] for key in ("decision", "scheduled_cases",
        "first_child_from_seed_references", "opening_calls_already_batched")}, sort_keys=True))


if __name__ == "__main__":
    main()
