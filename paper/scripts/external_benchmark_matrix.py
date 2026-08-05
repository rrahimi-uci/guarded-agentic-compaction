#!/usr/bin/env python3
"""Build the sealed all-source external benchmark screening matrix.

This stage performs no provider calls.  It binds accessible upstream bytes, normalizes
reference plans where they exist, and reports which benchmarks can or cannot exercise a
read-only trace compiler.  Task prompts, answers, patches, and credentials are never
serialized into the matrix.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_compaction.benchmarking.external import (  # noqa: E402
    ReferenceTask,
    analyze_reference_tasks,
)
from benchmarks.external import (  # noqa: E402
    load_agentbench,
    load_api_bank,
    load_bfcl,
    load_browsecomp,
    load_swebench,
    load_tau2,
    load_toolbench,
    load_toolsandbox,
)


DEFAULT_PREFLIGHT = ROOT / "paper/results/external_benchmarks/source_preflight.json"
DEFAULT_OUTPUT = ROOT / "paper/results/external_benchmarks/reference_analysis.json"
EXECUTION_RESULTS = {
    "api_bank": ROOT / "paper/results/external_benchmarks/api_bank_execution.json",
    "bfcl": ROOT / "paper/results/external_benchmarks/bfcl_gold_execution.json",
    "toolsandbox": ROOT / "paper/results/external_benchmarks/toolsandbox_live.json",
    "tau2": ROOT / "paper/results/external_benchmarks/tau2_live.json",
    "browsecomp": ROOT / "paper/results/external_benchmarks/browsecomp_live.json",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _task_set_digest(tasks: Sequence[ReferenceTask]) -> str:
    payload = json.dumps(
        sorted(task.digest for task in tasks), separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _nestful_record() -> dict[str, Any]:
    source = ROOT / "paper/results/nestful/results.json"
    data = _load_json(source)
    compiler = data["compiler"]
    provenance = compiler["provenance"]
    held_out = compiler["held_out_replay"]
    return {
        "status": "measured",
        "evidence_stage": "executed_provider_free_compiler_benchmark",
        "source_revision": data["source_manifest"]["commit"],
        "substrate": "executable_public_benchmark",
        "tasks": compiler["n_episodes"],
        "independent_groups": compiler["n_episodes"],
        "total_actions": provenance["dependency_slots"],
        "tasks_with_candidate_region": None,
        "complete_observed_traces": compiler["n_episodes"],
        "measured_compiler_results": {
            "candidate_recall": provenance["expected_producer_recall"],
            "unique_resolution_rate": provenance["unique_resolution_rate"],
            "held_out_pass": held_out["test_passed"],
            "held_out_abstain": held_out["test_abstained"],
            "held_out_wrong": held_out["test_wrong"],
            "default_gate_outcome": compiler["exact_gate"]["default_gate_outcome"],
        },
        "source_result": str(source.relative_to(ROOT)),
        "source_result_sha256": _sha256(source),
        "notes": [
            "Existing measured GAC compiler result; unlike screening rows, this executed the compiler.",
        ],
    }


def _screen(
    *,
    name: str,
    record: Mapping[str, Any],
    loader: Callable[[], tuple[ReferenceTask, ...]],
) -> dict[str, Any]:
    if record.get("status") != "available":
        return {
            "status": str(record.get("status") or "unavailable"),
            "evidence_stage": "source_access_only",
            "source_revision": record.get("revision"),
            "reason": record.get("reason"),
            "license": record.get("license"),
            "benchmark_scope": record.get("benchmark_scope"),
            "credential_name": record.get("credential_name"),
            "credential_value_serialized": False,
            "notes": ["No task or compiler metric is imputed for an inaccessible source."],
        }
    tasks = loader()
    analysis = analyze_reference_tasks(tasks)
    result = analysis.as_dict()
    result.update(
        {
            "status": "screened",
            "evidence_stage": "reference_plan_screening",
            "task_set_digest": _task_set_digest(tasks),
            "license": record.get("license"),
            "benchmark_scope": record.get("benchmark_scope"),
            "source_tree": record.get("tree"),
            "source_bytes_sha256": record.get("sha256"),
            "provider_calls": 0,
            "compiler_executions": 0,
            "quality_claim_licensed": False,
            "efficiency_claim_licensed": False,
        }
    )
    if name in {"swe_bench_verified", "browsecomp"}:
        result["notes"].append(
            "The upstream task set contains no reusable agent trajectory; zero candidate coverage is not a compiler failure."
        )
    if name == "toolbench":
        result["notes"].append(
            "Only the ten repository examples are present; this row is an adapter smoke test, not an official ToolBench result."
        )
    if name == "agentbench":
        result["notes"].append(
            "The full official run is infrastructure/data gated (MySQL, Redis, task services, and external Freebase bytes); no score is imputed."
        )
    if name == "swe_bench_verified":
        result["notes"].append(
            "The pinned 500-task dataset is available, but the official x86_64/16-GiB Docker execution contract is not met by this arm64/12.5-GiB Docker host."
        )
    return result


def _attach_execution(name: str, row: dict[str, Any]) -> None:
    """Attach claim-safe aggregates from a separately sealed execution artifact."""

    path = EXECUTION_RESULTS.get(name)
    if path is None or not path.is_file():
        row["execution_status"] = "not_executed"
        return
    payload = _load_json(path)
    evidence = payload.get("evidence") or {}
    attached: dict[str, Any] = {
        "result": str(path.relative_to(ROOT)),
        "result_sha256": _sha256(path),
        "schema": payload.get("schema"),
        "evidence_class": evidence.get("class"),
        "is_real_world_demo": bool(evidence.get("is_real_world_demo", False)),
        "compiler_execution": bool(
            evidence.get(
                "compiler_execution", evidence.get("is_compiler_execution", False)
            )
        ),
    }
    if name == "api_bank":
        compiler = payload["compiler"]
        upstream = payload["upstream_execution"]
        attached.update(
            {
                "tasks": payload["dataset"]["tasks"],
                "candidate_windows": compiler["candidate_windows"],
                "families_synthesized": compiler["held_out_recorded_replay"]["families_synthesized"],
                "held_out_passed": compiler["held_out_recorded_replay"]["test_passed"],
                "held_out_abstained": compiler["held_out_recorded_replay"]["test_abstained"],
                "held_out_wrong": compiler["held_out_recorded_replay"]["test_wrong"],
                "gate_outcome": compiler["exact_gate"]["outcome"],
                "upstream_actions_passed": upstream["action_outcomes"]["passed"],
                "upstream_actions_attempted": upstream["action_outcomes"]["attempted"],
            }
        )
    elif name == "bfcl":
        attached.update(
            {
                "tasks": payload["tasks"],
                "official_checker_valid": payload["official_checker_outcomes"]["valid"],
                "provider_requests": 0,
            }
        )
    elif name == "tau2":
        aggregate = payload["aggregate"]
        attached.update(
            {
                "tasks": aggregate["simulations"],
                "passed": aggregate["passed"],
                "provider_requests": aggregate["provider_requests_with_usage"],
                "total_tokens": aggregate["total_tokens"],
                "reported_cost_usd": aggregate["total_reported_cost_usd"],
            }
        )
    elif name == "browsecomp":
        aggregate = payload["aggregate"]
        attached.update(
            {
                "tasks": payload["selection"]["examples"],
                "correct": aggregate["correct"],
                "provider_requests": aggregate["provider_requests"],
                "total_tokens": aggregate["total_tokens"],
                "web_search_calls": aggregate["web_search_calls"],
            }
        )
    elif name == "toolsandbox":
        aggregate = payload["aggregate"]
        attached.update(
            {
                "tasks": aggregate["scenarios"],
                "milestone_similarity": aggregate["milestone_similarity"],
                "provider_requests": aggregate.get("provider_requests"),
            }
        )
    row["execution_status"] = "executed"
    row["execution"] = attached
    row["provider_calls"] = int(attached.get("provider_requests") or 0)
    row["compiler_executions"] = int(attached["compiler_execution"])


def build_matrix(preflight_path: Path, source_root: Path) -> dict[str, Any]:
    preflight = _load_json(preflight_path)
    sources = preflight["sources"]

    def source_path(name: str) -> Path:
        relative = Path(str(sources[name]["path"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe external source path for {name}")
        return source_root / relative

    loaders: dict[str, Callable[[], tuple[ReferenceTask, ...]]] = {
        "bfcl": lambda: load_bfcl(source_path("bfcl"), str(sources["bfcl"]["revision"])),
        "toolsandbox": lambda: load_toolsandbox(
            source_path("toolsandbox"), str(sources["toolsandbox"]["revision"])
        ),
        "tau2": lambda: load_tau2(source_path("tau2"), str(sources["tau2"]["revision"])),
        "api_bank": lambda: load_api_bank(
            source_path("api_bank"), str(sources["api_bank"]["revision"])
        ),
        "toolbench": lambda: load_toolbench(
            source_path("toolbench"), str(sources["toolbench"]["revision"])
        ),
        "agentbench": lambda: load_agentbench(
            source_path("agentbench"), str(sources["agentbench"]["revision"])
        ),
        "swe_bench_verified": lambda: load_swebench(
            source_path("swe_bench_verified"),
            str(sources["swe_bench_verified"]["revision"]),
        ),
        "browsecomp": lambda: load_browsecomp(
            source_path("browsecomp"), str(sources["browsecomp"]["revision"])
        ),
    }
    benchmarks: dict[str, Any] = {"nestful": _nestful_record()}
    for name in (
        "bfcl",
        "toolsandbox",
        "tau2",
        "api_bank",
        "toolbench",
        "agentbench",
        "gaia",
        "swe_bench_verified",
        "browsecomp",
    ):
        if name == "gaia":
            benchmarks[name] = _screen(
                name=name,
                record=sources[name],
                loader=lambda: (),
            )
        else:
            benchmarks[name] = _screen(
                name=name,
                record=sources[name],
                loader=loaders[name],
            )
        _attach_execution(name, benchmarks[name])
    screened = [item for item in benchmarks.values() if item["status"] == "screened"]
    return {
        "schema": "agent-compaction-external-benchmark-matrix/v1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_preflight": str(preflight_path.relative_to(ROOT)),
        "source_preflight_sha256": _sha256(preflight_path),
        "adapter_sha256": _sha256(ROOT / "benchmarks/external/adapters.py"),
        "reference_ir_sha256": _sha256(
            ROOT / "src/agent_compaction/benchmarking/external.py"
        ),
        "benchmarks": benchmarks,
        "totals": {
            "named_benchmarks": len(benchmarks),
            "measured_compiler_benchmarks": sum(
                item["status"] == "measured" or item.get("compiler_executions", 0) > 0
                for item in benchmarks.values()
            ),
            "executed_external_paths": sum(
                item.get("execution_status") == "executed"
                for item in benchmarks.values()
            ),
            "live_provider_benchmarks": sum(
                any(
                    marker in str(item.get("execution", {}).get("evidence_class", "")).lower()
                    for marker in ("live-provider", "real openai")
                )
                for item in benchmarks.values()
            ),
            "screened_sources": len(screened),
            "gated_sources": sum(item["status"] == "gated" for item in benchmarks.values()),
            "screened_tasks": sum(item["tasks"] for item in screened),
            "screened_reference_actions": sum(item["total_actions"] for item in screened),
            "screened_complete_observed_traces": sum(
                item["complete_observed_traces"] for item in screened
            ),
            "screened_tasks_with_candidate_region": sum(
                item["tasks_with_candidate_region"] for item in screened
            ),
            "provider_calls": sum(
                item.get("provider_calls", 0) for item in benchmarks.values()
            ),
            "provider_call_accounting_complete": False,
        },
        "claim_boundary": {
            "screening_is_compiler_execution": False,
            "screening_is_quality_evaluation": False,
            "simulated_benchmarks_are_real_world_demos": False,
            "task_only_zero_coverage_is_failure": False,
            "gated_source_metrics_imputed": False,
        },
        "secrets_serialized": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = build_matrix(args.preflight.resolve(), args.source_root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["totals"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
