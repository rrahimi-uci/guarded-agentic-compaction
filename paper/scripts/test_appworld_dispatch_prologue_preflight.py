"""Provider-free checks of the prologue eligibility rule on synthetic released logs.

The real measurement needs the released AppWorld baseline outputs under
``$BENCHMARK_SOURCE_ROOT/appworld``. These tests pin the rule itself: BEFORE is the
retained position-0 rule, AFTER admits exactly one committed prologue with exact
arguments and nothing else, architectures are never pooled, and BEFORE must reproduce a
retained result or the script refuses to write.
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

from guarded_agentic_compaction.schema.effects import EffectCatalog  # noqa: E402


def _module():
    spec = importlib.util.spec_from_file_location(
        "appworld_dispatch_prologue_preflight",
        Path(__file__).with_name("appworld_dispatch_prologue_preflight.py"),
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


MODULE = _module()

DOCS = "/api_docs/api_descriptions"
PROFILE = "/supervisor/profile"
PASSWORDS = "/supervisor/account_passwords"
TASK = "/supervisor/active_task"


def _log(*calls: str) -> str:
    return "\n".join(json.dumps({"method": "GET", "url": url}) for url in calls) + "\n"


@pytest.fixture()
def source_root(tmp_path: Path) -> Path:
    checkout = tmp_path / "appworld"
    docs = checkout / "data" / "api_docs" / "standard"
    docs.mkdir(parents=True)
    (docs / "api_docs.json").write_text(json.dumps({
        "show_api_descriptions": {"app_name": "api_docs", "api_name": "show_api_descriptions",
                                  "path": DOCS, "method": "GET"},
        "show_api_doc": {"app_name": "api_docs", "api_name": "show_api_doc",
                         "path": "/api_docs/api_doc", "method": "GET"},
    }))
    (docs / "supervisor.json").write_text(json.dumps({
        "show_profile": {"app_name": "supervisor", "api_name": "show_profile", "path": PROFILE, "method": "GET"},
        "show_account_passwords": {"app_name": "supervisor", "api_name": "show_account_passwords",
                                   "path": PASSWORDS, "method": "GET"},
        "show_active_task": {"app_name": "supervisor", "api_name": "show_active_task", "path": TASK, "method": "GET"},
    }))
    trajectories = {
        # ReAct-like: documentation first, then the program (four shapes)
        "react_gpt4o_test_normal": {
            "exact": _log(f"{DOCS}?app_name=supervisor", PROFILE, PASSWORDS, TASK),
            "wrong_args": _log(f"{DOCS}?app_name=amazon", PROFILE, PASSWORDS),
            "two_doc_calls": _log(f"{DOCS}?app_name=supervisor", "/api_docs/api_doc?app_name=supervisor&api_name=show_profile",
                                  PROFILE, PASSWORDS),
            "reordered": _log(PROFILE, f"{DOCS}?app_name=supervisor", PASSWORDS),
            "docs_then_other": _log(f"{DOCS}?app_name=supervisor", TASK, PROFILE, PASSWORDS),
        },
        # full-code-like: the program at position 0
        "full_code_refl_gpt4o_test_normal": {
            "position0": _log(PROFILE, PASSWORDS),
            "position0_after_docs_too": _log(PROFILE, PASSWORDS, f"{DOCS}?app_name=supervisor"),
        },
    }
    for run, tasks in trajectories.items():
        for task, text in tasks.items():
            log = checkout / "experiments" / "outputs" / run / "tasks" / task / "logs" / "api_calls.jsonl"
            log.parent.mkdir(parents=True)
            log.write_text(text)
    return tmp_path


def _analyze(source_root: Path, prologue=None):
    checkout = source_root / "appworld"
    catalog = EffectCatalog.from_yaml(MODULE.CATALOG_PATH)
    return MODULE.analyze(
        checkout / "experiments" / "outputs",
        checkout / "data" / "api_docs" / "standard",
        catalog,
        prologue or MODULE.parse_prologue(MODULE.DEFAULT_PROLOGUE),
    )


def test_default_prologue_is_the_documentation_lookup_with_exact_arguments() -> None:
    assert MODULE.parse_prologue(MODULE.DEFAULT_PROLOGUE) == (
        ("get", "/api_docs/api_descriptions", {"app_name": "supervisor"}),
    )
    assert MODULE.parse_prologue(["GET /x?y=1 a=b", "post /y"]) == (
        ("get", "/x", {"a": "b"}),
        ("post", "/y", {}),
    )


def test_before_is_the_retained_rule_and_after_admits_only_the_exact_prologue(source_root: Path) -> None:
    analysis = _analyze(source_root)
    react = analysis["by_agent_family"]["react"]
    full = analysis["by_agent_family"]["full_code_refl"]

    assert (react["tasks"], react["before_eligible_at_position_0"]) == (5, 0)
    # only ``exact`` matches: wrong arguments, a second documentation call, a
    # reordered program and an interposed read are all mismatches
    assert react["after_eligible_after_exact_prologue"] == 1
    assert react["after_eligible_total"] == 1
    assert react["after_rate"] == pytest.approx(0.2)
    # the labelled diagnostics are looser and must stay out of the eligibility columns
    assert react["diagnostic_prologue_routes_any_arguments"] == 2  # exact + wrong_args
    assert react["diagnostic_documentation_prefix_then_program"] == 3  # + two_doc_calls

    assert (full["tasks"], full["before_eligible_at_position_0"]) == (2, 2)
    assert full["after_eligible_after_exact_prologue"] == 0
    assert full["after_eligible_total"] == 2

    # architectures are reported separately; there is no pooled block
    assert "pooled" not in analysis
    assert analysis["prologue"][0]["tool"] == "api_docs.show_api_descriptions"
    # the signed catalog does not declare the prologue tool today
    assert analysis["prologue_tools_declared_in_catalog"] == {"api_docs.show_api_descriptions": False}
    assert analysis["first_call_arguments_for_prologue_route"] == {
        '{"app_name": "supervisor"}': 3,
        '{"app_name": "amazon"}': 1,
    }
    assert analysis["argument_sources_in_released_logs"] == {"query": 7, "none": 16}


def test_two_call_prologue_is_matched_in_order_with_nothing_else(source_root: Path) -> None:
    prologue = MODULE.parse_prologue([
        "get /api_docs/api_descriptions app_name=supervisor",
        "get /api_docs/api_doc app_name=supervisor api_name=show_profile",
    ])
    react = _analyze(source_root, prologue)["by_agent_family"]["react"]
    assert react["after_eligible_after_exact_prologue"] == 1  # two_doc_calls only
    assert react["before_eligible_at_position_0"] == 0


def test_retained_cross_check_and_table_never_pool(source_root: Path, tmp_path: Path) -> None:
    analysis = _analyze(source_root)
    retained = tmp_path / "retained.json"
    retained.write_text(json.dumps({"by_agent_family": {
        "react": {"tasks": 5, "eligible_at_position_0": 0},
        "full_code_refl": {"tasks": 2, "eligible_at_position_0": 2},
        "ipfuncall": {"tasks": 0, "eligible_at_position_0": 0},
        "plan_exec": {"tasks": 0, "eligible_at_position_0": 0},
    }}))
    check = MODULE.cross_check_retained(analysis["by_agent_family"], retained)
    assert check["reproduced"] and check["mismatches"] == {}

    retained.write_text(json.dumps({"by_agent_family": {
        "react": {"tasks": 5, "eligible_at_position_0": 1},
        "full_code_refl": {"tasks": 2, "eligible_at_position_0": 2},
        "ipfuncall": {"tasks": 0, "eligible_at_position_0": 0},
        "plan_exec": {"tasks": 0, "eligible_at_position_0": 0},
    }}))
    check = MODULE.cross_check_retained(analysis["by_agent_family"], retained)
    assert not check["reproduced"]
    assert list(check["mismatches"]) == ["react"]

    table = MODULE.latex_table(analysis["by_agent_family"])
    assert "ReAct" in table and "Full code + reflection" in table
    assert "Pooled" not in table
    assert "& 2 & 1.000 & 2 & 1.000" in table  # full-code: before == after
    assert "& 0 & 0.000 & 1 & 0.200" in table  # react: one exact prologue admitted


def test_real_measurement_requires_the_released_outputs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["x", "--source-root", str(tmp_path), "--output", str(tmp_path / "o.json")])
    with pytest.raises(SystemExit, match="released baseline outputs are unavailable"):
        MODULE.main()
