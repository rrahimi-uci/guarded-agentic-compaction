"""Region-program IR: what a GRC artifact actually executes.

A program is a straight-line sequence of permitted tool calls whose arguments are
:mod:`~agent_compaction.grc.dsl` bindings over the entry state and earlier
in-region observations, optionally guarded by a synthesized typed predicate
(Algorithm 4), optionally wrapped in a bounded ``ForEach``.

The IR is intentionally not Turing complete: no user-defined functions, no
unbounded loops, no arithmetic on control flow. ``registry.explain()`` prints it
back as the pseudocode shown in proposal §5.7 and use-cases §1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from ..paths import resolve_path
from .composite import CompositeSpec
from .dsl import Binding, Const, Expr, LIBRARY_VERSION, binding_from_dict

__all__ = [
    "Predicate",
    "CallStep",
    "LoopStep",
    "AssertStep",
    "CompositeSpec",
    "Program",
    "Step",
    "predicate_from_dict",
    "program_from_dict",
]

_OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: _num(a) < _num(b),
    ">": lambda a, b: _num(a) > _num(b),
    "<=": lambda a, b: _num(a) <= _num(b),
    ">=": lambda a, b: _num(a) >= _num(b),
    "in": lambda a, b: a in b if isinstance(b, (list, tuple, set, str)) else False,
    "prefix": lambda a, b: isinstance(a, str) and isinstance(b, str) and a.startswith(b),
    "empty": lambda a, b: (a is None) or (hasattr(a, "__len__") and len(a) == 0),
    "present": lambda a, b: a is not None,
    "len==": lambda a, b: hasattr(a, "__len__") and len(a) == b,
    "len>": lambda a, b: hasattr(a, "__len__") and len(a) > b,
    "len<": lambda a, b: hasattr(a, "__len__") and len(a) < b,
}


def _num(v: Any) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise TypeError(f"not numeric: {v!r}")
    return float(v)


@dataclass(frozen=True, slots=True)
class Predicate:
    """A typed atom over an observable path (Algorithm 4 line 4)."""

    path: str
    op: str
    const: Any = None

    def evaluate(self, env: Any) -> bool:
        fn = _OPS.get(self.op)
        if fn is None:
            raise ValueError(f"unknown predicate op {self.op}")
        value = resolve_path(env, self.path)
        try:
            return bool(fn(value, self.const))
        except (TypeError, ValueError):
            return False

    def pretty(self) -> str:
        if self.op in ("empty", "present"):
            return f"{self.op}({self.path})"
        return f"{self.path} {self.op} {self.const!r}"

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "op": self.op, "const": self.const}


def predicate_from_dict(d: dict[str, Any]) -> Predicate:
    return Predicate(d["path"], d["op"], d.get("const"))


@dataclass(slots=True)
class CallStep:
    """One permitted tool call, arguments bound by the DSL."""

    var: str
    tool: str
    args: dict[str, Binding] = field(default_factory=dict)
    when: Predicate | None = None
    schema_version: str | None = None

    kind: str = "call"

    def pretty(self, indent: str = "   ") -> str:
        arglist = ", ".join(f"{k} = {v.pretty()}" for k, v in sorted(self.args.items()))
        line = f"{indent}{self.var:<5}= call {self.tool}({arglist})"
        if self.when is not None:
            return f"{indent}if {self.when.pretty()}:\n{indent}   {line.strip()}"
        return line

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "call",
            "var": self.var,
            "tool": self.tool,
            "args": {k: v.to_dict() for k, v in self.args.items()},
            "when": self.when.to_dict() if self.when else None,
            "schema_version": self.schema_version,
        }


@dataclass(slots=True)
class LoopStep:
    """Bounded ``ForEach``: repeat a call while a synthesized predicate holds."""

    var: str
    tool: str
    args: dict[str, Binding] = field(default_factory=dict)
    accumulate: str = "items"
    counter: str | None = None
    continue_when: Predicate | None = None
    max_iters: int = 32

    kind: str = "loop"

    def index_name(self) -> str:
        """Display name for the iteration index.

        The counter is an *argument slot*, so it can collide with the loop's own
        result variable — ``shipments.list_page`` yields the variable ``page`` and
        the counter slot ``page``. Disambiguate rather than print two different
        things under one name in a program a human is expected to approve.
        """

        if not self.counter:
            return ""
        return self.counter if self.counter != self.var else f"{self.counter}_i"

    def pretty(self, indent: str = "   ") -> str:
        index = self.index_name()
        # The interpreter overwrites the counter slot with the iteration index on
        # every pass, so printing its synthesized binding (typically the constant
        # from the first observed call) would describe a program that does not run.
        arglist = ", ".join(
            f"{k} = {index if index and k == self.counter else v.pretty()}"
            for k, v in sorted(self.args.items())
        )
        cond = self.continue_when.pretty() if self.continue_when else "false"
        init = f"{index} = 0; {self.accumulate} = []" if index else f"{self.accumulate} = []"
        increment = f"\n{indent}     {index} = {index} + 1" if index else ""
        return (
            f"{indent}{init}\n"
            f"{indent}ForEach (max {self.max_iters}):\n"
            f"{indent}     {self.var} = call {self.tool}({arglist})\n"
            f"{indent}     {self.accumulate} ++= {self.var}.{self.accumulate}\n"
            f"{indent}     if not ({cond}): break"
            f"{increment}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "loop",
            "var": self.var,
            "tool": self.tool,
            "args": {k: v.to_dict() for k, v in self.args.items()},
            "accumulate": self.accumulate,
            "counter": self.counter,
            "continue_when": self.continue_when.to_dict() if self.continue_when else None,
            "max_iters": self.max_iters,
        }


@dataclass(slots=True)
class AssertStep:
    """In-program assertions. A failure is an abstention, never a wrong answer."""

    checks: tuple[Predicate, ...] = ()

    kind: str = "assert"

    def pretty(self, indent: str = "   ") -> str:
        return f"{indent}assert  " + " and ".join(c.pretty() for c in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "assert", "checks": [c.to_dict() for c in self.checks]}


Step = CallStep | LoopStep | AssertStep


def step_from_dict(d: dict[str, Any]) -> Step:
    kind = d["kind"]
    if kind == "call":
        return CallStep(
            var=d["var"],
            tool=d["tool"],
            args={k: binding_from_dict(v) for k, v in d["args"].items()},
            when=predicate_from_dict(d["when"]) if d.get("when") else None,
            schema_version=d.get("schema_version"),
        )
    if kind == "loop":
        return LoopStep(
            var=d["var"],
            tool=d["tool"],
            args={k: binding_from_dict(v) for k, v in d["args"].items()},
            accumulate=d.get("accumulate", "items"),
            counter=d.get("counter"),
            continue_when=predicate_from_dict(d["continue_when"]) if d.get("continue_when") else None,
            max_iters=d.get("max_iters", 32),
        )
    if kind == "assert":
        return AssertStep(tuple(predicate_from_dict(c) for c in d["checks"]))
    raise ValueError(f"unknown step kind {kind}")


@dataclass(slots=True)
class Program:
    """A compiled region program."""

    theta: tuple[str, ...] = ()
    steps: list[Step] = field(default_factory=list)
    outputs: dict[str, Binding] = field(default_factory=dict)
    library_version: str = LIBRARY_VERSION
    removed_requests: float = 0.0
    tools: tuple[str, ...] = ()
    composite: CompositeSpec | None = None

    def __post_init__(self) -> None:
        if not self.tools:
            self.tools = tuple(
                dict.fromkeys(s.tool for s in self.steps if isinstance(s, (CallStep, LoopStep)))
            )

    @property
    def size(self) -> int:
        """MDL node count, used in the ranking score of Eq. (16)."""

        n = 0
        for s in self.steps:
            if isinstance(s, (CallStep, LoopStep)):
                n += 1 + sum(b.mdl for b in s.args.values())
                if isinstance(s, CallStep) and s.when is not None:
                    n += 2
                if isinstance(s, LoopStep) and s.continue_when is not None:
                    n += 2
            elif isinstance(s, AssertStep):
                n += len(s.checks)
        if self.composite is not None:
            n += 1 + sum(binding.mdl for binding in self.composite.projection.values())
        return n + len(self.outputs)

    @property
    def branch_count(self) -> int:
        return sum(
            1
            for s in self.steps
            if (isinstance(s, CallStep) and s.when is not None)
            or (isinstance(s, LoopStep) and s.continue_when is not None)
        )

    def call_steps(self) -> list[CallStep | LoopStep]:
        return [s for s in self.steps if isinstance(s, (CallStep, LoopStep))]

    def pretty(self) -> str:
        theta = ", ".join(self.theta)
        lines = [f"program (θ = {{{theta}}}):"]
        for s in self.steps:
            lines.append(s.pretty())
        rets = ", ".join(f"{k}: {v.pretty()}" for k, v in sorted(self.outputs.items()))
        lines.append(f"   return  {{ {rets} }}")
        if self.composite is not None:
            exposed = ", ".join(sorted(self.composite.projection))
            lines.append(
                f"expose   {self.composite.name}({', '.join(self.composite.inputs)})"
                f" -> {{ {exposed} }} [internal={len(self.composite.internal_tools)}]"
            )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "theta": list(self.theta),
            "steps": [s.to_dict() for s in self.steps],
            "outputs": {k: v.to_dict() for k, v in self.outputs.items()},
            "library_version": self.library_version,
            "removed_requests": self.removed_requests,
            "tools": list(self.tools),
            "composite": self.composite.to_dict() if self.composite else None,
        }


def program_from_dict(d: dict[str, Any]) -> Program:
    return Program(
        theta=tuple(d.get("theta", ())),
        steps=[step_from_dict(s) for s in d.get("steps", [])],
        outputs={k: binding_from_dict(v) for k, v in d.get("outputs", {}).items()},
        library_version=d.get("library_version", LIBRARY_VERSION),
        removed_requests=d.get("removed_requests", 0),
        tools=tuple(d.get("tools", ())),
        composite=CompositeSpec.from_dict(d["composite"]) if d.get("composite") else None,
    )
