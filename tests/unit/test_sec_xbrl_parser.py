from __future__ import annotations

import pytest

from agent_compaction.evaluation import BenchmarkCase
from benchmarks.adapters.sec_filing_facts import SecSnapshot, sec_macro
from benchmarks.adapters.store import FrozenRecordStore
from benchmarks.build.sec_pool import parse_xbrl_instance, select_instance_filename
from benchmarks.fetch.common import SourceFetchError
from benchmarks.gold import sec_gold_from_records


INSTANCE = b'''<?xml version="1.0"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
 xmlns:xbrli="http://www.xbrl.org/2003/instance"
 xmlns:us-gaap="http://fasb.org/us-gaap/2024"
 xmlns:iso4217="http://www.xbrl.org/2003/iso4217">
 <context id="c1"><entity><identifier scheme="x">1</identifier></entity><period><instant>2024-12-31</instant></period></context>
 <unit id="usd"><measure>iso4217:USD</measure></unit>
 <us-gaap:Assets contextRef="c1" unitRef="usd">123.00</us-gaap:Assets>
</xbrl>'''


def test_parse_standard_xbrl_instance_preserves_context_and_unit() -> None:
    parsed = parse_xbrl_instance(INSTANCE)
    assert parsed["facts"] == [{
        "taxonomy": "us-gaap", "concept": "Assets", "value": "123.00",
        "unit": "USD", "start": None, "end": "2024-12-31", "context_id": "c1",
    }]


def test_instance_selection_rejects_ambiguous_xml() -> None:
    with pytest.raises(SourceFetchError, match="unique"):
        select_instance_filename({"directory": {"item": [
            {"name": "a.xml", "type": "XML"}, {"name": "b.xml", "type": "XML"}
        ]}})


def test_instance_selection_prefers_explicit_ex101() -> None:
    assert select_instance_filename({"directory": {"item": [
        {"name": "a.xml", "type": "EX-101.INS"},
        {"name": "a_cal.xml", "type": "EX-101.CAL"},
    ]}}) == "a.xml"


def test_malformed_xbrl_and_numeric_lexical_variants_are_handled_exactly() -> None:
    with pytest.raises(SourceFetchError, match="well-formed"):
        parse_xbrl_instance(b"<xbrl><broken></xbrl>")

    cik = "0000000001"
    accession = "0000000001-24-000001"
    records = {
        "submissions": {},
        "companyfacts": {
            cik: {
                "entityName": "Example Issuer",
                "facts": {
                    "us-gaap": {
                        "Assets": [
                            {
                                "end": "2024-12-31",
                                "filed": "2025-01-31",
                                "accession": accession,
                                "unit": "USD",
                                "value": "123",
                                "start": None,
                                "frame": "CY2024Q4I",
                            }
                        ]
                    }
                },
            }
        },
        "filings": {
            cik: [
                {
                    "accession": accession,
                    "filed_date": "2025-01-31",
                    "report_date": "2024-12-31",
                    "form": "10-K",
                }
            ]
        },
        "filing_facts": {
            f"{accession}:Assets:2024-12-31": {
                "value": "123.0",
                "unit": "USD",
                "start": None,
                "end": "2024-12-31",
                "fiscal_year": 2024,
                "fiscal_period": "FY",
                "sources": [],
            }
        },
        "filing_metadata": {
            accession: {
                "form": "10-K",
                "filed_date": "2025-01-31",
                "report_date": "2024-12-31",
            }
        },
    }
    store = FrozenRecordStore(records)
    case = BenchmarkCase(
        case_id="sec-numeric",
        group_id=cik,
        domain="sec",
        source_snapshot=f"sha256:{store.snapshot_digest}",
        inputs={
            "cik": cik,
            "taxonomy": "us-gaap",
            "concept": "Assets",
            "period_end": "2024-12-31",
            "as_of_date": "2025-01-31",
            "form": "10-K",
        },
    )
    output = sec_macro(case, SecSnapshot(store))
    assert output["companyfacts_filing_agreement"] == "AGREE"
    assert sec_gold_from_records(case, records) == output
