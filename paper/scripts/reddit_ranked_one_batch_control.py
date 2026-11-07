"""Provider-free one-batch reference on the exposed task 714.

This is a handwritten upper-bound control for the batched interface, not an
adaptive model result and not an automatically discovered GAC artifact.
"""
import argparse
import asyncio
import json
from pathlib import Path
import tarfile
import time

from adaptive_benchmark_screen import ROOT, PINS, check_source, sha
from browser_staging_boundary import Session
from reddit_ranked_read_feasibility import TASK, IMAGE, DATA, SOURCE, blueprint
from reddit_batched_adaptive_pilot_v2 import batch
from webarena_verified_development import evaluator, runtime_versions, write

OUT = ROOT / "paper/results/reddit_ranked_one_batch_control"
LOCAL = ROOT / "benchmarks/.cache/reddit_ranked_one_batch_control/v1"
BASELINE = ROOT / "paper/results/reddit_batched_adaptive_pilot_v2"
SOURCES = (Path(__file__), ROOT / "paper/scripts/reddit_batched_adaptive_pilot_v2.py",
    ROOT / "paper/scripts/reddit_ranked_read_feasibility.py",
    ROOT / "paper/scripts/browser_staging_boundary.py")


def freeze():
    check_source(SOURCE, PINS["webarena-verified"])
    if LOCAL.exists():
        raise ValueError("control already sealed; retain the attempt")
    baseline = json.loads((BASELINE / "report.json").read_text())
    if baseline["official_status"] != "success" or baseline["all_attempts"] != 1:
        raise ValueError("unexpected batched model baseline")
    seal = {"schema": "gac-reddit-ranked-one-batch-control-v1", "task_id": TASK,
        "scope": "handwritten reference on exposed task; no model; no GAC artifact",
        "source_revision": PINS["webarena-verified"], "data_sha256": sha(DATA),
        "image": IMAGE, "baseline_report_sha256": sha(BASELINE / "report.json"),
        "baseline_archive_sha256": sha(BASELINE / "raw_evidence.tar.gz"),
        "sources": {str(p.relative_to(ROOT)): sha(p) for p in SOURCES},
        "runtime_versions": runtime_versions(),
        "commands": [{"action": "goto", "value": "{base}/f/gadgets/top"},
                     {"action": "click", "role": "button", "name": "Downvote", "index": 0}],
        "provider_calls": 0}
    LOCAL.mkdir(parents=True)
    write(LOCAL / "seal.json", seal)
    for p in SOURCES:
        dest = LOCAL / "source" / p.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(p.read_bytes())
    print("sealed exposed-task one-batch reference")


def verify():
    seal = json.loads((LOCAL / "seal.json").read_text())
    check_source(SOURCE, seal["source_revision"])
    if (sha(DATA) != seal["data_sha256"]
            or sha(BASELINE / "report.json") != seal["baseline_report_sha256"]
            or sha(BASELINE / "raw_evidence.tar.gz") != seal["baseline_archive_sha256"]
            or any(sha(ROOT / p) != digest for p, digest in seal["sources"].items())
            or runtime_versions() != seal["runtime_versions"]):
        raise ValueError("sealed source, data or evidence drift")
    return seal


async def run():
    seal = verify()
    dest = LOCAL / "714"
    dest.mkdir(exist_ok=False)
    state = {"status": "started", "task_id": TASK, "provider_calls": 0,
             "passed": False}
    write(dest / "record.json", state)
    session = Session(blueprint(), dest / "session", staged=False)
    started = time.monotonic()
    try:
        await session.start()
        commands = json.loads(json.dumps(seal["commands"]).replace("{base}", session.base))
        result = await batch(session.page, {"actions": commands}, session.base)
        state["batch"] = result
        state["requests"] = list(session.events)
        state["blocked"] = list(session.blocked)
        base = session.base
        await session.close()
        answer = {"task_type": "MUTATE", "status": "SUCCESS", "retrieved_data": None,
                  "error_details": None}
        grade = evaluator(base).evaluate_task(task_id=TASK, agent_response=answer,
            network_trace=dest / "session/network.har")
        state["grade"] = grade.model_dump(mode="json")
        state["passed"] = (len(result["actions"]) == 2 and not result["stopped_on_error"]
                           and not session.blocked and str(grade.status) == "success")
        state["status"] = "completed"
    except Exception as exc:
        state.update(status="failed", error=type(exc).__name__, detail=str(exc)[:500])
    finally:
        try:
            await session.close()
        except Exception as exc:
            state.update(status="failed", passed=False, cleanup_error=str(exc)[:500])
        state["seconds_including_cleanup"] = time.monotonic() - started
        write(dest / "record.json", state)
    print(json.dumps({k: state.get(k) for k in ("status", "passed", "error", "detail")}))


def export():
    seal = verify()
    record = json.loads((LOCAL / "714/record.json").read_text())
    if record["status"] == "started":
        raise ValueError("control still running")
    OUT.mkdir(parents=True, exist_ok=False)
    archive = OUT / "raw_evidence.tar.gz"
    files = []
    with tarfile.open(archive, "w:gz") as tar:
        for p in sorted(LOCAL.rglob("*")):
            if p.is_file():
                rel = str(p.relative_to(LOCAL))
                tar.add(p, arcname=rel, recursive=False)
                files.append({"path": rel, "sha256": sha(p), "bytes": p.stat().st_size})
        tar.add(SOURCE / "LICENSE", arcname="upstream/LICENSE", recursive=False)
    write(OUT / "seal.json", seal)
    write(OUT / "report.json", {"schema": "gac-reddit-ranked-one-batch-report-v1",
        "task_id": TASK, "status": record["status"], "passed": record["passed"],
        "official_status": record.get("grade", {}).get("status"),
        "actions": len(record.get("batch", {}).get("actions", [])),
        "provider_calls": 0, "gac_artifacts": 0, "independent_task_groups": 0,
        "archive_sha256": sha(archive), "files": files})
    print("exported one-batch reference")


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
