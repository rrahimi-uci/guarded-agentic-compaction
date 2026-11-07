"""One-task, development-only adaptive batching pilot for selected Reddit task 714.

The task and its positive grader control were exposed before this pilot. This
runner cannot establish a fresh quality or cost effect. It tests whether a
competent agent can express the ranked read and first vote in one tool batch.
All provider requests use the shared, fail-closed campaign ledger.
"""
import argparse
import asyncio
import json
from pathlib import Path
import tarfile
import time

from adaptive_benchmark_screen import ROOT, PINS, check_source, sha
from adaptive_campaign_budget import BudgetClient, Ledger, MODEL
from reddit_ranked_read_feasibility import TASK, IMAGE, DATA, SOURCE, SELECTION, blueprint
from browser_staging_boundary import Session
from webarena_verified_development import allowed_url, bounded_messages, evaluator, runtime_versions, snapshot, write

OUT = ROOT / "paper/results/reddit_batched_adaptive_pilot"
LOCAL = ROOT / "benchmarks/.cache/reddit_batched_adaptive_pilot/v1"
CONTROL = ROOT / "paper/results/reddit_ranked_read_feasibility_v3"
LEDGER = ROOT / "benchmarks/.cache/adaptive_compiler_pilot/ledger.json"
SOURCE_PATHS = (Path(__file__), ROOT / "paper/scripts/adaptive_campaign_budget.py",
    ROOT / "paper/scripts/reddit_ranked_read_feasibility.py",
    ROOT / "paper/scripts/browser_staging_boundary.py",
    ROOT / "paper/scripts/webarena_verified_development.py", SELECTION)
SYSTEM = ("You are an autonomous browser agent on an isolated Reddit clone. "
    "Complete the public task from the current page. You may call browser_batch "
    "with 1 to 8 ordered actions when their arguments are already known. You "
    "receive each intermediate page observation after the batch. A batch stops "
    "on an action error. Use index for repeated controls, starting at zero. "
    "You may use a single-action batch when you need to inspect a result. "
    "Stay on the provided site. Do not use scripts, shell, hidden task definitions, "
    "or reference answers. Finish with the structured response. Only claim "
    "SUCCESS after checking the resulting page.")
ACTION = {"type": "object", "properties": {
    "action": {"type": "string", "enum": ["goto", "click", "fill", "select", "press", "back", "observe"]},
    "role": {"type": "string"}, "name": {"type": "string"},
    "value": {"type": "string"}, "index": {"type": "integer", "minimum": 0, "maximum": 99}},
    "required": ["action"], "additionalProperties": False}
TOOLS = [{"type": "function", "function": {
    "name": "browser_batch", "description": "Execute 1 to 8 already specified browser actions in order; return every intermediate page observation and stop on error. Index selects a repeated control, starting at zero.",
    "parameters": {"type": "object", "properties": {"actions": {
        "type": "array", "minItems": 1, "maxItems": 8, "items": ACTION}},
        "required": ["actions"], "additionalProperties": False}}},
    {"type": "function", "function": {"name": "finish",
    "description": "Finish with the official structured task response.",
    "parameters": {"type": "object", "properties": {
        "task_type": {"type": "string", "enum": ["RETRIEVE", "MUTATE", "NAVIGATE"]},
        "status": {"type": "string", "enum": ["SUCCESS", "UNKNOWN_ERROR"]},
        "retrieved_data": {"type": ["array", "null"], "items": {}},
        "error_details": {"type": ["string", "null"]}},
        "required": ["task_type", "status", "retrieved_data", "error_details"],
        "additionalProperties": False}}}]


def validate_batch(payload, base):
    if not isinstance(payload, dict) or set(payload) != {"actions"}:
        raise ValueError("expected actions only")
    rows = payload["actions"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 8:
        raise ValueError("batch must contain 1 to 8 actions")
    required = {"goto": {"value"}, "click": {"role", "name"},
                "fill": {"role", "name", "value"},
                "select": {"role", "name", "value"},
                "press": {"role", "name", "value"},
                "back": set(), "observe": set()}
    for row in rows:
        if not isinstance(row, dict) or row.get("action") not in required:
            raise ValueError("invalid action")
        kind = row["action"]
        expected = {"action"} | required[kind]
        if set(row) not in (expected, expected | {"index"} if kind in {"click", "fill", "select", "press"} else expected):
            raise ValueError("invalid action fields")
        if any(not isinstance(row[k], str) for k in required[kind]):
            raise ValueError("action fields must be strings")
        if "index" in row and (type(row["index"]) is not int or not 0 <= row["index"] <= 99):
            raise ValueError("invalid index")
        if kind == "goto" and not allowed_url(row["value"], base):
            raise ValueError("navigation outside isolated site")
    return rows


async def execute(page, row, base):
    kind = row["action"]
    if kind == "goto":
        await page.goto(row["value"], wait_until="domcontentloaded")
    elif kind in {"click", "fill", "select", "press"}:
        target = page.get_by_role(row["role"], name=row["name"], exact=True)
        if "index" in row:
            target = target.nth(row["index"])
        if kind == "click":
            await target.click(timeout=30000)
        elif kind == "fill":
            await target.fill(row["value"], timeout=30000)
        elif kind == "select":
            await target.select_option(label=row["value"], timeout=30000)
        else:
            await target.press(row["value"], timeout=30000)
    elif kind == "back":
        await page.go_back(wait_until="domcontentloaded")
    await page.wait_for_load_state("networkidle", timeout=30000)
    await page.wait_for_timeout(250)  # let in-flight vote responses reach HAR
    return await snapshot(page)


async def batch(page, payload, base):
    rows = validate_batch(payload, base)  # validate every action before effects
    outcomes = []
    for row in rows:
        try:
            observation = await execute(page, row, base)
        except Exception as exc:
            observation = {"error": type(exc).__name__, "detail": str(exc)[:500]}
        outcomes.append({"command": row, "observation": observation})
        if "error" in observation:
            break
    return {"actions": outcomes, "requested": len(rows),
            "stopped_on_error": "error" in outcomes[-1]["observation"]}


def freeze():
    check_source(SOURCE, PINS["webarena-verified"])
    if LOCAL.exists():
        raise ValueError("pilot version exists; retain the attempt")
    control = json.loads((CONTROL / "report.json").read_text())
    if control["all_passed"] is not True or control["scheduled"] != 1:
        raise ValueError("source/official-grader control not passed")
    seal = {"schema": "gac-reddit-batched-adaptive-pilot-v1", "task_id": TASK,
        "status": "development-only; exposed task; no independent quality-cost estimate",
        "image": IMAGE, "source_revision": PINS["webarena-verified"],
        "data_sha256": sha(DATA), "control_report_sha256": sha(CONTROL / "report.json"),
        "control_archive_sha256": sha(CONTROL / "raw_evidence.tar.gz"),
        "sources": {str(p.relative_to(ROOT)): sha(p) for p in SOURCE_PATHS},
        "system": SYSTEM, "tools": TOOLS, "model": MODEL,
        "max_model_requests": 16, "max_browser_actions": 64,
        "max_batch_actions": 8, "episode_seconds": 600,
        "stage": "discovery", "campaign_cap_usd": 300, "stage_cap_usd": 30,
        "runtime_versions": runtime_versions(),
        "failure_rule": "The one scheduled attempt remains in the denominator; never retry or replace it.",
        "provider_data": "Public task input and live accessibility observations only; no hidden evaluation fields."}
    LOCAL.mkdir(parents=True)
    write(LOCAL / "seal.json", seal)
    for path in SOURCE_PATHS:
        dest = LOCAL / "source" / path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(path.read_bytes())
    print("sealed exposed-task batched baseline pilot")


def verify():
    seal = json.loads((LOCAL / "seal.json").read_text())
    check_source(SOURCE, seal["source_revision"])
    if (sha(DATA) != seal["data_sha256"] or sha(CONTROL / "report.json") != seal["control_report_sha256"]
            or sha(CONTROL / "raw_evidence.tar.gz") != seal["control_archive_sha256"]
            or any(sha(ROOT / p) != h for p, h in seal["sources"].items())
            or runtime_versions() != seal["runtime_versions"]):
        raise ValueError("sealed source, control or runtime drift")
    return seal


async def run():
    from dotenv import load_dotenv
    from webarena_verified.types.agent_response import FinalAgentResponse
    seal = verify()
    target = LOCAL / "714"
    target.mkdir(exist_ok=False)
    state = {"status": "started", "task_id": TASK, "arm": "strong_batched_agent",
             "provider_trace": [], "batches": [], "browser_actions": 0,
             "termination": "incomplete"}
    write(target / "record.json", state)
    load_dotenv(ROOT / ".env")
    client = None
    session = Session(blueprint(), target / "session", staged=False)
    start = time.monotonic()
    try:
        client = BudgetClient(Ledger(LEDGER), stage="discovery", task="reddit-batched-v1:714", arm="baseline")
        await session.start()
        task = session.task
        state["input"] = task
        messages = [{"role": "system", "content": seal["system"]},
            {"role": "user", "content": json.dumps({"task": task, "observation": session.entry_observation})}]
        answer = None
        for _ in range(seal["max_model_requests"]):
            if time.monotonic() - start > seal["episode_seconds"]:
                state["termination"] = "episode_timeout"
                break
            response = await client.create(messages=bounded_messages(messages), tools=seal["tools"], parallel_tool_calls=False)
            state["provider_trace"].append(response.model_dump(mode="json"))
            write(target / "record.json", state)
            message = response.choices[0].message
            messages.append(message.model_dump(exclude_none=True))
            if not message.tool_calls or len(message.tool_calls) != 1:
                state["termination"] = "missing_or_multiple_tool_calls"
                break
            call = message.tool_calls[0]
            args = json.loads(call.function.arguments)
            if call.function.name == "finish":
                answer = FinalAgentResponse.model_validate(args).model_dump(mode="json")
                state["termination"] = "finish"
                break
            if call.function.name != "browser_batch":
                state["termination"] = "invalid_tool"
                break
            if state["browser_actions"] >= seal["max_browser_actions"]:
                state["termination"] = "action_limit"
                break
            try:
                commands = validate_batch(args, session.base)
                if state["browser_actions"] + len(commands) > seal["max_browser_actions"]:
                    state["termination"] = "action_limit"
                    break
                result = await batch(session.page, args, session.base)
            except Exception as exc:
                result = {"error": type(exc).__name__, "detail": str(exc)[:500], "actions": []}
            state["browser_actions"] += len(result["actions"])
            state["batches"].append(result)
            write(target / "record.json", state)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result)})
        else:
            state["termination"] = "request_limit"
        if answer is None:
            answer = {"task_type": "MUTATE", "status": "UNKNOWN_ERROR",
                      "retrieved_data": None, "error_details": "Agent did not finish successfully"}
        state["answer"] = answer
        base = session.base
        await session.close()
        grade = evaluator(base).evaluate_task(task_id=TASK, agent_response=answer,
            network_trace=target / "session/network.har")
        state["evaluation"] = grade.model_dump(mode="json")
        state["status"] = "completed"
    except Exception as exc:
        state.update(status="failed", error=type(exc).__name__, detail=str(exc)[:500])
    finally:
        try:
            await session.close()
        except Exception as exc:
            state.update(status="failed", cleanup_error=str(exc)[:500])
        if client:
            await client.close()
        state["seconds_including_cleanup"] = time.monotonic() - start
        write(target / "record.json", state)
    print(json.dumps({k: state.get(k) for k in ("status", "termination", "browser_actions", "error", "detail")}), flush=True)


def export():
    verify()
    state = json.loads((LOCAL / "714/record.json").read_text())
    if state["status"] == "started":
        raise ValueError("pilot still running")
    OUT.mkdir(parents=True, exist_ok=False)
    members = []
    archive = OUT / "raw_evidence.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for p in sorted(LOCAL.rglob("*")):
            if p.is_file():
                rel = str(p.relative_to(LOCAL))
                tar.add(p, arcname=rel, recursive=False)
                members.append({"path": rel, "sha256": sha(p), "bytes": p.stat().st_size})
        tar.add(SOURCE / "LICENSE", arcname="upstream/LICENSE", recursive=False)
    ledger = json.loads(LEDGER.read_text())
    charged = [r for r in ledger["requests"] if r["task"] == "reddit-batched-v1:714"]
    write(OUT / "seal.json", json.loads((LOCAL / "seal.json").read_text()))
    write(OUT / "report.json", {"schema": "gac-reddit-batched-adaptive-pilot-report-v1",
        "task_id": TASK, "status": state["status"], "termination": state["termination"],
        "official_status": state.get("evaluation", {}).get("status"),
        "model_requests": len(state["provider_trace"]), "browser_batches": len(state["batches"]),
        "browser_actions": state["browser_actions"],
        "first_batch_actions": len(state["batches"][0].get("actions", [])) if state["batches"] else 0,
        "ledger_charged_upper_usd": sum(r.get("accounted_upper_usd", r["reserved_usd"]) for r in charged),
        "ledger_request_count": len(charged),
        "all_attempts": 1, "independent_task_groups": 0, "gac_artifacts": 0,
        "archive_sha256": sha(archive), "files": members})
    print("exported development-only batched pilot")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "run", "export"))
    args = parser.parse_args()
    if args.command == "freeze":
        freeze()
    elif args.command == "run":
        asyncio.run(run())
    else:
        export()
