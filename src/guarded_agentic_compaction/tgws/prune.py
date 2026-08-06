"""TGWS pruning: greedy backward elimination under non-inferiority constraints.

For each accepted route leaf, start from the baseline configuration and repeatedly
propose removing **one** element — a prompt block, a tool schema, a handoff option,
or a reasoning tier. A removal is accepted only if it improves the objective *and*
passes quality and safety non-inferiority on grouped development cases
(execution-plan §8.1 steps 5-6, §9.4).

The evaluator is injected. That is deliberate: the only honest way to know whether
removing ``billing_rules`` from the prompt hurts is to run the workload, so the
caller supplies a callable that executes the configuration on a set of dev groups
and returns measured quality, requests, tokens, latency and safety events. Nothing
here estimates quality from a proxy.

Greedy elimination misses interacting removals. That is accepted for v0.1
(execution-plan §8.1 tradeoffs); a MIPRO/DSPy-style proposer would be an
evaluation-only comparator, not a replacement for the gate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Iterable, Sequence

__all__ = ["LeafConfig", "EvalResult", "Objective", "PruneTrace", "prune_leaf"]


@dataclass(frozen=True, slots=True)
class LeafConfig:
    """The configuration surface TGWS is allowed to shrink."""

    agent: str
    model: str
    reasoning_tier: str
    prompt_blocks: tuple[str, ...]
    tools: tuple[str, ...]
    handoffs: tuple[str, ...] = ()

    def without_block(self, block: str) -> "LeafConfig":
        return replace(self, prompt_blocks=tuple(b for b in self.prompt_blocks if b != block))

    def without_tool(self, tool: str) -> "LeafConfig":
        return replace(self, tools=tuple(t for t in self.tools if t != tool))

    def without_handoff(self, target: str) -> "LeafConfig":
        return replace(self, handoffs=tuple(h for h in self.handoffs if h != target))

    def with_tier(self, tier: str) -> "LeafConfig":
        return replace(self, reasoning_tier=tier)

    @property
    def size(self) -> int:
        return len(self.prompt_blocks) + len(self.tools) + len(self.handoffs)


@dataclass(frozen=True, slots=True)
class EvalResult:
    """Measured behaviour of one configuration on a set of dev groups."""

    quality: float
    requests: float
    input_tokens: float
    output_tokens: float
    latency_ms: float
    safety_events: int
    n_episodes: int
    success_rate: float = 0.0
    schema_tokens: float = 0.0
    prompt_tokens: float = 0.0
    extra: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Objective:
    """Weights of the TGWS objective (execution-plan §9.4)."""

    alpha_requests: float = 1.0
    beta_tokens: float = 0.0008
    gamma_latency: float = 0.0004
    eta_tools: float = 0.02
    mu_complexity: float = 0.01
    epsilon_quality: float = 0.02
    epsilon_success_rate: float = 0.02

    def value(self, r: EvalResult, config: LeafConfig) -> float:
        return (
            self.alpha_requests * r.requests
            + self.beta_tokens * (r.input_tokens + r.output_tokens)
            + self.gamma_latency * r.latency_ms
            + self.eta_tools * len(config.tools)
            + self.mu_complexity * config.size
        )


@dataclass(slots=True)
class PruneTrace:
    """Audit trail: every proposal, its measurement, and why it was accepted."""

    steps: list[dict[str, Any]] = field(default_factory=list)
    evaluations: int = 0

    def record(self, kind: str, item: str, accepted: bool, reason: str, objective: float) -> None:
        self.steps.append(
            {
                "kind": kind,
                "item": item,
                "accepted": accepted,
                "reason": reason,
                "objective": round(objective, 4),
            }
        )


def prune_leaf(
    baseline: LeafConfig,
    evaluate: Callable[[LeafConfig], EvalResult],
    *,
    objective: Objective = Objective(),
    protected_tools: Sequence[str] = (),
    protected_blocks: Sequence[str] = (),
    tiers: Sequence[str] = (),
    budget: int = 120,
) -> tuple[LeafConfig, EvalResult, PruneTrace]:
    """Greedy backward elimination. Returns the accepted configuration and its trace."""

    trace = PruneTrace()
    base_result = evaluate(baseline)
    trace.evaluations += 1
    current = baseline
    current_result = base_result
    current_obj = objective.value(base_result, current)

    def noninferior(candidate: EvalResult) -> tuple[bool, str]:
        if candidate.quality < base_result.quality - objective.epsilon_quality:
            return False, f"quality {candidate.quality:.4f} < {base_result.quality:.4f}-ε"
        if candidate.success_rate < base_result.success_rate - objective.epsilon_success_rate:
            return (
                False,
                f"success {candidate.success_rate:.4f} < "
                f"{base_result.success_rate:.4f}-ε",
            )
        if candidate.safety_events > base_result.safety_events:
            return False, f"safety {candidate.safety_events} > {base_result.safety_events}"
        return True, ""

    while trace.evaluations < budget:
        proposals: list[tuple[str, str, LeafConfig]] = []
        for block in current.prompt_blocks:
            if block not in protected_blocks:
                proposals.append(("prompt_block", block, current.without_block(block)))
        for tool in current.tools:
            if tool not in protected_tools:
                proposals.append(("tool", tool, current.without_tool(tool)))
        for target in current.handoffs:
            proposals.append(("handoff", target, current.without_handoff(target)))
        for tier in tiers:
            if tier != current.reasoning_tier:
                proposals.append(("reasoning_tier", tier, current.with_tier(tier)))
        if not proposals:
            break

        best: tuple[float, str, str, LeafConfig, EvalResult] | None = None
        for kind, item, cand in proposals:
            if trace.evaluations >= budget:
                break
            result = evaluate(cand)
            trace.evaluations += 1
            ok, why = noninferior(result)
            obj = objective.value(result, cand)
            if not ok:
                trace.record(kind, item, False, why, obj)
                continue
            if obj >= current_obj - 1e-9:
                trace.record(kind, item, False, f"objective {obj:.4f} ≥ {current_obj:.4f}", obj)
                continue
            trace.record(kind, item, True, "candidate", obj)
            if best is None or obj < best[0]:
                best = (obj, kind, item, cand, result)

        if best is None:
            break
        current_obj, kind, item, current, current_result = best
        trace.record(kind, item, True, "accepted", current_obj)

    return current, current_result, trace
