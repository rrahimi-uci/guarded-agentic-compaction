#!/usr/bin/env python3
"""Pin the "What the compiler decided without human input" table to retained evidence.

``validate_compiler_decisions()`` returns a list of ``(passed, message)`` pairs, the same
information ``validate_artifacts.ok(condition, message)`` records.  To register it as a family in
``validate_artifacts.py`` (the integrator does this; this file does not edit that one)::

    from validate_compiler_decisions import validate_compiler_decisions

    def validate_compiler_decisions_family() -> None:
        for passed, message in validate_compiler_decisions():
            ok(passed, message)

    FAMILIES["compiler_decisions"] = validate_compiler_decisions_family

The checks (a) regenerate the table from the retained result files into a scratch directory and
require the committed ``paper/iclr/tables/compiler_decisions.tex`` to be byte-identical, (b) pin
every number the table carries to the files named in ``flip-plans.md`` A.4 / task 2.3, and (c)
reject the editorial defects the reviewers raised (the old funnel's ``p/a/w`` and ``slots``).
No network or provider call is made and nothing committed is rewritten.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"
COMMITTED = PAPER / "iclr" / "tables" / "compiler_decisions.tex"
SCRIPT = PAPER / "scripts" / "iclr_revision_statistics.py"

Result = tuple[bool, str]


def _load_statistics() -> Any:
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("iclr_revision_statistics", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def validate_compiler_decisions() -> list[Result]:
    results: list[Result] = []

    def ok(condition: bool, message: str) -> None:
        results.append((bool(condition), f"decisions: {message}"))

    try:
        stats = _load_statistics()
        rows = stats.build_decisions()
    except Exception as error:  # a missing or changed retained file must fail closed, not crash the run
        return [(False, f"decisions: rows build from retained files ({type(error).__name__}: {error})")]
    by_id = {row["id"]: row for row in rows}
    facts = {row["id"]: row["facts"] for row in rows}

    # (a) structure and regeneration
    ok(len(rows) == 12 and len(by_id) == 12, "twelve rows, none duplicated")
    ok(all(all(row[k].strip() for k in ("saw", "decided", "why", "human")) for row in rows), "every row fills all four columns")
    ok(all(row["sources"] and all((PAPER / "results" / s).exists() for s in row["sources"]) for row in rows),
       "every row names retained source files and each exists")
    committed = COMMITTED.read_text(encoding="utf-8") if COMMITTED.exists() else ""
    with tempfile.TemporaryDirectory() as scratch:
        saved = stats.TABLES
        stats.TABLES = Path(scratch)
        try:
            stats.cmd_decisions()
            fresh = (Path(scratch) / "compiler_decisions.tex").read_text(encoding="utf-8")
        finally:
            stats.TABLES = saved
    ok(fresh == committed, "compiler_decisions.tex regenerates byte-identically from the retained files")
    ok("decisions" in stats.COMMANDS, "the decisions sub-command is registered (and so runs under `all`)")

    # (b) the numbers the table carries
    for fam in ("issue_type", "pr_outcome", "backlog_attention"):
        f = facts[fam]
        ok(f["gate_n"] == 92 and f["gate_violations"] == 0 and abs(f["gate_upper"] - 0.0498089) < 1e-6
           and f["discovery_traces"] == 132, f"{fam}: admitted at 92/0 (bound 0.0498) from 132 discovery traces")
        h = f["held_out"]
        ok(h["compiled"]["exact"] == 30 and h["manual"]["exact"] == 30 and h["compiled"]["n"] == 30 == h["manual"]["n"],
           f"{fam}: held-out 30/30 for the compiled and the hand-written arm")
    ok(len(facts["issue_type"]["admitted_reads"]) == 2 and len(facts["issue_type"]["refused_tools"]) == 3
       and facts["issue_type"]["refused_reason"].startswith("ungroundable_slot:issue_get_comments.limit"),
       "issue_type: two of three reads admitted, the third refused as an ungroundable slot (limit)")
    ok(len(facts["pr_outcome"]["admitted_reads"]) == 3 and len(facts["backlog_attention"]["admitted_reads"]) == 3,
       "pr_outcome and backlog_attention: three-read programs admitted")

    x = facts["cross_repository"]
    ok(x["repositories"] == 5 and len(x["admitted"]) == 4 and x["retired"] == ["pytorch/pytorch"]
       and x["retired_status"] == "failed_closed", "cross-repository: four of five repositories admit, pytorch/pytorch retires")
    ok(x["held_out_exact"] == 120 and x["held_out_n"] == 120 and all(g == (92, 0, 92) for g in x["gates"].values()),
       "cross-repository: 120/120 held out, every admitted gate 92/0")
    ok(x["retired_discovery_classes"] == {"closed_unmerged": 84, "merged": 2, "open": 30},
       "cross-repository: pytorch discovery pool is 84 closed, 30 open, 2 merged")

    t = facts["time_forward"]
    ok(t["fresh_pool"] == 811 and t["discovery_traces"] == 132 and t["exact_traces"] == 131,
       "time-forward: 811 fresh PRs, 131 of 132 exact discovery traces")
    ok(t["program_identical"] and t["retained_abstained"] == 60 and t["held_out_n"] == 60
       and set(t["held_out_exact"].values()) == {60},
       "time-forward: identical program, retained artifact abstains 60/60, every arm 60/60 exact")
    ok(t["admits"] and t["certificate_attempted"] == 132 and t["certificate_violations"] == 0
       and abs(t["certificate_upper"] - 0.0173) < 5e-5, "time-forward: 132 dispatched, 0 misses, end-to-end bound 0.0173")

    for rid, stage, exact_traces, groups in (("gpt6_luna", "compilation", 113, None), ("claude_sonnet5", "calibration", 116, [91, 90])):
        s = facts[rid]
        ok(all(s["identical"].values()) and s["backlog_stage"] == stage and s["backlog_traces"] == 132
           and s["backlog_exact_traces"] == exact_traces and s["backlog_needed"] == 116,
           f"{rid}: identical programs on two families, backlog refused at {stage} ({exact_traces}/132 exact, 116 needed)")
        if groups:
            ok(s["backlog_accepted_groups"] == groups and all(b >= 0.05 for b in s["backlog_bounds"]),
               f"{rid}: backlog candidates accepted {groups[0]} and {groups[1]} of 92 groups, bounds above 0.05")

    b = facts["bird_per_question"]
    ok(b["standard_retired_dev"] == 5 and b["standard_retired_train"] == 26 and b["standard_retired_at_synthesis"] == 4
       and b["standard_card_games_support"] == 34, "BIRD per-question: retires on 5/5 dev and 26/26 train; four at synthesis, card_games at support 34/92")
    ok(b["schema_first_admitted_dev"] == 5 and b["schema_first_admitted_train"] == 21 and b["schema_first_databases"] == 31
       and b["dev_correct_compiled"] == 97 and b["dev_correct_baseline"] == 94 and b["dev_n"] == 150
       and abs(b["dev_requests_vs_warm_repeat"] - 0.449) < 5e-4,
       "BIRD schema-first: admits 26 of 31 databases; 97 vs 94 of 150 correct")
    ok(all(g == (92, 0) for g in b["schema_first_gates_dev"].values()) and b["schema_first_min_all_tables_share"] == 1.0
       and all(s.startswith('{"list_tables -> get_schema": ') for s in b["schema_first_opening_sequences"]),
       "BIRD: schema-first is the fixed list_tables -> get_schema opening reading every table, with 92/0 gates on development")

    tb = facts["trace_benchmarks"]
    ok(tb["largest_family"] == (26, 8, 15) and tb["required_groups"] == 92 and tb["outcomes"] == ["RETIRE"] * 3
       and tb["traces"] == (1415, 212, 200) and tb["replay_wrong"] == (0, 0, 0),
       "trace benchmarks: NESTFUL, API-Bank, BFCL retire at n_max 26, 8, 15 < 92 with no wrong replay")

    a = facts["appworld"]
    ok(a["admitted"] == 1 and a["retired_at_calibration"] == 4 and a["retire_bounds"] == [0.051, 0.051, 1.0, 1.0]
       and a["admitted_gate"][:2] == (92, 0) and a["gold_tasks"] == 136,
       "AppWorld: one candidate admitted at 92/0, four retired at calibration (bounds 0.051, 0.051, 1.000, 1.000), 136 tasks")
    ok(a["dispatchable_react_plan_exec"] == 1 and a["react_plan_exec_trajectories"] == 4680,
       "AppWorld: dispatchable on 1 of 4,680 ReAct and plan-and-execute trajectories")

    e = facts["bfcl_getter_that_writes"]
    ok(e["tool"] == "TravelAPI.get_flight_cost" and e["calls"] == 36 == e["mutating_calls"] and e["declared_effect"] == "WRITE_REVERSIBLE"
       and not e["declared_compilable"] and e["mutated_fields"] == ["TravelAPI._flight_cost_lookup"],
       "BFCL: get_flight_cost mutates state on 36/36 calls and is declared a write, so the effect barrier blocks it")

    # (c) editorial pins: single-column, footnotesize, labelled, plain wording
    ok("\\label{tab:compiler-decisions}" in committed and "\\footnotesize" in committed
       and "\\linewidth" in committed and "\\textwidth" not in committed, "table is footnotesize, single-column and labelled tab:compiler-decisions")
    ok(committed.startswith("% generated by paper/scripts/iclr_revision_statistics.py decisions; do not edit"),
       "table carries the generated-file header")
    ok("p/a/w" not in committed and "slots" not in committed and "n_{\\max}" not in committed,
       "no p/a/w, slots or n_max shorthand from the old funnel")
    ok(committed.count("\\\\") == 13, "one header row and twelve body rows")
    return results


def main() -> None:
    results = validate_compiler_decisions()
    for passed, message in results:
        print(f"[{'ok' if passed else 'FAIL'}] {message}")
    failed = sum(not passed for passed, _ in results)
    print(f"\n{len(results) - failed} checks passed; {failed} failed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
