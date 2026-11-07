#!/usr/bin/env python3
"""Provider-free analysis of the unfiltered, author-unit multi-repository end-to-end study.

Reads, per repository, ``<results-dir>/<owner>__<repo>/`` containing ``selection.json``,
``calibration_groups.json`` (a list of per-group records, see ``GROUP_SCHEMA`` below),
``ledger.json`` and optionally ``compile.json``. Writes ``<results-dir>/summary.json`` and the
LaTeX table ``paper/iclr/tables/multirepo_end_to_end.tex``. Output is deterministic (no
timestamps, sorted keys), so regenerating twice leaves ``git diff`` empty.

Definitions (frozen protocol, flip-plans.md Appendix A.5):
  n   groups whose compiled-arm record is eligible AND (verifier abstained OR dispatched);
  k   compiled arm dispatched and task contract not met (a violation); a clean abstention is in
      n with loss 0;
  eligible-but-excluded   eligible, neither abstained nor dispatched (reported, not in n);
  U   exact one-sided Clopper-Pearson upper bound, same closed form as
      ``grc/calibrate.py``: (a) registered grid, m = 1, confidence 1 - 0.1/11;
      (b) single rule gamma = delta = 0.10, confidence 0.90;
  admit   iff U <= 0.05 under (a) (primary); (b) is secondary and reported alongside.

Run on real data:
  python paper/scripts/multirepo_end_to_end_analysis.py --results-dir paper/results/multirepo_end_to_end
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from guarded_agentic_compaction.grc.calibrate import GRID, clopper_pearson_upper  # noqa: E402
from scipy.stats import binomtest  # noqa: E402

ALPHA = 0.05
DELTA = 0.10
GRID_SIZE = len(GRID)  # |Lambda| = 11
TARGET_N = 200
REPO_CAP_USD = 5.0
TOTAL_CAP_USD = 25.0
ARMS = ("compiled", "baseline", "manual")
ARM_KEYS = ("eligible", "dispatched", "verifier_abstained", "contract_met", "fallback",
            "requests", "tokens", "latency_ms", "cost_usd")
RESOURCES = ("requests", "tokens", "latency_ms", "cost_usd")
RETIRED_STATUSES = ("retired", "shortfall_no_run")
RULES = ("grid_m1", "single_rule")

GROUP_SCHEMA = {
    "repo": "owner/repo", "number": 1, "author": "login", "created_day": "YYYY-MM-DD",
    "class": "open|merged|closed_unmerged",
    "arms": {arm: {key: "..." for key in ARM_KEYS} for arm in ARMS},
}

DEFAULT_RESULTS = ROOT / "paper/results/multirepo_end_to_end"
DEFAULT_TABLE = ROOT / "paper/iclr/tables/multirepo_end_to_end.tex"


# ----------------------------------------------------------------------------- bounds


def rule_confidence(rule: str, m: int = 1) -> float:
    """Coverage of the one-sided interval: (a) 1 - delta/(|Lambda| m); (b) 1 - delta."""

    if rule == "grid_m1":
        return 1.0 - DELTA / (GRID_SIZE * m)
    if rule == "single_rule":
        return 1.0 - DELTA
    raise ValueError(f"unknown rule {rule!r}")


def upper_bound(k: int, n: int, rule: str, m: int = 1) -> float:
    return float(clopper_pearson_upper(k, n, rule_confidence(rule, m)))


def max_admissible_k(n: int, rule: str = "grid_m1", m: int = 1) -> int:
    """Largest k with U(k, n) <= alpha, or -1 when even k = 0 cannot admit (decision floor)."""

    conf = rule_confidence(rule, m)
    best = -1
    for k in range(n + 1):
        if float(clopper_pearson_upper(k, n, conf)) <= ALPHA:
            best = k
        else:
            break
    return best


#: flip-plans.md Appendix A.3 (m = 1 registered grid; single rule), pinned for tests and validator.
APPENDIX_A3_FLOORS = {
    "grid_m1": {92: 0, 106: 0, 132: 0, 150: 1, 200: 3, 300: 6, 400: 9, 800: 25},
    "single_rule": {132: 3, 200: 5, 400: 14, 800: 31},
}


def check_appendix_a3() -> list[str]:
    """Return mismatches between the computed floors and Appendix A.3 (empty means all match)."""

    bad = []
    for rule, table in APPENDIX_A3_FLOORS.items():
        for n, expected in table.items():
            got = max_admissible_k(n, rule)
            if got != expected:
                bad.append(f"{rule} n={n}: computed {got}, Appendix A.3 {expected}")
    return bad


def mcnemar_exact(baseline_only: int, compiled_only: int) -> float:
    """Two-sided exact McNemar p-value on the discordant pairs."""

    total = baseline_only + compiled_only
    if total == 0:
        return 1.0
    return float(binomtest(min(baseline_only, compiled_only), total, 0.5).pvalue)


# ----------------------------------------------------------------------------- loading


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_dirs(results_dir: Path) -> list[Path]:
    """Repository directories are ``<owner>__<repo>``; anything else (fixture/, ...) is skipped."""

    if not results_dir.is_dir():
        return []
    return sorted(p for p in results_dir.iterdir() if p.is_dir() and "__" in p.name)


def validate_group(group: dict[str, Any]) -> None:
    for key in ("repo", "number", "author", "created_day", "class", "arms"):
        if key not in group:
            raise ValueError(f"group {group.get('number')!r} missing {key!r}")
    for arm in ARMS:
        record = group["arms"].get(arm)
        if record is None:
            raise ValueError(f"group {group['number']} missing arm {arm!r}")
        missing = [key for key in ARM_KEYS if key not in record]
        if missing:
            raise ValueError(f"group {group['number']} arm {arm!r} missing keys {missing}")
    compiled = group["arms"]["compiled"]
    if compiled["dispatched"] and compiled["verifier_abstained"]:
        raise ValueError(f"group {group['number']}: compiled arm both dispatched and abstained")


def in_n(group: dict[str, Any]) -> bool:
    c = group["arms"]["compiled"]
    return bool(c["eligible"]) and bool(c["dispatched"] or c["verifier_abstained"])


def is_violation(group: dict[str, Any]) -> bool:
    c = group["arms"]["compiled"]
    return bool(c["dispatched"]) and not bool(c["contract_met"])


# ----------------------------------------------------------------------------- statistics


def certificate(k: int, n: int) -> dict[str, Any]:
    out: dict[str, Any] = {"n": n, "k": k}
    for rule in RULES:
        upper = upper_bound(k, n, rule)
        out[rule] = {"confidence": rule_confidence(rule), "U": upper,
                     "max_admissible_k": max_admissible_k(n, rule), "admits": bool(upper <= ALPHA)}
    out["decision"] = "admit" if out["grid_m1"]["admits"] else "retire"
    return out


def _mean(values: list[float]) -> float | None:
    # math.fsum is correctly rounded, so the summary is byte-identical on every Python version
    # (3.12 changed the built-in sum of floats to compensated summation).
    return math.fsum(values) / len(values) if values else None


def resources(groups: list[dict[str, Any]]) -> dict[str, Any]:
    means = {arm: {key: _mean([float(g["arms"][arm][key]) for g in groups]) for key in RESOURCES}
             for arm in ARMS}
    reductions: dict[str, dict[str, float | None]] = {}
    for arm in ("compiled", "manual"):
        reductions[arm] = {}
        for key in RESOURCES:
            base, val = means["baseline"][key], means[arm][key]
            reductions[arm][key] = (100.0 * (1.0 - val / base)) if base and val is not None else None
    return {"mean_per_arm": means, "reduction_vs_baseline_pct": reductions}


def paired(groups: list[dict[str, Any]]) -> dict[str, Any]:
    both = baseline_only = compiled_only = neither = 0
    for g in groups:
        b, c = bool(g["arms"]["baseline"]["contract_met"]), bool(g["arms"]["compiled"]["contract_met"])
        if b and c:
            both += 1
        elif b:
            baseline_only += 1  # baseline met, compiled missed: a compiled-only miss
        elif c:
            compiled_only += 1
        else:
            neither += 1
    n = len(groups)
    return {
        "n": n, "both_met": both, "baseline_only_met": baseline_only,
        "compiled_only_met": compiled_only, "neither_met": neither,
        "baseline_met": both + baseline_only, "compiled_met": both + compiled_only,
        "mcnemar_exact_p_two_sided": mcnemar_exact(baseline_only, compiled_only),
        "compiled_only_misses": baseline_only,
        "compiled_only_misses_upper95": float(clopper_pearson_upper(baseline_only, n, 1.0 - ALPHA)) if n else 1.0,
    }


def fallback_outcomes(groups: list[dict[str, Any]]) -> dict[str, Any]:
    fb = [g for g in groups if g["arms"]["compiled"]["fallback"]]
    return {
        "abstained": sum(1 for g in groups if g["arms"]["compiled"]["verifier_abstained"]),
        "fallback_groups": len(fb),
        "fallback_contract_met": sum(1 for g in fb if g["arms"]["compiled"]["contract_met"]),
        "fallback_contract_missed": sum(1 for g in fb if not g["arms"]["compiled"]["contract_met"]),
    }


def summarise_groups(groups: list[dict[str, Any]]) -> dict[str, Any]:
    """Statistics for one set of groups (one repository, or the pool)."""

    eligible = [g for g in groups if g["arms"]["compiled"]["eligible"]]
    used = [g for g in groups if in_n(g)]
    k = sum(1 for g in used if is_violation(g))
    # The unit is one PR per author within a repository, so authors are (repo, login) pairs.
    authors = {(g["repo"], g["author"]) for g in used}
    dispatched = [g for g in used if g["arms"]["compiled"]["dispatched"]]
    return {
        "groups_recorded": len(groups),
        "ineligible": len(groups) - len(eligible),
        "eligible": len(eligible),
        "eligible_but_excluded": len(eligible) - len(used),
        "dispatched": len(dispatched),
        "dispatched_contract_met": len(dispatched) - k,
        "distinct_authors": len(authors),
        "distinct_logins": len({g["author"] for g in used}),
        "distinct_days": len({g["created_day"] for g in used}),
        "authors_equal_groups": len(authors) == len(used),
        "certificate": certificate(k, len(used)),
        "paired": paired(used),
        "fallback": fallback_outcomes(used),
        "resources": resources(used),
        "violations": [{"repo": g["repo"], "number": g["number"], "author": g["author"],
                        "class": g["class"]} for g in used if is_violation(g)],
        "class_counts_in_n": {c: sum(1 for g in used if g["class"] == c)
                              for c in sorted({g["class"] for g in used})},
    }


# ----------------------------------------------------------------------------- repositories


def load_repository(directory: Path) -> dict[str, Any]:
    """Read one repository directory: raw material plus not-run status."""

    files: dict[str, str] = {}
    loaded: dict[str, Any] = {}
    for fname in ("selection.json", "calibration_groups.json", "compile.json", "ledger.json"):
        path = directory / fname
        if path.exists():
            files[fname] = sha256_file(path)
            loaded[fname] = _read(path)
    groups = loaded.get("calibration_groups.json") or []
    status, reason = None, ""
    for source in (loaded.get("compile.json"), loaded.get("selection.json")):
        if isinstance(source, dict) and source.get("status") in RETIRED_STATUSES:
            status = source["status"]
            reason = str(source.get("reason", ""))
            break
    if status is None and not groups:
        status, reason = "incomplete", "calibration_groups.json missing or empty"
    return {"repo": directory.name.replace("__", "/", 1), "directory": directory.name, "files": files,
            "selection": loaded.get("selection.json"), "ledger": loaded.get("ledger.json"),
            "groups": groups, "status": status, "reason": reason}


def summarise_repository(raw: dict[str, Any]) -> dict[str, Any]:
    spent = None if raw["ledger"] is None else float(raw["ledger"]["spent_usd"])
    entry: dict[str, Any] = {
        "repo": raw["repo"], "directory": raw["directory"], "status": raw["status"] or "run",
        "reason": raw["reason"], "input_sha256": raw["files"],
        "ledger": {"present": raw["ledger"] is not None, "spent_usd": spent, "cap_usd": REPO_CAP_USD,
                   "within_cap": spent is None or spent <= REPO_CAP_USD},
    }
    sel = raw["selection"]
    if isinstance(sel, dict):
        entry["selection"] = {"disjoint": sel.get("disjoint"),
                              "calibration_n_planned": len(sel["calibration"]) if isinstance(sel.get("calibration"), list) else None}
    if entry["status"] != "run":
        return entry
    for g in raw["groups"]:
        validate_group(g)
    entry.update(summarise_groups(raw["groups"]))
    entry["shortfall_vs_target_n"] = max(0, TARGET_N - entry["certificate"]["n"])
    return entry


def build_summary(results_dir: Path) -> dict[str, Any]:
    raws = [load_repository(d) for d in repo_dirs(results_dir)]
    repos = [summarise_repository(r) for r in raws]
    run = [(r, e) for r, e in zip(raws, repos) if e["status"] == "run"]
    not_run = [{"repo": e["repo"], "status": e["status"], "reason": e["reason"],
                "ledger_spent_usd": e["ledger"]["spent_usd"]} for e in repos if e["status"] != "run"]
    pooled_groups = [g for r, _ in run for g in r["groups"]]
    pooled = None
    if pooled_groups:
        pooled = summarise_groups(pooled_groups)
        pooled["repos"] = [e["repo"] for _, e in run]
    spent = [e["ledger"]["spent_usd"] for e in repos if e["ledger"]["spent_usd"] is not None]
    total = round(math.fsum(spent), 6)
    return {
        "schema": "multirepo_end_to_end/summary/v1",
        "protocol": "paper/supplementary/multirepo-unfiltered-end-to-end-protocol.md",
        "rules": {"alpha": ALPHA, "delta": DELTA, "grid_size": GRID_SIZE,
                  "grid_m1_confidence": rule_confidence("grid_m1"),
                  "single_rule_confidence": rule_confidence("single_rule"),
                  "primary": "grid_m1", "target_n_per_repo": TARGET_N},
        "appendix_a3_floor_mismatches": check_appendix_a3(),
        "not_run": not_run,
        "repositories": repos,
        "pooled_run_repositories": pooled,
        "admitted_repositories": [e["repo"] for _, e in run if e["certificate"]["decision"] == "admit"],
        "ledger": {"total_spent_usd": total, "total_cap_usd": TOTAL_CAP_USD,
                   "within_total_cap": total <= TOTAL_CAP_USD,
                   "per_repo_spent_usd": {e["repo"]: e["ledger"]["spent_usd"] for e in repos}},
    }


# ----------------------------------------------------------------------------- table


def tex(text: str) -> str:
    return text.replace("\\", r"\textbackslash{}").replace("_", r"\_").replace("&", r"\&").replace("%", r"\%")


def pct(x: float | None) -> str:
    return "--" if x is None else f"{x:.1f}"


def _cert_row(name: str, c: dict[str, Any], p: dict[str, Any]) -> str:
    return (f"{name} & {c['n']} & {c['k']} & {c['grid_m1']['U']:.4f} & {c['single_rule']['U']:.4f} & "
            f"{c['decision']} & {p['baseline_only_met']}/{p['compiled_only_met']} & "
            f"{p['mcnemar_exact_p_two_sided']:.3f} \\\\")


def render_table(summary: dict[str, Any], label: str = "") -> str:
    lines = ["% generated by paper/scripts/multirepo_end_to_end_analysis.py; do not edit by hand"]
    if label:
        lines.append(f"% {label}")
    if not summary["repositories"]:
        return "\n".join(lines + [
            r"\begin{tabularx}{\linewidth}{@{}>{\raggedright\arraybackslash}X@{}}", r"\toprule",
            r"No repository results recorded yet. \\", r"\bottomrule", r"\end{tabularx}", ""])
    run = [e for e in summary["repositories"] if e["status"] == "run"]
    pooled = summary["pooled_run_repositories"]
    # Panel A (certificates): not-run repositories first, then repositories by descending k.
    lines += [r"\begin{tabularx}{\linewidth}{@{}>{\raggedright\arraybackslash}X r r r r l r r@{}}", r"\toprule",
              r"Repository & $n$ & $k$ & $U_{\mathrm{grid}}$ & $U_{\mathrm{1}}$ & Decision & b/c & $p_{\mathrm{McN}}$ \\",
              r"\midrule"]
    for item in summary["not_run"]:
        reason = f" ({tex(item['reason'])})" if item["reason"] else ""
        lines.append(rf"{tex(item['repo'])} & \multicolumn{{7}}{{l}}{{{tex(item['status'].replace('_', ' '))}{reason}; no certificate}} \\")
    for e in sorted(run, key=lambda r: (-r["certificate"]["k"], r["repo"])):
        lines.append(_cert_row(tex(e["repo"]), e["certificate"], e["paired"]))
    if pooled:
        lines += [r"\midrule", _cert_row(f"Pooled ({len(pooled['repos'])} run repositories)", pooled["certificate"], pooled["paired"])]
    lines += [r"\bottomrule", r"\end{tabularx}", "",
              r"\smallskip\noindent{\footnotesize $U_{\mathrm{grid}}$: exact one-sided Clopper--Pearson bound, registered grid, "
              r"$m{=}1$ (level $1-0.1/11$; admit iff $\le 0.05$); $U_{\mathrm{1}}$: single rule $\gamma=\delta=0.10$; "
              r"b/c: baseline-only / compiled-only contract met; $p_{\mathrm{McN}}$: exact two-sided McNemar.}", "",
              r"\medskip", ""]
    # Panel B (resources) after the adverse panel.
    lines += [r"\begin{tabularx}{\linewidth}{@{}>{\raggedright\arraybackslash}X r r r r r r r r@{}}", r"\toprule",
              r"Repository & \multicolumn{4}{c}{Compiled vs.\ unchanged (\%)} & \multicolumn{4}{c}{Hand-written vs.\ unchanged (\%)} \\",
              r"\cmidrule(lr){2-5}\cmidrule(lr){6-9}",
              r" & Req. & Tok. & Lat. & Cost & Req. & Tok. & Lat. & Cost \\", r"\midrule"]

    def red_row(name: str, red: dict[str, Any]) -> str:
        return (f"{name} & " + " & ".join(pct(red["compiled"][k]) for k in RESOURCES) + " & "
                + " & ".join(pct(red["manual"][k]) for k in RESOURCES) + r" \\")

    for e in run:
        lines.append(red_row(tex(e["repo"]), e["resources"]["reduction_vs_baseline_pct"]))
    if pooled:
        lines += [r"\midrule", red_row("Pooled", pooled["resources"]["reduction_vs_baseline_pct"])]
    lines += [r"\bottomrule", r"\end{tabularx}", ""]
    return "\n".join(lines)


# ----------------------------------------------------------------------------- driver


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def run(results_dir: Path, summary_out: Path | None = None, table_out: Path | None = None, label: str = "") -> dict[str, Any]:
    summary = build_summary(results_dir)
    write_json(summary_out or results_dir / "summary.json", summary)
    table_path = table_out or DEFAULT_TABLE
    table_path.parent.mkdir(parents=True, exist_ok=True)
    table_path.write_text(render_table(summary, label), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--summary-out", type=Path, default=None, help="default: <results-dir>/summary.json")
    parser.add_argument("--table-out", type=Path, default=DEFAULT_TABLE)
    parser.add_argument("--label", default="", help="comment line written into the table (e.g. SYNTHETIC FIXTURE)")
    args = parser.parse_args(argv)
    summary = run(args.results_dir, args.summary_out, args.table_out, args.label)
    if summary["appendix_a3_floor_mismatches"]:
        raise SystemExit("Appendix A.3 floor mismatch: " + "; ".join(summary["appendix_a3_floor_mismatches"]))
    print(f"repositories: {len(summary['repositories'])}; not run: {[n['repo'] for n in summary['not_run']]}")
    for e in summary["repositories"]:
        if e["status"] == "run":
            c = e["certificate"]
            print(f"{e['repo']}: n={c['n']} k={c['k']} U_grid={c['grid_m1']['U']:.4f} "
                  f"U_single={c['single_rule']['U']:.4f} decision={c['decision']}")
    print(f"ledger total: ${summary['ledger']['total_spent_usd']}")


if __name__ == "__main__":
    main()
