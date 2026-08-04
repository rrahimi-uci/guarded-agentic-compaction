"""Unit tests for the closed transform library (proposal §4.3)."""

from __future__ import annotations

import pytest

from agent_compaction.grc.dsl import (
    LIBRARY_VERSION,
    OPERATOR_CLASSES,
    Const,
    Expr,
    Op,
    SynthContext,
    TypeMismatch,
    apply_chain,
    chain_rank,
    search_chains,
)


def test_library_is_closed_and_versioned():
    names = {n for names in OPERATOR_CLASSES.values() for n in names}
    assert LIBRARY_VERSION == "T-v1"
    # the enumerated list of proposal §4.3 has 23 operator forms in 5 classes; the
    # table labels it "22 operators" (see docs/spec-review.md finding S1)
    assert len(names) == 23
    assert set(OPERATOR_CLASSES) == {
        "identity_coercion",
        "string",
        "numeric",
        "collection",
        "temporal",
    }


@pytest.mark.parametrize(
    "op,value,expected",
    [
        (Op("lower"), "AB@C", "ab@c"),
        (Op("strip"), "  x  ", "x"),
        (Op("split", ("@", 0)), "a@b", "a"),
        (Op("split", ("@", -1)), "a@b", "b"),
        (Op("add", (2,)), 3, 5),
        (Op("mul", (2,)), 3, 6),
        (Op("len"), [1, 2, 3], 3),
        (Op("sum"), [1, 2, 3], 6),
        (Op("first"), [{"a": 1}], {"a": 1}),
        (Op("project", ("a",)), [{"a": 1}, {"a": 2}], [1, 2]),
        (Op("filter", ("s", "==", "ok")), [{"s": "ok"}, {"s": "no"}], [{"s": "ok"}]),
        (Op("fmt", ("<{}>",)), "x", "<x>"),
        (Op("date_fmt", ("%Y",)), "2026-06-01", "2026"),
    ],
)
def test_operator_denotations(op, value, expected):
    assert op.apply(value) == expected


@pytest.mark.parametrize(
    "op,value",
    [
        (Op("lower"), 5),
        (Op("sum"), [{"a": 1}]),
        (Op("first"), []),
        (Op("len"), 7),
        (Op("project", ("missing",)), {"a": 1}),
        (Op("date_fmt", ("%Y",)), "not-a-date"),
    ],
)
def test_operators_reject_wrong_types(op, value):
    with pytest.raises(TypeMismatch):
        op.apply(value)


def test_search_finds_the_select_then_project_pattern():
    recs = [
        {"id": "cus_A", "status": "closed"},
        {"id": "cus_B", "status": "active"},
    ]
    chains = search_chains(recs, "cus_B", SynthContext(max_depth=2), max_results=8)
    rendered = ["|".join(str(o) for o in c) for c in chains]
    assert any("filter(status == 'active')" in r and "project('id')" in r for r in rendered)


def test_memorizing_filter_constant_is_not_generated():
    """``filter(id == <the answer>)`` encodes the target instead of deriving it."""

    recs = [{"id": "cus_A", "status": "closed"}, {"id": "cus_B", "status": "active"}]
    for chain in search_chains(recs, "cus_B", SynthContext(max_depth=2), max_results=8):
        assert "filter(id == 'cus_B')" not in [str(o) for o in chain]


def test_order_stable_chain_outranks_positional_one():
    """``filter`` must beat ``last`` when both fit: positional access is unstable."""

    recs = [{"id": "a", "status": "closed"}, {"id": "b", "status": "active"}]
    chains = search_chains(recs, "b", SynthContext(max_depth=2), max_results=8)
    first = "|".join(str(o) for o in chains[0])
    assert "filter" in first
    assert chain_rank(chains[0]) < chain_rank((Op("last"), Op("project", ("id",))))


def test_depth_bound_is_respected():
    ctx = SynthContext(max_depth=1)
    recs = [{"id": "a", "status": "closed"}, {"id": "b", "status": "active"}]
    for chain in search_chains(recs, "b", ctx, max_results=8):
        assert len(chain) <= 1


def test_search_cache_reuses_identical_value_problems():
    ctx = SynthContext(max_depth=2)
    source = [{"id": "a", "status": "closed"}, {"id": "b", "status": "active"}]
    first = search_chains(source, "b", ctx, max_results=8)
    second = search_chains(source, "b", ctx, max_results=8)
    assert first == second
    assert ctx.cache_misses == 1
    assert ctx.cache_hits == 1


def test_expression_evaluation_and_roundtrip():
    from agent_compaction.grc.dsl import binding_from_dict

    expr = Expr("z.ticket.requester_email", (Op("lower"),))
    env = {"z": {"ticket": {"requester_email": "A@B.example"}}}
    assert expr.evaluate(env) == "a@b.example"
    again = binding_from_dict(expr.to_dict())
    assert again.evaluate(env) == "a@b.example"
    assert binding_from_dict(Const(3).to_dict()).evaluate(env) == 3


def test_missing_source_path_raises_rather_than_guessing():
    expr = Expr("z.nope", (Op("lower"),))
    with pytest.raises(TypeMismatch):
        expr.evaluate({"z": {}})


def test_loop_does_not_rewrite_an_unrelated_integer_literal():
    from agent_compaction.grc.program import LoopStep, Predicate, Program
    from agent_compaction.runtime.facade import FacadeMode, ToolFacade
    from agent_compaction.runtime.interp import run_program
    from agent_compaction.schema.effects import EffectCatalog

    catalog = EffectCatalog.from_dict(
        {
            "tools": {
                "page": {
                    "effect": "READ_LOCAL",
                    "capabilities": ["speculatable", "replayable"],
                }
            }
        }
    )
    seen = []

    def execute(_tool, args):
        seen.append(dict(args))
        return {"items": [1, 2] if len(seen) == 1 else [3]}

    program = Program(
        steps=[
            LoopStep(
                var="page",
                tool="page",
                args={"limit": Const(4)},
                accumulate="items",
                counter=None,
                continue_when=Predicate("page.items", "len==", 2),
            )
        ]
    )
    result = run_program(
        program,
        {},
        ToolFacade(catalog=catalog, mode=FacadeMode.LIVE, executor=execute),
    )
    assert result.ok
    assert seen == [{"limit": 4}, {"limit": 4}]
    assert result.env["page"] == [{"items": [1, 2]}, {"items": [3]}]
