"""Statistical machinery (execution-plan §11.5, §13.6).

Everything here is grouped and paired by construction:

* **cluster bootstrap** over scenario groups, because repeated dispatches inside an
  episode and repeated episodes inside a scenario are not independent samples;
* **paired differences** on the same task instances, so that workload composition
  cannot masquerade as an effect;
* **exact binomial intervals** for gate failures and critical safety events — a
  zero observed rate is reported as an upper bound, never as "zero risk";
* **Holm correction** across secondary endpoints, and Bonferroni across the
  pre-registered gate grid (that one lives in :mod:`agent_compaction.grc.calibrate`).

Non-inferiority is one-sided by design: the question is never "is the candidate
better", it is "is the candidate not worse by more than ε".
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

__all__ = [
    "Interval",
    "PairedSample",
    "group_bootstrap_mean",
    "paired_group_bootstrap_diff",
    "paired_ratio",
    "noninferiority",
    "exact_binomial_upper",
    "holm_adjust",
    "describe",
]


@dataclass(frozen=True, slots=True)
class Interval:
    point: float
    low: float
    high: float
    level: float = 0.95
    method: str = "group_bootstrap"

    def __str__(self) -> str:  # pragma: no cover - display
        return f"{self.point:.4f} [{self.low:.4f}, {self.high:.4f}]"

    def as_dict(self) -> dict[str, Any]:
        return {
            "point": round(self.point, 6),
            "low": round(self.low, 6),
            "high": round(self.high, 6),
            "level": self.level,
            "method": self.method,
        }


@dataclass(frozen=True, slots=True)
class PairedSample:
    group: str
    baseline: float
    candidate: float

    @property
    def diff(self) -> float:
        return self.candidate - self.baseline


def _by_group(samples: Sequence[PairedSample]) -> dict[str, list[PairedSample]]:
    out: dict[str, list[PairedSample]] = {}
    for s in samples:
        out.setdefault(s.group, []).append(s)
    return out


def group_bootstrap_mean(
    values: Sequence[float],
    groups: Sequence[str],
    *,
    n_boot: int = 2000,
    level: float = 0.95,
    seed: int = 7,
) -> Interval:
    """Cluster bootstrap of a mean, resampling *groups* with replacement."""

    if not values:
        return Interval(float("nan"), float("nan"), float("nan"), level, "group_bootstrap")
    _validate_bootstrap(values, groups, n_boot=n_boot, level=level)
    buckets: dict[str, list[float]] = {}
    for v, g in zip(values, groups):
        buckets.setdefault(g, []).append(v)
    keys = list(buckets)
    point = sum(values) / len(values)
    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(n_boot):
        pool: list[float] = []
        for _ in range(len(keys)):
            pool.extend(buckets[keys[rng.randrange(len(keys))]])
        if pool:
            means.append(sum(pool) / len(pool))
    means.sort()
    lo = means[int((1 - level) / 2 * len(means))]
    hi = means[min(len(means) - 1, int((1 + level) / 2 * len(means)))]
    return Interval(point, lo, hi, level, "group_bootstrap")


def paired_group_bootstrap_diff(
    samples: Sequence[PairedSample],
    *,
    n_boot: int = 2000,
    level: float = 0.95,
    seed: int = 11,
) -> Interval:
    """Cluster bootstrap of the paired mean difference (candidate − baseline)."""

    if not samples:
        return Interval(float("nan"), float("nan"), float("nan"), level, "paired_group_bootstrap")
    _validate_bootstrap(samples, samples, n_boot=n_boot, level=level)
    buckets = _by_group(samples)
    keys = list(buckets)
    point = sum(s.diff for s in samples) / len(samples)
    rng = random.Random(seed)
    diffs: list[float] = []
    for _ in range(n_boot):
        pool: list[float] = []
        for _ in range(len(keys)):
            pool.extend(s.diff for s in buckets[keys[rng.randrange(len(keys))]])
        if pool:
            diffs.append(sum(pool) / len(pool))
    diffs.sort()
    lo = diffs[int((1 - level) / 2 * len(diffs))]
    hi = diffs[min(len(diffs) - 1, int((1 + level) / 2 * len(diffs)))]
    return Interval(point, lo, hi, level, "paired_group_bootstrap")


def paired_ratio(
    samples: Sequence[PairedSample],
    *,
    n_boot: int = 2000,
    level: float = 0.95,
    seed: int = 13,
) -> Interval:
    """Cluster bootstrap of the ratio of means (the ``R_req`` endpoint of Eq. 9).

    The ratio of means is bootstrapped rather than the mean of ratios: episodes with
    a small baseline count would otherwise dominate.
    """

    if not samples:
        return Interval(float("nan"), float("nan"), float("nan"), level, "paired_ratio_bootstrap")
    _validate_bootstrap(samples, samples, n_boot=n_boot, level=level)
    buckets = _by_group(samples)
    keys = list(buckets)
    num = sum(s.candidate for s in samples)
    den = sum(s.baseline for s in samples)
    point = num / den if den else float("nan")
    if not den:
        return Interval(
            point,
            float("nan"),
            float("nan"),
            level,
            "paired_ratio_bootstrap",
        )
    rng = random.Random(seed)
    ratios: list[float] = []
    for _ in range(n_boot):
        n = d = 0.0
        for _ in range(len(keys)):
            for s in buckets[keys[rng.randrange(len(keys))]]:
                n += s.candidate
                d += s.baseline
        if d:
            ratios.append(n / d)
    ratios.sort()
    if not ratios:
        return Interval(
            point,
            float("nan"),
            float("nan"),
            level,
            "paired_ratio_bootstrap",
        )
    lo = ratios[int((1 - level) / 2 * len(ratios))]
    hi = ratios[min(len(ratios) - 1, int((1 + level) / 2 * len(ratios)))]
    return Interval(point, lo, hi, level, "paired_ratio_bootstrap")


@dataclass(frozen=True, slots=True)
class NonInferiorityResult:
    endpoint: str
    margin: float
    diff: Interval
    passed: bool
    direction: str = "higher_is_better"

    def as_dict(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "margin": self.margin,
            "diff": self.diff.as_dict(),
            "passed": self.passed,
            "direction": self.direction,
        }


def noninferiority(
    samples: Sequence[PairedSample],
    *,
    endpoint: str,
    margin: float,
    level: float = 0.95,
    n_boot: int = 2000,
    seed: int = 17,
    direction: str = "higher_is_better",
) -> NonInferiorityResult:
    """One-sided paired non-inferiority test with a group-aware interval.

    ``higher_is_better``: pass when the lower bound of (candidate − baseline)
    exceeds ``−margin``. ``lower_is_better``: pass when the upper bound is below
    ``+margin``.
    """

    interval = paired_group_bootstrap_diff(samples, n_boot=n_boot, level=2 * level - 1, seed=seed)
    if direction == "higher_is_better":
        passed = interval.low > -margin
    else:
        passed = interval.high < margin
    return NonInferiorityResult(endpoint, margin, interval, passed, direction)


def exact_binomial_upper(k: int, n: int, *, conf: float = 0.95) -> float:
    """One-sided Clopper–Pearson upper bound (re-exported for report symmetry)."""

    from ..grc.calibrate import clopper_pearson_upper

    return clopper_pearson_upper(k, n, conf)


def holm_adjust(pvalues: dict[str, float], *, alpha: float = 0.05) -> dict[str, dict[str, Any]]:
    """Holm step-down correction across secondary endpoints."""

    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(items)
    out: dict[str, dict[str, Any]] = {}
    prev = 0.0
    for i, (name, p) in enumerate(items):
        adj = min(1.0, max(prev, (m - i) * p))
        prev = adj
        out[name] = {"p": p, "p_holm": adj, "reject": adj <= alpha}
    return out


def describe(values: Sequence[float]) -> dict[str, float]:
    if not values:
        return {}
    xs = sorted(values)
    n = len(xs)

    def q(p: float) -> float:
        return xs[min(n - 1, int(p * n))]

    mean = sum(xs) / n
    var = sum((x - mean) ** 2 for x in xs) / n
    return {
        "n": float(n),
        "mean": mean,
        "sd": math.sqrt(var),
        "cv": (math.sqrt(var) / mean) if mean else float("nan"),
        "p50": q(0.5),
        "p95": q(0.95),
        "p99": q(0.99),
        "min": xs[0],
        "max": xs[-1],
    }


def _validate_bootstrap(
    values: Sequence[Any], groups: Sequence[Any], *, n_boot: int, level: float
) -> None:
    if len(values) != len(groups):
        raise ValueError("values and groups must have equal length")
    if n_boot <= 0:
        raise ValueError("n_boot must be positive")
    if not 0.0 < level < 1.0:
        raise ValueError("level must be between 0 and 1")
