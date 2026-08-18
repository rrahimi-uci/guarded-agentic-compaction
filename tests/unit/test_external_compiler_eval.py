"""The shared external-benchmark compiler evaluation stays pinned to the promotion gate."""

from __future__ import annotations

from pathlib import Path

import yaml

from benchmarks.external.compiler_eval import evaluate_compiler, required_zero_violation_groups
from guarded_agentic_compaction.benchmarking import (
    EvidenceSubstrate,
    ReferenceAction,
    ReferenceTask,
    reference_task_to_episode,
)
from guarded_agentic_compaction.schema.effects import EffectCatalog, EffectClass
from guarded_agentic_compaction.schema.traces import ExecutionManifest, OutcomeLabels


ROOT = Path(__file__).resolve().parents[2]

CATALOG = EffectCatalog.model_validate(
    {
        "version": 1,
        "name": "fixture-read-catalog",
        "tools": {
            "get_record": {
                "effect": "READ_LOCAL",
                "capabilities": ["speculatable", "replayable", "cacheable"],
            },
            "get_label": {
                "effect": "READ_LOCAL",
                "capabilities": ["speculatable", "replayable", "cacheable"],
            },
            "update_record": {"effect": "WRITE_REVERSIBLE", "capabilities": []},
        },
    }
)


def _episode(index: int):
    task = ReferenceTask(
        benchmark="fixture",
        task_id=f"task-{index}",
        group_id=f"group-{index}",
        source_revision="b" * 40,
        substrate=EvidenceSubstrate.EXECUTABLE_PUBLIC_BENCHMARK,
        actions=(
            ReferenceAction(
                name="get_record",
                arguments={"id": f"{index}"},
                output={"id": f"{index}", "label": f"label-{index}"},
                output_observed=True,
                effect=EffectClass.READ_LOCAL,
            ),
            ReferenceAction(
                name="get_label",
                arguments={"label": f"label-{index}"},
                output={"ok": True},
                output_observed=True,
                effect=EffectClass.READ_LOCAL,
            ),
            ReferenceAction(
                name="update_record",
                arguments={"id": f"{index}"},
                output={"written": True},
                output_observed=True,
                effect=EffectClass.WRITE_REVERSIBLE,
            ),
        ),
    )
    return reference_task_to_episode(
        task,
        manifest=ExecutionManifest(manifest_id="fixture"),
        outcome=OutcomeLabels(task_success=True, semantic_score=1.0),
        entry_state={"inputs": {"id": f"{index}"}},
    )


def test_required_groups_match_the_pre_registered_promotion_config() -> None:
    promotion = yaml.safe_load(
        (ROOT / "configs/promotion.example.yaml").read_text(encoding="utf-8")
    )

    assert required_zero_violation_groups() == 92
    assert promotion["coverage"]["min_calibration_groups"] == 92


def test_small_corpus_retires_and_echoes_its_mining_parameters() -> None:
    episodes = [_episode(index) for index in range(6)]

    result = evaluate_compiler(
        episodes,
        CATALOG,
        ExecutionManifest(manifest_id="fixture"),
        entry_schema=("inputs", "environment"),
    )

    assert result["episodes"] == 6
    assert result["exact_gate"]["minimum_zero_violation_groups"] == 92
    # Six independent groups can never reach the exact zero-violation requirement.
    assert result["exact_gate"]["outcome"] == "RETIRE"
    assert result["exact_gate"]["certifiable_families_even_if_zero_violations"] == 0
    assert result["mining_parameters"] == {
        "entry_schema": ["inputs", "environment"],
        "max_depth": 2,
        "kappa": 3,
        "w_min": 2,
        "w_max": 12,
        "b_min": 2,
        "min_support_groups": 3,
        "n_permutations": 25,
    }
    assert result["held_out_recorded_replay"]["wrong_rate"] in (None, 0.0)


def test_write_barriers_are_reported_rather_than_compiled() -> None:
    episodes = [_episode(index) for index in range(4)]

    result = evaluate_compiler(episodes, CATALOG, ExecutionManifest(manifest_id="fixture"))

    assert result["blocked_window_candidates"].get("effect_write", 0) > 0
    assert "update_record" in result["blocked_by_tool"]
