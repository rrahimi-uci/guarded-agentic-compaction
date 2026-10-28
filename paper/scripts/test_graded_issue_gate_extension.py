"""Provider-free invariants for the sequential calibration extension of the issue gate."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "paper/scripts"))

import audit_graded_issue_gate_extension as audit  # noqa: E402
import graded_issue_gate_extension_preflight as extension  # noqa: E402
import graded_issue_gate_study as study  # noqa: E402
from guarded_agentic_compaction.grc.calibrate import GRID, CalibrationSample, calibrate_gate  # noqa: E402
from guarded_agentic_compaction.schema.artifacts import GateModel  # noqa: E402


def test_experiments_tree_is_scanned_for_spent_records(tmp_path: Path) -> None:
    nested = tmp_path / "generalization_gate" / "artifacts"
    nested.mkdir(parents=True)
    (nested / "seal.json").write_text('{"records": [{"issue_number": 4001}, {"record_number": 4002}]}\n')
    (tmp_path / "notes.md").write_text('"issue_number": 4003\n')
    assert extension.experiments_record_numbers(tmp_path) == {4001, 4002}
    assert extension.experiments_record_numbers(tmp_path / "missing") == set()


def test_binomial_floors_match_the_registered_bound() -> None:
    floors = extension.binomial_floors(max_violations=4)
    assert floors == {"0": 92, "1": 133, "2": 168, "3": 200, "4": 231}


def test_sealed_extension_matches_current_source_and_exclusions() -> None:
    sealed = json.loads(study.EXT_PREFLIGHT.read_text())
    assert sealed == extension.build()
    assert sealed["status"] == "sealed_not_run" and sealed["sequential_extension"] is True
    assert sealed["extension_size_forced_by_pool_exhaustion"] is True
    assert sealed["frozen_model"] == json.loads(extension.FROZEN_GATE.read_text())["frozen_model"]
    ids = [r["issue_number"] for r in sealed["fresh_calibration"]]
    assert ids == sorted(set(ids)) and len(ids) == sealed["remaining_pool"]["eligible_with_comments"]
    original = json.loads(extension.cohort.OUT.read_text())
    assert not set(ids) & {r["issue_number"] for rows in original["selected"].values() for r in rows}
    assert not sealed["pool_enlargement_check"]["any_shares_pinned_manifest"]


def _model() -> GateModel:
    return GateModel(features=("x",), weights=(1.0,), bias=0.0, feature_means=(0.0,), feature_scales=(1.0,))


def _samples(scores: list[float], violations: set[int]) -> list[CalibrationSample]:
    # score(x) = sigmoid(x); choose x so sigmoid(x) equals the requested q.
    import math

    return [CalibrationSample(group=f"g{i}", episode_id=f"issue:{i}", features={"x": math.log(q / (1 - q))},
                              unproductive=i in violations, violation=i in violations, eligible=True)
            for i, q in enumerate(scores)]


@pytest.mark.parametrize("mid_count, admitted", [(70, True), (60, False)])
def test_grid_recount_matches_algorithm_one(mid_count: int, admitted: bool) -> None:
    scores = [0.01] * 100 + [0.29] * mid_count + [0.9] * 10
    samples = _samples(scores, violations={5, 120})
    gate = calibrate_gate(samples, model=_model(), alpha=.05, delta=.10, seed=0)
    rows = audit.grid_rows(samples, _model())
    recorded = audit._rows_from_notes(gate.to_dict())
    assert [{k: r[k] for k in ("eta", "n", "violations", "upper", "coverage")} for r in rows] == recorded
    admissible = [r["eta"] for r in rows if r["admissible"]]
    assert rows[0]["n"] == 100 and rows[0]["violations"] == 1 and rows[-1]["n"] == 100 + mid_count
    if admitted:
        # two violations need 168 accepted groups: 170 at eta >= 0.30 admits, 160 does not
        assert admissible == [0.3, 0.4, 0.5] == list(gate.admissible) and gate.threshold == 0.5
    else:
        assert not admissible and gate.retire


def test_fisher_split_is_one_sided_and_descriptive() -> None:
    samples = _samples([0.01] * 50 + [0.4] * 50, violations={60, 61, 62, 63})
    split = audit.fisher_split(samples, _model(), 0.02)
    assert split["above"] == {"n": 50, "violations": 4} and split["at_or_below"] == {"n": 50, "violations": 0}
    assert 0 < split["one_sided_fisher_p"] < 0.1 and split["descriptive_only"]
    assert audit.fisher_split(samples, _model(), 0.5)["one_sided_fisher_p"] == 1.0


def test_extension_checkpoint_is_separate_and_pinned(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "checkpoint_extension.json"
    state = study._checkpoint("ext-sha", "cand-sha", 25.0, path=path, schema="gac-graded-issue-gate-checkpoint/extension-v1")
    path.write_text(json.dumps(state))
    with pytest.raises(ValueError, match="does not match"):
        study._checkpoint("ext-sha", "cand-sha", 25.0, path=path)  # the v2 schema must not resume it
    with pytest.raises(ValueError, match="does not match"):
        study._checkpoint("other-sha", "cand-sha", 25.0, path=path, schema="gac-graded-issue-gate-checkpoint/extension-v1")
    assert study.EXTENSION_CAP_USD == 25.0 and study.EXT_CHECKPOINT != study.CHECKPOINT


def test_retained_episodes_are_redacted_and_digest_linked(tmp_path: Path) -> None:
    from guarded_agentic_compaction.schema.traces import content_digest

    raw = {"events": [
        {"kind": "MODEL_REQ", "input": [{"encrypted_content": "opaque"}], "output": None},
        {"kind": "MODEL_RESP", "input": None, "output": ["ResponseReasoningItem(encrypted_content='x')", {"answer": 1}]},
    ]}

    class Episode:
        def to_dict(self) -> dict:
            import copy
            return copy.deepcopy(raw)

    class Result:
        issue_number = 4242
        trace_id = "trace-4242"
        episode = Episode()

    path = study.retain_episodes("phase_x", [Result()], root=tmp_path)
    data = json.loads(path.read_text())
    entry = data["episodes"][0]
    assert entry["episode_digest"] == content_digest(raw)
    assert entry["redacted_episode_digest"] == content_digest(entry["episode"]) != entry["episode_digest"]
    assert entry["reasoning_items_redacted"] == 1 and entry["encrypted_content_fields_redacted"] == 1
    assert "opaque" not in json.dumps(entry["episode"]) and "REDACTED_REASONING_ITEM" in json.dumps(entry["episode"])
    study.retain_episodes("phase_x", [Result()], root=tmp_path)
    assert len(json.loads(path.read_text())["episodes"]) == 2


@pytest.mark.skipif(not study.EXT_RESULT.exists(), reason="extension not executed")
def test_extension_table_regenerates_from_audit(tmp_path: Path, monkeypatch) -> None:
    committed = audit.TABLE_PATH.read_text(encoding="utf-8")
    monkeypatch.setattr(audit, "TABLE_PATH", tmp_path / "gate_extension.tex")
    assert audit.table() == committed
    data = json.loads(audit.AUDIT_PATH.read_text())
    assert len(data["grids"]["pooled"]["rows"]) == len(GRID) == 11
