"""OpenAI Agents SDK tracing adapter.

The adapter is a secondary ``TracingProcessor`` destination. It does not replace the
SDK's default exporter and it does not invent application-owned facts. Callers join a
completed SDK trace with an explicit manifest, entry state, isolation envelope, and
outcome before it can become compiler input.
"""

from __future__ import annotations

import json
import queue
import threading
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any, Sequence

from ..schema.traces import (
    Episode,
    EventKind,
    EventNode,
    ExecutionManifest,
    OutcomeLabels,
    TraceEnvelope,
    Usage,
)

__all__ = [
    "SdkSpanRecord",
    "SdkTraceRecord",
    "AgentsTraceProcessor",
    "install_agents_trace_processor",
    "episode_from_agents_trace",
]


@dataclass(frozen=True, slots=True)
class SdkSpanRecord:
    trace_id: str
    span_id: str
    parent_id: str | None
    started_at: str | None
    ended_at: str | None
    data: dict[str, Any]
    error: Any = None


@dataclass(frozen=True, slots=True)
class SdkTraceRecord:
    trace_id: str
    name: str
    group_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    spans: tuple[SdkSpanRecord, ...] = ()


class AgentsTraceProcessor:
    """Thread-safe, non-blocking collector compatible with SDK 0.19.x.

    ``include_sensitive_data`` defaults to false. In that mode structure and usage
    remain observable, but model/tool payloads are removed and the resulting episode
    intentionally fails compiler qualification until complete payloads are joined from
    an application-controlled store.
    """

    def __init__(self, *, include_sensitive_data: bool = False, max_completed: int = 1000) -> None:
        self.include_sensitive_data = include_sensitive_data
        self._lock = threading.RLock()
        self._traces: dict[str, dict[str, Any]] = {}
        self._spans: dict[str, list[SdkSpanRecord]] = {}
        self._completed: queue.Queue[SdkTraceRecord] = queue.Queue(maxsize=max_completed)
        self.dropped = 0

    def on_trace_start(self, trace: Any) -> None:
        with self._lock:
            self._traces[trace.trace_id] = {
                "name": getattr(trace, "name", "Agent workflow"),
                "group_id": getattr(trace, "group_id", None),
                "metadata": dict(getattr(trace, "metadata", None) or {}),
            }
            self._spans.setdefault(trace.trace_id, [])

    def on_trace_end(self, trace: Any) -> None:
        with self._lock:
            meta = self._traces.pop(trace.trace_id, {})
            spans = tuple(self._spans.pop(trace.trace_id, ()))
        record = SdkTraceRecord(
            trace_id=trace.trace_id,
            name=str(meta.get("name", getattr(trace, "name", "Agent workflow"))),
            group_id=meta.get("group_id"),
            metadata=dict(meta.get("metadata", {})),
            spans=spans,
        )
        try:
            self._completed.put_nowait(record)
        except queue.Full:
            self.dropped += 1

    def on_span_start(self, span: Any) -> None:
        return None

    def on_span_end(self, span: Any) -> None:
        try:
            data = _span_data(span, include_sensitive=self.include_sensitive_data)
            record = SdkSpanRecord(
                trace_id=span.trace_id,
                span_id=span.span_id,
                parent_id=getattr(span, "parent_id", None),
                started_at=getattr(span, "started_at", None),
                ended_at=getattr(span, "ended_at", None),
                data=data,
                error=getattr(span, "error", None),
            )
            with self._lock:
                self._spans.setdefault(span.trace_id, []).append(record)
        except Exception:
            # Tracing must never break the agent loop. Operational code can inspect
            # ``dropped`` and reconcile trace counts before compilation.
            self.dropped += 1

    def drain(self, *, limit: int | None = None) -> list[SdkTraceRecord]:
        out: list[SdkTraceRecord] = []
        while limit is None or len(out) < limit:
            try:
                out.append(self._completed.get_nowait())
            except queue.Empty:
                break
        return out

    def force_flush(self) -> None:
        return None

    def shutdown(self) -> None:
        with self._lock:
            self._traces.clear()
            self._spans.clear()


def install_agents_trace_processor(
    processor: AgentsTraceProcessor | None = None,
) -> AgentsTraceProcessor:
    """Register a secondary processor without replacing the default exporter."""

    try:
        from agents import add_trace_processor
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("install the 'agents' extra to capture Agents SDK traces") from exc
    installed = processor or AgentsTraceProcessor()
    add_trace_processor(installed)
    return installed


def episode_from_agents_trace(
    trace: SdkTraceRecord,
    *,
    envelope: TraceEnvelope,
    manifest: ExecutionManifest,
    entry_state: dict[str, Any],
    outcome: OutcomeLabels | None = None,
    final_state_digest: str = "",
    tool_aliases: dict[str, str] | None = None,
) -> Episode:
    """Normalize SDK generation/function/handoff/guardrail spans into the trace IR."""

    aliases = tool_aliases or {}
    events: list[EventNode] = []
    ordered = sorted(trace.spans, key=lambda item: (item.started_at or "", item.span_id))
    for span in ordered:
        data = span.data
        span_type = str(data.get("type", ""))
        start = _milliseconds(span.started_at)
        end = _milliseconds(span.ended_at) or start
        status = "error" if span.error else "ok"
        if span_type in {"generation", "response"}:
            usage = _usage(data.get("usage"))
            events.append(
                EventNode(
                    node_id=f"{span.span_id}:request",
                    kind=EventKind.MODEL_REQ,
                    index=len(events),
                    parent_id=span.parent_id,
                    input=data.get("input"),
                    t_start_ms=start,
                    t_end_ms=start,
                    request_id=span.span_id,
                )
            )
            events.append(
                EventNode(
                    node_id=f"{span.span_id}:response",
                    kind=EventKind.MODEL_RESP,
                    index=len(events),
                    parent_id=span.parent_id,
                    output=data.get("output"),
                    status=status,
                    t_start_ms=start,
                    t_end_ms=end,
                    usage=usage,
                    request_id=span.span_id,
                )
            )
        elif span_type == "function":
            sdk_tool = str(data.get("name") or "")
            tool = aliases.get(sdk_tool, sdk_tool)
            events.append(
                EventNode(
                    node_id=f"{span.span_id}:call",
                    kind=EventKind.TOOL_CALL,
                    index=len(events),
                    parent_id=span.parent_id,
                    tool=tool,
                    input=_json_value(data.get("input")),
                    t_start_ms=start,
                    t_end_ms=start,
                    call_id=span.span_id,
                )
            )
            events.append(
                EventNode(
                    node_id=f"{span.span_id}:result",
                    kind=EventKind.TOOL_RESULT,
                    index=len(events),
                    parent_id=span.parent_id,
                    tool=tool,
                    output=_json_value(data.get("output")),
                    status=status,
                    t_start_ms=start,
                    t_end_ms=end,
                    call_id=span.span_id,
                )
            )
        elif span_type == "handoff":
            events.append(
                EventNode(
                    node_id=span.span_id,
                    kind=EventKind.HANDOFF,
                    index=len(events),
                    parent_id=span.parent_id,
                    output={"from": data.get("from_agent"), "target": data.get("to_agent")},
                    status=status,
                    t_start_ms=start,
                    t_end_ms=end,
                )
            )
        elif span_type == "guardrail":
            events.append(
                EventNode(
                    node_id=span.span_id,
                    kind=EventKind.GUARDRAIL,
                    index=len(events),
                    parent_id=span.parent_id,
                    output={"name": data.get("name"), "triggered": data.get("triggered")},
                    status=status,
                    t_start_ms=start,
                    t_end_ms=end,
                )
            )
    return Episode(
        envelope=replace(
            envelope,
            trace_id=trace.trace_id,
            manifest_id=manifest.manifest_id,
            group_id=envelope.group_id or trace.group_id or "unknown",
        ),
        manifest=manifest,
        entry_state=dict(entry_state),
        events=events,
        outcome=outcome or OutcomeLabels(),
        final_state_digest=final_state_digest,
        attributes={"sdk_workflow_name": trace.name, "sdk_trace_metadata": trace.metadata},
    )


def _span_data(span: Any, *, include_sensitive: bool) -> dict[str, Any]:
    source = span.span_data
    data = dict(source.export())
    if include_sensitive:
        for key in ("input", "output"):
            if hasattr(source, key):
                data[key] = getattr(source, key)
        response = getattr(source, "response", None)
        if response is not None:
            data["output"] = getattr(response, "output", None)
    else:
        for key in ("input", "output", "data"):
            if key in data:
                data[key] = None
    return data


def _json_value(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _usage(value: Any) -> Usage:
    data = value if isinstance(value, dict) else {}
    input_details = data.get("input_tokens_details")
    if not isinstance(input_details, dict):
        input_details = {}
    return Usage(
        input_tokens=int(data.get("input_tokens", 0) or 0),
        cached_input_tokens=int(
            data.get("cached_input_tokens", input_details.get("cached_tokens", 0))
            or 0
        ),
        output_tokens=int(data.get("output_tokens", 0) or 0),
    )


def _milliseconds(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000.0
    except ValueError:
        return 0.0
