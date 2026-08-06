"""Append-only, hash-chained execution ledger for resumable benchmark runs."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

__all__ = ["LedgerConflict", "LedgerRecord", "RunLedger"]


class LedgerConflict(RuntimeError):
    """The ledger is corrupt or an event identifier was reused inconsistently."""


def _canonical(value: Mapping[str, Any]) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("ledger payload must be finite JSON data") from exc


@dataclass(frozen=True, slots=True)
class LedgerRecord:
    schema: str
    sequence: int
    run_id: str
    event_id: str
    event_type: str
    created_at: str
    payload: Mapping[str, Any]
    previous_hash: str
    record_hash: str

    def __post_init__(self) -> None:
        if type(self.sequence) is not int or self.sequence < 1:
            raise ValueError("ledger sequence must be a positive integer")
        for label in ("schema", "run_id", "event_id", "event_type", "created_at"):
            value = getattr(self, label)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"ledger {label} must be a non-empty string")
        for label in ("previous_hash", "record_hash"):
            value = getattr(self, label)
            if value and (
                len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise ValueError(f"ledger {label} must be a SHA-256 digest")
        if not isinstance(self.payload, Mapping):
            raise ValueError("ledger payload must be a mapping")
        _canonical(self.payload)

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["payload"] = dict(self.payload)
        return data


class RunLedger:
    """A local JSONL ledger with idempotent append and integrity validation."""

    schema = "agent-compaction-run-ledger/v1"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @staticmethod
    def _hash(data: Mapping[str, Any]) -> str:
        return hashlib.sha256(_canonical(data).encode("utf-8")).hexdigest()

    def _decode(self, text: str) -> list[LedgerRecord]:
        records: list[LedgerRecord] = []
        previous = ""
        for line_number, line in enumerate(text.splitlines(), start=1):
            try:
                raw = json.loads(line)
                record = LedgerRecord(**raw)
            except Exception as exc:
                raise LedgerConflict(f"invalid ledger record at line {line_number}") from exc
            if record.schema != self.schema or record.sequence != line_number:
                raise LedgerConflict(f"ledger sequence/schema mismatch at line {line_number}")
            if record.previous_hash != previous:
                raise LedgerConflict(f"ledger hash chain mismatch at line {line_number}")
            unsigned = record.as_dict()
            observed_hash = unsigned.pop("record_hash")
            if self._hash(unsigned) != observed_hash:
                raise LedgerConflict(f"ledger record hash mismatch at line {line_number}")
            previous = record.record_hash
            records.append(record)
        return records

    def records(self) -> tuple[LedgerRecord, ...]:
        if not self.path.exists():
            return ()
        with self.path.open("r", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_SH)
            try:
                return tuple(self._decode(handle.read()))
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def append(
        self,
        *,
        run_id: str,
        event_id: str,
        event_type: str,
        payload: Mapping[str, Any],
        created_at: str | None = None,
    ) -> LedgerRecord:
        for label, value in (
            ("run_id", run_id),
            ("event_id", event_id),
            ("event_type", event_type),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{label} must be a non-empty string")
        payload_dict = dict(payload)
        # Canonicalize through JSON so later mutation of caller-owned nested values
        # cannot change the returned record relative to the durable bytes.
        payload_dict = json.loads(_canonical(payload_dict))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                handle.seek(0)
                records = self._decode(handle.read())
                for existing in records:
                    if existing.run_id == run_id and existing.event_id == event_id:
                        if existing.event_type == event_type and dict(existing.payload) == payload_dict:
                            return existing
                        raise LedgerConflict(
                            f"event {(run_id, event_id)!r} was reused with different content"
                        )
                unsigned = {
                    "schema": self.schema,
                    "sequence": len(records) + 1,
                    "run_id": run_id,
                    "event_id": event_id,
                    "event_type": event_type,
                    "created_at": created_at
                    or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "payload": payload_dict,
                    "previous_hash": records[-1].record_hash if records else "",
                }
                record = LedgerRecord(**unsigned, record_hash=self._hash(unsigned))
                handle.seek(0, os.SEEK_END)
                handle.write(_canonical(record.as_dict()) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
                return record
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def validate(self) -> dict[str, Any]:
        records = self.records()
        return {
            "schema": self.schema,
            "records": len(records),
            "last_hash": records[-1].record_hash if records else "",
            "runs": sorted({record.run_id for record in records}),
        }

    def has_event(self, run_id: str, event_id: str) -> bool:
        return any(
            record.run_id == run_id and record.event_id == event_id
            for record in self.records()
        )
