"""Second-model replication of the primary live families (pre-registered).

Protocol: ``paper/supplementary/second-model-replication-protocol.md``.

Design B of the protocol: the sealed discovery traces, splits, and held-out
cohorts of the retained gpt-5.6-luna studies are reused unchanged; the
artifact is recompiled provider-free under a manifest that pins the second
model, so its compatibility key matches the runtime; then the held-out arms run
live on the second model.  PR-outcome and backlog-attention use the existing
family harness (``github_workflow_family_study.py --model ... --sealed-selection
... --discovery-checkpoint ...``).  This module supplies the same path for
issue-type routing, whose harness has no checkpoint-reuse option, and the
cross-family summary.

Sub-commands
------------
``preflight``  reconstruct the 132 sealed discovery traces from the checkpoint,
               recompile under the retained manifest and assert the retained
               artifact is reproduced (program, gate, splits), recompile under
               the second-model manifest, and seal the arms.  No provider call.
``run``        the three held-out arms (baseline, compiled, macro) on the second
               model in the retained Latin order.
``summarize``  pool the three families into ``summary.json`` and the ICLR table.
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
from typing import Any, Sequence

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import github_live_study as fixed  # noqa: E402
import recurrence_only_ablation as shared  # noqa: E402
from guarded_agentic_compaction.capture.agents_sdk import AgentsTraceProcessor  # noqa: E402
from guarded_agentic_compaction.schema.traces import (  # noqa: E402
    Episode,
    EventKind,
    EventNode,
    OutcomeLabels,
    TraceEnvelope,
    content_digest,
)

PROTOCOL = ROOT / "paper/supplementary/second-model-replication-protocol.md"
OUT_ROOT = ROOT / "paper/results/second_model_replication"
ISSUE_DIR = OUT_ROOT / "issue_type"
CHECKPOINT = ROOT / "paper/results/github_natural_replication/discovery_checkpoint.json"
FAMILY_ROOT = ROOT / "paper/results/github_workflow_families"
TABLE_PATH = ROOT / "paper/iclr/tables/second_model.tex"
TASK_DESIGN = "natural-extractive-v2"
CONDITIONS = ("baseline", "compiled", "macro")
SPLIT = {"train": 16, "dev": 8, "calibration": 92}


# ------------------------------------------------------------- discovery reconstruction


def reconstruct_discovery(
    checkpoint: dict[str, Any],
    *,
    store: dict[int, dict[str, Any]],
    manifest: Any,
) -> list[fixed.RunResult]:
    """Rebuild the sealed discovery episodes from the checkpoint's public rows.

    Mirrors ``github_workflow_family_study.reconstruct_discovery``: one model
    boundary per recorded call, tool results re-executed on the pinned snapshot,
    and the attributes ``compile_artifact`` reads for its coverage anchors.
    """

    runs: list[fixed.RunResult] = []
    for saved in checkpoint["results"]:
        number = int(saved["issue_number"])
        row = store[number]
        events: list[EventNode] = []
        for step, (tool, arguments) in enumerate(
            zip(saved["tool_sequence"], saved["tool_arguments"])
        ):
            base = len(events)
            call_id = f"issue-checkpoint-{number}-{step}"
            events.extend(
                [
                    EventNode(f"{call_id}-request", EventKind.MODEL_REQ, base),
                    EventNode(f"{call_id}-response", EventKind.MODEL_RESP, base + 1),
                    EventNode(
                        f"{call_id}-call", EventKind.TOOL_CALL, base + 2,
                        tool=str(tool), input=dict(arguments), call_id=call_id,
                        declared_effect="READ_LOCAL",
                    ),
                    EventNode(
                        f"{call_id}-result", EventKind.TOOL_RESULT, base + 3,
                        tool=str(tool),
                        output=shared.execute_issue_snapshot(store, str(tool), dict(arguments)),
                        call_id=call_id,
                    ),
                ]
            )
        base = len(events)
        events.extend(
            [
                EventNode(f"issue-checkpoint-{number}-final-request", EventKind.MODEL_REQ, base),
                EventNode(f"issue-checkpoint-{number}-final-response", EventKind.MODEL_RESP, base + 1),
            ]
        )
        quality = dict(saved["quality"])
        envelope = TraceEnvelope(
            trace_id=str(saved["trace_id"]),
            episode_id=f"github-{number}:discovery:r0",
            group_id=f"github-issue:{number}",
            manifest_id=manifest.manifest_id,
            principal="public-benchmark-runner",
            tenant_partition="public:huggingface-datasets",
            policy_version="github-triage-v1",
            day=str(row["day"]),
            privacy_class="public_dataset_provider_trace",
            entry_state_ref=content_digest({"issue_number": number}),
            external_state_version=fixed.HF_REVISION,
        )
        episode = Episode(
            envelope=envelope,
            manifest=manifest,
            entry_state={"issue_number": number},
            events=events,
            outcome=OutcomeLabels(
                task_success=bool(quality["overall"]),
                semantic_score=float(quality["score"]),
                safety_events=0,
                business_metrics={
                    "category_correct": float(quality["category_correct"]),
                    "tool_contract": float(quality["tool_contract"]),
                },
            ),
            final_state_digest=fixed.HF_PARQUET_SHA256,
            attributes={
                "real_public_record": True,
                "local_snapshot_tools": True,
                "provider_backed": True,
                "reconstructed_from_sealed_checkpoint": True,
                "issue_url": row["html_url"],
                "category": fixed.category_for(row["labels"]),
                "label_count": len(row["labels"]),
                "state": row["state"],
                "condition": "discovery",
                "repeat": 0,
                "task_design": TASK_DESIGN,
            },
        )
        runs.append(
            fixed.RunResult(
                condition="discovery",
                repeat=0,
                issue_number=number,
                trace_id=str(saved["trace_id"]),
                metrics=dict(saved["metrics"]),
                answer=dict(saved["answer"]),
                quality=quality,
                tool_sequence=list(saved["tool_sequence"]),
                tool_arguments=[dict(value) for value in saved["tool_arguments"]],
                dispatch=dict(saved.get("dispatch", {})),
                episode=episode,
            )
        )
    return runs


def compile_for_model(
    discovery: Sequence[fixed.RunResult], *, model: str, catalog: Any, tools: Sequence[Any]
) -> tuple[Any, dict[str, Any], Any]:
    manifest = fixed.make_manifest(model, tools, catalog, TASK_DESIGN)
    registry, record, _numbers = fixed.compile_artifact(
        list(discovery),
        catalog=catalog,
        manifest=manifest,
        train_n=SPLIT["train"],
        dev_n=SPLIT["dev"],
        calibration_n=SPLIT["calibration"],
        task_design=TASK_DESIGN,
    )
    return registry, record, manifest


def artifact_fingerprint(artifact: dict[str, Any]) -> dict[str, Any]:
    gate = artifact.get("gate", {})
    program = dict(artifact.get("program") or {})
    if program.get("composite") is None:
        # Program.to_dict gained an always-present ``composite`` key after the
        # retained run was serialized; a null composite is the same program.
        program.pop("composite", None)
    return {
        "artifact_id": artifact.get("artifact_id"),
        "program": program,
        "gate_n_calibration_groups": gate.get("n_calibration_groups"),
        "gate_n_accepted": gate.get("n_accepted"),
        "gate_violations": gate.get("observed_violations"),
        "gate_upper_bound": gate.get("risk_upper_bound"),
        "gate_threshold": gate.get("threshold"),
        "gate_retire": gate.get("retire"),
    }


# ------------------------------------------------------------------------ preflight


def preflight(args: argparse.Namespace) -> dict[str, Any]:
    store, audit = shared.load_store()
    retained = shared.load_retained()
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    scenarios = shared.sealed_scenarios(retained)
    catalog = fixed.make_catalog()
    tools = fixed.make_tools(store)
    retained_model = str(retained["run"]["model"])

    # 1. Reproduce the retained artifact under the retained manifest.
    original_manifest = fixed.make_manifest(retained_model, tools, catalog, TASK_DESIGN)
    discovery = reconstruct_discovery(checkpoint, store=store, manifest=original_manifest)
    _registry, original_record, _manifest = compile_for_model(
        discovery, model=retained_model, catalog=catalog, tools=tools
    )
    retained_art = retained["compiler"]["artifact"]
    reproduced = artifact_fingerprint(original_record["artifact"])
    expected = artifact_fingerprint(retained_art)
    checks = {
        "program_identical": reproduced["program"] == expected["program"],
        "artifact_id_identical": reproduced["artifact_id"] == expected["artifact_id"],
        "splits_digest_identical": original_record["splits"].get("digest")
        == retained["compiler"]["splits"].get("digest"),
        "gate_identical": {
            key: reproduced[key] == expected[key]
            for key in ("gate_n_calibration_groups", "gate_n_accepted", "gate_violations",
                        "gate_upper_bound", "gate_threshold", "gate_retire")
        },
        "candidate_count_identical": len(original_record["candidates"])
        == len(retained["compiler"]["candidates"]),
    }
    if not (checks["program_identical"] and checks["splits_digest_identical"]
            and all(checks["gate_identical"].values())):
        raise RuntimeError(
            "reconstruction does not reproduce the retained artifact: "
            + json.dumps({"checks": checks, "reproduced": reproduced, "expected": expected},
                         indent=2, default=str)
        )

    # 2. Recompile under the second-model manifest (same traces, new pin).
    second_manifest = fixed.make_manifest(args.model, tools, catalog, TASK_DESIGN)
    second_discovery = reconstruct_discovery(checkpoint, store=store, manifest=second_manifest)
    second_registry, second_record, _ = compile_for_model(
        second_discovery, model=args.model, catalog=catalog, tools=tools
    )
    second = artifact_fingerprint(second_record["artifact"])
    ISSUE_DIR.mkdir(parents=True, exist_ok=True)
    second_registry.save(ISSUE_DIR / "registry")

    from demos.live_runtime import MODEL_PRICES

    orders = retained["condition_order"]["primary"]["assignments"]
    numbers = [scenario.issue_number for scenario in scenarios]
    payload = {
        "schema": "agent-compaction-second-model-preflight/v1",
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "family": "issue_type",
        "execution_status": "preflight_only",
        "provider_calls": 0,
        "real_public_records": True,
        "simulated": False,
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": shared.sha256_file(PROTOCOL)},
        "source": audit,
        "retained": {
            "path": str(shared.RETAINED.relative_to(ROOT)),
            "sha256": shared.sha256_file(shared.RETAINED),
            "model": retained_model,
            "discovery_checkpoint": str(CHECKPOINT.relative_to(ROOT)),
            "discovery_checkpoint_sha256": shared.sha256_file(CHECKPOINT),
            "artifact": expected,
        },
        "reproduction_under_retained_manifest": {"checks": checks, "artifact": reproduced},
        "second_model": {
            "model": args.model,
            "list_price_pinned": args.model in MODEL_PRICES,
            "artifact": second,
            "program_identical_to_retained": second["program"] == expected["program"],
            "manifest_compatibility_key": second_manifest.compatibility_key(),
            "registry": str((ISSUE_DIR / "registry").relative_to(ROOT)),
        },
        "selection": {
            "discovery": [int(v["issue_number"]) for v in checkpoint["results"]],
            "test": numbers,
            "record_numbers_sha256": hashlib.sha256(json.dumps(sorted(numbers)).encode()).hexdigest(),
            "discovery_reused_from_sealed_checkpoint": True,
            "test_reused_from_sealed_selection": True,
        },
        "conditions": list(CONDITIONS),
        "condition_order": {"method": "retained balanced six-permutation Latin order", "assignments": orders},
        "model_settings": {
            "reasoning_effort": "low",
            "verbosity": "low",
            "parallel_tool_calls": False,
            "store": False,
            "max_turns": 8,
            "timeout_s": 120,
            "retry_policy": "one retry per timed-out episode; both attempts retained",
        },
        "spend": {"approved_usd_required": 1.0, "expected_usd": 0.05},
    }
    (ISSUE_DIR / "preflight.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
    )
    return payload


# ------------------------------------------------------------------------------ run


async def run(args: argparse.Namespace) -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")
    if args.approved_spend_usd is None or args.approved_spend_usd <= 0:
        raise RuntimeError("a positive --approved-spend-usd is required for a live run")
    pre = preflight(args)
    store, _audit = shared.load_store()
    retained = shared.load_retained()
    scenarios = shared.sealed_scenarios(retained)
    result_path = ISSUE_DIR / "results.json"
    if result_path.exists() and not args.force:
        raise RuntimeError(f"refusing to overwrite {result_path}; pass --force")

    from agents import add_trace_processor
    from guarded_agentic_compaction.registry.store import Registry

    processor = AgentsTraceProcessor(include_sensitive_data=True, max_completed=2000)
    add_trace_processor(processor)
    catalog = fixed.make_catalog()
    tools = fixed.make_tools(store)
    manifest = fixed.make_manifest(args.model, tools, catalog, TASK_DESIGN)
    macro_tools = fixed.make_macro_tool(store)
    macro_catalog = fixed.make_macro_catalog()
    macro_manifest = fixed.make_manifest(args.model, macro_tools, macro_catalog, TASK_DESIGN)
    registry = Registry.load(ISSUE_DIR / "registry")
    arms = {
        "baseline": {"tools": tools, "catalog": catalog, "manifest": manifest, "registry": None},
        "compiled": {"tools": tools, "catalog": catalog, "manifest": manifest, "registry": registry},
        "macro": {"tools": macro_tools, "catalog": macro_catalog, "manifest": macro_manifest, "registry": None},
    }
    orders = pre["condition_order"]["assignments"]

    results: list[fixed.RunResult] = []
    attempts: list[dict[str, Any]] = []
    spent = 0.0
    for scenario in scenarios:
        for condition in orders[str(scenario.issue_number)]:
            if spent > args.approved_spend_usd:
                attempts.append({"issue_number": scenario.issue_number, "condition": condition,
                                 "error": "approved spend exhausted"})
                continue
            arm = arms[condition]
            for attempt in (0, 1):
                rows, failures = await fixed.run_agents_batch(
                    [scenario],
                    condition=condition,
                    repeat=attempt,
                    model_name=args.model,
                    tools=arm["tools"],
                    processor=processor,
                    manifest=arm["manifest"],
                    catalog=arm["catalog"],
                    registry=arm["registry"],
                    concurrency=1,
                    task_design=TASK_DESIGN,
                    source_store=store,
                )
                for failure in failures:
                    attempts.append({**failure, "attempt": attempt})
                if rows:
                    row = rows[0]
                    row.repeat = 0
                    results.append(row)
                    spent += float(row.metrics.get("estimated_cost_usd") or 0.0)
                    break
                timed_out = any("TimeoutError" in str(f.get("error", "")) for f in failures)
                if not timed_out:
                    break
            (ISSUE_DIR / "evaluation_checkpoint.json").write_text(
                json.dumps({"results": [v.public_dict() for v in results], "attempts": attempts},
                           indent=2, sort_keys=True, default=str) + "\n",
                encoding="utf-8",
            )

    grouped = {c: [r for r in results if r.condition == c] for c in CONDITIONS}
    n = len(scenarios)
    payload = {
        "schema": "agent-compaction-second-model-replication/v1",
        "run": {
            "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "script": "paper/scripts/second_model_replication.py",
            "family": "issue_type",
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
            "comparative_claim_allowed": all(len(grouped[c]) == n for c in CONDITIONS),
            "protocol": pre["protocol"],
        },
        "source": pre["source"],
        "retained": pre["retained"],
        "second_model": pre["second_model"],
        "selection": pre["selection"],
        "condition_order": pre["condition_order"],
        "intention_to_treat": {
            c: {"attempted": n, "completed": len(grouped[c])} for c in CONDITIONS
        },
        "aggregate": fixed.aggregate_runs(results),
        "comparisons": {
            "baseline_vs_compiled": fixed.paired_analysis(grouped["baseline"], grouped["compiled"]),
            "baseline_vs_macro": fixed.paired_analysis(
                grouped["baseline"], grouped["macro"], candidate_label="macro"
            ),
        },
        "dispatch": {
            "compiled_compacted": sum(int(r.dispatch.get("compacted", 0) > 0) for r in grouped["compiled"]),
        },
        "attempts": attempts,
        "results": [v.public_dict() for v in results],
    }
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
                           encoding="utf-8")
    return payload


# ------------------------------------------------------------ design A: re-discovery


REDISCOVERY_DIR = OUT_ROOT / "issue_type_rediscovery"
REDISCOVERY_PROTOCOL = ROOT / "paper/supplementary/second-model-rediscovery-protocol.md"


def discovery_scenarios(retained: dict[str, Any], store: dict[int, dict[str, Any]]) -> list[fixed.Scenario]:
    out = []
    for number in retained["selection"]["discovery_issue_numbers"]:
        item = store[int(number)]
        out.append(fixed.Scenario(
            issue_number=int(number), category=fixed.category_for(item["labels"]),
            labels=tuple(item["labels"]), html_url=item["html_url"], day=item["day"], state=item["state"],
        ))
    return out


def rediscovery_preflight(args: argparse.Namespace) -> dict[str, Any]:
    store, audit = shared.load_store()
    retained = shared.load_retained()
    disc = discovery_scenarios(retained, store)
    test = shared.sealed_scenarios(retained)
    if len(disc) != 132 or len(test) != 30 or {s.issue_number for s in disc} & {s.issue_number for s in test}:
        raise RuntimeError("sealed issue-type cohorts are incomplete or overlap")
    payload = {
        "schema": "agent-compaction-second-model-rediscovery-preflight/v1",
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "family": "issue_type",
        "design": "A: live discovery on the second model over the sealed discovery records; compile, calibrate, and evaluate on the second model",
        "execution_status": "preflight_only",
        "provider_calls": 0,
        "real_public_records": True,
        "simulated": False,
        "protocol": {"path": str(REDISCOVERY_PROTOCOL.relative_to(ROOT)),
                     "sha256": shared.sha256_file(REDISCOVERY_PROTOCOL)},
        "source": audit,
        "model": args.model,
        "compiler": {"train": SPLIT["train"], "dev": SPLIT["dev"], "calibration": SPLIT["calibration"],
                     "task_design": TASK_DESIGN, "eligibility": "compiler_eligible (factuality_exact, allowed tools, matching issue_number)"},
        "selection": {
            "discovery": [s.issue_number for s in disc],
            "test": [s.issue_number for s in test],
            "discovery_reused_from_sealed_selection": True,
            "test_reused_from_sealed_selection": True,
            "record_numbers_sha256": hashlib.sha256(json.dumps(sorted(s.issue_number for s in test)).encode()).hexdigest(),
        },
        "conditions": list(CONDITIONS),
        "condition_order": {"method": "retained balanced six-permutation Latin order",
                            "assignments": retained["condition_order"]["primary"]["assignments"]},
        "model_settings": {"reasoning_effort": "low", "verbosity": "low", "parallel_tool_calls": False,
                           "store": False, "max_turns": 8, "timeout_s": 120,
                           "discovery_concurrency": 8,
                           "retry_policy": "held-out arms: one retry per timed-out episode, both attempts retained; discovery failures retained and excluded from eligibility"},
        "spend": {"approved_usd_required": 1.0, "expected_usd": 0.05},
    }
    REDISCOVERY_DIR.mkdir(parents=True, exist_ok=True)
    (REDISCOVERY_DIR / "preflight.json").write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
                                                    encoding="utf-8")
    return payload


async def rediscover(args: argparse.Namespace) -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    pre = rediscovery_preflight(args)
    if args.preflight_only:
        return pre
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")
    if args.approved_spend_usd is None or args.approved_spend_usd <= 0:
        raise RuntimeError("a positive --approved-spend-usd is required for a live run")
    result_path = REDISCOVERY_DIR / "results.json"
    if result_path.exists() and not args.force:
        raise RuntimeError(f"refusing to overwrite {result_path}; pass --force")
    store, _audit = shared.load_store()
    retained = shared.load_retained()
    disc_scenarios = discovery_scenarios(retained, store)
    test_scenarios = shared.sealed_scenarios(retained)

    from agents import add_trace_processor

    processor = AgentsTraceProcessor(include_sensitive_data=True, max_completed=2000)
    add_trace_processor(processor)
    catalog = fixed.make_catalog()
    tools = fixed.make_tools(store)
    manifest = fixed.make_manifest(args.model, tools, catalog, TASK_DESIGN)

    # Live discovery on the second model over the sealed 132 records.
    discovery, discovery_failures = await fixed.run_agents_batch(
        disc_scenarios, condition="discovery", repeat=0, model_name=args.model, tools=tools,
        processor=processor, manifest=manifest, catalog=catalog, registry=None, concurrency=8,
        task_design=TASK_DESIGN, source_store=store,
    )
    spent = sum(float(r.metrics.get("estimated_cost_usd") or 0.0) for r in discovery)
    checkpoint = {
        "schema": "agent-compaction-live-discovery-checkpoint/v1",
        "status": "discovery_complete_compilation_pending",
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "model": args.model, "openai_api_key_used": True, "secrets_serialized": False,
        "selection": pre["selection"],
        "aggregate": fixed.aggregate_runs(discovery),
        "failures": discovery_failures,
        "results": [r.public_dict() for r in discovery],
    }
    (REDISCOVERY_DIR / "discovery_checkpoint.json").write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    eligible = [r for r in discovery if fixed.compiler_eligible(r, TASK_DESIGN)]
    base_run = {
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "script": "paper/scripts/second_model_replication.py rediscover", "family": "issue_type",
        "model": args.model, "openai_agents_sdk": version("openai-agents"), "openai_python": version("openai"),
        "python": platform.python_version(), "platform": platform.platform(), "provider_backed": True,
        "real_public_records": True, "simulated": False, "openai_api_key_used": True,
        "secrets_serialized": False, "approved_spend_usd": args.approved_spend_usd, "protocol": pre["protocol"],
    }
    discovery_block = {
        "n": len(discovery), "failures": len(discovery_failures), "exact_traces": len(eligible),
        "needed": sum(SPLIT.values()), "aggregate": checkpoint["aggregate"],
        "tool_sequences": dict(__import__("collections").Counter(" -> ".join(r.tool_sequence) for r in discovery)),
    }
    try:
        registry, compile_record, _numbers = fixed.compile_artifact(
            discovery, catalog=catalog, manifest=manifest, train_n=SPLIT["train"], dev_n=SPLIT["dev"],
            calibration_n=SPLIT["calibration"], task_design=TASK_DESIGN,
        )
    except Exception as exc:
        payload = {
            "schema": "agent-compaction-second-model-rediscovery/v1",
            "run": {**base_run, "estimated_spend_usd": round(spent, 6), "comparative_claim_allowed": False,
                    "status": "retired_before_held_out_arms"},
            "source": pre["source"], "selection": pre["selection"], "discovery": discovery_block,
            "compiler": {"admitted": False, "stage": "compilation", "error_type": type(exc).__name__,
                         "error": str(exc)[:2000]},
            "decision_rule_reading": "H-A1 fails: a principled refusal on the second model; no held-out arm was run and no artifact is claimed.",
            "results": [], "attempts": [],
        }
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        return payload
    registry.save(REDISCOVERY_DIR / "registry")
    artifact = artifact_fingerprint(compile_record["artifact"])
    retained_art = artifact_fingerprint(retained["compiler"]["artifact"])

    macro_tools = fixed.make_macro_tool(store)
    macro_catalog = fixed.make_macro_catalog()
    macro_manifest = fixed.make_manifest(args.model, macro_tools, macro_catalog, TASK_DESIGN)
    arms = {
        "baseline": {"tools": tools, "catalog": catalog, "manifest": manifest, "registry": None},
        "compiled": {"tools": tools, "catalog": catalog, "manifest": manifest, "registry": registry},
        "macro": {"tools": macro_tools, "catalog": macro_catalog, "manifest": macro_manifest, "registry": None},
    }
    orders = pre["condition_order"]["assignments"]
    results: list[fixed.RunResult] = []
    attempts: list[dict[str, Any]] = []
    for scenario in test_scenarios:
        for condition in orders[str(scenario.issue_number)]:
            if spent > args.approved_spend_usd:
                attempts.append({"issue_number": scenario.issue_number, "condition": condition,
                                 "error": "approved spend exhausted"})
                continue
            arm = arms[condition]
            for attempt in (0, 1):
                rows, failures = await fixed.run_agents_batch(
                    [scenario], condition=condition, repeat=attempt, model_name=args.model,
                    tools=arm["tools"], processor=processor, manifest=arm["manifest"], catalog=arm["catalog"],
                    registry=arm["registry"], concurrency=1, task_design=TASK_DESIGN, source_store=store,
                )
                for failure in failures:
                    attempts.append({**failure, "attempt": attempt})
                if rows:
                    row = rows[0]
                    row.repeat = 0
                    results.append(row)
                    spent += float(row.metrics.get("estimated_cost_usd") or 0.0)
                    break
                if not any("TimeoutError" in str(f.get("error", "")) for f in failures):
                    break
            (REDISCOVERY_DIR / "evaluation_checkpoint.json").write_text(
                json.dumps({"results": [v.public_dict() for v in results], "attempts": attempts},
                           indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    grouped = {c: [r for r in results if r.condition == c] for c in CONDITIONS}
    n = len(test_scenarios)
    comparison = fixed.paired_analysis(grouped["baseline"], grouped["compiled"])
    compiled_only = comparison["quality"].get("factuality_exact", comparison["quality"]["overall"])["baseline_only_successes"]
    payload = {
        "schema": "agent-compaction-second-model-rediscovery/v1",
        "run": {**base_run, "estimated_spend_usd": round(spent, 6),
                "comparative_claim_allowed": all(len(grouped[c]) == n for c in CONDITIONS), "status": "complete"},
        "source": pre["source"], "selection": pre["selection"], "condition_order": pre["condition_order"],
        "discovery": discovery_block,
        "compiler": {
            "admitted": True, "artifact": artifact, "retained_artifact": retained_art,
            "program_identical_to_retained": artifact["program"] == retained_art["program"],
            "candidates_reaching_calibration": sum(1 for c in compile_record["candidates"] if c.get("gate") is not None),
            "report": compile_record["report"], "splits": compile_record["splits"],
            "rejection_by_stage": compile_record["rejection_by_stage"],
            "candidates": compile_record["candidates"],
        },
        "intention_to_treat": {c: {"attempted": n, "completed": len(grouped[c])} for c in CONDITIONS},
        "aggregate": fixed.aggregate_runs(results),
        "comparisons": {"baseline_vs_compiled": comparison,
                        "baseline_vs_macro": fixed.paired_analysis(grouped["baseline"], grouped["macro"], candidate_label="macro")},
        "dispatch": {"compiled_compacted": sum(int(r.dispatch.get("compacted", 0) > 0) for r in grouped["compiled"])},
        "hypotheses": {"H-A1_admitted_92_zero_violation": artifact["gate_n_accepted"] == 92 and artifact["gate_violations"] == 0,
                       "H-A2_same_program": artifact["program"] == retained_art["program"],
                       "H-A3_zero_compiled_only_failures": compiled_only == 0},
        "attempts": attempts,
        "results": [v.public_dict() for v in results],
    }
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return payload


# -------------------------------------------------------------------------- summary


def _family_block(results: dict[str, Any], baseline: str, compiled: str, manual: str) -> dict[str, Any]:
    rows = [r for r in results["results"] if int(r.get("repeat", 0)) == 0]

    def exact(row: dict[str, Any]) -> bool:
        q = row["quality"]
        return bool(q.get("factuality_exact", q.get("overall", False)))

    def totals(condition: str) -> dict[str, float]:
        sel = [r for r in rows if r["condition"] == condition]
        return {
            "n": len(sel),
            "exact": sum(exact(r) for r in sel),
            "requests": sum(float(r["metrics"]["requests"]) for r in sel),
            "total_tokens": sum(float(r["metrics"]["total_tokens"]) for r in sel),
            "wall_latency_ms": sum(float(r["metrics"]["wall_latency_ms"]) for r in sel),
            "estimated_cost_usd": sum(float(r["metrics"]["estimated_cost_usd"] or 0.0) for r in sel),
        }

    block = {"baseline": totals(baseline), "compiled": totals(compiled), "manual": totals(manual)}
    block["reductions"] = {
        key: (1.0 - block["compiled"][key] / block["baseline"][key]) if block["baseline"][key] else None
        for key in ("requests", "total_tokens", "wall_latency_ms", "estimated_cost_usd")
    }
    return block


DESIGNS = {
    "transfer": {
        "Issue-type routing": (ISSUE_DIR / "results.json", "baseline", "compiled", "macro"),
        "PR-outcome audit": (FAMILY_ROOT / "pr_outcome/gpt6_luna/results.json", "baseline", "compiled", "manual_pre_model"),
        "Backlog-attention routing": (FAMILY_ROOT / "backlog_attention/gpt6_luna/results.json", "baseline", "compiled", "manual_pre_model"),
    },
    "rediscovery": {
        "Issue-type routing": (REDISCOVERY_DIR / "results.json", "baseline", "compiled", "macro"),
        "PR-outcome audit": (FAMILY_ROOT / "pr_outcome/gpt6_luna_rediscovery/results.json", "baseline", "compiled", "manual_pre_model"),
        "Backlog-attention routing": (FAMILY_ROOT / "backlog_attention/gpt6_luna_rediscovery/results.json", "baseline", "compiled", "manual_pre_model"),
    },
}


def _collect(sources: dict[str, tuple[Path, str, str, str]]) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    families = []
    for name, (path, b, c, m) in sources.items():
        failure = path.parent / "failure.json"
        if not path.exists() and failure.exists():
            # The family harness raises before the held-out arms when discovery yields fewer
            # exact traces than the split needs; the failure record carries the counts.
            data = json.loads(failure.read_text(encoding="utf-8"))
            families.append({
                "family": name, "status": "retired", "model": data.get("model"),
                "source": str(failure.relative_to(ROOT)), "source_sha256": shared.sha256_file(failure),
                "discovery": data.get("discovery"), "compiler": {"admitted": False, "stage": data.get("stage"), "error": data.get("error")},
            })
            continue
        if not path.exists():
            families.append({"family": name, "status": "not_run", "source": str(path.relative_to(ROOT))})
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("compiler", {}).get("admitted") is False or data["run"].get("status") == "retired_before_held_out_arms":
            families.append({
                "family": name, "status": "retired", "model": data["run"]["model"],
                "source": str(path.relative_to(ROOT)), "source_sha256": shared.sha256_file(path),
                "discovery": data.get("discovery"), "compiler": data.get("compiler"),
            })
            continue
        block = _family_block(data, b, c, m)
        block.update({
            "family": name,
            "status": "complete" if data["run"].get("comparative_claim_allowed") else "incomplete",
            "model": data["run"]["model"],
            "source": str(path.relative_to(ROOT)),
            "source_sha256": shared.sha256_file(path),
        })
        art = (data.get("compiler") or {}).get("artifact") or {}
        if art:
            block["artifact_id"] = art.get("artifact_id")
            block["program_identical_to_retained"] = (data.get("compiler") or {}).get("program_identical_to_retained")
            block["candidates_reaching_calibration"] = (data.get("compiler") or {}).get("candidates_reaching_calibration")
        families.append(block)
    complete = [f for f in families if f.get("status") == "complete"]
    overall = None
    if complete:
        overall = {
            "n": sum(f["baseline"]["n"] for f in complete),
            "baseline_exact": sum(f["baseline"]["exact"] for f in complete),
            "compiled_exact": sum(f["compiled"]["exact"] for f in complete),
            "manual_exact": sum(f["manual"]["exact"] for f in complete),
        }
        for key in ("requests", "total_tokens", "wall_latency_ms", "estimated_cost_usd"):
            b = sum(f["baseline"][key] for f in complete)
            c = sum(f["compiled"][key] for f in complete)
            overall[key] = {"baseline": b, "compiled": c, "reduction": (1.0 - c / b) if b else None}
    return families, overall


def _table_rows(families: list[dict[str, Any]], overall: dict[str, Any] | None) -> list[str]:
    lines = []
    for f in families:
        if f.get("status") == "retired":
            d = f.get("discovery") or {}
            lines.append(f"\\quad {f['family']} & \\multicolumn{{7}}{{l}}{{\\textsc{{retire}} at compile time ({d.get('exact_traces', '?')}/{d.get('n', '?')} exact discovery traces)}} \\\\")
            continue
        if f.get("status") != "complete":
            lines.append(f"\\quad {f['family']} & \\multicolumn{{7}}{{l}}{{not run}} \\\\")
            continue
        r = f["reductions"]
        lines.append(
            f"\\quad {f['family']} & {f['baseline']['exact']}/{f['baseline']['n']} & "
            f"\\textbf{{{f['compiled']['exact']}/{f['compiled']['n']}}} & {f['manual']['exact']}/{f['manual']['n']} & & "
            f"{100*r['requests']:.1f} & {100*r['total_tokens']:.1f} & {100*r['estimated_cost_usd']:.1f} \\\\"
        )
    complete = [f for f in families if f.get("status") == "complete"]
    if overall and complete and len(complete) == len(families):
        lines.append(
            f"\\quad Weighted total ($n={overall['n']}$) & {overall['baseline_exact']}/{overall['n']} & "
            f"\\textbf{{{overall['compiled_exact']}/{overall['n']}}} & {overall['manual_exact']}/{overall['n']} & & "
            f"{100*overall['requests']['reduction']:.1f} & {100*overall['total_tokens']['reduction']:.1f} & "
            f"{100*overall['estimated_cost_usd']['reduction']:.1f} \\\\")
    return lines


def summarize(args: argparse.Namespace) -> dict[str, Any]:
    families, overall = _collect(DESIGNS["transfer"])
    families_a, overall_a = _collect(DESIGNS["rediscovery"])
    complete = [f for f in families if f.get("status") == "complete"]
    payload = {
        "schema": "agent-compaction-second-model-summary/v2",
        "model": args.model,
        "families": families,
        "overall": overall,
        "rediscovery": {"families": families_a, "overall": overall_a},
        "claim_boundary": (
            "Same sealed records, discovery traces, and splits as the gpt-5.6-luna studies; "
            "artifacts recompiled provider-free under the second-model manifest pin; held-out "
            "arms executed live on the second model. A transfer of the guarded pipeline to a "
            "second model family on the same cohorts, not an independent sample."
        ),
    }
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                                           encoding="utf-8")
    if complete:
        lines = [
            r"\begin{tabular}{@{}lccccccc@{}}", r"\toprule",
            r"& \multicolumn{3}{c}{Exact held-out contract} & & \multicolumn{3}{c}{Reduction (\%)} \\",
            r"\cmidrule(lr){2-4}\cmidrule(lr){6-8}",
            r"Family & Base & Compiled & Manual & & Requests & Tokens & Cost \\", r"\midrule",
            r"\multicolumn{8}{@{}l}{\emph{Transfer (design B): retained artifacts recompiled under the new pin}} \\",
        ]
        lines += _table_rows(families, overall)
        if any(f.get("status") != "not_run" for f in families_a):
            lines += [r"\addlinespace[2pt]",
                      r"\multicolumn{8}{@{}l}{\emph{Re-discovery (design A): the pipeline run on the second model's own traces}} \\"]
            lines += _table_rows(families_a, overall_a)
        lines += [r"\bottomrule", r"\end{tabular}"]
        TABLE_PATH.write_text(
            "% generated by paper/scripts/second_model_replication.py summarize; do not edit\n"
            + "\n".join(lines) + "\n", encoding="utf-8")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "run", "rediscover", "summarize"))
    parser.add_argument("--model", default="gpt-6-luna")
    parser.add_argument("--approved-spend-usd", type=float)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "preflight":
        payload = preflight(args)
        print(json.dumps({k: v for k, v in payload.items() if k not in ("selection", "condition_order")},
                         indent=2, sort_keys=True, default=str))
    elif args.command == "run":
        payload = asyncio.run(run(args))
        print(json.dumps({k: payload[k] for k in ("run", "intention_to_treat", "aggregate", "dispatch")},
                         indent=2, sort_keys=True, default=str))
    elif args.command == "rediscover":
        payload = asyncio.run(rediscover(args))
        keys = [k for k in ("run", "discovery", "intention_to_treat", "aggregate", "dispatch", "hypotheses",
                            "decision_rule_reading", "execution_status", "selection") if k in payload]
        shown = {k: payload[k] for k in keys}
        if "compiler" in payload:
            shown["compiler"] = {k: v for k, v in payload["compiler"].items() if k not in ("report", "candidates", "splits")}
        print(json.dumps(shown, indent=2, sort_keys=True, default=str))
    else:
        payload = summarize(args)
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
