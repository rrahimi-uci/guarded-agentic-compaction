"""Execution manifests: freeze the identity of what produced a trace.

Frozen at episode start, never edited afterwards. Any drift in a manifest field
invalidates every artifact compiled from episodes that carried it, which is what makes
"artifacts are build outputs, not assets" (proposal §6.4) enforceable rather than
aspirational.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Sequence

from ..schema.effects import EffectCatalog
from ..schema.traces import ExecutionManifest

__all__ = ["hash_text", "hash_tools", "build_manifest", "manifest_diff"]


def hash_text(text: str) -> str:
    return "#" + hashlib.sha256(text.encode()).hexdigest()[:8]


def hash_tools(tool_schemas: Iterable[Any]) -> str:
    blob = json.dumps([_schema_repr(t) for t in tool_schemas], sort_keys=True, default=str)
    return "#" + hashlib.sha256(blob.encode()).hexdigest()[:8]


def _schema_repr(tool: Any) -> Any:
    for attr in ("params_json_schema", "schema", "parameters"):
        if hasattr(tool, attr):
            return {"name": getattr(tool, "name", str(tool)), "schema": getattr(tool, attr)}
    if isinstance(tool, dict):
        return tool
    return {"name": getattr(tool, "name", str(tool))}


def build_manifest(
    *,
    commit: str,
    model: str,
    prompt: str,
    tools: Iterable[Any],
    policy: str,
    guardrails: str,
    catalog: EffectCatalog,
    entry_contract_version: str,
    sdk_version: str = "unknown",
    tracer_version: str = "agent-compaction/0.5.0",
) -> ExecutionManifest:
    # Hash a canonical, typed payload rather than delimiter-joining strings.  The
    # manifest id is used in diagnostics and trace envelopes, so it must change
    # when any compatibility-relevant input changes and must not admit ambiguous
    # tuples such as ("a|b", "c") and ("a", "b|c").
    tools_hash = hash_tools(tools)
    prompt_hash = hash_text(prompt)
    policy_hash = hash_text(policy)
    guardrail_hash = hash_text(guardrails)
    identity = {
        "commit": commit,
        "model": model,
        "prompt_hash": prompt_hash,
        "tools_hash": tools_hash,
        "policy_hash": policy_hash,
        "guardrail_hash": guardrail_hash,
        "effect_catalog_version": catalog.catalog_version,
        "entry_contract_version": entry_contract_version,
        "sdk_version": sdk_version,
        "tracer_version": tracer_version,
    }
    manifest_id = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:12]
    return ExecutionManifest(
        manifest_id=manifest_id,
        commit=commit,
        model=model,
        prompt_hash=prompt_hash,
        tools_hash=tools_hash,
        policy_hash=policy_hash,
        guardrail_hash=guardrail_hash,
        effect_catalog_version=catalog.catalog_version,
        entry_contract_version=entry_contract_version,
        sdk_version=sdk_version,
        tracer_version=tracer_version,
    )


def manifest_diff(a: ExecutionManifest, b: ExecutionManifest) -> dict[str, tuple[Any, Any]]:
    """Which manifest fields drifted. An empty diff means artifacts stay valid."""

    out: dict[str, tuple[Any, Any]] = {}
    for field_name in (
        "commit",
        "model",
        "prompt_hash",
        "tools_hash",
        "policy_hash",
        "guardrail_hash",
        "effect_catalog_version",
        "entry_contract_version",
        "sdk_version",
        "tracer_version",
    ):
        left, right = getattr(a, field_name), getattr(b, field_name)
        if left != right:
            out[field_name] = (left, right)
    return out
