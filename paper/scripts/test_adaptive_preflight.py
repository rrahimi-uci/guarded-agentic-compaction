"""Retained-accounting and planning checks without databases or upstream packages."""
import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adaptive_source_preflight import OUT, verify
from adaptive_comparison_design import build
from probe_agent_jit_sql import PIN, PROGRAMS, registry
from audit_bird_revision import changes
from audit_bird_content_overlap import overlap


def test_retained_source_audit():
    verify(json.loads((OUT / "source_audit.json").read_text()))


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "promote", "false_summary", "failure_as_empty"])
def test_source_accounting_fails_closed(mutation):
    report = json.loads((OUT / "source_audit.json").read_text())
    if mutation == "missing":
        report["rows"].pop()
    elif mutation == "duplicate":
        report["rows"].append(copy.deepcopy(report["rows"][0]))
    elif mutation == "promote":
        report["decision"] = "READY"
    elif mutation == "false_summary":
        report["databases"][0]["screened_in"] += 1
    else:
        report["rows"][0].update(gold_status="sql_error", row_count=0, distinct_rows=0, columns=1)
    with pytest.raises(ValueError):
        verify(report)


def test_design_reproduces_and_separates_absolute_risk_from_ni():
    actual = build()
    retained = json.loads((OUT / "design_sensitivity.json").read_text())
    assert actual.keys() == retained.keys()
    for observed, expected in zip(actual["rows"], retained["rows"], strict=True):
        assert observed == pytest.approx(expected, abs=1e-12)
    assert actual["calibration"] == retained["calibration"]
    assert actual["historical_compiled_quality"] == retained["historical_compiled_quality"]
    assert actual["source_hashes"] == retained["source_hashes"]
    assert all(r["error_rate"] > .05 for r in actual["historical_compiled_quality"].values())
    assert actual["calibration"][0]["accepted_zero_error_floor"] == 92
    assert actual["calibration"][1]["accepted_zero_error_floor"] == 106


def test_upstream_probe_is_pinned_and_does_not_claim_task_correctness():
    import hashlib
    import probe_agent_jit_sql as probe
    report = json.loads((OUT / "agent_jit_probe.json").read_text())
    assert report["commit"] == PIN and report["provider_calls"] == 0
    assert report["programs"] == PROGRAMS and report["registry"] == registry()
    assert report["probe_sha256"] == hashlib.sha256(Path(probe.__file__).read_bytes()).hexdigest()
    observations = {r["path"]: r for r in report["result"]["candidates"]}
    assert observations["wrong_answer_valid_contract"]["valid"]
    assert not observations["wrong_type"]["valid"]
    assert not observations["missing_list"]["valid"]
    assert not observations["missing_schema"]["valid"]
    assert observations["redundant_query"]["estimated_cost"] > observations["valid"]["estimated_cost"]


def test_revision_changes_preserve_prior_use_and_detect_unmatched_ids():
    old = [{"question_id": 1, "db_id": "a", "SQL": "SELECT 1"}, {"question_id": 2}]
    new = [{"question_id": 1, "db_id": "a", "SQL": "SELECT 2"}, {"question_id": 3}]
    rows = changes(old, new, {1})
    assert rows[0]["previously_used"] and rows[0]["changed_fields"] == ["SQL"]
    assert rows[1]["presence"] == "old_only" and rows[2]["presence"] == "new_only"
    with pytest.raises(ValueError):
        changes(old + [old[0]], new, set())


def test_content_screen_detects_cross_id_overlap_without_cross_database_collision():
    rows = [{"question_id": 1, "db_id": "a", "question": "Which  item?"},
            {"question_id": 2, "db_id": "a", "question": "Which item?"},
            {"question_id": 3, "db_id": "b", "question": "Which item?"}]
    assert overlap(rows, {1})["screened_in_ids_matching_prior_question"] == [2]


def test_report_and_revision_accounting():
    import hashlib
    import audit_bird_revision as revision
    from render_adaptive_preflight import render
    assert render() == (OUT / "REPORT.md").read_text()
    report = json.loads((OUT / "bird_revision_audit.json").read_text())
    assert report["source_hashes"][str(Path(revision.__file__).relative_to(OUT.parents[2]))] == hashlib.sha256(Path(revision.__file__).read_bytes()).hexdigest()
    assert report["counts"]["changed"] == sum(bool(r["changed_fields"]) for r in report["rows"])
    assert report["counts"]["changed_screened_in"] == sum(bool(r["changed_fields"]) and not r["previously_used"] for r in report["rows"])
    observed = report["gold_execution"]
    assert observed["source_audit_sha256"] == hashlib.sha256((OUT / "source_audit.json").read_bytes()).hexdigest()
    expected = {r["question_id"] for r in report["rows"] if not r["previously_used"]}
    assert {r["question_id"] for r in observed["rows"]} == expected
    assert len(observed["rows"]) == len(expected)
    from collections import Counter
    assert dict(Counter(r["status"] for r in observed["rows"])) == observed["status_counts"]
