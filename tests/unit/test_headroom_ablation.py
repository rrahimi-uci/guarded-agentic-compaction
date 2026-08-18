from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from guarded_agentic_compaction.benchmarking.headroom import (
    HEADROOM_VERSION,
    HeadroomAblationConfig,
    HeadroomCompressor,
    HeadroomUnavailableError,
    aggregate_headroom,
)


def test_headroom_adapter_forwards_valid_json_and_records_savings() -> None:
    def compress(messages, *, model):
        assert model == "gpt-5.6-luna"
        assert messages[1]["role"] == "tool"
        payload = json.loads(messages[1]["content"])
        payload["comments"] = [payload["comments"][0]]
        return SimpleNamespace(
            messages=[messages[0], {"role": "tool", "content": json.dumps(payload, sort_keys=True)}],
            tokens_before=100,
            tokens_after=40,
            tokens_saved=60,
            compression_ratio=0.6,
            transforms_applied=["smart_crusher"],
        )

    result = HeadroomCompressor(compress).compress_json(
        json.dumps({"record_number": 7, "source_revision": "pinned", "comments": ["a", "b"]}),
        required_fields=("record_number", "source_revision"),
    )

    assert result.applied is True
    assert json.loads(result.content)["comments"] == ["a"]
    assert result.tokens_saved == 60
    assert result.transforms_applied == ("smart_crusher",)


def test_headroom_adapter_fails_closed_when_a_required_source_field_changes() -> None:
    def compress(messages, *, model):
        return SimpleNamespace(
            messages=[messages[0], {"role": "tool", "content": '{"record_number": 8}'}],
            tokens_before=10,
            tokens_after=5,
            tokens_saved=5,
            compression_ratio=0.5,
            transforms_applied=["smart_crusher"],
        )

    content = '{"record_number": 7, "source_revision": "pinned"}'
    result = HeadroomCompressor(compress).compress_json(
        content, required_fields=("record_number", "source_revision")
    )

    assert result.content == content
    assert result.applied is False
    assert result.fallback_reason == "required_source_field_changed"


def test_headroom_adapter_fails_closed_for_invalid_json_or_third_party_failure() -> None:
    def invalid(_messages, *, model):
        return SimpleNamespace(messages=[{}, {"role": "tool", "content": "not json"}])

    result = HeadroomCompressor(invalid).compress_json('{"record_number": 7}')
    assert result.content == '{"record_number": 7}'
    assert result.fallback_reason == "compression_error:JSONDecodeError"


def test_headroom_adapter_requires_exact_pinned_version() -> None:
    with pytest.raises(HeadroomUnavailableError, match="0.5.18"):
        HeadroomCompressor(lambda *_args, **_kwargs: None, installed_version="0.5.19")


def test_headroom_audit_aggregates_applied_and_fallback_payloads() -> None:
    config = HeadroomAblationConfig()
    assert config.version == HEADROOM_VERSION

    def compress(messages, *, model):
        return SimpleNamespace(
            messages=messages,
            tokens_before=12,
            tokens_after=12,
            tokens_saved=0,
            compression_ratio=0.0,
            transforms_applied=[],
        )

    no_change = HeadroomCompressor(compress).compress_json('{"record_number": 7}')
    failed = HeadroomCompressor(compress).compress_json("not json")
    audit = aggregate_headroom((no_change, failed))
    assert audit == {
        "attempted_payloads": 2,
        "applied_payloads": 0,
        "fallback_payloads": 1,
        "tokens_before": 12,
        "tokens_after": 12,
        "tokens_saved": 0,
        "fallback_reasons": {"original_not_json:JSONDecodeError": 1},
    }


@pytest.mark.headroom
def test_pinned_headroom_package_compresses_a_real_tool_payload() -> None:
    pytest.importorskip("headroom")
    payload = {
        "record_number": 42,
        "source_revision": "pinned",
        "comments": [f"comment {index}: source-grounded evidence " * 20 for index in range(40)],
    }
    result = HeadroomCompressor.installed().compress_json(
        json.dumps(payload), required_fields=("record_number", "source_revision")
    )

    assert result.applied is True
    assert result.tokens_saved > 0
    assert json.loads(result.content)["record_number"] == 42
