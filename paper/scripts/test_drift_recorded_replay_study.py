"""Pin the pure helpers of ``drift_recorded_replay_study.py`` and the retained run's reading."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drift_recorded_replay_study as drift  # noqa: E402


def test_holm_step_down() -> None:
    assert drift.holm({"a": 0.01, "b": 0.04}) == {"a": pytest.approx(0.02), "b": pytest.approx(0.04)}
    assert drift.holm({"a": 1.0, "b": 1.0}) == {"a": 1.0, "b": 1.0}
    assert drift.holm({"a": 0.03, "b": 0.01}) == {"b": pytest.approx(0.02), "a": pytest.approx(0.03)}


def test_pairing_and_decision() -> None:
    a = {"r1": True, "r2": False, "r3": False}
    b = {"r1": False, "r2": True, "r3": False}
    pair = drift._pair(a, b)
    assert (pair["n"], pair["first_only_wrong"], pair["second_only_wrong"], pair["both_wrong"]) == (3, 1, 1, 0)
    assert pair["mcnemar_exact_p"] == 1.0
    base = {"paired_records": 10, "wrong_records": {"compiled_guarded": 0, "compiled_unverified": 0, "manual_unverified": 0}}
    assert drift.decision(base) == "null:all_arms_zero_wrong"
    assert drift.decision({**base, "wrong_records": {**base["wrong_records"], "manual_unverified": 2}}).startswith("program_separates")
    assert drift.decision({**base, "wrong_records": {**base["wrong_records"], "compiled_unverified": 1, "manual_unverified": 2}}).startswith("verifier_separates")
    assert drift.decision({**base, "wrong_records": {**base["wrong_records"], "compiled_guarded": 1, "compiled_unverified": 3}}).startswith("adverse")
    assert drift.cp_upper(0, 89) == pytest.approx(0.0331, abs=5e-4)


def test_retained_run_reads_as_the_null() -> None:
    res = json.loads((drift.ROOT / "paper/results/drift_recorded_replay/results.json").read_text())
    assert drift.decision(res["pooled"]) == res["decision"] == "null:all_arms_zero_wrong"
    assert drift.pooled(res["families"])["paired_records"] == 89
