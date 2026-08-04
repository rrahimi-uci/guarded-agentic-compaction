"""Privacy-bounded HMDA public-record tools and deterministic macro candidate."""

from __future__ import annotations

from typing import Any

from agent_compaction.evaluation import BenchmarkCase

from .store import FrozenRecordStore


PRIVACY_NOTICE = (
    "Public HMDA data are modified to protect applicant and borrower privacy; "
    "this interpretation does not reconstruct underwriting facts."
)


class HmdaSnapshot:
    def __init__(self, store: FrozenRecordStore) -> None:
        self.store = store

    def get_public_lar_record(
        self, *, snapshot_digest: str, year: int, lei: str, row_digest: str
    ) -> Any:
        return self.store.get(
            "rows", f"{year}:{lei}:{row_digest}", snapshot_digest=snapshot_digest
        )

    def get_hmda_public_schema(self, *, snapshot_digest: str, year: int) -> Any:
        return self.store.get("schemas", str(year), snapshot_digest=snapshot_digest)

    def get_hmda_field_definition(
        self, *, snapshot_digest: str, year: int, field: str
    ) -> Any:
        return self.store.get(
            "definitions", f"{year}:{field}", snapshot_digest=snapshot_digest
        )

    def get_hmda_filer(self, *, snapshot_digest: str, year: int, lei: str) -> Any:
        return self.store.get("filers", f"{year}:{lei}", snapshot_digest=snapshot_digest)

    def get_hmda_code_label(
        self, *, snapshot_digest: str, year: int, field: str, value: str
    ) -> Any:
        return self.store.get(
            "labels", f"{year}:{field}:{value}", snapshot_digest=snapshot_digest
        )


def _coded(
    tools: HmdaSnapshot,
    *,
    snapshot: str,
    year: int,
    field: str,
    value: Any,
) -> dict[str, Any]:
    label = tools.get_hmda_code_label(
        snapshot_digest=snapshot, year=year, field=field, value=str(value)
    )
    return {"code": value, "label": None if label is None else str(label)}


def hmda_macro(case: BenchmarkCase, tools: HmdaSnapshot) -> dict[str, Any]:
    inputs = case.inputs
    snapshot = case.source_snapshot
    year = int(inputs["activity_year"])
    lei = str(inputs["lei"])
    row_digest = str(inputs["row_digest"])
    row = tools.get_public_lar_record(
        snapshot_digest=snapshot, year=year, lei=lei, row_digest=row_digest
    )
    schema = tools.get_hmda_public_schema(snapshot_digest=snapshot, year=year)
    filer = tools.get_hmda_filer(snapshot_digest=snapshot, year=year, lei=lei)
    if row is None or schema is None or filer is None:
        raise LookupError("HMDA row, schema, and filer metadata must all be present")
    field_map = {
        "action_taken": "action_taken",
        "loan_type": "loan_type",
        "loan_purpose": "loan_purpose",
        "lien_status": "lien_status",
        "occupancy_type": "occupancy_type",
        "property_type": "derived_dwelling_category",
        "preapproval": "preapproval",
    }
    required_fields = {
        *field_map.values(),
        *(str(field) for field in inputs.get("requested_fields", ())),
        *(f"denial_reason-{index}" for index in range(1, 5)),
    }
    schema_fields = set(map(str, schema.get("fields", ())))
    missing_schema = sorted(required_fields - schema_fields)
    if missing_schema:
        raise LookupError(
            "HMDA frozen schema is missing required fields: "
            + ", ".join(missing_schema)
        )
    missing_definitions = sorted(
        field
        for field in required_fields
        if tools.get_hmda_field_definition(
            snapshot_digest=snapshot, year=year, field=field
        )
        is None
    )
    if missing_definitions:
        raise LookupError(
            "HMDA frozen definitions are missing required fields: "
            + ", ".join(missing_definitions)
        )
    if (
        str(row.get("activity_year")) != str(year)
        or str(row.get("lei")) != lei
        or str(row.get("raw_row_digest")) != row_digest
        or str(filer.get("lei")) != lei
    ):
        raise LookupError("HMDA normalized record identity is inconsistent")
    output: dict[str, Any] = {
        "activity_year": year,
        "filer": {"code": lei, "label": filer.get("name")},
    }
    for output_name, source_name in field_map.items():
        output[output_name] = _coded(
            tools,
            snapshot=snapshot,
            year=year,
            field=source_name,
            value=row.get(source_name, "NA"),
        )
    denial_reasons: list[dict[str, Any]] = []
    for index in range(1, 5):
        field = f"denial_reason-{index}"
        value = row.get(field)
        if value not in (None, "", "NA", "1111", "10"):
            denial_reasons.append(
                _coded(
                    tools,
                    snapshot=snapshot,
                    year=year,
                    field=field,
                    value=value,
                )
            )
    special: dict[str, str] = {}
    for field in inputs.get("requested_fields", []):
        value = str(row.get(field, "UNAVAILABLE"))
        normalized = {
            "NA": "NA",
            "1111": "NA",
            "Exempt": "EXEMPT",
            "": "UNAVAILABLE",
            "UNAVAILABLE": "UNAVAILABLE",
        }.get(value)
        if normalized:
            special[str(field)] = normalized
    for index in range(1, 5):
        field = f"denial_reason-{index}"
        if str(row.get(field, "")) == "10":
            special[field] = "NOT_APPLICABLE"
    output.update(
        {
            "denial_reasons": denial_reasons,
            "special_states": special,
            "privacy_notice": PRIVACY_NOTICE,
            "sources": list(row.get("sources", [])),
        }
    )
    return output
