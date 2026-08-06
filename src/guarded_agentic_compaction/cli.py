"""Command line interface. A CLI first; a control-plane service only when several
teams need one (execution-plan §10.3).

::

    guarded-agentic-compaction validate-catalog configs/effects.example.yaml
    guarded-agentic-compaction quality   traces.jsonl --effects configs/effects.example.yaml
    guarded-agentic-compaction estimate  traces.jsonl --effects ... --entry channel locale
    guarded-agentic-compaction compile   traces.jsonl --effects ... --out artifacts/v1
    guarded-agentic-compaction explain   artifacts/v1
    guarded-agentic-compaction diff      artifacts/v1 artifacts/v2
    guarded-agentic-compaction promote   artifacts/v1 --stage shadow --approved-by me@example
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence

from .capture.jsonl import read_jsonl
from .evaluation.splits import make_splits
from .estimate.headroom import estimate
from .graph.normalize import data_quality
from .grc.compile import GrcConfig, compile_grc_batch
from .registry.lifecycle import promote
from .registry.store import Registry
from .schema.artifacts import Lifecycle
from .schema.effects import EffectCatalog
from .benchmarking.commands import benchmark_freeze, benchmark_preflight, benchmark_script

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
    ap = argparse.ArgumentParser(prog="guarded-agentic-compaction", description=__doc__)
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

    bench = sub.add_parser(
        "benchmark", help="prospective real-record benchmark protocol commands"
    )
    bench_sub = bench.add_subparsers(dest="benchmark_cmd", required=True)

    preflight = bench_sub.add_parser(
        "preflight", help="validate manifests, case identity, source policy, and pool size"
    )
    preflight.add_argument("manifest")
    preflight.add_argument(
        "--cases",
        action="append",
        default=[],
        metavar="DOMAIN=JSONL",
        help="normalized case pool; repeat for every domain",
    )
    preflight.add_argument("--require-source-configuration", action="store_true")
    preflight.set_defaults(func=benchmark_preflight)

    freeze = bench_sub.add_parser(
        "freeze", help="freeze deterministic group roles and lineage identities"
    )
    freeze.add_argument("manifest")
    freeze.add_argument(
        "--cases", action="append", required=True, metavar="DOMAIN=JSONL"
    )
    freeze.add_argument("--model", required=True, help="exact provider model identifier")
    freeze.add_argument(
        "--pricing", required=True, help="pinned pricing manifest for the frozen model"
    )
    freeze.add_argument("--out", required=True)
    freeze.set_defaults(func=benchmark_freeze)

    def add_live_command(name: str, phase: str, help_text: str) -> None:
        command = bench_sub.add_parser(name, help=help_text)
        command.add_argument("protocol")
        command.add_argument("--cases", action="append", required=True, metavar="DOMAIN=JSONL")
        command.add_argument("--pool", action="append", required=True, metavar="DOMAIN=DIR")
        command.add_argument("--model", required=True)
        command.add_argument("--pricing", required=True)
        command.add_argument("--max-provider-usd", required=True, type=float)
        command.add_argument("--reservation-usd-per-execution", required=True, type=float)
        command.add_argument("--max-model-requests", type=int, default=8)
        command.add_argument("--retries", type=int, default=1)
        command.add_argument("--timeout", type=float, default=120.0)
        command.add_argument("--registry", action="append", default=[], metavar="DOMAIN=DIR")
        command.add_argument("--macro-approval", action="append", default=[], metavar="DOMAIN=JSON")
        command.add_argument("--policy")
        command.add_argument("--action-lock")
        command.add_argument("--out", required=True)
        command.add_argument("--dry-run", action="store_true")

        def run_live(args: argparse.Namespace, frozen_phase: str = phase) -> int:
            forwarded = [
                "--protocol", args.protocol,
                "--phase", frozen_phase,
                "--model", args.model,
                "--pricing", args.pricing,
                "--max-provider-usd", str(args.max_provider_usd),
                "--reservation-usd-per-execution", str(args.reservation_usd_per_execution),
                "--max-model-requests", str(args.max_model_requests),
                "--retries", str(args.retries),
                "--timeout", str(args.timeout),
                "--out", args.out,
            ]
            for value in args.cases:
                forwarded.extend(("--cases", value))
            for value in args.pool:
                forwarded.extend(("--pool", value))
            for value in args.registry:
                forwarded.extend(("--registry", value))
            for value in args.macro_approval:
                forwarded.extend(("--macro-approval", value))
            if args.policy:
                forwarded.extend(("--policy", args.policy))
            if args.action_lock:
                forwarded.extend(("--action-lock", args.action_lock))
            if args.dry_run:
                forwarded.append("--dry-run")
            args.script_name = "multidomain_study.py"
            args.forwarded = forwarded
            return benchmark_script(args)

        command.set_defaults(func=run_live)

    add_live_command("pilot", "pilot", "run or dry-run the capped 12-group real-provider pilot")
    add_live_command(
        "discovery",
        "discovery",
        "run baseline on the frozen discovery groups",
    )
    add_live_command(
        "development",
        "development",
        "run baseline on the frozen development groups",
    )
    add_live_command(
        "artifact-calibration",
        "artifact-calibration",
        "run baseline and GRC on frozen artifact-calibration groups",
    )
    add_live_command(
        "portfolio-calibration",
        "portfolio-calibration",
        "run all approved actions on frozen portfolio-calibration groups",
    )
    add_live_command("test", "test", "run the frozen sealed test and repeat cohort")

    grc = bench_sub.add_parser("compile-grc", help="compile GRC from retained discovery/development traces")
    grc.add_argument("protocol")
    grc.add_argument("--ledger", action="append", required=True, metavar="DOMAIN=PATH")
    grc.add_argument("--out", required=True)

    def run_grc(args: argparse.Namespace) -> int:
        args.script_name = "compile_multidomain.py"
        args.forwarded = ["--protocol", args.protocol, "--out", args.out]
        for value in args.ledger:
            args.forwarded.extend(("--ledger", value))
        return benchmark_script(args)

    grc.set_defaults(func=run_grc)

    grc_calibration = bench_sub.add_parser(
        "calibrate-grc",
        help="calibrate shadow artifacts and emit human-approved active study registries",
    )
    grc_calibration.add_argument("protocol")
    grc_calibration.add_argument(
        "--ledger", action="append", required=True, metavar="DOMAIN=PATH"
    )
    grc_calibration.add_argument(
        "--registry", action="append", required=True, metavar="DOMAIN=PATH"
    )
    grc_calibration.add_argument("--approved-by", required=True)
    grc_calibration.add_argument("--job-identity", default="multidomain-optimizer")
    grc_calibration.add_argument("--expiry-day", required=True)
    grc_calibration.add_argument("--out", required=True)

    def run_grc_calibration(args: argparse.Namespace) -> int:
        args.script_name = "calibrate_grc_artifacts.py"
        args.forwarded = [
            "--protocol", args.protocol,
            "--approved-by", args.approved_by,
            "--job-identity", args.job_identity,
            "--expiry-day", args.expiry_day,
            "--out", args.out,
        ]
        for flag, values in (("--ledger", args.ledger), ("--registry", args.registry)):
            for value in values:
                args.forwarded.extend((flag, value))
        return benchmark_script(args)

    grc_calibration.set_defaults(func=run_grc_calibration)

    freeze_actions = bench_sub.add_parser(
        "freeze-actions",
        help="freeze action, registry, approval, prompt, tool, and evaluator identities",
    )
    freeze_actions.add_argument("protocol")
    freeze_actions.add_argument(
        "--cases", action="append", required=True, metavar="DOMAIN=JSONL"
    )
    freeze_actions.add_argument(
        "--pool", action="append", required=True, metavar="DOMAIN=DIR"
    )
    freeze_actions.add_argument("--model", required=True)
    freeze_actions.add_argument("--pricing", required=True)
    freeze_actions.add_argument(
        "--grc-stage", required=True, choices=("shadow", "active")
    )
    freeze_actions.add_argument(
        "--registry", action="append", required=True, metavar="DOMAIN=DIR"
    )
    freeze_actions.add_argument(
        "--macro-approval", action="append", required=True, metavar="DOMAIN=JSON"
    )
    freeze_actions.add_argument("--out", required=True)

    def run_freeze_actions(args: argparse.Namespace) -> int:
        args.script_name = "freeze_multidomain_actions.py"
        args.forwarded = [
            "--protocol", args.protocol,
            "--model", args.model,
            "--pricing", args.pricing,
            "--grc-stage", args.grc_stage,
            "--out", args.out,
        ]
        for flag, values in (
            ("--cases", args.cases),
            ("--pool", args.pool),
            ("--registry", args.registry),
            ("--macro-approval", args.macro_approval),
        ):
            for value in values:
                args.forwarded.extend((flag, value))
        return benchmark_script(args)

    freeze_actions.set_defaults(func=run_freeze_actions)

    macro_review = bench_sub.add_parser(
        "prepare-macro-review",
        help="create provider-free macro review materials without granting approval",
    )
    macro_review.add_argument(
        "--pool", action="append", required=True, metavar="DOMAIN=DIR"
    )
    macro_review.add_argument("--out", required=True)

    def run_macro_review(args: argparse.Namespace) -> int:
        args.script_name = "prepare_macro_review.py"
        args.forwarded = ["--out", args.out]
        for value in args.pool:
            args.forwarded.extend(("--pool", value))
        return benchmark_script(args)

    macro_review.set_defaults(func=run_macro_review)

    calibrate = bench_sub.add_parser("calibrate", help="freeze family and global portfolio decisions")
    calibrate.add_argument("protocol")
    calibrate.add_argument("--ledger", action="append", required=True)
    calibrate.add_argument("--out", required=True)

    def run_calibrate(args: argparse.Namespace) -> int:
        args.script_name = "calibrate_multidomain.py"
        args.forwarded = ["--protocol", args.protocol, "--out", args.out]
        for value in args.ledger:
            args.forwarded.extend(("--ledger", value))
        return benchmark_script(args)

    calibrate.set_defaults(func=run_calibrate)

    analyze = bench_sub.add_parser("analyze", help="reproduce sealed quality/efficiency analysis")
    analyze.add_argument("protocol")
    analyze.add_argument("--policy", required=True)
    analyze.add_argument("--effort", required=True)
    analyze.add_argument("--ledger", action="append", required=True)
    analyze.add_argument("--out", required=True)

    def run_analyze(args: argparse.Namespace) -> int:
        args.script_name = "analyze_multidomain.py"
        args.forwarded = [
            "--protocol", args.protocol, "--policy", args.policy, "--out", args.out,
            "--effort", args.effort,
        ]
        for value in args.ledger:
            args.forwarded.extend(("--ledger", value))
        return benchmark_script(args)

    analyze.set_defaults(func=run_analyze)
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
