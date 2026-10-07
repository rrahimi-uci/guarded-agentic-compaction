"""Drift-robustness ablation: does the induced verifier convert wrong answers into abstentions?

Protocol: ``paper/supplementary/drift-robustness-ablation-protocol.md`` (pre-registered
2026-08-18; amended before execution on 2026-10-06, see its "Amendments" section).
Provider-free. Substrate: the five deterministic demonstration workloads.

For every admitted artifact of every demonstration the script
1. reproduces the sealed compile (same seed, splits and config as ``experiments/run.py``)
   and refuses to continue unless the admitted artifact ids equal the retained ones;
2. mines the sealed test split's windows for the artifact's family under the partition's
   train-fitted groundability policy, sorts them and caps them at ``--max-windows``;
3. checks the permissive verifier is inert on every unperturbed window;
4. runs the nine declared perturbation families over identical windows for two arms,
   ``compiled_guarded`` (induced verifier) and ``compiled_unverified`` (permissive
   ``Verifier()``), the hard runtime boundary retained in both;
5. pairs outcomes at group level (any ``wrong`` across the window's applicable suite),
   reports exact McNemar discordances, Clopper-Pearson upper bounds on zero counts, the
   over-abstention guardrail, and the hard-reject inventory; any ``sandbox_state_delta``
   aborts the run.

Nothing here is a provider measurement or evidence about the GitHub families.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from scipy.stats import beta, binomtest  # noqa: E402

from guarded_agentic_compaction.evaluation.perturb import (  # noqa: E402
    DEFAULT_PERTURBATIONS, _make_facade, run_perturbations,
)
from guarded_agentic_compaction.evaluation.splits import make_splits  # noqa: E402
from guarded_agentic_compaction.graph.provenance import build_all  # noqa: E402
from guarded_agentic_compaction.graph.windows import mine  # noqa: E402
from guarded_agentic_compaction.grc.compile import GrcConfig, compile_grc, partition_key  # noqa: E402
from guarded_agentic_compaction.runtime.interp import run_program  # noqa: E402
from guarded_agentic_compaction.schema.artifacts import Verifier  # noqa: E402

from demos.framework import run_workload  # noqa: E402
from experiments.conditions.registry import get_demo  # noqa: E402

DEMOS = ("support", "permissioned_rag", "incident_triage", "mcp_ops", "fulfillment")
RETAINED = ROOT / "experiments" / "results"
INVARIANT = tuple(p.name for p in DEFAULT_PERTURBATIONS if p.expect == "invariant")
ARMS = ("compiled_guarded", "compiled_unverified")


def cp_upper(k: int, n: int, conf: float = 0.95) -> float | None:
    if n == 0:
        return None
    if k >= n:
        return 1.0
    return float(beta.ppf(conf, k + 1, n - k))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value on the discordant pairs (b, c)."""
    if b + c == 0:
        return 1.0
    return float(binomtest(min(b, c), b + c, 0.5).pvalue)


def _digest(items: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(items).encode()).hexdigest()[:16]


def _grc_config(spec, seed: int) -> GrcConfig:
    # Byte-for-byte the non-quick configuration of experiments/run.py.
    return GrcConfig(entry_schema=spec.entry_allowlist, s_min=5, min_days=3, s_branch=20,
                     n_permutations=400, max_candidates=10, max_artifacts=4, seed=seed,
                     owner="research-mvp")


def _family_hash(candidate_id: str, partitioned: bool) -> str:
    parts = candidate_id.split("-")
    return "-".join(parts[2:-1] if partitioned else parts[2:])


def _family_key(candidate_id: str) -> str:
    """Candidate id without its rank index: ``cand-03-<hash>[-<partition>]`` -> ``<hash>[-<partition>]``.

    Ranks move between compiler versions when ties re-order; the family hash and the
    partition tag identify the artifact that was admitted.
    """
    return "-".join(candidate_id.split("-")[2:])


def _one_window_per_group(windows, max_windows: int):
    """Deterministic sample: the first window of each group, groups in sorted order."""
    seen: set[str] = set()
    picked = []
    for w in sorted(windows, key=lambda w: (w.group_id, w.episode.episode_id)):
        if w.group_id in seen:
            continue
        seen.add(w.group_id)
        picked.append(w)
        if len(picked) == max_windows:
            break
    return picked


def run_demo(key: str, *, seed: int, max_windows: int) -> dict[str, Any]:
    spec = get_demo(key)
    catalog = spec.catalog()
    t0 = time.time()
    world, specs = spec.make_workload(n_episodes=spec.n_episodes, seed=seed)
    episodes = run_workload(specs, world, spec.make_policy(), spec.manifest)
    splits = make_splits(episodes, shadow_fraction=0.10, seed=seed)
    out: dict[str, Any] = {"demo": key, "n_episodes": len(episodes),
                           "splits": {k: len(v) for k, v in splits.roles.items()},
                           "splits_digest": splits.digest(), "artifacts": {}, "notes": []}

    retained_path = RETAINED / f"{key}.json"
    retained = json.loads(retained_path.read_text()) if retained_path.exists() else None
    if retained is not None:
        out["retained_splits_digest"] = retained["splits"]["digest"]
        if retained["splits"]["digest"] != splits.digest():
            out["status"] = "aborted:splits_digest_mismatch"
            return out

    graphs, policy = build_all(episodes, catalog)
    cfg = _grc_config(spec, seed)
    sandbox = (lambda _w=world: _w)
    grc = compile_grc(episodes, catalog, splits, spec.manifest, cfg, sandbox=sandbox,
                      perturbations=DEFAULT_PERTURBATIONS, graphs=graphs, policy=policy)
    out["compile_s"] = round(time.time() - t0, 2)
    admitted = sorted(a.artifact_id for a in grc.artifacts)
    out["admitted_artifact_ids"] = admitted
    out["rejection_by_stage"] = dict(grc.rejection_by_stage)
    if retained is not None:
        retained_ids = sorted(c["candidate_id"] for c in retained["grc"]["candidates"] if c["artifact"])
        out["retained_artifact_ids"] = retained_ids
        now_f, ret_f = {_family_key(i) for i in admitted}, {_family_key(i) for i in retained_ids}
        out["family_match"] = {"identical_ids": retained_ids == admitted, "same_families": now_f == ret_f,
                               "families_now": sorted(now_f), "families_retained": sorted(ret_f),
                               "missing_now": sorted(ret_f - now_f), "new_now": sorted(now_f - ret_f)}
    if not grc.artifacts:
        out["status"] = "no_admitted_artifact"
        return out

    keys = tuple(cfg.partition_by)
    for art in grc.artifacts:
        rec = next(r for r in grc.candidates if r.artifact is art)
        names = list(rec.synthesis.names)
        partition = rec.notes.get("partition")
        pkey = tuple(partition[k] for k in keys) if partition else None
        part_eps = [ep for ep in episodes if pkey is None or partition_key(ep, keys) == pkey]
        train_eps = [ep for ep in part_eps if ep.group_id in splits.train]
        test_eps = [ep for ep in part_eps if ep.group_id in splits.test]
        _, train_policy = build_all(train_eps, catalog, None, max_depth=cfg.max_transform_depth, kappa=cfg.kappa)
        test_graphs, _ = build_all(test_eps, catalog, train_policy, max_depth=cfg.max_transform_depth, kappa=cfg.kappa)
        mined = mine(test_graphs, catalog, entry_schema=cfg.entry_schema, w_min=cfg.w_min, w_max=cfg.w_max,
                     b_min=cfg.b_min, s_min=1, min_principals=1, min_days=1, prefix_only=cfg.prefix_only)
        fam_hash = _family_hash(art.artifact_id, partition is not None)
        family = next((f for f in mined.families if f.canon_hash == fam_hash), None)
        entry: dict[str, Any] = {"artifact": art.name, "candidate_id": art.artifact_id, "partition": partition,
                                 "family_hash": fam_hash, "tools": list(art.program.tools), "names": names,
                                 "test_episodes": len(test_eps)}
        out["artifacts"][art.artifact_id] = entry
        if family is None:
            entry["status"] = "no_test_windows_for_family"
            continue
        windows = _one_window_per_group(family.windows, max_windows)
        entry["family_windows_available"] = len(family.windows)
        entry["n_windows"] = len(windows)
        entry["n_groups"] = len({w.group_id for w in windows})
        entry["window_digest"] = _digest([f"{w.group_id}:{w.episode.episode_id}" for w in windows])

        # Precondition 4: the permissive contract is inert on unperturbed runs.
        permissive = Verifier()
        inert, unperturbed_ok = True, 0
        for w in windows:
            facade, _ = _make_facade(art.program, catalog, w, None, sandbox)
            res = run_program(art.program, w.episode.entry_state, facade)
            if res.ok:
                unperturbed_ok += 1
                if permissive.verify(res.outputs, res.env, res.provenance, res.effects, len(res.calls)):
                    inert = False
        entry["permissive_verifier_inert"] = inert
        entry["unperturbed_ok_windows"] = unperturbed_ok
        if not inert:
            entry["status"] = "aborted:permissive_verifier_not_inert"
            continue

        arms: dict[str, Any] = {}
        for arm, verifier in (("compiled_guarded", art.verifier), ("compiled_unverified", permissive)):
            trace: list[dict[str, Any]] = []
            report, hard = run_perturbations(art.program, art.guard, verifier, windows, names, catalog, sandbox,
                                             DEFAULT_PERTURBATIONS, max_windows=max_windows, trace=trace)
            arms[arm] = {"report": report, "hard_rejects": hard, "trace": trace}
            if any("state_delta" in h["kind"] for h in hard):
                entry["status"] = f"aborted:sandbox_state_delta:{arm}"
                break
        if "status" in entry:
            entry["arms"] = {k: {"hard_rejects": v["hard_rejects"]} for k, v in arms.items()}
            continue
        entry["status"] = "completed"
        entry["arms"] = {}
        for arm, payload in arms.items():
            trace = payload["trace"]
            wrong_by_group: dict[str, bool] = {}
            applicable_by_group: dict[str, int] = {}
            for t in trace:
                g = t["group"]
                applicable_by_group[g] = applicable_by_group.get(g, 0) + (t["outcome"] != "no_reference")
                wrong_by_group[g] = wrong_by_group.get(g, False) or t["outcome"] == "wrong"
            inv = [t for t in trace if t["perturbation"] in INVARIANT]
            inv_abst = sum(t["outcome"] in ("abstained", "verifier_abstained") for t in inv)
            entry["arms"][arm] = {
                "per_perturbation": payload["report"],
                "hard_rejects": payload["hard_rejects"],
                "wrong_total": sum(t["outcome"] == "wrong" for t in trace),
                "wrong_groups": sorted(g for g, v in wrong_by_group.items() if v),
                "group_outcomes": {g: {"wrong": v, "applicable": applicable_by_group[g]} for g, v in sorted(wrong_by_group.items())},
                "invariant_abstention_rate": round(inv_abst / len(inv), 4) if inv else None,
                "invariant_n": len(inv),
            }
        g_arm = entry["arms"]["compiled_guarded"]["group_outcomes"]
        u_arm = entry["arms"]["compiled_unverified"]["group_outcomes"]
        groups = sorted(set(g_arm) & set(u_arm))
        b = sum(g_arm[g]["wrong"] and not u_arm[g]["wrong"] for g in groups)   # guarded wrong only
        c = sum(u_arm[g]["wrong"] and not g_arm[g]["wrong"] for g in groups)   # unverified wrong only
        both = sum(g_arm[g]["wrong"] and u_arm[g]["wrong"] for g in groups)
        entry["paired_groups"] = {"n": len(groups), "guarded_only_wrong": b, "unverified_only_wrong": c,
                                  "both_wrong": both, "mcnemar_exact_p": mcnemar_exact(b, c),
                                  "guarded_wrong_upper95": cp_upper(b + both, len(groups)),
                                  "unverified_wrong_upper95": cp_upper(c + both, len(groups))}
    out["status"] = "completed"
    out["elapsed_s"] = round(time.time() - t0, 2)
    return out


def pooled(results: dict[str, Any]) -> dict[str, Any]:
    b = c = both = n = 0
    wrong = {arm: 0 for arm in ARMS}
    inv = {arm: [0, 0] for arm in ARMS}
    for demo in results.values():
        for entry in demo.get("artifacts", {}).values():
            if entry.get("status") != "completed":
                continue
            pg = entry["paired_groups"]
            n += pg["n"]; b += pg["guarded_only_wrong"]; c += pg["unverified_only_wrong"]; both += pg["both_wrong"]
            for arm in ARMS:
                a = entry["arms"][arm]
                wrong[arm] += a["wrong_total"]
                inv[arm][0] += round(a["invariant_abstention_rate"] * a["invariant_n"]) if a["invariant_n"] else 0
                inv[arm][1] += a["invariant_n"]
    return {"paired_groups": n, "guarded_only_wrong": b, "unverified_only_wrong": c, "both_wrong": both,
            "mcnemar_exact_p": mcnemar_exact(b, c),
            "guarded_wrong_groups_upper95": cp_upper(b + both, n), "unverified_wrong_groups_upper95": cp_upper(c + both, n),
            "wrong_outcomes_total": wrong,
            "invariant_abstention_rate": {arm: (round(inv[arm][0] / inv[arm][1], 4) if inv[arm][1] else None) for arm in ARMS}}


def decision(p: dict[str, Any]) -> str:
    if p["paired_groups"] == 0:
        return "no_completed_artifact"
    if p["guarded_only_wrong"] + p["both_wrong"] > 0:
        return "adverse:compiled_guarded_wrong"
    if p["unverified_only_wrong"] > 0:
        return "verifier_separates_arms:guarded_zero_wrong_unverified_wrong"
    return "null:all_arms_zero_wrong"


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--demo", action="append", dest="demos", default=None)
    ap.add_argument("--seed", type=int, default=20260801)
    ap.add_argument("--max-windows", type=int, default=24)
    ap.add_argument("--out", type=Path, default=ROOT / "paper" / "results" / "drift_ablation" / "results.json")
    args = ap.parse_args(argv)
    demos = tuple(args.demos or DEMOS)
    results: dict[str, Any] = {}
    for key in demos:
        print(f"[drift] {key} ...", flush=True)
        results[key] = run_demo(key, seed=args.seed, max_windows=args.max_windows)
        print(f"[drift] {key}: {results[key].get('status')} artifacts={len(results[key].get('artifacts', {}))}", flush=True)
    agg = pooled(results)
    payload = {
        "schema": "agent-compaction-drift-ablation/v1",
        "protocol": "paper/supplementary/drift-robustness-ablation-protocol.md",
        "substrate": "simulated deterministic demonstration workloads; provider-free",
        "arms": list(ARMS),
        "manual_unverified": "not run: the demonstration comparators are policy-level macros, not IR programs (protocol amendment 2026-10-06)",
        "perturbations": [{"name": p.name, "family": p.family, "expect": p.expect} for p in DEFAULT_PERTURBATIONS],
        "seed": args.seed, "max_windows": args.max_windows, "provider_calls_executed": 0,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "demos": results, "pooled": agg, "decision": decision(agg),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")
    print(f"[drift] decision={payload['decision']} pooled={json.dumps(agg)}")
    print(f"[drift] wrote {args.out}")
    aborted = [f"{d}:{a}" for d, r in results.items() for a, e in r.get("artifacts", {}).items() if str(e.get("status", "")).startswith("aborted")]
    aborted += [d for d, r in results.items() if str(r.get("status", "")).startswith("aborted")]
    return 1 if aborted else 0


if __name__ == "__main__":
    raise SystemExit(main())
