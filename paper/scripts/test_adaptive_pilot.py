"""Offline tests: no provider requests or benchmark data required."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3

import pytest

import adaptive_campaign_budget as budget
from adaptive_pilot_runtime import SQLTools


def payload():
    return {"model": budget.MODEL, "max_completion_tokens": 4096,
            "messages": [{"role": "user", "content": "test"}]}


def reserve(ledger, task="q"):
    return ledger.reserve(payload(), stage="pilot", task=task, arm="baseline")


def test_concurrent_ledger_cannot_overspend(tmp_path, monkeypatch):
    monkeypatch.setitem(budget.STAGE_CAPS, "pilot", .1)
    path = tmp_path / "ledger.json"
    def attempt(i):
        try:
            return reserve(budget.Ledger(path), str(i))
        except budget.BudgetExceeded:
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(attempt, range(40)))
    data = json.loads(path.read_text())
    assert 0 < len(data["requests"]) < 40
    assert len(data["requests"]) == sum(i is not None for i in ids)
    assert data["accounted_upper_usd"] <= .1


def test_unknown_usage_and_restart_preserve_reservations(tmp_path):
    path = tmp_path / "ledger.json"
    ledger = budget.Ledger(path)
    rid = reserve(ledger)
    amount = json.loads(path.read_text())["accounted_upper_usd"]
    ledger.finish(rid, status="failed")
    assert json.loads(path.read_text())["accounted_upper_usd"] == amount
    reserve(budget.Ledger(path))
    assert json.loads(path.read_text())["accounted_upper_usd"] == 2 * amount


def test_usage_breach_persistently_stops_campaign(tmp_path):
    ledger = budget.Ledger(tmp_path / "ledger.json")
    rid = reserve(ledger)
    with pytest.raises(budget.BudgetExceeded):
        ledger.finish(rid, {"prompt_tokens": 999999, "completion_tokens": 1})
    with pytest.raises(budget.BudgetExceeded):
        reserve(budget.Ledger(ledger.path), "another-task")


def test_actual_usage_and_invalid_usage(tmp_path):
    ledger = budget.Ledger(tmp_path / "ledger.json")
    rid = reserve(ledger)
    ledger.finish(rid, {"prompt_tokens": 100, "completion_tokens": 10})
    data = json.loads(ledger.path.read_text())
    assert data["accounted_upper_usd"] == pytest.approx(.000062)
    with pytest.raises(ValueError):
        ledger.finish(rid)
    rid2 = reserve(ledger)
    ledger.finish(rid2, {"prompt_tokens": -1, "completion_tokens": 10})
    row = json.loads(ledger.path.read_text())["requests"][1]
    assert "accounted_upper_usd" not in row


def test_request_limits(tmp_path):
    ledger = budget.Ledger(tmp_path / "ledger.json")
    for _ in range(48):
        rid = reserve(ledger)
        ledger.finish(rid, {"prompt_tokens": 1, "completion_tokens": 1})
    with pytest.raises(budget.BudgetExceeded):
        reserve(ledger)
    p = payload(); p["messages"][0]["content"] = "x" * 200001
    with pytest.raises(budget.BudgetExceeded):
        ledger.reserve(p, stage="pilot", task="other", arm="baseline")


def test_selection_excludes_exposed_used_duplicates_and_unavailable():
    from adaptive_pilot import select_tasks
    questions = [{"question_id": i, "db_id": "db", "question": f"Q{i}"} for i in range(30)]
    questions[25]["question"] = " Q24 "
    tasks, reasons = select_tasks(questions, {20}, set(range(29)))
    assert len(tasks) == 4
    assert all(t["question_id"] not in {*range(18), 20, 24, 25, 29} for t in tasks)
    assert reasons["duplicate_question"] == 2
    assert sum(t["discovery_split"] == "train" for t in tasks) == 3
    assert select_tasks(list(reversed(questions)), {20}, set(range(29))) == (tasks, reasons)


def test_budget_client_charges_failure_without_retry(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import sys
    calls = []
    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs["max_retries"] == 0
            self.base_url = kwargs["base_url"]
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
        async def create(self, **kwargs):
            calls.append(kwargs)
            raise RuntimeError("synthetic provider failure")
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=FakeClient))
    ledger = budget.Ledger(tmp_path / "ledger.json")
    client = budget.BudgetClient(ledger, stage="pilot", task="fixture", arm="baseline")
    with pytest.raises(RuntimeError):
        asyncio.run(client.create(messages=[], max_tokens=99999, temperature=.5))
    assert len(calls) == 1
    assert calls[0]["max_completion_tokens"] == 4096
    assert calls[0]["reasoning_effort"] == "none"
    assert "temperature" not in calls[0]
    row = json.loads(ledger.path.read_text())["requests"][0]
    assert row["status"] == "provider_request_failed_usage_unknown"
    assert "accounted_upper_usd" not in row
    with pytest.raises(ValueError):
        client.with_options(max_retries=3)


def test_readonly_tools_and_prerequisites(tmp_path):
    path = tmp_path / "fixture.sqlite"
    with sqlite3.connect(path) as con:
        con.execute('CREATE TABLE "a b" (x INTEGER)')
        con.execute('INSERT INTO "a b" VALUES (1),(1)')
    before = path.read_bytes()
    tools = SQLTools(path)
    def call(n, a):
        return json.loads(tools.call(n, a)["payload"])
    assert "error" in call("run_query", {"sql": "SELECT 1"})
    assert call("list_tables", {}) == {"tables": ["a b"]}
    assert "error" in call("get_schema", {"table_names": ['a";DROP TABLE "a b";--']})
    assert call("get_schema", {"table_names": ["a b"]})["schemas"][0]["sample_rows"] == [[1], [1]]
    assert call("run_query", {"sql": 'SELECT * FROM "a b"'})["rows"] == [[1], [1]]
    assert call("run_query", {"sql": 'DELETE FROM "a b"'})["status"] == "denied"
    assert "error" in call("run_query", {"sql": 1})
    assert path.read_bytes() == before


def test_worker_in_pinned_container():
    import os
    if os.getenv("GAC_TEST_PILOT_DOCKER") != "1":
        pytest.skip("opt-in Docker integration; never downloads an image in ordinary CI")
    from adaptive_pilot_runtime import run_container
    seen = []
    async def dispatch(name, args):
        seen.append((name, args))
        return {"payload": '{"tables": ["t"]}'}
    code = 'x = await list_tables()\nresult = json.loads(x.payload)["tables"]'
    assert asyncio.run(run_container(code, dispatch, timeout=20)) == ["t"]
    assert seen == [("list_tables", {})]
    with pytest.raises(RuntimeError):
        asyncio.run(run_container('open("/app/write", "w").write("x")', dispatch, timeout=20))
    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(run_container('while True: pass', dispatch, timeout=2))


def test_stream_failure_retains_reservation(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    class Stream:
        def __aiter__(self):
            return self
        async def __anext__(self):
            raise RuntimeError("stream disconnected")
        async def close(self):
            pass
    class FakeClient:
        def __init__(self, **kwargs):
            self.base_url = kwargs["base_url"]
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
        async def create(self, **kwargs):
            assert kwargs["stream_options"]["include_usage"]
            return Stream()
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=FakeClient))
    ledger = budget.Ledger(tmp_path / "ledger.json")
    client = budget.BudgetClient(ledger, stage="pilot", task="fixture", arm="agent_jit")
    async def invoke():
        stream = await client.create(messages=[], stream=True)
        async for _ in stream:
            pass
    with pytest.raises(RuntimeError):
        asyncio.run(invoke())
    row = json.loads(ledger.path.read_text())["requests"][0]
    assert row["status"] == "stream_interrupted_usage_unknown"
    assert "accounted_upper_usd" not in row


def test_discovery_keeps_incorrect_and_failed_attempts():
    from adaptive_pilot_discovery import convert
    from guarded_agentic_compaction.schema.traces import ExecutionManifest
    manifest = ExecutionManifest("fixture")
    raw = {"question_id": 1, "db_id": "fixture", "execution_correct": False, "status": "failed"}
    episode = convert(raw, manifest, "fixture-hash")
    assert episode.outcome.task_success is False
    assert episode.attributes["attempt_status"] == "failed"
    assert episode.events == []  # compiler will report no_events, not silently drop it here


def test_retained_executor_parity_records_implementation_difference():
    from adaptive_pilot import OUT, ROOT, digest
    report = json.loads((OUT / "executor_parity.json").read_text())
    assert report["provider_calls"] == 0
    assert report["all_match"] is False
    assert report["prospective_all_match"] is True
    assert len(report["rows"]) == 5
    assert report["probe_sha256"] == digest(ROOT / "paper/scripts/probe_adaptive_executor_parity.py")
    assert report["prospective_worker_sha256"] == digest(ROOT / "experiments/adaptive_compiler_pilot/container_worker_native.py")


def test_retained_pilot_evidence():
    from adaptive_pilot import OUT
    from archive_adaptive_pilot import verify
    if not (OUT / "retention.json").exists():
        pytest.skip("live campaign archive not yet frozen")
    verify()
