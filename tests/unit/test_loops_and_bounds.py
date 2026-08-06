"""Regression tests for pagination handling and unsafe-bound denominators.

All three behaviours here were found by adding Demo E (order-fulfillment), whose
read prefix is the first in the repository to combine a paginated call with two
conditional calls and a mandatory commitment.
"""

from __future__ import annotations

import pytest

from guarded_agentic_compaction.evaluation.metrics import EpisodeMetrics
from guarded_agentic_compaction.grc.dsl import Const, Expr
from guarded_agentic_compaction.grc.program import LoopStep, Predicate
from guarded_agentic_compaction.grc.synthesize import _loop_predicate_atoms


def _page(index: int, size: int, has_more: bool, cursor: str | None) -> dict[str, object]:
    return {
        "page": index,
        "has_more": has_more,
        "next_cursor": cursor,
        "status": "ok",
        "shipments": [{"shipment_id": f"s{index}{k}"} for k in range(size)],
    }


class TestLoopPredicateAtoms:
    def test_boolean_continuation_flag_is_ranked_first(self) -> None:
        payloads = [_page(0, 3, True, "c1"), _page(1, 2, False, None)]
        atoms = _loop_predicate_atoms(payloads, "page", "shipments", [3, 2])
        assert atoms[0] == Predicate("page.has_more", "==", True)

    def test_continuation_handle_is_offered_when_nullable(self) -> None:
        payloads = [_page(0, 3, True, "c1"), _page(1, 2, False, None)]
        atoms = _loop_predicate_atoms(payloads, "page", "shipments", [3, 2])
        assert Predicate("page.next_cursor", "present", None) in atoms

    def test_length_atom_still_offered_as_fallback(self) -> None:
        payloads = [_page(0, 3, True, "c1"), _page(1, 2, False, None)]
        atoms = _loop_predicate_atoms(payloads, "page", "shipments", [3, 2])
        assert Predicate("page.shipments", "len==", 3) in atoms

    def test_field_absent_from_some_iterations_is_not_eligible(self) -> None:
        first = _page(0, 3, True, "c1")
        last = _page(1, 2, False, None)
        last.pop("next_cursor")
        atoms = _loop_predicate_atoms([first, last], "page", "shipments", [3, 2])
        assert all("next_cursor" not in atom.path for atom in atoms)

    def test_flag_atom_separates_a_run_that_defeats_the_length_atom(self) -> None:
        """The exact shape the length-only search could not express.

        An order with exactly one full page stops after iteration 0, so
        ``len(shipments) == 3`` is true at termination and cannot be the
        continue-condition; ``has_more`` still separates the run correctly.
        """

        runs = [
            [_page(0, 3, True, "c1"), _page(1, 1, False, None)],
            [_page(0, 3, False, None)],
        ]
        payloads = [p for run in runs for p in run]
        sizes = [len(p["shipments"]) for p in payloads]  # type: ignore[arg-type]

        def separates(atom: Predicate) -> bool:
            return all(
                atom.evaluate({"page": out}) == (index < len(run) - 1)
                for run in runs
                for index, out in enumerate(run)
            )

        atoms = _loop_predicate_atoms(payloads, "page", "shipments", sizes)
        assert separates(Predicate("page.has_more", "==", True))
        assert not separates(Predicate("page.shipments", "len==", 3))
        assert next(atom for atom in atoms if separates(atom)) == Predicate(
            "page.has_more", "==", True
        )


class TestLoopStepRendering:
    def test_counter_slot_renders_as_the_iteration_index(self) -> None:
        step = LoopStep(
            "pages",
            "shipments.list_page",
            {"order_ref": Expr("get.order_ref"), "page": Const(0)},
            accumulate="shipments",
            counter="page",
            continue_when=Predicate("pages.has_more", "==", True),
        )
        text = step.pretty()
        assert "page = page" in text
        assert "Const(0)" not in text

    def test_counter_colliding_with_the_loop_variable_is_disambiguated(self) -> None:
        step = LoopStep(
            "page",
            "shipments.list_page",
            {"page": Const(0)},
            accumulate="shipments",
            counter="page",
            continue_when=Predicate("page.has_more", "==", True),
        )
        assert step.index_name() == "page_i"
        text = step.pretty()
        assert "page_i = 0" in text
        assert "page = call shipments.list_page(page = page_i)" in text


class TestUnsafeBoundDenominator:
    def _metrics(self, *, compacted: int, incidents: int, writes: int) -> object:
        from guarded_agentic_compaction.evaluation.metrics import ConditionMetrics

        return ConditionMetrics(
            condition="c",
            aggregate={
                "episodes_compacted": float(1 if compacted else 0),
                "artifact_executions_total": float(compacted + incidents),
                "incidents_total": float(incidents),
                "artifact_write_effects_total": float(writes),
            },
        )

    def test_incident_only_condition_does_not_raise(self) -> None:
        """``k > n`` used to escape into Clopper-Pearson and raise ValueError."""

        from experiments.run import _unsafe_bound

        out = _unsafe_bound(self._metrics(compacted=0, incidents=2, writes=0))
        assert out["observed_unsafe"] == 2
        assert out["upper_95"] == pytest.approx(1.0)
        assert "denominator_warning" not in out

    def test_inconsistent_telemetry_reports_the_ceiling_and_says_so(self) -> None:
        from experiments.run import _unsafe_bound

        out = _unsafe_bound(self._metrics(compacted=1, incidents=0, writes=5))
        assert out["upper_95"] == pytest.approx(1.0)
        assert "denominator_warning" in out

    def test_clean_run_reports_a_bound_not_zero(self) -> None:
        from experiments.run import _unsafe_bound

        out = _unsafe_bound(self._metrics(compacted=40, incidents=0, writes=0))
        assert out["observed_unsafe"] == 0
        assert 0.0 < out["upper_95"] < 0.10

    def test_executions_count_repeats_within_one_episode(self) -> None:
        from guarded_agentic_compaction.evaluation.metrics import ConditionMetrics

        per = [
            EpisodeMetrics(episode_id="a", group_id="g", compacted=3, incidents=1),
            EpisodeMetrics(episode_id="b", group_id="g", compacted=1),
        ]
        total = sum(m.compacted + m.incidents for m in per)
        episodes = sum(1 for m in per if m.compacted)
        assert total == 5 and episodes == 2
        cm = ConditionMetrics(
            condition="c",
            aggregate={
                "episodes_compacted": float(episodes),
                "artifact_executions_total": float(total),
                "incidents_total": 1.0,
                "artifact_write_effects_total": 0.0,
            },
        )
        from experiments.run import _unsafe_bound

        out = _unsafe_bound(cm)
        assert out["artifact_executions"] == 5
        assert out["dispatched_episodes"] == 2
