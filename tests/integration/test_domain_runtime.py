from __future__ import annotations

from pathlib import Path

from agent_compaction.benchmarking import load_case_jsonl
from benchmarks.runtime import PROMPTS, load_domain_runtime
from benchmarks.adapters.hmda_public_lar import hmda_macro
from benchmarks.adapters.vulnerability_evidence import vulnerability_macro


ROOT = Path(__file__).resolve().parents[2]


def _runtime(domain: str):
    pool = ROOT / f"paper/results/multidomain/preflight/{domain}"
    cases = load_case_jsonl(pool / "cases.jsonl")
    return load_domain_runtime(domain=domain, pool_dir=pool, cases=cases, repository_root=ROOT)


def test_runtime_prompts_do_not_prescribe_tool_order_or_regulated_decisions() -> None:
    for domain, prompt in PROMPTS.items():
        assert "exact order" not in prompt.casefold()
        if domain != "sec":
            assert not any(name in prompt for name in _runtime(domain).source_tool_names)
    assert "credit decision" in PROMPTS["hmda"]
    assert "investment" in PROMPTS["sec"]
    assert "remediation" in PROMPTS["vulnerability"]


def test_real_runtime_tools_and_macro_use_same_snapshot() -> None:
    for domain in ("vulnerability", "hmda"):
        runtime = _runtime(domain)
        case = next(iter(runtime.cases.values()))
        source_tools = runtime.tools("baseline", case)
        macro_tools = runtime.tools("macro", case)
        assert {tool.name for tool in source_tools} == runtime.source_tool_names
        assert [tool.name for tool in macro_tools] == [runtime.macro_tool_name]
        assert runtime.catalog("baseline").catalog_version != runtime.catalog("macro").catalog_version


def test_runtime_combines_exact_oracle_and_tool_contract() -> None:
    for domain, macro in (
        ("vulnerability", vulnerability_macro),
        ("hmda", hmda_macro),
    ):
        runtime = _runtime(domain)
        case = next(iter(runtime.cases.values()))
        output = macro(case, runtime.facade)
        assert runtime.evaluate(
            case, output, [runtime.macro_tool_name], action="macro"
        ).passed
        wrong_path = runtime.evaluate(case, output, [], action="macro")
        assert not wrong_path.passed
        assert "tool_contract" in wrong_path.failed_fields


def test_source_tool_contract_requires_complete_evidence_path() -> None:
    for domain, macro in (
        ("vulnerability", vulnerability_macro),
        ("hmda", hmda_macro),
    ):
        runtime = _runtime(domain)
        case = next(iter(runtime.cases.values()))
        output = macro(case, runtime.facade)
        required = runtime._required_source_tools(case)
        # sorted(), not next(iter(...)): picking an arbitrary set element makes the
        # assertion depend on PYTHONHASHSEED, which made this test fail intermittently.
        partial = runtime.evaluate(
            case, output, [sorted(required)[0]], action="baseline"
        )
        assert not partial.passed
        assert partial.metadata["required_tools"] == tuple(sorted(required))
        complete = runtime.evaluate(
            case, output, sorted(required), action="baseline"
        )
        assert complete.passed
        wrong_arguments = runtime.evaluate(
            case,
            output,
            sorted(required),
            action="baseline",
            tool_calls=[
                {"name": name, "input": {"snapshot_digest": "sha256:" + "0" * 64}}
                for name in required
            ],
        )
        assert not wrong_arguments.passed
        assert wrong_arguments.metadata["tool_arguments_checked"] is True
