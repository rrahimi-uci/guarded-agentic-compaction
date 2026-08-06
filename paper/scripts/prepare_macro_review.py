#!/usr/bin/env python3
"""Create provider-free review bundles without manufacturing human approval."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[2]
for candidate in (ROOT, ROOT / "src", Path(__file__).resolve().parent):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from guarded_agentic_compaction.benchmarking import load_case_jsonl  # noqa: E402
from benchmarks.adapters.hmda_public_lar import hmda_macro  # noqa: E402
from benchmarks.adapters.sec_filing_facts import sec_macro  # noqa: E402
from benchmarks.adapters.vulnerability_evidence import vulnerability_macro  # noqa: E402
from benchmarks.runtime import load_domain_runtime  # noqa: E402
from multidomain_study import (  # noqa: E402
    _effect_catalog_approval_digest,
    _evaluator_digest,
    _macro_implementation_digest,
    _pairs,
    _sha,
)


def build_review_bundle(pool_values: Sequence[str]) -> dict[str, Any]:
    pools = _pairs(pool_values, label="pool")
    known_domains = {"vulnerability", "sec", "hmda"}
    if not pools or not set(pools) <= known_domains:
        raise ValueError("macro review pools must name vulnerability, sec, or hmda")
    macros = {
        "vulnerability": vulnerability_macro,
        "sec": sec_macro,
        "hmda": hmda_macro,
    }
    domains: dict[str, Any] = {}
    for domain, pool in sorted(pools.items()):
        cases = load_case_jsonl(pool / "cases.jsonl")
        runtime = load_domain_runtime(
            domain=domain,
            pool_dir=pool,
            cases=cases,
            repository_root=ROOT,
        )
        results = [
            runtime.evaluate(
                case,
                macros[domain](case, runtime.facade),
                [runtime.macro_tool_name],
                action="macro",
            )
            for case in cases
        ]
        pool_report = json.loads(
            (pool / "report.json").read_text(encoding="utf-8")
        )
        gold_construction = pool_report.get("gold_construction")
        if not isinstance(gold_construction, dict) or (
            gold_construction.get("independent_from_macro") is not True
        ):
            raise ValueError(
                f"{domain} pool lacks independently constructed gold evidence"
            )
        schema_name = {
            "vulnerability": "vulnerability.schema.json",
            "sec": "sec_fact.schema.json",
            "hmda": "hmda_record.schema.json",
        }[domain]
        adapter_name = {
            "vulnerability": "vulnerability_evidence.py",
            "sec": "sec_filing_facts.py",
            "hmda": "hmda_public_lar.py",
        }[domain]
        implementation_digest = _macro_implementation_digest(domain)
        domains[domain] = {
            "cases": len(cases),
            "independent_groups": len({case.group_id for case in cases}),
            "exact_independent_gold_passes": sum(result.passed for result in results),
            "gold_construction": gold_construction,
            "review_warning": (
                "Provider-free exact agreement uses a separately implemented, checksum-bound "
                "gold constructor, but it is not independent human review. The named reviewer "
                "must inspect the macro, gold implementation, schema, effect contract, and "
                "retained real-record outputs before signing."
            ),
            "implementation_digest": implementation_digest,
            "schema_digest": _sha(ROOT / "benchmarks/contracts" / schema_name),
            "effect_catalog_digest": _effect_catalog_approval_digest(runtime),
            "prompt_digest": hashlib.sha256(runtime.prompt.encode("utf-8")).hexdigest(),
            "retained_artifact_sha256": {
                name: _sha(pool / name)
                for name in ("cases.jsonl", "gold.jsonl", "snapshot.json", "report.json")
            },
            "code_paths": [
                "benchmarks/runtime.py",
                f"benchmarks/adapters/{adapter_name}",
                "benchmarks/gold.py",
                f"benchmarks/contracts/{schema_name}",
                "benchmarks/oracles.py",
            ],
            "approval_template": {
                "domain": domain,
                "macro_version": "v1",
                "author": "",
                "reviewer": "",
                "reviewed_at": "",
                "implementation_digest": implementation_digest,
                "schema_digest": _sha(ROOT / "benchmarks/contracts" / schema_name),
                "effect_catalog_digest": _effect_catalog_approval_digest(runtime),
                "evaluator_digest": _evaluator_digest(domain, runtime),
                "approved": False,
                "notes": "",
            },
        }
    return {
        "schema": "agent-compaction-macro-review-bundle/v1",
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "provider_calls_executed": 0,
        "approval_generated": False,
        "unavailable_domains": sorted(known_domains - set(pools)),
        "domains": domains,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pool", action="append", required=True, metavar="DOMAIN=DIR")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    payload = build_review_bundle(args.pool)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "review_bundle": str(args.out),
                "provider_calls_executed": 0,
                "approval_generated": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
