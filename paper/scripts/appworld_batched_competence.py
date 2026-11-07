"""Sealed AppWorld baseline-competence development study under common entry.

This is an adapted interface, not native AppWorld. All 12 scenarios are exposed
training data. References are used only for provider-free grader controls; they
never enter agent prompts or GAC discovery. Protected raw records are encrypted
before publication. No compiler artifact or confirmatory claim is made here.
"""
import argparse
import asyncio
from contextlib import asynccontextmanager
import hashlib
import json
from pathlib import Path
import subprocess
import time
import uuid

from adaptive_campaign_budget import BudgetClient, BudgetExceeded, Ledger, MODEL, INPUT_UPPER, OUTPUT_RATE, MAX_OUTPUT
from adaptive_pilot import ROOT, LOCAL as CAMPAIGN, digest, write
from appworld_adaptive_viability import IMAGE
from appworld_reference_study import select_development
from export_appworld_viability import PACK

CACHE = ROOT / "benchmarks/.cache/appworld_batched_competence/v1"
OUT = ROOT / "paper/results/appworld_batched_competence"
WORKER = ROOT / "experiments/appworld_batched_competence/worker.py"
REFERENCES = ROOT / "benchmarks/.cache/appworld_entry_preflight/v2/references"
INVENTORY = ROOT / "benchmarks/.cache/appworld_reference_study/inventory.json"
PRIOR = ROOT / "paper/results/appworld_entry_preflight"
LEDGER = CAMPAIGN / "ledger.json"
NAMESPACE = "appworld-batched-competence-v1:"
LOCAL_CAP_USD = 15.0
SETUP_APIS = {"supervisor.show_profile", "supervisor.show_account_passwords"}

SYSTEM = """Solve the user's task in the isolated AppWorld simulation with public APIs.
All nine apps were authenticated through the same measured 11-call setup. Do not
call login, profile or password APIs. When an endpoint requires access_token,
pass the literal string AUTO; the worker binds the token from that setup. The
tokens and passwords are not available to you. Use api_docs APIs to inspect
signatures before unfamiliar calls. Make a call_api_batch of 1 to 8 fully
specified ordered calls; each intermediate result is returned and a batch stops
on the first API error. Batch only when later arguments are already known from
the task or a prior observation. Never invent IDs or infer future results.
Complete the task with supervisor.complete_task when appropriate, then call
finish. The official saved-state tests determine success. No reference solution,
ground truth, private API, arbitrary code or external service is available."""
CALL = {"type": "object", "properties": {
    "app": {"type": "string"}, "api": {"type": "string"},
    "arguments": {"type": "object"}},
    "required": ["app", "api", "arguments"], "additionalProperties": False}
TOOLS = [{"type": "function", "function": {"name": "call_api_batch",
    "description": "Execute 1 to 8 known public API calls in order. Returns each result; stops on first API error. Use access_token AUTO where required.",
    "parameters": {"type": "object", "properties": {"calls": {
        "type": "array", "minItems": 1, "maxItems": 8, "items": CALL}},
        "required": ["calls"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "finish",
    "description": "End the task after making needed API calls; official saved-state grading follows.",
    "parameters": {"type": "object", "properties": {}, "additionalProperties": False}}}]


def public_reference_calls(record):
    commands = []
    for call in record["calls"]:
        name = call["tool"]
        if name.endswith(".login") or name in SETUP_APIS:
            continue
        app, api = name.split(".", 1)
        arguments = dict(call["arguments"])
        if "access_token" in arguments:
            arguments["access_token"] = "AUTO"
        commands.append({"app": app, "api": api, "arguments": arguments})
    return commands


def model_view(result):
    value = json.loads(json.dumps(result, default=str))
    limit = min(16000, 32000 // max(1, len(value.get("calls", []))))
    for row in value.get("calls", []):
        blob = json.dumps(row.get("result"), default=str)
        if len(blob) > limit:
            row["result"] = {"truncated_result_prefix": blob[:limit],
                             "model_view_truncated": True}
    return value


def bounded_messages(messages):
    tool_indices = [i for i, row in enumerate(messages) if row["role"] == "tool"]
    keep = set(tool_indices[-2:])
    return [dict(row, content="[Earlier API results omitted; re-read if needed.]")
            if i in set(tool_indices) - keep else row for i, row in enumerate(messages)]


@asynccontextmanager
async def worker(request, path):
    name = "gac-app-batched-" + uuid.uuid4().hex
    command = ["docker", "run", "--rm", "-i", "--name", name,
        "--label", "gac.study=appworld-batched-competence",
        "--network", "none", "--read-only", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges", "--pids-limit", "128",
        "--memory", "4g", "--cpus", "2", "--user", "65534:65534",
        "--tmpfs", "/tmp:rw,nosuid,size=512m",
        "--tmpfs", "/work:rw,nosuid,size=2g,mode=1777",
        "-v", f"{WORKER}:/worker.py:ro", IMAGE, "-I", "/worker.py"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(".stderr").open("wb") as stderr:
        process = await asyncio.create_subprocess_exec(*command,
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=stderr, limit=4_000_000)
        async def send(value):
            process.stdin.write((json.dumps(value, default=str) + "\n").encode())
            await process.stdin.drain()
        async def receive():
            line = await asyncio.wait_for(process.stdout.readline(), 120)
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
                await asyncio.wait_for(remover.wait(), 20)
            finally:
                if remover.returncode is None:
                    remover.kill()
                await remover.wait()
                if process.returncode is None:
                    process.kill()
                await process.wait()


def freeze():
    if CACHE.exists():
        raise ValueError("sealed version exists; retain all attempts")
    inventory = json.loads(INVENTORY.read_text())
    tasks = select_development(inventory["splits"])
    previous = json.loads((PRIOR / "report.json").read_text())
    prior_seal = json.loads((PRIOR / "reference_seal.json").read_text())
    if (len(tasks) != 12 or tasks != prior_seal["tasks"]
            or previous["control_totals"]["reference"]["passed"] != 12
            or previous["control_totals"]["empty"]["passed"] != 12
            or previous["control_totals"]["false_completion"]["passed"] != 12):
        raise ValueError("prior fixed development control gate missing")
    refs = {task: REFERENCES / (task + ".json") for task in tasks}
    if not all(json.loads(p.read_text()).get("reference_success") is True for p in refs.values()):
        raise ValueError("fixed reference inventory incomplete")
    image = json.loads(subprocess.check_output(["docker", "image", "inspect", IMAGE]))[0]
    sources = [Path(__file__), WORKER, ROOT / "paper/scripts/adaptive_campaign_budget.py",
               ROOT / "paper/scripts/adaptive_pilot.py",
               ROOT / "paper/scripts/appworld_reference_study.py",
               ROOT / "paper/scripts/appworld_adaptive_viability.py",
               ROOT / "paper/scripts/export_appworld_viability.py"]
    seal = {"schema": "gac-appworld-batched-competence-v1",
        "status": "exposed development; adapted preauthenticated entry; no native leaderboard claim",
        "image": IMAGE, "image_id": image["Id"],
        "upstream_inventory_sha256": digest(INVENTORY),
        "prior_report_sha256": digest(PRIOR / "report.json"),
        "reference_hashes": {task: digest(p) for task, p in refs.items()},
        "source_hashes": {str(p.relative_to(ROOT)): digest(p) for p in sources},
        "tasks": tasks, "grouping": "one variation per fixed exposed training scenario",
        "modes": ["reference", "empty", "false_completion"],
        "model": MODEL, "system": SYSTEM, "tools": TOOLS,
        "max_model_requests": 96, "max_api_calls": 192,
        "max_batch_calls": 8, "episode_seconds": 1200,
        "model_view": "Every raw result retained; model-facing result JSON capped at min(16000, 32000/batch_size) characters and only last two tool views retained.",
        "competence_gate": "At least 8/12 official task successes, with all failures and unstarted attempts counted in the denominator, before compiler-value comparison. This is a development engineering gate, not statistical noninferiority.",
        "ledger_before_sha256": digest(LEDGER),
        "local_cap_usd": LOCAL_CAP_USD, "stage": "discovery",
        "stage_cap_usd": 30, "campaign_cap_usd": 300,
        "setup": "Two actual supervisor reads and login to all nine public apps before every mode; 11 calls counted. Agent receives app list and AUTO token binding, never credentials.",
        "failure_rule": "All 12 scenarios remain scheduled; failures and unstarted outcomes remain in denominator. No retry or task replacement.",
        "claim_scope": "Baseline competence gate only; no GAC artifact, calibration, test or compiler comparison."}
    CACHE.mkdir(parents=True)
    write(CACHE / "seal.json", seal)
    for path in sources:
        dest = CACHE / "sealed_sources" / path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(path.read_bytes())
    print(json.dumps({"tasks": len(tasks), "controls": 36, "model": MODEL,
                      "local_cap_usd": LOCAL_CAP_USD}))


def verify():
    seal = json.loads((CACHE / "seal.json").read_text())
    if (digest(INVENTORY) != seal["upstream_inventory_sha256"]
            or digest(PRIOR / "report.json") != seal["prior_report_sha256"]
            or any(digest(REFERENCES / (task + ".json")) != h
                   for task, h in seal["reference_hashes"].items())
            or any(digest(ROOT / p) != h for p, h in seal["source_hashes"].items())):
        raise ValueError("sealed input or source drift")
    return seal


async def one_control(task, mode, seal):
    path = CACHE / "controls" / task / (mode + ".json")
    if path.exists():
        return
    row = {"task_id": task, "mode": mode, "status": "started", "passed": False}
    write(path, row)
    if mode == "reference":
        ref = json.loads((REFERENCES / (task + ".json")).read_text())
        request = {"task_id": task, "mode": mode, "commands": public_reference_calls(ref)}
    else:
        request = {"task_id": task, "mode": mode}
    started = time.monotonic()
    try:
        async with worker(request, path) as (_, receive):
            value = await receive()
            if value.get("type") != "evaluation":
                raise ValueError("missing official evaluation")
            row["evaluation"] = value
            row["passed"] = (value["tests"] > 0 and value["setup_calls"] == 11
                             and value["success"] is (mode == "reference"))
            row["status"] = "completed"
    except Exception as exc:
        row.update(status="failed", passed=False, error=type(exc).__name__, detail=str(exc)[:500])
    finally:
        row["seconds"] = time.monotonic() - started
        write(path, row)
    print(json.dumps({"task": task, "mode": mode, "passed": row["passed"]}), flush=True)


async def controls():
    seal = verify()
    for task in seal["tasks"]:
        for mode in seal["modes"]:
            await one_control(task, mode, seal)


def check_controls(seal):
    for task in seal["tasks"]:
        records = [json.loads((CACHE / "controls" / task / (m + ".json")).read_text())
                   for m in seal["modes"]]
        if not all(r.get("passed") for r in records):
            raise ValueError("exact-path reference/negative control failure")
        hashes = {r["evaluation"]["entry_state_sha256"] for r in records}
        if len(hashes) != 1:
            raise ValueError("common entry differs across controls")


def study_reservation(payload):
    from adaptive_campaign_budget import clean
    value = clean(payload)
    value.update(model=MODEL, max_completion_tokens=MAX_OUTPUT,
                 reasoning_effort="none", store=False, service_tier="default")
    size = len(json.dumps(value, ensure_ascii=False, sort_keys=True).encode())
    if size > 120_000:
        raise BudgetExceeded("competence pilot prompt byte cap")
    ledger = json.loads(LEDGER.read_text())
    used = sum(r.get("accounted_upper_usd", r["reserved_usd"])
               for r in ledger["requests"] if r["task"].startswith(NAMESPACE))
    maximum = ((size + 8192) * INPUT_UPPER + MAX_OUTPUT * OUTPUT_RATE) / 1e6
    if used + maximum > LOCAL_CAP_USD:
        raise BudgetExceeded("local competence allocation cap")


async def episode(task, seal, path, row):
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    client = BudgetClient(Ledger(LEDGER), stage="discovery", task=NAMESPACE + task,
                          arm="batched_baseline")
    try:
        async with worker({"mode": "agent", "task_id": task}, path) as (send, receive):
            context = await receive()
            if context.get("type") != "context" or context["setup_calls"] != 11:
                raise ValueError("missing common-entry public context")
            row["context"] = context
            messages = [{"role": "system", "content": seal["system"]},
                        {"role": "user", "content": json.dumps(context)}]
            row.update(provider_trace=[], batches=[], api_calls=0, termination="incomplete")
            for _ in range(seal["max_model_requests"]):
                payload = {"messages": bounded_messages(messages), "tools": seal["tools"],
                           "parallel_tool_calls": False}
                study_reservation(payload)
                response = await client.create(**payload)
                row["provider_trace"].append(response.model_dump(mode="json"))
                message = response.choices[0].message
                messages.append(message.model_dump(exclude_none=True))
                write(path, row)
                if not message.tool_calls or len(message.tool_calls) != 1:
                    row["termination"] = "missing_or_multiple_tool_calls"
                    break
                call = message.tool_calls[0]
                if call.function.name == "finish":
                    row["termination"] = "finish"
                    break
                if call.function.name != "call_api_batch":
                    row["termination"] = "invalid_tool"
                    break
                try:
                    args = json.loads(call.function.arguments)
                    commands = args["calls"]
                    if not isinstance(commands, list) or not 1 <= len(commands) <= 8:
                        raise ValueError("invalid batch shape")
                    if row["api_calls"] + len(commands) > seal["max_api_calls"]:
                        row["termination"] = "api_call_limit"
                        break
                    await send({"type": "batch", "commands": commands})
                    result = await receive()
                    if result.get("type") != "batch_result":
                        raise ValueError("missing batch result")
                except (ValueError, KeyError, TypeError) as exc:
                    result = {"type": "batch_result", "calls": [],
                              "error": type(exc).__name__ + ": " + str(exc)[:300]}
                row["api_calls"] += len(result["calls"])
                row["batches"].append(result)
                write(path, row)
                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "content": json.dumps(model_view(result), default=str)})
            else:
                row["termination"] = "request_limit"
            await send({"type": "finish"})
            grade = await receive()
            if grade.get("type") != "evaluation" or grade["tests"] <= 0:
                raise ValueError("missing official grading")
            row["evaluation"] = grade
            row["status"] = "completed"
    finally:
        await client.close()


async def run():
    seal = verify()
    check_controls(seal)
    for task in seal["tasks"]:
        path = CACHE / "episodes" / task / "record.json"
        if path.exists():
            continue
        row = {"status": "started", "task_id": task, "arm": "batched_baseline"}
        write(path, row)
        started = time.monotonic()
        try:
            await asyncio.wait_for(episode(task, seal, path, row), seal["episode_seconds"])
        except Exception as exc:
            row.update(status="failed", error=type(exc).__name__, detail=str(exc)[:500])
            if isinstance(exc, BudgetExceeded):
                row["termination"] = "budget_limit"
                break
        finally:
            row["seconds"] = time.monotonic() - started
            write(path, row)
        print(json.dumps({"task": task, "status": row["status"],
                          "success": row.get("evaluation", {}).get("success"),
                          "requests": len(row.get("provider_trace", [])),
                          "api_calls": row.get("api_calls", 0)}), flush=True)


def export():
    seal = verify()
    check_controls(seal)
    if (OUT / "operational_evidence.bundle").exists():
        raise ValueError("published bundle exists; retain and version amendments")
    rows = []
    for task in seal["tasks"]:
        path = CACHE / "episodes" / task / "record.json"
        rows.append(json.loads(path.read_text()) if path.exists()
                    else {"task_id": task, "status": "unstarted"})
    if any(r["status"] == "started" for r in rows):
        raise ValueError("unfinished attempt")
    ledger = json.loads(LEDGER.read_text())
    charges = [r for r in ledger["requests"] if r["task"].startswith(NAMESPACE)]
    write(CACHE / "ledger_excerpt.json", {"requests": charges,
        "campaign_accounted_upper_usd": ledger["accounted_upper_usd"],
        "ledger_sha256": digest(LEDGER)})
    OUT.mkdir(parents=True, exist_ok=True)
    write(OUT / "seal.json", seal)
    subprocess.run(["docker", "run", "--rm", "--network", "none", "--read-only",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--memory", "4g",
        "--tmpfs", "/work:rw,nosuid,size=2g,mode=1777",
        "-v", f"{CACHE}:/input:ro", "-v", f"{OUT}:/output:rw",
        IMAGE, "-I", "-c", PACK], check=True, timeout=180)
    completed = [r for r in rows if r["status"] == "completed"]
    report = {"schema": "gac-appworld-batched-competence-report-v1",
        "scheduled": len(rows), "completed": len(completed),
        "failed": sum(r["status"] == "failed" for r in rows),
        "unstarted": sum(r["status"] == "unstarted" for r in rows),
        "official_successes": sum(r.get("evaluation", {}).get("success") is True for r in rows),
        "model_requests": sum(len(r.get("provider_trace", [])) for r in rows),
        "api_calls": sum(r.get("api_calls", 0) for r in rows),
        "known_common_setup_calls": 11 * sum("context" in r for r in rows),
        "attempts_without_verified_entry": sum(r["status"] != "unstarted" and "context" not in r for r in rows),
        "control_totals": {mode: {"scheduled": len(seal["tasks"]), "passed": len(seal["tasks"])}
                           for mode in seal["modes"]},
        "charged_upper_usd": sum(r.get("accounted_upper_usd", r["reserved_usd"]) for r in charges),
        "ledger_request_count": len(charges),
        "campaign_accounted_upper_usd": ledger["accounted_upper_usd"],
        "remaining_campaign_usd": ledger["cap_usd"] - ledger["accounted_upper_usd"],
        "ledger_sha256": digest(LEDGER),
        "independent_test_groups": 0, "gac_artifacts": 0,
        "encrypted_evidence_sha256": digest(OUT / "operational_evidence.bundle"),
        "bundle_verification": json.loads((OUT / "bundle_verification.json").read_text()),
        "protected_raw_files": [{"path": str(p.relative_to(CACHE)), "sha256": digest(p),
                                 "bytes": p.stat().st_size}
            for p in sorted(CACHE.rglob("*")) if p.is_file() and p.suffix not in {".tmp", ".lock"}],
        "decision": ("BASELINE_COMPETENT_DEVELOPMENT_ONLY" if
                     sum(r.get("evaluation", {}).get("success") is True for r in rows) >= 8
                     else "BASELINE_COMPETENCE_GATE_FAILED")}
    write(OUT / "report.json", report)
    print(json.dumps({k: report[k] for k in ("scheduled", "completed", "failed",
        "unstarted", "official_successes", "model_requests", "charged_upper_usd")}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "controls", "run", "export"))
    args = parser.parse_args()
    if args.command == "freeze": freeze()
    elif args.command == "controls": asyncio.run(controls())
    elif args.command == "run": asyncio.run(run())
    else: export()
