#!/usr/bin/env python3
"""Sanitize selected official tau2/tau3 live-provider simulations for publication."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
REVISION = "1eceb0453fe2effa1ba26b6a51fc52b966944ec1"
DEFAULT_OUT = ROOT / "paper/results/external_benchmarks/tau2_live.json"
RUNS = {
    "airline": "gac_airline_task1",
    "retail": "gac_retail_task100",
    "telecom": "gac_telecom_one",
    "banking_knowledge": "gac_banking_task010",
}


def _task_hash(domain: str, task_id: Any) -> str:
    return hashlib.sha256(f"{domain}:{task_id}".encode()).hexdigest()


def _safe_simulation(domain: str, simulation: Mapping[str, Any]) -> dict[str, Any]:
    reward_info = simulation.get("reward_info") or {}
    action_checks = reward_info.get("action_checks") or []
    action_counts: Counter[str] = Counter()
    for item in action_checks:
        kind = str(item.get("tool_type") or "unknown")
        action_counts[f"{kind}_expected"] += 1
        action_counts[f"{kind}_matched"] += bool(item.get("action_match"))
    message_counts: Counter[str] = Counter()
    prompt_tokens = completion_tokens = provider_requests = tool_calls = 0
    for message in simulation.get("messages") or []:
        message_counts[str(message.get("role") or "unknown")] += 1
        usage = message.get("usage") or {}
        if usage:
            provider_requests += 1
            prompt_tokens += int(usage.get("prompt_tokens") or 0)
            completion_tokens += int(usage.get("completion_tokens") or 0)
        calls = message.get("tool_calls") or []
        tool_calls += len(calls) if isinstance(calls, list) else 0
    db_check = reward_info.get("db_check") or {}
    return {
        "domain": domain,
        "task_hash": _task_hash(domain, simulation.get("task_id")),
        "trial": simulation.get("trial"),
        "duration_seconds": simulation.get("duration"),
        "termination_reason": simulation.get("termination_reason"),
        "reward": reward_info.get("reward"),
        "db_match": db_check.get("db_match"),
        "agent_cost_usd": simulation.get("agent_cost"),
        "user_cost_usd": simulation.get("user_cost"),
        "action_counts": dict(sorted(action_counts.items())),
        "message_counts": dict(sorted(message_counts.items())),
        "provider_requests_with_usage": provider_requests,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "tool_calls": tool_calls,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    tau_root = args.source_root / "tau2"
    records: list[dict[str, Any]] = []
    for domain, name in RUNS.items():
        source = tau_root / "data" / "simulations" / name / "results.json"
        if not source.is_file():
            raise SystemExit(f"missing sealed simulation output for {domain}")
        payload = json.loads(source.read_text())
        if (payload.get("info") or {}).get("git_commit") != REVISION:
            raise SystemExit(f"tau2 revision mismatch for {domain}")
        simulations = payload.get("simulations") or []
        if len(simulations) != 1:
            raise SystemExit(f"expected exactly one bounded simulation for {domain}")
        records.append(_safe_simulation(domain, simulations[0]))

    totals: Counter[str] = Counter()
    for record in records:
        totals["simulations"] += 1
        totals["passed"] += record["reward"] == 1.0
        totals["provider_requests_with_usage"] += record["provider_requests_with_usage"]
        totals["prompt_tokens"] += record["prompt_tokens"]
        totals["completion_tokens"] += record["completion_tokens"]
        totals["tool_calls"] += record["tool_calls"]
    agent_cost = sum(float(item["agent_cost_usd"] or 0) for item in records)
    user_cost = sum(float(item["user_cost_usd"] or 0) for item in records)
    report = {
        "schema": "agent-compaction-external-live-evaluation/v1",
        "benchmark": "tau2/tau3 text benchmark",
        "source_revision": REVISION,
        "source_version": "1.0.1",
        "models": {"agent": "gpt-4.1-mini", "user_simulator": "gpt-4.1-mini"},
        "selection": {
            "scope": "one predeclared task from each accessible text domain",
            "trials_per_task": 1,
            "seed": 20260804,
            "not_official_leaderboard_submission": True,
        },
        "aggregate": {
            **dict(totals),
            "pass_rate": totals["passed"] / totals["simulations"],
            "agent_cost_usd": agent_cost,
            "user_simulator_cost_usd": user_cost,
            "total_reported_cost_usd": agent_cost + user_cost,
            "total_tokens": totals["prompt_tokens"] + totals["completion_tokens"],
        },
        "simulations": records,
        "evidence": {
            "class": "official simulated environments with real OpenAI provider calls",
            "is_real_world_demo": False,
            "compiler_execution": False,
            "gac_disposition": "reference actions screened only; incomplete tool results cannot be compiled",
            "prompts_messages_arguments_outputs_serialized": False,
            "credential_serialized": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
