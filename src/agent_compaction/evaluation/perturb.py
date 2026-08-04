"""Metamorphic perturbation suite (Algorithm 5 lines 13-17).

A perturbation is a *response transformer* plus an expectation. Transforming
observations rather than the world keeps the suite generic — it runs against a
sandbox when one exists and against the recording when it does not — and it makes
the oracle possible:

* ``invariant`` families (reorder, duplicate, pad) must not change the program's
  live-outs. The oracle is the unperturbed run of the same program on the same
  episode, so no domain knowledge is needed. This is what catches a binding that
  happens to select the right record positionally: ``last |> project(id)`` and
  ``filter(status == "active") |> project(id)`` are indistinguishable on training
  data and differ the moment records are reordered.
* ``abstain`` families (tool errors, schema drift, emptied collections) must
  abstain or produce an invariant answer. A *wrong* answer is a hard reject.

Line 17 is the asymmetry the whole design rests on: abstention is acceptable,
silent wrongness is fatal.
"""

from __future__ import annotations

import copy
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Iterable, Sequence

from ..grc.program import CallStep, LoopStep, Program
from ..runtime.facade import FacadeMode, Recording, ToolFacade
from ..runtime.interp import InterpResult, run_program
from ..schema.artifacts import HardGuard, Verifier
from ..schema.effects import EffectCatalog
from .replay import structural_shape

__all__ = [
    "Perturbation",
    "DEFAULT_PERTURBATIONS",
    "run_perturbations",
    "reorder_lists",
    "duplicate_first_record",
]

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..graph.windows import Window

Transform = Callable[[str, dict[str, Any], Any], Any]


@dataclass(slots=True)
class Perturbation:
    """One perturbation family."""

    name: str
    family: str
    expect: str = "invariant"  # invariant | abstain | either
    transform: Transform | None = None
    mutate_entry: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    fail_tools: tuple[str, ...] = ()
    fail_status: str = "error"


# ---------------------------------------------------------------------------
# transforms
# ---------------------------------------------------------------------------


def _lists_in(value: Any) -> bool:
    return isinstance(value, list) or (
        isinstance(value, dict) and any(isinstance(v, list) for v in value.values())
    )


def reorder_lists(tool: str, args: dict[str, Any], result: Any) -> Any:
    """Reverse every list in the response. Semantics must not depend on order."""

    def rec(v: Any) -> Any:
        if isinstance(v, list):
            return [rec(x) for x in reversed(v)]
        if isinstance(v, dict):
            return {k: rec(x) for k, x in v.items()}
        return v

    return rec(copy.deepcopy(result))


def duplicate_first_record(tool: str, args: dict[str, Any], result: Any) -> Any:
    """Prepend a deactivated copy of the first record of every list.

    The copy is marked with every status-like field set to a non-active value, so a
    correct selection predicate still picks the original.
    """

    inactive = {"status": "closed", "state": "inactive", "active": False, "enabled": False}

    def clone(rec: Any) -> Any:
        if not isinstance(rec, dict):
            return rec
        out = copy.deepcopy(rec)
        touched = False
        for key, value in list(out.items()):
            if key in inactive:
                out[key] = inactive[key]
                touched = True
            elif key in ("id", "uuid") and isinstance(value, str):
                out[key] = value[:-1] + "0" if value[-1] != "0" else value[:-1] + "9"
        return out if touched else None

    def rec(v: Any) -> Any:
        if isinstance(v, list):
            items = [rec(x) for x in v]
            if items:
                dup = clone(items[0])
                if dup is not None:
                    return [dup] + items
            return items
        if isinstance(v, dict):
            return {k: rec(x) for k, x in v.items()}
        return v

    return rec(copy.deepcopy(result))


def pad_lists(tool: str, args: dict[str, Any], result: Any) -> Any:
    """Append a copy of the last element to every list (oversized collection)."""

    def rec(v: Any) -> Any:
        if isinstance(v, list):
            items = [rec(x) for x in v]
            return items + ([copy.deepcopy(items[-1])] if items else [])
        if isinstance(v, dict):
            return {k: rec(x) for k, x in v.items()}
        return v

    return rec(copy.deepcopy(result))


def empty_lists(tool: str, args: dict[str, Any], result: Any) -> Any:
    def rec(v: Any) -> Any:
        if isinstance(v, list):
            return []
        if isinstance(v, dict):
            return {k: rec(x) for k, x in v.items()}
        return v

    return rec(copy.deepcopy(result))


def null_optional_fields(tool: str, args: dict[str, Any], result: Any) -> Any:
    """Null out the last scalar field of every object."""

    def rec(v: Any) -> Any:
        if isinstance(v, dict):
            out = {k: rec(x) for k, x in v.items()}
            scalars = [k for k, x in out.items() if not isinstance(x, (dict, list))]
            if len(scalars) > 1:
                out[scalars[-1]] = None
            return out
        if isinstance(v, list):
            return [rec(x) for x in v]
        return v

    return rec(copy.deepcopy(result))


def schema_drift(tool: str, args: dict[str, Any], result: Any) -> Any:
    """Rename every top-level key with a ``_v2`` suffix (schema-version mismatch)."""

    if isinstance(result, dict):
        return {f"{k}_v2": v for k, v in result.items()}
    if isinstance(result, list):
        return [schema_drift(tool, args, x) for x in result]
    return result


def whitespace_and_case(tool: str, args: dict[str, Any], result: Any) -> Any:
    """Irrelevant formatting change: pad strings that are not identifiers."""

    def rec(v: Any) -> Any:
        if isinstance(v, str) and " " in v:
            return f"  {v}  "
        if isinstance(v, dict):
            return {k: rec(x) for k, x in v.items()}
        if isinstance(v, list):
            return [rec(x) for x in v]
        return v

    return rec(copy.deepcopy(result))


DEFAULT_PERTURBATIONS: tuple[Perturbation, ...] = (
    Perturbation("reorder_lists", "reordering", "invariant", reorder_lists),
    Perturbation("duplicate_record", "duplicates", "invariant", duplicate_first_record),
    Perturbation("pad_lists", "large_collections", "either", pad_lists),
    Perturbation("empty_lists", "empty_collections", "abstain", empty_lists),
    Perturbation("null_fields", "nulls", "abstain", null_optional_fields),
    Perturbation("schema_drift", "schema_drift", "abstain", schema_drift),
    Perturbation("formatting", "irrelevant_formatting", "invariant", whitespace_and_case),
    Perturbation("tool_4xx", "tool_error", "abstain", fail_tools=("*",), fail_status="error"),
    Perturbation("tool_timeout", "timeout", "abstain", fail_tools=("*",), fail_status="timeout"),
)


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------


class _Injected(Exception):
    pass


def _make_facade(
    program: Program,
    catalog: EffectCatalog,
    window: Window,
    pert: Perturbation | None,
    sandbox: Callable[[], Any] | None,
) -> tuple[ToolFacade, Any]:
    world = sandbox() if sandbox is not None else None
    recording = None if world is not None else Recording.from_episode(window.episode)
    failing = set(pert.fail_tools) if pert else set()

    def executor(tool: str, args: dict[str, Any]) -> Any:
        if failing and ("*" in failing or tool in failing):
            raise _Injected(f"injected {pert.fail_status} on {tool}")
        if world is not None:
            result = world.execute(tool, args)
        else:
            result = recording.get(tool, args)
        if pert is not None and pert.transform is not None:
            result = pert.transform(tool, args, result)
        return result

    facade = ToolFacade(
        catalog=catalog,
        mode=FacadeMode.SANDBOX if world is not None else FacadeMode.LIVE,
        executor=executor,
        allowed_tools=tuple(program.tools),
        max_calls=32,
    )
    return facade, world


def _semantic_signature(result: InterpResult, program: Program, catalog: EffectCatalog) -> Any:
    """The program's *decisions*, which a perturbation must not change.

    The invariant is on the arguments the program derived, not on the observations
    it echoed back. Reversing a response list legitimately changes a live-out that
    passes through it; what must not change is which record the program selected.
    Comparing derived arguments is what makes ``last |> project(id)`` and
    ``filter(status == "active") |> project(id)`` distinguishable — they agree on
    every training trace and disagree the moment records are reordered.

    Values that originate in a non-``cacheable`` response (a freshly minted session
    handle) are replaced by a placeholder, so a new token is not mistaken for a
    changed decision.
    """

    from ..schema.effects import Capability

    volatile: set[Any] = set()
    tool_by_var = {s.var: s.tool for s in program.steps if isinstance(s, (CallStep, LoopStep))}
    for var, value in result.env.items():
        tool = tool_by_var.get(var)
        if tool is None:
            continue
        if Capability.CACHEABLE in catalog.get(tool).capabilities:
            continue
        for v in _scalars(value):
            volatile.add(v)

    sig = []
    for tool, args in result.calls:
        norm = {
            k: ("<handle>" if (not isinstance(v, (dict, list)) and v in volatile) else v)
            for k, v in sorted(args.items())
        }
        sig.append((tool, tuple(sorted(norm.items(), key=lambda kv: kv[0]))))
    return tuple(sig)


def _scalars(value: Any, depth: int = 0) -> Iterable[Any]:
    if depth > 4:
        return
    if isinstance(value, dict):
        for v in value.values():
            yield from _scalars(v, depth + 1)
    elif isinstance(value, list):
        for v in value[:32]:
            yield from _scalars(v, depth + 1)
    elif isinstance(value, (str, int, float)) and not isinstance(value, bool):
        yield value


def run_perturbations(
    program: Program,
    guard: HardGuard,
    verifier: Verifier,
    windows: Sequence[Window],
    names: Sequence[str],
    catalog: EffectCatalog,
    sandbox: Callable[[], Any] | None,
    perturbations: Sequence[Perturbation],
    *,
    max_windows: int = 24,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Run the suite. Returns ``(per-family report, hard rejects)``."""

    report: dict[str, dict[str, Any]] = {}
    hard: list[dict[str, Any]] = []
    sample = list(windows)[:max_windows]

    # baseline (unperturbed) outputs per window, used as the invariance oracle
    baseline: dict[str, Any] = {}
    for w in sample:
        facade, world = _make_facade(program, catalog, w, None, sandbox)
        before = world.state_digest() if world is not None else None
        res = run_program(program, w.episode.entry_state, facade)
        if world is not None and world.state_digest() != before:
            hard.append(
                {
                    "perturbation": "baseline",
                    "family": "state",
                    "episode": w.episode.episode_id,
                    "kind": "sandbox_state_delta",
                }
            )
            baseline[w.episode.episode_id] = None
            continue
        baseline[w.episode.episode_id] = _semantic_signature(res, program, catalog) if res.ok else None

    for pert in perturbations:
        counts = Counter()
        for w in sample:
            facade, world = _make_facade(program, catalog, w, pert, sandbox)
            before = world.state_digest() if world is not None else None
            entry = w.episode.entry_state
            if pert.mutate_entry is not None:
                entry = pert.mutate_entry(copy.deepcopy(entry))
            try:
                res = run_program(program, entry, facade)
            except _Injected:
                if world is not None and world.state_digest() != before:
                    counts["state_delta"] += 1
                    hard.append(
                        {
                            "perturbation": pert.name,
                            "family": pert.family,
                            "episode": w.episode.episode_id,
                            "kind": "sandbox_state_delta_on_abstain",
                        }
                    )
                    continue
                counts["abstained"] += 1
                continue
            if world is not None and world.state_digest() != before:
                counts["state_delta"] += 1
                hard.append(
                    {
                        "perturbation": pert.name,
                        "family": pert.family,
                        "episode": w.episode.episode_id,
                        "kind": "sandbox_state_delta",
                    }
                )
                continue
            if not res.ok:
                counts["abstained"] += 1
                continue
            bad = verifier.verify(res.outputs, res.env, res.provenance, res.effects, len(res.calls))
            if bad:
                counts["verifier_abstained"] += 1
                continue
            ref = baseline.get(w.episode.episode_id)
            got = _semantic_signature(res, program, catalog)
            if pert.expect == "invariant":
                if ref is None:
                    counts["no_reference"] += 1
                elif got == ref:
                    counts["passed"] += 1
                else:
                    counts["wrong"] += 1
                    hard.append(
                        {
                            "perturbation": pert.name,
                            "family": pert.family,
                            "episode": w.episode.episode_id,
                            "kind": "invariance_violated",
                        }
                    )
            elif pert.expect == "abstain":
                # producing an answer is only a hard reject when the answer differs
                # from the unperturbed one; matching it is harmless
                if ref is not None and got != ref:
                    counts["wrong"] += 1
                    hard.append(
                        {
                            "perturbation": pert.name,
                            "family": pert.family,
                            "episode": w.episode.episode_id,
                            "kind": "answered_where_abstention_required",
                        }
                    )
                else:
                    counts["passed"] += 1
            else:
                counts["passed"] += 1
        total = sum(counts.values())
        report[pert.name] = {
            "family": pert.family,
            "expect": pert.expect,
            "n": total,
            "mode": "sandbox" if sandbox is not None else "recorded",
            **{k: v for k, v in counts.items()},
            "abstention_rate": round((counts["abstained"] + counts["verifier_abstained"]) / total, 3) if total else 0.0,
        }
    return report, hard
