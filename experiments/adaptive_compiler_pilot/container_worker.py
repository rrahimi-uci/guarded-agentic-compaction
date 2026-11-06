"""Untrusted program worker: run only inside the pinned, networkless container.

No provider credentials or benchmark databases are available here. The host
validates and bounds every JSON RPC tool request independently.
"""
import ast
import asyncio
import builtins
import json
import sys
import types
from types import SimpleNamespace


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


async def rpc(tool, arguments):
    print(json.dumps({"type": "call", "tool": tool, "arguments": plain(arguments)}), flush=True)
    message = json.loads(sys.stdin.readline())
    if "error" in message:
        raise RuntimeError(message["error"])
    value = message["result"]
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
    # The OS container, not Python globals, is the security boundary.
    # Match upstream's JSON shim: ai_eval may return already parsed JSON.
    plan_json = types.ModuleType("json")
    plan_json.__dict__.update({k: v for k, v in vars(json).items() if not k.startswith("__")})
    plan_json.loads = lambda s, *a, **kw: s if s is None or isinstance(s, (dict, list, int, float, bool)) else json.loads(s, *a, **kw)
    def plan_import(name, *args, **kwargs):
        return plan_json if name == "json" else builtins.__import__(name, *args, **kwargs)
    namespace = {"list_tables": list_tables, "get_schema": get_schema,
                 "run_query": run_query, "ai_eval": ai_eval, "json": plan_json,
                 "__builtins__": {**vars(builtins), "__import__": plan_import}}
    try:
        code = compile(spec["code"], "<candidate>", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
        future = eval(code, namespace)
        if future is not None:
            await future
        print(json.dumps({"type": "result", "result": plain(namespace.get("result"))}), flush=True)
    except BaseException as exc:
        print(json.dumps({"type": "failure", "error": type(exc).__name__}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
