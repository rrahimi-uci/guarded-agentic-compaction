"""Guarded execution for manually authored pre-model programs.

This module is the engineering-baseline counterpart to trace-derived GRC/GCS.
It deliberately does not manufacture training support, a calibrated gate, or a
compiler artifact.  Instead, an application supplies a bounded :class:`Program`
and the runtime applies the same hard safety boundary that matters at execution:

* exact source and continuation manifest identities;
* a versioned effect catalog and explicit read-only allowlists;
* bounded, non-dynamic program interpretation through :class:`ToolFacade`;
* output, provenance, effect, and call-count verification; and
* fail-closed projection to one pre-model observation.

Keeping this path distinct is important for honest evaluation.  A hand-written
macro can be given the same pre-model opportunity as a learned composite without
being relabelled as compiler output or inheriting evidence it did not earn.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from ..grc.composite import CompositeProjectionError
from ..grc.dsl import LIBRARY_VERSION
from ..grc.program import Program
from ..schema.artifacts import HardGuard, Verifier
from ..schema.effects import Capability, EffectCatalog, EffectClass
from ..schema.traces import ExecutionManifest
from .facade import FacadeMode, ToolFacade
from .interp import run_program
from .runner import CompactedObservation
from .staging import Snapshot, Staging, StagingViolation

__all__ = [
    "ManualPreModelDecision",
    "ManualPreModelPlan",
    "ManualPreModelRunner",
]


@dataclass(slots=True)
class ManualPreModelPlan:
    """A reviewable, manually authored program with no learned evidence claim."""

    name: str
    program: Program
    source_compatibility_key: str
    guard: HardGuard
    verifier: Verifier
    owner: str = "unassigned"
    approved_by: str | None = None
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "program": self.program.to_dict(),
            "source_compatibility_key": self.source_compatibility_key,
            "guard": self.guard.to_dict(),
            "verifier": self.verifier.to_dict(),
            "owner": self.owner,
            "approved_by": self.approved_by,
            "schema_version": self.schema_version,
            "construction": "manual",
            "statistical_gate": False,
        }

    @property
    def plan_id(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return "manual-" + hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class ManualPreModelDecision:
    """Result of attempting one hand-authored plan before the provider call."""

    compacted: bool
    observations: list[Any] = field(default_factory=list)
    overhead_ms: float = 0.0
    record: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ManualPreModelRunner:
    """Execute a manual read program under exact compatibility and verification."""

    plan: ManualPreModelPlan
    catalog: EffectCatalog
    manifest: ExecutionManifest
    max_calls: int = 24
    observation_factory: Callable[[str, dict[str, Any], Any], Any] = CompactedObservation
    records: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.max_calls <= 0:
            raise ValueError("max_calls must be positive")

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
    ) -> ManualPreModelDecision:
        started = time.perf_counter()
        program = self.plan.program
        composite = program.composite

        reasons = self._structural_reasons()
        if reasons:
            return self._reject(started, reasons)
        if self.plan.source_compatibility_key != self.manifest.compatibility_key():
            return self._reject(started, ("source_manifest_mismatch",))
        if composite is None:  # guarded by _structural_reasons; narrows the type
            return self._reject(started, ("missing_pre_model_composite",))
        if composite.continuation_compatibility_key != continuation_compatibility_key:
            return self._reject(started, ("continuation_manifest_mismatch",))
        if any(tool in already_observed for tool in program.tools):
            return self._reject(started, ("region_already_started",))
        if snapshot_fn is None and any(
            self.catalog.get(tool).quota_attested for tool in program.tools
        ):
            return self._reject(started, ("missing_reversibility_snapshot",))

        try:
            arguments = composite.arguments(entry_state)
        except CompositeProjectionError:
            return self._reject(started, ("composite_input_failed",))

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
            **resolved_partition,
        }
        guard_reasons = self.plan.guard.evaluate(entry_state, context)
        if guard_reasons:
            return self._reject(started, tuple(guard_reasons))

        stage = Staging(snapshot_fn=snapshot_fn, catalog=self.catalog).begin() if snapshot_fn else None
        facade = ToolFacade(
            catalog=self.catalog,
            mode=FacadeMode.LIVE,
            executor=executor,
            allowed_tools=program.tools,
            max_calls=self.max_calls,
        )
        result = run_program(program, entry_state, facade)
        if not result.ok:
            return self._abort_or_incident(started, stage, "interp_failed", len(result.calls))

        verification = self.plan.verifier.verify(
            result.outputs,
            result.env,
            result.provenance,
            result.effects,
            len(result.calls),
        )
        if verification:
            reason = "verifier:" + verification[0].split(":", 1)[0]
            return self._abort_or_incident(started, stage, reason, len(result.calls))
        try:
            projected = composite.project(result.outputs)
        except CompositeProjectionError:
            return self._abort_or_incident(
                started, stage, "composite_projection_failed", len(result.calls)
            )
        if stage is not None:
            try:
                stage.commit(result.effects)
            except StagingViolation:
                return self._finish(
                    started,
                    compacted=False,
                    observations=[],
                    outcome="INCIDENT",
                    reasons=("staging_violation",),
                    n_calls=len(result.calls),
                )

        observation = self.observation_factory(composite.name, arguments, projected)
        return self._finish(
            started,
            compacted=True,
            observations=[observation],
            outcome="EXECUTED",
            reasons=(),
            n_calls=len(result.calls),
        )

    def _structural_reasons(self) -> tuple[str, ...]:
        plan = self.plan
        program = plan.program
        composite = program.composite
        reasons: list[str] = []
        if plan.schema_version != 1:
            reasons.append("invalid_plan:schema_version")
        if not plan.name:
            reasons.append("invalid_plan:name")
        if program.library_version != LIBRARY_VERSION:
            reasons.append("invalid_plan:dsl_version")
        step_tools = tuple(dict.fromkeys(step.tool for step in program.call_steps()))
        if not step_tools or step_tools != program.tools:
            reasons.append("invalid_plan:tool_index")
        if composite is None or not composite.pre_model:
            reasons.append("missing_pre_model_composite")
        else:
            if tuple(composite.inputs) != tuple(program.theta):
                reasons.append("invalid_plan:composite_inputs")
            if tuple(composite.internal_tools) != tuple(program.tools):
                reasons.append("invalid_plan:composite_tools")
            if not composite.projection:
                reasons.append("invalid_plan:composite_projection")
            output_roots = set(program.outputs)
            for target, binding in composite.projection.items():
                source = getattr(binding, "source", "")
                if not target or source.split(".", 1)[0] not in output_roots:
                    reasons.append("invalid_plan:composite_projection")

        output_names = set(program.outputs)
        clause_names = {clause.name for clause in plan.verifier.clauses}
        if not output_names or output_names != clause_names:
            reasons.append("invalid_plan:verifier_outputs")
        if not plan.verifier.call_counts:
            reasons.append("invalid_plan:verifier_call_counts")
        if not plan.verifier.allowed_effects or not plan.guard.allowed_effects:
            reasons.append("invalid_plan:effect_allowlist")

        allowed_effects = set(plan.guard.allowed_effects) & set(plan.verifier.allowed_effects)
        try:
            if not allowed_effects or any(
                not EffectClass(effect).is_read_like for effect in allowed_effects
            ):
                reasons.append("invalid_plan:non_read_effect")
        except ValueError:
            reasons.append("invalid_plan:unknown_effect")

        required = set(plan.guard.required_capabilities)
        for tool in program.tools:
            spec = self.catalog.get(tool)
            if not self.catalog.composite_eligible(tool):
                reasons.append(f"invalid_plan:forbidden_tool:{tool}")
            if spec.effect.value not in allowed_effects:
                reasons.append(f"invalid_plan:effect:{tool}")
            capabilities = {value.value for value in spec.capabilities}
            if not required.issubset(capabilities):
                reasons.append(f"invalid_plan:capability:{tool}")
            if Capability.BATCHABLE not in spec.capabilities:
                reasons.append(f"invalid_plan:not_batchable:{tool}")
        return tuple(dict.fromkeys(reasons))

    def _abort_or_incident(
        self,
        started: float,
        stage: Staging | None,
        reason: str,
        n_calls: int,
    ) -> ManualPreModelDecision:
        clean = stage is None or stage.abort()
        return self._finish(
            started,
            compacted=False,
            observations=[],
            outcome="BASELINE" if clean else "INCIDENT",
            reasons=(reason if clean else reason + "_dirty_abort",),
            n_calls=n_calls,
        )

    def _reject(self, started: float, reasons: Sequence[str]) -> ManualPreModelDecision:
        return self._finish(
            started,
            compacted=False,
            observations=[],
            outcome="BASELINE",
            reasons=tuple(reasons),
            n_calls=0,
        )

    def _finish(
        self,
        started: float,
        *,
        compacted: bool,
        observations: list[Any],
        outcome: str,
        reasons: Sequence[str],
        n_calls: int,
    ) -> ManualPreModelDecision:
        overhead_ms = (time.perf_counter() - started) * 1000.0
        composite = self.plan.program.composite
        record = {
            "outcome": outcome,
            "plan": self.plan.plan_id,
            "construction": "manual",
            "statistical_gate": False,
            "reasons": list(reasons)[:8],
            "n_calls": n_calls,
            "exposed_calls": 1 if compacted else 0,
            "composite": composite.name if compacted and composite is not None else None,
            "overhead_ms": round(overhead_ms, 3),
        }
        self.records.append(record)
        return ManualPreModelDecision(compacted, observations, overhead_ms, record)
