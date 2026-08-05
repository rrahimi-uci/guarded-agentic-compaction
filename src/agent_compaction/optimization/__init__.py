"""Optional third-party optimization adapters.

Adapters in this package do not change the framework-neutral trace IR or add
provider dependencies to the core installation.
"""

from .gepa import (
    GepaBackend,
    GepaEvaluation,
    GepaOptimizationError,
    GepaPromptConfig,
    GepaPromptOptimizer,
    GepaPromptResult,
    GepaUnavailableError,
    OfficialGepaBackend,
)

__all__ = [
    "GepaBackend",
    "GepaEvaluation",
    "GepaOptimizationError",
    "GepaPromptConfig",
    "GepaPromptOptimizer",
    "GepaPromptResult",
    "GepaUnavailableError",
    "OfficialGepaBackend",
]
