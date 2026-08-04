"""Deterministic offline stress engine and test-fixture substrate.

Why a simulator. The compaction pipeline is offline and evidence-gated: to
measure a request ratio, a non-inferiority interval, or a calibrated unsafe
dispatch bound you need thousands of paired episodes with ground-truth outcomes
and a resettable world. Neither a provider API nor a production deployment gives
that reproducibly on a laptop, and proposal §6.3 is explicit that *you cannot
replay production*.

The user-facing demos now run through ``experiments/live_run.py`` using real OpenAI
Agents SDK model calls. This module remains a **simulated stress workload**: a
deterministic tool world plus a scripted policy that stands in for the model at each
request boundary. Everything
downstream of the trace envelope — provenance, mining, synthesis, contracts,
calibration, dispatch, statistics — is the real implementation running on real
traces of this workload. Every number produced from it is labelled
``substrate=simulated`` in the run manifest and must never be quoted as a
production or provider measurement (execution-plan §13.6).

The policy is *not* a stub that always does the same thing: it carries a declared
deviation rate, alternative paths, occasional redundant calls, entity-shape
surprises (merged accounts, empty result sets), and drifting arms, because a
substrate without variance cannot falsify a gate.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Protocol, Sequence

from agent_compaction.schema.traces import (
    Episode,
    EventKind,
    EventNode,
    ExecutionManifest,
    OutcomeLabels,
    TraceEnvelope,
    Usage,
    content_digest,
)

__all__ = [
    "Call",
    "Finish",
    "Think",
    "HandoffAction",
    "Action",
    "ToolSpec",
    "World",
    "Policy",
    "PolicyContext",
    "CostModel",
    "EpisodeSpec",
    "run_episode",
    "ToolError",
    "Observation",
]


# ---------------------------------------------------------------------------
# actions
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Call:
    tool: str
    args: dict[str, Any]
    parallel_group: str | None = None


@dataclass(frozen=True, slots=True)
class Finish:
    answer: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Think:
    """A model request that emits a message rather than a tool call.

    Diagnosis and drafting turns are real model-request boundaries and belong in
    ``n_B``; excluding them would inflate every ratio in the results.
    """

    note: str = ""


@dataclass(frozen=True, slots=True)
class HandoffAction:
    target: str
    reason: str = ""


Action = Call | Finish | Think | HandoffAction


class ToolError(Exception):
    """Simulated tool failure (4xx/5xx/timeout) used by fault injection."""

    def __init__(self, message: str, status: str = "error") -> None:
        super().__init__(message)
        self.status = status


@dataclass(frozen=True, slots=True)
class Observation:
    tool: str
    args: dict[str, Any]
    result: Any
    status: str = "ok"


# ---------------------------------------------------------------------------
# tools + world
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ToolSpec:
    name: str
    fn: Callable[..., Any]
    latency_ms: float = 40.0
    schema_tokens: int = 120
    resource: str = ""


class World:
    """Base class for a demo world.

    A world owns state, records the effect multiset of everything executed
    against it, counts quota, and can be reset — the three properties production
    lacks and the reason the perturbation suite of Algorithm 5 can run here at
    all.
    """

    name = "world"

    def __init__(self, seed: int = 0) -> None:
        self.seed = seed
        self.rng = random.Random(seed)
        self.tools: dict[str, ToolSpec] = {}
        self.effect_log: list[str] = []
        self.call_log: list[tuple[str, dict[str, Any]]] = []
        self.quota: dict[str, int] = {}
        self.faults: dict[str, str] = {}
        self.committed: list[dict[str, Any]] = []
        self.register_tools()

    # -- registration -----------------------------------------------------
    def register_tools(self) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    def tool(
        self,
        name: str,
        fn: Callable[..., Any],
        *,
        latency_ms: float = 40.0,
        schema_tokens: int = 120,
        resource: str = "",
    ) -> None:
        self.tools[name] = ToolSpec(name, fn, latency_ms, schema_tokens, resource or name.split(".")[0])

    # -- execution --------------------------------------------------------
    def execute(self, tool: str, args: dict[str, Any]) -> Any:
        spec = self.tools.get(tool)
        if spec is None:
            raise ToolError(f"unknown tool {tool}", status="error")
        if tool in self.faults:
            self.quota[tool] = self.quota.get(tool, 0) + 1
            raise ToolError(f"injected fault on {tool}", status=self.faults[tool])
        self.call_log.append((tool, dict(args)))
        self.quota[tool] = self.quota.get(tool, 0) + 1
        return spec.fn(**args)

    def latency_of(self, tool: str) -> float:
        spec = self.tools.get(tool)
        return spec.latency_ms if spec else 30.0

    def schema_tokens(self, tools: Iterable[str]) -> int:
        return sum(self.tools[t].schema_tokens for t in tools if t in self.tools)

    def inject_fault(self, tool: str, status: str = "error") -> None:
        self.faults[tool] = status

    def clear_faults(self) -> None:
        self.faults.clear()

    def state_digest(self) -> str:
        """Digest of *business* state. Reads must not change it."""

        return content_digest(self.committed)

    def reset_logs(self) -> None:
        self.effect_log.clear()
        self.call_log.clear()

    # -- grading ----------------------------------------------------------
    def grade(self, entry_state: dict[str, Any], observations: Sequence[Observation], answer: dict[str, Any]) -> OutcomeLabels:  # pragma: no cover - overridden
        raise NotImplementedError


# ---------------------------------------------------------------------------
# policy
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class PolicyContext:
    entry_state: dict[str, Any]
    observations: list[Observation]
    rng: random.Random
    #: A policy RNG stream *separate* from the cost model's. Paired comparisons
    #: between conditions are only valid if the policy's per-episode deviation
    #: draws do not shift when a condition removes model requests: sharing one
    #: stream makes every removed request re-roll every later deviation, which
    #: shows up as spurious quality and safety differences.
    policy_rng: random.Random | None = None
    agent: str = "root"
    step: int = 0
    scratch: dict[str, Any] = field(default_factory=dict)

    def obs_for(self, tool: str) -> Observation | None:
        for o in reversed(self.observations):
            if o.tool == tool and o.status == "ok":
                return o
        return None

    def has(self, tool: str) -> bool:
        """True when a *successful* observation exists."""

        return self.obs_for(tool) is not None

    def attempted(self, tool: str) -> bool:
        """True when the tool was called at all, successfully or not.

        Policies branch on this rather than on :meth:`has` so that an injected
        fault produces one abstention rather than an infinite retry loop.
        """

        return any(o.tool == tool for o in self.observations)

    def results_for(self, tool: str) -> list[Any]:
        return [o.result for o in self.observations if o.tool == tool and o.status == "ok"]


class Policy(Protocol):
    """A scripted stand-in for the model at one request boundary."""

    name: str

    def prompt_blocks(self, ctx: PolicyContext) -> tuple[str, ...]: ...

    def exposed_tools(self, ctx: PolicyContext) -> tuple[str, ...]: ...

    def act(self, ctx: PolicyContext) -> Action: ...


# ---------------------------------------------------------------------------
# cost model
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class CostModel:
    """Token / latency / dollar model for simulated model requests.

    Cache decomposition matters: proposal §3.4 warns that removing a request
    removes a mostly-cached prefill, so dollar savings lag request savings. That
    asymmetry is modelled explicitly rather than assumed away.
    """

    prompt_block_tokens: int = 220
    history_tokens_per_obs: int = 180
    output_tokens_mean: float = 70.0
    cache_hit_fraction: float = 0.9
    # per *million* tokens, the unit providers actually publish
    price_in_cold_per_mtok: float = 1.25
    price_in_cached_per_mtok: float = 0.125
    price_out_per_mtok: float = 10.0
    base_latency_ms: float = 260.0
    latency_per_output_token_ms: float = 3.2
    latency_jitter_ms: float = 60.0

    def usage(self, *, n_prompt_blocks: int, schema_tokens: int, n_obs: int, first: bool, rng: random.Random) -> Usage:
        static = self.prompt_block_tokens * n_prompt_blocks + schema_tokens
        dynamic = self.history_tokens_per_obs * n_obs
        cached = 0 if first else int(static * self.cache_hit_fraction)
        cold = static - cached + dynamic
        out = max(8, int(rng.gauss(self.output_tokens_mean, self.output_tokens_mean * 0.25)))
        return Usage(input_tokens=cold, cached_input_tokens=cached, output_tokens=out)

    def latency_ms(self, usage: Usage, rng: random.Random) -> float:
        return max(
            30.0,
            self.base_latency_ms
            + self.latency_per_output_token_ms * usage.output_tokens
            + rng.gauss(0.0, self.latency_jitter_ms),
        )

    def dollars(self, usage: Usage) -> float:
        return (
            usage.input_tokens / 1e6 * self.price_in_cold_per_mtok
            + usage.cached_input_tokens / 1e6 * self.price_in_cached_per_mtok
            + usage.output_tokens / 1e6 * self.price_out_per_mtok
        )


# ---------------------------------------------------------------------------
# episode runner
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class EpisodeSpec:
    episode_id: str
    group_id: str
    entry_state: dict[str, Any]
    principal: str = "unknown"
    tenant_partition: str = "unknown"
    policy_version: str = "v0"
    day: str = "1970-01-01"
    seed: int = 0
    external_state_version: str = "idx-1"


class Dispatcher(Protocol):
    """Runtime hook evaluated at every model-request boundary (Algorithm 7)."""

    def on_boundary(
        self,
        spec: EpisodeSpec,
        manifest: ExecutionManifest,
        ctx: PolicyContext,
        world: World,
    ) -> Any: ...


def run_episode(
    *,
    spec: EpisodeSpec,
    world: World,
    policy: Policy,
    manifest: ExecutionManifest,
    cost: CostModel | None = None,
    dispatcher: Any | None = None,
    max_steps: int = 40,
) -> Episode:
    """Run one episode and emit a fully typed :class:`Episode`.

    When ``dispatcher`` is supplied it is consulted *before* each model request.
    If it returns a compaction result, the observations it produced are appended
    to history and **no model request is emitted** — that is where ``k`` requests
    per dispatch actually disappear from the measurement.
    """

    cost = cost or CostModel()
    rng = random.Random(spec.seed)
    ctx = PolicyContext(
        entry_state=spec.entry_state,
        observations=[],
        rng=rng,
        policy_rng=random.Random(spec.seed ^ 0x5EED5EED),
    )
    events: list[EventNode] = []
    clock = 0.0
    n = 0
    answer: dict[str, Any] = {}
    dispatch_records: list[dict[str, Any]] = []
    first_request = True

    def push(node: EventNode) -> None:
        events.append(node)

    while n < max_steps:
        # ---- Algorithm 7: dispatch decision at the boundary --------------
        if dispatcher is not None:
            decision = dispatcher.on_boundary(spec, manifest, ctx, world)
            if decision is not None and getattr(decision, "compacted", False):
                for obs in decision.observations:
                    ctx.observations.append(obs)
                    call_node = EventNode(
                        node_id=f"{spec.episode_id}:c{len(events)}",
                        kind=EventKind.TOOL_CALL,
                        index=len(events),
                        actor=ctx.agent,
                        tool=obs.tool,
                        input=obs.args,
                        t_start_ms=clock,
                        t_end_ms=clock + world.latency_of(obs.tool),
                        attributes={"compacted": True},
                    )
                    clock = call_node.t_end_ms
                    push(call_node)
                    push(
                        EventNode(
                            node_id=f"{spec.episode_id}:r{len(events)}",
                            kind=EventKind.TOOL_RESULT,
                            index=len(events),
                            actor=obs.tool,
                            tool=obs.tool,
                            output=obs.result,
                            status=obs.status,
                            t_start_ms=clock,
                            t_end_ms=clock,
                            attributes={"compacted": True},
                        )
                    )
                clock += decision.overhead_ms
                dispatch_records.append(decision.record)
                ctx.step += 1
                continue
            if decision is not None:
                clock += decision.overhead_ms
                dispatch_records.append(decision.record)

        # ---- ordinary model request --------------------------------------
        blocks = policy.prompt_blocks(ctx)
        tools = policy.exposed_tools(ctx)
        usage = cost.usage(
            n_prompt_blocks=len(blocks),
            schema_tokens=world.schema_tokens(tools),
            n_obs=len(ctx.observations),
            first=first_request,
            rng=rng,
        )
        first_request = False
        lat = cost.latency_ms(usage, rng)
        req = EventNode(
            node_id=f"{spec.episode_id}:q{len(events)}",
            kind=EventKind.MODEL_REQ,
            index=len(events),
            actor=ctx.agent,
            input={
                "prompt_blocks": list(blocks),
                "tools": list(tools),
                "n_observations": len(ctx.observations),
            },
            t_start_ms=clock,
            t_end_ms=clock + lat,
            usage=usage,
            request_id=f"req_{spec.episode_id}_{n}",
            attributes={
                "prompt_tokens": cost.prompt_block_tokens * len(blocks),
                "schema_tokens": world.schema_tokens(tools),
                "dollars": cost.dollars(usage),
            },
        )
        clock = req.t_end_ms
        push(req)
        n += 1

        action = policy.act(ctx)
        push(
            EventNode(
                node_id=f"{spec.episode_id}:a{len(events)}",
                kind=EventKind.MODEL_RESP,
                index=len(events),
                actor=ctx.agent,
                output=_action_payload(action),
                t_start_ms=clock,
                t_end_ms=clock,
                request_id=req.request_id,
            )
        )

        if isinstance(action, Finish):
            answer = action.answer
            break

        if isinstance(action, Think):
            ctx.scratch["thoughts"] = ctx.scratch.get("thoughts", 0) + 1
            ctx.step += 1
            continue

        if isinstance(action, HandoffAction):
            push(
                EventNode(
                    node_id=f"{spec.episode_id}:h{len(events)}",
                    kind=EventKind.HANDOFF,
                    index=len(events),
                    actor=ctx.agent,
                    output={"target": action.target, "reason": action.reason},
                    t_start_ms=clock,
                    t_end_ms=clock,
                )
            )
            ctx.agent = action.target
            ctx.step += 1
            continue

        # ---- tool call ---------------------------------------------------
        call = EventNode(
            node_id=f"{spec.episode_id}:c{len(events)}",
            kind=EventKind.TOOL_CALL,
            index=len(events),
            actor=ctx.agent,
            tool=action.tool,
            input=action.args,
            t_start_ms=clock,
            t_end_ms=clock + world.latency_of(action.tool),
            call_id=f"call_{spec.episode_id}_{n}",
            attributes={"parallel_group": action.parallel_group} if action.parallel_group else {},
        )
        clock = call.t_end_ms
        push(call)
        try:
            result = world.execute(action.tool, action.args)
            status = "ok"
        except ToolError as exc:
            result = {"error": str(exc)}
            status = exc.status
        obs = Observation(action.tool, dict(action.args), result, status)
        ctx.observations.append(obs)
        push(
            EventNode(
                node_id=f"{spec.episode_id}:r{len(events)}",
                kind=EventKind.TOOL_RESULT,
                index=len(events),
                actor=action.tool,
                tool=action.tool,
                output=result,
                status=status,
                t_start_ms=clock,
                t_end_ms=clock,
                call_id=call.call_id,
                attributes=dict(call.attributes),
            )
        )
        ctx.step += 1

    outcome = world.grade(spec.entry_state, ctx.observations, answer)
    envelope = TraceEnvelope(
        trace_id=f"tr_{spec.episode_id}",
        episode_id=spec.episode_id,
        group_id=spec.group_id,
        manifest_id=manifest.manifest_id,
        principal=spec.principal,
        tenant_partition=spec.tenant_partition,
        policy_version=spec.policy_version,
        day=spec.day,
        entry_state_ref=content_digest(spec.entry_state),
        external_state_version=spec.external_state_version,
    )
    return Episode(
        envelope=envelope,
        manifest=manifest,
        entry_state=spec.entry_state,
        events=events,
        outcome=outcome,
        final_state_digest=world.state_digest(),
        attributes={
            "answer": answer,
            "dispatch_records": dispatch_records,
            "dollars": sum(e.attributes.get("dollars", 0.0) for e in events),
            "policy": policy.name,
            "substrate": "simulated",
        },
    )


def _action_payload(action: Action) -> dict[str, Any]:
    if isinstance(action, Call):
        return {"type": "function_call", "tool": action.tool, "arguments": action.args}
    if isinstance(action, Finish):
        return {"type": "message", "answer": action.answer}
    if isinstance(action, Think):
        return {"type": "message", "note": action.note}
    return {"type": "handoff", "target": action.target}


# ---------------------------------------------------------------------------
# workload helpers used by TGWS pruning and by the experiment conditions
# ---------------------------------------------------------------------------


def run_workload(
    specs: Sequence[EpisodeSpec],
    world: World,
    policy: Policy,
    manifest: ExecutionManifest,
    *,
    cost: CostModel | None = None,
    dispatcher: Any | None = None,
) -> list[Episode]:
    """Run a list of episode specs and return the captured episodes."""

    cost = cost or CostModel()
    return [
        run_episode(spec=spec, world=world, policy=policy, manifest=manifest, cost=cost, dispatcher=dispatcher)
        for spec in specs
    ]


def summarize(episodes: Sequence[Episode]) -> dict[str, float]:
    """Per-episode means of everything the evaluation plan reports."""

    import statistics as st

    n = len(episodes)
    if not n:
        return {}
    usage = [ep.usage() for ep in episodes]
    lat = [ep.latency_ms() for ep in episodes]
    scores = [ep.outcome.semantic_score or 0.0 for ep in episodes]
    first_req = []
    for ep in episodes:
        b = ep.boundaries()
        if b:
            first_req.append(b[0].attributes)
    return {
        "n_episodes": float(n),
        "requests": sum(ep.n_requests() for ep in episodes) / n,
        "tool_calls": sum(len(ep.tool_calls()) for ep in episodes) / n,
        "input_tokens": sum(u.input_tokens for u in usage) / n,
        "cached_input_tokens": sum(u.cached_input_tokens for u in usage) / n,
        "output_tokens": sum(u.output_tokens for u in usage) / n,
        "dollars": sum(ep.attributes.get("dollars", 0.0) for ep in episodes) / n,
        "latency_ms_mean": sum(lat) / n,
        "latency_ms_p50": st.median(lat),
        "latency_ms_p95": sorted(lat)[min(n - 1, int(0.95 * n))],
        "latency_ms_p99": sorted(lat)[min(n - 1, int(0.99 * n))],
        "critical_path_ms": sum(ep.critical_path_ms() for ep in episodes) / n,
        "quality": sum(scores) / n,
        "success_rate": sum(1.0 for ep in episodes if ep.outcome.task_success) / n,
        "safety_events": float(sum(ep.outcome.safety_events for ep in episodes)),
        "prompt_tokens": sum(a.get("prompt_tokens", 0) for a in first_req) / max(1, len(first_req)),
        "schema_tokens": sum(a.get("schema_tokens", 0) for a in first_req) / max(1, len(first_req)),
        "dispatches": float(sum(len(ep.attributes.get("dispatch_records", [])) for ep in episodes)),
        "compacted_episodes": float(
            sum(
                1
                for ep in episodes
                if any(r.get("outcome") == "COMPACTED" for r in ep.attributes.get("dispatch_records", []))
            )
        ),
    }


def make_tgws_evaluator(
    specs_by_id: dict[str, EpisodeSpec],
    world_factory: Callable[[], World],
    policy_factory: Callable[[Any], Policy],
    manifest: ExecutionManifest,
    *,
    cost: CostModel | None = None,
) -> Callable[[Any, Sequence[Episode], Any], Any]:
    """Build the evaluator TGWS pruning needs: run the workload for real.

    There is no proxy for "does removing this prompt block hurt": the configuration
    is executed on the leaf's development episodes and measured.
    """

    from agent_compaction.tgws.prune import EvalResult

    def evaluate(leaf: Any, episodes: Sequence[Episode], config: Any) -> Any:
        specs = [specs_by_id[ep.episode_id] for ep in episodes if ep.episode_id in specs_by_id]
        world = world_factory()
        runs = run_workload(specs, world, policy_factory(config), manifest, cost=cost)
        m = summarize(runs)
        return EvalResult(
            quality=m.get("quality", 0.0),
            requests=m.get("requests", 0.0),
            input_tokens=m.get("input_tokens", 0.0),
            output_tokens=m.get("output_tokens", 0.0),
            latency_ms=m.get("latency_ms_mean", 0.0),
            safety_events=int(m.get("safety_events", 0)),
            n_episodes=int(m.get("n_episodes", 0)),
            success_rate=m.get("success_rate", 0.0),
            prompt_tokens=m.get("prompt_tokens", 0.0),
            schema_tokens=m.get("schema_tokens", 0.0),
        )

    return evaluate
