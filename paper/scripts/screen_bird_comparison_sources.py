"""Count remaining BIRD records after a conservative retained-study screen.

No model/SQL calls, downloads, source mutation, or claim of a sealed fresh cohort.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/results/calibration_population_audit/bird_source_screen.json"


def ids_in(value):
    result = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"question_id", "issue_number"} and type(child) is int:
                result.add(child)
            elif key in {"discovery", "test"} and isinstance(child, list):
                result.update(x for x in child if type(x) is int)
            result.update(ids_in(child))
    elif isinstance(value, list):
        for child in value:
            result.update(ids_in(child))
    return result


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build():
    cache = ROOT / "benchmarks/.cache/bird"
    root = ROOT / "paper/results/bird"
    sources = {}
    used = {"dev": set(), "train": set()}
    for path in sorted(root.rglob("*.json")):
        split = "train" if path.relative_to(root).parts[0] == "train" else "dev"
        data = path.read_bytes()
        used[split].update(ids_in(json.loads(data)))
        sources[str(path.relative_to(ROOT))] = sha(data)
    rows = []
    for split, directory in (("dev", "dev_20240627"), ("train", "train")):
        path = cache / "extract" / directory / f"{split}.json"
        data = path.read_bytes()
        # Compare the question bytes to the local archive entry. This does not
        # rehash the entire multi-gigabyte archive or validate every database.
        with zipfile.ZipFile(cache / f"{split}.zip") as archive:
            names = [n for n in archive.namelist() if n.split("/")[-1] == f"{split}.json"]
            if len(names) != 1 or archive.read(names[0]) != data:
                raise ValueError(f"question bytes differ from local archive: {split}")
        questions = json.loads(data)
        counts = Counter(q["db_id"] for q in questions)
        remaining = Counter(q["db_id"] for i, q in enumerate(questions)
                            if q.get("question_id", i) not in used[split])
        known = {q.get("question_id", i) for i, q in enumerate(questions)}
        if len(known) != len(questions):
            raise ValueError("duplicate question IDs")
        rows.append({"split": split, "question_file": str(path.relative_to(ROOT)),
                     "question_sha256": sha(data), "matches_local_archive_entry": True,
                     "total": len(questions), "screened_out": len(known & used[split]),
                     "remaining": sum(remaining.values()),
                     "unknown_referenced_ids": sorted(used[split] - known),
                     "screened_ids": sorted(known & used[split]),
                     "databases": [{"db_id": db, "total": counts[db], "remaining": remaining[db]}
                                   for db in sorted(counts)]})
    report = {"schema": "gac-bird-source-screen-v1", "provider_calls": 0,
              "decision": "NOT_READY_FOR_CONFIRMATORY_EXECUTION", "splits": rows,
              "source_hashes": sources,
              "scope": "All JSON under paper/results/bird, including predeclared selections and failed attempts; train/dev IDs separate.",
              "limitations": ["Remaining counts are not certified fresh, independent, or grader-valid groups.",
                              "No full archive rehash, database integrity audit, gold execution, or global prior-inspection audit performed.",
                              "No question text or gold outcomes inspected for candidate/task selection.",
                              "No compiler comparator adapter, candidate diversity, power choice, execution seal, or spending cap established."]}
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    for row in rows:
        maximum = max(row["databases"], key=lambda d: d["remaining"])
        print(row["split"], "total", row["total"], "remaining", row["remaining"], "largest remaining database", maximum)


if __name__ == "__main__":
    build()
