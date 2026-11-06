"""Bounded host bridge to the pinned upstream executor; no provider bypass."""
import asyncio
from contextlib import contextmanager
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

from adaptive_campaign_budget import BudgetExceeded
from adaptive_pilot import ROOT, digest
from adaptive_pilot_runtime import IMAGE, dumps
from probe_agent_jit_sql import PIN

FILES = ("local_python_executor.py", "codecheck.py", "cfg_builder.py")


@contextmanager
def upstream_runtime(checkout):
    """Mount only audited stdlib executor files, never checkout credentials."""
    if subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip() != PIN:
        raise ValueError("upstream commit mismatch")
    if subprocess.check_output(["git", "-C", str(checkout), "diff", "--name-only", "HEAD"], text=True).strip():
        raise ValueError("modified upstream checkout")
    expected = json.loads((ROOT / "paper/results/adaptive_compiler_pilot/executor_parity.json").read_text())["upstream_file_hashes"]
    with tempfile.TemporaryDirectory(prefix="gac-upstream-runtime-") as temporary:
        package = Path(temporary) / "upstream"
        package.mkdir(mode=0o755)
        (package / "__init__.py").write_text("")
        for name in FILES:
            source = checkout / "blastai/agents" / name
            if digest(source) != expected[name]:
                raise ValueError("upstream runtime bytes mismatch")
            shutil.copyfile(source, package / name)
        yield package


async def run_native(code, dispatch, package, *, timeout=180, reference=False):
    worker = ROOT / ("experiments/adaptive_prefix_validation/reference_worker.py" if reference else
                     "experiments/adaptive_compiler_pilot/container_worker_native.py")
    name = "gac-native-" + uuid.uuid4().hex
    command = ["docker", "run", "--rm", "-i", "--name", name, "--network", "none", "--read-only",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", "64",
        "--memory", "256m", "--cpus", "1", "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
        "--user", "65534:65534", "-v", f"{package}:/upstream:ro", "-v", f"{worker}:/worker.py:ro",
        IMAGE, "python", "-I", "/worker.py"]
    proc = await asyncio.create_subprocess_exec(*command, stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, limit=262144)
    async def exchange():
        proc.stdin.write((dumps({"code": code}) + "\n").encode())
        await proc.stdin.drain()
        size = 0
        for _ in range(65):
            line = await proc.stdout.readline()
            size += len(line)
            if not line or size > 2_000_000:
                raise RuntimeError("worker protocol/output cap")
            message = json.loads(line)
            if message.get("type") == "result":
                return {"status": "ok", "output": message["result"]}
            if message.get("type") == "failure":
                return {"status": "error", "error": message.get("error", "unknown")}
            if message.get("type") != "call" or not isinstance(message.get("arguments"), dict):
                raise RuntimeError("invalid worker RPC")
            try:
                reply = {"result": await dispatch(message["tool"], message["arguments"])}
            except BudgetExceeded:
                raise  # Never let generated code continue after a campaign stop.
            except Exception as exc:
                reply = {"error": type(exc).__name__}
            proc.stdin.write((dumps(reply) + "\n").encode())
            await proc.stdin.drain()
        raise RuntimeError("worker RPC cap")
    try:
        return await asyncio.wait_for(exchange(), timeout)
    finally:
        remover = await asyncio.create_subprocess_exec("docker", "rm", "-f", name,
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
        try:
            await asyncio.wait_for(remover.wait(), 15)
        finally:
            if remover.returncode is None:
                remover.kill()
            await remover.wait()
            if proc.returncode is None:
                proc.kill()
            await proc.wait()
