"""Algorithm 7 — runtime dispatch with staged deoptimization.

    resolve → hard guard → gate → stage.begin → interpret → verify → commit

Every failure before an external commitment returns ``BASELINE`` with the original
entry state and the safely reusable read observations. A failure *after* a
commitment raises ``INCIDENT``: the runtime does not pretend to roll back. In v0.x
programs may only contain pre-commit reads, so the incident path is reachable only
through a catalog or configuration error — which is exactly why it is implemented
and tested rather than assumed impossible.

``mode`` selects the three deployment steps of the adoption recipe:

``off``
    no-op; must produce byte-identical model input (conformance test 1).
``shadow``
    score and log what *would* have dispatched; execute nothing, commit nothing.
``live``
    dispatch.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from ..registry.store import Registry
from ..schema.artifacts import Artifact, DispatchOutcome, Lifecycle
from ..schema.effects import EffectCatalog
from .facade import FacadeMode, ForbiddenTool, Recording, ToolFacade
from .interp import InterpResult, PostCommitError, PreCommitError, run_program
from .staging import Snapshot, Staging, StagingViolation

__all__ = ["DispatchMode", "DispatchDecision", "Dispatcher", "DispatchTelemetry"]


class DispatchMode:
    OFF = "off"
    SHADOW = "shadow"
    LIVE = "live"

    @classmethod
    def values(cls) -> tuple[str, ...]:
        return (cls.OFF, cls.SHADOW, cls.LIVE)


@dataclass(slots=True)
class DispatchDecision:
    """What the dispatcher decided at one boundary."""

    outcome: DispatchOutcome
    artifact: Artifact | None = None
    q: float = 1.0
    reasons: tuple[str, ...] = ()
    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    results: list[Any] = field(default_factory=list)
    outputs: dict[str, Any] = field(default_factory=dict)
    effects: tuple[str, ...] = ()
    removed_requests: float = 0.0
    overhead_ms: float = 0.0
    shadow: bool = False
    error: str = ""

    @property
    def compacted(self) -> bool:
        return self.outcome is DispatchOutcome.COMPACTED and not self.shadow

    @property
    def record(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome.value,
            "artifact": self.artifact.artifact_id if self.artifact else None,
            "q": round(self.q, 4),
            "reasons": list(self.reasons)[:6],
            "n_calls": len(self.calls),
            "removed_requests": self.removed_requests,
            "overhead_ms": round(self.overhead_ms, 3),
            "shadow": self.shadow,
            "error": self.error[:160],
        }


@dataclass(slots=True)
class DispatchTelemetry:
    """Counters the drift/incident monitor consumes."""

    attempts: int = 0
    #: Boundaries where the guard *and* the gate accepted, i.e. real dispatch
    #: attempts. The verifier pass rate ρ of Eq. (8) is measured against this, not
    #: against every boundary the dispatcher merely looked at.
    dispatch_attempts: int = 0
    compacted: int = 0
    baseline: int = 0
    incidents: int = 0
    guard_misses: dict[str, int] = field(default_factory=dict)
    gate_rejections: int = 0
    verifier_failures: dict[str, int] = field(default_factory=dict)
    interp_failures: dict[str, int] = field(default_factory=dict)
    shadow_agreements: int = 0
    shadow_disagreements: int = 0
    shadow_would_dispatch: int = 0
    overhead_ms: float = 0.0
    removed_requests: float = 0.0

    def bump(self, bucket: dict[str, int], key: str) -> None:
        bucket[key] = bucket.get(key, 0) + 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "attempts": self.attempts,
            "compacted": self.compacted,
            "baseline": self.baseline,
            "incidents": self.incidents,
            "gate_rejections": self.gate_rejections,
            "guard_misses": dict(sorted(self.guard_misses.items(), key=lambda kv: -kv[1])[:8]),
            "verifier_failures": dict(self.verifier_failures),
            "interp_failures": dict(self.interp_failures),
            "dispatch_attempts": self.dispatch_attempts,
            "shadow_would_dispatch": self.shadow_would_dispatch,
            "shadow_would_dispatch_rate": (
                round(self.shadow_would_dispatch / self.attempts, 4)
                if self.attempts
                else 0.0
            ),
            "verifier_pass_rate": (
                round(self.compacted / self.dispatch_attempts, 4) if self.dispatch_attempts else 0.0
            ),
            "boundary_dispatch_rate": round(self.dispatch_attempts / self.attempts, 4) if self.attempts else 0.0,
            "overhead_ms_total": round(self.overhead_ms, 2),
            "removed_requests_total": round(self.removed_requests, 2),
        }


@dataclass(slots=True)
class Dispatcher:
    """Registry-backed dispatcher. One instance per deployment surface."""

    registry: Registry
    catalog: EffectCatalog
    mode: str = DispatchMode.SHADOW
    telemetry: DispatchTelemetry = field(default_factory=DispatchTelemetry)
    max_calls: int = 24
    gate_cost_ms: float = 1.0

    def __post_init__(self) -> None:
        if self.mode not in DispatchMode.values():
            raise ValueError(f"mode must be one of {DispatchMode.values()}, got {self.mode!r}")
        if self.max_calls <= 0:
            raise ValueError("max_calls must be positive")
        if self.gate_cost_ms < 0:
            raise ValueError("gate_cost_ms must be non-negative")

    def decide(
        self,
        *,
        compatibility_key: str,
        partition: dict[str, str],
        entry_state: dict[str, Any],
        context: dict[str, Any],
        executor: Callable[[str, dict[str, Any]], Any] | None = None,
        recording: Recording | None = None,
        snapshot_fn: Callable[[], Snapshot] | None = None,
        already_observed: Sequence[str] = (),
        defer_execution: bool = False,
    ) -> DispatchDecision:
        t0 = time.perf_counter()
        self.telemetry.attempts += 1

        if self.mode == DispatchMode.OFF:
            self.telemetry.baseline += 1
            return DispatchDecision(DispatchOutcome.BASELINE, reasons=("mode_off",), overhead_ms=0.0)

        # ---- line 1: O(1) resolve ---------------------------------------
        stages = (
            (Lifecycle.SHADOW, Lifecycle.APPROVED, Lifecycle.ACTIVE)
            if self.mode == DispatchMode.SHADOW
            else (Lifecycle.ACTIVE,)
        )
        candidates = self.registry.resolve(
            compatibility_key, partition, kind="grc", stages=stages
        )
        if not candidates:
            self.telemetry.baseline += 1
            self.telemetry.bump(self.telemetry.guard_misses, "no_artifact")
            return DispatchDecision(
                DispatchOutcome.BASELINE, reasons=("no_artifact",), overhead_ms=self._elapsed(t0)
            )

        # ---- lines 2-3: hard guard --------------------------------------
        admissible: list[tuple[Artifact, float]] = []
        first_reasons: tuple[str, ...] = ()
        for art in candidates:
            invalid = self._artifact_reasons(art)
            if invalid:
                if not first_reasons:
                    first_reasons = tuple(invalid)
                for reason in invalid:
                    self.telemetry.bump(self.telemetry.guard_misses, reason.split(":")[0])
                continue
            reasons = art.guard.evaluate(entry_state, context)
            if reasons:
                if not first_reasons:
                    first_reasons = tuple(reasons)
                for r in reasons:
                    self.telemetry.bump(self.telemetry.guard_misses, r.split(":")[0])
                continue
            if art.program is not None and any(t in already_observed for t in art.program.tools):
                # the region has already partly run in this episode; its live-ins
                # are no longer the ones the contract was fitted on
                self.telemetry.bump(self.telemetry.guard_misses, "region_already_started")
                continue
            if (
                self.mode == DispatchMode.LIVE
                and snapshot_fn is None
                and art.program is not None
                and any(self.catalog.get(tool).quota_attested for tool in art.program.tools)
            ):
                reason = "missing_reversibility_snapshot"
                if not first_reasons:
                    first_reasons = (reason,)
                self.telemetry.bump(self.telemetry.guard_misses, reason)
                continue
            feats = self._features(art, entry_state, context)
            ok, q = art.gate.accepts(feats)
            if not ok:
                self.telemetry.gate_rejections += 1
                continue
            admissible.append((art, q))

        if not admissible:
            self.telemetry.baseline += 1
            return DispatchDecision(
                DispatchOutcome.BASELINE,
                reasons=first_reasons or ("guard_or_gate",),
                overhead_ms=self._elapsed(t0),
            )

        # ---- line 4: deterministic argmin, ties by artifact id ----------
        admissible.sort(key=lambda pair: (pair[1], pair[0].artifact_id))
        artifact, q = admissible[0]

        if self.mode == DispatchMode.SHADOW:
            self.telemetry.shadow_would_dispatch += 1
            self.telemetry.baseline += 1
            return DispatchDecision(
                DispatchOutcome.BASELINE,
                artifact=artifact,
                q=q,
                reasons=("shadow",),
                shadow=True,
                removed_requests=artifact.evidence.removed_requests,
                overhead_ms=self._elapsed(t0),
            )

        if defer_execution:
            # The Agents SDK Model adapter emits one native tool call per Runner
            # turn. Selection happens here; execution and verifier accounting are
            # completed by that adapter after it observes the tool outputs.
            return DispatchDecision(
                DispatchOutcome.BASELINE,
                artifact=artifact,
                q=q,
                reasons=("execution_deferred",),
                removed_requests=artifact.evidence.removed_requests,
                overhead_ms=self._elapsed(t0),
            )

        # ---- lines 6-14: stage, run, verify, commit ---------------------
        self.telemetry.dispatch_attempts += 1
        stage = None
        if snapshot_fn is not None:
            stage = Staging(snapshot_fn=snapshot_fn, catalog=self.catalog).begin()

        facade = ToolFacade(
            catalog=self.catalog,
            mode=FacadeMode.LIVE if executor is not None else FacadeMode.RECORDED,
            executor=executor,
            recording=recording,
            allowed_tools=tuple(artifact.program.tools) if artifact.program else (),
            max_calls=self.max_calls,
        )
        result = run_program(artifact.program, entry_state, facade)

        if not result.ok:
            self.telemetry.bump(self.telemetry.interp_failures, result.error.split(":")[0][:40])
            clean = self._abort(stage)
            if not clean:
                self.telemetry.incidents += 1
                return DispatchDecision(
                    DispatchOutcome.INCIDENT,
                    artifact=artifact,
                    q=q,
                    reasons=("interp_failed_dirty_abort",),
                    error=result.error,
                    calls=result.calls,
                    effects=result.effects,
                    overhead_ms=self._elapsed(t0),
                )
            self.telemetry.baseline += 1
            return DispatchDecision(
                DispatchOutcome.BASELINE,
                artifact=artifact,
                q=q,
                reasons=("interp_failed",),
                error=result.error,
                calls=result.calls,
                effects=result.effects,
                overhead_ms=self._elapsed(t0),
            )

        bad = artifact.verifier.verify(
            result.outputs, result.env, result.provenance, result.effects, len(result.calls)
        )
        if bad:
            self.telemetry.bump(self.telemetry.verifier_failures, bad[0].split(":")[0])
            clean = self._abort(stage)
            if not clean:
                self.telemetry.incidents += 1
                return DispatchDecision(
                    DispatchOutcome.INCIDENT,
                    artifact=artifact,
                    q=q,
                    reasons=tuple(bad[:4]),
                    error="verifier failed and staging could not attest reversibility",
                    calls=result.calls,
                    effects=result.effects,
                    overhead_ms=self._elapsed(t0),
                )
            self.telemetry.baseline += 1
            return DispatchDecision(
                DispatchOutcome.BASELINE,
                artifact=artifact,
                q=q,
                reasons=tuple(bad[:4]),
                calls=result.calls,
                effects=result.effects,
                overhead_ms=self._elapsed(t0),
            )

        if stage is not None:
            try:
                stage.commit(result.effects)
            except StagingViolation as exc:
                self.telemetry.incidents += 1
                return DispatchDecision(
                    DispatchOutcome.INCIDENT,
                    artifact=artifact,
                    q=q,
                    reasons=("staging_violation",),
                    error=str(exc),
                    calls=result.calls,
                    effects=result.effects,
                    overhead_ms=self._elapsed(t0),
                )

        self.telemetry.compacted += 1
        self.telemetry.removed_requests += artifact.evidence.removed_requests
        return DispatchDecision(
            DispatchOutcome.COMPACTED,
            artifact=artifact,
            q=q,
            calls=result.calls,
            results=result.results,
            outputs=result.outputs,
            effects=result.effects,
            removed_requests=artifact.evidence.removed_requests,
            overhead_ms=self._elapsed(t0),
        )

    # -- helpers ----------------------------------------------------------
    def _features(self, artifact: Artifact, entry_state: dict[str, Any], context: dict[str, Any]) -> dict[str, float]:
        """Recompute the gate's features exactly as calibration computed them.

        The fitted feature spec travels inside the artifact. Recomputing features
        from a different code path — even a plausible-looking one — would break the
        conditionally i.i.d. group-indicator model the Eq. (18) certificate depends on.
        """

        from ..grc.calibrate import FEATURE_NAMES, GateFeatures

        spec = artifact.gate.features_spec
        if not spec:
            return {name: 0.0 for name in FEATURE_NAMES}
        feats = GateFeatures.from_dict(spec)
        return feats.raw(entry_state, day=str(context.get("day", "")))

    def _artifact_reasons(self, artifact: Artifact) -> list[str]:
        """Validate executable structure against the current permission catalog."""

        from ..grc.dsl import LIBRARY_VERSION

        if artifact.program is None:
            return ["invalid_artifact:no_program"]
        if artifact.program.library_version != LIBRARY_VERSION:
            return ["invalid_artifact:dsl_version"]
        reasons: list[str] = []
        for tool in artifact.program.tools:
            spec = self.catalog.get(tool)
            if not spec.compilable:
                reasons.append(f"invalid_artifact:forbidden_tool:{tool}")
            if artifact.guard.allowed_effects and spec.effect.value not in artifact.guard.allowed_effects:
                reasons.append(f"invalid_artifact:guard_effect:{tool}")
            if artifact.verifier.allowed_effects and spec.effect.value not in artifact.verifier.allowed_effects:
                reasons.append(f"invalid_artifact:verifier_effect:{tool}")
        return reasons

    def _abort(self, stage: Staging | None) -> bool:
        if stage is None:
            return True
        return stage.abort()

    def _elapsed(self, t0: float) -> float:
        ms = (time.perf_counter() - t0) * 1000.0 + self.gate_cost_ms
        self.telemetry.overhead_ms += ms
        return ms
