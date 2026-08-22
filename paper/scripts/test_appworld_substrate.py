"""Regression tests for the AppWorld substrate's provider-free logic.

These cover the parts of ``appworld_compiler_benchmark.py`` that decide what the substrate
claims: the two pre-registered arms, the fail-closed preconditions, the entry-state
contract, and the calibration split. None of them needs AppWorld installed, so CI keeps
covering the claim boundary even though the corpus itself requires a separate interpreter
and a data download.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))


def _load():
    spec = importlib.util.spec_from_file_location(
        "appworld_compiler_benchmark", Path(__file__).with_name("appworld_compiler_benchmark.py")
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _load()


def _record(task_id: str = "aaa_1", calls=None, mutations=()):
    return {
        "task_id": task_id,
        "split": "train",
        "scenario_id": task_id.rsplit("_", 1)[0],
        "execution_failed": False,
        "specs": {"supervisor": {"email": "a@b.c"}, "datetime": "2023-05-18T12:00:00"},
        "calls": calls
        if calls is not None
        else [
            {"tool": "supervisor.show_profile", "args": {}, "result": {"email": "a@b.c"},
             "mutations": list(mutations)},
            {"tool": "supervisor.show_account_passwords", "args": {},
             "result": [{"account_name": "spotify", "password": "p"}], "mutations": []},
        ],
    }


# --- the signed catalog -----------------------------------------------------


def test_signed_catalog_declares_every_login_a_write() -> None:
    """Arm A is the file as signed, and it is the conservative arm."""

    catalog = MODULE._arm_catalog("A")
    for name in MODULE.LOGIN_TOOLS:
        spec = catalog.get(name)
        assert not spec.effect.is_read_like, name
        assert not spec.compilable, name


def test_sensitivity_arm_flips_only_the_login_entries() -> None:
    """Arm B must move exactly five declarations and nothing else."""

    arm_a, arm_b = MODULE._arm_catalog("A"), MODULE._arm_catalog("B")
    assert set(arm_a.tools) == set(arm_b.tools)
    changed = {
        name
        for name in arm_a.tools
        if arm_a.get(name).effect is not arm_b.get(name).effect
        or arm_a.get(name).compilable != arm_b.get(name).compilable
    }
    assert changed == set(MODULE.LOGIN_TOOLS)
    for name in MODULE.LOGIN_TOOLS:
        assert arm_b.get(name).compilable, name


def test_no_write_is_compilable_in_either_arm() -> None:
    for arm in ("A", "B"):
        catalog = MODULE._arm_catalog(arm)
        for name, spec in catalog.tools.items():
            if not spec.effect.is_read_like:
                assert not spec.compilable, f"{arm}:{name}"


def test_catalog_declares_no_pure_tool() -> None:
    """Precondition 4: every AppWorld API reads the per-task database."""

    MODULE._assert_no_pure(MODULE._arm_catalog("A"))


# --- fail-closed preconditions ----------------------------------------------


def test_undeclared_api_aborts_rather_than_defaulting_to_unknown() -> None:
    catalog = MODULE._arm_catalog("A")
    record = _record(calls=[{"tool": "spotify.not_a_real_api", "args": {},
                             "result": {}, "mutations": []}])
    with pytest.raises(RuntimeError, match="no signed declaration"):
        MODULE._assert_catalog_completeness(catalog, [record])


def test_read_like_declaration_observed_mutating_aborts() -> None:
    """Precondition 3, the audit that makes the catalog a claim rather than a label."""

    catalog = MODULE._arm_catalog("A")
    record = _record(mutations=("UPDATE",))
    with pytest.raises(RuntimeError, match="observed mutating"):
        MODULE._audit_effects(catalog, [record])


def test_stricter_than_observed_is_permitted() -> None:
    """The audit is one-directional: a declared write that never mutates is fine."""

    catalog = MODULE._arm_catalog("A")
    record = _record(calls=[{"tool": "spotify.login", "args": {"username": "a"},
                             "result": {"access_token": "t"}, "mutations": []}])
    audit = MODULE._audit_effects(catalog, [record])
    assert audit["read_like_declarations_observed_mutating"] == 0
    assert "spotify.login" in audit["declared_stricter_than_observed"]


def test_replay_mismatch_aborts() -> None:
    record = _record()
    record["replay"] = [dict(call) for call in record["calls"]]
    record["replay"][0]["result"] = {"email": "different@b.c"}
    with pytest.raises(RuntimeError, match="did not reproduce"):
        MODULE._replay_matches([record])


def test_replay_call_count_mismatch_aborts() -> None:
    record = _record()
    record["replay"] = record["calls"][:1]
    with pytest.raises(RuntimeError, match="did not reproduce"):
        MODULE._replay_matches([record])


def test_exact_replay_reports_a_rate_when_it_matches() -> None:
    record = _record()
    record["replay"] = [dict(call) for call in record["calls"]]
    replay = MODULE._replay_matches([record])
    assert replay["compared_calls"] == 2
    assert replay["mismatched_calls"] == 0
    assert replay["exact_replay_rate"] == 1.0


# --- entry-state contract ---------------------------------------------------


def test_entry_state_carries_the_benchmark_snapshot_and_excludes_reused_values() -> None:
    """A value an earlier result produced is not a user input the second time."""

    record = _record(calls=[
        {"tool": "supervisor.show_profile", "args": {},
         "result": {"email": "a@b.c"}, "mutations": []},
        {"tool": "spotify.login", "args": {"username": "a@b.c", "password": "fresh"},
         "result": {"access_token": "t"}, "mutations": []},
    ])
    entry, reused = MODULE._entry_state(record)
    assert entry["environment"]["supervisor"]["email"] == "a@b.c"
    assert entry["environment"]["datetime"] == "2023-05-18T12:00:00"
    assert reused == 1, "the profile email is a prior result, not an entry input"
    retained = [path for slot in entry["inputs"].values() for path in slot]
    assert any("password" in path for path in retained)
    assert not any("username" in path for path in retained)


# --- calibration split -----------------------------------------------------


def test_split_reserves_exactly_the_required_calibration_count() -> None:
    """The bound needs 92 zero-violation groups; the split fixes that share, not a fraction."""

    catalog = MODULE._arm_catalog("A")
    manifest = MODULE._manifest(catalog, ["supervisor.show_profile"], "A")
    records = [_record(f"task{index}_1") for index in range(136)]
    episodes, _ = MODULE._episodes(records, catalog, manifest)
    splits, sizes = MODULE._split(episodes)
    assert sizes["calibration"] == MODULE.CALIBRATION_GROUPS == 92
    assert sum(sizes.values()) == 136
    roles = [splits.train, splits.dev, splits.calibration, splits.test]
    assert sum(len(role) for role in roles) == 136
    for left in range(len(roles)):
        for right in range(left + 1, len(roles)):
            assert not roles[left] & roles[right], "splits must be disjoint"


def test_split_is_deterministic_under_the_sealed_seed() -> None:
    catalog = MODULE._arm_catalog("A")
    manifest = MODULE._manifest(catalog, ["supervisor.show_profile"], "A")
    records = [_record(f"task{index}_1") for index in range(136)]
    episodes, _ = MODULE._episodes(records, catalog, manifest)
    first, _ = MODULE._split(episodes)
    second, _ = MODULE._split(episodes)
    assert first.calibration == second.calibration


# --- reported aggregates ---------------------------------------------------


def test_required_zero_violation_groups_is_the_configured_92() -> None:
    """The number the whole substrate exists to reach, recomputed rather than restated."""

    assert MODULE.required_zero_violation_groups(alpha=0.05, delta=0.10) == 92


def test_distribution_reports_the_call_counts_behind_the_claim_boundary() -> None:
    assert MODULE._distribution([]) == {}
    assert MODULE._distribution([5, 36, 244]) == {
        "n": 3, "min": 5, "median": 36, "max": 244, "total": 285
    }


# --- sealed result ---------------------------------------------------------


def test_sealed_result_matches_the_preregistered_prediction() -> None:
    """The published artifact must still say what the protocol predicted."""

    import json

    payload = json.loads(MODULE.DEFAULT_OUT.read_text())
    assert payload["protocol"]["predeclared_gate_outcome"] == "candidate_present"
    assert payload["protocol"]["prediction_held"] is True
    assert payload["effect_audit"]["read_like_declarations_observed_mutating"] == 0
    assert payload["effect_audit"]["tools_mutating_on_some_but_not_all_calls"] == []
    assert payload["exact_replay"]["mismatched_calls"] == 0
    for arm in ("A", "B"):
        gate = payload["arms"][arm]["exact_gate"]
        assert gate["max_observed_family_support"] >= gate["minimum_zero_violation_groups"]
        assert payload["arms"][arm]["held_out_recorded_replay"]["test_wrong"] == 0
        admission = payload["admission"][arm]
        assert admission["outcome"] == "ADMITTED"
        for row in admission["gates"]:
            if not row["retire"]:
                assert row["observed_violations"] == 0
                assert row["risk_upper_bound"] <= 0.05
