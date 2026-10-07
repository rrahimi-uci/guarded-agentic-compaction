"""Continuation-graded drift ablation on the primary PR-outcome and backlog records (live, capped).

Protocol: ``paper/supplementary/drift-continuation-graded-protocol.md`` (pre-registered
2026-10-07). For every (record, perturbation) cell two arms run on identical perturbed tools:
``guarded`` (retained artifact, induced verifier; abstention falls back to the unchanged agent
on the same perturbed tools) and ``unverified`` (same artifact with a permissive verifier).
The continuation is graded by the family's exact contract against the unperturbed record.
Injected failures surface as error payloads, as the real tools do. Live cells refuse to run
without ``--approved-spend-usd``; costs are ledgered against the cap.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import os
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from scipy.stats import beta, binomtest  # noqa: E402

from guarded_agentic_compaction.evaluation.perturb import DEFAULT_PERTURBATIONS  # noqa: E402
from guarded_agentic_compaction.registry.store import Registry  # noqa: E402
from guarded_agentic_compaction.schema.artifacts import Verifier  # noqa: E402

MODEL = "gpt-5.6-luna"
FAMILIES = {"pr_outcome": ROOT / "paper/results/github_workflow_families/pr_outcome/final",
            "backlog_attention": ROOT / "paper/results/github_workflow_families/backlog_attention/final"}
ARMS = ("guarded", "unverified")
PERTS = {p.name: p for p in DEFAULT_PERTURBATIONS}


def cp_upper(k: int, n: int, conf: float = 0.95) -> float | None:
    if n == 0:
        return None
    if k >= n:
        return 1.0
    return float(beta.ppf(conf, k + 1, n - k))


def mcnemar_exact(b: int, c: int) -> float:
    return 1.0 if b + c == 0 else float(binomtest(min(b, c), b + c, 0.5).pvalue)


def _canonical(value: Any) -> Any:
    """Key-sorted copy, the form the agent tools serialize; both arms perturb this form."""
    return json.loads(json.dumps(value, sort_keys=True, default=str))


def perturb_result(pert, tool: str, args: dict[str, Any], result: Any) -> Any:
    if pert.transform is None:  # injected tool failure, surfaced as the tools surface errors
        return {"error": pert.fail_status, "tool": tool, "record_number": args.get("record_number")}
    return pert.transform(tool, dict(args), _canonical(result))


def perturbed_tools(tools: Sequence[Any], pert) -> tuple[Any, ...]:
    from agents import FunctionTool

    out = []
    for tool in tools:
        original = tool.on_invoke_tool

        async def invoke(context: Any, args_json: str, _orig=original, _name=tool.name) -> str:
            value = await _orig(context, args_json)
            payload = json.loads(value) if isinstance(value, str) else value
            try:
                args = json.loads(args_json) if args_json else {}
            except json.JSONDecodeError:
                args = {}
            return json.dumps(perturb_result(pert, _name, args, payload), sort_keys=True, default=str)

        out.append(FunctionTool(name=tool.name, description=tool.description, params_json_schema=tool.params_json_schema,
                                on_invoke_tool=invoke, strict_json_schema=True))
    return tuple(out)


def unverified_copy(registry: Registry) -> Registry:
    copy_reg = Registry(name=f"{registry.name}-unverified")
    for art in registry.artifacts:
        clone = copy.deepcopy(art)
        clone.verifier = Verifier()
        copy_reg.add(clone)
    return copy_reg


class Ledger:
    def __init__(self, path: Path, cap: float | None) -> None:
        self.path, self.cap = path, cap
        self.state = json.loads(path.read_text()) if path.exists() else {"spent_usd": 0.0, "entries": []}

    def reserve(self, n: int, per: float = 0.01) -> None:
        if self.cap is None:
            raise RuntimeError("live cells without --approved-spend-usd")
        if self.state["spent_usd"] + n * per > self.cap:
            raise RuntimeError(f"reservation would exceed cap {self.cap} (spent {self.state['spent_usd']})")

    def charge(self, label: str, results: Sequence[Any]) -> None:
        cost = float(sum(float(r.metrics.get("estimated_cost_usd", 0.0)) for r in results))
        self.state["spent_usd"] = round(self.state["spent_usd"] + cost, 6)
        self.state["entries"].append({"label": label, "n": len(results), "usd": round(cost, 6), "cumulative_usd": self.state["spent_usd"],
                                      "at": datetime.now(UTC).isoformat(timespec="seconds")})
        self.path.write_text(json.dumps(self.state, indent=2) + "\n")


def classify(row: dict[str, Any]) -> dict[str, Any]:
    d = row.get("dispatch") or {}
    compacted = str(d.get("outcome") or "") in ("COMPACTED", "REPLAYED")
    exact = bool(row["quality"].get("overall"))
    return {"compacted": compacted, "exact": exact, "silent_wrong": compacted and not exact,
            "fallback_wrong": (not compacted) and not exact, "requests": int(row["metrics"].get("requests", 0))}


async def main_async(args: argparse.Namespace) -> int:
    import github_live_study as fixed
    import github_workflow_family_study as fam

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    ledger = Ledger(out / "ledger.json", args.approved_spend_usd)
    pert_names = list(args.perturbations or PERTS)
    families = list(args.families or FAMILIES)
    cells = [(f, p) for f in families for p in pert_names]
    if args.dry_run:
        n_records = sum(30 for _ in families)
        print(json.dumps({"dry_run": True, "families": families, "perturbations": pert_names, "cells_per_arm": n_records * len(pert_names),
                          "continuations_max": n_records * len(pert_names) * 2, "fallbacks_max": n_records * len(pert_names), "cap": args.approved_spend_usd}))
        return 0
    fam.load_dotenv(ROOT / ".env")
    if not os.getenv(fixed.provider_api_key_env(MODEL)):
        raise RuntimeError("provider key not set")
    from agents import add_trace_processor

    processor = fam.AgentsTraceProcessor(include_sensitive_data=True, max_completed=20_000)
    add_trace_processor(processor)
    ck_path = out / "cells_checkpoint.json"
    done = json.loads(ck_path.read_text()) if ck_path.exists() else {"results": [], "failures": []}
    completed = {(r["family"], r["arm"], r["perturbation"], int(r["issue_number"])) for r in done["results"]}
    store, store_audit = fam.load_store()
    for family in families:
        spec = fam.FAMILIES[family]
        catalog = fam.make_catalog(spec)
        tools = fam.make_tools(spec, store)
        source_manifest = fam.make_manifest(spec, MODEL, tools, catalog, "source", instructions=spec.discovery_prompt)
        baseline_manifest = fam.make_manifest(spec, MODEL, tools, catalog, "baseline", instructions=spec.prompt)
        continuation_manifest = fam.make_manifest(spec, MODEL, (), catalog, "pre-model", instructions=spec.prompt)
        retained = json.loads((FAMILIES[family] / "results.json").read_text())
        records = sorted({int(r["issue_number"]) for r in retained["results"] if r["condition"] == "baseline" and int(r.get("repeat", 0)) == 0})
        if args.records:
            records = records[: args.records]
        guarded = Registry.load(FAMILIES[family] / "registry")
        unverified = unverified_copy(guarded)
        for pert_name in pert_names:
            pert = PERTS[pert_name]
            executor = lambda tool, values, _p=pert, _s=spec: perturb_result(_p, tool, values, fam.execute_snapshot(_s, store, tool, values))  # noqa: E731
            fb_tools = perturbed_tools(tools, pert)
            for arm, reg in (("guarded", guarded), ("unverified", unverified)):
                todo = [n for n in records if (family, arm, pert_name, n) not in completed]
                if not todo:
                    continue
                ledger.reserve(len(todo), per=0.004)
                results, failures = await fam.run_batch(spec, [store[n] for n in todo], condition=f"drift:{arm}:{pert_name}", model_name=MODEL, tools=(),
                                                        processor=processor, manifest=continuation_manifest, catalog=catalog, store=store,
                                                        concurrency=args.concurrency, registry=reg, artifact_manifest=source_manifest,
                                                        fallback_tools=fb_tools, fallback_manifest=baseline_manifest, instructions=spec.prompt,
                                                        executor=executor)
                ledger.charge(f"{family}:{arm}:{pert_name}", results)
                for r in results:
                    d = r.public_dict(); d.update({"family": family, "arm": arm, "perturbation": pert_name}); done["results"].append(d)
                done["failures"].extend([{**f, "family": family, "arm": arm, "perturbation": pert_name} for f in failures])
                done.update({"schema": "agent-compaction-drift-continuation-graded/v1", "model": MODEL, "store_audit": store_audit,
                             "protocol": "paper/supplementary/drift-continuation-graded-protocol.md", "provider_calls_executed": True})
                ck_path.write_text(json.dumps(done, indent=2, sort_keys=True, default=str) + "\n")
                print(f"[drift-cg] {family} {arm} {pert_name}: {len(results)} cells; spent {ledger.state['spent_usd']:.4f}", flush=True)
    (out / "results.json").write_text(json.dumps(summarize(done), indent=2, sort_keys=True, default=str) + "\n")
    print(f"[drift-cg] decision={summarize(done)['decision']} spent {ledger.state['spent_usd']:.4f}")
    return 0


def summarize(done: dict[str, Any]) -> dict[str, Any]:
    rows = done["results"]
    per_cell = Counter(); per_record: dict[str, dict[str, bool]] = {arm: {} for arm in ARMS}
    table: dict[str, Any] = {}
    for r in rows:
        c = classify(r); key = (r["family"], r["arm"], r["perturbation"])
        t = table.setdefault(f"{r['family']}:{r['arm']}:{r['perturbation']}", Counter())
        t["cells"] += 1; t["compacted"] += c["compacted"]; t["exact"] += c["exact"]; t["silent_wrong"] += c["silent_wrong"]
        t["fallback_wrong"] += c["fallback_wrong"]; t["requests"] += c["requests"]
        rec = f"{r['family']}:{r['issue_number']}"
        per_record[r["arm"]][rec] = per_record[r["arm"]].get(rec, False) or c["silent_wrong"]
    g, u = per_record["guarded"], per_record["unverified"]
    common = sorted(set(g) & set(u))
    b = sum(g[k] and not u[k] for k in common); c_ = sum(u[k] and not g[k] for k in common); both = sum(g[k] and u[k] for k in common)
    inv = [n for n, p in PERTS.items() if p.expect == "invariant"]
    inv_abst = {}
    for arm in ARMS:
        cells = [r for r in rows if r["arm"] == arm and r["perturbation"] in inv]
        inv_abst[arm] = round(sum(not classify(r)["compacted"] for r in cells) / len(cells), 4) if cells else None
    wrong = {arm: sum(v.values()) for arm, v in per_record.items()}
    decision = ("no_cells" if not common else "adverse:guarded_silent_wrong" if wrong["guarded"] else
                "verifier_prevents_silent_wrong" if wrong["unverified"] else "null:no_silent_wrong_in_either_arm")
    return {"schema": "agent-compaction-drift-continuation-graded-summary/v1", "cells": len(rows), "paired_records": len(common),
            "silent_wrong_records": wrong, "discordant": {"guarded_only": b, "unverified_only": c_, "both": both, "mcnemar_exact_p": mcnemar_exact(b, c_)},
            "silent_wrong_upper95": {arm: cp_upper(wrong[arm], len(common)) for arm in ARMS},
            "invariant_fallback_rate": inv_abst, "per_cell": {k: dict(v) for k, v in sorted(table.items())}, "decision": decision,
            "failures": len(done.get("failures", []))}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--family", action="append", dest="families", default=None)
    ap.add_argument("--perturbation", action="append", dest="perturbations", default=None)
    ap.add_argument("--records", type=int, default=0, help="pilot: first N records per family")
    ap.add_argument("--approved-spend-usd", type=float, default=None)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", type=Path, default=ROOT / "paper/results/drift_continuation_graded")
    args = ap.parse_args(argv)
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
