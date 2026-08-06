#!/usr/bin/env python3
"""Freeze baseline, GRC, and reviewed-macro identities before portfolio calibration."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[2]
for candidate in (ROOT, ROOT / "src", Path(__file__).resolve().parent):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from guarded_agentic_compaction.benchmarking import FrozenProtocol  # noqa: E402
from guarded_agentic_compaction.registry.store import Registry  # noqa: E402
from guarded_agentic_compaction.schema.artifacts import Lifecycle  # noqa: E402
from benchmarks.runtime import load_domain_runtime  # noqa: E402
from multidomain_study import (  # noqa: E402
    ACTIONS,
    _approval,
    _build_action_spec,
    _canonical,
    _cases,
    _control_plane_digest,
    _pairs,
    _pricing,
)


def freeze_actions(args: argparse.Namespace) -> dict[str, Any]:
    protocol = FrozenProtocol.load(args.protocol)
    pricing = _pricing(args.pricing, args.model)
    expected_contract = {
        "model": args.model,
        "pricing_digest": pricing["sha256"],
        "pricing_revision": str(pricing["revision"]),
        "service_tier": str(pricing["service_tier"]),
        "maximum_billable_input_tokens_per_request": str(
            pricing["maximum_billable_input_tokens_per_request"]
        ),
        "output_token_limit_per_request": str(
            pricing["output_token_limit_per_request"]
        ),
        "openai_agents_version": version("openai-agents"),
        "openai_version": version("openai"),
    }
    if protocol.model != args.model or dict(protocol.execution_contract) != expected_contract:
        raise ValueError("model/pricing/SDK identity differs from the frozen protocol")
    cases = _cases(args.cases)
    pools = _pairs(args.pool, label="pool")
    registry_paths = _pairs(args.registry, label="registry")
    approval_paths = _pairs(args.macro_approval, label="macro approval")
    if set(cases) != set(protocol.group_roles) or set(pools) != set(cases):
        raise ValueError("protocol, case, and pool domains differ")
    specs: dict[str, dict[str, Any]] = {}
    unavailable: list[dict[str, str]] = []
    grc_stage = Lifecycle(args.grc_stage)
    for domain in sorted(cases):
        runtime = load_domain_runtime(
            domain=domain,
            pool_dir=pools[domain],
            cases=cases[domain],
            repository_root=ROOT,
        )
        registry = Registry.load(registry_paths[domain])
        approval = _approval(
            approval_paths[domain],
            domain=domain,
            runtime=runtime,
            repository_root=ROOT,
        )
        if not any(artifact.lifecycle is grc_stage for artifact in registry.artifacts):
            unavailable.append(
                {
                    "domain": domain,
                    "action": "grc",
                    "reason": f"registry_contains_no_{grc_stage.value}_artifacts",
                }
            )
        specs[domain] = {}
        for action in ACTIONS:
            spec = _build_action_spec(
                domain=domain,
                action=action,
                protocol=protocol,
                runtime=runtime,
                model_name=args.model,
                registry=registry if action == "grc" else None,
                approval=approval if action == "macro" else None,
                grc_stage=grc_stage.value if action == "grc" else None,
            )
            specs[domain][action] = {**asdict(spec), "action_digest": spec.digest}
    payload = {
        "schema": "agent-compaction-frozen-actions/v1",
        "frozen_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "protocol_digest": protocol.digest,
        "pricing_digest": pricing["sha256"],
        "model": args.model,
        "grc_stage": grc_stage.value,
        "control_plane_digest": _control_plane_digest(),
        "actions": specs,
        "unavailable_actions": unavailable,
        "provider_calls_executed": 0,
    }
    payload["action_lock_digest"] = hashlib.sha256(
        _canonical(payload).encode("utf-8")
    ).hexdigest()
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--cases", action="append", required=True, metavar="DOMAIN=JSONL")
    parser.add_argument("--pool", action="append", required=True, metavar="DOMAIN=DIR")
    parser.add_argument("--model", required=True)
    parser.add_argument("--pricing", required=True, type=Path)
    parser.add_argument("--grc-stage", required=True, choices=("shadow", "active"))
    parser.add_argument("--registry", action="append", required=True, metavar="DOMAIN=DIR")
    parser.add_argument(
        "--macro-approval", action="append", required=True, metavar="DOMAIN=JSON"
    )
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = freeze_actions(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "frozen": True,
                "path": str(args.out),
                "action_lock_digest": payload["action_lock_digest"],
                "unavailable_actions": payload["unavailable_actions"],
                "provider_calls_executed": 0,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
