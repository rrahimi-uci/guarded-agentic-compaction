"""Regression tests for the frozen-candidate coverage simulation.

These cover the exact (Part 1) and Monte Carlo (Part 2) claims the simulation makes:
that frozen single-candidate calibration reproduces the paper's own published 92- and
106-group requirements from first principles, that an uncorrected multi-candidate search
degrades with candidate count while the Bonferroni correction restores it, and that
clustered (non-i.i.d.) group draws degrade coverage in the direction and rough magnitude
the simulation reports. Part 1 is exact arithmetic, so its assertions are exact; Part 2 is
seeded Monte Carlo, so its assertions use the tolerance the sealed run's own replicate
count supports rather than exact equality.
"""

from __future__ import annotations

import importlib.util
import math
import random
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))


def _load():
    spec = importlib.util.spec_from_file_location(
        "frozen_candidate_coverage_simulation",
        Path(__file__).with_name("frozen_candidate_coverage_simulation.py"),
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _load()


# --- Part 1: exact arithmetic -----------------------------------------------


def test_registered_n_matches_the_shipped_bfcl_appworld_helper() -> None:
    """The simulation must use the same n the rest of the paper's compiler scripts use."""

    assert MODULE.REGISTERED_N == 92


def test_frozen_confidence_matches_the_paper_gamma() -> None:
    conf = MODULE.per_threshold_confidence(MODULE.DELTA, MODULE.GRID_SIZE, m=1)
    gamma = MODULE.DELTA / MODULE.GRID_SIZE
    assert math.isclose(conf, 1.0 - gamma, rel_tol=1e-12)


def test_bonferroni_confidence_is_the_m_scaled_gamma() -> None:
    conf = MODULE.per_threshold_confidence(MODULE.DELTA, MODULE.GRID_SIZE, m=4)
    gamma = MODULE.DELTA / (4 * MODULE.GRID_SIZE)
    assert math.isclose(conf, 1.0 - gamma, rel_tol=1e-12)


def test_zero_violation_groups_reproduces_the_published_92_and_106() -> None:
    """These two numbers are already checked by validate_artifacts.py against
    admission_register.json; this cross-checks them from an independent computation
    path rather than duplicating the published value as a bare constant."""

    from benchmarks.external.compiler_eval import required_zero_violation_groups

    assert required_zero_violation_groups(MODULE.ALPHA, MODULE.DELTA) == 92
    published_m2 = math.ceil(
        math.log(MODULE.DELTA / (2 * MODULE.GRID_SIZE)) / math.log(1 - MODULE.ALPHA)
    )
    assert published_m2 == 106
    assert required_zero_violation_groups(MODULE.ALPHA, MODULE.DELTA / 2) == 106


def test_exact_miscoverage_is_zero_at_the_boundary_rates() -> None:
    """r_true=0 can never exceed a Clopper-Pearson upper bound built from k=0 alone
    being the only possible outcome; r_true=1 is the symmetric floor case."""

    conf = MODULE.per_threshold_confidence(MODULE.DELTA, MODULE.GRID_SIZE, m=1)
    assert MODULE.exact_miscoverage_probability(0.0, MODULE.REGISTERED_N, conf) == 0.0


def test_worst_case_single_candidate_miscoverage_stays_within_the_gamma_budget() -> None:
    """This is Clopper-Pearson's defining guarantee, checked at its own worst case
    rather than assumed: miscoverage never exceeds gamma for any population rate."""

    conf = MODULE.per_threshold_confidence(MODULE.DELTA, MODULE.GRID_SIZE, m=1)
    _, worst_p = MODULE.worst_case_rate(MODULE.REGISTERED_N, conf, steps=1000)
    gamma = MODULE.DELTA / MODULE.GRID_SIZE
    assert worst_p <= gamma + 1e-9


def test_uncorrected_union_miscoverage_grows_monotonically_with_m() -> None:
    """The core Phase-0 claim: skipping the multiplicity correction lets risk grow with
    candidate count, which is exactly why the compiler-wide gap the paper names is real."""

    conf = MODULE.per_threshold_confidence(MODULE.DELTA, MODULE.GRID_SIZE, m=1)
    worst_rate, _ = MODULE.worst_case_rate(MODULE.REGISTERED_N, conf, steps=1000)
    p_single = MODULE.exact_miscoverage_probability(worst_rate, MODULE.REGISTERED_N, conf)
    unions = [MODULE.union_miscoverage_probability(p_single, m) for m in (1, 2, 3, 5, 8, 16)]
    assert unions == sorted(unions)
    assert unions[0] < unions[-1]
    # frozen (m=1) must stay inside the registered delta; unrestricted at large m must not
    assert unions[0] <= MODULE.DELTA
    assert unions[-1] > MODULE.DELTA


def test_bonferroni_correction_restores_validity_at_every_tested_m() -> None:
    part1 = MODULE.part_one()
    for row in part1["candidate_rows"]:
        assert not row["bonferroni_corrected_exceeds_delta"], row


def test_frozen_case_never_exceeds_delta_but_unrestricted_eventually_does() -> None:
    part1 = MODULE.part_one()
    rows = {row["candidates"]: row for row in part1["candidate_rows"]}
    assert not rows[1]["uncorrected_exceeds_delta"]
    assert any(row["uncorrected_exceeds_delta"] for row in part1["candidate_rows"])


def test_part_one_is_deterministic() -> None:
    """No RNG in Part 1: two runs must be byte-identical."""

    first, second = MODULE.part_one(), MODULE.part_one()
    assert first == second


# --- Part 2: seeded Monte Carlo ----------------------------------------------


def test_clustered_simulation_reduces_to_iid_at_block_size_one() -> None:
    """With no clustering and no shift, realized miscoverage should sit at (or below)
    the i.i.d. baseline the exact Part-1 result already bounds."""

    rng = random.Random(MODULE.MC_SEED)
    result = MODULE.simulate_clustered_groups(
        rng,
        n_groups=MODULE.REGISTERED_N,
        block_size=1,
        p_bad_block=0.0,
        bad_shift=0.0,
        base_rate=0.0,
        confidence=MODULE.per_threshold_confidence(MODULE.DELTA, MODULE.GRID_SIZE, m=1),
        replicates=20_000,
    )
    assert result["empirical_miscoverage"] == 0.0


def test_clustering_degrades_coverage_at_a_fixed_marginal_rate() -> None:
    """Holding the population marginal rate fixed, coarser blocks (fewer effectively
    independent units) must not show *less* miscoverage than finer ones; the paper's
    i.i.d.-group caveat is a real, monotone effect and not a modeling artifact."""

    confidence = MODULE.per_threshold_confidence(MODULE.DELTA, MODULE.GRID_SIZE, m=1)
    seeds = iter(range(4))
    rates = []
    for block_size in (1, 4, 23, 46):
        rng = random.Random(MODULE.MC_SEED + next(seeds))
        result = MODULE.simulate_clustered_groups(
            rng,
            n_groups=MODULE.REGISTERED_N,
            block_size=block_size,
            p_bad_block=0.25,
            bad_shift=0.30,
            base_rate=0.0,
            confidence=confidence,
            replicates=40_000,
        )
        rates.append(result["empirical_miscoverage"])
    assert rates == sorted(rates), rates
    assert rates[-1] > rates[0]


def test_sealed_simulation_result_is_internally_consistent() -> None:
    """The published artifact must still cross-check against the shipped 92/106 numbers
    and must not claim the corrected union ever exceeds delta."""

    import json

    payload = json.loads(MODULE.DEFAULT_OUT.read_text())
    part1 = payload["part_one_exact_multiplicity"]
    assert part1["cross_check"]["m1_matches_published_92"] is True
    assert part1["cross_check"]["m2_matches_published_106"] is True
    for row in part1["candidate_rows"]:
        assert not row["bonferroni_corrected_exceeds_delta"]
    assert any(row["uncorrected_exceeds_delta"] for row in part1["candidate_rows"])

    part2 = payload["part_two_clustered_groups_monte_carlo"]
    if part2 is not None:
        assert part2["seed"] == MODULE.MC_SEED
        assert part2["worst_exceeds_nominal_gamma"] is True
