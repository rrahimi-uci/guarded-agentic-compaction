"""The comment-grounding check: "none" is grounded only when the record has no comments."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "paper" / "scripts"))
import github_workflow_family_study as fam  # noqa: E402


def _grade(comments: list[str], excerpt: str) -> bool:
    spec = fam.FAMILIES["pr_outcome"]
    row = {"number": 1, "title": "t", "state": "open", "comments": comments, "pull_request": {"merged_at": None}}
    answer = {"record_number": 1, "title": "t", "outcome": "open", "comment_evidence": excerpt}
    return bool(fam.grade(spec, row, answer, list(spec.tools))["comment_grounded"])


def test_none_is_grounded_only_without_comments() -> None:
    assert _grade([], "none")
    assert not _grade(["Thanks nonetheless!"], "none")       # the 2026-10-07 audit case (PR 6694)
    assert not _grade(["A real comment"], "none")


def test_real_excerpt_must_appear_in_a_comment() -> None:
    assert _grade(["Please see the docs here."], "see the docs")
    assert not _grade(["Please see the docs here."], "unrelated")
    assert not _grade([], "anything")
