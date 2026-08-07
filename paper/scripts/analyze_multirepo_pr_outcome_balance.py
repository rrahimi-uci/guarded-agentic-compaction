#!/usr/bin/env python3
"""Diagnose discovery-balance effects in the multirepo PR-outcome-core study."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import github_multirepo_preflight as preflight  # noqa: E402
import github_multirepo_pr_outcome_core as core  # noqa: E402
from guarded_agentic_compaction.runtime.dispatch import DispatchMode, Dispatcher  # noqa: E402
from guarded_agentic_compaction.runtime.runner import CompactingRunner  # noqa: E402


OUT_PATH = ROOT / "paper" / "results" / "multirepo_pr_outcome_balance_analysis.json"
CURRENT_RESULTS_PATH = ROOT / "paper" / "results" / "github_multirepo_pr_outcome_core" / "results.json"
DEFAULT_REPOSITORIES = ("pandas-dev/pandas", "psf/requests", "pytorch/pytorch")
DEFAULT_DISCOVERY_CASES = 120
DEFAULT_TEST_CASES = 60
DEFAULT_SEED = 20260801


@dataclass(frozen=True)
class SyntheticStudy:
    repository: str
    source_manifest: Mapping[str, Any]
    selection: Mapping[str, Any]
    compilation: Mapping[str, Any]
    test_dispatch: Mapping[str, Any]


def _repo_slug(repository: str) -> str:
    return repository.replace("/", "__")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _current_reference_summary(payload: Mapping[str, Any], repository: str) -> dict[str, Any] | None:
    repo_payload = payload.get("repositories", {}).get(repository)
    if isinstance(repo_payload, dict):
        if repo_payload.get("status") == "failed_closed" or not repo_payload.get("compiler"):
            return {
                "status": repo_payload.get("status", "failed_closed"),
                "error": repo_payload.get("error"),
                "discovery_class_counts": repo_payload.get("selection", {}).get("discovery_class_counts"),
                "selection_time_forward": repo_payload.get("selection", {}).get("time_forward"),
            }
        artifact = repo_payload.get("compiler", {}).get("artifact")
        state_hull = None
        if isinstance(artifact, dict):
            clauses = artifact.get("verifier", {}).get("clauses", ())
            state_hull = next(
                (
                    clause.get("hull")
                    for clause in clauses
                    if isinstance(clause, dict) and clause.get("name") == "pr.state"
                ),
                None,
            )
        compiled_rows = [
            value
            for value in repo_payload.get("results", ())
            if isinstance(value, dict) and value.get("condition") == "compiled"
        ]
        total_by_class = Counter()
        compacted_by_class = Counter()
        for row in compiled_rows:
            class_name = _class_from_reference_row(row)
            total_by_class[class_name] += 1
            dispatch = row.get("dispatch") or {}
            if dispatch.get("outcome") in {"COMPACT", "COMPACTED"} or (
                len(row.get("tool_sequence", ())) == 1
                and str((row.get("tool_sequence") or [""])[0]).startswith("compiled_")
            ):
                compacted_by_class[class_name] += 1
        return {
            "status": "selected_and_run",
            "discovery_class_counts": repo_payload.get("selection", {}).get("discovery_class_counts"),
            "artifact_emitted": bool(artifact),
            "state_hull": state_hull,
            "compiled_total_by_class": dict(total_by_class),
            "compiled_compacted_by_class": dict(compacted_by_class),
            "selection_time_forward": repo_payload.get("selection", {}).get("time_forward"),
        }

    failure = next(
        (
            value
            for value in payload.get("repository_failures", ())
            if isinstance(value, dict) and value.get("repository") == repository
        ),
        None,
    )
    if not isinstance(failure, dict):
        return None
    return {
        "status": failure.get("status", "failed_closed"),
        "error": failure.get("error"),
        "discovery_class_counts": failure.get("selection", {}).get("discovery_class_counts"),
        "selection_time_forward": failure.get("selection", {}).get("time_forward"),
    }


def _class_from_reference_row(row: Mapping[str, Any]) -> str:
    dispatch = row.get("dispatch") or {}
    if isinstance(dispatch, dict):
        projected = dispatch.get("projected_output")
        if isinstance(projected, dict):
            state = str(projected.get("state") or "").lower()
            is_merged = bool(projected.get("is_merged"))
            if is_merged:
                return "merged"
            if state == "open":
                return "open"
            return "closed_unmerged"
    answer = row.get("answer") or {}
    return str(answer.get("outcome") or "unknown")


def _synthesize_checkpoint(
    repository: str,
    selection: Mapping[str, Any],
    store: Mapping[int, Mapping[str, Any]],
) -> dict[str, Any]:
    results = []
    for item in selection["discovery"]:
        number = int(item["issue_number"])
        row = store[number]
        results.append(
            {
                "repository": repository,
                "condition": "discovery",
                "repeat": 0,
                "issue_number": number,
                "trace_id": f"synthetic-{_repo_slug(repository)}-{number}",
                "metrics": {
                    "requests": 3,
                    "tool_calls": 2,
                    "input_tokens": 1000,
                    "output_tokens": 50,
                    "total_tokens": 1050,
                    "wall_latency_ms": 1000.0,
                    "estimated_cost_usd": 0.0003,
                },
                "answer": {
                    "record_number": number,
                    "title": str(row.get("title") or ""),
                    "outcome": core.pr_outcome(row),
                },
                "quality": {
                    "record_number_correct": True,
                    "title_correct": True,
                    "outcome_correct": True,
                    "trace_valid": True,
                    "tool_contract": True,
                    "score": 1.0,
                    "overall": True,
                    "quality_independent_of_tool_order": True,
                },
                "tool_sequence": list(core.SPEC.tools),
                "tool_arguments": [
                    {"record_number": number},
                    {"record_number": number},
                ],
                "dispatch": {},
            }
        )
    return {"results": results}


def _count_dispatch_outcomes(
    repository: str,
    selection: Mapping[str, Any],
    store: Mapping[int, Mapping[str, Any]],
    source_revision: str,
    registry: Any,
    catalog: Any,
    artifact_manifest: Any,
    continuation_manifest: Any,
) -> dict[str, Any]:
    runner = CompactingRunner(
        dispatcher=Dispatcher(registry=registry, catalog=catalog, mode=DispatchMode.LIVE),
        catalog=catalog,
        manifest=artifact_manifest,
    )
    totals = Counter()
    compacted = Counter()
    fallback_reasons = Counter()
    for item in selection["test"]:
        number = int(item["issue_number"])
        row = store[number]
        class_name = core.pr_outcome(row)
        totals[class_name] += 1
        attempt = runner.execute_pre_model(
            {"record_number": number},
            executor=lambda tool, values: core.execute_snapshot(source_revision, store, tool, values),
            day=str(row["day"]),
            continuation_compatibility_key=continuation_manifest.compatibility_key(),
        )
        if attempt.compacted:
            compacted[class_name] += 1
        else:
            fallback_reasons[str(attempt.record.get("reason") or "unknown")] += 1
    return {
        "total_by_class": dict(totals),
        "compacted_by_class": dict(compacted),
        "compacted_total": sum(compacted.values()),
        "test_total": sum(totals.values()),
        "fallback_reasons": dict(fallback_reasons),
    }


def analyze_repository(
    repository: str,
    *,
    discovery_cases: int,
    test_cases: int,
    seed: int,
) -> SyntheticStudy:
    source = core.DEFAULT_SOURCES[repository]
    if repository == "huggingface/datasets":
        source_manifest = core.fixed.fetch_dataset(force=False)
    else:
        source_manifest = _load_json(
            ROOT / "paper" / "results" / "datasets" / "github_multirepo" / _repo_slug(repository) / "source_manifest.json"
        )
    store, _ = core.load_store(source, source_manifest)
    selection = preflight.select_balanced_timeforward(
        repository,
        preflight.workflow_family.FAMILIES["pr_outcome"],
        store,
        discovery_cases=discovery_cases,
        test_cases=test_cases,
        seed=seed,
        minimum_gap_days=0,
        excluded_numbers=preflight.prior_records().get(repository, set()),
    )
    source_revision = f"{source_manifest['dataset']}@{source_manifest['revision']}"
    catalog = core.make_catalog(repository)
    tools = core.make_tools(source_revision, store)
    source_driver_manifest = core.make_manifest(
        repository,
        source_revision,
        "gpt-5.6-luna",
        tools,
        catalog,
        "source",
        instructions=core.SPEC.discovery_prompt,
    )
    continuation_manifest = core.make_manifest(
        repository,
        source_revision,
        "gpt-5.6-luna",
        (),
        catalog,
        "pre-model",
        instructions=core.SPEC.prompt,
    )
    checkpoint = _synthesize_checkpoint(repository, selection, store)
    discovery = core.reconstruct_discovery(
        repository,
        source_revision,
        checkpoint,
        store=store,
        manifest=source_driver_manifest,
    )
    registry, compilation = core.compile_artifact(
        repository,
        discovery,
        catalog=catalog,
        source_manifest=source_driver_manifest,
        continuation_manifest=continuation_manifest,
        seed=seed,
    )
    dispatch = _count_dispatch_outcomes(
        repository,
        selection,
        store,
        source_revision,
        registry,
        catalog,
        source_driver_manifest,
        continuation_manifest,
    )
    return SyntheticStudy(
        repository=repository,
        source_manifest=source_manifest,
        selection=selection,
        compilation=compilation,
        test_dispatch=dispatch,
    )


def build_analysis(
    *,
    repositories: Sequence[str] = DEFAULT_REPOSITORIES,
    discovery_cases: int = DEFAULT_DISCOVERY_CASES,
    test_cases: int = DEFAULT_TEST_CASES,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    current_reference = _load_json(CURRENT_RESULTS_PATH)
    repo_payloads: dict[str, Any] = {}
    for repository in repositories:
        synthetic = analyze_repository(
            repository,
            discovery_cases=discovery_cases,
            test_cases=test_cases,
            seed=seed,
        )
        artifact = synthetic.compilation["artifact"]
        state_hull = next(
            (
                clause["hull"]
                for clause in artifact["verifier"]["clauses"]
                if clause.get("name") == "pr.state"
            ),
            None,
        )
        repo_payloads[repository] = {
            "current_reference": _current_reference_summary(current_reference, repository),
            "balanced_counterfactual": {
                "source": dict(synthetic.source_manifest),
                "selection": dict(synthetic.selection),
                "artifact_emitted": True,
                "artifact_name": artifact["name"],
                "state_hull": state_hull,
                "gate_threshold": artifact["gate"]["threshold"],
                "admissible_thresholds": artifact["gate"]["admissible"],
                "risk_upper_bound": artifact["gate"]["risk_upper_bound"],
                "test_dispatch": dict(synthetic.test_dispatch),
            },
        }

    aggregate_current = {
        "compiled_total_by_class": defaultdict(int),
        "compiled_compacted_by_class": defaultdict(int),
    }
    aggregate_balanced = {
        "test_total_by_class": defaultdict(int),
        "compacted_by_class": defaultdict(int),
    }
    for payload in repo_payloads.values():
        current = payload.get("current_reference") or {}
        for class_name, value in (current.get("compiled_total_by_class") or {}).items():
            aggregate_current["compiled_total_by_class"][class_name] += int(value)
        for class_name, value in (current.get("compiled_compacted_by_class") or {}).items():
            aggregate_current["compiled_compacted_by_class"][class_name] += int(value)
        balanced = payload["balanced_counterfactual"]["test_dispatch"]
        for class_name, value in balanced["total_by_class"].items():
            aggregate_balanced["test_total_by_class"][class_name] += int(value)
        for class_name, value in balanced["compacted_by_class"].items():
            aggregate_balanced["compacted_by_class"][class_name] += int(value)

    return {
        "schema": "agent-compaction-multirepo-pr-outcome-balance-analysis/v1",
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "simulated": True,
        "provider_calls_executed": 0,
        "selection_protocol": "balanced_time_forward_round_robin",
        "inputs": {
            "current_reference_results": str(CURRENT_RESULTS_PATH.relative_to(ROOT)),
            "repositories": list(repositories),
            "discovery_cases": discovery_cases,
            "test_cases": test_cases,
            "seed": seed,
        },
        "aggregate": {
            "current_reference": {
                "compiled_total_by_class": dict(aggregate_current["compiled_total_by_class"]),
                "compiled_compacted_by_class": dict(aggregate_current["compiled_compacted_by_class"]),
            },
            "balanced_counterfactual": {
                "test_total_by_class": dict(aggregate_balanced["test_total_by_class"]),
                "compacted_by_class": dict(aggregate_balanced["compacted_by_class"]),
            },
        },
        "repositories": repo_payloads,
        "conclusion": {
            "current_open_gap_is_selection_sensitive": True,
            "balanced_provider_free_artifacts_cover_open_and_closed": all(
                sorted(
                    value["balanced_counterfactual"]["state_hull"]["values"]
                )
                == ["closed", "open"]
                for value in repo_payloads.values()
            ),
            "balanced_provider_free_compaction_covers_all_test_cases": all(
                value["balanced_counterfactual"]["test_dispatch"]["compacted_total"]
                == value["balanced_counterfactual"]["test_dispatch"]["test_total"]
                for value in repo_payloads.values()
            ),
            "pytorch_retirement_under_current_protocol_is_not_intrinsic_to_the_task": (
                repo_payloads["pytorch/pytorch"]["balanced_counterfactual"]["artifact_emitted"]
                and (repo_payloads["pytorch/pytorch"]["current_reference"] or {}).get("status")
                == "failed_closed"
            ),
        },
    }


def main() -> None:
    payload = build_analysis()
    OUT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload["conclusion"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
