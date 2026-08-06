#!/usr/bin/env python3
"""Provider-free validation of Guarded Composite Synthesis on real traces.

The input is the sealed 132-run OpenAI discovery checkpoint used by the paper.
Those provider-produced tool choices and arguments are reconstructed into typed
episodes; tool outputs are recomputed from the pinned public GitHub snapshot.  The
script performs no provider calls and does not claim a new live comparison.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "paper" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "paper" / "scripts"))

import github_live_study as fixed  # noqa: E402
import github_natural_workflow_study as natural  # noqa: E402
from guarded_agentic_compaction.paths import content_digest  # noqa: E402
from guarded_agentic_compaction.runtime.dispatch import DispatchMode, Dispatcher  # noqa: E402
from guarded_agentic_compaction.runtime.runner import CompactingRunner  # noqa: E402
from guarded_agentic_compaction.schema.artifacts import Lifecycle  # noqa: E402
from guarded_agentic_compaction.schema.traces import (  # noqa: E402
    Episode,
    EventKind,
    EventNode,
    OutcomeLabels,
    TraceEnvelope,
)


DEFAULT_CHECKPOINT = ROOT / "paper/results/github_natural_replication/discovery_checkpoint.json"
DEFAULT_REGRADED = ROOT / "paper/results/github_natural_replication/results.json"
DEFAULT_OUTPUT = ROOT / "paper/results/gcs_validation/provider_free.json"


def execute_snapshot(store: dict[int, dict[str, Any]], tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    number = int(arguments["issue_number"])
    item = store.get(number)
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
        comments = item["comments"] if item is not None else []
        limit = int(arguments["limit"])
        return {
            "source_revision": fixed.HF_REVISION,
            "thread": {
                "total": len(comments),
                "items": [comment[:800] for comment in comments[: max(0, min(limit, 3))]],
            },
        }
    raise KeyError(tool)


def _episode_from_checkpoint(
    row: dict[str, Any],
    *,
    store: dict[int, dict[str, Any]],
    manifest: Any,
) -> Episode:
    number = int(row["issue_number"])
    item = store[number]
    events: list[EventNode] = []
    for step, (tool, arguments) in enumerate(zip(row["tool_sequence"], row["tool_arguments"])):
        base = len(events)
        call_id = f"checkpoint-{number}-{step}"
        events.extend(
            [
                EventNode(f"{call_id}-request", EventKind.MODEL_REQ, base),
                EventNode(f"{call_id}-response", EventKind.MODEL_RESP, base + 1),
                EventNode(
                    f"{call_id}-call",
                    EventKind.TOOL_CALL,
                    base + 2,
                    tool=tool,
                    input=dict(arguments),
                    call_id=call_id,
                    declared_effect="READ_LOCAL",
                ),
                EventNode(
                    f"{call_id}-result",
                    EventKind.TOOL_RESULT,
                    base + 3,
                    tool=tool,
                    output=execute_snapshot(store, tool, dict(arguments)),
                    call_id=call_id,
                ),
            ]
        )
    base = len(events)
    events.extend(
        [
            EventNode(f"checkpoint-{number}-final-request", EventKind.MODEL_REQ, base),
            EventNode(f"checkpoint-{number}-final-response", EventKind.MODEL_RESP, base + 1),
        ]
    )
    envelope = TraceEnvelope(
        trace_id=str(row["trace_id"]),
        episode_id=f"gcs-checkpoint-{number}",
        group_id=f"github-issue:{number}",
        manifest_id=manifest.manifest_id,
        principal="public-benchmark-runner",
        tenant_partition="public:huggingface-datasets",
        policy_version="github-natural-v1",
        day=item["day"],
        privacy_class="public_dataset_provider_trace",
        entry_state_ref=content_digest({"issue_number": number}),
        external_state_version=fixed.HF_REVISION,
    )
    quality = dict(row["quality"])
    return Episode(
        envelope=envelope,
        manifest=manifest,
        entry_state={"issue_number": number},
        events=events,
        outcome=OutcomeLabels(
            task_success=bool(quality.get("factuality_exact")),
            semantic_score=float(quality.get("score", 0.0)),
        ),
        final_state_digest=fixed.HF_PARQUET_SHA256,
        attributes={
            "real_public_record": True,
            "provider_backed_source_trace": True,
            "reconstructed_from_sealed_checkpoint": True,
            "label_count": len(item["labels"]),
            "category": fixed.category_for(item["labels"]),
            "state": item["state"],
        },
    )


def reconstruct_runs(
    checkpoint: dict[str, Any],
    *,
    store: dict[int, dict[str, Any]],
    manifest: Any,
) -> list[fixed.RunResult]:
    runs: list[fixed.RunResult] = []
    for row in checkpoint["results"]:
        episode = _episode_from_checkpoint(row, store=store, manifest=manifest)
        runs.append(
            fixed.RunResult(
                condition="discovery",
                repeat=0,
                issue_number=int(row["issue_number"]),
                trace_id=str(row["trace_id"]),
                metrics=dict(row.get("metrics", {})),
                answer=dict(row.get("answer", {})),
                quality=dict(row["quality"]),
                tool_sequence=list(row["tool_sequence"]),
                tool_arguments=[dict(value) for value in row["tool_arguments"]],
                dispatch=dict(row.get("dispatch", {})),
                episode=episode,
            )
        )
    return runs


def expected_projection(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "issue_number": item["number"],
        "title": item["title"][:500],
        "state": item["state"],
        "body_excerpt": item["body"][:2400],
        "labels": list(item["labels"]),
        "comments": [comment[:800] for comment in item["comments"][:3]],
        "source_revision": fixed.HF_REVISION,
    }


def validate(args: argparse.Namespace) -> dict[str, Any]:
    checkpoint = json.loads(Path(args.checkpoint).read_text(encoding="utf-8"))
    regraded = json.loads(Path(args.regraded_results).read_text(encoding="utf-8"))
    quality_by_trace = {
        str(row["trace_id"]): dict(row["quality"])
        for row in regraded["results"]
        if row.get("condition") == "discovery"
    }
    checkpoint = dict(checkpoint)
    checkpoint["results"] = [
        {**row, "quality": quality_by_trace.get(str(row["trace_id"]), row["quality"])}
        for row in checkpoint["results"]
    ]
    frame = pd.read_parquet(fixed.DATA_PATH)
    store, _duplicates = fixed.build_store(frame)
    tools = fixed.make_tools(store)
    catalog = natural.make_catalog()
    model = str(checkpoint["run"]["resolved_config"]["model"])
    manifest = natural.make_manifest(model, tools, catalog, "base")
    runs = reconstruct_runs(checkpoint, store=store, manifest=manifest)
    registry, compilation = natural.compile_artifact(
        runs,
        catalog=catalog,
        manifest=manifest,
        train_n=args.train_cases,
        dev_n=args.dev_cases,
        calibration_n=args.calibration_cases,
    )
    artifact = registry.artifacts[0]
    artifact.lifecycle = Lifecycle.ACTIVE
    program = artifact.program
    if program is None or program.composite is None:
        raise RuntimeError(
            "compiler did not emit a guarded composite:\n"
            + str(compilation.get("report", ""))
            + "\n"
            + json.dumps(compilation.get("candidates", []), indent=2, default=str)[:8000]
        )
    if len(program.call_steps()) != 3:
        raise RuntimeError(f"expected complete three-read region, got {len(program.call_steps())}")

    dispatcher = Dispatcher(registry=registry, catalog=catalog, mode=DispatchMode.LIVE)
    runner = CompactingRunner(dispatcher=dispatcher, catalog=catalog, manifest=manifest)
    exact = 0
    dispatched = 0
    fallback = 0
    failures: list[dict[str, Any]] = []
    for run in runs:
        result = runner.execute_pre_model(
            {"issue_number": run.issue_number},
            executor=lambda tool, values, _store=store: execute_snapshot(_store, tool, values),
            day=store[run.issue_number]["day"],
        )
        if not result.compacted:
            fallback += 1
            continue
        dispatched += 1
        actual = result.observations[0].result
        expected = expected_projection(store[run.issue_number])
        if actual == expected:
            exact += 1
        else:
            failures.append(
                {
                    "issue_number": run.issue_number,
                    "actual_digest": content_digest(actual),
                    "expected_digest": content_digest(expected),
                }
            )

    payload = {
        "schema": "agent-compaction-gcs-provider-free-validation/v1",
        "evidence_class": "sealed real-provider tool traces + pinned public records + local replay",
        "provider_calls_executed": 0,
        "source_checkpoint": str(Path(args.checkpoint).relative_to(ROOT)),
        "source_checkpoint_digest": fixed.sha256(Path(args.checkpoint)),
        "regraded_results": str(Path(args.regraded_results).relative_to(ROOT)),
        "regraded_results_digest": fixed.sha256(Path(args.regraded_results)),
        "source_provider_trace_count": len(runs),
        "compiler": {
            "complete_region_steps": len(program.call_steps()),
            "internal_tools": list(program.tools),
            "composite_name": program.composite.name,
            "exposed_interfaces": 1,
            "projection_fields": sorted(program.composite.projection),
            "artifact_id": artifact.artifact_id,
            "artifact_digest": artifact.body_digest(),
            "report": compilation["report"],
            "config": compilation["config"],
        },
        "replay": {
            "attempted": len(runs),
            "dispatched": dispatched,
            "fallback": fallback,
            "exact_projected_matches": exact,
            "projection_failures": failures,
            "all_dispatched_exact": exact == dispatched and not failures,
        },
        "limitations": [
            "No new provider call was executed by this validation.",
            "Reconstructed episodes preserve sealed provider tool choices and arguments but not hidden reasoning text.",
            "A live paired GCS-versus-macro run is required for token, latency, cost, and answer-quality claims.",
        ],
        "resolved_arguments": vars(args),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--regraded-results", type=Path, default=DEFAULT_REGRADED)
    parser.add_argument("--train-cases", type=int, default=16)
    parser.add_argument("--dev-cases", type=int, default=8)
    parser.add_argument("--calibration-cases", type=int, default=92)
    return parser.parse_args()


if __name__ == "__main__":
    result = validate(parse_args())
    print(json.dumps({"compiler": result["compiler"], "replay": result["replay"]}, indent=2))
