"""Retrospective paired-quality uncertainty and database/failure sensitivity.

No provider calls. Missing own-arm outcomes count as incorrect. Intervals
assume i.i.d. question pairs and are pointwise by cohort, not simultaneous
across cohorts. Database deletions are descriptive sensitivity, not inference.
"""
from __future__ import annotations

import hashlib
import json
from math import fsum
from pathlib import Path

from scipy.stats import binomtest

from audit_bird_denominators import audit_cohort

ROOT = Path(__file__).resolve().parents[2]
COHORTS = {
    "primary": (".", "."),
    "rotated": ("rotated_rerun", "."),
    "second_model": ("replications/gpt-6-luna", "replications/gpt-6-luna"),
    "train": ("train", "train"),
}


def paired_interval(gains: int, losses: int, n: int, confidence: float = .95) -> list[float]:
    """Bonferroni difference of two CP intervals, preserving paired discordance.

    P(GAC correct) - P(base correct) = P(gain) - P(loss). Each marginal
    interval fails with probability <= (1-confidence)/2; a union bound needs
    no independence between the mutually exclusive gain and loss indicators.
    Independence and identical distribution across question pairs are assumed.
    """
    if n <= 0 or min(gains, losses) < 0 or gains + losses > n or not 0 < confidence < 1:
        raise ValueError("invalid paired counts or confidence")
    marginal_confidence = 1 - (1 - confidence) / 2
    gain = binomtest(gains, n).proportion_ci(marginal_confidence, method="exact")
    loss = binomtest(losses, n).proportion_ci(marginal_confidence, method="exact")
    return [float(gain.low - loss.high), float(gain.high - loss.low)]


def summarize(root: Path, selection_root: Path) -> dict:
    audited = audit_cohort(root, selection_root)
    preflight = selection_root / "preflight.json"
    selections = json.loads(preflight.read_text())["selections"]
    sources = {"selection/preflight.json": hashlib.sha256(preflight.read_bytes()).hexdigest()}
    sources.update({"evaluation/" + k: v for k, v in audited["source_sha256"].items()})
    blocks = []
    costs = {"baseline": [], "compiled": []}
    for db, split in sorted(selections.items()):
        compile_path = selection_root / "schema_first" / db / "compile.json"
        if not compile_path.exists():
            continue
        sources["selection/" + str(compile_path.relative_to(selection_root))] = hashlib.sha256(compile_path.read_bytes()).hexdigest()
        if json.loads(compile_path.read_text())["status"] != "admitted":
            continue
        evaluation = json.loads((root / "schema_first" / db / "evaluation.json").read_text())
        rows = {arm: {int(r["issue_number"]): r for r in evaluation["results"] if r["condition"] == arm}
                for arm in costs}
        gains = losses = 0
        for question in split["test"]:
            correct = {arm: bool(rows[arm].get(int(question), {}).get("quality", {}).get("overall", False))
                       for arm in costs}
            gains += correct["compiled"] and not correct["baseline"]
            losses += correct["baseline"] and not correct["compiled"]
        for arm in costs:
            costs[arm].extend(row["metrics"]["estimated_cost_usd"] for row in rows[arm].values())
        blocks.append({"database": db, "n": len(split["test"]), "gains": gains, "losses": losses})
    n = sum(b["n"] for b in blocks)
    gains = sum(b["gains"] for b in blocks)
    losses = sum(b["losses"] for b in blocks)
    if (n, gains, losses) != (audited["scheduled_questions"], audited["compiled_only_correct"], audited["baseline_only_correct"]):
        raise ValueError("paired sensitivity disagrees with all-scheduled audit")
    deletions = [{"omitted_database": b["database"],
                  "difference": (gains - losses - b["gains"] + b["losses"]) / (n - b["n"])}
                 for b in blocks if n > b["n"]]
    totals = {arm: fsum(values) for arm, values in costs.items()}
    return {
        "n": n, "databases": blocks, "gains": gains, "losses": losses,
        "difference": (gains - losses) / n,
        "pointwise_iid_conservative_ci95": paired_interval(gains, losses, n),
        "leave_one_database_out": deletions,
        "leave_one_database_out_range": [min(x["difference"] for x in deletions), max(x["difference"] for x in deletions)] if deletions else None,
        "database_signs": {"positive": sum(b["gains"] > b["losses"] for b in blocks),
                           "zero": sum(b["gains"] == b["losses"] for b in blocks),
                           "negative": sum(b["gains"] < b["losses"] for b in blocks)},
        "completed_run_estimated_cost_usd": totals,
        "unrecorded_net_compiled_cost_break_even_usd": totals["baseline"] - totals["compiled"],
        "missing_runs": {arm: len(audited["arms"][arm]["missing"]) for arm in costs},
        "source_sha256": sources,
    }


def build() -> dict:
    root = ROOT / "paper/results/bird"
    return {
        "schema": "bird-quality-sensitivity/v1",
        "analysis": "retrospective; no new executions or chosen noninferiority margin",
        "provider_calls_executed": 0,
        "interval_method": "97.5% two-sided Clopper-Pearson bounds for gain and loss; subtract endpoints; >=95% pointwise under iid question pairs",
        "limitations": ["selected databases, not random database sampling", "no pooling of overlapping primary/rotated/model cohorts",
                        "database deletions are descriptive, not confidence intervals", "costs are frozen-rate estimates, not invoices; discovery and maintenance excluded"],
        "cohorts": {name: summarize(root / run, root / selection) for name, (run, selection) in COHORTS.items()},
    }


def table(result: dict) -> str:
    lines = [r"% generated by paper/scripts/bird_quality_sensitivity.py; do not edit",
             r"\begin{tabular}{@{}lrrrr@{}}", r"\toprule",
             r"Cohort & $\Delta$ (pp) & Conservative 95\% interval & Delete-one range & DBs $+/0/-$ \\", r"\midrule"]
    for key, label in (("primary", "Primary"), ("rotated", "Rotated"), ("second_model", "Second model"), ("train", "Train split")):
        row = result["cohorts"][key]
        ci = row["pointwise_iid_conservative_ci95"]
        delete = row["leave_one_database_out_range"]
        signs = row["database_signs"]
        cells = [label, f"${100 * row['difference']:+.2f}$",
                 f"$[{100 * ci[0]:+.2f}, {100 * ci[1]:+.2f}]$",
                 f"$[{100 * delete[0]:+.2f}, {100 * delete[1]:+.2f}]$",
                 f"{signs['positive']}/{signs['zero']}/{signs['negative']}"]
        lines.append(" & ".join(cells) + r" \\")
    return "\n".join(lines + [r"\bottomrule", r"\end{tabular}"]) + "\n"


def main() -> None:
    result = build()
    (ROOT / "paper/results/bird/quality_sensitivity.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    (ROOT / "paper/iclr/tables/bird_quality_sensitivity.tex").write_text(table(result))
    print("wrote BIRD paired uncertainty and sensitivity; provider calls: 0")


if __name__ == "__main__":
    main()
