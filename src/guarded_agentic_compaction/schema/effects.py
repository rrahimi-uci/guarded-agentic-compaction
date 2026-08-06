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

import copy
import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

__all__ = [
    "EffectClass",
    "Capability",
    "CanonicalizationKind",
    "SemanticRelation",
    "CanonicalizationOp",
    "ArgumentSemantics",
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


class CanonicalizationKind(str, Enum):
    """Closed, reviewable argument-normalization operations.

    Canonicalization is executable business semantics, so catalogs may only use
    this bounded library.  Arbitrary callbacks would make a signed catalog
    non-portable and would move unreviewed code inside the compiler's trust
    boundary.
    """

    CLAMP_INT = "clamp_int"
    STRIP = "strip"
    CASEFOLD = "casefold"
    SORT_UNIQUE = "sort_unique"
    ALIASES = "aliases"


class SemanticRelation(str, Enum):
    """What an argument normalization promises to the task contract."""

    EQUIVALENT = "equivalent"
    MONOTONE_SUPERSET = "monotone_superset"


class CanonicalizationOp(BaseModel):
    """One deterministic operation in an argument equivalence contract."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: CanonicalizationKind
    admissible_minimum: int | None = None
    admissible_maximum: int | None = None
    minimum: int | None = None
    maximum: int | None = None
    aliases: dict[str, Any] = Field(default_factory=dict)

    @field_validator("maximum")
    @classmethod
    def _ordered_bounds(cls, value: int | None, info: Any) -> int | None:
        minimum = info.data.get("minimum")
        if value is not None and minimum is not None and value < minimum:
            raise ValueError("canonicalization maximum must be >= minimum")
        return value

    @model_validator(mode="after")
    def _validate_operation(self) -> "CanonicalizationOp":
        if (
            self.admissible_minimum is not None
            and self.admissible_maximum is not None
            and self.admissible_maximum < self.admissible_minimum
        ):
            raise ValueError("canonicalization admissible maximum must be >= minimum")
        range_values = (
            self.admissible_minimum,
            self.admissible_maximum,
            self.minimum,
            self.maximum,
        )
        if self.kind is not CanonicalizationKind.CLAMP_INT and any(
            value is not None for value in range_values
        ):
            raise ValueError("integer bounds are valid only for clamp_int")
        if self.kind is not CanonicalizationKind.ALIASES and self.aliases:
            raise ValueError("aliases are valid only for the aliases operation")
        return self

    def apply(self, value: Any) -> Any:
        if self.kind is CanonicalizationKind.CLAMP_INT:
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError("clamp_int requires an integer")
            if self.admissible_minimum is not None and value < self.admissible_minimum:
                raise ValueError("integer is below the canonicalization contract domain")
            if self.admissible_maximum is not None and value > self.admissible_maximum:
                raise ValueError("integer is above the canonicalization contract domain")
            if self.minimum is not None:
                value = max(self.minimum, value)
            if self.maximum is not None:
                value = min(self.maximum, value)
            return value
        if self.kind is CanonicalizationKind.STRIP:
            if not isinstance(value, str):
                raise TypeError("strip requires a string")
            return value.strip()
        if self.kind is CanonicalizationKind.CASEFOLD:
            if not isinstance(value, str):
                raise TypeError("casefold requires a string")
            return value.casefold()
        if self.kind is CanonicalizationKind.SORT_UNIQUE:
            if not isinstance(value, (list, tuple)):
                raise TypeError("sort_unique requires a list or tuple")
            # JSON identity is deterministic across heterogeneous scalar values.
            keyed = {json.dumps(item, sort_keys=True, default=str): item for item in value}
            return [keyed[key] for key in sorted(keyed)]
        if self.kind is CanonicalizationKind.ALIASES:
            if isinstance(value, str) and value in self.aliases:
                return copy.deepcopy(self.aliases[value])
            key = json.dumps(value, sort_keys=True, default=str)
            return copy.deepcopy(self.aliases.get(key, value))
        raise ValueError(f"unknown canonicalization kind {self.kind!r}")


class ArgumentSemantics(BaseModel):
    """Declared task-semantic representative for one dotted argument path.

    ``equivalent`` means the tool result itself is observationally equivalent.
    ``monotone_superset`` permits a different raw result only when the registered
    application contract proves that the canonical result preserves every fact
    the downstream task consumes.  This is signed configuration, not an
    equivalence inferred by the compiler.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    operations: tuple[CanonicalizationOp, ...] = ()
    relation: SemanticRelation = SemanticRelation.EQUIVALENT
    notes: str = ""

    @field_validator("operations", mode="before")
    @classmethod
    def _operations(cls, value: Any) -> Any:
        return () if value is None else tuple(value)

    def canonicalize(self, value: Any) -> Any:
        out = copy.deepcopy(value)
        for operation in self.operations:
            out = operation.apply(out)
        return out


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
    argument_semantics: dict[str, ArgumentSemantics] = Field(default_factory=dict)
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

    def canonicalize_arguments(self, tool: str | None, arguments: dict[str, Any]) -> dict[str, Any]:
        """Apply the catalog's signed task-semantic argument contract.

        A missing path stays missing. A type mismatch is an explicit failure; the
        compiler and runtime must not silently reinterpret a malformed argument.
        """

        out = copy.deepcopy(arguments)
        for path, semantics in sorted(self.get(tool).argument_semantics.items()):
            present, value = _get_path(out, path)
            if not present:
                continue
            _set_path(out, path, semantics.canonicalize(value))
        return out

    def arguments_equivalent(
        self,
        tool: str | None,
        left: dict[str, Any],
        right: dict[str, Any],
    ) -> bool:
        """Whether two calls share a declared task-semantic representative."""

        try:
            return self.canonicalize_arguments(tool, left) == self.canonicalize_arguments(tool, right)
        except (TypeError, ValueError):
            return False

    def composite_eligible(self, tool: str | None) -> bool:
        """Whether a reviewed tool may be packaged inside a fused interface."""

        spec = self.get(tool)
        return spec.compilable and Capability.BATCHABLE in spec.capabilities

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
        payload = self.model_dump(mode="json")
        # Preserve the identity of pre-GCS catalogs. The additive field has no
        # semantics when empty, so changing every existing manifest merely because
        # a newer reader knows the field would violate backward compatibility.
        for spec in payload.get("tools", {}).values():
            if not spec.get("argument_semantics"):
                spec.pop("argument_semantics", None)
        blob = json.dumps(
            payload, sort_keys=True, separators=(",", ":")
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


def _get_path(value: dict[str, Any], path: str) -> tuple[bool, Any]:
    cur: Any = value
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False, None
        cur = cur[part]
    return True, cur


def _set_path(value: dict[str, Any], path: str, item: Any) -> None:
    cur = value
    parts = path.split(".")
    for part in parts[:-1]:
        child = cur.get(part)
        if not isinstance(child, dict):
            child = {}
            cur[part] = child
        cur = child
    cur[parts[-1]] = item
