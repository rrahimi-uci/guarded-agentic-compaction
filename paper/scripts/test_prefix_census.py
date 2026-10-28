"""Provider-free checks of the prefix census: adapters, catalogs, the census rule, the table.

The real measurement needs the released corpora under ``--source-root``.  These tests pin
the rules themselves on synthetic records: closed shell identities, SWE-agent action
parsing, the first-boundary/user-turn/barrier conventions of the Episode IR, the census
counting over the paper's own PATG and window mining, the sensitivity-arm flip, and the
byte-deterministic table.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from benchmarks.external import trajectories as traj  # noqa: E402
from guarded_agentic_compaction.schema.effects import EffectCatalog  # noqa: E402
from guarded_agentic_compaction.schema.traces import EventKind  # noqa: E402


def _module():
    spec = importlib.util.spec_from_file_location(
        "prefix_census", Path(__file__).with_name("prefix_census.py")
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _module()


# --- closed identities ----------------------------------------------------------


@pytest.mark.parametrize(
    "command, expected",
    [
        ("ls -la src", "shell.ls"),
        ("cat README.md", "shell.cat"),
        ("grep -rn foo .", "shell.grep"),
        ("find . -name '*.py'", "shell.find"),
        ("find . -name '*.pyc' -delete", "shell.exec"),
        ("find . -exec rm {} \\;", "shell.exec"),
        ("git status", "shell.git_status"),
        ("git ls-files", "shell.git_ls_files"),
        ("git checkout -b x", "shell.exec"),
        ("cat a | grep b", "shell.exec"),
        ("ls; rm -rf /", "shell.exec"),
        ("echo $(ls)", "shell.exec"),
        ("cd src", "shell.exec"),
        ("python -m pytest", "shell.exec"),
        ("ls\nrm x", "shell.exec"),
        ("", "shell.exec"),
    ],
)
def test_shell_identity_is_closed_and_conservative(command: str, expected: str) -> None:
    assert traj.shell_tool_identity(command) == expected


def test_sweagent_action_parsing() -> None:
    assert traj.parse_sweagent_action("Let's look.\n\n```\nopen src/a.py 42\n```") == (
        "open", {"path": "src/a.py", "line_number": 42})
    assert traj.parse_sweagent_action("```\nsearch_dir \"def foo\" src\n```") == (
        "search_dir", {"search_term": "def foo", "dir": "src"})
    assert traj.parse_sweagent_action("```\nedit 3:5\nprint(1)\nend_of_edit\n```") == (
        "edit", {"range": "3:5", "lines": 2})
    assert traj.parse_sweagent_action("```\nls -F\n```") == ("shell.ls", {"command": "ls -F"})
    assert traj.parse_sweagent_action("no action here") is None
    assert traj.parse_sweagent_action("```\nsubmit\n```") == ("submit", {})


def test_openhands_identity_qualifies_editor_subcommands() -> None:
    assert traj.openhands_tool_identity("str_replace_editor", {"command": "view", "path": "/w"}) == (
        "str_replace_editor.view", {"path": "/w"})
    assert traj.openhands_tool_identity("execute_bash", {"command": "ls /w"}) == (
        "shell.ls", {"command": "ls /w"})
    assert traj.openhands_tool_identity("execute_bash", {"command": "C-c", "is_input": "true"}) == (
        "shell.stdin", {"command": "C-c"})
    assert traj.openhands_tool_identity("think", {"thought": "hm"}) == ("think", {"thought": "hm"})


# --- catalogs -----------------------------------------------------------------------


@pytest.mark.parametrize("name", ["openhands_swe_rebench", "sweagent_nebius", "taubench"])
def test_signed_catalogs_never_admit_shell_or_unknown(name: str) -> None:
    catalog = MODULE.load_catalog(name)
    assert not any(catalog.compilable(t) for t in catalog.tools if t.startswith("shell."))
    assert not catalog.compilable("something_unlisted")
    assert not catalog.compilable("think")


def test_sensitivity_arm_flips_only_the_allowlist() -> None:
    primary = MODULE.load_catalog("openhands_swe_rebench")
    arm = MODULE.load_catalog("openhands_swe_rebench", flip_to_read=MODULE.SHELL_READ_ARM)
    for tool in MODULE.SHELL_READ_ARM:
        assert not primary.compilable(tool) and arm.compilable(tool)
    assert not arm.compilable("shell.exec") and not arm.compilable("shell.stdin")
    assert arm.compilable("str_replace_editor.view") and not arm.compilable("str_replace_editor.create")
    assert arm.catalog_version != primary.catalog_version
    with pytest.raises(SystemExit):
        MODULE.load_catalog("taubench", flip_to_read=("shell.ls",))


# --- Episode IR conventions ----------------------------------------------------------


def _record(turns: list[traj.Turn], entry: dict | None = None, group: str = "g1") -> traj.TrajectoryRecord:
    return traj.TrajectoryRecord(
        corpus="synthetic", episode_id="e1", group_id=group,
        entry_state=entry or {"inputs": {"repo": "acme/widget", "problem_statement": "crash in widget.py"}},
        turns=turns, model="m",
    )


def _manifest(catalog: EffectCatalog) -> traj.ExecutionManifest:
    return traj.census_manifest("synthetic", revision="r", catalog_version=catalog.catalog_version,
                                tools=("open", "edit"), scaffold="s", entry_contract="e")


def test_build_episode_first_boundary_user_turn_and_barrier() -> None:
    catalog = MODULE.load_catalog("sweagent_nebius")
    record = _record([
        traj.Turn(calls=[traj.Call("open", {"path": "widget.py"}, "1 x", "c0")]),
        traj.Turn(calls=[traj.Call("goto", {"line_number": 10}, "10 y", "c1")], user_text="please hurry"),
        traj.Turn(calls=[traj.Call("edit", {"range": "1:2", "lines": 1}, "ok", "c2")]),
        traj.Turn(calls=[traj.Call("open", {"path": "other.py"}, "z", "c3")]),
    ])
    episode = traj.build_episode(record, _manifest(catalog), tools=("open",),
                                 barrier=lambda tool: not catalog.compilable(tool))
    kinds = [e.kind for e in episode.events]
    assert kinds[0] is EventKind.MODEL_REQ, "the first event is the first model boundary"
    assert EventKind.HANDOFF in kinds, "a new user utterance is a barrier event"
    assert kinds.index(EventKind.HANDOFF) < [i for i, k in enumerate(kinds) if k is EventKind.MODEL_REQ][1]
    tools = [e.tool for e in episode.events if e.kind is EventKind.TOOL_CALL]
    assert tools == ["open", "goto", "edit"], "ingestion keeps the first barrier as sentinel and stops"
    assert episode.attributes["ingestion_stopped_by"] == "barrier"
    assert episode.attributes["n_calls_total"] == 4
    assert MODULE.read_only_opening_length(episode, catalog) == (1, "user_turn")


def test_build_episode_caps_at_max_calls() -> None:
    catalog = MODULE.load_catalog("sweagent_nebius")
    record = _record([traj.Turn(calls=[traj.Call("open", {"path": f"f{i}.py"}, "x", f"c{i}")]) for i in range(20)])
    episode = traj.build_episode(record, _manifest(catalog), tools=("open",), max_calls=5)
    assert episode.attributes["n_calls_ingested"] == 5
    assert episode.attributes["ingestion_stopped_by"] == "max_calls"
    assert MODULE.read_only_opening_length(episode, catalog) == (5, None)


# --- the census ----------------------------------------------------------------------


def _synthetic_corpus() -> list[traj.TrajectoryRecord]:
    """Six tasks: four open with two groundable reads, one with an ungrounded read, one with a write."""

    records = []
    for i in range(5):
        repo = f"org{i}/widget{i}"
        # Four search terms are a bounded transform of the entry state (the last word of the
        # problem statement); the fifth is model-originated.  Five distinct values keep the
        # corpus-derived groundability policy from treating the field as a constant.
        term = f"symbol{i}" if i < 4 else "mysterious_symbol_q"
        entry = {"inputs": {"repo": repo, "problem_statement": f"crash in symbol{i}"}}
        records.append(traj.TrajectoryRecord(
            corpus="synthetic", episode_id=f"ep{i}", group_id=f"task{i}", entry_state=entry, model="m",
            turns=[
                traj.Turn(calls=[traj.Call("search_dir", {"search_term": term, "dir": repo}, f"Found 1 matches for {term} in {repo}", "a")]),
                traj.Turn(calls=[traj.Call("open", {"path": f"{repo}/setup.py"}, "1 import x", "b")]),
                traj.Turn(calls=[traj.Call("edit", {"range": "1:1", "lines": 1}, "ok", "c")]),
            ],
        ))
    records.append(traj.TrajectoryRecord(
        corpus="synthetic", episode_id="wr", group_id="task5", model="m",
        entry_state={"inputs": {"repo": "org5/pkg5", "problem_statement": "bug in pkg5"}},
        turns=[traj.Turn(calls=[traj.Call("create", {"filename": "reproduce.py"}, "ok", "a")]),
               traj.Turn(calls=[traj.Call("open", {"path": "org5/pkg5/setup.py"}, "x", "b")])],
    ))
    return records


def test_census_counts_read_only_and_groundable_openings() -> None:
    catalog = MODULE.load_catalog("sweagent_nebius")
    manifest = _manifest(catalog)
    records = _synthetic_corpus()

    def episodes():
        for record in records:
            yield traj.build_episode(record, manifest, tools=("open",), barrier=lambda t: not catalog.compilable(t))

    result = MODULE.census(episodes, catalog, corpus="synthetic", arm="primary")
    assert result["traces"] == 6 and result["groups"] == 6
    assert result["read_only_opening"]["ge2"] == 5, "five openings have two reads before the write"
    assert result["groundable_opening"]["ge2"] == 4, "the model-originated search term is ungrounded"
    assert result["opening_block_reasons"] == {"ungrounded_slot": 1}
    assert list(result["ungrounded_opening_slots"]) == ["search_dir#search_term"]
    assert result["first_barrier"]["edit"] == 5 and result["first_barrier"]["create"] == 1
    assert result["families"]["top"][0]["tools"] == ["search_dir", "open"]
    assert result["families"]["n_max"] == 4 and result["families"]["at_floor_ge3"] == 1
    assert result["exact_gate"]["minimum_zero_violation_groups"] == 92
    assert result["exact_gate"]["outcome"] == "RETIRE"
    assert result["groundable_opening"]["length_among_ge2"]["median"] == 2


# --- the table ---------------------------------------------------------------------------


def _row(corpus: str, arm: str, **overrides):
    row = {
        "corpus": corpus, "arm": arm, "traces": 1234, "groups": 56,
        "read_only_opening": {"share_ge2": 0.123},
        "groundable_opening": {"share_ge2": 0.0456, "length_among_ge2": {"n": 3, "median": 2}},
        "families": {"n": 7, "at_floor_ge3": 2, "n_max": 95},
    }
    row.update(overrides)
    return row


def test_table_is_deterministic_and_marks_floor() -> None:
    results = {"exact_gate_floor": 92, "corpora": [
        _row("openhands", "primary"),
        _row("appworld_released", "primary", groundable_opening=None, families=None),
    ]}
    first = MODULE.table(results)
    assert first == MODULE.table(results)
    assert first.startswith("% generated by paper/scripts/prefix_census.py table; do not edit\n")
    assert r"OpenHands / SWE-rebench & CodeAct, FC & 1{,}234 & 56 & 12.3\% & 4.6\% & 2 & 7 / 2 & 95$^\dagger$ \\" in first
    assert r"AppWorld released & 4 archs & 1{,}234 & 56 & 12.3\% & -- & -- & -- & -- \\" in first


def test_committed_results_and_table_agree() -> None:
    if not MODULE.RESULTS_PATH.exists():
        pytest.skip("census results not generated")
    results = json.loads(MODULE.RESULTS_PATH.read_text(encoding="utf-8"))
    assert MODULE.table(results) == MODULE.TABLE_PATH.read_text(encoding="utf-8")
    for row in results["corpora"]:
        gate = row.get("exact_gate")
        if gate:
            assert gate["minimum_zero_violation_groups"] == results["exact_gate_floor"] == 92
