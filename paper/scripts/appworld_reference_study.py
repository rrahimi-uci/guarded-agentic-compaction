"""Isolated AppWorld development runner with official final-state grading.

No test-split access, no production actions, no new calibration claim. Protected
task material stays in the ignored cache until encrypted for redistribution.
"""
import argparse
import asyncio
from contextlib import asynccontextmanager
import fcntl
import hashlib
import json
from pathlib import Path
import subprocess
import time
import uuid

from adaptive_campaign_budget import BudgetClient, BudgetExceeded, Ledger, MODEL
from adaptive_pilot import ROOT, LOCAL as CAMPAIGN, digest, write

OUT = ROOT / "paper/results/appworld_reference_study"
CACHE = ROOT / "benchmarks/.cache/appworld_reference_study"
IMAGE = "sha256:bb24405c0bd685433d8d3110a9f99f019af14696a2437e15d718b28dabdb68c7"
UPSTREAM = "42b5bcf3cd334fee33f0c37c02070a9f5807add5"
WORKER = ROOT / "experiments/appworld_reference_study/worker.py"
SEED = "gac-appworld-development-20261106-v1"
INSTRUCTIONS = """Solve the user's task in the simulated AppWorld environment.
Use the public APIs and their documentation. API calls execute in the simulator;
do not claim an action succeeded unless its result supports that claim. You can
look up API documentation using the supplied documentation APIs. Read the relevant
API documentation before calling an unfamiliar API. Authentication information,
when required, is available through the supervisor APIs. Do not invent credentials
or object identifiers. Use supervisor.complete_task when the task is finished.
Return a short final response after completing the task. All API actions are in
an isolated simulation, and task success is judged by independent executable tests."""
TOOL = {"type": "function", "function": {"name": "call_api",
    "description": "Call a documented public AppWorld API. Use documentation APIs to discover API signatures.",
    "parameters": {"type": "object", "properties": {"app": {"type": "string"}, "api": {"type": "string"},
        "arguments": {"type": "object"}}, "required": ["app", "api", "arguments"], "additionalProperties": False}}}


def select_development(splits, count=12):
    # One variation per scenario: repeated variants never inflate group counts.
    groups = {}
    for task in splits["train"]:
        groups.setdefault(task.rsplit("_", 1)[0], []).append(task)
    ranked = sorted(groups, key=lambda g: hashlib.sha256(f"{SEED}:{g}".encode()).hexdigest())
    if len(ranked) < count:
        raise ValueError("insufficient development scenarios; do not silently shrink")
    return [sorted(groups[g], key=lambda t: hashlib.sha256(f"{SEED}:{t}".encode()).hexdigest())[0]
            for g in ranked[:count]]


@asynccontextmanager
async def worker(request):
    name = "gac-appworld-" + uuid.uuid4().hex
    command = ["docker", "run", "--rm", "-i", "--name", name, "--network", "none", "--read-only",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", "128", "--memory", "4g",
        "--cpus", "2", "--user", "65534:65534", "--tmpfs", "/tmp:rw,nosuid,size=512m",
        "--tmpfs", "/work:rw,nosuid,size=2g,mode=1777", "-v", f"{WORKER}:/worker.py:ro", IMAGE, "-I", "/worker.py"]
    proc = await asyncio.create_subprocess_exec(*command, stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, limit=2_000_000)
    async def send(value):
        proc.stdin.write((json.dumps(value) + "\n").encode())
        await proc.stdin.drain()
    async def receive():
        line = await asyncio.wait_for(proc.stdout.readline(), 180)
        if not line:
            raise RuntimeError("worker ended before terminal result")
        value = json.loads(line)
        if value.get("type") == "failure":
            raise RuntimeError(json.dumps(value))
        return value
    try:
        await send(request)
        yield send, receive
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


async def inventory():
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "inventory.json"
    if path.exists():
        raise RuntimeError("inventory already retained; do not overwrite")
    async with worker({"mode": "inventory"}) as (_, receive):
        result = await receive()
    if result.get("type") != "inventory":
        raise ValueError("invalid inventory")
    write(path, result)
    print(json.dumps({s: {"tasks": len(ids), "scenarios": len({t.rsplit('_', 1)[0] for t in ids})}
                      for s, ids in result["splits"].items()}))


def freeze():
    path = CACHE / "seal.json"
    if path.exists():
        raise RuntimeError("seal already exists; retain old attempts and version amendments")
    inv = json.loads((CACHE / "inventory.json").read_text())
    selected = select_development(inv["splits"])
    sources = [Path(__file__).resolve(), WORKER, WORKER.with_name("Dockerfile"),
        ROOT / "paper/scripts/adaptive_campaign_budget.py"]
    seal = {"schema": "gac-appworld-development-seal-v1", "purpose": "development and grader validation only",
        "image": IMAGE, "upstream_commit": UPSTREAM, "inventory_sha256": digest(CACHE / "inventory.json"),
        "source_hashes": {str(p.relative_to(ROOT)): digest(p) for p in sources}, "model": MODEL,
        "tasks": selected, "max_model_requests": 32, "max_api_calls": 64, "episode_timeout_seconds": 600,
        "reference_control_api_cap": 1000,
        "instructions": INSTRUCTIONS, "tool": TOOL,
        "prior_exposure": "Historical AppWorld train/dev solutions and test trajectories were analyzed; no task is claimed to be a fresh confirmatory holdout.",
        "failure_rule": "All scheduled tasks retained. Failure, interruption or no terminal evaluation counts as unsuccessful.",
        "oracle_rule": "Report exact official test outcome and nonzero test count; reference and negative controls separate from agent evidence.",
        "budget_stage": "discovery", "campaign_cap_usd": 300, "stage_cap_usd": 30,
        "analysis": "Descriptive only. No candidate admission, learned-gate, noninferiority or superiority claim.",
        "followup_exclusion": "Every selected scenario and its variants remain development-only."}
    write(path, seal)
    print(json.dumps({"scheduled_development_scenarios": len(selected), "seal_sha256": digest(path)}))


def verify():
    seal = json.loads((CACHE / "seal.json").read_text())
    for p, sha in seal["source_hashes"].items():
        if digest(ROOT / p) != sha:
            raise RuntimeError("sealed source drift: " + p)
    if digest(CACHE / "inventory.json") != seal["inventory_sha256"]:
        raise RuntimeError("source inventory drift")
    return seal


async def control(task, mode, state=None):
    messages = []
    if state is not None:
        state["messages"] = messages
    async with worker({"mode": mode, "task_id": task}) as (_, receive):
        while True:
            item = await receive()
            messages.append(item)
            if item["type"] == "evaluation":
                return {"status": "completed", "evaluation": item, "messages": messages}


async def agent(task, seal, state, path):
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    client = BudgetClient(Ledger(CAMPAIGN / "ledger.json"), stage="discovery",
        task="appworld-development-v1:" + task, arm="baseline")
    try:
        return await _agent(task, seal, state, path, client)
    finally:
        await client.client.close()


async def _agent(task, seal, state, path, client):
    trace, calls = [], []
    state.update(provider_trace=trace, calls=calls)
    async with worker({"mode": "agent", "task_id": task}) as (send, receive):
        context = await receive()
        if context.get("type") != "context":
            raise ValueError("expected task context")
        state["context"] = context
        messages = [{"role": "system", "content": seal["instructions"]},
                    {"role": "user", "content": json.dumps(context, default=str)}]
        for _ in range(seal["max_model_requests"]):
            response = await client.create(messages=messages, tools=[seal["tool"]], parallel_tool_calls=False)
            trace.append(response.model_dump())
            write(path, {**state, "status": "running", "task_id": task, "mode": "agent"})
            message = response.choices[0].message
            messages.append(message.model_dump(exclude_none=True))
            if not message.tool_calls:
                break
            for call in message.tool_calls:
                if call.function.name != "call_api":
                    raise ValueError("unexpected tool")
                args = json.loads(call.function.arguments)
                if set(args) != {"app", "api", "arguments"}:
                    raise ValueError("invalid API command")
                if len(calls) >= seal["max_api_calls"]:
                    raise RuntimeError("API cap")
                await send({"type": "call", **args})
                result = await receive()
                if result.get("type") != "result":
                    raise ValueError("expected API result")
                calls.append({**args, "result": result["result"]})
                write(path, {**state, "status": "running", "task_id": task, "mode": "agent"})
                messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result["result"], default=str)})
        await send({"type": "finish"})
        evaluation = await receive()
        if evaluation.get("type") != "evaluation":
            raise ValueError("expected terminal evaluation")
    return {**state, "status": "completed", "evaluation": evaluation}


async def run(mode, limit):
    seal = verify()
    if mode == "agent":
        for task in seal["tasks"]:
            for kind in ("reference", "empty", "false_completion"):
                path = CACHE / kind / (task + ".json")
                row = json.loads(path.read_text())
                expected = kind == "reference"
                if row.get("status") != "completed" or row["evaluation"]["success"] != expected:
                    raise RuntimeError("grader controls have not passed for the entire fixed cohort")
    attempted = 0
    for index, task in enumerate(seal["tasks"]):
        path = CACHE / mode / (task + ".json")
        if path.exists():
            continue
        if limit is not None and attempted >= limit:
            break
        attempted += 1
        write(path, {"status": "started", "task_id": task, "mode": mode, "started": time.time()})
        started = time.monotonic()
        state = {}
        try:
            result = await asyncio.wait_for(agent(task, seal, state, path) if mode == "agent" else control(task, mode, state),
                                            seal["episode_timeout_seconds"])
        except Exception as exc:
            result = {**state, "status": "failed", "error": type(exc).__name__, "detail": str(exc)[:700]}
            write(path, {**result, "task_id": task, "mode": mode, "seconds": time.monotonic() - started})
            # Keep failures; do not replace a task or keep spending after an operational error.
            raise
        write(path, {**result, "task_id": task, "mode": mode, "seconds": time.monotonic() - started})
        print(json.dumps({"index": index, "mode": mode, "status": result["status"],
                          "success": result["evaluation"]["success"], "tests": result["evaluation"]["tests"]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inventory", "freeze", "reference", "empty", "false_completion", "agent"))
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    CACHE.mkdir(parents=True, exist_ok=True)
    with (CACHE / "runner.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.command == "inventory":
            asyncio.run(inventory())
        elif args.command == "freeze":
            freeze()
        else:
            asyncio.run(run(args.command, args.limit))
