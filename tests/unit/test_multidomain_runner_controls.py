from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from guarded_agentic_compaction.benchmarking.commands import _execution_contract, benchmark_script
from guarded_agentic_compaction.benchmarking.protocol import ProtocolError
from guarded_agentic_compaction.benchmarking import FrozenProtocol, frozen_artifact_digest
from guarded_agentic_compaction.benchmarking.preflight import STATISTICAL_CONTRACT
from guarded_agentic_compaction.benchmarking import load_case_jsonl
from guarded_agentic_compaction.evaluation import BenchmarkRole, RunLedger
from guarded_agentic_compaction.registry.store import Registry
from guarded_agentic_compaction.schema.artifacts import Lifecycle
from paper.scripts.calibrate_grc_artifacts import calibrate_domain
from paper.scripts.calibrate_multidomain import calibrate
from guarded_agentic_compaction.portfolio import PortfolioDecision, PortfolioPolicy
from paper.scripts.analyze_multidomain import (
    _amortization,
    _load_effort,
    _validate_test_bindings,
    analyze,
)
from paper.scripts.multidomain_study import (
    _attempt_cost_ceiling,
    _build_action_spec,
    _evaluator_digest,
    _pilot_projection,
    _pricing,
)
from benchmarks.runtime import load_domain_runtime


def _manifest(**updates: object) -> dict[str, object]:
    result: dict[str, object] = {
        "schema": "agent-compaction-pricing/v1",
        "model": "model-a",
        "input_usd_per_million": 1.0,
        "cached_input_usd_per_million": 0.5,
        "output_usd_per_million": 2.0,
        "maximum_billable_input_tokens_per_request": 100_000,
        "output_token_limit_per_request": 2_000,
        "service_tier": "default",
        "revision": "2026-08-04",
        "source_url": "https://example.org/official-pricing",
        "retrieved_at": "2026-08-04T15:00:00Z",
    }
    result.update(updates)
    return result


def _write(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_freeze_and_live_runner_share_exact_pricing_identity(tmp_path: Path) -> None:
    path = _write(tmp_path / "pricing.json", _manifest())
    live = _pricing(path, "model-a")
    frozen = _execution_contract(path, "model-a")
    assert frozen["pricing_digest"] == live["sha256"]
    assert frozen["pricing_revision"] == live["revision"]
    assert frozen["service_tier"] == "default"
    assert frozen["maximum_billable_input_tokens_per_request"] == "100000"
    assert frozen["output_token_limit_per_request"] == "2000"
    assert _attempt_cost_ceiling(live, 2) == pytest.approx(0.208)


def test_repository_study_dispatch_is_allowlisted_and_works_from_checkout(
    monkeypatch,
) -> None:
    root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(root)
    assert benchmark_script(
        SimpleNamespace(
            script_name="prepare_macro_review.py", forwarded=["--help"]
        )
    ) == 0
    assert benchmark_script(
        SimpleNamespace(script_name="../outside.py", forwarded=[])
    ) == 2


def test_evaluator_identity_binds_retained_gold() -> None:
    root = Path(__file__).resolve().parents[2]
    pool = root / "paper/results/multidomain/preflight/hmda"
    cases = load_case_jsonl(pool / "cases.jsonl")
    runtime = load_domain_runtime(
        domain="hmda", pool_dir=pool, cases=cases, repository_root=root
    )
    original = _evaluator_digest("hmda", runtime)
    mutated_gold = json.loads(json.dumps(runtime.gold))
    first = cases[0].case_id
    mutated_gold[first]["action_taken"]["label"] = "drifted-gold"
    assert _evaluator_digest("hmda", replace(runtime, gold=mutated_gold)) != original


def test_grc_action_identity_binds_shadow_or_active_lifecycle() -> None:
    root = Path(__file__).resolve().parents[2]
    pool = root / "paper/results/multidomain/preflight/hmda"
    cases = load_case_jsonl(pool / "cases.jsonl")
    runtime = load_domain_runtime(
        domain="hmda", pool_dir=pool, cases=cases, repository_root=root
    )
    protocol = FrozenProtocol(
        study_id="study",
        seed=7,
        config_digest="config",
        source_digests={"hmda": cases[0].source_snapshot},
        group_roles={"hmda": {}},
        case_ids={"hmda": ()},
        lineage_digest="lineage",
        model="model-a",
        execution_contract={"service_tier": "default"},
    )
    registry = Registry(name="identity-test")
    shadow = _build_action_spec(
        domain="hmda",
        action="grc",
        protocol=protocol,
        runtime=runtime,
        model_name="model-a",
        registry=registry,
        grc_stage="shadow",
    )
    active = _build_action_spec(
        domain="hmda",
        action="grc",
        protocol=protocol,
        runtime=runtime,
        model_name="model-a",
        registry=registry,
        grc_stage="active",
    )
    assert shadow.version == "grc-shadow-v1"
    assert active.version == "grc-active-v1"
    assert shadow.digest != active.digest
    with pytest.raises(ValueError, match="shadow or active"):
        _build_action_spec(
            domain="hmda",
            action="grc",
            protocol=protocol,
            runtime=runtime,
            model_name="model-a",
            registry=registry,
        )


def test_pricing_rejects_model_drift_extra_fields_and_naive_time(tmp_path: Path) -> None:
    path = _write(tmp_path / "pricing.json", _manifest())
    with pytest.raises(ValueError, match="model"):
        _pricing(path, "model-b")
    _write(path, _manifest(unreviewed_note="not allowed"))
    with pytest.raises(ValueError, match="fields"):
        _pricing(path, "model-a")
    _write(path, _manifest(retrieved_at="2026-08-04T15:00:00"))
    with pytest.raises(ProtocolError, match="timezone"):
        _execution_contract(path, "model-a")


def _metrics(scale: float) -> dict[str, object]:
    return {
        "model_requests": 2,
        "input_tokens": int(800 * scale),
        "cached_input_tokens": 0,
        "output_tokens": int(200 * scale),
        "total_tokens": int(1000 * scale),
        "estimated_cost_usd": scale,
        "wall_latency_ms": 1000 * scale,
        "critical_path_ms": 900 * scale,
        "tool_calls": max(1, int(4 * scale)),
        "quality_contract_pass": True,
    }


def test_calibration_treats_empty_grc_registry_as_explicit_unavailable() -> None:
    groups = [f"g-{index}" for index in range(75)]
    protocol = FrozenProtocol(
        study_id="study",
        seed=7,
        config_digest="config",
        source_digests={"hmda": "sha256:" + "a" * 64},
        group_roles={
            "hmda": {group: BenchmarkRole.PORTFOLIO_CALIBRATION for group in groups}
        },
        case_ids={"hmda": tuple(f"case-{index}" for index in range(75))},
        lineage_digest="lineage",
        model="model-a",
    )
    complete = []
    unavailable = []
    for group in groups:
        for action, scale in (("baseline", 1.0), ("macro", 0.5)):
            complete.append(
                {
                    "schedule": {
                        "domain": "hmda",
                        "group_id": group,
                        "action": action,
                        "role": "portfolio_calibration",
                        "repeat": 0,
                    },
                    "metrics": _metrics(scale),
                }
            )
        unavailable.append(
            {
                "schedule": {
                    "domain": "hmda",
                    "group_id": group,
                    "action": "grc",
                    "role": "portfolio_calibration",
                    "repeat": 0,
                },
                "reason": "registry_contains_no_compiled_artifacts",
            }
        )
    policy, global_decision = calibrate(protocol, complete, unavailable)
    assert policy.select(protocol.family_key("hmda")).selected_action == "macro"
    # The global comparison is certified over all three domains (225 groups).
    # A one-domain fixture therefore has to abstain.
    assert global_decision.selected_action == "baseline"
    assert all(item.support_groups == 75 for item in global_decision.evidence)


def test_global_fixed_comparator_excludes_actions_unavailable_in_any_domain() -> None:
    domains = ("vulnerability", "sec", "hmda")
    roles = {
        domain: {
            f"{domain}-g-{index}": BenchmarkRole.PORTFOLIO_CALIBRATION
            for index in range(75)
        }
        for domain in domains
    }
    protocol = FrozenProtocol(
        study_id="study",
        seed=7,
        config_digest="config",
        source_digests={domain: "sha256:" + str(index) * 64 for index, domain in enumerate(domains, 1)},
        group_roles=roles,
        case_ids={
            domain: tuple(f"{domain}-case-{index}" for index in range(75))
            for domain in domains
        },
        lineage_digest="lineage",
        model="model-a",
    )
    complete = []
    unavailable = []
    for domain in domains:
        for group in roles[domain]:
            for action, scale in (("baseline", 1.0), ("macro", 0.5)):
                complete.append(
                    {
                        "schedule": {
                            "domain": domain,
                            "group_id": group,
                            "action": action,
                            "role": "portfolio_calibration",
                            "repeat": 0,
                        },
                        "metrics": _metrics(scale),
                    }
                )
            if domain == "hmda":
                unavailable.append(
                    {
                        "schedule": {
                            "domain": domain,
                            "group_id": group,
                            "action": "grc",
                            "role": "portfolio_calibration",
                            "repeat": 0,
                        },
                        "reason": "registry_contains_no_active_artifacts",
                    }
                )
            else:
                complete.append(
                    {
                        "schedule": {
                            "domain": domain,
                            "group_id": group,
                            "action": "grc",
                            "role": "portfolio_calibration",
                            "repeat": 0,
                        },
                        "metrics": _metrics(0.1),
                    }
                )
    _, global_decision = calibrate(protocol, complete, unavailable)
    assert global_decision.selected_action == "macro"
    assert [item.action for item in global_decision.evidence] == ["macro"]
    assert global_decision.evidence[0].support_groups == 225


def test_sealed_analysis_binds_policy_action_lock_and_action_identity() -> None:
    policy = PortfolioPolicy(
        decisions={"family": PortfolioDecision(selected_action="baseline", evidence=())},
        registered_families=("family",),
        overall_confidence=0.99,
        manifest_digest="protocol",
    )
    payload = {
        "action_lock_digest": "lock",
        "action_digests": {"hmda": {"baseline": "baseline-digest"}},
    }
    record = SimpleNamespace(
        event_type="execution_complete",
        payload={
            "schedule": {"domain": "hmda", "action": "baseline"},
            "action_lock_digest": "lock",
            "portfolio_policy_digest": policy.digest,
            "action_spec": {"action_digest": "baseline-digest"},
        },
    )
    _validate_test_bindings(payload, policy, [record])
    record.payload["action_spec"]["action_digest"] = "drifted"
    with pytest.raises(ValueError, match="action identity"):
        _validate_test_bindings(payload, policy, [record])


def test_sealed_analysis_recomputes_complete_three_domain_design(monkeypatch) -> None:
    monkeypatch.setitem(STATISTICAL_CONTRACT, "bootstrap_resamples", 100)
    domains = ("vulnerability", "sec", "hmda")
    group_roles = {
        domain: {
            f"{domain}-g-{index}": BenchmarkRole.TEST for index in range(100)
        }
        for domain in domains
    }
    protocol = FrozenProtocol(
        study_id="study",
        seed=11,
        config_digest="config",
        source_digests={domain: "sha256:" + str(index) * 64 for index, domain in enumerate(domains, 1)},
        group_roles=group_roles,
        case_ids={domain: tuple() for domain in domains},
        lineage_digest="lineage",
        model="model-a",
    )
    decisions = {
        protocol.family_key(domain): PortfolioDecision(
            selected_action="baseline", evidence=()
        )
        for domain in domains
    }
    policy = PortfolioPolicy(
        decisions=decisions,
        registered_families=tuple(decisions),
        overall_confidence=0.99,
        manifest_digest=protocol.digest,
    )
    action_digests = {
        domain: {action: f"{domain}-{action}" for action in ("baseline", "grc", "macro")}
        for domain in domains
    }
    policy_payload = {
        "schema": "agent-compaction-frozen-portfolio/v1",
        "frozen_at": "2026-08-04T10:00:00Z",
        "protocol_digest": protocol.digest,
        "policy_digest": policy.digest,
        "action_lock_digest": "active-lock",
        "action_digests": action_digests,
        "policy": policy.as_dict(),
        "best_global_fixed_decision": PortfolioDecision(
            selected_action="baseline", evidence=()
        ).as_dict(),
    }
    policy_payload["portfolio_artifact_digest"] = frozen_artifact_digest(
        policy_payload, digest_field="portfolio_artifact_digest"
    )
    records = []
    for domain in domains:
        for index, group in enumerate(group_roles[domain]):
            repeats = range(3) if index < 20 else range(1)
            for repeat in repeats:
                for action in ("baseline", "grc", "macro"):
                    payload = {
                        "schedule": {
                            "domain": domain,
                            "group_id": group,
                            "action": action,
                            "role": "test",
                            "repeat": repeat,
                        },
                        "metrics": _metrics(1.0),
                        "answer": {"stable": True},
                        "tool_sequence": [action],
                        "action_lock_digest": "active-lock",
                        "portfolio_policy_digest": policy.digest,
                        "action_spec": {
                            "action_digest": action_digests[domain][action]
                        },
                    }
                    records.append(
                        SimpleNamespace(
                            run_id=protocol.digest,
                            event_type="execution_complete",
                            payload=payload,
                            created_at="2026-08-04T11:00:00Z",
                        )
                    )
    effort = {
        "revision": "test",
        "hourly_rate_usd": 0.0,
        "recurring_cost_usd_per_1000_executions": 0.0,
        "traffic_horizons": [1000],
        "components": [],
    }
    result = analyze(
        protocol,
        policy_payload,
        records,
        [dict(record.payload) for record in records],
        effort,
        "effort-digest",
    )
    assert len(result["quality_rows"]) == 6
    assert len(result["endpoint_rows"]) == 54
    assert len(result["determinism_rows"]) == 9
    assert result["portfolio_comparison"]["baseline"]["groups"] == 300
    json.dumps(result, allow_nan=False)


def test_empty_grc_registry_calibrates_to_explicit_unavailable_registry(
    tmp_path: Path,
) -> None:
    groups = [f"g-{index}" for index in range(100)]
    protocol = FrozenProtocol(
        study_id="study",
        seed=7,
        config_digest="config",
        source_digests={"hmda": "sha256:" + "a" * 64},
        group_roles={
            "hmda": {group: BenchmarkRole.ARTIFACT_CALIBRATION for group in groups}
        },
        case_ids={"hmda": tuple(f"case-{index}" for index in range(100))},
        lineage_digest="lineage",
        model="model-a",
    )
    registry_dir = tmp_path / "shadow"
    Registry(
        name="empty-shadow", active_stages=(Lifecycle.SHADOW,)
    ).save(registry_dir)
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = RunLedger(ledger_path)
    for group in groups:
        schedule = {
            "domain": "hmda",
            "group_id": group,
            "action": "baseline",
            "role": "artifact_calibration",
            "repeat": 0,
        }
        ledger.append(
            run_id=protocol.digest,
            event_id=f"{group}:baseline",
            event_type="execution_complete",
            payload={
                "schedule": schedule,
                "metrics": {"quality_contract_pass": True},
                "action_lock_digest": "shadow-lock",
                "action_spec": {"action_digest": "baseline-action"},
            },
        )
        ledger.append(
            run_id=protocol.digest,
            event_id=f"{group}:grc",
            event_type="execution_unavailable",
            payload={
                "schedule": {**schedule, "action": "grc"},
                "reason": "registry_contains_no_compiled_artifacts",
                "provider_calls_executed": 0,
                "action_lock_digest": "shadow-lock",
            },
        )
    report = calibrate_domain(
        domain="hmda",
        protocol=protocol,
        ledger_paths=[ledger_path],
        registry_path=registry_dir,
        output_dir=tmp_path / "calibrated",
        approved_by="reviewer@example.org",
        job_identity="optimizer",
        expiry_day="2099-01-01",
    )
    assert report["unavailable"] is True
    assert report["active_artifacts"] == 0
    restored = Registry.load(tmp_path / "calibrated/hmda")
    assert restored.active_stages == (Lifecycle.ACTIVE,)


def test_pilot_projection_uses_frozen_schedule_and_marks_grc_unavailable() -> None:
    records = []
    for action in ("baseline", "macro"):
        for index in range(12):
            records.append(
                SimpleNamespace(
                    event_type="execution_complete",
                    payload={
                        "schedule": {
                            "role": "reserve",
                            "domain": "hmda",
                            "action": action,
                        },
                        "metrics": {"estimated_cost_usd": 0.1},
                    },
                )
            )
    projection = _pilot_projection(
        records,
        {("hmda", "grc"): "registry_contains_no_compiled_artifacts"},
        ("hmda",),
    )
    assert projection["available"] is True
    assert projection["projected_inference_cost_usd"] == pytest.approx(60.0)
    assert projection["projected_inference_cost_with_contingency_usd"] == pytest.approx(75.0)


def test_effort_manifest_produces_explicit_break_even_accounting(tmp_path: Path) -> None:
    effort_path = _write(
        tmp_path / "effort.json",
        {
            "schema": "agent-compaction-construction-effort/v1",
            "revision": "reviewed-v1",
            "hourly_rate_usd": 100.0,
            "recurring_cost_usd_per_1000_executions": 10.0,
            "traffic_horizons": [1000, 10000],
            "components": [
                {
                    "name": "macro_authoring",
                    "domain": "hmda",
                    "hours": 2.0,
                    "direct_cost_usd": 5.0,
                    "notes": "measured author time",
                }
            ],
            "recorded_by": "researcher@example.org",
            "recorded_at": "2026-08-04T15:00:00Z",
        },
    )
    effort, digest = _load_effort(effort_path)
    result = _amortization(
        effort,
        digest,
        {"mean_estimated_cost_usd": 0.10},
        {"mean_estimated_cost_usd": 0.05},
    )
    assert result["fixed_construction_cost_usd"] == pytest.approx(205.0)
    assert result["net_savings_usd_per_execution_after_recurring_cost"] == pytest.approx(0.04)
    assert result["break_even_executions"] == 5125
