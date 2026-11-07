"""Integrity and behavioral guards for the exposed Reddit development study."""
import hashlib
import json
from pathlib import Path
import tarfile

import pytest

from reddit_ranked_read_feasibility import TOP_PATH, staged_request_allowed
from reddit_batched_adaptive_pilot import validate_batch
from reddit_batched_adaptive_pilot_v2 import bounded_batch_messages, model_view

BASE = "http://127.0.0.1:12345"
ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("url,method,resource,expected", [
    (BASE + "/", "GET", "document", True),
    (BASE + TOP_PATH, "GET", "document", True),
    (BASE + "/f/books/top", "GET", "document", False),
    (BASE + TOP_PATH + "?t=all", "GET", "document", False),
    (BASE + TOP_PATH, "POST", "fetch", False),
    ("https://example.com/f/gadgets/top", "GET", "document", False),
    ("file:///etc/passwd", "GET", "document", False),
    (BASE + "/submit", "GET", "document", False),
])
def test_stage_route_policy(url, method, resource, expected):
    assert staged_request_allowed(url, BASE, method, resource) is expected


def test_batch_validates_all_commands_before_effects():
    valid = {"actions": [
        {"action": "goto", "value": BASE + TOP_PATH},
        {"action": "click", "role": "button", "name": "Downvote", "index": 0},
    ]}
    assert validate_batch(valid, BASE) == valid["actions"]
    for tail in (
        {"action": "goto", "value": "https://example.com"},
        {"action": "click", "role": "button", "name": "Downvote", "index": True},
        {"action": "click", "role": "button", "name": "Downvote", "index": -1},
    ):
        with pytest.raises(ValueError):
            validate_batch({"actions": valid["actions"] + [tail]}, BASE)
    with pytest.raises(ValueError):
        validate_batch({"actions": valid["actions"] * 5}, BASE)


def test_model_view_preserves_raw_and_caps_history():
    raw = {"actions": [{"command": {"action": "observe"},
                         "observation": {"page": "x" * 8000, "url": BASE}}]}
    visible = model_view(raw)
    assert raw["actions"][0]["observation"]["page"] == "x" * 8000
    assert len(visible["actions"][0]["observation"]["page"]) == 6000
    assert visible["actions"][0]["observation"]["model_view_truncated"]
    messages = [{"role": "tool", "content": str(i)} for i in range(4)]
    bounded = bounded_batch_messages(messages)
    assert [m["content"] for m in bounded[-2:]] == ["2", "3"]
    assert all("omitted" in m["content"] for m in bounded[:2])


@pytest.mark.parametrize("directory", [
    "reddit_ranked_read_feasibility", "reddit_ranked_read_feasibility_v2",
    "reddit_ranked_read_feasibility_v3", "reddit_batched_adaptive_pilot",
    "reddit_batched_adaptive_pilot_v2", "reddit_ranked_one_batch_control",
])
def test_retained_archive_and_source_hashes(directory):
    out = ROOT / "paper/results" / directory
    report = json.loads((out / "report.json").read_text())
    seal = json.loads((out / "seal.json").read_text())
    archive = out / "raw_evidence.tar.gz"
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == report["archive_sha256"]
    with tarfile.open(archive) as tar:
        for item in report["files"]:
            blob = tar.extractfile(item["path"]).read()
            assert len(blob) == item["bytes"]
            assert hashlib.sha256(blob).hexdigest() == item["sha256"]
        for rel, digest in seal["sources"].items():
            blob = tar.extractfile("source/" + rel).read()
            assert hashlib.sha256(blob).hexdigest() == digest
            assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest
    if directory == "reddit_ranked_read_feasibility":
        assert report["scheduled"] == 5 and report["passed"] == 4
        assert not report["all_passed"]
    elif directory == "reddit_ranked_read_feasibility_v2":
        assert (out / "TERMINAL_WARNING.md").exists()
    elif directory == "reddit_ranked_read_feasibility_v3":
        assert report["all_passed"] and report["outcome"]["vote_response_bytes"] > 0
    elif directory == "reddit_batched_adaptive_pilot":
        assert report["status"] == "failed" and report["official_status"] is None
    elif directory == "reddit_batched_adaptive_pilot_v2":
        assert report["status"] == "completed" and report["official_status"] == "success"
    else:
        assert report["passed"] and report["official_status"] == "success"
        assert report["actions"] == 2 and report["provider_calls"] == 0


def test_amendment_hash_chain_survives_export_recovery():
    results = ROOT / "paper/results"
    chain = [
        ("reddit_ranked_read_feasibility_v2", "reddit_ranked_read_feasibility", "v1"),
        ("reddit_ranked_read_feasibility_v3", "reddit_ranked_read_feasibility_v2", "v2"),
        ("reddit_batched_adaptive_pilot", "reddit_ranked_read_feasibility_v3", "control"),
        ("reddit_batched_adaptive_pilot_v2", "reddit_batched_adaptive_pilot", "v1"),
        ("reddit_ranked_one_batch_control", "reddit_batched_adaptive_pilot_v2", "baseline"),
    ]
    for later, earlier, prefix in chain:
        seal = json.loads((results / later / "seal.json").read_text())
        for name, suffix in (("report.json", "report"), ("raw_evidence.tar.gz", "archive")):
            digest = hashlib.sha256((results / earlier / name).read_bytes()).hexdigest()
            assert digest == seal[f"{prefix}_{suffix}_sha256"]
