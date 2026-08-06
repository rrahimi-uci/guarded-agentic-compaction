"""Prospective benchmark protocol, freezing, execution, and analysis helpers."""

from .preflight import (
    PreflightError,
    PreflightReport,
    load_study_manifest,
    preflight_study,
    validate_study_manifest,
)
from .protocol import (
    FrozenProtocol,
    ProtocolError,
    case_pool_digest,
    freeze_protocol,
    load_case_jsonl,
)
from .budget import BudgetExceeded, ProviderBudget, ProviderCharge
from .actions import (
    ActionSpec,
    MacroApproval,
    MacroApprovalError,
    frozen_artifact_digest,
)
from .schedule import ScheduledExecution, build_role_schedule, schedule_summary
from .external import (
    EvidenceSubstrate,
    ReferenceAction,
    ReferenceAnalysis,
    ReferenceTask,
    analyze_reference_tasks,
    reference_task_to_episode,
)

__all__ = [
    "FrozenProtocol",
    "BudgetExceeded",
    "ActionSpec",
    "MacroApproval",
    "MacroApprovalError",
    "PreflightError",
    "PreflightReport",
    "ProtocolError",
    "ProviderBudget",
    "ProviderCharge",
    "case_pool_digest",
    "freeze_protocol",
    "frozen_artifact_digest",
    "load_case_jsonl",
    "load_study_manifest",
    "preflight_study",
    "validate_study_manifest",
    "ScheduledExecution",
    "build_role_schedule",
    "schedule_summary",
    "EvidenceSubstrate",
    "ReferenceAction",
    "ReferenceAnalysis",
    "ReferenceTask",
    "analyze_reference_tasks",
    "reference_task_to_episode",
]
