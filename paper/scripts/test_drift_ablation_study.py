"""Pin the pure helpers of ``drift_ablation_study.py`` and the retained run's reading."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import drift_ablation_study as drift  # noqa: E402


def test_mcnemar_exact_and_bounds() -> None:
    assert drift.mcnemar_exact(0, 0) == 1.0
    assert drift.mcnemar_exact(0, 5) == pytest.approx(0.0625, abs=1e-9)
    assert drift.mcnemar_exact(3, 3) == 1.0
    assert drift.cp_upper(0, 0) is None
    assert drift.cp_upper(0, 144) == pytest.approx(0.0206, abs=5e-4)
    assert drift.cp_upper(2, 2) == 1.0


def test_family_key_drops_rank_only() -> None:
    assert drift._family_key("cand-03-9db61fc97412") == "9db61fc97412"
    assert drift._family_key("cand-04-9db61fc97412") == "9db61fc97412"
    assert drift._family_key("cand-02-2bd979e8666f-bec8e9f6") == "2bd979e8666f-bec8e9f6"
    assert drift._family_hash("cand-02-2bd979e8666f-bec8e9f6", True) == "2bd979e8666f"
    assert drift._family_hash("cand-01-merge:aa03daa10b", False) == "merge:aa03daa10b"


def test_decision_rule_order() -> None:
    base = {"paired_groups": 10, "guarded_only_wrong": 0, "unverified_only_wrong": 0, "both_wrong": 0}
    assert drift.decision(base) == "null:all_arms_zero_wrong"
    assert drift.decision({**base, "unverified_only_wrong": 1}).startswith("verifier_separates_arms")
    # an adverse guarded outcome takes precedence over everything else
    assert drift.decision({**base, "unverified_only_wrong": 3, "guarded_only_wrong": 1}).startswith("adverse")
    assert drift.decision({**base, "both_wrong": 1}).startswith("adverse")
    assert drift.decision({**base, "paired_groups": 0}) == "no_completed_artifact"


def test_retained_run_reads_as_the_null() -> None:
    res = json.loads((drift.ROOT / "paper/results/drift_ablation/results.json").read_text())
    assert drift.decision(res["pooled"]) == res["decision"] == "null:all_arms_zero_wrong"
    assert drift.pooled(res["demos"])["paired_groups"] == 144
