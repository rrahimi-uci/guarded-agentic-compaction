#!/usr/bin/env python3
"""Fail-closed integrity and claim audit for the publication artifact."""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
import tomllib
import zipfile
from collections import Counter, defaultdict
from itertools import permutations
from pathlib import Path
from types import SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"
errors: list[str] = []
checks: list[str] = []


def ok(condition: bool, message: str) -> None:
    (checks if condition else errors).append(message)


def load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"load {path.relative_to(ROOT)}: {exc}")
        return {}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def evidence_equal(actual: Any, expected: Any) -> bool:
    """Compare retained evidence without requiring platform-identical float bits."""

    if isinstance(actual, bool) or isinstance(expected, bool):
        return actual is expected
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-12)
    if isinstance(actual, dict) and isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            evidence_equal(actual[key], expected[key]) for key in actual
        )
    if isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
        return len(actual) == len(expected) and all(
            evidence_equal(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def extract_pdf_text(path: Path) -> str:
    """Extract PDF text with Poppler when available and a Python fallback otherwise."""

    if shutil.which("pdftotext"):
        return subprocess.run(
            ["pdftotext", str(path), "-"], check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        ).stdout
    from pypdf import PdfReader

    return "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)


def validate_sources() -> None:
    nest_dir = PAPER / "results/datasets/nestful"
    nest = load(nest_dir / "source_manifest.json")
    ok(nest.get("commit") == "fc2c4123e73500a56185a5fb354f05d1c8b4890c", "NESTFUL revision pinned")
    for name, spec in nest.get("files", {}).items():
        path = nest_dir / name
        ok(path.exists(), f"NESTFUL source exists: {name}")
        if path.exists():
            ok(path.stat().st_size == spec["bytes"], f"NESTFUL byte count: {name}")
            ok(sha256(path) == spec["sha256"], f"NESTFUL checksum: {name}")

    gh_dir = PAPER / "results/datasets/github_issues"
    gh = load(gh_dir / "source_manifest.json")
    ok(gh.get("revision") == "e344be7b84d199661a9956036991e1fc25715a47", "GitHub dataset revision pinned")
    for name, key in (("train-00000-of-00001.parquet", "parquet"), ("UPSTREAM-README.md", "readme")):
        path = gh_dir / name
        spec = gh.get(key, {})
        ok(path.exists(), f"GitHub dataset source exists: {name}")
        if path.exists() and spec:
            ok(path.stat().st_size == spec["bytes"], f"GitHub byte count: {name}")
            ok(sha256(path) == spec["sha256"], f"GitHub checksum: {name}")


def validate_live() -> None:
    final = load(PAPER / "results/github_live/results.json")
    pilot = load(PAPER / "results/github_live/pilot_2026-08-03/results.json")
    if not final:
        return
    run = final["run"]
    ok(run["evidence_class"] == "real public records + deterministic snapshot tools + live OpenAI provider",
       "live evidence class is explicit")
    ok(run["openai_api_key_used"] is True, "OpenAI API key usage recorded")
    ok(run["hf_token_used_for_download"] is True, "Hugging Face token usage recorded")
    ok(run["secrets_serialized"] is False, "result declares no serialized secrets")
    ok(final.get("failures") == [], "final live run has no recorded failures")

    compiler = final["compiler"]
    gate = compiler["artifact"]["gate"]
    ok(gate["n_calibration_groups"] == 92, "gate has 92 configured calibration group records")
    ok(gate["n_accepted"] == 92 and gate["observed_violations"] == 0,
       "gate accepted 92 groups with zero observed violations")
    ok(abs(gate["risk_upper_bound"] - 0.049808920112407784) < 1e-12,
       "gate risk upper bound matches paper")
    ok(compiler["artifact"]["program"]["tools"] ==
       ["issue_get_record", "issue_get_labels", "issue_get_comments"],
       "compiled program is the reported three-tool prefix")
    ok("'non_prefix_runtime': 116" in compiler["report"],
       "116 suffix candidates were rejected")

    repeat0 = [r for r in final["results"] if r["condition"] in {"baseline", "compiled"} and r["repeat"] == 0]
    paired: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in repeat0:
        paired[row["issue_number"]][row["condition"]] = row
    ok(len(paired) == 18 and all(set(v) == {"baseline", "compiled"} for v in paired.values()),
       "18 complete held-out pairs")
    ok(all(v[c]["quality"]["overall"] for v in paired.values() for c in ("baseline", "compiled")),
       "all held-out task contracts pass")
    ok(all(v["baseline"]["metrics"]["requests"] == 4 and v["compiled"]["metrics"]["requests"] == 1
           for v in paired.values()), "every pair changes provider requests 4 to 1")
    ok(all(v["baseline"]["metrics"]["tool_calls"] == v["compiled"]["metrics"]["tool_calls"] == 3
           for v in paired.values()), "necessary tool calls remain three")

    metrics = final["paired_test"]["metrics"]
    expected = {
        "requests": 0.75,
        "total_tokens": 0.6566412841564924,
        "wall_latency_ms": 0.8495013609404082,
        "estimated_cost_usd": 0.5259976330354549,
        "tool_calls": 0.0,
    }
    for name, value in expected.items():
        ok(abs(metrics[name]["aggregate_reduction"] - value) < 1e-12, f"reported live metric: {name}")

    test_ids = {row["issue_number"] for row in final["selection"]["test"]}
    discovery_ids = set(final["selection"]["discovery_issue_numbers"])
    pilot_ids = set(pilot.get("selection", {}).get("discovery_issue_numbers", []))
    pilot_ids.update(row["issue_number"] for row in pilot.get("selection", {}).get("test", []))
    ok(test_ids.isdisjoint(discovery_ids), "final test is disjoint from final discovery")
    ok(test_ids.isdisjoint(pilot_ids), "final test is disjoint from archived pilot")
    ok(pilot["paired_test"]["quality"]["overall"]["compiled_rate"] == 1/6,
       "archived pilot retains 16.7 percent negative result")


def validate_natural_preflight() -> None:
    """Audit the prospective protocol without confusing design evidence for results."""

    path = PAPER / "results/github_natural_replication/preflight.json"
    ok(path.exists(), "natural-order live-study preflight exists")
    if not path.exists():
        return
    data = load(path)
    ok(data.get("schema") == "agent-compaction-natural-live-preflight/v1",
       "natural-order preflight schema")
    ok(data.get("status") == "designed_not_run",
       "natural-order protocol is explicitly unrun")
    ok(data.get("provider_calls_executed") == 0,
       "natural-order preflight made zero provider calls")
    ok(data.get("task_design") == "natural-extractive-v2",
       "natural-order task design recorded")

    from github_live_study import _stable_rank, prompt_for

    prompt_digest = hashlib.sha256(
        prompt_for("natural-extractive-v2").encode("utf-8")
    ).hexdigest()
    ok(data.get("prompt_sha256") == prompt_digest,
       "natural-order preflight binds the implemented prompt")

    selection = data.get("selection", {})
    discovery = [int(value) for value in selection.get("discovery_issue_numbers", [])]
    test = selection.get("test", [])
    test_ids = [int(item["issue_number"]) for item in test]
    ok(len(discovery) == 132 and len(set(discovery)) == 132,
       "natural-order design seals 132 unique discovery records")
    ok(len(test_ids) == 30 and len(set(test_ids)) == 30,
       "natural-order design seals 30 unique held-out records")
    ok(set(discovery).isdisjoint(test_ids),
       "natural-order discovery and test records are disjoint")
    category_counts: dict[str, int] = defaultdict(int)
    for item in test:
        category_counts[str(item.get("category"))] += 1
    ok(category_counts == {"bug": 10, "enhancement": 10, "question": 10},
       "natural-order held-out set is balanced across three real issue classes")

    oracle = data.get("oracle_preflight", {})
    ok(oracle.get("tool_order_prescribed") is False,
       "natural-order prompt does not prescribe tool order")
    ok(oracle.get("missing_required_source_fields") == [],
       "all natural-order records support exact factuality checks")
    ok(oracle.get("discovery_test_overlap") is False,
       "natural-order preflight independently records no split overlap")

    order = data.get("condition_order_plan", {})
    assignments = order.get("assignments", {})
    ok(order.get("method") == "balanced-six-permutation-latin-order",
       "natural-order design balances baseline, compiled, and macro order")
    ranked = sorted(
        test_ids,
        key=lambda number: _stable_rank(number, 20260802, "latin-order:0"),
    )
    latin_orders = list(permutations(("baseline", "compiled", "macro")))
    expected_assignments = {
        str(number): list(latin_orders[index % len(latin_orders)])
        for index, number in enumerate(ranked)
    }
    ok(assignments == expected_assignments,
       "natural-order condition assignment is reproducible from the sealed seed")
    observed_orders = Counter(tuple(value) for value in assignments.values())
    ok(len(observed_orders) == 6 and set(observed_orders.values()) == {5},
       "all six three-condition orders have five held-out records")

    publication = load(PAPER / "results/publication_manifest.json")
    hashed = {record.get("path") for record in publication.get("files", [])}
    ok({
        "paper/results/github_natural_replication/preflight.json",
        "paper/scripts/github_live_study.py",
        "paper/scripts/test_oracle_weakness.py",
        "paper/supplementary/natural-live-study-protocol.md",
    } <= hashed, "publication manifest hashes the prospective protocol and its tests")


def validate_natural_live() -> None:
    """Recompute the review-driven free-order study from sealed provider outputs."""

    path = PAPER / "results/github_natural_live/results.json"
    ok(path.exists(), "natural-workflow live result exists")
    if not path.exists():
        return
    data = load(path)
    run = data.get("run", {})
    ok(run.get("script") == "paper/scripts/github_natural_workflow_study.py",
       "natural-workflow result names its dedicated driver")
    ok(run.get("openai_api_key_used") is True and run.get("secrets_serialized") is False,
       "natural-workflow provider usage is recorded without serializing secrets")
    ok(run.get("workflow_prompt_prescribes_tool_names_or_order") is False,
       "natural-workflow prompt does not prescribe tool names or order")
    ok(run.get("quality_oracle_uses_tool_order") is False,
       "natural-workflow quality is independent of tool order")
    ok(run.get("counterbalanced_condition_order") is True,
       "natural-workflow run records counterbalanced condition order")
    ok(data.get("failures") == [], "natural-workflow run has no infrastructure failures")

    from github_natural_workflow_study import grade_factual
    import github_live_study as fixed

    frame = fixed.pd.read_parquet(fixed.DATA_PATH)
    store, _ = fixed.build_store(frame)
    results = data.get("results", [])
    discovery = [row for row in results if row.get("condition") == "discovery"]
    evaluation = [
        row for row in results if row.get("condition") in {"baseline", "compiled", "macro"}
    ]
    ok(len(discovery) == 80 and len(evaluation) == 54,
       "natural-workflow retains 80 discovery and 18-by-3 evaluation outputs")
    ok(len({row.get("trace_id") for row in results}) == len(results)
       and all(str(row.get("trace_id", "")).startswith("trace_") for row in results),
       "natural-workflow outputs retain unique native trace identifiers")

    recomputed: list[SimpleNamespace] = []
    quality_drift: list[tuple[str, int]] = []
    for row in results:
        number = int(row["issue_number"])
        item = store[number]
        scenario = fixed.Scenario(
            issue_number=number,
            category=fixed.category_for(item["labels"]),
            labels=tuple(item["labels"]),
            html_url=item["html_url"],
            day=item["day"],
            state=item["state"],
        )
        quality = grade_factual(
            scenario, row["answer"], row["tool_sequence"], store
        )
        if quality != row.get("quality"):
            quality_drift.append((str(row.get("condition")), number))
        recomputed.append(
            SimpleNamespace(
                condition=row["condition"],
                repeat=row["repeat"],
                issue_number=number,
                metrics=row["metrics"],
                quality=quality,
            )
        )
    ok(not quality_drift,
       f"natural-workflow exact-source oracle recomputes every row ({quality_drift})")

    aggregate = fixed.aggregate_runs(recomputed)
    ok(evidence_equal(aggregate, data.get("aggregate")),
       "natural-workflow aggregate metrics recompute from retained outputs")
    by_condition = {
        condition: [row for row in recomputed if row.condition == condition]
        for condition in ("baseline", "compiled", "macro")
    }
    base_compiled = fixed.paired_analysis(
        by_condition["baseline"], by_condition["compiled"]
    )
    base_macro = fixed.paired_analysis(
        by_condition["baseline"], by_condition["macro"]
    )
    macro_compiled = fixed.paired_analysis(
        by_condition["macro"], by_condition["compiled"]
    )
    ok(evidence_equal(base_compiled, data.get("baseline_vs_compiled")),
       "natural-workflow baseline-versus-compiler statistics recompute")
    ok(evidence_equal(base_macro, data.get("baseline_vs_macro")),
       "natural-workflow baseline-versus-macro statistics recompute")
    ok(evidence_equal(macro_compiled, data.get("macro_vs_compiled")),
       "natural-workflow macro-versus-compiler statistics recompute")

    rates = {
        name: aggregate[name]["factuality_exact_rate"]
        for name in ("baseline", "compiled", "macro")
    }
    ok(rates == {"baseline": 1, "compiled": 17 / 18, "macro": 1},
       "natural-workflow exact factual passes are 18/18, 17/18, and 18/18")
    failed = [
        (row.condition, row.issue_number)
        for row in recomputed
        if row.condition in {"baseline", "compiled", "macro"}
        and not row.quality["overall"]
    ]
    ok(failed == [("compiled", 6602)],
       "natural-workflow retains the single compiled-only exact-source failure")

    metrics = base_compiled["metrics"]
    expected_reductions = {
        "requests": 0.75,
        "total_tokens": 0.6603077427642188,
        "wall_latency_ms": 0.7638141095059023,
        "estimated_cost_usd": 0.48695065617539446,
        "tool_calls": 0.0,
    }
    for name, expected in expected_reductions.items():
        ok(abs(metrics[name]["aggregate_reduction"] - expected) < 1e-12,
           f"natural-workflow compiler reduction recomputes: {name}")

    selection = data.get("selection", {})
    discovery_ids = {int(value) for value in selection.get("discovery_issue_numbers", [])}
    test_ids = {int(row["issue_number"]) for row in selection.get("test", [])}
    ok(len(discovery_ids) == 80 and len(test_ids) == 18 and discovery_ids.isdisjoint(test_ids),
       "natural-workflow discovery and held-out selections are complete and disjoint")
    prior_ids: set[int] = set()
    for prior_path in (
        PAPER / "results/github_live/results.json",
        PAPER / "results/github_live/pilot_2026-08-03/results.json",
    ):
        prior = load(prior_path)
        prior_ids.update(int(value) for value in prior.get("selection", {}).get("discovery_issue_numbers", []))
        prior_ids.update(int(row["issue_number"]) for row in prior.get("selection", {}).get("test", []))
    ok((discovery_ids | test_ids).isdisjoint(prior_ids),
       "natural-workflow records are disjoint from both earlier live protocols")
    ok(selection.get("test_category_counts") == {"bug": 5, "enhancement": 2, "other": 11},
       "natural-workflow reports its unbalanced observed class mix")

    schedule = data.get("counterbalanced_schedule", [])
    schedule_orders = Counter(tuple(row.get("order", [])) for row in schedule)
    ok(len(schedule) == 18 and set(schedule_orders) == set(permutations(("baseline", "compiled", "macro")))
       and set(schedule_orders.values()) == {3},
       "natural-workflow balances all six condition orders across 18 records")

    compiler = data.get("compiler", {})
    splits = compiler.get("splits", {})
    ok(splits.get("sizes") == {"train": 20, "dev": 10, "calibration": 45,
                               "test": 0, "shadow": 0},
       "natural-workflow compiler split sizes are sealed")
    ok(compiler.get("selection_rule") ==
       "online overall=True under the original oracle; stable hash split; no tool-order filter",
       "natural-workflow compiler selection records its original oracle boundary")
    ok(compiler.get("observed_train_sequences") == {
        "issue_get_record -> issue_get_labels -> issue_get_comments": 20
    }, "natural-workflow train traces independently converge on one prefix")
    artifact = compiler.get("artifact", {})
    ok(artifact.get("program", {}).get("tools") ==
       ["issue_get_record", "issue_get_labels", "issue_get_comments"],
       "natural-workflow compiler emits the observed three-read prefix")
    gate = artifact.get("gate", {})
    ok(gate.get("n_calibration_groups") == gate.get("n_accepted") == 45
       and gate.get("observed_violations") == 0,
       "natural-workflow gate records 45 accepted replay groups and zero violations")
    ok(abs(float(gate.get("risk_upper_bound", 0)) - 0.09918477422824756) < 1e-12,
       "natural-workflow gate's configured upper bound recomputes")

    oracle_revision = data.get("oracle_revision", {})
    ok(oracle_revision.get("provider_calls_rerun") is False
       and oracle_revision.get("provider_outputs_changed") is False
       and len(oracle_revision.get("changed_rows", [])) == 4,
       "natural-workflow oracle correction preserves provider evidence and records four rows")
    input_effect = oracle_revision.get("compiler_input_effect", {})
    ok(input_effect.get("executed_artifact_retrained") is False
       and input_effect.get("originally_excluded_issue") == 1741
       and input_effect.get("originally_selected_replacement_issue") == 3511
       and input_effect.get("corrected_stable_rank_of_excluded_issue") == 6,
       "natural-workflow oracle correction discloses its compiler-split consequence")
    derived_revision = data.get("derived_statistics_revision", {})
    ok(derived_revision.get("provider_calls_rerun") is False
       and derived_revision.get("provider_metrics_changed") is False,
       "natural-workflow derived comparison adds no provider calls or metric changes")

    publication = load(PAPER / "results/publication_manifest.json")
    hashed = {record.get("path") for record in publication.get("files", [])}
    ok({
        "paper/results/github_natural_live/results.json",
        "paper/results/github_natural_live/smoke.json",
        "paper/results/github_natural_live/registry/registry.json",
        "paper/scripts/github_natural_workflow_study.py",
        "paper/scripts/test_natural_workflow_study.py",
    } <= hashed, "publication manifest hashes natural-workflow results, driver, and tests")


def validate_natural_replication() -> None:
    """Recompute the expanded paid replication from retained provider outputs."""

    path = PAPER / "results/github_natural_replication/results.json"
    ok(path.exists(), "expanded natural-workflow replication result exists")
    if not path.exists():
        return
    data = load(path)
    run = data.get("run", {})
    ok(run.get("evidence_class") ==
       "real public records + deterministic snapshot tools + live OpenAI provider",
       "replication records its real-record live-provider evidence class")
    ok(run.get("openai_api_key_used") is True
       and run.get("hf_token_used_for_download") is True
       and run.get("secrets_serialized") is False,
       "replication records credential use without serializing secrets")
    ok(run.get("task_design") == "natural-extractive-v2"
       and run.get("resolved_config", {}).get("include_macro") is True,
       "replication records the natural three-condition design")
    ok(data.get("failures") == [], "expanded replication has no infrastructure failures")

    import github_live_study as study

    frame = study.pd.read_parquet(study.DATA_PATH)
    store, _ = study.build_store(frame)
    rows = data.get("results", [])
    ok(len(rows) == 252, "replication retains 132 discovery and 120 evaluation outputs")
    ok(len({row.get("trace_id") for row in rows}) == 252,
       "replication retains a unique native trace identifier for every output")

    recomputed: list[SimpleNamespace] = []
    quality_drift: list[tuple[str, int, int]] = []
    for row in rows:
        number = int(row["issue_number"])
        source = store[number]
        scenario = study.Scenario(
            issue_number=number,
            category=study.category_for(source["labels"]),
            labels=tuple(source["labels"]),
            html_url=source["html_url"],
            day=source["day"],
            state=source["state"],
        )
        quality = study.grade(
            scenario,
            row["answer"],
            row["tool_sequence"],
            row["tool_arguments"],
            task_design="natural-extractive-v2",
            source_record=source,
            condition=row["condition"],
        )
        if quality != row.get("quality"):
            quality_drift.append((str(row["condition"]), int(row["repeat"]), number))
        recomputed.append(
            SimpleNamespace(
                condition=row["condition"],
                repeat=int(row["repeat"]),
                issue_number=number,
                metrics=row["metrics"],
                quality=quality,
                answer=row["answer"],
                tool_sequence=row["tool_sequence"],
                tool_arguments=row["tool_arguments"],
            )
        )
    ok(not quality_drift,
       f"replication semantic and exact-source oracles recompute every row ({quality_drift})")
    ok(evidence_equal(study.aggregate_runs(recomputed), data.get("aggregate")),
       "replication aggregate recomputes from retained outputs")

    evaluation = [run for run in recomputed if run.condition != "discovery"]
    primary = {
        condition: [
            run for run in evaluation
            if run.condition == condition and run.repeat == 0
        ]
        for condition in ("baseline", "compiled", "macro")
    }
    ok({key: len(value) for key, value in primary.items()} ==
       {"baseline": 30, "compiled": 30, "macro": 30},
       "replication contains 30 primary outputs for every condition")
    for condition, values in primary.items():
        ok(sum(run.quality["factuality_exact"] for run in values) == 30
           and sum(run.quality["overall"] for run in values) == 30,
           f"replication {condition} passes 30/30 exact factual and task contracts")

    paired = study.paired_analysis(primary["baseline"], primary["compiled"])
    paired_macro = study.paired_analysis(
        primary["baseline"], primary["macro"], candidate_label="macro"
    )
    macro_vs_compiled = study.paired_analysis(
        primary["compiled"], primary["macro"],
        baseline_label="compiled", candidate_label="macro",
    )
    ok(evidence_equal(paired, data.get("paired_test")),
       "replication baseline-versus-compiler statistics recompute")
    ok(evidence_equal(paired_macro, data.get("paired_macro_test")),
       "replication baseline-versus-macro statistics recompute")
    ok(evidence_equal(macro_vs_compiled, data.get("paired_macro_vs_compiled")),
       "replication macro-versus-compiler statistics recompute")
    ok(evidence_equal(study.determinism_analysis(evaluation), data.get("determinism")),
       "replication determinism statistics recompute")

    expected_compiler = {
        "requests": 0.5,
        "tool_calls": 0.0,
        "total_tokens": 0.39510733039606205,
        "wall_latency_ms": 0.5174195228225102,
        "estimated_cost_usd": 0.32001348896623205,
    }
    expected_macro = {
        "requests": 0.5,
        "tool_calls": 2 / 3,
        "total_tokens": 0.5819083915700837,
        "wall_latency_ms": 0.47228851001072136,
        "estimated_cost_usd": 0.37454668776675415,
    }
    for name, expected in expected_compiler.items():
        ok(abs(paired["metrics"][name]["aggregate_reduction"] - expected) < 1e-12,
           f"replication compiler reduction recomputes: {name}")
    for name, expected in expected_macro.items():
        ok(abs(paired_macro["metrics"][name]["aggregate_reduction"] - expected) < 1e-12,
           f"replication macro reduction recomputes: {name}")
    ok(macro_vs_compiled["metrics"]["total_tokens"]["macro_mean"] <
       macro_vs_compiled["metrics"]["total_tokens"]["compiled_mean"]
       and macro_vs_compiled["metrics"]["estimated_cost_usd"]["macro_mean"] <
       macro_vs_compiled["metrics"]["estimated_cost_usd"]["compiled_mean"]
       and macro_vs_compiled["metrics"]["tool_calls"]["macro_mean"] <
       macro_vs_compiled["metrics"]["tool_calls"]["compiled_mean"],
       "macro beats the partial compiler on tokens, cost, and tool calls")
    ok(macro_vs_compiled["metrics"]["wall_latency_ms"]["compiled_mean"] <
       macro_vs_compiled["metrics"]["wall_latency_ms"]["macro_mean"],
       "partial compiler is faster than the macro in the replication")

    selection = data.get("selection", {})
    discovery_ids = {int(value) for value in selection.get("discovery_issue_numbers", [])}
    test = selection.get("test", [])
    test_ids = {int(row["issue_number"]) for row in test}
    counts = Counter(str(row.get("category")) for row in test)
    ok(len(discovery_ids) == 132 and len(test_ids) == 30
       and discovery_ids.isdisjoint(test_ids),
       "replication discovery and test selections are complete and disjoint")
    ok(counts == {"bug": 10, "enhancement": 10, "question": 10},
       "replication test set is balanced over three real issue classes")
    preflight = load(PAPER / "results/github_natural_replication/preflight.json")
    ok(selection.get("discovery_issue_numbers") ==
       preflight.get("selection", {}).get("discovery_issue_numbers")
       and test == preflight.get("selection", {}).get("test"),
       "paid replication uses the provider-free preflight's sealed records")

    primary_orders = Counter(
        tuple(value)
        for value in data.get("condition_order", {}).get("primary", {})
        .get("assignments", {}).values()
    )
    ok(set(primary_orders) == set(permutations(("baseline", "compiled", "macro")))
       and set(primary_orders.values()) == {5},
       "replication balances all six primary condition orders five times")

    compiler = data.get("compiler", {})
    artifact = compiler.get("artifact", {})
    ok(artifact.get("program", {}).get("tools") ==
       ["issue_get_record", "issue_get_labels"]
       and artifact.get("program", {}).get("removed_requests") == 2,
       "replication compiler safely emits only the two-read groundable prefix")
    ok(compiler.get("rejection_by_stage") == {"synthesize:ungroundable_slot": 1}
       and "issue_get_comments.limit:no_consistent_expression" in compiler.get("report", ""),
       "replication retains the full-prefix ungroundable-argument rejection")
    gate = artifact.get("gate", {})
    ok(gate.get("n_calibration_groups") == gate.get("n_accepted") == 92
       and gate.get("observed_violations") == 0
       and abs(float(gate.get("risk_upper_bound", 0)) - 0.049808920112407784) < 1e-12,
       "replication gate records 92 accepted groups, zero violations, and its exact bound")
    trace_selection = data.get("compiler_trace_selection", {})
    ok(trace_selection.get("tool_contract_eligible") == 132
       and trace_selection.get("eligible_under_executed_rule") == 130
       and len(trace_selection.get("used_issue_numbers", [])) == 116,
       "replication discloses 132 contract-valid, 130 factual, and 116 selected traces")

    revision = data.get("oracle_revision", {})
    ok(revision.get("changed_rows") == 212
       and revision.get("provider_calls_rerun") is False
       and revision.get("provider_outputs_changed") is False
       and revision.get("metrics_changed") is False,
       "semantic oracle revision changes 212 quality records and no provider evidence")
    ok(sum("online_quality" in row for row in rows) == 212,
       "every oracle-changed row preserves its online quality record")

    checkpoint_path = PAPER / "results/github_natural_replication/discovery_checkpoint.json"
    checkpoint = load(checkpoint_path)
    checkpoint_meta = data.get("discovery_checkpoint", {})
    ok(checkpoint_meta.get("sha256") == sha256(checkpoint_path)
       and checkpoint_meta.get("retained_provider_outputs") == 132,
       "final result binds the paid discovery checkpoint by digest")
    checkpoint_rows = {
        row["trace_id"]: row for row in checkpoint.get("results", [])
    }
    final_discovery = [row for row in rows if row.get("condition") == "discovery"]
    evidence_fields = ("issue_number", "trace_id", "metrics", "answer",
                       "tool_sequence", "tool_arguments", "dispatch", "episode_digest")
    ok(len(checkpoint_rows) == 132 and all(
        all(row.get(field) == checkpoint_rows[row["trace_id"]].get(field)
            for field in evidence_fields)
        for row in final_discovery
    ), "final discovery rows preserve checkpointed provider outputs and measurements")

    failed = load(PAPER / "results/github_natural_replication/failed_attempt_2026-08-03.json")
    ok(failed.get("status") == "failed_before_compilation_and_test_arms"
       and failed.get("provider_call_count") == "unknown"
       and failed.get("test_arms_started") is False,
       "pre-checkpoint failed attempt remains bounded and makes no quantitative claim")
    smoke = load(PAPER / "results/github_natural_replication/smoke_postfix/smoke.json")
    ok(len(smoke.get("results", [])) == 3 and smoke.get("failures") == [],
       "post-fix paid smoke retains three successful real-provider outputs")

    publication = load(PAPER / "results/publication_manifest.json")
    hashed = {record.get("path") for record in publication.get("files", [])}
    ok({
        "paper/results/github_natural_replication/results.json",
        "paper/results/github_natural_replication/discovery_checkpoint.json",
        "paper/results/github_natural_replication/failed_attempt_2026-08-03.json",
        "paper/results/github_natural_replication/smoke_postfix/smoke.json",
        "paper/scripts/github_live_study.py",
        "paper/scripts/test_oracle_weakness.py",
    } <= hashed, "publication manifest hashes replication evidence, driver, and tests")


def validate_portfolio_live() -> None:
    """Recompute selection and outcomes for the prospective portfolio pilot."""

    path = PAPER / "results/portfolio_live/results.json"
    data = load(path)
    if not data:
        return
    ok(data.get("schema") == "agent-compaction-portfolio-live/v1", "portfolio result schema")
    ok(data.get("status") == "complete", "prospective portfolio run completed")
    run = data.get("run", {})
    ok(run.get("prospective_action_selection") is True,
       "portfolio action was selected before the fresh cohort")
    ok(run.get("shadow_nonselected_action_executed") is False,
       "non-selected compiler was not executed on the prospective cohort")
    ok(run.get("openai_api_key_used") is True and run.get("secrets_serialized") is False,
       "portfolio run records provider use without serializing secrets")
    ok(data.get("failures") == [], "prospective portfolio run has no failures")

    import portfolio_live_study as study

    decision, config, calibration = study.select_action(model=run.get("model", ""))
    ok(decision.as_dict() == data.get("decision"),
       "portfolio decision recomputes from sealed calibration")
    ok(config.minimum_groups == 30 and config.quality_risk_limit == 0.15,
       "portfolio support and risk limits are frozen")
    evidence = {item.action: item for item in decision.evidence}
    ok(set(evidence) == {"compile", "macro"}
       and all(item.admitted for item in evidence.values()),
       "both measured actions pass calibration gates")
    ok(decision.selected_action == "macro" and decision.requires_review,
       "higher-utility macro is selected as a reviewable recommendation")
    ok(evidence["macro"].mean_utility > evidence["compile"].mean_utility,
       "macro utility exceeds compiler utility on calibration groups")

    rows = data["results"]
    ok(len(rows) == 24 and len({row["trace_id"] for row in rows}) == 24,
       "portfolio retains 24 unique native provider traces")
    by_condition = {
        condition: [row for row in rows if row["condition"] == condition]
        for condition in ("baseline", "macro")
    }
    ok(all(len(values) == 12 for values in by_condition.values()),
       "portfolio has 12 complete paired records per condition")
    ok(all(row["quality"]["overall"] for values in by_condition.values() for row in values),
       "all prospective exact task contracts pass")
    ok(all(row["metrics"]["requests"] == 4 for row in by_condition["baseline"])
       and all(row["metrics"]["requests"] == 2 for row in by_condition["macro"]),
       "selected macro changes every fresh workflow from four to two requests")
    ok(all(row["metrics"]["tool_calls"] == 3 for row in by_condition["baseline"])
       and all(row["metrics"]["tool_calls"] == 1 for row in by_condition["macro"]),
       "selected macro changes every fresh workflow from three to one tool call")

    proxies = {
        condition: [
            SimpleNamespace(
                issue_number=int(row["issue_number"]),
                repeat=int(row.get("repeat", 0)),
                metrics=row["metrics"],
                quality=row["quality"],
            )
            for row in values
        ]
        for condition, values in by_condition.items()
    }
    import github_live_study as fixed

    recomputed = fixed.paired_analysis(
        proxies["baseline"], proxies["macro"],
        candidate_label="selected_macro", baseline_label="baseline",
    )
    ok(evidence_equal(recomputed, data.get("paired_selected_vs_baseline")),
       "prospective paired portfolio statistics recompute")
    reductions = data["paired_selected_vs_baseline"]["metrics"]
    expected = {
        "requests": 0.5,
        "tool_calls": 2 / 3,
        "total_tokens": 0.5919582286742746,
        "wall_latency_ms": 0.7162352929291833,
        "estimated_cost_usd": 0.4062388804348649,
    }
    for name, value in expected.items():
        ok(abs(reductions[name]["aggregate_reduction"] - value) < 1e-12,
           f"prospective portfolio metric recomputes: {name}")

    prior_numbers = {
        int(row["issue_number"])
        for row in calibration["results"]
        if "issue_number" in row
    }
    current_numbers = {int(row["issue_number"]) for row in rows}
    ok(not (prior_numbers & current_numbers),
       "prospective portfolio records are calibration-disjoint")
    ok(data.get("selection", {}).get("categories") == ["bug", "enhancement", "other"],
       "fresh portfolio cohort records its available class mix")


def validate_guarded_composite() -> None:
    """Audit provider-free replay and the exploratory paid GCS comparison."""

    replay_path = PAPER / "results/gcs_validation/provider_free.json"
    live_path = PAPER / "results/gcs_live/results.json"
    ok(replay_path.exists(), "GCS provider-free validation exists")
    ok(live_path.exists(), "GCS live comparison exists")
    if not replay_path.exists() or not live_path.exists():
        return

    replay = load(replay_path)
    ok(replay.get("schema") == "agent-compaction-gcs-provider-free-validation/v1",
       "GCS replay schema")
    ok(replay.get("provider_calls_executed") == 0,
       "GCS replay performs no provider calls")
    ok(replay.get("source_provider_trace_count") == 132,
       "GCS replay reconstructs all 132 sealed provider traces")
    compiler = replay.get("compiler", {})
    ok(compiler.get("complete_region_steps") == 3
       and compiler.get("exposed_interfaces") == 1,
       "GCS replay compiles three reads behind one interface")
    ok(replay.get("replay") == {
        "attempted": 132,
        "dispatched": 124,
        "fallback": 8,
        "exact_projected_matches": 124,
        "projection_failures": [],
        "all_dispatched_exact": True,
    }, "GCS provider-free projection outcomes are exact")

    data = load(live_path)
    run = data.get("run", {})
    ok(data.get("schema") == "agent-compaction-gcs-live-study/v1",
       "GCS live schema")
    ok(run.get("provider_backed") is True
       and run.get("real_public_records") is True
       and run.get("openai_api_key_used") is True
       and run.get("secrets_serialized") is False,
       "GCS live run records real provider/data use without secrets")
    ok(run.get("comparative_claim_allowed") is True and data.get("failures") == [],
       "GCS live comparison is complete")

    rows = data.get("results", [])
    selected = {int(value) for value in data.get("selection", {}).get("issue_numbers", [])}
    ok(len(rows) == 24 and len({row.get("trace_id") for row in rows}) == 24,
       "GCS live study retains 24 unique provider traces")
    paired: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        paired[int(row["issue_number"])][str(row["condition"])] = row
    ok(set(paired) == selected and len(paired) == 12
       and all(set(pair) == {"macro", "gcs"} for pair in paired.values()),
       "GCS live result has 12 complete selected pairs")
    ok(all(pair[condition]["quality"]["overall"]
           for pair in paired.values() for condition in ("macro", "gcs")),
       "GCS and macro both pass every retained exact contract")
    ok(all(pair["macro"]["metrics"]["requests"] == 2
           and pair["gcs"]["metrics"]["requests"] == 1
           and pair["macro"]["metrics"]["tool_calls"] == 1
           and pair["gcs"]["metrics"]["tool_calls"] == 1
           and pair["gcs"]["metrics"]["provider_tool_calls"] == 0
           and pair["gcs"]["metrics"]["internal_tool_calls"] == 3
           for pair in paired.values()),
       "GCS removes one provider request while retaining three internal reads")
    schedule = [tuple(item["order"]) for item in data.get("schedule", [])]
    ok(Counter(schedule) == Counter({("gcs", "macro"): 6, ("macro", "gcs"): 6}),
       "GCS condition order is counterbalanced")

    expected = {
        "requests": 0.5,
        "tool_calls": 0.0,
        "total_tokens": 0.3889982502187227,
        "wall_latency_ms": 0.40031515830575515,
        "estimated_cost_usd": 0.3227115951015347,
    }
    metrics = data.get("macro_vs_gcs", {}).get("metrics", {})
    for name, value in expected.items():
        actual = metrics.get(name, {}).get("aggregate_reduction")
        ok(actual is not None and abs(float(actual) - value) < 1e-12,
           f"GCS paired metric recomputes: {name}")

    prior_paths = (
        PAPER / "results/github_natural_replication/discovery_checkpoint.json",
        PAPER / "results/github_natural_replication/results.json",
        PAPER / "results/github_natural_live/results.json",
        PAPER / "results/portfolio_live/results.json",
        PAPER / "results/github_live/results.json",
    )
    prior: set[int] = set()
    for path in prior_paths:
        payload = load(path)
        prior.update(
            int(row["issue_number"])
            for row in payload.get("results", [])
            if isinstance(row, dict) and "issue_number" in row
        )
        prior_selection = payload.get("selection", {})
        prior.update(int(value) for value in prior_selection.get("discovery_issue_numbers", []))
        prior.update(int(value) for value in prior_selection.get("smoke_issue_numbers", []))
        prior.update(
            int(row["issue_number"])
            for row in prior_selection.get("test", [])
            if isinstance(row, dict) and "issue_number" in row
        )
    ok(selected.isdisjoint(prior), "GCS cohort is disjoint from every earlier issue cohort")


def validate_optimizer_head_to_head() -> None:
    """Audit the bounded official-GEPA and fair pre-model comparator study."""

    result_path = PAPER / "results/optimizer_head_to_head/results.json"
    preflight_path = PAPER / "results/optimizer_head_to_head/preflight.json"
    ok(result_path.exists(), "optimizer head-to-head result exists")
    ok(preflight_path.exists(), "optimizer head-to-head preflight exists")
    if not result_path.exists() or not preflight_path.exists():
        return

    data = load(result_path)
    preflight = load(preflight_path)
    run = data.get("run", {})
    ok(data.get("schema") == "agent-compaction-optimizer-head-to-head/v1",
       "optimizer head-to-head schema")
    ok(run.get("provider_backed") is True
       and run.get("real_public_records") is True
       and run.get("openai_api_key_used") is True
       and run.get("secrets_serialized") is False,
       "optimizer comparison records real provider/data use without secrets")
    ok(run.get("gepa") == "0.1.4" and run.get("comparative_claim_allowed") is True,
       "optimizer comparison uses official GEPA 0.1.4 and completed")
    ok(data.get("failures") == [], "optimizer comparison has no recorded failures")

    selection = data.get("selection", {})
    train = set(selection.get("optimization_train", []))
    validation = set(selection.get("optimization_validation", []))
    test = set(selection.get("test", []))
    ok(len(train) == 4 and len(validation) == 2 and len(test) == 6
       and not (train & validation or train & test or validation & test),
       "optimizer train, validation, and deployment splits are disjoint")
    ok(selection.get("test_frozen_before_optimization") is True
       and selection.get("selection_uses_provider_outcomes") is False,
       "optimizer deployment split was frozen without provider outcomes")
    ok(selection.get("unavailable_categories_after_exclusions") == ["question"],
       "optimizer result records the unavailable question category")
    ok(preflight.get("selection") == selection,
       "optimizer result retains the exact preflight selection")

    parity = data.get("preflight", {}).get("provider_free_parity", {})
    ok(parity.get("provider_calls") == 0
       and parity.get("cases") == parity.get("exact_projection_matches") == 12
       and parity.get("mismatches") == [],
       "GCS and manual pre-model projections match provider-free on all split records")

    rows = data.get("deployment_results", [])
    conditions = {"baseline", "gepa", "gcs", "gcs_gepa", "manual_pre_model"}
    paired: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        paired[int(row["issue_number"])][str(row["condition"])] = row
    ok(len(rows) == 30 and set(paired) == test
       and all(set(group) == conditions for group in paired.values()),
       "optimizer deployment result has six complete five-condition blocks")
    ok(all(group[condition]["quality"]["overall"]
           and group[condition]["quality"]["tool_contract"]
           for group in paired.values() for condition in conditions),
       "all optimizer deployment arms pass all exact and tool contracts")
    ok(all(group["baseline"]["metrics"]["requests"] == 4
           and group["gepa"]["metrics"]["requests"] == 4
           and group["gcs"]["metrics"]["requests"] == 1
           and group["gcs_gepa"]["metrics"]["requests"] == 1
           and group["manual_pre_model"]["metrics"]["requests"] == 1
           for group in paired.values()),
       "deployment request counts are structurally exact")

    optimization = data.get("optimization", {})
    gepa = optimization.get("gepa_result", {})
    accounting = optimization.get("accounting", {})
    ok(optimization.get("method") == "official GEPA 0.1.4 optimize_anything"
       and gepa.get("improved") is False
       and gepa.get("best_prompt") == gepa.get("seed_prompt"),
       "bounded GEPA retained its seed prompt")
    ok(gepa.get("metric_calls") == 14
       and accounting.get("reflection_calls") == 3
       and accounting.get("combined_provider_requests") == 59
       and accounting.get("combined_total_tokens") == 63954
       and accounting.get("excluded_from_deployment_metrics") is True,
       "GEPA optimization budget and overhead are reported separately")

    baseline_gcs = data.get("comparisons", {}).get("baseline_vs_gcs", {})
    manual_gcs = data.get("comparisons", {}).get("manual_pre_model_vs_gcs", {})
    ok(abs(baseline_gcs.get("metrics", {}).get("requests", {}).get(
        "aggregate_reduction", -1) - 0.75) < 1e-12,
       "GCS reduces deployment provider requests 75 percent versus unchanged")
    ok(abs(baseline_gcs.get("metrics", {}).get("input_tokens", {}).get(
        "aggregate_reduction", -1) - 0.7823734236777715) < 1e-12,
       "GCS reduces deployment input tokens 78.237 percent versus unchanged")
    for metric in ("requests", "tool_calls", "input_tokens"):
        block = manual_gcs.get("metrics", {}).get(metric, {})
        ok(block.get("aggregate_reduction") == 0.0,
           f"GCS and manual pre-model baseline tie structurally: {metric}")
    ok(data.get("measurement_validation", {}).get(
        "provider_span_latency_excluded_from_comparisons") is True,
       "invalid provider span latency is retained but excluded from comparisons")
    publication = load(PAPER / "results/publication_manifest.json")
    hashed = {record.get("path") for record in publication.get("files", [])}
    ok({
        "paper/results/optimizer_head_to_head/preflight.json",
        "paper/results/optimizer_head_to_head/results.json",
        "paper/scripts/github_optimizer_head_to_head.py",
        "src/agent_compaction/optimization/gepa.py",
        "src/agent_compaction/runtime/manual.py",
        "tests/integration/test_optimizer_head_to_head.py",
    } <= hashed, "publication manifest hashes optimizer evidence, adapters, and tests")


def validate_continuation_replay() -> None:
    """Recompute the post-model contract replay without trusting its summary."""

    replay_path = PAPER / "results/github_natural_live/continuation_replay.json"
    ok(replay_path.exists(), "continuation-contract replay artifact exists")
    if not replay_path.exists():
        return
    replay = load(replay_path)
    source_path = PAPER / "results/github_natural_live/results.json"
    source = load(source_path)
    ok(replay.get("schema") == "agent-compaction-continuation-replay/v1",
       "continuation replay schema is pinned")
    ok(replay.get("provider_calls_executed") == 0
       and replay.get("secrets_used") is False
       and replay.get("counterfactual") is True,
       "continuation replay is explicitly provider-free and counterfactual")
    source_record = replay.get("source_results", {})
    ok(source_record.get("sha256") == sha256(source_path),
       "continuation replay binds the retained live-provider result bytes")

    from continuation_replay import checked_renderer, exact_contract, observations_for
    from agent_compaction.runtime.continuation import ContinuationEvidence, ContinuationGuard
    import github_live_study as fixed

    frame = fixed.pd.read_parquet(fixed.DATA_PATH)
    store, _ = fixed.build_store(frame)
    compiled = sorted(
        (row for row in source.get("results", []) if row.get("condition") == "compiled"),
        key=lambda row: int(row["issue_number"]),
    )
    guard = ContinuationGuard(exact_contract, renderer=checked_renderer)
    recomputed_cases: list[dict[str, Any]] = []
    for row in compiled:
        number = int(row["issue_number"])
        evidence = ContinuationEvidence(
            entry_state={"issue_number": number},
            observations=observations_for(store[number]),
            artifact_id=str(row.get("dispatch", {}).get("artifact_id") or "github-natural-grc"),
            metadata={"source_revision": fixed.HF_REVISION},
        )
        before = tuple(exact_contract(row["answer"], evidence))
        decision = guard.decide(row["answer"], evidence)
        after = tuple(exact_contract(decision.output, evidence)) if decision.accepted else ()
        recomputed_cases.append(
            {
                "issue_number": number,
                "source_trace_id": row["trace_id"],
                "original_pass": not before,
                "original_violations": list(before),
                "decision": decision.record,
                "final_pass": decision.accepted and not after,
                "final_violations": list(after),
                "rendered_output": decision.output if decision.recovered else None,
            }
        )
    ok(recomputed_cases == replay.get("cases"),
       "continuation replay recomputes case-by-case from source observations")
    summary = {
        "candidate_passes": sum(case["original_pass"] for case in recomputed_cases),
        "candidate_failures": sum(not case["original_pass"] for case in recomputed_cases),
        "accepted_without_repair": sum(
            case["decision"]["outcome"] == "ACCEPTED" for case in recomputed_cases
        ),
        "checked_render_repairs": sum(
            case["decision"]["outcome"] == "RENDERED" for case in recomputed_cases
        ),
        "rejections": sum(
            case["decision"]["outcome"] == "REJECTED" for case in recomputed_cases
        ),
        "final_contract_passes": sum(case["final_pass"] for case in recomputed_cases),
    }
    ok(summary == replay.get("summary") == {
        "candidate_passes": 17,
        "candidate_failures": 1,
        "accepted_without_repair": 17,
        "checked_render_repairs": 1,
        "rejections": 0,
        "final_contract_passes": 18,
    }, "continuation replay detects one miss and checked rendering restores 18/18")
    ok(guard.telemetry.as_dict() == replay.get("telemetry"),
       "continuation replay telemetry recomputes")

    publication = load(PAPER / "results/publication_manifest.json")
    hashed = {record.get("path") for record in publication.get("files", [])}
    ok({
        "paper/results/github_natural_live/continuation_replay.json",
        "paper/scripts/continuation_replay.py",
        "src/agent_compaction/runtime/continuation.py",
        "tests/unit/test_continuation.py",
    } <= hashed, "publication manifest hashes continuation implementation and replay")


def validate_nestful() -> None:
    data = load(PAPER / "results/nestful/results.json")
    if not data:
        return
    c = data["compiler"]
    p = c["provenance"]
    r = c["held_out_replay"]
    ok(c["n_episodes"] == 1415, "NESTFUL has 1,415 executable audited episodes")
    ok((p["expected_producer_recovered"], p["dependency_slots"]) == (5531, 5746),
       "NESTFUL provenance denominator matches paper")
    ok((r["test_passed"], r["test_abstained"], r["test_wrong"]) == (24, 12, 0),
       "NESTFUL held-out outcomes match paper")
    gate = c["exact_gate"]
    ok((gate["max_observed_family_support"], gate["minimum_zero_violation_groups"]) == (26, 92),
       "NESTFUL support/gate minimum matches paper")
    ok(gate["families_certifiable_even_with_zero_violations"] == 0 and
       gate["default_gate_outcome"] == "RETIRE", "NESTFUL correctly retires every family")


def validate_demo_suite() -> None:
    """Recompute the Tier-3 table from raw results rather than trusting the .tex.

    The demonstration suite is cited in the manuscript, so its numbers need the same
    treatment as Tier 1 and Tier 2: derived from the raw run, not from a constant.
    """

    raw = ROOT / "experiments/live_results/all_results.json"
    ok(raw.exists(), "Tier-3 raw results present")
    if not raw.exists():
        return
    payload = load(raw)
    ok(payload.get("manifest", {}).get("substrate") == "openai_api_live",
       "Tier-3 records a live provider substrate")
    ok(payload.get("manifest", {}).get("data_class") == "fictional deterministic fixtures",
       "Tier-3 declares its records as fictional, matching the manuscript")

    demos = payload.get("demos", {})
    # Refusal conditions: the correct outcome is the baseline model-call count at
    # unchanged quality. Cost is deliberately NOT asserted equal (H5 is not in dollars).
    refusals = {
        "mcp_ops": "compacted_fallback",
        "fulfillment": "compacted_loop_refused",
    }
    for demo, condition in refusals.items():
        body = demos.get(demo, {})
        conditions = body.get("conditions", {})
        if condition not in conditions or "baseline" not in conditions:
            errors.append(f"Tier-3 missing condition: {demo}/{condition}")
            continue
        base, cand = conditions["baseline"], conditions[condition]
        ok(base["requests"] == cand["requests"],
           f"Tier-3 {demo}/{condition} reproduces the baseline model-call count")
        ok(abs(base["quality"] - cand["quality"]) < 1e-9,
           f"Tier-3 {demo}/{condition} reproduces baseline quality")

    ful = demos.get("fulfillment", {}).get("conditions", {})
    if "baseline" in ful and "compacted" in ful:
        ok(ful["baseline"]["requests"] == 7.0 and ful["compacted"]["requests"] == 2.0,
           "Tier-3 partial compaction is 7.0 to 2.0 model calls, as reported")

    # The cost-inversion finding: tokens fall while estimated cost rises.
    inversions = []
    for demo, body in demos.items():
        comparison = body.get("comparisons", {})
        tokens = comparison.get("total_tokens_reduction")
        cost = comparison.get("estimated_cost_usd_reduction")
        if tokens is not None and cost is not None and tokens > 0.05 and cost < 0:
            inversions.append(demo)
    ok(sorted(inversions) == ["fulfillment", "tgws_router"],
       "Tier-3 cost inversion holds for exactly the two demos the paper names")


def validate_multidomain_preflight() -> None:
    """Keep the HMDA addition tied to its provider-free evidence boundary."""

    path = PAPER / "results/multidomain/preflight/validation.json"
    data = load(path)
    domains = {row.get("domain"): row for row in data.get("domains", [])}
    hmda = domains.get("hmda", {})
    ok(path.exists(), "multidomain preflight validation exists")
    ok(hmda.get("available") is True, "HMDA preflight is available")
    ok((hmda.get("cases"), hmda.get("independent_groups")) == (420, 420),
       "HMDA preflight retains 420 independent groups")
    ok((hmda.get("exact_oracle_passes"), hmda.get("independent_gold_passes")) == (420, 420),
       "HMDA exact and independent gold checks pass 420/420")
    ok(hmda.get("variable_path_fraction") == 416 / 420,
       "HMDA variable-path fraction matches the frozen pool")
    ok(data.get("provider_calls_executed") == 0,
       "multidomain preflight records zero provider calls")


def validate_offline_comparator() -> None:
    """Recompute the macro comparison and enforce its simulated-evidence boundary."""

    results = ROOT / "experiments/results"
    manifest = load(results / "run_manifest.json")
    ok(manifest.get("substrate") == "simulated",
       "hand-written-macro comparator is explicitly labelled simulated")
    names = ["support", "permissioned_rag", "incident_triage", "mcp_ops", "fulfillment"]
    ok(manifest.get("demos") == names, "offline comparator manifest lists the five reported workloads")

    expected = {
        "support": (0.725755, 0.754701),
        "permissioned_rag": (0.335064, 0.718163),
        "incident_triage": (0.921818, 0.779789),
        "mcp_ops": (0.724002, 1.0),
        "fulfillment": (0.660514, 0.641539),
    }
    rows: list[tuple[str, float, float]] = []
    for name in names:
        payload = load(results / f"{name}.json")
        comparisons = payload.get("comparisons", {})
        try:
            macro = float(comparisons["simple"]["request_ratio"]["point"])
            method = float(comparisons["full"]["request_ratio"]["point"])
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"offline comparator {name}: {exc}")
            continue
        exp_macro, exp_method = expected[name]
        ok(abs(macro - exp_macro) < 1e-12 and abs(method - exp_method) < 1e-12,
           f"offline comparator raw ratios match paper: {name}")
        rows.append((name, macro, method))

    table = (PAPER / "tables/comparator.tex").read_text(encoding="utf-8")
    for name, macro, method in rows:
        ok(f"{macro:.3f} & {method:.3f}" in table,
           f"offline comparator table is generated from raw ratios: {name}")

    publication = load(PAPER / "results/publication_manifest.json")
    hashed = {record.get("path") for record in publication.get("files", [])}
    evidence_paths = {
        "experiments/results/run_manifest.json",
        "experiments/results/support.json",
        "experiments/results/permissioned_rag.json",
        "experiments/results/incident_triage.json",
        "experiments/results/mcp_ops.json",
        "experiments/results/fulfillment.json",
        "experiments/run.py",
        "experiments/manifests/preregistration.md",
    }
    ok(evidence_paths <= hashed,
       "publication manifest hashes the offline comparator evidence and driver")


def validate_claim_boundaries() -> None:
    """Make evidence-calibrated wording and test collection machine-checkable."""

    abstract = (PAPER / "tex/abstract-body.tex").read_text(encoding="utf-8")
    body = (PAPER / "tex/body.tex").read_text(encoding="utf-8")
    readme = (PAPER / "README.md").read_text(encoding="utf-8")
    appendix = (PAPER / "appendix/appendix.tex").read_text(encoding="utf-8")
    bibliography = (PAPER / "bibliography/references.bib").read_text(encoding="utf-8")

    stale = {
        "abstract": (
            "attacks them with a perturbation suite",
            "pre-registered",
            "fallback to the unmodified agent on any miss",
            "92 independent groups",
        ),
        "body": (
            "conditional on exchangeable",
            "definition under exchangeability",
            "without an observed task error",
            "reconstructs most nested",
        ),
        "README": ("24 pp", "15 pp", "cost exactly the baseline", "recovers 96.3%"),
    }
    for label, text, phrases in (
        ("abstract", abstract, stale["abstract"]),
        ("body", body, stale["body"]),
        ("README", readme, stale["README"]),
    ):
        for phrase in phrases:
            ok(phrase.lower() not in text.lower(), f"{label} excludes stale claim: {phrase}")

    ok("--test-per-class 6 --repeat-cases 6" in appendix,
       "appendix records the archived live-study design explicitly")

    # The paper previously stated a single 5% selective-risk bound while three artifacts
    # were calibrated at 10%. Check the register against the sealed gates, and check that
    # the body discloses every artifact that misses the registered target.
    register = load(PAPER / "results/admission_register.json")
    ok(register.get("schema") == "agent-compaction-admission-register/v1",
       "admission register schema")
    ok(evidence_equal(register.get("registered_alpha"), 0.05),
       "admission register states the registered selective-risk target")
    ok(register.get("certificate_scope") == "per-fixed-candidate threshold grid",
       "admission register scopes its certificate to one fixed candidate")
    ok(register.get("candidate_family_multiplicity_adjusted") is False and
       register.get("compiler_wide_candidate_search_guarantee") is False,
       "admission register rejects an unimplemented compiler-wide search guarantee")
    ok(register.get("two_candidate_zero_violation_groups_required") == 106,
       "admission register records the two-candidate Bonferroni requirement")
    looser = [row for row in register["artifacts"] if not row["meets_registered_alpha"]]
    ok(len(looser) == 3,
       f"admission register records the three artifacts above the registered alpha, found {len(looser)}")
    for row in register["artifacts"]:
        gate = row
        ok(evidence_equal(gate["coverage"], gate["n_accepted"] / gate["n_calibration_groups"]),
           f"admission register coverage is consistent: {row['study']}")
        ok(gate["observed_violations"] == 0,
           f"admission register records zero calibration violations: {row['study']}")
    ok(r"\input{../tables/admission_register.tex}" in body,
       "body includes the admission register table")
    ok("were calibrated at $\\alpha=.10$" in body or "calibrated at $\\alpha=.10$" in body,
       "body discloses the looser selective-risk level in prose")
    ok("the family would have retired" in body,
       "body states the consequence of the looser level at the registered target")
    ok("10\\%-selective-risk result" in body,
       "body labels the GCS result by the risk level that licenses it")
    ok("Per-candidate simultaneous calibration" in body and
       r"k_\eta\mid n_\eta=m\sim\operatorname{Binomial}(m,r_\eta)" in body and
       r"|\Lambda|\gamma=\delta" in body,
       "body includes the conditional-binomial and union-bound proof")
    ok(r"n_\eta=0\ \text{or}\ k_\eta=n_\eta" in body,
       "body gives the Clopper-Pearson edge cases explicitly")
    ok("not a multiplicity-corrected compiler-wide certificate" in body and
       "92 to 106 admitted groups" in body,
       "body discloses candidate-family multiplicity and its sample-size consequence")

    # Cache accounting is the evidence behind the token-versus-dollar claim; keep the
    # derived record and the prose that cites it bound together.
    cache = load(PAPER / "results/cache_accounting.json")
    ok(cache.get("schema") == "agent-compaction-cache-accounting/v1", "cache accounting schema")
    ok(len(cache["families"]) == 3, "cache accounting covers the three primary families")
    issue = next(row for row in cache["families"] if row["family"] == "Issue-type routing")
    ok(issue["arms"]["manual"]["cached_input_share"] == 0.0,
       "cache accounting records the macro's absent cache reuse")
    ok(issue["arms"]["compiled"]["cached_input_share"] > 0.2,
       "cache accounting records the compiled arm's retained cache reuse")
    for row in cache["families"]:
        ok(row["break_even_episodes"] and row["break_even_episodes"] > 0,
           f"cache accounting reports provider-side break-even: {row['family']}")
    ok(r"\input{../tables/cache_accounting.tex}" in body,
       "body includes the cache accounting table")
    abstract_words = re.findall(r"\b[\w'-]+\b", re.sub(r"\\[A-Za-z]+", " ", abstract))
    ok(len(abstract_words) <= 275,
       f"abstract stays concise at {len(abstract_words)} words")
    ok("its normal output is refusal" in abstract.lower()
       and "retain the unchanged agent" in abstract.lower(),
       "abstract scopes compiler admission as compile-or-retain")
    ok("traces establish recurrence, not" in abstract.lower(),
       "abstract states the central evidence boundary")
    ok("portfolio optimization beyond the pilot" in body.lower(),
       "body distinguishes the implemented pilot from extension work")
    ok(re.search(r"not evidence that the\s+selector beats an always-macro policy",
                 body.lower()) is not None,
       "body rejects a cross-workflow portfolio claim")
    claims = (PAPER / "tables/claims_register.tex").read_text(encoding="utf-8")
    ok("The portfolio recommends a measured macro" in claims,
       "claims register records the implemented reviewed recommendation")
    ok("Portfolio selection beats an always-macro policy" in claims and
       "Not supported" in claims,
       "claims register rejects unsupported fixed-policy superiority")
    ok("Guarded composite synthesis beats the measured provider-visible macro" in claims
       and "Exploratory" in claims,
       "claims register scopes the GCS macro result")
    ok("GCS outperforms an equally pre-executed manual program" in claims
       and "structural parity" in claims,
       "claims register rejects unsupported manual-program superiority")
    ok("Bounded GEPA improves this workflow" in claims
       and "seed retained" in claims,
       "claims register records the bounded GEPA negative result")
    ok("compiler-wide control after candidate-family search" in claims and
       "Not established" in claims and "106 zero-violation groups" in claims,
       "claims register rejects unsupported compiler-wide candidate-search control")
    for key in ("agrawal2026gepa", "wei2026evoc2f", "winston2026agentjit"):
        ok(key in bibliography and f"\\cite{{{key}}}" in body,
           f"current related work is cited and discussed: {key}")

    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    testpaths = config.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("testpaths", [])
    ok("paper/scripts" in testpaths,
       "default pytest collection includes the oracle-weakness regressions")


def validate_manifest() -> None:
    manifest = load(PAPER / "results/artifact_manifest.json")
    for record in manifest.get("artifacts", []):
        path = ROOT / record["path"]
        ok(path.exists(), f"manifest artifact exists: {record['path']}")
        if path.exists():
            ok(path.stat().st_size == record["bytes"], f"manifest byte count: {record['path']}")
            ok(sha256(path) == record["sha256"], f"manifest checksum: {record['path']}")

    publication_path = PAPER / "results/publication_manifest.json"
    if publication_path.exists():
        publication = load(publication_path)
        ok(publication.get("schema") == "agent-compaction-publication-manifest/v1",
           "publication manifest schema")
        for record in publication.get("files", []):
            path = ROOT / record["path"]
            ok(path.exists(), f"publication-manifest artifact exists: {record['path']}")
            if path.exists():
                ok(path.stat().st_size == record["bytes"], f"publication-manifest byte count: {record['path']}")
                ok(sha256(path) == record["sha256"], f"publication-manifest checksum: {record['path']}")


def validate_publication() -> None:
    required = [
        # Shared manuscript sources: one abstract, one body, one figure/algorithm set.
        "tex/main.tex", "tex/article.tex", "tex/body.tex", "tex/abstract.tex",
        "tex/abstract-body.tex",
        "figures/architecture.tex", "figures/alg-compile.tex",
        "figures/alg-provenance.tex", "figures/alg-calibrate.tex",
        "figures/alg-dispatch.tex",
        "appendix/appendix.tex", "bibliography/references.bib",
        # Executable evidence for the oracle limitation stated in the manuscript.
        "scripts/test_oracle_weakness.py",
        "build/main.pdf", "build/article.pdf",
        "README.md", "supplementary/evidence-register.md",
        "supplementary/experiment-verification.md",
        "paper-review.md", "supplementary/quality-assessment.md",
        "supplementary/natural-live-study-protocol.md",
        "supplementary/external-benchmark-audit.md",
        "results/github_natural_replication/preflight.json",
        "results/github_natural_replication/results.json",
        "results/github_natural_replication/discovery_checkpoint.json",
        "results/github_natural_live/results.json",
        "results/github_natural_live/smoke.json",
        "results/gcs_validation/provider_free.json",
        "results/gcs_live/results.json",
        "results/optimizer_head_to_head/preflight.json",
        "results/optimizer_head_to_head/results.json",
        "results/github_workflow_families/pr_outcome/final/results.json",
        "results/github_workflow_families/backlog_attention/final/results.json",
        "results/github_workflow_families/summary.json",
        "scripts/validate_guarded_composite.py",
        "scripts/github_gcs_live_study.py",
        "scripts/github_optimizer_head_to_head.py",
        "scripts/github_workflow_family_study.py",
        "scripts/build_github_family_summary.py",
        "generated_figures/live_efficiency.pdf", "generated_figures/paired_test.pdf",
        "generated_figures/gate_support.pdf", "generated_figures/pilot_ablation.pdf",
        "generated_figures/natural_live_comparison.pdf",
        "tables/natural_live_results.tex",
        "tables/natural_replication_results.tex",
        "tables/gcs_live_results.tex",
        "tables/optimizer_head_to_head.tex",
        "tables/github_workflow_families.tex",
        "tables/external_benchmark_matrix.tex",
        "results/external_benchmarks/source_preflight.json",
        "results/external_benchmarks/reference_analysis.json",
        "results/external_benchmarks/api_bank_execution.json",
        "results/external_benchmarks/bfcl_gold_execution.json",
        "results/external_benchmarks/toolsandbox_live.json",
        "results/external_benchmarks/tau2_live.json",
        "results/external_benchmarks/browsecomp_live.json",
        "scripts/external_benchmark_sources.py",
        "scripts/external_benchmark_matrix.py",
        "scripts/api_bank_benchmark.py",
        "scripts/bfcl_structural_benchmark.py",
        "scripts/toolsandbox_live_summary.py",
        "scripts/tau2_live_summary.py",
        "scripts/browsecomp_live_benchmark.py",
        "slides/GAC-seminar.pptx",
        "slides/GAC-technical-review.pptx",
        "slides/gac-template-map.json",
        "slides/README.md",
        "slides/compiling-recurrent-agent-workflows-into-guarded-programs.pptx",
        "slides/compiling-recurrent-agent-workflows-into-guarded-programs-detailed.pptx",
        "scripts/generate_slides.mjs",
        "results/slide_generation.json",
        "compiling-recurrent-agent-workflows-into-guarded-programs.pdf",
    ]
    for rel in required:
        ok((PAPER / rel).exists(), f"publication artifact exists: {rel}")

    # Both builds must be clean, and both must render the same content, because they
    # share a body: a divergence means one wrapper silently dropped an input.
    for build in ("main", "article"):
        log = PAPER / f"build/{build}.log"
        pdf = PAPER / f"build/{build}.pdf"
        # A stale log silently satisfies every check below. Tectonic only writes the log
        # with --keep-intermediates, so a build run without it leaves the previous log in
        # place; that hid a 11.9pt regression during this review.
        if log.exists() and pdf.exists():
            ok(log.stat().st_mtime >= pdf.stat().st_mtime - 5,
               f"{build}: LaTeX log is not older than the PDF it should describe")
        if log.exists():
            text = log.read_text(encoding="utf-8", errors="ignore")
            undefined = re.search(
                r"LaTeX Warning: (?:Citation|Reference).*undefined"
                r"|There were undefined references",
                text,
            )
            ok(undefined is None,
               f"{build}: LaTeX log has no undefined citation/reference warning")
            # This gate exists because a hand-run grep with a mis-escaped pattern
            # reported zero overfull boxes and hid 13 of them (up to 29.96pt) in a table
            # whose cells printed past their rules. A fixed-string machine check cannot
            # make that mistake.
            widths = [float(w) for w in re.findall(r"Overfull \\hbox \(([0-9.]+)pt", text)]
            worst = max(widths, default=0.0)
            ok(worst <= 2.0,
               f"{build}: no overfull box wider than 2.0pt "
               f"(worst {worst:.2f}pt of {len(widths)})")
            # Vertical overruns get their own, looser threshold, and deliberately so: a
            # 2pt horizontal overrun puts glyphs past a column rule or table edge where a
            # reader sees it, whereas a 2pt vertical overrun moves a page's last baseline
            # by 0.7mm. Two-column layouts with spanning floats produce these routinely.
            vboxes = [float(v) for v in re.findall(r"Overfull \\vbox \(([0-9.]+)pt", text)]
            worst_v = max(vboxes, default=0.0)
            ok(worst_v <= 3.0,
               f"{build}: no overfull vbox taller than 3.0pt "
               f"(worst {worst_v:.2f}pt of {len(vboxes)})")
        try:
            pdf_text = extract_pdf_text(PAPER / f"build/{build}.pdf")
            # Two-column extraction can insert a newline inside a section heading even
            # when the rendered heading is contiguous, while PyPDF can omit spaces in
            # algorithm captions. Normalize non-alphanumerics so the gate checks
            # publication content rather than an extractor's token-boundary choices.
            searchable_pdf_text = re.sub(r"[^a-z0-9]+", "", pdf_text.lower())
            # Assert the current title, not the method name: the phrase "Guarded Agentic
            # Compaction" still appears in the body where the method is defined, so
            # checking it would pass even if the title were dropped entirely.
            for phrase in ("Compiling Recurrent Agent Workflows",
                           "into Guarded Programs",
                           "Reza Rahimi",
                           "Jazzx AI",
                           "NESTFUL",
                           "Three real-record workflow families",
                           "transfer across three workflow families",
                           "90/90 exact outcomes",
                           "Expanded natural-order Tier-2 replication",
                           "GEPA",
                           "Fair placement and bounded prompt optimization",
                           "Prospective portfolio selection",
                           "Exploratory GCS",
                           "Portfolio optimization beyond the pilot",
                           "Limitations and Threats to Validity",
                           "Code Availability",
                           "github.com/rrahimi-uci/guarded-agentic-compaction"):
                normalized_phrase = re.sub(r"[^a-z0-9]+", "", phrase.lower())
                ok(normalized_phrase in searchable_pdf_text,
                   f"{build}: compiled PDF contains: {phrase}")
            # The architecture figure and retained end-to-end algorithm must actually
            # reach the page.
            # Algorithm 1's caption was retitled when it was corrected to describe the
            # end-to-end pipeline rather than one function; match the current wording.
            for phrase in ("System architecture", "end-to-end pipeline an operator runs",
                           "hand-written composite tool",
                           "typed provenance search",
                           "fixed-grid exact admission",
                           "staged dispatch"):
                normalized_phrase = re.sub(r"[^a-z0-9]+", "", phrase.lower())
                ok(normalized_phrase in searchable_pdf_text,
                   f"{build}: compiled PDF contains exhibit: {phrase}")
            ok("GACreconstructs" not in pdf_text,
               f"{build}: acronym macros do not swallow the following space")
        except Exception as exc:
            errors.append(f"{build}: PDF text validation: {exc}")


def validate_no_secrets() -> None:
    patterns = [
        re.compile(rb"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(rb"hf_[A-Za-z0-9]{20,}"),
        re.compile(rb"OPENAI_API_KEY\s*=\s*[^\s$<{]"),
    ]
    excluded_suffixes = {".parquet", ".png", ".pdf", ".pyc", ".xdv"}
    findings: list[str] = []
    for path in PAPER.rglob("*"):
        if (not path.is_file() or path.suffix in excluded_suffixes
                or path.name.startswith("~$") or path.name == ".DS_Store"):
            continue
        data = path.read_bytes()
        if any(pattern.search(data) for pattern in patterns):
            findings.append(str(path.relative_to(ROOT)))
    ok(not findings, f"publication tree contains no API-secret-shaped value ({findings})")


def validate_github_workflow_families() -> None:
    """Recompute the new real-record family claims from condition-level evidence."""

    paths = {
        "pr_outcome": PAPER / "results/github_workflow_families/pr_outcome/final/results.json",
        "backlog_attention": PAPER / "results/github_workflow_families/backlog_attention/final/results.json",
    }
    expected = {
        "pr_outcome": {
            "exact": (30, 30, 30),
            "tools": ["pr_get_record", "pr_get_merge_status", "pr_get_discussion"],
            "reductions": (0.75, 0.8081351858437466, 0.7298578346394264,
                           0.752987539445336),
        },
        "backlog_attention": {
            "exact": (29, 30, 30),
            "tools": ["backlog_get_record", "backlog_get_ownership",
                      "backlog_get_discussion"],
            "reductions": (0.7478991596638656, 0.8137251455821528,
                           0.6889010346028281, 0.7507844303160591),
        },
    }
    test_sets: dict[str, set[int]] = {}
    for family, path in paths.items():
        ok(path.exists(), f"{family}: final real-record family result exists")
        if not path.exists():
            continue
        result = load(path)
        ok(result.get("schema") == "agent-compaction-github-workflow-family/v1",
           f"{family}: result schema")
        run = result.get("run", {})
        ok(run.get("family") == family, f"{family}: run names the workflow family")
        ok(run.get("provider_backed") is True and run.get("openai_api_key_used") is True,
           f"{family}: live provider and configured API key were used")
        ok(run.get("real_public_records") is True and run.get("simulated") is False,
           f"{family}: real public records are not relabeled simulation")
        ok(run.get("secrets_serialized") is False,
           f"{family}: no secret value is serialized")
        selection = result.get("selection", {})
        discovery = set(map(int, selection.get("discovery", [])))
        test = set(map(int, selection.get("test", [])))
        test_sets[family] = test
        ok(len(discovery) == 132 and len(test) == 30 and discovery.isdisjoint(test),
           f"{family}: 132 discovery and 30 disjoint test records")
        ok(selection.get("selection_uses_provider_outcomes") is False,
           f"{family}: cohort selection is provider-outcome-free")
        ok(sorted(selection.get("discovery_class_counts", {}).values()) == [44, 44, 44]
           and sorted(selection.get("test_class_counts", {}).values()) == [10, 10, 10],
           f"{family}: discovery and test classes are balanced")
        rows = result.get("results", [])
        by_condition = {
            condition: [row for row in rows if row.get("condition") == condition]
            for condition in ("baseline", "compiled", "manual_pre_model")
        }
        ok(all(len(rows_) == 30 for rows_ in by_condition.values()),
           f"{family}: 30 paired rows per primary condition")
        exact_counts = tuple(
            sum(bool(row.get("quality", {}).get("overall")) for row in by_condition[name])
            for name in ("baseline", "compiled", "manual_pre_model")
        )
        ok(exact_counts == expected[family]["exact"],
           f"{family}: exact outcome counts are source-bound")
        ok(result.get("failures") == [], f"{family}: final run has zero infrastructure failures")
        artifact = result.get("compiler", {}).get("artifact", {})
        program = artifact.get("program", {})
        ok(program.get("tools") == expected[family]["tools"],
           f"{family}: distinct three-tool compiled vocabulary")
        gate = artifact.get("gate", {})
        ok(gate.get("n_calibration_groups") == 92
           and evidence_equal(gate.get("risk_upper_bound"), 0.049808920112407784),
           f"{family}: exact 92-group admission bound")
        guard_clauses = artifact.get("guard", {}).get("clauses", [])
        id_clause = next((item for item in guard_clauses
                          if item.get("path") == "z.record_number"), {})
        ok(id_clause.get("type_name") == "int"
           and id_clause.get("hull", {}).get("kind") == "any",
           f"{family}: opaque record identifier keeps type without empirical range")
        comparison = result.get("comparisons", {}).get("baseline_vs_compiled", {})
        metrics = comparison.get("metrics", {})
        observed = tuple(metrics[name]["aggregate_reduction"] for name in (
            "requests", "total_tokens", "wall_latency_ms", "estimated_cost_usd"
        ))
        ok(evidence_equal(observed, expected[family]["reductions"]),
           f"{family}: published efficiency reductions match raw rows")

    if test_sets.keys() == paths.keys():
        ok(test_sets["pr_outcome"].isdisjoint(test_sets["backlog_attention"]),
           "new workflow-family held-out cohorts are mutually disjoint")
    pilot_path = PAPER / "results/github_workflow_families/pr_outcome/pilot_v1/results.json"
    if pilot_path.exists() and "pr_outcome" in test_sets:
        pilot_test = set(map(int, load(pilot_path).get("selection", {}).get("test", [])))
        ok(test_sets["pr_outcome"].isdisjoint(pilot_test),
           "final PR cohort is fresh relative to the archived paid pilot")

    summary_path = PAPER / "results/github_workflow_families/summary.json"
    ok(summary_path.exists(), "three-family checked summary exists")
    if summary_path.exists():
        summary = load(summary_path)
        ok(summary.get("schema") == "agent-compaction-github-workflow-family-summary/v1",
           "three-family summary schema")
        ok(summary.get("simulated") is False, "three-family summary is real evidence")
        overall = summary.get("overall", {})
        ok((overall.get("n"), overall.get("baseline_exact"),
            overall.get("compiled_exact"), overall.get("manual_exact")) == (90, 89, 90, 90),
           "three-family aggregate exact counts")
        expected_overall = {
            "requests": 0.6657381615598885,
            "tool_calls": 0.4423791821561338,
            "total_tokens": 0.630649830153015,
            "wall_latency_ms": 0.6421234029412591,
            "estimated_cost_usd": 0.5867086898399436,
        }
        ok(all(evidence_equal(overall.get(name, {}).get("reduction"), value)
               for name, value in expected_overall.items()),
           "three-family weighted reductions match condition-level evidence")
        ok(all(sha256(ROOT / row["source"]) == row["source_sha256"]
               for row in summary.get("families", [])),
           "three-family summary binds every source result by SHA-256")


def validate_external_benchmarks() -> None:
    """Verify all ten named sources without collapsing unlike evidence classes."""

    path = PAPER / "results/external_benchmarks/reference_analysis.json"
    ok(path.exists(), "all-source benchmark evidence matrix exists")
    if not path.exists():
        return
    result = load(path)
    ok(result.get("schema") == "agent-compaction-external-benchmark-matrix/v1",
       "all-source benchmark evidence schema")
    expected = {
        "agentbench", "api_bank", "bfcl", "browsecomp", "gaia", "nestful",
        "swe_bench_verified", "tau2", "toolbench", "toolsandbox",
    }
    benchmarks = result.get("benchmarks", {})
    ok(set(benchmarks) == expected, "all ten named benchmark families have a disposition")
    totals = result.get("totals", {})
    ok(totals.get("named_benchmarks") == 10,
       "all-source ledger reports ten named benchmark families")
    ok(totals.get("measured_compiler_benchmarks") == 2,
       "only two benchmark families license compiler measurements")
    ok((totals.get("screened_tasks"), totals.get("screened_reference_actions")) ==
       (5419, 17836), "all-source screened task/action denominators are exact")
    ok((totals.get("executed_external_paths"), totals.get("live_provider_benchmarks"),
        totals.get("provider_calls")) == (5, 3, 77),
       "executed paths and exactly accounted provider calls are exact")
    ok(totals.get("provider_call_accounting_complete") is False,
       "ToolSandbox request accounting remains explicitly incomplete")

    api = benchmarks.get("api_bank", {}).get("execution", {})
    ok((api.get("tasks"), api.get("candidate_windows"), api.get("families_synthesized")) ==
       (212, 48, 2), "API-Bank compiler corpus and synthesis counts are exact")
    ok((api.get("held_out_passed"), api.get("held_out_abstained"),
        api.get("held_out_wrong"), api.get("gate_outcome")) == (0, 2, 0, "RETIRE"),
       "API-Bank held-out refusal outcome is exact")
    ok((api.get("upstream_actions_passed"), api.get("upstream_actions_attempted")) ==
       (338, 389), "API-Bank upstream replay denominator is exact")

    bfcl = benchmarks.get("bfcl", {}).get("execution", {})
    ok((bfcl.get("official_checker_valid"), bfcl.get("tasks")) == (200, 200),
       "BFCL gold plans pass the official checker")
    tau = benchmarks.get("tau2", {}).get("execution", {})
    ok((tau.get("tasks"), tau.get("passed"), tau.get("provider_requests"),
        tau.get("total_tokens")) == (4, 0, 71, 288757),
       "tau2/tau3 live-provider result is exact")
    toolsandbox = benchmarks.get("toolsandbox", {}).get("execution", {})
    ok(toolsandbox.get("tasks") == 1 and
       abs(float(toolsandbox.get("milestone_similarity", 0)) - 0.9818215727005191) < 1e-12,
       "ToolSandbox official simulated-environment result is exact")
    browse = benchmarks.get("browsecomp", {}).get("execution", {})
    ok((browse.get("tasks"), browse.get("correct"), browse.get("provider_requests"),
        browse.get("web_search_calls")) == (3, 1, 6, 28),
       "BrowseComp bounded live-web result is exact")
    ok(benchmarks.get("gaia", {}).get("reason") ==
       "upstream authorization denied with HTTP 403",
       "GAIA authorization gate is retained without imputed metrics")

    executed = [b.get("execution", {}) for b in benchmarks.values() if b.get("execution")]
    ok(all(item.get("is_real_world_demo") is False for item in executed),
       "no simulator or hosted benchmark is relabeled as a real-world demo")
    boundary = result.get("claim_boundary", {})
    ok(boundary == {
        "gated_source_metrics_imputed": False,
        "screening_is_compiler_execution": False,
        "screening_is_quality_evaluation": False,
        "simulated_benchmarks_are_real_world_demos": False,
        "task_only_zero_coverage_is_failure": False,
    }, "all-source claim boundary is fail-closed")
    ok(result.get("secrets_serialized") is False,
       "all-source evidence serializes no credential value")


def validate_slides() -> None:
    decks = (
        ("compiling-recurrent-agent-workflows-into-guarded-programs.pptx", 27, "seminar"),
        ("compiling-recurrent-agent-workflows-into-guarded-programs-detailed.pptx", 23, "technical"),
    )
    for filename, expected_slides, label in decks:
        path = PAPER / "slides" / filename
        ok(path.exists() and path.stat().st_size > 0,
           f"{label} publication slide deck exists and is non-empty")
        if not path.exists() or path.stat().st_size == 0:
            continue
        try:
            with zipfile.ZipFile(path) as package:
                names = package.namelist()
                slide_parts = sorted(
                    name for name in names
                    if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
                )
                ok(len(slide_parts) == expected_slides,
                   f"{label} publication slide deck contains {expected_slides} slides")
                payload = b"\n".join(package.read(name) for name in slide_parts)
                ok(b"Compiling Recurrent Agent" in payload
                   and b"Workflows into Guarded Programs" in payload,
                   f"{label} publication slide deck contains the current paper title")
                ok(b"When Traces Are Not Enough" not in payload,
                   f"{label} publication slide deck contains no superseded title")
                ok(b"Fair placement ties GCS" in payload,
                   f"{label} publication slide deck contains the fair-placement comparison")
                ok(b"GEPA retains its seed" in payload,
                   f"{label} publication slide deck contains the bounded GEPA result")
                ok(b"Efficiency transfers; manual programs remain the runtime baseline" in payload,
                   f"{label} publication slide deck contains the workflow-family result")
                ok(b"90 / 90" in payload,
                   f"{label} publication slide deck contains the three-family exact result")
                media = [name for name in names if name.startswith("ppt/media/")]
                ok(all(package.getinfo(name).file_size > 0 for name in media),
                   f"{label} publication slide deck contains no empty media parts")
        except Exception as exc:
            errors.append(f"{label} publication slide deck package validation: {exc}")

    # A deck rendered from an older generator is not an error, but shipping it silently
    # is. Require the mismatch to be declared, with the command that resolves it, so the
    # repository never asserts a deck matches sources it was not built from.
    record = load(PAPER / "results/slide_generation.json")
    generator = PAPER / "scripts/generate_slides.mjs"
    current = sha256(generator)
    recorded = record.get("generator_sha256_current")
    pending = record.get("regeneration_required")
    if recorded == current:
        ok(pending is None,
           "slide record claims no pending regeneration when the generator is unchanged")
    else:
        ok(isinstance(pending, dict) and pending.get("reason") and pending.get("command"),
           "slide record declares the pending regeneration for a revised generator")
        ok(sorted(pending.get("stale_outputs", [])) == sorted(
               record["outputs"][key]["path"] for key in ("seminar", "technical")),
           "slide record names both decks as stale")


def validate_slide_generation() -> None:
    """Bind generated decks to the exact templates, evidence, and source-slide map."""

    manifest_path = PAPER / "results/slide_generation.json"
    map_path = PAPER / "slides/gac-template-map.json"
    generator_path = PAPER / "scripts/generate_slides.mjs"
    ok(manifest_path.exists(), "slide-generation manifest exists")
    ok(map_path.exists(), "GAC source-to-output slide map exists")
    ok(generator_path.exists(), "artifact-tool slide generator exists")
    if not manifest_path.exists() or not map_path.exists():
        return

    manifest = load(manifest_path)
    mapping = load(map_path)
    ok(manifest.get("schema") == "agent-compaction-slide-generation/v1",
       "slide-generation manifest schema")
    ok(mapping.get("schema") == "agent-compaction-slide-template-map/v1",
       "GAC slide-template map schema")
    ok(manifest.get("generator") == "paper/scripts/generate_slides.mjs",
       "slide-generation manifest names the maintained generator")
    ok(manifest.get("template_map") == "paper/slides/gac-template-map.json",
       "slide-generation manifest names the maintained template map")

    expected_outputs = {"seminar": 27, "technical": 23}
    for name, expected_count in expected_outputs.items():
        spec = mapping.get("templates", {}).get(name, {})
        retained_template = manifest.get("templates", {}).get(name, {})
        source_path = ROOT / str(spec.get("path", "missing"))
        ok(source_path.exists(), f"{name} GAC source template exists")
        if source_path.exists():
            actual_hash = sha256(source_path)
            ok(spec.get("sha256") == actual_hash,
               f"{name} GAC source template matches pinned hash")
            ok(retained_template.get("sha256") == actual_hash,
               f"{name} slide manifest binds the source-template bytes")
        source_map = spec.get("source_slide_for_output", [])
        ok(len(source_map) == expected_count,
           f"{name} source-to-output map covers all {expected_count} slides")
        ok(manifest.get("source_slide_for_output", {}).get(name) == source_map,
           f"{name} generated deck retains the reviewed source-slide map")

        output = manifest.get("outputs", {}).get(name, {})
        output_path = ROOT / str(output.get("path", "missing"))
        ok(output.get("path") == spec.get("output"),
           f"{name} manifest points at the canonical publication deck")
        ok(output.get("slides") == expected_count,
           f"{name} slide manifest records {expected_count} output slides")
        ok(output_path.exists(), f"{name} generated publication deck exists")
        if output_path.exists():
            ok(output.get("sha256") == sha256(output_path),
               f"{name} generated publication deck matches its manifest hash")

    evidence = manifest.get("evidence", {})
    evidence_paths = {
        "gcs_live": PAPER / "results/gcs_live/results.json",
        "gcs_replay": PAPER / "results/gcs_validation/provider_free.json",
        "optimizer_head_to_head": PAPER / "results/optimizer_head_to_head/results.json",
        "external_benchmarks": PAPER / "results/external_benchmarks/reference_analysis.json",
        "github_workflow_families": PAPER / "results/github_workflow_families/summary.json",
    }
    for name, path in evidence_paths.items():
        ok(path.exists(), f"slide evidence exists: {name}")
        if path.exists():
            ok(evidence.get(name, {}).get("sha256") == sha256(path),
               f"slide-generation manifest binds evidence bytes: {name}")
    ok(manifest.get("evidence_boundary") ==
       "Three real-record workflow families support the primary transfer result: compiled 90/90, baseline 89/90, manual 90/90. The snapshot does not establish cross-repository or time-forward transfer. NESTFUL and API-Bank remain refusal evidence; eight other benchmark paths are supplementary interoperability audits.",
       "slide-generation manifest retains the current comparator evidence boundary")


def main() -> None:
    validate_sources()
    validate_live()
    validate_natural_preflight()
    validate_natural_live()
    validate_natural_replication()
    validate_portfolio_live()
    validate_guarded_composite()
    validate_optimizer_head_to_head()
    validate_continuation_replay()
    validate_nestful()
    validate_demo_suite()
    validate_multidomain_preflight()
    validate_offline_comparator()
    validate_manifest()
    validate_claim_boundaries()
    validate_publication()
    validate_github_workflow_families()
    validate_external_benchmarks()
    validate_slide_generation()
    validate_slides()
    validate_no_secrets()
    summary = {
        "validator": "paper/scripts/validate_artifacts.py",
        "checks_passed": len(checks),
        "checks_failed": len(errors),
        "passed": not errors,
        "failures": errors,
    }
    (PAPER / "results/validation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for item in checks:
        print(f"[ok] {item}")
    for item in errors:
        print(f"[FAIL] {item}")
    print(f"\n{len(checks)} checks passed; {len(errors)} failed")
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
