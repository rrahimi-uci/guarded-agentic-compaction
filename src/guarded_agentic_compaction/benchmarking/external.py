"""Framework-neutral contracts for external agent benchmark traces.

The public benchmarks used by the paper do not share an execution API.  Some expose
complete tool calls and results, some expose only a reference action plan, and others
provide only a task and an end-state oracle.  This module preserves those distinctions
instead of manufacturing compiler evidence from incomplete data.

``analyze_reference_tasks`` is deliberately a *screening* analysis.  It measures where
read-like regions and barriers occur in upstream reference plans; it is not a substitute
for running GAC on complete observed traces.  ``reference_task_to_episode`` therefore
fails closed unless every tool result was actually retained by the benchmark.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from ..schema.effects import EffectClass
from ..schema.traces import (
    Episode,
    EventKind,
    EventNode,
    ExecutionManifest,
    OutcomeLabels,
    TraceEnvelope,
)

__all__ = [
    "EvidenceSubstrate",
    "ReferenceAction",
    "ReferenceTask",
    "ReferenceAnalysis",
    "analyze_reference_tasks",
    "reference_task_to_episode",
]


def _json_clone(value: Any, *, label: str) -> Any:
    try:
        return json.loads(
            json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be finite JSON data") from exc


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


class EvidenceSubstrate(str, Enum):
    """What the upstream task represents; public does not imply real-world execution."""

    EXECUTABLE_PUBLIC_BENCHMARK = "executable_public_benchmark"
    PUBLIC_SIMULATION = "public_simulation"
    REAL_RECORDS = "real_records"
    REAL_WORLD_CONTAINER = "real_world_container"
    LIVE_WEB = "live_web"


@dataclass(frozen=True, slots=True)
class ReferenceAction:
    """One upstream reference action with an explicit evidence-completeness flag."""

    name: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    output: Any = None
    output_observed: bool = False
    effect: EffectClass = EffectClass.UNKNOWN
    requestor: str = "agent"
    turn: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("reference action name must not be empty")
        if not isinstance(self.requestor, str) or not self.requestor.strip():
            raise ValueError("reference action requestor must not be empty")
        if type(self.turn) is not int or self.turn < 0:
            raise ValueError("reference action turn must be a non-negative integer")
        if type(self.output_observed) is not bool:
            raise ValueError("output_observed must be a boolean")
        if not isinstance(self.effect, EffectClass):
            raise ValueError("reference action effect must be an EffectClass")
        object.__setattr__(
            self,
            "arguments",
            _freeze(_json_clone(dict(self.arguments), label="reference action arguments")),
        )
        object.__setattr__(
            self,
            "output",
            _freeze(_json_clone(self.output, label="reference action output")),
        )
        object.__setattr__(
            self,
            "metadata",
            _freeze(_json_clone(dict(self.metadata), label="reference action metadata")),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "arguments": _thaw(self.arguments),
            "output": _thaw(self.output),
            "output_observed": self.output_observed,
            "effect": self.effect.value,
            "requestor": self.requestor,
            "turn": self.turn,
            "metadata": _thaw(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class ReferenceTask:
    """One independent upstream task or scenario."""

    benchmark: str
    task_id: str
    group_id: str
    source_revision: str
    substrate: EvidenceSubstrate
    actions: tuple[ReferenceAction, ...] = ()
    prompt: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for label, value in (
            ("benchmark", self.benchmark),
            ("task_id", self.task_id),
            ("group_id", self.group_id),
            ("source_revision", self.source_revision),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label} must not be empty")
        if not isinstance(self.substrate, EvidenceSubstrate):
            raise ValueError("substrate must be an EvidenceSubstrate")
        if not isinstance(self.prompt, str):
            raise ValueError("reference task prompt must be a string")
        if not all(isinstance(action, ReferenceAction) for action in self.actions):
            raise ValueError("reference task actions must be ReferenceAction values")
        object.__setattr__(self, "actions", tuple(self.actions))
        object.__setattr__(
            self,
            "metadata",
            _freeze(_json_clone(dict(self.metadata), label="reference task metadata")),
        )

    @property
    def digest(self) -> str:
        payload = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        return {
            "benchmark": self.benchmark,
            "task_id": self.task_id,
            "group_id": self.group_id,
            "source_revision": self.source_revision,
            "substrate": self.substrate.value,
            "actions": [action.as_dict() for action in self.actions],
            "prompt": self.prompt,
            "metadata": _thaw(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class ReferenceAnalysis:
    """Conservative aggregate over upstream plans, never compiler-performance evidence."""

    benchmark: str
    source_revision: str
    substrate: EvidenceSubstrate
    tasks: int
    independent_groups: int
    tasks_with_reference_actions: int
    complete_observed_traces: int
    total_actions: int
    read_like_actions: int
    barrier_actions: int
    unknown_actions: int
    tasks_with_candidate_region: int
    tasks_with_barrier: int
    tasks_with_unknown: int
    maximum_read_region: int
    recurrent_candidate_families: int
    maximum_candidate_family_support: int
    effect_counts: Mapping[str, int]
    block_reason_counts: Mapping[str, int]
    candidate_family_support: Mapping[str, int]
    notes: tuple[str, ...] = (
        "reference-plan screening only; not a GAC execution result",
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "agent-compaction-reference-analysis/v1",
            "benchmark": self.benchmark,
            "source_revision": self.source_revision,
            "substrate": self.substrate.value,
            "tasks": self.tasks,
            "independent_groups": self.independent_groups,
            "tasks_with_reference_actions": self.tasks_with_reference_actions,
            "complete_observed_traces": self.complete_observed_traces,
            "total_actions": self.total_actions,
            "read_like_actions": self.read_like_actions,
            "barrier_actions": self.barrier_actions,
            "unknown_actions": self.unknown_actions,
            "tasks_with_candidate_region": self.tasks_with_candidate_region,
            "tasks_with_barrier": self.tasks_with_barrier,
            "tasks_with_unknown": self.tasks_with_unknown,
            "maximum_read_region": self.maximum_read_region,
            "recurrent_candidate_families": self.recurrent_candidate_families,
            "maximum_candidate_family_support": self.maximum_candidate_family_support,
            "effect_counts": dict(self.effect_counts),
            "block_reason_counts": dict(self.block_reason_counts),
            "candidate_family_support": dict(self.candidate_family_support),
            "notes": list(self.notes),
        }


def _read_regions(actions: Sequence[ReferenceAction]) -> list[tuple[str, ...]]:
    regions: list[tuple[str, ...]] = []
    current: list[str] = []
    for action in actions:
        if action.effect.is_read_like:
            current.append(action.name)
            continue
        if current:
            regions.append(tuple(current))
            current = []
    if current:
        regions.append(tuple(current))
    return regions


def _block_reason(effect: EffectClass) -> str | None:
    if effect is EffectClass.UNKNOWN:
        return "UNKNOWN_EFFECT"
    if effect.is_read_like:
        return None
    return f"EFFECT_{effect.value}"


def analyze_reference_tasks(
    tasks: Sequence[ReferenceTask], *, min_region_length: int = 2
) -> ReferenceAnalysis:
    """Screen one benchmark for read-like regions and explicit barriers.

    Tasks from different benchmark revisions or substrates may not be pooled.  Repeated
    variants sharing a ``group_id`` count as one independent group.
    """

    if type(min_region_length) is not int or min_region_length < 1:
        raise ValueError("min_region_length must be a positive integer")
    retained = tuple(tasks)
    if not retained:
        raise ValueError("at least one reference task is required")
    benchmarks = {task.benchmark for task in retained}
    revisions = {task.source_revision for task in retained}
    substrates = {task.substrate for task in retained}
    if len(benchmarks) != 1 or len(revisions) != 1 or len(substrates) != 1:
        raise ValueError("reference analysis cannot pool benchmark revisions or substrates")

    effects: Counter[str] = Counter()
    blocks: Counter[str] = Counter()
    family_support: Counter[str] = Counter()
    families_by_group: dict[str, set[str]] = {}
    total_actions = 0
    tasks_with_actions = 0
    complete = 0
    with_candidate = 0
    with_barrier = 0
    with_unknown = 0
    max_region = 0

    for task in retained:
        actions = task.actions
        total_actions += len(actions)
        tasks_with_actions += bool(actions)
        complete += bool(actions) and all(action.output_observed for action in actions)
        task_barrier = False
        task_unknown = False
        for action in actions:
            effects[action.effect.value] += 1
            reason = _block_reason(action.effect)
            if reason is not None:
                blocks[reason] += 1
                task_barrier = True
            if action.effect is EffectClass.UNKNOWN:
                task_unknown = True
        with_barrier += task_barrier
        with_unknown += task_unknown
        regions = _read_regions(actions)
        task_max = max((len(region) for region in regions), default=0)
        max_region = max(max_region, task_max)
        with_candidate += task_max >= min_region_length
        group_families = families_by_group.setdefault(task.group_id, set())
        group_families.update(
            " -> ".join(region)
            for region in regions
            if len(region) >= min_region_length
        )

    # Support is an independent-group count, not a raw region-occurrence count. A task
    # can repeat the same plan and benchmark suites can expose variants of one lineage;
    # neither may inflate recurrence evidence.
    for group_families in families_by_group.values():
        family_support.update(group_families)

    sorted_families = dict(
        sorted(family_support.items(), key=lambda item: (-item[1], item[0]))
    )
    read_like = sum(
        count for effect, count in effects.items() if EffectClass(effect).is_read_like
    )
    return ReferenceAnalysis(
        benchmark=next(iter(benchmarks)),
        source_revision=next(iter(revisions)),
        substrate=next(iter(substrates)),
        tasks=len(retained),
        independent_groups=len({task.group_id for task in retained}),
        tasks_with_reference_actions=tasks_with_actions,
        complete_observed_traces=complete,
        total_actions=total_actions,
        read_like_actions=read_like,
        barrier_actions=total_actions - read_like,
        unknown_actions=effects[EffectClass.UNKNOWN.value],
        tasks_with_candidate_region=with_candidate,
        tasks_with_barrier=with_barrier,
        tasks_with_unknown=with_unknown,
        maximum_read_region=max_region,
        recurrent_candidate_families=sum(
            support >= 2 for support in sorted_families.values()
        ),
        maximum_candidate_family_support=max(sorted_families.values(), default=0),
        effect_counts=MappingProxyType(dict(sorted(effects.items()))),
        block_reason_counts=MappingProxyType(dict(sorted(blocks.items()))),
        candidate_family_support=MappingProxyType(sorted_families),
    )


def reference_task_to_episode(
    task: ReferenceTask,
    *,
    manifest: ExecutionManifest,
    outcome: OutcomeLabels | None = None,
    entry_state: Mapping[str, Any] | None = None,
) -> Episode:
    """Normalize a complete retained reference trace into the compiler's Episode IR."""

    if not task.actions:
        raise ValueError("reference task has no actions")
    if not all(action.output_observed for action in task.actions):
        raise ValueError("reference task lacks observed tool results")
    events: list[EventNode] = []
    timestamp = 0.0
    for index, action in enumerate(task.actions):
        request_id = f"{task.task_id}:request:{index}"
        call_id = f"{task.task_id}:call:{index}"
        events.extend(
            [
                EventNode(
                    node_id=request_id,
                    kind=EventKind.MODEL_REQ,
                    index=len(events),
                    input={"prompt": task.prompt if index == 0 else "", "turn": action.turn},
                    t_start_ms=timestamp,
                    t_end_ms=timestamp,
                    request_id=request_id,
                ),
                EventNode(
                    node_id=f"{request_id}:response",
                    kind=EventKind.MODEL_RESP,
                    index=len(events) + 1,
                    output={"tool": action.name, "arguments": _thaw(action.arguments)},
                    t_start_ms=timestamp,
                    t_end_ms=timestamp + 1.0,
                    request_id=request_id,
                ),
                EventNode(
                    node_id=call_id,
                    kind=EventKind.TOOL_CALL,
                    index=len(events) + 2,
                    tool=action.name,
                    input=_thaw(action.arguments),
                    t_start_ms=timestamp + 1.0,
                    t_end_ms=timestamp + 1.0,
                    call_id=call_id,
                    declared_effect=action.effect.value,
                    attributes={"requestor": action.requestor, "reference_trace": True},
                ),
                EventNode(
                    node_id=f"{call_id}:result",
                    kind=EventKind.TOOL_RESULT,
                    index=len(events) + 3,
                    tool=action.name,
                    output=_thaw(action.output),
                    t_start_ms=timestamp + 1.0,
                    t_end_ms=timestamp + 2.0,
                    call_id=call_id,
                    declared_effect=action.effect.value,
                    attributes={"requestor": action.requestor, "reference_trace": True},
                ),
            ]
        )
        timestamp += 2.0
    envelope = TraceEnvelope(
        trace_id=f"reference:{task.benchmark}:{task.task_id}",
        episode_id=f"reference:{task.benchmark}:{task.task_id}",
        group_id=task.group_id,
        manifest_id=manifest.manifest_id,
        principal="public-benchmark",
        tenant_partition=task.benchmark,
        policy_version="reference-plan-v1",
        privacy_class="public-benchmark",
        external_state_version=task.source_revision,
    )
    return Episode(
        envelope=envelope,
        manifest=manifest,
        entry_state=dict(entry_state or {}),
        events=events,
        outcome=outcome or OutcomeLabels(),
        attributes={
            "benchmark": task.benchmark,
            "reference_task_digest": task.digest,
            "evidence_substrate": task.substrate.value,
        },
    )
