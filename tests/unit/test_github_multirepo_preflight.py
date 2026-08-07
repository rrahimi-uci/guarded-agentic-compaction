from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT / "paper" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import github_multirepo_preflight as preflight  # noqa: E402
import github_workflow_family_study as workflow_family  # noqa: E402


def _pr_row(
    number: int,
    *,
    day: str,
    state: str,
    merged_at: str | None,
) -> dict[str, object]:
    return {
        "repository": "octo/example",
        "number": number,
        "title": f"Record {number}",
        "body": "x" * 120,
        "labels": (),
        "state": state,
        "comments": ["looks good"],
        "assignees": [],
        "pull_request": {
            "url": f"https://api.github.com/repos/octo/example/pulls/{number}",
            "merged_at": merged_at,
        },
        "html_url": f"https://github.com/octo/example/pull/{number}",
        "repository_url": "https://api.github.com/repos/octo/example",
        "day": day,
        "created_at": f"{day}T00:00:00+00:00",
        "updated_at": f"{day}T01:00:00+00:00",
        "id": number,
    }


def test_infer_repository_supports_github_and_api_urls() -> None:
    assert preflight.infer_repository(
        {"html_url": "https://github.com/openai/openai-python/issues/1"}
    ) == "openai/openai-python"
    assert preflight.infer_repository(
        {"repository_url": "https://api.github.com/repos/openai/openai-python"}
    ) == "openai/openai-python"
    assert preflight.infer_repository(
        {
            "pull_request": {
                "url": "https://api.github.com/repos/openai/openai-python/pulls/1"
            }
        }
    ) == "openai/openai-python"


def test_balanced_timeforward_selection_is_strict_and_balanced() -> None:
    spec = workflow_family.FAMILIES["pr_outcome"]
    store: dict[int, dict[str, object]] = {}
    number = 100
    for day in ("2024-01-01", "2024-02-01"):
        for _ in range(2):
            store[number] = _pr_row(number, day=day, state="open", merged_at=None)
            number += 1
        for _ in range(2):
            store[number] = _pr_row(
                number,
                day=day,
                state="closed",
                merged_at="2024-02-02T00:00:00+00:00",
            )
            number += 1
        for _ in range(2):
            store[number] = _pr_row(number, day=day, state="closed", merged_at=None)
            number += 1

    selection = preflight.select_balanced_timeforward(
        "octo/example",
        spec,
        store,
        discovery_cases=6,
        test_cases=6,
        seed=20260801,
        minimum_gap_days=3,
        excluded_numbers=set(),
    )

    assert selection["discovery_class_counts"] == {
        "open": 2,
        "merged": 2,
        "closed_unmerged": 2,
    }
    assert selection["test_class_counts"] == {
        "open": 2,
        "merged": 2,
        "closed_unmerged": 2,
    }
    assert selection["time_forward"]["strict_time_forward"] is True
    assert selection["time_forward"]["discovery_day_range"]["max"] == "2024-01-01"
    assert selection["time_forward"]["test_day_range"]["min"] == "2024-02-01"
    assert selection["time_forward"]["gap_days"] >= 3
