"""Evidence lineage and isolated executor regression tests; no provider calls."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import tarfile

import pytest

from adaptive_pilot import ROOT, OUT as PILOT, digest
from freeze_adaptive_prefix import OUT, build
from validate_adaptive_sql_programs import recorded_inference


def test_candidate_reproduces_from_all_retained_baselines():
    report = json.loads((OUT / "candidate.json").read_text())
    assert json.loads(json.dumps(build())) == report
    assert report["scheduled"] == report["converted"] == 36
    assert report["incorrect_baselines_retained"] == 10
    assert report["artifacts_emitted"] == 0
    assert report["splits"]["sizes"] == {"train": 27, "dev": 9, "calibration": 0, "test": 0, "shadow": 0}
    candidate, = report["candidates"]
    assert candidate["rejected"] == "no_calibration_groups"
    assert candidate["support_groups"] == 27
    assert candidate["program"]["tools"] == ["list_tables"]
    assert candidate["challenge"]["recorded"]["passed"] == 9
    assert not candidate["challenge"]["perturbations_claimed"]


def test_retained_program_validation_has_complete_denominator_and_hashes():
    report = json.loads((OUT / "executor_sql_validation.json").read_text())
    seal = json.loads((PILOT / "seal.json").read_text())
    assert report["provider_calls"] == 0
    assert report["pilot_archive_sha256"] == digest(PILOT / "raw_evidence.tar.gz")
    assert report["pilot_seal_sha256"] == digest(PILOT / "seal.json")
    for path, sha in report["source_hashes"].items():
        assert digest(ROOT / path) == sha
    assert {r["question_id"] for r in report["rows"]} == {t["question_id"] for t in seal["tasks"]}
    assert len(report["rows"]) == 36
    assert all(r["matches"] and r["native"] == r["reference"] and not r["differences"] for r in report["rows"])
    assert report["summary"] == {"scheduled": 36, "matched": 36, "native_statuses": {"ok": 33, "error": 3}, "missing_inference": 0}
    assert sum(c["tool"] == "ai_eval" for r in report["rows"] for c in r["rpc"]) == 1
    with tarfile.open(PILOT / "raw_evidence.tar.gz", "r:gz") as archive:
        for row in report["rows"]:
            base = f"v2/{row['question_id']}-agent_jit"
            generated = json.load(archive.extractfile(base + "/candidates.json"))
            original = json.load(archive.extractfile(base + "/result.json"))
            assert row["selected_index"] == generated["selected_index"]
            code = generated["candidates"][generated["selected_index"]]["code"]
            assert row["program_sha256"] == hashlib.sha256(code.encode()).hexdigest()
            assert row["original_status"] == original["status"]


@pytest.mark.parametrize("value,expected", [(' {"x": 1} ', {"x": 1}), ("{'x': 1}", {"x": 1}),
    ('[1, 2]', [1, 2]), ('SELECT 1', 'SELECT 1'), ('{not valid', '{not valid')])
def test_canned_inference_preserves_original_parsing(value, expected):
    assert recorded_inference(value) == expected


def test_native_bridge_uses_upstream_semantics_and_stops_on_budget():
    checkout = os.getenv("GAC_UPSTREAM_CHECKOUT")
    if os.getenv("GAC_TEST_PILOT_DOCKER") != "1" or not checkout:
        pytest.skip("opt-in pinned Docker and upstream checkout; no downloads")
    from adaptive_native_runtime import run_native, upstream_runtime
    from adaptive_campaign_budget import BudgetExceeded
    seen = []
    async def dispatch(name, args):
        seen.append((name, args))
        return {"payload": '{"tables": ["t"]}'}
    async def stop(name, args):
        raise BudgetExceeded("synthetic campaign stop")
    with upstream_runtime(Path(checkout)) as package:
        code = 'import json\nx = await list_tables()\nprint("debug")\nresult = json.loads(x.payload)["tables"]'
        native = asyncio.run(run_native(code, dispatch, package, timeout=20))
        reference = asyncio.run(run_native(code, dispatch, package, timeout=20, reference=True))
        assert native == reference == {"status": "ok", "output": ["t"]}
        assert seen == [("list_tables", {}), ("list_tables", {})]
        with pytest.raises(BudgetExceeded):
            asyncio.run(run_native('x = await ai_eval("test")\nresult = x', stop, package, timeout=20))
        with pytest.raises(asyncio.TimeoutError):
            asyncio.run(run_native('while True: pass', dispatch, package, timeout=1))


def test_readiness_excludes_duplicates_of_used_tasks_and_retains_all_reasons():
    from adaptive_prefix_readiness import screen
    questions = [{"question_id": i, "db_id": "db", "question": f"q{i}"} for i in (1, 20, 21, 22, 23)]
    questions[2]["question"] = " Q20 "
    rows = screen(questions, {1, 20}, {22}, {1, 20, 21, 22})
    assert not any(r["eligible"] for r in rows)
    assert rows[0]["exclusions"] == ["historical_prior_use_or_selection", "web_view_exposed"]
    assert rows[2]["exclusions"] == ["normalized_exact_duplicate"]
    assert rows[-1]["exclusions"] == ["gold_execution_unavailable"]
    assert screen(list(reversed(questions)), {1, 20}, {22}, {1, 20, 21, 22}) == rows


def test_readiness_counts_and_calculations_have_not_been_promoted_to_evidence():
    from adaptive_prefix_readiness import power_rows
    report = json.loads((OUT / "readiness.json").read_text())
    assert report["decision"] == "NO_GO_FOR_CONFIRMATORY_EXECUTION"
    assert report["provider_calls"] == 0
    n = sum(r["eligible"] for r in report["rows"])
    assert n == report["eligible_question_count"] == sum(report["eligible_by_database"].values())
    expected = power_rows(n)
    assert len(report["power_sensitivity"]) == len(expected)
    for observed, calculated in zip(report["power_sensitivity"], expected):
        assert observed == pytest.approx(calculated, rel=1e-12, abs=1e-14)
    for path, sha in report["source_hashes"].items():
        if path.startswith("benchmarks/.cache/"):
            continue  # optional local data; read_corrected checks its pinned bytes on rebuild
        assert digest(ROOT / path) == sha
