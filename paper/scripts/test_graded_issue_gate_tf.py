"""Provider-free invariants for the fresh-issue single-look feasibility preflight and its audit."""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "paper/scripts"))

import audit_graded_issue_gate_tf as audit  # noqa: E402
import graded_issue_gate_study as study  # noqa: E402
import graded_issue_gate_tf_preflight as pf  # noqa: E402
import github_live_study as fixed  # noqa: E402


def test_max_admissible_k_matches_the_registered_floors() -> None:
    # flip-plans.md A.3 (registered grid, m = 1)
    expected = {92: 0, 106: 0, 132: 0, 150: 1, 200: 3, 300: 6, 400: 9, 800: 25}
    assert {n: pf.max_admissible_k(n) for n in expected} == expected
    assert pf.max_admissible_k(91) == -1
    assert pf.max_admissible_k(0) == -1
    assert {n: audit.independent_max_k(n) for n in expected} == expected


def test_admission_probability_is_a_binomial_cdf() -> None:
    assert pf.admission_probability(10, -1, 0.1) == 0.0
    assert pf.admission_probability(10, 0, 0.1) == pytest.approx(0.9**10)
    assert pf.admission_probability(2, 2, 0.3) == pytest.approx(1.0)


def test_descriptors_match_the_study_read_at_the_pinned_cutoff() -> None:
    store, _ = fixed.build_store(pd.read_parquet(pf.SNAPSHOT))
    sample = [r for r in store.values() if r["comments"]][:40]
    for row in sample:
        features, _ = study.risk_read(store, row["number"])
        assert pf.descriptors(row, date.fromisoformat(pf.PINNED_AGE_CUTOFF)) == features
    # the literal fixed cutoff gives every post-cutoff issue age zero; the snapshot-relative one does not
    assert all(pf.descriptors(r, date.fromisoformat(pf.PINNED_AGE_CUTOFF))["age_years"] == 0.0 for r in sample)
    assert any(pf.descriptors(r, date(2026, 10, 7))["age_years"] > 0.0 for r in sample)


def test_used_records_applies_field_and_broad_rules_and_skips_own_and_dataset_dirs(tmp_path: Path) -> None:
    (tmp_path / "studies").mkdir()
    (tmp_path / "studies" / "a.json").write_text(json.dumps({"rows": [{"issue_number": 11}, {"record_number": 12}]}))
    (tmp_path / "studies" / "b.json").write_text(json.dumps({"excluded_ids": [13, 14], "other": [15]}))
    (tmp_path / "graded_issue_gate_tf").mkdir()
    (tmp_path / "graded_issue_gate_tf" / "own.json").write_text(json.dumps({"issue_number": 16}))
    (tmp_path / "datasets").mkdir()
    (tmp_path / "datasets" / "m.json").write_text(json.dumps({"issue_number": 17}))
    field, broad = pf.used_records(set(range(10, 20)), roots=(tmp_path,), base=tmp_path)
    assert set(field) == {11, 12}
    assert set(broad) == {11, 12, 13, 14}


def test_retained_preflight_equals_a_provider_free_rebuild_and_is_no_go() -> None:
    retained = json.loads(pf.OUT.read_text())
    assert retained == pf.build()
    assert retained["provider_calls_executed"] == 0
    assert retained["status"] == "no_go_pool_too_small" and retained["no_go"] is True
    assert retained["no_go_even_under_same_record_space_rule"] is True
    pool = retained["pool_accounting"]
    assert pool["issues_with_at_least_one_comment"] == 197 and pool["pool_same_record_space_rule"] >= pool["pool_literal_rule"]
    for design in retained["design"].values():
        assert design["calibration_groups"] < pf.MIN_CALIBRATION_GROUPS
    assert retained["frozen_gate_v2_sha256"] == pf.sha256(pf.FROZEN_GATE)


def test_audit_regenerates_the_committed_table_and_snippet() -> None:
    result = audit.audit()
    assert result["provider_side_artifacts_present"] == [] and result["floors_match_independent_bisection"] is True
    retained = json.loads(pf.OUT.read_text())
    assert audit.TABLE_PATH.read_text() == audit.table(retained)
    assert audit.SNIPPET_PATH.read_text() == audit.snippet(retained)
