"""Recompute the amended issue-gate result from retained public source and runs.

Provider-free: verifies cohort, task grades, actual dispatch, grid counts,
exact risk bounds, and spending arithmetic. Writes an audit artifact.
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

import graded_issue_gate_preflight as cohort  # noqa: E402
import graded_issue_gate_study as study  # noqa: E402
import github_live_study as fixed  # noqa: E402
import github_natural_workflow_study as natural  # noqa: E402
from guarded_agentic_compaction.grc.calibrate import clopper_pearson_upper  # noqa: E402
from guarded_agentic_compaction.schema.artifacts import GateModel  # noqa: E402


def audit() -> dict:
    frozen = json.loads(cohort.OUT.read_text())
    assert frozen == cohort.build()
    result = json.loads(study.RESULT.read_text())
    checkpoint = json.loads(study.CHECKPOINT.read_text())
    assert result["status"] == "retired_before_test"
    assert result["preflight_sha256"] == cohort.sha256(cohort.OUT)
    assert checkpoint["pending_batch"] is None and not checkpoint["failures"]
    assert set(checkpoint["runs"]) == {"development_compiled", "calibration_compiled"}
    store, _ = fixed.build_store(pd.read_parquet(fixed.DATA_PATH))
    model = GateModel.from_dict(result["gate"]["frozen_model"])
    assert model.features == study.FEATURE_NAMES
    strata = {r["issue_number"]: r["stratum"]
              for split in frozen["selected"].values() for r in split}
    errors = {}
    samples_by_phase = {}
    all_rows = []
    for split, phase in (("development", "development_compiled"),
                         ("calibration", "calibration_compiled")):
        rows = checkpoint["runs"][phase]
        expected = {r["issue_number"] for r in frozen["selected"][split]}
        assert len(rows) == len(expected) and {r["issue_number"] for r in rows} == expected
        for row in rows:
            number = row["issue_number"]
            assert row["quality"] == natural.grade_factual(
                study.scenario(store, number), row["answer"], row["tool_sequence"], store
            )
            assert int(row["dispatch"]["compacted"]) > 0
            assert row["metrics"]["study_preread_calls"] == 1
            assert row["metrics"]["study_total_tool_calls"] == row["metrics"]["tool_calls"] + 1
        samples = study.group_samples(rows, store)
        samples_by_phase[phase] = samples
        by_stratum = Counter(strata[int(s.episode_id.split(":")[1])] for s in samples if s.violation)
        errors[split] = {"issues": len(samples), "task_errors": sum(s.violation for s in samples),
                         "errors_by_stratum": dict(by_stratum),
                         "error_issue_numbers": sorted(int(s.episode_id.split(":")[1]) for s in samples if s.violation)}
        all_rows.extend(rows)
    assert sum(float(r["metrics"]["estimated_cost_usd"] or 0) for r in all_rows) == checkpoint["estimated_spend_usd"]
    samples = samples_by_phase["calibration_compiled"]
    gate = result["gate"]["learned"]
    assert gate["retire"] and gate["n_calibration_groups"] == len(samples)
    grid_rows = ast.literal_eval(gate["notes"].split("grid rows: ", 1)[1])
    assert len(grid_rows) == 11
    for row in grid_rows:
        selected = [s for s in samples if s.eligible and model.score(s.features) <= row["eta"]]
        n = len({s.group for s in selected})
        k = len({s.group for s in selected if s.violation})
        assert (n, k) == (row["n"], row["violations"])
        upper = clopper_pearson_upper(k, n, 1 - .10 / 11) if n else 1.0
        assert round(upper, 4) == row["upper"]
    test_ids = {r["issue_number"] for r in frozen["selected"]["test"]}
    assert not test_ids & {r["issue_number"] for r in all_rows}
    return {"schema": "gac-graded-issue-gate-audit/v2", "provider_calls_executed": 0,
            "source_sha256": cohort.sha256(fixed.DATA_PATH),
            "preflight_sha256": cohort.sha256(cohort.OUT),
            "candidate_registry_sha256": cohort.sha256(study.REGISTRY),
            "checks": ["cohort_disjoint", "source_grades", "real_dispatch", "preread_accounted",
                       "exact_grid_counts_and_bounds", "spend_arithmetic", "held_out_untouched"],
            "groups": errors, "calibration_grid": grid_rows,
            "test_issues_untouched": len(test_ids),
            "v2_estimated_cost_usd": checkpoint["estimated_spend_usd"],
            "decision": "retired_before_test"}


if __name__ == "__main__":
    result = audit()
    out = ROOT / "paper/results/graded_issue_gate/audit_v2.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"decision": result["decision"], "groups": result["groups"],
                      "provider_calls_executed": 0}, indent=2))
