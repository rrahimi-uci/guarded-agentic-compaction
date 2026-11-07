"""Provider-free continuation parity and fail-closed dispatch checks."""
import copy
import json
from pathlib import Path
import tarfile

from bird_one_call_continuation_preflight import canonical_first_message
from bird_one_call_matched_pilot import prepare_prefix, current_manifest, PILOT, CANDIDATE


class FakeTools:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def call(self, name, arguments):
        self.calls.append((name, arguments))
        return self.result


def test_handwritten_and_candidate_prefixes_have_same_model_continuation():
    candidate = json.loads(CANDIDATE.read_text())
    task = json.loads((PILOT / "seal.json").read_text())["tasks"][0]
    with tarfile.open(PILOT / "raw_evidence.tar.gz", "r:gz") as archive:
        baseline = json.load(archive.extractfile(
            f"v2/{task['question_id']}-baseline/result.json"))
    result = baseline["tool_calls"][0]["result"]
    manual = FakeTools(result)
    compiled = FakeTools(result)
    question = {"db_id": task["db_id"]}
    manual_messages, manual_disposition = prepare_prefix(question, manual, "manual_one_call", candidate)
    candidate_messages, candidate_disposition = prepare_prefix(question, compiled, "candidate_one_call", candidate)
    assert manual_messages == candidate_messages
    assert manual.calls == compiled.calls == [("list_tables", {})]
    assert canonical_first_message(manual_messages[0]) == canonical_first_message(
        baseline["provider_trace"][0]["response"]["choices"][0]["message"])
    assert manual_disposition["outcome"] == "manual_prefix"
    assert candidate_disposition["outcome"] == "candidate_prefix"
    assert candidate_disposition["candidate_admitted"] is False


def test_candidate_guard_rejects_manifest_drift_without_tool_effect():
    candidate = copy.deepcopy(json.loads(CANDIDATE.read_text()))
    candidate["manifest"]["policy_hash"] = "changed-policy"
    tools = FakeTools({"payload": '{"tables": []}'})
    messages, disposition = prepare_prefix({"db_id": "any"}, tools,
                                           "candidate_one_call", candidate)
    assert messages == []
    assert tools.calls == []
    assert disposition["outcome"] == "fallback_guard"


def test_candidate_verifier_rejects_unseen_table_payload_after_one_read():
    candidate = json.loads(CANDIDATE.read_text())
    tools = FakeTools({"payload": '{"tables": ["UNSEEN_TABLE"]}'})
    messages, disposition = prepare_prefix({"db_id": "any"}, tools,
                                           "candidate_one_call", candidate)
    assert messages == []
    assert tools.calls == [("list_tables", {})]
    assert disposition["outcome"] == "fallback_verifier"


def test_manifest_rebuild_detects_policy_drift():
    candidate = copy.deepcopy(json.loads(CANDIDATE.read_text()))
    current_manifest(candidate)
    candidate["manifest"]["policy_hash"] = "changed-policy"
    try:
        current_manifest(candidate)
    except ValueError:
        pass
    else:
        raise AssertionError("manifest drift was accepted")
