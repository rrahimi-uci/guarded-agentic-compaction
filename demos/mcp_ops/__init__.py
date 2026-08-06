"""Demo D — multi-tenant MCP operations: the explicit negative control.

execution-plan §12.4 names the multi-tenant MCP case a *likely negative control*
because hard partitioning may leave too few groups, and use-cases §5's verdict is "do
not build the compiler; ship the estimator and stop". This demo reproduces that
outcome rather than asserting it:

* the same tool surface as Demo A, but served to **four tenants** from one deployment;
* an effect catalog in which only two of eight tools are declared, because in an MCP
  deployment discovery gives schemas, not effects — 55 of 61 tools undeclared is the
  documented starting point;
* ``tenant_partition`` is an exact guard key, so support is counted *within* a tenant
  and the corpus is divided four ways before anything is compiled.

The expected result is a correct refusal: a low ceiling, most windows blocked by
``UNKNOWN``, and no artifact. A system that compiled this workload would be wrong.
"""

from pathlib import Path

from demos.support.world import (
    ALL_TOOLS,
    ENTRY_ALLOWLIST,
    PROMPT_BLOCKS,
    TENANTS,
    SupportPolicy,
    SupportWorld,
)
from demos.support.world import MANIFEST as _SUPPORT_MANIFEST
from demos.support.world import build_workload as _support_workload
from guarded_agentic_compaction.schema.traces import ExecutionManifest
from guarded_agentic_compaction.schema.effects import EffectCatalog

EFFECTS_PATH = Path(__file__).with_name("effects.yaml")

MANIFEST = ExecutionManifest(
    manifest_id="mcp-m1",
    commit="demo-d",
    model=_SUPPORT_MANIFEST.model,
    prompt_hash="#mcp1",
    tools_hash="#mcp2",
    policy_hash="#mcp3",
    guardrail_hash="#0004",
    effect_catalog_version=EffectCatalog.from_yaml(EFFECTS_PATH).catalog_version,
    entry_contract_version="form_v3",
    sdk_version="sim-0.4.0",
    tracer_version="agent-compaction/0.5.0",
)


def build_workload(*, n_episodes: int = 2500, seed: int = 71, world=None):
    """Same shape as Demo A, spread across every tenant."""

    return _support_workload(n_episodes=n_episodes, seed=seed, tenants=TENANTS, world=world)


class McpPolicy(SupportPolicy):
    name = "mcp-ops-baseline"


__all__ = [
    "ALL_TOOLS",
    "EFFECTS_PATH",
    "ENTRY_ALLOWLIST",
    "MANIFEST",
    "PROMPT_BLOCKS",
    "McpPolicy",
    "SupportWorld",
    "build_workload",
]
