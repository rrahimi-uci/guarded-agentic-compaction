"""Regression checks over the immutable, paid GCS live-study result."""

from __future__ import annotations

import json
from pathlib import Path


RESULT = (
    Path(__file__).resolve().parents[2]
    / "paper"
    / "results"
    / "gcs_live"
    / "results.json"
)


def test_live_gcs_result_is_real_complete_and_secret_free() -> None:
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    run = payload["run"]
    comparison = payload["macro_vs_gcs"]

    assert run["provider_backed"] is True
    assert run["real_public_records"] is True
    assert run["openai_api_key_used"] is True
    assert run["secrets_serialized"] is False
    assert run["comparative_claim_allowed"] is True
    assert payload["failures"] == []
    assert comparison["n_pairs"] == 12
    assert {row["issue_number"] for row in payload["results"]} == set(
        payload["selection"]["issue_numbers"]
    )

    for condition in ("macro", "gcs"):
        aggregate = payload["aggregate"][condition]
        assert aggregate["n"] == 12
        assert aggregate["success_rate"] == 1
        assert aggregate["factuality_exact_rate"] == 1
        assert aggregate["tool_contract_rate"] == 1

    metrics = comparison["metrics"]
    assert metrics["requests"]["aggregate_reduction"] == 0.5
    assert metrics["total_tokens"]["aggregate_reduction"] > 0.38
    assert metrics["wall_latency_ms"]["aggregate_reduction"] > 0.40
    assert metrics["estimated_cost_usd"]["aggregate_reduction"] > 0.32
    assert metrics["tool_calls"]["aggregate_reduction"] == 0
