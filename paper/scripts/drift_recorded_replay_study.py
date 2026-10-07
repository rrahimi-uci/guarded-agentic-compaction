"""Drift-robustness ablation on the 90 retained GitHub held-out records, provider-free.

Protocol: ``paper/supplementary/drift-recorded-replay-protocol.md`` (pre-registered
2026-10-06). Three arms over identical reconstructed windows: the retained artifact with its
induced verifier, the same program with a permissive verifier, and the family's hand-written
pre-model plan with a permissive verifier. Tool results come from the revision-pinned snapshot
through the same sandbox the challenge recompile uses. Output:
``paper/results/drift_recorded_replay/results.json``.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from scipy.stats import beta, binomtest  # noqa: E402

import recompile_with_challenge as rwc  # noqa: E402
from guarded_agentic_compaction.evaluation.perturb import DEFAULT_PERTURBATIONS, _make_facade, run_perturbations  # noqa: E402
from guarded_agentic_compaction.graph.provenance import build_all  # noqa: E402
from guarded_agentic_compaction.graph.windows import mine  # noqa: E402
from guarded_agentic_compaction.runtime.interp import run_program  # noqa: E402
from guarded_agentic_compaction.schema.artifacts import Verifier  # noqa: E402

FAMILIES = ("issue_type", "pr_outcome", "backlog_attention")
ARMS = ("compiled_guarded", "compiled_unverified", "manual_unverified")
INVARIANT = tuple(p.name for p in DEFAULT_PERTURBATIONS if p.expect == "invariant")
MODEL = rwc.MODEL


def cp_upper(k: int, n: int, conf: float = 0.95) -> float | None:
    if n == 0:
        return None
    if k >= n:
        return 1.0
    return float(beta.ppf(conf, k + 1, n - k))


def mcnemar_exact(b: int, c: int) -> float:
    if b + c == 0:
        return 1.0
    return float(binomtest(min(b, c), b + c, 0.5).pvalue)


def holm(pvalues: dict[str, float]) -> dict[str, float]:
    """Holm step-down adjusted p-values."""
    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(items)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (name, p) in enumerate(items):
        running = max(running, min(1.0, (m - rank) * p))
        adjusted[name] = running
    return adjusted


def _digest(items: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(items).encode()).hexdigest()[:16]


def _family_hash(candidate_id: str) -> str:
    return "-".join(candidate_id.split("-")[2:])


def _load_family(name: str) -> dict[str, Any]:
    """Recompile the retained artifact, rebuild the sandbox, reconstruct held-out episodes."""
    import github_live_study as fixed

    retained = json.loads(rwc.ARTIFACTS[name]["retained"].read_text(encoding="utf-8"))
    baseline_rows = [r for r in retained["results"] if r["condition"] == "baseline" and int(r.get("repeat", 0)) == 0]
    captured, record, _retained, audit = rwc.recompile(name, with_challenge=False)
    art = next(a for a in captured.artifacts if a.artifact_id == record["artifact"]["artifact_id"])
    rec = next(r for r in captured.candidates if r.artifact is art)
    assert art.artifact_id == rwc.ARTIFACTS[name]["artifact_id"], (art.artifact_id, rwc.ARTIFACTS[name]["artifact_id"])
    assert art.gate.n_accepted == 92 and art.gate.observed_violations == 0, art.gate

    if name == "issue_type":
        import github_optimizer_head_to_head as h2h
        import recurrence_only_ablation as shared
        import second_model_replication as smr

        store, store_audit = shared.load_store()
        catalog = fixed.make_catalog()
        tools = fixed.make_tools(store)
        manifest = fixed.make_manifest(MODEL, tools, catalog, smr.TASK_DESIGN)
        episodes = [run.episode for run in smr.reconstruct_discovery({"results": baseline_rows}, store=store, manifest=manifest)]
        execute = lambda tool, args: shared.execute_issue_snapshot(store, tool, args)  # noqa: E731
        parquet_sha = store_audit["parquet_sha256"]
        # The head-to-head script's manual plan packages a composite that needs a
        # batchable catalog; the retained artifact's catalog does not declare one.
        # The arm needs only the program and its pins, so build the same three
        # calls (record, labels, comments with limit 3) without packaging.
        from guarded_agentic_compaction.grc.dsl import Const, Expr
        from guarded_agentic_compaction.grc.program import CallStep, Program
        from guarded_agentic_compaction.runtime.manual import ManualPreModelPlan
        from guarded_agentic_compaction.schema.artifacts import HardGuard

        program = Program(
            theta=("issue_number",),
            steps=[
                CallStep(var="record", tool="issue_get_record", args={"issue_number": Expr("z.issue_number", ())}),
                CallStep(var="labels", tool="issue_get_labels", args={"issue_number": Expr("z.issue_number", ())}),
                CallStep(var="comments", tool="issue_get_comments",
                         args={"issue_number": Expr("z.issue_number", ()), "limit": Const(3)}),
            ],
            outputs={"record": Expr("record", ()), "labels": Expr("labels", ()), "comments": Expr("comments", ())},
            removed_requests=3,
        )
        pins = {k: getattr(manifest, k) for k in ("model", "prompt_hash", "tools_hash", "policy_hash",
                                                   "guardrail_hash", "effect_catalog_version", "entry_contract_version")}
        manual = ManualPreModelPlan(name="drift-replay-manual-issue-type", program=program,
                                    source_compatibility_key=manifest.compatibility_key(),
                                    guard=HardGuard(manifest_pins=pins, allowed_effects=("READ_LOCAL",)),
                                    verifier=Verifier(), owner="paper-drift-replay")
        del h2h
    else:
        import github_workflow_family_study as fam

        spec = fam.FAMILIES[name]
        store, _store_audit = fam.load_store()
        catalog = fam.make_catalog(spec)
        tools = fam.make_tools(spec, store)
        source_manifest = fam.make_manifest(spec, MODEL, tools, catalog, "source", instructions=spec.discovery_prompt)
        continuation_manifest = fam.make_manifest(spec, MODEL, (), catalog, "pre-model", instructions=spec.prompt)
        episodes = [run.episode for run in fam.reconstruct_discovery(spec, {"results": baseline_rows}, store=store, manifest=source_manifest)]
        execute = lambda tool, args: fam.execute_snapshot(spec, store, tool, args)  # noqa: E731
        parquet_sha = fixed.HF_PARQUET_SHA256
        manual = fam.make_manual_plan(spec, catalog=catalog, source_manifest=source_manifest, continuation_manifest=continuation_manifest)

    worlds: list[Any] = []

    def sandbox() -> Any:
        world = rwc.SnapshotWorld(execute, parquet_sha256=parquet_sha, n_records=len(store))
        worlds.append(world)
        return world

    return {"artifact": art, "names": list(rec.synthesis.names), "config": captured.config, "policy": captured.policy,
            "catalog": catalog, "episodes": episodes, "sandbox": sandbox, "worlds": worlds, "execute": execute,
            "manual": manual, "baseline_rows": baseline_rows, "retained_artifact_id": record["artifact"]["artifact_id"]}


def _windows_for(art: Any, ctx: dict[str, Any]) -> tuple[list[Any], int]:
    cfg = ctx["config"]
    graphs, _ = build_all(ctx["episodes"], ctx["catalog"], ctx["policy"], max_depth=cfg.max_transform_depth, kappa=cfg.kappa)
    mined = mine(graphs, ctx["catalog"], entry_schema=cfg.entry_schema, w_min=cfg.w_min, w_max=cfg.w_max, b_min=cfg.b_min,
                 s_min=1, min_principals=1, min_days=1, prefix_only=cfg.prefix_only)
    fam_hash = _family_hash(art.artifact_id)
    family = next((f for f in mined.families if f.canon_hash == fam_hash), None)
    if family is None:
        return [], 0
    picked, seen = [], set()
    for w in sorted(family.windows, key=lambda w: (w.group_id, w.episode.episode_id)):
        if w.group_id in seen:
            continue
        seen.add(w.group_id)
        picked.append(w)
    return picked, len(family.windows)


def _applicability(ctx: dict[str, Any], windows: Sequence[Any]) -> dict[str, Any]:
    """Share of recorded calls each transform actually changes, per perturbation and tool."""
    rows_by_number = {int(r["issue_number"]): r for r in ctx["baseline_rows"]}
    calls: list[tuple[str, dict[str, Any], Any]] = []
    for w in windows:
        number = int(w.group_id.rsplit(":", 1)[1])
        row = rows_by_number[number]
        for tool, args in zip(row["tool_sequence"], row["tool_arguments"]):
            calls.append((str(tool), dict(args), ctx["execute"](str(tool), dict(args))))
    out: dict[str, Any] = {}
    for pert in DEFAULT_PERTURBATIONS:
        per_tool: dict[str, dict[str, int]] = {}
        for tool, args, result in calls:
            slot = per_tool.setdefault(tool, {"calls": 0, "changed": 0})
            slot["calls"] += 1
            if pert.transform is None:
                slot["changed"] += 1  # injected failure: always applicable
            else:
                changed = pert.transform(tool, dict(args), copy.deepcopy(result)) != result
                slot["changed"] += int(changed)
        out[pert.name] = {"expect": pert.expect, "injected": pert.transform is None, "per_tool": per_tool,
                          "applicable": any(v["changed"] > 0 for v in per_tool.values())}
    return out


def _arm_summary(trace: list[dict[str, Any]], report: dict[str, Any], hard: list[dict[str, Any]], applicable: set[str]) -> dict[str, Any]:
    wrong_by_group: dict[str, bool] = {}
    for t in trace:
        if t["perturbation"] not in applicable:
            continue
        g = t["group"]
        wrong_by_group[g] = wrong_by_group.get(g, False) or t["outcome"] == "wrong"
    inv = [t for t in trace if t["perturbation"] in INVARIANT]
    inv_abst = sum(t["outcome"] in ("abstained", "verifier_abstained") for t in inv)
    return {"per_perturbation": report, "hard_rejects": hard,
            "wrong_total": sum(t["outcome"] == "wrong" for t in trace),
            "wrong_total_applicable": sum(t["outcome"] == "wrong" for t in trace if t["perturbation"] in applicable),
            "wrong_groups": sorted(g for g, v in wrong_by_group.items() if v),
            "group_outcomes": {g: v for g, v in sorted(wrong_by_group.items())},
            "invariant_abstention_rate": round(inv_abst / len(inv), 4) if inv else None, "invariant_n": len(inv)}


def _pair(a: dict[str, bool], b: dict[str, bool]) -> dict[str, Any]:
    groups = sorted(set(a) & set(b))
    only_a = sum(a[g] and not b[g] for g in groups)
    only_b = sum(b[g] and not a[g] for g in groups)
    both = sum(a[g] and b[g] for g in groups)
    return {"n": len(groups), "first_only_wrong": only_a, "second_only_wrong": only_b, "both_wrong": both,
            "mcnemar_exact_p": mcnemar_exact(only_a, only_b),
            "first_wrong_upper95": cp_upper(only_a + both, len(groups)), "second_wrong_upper95": cp_upper(only_b + both, len(groups))}


def run_family(name: str) -> dict[str, Any]:
    t0 = time.time()
    ctx = _load_family(name)
    art, manual = ctx["artifact"], ctx["manual"]
    out: dict[str, Any] = {"family": name, "artifact_id": art.artifact_id, "retained_artifact_id": ctx["retained_artifact_id"],
                           "program_tools": list(art.program.tools), "manual_tools": list(manual.program.tools),
                           "n_heldout_records": len(ctx["baseline_rows"]), "names": ctx["names"]}
    windows, available = _windows_for(art, ctx)
    out["n_windows"] = len(windows)
    out["family_windows_available"] = available
    out["excluded_records"] = len(ctx["baseline_rows"]) - len(windows)
    out["window_digest"] = _digest([f"{w.group_id}:{w.episode.episode_id}" for w in windows])
    if not windows:
        out["status"] = "no_windows_for_family"
        return out
    out["applicability"] = _applicability(ctx, windows)
    applicable = {p for p, v in out["applicability"].items() if v["applicable"]}
    out["applicable_perturbations"] = sorted(applicable)

    permissive = Verifier()
    checks: dict[str, Any] = {}
    for label, program in (("compiled", art.program), ("manual", manual.program)):
        ok_n, inert = 0, True
        for w in windows:
            facade, _ = _make_facade(program, ctx["catalog"], w, None, ctx["sandbox"])
            res = run_program(program, w.episode.entry_state, facade)
            if res.ok:
                ok_n += 1
                if permissive.verify(res.outputs, res.env, res.provenance, res.effects, len(res.calls)):
                    inert = False
        checks[label] = {"unperturbed_ok_windows": ok_n, "permissive_verifier_inert": inert}
    out["preconditions"] = checks
    if not all(c["permissive_verifier_inert"] for c in checks.values()):
        out["status"] = "aborted:permissive_verifier_not_inert"
        return out

    arm_specs = (("compiled_guarded", art.program, art.guard, art.verifier, ctx["names"]),
                 ("compiled_unverified", art.program, art.guard, permissive, ctx["names"]),
                 ("manual_unverified", manual.program, manual.guard, permissive, list(manual.program.outputs)))
    out["arms"] = {}
    for arm, program, guard, verifier, names in arm_specs:
        trace: list[dict[str, Any]] = []
        report, hard = run_perturbations(program, guard, verifier, windows, names, ctx["catalog"], ctx["sandbox"],
                                         DEFAULT_PERTURBATIONS, max_windows=len(windows), trace=trace)
        if any("state_delta" in h["kind"] for h in hard):
            out["status"] = f"aborted:sandbox_state_delta:{arm}"
            out["arms"][arm] = {"hard_rejects": hard}
            return out
        out["arms"][arm] = _arm_summary(trace, report, hard, applicable)
    g = {k: v["group_outcomes"] for k, v in out["arms"].items()}
    out["comparisons"] = {"verifier:guarded_vs_unverified": _pair(g["compiled_guarded"], g["compiled_unverified"]),
                          "program:unverified_vs_manual": _pair(g["compiled_unverified"], g["manual_unverified"])}
    out["holm_adjusted_p"] = holm({k: v["mcnemar_exact_p"] for k, v in out["comparisons"].items()})
    out["sandbox"] = {"worlds_created": len(ctx["worlds"]), "tool_calls": sum(len(w.calls) for w in ctx["worlds"]),
                      "state_digest": ctx["worlds"][0].state_digest() if ctx["worlds"] else None}
    out["status"] = "completed"
    out["elapsed_s"] = round(time.time() - t0, 2)
    return out


def pooled(families: dict[str, Any]) -> dict[str, Any]:
    done = [f for f in families.values() if f.get("status") == "completed"]
    g = {arm: {} for arm in ARMS}
    wrong = {arm: 0 for arm in ARMS}
    inv = {arm: [0, 0] for arm in ARMS}
    for f in done:
        for arm in ARMS:
            a = f["arms"][arm]
            g[arm].update({f"{f['family']}:{k}": v for k, v in a["group_outcomes"].items()})
            wrong[arm] += a["wrong_total_applicable"]
            inv[arm][0] += round(a["invariant_abstention_rate"] * a["invariant_n"]) if a["invariant_n"] else 0
            inv[arm][1] += a["invariant_n"]
    comps = {"verifier:guarded_vs_unverified": _pair(g["compiled_guarded"], g["compiled_unverified"]),
             "program:unverified_vs_manual": _pair(g["compiled_unverified"], g["manual_unverified"])}
    return {"families_completed": [f["family"] for f in done], "paired_records": len(g["compiled_guarded"]),
            "wrong_records": {arm: sum(v.values()) for arm, v in g.items()}, "wrong_outcomes_applicable": wrong,
            "wrong_upper95": {arm: cp_upper(sum(v.values()), len(v)) for arm, v in g.items()},
            "comparisons": comps, "holm_adjusted_p": holm({k: v["mcnemar_exact_p"] for k, v in comps.items()}),
            "invariant_abstention_rate": {arm: (round(inv[arm][0] / inv[arm][1], 4) if inv[arm][1] else None) for arm in ARMS}}


def decision(p: dict[str, Any]) -> str:
    if p["paired_records"] == 0:
        return "no_completed_family"
    w = p["wrong_records"]
    if w["compiled_guarded"] > 0:
        return "adverse:compiled_guarded_wrong"
    if w["compiled_unverified"] > 0:
        return "verifier_separates_arms:guarded_zero_wrong_unverified_wrong"
    if w["manual_unverified"] > 0:
        return "program_separates_arms:compiled_zero_wrong_manual_wrong"
    return "null:all_arms_zero_wrong"


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--family", action="append", dest="families", default=None)
    ap.add_argument("--out", type=Path, default=ROOT / "paper" / "results" / "drift_recorded_replay" / "results.json")
    args = ap.parse_args(argv)
    families: dict[str, Any] = {}
    for name in tuple(args.families or FAMILIES):
        print(f"[drift-replay] {name} ...", flush=True)
        families[name] = run_family(name)
        print(f"[drift-replay] {name}: {families[name].get('status')} windows={families[name].get('n_windows')}", flush=True)
    agg = pooled(families)
    payload = {"schema": "agent-compaction-drift-recorded-replay/v1",
               "protocol": "paper/supplementary/drift-recorded-replay-protocol.md",
               "substrate": "retained primary held-out records, episodes reconstructed on the revision-pinned snapshot; provider-free",
               "arms": list(ARMS), "model_of_retained_artifacts": MODEL,
               "perturbations": [{"name": p.name, "family": p.family, "expect": p.expect} for p in DEFAULT_PERTURBATIONS],
               "provider_calls_executed": 0, "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "families": families, "pooled": agg, "decision": decision(agg)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")
    print(f"[drift-replay] decision={payload['decision']}")
    print(f"[drift-replay] pooled={json.dumps({k: v for k, v in agg.items() if k != 'comparisons'})}")
    print(f"[drift-replay] wrote {args.out}")
    return 1 if any(str(f.get("status", "")).startswith("aborted") for f in families.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
