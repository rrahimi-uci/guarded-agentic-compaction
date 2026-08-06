from __future__ import annotations

import pytest

from guarded_agentic_compaction.benchmarking import (
    EvidenceSubstrate,
    ReferenceAction,
    ReferenceTask,
    analyze_reference_tasks,
    reference_task_to_episode,
)
from guarded_agentic_compaction.schema.effects import EffectClass
from guarded_agentic_compaction.schema.traces import ExecutionManifest
from benchmarks.external import screening_effect


def _task(
    task_id: str,
    actions: tuple[ReferenceAction, ...],
    *,
    revision: str = "a" * 40,
    group_id: str | None = None,
) -> ReferenceTask:
    return ReferenceTask(
        benchmark="fixture",
        task_id=task_id,
        group_id=group_id or f"group:{task_id}",
        source_revision=revision,
        substrate=EvidenceSubstrate.EXECUTABLE_PUBLIC_BENCHMARK,
        actions=actions,
    )


def test_reference_screening_separates_read_regions_and_barriers() -> None:
    tasks = (
        _task(
            "one",
            (
                ReferenceAction(name="get_record", effect=EffectClass.READ_LOCAL),
                ReferenceAction(name="get_labels", effect=EffectClass.READ_LOCAL),
                ReferenceAction(name="update_record", effect=EffectClass.WRITE_REVERSIBLE),
                ReferenceAction(name="get_record", effect=EffectClass.READ_LOCAL),
            ),
        ),
        _task(
            "two",
            (
                ReferenceAction(name="get_record", effect=EffectClass.READ_LOCAL),
                ReferenceAction(name="get_labels", effect=EffectClass.READ_LOCAL),
                ReferenceAction(name="mystery", effect=EffectClass.UNKNOWN),
            ),
        ),
    )

    analysis = analyze_reference_tasks(tasks)

    assert analysis.tasks == 2
    assert analysis.total_actions == 7
    assert analysis.read_like_actions == 5
    assert analysis.tasks_with_candidate_region == 2
    assert analysis.maximum_read_region == 2
    assert analysis.recurrent_candidate_families == 1
    assert analysis.maximum_candidate_family_support == 2
    assert analysis.block_reason_counts == {
        "EFFECT_WRITE_REVERSIBLE": 1,
        "UNKNOWN_EFFECT": 1,
    }
    assert analysis.as_dict()["notes"] == [
        "reference-plan screening only; not a GAC execution result"
    ]


def test_reference_screening_rejects_revision_pooling() -> None:
    action = ReferenceAction(name="get_record", effect=EffectClass.READ_LOCAL)
    with pytest.raises(ValueError, match="cannot pool"):
        analyze_reference_tasks((_task("one", (action,)), _task("two", (action,), revision="b" * 40)))


def test_reference_family_support_counts_independent_groups_not_occurrences() -> None:
    region = (
        ReferenceAction(name="get_record", effect=EffectClass.READ_LOCAL),
        ReferenceAction(name="get_labels", effect=EffectClass.READ_LOCAL),
    )
    barrier = (ReferenceAction(name="update", effect=EffectClass.WRITE_REVERSIBLE),)
    analysis = analyze_reference_tasks(
        (
            _task("variant-a", region + barrier + region, group_id="lineage:1"),
            _task("variant-b", region, group_id="lineage:1"),
            _task("independent", region, group_id="lineage:2"),
        )
    )

    assert analysis.independent_groups == 2
    assert analysis.candidate_family_support == {"get_record -> get_labels": 2}
    assert analysis.maximum_candidate_family_support == 2


def test_reference_contracts_reject_invalid_runtime_types() -> None:
    with pytest.raises(ValueError, match="output_observed"):
        ReferenceAction(name="get_record", output_observed=1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="substrate"):
        ReferenceTask(
            benchmark="fixture",
            task_id="task",
            group_id="group",
            source_revision="a" * 40,
            substrate="simulation",  # type: ignore[arg-type]
        )


def test_reference_episode_requires_observed_results() -> None:
    task = _task(
        "incomplete",
        (ReferenceAction(name="get_record", effect=EffectClass.READ_LOCAL),),
    )
    manifest = ExecutionManifest(manifest_id="fixture")
    with pytest.raises(ValueError, match="lacks observed tool results"):
        reference_task_to_episode(task, manifest=manifest)


def test_complete_reference_trace_normalizes_to_episode() -> None:
    task = _task(
        "complete",
        (
            ReferenceAction(
                name="get_record",
                arguments={"id": "42"},
                output={"id": "42", "label": "ok"},
                output_observed=True,
                effect=EffectClass.READ_LOCAL,
            ),
            ReferenceAction(
                name="get_label",
                arguments={"id": "42"},
                output="ok",
                output_observed=True,
                effect=EffectClass.READ_LOCAL,
            ),
        ),
    )
    manifest = ExecutionManifest(manifest_id="fixture")

    episode = reference_task_to_episode(task, manifest=manifest)

    assert episode.n_requests() == 2
    assert [event.tool for event in episode.tool_calls()] == ["get_record", "get_label"]
    assert episode.envelope.external_state_version == "a" * 40
    assert episode.attributes["reference_task_digest"] == task.digest


@pytest.mark.parametrize(
    ("name", "method", "expected"),
    [
        ("get_order", None, EffectClass.READ_LOCAL),
        ("lookup", "GET", EffectClass.READ_EXTERNAL),
        ("update_order", None, EffectClass.WRITE_REVERSIBLE),
        ("lookup", "POST", EffectClass.WRITE_REVERSIBLE),
        ("ambiguous_action", None, EffectClass.UNKNOWN),
    ],
)
def test_screening_effect_is_conservative(
    name: str, method: str | None, expected: EffectClass
) -> None:
    assert screening_effect(name, method=method) is expected
