"""Provider-free parity check against the pinned upstream Python executor.

Both executors run in networkless containers; no generated Python runs on host.
This probe characterizes the frozen pilot, and does not repair/replace outcomes.
"""
import argparse
import asyncio
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

from adaptive_pilot import OUT, ROOT, digest, write
from adaptive_pilot_runtime import IMAGE, run_container
from probe_agent_jit_sql import PIN

PROGRAMS = {
    "assigned_result": 'result = {"sql": "SELECT 1"}',
    "printed_then_assigned": 'print("diagnostic")\nresult = {"sql": "SELECT 1"}',
    "top_level_return": 'result = {"sql": "SELECT 1"}\nreturn result',
    "last_binding": 'answer = {"sql": "SELECT 1"}',
    "rpc_with_print": 'import json\ntables = await list_tables()\nprint("diagnostic")\nresult = {"tables": json.loads(tables.payload)["tables"]}',
}
FILES = ("local_python_executor.py", "codecheck.py", "cfg_builder.py")
DRIVER = '''import asyncio, contextlib, io, json, sys
from types import SimpleNamespace
sys.path.insert(0, "/probe")
from upstream.local_python_executor import LocalPythonExecutor
async def list_tables():
    return SimpleNamespace(payload=json.dumps({"tables": ["t"]}))
async def main():
    results = {}
    for name, code in json.load(sys.stdin).items():
        with contextlib.redirect_stdout(io.StringIO()):
            value = await LocalPythonExecutor(additional_functions={"list_tables": list_tables})(code)
        results[name] = {"output": value.output, "error": value.error}
    print(json.dumps(results))
asyncio.run(main())
'''


async def probe(checkout):
    commit = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    if commit != PIN or subprocess.check_output(["git", "-C", str(checkout), "diff", "--name-only", "HEAD"], text=True).strip():
        raise ValueError("requires unmodified pinned upstream checkout")
    with tempfile.TemporaryDirectory(prefix="gac-runtime-parity-") as temporary:
        base = Path(temporary)
        (base / "upstream").mkdir()
        (base / "upstream/__init__.py").write_text("")
        hashes = {}
        for name in FILES:
            source = checkout / "blastai/agents" / name
            shutil.copyfile(source, base / "upstream" / name)
            hashes[name] = digest(source)
        (base / "driver.py").write_text(DRIVER)
        name = "gac-parity-" + uuid.uuid4().hex
        try:
            output = subprocess.run(["docker", "run", "--rm", "-i", "--name", name,
                "--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--pids-limit", "64", "--memory", "256m", "--cpus", "1", "--user", "65534:65534",
                "-v", f"{base}:/probe:ro", IMAGE, "python", "-I", "/probe/driver.py"],
                input=json.dumps(PROGRAMS), text=True, capture_output=True, timeout=30, check=True)
            upstream = json.loads(output.stdout)
        finally:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=15)
        prospective = {}
        native_worker = ROOT / "experiments/adaptive_compiler_pilot/container_worker_native.py"
        for fixture, code in PROGRAMS.items():
            name = "gac-native-parity-" + uuid.uuid4().hex
            try:
                output = subprocess.run(["docker", "run", "--rm", "-i", "--name", name,
                    "--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                    "--pids-limit", "64", "--memory", "256m", "--cpus", "1", "--user", "65534:65534",
                    "-v", f"{base / 'upstream'}:/upstream:ro", "-v", f"{native_worker}:/worker.py:ro",
                    IMAGE, "python", "-I", "/worker.py"], input=json.dumps({"code": code}) + "\n" + json.dumps({"result": {"payload": '{"tables": ["t"]}'}}) + "\n",
                    text=True, capture_output=True, timeout=20, check=True)
                messages = [json.loads(line) for line in output.stdout.splitlines()]
                for request in messages[:-1]:
                    assert request == {"type": "call", "tool": "list_tables", "arguments": {}}
                message = messages[-1]
                prospective[fixture] = {"output": message.get("result"), "error": message.get("error")}
            finally:
                subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=15)
    async def no_tools(name, args):
        assert name == "list_tables" and args == {}
        return {"payload": '{"tables": ["t"]}'}
    rows = []
    for name, code in PROGRAMS.items():
        try:
            local = {"output": await run_container(code, no_tools, timeout=20), "error": None}
        except Exception as exc:
            local = {"output": None, "error": str(exc)}
        same = (bool(local["error"]) == bool(upstream[name]["error"]) and local["output"] == upstream[name]["output"])
        replacement = prospective[name]
        proposed_same = (bool(replacement["error"]) == bool(upstream[name]["error"]) and replacement["output"] == upstream[name]["output"])
        rows.append({"fixture": name, "code": code, "upstream": upstream[name], "pilot_worker": local,
                     "same_success_and_output": same, "prospective_worker": replacement, "prospective_matches": proposed_same})
    write(OUT / "executor_parity.json", {"schema": "gac-pilot-executor-parity-v1", "provider_calls": 0,
        "upstream_commit": PIN, "upstream_file_hashes": hashes, "probe_sha256": digest(__file__),
        "image": IMAGE, "rows": rows, "all_match": all(r["same_success_and_output"] for r in rows),
        "prospective_worker_sha256": digest(native_worker), "prospective_all_match": all(r["prospective_matches"] for r in rows),
        "scope": "Hand-authored execution-contract fixtures; both executors isolated. Does not establish native browser semantics or relabel any pilot prediction."})
    print(json.dumps({"fixtures": len(rows), "pilot_matching": sum(r["same_success_and_output"] for r in rows),
                     "prospective_matching": sum(r["prospective_matches"] for r in rows), "provider_calls": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    asyncio.run(probe(parser.parse_args().checkout.resolve()))
