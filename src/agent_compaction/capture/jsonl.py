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
import os
from pathlib import Path
import tempfile
from typing import Iterable

from ..schema.traces import Episode

__all__ = ["EpisodeStoreError", "read_jsonl", "write_jsonl"]


class EpisodeStoreError(ValueError):
    """A JSONL snapshot is malformed or cannot represent the typed episode IR."""


def _canonical_line(episode: Episode) -> str:
    """Return the strict, deterministic wire representation of one episode."""

    try:
        return json.dumps(
            episode.to_dict(),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise EpisodeStoreError(
            f"episode {episode.episode_id!r} is not strict JSON: {exc}"
        ) from exc


def write_jsonl(episodes: Iterable[Episode], path: str | Path) -> Path:
    """Atomically write a deterministic episode snapshot and return its path.

    The existing target is replaced only after every episode has serialized and the
    temporary file has reached durable storage. Duplicate episode identities are rejected
    because they make joins and grouped evaluation ambiguous.
    """

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
    )
    temporary = Path(temporary_name)
    seen: set[str] = set()
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            for episode in episodes:
                if episode.episode_id in seen:
                    raise EpisodeStoreError(
                        f"duplicate episode_id while writing {target}: {episode.episode_id!r}"
                    )
                seen.add(episode.episode_id)
                handle.write(_canonical_line(episode) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        # Persist the directory entry where the platform supports directory fsync.
        try:
            directory_fd = os.open(target.parent, os.O_RDONLY)
        except OSError:  # pragma: no cover - platform-specific durability fallback
            directory_fd = None
        if directory_fd is not None:
            try:
                try:
                    os.fsync(directory_fd)
                except OSError:  # pragma: no cover - filesystems without directory fsync
                    pass
            finally:
                os.close(directory_fd)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return target


def read_jsonl(path: str | Path) -> list[Episode]:
    """Stream and validate an episode snapshot. Blank lines are ignored."""

    source = Path(path)
    episodes: list[Episode] = []
    seen: set[str] = set()
    with source.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise TypeError("top-level value must be a JSON object")
                episode = Episode.from_dict(payload)
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                raise EpisodeStoreError(f"{source}:{line_number}: {exc}") from exc
            if episode.episode_id in seen:
                raise EpisodeStoreError(
                    f"{source}:{line_number}: duplicate episode_id {episode.episode_id!r}"
                )
            seen.add(episode.episode_id)
            episodes.append(episode)
    return episodes
