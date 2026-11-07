#!/usr/bin/env python3
"""Test the current GAC binder on sealed BIRD list-to-schema transitions.

This is a provider-free, posthoc development diagnostic. The corrected BIRD
question file is an external input; no question or tool payload is published.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tarfile

from bird_schema_selection_probe import build as verify_probe_sources, digest
from guarded_agentic_compaction.grc.dsl import SynthContext
from guarded_agentic_compaction.grc.synthesize import synthesize_binding


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"
PILOT = PAPER / "results/bird_one_call_matched_pilot"
PROBE = PAPER / "results/bird_schema_selection_probe/report.json"
OUT = PAPER / "results/bird_binder_expressivity_audit"


def _attempt(envs: list[dict], targets: list[list[str]], groups: list[str]) -> dict:
    """Use the frozen T-v1 binder with a depth-three, 200-source search."""
    context = SynthContext.from_observations([*envs, *targets], max_depth=3)
    result = synthesize_binding(
        "table_names", envs, targets, groups, ctx=context, max_sources=200
    )
    return {
        "binding_found": result.ok,
        "reason": result.reason,
        "ambiguous_alternatives": result.ambiguous_alternatives,
        # Retain only a source-free operator shape. A successful future audit
        # needs separate inspection before publishing any fitted constants.
        "binding_kind": result.binding.to_dict()["kind"] if result.binding else None,
    }


def build(questions: Path) -> dict:
    verified = verify_probe_sources(questions)
    published_probe = json.loads(PROBE.read_text())
    if verified != published_probe:
        raise ValueError("BIRD schema probe changed since publication")
    pilot = json.loads((PILOT / "report.json").read_text())
    question_rows = json.loads(questions.read_text())
    by_id = {row["question_id"]: row for row in question_rows}
    baseline = [row for row in pilot["rows"] if row["arm"] == "baseline"]
    if len(baseline) != 36 or len(by_id) != len(question_rows):
        raise ValueError("question or baseline denominator drift")

    envs: list[dict] = []
    selected: list[list[str]] = []
    listed: list[list[str]] = []
    groups: list[str] = []
    listed_only_indices: list[int] = []
    with tarfile.open(PILOT / "raw_evidence.tar.gz", "r:gz") as archive:
        for row in baseline:
            task_id = row["question_id"]
            stream = archive.extractfile(f"episodes/{task_id}/baseline/record.json")
            if stream is None:
                raise ValueError("missing sealed baseline record")
            record = json.load(stream)
            if record["question_id"] != task_id or record["db_id"] != row["db_id"]:
                raise ValueError("baseline identity drift")
            tables = json.loads(record["tool_calls"][0]["result"]["payload"])["tables"]
            names = record["tool_calls"][1]["arguments"]["table_names"]
            entry = by_id[task_id]
            envs.append({
                "entry": {
                    "question": entry["question"],
                    "evidence": entry.get("evidence") or "",
                },
                "z0": {"tables": tables},
            })
            listed.append(tables)
            selected.append(names)
            groups.append(row["db_id"])
            if set(names) <= set(tables):
                listed_only_indices.append(len(envs) - 1)

    if len(listed_only_indices) != 35 or len(set(groups)) != 9:
        raise ValueError("BIRD binder sensitivity cohort drift")
    positive = _attempt(envs, listed, groups)
    full = _attempt(envs, selected, groups)
    sensitivity = _attempt(
        [envs[i] for i in listed_only_indices],
        [selected[i] for i in listed_only_indices],
        [groups[i] for i in listed_only_indices],
    )
    if not positive["binding_found"]:
        raise ValueError("list-valued identity positive control failed")
    decision = (
        "NO_EXACT_BINDING_IN_TESTED_T_V1_FAMILY"
        if not full["binding_found"] and not sensitivity["binding_found"]
        else "BINDING_FOUND_REQUIRES_FURTHER_INSPECTION"
    )
    return {
        "schema": "gac-bird-binder-expressivity-audit-v1",
        "scope": "posthoc development audit of baseline-selected schema batches",
        "decision": decision,
        "source": {
            "question_sha256": digest(questions),
            "pilot_report_sha256": digest(PILOT / "report.json"),
            "probe_report_sha256": digest(PROBE),
            "script_sha256": digest(Path(__file__)),
            "dsl_sha256": digest(ROOT / "src/guarded_agentic_compaction/grc/dsl.py"),
            "synthesis_sha256": digest(
                ROOT / "src/guarded_agentic_compaction/grc/synthesize.py"
            ),
        },
        "cases": len(envs),
        "databases": len(set(groups)),
        "listed_only_cases": len(listed_only_indices),
        "library": "T-v1",
        "max_depth": 3,
        "max_sources": 200,
        "positive_control": positive,
        "full_baseline_selection": full,
        "listed_only_sensitivity": sensitivity,
        "provider_calls": 0,
        "gac_artifacts_admitted": 0,
        "matched_arms": 0,
        "independent_test_groups": 0,
        "limitations": [
            "The target is the model-selected schema batch, not gold SQL tables or final-answer success.",
            "The same exposed 36 development cases were inspected before this audit.",
            "A failed exact T-v1 synthesis does not exclude a new learned or semantic selector.",
            "This function-level check is not a full compile, live-tool, continuation, or cost experiment.",
        ],
    }


def render(report: dict) -> str:
    positive = report["positive_control"]
    full = report["full_baseline_selection"]
    sensitivity = report["listed_only_sensitivity"]
    full_result = "an exact binding" if full["binding_found"] else "no exact binding"
    sensitivity_result = (
        "an exact binding" if sensitivity["binding_found"] else "no exact binding"
    )
    return f"""# BIRD list-to-schema binder expressivity audit

**Development decision: {report['decision']}.** The current versioned GAC
binding library was tested against the sealed BIRD baseline's varying
`get_schema(table_names=...)` batches. The corrected question file, published
pilot, and earlier [schema-selection probe](../bird_schema_selection_probe/REPORT.md)
were hash-checked before use. No question, SQL, model response, schema content,
or fitted constant is copied here.

The observed input to the binder contained the entry question and evidence,
plus the preceding `list_tables` result. Across **{report['cases']} cases in
{report['databases']} databases**, depth-{report['max_depth']} search over at
most {report['max_sources']} source paths found **{full_result}** for the
model-selected table lists
(`{full['reason']}`). Excluding the one case that requested a table absent
from the preceding list left **{report['listed_only_cases']} cases** and
again found **{sensitivity_result}**
(`{sensitivity['reason']}`). The same call found an identity binding for
the entire list of available tables in **{report['cases']} cases**; this
positive control verifies that list-valued targets and the grouped-refit path
work (`{positive['binding_kind']}`).

This is an exact reconstruction test of the current `T-v1` library, not a
test of whether a different selector could choose useful tables. The library
has fixed unary transformations and no operator that semantically compares
the entry question with each newly listed table. A new question-conditioned
selector would require a versioned method extension and its own leakage,
grouped-generalization, live-tool, continuation, and matched-control checks.
There was no provider call, new artifact,
matched final-answer arm, cost saving, or independent test.

Reproduce with the pinned corrected BIRD question file:

```sh
python paper/scripts/bird_binder_expressivity_audit.py --questions /path/to/corrected/dev_20251106.json
python paper/scripts/validate_artifacts.py --families bird_binder_expressivity_audit
```

The [machine-readable audit](report.json) retains the code and source hashes,
counts, search bounds, decisions, and limitations. CI checks those public
links and the claim boundary; re-running synthesis requires the external
corrected question file.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    args = parser.parse_args()
    report = build(args.questions)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    (OUT / "REPORT.md").write_text(render(report))
    print(
        f"BIRD binder: {report['cases']} cases; "
        f"decision {report['decision']}"
    )


if __name__ == "__main__":
    main()
