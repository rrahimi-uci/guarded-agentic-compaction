"""Shared runtime for provider-backed demonstration scenarios.

The enterprise services are deterministic local fixtures so a run is safe and
repeatable, but every agent decision and synthesis turn is executed by the real
OpenAI Agents SDK against the configured OpenAI model.  No API credential is ever
copied into a trace or result artifact.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from importlib.metadata import version
from typing import Any, Callable, Iterable, Sequence

from guarded_agentic_compaction.capture.agents_sdk import (
    AgentsTraceProcessor,
    SdkTraceRecord,
    episode_from_agents_trace,
)
from guarded_agentic_compaction.capture.manifests import build_manifest
from guarded_agentic_compaction.schema.effects import EffectCatalog
from guarded_agentic_compaction.schema.traces import (
    Episode,
    ExecutionManifest,
    OutcomeLabels,
    TraceEnvelope,
    content_digest,
)

from .framework import EpisodeSpec, Observation, ToolError, World

__all__ = [
    "LiveHarness",
    "LiveRun",
    "ModelPrice",
    "build_live_catalog",
    "build_live_manifest",
    "make_function_tools",
    "observations_from_trace",
    "safe_tool_name",
    "trace_metrics",
]


@dataclass(frozen=True, slots=True)
class ModelPrice:
    """Standard short-context price per million tokens."""

    input: float
    cached_input: float
    cache_write: float
    output: float


# Official standard short-context prices retrieved 2026-08-02 from
# https://developers.openai.com/api/docs/pricing.  Results identify this as an
# estimate from published list prices, not an invoice or account-specific rate.
MODEL_PRICES: dict[str, ModelPrice] = {
    "gpt-5.6-sol": ModelPrice(5.00, 0.50, 6.25, 30.00),
    "gpt-5.6-terra": ModelPrice(2.00, 0.20, 2.50, 12.00),
    "gpt-5.6-luna": ModelPrice(0.20, 0.02, 0.25, 1.20),
}


TOOL_DESCRIPTIONS: dict[str, str] = {
    "auth.issue_service_token": "Issue a read-only service token. Call this before CRM or billing reads.",
    "crm.find_customer": "Find customer records by normalized email and tenant using a service token.",
    "crm.get_subscription": "Read the subscription for an exact customer identifier.",
    "billing.list_invoices": "List the newest invoices for an exact customer identifier.",
    "entitlements.check": "Check whether a customer is entitled to an exact product feature.",
    "kb.search": "Search the knowledge base. This source is not deterministic.",
    "crm.update_ticket": "Write a resolution to a support ticket. Do not call during evidence gathering.",
    "refunds.issue": "Issue a refund. This is irreversible and requires approval.",
    "support.gather_context": "Gather the complete read-only support evidence bundle in one local operation.",
    "acl.check_scope": "Resolve the corpora this principal and role may access.",
    "index.version": "Read the current search index version.",
    "search.embed": "Create the deterministic retrieval key for a normalized question.",
    "search.retrieve": "Retrieve one ACL-filtered page of document identifiers.",
    "search.rerank": "Rerank retrieved document identifiers for a normalized query.",
    "docs.fetch_metadata": "Read metadata for the ranked document identifiers.",
    "docs.fetch_body": "Read a document body and create an access-audit record.",
    "web.search": "Search an external source outside the permissioned corpus.",
    "search.answer_context": "Build the complete ACL-filtered answer context using local read-only operations.",
    "alerts.get": "Read one alert by its exact alert identifier.",
    "logs.query": "Read recent service log evidence.",
    "deploys.recent": "Read recent deployments for a service.",
    "metrics.query": "Read a named service metric.",
    "runbooks.lookup": "Read the runbook for a service and symptom.",
    "approvals.request": "Request human approval for a remediation action.",
    "remediation.execute": "Execute an approved remediation. Never call without approval.",
    "case.add_note": "Write an incident note.",
    "triage.evidence_bundle": "Gather the route-specific read-only incident evidence bundle.",
    "auth.issue_ops_token": "Issue a read-only fulfillment operations token. Call this first.",
    "orders.get": "Read one order, its warehouse, tracking id and line items.",
    "shipments.list_page": (
        "Read one page of shipments for an order. Pages are zero-indexed and hold at "
        "most three shipments; the response reports has_more."
    ),
    "inventory.check": "Read available stock for an exact sku in an exact warehouse.",
    "carrier.track": "Read the carrier scan and estimated days to delivery for a tracking id.",
    "sla.policy": "Read the local service policy for a customer tier and region.",
    "risk.score": (
        "Advisory fraud score. The ensemble is non-deterministic and must never be "
        "used as evidence for a fulfillment decision."
    ),
    "orders.reschedule": "Commit a new delivery date for an order. Irreversible.",
    "case.escalate": "Commit an escalation of the exception case to a queue. Irreversible.",
    "refunds.issue_credit": "Issue an account credit. Irreversible and requires approval.",
    "fulfillment.evidence_bundle": "Gather the complete read-only fulfillment evidence bundle.",
}


def safe_tool_name(name: str) -> str:
    """Map catalog names to the function-name alphabet accepted by the API."""

    value = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
    if not value:
        raise ValueError(f"tool name has no safe representation: {name!r}")
    return value


def make_function_tools(
    world: World,
    names: Iterable[str],
) -> tuple[list[Any], dict[str, str]]:
    """Expose local fixture services as genuine Agents SDK function tools.

    Outputs are JSON strings rather than Python reprs.  That preserves typed tool
    results when :class:`CompactingModel` reconstructs dependencies between native
    function-call turns.
    """

    try:
        from agents import FunctionTool, function_tool
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("install the 'agents' extra to run live demonstrations") from exc

    tools: list[Any] = []
    aliases: dict[str, str] = {}
    for original in names:
        spec = world.tools[original]
        safe = safe_tool_name(original)
        template = function_tool(
            spec.fn,
            name_override=safe,
            description_override=TOOL_DESCRIPTIONS.get(
                original, f"Execute the local benchmark service operation {original}."
            ),
        )

        async def invoke(_context: Any, args_json: str, *, _name: str = original) -> str:
            try:
                args = json.loads(args_json or "{}")
                result = world.execute(_name, args)
                return json.dumps(result, sort_keys=True, default=str)
            except ToolError as exc:
                return json.dumps(
                    {"error": str(exc), "status": exc.status}, sort_keys=True
                )

        tools.append(
            FunctionTool(
                name=safe,
                description=template.description,
                params_json_schema=template.params_json_schema,
                on_invoke_tool=invoke,
                strict_json_schema=True,
            )
        )
        aliases[safe] = original
    return tools, aliases


def build_live_catalog(
    source: EffectCatalog,
    names: Iterable[str],
    *,
    name: str,
) -> EffectCatalog:
    """Create the runtime catalog over API-safe tool identifiers."""

    tools: dict[str, Any] = {}
    for original in names:
        payload = source.get(original).model_dump(mode="json")
        payload.pop("tool", None)
        tools[safe_tool_name(original)] = payload
    return EffectCatalog.from_dict({"version": source.version, "name": name, "tools": tools})


def build_live_manifest(
    *,
    model: str,
    prompt: str,
    tools: Iterable[Any],
    catalog: EffectCatalog,
    entry_contract_version: str,
    condition: str,
) -> ExecutionManifest:
    return build_manifest(
        commit="live-demo-2026-08-02",
        model=model,
        prompt=prompt,
        tools=tools,
        policy=f"openai-agents-sdk:{condition}",
        guardrails="read-only fixture services; irreversible tools excluded",
        catalog=catalog,
        entry_contract_version=entry_contract_version,
        sdk_version=version("openai-agents"),
    )


def _json_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def observations_from_trace(
    trace: SdkTraceRecord,
    aliases: dict[str, str],
) -> list[Observation]:
    out: list[Observation] = []
    for span in trace.spans:
        data = span.data
        if data.get("type") != "function":
            continue
        safe = str(data.get("name") or "")
        args = _json_value(data.get("input"))
        result = _json_value(data.get("output"))
        if not isinstance(args, dict):
            args = {}
        status = "error" if span.error or (isinstance(result, dict) and "error" in result) else "ok"
        out.append(Observation(aliases.get(safe, safe), args, result, status))
    return out


def trace_metrics(trace: SdkTraceRecord, *, model: str, wall_ms: float) -> dict[str, Any]:
    requests = 0
    tool_calls = 0
    handoffs = 0
    input_tokens = 0
    cached_tokens = 0
    cache_write_tokens = 0
    output_tokens = 0
    response_latency_ms = 0.0
    for span in trace.spans:
        kind = str(span.data.get("type") or "")
        if kind in {"generation", "response"}:
            requests += 1
            usage = span.data.get("usage") or {}
            details = usage.get("input_tokens_details") or {}
            input_tokens += int(usage.get("input_tokens", 0) or 0)
            cached_tokens += int(details.get("cached_tokens", 0) or 0)
            cache_write_tokens += int(details.get("cache_write_tokens", 0) or 0)
            output_tokens += int(usage.get("output_tokens", 0) or 0)
            response_latency_ms += _duration_ms(span.started_at, span.ended_at)
        elif kind == "function":
            tool_calls += 1
        elif kind == "handoff":
            handoffs += 1

    price = MODEL_PRICES.get(model)
    estimated_cost = None
    if price is not None:
        ordinary = max(0, input_tokens - cached_tokens - cache_write_tokens)
        estimated_cost = (
            ordinary * price.input
            + cached_tokens * price.cached_input
            + cache_write_tokens * price.cache_write
            + output_tokens * price.output
        ) / 1_000_000
    return {
        "requests": requests,
        "tool_calls": tool_calls,
        "handoffs": handoffs,
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_tokens,
        "cache_write_tokens": cache_write_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "wall_latency_ms": round(wall_ms, 3),
        "provider_response_latency_ms": round(response_latency_ms, 3),
        "estimated_cost_usd": round(estimated_cost, 8) if estimated_cost is not None else None,
    }


def _duration_ms(started_at: str | None, ended_at: str | None) -> float:
    if not started_at or not ended_at:
        return 0.0
    from datetime import datetime

    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        end = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
        return max(0.0, (end - start).total_seconds() * 1000.0)
    except ValueError:
        return 0.0


@dataclass(slots=True)
class LiveRun:
    demo: str
    condition: str
    scenario_id: str
    trace_id: str
    model: str
    metrics: dict[str, Any]
    outcome: OutcomeLabels
    answer: dict[str, Any]
    expected: dict[str, Any]
    manifest_id: str
    dispatch: dict[str, Any]
    episode: Episode

    def result_dict(self) -> dict[str, Any]:
        return {
            "demo": self.demo,
            "condition": self.condition,
            "scenario_id": self.scenario_id,
            "trace_id": self.trace_id,
            "model": self.model,
            "metrics": self.metrics,
            "outcome": asdict(self.outcome),
            "answer": self.answer,
            "expected": self.expected,
            "manifest_id": self.manifest_id,
            "dispatch": self.dispatch,
            "episode_digest": content_digest(self.episode.to_dict()),
        }


class LiveHarness:
    """Run Agents SDK workflows and join native traces with application labels."""

    def __init__(self) -> None:
        try:
            from agents import add_trace_processor
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("install the 'agents' extra to run live demonstrations") from exc
        self.processor = AgentsTraceProcessor(include_sensitive_data=True, max_completed=256)
        add_trace_processor(self.processor)

    async def run(
        self,
        *,
        demo: str,
        condition: str,
        model: str,
        agent: Any,
        user_input: str,
        spec: EpisodeSpec,
        world: World | None,
        manifest: ExecutionManifest,
        aliases: dict[str, str],
        expected: dict[str, Any],
        grade: Callable[[list[Observation], dict[str, Any]], OutcomeLabels],
        dispatch: Callable[[], dict[str, Any]] | None = None,
        max_turns: int = 16,
    ) -> LiveRun:
        from agents import RunConfig, Runner

        started = time.perf_counter()
        result = await Runner.run(
            agent,
            user_input,
            max_turns=max_turns,
            run_config=RunConfig(
                workflow_name=f"agent-compaction-live:{demo}:{condition}",
                group_id=spec.group_id,
                trace_include_sensitive_data=True,
                trace_metadata={
                    "demo": demo,
                    "condition": condition,
                    "scenario_id": spec.episode_id,
                    "fixture_data": "true",
                    "provider_backed": "true",
                },
            ),
        )
        wall_ms = (time.perf_counter() - started) * 1000.0
        records = self.processor.drain()
        if len(records) != 1:
            raise RuntimeError(
                f"expected one completed SDK trace for {spec.episode_id}, got {len(records)}"
            )
        trace = records[0]
        answer = _answer_dict(result.final_output)
        observations = observations_from_trace(trace, aliases)
        outcome = grade(observations, answer)
        envelope = TraceEnvelope(
            trace_id=trace.trace_id,
            episode_id=f"{spec.episode_id}:{condition}",
            group_id=spec.group_id,
            manifest_id=manifest.manifest_id,
            principal=spec.principal,
            tenant_partition=spec.tenant_partition,
            policy_version=spec.policy_version,
            day=spec.day,
            privacy_class="fictional_fixture",
            entry_state_ref=content_digest(spec.entry_state),
            external_state_version=spec.external_state_version,
        )
        episode = episode_from_agents_trace(
            trace,
            envelope=envelope,
            manifest=manifest,
            entry_state=spec.entry_state,
            outcome=outcome,
            final_state_digest=world.state_digest() if world is not None else "read-only-mcp",
            tool_aliases=aliases,
        )
        metrics = trace_metrics(trace, model=model, wall_ms=wall_ms)
        episode.attributes.update(
            {
                "answer": answer,
                "condition": condition,
                "dollars": metrics["estimated_cost_usd"] or 0.0,
                "model": model,
                "provider": "openai",
                "substrate": "openai_api_live",
                "wall_latency_ms": metrics["wall_latency_ms"],
                "pricing_source": "https://developers.openai.com/api/docs/pricing",
                "pricing_as_of": "2026-08-02",
            }
        )
        return LiveRun(
            demo=demo,
            condition=condition,
            scenario_id=spec.episode_id,
            trace_id=trace.trace_id,
            model=model,
            metrics=metrics,
            outcome=outcome,
            answer=answer,
            expected=expected,
            manifest_id=manifest.manifest_id,
            dispatch=dispatch() if dispatch else {},
            episode=episode,
        )


def _answer_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return dict(value.model_dump())
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        parsed = _json_value(value)
        return dict(parsed) if isinstance(parsed, dict) else {"text": value}
    return {"value": str(value)}
