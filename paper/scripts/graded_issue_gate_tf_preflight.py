"""Provider-free feasibility preflight for the fresh-issue single-look gate replication.

Strategy C of ``flip-plans.md``: re-run the frozen v2 graded issue gate once on an
independent pool, the post-cutoff ``huggingface/datasets`` issues. This script only
counts. It verifies that the pool supports the graded issue task (issues with at
least one comment, never used by any retained study), reports the distribution of
the six entry descriptors, and computes the design arithmetic (discovery split,
calibration size, exact admission floors, acceptance counts under the frozen score).
It then applies the pre-declared go rule: at least ``MIN_CALIBRATION_GROUPS``
calibration groups must remain after ``DISCOVERY_ISSUES`` discovery issues.

No provider call, no network access, and no record is selected for a study here.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src", ROOT / "paper/scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import gate_frontier_pilot_preflight as prior  # noqa: E402
import github_live_study as fixed  # noqa: E402
from guarded_agentic_compaction.grc.calibrate import GRID, clopper_pearson_upper  # noqa: E402
from guarded_agentic_compaction.schema.artifacts import GateModel  # noqa: E402

STUDY_DIR = ROOT / "paper/results/graded_issue_gate_tf"
OUT = STUDY_DIR / "preflight.json"
SNAPSHOT_DIR = ROOT / "paper/results/datasets/github_time_forward/huggingface__datasets"
SNAPSHOT = SNAPSHOT_DIR / "snapshot.parquet"
SNAPSHOT_MANIFEST = SNAPSHOT_DIR / "source_manifest.json"
FROZEN_GATE = ROOT / "paper/results/graded_issue_gate/frozen_gate_v2.json"
FROZEN_GATE_SHA256 = "c66af83acac0bc883f970140e874560ef35ff9f80144d0115e13e763d918c35a"
SCAN_ROOTS = (ROOT / "paper/results", ROOT / "experiments")
OWN_DIR_MARKER = "/graded_issue_gate_tf/"
SKIP_DIR_MARKER = "/datasets/"  # raw snapshots and their manifests are data, not studies
# Studies sealed after this preflight (2026-11-07) whose records never changed its count:
# the compiler-funnel live pilot (2026-11-08) runs on the same post-cutoff issues by design.
POST_SEALING_MARKERS = ("/compiler_funnel_pilot/",)
ALPHA = 0.05
DELTA = 0.10
SEED = 20261107
DISCOVERY_ISSUES = 80
MIN_CALIBRATION_GROUPS = 150  # the pre-declared "meaningful design" floor (about 150)
PINNED_AGE_CUTOFF = "2025-06-13"  # graded_issue_gate_study.risk_read: the pinned snapshot's last day
FEATURES = ("markdown_link", "bare_url", "log_comments", "label_count", "title_length", "age_years")
ASSUMED_ERROR_RATES = (0.0153, 0.02, 0.0443)  # extension point estimate 4/261; a stress value; its nominal bound
# Result files whose record numbers live in a different record space (BIRD question ids,
# other repositories' pull requests). They are excluded under the literal rule and listed
# separately so the sensitivity can be recomputed without them.
OTHER_RECORD_SPACE_MARKERS = (
    "/bird/", "bird_source_screen", "adaptive_comparison_preflight/source_audit",
    "github_multirepo_pr_outcome_balanced", "multirepo_pr_outcome_balance_analysis",
)
_KEY = re.compile(r"(number|issue|record|ids?$|selected|cohort)", re.I)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ints(value: Any):
    if isinstance(value, bool):
        return
    if isinstance(value, int):
        yield value
    elif isinstance(value, str) and value.isdigit():
        yield int(value)
    elif isinstance(value, list):
        for item in value:
            yield from _ints(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _ints(item)


def _keyed_numbers(obj: Any, wanted: set[int], out: set[int]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if _KEY.search(str(key)):
                out.update(i for i in _ints(value) if i in wanted)
            _keyed_numbers(value, wanted, out)
    elif isinstance(obj, list):
        for value in obj:
            _keyed_numbers(value, wanted, out)


def used_records(wanted: set[int], roots: tuple[Path, ...] = SCAN_ROOTS, base: Path = ROOT) -> tuple[dict[int, list[str]], dict[int, list[str]]]:
    """Map each wanted record number to the retained files that mention it, under two rules.

    Returns ``(field_hits, broad_hits)``. ``field_hits`` is the repository's established
    ``issue_number`` / ``record_number`` field rule (the literal exclusion rule of every
    earlier preflight). ``broad_hits`` adds a walk over any key that names a number, issue,
    record, id list, selection or cohort, and so also catches id lists. Both trees
    (``paper/results`` and ``experiments``) are scanned. This study's own directory and
    the raw snapshot directories are skipped.
    """
    field: dict[int, set[str]] = {}
    broad: dict[int, set[str]] = {}
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            text_path = "/" + path.relative_to(base).as_posix()
            if OWN_DIR_MARKER in text_path or SKIP_DIR_MARKER in text_path or any(m in text_path for m in POST_SEALING_MARKERS):
                continue
            try:
                text = path.read_text(errors="ignore")
            except OSError:
                continue
            by_field = {int(v) for v in prior.RECORD_NUMBER_PATTERN.findall(text)} & wanted
            found = set(by_field)
            if path.stat().st_size <= 80_000_000:
                try:
                    _keyed_numbers(json.loads(text), wanted, found)
                except (json.JSONDecodeError, RecursionError):
                    pass
            rel = path.relative_to(base).as_posix()
            for number in by_field:
                field.setdefault(number, set()).add(rel)
            for number in found:
                broad.setdefault(number, set()).add(rel)
    return ({n: sorted(f) for n, f in sorted(field.items())}, {n: sorted(f) for n, f in sorted(broad.items())})


def descriptors(row: dict[str, Any], age_cutoff: date) -> dict[str, float]:
    """The six entry descriptors of ``graded_issue_gate_study.risk_read`` with a chosen age cutoff."""
    stratum = prior._risk_stratum(row["comments"])
    created = date.fromisoformat(str(row["day"])[:10])
    return {
        "markdown_link": float(stratum == "markdown_link"),
        "bare_url": float(stratum == "bare_url"),
        "log_comments": math.log1p(len(row["comments"])),
        "label_count": float(len(row["labels"])),
        "title_length": float(len(row["title"])) / 100.0,
        "age_years": max(0, (age_cutoff - created).days) / 365.25,
    }


def max_admissible_k(n: int, *, alpha: float = ALPHA, delta: float = DELTA, grid_size: int = len(GRID)) -> int:
    """Largest violation count whose one-sided Clopper-Pearson bound at level 1-delta/|grid| is <= alpha (-1: none)."""
    if n <= 0:
        return -1
    conf = 1.0 - delta / grid_size
    best = -1
    for k in range(0, n + 1):
        if clopper_pearson_upper(k, n, conf) <= alpha:
            best = k
        else:
            break
    return best


def admission_probability(n: int, kmax: int, rate: float) -> float:
    """P(Binomial(n, rate) <= kmax); zero when no violation count is admissible."""
    if kmax < 0 or n <= 0:
        return 0.0
    return float(sum(math.comb(n, j) * rate**j * (1 - rate) ** (n - j) for j in range(kmax + 1)))


def _stable_key(number: int) -> str:
    return hashlib.sha256(f"graded-issue-tf:{SEED}:{number}".encode()).hexdigest()


def _summary(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    n = len(ordered)
    return {"mean": round(sum(ordered) / n, 4), "min": round(ordered[0], 4),
            "median": round(ordered[n // 2], 4), "max": round(ordered[-1], 4)} if n else {}


def acceptance_table(rows: list[dict], model: GateModel, age_cutoff: date) -> dict[str, int]:
    scores = [model.score(descriptors(r, age_cutoff)) for r in rows]
    return {f"{eta:.2f}": sum(score <= eta for score in scores) for eta in GRID}


def design_arithmetic(pool_size: int, label: str, accepted_at_050: int) -> dict[str, Any]:
    calibration = max(pool_size - DISCOVERY_ISSUES, 0)
    kmax = max_admissible_k(accepted_at_050)
    return {
        "pool": pool_size, "discovery": DISCOVERY_ISSUES, "calibration_groups": calibration,
        "meets_minimum_calibration": calibration >= MIN_CALIBRATION_GROUPS,
        "accepted_at_eta_0.50_if_all_dispatch": accepted_at_050,
        "max_admissible_k_at_eta_0.50": kmax,
        "admission_probability_at_assumed_error_rate": {
            f"{rate}": round(admission_probability(accepted_at_050, kmax, rate), 4) for rate in ASSUMED_ERROR_RATES},
        "label": label,
    }


def build() -> dict[str, Any]:
    manifest = json.loads(SNAPSHOT_MANIFEST.read_text())
    if sha256(SNAPSHOT) != manifest["parquet_sha256"]:
        raise ValueError("time-forward snapshot does not match its manifest")
    if sha256(FROZEN_GATE) != FROZEN_GATE_SHA256:
        raise ValueError("frozen_gate_v2.json drifted from the registered hash")
    frozen = json.loads(FROZEN_GATE.read_text())
    if frozen["learned"]["grid"] != list(GRID) or frozen["learned"]["alpha"] != ALPHA or frozen["learned"]["delta"] != DELTA:
        raise ValueError("registered grid or budget drifted")
    model = GateModel.from_dict(frozen["frozen_model"])

    store, duplicates = fixed.build_store(pd.read_parquet(SNAPSHOT))
    with_comments = {n: r for n, r in store.items() if r["comments"]}
    field_hits, hits = used_records(set(with_comments))
    literal = [with_comments[n] for n in sorted(with_comments) if n not in field_hits]
    same_space_used = {n for n, files in hits.items()
                       if any(not any(m in "/" + f for m in OTHER_RECORD_SPACE_MARKERS) for f in files)}
    sensitivity = [with_comments[n] for n in sorted(with_comments) if n not in same_space_used]

    snapshot_last_day = date.fromisoformat(max(str(r["day"])[:10] for r in store.values()))
    cutoffs = {"snapshot_relative_age": snapshot_last_day, "fixed_pinned_cutoff_age": date.fromisoformat(PINNED_AGE_CUTOFF)}
    # Which age convention the study would use is fixed here, before any outcome exists.
    primary_cutoff_name = "snapshot_relative_age"

    def distribution(rows: list[dict]) -> dict[str, Any]:
        cutoff = cutoffs[primary_cutoff_name]
        feats = [descriptors(r, cutoff) for r in rows]
        strata = Counter(prior._risk_stratum(r["comments"]) for r in rows)
        out: dict[str, Any] = {"n": len(rows), "markdown_link": strata.get("markdown_link", 0),
                               "bare_url": strata.get("bare_url", 0), "plain_text": strata.get("plain_text", 0)}
        for name in FEATURES[2:]:
            out[name] = _summary([f[name] for f in feats])
        out["category"] = dict(sorted(Counter(fixed.category_for(r["labels"]) for r in rows).items()))
        out["state"] = dict(sorted(Counter(r["state"] for r in rows).items()))
        return out

    ranked = sorted(literal, key=lambda r: _stable_key(r["number"]))
    illustrative_calibration = ranked[DISCOVERY_ISSUES:]
    ranked_sens = sorted(sensitivity, key=lambda r: _stable_key(r["number"]))
    illustrative_calibration_sens = ranked_sens[DISCOVERY_ISSUES:]

    acceptance = {}
    for name, cutoff in cutoffs.items():
        acceptance[name] = {"literal_pool_calibration": acceptance_table(illustrative_calibration, model, cutoff),
                            "same_record_space_pool_calibration": acceptance_table(illustrative_calibration_sens, model, cutoff)}
    acc_literal = acceptance[primary_cutoff_name]["literal_pool_calibration"]["0.50"]
    acc_sens = acceptance[primary_cutoff_name]["same_record_space_pool_calibration"]["0.50"]
    design = {
        "literal_exclusion": design_arithmetic(len(literal), "every record number under paper/results and experiments (issue_number/record_number fields)", acc_literal),
        "same_record_space_exclusion": design_arithmetic(len(sensitivity), "upper bound: only same record-space uses excluded", acc_sens),
    }
    go = design["literal_exclusion"]["meets_minimum_calibration"]
    go_upper = design["same_record_space_exclusion"]["meets_minimum_calibration"]
    return {
        "schema": "gac-graded-issue-gate-tf-preflight/v1",
        "provider_calls_executed": 0,
        "status": "go" if go else "no_go_pool_too_small",
        "decision_rule": f"go iff calibration groups >= {MIN_CALIBRATION_GROUPS} after {DISCOVERY_ISSUES} discovery issues",
        "snapshot": {"path": SNAPSHOT.relative_to(ROOT).as_posix(), "sha256": manifest["parquet_sha256"],
                     "repository": manifest["repository"], "created_after_utc_day": manifest["created_after_utc_day"],
                     "last_created_day": snapshot_last_day.isoformat(), "records": manifest["records"],
                     "issues": len(store), "pull_requests_removed": manifest["pull_requests"],
                     "duplicate_rows_collapsed": sum(duplicates.values())},
        "frozen_gate_v2_sha256": FROZEN_GATE_SHA256, "grid": list(GRID), "alpha": ALPHA, "delta": DELTA,
        "task": "graded issue task of graded_issue_gate_study.py (final factual contract, six entry descriptors)",
        "pool_accounting": {
            "issues_in_snapshot": len(store),
            "issues_without_comments": len(store) - len(with_comments),
            "issues_with_at_least_one_comment": len(with_comments),
            "excluded_by_field_rule": len(field_hits),
            "flagged_by_broad_key_walk": len(hits),
            "flagged_same_record_space": len(same_space_used),
            "flagged_other_record_space_only": len(hits) - len(same_space_used),
            "pool_literal_rule": len(literal),
            "pool_same_record_space_rule": len(sensitivity),
            "field_rule_hits_by_file_family": dict(sorted(Counter(
                f.rsplit("/", 1)[0] for files in field_hits.values() for f in files).items())),
            "excluded_numbers_field_rule": sorted(field_hits),
            "excluded_numbers_same_record_space": sorted(same_space_used),
        },
        "descriptor_distribution": {
            "age_convention": primary_cutoff_name,
            "all_issues_with_comments": distribution(list(with_comments.values())),
            "literal_pool": distribution(literal),
            "same_record_space_pool": distribution(sensitivity),
        },
        "age_convention": {
            "note": ("The frozen v2 age descriptor is days from creation to the pinned snapshot's last day, clipped at zero. "
                     "Applied literally (fixed cutoff 2025-06-13) every post-cutoff issue has age 0. The replication would use "
                     "the time-forward snapshot's own last created day, the same quantity for this snapshot."),
            "snapshot_last_day": snapshot_last_day.isoformat(), "primary": primary_cutoff_name,
        },
        "acceptance_if_all_dispatch": acceptance,
        "discovery_split_seed": SEED,
        "design": design,
        "admission_floors_registered_grid_m1": {str(n): max_admissible_k(n) for n in (92, 100, 106, 117, 132, 150, 168, 200)},
        "no_go": not go,
        "no_go_even_under_same_record_space_rule": not go_upper,
        "reading": ("The pool cannot supply the planned single look. " if not go else "The pool supports the planned single look. ") +
                   f"{len(literal)} issues pass the literal exclusion rule and {len(sensitivity)} pass the most generous one; "
                   f"after {DISCOVERY_ISSUES} discovery issues that leaves {max(len(literal) - DISCOVERY_ISSUES, 0)} and "
                   f"{max(len(sensitivity) - DISCOVERY_ISSUES, 0)} calibration groups against the floor of {MIN_CALIBRATION_GROUPS}.",
    }


def main() -> None:
    result = build()
    STUDY_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(result["status"], result["reading"], "provider calls: 0")


if __name__ == "__main__":
    main()
