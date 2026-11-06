"""Audit local BIRD bytes and all screened-in gold queries without model calls.

Build is optional-data work. Verify and tests require only retained public
metadata; neither downloads databases nor reexecutes benchmark SQL in CI.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import pickle
import shutil
import sqlite3
import zipfile

from adaptive_sql_grader import execute
from bird_sql_agent_study import SPLIT_CONFIG

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/results/adaptive_comparison_preflight"
SCREEN = ROOT / "paper/results/calibration_population_audit/bird_source_screen.json"
SELF = Path(__file__).resolve()


def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def stream_digest(handle):
    return hashlib.file_digest(handle, "sha256").hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n")


class _BuiltinOnly(pickle.Unpickler):
    def find_class(self, module, name):
        raise ValueError("gold exposure inventory permits only primitive pickle data")


def summarize(rows):
    databases = []
    for split, db in sorted({(r["split"], r["db_id"]) for r in rows}):
        subset = [r for r in rows if (r["split"], r["db_id"]) == (split, db)]
        databases.append({"split": split, "db_id": db, "screened_in": len(subset),
            "gold_status": dict(sorted(Counter(r["gold_status"] for r in subset).items())),
            "difficulty": dict(sorted(Counter(r["difficulty"] for r in subset).items())),
            "previously_gold_cached": sum(r["previously_gold_cached"] for r in subset),
            "empty_gold": sum(r["gold_status"] == "ok" and r["row_count"] == 0 for r in subset),
            "duplicate_gold": sum(r["gold_status"] == "ok" and r["row_count"] != r["distinct_rows"] for r in subset)})
    return databases


def verify(report):
    if report["decision"] != "NOT_READY_FOR_CONFIRMATORY_EXECUTION" or report["provider_calls"] != 0:
        raise ValueError("preflight cannot promote itself to execution or empirical evidence")
    for name, sha in report["source_hashes"].items():
        if digest(ROOT / name) != sha:
            raise ValueError(f"source changed: {name}")
    screen = json.loads(SCREEN.read_text())
    for name, sha in screen["source_hashes"].items():
        if digest(ROOT / name) != sha:
            raise ValueError(f"screen input changed: {name}")
    keys = [(r["split"], r["question_id"]) for r in report["rows"]]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate task ID")
    for split in screen["splits"]:
        rows = [r for r in report["rows"] if r["split"] == split["split"]]
        # This release has consecutive positional IDs in both splits.
        expected = set(range(split["total"])) - set(split["screened_ids"])
        if {r["question_id"] for r in rows} != expected:
            raise ValueError("missing, added or previously used question")
        counts = Counter(r["db_id"] for r in rows)
        if counts != Counter({d["db_id"]: d["remaining"] for d in split["databases"]}):
            raise ValueError("database allocation changed")
    if report["databases"] != summarize(report["rows"]):
        raise ValueError("incorrect source summary")
    for row in report["rows"]:
        if row["gold_status"] not in {"ok", "timeout", "resource_limit", "sql_error", "denied", "empty_sql", "not_query"}:
            raise ValueError("unknown gold disposition")
        if row["gold_status"] == "ok":
            if not 0 <= row["distinct_rows"] <= row["row_count"] or row["columns"] < 1:
                raise ValueError("invalid result accounting")
        elif any(row[k] is not None for k in ("row_count", "distinct_rows", "columns")):
            raise ValueError("unavailable gold represented as valid result")
    for split in screen["splits"]:
        rec = report["archives"][split["split"]]
        if rec["outer_sha256"] != SPLIT_CONFIG[split["split"]]["sha256"]:
            raise ValueError("wrong source release")
        if rec["question_sha256"] != split["question_sha256"]:
            raise ValueError("question provenance mismatch")
        if set(rec["database_sha256"]) != {d["db_id"] for d in split["databases"]}:
            raise ValueError("missing database provenance")


def build():
    screen = json.loads(SCREEN.read_text())
    report = {"schema": "gac-adaptive-source-preflight-v1", "provider_calls": 0,
        "decision": "NOT_READY_FOR_CONFIRMATORY_EXECUTION", "archives": {}, "rows": [],
        "sqlite_version": sqlite3.sqlite_version,
        "execution_limits": {"timeout_s": 30, "max_rows": 100_000, "max_bytes": 32_000_000},
        "source_hashes": {str(p.relative_to(ROOT)): digest(p) for p in
            (SCREEN, SELF, SELF.with_name("adaptive_sql_grader.py"), SELF.with_name("bird_sql_agent_study.py"))},
        "limitations": ["Gold execution is not validation of question/SQL semantics.",
            "Prior model-use screen covers retained paper/results/bird JSON; global author inspection and benchmark training exposure remain unknown.",
            "Gold cache presence is a lower bound on prior gold execution, not evidence of model exposure.",
            "All screened-in IDs retained, including failures; none is automatically a sealed evaluation cohort.",
            "Database integrity here means complete archive-byte matching, not an exhaustive SQLite integrity_check.",
            "No final order/tolerance annotations, candidate freeze, faithful live comparator, power choice or spending seal."]}
    for selection in screen["splits"]:
        split = selection["split"]
        cfg = SPLIT_CONFIG[split]
        print(f"Verifying {split} archive and every database", flush=True)
        outer_sha = digest(cfg["archive"])
        if outer_sha != cfg["sha256"]:
            raise ValueError(f"archive hash mismatch: {split}")
        questions_path = cfg["dir"] / cfg["questions"]
        questions = json.loads(questions_path.read_text())
        if {q.get("question_id", i) for i, q in enumerate(questions)} != set(range(len(questions))):
            raise ValueError("release no longer has consecutive IDs")
        nested_path = cfg["dir"] / f"{split}_databases.zip"
        with zipfile.ZipFile(cfg["archive"]) as outer:
            qname = next(n for n in outer.namelist() if n == f'{cfg["release"]}/{split}.json')
            if outer.read(qname) != questions_path.read_bytes():
                raise ValueError("question bytes differ from pinned archive")
            with outer.open(f'{cfg["release"]}/{split}_databases.zip') as handle:
                if not nested_path.exists():
                    # Only this known member of a checksum-pinned archive is
                    # materialized. Do not extract arbitrary archive paths.
                    pending = nested_path.with_suffix(".zip.partial")
                    with pending.open("wb") as target:
                        shutil.copyfileobj(handle, target, 1 << 20)
                    pending.replace(nested_path)
                    nested_sha = digest(nested_path)
                else:
                    nested_sha = stream_digest(handle)
        if nested_sha != digest(nested_path):
            raise ValueError("nested archive mismatch")
        hashes = {}
        with zipfile.ZipFile(nested_path) as archive:
            for db in sorted({q["db_id"] for q in questions}):
                names = [n for n in archive.namelist() if n.endswith(f"/{db}/{db}.sqlite")]
                if len(names) != 1:
                    raise ValueError(f"ambiguous database member: {db}")
                with archive.open(names[0]) as handle:
                    archived = stream_digest(handle)
                path = cfg["dir"] / cfg["databases"] / db / f"{db}.sqlite"
                if not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    pending = path.with_suffix(".sqlite.partial")
                    with archive.open(names[0]) as handle, pending.open("wb") as target:
                        shutil.copyfileobj(handle, target, 1 << 20)
                    pending.replace(path)
                if digest(path) != archived:
                    raise ValueError(f"database mismatch: {split}/{db}")
                hashes[db] = archived
        prior_gold = _BuiltinOnly(io.BytesIO(cfg["gold"].read_bytes())).load() if cfg["gold"].exists() else {}
        report["archives"][split] = {"outer_sha256": outer_sha, "nested_sha256": nested_sha,
            "question_sha256": digest(questions_path), "database_sha256": hashes,
            "prior_gold_cache_sha256": digest(cfg["gold"]) if cfg["gold"].exists() else None}
        excluded = set(selection["screened_ids"])
        todo = [(i, q) for i, q in enumerate(questions) if q.get("question_id", i) not in excluded]

        def audit(item):
            i, q = item
            path = cfg["dir"] / cfg["databases"] / q["db_id"] / f'{q["db_id"]}.sqlite'
            result = execute(path, q["SQL"])
            qid = q.get("question_id", i)
            return {"split": split, "question_id": qid, "db_id": q["db_id"],
                "difficulty": str(q.get("difficulty", "unlabelled")),
                "previously_gold_cached": qid in prior_gold,
                "question_record_sha256": hashlib.sha256(json.dumps(q, sort_keys=True).encode()).hexdigest(),
                "gold_status": result.status, "columns": result.columns if result.status == "ok" else None,
                "row_count": len(result.rows) if result.status == "ok" else None,
                "distinct_rows": len(set(result.rows)) if result.status == "ok" else None}

        with ThreadPoolExecutor(max_workers=4) as pool:
            for index, row in enumerate(pool.map(audit, todo), 1):
                report["rows"].append(row)
                if index % 100 == 0:
                    print(f"{split}: {index}/{len(todo)} gold queries audited", flush=True)
        # Verify the executor did not change any source bytes.
        for db, expected in hashes.items():
            if digest(cfg["dir"] / cfg["databases"] / db / f"{db}.sqlite") != expected:
                raise ValueError(f"database changed during audit: {db}")
        write(OUT / "source_audit.partial.json", report)
    report["databases"] = summarize(report["rows"])
    verify(report)
    write(OUT / "source_audit.json", report)
    (OUT / "source_audit.partial.json").unlink(missing_ok=True)
    print("Source byte and gold-execution audit complete; execution remains unsealed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "verify"])
    args = parser.parse_args()
    if args.command == "build":
        build()
    else:
        verify(json.loads((OUT / "source_audit.json").read_text()))
        print("Retained source audit verified without optional databases or model calls.")
