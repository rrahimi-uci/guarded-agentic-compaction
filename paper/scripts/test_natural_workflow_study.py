from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "paper" / "scripts"))

import github_live_study as fixed  # noqa: E402
from github_natural_workflow_study import (  # noqa: E402
    NATURAL_PROMPT,
    grade_factual,
    select_full_scenarios,
    select_smoke_scenarios,
)


def _fixture(comments: list[str] | None = None) -> tuple[fixed.Scenario, dict[int, dict]]:
    number = 4242
    store = {
        number: {
            "number": number,
            "title": "Parser fails on nested arrays",
            "state": "open",
            "body": "A real issue body for the fixture. " * 4,
            "labels": ("bug",),
            "comments": comments if comments is not None else ["Maintainer reproduced this on version 3.2."],
            "html_url": "https://example.invalid/issues/4242",
            "day": "2026-01-01",
        }
    }
    scenario = fixed.Scenario(
        issue_number=number,
        category="bug",
        labels=("bug",),
        html_url=store[number]["html_url"],
        day=store[number]["day"],
        state="open",
    )
    return scenario, store


def _answer() -> dict:
    return {
        "issue_number": 4242,
        "title": "Parser fails on nested arrays",
        "state": "open",
        "category": "bug",
        "evidence_label": "bug",
        "comment_evidence": "reproduced this on version 3.2",
    }


def test_prompt_does_not_name_or_order_tools() -> None:
    assert "issue_get_" not in NATURAL_PROMPT
    assert "exact order" not in NATURAL_PROMPT.lower()


def test_factual_grade_is_independent_of_tool_order() -> None:
    scenario, store = _fixture()
    left = grade_factual(
        scenario,
        _answer(),
        ["issue_get_record", "issue_get_labels", "issue_get_comments"],
        store,
    )
    right = grade_factual(
        scenario,
        _answer(),
        ["issue_get_comments", "issue_get_record", "issue_get_labels"],
        store,
    )
    assert left["overall"] is True
    assert right["overall"] is True
    assert left["score"] == right["score"] == 1.0


def test_manual_pre_model_interface_is_a_valid_task_trace() -> None:
    scenario, store = _fixture()
    result = grade_factual(
        scenario,
        _answer(),
        ["manual_issue_evidence_bundle"],
        store,
    )
    assert result["overall"] is True
    assert result["trace_valid"] is True
    assert result["tool_contract"] is True


def test_fabricated_comment_evidence_fails() -> None:
    scenario, store = _fixture()
    answer = _answer()
    answer["comment_evidence"] = "A patch shipped in version 9.9 after 400 GPU runs."
    result = grade_factual(scenario, answer, ["issue_get_record"], store)
    assert result["comment_grounded"] is False
    assert result["overall"] is False


def test_missing_comments_require_explicit_none() -> None:
    scenario, store = _fixture(comments=[])
    answer = _answer()
    answer["comment_evidence"] = "none"
    result = grade_factual(scenario, answer, ["issue_get_record"], store)
    assert result["comment_grounded"] is True
    assert result["overall"] is True


def test_short_and_literal_none_comments_are_valid_verbatim_evidence() -> None:
    scenario, store = _fixture(comments=["Thanks!"])
    answer = _answer()
    answer["comment_evidence"] = "Thanks!"
    assert grade_factual(scenario, answer, ["issue_get_record"], store)["overall"] is True

    scenario, store = _fixture(comments=["none"])
    answer["comment_evidence"] = "none"
    assert grade_factual(scenario, answer, ["issue_get_record"], store)["overall"] is True


def test_wrong_title_fails_even_when_tool_trace_is_valid() -> None:
    scenario, store = _fixture()
    answer = _answer()
    answer["title"] = "A plausible but invented title"
    result = grade_factual(scenario, answer, ["issue_get_record"], store)
    assert result["trace_valid"] is True
    assert result["title_correct"] is False
    assert result["overall"] is False


def test_smoke_selection_does_not_require_test_class_strata() -> None:
    scenario, store = _fixture()
    selected, manifest = select_smoke_scenarios(store, count=1, seed=7, excluded=set())
    assert [item.issue_number for item in selected] == [scenario.issue_number]
    assert manifest["smoke_issue_numbers"] == [scenario.issue_number]


def test_full_selection_is_disjoint_and_records_observed_categories() -> None:
    scenario, one = _fixture()
    store = {}
    for offset in range(8):
        number = scenario.issue_number + offset
        item = dict(one[scenario.issue_number])
        item["number"] = number
        item["html_url"] = f"https://example.invalid/issues/{number}"
        store[number] = item
    discovery, test, manifest = select_full_scenarios(
        store, discovery_count=3, test_count=2, seed=9, excluded={scenario.issue_number}
    )
    assert {item.issue_number for item in discovery}.isdisjoint(
        {item.issue_number for item in test}
    )
    assert len(discovery) == 3 and len(test) == 2
    assert sum(manifest["test_category_counts"].values()) == 2
