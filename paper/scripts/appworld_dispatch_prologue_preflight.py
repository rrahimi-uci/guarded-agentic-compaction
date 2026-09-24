#!/usr/bin/env python3
"""AppWorld structural eligibility before and after a read-only prologue, per architecture.

Acceptance test 5 of ``paper/supplementary/read-only-prologue-protocol.md``: recompute the
structural dispatch eligibility of the admitted AppWorld artifact on the released baseline
trajectories with the *same* prologue definition the runtime enforces
(``guarded_agentic_compaction.runtime.prologue``), and report it per agent architecture,
never pooled.

BEFORE is the retained rule of ``appworld_dispatch_preflight.py``: the admitted program's
exact call sequence at normalized position 0. This script must reproduce the retained
per-architecture counts exactly, and refuses to write a result otherwise.

AFTER admits, in addition, a trajectory whose committed calls before the program are
*exactly* the declared prologue: same routes, same order, same query/body arguments,
nothing else, followed immediately by the admitted program. That is the runtime's
``match_prologue`` rule transcribed onto released API logs, which retain method, url and
arguments but not results or model boundaries. Two looser counts are reported as
diagnostics only, clearly labelled, so the exact-argument assumption can be checked
against the data: the same prologue with any arguments, and any prefix of
documentation-only calls followed by the program.

Assumptions this measurement makes explicit in its output:

* the prologue is the API-documentation lookup the architectures open with, by default
  ``GET /api_docs/api_descriptions?app_name=supervisor`` (``--prologue`` overrides it);
* that route resolves to ``api_docs.show_api_descriptions``, which the signed catalog
  ``benchmarks/contracts/effects/appworld.yaml`` does **not** declare today. The runtime
  would refuse such a prologue (``prologue_undeclared_tool``) until a reviewer signs the
  declaration recorded under ``assumptions.required_catalog_declaration``. This script
  does not edit the catalog and reports the tool's current declaration state.

Provider-free. Reads only the released outputs and the pinned API documentation.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import parse_qsl, urlsplit


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from guarded_agentic_compaction.schema.effects import EffectCatalog  # noqa: E402


def _retained_module():
    spec = importlib.util.spec_from_file_location(
        "appworld_dispatch_preflight", Path(__file__).with_name("appworld_dispatch_preflight.py")
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


RETAINED = _retained_module()
ADMITTED_PROGRAM = RETAINED.ADMITTED_PROGRAM
FAMILIES = RETAINED.FAMILIES
CATALOG_PATH = RETAINED.CATALOG_PATH
RETAINED_RESULT = RETAINED.DEFAULT_OUT
DEFAULT_OUT = (
    ROOT / "paper" / "results" / "external_benchmarks" / "appworld_dispatch_prologue_preflight.json"
)
DEFAULT_TABLE = ROOT / "paper" / "iclr" / "tables" / "appworld_dispatch_prologue.tex"

#: The prologue the runtime would declare: one documentation read with exact arguments.
DEFAULT_PROLOGUE = ("get /api_docs/api_descriptions app_name=supervisor",)

#: What the signed catalog would have to say for the runtime to admit the prologue tool.
REQUIRED_CATALOG_DECLARATION = {
    "api_docs.show_api_descriptions": {
        "effect": "READ_LOCAL",
        "capabilities": ["speculatable", "replayable", "cacheable"],
        "resource": "appworld_api_docs",
        "notes": (
            "Documentation lookup over the pinned api_docs fixture. Not covered by the "
            "mutation audit because no gold solution calls it; a reviewer must sign it "
            "before any prologue over it can dispatch."
        ),
    }
}

Call = tuple[str, str, dict[str, str]]  # (method, path, arguments)


# ---------------------------------------------------------------------------
# prologue definition
# ---------------------------------------------------------------------------


def parse_prologue(specs: Sequence[str]) -> tuple[Call, ...]:
    """``"get /api_docs/api_descriptions app_name=supervisor"`` -> (method, path, args)."""

    calls: list[Call] = []
    for spec in specs:
        parts = spec.split()
        if len(parts) < 2:
            raise SystemExit(f"prologue call needs '<method> <path> [k=v ...]', got {spec!r}")
        method, path = parts[0].lower(), parts[1]
        args: dict[str, str] = {}
        for pair in parts[2:]:
            if "=" not in pair:
                raise SystemExit(f"prologue argument must be k=v, got {pair!r}")
            key, value = pair.split("=", 1)
            args[key] = value
        calls.append((method, path.split("?", 1)[0], args))
    return tuple(calls)


# ---------------------------------------------------------------------------
# released trajectories, arguments retained
# ---------------------------------------------------------------------------

_BODY_KEYS = ("data", "json", "body", "payload", "params")


def _arguments(record: Mapping[str, Any]) -> tuple[dict[str, str], str]:
    """Query parameters plus any flat body the released log retains, all as strings."""

    url = str(record.get("url", ""))
    args: dict[str, str] = {k: v for k, v in parse_qsl(urlsplit(url).query, keep_blank_values=True)}
    source = "query" if args else "none"
    for key in _BODY_KEYS:
        body = record.get(key)
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                body = None
        if isinstance(body, dict) and body:
            for k, v in body.items():
                args.setdefault(str(k), v if isinstance(v, str) else json.dumps(v, sort_keys=True))
            source = f"{source}+{key}" if source != "none" else key
    return args, source


def trajectory_with_arguments(path: Path, sources: Counter[str] | None = None) -> list[Call]:
    calls: list[Call] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        args, source = _arguments(record)
        if sources is not None:
            sources[source] += 1
        calls.append(
            (str(record["method"]).lower(), str(record["url"]).split("?", 1)[0], args)
        )
    return calls


# ---------------------------------------------------------------------------
# the two rules
# ---------------------------------------------------------------------------


def _routes_only(calls: Sequence[Call]) -> tuple[tuple[str, str], ...]:
    return tuple((method, path) for method, path, _ in calls)


def eligible_before(calls: Sequence[Call]) -> bool:
    """Retained rule: the admitted program at normalized position 0."""

    return _routes_only(calls[: len(ADMITTED_PROGRAM)]) == ADMITTED_PROGRAM


def eligible_after_exact_prologue(calls: Sequence[Call], prologue: Sequence[Call]) -> bool:
    """Runtime rule: committed calls == prologue exactly, then the program immediately."""

    n = len(prologue)
    if len(calls) < n + len(ADMITTED_PROGRAM):
        return False
    head = calls[:n]
    for (method, path, args), (want_method, want_path, want_args) in zip(head, prologue):
        if method != want_method or path != want_path or dict(args) != dict(want_args):
            return False
    return _routes_only(calls[n : n + len(ADMITTED_PROGRAM)]) == ADMITTED_PROGRAM


def prologue_routes_any_arguments(calls: Sequence[Call], prologue: Sequence[Call]) -> bool:
    """Diagnostic: the prologue's routes in order with any arguments, then the program."""

    n = len(prologue)
    return _routes_only(calls[:n]) == _routes_only(prologue) and _routes_only(
        calls[n : n + len(ADMITTED_PROGRAM)]
    ) == ADMITTED_PROGRAM


def documentation_prefix_then_program(
    calls: Sequence[Call], routes: Sequence[Any], is_docs_tool
) -> bool:
    """Diagnostic: any prefix of documentation-only reads, then the program."""

    depth = 0
    for method, path, _ in calls:
        tool = RETAINED._resolve(method, path, routes)
        if tool is None or not is_docs_tool(tool):
            break
        depth += 1
    if depth == 0:
        return False
    return _routes_only(calls[depth : depth + len(ADMITTED_PROGRAM)]) == ADMITTED_PROGRAM


# ---------------------------------------------------------------------------
# analysis
# ---------------------------------------------------------------------------


def analyze(outputs: Path, api_docs: Path, catalog: EffectCatalog, prologue: Sequence[Call]) -> dict[str, Any]:
    routes = RETAINED._load_route_table(api_docs)
    prologue_tools = [RETAINED._resolve(method, path, routes) for method, path, _ in prologue]

    def is_docs_tool(tool: str) -> bool:
        return tool.split(".", 1)[0] == "api_docs"

    per_run: list[dict[str, Any]] = []
    first_call_arguments: Counter[str] = Counter()
    argument_sources: Counter[str] = Counter()
    for run in sorted(outputs.glob("*_test_*")):
        if not (run / "tasks").is_dir():
            continue
        logs = sorted(run.glob("tasks/*/logs/api_calls.jsonl"))
        if not logs:
            continue
        counts: Counter[str] = Counter()
        for log in logs:
            calls = trajectory_with_arguments(log, argument_sources)
            counts["tasks"] += 1
            if not calls:
                counts["empty_trajectory"] += 1
                continue
            method, path, args = calls[0]
            if prologue and (method, path) == (prologue[0][0], prologue[0][1]):
                first_call_arguments[json.dumps(args, sort_keys=True)] += 1
            before = eligible_before(calls)
            after_exact = (not before) and eligible_after_exact_prologue(calls, prologue)
            counts["eligible_at_position_0"] += int(before)
            counts["eligible_after_exact_prologue"] += int(after_exact)
            counts["eligible_before_or_after"] += int(before or after_exact)
            counts["diagnostic_prologue_routes_any_arguments"] += int(
                (not before) and prologue_routes_any_arguments(calls, prologue)
            )
            counts["diagnostic_documentation_prefix_then_program"] += int(
                (not before) and documentation_prefix_then_program(calls, routes, is_docs_tool)
            )
        per_run.append(
            {
                "run": run.name,
                "family": RETAINED._family_of(run.name),
                "split": "test_challenge" if "test_challenge" in run.name else "test_normal",
                **{
                    key: counts[key]
                    for key in (
                        "tasks",
                        "empty_trajectory",
                        "eligible_at_position_0",
                        "eligible_after_exact_prologue",
                        "eligible_before_or_after",
                        "diagnostic_prologue_routes_any_arguments",
                        "diagnostic_documentation_prefix_then_program",
                    )
                },
            }
        )

    def _family(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
        rows = list(rows)
        tasks = sum(row["tasks"] for row in rows)
        before = sum(row["eligible_at_position_0"] for row in rows)
        after = sum(row["eligible_after_exact_prologue"] for row in rows)
        return {
            "runs": len(rows),
            "tasks": tasks,
            "before_eligible_at_position_0": before,
            "after_eligible_after_exact_prologue": after,
            "after_eligible_total": before + after,
            "before_rate": before / tasks if tasks else None,
            "after_rate": (before + after) / tasks if tasks else None,
            "diagnostic_prologue_routes_any_arguments": sum(
                row["diagnostic_prologue_routes_any_arguments"] for row in rows
            ),
            "diagnostic_documentation_prefix_then_program": sum(
                row["diagnostic_documentation_prefix_then_program"] for row in rows
            ),
        }

    by_family = {
        family: {"label": label, **_family(r for r in per_run if r["family"] == family)}
        for family, label in FAMILIES.items()
    }
    return {
        "per_run": per_run,
        "by_agent_family": by_family,
        "prologue": [
            {"method": m, "path": p, "arguments": a, "tool": t}
            for (m, p, a), t in zip(prologue, prologue_tools)
        ],
        "prologue_tools_declared_in_catalog": {
            str(tool): (tool in catalog.tools) for tool in prologue_tools
        },
        "first_call_arguments_for_prologue_route": dict(first_call_arguments.most_common(8)),
        "argument_sources_in_released_logs": dict(argument_sources),
        "declared_routes": len(routes),
    }


def cross_check_retained(by_family: Mapping[str, Any], retained_path: Path) -> dict[str, Any]:
    """BEFORE must reproduce the retained per-architecture counts exactly."""

    retained = json.loads(retained_path.read_text())["by_agent_family"]
    mismatches = {}
    for family, row in by_family.items():
        want = retained.get(family, {})
        got = (row["tasks"], row["before_eligible_at_position_0"])
        expected = (want.get("tasks"), want.get("eligible_at_position_0"))
        if got != expected:
            mismatches[family] = {"got": got, "retained": expected}
    return {"retained": RETAINED._display(retained_path), "reproduced": not mismatches, "mismatches": mismatches}


def latex_table(by_family: Mapping[str, Any]) -> str:
    def _n(value: int) -> str:
        return f"{value:,}".replace(",", "{,}")

    lines = [
        "\\begin{tabular}{@{}lrrrrrr@{}}",
        "\\toprule",
        "Released baseline architecture & Runs & Trajectories & "
        "Before (pos.~0) & Rate & After (pos.~0 or exact prologue) & Rate \\\\",
        "\\midrule",
    ]
    for family in FAMILIES:
        row = by_family[family]
        if not row["tasks"]:
            continue
        lines.append(
            f"{row['label']:38s} & {row['runs']} & {_n(row['tasks'])} & "
            f"{_n(row['before_eligible_at_position_0'])} & {row['before_rate']:.3f} & "
            f"{_n(row['after_eligible_total'])} & {row['after_rate']:.3f} \\\\"
        )
    lines += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--prologue", action="append", default=None,
                        help="'<method> <path> [k=v ...]'; repeat for a multi-call prologue")
    parser.add_argument("--retained", type=Path, default=RETAINED_RESULT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--table", type=Path, default=DEFAULT_TABLE)
    args = parser.parse_args()

    started = time.perf_counter()
    checkout = args.source_root / "appworld"
    outputs = checkout / "experiments" / "outputs"
    api_docs = checkout / "data" / "api_docs" / "standard"
    if not outputs.is_dir():
        raise SystemExit(
            f"released baseline outputs are unavailable at {outputs}; run "
            "`appworld download experiment-outputs` in the pinned checkout first"
        )
    if not api_docs.is_dir():
        raise SystemExit(f"pinned API documentation is unavailable at {api_docs}")
    if args.output.resolve() == RETAINED_RESULT.resolve():
        raise SystemExit("refusing to overwrite the retained position-0 result")

    prologue = parse_prologue(args.prologue or list(DEFAULT_PROLOGUE))
    catalog = EffectCatalog.from_yaml(CATALOG_PATH)
    analysis = analyze(outputs, api_docs, catalog, prologue)
    if not analysis["per_run"]:
        raise SystemExit("no released baseline runs were found")
    check = cross_check_retained(analysis["by_agent_family"], args.retained) if args.retained.is_file() else None
    if check is not None and not check["reproduced"]:
        raise SystemExit(f"BEFORE does not reproduce the retained result: {check['mismatches']}")

    report = {
        "schema": "gac-appworld-dispatch-prologue-preflight/v1",
        "benchmark": "appworld",
        "package_version": RETAINED.PACKAGE_VERSION,
        "effect_catalog": {"path": RETAINED._display(CATALOG_PATH), "sha256": RETAINED._sha256(CATALOG_PATH)},
        "artifact_under_test": {
            "program": [f"{method} {path}" for method, path in ADMITTED_PROGRAM],
            "evaluated_on": "released official baseline agent trajectories, test_normal and test_challenge",
        },
        "rules": {
            "before": "admitted program's exact call sequence at normalized position 0 (retained rule)",
            "after": "before, or committed calls == declared prologue exactly (routes, order, arguments, "
                     "nothing else) followed immediately by the admitted program (runtime match_prologue rule)",
            "diagnostics": "reported per architecture but not eligibility: prologue routes with any arguments; "
                           "any documentation-only prefix then the program",
        },
        "assumptions": {
            "prologue_definition": [f"{m} {p} " + " ".join(f"{k}={v}" for k, v in a.items()) for m, p, a in prologue],
            "required_catalog_declaration": REQUIRED_CATALOG_DECLARATION,
            "note": "the runtime refuses an undeclared prologue tool; AFTER assumes the declaration above is signed",
        },
        "retained_cross_check": check,
        **analysis,
        "does_not_measure": [
            "phi: the manifest check and the calibrated gate are not evaluated here",
            "n_B: the released logs retain API calls, not model boundaries",
            "any saving in requests, tokens, dollars, or latency",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    args.table.parent.mkdir(parents=True, exist_ok=True)
    args.table.write_text(latex_table(analysis["by_agent_family"]))

    print(f"wrote {RETAINED._display(args.output)} and {RETAINED._display(args.table)}")
    print("  prologue:", "; ".join(report["assumptions"]["prologue_definition"]))
    print("  declared in catalog:", analysis["prologue_tools_declared_in_catalog"])
    print("  by agent architecture (before -> after):")
    for family, row in analysis["by_agent_family"].items():
        if not row["tasks"]:
            continue
        print(
            f"      {family:16s} {row['label']:38s} "
            f"{row['before_eligible_at_position_0']:5d}/{row['tasks']:5d} = {row['before_rate']:.3f}"
            f"  ->  {row['after_eligible_total']:5d}/{row['tasks']:5d} = {row['after_rate']:.3f}"
        )


if __name__ == "__main__":
    main()
