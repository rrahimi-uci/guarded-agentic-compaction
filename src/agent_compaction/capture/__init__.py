"""Capture backends. Nothing above this package imports MLflow or the Agents SDK.

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
    "AgentsTraceProcessor": "agents_sdk",
    "SdkSpanRecord": "agents_sdk",
    "SdkTraceRecord": "agents_sdk",
    "episode_from_agents_trace": "agents_sdk",
    "install_agents_trace_processor": "agents_sdk",
    "EntryStateContract": "attributes",
    "pseudonymize": "attributes",
    "redact": "attributes",
    "build_manifest": "manifests",
    "hash_text": "manifests",
    "hash_tools": "manifests",
    "manifest_diff": "manifests",
    "available": "mlflow_adapter",
    "configure": "mlflow_adapter",
    "export_episodes": "mlflow_adapter",
    "load_episodes": "mlflow_adapter",
    "read_jsonl": "mlflow_adapter",
    "write_jsonl": "mlflow_adapter",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    module = _EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(f".{module}", __name__), name)


def __dir__() -> list[str]:
    return __all__
