"""Source acquisition policy, caching, checksums, and SEC gate tests."""

from __future__ import annotations

import io
import json
import urllib.error
from email.message import Message
from pathlib import Path

import pytest

from benchmarks.fetch.common import (
    SourceClient,
    SourceFetchError,
    SourcePolicyError,
    validate_sec_user_agent,
)
from benchmarks.fetch.sec import sec_client


class _Response(io.BytesIO):
    status = 200

    def __init__(
        self,
        payload: bytes,
        *,
        content_length: str | None = None,
        status: int = 200,
    ) -> None:
        super().__init__(payload)
        self.status = status
        headers = Message()
        headers["Content-Type"] = "application/json"
        headers["ETag"] = "public-etag"
        if content_length is not None:
            headers["Content-Length"] = content_length
        self.headers = headers

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def test_source_client_caches_atomically_and_redacts_request_headers(tmp_path, monkeypatch) -> None:
    calls = []

    def open_request(request, timeout):
        calls.append((request, timeout))
        return _Response(b'{"real":"public-record"}')

    monkeypatch.setattr("urllib.request.urlopen", open_request)
    client = SourceClient(tmp_path, user_agent="project contact@example.org")
    first = client.fetch("https://example.org/public.json", namespace="test")
    second = client.fetch("https://example.org/public.json", namespace="test")
    assert not first.cache_hit and second.cache_hit
    assert len(calls) == 1
    assert first.sha256 == second.sha256
    metadata = json.loads(Path(first.path).with_suffix(".metadata.json").read_text())
    assert metadata["response_headers"] == {
        "Content-Type": "application/json",
        "ETag": "public-etag",
    }
    assert "contact@example.org" not in json.dumps(metadata)


def test_source_client_rejects_insecure_or_missing_offline_sources(tmp_path) -> None:
    client = SourceClient(tmp_path, user_agent="public client")
    with pytest.raises(SourcePolicyError, match="HTTPS"):
        client.fetch("http://example.org/data", namespace="test")
    with pytest.raises(SourceFetchError, match="not cached"):
        client.fetch("https://example.org/data", namespace="test", offline=True)
    with pytest.raises(SourcePolicyError, match="namespace"):
        client.fetch(
            "https://example.org/data", namespace="../outside", offline=True
        )


def test_source_client_enforces_aggregate_cache_cap_before_download(tmp_path, monkeypatch) -> None:
    (tmp_path / "existing.bin").write_bytes(b"12345678")
    called = False

    def open_request(request, timeout):
        nonlocal called
        called = True
        return _Response(b"more")

    monkeypatch.setattr("urllib.request.urlopen", open_request)
    client = SourceClient(
        tmp_path,
        user_agent="public client",
        max_cache_bytes=8,
    )
    with pytest.raises(SourcePolicyError, match="cache"):
        client.fetch("https://example.org/new.json", namespace="test")
    assert not called


def test_source_client_rejects_corrupt_cache_and_truncated_download(
    tmp_path, monkeypatch
) -> None:
    client = SourceClient(tmp_path, user_agent="public client")
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda request, timeout: _Response(b"good")
    )
    record = client.fetch("https://example.org/good.json", namespace="test")
    Path(record.path).write_bytes(b"tampered")
    with pytest.raises(SourceFetchError, match="checksum"):
        client.fetch("https://example.org/good.json", namespace="test", offline=True)

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _Response(b"short", content_length="20"),
    )
    with pytest.raises(SourceFetchError, match="body length"):
        client.fetch("https://example.org/truncated.json", namespace="truncated")
    assert not list((tmp_path / "truncated").glob("*.bin"))
    assert not list((tmp_path / "truncated").glob("*.metadata.json"))


def test_source_client_rejects_stream_overflow_invalid_length_and_policy_status(
    tmp_path, monkeypatch
) -> None:
    client = SourceClient(tmp_path, user_agent="public client", max_bytes=4)
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda request, timeout: _Response(b"12345")
    )
    with pytest.raises(SourceFetchError, match="maximum"):
        client.fetch("https://example.org/overflow", namespace="overflow")

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _Response(b"x", content_length="invalid"),
    )
    with pytest.raises(SourceFetchError, match="Content-Length"):
        client.fetch("https://example.org/invalid", namespace="invalid")

    def forbidden(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 403, "forbidden", {}, None)

    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    with pytest.raises(SourcePolicyError, match="policy status 403"):
        client.fetch("https://example.org/forbidden", namespace="policy")


def test_sec_user_agent_requires_entity_and_contact() -> None:
    for invalid in (None, "", "anonymous", "contact@example.org"):
        with pytest.raises(SourcePolicyError, match="SEC_USER_AGENT"):
            validate_sec_user_agent(invalid)
    assert validate_sec_user_agent("Agent Compaction contact@example.org")


def test_sec_client_is_shared_for_online_throttling_and_offline_needs_no_contact(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    offline = sec_client(tmp_path, offline=True)
    assert "offline" in offline.user_agent
    monkeypatch.setenv("SEC_USER_AGENT", "Agent Compaction contact@example.org")
    assert sec_client(tmp_path) is sec_client(tmp_path)
