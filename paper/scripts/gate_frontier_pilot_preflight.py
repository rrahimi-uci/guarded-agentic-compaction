#!/usr/bin/env python3
"""Provider-free preflight for the gate-frontier pilot (Phase 2 of the prospective protocol).

``paper/supplementary/prospective-gate-frontier-protocol.md`` pre-registers a full study
(>=3 domains, >=300 held-out pairs) but names the real risk: every registered exact-alpha=.05
gate in this paper is step-like, and the likely reason is structural rather than statistical.
Two of the three primary families' own eligibility filters keep only unambiguous, single-label
records, and their quality oracle checks contract compliance (issue number, category, field
shape) rather than a fact that can actually diverge between the compiled prefix and a careful
reading. There is very little room in that design for a record to be genuinely riskier than
another, so a calibrated gate has nothing to discriminate.

This preflight targets a substrate that already refutes that: the natural-order study's
``grade_factual`` oracle checks that ``comment_evidence`` is a verbatim substring of a real
comment (``comment_grounded``), and the sealed record for issue 6602
(``paper/results/github_natural_live/continuation_replay.json``) shows this oracle catching a
real violation -- the compiled arm's returned excerpt did not match the source comment, which
contains a Markdown link. That is a concrete, previously-observed mechanism by which a record's
evidence can be harder to reproduce verbatim than another's, and it gives this pilot something
to stratify on that is not a guess: whether a record's first three comments contain a Markdown
link or a bare URL.

This script only selects and seals a cohort. It makes no provider call, computes no compiler
artifact, and reports no result. Running it costs nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "paper" / "results" / "datasets" / "github_issues" / "train-00000-of-00001.parquet"
SOURCE_MANIFEST = ROOT / "paper" / "results" / "datasets" / "github_issues" / "source_manifest.json"
DEFAULT_OUT = ROOT / "paper" / "results" / "gate_frontier_pilot" / "preflight.json"

# Every prior sealed GitHub study's result tree, so the pilot cohort can never reuse a record
# any earlier discovery, calibration, or held-out set already spent. Excludes external
# benchmarks (NESTFUL, API-Bank, BFCL, AppWorld, ...), which do not share this record space.
RESULTS_ROOT = ROOT / "paper" / "results"
# "gate_frontier_pilot" excludes this preflight's own prior output: without it, re-running
# the preflight after the pilot has executed would treat its own already-selected records
# as "used" and shrink the eligible pool on every subsequent run, which is not what
# "already used by a PRIOR, independent study" is supposed to mean.
EXCLUDED_SUBSTRINGS = (
    "external_benchmarks", "multidomain", "nestful", "frozen_candidate", "gate_frontier_pilot",
)

RECORD_NUMBER_PATTERN = re.compile(r'"(?:issue_number|record_number)"\s*:\s*(\d+)')
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(https?://")
BARE_URL_PATTERN = re.compile(r"https?://\S+")
CATEGORY_LABELS = {"bug", "enhancement", "question"}

SEED = 20260822


def category_for(labels: list[str]) -> str:
    """Mirrors github_live_study.category_for exactly: exactly one of the three, else 'other'."""

    names = {str(label).strip().lower() for label in (labels or ())}
    present = names & CATEGORY_LABELS
    if len(present) == 1:
        return next(iter(present))
    return "other"


def _already_used_record_numbers() -> set[int]:
    used: set[int] = set()
    for path in RESULTS_ROOT.rglob("*.json"):
        if any(marker in str(path) for marker in EXCLUDED_SUBSTRINGS):
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        used.update(int(match) for match in RECORD_NUMBER_PATTERN.findall(text))
    return used


def _risk_stratum(comments: list[str]) -> str:
    """The one empirically-grounded risk feature this pilot stratifies on.

    Not a guess: issue 6602's first comment contains exactly this pattern, and it is the
    recorded cause of the only comment_evidence:mismatch this codebase has on file.
    """

    first_three = [str(comment) for comment in (comments or [])[:3] if str(comment).strip()]
    joined = "\n".join(first_three)
    if MARKDOWN_LINK_PATTERN.search(joined):
        return "markdown_link"
    if BARE_URL_PATTERN.search(joined):
        return "bare_url"
    return "plain_text"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def build_pool() -> list[dict[str, Any]]:
    table = pq.read_table(SNAPSHOT)
    frame = table.to_pandas()
    used = _already_used_record_numbers()
    pool: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        number = int(row["number"])
        if number in used:
            continue
        raw_labels = row["labels"]
        labels = [str(label.get("name", label)) if isinstance(label, dict) else str(label)
                  for label in (raw_labels if raw_labels is not None else [])]
        raw_comments = row["comments"]
        comments = list(raw_comments) if raw_comments is not None else []
        title = str(row.get("title") or "")
        if not title.strip():
            continue
        pool.append({
            "number": number,
            "category": category_for(labels),
            "n_labels": len(labels),
            "n_comments": len(comments),
            "risk_stratum": _risk_stratum(comments),
            "is_pull_request": bool(row.get("pull_request")),
            "state": str(row.get("state") or ""),
        })
    return pool


def select_cohort(pool: list[dict[str, Any]], per_stratum: int, held_out_share: float) -> dict[str, Any]:
    rng = random.Random(SEED)
    by_stratum: dict[str, list[dict[str, Any]]] = {}
    for record in pool:
        # Restrict to plain issues (not pull requests) with at least one comment, so the
        # comment_grounded check is exercised on every selected record rather than trivially
        # satisfied by the "none" sentinel.
        if record["is_pull_request"] or record["n_comments"] == 0:
            continue
        by_stratum.setdefault(record["risk_stratum"], []).append(record)

    cohort: dict[str, list[dict[str, Any]]] = {}
    for stratum, records in by_stratum.items():
        ordered = sorted(records, key=lambda r: r["number"])
        rng.shuffle(ordered)
        cohort[stratum] = ordered[:per_stratum]

    all_selected = [record for records in cohort.values() for record in records]
    rng.shuffle(all_selected)
    n_held_out = max(1, round(len(all_selected) * held_out_share))
    held_out = sorted(all_selected[:n_held_out], key=lambda r: r["number"])
    calibration_dev = sorted(all_selected[n_held_out:], key=lambda r: r["number"])

    return {
        "by_stratum_available": {stratum: len(records) for stratum, records in by_stratum.items()},
        "by_stratum_selected": {stratum: len(records) for stratum, records in cohort.items()},
        "held_out": held_out,
        "calibration_dev": calibration_dev,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-stratum", type=int, default=30,
                         help="records drawn from each risk stratum before splitting")
    parser.add_argument("--held-out-share", type=float, default=0.5)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    started = time.perf_counter()
    if not SNAPSHOT.is_file():
        raise SystemExit(f"pinned snapshot is unavailable at {SNAPSHOT}")

    pool = build_pool()
    used_count = len(_already_used_record_numbers())
    selection = select_cohort(pool, args.per_stratum, args.held_out_share)

    category_mix = {}
    for record in selection["held_out"] + selection["calibration_dev"]:
        category_mix[record["category"]] = category_mix.get(record["category"], 0) + 1

    payload = {
        "schema": "gac-gate-frontier-pilot-preflight/v1",
        "status": "PREFLIGHT_SEALED_NOT_EXECUTED",
        "source_snapshot": {
            "path": str(SNAPSHOT.relative_to(ROOT)),
            "sha256": _sha256(SNAPSHOT),
            "manifest_sha256": _sha256(SOURCE_MANIFEST) if SOURCE_MANIFEST.is_file() else None,
        },
        "risk_stratification": {
            "feature": "markdown_link_or_bare_url_in_first_three_comments",
            "grounded_in": (
                "paper/results/github_natural_live/continuation_replay.json, issue 6602: "
                "the only recorded comment_evidence:mismatch in this codebase, caused by a "
                "Markdown link in the source comment"
            ),
            "pool_size_after_exclusions": len(pool),
            "already_used_record_numbers_excluded": used_count,
        },
        "cohort": {
            "seed": SEED,
            "per_stratum_target": args.per_stratum,
            "by_stratum_available_in_pool": selection["by_stratum_available"],
            "by_stratum_selected": selection["by_stratum_selected"],
            "held_out_count": len(selection["held_out"]),
            "calibration_dev_count": len(selection["calibration_dev"]),
            "category_mix_bug_enhancement_question_other": category_mix,
            "held_out_record_numbers": [r["number"] for r in selection["held_out"]],
            "calibration_dev_record_numbers": [r["number"] for r in selection["calibration_dev"]],
        },
        "provider_calls_made": 0,
        "runtime_seconds": time.perf_counter() - started,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    print(f"wrote {args.output.relative_to(ROOT)}")
    print(f"  pool after excluding {used_count} already-used records: {len(pool)}")
    print(f"  strata available: {selection['by_stratum_available']}")
    print(f"  strata selected:  {selection['by_stratum_selected']}")
    print(f"  held-out {len(selection['held_out'])} / calibration+dev {len(selection['calibration_dev'])}")
    print(f"  category mix (bug/enhancement/question/other): {category_mix}")
    print("  provider calls made: 0")


if __name__ == "__main__":
    main()
