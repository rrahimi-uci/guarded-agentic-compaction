"""Recurrence-only replay ablation on issue-type routing (pre-registered arm).

Protocol: ``paper/supplementary/recurrence-only-ablation-protocol.md``.

The arm replays the mined three-read sequence the compiler *refused*
(``issue_get_comments.limit=100`` has no provenance witness) with every barrier
disabled: no provenance check, no guard, no verifier, no calibrated gate.  The
three snapshot reads run before the model, their results are handed to one
provider request, and the answer is graded by the retained exact
source-grounded oracle.  Comparators are the retained baseline, compiled, and
macro arms on the same sealed 30 held-out records, so every contrast is paired.

``preflight`` executes the deterministic replay for every record without a
provider call and seals the plan; ``run`` makes the 30 provider requests.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import platform
import statistics
import sys
import time
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

import github_live_study as fixed  # noqa: E402
from guarded_agentic_compaction.capture.agents_sdk import (  # noqa: E402
    AgentsTraceProcessor,
    SdkTraceRecord,
    episode_from_agents_trace,
)
from guarded_agentic_compaction.schema.traces import (  # noqa: E402
    OutcomeLabels,
    TraceEnvelope,
    content_digest,
)
from demos.live_runtime import observations_from_trace, trace_metrics  # noqa: E402

PROTOCOL = ROOT / "paper/supplementary/recurrence-only-ablation-protocol.md"
RETAINED = ROOT / "paper/results/github_natural_replication/results.json"
OUT_DIR = ROOT / "paper/results/recurrence_only_ablation"
TASK_DESIGN = "natural-extractive-v2"
CONDITION = "recurrence_only_three_read"
THREE_READ_PLAN = (
    ("issue_get_record", {"issue_number": "z.issue_number"}),
    ("issue_get_labels", {"issue_number": "z.issue_number"}),
    ("issue_get_comments", {"issue_number": "z.issue_number", "limit": 100}),
)
RETAINED_CONDITIONS = ("baseline", "compiled", "macro")


# --------------------------------------------------------------------------- data


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_store() -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    """Load the pinned snapshot without a network call; fail closed on a checksum miss."""

    if not fixed.DATA_PATH.exists():
        raise RuntimeError(f"pinned snapshot missing: {fixed.DATA_PATH}")
    observed = sha256_file(fixed.DATA_PATH)
    if observed != fixed.HF_PARQUET_SHA256:
        raise RuntimeError(f"pinned dataset checksum mismatch: {observed}")
    frame = pd.read_parquet(fixed.DATA_PATH)
    store, _duplicates = fixed.build_store(frame)
    audit = {
        "dataset": fixed.HF_DATASET,
        "revision": fixed.HF_REVISION,
        "parquet_sha256": observed,
        "deduplicated_non_pr_issues": len(store),
    }
    return store, audit


def load_retained() -> dict[str, Any]:
    return json.loads(RETAINED.read_text(encoding="utf-8"))


def sealed_scenarios(retained: dict[str, Any]) -> list[fixed.Scenario]:
    items = retained["selection"]["test"]
    return [
        fixed.Scenario(
            issue_number=int(item["issue_number"]),
            category=str(item["category"]),
            labels=tuple(item["labels"]),
            html_url=str(item["html_url"]),
            day=str(item["day"]),
            state=str(item["state"]),
        )
        for item in items
    ]


def retained_rows(retained: dict[str, Any], condition: str) -> list[SimpleNamespace]:
    return [
        SimpleNamespace(
            condition=row["condition"],
            repeat=int(row.get("repeat", 0)),
            issue_number=int(row["issue_number"]),
            metrics=dict(row["metrics"]),
            quality=dict(row["quality"]),
        )
        for row in retained["results"]
        if row["condition"] == condition and int(row.get("repeat", 0)) == 0
    ]


def execute_issue_snapshot(
    store: dict[int, dict[str, Any]], tool: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Replicate the three snapshot tools byte for byte (see github_live_study.make_tools)."""

    item = store.get(int(arguments["issue_number"]))
    if tool == "issue_get_record":
        if item is None:
            return {"error": "not_found", "source_revision": fixed.HF_REVISION}
        return {
            "issue_number": item["number"],
            "state": item["state"],
            "source_revision": fixed.HF_REVISION,
            "content": {
                "title": item["title"][:500],
                "body_excerpt": item["body"][:2400],
                "html_url": item["html_url"],
            },
        }
    if tool == "issue_get_labels":
        return {
            "names": list(item["labels"]) if item is not None else [],
            "source_revision": fixed.HF_REVISION,
        }
    if tool == "issue_get_comments":
        limit = int(arguments["limit"])
        comments = item["comments"] if item is not None else []
        return {
            "source_revision": fixed.HF_REVISION,
            "thread": {
                "total": len(comments),
                "items": [comment[:800] for comment in comments[: max(0, min(limit, 3))]],
            },
        }
    raise KeyError(tool)


def replay_three_reads(
    store: dict[int, dict[str, Any]], issue_number: int
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any]]:
    """Unguarded replay of the mined region: no provenance, guard, verifier, or gate."""

    sequence: list[str] = []
    arguments: list[dict[str, Any]] = []
    evidence: dict[str, Any] = {}
    for tool, template in THREE_READ_PLAN:
        args = {
            key: (issue_number if value == "z.issue_number" else value)
            for key, value in template.items()
        }
        sequence.append(tool)
        arguments.append(args)
        evidence[tool] = execute_issue_snapshot(store, tool, args)
    return sequence, arguments, evidence


def evidence_prompt(issue_number: int, evidence: dict[str, Any]) -> str:
    payload = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
    return (
        "Triage this public GitHub issue snapshot record. "
        f"issue_number={issue_number}\n"
        "The runtime already executed the recorded read sequence. Do not call tools. "
        "Use only this source-grounded JSON evidence:\n" + payload
    )


# ------------------------------------------------------------------------ preflight


def plan_description() -> dict[str, Any]:
    return {
        "arm": CONDITION,
        "construction": "recurrence-only replay of the mined three-read region",
        "barriers_disabled": ["provenance", "guard", "verifier", "calibrated_gate", "position"],
        "steps": [
            {"tool": tool, "args": args} for tool, args in THREE_READ_PLAN
        ],
        "provider_requests_per_record": 1,
        "tools_exposed_to_model": 0,
        "runner_deviation": (
            "The protocol names a ManualPreModelPlan with a clause-free Verifier(); the "
            "guarded manual runner rejects such a plan structurally (verifier outputs and "
            "call counts are required, and the retained issue catalog does not declare the "
            "batchable capability). The arm therefore replays the three reads directly, "
            "which is the barrier-free replay the protocol defines, and records this here."
        ),
    }


def preflight(args: argparse.Namespace) -> dict[str, Any]:
    store, audit = load_store()
    retained = load_retained()
    scenarios = sealed_scenarios(retained)
    if len(scenarios) != 30:
        raise RuntimeError(f"sealed cohort has {len(scenarios)} records; expected 30")
    replays = []
    for scenario in scenarios:
        sequence, arguments, evidence = replay_three_reads(store, scenario.issue_number)
        record = evidence["issue_get_record"]
        if record.get("issue_number") != scenario.issue_number:
            raise RuntimeError(f"replay produced a foreign record for {scenario.issue_number}")
        replays.append(
            {
                "issue_number": scenario.issue_number,
                "tool_sequence": sequence,
                "tool_arguments": arguments,
                "evidence_sha256": hashlib.sha256(
                    json.dumps(evidence, sort_keys=True).encode()
                ).hexdigest(),
                "comment_items": len(evidence["issue_get_comments"]["thread"]["items"]),
                "evidence_bytes": len(json.dumps(evidence, sort_keys=True)),
            }
        )
    comparators = {}
    for condition in RETAINED_CONDITIONS:
        rows = retained_rows(retained, condition)
        comparators[condition] = {
            "n": len(rows),
            "factuality_exact": sum(bool(row.quality.get("factuality_exact")) for row in rows),
            "provider_requests": sum(int(row.metrics["requests"]) for row in rows),
        }
    numbers = [scenario.issue_number for scenario in scenarios]
    payload = {
        "schema": "agent-compaction-recurrence-only-preflight/v1",
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "execution_status": "preflight_only",
        "provider_calls": 0,
        "real_public_records": True,
        "simulated": False,
        "protocol": {
            "path": str(PROTOCOL.relative_to(ROOT)),
            "sha256": sha256_file(PROTOCOL),
        },
        "source": audit,
        "retained_comparators": {
            "path": str(RETAINED.relative_to(ROOT)),
            "sha256": sha256_file(RETAINED),
            "model": retained["run"]["model"],
            "conditions": comparators,
        },
        "selection": {
            "test": numbers,
            "record_numbers_sha256": hashlib.sha256(
                json.dumps(sorted(numbers)).encode()
            ).hexdigest(),
            "reused_from_sealed_selection": True,
        },
        "plan": plan_description(),
        "model": args.model,
        "model_settings": {
            "reasoning_effort": "low",
            "verbosity": "low",
            "parallel_tool_calls": False,
            "store": False,
            "max_turns": 8,
            "timeout_s": 120,
            "retry_policy": "one retry per timed-out episode; both attempts retained",
        },
        "spend": {"approved_usd_required": 0.25, "expected_usd": 0.02},
        "deterministic_replay": replays,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "preflight.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


# ------------------------------------------------------------------------------ run


def materialize(
    scenario: fixed.Scenario,
    *,
    model: str,
    trace: SdkTraceRecord,
    final_output: Any,
    wall_ms: float,
    manifest: Any,
    sequence: list[str],
    arguments: list[dict[str, Any]],
    source_record: dict[str, Any],
    attempt: int,
) -> fixed.RunResult:
    answer = fixed._answer_dict(final_output)
    quality = fixed.grade(
        scenario,
        answer,
        sequence,
        arguments,
        task_design=TASK_DESIGN,
        source_record=source_record,
        condition=CONDITION,
    )
    outcome = OutcomeLabels(
        task_success=bool(quality["overall"]),
        semantic_score=float(quality["score"]),
        safety_events=0,
        business_metrics={
            "category_correct": float(quality["category_correct"]),
            "tool_contract": float(quality["tool_contract"]),
        },
    )
    envelope = TraceEnvelope(
        trace_id=trace.trace_id,
        episode_id=f"github-{scenario.issue_number}:{CONDITION}:a{attempt}",
        group_id=f"github-issue:{scenario.issue_number}",
        manifest_id=manifest.manifest_id,
        principal="public-benchmark-runner",
        tenant_partition="public:huggingface-datasets",
        policy_version="github-triage-v1",
        day=scenario.day,
        privacy_class="public_dataset_provider_trace",
        entry_state_ref=content_digest({"issue_number": scenario.issue_number}),
        external_state_version=fixed.HF_REVISION,
    )
    episode = episode_from_agents_trace(
        trace,
        envelope=envelope,
        manifest=manifest,
        entry_state={"issue_number": scenario.issue_number},
        outcome=outcome,
        final_state_digest=fixed.HF_PARQUET_SHA256,
    )
    episode.attributes.update(
        {
            "real_public_record": True,
            "local_snapshot_tools": True,
            "provider_backed": True,
            "condition": CONDITION,
            "task_design": TASK_DESIGN,
            "recurrence_only_replay": True,
        }
    )
    metrics = trace_metrics(trace, model=model, wall_ms=wall_ms)
    metrics.update(
        {"provider_tool_calls": 0, "tool_calls": 3, "internal_tool_calls": 3}
    )
    return fixed.RunResult(
        condition=CONDITION,
        repeat=0,
        issue_number=scenario.issue_number,
        trace_id=trace.trace_id,
        metrics=metrics,
        answer=answer,
        quality=quality,
        tool_sequence=sequence,
        tool_arguments=arguments,
        dispatch={"outcome": "REPLAYED", "barriers": "disabled", "n_calls": 3},
        episode=episode,
    )


async def run_one(
    scenario: fixed.Scenario,
    *,
    store: dict[int, dict[str, Any]],
    model: str,
    manifest: Any,
    processor: AgentsTraceProcessor,
) -> tuple[fixed.RunResult | None, list[dict[str, Any]]]:
    from agents import RunConfig, Runner

    attempts: list[dict[str, Any]] = []
    sequence, arguments, evidence = replay_three_reads(store, scenario.issue_number)
    user_input = evidence_prompt(scenario.issue_number, evidence)
    for attempt in (0, 1):
        trace_id = "trace_" + hashlib.sha256(
            f"{CONDITION}:{attempt}:{scenario.issue_number}".encode()
        ).hexdigest()[:32]
        agent = fixed.make_agent(model, [], TASK_DESIGN)
        started = time.perf_counter()
        try:
            output = await asyncio.wait_for(
                Runner.run(
                    agent,
                    user_input,
                    max_turns=8,
                    run_config=RunConfig(
                        workflow_name=f"agent-compaction-paper:github:{CONDITION}",
                        trace_id=trace_id,
                        group_id=f"github-issue:{scenario.issue_number}",
                        trace_include_sensitive_data=True,
                        trace_metadata={
                            "data_source": fixed.HF_DATASET,
                            "data_revision": fixed.HF_REVISION,
                            "public_real_record": "true",
                            "provider_backed": "true",
                            "condition": CONDITION,
                            "attempt": str(attempt),
                            "issue_number": str(scenario.issue_number),
                        },
                    ),
                ),
                timeout=120.0,
            )
        except BaseException as exc:  # retained under intention-to-treat
            wall_ms = (time.perf_counter() - started) * 1000.0
            processor.drain()
            attempts.append(
                {
                    "issue_number": scenario.issue_number,
                    "attempt": attempt,
                    "error": f"{type(exc).__name__}: {exc}",
                    "wall_latency_ms": round(wall_ms, 3),
                }
            )
            if isinstance(exc, asyncio.TimeoutError) and attempt == 0:
                continue
            return None, attempts
        wall_ms = (time.perf_counter() - started) * 1000.0
        records = {record.trace_id: record for record in processor.drain()}
        trace = records.get(trace_id)
        if trace is None:
            attempts.append(
                {
                    "issue_number": scenario.issue_number,
                    "attempt": attempt,
                    "error": "missing completed SDK trace",
                }
            )
            return None, attempts
        if observations_from_trace(trace, {}):
            attempts.append(
                {
                    "issue_number": scenario.issue_number,
                    "attempt": attempt,
                    "error": "provider called a tool after the replayed evidence",
                }
            )
            return None, attempts
        result = materialize(
            scenario,
            model=model,
            trace=trace,
            final_output=output.final_output,
            wall_ms=wall_ms,
            manifest=manifest,
            sequence=sequence,
            arguments=arguments,
            source_record=store[scenario.issue_number],
            attempt=attempt,
        )
        return result, attempts
    return None, attempts


def continuation_audit(
    results: Sequence[fixed.RunResult], store: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    """Locate every returned excerpt in the pinned source, as the 6602 audit did."""

    rows = []
    for result in results:
        source = store[result.issue_number]
        excerpt = str(result.answer.get("evidence_excerpt", "")).strip()
        where = None
        if excerpt and excerpt in str(source.get("title", "")):
            where = "title"
        elif excerpt and excerpt in str(source.get("body", ""))[:2400]:
            where = "body"
        else:
            for index, comment in enumerate(source.get("comments", [])[:3]):
                if excerpt and excerpt in str(comment)[:800]:
                    where = f"comment[{index}]"
                    break
        rows.append(
            {
                "issue_number": result.issue_number,
                "excerpt_chars": len(excerpt),
                "located_in": where,
                "exact": bool(result.quality.get("evidence_excerpt_exact")),
                "markdown_link_in_source_comments": any(
                    "](" in str(comment) for comment in source.get("comments", [])[:3]
                ),
            }
        )
    return {
        "records": rows,
        "excerpt_located": sum(row["located_in"] is not None for row in rows),
        "excerpt_exact": sum(row["exact"] for row in rows),
    }


def decision_rule_reading(
    exact: int, n: int, requests: int, completed: int
) -> str:
    if completed == n and exact == n and requests == n:
        return (
            "30/30 exact, one request per record: on this cohort the provenance refusal "
            "cost one request per record without a measured quality benefit; the guard's "
            "value is the refusal of an unwitnessed argument plus the retained 6602 "
            "counterexample (18-record cohort), not a held-out failure."
        )
    if completed < n:
        return (
            f"{n - completed} episode(s) did not complete after one retry and count as "
            "failures of the arm under intention-to-treat; reported ahead of every other reading."
        )
    return (
        f"{n - exact} held-out failure(s): the failing record(s) and mechanism are the "
        "direct price of the missing guard; reported in full ahead of every other reading."
    )


async def run(args: argparse.Namespace) -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")
    if args.approved_spend_usd is None or args.approved_spend_usd <= 0:
        raise RuntimeError("a positive --approved-spend-usd is required for a live run")
    pre = preflight(args)
    store, _audit = load_store()
    retained = load_retained()
    scenarios = sealed_scenarios(retained)
    result_path = OUT_DIR / "results.json"
    if result_path.exists() and not args.force:
        raise RuntimeError(f"refusing to overwrite {result_path}; pass --force")

    from agents import add_trace_processor

    processor = AgentsTraceProcessor(include_sensitive_data=True, max_completed=500)
    add_trace_processor(processor)
    catalog = fixed.make_catalog()
    manifest = fixed.make_manifest(args.model, [], catalog, TASK_DESIGN)

    results: list[fixed.RunResult] = []
    attempts: list[dict[str, Any]] = []
    spent = 0.0
    for scenario in scenarios:
        if spent > args.approved_spend_usd:
            attempts.append(
                {"issue_number": scenario.issue_number, "error": "approved spend exhausted"}
            )
            continue
        result, record_attempts = await run_one(
            scenario, store=store, model=args.model, manifest=manifest, processor=processor
        )
        attempts.extend(record_attempts)
        if result is not None:
            results.append(result)
            spent += float(result.metrics.get("estimated_cost_usd") or 0.0)
        (OUT_DIR / "evaluation_checkpoint.json").write_text(
            json.dumps(
                {
                    "results": [value.public_dict() for value in results],
                    "attempts": attempts,
                },
                indent=2,
                sort_keys=True,
                default=str,
            )
            + "\n",
            encoding="utf-8",
        )

    n = len(scenarios)
    exact = sum(bool(value.quality.get("factuality_exact")) for value in results)
    requests = sum(int(value.metrics["requests"]) for value in results)
    comparisons = {
        f"{condition}_vs_{CONDITION}": fixed.paired_analysis(
            retained_rows(retained, condition),
            results,
            candidate_label=CONDITION,
            baseline_label=condition,
        )
        for condition in RETAINED_CONDITIONS
    }
    field_names = (
        "category_correct",
        "issue_number_correct",
        "evidence_label_correct",
        "title_exact",
        "state_exact",
        "comment_count_exact",
        "evidence_excerpt_exact",
        "factuality_exact",
        "tool_contract",
        "overall",
    )
    payload = {
        "schema": "agent-compaction-recurrence-only-ablation/v1",
        "run": {
            "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "script": "paper/scripts/recurrence_only_ablation.py",
            "model": args.model,
            "openai_agents_sdk": version("openai-agents"),
            "openai_python": version("openai"),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "provider_backed": True,
            "real_public_records": True,
            "simulated": False,
            "openai_api_key_used": True,
            "secrets_serialized": False,
            "approved_spend_usd": args.approved_spend_usd,
            "estimated_spend_usd": round(spent, 6),
            "comparative_claim_allowed": len(results) == n,
            "protocol": pre["protocol"],
        },
        "source": pre["source"],
        "selection": pre["selection"],
        "plan": pre["plan"],
        "retained_comparators": pre["retained_comparators"],
        "intention_to_treat": {
            "attempted": n,
            "completed": len(results),
            "failed_after_retry": n - len(results),
        },
        "aggregate": fixed.aggregate_runs(results),
        "per_field_exact": {
            name: sum(bool(value.quality.get(name)) for value in results) for name in field_names
        },
        "hypotheses": {
            "H-B1a_exact_30_of_30": exact == n and len(results) == n,
            "H-B1b_one_request_per_record": len(results) == n and requests == n,
            "H-B1c_at_least_one_excerpt_or_url_loss": any(
                not value.quality.get("evidence_excerpt_exact") for value in results
            ),
        },
        "decision_rule_reading": decision_rule_reading(exact, n, requests, len(results)),
        "comparisons": comparisons,
        "continuation_audit": continuation_audit(results, store),
        "attempts": attempts,
        "results": [value.public_dict() for value in results],
        "metric_definitions": {
            "requests": "native provider generation/response spans",
            "tool_calls": "the three deterministic reads replayed before the model",
            "wall_latency_ms": "host monotonic clock around the complete SDK run",
        },
    }
    result_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    return payload


# ---------------------------------------------------------------------------- table


TABLE_PATH = ROOT / "paper/iclr/tables/recurrence_only.tex"
TABLE_ROWS = (
    ("baseline", "Unchanged agent"),
    ("compiled", "Compiled two-read prefix (\\method)"),
    ("macro", "Hand-written bundle"),
    (CONDITION, "Recurrence-only three-read replay"),
)


def table(_args: argparse.Namespace) -> str:
    """Arm x metric over the 30 sealed records; every retained arm from its retained file."""

    results = json.loads((OUT_DIR / "results.json").read_text(encoding="utf-8"))
    retained = load_retained()
    rows: dict[str, list[dict[str, Any]]] = {
        condition: [row for row in retained["results"]
                    if row["condition"] == condition and int(row.get("repeat", 0)) == 0]
        for condition in RETAINED_CONDITIONS
    }
    rows[CONDITION] = list(results["results"])
    n_attempted = int(results["intention_to_treat"]["attempted"])
    lines = [
        r"\begin{tabular}{@{}lrrrrr@{}}", r"\toprule",
        r"Arm & Exact & Requests & Tokens & Latency (s) & Cost (\textcent) \\",
        r"\midrule",
    ]
    for condition, label in TABLE_ROWS:
        sel = rows[condition]
        n = len(sel)
        exact = sum(bool(r["quality"].get("factuality_exact")) for r in sel)
        mean = lambda key: (sum(float(r["metrics"][key] or 0.0) for r in sel) / n) if n else 0.0  # noqa: E731
        lines.append(
            f"{label} & {exact}/{n_attempted} & {mean('requests'):.2f} & {mean('total_tokens'):,.0f} & "
            f"{mean('wall_latency_ms') / 1000:.2f} & {100 * mean('estimated_cost_usd'):.3f} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    text = ("% generated by paper/scripts/recurrence_only_ablation.py table; do not edit\n"
            + "\n".join(lines) + "\n")
    TABLE_PATH.write_text(text, encoding="utf-8")
    return text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "run", "table"))
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--approved-spend-usd", type=float)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "preflight":
        payload = preflight(args)
        summary = {k: v for k, v in payload.items() if k != "deterministic_replay"}
        summary["deterministic_replay_records"] = len(payload["deterministic_replay"])
    elif args.command == "table":
        print(table(args))
        return
    else:
        payload = asyncio.run(run(args))
        summary = {
            key: payload[key]
            for key in (
                "run",
                "intention_to_treat",
                "aggregate",
                "per_field_exact",
                "hypotheses",
                "decision_rule_reading",
            )
        }
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
