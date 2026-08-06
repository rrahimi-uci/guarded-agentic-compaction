"""Artifact registry: local, signed, and resolvable in O(1) on the hot path.

Resolution is a dict lookup on ``(compatibility_key, partition)`` — no network, no
model call, no scan (proposal §4.7 line 1). Everything expensive happened offline.

The registry is also the audit surface: it holds the lifecycle state, the evidence,
the rollback target, and a kill switch that takes precedence over every other
decision.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from ..schema.artifacts import Artifact, Lifecycle

__all__ = ["Registry", "RegistryError"]


class RegistryError(Exception):
    pass


def _partition_key(partition: dict[str, str]) -> str:
    # Canonical JSON avoids aliasing partitions whose keys or values contain the
    # delimiters used by the original string-join representation.
    return json.dumps(partition, sort_keys=True, separators=(",", ":"))


@dataclass(slots=True)
class Registry:
    """A set of artifacts plus the controls around them."""

    name: str = "registry"
    artifacts: list[Artifact] = field(default_factory=list)
    signing_key: bytes = b""
    kill_switch: bool = False
    active_stages: tuple[Lifecycle, ...] = (Lifecycle.ACTIVE,)
    index: dict[str, list[Artifact]] = field(default_factory=dict)
    previous: "Registry | None" = None

    # -- construction -----------------------------------------------------
    def add(self, artifact: Artifact) -> None:
        if self.by_id(artifact.artifact_id) is not None:
            raise RegistryError(f"duplicate artifact id: {artifact.artifact_id}")
        if self.signing_key:
            artifact.sign(self.signing_key)
        self.artifacts.append(artifact)
        self._reindex()

    def extend(self, artifacts: Iterable[Artifact]) -> None:
        for a in artifacts:
            self.add(a)

    def _reindex(self) -> None:
        self.index = {}
        for a in self.artifacts:
            key = f"{a.compatibility_key}#{_partition_key(a.partition)}"
            self.index.setdefault(key, []).append(a)

    # -- resolution -------------------------------------------------------
    def resolve(
        self,
        compatibility_key: str,
        partition: dict[str, str],
        *,
        kind: str | None = None,
        stages: Sequence[Lifecycle] | None = None,
    ) -> list[Artifact]:
        if self.kill_switch:
            return []
        key = f"{compatibility_key}#{_partition_key(partition)}"
        eligible = tuple(stages) if stages is not None else self.active_stages
        out = [a for a in self.index.get(key, []) if a.lifecycle in eligible]
        if kind is not None:
            out = [a for a in out if a.kind == kind]
        if self.signing_key:
            out = [a for a in out if a.verify_signature(self.signing_key)]
        return out

    def by_id(self, artifact_id: str) -> Artifact | None:
        for a in self.artifacts:
            if a.artifact_id == artifact_id:
                return a
        return None

    def active(self) -> list[Artifact]:
        return [a for a in self.artifacts if a.lifecycle in self.active_stages]

    # -- reporting --------------------------------------------------------
    def report(self) -> str:
        lines = [
            f"registry {self.name}: {len(self.artifacts)} artifacts "
            f"({len(self.active())} active, kill_switch={self.kill_switch})",
            "─" * 78,
        ]
        for a in self.artifacts:
            lines.append(
                f"  {a.artifact_id:28s} {a.name:36s} {a.kind:5s} {a.lifecycle.value:16s} "
                f"k={a.evidence.removed_requests:.2f} supp={a.evidence.support_groups}/{a.evidence.total_groups} "
                f"η={a.gate.threshold:.2f} R⁺={a.gate.risk_upper_bound:.3f}"
            )
        return "\n".join(lines)

    def explain(self) -> str:
        return "\n\n".join(a.explain() for a in self.artifacts) or "(no artifacts)"

    # -- persistence ------------------------------------------------------
    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        if self.signing_key:
            for artifact in self.artifacts:
                artifact.sign(self.signing_key)
        payload = {
            "name": self.name,
            "kill_switch": self.kill_switch,
            "active_stages": [s.value for s in self.active_stages],
            "artifacts": [a.to_dict() for a in self.artifacts],
        }
        _atomic_write(p / "registry.json", json.dumps(payload, indent=2, default=str))
        for a in self.artifacts:
            _atomic_write(p / _artifact_filename(a.artifact_id), a.explain())
        return p / "registry.json"

    @classmethod
    def load(cls, path: str | Path, *, signing_key: bytes = b"") -> "Registry":
        p = Path(path)
        f = p / "registry.json" if p.is_dir() else p
        payload = json.loads(f.read_text())
        reg = cls(
            name=payload.get("name", "registry"),
            signing_key=signing_key,
            kill_switch=payload.get("kill_switch", False),
            active_stages=tuple(Lifecycle(s) for s in payload.get("active_stages", ["active"])),
        )
        reg.artifacts = [Artifact.from_dict(d) for d in payload.get("artifacts", [])]
        if signing_key:
            bad = [a.artifact_id for a in reg.artifacts if not a.verify_signature(signing_key)]
            if bad:
                raise RegistryError(f"signature verification failed for {bad}")
        reg._reindex()
        return reg

    def diff(self, other: "Registry") -> dict[str, Any]:
        """Registry diff for the CI story of proposal §6.4."""

        mine = {(a.name, _partition_key(a.partition)): a for a in self.artifacts}
        theirs = {(a.name, _partition_key(a.partition)): a for a in other.artifacts}
        gained_keys = sorted(set(mine) - set(theirs))
        lost_keys = sorted(set(theirs) - set(mine))
        gained = [name for name, _ in gained_keys]
        lost = [name for name, _ in lost_keys]
        kept_keys = sorted(set(mine) & set(theirs))
        kept = [name for name, _ in kept_keys]
        return {
            "gained": gained,
            "lost": lost,
            "kept": kept,
            "coverage_delta": round(
                sum(mine[n].gate.coverage for n in mine) - sum(theirs[n].gate.coverage for n in theirs), 4
            ),
        }


def _artifact_filename(artifact_id: str) -> str:
    """Map an artifact identity to a safe, collision-resistant local filename."""

    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", artifact_id).strip("._") or "artifact"
    digest = __import__("hashlib").sha256(artifact_id.encode()).hexdigest()[:8]
    return f"{cleaned[:96]}-{digest}.txt"


def _atomic_write(path: Path, content: str) -> None:
    """Replace a registry file atomically within its destination directory."""

    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
