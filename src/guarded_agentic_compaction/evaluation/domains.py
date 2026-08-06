"""Framework-neutral contracts for real-record benchmark domains.

Domain adapters live outside the compiler core.  They provide immutable case inputs,
group identities, exact oracles, effect catalogs, and compatibility identities while
the optimization machinery continues to operate only on :class:`Episode` traces.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from ..schema.effects import EffectCatalog

__all__ = [
    "BenchmarkRole",
    "BenchmarkCase",
    "OracleResult",
    "FrozenStudy",
    "DomainAdapter",
]


def _freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _frozen_mapping(value: Mapping[str, Any], *, label: str) -> Mapping[str, Any]:
    try:
        encoded = json.dumps(
            dict(value), sort_keys=True, separators=(",", ":"), allow_nan=False
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be finite JSON data") from exc
    # The JSON round trip detaches caller-owned objects.  Recursive freezing keeps
    # nested values immutable as well as the top-level mapping.
    return _freeze_json(json.loads(encoded))


def _digest(value: Mapping[str, Any]) -> str:
    blob = json.dumps(
        _thaw_json(value), sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class BenchmarkRole(str, Enum):
    """Disjoint data roles used by the prospective multidomain protocol."""

    DISCOVERY = "discovery"
    DEVELOPMENT = "development"
    ARTIFACT_CALIBRATION = "artifact_calibration"
    PORTFOLIO_CALIBRATION = "portfolio_calibration"
    TEST = "test"
    RESERVE = "reserve"


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    """One immutable public-record case and its independent-group identity."""

    case_id: str
    group_id: str
    domain: str
    source_snapshot: str
    inputs: Mapping[str, Any]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for label, value in (
            ("case_id", self.case_id),
            ("group_id", self.group_id),
            ("domain", self.domain),
            ("source_snapshot", self.source_snapshot),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label} must be a non-empty string")
        object.__setattr__(self, "inputs", _frozen_mapping(self.inputs, label="case inputs"))
        object.__setattr__(self, "metadata", _frozen_mapping(self.metadata, label="case metadata"))

    @property
    def input_digest(self) -> str:
        return _digest(self.inputs)

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "group_id": self.group_id,
            "domain": self.domain,
            "source_snapshot": self.source_snapshot,
            "inputs": _thaw_json(self.inputs),
            "input_digest": self.input_digest,
            "metadata": _thaw_json(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class OracleResult:
    """Exact evaluator result; an LLM judge is never the primary oracle."""

    case_id: str
    passed: bool
    field_results: Mapping[str, bool]
    errors: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError("case_id must not be empty")
        fields = dict(self.field_results)
        if not fields:
            raise ValueError("field_results must not be empty")
        if any(type(value) is not bool for value in fields.values()):
            raise ValueError("field_results values must be booleans")
        if self.passed != (all(fields.values()) and not self.errors):
            raise ValueError("passed must equal all(field_results) with no errors")
        object.__setattr__(self, "field_results", MappingProxyType(fields))
        object.__setattr__(self, "errors", tuple(str(item) for item in self.errors))
        object.__setattr__(
            self, "metadata", _frozen_mapping(self.metadata, label="oracle metadata")
        )

    @property
    def failed_fields(self) -> tuple[str, ...]:
        return tuple(sorted(name for name, passed in self.field_results.items() if not passed))

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "passed": self.passed,
            "field_results": dict(self.field_results),
            "failed_fields": list(self.failed_fields),
            "errors": list(self.errors),
            "metadata": _thaw_json(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class FrozenStudy:
    """Compatibility identity and immutable group-role allocation for one study."""

    study_id: str
    config_digest: str
    source_digests: Mapping[str, str]
    group_roles: Mapping[str, BenchmarkRole | str]
    model: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.study_id, str)
            or not self.study_id.strip()
            or not isinstance(self.config_digest, str)
            or not self.config_digest.strip()
        ):
            raise ValueError("study_id and config_digest must not be empty")
        sources = {str(k): str(v) for k, v in self.source_digests.items()}
        if not sources or any(not key or not value for key, value in sources.items()):
            raise ValueError("source_digests must contain non-empty names and digests")
        roles: dict[str, BenchmarkRole] = {}
        for group_id, role in self.group_roles.items():
            if not str(group_id).strip():
                raise ValueError("group role keys must not be empty")
            roles[str(group_id)] = role if isinstance(role, BenchmarkRole) else BenchmarkRole(role)
        if not roles:
            raise ValueError("group_roles must not be empty")
        object.__setattr__(self, "source_digests", MappingProxyType(sources))
        object.__setattr__(self, "group_roles", MappingProxyType(roles))
        object.__setattr__(
            self, "metadata", _frozen_mapping(self.metadata, label="study metadata")
        )

    def role_for(self, group_id: str) -> BenchmarkRole:
        try:
            return self.group_roles[group_id]
        except KeyError as exc:
            raise KeyError(f"group {group_id!r} is not registered in study {self.study_id!r}") from exc

    @property
    def compatibility_key(self) -> str:
        payload = {
            "study_id": self.study_id,
            "config_digest": self.config_digest,
            "source_digests": dict(self.source_digests),
            "split_digest": self.split_digest,
            "model": self.model,
        }
        return f"study:{_digest(payload)[:24]}"

    @property
    def split_digest(self) -> str:
        return _digest(
            {key: value.value for key, value in sorted(self.group_roles.items())}
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "study_id": self.study_id,
            "config_digest": self.config_digest,
            "source_digests": dict(self.source_digests),
            "group_roles": {key: value.value for key, value in self.group_roles.items()},
            "model": self.model,
            "metadata": _thaw_json(self.metadata),
            "split_digest": self.split_digest,
            "compatibility_key": self.compatibility_key,
        }


@runtime_checkable
class DomainAdapter(Protocol):
    """Minimal extension point shared by Agents SDK and other framework adapters."""

    name: str

    def cases(self, role: BenchmarkRole) -> Sequence[BenchmarkCase]: ...

    def build_agent(self, action: str, frozen: FrozenStudy) -> Any: ...

    def oracle(self, case: BenchmarkCase, output: object) -> OracleResult: ...

    def effect_catalog(self) -> EffectCatalog: ...

    def compatibility_key(self, frozen: FrozenStudy) -> str: ...
