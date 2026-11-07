#!/usr/bin/env python3
"""Audit whether exposed BIRD traces support a dependent two-read candidate.

This is a posthoc, provider-free diagnostic. The corrected question file stays
outside the publication tree; only aggregate counts and source hashes are written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"
PILOT = PAPER / "results/bird_one_call_matched_pilot"
OUT = PAPER / "results/bird_schema_selection_probe"
SCRIPT = PAPER / "scripts/bird_schema_selection_probe.py"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _request_tools(record: dict, turn: int) -> list[str]:
    response = record["provider_trace"][turn]["response"]
    message = response["choices"][0]["message"]
    return [call["function"]["name"] for call in message.get("tool_calls") or []]


def build(questions: Path, archive: Path = PILOT / "raw_evidence.tar.gz") -> dict:
    seal_path = PILOT / "seal.json"
    pilot_path = PILOT / "report.json"
    seal = json.loads(seal_path.read_text())
    pilot = json.loads(pilot_path.read_text())
    if digest(questions) != seal["question_sha256"]:
        raise ValueError("corrected BIRD question hash drift")
    if digest(archive) != pilot["archive_sha256"]:
        raise ValueError("sealed BIRD raw archive hash drift")
    if digest(seal_path) != pilot["seal_sha256"]:
        raise ValueError("sealed BIRD pilot seal hash drift")

    source_rows = json.loads(questions.read_text())
    by_id = {row["question_id"]: row for row in source_rows}
    if len(by_id) != len(source_rows):
        raise ValueError("duplicate question ID in corrected source")
    baseline = [row for row in pilot["rows"] if row["arm"] == "baseline"]
    if len(baseline) != 36 or len({row["question_id"] for row in baseline}) != 36:
        raise ValueError("baseline denominator or IDs changed")

    listed_counts: list[int] = []
    selected_counts: list[int] = []
    literal_exact = literal_nonempty = literal_hits = target_count = 0
    all_exact = second_request_schema = 0
    unlisted_cases = unlisted_occurrences = 0
    with tarfile.open(archive, "r:gz") as bundle:
        members = {member.name: member for member in bundle.getmembers() if member.isfile()}
        for row in baseline:
            task_id = row["question_id"]
            name = f"episodes/{task_id}/baseline/record.json"
            member = members.get(name)
            if member is None:
                raise ValueError(f"missing sealed baseline record {task_id}")
            stream = bundle.extractfile(member)
            if stream is None:
                raise ValueError(f"unreadable sealed baseline record {task_id}")
            raw = stream.read()
            if hashlib.sha256(raw).hexdigest() != row["raw_sha256"]:
                raise ValueError(f"baseline record hash drift {task_id}")
            record = json.loads(raw)
            question = by_id.get(task_id)
            if (question is None or record["question_id"] != task_id
                    or record["db_id"] != row["db_id"]
                    or record["arm"] != "baseline" or record["status"] != "completed"):
                raise ValueError(f"baseline identity or status drift {task_id}")
            calls = record["tool_calls"]
            if (len(calls) < 2 or calls[0]["tool"] != "list_tables"
                    or calls[1]["tool"] != "get_schema"):
                raise ValueError(f"two-read trace shape drift {task_id}")
            available = json.loads(calls[0]["result"]["payload"])["tables"]
            selected = calls[1]["arguments"]["table_names"]
            if (not isinstance(available, list) or not isinstance(selected, list)
                    or not selected or len(set(available)) != len(available)
                    or len(set(selected)) != len(selected)):
                raise ValueError(f"malformed table listing or selection {task_id}")
            unlisted = set(selected) - set(available)
            unlisted_cases += bool(unlisted)
            unlisted_occurrences += len(unlisted)
            if _request_tools(record, 0) != ["list_tables"]:
                raise ValueError(f"first request shape drift {task_id}")
            if _request_tools(record, 1) == ["get_schema"]:
                second_request_schema += 1

            # Deliberately simple, posthoc diagnostic: literal casefolded table
            # names in the entry question or evidence. No answer or SQL is read.
            entry = (question["question"] + " " + str(question.get("evidence") or "")).casefold()
            literal = {table for table in available if table.casefold() in entry}
            target = set(selected)
            listed_counts.append(len(available))
            selected_counts.append(len(selected))
            literal_nonempty += bool(literal)
            literal_exact += literal == target
            literal_hits += len(literal & target)
            target_count += len(target)
            all_exact += set(available) == target

    if sum(row["shape_set_correct"] for row in baseline) != pilot["summary"]["baseline"]["correct"]:
        raise ValueError("baseline quality count drift")
    return {
        "schema": "gac-bird-schema-selection-probe-v1",
        "decision": "NO_GO_FOR_PAID_DEPENDENT_SCHEMA_CANDIDATE",
        "scope": "posthoc provider-free diagnostic on 36 exposed BIRD development cases",
        "source": {
            "question_sha256": digest(questions),
            "archive_sha256": digest(archive),
            "pilot_seal_sha256": digest(seal_path),
            "pilot_report_sha256": digest(pilot_path),
            "script_sha256": digest(SCRIPT),
        },
        "baseline": {
            "cases": len(baseline),
            "correct": pilot["summary"]["baseline"]["correct"],
            "first_two_calls_list_then_schema": len(listed_counts),
            "schema_in_second_model_request": second_request_schema,
            "listed_table_occurrences": sum(listed_counts),
            "selected_table_occurrences": sum(selected_counts),
            "median_listed_tables": statistics.median(listed_counts),
            "median_selected_tables": statistics.median(selected_counts),
            "cases_with_unlisted_selected_table": unlisted_cases,
            "unlisted_selected_table_occurrences": unlisted_occurrences,
        },
        "literal_name_probe": {
            "definition": "casefolded exact table-name substring in question plus evidence; no fallback",
            "nonempty_cases": literal_nonempty,
            "exact_batches": literal_exact,
            "target_hits": literal_hits,
            "target_total": target_count,
        },
        "all_tables_probe": {
            "exact_baseline_batches": all_exact,
            "prefetch_table_occurrences": sum(listed_counts),
            "baseline_selected_table_occurrences": sum(selected_counts),
        },
        "provider_calls": 0,
        "new_gac_candidates": 0,
        "matched_arms": 0,
        "independent_test_groups": 0,
        "limitations": [
            "The selector and audit were chosen after exposure to these development traces.",
            "Matching a baseline table set is a surrogate, not a final-answer or cost test.",
            "Fetching every table's schema changes the model context and may increase tokens; it was not executed.",
            "The same selector or all-table prefetch is available to a handwritten control.",
        ],
    }


def render(report: dict) -> str:
    baseline = report["baseline"]
    literal = report["literal_name_probe"]
    all_tables = report["all_tables_probe"]
    return f"""# BIRD dependent schema-read feasibility probe

**Development decision: no paid matched arm for the tested selectors.** This
provider-free posthoc audit inspects the already exposed 36-case BIRD baseline
in the [sealed matched pilot](../bird_one_call_matched_pilot/REPORT.md). It
verifies the corrected public question-file hash, the published raw archive
and pilot seal, and every baseline record hash before counting. No question,
evidence, SQL, tool result, model response or protected database content is
copied into this report.

All **{baseline['cases']}/{baseline['cases']}** baseline traces opened with
`list_tables` followed by `get_schema`; the schema call occupied the second
model request in **{baseline['schema_in_second_model_request']}/{baseline['cases']}**.
The baseline selected **{baseline['selected_table_occurrences']}** table
occurrences from **{baseline['listed_table_occurrences']}** listed occurrences
(median **{baseline['median_selected_tables']:g}** selected versus
**{baseline['median_listed_tables']:g}** listed per case). It answered
**{baseline['correct']}/{baseline['cases']}** development questions correctly.
In **{baseline['cases_with_unlisted_selected_table']}** case, its schema request
included **{baseline['unlisted_selected_table_occurrences']}** table name absent
from the immediately preceding listing; a literal selector limited to listed
names cannot reproduce that request.
This exposes at most one *additional* model-request boundary beyond the
already tested one-call `list_tables` prefetch; it is not an executed saving.

The deliberately simple literal-name rule selects tables whose full names
occur case-insensitively in the entry question or evidence. It selects at
least one table in **{literal['nonempty_cases']}/{baseline['cases']}** cases,
matches the entire baseline-selected set in **{literal['exact_batches']}/{baseline['cases']}**,
and recovers **{literal['target_hits']}/{literal['target_total']}** selected-table
occurrences. It has no safe behavior when it selects no table. A proposed
`get_schema` call for *all* listed tables would match the baseline's selected
set in only **{all_tables['exact_baseline_batches']}/{baseline['cases']}** cases
and request **{all_tables['prefetch_table_occurrences']}** table schemas versus
**{all_tables['baseline_selected_table_occurrences']}** in the observed baseline.
That all-table path may change continuation quality and token cost; neither
path was executed or evaluated on final answers.

These observations do not prove that no semantic selector could work. They
show that the specific literal rule is too weak and that fetching every schema
is a different, potentially expensive context. Both rules are equally
available to a handwritten workflow. The exposed cases cannot serve as fresh
calibration or independent evaluation of a tuned selector. There is no new
admitted GAC artifact, matched comparison, quality--cost claim, or charge to
the shared $300 API budget. The paper's development-gate conclusion remains
unchanged.

Reproduce with the pinned corrected question file and retained archive:

```sh
python paper/scripts/bird_schema_selection_probe.py \\
  --questions /path/to/corrected/dev_20251106.json
python paper/scripts/validate_artifacts.py --families bird_schema_selection_probe
```

The exact baseline record hashes and source versions are recorded in the
referenced pilot seal, report and [machine-readable probe](report.json).
CI can check their published hash links and this report's claim boundary;
recomputing literal matches also needs the pinned external question file.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", required=True, type=Path)
    parser.add_argument("--archive", type=Path, default=PILOT / "raw_evidence.tar.gz")
    args = parser.parse_args()
    report = build(args.questions, args.archive)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (OUT / "REPORT.md").write_text(render(report))
    print(f"BIRD schema probe: {report['baseline']['cases']} cases; "
          f"literal exact {report['literal_name_probe']['exact_batches']}; "
          f"decision {report['decision']}")


if __name__ == "__main__":
    main()
