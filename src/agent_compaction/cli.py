"""Command line interface. A CLI first; a control-plane service only when several
teams need one (execution-plan §10.3).

::

    agent-compaction validate-catalog configs/effects.example.yaml
    agent-compaction quality   traces.jsonl --effects configs/effects.example.yaml
    agent-compaction estimate  traces.jsonl --effects ... --entry channel locale
    agent-compaction compile   traces.jsonl --effects ... --out artifacts/v1
    agent-compaction explain   artifacts/v1
    agent-compaction diff      artifacts/v1 artifacts/v2
    agent-compaction promote   artifacts/v1 --stage shadow --approved-by me@example
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence

from .capture.mlflow_adapter import read_jsonl
from .evaluation.splits import make_splits
from .estimate.headroom import estimate
from .graph.normalize import data_quality
from .grc.compile import GrcConfig, compile_grc_batch
from .registry.lifecycle import promote
from .registry.store import Registry
from .schema.artifacts import Lifecycle
from .schema.effects import EffectCatalog

__all__ = ["main"]


def _load(path: str) -> list[Any]:
    episodes = read_jsonl(path)
    if not episodes:
        raise SystemExit(f"no episodes in {path}")
    return episodes


def _catalog(path: str | None) -> EffectCatalog:
    if not path:
        # An empty catalog is a valid input and a useful one: everything is UNKNOWN,
        # nothing compiles, and the estimator reports exactly what declaring the top
        # tools would buy.
        return EffectCatalog.from_dict({"version": 1, "name": "empty", "tools": {}})
    return EffectCatalog.from_yaml(path)


def cmd_validate_catalog(args: argparse.Namespace) -> int:
    cat = _catalog(args.catalog)
    tools = args.tools or sorted(cat.tools)
    report = cat.validate_coverage(tools)
    print(f"catalog {cat.catalog_version}")
    print(f"  declared tools     {len(cat.tools)}")
    print(f"  coverage           {report['coverage']:.3f}")
    print(f"  undeclared         {report['undeclared'] or '-'}")
    print(f"  compilable         {report['compilable'] or '-'}")
    for tool, reason in sorted(report["blocked"].items()):
        print(f"  blocked {tool:38s} {reason}")
    return 0 if not report["undeclared"] else 1


def cmd_quality(args: argparse.Namespace) -> int:
    episodes = _load(args.traces)
    print(data_quality(episodes, _catalog(args.catalog)).render())
    return 0


def cmd_estimate(args: argparse.Namespace) -> int:
    episodes = _load(args.traces)
    rep = estimate(
        episodes,
        _catalog(args.catalog),
        entry_schema=args.entry or (),
        target_delta=args.target,
        kappa=args.kappa,
        max_depth=args.depth,
        alpha=args.alpha,
        snapshot_id=args.traces,
    )
    print(rep.render())
    if args.json:
        Path(args.json).write_text(json.dumps(rep.as_dict(), indent=2, default=str))
    return 0 if rep.feasible else 2


def cmd_compile(args: argparse.Namespace) -> int:
    episodes = _load(args.traces)
    catalog = _catalog(args.catalog)
    splits = make_splits(episodes, seed=args.seed)
    cfg = GrcConfig(
        entry_schema=tuple(args.entry or ()),
        partition_by=tuple(args.partition_by),
        max_transform_depth=args.depth,
        kappa=args.kappa,
        alpha=args.alpha,
        s_min=args.min_support,
        w_max=args.max_region,
        mode=args.mode,
        owner=args.owner,
        seed=args.seed,
        allow_legacy_catalog_version=args.allow_legacy_catalog_version,
    )
    batch = compile_grc_batch(episodes, catalog, splits, cfg)
    artifacts = []
    for compatibility_key, res in batch.items():
        print(f"manifest {compatibility_key} ({len(res.graphs)} episodes)")
        print(res.report())
        print()
        print(res.explain())
        artifacts.extend(res.artifacts)
    if args.out:
        reg = Registry(name=Path(args.out).name)
        reg.extend(artifacts)
        path = reg.save(args.out)
        print(f"\nwrote {path}")
    return 0 if artifacts else 3


def cmd_explain(args: argparse.Namespace) -> int:
    reg = Registry.load(args.registry)
    print(reg.report())
    print()
    print(reg.explain())
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    a, b = Registry.load(args.old), Registry.load(args.new)
    diff = b.diff(a)
    print(json.dumps(diff, indent=2))
    return 0 if not diff["lost"] else 1


def cmd_promote(args: argparse.Namespace) -> int:
    signing_key = os.environ.get(args.signing_key_env, "").encode()
    reg = Registry.load(args.registry, signing_key=signing_key)
    if any(artifact.signature for artifact in reg.artifacts) and not signing_key:
        raise SystemExit(
            "registry contains signed artifacts; set the environment variable named "
            f"by --signing-key-env ({args.signing_key_env}) before promotion"
        )
    stage = Lifecycle(args.stage)
    for art in reg.artifacts:
        promote(
            art,
            stage,
            approved_by=args.approved_by,
            job_identity=args.job_identity,
            evaluation_split=args.evaluation_split,
            expiry_day=args.expiry,
        )
        print(f"{art.artifact_id} -> {art.lifecycle.value}")
    reg.save(args.registry)
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="agent-compaction", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    vc = sub.add_parser("validate-catalog", help="CI validator for an effect catalog")
    vc.add_argument("catalog")
    vc.add_argument("--tools", nargs="*")
    vc.set_defaults(func=cmd_validate_catalog)

    q = sub.add_parser("quality", help="data-quality / Gate 0 report")
    q.add_argument("traces")
    q.add_argument("--effects", dest="catalog")
    q.set_defaults(func=cmd_quality)

    es = sub.add_parser("estimate", help="Eq. (10) feasibility before any compiler runs")
    es.add_argument("traces")
    es.add_argument("--effects", dest="catalog")
    es.add_argument("--entry", nargs="*", help="allowlisted entry-state paths")
    es.add_argument("--target", type=float, default=0.10)
    es.add_argument("--kappa", type=int, default=3)
    es.add_argument("--depth", type=int, default=2)
    es.add_argument("--alpha", type=float, default=0.05)
    es.add_argument("--json")
    es.set_defaults(func=cmd_estimate)

    c = sub.add_parser("compile", help="mine, synthesize, contract, calibrate, emit")
    c.add_argument("traces")
    c.add_argument("--effects", dest="catalog")
    c.add_argument("--entry", nargs="*")
    c.add_argument("--partition-by", nargs="*", default=["tenant_partition", "principal", "policy_version"])
    c.add_argument("--depth", type=int, default=2)
    c.add_argument("--kappa", type=int, default=3)
    c.add_argument("--alpha", type=float, default=0.05)
    c.add_argument("--min-support", type=int, default=5)
    c.add_argument("--max-region", type=int, default=8)
    c.add_argument("--mode", choices=("offline", "replay", "shadow", "live"), default="offline")
    c.add_argument("--owner", default="unassigned")
    c.add_argument("--seed", type=int, default=20260801)
    c.add_argument(
        "--allow-legacy-catalog-version",
        action="store_true",
        help="accept a digest-free name@version manifest during migration",
    )
    c.add_argument("--out")
    c.set_defaults(func=cmd_compile)

    ex = sub.add_parser("explain", help="print a registry and every artifact's program")
    ex.add_argument("registry")
    ex.set_defaults(func=cmd_explain)

    df = sub.add_parser("diff", help="registry diff for the CI story (§6.4)")
    df.add_argument("old")
    df.add_argument("new")
    df.set_defaults(func=cmd_diff)

    pr = sub.add_parser("promote", help="advance a registry one lifecycle stage")
    pr.add_argument("registry")
    pr.add_argument("--stage", default="shadow")
    pr.add_argument("--approved-by", default="")
    pr.add_argument("--job-identity", default="optimizer")
    pr.add_argument("--evaluation-split", default="dev")
    pr.add_argument("--expiry")
    pr.add_argument(
        "--signing-key-env",
        default="AGENT_COMPACTION_SIGNING_KEY",
        help="environment variable containing the registry HMAC key",
    )
    pr.set_defaults(func=cmd_promote)
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
