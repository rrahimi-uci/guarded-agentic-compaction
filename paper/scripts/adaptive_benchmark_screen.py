"""Metadata-only, reproducible benchmark selection; never emits reference answers.

Source acquisition is explicit. No providers, environment mutations, or task
outcomes participate in selection. A development cohort is not a calibration seal.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "benchmarks/.cache/adaptive_benchmark_screen"
OUT = ROOT / "paper/results/adaptive_benchmark_screen"
PINS = {
    "tau2-verified": "864350a8971a8f8ee9e7b8472e2edc380a806b0c",
    "webarena": "dce04686a56253aefba7b18a4fa0937cf1dc987b",
    "webarena-verified": "6473f72db5dcefc97b5725b59e734504edc28a21",
}
OLD_TAU = "1eceb0453fe2effa1ba26b6a51fc52b966944ec1"
SEED = "gac-webarena-verified-development-20261106-v1"
# The already inspected upstream Agent JIT catalog plus a task mentioned while
# inspecting its reproduction documentation. Exclude their entire templates.
PRIOR_WEB_IDS = {747, 308, 414, 133, 419, 29, 727, 580, 399, 404, 312, 30, 726}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def check_source(root, pin):
    if git(root, "rev-parse", "HEAD") != pin:
        raise ValueError("source revision mismatch: " + root.name)
    if git(root, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("tracked source modifications: " + root.name)


def tau_overlap(current, previous):
    ids = [str(r["id"]) for r in current]
    old = {str(r["id"]) for r in previous}
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate task IDs")
    # The pinned schema supplies DB+COMMUNICATE when reward_basis is absent.
    bases = Counter("+".join(sorted((r.get("evaluation_criteria") or {}).get(
        "reward_basis", ["DB", "COMMUNICATE"]))) for r in current)
    return {"tasks": len(ids), "prior_source_tasks": len(old),
            "same_id_prior_exposure": sum(i in old for i in ids),
            "unmatched_ids_not_certified_fresh": sum(i not in old for i in ids),
            "reward_basis_counts": dict(sorted(bases.items()))}


def original_web_counts(rows):
    # Conservatively exclude every fuzzy_match configuration, including N/A,
    # whose fallback can still invoke an LLM in the pinned native evaluator.
    eligible = [r for r in rows if "fuzzy_match" not in (r["eval"].get("reference_answers") or {})]
    return {"tasks": len(rows), "templates": len({r["intent_template_id"] for r in rows}),
            "without_fuzzy_match_tasks": len(eligible),
            "without_fuzzy_match_templates": len({r["intent_template_id"] for r in eligible}),
            "fuzzy_match_tasks": len(rows) - len(eligible)}


def select_web_development(rows, count=6):
    if count < 1:
        raise ValueError("positive development count required")
    ids = [r["task_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate task IDs")
    exposed = {r["intent_template_id"] for r in rows if r["task_id"] in PRIOR_WEB_IDS}
    groups = {}
    for row in rows:
        if row["sites"] != ["reddit"] or row["intent_template_id"] in exposed:
            continue
        groups.setdefault(row["intent_template_id"], []).append(row["task_id"])
    rank = lambda value: hashlib.sha256(f"{SEED}:{value}".encode()).hexdigest()
    if len(groups) < count:
        raise ValueError("insufficient development templates; no silent shrink")
    templates = sorted(groups, key=rank)[:count]
    selected = [{"template_id": g, "task_id": sorted(groups[g], key=rank)[0]} for g in templates]
    excluded = exposed | set(templates)
    return {"seed": SEED, "selection_basis": "single-site Reddit; one hash-selected instance per template; no outcome selection",
            "selected": selected, "prior_exposed_templates": sorted(exposed),
            "development_only_templates": sorted(templates),
            "excluded_from_future_confirmation_templates": sorted(excluded),
            "remaining_uninspected_candidate_templates": len({r["intent_template_id"] for r in rows} - excluded),
            "freshness": "Candidate templates only. Prior-use audit is conservative and incomplete; no certified fresh holdout or admission claim."}


def build(cache=CACHE):
    for name, pin in PINS.items():
        check_source(cache / name, pin)
    hashes, tau = {}, {}
    for domain in ("airline", "retail", "telecom"):
        rel = f"data/tau2/domains/{domain}/tasks.json"
        path = cache / "tau2-verified" / rel
        rows = json.loads(path.read_text())
        prior = json.loads(git(cache / "tau2-verified", "show", OLD_TAU + ":" + rel))
        tau[domain] = tau_overlap(rows, prior)
        hashes["tau2-verified/" + rel] = sha(path)
    original_path = cache / "webarena/config_files/test.raw.json"
    verified_path = cache / "webarena-verified/assets/dataset/webarena-verified.json"
    original, verified = (json.loads(p.read_text()) for p in (original_path, verified_path))
    for p in (original_path, verified_path):
        hashes[str(p.relative_to(cache))] = sha(p)
    return {"schema": "gac-adaptive-benchmark-screen-v1", "pins": PINS, "prior_tau_revision": OLD_TAU,
            "source_sha256": hashes, "tau2_verified": tau,
            "original_webarena": original_web_counts(original),
            "webarena_verified": {"tasks": len(verified),
                "templates": len({r["intent_template_id"] for r in verified}),
                "evaluators": dict(sorted(Counter(e["evaluator"] for r in verified for e in r["eval"]).items())),
                "single_site_reddit_tasks": sum(r["sites"] == ["reddit"] for r in verified)},
            "development": select_web_development(verified),
            "decision": "SELECT_WEBARENA_VERIFIED_FOR_DEVELOPMENT_ONLY",
            "confirmation_blockers": ["No calibrated GAC browser candidate or matched comparator integration",
                "No completed task-level prior-use and grouping audit",
                "No independent calibration cohort or power-qualified test cohort",
                "Official evaluators still require positive and negative runtime controls"],
            "provider_calls": 0, "performance_claim": None}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    args = parser.parse_args()
    result = build()
    path = OUT / "screen.json"
    if args.command == "verify":
        if json.loads(path.read_text()) != result:
            raise SystemExit("retained screen differs from pinned inputs")
        print("verified benchmark screen")
    else:
        if path.exists():
            raise SystemExit("retained screen exists; verify or version a new audit")
        OUT.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print("retained benchmark screen; no provider calls")
