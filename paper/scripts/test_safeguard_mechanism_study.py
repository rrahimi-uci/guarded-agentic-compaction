"""Behavioral checks for mechanism isolation, task consequences and evidence seals."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import safeguard_mechanism_study as study


def store(n=12):
    return {i: {"title": f"Issue {i}", "comments": ["first", "ERROR here", "third", "error four", "fifth"]}
            for i in range(1, n + 1)}


def candidate():
    return study.discover([1, 2, 3, 4], store())[0]


def case(limit=3, suite="ordinary", number=10):
    return next(c for c in study.cases([number]) if c["requested_limit"] == limit and c["suite"] == suite)


def test_selection_is_disjoint_deterministic_and_does_not_filter_empty_comments():
    data = store(40)
    for row in data.values():
        row["comments"] = []
    data[40]["pull_request"] = True
    sizes = dict.fromkeys(study.SIZES, 4)
    selected = study.select(data, {1, 2, 3}, sizes)
    ids = [n for split in selected.values() for n in split]
    assert len(set(ids)) == 16
    assert not set(ids) & {1, 2, 3, 40}
    assert selected == study.select(dict(reversed(list(data.items()))), {1, 2, 3}, sizes)
    with pytest.raises(ValueError, match="insufficient"):
        study.select(data, set(), dict.fromkeys(study.SIZES, 20))


def test_discovery_binding_is_fresh_and_invariant_limit_is_literal():
    artifact, observations = study.discover([1, 2, 3, 4], store())
    assert artifact.program.steps[0].args["issue_number"].to_dict()["kind"] == "expr"
    assert artifact.program.steps[1].args["limit"].to_dict() == {"kind": "const", "value": 3}
    assert len(observations) == 4
    assert artifact.guard.clauses[1].hull.contains(3)
    assert not artifact.guard.clauses[1].hull.contains(5)


@pytest.mark.parametrize("arm,component", [("no_entry_hull", "guard"),
    ("no_completeness_check", "verifier"), ("no_statistical_gate", "gate")])
def test_exactly_one_component_changes_and_original_is_immutable(arm, component):
    original = candidate()
    # Give it actual calibration metadata so gate ablation must clear it.
    original.gate.n_accepted = 192
    original.gate.risk_upper_bound = .03
    before = copy.deepcopy(original.to_dict())
    changed = study.arm_artifact(original, arm).to_dict()
    assert original.to_dict() == before
    assert {k for k in before if before[k] != changed[k]} == {component}
    if component == "guard":
        assert changed[component]["manifest_pins"] == before[component]["manifest_pins"]
        assert changed[component]["clauses"][1]["type_name"] == "int"
        assert changed[component]["clauses"][1]["required"]
    if component == "verifier":
        assert changed[component]["allowed_effects"] == before[component]["allowed_effects"]
        assert changed[component]["call_counts"] == before[component]["call_counts"]
        assert len(changed[component]["clauses"]) == len(before[component]["clauses"]) - 1
    if component == "gate":
        assert changed[component]["n_accepted"] == 0
        assert changed[component]["risk_upper_bound"] == 1
        assert changed[component]["alpha"] == 1


def test_guard_ablation_changes_a_task_answer_and_not_just_a_decision():
    art, data = candidate(), store()
    full = study.execute(case(5), "full", art, data)
    ablated = study.execute(case(5), "no_entry_hull", art, data)
    assert full["correct"] and full["fallback"]
    assert ablated["dispatched"] and not ablated["correct"]
    assert full["answer"] == {"issue_number": 10, "comment_count": 5, "matching_positions": [2, 4]}
    assert ablated["answer"] == {"issue_number": 10, "comment_count": 3, "matching_positions": [2]}


def test_verifier_ablation_partial_page_and_fallback_call_accounting():
    art, data = candidate(), store()
    c = case(3, "capped_response_stress")
    baseline = study.execute(c, "baseline", art, data)
    full = study.execute(c, "full", art, data)
    ablated = study.execute(c, "no_completeness_check", art, data)
    assert baseline["correct"] and baseline["tool_calls"] == 3
    assert full["correct"] and full["fallback"] and full["tool_calls"] == 5
    assert full["reasons"] == ["range:page.complete"]
    assert ablated["dispatched"] and not ablated["correct"]
    assert ablated["tool_calls"] == 2
    assert ablated["answer"]["comment_count"] == 2
    # Both arms see the same initial cap; fallback gets no privileged full read.
    assert full["calls"][:2] == ablated["calls"]


def test_harmless_refusal_is_not_counted_as_protection():
    art, data = candidate(), store()
    a = study.execute(case(1), "full", art, data)
    b = study.execute(case(1), "no_entry_hull", art, data)
    assert not a["dispatched"] and b["dispatched"]
    assert a["correct"] and b["correct"]


@pytest.mark.parametrize("comments", [[], ["ERROR"], ["normal", "error ERROR"]])
def test_empty_and_short_sources_are_retained_and_baseline_matches_independent_oracle(comments):
    data = store()
    data[10]["comments"] = comments
    for c in study.cases([10]):
        result = study.execute(c, "baseline", candidate(), data)
        assert result["correct"]
        assert result["answer"]["comment_count"] == min(len(comments), c["requested_limit"])


def test_gate_retirement_and_group_counts_use_distinct_issues():
    data, art = store(), candidate()
    calibrated, audit = study.fit_and_calibrate(art, {"development": [5, 6], "calibration": [7, 8, 9]}, data)
    assert len(audit["calibration"]) == 9
    assert calibrated.gate.n_calibration_groups == 3
    assert calibrated.gate.retire
    assert audit["eligible_development_feature_vectors"] == 1
    assert all(r["accepted_groups"] <= 3 for r in audit["grid"])


def test_summary_keeps_failed_cases_and_does_not_pool_suites(monkeypatch):
    art, data = candidate(), store()
    selected = study.cases([10])
    rows = [study.execute(c, arm, art, data) for c in selected for arm in study.ARMS]
    report = study.summarize(selected, rows)
    ordinary = report["suites"]["ordinary"]
    assert ordinary["issue_groups"] == 1
    assert ordinary["arms"]["full"]["scheduled"] == 3
    assert ordinary["paired_vs_full"]["no_entry_hull"]["full_only_correct"] == 1
    assert ordinary["paired_vs_full"]["no_entry_hull"]["dispatch_disagreements"] == 2
    stress = report["suites"]["capped_response_stress"]
    assert stress["paired_vs_full"]["no_completeness_check"]["full_only_correct_groups"] == 1
    rows[0].update(status="failed", correct=False, answer=None)
    report = study.summarize(selected, rows)
    assert report["status"] == "completed_with_failures"
    assert report["suites"]["ordinary"]["arms"]["baseline"]["failed"] == 1
    with pytest.raises(ValueError, match="matrix"):
        study.summarize(selected, rows[:-1])
    with pytest.raises(ValueError, match="matrix"):
        study.summarize(selected, rows + [rows[0]])


def test_tool_exception_is_retained_with_attempted_calls(monkeypatch):
    art = candidate()
    broken = store()
    del broken[10]["title"]
    result = study.execute(case(), "full", art, broken)
    assert result["status"] == "failed"
    assert not result["correct"]
    assert result["tool_calls"] >= 1


def test_seals_are_exclusive(tmp_path):
    p = tmp_path / "seal.json"
    study.save_new(p, {"frozen": True})
    with pytest.raises(FileExistsError):
        study.save_new(p, {"frozen": False})
    assert json.loads(p.read_text()) == {"frozen": True}


def test_retirement_stops_before_test_and_existing_attempt_cannot_resume(monkeypatch, tmp_path):
    splits = {"discovery": [1, 2, 3, 4], "development": [5, 6], "calibration": [7, 8, 9], "test": [10]}
    seal = {"splits": splits, "test_cases": study.cases([10])}
    study.save_new(tmp_path / "seal.json", seal)
    monkeypatch.setattr(study, "verify_seal", lambda _: (seal, store()))
    result = study.run(tmp_path)
    assert result["status"] == "retired_before_test"
    assert result["held_out_cases_executed"] == 0
    assert not (tmp_path / "run/outcomes.jsonl").exists()
    assert study.verify(tmp_path)["verified"]
    with pytest.raises(FileExistsError):
        study.run(tmp_path)


def test_completed_run_replays_and_detects_tampering_even_with_updated_hash(monkeypatch, tmp_path):
    splits = {"discovery": [1, 2, 3, 4], "development": [5, 6],
              "calibration": list(range(7, 107)), "test": [107, 108]}
    seal = {"splits": splits, "test_cases": study.cases(splits["test"])}
    study.save_new(tmp_path / "seal.json", seal)
    monkeypatch.setattr(study, "verify_seal", lambda _: (seal, store(108)))
    report = study.run(tmp_path)
    assert report["status"] == "completed"
    assert study.verify(tmp_path)["verified"]
    assert report["suites"]["ordinary"]["paired_vs_full"]["no_statistical_gate"]["dispatch_disagreements"] == 0
    path = tmp_path / "run/outcomes.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["answer"]["comment_count"] = 999
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    with pytest.raises(ValueError, match="digest mismatch"):
        study.verify(tmp_path)
    report["input_hashes"]["outcomes.jsonl"] = study.digest(path)
    (tmp_path / "run/summary.json").write_text(json.dumps(report))
    with pytest.raises(ValueError, match="replay mismatch"):
        study.verify(tmp_path)


def test_verify_seal_checks_code_before_loading_source(monkeypatch, tmp_path):
    study.save_new(tmp_path / "seal.json", {"code_hashes": {"fake": "old"}})
    monkeypatch.setattr(study, "code_hashes", lambda: {"fake": "new"})
    monkeypatch.setattr(study, "load_source", lambda: pytest.fail("must stop before source load"))
    with pytest.raises(ValueError, match="seal mismatch"):
        study.verify_seal(tmp_path)
