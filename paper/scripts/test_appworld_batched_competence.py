"""Guard adapted common-entry and batched API boundaries."""
import importlib.util
import hashlib
import json
from pathlib import Path

import pytest

from appworld_batched_competence import bounded_messages, model_view, public_reference_calls
import appworld_batched_trace_diagnostic as diagnostic

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("batched_worker", ROOT / "experiments/appworld_batched_competence/worker.py")
WORKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WORKER)


def test_reference_controls_remove_common_setup_and_bind_marker():
    raw = {"calls": [
        {"tool": "supervisor.show_profile", "arguments": {}},
        {"tool": "spotify.login", "arguments": {"username": "protected"}},
        {"tool": "spotify.show_song_library", "arguments": {"access_token": "protected", "page_index": 0}},
    ]}
    commands = public_reference_calls(raw)
    assert commands == [{"app": "spotify", "api": "show_song_library",
                         "arguments": {"access_token": "AUTO", "page_index": 0}}]
    assert raw["calls"][-1]["arguments"]["access_token"] == "protected"


def test_batch_validation_rejects_invalid_tail_before_execution():
    public = {("spotify", "show_song_library"), ("spotify", "login")}
    valid = {"app": "spotify", "api": "show_song_library",
             "arguments": {"access_token": "AUTO", "page_index": 0}}
    assert WORKER.validate_batch([valid], public) == [valid]
    for tail in (
        {"app": "private", "api": "hidden", "arguments": {}},
        {"app": "spotify", "api": "login", "arguments": {}},
        {"app": "spotify", "api": "show_song_library", "arguments": {"client": "bad"}},
        {"app": "spotify", "api": "show_song_library", "arguments": {"access_token": "secret"}},
    ):
        with pytest.raises(ValueError):
            WORKER.validate_batch([valid, tail], public)
    with pytest.raises(ValueError):
        WORKER.validate_batch([valid] * 9, public)


def test_model_history_cap_preserves_raw_result():
    raw = {"type": "batch_result", "calls": [{"result": "x" * 20000,
           "app": "spotify", "api": "show_song_library", "arguments": {}}]}
    visible = model_view(raw)
    assert raw["calls"][0]["result"] == "x" * 20000
    assert len(visible["calls"][0]["result"]["truncated_result_prefix"]) == 16000
    messages = [{"role": "tool", "content": str(i)} for i in range(4)]
    bounded = bounded_messages(messages)
    assert [row["content"] for row in bounded[-2:]] == ["2", "3"]
    assert all("omitted" in row["content"] for row in bounded[:2])


def test_trace_diagnostic_checks_hashes_and_excludes_protected_content(tmp_path, monkeypatch):
    monkeypatch.setattr(diagnostic, "PUBLIC", tmp_path / "public")
    cache = tmp_path / "cache"
    public = diagnostic.PUBLIC / "appworld_batched_competence"
    public.mkdir(parents=True)
    source = ROOT / "paper/scripts/appworld_batched_competence.py"
    seal = {"tasks": [f"case{i}" for i in range(12)],
            "source_hashes": {"paper/scripts/appworld_batched_competence.py":
                              hashlib.sha256(source.read_bytes()).hexdigest()}}
    (public / "seal.json").write_text(json.dumps(seal))
    hashes = []
    for task in seal["tasks"]:
        path = cache / "v1" / "episodes" / task / "record.json"
        path.parent.mkdir(parents=True)
        row = {"task_id": task, "status": "completed", "context": "PROTECTED_MARKER",
               "provider_trace": [], "batches": [], "api_calls": 0,
               "evaluation": {"success": task == "case0"}}
        path.write_text(json.dumps(row))
        hashes.append({"path": str(path.relative_to(cache / "v1")),
                       "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    (public / "report.json").write_text(json.dumps({"scheduled": 12,
        "official_successes": 1, "model_requests": 0, "api_calls": 0,
        "protected_raw_files": hashes}))
    result, _ = diagnostic.version_summary(cache, "v1", "appworld_batched_competence")
    assert result["verified_episode_hashes"] == 12
    assert "PROTECTED_MARKER" not in json.dumps(result)
    changed = cache / "v1/episodes/case0/record.json"
    changed.write_text(changed.read_text() + " ")
    with pytest.raises(ValueError, match="published protected-file hash"):
        diagnostic.version_summary(cache, "v1", "appworld_batched_competence")
