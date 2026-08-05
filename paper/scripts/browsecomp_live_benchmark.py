#!/usr/bin/env python3
"""Bounded live-web BrowseComp evaluation with no task or response disclosure.

The sealed encrypted CSV is decrypted only in memory using the canary carried by each
row.  The agent uses the Responses API hosted web-search tool and the answer is scored
with the pinned official simple-evals grader prompt.  Stored artifacts contain hashes,
booleans, timing, usage, and tool counts—never questions, answers, search results, model
responses, canaries, or API credentials.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import random
import re
import time
from pathlib import Path
from typing import Any

from openai import OpenAI


ROOT = Path(__file__).resolve().parents[2]
DATA_SHA256 = "7b24471cd5b3eb2a46830a14802b5c029ea62f488ff75a0f88af7923d1454abf"
HARNESS_REVISION = "652c89d0ca9df547706735883097e9537d40dc47"
DEFAULT_OUT = ROOT / "paper/results/external_benchmarks/browsecomp_live.json"

QUERY_TEMPLATE = """
{Question}

Your response should be in the following format:
Explanation: {{your explanation for your final answer}}
Exact Answer: {{your succinct, final answer}}
Confidence: {{your confidence score between 0% and 100% for your answer}}
""".strip()

GRADER_TEMPLATE = """
Judge whether the following [response] to [question] is correct or not based on the precise and unambiguous [correct_answer] below.

[question]: {question}

[response]: {response}

Your judgement must contain a line exactly matching `correct: yes` or `correct: no`. Extract the final exact answer from the response and compare only whether it matches [correct_answer].

[correct_answer]: {correct_answer}
""".strip()


def _load_repository_env() -> None:
    path = ROOT / ".env"
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _decrypt(ciphertext: str, password: str) -> str:
    encrypted = base64.b64decode(ciphertext)
    block = hashlib.sha256(password.encode()).digest()
    key = block * (len(encrypted) // len(block)) + block[: len(encrypted) % len(block)]
    return bytes(left ^ right for left, right in zip(encrypted, key)).decode()


def _usage(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    return {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }


def _tool_counts(response: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in getattr(response, "output", ()):
        kind = str(getattr(item, "type", "unknown"))
        counts[kind] = counts.get(kind, 0) + 1
    return dict(sorted(counts.items()))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--examples", type=int, default=3)
    parser.add_argument("--agent-model", default="gpt-5.6")
    parser.add_argument("--grader-model", default="gpt-4.1-mini")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if not 1 <= args.examples <= 20:
        raise SystemExit("examples must be in [1, 20] for this bounded study")
    _load_repository_env()
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is unavailable")
    source = args.source_root / "browsecomp-encrypted.csv"
    if _sha256(source) != DATA_SHA256:
        raise SystemExit("BrowseComp bytes do not match the sealed manifest")
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    selected = random.Random(0).sample(rows, args.examples)
    client = OpenAI()
    records: list[dict[str, Any]] = []
    aggregate = {
        "agent_input_tokens": 0,
        "agent_output_tokens": 0,
        "grader_input_tokens": 0,
        "grader_output_tokens": 0,
        "web_search_calls": 0,
        "correct": 0,
        "failed": 0,
    }
    started = time.perf_counter()
    for row in selected:
        problem = _decrypt(row["problem"], row["canary"])
        answer = _decrypt(row["answer"], row["canary"])
        task_hash = hashlib.sha256(row["problem"].encode()).hexdigest()
        one_started = time.perf_counter()
        try:
            agent = client.responses.create(
                model=args.agent_model,
                tools=[{"type": "web_search"}],
                tool_choice="auto",
                input=QUERY_TEMPLATE.format(Question=problem),
            )
            response_text = agent.output_text
            grader = client.responses.create(
                model=args.grader_model,
                input=GRADER_TEMPLATE.format(
                    question=problem,
                    response=response_text,
                    correct_answer=answer,
                ),
                temperature=0,
                max_output_tokens=512,
            )
            match = re.search(r"correct:\s*(yes|no)", grader.output_text.lower())
            correct = bool(match and match.group(1) == "yes")
            agent_usage = _usage(agent)
            grader_usage = _usage(grader)
            tool_counts = _tool_counts(agent)
            web_calls = tool_counts.get("web_search_call", 0)
            aggregate["agent_input_tokens"] += agent_usage["input_tokens"]
            aggregate["agent_output_tokens"] += agent_usage["output_tokens"]
            aggregate["grader_input_tokens"] += grader_usage["input_tokens"]
            aggregate["grader_output_tokens"] += grader_usage["output_tokens"]
            aggregate["web_search_calls"] += web_calls
            aggregate["correct"] += int(correct)
            records.append(
                {
                    "task_hash": task_hash,
                    "status": "scored",
                    "correct": correct,
                    "latency_seconds": time.perf_counter() - one_started,
                    "agent_usage": agent_usage,
                    "grader_usage": grader_usage,
                    "agent_output_item_counts": tool_counts,
                    "grader_format_valid": match is not None,
                }
            )
        except Exception as exc:
            aggregate["failed"] += 1
            records.append(
                {
                    "task_hash": task_hash,
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "latency_seconds": time.perf_counter() - one_started,
                }
            )
    scored = args.examples - aggregate["failed"]
    report = {
        "schema": "agent-compaction-external-live-evaluation/v1",
        "benchmark": "BrowseComp",
        "dataset_sha256": DATA_SHA256,
        "official_reference_harness_revision": HARNESS_REVISION,
        "selection": {"method": "random.Random(0).sample", "examples": args.examples},
        "agent_model": args.agent_model,
        "grader_model": args.grader_model,
        "aggregate": {
            **aggregate,
            "accuracy": aggregate["correct"] / scored if scored else None,
            "provider_requests": scored * 2,
            "total_tokens": sum(
                aggregate[key]
                for key in (
                    "agent_input_tokens",
                    "agent_output_tokens",
                    "grader_input_tokens",
                    "grader_output_tokens",
                )
            ),
            "wall_seconds": time.perf_counter() - started,
            "cost_usd": None,
            "cost_note": "not imputed; provider invoice data is unavailable",
        },
        "tasks": records,
        "evidence": {
            "class": "bounded live-provider live-web benchmark",
            "official_full_benchmark_score": False,
            "is_real_world_demo": False,
            "compiler_execution": False,
            "gac_disposition": "baseline bypass: hosted web search lacks a replay-safe local trace contract",
            "questions_answers_responses_search_results_serialized": False,
            "credential_serialized": False,
        },
        "openai_contract_source": "https://developers.openai.com/api/docs/guides/tools",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
