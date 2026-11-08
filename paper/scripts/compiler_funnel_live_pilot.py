"""Live pilot of the compiler funnel's one divergence on fresh, post-cutoff issues.

Protocol: ``paper/supplementary/compiler-funnel-live-pilot-protocol.md`` (sealed 2026-11-08).

Phases (one command each, every phase checkpointed under ``paper/results/compiler_funnel_pilot``):

* ``preflight``  provider-free: pool, split, hashes, expected spend.
* ``discovery``  live: the unchanged agent once per discovery issue.
* ``compile``    provider-free: GAC on the discovery traces (retained configuration) and the
                 four same-IR funnel policies on the same traces.
* ``test``       live: compiled (GAC), recurrence-only three-read replay, baseline, paired on
                 every test issue in a balanced Latin order.
* ``summarize``  provider-free: results.json from the checkpoints; ``table`` renders the LaTeX.

The fresh snapshot is bound exactly as the time-forward PR-outcome study binds it, so every
snapshot tool, oracle and envelope field of the retained issue-type study is reused unchanged.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import platform
import re
import statistics
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from importlib.metadata import version
from itertools import permutations
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Sequence

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import compiler_funnel as cf  # noqa: E402
import github_live_study as fixed  # noqa: E402
import recurrence_only_ablation as issue  # noqa: E402
import second_model_replication as second  # noqa: E402
import time_forward_pr_outcome_study as tf  # noqa: E402
from guarded_agentic_compaction.capture.agents_sdk import AgentsTraceProcessor  # noqa: E402

PROTOCOL = ROOT / "paper/supplementary/compiler-funnel-live-pilot-protocol.md"
OUT_DIR = ROOT / "paper/results/compiler_funnel_pilot"
TABLE_PATH = ROOT / "paper/iclr/tables/compiler_funnel_pilot.tex"
SNAPSHOT_DIR = tf.SNAPSHOT_DIR
MODEL = tf.MODEL
TASK_DESIGN = second.TASK_DESIGN
SEED = 20261108
NAMESPACE = "tf-issue-pilot"
DISCOVERY_N = 128
# Same-record-space uses found by the third-pass fresh-issue preflight (broad key walk over
# paper/results and experiments); excluded whatever the field-rule scan below finds.
KNOWN_SAME_SPACE_USES = (7693, 7694, 8029, 8590)
OTHER_RECORD_SPACE_MARKERS = ("/bird/", "bird_source_screen", "multirepo", "/datasets/", "/compiler_funnel_pilot/")
RECORD_FIELD = re.compile(r'"(?:issue_number|record_number)"\s*:\s*(\d+)')
ARMS = ("compiled", issue.CONDITION, "baseline")
ARM_LABELS = {
    "baseline": "Unchanged agent",
    "compiled": "Compiled two-read prefix (\\method, fresh compile)",
    issue.CONDITION: "Recurrence-only three-read replay",
}
TIMEOUT_S = 120.0
CONCURRENCY = 8
RESERVE_PER_EPISODE_USD = 0.002  # about twice the retained worst case


# ------------------------------------------------------------------------- binding


def bind() -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    """Bind every retained module to the fresh snapshot and load its store."""

    _fam, _fixed, manifest = tf.bind_snapshot(SNAPSHOT_DIR)
    store, audit = issue.load_store()  # checksum-verified against the bound digest
    audit = dict(audit)
    audit.update({"snapshot_dir": str(SNAPSHOT_DIR.relative_to(ROOT)), "created_after_utc_day": manifest["created_after_utc_day"],
                  "fetch_completed_utc": manifest["fetch_completed_utc"], "repository": manifest["repository"]})
    return store, audit


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ------------------------------------------------------------------------------ pool


def field_rule_uses(wanted: set[int]) -> dict[int, list[str]]:
    """Record numbers of ``wanted`` that appear as issue_number/record_number fields in retained
    result files of the same record space (BIRD, multi-repository and raw snapshot files skipped)."""

    hits: dict[int, set[str]] = {}
    for root in (ROOT / "paper/results", ROOT / "experiments"):
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.json")):
            rel = "/" + path.relative_to(ROOT).as_posix()
            if any(marker in rel for marker in OTHER_RECORD_SPACE_MARKERS):
                continue
            try:
                text = path.read_text(errors="ignore")
            except OSError:
                continue
            for match in RECORD_FIELD.findall(text):
                number = int(match)
                if number in wanted:
                    hits.setdefault(number, set()).add(rel.lstrip("/"))
    return {n: sorted(v) for n, v in sorted(hits.items())}


def pool_numbers(store: dict[int, dict[str, Any]], excluded: set[int]) -> list[int]:
    return [n for n in sorted(store) if store[n]["comments"] and n not in excluded]


def rank(number: int) -> str:
    return fixed._stable_rank(number, SEED, NAMESPACE)


def split(numbers: Sequence[int]) -> tuple[list[int], list[int]]:
    ranked = sorted(numbers, key=rank)
    return ranked[:DISCOVERY_N], ranked[DISCOVERY_N:]


def scenario(store: dict[int, dict[str, Any]], number: int) -> fixed.Scenario:
    item = store[number]
    return fixed.Scenario(issue_number=number, category=fixed.category_for(item["labels"]), labels=tuple(item["labels"]),
                          html_url=item["html_url"], day=item["day"], state=item["state"])


def latin_assignment(numbers: Sequence[int]) -> dict[int, tuple[str, ...]]:
    orders = list(permutations(ARMS))
    ranked = sorted(numbers, key=lambda n: fixed._stable_rank(n, SEED, f"{NAMESPACE}:latin"))
    return {n: orders[i % len(orders)] for i, n in enumerate(ranked)}


# ---------------------------------------------------------------------------- ledger


class Ledger:
    def __init__(self, cap: float | None) -> None:
        self.path = OUT_DIR / "ledger.json"
        self.cap = cap
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {"spent_usd": 0.0, "entries": []}

    def reserve(self, n_episodes: int) -> None:
        if self.cap is None or self.cap <= 0:
            raise RuntimeError("a positive --approved-spend-usd is required for a live phase")
        if self.state["spent_usd"] + n_episodes * RESERVE_PER_EPISODE_USD > self.cap:
            raise RuntimeError(f"reservation {n_episodes}x{RESERVE_PER_EPISODE_USD} would cross the cap {self.cap} "
                               f"(spent {self.state['spent_usd']})")

    def charge(self, phase: str, results: Sequence[Any]) -> None:
        cost = float(sum(float(r.metrics.get("estimated_cost_usd") or 0.0) for r in results))
        self.state["spent_usd"] = round(self.state["spent_usd"] + cost, 6)
        self.state["entries"].append({"phase": phase, "results": len(results), "estimated_cost_usd": round(cost, 6),
                                      "cumulative_usd": self.state["spent_usd"],
                                      "at": datetime.now(UTC).isoformat(timespec="seconds")})
        self.path.write_text(json.dumps(self.state, indent=2) + "\n")


# ------------------------------------------------------------------------- preflight


def preflight(args: argparse.Namespace) -> dict[str, Any]:
    store, audit = bind()
    with_comments = {n for n, r in store.items() if r["comments"]}
    field_hits = field_rule_uses(with_comments)
    excluded = set(KNOWN_SAME_SPACE_USES) | set(field_hits)
    pool = pool_numbers(store, excluded)
    discovery, test = split(pool)
    if len(pool) != DISCOVERY_N + len(test) or set(discovery) & set(test):
        raise RuntimeError("split is not a partition of the pool")
    expected = DISCOVERY_N * 0.0009 + len(test) * (0.0009 + 0.0006 + 0.0004)
    payload = {
        "schema": "gac-compiler-funnel-live-pilot-preflight/v1",
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "provider_calls": 0,
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": sha256(PROTOCOL)},
        "source": audit,
        "pool_accounting": {
            "issues_in_snapshot": len(store),
            "issues_with_at_least_one_comment": len(with_comments),
            "known_same_record_space_uses": list(KNOWN_SAME_SPACE_USES),
            "field_rule_hits": {str(k): v for k, v in field_hits.items()},
            "excluded": sorted(excluded & with_comments),
            "pool": len(pool),
            "body_at_least_80_chars": sum(len(store[n]["body"].strip()) >= 80 for n in pool),
            "category": dict(sorted(Counter(fixed.category_for(store[n]["labels"]) for n in pool).items())),
            "state": dict(sorted(Counter(store[n]["state"] for n in pool).items())),
            "comments_ge3": sum(len(store[n]["comments"]) >= 3 for n in pool),
            "number_range": [min(pool), max(pool)],
            "day_range": [min(store[n]["day"] for n in pool), max(store[n]["day"] for n in pool)],
        },
        "selection": {
            "seed": SEED, "namespace": NAMESPACE, "rule": "stable SHA-256 rank; first 128 discovery, rest test",
            "discovery": discovery, "test": test,
            "discovery_sha256": hashlib.sha256(json.dumps(discovery).encode()).hexdigest(),
            "test_sha256": hashlib.sha256(json.dumps(test).encode()).hexdigest(),
            "test_category": dict(sorted(Counter(fixed.category_for(store[n]["labels"]) for n in test).items())),
            "test_comments_ge3": sum(len(store[n]["comments"]) >= 3 for n in test),
            "latin_order": {str(n): list(o) for n, o in sorted(latin_assignment(test).items())},
        },
        "compile_plan": {"train": second.SPLIT["train"], "dev": second.SPLIT["dev"], "calibration": second.SPLIT["calibration"],
                         "eligible_needed": sum(second.SPLIT.values()), "eligibility_rule": "github_live_study.compiler_eligible",
                         "funnel_policies": {p: {"grounding": g, "alpha": a} for p, (g, a) in cf.POLICIES.items()}},
        "model": MODEL,
        "model_settings": {"reasoning_effort": "low", "verbosity": "low", "parallel_tool_calls": False, "store": False,
                           "max_turns": 8, "timeout_s": TIMEOUT_S, "concurrency": CONCURRENCY,
                           "retry_policy": "one retry per timed-out episode; both attempts retained"},
        "spend": {"episodes_planned": DISCOVERY_N + 3 * len(test), "expected_usd": round(expected, 4),
                  "approved_cap_usd": 5.0, "reserve_per_episode_usd": RESERVE_PER_EPISODE_USD},
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "preflight.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def load_preflight() -> dict[str, Any]:
    path = OUT_DIR / "preflight.json"
    if not path.exists():
        raise RuntimeError("run preflight first")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data["protocol"]["sha256"] != sha256(PROTOCOL):
        raise RuntimeError("the sealed protocol changed after the preflight; re-run preflight")
    return data


# ------------------------------------------------------------------------ live runs


def _require_key() -> None:
    load_dotenv(ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")


def _processor() -> AgentsTraceProcessor:
    from agents import add_trace_processor

    processor = AgentsTraceProcessor(include_sensitive_data=True, max_completed=4000)
    add_trace_processor(processor)
    return processor


async def batch_with_retry(scenarios: Sequence[fixed.Scenario], *, condition: str, tools: Sequence[Any], processor: AgentsTraceProcessor,
                           manifest: Any, catalog: Any, registry: Any, store: dict[int, dict[str, Any]]) -> tuple[list[fixed.RunResult], list[dict[str, Any]]]:
    """``run_agents_batch`` plus one retry of every timed-out episode (intention to treat)."""

    results, failures = await fixed.run_agents_batch(
        scenarios, condition=condition, repeat=0, model_name=MODEL, tools=tools, processor=processor, manifest=manifest,
        catalog=catalog, registry=registry, concurrency=CONCURRENCY, task_design=TASK_DESIGN, source_store=store)
    attempts = [{**f, "attempt": 0} for f in failures]
    timed_out = [s for s in scenarios if any(f.get("issue_number") == s.issue_number and "Timeout" in str(f.get("error")) for f in failures)]
    if timed_out:
        retry, retry_failures = await fixed.run_agents_batch(
            timed_out, condition=condition, repeat=0, model_name=MODEL, tools=tools, processor=processor, manifest=manifest,
            catalog=catalog, registry=registry, concurrency=CONCURRENCY, task_design=TASK_DESIGN, source_store=store)
        results.extend(retry)
        attempts.extend({**f, "attempt": 1} for f in retry_failures)
    return results, attempts


def _public(results: Sequence[fixed.RunResult]) -> list[dict[str, Any]]:
    return [r.public_dict() for r in results]


def _write(name: str, payload: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / name).write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


async def discovery(args: argparse.Namespace) -> dict[str, Any]:
    _require_key()
    pre = load_preflight()
    store, _audit = bind()
    path = OUT_DIR / "discovery_checkpoint.json"
    if path.exists() and not args.force:
        raise RuntimeError(f"refusing to overwrite {path}; pass --force")
    ledger = Ledger(args.approved_spend_usd)
    ledger.reserve(len(pre["selection"]["discovery"]))
    processor = _processor()
    tools, catalog = fixed.make_tools(store), fixed.make_catalog()
    manifest = fixed.make_manifest(MODEL, tools, catalog, TASK_DESIGN)
    scenarios = [scenario(store, n) for n in pre["selection"]["discovery"]]
    results, attempts = await batch_with_retry(scenarios, condition="discovery", tools=tools, processor=processor, manifest=manifest,
                                               catalog=catalog, registry=None, store=store)
    ledger.charge("discovery", results)
    eligible = [r for r in results if fixed.compiler_eligible(r, TASK_DESIGN)]
    payload = {
        "schema": "gac-compiler-funnel-live-pilot-discovery/v1",
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "model": MODEL, "condition": "discovery", "provider_backed": True, "real_public_records": True,
        "attempted": len(scenarios), "completed": len(results), "eligible": len(eligible),
        "sequences": dict(Counter(json.dumps(r.tool_sequence) for r in results)),
        "results": _public(results), "attempts": attempts, "spent_usd": ledger.state["spent_usd"],
    }
    payload["comment_limits"] = dict(Counter(json.dumps(next((a.get("limit") for t, a in zip(r.tool_sequence, r.tool_arguments)
                                                              if t == "issue_get_comments"), None)) for r in results))
    _write("discovery_checkpoint.json", payload)
    return payload


def _discovery_runs(store: dict[int, dict[str, Any]]) -> tuple[list[fixed.RunResult], dict[str, Any], Any, Any, Any]:
    checkpoint = json.loads((OUT_DIR / "discovery_checkpoint.json").read_text(encoding="utf-8"))
    tools, catalog = fixed.make_tools(store), fixed.make_catalog()
    manifest = fixed.make_manifest(MODEL, tools, catalog, TASK_DESIGN)
    runs = second.reconstruct_discovery(checkpoint, store=store, manifest=manifest)
    return runs, checkpoint, tools, catalog, manifest


def compile_phase(args: argparse.Namespace) -> dict[str, Any]:
    store, _audit = bind()
    runs, checkpoint, tools, catalog, manifest = _discovery_runs(store)
    eligible = [r for r in runs if fixed.compiler_eligible(r, TASK_DESIGN)]
    gac: dict[str, Any] = {"eligible": len(eligible), "needed": sum(second.SPLIT.values())}
    registry = None
    try:
        registry, record, _manifest = second.compile_for_model(runs, model=MODEL, catalog=catalog, tools=tools)
        artifact = record["artifact"]
        gac.update({"derivable": True, "artifact_id": artifact["artifact_id"], "artifact_tools": cf._artifact_tools(artifact),
                    "rejection_by_stage": record["rejection_by_stage"], "report": record["report"],
                    "artifact_explanation": record["artifact_explanation"], "gate": artifact.get("gate"), "guard": artifact.get("guard"),
                    "splits": record["splits"], "candidates": record["candidates"]})
    except RuntimeError as exc:
        gac.update({"derivable": False, "error": str(exc).splitlines()[0]})
    inputs = {"kind": "issue_type", "discovery": runs, "catalog": catalog, "tools": tools}
    if len(eligible) >= gac["needed"]:
        policies = {p: cf.compile_with(p, inputs) for p in cf.POLICIES}
    else:  # compile_grc is never reached below the split size; the funnel has nothing to compare
        policies = {p: {"policy": p, "artifacts": [], "candidates": [], "rejection_by_stage": {}, "majority_bindings": [],
                        "skipped": f"only {len(eligible)} eligible traces; the split needs {gac['needed']}"} for p in cf.POLICIES}
    payload = {
        "schema": "gac-compiler-funnel-live-pilot-compile/v1",
        "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "provider_calls": 0,
        "discovery_checkpoint_sha256": sha256(OUT_DIR / "discovery_checkpoint.json"),
        "discovery_completed": checkpoint["completed"],
        "gac": gac,
        "funnel": {"policies": policies, "divergence": cf.divergence(policies)},
    }
    _write("compile.json", payload)
    return payload


def _registry_for_test(store: dict[int, dict[str, Any]], compiled: dict[str, Any]) -> tuple[Any, Any, Any, Any]:
    """Recompile deterministically from the checkpoint and check it matches compile.json."""

    runs, _checkpoint, tools, catalog, manifest = _discovery_runs(store)
    if not compiled["gac"].get("derivable"):
        return None, tools, catalog, manifest
    registry, record, _manifest = second.compile_for_model(runs, model=MODEL, catalog=catalog, tools=tools)
    if record["artifact"]["artifact_id"] != compiled["gac"]["artifact_id"]:
        raise RuntimeError("recompilation did not reproduce the recorded artifact")
    return registry, tools, catalog, manifest


async def replay_batch(scenarios: Sequence[fixed.Scenario], *, store: dict[int, dict[str, Any]], manifest: Any,
                       processor: AgentsTraceProcessor) -> tuple[list[fixed.RunResult], list[dict[str, Any]]]:
    """The recurrence-only arm: ``recurrence_only_ablation.run_one`` per issue, bounded concurrency."""

    semaphore = asyncio.Semaphore(1)  # run_one drains the shared processor; keep its traces unambiguous
    results: list[fixed.RunResult] = []
    attempts: list[dict[str, Any]] = []

    async def one(s: fixed.Scenario) -> None:
        async with semaphore:
            result, record_attempts = await issue.run_one(s, store=store, model=MODEL, manifest=manifest, processor=processor)
        attempts.extend({**a, "condition": issue.CONDITION} for a in record_attempts)
        if result is not None:
            results.append(result)

    await asyncio.gather(*(one(s) for s in scenarios))
    return results, attempts


async def test_phase(args: argparse.Namespace) -> dict[str, Any]:
    _require_key()
    pre = load_preflight()
    compiled = json.loads((OUT_DIR / "compile.json").read_text(encoding="utf-8"))
    store, _audit = bind()
    path = OUT_DIR / "test_checkpoint.json"
    state = json.loads(path.read_text(encoding="utf-8")) if path.exists() and not args.force else {"results": [], "attempts": [], "stages": []}
    done = {(r["condition"], int(r["issue_number"])) for r in state["results"]}
    ledger = Ledger(args.approved_spend_usd)
    test_numbers = [int(n) for n in pre["selection"]["test"]]
    ledger.reserve(3 * len(test_numbers) - len(done))
    registry, tools, catalog, manifest = _registry_for_test(store, compiled)
    arms = list(ARMS) if registry is not None else [a for a in ARMS if a != "compiled"]
    replay_manifest = fixed.make_manifest(MODEL, [], catalog, TASK_DESIGN)
    processor = _processor()
    order = {int(n): tuple(o) for n, o in pre["selection"]["latin_order"].items()}
    for stage in range(3):
        for condition in ARMS:
            if condition not in arms:
                continue
            numbers = [n for n in test_numbers if order[n][stage] == condition and (condition, n) not in done]
            if not numbers:
                continue
            scenarios = [scenario(store, n) for n in numbers]
            if condition == issue.CONDITION:
                results, attempts = await replay_batch(scenarios, store=store, manifest=replay_manifest, processor=processor)
            else:
                results, attempts = await batch_with_retry(scenarios, condition=condition, tools=tools, processor=processor, manifest=manifest,
                                                           catalog=catalog, registry=registry if condition == "compiled" else None, store=store)
            ledger.charge(f"test:{stage}:{condition}", results)
            state["results"].extend(_public(results))
            state["attempts"].extend(attempts)
            state["stages"].append({"stage": stage, "condition": condition, "issue_numbers": numbers, "completed": len(results)})
            done.update((condition, r.issue_number) for r in results)
            state["spent_usd"] = ledger.state["spent_usd"]
            _write("test_checkpoint.json", state)
            print(f"stage {stage} {condition}: {len(results)}/{len(numbers)} completed, spent {ledger.state['spent_usd']:.4f} USD", flush=True)
    state.update({"schema": "gac-compiler-funnel-live-pilot-test/v1", "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"),
                  "arms": arms, "compiled_arm_derivable": registry is not None})
    _write("test_checkpoint.json", state)
    return state


# -------------------------------------------------------------------------- summary


def _rows(results: Sequence[dict[str, Any]], condition: str) -> list[SimpleNamespace]:
    return [SimpleNamespace(condition=r["condition"], repeat=int(r.get("repeat", 0)), issue_number=int(r["issue_number"]),
                            metrics=dict(r["metrics"]), quality=dict(r["quality"]), answer=dict(r.get("answer", {})))
            for r in results if r["condition"] == condition]


def classify_telemetry(d: dict[str, Any]) -> str:
    """One compiled episode's ``DispatchTelemetry.as_dict`` into the certificate classes.

    ``region_already_started`` misses are the later boundaries of a dispatched episode and do not
    make it ineligible; any other guard miss (entry hull, manifest) does.
    """

    if int(d.get("compacted") or 0) >= 1:
        return "dispatched"
    if int(d.get("gate_rejections") or 0) >= 1:
        return "gate_declined"
    if any(k != "region_already_started" for k in (d.get("guard_misses") or {})):
        return "guard_ineligible"
    if d.get("verifier_failures") or d.get("interp_failures"):
        return "abstained"
    return "no_dispatch"


FIELDS = ("category_correct", "issue_number_correct", "evidence_label_correct", "title_exact", "state_exact", "comment_count_exact",
          "evidence_excerpt_exact", "factuality_exact", "tool_contract", "overall")


def summarize(args: argparse.Namespace) -> dict[str, Any]:
    pre = load_preflight()
    disc = json.loads((OUT_DIR / "discovery_checkpoint.json").read_text(encoding="utf-8"))
    comp = json.loads((OUT_DIR / "compile.json").read_text(encoding="utf-8"))
    test = json.loads((OUT_DIR / "test_checkpoint.json").read_text(encoding="utf-8"))
    ledger = json.loads((OUT_DIR / "ledger.json").read_text(encoding="utf-8"))
    store, _audit = bind()
    n_test = len(pre["selection"]["test"])
    arms = test.get("arms", list(ARMS))
    by_arm = {a: _rows(test["results"], a) for a in arms}
    aggregate = {a: {
        "attempted": n_test, "completed": len(rows), "failed_after_retry": n_test - len(rows),
        "factuality_exact": sum(bool(r.quality.get("factuality_exact")) for r in rows),
        "overall": sum(bool(r.quality.get("overall")) for r in rows),
        "per_field_exact": {f: sum(bool(r.quality.get(f)) for r in rows) for f in FIELDS},
        "mean": {k: (statistics.mean(float(r.metrics.get(k) or 0.0) for r in rows) if rows else None)
                 for k in ("requests", "total_tokens", "wall_latency_ms", "estimated_cost_usd")},
        "provider_requests": sum(int(r.metrics["requests"]) for r in rows),
        "estimated_cost_usd": round(sum(float(r.metrics.get("estimated_cost_usd") or 0.0) for r in rows), 6),
    } for a, rows in by_arm.items()}
    if "compiled" in by_arm:
        aggregate["compiled"]["dispatch"] = dict(Counter(classify_telemetry(r.get("dispatch") or {}) for r in test["results"] if r["condition"] == "compiled"))
    comparisons = {}
    pairs = [("compiled", issue.CONDITION), ("compiled", "baseline"), (issue.CONDITION, "baseline")]
    for cand, base in pairs:
        if cand in by_arm and base in by_arm:
            comparisons[f"{cand}_vs_{base}"] = fixed.paired_analysis(by_arm[base], by_arm[cand], candidate_label=cand, baseline_label=base)
    misses = {a: sorted(r.issue_number for r in rows if not r.quality.get("factuality_exact")) for a, rows in by_arm.items()}
    only = {}
    for a in arms:
        others = [b for b in arms if b != a]
        only[a] = sorted(n for n in misses[a] if all(n not in misses[b] and any(r.issue_number == n for r in by_arm[b]) for b in others))
    replay_rows = by_arm.get(issue.CONDITION, [])
    audit = issue.continuation_audit(replay_rows, store) if replay_rows else None
    gac = comp["gac"]
    payload = {
        "schema": "gac-compiler-funnel-live-pilot/v1",
        "run": {
            "timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"), "script": "paper/scripts/compiler_funnel_live_pilot.py",
            "model": MODEL, "openai_agents_sdk": version("openai-agents"), "openai_python": version("openai"),
            "python": platform.python_version(), "platform": platform.platform(),
            "provider_backed": True, "real_public_records": True, "simulated": False, "openai_api_key_used": True, "secrets_serialized": False,
            "protocol": pre["protocol"], "approved_cap_usd": pre["spend"]["approved_cap_usd"], "estimated_spend_usd": ledger["spent_usd"],
            "ledger": ledger["entries"], "pilot": True,
            "comparative_claim_allowed": all(v["completed"] == n_test for v in aggregate.values()),
        },
        "source": pre["source"],
        "pool_accounting": pre["pool_accounting"],
        "selection": {k: pre["selection"][k] for k in ("seed", "namespace", "rule", "discovery", "test", "discovery_sha256", "test_sha256",
                                                          "test_category", "test_comments_ge3", "latin_order")},
        "discovery": {"attempted": disc["attempted"], "completed": disc["completed"], "eligible": disc["eligible"],
                      "sequences": disc["sequences"], "comment_limits": disc["comment_limits"],
                      "factuality_exact": sum(bool(r["quality"].get("factuality_exact")) for r in disc["results"]),
                      "estimated_cost_usd": round(sum(float(r["metrics"].get("estimated_cost_usd") or 0.0) for r in disc["results"]), 6),
                      "attempts": disc["attempts"]},
        "compile": {"gac": {k: gac.get(k) for k in ("eligible", "needed", "derivable", "artifact_id", "artifact_tools", "rejection_by_stage", "gate", "error")},
                    "funnel": {"admitted": {p: [a["tools"] for a in res["artifacts"] if not a["gate_retire"]] for p, res in comp["funnel"]["policies"].items()},
                               "rejection_by_stage": {p: res["rejection_by_stage"] for p, res in comp["funnel"]["policies"].items()},
                               "divergence": comp["funnel"]["divergence"],
                               "majority_bindings": {p: res["majority_bindings"] for p, res in comp["funnel"]["policies"].items()}}},
        "test": {"arms": arms, "compiled_arm_derivable": test.get("compiled_arm_derivable"), "aggregate": aggregate,
                 "comparisons": comparisons, "misses_by_arm": misses, "misses_only_in_arm": only,
                 "recurrence_only_continuation_audit": audit, "stages": test["stages"], "attempts": test["attempts"]},
        "reading": reading(aggregate, n_test, comp),
        "results": test["results"],
    }
    _write("results.json", payload)
    return payload


def reading(aggregate: dict[str, Any], n: int, comp: dict[str, Any]) -> str:
    parts = []
    if not comp["gac"].get("derivable"):
        parts.append("GAC admitted no artifact on the fresh discovery traces, so the compiled arm did not run.")
    for a in ARMS:
        if a in aggregate:
            v = aggregate[a]
            req = v["mean"]["requests"]
            parts.append(f"{a}: {v['factuality_exact']}/{n} exact ({v['failed_after_retry']} incomplete), "
                         + (f"{req:.2f} requests per issue." if req is not None else "no completed episode."))
    div = comp["funnel"]["divergence"]
    parts.append(f"Funnel on fresh discovery: {len(div)} divergent candidate(s) vs the full policy.")
    return " ".join(parts)


# ---------------------------------------------------------------------------- table


def table(results: dict[str, Any] | None = None) -> str:
    results = results or json.loads((OUT_DIR / "results.json").read_text(encoding="utf-8"))
    n = len(results["selection"]["test"])
    agg = results["test"]["aggregate"]
    lines = [r"\begin{tabular}{@{}lrrrrr@{}}", r"\toprule",
             r"Arm & Exact & Requests & Tokens & Latency (s) & Cost (\textcent) \\", r"\midrule"]
    for arm in ARMS:
        if arm not in agg:
            continue
        v = agg[arm]
        m = v["mean"]
        if m["requests"] is None:
            lines.append(f"{ARM_LABELS[arm]} & 0/{n} & -- & -- & -- & -- \\\\")
            continue
        lines.append(f"{ARM_LABELS[arm]} & {v['factuality_exact']}/{n} & {m['requests']:.2f} & {m['total_tokens']:,.0f} & "
                     f"{m['wall_latency_ms'] / 1000:.2f} & {100 * m['estimated_cost_usd']:.3f} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    text = "% generated by paper/scripts/compiler_funnel_live_pilot.py table; do not edit\n" + "\n".join(lines) + "\n"
    return text


# ----------------------------------------------------------------------------- main


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "discovery", "compile", "test", "summarize", "table"))
    parser.add_argument("--approved-spend-usd", type=float, default=None)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    if args.command == "preflight":
        payload = preflight(args)
        print(json.dumps({k: payload[k] for k in ("pool_accounting", "spend")} | {"discovery": DISCOVERY_N, "test": len(payload["selection"]["test"])},
                         indent=2, sort_keys=True))
    elif args.command == "discovery":
        payload = asyncio.run(discovery(args))
        print(json.dumps({k: payload[k] for k in ("attempted", "completed", "eligible", "sequences", "comment_limits", "spent_usd")}, indent=2))
    elif args.command == "compile":
        payload = compile_phase(args)
        gac = payload["gac"]
        print(json.dumps({"gac": {k: gac.get(k) for k in ("eligible", "derivable", "artifact_tools", "rejection_by_stage", "error")},
                          "funnel_admitted": {p: [a["tools"] for a in r["artifacts"] if not a["gate_retire"]] for p, r in payload["funnel"]["policies"].items()},
                          "divergence": [(d["policy"], d["tools"], d["calibration_replay"]) for d in payload["funnel"]["divergence"]]},
                         indent=2, default=str))
    elif args.command == "test":
        payload = asyncio.run(test_phase(args))
        print(json.dumps({"stages": payload["stages"], "spent_usd": payload.get("spent_usd")}, indent=2))
    elif args.command == "summarize":
        payload = summarize(args)
        print(json.dumps({"aggregate": payload["test"]["aggregate"], "reading": payload["reading"], "spend": payload["run"]["estimated_spend_usd"]},
                         indent=2, default=str))
    else:
        text = table()
        TABLE_PATH.write_text(text, encoding="utf-8")
        print(text)


if __name__ == "__main__":
    main()
