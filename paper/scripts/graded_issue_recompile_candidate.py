"""Re-derive a compatible issue artifact from prior discovery records only.

This is the declared v2 repair for the aborted graded-issue gate study. None of
the 474 new cohort issues is used to compile the candidate. Provider calls are
made only for the original natural-workflow discovery split.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src", ROOT / "paper/scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import graded_issue_gate_preflight as cohort  # noqa: E402
import github_live_study as fixed  # noqa: E402
import github_natural_workflow_study as natural  # noqa: E402
from guarded_agentic_compaction.capture.agents_sdk import AgentsTraceProcessor  # noqa: E402
from guarded_agentic_compaction.schema.traces import Episode, content_digest  # noqa: E402

OUT = ROOT / "paper/results/graded_issue_gate/candidate_v2"
PRIOR = ROOT / "paper/results/github_natural_live/results.json"
ABORT = ROOT / "paper/results/graded_issue_gate/abort_v1.json"
MODEL = "gpt-5.6-luna"


def redact_episode(episode: dict) -> tuple[dict, int, int]:
    """Remove opaque provider reasoning while keeping compiler evidence intact."""
    import copy

    episode = copy.deepcopy(episode)
    reasoning_items = 0
    encrypted_fields = 0

    def visit(value: object) -> None:
        nonlocal encrypted_fields
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "encrypted_content" and item is not None:
                    value[key] = None
                    encrypted_fields += 1
                else:
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(episode)
    for event in episode["events"]:
        if event["kind"] == "MODEL_RESP" and isinstance(event["output"], list):
            for i, item in enumerate(event["output"]):
                if isinstance(item, str) and "encrypted_content=" in item:
                    event["output"][i] = "REDACTED_REASONING_ITEM"
                    reasoning_items += 1
    return episode, reasoning_items, encrypted_fields


async def run(cap: float, *, from_saved: bool = False) -> dict:
    if not 0 < cap <= 200:
        raise ValueError("authorized ceiling is $200")
    if from_saved:
        if not (OUT / "discovery.json").exists() or (OUT / "summary.json").exists():
            raise RuntimeError("saved discovery missing or candidate already compiled")
    elif OUT.exists():
        raise RuntimeError("candidate_v2 already exists; no automatic provider rerun")
    else:
        load_dotenv(ROOT / ".env")
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY unavailable")
    if not ABORT.exists():
        raise RuntimeError("aborted attempt must be recorded first")
    aborted = json.loads(ABORT.read_text())
    if aborted["estimated_cost_usd"] + aborted["interrupted_batch_reserve_usd"] + 80 > cap:
        raise RuntimeError("spend guard stopped before provider calls")
    if cohort.build() != json.loads(cohort.OUT.read_text()):
        raise RuntimeError("cohort/source drift")
    original = json.loads(PRIOR.read_text())
    numbers = original["selection"]["discovery_issue_numbers"]
    fresh = {r["issue_number"] for rows in json.loads(cohort.OUT.read_text())["selected"].values() for r in rows}
    if len(numbers) != 80 or len(set(numbers)) != 80 or fresh & set(numbers):
        raise RuntimeError("original discovery split is not disjoint from new cohort")
    store, _ = fixed.build_store(pd.read_parquet(fixed.DATA_PATH))
    tools = fixed.make_tools(store)
    catalog = natural.make_catalog()
    manifest = natural.make_manifest(MODEL, tools, catalog, "base")
    from agents import add_trace_processor
    processor = AgentsTraceProcessor(include_sensitive_data=True, max_completed=1000)
    add_trace_processor(processor)
    scenarios = [fixed.Scenario(
        issue_number=n, category=fixed.category_for(store[n]["labels"]),
        labels=tuple(store[n]["labels"]), html_url=store[n]["html_url"],
        day=store[n]["day"], state=store[n]["state"],
    ) for n in numbers]
    if from_saved:
        raw = json.loads((OUT / "discovery.json").read_text())
        if (raw["manifest_id"] != manifest.manifest_id or raw["source_manifest_sha256"] !=
                cohort.sha256(cohort.prior.SOURCE_MANIFEST)):
            raise RuntimeError("saved discovery provenance differs from current source or manifest")
        failures = raw["failures"]
        discovery = [fixed.RunResult(
            condition="discovery", repeat=int(row["repeat"]), issue_number=int(row["issue_number"]),
            trace_id=row["trace_id"], metrics=row["metrics"], answer=row["answer"],
            quality=row["quality"], tool_sequence=row["tool_sequence"],
            tool_arguments=row["tool_arguments"], dispatch=row["dispatch"],
            episode=Episode.from_dict(row["episode"]),
        ) for row in raw["results"]]
        if {r.issue_number for r in discovery} != set(numbers):
            raise RuntimeError("saved discovery does not match original split")
    else:
        OUT.mkdir(parents=True)
        (OUT / "started.json").write_text(json.dumps({
            "schema": "gac-graded-issue-candidate-start/v2", "source_study": str(PRIOR.relative_to(ROOT)),
            "discovery_issue_numbers": numbers, "manifest_id": manifest.manifest_id,
            "new_cohort_overlap": 0, "approved_cap_usd": cap,
        }, indent=2) + "\n")
        discovery, failures = await natural.run_batch(
            scenarios, condition="discovery", repeat=0, model_name=MODEL,
            tools=tools, processor=processor, manifest=manifest, catalog=catalog,
            store=store, registry=None, concurrency=4,
        )
        retained = []
        reasoning_count = encrypted_count = 0
        for result in discovery:
            episode, n_reasoning, n_encrypted = redact_episode(result.episode.to_dict())
            reasoning_count += n_reasoning
            encrypted_count += n_encrypted
            retained.append({**result.public_dict(), "episode": episode,
                             "redacted_episode_digest": content_digest(episode)})
        raw = {"schema": "gac-graded-issue-candidate-discovery/v2",
               "source_manifest_sha256": cohort.sha256(cohort.prior.SOURCE_MANIFEST),
               "manifest_id": manifest.manifest_id, "failures": failures,
               "reasoning_items_redacted": reasoning_count,
               "encrypted_content_fields_redacted": encrypted_count,
               "redaction": "Opaque provider reasoning items and encrypted_content fields were removed.",
               "results": retained}
        (OUT / "discovery.json").write_text(json.dumps(raw, indent=2, sort_keys=True, default=str) + "\n")
    if failures or len(discovery) != 80:
        raise RuntimeError("incomplete discovery; no automatic retry")
    registry, compilation = natural.compile_artifact(
        discovery, catalog=catalog, manifest=manifest,
        train_n=20, dev_n=10, calibration_n=45,
    )
    if not registry.resolve(manifest.compatibility_key(), {}, kind="grc"):
        raise RuntimeError("recompiled artifact does not resolve under live manifest")
    registry.save(OUT / "registry")
    summary = {"schema": "gac-graded-issue-candidate/v2", "status": "admitted",
               "manifest_id": manifest.manifest_id, "compatibility_key": manifest.compatibility_key(),
               "artifact_id": registry.artifacts[0].artifact_id,
               "discovery_groups": 80, "quality_passes": sum(r.quality["overall"] for r in discovery),
               "estimated_cost_usd": sum(float(r.metrics["estimated_cost_usd"] or 0) for r in discovery),
               "compiler": compilation}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-spend-usd", type=float, required=True)
    parser.add_argument("--from-saved", action="store_true", help="compile retained discovery without a provider call")
    args = parser.parse_args()
    result = asyncio.run(run(args.approved_spend_usd, from_saved=args.from_saved))
    print(json.dumps({key: result[key] for key in ("status", "artifact_id", "quality_passes", "estimated_cost_usd")}, indent=2))


if __name__ == "__main__":
    main()
