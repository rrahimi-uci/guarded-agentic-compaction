#!/usr/bin/env python3
"""Capped OpenAI Agents SDK runner for the frozen real-record multidomain study.

This script never substitutes synthetic records. It executes only cases named by a
digested frozen protocol against immutable local snapshots. Possession of an API key
is not authorization: a positive command-line dollar cap, a pinned pricing manifest,
reviewed macro approvals, and GRC registries are required for the relevant actions.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import platform
import sys
import time
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any, Mapping, Sequence

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
for candidate in (ROOT, ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from agent_compaction.benchmarking import (  # noqa: E402
    ActionSpec,
    FrozenProtocol,
    MacroApproval,
    ProviderBudget,
    ScheduledExecution,
    build_role_schedule,
    frozen_artifact_digest,
    load_case_jsonl,
    schedule_summary,
)
from agent_compaction.benchmarking.preflight import STATISTICAL_CONTRACT  # noqa: E402
from agent_compaction.capture.agents_sdk import (  # noqa: E402
    AgentsTraceProcessor,
    episode_from_agents_trace,
)
from agent_compaction.capture.manifests import build_manifest  # noqa: E402
from agent_compaction.evaluation import CanonicalMetrics, RunLedger, episode_metrics  # noqa: E402
from agent_compaction.registry.store import Registry  # noqa: E402
from agent_compaction.portfolio import PortfolioPolicy  # noqa: E402
from agent_compaction.runtime.model_provider import CompactingModel  # noqa: E402
from agent_compaction.schema.artifacts import Lifecycle  # noqa: E402
from agent_compaction.schema.traces import (  # noqa: E402
    OutcomeLabels,
    TraceEnvelope,
    content_digest,
)
from benchmarks.runtime import DomainRuntime, load_domain_runtime  # noqa: E402


ACTIONS = ("baseline", "grc", "macro")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _pairs(values: Sequence[str], *, label: str) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"{label} must use DOMAIN=PATH")
        domain, raw_path = value.split("=", 1)
        if domain in result:
            raise ValueError(f"duplicate {label} for {domain!r}")
        result[domain] = Path(raw_path)
    return result


def _cases(values: Sequence[str]) -> dict[str, tuple]:
    return {domain: load_case_jsonl(path) for domain, path in _pairs(values, label="cases").items()}


def _pricing(path: Path, model: str) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    expected_fields = {
        "schema",
        "model",
        "input_usd_per_million",
        "cached_input_usd_per_million",
        "output_usd_per_million",
        "maximum_billable_input_tokens_per_request",
        "output_token_limit_per_request",
        "service_tier",
        "revision",
        "source_url",
        "retrieved_at",
    }
    if set(raw) != expected_fields:
        raise ValueError("pricing manifest fields do not match pricing.schema.json")
    if raw.get("schema") != "agent-compaction-pricing/v1" or raw.get("model") != model:
        raise ValueError("pricing manifest schema/model does not match the requested model")
    for field in ("input_usd_per_million", "cached_input_usd_per_million", "output_usd_per_million"):
        value = raw.get(field)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError(f"pricing manifest has invalid {field}")
    for field in (
        "maximum_billable_input_tokens_per_request",
        "output_token_limit_per_request",
    ):
        if type(raw.get(field)) is not int or raw[field] < 1:
            raise ValueError(f"pricing manifest has invalid {field}")
    if raw.get("service_tier") not in {"auto", "default", "flex", "priority"}:
        raise ValueError("pricing manifest service_tier is invalid")
    if not str(raw.get("revision", "")).strip() or not str(raw.get("source_url", "")).startswith("https://"):
        raise ValueError("pricing revision and HTTPS source_url are required")
    try:
        retrieved_at = datetime.fromisoformat(str(raw["retrieved_at"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("pricing retrieved_at must be ISO-8601") from exc
    if retrieved_at.tzinfo is None:
        raise ValueError("pricing retrieved_at must include a timezone")
    raw["sha256"] = _sha(path)
    return raw


def _price(metrics: Any, pricing: Mapping[str, Any]) -> float:
    ordinary = max(0, metrics.input_tokens - metrics.cached_input_tokens)
    return (
        ordinary * float(pricing["input_usd_per_million"])
        + metrics.cached_input_tokens * float(pricing["cached_input_usd_per_million"])
        + metrics.output_tokens * float(pricing["output_usd_per_million"])
    ) / 1_000_000


def _attempt_cost_ceiling(pricing: Mapping[str, Any], max_model_requests: int) -> float:
    """Conservative pre-call bound from frozen billing and token ceilings."""

    input_rate = max(
        float(pricing["input_usd_per_million"]),
        float(pricing["cached_input_usd_per_million"]),
    )
    per_request = (
        int(pricing["maximum_billable_input_tokens_per_request"]) * input_rate
        + int(pricing["output_token_limit_per_request"])
        * float(pricing["output_usd_per_million"])
    ) / 1_000_000
    return per_request * max_model_requests


def _schedule(
    protocol: FrozenProtocol,
    cases: Mapping[str, Sequence],
    *,
    phase: str,
) -> tuple[ScheduledExecution, ...]:
    if phase == "pilot":
        return build_role_schedule(
            protocol, cases, role="reserve", actions=ACTIONS, limit_per_domain=12
        )
    if phase == "discovery":
        return build_role_schedule(protocol, cases, role="discovery", actions=("baseline",))
    if phase == "development":
        return build_role_schedule(protocol, cases, role="development", actions=("baseline",))
    if phase == "artifact-calibration":
        return build_role_schedule(
            protocol, cases, role="artifact_calibration", actions=("baseline", "grc")
        )
    if phase == "portfolio-calibration":
        return build_role_schedule(protocol, cases, role="portfolio_calibration", actions=ACTIONS)
    if phase != "test":
        raise ValueError(f"unknown phase {phase!r}")
    primary = list(build_role_schedule(protocol, cases, role="test", actions=ACTIONS))
    repeats = build_role_schedule(
        protocol,
        cases,
        role="test",
        actions=ACTIONS,
        repeats=int(STATISTICAL_CONTRACT["repeats_per_group"]),
        limit_per_domain=int(STATISTICAL_CONTRACT["repeat_groups"]),
    )
    primary.extend(item for item in repeats if item.repeat > 0)
    return tuple(
        ScheduledExecution(
            sequence=index,
            stage=item.stage,
            domain=item.domain,
            case_id=item.case_id,
            group_id=item.group_id,
            role=item.role,
            action=item.action,
            repeat=item.repeat,
        )
        for index, item in enumerate(primary, 1)
    )


def _approval(
    path: Path, *, domain: str, runtime: DomainRuntime, repository_root: Path
) -> MacroApproval:
    raw = json.loads(path.read_text(encoding="utf-8"))
    approval = MacroApproval(**raw)
    approval.validate()
    expected_schema = _sha(
        repository_root
        / "benchmarks/contracts"
        / {"vulnerability": "vulnerability.schema.json", "hmda": "hmda_record.schema.json", "sec": "sec_fact.schema.json"}[domain]
    )
    if approval.domain != domain or approval.schema_digest != expected_schema:
        raise ValueError(f"macro approval does not match {domain} schema")
    if approval.implementation_digest != _macro_implementation_digest(domain):
        raise ValueError(f"macro approval does not match {domain} implementation")
    if approval.effect_catalog_digest != _effect_catalog_approval_digest(runtime):
        raise ValueError(f"macro approval does not match {domain} effect catalog")
    if approval.evaluator_digest != _evaluator_digest(domain, runtime):
        raise ValueError(f"macro approval does not match {domain} evaluator and gold")
    reviewed_at = datetime.fromisoformat(approval.reviewed_at.replace("Z", "+00:00"))
    if reviewed_at > datetime.now(UTC):
        raise ValueError("macro approval timestamp is in the future")
    return approval


def _implementation_material(domain: str) -> dict[str, str]:
    return {
        "runtime_sha256": _sha(ROOT / "benchmarks/runtime.py"),
        "domain_adapter_sha256": _sha(
            ROOT
            / "benchmarks/adapters"
            / {
                "vulnerability": "vulnerability_evidence.py",
                "sec": "sec_filing_facts.py",
                "hmda": "hmda_public_lar.py",
            }[domain]
        ),
    }


def _macro_implementation_digest(domain: str) -> str:
    return hashlib.sha256(
        _canonical(_implementation_material(domain)).encode("utf-8")
    ).hexdigest()


def _effect_catalog_approval_digest(runtime: DomainRuntime) -> str:
    """Full review digest; distinct from the catalog's short runtime ID."""

    return hashlib.sha256(
        _canonical(runtime.macro_catalog.model_dump(mode="json")).encode("utf-8")
    ).hexdigest()


def _evaluator_digest(domain: str, runtime: DomainRuntime) -> str:
    schema = {
        "vulnerability": "vulnerability.schema.json",
        "sec": "sec_fact.schema.json",
        "hmda": "hmda_record.schema.json",
    }[domain]
    material = {
        "schema_sha256": _sha(ROOT / "benchmarks/contracts" / schema),
        "oracle_sha256": _sha(ROOT / "benchmarks/oracles.py"),
        "gold_constructor_sha256": _sha(ROOT / "benchmarks/gold.py"),
        "retained_gold_sha256": hashlib.sha256(
            _canonical(dict(runtime.gold)).encode("utf-8")
        ).hexdigest(),
        "runtime_sha256": _sha(ROOT / "benchmarks/runtime.py"),
    }
    return hashlib.sha256(_canonical(material).encode("utf-8")).hexdigest()


def _control_plane_digest() -> str:
    paths = [
        ROOT / "src/agent_compaction/benchmarking/actions.py",
        ROOT / "src/agent_compaction/benchmarking/budget.py",
        ROOT / "src/agent_compaction/benchmarking/preflight.py",
        ROOT / "src/agent_compaction/benchmarking/protocol.py",
        ROOT / "src/agent_compaction/benchmarking/schedule.py",
        ROOT / "benchmarks/gold.py",
        ROOT / "benchmarks/oracles.py",
        ROOT / "benchmarks/runtime.py",
        ROOT / "paper/scripts/multidomain_study.py",
        ROOT / "paper/scripts/compile_multidomain.py",
        ROOT / "paper/scripts/calibrate_grc_artifacts.py",
        ROOT / "paper/scripts/freeze_multidomain_actions.py",
        ROOT / "paper/scripts/calibrate_multidomain.py",
        ROOT / "paper/scripts/analyze_multidomain.py",
        ROOT / "paper/scripts/validate_multidomain.py",
    ]
    material = {str(path.relative_to(ROOT)): _sha(path) for path in paths}
    return hashlib.sha256(_canonical(material).encode("utf-8")).hexdigest()


def _preflight(
    args: argparse.Namespace,
    protocol: FrozenProtocol,
    cases: Mapping[str, Sequence],
    schedule: Sequence[ScheduledExecution],
    runtimes: Mapping[str, DomainRuntime],
    pricing: Mapping[str, Any],
) -> dict[str, Any]:
    registry_paths = _pairs(args.registry, label="registry")
    approval_paths = _pairs(args.macro_approval, label="macro approval")
    actions = {item.action for item in schedule}
    errors: list[str] = []
    registries: dict[str, Registry] = {}
    unavailable_actions: dict[tuple[str, str], str] = {}
    approvals: dict[str, MacroApproval] = {}
    policy: PortfolioPolicy | None = None
    action_lock_digest = ""
    if "grc" in actions:
        required_grc_stage = (
            Lifecycle.SHADOW
            if args.phase in {"pilot", "artifact-calibration"}
            else Lifecycle.ACTIVE
        )
        for domain in runtimes:
            try:
                registries[domain] = Registry.load(registry_paths[domain])
                if not any(
                    artifact.lifecycle is required_grc_stage
                    for artifact in registries[domain].artifacts
                ):
                    unavailable_actions[(domain, "grc")] = (
                        f"registry_contains_no_{required_grc_stage.value}_artifacts"
                    )
            except Exception as exc:
                errors.append(f"{domain}: GRC registry unavailable ({type(exc).__name__})")
    if "macro" in actions:
        for domain, runtime in runtimes.items():
            try:
                approvals[domain] = _approval(
                    approval_paths[domain], domain=domain, runtime=runtime, repository_root=ROOT
                )
            except Exception as exc:
                errors.append(f"{domain}: macro approval unavailable ({type(exc).__name__})")
    if set(protocol.group_roles) != set(cases) or set(cases) != set(runtimes):
        errors.append("protocol, cases, and runtime domain sets differ")
    expected_execution_contract = {
        "model": args.model,
        "pricing_digest": pricing["sha256"],
        "pricing_revision": str(pricing["revision"]),
        "service_tier": str(pricing["service_tier"]),
        "maximum_billable_input_tokens_per_request": str(
            pricing["maximum_billable_input_tokens_per_request"]
        ),
        "output_token_limit_per_request": str(
            pricing["output_token_limit_per_request"]
        ),
        "openai_agents_version": version("openai-agents"),
        "openai_version": version("openai"),
    }
    if protocol.model != args.model or dict(protocol.execution_contract) != expected_execution_contract:
        errors.append("model, pricing, service tier, or SDK version drifted after protocol freeze")
    if args.phase in {"pilot", "portfolio-calibration", "test"}:
        try:
            if args.action_lock is None:
                raise ValueError("action lock path is required")
            action_lock_digest = _validate_action_lock(
                args.action_lock,
                protocol=protocol,
                runtimes=runtimes,
                registries=registries,
                approvals=approvals,
                model_name=args.model,
                expected_grc_stage=(
                    "shadow" if args.phase == "pilot" else "active"
                ),
            )
        except Exception as exc:
            errors.append(f"frozen action lock unavailable ({type(exc).__name__})")
    if args.phase == "test":
        try:
            raw_policy = json.loads(args.policy.read_text(encoding="utf-8"))
            if raw_policy.get("schema") != "agent-compaction-frozen-portfolio/v1":
                raise ValueError("unsupported frozen portfolio schema")
            if raw_policy.get("portfolio_artifact_digest") != frozen_artifact_digest(
                raw_policy, digest_field="portfolio_artifact_digest"
            ):
                raise ValueError("frozen portfolio artifact digest mismatch")
            policy = PortfolioPolicy.from_dict(raw_policy["policy"])
            if (
                raw_policy.get("protocol_digest") != protocol.digest
                or policy.manifest_digest != protocol.digest
                or raw_policy.get("policy_digest") != policy.digest
                or raw_policy.get("action_lock_digest") != action_lock_digest
            ):
                raise ValueError("portfolio policy/protocol digest mismatch")
            expected = {protocol.family_key(domain) for domain in protocol.group_roles}
            if set(policy.registered_families) != expected:
                raise ValueError("portfolio policy family set mismatch")
            for domain in protocol.group_roles:
                selected = policy.select(protocol.family_key(domain)).selected_action
                if (domain, selected) in unavailable_actions:
                    raise ValueError("portfolio selects an unavailable action")
        except Exception as exc:
            errors.append(f"frozen portfolio unavailable ({type(exc).__name__})")
    summary = schedule_summary(
        schedule,
        max_model_requests_per_execution=args.max_model_requests,
        retries=args.retries,
    )
    billable_executions = sum(
        (item.domain, item.action) not in unavailable_actions for item in schedule
    )
    summary["billable_executions"] = billable_executions
    summary["unavailable_executions"] = len(schedule) - billable_executions
    summary["maximum_provider_requests"] = (
        billable_executions * args.max_model_requests * (args.retries + 1)
    )
    maximum_reserved_usd = (
        billable_executions
        * (args.retries + 1)
        * args.reservation_usd_per_execution
    )
    attempt_cost_ceiling = _attempt_cost_ceiling(pricing, args.max_model_requests)
    if args.reservation_usd_per_execution + 1e-12 < attempt_cost_ceiling:
        errors.append(
            "per-execution reservation is below the frozen worst-case token-cost ceiling"
        )
    if maximum_reserved_usd > args.max_provider_usd + 1e-12:
        errors.append(
            "provider cap is below the maximum scheduled retry reservations"
        )
    return {
        "schema": "agent-compaction-multidomain-run-preflight/v1",
        "eligible": not errors,
        "errors": errors,
        "phase": args.phase,
        "protocol_digest": protocol.digest,
        "model": args.model,
        "pricing_revision": pricing["revision"],
        "pricing_digest": pricing["sha256"],
        "service_tier": pricing["service_tier"],
        "max_provider_usd": args.max_provider_usd,
        "reservation_usd_per_execution_attempt": args.reservation_usd_per_execution,
        "maximum_scheduled_reservation_usd": maximum_reserved_usd,
        "maximum_token_cost_per_execution_attempt_usd": attempt_cost_ceiling,
        "provider_calls_executed": 0,
        "credential_names_required": ["OPENAI_API_KEY"],
        "schedule": summary,
        "environment": {
            "python": platform.python_version(),
            "openai_agents": version("openai-agents"),
            "openai": version("openai"),
        },
        "registries": registries,
        "approvals": approvals,
        "policy": policy,
        "policy_digest": "" if policy is None else policy.digest,
        "action_lock_digest": action_lock_digest,
        "unavailable_action_records": [
            {"domain": domain, "action": action, "reason": reason}
            for (domain, action), reason in sorted(unavailable_actions.items())
        ],
        "unavailable_actions": unavailable_actions,
    }


def _trace_id(protocol: FrozenProtocol, item: ScheduledExecution, attempt: int) -> str:
    value = hashlib.sha256(
        f"{protocol.digest}:{item.event_id}:a{attempt}".encode()
    ).hexdigest()[:32]
    return f"trace_{value}"


def _tool_names(trace: Any) -> list[str]:
    return [str(call["name"]) for call in _tool_calls(trace)]


def _tool_calls(trace: Any) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for span in trace.spans:
        if span.data.get("type") != "function":
            continue
        value = span.data.get("input")
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
        calls.append({"name": str(span.data.get("name") or ""), "input": value})
    return calls


def _pilot_projection(
    records: Sequence[Any],
    unavailable_actions: Mapping[tuple[str, str], str],
    domains: Sequence[str],
) -> dict[str, Any]:
    completed = [
        record
        for record in records
        if record.event_type == "execution_complete"
        and record.payload["schedule"]["role"] == "reserve"
    ]
    failed = [record for record in records if record.event_type == "execution_failed"]
    by_key: dict[tuple[str, str], list[float]] = {}
    for record in completed:
        schedule = record.payload["schedule"]
        key = (str(schedule["domain"]), str(schedule["action"]))
        by_key.setdefault(key, []).append(
            float(record.payload["metrics"]["estimated_cost_usd"])
        )
    expected = {
        (domain, action)
        for domain in domains
        for action in ACTIONS
        if (domain, action) not in unavailable_actions
    }
    incomplete = sorted(
        f"{domain}:{action}"
        for domain, action in expected
        if len(by_key.get((domain, action), ())) != 12
    )
    if failed or incomplete or not expected:
        return {
            "available": False,
            "reason": "pilot failures or incomplete 12-group action cells",
            "incomplete_cells": incomplete,
            "failed_attempts": len(failed),
        }
    planned_per_action = {"baseline": 385, "grc": 315, "macro": 215}
    cells = []
    total = 0.0
    for domain, action in sorted(expected):
        values = by_key[(domain, action)]
        mean_cost = sum(values) / len(values)
        scheduled = planned_per_action[action]
        projected = mean_cost * scheduled
        total += projected
        cells.append(
            {
                "domain": domain,
                "action": action,
                "pilot_groups": len(values),
                "pilot_mean_cost_usd": mean_cost,
                "full_study_scheduled_executions": scheduled,
                "projected_inference_cost_usd": projected,
            }
        )
    return {
        "available": True,
        "basis": "pilot mean completed cost times frozen full-study schedule",
        "contingency_multiplier": 1.25,
        "cells": cells,
        "projected_inference_cost_usd": total,
        "projected_inference_cost_with_contingency_usd": total * 1.25,
        "excludes": [
            "engineering labor",
            "macro review labor",
            "source acquisition labor",
            "maintenance and monitoring",
        ],
    }


def _build_action_spec(
    *,
    domain: str,
    action: str,
    protocol: FrozenProtocol,
    runtime: DomainRuntime,
    model_name: str,
    registry: Registry | None = None,
    approval: MacroApproval | None = None,
    grc_stage: str | None = None,
) -> ActionSpec:
    implementation_material: dict[str, Any] = _implementation_material(domain)
    if action == "grc":
        if registry is None:
            raise ValueError("GRC action identity requires a registry")
        if grc_stage not in {"shadow", "active"}:
            raise ValueError("GRC action identity requires a shadow or active stage")
        implementation_material["artifacts"] = [
            artifact.to_dict() for artifact in registry.artifacts
        ]
    if action == "macro":
        if approval is None:
            raise ValueError("macro action identity requires review approval")
    implementation_digest = hashlib.sha256(
        _canonical(implementation_material).encode("utf-8")
    ).hexdigest()
    catalog = runtime.catalog(action)
    return ActionSpec(
        name=action,
        version=(
            approval.macro_version
            if action == "macro" and approval is not None
            else f"grc-{grc_stage}-v1" if action == "grc" else "baseline-v1"
        ),
        implementation_digest=implementation_digest,
        prompt_digest=hashlib.sha256(runtime.prompt.encode("utf-8")).hexdigest(),
        tool_digest=catalog.digest(),
        evaluator_digest=_evaluator_digest(domain, runtime),
        compatibility_key=protocol.family_key(domain),
        metadata={
            "source_snapshot": protocol.source_digests[domain],
            "model": model_name,
            "service_tier": protocol.execution_contract["service_tier"],
            "protocol_digest": protocol.digest,
        },
        macro_approval_digest=(
            approval.digest if action == "macro" and approval is not None else ""
        ),
    )


def _validate_action_lock(
    path: Path,
    *,
    protocol: FrozenProtocol,
    runtimes: Mapping[str, DomainRuntime],
    registries: Mapping[str, Registry],
    approvals: Mapping[str, MacroApproval],
    model_name: str,
    expected_grc_stage: str,
) -> str:
    raw = json.loads(path.read_text(encoding="utf-8"))
    expected_fields = {
        "schema",
        "frozen_at",
        "protocol_digest",
        "pricing_digest",
        "model",
        "grc_stage",
        "control_plane_digest",
        "actions",
        "unavailable_actions",
        "provider_calls_executed",
        "action_lock_digest",
    }
    if not isinstance(raw, dict) or set(raw) != expected_fields:
        raise ValueError("action lock fields are invalid")
    digest = str(raw.get("action_lock_digest", ""))
    unsigned = dict(raw)
    unsigned.pop("action_lock_digest", None)
    observed = hashlib.sha256(_canonical(unsigned).encode("utf-8")).hexdigest()
    if raw.get("schema") != "agent-compaction-frozen-actions/v1" or digest != observed:
        raise ValueError("action lock schema or digest is invalid")
    if (
        raw.get("protocol_digest") != protocol.digest
        or raw.get("pricing_digest") != protocol.execution_contract.get("pricing_digest")
        or raw.get("model") != model_name
        or raw.get("grc_stage") != expected_grc_stage
        or raw.get("control_plane_digest") != _control_plane_digest()
        or raw.get("provider_calls_executed") != 0
    ):
        raise ValueError("action lock differs from the frozen execution contract")
    frozen_at = datetime.fromisoformat(str(raw["frozen_at"]).replace("Z", "+00:00"))
    if frozen_at.tzinfo is None or frozen_at > datetime.now(UTC):
        raise ValueError("action lock timestamp is invalid")
    current: dict[str, dict[str, Any]] = {}
    unavailable: list[dict[str, str]] = []
    grc_stage = Lifecycle(expected_grc_stage)
    for domain in sorted(runtimes):
        registry = registries[domain]
        if not any(artifact.lifecycle is grc_stage for artifact in registry.artifacts):
            unavailable.append(
                {
                    "domain": domain,
                    "action": "grc",
                    "reason": f"registry_contains_no_{grc_stage.value}_artifacts",
                }
            )
        current[domain] = {}
        for action in ACTIONS:
            spec = _build_action_spec(
                domain=domain,
                action=action,
                protocol=protocol,
                runtime=runtimes[domain],
                model_name=model_name,
                registry=registry if action == "grc" else None,
                approval=approvals[domain] if action == "macro" else None,
                grc_stage=expected_grc_stage if action == "grc" else None,
            )
            current[domain][action] = {**asdict(spec), "action_digest": spec.digest}
    if raw.get("actions") != current or raw.get("unavailable_actions") != unavailable:
        raise ValueError("action implementation, registry, approval, prompt, tool, or evaluator drifted")
    return digest


def _model_settings(service_tier: str, output_token_limit: int) -> Any:
    from agents import ModelSettings
    from agents.model_settings import Reasoning

    return ModelSettings(
        reasoning=Reasoning(effort="low"), verbosity="low", parallel_tool_calls=False,
        max_tokens=output_token_limit, store=False, include_usage=True,
        extra_body={"service_tier": service_tier},
    )


async def _execute_one(
    *,
    item: ScheduledExecution,
    attempt: int,
    protocol: FrozenProtocol,
    runtime: DomainRuntime,
    model_name: str,
    pricing: Mapping[str, Any],
    processor: AgentsTraceProcessor,
    registry: Registry | None,
    timeout_s: float,
    max_model_requests: int,
    approval: MacroApproval | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    from agents import Agent, RunConfig, Runner
    from agents.models.openai_provider import OpenAIProvider

    case = runtime.cases[item.case_id]
    tools = runtime.tools(item.action, case)
    catalog = runtime.catalog(item.action)
    manifest = build_manifest(
        commit=protocol.config_digest,
        model=model_name,
        prompt=runtime.prompt,
        tools=tools,
        policy=f"{item.domain}-public-evidence-only-v1",
        guardrails="read-only local snapshot; public factual evidence; no regulated decision",
        catalog=catalog,
        entry_contract_version=f"{item.domain}-case-v1",
        sdk_version=version("openai-agents"),
    )
    compacting = None
    model: Any = model_name
    if item.action == "grc":
        if registry is None:
            raise RuntimeError("GRC action has no validated registry")
        compacting = CompactingModel(
            OpenAIProvider().get_model(model_name),
            registry=registry,
            catalog=catalog,
            manifest=manifest,
            mode="live",
            entry_state_fn=lambda _input: {
                "snapshot_digest": case.source_snapshot.removeprefix("sha256:"),
                **dict(case.inputs),
            },
            partition_fn=lambda _input, _entry: {},
            live_stages=(
                (Lifecycle.SHADOW,)
                if item.role in {"reserve", "artifact_calibration"}
                else (Lifecycle.ACTIVE,)
            ),
        )
        model = compacting
    agent = Agent(
        name=f"real-public-record-{item.domain}",
        instructions=runtime.prompt,
        model=model,
        model_settings=_model_settings(
            str(pricing["service_tier"]),
            int(pricing["output_token_limit_per_request"]),
        ),
        tools=tools,
        output_type=runtime.output_type,
    )
    trace_id = _trace_id(protocol, item, attempt)
    user_input = "Reconcile this frozen public-record case:\n" + _canonical(
        {
            "snapshot_digest": case.source_snapshot.removeprefix("sha256:"),
            "inputs": dict(case.inputs),
        }
    )
    started = time.perf_counter()
    result = await asyncio.wait_for(
        Runner.run(
            agent,
            user_input,
            max_turns=max_model_requests,
            run_config=RunConfig(
                workflow_name=f"agent-compaction-multidomain:{item.domain}:{item.action}",
                trace_id=trace_id,
                group_id=item.group_id,
                trace_include_sensitive_data=True,
                trace_metadata={
                    "public_real_record": "true",
                    "local_frozen_snapshot": "true",
                    "protocol_digest": protocol.digest,
                    "phase": item.role,
                    "domain": item.domain,
                    "action": item.action,
                    "repeat": str(item.repeat),
                },
            ),
        ),
        timeout=timeout_s,
    )
    wall_ms = (time.perf_counter() - started) * 1000.0
    traces = {trace.trace_id: trace for trace in processor.drain()}
    trace = traces.get(trace_id)
    if trace is None:
        raise RuntimeError("completed Agents SDK run has no local trace")
    tool_calls = _tool_calls(trace)
    tool_names = [str(call["name"]) for call in tool_calls]
    oracle = runtime.evaluate(
        case,
        result.final_output,
        tool_names,
        action=item.action,
        tool_calls=tool_calls,
    )
    oracle_score = sum(oracle.field_results.values()) / len(oracle.field_results)
    outcome = OutcomeLabels(
        task_success=oracle.passed,
        semantic_score=oracle_score,
        safety_events=0,
        business_metrics={"tool_contract": float("tool contract failed" not in oracle.errors)},
    )
    envelope = TraceEnvelope(
        trace_id=trace_id,
        episode_id=item.event_id,
        group_id=item.group_id,
        manifest_id=manifest.manifest_id,
        principal="public-benchmark-runner",
        tenant_partition=f"public:{item.domain}",
        policy_version="multidomain-public-evidence-v1",
        day=datetime.now(UTC).date().isoformat(),
        privacy_class="public_record_provider_trace",
        entry_state_ref=content_digest(dict(case.inputs)),
        external_state_version=case.source_snapshot,
    )
    episode = episode_from_agents_trace(
        trace,
        envelope=envelope,
        manifest=manifest,
        entry_state={
            "snapshot_digest": case.source_snapshot.removeprefix("sha256:"),
            **dict(case.inputs),
        },
        outcome=outcome,
        final_state_digest=case.source_snapshot,
    )
    episode.attributes.update(
        {
            "wall_latency_ms": wall_ms,
            "real_public_record": True,
            "local_snapshot_tools": True,
            "provider_backed": True,
            "domain": item.domain,
            "action": item.action,
            "repeat": item.repeat,
            "dispatch_records": (
                list(compacting.shadow_log)
                if compacting is not None
                else []
            ),
        }
    )
    observed = episode_metrics(episode, catalog)
    cost = _price(observed, pricing)
    metrics = CanonicalMetrics(
        model_requests=observed.requests,
        input_tokens=observed.input_tokens,
        cached_input_tokens=observed.cached_input_tokens,
        output_tokens=observed.output_tokens,
        total_tokens=observed.input_tokens + observed.output_tokens,
        estimated_cost_usd=cost,
        wall_latency_ms=wall_ms,
        critical_path_ms=observed.critical_path_ms,
        tool_calls=observed.tool_calls,
        quality_contract_pass=oracle.passed,
        provider_trace_id=trace_id,
    )
    output = result.final_output.model_dump(mode="json")
    action_spec = _build_action_spec(
        domain=item.domain,
        action=item.action,
        protocol=protocol,
        runtime=runtime,
        model_name=model_name,
        registry=registry,
        approval=approval,
        grc_stage=(
            "shadow"
            if item.role in {"reserve", "artifact_calibration"}
            else "active"
        )
        if item.action == "grc"
        else None,
    )
    record = {
        "schedule": item.as_dict(),
        "attempt": attempt,
        "trace_id": trace_id,
        "manifest_id": manifest.manifest_id,
        "metrics": metrics.as_dict(),
        "oracle": oracle.as_dict(),
        "answer": output,
        "tool_sequence": tool_names,
        "tool_calls": tool_calls,
        "dispatch": (
            {
                **compacting.dispatcher.telemetry.as_dict(),
                "records": list(compacting.shadow_log),
            }
            if compacting
            else {}
        ),
        "action_spec": {**asdict(action_spec), "action_digest": action_spec.digest},
    }
    return record, episode.to_dict()


async def _run(args: argparse.Namespace) -> int:
    protocol = FrozenProtocol.load(args.protocol)
    cases = _cases(args.cases)
    pool_paths = _pairs(args.pool, label="pool")
    runtimes = {
        domain: load_domain_runtime(
            domain=domain, pool_dir=pool_paths[domain], cases=domain_cases, repository_root=ROOT
        )
        for domain, domain_cases in cases.items()
    }
    pricing = _pricing(args.pricing, args.model)
    schedule = _schedule(protocol, cases, phase=args.phase)
    preflight = _preflight(args, protocol, cases, schedule, runtimes, pricing)
    registries = preflight.pop("registries")
    approvals = preflight.pop("approvals")
    policy = preflight.pop("policy")
    unavailable_actions = preflight.pop("unavailable_actions")
    output_dir = args.out
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "preflight.json").write_text(
        json.dumps(preflight, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "schedule.jsonl").write_text(
        "".join(_canonical(item.as_dict()) + "\n" for item in schedule), encoding="utf-8"
    )
    if args.dry_run:
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return 0 if preflight["eligible"] else 2
    if not preflight["eligible"]:
        raise RuntimeError("live run preflight failed; inspect preflight.json")
    load_dotenv(ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        raise RuntimeError("OPENAI_API_KEY is not configured")
    budget = ProviderBudget(args.max_provider_usd)
    ledger = RunLedger(output_dir / "ledger.jsonl")
    previous_records = ledger.records()
    unexpected_runs = sorted(
        {record.run_id for record in previous_records if record.run_id != protocol.digest}
    )
    if unexpected_runs:
        raise RuntimeError("output ledger contains a different frozen protocol")
    started_budget_ids = {
        str(record.payload["budget_event_id"])
        for record in previous_records
        if record.event_type == "execution_started"
    }
    terminal_budget_ids = {
        str(record.payload["budget_event_id"])
        for record in previous_records
        if record.event_type in {"execution_complete", "execution_failed"}
    }
    ambiguous = sorted(started_budget_ids - terminal_budget_ids)
    if ambiguous:
        raise RuntimeError(
            "ledger contains an interrupted provider attempt with unknown billing outcome"
        )
    for previous in previous_records:
        if previous.event_type == "execution_started":
            budget.reserve(
                str(previous.payload["budget_event_id"]),
                float(previous.payload["reserved_usd"]),
            )
        elif previous.event_type == "execution_complete":
            cost = float(previous.payload["metrics"]["estimated_cost_usd"])
            prior_id = str(previous.payload["budget_event_id"])
            if prior_id not in started_budget_ids:
                budget.reserve(prior_id, cost)
            budget.reconcile(prior_id, cost)
        elif previous.event_type == "execution_failed":
            prior_id = str(previous.payload["budget_event_id"])
            if prior_id not in started_budget_ids:
                budget.reserve(
                    prior_id,
                    float(previous.payload.get("reserved_usd", args.reservation_usd_per_execution)),
                )
    from agents import add_trace_processor

    processor = AgentsTraceProcessor(include_sensitive_data=True, max_completed=64)
    add_trace_processor(processor)
    resolved = {
        record.event_id
        for record in ledger.records()
        if record.event_type in {"execution_complete", "execution_unavailable"}
    }
    for item in schedule:
        if item.event_id in resolved:
            continue
        unavailable_reason = unavailable_actions.get((item.domain, item.action))
        if unavailable_reason:
            ledger.append(
                run_id=protocol.digest,
                event_id=item.event_id,
                event_type="execution_unavailable",
                payload={
                    "schedule": item.as_dict(),
                    "reason": unavailable_reason,
                    "provider_calls_executed": 0,
                    "action_lock_digest": preflight["action_lock_digest"],
                    "portfolio_policy_digest": "" if policy is None else policy.digest,
                },
            )
            continue
        success = False
        for attempt in range(args.retries + 1):
            budget_event_id = f"{item.event_id}:a{attempt}"
            budget.reserve(budget_event_id, args.reservation_usd_per_execution)
            ledger.append(
                run_id=protocol.digest,
                event_id=f"{item.event_id}:attempt:{attempt}:started",
                event_type="execution_started",
                payload={
                    "schedule": item.as_dict(),
                    "attempt": attempt,
                    "budget_event_id": budget_event_id,
                    "reserved_usd": args.reservation_usd_per_execution,
                },
            )
            try:
                record, episode = await _execute_one(
                    item=item, attempt=attempt, protocol=protocol, runtime=runtimes[item.domain],
                    model_name=args.model, pricing=pricing, processor=processor,
                    registry=registries.get(item.domain), timeout_s=args.timeout,
                    max_model_requests=args.max_model_requests,
                    approval=approvals.get(item.domain),
                )
                if record["metrics"]["model_requests"] > args.max_model_requests:
                    raise RuntimeError("execution exceeded the frozen model-request limit")
                actual = float(record["metrics"]["estimated_cost_usd"])
                budget.reconcile(budget_event_id, actual)
                episode_text = json.dumps(episode, indent=2, sort_keys=True) + "\n"
                episode_digest = hashlib.sha256(episode_text.encode()).hexdigest()
                episode_path = output_dir / "episodes" / f"{episode_digest}.json"
                episode_path.parent.mkdir(parents=True, exist_ok=True)
                if not episode_path.exists():
                    episode_path.write_text(episode_text, encoding="utf-8")
                record.update(
                    {
                        "budget_event_id": budget_event_id,
                        "reserved_usd": args.reservation_usd_per_execution,
                        "episode_digest": episode_digest,
                        "episode_path": str(episode_path.relative_to(ROOT)),
                        "macro_approval_digest": (
                            approvals[item.domain].digest if item.action == "macro" else ""
                        ),
                        "portfolio_policy_digest": "" if policy is None else policy.digest,
                        "action_lock_digest": preflight["action_lock_digest"],
                    }
                )
                ledger.append(
                    run_id=protocol.digest,
                    event_id=item.event_id,
                    event_type="execution_complete",
                    payload=record,
                )
                success = True
                break
            except Exception as exc:
                ledger.append(
                    run_id=protocol.digest,
                    event_id=f"{item.event_id}:attempt:{attempt}",
                    event_type="execution_failed",
                    payload={
                        "schedule": item.as_dict(),
                        "attempt": attempt,
                        "budget_event_id": budget_event_id,
                        "reserved_usd": args.reservation_usd_per_execution,
                        "error_type": type(exc).__name__,
                        "error_message_redacted": True,
                        "provider_request_count_known": False,
                        "provider_request_may_have_occurred": True,
                    },
                )
        if not success:
            continue
    result = {
        "schema": "agent-compaction-multidomain-run-summary/v1",
        "protocol_digest": protocol.digest,
        "phase": args.phase,
        "ledger": ledger.validate(),
        "budget": budget.as_dict(),
        "scheduled": len(schedule),
        "completed": sum(
            record.event_type == "execution_complete" for record in ledger.records()
        ),
        "unavailable": sum(
            record.event_type == "execution_unavailable" for record in ledger.records()
        ),
        "failed_attempts": sum(
            record.event_type == "execution_failed" for record in ledger.records()
        ),
        "provider_calls_observed_completed": sum(
            int(record.payload["metrics"]["model_requests"])
            for record in ledger.records()
            if record.event_type == "execution_complete"
        ),
        "failed_attempts_with_unknown_provider_requests": sum(
            record.event_type == "execution_failed"
            and not record.payload.get("provider_request_count_known", False)
            for record in ledger.records()
        ),
    }
    result["provider_calls_executed"] = (
        result["provider_calls_observed_completed"]
        if result["failed_attempts_with_unknown_provider_requests"] == 0
        else None
    )
    if args.phase == "pilot":
        result["full_study_cost_projection"] = _pilot_projection(
            ledger.records(), unavailable_actions, tuple(protocol.group_roles)
        )
    (output_dir / "summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["completed"] + result["unavailable"] == result["scheduled"] else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--cases", action="append", required=True, metavar="DOMAIN=JSONL")
    parser.add_argument("--pool", action="append", required=True, metavar="DOMAIN=DIR")
    parser.add_argument(
        "--phase",
        required=True,
        choices=("pilot", "discovery", "development", "artifact-calibration", "portfolio-calibration", "test"),
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--pricing", required=True, type=Path)
    parser.add_argument("--max-provider-usd", required=True, type=float)
    parser.add_argument("--reservation-usd-per-execution", required=True, type=float)
    parser.add_argument("--max-model-requests", type=int, default=8)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--registry", action="append", default=[], metavar="DOMAIN=DIR")
    parser.add_argument("--macro-approval", action="append", default=[], metavar="DOMAIN=JSON")
    parser.add_argument("--policy", type=Path, help="frozen portfolio required for test")
    parser.add_argument(
        "--action-lock",
        type=Path,
        help="provider-free frozen action identities required for pilot/calibration/test",
    )
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.max_provider_usd <= 0 or args.reservation_usd_per_execution <= 0:
        raise SystemExit("provider cap and per-execution reservation must be positive")
    if args.retries < 0 or args.max_model_requests < 1 or args.timeout <= 0:
        raise SystemExit("invalid retry/request/timeout bounds")
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
