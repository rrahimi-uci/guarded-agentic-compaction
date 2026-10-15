from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_fresh_safeguards as analysis
import fresh_safeguard_comparison as study


def fixture():
    seal = {"test_ids": [1, 2], "schedule": study.schedule([1, 2])}
    rows = [{**item, "status": "completed", "quality": {**dict.fromkeys(analysis.ANSWER_FIELDS, True), "factuality_exact": True},
             "metrics": dict.fromkeys(study.METRICS, 1.0), "dispatched": item["arm"] != "baseline"}
            for item in seal["schedule"]]
    checkpoint = {"preflight_sha256": study.object_digest(seal), "pending": None, "rows": rows,
                  "approved_spend_usd": 200, "unknown_cost_reserve_usd": 0}
    return seal, checkpoint


def test_wrong_classification_is_not_hidden_by_four_field_endpoint():
    seal, cp = fixture()
    next(r for r in cp["rows"] if r["arm"] == "gac")["quality"]["category_correct"] = False
    result = analysis.analyze(seal, cp)
    assert result["quality"]["registered_factuality_exact"]["correct"]["gac"] == 2
    assert result["quality"]["supplementary_all_answer_fields"]["correct"]["gac"] == 1
    assert result["errors"][0]["failed_answer_fields"] == ["category_correct"]


def test_zero_discordance_does_not_report_zero_uncertainty():
    seal, cp = fixture()
    result = analysis.analyze(seal, cp)
    contrast = result["quality"]["registered_factuality_exact"]["contrasts"]["gac_vs_baseline"]
    low, high = contrast["pointwise_iid_conservative_ci95"]
    assert low < 0 < high
    assert contrast["mcnemar_exact_p"] == 1
    assert result["reductions"]["gac_vs_baseline"]["requests"] == 0
    assert "do not establish equivalence" in analysis.markdown(result)


def test_failed_attempt_remains_in_quality_but_precludes_efficiency_claim():
    seal, cp = fixture()
    row = next(r for r in cp["rows"] if r["arm"] == "gac")
    row["status"] = "failed"
    row.pop("metrics")
    result = analysis.analyze(seal, cp)
    assert result["quality"]["registered_factuality_exact"]["correct"]["gac"] == 1
    assert result["resources"]["gac"]["completed_n"] == 1
    assert not result["resources"]["gac"]["all_costs_observed"]
    assert "gac_vs_baseline" not in result["reductions"]


def test_incomplete_and_interrupted_runs_cannot_be_analyzed():
    seal, cp = fixture()
    cp["pending"] = seal["schedule"][0]
    with pytest.raises(ValueError, match="pending"):
        analysis.analyze(seal, cp)
    cp["pending"] = None
    cp["rows"].pop()
    with pytest.raises(ValueError, match="all scheduled"):
        analysis.analyze(seal, cp)


def test_entirely_failed_arm_has_no_fabricated_resource_mean():
    seal, cp = fixture()
    for row in cp["rows"]:
        if row["arm"] == "gac":
            row["status"] = "failed"
            row.pop("metrics")
    result = analysis.analyze(seal, cp)
    assert result["resources"]["gac"]["mean_on_completed"]["requests"] is None
    assert "unobserved" in analysis.markdown(result)


def test_dispatch_claims_come_from_actual_cohort_not_default_size():
    seal, cp = fixture()
    seal["probe"] = {"outcomes": {"gac": {"COMPACTED": 1, "BASELINE": 1}}}
    cp["preflight_sha256"] = study.object_digest(seal)
    next(r for r in cp["rows"] if r["arm"] == "gac")["dispatched"] = False
    result = analysis.analyze(seal, cp)
    assert result["runtime_gate_dispatch_disagreements"] == [1]
    text = analysis.markdown(result)
    assert "dispatch disagreements: 1 records" in text
    assert "119" not in text
