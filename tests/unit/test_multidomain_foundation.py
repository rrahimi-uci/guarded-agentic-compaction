"""Provider-free tests for the multidomain evidence substrate."""

from __future__ import annotations

import json

import pytest

from guarded_agentic_compaction.evaluation import (
    BenchmarkCase,
    BenchmarkRole,
    BinaryPair,
    CanonicalMetrics,
    FrozenStudy,
    LedgerConflict,
    OracleResult,
    RunLedger,
    exact_paired_binary_noninferiority,
    paired_portfolio_observation,
)
from guarded_agentic_compaction.portfolio import (
    PortfolioPolicy,
    SelectionConfig,
    bonferroni_family_confidence,
    portfolio_risk_upper,
    select_portfolio_action,
)


def _metrics(*, quality: bool = True, ratio: float = 1.0) -> CanonicalMetrics:
    return CanonicalMetrics(
        model_requests=2,
        input_tokens=int(800 * ratio),
        cached_input_tokens=0,
        output_tokens=int(200 * ratio),
        total_tokens=int(1000 * ratio),
        estimated_cost_usd=1.0 * ratio,
        wall_latency_ms=1000.0 * ratio,
        critical_path_ms=900.0 * ratio,
        tool_calls=max(1, int(4 * ratio)),
        quality_contract_pass=quality,
        provider_trace_id="trace-redacted-id",
    )


def test_benchmark_case_is_detached_deeply_immutable_and_digest_stable() -> None:
    source = {"package": {"name": "demo"}, "aliases": ["A", "B"]}
    case = BenchmarkCase(
        case_id="vuln-1",
        group_id="PyPI:demo",
        domain="vulnerability",
        source_snapshot="sha256:" + "a" * 64,
        inputs=source,
    )
    original_digest = case.input_digest
    source["package"]["name"] = "changed"
    source["aliases"].append("C")
    assert case.as_dict()["inputs"] == {
        "aliases": ["A", "B"],
        "package": {"name": "demo"},
    }
    assert case.input_digest == original_digest
    with pytest.raises(TypeError):
        case.inputs["package"]["name"] = "mutate"


def test_case_oracle_and_study_reject_ambiguous_contracts() -> None:
    with pytest.raises(ValueError, match="finite JSON"):
        BenchmarkCase("c", "g", "sec", "s", {"value": float("nan")})
    with pytest.raises(ValueError, match="must not be empty"):
        OracleResult("c", True, {})
    with pytest.raises(ValueError, match="passed must equal"):
        OracleResult("c", True, {"value": False})

    roles = {"issuer-1": BenchmarkRole.TEST}
    study = FrozenStudy(
        study_id="study",
        config_digest="config-a",
        source_digests={"sec": "source-a"},
        group_roles=roles,
        model="gpt-test",
    )
    changed_split = FrozenStudy(
        study_id="study",
        config_digest="config-a",
        source_digests={"sec": "source-a"},
        group_roles={"issuer-1": BenchmarkRole.PORTFOLIO_CALIBRATION},
        model="gpt-test",
    )
    assert study.role_for("issuer-1") is BenchmarkRole.TEST
    assert study.compatibility_key != changed_split.compatibility_key


def test_canonical_mapper_rejects_alias_conflict_and_incomplete_totals() -> None:
    values = {
        "requests": 2,
        "input_tokens": 8,
        "cached_input_tokens": 2,
        "output_tokens": 2,
        "total_tokens": 10,
        "dollars": None,
        "latency_ms": 11,
        "critical_path_ms": 9,
        "tool_calls": 3,
        "exact_pass": True,
    }
    measured = CanonicalMetrics.from_live_mapping(values)
    assert measured.estimated_cost_usd is None
    assert measured.portfolio_metrics() == {
        "wall_latency_ms": 11.0,
        "total_tokens": 10.0,
        "tool_calls": 3.0,
    }
    with pytest.raises(ValueError, match="conflicting aliases"):
        CanonicalMetrics.from_live_mapping({**values, "requests": 3, "model_requests": 2})
    with pytest.raises(ValueError, match="critical_path_ms"):
        CanonicalMetrics.from_live_mapping(
            {key: value for key, value in values.items() if key != "critical_path_ms"}
        )
    with pytest.raises(ValueError, match="total_tokens must equal"):
        CanonicalMetrics.from_live_mapping({**values, "total_tokens": 11})


def test_canonical_pair_maps_to_strict_portfolio_observation() -> None:
    observation = paired_portfolio_observation(
        group_id="g1",
        action="grc",
        baseline=_metrics(),
        candidate=_metrics(ratio=0.5),
        compatibility_key="family-a",
    )
    assert observation.quality_violation is False
    assert observation.utility(SelectionConfig().weights) > 0
    incomplete = paired_portfolio_observation(
        group_id="g2",
        action="grc",
        baseline=CanonicalMetrics.from_live_mapping(
            {
                "requests": 1,
                "input_tokens": 8,
                "output_tokens": 2,
                "total_tokens": 10,
                "latency_ms": 10,
                "critical_path_ms": 9,
                "tool_calls": 1,
                "exact_pass": True,
            }
        ),
        candidate=_metrics(ratio=0.5),
        compatibility_key="family-a",
    )
    with pytest.raises(ValueError, match="estimated_cost_usd"):
        incomplete.utility(SelectionConfig().weights)


def test_exact_paired_noninferiority_uses_unique_groups() -> None:
    result = exact_paired_binary_noninferiority(
        [BinaryPair(f"g{i}", True, True) for i in range(100)],
        margin=0.05,
        confidence=0.99,
    )
    assert result.passed
    assert result.lower_bound == pytest.approx(-0.045007413978564004)

    one_loss = exact_paired_binary_noninferiority(
        [BinaryPair(f"g{i}", True, i != 0) for i in range(100)],
        margin=0.05,
        confidence=0.99,
    )
    assert not one_loss.passed
    assert one_loss.candidate_losses == 1
    with pytest.raises(ValueError, match="pseudo-replication"):
        exact_paired_binary_noninferiority(
            [BinaryPair("same", True, True), BinaryPair("same", True, True)],
            margin=0.05,
        )


def test_run_ledger_is_idempotent_hash_chained_and_detects_corruption(tmp_path) -> None:
    ledger = RunLedger(tmp_path / "run.jsonl")
    first = ledger.append(
        run_id="run-1", event_id="case-1:baseline", event_type="completed", payload={"ok": True}
    )
    assert ledger.append(
        run_id="run-1", event_id="case-1:baseline", event_type="completed", payload={"ok": True}
    ) == first
    second = ledger.append(
        run_id="run-1", event_id="case-1:grc", event_type="completed", payload={"ok": True}
    )
    assert second.previous_hash == first.record_hash
    assert ledger.validate()["records"] == 2
    with pytest.raises(LedgerConflict, match="reused"):
        ledger.append(
            run_id="run-1", event_id="case-1:grc", event_type="completed", payload={"ok": False}
        )

    raw = ledger.path.read_text(encoding="utf-8")
    ledger.path.write_text(raw.replace('"ok":true', '"ok":false', 1), encoding="utf-8")
    with pytest.raises(LedgerConflict, match="hash"):
        ledger.validate()
    with pytest.raises(ValueError, match="non-empty string"):
        RunLedger(tmp_path / "invalid.jsonl").append(
            run_id=1, event_id="event", event_type="completed", payload={}
        )


def test_portfolio_risk_numbers_match_frozen_plan() -> None:
    family_confidence = bonferroni_family_confidence(0.99, n_families=3)
    assert portfolio_risk_upper(
        0, 75, selection_confidence=family_confidence, n_actions=2
    ) == pytest.approx(0.09020352452572422)
    assert portfolio_risk_upper(
        1, 75, selection_confidence=family_confidence, n_actions=2
    ) == pytest.approx(0.11896657733300747)
    assert bonferroni_family_confidence(0.97, n_families=3) == pytest.approx(0.99)


def test_family_policy_roundtrip_unknown_family_and_review_gate() -> None:
    config = SelectionConfig(
        confidence=0.99,
        minimum_groups=75,
        expected_compatibility_key="frozen-family",
    )
    observations = [
        paired_portfolio_observation(
            group_id=f"g{i}",
            action="macro",
            baseline=_metrics(),
            candidate=_metrics(ratio=0.5),
            compatibility_key="frozen-family",
        )
        for i in range(75)
    ]
    decision = select_portfolio_action(observations, config=config)
    policy = PortfolioPolicy(
        decisions={"sec": decision},
        registered_families=("sec",),
        overall_confidence=0.99,
        manifest_digest="manifest-a",
    )
    assert policy.select("unknown").abstained
    assert not policy.permits("sec", "frozen-family")
    assert policy.permits("sec", "frozen-family", review_approved=True)
    assert not policy.permits("sec", "drifted", review_approved=True)
    restored = PortfolioPolicy.from_dict(json.loads(json.dumps(policy.as_dict())))
    assert restored.digest == policy.digest
    malformed = policy.as_dict()
    malformed["decisions"]["sec"]["requires_review"] = "false"
    with pytest.raises(ValueError, match="boolean"):
        PortfolioPolicy.from_dict(malformed)
