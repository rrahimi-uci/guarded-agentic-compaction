"""Mutation tests: a drifted workflow must invalidate its artifacts.

Real teams edit prompts weekly. If artifacts are treated as long-lived assets, a
touch-up silently decays coverage to zero — silently and *correctly*, because failing
closed produces no error (proposal §6.4). These tests assert the invalidation actually
happens, for every component of the compatibility key, and that the registry diff makes
the decay visible.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from agent_compaction.registry.lifecycle import expire_due, invalidated_by_drift, rollback
from agent_compaction.registry.store import Registry
from agent_compaction.runtime.dispatch import DispatchMode, Dispatcher
from agent_compaction.schema.artifacts import Artifact, Gate, GateModel, HardGuard, Lifecycle, Verifier
from agent_compaction.schema.effects import EffectCatalog
from agent_compaction.schema.traces import ExecutionManifest
from agent_compaction.grc.dsl import Expr
from agent_compaction.grc.program import CallStep, Program

CATALOG = EffectCatalog.from_dict(
    {
        "version": 1,
        "name": "mut",
        "tools": {
            "r.read": {
                "effect": "READ_EXTERNAL",
                "capabilities": ["speculatable", "replayable", "cacheable"],
                "resource": "r",
            }
        },
    }
)

BASE = ExecutionManifest(
    manifest_id="m1",
    commit="c1",
    model="model-1",
    prompt_hash="#p1",
    tools_hash="#t1",
    policy_hash="#pol1",
    guardrail_hash="#g1",
    effect_catalog_version=CATALOG.catalog_version,
    entry_contract_version="v1",
)


def _artifact(manifest: ExecutionManifest = BASE) -> Artifact:
    program = Program(
        theta=("key",),
        steps=[CallStep(var="a", tool="r.read", args={"key": Expr("z.key", ())})],
        outputs={"a": Expr("a", ())},
        removed_requests=2.0,
        tools=("r.read",),
    )
    return Artifact(
        artifact_id="art",
        name="mut.region@1",
        program=program,
        guard=HardGuard(
            manifest_pins={
                "model": manifest.model,
                "prompt_hash": manifest.prompt_hash,
                "tools_hash": manifest.tools_hash,
                "policy_hash": manifest.policy_hash,
                "guardrail_hash": manifest.guardrail_hash,
                "effect_catalog_version": manifest.effect_catalog_version,
                "entry_contract_version": manifest.entry_contract_version,
            },
            isolation={"tenant_partition": "t1"},
        ),
        verifier=Verifier(allowed_effects=("READ_EXTERNAL",)),
        gate=Gate(model=GateModel(bias=-6.0), threshold=0.5),
        manifest=manifest,
        compatibility_key=manifest.compatibility_key(),
        partition={"tenant_partition": "t1"},
        lifecycle=Lifecycle.ACTIVE,
    )


@pytest.mark.parametrize(
    "field_name,new_value",
    [
        ("model", "model-2"),
        ("prompt_hash", "#p2"),
        ("tools_hash", "#t2"),
        ("policy_hash", "#pol2"),
        ("guardrail_hash", "#g2"),
        ("effect_catalog_version", "mut@2#deadbeef"),
        ("entry_contract_version", "v2"),
        ("commit", "c2"),
        ("sdk_version", "sdk-2"),
        ("tracer_version", "tracer-2"),
    ],
)
def test_every_compatibility_component_invalidates_the_artifact(field_name, new_value):
    art = _artifact()
    drifted = replace(BASE, **{field_name: new_value})
    assert invalidated_by_drift(art, drifted.compatibility_key())

    reg = Registry(name="r")
    reg.add(art)
    disp = Dispatcher(registry=reg, catalog=CATALOG, mode=DispatchMode.LIVE)
    decision = disp.decide(
        compatibility_key=drifted.compatibility_key(),
        partition={"tenant_partition": "t1"},
        entry_state={"key": "k"},
        context={field_name: new_value, "tenant_partition": "t1"},
        executor=lambda t, a: {"ok": True},
    )
    assert decision.outcome.value == "BASELINE"
    assert "no_artifact" in decision.reasons


def test_a_demoted_catalog_entry_stops_dispatch_at_execution_time():
    """The facade re-checks the catalog at execution time, not only at compile time."""

    art = _artifact()
    reg = Registry(name="r")
    reg.add(art)
    demoted = EffectCatalog.from_dict(
        {"version": 2, "name": "mut", "tools": {"r.read": {"effect": "WRITE_IRREVERSIBLE"}}}
    )
    disp = Dispatcher(registry=reg, catalog=demoted, mode=DispatchMode.LIVE)
    decision = disp.decide(
        compatibility_key=BASE.compatibility_key(),
        partition={"tenant_partition": "t1"},
        entry_state={"key": "k"},
        context={
            "model": BASE.model,
            "prompt_hash": BASE.prompt_hash,
            "tools_hash": BASE.tools_hash,
            "policy_hash": BASE.policy_hash,
            "guardrail_hash": BASE.guardrail_hash,
            "effect_catalog_version": BASE.effect_catalog_version,
            "entry_contract_version": BASE.entry_contract_version,
            "tenant_partition": "t1",
        },
        executor=lambda t, a: {"ok": True},
    )
    assert decision.outcome.value == "BASELINE"


def test_cross_partition_dispatch_is_impossible():
    reg = Registry(name="r")
    reg.add(_artifact())
    disp = Dispatcher(registry=reg, catalog=CATALOG, mode=DispatchMode.LIVE)
    decision = disp.decide(
        compatibility_key=BASE.compatibility_key(),
        partition={"tenant_partition": "t2"},  # a different tenant
        entry_state={"key": "k"},
        context={"model": BASE.model, "tenant_partition": "t2"},
        executor=lambda t, a: {"ok": True},
    )
    assert decision.outcome.value == "BASELINE"


def test_registry_diff_makes_coverage_decay_visible():
    old = Registry(name="v1")
    old.add(_artifact())
    new = Registry(name="v2")
    diff = new.diff(old)
    assert diff["lost"] == ["mut.region@1"]
    assert diff["gained"] == []


def test_expiry_retires_artifacts_because_they_are_build_outputs():
    reg = Registry(name="r")
    art = _artifact()
    art.expiry_day = "2026-06-30"
    reg.add(art)
    assert expire_due(reg, "2026-06-15") == []
    retired = expire_due(reg, "2026-07-01")
    assert retired and retired[0].lifecycle is Lifecycle.RETIRED
    assert reg.resolve(BASE.compatibility_key(), {"tenant_partition": "t1"}) == []


def test_rollback_returns_the_previous_registry_and_retires_the_active_one():
    prev = Registry(name="v0")
    cur = Registry(name="v1")
    cur.add(_artifact())
    cur.previous = prev
    back = rollback(cur, actor="oncall", reason="incident")
    assert back is prev
    assert cur.artifacts[0].lifecycle is Lifecycle.RETIRED
