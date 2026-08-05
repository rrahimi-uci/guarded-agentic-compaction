#!/usr/bin/env python3
"""Build the three-family GitHub result ledger and manuscript table."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"
ISSUE_PATH = PAPER / "results/github_natural_replication/results.json"
PR_PATH = PAPER / "results/github_workflow_families/pr_outcome/final/results.json"
BACKLOG_PATH = PAPER / "results/github_workflow_families/backlog_attention/final/results.json"
OUTPUT = PAPER / "results/github_workflow_families/summary.json"
TABLE = PAPER / "tables/github_workflow_families.tex"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def condition_rows(payload: dict[str, Any], condition: str) -> list[dict[str, Any]]:
    return [
        row for row in payload["results"]
        if row["condition"] == condition and int(row.get("repeat", 0)) == 0
    ]


def exact(row: dict[str, Any]) -> bool:
    quality = row["quality"]
    return bool(quality.get("factuality_exact", quality.get("overall", False)))


def totals(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "n": len(rows),
        "exact": sum(exact(row) for row in rows),
        **{
            metric: sum(float(row["metrics"].get(metric) or 0.0) for row in rows)
            for metric in (
                "requests", "tool_calls", "total_tokens", "wall_latency_ms",
                "estimated_cost_usd",
            )
        },
    }


def reduction(before: float, after: float) -> float:
    return 1.0 - after / before if before else 0.0


def family_record(
    *,
    name: str,
    path: Path,
    payload: dict[str, Any],
    baseline: str,
    compiled: str,
    manual: str,
) -> dict[str, Any]:
    baseline_rows = condition_rows(payload, baseline)
    compiled_rows = condition_rows(payload, compiled)
    manual_rows = condition_rows(payload, manual)
    if not (len(baseline_rows) == len(compiled_rows) == len(manual_rows) == 30):
        raise RuntimeError(f"{name}: expected 30 primary rows per condition")
    ids = [
        {int(row["issue_number"]) for row in rows}
        for rows in (baseline_rows, compiled_rows, manual_rows)
    ]
    if not (ids[0] == ids[1] == ids[2]):
        raise RuntimeError(f"{name}: paired record sets differ")
    before = totals(baseline_rows)
    after = totals(compiled_rows)
    manual_totals = totals(manual_rows)
    return {
        "family": name,
        "source": str(path.relative_to(ROOT)),
        "source_sha256": digest(path),
        "record_numbers_sha256": hashlib.sha256(
            ",".join(map(str, sorted(ids[0]))).encode()
        ).hexdigest(),
        "baseline": before,
        "compiled": after,
        "manual": manual_totals,
        "reductions": {
            metric: reduction(before[metric], after[metric])
            for metric in (
                "requests", "tool_calls", "total_tokens", "wall_latency_ms",
                "estimated_cost_usd",
            )
        },
    }


def main() -> None:
    issue = load(ISSUE_PATH)
    pr = load(PR_PATH)
    backlog = load(BACKLOG_PATH)
    families = [
        family_record(
            name="Issue-type routing", path=ISSUE_PATH, payload=issue,
            baseline="baseline", compiled="compiled", manual="macro",
        ),
        family_record(
            name="PR-outcome audit", path=PR_PATH, payload=pr,
            baseline="baseline", compiled="compiled", manual="manual_pre_model",
        ),
        family_record(
            name="Backlog-attention routing", path=BACKLOG_PATH, payload=backlog,
            baseline="baseline", compiled="compiled", manual="manual_pre_model",
        ),
    ]
    overall: dict[str, Any] = {
        "n": sum(int(row["baseline"]["n"]) for row in families),
        "baseline_exact": sum(int(row["baseline"]["exact"]) for row in families),
        "compiled_exact": sum(int(row["compiled"]["exact"]) for row in families),
        "manual_exact": sum(int(row["manual"]["exact"]) for row in families),
    }
    for metric in (
        "requests", "tool_calls", "total_tokens", "wall_latency_ms",
        "estimated_cost_usd",
    ):
        before = sum(float(row["baseline"][metric]) for row in families)
        after = sum(float(row["compiled"][metric]) for row in families)
        overall[metric] = {
            "baseline": before,
            "compiled": after,
            "reduction": reduction(before, after),
        }
    payload = {
        "schema": "agent-compaction-github-workflow-family-summary/v1",
        "evidence_class": "real public GitHub records + live OpenAI provider + exact source-grounded contracts",
        "simulated": False,
        "families": families,
        "overall": overall,
        "metric_note": (
            "tool_calls counts provider-visible tool interfaces; compiled/manual pre-model "
            "conditions retain three verified internal reads"
        ),
        "claim_boundary": (
            "all records come from one revision-pinned repository snapshot; this is "
            "workflow-family, not cross-repository or time-forward, generalization"
        ),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        r"\begin{tabular}{@{}lrrrrrr@{}}",
        r"\toprule",
        r"Family & Exact $B\!\to\!C$ & Requests & Interfaces & Tokens & Latency & Cost \\",
        r"\midrule",
    ]
    for row in families:
        r = row["reductions"]
        lines.append(
            f"{row['family']} & {int(row['baseline']['exact'])}/30$\\to$"
            f"{int(row['compiled']['exact'])}/30 & "
            f"{100*r['requests']:.1f}\\% & {100*r['tool_calls']:.1f}\\% & "
            f"{100*r['total_tokens']:.1f}\\% & {100*r['wall_latency_ms']:.1f}\\% & "
            f"{100*r['estimated_cost_usd']:.1f}\\% \\\\"
        )
    lines.extend(
        [
            r"\midrule",
            f"Weighted total & {overall['baseline_exact']}/90$\\to$"
            f"{overall['compiled_exact']}/90 & "
            f"{100*overall['requests']['reduction']:.1f}\\% & "
            f"{100*overall['tool_calls']['reduction']:.1f}\\% & "
            f"{100*overall['total_tokens']['reduction']:.1f}\\% & "
            f"{100*overall['wall_latency_ms']['reduction']:.1f}\\% & "
            f"{100*overall['estimated_cost_usd']['reduction']:.1f}\\% \\\\ ",
            r"\bottomrule",
            r"\end{tabular}",
        ]
    )
    TABLE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)} and {TABLE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
