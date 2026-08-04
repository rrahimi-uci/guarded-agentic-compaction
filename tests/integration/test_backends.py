"""Integration with the persistence backend and the one framework adapter.

* **JSONL store**: round-trip typed episodes through newline-delimited JSON and assert the
  trace contract survives. This has no third-party dependency, which is the point: if the
  IR could only be reconstructed by calling a vendor SDK, the claim that the compiler's
  input representation is framework-independent would be circular.
* **OpenAI Agents SDK** (proposal §5.6): drive ``CompactingModel`` against a fake wrapped
  model — no API key, no network — and assert the conformance properties: ``off`` is
  byte-identical, a hit emits schema-valid native ``function_call`` items in order,
  reference replay reproduces them, a miss delegates, and handoffs/streaming reject.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from agent_compaction.capture import jsonl
from agent_compaction.grc.dsl import Const, Expr
from agent_compaction.grc.program import CallStep, Program
from agent_compaction.registry.store import Registry
from agent_compaction.runtime.dispatch import DispatchMode
from agent_compaction.runtime.model_provider import CompactingModel, UnsupportedFeature
from agent_compaction.schema.artifacts import Artifact, Gate, GateModel, HardGuard, Lifecycle, Verifier
from agent_compaction.schema.effects import EffectCatalog
from agent_compaction.schema.traces import ExecutionManifest

from scripts.generate_synthetic import SYNTHETIC_CATALOG, generate

# ---------------------------------------------------------------------------
# JSONL store
# ---------------------------------------------------------------------------


def test_jsonl_roundtrip_preserves_the_trace_contract(tmp_path):
    """The IR must survive persistence without any tracing platform present."""

    episodes = generate(n_episodes=6, seed=3)
    path = jsonl.write_jsonl(episodes, tmp_path / "episodes.jsonl")
    back = jsonl.read_jsonl(path)

    assert len(back) == len(episodes)
    for before, after in zip(episodes, back, strict=True):
        assert after.episode_id == before.episode_id
        assert after.group_id == before.group_id
        assert after.entry_state == before.entry_state
        assert after.manifest.compatibility_key() == before.manifest.compatibility_key()
        assert [e.kind for e in after.events] == [e.kind for e in before.events]
        assert [e.tool for e in after.events] == [e.tool for e in before.events]
        assert [e.input for e in after.events] == [e.input for e in before.events]
        assert [e.output for e in after.events] == [e.output for e in before.events]
        assert after.outcome.task_success == before.outcome.task_success
    # A round trip must be idempotent, or replay evidence is not reproducible.
    assert jsonl.write_jsonl(back, tmp_path / "again.jsonl").read_text() == path.read_text()


def test_jsonl_store_needs_no_third_party_import(tmp_path):
    """Guard the framework-independence claim in code, not only in prose."""

    import agent_compaction.capture.jsonl as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    for forbidden in ("import mlflow", "import agents", "import openai"):
        assert forbidden not in source
    assert jsonl.read_jsonl(jsonl.write_jsonl(generate(n_episodes=2, seed=1),
                                              tmp_path / "x.jsonl"))


def test_blank_lines_are_skipped(tmp_path):
    path = tmp_path / "sparse.jsonl"
    jsonl.write_jsonl(generate(n_episodes=2, seed=5), path)
    path.write_text(path.read_text() + "\n\n", encoding="utf-8")
    assert len(jsonl.read_jsonl(path)) == 2


# ---------------------------------------------------------------------------
# OpenAI Agents SDK
# ---------------------------------------------------------------------------

try:  # pragma: no cover - optional extra
    import agents  # noqa: F401

    agents_installed = True
except Exception:  # pragma: no cover
    agents_installed = False


CATALOG = EffectCatalog.from_dict(
    {
        "version": 1,
        "name": "sdk",
        "tools": {
            "acct.get": {
                "effect": "READ_EXTERNAL",
                "capabilities": ["speculatable", "replayable", "cacheable"],
                "resource": "acct",
            },
            "acct.orders": {
                "effect": "READ_EXTERNAL",
                "capabilities": ["speculatable", "replayable", "cacheable"],
                "resource": "acct",
            },
        },
    }
)

MANIFEST = ExecutionManifest(manifest_id="sdk-m", model="sim-model", prompt_hash="#p")


class _FakeModel:
    """Stands in for a provider model: counts calls and records what it saw."""

    def __init__(self) -> None:
        self.calls: list[Any] = []

    async def get_response(self, system_instructions, input, model_settings, tools, output_schema, handoffs, tracing, **kw):
        from agents.items import ModelResponse
        from agents.usage import Usage

        self.calls.append(input)
        return ModelResponse(output=[], usage=Usage(), response_id="fake")

    async def stream_response(self, *args, **kwargs):
        self.calls.append(args[1] if len(args) > 1 else kwargs.get("input"))
        if False:
            yield None


def _sdk_artifact() -> Artifact:
    program = Program(
        theta=("acct_id",),
        steps=[
            CallStep(var="acc", tool="acct.get", args={"acct_id": Expr("z.acct_id", ())}),
            CallStep(
                var="ord",
                tool="acct.orders",
                args={"acct_id": Expr("acc.id", ()), "limit": Const(3)},
            ),
        ],
        outputs={"acc": Expr("acc", ()), "ord": Expr("ord", ())},
        removed_requests=2.0,
        tools=("acct.get", "acct.orders"),
    )
    return Artifact(
        artifact_id="sdk-art",
        name="sdk.region@1",
        program=program,
        guard=HardGuard(manifest_pins={"model": "sim-model"}, isolation={}),
        verifier=Verifier(allowed_effects=("READ_EXTERNAL",)),
        gate=Gate(model=GateModel(bias=-6.0), threshold=0.5),
        manifest=MANIFEST,
        compatibility_key=MANIFEST.compatibility_key(),
        partition={},
        lifecycle=Lifecycle.ACTIVE,
    )


def _model(mode: str) -> tuple[CompactingModel, _FakeModel]:
    reg = Registry(name="sdk")
    reg.add(_sdk_artifact())
    fake = _FakeModel()
    return (
        CompactingModel(
            fake,
            registry=reg,
            catalog=CATALOG,
            manifest=MANIFEST,
            mode=mode,
            entry_state_fn=lambda inp: {"acct_id": "ac_777"},
        ),
        fake,
    )


class _Tool:
    def __init__(self, name: str) -> None:
        self.name = name


TOOLS = [_Tool("acct.get"), _Tool("acct.orders")]


@pytest.mark.agents_sdk
@pytest.mark.skipif(not agents_installed, reason="openai-agents extra not installed")
def test_conformance_1_off_mode_is_byte_identical_and_delegates():
    model, fake = _model(DispatchMode.OFF)
    inp = [{"role": "user", "content": "hello"}]
    asyncio.run(model.get_response(None, inp, None, TOOLS, None, [], None))
    assert len(fake.calls) == 1
    assert fake.calls[0] == inp
    assert model.input_digests == [__import__("agent_compaction").schema.content_digest(inp)]


@pytest.mark.agents_sdk
@pytest.mark.skipif(not agents_installed, reason="openai-agents extra not installed")
def test_conformance_2_and_3_hit_emits_ordered_native_items_reproducibly():
    import json as _json

    outs = []
    for _ in range(2):  # determinism: the same recorded entry reproduces the items
        model, fake = _model(DispatchMode.LIVE)

        async def run_turns():
            first = await model.get_response(None, [], None, TOOLS, None, [], None)
            call = first.output[0]
            history = [
                {"type": "function_call", "name": "acct.get", "call_id": call.call_id, "arguments": call.arguments},
                {"type": "function_call_output", "call_id": call.call_id, "output": _json.dumps({"id": "ac_777", "tier": "std"})},
            ]
            second = await model.get_response(None, history, None, TOOLS, None, [], None)
            return call, second.output[0]

        call, call2 = asyncio.run(run_turns())
        assert fake.calls == []  # no provider call on a hit
        assert call.type == "function_call"
        assert call.name == "acct.get"
        assert _json.loads(call.arguments) == {"acct_id": "ac_777"}
        assert call2.name == "acct.orders"
        assert _json.loads(call2.arguments) == {"acct_id": "ac_777", "limit": 3}
        outs.append((call.name, call.arguments, call2.name, call2.arguments, call.call_id, call2.call_id))
    assert outs[0] == outs[1]


@pytest.mark.agents_sdk
@pytest.mark.skipif(not agents_installed, reason="openai-agents extra not installed")
def test_conformance_4_plan_exhaustion_delegates_to_the_wrapped_model():
    import json as _json

    model, fake = _model(DispatchMode.LIVE)
    async def run_turns():
        first = await model.get_response(None, [], None, TOOLS, None, [], None)
        call = first.output[0]
        history = [
            {"type": "function_call_output", "call_id": call.call_id, "output": _json.dumps({"id": "ac_777"})}
        ]
        second = await model.get_response(None, history, None, TOOLS, None, [], None)
        call2 = second.output[0]
        history2 = history + [
            {"type": "function_call", "name": "acct.get", "call_id": call.call_id, "arguments": call.arguments},
            {"type": "function_call", "name": "acct.orders", "call_id": call2.call_id, "arguments": call2.arguments},
            {"type": "function_call_output", "call_id": call2.call_id, "output": _json.dumps({"orders": []})},
        ]
        await model.get_response(None, history2, None, TOOLS, None, [], None)

    asyncio.run(run_turns())
    assert len(fake.calls) == 1  # the plan finished, so the model was consulted again


@pytest.mark.agents_sdk
@pytest.mark.skipif(not agents_installed, reason="openai-agents extra not installed")
def test_conformance_5_shadow_logs_without_dispatching():
    model, fake = _model(DispatchMode.SHADOW)
    asyncio.run(model.get_response(None, [], None, TOOLS, None, [], None))
    assert len(fake.calls) == 1
    assert model.shadow_log and model.shadow_log[0]["shadow"] is True


@pytest.mark.agents_sdk
@pytest.mark.skipif(not agents_installed, reason="openai-agents extra not installed")
def test_conformance_7_handoffs_and_streaming_bypass_compaction():
    model, fake = _model(DispatchMode.LIVE)

    class _H:
        pass

    asyncio.run(model.get_response(None, [], None, TOOLS, None, [_H()], None))

    async def consume_stream():
        async for _ in model.stream_response(None, [], None, TOOLS, None, [], None):
            pass

    asyncio.run(consume_stream())
    assert len(fake.calls) == 2


@pytest.mark.agents_sdk
@pytest.mark.skipif(not agents_installed, reason="openai-agents extra not installed")
def test_tool_not_exposed_at_the_boundary_fails_closed():
    model, fake = _model(DispatchMode.LIVE)
    asyncio.run(model.get_response(None, [], None, [_Tool("something.else")], None, [], None))
    assert len(fake.calls) == 1  # delegated instead of emitting an unexposed call
