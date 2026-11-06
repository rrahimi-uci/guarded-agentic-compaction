"""Reference harness around unmodified upstream executor (Docker only).

This checks adapter behavior, not an independently implemented executor.
"""
import asyncio
import contextlib
import io
import json
import sys
from types import SimpleNamespace

sys.path.insert(0, "/")
from upstream.local_python_executor import LocalPythonExecutor


class Result(SimpleNamespace):
    def model_dump(self):
        return vars(self)


def plain(value):
    if isinstance(value, SimpleNamespace):
        return plain(vars(value))
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    return value


def emit(message):
    sys.__stdout__.write(json.dumps(message) + "\n")
    sys.__stdout__.flush()


async def call(name, arguments):
    emit({"type": "call", "tool": name, "arguments": plain(arguments)})
    reply = json.loads(sys.stdin.readline())
    if "error" in reply:
        raise RuntimeError(reply["error"])
    value = reply["result"]
    if name == "ai_eval" or not isinstance(value, dict):
        return value
    return Result(**value)


async def list_tables():
    return await call("list_tables", {})


async def get_schema(table_names):
    return await call("get_schema", {"table_names": table_names})


async def run_query(sql):
    return await call("run_query", {"sql": sql})


async def ai_eval(expr, **kwargs):
    return await call("ai_eval", {"prompt": expr, "data": kwargs})


async def main():
    code = json.loads(sys.stdin.readline())["code"]
    functions = {name: globals()[name] for name in ("list_tables", "get_schema", "run_query", "ai_eval")}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            value = await LocalPythonExecutor(additional_functions=functions)(code)
        emit({"type": "failure", "error": value.error[:500]} if value.error else
             {"type": "result", "result": plain(value.output)})
    except BaseException as exc:
        emit({"type": "failure", "error": type(exc).__name__})


if __name__ == "__main__":
    asyncio.run(main())
