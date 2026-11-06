import asyncio
from contextlib import asynccontextmanager
import importlib.util
import json
from types import SimpleNamespace

import pytest

import appworld_adaptive_viability as study


def worker_module():
    spec = importlib.util.spec_from_file_location("viability_worker_test", study.WORKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("sql,operation", [
    ("SELECT 1", None), ("-- comment\n UPDATE x SET a=1", "UPDATE"),
    ("/* hidden */DELETE FROM x", "DELETE"), ("CREATE TABLE x(a)", "CREATE"),
    ("WITH x AS (SELECT 1) SELECT * FROM x", "WITH"), ("PRAGMA journal_mode=OFF", "PRAGMA"),
    ("SELECT 'DELETE'", None),
])
def test_sql_audit_retains_writes_and_unknown_operations(sql, operation):
    assert worker_module().sql_operation(sql) == operation


def test_bounded_history_preserves_all_action_messages_without_mutating_raw():
    original = [{"role": "user", "content": "task"}]
    for i in range(8):
        original += [{"role": "assistant", "content": "action " + str(i)}, {"role": "tool", "content": "x" * 20000}]
    bounded = study.bounded_messages(original)
    assert len(bounded) == len(original)
    assert bounded[0] == original[0]
    assert all(bounded[i] == row for i, row in enumerate(original) if row["role"] != "tool")
    assert len(bounded[-1]["content"]) < 17000
    assert "omitted" in bounded[2]["content"]
    assert len(original[-1]["content"]) == 20000


def test_local_cap_includes_prior_reservations_and_rejects_large_payload(tmp_path, monkeypatch):
    monkeypatch.setattr(study, "CAMPAIGN", tmp_path)
    path = tmp_path / "ledger.json"
    path.write_text(json.dumps({"requests": [{"task": study.NAMESPACE + "old", "reserved_usd": 7.999}]}))
    with pytest.raises(study.BudgetExceeded):
        study.study_reservation({"messages": [{"role": "user", "content": "task"}]})
    path.write_text(json.dumps({"requests": []}))
    with pytest.raises(study.BudgetExceeded):
        study.study_reservation({"messages": [{"role": "user", "content": "x" * 100001}]})
    study.study_reservation({"messages": [{"role": "user", "content": "task"}]})
    assert json.loads(path.read_text()) == {"requests": []}


@pytest.mark.parametrize("arm", ["baseline", "manual_prefix"])
def test_manual_prefix_uses_real_calls_and_equivalent_tool_history(tmp_path, monkeypatch, arm):
    sent, payloads = [], []
    @asynccontextmanager
    async def fake_worker(request, path):
        async def send(value):
            sent.append(value)
        async def receive():
            if not sent:
                return {"type": "context", "instruction": "public task", "documentation": {}}
            if sent[-1]["type"] == "finish":
                return {"type": "evaluation", "success": False, "tests": 2, "passed_tests": 1}
            return {"type": "result", "result": {"observed": sent[-1]["api"]}, "observed_sql_operations": []}
        yield send, receive
    class Client:
        def __init__(self, *args, **kwargs):
            pass
        async def create(self, **payload):
            payloads.append(payload)
            message = SimpleNamespace(tool_calls=None, model_dump=lambda **kwargs: {"role": "assistant", "content": "done"})
            return SimpleNamespace(choices=[SimpleNamespace(message=message)], model_dump=lambda: {"choices": []})
        async def close(self):
            pass
    monkeypatch.setattr(study, "worker", fake_worker)
    monkeypatch.setattr(study, "BudgetClient", Client)
    monkeypatch.setattr(study, "study_reservation", lambda payload: None)
    monkeypatch.setattr(study, "CAMPAIGN", tmp_path)
    seal = {"instructions": "same instruction", "tool": study.TOOL, "prefix": study.PREFIX, "max_requests": 2, "max_api_calls": 48}
    row = {}
    asyncio.run(study.episode("development", arm, seal, tmp_path / "result.json", row))
    assert row["status"] == "completed" and row["evaluation"]["success"] is False
    calls = [v for v in sent if v["type"] == "call"]
    assert len(calls) == (2 if arm == "manual_prefix" else 0)
    messages = payloads[0]["messages"]
    assert messages[0]["content"] == "same instruction"
    assert len([m for m in messages if m["role"] == "tool"]) == len(calls)
    if calls:
        assert [json.loads(m["content"])["observed"] for m in messages if m["role"] == "tool"] == ["show_profile", "show_account_passwords"]


def test_catalog_does_not_reclassify_login_or_general_api_as_read():
    from guarded_agentic_compaction.runtime.facade import ToolFacade, FacadeMode
    from guarded_agentic_compaction.grc.program import Program, CallStep
    from guarded_agentic_compaction.runtime.interp import run_program
    for name in ("spotify.login", "file_system.login", "supervisor.complete_task", "call_api", "file_system.show_directory"):
        calls = []
        facade = ToolFacade(catalog=study.catalog(), mode=FacadeMode.SANDBOX,
            executor=lambda *args: calls.append(args))
        result = run_program(Program(steps=[CallStep("r", name)]), {}, facade)
        assert not result.ok and not calls


def test_summary_counts_failed_missing_and_discordant_arms():
    from analyze_appworld_viability import summarize
    seal = {"tasks": ["a_1", "b_2"], "arms": ["baseline", "manual_prefix"]}
    rows = [{"task_id": "a_1", "arm": "baseline", "status": "completed", "evaluation": {"success": True}},
            {"task_id": "a_1", "arm": "manual_prefix", "status": "failed"},
            {"task_id": "b_2", "arm": "baseline", "status": "unstarted"},
            {"task_id": "b_2", "arm": "manual_prefix", "status": "completed", "evaluation": {"success": True}}]
    result = summarize(seal, rows)
    assert result["arms"]["baseline"]["scheduled"] == 2
    assert result["arms"]["baseline"]["attempted"] == 1
    assert result["paired_success"] == {"both": 0, "baseline_only": 1, "manual_only": 1, "neither": 0}
    for invalid in (rows[:-1], rows + [rows[0]], [dict(r, status="running") for r in rows]):
        with pytest.raises(ValueError):
            summarize(seal, invalid)


@pytest.mark.parametrize('save_fails', [False, True])
def test_direct_request_state_is_persisted_before_close_and_save_failure_propagates(save_fails):
    events = []
    class World:
        def save(self):
            events.append('save')
            if save_fails:
                raise RuntimeError('cannot persist')
        def close(self):
            events.append('close')
    if save_fails:
        with pytest.raises(RuntimeError, match='cannot persist'):
            worker_module().persist_and_close(World())
    else:
        worker_module().persist_and_close(World())
    assert events == ['save', 'close']


def test_stopped_paid_attempt_cannot_resume(tmp_path, monkeypatch):
    monkeypatch.setattr(study, 'CACHE', tmp_path)
    (tmp_path / 'execution_stop.json').write_text('{}')
    with pytest.raises(ValueError, match='stopped attempt'):
        asyncio.run(study.run({}))


def test_trace_conversion_keeps_missing_tool_result_and_unknown_task_outcome():
    from analyze_appworld_viability import convert
    from guarded_agentic_compaction.capture.manifests import build_manifest
    from guarded_agentic_compaction.schema.traces import EventKind
    manifest = build_manifest(commit='synthetic', model='synthetic', prompt='synthetic', tools=study.TOOL,
        catalog=study.catalog(), policy='diagnostic', guardrails='unknown original outcome', entry_contract_version='test')
    raw = {'task_id': 'synthetic_1', 'status': 'failed', 'evaluation': {'success': False},
        'provider_trace': [{'id': 'r1', 'choices': [{'message': {'tool_calls': [{'id': 'c1', 'function': {
            'name': 'call_api', 'arguments': json.dumps({'app': 'supervisor', 'api': 'show_profile', 'arguments': {}})}}]}}]}]}
    episode = convert(raw, manifest)
    assert episode.outcome.task_success is None
    results = [e for e in episode.events if e.kind == EventKind.TOOL_RESULT]
    assert len(results) == 1 and results[0].status == 'error'
    assert results[0].output['synthetic_missingness_marker'] is True
    raw['calls'] = [{'tool': 'different.tool', 'arguments': {}, 'call_id': 'c1'}]
    with pytest.raises(ValueError, match='trace mismatch'):
        convert(raw, manifest)


def test_retained_interrupted_pilot_has_complete_accounting_and_separate_repair():
    import hashlib
    report = json.loads((study.OUT / 'report.json').read_text())
    seal = json.loads((study.OUT / 'seal.json').read_text())
    rows = report['episode_dispositions']
    assert len(rows) == 24
    assert {(r['task_id'], r['arm']) for r in rows} == {(t, a) for t in seal['tasks'] for a in seal['arms']}
    assert all(r['original_grade_valid'] is False for r in rows)
    assert sum(r['status'] == 'completed' for r in rows) == 9
    assert sum(r['status'] == 'failed' for r in rows) == 1
    assert sum(r['status'] == 'unstarted' for r in rows) == 14
    for arm, summary in report['summary']['arms'].items():
        selected = [r for r in rows if r['arm'] == arm]
        assert summary['model_requests'] == sum(r['model_requests'] for r in selected)
        assert summary['api_calls'] == sum(r['api_calls'] for r in selected)
        assert 'successes' not in summary
    assert report['measurement_validity'] == 'INVALID_ORIGINAL_GRADES_PERSISTENCE_DEFECT'
    repair = report['persistence_repair']
    assert repair['controls_passed'] == repair['direct_path_controls'] == 3
    completed = {(r['task_id'], r['arm']) for r in rows if r['status'] == 'completed'}
    assert {(r['task_id'], r['arm']) for r in repair['regrades']} == completed
    assert all(r['diagnostic_valid'] and r['observations_match'] and r['context_matches'] for r in repair['regrades'])
    assert report['compiler']['artifacts_emitted'] == 0
    assert report['compiler']['baselines_with_unknown_outcome_retained'] == 12
    assert report['decision'] == 'NO_GO_FOR_CONFIRMATORY_EXECUTION'
    ledger = json.loads((study.OUT / 'ledger_excerpt.json').read_text())['requests']
    amount = sum(r.get('accounted_upper_usd', r['reserved_usd']) for r in ledger)
    assert amount == pytest.approx(report['budget']['new_accounted_upper_usd'])
    assert amount < seal['pilot_cap_usd']
    assert report['budget']['campaign_accounted_upper_usd'] + report['budget']['remaining_cap_usd'] == pytest.approx(300)
    bundle = study.OUT / 'operational_evidence.bundle'
    assert hashlib.sha256(bundle.read_bytes()).hexdigest() == report['encrypted_evidence_sha256']
    assert report['bundle_verification']['passed']
    assert report['bundle_verification']['roundtrip_original_files_verified'] == len(report['protected_raw_files'])
    amendment = json.loads((study.OUT / 'analysis_amendment.json').read_text())
    assert hashlib.sha256((study.ROOT / 'paper/scripts/analyze_appworld_viability.py').read_bytes()).hexdigest() == amendment['amended_analysis_sha256']
    assert hashlib.sha256((study.ROOT / 'paper/scripts/repair_appworld_viability.py').read_bytes()).hexdigest() == json.loads((study.OUT / 'repair_plan.json').read_text())['source_hashes']['paper/scripts/repair_appworld_viability.py']
