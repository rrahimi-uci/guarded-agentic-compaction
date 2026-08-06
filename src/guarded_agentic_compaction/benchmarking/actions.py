"""Frozen action identities and independent macro-review evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Mapping

__all__ = [
    "ActionSpec",
    "MacroApproval",
    "MacroApprovalError",
    "frozen_artifact_digest",
]


class MacroApprovalError(ValueError):
    """A macro lacks independent, compatible review evidence."""


def frozen_artifact_digest(
    payload: Mapping[str, Any], *, digest_field: str
) -> str:
    """Digest a JSON artifact while excluding its self-referential digest field."""

    if not digest_field.strip():
        raise ValueError("digest_field must not be empty")
    material = dict(payload)
    material.pop(digest_field, None)
    try:
        blob = json.dumps(
            material,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("frozen artifact must contain finite JSON data") from exc
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class MacroApproval:
    domain: str
    macro_version: str
    author: str
    reviewer: str
    reviewed_at: str
    implementation_digest: str
    schema_digest: str
    effect_catalog_digest: str
    evaluator_digest: str
    approved: bool
    notes: str = ""

    def validate(self) -> None:
        for name in (
            "domain",
            "macro_version",
            "author",
            "reviewer",
            "reviewed_at",
            "implementation_digest",
            "schema_digest",
            "effect_catalog_digest",
            "evaluator_digest",
        ):
            if not getattr(self, name).strip():
                raise MacroApprovalError(f"{name} must not be empty")
        if self.author.strip().casefold() == self.reviewer.strip().casefold():
            raise MacroApprovalError("macro reviewer must be independent from author")
        try:
            reviewed_at = datetime.fromisoformat(self.reviewed_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise MacroApprovalError("reviewed_at must be ISO-8601") from exc
        if reviewed_at.tzinfo is None:
            raise MacroApprovalError("reviewed_at must include a timezone")
        for name in (
            "implementation_digest",
            "schema_digest",
            "effect_catalog_digest",
            "evaluator_digest",
        ):
            value = getattr(self, name)
            if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
                raise MacroApprovalError(f"{name} must be a lowercase SHA-256 digest")
        if not self.approved:
            raise MacroApprovalError("macro has not been approved")

    @property
    def digest(self) -> str:
        self.validate()
        blob = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ActionSpec:
    name: str
    version: str
    implementation_digest: str
    prompt_digest: str
    tool_digest: str
    evaluator_digest: str
    compatibility_key: str
    metadata: Mapping[str, Any]
    macro_approval_digest: str = ""

    def __post_init__(self) -> None:
        for name in (
            "name",
            "version",
            "implementation_digest",
            "prompt_digest",
            "tool_digest",
            "evaluator_digest",
            "compatibility_key",
        ):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} must not be empty")
        if self.name == "macro" and not self.macro_approval_digest:
            raise MacroApprovalError("macro action requires an approval digest")

    @property
    def digest(self) -> str:
        payload = asdict(self)
        payload["metadata"] = dict(self.metadata)
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()
