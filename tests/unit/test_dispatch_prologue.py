"""Read-only prologue: acceptance tests 1-4 of the protocol.

``paper/supplementary/read-only-prologue-protocol.md`` fixes what an implementation
of the position-invariant relaxation must pass before the paper may claim it:

1. a prologue mismatch, an extra call, an order change, a manifest mismatch or an
   unknown effect in the prologue returns the unchanged baseline agent;
2. no call already committed by the host is replayed and the compiled region's
   call count is unchanged;
3. provenance is recomputed with the prologue outputs as explicit live-ins and any
   slot that becomes ungrounded or ambiguous retires the region;
4. the archived suffix-dispatch pilot (reordered and duplicated calls) returns
   the baseline.

Acceptance test 5 (AppWorld eligibility per architecture) is a measurement, run by
``paper/scripts/appworld_dispatch_prologue_preflight.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from guarded_agentic_compaction.grc.composite import synthesize_composite
from guarded_agentic_compaction.grc.dsl import Const, Expr
from guarded_agentic_compaction.grc.program import CallStep, Program
from guarded_agentic_compaction.registry.store import Registry
from guarded_agentic_compaction.runtime.dispatch import DispatchMode, Dispatcher
from guarded_agentic_compaction.runtime.manual import ManualPreModelPlan, ManualPreModelRunner
from guarded_agentic_compaction.runtime.model_provider import ArtifactPlan, _committed_calls
from guarded_agentic_compaction.runtime.prologue import (
    CommittedCall,
    match_prologue,
    prologue_grounding_reasons,
)
from guarded_agentic_compaction.schema.artifacts import (
    Artifact,
    DispatchOutcome,
    Gate,
    GateModel,
    HardGuard,
    Lifecycle,
    OutputClause,
    Prologue,
    PrologueCall,
    Verifier,
)
from guarded_agentic_compaction.schema.effects import EffectCatalog
from guarded_agentic_compaction.schema.traces import ExecutionManifest


ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "paper" / "results" / "github_live" / "pilot_2026-08-03"

READ = {
    "effect": "READ_LOCAL",
    "capabilities": ["speculatable", "replayable", "cacheable", "batchable"],
}
CATALOG = EffectCatalog.from_dict(
    {
        "name": "prologue-test",
        "version": 1,
        "tools": {
            # the documentation read the AppWorld architectures open with; declared
            # here as the protocol would require (it is undeclared in the signed
            # AppWorld catalog today, see the preflight script)
            "api_docs.show_api_descriptions": READ,
            "supervisor.show_active_task": READ,
            "supervisor.show_profile": READ,
            "supervisor.show_account_passwords": READ,
            # declared but never admissible as a prologue
            "amazon.login": {"effect": "WRITE_REVERSIBLE", "capabilities": []},
            "api_docs.show_app_descriptions": {"effect": "READ_LOCAL", "capabilities": ["cacheable"]},
            "api_docs.unknown": {"effect": "UNKNOWN"},
        },
    }
)
MANIFEST = ExecutionManifest(
    manifest_id="prologue",
    model="model",
    effect_catalog_version=CATALOG.catalog_version,
)
DOCS = {"default_section": "basic", "apis": ["show_profile", "show_account_passwords"]}
DOCS_CALL = CommittedCall("api_docs.show_api_descriptions", {"app_name": "supervisor"}, DOCS)
TASK_CALL = CommittedCall("supervisor.show_active_task", {}, {"task_id": "t1"})


def _program(*, section_from_prologue: bool = True, section_source: str = "docs.default_section") -> Program:
    """The admitted two-read region; one slot optionally bound to the prologue output."""

    profile_args = {"section": Expr(section_source, ())} if section_from_prologue else {}
    return Program(
        theta=("task_id",),
        steps=[
            CallStep(var="profile", tool="supervisor.show_profile", args=profile_args),
            CallStep(var="passwords", tool="supervisor.show_account_passwords", args={}),
        ],
        outputs={"profile": Expr("profile", ()), "passwords": Expr("passwords", ())},
        removed_requests=2,
    )


def _prologue(*calls: PrologueCall) -> Prologue:
    if not calls:
        calls = (PrologueCall("docs", "api_docs.show_api_descriptions", {"app_name": Const("supervisor")}),)
    return Prologue(calls=tuple(calls))


def _artifact(prologue: Prologue | None, program: Program | None = None, *, artifact_id: str = "p-1") -> Artifact:
    return Artifact(
        artifact_id=artifact_id,
        name="prologue-test",
        program=program or _program(section_from_prologue=prologue is not None),
        guard=HardGuard(manifest_pins={"model": "model"}, allowed_effects=("READ_LOCAL",)),
        verifier=Verifier(
            clauses=[
                OutputClause("profile", "dict", provenance=("supervisor.show_profile",)),
                OutputClause("passwords", "dict", provenance=("supervisor.show_account_passwords",)),
            ],
            allowed_effects=("READ_LOCAL",),
            call_counts=(2,),
        ),
        gate=Gate(model=GateModel(bias=-6), threshold=0.5),
        manifest=MANIFEST,
        compatibility_key=MANIFEST.compatibility_key(),
        lifecycle=Lifecycle.ACTIVE,
        prologue=prologue,
    )


class _Executor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, tool: str, arguments: dict) -> dict:
        self.calls.append((tool, dict(arguments)))
        if tool == "supervisor.show_profile":
            return {"name": "Ada", "section": arguments.get("section")}
        if tool == "supervisor.show_account_passwords":
            return {"amazon": "pw"}
        raise AssertionError(f"the region must never issue {tool}")


def _dispatch(artifact: Artifact, *, committed, already_observed=None, context=None):
    registry = Registry(name="prologue")
    registry.add(artifact)
    dispatcher = Dispatcher(registry=registry, catalog=CATALOG, mode=DispatchMode.LIVE)
    executor = _Executor()
    if already_observed is None:
        already_observed = tuple(dict.fromkeys(c.tool for c in committed or ()))
    decision = dispatcher.decide(
        compatibility_key=MANIFEST.compatibility_key(),
        partition={},
        entry_state={"task_id": "t1"},
        context=context or {"model": "model"},
        executor=executor,
        already_observed=already_observed,
        committed_calls=committed,
    )
    return decision, executor, dispatcher


# ---------------------------------------------------------------------------
# no prologue declared: byte-identical to the strict position-0 rule
# ---------------------------------------------------------------------------


def test_without_a_prologue_any_committed_call_is_still_a_non_prefix_boundary() -> None:
    decision, executor, dispatcher = _dispatch(_artifact(None), committed=[DOCS_CALL])
    assert decision.outcome is DispatchOutcome.BASELINE
    assert decision.reasons == ("non_prefix_boundary",)
    assert executor.calls == []
    assert dispatcher.telemetry.guard_misses == {"non_prefix_boundary": 1}

    decision, executor, _ = _dispatch(_artifact(None), committed=[])
    assert decision.outcome is DispatchOutcome.COMPACTED
    assert [tool for tool, _ in executor.calls] == [
        "supervisor.show_profile",
        "supervisor.show_account_passwords",
    ]
    assert decision.prologue_live_ins == {}
    assert "prologue" not in _artifact(None).to_dict()


# ---------------------------------------------------------------------------
# acceptance test 2: exact prologue dispatches, nothing is replayed
# ---------------------------------------------------------------------------


def test_exact_prologue_binds_live_ins_and_replays_nothing() -> None:
    baseline_decision, _, _ = _dispatch(_artifact(None), committed=[])
    decision, executor, dispatcher = _dispatch(_artifact(_prologue()), committed=[DOCS_CALL])

    assert decision.outcome is DispatchOutcome.COMPACTED
    assert decision.compacted
    # the committed documentation read is not re-issued
    assert [tool for tool, _ in executor.calls] == [
        "supervisor.show_profile",
        "supervisor.show_account_passwords",
    ]
    # the region's call count is unchanged relative to position-0 dispatch
    assert len(decision.calls) == len(baseline_decision.calls) == 2
    assert decision.effects == ("READ_LOCAL", "READ_LOCAL")
    # the prologue output is an explicit live-in the region actually consumed
    assert decision.prologue_live_ins == {"docs": DOCS}
    assert decision.prologue_provenance == {"docs": "api_docs.show_api_descriptions"}
    assert decision.calls[0] == ("supervisor.show_profile", {"section": "basic"})
    assert decision.outputs["profile"]["section"] == "basic"
    assert dispatcher.telemetry.compacted == 1
    assert dispatcher.telemetry.guard_misses == {}


def test_prologue_artifact_never_runs_at_position_zero_or_without_a_record() -> None:
    decision, executor, _ = _dispatch(_artifact(_prologue()), committed=[])
    assert decision.outcome is DispatchOutcome.BASELINE
    assert decision.reasons == ("prologue_mismatch:missing_call@0",)
    assert executor.calls == []

    decision, executor, _ = _dispatch(_artifact(_prologue()), committed=None, already_observed=())
    assert decision.outcome is DispatchOutcome.BASELINE
    assert decision.reasons == ("prologue_unverifiable:no_committed_record",)
    assert executor.calls == []


# ---------------------------------------------------------------------------
# acceptance test 1: every deviation returns the unchanged baseline
# ---------------------------------------------------------------------------


TWO_CALL_PROLOGUE = _prologue(
    PrologueCall("docs", "api_docs.show_api_descriptions", {"app_name": Const("supervisor")}),
    PrologueCall("task", "supervisor.show_active_task", {}),
)


@pytest.mark.parametrize(
    "label, prologue, committed, context, expected",
    [
        (
            "different call",
            _prologue(),
            [TASK_CALL],
            None,
            "prologue_mismatch:tool@0:supervisor.show_active_task",
        ),
        ("extra call", _prologue(), [DOCS_CALL, TASK_CALL], None, "prologue_mismatch:extra_call@1"),
        ("duplicated call", _prologue(), [DOCS_CALL, DOCS_CALL], None, "prologue_mismatch:extra_call@1"),
        ("order change", TWO_CALL_PROLOGUE, [TASK_CALL, DOCS_CALL], None, "prologue_mismatch:order"),
        (
            "argument mismatch",
            _prologue(),
            [CommittedCall("api_docs.show_api_descriptions", {"app_name": "amazon"}, DOCS)],
            None,
            "prologue_mismatch:args@0",
        ),
        (
            "failed committed call",
            _prologue(),
            [CommittedCall("api_docs.show_api_descriptions", {"app_name": "supervisor"}, None, "error")],
            None,
            "prologue_mismatch:status@0:error",
        ),
        ("manifest mismatch", _prologue(), [DOCS_CALL], {"model": "other-model"}, "manifest:model"),
        (
            "undeclared prologue tool",
            _prologue(PrologueCall("doc", "api_docs.show_api_doc", {})),
            [CommittedCall("api_docs.show_api_doc", {}, {})],
            None,
            "prologue_undeclared_tool:api_docs.show_api_doc",
        ),
        (
            "unknown effect",
            _prologue(PrologueCall("u", "api_docs.unknown", {})),
            [CommittedCall("api_docs.unknown", {}, {})],
            None,
            "prologue_unknown_effect:api_docs.unknown",
        ),
        (
            "write effect",
            _prologue(PrologueCall("login", "amazon.login", {})),
            [CommittedCall("amazon.login", {}, {"token": "t"})],
            None,
            "prologue_effect:amazon.login:WRITE_REVERSIBLE",
        ),
        (
            "missing speculatable/replayable",
            _prologue(PrologueCall("apps", "api_docs.show_app_descriptions", {})),
            [CommittedCall("api_docs.show_app_descriptions", {}, {})],
            None,
            "prologue_capability:api_docs.show_app_descriptions:speculatable+replayable",
        ),
    ],
)
def test_any_prologue_deviation_returns_the_unchanged_baseline(label, prologue, committed, context, expected) -> None:
    program = _program(section_from_prologue=False)
    decision, executor, dispatcher = _dispatch(
        _artifact(prologue, program), committed=committed, context=context
    )
    assert decision.outcome is DispatchOutcome.BASELINE, label
    assert not decision.compacted, label
    assert decision.reasons[0] == expected, label
    assert executor.calls == [], label
    assert decision.calls == [], label
    assert decision.prologue_live_ins == {}, label
    assert dispatcher.telemetry.compacted == 0, label


def test_unrecorded_observation_is_a_mismatch_even_when_the_record_matches() -> None:
    # the host says it observed a tool the committed record does not contain: the
    # record does not describe this episode, so it cannot license dispatch
    decision, executor, _ = _dispatch(
        _artifact(_prologue()),
        committed=[DOCS_CALL],
        already_observed=("api_docs.show_api_descriptions", "amazon.login"),
    )
    assert decision.outcome is DispatchOutcome.BASELINE
    assert decision.reasons == ("prologue_mismatch:unrecorded_observation:amazon.login",)
    assert executor.calls == []


# ---------------------------------------------------------------------------
# acceptance test 3: grounding is recomputed over the extended live-in set
# ---------------------------------------------------------------------------


def test_ungrounded_slot_retires_the_region_before_any_call() -> None:
    # the region reads ``manual.default_section`` but the prologue declares ``docs``
    program = _program(section_source="manual.default_section")
    decision, executor, dispatcher = _dispatch(_artifact(_prologue(), program), committed=[DOCS_CALL])
    assert decision.outcome is DispatchOutcome.BASELINE
    assert decision.reasons == ("prologue_ungrounded_slot:profile.section",)
    assert executor.calls == []
    assert dispatcher.telemetry.guard_misses == {"prologue_ungrounded_slot": 1}


def test_ambiguous_live_in_retires_the_region() -> None:
    # the prologue var collides with a region step var: two producers for one name
    prologue = _prologue(PrologueCall("profile", "api_docs.show_api_descriptions", {"app_name": Const("supervisor")}))
    program = _program(section_source="profile.default_section")
    decision, executor, _ = _dispatch(_artifact(prologue, program), committed=[DOCS_CALL])
    assert decision.outcome is DispatchOutcome.BASELINE
    assert decision.reasons[0] == "prologue_ambiguous_live_in:profile"
    assert executor.calls == []

    # two prologue calls bound to the same var are ambiguous as well
    duplicated = _prologue(
        PrologueCall("docs", "api_docs.show_api_descriptions", {"app_name": Const("supervisor")}),
        PrologueCall("docs", "supervisor.show_active_task", {}),
    )
    decision, executor, _ = _dispatch(_artifact(duplicated), committed=[DOCS_CALL, TASK_CALL])
    assert decision.outcome is DispatchOutcome.BASELINE
    assert decision.reasons[0] == "prologue_ambiguous_live_in:docs"
    assert executor.calls == []


def test_grounding_closure_accepts_entry_state_prologue_and_earlier_steps_only() -> None:
    assert prologue_grounding_reasons(_program(section_source="docs.default_section"), _prologue()) == []
    assert prologue_grounding_reasons(_program(section_source="z.task_id"), _prologue()) == []
    later = Program(
        theta=("task_id",),
        steps=[
            CallStep(var="profile", tool="supervisor.show_profile", args={"section": Expr("passwords.x", ())}),
            CallStep(var="passwords", tool="supervisor.show_account_passwords", args={}),
        ],
        outputs={"profile": Expr("profile", ()), "extra": Expr("nowhere", ())},
    )
    assert prologue_grounding_reasons(later, _prologue()) == [
        "prologue_ungrounded_slot:profile.section",
        "prologue_ungrounded_slot:return.extra",
    ]


def test_prologue_bindings_may_only_read_the_entry_state() -> None:
    prologue = _prologue(PrologueCall("docs", "api_docs.show_api_descriptions", {"app_name": Expr("earlier.app", ())}))
    match = match_prologue(_program(), prologue, CATALOG, {"task_id": "t1"}, [DOCS_CALL])
    assert match.reasons == ("invalid_prologue:binding:docs.app_name",)

    # a region tool may not double as a prologue tool: it would be issued twice
    prologue = _prologue(PrologueCall("p", "supervisor.show_profile", {}))
    match = match_prologue(_program(section_from_prologue=False), prologue, CATALOG, {}, [])
    assert match.reasons == ("invalid_prologue:tool_in_region:supervisor.show_profile",)


# ---------------------------------------------------------------------------
# the same contract on the manual pre-model path and the SDK adapter
# ---------------------------------------------------------------------------


def _manual_runner(prologue: Prologue | None) -> ManualPreModelRunner:
    program = synthesize_composite(
        _program(section_from_prologue=prologue is not None),
        CATALOG,
        name="supervisor_entry",
        projection={"name": "tool:supervisor.show_profile::name"},
        continuation_compatibility_key="continuation-v1",
    )
    plan = ManualPreModelPlan(
        name="manual-prologue",
        program=program,
        source_compatibility_key=MANIFEST.compatibility_key(),
        guard=HardGuard(allowed_effects=("READ_LOCAL",)),
        verifier=Verifier(
            clauses=[
                OutputClause("profile", "dict", provenance=("supervisor.show_profile",)),
                OutputClause("passwords", "dict", provenance=("supervisor.show_account_passwords",)),
            ],
            allowed_effects=("READ_LOCAL",),
            call_counts=(2,),
        ),
        prologue=prologue,
    )
    return ManualPreModelRunner(plan, CATALOG, MANIFEST)


def test_manual_plan_applies_the_same_prologue_contract() -> None:
    plain = _manual_runner(None)
    assert "prologue" not in plain.plan.to_dict()
    executor = _Executor()
    rejected = plain.execute_pre_model(
        {"task_id": "t1"},
        executor=executor,
        already_observed=("api_docs.show_api_descriptions",),
        committed_calls=[DOCS_CALL],
        continuation_compatibility_key="continuation-v1",
    )
    assert not rejected.compacted
    assert rejected.record["reasons"] == ["non_prefix_boundary"]
    assert executor.calls == []

    runner = _manual_runner(_prologue())
    executor = _Executor()
    accepted = runner.execute_pre_model(
        {"task_id": "t1"},
        executor=executor,
        already_observed=("api_docs.show_api_descriptions",),
        committed_calls=[DOCS_CALL],
        continuation_compatibility_key="continuation-v1",
    )
    assert accepted.compacted
    assert accepted.record["n_calls"] == 2
    assert [tool for tool, _ in executor.calls] == [
        "supervisor.show_profile",
        "supervisor.show_account_passwords",
    ]
    assert executor.calls[0][1] == {"section": "basic"}

    executor = _Executor()
    mismatch = runner.execute_pre_model(
        {"task_id": "t1"},
        executor=executor,
        already_observed=("api_docs.show_api_descriptions", "supervisor.show_active_task"),
        committed_calls=[DOCS_CALL, TASK_CALL],
        continuation_compatibility_key="continuation-v1",
    )
    assert not mismatch.compacted
    assert mismatch.record["reasons"] == ["prologue_mismatch:extra_call@1"]
    assert executor.calls == []

    executor = _Executor()
    position_zero = runner.execute_pre_model(
        {"task_id": "t1"},
        executor=executor,
        committed_calls=[],
        continuation_compatibility_key="continuation-v1",
    )
    assert not position_zero.compacted
    assert position_zero.record["reasons"] == ["prologue_mismatch:missing_call@0"]
    assert executor.calls == []


def test_sdk_history_yields_the_ordered_committed_record() -> None:
    history = [
        {"role": "user", "content": "start"},
        {"type": "function_call", "name": "api_docs.show_api_descriptions", "call_id": "c1",
         "arguments": json.dumps({"app_name": "supervisor"})},
        {"type": "function_call_output", "call_id": "c1", "output": json.dumps(DOCS)},
        {"type": "function_call", "name": "api_docs.show_api_descriptions", "call_id": "c2",
         "arguments": json.dumps({"app_name": "supervisor"})},
        {"type": "function_call", "name": "supervisor.show_active_task", "call_id": "c3", "arguments": "{}"},
    ]
    committed = _committed_calls(history)
    assert committed is not None
    # duplicates are kept in order; an unanswered call is pending, never ok
    assert [(c.tool, c.status) for c in committed] == [
        ("api_docs.show_api_descriptions", "ok"),
        ("api_docs.show_api_descriptions", "pending"),
        ("supervisor.show_active_task", "pending"),
    ]
    assert committed[0].args == {"app_name": "supervisor"}
    assert committed[0].result == DOCS
    assert _committed_calls("plain prompt") is None
    assert _committed_calls([{"role": "user", "content": "hello"}]) == ()

    # the model adapter's plan seeds the live-in and emits only region calls
    plan = ArtifactPlan(
        _artifact(_prologue()),
        {"task_id": "t1"},
        live_ins={"docs": DOCS},
        live_in_provenance={"docs": "api_docs.show_api_descriptions"},
    )
    assert plan.next_call() == ("supervisor.show_profile", {"section": "basic"}, 0)
    assert plan.calls == []


def test_prologue_survives_artifact_serialization_and_signing() -> None:
    art = _artifact(_prologue())
    art.sign(b"secret")
    again = Artifact.from_dict(json.loads(json.dumps(art.to_dict(), default=str)))
    assert again.prologue is not None
    assert again.prologue.tools == ("api_docs.show_api_descriptions",)
    assert again.prologue.calls[0].args["app_name"].evaluate({}) == "supervisor"
    assert again.verify_signature(b"secret")
    assert "committed api_docs.show_api_descriptions(app_name = Const('supervisor'))" in again.explain()


# ---------------------------------------------------------------------------
# acceptance test 4: the archived suffix-dispatch pilot returns the baseline
# ---------------------------------------------------------------------------


def _pilot_catalog() -> EffectCatalog:
    # identical to paper/scripts/github_live_study.py::make_catalog; the digest is
    # asserted against the archived manifest pin below so the pins are exercised
    return EffectCatalog.from_dict(
        {
            "version": 1,
            "name": "github-issues-pinned-local-reads",
            "tools": {
                name: {
                    "effect": "READ_LOCAL",
                    "capabilities": ["speculatable", "replayable", "cacheable"],
                    "key": ["issue_number"],
                    "resource": "hf-github-issues-snapshot",
                    "notes": "Deterministic read over the pinned Apache-2.0 public snapshot",
                }
                for name in ("issue_get_record", "issue_get_labels", "issue_get_comments")
            },
        }
    )


def _pilot_sequences() -> set[tuple[str, ...]]:
    payload = json.loads((PILOT / "results.json").read_text())
    return {
        tuple(row["tool_sequence"])
        for row in payload["results"]
        if row["condition"] == "compiled"
    }


def _pilot_committed(sequence: tuple[str, ...], issue_number: int) -> list[CommittedCall]:
    out = []
    for tool in sequence:
        args = {"issue_number": issue_number}
        if tool == "issue_get_comments":
            args["limit"] = 3
        out.append(CommittedCall(tool, args, {"source_revision": "e344be7b84d199661a9956036991e1fc25715a47", "names": []}))
    return out


@pytest.mark.skipif(not (PILOT / "registry" / "registry.json").is_file(), reason="archived pilot not present")
def test_archived_suffix_dispatch_pilot_returns_the_baseline() -> None:
    registry = Registry.load(PILOT / "registry")
    artifact = registry.artifacts[0]
    catalog = _pilot_catalog()
    assert catalog.catalog_version == artifact.guard.manifest_pins["effect_catalog_version"]
    assert artifact.program is not None and artifact.program.tools == ("issue_get_labels", "issue_get_comments")
    assert artifact.prologue is None
    context = dict(artifact.guard.manifest_pins)
    context["day"] = "2023-12-08"
    entry_state = {"issue_number": 2108}
    sequences = _pilot_sequences()
    # the archived fault: the region ran first, so the record read was reordered
    # after it (29/40 runs) or the region was duplicated (4/40 runs)
    assert ("issue_get_labels", "issue_get_comments", "issue_get_record") in sequences
    assert (
        "issue_get_labels", "issue_get_comments", "issue_get_record", "issue_get_labels", "issue_get_comments",
    ) in sequences

    def decide(art: Artifact, committed: list[CommittedCall]):
        reg = Registry(name="pilot")
        reg.add(art)
        dispatcher = Dispatcher(registry=reg, catalog=catalog, mode=DispatchMode.LIVE)
        issued: list[str] = []

        def execute(tool: str, arguments: dict) -> dict:
            issued.append(tool)
            return {"source_revision": "e344be7b84d199661a9956036991e1fc25715a47", "names": []}

        decision = dispatcher.decide(
            compatibility_key=art.compatibility_key,
            partition={},
            entry_state=entry_state,
            context=context,
            executor=execute,
            already_observed=tuple(dict.fromkeys(c.tool for c in committed)),
            committed_calls=committed,
        )
        return decision, issued

    # (a) as archived, without a prologue: the suffix region still dispatches at
    # position 0 -- which is the pilot's fault -- only because nothing precedes it;
    # at every archived boundary with a committed call it is a non-prefix boundary
    for sequence in sequences:
        for cut in range(1, len(sequence) + 1):
            decision, issued = decide(artifact, _pilot_committed(sequence[:cut], 2108))
            assert decision.outcome is DispatchOutcome.BASELINE, (sequence, cut)
            assert decision.reasons == ("non_prefix_boundary",), (sequence, cut)
            assert issued == []

    # (b) with the record read declared as the region's prologue, position 0 is
    # closed to the suffix region and every archived reordered or duplicated
    # sequence is a mismatch; only the exact baseline order dispatches, and the
    # record read is never replayed
    with_prologue = Artifact.from_dict(artifact.to_dict())
    with_prologue.prologue = Prologue(
        calls=(PrologueCall("record", "issue_get_record", {"issue_number": Expr("z.issue_number", ())}),)
    )
    decision, issued = decide(with_prologue, [])
    assert decision.outcome is DispatchOutcome.BASELINE
    assert decision.reasons == ("prologue_mismatch:missing_call@0",)
    assert issued == []
    for sequence in sequences:
        for cut in range(1, len(sequence) + 1):
            prefix = sequence[:cut]
            decision, issued = decide(with_prologue, _pilot_committed(prefix, 2108))
            if prefix == ("issue_get_record",):
                assert decision.outcome is DispatchOutcome.COMPACTED
                assert issued == ["issue_get_labels", "issue_get_comments"]
                assert decision.calls[1] == ("issue_get_comments", {"issue_number": 2108, "limit": 3})
                continue
            assert decision.outcome is DispatchOutcome.BASELINE, (sequence, cut)
            assert decision.reasons[0].startswith("prologue_mismatch:"), (sequence, cut)
            assert issued == [], (sequence, cut)
    # a record read for a different issue is not the prologue either
    decision, issued = decide(with_prologue, _pilot_committed(("issue_get_record",), 2109))
    assert decision.reasons == ("prologue_mismatch:args@0",)
    assert issued == []
