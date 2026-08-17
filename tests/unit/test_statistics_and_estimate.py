"""Statistics and estimator unit tests (execution-plan §11.5, §9.6)."""

from __future__ import annotations

import math

import pytest

from guarded_agentic_compaction.estimate.headroom import break_even, estimate, required_calibration_groups
from guarded_agentic_compaction.evaluation.statistics import (
    PairedSample,
    describe,
    group_bootstrap_mean,
    holm_adjust,
    noninferiority,
    paired_group_bootstrap_diff,
    paired_ratio,
)
from guarded_agentic_compaction.grc.calibrate import (
    GRID,
    CalibrationSample,
    calibrate_gate,
    clopper_pearson_upper,
)
from guarded_agentic_compaction.schema.artifacts import GateModel

from scripts.generate_synthetic import ENTRY_ALLOWLIST, SYNTHETIC_CATALOG, generate


def test_clopper_pearson_zero_events_closed_form():
    # 1 - alpha^(1/n) for k = 0
    conf = 0.95
    for n in (1, 10, 100):
        assert clopper_pearson_upper(0, n, conf) == pytest.approx(1 - 0.05 ** (1 / n))


def test_clopper_pearson_is_monotone_in_n_and_k():
    conf = 1 - 0.10 / len(GRID)
    assert clopper_pearson_upper(0, 200, conf) < clopper_pearson_upper(0, 50, conf)
    assert clopper_pearson_upper(2, 100, conf) > clopper_pearson_upper(1, 100, conf)
    assert clopper_pearson_upper(5, 5, conf) == 1.0
    assert clopper_pearson_upper(0, 0, conf) == 1.0


def test_required_calibration_groups_matches_the_closed_form():
    n = required_calibration_groups(alpha=0.05, delta=0.10, grid_size=11)
    assert clopper_pearson_upper(0, n, 1 - 0.10 / 11) <= 0.05
    assert clopper_pearson_upper(0, n - 1, 1 - 0.10 / 11) > 0.05


def test_alpha_one_is_an_explicit_no_risk_budget_ablation():
    samples = [
        CalibrationSample(f"g{i}", {}, unproductive=True, violation=True)
        for i in range(5)
    ]
    gate = calibrate_gate(samples, alpha=1.0, phi_min=0.0)
    assert not gate.retire
    assert gate.risk_upper_bound == 1.0


def test_gate_certificate_describes_the_deployed_threshold_row():
    model = GateModel(
        features=("x",),
        weights=(1.0,),
        bias=0.0,
        feature_means=(0.0,),
        feature_scales=(1.0,),
    )
    samples = [
        CalibrationSample("g1", {"x": -1.0}, unproductive=False, violation=False),
        CalibrationSample("g1", {"x": 1.0}, unproductive=True, violation=True),
    ]
    gate = calibrate_gate(samples, model=model, alpha=1.0, phi_min=0.0, grid=(0.5, 0.9))
    assert gate.threshold == 1.0
    assert gate.observed_violations == 1
    assert gate.n_accepted == 1


def test_calibration_excludes_hard_guard_ineligible_samples_from_dispatch():
    samples = [
        CalibrationSample(
            f"g{i}",
            {},
            unproductive=False,
            violation=False,
            eligible=i < 92,
        )
        for i in range(100)
    ]
    gate = calibrate_gate(samples, alpha=0.05, delta=0.10)
    assert not gate.retire
    assert gate.n_calibration_groups == 100
    assert gate.n_accepted == 92
    assert gate.coverage == pytest.approx(0.92)
    assert gate.risk_upper_bound <= 0.05


def test_group_bootstrap_interval_brackets_the_point_estimate():
    values = [1.0, 1.2, 0.8, 1.1, 0.9, 1.0] * 6
    groups = [f"g{i % 6}" for i in range(len(values))]
    iv = group_bootstrap_mean(values, groups, n_boot=400, seed=3)
    assert iv.low <= iv.point <= iv.high


def test_paired_ratio_recovers_a_known_ratio():
    samples = [PairedSample(f"g{i}", baseline=10.0, candidate=6.0) for i in range(40)]
    iv = paired_ratio(samples, n_boot=200, seed=5)
    assert iv.point == pytest.approx(0.6)
    assert iv.high == pytest.approx(0.6)


def test_paired_ratio_reports_undefined_zero_baseline_without_crashing():
    samples = [PairedSample(f"g{i}", baseline=0.0, candidate=0.0) for i in range(10)]
    iv = paired_ratio(samples, n_boot=50, seed=5)
    assert math.isnan(iv.point)
    assert math.isnan(iv.low)
    assert math.isnan(iv.high)


def test_noninferiority_passes_when_equal_and_fails_on_a_real_drop():
    equal = [PairedSample(f"g{i}", 0.9, 0.9) for i in range(60)]
    res = noninferiority(equal, endpoint="q", margin=0.05, n_boot=300)
    assert res.passed

    worse = [PairedSample(f"g{i}", 0.9, 0.5) for i in range(60)]
    res2 = noninferiority(worse, endpoint="q", margin=0.05, n_boot=300)
    assert not res2.passed
    assert res2.diff.point == pytest.approx(-0.4)


def test_noninferiority_lower_is_better_direction():
    samples = [PairedSample(f"g{i}", 10.0, 9.0) for i in range(40)]
    res = noninferiority(
        samples, endpoint="requests", margin=0.5, n_boot=200, direction="lower_is_better"
    )
    assert res.passed


def test_holm_is_monotone_and_more_conservative_than_raw():
    adj = holm_adjust({"a": 0.001, "b": 0.02, "c": 0.30})
    assert adj["a"]["p_holm"] >= adj["a"]["p"]
    assert adj["a"]["p_holm"] <= adj["b"]["p_holm"] <= adj["c"]["p_holm"]
    assert adj["c"]["reject"] is False


def test_describe_reports_dispersion():
    d = describe([1.0, 2.0, 3.0, 4.0])
    assert d["n"] == 4
    assert d["mean"] == pytest.approx(2.5)
    assert d["cv"] > 0


def test_break_even_scales_inversely_with_saving():
    a = break_even(build_cost_usd=1000.0, maintenance_cost_usd_per_year=0.0, saving_per_episode_usd=0.01)
    b = break_even(build_cost_usd=1000.0, maintenance_cost_usd_per_year=0.0, saving_per_episode_usd=0.02)
    assert a["episodes_per_year"] == pytest.approx(2 * b["episodes_per_year"])
    zero = break_even(build_cost_usd=1.0, maintenance_cost_usd_per_year=0.0, saving_per_episode_usd=0.0)
    assert math.isinf(zero["episodes_per_day"])


def test_estimator_reports_blocked_mass_and_a_ceiling_on_planted_traces():
    eps = generate(n_episodes=240, seed=9)
    rep = estimate(eps, SYNTHETIC_CATALOG, entry_schema=ENTRY_ALLOWLIST, snapshot_id="t")
    assert rep.n_B > 0
    assert 0.0 < rep.phi_oracle <= 1.0
    assert rep.k_mean >= 2.0  # Eq. (5): at least two interior boundaries
    # the planted write and the planted undeclared tool must show up as blocked mass
    assert "notes.write" in rep.blocked_by_tool or "shadow.undeclared" in rep.blocked_by_tool
    assert "shadow.undeclared" in rep.undeclared_tools
    assert rep.calibration_groups_required == required_calibration_groups()
    assert "estimate report" in rep.render()


def test_estimator_returns_an_empty_report_without_episodes():
    rep = estimate([], SYNTHETIC_CATALOG)
    assert rep.n_episodes == 0
    assert "no episodes" in " ".join(rep.notes)
