from __future__ import annotations

import agent_compaction as ac
from agent_compaction.runtime import (
    ContinuationEvidence,
    ContinuationGuard,
    ContinuationOutcome,
)
from agent_compaction.runtime.runner import CompactingRunner


def evidence(expected: str = "grounded") -> ContinuationEvidence:
    return ContinuationEvidence(
        entry_state={"issue_number": 7},
        observations=({"text": expected},),
        artifact_id="grc-7",
        metadata={"expected": expected},
    )


def exact_contract(output: object, context: ContinuationEvidence) -> list[str]:
    if not isinstance(output, dict):
        return ["schema:not_mapping"]
    return [] if output.get("text") == context.metadata["expected"] else ["text:not_grounded"]


def test_accepts_a_candidate_that_satisfies_the_continuation_contract() -> None:
    guard = ContinuationGuard(exact_contract)
    candidate = {"text": "grounded"}

    decision = guard.decide(candidate, evidence())

    assert decision.outcome is ContinuationOutcome.ACCEPTED
    assert decision.output is candidate
    assert guard.telemetry.as_dict()["accepted"] == 1


def test_checked_renderer_repairs_and_revalidates_a_bad_candidate() -> None:
    guard = ContinuationGuard(
        exact_contract,
        renderer=lambda context: {"text": context.observations[0]["text"]},
    )

    decision = guard.decide({"text": "altered"}, evidence())

    assert decision.outcome is ContinuationOutcome.RENDERED
    assert decision.output == {"text": "grounded"}
    assert decision.candidate_violations == ("text:not_grounded",)
    assert decision.record["recovered"] is True


def test_invalid_renderer_falls_through_to_a_revalidated_baseline() -> None:
    guard = ContinuationGuard(exact_contract, renderer=lambda _context: {"text": "still wrong"})

    decision = guard.decide(
        {"text": "altered"},
        evidence(),
        baseline=lambda context: {"text": context.metadata["expected"]},
    )

    assert decision.outcome is ContinuationOutcome.BASELINE
    assert decision.output == {"text": "grounded"}
    assert decision.recovery_violations == ("text:not_grounded",)


def test_no_unvalidated_recovery_is_ever_emitted() -> None:
    guard = ContinuationGuard(exact_contract, renderer=lambda _context: {"text": "wrong"})

    decision = guard.decide(
        {"text": "altered"},
        evidence(),
        baseline=lambda _context: {"text": "also wrong"},
    )

    assert decision.outcome is ContinuationOutcome.REJECTED
    assert decision.output is None
    assert decision.accepted is False
    assert guard.telemetry.as_dict()["rejected"] == 1


def test_callback_exceptions_fail_closed_without_serializing_exception_text() -> None:
    def broken_contract(_output: object, _context: ContinuationEvidence) -> list[str]:
        raise RuntimeError("secret-bearing diagnostic")

    guard = ContinuationGuard(broken_contract, renderer=lambda _context: 1 / 0)
    decision = guard.decide("candidate", evidence(), baseline=lambda _context: 1 / 0)

    assert decision.outcome is ContinuationOutcome.REJECTED
    serialized = str(decision.record)
    assert "secret-bearing" not in serialized
    assert "validator_error:RuntimeError" in serialized
    assert guard.telemetry.validator_errors >= 1


def test_continuation_api_is_available_from_the_top_level_package() -> None:
    assert ac.ContinuationGuard is ContinuationGuard
    assert ac.ContinuationEvidence is ContinuationEvidence


def test_runner_continuation_hook_fails_closed_when_not_configured() -> None:
    # The method does not touch dispatcher/catalog/manifest, so minimal sentinels keep
    # this test focused on the post-model boundary rather than region dispatch.
    runner = CompactingRunner(dispatcher=None, catalog=None, manifest=None)  # type: ignore[arg-type]

    decision = runner.on_continuation(
        {"text": "grounded"}, entry_state={}, observations=()
    )

    assert decision.outcome is ContinuationOutcome.REJECTED
    assert decision.output is None
    assert runner.records[-1]["continuation"]["candidate_violations"] == [
        "continuation_guard_not_configured"
    ]


def test_runner_continuation_hook_uses_the_configured_guard() -> None:
    guard = ContinuationGuard(exact_contract)
    runner = CompactingRunner(  # type: ignore[arg-type]
        dispatcher=None, catalog=None, manifest=None, continuation_guard=guard
    )

    decision = runner.on_continuation(
        {"text": "grounded"},
        entry_state={"issue_number": 7},
        observations=({"text": "grounded"},),
        metadata={"expected": "grounded"},
    )

    assert decision.outcome is ContinuationOutcome.ACCEPTED
