#!/usr/bin/env python3
"""Real-provider head-to-head: GEPA, GCS, their composition, and a fair macro.

The study uses pinned public GitHub issue records and the OpenAI Agents SDK for
every task rollout.  GEPA 0.1.4 optimizes only the workflow's operational
strategy sentence; the safety and factual-output contract remains fixed.  The
manual macro is executed before the first provider request through an
independent, hand-authored guarded program, so it receives the same execution
opportunity as GCS without inheriting compiler evidence.

Optimization, validation, and final test cases are selected before any provider
outcome and are disjoint from all earlier live cohorts.  GEPA optimization spend
is reported separately from deployment spend.  ``--smoke`` performs real calls
but never authorizes a paper comparison claim.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import platform
import sys
import threading
import time
from collections import Counter
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Sequence

import pandas as pd
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import github_gcs_live_study as gcs_study  # noqa: E402
import github_live_study as fixed  # noqa: E402
import github_natural_workflow_study as natural  # noqa: E402
import validate_guarded_composite as validation  # noqa: E402
from guarded_agentic_compaction.capture.agents_sdk import AgentsTraceProcessor  # noqa: E402
from guarded_agentic_compaction.grc.composite import synthesize_composite  # noqa: E402
from guarded_agentic_compaction.grc.dsl import Const, Expr  # noqa: E402
from guarded_agentic_compaction.grc.program import CallStep, Program  # noqa: E402
from guarded_agentic_compaction.optimization.gepa import (  # noqa: E402
    GepaEvaluation,
    GepaPromptConfig,
    GepaPromptOptimizer,
)
from guarded_agentic_compaction.runtime.dispatch import DispatchMode, Dispatcher  # noqa: E402
from guarded_agentic_compaction.runtime.manual import ManualPreModelPlan, ManualPreModelRunner  # noqa: E402
from guarded_agentic_compaction.runtime.runner import CompactingRunner  # noqa: E402
from guarded_agentic_compaction.schema.artifacts import (  # noqa: E402
    GuardClause,
    HardGuard,
    Hull,
    OutputClause,
    Verifier,
)
from demos.live_runtime import MODEL_PRICES  # noqa: E402


OUT_DIR = ROOT / "paper/results/optimizer_head_to_head"
STRATEGY_SENTENCE = (
    "Use the available read-only evidence tools as needed and choose the calls and their order\n"
    "yourself."
)
CONDITIONS = ("baseline", "gepa", "gcs", "gcs_gepa", "manual_pre_model")


def prompt_for_strategy(strategy: str) -> str:
    if STRATEGY_SENTENCE not in natural.NATURAL_PROMPT:
        raise RuntimeError("the frozen natural prompt no longer contains its strategy sentence")
    return natural.NATURAL_PROMPT.replace(STRATEGY_SENTENCE, strategy.strip(), 1)


def _strategy_error(strategy: str) -> str | None:
    value = " ".join(strategy.split())
    if not value:
        return "strategy is empty"
    if len(strategy) > 1_200:
        return "strategy exceeds 1,200 characters"
    lowered = value.casefold()
    forbidden = (
        "ignore previous",
        "ignore the previous",
        "disregard previous",
        "override the contract",
        "override safety",
        "change the output schema",
        "reveal the system prompt",
    )
    if any(phrase in lowered for phrase in forbidden):
        return "strategy contains a control-override phrase"
    return None


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


def _prior_numbers() -> set[int]:
    excluded = gcs_study._excluded_numbers()
    for path in (OUT_DIR / "results.json", OUT_DIR / "smoke.json"):
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        selection = payload.get("selection", {})
        for role in ("optimization_train", "optimization_validation", "test"):
            excluded.update(int(value) for value in selection.get(role, ()))
        for row in payload.get("deployment_results", ()):
            if isinstance(row, dict) and "issue_number" in row:
                excluded.add(int(row["issue_number"]))
    return excluded


def _runtime_eligible(
    number: int,
    *,
    store: dict[int, dict[str, Any]],
    registry: Any,
    catalog: Any,
    source_manifest: Any,
    continuation_manifest: Any,
) -> tuple[bool, tuple[str, ...]]:
    runner = CompactingRunner(
        dispatcher=Dispatcher(registry=registry, catalog=catalog, mode=DispatchMode.LIVE),
        catalog=catalog,
        manifest=source_manifest,
    )
    result = runner.execute_pre_model(
        {"issue_number": number},
        executor=lambda tool, values: validation.execute_snapshot(store, tool, values),
        day=store[number]["day"],
        continuation_compatibility_key=continuation_manifest.compatibility_key(),
    )
    return result.compacted, tuple(result.record.get("reasons") or ())


def select_fresh_splits(
    store: dict[int, dict[str, Any]],
    *,
    train_n: int,
    val_n: int,
    test_n: int,
    seed: int,
    excluded: set[int],
    registry: Any,
    catalog: Any,
    source_manifest: Any,
    continuation_manifest: Any,
) -> tuple[list[fixed.Scenario], list[fixed.Scenario], list[fixed.Scenario], dict[str, Any]]:
    required = train_n + val_n + test_n
    category_order = ("bug", "enhancement", "question", "other")
    role_sizes = (train_n, val_n, test_n)
    ranked = sorted(
        (
            number
            for number, item in store.items()
            if number not in excluded and len(item["body"].strip()) >= 80
        ),
        key=lambda number: hashlib.sha256(
            f"{seed}:optimizer-head-to-head:{number}".encode()
        ).hexdigest(),
    )
    raw_category_counts = Counter(fixed.category_for(store[number]["labels"]) for number in ranked)
    categories = tuple(category for category in category_order if raw_category_counts[category])
    unavailable_categories = [category for category in category_order if not raw_category_counts[category]]
    if not categories:
        raise RuntimeError("no fresh category is available after the exclusion boundary")
    category_demand = Counter(
        category
        for size in role_sizes
        for category in (categories[index % len(categories)] for index in range(size))
    )
    admitted_by_category: dict[str, list[int]] = {category: [] for category in categories}
    rejected = Counter()
    for number in ranked:
        ok, reasons = _runtime_eligible(
            number,
            store=store,
            registry=registry,
            catalog=catalog,
            source_manifest=source_manifest,
            continuation_manifest=continuation_manifest,
        )
        if not ok:
            rejected.update(reasons or ("not_compacted",))
            continue
        category = fixed.category_for(store[number]["labels"])
        admitted_by_category[category].append(number)
        if all(
            len(admitted_by_category[category]) >= category_demand[category]
            for category in categories
        ):
            break
    short = {
        category: category_demand[category] - len(admitted_by_category[category])
        for category in categories
        if len(admitted_by_category[category]) < category_demand[category]
    }
    if short:
        raise RuntimeError(f"insufficient category-balanced runtime-eligible cases: {short}")

    def take(size: int) -> list[int]:
        values = []
        for index in range(size):
            category = categories[index % len(categories)]
            values.append(admitted_by_category[category].pop(0))
        return values

    train_ids = take(train_n)
    val_ids = take(val_n)
    test_ids = take(test_n)
    if set(train_ids) & set(val_ids) or set(train_ids + val_ids) & set(test_ids):
        raise AssertionError("optimizer split construction leaked examples")
    train_scenarios = [_scenario(number, store) for number in train_ids]
    val_scenarios = [_scenario(number, store) for number in val_ids]
    test_scenarios = [_scenario(number, store) for number in test_ids]
    selection = {
        "seed": seed,
        "optimization_train": train_ids,
        "optimization_validation": val_ids,
        "test": test_ids,
        "test_frozen_before_optimization": True,
        "selection_uses_provider_outcomes": False,
        "excluded_prior_issues": len(excluded),
        "pre_provider_rejections": dict(rejected),
        "category_counts": {
            role: dict(Counter(item.category for item in values))
            for role, values in {
                "optimization_train": train_scenarios,
                "optimization_validation": val_scenarios,
                "test": test_scenarios,
            }.items()
        },
        "category_balance_rule": "available categories in fixed bug, enhancement, question, other order; round-robin within each split",
        "available_categories": list(categories),
        "unavailable_categories_after_exclusions": unavailable_categories,
        "fresh_raw_category_counts": dict(raw_category_counts),
    }
    assert len(train_ids) + len(val_ids) + len(test_ids) == required
    return train_scenarios, val_scenarios, test_scenarios, selection


def make_manual_plan(
    *,
    catalog: Any,
    source_manifest: Any,
    continuation_manifest: Any,
) -> ManualPreModelPlan:
    program = Program(
        theta=("issue_number",),
        steps=[
            CallStep(
                var="record",
                tool="issue_get_record",
                args={"issue_number": Expr("z.issue_number", ())},
            ),
            CallStep(
                var="labels",
                tool="issue_get_labels",
                args={"issue_number": Expr("z.issue_number", ())},
            ),
            CallStep(
                var="comments",
                tool="issue_get_comments",
                args={
                    "issue_number": Expr("z.issue_number", ()),
                    "limit": Const(3),
                },
            ),
        ],
        outputs={
            "record": Expr("record", ()),
            "labels": Expr("labels", ()),
            "comments": Expr("comments", ()),
        },
        removed_requests=3,
    )
    program = synthesize_composite(
        program,
        catalog,
        name="manual_issue_evidence_bundle",
        description="Hand-authored guarded evidence plan for the public issue task.",
        projection={
            "issue_number": "tool:issue_get_record::issue_number",
            "title": "tool:issue_get_record::content.title",
            "state": "tool:issue_get_record::state",
            "body_excerpt": "tool:issue_get_record::content.body_excerpt",
            "labels": "tool:issue_get_labels::names",
            "comments": "tool:issue_get_comments::thread.items",
            "source_revision": "tool:issue_get_record::source_revision",
        },
        pre_model=True,
        continuation_compatibility_key=continuation_manifest.compatibility_key(),
    )
    pins = {
        "model": source_manifest.model,
        "prompt_hash": source_manifest.prompt_hash,
        "tools_hash": source_manifest.tools_hash,
        "policy_hash": source_manifest.policy_hash,
        "guardrail_hash": source_manifest.guardrail_hash,
        "effect_catalog_version": source_manifest.effect_catalog_version,
        "entry_contract_version": source_manifest.entry_contract_version,
    }
    return ManualPreModelPlan(
        name="paper-github-manual-pre-model-v1",
        program=program,
        source_compatibility_key=source_manifest.compatibility_key(),
        guard=HardGuard(
            manifest_pins=pins,
            clauses=[GuardClause("z.issue_number", "int", Hull("interval", low=1))],
            allowed_effects=("READ_LOCAL",),
        ),
        verifier=Verifier(
            clauses=[
                OutputClause("record", "dict", provenance=("issue_get_record",)),
                OutputClause("labels", "dict", provenance=("issue_get_labels",)),
                OutputClause("comments", "dict", provenance=("issue_get_comments",)),
            ],
            allowed_effects=("READ_LOCAL",),
            call_counts=(3,),
        ),
        owner="paper-optimizer-head-to-head",
        approved_by="paper-protocol-lab-only-not-production",
    )


def verify_pre_model_parity(
    scenarios: Sequence[fixed.Scenario],
    *,
    store: dict[int, dict[str, Any]],
    registry: Any,
    manual_plan: ManualPreModelPlan,
    catalog: Any,
    source_manifest: Any,
    continuation_manifest: Any,
) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        executor = lambda tool, values: validation.execute_snapshot(store, tool, values)
        compiled = CompactingRunner(
            Dispatcher(registry=registry, catalog=catalog, mode=DispatchMode.LIVE),
            catalog,
            source_manifest,
        ).execute_pre_model(
            {"issue_number": scenario.issue_number},
            executor=executor,
            day=scenario.day,
            continuation_compatibility_key=continuation_manifest.compatibility_key(),
        )
        manual = ManualPreModelRunner(
            manual_plan, catalog, source_manifest
        ).execute_pre_model(
            {"issue_number": scenario.issue_number},
            executor=executor,
            day=scenario.day,
            continuation_compatibility_key=continuation_manifest.compatibility_key(),
        )
        same = (
            compiled.compacted
            and manual.compacted
            and compiled.observations[0].result == manual.observations[0].result
        )
        row = {
            "issue_number": scenario.issue_number,
            "same_projected_evidence": same,
            "gcs_internal_calls": compiled.record.get("n_calls"),
            "manual_internal_calls": manual.record.get("n_calls"),
        }
        rows.append(row)
        if not same:
            mismatches.append(row)
    if mismatches:
        raise RuntimeError(f"manual/GCS provider-free parity failed on {len(mismatches)} cases")
    digest = hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "cases": len(rows),
        "exact_projection_matches": len(rows),
        "mismatches": mismatches,
        "rows_digest": digest,
        "provider_calls": 0,
    }


class OpenAIReflectionLM:
    """Synchronous, cost-accounted reflection callable for official GEPA."""

    def __init__(self, model: str) -> None:
        from openai import OpenAI

        self.model = model
        self.client = OpenAI()
        self.calls = 0
        self.input_tokens = 0
        self.cached_input_tokens = 0
        self.output_tokens = 0
        self.latency_ms = 0.0
        self._lock = threading.Lock()

    def __call__(self, prompt: str) -> str:
        started = time.perf_counter()
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            max_output_tokens=1_600,
            reasoning={"effort": "low"},
            text={"verbosity": "low"},
            store=False,
        )
        elapsed = (time.perf_counter() - started) * 1000.0
        output = str(response.output_text or "").strip()
        if not output:
            raise RuntimeError("GEPA reflection model returned no text")
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        details = getattr(usage, "input_tokens_details", None)
        cached_tokens = int(getattr(details, "cached_tokens", 0) or 0)
        with self._lock:
            self.calls += 1
            self.input_tokens += input_tokens
            self.cached_input_tokens += cached_tokens
            self.output_tokens += output_tokens
            self.latency_ms += elapsed
        return output

    def metrics(self) -> dict[str, Any]:
        price = MODEL_PRICES.get(self.model)
        estimated_cost = None
        if price is not None:
            ordinary = max(0, self.input_tokens - self.cached_input_tokens)
            estimated_cost = (
                ordinary * price.input
                + self.cached_input_tokens * price.cached_input
                + self.output_tokens * price.output
            ) / 1_000_000
        return {
            "model": self.model,
            "calls": self.calls,
            "input_tokens": self.input_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
            "latency_ms": round(self.latency_ms, 3),
            "estimated_cost_usd": (
                round(estimated_cost, 8) if estimated_cost is not None else None
            ),
        }


def _optimization_score(run: Any) -> float:
    quality = run.quality
    metrics = run.metrics
    # Exact task success dominates every possible efficiency term. Among exact
    # candidates, provider turns and then token volume determine the direction.
    return (
        1_000.0 * float(quality["overall"])
        + 100.0 * float(quality["score"])
        - 5.0 * float(metrics["requests"])
        - float(metrics["tool_calls"])
        - float(metrics["total_tokens"]) / 10_000.0
    )


def _optimization_feedback(run: Any, *, strategy: str) -> str:
    failed = [
        name
        for name, value in run.quality.items()
        if name.endswith("_correct") or name in {"comment_grounded", "trace_valid"}
        if value is False
    ]
    return (
        "The candidate replaces only the operational strategy sentence; the fixed safety and "
        "factual-output contract remains unchanged. "
        f"Exact task success={run.quality['overall']}; failed checks={failed or ['none']}; "
        f"tool sequence={run.tool_sequence}; provider requests={run.metrics['requests']}; "
        f"tool calls={run.metrics['tool_calls']}; total tokens={run.metrics['total_tokens']}. "
        "Preserve exact factual success first. Then reduce unnecessary model turns or tokens. "
        f"Current strategy length={len(strategy)}."
    )


def optimization_totals(rows: Sequence[Any], reflection: dict[str, Any]) -> dict[str, Any]:
    task_requests = sum(int(row.metrics["requests"]) for row in rows)
    task_input = sum(int(row.metrics["input_tokens"]) for row in rows)
    task_output = sum(int(row.metrics["output_tokens"]) for row in rows)
    task_cost = sum(float(row.metrics["estimated_cost_usd"] or 0.0) for row in rows)
    reflection_cost = float(reflection.get("estimated_cost_usd") or 0.0)
    return {
        "task_metric_calls": len(rows),
        "task_provider_requests": task_requests,
        "task_input_tokens": task_input,
        "task_output_tokens": task_output,
        "task_total_tokens": task_input + task_output,
        "task_wall_latency_ms": round(
            sum(float(row.metrics["wall_latency_ms"]) for row in rows), 3
        ),
        "task_estimated_cost_usd": round(task_cost, 8),
        "reflection_calls": int(reflection.get("calls", 0)),
        "reflection_total_tokens": int(reflection.get("total_tokens", 0)),
        "reflection_estimated_cost_usd": (
            round(reflection_cost, 8)
            if reflection.get("estimated_cost_usd") is not None
            else None
        ),
        "combined_provider_requests": task_requests + int(reflection.get("calls", 0)),
        "combined_total_tokens": task_input
        + task_output
        + int(reflection.get("total_tokens", 0)),
        "combined_estimated_cost_usd": round(task_cost + reflection_cost, 8),
        "excluded_from_deployment_metrics": True,
    }


def latency_measurement_validation(rows: Sequence[Any]) -> dict[str, Any]:
    invalid = []
    for row in rows:
        wall = float(row.metrics.get("wall_latency_ms") or 0.0)
        provider = float(row.metrics.get("provider_response_latency_ms") or 0.0)
        if provider < 0 or provider > wall + 250.0:
            invalid.append(
                {
                    "condition": row.condition,
                    "issue_number": row.issue_number,
                    "wall_latency_ms": wall,
                    "provider_response_latency_ms": provider,
                }
            )
    return {
        "wall_latency_source": "host monotonic clock around the complete Runner call",
        "provider_span_latency_source": "Agents SDK wall-clock span timestamps",
        "provider_span_latency_valid": not invalid,
        "provider_span_latency_outliers": invalid,
        "provider_span_latency_excluded_from_comparisons": bool(invalid),
        "validation_rule": "provider response sum must be nonnegative and <= wall latency + 250 ms",
    }


def paired_with_measurement_guard(
    baseline: Sequence[Any],
    candidate: Sequence[Any],
    *,
    baseline_label: str,
    candidate_label: str,
) -> dict[str, Any]:
    result = fixed.paired_analysis(
        baseline,
        candidate,
        baseline_label=baseline_label,
        candidate_label=candidate_label,
    )
    validation_record = latency_measurement_validation([*baseline, *candidate])
    if not validation_record["provider_span_latency_valid"]:
        excluded = result["metrics"].pop("provider_response_latency_ms", None)
        result.setdefault("excluded_metrics", {})["provider_response_latency_ms"] = {
            "reason": "span timestamp failed the wall-latency consistency check",
            "outliers": validation_record["provider_span_latency_outliers"],
            "unfiltered_analysis": excluded,
        }
    return result


def regrade_saved_payload(path: Path) -> dict[str, Any]:
    """Recompute task quality after an oracle fix without making provider calls."""

    path = path.resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "agent-compaction-optimizer-head-to-head/v1":
        raise RuntimeError("unsupported optimizer head-to-head result schema")
    before = fixed.sha256(path)
    frame = pd.read_parquet(fixed.DATA_PATH)
    store, _ = fixed.build_store(frame)
    runs: list[Any] = []
    changed = 0
    for row in payload.get("deployment_results", ()):
        number = int(row["issue_number"])
        corrected = natural.grade_factual(
            _scenario(number, store),
            dict(row["answer"]),
            list(row["tool_sequence"]),
            store,
        )
        prior = dict(row["quality"])
        if prior != corrected:
            row.setdefault("online_quality", prior)
            row["quality"] = corrected
            changed += 1
        runs.append(
            SimpleNamespace(
                condition=str(row["condition"]),
                repeat=int(row["repeat"]),
                issue_number=number,
                metrics=dict(row["metrics"]),
                quality=dict(row["quality"]),
                answer=dict(row["answer"]),
                tool_sequence=list(row["tool_sequence"]),
                tool_arguments=[dict(value) for value in row["tool_arguments"]],
            )
        )
    grouped = {
        condition: [row for row in runs if row.condition == condition]
        for condition in CONDITIONS
    }
    comparisons = {
        f"baseline_vs_{condition}": paired_with_measurement_guard(
            grouped["baseline"],
            grouped[condition],
            baseline_label="baseline",
            candidate_label=condition,
        )
        for condition in CONDITIONS
        if condition != "baseline"
    }
    comparisons["manual_pre_model_vs_gcs"] = paired_with_measurement_guard(
        grouped["manual_pre_model"],
        grouped["gcs"],
        baseline_label="manual_pre_model",
        candidate_label="gcs",
    )
    comparisons["gepa_vs_gcs_gepa"] = paired_with_measurement_guard(
        grouped["gepa"],
        grouped["gcs_gepa"],
        baseline_label="gepa",
        candidate_label="gcs_gepa",
    )
    payload["aggregate"] = fixed.aggregate_runs(runs)
    payload["comparisons"] = comparisons
    payload["measurement_validation"] = latency_measurement_validation(runs)
    optimization_rows = [
        SimpleNamespace(metrics=dict(row["metrics"]))
        for row in payload.get("optimization", {}).get("task_results", ())
    ]
    if optimization_rows:
        payload["optimization"]["accounting"] = optimization_totals(
            optimization_rows,
            dict(payload["optimization"]["reflection"]),
        )
    payload["oracle_revision"] = {
        "schema": "agent-compaction-optimizer-oracle-regrade/v1",
        "original_results_sha256": payload.get("oracle_revision", {}).get(
            "original_results_sha256", before
        ),
        "changed_rows": changed,
        "provider_calls_rerun": False,
        "provider_outputs_changed": False,
        "metrics_changed": False,
        "episode_digest_retains_online_trace_label": bool(changed),
        "reason": (
            "the guarded manual pre-model interface was added to the task trace allowlist"
            if changed
            else "recomputed derived comparisons, optimizer accounting, and measurement validation"
        ),
    }
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return payload


async def run(args: argparse.Namespace) -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")
    output = OUT_DIR / ("smoke.json" if args.smoke else "results.json")
    if output.exists() and not args.force:
        raise RuntimeError(f"refusing to overwrite existing evidence: {output}; pass --force")

    frame = pd.read_parquet(fixed.DATA_PATH)
    store, duplicates = fixed.build_store(frame)
    catalog = natural.make_catalog()
    base_tools = fixed.make_tools(store)
    base_manifest = natural.make_manifest(args.model, base_tools, catalog, "optimizer-source")
    gcs_manifest = natural.make_manifest(args.model, (), catalog, "gcs")

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
    gcs_registry, gcs_compilation = natural.compile_artifact(
        reconstructed,
        catalog=catalog,
        manifest=base_manifest,
        train_n=16,
        dev_n=8,
        calibration_n=92,
        continuation_compatibility_key=gcs_manifest.compatibility_key(),
    )

    train, val, test, selection = select_fresh_splits(
        store,
        train_n=args.train_cases,
        val_n=args.val_cases,
        test_n=args.test_cases,
        seed=args.seed,
        excluded=_prior_numbers(),
        registry=gcs_registry,
        catalog=catalog,
        source_manifest=base_manifest,
        continuation_manifest=gcs_manifest,
    )
    manual_plan = make_manual_plan(
        catalog=catalog,
        source_manifest=base_manifest,
        continuation_manifest=gcs_manifest,
    )
    parity = verify_pre_model_parity(
        [*train, *val, *test],
        store=store,
        registry=gcs_registry,
        manual_plan=manual_plan,
        catalog=catalog,
        source_manifest=base_manifest,
        continuation_manifest=gcs_manifest,
    )
    preflight = {
        "schema": "agent-compaction-optimizer-head-to-head-preflight/v1",
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "selection": selection,
        "manual_plan_id": manual_plan.plan_id,
        "provider_free_parity": parity,
        "source_revision": fixed.HF_REVISION,
        "parquet_sha256": fixed.HF_PARQUET_SHA256,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "preflight.json").write_text(
        json.dumps(preflight, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    from agents import add_trace_processor

    processor = AgentsTraceProcessor(include_sensitive_data=True, max_completed=4_000)
    add_trace_processor(processor)
    optimization_runs: list[Any] = []
    optimization_counter = 0

    def evaluate_strategy(strategy: str, scenario: fixed.Scenario) -> GepaEvaluation:
        nonlocal optimization_counter
        invalid = _strategy_error(strategy)
        if invalid is not None:
            return GepaEvaluation(
                -1_000_000.0,
                f"Candidate rejected before provider execution: {invalid}.",
                {"rejected": invalid, "provider_requests": 0},
            )
        optimization_counter += 1
        candidate_digest = hashlib.sha256(strategy.encode()).hexdigest()[:10]
        condition = f"gepa-opt-{optimization_counter:03d}-{candidate_digest}"
        instructions = prompt_for_strategy(strategy)
        manifest = natural.make_manifest(
            args.model,
            base_tools,
            catalog,
            condition,
            instructions=instructions,
        )
        rows, failures = asyncio.run(
            natural.run_batch(
                [scenario],
                condition=condition,
                repeat=0,
                model_name=args.model,
                tools=base_tools,
                processor=processor,
                manifest=manifest,
                catalog=catalog,
                store=store,
                registry=None,
                concurrency=1,
                instructions=instructions,
            )
        )
        if failures or len(rows) != 1:
            detail = failures[0]["error"].split(":", 1)[0] if failures else "missing_result"
            raise RuntimeError(f"task evaluation failed: {detail}")
        task_run = rows[0]
        optimization_runs.append(task_run)
        return GepaEvaluation(
            _optimization_score(task_run),
            _optimization_feedback(task_run, strategy=strategy),
            {
                "overall": task_run.quality["overall"],
                "factual_score": task_run.quality["score"],
                "provider_requests": task_run.metrics["requests"],
                "tool_calls": task_run.metrics["tool_calls"],
                "total_tokens": task_run.metrics["total_tokens"],
                "estimated_cost_usd": task_run.metrics["estimated_cost_usd"],
            },
        )

    reflection = OpenAIReflectionLM(args.reflection_model or args.model)
    optimizer = GepaPromptOptimizer(
        GepaPromptConfig(
            max_metric_calls=args.max_metric_calls,
            max_candidate_proposals=args.max_proposals,
            reflection_minibatch_size=min(args.reflection_minibatch, args.train_cases),
            seed=args.seed,
            max_candidate_chars=1_200,
            run_dir=OUT_DIR / ("gepa_smoke" if args.smoke else "gepa_run"),
            require_disjoint_splits=True,
            record_feedback=False,
        )
    )
    gepa_result = await asyncio.to_thread(
        optimizer.optimize,
        seed_prompt=STRATEGY_SENTENCE,
        evaluator=evaluate_strategy,
        trainset=train,
        valset=val,
        reflection_lm=reflection,
        example_id=lambda scenario: str(scenario.issue_number),
    )
    optimized_strategy = gepa_result.best_prompt
    optimized_prompt = prompt_for_strategy(optimized_strategy)
    optimized_gcs_manifest = natural.make_manifest(
        args.model,
        (),
        catalog,
        "gcs-gepa",
        instructions=optimized_prompt,
    )
    optimized_gcs_registry, optimized_gcs_compilation = natural.compile_artifact(
        reconstructed,
        catalog=catalog,
        manifest=base_manifest,
        train_n=16,
        dev_n=8,
        calibration_n=92,
        continuation_compatibility_key=optimized_gcs_manifest.compatibility_key(),
    )

    deployment_results: list[Any] = []
    failures: list[dict[str, Any]] = []
    schedule: list[dict[str, Any]] = []
    for index, scenario in enumerate(test):
        order = CONDITIONS[index % len(CONDITIONS) :] + CONDITIONS[: index % len(CONDITIONS)]
        schedule.append({"issue_number": scenario.issue_number, "order": list(order)})
        for condition in order:
            if condition == "baseline":
                tools = base_tools
                manifest = base_manifest
                instructions = natural.NATURAL_PROMPT
                kwargs: dict[str, Any] = {}
            elif condition == "gepa":
                tools = base_tools
                instructions = optimized_prompt
                manifest = natural.make_manifest(
                    args.model, tools, catalog, "gepa", instructions=instructions
                )
                kwargs = {}
            elif condition == "gcs":
                tools = ()
                manifest = gcs_manifest
                instructions = natural.NATURAL_PROMPT
                kwargs = {
                    "registry": gcs_registry,
                    "pre_model": True,
                    "artifact_manifest": base_manifest,
                    "pre_model_executor": lambda tool, values: validation.execute_snapshot(
                        store, tool, values
                    ),
                }
            elif condition == "gcs_gepa":
                tools = ()
                manifest = optimized_gcs_manifest
                instructions = optimized_prompt
                kwargs = {
                    "registry": optimized_gcs_registry,
                    "pre_model": True,
                    "artifact_manifest": base_manifest,
                    "pre_model_executor": lambda tool, values: validation.execute_snapshot(
                        store, tool, values
                    ),
                }
            else:
                tools = ()
                manifest = gcs_manifest
                instructions = natural.NATURAL_PROMPT
                kwargs = {
                    "pre_model": True,
                    "pre_model_executor": lambda tool, values: validation.execute_snapshot(
                        store, tool, values
                    ),
                    "pre_model_runner": ManualPreModelRunner(
                        manual_plan, catalog, base_manifest
                    ),
                }
            rows, errors = await natural.run_batch(
                [scenario],
                condition=condition,
                repeat=0,
                model_name=args.model,
                tools=tools,
                processor=processor,
                manifest=manifest,
                catalog=catalog,
                store=store,
                registry=kwargs.pop("registry", None),
                concurrency=1,
                instructions=instructions,
                **kwargs,
            )
            deployment_results.extend(rows)
            failures.extend(errors)

    grouped = {
        condition: [row for row in deployment_results if row.condition == condition]
        for condition in CONDITIONS
    }
    comparisons = {
        f"baseline_vs_{condition}": paired_with_measurement_guard(
            grouped["baseline"],
            grouped[condition],
            baseline_label="baseline",
            candidate_label=condition,
        )
        for condition in CONDITIONS
        if condition != "baseline"
    }
    comparisons["manual_pre_model_vs_gcs"] = paired_with_measurement_guard(
        grouped["manual_pre_model"],
        grouped["gcs"],
        baseline_label="manual_pre_model",
        candidate_label="gcs",
    )
    comparisons["gepa_vs_gcs_gepa"] = paired_with_measurement_guard(
        grouped["gepa"],
        grouped["gcs_gepa"],
        baseline_label="gepa",
        candidate_label="gcs_gepa",
    )
    complete = all(len(grouped[name]) == args.test_cases for name in CONDITIONS)
    reflection_metrics = reflection.metrics()
    payload = {
        "schema": "agent-compaction-optimizer-head-to-head/v1",
        "run": {
            "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "model": args.model,
            "reflection_model": args.reflection_model or args.model,
            "openai_agents_sdk": version("openai-agents"),
            "openai_python": version("openai"),
            "gepa": version("gepa"),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "openai_api_key_used": True,
            "secrets_serialized": False,
            "provider_backed": True,
            "real_public_records": True,
            "smoke": args.smoke,
            "comparative_claim_allowed": bool(not args.smoke and complete and not failures),
            "resolved_config": vars(args),
        },
        "source": {
            "dataset": fixed.HF_DATASET,
            "revision": fixed.HF_REVISION,
            "parquet_sha256": fixed.HF_PARQUET_SHA256,
            "raw_rows": len(frame),
            "deduplicated_non_pr_issues": len(store),
            "duplicate_issue_rows": sum(duplicates.values()),
        },
        "selection": selection,
        "preflight": preflight,
        "optimization": {
            "method": "official GEPA 0.1.4 optimize_anything",
            "optimized_parameter": "operational strategy sentence",
            "fixed_contract": True,
            "score_definition": (
                "1000*exact + 100*factual_score - 5*requests - tool_calls - total_tokens/10000"
            ),
            "gepa_result": gepa_result.to_dict(),
            "reflection": reflection_metrics,
            "accounting": optimization_totals(optimization_runs, reflection_metrics),
            "task_aggregate": fixed.aggregate_runs(optimization_runs),
            "task_results": [row.public_dict() for row in optimization_runs],
        },
        "manual_baseline": {
            "plan": manual_plan.to_dict(),
            "plan_id": manual_plan.plan_id,
            "provider_free_parity": parity,
            "not_compiler_derived": True,
            "not_statistically_gated": True,
            "lab_only_not_production_approved": True,
        },
        "compiler": {
            "gcs": gcs_compilation,
            "gcs_gepa": optimized_gcs_compilation,
        },
        "schedule": schedule,
        "aggregate": fixed.aggregate_runs(deployment_results),
        "comparisons": comparisons,
        "measurement_validation": latency_measurement_validation(deployment_results),
        "failures": failures,
        "deployment_results": [row.public_dict() for row in deployment_results],
        "metric_definitions": {
            "optimization_cost": "all GEPA task-evaluator and reflection calls; excluded from deployment metrics",
            "deployment_cost": "held-out test calls after the GEPA strategy was frozen",
            "pre_model_tool_calls": "one exposed observation; internal_tool_calls records the three local reads",
            "requests": "native provider generation/response spans",
            "wall_latency_ms": "primary latency metric from the host monotonic clock",
            "provider_response_latency_ms": "secondary span metric excluded from comparisons when it violates the wall-latency consistency check",
        },
    }
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    gcs_registry.save(OUT_DIR / "gcs_registry")
    optimized_gcs_registry.save(OUT_DIR / "gcs_gepa_registry")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--reflection-model")
    parser.add_argument("--train-cases", type=int, default=4)
    parser.add_argument("--val-cases", type=int, default=2)
    parser.add_argument("--test-cases", type=int, default=6)
    parser.add_argument("--max-metric-calls", type=int, default=16)
    parser.add_argument("--max-proposals", type=int, default=3)
    parser.add_argument("--reflection-minibatch", type=int, default=2)
    parser.add_argument("--seed", type=int, default=20260804)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--regrade-existing", type=Path)
    args = parser.parse_args()
    for name in ("train_cases", "val_cases", "test_cases", "max_metric_calls", "max_proposals"):
        if getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    return args


if __name__ == "__main__":
    parsed = parse_args()
    if parsed.regrade_existing is not None:
        revised = regrade_saved_payload(parsed.regrade_existing)
        print(
            json.dumps(
                {
                    "path": str(parsed.regrade_existing),
                    "oracle_revision": revised["oracle_revision"],
                    "aggregate": revised["aggregate"],
                },
                indent=2,
            )
        )
        raise SystemExit(0)
    result = asyncio.run(run(parsed))
    print(
        json.dumps(
            {
                "run": result["run"],
                "selection": result["selection"],
                "optimization": {
                    "gepa_result": result["optimization"]["gepa_result"],
                    "reflection": result["optimization"]["reflection"],
                },
                "aggregate": result["aggregate"],
                "comparisons": result["comparisons"],
                "failures": result["failures"],
            },
            indent=2,
            default=str,
        )
    )
