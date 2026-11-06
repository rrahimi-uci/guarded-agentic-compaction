"""Research-only fresh-episode browser boundary for pinned WebArena Reddit.

This executes candidate programs through GAC's checked interpreter, not an
admitted artifact. No production dispatcher or calibration gate is bypassed.
Fallback starts from an immutable, not-yet-instantiated episode blueprint.
An already running browser or arbitrary website cannot use this boundary.
"""
import asyncio
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
import uuid

from adaptive_benchmark_screen import ROOT
from webarena_verified_development import command, allowed_url, snapshot, public_input, selected_ids, DATA
from guarded_agentic_compaction.schema.effects import EffectCatalog
from guarded_agentic_compaction.runtime.facade import ToolFacade, FacadeMode
from guarded_agentic_compaction.runtime.interp import run_program

IMAGE = "am1n3e/webarena-verified-reddit@sha256:0594908059a03e5f610005689440a95c05e776e734006197c7b1eba12734cb46"
TOOL = "browser.open_submission_form"
POLICY = "webarena-reddit-fresh-blueprint-v1"
AUTH = "MarvelsGrantMan136:test1234"  # upstream's public simulation account
OUT = ROOT / "paper/results/browser_staging_boundary"
ASSET_PREFIXES = ("/build/", "/bundles/")
ASSET_PATHS = ("/js/translations/config.js", "/js/translations/en.js", "/js/routing.js")
ASSET_QUERIES = {
    "/bundles/bazingajstranslation/js/translator.min.js": "aee7f7cac8e57879",
    "/bundles/fosjsrouting/js/router.js": "cee7b3016ac52c0d",
    "/js/translations/config.js": "95e71d595f9f19b9",
    "/js/translations/en.js": "05d2ae8c44538212",
    "/js/routing.js": "8a3c719cedc7be73",
}  # literal cache-busting URLs emitted by the pinned image, not arbitrary queries


def catalog():
    return EffectCatalog.from_dict({"version": 1, "name": POLICY, "tools": {
        TOOL: {"effect": "READ_EXTERNAL", "capabilities": ["speculatable", "replayable"],
               "key": ["name"], "literal_only": ["name"], "resource": "owned-fresh-reddit-clone",
               "notes": "Only literal Submit link to /submit on pinned fresh Reddit root. Session/CSRF writes remain inside disposable clone. No cacheability or cross-episode reuse is declared."},
        "browser.observe": {"effect": "READ_LOCAL", "capabilities": [], "notes": "Not selected as a compiler optimization."},
        "browser.fill": {"effect": "WRITE_REVERSIBLE", "capabilities": []},
        "browser.submit": {"effect": "WRITE_IRREVERSIBLE", "capabilities": []},
        "browser": {"effect": "UNKNOWN", "capabilities": []},
    }})


def request_allowed(url, base, method, resource_type, *, staged):
    if not allowed_url(url, base):
        return False
    if not staged:
        return True
    parsed = urlparse(url)
    if method != "GET" or parsed.fragment or "%" in parsed.path or ".." in parsed.path:
        return False
    if parsed.query and parsed.query != ASSET_QUERIES.get(parsed.path):
        return False
    if resource_type == "document":
        return not parsed.query and parsed.path in {"/", "/submit"}
    if resource_type == "other":
        return not parsed.query and parsed.path == "/build/images/icons.64b6a2fd.svg"
    return (resource_type in {"script", "stylesheet", "image", "font"}
            and (parsed.path in ASSET_PATHS or parsed.path.startswith(ASSET_PREFIXES)))


@dataclass(frozen=True)
class Blueprint:
    """Immutable fresh public task. No pre-existing browser/server state."""
    task_id: int
    task_json: str
    image: str = IMAGE
    principal: str = AUTH
    policy: str = POLICY

    @classmethod
    def development(cls, task_id):
        if task_id not in selected_ids():
            raise ValueError("only the six previously designated development tasks")
        row = next(r for r in json.loads(DATA.read_text()) if r["task_id"] == task_id)
        public = {k: row[k] for k in ("task_id", "intent_template_id", "sites", "intent", "start_urls")}
        return cls(task_id, json.dumps(public, sort_keys=True))

    def validate(self):
        if self.image != IMAGE or self.principal != AUTH or self.policy != POLICY:
            raise ValueError("unvalidated image, principal or policy")
        row = json.loads(self.task_json)
        if (set(row) != {"task_id", "intent_template_id", "sites", "intent", "start_urls"}
                or self.task_id not in selected_ids() or row["task_id"] != self.task_id
                or row["sites"] != ["reddit"] or not isinstance(row["intent"], str)
                or not isinstance(row["start_urls"], list) or len(row["start_urls"]) != 1
                or not isinstance(row["start_urls"][0], str)):
            raise ValueError("invalid blueprint")
        public_input(row, "http://127.0.0.1:12345")
        return row

    @property
    def digest(self):
        return hashlib.sha256(json.dumps(self.__dict__, sort_keys=True).encode()).hexdigest()


class Session:
    """Own the application, browser context, page and HAR as a single lifetime."""
    def __init__(self, blueprint, output, *, staged):
        self.blueprint, self.output, self.staged = blueprint, Path(output), staged
        self.stack = AsyncExitStack()
        self.name = "gac-prefix-" + uuid.uuid4().hex
        self.network = self.name + "-net"
        self.closed = False
        self.events, self.blocked = [], []

    async def start(self):
        from playwright.async_api import async_playwright
        import urllib.request
        self.blueprint.validate()
        self.output.mkdir(parents=True, exist_ok=False)
        try:
            # Creation can succeed in Docker even if the CLI response times out.
            # Register cleanup before issuing either resource-creation command.
            self.stack.push_async_callback(command, "docker", "network", "rm", self.network)
            await command("docker", "network", "create", "--label", "gac.study=browser-prefix", self.network)
            # Register cleanup before creation: timeout/failure must not orphan a process.
            async def remove():
                proc = await asyncio.create_subprocess_exec("docker", "rm", "-f", "-v", self.name,
                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                try:
                    await asyncio.wait_for(proc.wait(), 30)
                except BaseException:
                    if proc.returncode is None:
                        proc.kill()
                    await proc.wait()
                    raise
                if proc.returncode:
                    raise RuntimeError("container cleanup failed; inspect owned resource " + self.name)
            self.stack.push_async_callback(remove)
            await command("docker", "run", "--detach", "--platform", "linux/amd64", "--name", self.name,
                "--label", "gac.study=browser-prefix", "--network", self.network,
                "--security-opt", "no-new-privileges", "--memory", "4g", "--cpus", "2", "--pids-limit", "512",
                "-p", "127.0.0.1::80", self.blueprint.image)
            port = (await command("docker", "port", self.name, "80/tcp")).rsplit(":", 1)[1]
            self.base = "http://127.0.0.1:" + port
            def healthy():
                try:
                    with urllib.request.urlopen(self.base, timeout=2) as response:
                        return response.status == 200
                except OSError:
                    return False
            for _ in range(60):
                if await asyncio.to_thread(healthy):
                    break
                await asyncio.sleep(1)
            else:
                raise RuntimeError("application readiness timeout")
            pw = await self.stack.enter_async_context(async_playwright())
            self.browser = await pw.chromium.launch()
            self.stack.push_async_callback(self.browser.close)
            self.context = await self.browser.new_context(service_workers="block", accept_downloads=False,
                record_har_path=str(self.output / "network.har"), record_har_content="embed",
                extra_http_headers={"X-Postmill-Auto-Login": self.blueprint.principal})
            self.stack.push_async_callback(self.context.close)
            await self.context.route("**/*", self.route)
            # No websocket transport is available to compiled or continuation tools.
            await self.context.route_web_socket("**/*", lambda ws: ws.close())
            self.page = await self.context.new_page()
            self.page.set_default_timeout(10000)
            self.task = public_input(self.blueprint.validate(), self.base)
            await self.page.goto(self.task["start_urls"][0], wait_until="networkidle")
            self.entry_observation = await snapshot(self.page)
            return self
        except BaseException:
            await self.close()
            raise

    async def route(self, route):
        r = route.request
        record = {"method": r.method, "path": urlparse(r.url).path, "resource_type": r.resource_type}
        if request_allowed(r.url, self.base, r.method, r.resource_type, staged=self.staged):
            self.events.append(record)
            await route.continue_()
        else:
            self.blocked.append(record)
            await route.abort()

    async def database_digest(self):
        # Fixed trusted command; neither generated code nor task text enters SQL/shell.
        return (await command("docker", "exec", "-u", "postgres", self.name, "sh", "-c",
            "set -o pipefail; pg_dump --data-only --no-owner --no-privileges postmill | sha256sum"))[0:64]

    async def open_form(self, args):
        if not self.staged or args != {"name": "Submit"}:
            raise ValueError("unsupported read arguments or non-staged execution")
        if self.page.url != self.base + "/" or len(self.context.pages) != 1:
            raise ValueError("not at fresh root boundary")
        link = self.page.get_by_role("link", name="Submit", exact=True)
        if await link.count() != 1 or await link.evaluate("e => e.tagName") != "A":
            raise ValueError("missing or ambiguous Submit anchor")
        if await link.get_attribute("href") != "/submit":
            raise ValueError("unexpected Submit destination")
        if self.blocked:
            raise ValueError("entry network policy violation")
        await link.click()
        await self.page.wait_for_load_state("networkidle")
        if not await self.verify_ready():
            raise ValueError("network policy violation or form postcondition failed")
        return await snapshot(self.page)

    async def verify_ready(self):
        heading_count = await self.page.get_by_role("heading", name="Create submission", exact=True).count()
        return (heading_count == 1 and not self.blocked and len(self.context.pages) == 1
                and self.page.url == self.base + "/submit")

    async def close(self):
        if not self.closed:
            self.closed = True
            await self.stack.aclose()


@dataclass
class BoundaryResult:
    outcome: str
    session: Session
    record: dict
    observations: list = field(default_factory=list)


class ResearchBoundary:
    """One use only. Returning research_commit does not authorize live GAC admission."""
    def __init__(self, blueprint, output, session_factory=Session):
        self.blueprint, self.output, self.session_factory = blueprint, Path(output), session_factory
        self.used = False

    async def attempt(self, program, *, verify_output, inject=None):
        if self.used:
            raise RuntimeError("boundary is one-shot; no retry after interaction")
        self.used = True
        row = self.blueprint.validate()
        record = {"scope": "research_mechanism_only", "blueprint_sha256": self.blueprint.digest,
                  "provider_calls": 0, "stage_requests": [], "stage_blocked": []}
        stage = None
        reason = ""
        try:
            if row["start_urls"] != ["__REDDIT__"]:
                raise ValueError("unsupported entry path")
            if program is None:
                raise ValueError("no admitted artifact or research candidate")
            stage = await self.session_factory(self.blueprint, self.output / "stage", staged=True).start()
            before = await stage.database_digest()
            if inject:
                await inject(stage)  # trusted fault-injection hook, never model supplied
            loop = asyncio.get_running_loop()
            async def bounded_read(args):
                return await asyncio.wait_for(stage.open_form(args), 30)
            def execute(tool, args):
                if tool != TOOL:
                    raise ValueError("undeclared browser tool")
                # Timeout lives on the event loop and waits for cancellation.
                # A timed-out thread must never leave browser work running.
                return asyncio.run_coroutine_threadsafe(bounded_read(args), loop).result()
            facade = ToolFacade(catalog=catalog(), mode=FacadeMode.SANDBOX, executor=execute,
                allowed_tools=(TOOL,), max_calls=1)
            worker = asyncio.create_task(asyncio.to_thread(run_program, program, {"site": "reddit"}, facade))
            try:
                result = await asyncio.shield(worker)
            except asyncio.CancelledError:
                # Drain the bounded interpreter before destroying its session.
                # Cancellation never creates a fresh baseline implicitly.
                await worker
                raise
            after = await stage.database_digest()
            record.update(database_before=before, database_after=after, program_ok=result.ok,
                          program_error=result.error, calls=result.calls)
            if (not result.ok or result.calls != [(TOOL, {"name": "Submit"})]
                    or before != after or not verify_output(result) or not await stage.verify_ready()):
                raise ValueError("program, database or output verification failed")
            # Promote the existing session; do not replay navigation, reload the
            # page, discard its CSRF token, or reconstruct a detached DOM.
            record.update(stage_requests=list(stage.events), stage_blocked=list(stage.blocked),
                          outcome="research_commit", state_handoff="same application, context and page")
            stage.staged = False
            return BoundaryResult("research_commit", stage, record, result.results)
        except asyncio.CancelledError:
            if stage:
                await stage.close()
            raise
        except Exception as exc:
            reason = str(exc)
            if stage:
                record.update(stage_requests=list(stage.events), stage_blocked=list(stage.blocked))
                await stage.close()  # cleanup failure propagates; cannot claim clean fallback
            record.update(outcome="baseline", reason=reason, discarded_stage=stage is not None,
                          state_handoff="new session from immutable fresh blueprint")
            baseline = await self.session_factory(self.blueprint, self.output / "baseline", staged=False).start()
            return BoundaryResult("baseline", baseline, record)
