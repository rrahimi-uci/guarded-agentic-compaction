#!/usr/bin/env python3
"""Synthetic trace generator with *planted* ground truth (execution-plan §10.6).

The compiler's acceptance criterion is not "it produced an artifact" but "it recovered
the regions that are recoverable and rejected the ones that are not". That needs
traces whose truth is known by construction, so this generator plants, per episode:

======================  =====================================================
plant                   what the compiler must do
======================  =====================================================
``valid``               a depth-2 binding over a stable list → recover it
``ungroundable``        an argument that first appears in a model response and
                        varies across traces → reject the window
``ambiguous``           the same value echoed by κ+1 producers → reject the slot
``effectful``           a WRITE_IRREVERSIBLE call inside the region → reject
``unknown_effect``      an undeclared tool inside the region → reject
``positional``          a list whose wanted record moves → reject ``last``,
                        accept ``filter(status == "active")``
``literal``             a pagination integer → bind as ``Const``, never derive
``missing_span``        a dropped tool result → episode not compiler-eligible
``drift``               a changed entry-contract version → separate manifest
======================  =====================================================

Usage::

    python scripts/generate_synthetic.py --out /tmp/synth.jsonl --episodes 400
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from agent_compaction.schema.effects import EffectCatalog
from agent_compaction.schema.traces import (
    Episode,
    EventKind,
    EventNode,
    ExecutionManifest,
    OutcomeLabels,
    TraceEnvelope,
    Usage,
    content_digest,
)

PLANTS = (
    "valid",
    "ungroundable",
    "ambiguous",
    "effectful",
    "unknown_effect",
    "positional",
    "literal",
    "missing_span",
    "drift",
)

SYNTHETIC_CATALOG = EffectCatalog.from_dict(
    {
        "version": 1,
        "name": "synthetic",
        "tools": {
            "auth.token": {
                "effect": "READ_EXTERNAL",
                "capabilities": ["speculatable", "replayable"],
                "resource": "auth",
            },
            "dir.lookup": {
                "effect": "READ_EXTERNAL",
                "capabilities": ["speculatable", "replayable", "cacheable"],
                "resource": "dir",
            },
            "acct.get": {
                "effect": "READ_EXTERNAL",
                "capabilities": ["speculatable", "replayable", "cacheable"],
                "resource": "acct",
            },
            "acct.page": {
                "effect": "READ_EXTERNAL",
                "capabilities": ["speculatable", "replayable", "cacheable"],
                "literal_only": ["limit"],
                "resource": "acct",
            },
            "notes.write": {"effect": "WRITE_IRREVERSIBLE", "capabilities": [], "resource": "notes"},
        },
    }
)

MANIFEST = ExecutionManifest(
    manifest_id="synth-m1",
    commit="synthetic",
    model="sim-model-1",
    prompt_hash="#p1",
    tools_hash="#t1",
    policy_hash="#pol1",
    guardrail_hash="#g1",
    effect_catalog_version=SYNTHETIC_CATALOG.catalog_version,
    entry_contract_version="v1",
)

ENTRY_ALLOWLIST = ("tenant", "user_email", "area", "page_size")


@dataclass(slots=True)
class _Builder:
    episode_id: str
    group_id: str
    entry_state: dict[str, Any]
    day: str
    plant: str
    events: list[EventNode] = field(default_factory=list)
    clock: float = 0.0

    def boundary(self, tools: Sequence[str]) -> None:
        self.events.append(
            EventNode(
                node_id=f"{self.episode_id}:q{len(self.events)}",
                kind=EventKind.MODEL_REQ,
                index=len(self.events),
                input={"prompt_blocks": ["b1", "b2"], "tools": list(tools), "n_observations": 0},
                t_start_ms=self.clock,
                t_end_ms=self.clock + 300,
                usage=Usage(input_tokens=800, cached_input_tokens=400, output_tokens=60),
                request_id=f"req-{len(self.events)}",
                attributes={"prompt_tokens": 400, "schema_tokens": 200, "dollars": 0.002},
            )
        )
        self.clock += 300

    def response(self, payload: dict[str, Any]) -> None:
        self.events.append(
            EventNode(
                node_id=f"{self.episode_id}:a{len(self.events)}",
                kind=EventKind.MODEL_RESP,
                index=len(self.events),
                output=payload,
                t_start_ms=self.clock,
                t_end_ms=self.clock,
            )
        )

    def call(self, tool: str, args: dict[str, Any], result: Any, *, drop_result: bool = False) -> None:
        self.boundary(["auth.token", "dir.lookup", "acct.get", "acct.page", "notes.write"])
        self.response({"type": "function_call", "tool": tool, "arguments": args})
        self.events.append(
            EventNode(
                node_id=f"{self.episode_id}:c{len(self.events)}",
                kind=EventKind.TOOL_CALL,
                index=len(self.events),
                tool=tool,
                input=args,
                t_start_ms=self.clock,
                t_end_ms=self.clock + 40,
            )
        )
        self.clock += 40
        if drop_result:
            return
        self.events.append(
            EventNode(
                node_id=f"{self.episode_id}:r{len(self.events)}",
                kind=EventKind.TOOL_RESULT,
                index=len(self.events),
                tool=tool,
                output=result,
                t_start_ms=self.clock,
                t_end_ms=self.clock,
            )
        )

    def finish(self) -> Episode:
        self.boundary(["auth.token"])
        self.response({"type": "message", "answer": {"ok": True}})
        envelope = TraceEnvelope(
            trace_id=f"tr-{self.episode_id}",
            episode_id=self.episode_id,
            group_id=self.group_id,
            manifest_id=MANIFEST.manifest_id,
            principal="svc.synth",
            tenant_partition=self.entry_state["tenant"],
            policy_version="pol-1",
            day=self.day,
            entry_state_ref=content_digest(self.entry_state),
        )
        manifest = MANIFEST
        if self.plant == "drift":
            # a changed entry-contract version must not be pooled with the rest
            manifest = ExecutionManifest(
                manifest_id="synth-m2",
                commit=MANIFEST.commit,
                model=MANIFEST.model,
                prompt_hash=MANIFEST.prompt_hash,
                tools_hash=MANIFEST.tools_hash,
                policy_hash=MANIFEST.policy_hash,
                guardrail_hash=MANIFEST.guardrail_hash,
                effect_catalog_version=MANIFEST.effect_catalog_version,
                entry_contract_version="v2",
            )
        return Episode(
            envelope=envelope,
            manifest=manifest,
            entry_state=self.entry_state,
            events=self.events,
            outcome=OutcomeLabels(task_success=True, semantic_score=1.0),
            final_state_digest="digest-0",
            attributes={"plant": self.plant, "substrate": "synthetic", "dollars": 0.01},
        )


def generate(
    *,
    n_episodes: int = 400,
    seed: int = 5,
    plant_weights: dict[str, float] | None = None,
) -> list[Episode]:
    rng = random.Random(seed)
    weights = plant_weights or {
        "valid": 0.46,
        "positional": 0.16,
        "literal": 0.08,
        "ungroundable": 0.08,
        "ambiguous": 0.06,
        "effectful": 0.06,
        "unknown_effect": 0.05,
        "missing_span": 0.03,
        "drift": 0.02,
    }
    names = list(weights)
    cum = []
    total = sum(weights.values())
    acc = 0.0
    for n in names:
        acc += weights[n] / total
        cum.append(acc)

    episodes: list[Episode] = []
    for i in range(n_episodes):
        r = rng.random()
        plant = names[next(j for j, c in enumerate(cum) if r <= c)]
        episodes.append(_one(i, plant, rng))
    return episodes


def _one(i: int, plant: str, rng: random.Random) -> Episode:
    email_raw = f"User.{i % 97}.Name@Corp{i % 7}.example"
    entry = {
        "tenant": "t_synth",
        "user_email": email_raw,
        "area": rng.choice(["alpha", "beta", "gamma", "delta"]),
        "page_size": 4,
    }
    b = _Builder(
        episode_id=f"syn-{i:05d}",
        group_id=f"case:{i % 220}",
        entry_state=entry,
        day=f"2026-05-{1 + (i % 27):02d}",
        plant=plant,
    )
    token = f"tok_{i:05d}"
    b.call("auth.token", {}, {"token": token, "expires_in": 600})

    # the planted valid binding: lower() over the entry-state email
    b.call(
        "dir.lookup",
        {"token": token, "email": email_raw.lower()},
        _records(i, plant, rng),
    )
    recs = b.events[-1].output
    active = [r for r in recs if r["status"] == "active"]
    acct_id = active[0]["id"] if active else recs[0]["id"]

    if plant == "ambiguous":
        # the same id echoed by several producers pushes the slot over kappa
        b.call("acct.get", {"token": token, "acct_id": acct_id}, {"acct_id": acct_id, "id": acct_id, "ref": acct_id, "tier": "std"})
        b.call("acct.page", {"token": token, "acct_id": acct_id, "limit": 4}, {"acct_id": acct_id, "id": acct_id, "items": [1, 2]})
        return b.finish()

    b.call("acct.get", {"token": token, "acct_id": acct_id}, {"acct_id": acct_id, "tier": "std", "seats": 5})

    if plant == "literal":
        b.call("acct.page", {"token": token, "acct_id": acct_id, "limit": 4}, {"items": [1, 2, 3], "page": 0})
    elif plant == "ungroundable":
        # a value that first appears in a model response and varies per trace
        note = f"free text {rng.randrange(10**6)}"
        b.call("acct.page", {"token": token, "acct_id": acct_id, "limit": 4, "note": note}, {"items": [1]})
    elif plant == "effectful":
        b.call("notes.write", {"acct_id": acct_id, "text": "audit"}, {"ok": True})
    elif plant == "unknown_effect":
        b.call("shadow.undeclared", {"acct_id": acct_id}, {"ok": True})
    elif plant == "missing_span":
        b.call("acct.page", {"token": token, "acct_id": acct_id, "limit": 4}, None, drop_result=True)
    else:
        b.call("acct.page", {"token": token, "acct_id": acct_id, "limit": 4}, {"items": [1, 2], "page": 0})
    return b.finish()


def _records(i: int, plant: str, rng: random.Random) -> list[dict[str, Any]]:
    base = f"ac_{i:05d}"
    active = {"id": base, "status": "active", "email": f"user.{i % 97}.name@corp{i % 7}.example"}
    closed = {"id": base + "x", "status": "closed", "email": active["email"]}
    if plant == "positional":
        # the wanted record moves: `first`/`last` cannot be consistent across traces
        return [closed, active] if i % 2 else [active, closed]
    if i % 5 == 0:
        return [closed, active]
    return [active]


def write_jsonl(episodes: Iterable[Episode], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as fh:
        for ep in episodes:
            fh.write(json.dumps(ep.to_dict(), default=str) + "\n")
    return p


def read_jsonl(path: str | Path) -> list[Episode]:
    return [Episode.from_dict(json.loads(line)) for line in Path(path).read_text().splitlines() if line.strip()]


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(ROOT / "tests" / "golden_traces" / "synthetic.jsonl"))
    ap.add_argument("--episodes", type=int, default=400)
    ap.add_argument("--seed", type=int, default=5)
    args = ap.parse_args(argv)
    eps = generate(n_episodes=args.episodes, seed=args.seed)
    path = write_jsonl(eps, args.out)
    from collections import Counter

    counts = Counter(ep.attributes["plant"] for ep in eps)
    print(f"wrote {len(eps)} episodes to {path}")
    print("plants:", dict(counts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
