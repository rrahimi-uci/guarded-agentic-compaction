"""Unit tests for the expansion-plan design arithmetic (no data needed)."""

from __future__ import annotations

import importlib.util
import sys
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


pt = _load("expansion_power_table")


def test_floors_match_the_compiler_and_the_plan():
    fl = pt.floors()
    assert fl["registered_grid"]["0"] == 92          # the gate's zero-violation floor
    assert fl["single_rule_95"]["0"] == 59           # gac-expansion.md section 15
    for rule in fl.values():                          # one more violation never needs fewer groups
        values = [rule[str(k)] for k in range(5)]
        assert values == sorted(values) and all(v is not None for v in values)


def test_detectable_miss_rate_falls_with_more_pairs():
    rates = [pt.detectable_miss_rate(n) for n in pt.PAIR_SIZES]
    assert rates == sorted(rates, reverse=True)
    # six discordant pairs are the minimum for an exact two-sided McNemar p <= 0.05
    assert 2 * 0.5 ** pt.MIN_DISCORDANT <= 0.05 < 2 * 0.5 ** (pt.MIN_DISCORDANT - 1)


def test_forced_runs_and_table():
    data = pt.build()
    assert data["h3_forced_runs_for_one_violation_95pct"]["0.05"] == 59
    text = pt.table(data)
    assert r"Registered grid ($\delta=0.10$ over 11 thresholds) & 92 & 133 & 168 & 200 & 231 \\" in text
    assert "5\\%: 59" in text


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
