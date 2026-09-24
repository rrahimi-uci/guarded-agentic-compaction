"""Read-only prologue admission: replay suppression under an extended entry contract.

The position invariant (Eq. 2) is enforced at runtime as "no tool observation has
been committed in this episode". ``paper/supplementary/read-only-prologue-protocol.md``
fixes the one relaxation the paper conjectures: an allowlisted, deterministic,
read-only *prologue* may precede the compiled prefix when the host's committed
observations are **exactly** the prologue's calls. This module is that check.

It is deliberately a pure function of four inputs -- the artifact's program, its
declared prologue, the signed effect catalog and the ordered committed calls -- so
that :class:`~guarded_agentic_compaction.runtime.dispatch.Dispatcher` and
:class:`~guarded_agentic_compaction.runtime.manual.ManualPreModelRunner` apply one
rule and one reason vocabulary. Every rejection returns a specific reason and the
caller falls back to the unchanged baseline agent; nothing here executes a tool.

Three properties the protocol's acceptance tests require are structural here:

1. *No replay.* An admitted prologue's results are handed back as explicit live-ins
   of the region (``PrologueMatch.live_ins``). The region's own call count and effect
   multiset are untouched, because the prologue never reaches the facade.
2. *Exactness.* Same tools, same order, same arguments, nothing extra, nothing
   missing, every committed call successful. An artifact without a prologue never
   enters this module and keeps the strict position-0 rule byte for byte.
3. *Grounding.* With the prologue outputs added to the live-in set, every argument
   slot, predicate and live-out of the region must still resolve to exactly one
   declared source: the entry state, a prologue live-in or an earlier region step.
   A slot that would be ungrounded, or a live-in name with two possible producers,
   retires the region at this boundary (``prologue_ungrounded_slot`` /
   ``prologue_ambiguous_live_in``). This is the runtime-side closure of protocol
   acceptance test 3; it does not re-run the compile-time PATG over supporting
   groups.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from ..grc.dsl import Const, Expr, TypeMismatch
from ..grc.program import AssertStep, CallStep, LoopStep, Predicate, Program
from ..schema.artifacts import HardGuard, Prologue
from ..schema.effects import Capability, EffectCatalog, EffectClass

__all__ = [
    "CommittedCall",
    "PrologueMatch",
    "prologue_structural_reasons",
    "prologue_catalog_reasons",
    "prologue_grounding_reasons",
    "match_prologue",
]


@dataclass(frozen=True, slots=True)
class CommittedCall:
    """One tool observation the host has already committed to the episode.

    Order matters: hosts pass the full committed sequence, duplicates included.
    ``status`` other than ``"ok"`` never satisfies a prologue call.
    """

    tool: str
    args: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    status: str = "ok"


@dataclass(slots=True)
class PrologueMatch:
    """Outcome of :func:`match_prologue`. ``ok`` iff ``reasons`` is empty."""

    reasons: tuple[str, ...] = ()
    #: prologue var -> committed result, in prologue order; empty unless ``ok``
    live_ins: dict[str, Any] = field(default_factory=dict)
    #: prologue var -> tool that produced it; feeds the interpreter's provenance
    provenance: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.reasons


# ---------------------------------------------------------------------------
# structural validity of the declaration
# ---------------------------------------------------------------------------


def _root(path: str) -> str:
    """``z.issue_number`` -> ``z``; ``docs[0].name`` -> ``docs``."""

    head = path.split(".", 1)[0]
    return head.split("[", 1)[0]


def prologue_structural_reasons(program: Program, prologue: Prologue) -> list[str]:
    """Reject malformed declarations before anything is compared or executed."""

    reasons: list[str] = []
    if prologue.schema_version != 1:
        reasons.append("invalid_prologue:schema_version")
    if not prologue.calls:
        reasons.append("invalid_prologue:empty")
    seen: set[str] = set()
    step_vars = {step.var for step in program.call_steps()}
    for index, call in enumerate(prologue.calls):
        if not call.var or not call.var.replace("_", "").isalnum() or call.var == "z":
            reasons.append(f"invalid_prologue:var@{index}")
        elif call.var in seen or call.var.endswith("__all"):
            # two producers for one name: the region could not tell them apart
            reasons.append(f"prologue_ambiguous_live_in:{call.var}")
        seen.add(call.var)
        if not call.tool:
            reasons.append(f"invalid_prologue:tool@{index}")
        if call.tool in program.tools:
            # A region tool that is also a prologue tool would be issued twice in
            # the episode, once by the host and once by the facade. The protocol
            # forbids replaying a committed call, so the sets must be disjoint.
            reasons.append(f"invalid_prologue:tool_in_region:{call.tool}")
        for path, binding in call.args.items():
            if isinstance(binding, Const):
                continue
            if isinstance(binding, Expr) and _root(binding.source) == "z":
                continue
            # bindings over earlier observations would make the prologue itself
            # depend on trace position, which is exactly what the contract excludes
            reasons.append(f"invalid_prologue:binding:{call.var}.{path}")
    if seen & step_vars:
        for var in sorted(seen & step_vars):
            reasons.append(f"prologue_ambiguous_live_in:{var}")
    if seen & set(program.outputs):
        for var in sorted(seen & set(program.outputs)):
            reasons.append(f"prologue_ambiguous_live_in:{var}")
    return list(dict.fromkeys(reasons))


# ---------------------------------------------------------------------------
# effect admissibility against the signed catalog
# ---------------------------------------------------------------------------


def prologue_catalog_reasons(
    prologue: Prologue,
    catalog: EffectCatalog,
    guard: HardGuard | None = None,
) -> list[str]:
    """Every prologue tool must be declared read-like, speculatable and replayable."""

    reasons: list[str] = []
    for call in prologue.calls:
        if call.tool not in catalog.tools:
            reasons.append(f"prologue_undeclared_tool:{call.tool}")
            continue
        spec = catalog.get(call.tool)
        if spec.effect is EffectClass.UNKNOWN:
            reasons.append(f"prologue_unknown_effect:{call.tool}")
            continue
        if not spec.effect.is_read_like or spec.approval_required:
            reasons.append(f"prologue_effect:{call.tool}:{spec.effect.value}")
            continue
        missing = [
            cap.value
            for cap in (Capability.SPECULATABLE, Capability.REPLAYABLE)
            if cap not in spec.capabilities
        ]
        if missing:
            reasons.append(f"prologue_capability:{call.tool}:" + "+".join(missing))
            continue
        if guard is not None and guard.allowed_effects and spec.effect.value not in guard.allowed_effects:
            reasons.append(f"prologue_guard_effect:{call.tool}")
    return list(dict.fromkeys(reasons))


# ---------------------------------------------------------------------------
# provenance closure with the prologue outputs as explicit live-ins
# ---------------------------------------------------------------------------


def _predicate_paths(predicate: Predicate | None) -> Iterable[str]:
    if predicate is not None:
        yield predicate.path


def prologue_grounding_reasons(program: Program, prologue: Prologue) -> list[str]:
    """Recompute slot grounding over ``{z} ∪ prologue vars ∪ earlier region vars``.

    Mirrors the compile-time marks of Algorithm 1 at the granularity the runtime
    can check without traces: a reference whose root is not a declared live-in is
    *ungrounded*; a live-in name with more than one producer is *ambiguous* (and is
    reported by :func:`prologue_structural_reasons`). Either retires the region.
    """

    reasons: list[str] = []
    available: set[str] = {"z", *prologue.vars}

    def check(root_path: str, where: str) -> None:
        root = _root(root_path)
        if root not in available:
            reasons.append(f"prologue_ungrounded_slot:{where}")

    for step in program.steps:
        if isinstance(step, AssertStep):
            for check_pred in step.checks:
                for path in _predicate_paths(check_pred):
                    check(path, f"assert.{path}")
            continue
        if isinstance(step, (CallStep, LoopStep)):
            predicate = step.when if isinstance(step, CallStep) else step.continue_when
            for path, binding in step.args.items():
                if isinstance(binding, Expr):
                    check(binding.source, f"{step.var}.{path}")
            if isinstance(step, CallStep):
                for path in _predicate_paths(predicate):
                    check(path, f"{step.var}.when.{path}")
            # the loop predicate is evaluated after the first call, so it may see
            # the step's own variable; register it before checking
            available.add(step.var)
            if isinstance(step, LoopStep):
                available.add(f"{step.var}__all")
                for path in _predicate_paths(predicate):
                    check(path, f"{step.var}.continue_when.{path}")
    for name, binding in program.outputs.items():
        if isinstance(binding, Expr):
            check(binding.source, f"return.{name}")
    return list(dict.fromkeys(reasons))


# ---------------------------------------------------------------------------
# the match itself
# ---------------------------------------------------------------------------


def match_prologue(
    program: Program,
    prologue: Prologue,
    catalog: EffectCatalog,
    entry_state: dict[str, Any],
    committed: Sequence[CommittedCall] | None,
    *,
    guard: HardGuard | None = None,
    already_observed: Sequence[str] = (),
) -> PrologueMatch:
    """Decide whether the committed observations are exactly the declared prologue.

    Order of checks is fixed so that the first reason is the most specific one:
    declaration validity, catalog admissibility, grounding, then the committed
    sequence (presence, length, tool, order, arguments, status). ``committed`` is
    ``None`` when the host cannot supply the ordered record; the boundary is then
    unverifiable and falls back.
    """

    reasons = prologue_structural_reasons(program, prologue)
    if reasons:
        return PrologueMatch(reasons=tuple(reasons))
    reasons = prologue_catalog_reasons(prologue, catalog, guard)
    if reasons:
        return PrologueMatch(reasons=tuple(reasons))
    reasons = prologue_grounding_reasons(program, prologue)
    if reasons:
        return PrologueMatch(reasons=tuple(reasons))

    if committed is None:
        return PrologueMatch(reasons=("prologue_unverifiable:no_committed_record",))
    committed = list(committed)

    # a host that reports an observed tool absent from the committed record is
    # describing a different episode than the one we are asked to verify
    committed_tools = {call.tool for call in committed}
    unrecorded = [tool for tool in already_observed if tool not in committed_tools]
    if unrecorded:
        return PrologueMatch(reasons=(f"prologue_mismatch:unrecorded_observation:{unrecorded[0]}",))

    expected_tools = list(prologue.tools)
    if len(committed) < len(expected_tools):
        return PrologueMatch(reasons=(f"prologue_mismatch:missing_call@{len(committed)}",))
    if len(committed) > len(expected_tools):
        return PrologueMatch(reasons=(f"prologue_mismatch:extra_call@{len(expected_tools)}",))
    actual_tools = [call.tool for call in committed]
    if actual_tools != expected_tools:
        if sorted(actual_tools) == sorted(expected_tools):
            return PrologueMatch(reasons=("prologue_mismatch:order",))
        for index, (want, got) in enumerate(zip(expected_tools, actual_tools)):
            if want != got:
                return PrologueMatch(reasons=(f"prologue_mismatch:tool@{index}:{got}",))

    env = {"z": entry_state}
    live_ins: dict[str, Any] = {}
    provenance: dict[str, str] = {}
    for index, (call, observed) in enumerate(zip(prologue.calls, committed)):
        if observed.status != "ok":
            return PrologueMatch(reasons=(f"prologue_mismatch:status@{index}:{observed.status}",))
        expected_args: dict[str, Any] = {}
        for path, binding in call.args.items():
            try:
                value = binding.evaluate(env)
            except (TypeMismatch, TypeError, ValueError, KeyError):
                return PrologueMatch(reasons=(f"prologue_binding_failed@{index}:{path}",))
            _set_path(expected_args, path, value)
        if expected_args != dict(observed.args):
            # exact equality, not catalog equivalence: the region was fitted on
            # this argument, and the committed call is the only evidence we have
            return PrologueMatch(reasons=(f"prologue_mismatch:args@{index}",))
        live_ins[call.var] = observed.result
        provenance[call.var] = call.tool
    return PrologueMatch(live_ins=live_ins, provenance=provenance)


def _set_path(target: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    cur = target
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value
