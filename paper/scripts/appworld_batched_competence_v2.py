"""Stronger-model amendment to the exposed AppWorld baseline competence pilot.

The original 1/12 GPT-5.6 Luna result and its encrypted evidence stay intact.
V2 uses GPT-5.6 Sol and an explicit completion reminder, while keeping the same
12 tasks, worker, batch tool, common entry, task caps and official grader.
This is development tuning, not a held-out model comparison or GAC result.
"""
import argparse
import asyncio
import json
from pathlib import Path
import subprocess
import time

from adaptive_pilot import ROOT, digest, write
from appworld_batched_competence import (CACHE as V1_CACHE, OUT as V1_OUT,
    PRIOR, INVENTORY, REFERENCES, WORKER, LEDGER, TOOLS, bounded_messages,
    model_view, worker, check_controls, verify as verify_v1)
from sol_campaign_budget import SolBudgetClient, MODEL, INPUT_UPPER, OUTPUT_RATE, MAX_OUTPUT, PRICE_SOURCE
from adaptive_campaign_budget import BudgetExceeded, clean
from export_appworld_viability import PACK

CACHE = ROOT / "benchmarks/.cache/appworld_batched_competence/v2"
OUT = ROOT / "paper/results/appworld_batched_competence_v2"
NAMESPACE = "appworld-batched-competence-v2:"
LOCAL_CAP_USD = 20.0
SYSTEM = ("Solve the user's task in the isolated AppWorld simulation with public APIs. "
    "Every app was authenticated through the same measured 11-call setup. "
    "Do not call login, profile or password APIs. Use access_token AUTO where "
    "required; the worker binds the token. Inspect unfamiliar API signatures "
    "with the api_docs APIs. Use call_api_batch with 1 to 8 fully specified calls "
    "when later arguments are already known; otherwise inspect each result "
    "before deciding the next call. Do not invent IDs or infer future results. "
    "The task is complete only after you call supervisor.complete_task with "
    "the appropriate answer when needed and check its result. Do not call "
    "finish merely because an earlier API returned successfully. If you cannot "
    "complete the task, call finish without claiming success. No reference "
    "solution, ground truth, private API, arbitrary code or external service "
    "is available. The independent saved-state tests determine success.")
SOURCES = (Path(__file__), ROOT / "paper/scripts/sol_campaign_budget.py",
    ROOT / "paper/scripts/appworld_batched_competence.py", WORKER,
    ROOT / "paper/scripts/adaptive_campaign_budget.py",
    ROOT / "paper/scripts/adaptive_pilot.py",
    ROOT / "paper/scripts/export_appworld_viability.py")


def freeze():
    if CACHE.exists():
        raise ValueError("v2 exists; retain every attempt")
    prior_seal = verify_v1()
    check_controls(prior_seal)
    rpc = json.loads((V1_CACHE / "rpc_controls/report.json").read_text())
    prior = json.loads((V1_OUT / "report.json").read_text())
    if (not rpc["all_passed"] or rpc["scheduled"] != 36 or prior["scheduled"] != 12
            or prior["official_successes"] != 1 or prior["decision"] != "BASELINE_COMPETENCE_GATE_FAILED"):
        raise ValueError("unexpected retained v1 evidence")
    seal = {"schema": "gac-appworld-batched-competence-v2",
        "status": "exposed development amendment; adapted preauthenticated entry; no native leaderboard claim",
        "amendment": "V1 GPT-5.6 Luna got 1/12; V2 changes to GPT-5.6 Sol and explicitly reminds the agent to call and check supervisor.complete_task. Tasks, worker, batch tool, common entry, official grader, 96 model-request and 192 API-call limits are unchanged. Both versions remain in the development denominator; neither is fresh confirmation.",
        "v1_seal_sha256": digest(V1_OUT / "seal.json"),
        "v1_report_sha256": digest(V1_OUT / "report.json"),
        "v1_bundle_sha256": digest(V1_OUT / "operational_evidence.bundle"),
        "rpc_report_sha256": digest(V1_CACHE / "rpc_controls/report.json"),
        "upstream_inventory_sha256": digest(INVENTORY),
        "prior_report_sha256": digest(PRIOR / "report.json"),
        "reference_hashes": prior_seal["reference_hashes"],
        "image": prior_seal["image"],
        "tasks": prior_seal["tasks"], "grouping": prior_seal["grouping"],
        "system": SYSTEM, "tools": TOOLS, "model": MODEL,
        "pricing_source": PRICE_SOURCE,
        "input_rate_upper_per_million": INPUT_UPPER,
        "output_rate_per_million": OUTPUT_RATE,
        "max_model_requests": 96, "max_api_calls": 192,
        "max_batch_calls": 8, "episode_seconds": 1200,
        "local_cap_usd": LOCAL_CAP_USD, "stage": "discovery",
        "stage_cap_usd": 30, "campaign_cap_usd": 300,
        "ledger_before_sha256": digest(LEDGER),
        "competence_gate": "At least 8/12 official successes, with all failures and unstarted attempts in the denominator. Development engineering gate only; not statistical noninferiority.",
        "failure_rule": "All 12 fixed scenarios remain scheduled; never retry or replace an attempt.",
        "source_hashes": {str(p.relative_to(ROOT)): digest(p) for p in SOURCES}}
    CACHE.mkdir(parents=True)
    write(CACHE / "seal.json", seal)
    for p in SOURCES:
        dest = CACHE / "sealed_sources" / p.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(p.read_bytes())
    print(json.dumps({"tasks": len(seal["tasks"]), "model": MODEL,
                      "local_cap_usd": LOCAL_CAP_USD}))


def verify():
    seal = json.loads((CACHE / "seal.json").read_text())
    if (digest(V1_OUT / "seal.json") != seal["v1_seal_sha256"]
            or digest(V1_OUT / "report.json") != seal["v1_report_sha256"]
            or digest(V1_OUT / "operational_evidence.bundle") != seal["v1_bundle_sha256"]
            or digest(V1_CACHE / "rpc_controls/report.json") != seal["rpc_report_sha256"]
            or digest(INVENTORY) != seal["upstream_inventory_sha256"]
            or digest(PRIOR / "report.json") != seal["prior_report_sha256"]
            or any(digest(REFERENCES / (t + ".json")) != h for t, h in seal["reference_hashes"].items())
            or any(digest(ROOT / p) != h for p, h in seal["source_hashes"].items())):
        raise ValueError("sealed v2 source or input drift")
    return seal


def study_reservation(payload):
    value = clean(payload)
    value.update(model=MODEL, max_completion_tokens=MAX_OUTPUT,
                 reasoning_effort="none", store=False, service_tier="default")
    size = len(json.dumps(value, ensure_ascii=False, sort_keys=True).encode())
    if size > 120_000:
        raise BudgetExceeded("competence amendment prompt byte cap")
    ledger = json.loads(LEDGER.read_text())
    used = sum(r.get("accounted_upper_usd", r["reserved_usd"])
               for r in ledger["requests"] if r["task"].startswith(NAMESPACE))
    maximum = ((size + 8192) * INPUT_UPPER + MAX_OUTPUT * OUTPUT_RATE) / 1e6
    if used + maximum > LOCAL_CAP_USD:
        raise BudgetExceeded("v2 local allocation cap")


async def episode(task, seal, path, row):
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    client = SolBudgetClient(LEDGER, stage="discovery", task=NAMESPACE + task,
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
    if (OUT / "operational_evidence.bundle").exists():
        raise ValueError("v2 bundle already published")
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
        seal["image"], "-I", "-c", PACK],
        check=True, timeout=180)
    completed = [r for r in rows if r["status"] == "completed"]
    successes = sum(r.get("evaluation", {}).get("success") is True for r in rows)
    report = {"schema": "gac-appworld-batched-competence-report-v2",
        "scheduled": len(rows), "completed": len(completed),
        "failed": sum(r["status"] == "failed" for r in rows),
        "unstarted": sum(r["status"] == "unstarted" for r in rows),
        "official_successes": successes,
        "model_requests": sum(len(r.get("provider_trace", [])) for r in rows),
        "api_calls": sum(r.get("api_calls", 0) for r in rows),
        "known_common_setup_calls": 11 * sum("context" in r for r in rows),
        "attempts_without_verified_entry": sum(r["status"] != "unstarted" and "context" not in r for r in rows),
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
        "decision": ("BASELINE_COMPETENT_DEVELOPMENT_ONLY" if successes >= 8
                     else "BASELINE_COMPETENCE_GATE_FAILED")}
    write(OUT / "report.json", report)
    print(json.dumps({k: report[k] for k in ("scheduled", "completed", "failed",
        "unstarted", "official_successes", "model_requests", "charged_upper_usd")}, sort_keys=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "run", "export"))
    args = parser.parse_args()
    if args.command == "freeze": freeze()
    elif args.command == "run": asyncio.run(run())
    else: export()
