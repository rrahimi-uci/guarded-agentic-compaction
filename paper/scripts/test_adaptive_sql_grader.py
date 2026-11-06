"""Adversarial, data-independent tests of prospective final-result grading."""
from pathlib import Path
import sqlite3
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adaptive_sql_grader import QueryResult, compare, execute


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "a ? database.sqlite"
    with sqlite3.connect(path) as con:
        con.executescript("CREATE TABLE t(x); INSERT INTO t VALUES (1),(1),(2),(NULL);")
    return path


def test_duplicates_and_order_are_separate_contracts(db):
    gold = execute(db, "SELECT x FROM t ORDER BY x")
    distinct = execute(db, "SELECT DISTINCT x FROM t ORDER BY x")
    reverse = execute(db, "SELECT x FROM t ORDER BY x DESC")
    assert compare(gold, distinct, contract="set")
    assert not compare(gold, distinct, contract="bag")
    assert compare(gold, reverse, contract="bag")
    assert not compare(gold, reverse, contract="sequence")


def test_empty_shape_null_and_numeric_equality(db):
    assert not compare(execute(db, "SELECT x FROM t WHERE 0"),
                       execute(db, "SELECT x,x FROM t WHERE 0"), contract="set")
    assert not compare(execute(db, "SELECT NULL"), execute(db, "SELECT 0"), contract="bag")
    assert compare(execute(db, "SELECT 1"), execute(db, "SELECT 1.0"), contract="bag")
    assert not compare(execute(db, "SELECT 0.3"), execute(db, "SELECT 0.1+0.2"), contract="bag")


def test_historical_metric_is_preserved_and_new_contract_is_explicit(db, monkeypatch):
    import bird_sql_agent_study as historical
    monkeypatch.setattr(historical, "connect", lambda _: sqlite3.connect(db.as_uri() + "?mode=ro", uri=True))
    gold = historical.execute_full("fixture", "SELECT x FROM t")
    assert historical.grade("fixture", gold, {"sql": "SELECT DISTINCT x FROM t"}, [])["overall"]
    empty = historical.execute_full("fixture", "SELECT x FROM t WHERE 0")
    assert historical.grade("fixture", empty, {"sql": "SELECT x,x FROM t WHERE 0"}, [])["overall"]
    assert not compare(execute(db, "SELECT x FROM t"), execute(db, "SELECT DISTINCT x FROM t"), contract="bag")


@pytest.mark.parametrize("sql", ["DELETE FROM t", "CREATE TEMP TABLE x(y)",
    "PRAGMA writable_schema=ON", "ATTACH DATABASE ':memory:' AS other",
    "SELECT load_extension('nonexistent')"])
def test_write_and_escape_attempts_are_denied(db, sql):
    before = db.read_bytes()
    assert execute(db, sql).status == "denied"
    assert db.read_bytes() == before


def test_errors_and_unavailable_gold_do_not_become_success(db):
    good = execute(db, "SELECT 1")
    bad = execute(db, "SELEC invalid")
    assert bad.status == "sql_error"
    assert compare(good, bad, contract="set") is False
    assert compare(bad, good, contract="set") is None
    assert execute(db, "").status == "empty_sql"
    assert execute(db, "SELECT 1; SELECT 2").status == "sql_error"
    with pytest.raises(ValueError):
        compare(good, good, contract="infer_from_prediction")


def test_timeout_and_fetch_limits_are_fail_closed(db):
    sql = "WITH RECURSIVE r(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM r) SELECT sum(x) FROM r"
    assert execute(db, sql, timeout=.01).status == "timeout"
    # Execution begins quickly; iteration itself must remain bounded.
    fetch_sql = "WITH RECURSIVE r(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM r) SELECT x FROM r"
    assert execute(db, fetch_sql, timeout=.01, max_rows=10_000_000).status == "timeout"
    assert execute(db, "SELECT x FROM t", max_rows=2) == QueryResult("resource_limit")
    assert execute(db, "SELECT 'long result'", max_bytes=2).status == "resource_limit"
    with pytest.raises(FileNotFoundError):
        execute(db.parent / "missing.sqlite", "SELECT 1")
