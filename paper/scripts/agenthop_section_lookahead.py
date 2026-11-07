#!/usr/bin/env python3
"""Provider-free, posthoc section-lookahead audit on the sealed AgentHop pilot.

The audit inspects model-visible section listings and subsequent tool calls. It
never constructs a GAC artifact, executes an intervention, or reads gold labels.
Simple selectors are deliberately labeled posthoc diagnostics, not a holdout.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "paper/results/agenthop_baseline_trace_pilot"
OUT = ROOT / "paper/results/agenthop_section_lookahead/report.json"
SOURCE = ROOT / "paper/results/agenthop_source_feasibility/report.json"
HEADING = re.compile(r"^\s*\(([A-Z]+)\) (.+?) \((\d+) chars\)", re.MULTILINE)
WORDS = re.compile(r"[a-z]+")
STOP = frozenset("a an and the for of to in on with at by from is are do does which what how their this that using use paper study method results".split())


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def headings(output: str) -> list[tuple[str, int]]:
    """Parse only the heading lines actually visible in the official tool result."""
    return [(match.group(2).strip(), int(match.group(3)))
            for match in HEADING.finditer(output)]


def alias_index(value: str) -> int | None:
    if not re.fullmatch(r"[A-Z]{1,3}", value):
        return None
    index = 0
    for letter in value:
        index = 26 * index + ord(letter) - ord("A") + 1
    return index - 1


def visible_heading(value: str, listing: list[tuple[str, int]]) -> str | None:
    index = alias_index(value)
    if index is not None and index < len(listing):
        return listing[index][0]
    for title, _ in listing:
        if title.casefold() == value.casefold():
            return title
    return None


def tokens(value: str) -> set[str]:
    return {word for word in WORDS.findall(value.lower())
            if len(word) > 2 and word not in STOP}


def simple_selectors(listing: list[tuple[str, int]], question: str) -> dict[str, str]:
    first = listing[0][0]
    introduction = next((name for name, _ in listing
                         if name.casefold() == "introduction"), first)
    experiment = next((name for name, _ in listing
                       if re.search(r"experiment|evaluat|result", name, re.I)), first)
    longest = max(listing, key=lambda row: row[1])[0]
    lexical = max(listing, key=lambda row: (len(tokens(row[0]) & tokens(question)), row[1]))[0]
    return {"introduction": introduction, "experiment_or_first": experiment,
            "longest": longest, "question_header_overlap": lexical}


def run(qa_path: Path, raw_dir: Path) -> dict:
    seal, baseline, source = (json.loads(path.read_text()) for path in
                              (BASE / "seal.json", BASE / "report.json", SOURCE))
    if baseline["seal_sha256"] != digest(BASE / "seal.json"):
        raise ValueError("baseline seal/report drift")
    if source["source"]["sha256"]["qa/full.jsonl"] != digest(qa_path):
        raise ValueError("QA source hash drift")
    ids = seal["case_ids"]
    if not len(ids) == baseline["recorded_cases"] == 24:
        raise ValueError("case count drift")
    observed = {row["case_id"]: row for row in baseline["observations"]}
    if set(observed) != set(ids):
        raise ValueError("observation IDs drift")
    questions = {}
    with qa_path.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["id"] in observed:
                questions[row["id"]] = row["question"]
    if set(questions) != set(ids):
        raise ValueError("selected QA missing")

    transitions = []
    simple_correct = Counter()
    simple_n = 0
    raw_hashes = []
    for sid in ids:
        raw_path = raw_dir / f"{sid}.json"
        raw_hash = digest(raw_path)
        if raw_hash != observed[sid]["raw_trace_sha256"]:
            raise ValueError(f"raw trace hash drift: {sid}")
        raw_hashes.append(raw_hash)
        trace = json.loads(raw_path.read_text())
        turns = {int(row["turn"]): row for row in trace["turns"]}
        if len(turns) != len(trace["turns"]):
            raise ValueError(f"duplicate turn: {sid}")
        calls = []
        for t, turn in sorted(turns.items()):
            for call in turn["tool_calls"]:
                name, args = call["name"], call["args"]
                safe = {key: args[key] for key in
                        ("paper_id", "section", "top_k", "answer")
                        if key in args and name != "think"}
                if name == "search_papers" and "query" in args:
                    safe["query_sha256"] = hashlib.sha256(
                        str(args["query"]).encode()).hexdigest()
                calls.append({"turn": t, "name": name, "arguments": safe})
        if calls != observed[sid]["tool_calls"]:
            raise ValueError(f"public/raw tool call mismatch: {sid}")
        for t, current in sorted(turns.items()):
            following = turns.get(t + 1)
            if following is None:
                continue
            lists = [row for row in current["tool_results"]
                     if row["name"] == "list_sections"]
            if not lists:
                continue
            listed = {row["args"]["paper_id"]: headings(row["output"]) for row in lists}
            next_calls = following["tool_calls"]
            reads = [row for row in next_calls if row["name"] == "read_section"
                     and row["args"].get("paper_id") in listed]
            if not reads:
                continue
            visible = sum(visible_heading(row["args"]["section"],
                            listed[row["args"]["paper_id"]]) is not None for row in reads)
            exact_next_batch = len(reads) == len(next_calls)
            transitions.append({"case_id": sid, "turn": t,
                "listed_papers": len(listed), "next_calls": len(next_calls),
                "next_same_paper_reads": len(reads),
                "visible_targets": visible, "exact_next_batch": exact_next_batch})
            # This narrow diagnostic gives each simple rule the same single
            # model-selected paper. It does not simulate a deployable policy.
            if len(listed) == len(next_calls) == len(reads) == 1 and visible == 1:
                listing = next(iter(listed.values()))
                target = visible_heading(reads[0]["args"]["section"], listing)
                if target is None:
                    raise ValueError("visible target lost")
                simple_n += 1
                for name, choice in simple_selectors(listing, questions[sid]).items():
                    simple_correct[name] += choice.casefold() == target.casefold()
    return {"schema": "gac-agenthop-section-lookahead-v1",
        "scope": "posthoc developmental timing and simple-selector diagnostic",
        "analysis_source_sha256": digest(Path(__file__)),
        "seal_sha256": digest(BASE / "seal.json"),
        "baseline_report_sha256": digest(BASE / "report.json"),
        "source_audit_sha256": digest(SOURCE),
        "qa_sha256": digest(qa_path), "raw_trace_hashes_verified": len(raw_hashes),
        "scheduled_cases": len(ids), "transition_count": len(transitions),
        "cases_with_transition": len({row["case_id"] for row in transitions}),
        "exact_next_batch_count": sum(row["exact_next_batch"] for row in transitions),
        "visible_target_count": sum(row["visible_targets"] for row in transitions),
        "target_count": sum(row["next_same_paper_reads"] for row in transitions),
        "simple_selector_subset": simple_n,
        "simple_selector_matches": dict(sorted(simple_correct.items())),
        "provider_calls": 0, "gac_candidates": 0, "matched_arms": 0,
        "decision": "TIMING_OPPORTUNITY_ONLY_NO_DERIVED_SELECTOR_OR_MATCHED_GAC_RUN",
        "limitations": [
            "Observed next-turn behavior is an oracle timing upper bound, not a prospective intervention or request saving.",
            "Simple selector rules and their diagnostic subset were inspected posthoc; the model-selected paper is held fixed and the result is not deployable or held out.",
            "A synthetic continuation may differ even if the prefetched tool outputs match.",
            "The 24 public cases share a source-connected corpus and cannot support a source-independent superiority claim."],
        "transitions": transitions}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qa", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.qa, args.raw_dir)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in
        ("transition_count", "exact_next_batch_count", "simple_selector_subset",
         "simple_selector_matches", "decision")}, sort_keys=True))


if __name__ == "__main__":
    main()
