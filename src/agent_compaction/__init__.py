"""agent-compaction: guarded, evidence-gated workflow optimization for LLM agents.

Two optimizers over one typed trace contract:

* **TGWS** (:mod:`agent_compaction.tgws`) — learn a shallow route from entry-state
  facts to a specialist prompt and a minimal tool surface, and abstain when the route
  or the input is uncertain.
* **GRC** (:mod:`agent_compaction.grc`) — find repeated read-only regions, prove every
  tool argument derives from entry state or earlier observations, synthesize a bounded
  deterministic program, and dispatch only under a calibrated contract gate.

Neither invents business logic, changes model weights, or removes an external effect.
Abstention is the default output, and "do not compact" is the common and correct one.
"""

from __future__ import annotations

from . import capture, evaluation, graph, grc, registry, runtime, schema, tgws
from .api import MODES, OptimizeJob, estimate, load_catalog, optimize, promote, retire, validate
from .capture.mlflow_adapter import read_jsonl, write_jsonl
from .estimate.headroom import EstimateReport, break_even, required_calibration_groups
from .evaluation.splits import Splits, make_splits
from .registry.store import Registry
from .runtime.dispatch import DispatchMode, Dispatcher
from .runtime.continuation import (
    ContinuationDecision,
    ContinuationEvidence,
    ContinuationGuard,
    ContinuationOutcome,
    ContinuationTelemetry,
)
from .runtime.runner import CompactingRunner, Decision, RouteResolver, compact
from .pipeline import (
    FunctionPass,
    GrcOptimizationPass,
    OptimizationContext,
    OptimizationPass,
    OptimizationPipeline,
    PassResult,
    PassStatus,
    PipelineReport,
    PipelineConfigurationError,
    PipelineExecutionError,
    TgwsOptimizationPass,
)
from .schema.artifacts import Artifact, Lifecycle
from .schema.effects import Capability, EffectCatalog, EffectClass
from .schema.traces import (
    Episode,
    EventKind,
    EventNode,
    ExecutionManifest,
    TraceEnvelope,
    manifest_partitions,
    require_compatible_manifest,
)

__version__ = "0.5.0"

__all__ = [
    "__version__",
    "MODES",
    "OptimizeJob",
    "estimate",
    "optimize",
    "validate",
    "promote",
    "retire",
    "load_catalog",
    "read_jsonl",
    "write_jsonl",
    "EstimateReport",
    "break_even",
    "required_calibration_groups",
    "Splits",
    "make_splits",
    "Registry",
    "Dispatcher",
    "DispatchMode",
    "ContinuationDecision",
    "ContinuationEvidence",
    "ContinuationGuard",
    "ContinuationOutcome",
    "ContinuationTelemetry",
    "CompactingRunner",
    "RouteResolver",
    "Decision",
    "compact",
    "FunctionPass",
    "GrcOptimizationPass",
    "OptimizationContext",
    "OptimizationPass",
    "OptimizationPipeline",
    "PassResult",
    "PassStatus",
    "PipelineReport",
    "PipelineConfigurationError",
    "PipelineExecutionError",
    "TgwsOptimizationPass",
    "Artifact",
    "Lifecycle",
    "EffectCatalog",
    "EffectClass",
    "Capability",
    "Episode",
    "EventKind",
    "EventNode",
    "ExecutionManifest",
    "TraceEnvelope",
    "manifest_partitions",
    "require_compatible_manifest",
    "capture",
    "evaluation",
    "graph",
    "grc",
    "registry",
    "runtime",
    "schema",
    "tgws",
]
