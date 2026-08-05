from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent_compaction.optimization.gepa import (
    GepaEvaluation,
    GepaOptimizationError,
    GepaPromptConfig,
    GepaPromptOptimizer,
)


class FakeBackend:
    version = "fake-gepa"

    def __init__(self, proposal: str = "improved") -> None:
        self.proposal = proposal
        self.calls = 0

    def optimize(self, *, seed_prompt, evaluator, trainset, valset, reflection_lm, config):
        _ = reflection_lm("feedback")
        seed_scores = []
        proposal_scores = []
        for example in valset:
            seed_scores.append(evaluator(seed_prompt, example)[0])
            self.calls += 1
            proposal_scores.append(evaluator(self.proposal, example)[0])
            self.calls += 1
        aggregate = [
            sum(seed_scores) / len(seed_scores),
            sum(proposal_scores) / len(proposal_scores),
        ]
        best = seed_prompt if aggregate[0] >= aggregate[1] else self.proposal
        return SimpleNamespace(
            candidates=[{"current_candidate": seed_prompt}, {"current_candidate": self.proposal}],
            best_candidate=best,
            val_aggregate_scores=aggregate,
            parents=[[None], [0]],
            total_metric_calls=self.calls,
            num_full_val_evals=2,
            seed=config.seed,
        )


def test_gepa_adapter_selects_best_prompt_and_records_bounded_audit_log() -> None:
    backend = FakeBackend("carefully improved")
    optimizer = GepaPromptOptimizer(
        GepaPromptConfig(max_metric_calls=8, seed=17),
        backend=backend,
    )

    def evaluate(candidate: str, example: dict) -> GepaEvaluation:
        score = float(len(candidate) + example["bonus"])
        return GepaEvaluation(
            score,
            feedback=f"candidate={candidate}; improve precision",
            metrics={"length": len(candidate), "example": example["id"]},
        )

    result = optimizer.optimize(
        seed_prompt="seed",
        evaluator=evaluate,
        trainset=[{"id": "train", "bonus": 0}],
        valset=[{"id": "val-a", "bonus": 1}, {"id": "val-b", "bonus": 2}],
        reflection_lm=lambda _prompt: "```carefully improved```",
        example_id=lambda item: item["id"],
    )

    assert result.best_prompt == "carefully improved"
    assert result.improved
    assert result.metric_calls == 4
    assert result.gepa_version == "fake-gepa"
    assert len(result.evaluation_log) == 4
    assert all("feedback" not in row and "feedback_digest" in row for row in result.evaluation_log)
    assert result.result_digest == result.result_digest


def test_gepa_adapter_enforces_split_isolation_before_backend_execution() -> None:
    backend = FakeBackend()
    optimizer = GepaPromptOptimizer(backend=backend)

    with pytest.raises(ValueError, match="overlap"):
        optimizer.optimize(
            seed_prompt="seed",
            evaluator=lambda _candidate, _example: GepaEvaluation(1.0, "ok"),
            trainset=[{"id": "same"}],
            valset=[{"id": "same"}],
            reflection_lm=lambda _prompt: "proposal",
            example_id=lambda item: item["id"],
        )

    assert backend.calls == 0


def test_gepa_adapter_rejects_oversized_candidates_without_calling_evaluator() -> None:
    backend = FakeBackend("x" * 20)
    optimizer = GepaPromptOptimizer(
        GepaPromptConfig(max_metric_calls=4, max_candidate_chars=10),
        backend=backend,
    )
    evaluated: list[str] = []

    result = optimizer.optimize(
        seed_prompt="seed",
        evaluator=lambda candidate, _example: (
            evaluated.append(candidate) or GepaEvaluation(1.0, "ok")
        ),
        trainset=["train"],
        valset=["val"],
        reflection_lm=lambda _prompt: "proposal",
    )

    assert evaluated == ["seed"]
    assert result.best_prompt == "seed"
    assert result.rejected_candidates == 1
    assert result.evaluation_log[-1]["rejected"] == "candidate_length"


def test_gepa_adapter_fails_on_non_finite_scores_and_budget_overrun() -> None:
    optimizer = GepaPromptOptimizer(
        GepaPromptConfig(max_metric_calls=4),
        backend=FakeBackend(),
    )
    with pytest.raises(GepaOptimizationError, match="non-finite"):
        optimizer.optimize(
            seed_prompt="seed",
            evaluator=lambda _candidate, _example: GepaEvaluation(float("nan"), "bad"),
            trainset=["train"],
            valset=["val"],
            reflection_lm=lambda _prompt: "proposal",
        )

    class OverBudget(FakeBackend):
        def optimize(self, **kwargs):
            raw = super().optimize(**kwargs)
            raw.total_metric_calls = 999
            return raw

    optimizer = GepaPromptOptimizer(
        GepaPromptConfig(max_metric_calls=4),
        backend=OverBudget(),
    )
    with pytest.raises(GepaOptimizationError, match="budget"):
        optimizer.optimize(
            seed_prompt="seed",
            evaluator=lambda candidate, _example: GepaEvaluation(float(len(candidate)), "ok"),
            trainset=["train"],
            valset=["val"],
            reflection_lm=lambda _prompt: "proposal",
        )


def test_gepa_adapter_sanitizes_evaluator_exception_text() -> None:
    optimizer = GepaPromptOptimizer(backend=FakeBackend())

    def fail(_candidate: str, _example: str) -> GepaEvaluation:
        raise RuntimeError("credential=must-not-escape")

    with pytest.raises(GepaOptimizationError) as error:
        optimizer.optimize(
            seed_prompt="seed",
            evaluator=fail,
            trainset=["train"],
            valset=["val"],
            reflection_lm=lambda _prompt: "proposal",
        )
    assert "must-not-escape" not in str(error.value)
