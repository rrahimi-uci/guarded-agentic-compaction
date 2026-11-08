"""Unit tests for the compiler-funnel live pilot (no snapshot, corpus or provider needed)."""

from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


lp = _load("compiler_funnel_live_pilot")


def test_split_is_a_deterministic_partition_with_128_discovery():
    numbers = list(range(7617, 7617 + 193))
    discovery, test = lp.split(numbers)
    assert len(discovery) == 128 and len(test) == 65
    assert not set(discovery) & set(test) and set(discovery) | set(test) == set(numbers)
    assert lp.split(list(reversed(numbers))) == (discovery, test)


def test_latin_assignment_is_balanced_over_the_six_orders():
    numbers = list(range(100, 165))
    assigned = lp.latin_assignment(numbers)
    counts = Counter(assigned.values())
    assert len(counts) == 6 and max(counts.values()) - min(counts.values()) <= 1
    for stage in range(3):  # every arm appears at every stage
        assert {order[stage] for order in assigned.values()} == set(lp.ARMS)


def test_pool_requires_a_comment_and_honours_exclusions():
    store = {1: {"comments": ["a"]}, 2: {"comments": []}, 3: {"comments": ["b"]}, 4: {"comments": ["c"]}}
    assert lp.pool_numbers(store, {4}) == [1, 3]


def test_classify_telemetry_matches_the_retained_dispatch_shapes():
    dispatched = {"compacted": 1, "baseline": 2, "guard_misses": {"region_already_started": 2}, "gate_rejections": 0}
    assert lp.classify_telemetry(dispatched) == "dispatched"
    assert lp.classify_telemetry({"compacted": 0, "guard_misses": {"entry_domain": 1}}) == "guard_ineligible"
    assert lp.classify_telemetry({"compacted": 0, "gate_rejections": 1}) == "gate_declined"
    assert lp.classify_telemetry({"compacted": 0, "verifier_failures": {"get.state": 1}}) == "abstained"
    assert lp.classify_telemetry({}) == "no_dispatch"


def test_table_renders_three_arms_from_minimal_results():
    mean = lambda req, tok, cost: {"requests": req, "total_tokens": tok, "wall_latency_ms": 3000.0, "estimated_cost_usd": cost}  # noqa: E731
    results = {
        "selection": {"test": list(range(65))},
        "compile": {"gac": {"artifact_tools": ["issue_get_record", "issue_get_labels"]}},
        "test": {"aggregate": {
            "compiled": {"factuality_exact": 64, "mean": mean(2.0, 1500, 0.0006)},
            lp.issue.CONDITION: {"factuality_exact": 63, "mean": mean(1.0, 900, 0.0004)},
            "baseline": {"factuality_exact": 65, "mean": mean(4.0, 2600, 0.0009)},
        }},
    }
    text = lp.table(results)
    assert r"Compiled 2-read program (\method, fresh compile) & 64/65 & 2.00 & 1,500 & 3.00 & 0.060 \\" in text
    results["compile"]["gac"]["artifact_tools"] = None
    assert r"Compiled program (\method, fresh compile) & 64/65" in lp.table(results)
    assert r"Recurrence-only three-read replay & 63/65 & 1.00 & 900 & 3.00 & 0.040 \\" in text
    assert r"Unchanged agent & 65/65 & 4.00 & 2,600 & 3.00 & 0.090 \\" in text


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
