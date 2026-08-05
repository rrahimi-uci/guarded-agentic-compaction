"""Runtime integration paths.

Two are supported, and the wrapper comes first on purpose (execution-plan §10.4):

1. :class:`CompactingRunner` — an explicit outer controller around the agent loop.
   It owns the entry-state snapshot and the staging boundary, which is what makes
   deoptimization exact when a region spans several tools.
2. :class:`~agent_compaction.runtime.model_provider.CompactingModel` — a custom
   Agents SDK ``Model``. Transparent, but post-emission deopt is limited by the
   ``Model`` interface, so it ships behind conformance tests.

:class:`RouteResolver` is the TGWS half: it selects a specialised configuration at
episode start and abstains to the baseline configuration when the route guard or
gate says no.

:func:`compact` is the decorator for agents that are not on the Agents SDK. It takes
``mode=`` — the missing keyword of proposal §6.5 — because without it a non-SDK
deployment cannot run the mandatory shadow step.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from ..paths import content_digest
from ..registry.store import Registry
from ..schema.artifacts import Artifact, DispatchOutcome, Lifecycle, RouteConfig
from ..schema.effects import EffectCatalog
from ..schema.traces import ExecutionManifest
from .continuation import (
    BaselineContinuation,
    ContinuationDecision,
    ContinuationEvidence,
    ContinuationGuard,
    ContinuationOutcome,
)
from .dispatch import DispatchDecision, DispatchMode, Dispatcher
from ..grc.composite import CompositeProjectionError
from .staging import Snapshot

__all__ = ["CompactingRunner", "RouteResolver", "compact", "Decision"]


@dataclass(slots=True)
class Decision:
    """Public decision object returned by :func:`compact`."""

    outcome: str
    observations: list[Any] = field(default_factory=list)
    artifact_id: str | None = None
    reasons: tuple[str, ...] = ()

    BASELINE = "BASELINE"
    COMPACTED = "COMPACTED"
    INCIDENT = "INCIDENT"


@dataclass(frozen=True, slots=True)
class CompactedObservation:
    """A region observation handed back to the host loop as a native history item.

    Structurally identical to what the host would have recorded had the model
    chosen the call itself — tool identity, typed arguments, typed result — which is
    the continuation contract of proposal §5.6 conformance test 2.
    """

    tool: str
    args: dict[str, Any]
    result: Any
    status: str = "ok"


@dataclass(slots=True)
class RunnerDecision:
    """Adapter object the simulated substrate consumes at a boundary."""

    compacted: bool
    observations: list[Any] = field(default_factory=list)
    overhead_ms: float = 0.0
    record: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CompactingRunner:
    """Outer controller for compiled regions and optional continuation validation.

    ``on_boundary`` verifies the deterministic tool program. Applications that also want
    an end-to-end claim must call :meth:`on_continuation` before committing the later
    model output. An absent continuation guard rejects that explicit check; it never
    silently upgrades program verification into answer verification.
    """

    dispatcher: Dispatcher
    catalog: EffectCatalog
    manifest: ExecutionManifest
    max_train_day: str = ""
    attest_quota: bool = True
    observation_factory: Callable[[str, dict[str, Any], Any], Any] | None = None
    continuation_guard: ContinuationGuard | None = None
    records: list[dict[str, Any]] = field(default_factory=list)

    # -- substrate hook ---------------------------------------------------
    def on_boundary(self, spec: Any, manifest: ExecutionManifest, ctx: Any, world: Any) -> RunnerDecision | None:
        return self._on_boundary(spec, manifest, ctx, world, self.observation_factory or CompactedObservation)

    def _on_boundary(
        self,
        spec: Any,
        manifest: ExecutionManifest,
        ctx: Any,
        world: Any,
        make_observation: Callable[[str, dict[str, Any], Any], Any],
    ) -> RunnerDecision | None:
        partition = {
            "tenant_partition": getattr(spec, "tenant_partition", "unknown"),
            "principal": getattr(spec, "principal", "unknown"),
            "policy_version": getattr(spec, "policy_version", "v0"),
        }
        context = {
            "model": manifest.model,
            "prompt_hash": manifest.prompt_hash,
            "tools_hash": manifest.tools_hash,
            "policy_hash": manifest.policy_hash,
            "guardrail_hash": manifest.guardrail_hash,
            "effect_catalog_version": self.catalog.catalog_version,
            "entry_contract_version": manifest.entry_contract_version,
            "day": getattr(spec, "day", ""),
            "max_train_day": self.max_train_day,
            **partition,
        }
        observed = {o.tool for o in getattr(ctx, "observations", [])}

        decision = self.dispatcher.decide(
            compatibility_key=manifest.compatibility_key(),
            partition=partition,
            entry_state=spec.entry_state,
            context=context,
            executor=(lambda tool, args: world.execute(tool, args)),
            snapshot_fn=(lambda: self._snapshot(world, ctx, spec)),
            already_observed=tuple(observed),
        )
        self.records.append(decision.record)
        observations = self._materialize_observations(
            decision,
            spec.entry_state,
            make_observation,
        )
        return RunnerDecision(
            compacted=decision.compacted,
            observations=observations if decision.compacted else [],
            overhead_ms=decision.overhead_ms,
            record=decision.record,
        )

    def execute_pre_model(
        self,
        entry_state: dict[str, Any],
        *,
        executor: Callable[[str, dict[str, Any]], Any],
        partition: dict[str, str] | None = None,
        day: str = "",
        snapshot_fn: Callable[[], Snapshot] | None = None,
        already_observed: Sequence[str] = (),
        continuation_compatibility_key: str = "",
    ) -> RunnerDecision:
        """Execute an admitted composite before the first provider request.

        This is the integration point that a normal agent loop cannot express at
        a model boundary.  Only artifacts explicitly packaged with
        ``composite.pre_model`` are released as one observation; an ordinary GRC
        artifact still executes safely but retains its internal observations.
        """

        resolved_partition = dict(partition or {})
        context = {
            "model": self.manifest.model,
            "prompt_hash": self.manifest.prompt_hash,
            "tools_hash": self.manifest.tools_hash,
            "policy_hash": self.manifest.policy_hash,
            "guardrail_hash": self.manifest.guardrail_hash,
            "effect_catalog_version": self.catalog.catalog_version,
            "entry_contract_version": self.manifest.entry_contract_version,
            "day": day,
            "max_train_day": self.max_train_day,
            **resolved_partition,
        }
        decision = self.dispatcher.decide(
            compatibility_key=self.manifest.compatibility_key(),
            partition=resolved_partition,
            entry_state=entry_state,
            context=context,
            executor=executor,
            snapshot_fn=snapshot_fn,
            already_observed=already_observed,
            require_pre_model_composite=True,
            continuation_compatibility_key=continuation_compatibility_key,
        )
        self.records.append(decision.record)
        observations = self._materialize_observations(
            decision,
            entry_state,
            self.observation_factory or CompactedObservation,
            require_pre_model=True,
        )
        return RunnerDecision(
            compacted=decision.compacted and bool(observations),
            observations=observations if decision.compacted else [],
            overhead_ms=decision.overhead_ms,
            record=decision.record,
        )

    @staticmethod
    def _materialize_observations(
        decision: DispatchDecision,
        entry_state: dict[str, Any],
        make_observation: Callable[[str, dict[str, Any], Any], Any],
        *,
        require_pre_model: bool = False,
    ) -> list[Any]:
        if not decision.compacted or decision.artifact is None or decision.artifact.program is None:
            return []
        composite = decision.artifact.program.composite
        if require_pre_model and composite is not None and composite.pre_model:
            try:
                arguments = composite.arguments(entry_state)
            except CompositeProjectionError:
                return []
            return [make_observation(composite.name, arguments, decision.projected_outputs)]
        if require_pre_model:
            return []
        return [
            make_observation(tool, args, result)
            for (tool, args), result in zip(decision.calls, decision.results)
        ]

    def _snapshot(self, world: Any, ctx: Any, spec: Any) -> Snapshot:
        """Snapshot of everything the attestation claims to cover.

        Only counters the catalog declares as ``quota_attested`` are included: a
        read that provably writes no counter cannot make an abort dirty, and a read
        that does write one must say so (use-cases §1).
        """

        quota = tuple(
            sorted(
                (tool, count)
                for tool, count in getattr(world, "quota", {}).items()
                if self.catalog.get(tool).quota_attested
            )
        )
        history = content_digest([(o.tool, o.args) for o in getattr(ctx, "observations", [])])
        return Snapshot(
            state_digest=world.state_digest(),
            history_digest=history,
            quota=quota,
            budget=len(getattr(ctx, "observations", [])),
            permission_context=getattr(spec, "principal", "unknown"),
        )

    def on_continuation(
        self,
        candidate: Any,
        *,
        entry_state: dict[str, Any],
        observations: Sequence[Any],
        artifact_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        baseline: BaselineContinuation | None = None,
    ) -> ContinuationDecision:
        """Validate a model continuation before the host commits it to history.

        The host owns when this hook runs because only the host knows when an output is
        still reversible. A rejected decision contains no output; callers must stop,
        escalate, or use another application-approved path rather than emitting the
        original candidate.
        """

        evidence = ContinuationEvidence(
            entry_state=dict(entry_state),
            observations=tuple(observations),
            artifact_id=artifact_id,
            metadata=dict(metadata or {}),
        )
        if self.continuation_guard is None:
            decision = ContinuationDecision(
                ContinuationOutcome.REJECTED,
                candidate_violations=("continuation_guard_not_configured",),
            )
        else:
            decision = self.continuation_guard.decide(candidate, evidence, baseline=baseline)
        self.records.append({"continuation": decision.record})
        return decision


@dataclass(slots=True)
class RouteResolver:
    """TGWS route selection at episode start, with abstention to baseline."""

    registry: Registry
    catalog: EffectCatalog
    manifest: ExecutionManifest
    mode: str = DispatchMode.LIVE
    hits: int = 0
    misses: int = 0
    miss_reasons: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.mode not in DispatchMode.values():
            raise ValueError(f"mode must be one of {DispatchMode.values()}, got {self.mode!r}")

    def resolve(self, spec: Any) -> RouteConfig | None:
        if self.mode == DispatchMode.OFF:
            return None
        partition = {
            "tenant_partition": getattr(spec, "tenant_partition", "unknown"),
            "principal": getattr(spec, "principal", "unknown"),
            "policy_version": getattr(spec, "policy_version", "v0"),
        }
        context = {
            "model": self.manifest.model,
            "prompt_hash": self.manifest.prompt_hash,
            "tools_hash": self.manifest.tools_hash,
            "policy_hash": self.manifest.policy_hash,
            "guardrail_hash": self.manifest.guardrail_hash,
            "effect_catalog_version": self.catalog.catalog_version,
            "entry_contract_version": self.manifest.entry_contract_version,
            **partition,
        }
        stages = (
            (Lifecycle.SHADOW, Lifecycle.APPROVED, Lifecycle.ACTIVE)
            if self.mode == DispatchMode.SHADOW
            else (Lifecycle.ACTIVE,)
        )
        candidates = self.registry.resolve(
            self.manifest.compatibility_key(), partition, kind="tgws", stages=stages
        )
        for art in candidates:
            reasons = art.guard.evaluate(spec.entry_state, context)
            if reasons:
                for r in reasons:
                    self.miss_reasons[r.split(":")[0]] = self.miss_reasons.get(r.split(":")[0], 0) + 1
                continue
            if art.route is None or not art.route.matches(spec.entry_state):
                self.miss_reasons["route_predicate"] = self.miss_reasons.get("route_predicate", 0) + 1
                continue
            feats = _route_features(
                art,
                spec.entry_state,
                day=str(getattr(spec, "day", "")),
            )
            ok, _q = art.gate.accepts(feats)
            if not ok:
                self.miss_reasons["gate"] = self.miss_reasons.get("gate", 0) + 1
                continue
            self.hits += 1
            if self.mode == DispatchMode.SHADOW:
                return None
            return art.route
        self.misses += 1
        return None


def _route_features(
    artifact: Artifact, entry_state: dict[str, Any], *, day: str = ""
) -> dict[str, float]:
    """Use the serialized calibration feature transform byte-for-byte."""

    from ..grc.calibrate import FEATURE_NAMES, GateFeatures

    if not artifact.gate.features_spec:
        return {name: 0.0 for name in FEATURE_NAMES}
    return GateFeatures.from_dict(artifact.gate.features_spec).raw(entry_state, day=day)


def compact(
    registry: Registry,
    catalog: EffectCatalog,
    manifest: ExecutionManifest,
    *,
    mode: str = DispatchMode.SHADOW,
    executor: Callable[[str, dict[str, Any]], Any] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for non-SDK agents.

    ``mode`` is a first-class argument: shadow is the mandatory first deployment
    step, and without this keyword a decorated agent could not run it.
    """

    dispatcher = Dispatcher(registry=registry, catalog=catalog, mode=mode)

    def decorate(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(entry_state: dict[str, Any], *args: Any, **kwargs: Any) -> Any:
            partition = {
                "tenant_partition": str(entry_state.get("tenant_id", "unknown")),
                "principal": str(entry_state.get("principal", "unknown")),
                "policy_version": str(entry_state.get("policy_version", "v0")),
            }
            decision = dispatcher.decide(
                compatibility_key=manifest.compatibility_key(),
                partition=partition,
                entry_state=entry_state,
                context={
                    "model": manifest.model,
                    "prompt_hash": manifest.prompt_hash,
                    "tools_hash": manifest.tools_hash,
                    "policy_hash": manifest.policy_hash,
                    "guardrail_hash": manifest.guardrail_hash,
                    "effect_catalog_version": catalog.catalog_version,
                    "entry_contract_version": manifest.entry_contract_version,
                    **partition,
                },
                executor=executor,
            )
            if decision.compacted:
                observations = [
                    {"tool": tool, "arguments": args_, "result": result}
                    for (tool, args_), result in zip(decision.calls, decision.results)
                ]
                return Decision(
                    outcome=Decision.COMPACTED,
                    observations=observations,
                    artifact_id=decision.artifact.artifact_id if decision.artifact else None,
                )
            if decision.outcome is DispatchOutcome.INCIDENT:
                return Decision(outcome=Decision.INCIDENT, reasons=decision.reasons)
            return fn(entry_state, *args, **kwargs)

        wrapper.dispatcher = dispatcher  # type: ignore[attr-defined]
        return wrapper

    return decorate
