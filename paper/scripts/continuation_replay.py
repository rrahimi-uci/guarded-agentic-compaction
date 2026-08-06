#!/usr/bin/env python3
"""Provider-free continuation-contract replay on retained real-provider outputs.

This is a counterfactual safety-layer evaluation, not a new live run. It takes the 18
sealed compiled answers from the natural GitHub study, rebuilds the exact three read
observations from the pinned public snapshot, validates each answer, and invokes a
deterministic checked renderer only when validation fails. No model, network, or secret is
used and no latency/cost improvement is claimed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Sequence

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import github_live_study as fixed  # noqa: E402
from guarded_agentic_compaction.runtime.continuation import (  # noqa: E402
    ContinuationEvidence,
    ContinuationGuard,
)


SOURCE = ROOT / "paper/results/github_natural_live/results.json"
OUTPUT = ROOT / "paper/results/github_natural_live/continuation_replay.json"


def normalize(value: Any) -> str:
    return " ".join(str(value or "").split())


def observations_for(item: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    """Reconstruct exactly the source fields returned by the three pinned read tools."""

    return (
        {
            "tool": "issue_get_record",
            "result": {
                "issue_number": item["number"],
                "title": item["title"],
                "state": item["state"],
            },
        },
        {"tool": "issue_get_labels", "result": {"labels": list(item["labels"])}},
        {
            "tool": "issue_get_comments",
            "result": {"comments": list(item["comments"][:3])},
        },
    )


def _source(evidence: ContinuationEvidence) -> tuple[dict[str, Any], list[str], list[str]]:
    by_tool = {
        str(observation["tool"]): observation["result"]
        for observation in evidence.observations
        if isinstance(observation, dict)
        and isinstance(observation.get("result"), dict)
    }
    record = by_tool.get("issue_get_record", {})
    labels = [str(value) for value in by_tool.get("issue_get_labels", {}).get("labels", [])]
    comments = [
        normalize(value)
        for value in by_tool.get("issue_get_comments", {}).get("comments", [])[:3]
        if normalize(value)
    ]
    return record, labels, comments


def exact_contract(output: Any, evidence: ContinuationEvidence) -> Sequence[str]:
    if not isinstance(output, dict):
        return ("schema:not_mapping",)
    record, labels, comments = _source(evidence)
    category = fixed.category_for(labels)
    expected_label = category if category != "other" else "none"
    excerpt = normalize(output.get("comment_evidence"))
    checks = {
        "issue_number": output.get("issue_number") == record.get("issue_number"),
        "title": normalize(output.get("title")) == normalize(record.get("title")),
        "state": normalize(output.get("state")).lower() == normalize(record.get("state")).lower(),
        "category": output.get("category") == category,
        "evidence_label": output.get("evidence_label") == expected_label,
        "comment_evidence": (
            any(excerpt in comment for comment in comments)
            if comments
            else excerpt.lower() == "none"
        ),
    }
    return tuple(f"{name}:mismatch" for name, passed in checks.items() if not passed)


def checked_renderer(evidence: ContinuationEvidence) -> dict[str, Any]:
    """Render only fields deterministically established by the three observations."""

    record, labels, comments = _source(evidence)
    required = {"issue_number", "title", "state"}
    if not required <= record.keys():
        raise ValueError("incomplete record observation")
    category = fixed.category_for(labels)
    # Normalization matches the public contract; taking a prefix preserves exact
    # containment while respecting the original 180-character output schema.
    excerpt = comments[0][:180] if comments else "none"
    return {
        "issue_number": record["issue_number"],
        "title": record["title"],
        "state": record["state"],
        "category": category,
        "evidence_label": category if category != "other" else "none",
        "comment_evidence": excerpt,
    }


def run() -> dict[str, Any]:
    source_payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    frame = pd.read_parquet(fixed.DATA_PATH)
    store, _duplicates = fixed.build_store(frame)
    rows = [row for row in source_payload["results"] if row["condition"] == "compiled"]
    if len(rows) != 18:
        raise RuntimeError(f"expected 18 compiled rows, found {len(rows)}")

    guard = ContinuationGuard(exact_contract, renderer=checked_renderer)
    cases: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda value: int(value["issue_number"])):
        number = int(row["issue_number"])
        evidence = ContinuationEvidence(
            entry_state={"issue_number": number},
            observations=observations_for(store[number]),
            artifact_id=str(row.get("dispatch", {}).get("artifact_id") or "github-natural-grc"),
            metadata={"source_revision": fixed.HF_REVISION},
        )
        original_violations = tuple(exact_contract(row["answer"], evidence))
        decision = guard.decide(row["answer"], evidence)
        final_violations = tuple(exact_contract(decision.output, evidence)) if decision.accepted else ()
        cases.append(
            {
                "issue_number": number,
                "source_trace_id": row["trace_id"],
                "original_pass": not original_violations,
                "original_violations": list(original_violations),
                "decision": decision.record,
                "final_pass": decision.accepted and not final_violations,
                "final_violations": list(final_violations),
                "rendered_output": decision.output if decision.recovered else None,
            }
        )

    payload = {
        "schema": "agent-compaction-continuation-replay/v1",
        "evidence_class": "provider_free_counterfactual_on_retained_real_provider_outputs",
        "provider_calls_executed": 0,
        "secrets_used": False,
        "counterfactual": True,
        "source_results": {
            "path": str(SOURCE.relative_to(ROOT)),
            "sha256": fixed.sha256(SOURCE),
            "compiled_rows": len(rows),
            "data_revision": fixed.HF_REVISION,
            "data_sha256": fixed.HF_PARQUET_SHA256,
        },
        "claim_boundary": {
            "establishes": "deterministic replay detection and checked rendering on retained cases",
            "does_not_establish": [
                "live end-to-end latency or cost after continuation checking",
                "semantic quality beyond the registered exact-source contract",
                "generalization beyond the frozen GitHub issue task",
            ],
        },
        "summary": {
            "candidate_passes": sum(case["original_pass"] for case in cases),
            "candidate_failures": sum(not case["original_pass"] for case in cases),
            "accepted_without_repair": sum(
                case["decision"]["outcome"] == "ACCEPTED" for case in cases
            ),
            "checked_render_repairs": sum(
                case["decision"]["outcome"] == "RENDERED" for case in cases
            ),
            "rejections": sum(case["decision"]["outcome"] == "REJECTED" for case in cases),
            "final_contract_passes": sum(case["final_pass"] for case in cases),
        },
        "telemetry": guard.telemetry.as_dict(),
        "cases": cases,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    payload = run()
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
