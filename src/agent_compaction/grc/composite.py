"""Guarded Composite Synthesis (GCS).

GCS packages an already synthesized region program behind one task-specific
interface.  The package changes what the model sees, not what the verifier trusts:
all internal calls still run through :class:`ToolFacade`, retain their individual
effects and provenance, and are verified before a projected result is released.

The projection language reuses the bounded binding DSL.  It cannot call code,
resolve a dynamic tool, or read state outside the program's verified live-outs.
"""

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Mapping

from ..paths import resolve_path
from ..schema.effects import EffectCatalog
from .dsl import Binding, Expr, binding_from_dict

if TYPE_CHECKING:  # pragma: no cover
    from .program import Program

__all__ = [
    "CompositeProjectionError",
    "CompositeSynthesisError",
    "CompositeSpec",
    "synthesize_composite",
]


class CompositeSynthesisError(ValueError):
    """A program cannot be safely packaged as a composite."""


class CompositeProjectionError(ValueError):
    """A verified program result cannot satisfy its exposed projection."""


def _set_path(target: dict[str, Any], path: str, value: Any) -> None:
    current = target
    parts = path.split(".")
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[parts[-1]] = value


@dataclass(slots=True)
class CompositeSpec:
    """Serializable one-interface view over an internally verified program."""

    name: str
    description: str
    inputs: tuple[str, ...]
    projection: dict[str, Binding]
    internal_tools: tuple[str, ...]
    pre_model: bool = True
    continuation_compatibility_key: str = ""
    schema_version: int = 1

    def arguments(self, entry_state: Mapping[str, Any]) -> dict[str, Any]:
        """Build the public composite arguments from admitted entry-state paths."""

        result: dict[str, Any] = {}
        for path in self.inputs:
            value = resolve_path(entry_state, path)
            if value is None:
                raise CompositeProjectionError(f"missing composite input: {path}")
            _set_path(result, path, copy.deepcopy(value))
        return result

    def project(self, outputs: Mapping[str, Any]) -> dict[str, Any]:
        """Expose only the declared sufficient view of verified live-outs."""

        result: dict[str, Any] = {}
        for target, binding in sorted(self.projection.items()):
            try:
                value = binding.evaluate(outputs)
            except Exception as exc:
                raise CompositeProjectionError(
                    f"projection {target!r} failed with {type(exc).__name__}"
                ) from exc
            if value is None:
                raise CompositeProjectionError(f"projection {target!r} resolved to null")
            _set_path(result, target, copy.deepcopy(value))
        return result

    def provenance(self, internal: Mapping[str, set[str]]) -> dict[str, tuple[str, ...]]:
        """Map every exposed field back to the internal source tools."""

        result: dict[str, tuple[str, ...]] = {}
        for target, binding in sorted(self.projection.items()):
            source = getattr(binding, "source", "")
            root = source.split(".", 1)[0]
            result[target] = tuple(sorted(internal.get(root, ())))
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputs": list(self.inputs),
            "projection": {name: binding.to_dict() for name, binding in self.projection.items()},
            "internal_tools": list(self.internal_tools),
            "pre_model": self.pre_model,
            "continuation_compatibility_key": self.continuation_compatibility_key,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CompositeSpec":
        return cls(
            name=str(payload["name"]),
            description=str(payload.get("description", "")),
            inputs=tuple(payload.get("inputs", ())),
            projection={
                str(name): binding_from_dict(dict(binding))
                for name, binding in dict(payload.get("projection", {})).items()
            },
            internal_tools=tuple(payload.get("internal_tools", ())),
            pre_model=bool(payload.get("pre_model", True)),
            continuation_compatibility_key=str(
                payload.get("continuation_compatibility_key", "")
            ),
            schema_version=int(payload.get("schema_version", 1)),
        )


def synthesize_composite(
    program: "Program",
    catalog: EffectCatalog,
    *,
    name: str | None = None,
    description: str | None = None,
    projection: Mapping[str, str | Binding] | None = None,
    pre_model: bool = True,
    continuation_compatibility_key: str = "",
) -> "Program":
    """Return a copy of ``program`` packaged behind one guarded interface.

    Every internal tool must explicitly carry the ``batchable`` capability.  A
    caller may request a task-specific ``target -> source`` projection, but each
    source must be rooted in a verified program live-out.  With no projection the
    full live-out mapping is preserved, which is safe but may save fewer tokens.
    """

    from .program import Program

    if not program.steps or not program.tools:
        raise CompositeSynthesisError("cannot package an empty program")
    blocked = [tool for tool in program.tools if not catalog.composite_eligible(tool)]
    if blocked:
        raise CompositeSynthesisError("tools lack batchable capability: " + ", ".join(blocked))

    roots = set(program.outputs)
    selected: dict[str, Binding] = {}
    raw_projection: Mapping[str, str | Binding] = projection or {
        output: output for output in sorted(program.outputs)
    }
    if not raw_projection:
        raise CompositeSynthesisError("composite projection must not be empty")
    variables_by_tool: dict[str, list[str]] = {}
    for step in program.call_steps():
        variables_by_tool.setdefault(step.tool, []).append(step.var)

    for target, source in sorted(raw_projection.items()):
        if not target or target.startswith(".") or target.endswith("."):
            raise CompositeSynthesisError(f"invalid projection target {target!r}")
        if isinstance(source, str) and source.startswith("tool:"):
            encoded = source[5:]
            if "::" not in encoded:
                raise CompositeSynthesisError(
                    "tool projection sources use 'tool:<name>::<result-path>'"
                )
            tool, result_path = encoded.split("::", 1)
            variables = variables_by_tool.get(tool, [])
            if len(variables) != 1:
                raise CompositeSynthesisError(
                    f"tool projection source {tool!r} must resolve to exactly one program step"
                )
            source = variables[0] + (f".{result_path}" if result_path else "")
        binding = Expr(source, ()) if isinstance(source, str) else source
        root = getattr(binding, "source", "").split(".", 1)[0]
        if root not in roots:
            raise CompositeSynthesisError(
                f"projection {target!r} reads {root!r}, outside verified live-outs"
            )
        selected[target] = binding

    digest = hashlib.sha256("|".join(program.tools).encode()).hexdigest()[:10]
    composite_name = name or f"compiled_{program.tools[0].split('.')[-1]}_{digest}"
    if not composite_name.replace("_", "").replace("-", "").isalnum():
        raise CompositeSynthesisError("composite name must be alphanumeric with '_' or '-'")

    packaged: Program = copy.deepcopy(program)
    packaged.composite = CompositeSpec(
        name=composite_name,
        description=description
        or "Guarded composite synthesized from a verified recurrent read program.",
        inputs=tuple(program.theta),
        projection=selected,
        internal_tools=tuple(program.tools),
        pre_model=pre_model,
        continuation_compatibility_key=continuation_compatibility_key,
    )
    return packaged
