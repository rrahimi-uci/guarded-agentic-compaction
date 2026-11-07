#!/usr/bin/env python3
"""Posthoc grouped ranker diagnostic for visible AgentHop section choices.

This is an optimistic development probe, not a GAC selector: eligibility uses
observed next-turn calls, and oracle-k evaluation supplies the true read count.
Every fold excludes all turns from its held-out case. No gold answers are used.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path

from sklearn import __version__ as sklearn_version
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression

from agenthop_section_lookahead import BASE, OUT as TIMING_OUT, digest, headings, run as timing_run, tokens, visible_heading

OUT = TIMING_OUT.with_name("ranker_probe.json")


def features(name: str, length: int, index: int, count: int, question: str) -> dict:
    title_tokens, question_tokens = tokens(name), tokens(question)
    lower = name.lower()
    row = {"index": index / max(count - 1, 1), "length": math.log1p(length),
           "number_of_headings": count,
           "question_overlap": len(title_tokens & question_tokens),
           "question_overlap_ratio": len(title_tokens & question_tokens) / max(len(title_tokens), 1),
           "intro": int("intro" in lower), "experiment": int("experiment" in lower),
           "evaluation": int("evaluat" in lower), "result": int("result" in lower),
           "related": int("related" in lower),
           "method": int("method" in lower or "approach" in lower),
           "appendix": int("apdx" in lower or "appendix" in lower),
           "background": int("background" in lower),
           "conclusion": int("conclusion" in lower)}
    row.update({"heading:" + token: 1 for token in title_tokens})
    return row


def units(qa_path: Path, raw_dir: Path) -> list[dict]:
    qa = {row["id"]: row for row in
          (json.loads(line) for line in qa_path.open(encoding="utf-8"))}
    baseline = json.loads((BASE / "report.json").read_text())
    selected = baseline["observations"]
    output = []
    for observation in selected:
        sid = observation["case_id"]
        raw_path = raw_dir / f"{sid}.json"
        if digest(raw_path) != observation["raw_trace_sha256"]:
            raise ValueError(f"raw trace hash drift: {sid}")
        raw = json.loads(raw_path.read_text())
        turns = {int(turn["turn"]): turn for turn in raw["turns"]}
        for t, current in turns.items():
            following = turns.get(t + 1)
            if following is None:
                continue
            lists = [result for result in current["tool_results"]
                     if result["name"] == "list_sections"]
            if len(lists) != 1:
                continue
            listing = headings(lists[0]["output"])
            paper_id = lists[0]["args"]["paper_id"]
            calls = following["tool_calls"]
            reads = [call for call in calls if call["name"] == "read_section"
                     and call["args"].get("paper_id") == paper_id]
            if not reads or len(reads) != len(calls):
                continue
            target = {visible_heading(call["args"]["section"], listing)
                      for call in reads}
            if None in target or len(target) != len(reads):
                continue
            output.append({"case_id": sid, "turn": t, "target_count": len(target),
                "features": [features(name, length, i, len(listing), qa[sid]["question"])
                             for i, (name, length) in enumerate(listing)],
                "labels": [int(name in target) for name, _ in listing]})
    return output


def run(qa_path: Path, raw_dir: Path) -> dict:
    timing = timing_run(qa_path, raw_dir)
    if timing != json.loads(TIMING_OUT.read_text()):
        raise ValueError("timing report drift")
    cohort = units(qa_path, raw_dir)
    if len(cohort) < 2 or len({row["case_id"] for row in cohort}) < 2:
        raise ValueError("insufficient grouped development cases")
    scored = []
    for heldout in cohort:
        train = [row for row in cohort if row["case_id"] != heldout["case_id"]]
        train_features = [feature for row in train for feature in row["features"]]
        train_labels = [label for row in train for label in row["labels"]]
        vectorizer = DictVectorizer()
        model = LogisticRegression(max_iter=2000, class_weight="balanced",
                                   C=0.3, solver="lbfgs", random_state=0)
        model.fit(vectorizer.fit_transform(train_features), train_labels)
        scores = model.predict_proba(vectorizer.transform(heldout["features"]))[:, 1]
        ranking = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
        actual = {i for i, label in enumerate(heldout["labels"]) if label}
        outcome = {"case_id": heldout["case_id"], "turn": heldout["turn"],
                   "target_count": heldout["target_count"],
                   "candidate_headings": len(heldout["labels"])}
        for name, count in (("top1", 1), ("top2", 2),
                            ("oracle_k", heldout["target_count"])):
            predicted = set(ranking[:count])
            outcome[name + "_exact"] = predicted == actual
            outcome[name + "_hits"] = len(predicted & actual)
        scored.append(outcome)
    return {"schema": "gac-agenthop-section-ranker-probe-v1",
        "scope": "posthoc grouped developmental diagnostic on outcome-selected visible-read subset",
        "analysis_source_sha256": digest(Path(__file__)),
        "timing_report_sha256": digest(TIMING_OUT),
        "qa_sha256": digest(qa_path), "sklearn_version": sklearn_version,
        "fold_rule": "leave one case ID out; all turns from that case excluded from training",
        "classifier": "DictVectorizer plus balanced LogisticRegression(C=0.3, solver=lbfgs, random_state=0)",
        "scheduled_baseline_cases": len(json.loads((BASE / "seal.json").read_text())["case_ids"]),
        "eligible_transitions": len(scored),
        "case_groups": len({row["case_id"] for row in scored}),
        "target_count_distribution": dict(sorted(Counter(row["target_count"] for row in scored).items())),
        "top1_exact": sum(row["top1_exact"] for row in scored),
        "top2_exact": sum(row["top2_exact"] for row in scored),
        "oracle_k_exact": sum(row["oracle_k_exact"] for row in scored),
        "oracle_k_hits": sum(row["oracle_k_hits"] for row in scored),
        "target_reads": sum(row["target_count"] for row in scored),
        "provider_calls": 0, "gac_candidates": 0, "matched_arms": 0,
        "decision": "EXPLORATORY_RANKER_TOO_WEAK_NO_PAID_MATCHED_ARM",
        "limitations": [
            "Features, regularization and subset were chosen after exposure to this development cohort; leave-one-case-out is not an independent confirmatory test.",
            "Eligibility uses observed future tool calls and excludes unlisted or mixed next batches.",
            "Oracle-k scoring supplies the true number of future reads, which a deployable selector would not know.",
            "The model-selected paper is supplied; selecting that paper is a separate unsolved binding problem.",
            "Matching model tool calls is a surrogate; final-answer quality, cost, continuation parity and source-independent generalization were not measured."],
        "folds": scored}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qa", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.qa, args.raw_dir)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in
        ("eligible_transitions", "case_groups", "top1_exact", "top2_exact",
         "oracle_k_exact", "oracle_k_hits", "target_reads", "decision")}, sort_keys=True))


if __name__ == "__main__":
    main()
