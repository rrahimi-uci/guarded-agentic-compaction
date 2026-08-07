from __future__ import annotations

from paper.scripts.analyze_gate_selectivity import build_analysis, parse_gate_rows


def test_parse_gate_rows_reads_structured_threshold_data() -> None:
    rows = parse_gate_rows(
        "protocol=frozen_external_model; grid rows: "
        "[{'eta': 0.02, 'n': 0, 'violations': 0, 'upper': 1.0, 'coverage': 0.0}, "
        "{'eta': 0.11, 'n': 92, 'violations': 0, 'upper': 0.0498, 'coverage': 1.0}]"
    )
    assert rows == [
        {"eta": 0.02, "n": 0, "violations": 0, "upper": 1.0, "coverage": 0.0},
        {"eta": 0.11, "n": 92, "violations": 0, "upper": 0.0498, "coverage": 1.0},
    ]


def test_build_analysis_matches_retained_gate_boundaries() -> None:
    analysis = build_analysis()
    registered = analysis["summary"]["registered_current"]
    assert registered["artifacts_analyzed"] == 7
    assert registered["step_all_or_none"] == 7
    assert registered["partial_frontier"] == 0
    assert registered["first_positive_eta_counts"] == {"0.11": 5, "0.14": 2}

    artifacts = {item["artifact_id"]: item for item in analysis["artifacts"]}
    assert artifacts["gcs_live"]["frontier_type"] == "partial_frontier"
    assert artifacts["gcs_live"]["n_accepted"] == 88
    assert artifacts["github_live_pilot_2026_08_03"]["frontier_type"] == "partial_frontier"
    assert artifacts["github_live_pilot_2026_08_03"]["first_positive_eta"] == 0.02

    refusals = {item["artifact_id"]: item for item in analysis["support_shortfall_refusals"]}
    assert refusals["nestful"]["max_observed_family_support"] == 26
    assert refusals["nestful"]["minimum_zero_violation_groups"] == 92
    assert refusals["api_bank"]["max_observed_family_support"] == 8
    assert refusals["api_bank"]["minimum_zero_violation_groups"] == 92

    projection = analysis["negative_evidence"]["failed_projection_pilot"]
    assert projection["reason_counts"]["composite_projection_failed"] == 13
    assert projection["reason_counts"]["range:pr.body_excerpt"] == 5
