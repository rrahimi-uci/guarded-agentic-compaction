#!/usr/bin/env python3
"""BIRD text-to-SQL agent study: compile-or-retire on a public benchmark, live.

Protocol: ``paper/supplementary/bird-sql-agent-protocol.md`` (registered before any provider
call). A tool-using SQL agent answers BIRD dev questions over read-only SQLite databases.
Two agent designs are registered:

* ``standard``      the agent lists tables, then reads the schema of the tables it judges
                    relevant to the question (adapted from LangChain's SQL-agent prompt);
* ``schema_first``  the agent lists tables, then reads the schema of every table, then
                    writes its query (a fixed workflow step, like the paper's prescribed design).

Each database with at least 146 dev questions is one workflow family. Phases, each
checkpointed under ``--out``:

  preflight   provider-free: data digests, families, sealed splits, gold results, prompt digests
  smoke       live: three questions per design on two non-family databases (plumbing only)
  discovery   live: the unchanged agent on each family's discovery questions
  compile     provider-free: compile-or-retire per (design, family), plus the strict audit
  test        live: baseline, baseline repeat, compiled artifact and hand-written schema
              prefetch on each admitted family's 30 sealed held-out questions
  summarize   provider-free: per-family and pooled endpoints

Live phases refuse to run without ``--approved-spend-usd``; every result's estimated cost is
ledgered and the run stops before a reservation would exceed the cap.
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import hashlib
import json
import os
import pickle
import random
import sqlite3
import statistics
import sys
import time
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from pydantic import BaseModel, Field  # noqa: E402

CACHE = ROOT / "benchmarks/.cache/bird"
SPLIT_CONFIG: dict[str, dict[str, Any]] = {
    "dev": {"archive": CACHE / "dev.zip", "url": "https://bird-bench.oss-cn-beijing.aliyuncs.com/dev.zip",
            "sha256": "cdd6d19faeb45a23970b98d3ef6c40a87987c95459c2cf12076897a60cf5a630",
            "dir": CACHE / "extract/dev_20240627", "questions": "dev.json", "databases": "dev_databases",
            "gold": CACHE / "gold_results.pkl", "release": "dev_20240627",
            "smoke": ("california_schools", "superhero")},
    "train": {"archive": CACHE / "train.zip", "url": "https://bird-bench.oss-cn-beijing.aliyuncs.com/train.zip",
              "sha256": "66e9e3115b59559554013aa3b124156249f30437a6b4e4f96de3d2dfb5ae8cbc",
              "dir": CACHE / "extract/train", "questions": "train.json", "databases": "train_databases",
              "gold": CACHE / "gold_results_train.pkl", "release": "train", "smoke": ()},
}
SPLIT = "dev"
BIRD_ARCHIVE = SPLIT_CONFIG["dev"]["archive"]
BIRD_ARCHIVE_URL = SPLIT_CONFIG["dev"]["url"]
BIRD_ARCHIVE_SHA256 = SPLIT_CONFIG["dev"]["sha256"]
BIRD_DIR = SPLIT_CONFIG["dev"]["dir"]
GOLD_CACHE = SPLIT_CONFIG["dev"]["gold"]
OUT_ROOT = ROOT / "paper/results/bird"
MODEL = "gpt-5.6-luna"
DESIGNS = ("standard", "schema_first")
FAMILY_MIN_QUESTIONS = 146          # 16 train + 8 dev + 92 calibration + 30 held out
TEST_N = 30
DISCOVERY_MAX = 132
SMOKE_DATABASES: tuple[str, ...] = ("california_schools", "superhero")   # excluded from the families
SMOKE_PER_DESIGN = 3
CONDITIONS = ("baseline", "baseline_repeat", "compiled", "manual_schema_prefetch")
TOOLS = ("list_tables", "get_schema", "run_query")
QUERY_TIMEOUT_S = 15.0
GRADE_TIMEOUT_S = 30.0
MAX_ROWS = 20
MAX_VALUE_CHARS = 100
SAMPLE_ROWS = 3
SPLIT_SEED = 20261008
DAY = "2024-06-27"                  # BIRD dev release; questions carry no dates


# --------------------------------------------------------------------------- prompts
_COMMON = """You are an agent designed to interact with a SQLite database.
Given an input question, create a syntactically correct SQLite query that answers it, run it to
check the result, and return that query as your final answer.
Never query for all the columns of a table; select only the columns the question asks for, and
return exactly what the question asks for, with no extra columns.
You have access to tools for interacting with the database. Only use the information returned by
the tools to construct your final answer.
You MUST double check your query before returning it. If you get an error while executing a
query, rewrite the query and try again.
DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.
The user may supply evidence: domain knowledge that maps the question's terms to columns and
values. Use it.
"""

PROMPTS = {
    "standard": _COMMON + """
You should look at the tables in the database to see what you can query. Then you should query
the schema of the most relevant tables.
""",
    "schema_first": _COMMON + """
Begin by listing the tables in the database. Then read the schema of every table in the
database. Only then write and test your query.
""",
}


class BirdAnswer(BaseModel):
    sql: str = Field(min_length=1, max_length=4000)


def configure(*, model: str, split: str) -> None:
    """Bind the module to one model and one BIRD split (the primary run is gpt-5.6-luna on dev)."""
    global MODEL, SPLIT, BIRD_ARCHIVE, BIRD_ARCHIVE_URL, BIRD_ARCHIVE_SHA256, BIRD_DIR, GOLD_CACHE, SMOKE_DATABASES
    cfg = SPLIT_CONFIG[split]
    MODEL, SPLIT = model, split
    BIRD_ARCHIVE, BIRD_ARCHIVE_URL, BIRD_ARCHIVE_SHA256 = cfg["archive"], cfg["url"], cfg["sha256"]
    BIRD_DIR, GOLD_CACHE, SMOKE_DATABASES = cfg["dir"], cfg["gold"], tuple(cfg["smoke"])


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _digest(obj: Any) -> str:
    return _sha(json.dumps(obj, sort_keys=True, default=str))


# --------------------------------------------------------------------------- database access
def db_path(db: str) -> Path:
    return BIRD_DIR / SPLIT_CONFIG[SPLIT]["databases"] / db / f"{db}.sqlite"


def connect(db: str) -> sqlite3.Connection:
    # mode=ro forbids writes at the driver; immutable=1 also forbids locks and journal files.
    return sqlite3.connect(f"file:{db_path(db)}?mode=ro&immutable=1", uri=True, check_same_thread=False)


def _execute(con: sqlite3.Connection, sql: str, timeout_s: float, fetch: Callable[[sqlite3.Cursor], Any]) -> Any:
    deadline = time.monotonic() + timeout_s
    con.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 20_000)
    try:
        return fetch(con.execute(sql))
    finally:
        con.set_progress_handler(None, 0)


def _cell(value: Any) -> Any:
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    if isinstance(value, str) and len(value) > MAX_VALUE_CHARS:
        return value[:MAX_VALUE_CHARS] + "..."
    return value


class BirdDatabase:
    """Deterministic read-only tools over one pinned BIRD SQLite database."""

    def __init__(self, db: str) -> None:
        self.db = db
        with connect(db) as con:
            self._tables = [
                row[0] for row in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid"
                )
            ]
            self._create = {
                row[0]: row[1] for row in con.execute(
                    "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            }

    def list_tables(self) -> dict[str, Any]:
        return {"database": self.db, "tables": list(self._tables)}

    def get_schema(self, table_names: Sequence[str]) -> dict[str, Any]:
        schemas: list[dict[str, Any]] = []
        unknown: list[str] = []
        con = connect(self.db)
        try:
            for name in table_names:
                if name not in self._create:
                    unknown.append(str(name))
                    continue
                cursor = _execute(con, f'SELECT * FROM "{name}" LIMIT {SAMPLE_ROWS}', QUERY_TIMEOUT_S, lambda c: c)
                columns = [d[0] for d in cursor.description]
                rows = [[_cell(v) for v in row] for row in cursor.fetchall()]
                schemas.append({
                    "table": name,
                    "create_statement": self._create[name],
                    "columns": columns,
                    "sample_rows": rows,
                })
        finally:
            con.close()
        out: dict[str, Any] = {"database": self.db, "schemas": schemas}
        if unknown:
            out["unknown_tables"] = unknown
        return out

    def run_query(self, sql: str) -> dict[str, Any]:
        con = connect(self.db)
        try:
            cursor = _execute(con, sql, QUERY_TIMEOUT_S, lambda c: c)
            columns = [d[0] for d in (cursor.description or ())]
            rows = cursor.fetchmany(MAX_ROWS + 1)
        except sqlite3.Error as exc:
            message = str(exc)
            if "interrupted" in message:
                message = f"query exceeded {QUERY_TIMEOUT_S:.0f}s and was interrupted"
            return {"error": message}
        finally:
            con.close()
        return {
            "columns": columns,
            "rows": [[_cell(v) for v in row] for row in rows[:MAX_ROWS]],
            "truncated": len(rows) > MAX_ROWS,
        }

    def execute(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool == "list_tables":
            return self.list_tables()
        if tool == "get_schema":
            return self.get_schema(list(arguments.get("table_names") or ()))
        if tool == "run_query":
            return self.run_query(str(arguments.get("sql") or ""))
        raise KeyError(tool)


def execute_full(db: str, sql: str, timeout_s: float = GRADE_TIMEOUT_S) -> tuple[frozenset | None, str]:
    """BIRD execution accuracy: the full result as a set of row tuples, or an error."""
    con = connect(db)
    try:
        rows = _execute(con, sql, timeout_s, lambda c: c.fetchall())
        return frozenset(tuple(r) for r in rows), ""
    except sqlite3.Error as exc:
        return None, "timeout" if "interrupted" in str(exc) else f"error:{type(exc).__name__}"
    except Exception as exc:  # noqa: BLE001 - unhashable or malformed rows
        return None, f"error:{type(exc).__name__}"
    finally:
        con.close()


# --------------------------------------------------------------------------- questions, families, splits
def load_questions() -> list[dict[str, Any]]:
    questions = json.loads((BIRD_DIR / SPLIT_CONFIG[SPLIT]["questions"]).read_text(encoding="utf-8"))
    for index, q in enumerate(questions):
        q.setdefault("question_id", index)  # BIRD train carries no question ids; use the file position
    return questions


def _rank(db: str, question_id: int) -> str:
    return _sha(f"bird-split:{SPLIT_SEED}:{db}:{question_id}")


def families(questions: Sequence[dict[str, Any]]) -> list[str]:
    counts = Counter(q["db_id"] for q in questions)
    return sorted(db for db, n in counts.items() if n >= FAMILY_MIN_QUESTIONS)


GOLD_FAILURE_LIMIT = 0.10   # extension protocol E4: exclude a family whose gold SQL fails this often


def study_families(pre: dict[str, Any]) -> list[str]:
    """Families the study runs: the preflight's families minus any excluded for unusable gold."""
    excluded = pre.get("excluded_families") or {}
    return [db for db in pre["families"] if db not in excluded]


def select(questions: Sequence[dict[str, Any]], db: str) -> dict[str, Any]:
    pool = sorted((q["question_id"] for q in questions if q["db_id"] == db), key=lambda qid: _rank(db, qid))
    test = pool[:TEST_N]
    discovery = pool[TEST_N:TEST_N + DISCOVERY_MAX]
    sel = {"database": db, "pool": len(pool), "test": test, "discovery": discovery,
           "unused": len(pool) - len(test) - len(discovery),
           "rule": f"sha256 rank of bird-split:{SPLIT_SEED}:<db>:<question_id>; first {TEST_N} held out; next up to {DISCOVERY_MAX} discovery"}
    sel["digest"] = _digest({"test": test, "discovery": discovery})
    return sel


def gold_results(questions: Sequence[dict[str, Any]], dbs: Sequence[str]) -> dict[int, tuple[frozenset | None, str]]:
    cache: dict[int, tuple[frozenset | None, str]] = {}
    if GOLD_CACHE.exists():
        cache = pickle.loads(GOLD_CACHE.read_bytes())
    missing = [q for q in questions if q["db_id"] in dbs and q["question_id"] not in cache]
    for q in missing:
        cache[q["question_id"]] = execute_full(q["db_id"], q["SQL"])
    if missing:
        GOLD_CACHE.write_bytes(pickle.dumps(cache))
    return cache


def grade(db: str, gold: tuple[frozenset | None, str], answer: dict[str, Any], tools: Sequence[str]) -> dict[str, Any]:
    sql = str(answer.get("sql") or "")
    predicted, error = execute_full(db, sql) if sql else (None, "error:empty")
    gold_rows, gold_error = gold
    correct = predicted is not None and gold_rows is not None and predicted == gold_rows
    trace_valid = all(tool in TOOLS for tool in tools)
    return {
        "execution_correct": bool(correct),
        "prediction_error": error,
        "gold_error": gold_error,
        "answered": bool(sql),
        "trace_valid": trace_valid,
        "tool_contract": trace_valid,
        "score": float(correct),
        "overall": bool(correct),
    }


# --------------------------------------------------------------------------- agent plumbing
def make_tools(database: BirdDatabase) -> tuple[Any, ...]:
    from agents import FunctionTool, function_tool

    @function_tool
    def list_tables() -> dict[str, Any]:
        """List the tables in the database."""
        return database.list_tables()

    @function_tool
    def get_schema(table_names: list[str]) -> dict[str, Any]:
        """Return the CREATE statement, column names and three sample rows of each named table."""
        return database.get_schema(table_names)

    @function_tool
    def run_query(sql: str) -> dict[str, Any]:
        """Run a read-only SQLite query and return at most 20 rows."""
        return database.run_query(sql)

    def wrap(tool: Any) -> Any:
        original = tool.on_invoke_tool

        async def invoke(context: Any, args_json: str) -> str:
            value = await original(context, args_json)
            return json.dumps(value, sort_keys=True, default=str)

        return FunctionTool(name=tool.name, description=tool.description, params_json_schema=tool.params_json_schema,
                            on_invoke_tool=invoke, strict_json_schema=True)

    return tuple(wrap(t) for t in (list_tables, get_schema, run_query))


def make_catalog(db: str):
    from guarded_agentic_compaction.schema.effects import EffectCatalog

    keys = {"list_tables": [], "get_schema": ["table_names"], "run_query": ["sql"]}
    return EffectCatalog.from_dict({
        "version": 1,
        "name": f"bird-{db}-readonly-sqlite",
        "tools": {
            tool: {
                "effect": "READ_LOCAL",
                "capabilities": ["speculatable", "replayable", "cacheable"],
                "key": keys[tool],
                "resource": f"bird-dev-sqlite:{db}",
                "notes": "Read-only query over a pinned BIRD dev SQLite file opened mode=ro, immutable=1",
            }
            for tool in TOOLS
        },
    })


def make_manifest(db: str, design: str, tools: Sequence[Any], catalog: Any) -> Any:
    from guarded_agentic_compaction.capture.manifests import build_manifest

    return build_manifest(
        commit="workspace-without-git-metadata",
        model=MODEL,
        prompt=PROMPTS[design],
        tools=tools,
        policy=f"bird-sql-{design}-v1",
        guardrails="read-only sqlite; BIRD execution-accuracy contract",
        catalog=catalog,
        entry_contract_version=f"bird-database-v1:{db}",
        sdk_version=version("openai-agents"),
    )


def user_input(q: dict[str, Any], prefetch: dict[str, Any] | None = None) -> str:
    text = f"Database: {q['db_id']}\nQuestion: {q['question']}\nEvidence: {q.get('evidence') or 'none'}"
    if prefetch is not None:
        text += ("\nThe runtime already listed the tables and read the schema of every table. "
                 "Use this instead of calling list_tables or get_schema:\n" + json.dumps(prefetch, sort_keys=True, default=str))
    return text


def _trace_id(design: str, condition: str, qid: int) -> str:
    return "trace_" + _sha(f"bird:{design}:{condition}:{qid}")[:32]


def materialize(q: dict[str, Any], *, design: str, condition: str, trace: Any, final_output: Any, wall_ms: float,
                manifest: Any, dispatch: dict[str, Any], gold: tuple[frozenset | None, str], db_sha: str,
                prefetch_calls: int = 0):
    import github_live_study as fixed
    from demos.live_runtime import observations_from_trace, trace_metrics
    from guarded_agentic_compaction.capture.agents_sdk import episode_from_agents_trace
    from guarded_agentic_compaction.schema.traces import OutcomeLabels, TraceEnvelope, content_digest

    answer = fixed._answer_dict(final_output)
    observations = observations_from_trace(trace, {})
    sequence = [o.tool for o in observations]
    arguments = [dict(o.args) for o in observations]
    quality = grade(q["db_id"], gold, answer, sequence)
    db = q["db_id"]
    envelope = TraceEnvelope(
        trace_id=trace.trace_id,
        episode_id=f"bird-{design}-{db}-{q['question_id']}:{condition}",
        group_id=f"bird-{db}:{q['question_id']}",
        manifest_id=manifest.manifest_id,
        principal="public-benchmark-runner",
        tenant_partition=f"public:bird-dev:{db}",
        policy_version=f"bird-sql-{design}-v1",
        day=DAY,
        privacy_class="public_dataset_provider_trace",
        entry_state_ref=content_digest({"database": db}),
        external_state_version=db_sha,
    )
    episode = episode_from_agents_trace(
        trace, envelope=envelope, manifest=manifest, entry_state={"database": db},
        outcome=OutcomeLabels(task_success=quality["overall"], semantic_score=quality["score"], safety_events=0,
                              business_metrics={"execution_correct": float(quality["overall"])}),
        final_state_digest=db_sha,
    )
    episode.attributes.update({"benchmark": "bird-dev", "design": design, "condition": condition,
                               "difficulty": q.get("difficulty"), "provider_backed": True})
    metrics = trace_metrics(trace, model=MODEL, wall_ms=wall_ms)
    metrics["model"] = MODEL
    if prefetch_calls:
        metrics["internal_tool_calls"] = prefetch_calls
        metrics["tool_calls"] = int(metrics.get("tool_calls", 0)) + prefetch_calls
    return fixed.RunResult(condition=condition, repeat=1 if condition == "baseline_repeat" else 0,
                           issue_number=int(q["question_id"]), trace_id=trace.trace_id, metrics=metrics, answer=answer,
                           quality=quality, tool_sequence=sequence, tool_arguments=arguments, dispatch=dispatch,
                           episode=episode)


async def run_batch(questions: Sequence[dict[str, Any]], *, design: str, condition: str, database: BirdDatabase,
                    processor: Any, manifest: Any, catalog: Any, gold: dict[int, Any], db_sha: str, concurrency: int,
                    registry: Any = None) -> tuple[list[Any], list[dict[str, Any]]]:
    from agents import Agent, RunConfig, Runner

    import github_live_study as fixed
    from guarded_agentic_compaction.capture.anthropic_model import resolve_model
    from guarded_agentic_compaction.runtime.model_provider import CompactingModel

    tools = make_tools(database)
    semaphore = asyncio.Semaphore(concurrency)
    trace_condition = "discovery" if condition == "discovery" else condition

    async def run_one(q: dict[str, Any]) -> tuple[Any, ...]:
        trace_id = _trace_id(design, trace_condition, q["question_id"])
        compacting = None
        prefetch = None
        if condition == "compiled":
            compacting = CompactingModel(
                fixed._provider_model(MODEL), registry=registry, catalog=catalog, manifest=manifest, mode="live",
                entry_state_fn=lambda _input, value={"database": database.db}: value,
                partition_fn=lambda _input, _entry: {},
            )
            model: Any = compacting
        else:
            model = resolve_model(MODEL)
        if condition == "manual_schema_prefetch":
            listing = database.list_tables()
            prefetch = {"list_tables": listing, "get_schema": database.get_schema(listing["tables"])}
        agent = Agent(name=f"bird-sql-{design}", instructions=PROMPTS[design], model=model,
                      model_settings=fixed.provider_model_settings(MODEL), tools=list(tools), output_type=BirdAnswer)
        async with semaphore:
            started = time.perf_counter()
            output = await asyncio.wait_for(Runner.run(
                agent, user_input(q, prefetch), max_turns=12,
                run_config=RunConfig(
                    workflow_name=f"agent-compaction-paper:bird:{design}:{condition}", trace_id=trace_id,
                    group_id=f"bird-{database.db}:{q['question_id']}", trace_include_sensitive_data=True,
                    trace_metadata={"benchmark": "bird-dev", "database": database.db, "design": design,
                                    "condition": condition, "question_id": str(q["question_id"])},
                ),
            ), timeout=180.0)
            wall_ms = (time.perf_counter() - started) * 1000.0
        telemetry = compacting.dispatcher.telemetry.as_dict() if compacting is not None else {}
        return q, trace_id, output, wall_ms, telemetry, (2 if prefetch is not None else 0)

    raw = await asyncio.gather(*(run_one(q) for q in questions), return_exceptions=True)
    records = {r.trace_id: r for r in processor.drain()}
    results: list[Any] = []
    failures: list[dict[str, Any]] = []
    for q, value in zip(questions, raw):
        if isinstance(value, BaseException):
            failures.append({"condition": condition, "question_id": q["question_id"], "error": f"{type(value).__name__}: {value}"[:500]})
            continue
        q_out, trace_id, output, wall_ms, telemetry, prefetch_calls = value
        trace = records.get(trace_id)
        if trace is None:
            failures.append({"condition": condition, "question_id": q["question_id"], "error": "missing completed SDK trace"})
            continue
        results.append(materialize(q_out, design=design, condition=condition, trace=trace, final_output=output.final_output,
                                   wall_ms=wall_ms, manifest=manifest, dispatch=telemetry, gold=gold[q_out["question_id"]],
                                   db_sha=db_sha, prefetch_calls=prefetch_calls))
    return results, failures


# --------------------------------------------------------------------------- compile and strict audit
def qualified(results: Sequence[Any]) -> list[Any]:
    """QUALIFY: completed runs with an answer and a valid trace. Correctness is NOT a filter."""
    return [r for r in results if r.condition == "discovery" and r.quality.get("answered") and r.quality.get("trace_valid")]


def compile_family(db: str, design: str, discovery: Sequence[Any], catalog: Any, manifest: Any) -> tuple[Any, dict[str, Any]]:
    from guarded_agentic_compaction.evaluation.splits import Splits
    from guarded_agentic_compaction.grc.compile import GrcConfig, compile_grc
    from guarded_agentic_compaction.registry.store import Registry
    from guarded_agentic_compaction.schema.artifacts import Lifecycle

    runs = qualified(discovery)
    train_n, dev_n, cal_n = 16, 8, 92
    needed = train_n + dev_n + cal_n
    record: dict[str, Any] = {"database": db, "design": design, "discovery_runs": len(discovery), "qualified": len(runs),
                              "qualify_rule": "completed run with a structured answer and a valid trace; answer correctness is not a filter",
                              "observed_opening_sequences": dict(Counter(" -> ".join(r.tool_sequence[:3]) for r in runs).most_common(8))}
    if len(runs) < needed:
        record.update({"status": "retired", "stage": "qualify", "reason": f"only {len(runs)} qualified traces; need {needed}"})
        return None, record
    selected = sorted(runs, key=lambda r: _sha(f"bird-compile-split:{SPLIT_SEED}:{design}:{db}:{r.issue_number}"))[:needed]
    train, dev, cal = selected[:train_n], selected[train_n:train_n + dev_n], selected[train_n + dev_n:]
    splits = Splits(train=frozenset(r.episode.group_id for r in train), dev=frozenset(r.episode.group_id for r in dev),
                    calibration=frozenset(r.episode.group_id for r in cal), seed=SPLIT_SEED)
    config = GrcConfig(entry_schema=("database",), partition_by=(), w_min=2, w_max=3, b_min=2, s_min=5, min_principals=1,
                       min_days=1, alpha=0.05, delta=0.10, phi_min=0.02, max_candidates=8, max_artifacts=2,
                       max_calibration_windows=cal_n, mode="replay", owner=f"paper-bird-{design}-{db}", seed=SPLIT_SEED,
                       synthesize_composites=False)
    result = compile_grc([r.episode for r in selected], catalog, splits, manifest, config, sandbox=None, perturbations=())
    candidates = [{**c.as_dict(), "gate": c.gate.to_dict() if c.gate is not None else None} for c in result.candidates]
    m = sum(1 for c in result.candidates if c.gate is not None)
    record.update({"config": asdict(config), "splits": splits.manifest(), "report": result.report(), "candidates": candidates,
                   "candidates_reaching_calibration": m, "rejection_by_stage": dict(result.rejection_by_stage),
                   "train_opening_sequences": dict(Counter(" -> ".join(r.tool_sequence[:3]) for r in train))})
    admitted = [a for a in result.artifacts if not a.gate.retire]
    if not admitted:
        record.update({"status": "retired", "stage": "compiler"})
        return None, record
    artifact = max(admitted, key=lambda a: (a.evidence.removed_requests, a.evidence.support_groups))
    audit = strict_audit(artifact, cal)
    record.update({"artifact": artifact.to_dict(), "artifact_explanation": artifact.explain(), "strict_audit": audit})
    if audit["disagreements"]:
        record.update({"status": "retired", "stage": "strict_audit"})
        return None, record
    artifact.lifecycle = Lifecycle.ACTIVE
    artifact.approved_by = "paper-bird-protocol-lab-only"
    registry = Registry(name=f"paper-bird-{design}-{db}")
    registry.add(artifact)
    record["status"] = "admitted"
    return registry, record


def strict_audit(artifact: Any, calibration_runs: Sequence[Any]) -> dict[str, Any]:
    """Every calibration group: do the agent's recorded opening calls equal the program's derived calls?

    The compiler labels a group whose recording lacks the program's call as unproductive,
    which stays in the count; at runtime the program would have run. This audit counts any
    such argument disagreement and, by the registered protocol, vetoes the admission claim.
    """
    from guarded_agentic_compaction.runtime.facade import Recording
    from guarded_agentic_compaction.runtime.interp import _eval_args

    steps = list(artifact.program.steps)
    disagreements: list[dict[str, Any]] = []
    for run in calibration_runs:
        recording = Recording.from_episode(run.episode)
        env: dict[str, Any] = {"z": dict(run.episode.entry_state)}
        for i, step in enumerate(steps):
            try:
                derived = _eval_args(step.args, env)
            except Exception as exc:  # noqa: BLE001
                disagreements.append({"question_id": run.issue_number, "step": i, "reason": f"binding:{exc}"[:200]})
                break
            recorded_tool = run.tool_sequence[i] if i < len(run.tool_sequence) else None
            recorded_args = run.tool_arguments[i] if i < len(run.tool_arguments) else None
            if recorded_tool != step.tool or recorded_args != derived:
                disagreements.append({"question_id": run.issue_number, "step": i, "program": [step.tool, derived],
                                      "agent": [recorded_tool, recorded_args]})
                break
            try:
                env[step.var] = recording.get(step.tool, derived)
            except Exception as exc:  # noqa: BLE001
                disagreements.append({"question_id": run.issue_number, "step": i, "reason": f"recording:{exc}"[:200]})
                break
    return {"calibration_groups": len(calibration_runs), "disagreements": disagreements,
            "rule": "any calibration group whose recorded opening calls differ from the program's derived calls vetoes the admission claim"}


# --------------------------------------------------------------------------- checkpoints
class Ledger:
    def __init__(self, path: Path, cap: float | None) -> None:
        self.path, self.cap = path, cap
        self.state = json.loads(path.read_text()) if path.exists() else {"spent_usd": 0.0, "entries": []}

    def charge(self, phase: str, results: Sequence[Any]) -> None:
        cost = float(sum(float(r.metrics.get("estimated_cost_usd") or 0.0) for r in results))
        self.state["spent_usd"] = round(self.state["spent_usd"] + cost, 6)
        self.state["entries"].append({"phase": phase, "results": len(results), "estimated_cost_usd": round(cost, 6),
                                      "cumulative_usd": self.state["spent_usd"], "at": datetime.now(UTC).isoformat(timespec="seconds")})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.state, indent=2) + "\n")

    def reserve(self, n: int, per_record: float = 0.03) -> None:
        if self.cap is None:
            raise RuntimeError("live phase without --approved-spend-usd")
        if self.state["spent_usd"] + n * per_record > self.cap:
            raise RuntimeError(f"reservation {n}x{per_record} would exceed cap {self.cap} (spent {self.state['spent_usd']})")


def save_runs(path: Path, results: Sequence[Any], failures: Sequence[dict[str, Any]], meta: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema": "agent-compaction-bird-runs/v1", "run": meta, "failures": list(failures),
               "results": [r.public_dict() for r in results]}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")
    with gzip.open(path.with_suffix(".episodes.jsonl.gz"), "wt", encoding="utf-8") as handle:
        for r in results:
            handle.write(json.dumps({"question_id": r.issue_number, "condition": r.condition,
                                     "episode": r.episode.to_dict()}, sort_keys=True, default=str) + "\n")


def load_runs(path: Path) -> tuple[list[Any], list[dict[str, Any]]]:
    import github_live_study as fixed
    from guarded_agentic_compaction.schema.traces import Episode

    if not path.exists():
        return [], []
    payload = json.loads(path.read_text())
    episodes: dict[tuple[str, int], Any] = {}
    ep_path = path.with_suffix(".episodes.jsonl.gz")
    if ep_path.exists():
        with gzip.open(ep_path, "rt", encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                episodes[(row["condition"], int(row["question_id"]))] = Episode.from_dict(row["episode"])
    results = []
    for d in payload["results"]:
        results.append(fixed.RunResult(condition=d["condition"], repeat=int(d.get("repeat", 0)), issue_number=int(d["issue_number"]),
                                       trace_id=d["trace_id"], metrics=d["metrics"], answer=d["answer"], quality=d["quality"],
                                       tool_sequence=d["tool_sequence"], tool_arguments=d["tool_arguments"], dispatch=d["dispatch"],
                                       episode=episodes.get((d["condition"], int(d["issue_number"])))))
    return results, list(payload.get("failures", []))


# --------------------------------------------------------------------------- phases
def preflight(out: Path) -> dict[str, Any]:
    archive_sha = _file_sha(BIRD_ARCHIVE)
    if archive_sha != BIRD_ARCHIVE_SHA256:
        raise RuntimeError(f"BIRD archive digest {archive_sha} != pinned {BIRD_ARCHIVE_SHA256}")
    questions = load_questions()
    fams = families(questions)
    if set(fams) & set(SMOKE_DATABASES):
        raise RuntimeError("a smoke-test database is also a family")
    counts = Counter(q["db_id"] for q in questions)
    selections = {db: select(questions, db) for db in fams}
    gold = gold_results(questions, fams)
    dbs: dict[str, Any] = {}
    for db in list(fams) + list(SMOKE_DATABASES):
        database = BirdDatabase(db)
        listing = database.list_tables()
        schema = database.get_schema(listing["tables"])
        dbs[db] = {"sqlite_sha256": _file_sha(db_path(db)), "tables": listing["tables"], "questions": counts[db],
                   "full_schema_chars": len(json.dumps(schema, sort_keys=True, default=str)),
                   "tool_determinism": _digest(database.get_schema(listing["tables"])) == _digest(schema)}
    fam_gold = {db: dict(Counter("ok" if gold[qid][0] is not None else gold[qid][1]
                                  for qid in selections[db]["test"] + selections[db]["discovery"])) for db in fams}
    write_probe = BirdDatabase(fams[0]).run_query("CREATE TABLE gac_write_probe(x)")
    excluded = {}
    if SPLIT != "dev":  # the primary (dev) preflight is retained as registered
        for db in fams:
            ids = selections[db]["test"] + selections[db]["discovery"]
            failed = sum(1 for qid in ids if gold[qid][0] is None)
            if failed / len(ids) > GOLD_FAILURE_LIMIT:
                excluded[db] = f"gold SQL fails on {failed} of {len(ids)} selected questions (> {GOLD_FAILURE_LIMIT:.0%})"
    report = {
        "schema": "agent-compaction-bird-preflight/v1",
        "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "provider_calls": 0,
        "archive": {"url": BIRD_ARCHIVE_URL, "sha256": archive_sha, "license": "CC BY-SA 4.0 (BIRD)", "split": SPLIT_CONFIG[SPLIT]["release"]},
        "model": MODEL,
        "family_rule": f"every BIRD dev database with at least {FAMILY_MIN_QUESTIONS} questions",
        "dev_question_counts": dict(counts.most_common()),
        "families": fams,
        "smoke_databases": list(SMOKE_DATABASES),
        "databases": dbs,
        "selections": selections,
        "gold_status": fam_gold,
        "read_only_probe": write_probe,
        **({"excluded_families": excluded} if SPLIT != "dev" else {}),
        "prompts": {d: {"sha256": _sha(p), "text": p} for d, p in PROMPTS.items()},
        "conditions": list(CONDITIONS),
        "settings": {"query_timeout_s": QUERY_TIMEOUT_S, "grade_timeout_s": GRADE_TIMEOUT_S, "max_rows": MAX_ROWS,
                     "max_value_chars": MAX_VALUE_CHARS, "sample_rows": SAMPLE_ROWS, "max_turns": 12, "episode_timeout_s": 180,
                     "model_settings": {"reasoning_effort": "low", "verbosity": "low", "parallel_tool_calls": False, "store": False}},
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "preflight.json").write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    return report


def _questions_by_id() -> dict[int, dict[str, Any]]:
    return {q["question_id"]: q for q in load_questions()}


async def live(args: argparse.Namespace) -> int:
    from dotenv import load_dotenv

    import github_live_study as fixed
    from guarded_agentic_compaction.capture.agents_sdk import AgentsTraceProcessor
    from guarded_agentic_compaction.registry.store import Registry

    out: Path = args.out
    source: Path = args.source or out
    pre = json.loads((source / "preflight.json").read_text())
    by_id = _questions_by_id()
    gold = gold_results(list(by_id.values()), list(pre["families"]) + list(SMOKE_DATABASES))
    ledger = Ledger(out / "ledger.json", args.approved_spend_usd)
    load_dotenv(ROOT / ".env")
    key_env = fixed.provider_api_key_env(MODEL)
    if not os.getenv(key_env):
        raise RuntimeError(f"{key_env} is not set")
    from agents import add_trace_processor

    processor = AgentsTraceProcessor(include_sensitive_data=True, max_completed=20_000)
    add_trace_processor(processor)
    meta = {"timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"), "model": MODEL, "provider_backed": True,
            "benchmark": "bird-dev_20240627", "simulated": False, "secrets_serialized": False,
            "protocol": args.protocol, "preflight_sha256": _file_sha(source / "preflight.json"), "split": SPLIT}
    designs = [args.design] if args.design else list(DESIGNS)
    dbs = [args.database] if args.database else study_families(pre)

    def ctx(db: str, design: str) -> tuple[Any, Any, Any, str]:
        database = BirdDatabase(db)
        catalog = make_catalog(db)
        manifest = make_manifest(db, design, make_tools(database), catalog)
        return database, catalog, manifest, pre["databases"][db]["sqlite_sha256"]

    if args.phase == "smoke":
        for design in designs:
            for db in SMOKE_DATABASES:
                qs = sorted((q for q in by_id.values() if q["db_id"] == db), key=lambda q: _rank(db, q["question_id"]))[:SMOKE_PER_DESIGN]
                database, catalog, manifest, sha = ctx(db, design)
                ledger.reserve(len(qs))
                results, failures = await run_batch(qs, design=design, condition="discovery", database=database, processor=processor,
                                                    manifest=manifest, catalog=catalog, gold=gold, db_sha=sha, concurrency=args.concurrency)
                ledger.charge(f"smoke:{design}:{db}", results)
                save_runs(out / "smoke" / design / f"{db}.json", results, failures, meta)
                print(f"[bird] smoke {design}/{db}: {[(r.tool_sequence, r.quality['overall']) for r in results]} failures={len(failures)}")
        print(f"[bird] spent {ledger.state['spent_usd']:.4f}")
        return 0

    if args.phase == "discovery":
        for design in designs:
            for db in dbs:
                path = out / design / db / "discovery.json"
                done, failures = load_runs(path)
                completed = {r.issue_number for r in done}
                todo = [by_id[qid] for qid in pre["selections"][db]["discovery"] if qid not in completed]
                if args.limit:
                    todo = todo[: args.limit]
                database, catalog, manifest, sha = ctx(db, design)
                for start in range(0, len(todo), args.batch):
                    chunk = todo[start:start + args.batch]
                    ledger.reserve(len(chunk))
                    results, fails = await run_batch(chunk, design=design, condition="discovery", database=database, processor=processor,
                                                     manifest=manifest, catalog=catalog, gold=gold, db_sha=sha, concurrency=args.concurrency)
                    ledger.charge(f"discovery:{design}:{db}", results)
                    done.extend(results)
                    failures.extend(fails)
                    save_runs(path, done, failures, meta)
                    print(f"[bird] discovery {design}/{db}: {len(done)}/{len(pre['selections'][db]['discovery'])} "
                          f"correct={sum(r.quality['overall'] for r in done)} failures={len(failures)} spent={ledger.state['spent_usd']:.4f}", flush=True)
        return 0

    if args.phase == "plumbing":
        # Extension protocol E3: compiled runs on two DISCOVERY questions per admitted family,
        # checking that synthesized calls pass through the provider adapter. Never analyzed.
        for design in designs:
            for db in dbs:
                compile_path = source / design / db / "compile.json"
                if not compile_path.exists() or json.loads(compile_path.read_text()).get("status") != "admitted":
                    continue
                registry = Registry.load(source / design / db / "registry")
                database, catalog, manifest, sha = ctx(db, design)
                qs = [by_id[qid] for qid in pre["selections"][db]["discovery"][:2]]
                ledger.reserve(len(qs))
                results, fails = await run_batch(qs, design=design, condition="compiled", database=database, processor=processor,
                                                 manifest=manifest, catalog=catalog, gold=gold, db_sha=sha, concurrency=2, registry=registry)
                ledger.charge(f"plumbing:{design}:{db}", results)
                save_runs(out / "plumbing" / design / f"{db}.json", results, fails, meta)
                print(f"[bird] plumbing {design}/{db}: dispatched={[int((r.dispatch or {}).get('compacted', 0)) for r in results]} "
                      f"requests={[r.metrics['requests'] for r in results]} failures={len(fails)}", flush=True)
        return 0

    if args.phase == "test":
        for design in designs:
            for db in dbs:
                compile_path = source / design / db / "compile.json"
                if not compile_path.exists() or json.loads(compile_path.read_text()).get("status") != "admitted":
                    continue
                registry = Registry.load(source / design / db / "registry")
                path = out / design / db / "evaluation.json"
                done, failures = load_runs(path)
                completed = {(r.condition, r.issue_number) for r in done}
                database, catalog, manifest, sha = ctx(db, design)
                test_ids = pre["selections"][db]["test"]
                # Order. The primary run (2026-10-08, ``--order fixed``) executed the conditions in
                # the fixed order of CONDITIONS per family, not rotated by record as registered; the
                # protocol records that deviation. ``--order rotated`` (the default from the
                # extension protocol on) runs round r with record i in condition (i + r) mod 4, so
                # every condition takes every position equally often across records.
                rounds: list[list[tuple[str, dict[str, Any]]]] = [[] for _ in CONDITIONS]
                for index, qid in enumerate(test_ids):
                    for r in range(len(CONDITIONS)):
                        condition = CONDITIONS[r] if args.order == "fixed" else CONDITIONS[(index + r) % len(CONDITIONS)]
                        if (condition, qid) not in completed:
                            rounds[r].append((condition, by_id[qid]))
                for r, items in enumerate(rounds):
                    for condition in CONDITIONS:
                        todo = [q for c, q in items if c == condition]
                        if not todo:
                            continue
                        ledger.reserve(len(todo))
                        results, fails = await run_batch(todo, design=design, condition=condition, database=database, processor=processor,
                                                         manifest=manifest, catalog=catalog, gold=gold, db_sha=sha, concurrency=args.concurrency,
                                                         registry=registry if condition == "compiled" else None)
                        ledger.charge(f"test:{design}:{db}:round{r}:{condition}", results)
                        done.extend(results)
                        failures.extend(fails)
                        save_runs(path, done, failures, meta)
                        print(f"[bird] test {design}/{db}/round{r}/{condition}: {sum(r_.quality['overall'] for r_ in results)}/{len(results)} "
                              f"failures={len(fails)} spent={ledger.state['spent_usd']:.4f}", flush=True)
        return 0
    raise ValueError(args.phase)


def compile_phase(out: Path, designs: Sequence[str], dbs: Sequence[str]) -> None:
    for design in designs:
        for db in dbs:
            path = out / design / db / "discovery.json"
            discovery, failures = load_runs(path)
            if not discovery:
                continue
            database = BirdDatabase(db)
            catalog = make_catalog(db)
            manifest = make_manifest(db, design, make_tools(database), catalog)
            registry, record = compile_family(db, design, discovery, catalog, manifest)
            record["discovery_failures"] = len(failures)
            record["discovery_execution_correct"] = sum(bool(r.quality["overall"]) for r in discovery)
            target = out / design / db
            if registry is not None:
                registry.save(target / "registry")
            (target / "compile.json").write_text(json.dumps(record, indent=2, sort_keys=True, default=str) + "\n")
            print(f"[bird] compile {design}/{db}: {record['status']} ({record.get('stage', '')}); "
                  f"openings {list(record.get('observed_opening_sequences', {}).items())[:2]}")


def _paired_bootstrap(base: Sequence[float], cand: Sequence[float], seed: int = SPLIT_SEED, n: int = 10_000) -> list[float]:
    rng = random.Random(seed)
    k = len(base)
    if not k:
        return [float("nan"), float("nan")]
    stats_ = []
    for _ in range(n):
        idx = [rng.randrange(k) for _ in range(k)]
        b = sum(base[i] for i in idx)
        c = sum(cand[i] for i in idx)
        stats_.append(1.0 - c / b if b else 0.0)
    stats_.sort()
    return [stats_[int(0.025 * n)], stats_[int(0.975 * n) - 1]]


def summarize(out: Path, source: Path | None = None, *, table: bool = True) -> dict[str, Any]:
    from scipy.stats import binomtest

    source = source or out
    pre = json.loads((source / "preflight.json").read_text())
    summary: dict[str, Any] = {"schema": "agent-compaction-bird-summary/v1", "model": MODEL, "split": SPLIT, "designs": {}}
    for design in DESIGNS:
        fam_out: dict[str, Any] = {}
        pooled: dict[str, list[Any]] = {c: [] for c in CONDITIONS}
        for db in study_families(pre):
            target = out / design / db
            src = source / design / db
            compile_record = json.loads((src / "compile.json").read_text()) if (src / "compile.json").exists() else None
            discovery, disc_fail = load_runs(src / "discovery.json")
            entry: dict[str, Any] = {
                "discovery_runs": len(discovery), "discovery_failures": len(disc_fail),
                "discovery_execution_correct": sum(bool(r.quality["overall"]) for r in discovery),
                "status": compile_record.get("status") if compile_record else None,
                "stage": compile_record.get("stage") if compile_record else None,
                "candidates_reaching_calibration": compile_record.get("candidates_reaching_calibration") if compile_record else None,
                "opening_sequences": dict(Counter(" -> ".join(r.tool_sequence[:2]) for r in discovery).most_common(4)),
                "schema_all_tables_share": (sum(1 for r in discovery if len(r.tool_arguments) > 1 and r.tool_sequence[:2] == ["list_tables", "get_schema"]
                                                and r.tool_arguments[1].get("table_names") == pre["databases"][db]["tables"]) / len(discovery)) if discovery else None,
            }
            if compile_record and compile_record.get("artifact"):
                art = compile_record["artifact"]
                entry["artifact_tools"] = [s.get("tool") for s in (art.get("program") or {}).get("steps", [])]
                entry["gate"] = {k: (art.get("gate") or {}).get(k) for k in ("n_calibration_groups", "observed_violations", "risk_upper_bound", "threshold", "coverage", "retire")}
                entry["strict_audit_disagreements"] = len((compile_record.get("strict_audit") or {}).get("disagreements", []))
            evaluation, eval_fail = load_runs(target / "evaluation.json")
            if evaluation:
                by = {c: {r.issue_number: r for r in evaluation if r.condition == c} for c in CONDITIONS}
                common = sorted(set.intersection(*(set(v) for v in by.values())))
                entry["evaluation"] = {"n": len(common), "failures": len(eval_fail),
                                       "correct": {c: sum(bool(by[c][q].quality["overall"]) for q in common) for c in CONDITIONS},
                                       "compiled_dispatched": sum(1 for q in common if int((by["compiled"][q].dispatch or {}).get("compacted", 0)) > 0),
                                       "mean": {c: {m: statistics.mean(float(by[c][q].metrics.get(m) or 0.0) for q in common) for m in
                                                    ("requests", "total_tokens", "wall_latency_ms", "estimated_cost_usd")} for c in CONDITIONS} if common else {}}
                for c in CONDITIONS:
                    pooled[c].extend(by[c][q] for q in common)
            fam_out[db] = entry
        design_out: dict[str, Any] = {"families": fam_out}
        if pooled["baseline"] and pooled["compiled"]:
            base = {r.issue_number: r for r in pooled["baseline"]}
            comparisons: dict[str, Any] = {}
            warm = {r.issue_number: r for r in pooled["baseline_repeat"]}
            cache_share = {c: (sum(int(r.metrics.get("cached_input_tokens") or 0) for r in pooled[c])
                               / max(1, sum(int(r.metrics.get("input_tokens") or 0) for r in pooled[c]))) for c in CONDITIONS}
            design_out["cached_input_share"] = cache_share
            for cand_name in ("compiled", "manual_schema_prefetch", "baseline_repeat"):
                cand = {r.issue_number: r for r in pooled[cand_name]}
                keys = sorted(set(base) & set(cand))
                b_ok = [bool(base[k].quality["overall"]) for k in keys]
                c_ok = [bool(cand[k].quality["overall"]) for k in keys]
                base_only = sum(b and not c for b, c in zip(b_ok, c_ok))
                cand_only = sum(c and not b for b, c in zip(b_ok, c_ok))
                diffs = [float(c) - float(b) for b, c in zip(b_ok, c_ok)]
                rng = random.Random(SPLIT_SEED + 1)
                boots = sorted(statistics.mean(diffs[rng.randrange(len(diffs))] for _ in diffs) for _ in range(10_000))
                reductions = {}
                for m in ("requests", "total_tokens", "wall_latency_ms", "estimated_cost_usd"):
                    bv = [float(base[k].metrics.get(m) or 0.0) for k in keys]
                    cv = [float(cand[k].metrics.get(m) or 0.0) for k in keys]
                    reductions[m] = {"reduction": 1.0 - sum(cv) / sum(bv) if sum(bv) else None, "ci95": _paired_bootstrap(bv, cv)}
                warm_reductions = {}
                if cand_name != "baseline_repeat":
                    for m in ("requests", "total_tokens", "wall_latency_ms", "estimated_cost_usd"):
                        wv = [float(warm[k].metrics.get(m) or 0.0) for k in keys]
                        cv = [float(cand[k].metrics.get(m) or 0.0) for k in keys]
                        warm_reductions[m] = {"reduction": 1.0 - sum(cv) / sum(wv) if sum(wv) else None, "ci95": _paired_bootstrap(wv, cv)}
                comparisons[cand_name] = {
                    "reductions_vs_warm_repeat": warm_reductions,
                    "n": len(keys), "baseline_correct": sum(b_ok), "candidate_correct": sum(c_ok),
                    "baseline_only_correct": base_only, "candidate_only_correct": cand_only,
                    "mcnemar_exact_p": float(binomtest(min(base_only, cand_only), base_only + cand_only, 0.5).pvalue) if base_only + cand_only else 1.0,
                    "accuracy_difference": statistics.mean(diffs), "accuracy_difference_ci95": [boots[250], boots[9749]],
                    "reductions": reductions,
                }
            design_out["pooled"] = comparisons
        summary["designs"][design] = design_out
    ledger_path = out / "ledger.json"
    summary["spent_usd"] = json.loads(ledger_path.read_text())["spent_usd"] if ledger_path.exists() else 0.0
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n")
    if table:
        write_table(summary, pre)
    return summary


TABLE_PATH = ROOT / "paper/iclr/tables/bird_results.tex"


def _standard_outcome(entry: dict[str, Any], out: Path, db: str) -> str:
    if entry.get("status") == "admitted":
        return "admit"
    if entry.get("stage") == "compiler":
        record = json.loads((out / "standard" / db / "compile.json").read_text())
        if record.get("candidates_reaching_calibration"):
            n = max((int((c.get("gate") or {}).get("n_calibration_groups") or 0)
                     for c in record.get("candidates", []) if c.get("gate")), default=0)
            return f"retire: support {n}/92" if n else "retire: calibration"
        return "retire: synthesis"
    return f"retire: {entry.get('stage')}"


def write_table(summary: dict[str, Any], pre: dict[str, Any], out: Path = OUT_ROOT) -> None:
    std = summary["designs"]["standard"]["families"]
    sf = summary["designs"]["schema_first"]["families"]
    lines = ["% generated by paper/scripts/bird_sql_agent_study.py --phase summarize; do not edit",
             r"\begin{tabular}{@{}lrlccccrrr@{}}", r"\toprule",
             r"& & Standard & \multicolumn{4}{c}{Schema-first: correct of 30} & \multicolumn{3}{c}{Compiled vs.\ warm repeat} \\",
             r"\cmidrule(lr){3-3}\cmidrule(lr){4-7}\cmidrule(l){8-10}",
             r"Database & Tables & GAC & Base & Repeat & Compiled & Manual & Requests & Tokens & Cost \\", r"\midrule"]
    for db in pre["families"]:
        e = sf.get(db, {})
        ev = e.get("evaluation") or {}
        c = ev.get("correct") or {}
        mean = ev.get("mean") or {}
        def red(metric: str) -> str:
            b, k = (mean.get("baseline_repeat") or {}).get(metric), (mean.get("compiled") or {}).get(metric)
            return f"{100 * (1 - k / b):.1f}\\%".replace("-", "$-$") if b and k is not None else "---"
        lines.append(
            f"\\code{{{db.replace('_', chr(92) + '_')}}} & {len(pre['databases'][db]['tables'])} & {_standard_outcome(std.get(db, {}), out, db)} & "
            f"{c.get('baseline', '---')} & {c.get('baseline_repeat', '---')} & \\textbf{{{c.get('compiled', '---')}}} & "
            f"{c.get('manual_schema_prefetch', '---')} & {red('requests')} & {red('total_tokens')} & {red('estimated_cost_usd')} \\\\")
    pooled = summary["designs"]["schema_first"].get("pooled") or {}
    comp = pooled.get("compiled")
    if comp:
        rep = pooled.get("baseline_repeat") or {}
        man = pooled.get("manual_schema_prefetch") or {}
        r = comp["reductions_vs_warm_repeat"]
        lines += [r"\midrule",
                  f"Pooled & & 5 retire & {comp['baseline_correct']} & {rep.get('candidate_correct', '---')} & "
                  f"\\textbf{{{comp['candidate_correct']}}} & {man.get('candidate_correct', '---')} & "
                  f"{100 * r['requests']['reduction']:.1f}\\% & {100 * r['total_tokens']['reduction']:.1f}\\% & "
                  f"{100 * r['estimated_cost_usd']['reduction']:.1f}\\% \\\\"]
    lines += [r"\bottomrule", r"\end{tabular}"]
    TABLE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=("preflight", "smoke", "discovery", "compile", "plumbing", "test", "summarize"), default="preflight")
    ap.add_argument("--design", choices=DESIGNS, default=None)
    ap.add_argument("--database", default=None)
    ap.add_argument("--approved-spend-usd", type=float, default=None)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--batch", type=int, default=24)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", type=Path, default=OUT_ROOT)
    ap.add_argument("--source", type=Path, default=None, help="directory holding preflight, discovery, compile and registry (default: --out)")
    ap.add_argument("--model", default="gpt-5.6-luna")
    ap.add_argument("--split", choices=tuple(SPLIT_CONFIG), default="dev")
    ap.add_argument("--order", choices=("rotated", "fixed"), default="rotated")
    ap.add_argument("--protocol", default="paper/supplementary/bird-sql-agent-protocol.md")
    ap.add_argument("--no-table", action="store_true", help="summarize without rewriting the paper table (replications)")
    args = ap.parse_args(argv)
    configure(model=args.model, split=args.split)
    if args.phase == "preflight":
        report = preflight(args.out)
        print(json.dumps({"families": report["families"], "tables": {d: len(v["tables"]) for d, v in report["databases"].items()},
                          "gold_status": report["gold_status"], "read_only_probe": report["read_only_probe"]}, indent=1))
        return 0
    if args.phase == "compile":
        pre = json.loads((args.out / "preflight.json").read_text())
        compile_phase(args.out, [args.design] if args.design else list(DESIGNS), [args.database] if args.database else study_families(pre))
        return 0
    if args.phase == "summarize":
        print(json.dumps(summarize(args.out, args.source, table=not args.no_table), indent=1, default=str)[:4000])
        return 0
    return asyncio.run(live(args))


if __name__ == "__main__":
    raise SystemExit(main())
