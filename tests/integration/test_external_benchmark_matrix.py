from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for item in value.values() for key in _all_keys(item)}
    if isinstance(value, list):
        return {key for item in value for key in _all_keys(item)}
    return set()


def test_external_benchmark_matrix_covers_every_named_source() -> None:
    matrix = json.loads(
        (ROOT / "paper/results/external_benchmarks/reference_analysis.json").read_text()
    )
    assert set(matrix["benchmarks"]) == {
        "nestful",
        "bfcl",
        "toolsandbox",
        "tau2",
        "api_bank",
        "toolbench",
        "agentbench",
        "gaia",
        "swe_bench_verified",
        "browsecomp",
    }
    assert matrix["totals"] == {
        "named_benchmarks": 10,
        "measured_compiler_benchmarks": 2,
        "executed_external_paths": 5,
        "live_provider_benchmarks": 3,
        "screened_sources": 8,
        "gated_sources": 1,
        "screened_tasks": 5419,
        "screened_reference_actions": 17836,
        "screened_complete_observed_traces": 212,
        "screened_tasks_with_candidate_region": 419,
        "provider_calls": 77,
        "provider_call_accounting_complete": False,
    }
    assert matrix["benchmarks"]["gaia"]["status"] == "gated"
    assert matrix["benchmarks"]["toolbench"]["quality_claim_licensed"] is False
    assert matrix["benchmarks"]["api_bank"]["execution"]["gate_outcome"] == "RETIRE"
    assert matrix["benchmarks"]["api_bank"]["execution"]["held_out_wrong"] == 0
    assert matrix["benchmarks"]["tau2"]["execution"]["passed"] == 0
    assert matrix["benchmarks"]["browsecomp"]["execution"]["correct"] == 1
    assert matrix["benchmarks"]["toolsandbox"]["execution"]["is_real_world_demo"] is False
    assert matrix["claim_boundary"]["screening_is_compiler_execution"] is False
    assert matrix["claim_boundary"]["simulated_benchmarks_are_real_world_demos"] is False


def test_external_source_preflight_contains_no_local_paths_or_secrets() -> None:
    path = ROOT / "paper/results/external_benchmarks/source_preflight.json"
    text = path.read_text()
    report = json.loads(text)
    assert report["counts"] == {"available": 10, "gated": 1, "failed": 0}
    assert report["secrets_serialized"] is False
    assert report["source_root_serialized"] is False
    assert "/Users/" not in text
    assert "/private/tmp" not in text
    assert not re.search(r'\bsk-[A-Za-z0-9_-]{20,}\b', text)
    assert "hf_" not in text


def test_external_execution_artifacts_are_bounded_and_redacted() -> None:
    paths = [
        ROOT / "paper/results/external_benchmarks/api_bank_execution.json",
        ROOT / "paper/results/external_benchmarks/bfcl_gold_execution.json",
        ROOT / "paper/results/external_benchmarks/toolsandbox_live.json",
        ROOT / "paper/results/external_benchmarks/tau2_live.json",
        ROOT / "paper/results/external_benchmarks/browsecomp_live.json",
    ]
    payloads = [json.loads(path.read_text()) for path in paths]
    for path, payload in zip(paths, payloads):
        text = path.read_text()
        assert payload["schema"] in {
            "agent-compaction-external-execution/v1",
            "agent-compaction-external-live-evaluation/v1",
        }
        assert payload["evidence"]["is_real_world_demo"] is False
        assert not ({"question", "answer", "content", "arguments", "response_text"} & _all_keys(payload))
        assert "/Users/" not in text
        assert "/private/tmp" not in text
        assert not re.search(r'\bsk-[A-Za-z0-9_-]{20,}\b', text)
        assert "hf_" not in text

    api, bfcl, sandbox, tau, browse = payloads
    assert api["evidence"]["compiler_execution"] is True
    assert api["upstream_execution"]["action_outcomes"] == {
        "attempted": 389,
        "dependency_unavailable": 5,
        "execution_error:KeyError": 9,
        "mismatch": 37,
        "passed": 338,
    }
    assert bfcl["official_checker_valid_rate"] == 1.0
    assert sandbox["aggregate"]["milestone_similarity"] > 0.98
    assert sandbox["aggregate"]["provider_requests"] is None
    assert tau["aggregate"]["simulations"] == 4
    assert tau["aggregate"]["pass_rate"] == 0.0
    assert browse["aggregate"]["correct"] == 1
    assert browse["aggregate"]["web_search_calls"] == 28
