"""Freeze and execute a bounded exploratory pilot; never a confirmatory study.

Commands: seal, run, report. No call is made by seal or report. Runtime outputs
and the persistent campaign ledger live in one fixed ignored local directory.
"""
import argparse
import ast
import asyncio
from collections import Counter, defaultdict
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys
import time

from adaptive_campaign_budget import BudgetClient, BudgetExceeded, Ledger, MODEL, STAGE_CAPS, TOTAL_CAP
from adaptive_pilot_runtime import ROOT, IMAGE, INSTRUCTIONS, SQLTools, dumps, registry, run_container
from adaptive_sql_grader import execute, compare
from audit_bird_revision import read_corrected, SNAPSHOT_SHA256

OUT = ROOT / "paper/results/adaptive_compiler_pilot"
LOCAL = ROOT / "benchmarks/.cache/adaptive_compiler_pilot"
DBROOT = ROOT / "benchmarks/.cache/bird/extract/dev_20240627/dev_databases"
QUESTIONS = ROOT / "benchmarks/.cache/bird/dev_20251106.json"
ARMS = ("baseline", "manual_prefetch", "agent_jit")
SEED = "gac-adaptive-pilot-2026-11-06-v1"
SOURCE_FILES = ["paper/scripts/" + name + ".py" for name in (
    "adaptive_pilot", "adaptive_pilot_runtime", "adaptive_campaign_budget", "adaptive_jit_generate", "adaptive_sql_grader",
    "probe_agent_jit_sql", "audit_bird_revision")]
SOURCE_FILES += ["experiments/adaptive_compiler_pilot/container_worker.py"]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")
    tmp.replace(path)


def select_tasks(questions, excluded, available):
    # Exclude all exact duplicates, including a duplicate of an excluded record.
    key = lambda q: (q["db_id"], " ".join(q["question"].split()).casefold())
    counts = Counter(key(q) for q in questions)
    eligible = defaultdict(list)
    dispositions = Counter()
    for q in questions:
        qid = q["question_id"]
        reason = ("previously_used" if qid in excluded else "web_exposed" if qid < 18
                  else "duplicate_question" if counts[key(q)] > 1 else "gold_unavailable" if qid not in available else "eligible")
        dispositions[reason] += 1
        if reason == "eligible":
            eligible[q["db_id"]].append(qid)
    tasks = []
    orders = list(itertools.permutations(ARMS))
    for db, ids in sorted(eligible.items()):
        if len(ids) < 4:
            continue
        ids.sort(key=lambda i: hashlib.sha256(f"{SEED}:{db}:{i}".encode()).hexdigest())
        for j, qid in enumerate(ids[:4]):
            tasks.append({"question_id": qid, "db_id": db, "discovery_split": "dev" if j == 3 else "train",
                          "arm_order": list(orders[len(tasks) % 6])})
    return tasks, dict(dispositions)


def seal():
    path = OUT / "seal.json"
    if path.exists() or (LOCAL / "ledger.json").exists():
        raise RuntimeError("seal already exists or campaign started; do not reset")
    source = ROOT / "paper/results/adaptive_comparison_preflight"
    screen = ROOT / "paper/results/calibration_population_audit/bird_source_screen.json"
    excluded = set(next(r["screened_ids"] for r in json.loads(screen.read_text())["splits"] if r["split"] == "dev"))
    audit = json.loads((source / "bird_revision_audit.json").read_text())
    available = {r["question_id"] for r in audit["gold_execution"]["rows"] if r["status"] == "ok"}
    tasks, disposition = select_tasks(read_corrected(QUESTIONS), excluded, available)
    pins = json.loads((source / "source_audit.json").read_text())["archives"]["dev"]["database_sha256"]
    selected_pins = {db: pins[db] for db in sorted({t["db_id"] for t in tasks})}
    for db, sha in selected_pins.items():
        if digest(DBROOT / db / f"{db}.sqlite") != sha:
            raise RuntimeError("database drift")
    document = {"schema": "gac-adaptive-pilot-seal-v1", "purpose": "exploratory feasibility; no quality or admission certificate",
        "seed": SEED, "model": MODEL, "model_is_mutable_alias": True, "reasoning_effort": "low",
        "max_completion_tokens": 4096, "episode_timeout_seconds": 600, "max_agent_turns": 12,
        "candidate_count": 32, "candidate_generation_concurrency": 4, "candidate_target": "sampled",
        "candidate_selection": "upstream minimum estimated runtime cost, first tie; no repairs",
        "primary_endpoint": "official-style unordered set execution accuracy; all scheduled arms in denominator",
        "diagnostics": ["row-shape-sensitive set", "duplicate-sensitive bag"],
        "failure_rule": "failed, interrupted, unstarted, invalid or timed-out prediction is incorrect; gold unavailable reported separately",
        "followup_exclusion": "every pilot ID excluded from future calibration and test",
        "campaign_cap_usd": TOTAL_CAP, "stage_caps_usd": STAGE_CAPS, "docker_image": IMAGE,
        "question_sha256": SNAPSHOT_SHA256, "database_sha256": selected_pins,
        "source_hashes": {p: digest(ROOT / p) for p in SOURCE_FILES},
        "screen_hashes": {str(p.relative_to(ROOT)): digest(p) for p in (screen, source / "bird_revision_audit.json", source / "source_audit.json")},
        "registry": registry(), "instructions": INSTRUCTIONS, "selection_dispositions": disposition,
        "tasks": tasks, "scheduled_episodes": len(tasks) * 3,
        "analysis": "descriptive paired outcomes; no p values, selection of winners or noninferiority claim",
        "gac": "mine all baseline traces in preassigned train/dev; empty calibration; no deployable artifact"}
    write(path, document)
    print(dumps({"sealed_tasks": len(tasks), "scheduled_episodes": len(tasks) * 3, "sha256": digest(path)}))


def verify(sealed):
    for p, sha in {**sealed["source_hashes"], **sealed["screen_hashes"]}.items():
        if digest(ROOT / p) != sha:
            raise RuntimeError(f"sealed file drift: {p}")
    for db, sha in sealed["database_sha256"].items():
        if digest(DBROOT / db / f"{db}.sqlite") != sha:
            raise RuntimeError("database drift")
    return {q["question_id"]: q for q in read_corrected(QUESTIONS)}


def task_text(q):
    return f"Database: {q['db_id']}\nQuestion: {q['question']}\nEvidence: {q.get('evidence') or 'none'}"


async def agent(q, toolset, client, arm, trace):
    text = task_text(q)
    if arm == "manual_prefetch":
        tables = toolset.call("list_tables", {})
        names = json.loads(tables["payload"])["tables"]
        schema = toolset.call("get_schema", {"table_names": names})
        text += "\nThe runtime already listed and read all tables. Reuse this information:\n" + dumps([tables, schema])
    messages = [{"role": "system", "content": INSTRUCTIONS}, {"role": "user", "content": text}]
    tools = [{"type": "function", "function": {"name": t["name"], "description": t["description"],
        "parameters": t["input_schema"]}} for t in registry()["tools"]]
    for turn in range(12):
        started = time.monotonic()
        response = await client.create(messages=messages, tools=tools, parallel_tool_calls=False)
        message = response.choices[0].message
        trace.append({"turn": turn, "response": response.model_dump(), "wall_seconds": time.monotonic() - started})
        messages.append(message.model_dump(exclude_none=True))
        if not message.tool_calls:
            return message.content
        for call in message.tool_calls:
            try:
                args = json.loads(call.function.arguments)
                result = toolset.call(call.function.name, args)
            except Exception as exc:
                result = {"payload": dumps({"error": type(exc).__name__})}
            messages.append({"role": "tool", "tool_call_id": call.id, "content": dumps(result)})
    raise RuntimeError("agent turn cap")


async def jit(q, toolset, client, trace, checkout, directory, sealed):
    request = {"ledger": str(LOCAL / "ledger.json"), "stage": "pilot", "task_id": str(q["question_id"]),
        "instructions": INSTRUCTIONS, "registry": registry(), "task": task_text(q),
        "state": {"tables_listed": False, "schema_read": False}, "candidates": sealed["candidate_count"]}
    write(directory / "generation_request.json", request)
    with (directory / "generation.log").open("w") as log:
        proc = await asyncio.create_subprocess_exec(str(checkout / ".venv/bin/python"),
            str(ROOT / "paper/scripts/adaptive_jit_generate.py"), str(directory / "generation_request.json"),
            str(directory / "candidates.json"), str(checkout), stdout=log, stderr=log)
        try:
            await proc.wait()
        finally:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()
    if proc.returncode:
        raise RuntimeError("upstream generation process failed; inspect retained log")
    generated = json.loads((directory / "candidates.json").read_text())
    index = generated["selected_index"]
    if index is None:
        raise RuntimeError("no statically valid candidate")
    async def dispatch(name, arguments):
        if name != "ai_eval":
            return toolset.call(name, arguments)
        if set(arguments) != {"prompt", "data"} or not isinstance(arguments["prompt"], str) or not isinstance(arguments["data"], dict):
            raise ValueError("invalid ai_eval arguments")
        def serialize(value):
            if isinstance(value, str):
                try:
                    return json.dumps(json.loads(value), indent=2)
                except ValueError:
                    return value
            return json.dumps(value, indent=2)
        context = "\n".join(f"{key}={serialize(value)}" for key, value in arguments["data"].items())
        prompt = arguments["prompt"] + ("\n\n" + context + "\n" if arguments["data"] else "")
        response = await client.create(messages=[{"role": "system", "content": generated["runtime_system_prompt"]}, {"role": "user", "content": prompt}])
        trace.append({"runtime_ai_eval": response.model_dump()})
        result = (response.choices[0].message.content or "").strip()
        if result.startswith(("[", "{")):
            for parse in (json.loads, ast.literal_eval):
                try:
                    return parse(result)
                except (ValueError, SyntaxError):
                    pass
        return result
    return await run_container(generated["candidates"][index]["code"], dispatch)


def answer_sql(value):
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict) or set(value) != {"sql"} or not isinstance(value["sql"], str):
        raise ValueError("expected JSON object with sql string")
    return value["sql"]


async def run(checkout, limit):
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    sealed = json.loads((OUT / "seal.json").read_text())
    questions = verify(sealed)
    LOCAL.mkdir(parents=True, exist_ok=True)
    if list(LOCAL.glob("*/result.json")) and not (LOCAL / "ledger.json").exists():
        raise RuntimeError("missing campaign ledger; cannot reset accounting")
    # Enforce a single campaign executor. Child generator only locks the ledger.
    import fcntl
    with (LOCAL / "runner.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        done = 0
        for spec in sealed["tasks"]:
            q = questions[spec["question_id"]]
            db = DBROOT / q["db_id"] / f"{q['db_id']}.sqlite"
            gold = execute(db, q["SQL"])
            for arm in spec["arm_order"]:
                directory = LOCAL / f"{q['question_id']}-{arm}"
                if (directory / "result.json").exists():
                    continue
                if limit is not None and done >= limit:
                    return
                tools = SQLTools(db)
                trace = []
                record = {"question_id": q["question_id"], "db_id": q["db_id"], "arm": arm,
                    "seal_sha256": digest(OUT / "seal.json"), "status": "interrupted", "execution_correct": False,
                    "gold_status": gold.status, "sql": None}
                # Persist the denominator before any request. Interrupted attempts are never replayed.
                write(directory / "result.json", record)
                client = BudgetClient(Ledger(LOCAL / "ledger.json"), stage="pilot", task=str(q["question_id"]), arm=arm)
                started = time.monotonic()
                try:
                    if gold.status != "ok":
                        raise RuntimeError("gold unavailable at execution")
                    operation = jit(q, tools, client, trace, checkout, directory, sealed) if arm == "agent_jit" else agent(q, tools, client, arm, trace)
                    value = await asyncio.wait_for(operation, sealed["episode_timeout_seconds"])
                    record["sql"] = answer_sql(value)
                    predicted = execute(db, record["sql"])
                    record.update(status="completed", predicted_status=predicted.status,
                        execution_correct=predicted.status == "ok" and set(gold.rows) == set(predicted.rows),
                        shape_set_correct=compare(gold, predicted, contract="set"), bag_correct=compare(gold, predicted, contract="bag"))
                except Exception as exc:
                    record.update(status="failed", error=type(exc).__name__, detail=str(exc)[:300])
                finally:
                    record.update(wall_seconds=time.monotonic() - started, tool_calls=tools.calls, provider_trace=trace)
                    write(directory / "result.json", record)
                    await client.close()
                done += 1
                print(dumps({k: record[k] for k in ("question_id", "arm", "status", "execution_correct", "wall_seconds")}), flush=True)
                if record.get("error") == "BudgetExceeded":
                    return
    verify(sealed)


def report():
    sealed = json.loads((OUT / "seal.json").read_text())
    ledger_path = LOCAL / "ledger.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {"requests": [], "accounted_upper_usd": 0}
    rows = []
    for spec in sealed["tasks"]:
        for arm in spec["arm_order"]:
            path = LOCAL / f"{spec['question_id']}-{arm}/result.json"
            raw = json.loads(path.read_text()) if path.exists() else {"status": "unstarted", "execution_correct": False}
            requests = [r for r in ledger["requests"] if r["task"] == str(spec["question_id"]) and r["arm"] == arm]
            row = {"question_id": spec["question_id"], "db_id": spec["db_id"], "arm": arm,
                **{k: raw.get(k) for k in ("status", "execution_correct", "shape_set_correct", "bag_correct", "gold_status", "predicted_status", "error", "wall_seconds")},
                "provider_requests": len(requests), "tool_calls": len(raw.get("tool_calls", [])),
                "accounted_upper_usd": sum(r.get("accounted_upper_usd", r["reserved_usd"]) for r in requests),
                "raw_sha256": digest(path) if path.exists() else None}
            candidates = path.parent / "candidates.json"
            if candidates.exists():
                data = json.loads(candidates.read_text())
                row.update(generated_candidates=len(data["candidates"]), valid_candidates=sum(bool(c and c.get("is_valid")) for c in data["candidates"]),
                           selected_index=data["selected_index"], candidates_sha256=digest(candidates))
            rows.append(row)
    summary = {arm: {"scheduled": len(sealed["tasks"]), "correct": sum(bool(r["execution_correct"]) for r in rows if r["arm"] == arm),
        "statuses": dict(Counter(r["status"] for r in rows if r["arm"] == arm)),
        "accounted_upper_usd": sum(r["accounted_upper_usd"] for r in rows if r["arm"] == arm)} for arm in ARMS}
    write(OUT / "report.json", {"schema": "gac-exploratory-pilot-report-v1", "seal_sha256": digest(OUT / "seal.json"),
        "campaign_accounted_upper_usd": ledger["accounted_upper_usd"], "budget_cap_usd": TOTAL_CAP,
        "summary": summary, "rows": rows, "claims": "exploratory only; no superiority, noninferiority, admission or learned-gate claim"})
    print(dumps(summary))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["seal", "run", "report"])
    parser.add_argument("--checkout", type=Path, default=Path("/tmp/gac-agent-jit-preflight"))
    parser.add_argument("--limit", type=int, help="maximum newly started episodes; resumes skip every previous attempt")
    args = parser.parse_args()
    if args.command == "seal":
        seal()
    elif args.command == "run":
        asyncio.run(run(args.checkout.resolve(), args.limit))
    else:
        report()
