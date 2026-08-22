"""Regression tests for the gate-frontier pilot's exact Fisher analysis.

Provider-free: these check the statistic against known closed-form and hand-computed
cases, and check the sealed analysis artifact is internally consistent with the sealed
results it was computed from.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def _load():
    spec = importlib.util.spec_from_file_location(
        "gate_frontier_pilot_analysis",
        Path(__file__).with_name("gate_frontier_pilot_analysis.py"),
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _load()


# --- exact Fisher statistic --------------------------------------------------


def test_zero_violations_in_both_groups_gives_p_equal_one() -> None:
    assert MODULE.fisher_exact_one_sided_greater(0, 60, 0, 60) == 1.0


def test_identical_rates_give_a_large_p_value() -> None:
    p = MODULE.fisher_exact_one_sided_greater(3, 60, 3, 60)
    assert p > 0.4


def test_all_violations_in_the_test_group_gives_the_smallest_p() -> None:
    """Every one of n1 is a violation, none of n2 -- the most extreme configuration."""

    p = MODULE.fisher_exact_one_sided_greater(5, 5, 0, 60)
    assert p < 1e-4


def test_matches_hand_computed_reference_value() -> None:
    """4/60 vs 0/60, the pilot's own headline comparison, computed independently by an
    unrolled sum over the 2x2 hypergeometric table rather than reusing the module's own
    loop structure."""

    from math import comb

    n1, n2, k = 60, 60, 4
    total = comb(n1 + n2, k)
    p = sum(comb(n1, x) * comb(n2, k - x) for x in range(4, min(n1, k) + 1)) / total
    assert math.isclose(
        MODULE.fisher_exact_one_sided_greater(4, 60, 0, 60), p, rel_tol=1e-9
    )


def test_p_value_decreases_as_the_violation_count_grows() -> None:
    values = [MODULE.fisher_exact_one_sided_greater(k, 60, 0, 60) for k in (0, 1, 2, 4, 8)]
    assert values == sorted(values, reverse=True)


def test_symmetry_a_vs_b_and_b_vs_a_are_not_the_same_test() -> None:
    """One-sided 'greater' is directional: 4 vs 0 and 0 vs 4 are different questions."""

    higher = MODULE.fisher_exact_one_sided_greater(4, 60, 0, 60)
    lower = MODULE.fisher_exact_one_sided_greater(0, 60, 4, 60)
    assert higher < lower


# --- pooled counts and cross-condition detection -----------------------------


def _fake_results(rows: list[dict]) -> dict:
    return {"graded_results": rows}


def test_pooled_counts_aggregates_across_conditions() -> None:
    rows = [
        {"stratum": "plain_text", "comment_grounded": True, "condition": "unchanged", "issue_number": 1},
        {"stratum": "plain_text", "comment_grounded": True, "condition": "compiled", "issue_number": 1},
        {"stratum": "markdown_link", "comment_grounded": False, "condition": "unchanged", "issue_number": 2},
        {"stratum": "markdown_link", "comment_grounded": True, "condition": "compiled", "issue_number": 2},
    ]
    counts = MODULE.pooled_counts(rows)
    assert counts["plain_text"] == {"n": 2, "violations": 0}
    assert counts["markdown_link"] == {"n": 2, "violations": 1}


def test_cross_condition_failure_requires_both_conditions_to_fail() -> None:
    rows = [
        {"stratum": "markdown_link", "comment_grounded": False, "condition": "unchanged", "issue_number": 5710},
        {"stratum": "markdown_link", "comment_grounded": False, "condition": "compiled", "issue_number": 5710},
        {"stratum": "markdown_link", "comment_grounded": False, "condition": "unchanged", "issue_number": 4448},
        {"stratum": "markdown_link", "comment_grounded": True, "condition": "compiled", "issue_number": 4448},
    ]
    analysis = MODULE.analyze(_fake_results(rows))
    assert analysis["records_failing_in_both_conditions"] == [5710]


def test_analysis_reports_no_signal_when_strata_are_flat() -> None:
    """Identical violation counts in every stratum must not read as significant. The
    threshold here is deliberately generous (not a specific numeric target) because exact
    tests at n=30 per identical-rate group are not extreme even when the null is exactly
    true; the point is 'clearly not significant', not a particular p-value."""

    rows = []
    for stratum in ("plain_text", "bare_url", "markdown_link"):
        for i in range(30):
            rows.append({"stratum": stratum, "comment_grounded": i != 0,
                         "condition": "unchanged", "issue_number": i})
    analysis = MODULE.analyze(_fake_results(rows))
    for stratum in ("markdown_link", "bare_url"):
        assert analysis["comparisons_vs_plain_text"][stratum]["vs_plain_text_one_sided_p"] > 0.5


# --- sealed artifact consistency ---------------------------------------------


def test_sealed_analysis_matches_the_sealed_results_it_was_computed_from() -> None:
    import json

    if not MODULE.RESULTS_PATH.is_file() or not MODULE.DEFAULT_OUT.is_file():
        return  # analysis has not been run in this checkout; nothing to check
    results = json.loads(MODULE.RESULTS_PATH.read_text())
    sealed = json.loads(MODULE.DEFAULT_OUT.read_text())
    recomputed = MODULE.analyze(results)
    assert recomputed["counts_by_stratum"] == sealed["counts_by_stratum"]
    assert recomputed["records_failing_in_both_conditions"] == sealed["records_failing_in_both_conditions"]
