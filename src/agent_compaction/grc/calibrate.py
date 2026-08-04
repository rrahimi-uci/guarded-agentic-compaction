"""Algorithm 6 — gate calibration with a valid risk statement.

The nonconformity score ``q(z)`` is a logistic model over *entry-only* observable
risk features (proposal Eq. 17). An LLM's verbal confidence is never a feature and
nothing unavailable at the boundary is either. Predictions used for calibration are
scenario-grouped out-of-fold.

Two quantities are reported, and conflating them would be the easy mistake:

``unproductive``
    abstained *or* wrong. The score is trained on this, because that is what
    determines the verifier pass rate ``ρ`` and therefore the wasted-attempt term
    of Eq. (8).
``violation``
    wrong only — a contract violation after dispatch. This is the safety-critical
    quantity, and it is the one the Clopper–Pearson certificate of Eq. (18) bounds.

Production compilers fit the score model on development groups, freeze it, and use
calibration groups only for threshold selection. The grid ``Λ`` is fixed a priori
with 11 values and the confidence budget ``δ`` is Bonferroni-split across it. With
few calibration groups the bound demands *zero* observed violations and returns
``RETIRE`` otherwise — which is the correct output, not a failure.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Sequence

from ..paths import resolve_path
from ..schema.artifacts import Gate, GateModel, HardGuard
from .program import Program

__all__ = [
    "GRID",
    "clopper_pearson_upper",
    "GateFeatures",
    "extract_features",
    "fit_gate_model",
    "calibrate_gate",
    "CalibrationSample",
]

#: Pre-registered threshold grid, |Λ| = 11 (proposal §4.6).
GRID: tuple[float, ...] = (0.02, 0.05, 0.08, 0.11, 0.14, 0.17, 0.20, 0.25, 0.30, 0.40, 0.50)

FEATURE_NAMES: tuple[str, ...] = (
    "unseen_category",
    "knn_distance",
    "missing_optional",
    "hull_margin",
    "drift_days",
    "provenance_ambiguity",
    "branch_entropy",
)


def _jsonable(v: Any) -> Any:
    return v if isinstance(v, (str, int, float, bool)) or v is None else str(v)


def clopper_pearson_upper(k: int, n: int, conf: float) -> float:
    """One-sided exact upper bound on a binomial rate.

    ``conf`` is the coverage of the one-sided interval (e.g. 0.9909 for
    1 − δ/|Λ| with δ = 0.10 and |Λ| = 11). Uses the Beta quantile identity; falls
    back to the closed form when ``k == 0``.
    """

    if n < 0 or k < 0 or k > n:
        raise ValueError("expected 0 <= k <= n")
    if not 0.0 < conf < 1.0:
        raise ValueError("conf must be between 0 and 1")
    if n == 0:
        return 1.0
    if k >= n:
        return 1.0
    alpha = 1.0 - conf
    if k == 0:
        return 1.0 - alpha ** (1.0 / n)
    try:
        from scipy.stats import beta

        return float(beta.ppf(conf, k + 1, n - k))
    except Exception:  # pragma: no cover - scipy always present in the lock
        lo, hi = k / n, 1.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if _binom_cdf(k, n, mid) > alpha:
                lo = mid
            else:
                hi = mid
        return hi


def _binom_cdf(k: int, n: int, p: float) -> float:
    total = 0.0
    for i in range(k + 1):
        total += math.comb(n, i) * (p**i) * ((1 - p) ** (n - i))
    return total


# ---------------------------------------------------------------------------
# features
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class GateFeatures:
    """Fitted training distribution needed to score an unseen entry state.

    Feature semantics follow the *hull kind* of each guard clause, not the raw
    value type. That distinction matters: an ``unseen_category`` signal computed by
    set membership on a high-cardinality field (an email address, a document id)
    fires on literally every unseen episode and turns the score into noise. Enum
    hulls contribute unseen-category mass, interval hulls contribute margin, regex
    hulls contribute a violation flag.
    """

    paths: tuple[str, ...] = ()
    hull_kinds: dict[str, str] = field(default_factory=dict)
    categories: dict[str, set[Any]] = field(default_factory=dict)
    numeric_ranges: dict[str, tuple[float, float]] = field(default_factory=dict)
    patterns: dict[str, dict[str, Any]] = field(default_factory=dict)
    max_day: str = ""
    provenance_ambiguity: float = 0.0
    branch_entropy: float = 0.0

    @classmethod
    def fit(
        cls,
        guard: HardGuard,
        windows: Sequence[Any],
        *,
        provenance_ambiguity: float = 0.0,
        branch_entropy: float = 0.0,
    ) -> "GateFeatures":
        paths = tuple(c.path for c in guard.clauses)
        kinds = {c.path: c.hull.kind for c in guard.clauses}
        cats: dict[str, set[Any]] = {}
        nums: dict[str, tuple[float, float]] = {}
        pats: dict[str, dict[str, Any]] = {}
        for clause in guard.clauses:
            if clause.hull.kind == "enum":
                cats[clause.path] = set(clause.hull.values)
            elif clause.hull.kind == "interval":
                nums[clause.path] = (
                    float(clause.hull.low if clause.hull.low is not None else 0.0),
                    float(clause.hull.high if clause.hull.high is not None else 0.0),
                )
            elif clause.hull.kind == "regex":
                pats[clause.path] = {
                    "pattern": clause.hull.pattern,
                    "min_len": clause.hull.min_len,
                    "max_len": clause.hull.max_len,
                }
        return cls(
            paths=paths,
            hull_kinds=kinds,
            categories=cats,
            numeric_ranges=nums,
            patterns=pats,
            max_day=max((getattr(w, "day", "") for w in windows), default=""),
            provenance_ambiguity=provenance_ambiguity,
            branch_entropy=branch_entropy,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "paths": list(self.paths),
            "hull_kinds": dict(self.hull_kinds),
            "categories": {k: [_jsonable(x) for x in sorted(v, key=str)] for k, v in self.categories.items()},
            "numeric_ranges": {k: list(v) for k, v in self.numeric_ranges.items()},
            "patterns": self.patterns,
            "max_day": self.max_day,
            "provenance_ambiguity": self.provenance_ambiguity,
            "branch_entropy": self.branch_entropy,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "GateFeatures":
        return cls(
            paths=tuple(d.get("paths", ())),
            hull_kinds=dict(d.get("hull_kinds", {})),
            categories={k: set(v) for k, v in d.get("categories", {}).items()},
            numeric_ranges={k: (float(v[0]), float(v[1])) for k, v in d.get("numeric_ranges", {}).items()},
            patterns=dict(d.get("patterns", {})),
            max_day=d.get("max_day", ""),
            provenance_ambiguity=d.get("provenance_ambiguity", 0.0),
            branch_entropy=d.get("branch_entropy", 0.0),
        )

    def raw(self, entry_state: dict[str, Any], *, day: str = "") -> dict[str, float]:
        import re

        env = {"z": entry_state}
        n_enum = max(1, len(self.categories))
        unseen = 0
        missing = 0
        margin = 0.0
        for p in self.paths:
            v = resolve_path(env, p)
            if v is None:
                missing += 1
                continue
            if p in self.categories:
                key = v if isinstance(v, (str, int, bool)) else str(v)
                if key not in self.categories[p]:
                    unseen += 1
            elif p in self.numeric_ranges:
                lo, hi = self.numeric_ranges[p]
                span = (hi - lo) or 1.0
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    if v < lo:
                        margin = max(margin, (lo - v) / span)
                    elif v > hi:
                        margin = max(margin, (v - hi) / span)
            elif p in self.patterns:
                spec = self.patterns[p]
                bad = not isinstance(v, str)
                if not bad and spec.get("pattern"):
                    bad = re.match(spec["pattern"], v) is None
                if not bad and spec.get("min_len") is not None:
                    bad = len(v) < spec["min_len"] or len(v) > (spec.get("max_len") or len(v))
                if bad:
                    margin = max(margin, 1.0)
        return {
            "unseen_category": unseen / n_enum,
            "knn_distance": unseen / n_enum,
            "missing_optional": missing / max(1, len(self.paths)),
            "hull_margin": min(1.0, margin),
            "drift_days": 1.0 if (day and self.max_day and day > self.max_day) else 0.0,
            "provenance_ambiguity": self.provenance_ambiguity,
            "branch_entropy": self.branch_entropy,
        }

    def vector(self, entry_state: dict[str, Any], *, day: str = "") -> tuple[float, ...]:
        raw = self.raw(entry_state, day=day)
        return tuple(raw[name] for name in FEATURE_NAMES)


def extract_features(features: GateFeatures, entry_state: dict[str, Any], *, day: str = "") -> dict[str, float]:
    return features.raw(entry_state, day=day)


# ---------------------------------------------------------------------------
# model fitting
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class CalibrationSample:
    group: str
    features: dict[str, float]
    unproductive: bool
    violation: bool
    episode_id: str = ""


def fit_gate_model(samples: Sequence[CalibrationSample], *, seed: int = 0) -> tuple[GateModel, list[float]]:
    """Fit ``q`` with scenario-grouped out-of-fold predictions.

    Returns the model fitted on all samples plus the out-of-fold scores used for
    threshold selection. If the labels are degenerate (no observed unproductive
    dispatch) the model is constant zero and the gate relies entirely on the exact
    binomial bound — reported rather than papered over.
    """

    import numpy as np

    X = np.array([[s.features.get(f, 0.0) for f in FEATURE_NAMES] for s in samples], dtype=float)
    y = np.array([1 if s.unproductive else 0 for s in samples], dtype=int)
    groups = np.array([s.group for s in samples])

    means = X.mean(axis=0) if len(X) else np.zeros(len(FEATURE_NAMES))
    scales = X.std(axis=0) if len(X) else np.ones(len(FEATURE_NAMES))
    # Near-zero variance must be treated as zero variance: dividing by 1e-15 turns a
    # constant feature into an infinite standardized value and saturates the score.
    scales[scales < 1e-9] = 1.0

    if len(set(y.tolist())) < 2:
        model = GateModel(
            features=FEATURE_NAMES,
            weights=tuple(0.0 for _ in FEATURE_NAMES),
            bias=-6.0 if y.sum() == 0 else 6.0,
            feature_means=tuple(means.tolist()),
            feature_scales=tuple(scales.tolist()),
        )
        oof = [model.score(s.features) for s in samples]
        return model, oof

    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import GroupKFold

    Xs = (X - means) / scales
    n_groups = len(set(groups.tolist()))
    if n_groups < 2:
        # A grouped out-of-fold prediction is undefined with one group. Use a
        # constant score; the exact group-level bound will normally retire it.
        prevalence = min(1 - 1e-6, max(1e-6, float(y.mean())))
        bias = math.log(prevalence / (1.0 - prevalence))
        model = GateModel(
            features=FEATURE_NAMES,
            weights=tuple(0.0 for _ in FEATURE_NAMES),
            bias=bias,
            feature_means=tuple(means.tolist()),
            feature_scales=tuple(scales.tolist()),
        )
        return model, [prevalence] * len(samples)
    n_splits = max(2, min(5, n_groups))
    oof = [0.0] * len(samples)
    gkf = GroupKFold(n_splits=n_splits)
    for train_idx, test_idx in gkf.split(Xs, y, groups):
        if len(set(y[train_idx].tolist())) < 2:
            probability = float(y[train_idx].mean()) if len(train_idx) else float(y.mean())
            for idx in test_idx:
                oof[idx] = probability
            continue
        clf = LogisticRegression(max_iter=500, class_weight="balanced", random_state=seed)
        clf.fit(Xs[train_idx], y[train_idx])
        probs = clf.predict_proba(Xs[test_idx])[:, 1]
        for j, idx in enumerate(test_idx):
            oof[idx] = float(probs[j])

    final = LogisticRegression(max_iter=500, class_weight="balanced", random_state=seed)
    final.fit(Xs, y)
    model = GateModel(
        features=FEATURE_NAMES,
        weights=tuple(float(w) for w in final.coef_[0]),
        bias=float(final.intercept_[0]),
        feature_means=tuple(means.tolist()),
        feature_scales=tuple(scales.tolist()),
    )
    return model, oof


# ---------------------------------------------------------------------------
# threshold selection
# ---------------------------------------------------------------------------


def calibrate_gate(
    samples: Sequence[CalibrationSample],
    *,
    features: "GateFeatures | None" = None,
    model: GateModel | None = None,
    alpha: float = 0.05,
    delta: float = 0.10,
    phi_min: float = 0.02,
    grid: Sequence[float] = GRID,
    seed: int = 0,
) -> Gate:
    # ``alpha=1`` is reserved for the published support-only research ablation:
    # it deliberately disables the risk budget and therefore needs an accept-all
    # threshold outside the production grid.  Production configurations use
    # alpha < 1 and retain the fixed preregistered grid byte-for-byte.
    if alpha == 1.0 and 1.0 not in grid:
        grid = (*grid, 1.0)
    if not samples:
        return Gate(
            grid=tuple(grid),
            alpha=alpha,
            delta=delta,
            retire=True,
            notes="no admissible threshold: no calibration samples",
        )
    if not grid:
        raise ValueError("calibration grid must not be empty")
    if not 0.0 < alpha <= 1.0 or not 0.0 < delta < 1.0:
        raise ValueError("alpha must be in (0, 1] and delta must be in (0, 1)")
    if not 0.0 <= phi_min <= 1.0:
        raise ValueError("phi_min must be between 0 and 1")
    # A deployable compiler must fit the score model on development data and pass
    # that frozen model here.  Keeping the self-fitted OOF path preserves the
    # low-level public helper, but its notes make the weaker protocol explicit.
    if model is None:
        model, scores = fit_gate_model(samples, seed=seed)
        protocol = "self_fitted_group_oof"
    else:
        scores = [model.score(sample.features) for sample in samples]
        protocol = "frozen_external_model"
    n_groups = len({s.group for s in samples})
    conf = 1.0 - delta / len(grid)

    admissible: list[float] = []
    best: tuple[float, float, int, int, float] | None = None  # (eta, R+, n_acc, viol, coverage)
    rows: list[dict[str, Any]] = []
    for eta in sorted(grid):
        accepted = [i for i, q in enumerate(scores) if q <= eta]
        if not accepted:
            rows.append({"eta": eta, "n": 0, "violations": 0, "upper": 1.0, "coverage": 0.0})
            continue
        # the unit of independence is the group, not the episode
        acc_groups = {samples[i].group for i in accepted}
        viol_groups = {samples[i].group for i in accepted if samples[i].violation}
        n = len(acc_groups)
        k = len(viol_groups)
        upper = clopper_pearson_upper(k, n, conf)
        coverage = n / n_groups if n_groups else 0.0
        rows.append(
            {"eta": eta, "n": n, "violations": k, "upper": round(upper, 4), "coverage": round(coverage, 4)}
        )
        if upper <= alpha and coverage >= phi_min:
            admissible.append(eta)
            # Thresholds are visited in increasing order and acceptance is
            # monotone. Keep the last admissible row so every stored statistic
            # describes the exact threshold that will execute at runtime.
            best = (eta, upper, n, k, coverage)

    if best is None:
        return Gate(
            model=model,
            features_spec=(features.to_dict() if features is not None else {}),
            threshold=0.0,
            grid=tuple(grid),
            alpha=alpha,
            delta=delta,
            n_calibration_groups=n_groups,
            retire=True,
            notes=(
                f"protocol={protocol}; no admissible threshold: "
                + _why(rows, alpha, phi_min)
            ),
        )

    eta, upper, n_acc, viol, coverage = best
    return Gate(
        model=model,
        features_spec=(features.to_dict() if features is not None else {}),
        threshold=eta,
        grid=tuple(grid),
        alpha=alpha,
        delta=delta,
        n_calibration_groups=n_groups,
        n_accepted=n_acc,
        observed_violations=viol,
        risk_upper_bound=upper,
        coverage=coverage,
        admissible=tuple(admissible),
        retire=False,
        notes=f"protocol={protocol}; grid rows: {rows}",
    )


def _why(rows: Sequence[dict[str, Any]], alpha: float, phi_min: float) -> str:
    if not rows:
        return "no calibration samples"
    best_upper = min((r["upper"] for r in rows if r["n"]), default=1.0)
    best_cov = max((r["coverage"] for r in rows), default=0.0)
    if best_upper > alpha:
        return (
            f"tightest attainable Clopper-Pearson upper bound is {best_upper:.3f} > alpha={alpha}; "
            "more calibration groups (or zero observed violations) are required"
        )
    return f"coverage {best_cov:.3f} below phi_min={phi_min}"
