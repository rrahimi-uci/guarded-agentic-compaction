#!/usr/bin/env python3
"""Fresh paired live comparison: guarded composite versus hand-written macro."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import platform
import sys
from collections import Counter
from datetime import UTC, datetime
from importlib.metadata import version
from itertools import cycle
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "paper" / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import github_live_study as fixed  # noqa: E402
import github_natural_workflow_study as natural  # noqa: E402
import validate_guarded_composite as validation  # noqa: E402
from agent_compaction.capture.agents_sdk import AgentsTraceProcessor  # noqa: E402


OUT_DIR = ROOT / "paper/results/gcs_live"


def _excluded_numbers() -> set[int]:
    excluded: set[int] = set()
    paths = (
        ROOT / "paper/results/github_natural_replication/discovery_checkpoint.json",
        ROOT / "paper/results/github_natural_replication/results.json",
        ROOT / "paper/results/github_natural_live/results.json",
        ROOT / "paper/results/portfolio_live/results.json",
        ROOT / "paper/results/github_live/results.json",
        OUT_DIR / "results.json",
        OUT_DIR / "smoke.json",
    )
    for path in paths:
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload.get("results", ()):
            if isinstance(row, dict) and "issue_number" in row:
                excluded.add(int(row["issue_number"]))
        selection = payload.get("selection", {})
        excluded.update(int(value) for value in selection.get("discovery_issue_numbers", ()))
        excluded.update(int(value) for value in selection.get("smoke_issue_numbers", ()))
        excluded.update(
            int(row["issue_number"])
            for row in selection.get("test", ())
            if isinstance(row, dict) and "issue_number" in row
        )
    return excluded


def _scenario(number: int, store: dict[int, dict[str, Any]]) -> fixed.Scenario:
    item = store[number]
    return fixed.Scenario(
        issue_number=number,
        category=fixed.category_for(item["labels"]),
        labels=tuple(item["labels"]),
        html_url=item["html_url"],
        day=item["day"],
        state=item["state"],
    )


def _select(
    store: dict[int, dict[str, Any]],
    *,
    count: int,
    seed: int,
    excluded: set[int],
    registry: Any,
    catalog: Any,
    artifact_manifest: Any,
    continuation_manifest: Any,
) -> tuple[list[fixed.Scenario], dict[str, Any]]:
    # Eligibility is checked through the exact runtime path before the paid cohort
    # is frozen; no answer or provider outcome is observed during selection.
    from agent_compaction.runtime.dispatch import DispatchMode, Dispatcher
    from agent_compaction.runtime.runner import CompactingRunner

    ranked = sorted(
        (
            number
            for number, item in store.items()
            if number not in excluded and len(item["body"].strip()) >= 80
        ),
        key=lambda number: hashlib.sha256(f"{seed}:gcs-live:{number}".encode()).hexdigest(),
    )
    selected: list[fixed.Scenario] = []
    rejected = Counter()
    for number in ranked:
        runner = CompactingRunner(
            dispatcher=Dispatcher(registry=registry, catalog=catalog, mode=DispatchMode.LIVE),
            catalog=catalog,
            manifest=artifact_manifest,
        )
        result = runner.execute_pre_model(
            {"issue_number": number},
            executor=lambda tool, values, _store=store: validation.execute_snapshot(
                _store, tool, values
            ),
            day=store[number]["day"],
            continuation_compatibility_key=continuation_manifest.compatibility_key(),
        )
        if not result.compacted:
            rejected.update(result.record.get("reasons") or ["not_compacted"])
            continue
        selected.append(_scenario(number, store))
        if len(selected) == count:
            break
    if len(selected) != count:
        raise RuntimeError(f"only {len(selected)} fresh runtime-eligible cases; need {count}")
    return selected, {
        "seed": seed,
        "issue_numbers": [item.issue_number for item in selected],
        "category_counts": dict(Counter(item.category for item in selected)),
        "excluded_prior_issues": len(excluded),
        "pre_provider_rejections": dict(rejected),
        "selection_uses_provider_outcomes": False,
    }


async def run(args: argparse.Namespace) -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")
    frame = pd.read_parquet(fixed.DATA_PATH)
    store, duplicates = fixed.build_store(frame)
    catalog = natural.make_catalog()
    base_tools = fixed.make_tools(store)
    macro_tools = [natural.make_bundle_tool(store)]
    base_manifest = natural.make_manifest(args.model, base_tools, catalog, "base")
    gcs_manifest = natural.make_manifest(args.model, (), catalog, "gcs")
    macro_manifest = natural.make_manifest(args.model, macro_tools, catalog, "macro")

    checkpoint = json.loads(validation.DEFAULT_CHECKPOINT.read_text(encoding="utf-8"))
    regraded = json.loads(validation.DEFAULT_REGRADED.read_text(encoding="utf-8"))
    quality_by_trace = {
        str(row["trace_id"]): dict(row["quality"])
        for row in regraded["results"]
        if row.get("condition") == "discovery"
    }
    checkpoint["results"] = [
        {**row, "quality": quality_by_trace.get(str(row["trace_id"]), row["quality"])}
        for row in checkpoint["results"]
    ]
    reconstructed = validation.reconstruct_runs(checkpoint, store=store, manifest=base_manifest)
    registry, compilation = natural.compile_artifact(
        reconstructed,
        catalog=catalog,
        manifest=base_manifest,
        train_n=16,
        dev_n=8,
        calibration_n=92,
        continuation_compatibility_key=gcs_manifest.compatibility_key(),
    )
    scenarios, selection = _select(
        store,
        count=args.cases,
        seed=args.seed,
        excluded=_excluded_numbers(),
        registry=registry,
        catalog=catalog,
        artifact_manifest=base_manifest,
        continuation_manifest=gcs_manifest,
    )

    from agents import add_trace_processor

    processor = AgentsTraceProcessor(include_sensitive_data=True, max_completed=1000)
    add_trace_processor(processor)
    results: list[Any] = []
    failures: list[dict[str, Any]] = []
    schedule: list[dict[str, Any]] = []
    orders = cycle((("gcs", "macro"), ("macro", "gcs")))
    for scenario in scenarios:
        order = next(orders)
        schedule.append({"issue_number": scenario.issue_number, "order": list(order)})
        for condition in order:
            if condition == "gcs":
                batch, errors = await natural.run_batch(
                    [scenario],
                    condition="gcs",
                    repeat=0,
                    model_name=args.model,
                    tools=(),
                    processor=processor,
                    manifest=gcs_manifest,
                    catalog=catalog,
                    store=store,
                    registry=registry,
                    concurrency=1,
                    pre_model=True,
                    artifact_manifest=base_manifest,
                    pre_model_executor=lambda tool, values, _store=store: validation.execute_snapshot(
                        _store, tool, values
                    ),
                )
            else:
                batch, errors = await natural.run_batch(
                    [scenario],
                    condition="macro",
                    repeat=0,
                    model_name=args.model,
                    tools=macro_tools,
                    processor=processor,
                    manifest=macro_manifest,
                    catalog=catalog,
                    store=store,
                    registry=None,
                    concurrency=1,
                )
            results.extend(batch)
            failures.extend(errors)

    gcs = [row for row in results if row.condition == "gcs"]
    macro = [row for row in results if row.condition == "macro"]
    comparison = fixed.paired_analysis(
        macro,
        gcs,
        baseline_label="macro",
        candidate_label="gcs",
    )
    payload = {
        "schema": "agent-compaction-gcs-live-study/v1",
        "run": {
            "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "model": args.model,
            "openai_agents_sdk": version("openai-agents"),
            "openai_python": version("openai"),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "openai_api_key_used": True,
            "secrets_serialized": False,
            "provider_backed": True,
            "real_public_records": True,
            "comparative_claim_allowed": not failures and len(gcs) == len(macro) == args.cases,
            "resolved_config": vars(args),
        },
        "source": {
            "dataset": fixed.HF_DATASET,
            "revision": fixed.HF_REVISION,
            "parquet_sha256": fixed.HF_PARQUET_SHA256,
            "raw_rows": len(frame),
            "deduplicated_non_pr_issues": len(store),
            "duplicate_issue_rows": sum(duplicates.values()),
            "discovery_checkpoint_sha256": fixed.sha256(validation.DEFAULT_CHECKPOINT),
            "regraded_results_sha256": fixed.sha256(validation.DEFAULT_REGRADED),
        },
        "selection": selection,
        "schedule": schedule,
        "compiler": compilation,
        "aggregate": fixed.aggregate_runs(results),
        "macro_vs_gcs": comparison,
        "failures": failures,
        "results": [row.public_dict() for row in results],
        "metric_definitions": {
            "gcs_tool_calls": "one exposed guarded composite; internal_tool_calls records source reads",
            "macro_tool_calls": "one provider-visible hand-written composite call",
            "requests": "native provider generation/response spans",
        },
    }
    output = OUT_DIR / ("smoke.json" if args.smoke else "results.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    registry.save(OUT_DIR / "registry")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--cases", type=int, default=12)
    parser.add_argument("--seed", type=int, default=20260804)
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    result = asyncio.run(run(parse_args()))
    print(
        json.dumps(
            {
                "run": result["run"],
                "selection": result["selection"],
                "aggregate": result["aggregate"],
                "macro_vs_gcs": result["macro_vs_gcs"],
                "failures": result["failures"],
            },
            indent=2,
            default=str,
        )
    )
