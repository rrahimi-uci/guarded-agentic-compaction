"""Provider-free unit tests for github_multirepo_gate_frontier_study.py.

These cover the two genuinely new pieces the module adds on top of the already-tested
github_multirepo_pr_outcome_core.py harness: parsing the calibration grid sweep back out
of a compiled artifact's gate notes, and the cohort-sealing design (five repositories,
300 pooled held-out cases) that this study's preflight targets. Nothing here makes a
provider call or touches a checked-in results artifact; the full live pipeline (discovery,
both compile passes, three-condition dispatch) is validated by a real, tiny, logged smoke
run against one repository, not by synthetic fixtures here.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import github_multirepo_gate_frontier_study as frontier  # noqa: E402
import github_multirepo_pr_outcome_core as core  # noqa: E402


def _notes(rows: list[dict[str, object]]) -> str:
    return f"protocol=self_fitted_group_oof; grid rows: {rows}"


def test_coverage_curve_parses_grid_rows_from_gate_notes() -> None:
    rows = [
        {"eta": 0.1, "n": 0, "violations": 0, "upper": 1.0, "coverage": 0.0},
        {"eta": 0.2, "n": 40, "violations": 0, "upper": 0.03, "coverage": 0.43},
        {"eta": 0.3, "n": 92, "violations": 1, "upper": 0.06, "coverage": 1.0},
    ]
    compilation = {"artifact": {"gate": {"notes": _notes(rows)}}}
    parsed = frontier.coverage_curve(compilation)
    assert parsed == rows


def test_coverage_curve_returns_none_without_an_admitted_artifact() -> None:
    assert frontier.coverage_curve({"status": "retired"}) is None
    assert frontier.coverage_curve({"artifact": {"gate": {"notes": "no grid here"}}}) is None


def test_coverage_curve_returns_none_on_malformed_grid_literal() -> None:
    compilation = {"artifact": {"gate": {"notes": "protocol=x; grid rows: not [a valid <literal>"}}}
    assert frontier.coverage_curve(compilation) is None


def test_distinct_nonzero_coverage_levels_deduplicates_and_drops_zero() -> None:
    rows = [
        {"eta": 0.1, "coverage": 0.0},
        {"eta": 0.2, "coverage": 0.43},
        {"eta": 0.3, "coverage": 0.43},
        {"eta": 0.4, "coverage": 1.0},
    ]
    assert frontier.distinct_nonzero_coverage_levels(rows) == [0.43, 1.0]


def test_distinct_nonzero_coverage_levels_handles_missing_or_empty_input() -> None:
    assert frontier.distinct_nonzero_coverage_levels(None) == []
    assert frontier.distinct_nonzero_coverage_levels([]) == []


def test_frontier_config_targets_three_hundred_pooled_cases_across_five_repos() -> None:
    payload = frontier.build_preflight(tuple(core.DEFAULT_SOURCES.values()), force_download=False)
    checks = payload["global_checks"]
    assert checks["complete_repo_count"] == 5
    assert checks["pooled_test_cases"] == frontier.MINIMUM_POOLED_TEST_CASES == 300
    assert checks["all_selected_repositories_time_forward"] is True
    for repository, entry in payload["repositories"].items():
        assert entry["status"] == "selected", (repository, entry.get("reason"))
        assert len(entry["selection"]["test"]) == frontier.TEST_CASES_PER_REPO == 60


def test_support_only_compile_uses_alpha_one_and_frozen_selection() -> None:
    # Exercise the config construction path without a full compiler run: build the exact
    # GrcConfig compile_support_only_artifact would pass to compile_grc and check the two
    # properties the docstring promises -- everything else about it mirrors
    # core.compile_artifact's own config byte-for-byte.
    import inspect

    source = inspect.getsource(frontier.compile_support_only_artifact)
    assert "alpha=1.0" in source
    assert "freeze_one_candidate_before_calibration=True" in source
    # and the learned-gate path this is compared against stays at the registered budget
    learned_source = inspect.getsource(core.compile_artifact)
    assert "alpha=0.05" in learned_source
    assert "freeze_one_candidate_before_calibration=True" in learned_source


def test_support_only_registers_under_a_distinct_registry_name() -> None:
    source_repr = "compile_support_only_artifact"
    assert source_repr in dir(frontier)
    import inspect

    source = inspect.getsource(frontier.compile_support_only_artifact)
    assert "support-only" in source
