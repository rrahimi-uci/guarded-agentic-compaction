"""Provider-free preflight for the time-forward cohort (proposal-90.md A2 / C2).

Reads the time-forward snapshot acquired from the GitHub API, classes every record under the
three primary families' own class rules, removes every record number that any retained study
under ``paper/results`` has already evaluated or selected (any ``issue_number`` /
``record_number`` field anywhere in a ``huggingface/datasets`` result or checkpoint), and
reports, per family, whether the fresh pool can supply disjoint calibration and test sets:
calibration >= 45 eligible groups (single-rule, m=1, zero violations) or >= 77 (one violation),
test >= 60 class-balanced (20 per class). Writes ``preflight.json`` beside the snapshot.
No provider call; no record is selected here, only counted.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

SNAPSHOT_DIR = ROOT / "paper/results/datasets/github_time_forward/huggingface__datasets"
RESULTS = ROOT / "paper/results"
FLOORS = {"calibration_zero_violations_m1": 45, "calibration_one_violation_m1": 77, "calibration_zero_violations_m2": 59,
          "registered_grid_m1": 92, "test_total": 60, "test_per_class": 20}


def _numbers(value: Any) -> Iterator[int]:
    if isinstance(value, dict):
        for k, v in value.items():
            if k in ("issue_number", "record_number", "number") and isinstance(v, (int, str)) and str(v).isdigit():
                yield int(v)
            else:
                yield from _numbers(v)
    elif isinstance(value, list):
        for v in value:
            yield from _numbers(v)


def used_records() -> tuple[set[int], dict[str, int]]:
    """Every huggingface/datasets record number any retained result or checkpoint mentions."""
    used: set[int] = set()
    per_file: dict[str, int] = {}
    for path in sorted(RESULTS.rglob("*.json")):
        if "datasets/" in str(path.relative_to(RESULTS)) or path.stat().st_size > 60_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "huggingface/datasets" not in text and "github-issue" not in text and "issue_number" not in text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        found = set(_numbers(payload))
        if found:
            per_file[str(path.relative_to(ROOT))] = len(found)
            used |= found
    return used, per_file


def main() -> int:
    import pandas as pd

    import github_live_study as fixed
    import github_workflow_family_study as fam

    manifest = json.loads((SNAPSHOT_DIR / "source_manifest.json").read_text())
    frame = pd.read_parquet(SNAPSHOT_DIR / "snapshot.parquet")
    rows = frame.to_dict(orient="records")
    for row in rows:
        row["number"] = int(row["number"])
        row["comments"] = [str(v) for v in (list(row.get("comments")) if row.get("comments") is not None else [])]
        row["assignees"] = [dict(v) for v in (list(row.get("assignees")) if row.get("assignees") is not None else []) if isinstance(v, dict)]
        row["labels"] = [dict(v) for v in (list(row.get("labels")) if row.get("labels") is not None else []) if isinstance(v, dict)]
        pr = row.get("pull_request")
        row["pull_request"] = dict(pr) if isinstance(pr, dict) and any(v for v in pr.values()) else None
    used, per_file = used_records()
    fresh = [r for r in rows if r["number"] not in used]
    # the pinned snapshot's own numbers, for a second overlap check
    pinned = set(int(n) for n in pd.read_parquet(fixed.DATA_PATH, columns=["number"])["number"])
    out: dict[str, Any] = {
        "schema": "agent-compaction-time-forward-preflight/v1",
        "snapshot": manifest, "records": len(rows), "created_after": manifest["created_after_utc_day"],
        "used_record_numbers_known": len(used), "used_record_files": len(per_file),
        "overlap_with_used": sorted(r["number"] for r in rows if r["number"] in used),
        "overlap_with_pinned_snapshot": sorted(r["number"] for r in rows if r["number"] in pinned),
        "fresh_records": len(fresh), "provider_calls_executed": 0, "families": {},
    }
    issues = [r for r in fresh if not r.get("pull_request")]
    prs = [r for r in fresh if r.get("pull_request")]
    # issue-type routing: exclusive label category (github_live_study.category_for)
    cats = Counter(fixed.category_for([lab.get("name", "") for lab in r["labels"]]) for r in issues)
    exclusive = {k: v for k, v in cats.items() if k in ("bug", "enhancement", "question")}
    out["families"]["issue_type"] = {
        "pool": len(issues), "classes": dict(cats), "exclusive_classes": exclusive,
        "test_balanced_possible": all(exclusive.get(c, 0) >= FLOORS["test_per_class"] for c in ("bug", "enhancement", "question")),
        "after_test_remaining": sum(exclusive.values()) - 3 * FLOORS["test_per_class"],
    }
    pr_classes = Counter(fam.pr_outcome(r) for r in prs)
    out["families"]["pr_outcome"] = {
        "pool": len(prs), "classes": dict(pr_classes),
        "test_balanced_possible": all(pr_classes.get(c, 0) >= FLOORS["test_per_class"] for c in ("open", "merged", "closed_unmerged")),
        "after_test_remaining": len(prs) - 3 * FLOORS["test_per_class"],
    }
    bl_classes = Counter(fam.backlog_route(r) for r in issues)
    out["families"]["backlog_attention"] = {
        "pool": len(issues), "classes": dict(bl_classes),
        "test_balanced_possible": all(bl_classes.get(c, 0) >= FLOORS["test_per_class"] for c in ("owned", "discussed_unowned", "awaiting_first_response")),
        "after_test_remaining": len(issues) - 3 * FLOORS["test_per_class"],
    }
    for name, f in out["families"].items():
        remaining = f["after_test_remaining"]
        f["calibration_floors"] = {k: v for k, v in FLOORS.items() if k.startswith("calibration") or k == "registered_grid_m1"}
        f["go"] = {k: bool(f["test_balanced_possible"] and remaining >= v) for k, v in f["calibration_floors"].items()}
        f["reading"] = ("GO: balanced test and single-rule zero-violation calibration are both coverable"
                        if f["go"]["calibration_zero_violations_m1"] else "NO-GO at the single-rule floor; see classes")
    (SNAPSHOT_DIR / "preflight.json").write_text(json.dumps(out, indent=2, sort_keys=True, default=str) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k in ("records", "fresh_records", "used_record_numbers_known")}))
    for name, f in out["families"].items():
        print(name, f["classes"], f.get("exclusive_classes", ""), f["reading"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
