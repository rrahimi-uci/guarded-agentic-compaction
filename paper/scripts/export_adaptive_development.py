"""Publish complete development evidence without promoting it to paper results."""
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import tarfile

from adaptive_benchmark_screen import CACHE, OUT, ROOT, sha


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def summarize(seal, attempts):
    expected = set(seal["tasks"])
    ids = [row["task_id"] for row in attempts]
    if set(ids) != expected or len(ids) != len(expected):
        raise ValueError("every scheduled task must have exactly one terminal attempt")
    if any(r["status"] not in {"completed", "failed"} for r in attempts):
        raise ValueError("unfinished attempt; do not publish as a complete pilot")
    return {"scheduled": len(expected), "attempted": len(attempts),
        "successes": sum(r["status"] == "completed" and r.get("evaluation", {}).get("status") == "success" for r in attempts),
        "attempt_statuses": dict(sorted(Counter(r["status"] for r in attempts).items())),
        "termination_reasons": dict(sorted(Counter(r.get("termination", "infrastructure_error") for r in attempts).items())),
        "evaluation_statuses": dict(sorted(Counter(r.get("evaluation", {}).get("status", "unscored") for r in attempts).items())),
        "provider_requests": sum(len(r.get("provider_trace", [])) for r in attempts),
        "browser_actions": sum(len(r.get("actions", [])) for r in attempts),
        "browser_action_errors": sum("error" in a["observation"] for r in attempts for a in r.get("actions", [])),
        "interpretation": "Development baseline only; not a GAC comparison, independent holdout, calibrated admission, or efficiency result."}


def export():
    public = OUT / "webarena_development"
    if (public / "report.json").exists():
        raise ValueError("retained export exists; do not overwrite")
    local = CACHE / "development-v2"
    seal = json.loads((local / "seal.json").read_text())
    attempts = [json.loads((local / str(task) / "attempt.json").read_text()) for task in seal["tasks"]]
    summary = summarize(seal, attempts)
    ledger = json.loads((ROOT / "benchmarks/.cache/adaptive_compiler_pilot/ledger.json").read_text())
    charges = [r for r in ledger["requests"] if r["task"].startswith("webdev-v2:")]
    # Never clear or rewrite the authoritative cross-study ledger.
    summary["campaign_accounted_upper_usd"] = ledger["accounted_upper_usd"]
    summary["pilot_accounted_upper_usd"] = sum(r.get("accounted_upper_usd", r["reserved_usd"]) for r in charges)
    summary["remaining_campaign_cap_usd"] = ledger["cap_usd"] - ledger["accounted_upper_usd"]
    summary["cost_scope"] = "Conservative API ledger accounting, not a provider invoice; includes unknown-usage reservations. Local compute is not priced."
    summary["ledger_requests"] = len(charges)
    public.mkdir(parents=True, exist_ok=True)
    write(public / "seal.json", seal)
    write(public / "ledger_excerpt.json", {"requests": charges})
    controls = json.loads((local / "controls.json").read_text())
    rows = [{"task_id": r["task_id"], "status": r["status"], "termination": r.get("termination"),
             "evaluation_status": r.get("evaluation", {}).get("status"),
             "provider_requests": len(r.get("provider_trace", [])), "browser_actions": len(r.get("actions", []))}
            for r in attempts]
    inputs = []
    archive = public / "raw_evidence.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for version in ("development", "development-v2"):
            for path in sorted((CACHE / version).rglob("*")):
                if not path.is_file() or path.suffix in {".lock", ".tmp"}:
                    continue
                relative = str(path.relative_to(CACHE))
                tar.add(path, arcname=relative, recursive=False)
                inputs.append({"path": relative, "sha256": sha(path), "bytes": path.stat().st_size})
        license_path = CACHE / "webarena-verified/LICENSE"
        tar.add(license_path, arcname="upstream/LICENSE", recursive=False)
    report = {"schema": "gac-webarena-development-report-v1", "summary": summary, "rows": rows,
        "controls": {"all_passed": controls["all_passed"], "negative": controls["negative_controls"],
            "positive_task_id": 634, "positive_status": controls["positive_control"]["status"],
            "scope": "One actual browser mutation positive control; twelve no-action negative controls. Not full per-task oracle validation."},
        "upstream_unit_validation": {"passed": 469, "skipped": 4,
            "scope": "tests/core/evaluation and tests/types; ignore SyntaxWarning from unmodified dependency geocoder under Python 3.13",
            "log_sha256": sha(Path("/tmp/gac-webarena-grader-tests-v2.log"))},
        "raw_archive_sha256": sha(archive), "raw_files": inputs,
        "source_hashes": {"paper/scripts/export_adaptive_development.py": sha(Path(__file__))},
        "publication": "No manuscript performance claim updated. Synthetic benchmark account only. No hidden evaluation fields sent in model prompts."}
    (public / "upstream_unit_validation.txt").write_bytes(Path("/tmp/gac-webarena-grader-tests-v2.log").read_bytes())
    write(public / "report.json", report)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    export()
