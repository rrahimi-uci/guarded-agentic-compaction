"""Seal the forced-size calibration extension of the graded issue gate; no provider call.

The amended v2 study (``results_v2.json``) retired its learned gate on 184
calibration groups after the first calibration was observed. This script seals
a *sequential extension*: every remaining eligible, unused issue in the pinned
public snapshot becomes a fresh calibration group. The size is forced by pool
exhaustion, not chosen. The frozen score model, grid, alpha and delta are reused
byte-identically from ``frozen_gate_v2.json`` (hash-pinned here), and the 90
sealed test issues stay untouched until a threshold is fixed on the pooled set.

The original exclusion rule scanned ``paper/results/`` only. The extension also
scans ``experiments/`` so that no record spent by the AWM/generalization studies
can re-enter; the original 474-issue cohort is checked to be disjoint from that
set as well, and the count is disclosed.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import gate_frontier_pilot_preflight as prior
import graded_issue_gate_preflight as cohort
import github_live_study as fixed
import pandas as pd
from guarded_agentic_compaction.grc.calibrate import GRID, clopper_pearson_upper

ROOT = Path(__file__).resolve().parents[2]
STUDY_DIR = ROOT / "paper/results/graded_issue_gate"
OUT = STUDY_DIR / "extension_preflight.json"
PROTOCOL = STUDY_DIR / "extension_protocol.md"
FROZEN_GATE = STUDY_DIR / "frozen_gate_v2.json"
ORIGINAL_RESULT = STUDY_DIR / "results_v2.json"
ORIGINAL_CHECKPOINT = STUDY_DIR / "checkpoint_v2.json"
REGISTRY = STUDY_DIR / "candidate_v2/registry/registry.json"
EXPERIMENTS_ROOT = ROOT / "experiments"
DATASETS_ROOT = ROOT / "paper/results/datasets"
ALPHA = 0.05
DELTA = 0.10
ANALYSIS_PLAN = (
    "primary: Algorithm 1 on the pooled calibration set (184 original + fresh), alpha=0.05, delta=0.10, the same 11-point grid",
    "secondary: Algorithm 1 on the fresh calibration set alone, same settings",
    "conditional: if the pooled analysis admits a threshold, run the 90 sealed test issues under that threshold "
    "(compiled arm where q <= eta, unchanged agent otherwise) plus the unchanged agent on all 90 and the support-only routing; "
    "report task errors with a one-sided 95% Clopper-Pearson bound and the paired discordance",
    "descriptive: violation counts per grid row on the pooled set and a one-sided Fisher exact test that the violation rate "
    "among groups with q above the lowest admissible threshold exceeds the rate at or below it (low power; not a certificate)",
)


def experiments_record_numbers(root: Path = EXPERIMENTS_ROOT) -> set[int]:
    """Issue numbers spent by any study retained under ``experiments/``."""
    used: set[int] = set()
    if not root.exists():
        return used
    for path in root.rglob("*.json"):
        used.update(int(value) for value in prior.RECORD_NUMBER_PATTERN.findall(path.read_text(errors="ignore")))
    return used


def binomial_floors(*, alpha: float = ALPHA, delta: float = DELTA, grid_size: int = len(GRID),
                    max_violations: int = 6) -> dict[str, int]:
    """Smallest accepted-group count that admits ``k`` violations under the registered bound."""
    conf = 1.0 - delta / grid_size
    floors: dict[str, int] = {}
    for k in range(max_violations + 1):
        n = max(k + 1, 1)
        while clopper_pearson_upper(k, n, conf) > alpha:
            n += 1
        floors[str(k)] = n
    return floors


def pool_enlargement_check() -> dict:
    """Whether any other retained snapshot shares the pinned manifest (it must not)."""
    pinned = json.loads(prior.SOURCE_MANIFEST.read_text())
    pinned_sha = pinned["parquet"]["sha256"]
    rows = []
    for manifest in sorted(DATASETS_ROOT.glob("github_*/*/source_manifest.json")):
        data = json.loads(manifest.read_text())
        rows.append({
            "manifest": str(manifest.relative_to(ROOT)),
            "repository": data.get("repository"),
            "parquet_sha256": data.get("parquet_sha256"),
            "same_parquet_as_pinned_snapshot": data.get("parquet_sha256") == pinned_sha,
            "same_github_repository": str(data.get("repository", "")).endswith("huggingface/datasets"),
        })
    return {"pinned_dataset": pinned["dataset"], "pinned_parquet_sha256": pinned_sha,
            "candidates": rows,
            "any_shares_pinned_manifest": any(r["same_parquet_as_pinned_snapshot"] for r in rows),
            "verdict": "no other retained snapshot shares the pinned manifest; the time-forward snapshot is the same "
                       "GitHub repository but a different fetch (post-cutoff records under its own manifest and age "
                       "cutoff), and the multi-repository snapshots are other repositories, so the pool cannot be enlarged"}


def remaining_pool(store: dict[int, dict], excluded: set[int]) -> tuple[list[dict], int]:
    eligible: list[dict] = []
    without_comments = 0
    for number, row in sorted(store.items()):
        if number in excluded or bool(row.get("pull_request")):
            continue
        if not row["comments"]:
            without_comments += 1
            continue
        eligible.append({"issue_number": int(number), "stratum": prior._risk_stratum(row["comments"]),
                         "category": fixed.category_for(row["labels"]), "n_comments": len(row["comments"])})
    return eligible, without_comments


def build() -> dict:
    original = json.loads(cohort.OUT.read_text())
    if original != cohort.build() or original["status"] != "sealed_not_run":
        raise ValueError("original sealed cohort drifted; refusing to seal an extension")
    frozen = json.loads(FROZEN_GATE.read_text())
    result = json.loads(ORIGINAL_RESULT.read_text())
    if result["status"] != "retired_before_test" or result["gate"]["frozen_model"] != frozen["frozen_model"]:
        raise ValueError("frozen gate record does not match the retired v2 result")
    if frozen["learned"]["grid"] != list(GRID) or frozen["learned"]["alpha"] != ALPHA or frozen["learned"]["delta"] != DELTA:
        raise ValueError("registered grid or budget drifted")
    original_ids = {r["issue_number"] for rows in original["selected"].values() for r in rows}
    pilot = json.loads(cohort.PILOT.read_text())["cohort"]
    pilot_ids = set(pilot["held_out_record_numbers"] + pilot["calibration_dev_record_numbers"])
    results_ids = cohort.prior_record_numbers()
    experiments_ids = experiments_record_numbers()
    if original_ids & experiments_ids or pilot_ids & experiments_ids:
        raise ValueError("original cohort overlaps experiments/ records; the v2 result needs a disclosure first")
    excluded = results_ids | pilot_ids | original_ids | experiments_ids
    store, duplicates = fixed.build_store(pd.read_parquet(prior.SNAPSHOT))
    fresh, without_comments = remaining_pool(store, excluded)
    # Records only the invalid 90-record pilot touched would otherwise be eligible; the
    # original exclusion rule treats them as spent and the extension keeps that rule.
    pilot_exclusive = pilot_ids - results_ids - original_ids - experiments_ids
    pilot_only, _ = remaining_pool(store, excluded - pilot_exclusive)
    pilot_still_unused = len(pilot_only) - len(fresh)
    strata = Counter(r["stratum"] for r in fresh)
    return {
        "schema": "gac-graded-issue-gate-extension-preflight/v1",
        "status": "sealed_not_run", "provider_calls_executed": 0,
        "sequential_extension": True,
        "registered_after_first_calibration_observed": True,
        "extension_size_forced_by_pool_exhaustion": True,
        "test_issues_sealed_until_threshold_fixed": 90,
        "source_sha256": cohort.sha256(prior.SNAPSHOT),
        "source_manifest_sha256": cohort.sha256(prior.SOURCE_MANIFEST),
        "original_preflight_sha256": cohort.sha256(cohort.OUT),
        "frozen_gate_v2_sha256": cohort.sha256(FROZEN_GATE),
        "results_v2_sha256": cohort.sha256(ORIGINAL_RESULT),
        "checkpoint_v2_sha256": cohort.sha256(ORIGINAL_CHECKPOINT),
        "candidate_registry_sha256": cohort.sha256(REGISTRY),
        "frozen_model": frozen["frozen_model"],
        "grid": list(GRID), "alpha": ALPHA, "delta": DELTA, "seed": original["seed"],
        "original_calibration_groups": len(original["selected"]["calibration"]),
        "exclusion": {
            "results_tree_record_numbers": len(results_ids),
            "pilot_cohort_record_numbers": len(pilot_ids),
            "original_cohort_record_numbers": len(original_ids),
            "experiments_tree_record_numbers": len(experiments_ids),
            "experiments_record_numbers_not_in_results_tree": len(experiments_ids - results_ids - pilot_ids - original_ids),
            "original_cohort_overlap_with_experiments": 0,
            "union": len(excluded),
            "pilot_records_still_unused_but_excluded": pilot_still_unused,
        },
        "duplicate_source_rows_collapsed": sum(duplicates.values()),
        "remaining_pool": {"eligible_with_comments": len(fresh), "by_stratum": dict(sorted(strata.items())),
                           "by_category": dict(sorted(Counter(r["category"] for r in fresh).items())),
                           "ineligible_without_comments": without_comments},
        "fresh_calibration": fresh,
        "pooled_calibration_groups": len(original["selected"]["calibration"]) + len(fresh),
        "binomial_floors_n_min_by_violations": binomial_floors(),
        "analysis_plan": list(ANALYSIS_PLAN),
        "pool_enlargement_check": pool_enlargement_check(),
        "sampling_frame": "every unused public snapshot issue with at least one comment; no quota, no sampling",
        "evidence_policy": "frozen v2 score and grid; pooled calibration chooses the threshold; test untouched until fixed",
    }


def main() -> None:
    result = build()
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("sealed graded issue gate extension", result["remaining_pool"], "provider calls: 0")


if __name__ == "__main__":
    main()
