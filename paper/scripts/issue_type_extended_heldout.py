"""Extended held-out cohort for issue-type routing on the calibrated model.

Protocol: ``paper/supplementary/issue-type-extended-heldout-protocol.md``.

120 unused records from the pinned snapshot (40 ``bug`` / 40 ``enhancement`` /
40 ``other``, stable-rank draw, seed 20260924), three arms on ``gpt-5.6-luna``
with the retained registry (artifact ``cand-01-1ebb8b2849c7`` unchanged), in a
balanced six-permutation Latin order.  ``preflight`` seals the cohort and checks
that the retained artifact resolves under the rebuilt manifest without a
provider call; ``run`` executes the arms; ``table`` regenerates the ICLR table.
"""

from __future__ import annotations

import argparse
import asyncio
import glob
import hashlib
import json
import os
import platform
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from importlib.metadata import version
from itertools import permutations
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from scipy.stats import beta

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import github_live_study as fixed  # noqa: E402
import recurrence_only_ablation as shared  # noqa: E402
from guarded_agentic_compaction.capture.agents_sdk import AgentsTraceProcessor  # noqa: E402

PROTOCOL = ROOT / "paper/supplementary/issue-type-extended-heldout-protocol.md"
OUT_DIR = ROOT / "paper/results/issue_type_extended_heldout"
TABLE_PATH = ROOT / "paper/iclr/tables/extended_heldout.tex"
RETAINED_REGISTRY = ROOT / "paper/results/github_natural_replication/registry"
RETAINED_ARTIFACT = "cand-01-1ebb8b2849c7"
TASK_DESIGN = "natural-extractive-v2"
MODEL = "gpt-5.6-luna"
SEED = 20260924
PER_CLASS = 40
CLASSES = ("bug", "enhancement", "other")
CONDITIONS = ("baseline", "compiled", "macro")
PRIMARY_N = 90  # held-out records behind Table 1 (three families)


def used_issue_numbers() -> tuple[set[int], list[str]]:
    """Every issue number any retained issue-type cohort has touched."""

    used: set[int] = set()
    sources: list[str] = []
    patterns = (
        "paper/results/github_natural_replication/**/*.json",
        "paper/results/github_natural_live/**/*.json",
        "paper/results/github_live/**/*.json",
        "paper/results/recurrence_only_ablation/*.json",
        "paper/results/second_model_replication/**/*.json",
    )
    for pattern in patterns:
        for path in sorted(glob.glob(str(ROOT / pattern), recursive=True)):
            try:
                data = json.loads(Path(path).read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            selection = data.get("selection") or {}
            before = len(used)
            used.update(int(v) for v in selection.get("discovery_issue_numbers", []))
            used.update(int(v) for v in selection.get("discovery", []) if not isinstance(v, dict))
            for item in selection.get("test", []):
                used.add(int(item["issue_number"]) if isinstance(item, dict) else int(item))
            for row in data.get("results", []) if isinstance(data.get("results"), list) else []:
                if isinstance(row, dict) and "issue_number" in row:
                    used.add(int(row["issue_number"]))
            if len(used) > before:
                sources.append(str(Path(path).relative_to(ROOT)))
    return used, sources


def select_cohort(store: dict[int, dict[str, Any]], used: set[int]) -> tuple[list[fixed.Scenario], dict[str, Any]]:
    pools: dict[str, list[int]] = defaultdict(list)
    for number, item in store.items():
        if number in used or len(item["body"].strip()) < 80:
            continue
        category = fixed.category_for(item["labels"])
        if category == "other":
            pools["other"].append(number)
        elif category in ("bug", "enhancement") and set(item["labels"]) & {"bug", "enhancement", "question"} == {category}:
            pools[category].append(number)
    chosen: list[int] = []
    pool_sizes = {cls: len(pools[cls]) for cls in CLASSES}
    for cls in CLASSES:
        ranked = sorted(pools[cls], key=lambda n: fixed._stable_rank(n, SEED, f"test:{cls}"))
        if len(ranked) < PER_CLASS:
            raise RuntimeError(f"not enough unused {cls} records: {len(ranked)} < {PER_CLASS}")
        chosen.extend(ranked[:PER_CLASS])
    scenarios = []
    for number in chosen:
        item = store[number]
        scenarios.append(fixed.Scenario(
            issue_number=number, category=fixed.category_for(item["labels"]), labels=tuple(item["labels"]),
            html_url=item["html_url"], day=item["day"], state=item["state"],
        ))
    orders = list(permutations(CONDITIONS))
    ranked = sorted(scenarios, key=lambda s: fixed._stable_rank(s.issue_number, SEED, "latin-order:0"))
    assignments = {str(s.issue_number): list(orders[i % len(orders)]) for i, s in enumerate(ranked)}
    selection = {
        "seed": SEED,
        "per_class": PER_CLASS,
        "classes": list(CLASSES),
        "class_rule": "bug/enhancement exclusive-label classes as in the retained selection; other = retained oracle's fourth category; question excluded (16 exclusive issues in the snapshot, 10 used)",
        "excluded_prior_issue_count": len(used),
        "unused_pool_sizes": pool_sizes,
        "test": [
            {"issue_number": s.issue_number, "category": s.category, "labels": list(s.labels),
             "html_url": s.html_url, "day": s.day, "state": s.state} for s in scenarios
        ],
        "record_numbers_sha256": hashlib.sha256(json.dumps(sorted(chosen)).encode()).hexdigest(),
        "condition_order": {"method": "balanced-six-permutation-latin-order", "assignments": assignments,
                            "counts": dict(Counter("_then_".join(v) for v in assignments.values()))},
    }
    return scenarios, selection


def rebuild_registry(store: dict[int, dict[str, Any]], catalog: Any, tools: Any) -> tuple[Any, dict[str, Any]]:
    """Recompile the retained artifact provider-free under the current tracer version.

    The retained registry pins ``tracer_version=agent-compaction/0.5.0`` inside its
    compatibility key; the package is now 0.6.0, so the retained entry would fall back
    at dispatch by design (a manifest-pin barrier).  Recompiling from the sealed
    discovery checkpoint reproduces the same artifact (id, program, splits, 92/0 gate)
    under the current pin; the preflight asserts that equality before any live call.
    """

    import second_model_replication as design

    from guarded_agentic_compaction.registry.store import Registry

    retained = shared.load_retained()
    checkpoint = json.loads(design.CHECKPOINT.read_text(encoding="utf-8"))
    manifest = fixed.make_manifest(MODEL, tools, catalog, TASK_DESIGN)
    discovery = design.reconstruct_discovery(checkpoint, store=store, manifest=manifest)
    registry, record, _ = design.compile_for_model(discovery, model=MODEL, catalog=catalog, tools=tools)
    got = design.artifact_fingerprint(record["artifact"])
    want = design.artifact_fingerprint(retained["compiler"]["artifact"])
    retained_registry = Registry.load(RETAINED_REGISTRY)
    retained_key = next(a for a in retained_registry.artifacts if a.artifact_id == RETAINED_ARTIFACT).compatibility_key
    checks = {
        "artifact_id_identical": got["artifact_id"] == want["artifact_id"] == RETAINED_ARTIFACT,
        "program_identical": got["program"] == want["program"],
        "splits_digest_identical": record["splits"].get("digest") == retained["compiler"]["splits"].get("digest"),
        "gate_identical": all(got[k] == want[k] for k in ("gate_n_calibration_groups", "gate_n_accepted", "gate_violations", "gate_upper_bound", "gate_threshold", "gate_retire")),
        "retained_compatibility_key": retained_key,
        "current_compatibility_key": manifest.compatibility_key(),
        "retained_tracer_version": (retained["compiler"]["artifact"].get("manifest") or {}).get("tracer_version"),
        "current_tracer_version": manifest.tracer_version,
    }
    if not (checks["artifact_id_identical"] and checks["program_identical"] and checks["splits_digest_identical"] and checks["gate_identical"]):
        raise RuntimeError("recompilation does not reproduce the retained artifact: " + json.dumps(checks, default=str))
    return registry, {"checks": checks, "artifact": got}


def preflight(_args: argparse.Namespace) -> dict[str, Any]:
    store, audit = shared.load_store()
    used, sources = used_issue_numbers()
    scenarios, selection = select_cohort(store, used)
    catalog = fixed.make_catalog()
    tools = fixed.make_tools(store)
    manifest = fixed.make_manifest(MODEL, tools, catalog, TASK_DESIGN)
    registry, rebuild = rebuild_registry(store, catalog, tools)
    artifact = registry.artifacts[0]
    resolves = artifact.compatibility_key == manifest.compatibility_key()
    if not resolves:
        raise RuntimeError("recompiled artifact does not resolve under the rebuilt manifest")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    registry.save(OUT_DIR / "registry")
    missing = [s.issue_number for s in scenarios if not store[s.issue_number]["title"].strip() or not store[s.issue_number]["state"].strip()]
    if missing:
        raise RuntimeError(f"{len(missing)} selected records lack oracle fields")
    payload = {
        "schema": "agent-compaction-extended-heldout-preflight/v1",
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "execution_status": "preflight_only",
        "provider_calls": 0,
        "real_public_records": True,
        "simulated": False,
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": shared.sha256_file(PROTOCOL)},
        "source": audit,
        "exclusion_sources": sources,
        "model": MODEL,
        "artifact": {"retained_registry": str(RETAINED_REGISTRY.relative_to(ROOT)), "artifact_id": RETAINED_ARTIFACT,
                     "recompiled_registry": str((OUT_DIR / "registry").relative_to(ROOT)),
                     "compatibility_key": artifact.compatibility_key, "resolves_under_rebuilt_manifest": resolves,
                     "recompilation": rebuild,
                     "gate_n_accepted": artifact.gate.to_dict().get("n_accepted")},
        "conditions": list(CONDITIONS),
        "selection": selection,
        "model_settings": {"reasoning_effort": "low", "verbosity": "low", "parallel_tool_calls": False,
                           "store": False, "max_turns": 8, "timeout_s": 120,
                           "retry_policy": "one retry per timed-out episode; both attempts retained"},
        "spend": {"approved_usd_required": 1.0, "expected_usd": 0.12},
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "preflight.json").write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
                                            encoding="utf-8")
    return payload


def one_sided_upper(k: int, n: int, conf: float = 0.95) -> float:
    if n <= 0:
        return 1.0
    if k >= n:
        return 1.0
    return float(beta.ppf(conf, k + 1, n - k))


async def run(args: argparse.Namespace) -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")
    if args.approved_spend_usd is None or args.approved_spend_usd <= 0:
        raise RuntimeError("a positive --approved-spend-usd is required for a live run")
    pre = preflight(args)
    result_path = OUT_DIR / "results.json"
    if result_path.exists() and not args.force:
        raise RuntimeError(f"refusing to overwrite {result_path}; pass --force")
    store, _audit = shared.load_store()
    scenarios = [
        fixed.Scenario(issue_number=int(i["issue_number"]), category=i["category"], labels=tuple(i["labels"]),
                       html_url=i["html_url"], day=i["day"], state=i["state"])
        for i in pre["selection"]["test"]
    ]
    orders = pre["selection"]["condition_order"]["assignments"]

    from agents import add_trace_processor
    from guarded_agentic_compaction.registry.store import Registry

    processor = AgentsTraceProcessor(include_sensitive_data=True, max_completed=2000)
    add_trace_processor(processor)
    catalog = fixed.make_catalog()
    tools = fixed.make_tools(store)
    manifest = fixed.make_manifest(MODEL, tools, catalog, TASK_DESIGN)
    macro_tools = fixed.make_macro_tool(store)
    macro_catalog = fixed.make_macro_catalog()
    macro_manifest = fixed.make_manifest(MODEL, macro_tools, macro_catalog, TASK_DESIGN)
    registry = Registry.load(OUT_DIR / "registry")
    arms = {
        "baseline": {"tools": tools, "catalog": catalog, "manifest": manifest, "registry": None},
        "compiled": {"tools": tools, "catalog": catalog, "manifest": manifest, "registry": registry},
        "macro": {"tools": macro_tools, "catalog": macro_catalog, "manifest": macro_manifest, "registry": None},
    }
    results: list[fixed.RunResult] = []
    attempts: list[dict[str, Any]] = []
    spent = 0.0
    for scenario in scenarios:
        for condition in orders[str(scenario.issue_number)]:
            if spent > args.approved_spend_usd:
                attempts.append({"issue_number": scenario.issue_number, "condition": condition,
                                 "error": "approved spend exhausted"})
                continue
            arm = arms[condition]
            for attempt in (0, 1):
                rows, failures = await fixed.run_agents_batch(
                    [scenario], condition=condition, repeat=attempt, model_name=MODEL, tools=arm["tools"],
                    processor=processor, manifest=arm["manifest"], catalog=arm["catalog"],
                    registry=arm["registry"], concurrency=1, task_design=TASK_DESIGN, source_store=store,
                )
                for failure in failures:
                    attempts.append({**failure, "attempt": attempt})
                if rows:
                    row = rows[0]
                    row.repeat = 0
                    results.append(row)
                    spent += float(row.metrics.get("estimated_cost_usd") or 0.0)
                    break
                if not any("TimeoutError" in str(f.get("error", "")) for f in failures):
                    break
            (OUT_DIR / "evaluation_checkpoint.json").write_text(
                json.dumps({"results": [v.public_dict() for v in results], "attempts": attempts},
                           indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

    grouped = {c: [r for r in results if r.condition == c] for c in CONDITIONS}
    n = len(scenarios)
    comparison = fixed.paired_analysis(grouped["baseline"], grouped["compiled"])
    quality = comparison["quality"].get("factuality_exact", comparison["quality"]["overall"])
    compiled_only = int(quality["baseline_only_successes"])
    n_pairs = int(comparison["n_pairs"])
    pooled_n = PRIMARY_N + n_pairs
    payload = {
        "schema": "agent-compaction-extended-heldout/v1",
        "run": {
            "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "script": "paper/scripts/issue_type_extended_heldout.py",
            "model": MODEL, "openai_agents_sdk": version("openai-agents"), "openai_python": version("openai"),
            "python": platform.python_version(), "platform": platform.platform(), "provider_backed": True,
            "real_public_records": True, "simulated": False, "openai_api_key_used": True,
            "secrets_serialized": False, "approved_spend_usd": args.approved_spend_usd,
            "estimated_spend_usd": round(spent, 6),
            "comparative_claim_allowed": all(len(grouped[c]) == n for c in CONDITIONS),
            "protocol": pre["protocol"],
        },
        "source": pre["source"],
        "artifact": pre["artifact"],
        "selection": pre["selection"],
        "intention_to_treat": {c: {"attempted": n, "completed": len(grouped[c])} for c in CONDITIONS},
        "aggregate": fixed.aggregate_runs(results),
        "comparisons": {"baseline_vs_compiled": comparison,
                        "baseline_vs_macro": fixed.paired_analysis(grouped["baseline"], grouped["macro"], candidate_label="macro")},
        "dispatch": {"compiled_compacted": sum(int(r.dispatch.get("compacted", 0) > 0) for r in grouped["compiled"]),
                     "guard_misses": dict(Counter(json.dumps(r.dispatch.get("guard_misses"), sort_keys=True) for r in grouped["compiled"]))},
        "compiled_only_bound": {
            "extension": {"k": compiled_only, "n": n_pairs, "upper_95_one_sided": one_sided_upper(compiled_only, n_pairs)},
            "pooled_with_primary": {"k": compiled_only, "n": pooled_n, "upper_95_one_sided": one_sided_upper(compiled_only, pooled_n),
                                    "note": "the 90 primary held-out records had zero compiled-only failures"},
        },
        "hypotheses": {
            "H-E1_zero_compiled_only_failures": compiled_only == 0 and n_pairs == n,
            "H-E2_dispatch_120_of_120": sum(int(r.dispatch.get("compacted", 0) > 0) for r in grouped["compiled"]) == n,
            "H-E3_pooled_bound_at_most_1_5pct": one_sided_upper(compiled_only, pooled_n) <= 0.015,
        },
        "attempts": attempts,
        "results": [v.public_dict() for v in results],
    }
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return payload


def table(_args: argparse.Namespace) -> str:
    data = json.loads((OUT_DIR / "results.json").read_text(encoding="utf-8"))
    rows = data["results"]
    n_att = int(data["intention_to_treat"]["baseline"]["attempted"])
    labels = {"baseline": "Unchanged agent", "compiled": "Compiled two-read prefix (\\method)", "macro": "Hand-written bundle"}
    lines = [r"\begin{tabular}{@{}lrrrrr@{}}", r"\toprule",
             r"Arm & Exact & Requests & Tokens & Latency (s) & Cost (\textcent) \\", r"\midrule"]
    for condition in CONDITIONS:
        sel = [r for r in rows if r["condition"] == condition]
        m = len(sel)
        exact = sum(bool(r["quality"].get("factuality_exact")) for r in sel)
        mean = lambda key: (sum(float(r["metrics"][key] or 0.0) for r in sel) / m) if m else 0.0  # noqa: E731
        lines.append(f"{labels[condition]} & {exact}/{n_att} & {mean('requests'):.2f} & {mean('total_tokens'):,.0f} & "
                     f"{mean('wall_latency_ms') / 1000:.2f} & {100 * mean('estimated_cost_usd'):.3f} \\\\")
    b = data["compiled_only_bound"]
    lines += [r"\midrule",
              f"\\multicolumn{{6}}{{@{{}}l}}{{Compiled-only failures: {b['extension']['k']}/{b['extension']['n']} here "
              f"(one-sided 95\\% bound {100 * b['extension']['upper_95_one_sided']:.1f}\\%); "
              f"{b['pooled_with_primary']['k']}/{b['pooled_with_primary']['n']} pooled with the primary cohorts "
              f"(bound {100 * b['pooled_with_primary']['upper_95_one_sided']:.1f}\\%)}} \\\\",
              r"\bottomrule", r"\end{tabular}"]
    text = ("% generated by paper/scripts/issue_type_extended_heldout.py table; do not edit\n" + "\n".join(lines) + "\n")
    TABLE_PATH.write_text(text, encoding="utf-8")
    return text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "run", "table"))
    parser.add_argument("--approved-spend-usd", type=float)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "preflight":
        payload = preflight(args)
        shown = {k: v for k, v in payload.items() if k != "selection"}
        shown["selection_summary"] = {"n": len(payload["selection"]["test"]),
                                      "classes": dict(Counter(i["category"] for i in payload["selection"]["test"])),
                                      "unused_pool_sizes": payload["selection"]["unused_pool_sizes"],
                                      "order_counts": payload["selection"]["condition_order"]["counts"]}
        print(json.dumps(shown, indent=2, sort_keys=True, default=str))
    elif args.command == "table":
        print(table(args))
    else:
        payload = asyncio.run(run(args))
        print(json.dumps({k: payload[k] for k in ("run", "intention_to_treat", "aggregate", "dispatch",
                                                  "compiled_only_bound", "hypotheses")},
                         indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
