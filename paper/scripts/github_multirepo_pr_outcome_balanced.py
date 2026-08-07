#!/usr/bin/env python3
"""Balanced time-forward multirepo PR-outcome-core study."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import github_multirepo_preflight as preflight  # noqa: E402
import github_multirepo_pr_outcome_core as core  # noqa: E402


OUT_ROOT = ROOT / "paper" / "results" / "github_multirepo_pr_outcome_balanced"


def build_preflight(
    sources: Sequence[core.RepoSource],
    *,
    discovery_cases: int,
    test_cases: int,
    minimum_gap_days: int,
    seed: int,
    force_download: bool,
) -> dict[str, Any]:
    excluded = preflight.prior_records()
    repo_payloads: dict[str, Any] = {}
    complete_repos = 0
    pooled_test_cases = 0
    for source in sources:
        source_manifest = core.fetch_source(source, force=force_download)
        store, audit = core.load_store(source, source_manifest)
        try:
            selection = preflight.select_balanced_timeforward(
                source.repository,
                preflight.workflow_family.FAMILIES["pr_outcome"],
                store,
                discovery_cases=discovery_cases,
                test_cases=test_cases,
                seed=seed,
                minimum_gap_days=minimum_gap_days,
                excluded_numbers=excluded.get(source.repository, set()),
            )
        except preflight.PreflightDesignError as exc:
            repo_payloads[source.repository] = {
                "status": "unavailable",
                "audit": audit,
                "reason": str(exc),
            }
            continue
        repo_payloads[source.repository] = {
            "status": "selected",
            "audit": audit,
            "selection": selection,
        }
        complete_repos += 1
        pooled_test_cases += len(selection["test"])
    payload = {
        "schema": "agent-compaction-github-multirepo-pr-outcome-balanced-preflight/v1",
        "status": "designed_not_run",
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "provider_calls_executed": 0,
        "real_public_records": True,
        "simulated": False,
        "selection_protocol": "balanced_time_forward_round_robin",
        "resolved_config": {
            "repositories": [source.repository for source in sources],
            "discovery_cases": discovery_cases,
            "test_cases_per_repo": test_cases,
            "minimum_gap_days": minimum_gap_days,
            "seed": seed,
        },
        "repositories": repo_payloads,
        "global_checks": {
            "complete_repo_count": complete_repos,
            "pooled_test_cases": pooled_test_cases,
            "all_selected_repositories_time_forward": all(
                value.get("status") != "selected" or value["selection"]["time_forward"]["strict_time_forward"]
                for value in repo_payloads.values()
            ),
        },
    }
    payload["preflight_sha256"] = core.hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()
    return payload


async def run(args: argparse.Namespace) -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    core.OUT_ROOT = OUT_ROOT
    sources = core._selected_sources(args.repositories)
    preflight_payload = build_preflight(
        sources,
        discovery_cases=args.discovery_cases,
        test_cases=args.test_cases_per_repo,
        minimum_gap_days=args.minimum_gap_days,
        seed=args.seed,
        force_download=args.force_download,
    )
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    preflight_path = OUT_ROOT / "preflight.json"
    preflight_path.write_text(json.dumps(preflight_payload, indent=2, sort_keys=True) + "\n")
    if args.preflight_only:
        return {"preflight": preflight_payload}

    selected = {
        repository: value
        for repository, value in preflight_payload["repositories"].items()
        if value.get("status") == "selected"
    }
    if len(selected) < args.minimum_complete_repos:
        raise RuntimeError(
            f"only {len(selected)} repositories satisfy the balanced frozen protocol; need {args.minimum_complete_repos}"
        )
    if sum(len(value["selection"]["test"]) for value in selected.values()) < args.minimum_pooled_test_cases:
        raise RuntimeError("pooled held-out cohort is too small for the configured minimum")

    repo_results: dict[str, Any] = {}
    repo_failures: list[dict[str, Any]] = []
    pooled_results: list[core.RepoRunResult] = []
    pooled_failures: list[dict[str, Any]] = []
    for source in sources:
        if source.repository not in selected:
            continue
        source_manifest = selected[source.repository]["audit"]["source_manifest"]
        store, _ = core.load_store(source, source_manifest)
        discovery_rows = [
            dict(store[int(value["issue_number"])])
            for value in selected[source.repository]["selection"]["discovery"]
        ]
        test_rows = [
            dict(store[int(value["issue_number"])])
            for value in selected[source.repository]["selection"]["test"]
        ]
        try:
            repo_payload = await core.run_repo(
                source,
                source_manifest=source_manifest,
                store=store,
                selection=selected[source.repository]["selection"],
                discovery_rows=discovery_rows,
                test_rows=test_rows,
                args=args,
            )
        except Exception as exc:
            output_dir = core._repo_result_dir(source.repository)
            failure_payload = {
                "repository": source.repository,
                "status": "failed_closed",
                "error": f"{type(exc).__name__}: {exc}",
                "source": dict(source_manifest),
                "selection": selected[source.repository]["selection"],
                "discovery_checkpoint": core._checkpoint_summary(output_dir / "discovery_checkpoint.json"),
                "evaluation_checkpoint": core._checkpoint_summary(output_dir / "evaluation_checkpoint.json"),
            }
            repo_results[source.repository] = failure_payload
            repo_failures.append(failure_payload)
            continue
        repo_results[source.repository] = repo_payload
        if args.smoke:
            continue
        pooled_results.extend(
            core.RepoRunResult(
                repository=str(value["repository"]),
                condition=str(value["condition"]),
                repeat=int(value.get("repeat", 0)),
                issue_number=int(value["issue_number"]),
                trace_id=str(value["trace_id"]),
                metrics=dict(value["metrics"]),
                answer=dict(value["answer"]),
                quality=dict(value["quality"]),
                tool_sequence=list(value["tool_sequence"]),
                tool_arguments=[dict(item) for item in value["tool_arguments"]],
                dispatch=dict(value.get("dispatch", {})),
                episode=SimpleNamespace(to_dict=lambda value=value: {"episode_digest": value["episode_digest"]}),
            )
            for value in repo_payload["results"]
        )
        pooled_failures.extend(repo_payload["failures"])

    if args.smoke:
        payload = {
            "schema": "agent-compaction-github-multirepo-pr-outcome-balanced-smoke-summary/v1",
            "preflight": preflight_payload,
            "repositories": repo_results,
        }
        summary_path = OUT_ROOT / "smoke.json"
        summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")
        return payload

    grouped = {condition: [row for row in pooled_results if row.condition == condition] for condition in core.CONDITIONS}
    payload = {
        "schema": "agent-compaction-github-multirepo-pr-outcome-balanced-summary/v1",
        "run": {
            "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "repositories": list(repo_results),
            "family": core.SPEC.name,
            "model": args.model,
            "provider_backed": True,
            "real_public_records": True,
            "simulated": False,
            "openai_api_key_used": True,
            "secrets_serialized": False,
            "comparative_claim_allowed": not pooled_failures and not repo_failures,
            "selection_protocol": "balanced_time_forward_round_robin",
            "resolved_config": vars(args),
        },
        "preflight": preflight_payload,
        "aggregate": core.aggregate_runs(pooled_results),
        "comparisons": {
            "baseline_vs_compiled": core.paired(grouped["baseline"], grouped["compiled"], "compiled"),
            "baseline_vs_template_pre_model": core.paired(
                grouped["baseline"], grouped["template_pre_model"], "template_pre_model"
            ),
        },
        "failures": pooled_failures,
        "repository_failures": repo_failures,
        "repositories": repo_results,
        "pooled_test_pairs": len(grouped["baseline"]),
    }
    summary_path = OUT_ROOT / "results.json"
    summary_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repositories",
        nargs="+",
        default=tuple(core.DEFAULT_SOURCES),
        help="repositories to include; defaults to the built-in multirepo cohort",
    )
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--discovery-cases", type=int, default=120)
    parser.add_argument("--test-cases-per-repo", type=int, default=60)
    parser.add_argument("--minimum-gap-days", type=int, default=0)
    parser.add_argument("--minimum-complete-repos", type=int, default=3)
    parser.add_argument("--minimum-pooled-test-cases", type=int, default=180)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260807)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--force-download", action="store_true")
    args = parser.parse_args()
    if args.discovery_cases < 120 and not (args.preflight_only or args.smoke):
        parser.error("--discovery-cases must be at least 120 for the balanced exact gate")
    if args.discovery_cases % 3 != 0:
        parser.error("--discovery-cases must be divisible by three for balanced class allocation")
    if args.test_cases_per_repo <= 0 or args.test_cases_per_repo % 3 != 0:
        parser.error("--test-cases-per-repo must be positive and divisible by three")
    if args.concurrency <= 0:
        parser.error("--concurrency must be positive")
    return args


def main() -> None:
    payload = asyncio.run(run(parse_args()))
    summary = {
        "schema": payload.get("schema", payload.get("preflight", {}).get("schema")),
        "run": payload.get("run"),
        "aggregate": payload.get("aggregate"),
        "comparisons": payload.get("comparisons"),
        "failures": payload.get("failures"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
