"""Build a real SEC fact-reconciliation pool from cached EDGAR records."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Sequence

from guarded_agentic_compaction.evaluation import BenchmarkCase
from benchmarks.adapters.store import canonical
from benchmarks.fetch.common import SourceFetchError, SourcePolicyError
from benchmarks.fetch.sec import (
    fetch_filing_file,
    fetch_filing_index,
    fetch_issuer_sources,
)
from benchmarks.gold import sec_gold_from_records


SCHEMA = "agent-compaction-sec-snapshot/v1"
FORMS = {"10-K", "10-Q", "10-K/A", "10-Q/A"}
CONCEPTS = (
    "Assets",
    "Liabilities",
    "StockholdersEquity",
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "NetIncomeLoss",
    "EntityCommonStockSharesOutstanding",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def select_instance_filename(index: dict[str, Any]) -> str:
    """Select an XBRL instance, rejecting inline-only or ambiguous directories."""

    items = index.get("directory", {}).get("item", [])
    explicit = [
        str(item.get("name"))
        for item in items
        if str(item.get("type", "")).upper() == "EX-101.INS"
    ]
    if len(explicit) == 1:
        return explicit[0]
    excluded = ("_cal.xml", "_def.xml", "_lab.xml", "_pre.xml", "filingsummary.xml")
    candidates = [
        str(item.get("name"))
        for item in items
        if str(item.get("name", "")).casefold().endswith(".xml")
        and not str(item.get("name", "")).casefold().endswith(excluded)
    ]
    if len(candidates) != 1:
        raise SourceFetchError("filing has no unique non-inline XBRL instance")
    return candidates[0]


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _unit(element: ET.Element) -> str | None:
    measures = [
        (child.text or "").split(":")[-1]
        for child in element.iter()
        if _local(child.tag) == "measure" and child.text
    ]
    return " per ".join(measures) if measures else None


def parse_xbrl_instance(data: bytes) -> dict[str, Any]:
    """Extract contexts, units, and standard facts from one XBRL instance."""

    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise SourceFetchError("filing instance is not well-formed XML") from exc
    contexts: dict[str, dict[str, str | None]] = {}
    units: dict[str, str | None] = {}
    for element in root.iter():
        name = _local(element.tag)
        if name == "context" and element.get("id"):
            start = end = instant = None
            for child in element.iter():
                child_name = _local(child.tag)
                if child_name == "startDate":
                    start = child.text
                elif child_name == "endDate":
                    end = child.text
                elif child_name == "instant":
                    instant = child.text
            contexts[element.get("id", "")] = {
                "start": start,
                "end": instant or end,
            }
        elif name == "unit" and element.get("id"):
            units[element.get("id", "")] = _unit(element)
    facts: list[dict[str, Any]] = []
    for element in root:
        context = element.get("contextRef")
        if not context or context not in contexts:
            continue
        namespace = element.tag[1:].split("}", 1)[0] if element.tag.startswith("{") else ""
        if "fasb.org/us-gaap" not in namespace and "xbrl.sec.gov/dei" not in namespace:
            continue
        value = "".join(element.itertext()).strip()
        if element.get("{http://www.w3.org/2001/XMLSchema-instance}nil") == "true":
            value = None
        facts.append(
            {
                "taxonomy": "us-gaap" if "fasb.org/us-gaap" in namespace else "dei",
                "concept": _local(element.tag),
                "value": value,
                "unit": units.get(element.get("unitRef", "")),
                "start": contexts[context]["start"],
                "end": contexts[context]["end"],
                "context_id": context,
            }
        )
    return {"contexts": contexts, "units": units, "facts": facts}


def _normalized_decimal(value: Any) -> str:
    text = str(value).replace(",", "").strip()
    try:
        decimal = Decimal(text)
    except InvalidOperation:
        return text
    normalized = format(decimal, "f")
    return normalized.rstrip("0").rstrip(".") if "." in normalized else normalized


def _submissions_filings(payload: dict[str, Any]) -> list[dict[str, Any]]:
    recent = payload.get("filings", {}).get("recent", {})
    keys = (
        "accessionNumber", "filingDate", "reportDate", "form", "primaryDocument"
    )
    lengths = [len(recent.get(key, [])) for key in keys]
    if not lengths or len(set(lengths)) != 1:
        raise SourceFetchError("SEC submissions recent arrays are misaligned")
    return [
        {
            "accession": recent["accessionNumber"][index],
            "filed_date": recent["filingDate"][index],
            "report_date": recent["reportDate"][index],
            "form": recent["form"][index],
            "primary_document": recent["primaryDocument"][index],
        }
        for index in range(lengths[0])
        if recent["form"][index] in FORMS
    ]


def _company_candidates(payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for taxonomy in ("us-gaap", "dei"):
        taxonomy_facts = payload.get("facts", {}).get(taxonomy, {})
        for concept in CONCEPTS:
            concept_payload = taxonomy_facts.get(concept, {})
            for unit, observations in concept_payload.get("units", {}).items():
                for item in observations:
                    if item.get("form") not in FORMS or not item.get("accn") or not item.get("end"):
                        continue
                    yield {
                        "taxonomy": taxonomy,
                        "concept": concept,
                        "unit": unit,
                        "value": item.get("val"),
                        "start": item.get("start"),
                        "end": item.get("end"),
                        "accession": item.get("accn"),
                        "filed": item.get("filed"),
                        "form": item.get("form"),
                        "fiscal_year": item.get("fy"),
                        "fiscal_period": item.get("fp"),
                        "frame": item.get("frame"),
                    }


def _source(name: str, record_id: str, url: str, digest: str) -> dict[str, str]:
    return {"source": name, "record_id": record_id, "url": url, "snapshot_digest": digest}


def acquire_issuer(
    cik: str, cache_dir: Path, *, offline: bool = False
) -> tuple[dict[str, Any], str | None]:
    records = fetch_issuer_sources(cik, cache_dir, offline=offline)
    submissions = json.loads(Path(records["submissions"].path).read_text(encoding="utf-8"))
    company = json.loads(Path(records["companyfacts"].path).read_text(encoding="utf-8"))
    filings = _submissions_filings(submissions)
    by_accession = {item["accession"]: item for item in filings}
    company_candidates = list(_company_candidates(company))

    def hard_state(item: dict[str, Any]) -> bool:
        related = [
            other
            for other in company_candidates
            if other["taxonomy"] == item["taxonomy"]
            and other["concept"] == item["concept"]
            and other["end"] == item["end"]
            and other["filed"] <= item["filed"]
        ]
        units = {other["unit"] for other in related}
        contexts = {(other["start"], other["end"], other["frame"]) for other in related}
        return item["form"].endswith("/A") or len(units) > 1 or len(contexts) > 1

    prefer_hard = int(hashlib.sha256(f"20260804:{cik}:hard".encode()).hexdigest(), 16) % 5 == 0
    ranked = sorted(
        company_candidates,
        key=lambda item: (
            0 if (prefer_hard and hard_state(item)) else 1,
            hashlib.sha256(
                f"20260804:{cik}:{item['accession']}:{item['concept']}:{item['end']}".encode()
            ).hexdigest(),
        ),
    )
    for candidate in ranked:
        filing = by_accession.get(candidate["accession"])
        if filing is None or filing["report_date"] != candidate["end"]:
            continue
        applicable = [
            item
            for item in filings
            if item["form"]
            in {
                candidate["form"].removesuffix("/A"),
                f"{candidate['form'].removesuffix('/A')}/A",
            }
            and item["report_date"] == candidate["end"]
            and item["filed_date"] <= candidate["filed"]
        ]
        if not applicable or max(
            applicable, key=lambda item: (item["filed_date"], item["accession"])
        )["accession"] != candidate["accession"]:
            # The case's deterministic as-of rule must resolve to the exact
            # filing whose XBRL instance is retained below.
            continue
        try:
            index_record = fetch_filing_index(
                cik, candidate["accession"], cache_dir, offline=offline
            )
            index = json.loads(Path(index_record.path).read_text(encoding="utf-8"))
            filename = select_instance_filename(index)
            document = fetch_filing_file(
                cik, candidate["accession"], filename, cache_dir, offline=offline
            )
            parsed = parse_xbrl_instance(Path(document.path).read_bytes())
        except SourcePolicyError:
            raise
        except Exception:
            continue
        matches = [
            fact
            for fact in parsed["facts"]
            if fact["taxonomy"] == candidate["taxonomy"]
            and fact["concept"] == candidate["concept"]
            and fact["end"] == candidate["end"]
            and (fact["unit"] == candidate["unit"] or fact["unit"] is None)
        ]
        exact = [
            fact
            for fact in matches
            if _normalized_decimal(fact["value"]) == _normalized_decimal(candidate["value"])
        ]
        if len(exact) != 1:
            continue
        fact = exact[0]
        company_source = _source(
            "SEC Company Facts", f"{cik}:{candidate['concept']}:{candidate['accession']}",
            records["companyfacts"].url, records["companyfacts"].sha256,
        )
        filing_source = _source(
            "SEC filed XBRL instance", f"{candidate['accession']}:{candidate['concept']}:{fact['context_id']}",
            document.url, document.sha256,
        )
        related_company = [
            other
            for other in company_candidates
            if other["taxonomy"] == candidate["taxonomy"]
            and other["concept"] == candidate["concept"]
            and other["end"] == candidate["end"]
            and other["filed"] <= candidate["filed"]
        ]
        normalized_company = {
            "entityName": company.get("entityName", ""),
            "facts": {
                candidate["taxonomy"]: {
                    candidate["concept"]: [
                        {**other, "sources": [company_source]}
                        for other in related_company
                    ]
                }
            },
            "_source": company_source,
        }
        return {
            "cik": cik.zfill(10),
            "company": normalized_company,
            "submissions": {"filings": filings, "_source": _source(
                "SEC Submissions", cik.zfill(10), records["submissions"].url, records["submissions"].sha256
            )},
            "filings": filings,
            "filing": filing,
            "fact": {
                "value": str(candidate["value"]), "unit": candidate["unit"],
                "start": fact["start"], "end": fact["end"],
                "fiscal_year": candidate["fiscal_year"], "fiscal_period": candidate["fiscal_period"],
                "sources": [company_source, filing_source],
            },
            "candidate": candidate,
            "hard_state": hard_state(candidate),
            "document_digest": document.sha256,
        }, None
    return {}, "no_resolvable_standard_instance_fact"


def build_pool(
    *,
    ciks: Sequence[str],
    cache_dir: Path,
    output_dir: Path,
    minimum_groups: int = 420,
    offline: bool = False,
) -> dict[str, Any]:
    accepted = []
    rejected = []
    unique_ciks = list(dict.fromkeys(str(cik).zfill(10) for cik in ciks))
    for cik in unique_ciks:
        try:
            issuer, reason = acquire_issuer(cik, cache_dir, offline=offline)
        except SourcePolicyError:
            raise
        except Exception as exc:
            issuer, reason = {}, type(exc).__name__
        if issuer:
            accepted.append(issuer)
        else:
            rejected.append({"cik": cik.zfill(10), "reason": reason})
        if len(accepted) >= minimum_groups + 100:
            break
    if len(accepted) < minimum_groups:
        raise RuntimeError(f"only {len(accepted)} complete issuer groups; {minimum_groups} required")
    complete_candidate_groups = len(accepted)

    def variable(item: dict[str, Any]) -> bool:
        return bool(item["hard_state"])

    hard = [item for item in accepted if variable(item)]
    ordinary = [item for item in accepted if not variable(item)]
    required_hard = (minimum_groups + 9) // 10
    if len(hard) < required_hard:
        raise RuntimeError(f"only {len(hard)} variable-path SEC issuers; {required_hard} required")
    accepted = [*hard[:required_hard], *ordinary[: minimum_groups - required_hard]]
    if len(accepted) != minimum_groups:
        raise RuntimeError(
            f"only {len(accepted)} groups remain after SEC hard-state stratification; "
            f"{minimum_groups} required"
        )
    records: dict[str, Any] = {
        "submissions": {}, "companyfacts": {}, "filings": {},
        "filing_facts": {}, "filing_metadata": {},
    }
    cases_data = []
    for item in accepted:
        cik = item["cik"]
        candidate = item["candidate"]
        accession = candidate["accession"]
        records["submissions"][cik] = item["submissions"]
        records["companyfacts"][cik] = item["company"]
        records["filings"][cik] = item["filings"]
        key = f"{accession}:{candidate['concept']}:{candidate['end']}"
        records["filing_facts"][key] = item["fact"]
        records["filing_metadata"][accession] = item["filing"]
        case_id = f"sec-{cik}-{accession}-{candidate['concept'].casefold()}"
        cases_data.append({
            "case_id": case_id,
            "group_id": cik,
            "domain": "sec",
            "inputs": {
                "cik": cik, "taxonomy": candidate["taxonomy"], "concept": candidate["concept"],
                "period_end": candidate["end"], "as_of_date": candidate["filed"],
                "form": candidate["form"].removesuffix("/A"),
            },
            "metadata": {
                "lineage_ids": [cik, accession], "real_public_record": True,
                "amendment": candidate["form"].endswith("/A"),
            },
        })
    digest = hashlib.sha256(canonical(records).encode()).hexdigest()
    for case in cases_data:
        case["source_snapshot"] = f"sha256:{digest}"
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot = {"schema": SCHEMA, "snapshot_digest": f"sha256:{digest}", "records": records}
    snapshot_path = output_dir / "snapshot.json"
    cases_path = output_dir / "cases.jsonl"
    gold_path = output_dir / "gold.jsonl"
    snapshot_path.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    cases_path.write_text(
        "".join(json.dumps(case, sort_keys=True) + "\n" for case in cases_data),
        encoding="utf-8",
    )
    gold = []
    for raw in cases_data:
        case = BenchmarkCase(
            case_id=raw["case_id"], group_id=raw["group_id"], domain="sec",
            source_snapshot=raw["source_snapshot"], inputs=raw["inputs"], metadata=raw["metadata"],
        )
        gold.append(
            {
                "case_id": case.case_id,
                "output": sec_gold_from_records(case, records),
            }
        )
    gold_path.write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in gold),
        encoding="utf-8",
    )
    variable_groups = sum(
        item["output"]["amendment"] or item["output"]["state"] != "OK"
        for item in gold
    )
    report = {
        "schema": "agent-compaction-sec-pool-report/v1",
        "real_public_records": True,
        "provider_calls_executed": 0,
        "candidate_ciks": len(unique_ciks),
        "complete_candidate_groups": complete_candidate_groups,
        "selected_groups": len(cases_data),
        "rejected_candidates": rejected,
        "snapshot_digest": digest,
        "variable_path_groups": variable_groups,
        "variable_path_fraction": variable_groups / len(gold),
        "selected_hard_state_groups": sum(bool(item["hard_state"]) for item in accepted),
        "sec_user_agent_required": True,
        "maximum_request_rate_per_second": 5,
        "gold_construction": {
            "implementation": "benchmarks/gold.py:sec_gold_from_records",
            "implementation_sha256": _sha256_file(
                Path(__file__).resolve().parents[1] / "gold.py"
            ),
            "independent_from_macro": True,
            "cases": len(gold),
        },
        "normalized_artifact_sha256": {
            "cases.jsonl": _sha256_file(cases_path),
            "gold.jsonl": _sha256_file(gold_path),
            "snapshot.json": _sha256_file(snapshot_path),
        },
    }
    (output_dir / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ciks", required=True, type=Path, help="JSON list or newline-delimited CIKs")
    parser.add_argument("--cache", default=Path("benchmarks/.cache"), type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--minimum-groups", type=int, default=420)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)
    text = args.ciks.read_text(encoding="utf-8")
    try:
        parsed = json.loads(text)
        values = parsed.values() if isinstance(parsed, dict) else parsed
        ciks = [
            str(item.get("cik_str") or item.get("cik") or item.get("cikStr"))
            if isinstance(item, dict)
            else str(item)
            for item in values
        ]
    except json.JSONDecodeError:
        ciks = [line.strip() for line in text.splitlines() if line.strip()]
    report = build_pool(
        ciks=ciks,
        cache_dir=args.cache,
        output_dir=args.out,
        minimum_groups=args.minimum_groups,
        offline=args.offline,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
