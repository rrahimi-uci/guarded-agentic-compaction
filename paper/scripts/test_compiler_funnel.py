"""Unit tests for the same-IR compiler funnel (no corpus or provider needed)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


cf = _load("compiler_funnel")
from guarded_agentic_compaction.grc.dsl import Const  # noqa: E402
from guarded_agentic_compaction.grc.synthesize import BindingResult  # noqa: E402


def test_majority_fallback_binds_modal_literal_only_when_grounding_refuses():
    log: list = []

    def refusing(slot_path, envs, targets, groups, *, ctx, literal_only=False):
        return BindingResult(None, "no_consistent_expression")

    wrapped = cf.majority_fallback(refusing, log)
    res = wrapped("limit", [{}] * 5, [100, 100, 1, 100, 1], ["g"] * 5, ctx=None)
    assert res.ok and isinstance(res.binding, Const) and res.binding.value == 100
    assert log == [{"slot": "limit", "grounding_reason": "no_consistent_expression", "modal_value": 100,
                    "modal_share": 0.6, "n_targets": 5, "distinct_values": 2}]
    # ties break lexically on the serialized value; a grounded result passes through untouched
    tie = wrapped("x", [{}] * 2, ["b", "a"], ["g", "g"], ctx=None)
    assert tie.binding.value == "a"

    def grounded(slot_path, envs, targets, groups, *, ctx, literal_only=False):
        return BindingResult(Const(7))

    assert cf.majority_fallback(grounded, log)("y", [{}], [7], ["g"], ctx=None).binding.value == 7
    assert len(log) == 2


def test_config_factory_forces_alpha_and_extra_fields():
    make = cf.config_factory(1.0, freeze_one_candidate_before_calibration=True)
    cfg = make(entry_schema=("record_number",), alpha=0.05, w_max=3)
    assert cfg.alpha == 1.0 and cfg.freeze_one_candidate_before_calibration and cfg.w_max == 3
    assert cf.config_factory(0.05)(alpha=1.0).alpha == 0.05


def _cand(cid, tools, stage, rejected=None, notes=None):
    return {"candidate_id": cid, "tools": tools, "stage": stage, "rejected": rejected, "removed_requests": len(tools),
            "notes": notes or {}, "program": None, "gate": None}


def test_divergence_lists_candidates_emitted_elsewhere_but_not_by_full():
    full = {"candidates": [_cand("cand-00-aaa", ["a", "b", "c"], "synthesized", "ungroundable_slot:c.limit"),
                           _cand("cand-01-bbb", ["a", "b"], "emitted")]}
    other = {"candidates": [_cand("cand-00-aaa", ["a", "b", "c"], "emitted",
                                  notes={"gate_calibration_samples": 92, "gate_calibration_violations": 0,
                                         "gate_calibration_unproductive": 1}),
                            _cand("cand-01-bbb", ["a", "b"], "dominated", "dominated_by_longer_region")]}
    div = cf.divergence({"full": full, "recurrence_only": other, "support_only": full})
    assert len(div) == 1
    d = div[0]
    assert d["policy"] == "recurrence_only" and d["full_stage"] == "synthesized"
    assert d["calibration_replay"]["gate_calibration_violations"] == 0
    assert d["calibration_replay"]["gate_calibration_unproductive"] == 1


def test_table_renders_divergence_and_null_rows():
    row = lambda cohort, arts, div: {  # noqa: E731
        "cohort": cohort, "policies": {p: {"artifacts": [{"tools": t, "gate_retire": False} for t in arts[p]]} for p in cf.POLICIES},
        "divergence": div,
    }
    results = {"cohorts": [
        row("issue_type", {"full": [["a", "b"]], "support_only": [["a", "b"]], "recurrence_only": [["a", "b", "c"]], "stats_only": [["a", "b", "c"]]},
            [{"policy": "recurrence_only", "tools": ["a", "b", "c"], "full_stage": "synthesized",
              "calibration_replay": {"gate_calibration_samples": 92, "gate_calibration_violations": 0, "gate_calibration_unproductive": 1}}]),
        row("django__django", {p: [["a", "b", "c"]] for p in cf.POLICIES}, []),
        {"cohort": "skipped", "skipped": "no local snapshot"},
    ]}
    text = cf.table(results)
    assert r"Issue-type routing & 2-read & 2-read & 3-read & 3-read & recurrence-only: 3-read (synthesized; 0/1 of 92) \\" in text
    assert r"django/django & 3-read & 3-read & 3-read & 3-read & none \\" in text
    assert "skipped" not in text


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
