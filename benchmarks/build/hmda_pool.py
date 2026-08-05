"""Build a privacy-bounded 420-group HMDA pool from official public CSV files."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from agent_compaction.evaluation import BenchmarkCase
from benchmarks.adapters.store import canonical
from benchmarks.gold import hmda_gold_from_records


SCHEMA = "agent-compaction-hmda-snapshot/v1"
PUBLIC_SCHEMA_URL = (
    "https://ffiec.cfpb.gov/documentation/publications/loan-level-datasets/"
    "filing-instructions-guide"
)
PUBLIC_FIELDS_URL = (
    "https://ffiec.cfpb.gov/documentation/publications/loan-level-datasets/"
)
DATA_URL = "https://ffiec.cfpb.gov/v2/data-browser-api/view/csv"

LABELS: dict[str, dict[str, str]] = {
    "action_taken": {
        "1": "Loan originated",
        "2": "Application approved but not accepted",
        "3": "Application denied",
        "4": "Application withdrawn by applicant",
        "5": "File closed for incompleteness",
        "6": "Purchased loan",
        "7": "Preapproval request denied",
        "8": "Preapproval request approved but not accepted",
    },
    "preapproval": {"1": "Preapproval requested", "2": "Preapproval not requested"},
    "loan_type": {
        "1": "Conventional",
        "2": "FHA insured",
        "3": "VA guaranteed",
        "4": "USDA Rural Housing Service or Farm Service Agency guaranteed",
    },
    "loan_purpose": {
        "1": "Home purchase",
        "2": "Home improvement",
        "31": "Refinancing",
        "32": "Cash-out refinancing",
        "4": "Other purpose",
        "5": "Not applicable",
    },
    "lien_status": {"1": "Secured by a first lien", "2": "Secured by a subordinate lien"},
    "occupancy_type": {
        "1": "Principal residence",
        "2": "Second residence",
        "3": "Investment property",
    },
    "denial_reason": {
        "1": "Debt-to-income ratio",
        "2": "Employment history",
        "3": "Credit history",
        "4": "Collateral",
        "5": "Insufficient cash",
        "6": "Unverifiable information",
        "7": "Credit application incomplete",
        "8": "Mortgage insurance denied",
        "9": "Other",
        "10": "Not applicable",
    },
}

SAFE_ROW_FIELDS = (
    "activity_year",
    "lei",
    "action_taken",
    "preapproval",
    "loan_type",
    "loan_purpose",
    "lien_status",
    "occupancy_type",
    "derived_dwelling_category",
    "reverse_mortgage",
    "open-end_line_of_credit",
    "business_or_commercial_purpose",
    "construction_method",
    "manufactured_home_secured_property_type",
    "manufactured_home_land_property_interest",
    "total_units",
    "denial_reason-1",
    "denial_reason-2",
    "denial_reason-3",
    "denial_reason-4",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _row_digest(row: Mapping[str, str]) -> str:
    return hashlib.sha256(canonical(dict(row)).encode("utf-8")).hexdigest()


def _safe_row(row: Mapping[str, str], *, raw_digest: str, year: int) -> dict[str, Any]:
    safe = {field: row.get(field, "") for field in SAFE_ROW_FIELDS}
    safe["raw_row_digest"] = raw_digest
    safe["sources"] = []  # populated once source digests are known
    if safe["activity_year"] != str(year):
        raise ValueError("CSV activity_year does not match declared input year")
    return safe


def _candidate_score(row: Mapping[str, str]) -> tuple[int, int, str]:
    action = row.get("action_taken", "")
    rare_action = {"7": 8, "8": 7, "5": 6, "4": 5, "3": 4, "2": 3, "6": 2, "1": 1}.get(action, 0)
    hard = sum(
        row.get(field, "") in {"NA", "Exempt", "1111", ""}
        for field in ("reverse_mortgage", "open-end_line_of_credit", "denial_reason-1")
    )
    return rare_action, hard, _row_digest(row)


def _choose_rows(
    csv_inputs: Sequence[tuple[int, Path]],
    minimum_groups: int,
    source_urls: Mapping[int, str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_lei_year: dict[str, dict[int, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
    input_report: list[dict[str, Any]] = []
    total_rows = 0
    fieldnames_by_year: dict[int, list[str]] = {}
    for year, path in sorted(csv_inputs):
        rows = 0
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames_by_year[year] = list(reader.fieldnames or [])
            missing = sorted(set(SAFE_ROW_FIELDS) - set(reader.fieldnames or []))
            if missing:
                raise ValueError(f"{path} is missing required public fields: {', '.join(missing)}")
            for row in reader:
                rows += 1
                by_lei_year[row["lei"]][year].append(row)
        total_rows += rows
        input_report.append(
            {
                "year": year,
                "file_name": path.name,
                "source_url": source_urls[year],
                "sha256": _sha256_file(path),
                "rows": rows,
            }
        )
    if len(by_lei_year) < minimum_groups:
        raise ValueError(f"only {len(by_lei_year)} unique LEIs; {minimum_groups} required")

    # Stable ranking chooses exactly the required number of independent filers.
    selected_leis = sorted(
        by_lei_year,
        key=lambda lei: (hashlib.sha256(f"20260804:{lei}".encode()).hexdigest(), lei),
    )[:minimum_groups]
    selected: list[dict[str, Any]] = []
    for index, lei in enumerate(selected_leis):
        available_years = sorted(by_lei_year[lei])
        preferred = available_years[index % len(available_years)]
        candidates = by_lei_year[lei][preferred]
        row = max(candidates, key=_candidate_score)
        selected.append(dict(row))
    report = {
        "schema": "agent-compaction-hmda-pool-report/v1",
        "real_public_records": True,
        "provider_calls_executed": 0,
        "input_files": input_report,
        "total_input_rows": total_rows,
        "unique_input_leis": len(by_lei_year),
        "selected_groups": len(selected),
        "excluded_groups": len(by_lei_year) - len(selected),
        "selected_years": dict(sorted(Counter(row["activity_year"] for row in selected).items())),
        "selected_actions": dict(sorted(Counter(row["action_taken"] for row in selected).items())),
        "protected_demographic_fields_exposed_to_tools": False,
        "fieldnames_by_year": {str(year): names for year, names in sorted(fieldnames_by_year.items())},
    }
    return selected, report


def _label_records(years: Iterable[int]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for year in years:
        for field, values in LABELS.items():
            target_fields = [f"denial_reason-{index}" for index in range(1, 5)] if field == "denial_reason" else [field]
            for target in target_fields:
                for value, label in values.items():
                    labels[f"{year}:{target}:{value}"] = label
        # The derived dwelling category is already a public label, but preserving
        # it through the same lookup contract keeps the macro field-generic.
        for value in (
            "Single Family (1-4 Units):Site-Built",
            "Single Family (1-4 Units):Manufactured",
            "Multifamily:Site-Built",
            "Multifamily:Manufactured",
        ):
            labels[f"{year}:derived_dwelling_category:{value}"] = value
    return labels


def build_pool(
    csv_inputs: Sequence[tuple[int, Path]],
    output_dir: str | Path,
    *,
    minimum_groups: int = 420,
    source_urls: Mapping[int, str] | None = None,
) -> dict[str, Any]:
    resolved_urls = dict(source_urls or {})
    for year, _path in csv_inputs:
        resolved_urls.setdefault(year, f"{DATA_URL}?years={year}&states=RI")
    if any(not url.startswith("https://") for url in resolved_urls.values()):
        raise ValueError("HMDA source URLs must use HTTPS")
    selected, report = _choose_rows(csv_inputs, minimum_groups, resolved_urls)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    years = sorted({int(row["activity_year"]) for row in selected})
    labels = _label_records(years)
    # The acquisition report retains the complete public CSV header for audit,
    # but the model-visible schema is deliberately limited to the same safe
    # allowlist as the row facade. Merely hiding protected values while exposing
    # their columns would violate the benchmark's declared privacy boundary.
    schema_records = {
        str(year): {"year": year, "fields": list(SAFE_ROW_FIELDS)}
        for year in years
    }
    definitions = {
        f"{year}:{field}": {"year": year, "field": field, "source": PUBLIC_FIELDS_URL}
        for year in years
        for field in SAFE_ROW_FIELDS
    }
    rows: dict[str, Any] = {}
    source_file_by_year = {item["year"]: item for item in report["input_files"]}
    for raw in selected:
        year = int(raw["activity_year"])
        raw_digest = _row_digest(raw)
        rows[f"{year}:{raw['lei']}:{raw_digest}"] = _safe_row(
            raw, raw_digest=raw_digest, year=year
        )
    records = {
        "rows": rows,
        "schemas": schema_records,
        "definitions": definitions,
        "filers": {
            f"{year}:{row['lei']}": {"lei": row["lei"], "name": None}
            for row in selected
            for year in (int(row["activity_year"]),)
        },
        "labels": labels,
    }
    snapshot_digest = hashlib.sha256(canonical(records).encode("utf-8")).hexdigest()
    schema_digest = hashlib.sha256(canonical(schema_records).encode("utf-8")).hexdigest()
    definition_digest = hashlib.sha256(canonical({"definitions": definitions, "labels": labels}).encode("utf-8")).hexdigest()

    cases: list[dict[str, Any]] = []
    gold: list[dict[str, Any]] = []
    for raw in selected:
        year = int(raw["activity_year"])
        raw_digest = _row_digest(raw)
        row_key = f"{year}:{raw['lei']}:{raw_digest}"
        source_refs = [
            {
                "source": "HMDA public Data Browser CSV",
                "record_id": row_key,
                "url": resolved_urls[year],
                "snapshot_digest": source_file_by_year[year]["sha256"],
            },
            {
                "source": "HMDA public LAR schema",
                "record_id": f"public-lar-schema-{year}",
                "url": PUBLIC_SCHEMA_URL,
                "snapshot_digest": schema_digest,
            },
            {
                "source": "HMDA public field definitions",
                "record_id": f"public-fields-{year}",
                "url": PUBLIC_FIELDS_URL,
                "snapshot_digest": definition_digest,
            },
        ]
        records["rows"][row_key]["sources"] = source_refs
        case_id = f"hmda-{year}-{raw['lei']}-{raw_digest[:16]}"
        cases.append(
            {
                "case_id": case_id,
                "group_id": raw["lei"],
                "domain": "hmda",
                "source_snapshot": f"sha256:{snapshot_digest}",
                "inputs": {
                    "activity_year": year,
                    "lei": raw["lei"],
                    "row_digest": raw_digest,
                    "requested_fields": ["reverse_mortgage", "open-end_line_of_credit"],
                },
                "metadata": {
                    "lineage_ids": [raw["lei"], raw_digest],
                    "action_cohort": raw["action_taken"],
                    "real_public_record": True,
                    "protected_demographic_fields_exposed": False,
                },
            }
        )
        # Gold is constructed only after the complete snapshot and case contract
        # have been assembled below.  Appending the case here keeps selection and
        # source attribution deterministic without calling the macro candidate.

    # Adding source references changes the model-visible records and therefore the
    # final snapshot identity. Rebind every case after records are final.
    snapshot_digest = hashlib.sha256(canonical(records).encode("utf-8")).hexdigest()
    for case in cases:
        case["source_snapshot"] = f"sha256:{snapshot_digest}"
    for raw in cases:
        case = BenchmarkCase(
            case_id=raw["case_id"],
            group_id=raw["group_id"],
            domain=raw["domain"],
            source_snapshot=raw["source_snapshot"],
            inputs=raw["inputs"],
            metadata=raw["metadata"],
        )
        gold.append(
            {
                "case_id": case.case_id,
                "output": hmda_gold_from_records(case, records),
            }
        )
    snapshot_payload = {
        "schema": SCHEMA,
        "snapshot_digest": f"sha256:{snapshot_digest}",
        "records": records,
    }
    (output / "snapshot.json").write_text(
        json.dumps(snapshot_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "cases.jsonl").write_text(
        "".join(json.dumps(case, sort_keys=True) + "\n" for case in cases), encoding="utf-8"
    )
    (output / "gold.jsonl").write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in gold), encoding="utf-8"
    )
    report.update(
        {
            "snapshot_digest": snapshot_digest,
            "case_file_sha256": hashlib.sha256((output / "cases.jsonl").read_bytes()).hexdigest(),
            "gold_file_sha256": hashlib.sha256((output / "gold.jsonl").read_bytes()).hexdigest(),
            "snapshot_file_sha256": hashlib.sha256((output / "snapshot.json").read_bytes()).hexdigest(),
            "variable_path_groups": sum(
                1
                for item in gold
                if item["output"]["denial_reasons"] or item["output"]["special_states"]
            ),
            "gold_construction": {
                "implementation": "benchmarks/gold.py:hmda_gold_from_records",
                "implementation_sha256": _sha256_file(
                    Path(__file__).resolve().parents[1] / "gold.py"
                ),
                "independent_from_macro": True,
                "cases": len(gold),
            },
            "agent_visible_schema_fields": list(SAFE_ROW_FIELDS),
        }
    )
    report["variable_path_fraction"] = report["variable_path_groups"] / len(gold)
    (output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def reseal_normalized_pool(output_dir: str | Path) -> dict[str, Any]:
    """Apply current privacy and gold contracts to an existing normalized pool.

    This provider-free migration is intentionally narrower than source
    acquisition: it cannot establish empty-cache reproducibility. It exists so
    retained normalized evidence can be deterministically hardened after a
    model-visible schema-boundary correction without reconstructing omitted raw
    public CSV archives.
    """

    output = Path(output_dir)
    snapshot_path = output / "snapshot.json"
    cases_path = output / "cases.jsonl"
    gold_path = output / "gold.jsonl"
    report_path = output / "report.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if snapshot.get("schema") != SCHEMA or not isinstance(snapshot.get("records"), dict):
        raise ValueError("unsupported normalized HMDA snapshot")
    records = snapshot["records"]
    schemas = records.get("schemas")
    rows = records.get("rows")
    if not isinstance(schemas, dict) or not isinstance(rows, dict):
        raise ValueError("normalized HMDA snapshot lacks schemas or rows")
    for year, schema in schemas.items():
        if not isinstance(schema, dict) or str(schema.get("year")) != str(year):
            raise ValueError("normalized HMDA schema identity is inconsistent")
        schema["fields"] = list(SAFE_ROW_FIELDS)
    schema_digest = hashlib.sha256(canonical(schemas).encode("utf-8")).hexdigest()
    for row in rows.values():
        if not isinstance(row, dict):
            raise ValueError("normalized HMDA row must be an object")
        unexpected = set(row) - {*SAFE_ROW_FIELDS, "raw_row_digest", "sources"}
        if unexpected:
            raise ValueError(
                "normalized HMDA row exposes non-allowlisted fields: "
                + ", ".join(sorted(unexpected))
            )
        for source in row.get("sources", ()):
            if source.get("source") == "HMDA public LAR schema":
                source["snapshot_digest"] = schema_digest

    cases_raw = [
        json.loads(line)
        for line in cases_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    snapshot_digest = hashlib.sha256(canonical(records).encode("utf-8")).hexdigest()
    for raw in cases_raw:
        raw["source_snapshot"] = f"sha256:{snapshot_digest}"
    gold = []
    for raw in cases_raw:
        case = BenchmarkCase(
            case_id=raw["case_id"],
            group_id=raw["group_id"],
            domain=raw["domain"],
            source_snapshot=raw["source_snapshot"],
            inputs=raw["inputs"],
            metadata=raw.get("metadata", {}),
        )
        gold.append(
            {"case_id": case.case_id, "output": hmda_gold_from_records(case, records)}
        )
    snapshot["snapshot_digest"] = f"sha256:{snapshot_digest}"
    snapshot_path.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    cases_path.write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in cases_raw),
        encoding="utf-8",
    )
    gold_path.write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in gold),
        encoding="utf-8",
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report.update(
        {
            "snapshot_digest": snapshot_digest,
            "case_file_sha256": _sha256_file(cases_path),
            "gold_file_sha256": _sha256_file(gold_path),
            "snapshot_file_sha256": _sha256_file(snapshot_path),
            "agent_visible_schema_fields": list(SAFE_ROW_FIELDS),
            "gold_construction": {
                "implementation": "benchmarks/gold.py:hmda_gold_from_records",
                "implementation_sha256": _sha256_file(
                    Path(__file__).resolve().parents[1] / "gold.py"
                ),
                "independent_from_macro": True,
                "cases": len(gold),
            },
        }
    )
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", action="append", required=True, metavar="YEAR=PATH")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--minimum-groups", type=int, default=420)
    parser.add_argument(
        "--source-url",
        action="append",
        default=[],
        metavar="YEAR=HTTPS_URL",
        help="exact public CSV URL used for each input; defaults to the RI study URL",
    )
    args = parser.parse_args(argv)
    inputs: list[tuple[int, Path]] = []
    for value in args.csv:
        if "=" not in value:
            parser.error("--csv requires YEAR=PATH")
        year, path = value.split("=", 1)
        inputs.append((int(year), Path(path)))
    source_urls: dict[int, str] = {}
    for value in args.source_url:
        if "=" not in value:
            parser.error("--source-url requires YEAR=HTTPS_URL")
        year, url = value.split("=", 1)
        source_urls[int(year)] = url
    report = build_pool(
        inputs,
        args.out,
        minimum_groups=args.minimum_groups,
        source_urls=source_urls,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
