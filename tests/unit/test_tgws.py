"""TGWS unit tests: route fitting, stability checks, and greedy pruning."""

from __future__ import annotations

import pytest

from agent_compaction.tgws.prune import EvalResult, LeafConfig, Objective, prune_leaf
from agent_compaction.tgws.routes import (
    RouteLeaf,
    build_examples,
    default_route_label,
    fit_route_tree,
)

from scripts.generate_synthetic import ENTRY_ALLOWLIST, generate


def _episodes():
    return generate(n_episodes=300, seed=13)


def test_route_labels_come_from_observable_behaviour():
    eps = _episodes()
    labels = {default_route_label(ep) for ep in eps}
    assert labels
    assert all(l.startswith(("path:", "handoff:")) for l in labels)


def test_route_features_are_restricted_to_the_allowlist():
    eps = _episodes()
    examples = build_examples(eps, ENTRY_ALLOWLIST)
    for ex in examples:
        assert set(ex.features).issubset(set(ENTRY_ALLOWLIST))


def test_tree_respects_depth_support_and_purity_bounds():
    eps = _episodes()
    tree = fit_route_tree(eps, ENTRY_ALLOWLIST, max_depth=3, min_support=20, min_purity=0.9, min_groups=5)
    for leaf in tree.leaves:
        assert len(leaf.predicates) <= 3
        assert leaf.support >= 20
        assert leaf.group_support >= 5
    for leaf in tree.stable_leaves():
        assert leaf.purity >= 0.9


def test_unstable_leaves_are_marked_not_silently_used():
    """A leaf whose purity collapses in one subgroup must be rejected."""

    from agent_compaction.tgws.routes import _check_stability, RouteExample

    good = [
        RouteExample(f"e{i}", f"g{i}", f"2026-05-{1 + i % 20:02d}", "p1", "t1", {"a": 1}, "L")
        for i in range(40)
    ]
    ok, why = _check_stability(good, "L", 0.9)
    assert ok and not why

    mixed = good[:20] + [
        RouteExample(f"x{i}", f"h{i}", f"2026-05-{1 + i % 20:02d}", "p2", "t1", {"a": 1}, "OTHER")
        for i in range(20)
    ]
    ok2, why2 = _check_stability(mixed, "L", 0.9)
    assert not ok2
    assert "subgroup" in why2 or "temporal" in why2


def _evaluator(costs: dict[str, EvalResult]):
    def evaluate(config: LeafConfig) -> EvalResult:
        key = "|".join(sorted(config.prompt_blocks)) + "#" + "|".join(sorted(config.tools))
        return costs.get(key, costs["default"])

    return evaluate


def test_pruning_accepts_only_non_inferior_removals():
    base = LeafConfig(
        agent="a",
        model="m",
        reasoning_tier="default",
        prompt_blocks=("keep", "drop", "harmful"),
        tools=("t1", "t2"),
    )
    baseline = EvalResult(quality=0.9, requests=10, input_tokens=1000, output_tokens=100,
                          latency_ms=500, safety_events=0, n_episodes=50)

    def evaluate(config: LeafConfig) -> EvalResult:
        blocks = set(config.prompt_blocks)
        if "harmful" not in blocks and "drop" in blocks:
            # removing 'harmful' is cheap and harmless
            return EvalResult(0.9, 9.0, 900, 95, 480, 0, 50)
        if "drop" not in blocks and "harmful" in blocks:
            # removing 'drop' costs quality beyond the margin
            return EvalResult(0.5, 8.0, 800, 90, 450, 0, 50)
        if "harmful" not in blocks and "drop" not in blocks:
            return EvalResult(0.5, 7.0, 700, 85, 430, 0, 50)
        return baseline

    pruned, result, trace = prune_leaf(
        base, evaluate, objective=Objective(epsilon_quality=0.02), budget=40
    )
    assert "harmful" not in pruned.prompt_blocks
    assert "drop" in pruned.prompt_blocks  # rejected: quality regression
    assert result.quality >= baseline.quality - 0.02
    assert any(s["accepted"] and s["item"] == "harmful" for s in trace.steps)
    assert any(not s["accepted"] and s["item"] == "drop" for s in trace.steps)


def test_pruning_never_touches_protected_elements():
    base = LeafConfig("a", "m", "default", ("keep", "policy"), ("t1", "write_tool"))

    def evaluate(config: LeafConfig) -> EvalResult:
        # everything looks strictly better when things are removed
        n = len(config.prompt_blocks) + len(config.tools)
        return EvalResult(0.95, float(n), 100.0 * n, 10.0 * n, 50.0 * n, 0, 50)

    pruned, _, _ = prune_leaf(
        base,
        evaluate,
        protected_tools=("write_tool",),
        protected_blocks=("policy",),
        budget=40,
    )
    assert "write_tool" in pruned.tools
    assert "policy" in pruned.prompt_blocks


def test_pruning_rejects_a_removal_that_raises_safety_events():
    # a single removable block, so the only proposal on the table is the unsafe one
    base = LeafConfig("a", "m", "default", ("guard",), ("t1",))
    baseline = EvalResult(0.9, 10.0, 1000, 100, 500, 0, 50)

    def evaluate(config: LeafConfig) -> EvalResult:
        if "guard" not in config.prompt_blocks:
            # cheaper and *better* on quality, but it introduces a safety event
            return EvalResult(0.95, 8.0, 800, 90, 450, safety_events=1, n_episodes=50)
        return baseline

    # `t1` is protected so that the guard block is the only live proposal
    pruned, _, trace = prune_leaf(base, evaluate, protected_tools=("t1",), budget=20)
    assert pruned == base
    assert any("safety" in s["reason"] for s in trace.steps)


def test_objective_prices_tool_surface_and_complexity():
    obj = Objective()
    r = EvalResult(0.9, 10.0, 1000, 100, 500, 0, 50)
    big = LeafConfig("a", "m", "d", ("b1", "b2"), ("t1", "t2", "t3"))
    small = LeafConfig("a", "m", "d", ("b1",), ("t1",))
    assert obj.value(r, small) < obj.value(r, big)


def test_unseen_categorical_value_abstains_instead_of_taking_the_catch_all():
    """A decision tree's last leaf is a conjunction of negations.

    Without an observed-value domain, an entry carrying a category that never
    appeared in training matches that leaf by construction and silently inherits a
    route whose purity was never measured on it.
    """

    from agent_compaction.tgws.routes import RouteTree

    catch_all = RouteLeaf(
        predicates=(("channel", "!=", "email"),),
        label="route:phone",
        support=100,
        purity=1.0,
        coverage=0.5,
        group_support=40,
    )
    tree = RouteTree(
        leaves=[
            RouteLeaf(
                predicates=(("channel", "==", "email"),),
                label="route:email",
                support=100,
                purity=1.0,
                coverage=0.5,
                group_support=40,
            ),
            catch_all,
        ],
        categorical_domains={"channel": ("chat", "email", "phone")},
    )

    assert tree.route({"channel": "email"}).label == "route:email"
    assert tree.route({"channel": "phone"}).label == "route:phone"
    # 'fax' matches the catch-all leaf's predicate but was never observed.
    assert catch_all.matches({"channel": "fax"})
    assert tree.out_of_domain({"channel": "fax"}) == ("channel",)
    assert tree.route({"channel": "fax"}) is None


def test_numeric_split_features_are_not_pinned_to_observed_values():
    """A ``>=`` threshold extrapolates by design; pinning it would reject valid input."""

    eps = _episodes()
    tree = fit_route_tree(eps, ENTRY_ALLOWLIST, min_support=10, min_groups=4)
    numeric = {
        path
        for leaf in tree.leaves
        for path, op, _c in leaf.predicates
        if op in (">=", "<")
    }
    assert numeric.isdisjoint(tree.categorical_domains)


def test_domain_is_reported_so_a_reviewer_can_see_what_abstains():
    eps = _episodes()
    tree = fit_route_tree(eps, ENTRY_ALLOWLIST, min_support=10, min_groups=4)
    if tree.categorical_domains:
        assert "anything else abstains" in tree.report()
