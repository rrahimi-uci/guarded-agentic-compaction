"""Exact programmatic oracles for retained public-record benchmarks."""

from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from agent_compaction.evaluation import BenchmarkCase, OracleResult


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


class ExactObjectOracle:
    """Validate an output schema, then compare every required field exactly.

    Gold objects are held by the evaluator only.  Agent tools receive a separate
    snapshot facade and cannot call this object.
    """

    def __init__(
        self,
        schema_path: str | Path,
        gold_by_case: Mapping[str, Mapping[str, Any]],
    ) -> None:
        schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        self._validator = Draft202012Validator(schema)
        required = schema.get("required", [])
        if not required:
            raise ValueError("exact oracle schema must declare required fields")
        self._required = tuple(str(item) for item in required)
        normalized: dict[str, str] = {}
        for case_id, gold in gold_by_case.items():
            missing = sorted(set(self._required) - set(gold))
            if missing:
                raise ValueError(f"gold {case_id!r} is missing fields: {', '.join(missing)}")
            gold_json = _canonical(dict(gold))
            gold_object = json.loads(gold_json)
            errors = sorted(
                self._validator.iter_errors(gold_object),
                key=lambda item: tuple(str(part) for part in item.path),
            )
            if errors:
                raise ValueError(f"gold {case_id!r} violates schema: {errors[0].message}")
            normalized[str(case_id)] = gold_json
        self._gold_json = MappingProxyType(normalized)

    def evaluate(self, case: BenchmarkCase, output: object) -> OracleResult:
        gold_json = self._gold_json.get(case.case_id)
        if gold_json is None:
            raise KeyError(f"no gold contract is registered for case {case.case_id!r}")
        gold = json.loads(gold_json)
        if not isinstance(output, Mapping):
            return OracleResult(
                case_id=case.case_id,
                passed=False,
                field_results={field: False for field in self._required},
                errors=("output must be an object",),
            )
        try:
            candidate = json.loads(_canonical(dict(output)))
        except (TypeError, ValueError) as exc:
            return OracleResult(
                case_id=case.case_id,
                passed=False,
                field_results={field: False for field in self._required},
                errors=(f"output is not finite JSON: {exc}",),
            )
        schema_errors = sorted(
            self._validator.iter_errors(candidate),
            key=lambda item: tuple(str(part) for part in item.path),
        )
        fields = {
            field: field in candidate and candidate[field] == gold[field]
            for field in self._required
        }
        errors = tuple(
            f"schema:{'/'.join(str(part) for part in error.path) or '$'}:{error.message}"
            for error in schema_errors
        )
        return OracleResult(
            case_id=case.case_id,
            passed=all(fields.values()) and not errors,
            field_results=fields,
            errors=errors,
            metadata={"oracle": "exact_required_fields_and_json_schema"},
        )
