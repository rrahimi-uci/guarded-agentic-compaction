"""Exercise the pinned external parser against selected SEC fact edge cases."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

from benchmarks.adapters.store import FrozenRecordStore
from benchmarks.audit_sec_edgartools import audit_pool, check_observation
from benchmarks.build.sec_pool import SCHEMA
from paper.scripts.validate_multidomain import validate_sec_edgartools_attestation


CIK = "0000000001"
ACCESSION = "0000000001-25-000001"
RAW_FACT = {
    "start": "2024-01-01", "end": "2024-12-31", "val": 123,
    "accn": ACCESSION, "fy": 2024, "fp": "FY", "form": "10-K",
    "filed": "2025-02-01", "frame": "CY2024",
}


def _sample():
    raw = {
        "cik": 1, "entityName": "Example Inc",
        "facts": {"us-gaap": {"Revenues": {
            "label": "Revenues", "description": "Revenue in period",
            "units": {"USD": [RAW_FACT]},
        }}},
    }
    source = {
        "entityName": "Example Inc",
        "facts": {"us-gaap": {"Revenues": [{
            "taxonomy": "us-gaap", "concept": "Revenues", "unit": "USD",
            "start": "2024-01-01", "end": "2024-12-31", "value": 123,
            "accession": ACCESSION, "filed": "2025-02-01", "form": "10-K",
        }]}},
    }
    filed = {"start": "2024-01-01", "end": "2024-12-31", "unit": "USD", "value": "123.0"}
    params = dict(cik=CIK, taxonomy="us-gaap", concept="Revenues",
                  accession=ACCESSION, period_end="2024-12-31", as_of_date="2025-02-01")
    return raw, source, filed, params


def test_external_parser_confirms_period_unit_accession_and_numeric_value():
    raw, source, filed, params = _sample()
    assert check_observation(raw, source, filed, **params)["status"] == "pass"
    changed = deepcopy(raw)
    changed["facts"]["us-gaap"]["Revenues"]["units"]["USD"][0]["val"] = 124
    assert check_observation(changed, source, filed, **params)["reason"] == "edgartools_observation_ambiguous_or_missing"
    duplicate = deepcopy(raw)
    duplicate["facts"]["us-gaap"]["Revenues"]["units"]["USD"].append(deepcopy(RAW_FACT))
    result = check_observation(duplicate, source, filed, **params)
    assert result["status"] == "fail" and result["matching_observations"] == 2
    per_share = deepcopy(raw)
    per_share["facts"]["us-gaap"]["Revenues"]["units"] = {"USD/shares": [deepcopy(RAW_FACT)]}
    per_share_source = deepcopy(source)
    per_share_source["facts"]["us-gaap"]["Revenues"][0]["unit"] = "USD/shares"
    per_share_filed = {**filed, "unit": "USD/shares"}
    assert check_observation(per_share, per_share_source, per_share_filed, **params)["status"] == "pass"
    params["as_of_date"] = "2025-01-31"
    assert check_observation(raw, source, filed, **params)["reason"] == "observation_postdates_as_of"


def test_pool_audit_checks_raw_digest_and_never_requests_network(tmp_path: Path, monkeypatch):
    raw, source, filed, params = _sample()
    data = (json.dumps(raw) + "\n").encode()
    raw_path = tmp_path / "companyfacts.json"
    raw_path.write_bytes(data)
    raw_digest = hashlib.sha256(data).hexdigest()
    source["_source"] = {"snapshot_digest": raw_digest}
    records = {
        "companyfacts": {CIK: source},
        "filing_facts": {f"{ACCESSION}:Revenues:2024-12-31": filed},
    }
    store = FrozenRecordStore(records)
    pool = tmp_path / "pool"
    pool.mkdir()
    (pool / "snapshot.json").write_text(json.dumps({
        "schema": SCHEMA, "snapshot_digest": f"sha256:{store.snapshot_digest}", "records": records,
    }))
    (pool / "cases.jsonl").write_text(json.dumps({
        "case_id": "sec-example", "domain": "sec", "source_snapshot": f"sha256:{store.snapshot_digest}",
        "inputs": {key: params[key] for key in ("cik", "taxonomy", "concept", "period_end", "as_of_date")},
        "metadata": {"lineage_ids": [CIK, ACCESSION]},
    }) + "\n")
    calls = []
    def cached_fetch(cik, cache_dir, *, offline):
        calls.append((cik, cache_dir, offline))
        return {"companyfacts": SimpleNamespace(path=str(raw_path), sha256=raw_digest)}
    monkeypatch.setattr("benchmarks.audit_sec_edgartools.fetch_issuer_sources", cached_fetch)
    report = audit_pool(pool, tmp_path)
    assert report["valid"] and report["passed_cases"] == 1
    assert report["provider_calls_executed"] == 0 and calls == [(CIK, tmp_path, True)]
    binding = {
        "edgartools_audit": {
            "artifact_sha256": hashlib.sha256((pool / "edgartools_audit.json").read_bytes()).hexdigest(),
            "snapshot_digest": report["snapshot_digest"],
            "cases_sha256": report["cases_sha256"],
        }
    }
    snapshot = json.loads((pool / "snapshot.json").read_text())
    cases = [json.loads((pool / "cases.jsonl").read_text())]
    assert validate_sec_edgartools_attestation(pool, binding, snapshot, cases) == []
    bad_binding = deepcopy(binding)
    bad_binding["edgartools_audit"]["artifact_sha256"] = "0" * 64
    assert validate_sec_edgartools_attestation(pool, bad_binding, snapshot, cases)

    source["_source"]["snapshot_digest"] = "0" * 64
    records["companyfacts"][CIK] = source
    store = FrozenRecordStore(records)
    payload = json.loads((pool / "snapshot.json").read_text())
    payload["records"] = records
    payload["snapshot_digest"] = f"sha256:{store.snapshot_digest}"
    (pool / "snapshot.json").write_text(json.dumps(payload))
    case = json.loads((pool / "cases.jsonl").read_text())
    case["source_snapshot"] = f"sha256:{store.snapshot_digest}"
    (pool / "cases.jsonl").write_text(json.dumps(case) + "\n")
    report = audit_pool(pool, tmp_path)
    assert not report["valid"] and report["results"][0]["reason"].startswith("ValueError: cached SEC response")
