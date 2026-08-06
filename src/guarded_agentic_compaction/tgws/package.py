"""TGWS orchestrator: fit routes, prune per leaf, calibrate abstention, package.

The output is one artifact per accepted route leaf plus an explicit
default-to-baseline branch. Three guards on the result, all from
execution-plan §8.1:

* rare or uncertain inputs abstain — the calibrated gate bounds the rate at which
  the route is wrong, using the same exact Clopper–Pearson machinery as GRC;
* a leaf is only kept if pruning measured an improvement under quality and safety
  non-inferiority on *dev* groups;
* the leaf set must be a net complexity reduction, or artifact proliferation eats
  the saving (the ``M(A)`` term of §9.1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from ..evaluation.splits import Splits
from ..graph.normalize import qualify_all
from ..grc.calibrate import CalibrationSample, GateFeatures, calibrate_gate, fit_gate_model
from ..grc.program import Predicate
from ..paths import resolve_path, stable_int
from ..schema.artifacts import Artifact, Evidence, GuardClause, HardGuard, Hull, Lifecycle, RouteConfig
from ..schema.effects import EffectCatalog
from ..schema.traces import Episode, ExecutionManifest, require_compatible_manifest
from .prune import EvalResult, LeafConfig, Objective, PruneTrace, prune_leaf
from .routes import RouteLeaf, RouteTree, build_examples, default_route_label, fit_route_tree

__all__ = ["TgwsConfig", "TgwsResult", "compile_tgws"]


@dataclass(slots=True)
class TgwsConfig:
    entry_allowlist: tuple[str, ...] = ()
    partition_by: tuple[str, ...] = ("tenant_partition", "principal", "policy_version")
    max_depth: int = 3
    min_support: int = 20
    min_purity: float = 0.90
    min_groups: int = 10
    max_leaves: int = 4
    max_complexity_multiple: float = 2.0
    objective: Objective = field(default_factory=Objective)
    protected_tools: tuple[str, ...] = ()
    protected_blocks: tuple[str, ...] = ()
    tiers: tuple[str, ...] = ()
    alpha: float = 0.05
    delta: float = 0.10
    phi_min: float = 0.02
    budget_per_leaf: int = 90
    #: Calibration episodes per leaf. Each one costs two workload runs (baseline and
    #: pruned configuration), so this is the dominant cost of TGWS calibration.
    max_dev_episodes: int = 150
    max_calibration_episodes: int = 400
    #: How much measured quality loss counts as a violation. 0.0 means any loss.
    calibration_margin: float = 0.0
    owner: str = "unassigned"
    seed: int = 20260801
    allow_legacy_catalog_version: bool = False


@dataclass(slots=True)
class LeafRecord:
    leaf: RouteLeaf
    stage: str = "routed"
    rejected: str | None = None
    config: LeafConfig | None = None
    baseline_eval: EvalResult | None = None
    pruned_eval: EvalResult | None = None
    trace: PruneTrace | None = None
    artifact: Artifact | None = None
    gate_notes: str = ""
    route_mismatch_rate: float = 0.0


@dataclass(slots=True)
class TgwsResult:
    tree: RouteTree | None = None
    leaves: list[LeafRecord] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    rejection_by_stage: dict[str, int] = field(default_factory=dict)

    def report(self) -> str:
        lines = ["TGWS report", "───────────"]
        if self.tree:
            lines.append(self.tree.report())
        lines.append(f"artifacts emitted {len(self.artifacts)}")
        for rec in self.leaves:
            head = f"  [{rec.stage:10s}] {rec.leaf.pretty()}"
            lines.append(head)
            if rec.rejected:
                lines.append(f"       REJECTED: {rec.rejected}")
            if rec.baseline_eval and rec.pruned_eval:
                b, p = rec.baseline_eval, rec.pruned_eval
                lines.append(
                    f"       requests {b.requests:.2f}→{p.requests:.2f}  "
                    f"in_tokens {b.input_tokens:.0f}→{p.input_tokens:.0f}  "
                    f"quality {b.quality:.4f}→{p.quality:.4f}  "
                    f"latency {b.latency_ms:.0f}→{p.latency_ms:.0f}ms  "
                    f"evals={rec.trace.evaluations if rec.trace else 0}"
                )
            if rec.config:
                lines.append(
                    f"       kept blocks={list(rec.config.prompt_blocks)} tools={list(rec.config.tools)}"
                )
        return "\n".join(lines)

    def explain(self) -> str:
        return "\n\n".join(a.explain() for a in self.artifacts) or "(no artifacts)"


def compile_tgws(
    episodes: Sequence[Episode],
    catalog: EffectCatalog,
    splits: Splits,
    manifest: ExecutionManifest,
    config: TgwsConfig,
    *,
    baseline: LeafConfig,
    evaluate: Callable[[RouteLeaf, Sequence[Episode], LeafConfig], EvalResult],
    label_fn: Callable[[Episode], str] = default_route_label,
) -> TgwsResult:
    """Fit routes and prune per leaf. Partitions are compiled separately.

    Route trees are behavioural evidence about a principal's traffic, so the same
    isolation rule applies as for GRC: a leaf whose support spans two authorization
    scopes has pooled evidence across a boundary §7.4 forbids. Rather than reject such
    leaves after the fact, the corpus is partitioned before fitting.
    """

    manifest = require_compatible_manifest(episodes, manifest)
    if not catalog.matches_version(
        manifest.effect_catalog_version,
        allow_legacy=config.allow_legacy_catalog_version,
    ):
        raise ValueError(
            "the compilation manifest and effect catalog disagree: "
            f"{manifest.effect_catalog_version!r} != {catalog.catalog_version!r}"
        )

    qualified, qualification = qualify_all(episodes, catalog)
    qualification_counts: dict[str, int] = {}
    for result in qualification:
        for reason in result.reasons:
            if reason.startswith("undeclared_tools"):
                continue
            key = f"qualify:{reason.split(':')[0]}"
            qualification_counts[key] = qualification_counts.get(key, 0) + 1
    episodes = qualified
    if not episodes:
        return TgwsResult(rejection_by_stage=qualification_counts)

    keys = tuple(config.partition_by)
    if keys:
        buckets: dict[tuple[str, ...], list[Episode]] = {}
        for ep in episodes:
            buckets.setdefault(
                tuple(str(getattr(ep.envelope, k, "unknown")) for k in keys), []
            ).append(ep)
        if len(buckets) > 1:
            merged = TgwsResult(rejection_by_stage=dict(qualification_counts))
            for pkey, part in sorted(buckets.items()):
                partition_tag = f"{stable_int(pkey, bits=32):08x}"
                sub = compile_tgws(
                    part,
                    catalog,
                    splits,
                    manifest,
                    config,
                    baseline=baseline,
                    evaluate=evaluate,
                    label_fn=label_fn,
                )
                merged.leaves.extend(sub.leaves)
                for art in sub.artifacts:
                    art.artifact_id = f"{art.artifact_id}-{partition_tag}"
                merged.artifacts.extend(sub.artifacts)
                if merged.tree is None:
                    merged.tree = sub.tree
                elif sub.tree is not None:
                    merged.tree.leaves.extend(sub.tree.leaves)
                for k, v in sub.rejection_by_stage.items():
                    merged.rejection_by_stage[k] = merged.rejection_by_stage.get(k, 0) + v
            if len(merged.artifacts) > config.max_leaves:
                merged.rejection_by_stage["select:max_leaves"] = (
                    len(merged.artifacts) - config.max_leaves
                )
                merged.artifacts = merged.artifacts[: config.max_leaves]
            return merged

    res = TgwsResult(rejection_by_stage=dict(qualification_counts))
    train = [ep for ep in episodes if ep.group_id in splits.train]
    dev = [ep for ep in episodes if ep.group_id in splits.dev]
    cal = [ep for ep in episodes if ep.group_id in splits.calibration]

    tree = fit_route_tree(
        train,
        config.entry_allowlist,
        label_fn=label_fn,
        max_depth=config.max_depth,
        min_support=config.min_support,
        min_purity=config.min_purity,
        min_groups=config.min_groups,
    )
    res.tree = tree

    def bump(stage: str) -> None:
        res.rejection_by_stage[stage] = res.rejection_by_stage.get(stage, 0) + 1

    for leaf in tree.leaves:
        rec = LeafRecord(leaf=leaf)
        res.leaves.append(rec)
        if not leaf.stable:
            rec.rejected = f"unstable_route:{leaf.instability}"
            bump("route:unstable")
            continue
        if leaf.purity < config.min_purity or leaf.support < config.min_support:
            rec.rejected = f"low_purity_or_support:{leaf.purity:.2f}/{leaf.support}"
            bump("route:low_purity")
            continue

        dev_leaf = [ep for ep in dev if leaf.matches(_features(ep, config.entry_allowlist))]
        # Declared evaluation budget (execution-plan §8.1 "cap evaluation with a fixed
        # budget"). Pruning re-runs the workload for every proposal, so the dev sample
        # per evaluation is bounded and the bound is reported with the result.
        dev_leaf = dev_leaf[: config.max_dev_episodes]
        if len(dev_leaf) < 10:
            rec.rejected = f"insufficient_dev_episodes:{len(dev_leaf)}"
            bump("prune:no_dev")
            continue

        pruned, pruned_eval, trace = prune_leaf(
            baseline,
            lambda c, _l=leaf, _d=dev_leaf: evaluate(_l, _d, c),
            objective=config.objective,
            protected_tools=config.protected_tools,
            protected_blocks=config.protected_blocks,
            tiers=config.tiers,
            budget=config.budget_per_leaf,
        )
        rec.config = pruned
        rec.trace = trace
        rec.baseline_eval = evaluate(leaf, dev_leaf, baseline)
        rec.pruned_eval = pruned_eval
        rec.stage = "pruned"
        if pruned == baseline:
            rec.rejected = "no_accepted_removal"
            bump("prune:no_removal")
            continue

        # ---- abstention calibration on calibration groups only --------------
        cal_leaf = [ep for ep in cal if leaf.matches(_features(ep, config.entry_allowlist))]
        guard = _leaf_guard(leaf, train, manifest, catalog, config)
        features = GateFeatures.fit(guard, _pseudo_windows(train, leaf, config), branch_entropy=0.0)
        # The violation label is *outcome-based*, not path imitation. A route learned
        # from historical handoffs can reproduce a bad workflow, and the baseline's
        # own choice is noisy; execution-plan §8.1 is explicit that leaves must be
        # compared against task outcomes rather than against path agreement. So each
        # calibration episode is run under both configurations and a violation is a
        # measured degradation, not a disagreement with history.
        gate_training = _outcome_samples(
            dev_leaf,
            leaf,
            baseline,
            pruned,
            features,
            evaluate,
            margin=config.calibration_margin,
        )
        samples = _outcome_samples(
            cal_leaf[: config.max_calibration_episodes],
            leaf,
            baseline,
            pruned,
            features,
            evaluate,
            margin=config.calibration_margin,
        )
        route_mismatch = sum(1 for ep in cal_leaf if label_fn(ep) != leaf.label)
        rec.route_mismatch_rate = route_mismatch / max(1, len(cal_leaf))
        if not samples:
            rec.rejected = "no_calibration_episodes"
            bump("calibrate:no_groups")
            continue
        gate_model, _ = fit_gate_model(gate_training, seed=config.seed)
        gate = calibrate_gate(
            samples,
            features=features,
            model=gate_model,
            alpha=config.alpha,
            delta=config.delta,
            phi_min=config.phi_min,
            seed=config.seed,
        )
        rec.gate_notes = gate.notes[:200]
        rec.stage = "calibrated"
        if gate.retire:
            rec.rejected = "gate_retire:" + gate.notes[:120]
            bump("calibrate:retire")
            continue

        if any("|" in v for v in guard.isolation.values()):
            rec.rejected = "isolation_key_pooled:" + ",".join(
                k for k, v in guard.isolation.items() if "|" in v
            )
            bump("contract:isolation_pooled")
            continue

        route = RouteConfig(
            predicates=tuple(Predicate(f"z.{p}", op, const) for p, op, const in leaf.predicates),
            route_label=leaf.label,
            agent=pruned.agent,
            model=pruned.model,
            reasoning_tier=pruned.reasoning_tier,
            prompt_blocks=pruned.prompt_blocks,
            tools=pruned.tools,
            handoffs=pruned.handoffs,
            support=leaf.support,
            purity=leaf.purity,
            coverage=leaf.coverage,
            prompt_tokens=int(pruned_eval.prompt_tokens),
            schema_tokens=int(pruned_eval.schema_tokens),
            baseline_prompt_tokens=int(rec.baseline_eval.prompt_tokens),
            baseline_schema_tokens=int(rec.baseline_eval.schema_tokens),
        )
        art = Artifact(
            artifact_id=(
                f"tgws-{len(res.artifacts):02d}-"
                f"{stable_int(leaf.predicates, bits=32) % 10**6:06d}"
            ),
            name="route." + (leaf.label.replace("handoff:", "").replace("path:", "")[:28] or "default"),
            kind="tgws",
            version=1,
            route=route,
            guard=guard,
            gate=gate,
            manifest=manifest,
            compatibility_key=manifest.compatibility_key(),
            partition=dict(guard.isolation),
            evidence=Evidence(
                support_groups=leaf.group_support,
                total_groups=len({ep.group_id for ep in train}),
                removed_requests=max(0.0, rec.baseline_eval.requests - pruned_eval.requests),
                split_ids={
                    role: sorted(set(m) & {ep.group_id for ep in episodes})
                    for role, m in splits.roles.items()
                    if set(m) & {ep.group_id for ep in episodes}
                },
                metrics={
                    "baseline": _eval_dict(rec.baseline_eval),
                    "pruned": _eval_dict(pruned_eval),
                    "prune_trace": trace.steps[-24:],
                    "evaluations": trace.evaluations,
                    "dev_episodes_per_evaluation": len(dev_leaf),
                    "route_purity": leaf.purity,
                    "route_mismatch_rate_calibration": round(rec.route_mismatch_rate, 4),
                    "calibration_violations": gate.observed_violations,
                    "gate_training_episodes": len(gate_training),
                    "gate_calibration_episodes": len(samples),
                    "gate_grid": gate.notes[:400],
                },
                dataset_digest=splits.digest(),
            ),
            lifecycle=Lifecycle.REPLAY_VALIDATED,
            owner=config.owner,
            monitoring={"min_route_purity": config.min_purity, "max_route_error": config.alpha},
        )
        rec.artifact = art
        rec.stage = "emitted"
        res.artifacts.append(art)
        if len(res.artifacts) >= config.max_leaves:
            break

    # ---- net complexity check ------------------------------------------------
    total_size = sum(
        len(a.route.prompt_blocks) + len(a.route.tools) + len(a.route.handoffs)
        for a in res.artifacts
        if a.route
    )
    if res.artifacts and total_size > config.max_complexity_multiple * baseline.size:
        res.rejection_by_stage["select:complexity"] = len(res.artifacts)
        res.artifacts = []
        for rec in res.leaves:
            if rec.stage == "emitted":
                rec.stage = "dropped"
                rec.rejected = "leaf_set_exceeds_complexity_budget"
                rec.artifact = None
    return res


def _outcome_samples(
    episodes: Sequence[Episode],
    leaf: RouteLeaf,
    baseline: LeafConfig,
    candidate: LeafConfig,
    features: GateFeatures,
    evaluate: Callable[[RouteLeaf, Sequence[Episode], LeafConfig], EvalResult],
    *,
    margin: float,
) -> list[CalibrationSample]:
    """Measure per-episode candidate regressions for a frozen gate protocol."""

    samples: list[CalibrationSample] = []
    for episode in episodes:
        base_eval = evaluate(leaf, [episode], baseline)
        candidate_eval = evaluate(leaf, [episode], candidate)
        degraded = candidate_eval.quality < base_eval.quality - margin
        success_loss = candidate_eval.success_rate < base_eval.success_rate - margin
        unsafe = candidate_eval.safety_events > base_eval.safety_events
        violation = bool(degraded or success_loss or unsafe)
        samples.append(
            CalibrationSample(
                group=episode.group_id,
                features=features.raw(episode.entry_state, day=episode.envelope.day),
                unproductive=violation,
                violation=violation,
                episode_id=episode.episode_id,
            )
        )
    return samples


def _features(ep: Episode, allowlist: Sequence[str]) -> dict[str, Any]:
    return {p: resolve_path(ep.entry_state, p) for p in allowlist}


def _eval_dict(r: EvalResult) -> dict[str, float]:
    return {
        "quality": round(r.quality, 5),
        "success_rate": round(r.success_rate, 5),
        "requests": round(r.requests, 4),
        "input_tokens": round(r.input_tokens, 1),
        "output_tokens": round(r.output_tokens, 1),
        "latency_ms": round(r.latency_ms, 1),
        "safety_events": r.safety_events,
        "n_episodes": r.n_episodes,
        "prompt_tokens": round(r.prompt_tokens, 1),
        "schema_tokens": round(r.schema_tokens, 1),
    }


def _leaf_guard(
    leaf: RouteLeaf,
    train: Sequence[Episode],
    manifest: ExecutionManifest,
    catalog: EffectCatalog,
    config: TgwsConfig,
) -> HardGuard:
    from ..grc.contracts import fit_hull

    pins = {
        "model": manifest.model,
        "prompt_hash": manifest.prompt_hash,
        "tools_hash": manifest.tools_hash,
        "policy_hash": manifest.policy_hash,
        "guardrail_hash": manifest.guardrail_hash,
        "effect_catalog_version": catalog.catalog_version,
        "entry_contract_version": manifest.entry_contract_version,
    }
    matching = [ep for ep in train if leaf.matches(_features(ep, config.entry_allowlist))]
    isolation: dict[str, str] = {}
    for key in config.partition_by:
        values = {getattr(ep.envelope, key, "unknown") for ep in matching}
        isolation[key] = next(iter(values)) if len(values) == 1 else "|".join(sorted(values))
    clauses: list[GuardClause] = []
    seen_paths: set[str] = set()
    for path, op, const in leaf.predicates:
        if path in seen_paths:
            continue
        seen_paths.add(path)
        values = [resolve_path(ep.entry_state, path) for ep in matching]
        present = [v for v in values if v is not None]
        if not present:
            continue
        clauses.append(
            GuardClause(
                path=f"z.{path}",
                type_name=type(present[0]).__name__ if not isinstance(present[0], bool) else "bool",
                hull=fit_hull(present),
                role="hull",
            )
        )
    return HardGuard(manifest_pins=pins, isolation=isolation, clauses=clauses, allowed_effects=())


def _pseudo_windows(train: Sequence[Episode], leaf: RouteLeaf, config: TgwsConfig) -> list[Any]:
    """Adapter so that :class:`GateFeatures` can be fitted from episodes."""

    class _W:
        __slots__ = ("episode", "day", "group_id")

        def __init__(self, ep: Episode) -> None:
            self.episode = ep
            self.day = ep.envelope.day
            self.group_id = ep.group_id

    return [_W(ep) for ep in train if leaf.matches(_features(ep, config.entry_allowlist))]
