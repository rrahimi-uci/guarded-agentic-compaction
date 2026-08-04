"""Framework-neutral optimization pipeline and extension contract.

The built-in TGWS and GRC optimizers are useful passes, not the architecture. This
module gives applications and third-party packages a small, typed contract for adding
prompt, tool, memory, routing, cost, latency, or execution-plan optimizers without
coupling them to the compiler internals.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Protocol, Sequence, runtime_checkable

from .evaluation.splits import Splits
from .schema.artifacts import Artifact
from .schema.effects import EffectCatalog
from .schema.traces import Episode, ExecutionManifest

__all__ = [
    "PassStatus",
    "PassResult",
    "OptimizationContext",
    "OptimizationPass",
    "FunctionPass",
    "GrcOptimizationPass",
    "TgwsOptimizationPass",
    "OptimizationPipeline",
    "PipelineReport",
    "PipelineConfigurationError",
    "PipelineExecutionError",
]


class PassStatus(str, Enum):
    APPLIED = "applied"
    ABSTAINED = "abstained"


@dataclass(slots=True)
class PassResult:
    """Auditable output of one optimization pass."""

    name: str
    status: PassStatus = PassStatus.ABSTAINED
    artifacts: tuple[Artifact, ...] = ()
    provides: frozenset[str] = frozenset()
    metrics: dict[str, Any] = field(default_factory=dict)
    notes: tuple[str, ...] = ()
    duration_ms: float = 0.0


@dataclass(slots=True)
class OptimizationContext:
    """Shared, framework-neutral state passed between optimizers."""

    episodes: Sequence[Episode]
    catalog: EffectCatalog
    manifest: ExecutionManifest
    splits: Splits
    config: Mapping[str, Any] = field(default_factory=dict)
    artifacts: list[Artifact] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)
    capabilities: set[str] = field(
        default_factory=lambda: {"trace_ir", "effect_catalog", "grouped_splits"}
    )


@runtime_checkable
class OptimizationPass(Protocol):
    """Extension point implemented by every optimization strategy."""

    name: str
    requires: frozenset[str]

    def run(self, context: OptimizationContext) -> PassResult: ...


@dataclass(frozen=True, slots=True)
class FunctionPass:
    """Convenience adapter for a callable optimization pass."""

    name: str
    function: Callable[[OptimizationContext], PassResult]
    requires: frozenset[str] = frozenset()

    def run(self, context: OptimizationContext) -> PassResult:
        return self.function(context)


@dataclass(frozen=True, slots=True)
class GrcOptimizationPass:
    """Built-in adapter that makes guarded region compilation composable."""

    config: Any
    sandbox: Callable[[], Any] | None = None
    perturbations: Sequence[Any] | None = None
    name: str = "grc"
    requires: frozenset[str] = frozenset(
        {"trace_ir", "effect_catalog", "grouped_splits"}
    )

    def run(self, context: OptimizationContext) -> PassResult:
        from .evaluation.perturb import DEFAULT_PERTURBATIONS
        from .grc.compile import compile_grc

        result = compile_grc(
            context.episodes,
            context.catalog,
            context.splits,
            context.manifest,
            self.config,
            sandbox=self.sandbox,
            perturbations=(
                DEFAULT_PERTURBATIONS
                if self.perturbations is None
                else self.perturbations
            ),
        )
        context.state["grc_result"] = result
        artifacts = tuple(result.artifacts)
        return PassResult(
            self.name,
            PassStatus.APPLIED if artifacts else PassStatus.ABSTAINED,
            artifacts=artifacts,
            provides=frozenset({"workflow_compaction"}) if artifacts else frozenset(),
            metrics={
                "candidates": len(result.candidates),
                "artifacts": len(artifacts),
                "rejections": dict(result.rejection_by_stage),
            },
            notes=(() if artifacts else ("no candidate passed every safety gate",)),
        )


@dataclass(frozen=True, slots=True)
class TgwsOptimizationPass:
    """Built-in adapter for trace-guided prompt, tool, and route specialization."""

    config: Any
    baseline: Any
    evaluate: Callable[..., Any]
    label_fn: Callable[[Episode], str] | None = None
    name: str = "tgws"
    requires: frozenset[str] = frozenset(
        {"trace_ir", "effect_catalog", "grouped_splits"}
    )

    def run(self, context: OptimizationContext) -> PassResult:
        from .tgws.package import compile_tgws

        kwargs = {"label_fn": self.label_fn} if self.label_fn is not None else {}
        result = compile_tgws(
            context.episodes,
            context.catalog,
            context.splits,
            context.manifest,
            self.config,
            baseline=self.baseline,
            evaluate=self.evaluate,
            **kwargs,
        )
        context.state["tgws_result"] = result
        artifacts = tuple(result.artifacts)
        return PassResult(
            self.name,
            PassStatus.APPLIED if artifacts else PassStatus.ABSTAINED,
            artifacts=artifacts,
            provides=frozenset({"workflow_specialization"}) if artifacts else frozenset(),
            metrics={
                "leaves": len(result.leaves),
                "artifacts": len(artifacts),
                "rejections": dict(result.rejection_by_stage),
            },
            notes=(() if artifacts else ("no route leaf passed every safety gate",)),
        )


@dataclass(slots=True)
class PipelineReport:
    results: list[PassResult] = field(default_factory=list)
    capabilities: frozenset[str] = frozenset()
    duration_ms: float = 0.0

    @property
    def artifacts(self) -> list[Artifact]:
        return [artifact for result in self.results for artifact in result.artifacts]

    def as_dict(self) -> dict[str, Any]:
        return {
            "duration_ms": round(self.duration_ms, 3),
            "capabilities": sorted(self.capabilities),
            "passes": [
                {
                    "name": result.name,
                    "status": result.status.value,
                    "artifacts": [a.artifact_id for a in result.artifacts],
                    "provides": sorted(result.provides),
                    "metrics": result.metrics,
                    "notes": list(result.notes),
                    "duration_ms": round(result.duration_ms, 3),
                }
                for result in self.results
            ],
        }


class PipelineConfigurationError(ValueError):
    pass


class PipelineExecutionError(RuntimeError):
    pass


class OptimizationPipeline:
    """Run ordered, dependency-checked optimization passes deterministically."""

    def __init__(self, passes: Sequence[OptimizationPass]) -> None:
        self.passes = tuple(passes)
        names = [item.name for item in self.passes]
        if len(names) != len(set(names)):
            raise PipelineConfigurationError("optimization pass names must be unique")

    def run(self, context: OptimizationContext) -> PipelineReport:
        started = time.perf_counter()
        results: list[PassResult] = []
        available = set(context.capabilities)
        for optimizer in self.passes:
            missing = set(optimizer.requires) - available
            if missing:
                raise PipelineConfigurationError(
                    f"pass {optimizer.name!r} is missing capabilities: {sorted(missing)}"
                )
            pass_started = time.perf_counter()
            try:
                result = optimizer.run(context)
            except Exception as exc:
                raise PipelineExecutionError(f"optimization pass {optimizer.name!r} failed") from exc
            if result.name != optimizer.name:
                raise PipelineConfigurationError(
                    f"pass {optimizer.name!r} returned result for {result.name!r}"
                )
            result.duration_ms = (time.perf_counter() - pass_started) * 1000.0
            if result.status is PassStatus.APPLIED:
                available.update(result.provides)
                context.capabilities.update(result.provides)
                context.artifacts.extend(result.artifacts)
            results.append(result)
        return PipelineReport(
            results=results,
            capabilities=frozenset(available),
            duration_ms=(time.perf_counter() - started) * 1000.0,
        )
