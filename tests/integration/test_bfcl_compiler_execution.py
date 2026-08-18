"""The sealed BFCL gold-plan compiler artifact keeps its exact, fail-closed shape.

No benchmark checkout is needed: the pinned upstream imports live inside ``Backend``, so the
driver's pure helpers are importable on their own, and the committed artifact carries every
number this test pins.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "paper" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import bfcl_compiler_benchmark as driver  # noqa: E402


RESULT = ROOT / "paper/results/external_benchmarks/bfcl_compiler_execution.json"


def _result() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_executed_corpus_is_complete_and_exactly_replayable() -> None:
    result = _result()

    assert result["source_revision"] == driver.REVISION
    assert result["dataset"]["tasks"] == 200
    assert result["dataset"]["observed_calls"] == 1142
    assert result["dataset"]["complete_observed_traces"] == 200
    assert result["dataset"]["independent_groups"] == 200
    assert result["dataset"]["unique_tools"] == 81
    assert result["dataset"]["compilable_tools"] == 34
    assert result["catalog_coverage"]["undeclared"] == []
    assert result["execution_audit"]["error_results"] == 0
    assert result["replay_oracle"]["compared_calls"] == 1142
    assert result["replay_oracle"]["mismatched_calls"] == 0
    assert result["replay_oracle"]["exact_replay_rate"] == 1.0


def test_effect_declarations_are_never_looser_than_observed_behaviour() -> None:
    result = _result()

    mutation = result["execution_audit"]["state_mutation_audit"]
    assert mutation["mutating_calls"] == 1060
    assert mutation["rng_advancing_calls"] == 94
    assert mutation["tools_observed_mutating"] == 44
    assert result["catalog_audits"] == {
        "compilable_declarations_observed_advancing_rng": 0,
        "pure_declarations": 3,
        "read_like_declarations_observed_mutating": 0,
    }
    for name, row in mutation["by_tool"].items():
        if row["mutating_calls"]:
            assert not row["declared_compilable"], name
        if row["rng_advancing_calls"]:
            assert not row["declared_compilable"], name


def test_gate_retires_every_family_as_pre_registered() -> None:
    result = _result()

    compiler = result["compiler"]
    assert compiler["candidate_windows"] == 146
    assert compiler["candidate_families"] == 77
    assert compiler["families_support_ge_3"] == 9
    assert compiler["maximum_family_support"] == 15
    assert compiler["held_out_recorded_replay"]["families_synthesized"] == 4
    assert compiler["held_out_recorded_replay"]["test_passed"] == 3
    assert compiler["held_out_recorded_replay"]["test_abstained"] == 3
    assert compiler["held_out_recorded_replay"]["test_wrong"] == 0
    assert compiler["exact_gate"]["minimum_zero_violation_groups"] == 92
    assert compiler["exact_gate"]["outcome"] == "RETIRE"
    assert compiler["exact_gate"]["certifiable_families_even_if_zero_violations"] == 0

    pre = result["preregistration"]
    assert pre["predeclared_gate_outcome"] == driver.PREDECLARED_GATE_OUTCOME == "RETIRE"
    assert pre["observed_gate_outcome"] == "RETIRE"
    assert pre["prediction_held"] is True
    assert (ROOT / pre["protocol"]).exists()


def test_claim_boundary_stays_fail_closed() -> None:
    evidence = _result()["evidence"]

    assert evidence["compiler_execution"] is True
    assert evidence["provider_calls"] == 0
    for key in (
        "prompts_arguments_outputs_serialized",
        "is_real_world_demo",
        "is_live_provider_evaluation",
        "licenses_end_to_end_planning_quality_claim",
        "licenses_function_calling_accuracy_claim",
        "licenses_production_safety_claim",
    ):
        assert evidence[key] is False, key


def test_observed_result_parsing_keeps_unparseable_payloads_verbatim() -> None:
    assert driver._parse_observed('{"a": 1}') == ({"a": 1}, "json")
    assert driver._parse_observed("['x', 'y']") == (["x", "y"], "literal")
    assert driver._parse_observed("None") == (None, "literal")
    # mpmath repr is neither JSON nor a Python literal; it must survive unchanged.
    raw = "{'result': mpf('2.0')}"
    assert driver._parse_observed(raw) == (raw, "raw_string")


def test_parse_kind_counts_cover_every_observed_call() -> None:
    result = _result()

    kinds = result["execution_audit"]["observed_output_parse"]

    assert sum(kinds.values()) == result["dataset"]["observed_calls"]
    assert kinds == {"json": 1082, "literal": 56, "raw_string": 4}
