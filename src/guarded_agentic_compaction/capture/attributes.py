"""The application-owned facts the trace contract adds (execution-plan §6).

The SDK already traces runner/task boundaries, turns, generations, functions,
guardrails and handoffs, and the adapter already captures inputs, outputs, calls
and errors.
This module carries only what neither can infer, and enforces the two rules that make
the rest safe: the entry state is *allowlisted*, and payloads are redacted before they
are stored.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from ..paths import flatten, resolve_path

__all__ = ["EntryStateContract", "redact", "PII_PATTERNS", "pseudonymize"]

#: Deliberately conservative: anything matching is tokenized before storage. The
#: allowlist is the primary control; these patterns are the second line.
PII_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"[\w.+-]+@[\w-]+\.[\w.-]+", "<email>"),
    (r"\b(?:\d[ -]*?){13,16}\b", "<card>"),
    (r"\b\d{3}-\d{2}-\d{4}\b", "<ssn>"),
    (r"\b(?:\+?\d{1,3}[ -]?)?\(?\d{3}\)?[ -]?\d{3}[ -]?\d{4}\b", "<phone>"),
)


@dataclass(slots=True)
class EntryStateContract:
    """Typed, allowlisted entry state. Fields outside the allowlist never leave the app."""

    allowlist: tuple[str, ...] = ()
    version: str = "v1"
    redact_values: bool = False

    def project(self, state: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for path in self.allowlist:
            value = resolve_path(state, path)
            if value is None:
                continue
            if self.redact_values:
                value = redact(value)
            _assign(out, path, value)
        return out

    def violations(self, state: dict[str, Any]) -> list[str]:
        """Paths present in the state that the contract does not admit."""

        allowed = set(self.allowlist)
        out: list[str] = []
        for path, value in flatten(state):
            if isinstance(value, (dict, list)):
                continue
            if not any(path == a or path.startswith(a + ".") or path.startswith(a + "[") for a in allowed):
                out.append(path)
        return out

    def digest(self) -> str:
        import json

        payload = json.dumps(
            {"allowlist": list(self.allowlist), "version": self.version},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _assign(target: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    cur = target
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


def redact(value: Any) -> Any:
    """Replace PII-shaped substrings. Structure is preserved; values are not."""

    if isinstance(value, str):
        out = value
        for pattern, token in PII_PATTERNS:
            out = re.sub(pattern, token, out)
        return out
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def pseudonymize(value: str, *, salt: str) -> str:
    """Stable pseudonym for a principal or tenant. Never a secret, never reversible."""

    return "p_" + hashlib.sha256((salt + "|" + value).encode()).hexdigest()[:16]
