#!/usr/bin/env python3
"""Compile GRC registries from frozen discovery/development baseline episodes."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[2]
for candidate in (ROOT, ROOT / "src"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from guarded_agentic_compaction.benchmarking import FrozenProtocol  # noqa: E402
from guarded_agentic_compaction.evaluation import RunLedger, Splits, assert_disjoint  # noqa: E402
from guarded_agentic_compaction.grc.compile import GrcConfig, compile_grc  # noqa: E402
from guarded_agentic_compaction.registry.lifecycle import promote  # noqa: E402
from guarded_agentic_compaction.registry.store import Registry  # noqa: E402
from guarded_agentic_compaction.schema.artifacts import Lifecycle  # noqa: E402
from guarded_agentic_compaction.schema.effects import EffectCatalog  # noqa: E402
from guarded_agentic_compaction.schema.traces import Episode  # noqa: E402


def _ledger_args(values: Sequence[str]) -> dict[str, list[Path]]:
    result: dict[str, list[Path]] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("ledger must use DOMAIN=PATH")
        domain, path = value.split("=", 1)
        result.setdefault(domain, []).append(Path(path))
    return result


def _episode_path(payload: dict[str, Any]) -> Path:
    raw = Path(str(payload["episode_path"]))
    if raw.is_absolute():
        raise ValueError("episode_path must be repository-relative")
    resolved = (ROOT / raw).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError("episode_path escapes the repository") from exc
    if hashlib.sha256(resolved.read_bytes()).hexdigest() != payload["episode_digest"]:
        raise ValueError("retained episode digest mismatch")
    return resolved


def _episodes(
    paths: Sequence[Path], domain: str, protocol_digest: str
) -> list[Episode]:
    result: list[Episode] = []
    seen: set[str] = set()
    seen_groups: set[str] = set()
    for path in paths:
        for record in RunLedger(path).records():
            if record.run_id != protocol_digest:
                raise ValueError("ledger run does not match the frozen protocol")
            if record.event_type != "execution_complete":
                continue
            schedule = record.payload["schedule"]
            if schedule["domain"] != domain or schedule["action"] != "baseline":
                continue
            episode_path = _episode_path(dict(record.payload))
            episode = Episode.from_dict(json.loads(episode_path.read_text(encoding="utf-8")))
            if (
                episode.episode_id != record.event_id
                or episode.group_id != schedule["group_id"]
                or episode.attributes.get("domain") != domain
                or episode.attributes.get("action") != "baseline"
                or episode.attributes.get("provider_backed") is not True
                or episode.attributes.get("real_public_record") is not True
                or episode.attributes.get("local_snapshot_tools") is not True
            ):
                raise ValueError(
                    "retained episode identity or real-provider attestation differs "
                    "from its baseline ledger record"
                )
            if episode.episode_id in seen:
                raise ValueError(f"duplicate retained episode {episode.episode_id!r}")
            if episode.group_id in seen_groups:
                raise ValueError(
                    f"duplicate retained baseline group {episode.group_id!r}"
                )
            seen.add(episode.episode_id)
            seen_groups.add(episode.group_id)
            result.append(episode)
    return result


def _split(protocol: FrozenProtocol, domain: str, episodes: Sequence[Episode]) -> Splits:
    roles = protocol.group_roles[domain]
    unknown = sorted({episode.group_id for episode in episodes if episode.group_id not in roles})
    if unknown:
        raise ValueError(f"{domain} episodes contain groups outside the frozen protocol")
    discovery = sorted(
        {ep.group_id for ep in episodes if roles[ep.group_id].value == "discovery"}
    )
    development = sorted(
        {ep.group_id for ep in episodes if roles[ep.group_id].value == "development"},
        key=lambda group: hashlib.sha256(
            f"{protocol.seed}:{domain}:grc-development:{group}".encode()
        ).hexdigest(),
    )
    cut = len(development) // 2
    result = Splits(
        train=frozenset(discovery),
        dev=frozenset(development[:cut]),
        calibration=frozenset(development[cut:]),
        seed=protocol.seed,
    )
    assert_disjoint(result)
    if len(result.train) != 40 or len(result.dev) < 15 or len(result.calibration) < 15:
        raise ValueError(
            f"{domain} requires 40 discovery and 30 development groups; got {result.manifest()['sizes']}"
        )
    return result


def compile_domain(
    *, domain: str, protocol: FrozenProtocol, ledger_paths: Sequence[Path], out: Path
) -> dict[str, Any]:
    episodes = _episodes(ledger_paths, domain, protocol.digest)
    splits = _split(protocol, domain, episodes)
    eligible = [
        episode
        for episode in episodes
        if episode.group_id in splits.train | splits.dev | splits.calibration
    ]
    manifests = {episode.manifest.compatibility_key() for episode in eligible}
    if len(manifests) != 1:
        raise ValueError(f"{domain} baseline episodes have {len(manifests)} compatibility keys")
    catalog = EffectCatalog.from_yaml(ROOT / f"benchmarks/contracts/effects/{domain}.yaml")
    entry_schema = tuple(sorted({key for episode in eligible for key in episode.entry_state}))
    config = GrcConfig(
        entry_schema=entry_schema,
        partition_by=(),
        s_min=5,
        min_principals=1,
        min_days=1,
        alpha=0.01,
        delta=0.10,
        phi_min=0.02,
        mode="offline",
        owner="multidomain-study",
        seed=protocol.seed,
    )
    compiled = compile_grc(eligible, catalog, splits, eligible[0].manifest, config)
    registry = Registry(
        name=f"multidomain-{domain}-grc",
        active_stages=(Lifecycle.SHADOW,),
    )
    for artifact in compiled.artifacts:
        promote(
            artifact,
            Lifecycle.SHADOW,
            approved_by="",
            job_identity="multidomain-optimizer",
            evaluation_split="development",
        )
        registry.add(artifact)
    registry_path = registry.save(out / domain)
    report = {
        "schema": "agent-compaction-multidomain-grc-compile/v1",
        "domain": domain,
        "protocol_digest": protocol.digest,
        "compatibility_key": next(iter(manifests)),
        "split": splits.manifest(),
        "episodes": len(eligible),
        "entry_schema": list(entry_schema),
        "artifact_count": len(compiled.artifacts),
        "grc_available": bool(compiled.artifacts),
        "candidate_count": len(compiled.candidates),
        "rejections": dict(compiled.rejection_by_stage),
        "candidates": [candidate.as_dict() for candidate in compiled.candidates],
        "registry_path": str(registry_path.relative_to(ROOT)),
        "registry_stage": "shadow",
        "provider_calls_executed": 0,
        "notes": "Compilation reuses retained real provider traces; it makes no new provider calls.",
    }
    (out / domain / "compile-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--ledger", action="append", required=True, metavar="DOMAIN=PATH")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    protocol = FrozenProtocol.load(args.protocol)
    ledgers = _ledger_args(args.ledger)
    reports = [
        compile_domain(
            domain=domain, protocol=protocol, ledger_paths=ledgers[domain], out=args.out
        )
        for domain in sorted(protocol.group_roles)
    ]
    print(json.dumps(reports, indent=2, sort_keys=True))
    # No admissible artifact is a valid, explicit negative result. The emitted
    # empty shadow registry lets later phases record GRC as unavailable.
    return 0 if reports else 2


if __name__ == "__main__":
    raise SystemExit(main())
