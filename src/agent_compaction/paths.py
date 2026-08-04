"""Path/payload primitives shared by every layer.

Kept dependency-free on purpose: the DSL, the schemas and the graph builder all
need ``flatten``/``resolve_path``, and routing them through :mod:`schema.traces`
creates an import cycle (schema → artifacts → grc.program → grc.dsl → schema).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

__all__ = ["flatten", "resolve_path", "content_digest", "stable_int", "PathValue"]


PathValue = tuple[str, Any]


def flatten(payload: Any, prefix: str = "", *, max_items: int = 64, max_depth: int = 6) -> list[PathValue]:
    """Flatten a JSON-ish payload into ``(path, value)`` pairs.

    Paths use dotted field access and bracketed list indices so that a path is
    both human readable and machine re-resolvable: ``recs[1].id``,
    ``invoices[0].line_items[1].amount_cents``.

    Container nodes are emitted as well as leaves, because Algorithm 3 needs to
    bind *root* paths (a list) and then apply ``filter |> project`` to them.
    """

    out: list[PathValue] = []

    def rec(node: Any, path: str, depth: int) -> None:
        if depth > max_depth:
            return
        if isinstance(node, dict):
            if path:
                out.append((path, node))
            for k, v in node.items():
                if not isinstance(k, str):
                    continue
                child = f"{path}.{k}" if path else k
                rec(v, child, depth + 1)
        elif isinstance(node, (list, tuple)):
            if path:
                out.append((path, list(node)))
            for i, v in enumerate(node[:max_items]):
                rec(v, f"{path}[{i}]", depth + 1)
        else:
            if path:
                out.append((path, node))

    rec(payload, prefix, 0)
    return out


def resolve_path(payload: Any, path: str) -> Any:
    """Inverse of :func:`flatten` for a single path. Returns ``None`` on miss."""

    if not isinstance(path, str) or not path:
        return payload if path == "" else None

    cur = payload
    token = ""
    i = 0
    n = len(path)
    while i < n:
        ch = path[i]
        if ch == ".":
            if token:
                cur = _get_field(cur, token)
                token = ""
            i += 1
        elif ch == "[":
            if token:
                cur = _get_field(cur, token)
                token = ""
            j = path.find("]", i)
            if j < 0:
                return None
            raw_index = path[i + 1 : j]
            if not raw_index.isdigit():
                return None
            idx = int(raw_index)
            if not isinstance(cur, (list, tuple)) or idx >= len(cur):
                return None
            cur = cur[idx]
            i = j + 1
        else:
            token += ch
            i += 1
        if cur is None:
            return None
    if token:
        cur = _get_field(cur, token)
    return cur


def _get_field(node: Any, name: str) -> Any:
    if isinstance(node, dict):
        return node.get(name)
    return getattr(node, name, None)


def content_digest(payload: Any) -> str:
    """Stable content-addressed digest for payload references."""

    blob = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode()).hexdigest()[:32]


def stable_int(payload: Any, *, bits: int = 64) -> int:
    """Return a process-independent integer digest.

    Python's built-in ``hash`` is salted per process and must not be used for
    artifact identities, benchmark fixtures, or protocol call IDs.
    """

    if bits <= 0 or bits % 8:
        raise ValueError("bits must be a positive multiple of 8")
    blob = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()
    return int.from_bytes(hashlib.sha256(blob).digest()[: bits // 8], "big")

