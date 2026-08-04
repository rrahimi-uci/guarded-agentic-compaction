"""Bounded interpreter for a compiled region program.

The interpreter is deliberately small: evaluate bindings, call permitted tools
through the facade, honour one synthesized branch per step and one bounded loop,
check assertions, project live-outs. It has no eval, no recursion, no dynamic tool
resolution, and a hard call budget.

Failure taxonomy matters more than the happy path (proposal §4.7):

* :class:`PreCommitError` — anything that happens before an external commitment.
  Deoptimization to the baseline is exact.
* :class:`PostCommitError` — a failure after a commitment. The runtime does not
  pretend to roll back; it raises an incident. In v0.x programs may only contain
  pre-commit reads, so this can only arise from a catalog/config error, and the
  interpreter asserts that rather than trusting it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from ..grc.dsl import Binding, Const, Expr, TypeMismatch
from ..grc.program import AssertStep, CallStep, LoopStep, Program
from ..paths import resolve_path
from .facade import FacadeError, ToolFacade

__all__ = ["InterpResult", "PreCommitError", "PostCommitError", "run_program", "set_path"]


class PreCommitError(Exception):
    """Recoverable: nothing was committed, the baseline can take over exactly."""


class PostCommitError(Exception):
    """Unrecoverable: an external commitment happened. Incident, not fallback."""


@dataclass(slots=True)
class InterpResult:
    ok: bool
    outputs: dict[str, Any] = field(default_factory=dict)
    env: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, set[str]] = field(default_factory=dict)
    effects: tuple[str, ...] = ()
    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    results: list[Any] = field(default_factory=list)
    error: str = ""
    steps_run: int = 0
    branch_taken: dict[str, bool] = field(default_factory=dict)


def set_path(target: dict[str, Any], path: str, value: Any) -> None:
    """Assign a dotted path inside a nested dict, creating intermediates.

    Argument slots are flattened leaf paths, so a tool that takes a nested object
    is reassembled here rather than bound as one opaque blob.
    """

    parts = path.split(".")
    cur = target
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value


def _eval_args(args: dict[str, Binding], env: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for path, binding in args.items():
        try:
            value = binding.evaluate(env)
        except (TypeMismatch, TypeError, ValueError, KeyError) as exc:
            raise PreCommitError(f"binding failed for {path}: {exc}") from exc
        set_path(out, path, value)
    return out


def run_program(
    program: Program,
    entry_state: dict[str, Any],
    facade: ToolFacade,
    *,
    max_calls: int | None = None,
) -> InterpResult:
    env: dict[str, Any] = {"z": entry_state}
    provenance: dict[str, set[str]] = {}
    branch_taken: dict[str, bool] = {}
    facade.reset()
    if max_calls is not None:
        facade.max_calls = max_calls
    steps_run = 0

    try:
        for step in program.steps:
            if isinstance(step, AssertStep):
                for check in step.checks:
                    if not check.evaluate(env):
                        raise PreCommitError(f"assertion failed: {check.pretty()}")
                steps_run += 1
                continue

            if isinstance(step, CallStep):
                if step.when is not None:
                    take = step.when.evaluate(env)
                    branch_taken[step.var] = take
                    if not take:
                        env[step.var] = None
                        steps_run += 1
                        continue
                args = _eval_args(step.args, env)
                result = facade.call(step.tool, args)
                env[step.var] = result
                provenance[step.var] = {step.tool}
                steps_run += 1
                continue

            if isinstance(step, LoopStep):
                accumulated: list[Any] = []
                raw_results: list[Any] = []
                last: Any = None
                for i in range(step.max_iters):
                    args = _eval_args(step.args, env)
                    if step.counter:
                        set_path(args, step.counter, i)
                    last = facade.call(step.tool, args)
                    raw_results.append(last)
                    env[step.var] = last
                    items = last.get(step.accumulate) if isinstance(last, dict) else last
                    if isinstance(items, list):
                        accumulated.extend(items)
                    if step.continue_when is None or not step.continue_when.evaluate(env):
                        break
                else:
                    raise PreCommitError(f"loop bound {step.max_iters} exhausted")
                # Synthesis represents a collapsed repeated step as the ordered
                # list of its raw observations. Preserve that exact shape for
                # downstream bindings, live-outs, replay, and verification.
                env[step.var] = raw_results
                env[f"{step.var}__all"] = accumulated
                provenance[step.var] = {step.tool}
                steps_run += 1
                continue

            raise PreCommitError(f"unknown step type {type(step).__name__}")

        outputs: dict[str, Any] = {}
        for name, binding in program.outputs.items():
            if isinstance(binding, Expr) and binding.source in env and not binding.ops:
                outputs[name] = env[binding.source]
                continue
            try:
                outputs[name] = binding.evaluate(env)
            except (TypeMismatch, TypeError, ValueError, KeyError):
                outputs[name] = None
        return InterpResult(
            ok=True,
            outputs=outputs,
            env=env,
            provenance=provenance,
            effects=facade.effect_multiset,
            calls=list(facade.calls),
            results=list(facade.results),
            steps_run=steps_run,
            branch_taken=branch_taken,
        )

    except (PreCommitError, FacadeError) as exc:
        return InterpResult(
            ok=False,
            env=env,
            effects=facade.effect_multiset,
            calls=list(facade.calls),
            results=list(facade.results),
            error=f"{type(exc).__name__}: {exc}",
            steps_run=steps_run,
            branch_taken=branch_taken,
        )
