#!/usr/bin/env python3
"""Summarize registered and exploratory gate selectivity evidence from retained artifacts."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
for candidate in (ROOT, ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))


NONZERO_EPS = 1e-12


@dataclass(frozen=True, slots=True)
class GateSource:
    artifact_id: str
    label: str
    source_path: str
    pointer: tuple[str, ...]
    evidence_status: str
    cohort: str
    note: str = ""


@dataclass(frozen=True, slots=True)
class RefusalSource:
    artifact_id: str
    label: str
    source_path: str
    pointer: tuple[str, ...]
    note: str = ""


CURRENT_REGISTERED_SOURCES: tuple[GateSource, ...] = (
    GateSource(
        artifact_id="github_natural_replication",
        label="Natural-order GitHub replication",
        source_path="paper/results/github_natural_replication/results.json",
        pointer=("compiler", "artifact", "gate"),
        evidence_status="current_registered",
        cohort="within_repo_live",
        note="Primary issue-type routing artifact at registered alpha=.05.",
    ),
    GateSource(
        artifact_id="workflow_pr_outcome",
        label="Workflow family: PR-outcome",
        source_path="paper/results/github_workflow_families/pr_outcome/final/results.json",
        pointer=("compiler", "artifact", "gate"),
        evidence_status="current_registered",
        cohort="within_repo_live",
        note="Richer workflow-family artifact at registered alpha=.05.",
    ),
    GateSource(
        artifact_id="workflow_backlog_attention",
        label="Workflow family: backlog-attention",
        source_path="paper/results/github_workflow_families/backlog_attention/final/results.json",
        pointer=("compiler", "artifact", "gate"),
        evidence_status="current_registered",
        cohort="within_repo_live",
        note="Richer workflow-family artifact at registered alpha=.05.",
    ),
    GateSource(
        artifact_id="multirepo_huggingface_datasets",
        label="Multirepo extension: huggingface/datasets",
        source_path="paper/results/github_multirepo_pr_outcome_core/results.json",
        pointer=("repositories", "huggingface/datasets", "compiler", "artifact", "gate"),
        evidence_status="current_registered",
        cohort="cross_repo_time_forward",
        note="Simplified two-read PR-outcome-core artifact at registered alpha=.05.",
    ),
    GateSource(
        artifact_id="multirepo_pandas_dev_pandas",
        label="Multirepo extension: pandas-dev/pandas",
        source_path="paper/results/github_multirepo_pr_outcome_core/results.json",
        pointer=("repositories", "pandas-dev/pandas", "compiler", "artifact", "gate"),
        evidence_status="current_registered",
        cohort="cross_repo_time_forward",
        note="Simplified two-read PR-outcome-core artifact at registered alpha=.05.",
    ),
    GateSource(
        artifact_id="multirepo_psf_requests",
        label="Multirepo extension: psf/requests",
        source_path="paper/results/github_multirepo_pr_outcome_core/results.json",
        pointer=("repositories", "psf/requests", "compiler", "artifact", "gate"),
        evidence_status="current_registered",
        cohort="cross_repo_time_forward",
        note="Simplified two-read PR-outcome-core artifact at registered alpha=.05.",
    ),
    GateSource(
        artifact_id="multirepo_streamlit_streamlit",
        label="Multirepo extension: streamlit/streamlit",
        source_path="paper/results/github_multirepo_pr_outcome_core/results.json",
        pointer=("repositories", "streamlit/streamlit", "compiler", "artifact", "gate"),
        evidence_status="current_registered",
        cohort="cross_repo_time_forward",
        note="Simplified two-read PR-outcome-core artifact at registered alpha=.05.",
    ),
)


EXPLORATORY_SOURCES: tuple[GateSource, ...] = (
    GateSource(
        artifact_id="github_live_pilot_2026_08_03",
        label="Archived live pilot (2026-08-03)",
        source_path="paper/results/github_live/pilot_2026-08-03/results.json",
        pointer=("compiler", "artifact", "gate"),
        evidence_status="archived_exploratory",
        cohort="within_repo_live",
        note=(
            "Archived exact-.05 pilot with a non-flat curve; retained as exploratory gate "
            "evidence, not as the main preserved-quality result."
        ),
    ),
    GateSource(
        artifact_id="github_natural_live",
        label="Earlier natural live artifact",
        source_path="paper/results/github_natural_live/results.json",
        pointer=("compiler", "artifact", "gate"),
        evidence_status="looser_alpha_current",
        cohort="within_repo_live",
        note="Current retained artifact, but calibrated at alpha=.10 rather than the registered .05.",
    ),
    GateSource(
        artifact_id="gcs_live",
        label="Guarded composite study",
        source_path="paper/results/gcs_live/results.json",
        pointer=("compiler", "artifact", "gate"),
        evidence_status="looser_alpha_current",
        cohort="within_repo_live",
        note="Only current retained partial-coverage frontier, but calibrated at alpha=.10.",
    ),
)


REFUSAL_SOURCES: tuple[RefusalSource, ...] = (
    RefusalSource(
        artifact_id="nestful",
        label="NESTFUL exact gate",
        source_path="paper/results/nestful/results.json",
        pointer=("compiler", "exact_gate"),
        note="Support shortfall on a trace-complete public benchmark.",
    ),
    RefusalSource(
        artifact_id="api_bank",
        label="API-Bank exact gate",
        source_path="paper/results/external_benchmarks/api_bank_execution.json",
        pointer=("compiler", "exact_gate"),
        note="Support shortfall on a second compiler-compatible benchmark substrate.",
    ),
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dig(payload: dict[str, Any], pointer: Iterable[str]) -> Any:
    current: Any = payload
    for key in pointer:
        current = current[key]
    return current


def parse_gate_rows(notes: str) -> list[dict[str, float]]:
    marker = "grid rows:"
    if marker not in notes:
        raise ValueError("gate notes do not include threshold-grid rows")
    raw = notes.split(marker, 1)[1].strip()
    rows = ast.literal_eval(raw)
    if not isinstance(rows, list):
        raise ValueError("parsed gate rows are not a list")
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("gate row is not a mapping")
        normalized.append(
            {
                "eta": float(row["eta"]),
                "n": int(row["n"]),
                "violations": int(row["violations"]),
                "upper": float(row["upper"]),
                "coverage": float(row["coverage"]),
            }
        )
    return normalized


def _nonzero_weights(model: dict[str, Any]) -> list[dict[str, float | str]]:
    features = list(model.get("features", []))
    weights = list(model.get("weights", []))
    out = []
    for feature, weight in zip(features, weights, strict=False):
        weight_value = float(weight)
        if abs(weight_value) > NONZERO_EPS:
            out.append({"feature": str(feature), "weight": weight_value})
    return out


def _frontier_type(rows: list[dict[str, float]]) -> str:
    if not rows:
        return "unknown"
    positive = [row for row in rows if row["n"] > 0]
    if not positive:
        return "retire_all_thresholds_empty"
    partial = [row for row in rows if 0.0 < row["coverage"] < 1.0]
    if partial:
        return "partial_frontier"
    observed_n = {row["n"] for row in rows}
    if len(observed_n) == 2 and 0 in observed_n:
        return "step_all_or_none"
    return "multi_step_nonpartial"


def analyze_gate_source(source: GateSource) -> dict[str, Any]:
    payload = load_json(ROOT / source.source_path)
    gate = dig(payload, source.pointer)
    rows = parse_gate_rows(str(gate.get("notes", "")))
    model = dict(gate.get("model", {}))
    nonzero = _nonzero_weights(model)
    distinct_coverages = sorted({round(float(row["coverage"]), 4) for row in rows})
    change_points = []
    previous_n: int | None = None
    for row in rows:
        current_n = int(row["n"])
        if previous_n is None or current_n != previous_n:
            change_points.append(dict(row))
        previous_n = current_n
    first_positive = next((row for row in rows if row["n"] > 0), None)
    first_full = next((row for row in rows if row["coverage"] >= 0.999999), None)
    first_admissible = next((row for row in rows if row["upper"] <= float(gate["alpha"])), None)
    exact_registered = (
        source.evidence_status == "current_registered" and float(gate["alpha"]) == 0.05
    )
    result = {
        "artifact_id": source.artifact_id,
        "label": source.label,
        "source_path": source.source_path,
        "cohort": source.cohort,
        "evidence_status": source.evidence_status,
        "registered_current_exact_alpha_0_05": exact_registered,
        "alpha": float(gate["alpha"]),
        "delta": float(gate["delta"]),
        "threshold": float(gate["threshold"]),
        "n_accepted": int(gate["n_accepted"]),
        "n_calibration_groups": int(gate["n_calibration_groups"]),
        "coverage": float(gate["coverage"]),
        "observed_violations": int(gate["observed_violations"]),
        "risk_upper_bound": float(gate["risk_upper_bound"]),
        "frontier_type": _frontier_type(rows),
        "first_positive_eta": None if first_positive is None else float(first_positive["eta"]),
        "first_full_coverage_eta": None if first_full is None else float(first_full["eta"]),
        "first_admissible_eta": None if first_admissible is None else float(first_admissible["eta"]),
        "distinct_coverage_levels": distinct_coverages,
        "change_points": change_points,
        "grid_rows": rows,
        "note": source.note,
        "model": {
            "bias": float(model.get("bias", 0.0)) if model else None,
            "features": list(model.get("features", [])),
            "nonzero_weights": nonzero,
            "nonzero_feature_count": len(nonzero),
            "distinct_nonzero_weight_count": len(
                {round(float(item["weight"]), 14) for item in nonzero}
            ),
        },
    }
    return result


def analyze_gate_source_with_optional_candidate_notes(source: GateSource) -> dict[str, Any]:
    result = analyze_gate_source(source)
    payload = load_json(ROOT / source.source_path)
    container = dig(payload, source.pointer[:-2])
    candidates = container.get("candidates", []) if isinstance(container, dict) else []
    matching: dict[str, Any] | None = None
    for candidate in candidates:
        gate = candidate.get("gate")
        if not isinstance(gate, dict):
            continue
        if (
            float(gate.get("threshold", -1)) == float(result["threshold"])
            and int(gate.get("n_accepted", -1)) == int(result["n_accepted"])
            and abs(float(gate.get("risk_upper_bound", -1.0)) - float(result["risk_upper_bound"])) < 1e-12
        ):
            matching = candidate
            break
    if isinstance(matching, dict) and isinstance(matching.get("notes"), dict):
        notes = matching["notes"]
        gate_note_payload = {
            key: value
            for key, value in notes.items()
            if key.startswith("gate_")
        }
        if gate_note_payload:
            result["gate_reason_summary"] = gate_note_payload
    return result


def analyze_refusal_source(source: RefusalSource) -> dict[str, Any]:
    payload = load_json(ROOT / source.source_path)
    exact_gate = dig(payload, source.pointer)
    max_support = int(
        exact_gate.get(
            "max_observed_family_support",
            exact_gate.get("max_observed_family_support", 0),
        )
    )
    required = int(
        exact_gate.get(
            "minimum_zero_violation_groups",
            exact_gate.get("minimum_zero_violation_groups", 0),
        )
    )
    return {
        "artifact_id": source.artifact_id,
        "label": source.label,
        "source_path": source.source_path,
        "analysis_kind": "support_shortfall_refusal",
        "alpha": float(exact_gate["alpha"]),
        "delta": float(exact_gate["delta"]),
        "max_observed_family_support": max_support,
        "minimum_zero_violation_groups": required,
        "support_shortfall": required - max_support,
        "families_certifiable_even_with_zero_violations": int(
            exact_gate.get(
                "families_certifiable_even_with_zero_violations",
                exact_gate.get("certifiable_families_even_if_zero_violations", 0),
            )
        ),
        "outcome": str(
            exact_gate.get("outcome", exact_gate.get("default_gate_outcome", "RETIRE"))
        ),
        "note": source.note,
    }


def _projection_failure_summary() -> dict[str, Any]:
    path = ROOT / "paper/results/github_workflow_families/pr_outcome/pilot_v1/failed_attempt_projection_2026-08-05.json"
    payload = load_json(path)
    by_condition: Counter[str] = Counter()
    by_reason: Counter[str] = Counter()
    for failure in payload.get("failures", []):
        by_condition[str(failure.get("condition", "unknown"))] += 1
        error = str(failure.get("error", ""))
        start = error.find("{")
        if start < 0:
            by_reason["unparsed_error"] += 1
            continue
        details = json.loads(error[start:])
        for reason in details.get("reasons", []):
            by_reason[str(reason)] += 1
    return {
        "source_path": str(path.relative_to(ROOT)),
        "condition_counts": dict(sorted(by_condition.items())),
        "reason_counts": dict(sorted(by_reason.items())),
        "note": (
            "Retained projection failures supply concrete negative reasons "
            "(projection mismatch, range rejection, hull rejection) that current exact-.05 "
            "gates do not expose directly in their final artifacts."
        ),
    }


def _failed_attempt_summary() -> dict[str, Any]:
    path = ROOT / "paper/results/github_natural_replication/failed_attempt_2026-08-03.json"
    payload = load_json(path)
    error = str(payload.get("error", ""))
    match = re.search(r"only (\\d+) compiler-eligible traces; need (\\d+)", error)
    return {
        "source_path": str(path.relative_to(ROOT)),
        "status": payload.get("status"),
        "stage": payload.get("stage"),
        "error": error,
        "eligible_traces": None if match is None else int(match.group(1)),
        "required_traces": None if match is None else int(match.group(2)),
        "note": (
            "The pre-fix live failure is retained as eligibility-side negative evidence, "
            "not as a quantitative gate result."
        ),
    }


def _pytorch_failed_closed_summary() -> list[dict[str, Any]]:
    path = ROOT / "paper/results/github_multirepo_pr_outcome_core/results.json"
    payload = load_json(path)
    out = []
    for item in payload.get("repository_failures", []):
        selection = dict(item.get("selection", {}))
        out.append(
            {
                "source_path": str(path.relative_to(ROOT)),
                "repository": item.get("repository"),
                "error": item.get("error"),
                "status": item.get("status", "failed_closed"),
                "discovery_class_counts": selection.get("discovery_class_counts", {}),
                "test_class_counts": selection.get("test_class_counts", {}),
                "note": (
                    "The fifth multirepo repository retires under the strict frozen-candidate "
                    "gate rather than broadening coverage post hoc."
                ),
            }
        )
    return out


def build_analysis() -> dict[str, Any]:
    artifacts = [
        analyze_gate_source_with_optional_candidate_notes(source)
        for source in (*CURRENT_REGISTERED_SOURCES, *EXPLORATORY_SOURCES)
    ]
    refusals = [analyze_refusal_source(source) for source in REFUSAL_SOURCES]

    registered = [
        artifact for artifact in artifacts if artifact["registered_current_exact_alpha_0_05"]
    ]
    exploratory = [
        artifact for artifact in artifacts if not artifact["registered_current_exact_alpha_0_05"]
    ]
    first_positive_counts = Counter(
        f"{artifact['first_positive_eta']:.2f}"
        for artifact in registered
        if artifact["first_positive_eta"] is not None
    )
    registered_step = [
        artifact for artifact in registered if artifact["frontier_type"] == "step_all_or_none"
    ]
    registered_partial = [
        artifact for artifact in registered if artifact["frontier_type"] == "partial_frontier"
    ]
    exploratory_partial = [
        artifact for artifact in exploratory if artifact["frontier_type"] == "partial_frontier"
    ]
    exact_nonzero_signatures = Counter(
        tuple(
            f"{item['feature']}={item['weight']:.12g}"
            for item in artifact["model"]["nonzero_weights"]
        )
        for artifact in registered
    )
    summary = {
        "registered_current": {
            "artifacts_analyzed": len(registered),
            "step_all_or_none": len(registered_step),
            "partial_frontier": len(registered_partial),
            "first_positive_eta_counts": dict(sorted(first_positive_counts.items())),
            "exact_coverage_fraction_at_selected_threshold": {
                artifact["artifact_id"]: artifact["coverage"] for artifact in registered
            },
            "model_nonzero_weight_signatures": {
                " | ".join(signature): count for signature, count in exact_nonzero_signatures.items()
            },
        },
        "exploratory_or_looser_alpha": {
            "artifacts_analyzed": len(exploratory),
            "partial_frontier": len(exploratory_partial),
            "artifact_ids": [artifact["artifact_id"] for artifact in exploratory],
        },
        "support_shortfall_refusals": {
            item["artifact_id"]: {
                "max_observed_family_support": item["max_observed_family_support"],
                "minimum_zero_violation_groups": item["minimum_zero_violation_groups"],
                "support_shortfall": item["support_shortfall"],
            }
            for item in refusals
        },
        "claim_boundary": (
            "The current exact-.05 artifacts still behave as support-threshold gates: "
            "seven of seven registered current artifacts are step functions with no "
            "partial frontier. Partial selectivity exists only in retained exploratory "
            "or looser-alpha artifacts, so the main paper should keep describing the "
            "registered gate as mostly all-or-none."
        ),
    }
    return {
        "schema": "agent-compaction-gate-selectivity-analysis/v1",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "registered_alpha": 0.05,
        "artifacts": artifacts,
        "support_shortfall_refusals": refusals,
        "negative_evidence": {
            "failed_projection_pilot": _projection_failure_summary(),
            "failed_live_attempt": _failed_attempt_summary(),
            "failed_closed_multirepo": _pytorch_failed_closed_summary(),
        },
        "summary": summary,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize retained gate selectivity evidence from checked-in artifacts."
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "paper/results/gate_selectivity_analysis.json",
        help="Destination JSON path (default: %(default)s)",
    )
    args = parser.parse_args(argv)
    analysis = build_analysis()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(analysis, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via CLI
    raise SystemExit(main())
