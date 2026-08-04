"""End-to-end exact audit of the retained 420-group real HMDA pool."""

from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path

import pytest

from agent_compaction.benchmarking import freeze_protocol, load_case_jsonl
from agent_compaction.evaluation import BenchmarkCase, BenchmarkRole
from benchmarks.adapters.hmda_public_lar import HmdaSnapshot, hmda_macro
from benchmarks.adapters.store import FrozenRecordStore
from benchmarks.adapters.store import SnapshotError, canonical
from benchmarks.build.hmda_pool import SAFE_ROW_FIELDS, reseal_normalized_pool
from benchmarks.gold import hmda_gold_from_records
from benchmarks.oracles import ExactObjectOracle


ROOT = Path(__file__).resolve().parents[2]
POOL = ROOT / "paper/results/multidomain/preflight/hmda"


def _gold() -> dict[str, dict]:
    return {
        item["case_id"]: item["output"]
        for item in map(json.loads, (POOL / "gold.jsonl").read_text().splitlines())
    }


def test_real_hmda_pool_meets_size_cohort_and_privacy_gates() -> None:
    report = json.loads((POOL / "report.json").read_text())
    assert report["real_public_records"] is True
    assert report["provider_calls_executed"] == 0
    assert report["selected_groups"] == 420
    assert set(report["selected_years"]) == {"2023", "2024"}
    assert set(report["selected_actions"]) == set("12345678")
    assert report["variable_path_fraction"] >= 0.10
    assert report["protected_demographic_fields_exposed_to_tools"] is False
    assert report["gold_construction"]["independent_from_macro"] is True
    assert report["gold_construction"]["cases"] == 420

    snapshot = json.loads((POOL / "snapshot.json").read_text())
    forbidden_fragments = ("applicant_", "co-applicant_", "derived_race", "derived_sex", "derived_ethnicity")
    for row in snapshot["records"]["rows"].values():
        assert not any(
            any(fragment in field for fragment in forbidden_fragments)
            for field in row
        )
    for schema in snapshot["records"]["schemas"].values():
        assert schema["fields"] == list(SAFE_ROW_FIELDS)
        assert not any(
            any(fragment in field for fragment in forbidden_fragments)
            for field in schema["fields"]
        )
    assert report["agent_visible_schema_fields"] == list(SAFE_ROW_FIELDS)


def test_all_420_hmda_outputs_recompute_exactly_and_freeze_without_leakage() -> None:
    cases = load_case_jsonl(POOL / "cases.jsonl")
    assert len(cases) == len({case.group_id for case in cases}) == 420
    store = FrozenRecordStore.load(
        POOL / "snapshot.json", schema="agent-compaction-hmda-snapshot/v1"
    )
    tools = HmdaSnapshot(store)
    retained_gold = _gold()
    raw_snapshot = json.loads((POOL / "snapshot.json").read_text())
    assert all(
        hmda_gold_from_records(case, raw_snapshot["records"])
        == retained_gold[case.case_id]
        for case in cases
    )
    oracle = ExactObjectOracle(
        ROOT / "benchmarks/contracts/hmda_record.schema.json", retained_gold
    )
    results = [oracle.evaluate(case, hmda_macro(case, tools)) for case in cases]
    assert all(result.passed for result in results)

    protocol = freeze_protocol(
        study_id="hmda-real-pool-audit",
        seed=20260804,
        config_digest="audit-config",
        source_digests={"hmda": cases[0].source_snapshot},
        cases_by_domain={"hmda": cases},
        role_counts={
            BenchmarkRole.DISCOVERY: 40,
            BenchmarkRole.DEVELOPMENT: 30,
            BenchmarkRole.ARTIFACT_CALIBRATION: 100,
            BenchmarkRole.PORTFOLIO_CALIBRATION: 75,
            BenchmarkRole.TEST: 100,
        },
        reserve_groups=75,
    )
    assert len(protocol.group_roles["hmda"]) == 420


def test_hmda_oracle_rejects_wrong_field_source_and_fabricated_claim() -> None:
    cases = load_case_jsonl(POOL / "cases.jsonl")
    case = cases[0]
    gold = _gold()
    oracle = ExactObjectOracle(ROOT / "benchmarks/contracts/hmda_record.schema.json", gold)

    wrong = dict(gold[case.case_id])
    wrong["action_taken"] = {"code": "1", "label": "Fabricated"}
    assert not oracle.evaluate(case, wrong).passed

    wrong_source = json.loads(json.dumps(gold[case.case_id]))
    wrong_source["sources"][0]["record_id"] = "wrong-row"
    result = oracle.evaluate(case, wrong_source)
    assert not result.passed and "sources" in result.failed_fields

    fabricated = dict(gold[case.case_id])
    fabricated["fair_lending_conclusion"] = "compliant"
    result = oracle.evaluate(case, fabricated)
    assert not result.passed
    assert any("Additional properties" in error for error in result.errors)


def test_hmda_missing_schema_and_snapshot_schema_drift_fail_closed(tmp_path: Path) -> None:
    case = load_case_jsonl(POOL / "cases.jsonl")[0]
    raw = json.loads((POOL / "snapshot.json").read_text())
    records = json.loads(json.dumps(raw["records"]))
    records["schemas"].pop(str(case.inputs["activity_year"]))
    digest = hashlib.sha256(canonical(records).encode()).hexdigest()
    mutated_case = BenchmarkCase(
        case_id=case.case_id,
        group_id=case.group_id,
        domain=case.domain,
        source_snapshot=f"sha256:{digest}",
        inputs=case.inputs,
        metadata=case.metadata,
    )
    with pytest.raises(LookupError, match="schema"):
        hmda_macro(
            mutated_case,
            HmdaSnapshot(FrozenRecordStore(records, snapshot_digest=digest)),
        )

    drifted = tmp_path / "snapshot.json"
    drifted.write_text(
        json.dumps({**raw, "schema": "agent-compaction-hmda-snapshot/v2"}),
        encoding="utf-8",
    )
    with pytest.raises(SnapshotError, match="unsupported"):
        FrozenRecordStore.load(drifted, schema="agent-compaction-hmda-snapshot/v1")


def test_hmda_provider_free_reseal_is_idempotent(tmp_path: Path) -> None:
    pool = tmp_path / "hmda"
    pool.mkdir()
    for name in ("cases.jsonl", "gold.jsonl", "snapshot.json", "report.json"):
        shutil.copy2(POOL / name, pool / name)
    first = reseal_normalized_pool(pool)
    first_hashes = {
        name: hashlib.sha256((pool / name).read_bytes()).hexdigest()
        for name in ("cases.jsonl", "gold.jsonl", "snapshot.json", "report.json")
    }
    second = reseal_normalized_pool(pool)
    second_hashes = {
        name: hashlib.sha256((pool / name).read_bytes()).hexdigest()
        for name in ("cases.jsonl", "gold.jsonl", "snapshot.json", "report.json")
    }
    assert first == second
    assert first_hashes == second_hashes
