"""Offline mapping tests for the Anthropic Agents-SDK adapter (no network)."""

from __future__ import annotations

import json

import pytest

from agents.model_settings import ModelSettings

from guarded_agentic_compaction.capture.anthropic_model import (
    AnthropicModel,
    anthropic_model_id,
    is_anthropic_model,
    items_to_messages,
    resolve_model,
    usage_from_anthropic,
)


class _Usage:
    input_tokens = 100
    output_tokens = 20
    cache_read_input_tokens = 30
    cache_creation_input_tokens = 10
    output_tokens_details = None


def test_resolve_model_keeps_openai_names_and_wraps_anthropic():
    assert resolve_model("gpt-5.6-luna") == "gpt-5.6-luna"
    model = resolve_model("anthropic/claude-sonnet-5")
    assert isinstance(model, AnthropicModel) and model.model == "claude-sonnet-5"
    assert is_anthropic_model("anthropic/x") and not is_anthropic_model("gpt-6-luna")
    with pytest.raises(ValueError):
        anthropic_model_id("gpt-6-luna")


def test_items_to_messages_maps_tool_calls_and_results():
    items = [
        {"type": "message", "role": "user", "content": "issue_number=7020"},
        {"type": "function_call", "call_id": "c1", "name": "issue_get_record", "arguments": '{"issue_number": 7020}'},
        {"type": "function_call_output", "call_id": "c1", "output": '{"issue_number": 7020}'},
    ]
    system: list[str] = []
    messages = items_to_messages(items, system)
    assert [m["role"] for m in messages] == ["user", "assistant", "user"]
    assert messages[1]["content"][0] == {"type": "tool_use", "id": "c1", "name": "issue_get_record", "input": {"issue_number": 7020}}
    assert messages[2]["content"][0]["type"] == "tool_result" and messages[2]["content"][0]["tool_use_id"] == "c1"
    assert system == []


def test_usage_normalizes_to_openai_convention():
    usage = usage_from_anthropic(_Usage())
    assert usage.input_tokens == 140 and usage.output_tokens == 20 and usage.total_tokens == 160
    assert usage.input_tokens_details.cached_tokens == 30
    assert getattr(usage.input_tokens_details, "cache_write_tokens", None) == 10


def test_build_request_applies_effort_and_parallel_tool_policy():
    model = AnthropicModel("claude-sonnet-5", effort="low")
    request = model.build_request("be terse", "hello", ModelSettings(parallel_tool_calls=False), [], None)
    assert request["model"] == "claude-sonnet-5" and request["system"] == "be terse"
    assert request["output_config"] == {"effort": "low"} and "tools" not in request
    assert "thinking" not in request and "temperature" not in request
    assert json.dumps(request["messages"]) == json.dumps([{"role": "user", "content": [{"type": "text", "text": "hello"}]}])
