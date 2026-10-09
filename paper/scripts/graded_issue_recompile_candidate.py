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

OUT = ROOT / "paper/results/graded_issue_gate/candidate_v2"
PRIOR = ROOT / "paper/results/github_natural_live/results.json"
ABORT = ROOT / "paper/results/graded_issue_gate/abort_v1.json"
MODEL = "gpt-5.6-luna"


async def run(cap: float) -> dict:
    if not 0 < cap <= 200:
        raise ValueError("authorized ceiling is $200")
    load_dotenv(ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY unavailable")
    if OUT.exists():
        raise RuntimeError("candidate_v2 already exists; no automatic rerun")
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
    OUT.mkdir(parents=True)
    (OUT / "started.json").write_text(json.dumps({
        "schema": "gac-graded-issue-candidate-start/v2", "source_study": str(PRIOR.relative_to(ROOT)),
        "discovery_issue_numbers": numbers, "manifest_id": manifest.manifest_id,
        "new_cohort_overlap": 0, "approved_cap_usd": cap,
    }, indent=2) + "\n")
    discovery, failures = await natural.run_batch(
        scenarios, condition="v2_discovery", repeat=0, model_name=MODEL,
        tools=tools, processor=processor, manifest=manifest, catalog=catalog,
        store=store, registry=None, concurrency=4,
    )
    raw = {"schema": "gac-graded-issue-candidate-discovery/v2",
           "source_manifest_sha256": cohort.sha256(cohort.prior.SOURCE_MANIFEST),
           "manifest_id": manifest.manifest_id, "failures": failures,
           "results": [{**r.public_dict(), "episode": r.episode.to_dict()} for r in discovery]}
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
    args = parser.parse_args()
    result = asyncio.run(run(args.approved_spend_usd))
    print(json.dumps({key: result[key] for key in ("status", "artifact_id", "quality_passes", "estimated_cost_usd")}, indent=2))


if __name__ == "__main__":
    main()
