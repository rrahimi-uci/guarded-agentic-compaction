"""Public API — three calls to value: capture, estimate/compile, deploy.

::

    import agent_compaction as ac

    episodes = ac.read_jsonl("traces.jsonl")
    catalog = ac.load_catalog("configs/effects.yaml")

    report = ac.estimate(episodes, catalog, entry_schema=[...])
    job    = ac.optimize(episodes, catalog, algorithms=["tgws", "grc"],
                         partition_by=["tenant_partition", "principal"], mode="offline")
    ac.validate(job, suites=["replay", "perturbation"])
    ac.promote(job, stage="shadow", approved_by="reviewer@example")

Every control the published examples left implicit is an explicit argument here
(proposal §6.5, execution-plan §14): ``partition_by``, ``mode``, allowed effects,
literal-only fields (from the catalog), maximum transform depth, and the terminal
handoff rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

from .evaluation.perturb import DEFAULT_PERTURBATIONS, Perturbation
from .evaluation.splits import Splits, make_splits
from .estimate.headroom import EstimateReport, estimate as _estimate
from .grc.compile import CompileResult, GrcConfig, compile_grc
from .registry.lifecycle import promote as _promote, retire as _retire
from .registry.store import Registry
from .schema.artifacts import Artifact, Lifecycle
from .schema.effects import EffectCatalog
from .schema.traces import Episode, ExecutionManifest, require_compatible_manifest
from .tgws.package import TgwsConfig, TgwsResult, compile_tgws
from .tgws.prune import LeafConfig

__all__ = [
    "OptimizeJob",
    "estimate",
    "optimize",
    "validate",
    "promote",
    "retire",
    "load_catalog",
    "MODES",
]

#: Execution modes. Only ``offline`` and ``replay`` touch no live dependency.
MODES = ("offline", "replay", "shadow", "live")


def load_catalog(path: str | Path) -> EffectCatalog:
    return EffectCatalog.from_yaml(path)


def estimate(
    episodes: Sequence[Episode],
    catalog: EffectCatalog,
    *,
    entry_schema: Sequence[str] = (),
    target_delta: float = 0.10,
    **kwargs: Any,
) -> EstimateReport:
    """Evaluate Eq. (10) on existing traces. Run this before building anything."""

    return _estimate(episodes, catalog, entry_schema=entry_schema, target_delta=target_delta, **kwargs)


@dataclass(slots=True)
class OptimizeJob:
    """The result of one optimization run: artifacts plus every rejection."""

    job_id: str
    mode: str
    splits: Splits
    grc: CompileResult | None = None
    tgws: TgwsResult | None = None
    registry: Registry | None = None
    validation: dict[str, Any] = field(default_factory=dict)

    @property
    def artifacts(self) -> list[Artifact]:
        out: list[Artifact] = []
        if self.tgws is not None:
            out.extend(self.tgws.artifacts)
        if self.grc is not None:
            out.extend(self.grc.artifacts)
        return out

    @property
    def candidate_id(self) -> str:
        return self.job_id

    def report(self) -> str:
        parts = [f"optimization job {self.job_id} (mode={self.mode})"]
        if self.tgws is not None:
            parts.append(self.tgws.report())
        if self.grc is not None:
            parts.append(self.grc.report())
        return "\n\n".join(parts)

    def explain(self) -> str:
        return "\n\n".join(a.explain() for a in self.artifacts) or "(no artifacts)"

    def save(self, path: str | Path, *, signing_key: bytes = b"") -> Path:
        reg = self.registry or Registry(name=self.job_id, signing_key=signing_key)
        if self.registry is None:
            reg.extend(self.artifacts)
            self.registry = reg
        elif signing_key:
            if reg.signing_key and reg.signing_key != signing_key:
                raise ValueError("registry is already configured with a different signing key")
            reg.signing_key = signing_key
        return reg.save(path)


def optimize(
    episodes: Sequence[Episode],
    catalog: EffectCatalog,
    *,
    manifest: ExecutionManifest | None = None,
    algorithms: Sequence[str] = ("tgws", "grc"),
    mode: str = "offline",
    partition_by: Sequence[str] = ("tenant_partition", "principal", "policy_version"),
    entry_schema: Sequence[str] = (),
    splits: Splits | None = None,
    max_transform_depth: int = 2,
    kappa: int = 3,
    alpha: float = 0.05,
    delta: float = 0.10,
    phi_min: float = 0.02,
    s_min: int = 5,
    s_branch: int = 20,
    min_days: int = 3,
    sandbox: Callable[[], Any] | None = None,
    perturbations: Sequence[Perturbation] = DEFAULT_PERTURBATIONS,
    tgws_baseline: LeafConfig | None = None,
    tgws_evaluate: Callable[..., Any] | None = None,
    route_label: Callable[[Episode], str] | None = None,
    synthesize_composites: bool = True,
    composite_projection: dict[str, str] | None = None,
    composite_pre_model: bool = True,
    composite_continuation_key: str = "",
    owner: str = "unassigned",
    seed: int = 20260801,
    job_id: str = "job-1",
) -> OptimizeJob:
    """Run the ladder: specialise routing first, then compile residual regions.

    The order is not cosmetic. Prompt/tool specialisation is cheaper, safer and often
    captures the same benefit, so GRC only ever sees what TGWS left behind
    (execution-plan §7 "apply transformations in risk order").
    """

    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    if not episodes:
        raise ValueError("no episodes to optimize")
    unknown = sorted(set(algorithms) - {"tgws", "grc"})
    if unknown:
        raise ValueError(f"unknown optimization algorithms: {unknown}")
    if not algorithms:
        raise ValueError("at least one optimization algorithm is required")
    manifest = require_compatible_manifest(episodes, manifest)
    if not catalog.matches_version(manifest.effect_catalog_version):
        raise ValueError(
            "the optimization manifest and effect catalog disagree: "
            f"{manifest.effect_catalog_version!r} != {catalog.catalog_version!r}"
        )
    splits = splits or make_splits(episodes, seed=seed)

    job = OptimizeJob(job_id=job_id, mode=mode, splits=splits)

    if "tgws" in algorithms:
        if tgws_baseline is None or tgws_evaluate is None:
            raise ValueError(
                "tgws requires `tgws_baseline` and `tgws_evaluate`: pruning is only "
                "accepted on measured, not estimated, quality"
            )
        job.tgws = compile_tgws(
            episodes,
            catalog,
            splits,
            manifest,
            TgwsConfig(
                entry_allowlist=tuple(entry_schema),
                partition_by=tuple(partition_by),
                alpha=alpha,
                delta=delta,
                phi_min=phi_min,
                owner=owner,
                seed=seed,
            ),
            baseline=tgws_baseline,
            evaluate=tgws_evaluate,
            **({"label_fn": route_label} if route_label else {}),
        )

    if "grc" in algorithms:
        job.grc = compile_grc(
            episodes,
            catalog,
            splits,
            manifest,
            GrcConfig(
                entry_schema=tuple(entry_schema),
                partition_by=tuple(partition_by),
                max_transform_depth=max_transform_depth,
                kappa=kappa,
                alpha=alpha,
                delta=delta,
                phi_min=phi_min,
                s_min=s_min,
                s_branch=s_branch,
                min_days=min_days,
                mode=mode,
                owner=owner,
                seed=seed,
                synthesize_composites=synthesize_composites,
                composite_projection=dict(composite_projection or {}),
                composite_pre_model=composite_pre_model,
                composite_continuation_key=composite_continuation_key,
            ),
            sandbox=sandbox if mode != "offline" or sandbox is not None else None,
            perturbations=perturbations,
            # Let the compiler build graphs inside each isolation partition. A
            # corpus-wide FieldStats object would leak cross-tenant cardinality
            # into provenance decisions even though artifacts are partitioned.
            graphs=None,
            policy=None,
        )

    job.registry = Registry(name=job_id)
    job.registry.extend(job.artifacts)
    return job


def validate(
    job: OptimizeJob,
    *,
    suites: Sequence[str] = ("replay", "perturbation"),
) -> dict[str, Any]:
    """Summarise the evidence each artifact already carries, per suite.

    Validation is not re-run here: the suites execute during compilation so that a
    candidate that fails them never becomes an artifact. This call collects the
    evidence for review and flags anything that was *not claimed* — proposal §6.3 is
    explicit that pretending the perturbation suite ran is the one indefensible option.
    """

    out: dict[str, Any] = {"suites": list(suites), "artifacts": {}}
    for art in job.artifacts:
        ev = art.evidence
        entry: dict[str, Any] = {
            "kind": art.kind,
            "support_groups": ev.support_groups,
            "removed_requests": ev.removed_requests,
            "lifecycle": art.lifecycle.value,
        }
        if "replay" in suites:
            entry["replay"] = ev.replay or {"claimed": False}
        if "perturbation" in suites:
            claimed = bool(ev.metrics.get("perturbations_claimed"))
            entry["perturbation"] = {
                "claimed": claimed,
                "families": sorted(ev.perturbation) if ev.perturbation else [],
                "hard_rejects": [c for c in ev.counterexamples if c.get("perturbation")],
                "note": None
                if claimed
                else "no sandbox was available: the artifact is validated on the "
                "distribution it has seen and its tail behaviour is unverified",
            }
        if "shadow" in suites:
            entry["shadow"] = {"claimed": art.lifecycle in (Lifecycle.SHADOW, Lifecycle.APPROVED, Lifecycle.ACTIVE)}
        entry["gate"] = {
            "threshold": art.gate.threshold,
            "risk_upper_bound": art.gate.risk_upper_bound,
            "calibration_groups": art.gate.n_calibration_groups,
            "observed_violations": art.gate.observed_violations,
        }
        out["artifacts"][art.artifact_id] = entry
    job.validation = out
    return out


def promote(
    job: OptimizeJob,
    *,
    stage: str = "shadow",
    approved_by: str = "",
    job_identity: str = "optimizer",
    evaluation_split: str = "dev",
    expiry_day: str | None = None,
) -> list[Artifact]:
    """Advance every artifact in the job by one lifecycle stage."""

    target = Lifecycle(stage)
    out: list[Artifact] = []
    for art in job.artifacts:
        promoted = _promote(
                art,
                target,
                approved_by=approved_by,
                job_identity=job_identity,
                evaluation_split=evaluation_split,
                expiry_day=expiry_day,
            )
        if job.registry is not None and job.registry.signing_key:
            promoted.sign(job.registry.signing_key)
        out.append(promoted)
    return out


def retire(job: OptimizeJob, *, actor: str, reason: str) -> list[Artifact]:
    return [_retire(a, actor=actor, reason=reason) for a in job.artifacts]
