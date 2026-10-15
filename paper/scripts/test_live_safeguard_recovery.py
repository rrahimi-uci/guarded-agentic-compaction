"""No-provider tests for equal recovery, SDK execution and fail-closed spending."""
from __future__ import annotations

import asyncio
import copy
import json
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import live_safeguard_recovery as study


def source():
    return {i: {"title": f"Issue {i}", "comments": ["one", "ERROR", "three", "error four", "five"]}
            for i in range(1, 11)}


def artifact():
    return study.offline.discover([1, 2, 3, 4], source())[0]


def case(limit=3, suite="ordinary"):
    return next(c for c in study.offline.cases([10]) if c["requested_limit"] == limit and c["suite"] == suite)


def response(input_tokens=100, output_tokens=10, cached=20):
    from agents.usage import Usage
    usage = Usage(requests=1, input_tokens=input_tokens, output_tokens=output_tokens,
                  total_tokens=input_tokens + output_tokens)
    usage.input_tokens_details.cached_tokens = cached
    return SimpleNamespace(usage=usage)


def frozen():
    c = case()
    return {"cases": [c], "schedule": [{"case_id": c["case_id"], "arm": arm} for arm in study.ARMS],
            "configuration": {"price_table": study.price_table()}}


def fake_result(model_input):
    request = json.loads(model_input)["request"]
    answer = study.offline.source_answer({**request, "suite": "ordinary"}, source())
    return SimpleNamespace(final_output=answer, raw_responses=[response()])


def test_hash_selection_and_every_permutation_per_condition():
    prior = {"splits": {"test": list(range(1, 97))}, "outcomes": {"correct": False}}
    chosen = study.selected_numbers(prior)
    prior["outcomes"] = {"correct": True}
    assert study.selected_numbers(prior) == chosen
    assert len(chosen) == len(set(chosen)) == 24
    schedule = study.schedule(chosen)
    assert len(schedule) == len({(r["case_id"], r["arm"]) for r in schedule}) == 576
    for suite in study.offline.SUITES:
        for limit in study.offline.LIMITS:
            orders = [tuple(r["arm"] for r in schedule if r["case_id"] == f"{n}:{suite}:{limit}") for n in chosen]
            assert len(set(orders)) == 24
            for position in range(4):
                assert Counter(order[position] for order in orders) == dict.fromkeys(study.ARMS, 6)


@pytest.mark.parametrize("c", [case(5), case(3, "capped_response_stress")])
def test_full_refusal_gets_exact_baseline_input_and_no_oracle(c):
    a, _ = study.initial_context(c, "baseline", artifact(), source())
    b, _ = study.initial_context(c, "full", artifact(), source())
    assert b["metadata"]["fallback"]
    assert a["model_input"] == b["model_input"]
    assert set(json.loads(b["model_input"])) == {"request", "initial_observations"}
    assert json.loads(b["model_input"])["initial_observations"] == []
    if c["suite"] == "capped_response_stress":
        assert len(b["metadata"]["prefetch_calls"]) == 2


def test_initial_observations_expose_original_limit_and_do_not_repin_artifact():
    art = artifact()
    before = art.to_dict()
    context, _ = study.initial_context(case(5), "no_entry_hull", art, source())
    obs = json.loads(context["model_input"])["initial_observations"]
    assert obs[1]["arguments"]["limit"] == 3
    assert len(obs[1]["result"]["items"]) == 3
    assert obs[1]["result"]["complete"] is True
    assert art.to_dict() == before
    assert art.manifest.model != study.MODEL


def test_recovery_tool_schemas_are_identical_across_arms():
    specs = []
    for arm in study.ARMS:
        _, backend = study.initial_context(case(), arm, artifact(), source())
        specs.append(study.tool_specs(study.recovery_tools(backend, case(), [])))
    assert all(s == specs[0] for s in specs)
    assert [t["name"] for t in specs[0]] == ["read_issue", "read_comment_page"]
    assert all(t["strict"] for t in specs[0])


def test_real_sdk_loop_can_repair_prefetch_without_a_provider(monkeypatch):
    from agents.models.interface import Model
    from agents.items import ModelResponse
    from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText

    class RepairModel(Model):
        calls = 0

        async def get_response(self, **kwargs):
            self.calls += 1
            assert kwargs["tracing"].is_disabled()
            assert kwargs["model_settings"].retry.max_retries == 0
            assert [t.name for t in kwargs["tools"]] == ["read_issue", "read_comment_page"]
            if self.calls == 1:
                output = [ResponseFunctionToolCall(type="function_call", name="read_comment_page",
                    arguments=json.dumps({"issue_number": 10, "offset": 3, "limit": 2}),
                    call_id="repair", id="fc_repair")]
            else:
                history = kwargs["input"]
                assert any(item.get("type") == "function_call_output" and 'error four' in item.get("output", "") for item in history)
                output = [ResponseOutputMessage(id="message_repair", type="message", role="assistant", status="completed",
                    content=[ResponseOutputText(type="output_text", annotations=[],
                        text=json.dumps({"issue_number": 10, "comment_count": 5, "matching_positions": [2, 4]}))])]
            return ModelResponse(output=output, usage=response().usage, response_id=f"offline_{self.calls}")

        async def stream_response(self, *args, **kwargs):
            raise NotImplementedError
            yield

    prices = study.price_table()
    model = RepairModel()
    monkeypatch.setattr(study, "MODEL", model)
    row = asyncio.run(study.execute(case(5), "no_entry_hull", artifact(), source(), prices))
    assert row["correct"] and row["dispatched"]
    assert model.calls == row["metrics"]["requests"] == 2
    assert row["metrics"]["prefetch_tool_calls"] == 2
    assert row["metrics"]["continuation_tool_calls"] == 1
    assert row["metrics"]["total_tool_calls"] == 3
    assert "raw_responses" not in row
    assert "output" not in row["usage"][0]


def test_usage_counts_every_response_and_cached_input():
    prices = study.price_table()
    rows, total = study.usage_metrics([response(), response(50, 5, 0)], prices)
    assert total["requests"] == 2 and total["total_tokens"] == 165
    assert total["input_tokens"] == 150 and total["cached_input_tokens"] == 20
    expected = (130 * prices["input"] + 20 * prices["cached_input"] + 15 * prices["output"]) / 1e6
    assert total["estimated_cost_usd"] == pytest.approx(expected)


@pytest.mark.parametrize("responses", [[], [response(0, 1, 0)], [response(10, 1, 20)]])
def test_missing_or_inconsistent_usage_is_not_zero_cost(responses):
    with pytest.raises(ValueError):
        study.usage_metrics(responses, study.price_table())


@pytest.mark.parametrize("cap", [0, -.1, .5, float("nan"), float("inf")])
def test_budget_requires_explicit_finite_reserve(tmp_path, cap):
    with pytest.raises(ValueError, match="cap"):
        study.checkpoint(tmp_path, frozen(), cap)


def configure_runner(monkeypatch):
    import agents
    import openai

    class Client:
        def __init__(self, **kwargs):
            assert kwargs == {"max_retries": 0}

        async def close(self):
            pass

    monkeypatch.setenv("OPENAI_API_KEY", "offline-test-not-a-key")
    monkeypatch.setattr(openai, "AsyncOpenAI", Client)
    monkeypatch.setattr(agents, "set_default_openai_client", lambda *args, **kwargs: None)
    monkeypatch.setattr(study, "verify", lambda _: (frozen(), source(), artifact()))


def test_checkpoint_precedes_call_and_completed_run_makes_no_new_calls(monkeypatch, tmp_path):
    configure_runner(monkeypatch)
    called = []

    async def fake_invoke(model_input, tools):
        state = json.loads((tmp_path / "checkpoint.json").read_text())
        assert state["pending"] == frozen()["schedule"][len(called)]
        called.append(model_input)
        return fake_result(model_input)

    monkeypatch.setattr(study, "invoke", fake_invoke)
    assert asyncio.run(study.run(tmp_path, 2))["status"] == "completed"
    assert len(called) == 4
    assert asyncio.run(study.run(tmp_path, 2))["status"] == "completed"
    assert len(called) == 4
    assert study.analyze(tmp_path)["source_regrade_passed"]
    with pytest.raises(ValueError, match="budget mismatch"):
        asyncio.run(study.run(tmp_path, 3))


def test_failed_episode_stops_retains_reserve_and_never_retries(monkeypatch, tmp_path):
    configure_runner(monkeypatch)
    calls = []

    async def fail(*args):
        calls.append(1)
        raise TimeoutError("do not serialize potential credential fragments")

    monkeypatch.setattr(study, "invoke", fail)
    report = asyncio.run(study.run(tmp_path, 2))
    assert report["status"] == "incomplete"
    assert report["unknown_cost_reserve_usd"] == 1
    assert len(calls) == 1
    state = json.loads((tmp_path / "checkpoint.json").read_text())
    assert state["rows"][0]["error_type"] == "TimeoutError"
    assert "credential" not in json.dumps(state)
    with pytest.raises(ValueError, match="retry refused"):
        asyncio.run(study.run(tmp_path, 2))
    assert len(calls) == 1


def test_budget_exhaustion_preserves_unattempted_cases(monkeypatch, tmp_path):
    configure_runner(monkeypatch)

    async def fake_invoke(model_input, tools):
        return fake_result(model_input)

    monkeypatch.setattr(study, "invoke", fake_invoke)
    report = asyncio.run(study.run(tmp_path, 1.000001))
    assert report["attempted"] == 1
    assert report["scheduled"] == 4 and report["status"] == "incomplete"
    assert report["suites"]["ordinary"]["arms"]["full"]["not_attempted"] == 1
    assert not report["suites"]["ordinary"]["arms"]["full"]["resource_accounting_complete"]


def test_pending_checkpoint_and_existing_lock_refuse_execution(monkeypatch, tmp_path):
    configure_runner(monkeypatch)
    state = study.checkpoint(tmp_path, frozen(), 2)
    state["pending"] = frozen()["schedule"][0]
    study.write_json(tmp_path / "checkpoint.json", state)
    with pytest.raises(ValueError, match="pending"):
        asyncio.run(study.run(tmp_path, 2))
    (tmp_path / "run.lock").write_text("existing")
    with pytest.raises(ValueError, match="lock"):
        asyncio.run(study.run(tmp_path, 2))
    assert (tmp_path / "run.lock").read_text() == "existing"


def test_tampered_cost_cannot_resume_even_when_usage_totals_are_changed(monkeypatch, tmp_path):
    configure_runner(monkeypatch)

    async def fake_invoke(model_input, tools):
        return fake_result(model_input)

    monkeypatch.setattr(study, "invoke", fake_invoke)
    asyncio.run(study.run(tmp_path, 1.000001))
    state = json.loads((tmp_path / "checkpoint.json").read_text())
    state["rows"][0]["metrics"]["estimated_cost_usd"] = 0
    state["rows"][0]["usage"][0]["estimated_cost_usd"] = 0
    study.write_json(tmp_path / "checkpoint.json", state)
    with pytest.raises(ValueError, match="frozen prices"):
        asyncio.run(study.run(tmp_path, 1.000001))


def test_summary_rejects_reordering_and_keeps_failures_in_denominators():
    f = frozen()
    row = {**f["schedule"][0], "status": "failed"}
    report = study.summarize(f, [row])
    assert report["suites"]["ordinary"]["arms"]["baseline"]["failed"] == 1
    assert report["suites"]["ordinary"]["arms"]["baseline"]["correct"] == 0
    assert report["suites"]["ordinary"]["arms"]["full"]["not_attempted"] == 1
    with pytest.raises(ValueError, match="misordered"):
        study.summarize(f, [{**row, "arm": "full"}])


def test_seal_serializes_sdk_configuration_and_detects_cohort_tampering(monkeypatch, tmp_path):
    data = {i: {"title": f"Issue {i}", "comments": ["error"]} for i in range(1, 97)}
    prior = {"splits": {"test": list(data)}, "source": {"sha256": "offline-fixture"}}
    monkeypatch.setattr(study, "prior_inputs", lambda: (prior, data, artifact(), {}))
    monkeypatch.setattr(study, "code_hashes", lambda: {"fixture": "frozen"})
    assert study.prepare(tmp_path)["episodes"] == 576
    seal, _, _ = study.verify(tmp_path)
    assert seal["configuration"]["settings"]["reasoning"]["effort"] == "low"
    assert seal["configuration"]["settings"]["retry"]["max_retries"] == 0
    with pytest.raises(FileExistsError):
        study.prepare(tmp_path)
    seal["cohort"][0] = 999
    study.write_json(tmp_path / "seal.json", seal)
    with pytest.raises(ValueError, match="cohort"):
        study.verify(tmp_path)
