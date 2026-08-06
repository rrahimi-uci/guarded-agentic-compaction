"""Independent review is a hard gate for deterministic macro actions."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import jsonschema
import pytest

from guarded_agentic_compaction.benchmarking.actions import (
    ActionSpec,
    MacroApproval,
    MacroApprovalError,
    frozen_artifact_digest,
)
from guarded_agentic_compaction.benchmarking import load_case_jsonl
from benchmarks.runtime import load_domain_runtime
from paper.scripts.multidomain_study import _effect_catalog_approval_digest
from paper.scripts.prepare_macro_review import build_review_bundle


ROOT = Path(__file__).resolve().parents[2]


def _approval(**overrides) -> MacroApproval:
    values = {
        "domain": "hmda",
        "macro_version": "v1",
        "author": "author@example.org",
        "reviewer": "reviewer@example.org",
        "reviewed_at": "2026-08-04T15:00:00Z",
        "implementation_digest": "c" * 64,
        "schema_digest": "a" * 64,
        "effect_catalog_digest": "b" * 64,
        "evaluator_digest": "d" * 64,
        "approved": True,
    }
    values.update(overrides)
    return MacroApproval(**values)


def test_macro_approval_must_be_independent_and_explicit() -> None:
    assert len(_approval().digest) == 64
    with pytest.raises(MacroApprovalError, match="independent"):
        _approval(reviewer="AUTHOR@example.org").digest
    with pytest.raises(MacroApprovalError, match="not been approved"):
        _approval(approved=False).digest
    with pytest.raises(MacroApprovalError, match="timezone"):
        _approval(reviewed_at="2026-08-04T15:00:00").digest
    with pytest.raises(MacroApprovalError, match="SHA-256"):
        _approval(schema_digest="schema").digest


def test_macro_action_cannot_freeze_without_approval_digest() -> None:
    with pytest.raises(MacroApprovalError, match="approval"):
        ActionSpec(
            name="macro",
            version="v1",
            implementation_digest="implementation",
            prompt_digest="prompt",
            tool_digest="tools",
            evaluator_digest="evaluator",
            compatibility_key="family",
            metadata={},
        )


def test_frozen_artifact_digest_detects_non_policy_field_tampering() -> None:
    payload = {
        "policy": {"selected": "macro"},
        "frozen_at": "2026-08-04T15:00:00Z",
        "best_global_fixed_decision": {"selected_action": "macro"},
    }
    payload["portfolio_artifact_digest"] = frozen_artifact_digest(
        payload, digest_field="portfolio_artifact_digest"
    )
    assert payload["portfolio_artifact_digest"] == frozen_artifact_digest(
        payload, digest_field="portfolio_artifact_digest"
    )
    payload["best_global_fixed_decision"]["selected_action"] = "grc"
    assert payload["portfolio_artifact_digest"] != frozen_artifact_digest(
        payload, digest_field="portfolio_artifact_digest"
    )


def test_external_benchmark_control_schemas_are_valid_and_strict() -> None:
    approval_schema = json.loads(
        (ROOT / "benchmarks/contracts/macro-approval.schema.json").read_text()
    )
    pricing_schema = json.loads(
        (ROOT / "benchmarks/contracts/pricing.schema.json").read_text()
    )
    effort_schema = json.loads(
        (ROOT / "benchmarks/contracts/construction-effort.schema.json").read_text()
    )
    jsonschema.Draft202012Validator.check_schema(approval_schema)
    jsonschema.Draft202012Validator.check_schema(pricing_schema)
    jsonschema.Draft202012Validator.check_schema(effort_schema)
    jsonschema.validate(
        asdict(_approval(notes="independent review")),
        approval_schema,
    )
    jsonschema.validate(
        {
            "schema": "agent-compaction-pricing/v1",
            "model": "provider-model-id",
            "input_usd_per_million": 1,
            "cached_input_usd_per_million": 0.5,
            "output_usd_per_million": 2,
            "maximum_billable_input_tokens_per_request": 100000,
            "output_token_limit_per_request": 2000,
            "service_tier": "default",
            "revision": "2026-08-04",
            "source_url": "https://example.org/pricing",
            "retrieved_at": "2026-08-04T15:00:00Z",
        },
        pricing_schema,
    )


def test_generated_macro_review_template_satisfies_real_approval_schema() -> None:
    pool = ROOT / "paper/results/multidomain/preflight/hmda"
    bundle = build_review_bundle([f"hmda={pool}"])
    template = dict(bundle["domains"]["hmda"]["approval_template"])
    assert len(template["effect_catalog_digest"]) == 64
    assert len(template["evaluator_digest"]) == 64
    template.update(
        {
            "author": "author@example.org",
            "reviewer": "reviewer@example.org",
            "reviewed_at": "2026-08-04T15:00:00Z",
            "approved": True,
        }
    )
    schema = json.loads(
        (ROOT / "benchmarks/contracts/macro-approval.schema.json").read_text()
    )
    jsonschema.validate(template, schema)
    runtime = load_domain_runtime(
        domain="hmda",
        pool_dir=pool,
        cases=load_case_jsonl(pool / "cases.jsonl"),
        repository_root=ROOT,
    )
    assert template["effect_catalog_digest"] == _effect_catalog_approval_digest(runtime)
    assert len(MacroApproval(**template).digest) == 64
