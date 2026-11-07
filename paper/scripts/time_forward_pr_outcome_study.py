"""Time-forward PR-outcome study: re-derived artifact, end-to-end calibration labels, evaluation.

Protocol: ``paper/supplementary/time-forward-end-to-end-protocol.md`` (pre-registered
2026-10-07, amended before execution). Phases, each checkpointed under ``--out``:

  selection   write the three disjoint fresh splits (test 60, discovery 132, calibration 132)
  discovery   live: unchanged agent on the discovery records; compile with one frozen candidate
  calibrate   live: dispatch the re-derived artifact on each calibration group, run the
              continuation once, grade the exact contract; single-rule end-to-end certificate
  test        live: baseline, re-derived artifact, retained artifact under its pins, manual
              program on the 60 test records

Live phases refuse to run without ``--approved-spend-usd``; every result's estimated cost is
ledgered and the run stops when the cap would be exceeded. ``--pilot N`` runs the first N
calibration groups and stops. Everything the family study does (tools, prompts, grader,
manifests, compiler) is reused unchanged; only the snapshot identity differs.

Multi-repository mode (protocol ``paper/supplementary/multirepo-unfiltered-end-to-end-protocol.md``).
Every flag below is optional and the default invocation is unchanged:

  --snapshot-dir DIR        directory with ``snapshot.parquet`` and ``source_manifest.json``
  --registry DIR            frozen artifact registry: no discovery, nothing compiled, used for the
                            compiled arm
  --unit author             one pull request per distinct ``user.login`` in calibration, authors
                            disjoint from discovery (and from ``--discovery-authors-file``)
  --discovery-authors-file  logins (JSON list, one per line) or a ``selection.json`` whose
                            ``discovery`` record numbers name them; used with ``--registry``
  --calibration-n N         requested calibration groups (default 132); n = min(N, available);
                            n < 106 writes ``selection.json`` with status ``shortfall_no_run`` and
                            every later phase refuses to run
  --no-test                 no test split and no test phase
  --arms a,b,c              arms among compiled,baseline,manual run on every calibration group
                            (compiled is required); writes ``calibration_groups.json``
  --qualified-exclusion     huggingface/datasets only: exclude just the numbers of retained hf studies
                            (default: legacy rule, any retained result mentioning a number)
  --repo-tag OWNER/NAME     stable rank tag ``multirepo-e2e:<repo>:pr_outcome:<number>``
  --batch-size N            groups per checkpointed batch (default 8 with --arms, else all)
"""

from __future__ import annotations

import argparse
import asyncio
import functools
import hashlib
import json
import os
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from scipy.stats import beta  # noqa: E402

SNAPSHOT_DIR = ROOT / "paper/results/datasets/github_time_forward/huggingface__datasets"
RETAINED_REGISTRY = ROOT / "paper/results/github_workflow_families/pr_outcome/final/registry"
FAMILY = "pr_outcome"
MODEL = "gpt-5.6-luna"
SPLITS = {"test_per_class": 20, "discovery": 132, "calibration": 132}
ALPHA, DELTA = 0.05, 0.10
MIN_CALIBRATION_N = 106  # below this the registered grid cannot admit even at zero violations
ARMS = ("compiled", "baseline", "manual")
ARM_CONDITION = {"compiled": "compiled", "baseline": "baseline", "manual": "manual_pre_model"}
GROUP_ARM_KEYS = ("eligible", "dispatched", "verifier_abstained", "contract_met", "fallback", "requests", "tokens", "latency_ms", "cost_usd")


def cp_upper(k: int, n: int, conf: float) -> float | None:
    if n == 0:
        return None
    if k >= n:
        return 1.0
    if k == 0:
        return 1.0 - (1.0 - conf) ** (1.0 / n)
    return float(beta.ppf(conf, k + 1, n - k))


def _rank(number: int, tag: str | None = None) -> str:
    """Stable rank. ``tag`` None is the retained time-forward tag; else ``multirepo-e2e:<repo>:pr_outcome:<n>``."""
    if tag is None:
        return hashlib.sha256(f"time-forward:{FAMILY}:{number}".encode()).hexdigest()
    return hashlib.sha256(f"multirepo-e2e:{tag}:{FAMILY}:{number}".encode()).hexdigest()


def _rel(path: Path) -> str:
    path = Path(path).resolve()
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def author_of(row: dict[str, Any]) -> str | None:
    user = row.get("user")
    login = user.get("login") if isinstance(user, dict) else None
    return str(login) if login else None


def day_of(row: dict[str, Any]) -> str:
    return str(row.get("created_at"))[:10]


def load_discovery_authors(path: Path, store: dict[int, dict[str, Any]]) -> set[str]:
    """Lower-cased logins from a JSON list / one-per-line file, or from a selection.json's discovery numbers."""
    text = Path(path).read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {line.strip().lower() for line in text.splitlines() if line.strip()}
    if isinstance(payload, dict):
        numbers = payload.get("discovery") or []
        authors = {author_of(store[int(n)]) for n in numbers if int(n) in store}
        missing = [n for n in numbers if int(n) not in store]
        if missing:
            raise RuntimeError(f"{len(missing)} discovery record(s) of {path} are not in the snapshot; supply a login list instead")
        return {a.lower() for a in authors if a}
    return {str(v).strip().lower() for v in payload if str(v).strip()}


def _digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def bind_snapshot(snapshot_dir: Path | None = None):
    """Point the family study at the time-forward snapshot and its identity."""
    import github_live_study as fixed
    import github_workflow_family_study as fam

    snapshot_dir = Path(snapshot_dir) if snapshot_dir is not None else SNAPSHOT_DIR
    manifest = json.loads((snapshot_dir / "source_manifest.json").read_text())
    fam.DATA_PATH = snapshot_dir / "snapshot.parquet"
    fixed.DATA_PATH = snapshot_dir / "snapshot.parquet"
    fixed.HF_REVISION = manifest["parquet_sha256"]
    fixed.HF_PARQUET_SHA256 = manifest["parquet_sha256"]
    fixed.HF_DATASET = f"github-api:{manifest['repository']}:created-after-{manifest['created_after_utc_day']}"
    return fam, fixed, manifest


def select(fam, store: dict[int, dict[str, Any]], used: set[int]) -> dict[str, Any]:
    spec = fam.FAMILIES[FAMILY]
    fresh = sorted((n for n, row in store.items() if row.get("pull_request") and n not in used), key=_rank)
    by_class: dict[str, list[int]] = {}
    for n in fresh:
        by_class.setdefault(spec.class_for(store[n]), []).append(n)
    test: list[int] = []
    for cls in spec.classes:
        pool = by_class.get(cls, [])
        if len(pool) < SPLITS["test_per_class"]:
            raise RuntimeError(f"class {cls} has {len(pool)} fresh records; need {SPLITS['test_per_class']}")
        test.extend(pool[: SPLITS["test_per_class"]])
    remaining = {cls: [n for n in by_class.get(cls, []) if n not in set(test)] for cls in spec.classes}
    discovery: list[int] = []
    while len(discovery) < SPLITS["discovery"]:
        progressed = False
        for cls in spec.classes:
            if remaining[cls] and len(discovery) < SPLITS["discovery"]:
                discovery.append(remaining[cls].pop(0))
                progressed = True
        if not progressed:
            raise RuntimeError("fresh pool exhausted before the discovery split was filled")
    taken = set(test) | set(discovery)
    calibration = [n for n in fresh if n not in taken][: SPLITS["calibration"]]
    if len(calibration) < SPLITS["calibration"]:
        raise RuntimeError(f"only {len(calibration)} calibration records available")
    sel = {
        "schema": "agent-compaction-time-forward-selection/v1", "family": FAMILY, "rule": "stable sha256 rank; test 20 per class; discovery round-robin over classes; calibration next in rank order",
        "fresh_pool": len(fresh), "test": test, "discovery": discovery, "calibration": calibration,
        "test_class_counts": dict(Counter(spec.class_for(store[n]) for n in test)),
        "discovery_class_counts": dict(Counter(spec.class_for(store[n]) for n in discovery)),
        "calibration_class_counts": dict(Counter(spec.class_for(store[n]) for n in calibration)),
        "disjoint": not (set(test) & set(discovery) or set(test) & set(calibration) or set(discovery) & set(calibration)),
    }
    sel["digest"] = _digest({k: sel[k] for k in ("test", "discovery", "calibration")})
    return sel


def select_multirepo(fam, store: dict[int, dict[str, Any]], used: set[int], *, repo_tag: str | None = None, unit: str = "record",
                     calibration_n: int = SPLITS["calibration"], with_test: bool = True, with_discovery: bool = True,
                     excluded_authors: set[str] | frozenset[str] = frozenset(), min_n: int = MIN_CALIBRATION_N) -> dict[str, Any]:
    """Splits for the multi-repository protocol; never raises on a short pool, records the shortfall instead.

    Records are pull requests not in ``used``, ranked by the stable hash. Test (optional): 20 per
    class. Discovery (optional): per-class quota of ``SPLITS['discovery'] / classes`` in round-robin
    order, any shortfall filled in rank order and recorded. Calibration: the next records in rank
    order; with ``unit == "author"`` only the first (lowest-rank) record of each author, skipping
    authors of the discovery split and of ``excluded_authors`` and records without a login, so
    calibration authors are pairwise distinct and disjoint from discovery. ``n = min(requested,
    available)``; ``n < min_n`` gives status ``shortfall_no_run``.
    """
    spec = fam.FAMILIES[FAMILY]
    fresh = sorted((n for n, row in store.items() if fam._is_pr(row) and n not in used), key=lambda n: _rank(n, repo_tag))
    by_class: dict[str, list[int]] = {}
    for n in fresh:
        by_class.setdefault(spec.class_for(store[n]), []).append(n)
    test: list[int] = []
    test_shortfall: dict[str, int] = {}
    if with_test:
        for cls in spec.classes:
            pool = by_class.get(cls, [])
            if len(pool) < SPLITS["test_per_class"]:
                test_shortfall[cls] = SPLITS["test_per_class"] - len(pool)
            test.extend(pool[: SPLITS["test_per_class"]])
    taken = set(test)
    discovery: list[int] = []
    filled = 0
    if with_discovery:
        quota = -(-SPLITS["discovery"] // len(spec.classes))
        remaining = {cls: [n for n in by_class.get(cls, []) if n not in taken] for cls in spec.classes}
        counts = {cls: 0 for cls in spec.classes}
        progressed = True
        while len(discovery) < SPLITS["discovery"] and progressed:
            progressed = False
            for cls in spec.classes:
                if remaining[cls] and counts[cls] < quota and len(discovery) < SPLITS["discovery"]:
                    discovery.append(remaining[cls].pop(0))
                    counts[cls] += 1
                    progressed = True
        if len(discovery) < SPLITS["discovery"]:
            chosen = set(discovery)
            for n in fresh:  # shortfall: fill in rank order from whatever is left
                if len(discovery) >= SPLITS["discovery"]:
                    break
                if n not in taken and n not in chosen:
                    discovery.append(n)
                    chosen.add(n)
                    filled += 1
        taken |= set(discovery)
    discovery_authors = {a.lower() for a in (author_of(store[n]) for n in discovery) if a}
    blocked = {a.lower() for a in excluded_authors} | discovery_authors
    seen: set[str] = set()
    calibration: list[int] = []
    skipped_no_login = 0
    for n in fresh:  # walk the whole pool so the available count is exact; only the first calibration_n are kept
        if n in taken:
            continue
        if unit == "author":
            login = author_of(store[n])
            if login is None:
                skipped_no_login += 1
                continue
            key = login.lower()
            if key in blocked or key in seen:
                continue
            seen.add(key)
        calibration.append(n)
    available = len(calibration)
    calibration = calibration[:calibration_n]
    cal_authors = [author_of(store[n]) for n in calibration]
    n_cal = len(calibration)
    status = "selected" if n_cal >= min_n else "shortfall_no_run"
    sel: dict[str, Any] = {
        "schema": "agent-compaction-multirepo-selection/v1", "status": status, "family": FAMILY, "repository": repo_tag, "unit": unit,
        "rank_tag": "time-forward:pr_outcome:<number>" if repo_tag is None else f"multirepo-e2e:{repo_tag}:pr_outcome:<number>",
        "rule": "stable sha256 rank; test 20 per class (if any); discovery per-class quota round-robin with rank-order fill (if any); "
                "calibration next in rank order, one per distinct author and disjoint in authors from discovery when unit=author",
        "fresh_pool": len(fresh), "fresh_pool_distinct_authors": len({a.lower() for a in (author_of(store[n]) for n in fresh) if a}),
        "test": test, "discovery": discovery, "calibration": calibration,
        "requested_calibration_n": calibration_n, "calibration_available": available, "calibration_n": n_cal, "calibration_shortfall": max(0, calibration_n - n_cal),
        "min_calibration_n": min_n, "test_shortfall": test_shortfall,
        "discovery_requested": SPLITS["discovery"] if with_discovery else 0, "discovery_shortfall": (SPLITS["discovery"] - len(discovery)) if with_discovery else 0,
        "discovery_filled_in_rank_order": filled,
        "test_class_counts": dict(Counter(spec.class_for(store[n]) for n in test)),
        "discovery_class_counts": dict(Counter(spec.class_for(store[n]) for n in discovery)),
        "calibration_class_counts": dict(Counter(spec.class_for(store[n]) for n in calibration)),
        "calibration_distinct_authors": len({a.lower() for a in cal_authors if a}),
        "calibration_distinct_days": len({day_of(store[n]) for n in calibration}),
        "calibration_bot_logins": sum(1 for n in calibration if str((store[n].get("user") or {}).get("type", "")).lower() == "bot" or str(author_of(store[n]) or "").endswith("[bot]")),
        "records_without_login_skipped": skipped_no_login,
        "discovery_authors": len(discovery_authors), "excluded_authors_supplied": len({a.lower() for a in excluded_authors}),
        "disjoint": not (set(test) & set(discovery) or set(test) & set(calibration) or set(discovery) & set(calibration)),
        "author_disjoint_from_discovery": not ({a.lower() for a in cal_authors if a} & (discovery_authors | {a.lower() for a in excluded_authors})),
        "authors_pairwise_distinct": len({a.lower() for a in cal_authors if a}) == sum(1 for a in cal_authors if a) == n_cal if unit == "author" else None,
    }
    sel["digest"] = _digest({k: sel[k] for k in ("test", "discovery", "calibration")})
    return sel


class Ledger:
    def __init__(self, path: Path, cap: float | None) -> None:
        self.path, self.cap = path, cap
        self.state = json.loads(path.read_text()) if path.exists() else {"spent_usd": 0.0, "entries": []}

    def charge(self, phase: str, results: Sequence[Any]) -> None:
        cost = float(sum(float(r.metrics.get("estimated_cost_usd", 0.0)) for r in results))
        self.state["spent_usd"] = round(self.state["spent_usd"] + cost, 6)
        self.state["entries"].append({"phase": phase, "results": len(results), "estimated_cost_usd": round(cost, 6),
                                      "cumulative_usd": self.state["spent_usd"], "at": datetime.now(UTC).isoformat(timespec="seconds")})
        self.path.write_text(json.dumps(self.state, indent=2) + "\n")

    def reserve(self, n_records: int, per_record: float = 0.01) -> None:
        if self.cap is None:
            raise RuntimeError("live phase without --approved-spend-usd")
        if self.state["spent_usd"] + n_records * per_record > self.cap:
            raise RuntimeError(f"reservation {n_records}x{per_record} would exceed cap {self.cap} (spent {self.state['spent_usd']})")


def _public(results: Sequence[Any]) -> list[dict[str, Any]]:
    return [r.public_dict() for r in results]


def arm_group_record(arm: str, result: dict[str, Any] | None, failure: dict[str, Any] | None) -> dict[str, Any]:
    """One arm of one calibration group in the ``calibration_groups.json`` schema (plus ``failed``)."""
    if result is None:
        return {"eligible": None, "dispatched": False, "verifier_abstained": False, "contract_met": False, "fallback": False,
                "requests": 0, "tokens": 0, "latency_ms": 0.0, "cost_usd": 0.0, "failed": True, "error": str((failure or {}).get("error", "no result"))}
    m = result.get("metrics") or {}
    cls = "attempted" if arm == "baseline" else classify_dispatch(result)
    return {"eligible": cls != "ineligible", "dispatched": arm != "baseline" and cls == "attempted",
            "verifier_abstained": arm != "baseline" and cls == "abstained",
            "contract_met": bool((result.get("quality") or {}).get("overall")),
            "fallback": arm != "baseline" and cls != "attempted",
            "requests": int(m.get("requests", 0)), "tokens": int(m.get("total_tokens", 0)),
            "latency_ms": float(m.get("wall_latency_ms", 0.0)), "cost_usd": float(m.get("estimated_cost_usd", 0.0)), "failed": False}


def build_group_records(fam, store: dict[int, dict[str, Any]], selection: dict[str, Any], done: dict[str, Any], arms: Sequence[str], repo: str) -> list[dict[str, Any]]:
    """Per-group records, in selection order, for every group with at least one finished arm."""
    spec = fam.FAMILIES[FAMILY]
    results = {(r["condition"], int(r["issue_number"])): r for r in done["results"]}
    failures = {(f["condition"], int(f["record_number"])): f for f in done["failures"]}
    groups: list[dict[str, Any]] = []
    for n in selection["calibration"]:
        arm_records: dict[str, Any] = {}
        for arm in arms:
            key = (ARM_CONDITION[arm], int(n))
            if key in results:
                arm_records[arm] = arm_group_record(arm, results[key], None)
            elif key in failures:
                arm_records[arm] = arm_group_record(arm, None, failures[key])
        if not arm_records:
            continue
        row = store[int(n)]
        groups.append({"repo": repo, "number": int(n), "author": author_of(row), "created_day": day_of(row), "class": spec.class_for(row), "arms": arm_records})
    return groups


async def calibrate_arms(*, fam, spec, store, selection, arms, registry, source_manifest, continuation_manifest, baseline_manifest, tools, catalog,
                         processor, ledger, out: Path, run_meta, concurrency: int, pilot: int, batch_size: int, repo: str) -> dict[str, Any]:
    """Run every requested arm on every calibration group in checkpointed batches; no retries."""
    from guarded_agentic_compaction.runtime.manual import ManualPreModelRunner

    cal_path = out / "calibration_checkpoint.json"
    done = json.loads(cal_path.read_text()) if cal_path.exists() else {"results": [], "failures": []}
    manual_runner = (ManualPreModelRunner(fam.make_manual_plan(spec, catalog=catalog, source_manifest=source_manifest, continuation_manifest=continuation_manifest), catalog, source_manifest)
                     if "manual" in arms else None)

    def kwargs_for(arm: str) -> dict[str, Any]:
        if arm == "compiled":
            return {"tools": (), "manifest": continuation_manifest, "registry": registry, "artifact_manifest": source_manifest,
                    "fallback_tools": tools, "fallback_manifest": baseline_manifest, "instructions": spec.prompt}
        if arm == "manual":
            return {"tools": (), "manifest": continuation_manifest, "pre_model_runner": manual_runner,
                    "fallback_tools": tools, "fallback_manifest": baseline_manifest, "instructions": spec.prompt}
        return {"tools": tools, "manifest": baseline_manifest, "instructions": spec.prompt}

    def finished() -> set[tuple[str, int]]:  # a recorded failure is final: the protocol has no retry
        return ({(r["condition"], int(r["issue_number"])) for r in done["results"]}
                | {(f["condition"], int(f["record_number"])) for f in done["failures"]})

    def persist() -> None:
        done.update({"schema": "agent-compaction-time-forward-calibration/v1", "run": run_meta, "selection_digest": selection["digest"], "arms": list(arms)})
        cal_path.write_text(json.dumps(done, indent=2, sort_keys=True, default=str) + "\n")
        (out / "calibration_groups.json").write_text(json.dumps(build_group_records(fam, store, selection, done, arms, repo), indent=2, sort_keys=True) + "\n")

    done_keys = finished()
    todo = [n for n in selection["calibration"] if any((ARM_CONDITION[a], int(n)) not in done_keys for a in arms)]
    if pilot:
        todo = todo[:pilot]
    batches = [todo[i:i + batch_size] for i in range(0, len(todo), batch_size)] if todo else []
    for index, batch in enumerate(batches):
        order = list(arms[index % len(arms):]) + list(arms[: index % len(arms)])
        for arm in order:
            pending = [n for n in batch if (ARM_CONDITION[arm], int(n)) not in finished()]
            if not pending:
                continue
            ledger.reserve(len(pending), per_record=0.02)
            results, failures = await fam.run_batch(spec, [store[n] for n in pending], condition=ARM_CONDITION[arm], model_name=MODEL, processor=processor,
                                                    catalog=catalog, store=store, concurrency=concurrency, **kwargs_for(arm))
            ledger.charge(f"calibrate:{arm}", results)
            for r in results:
                d = r.public_dict()
                d["condition"] = ARM_CONDITION[arm]
                done["results"].append(d)
            done["failures"].extend(failures)
            persist()
        print(f"[tf] calibrate batch {index + 1}/{len(batches)} done; spent {ledger.state['spent_usd']:.4f}")
    persist()
    return done


async def main_async(args: argparse.Namespace) -> int:
    multi = any(v is not None for v in (args.snapshot_dir, args.registry, args.calibration_n, args.repo_tag, args.arms, args.discovery_authors_file)) \
        or args.unit != "record" or args.no_test or args.qualified_exclusion
    fam, fixed, snap = bind_snapshot(args.snapshot_dir)
    import github_time_forward_preflight as pre
    from guarded_agentic_compaction.grc.compile import GrcConfig
    from guarded_agentic_compaction.registry.store import Registry
    from guarded_agentic_compaction.runtime.manual import ManualPreModelRunner

    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    spec = fam.FAMILIES[FAMILY]
    store, store_audit = fam.load_store()
    repository = str(snap.get("repository"))
    if multi:
        if args.repo_tag is not None and args.repo_tag != repository:
            raise RuntimeError(f"--repo-tag {args.repo_tag} does not match the snapshot repository {repository}")
        arms = tuple(a.strip() for a in args.arms.split(",") if a.strip()) if args.arms else ()
        arms = arms or ("compiled",)
        if any(a not in ARMS for a in arms) or "compiled" not in arms or len(set(arms)) != len(arms):
            raise RuntimeError(f"--arms must be a comma list drawn from {ARMS} containing compiled")
        used, used_files = pre.used_records(repository, qualified=args.qualified_exclusion, exclude_paths=[out, pre.OWN_STUDY_DIR])
    else:
        arms = ()
        used, _ = pre.used_records()
    sel_path = out / "selection.json"
    if sel_path.exists():
        selection = json.loads(sel_path.read_text())
    else:
        if multi:
            excluded = load_discovery_authors(args.discovery_authors_file, store) if args.discovery_authors_file else set()
            selection = select_multirepo(fam, store, used, repo_tag=args.repo_tag, unit=args.unit,
                                         calibration_n=args.calibration_n if args.calibration_n is not None else SPLITS["calibration"],
                                         with_test=not args.no_test, with_discovery=args.registry is None, excluded_authors=excluded)
            selection.update({"exclusion": "legacy" if repository == pre.HF_REPO and not args.qualified_exclusion else "repository-qualified",
                              "used_record_numbers": len(used), "used_record_files": len(used_files), "snapshot_dir": _rel(args.snapshot_dir or SNAPSHOT_DIR), "registry": _rel(args.registry) if args.registry else None,
                              "discovery_authors_file": str(args.discovery_authors_file) if args.discovery_authors_file else None,
                              "calibration_meta": [{"number": n, "author": author_of(store[n]), "created_day": day_of(store[n]), "class": spec.class_for(store[n])} for n in selection["calibration"]]})
        else:
            selection = select(fam, store, used)
        sel_path.write_text(json.dumps(selection, indent=2) + "\n")
    print(f"[tf] selection digest {selection['digest']} test={len(selection['test'])} discovery={len(selection['discovery'])} calibration={len(selection['calibration'])}")
    if selection.get("status") == "shortfall_no_run":
        print(f"[tf] SHORTFALL: calibration n={selection['calibration_n']} < {selection['min_calibration_n']} (requested {selection['requested_calibration_n']}); no run. See {sel_path}")
        return 0 if args.phase == "selection" else 3
    if args.phase == "selection":
        return 0

    ledger = Ledger(out / "ledger.json", args.approved_spend_usd)
    if args.dry_run:
        report = {"dry_run": True, "phase": args.phase, "records": {k: len(selection[k]) for k in ("test", "discovery", "calibration")},
                  "cap": args.approved_spend_usd, "spent": ledger.state["spent_usd"]}
        if multi:
            report.update({"repository": repository, "arms": list(arms), "registry": str(args.registry) if args.registry else str(out / "registry"),
                           "discovery_skipped": args.registry is not None, "test_skipped": args.no_test, "status": selection.get("status", "selected")})
        print(json.dumps(report))
        return 0
    fam.load_dotenv(ROOT / ".env")
    key_env = fixed.provider_api_key_env(MODEL)
    if not os.getenv(key_env):
        raise RuntimeError(f"{key_env} is not set")
    from agents import add_trace_processor

    processor = fam.AgentsTraceProcessor(include_sensitive_data=True, max_completed=8_000)
    add_trace_processor(processor)
    catalog = fam.make_catalog(spec)
    tools = fam.make_tools(spec, store)
    source_manifest = fam.make_manifest(spec, MODEL, tools, catalog, "source", instructions=spec.discovery_prompt)
    baseline_manifest = fam.make_manifest(spec, MODEL, tools, catalog, "baseline", instructions=spec.prompt)
    continuation_manifest = fam.make_manifest(spec, MODEL, (), catalog, "pre-model", instructions=spec.prompt)
    run_meta = {"timestamp_utc": datetime.now(UTC).isoformat(timespec="seconds"), "family": FAMILY, "model": MODEL, "provider_backed": True,
                "real_public_records": True, "simulated": False, "openai_api_key_used": True, "secrets_serialized": False,
                "snapshot": snap, "store_audit": store_audit, "selection_digest": selection["digest"], "protocol": "paper/supplementary/time-forward-end-to-end-protocol.md"}
    if multi:
        run_meta.update({"protocol": "paper/supplementary/multirepo-unfiltered-end-to-end-protocol.md", "repository": repository, "unit": args.unit,
                         "arms": list(arms), "frozen_registry": str(args.registry) if args.registry else None})
    rows_of = lambda numbers: [store[n] for n in numbers]  # noqa: E731
    frozen = multi and args.registry is not None
    registry_dir = Path(args.registry) if frozen else out / "registry"

    # ---- discovery + re-derivation ------------------------------------------
    disc_path = out / "discovery_checkpoint.json"
    if frozen:
        if args.phase == "discovery":
            print(f"[tf] discovery skipped: frozen registry {registry_dir}")
            return 0
    elif args.phase in ("discovery", "all") or not disc_path.exists():
        if disc_path.exists():
            checkpoint = json.loads(disc_path.read_text())
            discovery = fam.reconstruct_discovery(spec, checkpoint, store=store, manifest=source_manifest)
        else:
            ledger.reserve(len(selection["discovery"]))
            discovery, failures = await fam.run_batch(spec, rows_of(selection["discovery"]), condition="discovery", model_name=MODEL, tools=tools,
                                                      processor=processor, manifest=source_manifest, catalog=catalog, store=store,
                                                      concurrency=args.concurrency, instructions=spec.discovery_prompt)
            ledger.charge("discovery", discovery)
            disc_path.write_text(json.dumps({"schema": "agent-compaction-time-forward-discovery/v1", "run": run_meta, "failures": failures,
                                             "selection": selection, "results": _public(discovery)}, indent=2, sort_keys=True, default=str) + "\n")
        exact = sum(1 for r in discovery if r.quality["overall"])
        print(f"[tf] discovery: {len(discovery)} traces, {exact} exact; spent {ledger.state['spent_usd']:.4f}")
        fam.GrcConfig = functools.partial(GrcConfig, freeze_one_candidate_before_calibration=True)
        try:
            registry, compilation = fam.compile_artifact(spec, discovery, catalog=catalog, source_manifest=source_manifest, continuation_manifest=continuation_manifest)
        except RuntimeError as exc:
            (out / "compile.json").write_text(json.dumps({"status": "retired", "error": str(exc), "run": run_meta}, indent=2, default=str) + "\n")
            print(f"[tf] compile retired: {exc}")
            return 0
        registry.save(out / "registry")
        compilation["frozen_single_candidate"] = True
        (out / "compile.json").write_text(json.dumps({"status": "admitted" if registry.artifacts else "retired", "compilation": compilation, "run": run_meta}, indent=2, sort_keys=True, default=str) + "\n")
        print(f"[tf] compile: {len(registry.artifacts)} artifact(s): {[a.artifact_id for a in registry.artifacts]}")
        if args.phase == "discovery":
            return 0
    registry = Registry.load(registry_dir)
    if not registry.artifacts:
        print("[tf] no re-derived artifact; A2 retires at compilation")
        return 0

    # ---- A2: end-to-end calibration labels -----------------------------------
    cal_path = out / "calibration_checkpoint.json"
    if args.phase in ("calibrate", "all"):
        if arms:
            done = await calibrate_arms(fam=fam, spec=spec, store=store, selection=selection, arms=arms, registry=registry, source_manifest=source_manifest,
                                        continuation_manifest=continuation_manifest, baseline_manifest=baseline_manifest, tools=tools, catalog=catalog,
                                        processor=processor, ledger=ledger, out=out, run_meta=run_meta, concurrency=args.concurrency, pilot=args.pilot,
                                        batch_size=args.batch_size or 8, repo=repository)
        else:
            done = json.loads(cal_path.read_text()) if cal_path.exists() else {"results": [], "failures": []}
            completed = {int(r["issue_number"]) for r in done["results"]}
            todo = [n for n in selection["calibration"] if n not in completed]
            if args.pilot:
                todo = todo[: args.pilot]
            if todo:
                ledger.reserve(len(todo), per_record=0.02)
                results, failures = await fam.run_batch(spec, rows_of(todo), condition="compiled", model_name=MODEL, tools=(), processor=processor,
                                                        manifest=continuation_manifest, catalog=catalog, store=store, concurrency=args.concurrency,
                                                        registry=registry, artifact_manifest=source_manifest, fallback_tools=tools,
                                                        fallback_manifest=baseline_manifest, instructions=spec.prompt)
                ledger.charge("calibrate", results)
                done["results"].extend(_public(results)); done["failures"].extend(failures)
                done.update({"schema": "agent-compaction-time-forward-calibration/v1", "run": run_meta, "selection_digest": selection["digest"]})
                cal_path.write_text(json.dumps(done, indent=2, sort_keys=True, default=str) + "\n")
        summary = certificate(done["results"])
        if arms:
            summary["compiled_arm_failures"] = sorted(int(f["record_number"]) for f in done["failures"] if f["condition"] == "compiled")
        (out / "certificate.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        print(f"[tf] calibration: {json.dumps({k: summary[k] for k in ('n_eligible', 'attempted', 'abstained', 'violations', 'upper_90', 'admits')})}; spent {ledger.state['spent_usd']:.4f}")
        if args.pilot or args.phase == "calibrate":
            return 0

    # ---- C2: time-forward evaluation ------------------------------------------
    if args.phase == "test" and args.no_test:
        print("[tf] --no-test: the test phase is skipped")
        return 0
    if args.phase in ("test", "all") and not args.no_test:
        eval_path = out / "evaluation_checkpoint.json"
        done = json.loads(eval_path.read_text()) if eval_path.exists() else {"results": [], "failures": []}
        completed = {(r["condition"], int(r["issue_number"])) for r in done["results"]}
        retained = None
        try:
            retained = Registry.load(RETAINED_REGISTRY)
        except Exception as exc:  # noqa: BLE001
            done["retained_registry_error"] = str(exc)
        manual_runner = ManualPreModelRunner(fam.make_manual_plan(spec, catalog=catalog, source_manifest=source_manifest, continuation_manifest=continuation_manifest), catalog, source_manifest)
        conditions = ["baseline", "compiled", "manual_pre_model"] + (["compiled_retained"] if retained is not None else [])
        for index, n in enumerate(selection["test"]):
            order = conditions[index % len(conditions):] + conditions[: index % len(conditions)]
            for condition in order:
                if (condition, n) in completed:
                    continue
                kwargs: dict[str, Any] = {"tools": tools, "manifest": baseline_manifest, "instructions": spec.prompt}
                label = condition
                if condition == "compiled":
                    kwargs = {"tools": (), "manifest": continuation_manifest, "registry": registry, "artifact_manifest": source_manifest,
                              "fallback_tools": tools, "fallback_manifest": baseline_manifest, "instructions": spec.prompt}
                elif condition == "compiled_retained":
                    kwargs = {"tools": (), "manifest": continuation_manifest, "registry": retained, "artifact_manifest": source_manifest,
                              "fallback_tools": tools, "fallback_manifest": baseline_manifest, "instructions": spec.prompt}
                    label = "compiled"
                elif condition == "manual_pre_model":
                    kwargs = {"tools": (), "manifest": continuation_manifest, "pre_model_runner": manual_runner,
                              "fallback_tools": tools, "fallback_manifest": baseline_manifest, "instructions": spec.prompt}
                ledger.reserve(1, per_record=0.02)
                results, failures = await fam.run_batch(spec, [store[n]], condition=label, model_name=MODEL, processor=processor, catalog=catalog,
                                                        store=store, concurrency=1, **kwargs)
                ledger.charge(f"test:{condition}", results)
                for r in results:
                    d = r.public_dict(); d["condition"] = condition; done["results"].append(d)
                done["failures"].extend(failures)
                done.update({"schema": "agent-compaction-time-forward-evaluation/v1", "run": run_meta, "selection_digest": selection["digest"], "conditions": conditions})
                eval_path.write_text(json.dumps(done, indent=2, sort_keys=True, default=str) + "\n")
        summary = evaluation_summary(done["results"], conditions)
        (out / "evaluation.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        print(f"[tf] evaluation: {json.dumps(summary['exact'])}; spent {ledger.state['spent_usd']:.4f}")
    return 0


def classify_dispatch(row: dict[str, Any]) -> str:
    d = row.get("dispatch") or {}
    outcome = str(d.get("outcome") or "")
    if outcome in ("REPLAYED", "COMPACTED", "EXECUTED"):  # completed dispatch (compiled or manual plan)
        return "attempted"
    reasons = " ".join(str(x) for x in (d.get("reasons") or [])) + " " + json.dumps(d, default=str)
    if "manifest" in reasons or "guard" in reasons.lower() and "verifier" not in reasons.lower():
        return "ineligible"
    return "abstained"


def certificate(results: Sequence[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[int, dict[str, Any]] = {}
    for r in results:
        if r.get("condition", "compiled") != "compiled":
            continue
        groups[int(r["issue_number"])] = {"class": classify_dispatch(r), "exact": bool(r["quality"].get("overall")), "dispatch": r.get("dispatch")}
    attempted = [g for g in groups.values() if g["class"] == "attempted"]
    abstained = [g for g in groups.values() if g["class"] == "abstained"]
    violations = sum(1 for g in attempted if not g["exact"])
    n = len(attempted) + len(abstained)
    upper = cp_upper(violations, n, 1 - DELTA)
    return {"rule": "single pre-registered acceptance rule; gamma = delta = 0.10; m = 1; violation = contract miss after a completed dispatch; abstention stays in n",
            "n_eligible": n, "attempted": len(attempted), "abstained": len(abstained), "ineligible": sum(1 for g in groups.values() if g["class"] == "ineligible"),
            "violations": violations, "violation_records": sorted(k for k, g in groups.items() if g["class"] == "attempted" and not g["exact"]),
            "upper_90": upper, "admits": bool(upper is not None and upper <= ALPHA), "alpha": ALPHA, "delta": DELTA,
            "floors_at_k": {str(k): next(nn for nn in range(k + 1, 2000) if cp_upper(k, nn, 1 - DELTA) <= ALPHA) for k in range(5)},
            "per_record": {str(k): v for k, v in sorted(groups.items())}}


def evaluation_summary(results: Sequence[dict[str, Any]], conditions: Sequence[str]) -> dict[str, Any]:
    by = {c: {int(r["issue_number"]): r for r in results if r["condition"] == c} for c in conditions}
    out: dict[str, Any] = {"n": {c: len(v) for c, v in by.items()}, "exact": {c: sum(bool(r["quality"].get("overall")) for r in v.values()) for c, v in by.items()},
                           "dispatch": {c: dict(Counter(classify_dispatch(r) for r in v.values())) for c, v in by.items() if c != "baseline"},
                           "mean_metrics": {}}
    for c, v in by.items():
        if v:
            out["mean_metrics"][c] = {k: round(sum(float(r["metrics"].get(k, 0)) for r in v.values()) / len(v), 6) for k in ("requests", "total_tokens", "wall_latency_ms", "estimated_cost_usd")}
    base = by.get("baseline", {})
    if "baseline" in out["mean_metrics"]:
        b = out["mean_metrics"]["baseline"]
        out["reduction_vs_baseline_pct"] = {c: {k: round(100 * (1 - v[k] / b[k]), 1) for k in b if b[k]} for c, v in out["mean_metrics"].items() if c != "baseline"}
    out["compiled_only_misses"] = {c: sorted(k for k, r in v.items() if k in base and base[k]["quality"].get("overall") and not r["quality"].get("overall")) for c, v in by.items() if c != "baseline"}
    return out


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--phase", choices=("selection", "discovery", "calibrate", "test", "all"), default="selection")
    ap.add_argument("--approved-spend-usd", type=float, default=None)
    ap.add_argument("--pilot", type=int, default=0)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", type=Path, default=ROOT / "paper/results/time_forward/pr_outcome")
    ap.add_argument("--snapshot-dir", type=Path, default=None, help="directory with snapshot.parquet and source_manifest.json (default: the huggingface/datasets time-forward snapshot)")
    ap.add_argument("--registry", type=Path, default=None, help="frozen artifact registry for the compiled arm; discovery and compilation are skipped")
    ap.add_argument("--unit", choices=("record", "author"), default="record", help="author: one pull request per distinct user.login in calibration")
    ap.add_argument("--calibration-n", type=int, default=None, help="requested calibration groups (default 132); n = min(requested, available); n < 106 refuses to run")
    ap.add_argument("--no-test", action="store_true", help="no test split and no test phase")
    ap.add_argument("--arms", default=None, help="comma list of compiled,baseline,manual run on every calibration group (compiled required)")
    ap.add_argument("--repo-tag", default=None, help="OWNER/NAME for the stable rank tag multirepo-e2e:<repo>:pr_outcome:<number>; must equal the snapshot repository")
    ap.add_argument("--qualified-exclusion", action="store_true",
                    help="for huggingface/datasets use the repository-qualified exclusion (only hf records of retained hf studies); default keeps the legacy any-repository rule")
    ap.add_argument("--discovery-authors-file", type=Path, default=None, help="logins (JSON list / one per line) or a selection.json; calibration authors are disjoint from them")
    ap.add_argument("--batch-size", type=int, default=0, help="groups per checkpointed batch with --arms (default 8)")
    args = ap.parse_args(argv)
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
