"""Provider-free, development-only read-boundary probe on selected task 714.

This is a handwritten route hypothesis and an official-grader integration check.
It neither admits a GAC artifact nor evaluates a model. All runs use an owned,
pinned Reddit clone. The inherited database digest does not cover session files,
CSRF state, server logs, time or arbitrary external effects.
"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import tarfile
import time
from urllib.parse import urlparse

from adaptive_benchmark_screen import ROOT, PINS, check_source, sha
from browser_staging_boundary import Blueprint, IMAGE, Session, request_allowed
from webarena_verified_development import DATA, SOURCE, allowed_url, evaluator, public_input, runtime_versions, snapshot, write

TASK = 714
OUT = ROOT / "paper/results/reddit_ranked_read_feasibility"
LOCAL = ROOT / "benchmarks/.cache/reddit_ranked_read_feasibility/v1"
SELECTION = ROOT / "paper/results/adaptive_comparison_followup/selection.json"
TOP_PATH = "/f/gadgets/top"
MODES = ("empty_negative", "read_only", "blocked_wrong_forum", "blocked_post", "read_then_vote")
SOURCE_PATHS = (Path(__file__), ROOT / "paper/scripts/browser_staging_boundary.py",
    ROOT / "paper/scripts/webarena_verified_development.py", SELECTION)
IMAGE_SOURCE_HASHES = {
    "/var/www/html/config/app_routes/forum.yaml": "7e9ae215135fc467330365dff9941ab19aa767874d96d1a9a8b3f6a97eb583e3",
    "/var/www/html/src/Controller/ForumController.php": "8548c7e151a2f0e6c459e540bde62313204538595adeae13d149101ca2edde99",
    "/var/www/html/src/SubmissionFinder/SubmissionFinder.php": "35f720ea2cceecf85d9f6ad7dcb96285e1f2ff74362c1531bf7c72ca0a47995b",
    "/var/www/html/src/SubmissionFinder/Criteria.php": "77c71869255bff5f7a437fa2891c8e9867a250c650197e7e766279ff1e4252ce",
    "/var/www/html/src/Entity/Submission.php": "d6dcbbf76064ab4d795044baf3460f5b0e911ce932154309330cc7b2e460e071",
}


def selected_task():
    selection = json.loads(SELECTION.read_text())
    if {x["task_id"] for x in selection["selected"]} != {613, 626, 714, 647}:
        raise ValueError("development selection changed")
    rows = [r for r in json.loads(DATA.read_text()) if r["task_id"] == TASK]
    if len(rows) != 1 or rows[0]["sites"] != ["reddit"] or rows[0]["intent_template_id"] != 24:
        raise ValueError("unexpected selected task")
    return rows[0]


def staged_request_allowed(url, base, method, resource_type):
    """Only the audited listing documents and old pinned assets are stageable."""
    if not allowed_url(url, base) or method != "GET":
        return False
    parsed = urlparse(url)
    if resource_type == "document":
        return not parsed.query and not parsed.fragment and parsed.path in {"/", TOP_PATH}
    return request_allowed(url, base, method, resource_type, staged=True)


class DevelopmentBlueprint(Blueprint):
    def validate(self):
        if self.task_id != TASK or self.image != IMAGE or self.principal != "MarvelsGrantMan136:test1234" or self.policy != "webarena-reddit-fresh-blueprint-v1":
            raise ValueError("unvalidated research blueprint")
        row = selected_task()
        fields = {k: row[k] for k in ("task_id", "intent_template_id", "sites", "intent", "start_urls")}
        if self.task_json != json.dumps(fields, sort_keys=True):
            raise ValueError("public task fields changed")
        return fields


class RankedSession(Session):
    async def route(self, route):
        req = route.request
        event = {"method": req.method, "path": urlparse(req.url).path, "resource_type": req.resource_type}
        allowed = (staged_request_allowed(req.url, self.base, req.method, req.resource_type)
                   if self.staged else allowed_url(req.url, self.base))
        if allowed:
            self.events.append(event)
            await route.continue_()
        else:
            self.blocked.append(event)
            await route.abort()


def blueprint():
    row = selected_task()
    fields = {k: row[k] for k in ("task_id", "intent_template_id", "sites", "intent", "start_urls")}
    return DevelopmentBlueprint(TASK, json.dumps(fields, sort_keys=True))


def image_source_hashes():
    import subprocess
    result = subprocess.check_output(["docker", "run", "--rm", "--platform", "linux/amd64",
        "--network", "none", "--read-only", "--entrypoint", "sha256sum", IMAGE,
        *IMAGE_SOURCE_HASHES], text=True, timeout=60)
    observed = {path: digest for digest, path in (line.split(maxsplit=1) for line in result.splitlines())}
    if observed != IMAGE_SOURCE_HASHES:
        raise ValueError("pinned application source mismatch")
    return observed


def freeze():
    check_source(SOURCE, PINS["webarena-verified"])
    selected_task()
    if LOCAL.exists():
        raise ValueError("version exists; retain attempts and create an amendment")
    source = image_source_hashes()
    import subprocess
    image = json.loads(subprocess.check_output(["docker", "image", "inspect", IMAGE]))[0]
    seal = {"schema": "gac-ranked-read-feasibility-v1", "task_id": TASK,
        "scope": "development-only source and runtime controls; no model or GAC admission",
        "image": IMAGE, "image_id": image["Id"], "image_source_hashes": source,
        "source_revision": PINS["webarena-verified"], "data_sha256": sha(DATA),
        "sources": {str(p.relative_to(ROOT)): sha(p) for p in SOURCE_PATHS},
        "runtime_versions": runtime_versions(), "modes": MODES,
        "hypothesis": "GET /f/gadgets/top after authenticated fresh-root setup is a bounded read; voting remains a write after stage promotion.",
        "refusal": "Any source drift, blocked resource, DB change, action error, failed grader control or cleanup failure prevents a positive feasibility decision.",
        "provider_calls": 0}
    LOCAL.mkdir(parents=True)
    write(LOCAL / "seal.json", seal)
    for p in SOURCE_PATHS:
        dest = LOCAL / "source" / p.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(p.read_bytes())
    print("sealed five development-only provider-free controls")


def verify():
    seal = json.loads((LOCAL / "seal.json").read_text())
    check_source(SOURCE, seal["source_revision"])
    if sha(DATA) != seal["data_sha256"] or any(sha(ROOT / rel) != digest for rel, digest in seal["sources"].items()):
        raise ValueError("sealed source drift")
    if runtime_versions() != seal["runtime_versions"]:
        raise ValueError("sealed runtime drift")
    return seal


async def attempt(mode):
    dest = LOCAL / mode
    dest.mkdir(exist_ok=False)
    state = {"mode": mode, "status": "started", "provider_calls": 0,
        "task_id": TASK, "grade": None, "effect": "none"}
    write(dest / "record.json", state)
    session = RankedSession(blueprint(), dest / "session", staged=True)
    started = time.monotonic()
    try:
        await session.start()
        state["entry_observation"] = session.entry_observation
        before = await session.database_digest()
        state["database_before"] = before
        if mode in {"read_only", "blocked_wrong_forum", "blocked_post", "read_then_vote"}:
            if mode == "blocked_wrong_forum":
                try:
                    await session.page.goto(session.base + "/f/books/top", wait_until="domcontentloaded")
                except Exception as exc:
                    state["navigation_error"] = type(exc).__name__
            else:
                response = await session.page.goto(session.base + TOP_PATH, wait_until="networkidle")
                state["navigation_status"] = response.status if response else None
                state["read_observation"] = await snapshot(session.page)
            if mode == "blocked_post":
                state["post_probe"] = await session.page.evaluate("async () => { try { await fetch('/f/gadgets/top', {method: 'POST'}); return 'unexpected success'; } catch (_) { return 'blocked'; } }")
        after = await session.database_digest()
        state["database_after"] = after
        state["read_stage_safe"] = before == after and not any(e["method"] != "GET" for e in session.events)
        if mode in {"empty_negative", "read_only", "blocked_wrong_forum", "blocked_post"}:
            state["read_stage_safe"] &= (not session.blocked if mode in {"empty_negative", "read_only"}
                                        else bool(session.blocked))
        if mode == "read_then_vote" and state["read_stage_safe"] and not session.blocked:
            session.staged = False
            await session.page.get_by_role("button", name="Downvote", exact=True).first.click(timeout=30000)
            await session.page.wait_for_load_state("networkidle", timeout=30000)
            state["effect"] = "vote_attempted_after_promotion"
            state["vote_observation"] = await snapshot(session.page)
        state["blocked"] = list(session.blocked)
        state["requests"] = list(session.events)
        base = session.base
        await session.close()  # flush HAR before the independent official evaluator
        response = {"task_type": "MUTATE", "status": "SUCCESS", "retrieved_data": None, "error_details": None}
        grade = evaluator(base).evaluate_task(task_id=TASK, agent_response=response,
            network_trace=dest / "session/network.har")
        state["grade"] = grade.model_dump(mode="json")
        expected = "success" if mode == "read_then_vote" else "failure"
        state["passed"] = (str(grade.status) == expected and state["read_stage_safe"]
                           and (mode != "read_only" or state.get("navigation_status") == 200)
                           and (mode != "blocked_wrong_forum" or state.get("navigation_error") is not None)
                           and (mode != "blocked_post" or state.get("post_probe") == "blocked")
                           and (mode != "read_then_vote" or (state.get("navigation_status") == 200
                                   and state["effect"] == "vote_attempted_after_promotion")))
        state["status"] = "completed"
    except Exception as exc:
        state.update(status="failed", passed=False, error=type(exc).__name__, detail=str(exc)[:500])
    finally:
        try:
            await session.close()
        except Exception as exc:
            state.update(status="failed", passed=False, cleanup_error=str(exc)[:500])
        state["seconds_including_cleanup"] = time.monotonic() - started
        write(dest / "record.json", state)
    print(json.dumps({k: state.get(k) for k in ("mode", "status", "passed", "effect")}), flush=True)


async def run():
    seal = verify()
    for mode in seal["modes"]:
        if (LOCAL / mode).exists():
            continue
        await attempt(mode)


def export():
    seal = verify()
    records = [json.loads((LOCAL / mode / "record.json").read_text()) for mode in seal["modes"]]
    if any(row["status"] == "started" for row in records):
        raise ValueError("unfinished controls")
    OUT.mkdir(parents=True, exist_ok=False)
    archive = OUT / "raw_evidence.tar.gz"
    members = []
    with tarfile.open(archive, "w:gz") as tar:
        for p in sorted(LOCAL.rglob("*")):
            if not p.is_file():
                continue
            rel = str(p.relative_to(LOCAL))
            tar.add(p, arcname=rel, recursive=False)
            members.append({"path": rel, "sha256": sha(p), "bytes": p.stat().st_size})
        license_path = SOURCE / "LICENSE"
        tar.add(license_path, arcname="upstream/LICENSE", recursive=False)
        members.append({"path": "upstream/LICENSE", "sha256": sha(license_path), "bytes": license_path.stat().st_size})
    write(OUT / "seal.json", seal)
    report = {"schema": "gac-ranked-read-feasibility-report-v1", "scheduled": len(records),
        "passed": sum(bool(row.get("passed")) for row in records),
        "all_passed": all(row.get("passed", False) for row in records),
        "rows": [{k: row.get(k) for k in ("mode", "status", "passed", "effect", "navigation_status", "navigation_error", "seconds_including_cleanup")} for row in records],
        "provider_calls": 0, "gac_artifacts": 0, "independent_task_groups": 0,
        "archive_sha256": sha(archive), "files": members}
    write(OUT / "report.json", report)
    print(json.dumps({k: report[k] for k in ("scheduled", "passed", "all_passed")}))


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
