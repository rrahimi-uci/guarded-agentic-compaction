"""Prospective executor fix: use pinned upstream LocalPythonExecutor in Docker.

Not used in the frozen v1/v2 live pilot. /upstream contains only the three pinned
stdlib-only executor/checker files, with an empty package initializer. Host RPC
must retain the same limits and SQL validation as the pilot.
"""
import asyncio
import contextlib
import io
import json
import sys
from types import SimpleNamespace

sys.path.insert(0, "/")
from upstream.local_python_executor import LocalPythonExecutor


class Payload(SimpleNamespace):
    def model_dump(self):
        return vars(self)


def plain(value):
    if isinstance(value, SimpleNamespace):
        return {k: plain(v) for k, v in vars(value).items()}
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def send(value):
    sys.__stdout__.write(json.dumps(value) + "\n")
    sys.__stdout__.flush()


async def rpc(tool, arguments):
    send({"type": "call", "tool": tool, "arguments": plain(arguments)})
    reply = json.loads(sys.stdin.readline())
    if "error" in reply:
        raise RuntimeError(reply["error"])
    value = reply["result"]
    return Payload(**value) if tool != "ai_eval" and isinstance(value, dict) else value


async def list_tables():
    return await rpc("list_tables", {})


async def get_schema(table_names):
    return await rpc("get_schema", {"table_names": table_names})


async def run_query(sql):
    return await rpc("run_query", {"sql": sql})


async def ai_eval(expr, **kwargs):
    return await rpc("ai_eval", {"prompt": expr, "data": kwargs})


async def main():
    spec = json.loads(sys.stdin.readline())
    executor = LocalPythonExecutor(additional_functions={"list_tables": list_tables,
        "get_schema": get_schema, "run_query": run_query, "ai_eval": ai_eval})
    try:
        # Upstream captures print itself and mirrors logs to stdout. Keep logs
        # off the RPC channel while preserving upstream state/result semantics.
        with contextlib.redirect_stdout(io.StringIO()):
            result = await executor(spec["code"])
        if result.error:
            send({"type": "failure", "error": result.error[:500]})
        else:
            send({"type": "result", "result": plain(result.output), "logs": result.logs[:4096]})
    except BaseException as exc:
        send({"type": "failure", "error": type(exc).__name__})


if __name__ == "__main__":
    asyncio.run(main())
