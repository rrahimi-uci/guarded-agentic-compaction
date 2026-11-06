"""Regression tests for contamination, deterministic selection and oracle isolation."""
import copy
import hashlib
import json
from pathlib import Path
import tarfile

import pytest

from adaptive_benchmark_screen import original_web_counts, select_web_development, tau_overlap, PRIOR_WEB_IDS
from webarena_verified_development import allowed_url, bounded_messages, public_input
from appworld_reference_study import select_development
from export_adaptive_development import summarize


def rows():
    return [{"task_id": 10000 + i, "intent_template_id": i // 3,
             "sites": ["reddit"], "intent": "Public task", "start_urls": ["__REDDIT__/"],
             "eval": {"expected": "HIDDEN"}} for i in range(30)]


def test_changed_tau_answers_do_not_make_old_ids_fresh():
    result = tau_overlap([{"id": 1, "evaluation_criteria": {"actions": ["new"]}}], [{"id": "1"}])
    assert result["same_id_prior_exposure"] == 1
    assert result["reward_basis_counts"] == {"COMMUNICATE+DB": 1}
    assert result["unmatched_ids_not_certified_fresh"] == 0


def test_tau_duplicate_ids_fail_closed():
    with pytest.raises(ValueError):
        tau_overlap([{"id": 1}, {"id": "1"}], [])


def test_selection_is_per_template_and_independent_of_order_or_answers():
    data = rows()
    result = select_web_development(data)
    changed = copy.deepcopy(data[::-1])
    for row in changed:
        row["intent"] = "different task text"
        row["eval"] = {"expected": "changed answer"}
    assert select_web_development(changed) == result
    assert len({r["template_id"] for r in result["selected"]}) == 6


def test_prior_exposure_excludes_all_variants():
    data = rows()
    data[0]["task_id"] = next(iter(PRIOR_WEB_IDS))
    result = select_web_development(data)
    assert 0 in result["prior_exposed_templates"]
    assert 0 not in {r["template_id"] for r in result["selected"]}


def test_insufficient_groups_and_duplicate_ids_are_rejected():
    with pytest.raises(ValueError):
        select_web_development(rows()[:6])
    with pytest.raises(ValueError):
        select_web_development(rows() + [rows()[0]])


def test_fuzzy_na_is_not_mistaken_for_deterministic_grading():
    data = [{"intent_template_id": 1, "eval": {"reference_answers": {"fuzzy_match": "N/A"}}},
            {"intent_template_id": 2, "eval": {"reference_answers": {"exact_match": "x"}}}]
    result = original_web_counts(data)
    assert result["without_fuzzy_match_tasks"] == 1
    assert result["fuzzy_match_tasks"] == 1


def test_public_input_never_exposes_expected_values():
    row = rows()[0]
    value = public_input(row, "http://127.0.0.1:1234")
    assert "HIDDEN" not in json.dumps(value)
    assert set(value) == {"task_id", "intent_template_id", "sites", "intent", "start_urls"}


@pytest.mark.parametrize("url", ["file:///etc/passwd", "javascript:alert(1)", "https://example.com",
    "http://127.0.0.1:1235", "http://127.0.0.1:1234@evil.example", "http://user@127.0.0.1:1234",
    "http://127.0.0.1:invalid", None])
def test_browser_cannot_navigate_outside_its_container(url):
    assert not allowed_url(url, "http://127.0.0.1:1234")


def test_local_navigation_and_bounded_context():
    assert allowed_url("http://127.0.0.1:1234/f/books", "http://127.0.0.1:1234")
    messages = [{"role": "user", "content": "task"}] + [{"role": "tool", "content": str(i)} for i in range(6)]
    result = bounded_messages(messages)
    assert result[0] == messages[0]
    assert result[-4:] == messages[-4:]
    assert "omitted" in result[1]["content"]
    assert messages[1]["content"] == "0"  # trace remains untouched


def test_appworld_scenario_variations_do_not_inflate_sample():
    data = {"train": [f"group{i}_{j}" for i in range(12) for j in range(3)]}
    selected = select_development(data)
    assert len({s.rsplit("_", 1)[0] for s in selected}) == 12
    assert select_development({"train": data["train"][::-1]}) == selected
    with pytest.raises(ValueError):
        select_development({"train": ["same_1", "same_2"]})


def test_report_retains_failures_and_rejects_partial_or_duplicate_cohorts():
    seal = {"tasks": [1, 2]}
    attempts = [{"task_id": 1, "status": "completed", "evaluation": {"status": "success"}},
                {"task_id": 2, "status": "failed"}]
    result = summarize(seal, attempts)
    assert result["scheduled"] == result["attempted"] == 2
    assert result["successes"] == 1
    assert result["evaluation_statuses"]["unscored"] == 1
    for bad in (attempts[:1], attempts + [attempts[0]], [attempts[0], {"task_id": 2, "status": "started"}]):
        with pytest.raises(ValueError):
            summarize(seal, bad)


def test_retained_pilot_matches_complete_raw_evidence_and_sealed_sources():
    root = Path(__file__).resolve().parents[2]
    out = root / "paper/results/adaptive_benchmark_screen/webarena_development"
    report = json.loads((out / "report.json").read_text())
    seal = json.loads((out / "seal.json").read_text())
    archive = out / "raw_evidence.tar.gz"
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == report["raw_archive_sha256"]
    for rel, digest in {**seal["source_hashes"], **report["source_hashes"]}.items():
        assert hashlib.sha256((root / rel).read_bytes()).hexdigest() == digest
    with tarfile.open(archive) as tar:
        for row in report["raw_files"]:
            data = tar.extractfile(row["path"]).read()
            assert len(data) == row["bytes"]
            assert hashlib.sha256(data).hexdigest() == row["sha256"]
        attempts = [json.load(tar.extractfile(f"development-v2/{task}/attempt.json")) for task in seal["tasks"]]
        recomputed = summarize(seal, attempts)
        assert all(report["summary"][k] == v for k, v in recomputed.items())
        old = json.load(tar.extractfile("development/controls.json"))
        assert old["all_passed"] is False
        assert {r["status"] for r in old["negative_controls"]} == {"error"}
        controls = json.load(tar.extractfile("development-v2/controls.json"))
        assert controls["all_passed"] is True
        assert controls["positive_control"]["status"] == "success"
        assert len(controls["negative_controls"]) == 2 * len(seal["tasks"])
        assert all(r["status"] == "failure" for r in controls["negative_controls"])
        # Upstream public task fields only; hidden grading data never enters user input.
        for attempt in attempts:
            assert set(attempt["input"]) == {"task_id", "intent_template_id", "sites", "intent", "start_urls"}
    charges = json.loads((out / "ledger_excerpt.json").read_text())["requests"]
    assert len(charges) == report["summary"]["provider_requests"] == 42
    assert sum(r["accounted_upper_usd"] for r in charges) == pytest.approx(report["summary"]["pilot_accounted_upper_usd"])
