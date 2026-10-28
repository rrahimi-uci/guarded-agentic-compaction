"""Recompute the graded issue gate extension from retained public source and runs.

Provider-free: verifies the sealed fresh cohort and its disjointness (including
``experiments/``), regrades every answer against the source, recounts the pooled
and fresh grids with exact bounds, recomputes the admission decision, the
descriptive Fisher split, the test-set outcome if it ran, episode retention, and
spending arithmetic. Writes ``audit_extension.json`` and the appendix table.
"""
from __future__ import annotations

import ast
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src", ROOT / "paper/scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import graded_issue_gate_extension_preflight as extension  # noqa: E402
import graded_issue_gate_preflight as cohort  # noqa: E402
import graded_issue_gate_study as study  # noqa: E402
import github_live_study as fixed  # noqa: E402
import github_natural_workflow_study as natural  # noqa: E402
from guarded_agentic_compaction.grc.calibrate import GRID, CalibrationSample, clopper_pearson_upper  # noqa: E402
from guarded_agentic_compaction.schema.artifacts import GateModel  # noqa: E402
from guarded_agentic_compaction.schema.traces import content_digest  # noqa: E402

AUDIT_PATH = study.OUT / "audit_extension.json"
TABLE_PATH = ROOT / "paper/iclr/tables/gate_extension.tex"
PHI_MIN = 0.02


def grid_rows(samples: list[CalibrationSample], model: GateModel, *, alpha: float = extension.ALPHA,
              delta: float = extension.DELTA, grid: tuple[float, ...] = GRID) -> list[dict]:
    """The exact per-threshold counts and bounds Algorithm 1 sees, recomputed independently."""
    conf = 1.0 - delta / len(grid)
    n_groups = len({s.group for s in samples})
    rows = []
    for eta in grid:
        accepted = [s for s in samples if s.eligible and model.score(s.features) <= eta]
        n = len({s.group for s in accepted})
        k = len({s.group for s in accepted if s.violation})
        upper = clopper_pearson_upper(k, n, conf) if n else 1.0
        coverage = n / n_groups if n_groups else 0.0
        rows.append({"eta": eta, "n": n, "violations": k, "upper": round(upper, 4),
                     "coverage": round(coverage, 4), "admissible": bool(n and upper <= alpha and coverage >= PHI_MIN)})
    return rows


def fisher_split(samples: list[CalibrationSample], model: GateModel, eta: float) -> dict:
    """One-sided Fisher exact test: violation rate above ``eta`` exceeds the rate at or below it."""
    from scipy.stats import fisher_exact

    eligible = [s for s in samples if s.eligible]
    above = [s for s in eligible if model.score(s.features) > eta]
    below = [s for s in eligible if model.score(s.features) <= eta]
    k_above, k_below = sum(s.violation for s in above), sum(s.violation for s in below)
    table = [[k_above, len(above) - k_above], [k_below, len(below) - k_below]]
    p_value = float(fisher_exact(table, alternative="greater")[1]) if above and below else 1.0
    return {"split_eta": eta, "above": {"n": len(above), "violations": k_above},
            "at_or_below": {"n": len(below), "violations": k_below},
            "one_sided_fisher_p": round(p_value, 4), "descriptive_only": True}


def _rows_from_notes(gate: dict) -> list[dict]:
    return ast.literal_eval(gate["notes"].split("grid rows: ", 1)[1])


def audit() -> dict:
    sealed = json.loads(study.EXT_PREFLIGHT.read_text())
    assert sealed == extension.build()
    original = json.loads(cohort.OUT.read_text())
    assert original == cohort.build()
    result = json.loads(study.EXT_RESULT.read_text())
    checkpoint = json.loads(study.EXT_CHECKPOINT.read_text())
    assert result["status"] in {"retired_before_test", "completed"}
    assert result["extension_preflight_sha256"] == cohort.sha256(study.EXT_PREFLIGHT)
    assert checkpoint["preflight_sha256"] == cohort.sha256(study.EXT_PREFLIGHT)
    assert checkpoint["candidate_sha256"] == cohort.sha256(study.REGISTRY) == sealed["candidate_registry_sha256"]
    assert checkpoint["pending_batch"] is None and not checkpoint["failures"]
    assert checkpoint["approved_spend_usd"] <= study.EXTENSION_CAP_USD
    for key, path in (("frozen_gate_v2_sha256", extension.FROZEN_GATE), ("results_v2_sha256", study.RESULT),
                      ("checkpoint_v2_sha256", study.CHECKPOINT), ("original_preflight_sha256", cohort.OUT)):
        assert sealed[key] == cohort.sha256(path), key
    store, _ = fixed.build_store(pd.read_parquet(fixed.DATA_PATH))
    model = GateModel.from_dict(result["gate"]["frozen_model"])
    assert model.to_dict() == sealed["frozen_model"] == json.loads(extension.FROZEN_GATE.read_text())["frozen_model"]
    assert model.features == study.FEATURE_NAMES

    # Cohort: the fresh groups are exactly the sealed remainder and disjoint from everything spent.
    fresh_ids = [r["issue_number"] for r in sealed["fresh_calibration"]]
    original_ids = {r["issue_number"] for rows in original["selected"].values() for r in rows}
    pilot = json.loads(cohort.PILOT.read_text())["cohort"]
    pilot_ids = set(pilot["held_out_record_numbers"] + pilot["calibration_dev_record_numbers"])
    spent = cohort.prior_record_numbers() | extension.experiments_record_numbers() | pilot_ids | original_ids
    assert len(fresh_ids) == len(set(fresh_ids)) and not set(fresh_ids) & spent
    strata = {r["issue_number"]: r["stratum"] for r in sealed["fresh_calibration"]}
    strata.update({r["issue_number"]: r["stratum"] for rows in original["selected"].values() for r in rows})

    def check_rows(rows: list[dict], expected: set[int]) -> None:
        assert len(rows) == len(expected) and {r["issue_number"] for r in rows} == expected
        for row in rows:
            number = row["issue_number"]
            assert row["quality"] == natural.grade_factual(
                study.scenario(store, number), row["answer"], row["tool_sequence"], store)
            assert row["metrics"]["study_preread_calls"] == 1
            assert row["metrics"]["study_total_tool_calls"] == row["metrics"]["tool_calls"] + 1

    v2_checkpoint = json.loads(study.CHECKPOINT.read_text())
    original_rows = v2_checkpoint["runs"]["calibration_compiled"]
    check_rows(original_rows, {r["issue_number"] for r in original["selected"]["calibration"]})
    fresh_rows = checkpoint["runs"]["extension_calibration_compiled"]
    check_rows(fresh_rows, set(fresh_ids))
    original_samples = study.group_samples(original_rows, store)
    fresh_samples = study.group_samples(fresh_rows, store)
    pooled = original_samples + fresh_samples

    def describe(samples: list[CalibrationSample]) -> dict:
        errors = sorted(int(s.episode_id.split(":")[1]) for s in samples if s.violation)
        return {"groups": len(samples), "admitted": sum(s.eligible for s in samples),
                "task_errors": len(errors), "error_issue_numbers": errors,
                "errors_by_stratum": dict(Counter(strata[n] for n in errors))}

    groups = {"original_calibration": describe(original_samples), "fresh_calibration": describe(fresh_samples),
              "pooled_calibration": describe(pooled)}
    assert groups["original_calibration"]["task_errors"] == 2 and groups["original_calibration"]["admitted"] == 184

    # Grids and admission, recomputed and compared with what the runner recorded.
    grids = {}
    for name, samples in (("pooled", pooled), ("fresh", fresh_samples)):
        rows = grid_rows(samples, model)
        recorded = _rows_from_notes(result["gate"][f"learned_{name}"])
        assert [{k: r[k] for k in ("eta", "n", "violations", "upper", "coverage")} for r in rows] == recorded
        gate = result["gate"][f"learned_{name}"]
        admissible = [r["eta"] for r in rows if r["admissible"]]
        if admissible:
            assert not gate["retire"] and gate["threshold"] == max(admissible) and list(gate["admissible"]) == admissible
        else:
            assert gate["retire"]
        grids[name] = {"rows": rows, "admissible": admissible,
                       "threshold": (max(admissible) if admissible else None), "retire": not admissible}
    support = result["gate"]["support_only_pooled"]
    assert support["alpha"] == 1.0 and support["threshold"] == 1.0 and not support["retire"]

    # Descriptive split: lowest admissible pooled threshold, else the lowest grid point.
    split_eta = min(grids["pooled"]["admissible"]) if grids["pooled"]["admissible"] else GRID[0]
    fisher = fisher_split(pooled, model, split_eta)
    fisher["split_rule"] = ("lowest admissible pooled threshold" if grids["pooled"]["admissible"]
                            else "no admissible threshold; lowest grid point")

    # Test set: run only after admission, under the pooled threshold.
    test_ids = {r["issue_number"] for r in original["selected"]["test"]}
    test = None
    if result["status"] == "retired_before_test":
        assert grids["pooled"]["retire"]
        assert set(checkpoint["runs"]) == {"extension_calibration_compiled"}
        assert not test_ids & {r["issue_number"] for r in fresh_rows}
    else:
        assert not grids["pooled"]["retire"]
        decisions = {int(k): v for k, v in result["decisions"].items()}
        assert set(decisions) == test_ids
        eta = grids["pooled"]["threshold"]
        for number in test_ids:
            assert decisions[number] == (model.score(study.risk_read(store, number)[0]) <= eta)
        runs = checkpoint["runs"]
        check_rows(runs["test_baseline"], test_ids)
        check_rows(runs["test_learned_compiled"], {n for n in test_ids if decisions[n]})
        check_rows(runs["test_learned_fallback"], {n for n in test_ids if not decisions[n]})
        check_rows(runs["test_support_compiled"], test_ids)
        assert runs.get("test_support_fallback", []) == []
        outcomes = study._test_outcomes(runs)
        assert outcomes == result["outcomes"]

        def arm(rows: list[dict]) -> dict:
            n = len(rows)
            k = sum(not bool(r["quality"]["overall"]) for r in rows)
            return {"attempted": n, "task_errors": k, "correct": n - k,
                    "compacted": sum(int(r["dispatch"]["compacted"]) > 0 for r in rows),
                    "one_sided_95_upper_error_rate": round(clopper_pearson_upper(k, n, 0.95), 4) if n else 1.0}

        learned_rows = runs["test_learned_compiled"] + runs["test_learned_fallback"]
        base_ok = {r["issue_number"]: bool(r["quality"]["overall"]) for r in runs["test_baseline"]}
        learned_ok = {r["issue_number"]: bool(r["quality"]["overall"]) for r in learned_rows}
        routed = sum(decisions.values())
        test = {"issues": len(test_ids), "threshold": eta, "routed_to_compiled": routed,
                "coverage": round(routed / len(test_ids), 4),
                "arms": {"baseline": arm(runs["test_baseline"]), "learned": arm(learned_rows),
                         "learned_compiled_only": arm(runs["test_learned_compiled"]),
                         "support_only": arm(runs["test_support_compiled"] + runs["test_support_fallback"])},
                "paired_baseline_vs_learned": {
                    "both_correct": sum(base_ok[n] and learned_ok[n] for n in test_ids),
                    "baseline_only_correct": sum(base_ok[n] and not learned_ok[n] for n in test_ids),
                    "learned_only_correct": sum(learned_ok[n] and not base_ok[n] for n in test_ids),
                    "both_wrong": sum(not base_ok[n] and not learned_ok[n] for n in test_ids)},
                "wrong_after_compiled_dispatch": sorted(
                    r["issue_number"] for r in runs["test_learned_compiled"]
                    if int(r["dispatch"]["compacted"]) > 0 and not bool(r["quality"]["overall"]))}

    # Every raw episode retained, redacted, and tied to its checkpoint row digest.
    episodes = {}
    for phase, rows in checkpoint["runs"].items():
        retained = json.loads((study.EXT_EPISODES / f"{phase}.json").read_text())["episodes"]
        by_number = {e["issue_number"]: e for e in retained}
        assert set(by_number) == {r["issue_number"] for r in rows} and len(retained) == len(rows)
        for row in rows:
            entry = by_number[row["issue_number"]]
            assert entry["episode_digest"] == row["episode_digest"] and entry["trace_id"] == row["trace_id"]
            assert content_digest(entry["episode"]) == entry["redacted_episode_digest"]
        episodes[phase] = len(retained)

    all_rows = [row for rows in checkpoint["runs"].values() for row in rows]
    assert sum(float(r["metrics"]["estimated_cost_usd"] or 0) for r in all_rows) == checkpoint["estimated_spend_usd"]
    assert checkpoint["estimated_spend_usd"] <= checkpoint["approved_spend_usd"]
    assert checkpoint["provider_episodes_attempted"] == len(all_rows)
    decision = ("retired_before_test" if result["status"] == "retired_before_test" else "admitted_and_tested")
    return {"schema": "gac-graded-issue-gate-extension-audit/v1", "provider_calls_executed": 0,
            "source_sha256": cohort.sha256(fixed.DATA_PATH),
            "extension_preflight_sha256": cohort.sha256(study.EXT_PREFLIGHT),
            "original_preflight_sha256": cohort.sha256(cohort.OUT),
            "frozen_gate_v2_sha256": cohort.sha256(extension.FROZEN_GATE),
            "checks": ["sealed_extension_matches_build", "pins_unchanged", "fresh_disjoint_incl_experiments",
                       "source_grades", "preread_accounted", "exact_grid_counts_and_bounds_pooled_and_fresh",
                       "admission_recomputed", "test_routing_recomputed", "episodes_retained",
                       "spend_arithmetic"],
            "alpha": extension.ALPHA, "delta": extension.DELTA, "grid_size": len(GRID),
            "groups": groups, "grids": grids, "fisher_split": fisher, "test": test,
            "episodes_retained": episodes, "provider_episodes_attempted": checkpoint["provider_episodes_attempted"],
            "extension_estimated_cost_usd": checkpoint["estimated_spend_usd"],
            "approved_cap_usd": checkpoint["approved_spend_usd"],
            "decision": decision}


def table(data: dict | None = None) -> str:
    data = data or json.loads(AUDIT_PATH.read_text())
    pooled, fresh = data["grids"]["pooled"], data["grids"]["fresh"]
    n_pooled, n_fresh = data["groups"]["pooled_calibration"]["groups"], data["groups"]["fresh_calibration"]["groups"]
    lines = [r"\begin{tabular}{@{}rrrrrrrrr@{}}", r"\toprule",
             f" & \\multicolumn{{4}}{{c}}{{Pooled ({n_pooled} groups)}} & \\multicolumn{{4}}{{c}}{{Fresh ({n_fresh} groups)}} \\\\",
             r"\cmidrule(lr){2-5}\cmidrule(lr){6-9}",
             r"$\eta$ & $n$ & $k$ & $U$ & Cov. & $n$ & $k$ & $U$ & Cov. \\", r"\midrule"]
    for p, f in zip(pooled["rows"], fresh["rows"]):
        def cell(row: dict) -> str:
            mark = r"$^{\dagger}$" if row["admissible"] else ""
            return f"{row['n']} & {row['violations']} & {row['upper']:.4f}{mark} & {row['coverage']:.2f}"
        lines.append(f"{p['eta']:.2f} & {cell(p)} & {cell(f)} \\\\")

    def verdict(name: str, grid: dict) -> str:
        if grid["retire"]:
            return f"{name}: no admissible threshold (retire)"
        return f"{name}: admitted $\\eta={grid['threshold']:.2f}$"

    fisher = data["fisher_split"]
    lines += [r"\midrule",
              f"\\multicolumn{{9}}{{@{{}}l}}{{{verdict('Pooled', pooled)}; {verdict('fresh', fresh)}.}} \\\\",
              f"\\multicolumn{{9}}{{@{{}}l}}{{Descriptive split at $\\eta={fisher['split_eta']:.2f}$: "
              f"{fisher['above']['violations']}/{fisher['above']['n']} errors above vs.\\ "
              f"{fisher['at_or_below']['violations']}/{fisher['at_or_below']['n']} at or below; one-sided Fisher $p={fisher['one_sided_fisher_p']:.3f}$.}} \\\\"]
    test = data["test"]
    if test is None:
        lines.append(r"\multicolumn{9}{@{}l}{Test set (90 issues): not run; it stays sealed.} \\")
    else:
        learned, base = test["arms"]["learned"], test["arms"]["baseline"]
        lines.append(f"\\multicolumn{{9}}{{@{{}}l}}{{Test (90 issues, {test['routed_to_compiled']} routed): learned arm "
                     f"{learned['task_errors']}/{learned['attempted']} errors (one-sided 95\\% bound {100 * learned['one_sided_95_upper_error_rate']:.1f}\\%); "
                     f"unchanged agent {base['task_errors']}/{base['attempted']} (bound {100 * base['one_sided_95_upper_error_rate']:.1f}\\%).}} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    text = "% generated by paper/scripts/audit_graded_issue_gate_extension.py table; do not edit\n" + "\n".join(lines) + "\n"
    TABLE_PATH.write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "table":
        print(table())
    else:
        data = audit()
        AUDIT_PATH.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        table(data)
        print(json.dumps({"decision": data["decision"], "groups": data["groups"],
                          "pooled": {k: v for k, v in data["grids"]["pooled"].items() if k != "rows"},
                          "fresh": {k: v for k, v in data["grids"]["fresh"].items() if k != "rows"},
                          "test": data["test"], "provider_calls_executed": 0}, indent=2))
