"""Compare the pinned old dev questions with the official corrected release.

No model calls, semantic judgments, or automatic replacement of old results.
The separately acquired snapshot is optional; retained metadata is CI-readable.
"""
import hashlib
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from adaptive_sql_grader import execute
from adaptive_source_preflight import digest

ROOT = Path(__file__).resolve().parents[2]
REVISION = "3c11fb193e5439b338e23677fa0aae11e8b85db9"
SNAPSHOT_SHA256 = "ffd8018378ddb1a8794753e0a31cfc81862ff7318a5184c22f3dc4ce03a03feb"
URL = f"https://huggingface.co/datasets/birdsql/bird_sql_dev_20251106/resolve/{REVISION}/data/dev_20251106-00000-of-00001.json"
FIELDS = ("db_id", "question", "evidence", "SQL", "difficulty")


def read_corrected(path):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != SNAPSHOT_SHA256:
        raise ValueError("corrected release snapshot checksum mismatch")
    text = data.decode()
    return json.loads(text) if text.lstrip().startswith("[") else [json.loads(line) for line in text.splitlines() if line.strip()]


def changes(old, new, previously_used):
    def index(rows):
        result = {r["question_id"]: r for r in rows}
        if len(result) != len(rows):
            raise ValueError("duplicate revision ID")
        return result
    before, after = index(old), index(new)
    rows = []
    for qid in sorted(before.keys() | after.keys()):
        fields = [k for k in FIELDS if before.get(qid, {}).get(k) != after.get(qid, {}).get(k)]
        rows.append({"question_id": qid, "previously_used": qid in previously_used,
            "presence": "both" if qid in before and qid in after else "old_only" if qid in before else "new_only",
            "changed_fields": fields})
    return rows


def build():
    old = ROOT / "benchmarks/.cache/bird/extract/dev_20240627/dev.json"
    new = ROOT / "benchmarks/.cache/bird/dev_20251106.json"
    screen = ROOT / "paper/results/calibration_population_audit/bird_source_screen.json"
    updated = read_corrected(new)
    excluded = next(r["screened_ids"] for r in json.loads(screen.read_text())["splits"] if r["split"] == "dev")
    rows = changes(json.loads(old.read_text()), updated, set(excluded))
    source_audit = ROOT / "paper/results/adaptive_comparison_preflight/source_audit.json"
    gold_execution = None
    if source_audit.exists():
        # Optional expansion after full source verification. Keep every screened
        # ID regardless of execution result; never choose tasks by success.
        pins = json.loads(source_audit.read_text())["archives"]["dev"]["database_sha256"]
        dbroot = old.parent / "dev_databases"
        def check_bytes():
            for db, sha in pins.items():
                if digest(dbroot / db / f"{db}.sqlite") != sha:
                    raise ValueError(f"database changed: {db}")
        check_bytes()
        def audit(q):
            result = execute(dbroot / q["db_id"] / f'{q["db_id"]}.sqlite', q["SQL"])
            return {"question_id": q["question_id"], "db_id": q["db_id"], "status": result.status,
                "web_view_exposed": q["question_id"] in range(18),
                "rows": len(result.rows) if result.status == "ok" else None,
                "distinct_rows": len(set(result.rows)) if result.status == "ok" else None}
        with ThreadPoolExecutor(max_workers=4) as pool:
            observations = list(pool.map(audit, [q for q in updated if q["question_id"] not in excluded]))
        check_bytes()
        gold_execution = {"source_audit_sha256": digest(source_audit),
            "status_counts": dict(sorted(Counter(r["status"] for r in observations).items())), "rows": observations}
    report = {"schema": "gac-bird-revision-audit-v1", "provider_calls": 0,
        "source_url": URL, "upstream_revision": REVISION,
        "source_hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (old, new, screen, Path(__file__).resolve())},
        "counts": {"old": len(json.loads(old.read_text())), "new": len(updated),
            "changed": sum(bool(r["changed_fields"]) for r in rows),
            "changed_screened_in": sum(bool(r["changed_fields"]) and not r["previously_used"] for r in rows),
            "changed_fields": {k: sum(k in r["changed_fields"] for r in rows) for k in FIELDS}},
        "rows": rows,
        "gold_execution": gold_execution,
        "limitations": ["Field changes are not all annotation errors; release also changes task content.",
            "Gold execution, when present, tests availability against archive-pinned databases, not semantic correctness.",
            "Do not mix old outcomes with revised questions or count reused IDs as fresh tasks.",
            "During provenance discovery, the official web viewer exposed corrected dev IDs 0 through 17 to the assistant; these are not blinded to this audit.",
            "Source screening remains based on original split IDs, including every earlier attempted or selected task."]}
    out = ROOT / "paper/results/adaptive_comparison_preflight/bird_revision_audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report["counts"], indent=2))


if __name__ == "__main__":
    build()
