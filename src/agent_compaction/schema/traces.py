"""Typed trace IR (execution-plan §6, proposal §3.1-3.2).

This module is the compiler's own intermediate representation. It is deliberately
independent of the OpenAI Agents SDK and of any other tracing platform: those are
*backends* that
produce ``Episode`` objects (see :mod:`agent_compaction.capture`).

Design rules encoded here:

* Raw payloads are preserved by reference (``content_ref``) and by value only
  when the privacy class allows it.
* An episode carries a frozen :class:`ExecutionManifest`; episodes with
  different manifests are never pooled (execution-plan §5).
* ``group_id`` is the unit of statistical independence, never a span.
* Hidden chain-of-thought is never represented. Only observable response items.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Iterable, Iterator, Sequence

from ..paths import content_digest, flatten, resolve_path

__all__ = [
    "EventKind",
    "Usage",
    "EventNode",
    "ExecutionManifest",
    "TraceEnvelope",
    "OutcomeLabels",
    "Episode",
    "flatten",
    "content_digest",
    "PathValue",
    "manifest_partitions",
    "require_compatible_manifest",
]


class EventKind(str, Enum):
    """Observable event kinds.

    ``MODEL_REQ``/``MODEL_RESP`` are the model-request boundaries of proposal
    §3.1; ``TOOL_CALL``/``TOOL_RESULT`` carry typed payloads. ``HANDOFF``,
    ``GUARDRAIL`` and ``APPROVAL`` are Agents-SDK semantic events that act as
    region barriers (execution-plan §8.2 "Eligibility").
    """

    MODEL_REQ = "MODEL_REQ"
    MODEL_RESP = "MODEL_RESP"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    HANDOFF = "HANDOFF"
    GUARDRAIL = "GUARDRAIL"
    APPROVAL = "APPROVAL"


@dataclass(frozen=True, slots=True)
class Usage:
    """Token accounting, decomposed for the cache-aware cost model of Eq. (9)."""

    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            self.input_tokens + other.input_tokens,
            self.cached_input_tokens + other.cached_input_tokens,
            self.output_tokens + other.output_tokens,
        )


@dataclass(slots=True)
class EventNode:
    """One observable event.

    ``effect`` is *not* stored here as truth: effects are declared in the
    versioned catalog and resolved during graph construction. The field exists
    only to carry what the application asserted at capture time so that a
    mismatch with the catalog can be reported as a data-quality defect.
    """

    node_id: str
    kind: EventKind
    index: int
    actor: str = ""
    parent_id: str | None = None
    tool: str | None = None
    schema_version: str | None = None
    input: Any = None
    output: Any = None
    status: str = "ok"
    t_start_ms: float = 0.0
    t_end_ms: float = 0.0
    usage: Usage = field(default_factory=Usage)
    request_id: str | None = None
    call_id: str | None = None
    declared_effect: str | None = None
    truncated: bool = False
    attributes: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        return max(0.0, self.t_end_ms - self.t_start_ms)

    @property
    def is_boundary(self) -> bool:
        return self.kind is EventKind.MODEL_REQ

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        d["usage"] = asdict(self.usage)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "EventNode":
        d = dict(d)
        d["kind"] = EventKind(d["kind"])
        d["usage"] = Usage(**(d.get("usage") or {}))
        return cls(**d)


@dataclass(frozen=True, slots=True)
class ExecutionManifest:
    """Frozen identity of the executing workflow (execution-plan §6).

    Any drift in these fields invalidates every artifact compiled from episodes
    that carried the manifest — that is the compatibility hash of §5.
    """

    manifest_id: str
    commit: str = "unknown"
    model: str = "unknown"
    prompt_hash: str = "unknown"
    tools_hash: str = "unknown"
    policy_hash: str = "unknown"
    guardrail_hash: str = "unknown"
    effect_catalog_version: str = "unknown"
    entry_contract_version: str = "unknown"
    sdk_version: str = "unknown"
    tracer_version: str = "unknown"

    def compatibility_key(self) -> str:
        """Hash every input that can change compilation or dispatch semantics."""

        # A delimiter-joined representation is ambiguous when a field itself
        # contains the delimiter. Canonical JSON keeps the compatibility identity
        # collision-resistant without constraining user-provided manifest values.
        payload = json.dumps(
            {
                "commit": self.commit,
                "model": self.model,
                "prompt_hash": self.prompt_hash,
                "tools_hash": self.tools_hash,
                "policy_hash": self.policy_hash,
                "guardrail_hash": self.guardrail_hash,
                "effect_catalog_version": self.effect_catalog_version,
                "entry_contract_version": self.entry_contract_version,
                "sdk_version": self.sdk_version,
                "tracer_version": self.tracer_version,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class TraceEnvelope:
    """Application-owned facts that no tracing platform can infer."""

    trace_id: str
    episode_id: str
    group_id: str
    manifest_id: str
    principal: str = "unknown"
    tenant_partition: str = "unknown"
    policy_version: str = "v0"
    day: str = "1970-01-01"
    privacy_class: str = "internal"
    entry_state_ref: str | None = None
    outcome_ref: str | None = None
    external_state_version: str = "unknown"
    approval_scope: str | None = None


@dataclass(frozen=True, slots=True)
class OutcomeLabels:
    """Task and business outcomes, joined asynchronously by episode id."""

    task_success: bool | None = None
    semantic_score: float | None = None
    safety_events: int = 0
    business_metrics: dict[str, float] = field(default_factory=dict)
    label_latency_s: float = 0.0


@dataclass(slots=True)
class Episode:
    """One qualified episode: the unit the compiler reasons over."""

    envelope: TraceEnvelope
    manifest: ExecutionManifest
    entry_state: dict[str, Any]
    events: list[EventNode]
    outcome: OutcomeLabels = field(default_factory=OutcomeLabels)
    final_state_digest: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)

    # -- convenience views ------------------------------------------------
    @property
    def episode_id(self) -> str:
        return self.envelope.episode_id

    @property
    def group_id(self) -> str:
        return self.envelope.group_id

    def boundaries(self) -> list[EventNode]:
        return [e for e in self.events if e.kind is EventKind.MODEL_REQ]

    def n_requests(self) -> int:
        return len(self.boundaries())

    def tool_calls(self) -> list[EventNode]:
        return [e for e in self.events if e.kind is EventKind.TOOL_CALL]

    def usage(self) -> Usage:
        total = Usage()
        for e in self.events:
            total = total + e.usage
        return total

    def latency_ms(self) -> float:
        if not self.events:
            return 0.0
        return max(e.t_end_ms for e in self.events) - min(e.t_start_ms for e in self.events)

    def critical_path_ms(self) -> float:
        """Sum of durations along the serial chain of events.

        The simulated substrate executes a single serial agent loop, so the
        critical path is the sum of event durations; parallel demos override
        this by marking concurrent events with ``attributes['parallel_group']``.
        """
        total = 0.0
        seen_groups: set[str] = set()
        for e in self.events:
            pg = e.attributes.get("parallel_group")
            if pg is None:
                total += e.duration_ms
                continue
            if pg in seen_groups:
                continue
            seen_groups.add(pg)
            peers = [x.duration_ms for x in self.events if x.attributes.get("parallel_group") == pg]
            total += max(peers) if peers else 0.0
        return total

    def tools_used(self) -> set[str]:
        return {e.tool for e in self.events if e.tool}

    def to_dict(self) -> dict[str, Any]:
        return {
            "envelope": asdict(self.envelope),
            "manifest": asdict(self.manifest),
            "entry_state": self.entry_state,
            "events": [e.to_dict() for e in self.events],
            "outcome": asdict(self.outcome),
            "final_state_digest": self.final_state_digest,
            "attributes": self.attributes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Episode":
        return cls(
            envelope=TraceEnvelope(**d["envelope"]),
            manifest=ExecutionManifest(**d["manifest"]),
            entry_state=d["entry_state"],
            events=[EventNode.from_dict(e) for e in d["events"]],
            outcome=OutcomeLabels(**d.get("outcome", {})),
            final_state_digest=d.get("final_state_digest", ""),
            attributes=d.get("attributes", {}),
        )


# ---------------------------------------------------------------------------
# payload helpers (re-exported from agent_compaction.paths to avoid import cycles)
# ---------------------------------------------------------------------------


def episode_group_counts(episodes: Iterable[Episode]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for ep in episodes:
        counts[ep.group_id] = counts.get(ep.group_id, 0) + 1
    return counts


def iter_events(episodes: Sequence[Episode]) -> Iterator[tuple[Episode, EventNode]]:
    for ep in episodes:
        for ev in ep.events:
            yield ep, ev


def manifest_partitions(episodes: Sequence[Episode]) -> dict[str, list[Episode]]:
    """Partition a corpus by the full execution compatibility identity.

    This is the safe entry point for rolling deployments whose trace snapshot can
    contain several workflow versions. A partition may be compiled independently;
    evidence from different keys must never be pooled.
    """

    out: dict[str, list[Episode]] = {}
    for episode in episodes:
        out.setdefault(episode.manifest.compatibility_key(), []).append(episode)
    return out


def require_compatible_manifest(
    episodes: Sequence[Episode], manifest: ExecutionManifest | None = None
) -> ExecutionManifest:
    """Return the corpus manifest or raise when workflow versions are mixed."""

    if not episodes:
        raise ValueError("no episodes to compile")
    expected = manifest or episodes[0].manifest
    expected_key = expected.compatibility_key()
    incompatible = sorted(
        episode.episode_id
        for episode in episodes
        if episode.manifest.compatibility_key() != expected_key
    )
    if incompatible:
        sample = ", ".join(incompatible[:5])
        raise ValueError(
            "episodes from different execution manifests cannot be pooled; "
            f"{len(incompatible)} incompatible episode(s), including {sample}; "
            "partition with manifest_partitions() or use a batch compiler"
        )
    return expected
