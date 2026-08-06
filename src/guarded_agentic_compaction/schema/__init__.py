"""Frozen schemas: traces, effects, artifacts (execution-plan §6).

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
    "Artifact": "artifacts",
    "DispatchOutcome": "artifacts",
    "Evidence": "artifacts",
    "Gate": "artifacts",
    "GateModel": "artifacts",
    "GuardClause": "artifacts",
    "HardGuard": "artifacts",
    "Hull": "artifacts",
    "Lifecycle": "artifacts",
    "OutputClause": "artifacts",
    "RouteConfig": "artifacts",
    "Verifier": "artifacts",
    "Capability": "effects",
    "ArgumentSemantics": "effects",
    "CanonicalizationKind": "effects",
    "CanonicalizationOp": "effects",
    "SemanticRelation": "effects",
    "EffectCatalog": "effects",
    "EffectClass": "effects",
    "EffectSpec": "effects",
    "Episode": "traces",
    "EventKind": "traces",
    "EventNode": "traces",
    "ExecutionManifest": "traces",
    "OutcomeLabels": "traces",
    "TraceEnvelope": "traces",
    "Usage": "traces",
    "content_digest": "traces",
    "flatten": "traces",
    "resolve_path": "traces",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    module = _EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(f".{module}", __name__), name)


def __dir__() -> list[str]:
    return __all__
