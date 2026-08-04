"""Framework-neutral episode store: newline-delimited JSON of the typed Episode IR.

This is the reference persistence backend and the one every experiment, demonstration and
paper script uses. It has no third-party dependency at all: an episode is written with
:func:`json.dumps` and read back with :meth:`Episode.from_dict`, so the on-disk form is
exactly the IR that :mod:`agent_compaction.schema.traces` defines.

That property is the point. A round trip through this module is what lets the compiler
claim its input representation is independent of any tracing platform: if the IR could
only be reconstructed by calling a vendor SDK, the claim would be circular. Capture
adapters (currently the OpenAI Agents SDK) translate a foreign trace model *into* the IR;
this module persists the IR itself.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..schema.traces import Episode

__all__ = ["read_jsonl", "write_jsonl"]


def write_jsonl(episodes: list[Episode], path: str | Path) -> Path:
    """Write one JSON object per line and return the path written."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for episode in episodes:
            handle.write(json.dumps(episode.to_dict(), default=str) + "\n")
    return target


def read_jsonl(path: str | Path) -> list[Episode]:
    """Read episodes written by :func:`write_jsonl`. Blank lines are skipped."""

    return [
        Episode.from_dict(json.loads(line))
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
