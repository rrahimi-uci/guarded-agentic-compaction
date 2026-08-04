"""Demo C — multi-agent incident triage (execution-plan §12.3)."""

from .world import (
    ALL_TOOLS,
    EFFECTS_PATH,
    ENTRY_ALLOWLIST,
    FAMILY_SPECIALIST,
    MANIFEST,
    PROMPT_BLOCKS,
    SPECIALISTS,
    TriagePolicy,
    TriageWorld,
    build_workload,
)

__all__ = [
    "ALL_TOOLS",
    "EFFECTS_PATH",
    "ENTRY_ALLOWLIST",
    "FAMILY_SPECIALIST",
    "MANIFEST",
    "PROMPT_BLOCKS",
    "SPECIALISTS",
    "TriagePolicy",
    "TriageWorld",
    "build_workload",
]
