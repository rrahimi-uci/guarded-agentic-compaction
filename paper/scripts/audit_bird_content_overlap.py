"""Identify exact question-text overlap beyond historical numeric ID screening."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def overlap(questions, used):
    groups = defaultdict(list)
    for index, q in enumerate(questions):
        # Same database and whitespace-normalized question. Evidence/SQL can
        # differ: this is conservative inspection overlap, not semantic identity.
        key = (q["db_id"], " ".join(q["question"].split()))
        groups[key].append(q.get("question_id", index))
    duplicate_groups = []
    affected = set()
    for (db, question), ids in sorted(groups.items()):
        if len(ids) > 1:
            prior = sorted(set(ids) & used)
            remaining = sorted(set(ids) - used)
            if prior:
                affected.update(remaining)
            duplicate_groups.append({"db_id": db,
                "normalized_question_sha256": hashlib.sha256(question.encode()).hexdigest(),
                "prior_ids": prior, "screened_in_ids": remaining})
    return {"duplicate_question_groups": duplicate_groups,
            "screened_in_ids_matching_prior_question": sorted(affected)}


def build():
    path = ROOT / "paper/results/calibration_population_audit/bird_source_screen.json"
    screen = json.loads(path.read_text())
    report = {"schema": "gac-bird-content-overlap-v1", "provider_calls": 0, "splits": {},
        "source_hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (path, Path(__file__).resolve())},
        "scope": "Exact within-database whitespace-normalized question text across IDs; no semantic paraphrase or model-training audit."}
    for split in screen["splits"]:
        source = ROOT / split["question_file"]
        if hashlib.sha256(source.read_bytes()).hexdigest() != split["question_sha256"]:
            raise ValueError("source changed")
        report["source_hashes"][split["question_file"]] = split["question_sha256"]
        report["splits"][split["split"]] = overlap(json.loads(source.read_text()), set(split["screened_ids"]))
    out = ROOT / "paper/results/adaptive_comparison_preflight/content_overlap.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    for split, rows in report["splits"].items():
        print(split, rows["screened_in_ids_matching_prior_question"])


if __name__ == "__main__":
    build()
