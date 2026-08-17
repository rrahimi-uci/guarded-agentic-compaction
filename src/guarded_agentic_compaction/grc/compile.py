"""GRC orchestrator: mine → synthesize → contract → challenge → calibrate → emit.

This is the ladder of proposal §4 run end to end for one snapshot, with every
rejection recorded by stage so that "nothing here is compilable" is a first-class,
reportable result rather than an empty list.

Stage order and the reason for it:

1. ``mine`` — cheap, and its blocked-window counters are what the estimator reports.
2. ``synthesize`` — bindings and branches; most families die here, correctly.
3. ``contract`` — guard and verifier fitted on train groups only.
4. ``challenge`` — grouped dev replay plus the perturbation suite.
5. ``calibrate`` — gate threshold on calibration groups only, never on dev or test.
6. ``emit`` — an immutable artifact carrying its evidence.

A candidate may never be calibrated on the data used to synthesize it, and the
sealed test is not touched anywhere in this module (execution-plan §10.5).
The gate's exact confidence budget is per fixed candidate. This orchestrator may
calibrate several families on the same calibration groups, so its candidate search does
not currently carry a compiler-wide familywise guarantee; publication claims must retain
that distinction unless a candidate-level multiplicity procedure is added.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from ..evaluation.perturb import DEFAULT_PERTURBATIONS, Perturbation
from ..evaluation.splits import Splits
from ..graph.provenance import GroundabilityPolicy, PATG, build_all
from ..graph.normalize import qualify_all
from ..graph.windows import Family, MiningResult, Window, mine
from ..schema.artifacts import Artifact, Evidence, Gate, Lifecycle
from ..schema.effects import EffectCatalog
from ..schema.traces import (
    Episode,
    ExecutionManifest,
    manifest_partitions,
    require_compatible_manifest,
)
from ..paths import stable_int
from .calibrate import CalibrationSample, GateFeatures, calibrate_gate, fit_gate_model
from .contracts import ChallengeReport, challenge, induce_guard, induce_verifier
from .composite import CompositeSynthesisError, synthesize_composite
from .program import Program
from .synthesize import SynthesisResult, synthesize_program, var_name_for, window_env

__all__ = ["GrcConfig", "CandidateRecord", "CompileResult", "compile_grc", "compile_grc_batch"]


@dataclass(slots=True)
class GrcConfig:
    """Every knob the API must expose (execution-plan §14 "known gaps")."""

    entry_schema: tuple[str, ...] = ()
    partition_by: tuple[str, ...] = ("tenant_partition", "principal", "policy_version")
    w_min: int = 2
    w_max: int = 8
    b_min: int = 2
    s_min: int = 5
    min_principals: int = 1
    min_days: int = 3
    #: The shipped runners resolve artifacts only at the initial model boundary.
    #: Until runtime state includes a verified region-position key, compiling a
    #: suffix would execute it too early and can reorder/duplicate tool calls.
    prefix_only: bool = True
    max_transform_depth: int = 2
    kappa: int = 3
    s_branch: int = 20
    n_permutations: int = 400
    alpha: float = 0.05
    delta: float = 0.10
    phi_min: float = 0.02
    #: Freeze the highest-ranked candidate that survives synthesis and challenge
    #: before touching calibration groups. This avoids calibrating several families
    #: on the same holdout split at the cost of lower coverage. The published paper
    #: keeps this off and reports the weaker per-candidate certificate explicitly.
    freeze_one_candidate_before_calibration: bool = False
    max_artifacts: int = 8
    max_candidates: int = 24
    #: Declared evaluation budgets. Replay and calibration cost one program execution
    #: per window, so both are bounded and the bound is reported with the evidence
    #: (execution-plan §8.1 "cap evaluation with a fixed budget").
    max_dev_windows: int = 400
    max_calibration_windows: int = 700
    mode: str = "offline"  # offline | replay | shadow | live
    owner: str = "unassigned"
    seed: int = 20260801
    allow_legacy_catalog_version: bool = False
    #: Package an eligible verified program behind one projected interface. Tools
    #: must explicitly declare the ``batchable`` capability; otherwise ordinary
    #: GRC remains available and the ineligibility is recorded on the candidate.
    synthesize_composites: bool = True
    composite_projection: dict[str, str] = field(default_factory=dict)
    composite_pre_model: bool = True
    composite_continuation_key: str = ""

    def digest(self) -> str:
        blob = repr(sorted(self.__dict__.items() if hasattr(self, "__dict__") else []))
        if not blob or blob == "[]":
            blob = "|".join(f"{f}={getattr(self, f)}" for f in self.__slots__)  # type: ignore[attr-defined]
        return hashlib.sha256(blob.encode()).hexdigest()[:12]


@dataclass(slots=True)
class CandidateRecord:
    """What happened to one candidate family, at whichever stage it died."""

    candidate_id: str
    tools: tuple[str, ...]
    support_groups: int
    support_days: int
    removed_requests: float
    stage: str = "mined"
    rejected: str | None = None
    artifact: Artifact | None = None
    synthesis: SynthesisResult | None = None
    challenge: ChallengeReport | None = None
    gate: Gate | None = None
    notes: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "tools": list(self.tools),
            "support_groups": self.support_groups,
            "support_days": self.support_days,
            "removed_requests": self.removed_requests,
            "stage": self.stage,
            "rejected": self.rejected,
            "artifact": self.artifact.name if self.artifact else None,
            "notes": self.notes,
        }


@dataclass(slots=True)
class CompileResult:
    artifacts: list[Artifact] = field(default_factory=list)
    candidates: list[CandidateRecord] = field(default_factory=list)
    mining: MiningResult | None = None
    graphs: list[PATG] = field(default_factory=list)
    policy: GroundabilityPolicy | None = None
    rejection_by_stage: Counter = field(default_factory=Counter)
    config: GrcConfig | None = None

    def report(self) -> str:
        lines = [
            "GRC compile report",
            "──────────────────",
            f"candidates mined        {len(self.candidates)}",
            f"artifacts emitted       {len(self.artifacts)}",
            f"rejections by stage     {dict(self.rejection_by_stage)}",
        ]
        if self.mining:
            lines.append(f"windows accepted        {self.mining.n_windows}")
            lines.append(f"windows blocked         {dict(self.mining.blocked)}")
            lines.append(f"blocked by tool         {dict(self.mining.blocked_by_tool)}")
        for c in self.candidates:
            head = f"  [{c.stage:12s}] {'/'.join(t.split('.')[-1] for t in c.tools)}"
            tail = f"supp={c.support_groups} k={c.removed_requests:.1f}"
            if c.rejected:
                tail += f"  REJECTED: {c.rejected}"
            lines.append(f"{head:66s} {tail}")
        return "\n".join(lines)

    def explain(self) -> str:
        return "\n\n".join(a.explain() for a in self.artifacts) or "(no artifacts)"


def partition_key(episode: Episode, keys: Sequence[str]) -> tuple[str, ...]:
    return tuple(str(getattr(episode.envelope, k, "unknown")) for k in keys)


def compile_grc(
    episodes: Sequence[Episode],
    catalog: EffectCatalog,
    splits: Splits,
    manifest: ExecutionManifest,
    config: GrcConfig,
    *,
    sandbox: Callable[[], Any] | None = None,
    perturbations: Sequence[Perturbation] = DEFAULT_PERTURBATIONS,
    graphs: Sequence[PATG] | None = None,
    policy: GroundabilityPolicy | None = None,
) -> CompileResult:
    """Compile one snapshot. Partitions are compiled *separately*, never pooled.

    ``partition_by`` is the first-class partition key the published API lacked
    (proposal §6.5): tenant, principal and policy version are exact guard keys, so a
    registry built from one partition's traces is never valid in another. Pooling
    them would let a single artifact draw support across an isolation boundary,
    which §7.4 forbids outright.
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
    qualification_counts: Counter = Counter()
    for result in qualification:
        for reason in result.reasons:
            if reason.startswith("undeclared_tools"):
                continue
            qualification_counts[f"qualify:{reason.split(':')[0]}"] += 1
    if len(qualified) != len(episodes):
        episodes = qualified
        # Pre-built graphs and corpus statistics may contain rejected rows. Rebuild
        # them from the qualified corpus rather than leaking malformed evidence.
        graphs = None
        policy = None
    if not episodes:
        return CompileResult(rejection_by_stage=qualification_counts, config=config)

    keys = tuple(config.partition_by)
    if keys:
        groups: dict[tuple[str, ...], list[Episode]] = {}
        for ep in episodes:
            groups.setdefault(partition_key(ep, keys), []).append(ep)
        if len(groups) > 1:
            merged = CompileResult(config=config, rejection_by_stage=qualification_counts)
            for pkey, part in sorted(groups.items()):
                partition_tag = f"{stable_int(pkey, bits=32):08x}"
                sub = compile_grc(
                    part,
                    catalog,
                    splits,
                    manifest,
                    config,
                    sandbox=sandbox,
                    perturbations=perturbations,
                    graphs=None,
                    policy=None,
                )
                for rec in sub.candidates:
                    rec.notes["partition"] = dict(zip(keys, pkey))
                    rec.candidate_id = f"{rec.candidate_id}-{partition_tag}"
                    if rec.artifact is not None:
                        rec.artifact.artifact_id = rec.candidate_id
                merged.artifacts.extend(sub.artifacts)
                merged.candidates.extend(sub.candidates)
                for k, v in sub.rejection_by_stage.items():
                    merged.rejection_by_stage[k] += v
                if merged.mining is None:
                    merged.mining = sub.mining
                elif sub.mining is not None:
                    merged.mining.n_windows += sub.mining.n_windows
                    merged.mining.blocked += sub.mining.blocked
                    merged.mining.blocked_by_tool += sub.mining.blocked_by_tool
                merged.graphs.extend(sub.graphs)
                merged.policy = merged.policy or sub.policy
            merged.artifacts, dropped = _select_artifacts(merged.artifacts)
            if len(merged.artifacts) > config.max_artifacts:
                dropped.extend(a.name for a in merged.artifacts[config.max_artifacts :])
                merged.artifacts = merged.artifacts[: config.max_artifacts]
            for _ in dropped:
                merged.rejection_by_stage["select:dominated"] += 1
            return merged

    res = CompileResult(config=config, rejection_by_stage=qualification_counts)

    train_episodes = [ep for ep in episodes if ep.group_id in splits.train]
    if not train_episodes:
        res.rejection_by_stage["split:no_train_groups"] += 1
        return res

    # Candidate identity, provenance policy, support, and ranking are train-only.
    # A graph or corpus-derived policy fitted on calibration/test inputs would make
    # the candidate data-dependent and invalidate the fixed-candidate premise of
    # the exact calibration theorem. PATGs do not carry fit-lineage metadata, so
    # this correctness-critical path rebuilds them even if a caller supplied a
    # precomputed all-snapshot cache through the backwards-compatible arguments.
    train_graphs, policy = build_all(
        train_episodes,
        catalog,
        None,
        max_depth=config.max_transform_depth,
        kappa=config.kappa,
    )

    calibration_visible = set(splits.dev) | set(splits.calibration)
    heldin_episodes = [ep for ep in episodes if ep.group_id in calibration_visible]
    heldin_graphs, _ = build_all(
        heldin_episodes,
        catalog,
        policy,
        max_depth=config.max_transform_depth,
        kappa=config.kappa,
    )
    usable_graphs = list(train_graphs) + list(heldin_graphs)
    res.graphs = usable_graphs
    res.policy = policy

    mining = mine(
        train_graphs,
        catalog,
        entry_schema=config.entry_schema,
        w_min=config.w_min,
        w_max=config.w_max,
        b_min=config.b_min,
        s_min=config.s_min,
        min_principals=config.min_principals,
        min_days=config.min_days,
        prefix_only=config.prefix_only,
    )
    res.mining = mining
    for _, reason in mining.rejected_families:
        res.rejection_by_stage[f"mine:{reason.split(':')[0]}"] += 1

    # Attach dev/calibration windows only after train mining has fixed the ranked
    # family list. The sealed test and prospective shadow sets are never graphed.
    attached = mine(
        usable_graphs,
        catalog,
        entry_schema=config.entry_schema,
        w_min=config.w_min,
        w_max=config.w_max,
        b_min=config.b_min,
        s_min=1,
        min_principals=1,
        min_days=1,
        prefix_only=config.prefix_only,
    )
    attached_by_hash = {family.canon_hash: family for family in attached.families}

    frozen_precalibration_selected = False

    for idx, train_family in enumerate(mining.families[: config.max_candidates]):
        family = attached_by_hash.get(train_family.canon_hash, train_family)
        cid = f"cand-{idx:02d}-{train_family.canon_hash}"
        rec = CandidateRecord(
            candidate_id=cid,
            tools=train_family.tools,
            support_groups=train_family.support,
            support_days=len(train_family.days),
            removed_requests=train_family.mean_removed,
        )
        res.candidates.append(rec)

        train_w = [w for w in family.windows if w.group_id in splits.train]
        dev_w = [w for w in family.windows if w.group_id in splits.dev][: config.max_dev_windows]
        cal_w = [w for w in family.windows if w.group_id in splits.calibration][
            : config.max_calibration_windows
        ]

        if len({w.group_id for w in train_w}) < config.s_min:
            rec.stage = "mined"
            rec.rejected = f"train_support:{len({w.group_id for w in train_w})}<{config.s_min}"
            res.rejection_by_stage["synthesize:train_support"] += 1
            continue

        synth = synthesize_program(
            family,
            train_w,
            catalog,
            policy,
            max_depth=config.max_transform_depth,
            s_branch=config.s_branch,
            n_permutations=config.n_permutations,
        )
        rec.synthesis = synth
        rec.notes.update(synth.stats)
        if not synth.ok:
            rec.stage = "synthesized"
            rec.rejected = synth.reason
            res.rejection_by_stage["synthesize:" + synth.reason.split(":")[0]] += 1
            continue

        program = synth.program
        names = list(synth.names)
        if program.removed_requests < config.b_min:
            rec.stage = "synthesized"
            rec.rejected = f"k_below_b_min:{program.removed_requests}"
            res.rejection_by_stage["synthesize:k_below_b_min"] += 1
            continue

        if config.synthesize_composites:
            try:
                program = synthesize_composite(
                    program,
                    catalog,
                    projection=config.composite_projection or None,
                    pre_model=config.composite_pre_model,
                    continuation_compatibility_key=config.composite_continuation_key,
                )
            except CompositeSynthesisError as exc:
                # Composite packaging is an optimization above ordinary GRC, not
                # permission to discard a sound compiled program.
                rec.notes["composite"] = f"ineligible:{exc}"
            else:
                rec.notes["composite"] = "synthesized"
                rec.notes["composite_name"] = program.composite.name if program.composite else ""

        guard = induce_guard(program, train_w, manifest, catalog, partition_by=config.partition_by)
        verifier = induce_verifier(program, train_w, names, catalog)
        rec.stage = "contracted"

        if any("|" in v for v in guard.isolation.values()):
            rec.rejected = "isolation_key_pooled:" + ",".join(
                k for k, v in guard.isolation.items() if "|" in v
            )
            res.rejection_by_stage["contract:isolation_pooled"] += 1
            continue

        if not dev_w:
            rec.rejected = "no_dev_groups"
            res.rejection_by_stage["challenge:no_dev_groups"] += 1
            continue

        chal = challenge(
            program,
            guard,
            verifier,
            dev_w,
            names,
            catalog,
            sandbox=sandbox,
            perturbations=perturbations,
        )
        rec.challenge = chal
        rec.stage = "replay_validated"
        if not chal.ok:
            rec.rejected = "challenge_failed:" + (
                chal.hard_rejects[0]["kind"] if chal.hard_rejects else _first_replay_reason(chal)
            )
            res.rejection_by_stage["challenge:hard_reject"] += 1
            continue

        if config.freeze_one_candidate_before_calibration:
            frozen_precalibration_selected = True
            rec.notes["candidate_selection"] = "frozen_before_calibration"

        # ---- calibration (calibration groups only) -------------------------
        features = GateFeatures.fit(
            guard,
            train_w,
            provenance_ambiguity=min(1.0, rec.notes.get("n_alternative_bindings", 0) / 50.0),
            branch_entropy=train_family.branch_entropy(),
        )
        dev_samples = _calibration_samples(
            program,
            guard,
            verifier,
            dev_w,
            names,
            catalog,
            features,
            sandbox,
            include_perturbations=True,
        )
        samples = _calibration_samples(
            program,
            guard,
            verifier,
            cal_w,
            names,
            catalog,
            features,
            sandbox,
            include_perturbations=False,
        )
        rec.notes.update(
            {
                "gate_dev_samples": len(dev_samples),
                "gate_dev_unproductive": sum(sample.unproductive for sample in dev_samples),
                "gate_dev_violations": sum(sample.violation for sample in dev_samples),
                "gate_calibration_samples": len(samples),
                "gate_calibration_unproductive": sum(sample.unproductive for sample in samples),
                "gate_calibration_violations": sum(sample.violation for sample in samples),
                "gate_dev_reasons": dict(
                    Counter(sample.reason for sample in dev_samples if sample.reason)
                ),
                "gate_calibration_reasons": dict(
                    Counter(sample.reason for sample in samples if sample.reason)
                ),
            }
        )
        if not dev_samples:
            rec.rejected = "no_gate_training_groups"
            res.rejection_by_stage["calibrate:no_training_groups"] += 1
            if config.freeze_one_candidate_before_calibration:
                break
            continue
        if not samples:
            rec.rejected = "no_calibration_groups"
            res.rejection_by_stage["calibrate:no_groups"] += 1
            if config.freeze_one_candidate_before_calibration:
                break
            continue
        gate_model, _ = fit_gate_model(dev_samples, seed=config.seed)
        gate = calibrate_gate(
            samples,
            features=features,
            model=gate_model,
            alpha=config.alpha,
            delta=config.delta,
            phi_min=config.phi_min,
            seed=config.seed,
        )
        rec.gate = gate
        rec.stage = "calibrated"
        if gate.retire:
            rec.rejected = "gate_retire:" + gate.notes[:120]
            res.rejection_by_stage["calibrate:retire"] += 1
            if config.freeze_one_candidate_before_calibration:
                break
            continue

        artifact = _emit(
            train_family,
            program,
            names,
            guard,
            verifier,
            gate,
            manifest,
            catalog,
            chal,
            rec,
            splits,
            config,
            partition_groups={ep.group_id for ep in episodes},
        )
        rec.artifact = artifact
        rec.stage = "emitted"
        res.artifacts.append(artifact)
        if (
            len(res.artifacts) >= config.max_artifacts
            or (
                config.freeze_one_candidate_before_calibration
                and frozen_precalibration_selected
            )
        ):
            break

    res.artifacts, dropped = _select_artifacts(res.artifacts)
    for name in dropped:
        res.rejection_by_stage["select:dominated"] += 1
        for c in res.candidates:
            if c.artifact is not None and c.artifact.name == name:
                c.stage = "dominated"
                c.rejected = "dominated_by_longer_region"
                c.artifact = None
    return res


def compile_grc_batch(
    episodes: Sequence[Episode],
    catalog: EffectCatalog,
    splits: Splits,
    config: GrcConfig,
    *,
    sandbox: Callable[[], Any] | None = None,
    perturbations: Sequence[Perturbation] = DEFAULT_PERTURBATIONS,
) -> dict[str, CompileResult]:
    """Compile every workflow version independently.

    Rolling deployments commonly produce snapshots containing several manifests.
    A separate result per compatibility key prevents support and calibration evidence
    from crossing versions while allowing all resulting artifacts to share a registry.
    """

    results: dict[str, CompileResult] = {}
    for key, partition in sorted(manifest_partitions(episodes).items()):
        result = compile_grc(
            partition,
            catalog,
            splits,
            partition[0].manifest,
            config,
            sandbox=sandbox,
            perturbations=perturbations,
        )
        tag = key[:8]
        for record in result.candidates:
            record.candidate_id = f"{record.candidate_id}-{tag}"
            if record.artifact is not None:
                record.artifact.artifact_id = record.candidate_id
        results[key] = result
    return results


def _select_artifacts(artifacts: Sequence[Artifact]) -> tuple[list[Artifact], list[str]]:
    """Keep a non-overlapping, maximal set.

    Two artifacts whose tool sequences are in a prefix relation fire on the same
    episodes; keeping both multiplies the maintenance surface (the ``M(A)`` term of
    execution-plan §9.1) without adding coverage. The longer region wins because it
    removes more requests; ties break on support then on name for determinism.
    """

    order = sorted(
        artifacts,
        key=lambda a: (
            -(a.program.removed_requests if a.program else 0),
            -a.evidence.support_groups,
            a.name,
        ),
    )
    kept: list[Artifact] = []
    dropped: list[str] = []
    for art in order:
        seq = tuple(art.program.tools) if art.program else ()
        dominated = False
        for other in kept:
            oseq = tuple(other.program.tools) if other.program else ()
            if seq == oseq[: len(seq)] or oseq == seq[: len(oseq)]:
                if art.partition == other.partition:
                    dominated = True
                    break
        if dominated:
            dropped.append(art.name)
        else:
            kept.append(art)
    return kept, dropped


def _first_replay_reason(chal: ChallengeReport) -> str:
    for rep in (chal.recorded, chal.sandbox):
        if rep.reasons:
            return next(iter(rep.reasons))
    return "unknown"


def _calibration_guard_context(guard, episode: Episode, catalog: EffectCatalog) -> dict[str, Any]:
    manifest = episode.manifest
    context = {
        key: (
            catalog.catalog_version
            if key == "effect_catalog_version"
            else getattr(manifest, key, None)
        )
        for key in guard.manifest_pins
    }
    context.update(
        {key: getattr(episode.envelope, key, "unknown") for key in guard.isolation}
    )
    return context


def _calibration_samples(
    program: Program,
    guard,
    verifier,
    cal_windows: Sequence[Window],
    names: Sequence[str],
    catalog: EffectCatalog,
    features: GateFeatures,
    sandbox: Callable[[], Any] | None,
    *,
    include_perturbations: bool,
) -> list[CalibrationSample]:
    """Label held-out groups by what a dispatch would actually have done.

    Development labels may include hostile perturbations to train a useful risk
    score.  Threshold calibration uses only the clean calibration distribution so
    its exact group-level risk statement applies to the runtime population rather
    than to a synthetic mixture chosen by the implementation.
    """

    from ..evaluation.perturb import DEFAULT_PERTURBATIONS, _make_facade, _semantic_signature
    from ..runtime.interp import run_program

    samples: list[CalibrationSample] = []
    for w in cal_windows:
        guard_context = _calibration_guard_context(guard, w.episode, catalog)
        eligible = not guard.evaluate(w.episode.entry_state, guard_context)
        facade, _ = _make_facade(program, catalog, w, None, sandbox)
        res = run_program(program, w.episode.entry_state, facade)
        unproductive = not res.ok
        reason = res.error.split(":", 1)[0] if not res.ok else ""
        violation = False
        if res.ok:
            bad = verifier.verify(res.outputs, res.env, res.provenance, res.effects, len(res.calls))
            if bad:
                unproductive = True
                reason = "verifier:" + bad[0]
            else:
                for i in range(min(len(names), len(w.steps))):
                    recorded = _recorded_output(w, i)
                    got = res.outputs.get(names[i])
                    if recorded is None and got is None:
                        continue
                    if recorded is None or got is None:
                        violation = True
                        unproductive = True
                        reason = "recorded_output_missing"
                        break
                    if recorded is not None and got is not None:
                        from ..evaluation.replay import equivalent

                        tool = w.steps[i].tool
                        if not equivalent(recorded, got, tool, catalog):
                            violation = True
                            unproductive = True
                            reason = "recorded_output_mismatch"
                            break
        samples.append(
            CalibrationSample(
                group=w.group_id,
                features=features.raw(w.episode.entry_state, day=w.day),
                unproductive=unproductive,
                violation=violation,
                eligible=eligible,
                episode_id=w.episode.episode_id,
                reason=reason,
            )
        )

        if not include_perturbations:
            continue

        # One hostile development variant per window helps train the risk score.
        pert = DEFAULT_PERTURBATIONS[len(samples) % len(DEFAULT_PERTURBATIONS)]
        pfacade, _ = _make_facade(program, catalog, w, pert, sandbox)
        try:
            pres = run_program(program, w.episode.entry_state, pfacade)
        except Exception:
            pres = None
        if pres is not None:
            p_unproductive = not pres.ok
            p_violation = False
            if pres.ok:
                bad = verifier.verify(
                    pres.outputs, pres.env, pres.provenance, pres.effects, len(pres.calls)
                )
                if bad:
                    p_unproductive = True
                elif pert.expect == "invariant":
                    ref_facade, _ = _make_facade(program, catalog, w, None, sandbox)
                    ref = run_program(program, w.episode.entry_state, ref_facade)
                    if ref.ok and _semantic_signature(pres, program, catalog) != _semantic_signature(
                        ref, program, catalog
                    ):
                        p_violation = True
                        p_unproductive = True
            feats = dict(features.raw(w.episode.entry_state, day=w.day))
            feats["provenance_ambiguity"] = min(1.0, feats.get("provenance_ambiguity", 0.0) + 0.5)
            feats["hull_margin"] = min(1.0, feats.get("hull_margin", 0.0) + 0.5)
            samples.append(
                CalibrationSample(
                    group=w.group_id,
                    features=feats,
                    unproductive=p_unproductive,
                    violation=p_violation,
                    eligible=eligible,
                    episode_id=w.episode.episode_id + f"#{pert.name}",
                    reason=("perturbation_unproductive" if p_unproductive else ""),
                )
            )
    return samples


def _recorded_output(w: Window, i: int) -> Any:
    step = w.steps[i]
    if not step.result_positions:
        return None
    return w.patg.order[step.result_positions[-1]].output


def _emit(
    family: Family,
    program: Program,
    names: Sequence[str],
    guard,
    verifier,
    gate: Gate,
    manifest: ExecutionManifest,
    catalog: EffectCatalog,
    chal: ChallengeReport,
    rec: CandidateRecord,
    splits: Splits,
    config: GrcConfig,
    partition_groups: set[str],
) -> Artifact:
    tag = family.canon_hash.replace("merge:", "br-")[:8]
    name = ".".join(t.split(".")[-1] for t in program.tools[:2]) + f".region@{tag}"
    train_support = len(family.groups & set(splits.train))
    evidence = Evidence(
        support_groups=train_support,
        total_groups=len(set(splits.train) & partition_groups),
        support_principals=len(family.principals),
        support_days=len(family.days),
        removed_requests=program.removed_requests,
        split_ids={
            role: sorted(set(members) & partition_groups)
            for role, members in splits.roles.items()
            if set(members) & partition_groups
        },
        replay=chal.recorded.as_dict(),
        perturbation=chal.perturbation,
        counterexamples=list(chal.recorded.counterexamples[:8]) + list(chal.hard_rejects[:8]),
        metrics={
            "sandbox": chal.sandbox.as_dict(),
            "perturbations_claimed": chal.perturbations_claimed,
            "branch": rec.notes.get("branch"),
            "branch_permutation_p": rec.notes.get("branch_p"),
            "branch_alternatives": rec.notes.get("branch_alternatives"),
            "n_alternative_bindings": rec.notes.get("n_alternative_bindings"),
            "composite": rec.notes.get("composite", "disabled"),
            "composite_name": rec.notes.get("composite_name", ""),
            "gate_grid": gate.notes[:400],
            "var_names": list(names),
            "dev_windows_evaluated": len(chal.recorded.as_dict().get("n", 0) or 0) if False else chal.recorded.n,
            "calibration_windows_evaluated": gate.n_calibration_groups,
        },
        dataset_digest=splits.digest(),
        notes="substrate and evidence are recorded in the run manifest",
    )
    return Artifact(
        artifact_id=rec.candidate_id,
        name=name,
        kind="grc",
        version=1,
        program=program,
        guard=guard,
        verifier=verifier,
        gate=gate,
        manifest=manifest,
        compatibility_key=manifest.compatibility_key(),
        partition=dict(guard.isolation),
        evidence=evidence,
        lifecycle=Lifecycle.REPLAY_VALIDATED,
        owner=config.owner,
        monitoring={
            "min_verifier_pass_rate": 0.90,
            "max_unsafe_dispatch": config.alpha,
            "expected_coverage": gate.coverage,
        },
    )
