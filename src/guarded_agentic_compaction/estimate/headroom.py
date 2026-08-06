"""The feasibility estimator: Eq. (10) before any compiler runs.

``ac.estimate()`` is the cheapest useful thing in the system. It answers "is there
anything here?" from traces alone and can return a decisive *no* for the price of an
afternoon (use-cases, adoption recipe step 3).

It reports:

* ``n_B`` — baseline model requests per episode;
* ``φ`` (oracle) — the fraction of episodes containing at least one eligible
  candidate region, *before* any guard or gate narrows it;
* ``k`` — model requests removable per successful dispatch;
* the achievable ceiling ``Δ_max = φ·k / n_B`` and the necessary condition
  ``φρk ≥ Δ·n_B``;
* blocked-window mass attributed **by reason and by tool**, so the effect catalog gets
  written in descending order of value rather than alphabetically;
* independent group / principal / day counts, and the calibration sample size the
  Clopper–Pearson bound would need at the target ``α``;
* the economic break-even of Eq. (12) under low/base/high cost assumptions.

The ceiling is an *oracle* number: it assumes ρ = 1 and a gate that never abstains.
Anything the compiler actually achieves must be lower.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Sequence

from ..graph.normalize import DataQualityReport, data_quality
from ..graph.provenance import GroundabilityPolicy, PATG, build_all
from ..graph.windows import MiningResult, mine
from ..schema.effects import EffectCatalog
from ..schema.traces import Episode

__all__ = ["EstimateReport", "estimate", "required_calibration_groups", "break_even"]


def required_calibration_groups(alpha: float = 0.05, delta: float = 0.10, grid_size: int = 11) -> int:
    """Smallest ``n`` for which a zero-violation exact bound can clear ``α``.

    ``1 − (δ/|Λ|)^(1/n) ≤ α``. This is the sample-complexity fact that decides
    whether a workload can ever be calibrated, and reporting it up front is cheaper
    than discovering it at Gate 3.
    """

    conf_alpha = delta / grid_size
    return int(math.ceil(math.log(conf_alpha) / math.log(1 - alpha)))


def break_even(
    *,
    build_cost_usd: float,
    maintenance_cost_usd_per_year: float,
    saving_per_episode_usd: float,
) -> dict[str, float]:
    """Eq. (12) / §9.6: episodes needed per year and per day to repay the build."""

    if saving_per_episode_usd <= 0:
        return {"episodes_per_year": float("inf"), "episodes_per_day": float("inf")}
    total = build_cost_usd + maintenance_cost_usd_per_year
    per_year = total / saving_per_episode_usd
    return {"episodes_per_year": per_year, "episodes_per_day": per_year / 365.0}


@dataclass(slots=True)
class EstimateReport:
    snapshot_id: str = ""
    n_episodes: int = 0
    n_groups: int = 0
    n_principals: int = 0
    n_days: int = 0
    n_B: float = 0.0
    phi_oracle: float = 0.0
    phi_any: float = 0.0
    k_mean: float = 0.0
    delta_max: float = 0.0
    required_phi_rho_k: float = 0.0
    target_delta: float = 0.10
    feasible: bool = False
    blocked_shares: dict[str, float] = field(default_factory=dict)
    blocked_by_tool: dict[str, int] = field(default_factory=dict)
    undeclared_tools: list[str] = field(default_factory=list)
    top_candidates: list[dict[str, Any]] = field(default_factory=list)
    data_quality: DataQualityReport | None = None
    calibration_groups_required: int = 0
    calibration_groups_available: int = 0
    economics: dict[str, float] = field(default_factory=dict)
    slot_stats: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = [
            "estimate report",
            "───────────────",
            f" n_B  = {self.n_B:.1f} model requests/episode  "
            f"({self.n_episodes} episodes, {self.n_groups} groups, "
            f"{self.n_principals} principals, {self.n_days} days)",
            f" ceiling: phi={self.phi_oracle:.2f} (any candidate: {self.phi_any:.2f})  k={self.k_mean:.1f}  "
            f"->  max request reduction {100 * self.delta_max:.1f}%   [Eq. 10, oracle: rho=1]",
            f" target Δ={self.target_delta:.2f} needs phi*rho*k >= {self.required_phi_rho_k:.2f}  "
            f"-> {'FEASIBLE' if self.feasible else 'NOT FEASIBLE at this ceiling'}",
        ]
        if self.blocked_shares:
            parts = ", ".join(f"{100 * v:.0f}% by {k}" for k, v in list(self.blocked_shares.items())[:4])
            lines.append(f" blocked: {parts}")
        if self.blocked_by_tool:
            parts = ", ".join(f"{t}({n})" for t, n in list(self.blocked_by_tool.items())[:5])
            lines.append(f" blocked-window mass by tool: {parts}")
        if self.undeclared_tools:
            lines.append(f" undeclared (UNKNOWN, never compiled): {', '.join(self.undeclared_tools[:6])}")
        lines.append(
            f" calibration: {self.calibration_groups_available} groups available, "
            f"{self.calibration_groups_required} required for a zero-violation bound at the target α"
        )
        if self.slot_stats:
            lines.append(f" slots: {self.slot_stats}")
        for c in self.top_candidates[:5]:
            lines.append(
                f"   candidate {c['tools']}  support={c['groups']} groups/{c['days']} days  "
                f"k={c['k']:.1f}  score={c['score']:.1f}"
            )
        if self.economics:
            lines.append(
                f" break-even: {self.economics.get('episodes_per_day', float('nan')):.0f} episodes/day "
                f"at ${self.economics.get('saving_per_episode_usd', 0):.4f} saved/episode"
            )
        for n in self.notes:
            lines.append(f" note: {n}")
        return "\n".join(lines)

    def as_dict(self) -> dict[str, Any]:
        d = {
            k: v
            for k, v in self.__dict__.items()
            if k != "data_quality"
        } if hasattr(self, "__dict__") else {}
        if not d:
            d = {f: getattr(self, f) for f in self.__slots__ if f != "data_quality"}  # type: ignore[attr-defined]
        if self.data_quality is not None:
            d["data_quality"] = {
                "n_episodes": self.data_quality.n_episodes,
                "n_eligible": self.data_quality.n_eligible,
                "n_groups": self.data_quality.n_groups,
                "span_completeness": self.data_quality.span_completeness,
                "effect_coverage": self.data_quality.effect_coverage,
                "outcome_coverage": self.data_quality.outcome_coverage,
                "gate0_pass": self.data_quality.gate0_pass,
                "rejection_reasons": self.data_quality.rejection_reasons,
            }
        return d


def estimate(
    episodes: Sequence[Episode],
    catalog: EffectCatalog,
    *,
    entry_schema: Sequence[str] = (),
    target_delta: float = 0.10,
    w_min: int = 2,
    w_max: int = 8,
    b_min: int = 2,
    s_min: int = 5,
    min_days: int = 3,
    kappa: int = 3,
    max_depth: int = 2,
    alpha: float = 0.05,
    delta: float = 0.10,
    snapshot_id: str = "",
    graphs: Sequence[PATG] | None = None,
    policy: GroundabilityPolicy | None = None,
    mining: MiningResult | None = None,
    build_cost_usd: float = 70000.0,
    maintenance_cost_usd_per_year: float = 15000.0,
    cache_discount: float = 1 / 3,
) -> EstimateReport:
    rep = EstimateReport(snapshot_id=snapshot_id, target_delta=target_delta)
    if not episodes:
        rep.notes.append("no episodes in snapshot")
        return rep

    rep.n_episodes = len(episodes)
    rep.n_groups = len({ep.group_id for ep in episodes})
    rep.n_principals = len({ep.envelope.principal for ep in episodes})
    rep.n_days = len({ep.envelope.day for ep in episodes})
    rep.n_B = sum(ep.n_requests() for ep in episodes) / len(episodes)
    rep.data_quality = data_quality(episodes, catalog)
    rep.undeclared_tools = rep.data_quality.undeclared_tools

    if graphs is None:
        graphs, policy = build_all(episodes, catalog, policy, max_depth=max_depth, kappa=kappa)
    if mining is None:
        mining = mine(
            graphs,
            catalog,
            entry_schema=entry_schema,
            w_min=w_min,
            w_max=w_max,
            b_min=b_min,
            s_min=s_min,
            min_days=min_days,
        )

    slots: Counter = Counter()
    for g in graphs:
        for key, value in g.diagnostics.items():
            slots[key] += value
    rep.slot_stats = dict(slots)

    rep.blocked_shares = mining.blocked_shares()
    rep.blocked_by_tool = dict(mining.blocked_by_tool.most_common(8))

    # Oracle coverage is measured for the *top-scoring* candidate, not for the union
    # of every candidate: an artifact is compiled per family, and "some window
    # somewhere matched" would report a ceiling no single artifact can deliver. The
    # union is reported separately as phi_any.
    ks: list[float] = []
    covered: set[str] = set()
    any_covered: set[str] = set()
    for fam in mining.families:
        for w in fam.windows:
            any_covered.add(w.episode.episode_id)
    if mining.families:
        best = mining.families[0]
        covered = {w.episode.episode_id for w in best.windows}
        ks = [float(w.removed_requests) for w in best.windows]
    rep.phi_any = len(any_covered) / len(episodes)
    rep.phi_oracle = len(covered) / len(episodes)
    rep.k_mean = (sum(ks) / len(ks)) if ks else 0.0
    rep.delta_max = (rep.phi_oracle * rep.k_mean / rep.n_B) if rep.n_B else 0.0
    rep.required_phi_rho_k = target_delta * rep.n_B
    rep.feasible = rep.phi_oracle * rep.k_mean >= rep.required_phi_rho_k

    rep.top_candidates = [
        {
            "tools": [t.split(".")[-1] for t in fam.tools],
            "groups": fam.support,
            "days": len(fam.days),
            "principals": len(fam.principals),
            "k": fam.mean_removed,
            "score": fam.score(),
            "canon_hash": fam.canon_hash,
        }
        for fam in mining.families[:8]
    ]

    rep.calibration_groups_required = required_calibration_groups(alpha=alpha, delta=delta)
    rep.calibration_groups_available = int(rep.n_groups * 0.20)
    if rep.calibration_groups_available < rep.calibration_groups_required:
        rep.notes.append(
            f"calibration is the binding constraint: {rep.calibration_groups_available} groups at a 20% "
            f"split vs {rep.calibration_groups_required} required; the exact bound cannot clear α={alpha}"
        )

    # economics: dollar saving lags request saving because the removed prefill is cached
    dollars = [ep.attributes.get("dollars", 0.0) for ep in episodes]
    per_episode_cost = (sum(dollars) / len(dollars)) if dollars else 0.0
    saving = per_episode_cost * rep.delta_max * cache_discount
    rep.economics = {
        "cost_per_episode_usd": per_episode_cost,
        "saving_per_episode_usd": saving,
        "cache_discount": cache_discount,
        **break_even(
            build_cost_usd=build_cost_usd,
            maintenance_cost_usd_per_year=maintenance_cost_usd_per_year,
            saving_per_episode_usd=saving,
        ),
    }
    rep.notes.append(
        "this ceiling covers compiled read-only regions only: savings from route "
        "specialisation (removing a predictable coordinator turn or handoff) are not "
        "modelled by Eq. (10) and can exceed it"
    )
    if not rep.feasible:
        rep.notes.append(
            "the oracle ceiling is below the target: no gate, contract or threshold setting can "
            "recover it — hand-write the top region or stop"
        )
    return rep
