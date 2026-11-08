"""Unit tests for the interior-region census (synthetic episodes, no corpus needed)."""

from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from benchmarks.external import trajectories as traj  # noqa: E402
from guarded_agentic_compaction.graph.provenance import GroundabilityPolicy, build_patg  # noqa: E402
from guarded_agentic_compaction.graph.windows import BlockReason  # noqa: E402
from guarded_agentic_compaction.schema.effects import EffectCatalog  # noqa: E402


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ic = _load("interior_census")

READ = {"effect": "READ_LOCAL", "capabilities": ["speculatable", "replayable", "cacheable"], "resource": "db", "notes": "test"}
CATALOG = EffectCatalog.from_dict({
    "version": 1,
    "name": "interior-census-test",
    "tools": {
        "read_a": READ,
        "read_b": READ,
        "read_c": READ,
        "write_x": {"effect": "WRITE_REVERSIBLE", "capabilities": [], "resource": "db", "notes": "test"},
    },
})
MANIFEST = traj.census_manifest("test", revision="0", catalog_version=CATALOG.catalog_version,
                                tools=("read_a", "read_b", "read_c", "write_x"), scaffold="test", entry_contract="t")
TOOLS = ("read_a", "read_b", "read_c", "write_x")


def _episode(turns, *, episode_id="e1", group="g1"):
    record = traj.TrajectoryRecord(
        corpus="test", episode_id=episode_id, group_id=group,
        entry_state={"inputs": {"ticket": "TK-77881", "repo": "org/project"}},
        turns=turns, model="m", attributes={}, success=None,
    )
    return traj.build_episode(record, MANIFEST, tools=TOOLS, max_calls=ic.MAX_CALLS_INTERIOR, barrier=None)


def _call(tool, args, result, cid):
    return traj.Call(tool=tool, arguments=args, result=result, call_id=cid)


def _graph(episode):
    return build_patg(episode, CATALOG, GroundabilityPolicy.from_catalog(CATALOG), max_depth=2, kappa=3)


def _windows(graph, policy):
    blocked: Counter = Counter()
    wins = ic.enumerate_interior_windows(
        graph, CATALOG, entry_schema=("inputs",), policy=policy, w_min=2, w_max=12, b_min=2, blocked=blocked,
    )
    return wins, blocked


def test_keep_is_deterministic_and_k1_keeps_all():
    assert ic.keep("anything", 1)
    ids = [f"ep-{i}" for i in range(2000)]
    kept = [i for i in ids if ic.keep(i, 8)]
    assert kept == [i for i in ids if ic.keep(i, 8)]
    assert 150 < len(kept) < 350  # about one in eight


def test_entry_grounded_region_after_a_write_is_found_under_both_policies():
    episode = _episode([
        traj.Turn(calls=[_call("write_x", {"ticket": "TK-77881", "note": "triaged"}, {"ok": True}, "c0")]),
        traj.Turn(calls=[_call("read_a", {"ticket": "TK-77881"}, {"owner_id": "USR-4412", "state": "open"}, "c1")]),
        traj.Turn(calls=[_call("read_b", {"owner": "USR-4412"}, {"name": "Ada"}, "c2")]),
    ])
    graph = _graph(episode)
    frontier = ic.frontier_position(graph, CATALOG)
    assert frontier is not None and graph.order[frontier].tool == "write_x"
    for policy in ("strict", "projected"):
        wins, blocked = _windows(graph, policy)
        beyond = [w for w in wins if w.a > frontier]
        assert beyond, (policy, dict(blocked))
        best = max(beyond, key=lambda w: w.n_tool_events)
        assert best.tools() == ("read_a", "read_b")
        assert best.live_in == ("z.inputs",)
        assert best.interior_boundaries == 2


def test_prior_result_live_in_is_rejected_strictly_and_projected():
    episode = _episode([
        traj.Turn(calls=[_call("write_x", {"ticket": "TK-77881", "note": "triaged"}, {"ok": True}, "c0")]),
        traj.Turn(calls=[_call("read_c", {"ticket": "TK-77881"}, {"thread_id": "THR-990021"}, "c1")]),
        traj.Turn(calls=[_call("read_a", {"thread": "THR-990021"}, {"owner_id": "USR-4412"}, "c2")]),
        traj.Turn(calls=[_call("read_b", {"owner": "USR-4412"}, {"name": "Ada"}, "c3")]),
    ])
    graph = _graph(episode)
    frontier = ic.frontier_position(graph, CATALOG)
    read_a_boundary = max(b for b in graph.boundaries if b < next(
        p for p, e in enumerate(graph.order) if e.tool == "read_a" and e.kind.name == "TOOL_CALL"))
    strict, blocked_strict = _windows(graph, "strict")
    assert not [w for w in strict if w.a == read_a_boundary]
    assert blocked_strict[BlockReason.LIVE_IN_NOT_ENTRY] >= 1
    projected, _ = _windows(graph, "projected")
    hit = [w for w in projected if w.a == read_a_boundary and w.tools() == ("read_a", "read_b")]
    assert hit and hit[0].live_in == ("prior:read_c",)
    # the three-read window from read_c's boundary needs only the entry state
    three = [w for w in projected if w.tools() == ("read_c", "read_a", "read_b")]
    assert three and three[0].live_in == ("z.inputs",) and three[0].a > frontier


def test_all_read_opening_has_no_frontier_and_no_beyond_frontier_region():
    episode = _episode([
        traj.Turn(calls=[_call("read_a", {"ticket": "TK-77881"}, {"owner_id": "USR-4412"}, "c0")]),
        traj.Turn(calls=[_call("read_b", {"owner": "USR-4412"}, {"name": "Ada"}, "c1")]),
        traj.Turn(calls=[_call("read_c", {"ticket": "TK-77881"}, {"thread_id": "THR-1"}, "c2")]),
    ])
    graph = _graph(episode)
    assert ic.frontier_position(graph, CATALOG) is None
    wins, _ = _windows(graph, "projected")
    assert wins and all(w.a > 0 for w in wins)  # interior suffixes of the opening exist ...
    runs = ic.interior_read_only_runs(graph, CATALOG)
    assert [d for _, d in runs] == [2, 1]


def test_user_turn_is_a_barrier_for_interior_runs():
    episode = _episode([
        traj.Turn(calls=[_call("write_x", {"ticket": "TK-77881", "note": "x"}, {"ok": True}, "c0")]),
        traj.Turn(calls=[_call("read_a", {"ticket": "TK-77881"}, {"owner_id": "USR-4412"}, "c1")]),
        traj.Turn(user_text="please also check the owner", calls=[_call("read_b", {"owner": "USR-4412"}, {"name": "Ada"}, "c2")]),
    ])
    graph = _graph(episode)
    runs = dict(ic.interior_read_only_runs(graph, CATALOG))
    assert max(runs.values()) == 1
    wins, blocked = _windows(graph, "projected")
    assert not [w for w in wins if w.tools() == ("read_a", "read_b")]
    assert blocked[BlockReason.BARRIER_EVENT] >= 1


def test_table_renders_from_minimal_results(tmp_path):
    row = {
        "corpus": "taubench", "arm": "primary", "traces": 10, "groups": 5,
        "interior_read_only_runs": {"share_beyond_frontier_run_ge2": 0.5},
        "policies": {
            "strict": {"beyond_frontier_groundable_ge2": {"share": 0.1}},
            "projected": {"beyond_frontier_groundable_ge2": {"share": 0.3},
                          "families_beyond_frontier": {"n": 4, "at_floor_ge3": 1, "n_max": 95}},
        },
    }
    text = ic.table({"corpora": [row]})
    assert r"$\tau$-bench runs & 10 & 5 & 50.0\% & 10.0\% & 30.0\% & 4 / 1 & 95$^\dagger$" in text


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
