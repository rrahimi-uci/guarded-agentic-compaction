#!/usr/bin/env python3
"""Sanitize one bounded official ToolSandbox live-provider execution.

The upstream trajectory contains messages and tool values.  This publication artifact
retains only structural counts and official scores, and never copies those values.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REVISION = "165848b9a78cead7ca7fe7c89c688b58e6501219"
SCENARIO = "search_message_with_recency_oldest"
DEFAULT_OUT = ROOT / "paper/results/external_benchmarks/toolsandbox_live.json"
DOCKERFILE = ROOT / "benchmarks/external/envs/toolsandbox.Dockerfile"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    summaries = sorted(args.run_root.glob("*/result_summary.json"))
    if len(summaries) != 1:
        raise SystemExit(f"expected exactly one ToolSandbox result, found {len(summaries)}")
    payload = json.loads(summaries[0].read_text(encoding="utf-8"))
    if payload.get("git_sha") != REVISION:
        raise SystemExit("ToolSandbox revision mismatch")
    scenarios = payload.get("per_scenario_results") or []
    if len(scenarios) != 1 or scenarios[0].get("name") != SCENARIO:
        raise SystemExit("unexpected ToolSandbox scenario selection")
    scenario = scenarios[0]
    if scenario.get("traceback") or scenario.get("exception_type"):
        raise SystemExit("ToolSandbox scenario did not execute cleanly")
    conversation_path = summaries[0].parent / "trajectories" / SCENARIO / "conversation.json"
    conversation: list[dict[str, Any]] = json.loads(
        conversation_path.read_text(encoding="utf-8")
    )
    roles = Counter(str(item.get("role") or "unknown") for item in conversation)
    tool_calls = sum(
        len(item.get("tool_calls") or [])
        for item in conversation
        if isinstance(item.get("tool_calls"), list)
    )
    report = {
        "schema": "agent-compaction-external-live-evaluation/v1",
        "benchmark": "ToolSandbox",
        "source_revision": REVISION,
        "source_license": "Apple sample-code license with bundled acknowledgements",
        "selection": {
            "scenario": SCENARIO,
            "scenarios": 1,
            "seed": 42,
            "not_official_leaderboard_submission": True,
        },
        "models": {
            "agent": "gpt-4o-2024-05-13",
            "user_simulator": "gpt-4o-2024-05-13",
        },
        "aggregate": {
            "scenarios": 1,
            "milestone_similarity": scenario["milestone_similarity"],
            "minefield_similarity": scenario["minefield_similarity"],
            "similarity": scenario["similarity"],
            "turn_count": scenario["turn_count"],
            "conversation_messages": len(conversation),
            "message_roles": dict(sorted(roles.items())),
            "assistant_messages": roles["assistant"],
            "tool_calls": tool_calls,
            "provider_requests": None,
            "provider_tokens": None,
            "provider_accounting_note": (
                "The pinned upstream harness does not retain token usage; assistant-message "
                "count is reported but is not relabeled as exact provider requests."
            ),
        },
        "runtime_contract": {
            "container_architecture": "linux/arm64",
            "python": "3.11",
            "base_image": (
                "python@sha256:1c06f14f1f45c37c7ba0563077e651f288b728eb4a227db32da92b52794ddb3e"
            ),
            "compatibility_pin": "httpx==0.27.2",
            "dockerfile": "benchmarks/external/envs/toolsandbox.Dockerfile",
            "dockerfile_sha256": _sha256(DOCKERFILE),
            "upstream_packaging_findings": [
                "ccy==1.3.1 declares Python <3.12 although the project declares Python <=3.12",
                "openai==1.17.0 is incompatible with current httpx unless httpx is pinned below 0.28",
                "the result writer invokes git but git is not declared as a runtime dependency",
            ],
        },
        "evidence": {
            "class": "official simulated environment with real OpenAI provider calls",
            "is_real_world_demo": False,
            "compiler_execution": False,
            "official_full_benchmark_score": False,
            "gac_disposition": (
                "reference actions screened only; the raw live trajectory remains outside "
                "the repository and is not licensed as replay-safe compiler evidence"
            ),
            "prompts_messages_arguments_outputs_serialized": False,
            "credential_serialized": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
