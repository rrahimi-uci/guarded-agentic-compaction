#!/usr/bin/env python3
"""Prospective live evaluation of the risk-bounded optimization portfolio.

The selector is fitted only from the completed, real-record natural-workflow
replication.  It then chooses baseline, compiler, or macro before this script touches
the fresh held-out records.  The prospective arm executes the unchanged agent and the
selected action against a pinned snapshot of real public GitHub issues through the live
OpenAI Agents SDK.  No secret value is printed or serialized.

Macros are recommendations, not silently deployed transformations.  A live run therefore
requires ``--approve-reviewed-macro`` when the selected action is a macro.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import platform
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any, Sequence

import pandas as pd
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import github_live_study as fixed  # noqa: E402
from guarded_agentic_compaction.capture.agents_sdk import AgentsTraceProcessor  # noqa: E402
from guarded_agentic_compaction.portfolio import (  # noqa: E402
    PortfolioObservation,
    SelectionConfig,
    select_portfolio_action,
)


CALIBRATION_PATH = ROOT / "paper/results/github_natural_replication/results.json"
OUT_DIR = ROOT / "paper/results/portfolio_live"
TASK_DESIGN = "natural-extractive-v2"


def family_key(*, model: str) -> str:
    payload = {
        "dataset_revision": fixed.HF_REVISION,
        "model": model,
        "task_design": TASK_DESIGN,
        "prompt_sha256": hashlib.sha256(fixed.prompt_for(TASK_DESIGN).encode()).hexdigest(),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()[:20]


def portfolio_observations(payload: dict[str, Any], *, compatibility_key: str) -> list[PortfolioObservation]:
    """Convert retained paired outputs into group-aware portfolio observations."""

    rows: dict[tuple[int, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in payload["results"]:
        condition = str(row.get("condition"))
        if condition not in {"baseline", "compiled", "macro"}:
            continue
        key = (int(row["issue_number"]), int(row.get("repeat", 0)))
        rows[key][condition] = row
    observations: list[PortfolioObservation] = []
    for (issue_number, repeat), conditions in sorted(rows.items()):
        baseline = conditions.get("baseline")
        if baseline is None:
            continue
        for condition, action in (("compiled", "compile"), ("macro", "macro")):
            candidate = conditions.get(condition)
            if candidate is None:
                continue
            observations.append(
                PortfolioObservation(
                    group_id=f"github-issue:{issue_number}",
                    action=action,
                    baseline_quality=bool(baseline["quality"]["overall"]),
                    candidate_quality=bool(candidate["quality"]["overall"]),
                    baseline_metrics=baseline["metrics"],
                    candidate_metrics=candidate["metrics"],
                    compatibility_key=compatibility_key,
                    metadata={"issue_number": issue_number, "repeat": repeat},
                )
            )
    return observations


def select_action(*, model: str) -> tuple[Any, SelectionConfig, dict[str, Any]]:
    payload = json.loads(CALIBRATION_PATH.read_text(encoding="utf-8"))
    calibration_model = payload["run"]["model"]
    if calibration_model != model:
        raise ValueError(
            f"calibration model {calibration_model!r} does not match requested model {model!r}"
        )
    key = family_key(model=model)
    config = SelectionConfig(
        quality_risk_limit=0.15,
        regret_risk_limit=0.15,
        confidence=0.95,
        minimum_groups=30,
        minimum_utility=0.0,
        expected_compatibility_key=key,
    )
    decision = select_portfolio_action(
        portfolio_observations(payload, compatibility_key=key),
        config=config,
    )
    return decision, config, payload


def prior_issue_numbers() -> set[int]:
    numbers: set[int] = set()
    paths = [
        ROOT / "paper/results/github_live/results.json",
        ROOT / "paper/results/github_live/pilot_2026-08-03/results.json",
        ROOT / "paper/results/github_natural_live/results.json",
        ROOT / "paper/results/github_natural_replication/results.json",
        OUT_DIR / "results.json",
    ]
    for path in paths:
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        numbers.update(
            int(row["issue_number"])
            for row in payload.get("results", [])
            if "issue_number" in row
        )
        numbers.update(int(value) for value in payload.get("selection", {}).get("discovery_issue_numbers", []))
        numbers.update(
            int(row["issue_number"])
            for row in payload.get("selection", {}).get("test", [])
            if "issue_number" in row
        )
    return numbers


def fresh_scenarios(
    store: dict[int, dict[str, Any]], *, cases_per_class: int, seed: int
) -> tuple[list[fixed.Scenario], dict[str, Any]]:
    excluded = prior_issue_numbers()
    by_category: dict[str, list[int]] = defaultdict(list)
    for number, item in store.items():
        if number in excluded or len(item["body"].strip()) < 80:
            continue
        category = fixed.category_for(item["labels"])
        if category != "other" and set(item["labels"]).intersection(
            {"bug", "enhancement", "question"}
        ) != {category}:
            continue
        by_category[category].append(number)
    preferred = ("bug", "enhancement", "question", "other")
    selected_categories = [
        category
        for category in preferred
        if len(by_category.get(category, ())) >= cases_per_class
    ][:3]
    if len(selected_categories) < 3:
        counts = {key: len(values) for key, values in by_category.items()}
        raise RuntimeError(
            f"fewer than three categories have {cases_per_class} fresh records: {counts}"
        )
    numbers: list[int] = []
    for category in selected_categories:
        ranked = sorted(
            by_category[category],
            key=lambda value: fixed._stable_rank(
                value, seed, f"portfolio-test:{category}"
            ),
        )
        numbers.extend(ranked[:cases_per_class])

    def scenario(number: int) -> fixed.Scenario:
        item = store[number]
        return fixed.Scenario(
            issue_number=number,
            category=fixed.category_for(item["labels"]),
            labels=tuple(item["labels"]),
            html_url=item["html_url"],
            day=item["day"],
            state=item["state"],
        )

    scenarios = [scenario(number) for number in numbers]
    return scenarios, {
        "seed": seed,
        "excluded_prior_issue_count": len(excluded),
        "categories": selected_categories,
        "cases_per_class": cases_per_class,
        "test": [asdict(item) for item in scenarios],
        "available_fresh_category_counts": {
            key: len(values) for key, values in sorted(by_category.items())
        },
        "filters": {
            "exclude_all_prior_study_records": True,
            "exclude_pull_requests": True,
            "minimum_body_characters": 80,
            "exclusive_named_category": True,
        },
    }


async def run_pair(
    scenarios: Sequence[fixed.Scenario],
    *,
    model: str,
    store: dict[int, dict[str, Any]],
    concurrency: int,
    seed: int,
) -> tuple[list[Any], list[dict[str, Any]], dict[str, Any]]:
    """Counterbalance baseline and the preselected macro across two stages."""

    tools = fixed.make_tools(store)
    catalog = fixed.make_catalog()
    manifest = fixed.make_manifest(model, tools, catalog, TASK_DESIGN)
    macro_tools = fixed.make_macro_tool(store)
    macro_catalog = fixed.make_macro_catalog()
    macro_manifest = fixed.make_manifest(model, macro_tools, macro_catalog, TASK_DESIGN)
    from agents import add_trace_processor

    processor = AgentsTraceProcessor(include_sensitive_data=True, max_completed=256)
    add_trace_processor(processor)
    ranked = sorted(
        scenarios,
        key=lambda item: fixed._stable_rank(item.issue_number, seed, "portfolio-order"),
    )
    split = (len(ranked) + 1) // 2
    first, second = ranked[:split], ranked[split:]
    stages = (
        (("baseline", first), ("macro", second)),
        (("macro", first), ("baseline", second)),
    )
    results: list[Any] = []
    failures: list[dict[str, Any]] = []
    schedule: list[dict[str, Any]] = []
    for stage_index, stage in enumerate(stages):
        for condition, batch in stage:
            if not batch:
                continue
            is_macro = condition == "macro"
            values, batch_failures = await fixed.run_agents_batch(
                batch,
                condition=condition,
                repeat=0,
                model_name=model,
                tools=macro_tools if is_macro else tools,
                processor=processor,
                manifest=macro_manifest if is_macro else manifest,
                catalog=macro_catalog if is_macro else catalog,
                registry=None,
                concurrency=concurrency,
                task_design=TASK_DESIGN,
                source_store=store,
            )
            results.extend(values)
            failures.extend(batch_failures)
            schedule.append(
                {
                    "stage": stage_index,
                    "condition": condition,
                    "issue_numbers": [item.issue_number for item in batch],
                }
            )
    assignments = {
        str(item.issue_number): (
            ["baseline", "macro"] if item in first else ["macro", "baseline"]
        )
        for item in ranked
    }
    return results, failures, {
        "method": "two-condition-counterbalanced",
        "assignments": assignments,
        "batch_schedule": schedule,
    }


def _config_dict(config: SelectionConfig) -> dict[str, Any]:
    value = asdict(config)
    value["weights"] = asdict(config.weights)
    return value


async def async_main(args: argparse.Namespace) -> None:
    decision, config, calibration = select_action(model=args.model)
    source_manifest = fixed.fetch_dataset(args.force_download)
    frame = pd.read_parquet(fixed.DATA_PATH)
    store, duplicates = fixed.build_store(frame)
    scenarios, selection = fresh_scenarios(
        store, cases_per_class=args.cases_per_class, seed=args.seed
    )
    preflight = {
        "schema": "agent-compaction-portfolio-live/v1",
        "status": "preflight" if args.preflight else "running",
        "decision": decision.as_dict(),
        "selection_config": _config_dict(config),
        "calibration": {
            "path": str(CALIBRATION_PATH.relative_to(ROOT)),
            "sha256": fixed.sha256(CALIBRATION_PATH),
            "independent_groups": len(
                {row["issue_number"] for row in calibration["results"] if row["condition"] == "baseline"}
            ),
            "provider_outputs_reused": True,
        },
        "source_manifest": source_manifest,
        "selection": selection,
        "dataset_audit": {
            "raw_rows": len(frame),
            "deduplicated_non_pr_issues": len(store),
            "duplicate_issue_rows": sum(duplicates.values()),
        },
        "provider_calls_executed": 0,
        "macro_review_approved": bool(args.approve_reviewed_macro),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "preflight.json").write_text(
        json.dumps(preflight, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    if args.preflight:
        print(json.dumps(preflight, indent=2, sort_keys=True, default=str))
        return
    if decision.selected_action != "macro":
        raise RuntimeError(
            f"this prospective protocol expects a reviewed macro selection; got {decision.selected_action!r}"
        )
    if decision.requires_review and not args.approve_reviewed_macro:
        raise RuntimeError("selected macro requires --approve-reviewed-macro before provider calls")
    load_dotenv(ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set in .env or the environment")
    results, failures, schedule = await run_pair(
        scenarios,
        model=args.model,
        store=store,
        concurrency=args.concurrency,
        seed=args.seed,
    )
    baseline = [row for row in results if row.condition == "baseline"]
    selected = [row for row in results if row.condition == "macro"]
    common = set(row.issue_number for row in baseline) & set(row.issue_number for row in selected)
    payload = {
        "schema": "agent-compaction-portfolio-live/v1",
        "status": "complete" if not failures and len(common) == len(scenarios) else "incomplete",
        "run": {
            "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "script": "paper/scripts/portfolio_live_study.py",
            "model": args.model,
            "task_design": TASK_DESIGN,
            "openai_agents_sdk": version("openai-agents"),
            "openai_python": version("openai"),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "openai_api_key_used": True,
            "hf_token_used_for_download": bool(os.getenv("HF_TOKEN")),
            "secrets_serialized": False,
            "evidence_class": "fresh real public records + deterministic snapshot tools + live OpenAI provider",
            "prospective_action_selection": True,
            "shadow_nonselected_action_executed": False,
            "not_evidence_for": [
                "live GitHub service reliability",
                "multi-domain generalization",
                "automatic macro synthesis",
                "production deployment safety",
            ],
        },
        "decision": decision.as_dict(),
        "selection_config": _config_dict(config),
        "calibration": preflight["calibration"],
        "source_manifest": source_manifest,
        "selection": selection,
        "condition_order": schedule,
        "aggregate": fixed.aggregate_runs(results),
        "paired_selected_vs_baseline": fixed.paired_analysis(
            baseline,
            selected,
            candidate_label="selected_macro",
            baseline_label="baseline",
        ),
        "quality": {
            "paired_groups": len(common),
            "baseline_exact": sum(row.quality["overall"] for row in baseline),
            "selected_exact": sum(row.quality["overall"] for row in selected),
        },
        "failures": failures,
        "results": [row.public_dict() for row in results],
    }
    (OUT_DIR / "results.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "decision": payload["decision"],
                "aggregate": payload["aggregate"],
                "quality": payload["quality"],
                "failures": failures,
            },
            indent=2,
            default=str,
        )
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--cases-per-class", type=int, default=4)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260804)
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--approve-reviewed-macro", action="store_true")
    args = parser.parse_args(argv)
    if args.cases_per_class < 1:
        parser.error("--cases-per-class must be positive")
    if args.concurrency < 1:
        parser.error("--concurrency must be positive")
    return args


def main(argv: Sequence[str] | None = None) -> None:
    asyncio.run(async_main(parse_args(argv)))


if __name__ == "__main__":
    main()
