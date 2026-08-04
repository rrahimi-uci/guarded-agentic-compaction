#!/usr/bin/env python3
"""Fail-closed integrity and claim audit for the publication artifact."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tomllib
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
    ok(aggregate == data.get("aggregate"),
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
    ok(base_compiled == data.get("baseline_vs_compiled"),
       "natural-workflow baseline-versus-compiler statistics recompute")
    ok(base_macro == data.get("baseline_vs_macro"),
       "natural-workflow baseline-versus-macro statistics recompute")
    ok(macro_compiled == data.get("macro_vs_compiled"),
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
    ok(study.aggregate_runs(recomputed) == data.get("aggregate"),
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
    ok(paired == data.get("paired_test"),
       "replication baseline-versus-compiler statistics recompute")
    ok(paired_macro == data.get("paired_macro_test"),
       "replication baseline-versus-macro statistics recompute")
    ok(macro_vs_compiled == data.get("paired_macro_vs_compiled"),
       "replication macro-versus-compiler statistics recompute")
    ok(study.determinism_analysis(evaluation) == data.get("determinism"),
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
        "supplementary/reviewer-report.md", "supplementary/quality-assessment.md",
        "supplementary/natural-live-study-protocol.md",
        "results/github_natural_replication/preflight.json",
        "results/github_natural_replication/results.json",
        "results/github_natural_replication/discovery_checkpoint.json",
        "results/github_natural_live/results.json",
        "results/github_natural_live/smoke.json",
        "generated_figures/live_efficiency.pdf", "generated_figures/paired_test.pdf",
        "generated_figures/gate_support.pdf", "generated_figures/pilot_ablation.pdf",
        "generated_figures/natural_live_comparison.pdf",
        "tables/natural_live_results.tex",
        "tables/natural_replication_results.tex",
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
            pdf_text = subprocess.run(
                ["pdftotext", str(PAPER / f"build/{build}.pdf"), "-"], check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            ).stdout
            # Assert the current title, not the method name: the phrase "Guarded Agentic
            # Compaction" still appears in the body where the method is defined, so
            # checking it would pass even if the title were dropped entirely.
            for phrase in ("When Traces Are Not Enough", "Guarded Compilation of Tool-Using",
                           "NESTFUL",
                           "Expanded natural-order Tier-2 replication",
                           "GEPA",
                           "Limitations and Threats to Validity",
                           "Reproducibility Details"):
                ok(phrase.lower() in pdf_text.lower(),
                   f"{build}: compiled PDF contains: {phrase}")
            # The architecture figure and every algorithm must actually reach the page.
            # Algorithm 1's caption was retitled when it was corrected to describe the
            # end-to-end pipeline rather than one function; match the current wording.
            for phrase in ("System architecture", "end-to-end pipeline an operator runs",
                           "hand-written composite tool",
                           "typed argument provenance",
                           "fixed-grid exact selective admission",
                           "boundary-time admission"):
                ok(phrase.lower() in pdf_text.lower(),
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
        if not path.is_file() or path.suffix in excluded_suffixes:
            continue
        data = path.read_bytes()
        if any(pattern.search(data) for pattern in patterns):
            findings.append(str(path.relative_to(ROOT)))
    ok(not findings, f"publication tree contains no API-secret-shaped value ({findings})")


def main() -> None:
    validate_sources()
    validate_live()
    validate_natural_preflight()
    validate_natural_live()
    validate_natural_replication()
    validate_continuation_replay()
    validate_nestful()
    validate_demo_suite()
    validate_offline_comparator()
    validate_manifest()
    validate_claim_boundaries()
    validate_publication()
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
