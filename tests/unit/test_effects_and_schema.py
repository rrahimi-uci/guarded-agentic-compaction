"""Effect catalog and schema invariants (execution-plan WP1, WP2)."""

from __future__ import annotations

import json

import pytest

from agent_compaction.paths import content_digest, flatten, resolve_path
from agent_compaction.schema.artifacts import (
    Artifact,
    Gate,
    GuardClause,
    HardGuard,
    Hull,
    Lifecycle,
    OutputClause,
    Verifier,
)
from agent_compaction.schema.effects import Capability, EffectCatalog, EffectClass
from agent_compaction.schema.traces import Episode, EventKind, EventNode, ExecutionManifest, TraceEnvelope

import demos.support as support


# ---------------------------------------------------------------------------
# effect catalog
# ---------------------------------------------------------------------------


def test_unlisted_tool_is_unknown_and_never_compilable():
    cat = EffectCatalog.from_dict({"version": 1, "tools": {}})
    spec = cat.get("anything.at.all")
    assert spec.effect is EffectClass.UNKNOWN
    assert not spec.compilable
    assert spec.block_reason() == "UNKNOWN_EFFECT"


def test_read_without_both_precommit_capabilities_is_blocked():
    cat = EffectCatalog.from_dict(
        {
            "version": 1,
            "tools": {
                "r.only_spec": {"effect": "READ_EXTERNAL", "capabilities": ["speculatable"]},
                "r.both": {"effect": "READ_EXTERNAL", "capabilities": ["speculatable", "replayable"]},
            },
        }
    )
    assert not cat.compilable("r.only_spec")
    assert "MISSING_CAPABILITY" in cat.get("r.only_spec").block_reason()
    assert cat.compilable("r.both")


def test_approval_required_is_never_compilable_even_when_read_like():
    cat = EffectCatalog.from_dict(
        {
            "version": 1,
            "tools": {
                "a.req": {
                    "effect": "READ_LOCAL",
                    "capabilities": ["speculatable", "replayable"],
                    "approval_required": True,
                }
            },
        }
    )
    assert not cat.compilable("a.req")
    assert cat.get("a.req").block_reason() == "APPROVAL_BARRIER"


def test_demo_catalogs_declare_every_write_and_leave_the_nondeterministic_tool_unknown():
    cat = EffectCatalog.from_yaml(support.EFFECTS_PATH)
    assert cat.get("crm.update_ticket").effect is EffectClass.WRITE_IRREVERSIBLE
    assert cat.get("refunds.issue").effect is EffectClass.WRITE_IRREVERSIBLE
    # kb.search is deliberately absent: non-deterministic ranking cannot replay
    assert cat.get("kb.search").effect is EffectClass.UNKNOWN
    assert cat.compilable("crm.find_customer")
    assert "limit" in cat.literal_only_paths("billing.list_invoices")


def test_catalog_digest_changes_with_content():
    a = EffectCatalog.from_dict({"version": 1, "tools": {"t": {"effect": "READ_LOCAL"}}})
    b = EffectCatalog.from_dict({"version": 1, "tools": {"t": {"effect": "READ_EXTERNAL"}}})
    assert a.digest() != b.digest()
    assert a.catalog_version != b.catalog_version


def test_catalog_digest_is_independent_of_mapping_insertion_order():
    first = EffectCatalog.from_dict(
        {
            "version": 1,
            "tools": {
                "a": {"effect": "READ_LOCAL"},
                "b": {"effect": "READ_EXTERNAL"},
            },
        }
    )
    second = EffectCatalog.from_dict(
        {
            "tools": {
                "b": {"effect": "READ_EXTERNAL"},
                "a": {"effect": "READ_LOCAL"},
            },
            "version": 1,
        }
    )
    assert first.catalog_version == second.catalog_version


def test_catalog_version_requires_a_digest_unless_legacy_is_explicit():
    catalog = EffectCatalog.from_dict({"name": "demo", "version": 2, "tools": {}})
    assert catalog.matches_version(catalog.catalog_version)
    assert not catalog.matches_version("demo@2")
    assert catalog.matches_version("demo@2", allow_legacy=True)
    assert not catalog.matches_version("unknown", allow_legacy=True)


def test_order_edge_requires_a_shared_resource_and_a_write():
    cat = EffectCatalog.from_yaml(support.EFFECTS_PATH)
    assert cat.conflicts_on_resource("billing.list_invoices", "refunds.issue")
    assert not cat.conflicts_on_resource("billing.list_invoices", "crm.get_subscription")


def test_coverage_validator_reports_blocking_tools():
    cat = EffectCatalog.from_yaml(support.EFFECTS_PATH)
    report = cat.validate_coverage(["crm.find_customer", "kb.search", "refunds.issue"])
    assert report["undeclared"] == ["kb.search"]
    assert set(report["blocked"]) == {"kb.search", "refunds.issue"}
    assert report["compilable"] == ["crm.find_customer"]


# ---------------------------------------------------------------------------
# path helpers
# ---------------------------------------------------------------------------


def test_flatten_and_resolve_are_inverse_on_nested_payloads():
    payload = {"a": {"b": [{"c": 1}, {"c": 2}]}, "d": "x"}
    pairs = flatten(payload)
    for path, value in pairs:
        assert resolve_path(payload, path) == value
    assert ("a.b[1].c", 2) in pairs


def test_resolve_path_returns_none_on_miss_rather_than_raising():
    assert resolve_path({"a": 1}, "b.c") is None
    assert resolve_path({"a": [1]}, "a[5]") is None


def test_content_digest_is_order_insensitive_for_dicts():
    assert content_digest({"a": 1, "b": 2}) == content_digest({"b": 2, "a": 1})


# ---------------------------------------------------------------------------
# hulls, guards, verifiers
# ---------------------------------------------------------------------------


def test_hull_kinds_accept_and_reject():
    assert Hull("interval", low=1, high=3).contains(2)
    assert not Hull("interval", low=1, high=3).contains(4)
    assert Hull("enum", values=("a", "b")).contains("a")
    assert not Hull("enum", values=("a", "b")).contains("c")
    regex = Hull("regex", pattern=r"^cus_[A-Z0-9]{6}$", min_len=10, max_len=10)
    assert regex.contains("cus_AB12CD")
    assert not regex.contains("cus_short")
    assert Hull("any").contains(object())


def test_hard_guard_reports_every_violated_reason():
    guard = HardGuard(
        manifest_pins={"model": "m1"},
        isolation={"tenant_partition": "t1"},
        clauses=[GuardClause("z.area", "str", Hull("enum", values=("alpha",)))],
    )
    reasons = guard.evaluate({"area": "beta"}, {"model": "m2", "tenant_partition": "t2"})
    assert any(r.startswith("manifest:") for r in reasons)
    assert any(r.startswith("isolation:") for r in reasons)
    assert any(r.startswith("hull:") for r in reasons)
    assert guard.evaluate({"area": "alpha"}, {"model": "m1", "tenant_partition": "t1"}) == []


def test_conditional_output_clause_accepts_the_arm_where_it_is_absent():
    from agent_compaction.grc.program import Predicate

    clause = OutputClause(
        name="ent",
        type_name="dict",
        non_null=True,
        present_iff=Predicate("subs.tier", "==", "enterprise"),
    )
    env = {"subs": {"tier": "team"}}
    assert clause.check({}, env, {}) is None  # absent on the non-enterprise arm: fine
    assert clause.check({"ent": {"x": 1}}, env, {}) == "unexpected_present:ent"
    env2 = {"subs": {"tier": "enterprise"}}
    assert clause.check({}, env2, {}) == "missing:ent"


def test_verifier_rejects_effects_outside_the_allowlist():
    v = Verifier(clauses=[], allowed_effects=("READ_EXTERNAL",), call_counts=(2,))
    assert v.verify({}, {}, {}, ["READ_EXTERNAL", "READ_EXTERNAL"], 2) == []
    bad = v.verify({}, {}, {}, ["READ_EXTERNAL", "WRITE_IRREVERSIBLE"], 2)
    assert bad == ["effect:WRITE_IRREVERSIBLE"]
    assert v.verify({}, {}, {}, ["READ_EXTERNAL"], 3) == ["n_calls:3"]


# ---------------------------------------------------------------------------
# artifacts
# ---------------------------------------------------------------------------


def _artifact() -> Artifact:
    return Artifact(
        artifact_id="a1",
        name="demo.region@1",
        guard=HardGuard(manifest_pins={"model": "m1"}),
        gate=Gate(threshold=0.1),
        manifest=ExecutionManifest(manifest_id="m1"),
        compatibility_key="key-1",
    )


def test_artifact_signing_detects_tampering():
    art = _artifact()
    art.sign(b"secret")
    assert art.verify_signature(b"secret")
    art.gate.threshold = 0.9
    assert not art.verify_signature(b"secret")


def test_artifact_json_roundtrip_preserves_everything_that_matters():
    art = _artifact()
    art.sign(b"secret")
    again = Artifact.from_dict(json.loads(json.dumps(art.to_dict(), default=str)))
    assert again.artifact_id == art.artifact_id
    assert again.gate.threshold == art.gate.threshold
    assert again.verify_signature(b"secret")


def test_manifest_compatibility_key_changes_on_prompt_drift():
    m1 = ExecutionManifest(manifest_id="m", prompt_hash="#a")
    m2 = ExecutionManifest(manifest_id="m", prompt_hash="#b")
    assert m1.compatibility_key() != m2.compatibility_key()


def test_manifest_compatibility_key_has_no_delimiter_collision():
    # These two records had the same pipe-joined representation before the
    # compatibility identity switched to canonical JSON.
    m1 = ExecutionManifest(manifest_id="m", commit="a|b", model="c")
    m2 = ExecutionManifest(manifest_id="m", commit="a", model="b|c")
    assert m1.compatibility_key() != m2.compatibility_key()
