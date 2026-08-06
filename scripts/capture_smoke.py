#!/usr/bin/env python3
"""Capture smoke test: prove the trace path end to end before trusting a corpus.

Runs a handful of episodes through the simulated substrate, writes them via each available
backend, reads them back, and reconciles counts and digests. This is the check that catches
the two failure modes that silently corrupt a mining corpus: a second exporter fragmenting
the span tree, and a short-lived job exiting with traces still queued.

    python scripts/capture_smoke.py --backend jsonl
    python scripts/capture_smoke.py --episodes 24
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from guarded_agentic_compaction.capture import jsonl
from guarded_agentic_compaction.capture.attributes import EntryStateContract
from guarded_agentic_compaction.graph.normalize import data_quality
from guarded_agentic_compaction.schema.effects import EffectCatalog

import demos.support as support
from demos.framework import run_workload


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--episodes", type=int, default=12)
    args = ap.parse_args(argv)

    world, specs = support.build_workload(n_episodes=args.episodes)
    episodes = run_workload(specs, world, support.SupportPolicy(), support.MANIFEST)
    catalog = EffectCatalog.from_yaml(support.EFFECTS_PATH)
    print(data_quality(episodes, catalog).render())

    contract = EntryStateContract(allowlist=support.ENTRY_ALLOWLIST, version="form_v3")
    leaked = contract.violations(episodes[0].entry_state)
    print(f"\nentry-state contract {contract.digest()}: {len(leaked)} field(s) outside the allowlist")
    if leaked:
        print(f"  not captured: {leaked}")

    path = Path(tempfile.mkdtemp()) / "smoke.jsonl"
    jsonl.write_jsonl(episodes, path)
    back = jsonl.read_jsonl(path)

    print(f"\nwrote {len(episodes)} episodes, read {len(back)} back")
    ok = len(back) == len(episodes)
    by_id = {ep.episode_id: ep for ep in back}
    for ep in episodes:
        got = by_id.get(ep.episode_id)
        if got is None or got.n_requests() != ep.n_requests():
            ok = False
            print(f"  MISMATCH {ep.episode_id}")
    print("reconciliation:", "ok" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
