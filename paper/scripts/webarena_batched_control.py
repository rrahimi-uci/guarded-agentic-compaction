"""Provider-free batching controls on two already exposed WebArena tasks.

Trusted historical answers/actions are control fixtures only. This module has no
model client and never admits a GAC artifact. Generic browser actions remain
UNKNOWN effects; batching a write does not make it safe to speculate.
"""
import argparse
import asyncio
import copy
import hashlib
import json
from pathlib import Path
import re
import tarfile
import time

from adaptive_benchmark_screen import ROOT, PINS, check_source, sha
from browser_staging_boundary import Blueprint, Session, IMAGE
from webarena_verified_development import DATA, SOURCE, action, allowed_url, evaluator, runtime_versions, snapshot, write

OUT = ROOT / "paper/results/adaptive_comparison_followup"
LOCAL = ROOT / "benchmarks/.cache/adaptive_comparison_followup/batch-controls-v2"
PRIOR = ROOT / "paper/results/adaptive_benchmark_screen/webarena_development"
MAX_BATCH = 8
ACTION_SCHEMA = {
    "type": "object", "properties": {
        "action": {"type": "string", "enum": ["goto", "click", "fill", "select", "press", "back", "observe"]},
        "role": {"type": "string"}, "name": {"type": "string"}, "value": {"type": "string"}},
    "required": ["action"], "additionalProperties": False}
BATCH_TOOL = {"type": "function", "function": {
    "name": "browser_batch",
    "description": "Execute 1 to 8 ordered browser actions without another model turn. Use only arguments already known. Every intermediate observation is returned; stop on the first error. Actions may write and are not speculative or rolled back.",
    "parameters": {"type": "object", "properties": {"actions": {
        "type": "array", "minItems": 1, "maxItems": MAX_BATCH, "items": ACTION_SCHEMA}},
        "required": ["actions"], "additionalProperties": False}}}


def validate_batch(payload, base):
    if not isinstance(payload, dict) or set(payload) != {"actions"}:
        raise ValueError("expected actions only")
    commands = payload["actions"]
    if not isinstance(commands, list) or not 1 <= len(commands) <= MAX_BATCH:
        raise ValueError("batch must have 1 to 8 actions")
    for args in commands:
        if not isinstance(args, dict) or not all(isinstance(v, str) for v in args.values()):
            raise ValueError("action fields must be strings")
        kind = args.get("action")
        fields = {"goto": {"value"}, "click": {"role", "name"},
                  "fill": {"role", "name", "value"}, "select": {"role", "name", "value"},
                  "press": {"role", "name", "value"}, "back": set(), "observe": set()}
        if kind not in fields or set(args) != fields[kind] | {"action"}:
            raise ValueError("invalid action fields")
        if kind == "goto" and not allowed_url(args["value"], base):
            raise ValueError("navigation outside isolated site")
    return copy.deepcopy(commands)


async def settled_action(page, args, base):
    await action(page, args, base)
    await page.wait_for_load_state("networkidle", timeout=30000)
    return await snapshot(page)


def comparison_view(actions, base, task_id):
    """Control-only comparison; original observations always remain retained.

    Posting task 634 has a newly generated timestamp and random empty-comment
    emoji. Normalize only these displayed fields, not task data, errors or URLs.
    This is not a production state-equivalence rule or a task-answer grader.
    """
    value = json.loads(json.dumps(actions).replace(base, "__REDDIT__"))
    if task_id == 634:
        for result in value:
            observation = result["observation"]
            if "page" in observation:
                observation["page"] = re.sub(r'(?m)^(\s*- time:) on [A-Z][a-z]+ \d{1,2}, \d{4} at \d{1,2}:\d{2} [AP]M$',
                    r'\1 [new-post display time]', observation["page"])
                observation["page"] = re.sub(r'(?m)^(\s*- img "A tense emoji":).+$',
                    r'\1 [decorative emoji]', observation["page"])
    return value


def positive_passes(actions, commands, grade_status):
    return (grade_status == "success" and [a["command"] for a in actions] == commands
            and all("error" not in a["observation"] for a in actions))


async def batch(page, payload, base, *, execute=settled_action):
    commands = validate_batch(payload, base)  # reject malformed tail before any effect
    results = []
    for args in commands:
        try:
            observation = await execute(page, args, base)
        except Exception as exc:
            observation = {"error": type(exc).__name__, "detail": str(exc)[:500]}
        results.append({"command": args, "observation": observation})
        if "error" in observation:
            break
    return {"actions": results, "requested": len(commands),
            "completed_without_error": sum("error" not in r["observation"] for r in results),
            "stopped_on_error": "error" in results[-1]["observation"]}


def fixtures():
    archive = PRIOR / "raw_evidence.tar.gz"
    if sha(archive) != json.loads((PRIOR / "report.json").read_text())["raw_archive_sha256"]:
        raise ValueError("historical control archive changed")
    with tarfile.open(archive) as tar:
        raws = [json.load(tar.extractfile(f"development-v2/{task}/attempt.json")) for task in (69, 634)]
    result = []
    for raw in raws:
        # Remove the historically failed selector and the unnecessary URL-mode
        # radio action on the posting fixture. This is a handwritten control,
        # never an automatically discovered program or a new agent trajectory.
        commands = [a["command"] for a in raw["actions"] if "error" not in a["observation"]
                    and a["command"] != {"action": "click", "name": "URL", "role": "radio"}]
        result.append({"task_id": raw["task_id"], "commands": commands, "answer": raw["answer"]})
    return result


def freeze():
    check_source(SOURCE, PINS["webarena-verified"])
    if LOCAL.exists():
        raise ValueError("control version exists; preserve all attempts")
    source_paths = [Path(__file__), ROOT / "paper/scripts/browser_staging_boundary.py",
        ROOT / "paper/scripts/webarena_verified_development.py", ROOT / "paper/scripts/adaptive_benchmark_screen.py"]
    value = {"schema": "gac-batching-controls-v2", "fixtures": fixtures(), "image": IMAGE,
             "amendment": "Retain v1: expected grader outcomes did not establish action success or observation parity. Require successful complete positive actions, 30-second action limits and settled snapshots. Normalize only the new-post display timestamp and decorative empty-comment emoji in task 634; retain raw observations. No paid runs occurred.",
             "source_revision": PINS["webarena-verified"], "data_sha256": sha(DATA),
             "sources": {str(p.relative_to(ROOT)): sha(p) for p in source_paths},
             "runtime_versions": runtime_versions(), "provider_calls": 0,
             "scope": "Trusted control replay only; no adaptive model, compilation, saved-request or quality-cost result.",
             "scheduled": [{"task_id": t, "mode": m} for t in (69, 634)
                           for m in ("sequential", "batch", "empty", "false_completion")]
                          + [{"task_id": 634, "mode": "first_error"}]}
    LOCAL.mkdir(parents=True)
    write(LOCAL / "seal.json", value)
    for p in source_paths:
        target = LOCAL / "source" / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(p.read_bytes())
    print("sealed nine provider-free controls; two previously exposed tasks")


def verify():
    seal = json.loads((LOCAL / "seal.json").read_text())
    check_source(SOURCE, seal["source_revision"])
    if sha(DATA) != seal["data_sha256"] or any(sha(ROOT / p) != h for p, h in seal["sources"].items()):
        raise ValueError("sealed source/data drift")
    if runtime_versions() != seal["runtime_versions"]:
        raise ValueError("sealed runtime drift")
    return seal


async def control(item, seal):
    fixture = next(f for f in seal["fixtures"] if f["task_id"] == item["task_id"])
    target = LOCAL / f"{item['task_id']}-{item['mode']}"
    target.mkdir(exist_ok=False)
    state = {**item, "status": "started", "provider_calls": 0}
    write(target / "record.json", state)
    session = Session(Blueprint.development(item["task_id"]), target / "session", staged=False)
    started = time.monotonic()
    try:
        await session.start()
        session.page.set_default_timeout(30000)
        commands = fixture["commands"]
        if item["mode"] in {"empty", "false_completion"}:
            commands = []
        elif item["mode"] == "first_error":
            commands = [{"action": "click", "role": "button", "name": "GAC nonexistent control target"}] + commands
        if item["mode"] == "sequential":
            state["actions"] = []
            for args in commands:
                output = await batch(session.page, {"actions": [args]}, session.base)
                state["actions"].extend(output["actions"])
                if output["stopped_on_error"]:
                    break
        elif commands:
            state.update(await batch(session.page, {"actions": commands}, session.base))
        else:
            state["actions"] = []
        answer = copy.deepcopy(fixture["answer"])
        if item["mode"] in {"empty", "false_completion", "first_error"}:
            answer.update(status="UNKNOWN_ERROR" if item["mode"] == "empty" else "SUCCESS",
                          retrieved_data=[] if answer["task_type"] == "RETRIEVE" else None,
                          error_details="No task execution" if item["mode"] == "empty" else None)
        state["answer"] = answer
        state["base"] = session.base
        state["normalized_actions"] = comparison_view(state["actions"], session.base, item["task_id"])
        await session.context.close()  # flush complete HAR before official evaluation
        grade = evaluator(session.base).evaluate_task(task_id=item["task_id"], agent_response=answer,
            network_trace=target / "session/network.har")
        state["evaluation"] = grade.model_dump(mode="json")
        expected = "success" if item["mode"] in {"batch", "sequential"} else "failure"
        state["passed"] = str(grade.status) == expected
        if item["mode"] in {"batch", "sequential"}:
            state["passed"] = positive_passes(state["actions"], commands, str(grade.status))
        if item["mode"] == "first_error":
            state["passed"] &= len(state["actions"]) == 1 and state["stopped_on_error"]
        state["status"] = "completed"
    except Exception as exc:
        state.update(status="failed", passed=False, error=type(exc).__name__, detail=str(exc)[:500])
    finally:
        try:
            await session.close()
        except Exception as exc:
            state.update(status="failed", passed=False, cleanup_error=str(exc)[:500])
        state["seconds_including_cleanup"] = time.monotonic() - started
        write(target / "record.json", state)
    print(json.dumps({k: state[k] for k in ("task_id", "mode", "status", "passed")}), flush=True)


async def run():
    seal = verify()
    for item in seal["scheduled"]:
        if (LOCAL / f"{item['task_id']}-{item['mode']}").exists():
            continue  # failed and partial attempts are never retried
        await control(item, seal)


def export():
    seal = verify()
    records = [json.loads((LOCAL / f"{i['task_id']}-{i['mode']}" / "record.json").read_text()) for i in seal["scheduled"]]
    if any(r["status"] == "started" for r in records):
        raise ValueError("unfinished controls")
    pairs = []
    for task in (69, 634):
        a, b = [next(r for r in records if r["task_id"] == task and r["mode"] == m) for m in ("sequential", "batch")]
        pairs.append({"task_id": task, "actions_equal_after_declared_display_normalization":
                      "normalized_actions" in a and a.get("normalized_actions") == b.get("normalized_actions"),
                      "action_count": len(b.get("actions", []))})
    target = OUT / "batch_controls_v2"
    target.mkdir(parents=True, exist_ok=False)
    archive = target / "raw_evidence.tar.gz"
    members = []
    with tarfile.open(archive, "w:gz") as tar:
        paths = [(p, str(p.relative_to(LOCAL))) for p in sorted(LOCAL.rglob("*")) if p.is_file()]
        paths.append((SOURCE / "LICENSE", "upstream/LICENSE"))
        for p, rel in paths:
            tar.add(p, arcname=rel, recursive=False)
            members.append({"path": rel, "sha256": sha(p), "bytes": p.stat().st_size})
    write(target / "seal.json", seal)
    report = {"schema": "gac-batching-control-report-v2", "scheduled": len(records),
              "passed": sum(r.get("passed", False) for r in records), "pairs": pairs,
              "all_passed": all(r.get("passed", False) for r in records) and all(p["actions_equal_after_declared_display_normalization"] for p in pairs),
              "provider_calls": 0, "scope": seal["scope"],
              "rows": [{k: r.get(k) for k in ("task_id", "mode", "status", "passed", "seconds_including_cleanup")} for r in records],
              "archive_sha256": sha(archive), "files": members}
    write(target / "report.json", report)
    print(json.dumps({k: report[k] for k in ("scheduled", "passed", "pairs", "all_passed")}))


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
