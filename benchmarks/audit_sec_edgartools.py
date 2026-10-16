"""Offline, independent-parser check of selected SEC Company Facts observations.

This compares the existing normalized pool against EdgarTools' parser of the
checksum-pinned raw SEC Company Facts responses. It does not provide independent
filing gold or change the selected cohort, grader, or agent-visible tools.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from importlib.metadata import version
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence

from benchmarks.adapters.store import FrozenRecordStore
from benchmarks.build.sec_pool import SCHEMA
from benchmarks.fetch.sec import fetch_issuer_sources


AUDIT_SCHEMA = "agent-compaction-sec-edgartools-audit/v1"
UNITS = {"pure": "number", "USD/shares": "USD per share"}


def _number(value: Any) -> Decimal | str:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return str(value)


def check_observation(
    raw_companyfacts: Mapping[str, Any],
    normalized_company: Mapping[str, Any],
    filing_fact: Mapping[str, Any],
    *,
    cik: str,
    taxonomy: str,
    concept: str,
    accession: str,
    period_end: str,
    as_of_date: str,
) -> dict[str, Any]:
    """Cross-check one already selected record; never choose or replace records."""

    if str(raw_companyfacts.get("cik", "")).zfill(10) != cik:
        return {"status": "fail", "reason": "raw_cik_mismatch"}
    if raw_companyfacts.get("entityName") != normalized_company.get("entityName"):
        return {"status": "fail", "reason": "entity_name_mismatch"}
    selected = [
        item for item in normalized_company.get("facts", {}).get(taxonomy, {}).get(concept, [])
        if item.get("accession") == accession
        and item.get("end") == period_end
        and item.get("start") == filing_fact.get("start")
        and item.get("unit") == filing_fact.get("unit")
        and _number(item.get("value")) == _number(filing_fact.get("value"))
    ]
    if len(selected) != 1:
        return {"status": "fail", "reason": "normalized_observation_ambiguous_or_missing",
                "matching_observations": len(selected)}
    expected = selected[0]
    if str(expected.get("filed", "")) > as_of_date:
        return {"status": "fail", "reason": "observation_postdates_as_of"}

    # Pass only the chosen concept to the external parser. This keeps the audit
    # bounded even for large issuers and preserves all units/periods for that
    # concept, so duplicates remain observable.
    raw_concept = raw_companyfacts.get("facts", {}).get(taxonomy, {}).get(concept)
    if not isinstance(raw_concept, dict):
        return {"status": "fail", "reason": "raw_concept_missing"}
    try:
        from edgar.entity.parser import EntityFactsParser
    except ImportError as exc:
        raise RuntimeError("Install the pinned SEC extra: pip install -e '.[sec]'") from exc
    parsed = EntityFactsParser.parse_company_facts({
        "cik": raw_companyfacts["cik"],
        "entityName": raw_companyfacts["entityName"],
        "facts": {taxonomy: {concept: raw_concept}},
    })
    if parsed is None:
        return {"status": "fail", "reason": "edgartools_parse_failed"}
    matches = [
        fact for fact in parsed
        if fact.taxonomy == taxonomy
        and fact.concept == f"{taxonomy}:{concept}"
        and fact.accession == accession
        and fact.period_end == date.fromisoformat(period_end)
        and fact.period_start == (date.fromisoformat(expected["start"]) if expected.get("start") else None)
        and fact.filing_date == date.fromisoformat(str(expected["filed"]))
        and fact.form_type == expected.get("form")
        and fact.unit == UNITS.get(str(expected["unit"]), expected["unit"])
        and _number(fact.value) == _number(expected["value"])
    ]
    if len(matches) != 1:
        return {"status": "fail", "reason": "edgartools_observation_ambiguous_or_missing",
                "matching_observations": len(matches)}
    return {"status": "pass", "accession": accession, "taxonomy": taxonomy,
            "concept": concept, "period_end": period_end,
            "value": str(expected["value"]), "unit": str(expected["unit"])}


def audit_pool(pool_dir: Path, cache_dir: Path) -> dict[str, Any]:
    """Replay cached official responses; never emit an SEC or model request."""

    if version("edgartools") != "5.62.0":
        raise RuntimeError("EdgarTools audit requires the pinned edgartools==5.62.0")
    store = FrozenRecordStore.load(pool_dir / "snapshot.json", schema=SCHEMA)
    snapshot = f"sha256:{store.snapshot_digest}"
    cases = [json.loads(line) for line in (pool_dir / "cases.jsonl").read_text().splitlines()]
    results: list[dict[str, Any]] = []
    raw_by_cik: dict[str, Mapping[str, Any]] = {}
    for case in cases:
        inputs = case["inputs"]
        cik = str(inputs["cik"]).zfill(10)
        accession = str(case["metadata"]["lineage_ids"][1])
        item: dict[str, Any] = {"case_id": case["case_id"], "cik": cik,
                                "accession": accession}
        try:
            if case["domain"] != "sec" or case["source_snapshot"] != snapshot:
                raise ValueError("case snapshot/domain mismatch")
            company = store.get("companyfacts", cik, snapshot_digest=snapshot)
            fact = store.get("filing_facts",
                             f"{accession}:{inputs['concept']}:{inputs['period_end']}",
                             snapshot_digest=snapshot)
            if not company or not fact:
                raise ValueError("selected normalized observation missing")
            if cik not in raw_by_cik:
                raw_record = fetch_issuer_sources(cik, cache_dir, offline=True)["companyfacts"]
                if raw_record.sha256 != company["_source"]["snapshot_digest"]:
                    raise ValueError("cached SEC response differs from normalized source digest")
                raw_by_cik[cik] = json.loads(Path(raw_record.path).read_text())
            item.update(check_observation(
                raw_by_cik[cik], company, fact, cik=cik,
                taxonomy=str(inputs["taxonomy"]), concept=str(inputs["concept"]),
                accession=accession, period_end=str(inputs["period_end"]),
                as_of_date=str(inputs["as_of_date"]),
            ))
        except (KeyError, ValueError, OSError) as exc:
            item.update(status="fail", reason=type(exc).__name__ + ": " + str(exc))
        results.append(item)
    passed = sum(item["status"] == "pass" for item in results)
    report = {
        "schema": AUDIT_SCHEMA,
        "edgartools_version": version("edgartools"),
        "snapshot_digest": snapshot,
        "cases_sha256": hashlib.sha256((pool_dir / "cases.jsonl").read_bytes()).hexdigest(),
        "cases": len(cases), "passed_cases": passed, "failed_cases": len(cases) - passed,
        "valid": bool(cases) and passed == len(cases),
        "source": "cached official SEC Company Facts JSON",
        "provider_calls_executed": 0,
        "limitation": "Independent parser of the same Company Facts response; not independent filing gold.",
        "results": results,
    }
    (pool_dir / "edgartools_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=Path("benchmarks/.cache"))
    args = parser.parse_args(argv)
    report = audit_pool(args.pool, args.cache)
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
