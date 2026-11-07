"""Provider-free exact agent-RPC controls for the sealed AppWorld batch study.

Reference calls are protected local control inputs only. This uses the same
worker agent mode, batch messages, save and official grader as paid execution.
"""
import argparse
import asyncio
import json
from pathlib import Path
import time

from adaptive_pilot import ROOT, digest, write
from appworld_batched_competence import CACHE, REFERENCES, WORKER, public_reference_calls, worker

LOCAL = CACHE / "rpc_controls"
SOURCES = (Path(__file__), ROOT / "paper/scripts/appworld_batched_competence.py", WORKER)
MODES = ("reference", "empty", "false_completion")


def freeze():
    if LOCAL.exists():
        raise ValueError("RPC controls already sealed")
    prior = json.loads((CACHE / "seal.json").read_text())
    seal = {"schema": "gac-appworld-batched-rpc-controls-v1",
        "prior_seal_sha256": digest(CACHE / "seal.json"),
        "tasks": prior["tasks"], "modes": MODES,
        "sources": {str(p.relative_to(ROOT)): digest(p) for p in SOURCES},
        "reference_hashes": prior["reference_hashes"],
        "scope": "provider-free exact agent RPC path; protected references never enter model context",
        "provider_calls": 0}
    LOCAL.mkdir(parents=True)
    write(LOCAL / "seal.json", seal)
    for p in SOURCES:
        dest = LOCAL / "source" / p.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(p.read_bytes())
    print("sealed 36 exact agent-RPC controls")


def verify():
    seal = json.loads((LOCAL / "seal.json").read_text())
    if (digest(CACHE / "seal.json") != seal["prior_seal_sha256"]
            or any(digest(ROOT / p) != h for p, h in seal["sources"].items())
            or any(digest(REFERENCES / (task + ".json")) != h
                   for task, h in seal["reference_hashes"].items())):
        raise ValueError("sealed RPC control source or input drift")
    return seal


async def attempt(task, mode):
    path = LOCAL / task / (mode + ".json")
    if path.exists():
        return
    row = {"status": "started", "task_id": task, "mode": mode,
           "provider_calls": 0, "passed": False, "batch_results": []}
    write(path, row)
    started = time.monotonic()
    try:
        async with worker({"mode": "agent", "task_id": task}, path) as (send, receive):
            context = await receive()
            if context.get("type") != "context" or context.get("setup_calls") != 11:
                raise ValueError("missing common-entry agent context")
            row["entry_state_sha256"] = context["entry_state_sha256"]
            commands = []
            if mode == "reference":
                ref = json.loads((REFERENCES / (task + ".json")).read_text())
                commands = public_reference_calls(ref)
            elif mode == "false_completion":
                commands = [{"app": "supervisor", "api": "complete_task",
                             "arguments": {"answer": "UNSUPPORTED ANSWER"}}]
            for i in range(0, len(commands), 8):
                await send({"type": "batch", "commands": commands[i:i + 8]})
                result = await receive()
                if result.get("type") != "batch_result" or result.get("error"):
                    raise ValueError("agent RPC batch rejected")
                row["batch_results"].append(result)
            await send({"type": "finish"})
            grade = await receive()
            if grade.get("type") != "evaluation":
                raise ValueError("missing official agent-path grade")
            row["evaluation"] = grade
            row["passed"] = (grade["tests"] > 0 and grade["setup_calls"] == 11
                             and grade["success"] is (mode == "reference")
                             and grade["entry_state_sha256"] == row["entry_state_sha256"])
            row["status"] = "completed"
    except Exception as exc:
        row.update(status="failed", passed=False, error=type(exc).__name__, detail=str(exc)[:500])
    finally:
        row["seconds"] = time.monotonic() - started
        write(path, row)
    print(json.dumps({"task": task, "mode": mode, "passed": row["passed"]}), flush=True)


async def run():
    seal = verify()
    for task in seal["tasks"]:
        for mode in seal["modes"]:
            await attempt(task, mode)


def report():
    seal = verify()
    rows = [json.loads((LOCAL / task / (mode + ".json")).read_text())
            for task in seal["tasks"] for mode in seal["modes"]]
    if any(r["status"] == "started" for r in rows):
        raise ValueError("RPC controls incomplete")
    for task in seal["tasks"]:
        cohort = [r for r in rows if r["task_id"] == task]
        if len({r.get("entry_state_sha256") for r in cohort}) != 1:
            raise ValueError("agent RPC entry state differs across modes")
    result = {"schema": "gac-appworld-batched-rpc-control-report-v1",
        "scheduled": len(rows), "passed": sum(r["passed"] for r in rows),
        "all_passed": all(r["passed"] for r in rows),
        "provider_calls": 0, "independent_test_groups": 0,
        "seal_sha256": digest(LOCAL / "seal.json")}
    write(LOCAL / "report.json", result)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "run", "report"))
    args = parser.parse_args()
    if args.command == "freeze": freeze()
    elif args.command == "run": asyncio.run(run())
    else: report()
