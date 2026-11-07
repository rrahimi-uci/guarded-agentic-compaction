"""Tests for the generated "What the compiler decided without human input" table.

The table is built from retained result files only (``iclr_revision_statistics.py decisions``).
These tests pin its structure and its key numbers and check that regeneration is deterministic and
never touches the committed table.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import iclr_revision_statistics as stats  # noqa: E402
import validate_compiler_decisions as validator  # noqa: E402

COMMITTED_TABLES = stats.TABLES


@pytest.fixture(scope="module", autouse=True)
def _scratch_tables(tmp_path_factory):
    stats.TABLES = tmp_path_factory.mktemp("decisions_tables")
    yield
    stats.TABLES = COMMITTED_TABLES


@pytest.fixture(scope="module")
def rows():
    return stats.build_decisions()


@pytest.fixture(scope="module")
def facts(rows):
    return {row["id"]: row["facts"] for row in rows}


def test_row_budget_and_columns(rows):
    assert len(rows) == 12 <= stats.DECISIONS_MAX_ROWS
    assert len({row["id"] for row in rows}) == len(rows)
    for row in rows:
        for column in ("saw", "decided", "why", "human"):
            assert row[column].strip(), (row["id"], column)
        assert row["sources"], row["id"]
        assert all((stats.RESULTS / source).exists() for source in row["sources"]), row["id"]


def test_row_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(stats, "DECISIONS_MAX_ROWS", 11)
    with pytest.raises(ValueError, match="main-text limit"):
        stats.build_decisions()


def test_primary_families_admitted_and_tie_the_hand_written_program(facts):
    for family in ("issue_type", "pr_outcome", "backlog_attention"):
        f = facts[family]
        assert (f["gate_n"], f["gate_violations"], f["discovery_traces"]) == (92, 0, 132)
        assert f["held_out"]["compiled"]["exact"] == f["held_out"]["manual"]["exact"] == 30
    assert len(facts["issue_type"]["admitted_reads"]) == 2 and len(facts["issue_type"]["refused_tools"]) == 3


def test_cross_repository_and_time_forward(facts):
    cross = facts["cross_repository"]
    assert (len(cross["admitted"]), cross["retired"]) == (4, ["pytorch/pytorch"])
    assert (cross["held_out_exact"], cross["held_out_n"]) == (120, 120)
    forward = facts["time_forward"]
    assert forward["program_identical"] and forward["retained_abstained"] == 60
    assert (forward["certificate_attempted"], forward["certificate_violations"]) == (132, 0)
    assert forward["certificate_upper"] == pytest.approx(0.0173, abs=5e-5)


def test_second_model_and_provider_refuse_backlog(facts):
    assert all(facts["gpt6_luna"]["identical"].values()) and facts["gpt6_luna"]["backlog_exact_traces"] == 113
    assert all(facts["claude_sonnet5"]["identical"].values())
    assert facts["claude_sonnet5"]["backlog_accepted_groups"] == [91, 90]


def test_bird_trace_benchmarks_appworld_and_effect_barrier(facts):
    bird = facts["bird_per_question"]
    assert (bird["standard_retired_dev"], bird["standard_retired_train"]) == (5, 26)
    assert (bird["schema_first_admitted_dev"] + bird["schema_first_admitted_train"], bird["schema_first_databases"]) == (26, 31)
    assert (bird["dev_correct_compiled"], bird["dev_correct_baseline"], bird["dev_n"]) == (97, 94, 150)
    assert facts["trace_benchmarks"]["largest_family"] == (26, 8, 15)
    app = facts["appworld"]
    assert (app["admitted"], app["retired_at_calibration"]) == (1, 4)
    assert (app["dispatchable_react_plan_exec"], app["react_plan_exec_trajectories"]) == (1, 4680)
    barrier = facts["bfcl_getter_that_writes"]
    assert barrier["calls"] == barrier["mutating_calls"] == 36 and not barrier["declared_compilable"]


def test_render_is_deterministic_and_single_column(rows):
    first, second = stats.render_decisions(rows), stats.render_decisions(rows)
    assert first == second
    assert "\\label{tab:compiler-decisions}" in first and "\\footnotesize" in first
    assert "\\textwidth" not in first and first.count("\\begin{table}") == first.count("\\end{table}") == 1
    assert abs(sum(stats.DECISIONS_WIDTHS) + 0.06 - 1.0) < 0.05  # columns plus 3pt gaps fit one column
    assert first.count("{") == first.count("}")
    for old in ("p/a/w", "slots"):
        assert old not in first


def test_command_writes_only_to_the_scratch_directory(rows):
    committed_before = (COMMITTED_TABLES / "compiler_decisions.tex").read_bytes() if (COMMITTED_TABLES / "compiler_decisions.tex").exists() else None
    stats.cmd_decisions()
    assert (stats.TABLES / "compiler_decisions.tex").exists()
    after = (COMMITTED_TABLES / "compiler_decisions.tex").read_bytes() if (COMMITTED_TABLES / "compiler_decisions.tex").exists() else None
    assert committed_before == after
    assert "decisions" in stats.COMMANDS


def test_committed_table_matches_regeneration(rows):
    committed = (COMMITTED_TABLES / "compiler_decisions.tex").read_text(encoding="utf-8")
    assert committed == stats.GENERATED.format(name="decisions") + stats.render_decisions(rows).rstrip() + "\n"


def test_validator_passes_on_retained_evidence():
    results = validator.validate_compiler_decisions()
    failures = [message for passed, message in results if not passed]
    assert not failures and len(results) >= 30
