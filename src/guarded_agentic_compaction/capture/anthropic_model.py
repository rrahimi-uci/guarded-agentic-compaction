"""Anthropic Messages API backend for the OpenAI Agents SDK ``Model`` interface.

The paper's live harness drives every agent through ``agents.Runner``. This module
lets the same harness run on Claude through the official ``anthropic`` SDK (1.x),
without LiteLLM or an OpenAI-compatible shim. Mapping decisions, in one place:

* ``system_instructions`` -> the top-level ``system`` string. System/developer input
  items (the harness never emits them) are appended to that string, because the
  Messages API has no positional system role.
* Input items (OpenAI Responses format) -> ``messages``: plain string and ``message``
  items become text blocks; ``function_call`` -> ``tool_use`` (arguments parsed with
  ``json``); ``function_call_output`` -> ``tool_result`` inside a ``user`` message;
  a ``reasoning`` item produced by this model replays its Anthropic thinking blocks
  verbatim at the front of the following assistant message (the API requires blocks
  to be passed back unchanged; blocks are never fabricated for synthetic turns).
* ``FunctionTool`` -> ``{"name", "description", "input_schema", "strict": true}``
  when the tool is strict. ``model_settings.parallel_tool_calls is False`` ->
  ``tool_choice={"type": "auto", "disable_parallel_tool_use": True}``.
* ``output_schema`` (the agent's ``output_type``) -> ``output_config.format`` with
  ``{"type": "json_schema"}``. The Runner parses the returned text with
  ``output_schema.validate_json``, so the final text block is returned as an
  ordinary ``ResponseOutputMessage`` and ``result.final_output`` is the Pydantic
  object. Schemas pass through ``anthropic.transform_schema`` (the SDK's own
  lowering: unsupported keywords such as ``minLength`` move into descriptions;
  the Agents SDK still validates them client-side).
* Thinking is adaptive by default on ``claude-opus-5``; the ``thinking`` parameter is
  omitted and depth is set with ``output_config.effort`` (``low`` matches the
  paper's OpenAI reasoning effort). ``temperature``/``top_p`` are never sent.
* Usage -> Agents SDK ``Usage``. Anthropic reports uncached input, cache reads and
  cache writes as three disjoint counters; the harness (``trace_metrics``) expects
  the OpenAI convention where ``input_tokens`` is the whole prompt and the details
  carry the cached/written subsets. ``input_tokens`` is therefore the sum of the
  three, ``input_tokens_details.cached_tokens`` = ``cache_read_input_tokens`` and
  ``input_tokens_details.cache_write_tokens`` = ``cache_creation_input_tokens``.
* One ``generation_span`` per request carries that usage, so the harness's trace
  processor sees the same span shape it sees for OpenAI models.
* ``stop_reason == "refusal"`` raises :class:`AnthropicRefusalError`;
  ``"max_tokens"`` raises ``ModelBehaviorError``. ``max_tokens`` defaults to 16000
  (non-streaming). Streaming is not implemented: ``Runner.run`` never streams.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Sequence

from agents.agent_output import AgentOutputSchemaBase
from agents.exceptions import ModelBehaviorError, UserError
from agents.handoffs import Handoff
from agents.items import ModelResponse, TResponseInputItem, TResponseOutputItem
from agents.model_settings import ModelSettings
from agents.models._trace import model_config_for_trace
from agents.models.fake_id import FAKE_RESPONSES_ID
from agents.models.interface import Model, ModelTracing
from agents.tool import FunctionTool, Tool
from agents.tracing import generation_span
from agents.usage import Usage, model_usage_to_span_usage
from openai.types.responses import (
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
    ResponseReasoningItem,
)
from openai.types.responses.response_reasoning_item import Content as ReasoningContent
from openai.types.responses.response_usage import InputTokensDetails, OutputTokensDetails

__all__ = [
    "ANTHROPIC_PREFIX",
    "AnthropicModel",
    "AnthropicRefusalError",
    "anthropic_model_id",
    "anthropic_model_settings",
    "is_anthropic_model",
    "provider_api_key_env",
    "resolve_model",
]

logger = logging.getLogger(__name__)

ANTHROPIC_PREFIX = "anthropic/"
DEFAULT_EFFORT = "low"
DEFAULT_MAX_TOKENS = 16000
_THINKING_KEY = "anthropic_thinking_blocks"


class AnthropicRefusalError(RuntimeError):
    """The model stopped with ``stop_reason == "refusal"``; the answer is unusable."""

    def __init__(self, model: str, category: str | None, explanation: str | None) -> None:
        self.model = model
        self.category = category
        self.explanation = explanation
        super().__init__(
            f"{model} refused the request"
            + (f" (category={category})" if category else "")
            + (f": {explanation}" if explanation else "")
        )


# ------------------------------------------------------------------ provider resolution


def is_anthropic_model(model: Any) -> bool:
    """True for ``anthropic/...`` names, :class:`AnthropicModel`, or a wrapper around one."""

    if isinstance(model, str):
        return model.startswith(ANTHROPIC_PREFIX)
    if isinstance(model, AnthropicModel):
        return True
    wrapped = getattr(model, "_wrapped", None)
    return wrapped is not None and is_anthropic_model(wrapped)


def anthropic_model_id(name: str) -> str:
    """``anthropic/claude-opus-5`` -> ``claude-opus-5``."""

    if not name.startswith(ANTHROPIC_PREFIX) or len(name) <= len(ANTHROPIC_PREFIX):
        raise ValueError(f"not an anthropic model name: {name!r}")
    return name[len(ANTHROPIC_PREFIX) :]


def resolve_model(name: str) -> Any:
    """Return the plain string for OpenAI names and an :class:`AnthropicModel` otherwise.

    OpenAI names are returned untouched so the Agents SDK's default provider
    resolves them exactly as before.
    """

    if is_anthropic_model(name):
        return AnthropicModel(anthropic_model_id(name))
    return name


def anthropic_model_settings() -> ModelSettings:
    """Agents SDK settings for the Anthropic arm.

    Only ``parallel_tool_calls=False`` is expressed here; it maps to
    ``disable_parallel_tool_use``. Reasoning effort ``low`` is applied inside
    :class:`AnthropicModel` (``output_config.effort``), and ``verbosity``/``store``
    have no Messages API counterpart.
    """

    return ModelSettings(parallel_tool_calls=False)


def provider_api_key_env(model: Any) -> str:
    """Name of the credential environment variable the provider of ``model`` reads."""

    return "ANTHROPIC_API_KEY" if is_anthropic_model(model) else "OPENAI_API_KEY"


# -------------------------------------------------------------------------- the model


class AnthropicModel(Model):
    """Agents SDK ``Model`` that calls Claude through ``anthropic.AsyncAnthropic``."""

    def __init__(
        self,
        model: str,
        *,
        client: Any | None = None,
        effort: str = DEFAULT_EFFORT,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens
        self._client = client

    def _get_client(self) -> Any:
        if self._client is None:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic()
        return self._client

    async def get_response(
        self,
        system_instructions: str | None,
        input: str | list[TResponseInputItem],
        model_settings: ModelSettings,
        tools: list[Tool],
        output_schema: AgentOutputSchemaBase | None,
        handoffs: list[Handoff],
        tracing: ModelTracing,
        *,
        previous_response_id: str | None = None,
        conversation_id: str | None = None,
        prompt: Any | None = None,
    ) -> ModelResponse:
        if handoffs:
            raise UserError("AnthropicModel does not support handoffs")
        if previous_response_id or conversation_id or prompt is not None:
            raise UserError(
                "AnthropicModel does not support server-managed conversation state or prompts"
            )
        request = self.build_request(system_instructions, input, model_settings, tools, output_schema)
        trace_config = model_config_for_trace(
            model_settings,
            extra_config={"provider": "anthropic", "effort": self.effort, "max_tokens": request["max_tokens"]},
        )
        with generation_span(
            model=self.model, model_config=trace_config, disabled=tracing.is_disabled()
        ) as span:
            if tracing.include_data():
                span.span_data.input = _trace_input(request)
            response = await self._get_client().messages.create(**request)
            usage = usage_from_anthropic(response.usage)
            span.span_data.usage = model_usage_to_span_usage(usage)
            if tracing.include_data():
                span.span_data.output = [block.model_dump(exclude_none=True) for block in response.content]
            if response.stop_reason == "refusal":
                details = getattr(response, "stop_details", None)
                error = AnthropicRefusalError(
                    self.model,
                    getattr(details, "category", None),
                    getattr(details, "explanation", None),
                )
                span.set_error({"message": "refusal", "data": {"category": error.category}})
                raise error
            if response.stop_reason == "max_tokens":
                raise ModelBehaviorError(
                    f"{self.model} hit max_tokens={request['max_tokens']} before finishing"
                )
            provider_data = {"model": self.model, "response_id": response.id}
            return ModelResponse(
                output=output_items_from_content(response.content, provider_data),
                usage=usage,
                response_id=None,
            )

    def stream_response(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError("AnthropicModel is non-streaming; use Runner.run")

    # -- request construction ------------------------------------------------

    def build_request(
        self,
        system_instructions: str | None,
        input: str | list[TResponseInputItem],
        model_settings: ModelSettings,
        tools: Sequence[Tool],
        output_schema: AgentOutputSchemaBase | None,
    ) -> dict[str, Any]:
        from anthropic import transform_schema

        system_parts = [system_instructions] if system_instructions else []
        messages = items_to_messages(input, system_parts)
        request: dict[str, Any] = {
            "model": self.model,
            "max_tokens": model_settings.max_tokens or self.max_tokens,
            "messages": messages,
            "output_config": {"effort": self.effort},
        }
        if system_parts:
            request["system"] = "\n\n".join(system_parts)
        if model_settings.temperature is not None or model_settings.top_p is not None:
            logger.debug("AnthropicModel ignores temperature/top_p (adaptive thinking)")
        anthropic_tools = [tool_to_anthropic(tool, transform_schema) for tool in tools]
        if anthropic_tools:
            request["tools"] = anthropic_tools
            request["tool_choice"] = _tool_choice(model_settings)
        if output_schema is not None and not output_schema.is_plain_text():
            request["output_config"]["format"] = {
                "type": "json_schema",
                "schema": transform_schema(output_schema.json_schema()),
            }
        return request


# ------------------------------------------------------------------ item conversion


def tool_to_anthropic(tool: Tool, transform_schema: Any) -> dict[str, Any]:
    if not isinstance(tool, FunctionTool):
        raise UserError(f"AnthropicModel supports FunctionTool only, got {type(tool).__name__}")
    spec: dict[str, Any] = {
        "name": tool.name,
        "description": tool.description or "",
        "input_schema": transform_schema(tool.params_json_schema),
    }
    if tool.strict_json_schema:
        spec["strict"] = True
    return spec


def _tool_choice(model_settings: ModelSettings) -> dict[str, Any]:
    choice = model_settings.tool_choice
    if choice in (None, "auto"):
        out: dict[str, Any] = {"type": "auto"}
    elif choice == "none":
        return {"type": "none"}
    elif choice == "required":
        out = {"type": "any"}
    elif isinstance(choice, str):
        out = {"type": "tool", "name": choice}
    else:
        raise UserError(f"unsupported tool_choice for AnthropicModel: {choice!r}")
    if model_settings.parallel_tool_calls is False:
        out["disable_parallel_tool_use"] = True
    return out


def items_to_messages(
    items: str | Sequence[Any], system_parts: list[str]
) -> list[dict[str, Any]]:
    """Convert Responses-format input items into Messages API ``messages``."""

    if isinstance(items, str):
        return [{"role": "user", "content": [{"type": "text", "text": items}]}]

    messages: list[dict[str, Any]] = []
    role: str | None = None
    content: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal role, content
        if role is not None and content:
            messages.append({"role": role, "content": content})
        role, content = None, []

    def ensure(target: str) -> None:
        nonlocal role
        if role != target:
            flush()
            role = target

    for raw in items:
        item = _as_dict(raw)
        kind = item.get("type")
        if kind in (None, "message"):
            item_role = item.get("role")
            if item_role in ("system", "developer"):
                flush()
                text = _text_of(item.get("content"))
                if text:
                    system_parts.append(text)
            elif item_role in ("user", "assistant"):
                ensure(item_role)
                content.extend(_text_blocks(item.get("content")))
            else:
                raise UserError(f"unexpected message role for AnthropicModel: {item_role!r}")
        elif kind == "function_call":
            ensure("assistant")
            arguments = item.get("arguments") or "{}"
            content.append(
                {
                    "type": "tool_use",
                    "id": item["call_id"],
                    "name": item["name"],
                    "input": json.loads(arguments),
                }
            )
        elif kind == "function_call_output":
            ensure("user")
            content.append(
                {
                    "type": "tool_result",
                    "tool_use_id": item["call_id"],
                    "content": _text_of(item.get("output")),
                }
            )
        elif kind == "reasoning":
            blocks = (item.get("provider_data") or {}).get(_THINKING_KEY)
            if blocks:
                ensure("assistant")
                content.extend(dict(block) for block in blocks)
            # Reasoning items without Anthropic blocks (other providers) have nothing
            # the Messages API could replay; they are dropped.
        else:
            raise UserError(f"unsupported input item for AnthropicModel: {kind!r}")
    flush()
    return messages


def output_items_from_content(
    content: Sequence[Any], provider_data: dict[str, Any]
) -> list[TResponseOutputItem]:
    """Convert Anthropic content blocks into Responses output items.

    Order is reasoning, message, tool calls, matching the SDK's own converters.
    """

    items: list[TResponseOutputItem] = []
    thinking = [
        block.model_dump(exclude_none=True)
        for block in content
        if block.type in ("thinking", "redacted_thinking")
    ]
    if thinking:
        kwargs: dict[str, Any] = {
            "id": FAKE_RESPONSES_ID,
            "summary": [],
            "type": "reasoning",
            "provider_data": {**provider_data, _THINKING_KEY: thinking},
        }
        visible = [b["thinking"] for b in thinking if b.get("thinking")]
        if visible:
            kwargs["content"] = [
                ReasoningContent(text=text, type="reasoning_text") for text in visible
            ]
        items.append(ResponseReasoningItem(**kwargs))
    texts = [block.text for block in content if block.type == "text" and block.text]
    if texts:
        items.append(
            ResponseOutputMessage(
                id=FAKE_RESPONSES_ID,
                content=[
                    ResponseOutputText(
                        text="\n".join(texts), type="output_text", annotations=[], logprobs=[]
                    )
                ],
                role="assistant",
                type="message",
                status="completed",
                provider_data=provider_data,
            )
        )
    for block in content:
        if block.type == "tool_use":
            items.append(
                ResponseFunctionToolCall(
                    id=FAKE_RESPONSES_ID,
                    call_id=block.id,
                    name=block.name,
                    arguments=json.dumps(block.input),
                    type="function_call",
                    provider_data=provider_data,
                )
            )
        elif block.type not in ("thinking", "redacted_thinking", "text"):
            raise UserError(f"unsupported Anthropic content block: {block.type!r}")
    return items


def usage_from_anthropic(usage: Any) -> Usage:
    """Normalize Anthropic's disjoint counters to the OpenAI-style totals the harness prices."""

    cache_read = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
    cache_write = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
    prompt_tokens = int(getattr(usage, "input_tokens", 0) or 0) + cache_read + cache_write
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
    details = getattr(usage, "output_tokens_details", None)
    thinking_tokens = int(getattr(details, "thinking_tokens", 0) or 0)
    return Usage(
        requests=1,
        input_tokens=prompt_tokens,
        output_tokens=output_tokens,
        total_tokens=prompt_tokens + output_tokens,
        input_tokens_details=InputTokensDetails.model_validate(
            {"cached_tokens": cache_read, "cache_write_tokens": cache_write}
        ),
        output_tokens_details=OutputTokensDetails(reasoning_tokens=thinking_tokens),
    )


# --------------------------------------------------------------------------- helpers


def _as_dict(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    if hasattr(item, "model_dump"):
        return item.model_dump(exclude_unset=True)
    raise UserError(f"unsupported input item type for AnthropicModel: {type(item).__name__}")


def _text_blocks(content: Any) -> list[dict[str, Any]]:
    text = _text_of(content)
    return [{"type": "text", "text": text}] if text.strip() else []


def _text_of(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for part in content:
        part = _as_dict(part)
        kind = part.get("type")
        if kind in ("input_text", "output_text", "text"):
            parts.append(str(part.get("text", "")))
        elif kind == "refusal":
            parts.append(str(part.get("refusal", "")))
        else:
            raise UserError(f"unsupported content part for AnthropicModel: {kind!r}")
    return "\n".join(parts)


def _trace_input(request: dict[str, Any]) -> list[dict[str, Any]]:
    system = request.get("system")
    prefix = [{"role": "system", "content": system}] if system else []
    return prefix + list(request["messages"])
