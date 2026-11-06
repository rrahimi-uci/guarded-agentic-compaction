"""Equal-information SQL tools and isolated execution for the exploratory pilot."""
import asyncio
import json
from pathlib import Path
import uuid

from adaptive_sql_grader import execute
from probe_agent_jit_sql import registry as fixture_registry

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "python@sha256:09a17cad02668ae61ece136b4fd36ac3849e14f670ebedb637ea3e15580525bc"
INSTRUCTIONS = """Solve the SQLite question using the supplied database and evidence.
First list tables, then read the schemas of relevant tables before querying.
Tools return an object whose payload field is a JSON string. Parse it to access
tables, schemas or query rows. Select relevant tables adaptively; do not assume
database schema from memory. You may refine a query after seeing its results.
Return ONLY a JSON object with one string field sql containing the final query.
The final query is evaluated separately. Never substitute displayed sample rows
for the SQL answer. Do not modify the database."""


def dumps(value):
    return json.dumps(value, sort_keys=True, default=str, ensure_ascii=False)


def registry():
    reg = fixture_registry()
    descriptions = {"list_tables": "List table names. payload is JSON {tables: [names]}.",
        "get_schema": "Read CREATE SQL and three sample rows for each requested table. payload is JSON {schemas: [...]}.",
        "run_query": "Execute read-only SQLite SQL. payload has status, column_count, up to 20 rows and displayed_rows_truncated."}
    for tool in reg["tools"]:
        tool["description"] = descriptions[tool["name"]]
        tool["output_schema"] = {"type": "object", "properties": {"payload": {"type": "string"}}, "required": ["payload"]}
        tool["input_schema"]["additionalProperties"] = False
    return reg


class SQLTools:
    def __init__(self, path):
        self.path = Path(path)
        self.listed = False
        self.schema = False
        self.calls = []

    def call(self, name, args):
        if len(self.calls) >= 64:
            raise RuntimeError("tool call cap")
        row = {"tool": name, "arguments": args}
        self.calls.append(row)
        try:
            value = self._call(name, args)
        except Exception as exc:
            value = {"error": type(exc).__name__, "detail": str(exc)[:200]}
        result = {"payload": dumps(value)}
        if len(dumps(result).encode()) > 160_000:
            result = {"payload": dumps({"error": "tool_output_limit"})}
        row["result"] = result
        return result

    def _call(self, name, args):
        schemas = {t["name"]: t["input_schema"] for t in registry()["tools"]}
        if name not in schemas:
            raise ValueError("unknown tool")
        # Runtime validation is independent of upstream static admission.
        from jsonschema import validate
        validate(args, schemas[name])
        if name == "list_tables":
            result = execute(self.path, "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
            if result.status != "ok":
                raise RuntimeError(result.status)
            self.listed = True
            return {"tables": [r[0] for r in result.rows]}
        if name == "get_schema":
            if not self.listed:
                raise ValueError("list_tables prerequisite missing")
            all_tables = execute(self.path, "SELECT name,sql FROM sqlite_master WHERE type='table'")
            if all_tables.status != "ok":
                raise RuntimeError(all_tables.status)
            mapping = dict(all_tables.rows)
            names = args["table_names"]
            if not names or len(names) > 100 or any(n not in mapping for n in names):
                raise ValueError("request one or more existing tables")
            rows = []
            for name in names:
                quoted = '"' + name.replace('"', '""') + '"'
                sample = execute(self.path, f"SELECT * FROM {quoted} LIMIT 3", max_bytes=100_000)
                rows.append({"table": name, "create_sql": mapping[name], "sample_status": sample.status, "sample_rows": sample.rows})
            self.schema = True
            return {"schemas": rows}
        if not self.schema:
            raise ValueError("get_schema prerequisite missing")
        result = execute(self.path, args["sql"], timeout=15, max_bytes=1_000_000)
        return {"status": result.status, "column_count": result.columns, "rows": result.rows[:20],
                "displayed_rows_truncated": len(result.rows) > 20}


async def run_container(code, dispatch, *, timeout=180):
    """No database/workspace/key mounts; host bounds and validates each RPC."""
    name = "gac-pilot-" + uuid.uuid4().hex
    worker = ROOT / "experiments/adaptive_compiler_pilot/container_worker.py"
    command = ["docker", "run", "--rm", "-i", "--name", name, "--network", "none",
        "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--pids-limit", "64", "--memory", "256m", "--cpus", "1",
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m", "--user", "65534:65534",
        "-v", f"{worker}:/app/worker.py:ro", IMAGE, "python", "-I", "/app/worker.py"]
    proc = await asyncio.create_subprocess_exec(*command, stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, limit=262_144)
    async def exchange():
        proc.stdin.write((dumps({"code": code}) + "\n").encode())
        await proc.stdin.drain()
        total = 0
        for _ in range(65):
            line = await proc.stdout.readline()
            total += len(line)
            if not line or total > 2_000_000:
                raise RuntimeError("worker protocol/output limit")
            message = json.loads(line)
            if message.get("type") == "result":
                return message["result"]
            if message.get("type") != "call":
                raise RuntimeError("worker failure: " + str(message.get("error", "invalid message")))
            try:
                value = await dispatch(message["tool"], message["arguments"])
                reply = {"result": value}
            except Exception as exc:
                reply = {"error": type(exc).__name__}
            proc.stdin.write((dumps(reply) + "\n").encode())
            await proc.stdin.drain()
        raise RuntimeError("worker RPC cap")
    try:
        return await asyncio.wait_for(exchange(), timeout)
    finally:
        # Kill the container itself, not just the docker client, including on cancellation.
        remover = await asyncio.create_subprocess_exec("docker", "rm", "-f", name,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        await remover.wait()
        if proc.returncode is None:
            proc.kill()
        await proc.wait()
