"""Independent gold construction for normalized real-record benchmark snapshots.

These functions deliberately do not import or call the reviewed macro candidates.
They traverse the normalized records directly so a macro defect can be observed by
the exact oracle instead of being copied into its expected output.
"""

from __future__ import annotations

import copy
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from agent_compaction.evaluation import BenchmarkCase


HMDA_PRIVACY_NOTICE = (
    "Public HMDA data are modified to protect applicant and borrower privacy; "
    "this interpretation does not reconstruct underwriting facts."
)


def _record(
    records: Mapping[str, Any], section: str, key: str
) -> Mapping[str, Any] | None:
    value = records.get(section, {}).get(key)
    return value if isinstance(value, Mapping) else None


def vulnerability_gold_from_records(
    case: BenchmarkCase, records: Mapping[str, Any]
) -> dict[str, Any]:
    """Construct vulnerability gold without executing snapshot tools or the macro."""

    inputs = case.inputs
    advisory_id = str(inputs["advisory_id"])
    ecosystem = str(inputs["ecosystem"])
    package = str(inputs["package"])
    version = str(inputs["version"])
    osv = _record(records, "osv", advisory_id)
    query = _record(records, "osv_queries", f"{ecosystem}:{package}:{version}")
    github = _record(records, "github", advisory_id)
    if osv is None or query is None:
        raise LookupError("normalized OSV advisory and package-version record are required")

    aliases = sorted(
        set(map(str, osv.get("aliases", ())))
        | set(map(str, (github or {}).get("aliases", ())))
    )
    cve_ids = [alias for alias in aliases if alias.startswith("CVE-")]
    nvd = _record(records, "nvd", cve_ids[0]) if cve_ids else None
    kev = _record(records, "kev", cve_ids[0]) if cve_ids else None

    affected = query.get("affected")
    affected_state = (
        "AFFECTED"
        if affected is True
        else "NOT_AFFECTED"
        if affected is False
        else "NOT_ASSESSABLE"
    )
    affected_ranges = [
        {
            "source": source,
            "introduced": item.get("introduced"),
            "fixed": item.get("fixed"),
            "last_affected": item.get("last_affected"),
        }
        for source, record in (("OSV", osv), ("GitHub Advisory Database", github))
        if record is not None
        for item in record.get("ranges", ())
    ]
    severity = [
        {
            "source": source,
            "type": item.get("type"),
            "vector": item.get("vector"),
            "score": None if item.get("score") is None else str(item.get("score")),
        }
        for source, record in (("GitHub Advisory Database", github), ("NVD", nvd))
        if record is not None
        for item in record.get("severity", ())
    ]
    cwe_ids = sorted(
        set(map(str, osv.get("cwe_ids", ())))
        | set(map(str, (github or {}).get("cwe_ids", ())))
        | set(map(str, (nvd or {}).get("cwe_ids", ())))
    )

    if not cve_ids:
        kev_output = {
            "membership": "NOT_APPLICABLE",
            "catalog_version": "no-cve-alias",
            "date_added": None,
        }
    elif kev is None:
        kev_output = {
            "membership": "NOT_ASSESSABLE",
            "catalog_version": "unavailable",
            "date_added": None,
        }
    else:
        kev_output = {
            "membership": "LISTED" if kev.get("listed") else "NOT_LISTED",
            "catalog_version": str(kev.get("catalog_version", "unknown")),
            "date_added": kev.get("date_added"),
        }

    osv_ranges = {
        (item.get("introduced"), item.get("fixed"), item.get("last_affected"))
        for item in osv.get("ranges", ())
    }
    github_ranges = {
        (item.get("introduced"), item.get("fixed"), item.get("last_affected"))
        for item in (github or {}).get("ranges", ())
    }
    conflicts: list[str] = []
    if github is not None and osv_ranges != github_ranges:
        conflicts.append("AFFECTED_RANGE_DISAGREEMENT")
        affected_state = "CONFLICT"

    missing_fields: list[str] = []
    if github is None:
        missing_fields.append("github_advisory")
    if cve_ids and nvd is None:
        missing_fields.append("nvd_enrichment")
    if cve_ids and kev is None:
        missing_fields.append("kev_catalog")

    sources = [
        copy.deepcopy(source_record["_source"])
        for source_record in (osv, github, nvd, kev)
        if source_record is not None and isinstance(source_record.get("_source"), Mapping)
    ]
    return {
        "canonical_advisory_id": advisory_id,
        "aliases": aliases,
        "ecosystem": ecosystem,
        "package": package,
        "queried_version": version,
        "affected_state": affected_state,
        "affected_ranges": affected_ranges,
        "published": osv.get("published"),
        "modified": osv.get("modified"),
        "withdrawn": osv.get("withdrawn"),
        "severity": severity,
        "cwe_ids": cwe_ids,
        "kev": kev_output,
        "conflicts": conflicts,
        "missing_fields": missing_fields,
        "sources": sources,
    }


def hmda_gold_from_records(
    case: BenchmarkCase, records: Mapping[str, Any]
) -> dict[str, Any]:
    """Construct HMDA gold directly from the privacy-bounded normalized record."""

    inputs = case.inputs
    year = int(inputs["activity_year"])
    lei = str(inputs["lei"])
    row_digest = str(inputs["row_digest"])
    row = _record(records, "rows", f"{year}:{lei}:{row_digest}")
    schema = _record(records, "schemas", str(year))
    filer = _record(records, "filers", f"{year}:{lei}")
    if row is None or schema is None or filer is None:
        raise LookupError("normalized HMDA row, schema, and filer are required")
    schema_fields = set(map(str, schema.get("fields", ())))
    core_fields = {
        "action_taken",
        "loan_type",
        "loan_purpose",
        "lien_status",
        "occupancy_type",
        "derived_dwelling_category",
        "preapproval",
        *(str(field) for field in inputs.get("requested_fields", ())),
        *(f"denial_reason-{index}" for index in range(1, 5)),
    }
    if missing_schema := sorted(core_fields - schema_fields):
        raise LookupError(
            "normalized HMDA schema is missing fields: " + ", ".join(missing_schema)
        )
    definitions = records.get("definitions", {})
    if missing_definitions := sorted(
        field for field in core_fields if f"{year}:{field}" not in definitions
    ):
        raise LookupError(
            "normalized HMDA definitions are missing fields: "
            + ", ".join(missing_definitions)
        )
    if (
        str(row.get("activity_year")) != str(year)
        or str(row.get("lei")) != lei
        or str(row.get("raw_row_digest")) != row_digest
        or str(filer.get("lei")) != lei
    ):
        raise LookupError("normalized HMDA record identity is inconsistent")

    def coded(field: str, value: Any) -> dict[str, Any]:
        if field not in schema_fields:
            raise LookupError(f"HMDA field {field!r} is absent from the frozen schema")
        label = records.get("labels", {}).get(f"{year}:{field}:{value}")
        return {"code": value, "label": None if label is None else str(label)}

    fields = {
        "action_taken": "action_taken",
        "loan_type": "loan_type",
        "loan_purpose": "loan_purpose",
        "lien_status": "lien_status",
        "occupancy_type": "occupancy_type",
        "property_type": "derived_dwelling_category",
        "preapproval": "preapproval",
    }
    output: dict[str, Any] = {
        "activity_year": year,
        "filer": {"code": lei, "label": filer.get("name")},
    }
    for output_name, field in fields.items():
        output[output_name] = coded(field, row.get(field, "NA"))

    denial_reasons = []
    for index in range(1, 5):
        field = f"denial_reason-{index}"
        value = row.get(field)
        if value not in (None, "", "NA", "1111", "10"):
            denial_reasons.append(coded(field, value))

    special_states: dict[str, str] = {}
    for field in inputs.get("requested_fields", ()):
        if str(field) not in schema_fields:
            raise LookupError(f"requested HMDA field {field!r} is absent from the frozen schema")
        value = str(row.get(str(field), "UNAVAILABLE"))
        state = {
            "NA": "NA",
            "1111": "NA",
            "Exempt": "EXEMPT",
            "": "UNAVAILABLE",
            "UNAVAILABLE": "UNAVAILABLE",
        }.get(value)
        if state is not None:
            special_states[str(field)] = state
    for index in range(1, 5):
        field = f"denial_reason-{index}"
        if str(row.get(field, "")) == "10":
            special_states[field] = "NOT_APPLICABLE"

    output.update(
        {
            "denial_reasons": denial_reasons,
            "special_states": special_states,
            "privacy_notice": HMDA_PRIVACY_NOTICE,
            "sources": copy.deepcopy(list(row.get("sources", ()))),
        }
    )
    return output


def _comparable_sec_value(value: Any) -> tuple[str, str]:
    text = str(value).replace(",", "").strip()
    try:
        return "number", format(Decimal(text).normalize(), "f")
    except InvalidOperation:
        return "text", text


def _missing_sec_gold(
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


def sec_gold_from_records(
    case: BenchmarkCase, records: Mapping[str, Any]
) -> dict[str, Any]:
    """Construct SEC gold directly from normalized Company Facts and filed facts."""

    inputs = case.inputs
    cik = str(inputs["cik"]).zfill(10)
    taxonomy = str(inputs.get("taxonomy", "us-gaap"))
    concept = str(inputs["concept"])
    period_end = str(inputs["period_end"])
    as_of = str(inputs["as_of_date"])
    form = str(inputs["form"])
    date.fromisoformat(period_end)
    date.fromisoformat(as_of)

    company = _record(records, "companyfacts", cik)
    if company is None:
        return _missing_sec_gold(cik, taxonomy, concept, state="MISSING")
    filings_value = records.get("filings", {}).get(cik, ())
    filings = [item for item in filings_value if isinstance(item, Mapping)]
    applicable = [
        item
        for item in filings
        if item.get("form") in {form, f"{form}/A"}
        and str(item.get("filed_date", "")) <= as_of
        and item.get("report_date") == period_end
    ]
    if not applicable:
        return _missing_sec_gold(
            cik, taxonomy, concept, issuer=str(company.get("entityName", ""))
        )
    filing = max(
        applicable,
        key=lambda item: (str(item.get("filed_date", "")), str(item.get("accession", ""))),
    )
    accession = str(filing["accession"])
    fact = _record(records, "filing_facts", f"{accession}:{concept}:{period_end}")
    if fact is None:
        return _missing_sec_gold(
            cik, taxonomy, concept, issuer=str(company.get("entityName", ""))
        )

    concept_values = company.get("facts", {}).get(taxonomy, {}).get(concept, ())
    candidates = [
        item
        for item in concept_values
        if isinstance(item, Mapping)
        and item.get("end") == period_end
        and str(item.get("filed", "")) <= as_of
    ]
    units = {item.get("unit") for item in candidates}
    contexts = {
        (item.get("start"), item.get("end"), item.get("frame"))
        for item in candidates
    }
    state = (
        "MULTIPLE_UNITS"
        if len(units) > 1
        else "MULTIPLE_CONTEXTS"
        if len(contexts) > 1
        else "OK"
    )
    company_item = next(
        (
            item
            for item in candidates
            if item.get("accession") == accession and item.get("unit") == fact.get("unit")
        ),
        None,
    )
    agreement = "NOT_ASSESSABLE"
    if company_item is not None:
        agreement = (
            "AGREE"
            if _comparable_sec_value(company_item.get("value"))
            == _comparable_sec_value(fact.get("value"))
            else "DISAGREE"
        )
    metadata = _record(records, "filing_metadata", accession) or filing
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
        "sources": copy.deepcopy(list(fact.get("sources", ()))),
    }
