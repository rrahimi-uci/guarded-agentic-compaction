"""Render descriptive pilot results without promoting them to confirmation."""
from collections import Counter
import json
import statistics

from adaptive_pilot import OUT


def main():
    report = json.loads((OUT / "report.json").read_text())
    discovery = json.loads((OUT / "gac_discovery.json").read_text())
    old = json.loads((OUT / "report_v1.json").read_text())
    seal = json.loads((OUT / "seal.json").read_text())
    parity = json.loads((OUT / "executor_parity.json").read_text())
    rows = report["rows"]
    lines = ["# Adaptive compiler pilot: results and decision", "",
        "**Exploratory pilot only. NO-GO for confirmatory execution or a new quality certificate.**", "",
        f"The amended protocol scheduled {len(rows)} episodes on {len(seal['tasks'])} questions: four per each of nine databases. "
        "This weights databases equally within the pilot; it is not a random sample of the complete BIRD benchmark. "
        "Tasks came from the pinned corrected dev release after the documented prior-use, exact-duplicate, web-exposure and executable-gold screens. "
        "All failures stay in the denominator. All pilot IDs are excluded from future calibration and final testing.", "",
        "## Observations", "",
        "| Arm | Set-correct / scheduled | Completed / failed / unstarted | Provider requests | Tool calls | Accounted upper USD | Median processing seconds |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: |"]
    for arm, summary in report["summary"].items():
        selected = [r for r in rows if r["arm"] == arm]
        counts = summary["statuses"]
        wall = [r["wall_seconds"] for r in selected if r.get("wall_seconds") is not None]
        lines.append(f"| {arm} | {summary['correct']}/{summary['scheduled']} | "
            f"{counts.get('completed', 0)} / {counts.get('failed', 0)} / {counts.get('unstarted', 0)} | "
            f"{sum(r['provider_requests'] for r in selected)} | {sum(r['tool_calls'] for r in selected)} | "
            f"{summary['accounted_upper_usd']:.4f} | {statistics.median(wall) if wall else 0:.2f} |")
    by_task = {(r["question_id"], r["arm"]): r for r in rows}
    lines += ["", "Paired descriptive outcomes against the baseline (no hypothesis test):", ""]
    for arm in ("manual_prefetch", "agent_jit"):
        pairs = [(by_task[t["question_id"], "baseline"]["execution_correct"], by_task[t["question_id"], arm]["execution_correct"]) for t in seal["tasks"]]
        lines.append(f"- {arm}: {sum(bool(b) and not a for a, b in pairs)} correct-only-in-arm; "
                     f"{sum(bool(a) and not b for a, b in pairs)} correct-only-in-baseline; "
                     f"{sum(bool(a) == bool(b) for a, b in pairs)} agreements.")
    jit = [r for r in rows if r["arm"] == "agent_jit"]
    lines += ["", f"Agent JIT produced {sum(r.get('generated_candidates', 0) for r in jit)} retained sampled candidates, "
        f"of which {sum(r.get('valid_candidates', 0) for r in jit)} passed its static checks. "
        "Selection used minimum upstream estimated runtime cost, with generation order breaking ties; no gold answer was used in selection. "
        "Static validity did not establish correct final answers. "
        f"Failed-arm exception classes: `{dict(Counter(r['error'] for r in jit if r['status'] == 'failed'))}`.", "",
        "The stronger row-shape and duplicate-sensitive diagnostics remain in `report.json`; they are not independently annotated semantic oracles. "
        "Primary set agreement ignores order and duplicate multiplicity. Processing time includes final SQL grading and local orchestration; "
        "it is not a clean deployment-latency estimate. Provider accounting includes all candidate generation and runtime inference, "
        "but excludes human engineering, machine rental and provider-independent setup cost.", "",
        "## GAC feasibility", "",
        f"All {discovery['scheduled_baselines']} scheduled baseline IDs retain their preassigned discovery role; "
        f"{discovery['converted']} attempts were converted to observable traces. "
        "Incorrect answers and failed attempts were not selected away. The compiler's own trace qualification and rejection reasons are retained.", "",
        "```text", discovery["report"], "```", "",
        "The adapter returns JSON inside a payload string. A separately labeled, posthoc diagnostic decodes those results into typed fields before discovery:", "",
        "```text", discovery["decoded_payload_diagnostic"]["report"], "```", "",
        "That diagnostic is not a live arm or a deployable artifact. Any future runtime must implement the same normalization, then use fresh calibration. "
        "Neither analysis has calibration groups; no risk certificate, positive certified coverage or learned-gate benefit is established.", "",
        "## Operational amendment and spending", "",
        f"V1 attempted three episodes before the endpoint incompatibility was discovered; its other 105 scheduled episodes remain unstarted. "
        f"Its conservative account was ${old['campaign_accounted_upper_usd']:.7f}. "
        "Two function-tool calls were rejected with reasoning `low`; the Agent JIT attempt completed incorrectly. "
        "V2 uses reasoning `none` for every arm and 32 concurrent candidate generations. The cohort and arm order are unchanged; "
        "Q36 was therefore operationally exposed before v2. These amendments and all original failures are preserved, not silently replaced.", "",
        f"**Combined conservative campaign accounting: ${report['campaign_accounted_upper_usd']:.4f} of the authorized $300.00 cap**, "
        f"leaving ${300-report['campaign_accounted_upper_usd']:.4f} against that accounting bound. "
        "This includes v1 and v2; stage allocation remains $30 pilot/$30 discovery/$60 calibration/$180 test. "
        "Unknown usage retains its full reservation. The provider invoice can differ because the ledger uses conservative pinned rates rather than actual cache discounts.", "",
        "## Decision and reviewer concerns", "",
        "The pilot establishes a working budgeted SQL adaptation and exposes practical output/runtime limitations. "
        "It does **not** establish that GAC beats another compiler, that native Agent JIT performs poorly, that handwritten prefetch is equivalent to GAC, "
        "or that the paper's acceptance-critical comparison has been completed. Native browser observation/execution is not reproduced. "
        "Generated programs can fail the SQL adapter's required answer contract; its worker also imposes a strict JSON RPC protocol and differs from upstream's Python executor. "
        "Those differences must be validated before using the port's score as comparative evidence.", "",
        f"The provider-free executor probe matched upstream success/output on only {sum(r['same_success_and_output'] for r in parity['rows'])}/{len(parity['rows'])} hand-authored fixtures "
        f"for the frozen pilot worker. A prospective worker using the unmodified pinned upstream executor matched {sum(r['prospective_matches'] for r in parity['rows'])}/{len(parity['rows'])}, "
        "including print handling, return/last-binding semantics and an RPC fixture. The replacement was not used in this live pilot, "
        "and these fixture checks are not full SQL-port or native-browser validation. No pilot outcomes are repaired or relabeled by that result.", "",
        "Next gates, before spending the remaining budget:", "",
        "1. Extend the prospective worker's fixture parity to retained SQL programs and the answer contract; freeze a supported runtime without relabeling this pilot as an independent test.",
        "2. Establish a candidate that survives discovery/challenge under the actual runtime representation. If none does, report refusal and change the task/design prospectively rather than tuning on final-test answers.",
        "3. Freeze source/sampling weights, common candidate families, quality margin, multiplicity, and a feasible fixed sample size; reserve fresh groups before observing baseline outcomes or mined-family occurrence.",
        "4. Run unfiltered final-outcome calibration and a separate final test, including rejected candidates, fallback and complete compilation costs. Retain any failed or unavailable certificate.", "",
        "No extra paid calibration or final test has been launched. The manuscript's quantitative claims have not been replaced with these exploratory rates. "
        "The evidence improves the research audit; it does not remove every legitimate reason for rejection.", "",
        "## Audit and reproduction", "",
        "`seal.json`, `seal_v1.json`, `report.json`, `report_v1.json`, `gac_discovery.json`, `retention.json`, "
        "`raw_evidence.tar.gz` and `source_v1.tar.gz` preserve settings, task denominators, observable traces, candidates, the campaign ledger and historical source bytes. "
        "Database bytes and credentials are not included. Dataset provenance and upstream attribution appear in `retention.json`.", "",
        "```sh", "python paper/scripts/archive_adaptive_pilot.py verify", "python paper/scripts/render_adaptive_pilot.py", "```", "",
        "New paid runs require the pinned external caches/environments described in the experiment README. Do not reset the campaign ledger or reuse pilot IDs as untouched evaluation data.", ""]
    (OUT / "REPORT.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
