"""Deterministic counterbalanced schedules for frozen benchmark roles."""

from __future__ import annotations

import hashlib
import itertools
from dataclasses import asdict, dataclass
from typing import Mapping, Sequence

from ..evaluation.domains import BenchmarkCase, BenchmarkRole
from .protocol import FrozenProtocol, ProtocolError, case_pool_digest

__all__ = ["ScheduledExecution", "build_role_schedule", "schedule_summary"]


@dataclass(frozen=True, slots=True)
class ScheduledExecution:
    sequence: int
    stage: int
    domain: str
    case_id: str
    group_id: str
    role: str
    action: str
    repeat: int

    @property
    def event_id(self) -> str:
        return f"{self.domain}:{self.case_id}:{self.action}:r{self.repeat}"

    def as_dict(self) -> dict[str, int | str]:
        return asdict(self)


def _rank(seed: int, *parts: object) -> str:
    return hashlib.sha256(":".join(map(str, (seed, *parts))).encode()).hexdigest()


def build_role_schedule(
    protocol: FrozenProtocol,
    cases_by_domain: Mapping[str, Sequence[BenchmarkCase]],
    *,
    role: BenchmarkRole | str,
    actions: Sequence[str] = ("baseline", "grc", "macro"),
    repeats: int = 1,
    limit_per_domain: int | None = None,
) -> tuple[ScheduledExecution, ...]:
    """Assign every group a deterministic action order and stage execution."""

    selected_role = role if isinstance(role, BenchmarkRole) else BenchmarkRole(role)
    action_names = tuple(actions)
    if not action_names or len(set(action_names)) != len(action_names):
        raise ProtocolError("actions must be a non-empty unique sequence")
    if type(repeats) is not int or repeats < 1:
        raise ProtocolError("repeats must be a positive integer")
    if limit_per_domain is not None and (
        type(limit_per_domain) is not int or limit_per_domain < 1
    ):
        raise ProtocolError("limit_per_domain must be positive")
    permutations = tuple(itertools.permutations(action_names))
    result: list[ScheduledExecution] = []
    sequence = 0
    for domain in sorted(protocol.group_roles):
        if domain not in cases_by_domain:
            raise ProtocolError(f"missing cases for frozen domain {domain!r}")
        expected_pool_digest = protocol.case_pool_digests.get(domain)
        if expected_pool_digest and case_pool_digest(cases_by_domain[domain]) != expected_pool_digest:
            raise ProtocolError(f"normalized case pool drifted after freeze for {domain!r}")
        allowed_ids = set(protocol.case_ids[domain])
        by_group: dict[str, BenchmarkCase] = {}
        for case in cases_by_domain[domain]:
            if case.case_id not in allowed_ids:
                continue
            if case.group_id in by_group:
                raise ProtocolError(
                    f"role scheduler requires one case per group; duplicate {case.group_id!r}"
                )
            by_group[case.group_id] = case
        groups = [
            group
            for group, assigned in protocol.group_roles[domain].items()
            if assigned is selected_role
        ]
        groups.sort(
            key=lambda group: (
                _rank(protocol.seed, domain, selected_role.value, group),
                group,
            )
        )
        if limit_per_domain is not None:
            groups = groups[:limit_per_domain]
        if any(group not in by_group for group in groups):
            missing = sorted(group for group in groups if group not in by_group)
            raise ProtocolError(f"frozen cases missing for groups {missing[:3]}")
        for repeat in range(repeats):
            ranked = sorted(
                groups,
                key=lambda value: _rank(protocol.seed, repeat, domain, value),
            )
            assignments = {
                group: permutations[index % len(permutations)]
                for index, group in enumerate(ranked)
            }
            for stage in range(len(action_names)):
                for action in action_names:
                    batch = [group for group in groups if assignments[group][stage] == action]
                    for group in batch:
                        sequence += 1
                        case = by_group[group]
                        result.append(
                            ScheduledExecution(
                                sequence=sequence,
                                stage=stage,
                                domain=domain,
                                case_id=case.case_id,
                                group_id=group,
                                role=selected_role.value,
                                action=action,
                                repeat=repeat,
                            )
                        )
    event_ids = [item.event_id for item in result]
    if len(event_ids) != len(set(event_ids)):
        raise ProtocolError("schedule generated duplicate execution identities")
    return tuple(result)


def schedule_summary(
    schedule: Sequence[ScheduledExecution],
    *,
    max_model_requests_per_execution: int,
    retries: int,
) -> dict[str, object]:
    if max_model_requests_per_execution < 1 or retries < 0:
        raise ValueError("request limit must be positive and retries non-negative")
    by_domain_action: dict[str, int] = {}
    for item in schedule:
        key = f"{item.domain}:{item.action}"
        by_domain_action[key] = by_domain_action.get(key, 0) + 1
    return {
        "schema": "agent-compaction-execution-schedule/v1",
        "scheduled_executions": len(schedule),
        "scheduled_by_domain_action": dict(sorted(by_domain_action.items())),
        "max_model_requests_per_execution": max_model_requests_per_execution,
        "retries": retries,
        "maximum_provider_requests": len(schedule)
        * max_model_requests_per_execution
        * (retries + 1),
    }
