"""SEC filing-fact local tools and deterministic reviewed-macro candidate."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from guarded_agentic_compaction.evaluation import BenchmarkCase

from .store import FrozenRecordStore, SnapshotError


class SecSnapshot:
    def __init__(self, store: FrozenRecordStore) -> None:
        self.store = store

    def get_sec_submissions(self, *, snapshot_digest: str, cik: str) -> Any:
        return self.store.get("submissions", cik.zfill(10), snapshot_digest=snapshot_digest)

    def get_sec_companyfacts(self, *, snapshot_digest: str, cik: str) -> Any:
        return self.store.get("companyfacts", cik.zfill(10), snapshot_digest=snapshot_digest)

    def list_applicable_filings(
        self, *, snapshot_digest: str, cik: str, form: str, as_of_date: str
    ) -> list[dict[str, Any]]:
        filings = self.store.get("filings", cik.zfill(10), snapshot_digest=snapshot_digest) or []
        return [
            filing
            for filing in filings
            if filing.get("form") in {form, f"{form}/A"}
            and str(filing.get("filed_date", "")) <= as_of_date
        ]

    def read_filing_xbrl_fact(
        self,
        *,
        snapshot_digest: str,
        accession: str,
        concept: str,
        period: str,
    ) -> Any:
        return self.store.get(
            "filing_facts",
            f"{accession}:{concept}:{period}",
            snapshot_digest=snapshot_digest,
        )

    def read_filing_metadata(self, *, snapshot_digest: str, accession: str) -> Any:
        return self.store.get("filing_metadata", accession, snapshot_digest=snapshot_digest)


def _comparable_value(value: Any) -> tuple[str, str]:
    text = str(value).replace(",", "").strip()
    try:
        return "number", format(Decimal(text).normalize(), "f")
    except InvalidOperation:
        return "text", text


def sec_macro(case: BenchmarkCase, tools: SecSnapshot) -> dict[str, Any]:
    """Reconcile a standard fact without collapsing units or contexts."""

    inputs = case.inputs
    snapshot = case.source_snapshot
    cik = str(inputs["cik"]).zfill(10)
    concept = str(inputs["concept"])
    taxonomy = str(inputs.get("taxonomy", "us-gaap"))
    period_end = str(inputs["period_end"])
    as_of = str(inputs["as_of_date"])
    form = str(inputs["form"])
    try:
        date.fromisoformat(period_end)
        date.fromisoformat(as_of)
    except ValueError as exc:
        raise SnapshotError("SEC case dates must be ISO dates") from exc

    company = tools.get_sec_companyfacts(snapshot_digest=snapshot, cik=cik)
    if not company:
        return _sec_missing(cik, taxonomy, concept, state="MISSING")
    filings = tools.list_applicable_filings(
        snapshot_digest=snapshot, cik=cik, form=form, as_of_date=as_of
    )
    matching = [item for item in filings if item.get("report_date") == period_end]
    if not matching:
        return _sec_missing(cik, taxonomy, concept, issuer=company.get("entityName", ""))
    applicable = max(matching, key=lambda item: (item["filed_date"], item["accession"]))
    accession = applicable["accession"]
    fact = tools.read_filing_xbrl_fact(
        snapshot_digest=snapshot,
        accession=accession,
        concept=concept,
        period=period_end,
    )
    if not fact:
        return _sec_missing(cik, taxonomy, concept, issuer=company.get("entityName", ""))

    candidates = [
        item
        for item in company.get("facts", {}).get(taxonomy, {}).get(concept, [])
        if item.get("end") == period_end and item.get("filed", "") <= as_of
    ]
    units = {item.get("unit") for item in candidates}
    contexts = {(item.get("start"), item.get("end"), item.get("frame")) for item in candidates}
    state = "OK"
    if len(units) > 1:
        state = "MULTIPLE_UNITS"
    elif len(contexts) > 1:
        state = "MULTIPLE_CONTEXTS"
    company_item = next(
        (item for item in candidates if item.get("accession") == accession and item.get("unit") == fact.get("unit")),
        None,
    )
    agreement = "NOT_ASSESSABLE"
    if company_item is not None:
        agreement = (
            "AGREE"
            if _comparable_value(company_item.get("value"))
            == _comparable_value(fact.get("value"))
            else "DISAGREE"
        )
    metadata = tools.read_filing_metadata(snapshot_digest=snapshot, accession=accession) or applicable
    return {
        "cik": cik,
        "issuer": company.get("entityName", ""),
        "taxonomy": taxonomy,
        "concept": concept,
        "value": str(fact["value"]),
        "unit": fact.get("unit"),
        "period_start": fact.get("start"),
        "period_end": fact.get("end"),
        "form": metadata.get("form"),
        "fiscal_year": fact.get("fiscal_year"),
        "fiscal_period": fact.get("fiscal_period"),
        "accession": accession,
        "filed_date": metadata.get("filed_date"),
        "report_date": metadata.get("report_date"),
        "amendment": str(metadata.get("form", "")).endswith("/A"),
        "applicable_accession_as_of": accession,
        "companyfacts_filing_agreement": agreement,
        "state": state,
        "sources": list(fact.get("sources", [])),
    }


def _sec_missing(
    cik: str,
    taxonomy: str,
    concept: str,
    *,
    issuer: str = "",
    state: str = "NOT_ASSESSABLE",
) -> dict[str, Any]:
    return {
        "cik": cik,
        "issuer": issuer or "Unknown issuer",
        "taxonomy": taxonomy,
        "concept": concept,
        "value": None,
        "unit": None,
        "period_start": None,
        "period_end": None,
        "form": None,
        "fiscal_year": None,
        "fiscal_period": None,
        "accession": None,
        "filed_date": None,
        "report_date": None,
        "amendment": None,
        "applicable_accession_as_of": None,
        "companyfacts_filing_agreement": "NOT_ASSESSABLE",
        "state": state,
        "sources": [],
    }
