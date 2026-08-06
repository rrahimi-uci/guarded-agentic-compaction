"""Rendering helpers for estimate and experiment reports.

Every table published by this project carries its denominators, its substrate label and
the run manifest that produced it (execution-plan §13.6). These helpers make that the
default rather than something a report author has to remember.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

__all__ = ["render_table", "render_markdown"]


def render_table(
    rows: Sequence[dict[str, Any]],
    columns: Sequence[tuple[str, str]],
    *,
    align_right: Iterable[str] = (),
) -> str:
    """Render a markdown table from ``rows`` given ``(key, header)`` columns."""

    right = set(align_right)
    header = "| " + " | ".join(h for _, h in columns) + " |"
    sep = "|" + "|".join(("---:" if k in right else ":---") for k, _ in columns) + "|"
    lines = [header, sep]
    for row in rows:
        cells = []
        for key, _ in columns:
            value = row.get(key, "")
            cells.append(_fmt(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _fmt(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.4g}"
    if isinstance(value, dict):
        return ", ".join(f"{k}={_fmt(v)}" for k, v in list(value.items())[:4])
    if isinstance(value, (list, tuple)):
        return ", ".join(_fmt(v) for v in value[:5])
    return str(value)


def render_markdown(title: str, sections: Sequence[tuple[str, str]], *, manifest: dict[str, Any] | None = None) -> str:
    parts = [f"# {title}", ""]
    if manifest:
        parts.append("**Run manifest.** " + ", ".join(f"{k}={v}" for k, v in manifest.items() if k != "warning"))
        if manifest.get("warning"):
            parts.append("")
            parts.append(f"> {manifest['warning']}")
        parts.append("")
    for heading, body in sections:
        parts.append(f"## {heading}")
        parts.append("")
        parts.append(body)
        parts.append("")
    return "\n".join(parts)
