"""Provider-free SQL execution and explicit result contracts for prospective studies.

Does not change the historical BIRD metric. Exact bag/sequence contracts are
additional diagnostics, not automatic natural-language correctness oracles.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import sqlite3
import time


@dataclass(frozen=True)
class QueryResult:
    status: str
    rows: tuple[tuple, ...] = ()
    columns: int = 0


def execute(path: Path, sql: str, *, timeout: float = 30.0,
            max_rows: int = 100_000, max_bytes: int = 32_000_000) -> QueryResult:
    """Single read-only SELECT; bound VM time, returned rows and payload bytes.

    The progress handler remains active through fetching. This is not an OS
    sandbox or a hard wall-time bound on blocked disk I/O. A resource-limit
    result is unavailable, never a truncated successful answer.
    """
    if timeout <= 0 or max_rows < 1 or max_bytes < 1:
        raise ValueError("execution limits must be positive")
    if not sql.strip():
        return QueryResult("empty_sql")
    # strict=True prevents SQLite silently opening an unintended missing file.
    uri = path.resolve(strict=True).as_uri() + "?mode=ro&immutable=1"
    con = sqlite3.connect(uri, uri=True)
    deadline = time.monotonic() + timeout
    allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ,
               sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}
    denied = False

    def authorize(action, arg1, arg2, database, trigger):
        nonlocal denied
        safe = action in allowed
        if action == sqlite3.SQLITE_FUNCTION:
            safe = (arg2 or "").lower() not in {"load_extension", "readfile", "writefile"}
        if not safe:
            denied = True
        return sqlite3.SQLITE_OK if safe else sqlite3.SQLITE_DENY

    con.set_authorizer(authorize)
    con.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
    try:
        cursor = con.execute(sql)
        if cursor.description is None:
            return QueryResult("not_query")
        rows = []
        size = 0
        for row in cursor:
            if time.monotonic() >= deadline:
                return QueryResult("timeout")
            size += sum(len(v) if isinstance(v, bytes) else len(str(v).encode()) for v in row)
            if len(rows) >= max_rows or size > max_bytes:
                return QueryResult("resource_limit")
            rows.append(tuple(row))
        return QueryResult("ok", tuple(rows), len(cursor.description))
    except sqlite3.Error as exc:
        return QueryResult("denied" if denied else "timeout" if "interrupted" in str(exc) else "sql_error")
    finally:
        con.close()


def compare(gold: QueryResult, predicted: QueryResult, *, contract: str) -> bool | None:
    """None means no usable gold; prediction failure against valid gold is False.

    Empty results still require the right column count. Numeric comparisons use
    Python/SQLite value equality (1 == 1.0); no implicit rounding/tolerance.
    Sequence must be declared from task semantics, not inferred from a model SQL.
    """
    if contract not in {"set", "bag", "sequence"}:
        raise ValueError("declare set, bag or sequence contract")
    if gold.status != "ok":
        return None
    if predicted.status != "ok" or gold.columns != predicted.columns:
        return False
    if contract == "set":
        return set(gold.rows) == set(predicted.rows)
    if contract == "bag":
        return Counter(gold.rows) == Counter(predicted.rows)
    return gold.rows == predicted.rows
