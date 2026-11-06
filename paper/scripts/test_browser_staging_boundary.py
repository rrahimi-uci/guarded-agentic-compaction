"""Failure-path tests; live container controls are retained separately."""
import asyncio
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tarfile
import sys
from types import ModuleType

import pytest

from browser_staging_boundary import Blueprint, ResearchBoundary, Session, TOOL, request_allowed
from guarded_agentic_compaction.grc.dsl import Const, Expr
from guarded_agentic_compaction.grc.program import CallStep, Program


def blueprint():
    return Blueprint(634, json.dumps({"task_id": 634, "intent_template_id": 1,
        "sites": ["reddit"], "intent": "Public test task", "start_urls": ["__REDDIT__"]}))


def program(tool=TOOL):
    return Program(steps=[CallStep("form", tool, {"name": Const("Submit")})],
                   outputs={"observation": Expr("form")}, removed_requests=1)


BASE = "http://127.0.0.1:12345"


@pytest.mark.parametrize("path,method,kind", [
    ("/submit", "POST", "document"), ("/", "DELETE", "fetch"),
    ("/submit?write=1", "GET", "document"), ("/logout", "GET", "document"),
    ("/submit/iphone", "GET", "document"), ("/%73ubmit", "GET", "document"),
    ("/build/../logout", "GET", "script"), ("/submit", "GET", "fetch"),
    ("/build/test.js", "POST", "script"), ("/build/test.js", "GET", "document"),
])
def test_staged_network_blocks_effects_and_unreviewed_routes(path, method, kind):
    assert not request_allowed(BASE + path, BASE, method, kind, staged=True)


def test_continuation_can_write_only_to_owned_origin():
    assert request_allowed(BASE + "/submit", BASE, "POST", "document", staged=False)
    for staged in (True, False):
        assert not request_allowed("https://example.com/", BASE, "GET", "document", staged=staged)
        assert not request_allowed("http://127.0.0.1:12346/", BASE, "GET", "document", staged=staged)
    assert request_allowed(BASE + "/submit", BASE, "GET", "document", staged=True)
    assert request_allowed(BASE + "/build/app.js", BASE, "GET", "script", staged=True)
    assert request_allowed(BASE + "/js/routing.js?8a3c719cedc7be73", BASE, "GET", "script", staged=True)
    assert not request_allowed(BASE + "/js/routing.js?other", BASE, "GET", "script", staged=True)
    assert request_allowed(BASE + "/build/images/icons.64b6a2fd.svg", BASE, "GET", "other", staged=True)
    assert not request_allowed(BASE + "/submit", BASE, "GET", "other", staged=True)


def test_hidden_grader_and_unvalidated_runtime_are_rejected():
    bp = blueprint()
    row = bp.validate()
    row["eval"] = {"expected": "secret"}
    for bad in (replace(bp, task_json=json.dumps(row)), replace(bp, image="latest"),
                replace(bp, principal="other"), replace(bp, policy="other")):
        with pytest.raises(ValueError):
            bad.validate()


def test_network_created_before_cli_timeout_is_still_cleaned(tmp_path, monkeypatch):
    import browser_staging_boundary as module
    api = ModuleType("playwright.async_api")
    api.async_playwright = lambda: None
    monkeypatch.setitem(sys.modules, "playwright.async_api", api)
    calls = []
    async def fake_command(*args, **kwargs):
        calls.append(args)
        if args[:3] == ("docker", "network", "create"):
            raise TimeoutError("Docker accepted creation but CLI response was lost")
        assert args[:3] == ("docker", "network", "rm")
        return "removed"
    monkeypatch.setattr(module, "command", fake_command)
    session = Session(blueprint(), tmp_path / "stage", staged=True)
    with pytest.raises(TimeoutError):
        asyncio.run(session.start())
    assert len(calls) == 2 and calls[0][-1] == calls[1][-1] == session.network
    assert session.closed


class FakeSession:
    instances = []
    mutation = False
    fail_cleanup = False
    pause = None
    late_violation = False

    def __init__(self, bp, output, *, staged):
        self.bp, self.output, self.staged = bp, output, staged
        self.closed, self.reads, self.digests = False, 0, 0
        self.events, self.blocked = [], []
        self.instances.append(self)

    async def start(self):
        # An older staged resource must be gone before fallback starts.
        if not self.staged:
            assert all(s.closed for s in self.instances[:-1])
        return self

    async def database_digest(self):
        self.digests += 1
        if self.late_violation and self.digests > 1:
            self.blocked.append({"method": "POST"})
        return "changed" if self.mutation and self.digests > 1 else "original"

    async def verify_ready(self):
        return not self.blocked

    async def open_form(self, args):
        self.reads += 1
        self.events.append({"method": "GET", "path": "/submit"})
        if self.pause:
            await self.pause.wait()
        assert not self.closed
        return {"url": BASE + "/submit", "page": "Create submission"}

    async def close(self):
        if self.fail_cleanup:
            raise RuntimeError("cleanup failed")
        self.closed = True


@pytest.fixture(autouse=True)
def reset_fake():
    FakeSession.instances = []
    FakeSession.mutation = FakeSession.fail_cleanup = False
    FakeSession.pause = None
    FakeSession.late_violation = False


def test_commit_promotes_same_session_and_observation_without_replay(tmp_path):
    async def check():
        b = ResearchBoundary(blueprint(), tmp_path, FakeSession)
        result = await b.attempt(program(), verify_output=lambda r: bool(r.outputs))
        assert result.outcome == "research_commit"
        assert result.session is FakeSession.instances[0]
        assert result.session.reads == 1 and not result.session.staged
        assert result.observations[0]["url"] == BASE + "/submit"
        assert result.record["provider_calls"] == 0
        with pytest.raises(RuntimeError, match="one-shot"):
            await b.attempt(program(), verify_output=lambda r: True)
    asyncio.run(check())


@pytest.mark.parametrize("failure", ["verifier", "mutation", "write_tool", "unknown_tool", "absent", "empty", "over_budget", "late_violation"])
def test_failures_discard_stage_before_fresh_baseline_and_retain_requests(tmp_path, failure):
    async def check():
        FakeSession.mutation = failure == "mutation"
        FakeSession.late_violation = failure == "late_violation"
        p = None if failure == "absent" else program({"write_tool": "browser.submit",
            "unknown_tool": "browser"}.get(failure, TOOL))
        if failure == "empty":
            p = Program()
        if failure == "over_budget":
            p.steps.append(CallStep("second", TOOL, {"name": Const("Submit")}))
        result = await ResearchBoundary(blueprint(), tmp_path, FakeSession).attempt(
            p, verify_output=lambda r: failure != "verifier")
        assert result.outcome == "baseline" and not result.session.staged
        assert result.session.bp.digest == blueprint().digest
        if failure != "absent":
            stage = FakeSession.instances[0]
            assert stage.closed and result.session is not stage
            assert stage.reads == (0 if failure in {"write_tool", "unknown_tool", "empty"} else 1)
            assert result.record["stage_requests"] == stage.events
        else:
            assert len(FakeSession.instances) == 1
    asyncio.run(check())


def test_cleanup_failure_is_incident_not_clean_fallback(tmp_path):
    async def check():
        FakeSession.fail_cleanup = True
        with pytest.raises(RuntimeError, match="cleanup failed"):
            await ResearchBoundary(blueprint(), tmp_path, FakeSession).attempt(program(), verify_output=lambda r: False)
        assert len(FakeSession.instances) == 1
    asyncio.run(check())


def test_cancellation_drains_browser_operation_and_does_not_start_baseline(tmp_path):
    async def check():
        FakeSession.pause = asyncio.Event()
        task = asyncio.create_task(ResearchBoundary(blueprint(), tmp_path, FakeSession).attempt(
            program(), verify_output=lambda r: True))
        while not FakeSession.instances or not FakeSession.instances[0].reads:
            await asyncio.sleep(0.001)
        task.cancel()
        await asyncio.sleep(0)
        assert not FakeSession.instances[0].closed
        FakeSession.pause.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert len(FakeSession.instances) == 1 and FakeSession.instances[0].closed
    asyncio.run(check())


@pytest.mark.parametrize("failure", ["ambiguous", "tag", "destination", "entry_policy", "missing_heading"])
def test_actual_tool_checks_structure_and_destination_before_promotion(tmp_path, failure):
    class Locator:
        def __init__(self, heading=False):
            self.heading = heading
        async def count(self):
            return 0 if self.heading and failure == "missing_heading" else 2 if not self.heading and failure == "ambiguous" else 1
        async def evaluate(self, source):
            return "BUTTON" if failure == "tag" else "A"
        async def get_attribute(self, name):
            return "/logout" if failure == "destination" else "/submit"
        async def click(self):
            page.clicks += 1
            page.url = BASE + "/submit"
    class Page:
        url, clicks = BASE + "/", 0
        def get_by_role(self, role, **kwargs):
            return Locator(role == "heading")
        async def wait_for_load_state(self, state):
            pass
    page = Page()
    session = Session(blueprint(), tmp_path, staged=True)
    session.base, session.page = BASE, page
    session.context = type("Context", (), {"pages": [page]})()
    if failure == "entry_policy":
        session.blocked.append({"method": "POST"})
    with pytest.raises(ValueError):
        asyncio.run(session.open_form({"name": "Submit"}))
    assert page.clicks == (1 if failure == "missing_heading" else 0)


def test_discovery_retains_every_prior_attempt_and_does_not_admit():
    from browser_prefix_discovery import build
    report = build()
    assert report["scheduled"] == report["converted"] == 6
    assert report["historical_requests"] == 42
    assert report["historical_actions"] == 36
    assert report["historical_action_errors_retained"] == 6
    assert report["typed_prefix_tasks"] == [634, 600, 622, 643]
    assert report["artifacts_emitted"] == 0
    assert report["candidates"][0]["rejected"] == "no_dev_groups"


def test_retained_controls_include_setup_failures_and_match_sealed_sources():
    root = Path(__file__).resolve().parents[2]
    output = root / "paper/results/browser_staging_boundary"
    report = json.loads((output / "report.json").read_text())
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest(output / "raw_evidence.tar.gz") == report["raw_archive_sha256"]
    assert digest(output / "discovery.json") == report["discovery_sha256"]
    assert digest(root / "paper/scripts/export_browser_boundary.py") == report["export_source_sha256"]
    assert report["provider_calls"] == report["new_api_spend_usd"] == 0
    assert [r["all_passed"] for r in report["attempts"]] == [False, False, True, True, True]
    assert all(r["ledger_unchanged"] for r in report["attempts"])
    assert all(not r["remaining_owned_containers"] and not r["remaining_owned_networks"] for r in report["attempts"])
    with tarfile.open(output / "raw_evidence.tar.gz") as tar:
        expected_names = [f["path"] for f in report["raw_files"]]
        assert sorted(tar.getnames()) == sorted(expected_names)
        for item in report["raw_files"]:
            content = tar.extractfile(item["path"]).read()
            assert len(content) == item["bytes"]
            assert hashlib.sha256(content).hexdigest() == item["sha256"]
        for attempt in report["attempts"]:
            name = attempt["name"]
            seal = json.load(tar.extractfile(name + "/seal.json"))
            raw = json.load(tar.extractfile(name + "/report.json"))
            assert len(raw["rows"]) == len(seal["cases"])
            for rel, expected in seal["source_hashes"].items():
                assert hashlib.sha256(tar.extractfile(name + "/sealed_sources/" + rel).read()).hexdigest() == expected
            if name == report["final_attempt"]:
                assert raw == report["final_controls"]
                assert all(digest(root / rel) == expected for rel, expected in seal["source_hashes"].items())
        rows = {r["case"]: r for r in report["final_controls"]["rows"]}
        for name in ("handoff", "automatic_candidate_handoff", "verifier_reject"):
            assert rows[name]["evaluation"]["status"] == "success"
            boundary = rows[name]["boundary"]
            assert boundary["program_ok"] and boundary["database_before"] == boundary["database_after"]
        mutation = rows["database_mutation"]
        assert mutation["evaluation"]["status"] == "failure"
        assert mutation["boundary"]["program_ok"]
        assert mutation["boundary"]["database_before"] != mutation["boundary"]["database_after"]
        assert mutation["baseline_database_digest"] == mutation["boundary"]["database_before"]
        blocked = rows["blocked_post"]
        assert blocked["evaluation"]["status"] == "failure"
        assert blocked["boundary"]["stage_blocked"] == [{"method": "POST", "path": "/submit", "resource_type": "fetch"}]
        assert all(r["method"] == "GET" for r in blocked["boundary"]["stage_requests"])
