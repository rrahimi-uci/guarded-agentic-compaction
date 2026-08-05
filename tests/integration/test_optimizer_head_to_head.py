from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "paper/results/optimizer_head_to_head/results.json"
SMOKE = ROOT / "paper/results/optimizer_head_to_head/smoke.json"
PREFLIGHT = ROOT / "paper/results/optimizer_head_to_head/preflight.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_real_optimizer_head_to_head_is_complete_and_split_isolated() -> None:
    payload = _load(RESULTS)
    smoke = _load(SMOKE)
    preflight = _load(PREFLIGHT)

    assert payload["run"]["provider_backed"] is True
    assert payload["run"]["real_public_records"] is True
    assert payload["run"]["openai_api_key_used"] is True
    assert payload["run"]["secrets_serialized"] is False
    assert payload["run"]["smoke"] is False
    assert payload["run"]["comparative_claim_allowed"] is True
    assert payload["run"]["gepa"] == "0.1.4"
    assert payload["failures"] == []

    selection = payload["selection"]
    train = set(selection["optimization_train"])
    validation = set(selection["optimization_validation"])
    test = set(selection["test"])
    assert len(train) == 4 and len(validation) == 2 and len(test) == 6
    assert train.isdisjoint(validation | test)
    assert validation.isdisjoint(test)
    assert selection["test_frozen_before_optimization"] is True
    assert selection["selection_uses_provider_outcomes"] is False
    assert selection["unavailable_categories_after_exclusions"] == ["question"]
    smoke_selection = smoke["selection"]
    smoke_ids = set(
        smoke_selection["optimization_train"]
        + smoke_selection["optimization_validation"]
        + smoke_selection["test"]
    )
    assert smoke_ids.isdisjoint(train | validation | test)
    assert preflight["selection"] == selection


def test_gepa_used_real_bounded_search_but_retained_the_seed() -> None:
    payload = _load(RESULTS)
    optimization = payload["optimization"]
    result = optimization["gepa_result"]

    assert optimization["method"] == "official GEPA 0.1.4 optimize_anything"
    assert result["metric_calls"] == 14
    assert result["metric_calls"] <= payload["run"]["resolved_config"]["max_metric_calls"]
    assert result["improved"] is False
    assert result["best_prompt"] == result["seed_prompt"]
    assert len({row["candidate_digest"] for row in result["evaluation_log"]}) == 4
    assert all(row["metrics"]["overall"] is True for row in result["evaluation_log"])
    assert optimization["reflection"]["calls"] == 3
    assert optimization["accounting"]["task_metric_calls"] == 14
    assert optimization["accounting"]["combined_provider_requests"] == 59
    assert optimization["accounting"]["excluded_from_deployment_metrics"] is True


def test_gcs_matches_fair_pre_model_macro_and_beats_model_driven_baseline() -> None:
    payload = _load(RESULTS)
    aggregate = payload["aggregate"]

    assert set(aggregate) == {
        "baseline",
        "gepa",
        "gcs",
        "gcs_gepa",
        "manual_pre_model",
    }
    assert all(row["n"] == 6 for row in aggregate.values())
    assert all(row["success_rate"] == 1 for row in aggregate.values())
    assert all(row["tool_contract_rate"] == 1 for row in aggregate.values())
    assert aggregate["baseline"]["provider_requests"] == 24
    assert aggregate["gepa"]["provider_requests"] == 24
    assert aggregate["gcs"]["provider_requests"] == 6
    assert aggregate["manual_pre_model"]["provider_requests"] == 6
    assert aggregate["gcs"]["input_tokens"] == aggregate["manual_pre_model"]["input_tokens"]

    baseline_vs_gcs = payload["comparisons"]["baseline_vs_gcs"]
    assert baseline_vs_gcs["metrics"]["requests"]["aggregate_reduction"] == 0.75
    assert baseline_vs_gcs["metrics"]["requests"]["wilcoxon_p"] == 0.03125
    assert baseline_vs_gcs["metrics"]["input_tokens"]["aggregate_reduction"] > 0.78
    macro_vs_gcs = payload["comparisons"]["manual_pre_model_vs_gcs"]
    assert macro_vs_gcs["metrics"]["requests"]["aggregate_reduction"] == 0
    assert macro_vs_gcs["metrics"]["input_tokens"]["aggregate_reduction"] == 0
    assert macro_vs_gcs["quality"]["overall"]["paired_difference"] == 0

    parity = payload["manual_baseline"]["provider_free_parity"]
    assert parity["cases"] == parity["exact_projection_matches"] == 12
    assert parity["mismatches"] == []
    assert parity["provider_calls"] == 0


def test_invalid_provider_span_latency_is_retained_but_excluded() -> None:
    payload = _load(RESULTS)
    validation = payload["measurement_validation"]
    assert validation["provider_span_latency_valid"] is False
    assert validation["provider_span_latency_excluded_from_comparisons"] is True
    assert validation["provider_span_latency_outliers"] == [
        {
            "condition": "gcs_gepa",
            "issue_number": 4775,
            "provider_response_latency_ms": 9006.505,
            "wall_latency_ms": 3811.02,
        }
    ]
    comparison = payload["comparisons"]["baseline_vs_gcs_gepa"]
    assert "provider_response_latency_ms" not in comparison["metrics"]
    assert "provider_response_latency_ms" in comparison["excluded_metrics"]
    assert "wall_latency_ms" in comparison["metrics"]
