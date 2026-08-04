"""Immutable normalized snapshot store shared by domain adapters."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


class SnapshotError(RuntimeError):
    """Snapshot identity, schema, or record lookup is invalid."""


def canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise SnapshotError("snapshot records must be finite JSON") from exc


class FrozenRecordStore:
    """Qualified local reads whose digest binds every model-visible source record."""

    def __init__(self, records: Mapping[str, Any], *, snapshot_digest: str | None = None) -> None:
        encoded = canonical(dict(records))
        observed = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        if snapshot_digest is not None and snapshot_digest.removeprefix("sha256:") != observed:
            raise SnapshotError("normalized records do not match the declared snapshot digest")
        self.snapshot_digest = observed
        self._records = MappingProxyType(json.loads(encoded))

    def check(self, snapshot_digest: str) -> None:
        if snapshot_digest.removeprefix("sha256:") != self.snapshot_digest:
            raise SnapshotError("requested snapshot does not match the frozen records")

    def get(self, section: str, key: str, *, snapshot_digest: str) -> Any:
        self.check(snapshot_digest)
        value = self._records.get(section, {}).get(key)
        return copy.deepcopy(value)

    def section(self, section: str, *, snapshot_digest: str) -> Mapping[str, Any]:
        self.check(snapshot_digest)
        return copy.deepcopy(self._records.get(section, {}))

    @classmethod
    def load(cls, path: str | Path, *, schema: str) -> "FrozenRecordStore":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("schema") != schema:
            raise SnapshotError("unsupported normalized snapshot schema")
        return cls(payload["records"], snapshot_digest=payload.get("snapshot_digest"))
