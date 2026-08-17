"""End to end on a real demonstration: capture → estimate → compile → promote → dispatch.

This is the test that would catch a regression the unit suites cannot see: an artifact that
compiles but never dispatches, a dispatch that changes quality, a fallback path that leaks
an effect, or a request ratio that silently becomes 1.0.

It runs a reduced workload so it stays inside a normal test budget, and asserts *relations*
(fewer requests, equal quality, zero artifact writes) rather than exact numbers, because the
exact numbers belong in `experiments/` where they are published with their manifest.
"""

from __future__ import annotations

import pytest

from guarded_agentic_compaction.evaluation.metrics import condition_metrics
from guarded_agentic_compaction.evaluation.splits import make_splits
from guarded_agentic_compaction.estimate.headroom import estimate
from guarded_agentic_compaction.graph.provenance import build_all
from guarded_agentic_compaction.grc.compile import GrcConfig, compile_grc
from guarded_agentic_compaction.registry.lifecycle import promote
from guarded_agentic_compaction.registry.store import Registry
from guarded_agentic_compaction.runtime.dispatch import DispatchMode, Dispatcher
from guarded_agentic_compaction.runtime.runner import CompactingRunner
from guarded_agentic_compaction.schema.artifacts import Lifecycle
from guarded_agentic_compaction.schema.effects import EffectCatalog

import demos.support as support
from demos.framework import Observation, run_workload, summarize

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def compiled():
    catalog = EffectCatalog.from_yaml(support.EFFECTS_PATH)
    world, specs = support.build_workload(n_episodes=2200, seed=4242)
    episodes = run_workload(specs, world, support.SupportPolicy(), support.MANIFEST)
    splits = make_splits(episodes, seed=4242)
    graphs, policy = build_all(episodes, catalog)
    est = estimate(
        episodes,
        catalog,
        entry_schema=support.ENTRY_ALLOWLIST,
        graphs=graphs,
        policy=policy,
    )
    cfg = GrcConfig(
        entry_schema=support.ENTRY_ALLOWLIST,
        s_min=5,
        min_days=3,
        n_permutations=100,
        max_candidates=6,
        max_artifacts=2,
        seed=4242,
    )
    res = compile_grc(
        episodes,
        catalog,
        splits,
        support.MANIFEST,
        cfg,
        sandbox=(lambda _w=world: _w),
        graphs=graphs,
        policy=policy,
    )
    return catalog, world, specs, episodes, splits, est, res


def test_estimator_finds_headroom_and_names_the_blockers(compiled):
    *_, est, _ = compiled
    assert est.n_B > 5
    assert est.k_mean >= 2
    assert est.delta_max > 0.05
    # kb.search is undeclared by design and must dominate the blocked mass
    assert "kb.search" in est.blocked_by_tool
    assert "kb.search" in est.undeclared_tools


def test_compilation_emits_a_readable_grounded_artifact(compiled):
    *_, splits, _, res = compiled
    assert res.artifacts, res.report()
    graph_groups = {graph.episode.group_id for graph in res.graphs}
    assert graph_groups <= set(splits.train | splits.dev | splits.calibration)
    assert graph_groups.isdisjoint(splits.test | splits.shadow)
    assert all(
        family.groups <= set(splits.train)
        for family in (res.mining.families if res.mining else ())
    )
    art = res.artifacts[0]
    text = art.explain()
    assert "z.ticket.requester_email |> lower" in text
    assert "filter(status == 'active') |> project('id')" in text
    # a literal-only pagination argument is bound as a constant whenever the region
    # reaches the paginated call; the shorter arm may stop before it
    if "billing.list_invoices" in art.program.tools:
        assert "limit = Const(3)" in text
    assert art.evidence.support_groups >= 5
    assert art.gate.risk_upper_bound <= art.gate.alpha
    assert art.evidence.metrics["perturbations_claimed"] is True
    # nothing that writes may appear in the program
    for tool in art.program.tools:
        assert compiled[0].compilable(tool)


def test_dispatch_reduces_requests_without_changing_quality_or_effects(compiled):
    catalog, world, specs, episodes, splits, _, res = compiled
    reg = Registry(name="e2e", signing_key=b"test-key")
    for art in res.artifacts:
        promote(art, Lifecycle.SHADOW, approved_by="", job_identity="job")
        promote(art, Lifecycle.APPROVED, approved_by="human@example", job_identity="job")
        promote(art, Lifecycle.ACTIVE, approved_by="human@example", job_identity="job")
        reg.add(art)

    test_specs = [s for s in specs if s.group_id in splits.test]
    assert test_specs

    base = run_workload(test_specs, support.SupportWorld(), support.SupportPolicy(), support.MANIFEST)
    disp = Dispatcher(registry=reg, catalog=catalog, mode=DispatchMode.LIVE)
    runner = CompactingRunner(
        dispatcher=disp,
        catalog=catalog,
        manifest=support.MANIFEST,
        max_train_day=max(s.day for s in specs),
        observation_factory=Observation,
    )
    comp = run_workload(
        test_specs, support.SupportWorld(), support.SupportPolicy(), support.MANIFEST, dispatcher=runner
    )

    mb, mc = summarize(base), summarize(comp)
    assert mc["requests"] < mb["requests"], (mb["requests"], mc["requests"])
    assert mc["requests"] / mb["requests"] < 0.90
    assert mc["quality"] >= mb["quality"] - 0.02
    assert mc["success_rate"] >= mb["success_rate"] - 0.02

    cm = condition_metrics("full", comp, catalog, dispatch_telemetry=disp.telemetry.as_dict())
    assert cm.aggregate["artifact_write_effects_total"] == 0
    assert cm.aggregate["incidents_total"] == 0
    assert cm.aggregate["coverage_phi"] > 0.3
    assert disp.telemetry.as_dict()["verifier_pass_rate"] >= 0.85


def test_shadow_mode_changes_nothing_but_still_measures_coverage(compiled):
    catalog, world, specs, episodes, splits, _, res = compiled
    reg = Registry(name="e2e-shadow")
    for art in res.artifacts:
        art.lifecycle = Lifecycle.ACTIVE
        reg.add(art)
    test_specs = [s for s in specs if s.group_id in splits.test][:120]

    base = run_workload(test_specs, support.SupportWorld(), support.SupportPolicy(), support.MANIFEST)
    disp = Dispatcher(registry=reg, catalog=catalog, mode=DispatchMode.SHADOW)
    runner = CompactingRunner(
        dispatcher=disp, catalog=catalog, manifest=support.MANIFEST, observation_factory=Observation
    )
    shadow = run_workload(
        test_specs, support.SupportWorld(), support.SupportPolicy(), support.MANIFEST, dispatcher=runner
    )
    mb, ms = summarize(base), summarize(shadow)
    assert ms["requests"] == pytest.approx(mb["requests"])
    assert ms["quality"] == pytest.approx(mb["quality"])
    tel = disp.telemetry.as_dict()
    assert tel["compacted"] == 0
    assert tel["attempts"] > 0


def test_freeze_one_candidate_before_calibration_avoids_lower_ranked_calibration(compiled):
    catalog, world, specs, episodes, splits, _, normal = compiled
    graphs, policy = build_all(episodes, catalog)
    frozen = compile_grc(
        episodes,
        catalog,
        splits,
        support.MANIFEST,
        GrcConfig(
            entry_schema=support.ENTRY_ALLOWLIST,
            s_min=5,
            min_days=3,
            n_permutations=100,
            max_candidates=6,
            max_artifacts=8,
            seed=4242,
            freeze_one_candidate_before_calibration=True,
        ),
        sandbox=(lambda _w=world: _w),
        graphs=graphs,
        policy=policy,
    )

    assert frozen.artifacts, frozen.report()
    assert frozen.artifacts[0].name == normal.artifacts[0].name
    assert len(frozen.candidates) < len(normal.candidates)
    assert sum(
        1
        for candidate in frozen.candidates
        if candidate.notes.get("candidate_selection") == "frozen_before_calibration"
    ) == 1
    assert not any(candidate.stage == "dominated" for candidate in frozen.candidates)
    assert not any(
        (candidate.rejected or "").startswith("gate_retire:")
        for candidate in frozen.candidates
    )
