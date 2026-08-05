from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "paper" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import github_workflow_family_study as study  # noqa: E402


def test_final_family_selections_are_balanced_disjoint_and_source_valid() -> None:
    store, audit = study.load_store()
    assert audit["raw_rows"] == 7_540
    for spec in study.FAMILIES.values():
        final = json.loads(
            (
                ROOT
                / f"paper/results/github_workflow_families/{spec.name}/final/results.json"
            ).read_text(encoding="utf-8")
        )
        selection = final["selection"]
        discovery = [store[int(number)] for number in selection["discovery"]]
        test = [store[int(number)] for number in selection["test"]]
        assert len(discovery) == 132 and all(spec.eligible(row) for row in discovery)
        assert len(test) == 30 and all(spec.eligible(row) for row in test)
        assert selection["discovery_class_counts"] == {
            label: 44 for label in spec.classes
        }
        assert selection["test_class_counts"] == {
            label: 10 for label in spec.classes
        }
        assert {row["number"] for row in discovery}.isdisjoint(
            row["number"] for row in test
        )
        assert {
            label: sum(spec.class_for(row) == label for row in discovery)
            for label in spec.classes
        } == selection["discovery_class_counts"]
        assert {
            label: sum(spec.class_for(row) == label for row in test)
            for label in spec.classes
        } == selection["test_class_counts"]


def test_pr_outcome_exact_grader_rejects_mutation() -> None:
    store, _ = study.load_store()
    spec = study.FAMILIES["pr_outcome"]
    row = next(row for row in store.values() if spec.eligible(row) and study.pr_outcome(row) == "merged")
    answer = {
        "record_number": row["number"],
        "title": study.normalize_text(row["title"]),
        "outcome": "merged",
        "comment_evidence": study._comments(row)[0] if study._comments(row) else "none",
    }
    assert study.grade(spec, row, answer, spec.tools)["overall"] is True
    answer["outcome"] = "closed_unmerged"
    assert study.grade(spec, row, answer, spec.tools)["overall"] is False


def test_backlog_attention_exact_grader_and_snapshot_tools() -> None:
    store, _ = study.load_store()
    spec = study.FAMILIES["backlog_attention"]
    row = next(
        row for row in store.values()
        if spec.eligible(row) and study.backlog_route(row) == "owned"
    )
    number = int(row["number"])
    record = study.execute_snapshot(spec, store, spec.tools[0], {"record_number": number})
    ownership = study.execute_snapshot(spec, store, spec.tools[1], {"record_number": number})
    discussion = study.execute_snapshot(
        spec, store, spec.tools[2], {"record_number": number, "limit": 3}
    )
    answer = {
        "record_number": number,
        "title": record["title"],
        "route": "owned",
        "owner": ownership["assignees"][0],
        "comment_evidence": (
            study.normalize_text(discussion["comments"][0])
            if discussion["comments"]
            else "none"
        ),
    }
    assert study.grade(spec, row, answer, spec.tools)["overall"] is True
    answer["owner"] = "not-the-owner"
    assert study.grade(spec, row, answer, spec.tools)["overall"] is False
