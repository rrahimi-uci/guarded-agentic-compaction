"""Run the pinned upstream static planner on synthetic SQL-tool programs.

Execute with the upstream checkout's isolated Python environment. No generated
program is executed, no provider is called, and this is not a live SQL adapter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/results/adaptive_comparison_preflight/agent_jit_probe.json"
PIN = "ad6df6b8d19573efa4a1155951c6a838f6b1b4d7"
FILES = ("agent_jit/planner.py", "agent_jit/definitions.py", "blastai/agents/models.py",
         "blastai/agents/codecheck.py", "blastai/agents/codecost.py",
         "blastai/agents/codegen.py", "agent_jit/adapters/planner.py", "uv.lock")


def registry():
    tools = []
    for name, params, out, pre, post, kind in [
        ("list_tables", {}, {"tables": {"type": "array", "items": {"type": "string"}}}, {}, {"tables_listed": True}, "listItems"),
        ("get_schema", {"table_names": {"type": "array", "items": {"type": "string"}}},
         {"schema": {"type": "string"}}, {"tables_listed": True}, {"schema_read": True}, "getFields"),
        ("run_query", {"sql": {"type": "string"}}, {"answer": {"type": "string"}},
         {"schema_read": True}, {}, "getFields"),
    ]:
        tools.append({"name": name, "title": name, "description": "Synthetic contract fixture; no runtime implementation.",
            "tool_executor_type": "smcp", "type": kind, "lang": "js", "pre": pre, "post": post,
            "input_schema": {"type": "object", "properties": params, "required": list(params)},
            "output_schema": {"type": "object", "properties": out, "required": list(out)}})
    return {"tools": tools}


PROGRAMS = {
    "valid": 'tables = await list_tables()\nschema = await get_schema(table_names=tables.tables)\nanswer = await run_query(sql="SELECT 1")\nresult = answer.answer\n',
    "missing_list": 'schema = await get_schema(table_names=["t"])\nresult = schema.schema\n',
    "missing_schema": 'tables = await list_tables()\nanswer = await run_query(sql="SELECT 1")\nresult = answer.answer\n',
    "wrong_type": 'tables = await list_tables()\nschema = await get_schema(table_names=tables.tables)\nanswer = await run_query(sql=123)\nresult = answer.answer\n',
    "wrong_answer_valid_contract": 'tables = await list_tables()\nschema = await get_schema(table_names=tables.tables)\nanswer = await run_query(sql="SELECT 2")\nresult = answer.answer\n',
    "redundant_query": 'tables = await list_tables()\nschema = await get_schema(table_names=tables.tables)\nunused = await run_query(sql="SELECT 1")\nanswer = await run_query(sql="SELECT 1")\nresult = answer.answer\n',
}


def main(checkout):
    commit = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(["git", "-C", str(checkout), "status", "--porcelain", "--untracked-files=no"], text=True)
    if commit != PIN or dirty:
        raise ValueError("requires an unmodified pinned upstream checkout")
    sys.path.insert(0, str(checkout))
    # Upstream checks invoke ty by name; use the isolated interpreter's bin dir.
    os.environ["PATH"] = str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]
    from agent_jit.planner import rank
    with tempfile.TemporaryDirectory(prefix="gac-jit-static-") as tmp:
        base = Path(tmp)
        reg = base / "registry.json"
        reg.write_text(json.dumps(registry()))
        paths = []
        for name, program in PROGRAMS.items():
            path = base / f"{name}.py"
            path.write_text(program)
            paths.append(path)
        result = rank(paths, reg, {"tables_listed": False, "schema_read": False})
        for row in result["candidates"]:
            row["path"] = Path(row["path"]).stem
        result["selected"] = Path(result["selected"]).stem if result["selected"] else None
        result["tied_candidates"] = [Path(p).stem for p in result["tied_candidates"]]
    observed = {r["path"]: r["valid"] for r in result["candidates"]}
    expected = {name: name in {"valid", "wrong_answer_valid_contract", "redundant_query"} for name in PROGRAMS}
    if observed != expected or result["selected"] != "valid":
        raise ValueError(f"static adapter assumptions failed: {result}")
    report = {"schema": "gac-agent-jit-static-probe-v1", "provider_calls": 0,
        "python_version": sys.version,
        "upstream_url": "https://github.com/agent-jit-compilation/agent-jit-compilation", "commit": commit,
        "upstream_file_hashes": {p: hashlib.sha256((checkout / p).read_bytes()).hexdigest() for p in FILES},
        "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "registry": registry(), "programs": PROGRAMS, "result": result,
        "scope": "Six hand-authored synthetic programs checked and ranked by unmodified upstream code; no plan generation or execution.",
        "decision": "STATIC_SQL_CONTRACT_MAPPING_FEASIBLE_LIVE_ADAPTER_UNIMPLEMENTED",
        "remaining": ["Implement equal-information SQL tool return types and runtime dispatch.",
            "Preserve upstream generation, candidate accounting, validation and cost ranking.",
            "Isolate generated program execution and enforce shared time, tool and provider budgets.",
            "Verify adaptive inference, fallback, rejected candidates and failures end to end.",
            "Document SQL adaptation rather than claiming native browser reproduction."]}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"commit": commit, "observed": observed, "selected": result["selected"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    main(parser.parse_args().checkout.resolve())
