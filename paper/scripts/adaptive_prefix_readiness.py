"""Remaining source inventory and fixed-method power sensitivities; no execution seal."""
from collections import Counter
import json
from pathlib import Path

from scipy.stats import binom

from adaptive_pilot import ROOT, OUT as PILOT, QUESTIONS, digest, write
from audit_bird_revision import read_corrected
from freeze_adaptive_prefix import OUT
from matched_compiler_feasibility import ni_max_losses, superiority_power


def screen(questions, historical, pilot, executable):
    key = lambda q: (q["db_id"], " ".join(q["question"].lower().split()))
    duplicates = Counter(key(q) for q in questions)
    rows = []
    for q in sorted(questions, key=lambda q: q["question_id"]):
        qid = q["question_id"]
        reasons = []
        if qid in historical:
            reasons.append("historical_prior_use_or_selection")
        if qid in pilot:
            reasons.append("exploratory_pilot")
        if qid in range(18):
            reasons.append("web_view_exposed")
        if duplicates[key(q)] > 1:
            reasons.append("normalized_exact_duplicate")
        if qid not in executable:
            reasons.append("gold_execution_unavailable")
        rows.append({"question_id": qid, "db_id": q["db_id"], "exclusions": reasons,
                     "eligible": not reasons})
    return rows


def power_rows(available):
    rows = []
    for n in sorted({100, 300, 400, 500, 600, max(1, available - 120)}):
        losses = ni_max_losses(n, margin=.02, error=.05)
        rows.append({"test_groups": n, "fits_after_120_calibration_groups": n <= available - 120,
            "superiority_power_gain_04_loss_01": superiority_power(n, .04, .01, .05),
            "superiority_power_gain_03_loss_01": superiority_power(n, .03, .01, .05),
            "two_point_conservative_ni_max_losses": losses,
            "two_point_conservative_ni_power_at_loss_01": float(binom.cdf(losses, n, .01))})
    return rows


def build():
    history_path = ROOT / "paper/results/calibration_population_audit/bird_source_screen.json"
    audit_path = ROOT / "paper/results/adaptive_comparison_preflight/bird_revision_audit.json"
    pilot_path = PILOT / "future_exclusions.json"
    history = next(r["screened_ids"] for r in json.loads(history_path.read_text())["splits"] if r["split"] == "dev")
    pilot = json.loads(pilot_path.read_text())["question_ids"]
    executable = {r["question_id"] for r in json.loads(audit_path.read_text())["gold_execution"]["rows"] if r["status"] == "ok"}
    rows = screen(read_corrected(QUESTIONS), set(history), set(pilot), executable)
    counts = dict(sorted(Counter(r["db_id"] for r in rows if r["eligible"]).items()))
    available = sum(counts.values())
    sources = [Path(__file__).resolve(), history_path, audit_path, pilot_path,
        OUT / "candidate.json", OUT / "executor_sql_validation.json", QUESTIONS,
        ROOT / "paper/scripts/matched_compiler_feasibility.py"]
    return {"schema": "gac-adaptive-prefix-readiness-v1", "provider_calls": 0,
        "decision": "NO_GO_FOR_CONFIRMATORY_EXECUTION",
        "source_hashes": {str(p.relative_to(ROOT)): digest(p) for p in sources},
        "source_records": len(rows), "eligible_question_count": available, "eligible_by_database": counts,
        "rows": rows, "power_sensitivity": power_rows(available),
        "planning_assumptions": ["One primary paired quality contrast at alpha 0.05; not a six-arm familywise result.",
            "IID paired questions and hypothetical discordance probabilities; database/template clustering is unresolved.",
            "120 calibration groups is a sensitivity allocation, not a sealed or sufficient final design.",
            "Two percentage points is a sensitivity margin, not a selected noninferiority tolerance.",
            "The available count is source capacity, not evidence of independent units or semantic gold validity.",
            "Prior gold-cache exposure is documented by the preflight audit; these are not untouched benchmark records.",
            "Exact text duplicate screening does not identify paraphrases, template dependence, or model pretraining exposure."],
        "resolved": ["All 36 retained selected SQL programs match the pinned upstream executor under identical RPC fixtures.",
            "One list_tables candidate is reproducibly synthesized from 27 training groups and passes 9 development replays."],
        "remaining": ["Fresh unfiltered calibration and independent final outcomes do not exist for this candidate.",
            "Runtime continuation packaging, fallback accounting, all-arm answer normalization and an execution seal remain required.",
            "A one-call handwritten policy implements the same action; superiority of automatic compilation is not identified by this candidate.",
            "No calibrated learned ranking or multiple positive certified coverage points exist.",
            "Quality tolerance, sampling estimand, grouping, multiplicity and test size must be fixed before paid evaluation.",
            "The SQL adaptation is not a native Agent JIT or EvoC2F benchmark reproduction."]}


if __name__ == "__main__":
    report = build()
    write(OUT / "readiness.json", report)
    print(json.dumps({k: report[k] for k in ("decision", "eligible_question_count", "eligible_by_database")}))
