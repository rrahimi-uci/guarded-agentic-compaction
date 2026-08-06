"""Demo registration for the experiment driver.

One place that knows, per demonstration: how to build the world and workload, which
effect catalog applies, what the baseline configuration is, how to instantiate a
policy from a (possibly pruned) configuration, and which route label TGWS should
learn. Everything else in the driver is demo-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from guarded_agentic_compaction.schema.effects import EffectCatalog
from guarded_agentic_compaction.schema.traces import Episode, ExecutionManifest
from guarded_agentic_compaction.tgws.prune import LeafConfig

import demos.fulfillment as fulfillment
import demos.incident_triage as triage
import demos.mcp_ops as mcp
import demos.permissioned_rag as rag
import demos.support as support
from demos.framework import EpisodeSpec, World


@dataclass(slots=True)
class DemoSpec:
    key: str
    title: str
    module: Any
    manifest: ExecutionManifest
    effects_path: Any
    entry_allowlist: tuple[str, ...]
    baseline_config: LeafConfig
    make_world: Callable[[], World]
    make_workload: Callable[..., tuple[World, list[EpisodeSpec]]]
    make_policy: Callable[..., Any]
    protected_tools: tuple[str, ...] = ()
    protected_blocks: tuple[str, ...] = ()
    route_label: Callable[[Episode], str] | None = None
    n_episodes: int = 2500
    macro_tool: str = ""
    notes: str = ""

    def catalog(self) -> EffectCatalog:
        return EffectCatalog.from_yaml(self.effects_path)

    def policy_from_config(self, config: LeafConfig, **kwargs: Any) -> Any:
        return self.make_policy(prompt_blocks=config.prompt_blocks, tools=config.tools, **kwargs)


def _support_spec() -> DemoSpec:
    return DemoSpec(
        key="support",
        title="Demo A — Tier-1 support evidence gathering",
        module=support,
        manifest=support.MANIFEST,
        effects_path=support.EFFECTS_PATH,
        entry_allowlist=support.ENTRY_ALLOWLIST,
        baseline_config=LeafConfig(
            agent="tier1-support",
            model=support.MANIFEST.model,
            reasoning_tier="default",
            prompt_blocks=support.world.PROMPT_BLOCKS,
            tools=support.world.ALL_TOOLS,
        ),
        make_world=lambda: support.SupportWorld(),
        make_workload=support.build_workload,
        make_policy=support.SupportPolicy,
        protected_tools=("crm.update_ticket",),
        protected_blocks=("role_tier1",),
        n_episodes=3000,
        macro_tool="support.gather_context",
        notes="reference shape: read-only evidence prefix, depth-2 entity binding, tier branch",
    )


def _rag_spec() -> DemoSpec:
    return DemoSpec(
        key="permissioned_rag",
        title="Demo B — permissioned RAG knowledge assistant",
        module=rag,
        manifest=rag.MANIFEST,
        effects_path=rag.EFFECTS_PATH,
        entry_allowlist=rag.ENTRY_ALLOWLIST,
        baseline_config=LeafConfig(
            agent="kb-assistant",
            model=rag.MANIFEST.model,
            reasoning_tier="default",
            prompt_blocks=rag.PROMPT_BLOCKS,
            tools=rag.ALL_TOOLS,
        ),
        make_world=lambda: rag.RagWorld(),
        make_workload=rag.build_workload,
        make_policy=rag.RagPolicy,
        protected_tools=("acl.check_scope",),
        protected_blocks=("acl_rules", "citation_policy"),
        n_episodes=6000,
        macro_tool="search.answer_context",
        notes="the guard is the contribution: ACL scope, index version, freshness are hard keys",
    )


def _triage_spec() -> DemoSpec:
    return DemoSpec(
        key="incident_triage",
        title="Demo C — multi-agent incident triage",
        module=triage,
        manifest=triage.MANIFEST,
        effects_path=triage.EFFECTS_PATH,
        entry_allowlist=triage.ENTRY_ALLOWLIST,
        baseline_config=LeafConfig(
            agent="coordinator",
            model=triage.MANIFEST.model,
            reasoning_tier="default",
            prompt_blocks=triage.PROMPT_BLOCKS,
            tools=triage.ALL_TOOLS,
        ),
        make_world=lambda: triage.TriageWorld(),
        make_workload=triage.build_workload,
        make_policy=triage.TriagePolicy,
        protected_tools=("approvals.request", "remediation.execute"),
        protected_blocks=("coordinator_role", "approval_policy"),
        n_episodes=3000,
        macro_tool="triage.evidence_bundle",
        notes="TGWS removes coordinator turns; a handoff is a barrier for GRC",
    )


def _mcp_spec() -> DemoSpec:
    """Demo D: the negative control. Expected outcome is a correct refusal."""

    return DemoSpec(
        key="mcp_ops",
        title="Demo D — multi-tenant MCP operations (negative control)",
        module=mcp,
        manifest=mcp.MANIFEST,
        effects_path=mcp.EFFECTS_PATH,
        entry_allowlist=mcp.ENTRY_ALLOWLIST,
        baseline_config=LeafConfig(
            agent="mcp-ops",
            model=mcp.MANIFEST.model,
            reasoning_tier="default",
            prompt_blocks=mcp.PROMPT_BLOCKS,
            tools=mcp.ALL_TOOLS,
        ),
        make_world=lambda: mcp.SupportWorld(),
        make_workload=mcp.build_workload,
        make_policy=mcp.McpPolicy,
        protected_tools=("crm.update_ticket",),
        protected_blocks=("role_tier1",),
        n_episodes=4000,
        macro_tool="support.gather_context",
        notes="a correct guard that makes the workload uneconomic: ship the estimator, "
        "do not build the compiler",
    )


def _fulfillment_spec() -> DemoSpec:
    """Demo E: the hardest shape. Branches, pagination, and a mandatory commitment."""

    return DemoSpec(
        key="fulfillment",
        title="Demo E — order-fulfillment exception handling",
        module=fulfillment,
        manifest=fulfillment.MANIFEST,
        effects_path=fulfillment.EFFECTS_PATH,
        entry_allowlist=fulfillment.ENTRY_ALLOWLIST,
        baseline_config=LeafConfig(
            agent="fulfillment-ops",
            model=fulfillment.MANIFEST.model,
            reasoning_tier="default",
            prompt_blocks=fulfillment.PROMPT_BLOCKS,
            tools=fulfillment.ALL_TOOLS,
        ),
        make_world=lambda: fulfillment.FulfillmentWorld(),
        make_workload=fulfillment.build_workload,
        make_policy=fulfillment.FulfillmentPolicy,
        protected_tools=fulfillment.PROTECTED_TOOLS,
        protected_blocks=fulfillment.PROTECTED_BLOCKS,
        route_label=_fulfillment_route_label,
        n_episodes=3000,
        macro_tool="fulfillment.evidence_bundle",
        notes="two synthesized branches, a paginated read, and a commitment that "
        "bounds every region to a prefix: partial compaction is the correct result",
    )


def _fulfillment_route_label(episode: Episode) -> str:
    """Route label for Demo E: the exception class drives the whole specialization.

    Read from the entry state rather than from the executed path so that a deviating
    episode still labels its intended route; the purity check then measures how often
    the baseline actually followed it.
    """

    case = episode.entry_state.get("case") or {}
    return "route:" + str(case.get("exception_class", "unknown"))


DEMOS: dict[str, Callable[[], DemoSpec]] = {
    "support": _support_spec,
    "permissioned_rag": _rag_spec,
    "incident_triage": _triage_spec,
    "mcp_ops": _mcp_spec,
    "fulfillment": _fulfillment_spec,
}


def get_demo(key: str) -> DemoSpec:
    if key not in DEMOS:
        raise KeyError(f"unknown demo {key}; known: {sorted(DEMOS)}")
    return DEMOS[key]()
