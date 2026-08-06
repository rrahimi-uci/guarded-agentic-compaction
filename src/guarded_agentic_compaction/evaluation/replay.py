"""Replay modes (execution-plan §7).

Four modes with strictly different evidentiary value, kept apart on purpose:

===================  ==================================================  ==========================
mode                 permitted behaviour                                 evidence
===================  ==================================================  ==========================
recorded             no external calls; historical observations only      bindings, determinism, gate
sandbox              isolated live reads/writes against a fresh world     new-path and failure behaviour
shadow               baseline does the real work; candidate commits none  coverage, agreement, drift
canary               narrow live scope under an approved effect policy    operational impact
===================  ==================================================  ==========================

Recorded replay cannot prove that a new call ordering works against live state, and
sandbox replay cannot prove anything about production distribution. The reports
therefore never merge.

**Declared equivalence.** A fresh sandbox mints a fresh session handle, so an exact
live-out comparison would fail for reasons that have nothing to do with the
program. Equivalence is derived from the catalog rather than hand-waved: a tool
declared ``cacheable`` must return the same value for the same key, so it is
compared exactly; a tool without ``cacheable`` (a token mint, a paginated feed) is
compared structurally — same shape, same types, same cardinality.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Sequence

from ..grc.program import CallStep, LoopStep, Program
from ..runtime.facade import FacadeMode, Recording, ToolFacade
from ..runtime.interp import run_program
from ..schema.artifacts import HardGuard, Verifier
from ..schema.effects import Capability, EffectCatalog

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..graph.windows import Window

__all__ = ["sandbox_replay", "equivalent", "structural_shape"]


def structural_shape(value: Any, depth: int = 0) -> Any:
    """Type/cardinality skeleton of a payload, used for declared equivalence."""

    if depth > 5:
        return "..."
    if isinstance(value, dict):
        return {k: structural_shape(v, depth + 1) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return ["list", len(value)] + [structural_shape(v, depth + 1) for v in value[:1]]
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    return type(value).__name__


def equivalent(recorded: Any, actual: Any, tool: str, catalog: EffectCatalog) -> bool:
    spec = catalog.get(tool)
    if Capability.CACHEABLE in spec.capabilities:
        return recorded == actual
    return structural_shape(recorded) == structural_shape(actual)


def sandbox_replay(
    program: Program,
    guard: HardGuard,
    verifier: Verifier,
    windows: Sequence[Window],
    names: Sequence[str],
    catalog: EffectCatalog,
    sandbox: Callable[[], Any],
    *,
    executor_attr: str = "execute",
) -> "ReplayReport":
    """Algorithm 5 lines 8-12: replay ``P`` against a fresh world at the recorded ``z``."""

    from ..grc.contracts import ReplayReport  # local import: contracts imports us

    rep = ReplayReport()
    tool_by_var = {s.var: s.tool for s in program.steps if isinstance(s, (CallStep, LoopStep))}
    for w in windows:
        rep.n += 1
        world = sandbox()
        before = world.state_digest()
        executor = getattr(world, executor_attr)
        facade = ToolFacade(
            catalog=catalog,
            mode=FacadeMode.SANDBOX,
            executor=lambda tool, args, _ex=executor: _ex(tool, args),
            allowed_tools=tuple(program.tools),
            max_calls=32,
        )
        result = run_program(program, w.episode.entry_state, facade)
        if not result.ok:
            if world.state_digest() != before:
                rep.state_delta += 1
                rep.reasons["state_digest_delta_on_abstain"] += 1
                continue
            rep.abstained += 1
            rep.reasons[result.error.split(":")[0][:48]] += 1
            continue
        bad = verifier.verify(result.outputs, result.env, result.provenance, result.effects, len(result.calls))
        if bad:
            if world.state_digest() != before:
                rep.state_delta += 1
                rep.reasons["state_digest_delta_on_verifier"] += 1
                continue
            rep.abstained += 1
            rep.reasons["verifier:" + bad[0]] += 1
            continue
        # live-out equivalence against the recorded run
        wrong: list[str] = []
        for i in range(min(len(names), len(w.steps))):
            var = names[i]
            recorded = _recorded(w, i)
            got = result.outputs.get(var)
            if recorded is None and got is None:
                continue
            if recorded is None or got is None or not equivalent(
                recorded, got, tool_by_var.get(var, ""), catalog
            ):
                wrong.append(var)
        if wrong:
            rep.wrong += 1
            rep.reasons["live_out_mismatch"] += 1
            rep.counterexamples.append(
                {"episode": w.episode.episode_id, "kind": "sandbox_live_out_mismatch", "fields": wrong}
            )
            continue
        if world.state_digest() != before:
            rep.state_delta += 1
            rep.reasons["state_digest_delta"] += 1
            continue
        rep.passed += 1
    return rep


def _recorded(w: Window, i: int) -> Any:
    step = w.steps[i]
    if not step.result_positions:
        return None
    return w.patg.order[step.result_positions[-1]].output
