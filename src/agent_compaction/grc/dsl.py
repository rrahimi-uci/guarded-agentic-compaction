"""The closed transform library ``T`` and expression IR (proposal §4.3).

This is the *entire* expressive power of the binder. It is closed, versioned,
and deliberately small: every operator added widens Algorithm 1's spurious-match
surface as well as Algorithm 3's coverage, so growth is a two-sided trade
(proposal §6.2 row 3).

Operator classes, exactly as enumerated in proposal §4.3:

======================  ====================================================
Identity / coercion     ``id`` ``str`` ``int`` ``float`` ``bool``
String                  ``lower`` ``upper`` ``strip`` ``split(sep)[i]``
                        ``join(sep)`` ``fmt(template)``
Numeric                 ``add(c)`` ``mul(c)`` ``round(k)`` ``sum`` ``len``
Collection              ``project(path)`` ``filter(path op const)`` ``first``
                        ``last`` ``sort(path)`` ``topk(path,n)``
Temporal                ``date_fmt(pattern)``
======================  ====================================================

That enumeration contains 23 operator forms; proposal §4.3 labels the table "22
operators". The implementation follows the enumerated list and records the
discrepancy in ``docs/spec-review.md`` rather than silently dropping one.

Search strategy. Rather than enumerating ``|T|^d`` expressions and testing each
(the naive reading of Algorithm 1's ``TransformSearch``), the implementation runs
a *value-directed* breadth-first search from the concrete source value and keeps
chains whose denotation equals the target. This is the same version space with
the same depth bound, it prunes by runtime type for free, and it collapses
observationally equivalent chains (proposal §4.8).
"""

from __future__ import annotations

import datetime as _dt
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Iterator, Sequence

from ..paths import content_digest, resolve_path

__all__ = [
    "LIBRARY_VERSION",
    "Op",
    "Expr",
    "Const",
    "Binding",
    "SynthContext",
    "search_chains",
    "apply_chain",
    "OPERATOR_CLASSES",
    "TypeMismatch",
]

LIBRARY_VERSION = "T-v1"

#: Operator names grouped by class, for reporting and for the docs table.
OPERATOR_CLASSES: dict[str, tuple[str, ...]] = {
    "identity_coercion": ("id", "str", "int", "float", "bool"),
    "string": ("lower", "upper", "strip", "split", "join", "fmt"),
    "numeric": ("add", "mul", "round", "sum", "len"),
    "collection": ("project", "filter", "first", "last", "sort", "topk"),
    "temporal": ("date_fmt",),
}

N_OPERATORS = sum(len(v) for v in OPERATOR_CLASSES.values())


class TypeMismatch(Exception):
    """Raised when an operator is applied to an incompatible value."""


# ---------------------------------------------------------------------------
# operators
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Op:
    """One library operator with its (constant) parameters."""

    name: str
    params: tuple[Any, ...] = ()

    def __str__(self) -> str:  # pragma: no cover - display only
        if not self.params:
            return self.name
        if self.name == "split":
            sep, idx = self.params
            return f"split({sep!r})[{idx}]"
        if self.name == "filter":
            path, op, const = self.params
            return f"filter({path} {op} {const!r})"
        return f"{self.name}({', '.join(repr(p) for p in self.params)})"

    @property
    def cost(self) -> int:
        """MDL cost: one unit for the operator plus one per parameter token."""

        return 1 + sum(1 + len(str(p)) // 8 for p in self.params)

    def apply(self, v: Any) -> Any:
        fn = _DISPATCH.get(self.name)
        if fn is None:  # pragma: no cover - defensive
            raise TypeMismatch(f"unknown operator {self.name}")
        return fn(v, *self.params)


def _need_str(v: Any) -> str:
    if not isinstance(v, str):
        raise TypeMismatch("expected str")
    return v


def _need_num(v: Any) -> float | int:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise TypeMismatch("expected number")
    return v


def _need_list(v: Any) -> list:
    if not isinstance(v, (list, tuple)):
        raise TypeMismatch("expected list")
    return list(v)


def _op_id(v: Any) -> Any:
    return v


def _op_str(v: Any) -> str:
    if isinstance(v, (dict, list, tuple)):
        raise TypeMismatch("str() of container")
    return str(v)


def _op_int(v: Any) -> int:
    try:
        if isinstance(v, bool):
            raise TypeMismatch("int() of bool")
        return int(v)
    except (TypeError, ValueError) as exc:
        raise TypeMismatch(str(exc)) from exc


def _op_float(v: Any) -> float:
    try:
        if isinstance(v, bool):
            raise TypeMismatch("float() of bool")
        return float(v)
    except (TypeError, ValueError) as exc:
        raise TypeMismatch(str(exc)) from exc


def _op_bool(v: Any) -> bool:
    if isinstance(v, (dict, list, tuple)):
        raise TypeMismatch("bool() of container")
    return bool(v)


def _op_lower(v: Any) -> str:
    return _need_str(v).lower()


def _op_upper(v: Any) -> str:
    return _need_str(v).upper()


def _op_strip(v: Any) -> str:
    return _need_str(v).strip()


def _op_split(v: Any, sep: str, idx: int) -> str:
    parts = _need_str(v).split(sep)
    if not parts:
        raise TypeMismatch("empty split")
    try:
        return parts[idx]
    except IndexError as exc:
        raise TypeMismatch("split index") from exc


def _op_join(v: Any, sep: str) -> str:
    items = _need_list(v)
    if not all(isinstance(x, str) for x in items):
        raise TypeMismatch("join of non-str")
    return sep.join(items)


def _op_fmt(v: Any, template: str) -> str:
    if isinstance(v, (dict, list, tuple)):
        raise TypeMismatch("fmt of container")
    if template.count("{}") != 1:
        raise TypeMismatch("template must hold exactly one slot")
    return template.replace("{}", str(v))


def _op_add(v: Any, c: float) -> float | int:
    x = _need_num(v)
    out = x + c
    return int(out) if isinstance(x, int) and float(c).is_integer() else out


def _op_mul(v: Any, c: float) -> float | int:
    x = _need_num(v)
    out = x * c
    return int(out) if isinstance(x, int) and float(c).is_integer() else out


def _op_round(v: Any, k: int) -> float | int:
    x = _need_num(v)
    return round(x, k) if k else int(round(x))


def _op_sum(v: Any) -> float | int:
    items = _need_list(v)
    if not items:
        return 0
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in items):
        raise TypeMismatch("sum of non-numbers")
    total = sum(items)
    return int(total) if all(isinstance(x, int) for x in items) else total


def _op_len(v: Any) -> int:
    if isinstance(v, (list, tuple, str, dict)):
        return len(v)
    raise TypeMismatch("len of scalar")


def _op_project(v: Any, path: str) -> Any:
    if isinstance(v, dict):
        out = resolve_path(v, path)
        if out is None:
            raise TypeMismatch("project miss")
        return out
    items = _need_list(v)
    vals = []
    for item in items:
        got = resolve_path(item, path) if isinstance(item, (dict, list)) else None
        if got is None:
            raise TypeMismatch("project miss in list")
        vals.append(got)
    if len(vals) == 1:
        return vals[0]
    return vals


_CMP: dict[str, Callable[[Any, Any], bool]] = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: _cmp_num(a, b, lambda x, y: x < y),
    ">": lambda a, b: _cmp_num(a, b, lambda x, y: x > y),
    "<=": lambda a, b: _cmp_num(a, b, lambda x, y: x <= y),
    ">=": lambda a, b: _cmp_num(a, b, lambda x, y: x >= y),
    "in": lambda a, b: isinstance(b, (list, tuple, str)) and a in b,
}


def _cmp_num(a: Any, b: Any, fn: Callable[[Any, Any], bool]) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return fn(a, b)
    if isinstance(a, str) and isinstance(b, str):
        return fn(a, b)
    return False


def _op_filter(v: Any, path: str, op: str, const: Any) -> list:
    items = _need_list(v)
    cmp = _CMP.get(op)
    if cmp is None:
        raise TypeMismatch("bad comparator")
    out = []
    for item in items:
        got = resolve_path(item, path) if isinstance(item, (dict, list)) else item
        if cmp(got, const):
            out.append(item)
    return out


def _op_first(v: Any) -> Any:
    items = _need_list(v)
    if not items:
        raise TypeMismatch("first of empty")
    return items[0]


def _op_last(v: Any) -> Any:
    items = _need_list(v)
    if not items:
        raise TypeMismatch("last of empty")
    return items[-1]


def _sort_key(path: str) -> Callable[[Any], tuple[int, Any]]:
    def key(item: Any) -> tuple[int, Any]:
        got = resolve_path(item, path) if isinstance(item, (dict, list)) else item
        if got is None:
            return (1, "")
        return (0, got)

    return key


def _op_sort(v: Any, path: str) -> list:
    items = _need_list(v)
    try:
        return sorted(items, key=_sort_key(path))
    except TypeError as exc:
        raise TypeMismatch("unsortable") from exc


def _op_topk(v: Any, path: str, n: int) -> list:
    return _op_sort(v, path)[-n:][::-1] if n > 0 else []


def _op_date_fmt(v: Any, pattern: str) -> str:
    s = _need_str(v)
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return _dt.datetime.strptime(s[: len(fmt) + 8].rstrip("Z"), fmt).strftime(pattern)
        except ValueError:
            continue
    raise TypeMismatch("unparseable date")


_DISPATCH: dict[str, Callable[..., Any]] = {
    "id": _op_id,
    "str": _op_str,
    "int": _op_int,
    "float": _op_float,
    "bool": _op_bool,
    "lower": _op_lower,
    "upper": _op_upper,
    "strip": _op_strip,
    "split": _op_split,
    "join": _op_join,
    "fmt": _op_fmt,
    "add": _op_add,
    "mul": _op_mul,
    "round": _op_round,
    "sum": _op_sum,
    "len": _op_len,
    "project": _op_project,
    "filter": _op_filter,
    "first": _op_first,
    "last": _op_last,
    "sort": _op_sort,
    "topk": _op_topk,
    "date_fmt": _op_date_fmt,
}

assert set(_DISPATCH) == {name for names in OPERATOR_CLASSES.values() for name in names}


# ---------------------------------------------------------------------------
# expressions
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Const:
    """A literal, admissible only when invariant across all supporting traces."""

    value: Any

    def evaluate(self, env: Any = None) -> Any:
        return self.value

    @property
    def mdl(self) -> int:
        return 1 + len(str(self.value)) // 8

    @property
    def depth(self) -> int:
        return 0

    def pretty(self) -> str:
        return f"Const({self.value!r})"

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "const", "value": self.value}


@dataclass(frozen=True, slots=True)
class Expr:
    """``f ∘ σ``: a source path plus a bounded chain of library operators."""

    source: str
    ops: tuple[Op, ...] = ()

    def evaluate(self, env: Any) -> Any:
        v = resolve_path(env, self.source)
        if v is None and self.source not in ("", None):
            raise TypeMismatch(f"source path missing: {self.source}")
        return apply_chain(v, self.ops)

    @property
    def mdl(self) -> int:
        return 1 + len(self.source.split(".")) + sum(op.cost for op in self.ops)

    @property
    def depth(self) -> int:
        return len(self.ops)

    def pretty(self) -> str:
        if not self.ops:
            return self.source
        return self.source + " |> " + " |> ".join(str(op) for op in self.ops)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "expr",
            "source": self.source,
            "ops": [{"name": o.name, "params": list(o.params)} for o in self.ops],
        }


Binding = Expr | Const


def binding_from_dict(d: dict[str, Any]) -> Binding:
    if d["kind"] == "const":
        return Const(d["value"])
    return Expr(d["source"], tuple(Op(o["name"], tuple(o["params"])) for o in d["ops"]))


def apply_chain(value: Any, ops: Sequence[Op]) -> Any:
    v = value
    for op in ops:
        v = op.apply(v)
    return v


# ---------------------------------------------------------------------------
# synthesis context and value-directed search
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SynthContext:
    """Parameter pools for operator instantiation.

    Constants come only from literals observed in the supporting traces plus
    ``{0, 1, -1, ""}`` (proposal §4.3).
    """

    numeric_consts: tuple[float, ...] = (0.0, 1.0, -1.0)
    string_consts: tuple[str, ...] = ("",)
    field_paths: tuple[str, ...] = ()
    separators: tuple[str, ...] = ("@", ".", "-", "_", "/", " ", ",", ":")
    split_indices: tuple[int, ...] = (0, 1, -1)
    date_patterns: tuple[str, ...] = ("%Y-%m-%d", "%Y-%m", "%Y", "%d/%m/%Y")
    max_depth: int = 2
    max_nodes: int = 20000
    max_frontier: int = 96
    max_cache_entries: int = 20000
    cache_hits: int = field(default=0, init=False)
    cache_misses: int = field(default=0, init=False)
    _search_cache: dict[tuple[str, str, int], tuple[tuple[Op, ...], ...]] = field(
        default_factory=dict, init=False, repr=False
    )

    @classmethod
    def from_observations(
        cls,
        values: Iterable[Any],
        *,
        max_depth: int = 2,
    ) -> "SynthContext":
        nums: set[float] = {0.0, 1.0, -1.0}
        strs: set[str] = {""}
        fields: set[str] = set()

        def walk(v: Any, depth: int = 0) -> None:
            if depth > 4:
                return
            if isinstance(v, bool):
                return
            if isinstance(v, (int, float)):
                nums.add(float(v))
            elif isinstance(v, str):
                if len(v) <= 64:
                    strs.add(v)
            elif isinstance(v, dict):
                for k, sub in v.items():
                    if isinstance(k, str):
                        fields.add(k)
                        if isinstance(sub, dict):
                            for k2 in sub:
                                if isinstance(k2, str):
                                    fields.add(f"{k}.{k2}")
                    walk(sub, depth + 1)
            elif isinstance(v, (list, tuple)):
                for sub in v[:16]:
                    walk(sub, depth + 1)

        for value in values:
            walk(value)
        return cls(
            numeric_consts=tuple(sorted(nums)[:32]),
            string_consts=tuple(sorted(strs)[:64]),
            field_paths=tuple(sorted(fields)[:48]),
            max_depth=max_depth,
        )

    # -- operator instantiation ------------------------------------------
    def candidate_ops(self, value: Any, target: Any) -> list[Op]:
        """Operators worth applying to ``value`` given a ``target`` denotation.

        Runtime-type directed: this is the type check of Algorithm 3 line 6,
        performed against the concrete value rather than a declared signature.
        """

        ops: list[Op] = []
        if isinstance(value, str):
            ops += [Op("lower"), Op("upper"), Op("strip"), Op("len")]
            if isinstance(target, (int, float)) and not isinstance(target, bool):
                ops += [Op("int"), Op("float")]
            for sep in self.separators:
                if sep in value:
                    for idx in self.split_indices:
                        ops.append(Op("split", (sep, idx)))
            if isinstance(target, str) and value and value in target and value != target:
                ops.append(Op("fmt", (target.replace(value, "{}", 1),)))
            if any(ch.isdigit() for ch in value) and "-" in value or "/" in value:
                for pat in self.date_patterns:
                    ops.append(Op("date_fmt", (pat,)))
        elif isinstance(value, bool):
            ops += [Op("str")]
        elif isinstance(value, (int, float)):
            ops += [Op("str"), Op("int"), Op("float")]
            for c in self.numeric_consts:
                if c not in (0.0,):
                    ops.append(Op("add", (c,)))
                if c not in (0.0, 1.0):
                    ops.append(Op("mul", (c,)))
            ops += [Op("round", (0,)), Op("round", (2,))]
        elif isinstance(value, (list, tuple)):
            ops += [Op("len"), Op("first"), Op("last"), Op("sum")]
            # Collection operators are parameterised from the value *at hand*
            # rather than from a corpus-wide pool. Without this the enumeration
            # is |fields| x |consts| wide at every node and depth 2 explodes;
            # with it, the search stays in the hundreds of nodes and still covers
            # the dominant select-then-project pattern of proposal §4.3.
            fields = _item_fields(value)
            for path in fields:
                ops.append(Op("project", (path,)))
                ops.append(Op("sort", (path,)))
                ops.append(Op("topk", (path, 1)))
                for const in _item_values(value, path):
                    # A filter constant equal to the sought value encodes the answer
                    # rather than deriving it: `filter(id == "cus_B") |> project(id)`
                    # fits any single trace and generalizes to nothing. Skipping it
                    # keeps the ranked candidate list free of memorizing chains
                    # (which Algorithm 3's cross-trace check would reject anyway, but
                    # only after they have crowded out the correct one).
                    if _same_scalar(const, target):
                        continue
                    ops.append(Op("filter", (path, "==", const)))
                    if isinstance(const, (int, float)) and not isinstance(const, bool):
                        ops.append(Op("filter", (path, ">=", const)))
            if value and all(isinstance(x, str) for x in value):
                ops.append(Op("join", (",",)))
        elif isinstance(value, dict):
            for path in _dict_paths(value):
                ops.append(Op("project", (path,)))
            ops.append(Op("len"))
        return ops


def _same_scalar(a: Any, b: Any) -> bool:
    if isinstance(a, (dict, list)) or isinstance(b, (dict, list)):
        return False
    return a == b


def _item_fields(items: Sequence[Any], *, limit: int = 12) -> tuple[str, ...]:
    """Field paths present in *every* dict item of a list (depth ≤ 2)."""

    dicts = [x for x in items if isinstance(x, dict)]
    if not dicts:
        return ()
    common: set[str] | None = None
    for d in dicts[:16]:
        paths: set[str] = set()
        for k, v in d.items():
            if not isinstance(k, str):
                continue
            paths.add(k)
            if isinstance(v, dict):
                for k2 in v:
                    if isinstance(k2, str):
                        paths.add(f"{k}.{k2}")
        common = paths if common is None else (common & paths)
    return tuple(sorted(common or ())[:limit])


def _item_values(items: Sequence[Any], path: str, *, limit: int = 8) -> tuple[Any, ...]:
    seen: list[Any] = []
    for x in items[:24]:
        if not isinstance(x, (dict, list)):
            continue
        v = resolve_path(x, path)
        if v is None or isinstance(v, (dict, list)):
            continue
        if v not in seen:
            seen.append(v)
        if len(seen) >= limit:
            break
    return tuple(seen)


def _dict_paths(d: dict[str, Any], *, limit: int = 24) -> tuple[str, ...]:
    paths: list[str] = []
    for k, v in d.items():
        if not isinstance(k, str):
            continue
        paths.append(k)
        if isinstance(v, dict):
            for k2 in v:
                if isinstance(k2, str):
                    paths.append(f"{k}.{k2}")
    return tuple(paths[:limit])


#: How order-dependent an operator is. Positional selection (``first``/``last``)
#: and rank selection (``sort``/``topk``) are order-dependent: they agree with a
#: predicate-based selection on any single trace where the wanted record happens
#: to be first or last, and disagree the moment the provider reorders records.
#: When two chains have the same denotation on a trace, the more stable one is
#: kept — otherwise observational-equivalence pruning silently discards
#: ``filter(status == "active")`` in favour of ``last``.
OP_INSTABILITY: dict[str, int] = {
    "filter": 0,
    "project": 1,
    "len": 1,
    "sum": 1,
    "join": 1,
    "id": 1,
    "str": 1,
    "int": 1,
    "float": 1,
    "bool": 1,
    "lower": 1,
    "upper": 1,
    "strip": 1,
    "split": 1,
    "fmt": 1,
    "add": 1,
    "mul": 1,
    "round": 1,
    "date_fmt": 1,
    "sort": 2,
    "topk": 2,
    "first": 3,
    "last": 3,
}


def chain_rank(chain: Sequence[Op]) -> tuple[int, int, int, str]:
    """Ordering key: length, then order-stability, then MDL, then lexical."""

    instability = max((OP_INSTABILITY.get(o.name, 1) for o in chain), default=0)
    return (
        len(chain),
        instability,
        sum(o.cost for o in chain),
        "|".join(str(o) for o in chain),
    )


def search_chains(
    source_value: Any,
    target: Any,
    ctx: SynthContext,
    *,
    max_results: int = 8,
) -> list[tuple[Op, ...]]:
    """Value-directed BFS for operator chains with ``chain(source) == target``.

    Returns chains ordered by (depth, MDL). Chains are deduplicated by
    denotation at each level, which is the observational-equivalence pruning of
    proposal §4.8.
    """

    key = (content_digest(source_value), content_digest(target), max_results)
    cached = ctx._search_cache.get(key)
    if cached is not None:
        ctx.cache_hits += 1
        return list(cached)
    ctx.cache_misses += 1
    results = _search_chains_uncached(source_value, target, ctx, max_results=max_results)
    if len(ctx._search_cache) < ctx.max_cache_entries:
        ctx._search_cache[key] = tuple(results)
    return results


def _search_chains_uncached(
    source_value: Any,
    target: Any,
    ctx: SynthContext,
    *,
    max_results: int,
) -> list[tuple[Op, ...]]:
    """Uncached value-directed search; split out to keep cache semantics exact."""

    results: list[tuple[Op, ...]] = []
    if _eq(source_value, target):
        results.append(())
    frontier: list[tuple[Any, tuple[Op, ...]]] = [(source_value, ())]
    nodes = 0
    for _ in range(ctx.max_depth):
        kept: dict[str, tuple[tuple[int, int, int, str], Any, tuple[Op, ...]]] = {}
        for value, chain in frontier:
            for op in ctx.candidate_ops(value, target):
                nodes += 1
                if nodes > ctx.max_nodes:
                    return _rank(results, max_results)
                try:
                    out = op.apply(value)
                except (TypeMismatch, TypeError, ValueError, ZeroDivisionError):
                    continue
                new_chain = chain + (op,)
                if _eq(out, target):
                    results.append(new_chain)
                    if len(results) >= max_results * 4:
                        return _rank(results, max_results)
                if not isinstance(out, (str, int, float, list, dict)):
                    continue
                key = _denote(out)
                rank = chain_rank(new_chain)
                cur = kept.get(key)
                if cur is None or rank < cur[0]:
                    kept[key] = (rank, out, new_chain)
        frontier = [(v, c) for _, v, c in sorted(kept.values(), key=lambda x: x[0])[: ctx.max_frontier]]
        if not frontier:
            break
    return _rank(results, max_results)


def _rank(results: list[tuple[Op, ...]], max_results: int) -> list[tuple[Op, ...]]:
    uniq: dict[str, tuple[Op, ...]] = {}
    for chain in results:
        key = "|".join(str(o) for o in chain)
        if key not in uniq:
            uniq[key] = chain
    ranked = sorted(uniq.values(), key=chain_rank)
    return ranked[:max_results]


def _eq(a: Any, b: Any) -> bool:
    if isinstance(a, float) and isinstance(b, (int, float)):
        return math.isclose(a, float(b), rel_tol=1e-9, abs_tol=1e-9)
    if isinstance(b, float) and isinstance(a, (int, float)):
        return math.isclose(float(a), b, rel_tol=1e-9, abs_tol=1e-9)
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    return a == b


def _denote(value: Any) -> str:
    try:
        import json

        return json.dumps(value, sort_keys=True, default=str)[:512]
    except Exception:  # pragma: no cover - defensive
        return repr(value)[:512]
