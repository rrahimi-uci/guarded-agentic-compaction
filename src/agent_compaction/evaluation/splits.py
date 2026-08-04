"""Grouped data separation (execution-plan §11.3).

Splitting is by scenario group, never by span or episode: near-duplicate prompts,
templates, documents, users and workflow-generated variants stay together, or the
"held-out" set is a copy of the training set with a different id.

Four disjoint roles plus one prospective role:

* **train** — mining, route fitting, synthesis.
* **dev** — transformation choice, contract refinement, margins.
* **calibration** — gate threshold only.
* **test** — sealed; opened once, after artifacts and analysis code are frozen.
* **shadow** — prospective operational validation, never pooled into the
  retrospective test claim.

When drift is plausible the split is chronological: the sealed test is the tail of
the stream, not a random sample of it.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

__all__ = ["Splits", "make_splits", "assert_disjoint", "LeakageError"]


class LeakageError(AssertionError):
    """Raised when split membership overlaps."""


@dataclass(slots=True)
class Splits:
    train: frozenset[str] = frozenset()
    dev: frozenset[str] = frozenset()
    calibration: frozenset[str] = frozenset()
    test: frozenset[str] = frozenset()
    shadow: frozenset[str] = frozenset()
    chronological: bool = False
    seed: int = 0

    @property
    def roles(self) -> dict[str, frozenset[str]]:
        return {
            "train": self.train,
            "dev": self.dev,
            "calibration": self.calibration,
            "test": self.test,
            "shadow": self.shadow,
        }

    def role_of(self, group_id: str) -> str | None:
        for name, members in self.roles.items():
            if group_id in members:
                return name
        return None

    def filter(self, items: Sequence[Any], role: str, *, key: str = "group_id") -> list[Any]:
        members = self.roles[role]
        out = []
        for item in items:
            gid = getattr(item, key, None)
            if gid is None and hasattr(item, "episode"):
                gid = item.episode.group_id
            if gid in members:
                out.append(item)
        return out

    def digest(self) -> str:
        blob = json.dumps(
            {name: sorted(members) for name, members in self.roles.items()},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    def manifest(self) -> dict[str, Any]:
        return {
            "digest": self.digest(),
            "chronological": self.chronological,
            "seed": self.seed,
            "sizes": {name: len(members) for name, members in self.roles.items()},
            "groups": {name: sorted(members) for name, members in self.roles.items()},
        }


def make_splits(
    episodes: Sequence[Any],
    *,
    fractions: tuple[float, float, float, float] = (0.35, 0.20, 0.20, 0.25),
    shadow_fraction: float = 0.0,
    chronological: bool = False,
    seed: int = 20260801,
) -> Splits:
    """Partition scenario groups into train/dev/calibration/test (+ shadow tail)."""

    if len(fractions) != 4 or any(value < 0 for value in fractions):
        raise ValueError("fractions must contain four non-negative values")
    if abs(sum(fractions) - 1.0) > 1e-9:
        raise ValueError("split fractions must sum to 1")
    if not 0.0 <= shadow_fraction < 1.0:
        raise ValueError("shadow_fraction must be in [0, 1)")

    groups: dict[str, str] = {}
    for ep in episodes:
        gid = ep.envelope.group_id if hasattr(ep, "envelope") else ep.group_id
        day = ep.envelope.day if hasattr(ep, "envelope") else getattr(ep, "day", "")
        prev = groups.get(gid)
        groups[gid] = min(prev, day) if prev else day

    ordered = sorted(groups, key=lambda g: (groups[g], g)) if chronological else sorted(groups)
    if not chronological:
        rng = random.Random(seed)
        rng.shuffle(ordered)

    n = len(ordered)
    n_shadow = int(round(n * shadow_fraction))
    shadow = ordered[n - n_shadow :] if n_shadow else []
    body = ordered[: n - n_shadow]
    m = len(body)
    f_tr, f_dev, f_cal, _ = fractions
    i1 = int(round(m * f_tr))
    i2 = i1 + int(round(m * f_dev))
    i3 = i2 + int(round(m * f_cal))
    splits = Splits(
        train=frozenset(body[:i1]),
        dev=frozenset(body[i1:i2]),
        calibration=frozenset(body[i2:i3]),
        test=frozenset(body[i3:]),
        shadow=frozenset(shadow),
        chronological=chronological,
        seed=seed,
    )
    assert_disjoint(splits)
    return splits


def assert_disjoint(splits: Splits) -> None:
    seen: dict[str, str] = {}
    for role, members in splits.roles.items():
        for gid in members:
            if gid in seen:
                raise LeakageError(f"group {gid} in both {seen[gid]} and {role}")
            seen[gid] = role
