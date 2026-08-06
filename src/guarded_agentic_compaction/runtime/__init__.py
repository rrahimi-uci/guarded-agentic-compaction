"""Runtime: dispatch (Alg. 7), staging, the permission facade, integration paths.

Exports are resolved lazily (PEP 562). The sibling packages depend on each other in
both directions at *type* level — the graph builder uses the DSL, the compiler uses the
graph, evaluation uses both — and eager re-exports in these ``__init__`` files would
turn that into an import cycle. Lazy attribute access keeps the public surface flat
without ordering constraints.
"""

from __future__ import annotations

import importlib
from typing import Any

_EXPORTS: dict[str, str] = {
    "BaselineContinuation": "continuation",
    "ContinuationContract": "continuation",
    "ContinuationDecision": "continuation",
    "ContinuationEvidence": "continuation",
    "ContinuationGuard": "continuation",
    "ContinuationOutcome": "continuation",
    "ContinuationRenderer": "continuation",
    "ContinuationTelemetry": "continuation",
    "DispatchDecision": "dispatch",
    "DispatchMode": "dispatch",
    "DispatchTelemetry": "dispatch",
    "Dispatcher": "dispatch",
    "FacadeMode": "facade",
    "ForbiddenTool": "facade",
    "Recording": "facade",
    "ToolFacade": "facade",
    "InterpResult": "interp",
    "PostCommitError": "interp",
    "PreCommitError": "interp",
    "run_program": "interp",
    "ManualPreModelDecision": "manual",
    "ManualPreModelPlan": "manual",
    "ManualPreModelRunner": "manual",
    "ArtifactPlan": "model_provider",
    "CompactingModel": "model_provider",
    "UnsupportedFeature": "model_provider",
    "CompactingRunner": "runner",
    "Decision": "runner",
    "RouteResolver": "runner",
    "compact": "runner",
    "Snapshot": "staging",
    "Staging": "staging",
    "StagingViolation": "staging",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    module = _EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(f".{module}", __name__), name)


def __dir__() -> list[str]:
    return __all__
