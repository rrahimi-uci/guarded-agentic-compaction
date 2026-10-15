"""Single-mechanism interventions through the real dispatcher; no provider calls.

See experiments/safeguard_mechanisms/README.md for the constructed-workload and
deterministic-continuation boundaries. Nothing here modifies production runtime.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from dataclasses import replace
from importlib.metadata import version
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "paper/scripts"))

from fresh_safeguard_comparison import digest, object_digest, used_ids
from guarded_agentic_compaction.grc.calibrate import (
    GRID, CalibrationSample, GateFeatures, calibrate_gate, fit_gate_model,
    clopper_pearson_upper,
)
from guarded_agentic_compaction.grc.contracts import fit_hull
from guarded_agentic_compaction.grc.dsl import Expr, SynthContext
from guarded_agentic_compaction.grc.program import CallStep, Program
from guarded_agentic_compaction.grc.synthesize import synthesize_binding
from guarded_agentic_compaction.registry.store import Registry
from guarded_agentic_compaction.runtime.dispatch import Dispatcher
from guarded_agentic_compaction.schema.artifacts import (
    Artifact, Gate, GuardClause, HardGuard, Hull, Lifecycle, OutputClause, Verifier,
)
from guarded_agentic_compaction.schema.effects import EffectCatalog
from guarded_agentic_compaction.schema.traces import ExecutionManifest

ARMS = ("baseline", "full", "no_entry_hull", "no_completeness_check", "no_statistical_gate")
LIMITS = (1, 3, 5)
SUITES = ("ordinary", "capped_response_stress")
SIZES = {"discovery": 24, "development": 96, "calibration": 192, "test": 96}
SEED = 20261016
OUT = ROOT / "experiments/safeguard_mechanisms/artifacts"
PROTOCOL = ROOT / "experiments/safeguard_mechanisms/README.md"
CATALOG = EffectCatalog.from_dict({"name": "comment-window-diagnostic", "version": 1,
    "tools": {name: {"effect": "READ_LOCAL", "capabilities": ["speculatable", "replayable"]}
              for name in ("issue.read", "comments.page")}})
MANIFEST = ExecutionManifest(manifest_id="comment-window-diagnostic-v1",
    model="deterministic-comment-counter-v1", prompt_hash="comment-window-v1",
    effect_catalog_version=CATALOG.catalog_version)


def save_new(path: Path, value: Any) -> None:
    """Exclusive creation: never overwrite a seal or earlier attempt."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def load_source() -> tuple[dict, dict]:
    # Lazy import keeps the diagnostic unit tests independent of live extras/data.
    from recurrence_only_ablation import load_store
    return load_store()


def dependencies() -> dict:
    return {name: version(name) for name in ("numpy", "scipy", "scikit-learn", "pandas", "pyarrow")}


def code_hashes() -> dict:
    paths = list((ROOT / "src/guarded_agentic_compaction").rglob("*.py"))
    paths += [Path(__file__), PROTOCOL, ROOT / "paper/scripts/fresh_safeguard_comparison.py",
              ROOT / "paper/scripts/recurrence_only_ablation.py", ROOT / "paper/scripts/github_live_study.py"]
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted(set(paths))}


def exclusions() -> tuple[set[int], dict]:
    from fresh_safeguard_comparison import exclusion_audit
    excluded, hashes = exclusion_audit(ROOT / "paper/results")
    for path in sorted((ROOT / "experiments/fresh_safeguards").rglob("*.json")):
        excluded.update(used_ids(json.loads(path.read_text())))
        hashes[str(path.relative_to(ROOT))] = digest(path)
    return excluded, hashes


def select(store: dict, excluded: set[int], sizes: dict = SIZES) -> dict:
    if set(sizes) != set(SIZES) or any(type(n) is not int or n <= 0 for n in sizes.values()):
        raise ValueError("four nonempty group splits required")
    numbers = sorted((n for n, row in store.items() if n not in excluded and not row.get("pull_request")),
                     key=lambda n: object_digest(["mechanism-cohort", SEED, n]))
    if len(numbers) < sum(sizes.values()):
        raise ValueError("insufficient unused records; no silent reuse")
    result, start = {}, 0
    for role in SIZES:
        result[role] = numbers[start:start + sizes[role]]
        start += sizes[role]
    return result


def cases(numbers: list[int], suites: tuple = SUITES) -> list[dict]:
    return [{"case_id": f"{n}:{suite}:{limit}", "issue_number": n,
             "requested_limit": limit, "suite": suite, "keyword": "error"}
            for n in numbers for suite in suites for limit in LIMITS]


def prepare(out: Path) -> dict:
    store, source = load_source()
    excluded, previous = exclusions()
    splits = select(store, excluded)
    seal = {"schema_version": 1, "source": source, "splits": splits,
            "prior_study_hashes": previous, "excluded_count": len(excluded),
            "code_hashes": code_hashes(), "dependencies": dependencies(),
            "test_cases": cases(splits["test"]), "provider_calls_executed": 0,
            "evidence_tier": "public text with constructed requests; deterministic continuation"}
    save_new(out / "seal.json", seal)
    return {"status": "sealed", "groups": {r: len(v) for r, v in splits.items()},
            "test_cases": len(seal["test_cases"]), "provider_calls_executed": 0}


def verify_seal(out: Path) -> tuple[dict, dict]:
    seal = json.loads((out / "seal.json").read_text())
    if seal["code_hashes"] != code_hashes() or seal["dependencies"] != dependencies():
        raise ValueError("code/protocol/dependency seal mismatch")
    for name, expected in seal["prior_study_hashes"].items():
        if digest(ROOT / name) != expected:
            raise ValueError("prior-study evidence changed")
    store, source = load_source()
    excluded, previous = exclusions()
    if (source != seal["source"] or previous != seal["prior_study_hashes"]
            or len(excluded) != seal["excluded_count"] or select(store, excluded) != seal["splits"]
            or cases(seal["splits"]["test"]) != seal["test_cases"]):
        raise ValueError("source/cohort/request matrix mismatch")
    return seal, store


class SnapshotTools:
    def __init__(self, store: dict, case: dict):
        self.store, self.case, self.calls = store, case, []

    def __call__(self, name: str, args: dict) -> dict:
        self.calls.append({"tool": name, "arguments": copy.deepcopy(args)})
        n = args["issue_number"]
        if n != self.case["issue_number"]:
            raise ValueError("cross-record read")
        row = self.store[n]
        if name == "issue.read":
            return {"issue_number": n, "title": row["title"]}
        if name != "comments.page":
            raise ValueError("unknown tool")
        offset, limit = args["offset"], args["limit"]
        if type(offset) is not int or type(limit) is not int or offset < 0 or not 1 <= limit <= 5:
            raise ValueError("invalid page arguments")
        available = row["comments"][offset:offset + limit]
        returned = available[:2] if self.case["suite"] == "capped_response_stress" else available
        complete = len(returned) == len(available)
        return {"items": [{"position": offset + i + 1, "text": text}
                          for i, text in enumerate(returned)],
                "complete": complete, "next_offset": None if complete else offset + len(returned)}


def reference_reads(tool: SnapshotTools, case: dict) -> dict:
    """Baseline policy consumes the same API and cap, and follows pagination."""
    record = tool("issue.read", {"issue_number": case["issue_number"]})
    items, offset = [], 0
    while offset < case["requested_limit"]:
        page = tool("comments.page", {"issue_number": case["issue_number"],
                    "offset": offset, "limit": case["requested_limit"] - offset})
        items.extend(page["items"])
        if page["complete"]:
            break
        next_offset = page["next_offset"]
        if type(next_offset) is not int or not offset < next_offset <= case["requested_limit"]:
            raise ValueError("non-progressing pagination")
        offset = next_offset
    return {"record": record, "page": {"items": items, "complete": True, "next_offset": None}}


def continue_answer(case: dict, evidence: dict) -> dict:
    """Only the request and released evidence enter this fixed continuation."""
    items = [item for item in evidence["page"]["items"] if item["position"] <= case["requested_limit"]]
    return {"issue_number": evidence["record"]["issue_number"], "comment_count": len(items),
            "matching_positions": [item["position"] for item in items
                                   if case["keyword"].casefold() in item["text"].casefold()]}


def source_answer(case: dict, store: dict) -> dict:
    """Separate source oracle: does not call the tools or continuation."""
    comments = store[case["issue_number"]]["comments"]
    count = min(case["requested_limit"], len(comments))
    pattern = re.compile(re.escape(case["keyword"]), re.IGNORECASE)
    return {"issue_number": case["issue_number"], "comment_count": count,
            "matching_positions": [i + 1 for i in range(count) if pattern.search(comments[i])]}


def discover(numbers: list[int], store: dict) -> tuple[Artifact, list[dict]]:
    observations = []
    for n in numbers:
        case = {"issue_number": n, "requested_limit": 3, "suite": "ordinary", "keyword": "error"}
        tool = SnapshotTools(store, case)
        evidence = reference_reads(tool, case)
        observations.append({"entry": {"issue_number": n, "requested_limit": 3},
                             "calls": tool.calls, "output_digest": object_digest(evidence)})
    envs = [{"z": row["entry"]} for row in observations]
    groups = [str(n) for n in numbers]
    steps = []
    for index, (name, tool) in enumerate((("record", "issue.read"), ("page", "comments.page"))):
        bindings = {}
        for slot in observations[0]["calls"][index]["arguments"]:
            targets = [row["calls"][index]["arguments"][slot] for row in observations]
            result = synthesize_binding(slot, envs, targets, groups, ctx=SynthContext(max_depth=2))
            if not result.ok:
                raise ValueError(f"discovery binding retired: {slot}: {result.reason}")
            bindings[slot] = result.binding
        steps.append(CallStep(name, tool, bindings))
    program = Program(theta=("issue_number", "requested_limit"), steps=steps,
                      outputs={"record": Expr("record"), "page": Expr("page")})
    guard = HardGuard(manifest_pins={"model": MANIFEST.model, "prompt_hash": MANIFEST.prompt_hash},
        clauses=[GuardClause("z.issue_number", "int", Hull("any")),
                 GuardClause("z.requested_limit", "int", fit_hull([3 for _ in observations]))],
        allowed_effects=("READ_LOCAL",))
    verifier = Verifier(clauses=[OutputClause("record", "dict", provenance=("issue.read",)),
        OutputClause("page", "dict", provenance=("comments.page",)),
        OutputClause("page.items", "list", provenance=("comments.page",)),
        OutputClause("page.complete", "bool", hull=Hull("enum", values=(True,)), provenance=("comments.page",))],
        allowed_effects=("READ_LOCAL",), call_counts=(2,))
    return Artifact(artifact_id="fresh-comment-window", name="diagnostic-template-binding-synthesis",
        program=program, guard=guard, verifier=verifier, gate=permissive_gate(), manifest=MANIFEST,
        compatibility_key=MANIFEST.compatibility_key(), lifecycle=Lifecycle.ACTIVE), observations


def permissive_gate() -> Gate:
    return Gate(threshold=1.0, alpha=1.0, risk_upper_bound=1.0,
                notes="UNCERTIFIED diagnostic bypass; no retained calibration certificate")


def arm_artifact(full: Artifact, arm: str) -> Artifact:
    result = copy.deepcopy(full)
    if arm == "no_entry_hull":
        result.guard.clauses = [replace(c, hull=Hull("any")) if c.path == "z.requested_limit" else c
                                for c in result.guard.clauses]
    elif arm == "no_completeness_check":
        result.verifier.clauses = [c for c in result.verifier.clauses if c.name != "page.complete"]
    elif arm == "no_statistical_gate":
        result.gate = permissive_gate()
    elif arm != "full":
        raise ValueError("unknown compiled arm")
    return result


def execute(case: dict, arm: str, artifact: Artifact, store: dict) -> dict:
    tool = SnapshotTools(store, case)
    row = {**case, "arm": arm, "status": "failed", "correct": False, "dispatched": False,
           "fallback": False, "answer": None, "reasons": [], "error": ""}
    try:
        expected = source_answer(case, store)
        if arm == "baseline":
            evidence = reference_reads(tool, case)
        else:
            current = arm_artifact(artifact, arm)
            registry = Registry()
            registry.add(current)
            decision = Dispatcher(registry, CATALOG, mode="live").decide(
                compatibility_key=MANIFEST.compatibility_key(), partition={},
                entry_state={"issue_number": case["issue_number"], "requested_limit": case["requested_limit"]},
                context={"model": MANIFEST.model, "prompt_hash": MANIFEST.prompt_hash}, executor=tool)
            row.update(dispatched=decision.compacted, reasons=list(decision.reasons), score=decision.q)
            if decision.outcome.value == "INCIDENT":
                raise RuntimeError("dispatcher incident")
            row["fallback"] = not decision.compacted
            evidence = decision.outputs if decision.compacted else reference_reads(tool, case)
        answer = continue_answer(case, evidence)
        row.update(status="completed", answer=answer, expected=expected, correct=answer == expected,
                   released_evidence_digest=object_digest(evidence))
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
    row["calls"] = tool.calls
    row["tool_calls"] = len(tool.calls)
    return row


def calibration_rows(numbers: list[int], artifact: Artifact, store: dict, features: GateFeatures) -> list[dict]:
    rows = []
    for case in cases(numbers, ("ordinary",)):
        entry = {key: case[key] for key in ("issue_number", "requested_limit")}
        outcome = execute(case, "full", artifact, store)
        if outcome["status"] != "completed":
            raise ValueError("failed development/calibration execution; stop before held-out test")
        rows.append({"group": str(case["issue_number"]), "episode_id": case["case_id"],
            "features": features.raw(entry),
            "eligible": not artifact.guard.evaluate(entry, {"model": MANIFEST.model, "prompt_hash": MANIFEST.prompt_hash}),
            "unproductive": not outcome["dispatched"] or not outcome["correct"],
            "violation": outcome["dispatched"] and not outcome["correct"],
            "reason": ",".join(outcome["reasons"])})
    return rows


def fit_and_calibrate(artifact: Artifact, splits: dict, store: dict) -> tuple[Artifact, dict]:
    features = GateFeatures.fit(artifact.guard, [])
    development = calibration_rows(splits["development"], artifact, store, features)
    eligible = [CalibrationSample(**r) for r in development if r["eligible"]]
    if not eligible:
        raise ValueError("no eligible development cases")
    model, _ = fit_gate_model(eligible, seed=SEED)
    calibration = calibration_rows(splits["calibration"], artifact, store, features)
    samples = [CalibrationSample(**r) for r in calibration]
    gate = calibrate_gate(samples, features=features, model=model, seed=SEED)
    grid = []
    for threshold in GRID:
        accepted = [r for r in calibration if r["eligible"] and model.score(r["features"]) <= threshold]
        n = len({r["group"] for r in accepted})
        k = len({r["group"] for r in accepted if r["violation"]})
        grid.append({"threshold": threshold, "accepted_groups": n, "violation_groups": k,
                     "upper": clopper_pearson_upper(k, n, 1 - .1 / len(GRID)) if n else 1.0})
    result = copy.deepcopy(artifact)
    result.gate = gate
    return result, {"development": development, "calibration": calibration,
        "gate": gate.to_dict(), "grid": grid,
        "eligible_development_feature_vectors": len({object_digest(s.features) for s in eligible}),
        "calibration_score_values": sorted({model.score(r["features"]) for r in calibration}),
        "fresh_llm_discovery": False, "end_to_end_risk_certified": False}


def summarize(test_cases: list[dict], rows: list[dict]) -> dict:
    expected = {(case["case_id"], arm) for case in test_cases for arm in ARMS}
    index = {(r["case_id"], r["arm"]): r for r in rows}
    if len(index) != len(rows) or set(index) != expected:
        raise ValueError("incomplete, duplicate, or unexpected outcome matrix")
    report = {"status": "completed" if all(r["status"] == "completed" for r in rows) else "completed_with_failures",
              "provider_calls_executed": 0, "live_llm_accuracy_measured": False,
              "end_to_end_risk_certified": False, "suites": {}}
    for suite in SUITES:
        selected = [c for c in test_cases if c["suite"] == suite]
        counts, contrasts = {}, {}
        for arm in ARMS:
            arm_rows = [index[c["case_id"], arm] for c in selected]
            counts[arm] = {"scheduled": len(arm_rows),
                "completed": sum(r["status"] == "completed" for r in arm_rows),
                "failed": sum(r["status"] != "completed" for r in arm_rows),
                "correct": sum(r["correct"] for r in arm_rows),
                "dispatched": sum(r["dispatched"] for r in arm_rows),
                "fallbacks": sum(r["fallback"] for r in arm_rows),
                "wrong_after_dispatch": sum(r["dispatched"] and r["status"] == "completed" and not r["correct"] for r in arm_rows),
                "tool_calls": sum(r["tool_calls"] for r in arm_rows)}
            if arm not in ("baseline", "full"):
                pairs = [(index[c["case_id"], "full"], index[c["case_id"], arm]) for c in selected]
                wins = [(a, b) for a, b in pairs if a["correct"] and not b["correct"]]
                losses = [(a, b) for a, b in pairs if b["correct"] and not a["correct"]]
                contrasts[arm] = {"full_only_correct": len(wins), "ablation_only_correct": len(losses),
                    "full_only_correct_groups": len({a["issue_number"] for a, _ in wins}),
                    "ablation_only_correct_groups": len({a["issue_number"] for a, _ in losses}),
                    "dispatch_disagreements": sum(a["dispatched"] != b["dispatched"] for a, b in pairs),
                    "failed_pairs": sum(a["status"] != "completed" or b["status"] != "completed" for a, b in pairs)}
        report["suites"][suite] = {"issue_groups": len({c["issue_number"] for c in selected}),
                                    "arms": counts, "paired_vs_full": contrasts}
    return report


def render(report: dict) -> str:
    lines = ["# Provider-free mechanism diagnostic", "",
        "Public source text; constructed requests; deterministic reference policy and continuation.",
        "Zero provider calls. These are not live LLM accuracy or deployment failure rates.", ""]
    if report["status"] == "retired_before_test":
        return "\n".join(lines + ["The fresh gate retired. Held-out cases were not evaluated.", ""])
    for suite in SUITES:
        result = report["suites"][suite]
        lines += [f"## {suite}", "", f"{result['issue_groups']} issue groups; three correlated request variants each.", "",
            "| Arm | Correct / scheduled | Failed | Dispatched | Wrong after dispatch | Total tool calls |",
            "| --- | ---: | ---: | ---: | ---: | ---: |"]
        for arm in ARMS:
            r = result["arms"][arm]
            lines.append(f"| {arm} | {r['correct']}/{r['scheduled']} | {r['failed']} | {r['dispatched']} | {r['wrong_after_dispatch']} | {r['tool_calls']} |")
        lines += ["", "Paired differences against full (cases; groups are reported separately in JSON):", ""]
        for arm in ARMS[2:]:
            r = result["paired_vs_full"][arm]
            lines.append(f"- {arm}: full-only correct {r['full_only_correct']}; ablation-only correct {r['ablation_only_correct']}; dispatch disagreements {r['dispatch_disagreements']}; failed pairs {r['failed_pairs']}.")
        lines.append("")
    lines += ["The capped-response suite is constructed distribution shift. Do not pool the suites.",
        "A constant gate or identical gate decisions provides no incremental-gate evidence.",
        "The template, task-scope guard and completeness contract are explicit study design;"]
    return "\n".join(lines + ["this is not evidence that the production compiler discovers these safeguards automatically.", ""])


def run(out: Path) -> dict:
    seal, store = verify_seal(out)
    run_dir = out / "run"
    run_dir.mkdir()  # exclusive attempt lock; preserve interrupted outputs
    artifact, discovery = discover(seal["splits"]["discovery"], store)
    save_new(run_dir / "candidate.json", {"artifact": artifact.to_dict(), "observations": discovery})
    artifact, calibration = fit_and_calibrate(artifact, seal["splits"], store)
    save_new(run_dir / "calibration.json", calibration)
    save_new(run_dir / "arms.json", {arm: arm_artifact(artifact, arm).to_dict() for arm in ARMS if arm != "baseline"})
    if artifact.gate.retire:
        report = {"status": "retired_before_test", "provider_calls_executed": 0, "held_out_cases_executed": 0}
    else:
        rows = []
        with (run_dir / "outcomes.jsonl").open("x") as stream:
            for case in seal["test_cases"]:
                for arm in ARMS:
                    row = execute(case, arm, artifact, store)
                    stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
                    stream.flush()
                    rows.append(row)
        report = summarize(seal["test_cases"], rows)
    report["seal_sha256"] = digest(out / "seal.json")
    report["input_hashes"] = {p.name: digest(p) for p in sorted(run_dir.iterdir()) if p.is_file()}
    save_new(run_dir / "summary.json", report)
    (run_dir / "results.md").write_text(render(report))
    return report


def verify(out: Path) -> dict:
    seal, store = verify_seal(out)
    run_dir = out / "run"
    report = json.loads((run_dir / "summary.json").read_text())
    if report["seal_sha256"] != digest(out / "seal.json"):
        raise ValueError("seal digest mismatch")
    for name, expected in report["input_hashes"].items():
        if digest(run_dir / name) != expected:
            raise ValueError(f"retained artifact digest mismatch: {name}")
    candidate, observations = discover(seal["splits"]["discovery"], store)
    if object_digest(json.loads((run_dir / "candidate.json").read_text())) != object_digest({"artifact": candidate.to_dict(), "observations": observations}):
        raise ValueError("candidate replay mismatch")
    artifact, calibration = fit_and_calibrate(candidate, seal["splits"], store)
    if object_digest(calibration) != object_digest(json.loads((run_dir / "calibration.json").read_text())):
        raise ValueError("calibration replay mismatch")
    arms = {arm: arm_artifact(artifact, arm).to_dict() for arm in ARMS if arm != "baseline"}
    if object_digest(arms) != object_digest(json.loads((run_dir / "arms.json").read_text())):
        raise ValueError("arm isolation mismatch")
    if artifact.gate.retire:
        expected = {"status": "retired_before_test", "provider_calls_executed": 0, "held_out_cases_executed": 0}
    else:
        rows = [json.loads(line) for line in (run_dir / "outcomes.jsonl").read_text().splitlines()]
        replay = [execute(case, arm, artifact, store) for case in seal["test_cases"] for arm in ARMS]
        if rows != replay:
            raise ValueError("outcome replay mismatch")
        expected = summarize(seal["test_cases"], rows)
    if {k: v for k, v in report.items() if k not in ("seal_sha256", "input_hashes")} != expected:
        raise ValueError("summary replay mismatch")
    if (run_dir / "results.md").read_text() != render(report):
        raise ValueError("rendered report mismatch")
    return {"verified": True, "status": expected["status"], "provider_calls_executed": 0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run", "verify"))
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    result = {"prepare": prepare, "run": run, "verify": verify}[args.command](args.out)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
