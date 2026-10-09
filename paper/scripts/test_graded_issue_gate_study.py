"""Provider-free invariants for the prospective graded issue gate study."""
from __future__ import annotations

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "paper/scripts"))

import graded_issue_gate_preflight as cohort  # noqa: E402
import graded_issue_gate_study as study  # noqa: E402


def test_own_checkpoint_cannot_change_sealed_cohort(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cohort.prior, "RESULTS_ROOT", tmp_path)
    earlier = tmp_path / "earlier"
    earlier.mkdir()
    (earlier / "results.json").write_text('{"issue_number": 101}\n')
    own = tmp_path / "graded_issue_gate"
    own.mkdir()
    (own / "checkpoint.json").write_text('{"issue_number": 202}\n')
    assert cohort.prior_record_numbers() == {101}


def test_wrong_answer_is_a_violation_only_after_real_dispatch() -> None:
    number = 4242
    store = {number: {
        "number": number, "title": "Parser issue", "state": "open",
        "body": "body", "labels": ["bug"], "comments": ["Thanks for reporting."],
        "html_url": "https://example.invalid/issues/4242", "day": "2025-01-01",
    }}
    wrong = {
        "issue_number": number, "title": "incorrect", "state": "open",
        "category": "bug", "evidence_label": "bug", "comment_evidence": "Thanks",
    }
    base = {"issue_number": number, "answer": wrong, "tool_sequence": ["issue_get_record"],
            "quality": {"overall": False}}
    dispatched = study.group_samples([{**base, "dispatch": {"compacted": 1}}], store)[0]
    refused = study.group_samples([{**base, "dispatch": {"compacted": 0}}], store)[0]
    assert dispatched.eligible and dispatched.violation and dispatched.unproductive
    assert not refused.eligible and not refused.violation
    assert set(dispatched.features) == set(study.FEATURE_NAMES)


def test_sealed_cohort_matches_current_source_and_prior_exclusions() -> None:
    assert json.loads(cohort.OUT.read_text()) == cohort.build()


def test_interrupted_paid_batch_cannot_be_silently_retried(monkeypatch, tmp_path: Path) -> None:
    checkpoint_path = tmp_path / "checkpoint.json"
    monkeypatch.setattr(study, "CHECKPOINT", checkpoint_path)
    state = study._checkpoint("sealed-sha", 200.0)
    state["pending_batch"] = {"phase": "development_compiled", "issue_numbers": [4242]}
    checkpoint_path.write_text(json.dumps(state))
    import pytest

    with pytest.raises(ValueError, match="interrupted provider batch"):
        study._checkpoint("sealed-sha", 200.0)
