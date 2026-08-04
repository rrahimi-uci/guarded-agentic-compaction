"""Fault injection: nothing may cross the commit boundary (execution-plan WP6).

The suite asserts the four properties the safety model rests on:

1. recorded replay cannot reach an effectful tool — the facade refuses, so
   "production replay cannot call effectful tools" is enforced by code;
2. a tool failure mid-region deoptimizes to the baseline and commits nothing;
3. a verifier failure with a dirty staging snapshot is classified as an INCIDENT, not
   as a silent fallback;
4. the kill switch and signature verification take precedence over dispatch.
"""

from __future__ import annotations

import pytest

from agent_compaction.grc.dsl import Const, Expr
from agent_compaction.grc.program import CallStep, Predicate, Program
from agent_compaction.registry.store import Registry
from agent_compaction.runtime.dispatch import DispatchMode, Dispatcher
from agent_compaction.runtime.facade import FacadeMode, ForbiddenTool, Recording, ToolFacade
from agent_compaction.runtime.interp import run_program
from agent_compaction.runtime.runner import RouteResolver
from agent_compaction.runtime.staging import Snapshot, Staging, StagingViolation
from agent_compaction.schema.artifacts import (
    Artifact,
    Gate,
    GateModel,
    HardGuard,
    Lifecycle,
    OutputClause,
    Verifier,
)
from agent_compaction.schema.effects import EffectCatalog
from agent_compaction.schema.traces import ExecutionManifest

CATALOG = EffectCatalog.from_dict(
    {
        "version": 1,
        "name": "fault",
        "tools": {
            "r.read": {
                "effect": "READ_EXTERNAL",
                "capabilities": ["speculatable", "replayable", "cacheable"],
                "resource": "r",
            },
            "r.read2": {
                "effect": "READ_EXTERNAL",
                "capabilities": ["speculatable", "replayable", "cacheable"],
                "resource": "r",
            },
            "w.write": {"effect": "WRITE_IRREVERSIBLE", "capabilities": [], "resource": "w"},
            "q.metered": {
                "effect": "READ_EXTERNAL",
                "capabilities": ["speculatable", "replayable"],
                "quota_attested": True,
                "resource": "q",
            },
        },
    }
)

MANIFEST = ExecutionManifest(manifest_id="m", model="m1", prompt_hash="#p")


def _program(second_tool: str = "r.read2") -> Program:
    return Program(
        theta=("key",),
        steps=[
            CallStep(var="a", tool="r.read", args={"key": Expr("z.key", ())}),
            CallStep(var="b", tool=second_tool, args={"ref": Expr("a.ref", ())}),
        ],
        outputs={"a": Expr("a", ()), "b": Expr("b", ())},
        removed_requests=2.0,
        tools=("r.read", second_tool),
    )


def _artifact(program: Program) -> Artifact:
    return Artifact(
        artifact_id="art-1",
        name="fault.region@1",
        program=program,
        guard=HardGuard(manifest_pins={"model": "m1"}, isolation={"tenant_partition": "t1"}),
        verifier=Verifier(
            clauses=[OutputClause(name="a", type_name="dict", provenance=("r.read",))],
            allowed_effects=("READ_EXTERNAL",),
        ),
        gate=Gate(model=GateModel(features=(), weights=(), bias=-6.0), threshold=0.5),
        manifest=MANIFEST,
        compatibility_key=MANIFEST.compatibility_key(),
        partition={"tenant_partition": "t1"},
        lifecycle=Lifecycle.ACTIVE,
    )


class _World:
    def __init__(self, fail: str | None = None, write_on: str | None = None) -> None:
        self.fail = fail
        self.write_on = write_on
        self.committed: list[str] = []
        self.quota: dict[str, int] = {}

    def execute(self, tool: str, args: dict) -> dict:
        self.quota[tool] = self.quota.get(tool, 0) + 1
        if self.fail == tool:
            raise RuntimeError("injected 5xx")
        if self.write_on == tool:
            self.committed.append(tool)
        return {"ref": "abc123", "tool": tool}

    def state_digest(self) -> str:
        return f"digest:{len(self.committed)}"


def test_recorded_replay_cannot_call_an_effectful_tool():
    facade = ToolFacade(catalog=CATALOG, mode=FacadeMode.RECORDED, recording=Recording())
    with pytest.raises(ForbiddenTool):
        facade.call("w.write", {"x": 1})
    assert facade.calls == []


def test_facade_refuses_tools_outside_the_artifact_allowlist():
    facade = ToolFacade(
        catalog=CATALOG,
        mode=FacadeMode.LIVE,
        executor=lambda t, a: {},
        allowed_tools=("r.read",),
    )
    with pytest.raises(ForbiddenTool):
        facade.call("r.read2", {})


def test_facade_enforces_a_call_budget():
    facade = ToolFacade(
        catalog=CATALOG, mode=FacadeMode.LIVE, executor=lambda t, a: {}, max_calls=1
    )
    facade.call("r.read", {})
    with pytest.raises(Exception):
        facade.call("r.read", {})


def test_runtime_modes_reject_typos_instead_of_falling_through_to_live():
    reg = Registry(name="r")
    with pytest.raises(ValueError):
        Dispatcher(registry=reg, catalog=CATALOG, mode="liv")
    with pytest.raises(ValueError):
        ToolFacade(catalog=CATALOG, mode="liv", executor=lambda _t, _a: {})
    with pytest.raises(ValueError):
        RouteResolver(registry=reg, catalog=CATALOG, manifest=MANIFEST, mode="liv")


def test_tool_failure_mid_region_falls_back_and_commits_nothing():
    world = _World(fail="r.read2")
    reg = Registry(name="r")
    reg.add(_artifact(_program()))
    disp = Dispatcher(registry=reg, catalog=CATALOG, mode=DispatchMode.LIVE)
    decision = disp.decide(
        compatibility_key=MANIFEST.compatibility_key(),
        partition={"tenant_partition": "t1"},
        entry_state={"key": "k1"},
        context={"model": "m1", "tenant_partition": "t1"},
        executor=world.execute,
        snapshot_fn=lambda: Snapshot(world.state_digest(), "h", (), 0, "p"),
    )
    assert decision.outcome.value == "BASELINE"
    assert "interp_failed" in decision.reasons
    assert world.committed == []
    assert disp.telemetry.incidents == 0


def test_tool_failure_after_a_quota_commit_is_an_incident():
    program = Program(
        theta=("key",),
        steps=[
            CallStep(var="a", tool="q.metered", args={"key": Expr("z.key", ())}),
            CallStep(var="b", tool="r.read2", args={"ref": Expr("a.ref", ())}),
        ],
        outputs={"a": Expr("a", ()), "b": Expr("b", ())},
        removed_requests=2.0,
        tools=("q.metered", "r.read2"),
    )
    world = _World(fail="r.read2")
    reg = Registry(name="r")
    reg.add(_artifact(program))
    disp = Dispatcher(registry=reg, catalog=CATALOG, mode=DispatchMode.LIVE)

    def snapshot() -> Snapshot:
        quota = tuple(
            sorted((tool, count) for tool, count in world.quota.items() if tool == "q.metered")
        )
        return Snapshot(world.state_digest(), "h", quota, 0, "p")

    decision = disp.decide(
        compatibility_key=MANIFEST.compatibility_key(),
        partition={"tenant_partition": "t1"},
        entry_state={"key": "k1"},
        context={"model": "m1", "tenant_partition": "t1"},
        executor=world.execute,
        snapshot_fn=snapshot,
    )
    assert decision.outcome.value == "INCIDENT"
    assert decision.reasons == ("interp_failed_dirty_abort",)
    assert disp.telemetry.incidents == 1


def test_a_write_inside_the_program_is_refused_before_it_runs():
    world = _World(write_on="w.write")
    reg = Registry(name="r")
    reg.add(_artifact(_program(second_tool="w.write")))
    disp = Dispatcher(registry=reg, catalog=CATALOG, mode=DispatchMode.LIVE)
    decision = disp.decide(
        compatibility_key=MANIFEST.compatibility_key(),
        partition={"tenant_partition": "t1"},
        entry_state={"key": "k1"},
        context={"model": "m1", "tenant_partition": "t1"},
        executor=world.execute,
    )
    assert decision.outcome.value == "BASELINE"
    assert world.committed == []


def test_verifier_failure_with_a_dirty_snapshot_is_an_incident_not_a_fallback():
    world = _World()
    art = _artifact(_program())
    # a verifier clause that cannot hold, to force the failure path
    art.verifier = Verifier(
        clauses=[OutputClause(name="a", type_name="str")], allowed_effects=("READ_EXTERNAL",)
    )
    reg = Registry(name="r")
    reg.add(art)
    disp = Dispatcher(registry=reg, catalog=CATALOG, mode=DispatchMode.LIVE)

    state = {"n": 0}

    def snapshot() -> Snapshot:
        # the world moves under us: the abort cannot attest reversibility
        state["n"] += 1
        return Snapshot(f"digest:{state['n']}", "h", (), 0, "p")

    decision = disp.decide(
        compatibility_key=MANIFEST.compatibility_key(),
        partition={"tenant_partition": "t1"},
        entry_state={"key": "k1"},
        context={"model": "m1", "tenant_partition": "t1"},
        executor=world.execute,
        snapshot_fn=snapshot,
    )
    assert decision.outcome.value == "INCIDENT"
    assert disp.telemetry.incidents == 1


def test_verifier_failure_with_a_clean_snapshot_is_an_exact_fallback():
    world = _World()
    art = _artifact(_program())
    art.verifier = Verifier(clauses=[OutputClause(name="a", type_name="str")])
    reg = Registry(name="r")
    reg.add(art)
    disp = Dispatcher(registry=reg, catalog=CATALOG, mode=DispatchMode.LIVE)
    decision = disp.decide(
        compatibility_key=MANIFEST.compatibility_key(),
        partition={"tenant_partition": "t1"},
        entry_state={"key": "k1"},
        context={"model": "m1", "tenant_partition": "t1"},
        executor=world.execute,
        snapshot_fn=lambda: Snapshot("stable", "h", (), 0, "p"),
    )
    assert decision.outcome.value == "BASELINE"
    assert disp.telemetry.incidents == 0


def test_attested_quota_counter_makes_the_abort_dirty():
    """A read that increments an attested counter cannot claim a clean abort."""

    snaps = iter(
        [
            Snapshot("s", "h", (("q.metered", 1),), 0, "p"),
            Snapshot("s", "h", (("q.metered", 2),), 0, "p"),
        ]
    )
    stage = Staging(snapshot_fn=lambda: next(snaps), catalog=CATALOG).begin()
    assert stage.abort() is False
    assert "quota" in stage.reasons


def test_unobservable_state_reported_after_begin_makes_abort_dirty():
    snaps = iter(
        [
            Snapshot("s", "h", (), 0, "p"),
            Snapshot("s", "h", (), 0, "p", unobservable=("provider_audit",)),
        ]
    )
    stage = Staging(snapshot_fn=lambda: next(snaps), catalog=CATALOG).begin()
    assert stage.abort() is False
    assert "unobservable:provider_audit" in stage.reasons


def test_staging_refuses_to_commit_a_non_stageable_effect():
    stage = Staging(snapshot_fn=lambda: Snapshot("s", "h", (), 0, "p"), catalog=CATALOG).begin()
    with pytest.raises(StagingViolation):
        stage.commit(["READ_EXTERNAL", "WRITE_IRREVERSIBLE"])


def test_kill_switch_stops_every_dispatch():
    reg = Registry(name="r")
    reg.add(_artifact(_program()))
    reg.kill_switch = True
    disp = Dispatcher(registry=reg, catalog=CATALOG, mode=DispatchMode.LIVE)
    decision = disp.decide(
        compatibility_key=MANIFEST.compatibility_key(),
        partition={"tenant_partition": "t1"},
        entry_state={"key": "k1"},
        context={"model": "m1", "tenant_partition": "t1"},
        executor=_World().execute,
    )
    assert decision.outcome.value == "BASELINE"
    assert "no_artifact" in decision.reasons


def test_unsigned_artifact_is_not_resolvable_in_a_signed_registry():
    reg = Registry(name="r", signing_key=b"k")
    art = _artifact(_program())
    reg.add(art)
    assert reg.resolve(MANIFEST.compatibility_key(), {"tenant_partition": "t1"})
    art.signature = "deadbeef"
    assert not reg.resolve(MANIFEST.compatibility_key(), {"tenant_partition": "t1"})


def test_shadow_mode_never_executes_the_program():
    world = _World()
    reg = Registry(name="r")
    reg.add(_artifact(_program()))
    disp = Dispatcher(registry=reg, catalog=CATALOG, mode=DispatchMode.SHADOW)
    decision = disp.decide(
        compatibility_key=MANIFEST.compatibility_key(),
        partition={"tenant_partition": "t1"},
        entry_state={"key": "k1"},
        context={"model": "m1", "tenant_partition": "t1"},
        executor=world.execute,
    )
    assert decision.shadow
    assert decision.outcome.value == "BASELINE"
    assert world.quota == {}
    assert disp.telemetry.shadow_would_dispatch == 1


def test_shadow_lifecycle_is_visible_only_to_shadow_dispatch():
    world = _World()
    art = _artifact(_program())
    art.lifecycle = Lifecycle.SHADOW
    reg = Registry(name="r")
    reg.add(art)

    shadow = Dispatcher(registry=reg, catalog=CATALOG, mode=DispatchMode.SHADOW)
    shadow_decision = shadow.decide(
        compatibility_key=MANIFEST.compatibility_key(),
        partition={"tenant_partition": "t1"},
        entry_state={"key": "k1"},
        context={"model": "m1", "tenant_partition": "t1"},
        executor=world.execute,
    )
    assert shadow_decision.shadow
    assert shadow_decision.artifact is art

    live = Dispatcher(registry=reg, catalog=CATALOG, mode=DispatchMode.LIVE)
    live_decision = live.decide(
        compatibility_key=MANIFEST.compatibility_key(),
        partition={"tenant_partition": "t1"},
        entry_state={"key": "k1"},
        context={"model": "m1", "tenant_partition": "t1"},
        executor=world.execute,
    )
    assert live_decision.reasons == ("no_artifact",)
    assert world.quota == {}


def test_quota_attested_live_region_requires_a_reversibility_snapshot():
    world = _World()
    reg = Registry(name="r")
    reg.add(_artifact(_program(second_tool="q.metered")))
    disp = Dispatcher(registry=reg, catalog=CATALOG, mode=DispatchMode.LIVE)
    decision = disp.decide(
        compatibility_key=MANIFEST.compatibility_key(),
        partition={"tenant_partition": "t1"},
        entry_state={"key": "k1"},
        context={"model": "m1", "tenant_partition": "t1"},
        executor=world.execute,
    )
    assert decision.outcome.value == "BASELINE"
    assert decision.reasons == ("missing_reversibility_snapshot",)
    assert world.quota == {}


def test_off_mode_is_a_no_op():
    reg = Registry(name="r")
    reg.add(_artifact(_program()))
    disp = Dispatcher(registry=reg, catalog=CATALOG, mode=DispatchMode.OFF)
    decision = disp.decide(
        compatibility_key=MANIFEST.compatibility_key(),
        partition={"tenant_partition": "t1"},
        entry_state={"key": "k1"},
        context={"model": "m1", "tenant_partition": "t1"},
    )
    assert decision.reasons == ("mode_off",)
    assert decision.overhead_ms == 0.0
