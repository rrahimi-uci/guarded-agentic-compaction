from __future__ import annotations

import json

from guarded_agentic_compaction.grc.composite import synthesize_composite
from guarded_agentic_compaction.grc.dsl import Expr
from guarded_agentic_compaction.grc.program import CallStep, Program
from guarded_agentic_compaction.registry.store import Registry
from guarded_agentic_compaction.runtime.dispatch import DispatchMode, Dispatcher
from guarded_agentic_compaction.runtime.facade import FacadeMode, Recording, ToolFacade
from guarded_agentic_compaction.runtime.runner import CompactingRunner
from guarded_agentic_compaction.schema.artifacts import (
    Artifact,
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
        "name": "composite-test",
        "version": 1,
        "tools": {
            "records.read": {
                "effect": "READ_LOCAL",
                "capabilities": ["speculatable", "replayable", "cacheable", "batchable"],
            },
            "comments.read": {
                "effect": "READ_LOCAL",
                "capabilities": ["speculatable", "replayable", "cacheable", "batchable"],
                "argument_semantics": {
                    "limit": {
                        "relation": "monotone_superset",
                        "operations": [
                            {
                                "kind": "clamp_int",
                                "admissible_minimum": 3,
                                "minimum": 3,
                                "maximum": 3,
                            }
                        ],
                        "notes": "The registered task consumes at most three comments.",
                    }
                },
            },
        },
    }
)

MANIFEST = ExecutionManifest(
    manifest_id="composite",
    model="model",
    effect_catalog_version=CATALOG.catalog_version,
)


def _program(
    *,
    missing_projection: bool = False,
    continuation_key: str = "",
) -> Program:
    base = Program(
        theta=("record_id",),
        steps=[
            CallStep(
                var="record",
                tool="records.read",
                args={"record_id": Expr("z.record_id", ())},
            ),
            CallStep(
                var="comments",
                tool="comments.read",
                args={
                    "record_id": Expr("z.record_id", ()),
                    "limit": Expr("record.requested_limit", ()),
                },
            ),
        ],
        outputs={"record": Expr("record", ()), "comments": Expr("comments", ())},
        removed_requests=2,
    )
    return synthesize_composite(
        base,
        CATALOG,
        name="read_record_bundle",
        projection={
            "title": "tool:records.read::title",
            "comments": (
                "tool:comments.read::missing"
                if missing_projection
                else "tool:comments.read::items"
            ),
        },
        continuation_compatibility_key=continuation_key,
    )


def _artifact(program: Program) -> Artifact:
    return Artifact(
        artifact_id="composite-1",
        name="composite-test",
        program=program,
        guard=HardGuard(),
        verifier=Verifier(
            clauses=[
                OutputClause("record", "dict", provenance=("records.read",)),
                OutputClause("comments", "dict", provenance=("comments.read",)),
            ],
            allowed_effects=("READ_LOCAL",),
            call_counts=(2,),
        ),
        gate=Gate(model=GateModel(bias=-6), threshold=0.5),
        manifest=MANIFEST,
        compatibility_key=MANIFEST.compatibility_key(),
        lifecycle=Lifecycle.ACTIVE,
    )


def _execute(tool: str, arguments: dict) -> dict:
    if tool == "records.read":
        return {
            "title": "Verified title",
            "requested_limit": 100,
            "unused_body": "x" * 1000,
        }
    if tool == "comments.read":
        assert arguments["limit"] == 3
        return {"items": ["one", "two", "three"], "unused": "y" * 1000}
    raise AssertionError(tool)


def test_semantic_argument_contract_is_deterministic_and_recording_aware() -> None:
    assert CATALOG.canonicalize_arguments("comments.read", {"limit": 100}) == {"limit": 3}
    assert CATALOG.arguments_equivalent(
        "comments.read", {"limit": 100}, {"limit": 3}
    )
    assert not CATALOG.arguments_equivalent(
        "comments.read", {"limit": 1}, {"limit": 3}
    )
    recording = Recording()
    recording.add("comments.read", {"record_id": 7, "limit": 100}, {"items": ["a"]})
    facade = ToolFacade(catalog=CATALOG, mode=FacadeMode.RECORDED, recording=recording)
    assert facade.call("comments.read", {"record_id": 7, "limit": 3}) == {"items": ["a"]}
    assert facade.calls == [("comments.read", {"record_id": 7, "limit": 3})]

    alias_catalog = EffectCatalog.from_dict(
        {
            "tools": {
                "records.read": {
                    "effect": "READ_LOCAL",
                    "capabilities": ["speculatable", "replayable"],
                    "argument_semantics": {
                        "state": {
                            "operations": [
                                {"kind": "aliases", "aliases": {"opened": "open"}}
                            ]
                        }
                    },
                }
            }
        }
    )
    assert alias_catalog.canonicalize_arguments(
        "records.read", {"state": "opened"}
    ) == {"state": "open"}


def test_composite_round_trip_projects_one_interface_and_keeps_internal_provenance() -> None:
    artifact = _artifact(_program())
    restored = Artifact.from_dict(json.loads(json.dumps(artifact.to_dict())))
    assert restored.program is not None and restored.program.composite is not None
    assert restored.program.composite.name == "read_record_bundle"

    registry = Registry(name="composite")
    registry.add(restored)
    dispatcher = Dispatcher(registry=registry, catalog=CATALOG, mode=DispatchMode.LIVE)
    decision = dispatcher.decide(
        compatibility_key=MANIFEST.compatibility_key(),
        partition={},
        entry_state={"record_id": 7},
        context={"model": "model"},
        executor=_execute,
        require_pre_model_composite=True,
    )

    assert decision.compacted
    assert len(decision.calls) == 2
    assert decision.record["exposed_calls"] == 1
    assert decision.projected_outputs == {
        "comments": ["one", "two", "three"],
        "title": "Verified title",
    }
    assert decision.projected_provenance == {
        "comments": ("comments.read",),
        "title": ("records.read",),
    }


def test_pre_model_runner_emits_one_projected_observation() -> None:
    registry = Registry(name="pre-model")
    registry.add(_artifact(_program()))
    runner = CompactingRunner(
        dispatcher=Dispatcher(registry=registry, catalog=CATALOG, mode=DispatchMode.LIVE),
        catalog=CATALOG,
        manifest=MANIFEST,
    )
    result = runner.execute_pre_model({"record_id": 7}, executor=_execute)
    assert result.compacted
    assert len(result.observations) == 1
    observation = result.observations[0]
    assert observation.tool == "read_record_bundle"
    assert observation.args == {"record_id": 7}
    assert observation.result["title"] == "Verified title"
    assert result.record["n_calls"] == 2
    assert result.record["exposed_calls"] == 1


def test_projection_failure_falls_back_before_release() -> None:
    registry = Registry(name="projection-failure")
    registry.add(_artifact(_program(missing_projection=True)))
    dispatcher = Dispatcher(registry=registry, catalog=CATALOG, mode=DispatchMode.LIVE)
    decision = dispatcher.decide(
        compatibility_key=MANIFEST.compatibility_key(),
        partition={},
        entry_state={"record_id": 7},
        context={"model": "model"},
        executor=_execute,
        require_pre_model_composite=True,
    )
    assert not decision.compacted
    assert decision.reasons == ("composite_projection_failed",)
    assert dispatcher.telemetry.verifier_failures == {"composite_projection": 1}


def test_composite_packaging_does_not_change_ordinary_grc_dispatch() -> None:
    registry = Registry(name="ordinary-grc")
    registry.add(_artifact(_program(missing_projection=True)))
    dispatcher = Dispatcher(registry=registry, catalog=CATALOG, mode=DispatchMode.LIVE)
    decision = dispatcher.decide(
        compatibility_key=MANIFEST.compatibility_key(),
        partition={},
        entry_state={"record_id": 7},
        context={"model": "model"},
        executor=_execute,
    )

    assert decision.compacted
    assert decision.projected_outputs == {}
    assert decision.record["exposed_calls"] == 2
    assert decision.record["composite"] is None


def test_pre_model_composite_requires_exact_continuation_manifest() -> None:
    registry = Registry(name="continuation-manifest")
    registry.add(_artifact(_program(continuation_key="expected-continuation")))
    calls: list[str] = []

    def execute(tool: str, arguments: dict) -> dict:
        calls.append(tool)
        return _execute(tool, arguments)

    runner = CompactingRunner(
        dispatcher=Dispatcher(registry=registry, catalog=CATALOG, mode=DispatchMode.LIVE),
        catalog=CATALOG,
        manifest=MANIFEST,
    )
    result = runner.execute_pre_model(
        {"record_id": 7},
        executor=execute,
        continuation_compatibility_key="different-continuation",
    )

    assert not result.compacted
    assert result.observations == []
    assert result.record["reasons"] == ["continuation_manifest_mismatch"]
    assert calls == []


def test_pre_model_composite_validates_public_arguments_before_tools() -> None:
    registry = Registry(name="missing-public-input")
    registry.add(_artifact(_program()))
    calls: list[str] = []
    runner = CompactingRunner(
        dispatcher=Dispatcher(registry=registry, catalog=CATALOG, mode=DispatchMode.LIVE),
        catalog=CATALOG,
        manifest=MANIFEST,
    )
    result = runner.execute_pre_model(
        {},
        executor=lambda tool, arguments: calls.append(tool),
    )

    assert not result.compacted
    assert result.record["reasons"] == ["composite_input_failed"]
    assert calls == []


def test_tampered_composite_contract_is_rejected_before_execution() -> None:
    artifact = _artifact(_program())
    assert artifact.program is not None and artifact.program.composite is not None
    artifact.program.composite.inputs = ("record_id", "private_token")
    registry = Registry(name="tampered-composite")
    registry.add(artifact)
    calls: list[str] = []
    dispatcher = Dispatcher(registry=registry, catalog=CATALOG, mode=DispatchMode.LIVE)
    decision = dispatcher.decide(
        compatibility_key=MANIFEST.compatibility_key(),
        partition={},
        entry_state={"record_id": 7, "private_token": "must-not-leak"},
        context={"model": "model"},
        executor=lambda tool, arguments: calls.append(tool),
    )

    assert not decision.compacted
    assert decision.reasons == ("invalid_artifact:composite_inputs",)
    assert calls == []
