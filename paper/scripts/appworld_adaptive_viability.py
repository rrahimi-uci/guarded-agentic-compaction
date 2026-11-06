"""Bounded AppWorld development screen and matched manual-prefix pilot.

All selected scenarios are previously exposed development material. Neither
reference solutions nor evaluator answers enter the agent context. Protected raw
data stays local and must be encrypted before redistribution.
"""
import argparse
import asyncio
from contextlib import asynccontextmanager
import fcntl
import hashlib
import json
from pathlib import Path
import time
import uuid

from adaptive_campaign_budget import BudgetClient, BudgetExceeded, Ledger, MODEL, INPUT_UPPER, OUTPUT_RATE, MAX_OUTPUT
from adaptive_pilot import ROOT, LOCAL as CAMPAIGN, digest, write
from appworld_reference_study import IMAGE as BASE_IMAGE, UPSTREAM, INSTRUCTIONS, TOOL, select_development
from guarded_agentic_compaction.schema.effects import EffectCatalog

BASE = ROOT / "benchmarks/.cache/appworld_adaptive_viability"
CACHE = BASE / "v2"
IMAGE = "sha256:d9e0e53e548439321832c2f3a2b424e2f6ce77436bfae4e5ec22e1f2da8a4718"
OUT = ROOT / "paper/results/appworld_adaptive_viability"
WORKER = ROOT / "experiments/appworld_adaptive_viability/worker.py"
READS = ("supervisor.show_profile", "supervisor.show_account_passwords",
         "api_docs.show_app_descriptions", "api_docs.show_api_descriptions", "api_docs.show_api_doc", "api_docs.search_api_docs")
PREFIX = [{"app": "supervisor", "api": name, "arguments": {}}
          for name in ("show_profile", "show_account_passwords")]
NAMESPACE = "appworld-viability-v2:"
LIMIT = 8.0  # bounded local pilot allocation inside the existing $30 discovery stage


def catalog():
    return EffectCatalog.from_dict({"version": 1, "name": "appworld-0.2.0-development-reads", "tools": {
        **{name: {"effect": "READ_LOCAL", "capabilities": ["speculatable", "replayable"],
                  "resource": "pinned-isolated-appworld", "notes": "Audited pinned public documentation/supervisor read; SQL effects monitored. No credential-minting API included."} for name in READS},
        "supervisor.complete_task": {"effect": "WRITE_IRREVERSIBLE", "capabilities": []},
    }})


def bounded_messages(messages):
    recent = [i for i, m in enumerate(messages) if m["role"] == "tool"][-4:]
    result = []
    for i, message in enumerate(messages):
        value = dict(message)
        if message["role"] == "tool":
            if i not in recent:
                value["content"] = "[Earlier API result omitted; call a read API again if needed.]"
            elif len(value["content"]) > 16000:
                value["content"] = value["content"][:16000] + "\n[Result truncated; use documented pagination or filtering.]"
        result.append(value)
    return result


@asynccontextmanager
async def worker(request, path):
    name = "gac-app-viability-" + uuid.uuid4().hex
    command = ["docker", "run", "--rm", "-i", "--name", name, "--label", "gac.study=appworld-viability",
        "--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--pids-limit", "128", "--memory", "4g", "--cpus", "2", "--user", "65534:65534",
        "--tmpfs", "/tmp:rw,nosuid,size=512m", "--tmpfs", "/work:rw,nosuid,size=2g,mode=1777",
        "-v", f"{WORKER}:/worker.py:ro", IMAGE, "-I", "/worker.py"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(".stderr").open("wb") as stderr:
        proc = await asyncio.create_subprocess_exec(*command, stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=stderr, limit=2_000_000)
        async def send(value):
            proc.stdin.write((json.dumps(value) + "\n").encode())
            await proc.stdin.drain()
        async def receive():
            line = await asyncio.wait_for(proc.stdout.readline(), 90)
            if not line:
                raise RuntimeError("worker ended without terminal result")
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


def freeze():
    path = CACHE / "seal.json"
    if path.exists():
        raise ValueError("sealed attempt exists; never overwrite or reset attempts")
    inventory = ROOT / "benchmarks/.cache/appworld_reference_study/inventory.json"
    tasks = select_development(json.loads(inventory.read_text())["splits"])
    sources = [Path(__file__).resolve(), WORKER, WORKER.with_name("Dockerfile"), ROOT / "paper/scripts/adaptive_campaign_budget.py",
               ROOT / "paper/scripts/appworld_reference_study.py"]
    seal = {"schema": "appworld-adaptive-viability-v2", "image": IMAGE, "upstream": UPSTREAM,
        "base_image": BASE_IMAGE, "dependency_pins": {"sqlalchemy": "2.0.44", "sqlmodel": "0.0.44"},
        "amendment": "Before any paid calls: v1 reference control fails with SQLite missing-table exceptions on one of 12 tasks. The same unmodified task/reference/grader passes in the compatible dependency image. Rerun all 36 controls; task list, seed, model, limits, arms and grading requirements unchanged. Old results retained.",
        "prior_seal_sha256": digest(BASE / "seal.json"),
        "inventory_sha256": digest(inventory), "tasks": tasks, "scenarios": [t.rsplit("_", 1)[0] for t in tasks],
        "source_hashes": {str(p.relative_to(ROOT)): digest(p) for p in sources},
        "source_selection": "Unchanged prior hash ordering: 12 distinct official training scenarios; no task outcome selection.",
        "discovery_groups": tasks[:8], "challenge_groups": tasks[8:], "calibration_groups": [], "test_groups": [],
        "model": MODEL, "instructions": INSTRUCTIONS, "tool": TOOL, "max_requests": 24,
        "max_api_calls": 48, "max_payload_bytes": 100000, "timeout_seconds": 600,
        "pilot_cap_usd": LIMIT, "stage": "discovery", "campaign_cap_usd": 300,
        "context_policy": "All task/action history; last four tool results, each capped at 16000 characters. Full raw results retained.",
        "arms": ["baseline", "manual_prefix"], "prefix": PREFIX,
        "arm_order": {t: (["baseline", "manual_prefix"] if i % 2 == 0 else ["manual_prefix", "baseline"])
                      for i, t in enumerate(tasks)},
        "oracle_controls": ["reference", "empty", "false_completion"],
        "reference_controls_rule": "All 12 selected cases must have a successful nonempty reference test suite and failing negative controls before any paid execution.",
        "effect_catalog": catalog().model_dump(mode="json"),
        "candidate_gate": {"minimum_train_support": 3, "minimum_saved_requests": 2,
            "prefix_lengths": [2, 3, 4], "required_distinct_nontrivial_families": 2,
            "trivial": "Documentation-only or supervisor profile/password-only programs cannot establish distinctive compiler value.",
            "admission": "No calibration groups: no GAC artifact may be emitted. Research candidate execution is not admitted GAC."},
        "failure_rule": "Retain every scheduled arm. Task failures count as unsuccessful. Stop paid execution on provider/budget or read-effect violations; do not replace tasks.",
        "interpretation": "Development-only matched baseline/manual comparison and compiler viability screen, not confirmation, certification or a competing-compiler ranking.",
        "exposure": "Historical train/dev references and test trajectories already inspected. All selected scenarios and variants remain development-only.",
        "redistribution": "Protected raw inputs, API results, traces and reference outputs must be encrypted with upstream pack_bundle; public output is aggregates, counts and hashes only."}
    write(path, seal)
    for source in sources:
        copy = CACHE / "sealed_sources" / source.relative_to(ROOT)
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_bytes(source.read_bytes())
    print(json.dumps({"scenarios": len(tasks), "scheduled_agent_arms": 2 * len(tasks), "pilot_cap_usd": LIMIT}))


def verify_records():
    """Verify historical bytes, including versions superseded by a recorded fix."""
    seal = json.loads((CACHE / "seal.json").read_text())
    for rel, expected in seal["source_hashes"].items():
        if digest(CACHE / "sealed_sources" / rel) != expected:
            raise ValueError("historical sealed source drift: " + rel)
    inventory = ROOT / "benchmarks/.cache/appworld_reference_study/inventory.json"
    if digest(inventory) != seal["inventory_sha256"]:
        raise ValueError("inventory drift")
    return seal


def verify():
    seal = verify_records()
    for rel, expected in seal["source_hashes"].items():
        if digest(ROOT / rel) != expected:
            raise ValueError("sealed source drift: " + rel)
    return seal


async def controls(seal):
    for index, task in enumerate(seal["tasks"]):
        for mode in seal["oracle_controls"]:
            path = CACHE / "controls" / task / (mode + ".json")
            if path.exists():
                continue
            row = {"status": "started", "task_id": task, "mode": mode, "messages": []}
            write(path, row)
            start = time.monotonic()
            try:
                async with worker({"mode": mode, "task_id": task}, path) as (_, receive):
                    while True:
                        value = await receive()
                        row["messages"].append(value)
                        if value["type"] == "evaluation":
                            row["evaluation"] = value
                            row["passed"] = value["tests"] > 0 and value["success"] == (mode == "reference")
                            break
                row["status"] = "completed"
            except Exception as exc:
                row.update(status="failed", passed=False, error=type(exc).__name__, detail=str(exc))
            row["seconds"] = time.monotonic() - start
            write(path, row)
            print(json.dumps({"index": index, "mode": mode, "passed": row["passed"]}), flush=True)


def study_reservation(payload):
    """Bound this pilot before the shared ledger's authoritative reservation."""
    from adaptive_campaign_budget import clean
    payload = clean(payload)
    payload.update(model=MODEL, max_completion_tokens=MAX_OUTPUT, reasoning_effort="none", store=False, service_tier="default")
    size = len(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode())
    if size > 100000:
        raise BudgetExceeded("pilot context byte cap")
    ledger = json.loads((CAMPAIGN / "ledger.json").read_text())
    used = sum(r.get("accounted_upper_usd", r["reserved_usd"]) for r in ledger["requests"] if r["task"].startswith(NAMESPACE))
    maximum = ((size + 8192) * INPUT_UPPER + MAX_OUTPUT * OUTPUT_RATE) / 1e6
    if used + maximum > LIMIT:
        raise BudgetExceeded("pilot allocation cap")


async def episode(task, arm, seal, path, row):
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    client = BudgetClient(Ledger(CAMPAIGN / "ledger.json"), stage="discovery", task=NAMESPACE + task, arm=arm)
    try:
        async with worker({"mode": "agent", "task_id": task}, path) as (send, receive):
            context = await receive()
            if context.get("type") != "context":
                raise ValueError("missing public context")
            row["context"] = context
            messages = [{"role": "system", "content": seal["instructions"]},
                        {"role": "user", "content": json.dumps(context)}]
            row.update(calls=[], provider_trace=[], messages=messages)
            async def call(args, call_id, origin):
                if set(args) != {"app", "api", "arguments"}:
                    raise ValueError("malformed tool command")
                if len(row["calls"]) >= seal["max_api_calls"]:
                    raise ValueError("tool-call cap")
                await send({"type": "call", **args})
                result = await receive()
                if result.get("type") != "result":
                    raise ValueError("missing result")
                name = args["app"] + "." + args["api"]
                row["calls"].append({"tool": name, "arguments": args["arguments"], "result": result["result"],
                    "observed_sql_operations": result["observed_sql_operations"], "origin": origin, "call_id": call_id})
                if name in READS and result["observed_sql_operations"]:
                    raise RuntimeError("READ_EFFECT_VIOLATION")
                messages.append({"role": "tool", "tool_call_id": call_id, "content": json.dumps(result["result"], default=str)})
                write(path, row)
            if arm == "manual_prefix":
                for i, args in enumerate(seal["prefix"]):
                    cid = "manual_prefix_" + str(i)
                    messages.append({"role": "assistant", "content": None, "tool_calls": [{"id": cid,
                        "type": "function", "function": {"name": "call_api", "arguments": json.dumps(args)}}]})
                    await call(args, cid, "manual_prefix")
            for _ in range(seal["max_requests"]):
                payload = {"messages": bounded_messages(messages), "tools": [seal["tool"]], "parallel_tool_calls": False}
                study_reservation(payload)
                response = await client.create(**payload)
                row["provider_trace"].append(response.model_dump())
                message = response.choices[0].message
                messages.append(message.model_dump(exclude_none=True))
                write(path, row)
                if not message.tool_calls:
                    row["termination"] = "model_final"
                    break
                for request in message.tool_calls:
                    if request.function.name != "call_api":
                        raise ValueError("unknown tool")
                    await call(json.loads(request.function.arguments), request.id, "model")
            else:
                row["termination"] = "request_cap"
            await send({"type": "finish"})
            value = await receive()
            if value.get("type") != "evaluation" or value["tests"] <= 0:
                raise ValueError("invalid official evaluation")
            row.update(status="completed", evaluation=value)
    finally:
        await client.close()


async def run(seal):
    if (CACHE / "execution_stop.json").exists():
        raise ValueError("stopped attempt cannot resume; preserve records and design a new protocol")
    for task in seal["tasks"]:
        for mode in seal["oracle_controls"]:
            row = json.loads((CACHE / "controls" / task / (mode + ".json")).read_text())
            if not row.get("passed"):
                raise ValueError("entire frozen cohort must pass controls before paid execution")
    for index, task in enumerate(seal["tasks"]):
        for arm in seal["arm_order"][task]:
            path = CACHE / "episodes" / task / (arm + ".json")
            if path.exists():
                continue
            row = {"status": "started", "task_id": task, "arm": arm}
            write(path, row)
            start = time.monotonic()
            try:
                await asyncio.wait_for(episode(task, arm, seal, path, row), seal["timeout_seconds"])
            except BaseException as exc:
                row.update(status="failed", error=type(exc).__name__, detail=str(exc))
                raise  # stop on operational errors; never erase or repeat paid attempts
            finally:
                row["seconds"] = time.monotonic() - start
                write(path, row)
            print(json.dumps({"index": index, "arm": arm, "success": row["evaluation"]["success"],
                              "requests": len(row["provider_trace"]), "api_calls": len(row["calls"])}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("freeze", "controls", "run"))
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    with (CACHE / "runner.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.command == "freeze":
            freeze()
        elif args.command == "controls":
            asyncio.run(controls(verify()))
        else:
            asyncio.run(run(verify()))
