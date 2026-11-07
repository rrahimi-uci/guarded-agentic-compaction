#!/usr/bin/env python3
"""Provider-free exact-grader, budget and raw-trace audit of the sealed pilot."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path

from agenthop_baseline_trace_pilot import (
    COMPETENCE_SUCCESSES, OUT, ROOT, ledger_totals, read_qa, selected_ids,
)
from agenthop_campaign_budget import (
    INPUT_UPPER, MODEL, OUTPUT_UPPER, TASK_PREFIX,
)
from agenthop_source_feasibility import build as source_build, digest


def audit(args) -> dict:
    source_build(args.qa, args.graphs, args.papers, args.code_root)
    seal = json.loads((OUT / "seal.json").read_text())
    report = json.loads((OUT / "report.json").read_text())
    rows = {row["id"]: row for row in read_qa(args.qa)}
    ids = seal["case_ids"]
    if (ids != selected_ids(list(rows.values())) or len(set(ids)) != 24
            or report["seal_sha256"] != digest(OUT / "seal.json")
            or seal["pilot_script_sha256"] != digest(ROOT / "paper/scripts/agenthop_baseline_trace_pilot.py")
            or seal["budget_script_sha256"] != digest(ROOT / "paper/scripts/agenthop_campaign_budget.py")):
        raise ValueError("cohort, seal or code drift")
    observations = report["observations"]
    if ([row["case_id"] for row in observations] != ids[:len(observations)]
            or len(observations) != report["recorded_cases"]):
        raise ValueError("missing or reordered fixed observations")
    scored = []
    raw_verified = 0
    for observed in observations:
        sid = observed["case_id"]
        on_disk = json.loads((OUT / "observations" / (sid + ".json")).read_text())
        if observed != on_disk:
            raise ValueError(f"published observation differs from retained case {sid}")
        gold_index = rows[sid]["correct_index"]
        predicted = observed.get("predicted_index", -1)
        correct = observed["status"] == "completed" and predicted == gold_index
        if observed["correct"] != correct:
            raise ValueError(f"official answer check mismatch {sid}")
        if "raw_trace_sha256" in observed:
            raw_path = args.raw_dir / (sid + ".json")
            if not raw_path.exists() or digest(raw_path) != observed["raw_trace_sha256"]:
                raise ValueError(f"missing or altered protected raw trace {sid}")
            raw_verified += 1
        elif observed["status"] != "infrastructure_error":
            raise ValueError(f"unexpected missing raw trace {sid}")
        scored.append({"case_id": sid, "correct_index": gold_index,
                       "predicted_index": predicted, "correct": correct,
                       "terminated_by": observed.get("terminated_by"),
                       "status": observed["status"]})
    total_correct = sum(row["correct"] for row in scored)
    if (total_correct != report["correct"]
            or (len(observations) == len(ids) and total_correct >= COMPETENCE_SUCCESSES)
            != report["competence_gate_passed"]):
        raise ValueError("aggregate competence check mismatch")

    ledger = json.loads(args.ledger.read_text())
    study_rows = [row for row in ledger["requests"] if row["task"].startswith(TASK_PREFIX)]
    if (len(study_rows) != report["provider_requests"]
            or any(row["stage"] != "pilot" or row["arm"] != "baseline"
                   or row["model"] != MODEL for row in study_rows)
            or any(row["status"] == "reserved" or row["status"].endswith("_STOP")
                   for row in study_rows)):
        raise ValueError("ledger request population or status mismatch")
    charged = math.fsum(row.get("accounted_upper_usd", row["reserved_usd"]) for row in study_rows)
    if abs(charged - report["pilot_increment_upper_usd"]) > 1e-9:
        raise ValueError("study cost mismatch")
    for row in study_rows:
        usage = row.get("usage")
        if usage:
            expected = (usage["input_tokens"] * INPUT_UPPER
                        + usage["output_tokens"] * OUTPUT_UPPER) / 1e6
            if abs(row["accounted_upper_usd"] - expected) > 1e-9:
                raise ValueError("request cost mismatch")
    if abs(ledger_totals(args.ledger)["accounted_upper_usd"]
           - report["campaign_accounted_upper_usd"]) > 1e-9:
        raise ValueError("campaign cost mismatch")
    ledger_snapshot = {"schema": "gac-agenthop-baseline-ledger-snapshot-v1",
        "source_ledger_sha256": digest(args.ledger),
        "campaign_accounted_upper_usd": ledger["accounted_upper_usd"],
        "campaign_cap_usd": ledger["cap_usd"],
        "stage_caps": ledger["stage_caps"],
        "study_requests": study_rows}
    snapshot_path = OUT / "ledger_snapshot.json"
    snapshot_path.write_text(json.dumps(ledger_snapshot, indent=2, sort_keys=True) + "\n")

    navigation = []
    for observed in observations:
        names = tuple(call["name"] for call in observed["tool_calls"]
                      if call["name"] not in ("think", "submit_answer"))
        navigation.append(names)
    two_call = Counter(names[:2] for names in navigation if len(names) >= 2)
    three_call = Counter(names[:3] for names in navigation if len(names) >= 3)
    return {"schema": "gac-agenthop-baseline-trace-audit-v1",
        "decision": report["decision"], "seal_sha256": digest(OUT / "seal.json"),
        "report_sha256": digest(OUT / "report.json"),
        "qa_sha256": digest(args.qa), "ledger_sha256": digest(args.ledger),
        "ledger_snapshot_sha256": digest(snapshot_path),
        "scheduled_cases": len(ids), "grade_audited_cases": len(scored),
        "raw_trace_hashes_verified": raw_verified,
        "correct": total_correct,
        "competence_gate_passed": report["competence_gate_passed"],
        "provider_requests": len(study_rows),
        "study_accounted_upper_usd": charged,
        "two_call_name_prefixes": [{"names": list(names), "cases": count}
            for names, count in sorted(two_call.items(), key=lambda item: (-item[1], item[0]))],
        "three_call_name_prefixes": [{"names": list(names), "cases": count}
            for names, count in sorted(three_call.items(), key=lambda item: (-item[1], item[0]))],
        "prefix_warning": "Name recurrence does not prove dynamic argument grounding, a unique selector, safe effects or a useful GAC candidate",
        "gac_candidates_admitted": 0,
        "graded_cases": scored}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qa", type=Path, required=True)
    parser.add_argument("--graphs", type=Path, required=True)
    parser.add_argument("--papers", type=Path, required=True)
    parser.add_argument("--code-root", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args)
    (OUT / "audit.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in ("decision", "correct",
        "scheduled_cases", "provider_requests", "study_accounted_upper_usd")}, sort_keys=True))


if __name__ == "__main__":
    main()
