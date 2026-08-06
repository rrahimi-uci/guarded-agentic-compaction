"""Deterministic role freezing and lineage isolation for prospective studies."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from ..evaluation.domains import BenchmarkCase, BenchmarkRole, FrozenStudy

__all__ = [
    "FrozenProtocol",
    "ProtocolError",
    "case_pool_digest",
    "freeze_protocol",
    "load_case_jsonl",
]


class ProtocolError(ValueError):
    """Case identity, role allocation, or lineage violates the frozen protocol."""


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ProtocolError("protocol data must be finite JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def case_pool_digest(cases: Sequence[BenchmarkCase]) -> str:
    """Bind every model-visible input and grouping field in a normalized pool."""

    return _digest(
        sorted(
            (case.as_dict() for case in cases),
            key=lambda item: (item["case_id"], item["group_id"]),
        )
    )


def load_case_jsonl(path: str | Path) -> tuple[BenchmarkCase, ...]:
    """Load normalized cases without accepting evaluator-only gold fields."""

    source = Path(path)
    cases: list[BenchmarkCase] = []
    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            forbidden = {"gold", "expected", "oracle"} & set(raw)
            if forbidden:
                raise ProtocolError(
                    f"case input at line {line_number} exposes evaluator fields: "
                    f"{', '.join(sorted(forbidden))}"
                )
            cases.append(
                BenchmarkCase(
                    case_id=raw["case_id"],
                    group_id=raw["group_id"],
                    domain=raw["domain"],
                    source_snapshot=raw["source_snapshot"],
                    inputs=raw["inputs"],
                    metadata=raw.get("metadata", {}),
                )
            )
        except ProtocolError:
            raise
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ProtocolError(f"invalid case at {source}:{line_number}") from exc
    return tuple(cases)


def _lineages(case: BenchmarkCase) -> tuple[str, ...]:
    value = case.metadata.get("lineage_ids", ())
    if isinstance(value, str):
        items = (value,)
    elif isinstance(value, (list, tuple)):
        items = tuple(value)
    else:
        raise ProtocolError(f"case {case.case_id!r} lineage_ids must be a list of strings")
    if any(not isinstance(item, str) or not item.strip() for item in items):
        raise ProtocolError(f"case {case.case_id!r} has an invalid lineage identifier")
    return tuple(sorted(set(items)))


@dataclass(frozen=True, slots=True)
class FrozenProtocol:
    """Frozen selection and role allocation for every registered domain."""

    study_id: str
    seed: int
    config_digest: str
    source_digests: Mapping[str, str]
    group_roles: Mapping[str, Mapping[str, BenchmarkRole]]
    case_ids: Mapping[str, tuple[str, ...]]
    lineage_digest: str
    case_pool_digests: Mapping[str, str] = field(default_factory=dict)
    model: str = ""
    execution_contract: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_digests", MappingProxyType(dict(self.source_digests)))
        object.__setattr__(
            self,
            "group_roles",
            MappingProxyType(
                {
                    domain: MappingProxyType(dict(roles))
                    for domain, roles in self.group_roles.items()
                }
            ),
        )
        object.__setattr__(
            self,
            "case_ids",
            MappingProxyType({domain: tuple(ids) for domain, ids in self.case_ids.items()}),
        )
        object.__setattr__(
            self,
            "case_pool_digests",
            MappingProxyType(dict(self.case_pool_digests)),
        )
        object.__setattr__(
            self,
            "execution_contract",
            MappingProxyType(dict(self.execution_contract)),
        )

    @property
    def digest(self) -> str:
        payload = self.as_dict(include_digest=False)
        return _digest(payload)

    def family_key(self, domain: str) -> str:
        if domain not in self.group_roles:
            raise KeyError(f"unknown frozen domain {domain!r}")
        return f"{self.study_id}:{domain}:{self.digest[:24]}"

    def study_for(self, domain: str) -> FrozenStudy:
        if domain not in self.group_roles:
            raise KeyError(f"unknown frozen domain {domain!r}")
        return FrozenStudy(
            study_id=f"{self.study_id}:{domain}",
            config_digest=self.config_digest,
            source_digests={domain: self.source_digests[domain]},
            group_roles=self.group_roles[domain],
            model=self.model,
            metadata={
                "protocol_digest": self.digest,
                "lineage_digest": self.lineage_digest,
            },
        )

    def as_dict(self, *, include_digest: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema": "agent-compaction-frozen-protocol/v1",
            "study_id": self.study_id,
            "seed": self.seed,
            "config_digest": self.config_digest,
            "source_digests": dict(sorted(self.source_digests.items())),
            "group_roles": {
                domain: {
                    group: role.value
                    for group, role in sorted(roles.items())
                }
                for domain, roles in sorted(self.group_roles.items())
            },
            "case_ids": {
                domain: list(ids) for domain, ids in sorted(self.case_ids.items())
            },
            "case_pool_digests": dict(sorted(self.case_pool_digests.items())),
            "lineage_digest": self.lineage_digest,
            "model": self.model,
            "execution_contract": dict(sorted(self.execution_contract.items())),
        }
        if include_digest:
            result["protocol_digest"] = self.digest
        return result

    def write(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.as_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return destination

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrozenProtocol":
        if payload.get("schema") != "agent-compaction-frozen-protocol/v1":
            raise ProtocolError("unsupported frozen protocol schema")
        roles = {
            str(domain): {
                str(group): BenchmarkRole(role)
                for group, role in dict(domain_roles).items()
            }
            for domain, domain_roles in dict(payload["group_roles"]).items()
        }
        result = cls(
            study_id=str(payload["study_id"]),
            seed=int(payload["seed"]),
            config_digest=str(payload["config_digest"]),
            source_digests=dict(payload["source_digests"]),
            group_roles=roles,
            case_ids={
                str(domain): tuple(ids)
                for domain, ids in dict(payload["case_ids"]).items()
            },
            case_pool_digests={
                str(domain): str(digest)
                for domain, digest in dict(payload.get("case_pool_digests", {})).items()
            },
            lineage_digest=str(payload["lineage_digest"]),
            model=str(payload.get("model", "")),
            execution_contract={
                str(key): str(value)
                for key, value in dict(payload.get("execution_contract", {})).items()
            },
        )
        if payload.get("protocol_digest") != result.digest:
            raise ProtocolError("frozen protocol digest mismatch")
        return result

    @classmethod
    def load(cls, path: str | Path) -> "FrozenProtocol":
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProtocolError("cannot load frozen protocol") from exc
        return cls.from_dict(payload)


def freeze_protocol(
    *,
    study_id: str,
    seed: int,
    config_digest: str,
    source_digests: Mapping[str, str],
    cases_by_domain: Mapping[str, Sequence[BenchmarkCase]],
    role_counts: Mapping[BenchmarkRole | str, int],
    reserve_groups: int,
    model: str = "",
    execution_contract: Mapping[str, str] | None = None,
) -> FrozenProtocol:
    """Select groups deterministically and prove group/lineage role isolation."""

    if not study_id.strip() or not config_digest.strip():
        raise ProtocolError("study_id and config_digest must not be empty")
    if type(seed) is not int:
        raise ProtocolError("seed must be an integer")
    if type(reserve_groups) is not int or reserve_groups < 0:
        raise ProtocolError("reserve_groups must be a non-negative integer")
    normalized_counts: dict[BenchmarkRole, int] = {}
    for role, count in role_counts.items():
        normalized = role if isinstance(role, BenchmarkRole) else BenchmarkRole(role)
        if normalized is BenchmarkRole.RESERVE:
            raise ProtocolError("reserve count is supplied separately")
        if type(count) is not int or count < 1:
            raise ProtocolError("role counts must be positive integers")
        normalized_counts[normalized] = count
    if not normalized_counts:
        raise ProtocolError("at least one role count is required")

    required = sum(normalized_counts.values()) + reserve_groups
    frozen_roles: dict[str, dict[str, BenchmarkRole]] = {}
    selected_case_ids: dict[str, tuple[str, ...]] = {}
    case_pool_digests: dict[str, str] = {}
    all_lineage_records: list[tuple[str, str, str, str]] = []
    seen_case_ids: set[str] = set()

    for domain in sorted(cases_by_domain):
        if domain not in source_digests:
            raise ProtocolError(f"domain {domain!r} has no source digest")
        cases = tuple(cases_by_domain[domain])
        case_pool_digests[domain] = case_pool_digest(cases)
        by_group: dict[str, list[BenchmarkCase]] = {}
        for case in cases:
            if case.domain != domain:
                raise ProtocolError(
                    f"case {case.case_id!r} is in {domain!r} but declares {case.domain!r}"
                )
            if case.case_id in seen_case_ids:
                raise ProtocolError(f"duplicate case_id across domains: {case.case_id}")
            seen_case_ids.add(case.case_id)
            by_group.setdefault(case.group_id, []).append(case)
        if len(by_group) < required:
            raise ProtocolError(
                f"domain {domain!r} has {len(by_group)} groups; {required} are required"
            )
        ranked = sorted(
            by_group,
            key=lambda group: (
                hashlib.sha256(f"{seed}:{domain}:{group}".encode()).hexdigest(),
                group,
            ),
        )[:required]
        assignments: dict[str, BenchmarkRole] = {}
        cursor = 0
        # Role counts are a mapping, so caller insertion order must not change
        # which groups become test versus development evidence. Enum order is
        # the canonical allocation order serialized by the study manifest.
        for role in BenchmarkRole:
            if role is BenchmarkRole.RESERVE or role not in normalized_counts:
                continue
            count = normalized_counts[role]
            for group in ranked[cursor : cursor + count]:
                assignments[group] = role
            cursor += count
        for group in ranked[cursor:]:
            assignments[group] = BenchmarkRole.RESERVE

        lineage_role: dict[str, BenchmarkRole] = {}
        ids: list[str] = []
        for group in ranked:
            role = assignments[group]
            for case in sorted(by_group[group], key=lambda item: item.case_id):
                ids.append(case.case_id)
                for lineage in _lineages(case):
                    previous = lineage_role.setdefault(lineage, role)
                    if previous is not role:
                        raise ProtocolError(
                            f"lineage {lineage!r} crosses {previous.value} and {role.value}"
                        )
                    all_lineage_records.append((domain, lineage, role.value, group))
        frozen_roles[domain] = assignments
        selected_case_ids[domain] = tuple(ids)

    return FrozenProtocol(
        study_id=study_id,
        seed=seed,
        config_digest=config_digest,
        source_digests=source_digests,
        group_roles=frozen_roles,
        case_ids=selected_case_ids,
        lineage_digest=_digest(sorted(all_lineage_records)),
        case_pool_digests=case_pool_digests,
        model=model,
        execution_contract=dict(execution_contract or {}),
    )
