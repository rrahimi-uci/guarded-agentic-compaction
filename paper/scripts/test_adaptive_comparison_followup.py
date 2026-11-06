"""Selection leakage, effect boundaries and retained-control integrity."""
import asyncio
import copy
import hashlib
import json
from pathlib import Path
import tarfile

import pytest

from adaptive_comparison_followup import select
from webarena_batched_control import batch, validate_batch, comparison_view, positive_passes

BASE = "http://127.0.0.1:12345"


def test_extension_is_outcome_blind_and_excludes_whole_prior_templates():
    rows = [{"task_id": i, "intent_template_id": i // 3, "sites": ["reddit"],
             "intent": "old", "eval": {"answer": "secret"}} for i in range(24)]
    prior = {"development": {"excluded_from_future_confirmation_templates": [0, 2]}}
    original = select(rows, prior)
    changed = copy.deepcopy(rows[::-1])
    for row in changed:
        row.update(intent="new", eval={"answer": "different", "outcome": "success"})
    assert select(changed, prior) == original
    assert not {0, 2} & {r["template_id"] for r in original["selected"]}
    assert len({r["template_id"] for r in original["selected"]}) == 4
    with pytest.raises(ValueError):
        select(rows + [rows[0]], prior)
    with pytest.raises(ValueError):
        select(rows[:3], prior)


@pytest.mark.parametrize("payload", [
    {"actions": []}, {"actions": [{"action": "observe"}] * 9},
    {"actions": [{"action": "evaluate", "value": "secret"}]},
    {"actions": [{"action": "goto", "value": "https://example.com"}]},
    {"actions": [{"action": "goto", "value": "http://127.0.0.1:9999"}]},
    {"actions": [{"action": "fill", "role": "textbox", "name": "x", "value": None}]},
    {"actions": [{"action": "click", "role": "button"}]},
    {"actions": [{"action": "observe", "script": "hidden"}]},
    {"actions": [{"action": "observe"}], "oracle": "secret"},
])
def test_invalid_batch_has_no_effect_even_when_invalid_action_is_last(payload):
    calls = []
    async def execute(*args):
        calls.append(args)
        return {"ok": True}
    with pytest.raises(ValueError):
        asyncio.run(batch(None, payload, BASE, execute=execute))
    assert calls == []


def test_invalid_tail_is_validated_before_first_write():
    calls = []
    async def execute(*args):
        calls.append(args)
    with pytest.raises(ValueError):
        asyncio.run(batch(None, {"actions": [
            {"action": "click", "role": "button", "name": "Post"},
            {"action": "goto", "value": "file:///etc/passwd"}]}, BASE, execute=execute))
    assert calls == []


def test_runtime_failure_stops_tail_and_retains_successful_prior_effects():
    calls = []
    async def execute(page, args, base):
        calls.append(args)
        if len(calls) == 2:
            raise RuntimeError("element missing")
        return {"page": "first action changed state"}
    payload = {"actions": [{"action": "observe"}] * 3}
    result = asyncio.run(batch(None, payload, BASE, execute=execute))
    assert len(calls) == len(result["actions"]) == 2
    assert result["stopped_on_error"] and result["completed_without_error"] == 1
    assert result["actions"][0]["observation"]["page"] == "first action changed state"
    assert result["actions"][1]["observation"]["error"] == "RuntimeError"


def test_cancellation_never_executes_tail_or_becomes_ordinary_action_error():
    calls = []
    async def execute(*args):
        calls.append(args)
        raise asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(batch(None, {"actions": [{"action": "observe"}] * 2}, BASE, execute=execute))
    assert len(calls) == 1


def test_validation_does_not_alias_caller_commands():
    payload = {"actions": [{"action": "observe"}]}
    validated = validate_batch(payload, BASE)
    payload["actions"][0]["action"] = "unknown"
    assert validated == [{"action": "observe"}]


def test_successful_grader_cannot_hide_timeout_or_missing_actions():
    commands = [{"action": "observe"}, {"action": "back"}]
    failed = [{"command": commands[0], "observation": {"error": "TimeoutError"}}]
    assert not positive_passes(failed, commands, "success")
    assert not positive_passes([], commands, "success")
    completed = [{"command": c, "observation": {"page": "ok"}} for c in commands]
    assert positive_passes(completed, commands, "success")
    assert not positive_passes(completed, commands, "failure")


def test_display_normalization_does_not_erase_semantic_changes_or_errors():
    raw = [{"command": {"action": "observe"}, "observation": {"url": BASE + "/x",
        "page": '- time: on November 6, 2026 at 5:18 PM\n- img "A tense emoji": (x)\n- paragraph: original'}}]
    later = copy.deepcopy(raw)
    later[0]["observation"]["page"] = later[0]["observation"]["page"].replace("5:18", "5:19").replace("(x)", "(y)")
    assert comparison_view(raw, BASE, 634) == comparison_view(later, BASE, 634)
    assert comparison_view(raw, BASE, 69) != comparison_view(later, BASE, 69)
    later[0]["observation"]["page"] += "\n- paragraph: changed task content"
    assert comparison_view(raw, BASE, 634) != comparison_view(later, BASE, 634)
    assert "5:18" in raw[0]["observation"]["page"]


def test_retained_control_versions_and_source_snapshots_are_complete():
    root = Path(__file__).resolve().parents[2]
    parent = root / "paper/results/adaptive_comparison_followup"
    for name, expected in (("batch_controls", False), ("batch_controls_v2", True)):
        directory = parent / name
        report = json.loads((directory / "report.json").read_text())
        seal = json.loads((directory / "seal.json").read_text())
        assert report["scheduled"] == 9 and report["all_passed"] is expected
        archive = directory / "raw_evidence.tar.gz"
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == report["archive_sha256"]
        with tarfile.open(archive) as tar:
            for row in report["files"]:
                blob = tar.extractfile(row["path"]).read()
                assert len(blob) == row["bytes"]
                assert hashlib.sha256(blob).hexdigest() == row["sha256"]
            for path, digest in seal["sources"].items():
                assert hashlib.sha256(tar.extractfile("source/" + path).read()).hexdigest() == digest
            records = []
            for scheduled in seal["scheduled"]:
                path = f"{scheduled['task_id']}-{scheduled['mode']}/record.json"
                record = json.load(tar.extractfile(path))
                records.append(record)
                assert record["status"] == "completed" and record["provider_calls"] == 0
                if name.endswith("v2"):
                    assert record["passed"]
                    assert record["normalized_actions"] == comparison_view(record["actions"], record["base"], record["task_id"])
                    if scheduled["mode"] in {"batch", "sequential"}:
                        commands = next(f["commands"] for f in seal["fixtures"] if f["task_id"] == record["task_id"])
                        assert positive_passes(record["actions"], commands, record["evaluation"]["status"])
                    else:
                        assert record["evaluation"]["status"] == "failure"
                        if scheduled["mode"] == "first_error":
                            assert len(record["actions"]) == 1 and record["stopped_on_error"]
            assert sum(r["passed"] for r in records) == report["passed"]
            for pair in report["pairs"]:
                a, b = [next(r for r in records if r["task_id"] == pair["task_id"] and r["mode"] == m) for m in ("sequential", "batch")]
                key = "actions_equal_after_declared_display_normalization" if name.endswith("v2") else "actions_equal_after_origin_normalization"
                assert pair[key] == (a["normalized_actions"] == b["normalized_actions"])
                assert pair["action_count"] == len(b["actions"])
        if name.endswith("v2"):
            for path, digest in seal["sources"].items():
                assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest


def test_retained_selection_excludes_new_development_templates():
    root = Path(__file__).resolve().parents[2]
    value = json.loads((root / "paper/results/adaptive_comparison_followup/selection.json").read_text())
    assert {r["task_id"] for r in value["selected"]} == {613, 626, 714, 647}
    assert {r["template_id"] for r in value["selected"]} <= set(value["excluded_from_future_confirmation_templates"])
    assert value["provider_calls"] == 0
    for rel, digest in value["source_hashes"].items():
        if not rel.startswith("benchmarks/.cache/"):
            assert hashlib.sha256((root / rel).read_bytes()).hexdigest() == digest
