"""Provider-free mechanism controls, not an admitted GAC evaluation arm.

Only development case 634 is exercised. The fixed handwritten continuation is
an integration control with the official independent HAR grader, not a model.
Every attempted run is retained; changing the harness requires a new directory.
"""
import argparse
import asyncio
import importlib.metadata
import json
from pathlib import Path
import time

from adaptive_benchmark_screen import PINS, ROOT, check_source, sha
from browser_staging_boundary import Blueprint, ResearchBoundary, TOOL, IMAGE, OUT
from guarded_agentic_compaction.grc.dsl import Const, Expr
from guarded_agentic_compaction.grc.program import CallStep, Program, program_from_dict
from webarena_verified_development import DATA, SOURCE, command, evaluator, snapshot, write

CASES = ("handoff", "automatic_candidate_handoff", "verifier_reject", "database_mutation", "blocked_post")


def mechanism_program():
    # Explicit handwritten positive control; automatic discovery is separate.
    return Program(steps=[CallStep("form", TOOL, {"name": Const("Submit")})],
                   outputs={"observation": Expr("form")}, removed_requests=1)


def unadmitted_candidate():
    data = json.loads((OUT / "discovery.json").read_text())
    assert data["artifacts_emitted"] == 0 and len(data["candidates"]) == 1
    assert data["candidates"][0]["rejected"] == "no_dev_groups"
    return program_from_dict(data["candidates"][0]["program"])


async def complete_public_task(session):
    page = session.page
    if page.url == session.base + "/":
        await page.get_by_role("link", name="Submit", exact=True).click()
    await page.get_by_role("textbox", name="Title This field is required.", exact=True).fill("used iphone recommendations?")
    await page.get_by_role("textbox", name="Body", exact=True).fill("Hey, looking for good used iphone under $1000, any suggestions?")
    # The fully loaded pinned UI uses Select2, not its hidden native select.
    await page.get_by_role("combobox", name="Choose one…", exact=True).click()
    await page.get_by_role("option", name="iphone", exact=True).click()
    await page.get_by_role("button", name="Create submission", exact=True).click()
    await page.wait_for_load_state("networkidle")
    return await snapshot(page)


async def run_case(case, output):
    started = time.monotonic()
    output.mkdir(parents=True, exist_ok=False)
    row = {"case": case, "status": "started", "task_id": 634, "provider_calls": 0}
    write(output / "result.json", row)
    session = None
    try:
        async def inject(stage):
            if case == "database_mutation":
                # Trusted failure injection, never task/model-provided SQL.
                await command("docker", "exec", "-u", "postgres", stage.name,
                    "psql", "-v", "ON_ERROR_STOP=1", "postmill", "-c",
                    "CREATE TABLE gac_boundary_probe(value text); INSERT INTO gac_boundary_probe VALUES ('must not escape');")
            if case == "blocked_post":
                # Must be blocked before hitting the backend. Failure is visible
                # in stage_blocked; the discarded request remains in the HAR.
                await stage.page.evaluate("async () => { try { await fetch('/submit', {method:'POST', body:'probe=blocked'}); } catch (_) {} }")
        result = await ResearchBoundary(Blueprint.development(634), output).attempt(
            unadmitted_candidate() if case == "automatic_candidate_handoff" else mechanism_program(),
            verify_output=lambda r: case != "verifier_reject" and bool(r.outputs), inject=inject)
        session = result.session
        row["boundary"] = result.record
        row["session_container"] = session.name
        row["network"] = session.network
        row["initial_observation"] = session.entry_observation
        row["prefix_observations"] = result.observations
        row["baseline_database_digest"] = await session.database_digest() if result.outcome == "baseline" else None
        positive = case in {"handoff", "automatic_candidate_handoff", "verifier_reject"}
        expected = "research_commit" if case in {"handoff", "automatic_candidate_handoff"} else "baseline"
        if result.outcome != expected:
            raise AssertionError(f"expected {expected}, got {result.outcome}: {result.record.get('reason')}")
        if case in {"verifier_reject", "database_mutation"}:
            assert result.record["program_ok"], "isolate the intended rejection, not a different tool failure"
        if case == "verifier_reject":
            assert result.record["database_before"] == result.record["database_after"]
        if positive:
            row["final_observation"] = await complete_public_task(session)
        if case == "database_mutation":
            assert result.record["database_before"] != result.record["database_after"]
            assert row["baseline_database_digest"] == result.record["database_before"]
        if case == "blocked_post":
            assert result.record["stage_blocked"] == [{"method": "POST", "path": "/submit", "resource_type": "fetch"}]
            assert not any(r["method"] == "POST" for r in result.record["stage_requests"])
        row["session_requests"] = list(session.events)  # includes entry and any promoted prefix
        base, har = session.base, session.output / "network.har"
        await session.close()  # flush HAR before independently grading the result
        evaluation = evaluator(base).evaluate_task(task_id=634,
            agent_response={"task_type": "MUTATE", "status": "SUCCESS", "retrieved_data": None, "error_details": None},
            network_trace=har)
        row["evaluation"] = evaluation.model_dump(mode="json")
        expected_grade = "success" if positive else "failure"
        assert str(evaluation.status) == expected_grade
        row.update(status="completed", passed=True)
    except Exception as exc:
        row.update(status="failed", passed=False, error=type(exc).__name__, detail=str(exc))
    finally:
        if session:
            await session.close()
        row["elapsed_seconds_including_setup_cleanup"] = time.monotonic() - started
        write(output / "result.json", row)
    print(json.dumps({k: row.get(k) for k in ("case", "status", "passed", "detail")}), flush=True)
    return row


async def run(output):
    check_source(SOURCE, PINS["webarena-verified"])
    output.mkdir(parents=True, exist_ok=False)
    sources = [Path(__file__).resolve(), ROOT / "paper/scripts/browser_staging_boundary.py"]
    sources += sorted((ROOT / "src/guarded_agentic_compaction").rglob("*.py"))
    ledger = ROOT / "benchmarks/.cache/adaptive_compiler_pilot/ledger.json"
    seal = {"scope": "provider-free mechanism controls on one development task; handwritten continuation; automatic candidate is unadmitted",
        "cases": list(CASES), "program": mechanism_program().to_dict(), "image": IMAGE,
        "source_hashes": {str(p.relative_to(ROOT)): sha(p) for p in sources},
        "upstream_commit": PINS["webarena-verified"], "dataset_sha256": sha(DATA),
        "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
        "ledger_before_sha256": sha(ledger), "provider_calls": 0,
        "candidate_sha256": sha(OUT / "discovery.json"), "candidate_program": unadmitted_candidate().to_dict()}
    for source in sources:
        copy = output / "sealed_sources" / source.relative_to(ROOT)
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_bytes(source.read_bytes())
    write(output / "seal.json", seal)
    rows = []
    for case in CASES:
        rows.append(await run_case(case, output / case))
    owned = await command("docker", "ps", "-a", "--filter", "label=gac.study=browser-prefix", "--format", "{{.Names}}")
    networks = await command("docker", "network", "ls", "--filter", "label=gac.study=browser-prefix", "--format", "{{.Name}}")
    report = {"rows": rows, "all_passed": all(r.get("passed") for r in rows),
        "ledger_unchanged": sha(ledger) == seal["ledger_before_sha256"],
        "remaining_owned_containers": owned.splitlines(), "remaining_owned_networks": networks.splitlines()}
    write(output / "report.json", report)
    if not report["all_passed"] or not report["ledger_unchanged"] or owned or networks:
        raise SystemExit("Controls failed or cleanup incomplete; retain this attempt.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    asyncio.run(run(parser.parse_args().output.resolve()))
