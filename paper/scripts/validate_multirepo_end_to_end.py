"""Validator family ``multirepo_end_to_end`` (flip-plans.md task 1.9).

``validate_multirepo_end_to_end(results_dir)`` returns a list of ``CheckResult(ok, message)`` in the
style of the ``time_forward_pr_outcome`` family of ``validate_artifacts.py``. The integrator registers
it there, for example::

    from validate_multirepo_end_to_end import validate_multirepo_end_to_end
    def validate_multirepo_end_to_end_family() -> None:
        for r in validate_multirepo_end_to_end(PAPER / "results/multirepo_end_to_end"):
            ok(r.ok, r.message)

It pins n, k, U, decisions, input digests and ledger totals recorded in ``summary.json`` and
recomputes each from the raw ``calibration_groups.json`` with its own small implementation
(scipy Beta quantile and the closed form for k = 0), independent of the analysis script's code path.
It also checks that regenerating the summary reproduces the committed file.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, NamedTuple

ALPHA, DELTA, GRID_SIZE = 0.05, 0.10, 11
REPO_CAP_USD, TOTAL_CAP_USD = 5.0, 25.0
RETIRED = ("retired", "shortfall_no_run")
#: flip-plans.md Appendix A.3, copied here so the validator does not trust the analysis script.
A3 = {"grid": {92: 0, 106: 0, 132: 0, 150: 1, 200: 3, 300: 6, 400: 9, 800: 25},
      "single": {132: 3, 200: 5, 400: 14, 800: 31}}


class CheckResult(NamedTuple):
    ok: bool
    message: str


def _upper(k: int, n: int, conf: float) -> float:
    if n == 0 or k >= n:
        return 1.0
    if k == 0:
        return 1.0 - (1.0 - conf) ** (1.0 / n)
    from scipy.stats import beta

    return float(beta.ppf(conf, k + 1, n - k))


def _floor(n: int, conf: float) -> int:
    best = -1
    for k in range(n + 1):
        if _upper(k, n, conf) <= ALPHA:
            best = k
        else:
            break
    return best


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _close(a: Any, b: Any) -> bool:
    return a is not None and b is not None and math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-12)


def _recompute(groups: list[dict[str, Any]]) -> dict[str, Any]:
    used = [g for g in groups if g["arms"]["compiled"]["eligible"]
            and (g["arms"]["compiled"]["dispatched"] or g["arms"]["compiled"]["verifier_abstained"])]
    eligible = [g for g in groups if g["arms"]["compiled"]["eligible"]]
    k = sum(1 for g in used if g["arms"]["compiled"]["dispatched"] and not g["arms"]["compiled"]["contract_met"])
    return {"n": len(used), "k": k, "excluded": len(eligible) - len(used),
            "authors": len({(g["repo"], g["author"]) for g in used}),
            "days": len({g["created_day"] for g in used})}


def validate_multirepo_end_to_end(results_dir: str | Path) -> list[CheckResult]:
    """Pin and recompute the multi-repository end-to-end summary. Never raises on bad data."""

    results: list[CheckResult] = []

    def ok(condition: bool, message: str) -> None:
        results.append(CheckResult(bool(condition), f"multirepo e2e: {message}"))

    results_dir = Path(results_dir)
    summary_path = results_dir / "summary.json"
    ok(summary_path.exists(), "summary.json present")
    if not summary_path.exists():
        return results
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        ok(False, f"summary.json loads ({exc})")
        return results

    conf = {"grid": 1.0 - DELTA / GRID_SIZE, "single": 1.0 - DELTA}
    rules = summary.get("rules", {})
    ok(rules.get("alpha") == ALPHA and rules.get("delta") == DELTA and rules.get("grid_size") == GRID_SIZE
       and rules.get("primary") == "grid_m1", "rules pinned: alpha 0.05, delta 0.10, |grid| 11, primary registered grid m = 1")
    ok(_close(rules.get("grid_m1_confidence"), conf["grid"]) and _close(rules.get("single_rule_confidence"), conf["single"]),
       "bound confidences are 1 - 0.1/11 and 0.90")
    ok(all(_floor(n, conf[r]) == k for r, tbl in A3.items() for n, k in tbl.items()) and not summary.get("appendix_a3_floor_mismatches"),
       "decision floors match Appendix A.3 (grid m = 1: 92:0 ... 800:25; single rule: 132:3 ... 800:31)")

    on_disk = sorted(p.name for p in results_dir.iterdir() if p.is_dir() and "__" in p.name)
    listed = sorted(e.get("directory", "") for e in summary.get("repositories", []))
    ok(on_disk == listed, f"summary lists exactly the repository directories on disk ({len(on_disk)})")

    run_groups: list[dict[str, Any]] = []
    spent_total = 0.0
    run_repos: list[str] = []
    for entry in summary.get("repositories", []):
        repo, directory = entry.get("repo", "?"), results_dir / entry.get("directory", "?")
        if not directory.is_dir():
            ok(False, f"{repo}: directory exists")
            continue
        for fname, digest in sorted(entry.get("input_sha256", {}).items()):
            path = directory / fname
            ok(path.exists() and _sha(path) == digest, f"{repo}: {fname} digest matches summary")
        ledger_path = directory / "ledger.json"
        if ledger_path.exists():
            spent = float(json.loads(ledger_path.read_text())["spent_usd"])
            spent_total += spent
            ok(_close(entry["ledger"]["spent_usd"], spent) and spent <= REPO_CAP_USD,
               f"{repo}: ledger spend ${spent:.6f} matches summary and is within the ${REPO_CAP_USD:.0f} cap")
        else:
            ok(entry.get("ledger", {}).get("present") is False, f"{repo}: ledger absent and recorded as absent")
        sel_path = directory / "selection.json"
        if sel_path.exists():
            sel = json.loads(sel_path.read_text())
            ok(sel.get("disjoint") is not False, f"{repo}: selection is not recorded as overlapping")
        groups_path = directory / "calibration_groups.json"
        groups = json.loads(groups_path.read_text()) if groups_path.exists() else []
        if entry.get("status") != "run":
            ok(entry.get("status") in (*RETIRED, "incomplete") and "certificate" not in entry,
               f"{repo}: not run ({entry.get('status')}) and carries no certificate")
            continue
        run_repos.append(repo)
        run_groups.extend(groups)
        got = _recompute(groups)
        cert = entry["certificate"]
        ok(cert["n"] == got["n"] and cert["k"] == got["k"], f"{repo}: n = {got['n']}, k = {got['k']} recomputed from raw groups match summary")
        ok(entry["eligible_but_excluded"] == got["excluded"], f"{repo}: eligible-but-excluded = {got['excluded']} matches")
        ok(entry["distinct_authors"] == got["authors"] and entry["distinct_days"] == got["days"],
           f"{repo}: distinct authors {got['authors']} and days {got['days']} match")
        ok(got["authors"] == got["n"], f"{repo}: one group per author (authors = groups = {got['n']})")
        for name, rule in (("grid", "grid_m1"), ("single", "single_rule")):
            upper = _upper(got["k"], got["n"], conf[name])
            ok(_close(cert[rule]["U"], upper), f"{repo}: U ({name}) = {upper:.4f} recomputed matches summary")
            ok(cert[rule]["max_admissible_k"] == _floor(got["n"], conf[name]) and cert[rule]["admits"] is (upper <= ALPHA),
               f"{repo}: {name} floor and admission flag consistent")
        decision = "admit" if _upper(got["k"], got["n"], conf["grid"]) <= ALPHA else "retire"
        ok(cert["decision"] == decision, f"{repo}: decision {decision} (primary registered grid, m = 1) matches summary")

    pooled = summary.get("pooled_run_repositories")
    if run_groups:
        got = _recompute(run_groups)
        ok(pooled is not None and pooled["certificate"]["n"] == got["n"] and pooled["certificate"]["k"] == got["k"]
           and pooled["repos"] == run_repos, f"pooled: n = {got['n']}, k = {got['k']} over {len(run_repos)} run repositories match")
        if pooled is not None:
            decision = "admit" if _upper(got["k"], got["n"], conf["grid"]) <= ALPHA else "retire"
            ok(_close(pooled["certificate"]["grid_m1"]["U"], _upper(got["k"], got["n"], conf["grid"]))
               and _close(pooled["certificate"]["single_rule"]["U"], _upper(got["k"], got["n"], conf["single"]))
               and pooled["certificate"]["decision"] == decision, "pooled: U (both rules) and decision recomputed match")
    else:
        ok(pooled is None, "pooled: absent when no repository ran")

    ledger = summary.get("ledger", {})
    ok(_close(ledger.get("total_spent_usd"), round(spent_total, 6)) and spent_total <= TOTAL_CAP_USD,
       f"ledger total ${spent_total:.6f} matches summary and is within the ${TOTAL_CAP_USD:.0f} cap")
    ok(sorted(n["repo"] for n in summary.get("not_run", []))
       == sorted(e["repo"] for e in summary.get("repositories", []) if e.get("status") != "run"),
       "retired / shortfall list matches repository statuses")

    try:  # regeneration reproduces the committed summary (determinism, nothing stale)
        if str(Path(__file__).resolve().parent) not in sys.path:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
        import multirepo_end_to_end_analysis as ana

        regenerated = json.loads(json.dumps(ana.build_summary(results_dir), sort_keys=True))
        ok(regenerated == summary, "summary.json equals a fresh regeneration from the raw groups")
    except Exception as exc:  # noqa: BLE001
        ok(False, f"summary regeneration ({exc})")
    return results
