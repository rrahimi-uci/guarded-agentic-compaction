"""Regression tests for the gate-frontier pilot preflight.

Provider-free throughout: these check the stratification logic, the exclusion of
already-used record numbers, and determinism of the seeded selection -- not any live
result, since none exists yet (the pilot is preflight-sealed, not executed).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def _load():
    spec = importlib.util.spec_from_file_location(
        "gate_frontier_pilot_preflight",
        Path(__file__).with_name("gate_frontier_pilot_preflight.py"),
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _load()


# --- category_for parity with github_live_study ----------------------------


def test_category_for_matches_github_live_study_exactly() -> None:
    """This must not drift from the shipped classifier the live studies use."""

    sys.path.insert(0, str(ROOT / "paper" / "scripts"))
    from github_live_study import category_for as shipped_category_for  # noqa: E402

    cases = [
        [],
        ["bug"],
        ["enhancement"],
        ["question"],
        ["bug", "enhancement"],
        ["bug", "question"],
        ["enhancement", "question"],
        ["bug", "enhancement", "question"],
        ["good first issue"],
        ["bug", "good first issue"],
    ]
    for labels in cases:
        assert MODULE.category_for(labels) == shipped_category_for(labels), labels


def test_other_is_the_ambiguous_bucket() -> None:
    assert MODULE.category_for([]) == "other"
    assert MODULE.category_for(["bug", "enhancement"]) == "other"
    assert MODULE.category_for(["wontfix"]) == "other"


# --- risk stratification, grounded in the recorded 6602 failure -------------


def test_issue_6602_comment_is_classified_markdown_link() -> None:
    """The exact recorded comment_evidence:mismatch case this stratification targets."""

    comment = (
        "I'm facing this problem while doing my translation of "
        "[mteb/stackexchange-clustering](https://huggingface.co/datasets/mteb/stackexchange-clustering). "
        "each row has lots of samples (up to 100k samples)"
    )
    assert MODULE._risk_stratum([comment]) == "markdown_link"


def test_bare_url_without_markdown_syntax_is_its_own_stratum() -> None:
    assert MODULE._risk_stratum(["see https://example.com/issue/123 for details"]) == "bare_url"


def test_plain_text_with_no_link_is_the_baseline_stratum() -> None:
    assert MODULE._risk_stratum(["Thanks, this fixed it for me!"]) == "plain_text"


def test_markdown_link_takes_precedence_over_bare_url_when_both_present() -> None:
    comment = "See [the docs](https://example.com/docs) or just https://example.com/raw"
    assert MODULE._risk_stratum([comment]) == "markdown_link"


def test_only_first_three_comments_are_considered() -> None:
    comments = ["plain one", "plain two", "plain three", "[link](https://example.com)"]
    assert MODULE._risk_stratum(comments) == "plain_text"


def test_empty_comment_list_is_plain_text_not_an_error() -> None:
    assert MODULE._risk_stratum([]) == "plain_text"


# --- selection determinism and disjointness ---------------------------------


def _fake_pool() -> list[dict]:
    pool = []
    number = 1
    for stratum in ("plain_text", "bare_url", "markdown_link"):
        for _ in range(50):
            pool.append({
                "number": number, "category": "other", "n_labels": 0,
                "n_comments": 2, "risk_stratum": stratum,
                "is_pull_request": False, "state": "open",
            })
            number += 1
    return pool


def test_selection_is_deterministic_under_the_sealed_seed() -> None:
    pool = _fake_pool()
    first = MODULE.select_cohort(pool, per_stratum=10, held_out_share=0.5)
    second = MODULE.select_cohort(pool, per_stratum=10, held_out_share=0.5)
    assert first["held_out"] == second["held_out"]
    assert first["calibration_dev"] == second["calibration_dev"]


def test_held_out_and_calibration_dev_are_disjoint() -> None:
    pool = _fake_pool()
    selection = MODULE.select_cohort(pool, per_stratum=10, held_out_share=0.5)
    held_out_numbers = {r["number"] for r in selection["held_out"]}
    dev_numbers = {r["number"] for r in selection["calibration_dev"]}
    assert not held_out_numbers & dev_numbers


def test_selection_respects_the_per_stratum_cap() -> None:
    pool = _fake_pool()
    selection = MODULE.select_cohort(pool, per_stratum=10, held_out_share=0.5)
    for stratum, count in selection["by_stratum_selected"].items():
        assert count <= 10, stratum


def test_pull_requests_and_comment_free_records_are_excluded() -> None:
    pool = _fake_pool()
    pool.append({"number": 9999, "category": "other", "n_labels": 0, "n_comments": 3,
                 "risk_stratum": "plain_text", "is_pull_request": True, "state": "open"})
    pool.append({"number": 9998, "category": "other", "n_labels": 0, "n_comments": 0,
                 "risk_stratum": "plain_text", "is_pull_request": False, "state": "open"})
    selection = MODULE.select_cohort(pool, per_stratum=100, held_out_share=0.5)
    all_numbers = {r["number"] for r in selection["held_out"] + selection["calibration_dev"]}
    assert 9999 not in all_numbers
    assert 9998 not in all_numbers


# --- sealed preflight artifact -----------------------------------------------


def test_sealed_preflight_made_no_provider_calls() -> None:
    import json

    payload = json.loads(MODULE.DEFAULT_OUT.read_text())
    assert payload["provider_calls_made"] == 0
    assert payload["status"] == "PREFLIGHT_SEALED_NOT_EXECUTED"


def test_sealed_preflight_cohort_is_disjoint_from_prior_studies() -> None:
    import json

    payload = json.loads(MODULE.DEFAULT_OUT.read_text())
    cohort = payload["cohort"]
    selected = set(cohort["held_out_record_numbers"]) | set(cohort["calibration_dev_record_numbers"])
    excluded_count = payload["risk_stratification"]["already_used_record_numbers_excluded"]
    used = MODULE._already_used_record_numbers()
    assert len(used) == excluded_count
    assert not selected & used
