from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "paper" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import github_multirepo_preflight as preflight  # noqa: E402


def test_real_snapshot_preflight_selects_all_three_families_time_forward() -> None:
    payload = preflight.design_preflight(
        snapshot_paths=(preflight.issue_type.DATA_PATH,),
        repositories=("huggingface/datasets",),
        families=("issue_type", "pr_outcome", "backlog_attention"),
        discovery_cases=132,
        test_cases=30,
        minimum_complete_repos=1,
        exclude_existing_paper_results=False,
    )

    assert payload["schema"] == "agent-compaction-github-multirepo-preflight/v1"
    assert payload["status"] == "designed_not_run"
    assert payload["provider_calls_executed"] == 0
    assert payload["real_public_records"] is True
    assert payload["simulated"] is False
    assert payload["sources"]["repositories_discovered"] == ["huggingface/datasets"]
    assert payload["sources"]["snapshots"] == [
        {
            "bytes": 12_659_096,
            "duplicate_rows_replaced_or_ignored": 100,
            "path": "paper/results/datasets/github_issues/train-00000-of-00001.parquet",
            "raw_rows": 7_540,
            "repositories_discovered": {"huggingface/datasets": 7_540},
            "sha256": "09453eefae39e45a969ab0bee72ca0e188fe79dc50403b0f2a78c39894f5d1a3",
            "unresolved_repository_rows": 0,
        }
    ]
    assert payload["global_checks"] == {
        "complete_repo_count": 1,
        "minimum_complete_repos": 1,
        "satisfies_minimum_complete_repos": True,
        "all_selected_families_time_forward": True,
    }

    repository = payload["repositories"]["huggingface/datasets"]
    assert repository["complete_for_requested_families"] is True
    assert repository["audit"] == {
        "deduplicated_records": 7_440,
        "duplicate_rows_replaced_or_ignored": 100,
        "snapshot_sources": [
            "paper/results/datasets/github_issues/train-00000-of-00001.parquet"
        ],
        "day_range": {
            "min": "2020-04-14",
            "max": "2025-06-13",
            "unique_days": 1_615,
        },
    }

    for family_name, expected_class in (
        ("issue_type", {"bug": 10, "enhancement": 10, "question": 10}),
        ("pr_outcome", {"open": 10, "merged": 10, "closed_unmerged": 10}),
        (
            "backlog_attention",
            {"owned": 10, "discussed_unowned": 10, "awaiting_first_response": 10},
        ),
    ):
        family = repository["families"][family_name]
        assert family["status"] == "selected"
        selection = family["selection"]
        assert len(selection["discovery"]) == 132
        assert len(selection["test"]) == 30
        assert selection["time_forward"]["strict_time_forward"] is True
        assert selection["time_forward"]["gap_days"] >= 0
        assert selection["test_class_counts"] == expected_class


def test_real_snapshot_preflight_fails_closed_on_multirepo_minimum() -> None:
    payload = preflight.design_preflight(
        snapshot_paths=(preflight.issue_type.DATA_PATH,),
        families=("issue_type", "pr_outcome", "backlog_attention"),
        discovery_cases=132,
        test_cases=30,
        minimum_complete_repos=3,
        exclude_existing_paper_results=False,
    )

    assert payload["sources"]["repositories_discovered"] == ["huggingface/datasets"]
    assert payload["global_checks"]["complete_repo_count"] == 1
    assert payload["global_checks"]["minimum_complete_repos"] == 3
    assert payload["global_checks"]["satisfies_minimum_complete_repos"] is False
