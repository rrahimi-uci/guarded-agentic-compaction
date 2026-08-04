"""Versioned effect catalog (proposal §5.3, execution-plan WP2).

Anything not listed is ``UNKNOWN`` and is never compiled. This file is the whole
safety boundary of v0.x: it converts "infer the effects of a tool" (an open
research problem) into configuration that a human signs off on.

Two documented specification gaps are closed here (proposal §6.5):

* ``literal_only``: per-tool argument slots that may only be bound by identity
  or by a constant, never reconstructed by a transform.
* ``max_transform_depth``: per-tool override of the global DSL depth cap.
* ``quota_attested``: whether invoking this tool increments a counter inside the
  set ``stage.reversible()`` attests over (proposal §4.7). use-cases §1 makes this
  a per-deployment claim about the token mint; here it is configuration, so a
  deployment whose mint writes an audit row cannot silently claim a clean abort.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = [
    "EffectClass",
    "Capability",
    "EffectSpec",
    "EffectCatalog",
    "UNKNOWN_SPEC",
]


class EffectClass(str, Enum):
    """Effect classes. ``UNKNOWN`` is the default and is never compilable."""

    PURE = "PURE"
    READ_LOCAL = "READ_LOCAL"
    READ_EXTERNAL = "READ_EXTERNAL"
    WRITE_REVERSIBLE = "WRITE_REVERSIBLE"
    WRITE_IRREVERSIBLE = "WRITE_IRREVERSIBLE"
    UNKNOWN = "UNKNOWN"

    @property
    def is_read_like(self) -> bool:
        return self in (EffectClass.PURE, EffectClass.READ_LOCAL, EffectClass.READ_EXTERNAL)


class Capability(str, Enum):
    """Capabilities license *specific* optimizations (proposal §5.3).

    Read-only and idempotent are deliberately not capabilities: a nominal read
    can still burn quota, create audit state, or observe time-varying data.
    """

    SPECULATABLE = "speculatable"
    REPLAYABLE = "replayable"
    CACHEABLE = "cacheable"
    REORDERABLE = "reorderable"
    BATCHABLE = "batchable"


class EffectSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool: str = ""
    effect: EffectClass = EffectClass.UNKNOWN
    capabilities: tuple[Capability, ...] = ()
    key: tuple[str, ...] = ()
    freshness_s: float | None = None
    literal_only: tuple[str, ...] = ()
    max_transform_depth: int | None = None
    resource: str | None = None
    approval_required: bool = False
    quota_attested: bool = False
    notes: str = ""

    @field_validator("capabilities", mode="before")
    @classmethod
    def _caps(cls, v: Any) -> Any:
        if v is None:
            return ()
        return tuple(v)

    @property
    def compilable(self) -> bool:
        """Eligible for inclusion in a compiled region (proposal Eq. 5 + §7.3).

        Requires a read-like effect *and* both pre-commit capabilities. An
        approval-gated tool is never compilable regardless of class.
        """

        if self.approval_required:
            return False
        if not self.effect.is_read_like:
            return False
        return (
            Capability.SPECULATABLE in self.capabilities
            and Capability.REPLAYABLE in self.capabilities
        )

    @property
    def is_barrier(self) -> bool:
        """Barriers terminate a candidate region (execution-plan §8.2)."""

        return not self.compilable

    def block_reason(self) -> str | None:
        if self.effect is EffectClass.UNKNOWN:
            return "UNKNOWN_EFFECT"
        if self.approval_required:
            return "APPROVAL_BARRIER"
        if not self.effect.is_read_like:
            return f"EFFECT_{self.effect.value}"
        missing = [
            c.value
            for c in (Capability.SPECULATABLE, Capability.REPLAYABLE)
            if c not in self.capabilities
        ]
        if missing:
            return "MISSING_CAPABILITY_" + "+".join(missing)
        return None


UNKNOWN_SPEC = EffectSpec(tool="<unknown>", effect=EffectClass.UNKNOWN)


class EffectCatalog(BaseModel):
    """A versioned catalog. Unlisted tools resolve to :data:`UNKNOWN_SPEC`."""

    model_config = ConfigDict(extra="forbid")

    version: int = 1
    name: str = "effects"
    tools: dict[str, EffectSpec] = Field(default_factory=dict)

    @field_validator("tools", mode="after")
    @classmethod
    def _stamp_names(cls, v: dict[str, EffectSpec]) -> dict[str, EffectSpec]:
        return {k: spec.model_copy(update={"tool": k}) for k, spec in v.items()}

    # -- construction -----------------------------------------------------
    @classmethod
    def from_yaml(cls, path: str | Path) -> "EffectCatalog":
        data = yaml.safe_load(Path(path).read_text()) or {}
        data.setdefault("name", Path(path).stem)
        return cls.model_validate(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EffectCatalog":
        return cls.model_validate(data)

    # -- lookups ----------------------------------------------------------
    def get(self, tool: str | None) -> EffectSpec:
        if tool is None:
            return UNKNOWN_SPEC
        return self.tools.get(tool, UNKNOWN_SPEC.model_copy(update={"tool": tool}))

    def effect_of(self, tool: str | None) -> EffectClass:
        return self.get(tool).effect

    def compilable(self, tool: str | None) -> bool:
        return self.get(tool).compilable

    def literal_only_paths(self, tool: str | None) -> tuple[str, ...]:
        return self.get(tool).literal_only

    def allowed_effects(self) -> set[EffectClass]:
        return {spec.effect for spec in self.tools.values() if spec.compilable}

    def undeclared(self, tools: Iterable[str]) -> list[str]:
        return sorted({t for t in tools if t and t not in self.tools})

    def conflicts_on_resource(self, tool_a: str | None, tool_b: str | None) -> bool:
        """Order-edge predicate: two events conflict when they share a resource
        and at least one of them writes it (Algorithm 1 line 18)."""

        a, b = self.get(tool_a), self.get(tool_b)
        res_a = a.resource or (tool_a.split(".")[0] if tool_a else None)
        res_b = b.resource or (tool_b.split(".")[0] if tool_b else None)
        if res_a is None or res_a != res_b:
            return False
        writes = {EffectClass.WRITE_REVERSIBLE, EffectClass.WRITE_IRREVERSIBLE, EffectClass.UNKNOWN}
        return a.effect in writes or b.effect in writes

    # -- identity ---------------------------------------------------------
    def digest(self) -> str:
        # Catalog identity is semantic, not YAML/dict insertion order.
        blob = json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    @property
    def catalog_version(self) -> str:
        return f"{self.name}@{self.version}#{self.digest()}"

    def matches_version(self, reference: str, *, allow_legacy: bool = False) -> bool:
        """Whether a manifest reference names this catalog.

        Manifests pin :attr:`catalog_version`, including its digest. The digest-free
        ``name@version`` form can be admitted only through an explicit migration
        flag; ``unknown`` is never sufficient evidence for compilation.
        """

        return reference == self.catalog_version or (
            allow_legacy and reference == f"{self.name}@{self.version}"
        )

    def validate_coverage(self, tools: Iterable[str]) -> dict[str, Any]:
        """CI validator (WP2): report tools that would block compilation."""

        tools = sorted({t for t in tools if t})
        undeclared = [t for t in tools if t not in self.tools]
        blocked = {t: self.get(t).block_reason() for t in tools if not self.compilable(t)}
        return {
            "n_tools": len(tools),
            "undeclared": undeclared,
            "coverage": 0.0 if not tools else 1.0 - len(undeclared) / len(tools),
            "blocked": blocked,
            "compilable": [t for t in tools if self.compilable(t)],
        }
