"""Select a bounded development extension without consulting task text or answers.

This is a feasibility audit, not an experiment seal or permission to spend. Whole
templates selected here become development-only even if feasibility fails.
"""
import argparse
import hashlib
import json
from pathlib import Path

from adaptive_benchmark_screen import CACHE, PINS, ROOT, check_source, sha

OUT = ROOT / "paper/results/adaptive_comparison_followup"
SEED = "gac-batched-development-20261106-v1"
PRIOR = ROOT / "paper/results/adaptive_benchmark_screen/screen.json"
DATA = CACHE / "webarena-verified/assets/dataset/webarena-verified.json"


def select(rows, prior, count=4):
    if type(count) is not int or count < 1:
        raise ValueError("positive count required")
    ids = [r["task_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate task IDs")
    excluded = set(prior["development"]["excluded_from_future_confirmation_templates"])
    groups = {}
    for row in rows:
        if row["sites"] == ["reddit"] and row["intent_template_id"] not in excluded:
            groups.setdefault(row["intent_template_id"], []).append(row["task_id"])
    if len(groups) < count:
        raise ValueError("insufficient templates; no silent cohort reduction")
    rank = lambda value: hashlib.sha256(f"{SEED}:{value}".encode()).hexdigest()
    chosen = sorted(groups, key=rank)[:count]
    return {"seed": SEED, "selection_basis": "single-site Reddit; hash order over unexcluded template IDs, then task IDs; no intent, evaluator, or outcome selection",
            "selected": [{"template_id": g, "task_id": sorted(groups[g], key=rank)[0]} for g in chosen],
            "remaining_reddit_candidate_templates": len(groups) - count,
            "excluded_from_future_confirmation_templates": sorted(excluded | set(chosen)),
            "scope": "development only; unexcluded does not mean fresh or independent"}


def build():
    check_source(CACHE / "webarena-verified", PINS["webarena-verified"])
    return {"schema": "gac-adaptive-followup-selection-v1",
            "source_revision": PINS["webarena-verified"],
            "source_hashes": {str(p.relative_to(ROOT)): sha(p) for p in (DATA, PRIOR, Path(__file__))},
            **select(json.loads(DATA.read_text()), json.loads(PRIOR.read_text())),
            "provider_calls": 0, "decision": "INSPECT_SELECTED_DEVELOPMENT_ONLY",
            "paid_execution_gate": "A separate runner seal, valid controls, audited useful read regions, and a strong batched baseline are required. This selection alone does not authorize a comparative run."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    args = parser.parse_args()
    result = build()
    target = OUT / "selection.json"
    if args.command == "verify":
        if json.loads(target.read_text()) != result:
            raise SystemExit("retained selection differs from pinned inputs")
        print("verified development extension; no provider calls")
    else:
        if target.exists():
            raise SystemExit("selection exists; do not overwrite")
        OUT.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(json.dumps(result["selected"]))
