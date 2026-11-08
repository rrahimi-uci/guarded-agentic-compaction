"""Same-IR compiler funnel: GAC against support-only, recurrence-only and stats-only policies.

Protocol: ``paper/supplementary/compiler-funnel-protocol.md`` (registered before any policy other
than the shipped one was run).  Provider-free: every pass replays recorded tool results from the
pinned snapshots; nothing is dispatched.

The four policies are the shipped compiler with two switches:

* statistical admission on (``alpha = 0.05``) or off (``alpha = 1.0``: the gate accepts every
  calibrated candidate; calibration replay still runs and its counts are kept);
* grounding on (Algorithm 3 refuses a slot with no witness) or off (a majority-literal fallback:
  the slot is bound to its modal training value).

Everything else -- mining, guard and verifier induction, the recorded-replay challenge, dominance
selection -- is the shipped code, reached through the production entry points of the retained
studies so that splits and manifests are identical.  The P1 pass must reproduce every retained
decision; a mismatch stops the study.

Commands: ``run`` (all cohorts, all policies), ``table``.
"""

from __future__ import annotations

import argparse
import functools
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import github_live_study as fixed  # noqa: E402
import github_workflow_family_study as fam  # noqa: E402
import recurrence_only_ablation as issue  # noqa: E402
import second_model_replication as second  # noqa: E402
import time_forward_pr_outcome_study as tf  # noqa: E402
from guarded_agentic_compaction.grc import synthesize as grc_synth  # noqa: E402
from guarded_agentic_compaction.grc.compile import CompileResult, GrcConfig, compile_grc  # noqa: E402
from guarded_agentic_compaction.grc.dsl import Const  # noqa: E402
from guarded_agentic_compaction.grc.synthesize import BindingResult  # noqa: E402

OUT_DIR = ROOT / "paper" / "results" / "compiler_funnel"
RESULTS_PATH = OUT_DIR / "results.json"
TABLE_PATH = ROOT / "paper" / "iclr" / "tables" / "compiler_funnel.tex"
PROTOCOL_PATH = ROOT / "paper" / "supplementary" / "compiler-funnel-protocol.md"
MULTIREPO_RESULTS = ROOT / "paper" / "results" / "multirepo_end_to_end"
DEFAULT_MULTIREPO_SNAPSHOTS = Path(
    "/Users/rezarahimi/Documents/GitHub/personal/guarded-agentic-compaction/benchmarks/.cache/multirepo_e2e"
)
MODEL = tf.MODEL
SNAPSHOT_DATE = "2026-11-08"

#: policy name -> (grounding on?, alpha)
POLICIES: dict[str, tuple[bool, float]] = {
    "full": (True, 0.05),
    "support_only": (True, 1.0),
    "recurrence_only": (False, 1.0),
    "stats_only": (False, 0.05),
}
PRIMARY = ("issue_type", "pr_outcome", "backlog_attention")
RETAINED_PRIMARY = {
    "issue_type": ROOT / "paper/results/github_natural_replication/results.json",
    "pr_outcome": ROOT / "paper/results/github_workflow_families/pr_outcome/pilot_v1/results.json",
    "backlog_attention": ROOT / "paper/results/github_workflow_families/backlog_attention/final/results.json",
}


# ---------------------------------------------------------------------------
# the two switches
# ---------------------------------------------------------------------------


def _key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def majority_fallback(original: Callable[..., BindingResult], log: list[dict[str, Any]]) -> Callable[..., BindingResult]:
    """Grounding off: when Algorithm 3 refuses a slot, bind it to its modal training literal."""

    @functools.wraps(original)
    def wrapper(slot_path, envs, targets, groups, *args, **kwargs):
        res = original(slot_path, envs, targets, groups, *args, **kwargs)
        if res.ok or not targets:
            return res
        counts = Counter(_key(t) for t in targets)
        best_key = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        value = next(t for t in targets if _key(t) == best_key)
        log.append({
            "slot": slot_path,
            "grounding_reason": res.reason,
            "modal_value": value,
            "modal_share": counts[best_key] / len(targets),
            "n_targets": len(targets),
            "distinct_values": len(counts),
        })
        return BindingResult(Const(value), reason="", ambiguous_alternatives=res.ambiguous_alternatives)

    return wrapper


def config_factory(alpha: float, **extra: Any) -> Callable[..., GrcConfig]:
    """Replace the study modules' ``GrcConfig`` so that alpha (and any extra field) is forced."""

    def make(**kwargs: Any) -> GrcConfig:
        kwargs = dict(kwargs)
        kwargs["alpha"] = alpha
        kwargs.update(extra)
        return GrcConfig(**kwargs)

    return make


class Patched:
    """Context manager: force alpha, optionally disable grounding, and capture CompileResults."""

    def __init__(self, policy: str, *, freeze: bool = False):
        self.grounding, self.alpha = POLICIES[policy]
        self.freeze = freeze
        self.results: list[CompileResult] = []
        self.majority_log: list[dict[str, Any]] = []

    def __enter__(self) -> "Patched":
        self._saved = (fam.GrcConfig, fixed.GrcConfig, fam.compile_grc, fixed.compile_grc, grc_synth.synthesize_binding)
        extra = {"freeze_one_candidate_before_calibration": True} if self.freeze else {}
        fam.GrcConfig = fixed.GrcConfig = config_factory(self.alpha, **extra)

        def capture(*args: Any, **kwargs: Any) -> CompileResult:
            res = compile_grc(*args, **kwargs)
            self.results.append(res)
            return res

        fam.compile_grc = fixed.compile_grc = capture
        if not self.grounding:
            grc_synth.synthesize_binding = majority_fallback(self._saved[4], self.majority_log)
        return self

    def __exit__(self, *exc: Any) -> None:
        fam.GrcConfig, fixed.GrcConfig, fam.compile_grc, fixed.compile_grc, grc_synth.synthesize_binding = self._saved


# ---------------------------------------------------------------------------
# serialization
# ---------------------------------------------------------------------------


def _binding_repr(binding: Any) -> str:
    return repr(binding)


def serialize(res: CompileResult, *, error: str | None) -> dict[str, Any]:
    candidates = []
    for c in res.candidates:
        d = c.as_dict()
        d["synthesis_reason"] = c.synthesis.reason if c.synthesis else None
        d["slot_reasons"] = dict(c.synthesis.slot_reasons) if c.synthesis else {}
        program = c.synthesis.program if c.synthesis and c.synthesis.program is not None else None
        d["program"] = (
            [{"var": s.var, "tool": s.tool, "args": {k: _binding_repr(v) for k, v in sorted(s.args.items())}}
             for s in program.steps] if program is not None else None
        )
        d["challenge"] = (
            {"ok": c.challenge.ok, "recorded_ok": c.challenge.recorded.ok,
             "hard_rejects": [h.get("kind") for h in c.challenge.hard_rejects]}
            if c.challenge else None
        )
        d["gate"] = (
            {"alpha": c.gate.alpha, "delta": c.gate.delta, "threshold": c.gate.threshold, "retire": c.gate.retire,
             "n_calibration_groups": c.gate.n_calibration_groups, "n_accepted": c.gate.n_accepted,
             "observed_violations": c.gate.observed_violations, "risk_upper_bound": c.gate.risk_upper_bound,
             "coverage": c.gate.coverage}
            if c.gate else None
        )
        candidates.append(d)
    mining = res.mining
    return {
        "error": error,
        "artifacts": [
            {"name": a.name, "artifact_id": a.artifact_id,
             "tools": [s.tool for s in a.program.steps] if a.program is not None else None,
             "removed_requests": a.evidence.removed_requests, "support_groups": a.evidence.support_groups,
             "gate_retire": a.gate.retire, "gate_risk_upper_bound": a.gate.risk_upper_bound,
             "gate_observed_violations": a.gate.observed_violations, "gate_n_calibration_groups": a.gate.n_calibration_groups}
            for a in res.artifacts
        ],
        "candidates": candidates,
        "rejection_by_stage": dict(res.rejection_by_stage),
        "mining": None if mining is None else {
            "n_windows": mining.n_windows, "n_episodes": mining.n_episodes,
            "blocked": {str(k): v for k, v in mining.blocked.items()},
            "blocked_by_tool": {str(k): v for k, v in mining.blocked_by_tool.items()},
            "families": [{"tools": list(f.tools), "support": f.support} for f in mining.families],
            "rejected_families": [{"tools": list(f.tools), "reason": r} for f, r in mining.rejected_families],
        },
        "config": {k: v for k, v in res.config.__dict__.items()} if res.config is not None and hasattr(res.config, "__dict__")
        else ({f: getattr(res.config, f) for f in res.config.__slots__} if res.config is not None else None),  # type: ignore[attr-defined]
    }


# ---------------------------------------------------------------------------
# cohorts
# ---------------------------------------------------------------------------


def primary_inputs(name: str, stores: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct a primary family exactly as generalization_gate_study.build_runtime does."""

    checkpoint = json.loads(gg_source_paths()[name].read_text(encoding="utf-8"))
    if name == "issue_type":
        store = stores["issue_type"]
        tools, catalog = fixed.make_tools(store), fixed.make_catalog()
        manifest = fixed.make_manifest(MODEL, tools, catalog, second.TASK_DESIGN)
        discovery = second.reconstruct_discovery(checkpoint, store=store, manifest=manifest)
        return {"kind": "issue_type", "discovery": discovery, "catalog": catalog, "tools": tools}
    store = stores["family"]
    spec = fam.FAMILIES[name]
    tools, catalog = fam.make_tools(spec, store), fam.make_catalog(spec)
    manifest = fam.make_manifest(spec, MODEL, tools, catalog, "source")
    continuation = fam.make_manifest(spec, MODEL, (), catalog, "pre-model")
    discovery = fam.reconstruct_discovery(spec, checkpoint, store=store, manifest=manifest)
    return {"kind": "family", "spec": spec, "discovery": discovery, "catalog": catalog,
            "source_manifest": manifest, "continuation_manifest": continuation}


def gg_source_paths() -> dict[str, Path]:
    return {
        "issue_type": ROOT / "paper/results/github_natural_replication/discovery_checkpoint.json",
        "pr_outcome": fam.OUT_ROOT / "pr_outcome/pilot_v1/discovery_checkpoint.json",
        "backlog_attention": fam.OUT_ROOT / "backlog_attention/final/discovery_checkpoint.json",
    }


def compile_with(policy: str, inputs: dict[str, Any], *, freeze: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    error = None
    with Patched(policy, freeze=freeze) as patched:
        try:
            if inputs["kind"] == "issue_type":
                second.compile_for_model(inputs["discovery"], model=MODEL, catalog=inputs["catalog"], tools=inputs["tools"])
            else:
                fam.compile_artifact(inputs["spec"], inputs["discovery"], catalog=inputs["catalog"],
                                     source_manifest=inputs["source_manifest"],
                                     continuation_manifest=inputs["continuation_manifest"])
        except RuntimeError as exc:  # "compiler emitted no admitted artifact" is a result, not a failure
            error = str(exc).splitlines()[0]
        if not patched.results:
            raise SystemExit(f"{policy}: compile_grc was not reached ({error})")
        out = serialize(patched.results[-1], error=error)
    out["majority_bindings"] = patched.majority_log
    out["policy"] = policy
    out["grounding"] = POLICIES[policy][0]
    out["alpha"] = POLICIES[policy][1]
    out["runtime_seconds"] = round(time.perf_counter() - started, 2)
    return out


def retained_primary(name: str) -> dict[str, Any] | None:
    path = RETAINED_PRIMARY[name]
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    comp = data.get("compiler") or data.get("compilation") or {}
    artifact = comp.get("artifact") or {}
    return {
        "path": str(path.relative_to(ROOT)),
        "rejection_by_stage": comp.get("rejection_by_stage"),
        "artifact_tools": _artifact_tools(artifact),
        "artifact_id": artifact.get("artifact_id"),
    }


def _artifact_tools(artifact: dict[str, Any]) -> list[str] | None:
    program = artifact.get("program") or {}
    steps = program.get("steps") if isinstance(program, dict) else None
    if steps:
        return [s.get("tool") for s in steps]
    return None


def retained_multirepo(repo_dir: Path) -> dict[str, Any] | None:
    path = repo_dir / "compile.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    comp = data.get("compilation") or {}
    artifact = comp.get("artifact") or {}
    return {"path": str(path.relative_to(ROOT)), "status": data.get("status"),
            "rejection_by_stage": comp.get("rejection_by_stage"), "artifact_tools": _artifact_tools(artifact),
            "artifact_id": artifact.get("artifact_id")}


def reproduces(p1: dict[str, Any], retained: dict[str, Any] | None) -> dict[str, Any]:
    if retained is None:
        return {"checked": False}
    ours_tools = [a["tools"] for a in p1["artifacts"] if not a["gate_retire"]]
    ours_ids = [a["artifact_id"] for a in p1["artifacts"] if not a["gate_retire"]]
    same_tools = retained["artifact_tools"] in ours_tools if retained["artifact_tools"] else None
    same_id = retained["artifact_id"] in ours_ids if retained["artifact_id"] else None
    same_stages = (retained["rejection_by_stage"] == p1["rejection_by_stage"]) if retained["rejection_by_stage"] is not None else None
    ok = all(v is not False for v in (same_tools, same_id, same_stages))
    return {"checked": True, "same_artifact_tools": same_tools, "same_artifact_id": same_id,
            "same_rejection_by_stage": same_stages, "ok": ok, "retained": retained}


def divergence(by_policy: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Candidates some policy emits that P1 does not."""

    p1 = {c["candidate_id"].split("-", 2)[-1]: c for c in by_policy["full"]["candidates"]}
    out = []
    for policy, res in by_policy.items():
        if policy == "full":
            continue
        for c in res["candidates"]:
            if c["stage"] != "emitted":
                continue
            h = c["candidate_id"].split("-", 2)[-1]
            base = p1.get(h)
            if base is not None and base["stage"] == "emitted":
                continue
            out.append({
                "policy": policy, "candidate": c["candidate_id"], "tools": c["tools"],
                "removed_requests": c["removed_requests"],
                "full_stage": base["stage"] if base else "absent", "full_rejected": base["rejected"] if base else None,
                "program": c["program"],
                "calibration_replay": {k: c["notes"].get(k) for k in (
                    "gate_calibration_samples", "gate_calibration_violations", "gate_calibration_unproductive",
                    "gate_calibration_reasons", "gate_dev_samples", "gate_dev_violations", "gate_dev_unproductive",
                    "gate_dev_reasons")},
                "gate": c["gate"],
            })
    return out


def run(multirepo_root: Path, cohorts: list[str] | None) -> dict[str, Any]:
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    stores = {"family": fam.load_store()[0], "issue_type": issue.load_store()[0]}
    wanted = set(cohorts) if cohorts else None
    for name in PRIMARY:
        if wanted and name not in wanted:
            continue
        print(f"funnel: {name} ...", flush=True)
        inputs = primary_inputs(name, stores)
        by_policy = {p: compile_with(p, inputs) for p in POLICIES}
        rep = reproduces(by_policy["full"], retained_primary(name))
        if rep.get("checked") and not rep["ok"]:
            raise SystemExit(f"{name}: P1 does not reproduce the retained decision: {rep}")
        rows.append({"cohort": name, "kind": "primary", "n_discovery": len(inputs["discovery"]),
                     "reproduction": rep, "policies": by_policy, "divergence": divergence(by_policy)})
        _print_row(rows[-1])
    repos = sorted(d for d in MULTIREPO_RESULTS.iterdir() if d.is_dir() and (d / "discovery_checkpoint.json").exists())
    for repo_dir in repos:
        name = repo_dir.name
        if wanted and name not in wanted:
            continue
        snap = multirepo_root / name
        if not (snap / "snapshot.parquet").exists():
            print(f"funnel: {name} skipped (no local snapshot at {snap})", flush=True)
            rows.append({"cohort": name, "kind": "multirepo", "skipped": "no local snapshot"})
            continue
        print(f"funnel: {name} ...", flush=True)
        tf.bind_snapshot(snap)
        store = fam.load_store()[0]
        spec = fam.FAMILIES[tf.FAMILY]
        tools, catalog = fam.make_tools(spec, store), fam.make_catalog(spec)
        source_manifest = fam.make_manifest(spec, MODEL, tools, catalog, "source")
        continuation = fam.make_manifest(spec, MODEL, (), catalog, "pre-model")
        checkpoint = json.loads((repo_dir / "discovery_checkpoint.json").read_text(encoding="utf-8"))
        discovery = fam.reconstruct_discovery(spec, checkpoint, store=store, manifest=source_manifest)
        inputs = {"kind": "family", "spec": spec, "discovery": discovery, "catalog": catalog,
                  "source_manifest": source_manifest, "continuation_manifest": continuation}
        by_policy = {p: compile_with(p, inputs, freeze=True) for p in POLICIES}
        rep = reproduces(by_policy["full"], retained_multirepo(repo_dir))
        if rep.get("checked") and not rep["ok"]:
            raise SystemExit(f"{name}: P1 does not reproduce the retained decision: {rep}")
        rows.append({"cohort": name, "kind": "multirepo", "n_discovery": len(discovery), "frozen_single_candidate": True,
                     "snapshot_manifest_sha256": fixed.HF_PARQUET_SHA256,
                     "reproduction": rep, "policies": by_policy, "divergence": divergence(by_policy)})
        _print_row(rows[-1])
    return {
        "schema": "gac-compiler-funnel/v1",
        "script": "paper/scripts/compiler_funnel.py",
        "protocol": {"path": str(PROTOCOL_PATH.relative_to(ROOT)), "sha256": _sha256(PROTOCOL_PATH)},
        "snapshot_date": SNAPSHOT_DATE,
        "evidence_class": "provider-free recorded replay through the shipped compiler; descriptive; no dispatch",
        "policies": {p: {"grounding": g, "alpha": a} for p, (g, a) in POLICIES.items()},
        "definitions": {
            "grounding_off": "majority-literal fallback in Algorithm 3: a slot with no invariant literal and no expression is bound to its modal training value (lexical tie-break)",
            "statistical_admission_off": "alpha = 1.0: the gate accepts every calibrated candidate; calibration replay still runs and its counts are recorded",
            "divergence": "a candidate some policy emits that the full policy does not emit; its calibration replay counts are the replay half of H3",
        },
        "cohorts": rows,
        "summary": summary(rows),
        "runtime_seconds": round(time.perf_counter() - started, 1),
    }


def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    done = [r for r in rows if "policies" in r]
    div = [(r["cohort"], d) for r in done for d in r["divergence"]]
    return {
        "cohorts": len(done),
        "cohorts_reproducing_retained_decision": sum(1 for r in done if r["reproduction"].get("ok")),
        "cohorts_with_divergence": len({c for c, _ in div}),
        "divergent_candidates": len(div),
        "divergence_replay_violations": sum((d["calibration_replay"].get("gate_calibration_violations") or 0) for _, d in div),
        "divergence_replay_unproductive": sum((d["calibration_replay"].get("gate_calibration_unproductive") or 0) for _, d in div),
        "equal_routing_cohorts": [r["cohort"] for r in done if not r["divergence"]],
    }


def _print_row(row: dict[str, Any]) -> None:
    adm = {p: [a["tools"] for a in res["artifacts"] if not a["gate_retire"]] for p, res in row["policies"].items()}
    print(f"  reproduces={row['reproduction'].get('ok')} admitted={ {p: [len(t) for t in v] for p, v in adm.items()} } "
          f"divergence={len(row['divergence'])}", flush=True)
    for d in row["divergence"]:
        cr = d["calibration_replay"]
        print(f"    {d['policy']}: {d['tools']} full_stage={d['full_stage']} ({d['full_rejected']}) "
              f"cal viol={cr.get('gate_calibration_violations')} unprod={cr.get('gate_calibration_unproductive')} "
              f"of {cr.get('gate_calibration_samples')}", flush=True)


def _sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# table
# ---------------------------------------------------------------------------

LABELS = {"issue_type": "Issue-type routing", "pr_outcome": "PR-outcome", "backlog_attention": "Backlog attention"}


def _short(tools: list[str] | None) -> str:
    if not tools:
        return "--"
    return str(len(tools)) + "-read"


def table(results: dict[str, Any] | None = None) -> str:
    results = results or json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    lines = [
        r"\begin{tabular}{@{}llllll@{}}",
        r"\toprule",
        r"Cohort & Full & Support-only & Recurrence-only & Stats-only & Divergence (full stage; replay viol./unprod.) \\",
        r"\midrule",
    ]
    for row in results["cohorts"]:
        if "policies" not in row:
            continue
        label = LABELS.get(row["cohort"], row["cohort"].replace("__", "/").replace("_", r"\_"))
        cells = []
        for p in POLICIES:
            adm = [a for a in row["policies"][p]["artifacts"] if not a["gate_retire"]]
            cells.append(", ".join(_short(a["tools"]) for a in adm) if adm else "none")
        if row["divergence"]:
            parts = []
            for d in row["divergence"]:
                cr = d["calibration_replay"]
                parts.append(f"{d['policy'].replace('_', '-')}: {_short(d['tools'])} ({d['full_stage']}; "
                             f"{cr.get('gate_calibration_violations')}/{cr.get('gate_calibration_unproductive')} of {cr.get('gate_calibration_samples')})")
            div = "; ".join(parts)
        else:
            div = "none"
        lines.append(f"{label} & " + " & ".join(cells) + f" & {div} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "% generated by paper/scripts/compiler_funnel.py table; do not edit\n" + "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("run", "table"))
    parser.add_argument("--multirepo-snapshots", type=Path, default=DEFAULT_MULTIREPO_SNAPSHOTS)
    parser.add_argument("--cohorts", default=None, help="comma-separated subset (default: all)")
    parser.add_argument("--output", type=Path, default=RESULTS_PATH)
    args = parser.parse_args(argv)
    if args.command == "table":
        text = table()
        TABLE_PATH.write_text(text, encoding="utf-8")
        print(text)
        return
    cohorts = [c.strip() for c in args.cohorts.split(",")] if args.cohorts else None
    result = run(args.multirepo_snapshots, cohorts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(f"wrote {args.output.relative_to(ROOT) if args.output.is_relative_to(ROOT) else args.output}")
    print(json.dumps(result["summary"], indent=1))
    if args.output == RESULTS_PATH:
        TABLE_PATH.write_text(table(result), encoding="utf-8")
        print(f"wrote {TABLE_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
