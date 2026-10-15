"""Post-run audit and descriptive analysis, separate from the sealed live driver.

The registered endpoint remains factuality_exact. A stricter seven-field answer
endpoint and pointwise paired intervals are explicitly supplementary analyses.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fresh_safeguard_comparison as study

ANSWER_FIELDS = ("category_correct", "issue_number_correct", "evidence_label_correct",
                 "title_exact", "state_exact", "comment_count_exact", "evidence_excerpt_exact")
CONTRASTS = (("baseline", "gac"), ("baseline", "support_only"),
             ("baseline", "recurrence_only"), ("recurrence_only", "gac"), ("support_only", "gac"))


def correct(row: dict, endpoint: str) -> bool:
    if row["status"] != "completed":
        return False
    if endpoint == "registered_factuality_exact":
        return row["quality"]["factuality_exact"] is True
    if endpoint != "supplementary_all_answer_fields":
        raise ValueError("unknown quality endpoint")
    return all(row["quality"][field] is True for field in ANSWER_FIELDS)


def analyze(frozen: dict, checkpoint: dict) -> dict:
    from bird_quality_sensitivity import paired_interval
    from scipy.stats import binomtest

    if checkpoint["preflight_sha256"] != study.object_digest(frozen):
        raise ValueError("checkpoint/preflight identity mismatch")
    if checkpoint["pending"]:
        raise ValueError("run has an unresolved pending call")
    summary = study.summarize(frozen, checkpoint["rows"])
    if summary["status"] != "completed":
        raise ValueError("analysis waits for all scheduled outcomes; inspect incomplete summary separately")
    rows = {(r["issue_number"], r["arm"]): r for r in checkpoint["rows"]}
    quality = {}
    for endpoint in ("registered_factuality_exact", "supplementary_all_answer_fields"):
        contrasts = {}
        for baseline, candidate in CONTRASTS:
            pairs = [(correct(rows[(n, baseline)], endpoint), correct(rows[(n, candidate)], endpoint))
                     for n in frozen["test_ids"]]
            gains = sum(c and not b for b, c in pairs)
            losses = sum(b and not c for b, c in pairs)
            contrasts[f"{candidate}_vs_{baseline}"] = {
                "n": len(pairs), "gains": gains, "losses": losses,
                "difference": (gains - losses) / len(pairs),
                "pointwise_iid_conservative_ci95": paired_interval(gains, losses, len(pairs)),
                "mcnemar_exact_p": float(binomtest(gains, gains + losses, .5).pvalue) if gains + losses else 1.0,
            }
        quality[endpoint] = {
            "correct": {arm: sum(correct(rows[(n, arm)], endpoint) for n in frozen["test_ids"]) for arm in study.ARMS},
            "contrasts": contrasts,
        }
    resources = {}
    for arm in study.ARMS:
        complete = [rows[(n, arm)] for n in frozen["test_ids"] if rows[(n, arm)]["status"] == "completed"]
        resources[arm] = {
            "completed_n": len(complete), "scheduled_n": len(frozen["test_ids"]),
            "all_costs_observed": len(complete) == len(frozen["test_ids"]),
            "mean_on_completed": {m: mean(r["metrics"][m] for r in complete) if complete else None for m in study.METRICS},
        }
    reductions = {}
    for baseline, candidate in CONTRASTS:
        if resources[baseline]["all_costs_observed"] and resources[candidate]["all_costs_observed"]:
            reductions[f"{candidate}_vs_{baseline}"] = {
                m: 1 - resources[candidate]["mean_on_completed"][m] / resources[baseline]["mean_on_completed"][m]
                if resources[baseline]["mean_on_completed"][m] else None for m in study.METRICS}
    errors = [{"issue_number": n, "arm": arm, "status": rows[(n, arm)]["status"],
               "failed_answer_fields": [f for f in ANSWER_FIELDS if not rows[(n, arm)].get("quality", {}).get(f, False)],
               "dispatched": rows[(n, arm)].get("dispatched")}
              for n in frozen["test_ids"] for arm in study.ARMS
              if not correct(rows[(n, arm)], "supplementary_all_answer_fields")]
    return {
        "schema": "gac-fresh-safeguards-analysis/v1", "provider_calls_executed_by_analysis": 0,
        "analysis_status": "supplementary descriptive analysis of a prospectively sealed run",
        "registered_endpoint": "factuality_exact: title, state, comment count, and source excerpt",
        "supplementary_endpoint": "all seven answer fields, including category, issue number, and evidence label",
        "n": len(frozen["test_ids"]), "summary": summary, "quality": quality,
        "preflight_dispatch_outcomes": frozen.get("probe", {}).get("outcomes", {}),
        "candidate_reconstruction": frozen.get("source", {}).get("candidate_reproduction", {}),
        "runtime_gate_dispatch_disagreements": [n for n in frozen["test_ids"]
            if rows[(n, "gac")].get("dispatched") != rows[(n, "support_only")].get("dispatched")],
        "resources": resources, "reductions": reductions, "errors": errors,
        "completed_estimated_cost_usd": sum(r.get("metrics", {}).get("estimated_cost_usd", 0)
                                             for r in checkpoint["rows"]),
        "unknown_cost_reserve_usd": checkpoint["unknown_cost_reserve_usd"],
        "approved_spend_usd": checkpoint["approved_spend_usd"],
        "interval_scope": "95% pointwise under iid record pairs; not simultaneous across contrasts; independence unverified",
        "limitations": frozen.get("limitations", []) + [
            "supplementary endpoints and intervals are not a preregistered confirmatory test",
            "no noninferiority margin, no causal protection claim, no new risk certificate",
            "shared source grader reexecution is consistency checking, not an independent gold implementation",
            "current-compiler reconstruction changes identifier guards, verifier clauses, and gate feature specification relative to the historical artifact",
            "frozen rate estimates exclude lifecycle and human costs; not invoice verified"],
    }


def regrade(frozen: dict, checkpoint: dict) -> dict:
    import github_live_study as fixed
    import recurrence_only_ablation as shared

    store, _ = shared.load_store()
    compared = 0
    for row in checkpoint["rows"]:
        if row["status"] != "completed":
            continue
        number = row["issue_number"]
        source = store[number]
        scenario = fixed.Scenario(number, fixed.category_for(source["labels"]), tuple(source["labels"]),
                                  source["html_url"], source["day"], source["state"])
        graded = fixed.grade(scenario, row["answer"], row["tool_sequence"], row["tool_arguments"],
                             task_design=study.TASK, source_record=source, condition=row["arm"])
        for field in (*ANSWER_FIELDS, "factuality_exact"):
            if graded[field] != row["quality"][field]:
                raise ValueError(f"retained label mismatch: {number}/{row['arm']}/{field}")
        compared += 1
    return {"completed_answers_regraded": compared, "label_mismatches": 0, "provider_calls_executed": 0}


def markdown(result: dict) -> str:
    lines = ["# Fresh-record safeguard comparison: observed results", "",
             f"This run evaluated {result['n']} unused historical-snapshot issues under four arms.",
             "The registered four-field factuality endpoint and supplementary seven-field answer endpoint are shown separately.",
             "Resource means use completed episodes; consult each arm's completed/failed counts before comparing incomplete runs.", "",
             "| Arm | Factuality correct | All answer fields correct | Dispatched | Requests/episode | Tokens/episode | Latency (s) | Estimated cost/episode (USD) |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for arm in study.ARMS:
        m = result["resources"][arm]["mean_on_completed"]
        q = result["quality"]
        values = [q["registered_factuality_exact"]["correct"][arm], q["supplementary_all_answer_fields"]["correct"][arm]]
        def formatted(metric, scale=1, precision=2):
            return "unobserved" if m[metric] is None else f"{m[metric]/scale:.{precision}f}"
        lines.append(f"| {arm} | {values[0]}/{result['n']} | {values[1]}/{result['n']} | "
                     f"{result['summary']['arms'][arm]['dispatched']} | {formatted('requests')} | "
                     f"{formatted('total_tokens', precision=1)} | {formatted('wall_latency_ms', 1000)} | "
                     f"{formatted('estimated_cost_usd', precision=6)} |")
    lines += ["", f"Recorded estimated spend: ${result['completed_estimated_cost_usd']:.6f}; "
              f"authorized cap: ${result['approved_spend_usd']:.2f}. Prices are frozen estimates, not invoices.",
              "", "| Comparison (registered endpoint) | Gains | Losses | Accuracy difference (percentage points) | Conservative 95% interval |",
              "| --- | ---: | ---: | ---: | --- |"]
    for name, c in result["quality"]["registered_factuality_exact"]["contrasts"].items():
        low, high = c["pointwise_iid_conservative_ci95"]
        lines.append(f"| {name} | {c['gains']} | {c['losses']} | {100*c['difference']:+.2f} | [{100*low:+.2f}, {100*high:+.2f}] |")
    lines += ["", "Intervals are supplementary, pointwise, and assume independent identically distributed record pairs. "
              "They do not establish equivalence or noninferiority. Errors are retained in `analysis.json` and raw answers in `checkpoint.json`.",
              "", "Provider-free dispatch outcomes: `" + json.dumps(result["preflight_dispatch_outcomes"], sort_keys=True) + "`.",
              "", f"Observed GAC/support-only dispatch disagreements: {len(result['runtime_gate_dispatch_disagreements'])} records. "
              "When dispatch behavior is identical, final answer differences alone cannot demonstrate gate protection: "
              "each arm makes separate stochastic provider executions.",
              "", "No paper score or acceptance claim follows automatically from completing this run.", "", "Limitations:", ""]
    lines += [f"- {item}" for item in result["limitations"]]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=study.DEFAULT_OUT)
    parser.add_argument("--output", type=Path, default=study.ROOT / "experiments/fresh_safeguards/analysis")
    args = parser.parse_args()
    frozen = json.loads((args.input / "preflight.json").read_text())
    checkpoint = json.loads((args.input / "checkpoint.json").read_text())
    result = analyze(frozen, checkpoint)
    result["regrade_audit"] = regrade(frozen, checkpoint)
    result["source_sha256"] = {name: study.digest(args.input / name) for name in ("preflight.json", "checkpoint.json")}
    result["analysis_code_sha256"] = {str(p.relative_to(study.ROOT)): study.digest(p)
                                      for p in (Path(__file__), study.ROOT / "paper/scripts/bird_quality_sensitivity.py")}
    study.write_json(args.output / "analysis.json", result)
    (args.output / "results.md").write_text(markdown(result))
    print(json.dumps({"records": result["n"], "estimated_spend_usd": result["completed_estimated_cost_usd"],
                      "regrade": result["regrade_audit"]}, indent=2))


if __name__ == "__main__":
    main()
