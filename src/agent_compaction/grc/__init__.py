"""GRC: guarded region compilation (proposal §4, algorithms 1-7).

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
    "CalibrationSample": "calibrate",
    "GRID": "calibrate",
    "GateFeatures": "calibrate",
    "calibrate_gate": "calibrate",
    "clopper_pearson_upper": "calibrate",
    "CandidateRecord": "compile",
    "CompileResult": "compile",
    "GrcConfig": "compile",
    "compile_grc": "compile",
    "compile_grc_batch": "compile",
    "CompositeProjectionError": "composite",
    "CompositeSpec": "composite",
    "CompositeSynthesisError": "composite",
    "synthesize_composite": "composite",
    "ChallengeReport": "contracts",
    "challenge": "contracts",
    "fit_hull": "contracts",
    "induce_guard": "contracts",
    "induce_verifier": "contracts",
    "Const": "dsl",
    "Expr": "dsl",
    "LIBRARY_VERSION": "dsl",
    "OPERATOR_CLASSES": "dsl",
    "Op": "dsl",
    "SynthContext": "dsl",
    "search_chains": "dsl",
    "AssertStep": "program",
    "CallStep": "program",
    "LoopStep": "program",
    "Predicate": "program",
    "Program": "program",
    "synthesize_binding": "synthesize",
    "synthesize_branch": "synthesize",
    "synthesize_program": "synthesize",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    module = _EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(f".{module}", __name__), name)


def __dir__() -> list[str]:
    return __all__
