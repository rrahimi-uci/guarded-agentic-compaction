#!/usr/bin/env python3
"""Executable evidence that the live study's quality oracle is a contract, not factuality.

The manuscript says so in prose (Section 8, "The quality oracle is a registered contract").
This file makes the claim falsifiable: if someone later strengthens `grade()` to check
summary factuality, these tests fail and the prose must be updated. If someone weakens it
further, they also fail. Either way the paper and the code cannot drift silently.

Run: .venv/bin/python -m pytest paper/scripts/test_oracle_weakness.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "paper" / "scripts"))

from github_live_study import Scenario, compiler_eligible, grade  # noqa: E402

EXPECTED_TOOLS = ["issue_get_record", "issue_get_labels", "issue_get_comments"]


def _scenario() -> Scenario:
    return Scenario(
        issue_number=4242,
        category="bug",
        labels=("bug",),
        html_url="https://example.invalid/issues/4242",
        day="2025-05-01",
        state="closed",
    )


def _args(issue: int) -> list[dict[str, object]]:
    return [
        {"issue_number": issue},
        {"issue_number": issue},
        {"issue_number": issue, "limit": 3},
    ]


def _answer(summary: str) -> dict[str, object]:
    return {
        "category": "bug",
        "issue_number": 4242,
        "evidence_label": "bug",
        "summary": summary,
    }


def test_a_fabricated_summary_passes_the_oracle() -> None:
    """The central admission: fluent invention inside the length bound is accepted."""

    scenario = _scenario()
    fabrication = (
        "The maintainers confirmed this is a GPU memory leak introduced in v2.1 and "
        "shipped a patch in v2.2 after profiling 400 runs."
    )
    result = grade(scenario, _answer(fabrication), EXPECTED_TOOLS, _args(4242))
    assert result["summary_valid"] is True
    assert result["overall"] is True, (
        "If this now fails, grade() checks factuality and the paper's limitation "
        "paragraph is out of date."
    )


def test_summary_is_rejected_only_for_shape() -> None:
    scenario = _scenario()
    assert grade(scenario, _answer(""), EXPECTED_TOOLS, _args(4242))["summary_valid"] is False
    assert grade(scenario, _answer("x" * 241), EXPECTED_TOOLS, _args(4242))["summary_valid"] is False
    assert grade(scenario, _answer("x" * 240), EXPECTED_TOOLS, _args(4242))["summary_valid"] is True


def test_tool_conformance_is_one_fifth_of_the_quality_score() -> None:
    """Control-flow compliance is folded into a number the paper calls quality."""

    scenario = _scenario()
    answer = _answer("A concise, accurate-looking summary.")
    conforming = grade(scenario, answer, EXPECTED_TOOLS, _args(4242))
    reordered = grade(
        scenario,
        answer,
        ["issue_get_labels", "issue_get_record", "issue_get_comments"],
        [_args(4242)[1], _args(4242)[0], _args(4242)[2]],
    )
    assert conforming["score"] == 1.0
    assert reordered["tool_contract"] is False
    # Same answer, same evidence, different call order: exactly 20% of the score.
    assert abs(conforming["score"] - reordered["score"] - 0.2) < 1e-9
    assert reordered["overall"] is False


def _source_record() -> dict[str, object]:
    return {
        "title": "Trainer crashes when resuming a sharded checkpoint",
        "body": "Resuming after epoch two raises an index error in the data loader.",
        "state": "closed",
        "comments": ["Confirmed with version 4.52 on two Linux hosts."],
    }


def _extractive_answer(excerpt: str) -> dict[str, object]:
    return {
        "category": "bug",
        "issue_number": 4242,
        "evidence_label": "bug",
        "title": "Trainer crashes when resuming a sharded checkpoint",
        "state": "closed",
        "comment_count": 1,
        "evidence_excerpt": excerpt,
    }


def test_natural_protocol_accepts_any_safe_complete_tool_order() -> None:
    """The new protocol measures discovered order rather than prescribing it."""

    scenario = _scenario()
    reordered_tools = [
        "issue_get_labels",
        "issue_get_comments",
        "issue_get_record",
    ]
    reordered_args = [
        {"issue_number": 4242},
        {"issue_number": 4242, "limit": 3},
        {"issue_number": 4242},
    ]
    result = grade(
        scenario,
        _extractive_answer("Confirmed with version 4.52 on two Linux hosts."),
        reordered_tools,
        reordered_args,
        task_design="natural-extractive-v2",
        source_record=_source_record(),
    )
    assert result["tool_contract"] is True
    assert result["factuality_exact"] is True
    assert result["overall"] is True


def test_natural_protocol_accepts_any_integer_comments_limit_as_needed() -> None:
    scenario = _scenario()
    answer = _extractive_answer("Confirmed with version 4.52 on two Linux hosts.")
    high_limit = _args(4242)
    high_limit[-1]["limit"] = 100
    accepted = grade(
        scenario,
        answer,
        EXPECTED_TOOLS,
        high_limit,
        task_design="natural-extractive-v2",
        source_record=_source_record(),
    )
    one_limit = _args(4242)
    one_limit[-1]["limit"] = 1
    also_accepted = grade(
        scenario,
        answer,
        EXPECTED_TOOLS,
        one_limit,
        task_design="natural-extractive-v2",
        source_record=_source_record(),
    )
    invalid_limit = _args(4242)
    invalid_limit[-1]["limit"] = "three"
    rejected = grade(
        scenario,
        answer,
        EXPECTED_TOOLS,
        invalid_limit,
        task_design="natural-extractive-v2",
        source_record=_source_record(),
    )
    assert accepted["tool_contract"] is True
    assert accepted["overall"] is True
    assert also_accepted["tool_contract"] is True
    assert rejected["tool_contract"] is False


def test_natural_protocol_rejects_fluent_fabrication() -> None:
    """The exact-source oracle closes the weakness documented for prescribed-v1."""

    result = grade(
        _scenario(),
        _extractive_answer(
            "The maintainers shipped a CUDA fix after profiling four hundred runs."
        ),
        EXPECTED_TOOLS,
        _args(4242),
        task_design="natural-extractive-v2",
        source_record=_source_record(),
    )
    assert result["evidence_excerpt_exact"] is False
    assert result["factuality_exact"] is False
    assert result["overall"] is False


def test_natural_protocol_rejects_inexact_factual_fields() -> None:
    answer = _extractive_answer("Confirmed with version 4.52 on two Linux hosts.")
    answer["comment_count"] = 2
    result = grade(
        _scenario(),
        answer,
        EXPECTED_TOOLS,
        _args(4242),
        task_design="natural-extractive-v2",
        source_record=_source_record(),
    )
    assert result["comment_count_exact"] is False
    assert result["factuality_exact"] is False


def test_natural_protocol_accepts_hand_written_macro_contract() -> None:
    result = grade(
        _scenario(),
        _extractive_answer("Confirmed with version 4.52 on two Linux hosts."),
        ["issue_get_bundle"],
        [{"issue_number": 4242}],
        task_design="natural-extractive-v2",
        source_record=_source_record(),
        condition="macro",
    )
    assert result["tool_contract"] is True
    assert result["factuality_exact"] is True
    assert result["overall"] is True


def _compiler_run(
    *,
    factual: bool = True,
    tools: list[str] | None = None,
    arguments: list[dict[str, object]] | None = None,
    tool_contract: bool = False,
) -> SimpleNamespace:
    selected_tools = tools or ["issue_get_comments", "issue_get_record"]
    selected_arguments = arguments or [
        # The public tool clamps any integer to at most three returned comments. The
        # model may therefore choose 100 without changing the observable read contract.
        {"issue_number": 4242, "limit": 100},
        {"issue_number": 4242},
    ]
    return SimpleNamespace(
        repeat=0,
        condition="discovery",
        issue_number=4242,
        quality={"factuality_exact": factual, "tool_contract": tool_contract},
        tool_sequence=selected_tools,
        tool_arguments=selected_arguments,
    )


def test_natural_compiler_eligibility_does_not_require_the_planted_three_call_contract() -> None:
    run = _compiler_run()
    assert compiler_eligible(run, "natural-extractive-v2") is True
    assert compiler_eligible(run, "prescribed-v1") is False


def test_natural_compiler_eligibility_rejects_unfaithful_or_unsafe_traces() -> None:
    assert compiler_eligible(_compiler_run(factual=False), "natural-extractive-v2") is False
    assert compiler_eligible(
        _compiler_run(
            tools=["issue_get_record"], arguments=[{"issue_number": 9999}]
        ),
        "natural-extractive-v2",
    ) is False
    assert compiler_eligible(
        _compiler_run(
            tools=["dangerous_write"], arguments=[{"issue_number": 4242}]
        ),
        "natural-extractive-v2",
    ) is False
