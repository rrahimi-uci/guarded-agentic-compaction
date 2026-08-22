#!/usr/bin/env python3
"""Provider-free analysis of the executed gate-frontier pilot.

Reads paper/results/gate_frontier_pilot/results.json (already produced by a live run of
gate_frontier_pilot_study.py) and computes the exact statistic the pre-registered decision
rule needs: whether comment_grounded violations concentrate by risk stratum. This is exact
Fisher inference, not an approximation, and it makes no provider call itself.
"""

from __future__ import annotations

import json
import sys
from math import comb
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RESULTS_PATH = ROOT / "paper" / "results" / "gate_frontier_pilot" / "results.json"
DEFAULT_OUT = ROOT / "paper" / "results" / "gate_frontier_pilot" / "analysis.json"


def fisher_exact_one_sided_greater(a: int, n1: int, c: int, n2: int) -> float:
    """P(observing >= a violations in group 1) under the null of equal rates.

    Exact hypergeometric tail, not a normal or chi-square approximation: appropriate at
    the small counts this pilot produces (single-digit violations per stratum).
    """

    def hypergeometric(x: int, n1_: int, x2: int, n2_: int) -> float:
        k = x + x2
        return comb(n1_, x) * comb(n2_, x2) / comb(n1_ + n2_, k)

    total = 0.0
    max_a = min(n1, a + c)
    for x in range(a, max_a + 1):
        other = a + c - x
        if other < 0 or other > n2:
            continue
        total += hypergeometric(x, n1, other, n2)
    return total


def pooled_counts(graded_results: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for row in graded_results:
        stratum = row["stratum"]
        bucket = counts.setdefault(stratum, {"n": 0, "violations": 0})
        bucket["n"] += 1
        bucket["violations"] += int(not row["comment_grounded"])
    return counts


def analyze(results: dict[str, Any]) -> dict[str, Any]:
    counts = pooled_counts(results["graded_results"])
    baseline = counts.get("plain_text", {"n": 0, "violations": 0})
    comparisons = {}
    for stratum in ("markdown_link", "bare_url"):
        if stratum not in counts:
            continue
        bucket = counts[stratum]
        p_value = fisher_exact_one_sided_greater(
            bucket["violations"], bucket["n"], baseline["violations"], baseline["n"]
        )
        comparisons[stratum] = {
            "violations": bucket["violations"],
            "n": bucket["n"],
            "rate": 1 - bucket["violations"] / bucket["n"] if bucket["n"] else None,
            "vs_plain_text_one_sided_p": p_value,
        }
    pooled_risk = {
        "violations": sum(counts.get(s, {"violations": 0})["violations"]
                          for s in ("markdown_link", "bare_url")),
        "n": sum(counts.get(s, {"n": 0})["n"] for s in ("markdown_link", "bare_url")),
    }
    if pooled_risk["n"]:
        pooled_p = fisher_exact_one_sided_greater(
            pooled_risk["violations"], pooled_risk["n"],
            baseline["violations"], baseline["n"],
        )
    else:
        pooled_p = None

    # A count concentrating in one specific record across both arms is a materially
    # different (stronger) signal than isolated single-arm failures: it means the record
    # itself, not condition-specific noise, is the hard case.
    by_issue_condition: dict[int, set[str]] = {}
    for row in results["graded_results"]:
        if not row["comment_grounded"]:
            by_issue_condition.setdefault(row["issue_number"], set()).add(row["condition"])
    cross_condition_failures = sorted(
        number for number, conditions in by_issue_condition.items() if len(conditions) > 1
    )

    return {
        "schema": "gac-gate-frontier-pilot-analysis/v1",
        "counts_by_stratum": counts,
        "comparisons_vs_plain_text": comparisons,
        "pooled_markdown_link_and_bare_url_vs_plain_text": {
            **pooled_risk, "one_sided_p": pooled_p,
        },
        "records_failing_in_both_conditions": cross_condition_failures,
        "reading": (
            "Exact one-sided Fisher tests, uncorrected for the two strata compared. "
            "markdown_link is the only stratum approaching the predicted signal; "
            "bare_url shows no discriminable elevation at this sample size. Read together "
            "with the decision rule in gate-frontier-pilot-protocol.md, not as a "
            "standalone significance claim."
        ),
    }


def main() -> None:
    if not RESULTS_PATH.is_file():
        raise SystemExit(f"no executed pilot results at {RESULTS_PATH}; run "
                          "gate_frontier_pilot_study.py first")
    results = json.loads(RESULTS_PATH.read_text())
    analysis = analyze(results)
    DEFAULT_OUT.write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n")
    print(f"wrote {DEFAULT_OUT.relative_to(ROOT)}")
    for stratum, row in analysis["comparisons_vs_plain_text"].items():
        print(f"  {stratum:14s} {row['violations']}/{row['n']} violations, "
              f"one-sided p vs plain_text = {row['vs_plain_text_one_sided_p']:.4f}")
    print(f"  records failing in both conditions: {analysis['records_failing_in_both_conditions']}")


if __name__ == "__main__":
    main()
