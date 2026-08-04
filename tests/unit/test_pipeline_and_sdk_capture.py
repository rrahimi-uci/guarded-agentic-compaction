from __future__ import annotations

from dataclasses import dataclass

import pytest

from agent_compaction.capture.agents_sdk import (
    AgentsTraceProcessor,
    episode_from_agents_trace,
)
from agent_compaction.capture.manifests import build_manifest
from agent_compaction.evaluation.splits import Splits
from agent_compaction.paths import resolve_path, stable_int
from agent_compaction.pipeline import (
    FunctionPass,
    OptimizationContext,
    OptimizationPipeline,
    PassResult,
    PassStatus,
    PipelineConfigurationError,
)
from agent_compaction.schema.effects import EffectCatalog
from agent_compaction.schema.traces import ExecutionManifest, OutcomeLabels, TraceEnvelope


CATALOG = EffectCatalog.from_dict(
    {
        "name": "capture",
        "tools": {
            "acct.get": {
                "effect": "READ_EXTERNAL",
                "capabilities": ["speculatable", "replayable"],
            }
        },
    }
)
MANIFEST = ExecutionManifest(
    manifest_id="m",
    model="test",
    effect_catalog_version=CATALOG.catalog_version,
)


def test_pipeline_checks_capabilities_and_preserves_order():
    context = OptimizationContext([], CATALOG, MANIFEST, Splits())

    def analyze(ctx):
        ctx.state["graph"] = "ready"
        return PassResult("analyze", PassStatus.APPLIED, provides=frozenset({"graph"}))

    def optimize(ctx):
        assert ctx.state["graph"] == "ready"
        return PassResult("optimize", PassStatus.ABSTAINED, notes=("no safe rewrite",))

    report = OptimizationPipeline(
        [
            FunctionPass("analyze", analyze),
            FunctionPass("optimize", optimize, requires=frozenset({"graph"})),
        ]
    ).run(context)
    assert [result.name for result in report.results] == ["analyze", "optimize"]
    assert "graph" in report.capabilities

    with pytest.raises(PipelineConfigurationError):
        OptimizationPipeline(
            [FunctionPass("bad", optimize, requires=frozenset({"missing"}))]
        ).run(context)


def test_path_resolution_and_stable_identity_fail_closed():
    payload = {"items": [{"id": "a"}]}
    assert resolve_path(payload, "items[0].id") == "a"
    assert resolve_path(payload, "items[-1].id") is None
    assert resolve_path(payload, "items[broken].id") is None
    assert resolve_path(payload, "items[0.id") is None
    assert stable_int({"b": 2, "a": 1}) == stable_int({"a": 1, "b": 2})


def test_manifest_identity_is_unambiguous_and_covers_compatibility_inputs():
    common = {
        "prompt": "p",
        "tools": [{"name": "acct.get", "schema": {"type": "object"}}],
        "policy": "policy",
        "guardrails": "guard",
        "catalog": CATALOG,
        "entry_contract_version": "v1",
    }
    left = build_manifest(commit="a|b", model="c", **common)
    right = build_manifest(commit="a", model="b|c", **common)
    assert left.manifest_id != right.manifest_id

    changed_tools = build_manifest(
        commit="a|b",
        model="c",
        **{**common, "tools": [{"name": "acct.get", "schema": {"type": "string"}}]},
    )
    assert left.manifest_id != changed_tools.manifest_id


@dataclass
class _Trace:
    trace_id: str = "trace_1"
    name: str = "support"
    group_id: str = "conversation_1"
    metadata: dict | None = None


class _Data:
    def __init__(self, payload):
        self.payload = payload
        self.input = payload.get("input")
        self.output = payload.get("output")

    def export(self):
        return dict(self.payload)


@dataclass
class _Span:
    span_id: str
    span_data: _Data
    trace_id: str = "trace_1"
    parent_id: str | None = None
    started_at: str = "2026-08-02T00:00:00+00:00"
    ended_at: str = "2026-08-02T00:00:00.010000+00:00"
    error: object | None = None


def test_agents_processor_collects_and_normalizes_native_spans():
    processor = AgentsTraceProcessor(include_sensitive_data=True)
    trace = _Trace(metadata={"environment": "test"})
    processor.on_trace_start(trace)
    processor.on_span_end(
        _Span(
            "generation_1",
            _Data(
                {
                    "type": "generation",
                    "input": [{"role": "user", "content": "lookup"}],
                    "output": [{"type": "function_call"}],
                    "usage": {"input_tokens": 10, "output_tokens": 3},
                }
            ),
        )
    )
    processor.on_span_end(
        _Span(
            "function_1",
            _Data(
                {
                    "type": "function",
                    "name": "acct.get",
                    "input": '{"acct_id":"a1"}',
                    "output": {"id": "a1"},
                }
            ),
        )
    )
    processor.on_trace_end(trace)
    records = processor.drain()
    assert len(records) == 1

    episode = episode_from_agents_trace(
        records[0],
        envelope=TraceEnvelope(
            trace_id="pending",
            episode_id="e1",
            group_id="g1",
            manifest_id="pending",
        ),
        manifest=MANIFEST,
        entry_state={"acct_id": "a1"},
        outcome=OutcomeLabels(task_success=True),
        tool_aliases={"acct.get": "accounts.get"},
    )
    assert episode.n_requests() == 1
    assert episode.tool_calls()[0].tool == "accounts.get"
    assert episode.tool_calls()[0].input == {"acct_id": "a1"}
    assert episode.usage().input_tokens == 10
    assert episode.envelope.trace_id == "trace_1"


def test_agents_processor_redacts_payloads_by_default():
    processor = AgentsTraceProcessor()
    trace = _Trace()
    processor.on_trace_start(trace)
    processor.on_span_end(
        _Span(
            "function_1",
            _Data(
                {
                    "type": "function",
                    "name": "acct.get",
                    "input": '{"secret":"value"}',
                    "output": {"secret": "value"},
                }
            ),
        )
    )
    processor.on_trace_end(trace)
    span = processor.drain()[0].spans[0]
    assert span.data["input"] is None
    assert span.data["output"] is None


def test_agents_processor_rejects_an_accidentally_unbounded_completed_queue():
    with pytest.raises(ValueError, match="max_completed"):
        AgentsTraceProcessor(max_completed=0)


def test_agents_processor_reports_queue_and_shutdown_loss():
    processor = AgentsTraceProcessor(max_completed=1)

    first = _Trace(trace_id="trace_1")
    processor.on_trace_start(first)
    processor.on_trace_end(first)

    second = _Trace(trace_id="trace_2")
    processor.on_trace_start(second)
    processor.on_trace_end(second)
    assert processor.dropped == 1

    incomplete = _Trace(trace_id="trace_3")
    processor.on_trace_start(incomplete)
    processor.shutdown()
    assert processor.dropped == 2

    # Shutdown does not destroy records that completed before it was called.
    assert [record.trace_id for record in processor.drain()] == ["trace_1"]
