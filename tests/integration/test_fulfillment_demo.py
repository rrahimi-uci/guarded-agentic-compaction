"""Demo E end-to-end checks that need no provider credential.

Everything the live run depends on except the model calls: the world grades what
it claims to grade, the compiled prefix executes and verifies under every branch
profile, the loop-bearing artifact is refused by the Model adapter rather than
mis-executed, and the drifted entry state misses the hard guard.
"""

from __future__ import annotations

import pytest

from agent_compaction.runtime.facade import FacadeMode, ToolFacade
from agent_compaction.runtime.interp import run_program
from agent_compaction.runtime.model_provider import _model_program_supported
from demos.live_runtime import build_live_catalog, make_function_tools, safe_tool_name
from experiments.conditions.registry import get_demo

import experiments.live_run as live_run

SEED = 20260802


@pytest.fixture(scope="module")
def fixtures():
    spec = get_demo("fulfillment")
    world, candidates = spec.make_workload(n_episodes=120, seed=SEED)
    scenarios = live_run._select_fulfillment_specs(world, candidates, 4)
    catalog = build_live_catalog(
        spec.catalog(), live_run.FULFILLMENT_TOOLS, name="fulfillment-test"
    )
    inverse = {safe_tool_name(name): name for name in live_run.FULFILLMENT_TOOLS}
    return spec, world, scenarios, catalog, inverse


def _run(program, entry_state, world, catalog, inverse):
    facade = ToolFacade(
        catalog=catalog,
        mode=FacadeMode.SANDBOX,
        executor=lambda tool, args: world.execute(inverse[tool], args),
        max_calls=16,
    )
    return run_program(program, entry_state, facade)


class TestWorld:
    def test_catalog_blocks_exactly_the_uncompilable_tools(self, fixtures):
        spec, _world, _scen, _cat, _inv = fixtures
        coverage = spec.catalog().validate_coverage(spec.baseline_config.tools)
        assert coverage["undeclared"] == []
        assert set(coverage["blocked"]) == {
            "case.escalate",
            "orders.reschedule",
            "refunds.issue_credit",
            "risk.score",
        }
        assert coverage["blocked"]["refunds.issue_credit"] == "APPROVAL_BARRIER"
        assert coverage["blocked"]["risk.score"] == "UNKNOWN_EFFECT"

    def test_baseline_policy_solves_the_workload(self, fixtures):
        spec, _world, _scen, _cat, _inv = fixtures
        from demos.framework import run_workload, summarize

        world, specs = spec.make_workload(n_episodes=60, seed=SEED)
        episodes = run_workload(
            specs, world, spec.policy_from_config(spec.baseline_config), spec.manifest
        )
        metrics = summarize(episodes)
        assert metrics["success_rate"] == 1.0
        assert metrics["safety_events"] == 0.0
        # Every episode commits exactly once, so the region can only be a prefix.
        assert metrics["requests"] > metrics["tool_calls"]

    def test_every_episode_makes_exactly_one_commitment(self, fixtures):
        spec, _world, _scen, _cat, _inv = fixtures
        from demos.framework import run_workload

        world, specs = spec.make_workload(n_episodes=40, seed=SEED)
        episodes = run_workload(
            specs, world, spec.policy_from_config(spec.baseline_config), spec.manifest
        )
        writes = {"orders.reschedule", "case.escalate", "refunds.issue_credit"}
        for episode in episodes:
            committed = [c for c in episode.tool_calls() if c.tool in writes]
            assert len(committed) == 1, episode.episode_id


class TestCompiledPrefix:
    def test_scenarios_cover_both_sides_of_the_pagination_branch(self, fixtures):
        _spec, world, scenarios, _cat, _inv = fixtures
        paginated = {
            len(world.shipments[s.entry_state["case"]["order_ref"]]) > 3 for s in scenarios
        }
        assert paginated == {True, False}

    def test_program_executes_and_verifies_under_every_branch_profile(self, fixtures):
        spec, world, scenarios, catalog, inverse = fixtures
        program = live_run._fulfillment_program()
        artifact = live_run._fulfillment_artifact(
            manifest=spec.manifest,
            catalog=catalog,
            program=program,
            artifact_id="test-straight",
            pin_entry_contract="wms_v2",
        )
        profiles = set()
        for scenario in scenarios:
            result = _run(program, scenario.entry_state, world, catalog, inverse)
            assert result.ok, result.error
            assert artifact.verifier.verify(
                result.outputs,
                result.env,
                result.provenance,
                tuple(sorted(result.effects)),
                len(result.calls),
            ) == []
            profiles.add(len(result.calls))
        # 4 calls (no branch), 5 (one branch), 6 (two branches) all occur.
        assert len(profiles) >= 3

    def test_program_never_touches_a_write_or_an_unknown_tool(self, fixtures):
        spec, world, scenarios, catalog, inverse = fixtures
        program = live_run._fulfillment_program()
        for scenario in scenarios:
            result = _run(program, scenario.entry_state, world, catalog, inverse)
            assert set(result.effects) <= {"READ_EXTERNAL", "READ_LOCAL"}
            assert all(
                tool not in {"orders_reschedule", "case_escalate", "risk_score"}
                for tool, _args in result.calls
            )

    def test_shipment_evidence_matches_the_graded_expectation(self, fixtures):
        _spec, world, scenarios, catalog, inverse = fixtures
        program = live_run._fulfillment_program()
        for scenario in scenarios:
            result = _run(program, scenario.entry_state, world, catalog, inverse)
            seen = list((result.outputs.get("page0") or {}).get("shipments") or [])
            page1 = result.outputs.get("page1") or {}
            seen += list(page1.get("shipments") or [])
            assert len(seen) == world.expected(scenario.entry_state)["shipment_count"]

    def test_loop_variant_is_semantically_equivalent(self, fixtures):
        _spec, world, scenarios, catalog, inverse = fixtures
        straight = live_run._fulfillment_program()
        looped = live_run._fulfillment_program(paginate_as_loop=True)
        for scenario in scenarios:
            a = _run(straight, scenario.entry_state, world, catalog, inverse)
            b = _run(looped, scenario.entry_state, world, catalog, inverse)
            assert a.ok and b.ok
            pages_a = list((a.outputs.get("page0") or {}).get("shipments") or []) + list(
                (a.outputs.get("page1") or {}).get("shipments") or []
            )
            pages_b = [s for page in (b.outputs.get("pages") or []) for s in page["shipments"]]
            assert pages_a == pages_b


class TestAdapterRefusals:
    def test_model_adapter_accepts_the_straight_line_program(self, fixtures):
        spec, _world, _scen, catalog, _inv = fixtures
        artifact = live_run._fulfillment_artifact(
            manifest=spec.manifest,
            catalog=catalog,
            program=live_run._fulfillment_program(),
            artifact_id="a",
            pin_entry_contract="wms_v2",
        )
        assert _model_program_supported(artifact)

    def test_model_adapter_refuses_the_loop_bearing_program(self, fixtures):
        spec, _world, _scen, catalog, _inv = fixtures
        artifact = live_run._fulfillment_artifact(
            manifest=spec.manifest,
            catalog=catalog,
            program=live_run._fulfillment_program(paginate_as_loop=True),
            artifact_id="b",
            pin_entry_contract="wms_v2",
        )
        assert not _model_program_supported(artifact)

    def test_drifted_entry_state_misses_the_hard_guard(self, fixtures):
        spec, _world, scenarios, catalog, _inv = fixtures
        artifact = live_run._fulfillment_artifact(
            manifest=spec.manifest,
            catalog=catalog,
            program=live_run._fulfillment_program(),
            artifact_id="c",
            pin_entry_contract="wms_v2",
        )
        scenario = scenarios[0]
        drifted = live_run._drifted(scenario)
        assert drifted.entry_state["case"]["intake"] == "wms_v3"

        def context(entry):
            return {
                "model": spec.manifest.model,
                "entry_contract_version": entry["case"]["intake"],
            }

        assert artifact.guard.evaluate(scenario.entry_state, context(scenario.entry_state)) == []
        reasons = artifact.guard.evaluate(drifted.entry_state, context(drifted.entry_state))
        assert reasons == ["manifest:entry_contract_version"]

    def test_verifier_rejects_an_unexpected_call_count(self, fixtures):
        spec, _world, _scen, catalog, _inv = fixtures
        artifact = live_run._fulfillment_artifact(
            manifest=spec.manifest,
            catalog=catalog,
            program=live_run._fulfillment_program(),
            artifact_id="d",
            pin_entry_contract="wms_v2",
        )
        assert artifact.verifier.call_counts == (4, 5, 6, 7)
        assert artifact.verifier.verify({}, {}, {}, ("READ_EXTERNAL",), 9) == ["n_calls:9"]


class TestRouter:
    def test_route_tree_separates_every_exception_class(self):
        tree = live_run._fit_router(seed=SEED, n_episodes=400)
        labels = {leaf.label for leaf in tree.stable_leaves()}
        assert labels == {
            "route:carrier_delay",
            "route:stock_shortfall",
            "route:address_invalid",
            "route:payment_hold",
        }
        assert all(leaf.purity >= 0.90 for leaf in tree.stable_leaves())

    def test_every_route_surface_is_a_strict_subset_of_the_generalist(self):
        import demos.fulfillment as fulfillment

        for key, tools in fulfillment.ROUTE_TOOLS.items():
            assert set(tools) < set(live_run.FULFILLMENT_TOOLS), key
            assert set(fulfillment.ROUTE_BLOCKS[key]) < set(fulfillment.PROMPT_BLOCKS), key
            # The protected blocks survive every pruning decision.
            assert set(fulfillment.PROTECTED_BLOCKS) <= set(fulfillment.ROUTE_BLOCKS[key])

    def test_route_surface_retains_the_tools_that_route_actually_needs(self):
        import demos.fulfillment as fulfillment

        assert "carrier.track" in fulfillment.ROUTE_TOOLS["carrier_delay"]
        assert "inventory.check" in fulfillment.ROUTE_TOOLS["stock_shortfall"]
        assert "carrier.track" not in fulfillment.ROUTE_TOOLS["stock_shortfall"]
        for tools in fulfillment.ROUTE_TOOLS.values():
            assert "risk.score" not in tools

    def test_router_abstains_when_no_leaf_matches(self):
        spec = get_demo("fulfillment")
        tree = live_run._fit_router(seed=SEED, n_episodes=400)
        features = {path: None for path in spec.entry_allowlist}
        features["case.exception_class"] = "unmodelled_class"
        assert tree.route(features) is None


class TestLiveSurface:
    def test_function_tools_expose_the_whole_baseline_surface(self, fixtures):
        _spec, world, _scen, _cat, _inv = fixtures
        tools, aliases = make_function_tools(world, live_run.FULFILLMENT_TOOLS)
        assert len(tools) == len(live_run.FULFILLMENT_TOOLS)
        assert aliases["shipments_list_page"] == "shipments.list_page"

    def test_prompt_assembly_keeps_every_named_block(self):
        import demos.fulfillment as fulfillment

        text = live_run._fulfillment_prompt(fulfillment.PROMPT_BLOCKS)
        assert "risk_score is advisory only" in text
        for rule in ("carrier_eta_within_sla", "stock_available", "payment_hold_credit"):
            assert rule in text

    def test_every_route_prompt_still_describes_the_full_procedure(self):
        """A wrapper that may abstain needs an instruction that survives abstention.

        Demos A and B specialize the compacted prompt to assert that evidence already
        exists. That is only safe while compaction is guaranteed, and it never is: the
        first live run of this demo scored 0.33–0.75 on exactly the conditions where the
        runtime correctly refused, because the agent had been told to trust evidence the
        guard had just stopped it from gathering.
        """

        import demos.fulfillment as fulfillment

        for key, blocks in fulfillment.ROUTE_BLOCKS.items():
            text = live_run._fulfillment_prompt(blocks)
            assert "Call auth_issue_ops_token first" in text, key
            assert "has_more true" in text, key
            assert "exactly one commitment" in text.lower(), key


class TestQuotaAttestation:
    """The mint's declaration decides whether the Model adapter can dispatch at all."""

    def _artifact(self, catalog, spec):
        return live_run._fulfillment_artifact(
            manifest=spec.manifest,
            catalog=catalog,
            program=live_run._fulfillment_program(),
            artifact_id="quota",
            pin_entry_contract="wms_v2",
        )

    def test_declared_mint_is_not_quota_attested(self, fixtures):
        spec, _world, _scen, catalog, _inv = fixtures
        assert not catalog.get("auth_issue_ops_token").quota_attested
        assert catalog.compilable("auth_issue_ops_token")

    def test_quota_attested_mint_fails_closed_without_a_staging_owner(self, fixtures):
        """Flipping the flag must block live dispatch, not silently proceed.

        The ``CompactingModel`` adapter owns no staging boundary and passes no
        ``snapshot_fn``, so a program touching a quota-attested tool can never be
        dispatched through it. That is the documented reason the outer
        ``CompactingRunner`` is the recommended path.
        """

        from agent_compaction.runtime.dispatch import DispatchMode, Dispatcher
        from agent_compaction.registry.store import Registry
        from agent_compaction.schema.artifacts import DispatchOutcome
        from agent_compaction.schema.effects import EffectCatalog

        spec, _world, scenarios, catalog, _inv = fixtures
        payload = catalog.model_dump(mode="json")
        payload["tools"]["auth_issue_ops_token"]["quota_attested"] = True
        attested = EffectCatalog.from_dict(payload)

        entry = scenarios[0].entry_state
        for active, expect_dispatch in ((catalog, True), (attested, False)):
            registry = Registry(name="quota-test")
            registry.add(self._artifact(active, spec))
            dispatcher = Dispatcher(
                registry=registry, catalog=active, mode=DispatchMode.LIVE
            )
            decision = dispatcher.decide(
                compatibility_key=spec.manifest.compatibility_key(),
                partition={},
                entry_state=entry,
                context={
                    "model": spec.manifest.model,
                    "entry_contract_version": entry["case"]["intake"],
                },
                executor=None,
                recording=None,
                defer_execution=True,
            )
            if expect_dispatch:
                assert decision.artifact is not None
            else:
                assert decision.outcome is DispatchOutcome.BASELINE
                assert dispatcher.telemetry.guard_misses.get(
                    "missing_reversibility_snapshot"
                )
