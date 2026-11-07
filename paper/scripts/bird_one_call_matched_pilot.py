"""Sealed developmental BIRD continuation pilot for one research candidate.

Three arms share fixed tasks, tools, prompt, model and grader: unchanged agent,
handwritten one-call prefix, and guard/program/verifier research candidate.
The candidate has no calibration or admitted GAC artifact. This is a mechanism
and quality/cost feasibility test, never a confirmatory superiority result.
"""
import argparse
import asyncio
from collections import Counter
from dataclasses import asdict
import fcntl
import gzip
import itertools
import json
from pathlib import Path
import tarfile
import time

from adaptive_campaign_budget import BudgetClient, BudgetExceeded, Ledger, MODEL, TOTAL_CAP
from adaptive_pilot import ROOT, digest, write
from adaptive_pilot_runtime import INSTRUCTIONS, SQLTools, dumps, registry
from adaptive_sql_grader import execute, compare
from audit_bird_revision import read_corrected, SNAPSHOT_SHA256
from bird_one_call_matched_candidate import POLICY
from bird_one_call_continuation_preflight import synthetic_prefix
from guarded_agentic_compaction.capture.manifests import build_manifest
from guarded_agentic_compaction.grc.program import program_from_dict
from guarded_agentic_compaction.runtime.facade import FacadeMode, ToolFacade
from guarded_agentic_compaction.runtime.interp import run_program
from guarded_agentic_compaction.schema.artifacts import HardGuard, Verifier
from guarded_agentic_compaction.schema.effects import EffectCatalog

PILOT = ROOT / "paper/results/adaptive_compiler_pilot"
PREFLIGHT = ROOT / "paper/results/bird_one_call_continuation_preflight"
CANDIDATE = PREFLIGHT / "candidate.json"
OUT = ROOT / "paper/results/bird_one_call_matched_pilot"
CACHE = ROOT / "benchmarks/.cache/bird_one_call_matched_pilot/v1"
LEDGER = ROOT / "benchmarks/.cache/adaptive_compiler_pilot/ledger.json"
DBROOT = ROOT / "benchmarks/.cache/bird/extract/dev_20240627/dev_databases"
QUESTIONS = ROOT / "benchmarks/.cache/bird/dev_20251106.json"
NAMESPACE = "bird-one-call-matched-v1:"
ARMS = ("baseline", "manual_one_call", "candidate_one_call")
LOCAL_CAP_USD = 10.0
MAX_AGENT_TURNS = 12
EPISODE_SECONDS = 600
SOURCES = (Path(__file__).resolve(),
    ROOT / "paper/scripts/bird_one_call_matched_candidate.py",
    ROOT / "paper/scripts/bird_one_call_continuation_preflight.py",
    ROOT / "paper/scripts/adaptive_campaign_budget.py",
    ROOT / "paper/scripts/adaptive_pilot.py",
    ROOT / "paper/scripts/adaptive_pilot_runtime.py",
    ROOT / "paper/scripts/adaptive_sql_grader.py",
    ROOT / "paper/scripts/audit_bird_revision.py")


def current_manifest(candidate):
    seal = json.loads((PILOT / "seal.json").read_text())
    catalog = EffectCatalog.from_dict(candidate["catalog"])
    manifest = build_manifest(
        commit=seal["source_hashes"]["paper/scripts/adaptive_pilot.py"],
        model=MODEL, prompt=INSTRUCTIONS, tools=registry()["tools"], policy=POLICY,
        guardrails="read-only immutable SQLite", catalog=catalog,
        entry_contract_version="pooled-bird-database-v1")
    if asdict(manifest) != candidate["manifest"]:
        raise ValueError("candidate manifest differs from current prompt/model/tools/policy")
    return catalog


def freeze():
    if CACHE.exists() or OUT.exists():
        raise ValueError("pilot version already exists; retain every attempt")
    candidate = json.loads(CANDIDATE.read_text())
    preflight = json.loads((PREFLIGHT / "report.json").read_text())
    historical = json.loads((PILOT / "seal.json").read_text())
    current_manifest(candidate)
    if (candidate["artifacts_emitted"] != 0
            or candidate["status"] != "RESEARCH_CANDIDATE_ONLY_NO_CALIBRATION_NO_ADMISSION"
            or preflight["candidate_sha256"] != digest(CANDIDATE)
            or preflight["scheduled"] != 36
            or any(value != 36 for value in preflight["totals"].values())
            or len(historical["tasks"]) != 36):
        raise ValueError("candidate or provider-free gate incomplete")
    if digest(QUESTIONS) != SNAPSHOT_SHA256:
        raise ValueError("corrected BIRD questions drift")
    for db, expected in historical["database_sha256"].items():
        if digest(DBROOT / db / f"{db}.sqlite") != expected:
            raise ValueError("selected database drift")
    if not LEDGER.exists():
        raise ValueError("shared campaign ledger missing; cannot reset")
    orders = list(itertools.permutations(ARMS))
    tasks = [{"question_id": task["question_id"], "db_id": task["db_id"],
              "arm_order": list(orders[index % len(orders)])}
             for index, task in enumerate(historical["tasks"])]
    seal = {"schema": "gac-bird-one-call-matched-pilot-v1",
        "status": "exposed development mechanism/quality-cost pilot; no calibration or GAC admission",
        "tasks": tasks, "arms": ARMS, "scheduled_episodes": len(tasks) * len(ARMS),
        "model": MODEL, "model_mutable_alias": True, "reasoning_effort": "none",
        "instructions": INSTRUCTIONS, "tools": registry()["tools"],
        "max_agent_turns": MAX_AGENT_TURNS, "max_tool_calls": 64,
        "episode_seconds": EPISODE_SECONDS,
        "primary_development_metric": "shape-sensitive unordered set agreement with executable corrected BIRD SQL; all scheduled failures count incorrect",
        "secondary_metrics": ["historical row-shape-blind set agreement", "bag agreement",
            "provider requests", "provider tokens", "tool calls", "fallback", "wall time"],
        "common_input": "Same question, evidence, prompt, SQL tool definitions, model, reasoning setting and limits. Manual and candidate arms share identical synthetic one-call continuation messages when the candidate dispatches.",
        "candidate_admission": "none; research candidate only; no selection-wide or final-answer certificate",
        "candidate_sha256": digest(CANDIDATE),
        "preflight_sha256": digest(PREFLIGHT / "report.json"),
        "historical_pilot_seal_sha256": digest(PILOT / "seal.json"),
        "historical_pilot_report_sha256": digest(PILOT / "report.json"),
        "question_sha256": digest(QUESTIONS),
        "database_sha256": historical["database_sha256"],
        "source_hashes": {str(path.relative_to(ROOT)): digest(path) for path in SOURCES},
        "candidate_source_hashes": candidate["source_hashes"],
        "ledger_before_sha256": digest(LEDGER),
        "campaign_cap_usd": TOTAL_CAP, "local_cap_usd": LOCAL_CAP_USD,
        "ledger_stage": "pilot", "namespace": NAMESPACE,
        "failure_rule": "Every fixed task and arm remains in denominator; no retry/replacement. Interrupted/failed/unstarted outcome is incorrect.",
        "analysis": "paired descriptive development estimates only; no p value, noninferiority, superiority, admission or model-only claim"}
    CACHE.mkdir(parents=True)
    write(CACHE / "seal.json", seal)
    for path in SOURCES:
        destination = CACHE / "sealed_sources" / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())
    print(dumps({"tasks": len(tasks), "episodes": len(tasks) * len(ARMS),
                 "local_cap_usd": LOCAL_CAP_USD}))


def verify():
    seal = json.loads((CACHE / "seal.json").read_text())
    if (digest(CANDIDATE) != seal["candidate_sha256"]
            or digest(PREFLIGHT / "report.json") != seal["preflight_sha256"]
            or digest(PILOT / "seal.json") != seal["historical_pilot_seal_sha256"]
            or digest(PILOT / "report.json") != seal["historical_pilot_report_sha256"]
            or digest(QUESTIONS) != seal["question_sha256"]
            or any(digest(ROOT / name) != expected
                   for name, expected in seal["source_hashes"].items())
            or any(digest(ROOT / name) != expected
                   for name, expected in seal["candidate_source_hashes"].items())
            or any(digest(DBROOT / db / f"{db}.sqlite") != expected
                   for db, expected in seal["database_sha256"].items())):
        raise ValueError("sealed source or input drift")
    current_manifest(json.loads(CANDIDATE.read_text()))
    return seal


def task_text(question):
    return f"Database: {question['db_id']}\nQuestion: {question['question']}\nEvidence: {question.get('evidence') or 'none'}"


def tool_definitions():
    return [{"type": "function", "function": {"name": tool["name"],
        "description": tool["description"], "parameters": tool["input_schema"]}}
        for tool in registry()["tools"]]


def local_budget_check():
    ledger = json.loads(LEDGER.read_text())
    used = sum(row.get("accounted_upper_usd", row["reserved_usd"])
               for row in ledger["requests"] if row["task"].startswith(NAMESPACE))
    if used + 0.25 > LOCAL_CAP_USD:
        raise BudgetExceeded("local exploratory pilot allocation")


def prepare_prefix(question, toolset, arm, candidate):
    if arm == "baseline":
        return [], {"outcome": "baseline", "candidate_admitted": False}
    if arm == "manual_one_call":
        result = toolset.call("list_tables", {})
        return list(synthetic_prefix(result)), {"outcome": "manual_prefix", "candidate_admitted": False}
    if arm != "candidate_one_call":
        raise ValueError("unknown arm")
    spec = candidate["candidate"]
    catalog = EffectCatalog.from_dict(candidate["catalog"])
    guard = HardGuard.from_dict(spec["hard_guard"])
    reasons = guard.evaluate({"database": question["db_id"]}, candidate["manifest"])
    if reasons:
        return [], {"outcome": "fallback_guard", "reasons": reasons[:6], "candidate_admitted": False}
    program = program_from_dict(spec["program"])
    result = run_program(program, {"database": question["db_id"]}, ToolFacade(catalog,
        mode=FacadeMode.LIVE, executor=toolset.call,
        allowed_tools=("list_tables",), max_calls=1))
    if not result.ok:
        return [], {"outcome": "fallback_program", "reason": result.error[:160],
                    "candidate_admitted": False}
    verifier = Verifier.from_dict(spec["verifier"])
    reasons = verifier.verify(result.outputs, result.env, result.provenance,
                              result.effects, len(result.calls))
    if reasons:
        return [], {"outcome": "fallback_verifier", "reasons": reasons[:6],
                    "candidate_admitted": False}
    if result.calls != [("list_tables", {})] or len(result.results) != 1:
        raise ValueError("one-call program diverged")
    return list(synthetic_prefix(result.results[0])), {
        "outcome": "candidate_prefix", "candidate_admitted": False,
        "program_calls": len(result.calls), "verifier_passed": True}


async def agent(question, toolset, client, arm, candidate, trace, row):
    messages = [{"role": "system", "content": INSTRUCTIONS},
                {"role": "user", "content": task_text(question)}]
    prefix, disposition = prepare_prefix(question, toolset, arm, candidate)
    messages.extend(prefix)
    row["prefix_disposition"] = disposition
    row["synthetic_prefix_messages"] = prefix
    tools = tool_definitions()
    for turn in range(MAX_AGENT_TURNS):
        local_budget_check()
        started = time.monotonic()
        response = await client.create(messages=messages, tools=tools,
                                       parallel_tool_calls=False)
        trace.append({"turn": turn, "response": response.model_dump(mode="json"),
                      "wall_seconds": time.monotonic() - started})
        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))
        row["provider_trace"] = trace
        if not message.tool_calls:
            return message.content
        for call in message.tool_calls:
            try:
                arguments = json.loads(call.function.arguments)
                result = toolset.call(call.function.name, arguments)
            except Exception as exc:
                result = {"payload": dumps({"error": type(exc).__name__})}
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": dumps(result)})
    raise RuntimeError("agent turn cap")


def answer_sql(value):
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict) or set(value) != {"sql"} or not isinstance(value["sql"], str):
        raise ValueError("expected JSON object with sql string")
    return value["sql"]


async def run(limit=None):
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    seal = verify()
    candidate = json.loads(CANDIDATE.read_text())
    questions = {question["question_id"]: question for question in read_corrected(QUESTIONS)}
    with (CACHE / "runner.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        started_count = 0
        for task in seal["tasks"]:
            question = questions[task["question_id"]]
            db = DBROOT / task["db_id"] / f"{task['db_id']}.sqlite"
            gold = execute(db, question["SQL"])
            for arm in task["arm_order"]:
                path = CACHE / "episodes" / str(task["question_id"]) / arm / "record.json"
                if path.exists():
                    continue
                if limit is not None and started_count >= limit:
                    return
                row = {"status": "started", "question_id": task["question_id"],
                    "db_id": task["db_id"], "arm": arm,
                    "seal_sha256": digest(CACHE / "seal.json"),
                    "gold_status": gold.status, "execution_correct": False,
                    "shape_set_correct": False, "bag_correct": False,
                    "provider_trace": [], "tool_calls": []}
                write(path, row)
                client = BudgetClient(Ledger(LEDGER), stage="pilot",
                    task=NAMESPACE + str(task["question_id"]), arm=arm)
                toolset = SQLTools(db)
                trace = []
                started = time.monotonic()
                try:
                    if gold.status != "ok":
                        raise RuntimeError("gold unavailable at execution")
                    value = await asyncio.wait_for(
                        agent(question, toolset, client, arm, candidate, trace, row),
                        EPISODE_SECONDS)
                    row["sql"] = answer_sql(value)
                    predicted = execute(db, row["sql"])
                    row.update(status="completed", predicted_status=predicted.status,
                        execution_correct=predicted.status == "ok" and set(gold.rows) == set(predicted.rows),
                        shape_set_correct=compare(gold, predicted, contract="set"),
                        bag_correct=compare(gold, predicted, contract="bag"))
                except Exception as exc:
                    row.update(status="failed", error=type(exc).__name__)
                    if isinstance(exc, BudgetExceeded):
                        row["budget_stop"] = True
                finally:
                    row.update(wall_seconds=time.monotonic() - started,
                               tool_calls=toolset.calls, provider_trace=trace)
                    write(path, row)
                    await client.close()
                started_count += 1
                print(dumps({"arm": arm, "status": row["status"],
                             "shape_set_correct": row["shape_set_correct"],
                             "requests": len(trace), "tool_calls": len(toolset.calls)}), flush=True)
                if row.get("budget_stop"):
                    return


def export():
    seal = verify()
    if OUT.exists():
        raise ValueError("published pilot already exists")
    rows = []
    for task in seal["tasks"]:
        for arm in task["arm_order"]:
            path = CACHE / "episodes" / str(task["question_id"]) / arm / "record.json"
            rows.append(json.loads(path.read_text()) if path.exists()
                        else {"status": "unstarted", "question_id": task["question_id"],
                              "db_id": task["db_id"], "arm": arm,
                              "execution_correct": False, "shape_set_correct": False,
                              "bag_correct": False})
    if any(row["status"] == "started" for row in rows):
        raise ValueError("unfinished attempt; retain before export")
    ledger = json.loads(LEDGER.read_text())
    charges = [row for row in ledger["requests"]
               if row["task"].startswith(NAMESPACE)]
    OUT.mkdir(parents=True)
    write(OUT / "seal.json", seal)
    with (OUT / "raw_evidence.tar.gz").open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w") as archive:
                for path in sorted((CACHE / "episodes").rglob("record.json")):
                    info = archive.gettarinfo(str(path), arcname=str(path.relative_to(CACHE)))
                    info.mtime = 0
                    with path.open("rb") as source:
                        archive.addfile(info, source)
                for path in (CACHE / "seal.json",):
                    info = archive.gettarinfo(str(path), arcname=str(path.relative_to(CACHE)))
                    info.mtime = 0
                    with path.open("rb") as source:
                        archive.addfile(info, source)
    summary = {}
    for arm in ARMS:
        subset = [row for row in rows if row["arm"] == arm]
        arm_charges = [charge for charge in charges if charge["arm"] == arm]
        summary[arm] = {"scheduled": len(subset),
            "completed": sum(row["status"] == "completed" for row in subset),
            "correct": sum(bool(row["shape_set_correct"]) for row in subset),
            "historical_set_correct": sum(bool(row["execution_correct"]) for row in subset),
            "provider_requests": len(arm_charges),
            "tool_calls": sum(len(row.get("tool_calls", [])) for row in subset),
            "accounted_upper_usd": sum(charge.get("accounted_upper_usd", charge["reserved_usd"])
                                      for charge in arm_charges),
            "status_counts": dict(Counter(row["status"] for row in subset))}
    paired = {}
    for comparator in ("manual_one_call", "candidate_one_call"):
        left = {row["question_id"]: row for row in rows if row["arm"] == "baseline"}
        right = {row["question_id"]: row for row in rows if row["arm"] == comparator}
        paired[comparator] = {"comparator_only_correct": sum(
            right[qid]["shape_set_correct"] and not left[qid]["shape_set_correct"] for qid in left),
            "baseline_only_correct": sum(
                left[qid]["shape_set_correct"] and not right[qid]["shape_set_correct"] for qid in left),
            "agreements": sum(bool(left[qid]["shape_set_correct"]) == bool(right[qid]["shape_set_correct"])
                              for qid in left)}
    report = {"schema": "gac-bird-one-call-matched-pilot-report-v1",
        "seal_sha256": digest(OUT / "seal.json"),
        "archive_sha256": digest(OUT / "raw_evidence.tar.gz"),
        "scheduled": len(rows), "summary": summary, "paired": paired,
        "candidate_prefix_count": sum(row.get("prefix_disposition", {}).get("outcome") == "candidate_prefix"
                                      for row in rows),
        "candidate_fallback_count": sum(str(row.get("prefix_disposition", {}).get("outcome", "")).startswith("fallback")
                                        for row in rows),
        "provider_requests": len(charges),
        "charged_upper_usd": sum(charge.get("accounted_upper_usd", charge["reserved_usd"])
                                 for charge in charges),
        "campaign_accounted_upper_usd": ledger["accounted_upper_usd"],
        "remaining_campaign_usd": TOTAL_CAP - ledger["accounted_upper_usd"],
        "ledger_sha256": digest(LEDGER),
        "prior_baseline_discovery_upper_usd": json.loads((PILOT / "report.json").read_text())["summary"]["baseline"]["accounted_upper_usd"],
        "gac_artifacts": 0, "independent_test_groups": 0,
        "rows": [{"question_id": row["question_id"], "db_id": row["db_id"],
                  "arm": row["arm"], "status": row["status"],
                  "shape_set_correct": row["shape_set_correct"],
                  "historical_set_correct": row["execution_correct"],
                  "bag_correct": row["bag_correct"],
                  "prefix_outcome": row.get("prefix_disposition", {}).get("outcome"),
                  "raw_sha256": digest(CACHE / "episodes" / str(row["question_id"]) / row["arm"] / "record.json")
                      if row["status"] != "unstarted" else None}
                 for row in rows],
        "decision": "DEVELOPMENT_MECHANISM_ONLY_NO_ADMISSION_OR_CONFIRMATION"}
    write(OUT / "report.json", report)
    print(dumps({"scheduled": len(rows), "summary": summary,
                 "charged_upper_usd": report["charged_upper_usd"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "run", "export"))
    parser.add_argument("--limit", type=int, default=None,
                        help="maximum newly started episodes; never retry existing records")
    args = parser.parse_args()
    if args.command == "freeze":
        freeze()
    elif args.command == "run":
        asyncio.run(run(args.limit))
    else:
        export()
