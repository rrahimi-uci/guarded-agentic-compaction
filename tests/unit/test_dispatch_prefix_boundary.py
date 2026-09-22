"""Position invariant at runtime (Algorithm 4, line 2).

A compiled region is calibrated on the entry state at position 0 of an episode.
The dispatcher therefore falls back to the baseline whenever *any* tool has
already been observed in the conversation, related to the region or not. The
older ``tools(P) ∩ already_observed`` test is kept for defense in depth, but the
position rule must fire first and carry its own reason.
"""

from __future__ import annotations

from guarded_agentic_compaction.grc.dsl import Expr
from guarded_agentic_compaction.grc.program import CallStep, Program
from guarded_agentic_compaction.grc.composite import synthesize_composite
from guarded_agentic_compaction.registry.store import Registry
from guarded_agentic_compaction.runtime.dispatch import DispatchMode, Dispatcher
from guarded_agentic_compaction.runtime.manual import ManualPreModelPlan, ManualPreModelRunner
from guarded_agentic_compaction.runtime.model_provider import _observed_tools
from guarded_agentic_compaction.schema.artifacts import (
    Artifact,
    DispatchOutcome,
    Gate,
    GateModel,
    HardGuard,
    Lifecycle,
    OutputClause,
    Verifier,
)
from guarded_agentic_compaction.schema.effects import EffectCatalog
from guarded_agentic_compaction.schema.traces import ExecutionManifest


CATALOG = EffectCatalog.from_dict(
    {
        "name": "prefix-boundary-test",
        "version": 1,
        "tools": {
            "records.read": {
                "effect": "READ_LOCAL",
                "capabilities": ["speculatable", "replayable", "cacheable", "batchable"],
            },
            "search.web": {
                "effect": "READ_LOCAL",
                "capabilities": ["speculatable", "replayable", "cacheable", "batchable"],
            },
        },
    }
)

MANIFEST = ExecutionManifest(
    manifest_id="prefix-boundary",
    model="model",
    effect_catalog_version=CATALOG.catalog_version,
)


def _program() -> Program:
    return Program(
        theta=("record_id",),
        steps=[
            CallStep(
                var="record",
                tool="records.read",
                args={"record_id": Expr("z.record_id", ())},
            ),
        ],
        outputs={"record": Expr("record", ())},
        removed_requests=1,
    )


def _artifact() -> Artifact:
    return Artifact(
        artifact_id="prefix-1",
        name="prefix-boundary-test",
        program=_program(),
        guard=HardGuard(),
        verifier=Verifier(
            clauses=[OutputClause("record", "dict", provenance=("records.read",))],
            allowed_effects=("READ_LOCAL",),
            call_counts=(1,),
        ),
        gate=Gate(model=GateModel(bias=-6), threshold=0.5),
        manifest=MANIFEST,
        compatibility_key=MANIFEST.compatibility_key(),
        lifecycle=Lifecycle.ACTIVE,
    )


def _execute(tool: str, arguments: dict) -> dict:
    assert tool == "records.read"
    return {"title": "Verified title", "record_id": arguments["record_id"]}


def _dispatcher() -> Dispatcher:
    registry = Registry(name="prefix-boundary")
    registry.add(_artifact())
    return Dispatcher(registry=registry, catalog=CATALOG, mode=DispatchMode.LIVE)


def _decide(dispatcher: Dispatcher, already_observed: tuple[str, ...]):
    return dispatcher.decide(
        compatibility_key=MANIFEST.compatibility_key(),
        partition={},
        entry_state={"record_id": 7},
        context={"model": "model"},
        executor=_execute,
        already_observed=already_observed,
    )


def test_unrelated_prior_observation_falls_back_with_non_prefix_boundary() -> None:
    dispatcher = _dispatcher()
    # ``search.web`` is not a tool of the region: the old intersection rule would
    # have let this boundary through.
    decision = _decide(dispatcher, ("search.web",))

    assert decision.outcome is DispatchOutcome.BASELINE
    assert not decision.compacted
    assert decision.reasons == ("non_prefix_boundary",)
    assert decision.calls == []
    assert dispatcher.telemetry.guard_misses == {"non_prefix_boundary": 1}
    assert dispatcher.telemetry.baseline == 1
    assert dispatcher.telemetry.compacted == 0


def test_related_prior_observation_is_also_reported_as_non_prefix_boundary() -> None:
    dispatcher = _dispatcher()
    decision = _decide(dispatcher, ("records.read",))

    assert decision.outcome is DispatchOutcome.BASELINE
    assert decision.reasons == ("non_prefix_boundary",)
    # the position rule fires first; the intersection rule stays as defense in depth
    assert "region_already_started" not in dispatcher.telemetry.guard_misses


def test_empty_already_observed_keeps_previous_dispatch_behavior() -> None:
    dispatcher = _dispatcher()
    decision = _decide(dispatcher, ())

    assert decision.outcome is DispatchOutcome.COMPACTED
    assert decision.compacted
    assert decision.calls == [("records.read", {"record_id": 7})]
    assert decision.outputs["record"]["title"] == "Verified title"
    assert dispatcher.telemetry.guard_misses == {}
    assert dispatcher.telemetry.compacted == 1


def test_observed_tools_reads_function_call_items_from_sdk_history() -> None:
    history = [
        {"role": "user", "content": "look up record 7"},
        {
            "type": "function_call",
            "name": "search.web",
            "call_id": "call-1",
            "arguments": "{\"q\": \"record 7\"}",
        },
        {"type": "function_call_output", "call_id": "call-1", "output": "{}"},
    ]
    observed = _observed_tools(history)

    assert len(observed) > 0
    assert observed == ("search.web",)
    # a fresh conversation has no observations and must not trip the rule
    assert _observed_tools([{"role": "user", "content": "hello"}]) == ()
    assert _observed_tools("plain string prompt") == ()
    assert _observed_tools(None) == ()


def _manual_runner() -> ManualPreModelRunner:
    program = synthesize_composite(
        _program(),
        CATALOG,
        name="read_record",
        projection={"title": "tool:records.read::title"},
        continuation_compatibility_key="continuation-v1",
    )
    plan = ManualPreModelPlan(
        name="manual-prefix",
        program=program,
        source_compatibility_key=MANIFEST.compatibility_key(),
        guard=HardGuard(allowed_effects=("READ_LOCAL",)),
        verifier=Verifier(
            clauses=[OutputClause("record", "dict", provenance=("records.read",))],
            allowed_effects=("READ_LOCAL",),
            call_counts=(1,),
        ),
    )
    return ManualPreModelRunner(plan, CATALOG, MANIFEST)


def test_manual_pre_model_plan_enforces_the_same_position_invariant() -> None:
    calls: list[str] = []
    runner = _manual_runner()
    rejected = runner.execute_pre_model(
        {"record_id": 7},
        executor=lambda tool, _args: calls.append(tool) or {"title": "t"},
        already_observed=("search.web",),
        continuation_compatibility_key="continuation-v1",
    )
    assert not rejected.compacted
    assert rejected.record["reasons"] == ["non_prefix_boundary"]
    assert calls == []

    accepted = runner.execute_pre_model(
        {"record_id": 7},
        executor=lambda tool, _args: calls.append(tool) or {"title": "t"},
        continuation_compatibility_key="continuation-v1",
    )
    assert accepted.compacted
    assert calls == ["records.read"]
