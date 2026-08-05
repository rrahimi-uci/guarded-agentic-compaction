#!/usr/bin/env python3
"""Execute every pinned BFCL v4 multi-turn-base gold plan with its official checker.

This is an executable environment/trace-structure check, not an LLM function-calling
score: the reference plan is supplied as both candidate and ground truth.  The output
retains counts and source identities only; prompts, calls, state, and results are not
serialized.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REVISION = "6ea57973c7a6097fd7c5915698c54c17c5b1b6c8"
DEFAULT_OUT = ROOT / "paper/results/external_benchmarks/bfcl_gold_execution.json"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _digest_ids(items: list[dict[str, Any]]) -> str:
    encoded = json.dumps(sorted(str(item["id"]) for item in items), separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    checkout = args.source_root / "gorilla" / "berkeley-function-call-leaderboard"
    if not checkout.is_dir():
        raise SystemExit("pinned BFCL checkout is unavailable")
    sys.path.insert(0, str(checkout))
    from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_checker import (  # noqa: PLC0415
        multi_turn_checker,
    )

    data = checkout / "bfcl_eval" / "data"
    questions = _read_jsonl(data / "BFCL_v4_multi_turn_base.json")
    answers = {
        item["id"]: item
        for item in _read_jsonl(
            data / "possible_answer" / "BFCL_v4_multi_turn_base.json"
        )
    }
    outcomes: Counter[str] = Counter()
    turns = calls = 0
    started = time.perf_counter()
    for index, question in enumerate(questions):
        ground_truth = answers[question["id"]]["ground_truth"]
        decoded = [[turn] for turn in ground_truth]
        turns += len(ground_truth)
        calls += sum(len(turn) for turn in ground_truth)
        random.seed(int.from_bytes(str(question["id"]).encode(), "little") % (2**32))
        try:
            result = multi_turn_checker(
                decoded,
                ground_truth,
                question,
                "multi_turn_base",
                f"gold-structural-{index}",
            )
        except Exception as exc:
            outcomes[f"exception:{type(exc).__name__}"] += 1
            continue
        if result.get("valid"):
            outcomes["valid"] += 1
        else:
            outcomes[
                "invalid:"
                + str(result.get("error_type") or result.get("error", {}).get("error_type") or "unknown")
            ] += 1

    report = {
        "schema": "agent-compaction-external-execution/v1",
        "benchmark": "BFCL v4 multi_turn_base",
        "source_revision": REVISION,
        "source_license": "Apache-2.0",
        "task_set_digest": _digest_ids(questions),
        "tasks": len(questions),
        "turns": turns,
        "reference_calls": calls,
        "official_checker_outcomes": dict(sorted(outcomes.items())),
        "official_checker_valid_rate": outcomes["valid"] / len(questions),
        "runtime_seconds": time.perf_counter() - started,
        "provider_calls": 0,
        "values_serialized": False,
        "evidence": {
            "class": "official executable public benchmark environment with gold plans",
            "is_model_quality_evaluation": False,
            "is_compiler_execution": False,
            "is_real_world_demo": False,
            "licenses_claim": "the pinned reference plans remain executable under the pinned official checker",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
