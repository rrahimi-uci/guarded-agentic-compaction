"""Permission facade: the only way a compiled program can touch a tool.

Fail closed is not a slogan here, it is this class. Every call is checked against
the versioned effect catalog *at execution time*, not only at compile time, so a
catalog edit that demotes a tool immediately stops dispatch. The facade also
implements the modes of execution-plan §7:

``recorded``
    No external calls at all. Arguments are looked up in a recording taken from
    the episode being replayed; a miss is an error, never a live call. This is
    what makes "production replay cannot call effectful tools" a property of the
    code rather than a review checklist item.
``sandbox``
    Live calls against an isolated world/fixture. Used for grouped replay and the
    perturbation suite.
``live``
    Live calls against the real dependency, restricted to compilable tools.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

from ..schema.effects import Capability, EffectCatalog, EffectClass

__all__ = ["FacadeMode", "ToolFacade", "FacadeError", "RecordingMiss", "ForbiddenTool", "Recording"]


class FacadeError(Exception):
    """Base class: any facade error is a pre-commit failure."""


class ForbiddenTool(FacadeError):
    """The program asked for a tool the catalog does not license."""


class RecordingMiss(FacadeError):
    """Recorded replay asked for an argument combination that was never observed."""


class ToolFailure(FacadeError):
    """The underlying tool raised (4xx/5xx/timeout)."""


class FacadeMode:
    RECORDED = "recorded"
    SANDBOX = "sandbox"
    LIVE = "live"

    @classmethod
    def values(cls) -> tuple[str, ...]:
        return (cls.RECORDED, cls.SANDBOX, cls.LIVE)


def _key(tool: str, args: dict[str, Any]) -> str:
    return tool + "|" + json.dumps(args, sort_keys=True, default=str)


@dataclass(slots=True)
class Recording:
    """Observed ``(tool, args) → result`` pairs from one episode."""

    entries: dict[str, Any] = field(default_factory=dict)
    by_tool: dict[str, list[tuple[dict[str, Any], Any]]] = field(default_factory=dict)

    def add(self, tool: str, args: dict[str, Any], result: Any) -> None:
        self.entries[_key(tool, args)] = result
        self.by_tool.setdefault(tool, []).append((dict(args), result))

    def get(self, tool: str, args: dict[str, Any]) -> Any:
        key = _key(tool, args)
        if key in self.entries:
            return self.entries[key]
        raise RecordingMiss(f"no recorded response for {tool} with {sorted(args)}")

    def get_semantic(
        self,
        tool: str,
        args: dict[str, Any],
        catalog: EffectCatalog,
    ) -> Any:
        """Resolve exact arguments first, then a declared semantic representative."""

        try:
            return self.get(tool, args)
        except RecordingMiss:
            for observed, result in self.by_tool.get(tool, ()):
                if catalog.arguments_equivalent(tool, observed, args):
                    return result
        raise RecordingMiss(f"no semantically equivalent response for {tool} with {sorted(args)}")

    @classmethod
    def from_episode(cls, episode: Any) -> "Recording":
        from ..schema.traces import EventKind

        rec = cls()
        pending: list[Any] = []
        pending_by_id: dict[str, Any] = {}
        for ev in episode.events:
            if ev.kind is EventKind.TOOL_CALL:
                if ev.call_id:
                    pending_by_id[ev.call_id] = ev
                else:
                    pending.append(ev)
            elif ev.kind is EventKind.TOOL_RESULT:
                call = pending_by_id.pop(ev.call_id, None) if ev.call_id else None
                if call is None and pending:
                    call = pending.pop(0)
                if call is None:
                    continue
                if ev.status == "ok" and isinstance(call.input, dict):
                    rec.add(call.tool or "", call.input, ev.output)
        return rec


@dataclass(slots=True)
class ToolFacade:
    """Checked tool access for the interpreter."""

    catalog: EffectCatalog
    mode: str = FacadeMode.RECORDED
    recording: Recording | None = None
    executor: Callable[[str, dict[str, Any]], Any] | None = None
    allowed_tools: tuple[str, ...] = ()
    max_calls: int = 16
    effects: list[str] = field(default_factory=list)
    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    results: list[Any] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.mode not in FacadeMode.values():
            raise ValueError(f"mode must be one of {FacadeMode.values()}, got {self.mode!r}")
        if self.max_calls <= 0:
            raise ValueError("max_calls must be positive")

    def call(self, tool: str, args: dict[str, Any]) -> Any:
        spec = self.catalog.get(tool)
        if not spec.compilable:
            raise ForbiddenTool(f"{tool} is {spec.effect.value} ({spec.block_reason()})")
        if self.allowed_tools and tool not in self.allowed_tools:
            raise ForbiddenTool(f"{tool} not in artifact tool allowlist")
        if len(self.calls) >= self.max_calls:
            raise FacadeError("call budget exceeded")
        try:
            args = self.catalog.canonicalize_arguments(tool, args)
        except (TypeError, ValueError) as exc:
            raise FacadeError(f"argument canonicalization failed for {tool}: {exc}") from exc
        self.calls.append((tool, dict(args)))
        self.effects.append(spec.effect.value)
        if self.mode == FacadeMode.RECORDED:
            if self.recording is None:
                raise FacadeError("recorded mode without a recording")
            result = self.recording.get_semantic(tool, args, self.catalog)
            self.results.append(result)
            return result
        if self.executor is None:
            raise FacadeError(f"{self.mode} mode without an executor")
        try:
            result = self.executor(tool, args)
        except FacadeError:
            raise
        except Exception as exc:  # tool 4xx/5xx/timeout
            raise ToolFailure(f"{tool}: {exc}") from exc
        self.results.append(result)
        return result

    def reset(self) -> None:
        self.effects.clear()
        self.calls.clear()
        self.results.clear()

    @property
    def effect_multiset(self) -> tuple[str, ...]:
        return tuple(sorted(self.effects))
