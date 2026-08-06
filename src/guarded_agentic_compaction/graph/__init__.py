"""Typed trace graph: qualification, provenance (Alg. 1), window mining (Alg. 2).

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
    "DataQualityReport": "normalize",
    "FieldStats": "normalize",
    "canonical_order": "normalize",
    "data_quality": "normalize",
    "field_statistics": "normalize",
    "qualify": "normalize",
    "qualify_all": "normalize",
    "signature": "normalize",
    "DataEdge": "provenance",
    "GroundabilityPolicy": "provenance",
    "PATG": "provenance",
    "Producer": "provenance",
    "Slot": "provenance",
    "SlotMark": "provenance",
    "build_all": "provenance",
    "build_patg": "provenance",
    "BlockReason": "windows",
    "Family": "windows",
    "MiningResult": "windows",
    "Window": "windows",
    "WindowStep": "windows",
    "enumerate_windows": "windows",
    "mine": "windows",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    module = _EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(f".{module}", __name__), name)


def __dir__() -> list[str]:
    return __all__
