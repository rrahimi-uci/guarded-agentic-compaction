"""Fail closed on lost records, hidden exclusions, or promoted replay evidence."""
import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_calibration_population as audit
from screen_bird_comparison_sources import ids_in


@pytest.fixture
def report():
    return json.loads((audit.OUT / "report.json").read_text())


def test_retained_accounting_and_narrow_scope(report):
    audit.verify(report)
    assert sum(f["discovery_records"] for f in report["families"]) == 396
    assert sum(len(f["candidates"]) for f in report["families"]) == 5
    selected = [c for f in report["families"] for c in f["candidates"] if c["selected_artifact"]]
    assert [c["excluded_records_passing_entry_guard_and_gate"] for c in selected] == [[539, 2781], [5700], []]
    assert all(c["guard_gate_source"] == "retained_registry" for c in selected)


def test_unused_is_not_outcome_filtered():
    assert audit.disposition(True, None) == "eligible_unused"
    assert audit.disposition(False, None) == "excluded_by_discovery_filter"
    with pytest.raises(ValueError):
        audit.disposition(False, "calibration")


def test_missing_record_rejected(report):
    report["families"][0]["records"].pop()
    with pytest.raises(ValueError, match="missing or duplicate"):
        audit.validate(report)


def test_duplicate_group_rejected(report):
    rows = report["families"][0]["records"]
    rows[-1] = copy.deepcopy(rows[0])
    with pytest.raises(ValueError, match="missing or duplicate"):
        audit.validate(report)


def test_hidden_exclusion_rejected(report):
    report["families"][0]["candidates"][0]["excluded_records_passing_entry_guard_and_gate"] = []
    with pytest.raises(ValueError, match="excluded-eligible"):
        audit.validate(report)


def test_missing_family_window_not_silently_dropped(report):
    family = report["families"][0]
    candidate = family["candidates"][0]["candidate_id"]
    row = next(r for r in family["records"] if r["disposition"] == "calibration")
    row["candidates"][candidate]["historical_label_count"] = 0
    with pytest.raises(ValueError, match="missing-window"):
        audit.validate(report)


def test_split_leakage_rejected(report):
    family = report["families"][0]
    family["split_manifest"]["groups"]["test"] = [family["records"][0]["group_id"]]
    with pytest.raises(ValueError, match="split membership"):
        audit.validate(report)


def test_replay_not_promoted_to_continuation(report):
    row = report["families"][0]["records"][0]
    next(iter(row["candidates"].values()))["final_continuation_calibrated"] = True
    with pytest.raises(ValueError, match="replay labels"):
        audit.validate(report)


def test_no_new_certificate(report):
    report["new_certificate"] = True
    with pytest.raises(ValueError, match="must not claim"):
        audit.validate(report)


def test_consistent_but_false_saved_gate_score_rejected(report):
    row = report["families"][0]["records"][0]
    next(iter(row["candidates"].values()))["score"] += 0.1
    with pytest.raises(ValueError, match="eligibility does not reproduce"):
        audit.verify(report)


def test_bird_screen_includes_failed_and_unexecuted_selected_ids():
    source = {"results": [{"issue_number": 3}], "failures": [{"question_id": 4}],
              "selections": {"db": {"discovery": [5, 6], "test": [7], "pool": 100}},
              "requests": 20, "question_id": True}
    assert ids_in(source) == {3, 4, 5, 6, 7}
