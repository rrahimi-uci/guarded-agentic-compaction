"""Check paired uncertainty at boundaries and database/failure accounting."""
import json
import sys
from pathlib import Path

import pytest
from scipy.stats import multinomial

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bird_quality_sensitivity import ROOT, build, paired_interval, table


def test_zero_discordance_retains_uncertainty_and_swap_reverses_interval():
    # No discordance is not proof of equivalence.
    upper = 1 - .0125 ** (1 / 150)
    assert paired_interval(0, 0, 150) == pytest.approx([-upper, upper])
    low, high = paired_interval(2, 5, 150)
    assert paired_interval(5, 2, 150) == pytest.approx([-high, -low])
    with pytest.raises(ValueError):
        paired_interval(2, 2, 3)


def test_exact_small_sample_multinomial_coverage():
    # Enumerate all paired outcomes; gain and loss are mutually exclusive.
    n = 8
    intervals = {(g, l): paired_interval(g, l, n) for g in range(n + 1) for l in range(n - g + 1)}
    for pg, pl in [(0, 0), (.02, .03), (.1, .3), (.4, .4), (0, .5), (1, 0)]:
        coverage = sum(multinomial.pmf([g, l, n-g-l], n, [pg, pl, 1-pg-pl])
                       for (g, l), (low, high) in intervals.items() if low <= pg-pl <= high)
        assert coverage >= .95 - 1e-12


def test_retained_cohorts_preserve_failures_and_database_sensitivity():
    actual = build()
    expected = json.loads((ROOT / "paper/results/bird/quality_sensitivity.json").read_text())
    for name, row in actual["cohorts"].items():
        retained = expected["cohorts"][name]
        for key in row:
            if key == "pointwise_iid_conservative_ci95":
                assert row[key] == pytest.approx(retained[key], abs=1e-12)
            else:
                assert row[key] == retained[key]
    train = actual["cohorts"]["train"]
    assert train["n"] == 630
    assert train["gains"] == 17 and train["losses"] == 18
    assert train["leave_one_database_out_range"] == pytest.approx([-.005, 1/300])
    assert train["missing_runs"] == {"baseline": 0, "compiled": 1}
    assert train["unrecorded_net_compiled_cost_break_even_usd"] == pytest.approx(.16295239)
    assert table(actual) == (ROOT / "paper/iclr/tables/bird_quality_sensitivity.tex").read_text()
