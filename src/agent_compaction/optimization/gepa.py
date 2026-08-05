"""Budgeted adapter for the official GEPA textual optimizer.

The adapter intentionally accepts a framework-neutral synchronous evaluator.
An OpenAI Agents SDK application can therefore evaluate each candidate through
its normal runner and traces without coupling the library to one provider loop.
The official package is imported lazily and is an optional dependency.

GEPA's optional ``full`` extra includes experiment trackers.  This adapter uses
the dependency-free core wheel and explicitly disables MLflow and Weights &
Biases, preserving agent-compaction's tracker-free runtime.
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence, runtime_checkable

__all__ = [
    "GepaBackend",
    "GepaEvaluation",
    "GepaOptimizationError",
    "GepaPromptConfig",
    "GepaPromptOptimizer",
    "GepaPromptResult",
    "GepaUnavailableError",
    "OfficialGepaBackend",
]


class GepaUnavailableError(RuntimeError):
    """The pinned optional GEPA implementation is unavailable or incompatible."""


class GepaOptimizationError(RuntimeError):
    """GEPA or the supplied candidate evaluator failed."""


@dataclass(frozen=True, slots=True)
class GepaEvaluation:
    """One scalar score plus actionable, non-secret reflection feedback."""

    score: float
    feedback: str
    metrics: Mapping[str, Any] = field(default_factory=dict)


PromptEvaluator = Callable[[str, Any], GepaEvaluation]
ReflectionLM = Callable[[str], str]


@dataclass(frozen=True, slots=True)
class GepaPromptConfig:
    """Hard bounds and reproducibility controls for one GEPA run."""

    max_metric_calls: int = 20
    max_candidate_proposals: int = 4
    reflection_minibatch_size: int = 2
    seed: int = 0
    min_candidate_chars: int = 1
    max_candidate_chars: int = 8_000
    run_dir: str | Path | None = None
    expected_gepa_version: str = "0.1.4"
    require_disjoint_splits: bool = True
    record_feedback: bool = False

    def __post_init__(self) -> None:
        if self.max_metric_calls <= 0:
            raise ValueError("max_metric_calls must be positive")
        if self.max_candidate_proposals <= 0:
            raise ValueError("max_candidate_proposals must be positive")
        if self.reflection_minibatch_size <= 0:
            raise ValueError("reflection_minibatch_size must be positive")
        if self.min_candidate_chars <= 0:
            raise ValueError("min_candidate_chars must be positive")
        if self.max_candidate_chars < self.min_candidate_chars:
            raise ValueError("max_candidate_chars must be >= min_candidate_chars")


@dataclass(frozen=True, slots=True)
class GepaPromptResult:
    """Serializable evidence returned from a completed official GEPA run."""

    seed_prompt: str
    best_prompt: str
    seed_score: float
    best_score: float
    candidates: tuple[str, ...]
    candidate_scores: tuple[float, ...]
    parents: tuple[tuple[int | None, ...], ...]
    metric_calls: int
    full_validation_evaluations: int
    evaluation_log: tuple[dict[str, Any], ...]
    rejected_candidates: int
    gepa_version: str
    seed: int

    @property
    def improved(self) -> bool:
        return self.best_score > self.seed_score

    @property
    def result_digest(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed_prompt": self.seed_prompt,
            "best_prompt": self.best_prompt,
            "seed_score": self.seed_score,
            "best_score": self.best_score,
            "improved": self.improved,
            "candidates": list(self.candidates),
            "candidate_scores": list(self.candidate_scores),
            "parents": [list(row) for row in self.parents],
            "metric_calls": self.metric_calls,
            "full_validation_evaluations": self.full_validation_evaluations,
            "evaluation_log": list(self.evaluation_log),
            "rejected_candidates": self.rejected_candidates,
            "gepa_version": self.gepa_version,
            "seed": self.seed,
        }


@runtime_checkable
class GepaBackend(Protocol):
    """Narrow backend seam used for optional loading and provider-free tests."""

    version: str

    def optimize(
        self,
        *,
        seed_prompt: str,
        evaluator: Callable[[str, Any], tuple[float, dict[str, Any]]],
        trainset: Sequence[Any],
        valset: Sequence[Any],
        reflection_lm: ReflectionLM,
        config: GepaPromptConfig,
    ) -> Any: ...


@dataclass(frozen=True, slots=True)
class OfficialGepaBackend:
    """Lazy bridge to ``gepa.optimize_anything`` from the official package."""

    expected_version: str = "0.1.4"

    @property
    def version(self) -> str:
        try:
            installed = version("gepa")
        except PackageNotFoundError as exc:  # pragma: no cover - environment dependent
            raise GepaUnavailableError(
                "install agent-compaction[gepa] to use the GEPA optimizer"
            ) from exc
        if installed != self.expected_version:
            raise GepaUnavailableError(
                f"GEPA version {installed} is installed; expected {self.expected_version}"
            )
        return installed

    def optimize(
        self,
        *,
        seed_prompt: str,
        evaluator: Callable[[str, Any], tuple[float, dict[str, Any]]],
        trainset: Sequence[Any],
        valset: Sequence[Any],
        reflection_lm: ReflectionLM,
        config: GepaPromptConfig,
    ) -> Any:
        _ = self.version
        try:
            from gepa.optimize_anything import (
                EngineConfig,
                GEPAConfig,
                ReflectionConfig,
                TrackingConfig,
                optimize_anything,
            )
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise GepaUnavailableError(
                "the installed GEPA core cannot expose optimize_anything"
            ) from exc

        return optimize_anything(
            seed_candidate=seed_prompt,
            evaluator=evaluator,
            dataset=list(trainset),
            valset=list(valset),
            objective=(
                "Improve the deployment instruction while preserving all fixed task and "
                "safety contracts. Higher evaluator score is better."
            ),
            background=(
                "The candidate is an additional instruction block for a real agent "
                "workflow. Use evaluator feedback; do not assume access to hidden data."
            ),
            config=GEPAConfig(
                engine=EngineConfig(
                    run_dir=str(config.run_dir) if config.run_dir is not None else None,
                    seed=config.seed,
                    display_progress_bar=False,
                    raise_on_exception=True,
                    use_cloudpickle=False,
                    track_best_outputs=True,
                    max_metric_calls=config.max_metric_calls,
                    max_candidate_proposals=config.max_candidate_proposals,
                    parallel=False,
                    max_workers=1,
                    cache_evaluation=False,
                    capture_stdio=False,
                ),
                reflection=ReflectionConfig(
                    reflection_lm=reflection_lm,
                    reflection_minibatch_size=config.reflection_minibatch_size,
                ),
                tracking=TrackingConfig(use_wandb=False, use_mlflow=False),
            ),
        )


@dataclass(slots=True)
class GepaPromptOptimizer:
    """Run GEPA with exact split isolation, budgets, and auditable evaluations."""

    config: GepaPromptConfig = field(default_factory=GepaPromptConfig)
    backend: GepaBackend | None = None

    def optimize(
        self,
        *,
        seed_prompt: str,
        evaluator: PromptEvaluator,
        trainset: Sequence[Any],
        valset: Sequence[Any],
        reflection_lm: ReflectionLM,
        example_id: Callable[[Any], str] | None = None,
    ) -> GepaPromptResult:
        if not seed_prompt.strip():
            raise ValueError("seed_prompt must not be empty")
        if not trainset or not valset:
            raise ValueError("trainset and valset must both be non-empty")
        key_fn = example_id or _example_key
        train_ids = [str(key_fn(value)) for value in trainset]
        val_ids = [str(key_fn(value)) for value in valset]
        if len(train_ids) != len(set(train_ids)) or len(val_ids) != len(set(val_ids)):
            raise ValueError("each GEPA split must contain unique example identities")
        overlap = sorted(set(train_ids) & set(val_ids))
        if self.config.require_disjoint_splits and overlap:
            raise ValueError(f"GEPA train/validation overlap: {overlap[:4]}")

        backend = self.backend or OfficialGepaBackend(self.config.expected_gepa_version)
        backend_version = backend.version
        evaluation_log: list[dict[str, Any]] = []
        rejected_candidates = 0
        lock = threading.Lock()

        def evaluate(candidate: str, example: Any) -> tuple[float, dict[str, Any]]:
            nonlocal rejected_candidates
            candidate = str(candidate)
            candidate_digest = hashlib.sha256(candidate.encode()).hexdigest()[:16]
            identifier = str(key_fn(example))
            if not (self.config.min_candidate_chars <= len(candidate) <= self.config.max_candidate_chars):
                with lock:
                    rejected_candidates += 1
                    evaluation_log.append(
                        {
                            "candidate_digest": candidate_digest,
                            "example_id": identifier,
                            "score": -1_000_000.0,
                            "rejected": "candidate_length",
                        }
                    )
                return -1_000_000.0, {
                    "Feedback": (
                        "Candidate rejected before execution: instruction length must be "
                        f"{self.config.min_candidate_chars}..{self.config.max_candidate_chars} characters."
                    ),
                    "scores": {"deployment_objective": -1_000_000.0},
                }
            try:
                result = evaluator(candidate, example)
            except Exception as exc:
                raise GepaOptimizationError(
                    f"candidate evaluator failed with {type(exc).__name__}"
                ) from exc
            if not isinstance(result, GepaEvaluation):
                raise GepaOptimizationError("candidate evaluator must return GepaEvaluation")
            score = float(result.score)
            if not math.isfinite(score):
                raise GepaOptimizationError("candidate evaluator returned a non-finite score")
            metrics = _json_safe_mapping(result.metrics)
            log_row: dict[str, Any] = {
                "candidate_digest": candidate_digest,
                "example_id": identifier,
                "score": score,
                "metrics": metrics,
            }
            if self.config.record_feedback:
                log_row["feedback"] = result.feedback
            else:
                log_row["feedback_digest"] = hashlib.sha256(result.feedback.encode()).hexdigest()
            with lock:
                evaluation_log.append(log_row)
            return score, {
                "Feedback": result.feedback,
                "Metrics": metrics,
                "scores": {"deployment_objective": score},
            }

        try:
            raw = backend.optimize(
                seed_prompt=seed_prompt,
                evaluator=evaluate,
                trainset=trainset,
                valset=valset,
                reflection_lm=reflection_lm,
                config=self.config,
            )
        except (GepaUnavailableError, GepaOptimizationError):
            raise
        except Exception as exc:
            raise GepaOptimizationError(
                f"official GEPA optimization failed with {type(exc).__name__}"
            ) from exc

        candidates = tuple(_candidate_text(value) for value in raw.candidates)
        scores = tuple(float(value) for value in raw.val_aggregate_scores)
        if not candidates or len(candidates) != len(scores):
            raise GepaOptimizationError("GEPA returned an invalid candidate/score frontier")
        best_prompt = _candidate_text(raw.best_candidate)
        if best_prompt not in candidates:
            raise GepaOptimizationError("GEPA best candidate is absent from its frontier")
        parents = tuple(
            tuple(None if value is None else int(value) for value in row)
            for row in raw.parents
        )
        metric_calls = int(raw.total_metric_calls or len(evaluation_log))
        if metric_calls > self.config.max_metric_calls:
            raise GepaOptimizationError("GEPA exceeded the configured metric-call budget")
        return GepaPromptResult(
            seed_prompt=seed_prompt,
            best_prompt=best_prompt,
            seed_score=scores[0],
            best_score=max(scores),
            candidates=candidates,
            candidate_scores=scores,
            parents=parents,
            metric_calls=metric_calls,
            full_validation_evaluations=int(raw.num_full_val_evals or 0),
            evaluation_log=tuple(evaluation_log),
            rejected_candidates=rejected_candidates,
            gepa_version=backend_version,
            seed=int(raw.seed if raw.seed is not None else self.config.seed),
        )


def _candidate_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        if "current_candidate" in value:
            return str(value["current_candidate"])
        if len(value) == 1:
            return str(next(iter(value.values())))
    raise GepaOptimizationError("GEPA returned a non-text candidate")


def _example_key(value: Any) -> str:
    try:
        payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    except (TypeError, ValueError):
        payload = repr(value)
    return hashlib.sha256(payload.encode()).hexdigest()


def _json_safe_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(json.dumps(dict(value), sort_keys=True, default=str))
    except (TypeError, ValueError) as exc:
        raise GepaOptimizationError("evaluation metrics are not serializable") from exc
