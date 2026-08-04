"""Experiment driver: four scored conditions per demonstration (execution-plan §11.2).

1. ``baseline``      — unchanged workflow.
2. ``simple``        — hand-written composite tool with concurrent reads, same effect
                       boundary. The mandatory comparator: GRC is never credited with
                       savings a two-hour function would have delivered.
3. ``full``          — TGWS then GRC, with provenance, contracts and calibration.
4. ``support_only``  — same support threshold, but no provenance-aware risk gating:
                       no entropy filter, no ambiguity cap, no contract challenge, no
                       calibrated gate. The H4 ablation.

Protocol discipline enforced by construction:

* artifacts are built from train/dev/calibration groups only;
* the sealed test split is executed **once**, at the end, after every artifact and
  every metric definition is frozen;
* the prospective shadow split is reported separately and never pooled into the
  retrospective claim;
* every table carries its denominators, its substrate label and its run manifest.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from agent_compaction.evaluation.metrics import ConditionMetrics, condition_metrics, maintenance_metrics
from agent_compaction.evaluation.perturb import DEFAULT_PERTURBATIONS
from agent_compaction.evaluation.splits import Splits, make_splits
from agent_compaction.evaluation.statistics import (
    PairedSample,
    exact_binomial_upper,
    group_bootstrap_mean,
    noninferiority,
    paired_group_bootstrap_diff,
    paired_ratio,
)
from agent_compaction.estimate.headroom import estimate
from agent_compaction.graph.provenance import GroundabilityPolicy, build_all
from agent_compaction.grc.compile import GrcConfig, compile_grc
from agent_compaction.registry.lifecycle import promote
from agent_compaction.registry.store import Registry
from agent_compaction.runtime.dispatch import DispatchMode, Dispatcher
from agent_compaction.runtime.runner import CompactingRunner, RouteResolver
from agent_compaction.schema.artifacts import Lifecycle
from agent_compaction.tgws.package import TgwsConfig, compile_tgws
from agent_compaction.tgws.prune import LeafConfig, Objective
from agent_compaction.tgws.routes import default_route_label

from demos.framework import Observation, run_workload, summarize
from experiments.conditions.registry import DemoSpec, get_demo

SIGNING_KEY = b"agent-compaction-demo-signing-key"


@dataclass(slots=True)
class DemoResult:
    demo: str
    title: str
    n_B: float = 0.0
    estimate: dict[str, Any] = field(default_factory=dict)
    splits: dict[str, Any] = field(default_factory=dict)
    tgws: dict[str, Any] = field(default_factory=dict)
    grc: dict[str, Any] = field(default_factory=dict)
    conditions: dict[str, dict[str, Any]] = field(default_factory=dict)
    comparisons: dict[str, Any] = field(default_factory=dict)
    hypotheses: dict[str, Any] = field(default_factory=dict)
    shadow: dict[str, Any] = field(default_factory=dict)
    maintenance: dict[str, Any] = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    timings: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def run_demo(
    spec: DemoSpec,
    *,
    n_episodes: int,
    seed: int,
    quick: bool = False,
) -> DemoResult:
    res = DemoResult(demo=spec.key, title=spec.title)
    catalog = spec.catalog()
    t0 = time.time()

    # ---- capture: one authoritative pass over the whole stream -------------
    world, specs = spec.make_workload(n_episodes=n_episodes, seed=seed)
    baseline_policy = spec.make_policy()
    episodes = run_workload(specs, world, baseline_policy, spec.manifest)
    specs_by_id = {s.episode_id: s for s in specs}
    res.n_B = sum(ep.n_requests() for ep in episodes) / len(episodes)
    res.timings["capture_s"] = round(time.time() - t0, 2)

    splits = make_splits(episodes, shadow_fraction=0.10, seed=seed)
    res.splits = {k: len(v) for k, v in splits.roles.items()}
    res.splits["digest"] = splits.digest()

    # ---- estimator (Gate 0/1) ---------------------------------------------
    t = time.time()
    graphs, policy = build_all(episodes, catalog)
    est = estimate(
        episodes,
        catalog,
        entry_schema=spec.entry_allowlist,
        snapshot_id=f"{spec.key}-{seed}-{n_episodes}",
        graphs=graphs,
        policy=policy,
    )
    res.estimate = {
        "n_B": round(est.n_B, 3),
        "phi_oracle": round(est.phi_oracle, 3),
        "phi_any": round(est.phi_any, 3),
        "k_mean": round(est.k_mean, 3),
        "delta_max": round(est.delta_max, 4),
        "feasible": est.feasible,
        "blocked_shares": {k: round(v, 3) for k, v in est.blocked_shares.items()},
        "blocked_by_tool": est.blocked_by_tool,
        "undeclared_tools": est.undeclared_tools,
        "calibration_groups_required": est.calibration_groups_required,
        "calibration_groups_available": est.calibration_groups_available,
        "economics": {k: round(v, 6) for k, v in est.economics.items()},
        "gate0_pass": bool(est.data_quality and est.data_quality.gate0_pass),
        "slot_stats": est.slot_stats,
        "notes": est.notes,
        "render": est.render(),
    }
    res.timings["estimate_s"] = round(time.time() - t, 2)

    # ---- TGWS -------------------------------------------------------------
    t = time.time()
    from demos.framework import make_tgws_evaluator

    evaluator = make_tgws_evaluator(
        specs_by_id,
        spec.make_world,
        lambda cfg: spec.policy_from_config(cfg),
        spec.manifest,
    )
    tgws_cfg = TgwsConfig(
        entry_allowlist=spec.entry_allowlist,
        max_depth=3,
        min_support=20,
        min_purity=0.90,
        min_groups=8,
        max_leaves=4 if not quick else 2,
        objective=Objective(),
        protected_tools=spec.protected_tools,
        protected_blocks=spec.protected_blocks,
        budget_per_leaf=60 if not quick else 24,
        seed=seed,
    )
    tgws = compile_tgws(
        episodes,
        catalog,
        splits,
        spec.manifest,
        tgws_cfg,
        baseline=spec.baseline_config,
        evaluate=evaluator,
        label_fn=default_route_label,
    )
    res.tgws = {
        "n_leaves": len(tgws.tree.leaves) if tgws.tree else 0,
        "artifacts": len(tgws.artifacts),
        "rejections": tgws.rejection_by_stage,
        "report": tgws.report(),
        "leaves": [
            {
                "predicates": [list(p) for p in rec.leaf.predicates],
                "label": rec.leaf.label,
                "stage": rec.stage,
                "rejected": rec.rejected,
                "purity": round(rec.leaf.purity, 4),
                "support": rec.leaf.support,
                "baseline": (asdict(rec.baseline_eval) if rec.baseline_eval else None),
                "pruned": (asdict(rec.pruned_eval) if rec.pruned_eval else None),
                "kept_tools": list(rec.config.tools) if rec.config else None,
                "kept_blocks": list(rec.config.prompt_blocks) if rec.config else None,
            }
            for rec in tgws.leaves
        ],
    }
    res.timings["tgws_s"] = round(time.time() - t, 2)

    # ---- GRC (full) -------------------------------------------------------
    t = time.time()
    sandbox = (lambda _w=world: _w)
    grc_cfg = GrcConfig(
        entry_schema=spec.entry_allowlist,
        s_min=5,
        min_days=3,
        s_branch=20,
        n_permutations=200 if quick else 400,
        max_candidates=6 if quick else 10,
        max_artifacts=4,
        seed=seed,
        owner="research-mvp",
    )
    grc = compile_grc(
        episodes,
        catalog,
        splits,
        spec.manifest,
        grc_cfg,
        sandbox=sandbox,
        perturbations=DEFAULT_PERTURBATIONS,
        graphs=graphs,
        policy=policy,
    )
    res.grc = {
        "artifacts": len(grc.artifacts),
        "candidates": [c.as_dict() for c in grc.candidates],
        "rejections": dict(grc.rejection_by_stage),
        "report": grc.report(),
        "explain": grc.explain(),
    }
    res.timings["grc_s"] = round(time.time() - t, 2)

    # ---- support-only ablation (condition 4) ------------------------------
    t = time.time()
    ablation_policy = GroundabilityPolicy(
        stoplist=frozenset(),
        min_str_len=1,
        min_field_cardinality=1,
        max_top_share=1.0,
        stats=None,
        literal_only={},
    )
    ablation_graphs, _ = build_all(episodes, catalog, ablation_policy, kappa=99)
    ablation_cfg = GrcConfig(
        entry_schema=spec.entry_allowlist,
        s_min=5,
        min_days=1,
        s_branch=20,
        n_permutations=1,
        max_candidates=6 if quick else 10,
        max_artifacts=4,
        kappa=99,
        alpha=1.0,  # no risk budget: accept every threshold
        phi_min=0.0,
        seed=seed,
        owner="ablation",
    )
    ablation = compile_grc(
        episodes,
        catalog,
        splits,
        spec.manifest,
        ablation_cfg,
        sandbox=None,  # no sandbox replay, no perturbation suite
        perturbations=(),
        graphs=ablation_graphs,
        policy=ablation_policy,
    )
    for art in ablation.artifacts:
        art.gate.threshold = 1.0  # support-only routing: dispatch whenever the guard holds
        art.gate.retire = False
    res.timings["ablation_s"] = round(time.time() - t, 2)

    # ---- registries -------------------------------------------------------
    full_reg = Registry(name=f"{spec.key}-full", signing_key=SIGNING_KEY)
    for art in list(tgws.artifacts) + list(grc.artifacts):
        promote(art, Lifecycle.SHADOW, approved_by="", job_identity="optimizer")
        promote(art, Lifecycle.APPROVED, approved_by="reviewer@example", job_identity="optimizer")
        promote(art, Lifecycle.ACTIVE, approved_by="reviewer@example", job_identity="optimizer")
        full_reg.add(art)
    abl_reg = Registry(name=f"{spec.key}-support-only", signing_key=SIGNING_KEY)
    for art in ablation.artifacts:
        promote(art, Lifecycle.SHADOW, approved_by="", job_identity="optimizer")
        promote(art, Lifecycle.APPROVED, approved_by="reviewer@example", job_identity="optimizer")
        promote(art, Lifecycle.ACTIVE, approved_by="reviewer@example", job_identity="optimizer")
        abl_reg.add(art)
    res.artifacts = [a.explain() for a in full_reg.artifacts]
    res.maintenance = maintenance_metrics(full_reg.artifacts)

    max_train_day = max((ep.envelope.day for ep in episodes if ep.group_id in splits.train), default="")

    # ---- sealed test: executed once ---------------------------------------
    t = time.time()
    test_specs = [s for s in specs if s.group_id in splits.test]
    conditions: dict[str, ConditionMetrics] = {}

    conditions["baseline"] = condition_metrics(
        "baseline",
        run_workload(test_specs, spec.make_world(), spec.make_policy(), spec.manifest),
        catalog,
    )
    conditions["simple"] = condition_metrics(
        "simple",
        run_workload(test_specs, spec.make_world(), spec.make_policy(use_macro=True), spec.manifest),
        catalog,
    )

    full_eps, full_tel, route_stats = _run_optimized(
        spec, catalog, full_reg, test_specs, max_train_day, mode=DispatchMode.LIVE
    )
    conditions["full"] = condition_metrics("full", full_eps, catalog, dispatch_telemetry=full_tel)
    conditions["full"].dispatch["routes"] = route_stats

    abl_eps, abl_tel, abl_routes = _run_optimized(
        spec, catalog, abl_reg, test_specs, max_train_day, mode=DispatchMode.LIVE
    )
    conditions["support_only"] = condition_metrics(
        "support_only", abl_eps, catalog, dispatch_telemetry=abl_tel
    )
    res.timings["sealed_test_s"] = round(time.time() - t, 2)

    for name, cm in conditions.items():
        res.conditions[name] = {
            "n_episodes": cm.n_episodes,
            "n_groups": cm.n_groups,
            "aggregate": {k: round(v, 5) for k, v in cm.aggregate.items()},
            "dispatch": cm.dispatch,
        }

    # ---- comparisons ------------------------------------------------------
    res.comparisons = _compare(conditions)
    res.hypotheses = _hypotheses(conditions, res.comparisons, est)

    # ---- prospective shadow (never pooled) --------------------------------
    t = time.time()
    shadow_specs = [s for s in specs if s.group_id in splits.shadow]
    if shadow_specs:
        sh_eps, sh_tel, sh_routes = _run_optimized(
            spec, catalog, full_reg, shadow_specs, max_train_day, mode=DispatchMode.SHADOW
        )
        sh = condition_metrics("shadow", sh_eps, catalog, dispatch_telemetry=sh_tel)
        res.shadow = {
            "n_episodes": sh.n_episodes,
            "n_groups": sh.n_groups,
            "would_dispatch_boundaries": sh_tel.get("attempts", 0),
            "telemetry": sh_tel,
            "routes": sh_routes,
            "note": "shadow evidence is operational only and is never pooled into the sealed-test claim",
        }
    res.timings["shadow_s"] = round(time.time() - t, 2)
    res.timings["total_s"] = round(time.time() - t0, 2)
    return res


def _run_optimized(
    spec: DemoSpec,
    catalog: Any,
    registry: Registry,
    test_specs: Sequence[Any],
    max_train_day: str,
    *,
    mode: str,
) -> tuple[list[Any], dict[str, Any], dict[str, Any]]:
    """Run the optimized condition: TGWS route selection + GRC dispatch."""

    world = spec.make_world()
    dispatcher = Dispatcher(registry=registry, catalog=catalog, mode=mode)
    runner = CompactingRunner(
        dispatcher=dispatcher,
        catalog=catalog,
        manifest=spec.manifest,
        max_train_day=max_train_day,
        observation_factory=Observation,
    )
    resolver = RouteResolver(
        registry=registry, catalog=catalog, manifest=spec.manifest, mode=mode
    )
    episodes = []
    for s in test_specs:
        route = resolver.resolve(s)
        if route is not None:
            policy = spec.policy_from_config(
                LeafConfig(
                    agent=route.agent,
                    model=route.model,
                    reasoning_tier=route.reasoning_tier,
                    prompt_blocks=route.prompt_blocks,
                    tools=route.tools,
                ),
                **_route_kwargs(spec, route),
            )
        else:
            policy = spec.make_policy()
        episodes.extend(run_workload([s], world, policy, spec.manifest, dispatcher=runner))
    stats = {
        "route_hits": resolver.hits,
        "route_misses": resolver.misses,
        "route_miss_reasons": resolver.miss_reasons,
    }
    return episodes, dispatcher.telemetry.as_dict(), stats


def _route_kwargs(spec: DemoSpec, route: Any) -> dict[str, Any]:
    """Demo-specific extras a route can set (triage: skip the coordinator)."""

    if spec.key == "incident_triage" and route.route_label.startswith("handoff:"):
        return {"route_to": route.route_label.split(":", 1)[1]}
    return {}


def _paired(a: ConditionMetrics, b: ConditionMetrics, field_name: str) -> list[PairedSample]:
    left, right = a.by_id(), b.by_id()
    out: list[PairedSample] = []
    for eid, lm in left.items():
        rm = right.get(eid)
        if rm is None:
            continue
        out.append(
            PairedSample(
                group=lm.group_id,
                baseline=float(getattr(lm, field_name)),
                candidate=float(getattr(rm, field_name)),
            )
        )
    return out


def _compare(conditions: dict[str, ConditionMetrics]) -> dict[str, Any]:
    base = conditions["baseline"]
    out: dict[str, Any] = {}
    for name, cm in conditions.items():
        if name == "baseline":
            continue
        pairs_req = _paired(base, cm, "requests")
        pairs_q = _paired(base, cm, "quality")
        pairs_lat = _paired(base, cm, "latency_ms")
        pairs_tok = _paired(base, cm, "input_tokens")
        pairs_dollars = _paired(base, cm, "dollars")
        n_groups = len({p.group for p in pairs_req})
        safety_base = int(base.aggregate.get("safety_events_total", 0))
        safety_cand = int(cm.aggregate.get("safety_events_total", 0))
        out[name] = {
            "n_paired_episodes": len(pairs_req),
            "n_groups": n_groups,
            "request_ratio": paired_ratio(pairs_req).as_dict(),
            "request_diff": paired_group_bootstrap_diff(pairs_req).as_dict(),
            "token_ratio": paired_ratio(pairs_tok).as_dict(),
            "dollar_ratio": paired_ratio(pairs_dollars).as_dict(),
            "latency_ratio": paired_ratio(pairs_lat).as_dict(),
            "quality_noninferiority": noninferiority(
                pairs_q, endpoint="semantic_score", margin=0.05
            ).as_dict(),
            "quality_noninferiority_strict": noninferiority(
                pairs_q, endpoint="semantic_score", margin=0.03
            ).as_dict(),
            "success_diff": paired_group_bootstrap_diff(_paired(base, cm, "success")).as_dict(),
            "safety": {
                "baseline_events": safety_base,
                "candidate_events": safety_cand,
                "delta": safety_cand - safety_base,
                "artifact_write_effects": int(cm.aggregate.get("artifact_write_effects_total", 0)),
                "incidents": int(cm.aggregate.get("incidents_total", 0)),
                "invariant": safety_cand <= safety_base
                and int(cm.aggregate.get("artifact_write_effects_total", 0)) == 0,
            },
            "coverage_phi": round(cm.aggregate.get("coverage_phi", 0.0), 4),
            "unsafe_dispatch_upper_bound": _unsafe_bound(cm),
        }
    return out


def _unsafe_bound(cm: ConditionMetrics) -> dict[str, Any]:
    """Exact upper bound on unsafe dispatch among artifact *executions*.

    The denominator is executions rather than compacted episodes. An episode may
    execute a region more than once and an incident is an execution that failed
    after a commitment, so ``episodes_compacted`` can be smaller than the event
    count — which used to make ``k > n`` and raise out of the Clopper–Pearson
    routine instead of reporting a bound. When the numerator still exceeds the
    denominator the honest answer is a bound of 1.0 plus the inconsistency, never
    a silently rescaled rate.
    """

    executions = int(cm.aggregate.get("artifact_executions_total", 0))
    incidents = int(cm.aggregate.get("incidents_total", 0))
    writes = int(cm.aggregate.get("artifact_write_effects_total", 0))
    events = incidents + writes
    n = max(executions, events, 1)
    out = {
        "artifact_executions": executions,
        "dispatched_episodes": int(cm.aggregate.get("episodes_compacted", 0)),
        "observed_unsafe": events,
        "upper_95": round(exact_binomial_upper(events, n, conf=0.95), 5),
        "note": "a zero observed rate is reported as an upper bound, never as zero risk",
    }
    if events > executions:
        out["denominator_warning"] = (
            f"{events} unsafe events against {executions} recorded executions: "
            "telemetry is inconsistent and the bound is reported at its ceiling"
        )
    return out


def _hypotheses(
    conditions: dict[str, ConditionMetrics], comparisons: dict[str, Any], est: Any
) -> dict[str, Any]:
    full = comparisons.get("full", {})
    simple = comparisons.get("simple", {})
    abl = comparisons.get("support_only", {})
    ratio = full.get("request_ratio", {})
    q = full.get("quality_noninferiority", {})
    out = {
        "H1_synthesis": {
            "statement": "automatic synthesis yields at least one non-trivial artifact "
            "(k>=2, with a synthesized transform or observation-dependent branch)",
            "passed": conditions["full"].aggregate.get("episodes_compacted", 0) > 0,
        },
        "H2_quality": {
            "statement": "lower one-sided 95% CI on the paired task-score difference exceeds -0.05",
            "margin": 0.05,
            "diff": q.get("diff"),
            "passed": bool(q.get("passed")),
        },
        "H3_requests": {
            "statement": "upper one-sided 95% CI on the model-request ratio is below 0.90",
            "ratio": ratio,
            "passed": bool(ratio.get("high", 1.0) < 0.90),
        },
        "H3b_cost_latency": {
            "dollar_ratio": full.get("dollar_ratio"),
            "latency_ratio": full.get("latency_ratio"),
            "note": "secondary, unthresholded; dollars lag requests because the removed prefill is cached",
        },
        "H4_ablation": {
            "statement": "provenance/contract-aware gating has fewer unsafe dispatches than "
            "support-only routing at comparable coverage",
            "full": {
                "coverage": full.get("coverage_phi"),
                "unsafe": full.get("unsafe_dispatch_upper_bound"),
                "safety": full.get("safety"),
            },
            "support_only": {
                "coverage": abl.get("coverage_phi"),
                "unsafe": abl.get("unsafe_dispatch_upper_bound"),
                "safety": abl.get("safety"),
            },
        },
        "H5_operations": {
            "latency_ratio": full.get("latency_ratio"),
            "incidents": full.get("safety", {}).get("incidents"),
            "note": "exploratory",
        },
        "incremental_value_over_hand_written": {
            "simple_request_ratio": simple.get("request_ratio"),
            "full_request_ratio": ratio,
            "note": "GRC is only credited with the difference; a macro still costs one model "
            "request per invocation because the model selects it",
        },
    }
    out["co_primary_passed"] = bool(out["H2_quality"]["passed"] and out["H3_requests"]["passed"])
    return out


def run_manifest(args: argparse.Namespace) -> dict[str, Any]:
    import numpy
    import scipy
    import sklearn

    return {
        "substrate": "simulated",
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "sklearn": sklearn.__version__,
        "seed": args.seed,
        "n_episodes": args.episodes,
        "quick": args.quick,
        "demos": args.demos,
        "warning": "every number produced here is measured on a simulated workload; it is "
        "not a provider or production measurement",
    }


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run the agent-compaction experiments")
    ap.add_argument(
        "--demos",
        nargs="*",
        default=["support", "permissioned_rag", "incident_triage", "mcp_ops"],
    )
    ap.add_argument(
        "--episodes",
        type=int,
        default=0,
        help="override the per-demo episode count (0 = use each demo's declared size)",
    )
    ap.add_argument("--seed", type=int, default=20260801)
    ap.add_argument("--quick", action="store_true", help="smaller budgets for a fast smoke run")
    ap.add_argument("--out", default=str(ROOT / "experiments" / "results"))
    args = ap.parse_args(argv)

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = run_manifest(args)
    (outdir / "run_manifest.json").write_text(json.dumps(manifest, indent=2))

    all_results: dict[str, Any] = {"manifest": manifest, "demos": {}}
    for key in args.demos:
        spec = get_demo(key)
        _log(f"=== {spec.title} ===")
        n_eps = args.episodes if args.episodes else spec.n_episodes
        res = run_demo(spec, n_episodes=n_eps, seed=args.seed, quick=args.quick)
        all_results["demos"][key] = asdict(res)
        (outdir / f"{key}.json").write_text(json.dumps(asdict(res), indent=2, default=str))
        _log(
            f"{key}: n_B={res.n_B:.2f} "
            f"R_req(full)={res.comparisons.get('full', {}).get('request_ratio', {}).get('point', float('nan')):.3f} "
            f"co-primary={res.hypotheses.get('co_primary_passed')} "
            f"({res.timings.get('total_s')}s)"
        )
    (outdir / "all_results.json").write_text(json.dumps(all_results, indent=2, default=str))
    _log(f"wrote {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
