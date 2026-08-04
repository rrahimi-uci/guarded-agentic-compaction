"""``CompactingModel``: the OpenAI Agents SDK integration path (proposal §5.6).

The wrapper returns a deterministic ``ModelResponse`` carrying the artifact's next
synthesized ``function_call`` on a hit and delegates to the wrapped model on a miss.
The ordinary ``Runner`` then executes the tool and returns the result, so SDK tool
dispatch, tracing and usage attribution are preserved while the provider call
disappears.

This is **not equivalent by construction**, and the limitation is structural rather
than an implementation gap: once the wrapper has emitted a ``ModelResponse`` the
Runner may already have committed it to session history, and the ``Model`` interface
alone cannot erase that. Exact post-emission deoptimization requires a staging owner
in an outer controller — which is why
:class:`~agent_compaction.runtime.runner.CompactingRunner` is the recommended path and
this one ships behind the conformance tests of §5.6:

1. ``mode="off"`` produces byte-identical input at the next provider call;
2. an accepted execution emits schema-valid native items (tool identity, typed
   arguments, ordering, continuation);
3. deterministic reference replay of the same recorded entry reproduces the items;
4. a rejected pre-emission attempt restores identical model-visible input;
5. usage, errors and tracing stay attributable;
6. multi-turn history strategies pass;
7. streaming, hosted tools, handoffs, loops and assertions reject *compaction*
   and transparently use the wrapped baseline model.

The adapter is intentionally narrower than the outer ``CompactingRunner``. It only
compacts straight-line local function-tool programs. Everything else fails closed to
the baseline workflow without making the Agents SDK application unavailable.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
import threading
from typing import Any, Sequence

from ..paths import content_digest, stable_int
from ..registry.store import Registry
from ..schema.artifacts import Artifact, DispatchOutcome
from ..schema.effects import EffectCatalog
from ..schema.traces import ExecutionManifest
from .dispatch import DispatchMode, Dispatcher

__all__ = ["ArtifactPlan", "CompactingModel", "UnsupportedFeature"]


try:  # Keep the Agents SDK an optional dependency for the compiler core.
    from agents.models.interface import Model as _AgentsModel
except ImportError:  # pragma: no cover - exercised in core-only installations
    class _AgentsModel:  # type: ignore[no-redef]
        """Fallback base when the optional OpenAI Agents SDK is not installed."""

        pass


class UnsupportedFeature(Exception):
    """Retained for compatibility; unsupported features now bypass compaction."""


@dataclass(slots=True)
class ArtifactPlan:
    """State machine over an artifact's call sequence.

    One emitted ``function_call`` per model boundary: the SDK executes it and the next
    boundary advances the plan. Arguments are re-evaluated against the *observed*
    results, so a mid-plan mismatch abandons the plan instead of guessing.
    """

    artifact: Artifact
    entry_state: dict[str, Any]
    env: dict[str, Any] = field(default_factory=dict)
    step_index: int = 0
    finished: bool = False
    aborted: str = ""
    pending_var: str = ""
    pending_call_id: str = ""
    calls: list[str] = field(default_factory=list)
    provenance: dict[str, set[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.env = {"z": self.entry_state}

    def active(self) -> bool:
        return not self.finished and not self.aborted

    def steps(self) -> list[Any]:
        return list(self.artifact.program.steps if self.artifact.program else [])

    def next_call(self) -> tuple[str, dict[str, Any], int] | None:
        """The next tool call, or ``None`` when the plan is complete."""

        from ..grc.program import CallStep
        from ..runtime.interp import _eval_args

        steps = self.steps()
        while self.step_index < len(steps):
            step = steps[self.step_index]
            self.step_index += 1
            if not isinstance(step, CallStep):
                self.aborted = f"unsupported_step:{type(step).__name__}"
                return None
            if step.when is not None and not step.when.evaluate(self.env):
                self.env[step.var] = None
                continue
            try:
                args = _eval_args(step.args, self.env)
            except Exception as exc:  # binding failed: abandon, do not guess
                self.aborted = f"binding_failed:{exc}"
                return None
            self.pending_var = step.var
            return step.tool, args, self.step_index - 1
        self.finished = True
        return None

    def observe(self, var: str, result: Any) -> None:
        self.env[var] = result
        if self.step_index:
            step = self.steps()[self.step_index - 1]
            self.calls.append(step.tool)
            self.provenance[var] = {step.tool}
        self.pending_var = ""
        self.pending_call_id = ""

    def verify(self, catalog: EffectCatalog) -> list[str]:
        """Evaluate live-outs and the artifact verifier after the final tool result."""

        program = self.artifact.program
        if program is None:
            return ["no_program"]
        outputs: dict[str, Any] = {}
        for name, binding in program.outputs.items():
            try:
                outputs[name] = binding.evaluate(self.env)
            except Exception:
                outputs[name] = None
        effects = tuple(sorted(catalog.effect_of(tool).value for tool in self.calls))
        return self.artifact.verifier.verify(
            outputs,
            self.env,
            self.provenance,
            effects,
            len(self.calls),
        )


class CompactingModel(_AgentsModel):
    """Wraps an Agents SDK ``Model``.

    Kept import-light on purpose: the class is usable (and testable) without the SDK
    installed, and only imports ``agents`` when it has to build a response.
    """

    def __init__(
        self,
        wrapped: Any,
        *,
        registry: Registry,
        catalog: EffectCatalog,
        manifest: ExecutionManifest,
        mode: str = DispatchMode.SHADOW,
        entry_state_fn: Any = None,
        partition: dict[str, str] | None = None,
        partition_fn: Any = None,
        context_fn: Any = None,
        allow_streaming: bool = False,
    ) -> None:
        self._wrapped = wrapped
        self._registry = registry
        self._catalog = catalog
        self._manifest = manifest
        self.mode = mode
        self._entry_state_fn = entry_state_fn
        self._partition = partition or {}
        self._partition_fn = partition_fn
        self._context_fn = context_fn
        self._allow_streaming = allow_streaming
        self._plan_var: ContextVar[ArtifactPlan | None] = ContextVar(
            f"agent_compaction_plan_{id(self)}", default=None
        )
        # The SDK may invoke successive model turns in sibling asyncio contexts.
        # A ContextVar alone therefore loses the plan between real Runner turns even
        # though direct conformance tests call the methods in one task.  Native SDK
        # traces provide a stable per-run identity, so retain in-flight plans by
        # trace id and use the ContextVar only for direct/non-SDK callers.
        self._plans_by_run: dict[str, ArtifactPlan] = {}
        self._plans_lock = threading.RLock()
        self.dispatcher = Dispatcher(registry=registry, catalog=catalog, mode=mode)
        self.shadow_log: list[dict[str, Any]] = []
        self.input_digests: list[str] = []

    # -- SDK surface -------------------------------------------------------
    async def get_response(
        self,
        system_instructions: str | None,
        input: Any,
        model_settings: Any,
        tools: Sequence[Any],
        output_schema: Any,
        handoffs: Sequence[Any],
        tracing: Any,
        **kwargs: Any,
    ) -> Any:
        self.input_digests.append(content_digest(_input_repr(input)))

        # Handoffs and server-managed continuation can omit the local history the
        # adapter needs to verify a multi-call plan. Bypass compaction while keeping
        # the baseline Agents SDK workflow fully available.
        server_managed = bool(kwargs.get("previous_response_id") or kwargs.get("conversation_id"))
        if self.mode == DispatchMode.OFF or handoffs or server_managed:
            return await self._wrapped.get_response(
                system_instructions, input, model_settings, tools, output_schema, handoffs, tracing, **kwargs
            )

        run_key = _current_trace_id()
        plan = self._get_plan(run_key)
        if plan is not None and plan.active():
            response = self._advance(plan, input, tools)
            if response is not None:
                return response
            if plan.finished:
                bad = plan.verify(self._catalog)
                if bad:
                    plan.aborted = "verifier:" + bad[0]
                    self.dispatcher.telemetry.bump(
                        self.dispatcher.telemetry.verifier_failures, bad[0].split(":")[0]
                    )
                    self.dispatcher.telemetry.baseline += 1
                else:
                    self.dispatcher.telemetry.compacted += 1
                    self.dispatcher.telemetry.removed_requests += plan.artifact.evidence.removed_requests
            else:
                self.dispatcher.telemetry.bump(
                    self.dispatcher.telemetry.interp_failures,
                    (plan.aborted or "plan_aborted").split(":")[0],
                )
                self.dispatcher.telemetry.baseline += 1
            self._set_plan(run_key, None)

        elif plan is not None:
            self._set_plan(run_key, None)

        entry_state = self._entry_state(input)
        partition = self._runtime_partition(input, entry_state)
        runtime_context = {
            "model": self._manifest.model,
            "prompt_hash": self._manifest.prompt_hash,
            "tools_hash": self._manifest.tools_hash,
            "policy_hash": self._manifest.policy_hash,
            "guardrail_hash": self._manifest.guardrail_hash,
            "effect_catalog_version": self._catalog.catalog_version,
            "entry_contract_version": self._manifest.entry_contract_version,
            "day": str(entry_state.get("day", "")),
            **partition,
        }
        if self._context_fn is not None:
            runtime_context.update(dict(self._context_fn(input, entry_state)))
        decision = self.dispatcher.decide(
            compatibility_key=self._manifest.compatibility_key(),
            partition=partition,
            entry_state=entry_state,
            context=runtime_context,
            executor=None,  # the SDK Runner executes the tools, not the facade
            recording=None,
            # A region that already ran in this conversation must not be dispatched
            # again: its live-ins are no longer the ones the contract was fitted on.
            already_observed=_observed_tools(input),
            defer_execution=True,
        )
        if decision.artifact is not None:
            self.shadow_log.append(decision.record)
        if (
            self.mode != DispatchMode.LIVE
            or decision.artifact is None
            or not _model_program_supported(decision.artifact)
        ):
            return await self._wrapped.get_response(
                system_instructions, input, model_settings, tools, output_schema, handoffs, tracing, **kwargs
            )

        plan = ArtifactPlan(decision.artifact, entry_state)
        self._set_plan(run_key, plan)
        self.dispatcher.telemetry.dispatch_attempts += 1
        response = self._emit_next(plan, tools)
        if response is None:
            self._set_plan(run_key, None)
            self.dispatcher.telemetry.baseline += 1
            return await self._wrapped.get_response(
                system_instructions, input, model_settings, tools, output_schema, handoffs, tracing, **kwargs
            )
        return response

    def stream_response(self, *args: Any, **kwargs: Any) -> Any:
        """Streaming bypasses compaction and preserves the wrapped model contract."""

        return self._wrapped.stream_response(*args, **kwargs)

    async def close(self) -> None:
        """Release resources owned by the wrapped SDK model, when supported."""

        close = getattr(self._wrapped, "close", None)
        if close is not None:
            await close()

    def get_retry_advice(self, request: Any) -> Any:
        """Preserve provider-specific retry guidance through the wrapper."""

        get_retry_advice = getattr(self._wrapped, "get_retry_advice", None)
        return get_retry_advice(request) if get_retry_advice is not None else None

    async def _cleanup_on_run_end(self, owner: object) -> None:
        self._set_plan(_current_trace_id(), None)
        cleanup = getattr(self._wrapped, "_cleanup_on_run_end", None)
        if cleanup is not None:
            await cleanup(owner)

    def _get_plan(self, run_key: str | None) -> ArtifactPlan | None:
        if run_key is None:
            return self._plan_var.get()
        with self._plans_lock:
            return self._plans_by_run.get(run_key)

    def _set_plan(self, run_key: str | None, plan: ArtifactPlan | None) -> None:
        if run_key is None:
            self._plan_var.set(plan)
            return
        with self._plans_lock:
            if plan is None:
                self._plans_by_run.pop(run_key, None)
            else:
                self._plans_by_run[run_key] = plan

    # -- internals ---------------------------------------------------------
    def _entry_state(self, input: Any) -> dict[str, Any]:
        if self._entry_state_fn is not None:
            return dict(self._entry_state_fn(input))
        if isinstance(input, dict):
            return dict(input)
        return {"input": _input_repr(input)}

    def _runtime_partition(self, input: Any, entry_state: dict[str, Any]) -> dict[str, str]:
        if self._partition_fn is not None:
            return {k: str(v) for k, v in dict(self._partition_fn(input, entry_state)).items()}
        if self._partition:
            return dict(self._partition)
        mapping = {
            "tenant_partition": entry_state.get("tenant_partition", entry_state.get("tenant_id")),
            "principal": entry_state.get("principal"),
            "policy_version": entry_state.get("policy_version"),
        }
        return {key: str(value) for key, value in mapping.items() if value is not None}

    def _advance(self, plan: ArtifactPlan, input: Any, tools: Sequence[Any]) -> Any | None:
        """Feed the last tool result back into the plan and emit the next call."""

        found, result = _tool_result(input, plan.pending_call_id)
        if plan.pending_var and not found:
            plan.aborted = "missing_tool_result"
            return None
        if plan.pending_var:
            plan.observe(plan.pending_var, result)
        return self._emit_next(plan, tools)

    def _emit_next(self, plan: ArtifactPlan, tools: Sequence[Any]) -> Any | None:
        nxt = plan.next_call()
        if nxt is None:
            return None
        tool, args, step_index = nxt
        names = _local_tool_names(tools)
        if tool not in names:
            # the tool the artifact needs is not exposed at this boundary: fail closed
            plan.aborted = f"tool_not_exposed:{tool}"
            return None
        response = _function_call_response(
            tool,
            args,
            nonce=f"{plan.artifact.artifact_id}:{step_index}",
        )
        plan.pending_call_id = response.output[0].call_id
        return response


def _input_repr(input: Any) -> Any:
    if isinstance(input, str):
        return input
    try:
        return [dict(item) if isinstance(item, dict) else str(item) for item in input]
    except TypeError:  # pragma: no cover - defensive
        return str(input)


def _current_trace_id() -> str | None:
    """Return the Agents SDK run trace id without requiring the optional SDK."""

    try:
        from agents.tracing import get_current_trace

        trace = get_current_trace()
        value = getattr(trace, "trace_id", None)
        return str(value) if value else None
    except ImportError:  # pragma: no cover - core-only installation
        return None


def _observed_tools(input: Any) -> tuple[str, ...]:
    """Tools already called in this conversation, read from the native history items."""

    if isinstance(input, str) or input is None:
        return ()
    out: list[str] = []
    for item in input:
        if isinstance(item, dict) and item.get("type") == "function_call":
            name = item.get("name")
            if isinstance(name, str):
                out.append(name)
    return tuple(dict.fromkeys(out))


def _tool_result(input: Any, call_id: str) -> tuple[bool, Any]:
    if isinstance(input, str) or input is None:
        return False, None
    import json

    for item in reversed(list(input)):
        if (
            isinstance(item, dict)
            and item.get("type") == "function_call_output"
            and (not call_id or item.get("call_id") == call_id)
        ):
            raw = item.get("output")
            if isinstance(raw, str):
                try:
                    return True, json.loads(raw)
                except json.JSONDecodeError:
                    return True, raw
            return True, raw
    return False, None


def _function_call_response(tool: str, args: dict[str, Any], *, nonce: str = "") -> Any:
    """Build a ``ModelResponse`` carrying one ``function_call`` output item."""

    import json

    from agents.items import ModelResponse
    from agents.usage import Usage
    from openai.types.responses import ResponseFunctionToolCall

    identity = {"tool": tool, "args": args, "nonce": nonce}
    call = ResponseFunctionToolCall(
        id=f"fc_{stable_int(('item', identity), bits=64):016x}",
        call_id=f"call_{stable_int(('call', identity), bits=64):016x}",
        name=tool,
        arguments=json.dumps(args, default=str),
        type="function_call",
    )
    return ModelResponse(output=[call], usage=Usage(), response_id=None)


def _model_program_supported(artifact: Artifact) -> bool:
    """The Model adapter supports straight-line call programs only."""

    from ..grc.program import CallStep

    program = artifact.program
    return bool(program and program.steps and all(isinstance(step, CallStep) for step in program.steps))


def _local_tool_names(tools: Sequence[Any]) -> set[str | None]:
    """Exclude known hosted/MCP tool surfaces from transparent compaction."""

    out: set[str | None] = set()
    for tool in tools:
        kind = type(tool).__name__.lower()
        if any(marker in kind for marker in ("hosted", "mcp", "websearch", "filesearch", "computer")):
            continue
        out.add(getattr(tool, "name", None))
    return out
