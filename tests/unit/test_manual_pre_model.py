from __future__ import annotations

from agent_compaction.grc.composite import synthesize_composite
from agent_compaction.grc.dsl import Expr
from agent_compaction.grc.program import CallStep, Program
from agent_compaction.runtime.manual import ManualPreModelPlan, ManualPreModelRunner
from agent_compaction.schema.artifacts import GuardClause, HardGuard, Hull, OutputClause, Verifier
from agent_compaction.schema.effects import EffectCatalog
from agent_compaction.schema.traces import ExecutionManifest


def _catalog(*, record_effect: str = "READ_LOCAL", quota_attested: bool = False) -> EffectCatalog:
    return EffectCatalog.from_dict(
        {
            "name": "manual-plan-test",
            "version": 1,
            "tools": {
                "record.read": {
                    "effect": record_effect,
                    "capabilities": ["speculatable", "replayable", "batchable"],
                    "quota_attested": quota_attested,
                },
                "labels.read": {
                    "effect": "READ_LOCAL",
                    "capabilities": ["speculatable", "replayable", "batchable"],
                },
            },
        }
    )


def _manifest(catalog: EffectCatalog, *, prompt_hash: str = "prompt-v1") -> ExecutionManifest:
    return ExecutionManifest(
        manifest_id="manual-test",
        model="test-model",
        prompt_hash=prompt_hash,
        tools_hash="tools-v1",
        policy_hash="policy-v1",
        guardrail_hash="guard-v1",
        effect_catalog_version=catalog.catalog_version,
        entry_contract_version="record-id-v1",
        sdk_version="test-sdk",
        tracer_version="test-tracer",
    )


def _plan(catalog: EffectCatalog, manifest: ExecutionManifest) -> ManualPreModelPlan:
    program = Program(
        theta=("record_id",),
        steps=[
            CallStep(
                var="record",
                tool="record.read",
                args={"record_id": Expr("z.record_id", ())},
            ),
            CallStep(
                var="labels",
                tool="labels.read",
                args={"record_id": Expr("z.record_id", ())},
            ),
        ],
        outputs={"record": Expr("record", ()), "labels": Expr("labels", ())},
    )
    program = synthesize_composite(
        program,
        catalog,
        name="manual_record_bundle",
        projection={
            "record_id": "tool:record.read::record_id",
            "title": "tool:record.read::title",
            "labels": "tool:labels.read::names",
        },
        continuation_compatibility_key="continuation-v1",
    )
    pins = {
        "model": manifest.model,
        "prompt_hash": manifest.prompt_hash,
        "tools_hash": manifest.tools_hash,
        "policy_hash": manifest.policy_hash,
        "guardrail_hash": manifest.guardrail_hash,
        "effect_catalog_version": manifest.effect_catalog_version,
        "entry_contract_version": manifest.entry_contract_version,
    }
    return ManualPreModelPlan(
        name="manual-record-bundle-v1",
        program=program,
        source_compatibility_key=manifest.compatibility_key(),
        guard=HardGuard(
            manifest_pins=pins,
            clauses=[GuardClause("z.record_id", "int", Hull("interval", low=1))],
            allowed_effects=("READ_LOCAL",),
        ),
        verifier=Verifier(
            clauses=[
                OutputClause("record", "dict", provenance=("record.read",)),
                OutputClause("labels", "dict", provenance=("labels.read",)),
            ],
            allowed_effects=("READ_LOCAL",),
            call_counts=(2,),
        ),
        owner="test",
        approved_by="independent-reviewer",
    )


def _execute(tool: str, arguments: dict) -> dict:
    assert arguments == {"record_id": 7}
    if tool == "record.read":
        return {"record_id": 7, "title": "Verified"}
    if tool == "labels.read":
        return {"names": ["bug"]}
    raise AssertionError(tool)


def test_manual_pre_model_plan_executes_and_projects_one_observation() -> None:
    catalog = _catalog()
    manifest = _manifest(catalog)
    runner = ManualPreModelRunner(_plan(catalog, manifest), catalog, manifest)

    result = runner.execute_pre_model(
        {"record_id": 7},
        executor=_execute,
        continuation_compatibility_key="continuation-v1",
    )

    assert result.compacted
    assert result.record["construction"] == "manual"
    assert result.record["statistical_gate"] is False
    assert result.record["n_calls"] == 2
    assert result.record["exposed_calls"] == 1
    assert result.observations[0].result == {
        "labels": ["bug"],
        "record_id": 7,
        "title": "Verified",
    }


def test_manual_plan_rejects_manifest_and_continuation_drift_before_tools() -> None:
    catalog = _catalog()
    original = _manifest(catalog)
    calls: list[str] = []
    runner = ManualPreModelRunner(_plan(catalog, original), catalog, _manifest(catalog, prompt_hash="drift"))

    mismatch = runner.execute_pre_model(
        {"record_id": 7},
        executor=lambda tool, _args: calls.append(tool),
        continuation_compatibility_key="continuation-v1",
    )
    assert not mismatch.compacted
    assert mismatch.record["reasons"] == ["source_manifest_mismatch"]
    assert calls == []

    runner = ManualPreModelRunner(_plan(catalog, original), catalog, original)
    mismatch = runner.execute_pre_model(
        {"record_id": 7},
        executor=lambda tool, _args: calls.append(tool),
        continuation_compatibility_key="continuation-v2",
    )
    assert not mismatch.compacted
    assert mismatch.record["reasons"] == ["continuation_manifest_mismatch"]
    assert calls == []


def test_manual_plan_rejects_catalog_demotion_and_partial_region_before_tools() -> None:
    source_catalog = _catalog()
    manifest = _manifest(source_catalog)
    plan = _plan(source_catalog, manifest)
    calls: list[str] = []

    demoted = ManualPreModelRunner(plan, _catalog(record_effect="WRITE_REVERSIBLE"), manifest)
    result = demoted.execute_pre_model(
        {"record_id": 7},
        executor=lambda tool, _args: calls.append(tool),
        continuation_compatibility_key="continuation-v1",
    )
    assert not result.compacted
    assert any("forbidden_tool:record.read" in reason for reason in result.record["reasons"])
    assert calls == []

    runner = ManualPreModelRunner(plan, source_catalog, manifest)
    result = runner.execute_pre_model(
        {"record_id": 7},
        executor=lambda tool, _args: calls.append(tool),
        already_observed=("record.read",),
        continuation_compatibility_key="continuation-v1",
    )
    assert not result.compacted
    assert result.record["reasons"] == ["region_already_started"]
    assert calls == []


def test_manual_plan_fails_closed_on_tool_and_verifier_failures() -> None:
    catalog = _catalog()
    manifest = _manifest(catalog)
    runner = ManualPreModelRunner(_plan(catalog, manifest), catalog, manifest)

    tool_failure = runner.execute_pre_model(
        {"record_id": 7},
        executor=lambda _tool, _args: (_ for _ in ()).throw(TimeoutError("secret detail")),
        continuation_compatibility_key="continuation-v1",
    )
    assert not tool_failure.compacted
    assert tool_failure.observations == []
    assert tool_failure.record["reasons"] == ["interp_failed"]
    assert "secret detail" not in str(tool_failure.record)

    def invalid_labels(tool: str, arguments: dict) -> dict | list[str]:
        if tool == "record.read":
            return _execute(tool, arguments)
        return ["bug"]

    verifier_failure = runner.execute_pre_model(
        {"record_id": 7},
        executor=invalid_labels,
        continuation_compatibility_key="continuation-v1",
    )
    assert not verifier_failure.compacted
    assert verifier_failure.observations == []
    assert verifier_failure.record["reasons"] == ["verifier:type"]


def test_manual_plan_requires_reversibility_snapshot_for_quota_attested_reads() -> None:
    catalog = _catalog(quota_attested=True)
    manifest = _manifest(catalog)
    runner = ManualPreModelRunner(_plan(catalog, manifest), catalog, manifest)
    calls: list[str] = []

    result = runner.execute_pre_model(
        {"record_id": 7},
        executor=lambda tool, _args: calls.append(tool),
        continuation_compatibility_key="continuation-v1",
    )

    assert not result.compacted
    assert result.record["reasons"] == ["missing_reversibility_snapshot"]
    assert calls == []
