#!/usr/bin/env python3
"""Live execution of the gate-frontier pilot sealed in gate_frontier_pilot_preflight.py.

Reuses the natural-order study's machinery directly rather than reimplementing it:
``make_tools``/``make_catalog``/``build_store`` from ``github_live_study``,
``make_manifest``/``run_batch``/``grade_factual`` from ``github_natural_workflow_study``,
and the already-emitted artifact in ``paper/results/github_natural_live/registry``. No
discovery or compilation happens here -- the recurrent ``record -> labels -> comments``
program already exists and is validated; this script only runs the unchanged agent and
that existing compiled artifact against the pilot's own held-out and calibration-dev
cohorts and reports ``grade_factual`` by risk stratum.

This departs from the counterbalanced single-scenario-at-a-time schedule
``run_counterbalanced_test`` uses for the primary study in one respect, disclosed here
because it is a design simplification made before running anything, not an
after-the-fact adjustment: each condition (unchanged, compiled) runs as one concurrent
batch over all scenarios rather than interleaved per-scenario ordering. The two arms are
independent model runs graded against the same fixed source records, so per-scenario
condition order has no plausible channel to affect a factual grounding check, and batching
is materially cheaper and faster for a 90-record pilot.

Requires OPENAI_API_KEY and --approved-spend-usd. Estimated cost per
gate-frontier-pilot-protocol.md: under $10.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import sys
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import github_live_study as fixed  # noqa: E402
import github_natural_workflow_study as natural  # noqa: E402
from guarded_agentic_compaction.capture.agents_sdk import AgentsTraceProcessor  # noqa: E402
from guarded_agentic_compaction.registry.store import Registry  # noqa: E402


PREFLIGHT_PATH = ROOT / "paper" / "results" / "gate_frontier_pilot" / "preflight.json"
EXISTING_REGISTRY = ROOT / "paper" / "results" / "github_natural_live" / "registry" / "registry.json"
OUT_DIR = ROOT / "paper" / "results" / "gate_frontier_pilot"
MODEL = "gpt-5.6-luna"  # matches the existing registry's pinned manifest


def _scenario(store: dict[int, dict[str, Any]], number: int) -> fixed.Scenario:
    item = store[number]
    return fixed.Scenario(
        issue_number=number,
        category=fixed.category_for(item["labels"]),
        labels=tuple(item["labels"]),
        html_url=item["html_url"],
        day=item["day"],
        state=item["state"],
    )


def _recompute_strata(store: dict[int, dict[str, Any]], numbers: list[int]) -> dict[int, str]:
    """Recomputed from the same source rows the preflight stratified, rather than trusted
    blind -- the preflight records counts, not a number->stratum map, by design (it does
    not serialize comment text). This must produce the same stratum for every number the
    preflight selected; a test asserts that.
    """

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "gate_frontier_pilot_preflight",
        Path(__file__).with_name("gate_frontier_pilot_preflight.py"),
    )
    preflight_module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(preflight_module)

    result: dict[int, str] = {}
    for number in numbers:
        result[number] = preflight_module._risk_stratum(store[number]["comments"])
    return result


async def async_main(args: argparse.Namespace) -> None:
    load_dotenv(ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set in .env or the environment")
    if args.approved_spend_usd <= 0:
        raise RuntimeError("--approved-spend-usd must be a positive explicit spend ceiling")
    if not EXISTING_REGISTRY.is_file():
        raise SystemExit(f"expected existing registry at {EXISTING_REGISTRY}")

    preflight = json.loads(PREFLIGHT_PATH.read_text())
    cohort = preflight["cohort"]
    held_out_numbers: list[int] = cohort["held_out_record_numbers"]
    dev_numbers: list[int] = cohort["calibration_dev_record_numbers"]
    all_numbers = held_out_numbers + dev_numbers
    if args.only_numbers:
        wanted = set(args.only_numbers)
        all_numbers = [n for n in all_numbers if n in wanted]
    if args.limit:
        all_numbers = all_numbers[: args.limit]
    held_out_numbers = [n for n in held_out_numbers if n in all_numbers]
    dev_numbers = [n for n in dev_numbers if n in all_numbers]

    frame = pd.read_parquet(fixed.DATA_PATH)
    store, _duplicates = fixed.build_store(frame)
    missing = [n for n in all_numbers if n not in store]
    if missing:
        raise RuntimeError(f"{len(missing)} sealed pilot records are missing from the "
                            f"rebuilt store (deduplication mismatch?): {missing[:10]}")

    strata = _recompute_strata(store, all_numbers)
    scenarios = [_scenario(store, number) for number in all_numbers]

    tools = fixed.make_tools(store)
    catalog = natural.make_catalog()
    unchanged_manifest = natural.make_manifest(MODEL, tools, catalog, "unchanged")
    compiled_manifest = natural.make_manifest(MODEL, tools, catalog, "compiled")
    registry = Registry.load(EXISTING_REGISTRY)

    from agents import add_trace_processor

    processor = AgentsTraceProcessor(include_sensitive_data=True, max_completed=1000)
    add_trace_processor(processor)

    started = time.perf_counter()
    unchanged_results, unchanged_failures = await natural.run_batch(
        scenarios, condition="unchanged", repeat=0, model_name=MODEL, tools=tools,
        processor=processor, manifest=unchanged_manifest, catalog=catalog, store=store,
        registry=None, concurrency=args.concurrency,
    )
    compiled_results, compiled_failures = await natural.run_batch(
        scenarios, condition="compiled", repeat=0, model_name=MODEL, tools=tools,
        processor=processor, manifest=compiled_manifest, catalog=catalog, store=store,
        registry=registry, concurrency=args.concurrency,
    )
    elapsed = time.perf_counter() - started

    def _graded(results: list[fixed.RunResult]) -> list[dict[str, Any]]:
        rows = []
        for run in results:
            checks = natural.grade_factual(
                fixed.Scenario(
                    issue_number=run.issue_number,
                    category=fixed.category_for(store[run.issue_number]["labels"]),
                    labels=tuple(store[run.issue_number]["labels"]),
                    html_url=store[run.issue_number]["html_url"],
                    day=store[run.issue_number]["day"],
                    state=store[run.issue_number]["state"],
                ),
                run.answer,
                run.tool_sequence,
                store,
            )
            split = "held_out" if run.issue_number in held_out_numbers else "calibration_dev"
            rows.append({
                "issue_number": run.issue_number,
                "condition": run.condition,
                "stratum": strata[run.issue_number],
                "split": split,
                "comment_evidence": run.answer.get("comment_evidence"),
                **checks,
            })
        return rows

    graded = _graded(unchanged_results) + _graded(compiled_results)

    by_condition_stratum: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for row in graded:
        key = (row["condition"], row["stratum"])
        by_condition_stratum[key]["n"] += 1
        by_condition_stratum[key]["comment_grounded"] += int(row["comment_grounded"])
        by_condition_stratum[key]["overall_pass"] += int(row["overall"])

    summary_rows = []
    for (condition, stratum), counts in sorted(by_condition_stratum.items()):
        n = counts["n"]
        summary_rows.append({
            "condition": condition,
            "stratum": stratum,
            "n": n,
            "comment_grounded_rate": counts["comment_grounded"] / n if n else None,
            "comment_grounded_violations": n - counts["comment_grounded"],
            "overall_pass_rate": counts["overall_pass"] / n if n else None,
        })

    payload = {
        "schema": "gac-gate-frontier-pilot-results/v1",
        "run": {
            "script": "paper/scripts/gate_frontier_pilot_study.py",
            "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "model": MODEL,
            "openai_agents_sdk": version("openai-agents"),
            "openai_python": version("openai"),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "openai_api_key_used": True,
            "secrets_serialized": False,
            "approved_spend_ceiling_usd": args.approved_spend_usd,
            "concurrency": args.concurrency,
            "limit": args.limit,
            "elapsed_seconds": elapsed,
            "existing_registry": str(EXISTING_REGISTRY.relative_to(ROOT)),
            "preflight": str(PREFLIGHT_PATH.relative_to(ROOT)),
        },
        "scenario_counts": {
            "requested": len(all_numbers),
            "held_out": len(held_out_numbers),
            "calibration_dev": len(dev_numbers),
        },
        "failures": {"unchanged": unchanged_failures, "compiled": compiled_failures},
        "summary_by_condition_and_stratum": summary_rows,
        "graded_results": graded,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / args.out_name
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")

    print(f"wrote {out_path.relative_to(ROOT)}")
    print(f"  elapsed {elapsed:.1f}s, {len(unchanged_failures)} unchanged failures, "
          f"{len(compiled_failures)} compiled failures")
    for row in summary_rows:
        print(f"    {row['condition']:10s} {row['stratum']:14s} n={row['n']:3d} "
              f"comment_grounded={row['comment_grounded_rate']:.3f} "
              f"(violations={row['comment_grounded_violations']}) "
              f"overall_pass={row['overall_pass_rate']:.3f}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--approved-spend-usd", type=float, required=True)
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--limit", type=int, default=None,
                         help="smoke-test switch: only the first N sealed records")
    parser.add_argument("--only-numbers", type=int, nargs="+", default=None,
                         help="diagnostic switch: rerun only these specific issue numbers")
    parser.add_argument("--out-name", default="results.json")
    return parser.parse_args()


def main() -> None:
    asyncio.run(async_main(parse_args()))


if __name__ == "__main__":
    main()
