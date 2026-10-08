"""Provider-free tests for the BIRD SQL-agent study (skipped when the BIRD cache is absent)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bird_sql_agent_study as bird  # noqa: E402

needs_data = pytest.mark.skipif(not (bird.BIRD_DIR / "dev.json").exists(), reason="BIRD dev cache not present")


def test_prompts_differ_only_in_the_workflow_step() -> None:
    standard, first = bird.PROMPTS["standard"], bird.PROMPTS["schema_first"]
    assert standard.startswith(bird._COMMON) and first.startswith(bird._COMMON)
    assert "most relevant tables" in standard and "every table" in first


def test_qualify_does_not_filter_on_correctness() -> None:
    from types import SimpleNamespace

    runs = [SimpleNamespace(condition="discovery", quality={"answered": True, "trace_valid": True, "overall": ok}) for ok in (True, False)]
    assert len(bird.qualified(runs)) == 2


@needs_data
def test_families_and_splits_are_fixed() -> None:
    questions = bird.load_questions()
    fams = bird.families(questions)
    assert fams == ["card_games", "codebase_community", "formula_1", "student_club", "thrombosis_prediction"]
    assert not set(fams) & set(bird.SMOKE_DATABASES)
    for db in fams:
        a, b = bird.select(questions, db), bird.select(questions, db)
        assert a == b and len(a["test"]) == bird.TEST_N
        assert not set(a["test"]) & set(a["discovery"])


@needs_data
def test_tools_are_read_only_and_deterministic() -> None:
    db = bird.BirdDatabase("thrombosis_prediction")
    listing = db.list_tables()
    assert listing["tables"] and db.get_schema(listing["tables"]) == db.get_schema(listing["tables"])
    assert "error" in db.run_query("DELETE FROM Patient")
    assert "unknown_tables" in db.get_schema(["no_such_table"])
    assert len(db.run_query("SELECT * FROM Laboratory")["rows"]) <= bird.MAX_ROWS


@needs_data
def test_grading_is_set_equality() -> None:
    db = "thrombosis_prediction"
    gold = bird.execute_full(db, "SELECT ID FROM Patient WHERE SEX = 'F'")
    assert bird.grade(db, gold, {"sql": "SELECT ID FROM Patient WHERE SEX = 'F' ORDER BY ID DESC"}, [])["overall"]
    assert not bird.grade(db, gold, {"sql": "SELECT ID FROM Patient"}, [])["overall"]
    assert not bird.grade(db, gold, {"sql": "SELEC broken"}, [])["overall"]
