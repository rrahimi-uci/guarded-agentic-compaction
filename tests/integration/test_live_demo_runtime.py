from __future__ import annotations

import asyncio
import json

from guarded_agentic_compaction.runtime.model_provider import CompactingModel
from demos.live_runtime import build_live_catalog, make_function_tools, safe_tool_name
from demos.support.world import EFFECTS_PATH, SupportWorld
from guarded_agentic_compaction.schema.effects import EffectCatalog


def test_live_tool_names_and_catalog_preserve_effect_attestations():
    world = SupportWorld()
    names = ("auth.issue_service_token", "crm.find_customer")
    tools, aliases = make_function_tools(world, names)
    source = EffectCatalog.from_yaml(EFFECTS_PATH)
    catalog = build_live_catalog(source, names, name="support-live-test")

    assert [tool.name for tool in tools] == ["auth_issue_service_token", "crm_find_customer"]
    assert aliases["crm_find_customer"] == "crm.find_customer"
    assert catalog.compilable("auth_issue_service_token")
    assert catalog.compilable("crm_find_customer")
    assert safe_tool_name("namespace.operation/read") == "namespace_operation_read"


def test_live_function_tool_outputs_json_for_compiled_dependency_replay():
    world = SupportWorld()
    tools, _ = make_function_tools(world, ("auth.issue_service_token",))
    raw = asyncio.run(tools[0].on_invoke_tool(None, "{}"))
    result = json.loads(raw)
    assert result["token"].startswith("svc_")
    assert result["scope"] == "support.read"


def test_compacting_model_is_a_real_agents_sdk_model_when_extra_is_installed():
    from agents.models.interface import Model

    assert issubclass(CompactingModel, Model)
