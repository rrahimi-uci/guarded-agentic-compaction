"""Amended positive control: read the vote response body before closing.

The five v1 and one v2 attempts remain intact. The v2 grader passed but its
Playwright response.finished() call left an unhandled target-closure task.
This version repeats only that already exposed positive control.
"""
import argparse
import asyncio
import json
from pathlib import Path
import tarfile
import time
from urllib.parse import urlparse

from adaptive_benchmark_screen import ROOT, PINS, check_source, sha
from reddit_ranked_read_feasibility import TASK, IMAGE, DATA, SOURCE, SELECTION, TOP_PATH, RankedSession, blueprint, image_source_hashes
from webarena_verified_development import evaluator, runtime_versions, snapshot, write

OUT = ROOT / "paper/results/reddit_ranked_read_feasibility_v3"
LOCAL = ROOT / "benchmarks/.cache/reddit_ranked_read_feasibility/v3"
V2 = ROOT / "paper/results/reddit_ranked_read_feasibility_v2"
SOURCE_PATHS = (Path(__file__), ROOT / "paper/scripts/reddit_ranked_read_feasibility.py",
    ROOT / "paper/scripts/reddit_ranked_read_feasibility_v2.py",
    ROOT / "paper/scripts/browser_staging_boundary.py",
    ROOT / "paper/scripts/webarena_verified_development.py", SELECTION)


def vote_response(response):
    return (urlparse(response.url).path.startswith("/sv/")
            and urlparse(response.url).path.endswith(".json")
            and response.request.method == "POST")


def freeze():
    check_source(SOURCE, PINS["webarena-verified"])
    if LOCAL.exists():
        raise ValueError("v3 exists; never overwrite an attempted control")
    prior = json.loads((V2 / "report.json").read_text())
    if prior["scheduled"] != 1 or prior["passed"] != 1 or not prior["all_passed"]:
        raise ValueError("unexpected v2 recorded outcome")
    if not (V2 / "TERMINAL_WARNING.md").exists():
        raise ValueError("missing v2 terminal-warning amendment")
    source = image_source_hashes()
    seal = {"schema": "gac-ranked-read-feasibility-v3", "task_id": TASK,
        "scope": "repeated provider-free positive control; no GAC admission or model",
        "amendment": "v2 got the correct 200 POST and grader success but left an unhandled Playwright response.finished() background task. Read the response body instead. No target IDs, tasks, ranking choice or grader rules changed.",
        "v2_report_sha256": sha(V2 / "report.json"), "v2_archive_sha256": sha(V2 / "raw_evidence.tar.gz"),
        "v2_terminal_warning_sha256": sha(V2 / "TERMINAL_WARNING.md"),
        "image": IMAGE, "image_source_hashes": source,
        "source_revision": PINS["webarena-verified"], "data_sha256": sha(DATA),
        "sources": {str(p.relative_to(ROOT)): sha(p) for p in SOURCE_PATHS},
        "runtime_versions": runtime_versions(), "provider_calls": 0}
    LOCAL.mkdir(parents=True)
    write(LOCAL / "seal.json", seal)
    for path in SOURCE_PATHS:
        dest = LOCAL / "source" / path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(path.read_bytes())
    print("sealed v3 positive-control amendment")


def verify():
    seal = json.loads((LOCAL / "seal.json").read_text())
    check_source(SOURCE, seal["source_revision"])
    if (sha(V2 / "report.json") != seal["v2_report_sha256"]
            or sha(V2 / "raw_evidence.tar.gz") != seal["v2_archive_sha256"]
            or sha(V2 / "TERMINAL_WARNING.md") != seal["v2_terminal_warning_sha256"]
            or sha(DATA) != seal["data_sha256"]
            or any(sha(ROOT / p) != digest for p, digest in seal["sources"].items())
            or runtime_versions() != seal["runtime_versions"]):
        raise ValueError("sealed evidence, source or runtime drift")
    return seal


async def run():
    verify()
    target = LOCAL / "read_then_vote"
    target.mkdir(exist_ok=False)
    record = {"status": "started", "task_id": TASK, "provider_calls": 0,
              "mode": "read_then_vote", "passed": False}
    write(target / "record.json", record)
    session = RankedSession(blueprint(), target / "session", staged=True)
    started = time.monotonic()
    failures = []
    try:
        await session.start()
        session.page.on("requestfailed", lambda req: failures.append({
            "method": req.method, "path": urlparse(req.url).path, "failure": req.failure}))
        before = await session.database_digest()
        response = await session.page.goto(session.base + TOP_PATH, wait_until="networkidle")
        record["navigation_status"] = response.status if response else None
        record["read_observation"] = await snapshot(session.page)
        after = await session.database_digest()
        record["database_before"] = before
        record["database_after"] = after
        record["stage_requests"] = list(session.events)
        record["stage_blocked"] = list(session.blocked)
        if before != after or session.blocked or record["navigation_status"] != 200:
            raise ValueError("read stage did not pass its boundary checks")
        session.staged = False
        async with session.page.expect_response(vote_response, timeout=30000) as response_info:
            await session.page.get_by_role("button", name="Downvote", exact=True).first.click(timeout=30000)
        vote = await response_info.value
        body = await vote.body()
        record["vote_response_bytes"] = len(body)
        await session.page.wait_for_timeout(250)
        record["vote_response_status"] = vote.status
        record["vote_observation"] = await snapshot(session.page)
        record["requests"] = list(session.events)
        record["blocked"] = list(session.blocked)
        record["request_failures"] = list(failures)
        base = session.base
        await session.close()
        answer = {"task_type": "MUTATE", "status": "SUCCESS", "retrieved_data": None, "error_details": None}
        grade = evaluator(base).evaluate_task(task_id=TASK, agent_response=answer,
            network_trace=target / "session/network.har")
        record["grade"] = grade.model_dump(mode="json")
        record["passed"] = (vote.status == 200 and len(body) > 0 and str(grade.status) == "success"
                            and not session.blocked and not failures
                            and any(r["method"] == "POST" for r in record["requests"]))
        record["status"] = "completed"
    except Exception as exc:
        record.update(status="failed", passed=False, error=type(exc).__name__, detail=str(exc)[:500])
    finally:
        try:
            await session.close()
        except Exception as exc:
            record.update(status="failed", passed=False, cleanup_error=str(exc)[:500])
        record["seconds_including_cleanup"] = time.monotonic() - started
        write(target / "record.json", record)
    print(json.dumps({k: record.get(k) for k in ("status", "passed", "vote_response_status", "error", "detail")}))


def export():
    seal = verify()
    record = json.loads((LOCAL / "read_then_vote/record.json").read_text())
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
        license_path = SOURCE / "LICENSE"
        tar.add(license_path, arcname="upstream/LICENSE", recursive=False)
        files.append({"path": "upstream/LICENSE", "sha256": sha(license_path), "bytes": license_path.stat().st_size})
    write(OUT / "seal.json", seal)
    write(OUT / "report.json", {"schema": "gac-ranked-read-feasibility-report-v3",
        "scheduled": 1, "passed": int(record.get("passed", False)), "all_passed": record.get("passed", False),
        "provider_calls": 0, "gac_artifacts": 0, "independent_task_groups": 0,
        "outcome": {k: record.get(k) for k in ("status", "passed", "navigation_status", "vote_response_status", "vote_response_bytes", "seconds_including_cleanup")},
        "archive_sha256": sha(archive), "files": files})
    print(json.dumps({"passed": record.get("passed", False)}))


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
