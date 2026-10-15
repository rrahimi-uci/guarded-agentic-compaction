"""Offline checks for prospective selection, arm isolation and honest accounting."""
from __future__ import annotations

import asyncio
import copy
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fresh_safeguard_comparison as study


def frozen(n=24):
    ids = list(range(100, 100 + n))
    return {"test_ids": ids, "schedule": study.schedule(ids)}


def outcome(number, arm, *, correct=True, dispatched=False, status="completed"):
    return {"issue_number": number, "arm": arm, "status": status,
            "quality": {"factuality_exact": correct}, "dispatched": dispatched,
            "metrics": {metric: 0.001 for metric in study.METRICS},
            "answer": {}, "tool_sequence": [], "tool_arguments": [], "trace_id": "fixture"}


def test_prior_selections_and_raw_rows_are_excluded():
    value = {"results": [{"issue_number": 101}, {"record_number": 102}],
             "selection": {"test": [103, 104], "discovery": [{"issue_number": 105}]},
             "held_out_record_numbers": [106], "group_id": "github-natural-issue:107",
             "metrics": {"requests": 108}, "other_list": [109]}
    assert study.used_ids(value) == set(range(101, 108))


def test_selection_does_not_condition_on_quality_or_dispatch():
    store = {i: {"pull_request": False, "quality": False, "comments": [], "labels": []}
             for i in range(1, 81)}
    store[80]["pull_request"] = True
    chosen = study.select_records(store, set(range(1, 20)), 24, 1)
    assert len(set(chosen)) == 24
    assert not set(chosen) & (set(range(1, 20)) | {80})
    assert chosen == study.select_records(dict(reversed(list(store.items()))), set(range(1, 20)), 24, 1)
    with pytest.raises(ValueError, match="unused"):
        study.select_records(store, set(range(1, 70)), 24, 1)
    with pytest.raises(ValueError, match="multiple of 24"):
        study.select_records(store, set(), 25, 1)


def test_all_permutations_and_positions_balanced():
    scheduled = study.schedule(list(range(120)))
    assert len(scheduled) == 480
    assert len({(r["issue_number"], r["arm"]) for r in scheduled}) == 480
    for position in range(4):
        assert Counter(r["arm"] for r in scheduled[position::4]) == dict.fromkeys(study.ARMS, 30)
    assert len({tuple(r["arm"] for r in scheduled[i:i + 4]) for i in range(0, 480, 4)}) == 24


def test_support_arm_changes_only_gate_and_never_retains_certificate():
    from guarded_agentic_compaction.registry.store import Registry
    original = Registry.load(study.REGISTRY)
    before = copy.deepcopy(original.artifacts[0].to_dict())
    support = study.support_registry(original)
    changed = support.artifacts[0].to_dict()
    assert original.artifacts[0].to_dict() == before
    assert {k: v for k, v in before.items() if k != "gate"} == {k: v for k, v in changed.items() if k != "gate"}
    assert support.artifacts[0].gate.accepts({})[0]
    assert support.artifacts[0].gate.alpha == 1
    assert support.artifacts[0].gate.risk_upper_bound == 1
    assert support.artifacts[0].gate.n_accepted == 0  # never reuse empirical certification metadata
    original.artifacts[0].gate.n_calibration_groups = 91
    with pytest.raises(ValueError, match="92-group"):
        study.support_registry(original)


def test_summary_keeps_failures_and_missing_records_separate():
    seal = frozen()
    rows = [outcome(100, "baseline"), outcome(100, "gac", status="failed"),
            outcome(101, "baseline", correct=False), outcome(101, "gac", correct=False, dispatched=True)]
    result = study.summarize(seal, rows)
    assert result["status"] == "incomplete"
    assert not result["comparative_claim_allowed"]
    gac = result["arms"]["gac"]
    assert (gac["scheduled"], gac["attempted"], gac["completed"], gac["failed"], gac["not_attempted"]) == (24, 2, 1, 1, 22)
    assert gac["wrong_after_dispatch"] == 1
    assert not gac["resource_accounting_complete"]
    assert result["paired_vs_baseline"]["gac"]["baseline_only_correct"] == 1
    assert result["paired_vs_baseline"]["gac"]["attempted_pairs"] == 2
    with pytest.raises(ValueError, match="duplicate"):
        study.summarize(seal, rows + [rows[0]])
    with pytest.raises(ValueError, match="unexpected"):
        study.summarize(seal, [outcome(999, "baseline")])


def test_complete_null_result_is_not_labeled_protection():
    seal = frozen()
    rows = [outcome(r["issue_number"], r["arm"]) for r in seal["schedule"]]
    result = study.summarize(seal, rows)
    assert result["comparative_claim_allowed"]
    assert result["status"] == "completed"
    assert not result["end_to_end_risk_certified"]
    assert all(a["correct"] == 24 and a["resource_accounting_complete"] for a in result["arms"].values())
    assert all(c["baseline_only_correct"] == c["candidate_only_correct"] == 0 for c in result["paired_vs_baseline"].values())


@pytest.mark.parametrize("cap", [float("nan"), float("inf"), -1, 0, .5])
def test_budget_must_be_finite_and_reserve_one_operation(tmp_path, cap):
    with pytest.raises(ValueError, match="finite"):
        study.open_checkpoint(tmp_path, frozen(), cap)


def test_pending_failed_and_tampered_checkpoints_cannot_resume(tmp_path):
    seal = frozen()
    state = study.open_checkpoint(tmp_path, seal, 2)
    state["pending"] = seal["schedule"][0]
    study.write_json(tmp_path / "checkpoint.json", state)
    with pytest.raises(ValueError, match="interrupted"):
        study.open_checkpoint(tmp_path, seal, 2)
    state["pending"] = None
    state["rows"] = [outcome(100, "baseline", status="failed")]
    study.write_json(tmp_path / "checkpoint.json", state)
    with pytest.raises(ValueError, match="failed"):
        study.open_checkpoint(tmp_path, seal, 2)
    state["rows"] = []
    study.write_json(tmp_path / "checkpoint.json", state)
    with pytest.raises(ValueError, match="spend cap"):
        study.open_checkpoint(tmp_path, seal, 3)
    tampered = copy.deepcopy(seal)
    tampered["test_ids"][0] = 999
    with pytest.raises(ValueError, match="preflight"):
        study.open_checkpoint(tmp_path, tampered, 2)


def test_clean_checkpoint_must_follow_sealed_order(tmp_path):
    seal = frozen()
    state = study.open_checkpoint(tmp_path, seal, 2)
    state["rows"] = [outcome(100, "gac")]
    study.write_json(tmp_path / "checkpoint.json", state)
    with pytest.raises(ValueError, match="order"):
        study.open_checkpoint(tmp_path, seal, 2)


@pytest.mark.parametrize("fail", [False, True])
def test_runner_checkpoint_before_call_and_no_retry(monkeypatch, tmp_path, fail):
    seal = frozen()
    monkeypatch.setattr(study, "verify", lambda out: (seal, ()))
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-not-a-real-key")
    seen = []

    async def fake_execute(number, arm, current, processor):
        checkpoint = json.loads((tmp_path / "checkpoint.json").read_text())
        assert checkpoint["pending"] == {"issue_number": number, "arm": arm}
        seen.append((number, arm))
        if fail:
            raise TimeoutError("offline fixture")
        return outcome(number, arm)

    monkeypatch.setattr(study, "execute", fake_execute)
    report = asyncio.run(study.run(tmp_path, 2))
    state = json.loads((tmp_path / "checkpoint.json").read_text())
    assert state["pending"] is None
    if fail:
        assert len(seen) == 1
        assert state["unknown_cost_reserve_usd"] == 1
        assert report["status"] == "incomplete"
        with pytest.raises(ValueError, match="failed"):
            asyncio.run(study.run(tmp_path, 2))
        assert len(seen) == 1
    else:
        assert len(seen) == 96
        assert report["status"] == "completed"
        asyncio.run(study.run(tmp_path, 2))
        assert len(seen) == 96  # a completed run makes no new calls


def test_missing_metrics_stop_execution_and_preserve_unknown_cost(monkeypatch, tmp_path):
    monkeypatch.setattr(study, "verify", lambda out: (frozen(), ()))
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-not-a-real-key")

    async def fake_execute(number, arm, current, processor):
        row = outcome(number, arm)
        row["metrics"]["estimated_cost_usd"] = None
        return row

    monkeypatch.setattr(study, "execute", fake_execute)
    report = asyncio.run(study.run(tmp_path, 2))
    assert report["arms"]["baseline"]["failed"] == 1
    assert report["arms"]["baseline"]["completed"] == 0
    assert not report["comparative_claim_allowed"]


def test_budget_stops_before_next_call_without_excluding_future_cases(monkeypatch, tmp_path):
    monkeypatch.setattr(study, "verify", lambda out: (frozen(), ()))
    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-not-a-real-key")
    seen = []

    async def fake_execute(number, arm, current, processor):
        seen.append((number, arm))
        row = outcome(number, arm)
        row["metrics"]["estimated_cost_usd"] = .2
        return row

    monkeypatch.setattr(study, "execute", fake_execute)
    report = asyncio.run(study.run(tmp_path, 1.1))
    assert len(seen) == 1
    assert sum(a["not_attempted"] for a in report["arms"].values()) == 95
    assert report["status"] == "incomplete"


def test_existing_lock_prevents_second_runner(monkeypatch, tmp_path):
    (tmp_path / "run.lock").write_text("existing run")
    monkeypatch.setattr(study, "verify", lambda _: pytest.fail("must stop before loading or calling"))
    with pytest.raises(ValueError, match="already active"):
        asyncio.run(study.run(tmp_path, 2))
    assert (tmp_path / "run.lock").read_text() == "existing run"


def test_real_dispatch_probe_supplies_live_manifest_context():
    import github_live_study as fixed
    from guarded_agentic_compaction.registry.store import Registry

    original = Registry.load(study.REGISTRY)
    # The retained artifact's own manifest is intentional in this fixture. The
    # production preflight separately reconstructs and checks the current one.
    manifest = original.artifacts[0].manifest
    store = {4420: {"number": 4420, "title": "issue", "body": "body", "state": "open",
                    "labels": ["bug"], "comments": ["evidence"], "html_url": "https://example.invalid/4420",
                    "day": "2025-01-01"}}
    result = study.probe([4420], store, fixed.make_catalog(), manifest,
                         {"gac": original, "support_only": study.support_registry(original)})
    assert result["provider_calls_executed"] == 0
    assert not result["end_to_end_quality_measured"]
    assert result["outcomes"] == {"gac": {"COMPACTED": 1}, "support_only": {"COMPACTED": 1},
                                  "recurrence_only": {"REPLAYED": 1}}


def test_recurrence_uses_same_task_and_includes_replay_latency(monkeypatch):
    from types import SimpleNamespace
    import agents
    import demos.live_runtime as live
    import github_live_study as fixed
    import recurrence_only_ablation as shared

    store = {100: {"labels": ["bug"], "html_url": "https://example.invalid/100", "day": "2025-01-01", "state": "open"}}
    processor = SimpleNamespace(drain=lambda: [SimpleNamespace(trace_id="trace_" + study.object_digest(["fresh-safeguards", 100, "recurrence_only"])[:32])])
    made = []
    monkeypatch.setattr(fixed, "make_agent", lambda model, tools, task: made.append((model, tools, task)) or "agent")
    monkeypatch.setattr(fixed, "make_manifest", lambda *args: "manifest")
    monkeypatch.setattr(shared, "replay_three_reads", lambda store, number: (["read"], [{}], {"source": "evidence"}))
    monkeypatch.setattr(live, "observations_from_trace", lambda *args: [])
    times = iter((10.0, 25.0))
    monkeypatch.setattr(study.time, "perf_counter", lambda: next(times))
    calls = []

    async def fake_run(agent, prompt, **kwargs):
        calls.append((agent, prompt, kwargs))
        return SimpleNamespace(final_output={"answer": "fixture"})

    monkeypatch.setattr(agents.Runner, "run", fake_run)
    captured = {}

    def materialize(*args, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(public_dict=lambda: {"quality": {"factuality_exact": True}})

    monkeypatch.setattr(shared, "materialize", materialize)
    result = asyncio.run(study.recurrence_run(100, (store, None, None, None, None, None, None), processor))
    assert made == [(study.MODEL, [], study.TASK)]
    assert len(calls) == 1
    assert captured["wall_ms"] == 15000
    assert captured["source_record"] == store[100]
    assert result["dispatched"] is True
