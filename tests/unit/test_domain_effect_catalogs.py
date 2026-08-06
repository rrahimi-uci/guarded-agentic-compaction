from __future__ import annotations

import inspect
from pathlib import Path

from guarded_agentic_compaction.schema.effects import EffectCatalog
from benchmarks.adapters.hmda_public_lar import HmdaSnapshot
from benchmarks.adapters.sec_filing_facts import SecSnapshot
from benchmarks.adapters.vulnerability_evidence import VulnerabilitySnapshot


ROOT = Path(__file__).resolve().parents[2]


def _assert_catalog_matches(domain: str, facade: type, expected: set[str]) -> None:
    catalog = EffectCatalog.from_yaml(ROOT / f"benchmarks/contracts/effects/{domain}.yaml")
    assert set(catalog.tools) == expected
    for name, declaration in catalog.tools.items():
        method = getattr(facade, name)
        signature = inspect.signature(method)
        actual = set(signature.parameters) - {"self"}
        assert set(declaration.key) == actual
        assert declaration.compilable


def test_domain_effect_catalogs_match_facade_signatures() -> None:
    _assert_catalog_matches(
        "vulnerability",
        VulnerabilitySnapshot,
        {
            "get_osv_advisory",
            "query_osv_package_version",
            "get_github_advisory",
            "get_nvd_record",
            "get_kev_record",
        },
    )
    _assert_catalog_matches(
        "sec",
        SecSnapshot,
        {
            "get_sec_submissions",
            "get_sec_companyfacts",
            "list_applicable_filings",
            "read_filing_xbrl_fact",
            "read_filing_metadata",
        },
    )
    _assert_catalog_matches(
        "hmda",
        HmdaSnapshot,
        {
            "get_public_lar_record",
            "get_hmda_public_schema",
            "get_hmda_field_definition",
            "get_hmda_filer",
            "get_hmda_code_label",
        },
    )
