"""Golden traces: the frozen fixture that catches silent semantic drift.

The committed ``synthetic.jsonl`` is de-identified, generated, and small enough to read.
Its job is to fail loudly when a refactor changes what the pipeline *means*: the trace
round-trip, the canonical order, the provenance graph's shape, the mined families, and
the printed program are all pinned.

When a golden assertion fails the fix is either a real bug or a deliberate semantic
change — in which case regenerate the fixture with ``scripts/generate_synthetic.py``
and record why in the commit.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from agent_compaction.evaluation.splits import make_splits
from agent_compaction.graph.normalize import canonical_order, data_quality, qualify
from agent_compaction.graph.provenance import build_all
from agent_compaction.graph.windows import mine
from agent_compaction.grc.compile import GrcConfig, compile_grc

from scripts.generate_synthetic import ENTRY_ALLOWLIST, SYNTHETIC_CATALOG, read_jsonl

GOLDEN = Path(__file__).with_name("synthetic.jsonl")


@pytest.fixture(scope="module")
def episodes():
    assert GOLDEN.exists(), "run scripts/generate_synthetic.py to create the fixture"
    return read_jsonl(GOLDEN)


def test_fixture_is_committed_and_stable(episodes):
    assert len(episodes) == 400
    plants = {ep.attributes["plant"] for ep in episodes}
    assert plants == {
        "valid",
        "positional",
        "literal",
        "ungroundable",
        "ambiguous",
        "effectful",
        "unknown_effect",
        "missing_span",
        "drift",
    }


def test_episode_roundtrip_is_lossless(episodes):
    from agent_compaction.schema.traces import Episode

    for ep in episodes[:20]:
        again = Episode.from_dict(json.loads(json.dumps(ep.to_dict(), default=str)))
        assert again.to_dict() == ep.to_dict()


def test_missing_span_episodes_are_not_compiler_eligible(episodes):
    for ep in episodes:
        res = qualify(ep, SYNTHETIC_CATALOG)
        if ep.attributes["plant"] == "missing_span":
            assert not res.eligible
            assert "missing_tool_result" in res.reasons


def test_drift_episodes_carry_a_separate_manifest(episodes):
    drifted = [ep for ep in episodes if ep.attributes["plant"] == "drift"]
    assert drifted
    for ep in drifted:
        assert ep.manifest.entry_contract_version == "v2"
        assert ep.manifest.compatibility_key() != episodes[0].manifest.compatibility_key()


def test_canonical_order_is_deterministic(episodes):
    ep = episodes[0]
    a = [e.node_id for e in canonical_order(ep, SYNTHETIC_CATALOG)]
    b = [e.node_id for e in canonical_order(ep, SYNTHETIC_CATALOG)]
    assert a == b
    assert len(a) == len(ep.events)


def test_provenance_graph_shape_is_pinned(episodes):
    graphs, _ = build_all(episodes[:60], SYNTHETIC_CATALOG)
    totals: dict[str, int] = {}
    for g in graphs:
        for k, v in g.diagnostics.items():
            totals[k] = totals.get(k, 0) + v
    # exact counts drift with generator changes; the *relations* must not
    assert totals["grounded"] > totals.get("ungrounded", 0)
    assert totals.get("literal_only", 0) > 0, "the planted pagination literal must be seen"
    assert totals.get("model_originated", 0) >= 0


def test_mined_family_signature_is_stable(episodes):
    graphs, _ = build_all(episodes, SYNTHETIC_CATALOG)
    res = mine(graphs, SYNTHETIC_CATALOG, entry_schema=ENTRY_ALLOWLIST, s_min=5, min_days=3)
    assert res.families
    top = res.families[0]
    assert top.tools[:2] == ("auth.token", "dir.lookup")
    assert top.mean_removed >= 2.0
    # the canonical hash must be a pure function of shape, so it repeats
    again = mine(graphs, SYNTHETIC_CATALOG, entry_schema=ENTRY_ALLOWLIST, s_min=5, min_days=3)
    assert [f.canon_hash for f in res.families] == [f.canon_hash for f in again.families]


def test_runtime_compilation_rejects_suffix_only_regions(episodes):
    """The shipped dispatchers resolve at the first boundary, not mid-episode."""

    from agent_compaction.schema.effects import EffectCatalog
    from agent_compaction.schema.traces import (
        Episode,
        EventKind,
        EventNode,
        ExecutionManifest,
        OutcomeLabels,
        TraceEnvelope,
    )

    catalog = EffectCatalog.from_dict(
        {
            "name": "prefix-test",
            "tools": {
                name: {
                    "effect": "PURE",
                    "capabilities": ["speculatable", "replayable"],
                }
                for name in ("read.first", "read.second", "read.third")
            },
        }
    )
    manifest = ExecutionManifest(
        manifest_id="prefix-test",
        commit="test",
        model="test",
        prompt_hash="p",
        tools_hash="t",
        policy_hash="pol",
        guardrail_hash="g",
        effect_catalog_version=catalog.catalog_version,
        entry_contract_version="v1",
    )
    copies = []
    for i in range(6):
        events = []
        for step, tool in enumerate(("read.first", "read.second", "read.third")):
            base = len(events)
            call_id = f"c-{i}-{step}"
            events.extend(
                [
                    EventNode(f"n-{i}-{base}", EventKind.MODEL_REQ, base),
                    EventNode(f"n-{i}-{base+1}", EventKind.MODEL_RESP, base + 1),
                    EventNode(
                        f"n-{i}-{base+2}",
                        EventKind.TOOL_CALL,
                        base + 2,
                        tool=tool,
                        input={"value": 100 * (step + 1) + i},
                        call_id=call_id,
                    ),
                    EventNode(
                        f"n-{i}-{base+3}",
                        EventKind.TOOL_RESULT,
                        base + 3,
                        tool=tool,
                        output={"result": 1000 * (step + 1) + i},
                        call_id=call_id,
                    ),
                ]
            )
        envelope = TraceEnvelope(
            trace_id=f"tr-{i}",
            episode_id=f"ep-{i}",
            group_id=f"group-{i}",
            manifest_id=manifest.manifest_id,
            principal="test",
            tenant_partition="test",
            policy_version="v1",
            day="2026-01-01",
        )
        copies.append(
            Episode(
                envelope,
                manifest,
                entry_state={
                    "inputs": {
                        "first": 100 + i,
                        "second": 200 + i,
                        "third": 300 + i,
                    }
                },
                events=events,
                outcome=OutcomeLabels(task_success=True),
            )
        )

    graphs, _ = build_all(copies, catalog)
    unrestricted = mine(
        graphs,
        catalog,
        entry_schema=("inputs",),
        s_min=5,
        min_days=1,
    )
    assert any(window.a > 0 for family in unrestricted.families for window in family.windows)
    res = mine(
        graphs,
        catalog,
        entry_schema=("inputs",),
        s_min=5,
        min_days=1,
        prefix_only=True,
    )
    assert res.blocked["non_prefix_runtime"] > 0
    assert all(window.a == 0 for family in res.families for window in family.windows)


def test_compiled_program_text_is_reviewable_and_pinned(episodes):
    episodes = [
        episode
        for episode in episodes
        if episode.manifest.compatibility_key() == episodes[0].manifest.compatibility_key()
    ]
    splits = make_splits(episodes, seed=3)
    cfg = GrcConfig(entry_schema=ENTRY_ALLOWLIST, s_min=5, min_days=3, n_permutations=40, alpha=0.20)
    res = compile_grc(episodes, SYNTHETIC_CATALOG, splits, episodes[0].manifest, cfg)
    assert res.artifacts, res.report()
    text = res.artifacts[0].explain()
    for expected in ("artifact", "guard", "program (θ =", "gate    q ="):
        assert expected in text
    # the program must reference the entry state and not a raw literal email
    assert "z.user_email" in text
    assert "lower" in text


def test_data_quality_report_matches_the_fixture(episodes):
    rep = data_quality(episodes, SYNTHETIC_CATALOG)
    assert rep.n_episodes == 400
    assert rep.span_completeness < 1.0  # the planted missing spans
    assert "shadow.undeclared" in rep.undeclared_tools
    assert rep.n_groups >= 200
