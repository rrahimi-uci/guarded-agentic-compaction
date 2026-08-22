#!/usr/bin/env python3
"""Prospective gate-frontier study: baseline vs. learned gate vs. support-only gate.

Implements the design pre-registered in
paper/supplementary/prospective-gate-frontier-protocol.md by extending
paper/scripts/github_multirepo_pr_outcome_core.py's already-tested, already-executed
cross-repository ``pr_outcome_core`` harness rather than duplicating it: the same five
repositories, the same discovery/test selection code, the same effect catalog, tools,
grading, and frozen-candidate compilation. Two things are new relative to the core
study, and nothing else is:

1. A second, independent ``compile_grc`` pass per repository with ``alpha=1.0`` instead
   of ``0.05``. ``alpha=1.0`` is ``calibrate_gate``'s own "published support-only
   research ablation" (see the comment above the ``alpha == 1.0`` branch in
   ``src/guarded_agentic_compaction/grc/calibrate.py``): it keeps every stage of the
   pipeline -- mining, synthesis, challenge, freezing -- identical, and removes only the
   Clopper-Pearson risk budget, producing an accept-all-once-supported gate. That is
   this repository's own precedented operationalization of "dispatch on recurrence
   alone", not a new statistical mechanism invented for this study. Because frozen
   selection ranks and stops on train/dev evidence, which does not depend on alpha, the
   same candidate that reaches calibration in the learned-gate pass reaches calibration
   here too; only whether, and at what coverage, it is admitted can differ.
2. A coverage-level curve read back out of the admitted learned-gate artifact's own
   calibration sweep. ``calibrate_gate`` already computes one row -- accepted count,
   violation count, exact Clopper-Pearson upper bound, coverage -- for every point on
   the frozen eleven-point grid before it ever selects a threshold, and records the full
   list in ``Gate.notes`` as ``"...; grid rows: [...]"``. Nothing here reruns or
   re-derives that sweep; it only parses back out what compilation already computed, so
   the paper can report how many distinct nonzero coverage levels the learned gate
   reaches on this cohort, per the protocol's coverage-levels requirement.

Selection targets exactly the design committed in the protocol: discovery_cases=116
(16 train + 8 dev + 92 calibration, the exact gate's own minimum), test_cases_per_repo=60
across the same five repositories used by ``github_multirepo_pr_outcome_core.py``
(huggingface/datasets, pandas-dev/pandas, psf/requests, streamlit/streamlit,
pytorch/pytorch), which is the unique configuration -- verified provider-free before
this file was written -- at which all five repositories stay selectable and the pooled
held-out cohort is exactly 300 cases, matching the protocol's >=300-pair, >=3-domain
requirement with no repository excluded to reach it.

No live provider call happens unless ``run`` is invoked without ``--preflight-only`` and
``--approved-spend-usd`` is passed with a positive value, matching every other live study
in this repository's discipline for gating real spend behind explicit authorization.
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import hashlib
import json
import os
import platform
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import version
from itertools import permutations
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import github_multirepo_pr_outcome_core as core  # noqa: E402
from guarded_agentic_compaction.evaluation.splits import Splits  # noqa: E402
from guarded_agentic_compaction.grc.compile import GrcConfig, compile_grc  # noqa: E402
from guarded_agentic_compaction.registry.store import Registry  # noqa: E402
from guarded_agentic_compaction.schema.artifacts import Lifecycle  # noqa: E402


OUT_ROOT = ROOT / "paper" / "results" / "github_multirepo_gate_frontier"
CONDITIONS = ("baseline", "learned_gate", "support_only")
DISCOVERY_CASES = core.DISCOVERY_CASES
TEST_CASES_PER_REPO = 60
MINIMUM_POOLED_TEST_CASES = 300
MINIMUM_COMPLETE_REPOS = 3


def _repo_result_dir(repository: str) -> Path:
    return OUT_ROOT / "repos" / core._repo_slug(repository)


def _checkpoint_summary(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {"schema": payload.get("schema"), "results": len(payload.get("results", ()))}


def compile_support_only_artifact(
    repository: str,
    discovery: Sequence[Any],
    *,
    catalog: Any,
    source_manifest: Any,
    continuation_manifest: Any,
    seed: int,
) -> tuple[Registry | None, dict[str, Any]]:
    """Mirror ``core.compile_artifact`` exactly except for ``alpha``.

    Same discovery episodes, same train/dev/calibration split (identical hash, identical
    seed), same mining/synthesis/freezing configuration -- only ``alpha`` changes, from
    ``0.05`` to ``1.0``. Unlike ``core.compile_artifact``, this returns ``(None, ...)``
    with a ``"retired"`` status instead of raising when nothing is admitted: a retirement
    here is a legitimate, reportable outcome for a comparator arm, not a fail-closed
    precondition failure.
    """
    eligible = [
        run for run in discovery
        if run.condition == "discovery" and run.quality["overall"]
    ]
    needed = core.TRAIN_CASES + core.DEV_CASES + core.CALIBRATION_CASES
    if len(eligible) < needed:
        raise RuntimeError(f"only {len(eligible)} exact discovery traces; need {needed}")
    selected = sorted(
        eligible,
        key=lambda run: hashlib.sha256(
            f"multirepo-family-split:{repository}:{run.issue_number}".encode()
        ).hexdigest(),
    )[:needed]
    train = selected[: core.TRAIN_CASES]
    dev = selected[core.TRAIN_CASES : core.TRAIN_CASES + core.DEV_CASES]
    calibration = selected[core.TRAIN_CASES + core.DEV_CASES :]
    splits = Splits(
        train=frozenset(run.episode.group_id for run in train),
        dev=frozenset(run.episode.group_id for run in dev),
        calibration=frozenset(run.episode.group_id for run in calibration),
        seed=seed,
    )
    config = GrcConfig(
        entry_schema=("record_number",),
        partition_by=(),
        w_min=2,
        w_max=2,
        b_min=2,
        s_min=5,
        min_principals=1,
        min_days=1,
        alpha=1.0,
        delta=0.10,
        phi_min=0.02,
        max_candidates=12,
        max_artifacts=4,
        max_calibration_windows=core.CALIBRATION_CASES,
        mode="replay",
        owner=f"paper-github-{core._repo_slug(repository)}-{core.SPEC.name}-support-only-study",
        seed=seed,
        synthesize_composites=True,
        composite_projection=core.SPEC.projection,
        composite_pre_model=True,
        composite_continuation_key=continuation_manifest.compatibility_key(),
        freeze_one_candidate_before_calibration=True,
    )
    result = compile_grc(
        [run.episode for run in selected],
        catalog,
        splits,
        source_manifest,
        config,
        sandbox=None,
        perturbations=(),
    )
    admitted = [artifact for artifact in result.artifacts if not artifact.gate.retire]
    base = {
        "report": result.report(),
        "config": asdict(config),
        "splits": splits.manifest(),
        "selection_rule": "exact traces; stable hash split; no tool-order filter; alpha=1.0 support-only ablation",
        "rejection_by_stage": dict(result.rejection_by_stage),
    }
    if not admitted:
        return None, {**base, "status": "retired"}
    artifact = max(admitted, key=lambda value: (
        value.evidence.removed_requests,
        value.evidence.support_groups,
    ))
    artifact.lifecycle = Lifecycle.ACTIVE
    artifact.approved_by = "paper-multirepo-protocol-lab-only"
    registry = Registry(name=f"paper-github-{core._repo_slug(repository)}-{core.SPEC.name}-support-only")
    registry.add(artifact)
    return registry, {
        **base,
        "artifact": artifact.to_dict(),
        "artifact_explanation": artifact.explain(),
        "status": "admitted",
        "lab_promotion": {"not_production_approval": True},
    }


def coverage_curve(compilation: Mapping[str, Any]) -> list[dict[str, Any]] | None:
    """Read the calibration grid sweep back out of a compiled artifact's gate notes.

    ``calibrate_gate`` computes one row per point on the frozen grid -- accepted count,
    violation count, exact Clopper-Pearson upper bound, coverage -- before it ever
    selects a threshold, and stores the full list as text in ``Gate.notes``
    (``"...; grid rows: [...]"``). This parses that back into structured rows; it does
    not rerun or re-derive anything the compiler did not already compute.
    """
    artifact = compilation.get("artifact")
    if not artifact:
        return None
    notes = str(((artifact.get("gate") or {}).get("notes")) or "")
    marker = "grid rows: "
    if marker not in notes:
        return None
    literal = notes.split(marker, 1)[1]
    try:
        rows = ast.literal_eval(literal)
    except (ValueError, SyntaxError):
        return None
    return rows


def distinct_nonzero_coverage_levels(rows: Sequence[Mapping[str, Any]] | None) -> list[float]:
    if not rows:
        return []
    return sorted({float(row["coverage"]) for row in rows if float(row.get("coverage") or 0.0) > 0.0})


def build_preflight(sources: Sequence[Any], *, force_download: bool) -> dict[str, Any]:
    payload = core.build_preflight(
        sources,
        discovery_cases=DISCOVERY_CASES,
        test_cases=TEST_CASES_PER_REPO,
        minimum_gap_days=0,
        seed=20260807,
        force_download=force_download,
    )
    payload["schema"] = "agent-compaction-github-multirepo-gate-frontier-preflight/v1"
    return payload


async def run_repo(
    source: Any,
    *,
    source_manifest: Mapping[str, Any],
    store: Mapping[int, Mapping[str, Any]],
    selection: Mapping[str, Any],
    discovery_rows: Sequence[dict[str, Any]],
    test_rows: Sequence[dict[str, Any]],
    args: argparse.Namespace,
) -> dict[str, Any]:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")
    repository = source.repository
    output_dir = _repo_result_dir(repository)
    output_dir.mkdir(parents=True, exist_ok=True)

    result_path = output_dir / "results.json"
    if args.resume and result_path.exists():
        return json.loads(result_path.read_text(encoding="utf-8"))
    if result_path.exists() and not args.force:
        raise RuntimeError(f"refusing to overwrite {result_path}; pass --force")

    from agents import add_trace_processor

    processor = core.AgentsTraceProcessor(include_sensitive_data=True, max_completed=20_000)
    add_trace_processor(processor)

    source_revision = f"{source_manifest['dataset']}@{source_manifest['revision']}"
    catalog = core.make_catalog(repository)
    tools = core.make_tools(source_revision, store)
    source_driver_manifest = core.make_manifest(
        repository, source_revision, args.model, tools, catalog, "source",
        instructions=core.SPEC.discovery_prompt,
    )
    baseline_manifest = core.make_manifest(
        repository, source_revision, args.model, tools, catalog, "baseline", instructions=core.SPEC.prompt
    )
    continuation_manifest = core.make_manifest(
        repository, source_revision, args.model, (), catalog, "pre-model", instructions=core.SPEC.prompt
    )

    discovery_checkpoint = output_dir / "discovery_checkpoint.json"
    if args.resume and discovery_checkpoint.exists():
        checkpoint = json.loads(discovery_checkpoint.read_text(encoding="utf-8"))
        if checkpoint.get("selection") != dict(selection):
            raise RuntimeError("discovery checkpoint does not match the frozen selection")
        discovery = core.reconstruct_discovery(
            repository, source_revision, checkpoint, store=store, manifest=source_driver_manifest,
        )
        discovery_failures = list(checkpoint.get("failures", ()))
    else:
        discovery, discovery_failures = await core.run_batch(
            repository, source_revision, list(discovery_rows),
            condition="discovery", model_name=args.model, tools=tools, processor=processor,
            manifest=source_driver_manifest, catalog=catalog, store=store,
            concurrency=args.concurrency, instructions=core.SPEC.discovery_prompt,
        )
        checkpoint = {
            "schema": "agent-compaction-github-multirepo-gate-frontier-discovery/v1",
            "repository": repository,
            "family": core.SPEC.name,
            "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "source": dict(source_manifest),
            "selection": dict(selection),
            "model": args.model,
            "provider_backed": True,
            "real_public_records": True,
            "simulated": False,
            "failures": discovery_failures,
            "results": [value.public_dict() for value in discovery],
        }
        discovery_checkpoint.write_text(
            json.dumps(checkpoint, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8",
        )

    learned_registry, learned_compilation = core.compile_artifact(
        repository, discovery, catalog=catalog, source_manifest=source_driver_manifest,
        continuation_manifest=continuation_manifest, seed=args.seed,
    )
    support_registry, support_compilation = compile_support_only_artifact(
        repository, discovery, catalog=catalog, source_manifest=source_driver_manifest,
        continuation_manifest=continuation_manifest, seed=args.seed,
    )

    evaluation_checkpoint = output_dir / "evaluation_checkpoint.json"
    results: list[Any] = []
    failures: list[dict[str, Any]] = []
    if args.resume and evaluation_checkpoint.exists():
        saved = json.loads(evaluation_checkpoint.read_text(encoding="utf-8"))
        if saved.get("selection") != dict(selection):
            raise RuntimeError("evaluation checkpoint does not match the frozen selection")
        results = [
            core.RepoRunResult(
                repository=str(value["repository"]), condition=str(value["condition"]),
                repeat=int(value.get("repeat", 0)), issue_number=int(value["issue_number"]),
                trace_id=str(value["trace_id"]), metrics=dict(value["metrics"]),
                answer=dict(value["answer"]), quality=dict(value["quality"]),
                tool_sequence=list(value["tool_sequence"]),
                tool_arguments=[dict(item) for item in value["tool_arguments"]],
                dispatch=dict(value.get("dispatch", {})),
                episode=SimpleNamespace(to_dict=lambda value=value: {"episode_digest": value["episode_digest"]}),
            )
            for value in saved.get("results", ())
        ]
        failures = list(saved.get("failures", ()))
    completed = {(row.condition, int(row.issue_number)) for row in results}
    schedule: list[dict[str, Any]] = []
    orders = list(permutations(CONDITIONS))
    for index, row in enumerate(test_rows):
        order = orders[index % len(orders)]
        schedule.append({"record_number": int(row["number"]), "order": list(order)})
        for condition in order:
            if (condition, int(row["number"])) in completed:
                continue
            kwargs: dict[str, Any] = {}
            condition_tools: Sequence[Any] = tools
            manifest = baseline_manifest
            if condition == "learned_gate" and learned_registry is not None:
                condition_tools = ()
                manifest = continuation_manifest
                kwargs = {
                    "registry": learned_registry, "artifact_manifest": source_driver_manifest,
                    "fallback_tools": tools, "fallback_manifest": baseline_manifest,
                }
            elif condition == "support_only" and support_registry is not None:
                condition_tools = ()
                manifest = continuation_manifest
                kwargs = {
                    "registry": support_registry, "artifact_manifest": source_driver_manifest,
                    "fallback_tools": tools, "fallback_manifest": baseline_manifest,
                }
            # a retired arm (learned_registry/support_registry is None) falls back to
            # the unchanged agent for that condition, and is reported as retired rather
            # than silently substituted -- see the top-level payload's "compilers" block.
            rows, errors = await core.run_batch(
                repository, source_revision, [dict(row)], condition=condition,
                model_name=args.model, tools=condition_tools, processor=processor,
                manifest=manifest, catalog=catalog, store=store, concurrency=1,
                instructions=core.SPEC.prompt, **kwargs,
            )
            results.extend(rows)
            failures.extend(errors)
            completed.update((value.condition, int(value.issue_number)) for value in rows)
            evaluation_checkpoint.write_text(
                json.dumps(
                    {
                        "schema": "agent-compaction-github-multirepo-gate-frontier-evaluation-checkpoint/v1",
                        "repository": repository, "selection": dict(selection),
                        "results": [value.public_dict() for value in results], "failures": failures,
                    },
                    indent=2, sort_keys=True, default=str,
                ) + "\n", encoding="utf-8",
            )

    grouped = {condition: [row for row in results if row.condition == condition] for condition in CONDITIONS}
    complete = all(len(grouped[name]) == len(test_rows) for name in CONDITIONS)
    learned_rows = coverage_curve(learned_compilation)
    support_rows = coverage_curve(support_compilation)
    payload = {
        "schema": "agent-compaction-github-multirepo-gate-frontier/v1",
        "run": {
            "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "repository": repository, "family": core.SPEC.name, "model": args.model,
            "openai_agents_sdk": version("openai-agents"), "openai_python": version("openai"),
            "python": platform.python_version(), "platform": platform.platform(),
            "provider_backed": True, "real_public_records": True, "simulated": False,
            "openai_api_key_used": True, "secrets_serialized": False,
            "comparative_claim_allowed": bool(complete and not failures),
            "resolved_config": vars(args),
        },
        "source": dict(source_manifest),
        "selection": dict(selection),
        "compilers": {"learned_gate": learned_compilation, "support_only": support_compilation},
        "coverage_curves": {
            "learned_gate": learned_rows,
            "support_only": support_rows,
            "learned_gate_distinct_nonzero_coverage_levels": distinct_nonzero_coverage_levels(learned_rows),
            "support_only_distinct_nonzero_coverage_levels": distinct_nonzero_coverage_levels(support_rows),
        },
        "schedule": schedule,
        "aggregate": core.aggregate_runs(results),
        "comparisons": {
            "baseline_vs_learned_gate": core.paired(grouped["baseline"], grouped["learned_gate"], "learned_gate"),
            "baseline_vs_support_only": core.paired(grouped["baseline"], grouped["support_only"], "support_only"),
        },
        "failures": failures,
        "results": [value.public_dict() for value in results],
    }
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")
    if learned_registry is not None:
        learned_registry.save(output_dir / "registry_learned_gate")
    if support_registry is not None:
        support_registry.save(output_dir / "registry_support_only")
    return payload


async def run(args: argparse.Namespace) -> dict[str, Any]:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    sources = core._selected_sources(args.repositories)
    preflight_payload = build_preflight(sources, force_download=args.force_download)
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "preflight.json").write_text(
        json.dumps(preflight_payload, indent=2, sort_keys=True) + "\n"
    )
    if args.preflight_only:
        return {"preflight": preflight_payload}

    if not args.approved_spend_usd or args.approved_spend_usd <= 0:
        raise SystemExit(
            "refusing to make live provider calls without --approved-spend-usd > 0; "
            "see paper/supplementary/prospective-gate-frontier-protocol.md"
        )

    selected = {
        repository: value
        for repository, value in preflight_payload["repositories"].items()
        if value.get("status") == "selected"
    }
    if len(selected) < args.minimum_complete_repos:
        raise RuntimeError(
            f"only {len(selected)} repositories satisfy the frozen protocol; need {args.minimum_complete_repos}"
        )
    if sum(len(value["selection"]["test"]) for value in selected.values()) < args.minimum_pooled_test_cases:
        raise RuntimeError("pooled held-out cohort is too small for the configured minimum")

    repo_results: dict[str, Any] = {}
    repo_failures: list[dict[str, Any]] = []
    pooled_results: list[Any] = []
    pooled_failures: list[dict[str, Any]] = []
    for source in sources:
        if source.repository not in selected:
            continue
        source_manifest = selected[source.repository]["audit"]["source_manifest"]
        store, _ = core.load_store(source, source_manifest)
        discovery_rows = [
            dict(store[int(value["record_number"])])
            for value in selected[source.repository]["selection"]["discovery"]
        ]
        test_rows = [
            dict(store[int(value["record_number"])])
            for value in selected[source.repository]["selection"]["test"]
        ]
        try:
            repo_payload = await run_repo(
                source, source_manifest=source_manifest, store=store,
                selection=selected[source.repository]["selection"],
                discovery_rows=discovery_rows, test_rows=test_rows, args=args,
            )
        except Exception as exc:
            output_dir = _repo_result_dir(source.repository)
            failure_payload = {
                "repository": source.repository, "status": "failed_closed",
                "error": f"{type(exc).__name__}: {exc}", "source": dict(source_manifest),
                "selection": selected[source.repository]["selection"],
                "discovery_checkpoint": _checkpoint_summary(output_dir / "discovery_checkpoint.json"),
                "evaluation_checkpoint": _checkpoint_summary(output_dir / "evaluation_checkpoint.json"),
            }
            repo_results[source.repository] = failure_payload
            repo_failures.append(failure_payload)
            continue
        repo_results[source.repository] = repo_payload
        pooled_results.extend(
            core.RepoRunResult(
                repository=str(value["repository"]), condition=str(value["condition"]),
                repeat=int(value.get("repeat", 0)), issue_number=int(value["issue_number"]),
                trace_id=str(value["trace_id"]), metrics=dict(value["metrics"]),
                answer=dict(value["answer"]), quality=dict(value["quality"]),
                tool_sequence=list(value["tool_sequence"]),
                tool_arguments=[dict(item) for item in value["tool_arguments"]],
                dispatch=dict(value.get("dispatch", {})),
                episode=SimpleNamespace(to_dict=lambda value=value: {"episode_digest": value["episode_digest"]}),
            )
            for value in repo_payload["results"]
        )
        pooled_failures.extend(repo_payload["failures"])

    grouped = {condition: [row for row in pooled_results if row.condition == condition] for condition in CONDITIONS}
    all_coverage_levels = sorted({
        level
        for repo_payload in repo_results.values()
        for key in ("learned_gate_distinct_nonzero_coverage_levels",)
        for level in (repo_payload.get("coverage_curves", {}).get(key) or [])
    })
    payload = {
        "schema": "agent-compaction-github-multirepo-gate-frontier-summary/v1",
        "run": {
            "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "repositories": list(repo_results), "family": core.SPEC.name, "model": args.model,
            "provider_backed": True, "real_public_records": True, "simulated": False,
            "openai_api_key_used": True, "secrets_serialized": False,
            "comparative_claim_allowed": not pooled_failures and not repo_failures,
            "approved_spend_usd": args.approved_spend_usd,
            "resolved_config": vars(args),
        },
        "preflight": preflight_payload,
        "aggregate": core.aggregate_runs(pooled_results),
        "comparisons": {
            "baseline_vs_learned_gate": core.paired(grouped["baseline"], grouped["learned_gate"], "learned_gate"),
            "baseline_vs_support_only": core.paired(grouped["baseline"], grouped["support_only"], "support_only"),
        },
        "pooled_learned_gate_distinct_nonzero_coverage_levels": all_coverage_levels,
        "failures": pooled_failures,
        "repository_failures": repo_failures,
        "repositories": repo_results,
        "pooled_test_pairs": len(grouped["baseline"]),
    }
    (OUT_ROOT / "results.json").write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repositories", nargs="+", default=tuple(core.DEFAULT_SOURCES))
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--minimum-complete-repos", type=int, default=MINIMUM_COMPLETE_REPOS)
    parser.add_argument("--minimum-pooled-test-cases", type=int, default=MINIMUM_POOLED_TEST_CASES)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260807)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument(
        "--approved-spend-usd", type=float, default=0.0,
        help="required, >0, before any live provider call is made",
    )
    args = parser.parse_args()
    if args.concurrency <= 0:
        parser.error("--concurrency must be positive")
    return args


def main() -> None:
    payload = asyncio.run(run(parse_args()))
    summary = {
        "schema": payload.get("schema", payload.get("preflight", {}).get("schema")),
        "run": payload.get("run"),
        "aggregate": payload.get("aggregate"),
        "comparisons": payload.get("comparisons"),
        "pooled_learned_gate_distinct_nonzero_coverage_levels": payload.get(
            "pooled_learned_gate_distinct_nonzero_coverage_levels"
        ),
        "failures": payload.get("failures"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
