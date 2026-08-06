"""Artifact registry and lifecycle controls.

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
    "LifecycleError": "lifecycle",
    "audit_log": "lifecycle",
    "expire_due": "lifecycle",
    "invalidated_by_drift": "lifecycle",
    "promote": "lifecycle",
    "retire": "lifecycle",
    "rollback": "lifecycle",
    "Registry": "store",
    "RegistryError": "store",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    module = _EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(f".{module}", __name__), name)


def __dir__() -> list[str]:
    return __all__
