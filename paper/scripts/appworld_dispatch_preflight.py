#!/usr/bin/env python3
"""Structural dispatch eligibility of the admitted AppWorld artifact on released baselines.

The compiler substrate in ``appworld_compiler_benchmark.py`` mines and admits an artifact
from *gold solution* traces.  That establishes admissibility.  It says nothing about
whether the artifact would ever dispatch against a real agent, because a gold solution is
not an agent trajectory: it has no planning turns, no documentation lookups, and no
recovery steps.

AppWorld publishes the official baseline agents' experiment outputs -- 28 released runs
over four agent architectures and four models -- and each retains the ordered API calls the
agent actually issued.  That is enough to measure the one term of the cost model the paper
has never measured on an external corpus: how often the compiled region is *structurally
eligible* at the entry boundary.

What this measures, precisely, and what it does not:

* It measures structural eligibility: does the admitted program's exact call sequence occur
  at normalized position 0 of a real trajectory.  That is the position invariant of
  \\eqref{eq:prefix} plus tool identity, evaluated on held-out agent behaviour.
* It is an **upper bound on** $\\phi$, not $\\phi$.  Full dispatch additionally requires the
  manifest check $M'\\simeq M$ and the calibrated gate $q(z)\\le\\eta$.  None of the released
  baselines runs the artifact's pinned manifest, so the true dispatch rate against these
  specific runs is zero; what is transferable is the structural rate.
* It cannot measure $n_B$.  The released logs retain API calls, not model boundaries, so the
  fraction of *calls* a region covers is computable and the fraction of *model requests* is
  not.  No saving is reported here, and none can be.

Provider-free.  Reads only the released outputs and the pinned API documentation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from guarded_agentic_compaction.schema.effects import EffectCatalog  # noqa: E402


PACKAGE_VERSION = "0.1.3.post1"
CATALOG_PATH = ROOT / "benchmarks" / "contracts" / "effects" / "appworld.yaml"
COMPILER_RESULT = (
    ROOT / "paper" / "results" / "external_benchmarks" / "appworld_compiler_execution.json"
)
DEFAULT_OUT = (
    ROOT / "paper" / "results" / "external_benchmarks" / "appworld_dispatch_preflight.json"
)

#: The program the compiler admitted, as (method, path) pairs in the released logs' shape.
ADMITTED_PROGRAM = (("get", "/supervisor/profile"), ("get", "/supervisor/account_passwords"))

#: A read the agent may issue before the region and which a deployed guard could admit as
#: part of the entry boundary.  Reported separately rather than folded in, because admitting
#: it is a design change the compiler did not make.
ENTRY_READ = ("get", "/supervisor/active_task")

#: Agent architectures, keyed by the released directory prefix.
FAMILIES = {
    "full_code_refl": "Full code + reflection",
    "ipfuncall": "Iterative parallel function calling",
    "plan_exec": "Plan and execute",
    "react": "ReAct",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _display(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _distribution(values: Sequence[int]) -> dict[str, Any]:
    if not values:
        return {}
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "min": ordered[0],
        "median": ordered[len(ordered) // 2],
        "max": ordered[-1],
    }


# ---------------------------------------------------------------------------
# url -> declared tool identity
# ---------------------------------------------------------------------------


def _load_route_table(api_docs: Path) -> list[tuple[str, re.Pattern[str], str]]:
    """Compile the pinned API documentation into (method, path regex, tool) routes.

    216 of AppWorld's 457 documented paths carry paremeters, so a released log's
    ``/simple_note/notes/930`` has to be matched against ``/simple_note/notes/{note_id}``.
    Literal routes are ordered before templated ones so a literal path is never captured by
    a template that would also match it.
    """

    literal: list[tuple[str, re.Pattern[str], str]] = []
    templated: list[tuple[str, re.Pattern[str], str]] = []
    for source in sorted(api_docs.glob("*.json")):
        for name, spec in json.loads(source.read_text()).items():
            path = str(spec["path"])
            method = str(spec["method"]).lower()
            tool = f"{spec['app_name']}.{name}"
            pattern = re.compile(
                "^" + re.sub(r"\{[^}]+\}", r"[^/]+", re.escape(path).replace(r"\{", "{")
                            .replace(r"\}", "}")) + "$"
            )
            (templated if "{" in path else literal).append((method, pattern, tool))
    return literal + templated


def _resolve(method: str, url: str, routes: Sequence[tuple[str, re.Pattern[str], str]]) -> str | None:
    path = url.split("?", 1)[0]
    for route_method, pattern, tool in routes:
        if route_method == method and pattern.match(path):
            return tool
    return None


# ---------------------------------------------------------------------------
# released trajectories
# ---------------------------------------------------------------------------


def _trajectory(path: Path) -> list[tuple[str, str]]:
    calls: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        calls.append((str(record["method"]).lower(), str(record["url"]).split("?", 1)[0]))
    return calls


def _family_of(name: str) -> str:
    for prefix in FAMILIES:
        if name.startswith(prefix):
            return prefix
    return "unknown"


def _maximal_read_prefix(
    calls: Sequence[tuple[str, str]],
    routes: Sequence[tuple[str, re.Pattern[str], str]],
    catalog: EffectCatalog,
) -> tuple[int, str | None]:
    """How deep a compiled region could reach in this trajectory before a barrier.

    Reported as headroom, not as a claim: reaching a barrier at depth d means no compiled
    region on this trajectory can exceed d calls, whatever the mining parameters.
    """

    depth = 0
    for method, url in calls:
        tool = _resolve(method, url, routes)
        if tool is None:
            return depth, "undeclared_route"
        spec = catalog.get(tool)
        if not spec.compilable:
            return depth, tool
        depth += 1
    return depth, None


def analyze(outputs: Path, api_docs: Path, catalog: EffectCatalog) -> dict[str, Any]:
    routes = _load_route_table(api_docs)
    per_run: list[dict[str, Any]] = []
    first_call: Counter[str] = Counter()
    barrier_at_depth_zero: Counter[str] = Counter()

    for run in sorted(outputs.glob("*_test_*")):
        if not (run / "tasks").is_dir():
            continue
        logs = sorted(run.glob("tasks/*/logs/api_calls.jsonl"))
        if not logs:
            continue
        counts: Counter[str] = Counter()
        call_lengths: list[int] = []
        read_depths: list[int] = []
        for log in logs:
            calls = _trajectory(log)
            counts["tasks"] += 1
            if not calls:
                counts["empty_trajectory"] += 1
                continue
            call_lengths.append(len(calls))
            first_call[f"{calls[0][0]}:{calls[0][1]}"] += 1
            if tuple(calls[: len(ADMITTED_PROGRAM)]) == ADMITTED_PROGRAM:
                counts["eligible_at_position_0"] += 1
            elif (
                calls[0] == ENTRY_READ
                and tuple(calls[1 : 1 + len(ADMITTED_PROGRAM)]) == ADMITTED_PROGRAM
            ):
                counts["eligible_after_entry_read"] += 1
            if any(
                tuple(calls[index : index + len(ADMITTED_PROGRAM)]) == ADMITTED_PROGRAM
                for index in range(len(calls) - len(ADMITTED_PROGRAM) + 1)
            ):
                counts["program_occurs_anywhere"] += 1
            depth, barrier = _maximal_read_prefix(calls, routes, catalog)
            read_depths.append(depth)
            if depth == 0 and barrier:
                barrier_at_depth_zero[barrier] += 1
        per_run.append({
            "run": run.name,
            "family": _family_of(run.name),
            "split": "test_challenge" if "test_challenge" in run.name else "test_normal",
            **{key: counts[key] for key in (
                "tasks", "empty_trajectory", "eligible_at_position_0",
                "eligible_after_entry_read", "program_occurs_anywhere")},
            "calls_per_task": _distribution(call_lengths),
            "maximal_read_prefix": _distribution(read_depths),
        })

    def _pool(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
        rows = list(rows)
        tasks = sum(row["tasks"] for row in rows)
        at_zero = sum(row["eligible_at_position_0"] for row in rows)
        after = sum(row["eligible_after_entry_read"] for row in rows)
        anywhere = sum(row["program_occurs_anywhere"] for row in rows)
        return {
            "runs": len(rows),
            "tasks": tasks,
            "eligible_at_position_0": at_zero,
            "eligible_after_entry_read": after,
            "program_occurs_anywhere": anywhere,
            "structural_eligibility_at_position_0": at_zero / tasks if tasks else None,
            "structural_eligibility_with_entry_read": (
                (at_zero + after) / tasks if tasks else None
            ),
            "occurs_but_not_at_position_0": anywhere - at_zero - after,
        }

    by_family = {
        family: {"label": label, **_pool(r for r in per_run if r["family"] == family)}
        for family, label in FAMILIES.items()
    }
    by_split = {
        split: _pool(r for r in per_run if r["split"] == split)
        for split in ("test_normal", "test_challenge")
    }
    return {
        "per_run": per_run,
        "by_agent_family": by_family,
        "by_split": by_split,
        "pooled": _pool(per_run),
        "first_call_in_released_trajectories": dict(first_call.most_common(8)),
        "barrier_at_depth_zero": dict(barrier_at_depth_zero.most_common(8)),
        "declared_routes": len(routes),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
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

    catalog = EffectCatalog.from_yaml(CATALOG_PATH)
    analysis = analyze(outputs, api_docs, catalog)
    if not analysis["per_run"]:
        raise SystemExit("no released baseline runs were found")

    admitted_program = None
    if COMPILER_RESULT.is_file():
        payload = json.loads(COMPILER_RESULT.read_text())
        gates = payload["admission"]["A"]["gates"]
        admitted = [row for row in gates if not row["retire"]]
        if admitted:
            admitted_program = admitted[0]["program_tools"]

    report = {
        "schema": "gac-appworld-dispatch-preflight/v1",
        "benchmark": "appworld",
        "package_version": PACKAGE_VERSION,
        "effect_catalog": {
            "path": _display(CATALOG_PATH),
            "sha256": _sha256(CATALOG_PATH),
        },
        "artifact_under_test": {
            "program": [f"{method} {path}" for method, path in ADMITTED_PROGRAM],
            "admitted_program_tools": admitted_program,
            "source": _display(COMPILER_RESULT),
            "compiled_on": "public train+dev gold solutions",
            "evaluated_on": "released official baseline agent trajectories, test_normal and test_challenge",
        },
        **analysis,
        "measures": [
            "structural eligibility: the admitted program's exact call sequence at normalized position 0",
            "an upper bound on phi, not phi: the manifest check and the calibrated gate are not evaluated here",
            "maximal read prefix: how deep any compiled region could reach before a declared barrier",
        ],
        "does_not_measure": [
            "n_B: the released logs retain API calls, not model boundaries",
            "any saving in requests, tokens, dollars, or latency",
            "task quality: the released evaluations are upstream results for the baselines, not for a dispatched artifact",
        ],
        "runtime_seconds": time.perf_counter() - started,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    pooled = report["pooled"]
    print(f"wrote {_display(args.output)}")
    print(f"  {pooled['runs']} released baseline runs, {pooled['tasks']} trajectories")
    print(f"  structural eligibility at position 0: "
          f"{pooled['eligible_at_position_0']}/{pooled['tasks']} "
          f"= {pooled['structural_eligibility_at_position_0']:.3f}")
    print(f"  with a leading supervisor/active_task admitted: "
          f"{pooled['structural_eligibility_with_entry_read']:.3f}")
    print(f"  program occurs but not at position 0 (position invariant refuses): "
          f"{pooled['occurs_but_not_at_position_0']}")
    print("  by agent architecture:")
    for family, row in report["by_agent_family"].items():
        if not row["tasks"]:
            continue
        print(f"      {family:16s} {row['label']:38s} "
              f"{row['eligible_at_position_0']:5d}/{row['tasks']:5d} "
              f"= {row['structural_eligibility_at_position_0']:.3f}")
    print("  first call in released trajectories:")
    for call, count in list(report["first_call_in_released_trajectories"].items())[:4]:
        print(f"      {count:6d}  {call}")


if __name__ == "__main__":
    main()
