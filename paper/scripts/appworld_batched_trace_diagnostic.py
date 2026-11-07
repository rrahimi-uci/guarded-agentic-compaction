"""Posthoc, aggregate-only diagnosis of the sealed AppWorld competence traces.

This script reads protected local records, verifies their published hashes, and
emits counts only. It never prints task text, API arguments/results, task IDs,
credentials, reference calls or provider messages. It does not create a new
candidate, grader result or confirmatory estimate.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from appworld_batched_competence import model_view

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "paper/results"
VERSIONS = ("appworld_batched_competence", "appworld_batched_competence_v2")
OUT = PUBLIC / "appworld_batched_competence/trace_diagnostic.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def version_summary(cache_root, version, name):
    public = PUBLIC / name
    seal, report = load(public / "seal.json"), load(public / "report.json")
    protected_hashes = {row["path"]: row["sha256"]
                        for row in report["protected_raw_files"]}
    if len(seal["tasks"]) != 12 or report["scheduled"] != 12:
        raise ValueError("unexpected cohort size")
    if digest(ROOT / "paper/scripts/appworld_batched_competence.py") != (
            seal["source_hashes"]["paper/scripts/appworld_batched_competence.py"]):
        raise ValueError("model view source changed")
    rows = []
    for task in seal["tasks"]:
        path = cache_root / version / "episodes" / task / "record.json"
        key = str(path.relative_to(cache_root / version))
        if protected_hashes.get(key) != digest(path):
            raise ValueError("episode differs from published protected-file hash")
        row = load(path)
        if row.get("task_id") != task or row.get("status") != "completed":
            raise ValueError("missing fixed completed attempt")
        rows.append(row)
    if (sum(bool(row["evaluation"]["success"]) for row in rows)
            != report["official_successes"]
            or sum(len(row["provider_trace"]) for row in rows)
            != report["model_requests"]
            or sum(row["api_calls"] for row in rows) != report["api_calls"]):
        raise ValueError("episode totals differ from public report")

    prefixes = Counter()
    first = Counter()
    truncated = 0
    cases_truncated = 0
    batches = 0
    invalid_batches = 0
    api_errors = 0
    complete_cases = 0
    complete_attempts = 0
    elided = 0
    cases_elided = 0
    terminations = Counter()
    for row in rows:
        seq = []
        case_trunc = 0
        case_complete = 0
        for batch in row["batches"]:
            batches += 1
            invalid_batches += bool(batch.get("error"))
            for call in batch.get("calls", []):
                app, api = call.get("app"), call.get("api")
                if app not in {"api_docs", "supervisor"}:
                    seq.append((app, api))
                case_complete += (app, api) == ("supervisor", "complete_task")
                api_errors += isinstance(call.get("result"), dict) and "error" in call["result"]
            view = model_view(batch)
            case_trunc += sum(isinstance(call.get("result"), dict)
                              and bool(call["result"].get("model_view_truncated"))
                              for call in view.get("calls", []))
        if seq:
            first[seq[0]] += 1
        if len(seq) >= 2:
            prefixes[tuple(seq[:2])] += 1
        truncated += case_trunc
        cases_truncated += case_trunc > 0
        complete_cases += case_complete > 0
        complete_attempts += case_complete
        elided += max(0, len(row["batches"]) - 2)
        cases_elided += len(row["batches"]) > 2
        terminations[row.get("termination", "missing")] += 1

    return ({"version": version, "seal_sha256": digest(public / "seal.json"),
             "report_sha256": digest(public / "report.json"),
             "verified_episode_hashes": len(rows),
             "official_successes": report["official_successes"],
             "model_requests": report["model_requests"], "api_calls": report["api_calls"],
             "batch_messages": batches, "invalid_batch_messages": invalid_batches,
             "api_error_results": api_errors,
             "cases_with_complete_task": complete_cases,
             "complete_task_attempts": complete_attempts,
             "cases_with_truncated_result_view": cases_truncated,
             "truncated_result_views": truncated,
             "cases_with_older_batch_views_elided": cases_elided,
             "older_batch_views_elided_at_final_model_call": elided,
             "first_non_docs_api_name_max_frequency": max(first.values(), default=0),
             "two_non_docs_api_name_repeat_groups": sum(n >= 2 for n in prefixes.values()),
             "cases_in_repeated_two_api_name_groups": sum(n for n in prefixes.values() if n >= 2),
             "terminations": dict(sorted(terminations.items()))},
            {row["task_id"] for row in rows if row["evaluation"]["success"]})


def build(cache_root):
    versions = []
    successes = []
    for version, name in zip(("v1", "v2"), VERSIONS, strict=True):
        result, success = version_summary(cache_root, version, name)
        versions.append(result)
        successes.append(success)
    return {"schema": "gac-appworld-batched-posthoc-trace-diagnostic-v1",
            "status": "exploratory diagnosis of exposed development cases; no candidate admission or causal attribution",
            "source_sha256": digest(Path(__file__)),
            "versions": versions,
            "cross_version_success_overlap": len(successes[0] & successes[1]),
            "reference_calls_read": False,
            "model_calls_made": 0,
            "gac_runs": 0,
            "interpretation": "API-name prefix repetition is only a surface diagnostic. It does not establish matched arguments, read-only effects, a grounded compiled region, final quality, or savings. Truncation and history elision counts describe the interface, not the cause of failures."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-root", type=Path, default=ROOT / "benchmarks/.cache/appworld_batched_competence")
    args = parser.parse_args()
    result = build(args.cache_root)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"versions": [(r["version"], r["official_successes"])
                                   for r in result["versions"]],
                      "model_calls_made": result["model_calls_made"]}))
