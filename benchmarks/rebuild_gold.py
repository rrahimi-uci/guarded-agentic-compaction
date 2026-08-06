"""Recompute independent gold from an existing normalized real-record pool.

This command is deliberately provider-free.  It is useful when the independent
gold implementation is reviewed or strengthened: raw public archives do not need
to be fetched again because snapshot, case, and source identities remain unchanged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from guarded_agentic_compaction.benchmarking import load_case_jsonl
from guarded_agentic_compaction.evaluation import BenchmarkCase

from .gold import (
    hmda_gold_from_records,
    sec_gold_from_records,
    vulnerability_gold_from_records,
)


GoldBuilder = Callable[[BenchmarkCase, Mapping[str, Any]], dict[str, Any]]
BUILDERS: dict[str, GoldBuilder] = {
    "vulnerability": vulnerability_gold_from_records,
    "sec": sec_gold_from_records,
    "hmda": hmda_gold_from_records,
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def rebuild_gold(domain: str, pool: str | Path) -> dict[str, Any]:
    if domain not in BUILDERS:
        raise ValueError(f"unsupported domain {domain!r}")
    pool_path = Path(pool)
    cases = load_case_jsonl(pool_path / "cases.jsonl")
    snapshot = json.loads((pool_path / "snapshot.json").read_text(encoding="utf-8"))
    records = snapshot.get("records")
    if not isinstance(records, Mapping):
        raise ValueError("snapshot records must be an object")
    expected_schema = f"agent-compaction-{domain}-snapshot/v1"
    if snapshot.get("schema") != expected_schema:
        raise ValueError(
            f"snapshot schema must be {expected_schema!r}, got {snapshot.get('schema')!r}"
        )
    snapshot_digest = str(snapshot.get("snapshot_digest", "")).removeprefix("sha256:")
    if any(
        case.domain != domain
        or case.source_snapshot.removeprefix("sha256:") != snapshot_digest
        for case in cases
    ):
        raise ValueError("case domain or snapshot identity differs from the normalized pool")

    builder = BUILDERS[domain]
    rows = [
        {"case_id": case.case_id, "output": builder(case, records)}
        for case in cases
    ]
    gold_path = pool_path / "gold.jsonl"
    _atomic_text(
        gold_path,
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
    )

    report_path = pool_path / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    implementation_path = Path(__file__).resolve().with_name("gold.py")
    report["gold_construction"] = {
        "implementation": f"benchmarks/gold.py:{builder.__name__}",
        "implementation_sha256": _sha256(implementation_path),
        "independent_from_macro": True,
        "cases": len(rows),
    }
    gold_digest = _sha256(gold_path)
    if domain == "hmda":
        report["gold_file_sha256"] = gold_digest
    else:
        normalized = report.setdefault("normalized_artifact_sha256", {})
        if not isinstance(normalized, dict):
            raise ValueError("normalized_artifact_sha256 must be an object")
        normalized["gold.jsonl"] = gold_digest
    _atomic_text(
        report_path,
        json.dumps(report, indent=2, sort_keys=True) + "\n",
    )
    return {
        "schema": "agent-compaction-independent-gold-rebuild/v1",
        "domain": domain,
        "cases": len(rows),
        "gold_sha256": gold_digest,
        "snapshot_digest": snapshot_digest,
        "provider_calls_executed": 0,
        "gold_construction": report["gold_construction"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("domain", choices=sorted(BUILDERS))
    parser.add_argument("pool", type=Path)
    args = parser.parse_args(argv)
    result = rebuild_gold(args.domain, args.pool)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
