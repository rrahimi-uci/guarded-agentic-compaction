"""Invariants for the signed BFCL multi-turn effect catalog.

These checks need no benchmark checkout: they hold the hand-signed declarations to the
shape the compiler relies on, so a later edit cannot quietly widen what is compilable.
The empirical half of the audit — no read-like declaration observed mutating state — runs
inside ``paper/scripts/bfcl_compiler_benchmark.py`` against the pinned backend.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from guarded_agentic_compaction.schema.effects import Capability, EffectCatalog, EffectClass


ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "benchmarks/contracts/effects/bfcl.yaml"

INVOLVED_CLASSES = {
    "GorillaFileSystem",
    "MathAPI",
    "MessageAPI",
    "TicketAPI",
    "TradingBot",
    "TravelAPI",
    "TwitterAPI",
    "VehicleControlAPI",
}
# Read-like, but never replay-licensed: one derives an age from the host date, the other
# draws from the seeded scenario RNG and advances it.
NOT_REPLAY_LICENSED = {
    "TravelAPI.verify_traveler_information",
    "VehicleControlAPI.get_outside_temperature_from_google",
}


def _catalog() -> EffectCatalog:
    return EffectCatalog.from_yaml(CATALOG_PATH)


def test_catalog_declares_every_gold_plan_tool_with_a_qualified_name() -> None:
    catalog = _catalog()

    assert len(catalog.tools) == 81
    for name in catalog.tools:
        class_name, _, method = name.partition(".")
        assert class_name in INVOLVED_CLASSES, name
        assert method and not method.startswith("_"), name


def test_catalog_effect_mix_is_exact() -> None:
    catalog = _catalog()

    mix = Counter(spec.effect for spec in catalog.tools.values())

    assert mix == {
        EffectClass.READ_LOCAL: 31,
        EffectClass.WRITE_REVERSIBLE: 24,
        EffectClass.WRITE_IRREVERSIBLE: 21,
        EffectClass.PURE: 3,
        EffectClass.READ_EXTERNAL: 2,
    }
    assert EffectClass.UNKNOWN not in mix


def test_pure_is_reserved_for_the_upstream_stateless_class() -> None:
    catalog = _catalog()

    pure = {name for name, spec in catalog.tools.items() if spec.effect is EffectClass.PURE}

    assert pure == {"MathAPI.logarithm", "MathAPI.mean", "MathAPI.standard_deviation"}


def test_compilable_tools_are_read_like_and_carry_both_pre_commit_capabilities() -> None:
    catalog = _catalog()

    compilable = {name for name, spec in catalog.tools.items() if spec.compilable}

    assert len(compilable) == 34
    for name in compilable:
        spec = catalog.get(name)
        assert spec.effect.is_read_like
        assert Capability.SPECULATABLE in spec.capabilities
        assert Capability.REPLAYABLE in spec.capabilities
        assert not spec.approval_required


def test_time_varying_reads_are_declared_but_never_compilable() -> None:
    catalog = _catalog()

    for name in NOT_REPLAY_LICENSED:
        spec = catalog.get(name)
        assert spec.effect is EffectClass.READ_EXTERNAL, name
        assert spec.capabilities == (), name
        assert not spec.compilable, name


def test_nominal_getter_that_writes_internal_state_is_declared_a_write() -> None:
    """``get_flight_cost`` mutates the instance's flight-cost lookup on every call."""

    spec = _catalog().get("TravelAPI.get_flight_cost")

    assert spec.effect is EffectClass.WRITE_REVERSIBLE
    assert not spec.compilable


def test_every_write_declaration_is_a_barrier() -> None:
    catalog = _catalog()

    for name, spec in catalog.tools.items():
        if spec.effect.is_read_like:
            continue
        assert spec.is_barrier, name
        assert spec.capabilities == (), name
