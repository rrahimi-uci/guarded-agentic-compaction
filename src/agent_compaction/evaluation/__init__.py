"""Evaluation: grouped splits, replay modes, perturbations, metrics, statistics.

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
    "BenchmarkComparison": "benchmark",
    "compare_episodes": "benchmark",
    "repeat_agreement": "benchmark",
    "ConditionMetrics": "metrics",
    "EpisodeMetrics": "metrics",
    "condition_metrics": "metrics",
    "episode_metrics": "metrics",
    "maintenance_metrics": "metrics",
    "BenchmarkCase": "domains",
    "BenchmarkRole": "domains",
    "DomainAdapter": "domains",
    "FrozenStudy": "domains",
    "OracleResult": "domains",
    "CanonicalMetrics": "evidence",
    "paired_portfolio_observation": "evidence",
    "BinaryPair": "paired_exact",
    "ExactPairedNonInferiority": "paired_exact",
    "exact_paired_binary_noninferiority": "paired_exact",
    "LedgerConflict": "ledger",
    "LedgerRecord": "ledger",
    "RunLedger": "ledger",
    "DEFAULT_PERTURBATIONS": "perturb",
    "Perturbation": "perturb",
    "run_perturbations": "perturb",
    "equivalent": "replay",
    "sandbox_replay": "replay",
    "structural_shape": "replay",
    "LeakageError": "splits",
    "Splits": "splits",
    "assert_disjoint": "splits",
    "make_splits": "splits",
    "Interval": "statistics",
    "PairedSample": "statistics",
    "exact_binomial_upper": "statistics",
    "group_bootstrap_mean": "statistics",
    "holm_adjust": "statistics",
    "noninferiority": "statistics",
    "paired_group_bootstrap_diff": "statistics",
    "paired_ratio": "statistics",
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    module = _EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(f".{module}", __name__), name)


def __dir__() -> list[str]:
    return __all__
