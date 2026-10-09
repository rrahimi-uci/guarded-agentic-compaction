"""Seal a disjoint, stratified public-issue cohort without provider calls.

Markdown strata guide sampling only. The registered gate may inspect comments
only through its separately counted pre-dispatch read, never through test labels.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import gate_frontier_pilot_preflight as prior
import github_live_study as fixed
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/results/graded_issue_gate/preflight.json"
PILOT = ROOT / "paper/results/gate_frontier_pilot/preflight.json"
SEED = 20261008
QUOTAS = {
    "development": {"plain_text": 80, "bare_url": 60, "markdown_link": 60},
    "calibration": {"plain_text": 76, "bare_url": 55, "markdown_link": 53},
    "test": {"plain_text": 37, "bare_url": 30, "markdown_link": 23},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prior_record_numbers() -> set[int]:
    """Exclude earlier studies, but never count this study's own checkpoints."""
    used: set[int] = set()
    excluded_paths = (*prior.EXCLUDED_SUBSTRINGS, "/graded_issue_gate/")
    for path in prior.RESULTS_ROOT.rglob("*.json"):
        if any(marker in str(path) for marker in excluded_paths):
            continue
        used.update(int(value) for value in prior.RECORD_NUMBER_PATTERN.findall(
            path.read_text(errors="ignore")
        ))
    return used


def select(pool: list[dict], excluded: set[int]) -> dict:
    by_stratum: dict[str, list[dict]] = {stratum: [] for stratum in QUOTAS["development"]}
    for row in pool:
        number = int(row["number"])
        if number in excluded or row["is_pull_request"] or not row["n_comments"]:
            continue
        by_stratum[row["risk_stratum"]].append(row)
    selected: dict[str, list[dict]] = {split: [] for split in QUOTAS}
    for stratum, rows in by_stratum.items():
        rows.sort(key=lambda row: hashlib.sha256(f"graded-issue:{SEED}:{stratum}:{row['number']}".encode()).hexdigest())
        needed = sum(quota[stratum] for quota in QUOTAS.values())
        if len(rows) < needed:
            raise ValueError(f"{stratum}: {len(rows)} eligible, need {needed}")
        start = 0
        for split, quotas in QUOTAS.items():
            count = quotas[stratum]
            selected[split].extend({"issue_number": int(row["number"]), "stratum": stratum,
                                    "category": row["category"], "n_comments": row["n_comments"]}
                                   for row in rows[start:start + count])
            start += count
    for rows in selected.values():
        rows.sort(key=lambda row: row["issue_number"])
    ids = [row["issue_number"] for rows in selected.values() for row in rows]
    if len(ids) != len(set(ids)) or set(ids) & excluded:
        raise ValueError("selected records overlap")
    return {"available": {key: len(value) for key, value in by_stratum.items()},
            "selected": selected,
            "selected_category_counts": {split: dict(Counter(r["category"] for r in rows))
                                         for split, rows in selected.items()}}


def build() -> dict:
    manifest = json.loads(prior.SOURCE_MANIFEST.read_text())
    expected_sha = manifest["parquet"]["sha256"]
    actual_sha = sha256(prior.SNAPSHOT)
    if actual_sha != expected_sha:
        raise ValueError("public source snapshot does not match its pinned manifest")
    earlier = json.loads(PILOT.read_text())
    cohort = earlier["cohort"]
    pilot_ids = set(cohort["held_out_record_numbers"] + cohort["calibration_dev_record_numbers"])
    excluded = prior_record_numbers() | pilot_ids
    # The raw parquet contains repeated issue numbers; use the study's canonical
    # most-recent-row rule before sampling distinct calibration groups.
    store, duplicates = fixed.build_store(pd.read_parquet(prior.SNAPSHOT))
    pool = [{"number": number, "category": fixed.category_for(row["labels"]),
             "n_comments": len(row["comments"]), "is_pull_request": bool(row.get("pull_request")),
             "risk_stratum": prior._risk_stratum(row["comments"])}
            for number, row in store.items()]
    choice = select(pool, excluded)
    return {
        "schema": "gac-graded-issue-gate-preflight/v1",
        "status": "sealed_not_run", "provider_calls_executed": 0, "seed": SEED,
        "source_sha256": actual_sha, "source_manifest_sha256": sha256(prior.SOURCE_MANIFEST),
        "prior_pilot_preflight_sha256": sha256(PILOT),
        "additional_prior_pilot_ids_excluded": len(pilot_ids),
        "all_prior_ids_excluded": len(excluded),
        "duplicate_source_rows_collapsed": sum(duplicates.values()),
        "quota_by_stratum_and_role": QUOTAS,
        "sampling_frame": "unused public snapshot issues with at least one comment; fixed stratum quotas",
        "target_population": "the three-stratum quota mixture, not the natural issue frequency",
        "evidence_policy": "development fits score; calibration chooses threshold; test untouched until frozen",
        **choice,
    }


def main() -> None:
    result = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("sealed graded issue cohort", {key: len(value) for key, value in result["selected"].items()},
          "provider calls: 0")


if __name__ == "__main__":
    main()
