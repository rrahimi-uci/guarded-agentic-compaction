"""Property tests: the invariants execution-plan §10.6 requires.

* no accepted expression depends on data unavailable at its slot;
* effect barriers are never crossed by an accepted window;
* split membership is disjoint;
* deoptimization before commitment is observationally equivalent to the baseline
  entry state;
* the planted synthetic regions are recovered and the planted invalid ones rejected.
"""

from __future__ import annotations

import random

import pytest

from agent_compaction.evaluation.splits import LeakageError, Splits, assert_disjoint, make_splits
from agent_compaction.graph.provenance import SlotMark, build_all
from agent_compaction.graph.windows import mine
from agent_compaction.grc.compile import GrcConfig, compile_grc
from agent_compaction.grc.dsl import Const, Expr
from agent_compaction.grc.program import CallStep, LoopStep
from agent_compaction.grc.synthesize import synthesize_program, var_name_for
from agent_compaction.schema.effects import EffectClass

from scripts.generate_synthetic import ENTRY_ALLOWLIST, SYNTHETIC_CATALOG, generate


@pytest.fixture(scope="module")
def mined():
    episodes = generate(n_episodes=360, seed=11)
    graphs, policy = build_all(episodes, SYNTHETIC_CATALOG)
    result = mine(graphs, SYNTHETIC_CATALOG, entry_schema=ENTRY_ALLOWLIST, s_min=5, min_days=3)
    return episodes, graphs, policy, result


def test_no_accepted_window_contains_a_non_compilable_tool(mined):
    _, _, _, result = mined
    for fam in result.families:
        for w in fam.windows:
            for step in w.steps:
                spec = SYNTHETIC_CATALOG.get(step.tool)
                assert spec.compilable, f"barrier tool {step.tool} inside an accepted window"
                assert spec.effect is not EffectClass.UNKNOWN


def test_planted_write_and_undeclared_tools_are_never_in_a_family(mined):
    _, _, _, result = mined
    tools = {t for fam in result.families for t in fam.tools}
    assert "notes.write" not in tools
    assert "shadow.undeclared" not in tools
    assert result.blocked_by_tool.get("notes.write", 0) > 0
    assert result.blocked_by_tool.get("shadow.undeclared", 0) > 0


def test_no_accepted_window_has_an_ungrounded_or_ambiguous_slot(mined):
    _, _, _, result = mined
    for fam in result.families:
        for w in fam.windows:
            for step in w.steps:
                for slot in step.slots.values():
                    assert slot.mark not in (SlotMark.UNGROUNDED, SlotMark.AMBIGUOUS)


def test_every_live_in_is_an_allowlisted_entry_state_path(mined):
    _, _, _, result = mined
    allowed = {f"z.{p}" for p in ENTRY_ALLOWLIST}
    for fam in result.families:
        for w in fam.windows:
            for li in w.live_in:
                assert li in allowed


def test_bindings_only_reference_the_entry_state_or_earlier_steps(mined):
    episodes, _, policy, result = mined
    fam = max(result.families, key=lambda f: f.support)
    synth = synthesize_program(fam, fam.windows, SYNTHETIC_CATALOG, policy, n_permutations=20)
    assert synth.ok, synth.reason
    names = list(synth.names)
    for i, step in enumerate(synth.program.steps):
        if not isinstance(step, (CallStep, LoopStep)):
            continue
        available = {"z"} | set(names[:i])
        for path, binding in step.args.items():
            if isinstance(binding, Const):
                continue
            root = binding.source.split(".")[0].split("[")[0]
            assert root in available, f"{step.tool}.{path} reads {root}, unavailable at step {i}"


def test_planted_valid_region_is_recovered_with_a_synthesized_transform(mined):
    episodes, graphs, policy, _ = mined
    # Rolling-version drift is deliberately present in the synthetic corpus.  A
    # compiler invocation is scoped to one compatibility key; the batch API owns
    # the separate-version orchestration.
    key = episodes[0].manifest.compatibility_key()
    compatible = [
        (episode, graph)
        for episode, graph in zip(episodes, graphs)
        if episode.manifest.compatibility_key() == key
    ]
    episodes = [episode for episode, _graph in compatible]
    graphs = [graph for _episode, graph in compatible]
    splits = make_splits(episodes, seed=3)
    cfg = GrcConfig(entry_schema=ENTRY_ALLOWLIST, s_min=5, min_days=3, n_permutations=40, alpha=0.20)
    res = compile_grc(episodes, SYNTHETIC_CATALOG, splits, episodes[0].manifest, cfg, graphs=graphs, policy=policy)
    assert res.artifacts, res.report()
    art = res.artifacts[0]
    rendered = art.program.pretty()
    # the planted email normalisation must be recovered as a transform, not memorised
    assert "lower" in rendered
    assert "z.user_email" in rendered
    # the planted pagination integer must be a Const, never derived
    assert "Const(4)" in rendered or "limit = Const" in rendered


def test_positional_binding_is_rejected_in_favour_of_a_predicate(mined):
    episodes, graphs, policy, result = mined
    fam = max(result.families, key=lambda f: f.support)
    synth = synthesize_program(fam, fam.windows, SYNTHETIC_CATALOG, policy, n_permutations=20)
    assert synth.ok
    rendered = synth.program.pretty()
    if "acct_id" in rendered:
        assert "filter(status == 'active')" in rendered or "[0]" not in rendered


def test_splits_are_disjoint_and_stable(mined):
    episodes, _, _, _ = mined
    splits = make_splits(episodes, shadow_fraction=0.1, seed=7)
    assert_disjoint(splits)
    all_groups = set().union(*splits.roles.values())
    assert all_groups == {ep.group_id for ep in episodes}
    again = make_splits(episodes, shadow_fraction=0.1, seed=7)
    assert again.digest() == splits.digest()


def test_leakage_is_detected():
    bad = Splits(train=frozenset({"g1"}), test=frozenset({"g1"}))
    with pytest.raises(LeakageError):
        assert_disjoint(bad)


def test_split_digest_has_no_group_delimiter_collision():
    first = Splits(train=frozenset({"a,b", "c"}))
    second = Splits(train=frozenset({"a", "b,c"}))
    assert first.digest() != second.digest()


def test_chronological_split_puts_later_days_in_test(mined):
    episodes, _, _, _ = mined
    splits = make_splits(episodes, chronological=True, seed=1)
    day_of = {}
    for ep in episodes:
        day_of.setdefault(ep.group_id, ep.envelope.day)
    train_days = [day_of[g] for g in splits.train]
    test_days = [day_of[g] for g in splits.test]
    assert max(train_days) <= max(test_days)


def test_deopt_leaves_the_entry_state_untouched(mined):
    """A failed dispatch must not mutate the entry state or business state."""

    import copy

    from agent_compaction.runtime.facade import FacadeMode, ToolFacade
    from agent_compaction.runtime.interp import run_program

    episodes, graphs, policy, result = mined
    fam = max(result.families, key=lambda f: f.support)
    synth = synthesize_program(fam, fam.windows, SYNTHETIC_CATALOG, policy, n_permutations=20)
    entry = copy.deepcopy(fam.windows[0].episode.entry_state)
    before = copy.deepcopy(entry)

    def failing(tool, args):
        raise RuntimeError("injected")

    facade = ToolFacade(
        catalog=SYNTHETIC_CATALOG,
        mode=FacadeMode.LIVE,
        executor=failing,
        allowed_tools=tuple(synth.program.tools),
    )
    res = run_program(synth.program, entry, facade)
    assert not res.ok
    assert entry == before
