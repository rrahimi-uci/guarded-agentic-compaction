"""Provider-free live-tool and message-shape preflight for the BIRD one-call candidate.

All 36 original exploratory pilot cases stay in the denominator. This checks
the new-policy research candidate against the retained first tool observation
using fresh read-only SQL calls. It does not admit an artifact, call a model,
or grade any new final answer.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import tarfile

from adaptive_pilot_runtime import SQLTools, dumps
from guarded_agentic_compaction.grc.program import program_from_dict
from guarded_agentic_compaction.runtime.facade import FacadeMode, ToolFacade
from guarded_agentic_compaction.runtime.interp import run_program
from guarded_agentic_compaction.schema.artifacts import HardGuard, Verifier
from guarded_agentic_compaction.schema.effects import EffectCatalog

ROOT = Path(__file__).resolve().parents[2]
HISTORICAL = ROOT / "paper/results/adaptive_prefix_validation/candidate.json"
CANDIDATE = ROOT / "paper/results/bird_one_call_continuation_preflight/candidate.json"
PILOT = ROOT / "paper/results/adaptive_compiler_pilot"
OUT = ROOT / "paper/results/bird_one_call_continuation_preflight"


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def canonical_first_message(message):
    """Ignore response-only empty annotations and the arbitrary tool-call ID."""
    value = {k: v for k, v in message.items() if v not in (None, [])}
    calls = value.get("tool_calls") or []
    if set(value) != {"role", "tool_calls"} or value["role"] != "assistant" or len(calls) != 1:
        return None
    call = calls[0]
    if set(call) != {"function", "id", "type"} or call.get("type") != "function":
        return None
    return {"role": "assistant", "function": call["function"], "type": call["type"]}


def synthetic_prefix(result, call_id="call_gac_preflight"):
    if not isinstance(result, dict):
        raise TypeError("prefix result must be a tool result object")
    assistant = {"role": "assistant", "tool_calls": [{"id": call_id, "type": "function",
        "function": {"name": "list_tables", "arguments": "{}"}}]}
    tool = {"role": "tool", "tool_call_id": call_id, "content": dumps(result)}
    return assistant, tool


def build(db_root):
    source = json.loads(CANDIDATE.read_text())
    historical = json.loads(HISTORICAL.read_text())
    seal = json.loads((PILOT / "seal.json").read_text())
    archive_path = PILOT / "raw_evidence.tar.gz"
    if (source["status"] != "RESEARCH_CANDIDATE_ONLY_NO_CALIBRATION_NO_ADMISSION"
            or source["artifacts_emitted"] != 0 or source["candidate"].get("artifact") is not None
            or source["historical_candidate_sha256"] != digest(HISTORICAL)
            or source["pilot_archive_sha256"] != digest(archive_path)
            or source["pilot_seal_sha256"] != digest(PILOT / "seal.json")
            or len(seal["tasks"]) != 36):
        raise ValueError("new-policy candidate or cohort drift")
    if any(digest(ROOT / name) != expected for name, expected in source["source_hashes"].items()):
        raise ValueError("new-policy candidate source drift")
    program_row = source["candidate"]
    program = program_from_dict(program_row["program"])
    guard = HardGuard.from_dict(program_row["hard_guard"])
    old_guard = HardGuard.from_dict(historical["candidates"][0]["hard_guard"])
    verifier = Verifier.from_dict(program_row["verifier"])
    catalog = EffectCatalog.from_dict(source["catalog"])
    if len(program.steps) != 1 or program.tools != ("list_tables",) or program.removed_requests != 1:
        raise ValueError("unexpected candidate program")

    rows = []
    with tarfile.open(archive_path, "r:gz") as archive:
        for task in seal["tasks"]:
            qid, db = task["question_id"], task["db_id"]
            path = db_root / db / f"{db}.sqlite"
            expected = seal["database_sha256"][db]
            before = digest(path)
            if before != expected:
                raise ValueError("database differs from sealed pilot")
            member = archive.extractfile(f"v2/{qid}-baseline/result.json")
            if member is None:
                raise ValueError("missing retained baseline")
            baseline = json.load(member)
            first = baseline["tool_calls"][0]
            recorded_message = baseline["provider_trace"][0]["response"]["choices"][0]["message"]
            observed_shape = canonical_first_message(recorded_message)
            tools = SQLTools(path)
            guard_reasons = guard.evaluate({"database": db}, source["manifest"])
            old_guard_reasons = old_guard.evaluate({"database": db}, source["manifest"])
            result = run_program(program, {"database": db}, ToolFacade(catalog,
                mode=FacadeMode.LIVE, executor=tools.call,
                allowed_tools=("list_tables",), max_calls=1))
            verify_reasons = (verifier.verify(result.outputs, result.env,
                result.provenance, result.effects, len(result.calls)) if result.ok else ["program_failed"])
            generated = synthetic_prefix(result.results[0]) if result.results else None
            shape_equal = (generated is not None and observed_shape == canonical_first_message(generated[0])
                           and generated[1]["content"] == dumps(first["result"]))
            after = digest(path)
            rows.append({"question_id": qid, "db_id": db,
                "first_baseline_action_is_list_tables": first["tool"] == "list_tables",
                "new_policy_manifest_guard_passed": not guard_reasons,
                "historical_guard_rejects_new_policy": bool(old_guard_reasons),
                "program_passed": result.ok and result.calls == [("list_tables", {})]
                                  and len(tools.calls) == 1,
                "verifier_passed": not verify_reasons,
                "tool_result_exact": result.results == [first["result"]],
                "canonical_continuation_shape_equal": shape_equal,
                "database_unchanged": before == after})
    fields = [key for key in rows[0] if key not in {"question_id", "db_id"}]
    totals = {key: sum(row[key] for row in rows) for key in fields}
    return {"schema": "gac-bird-one-call-continuation-preflight-v1",
        "status": "provider-free development feasibility; new-policy research candidate only; no admitted artifact or final-answer test",
        "candidate_sha256": digest(CANDIDATE),
        "historical_candidate_sha256": digest(HISTORICAL),
        "pilot_seal_sha256": digest(PILOT / "seal.json"),
        "pilot_archive_sha256": digest(archive_path),
        "source_sha256": digest(Path(__file__)),
        "scheduled": len(seal["tasks"]), "completed": len(rows), "totals": totals,
        "rows": rows, "provider_calls": 0, "gac_artifacts": 0,
        "independent_test_groups": 0,
        "limitations": ["The candidate and all cases derive from the same exposed 36-case development pilot.",
            "A new development policy generated a new research candidate and manifest; its source/runtime bytes must be sealed before any paid continuation attempt.",
            "Canonical message-shape equality ignores arbitrary call IDs and empty response-only annotations; the provider has not accepted a synthetic message in this study.",
            "First-tool parity and unchanged database bytes do not establish final-answer quality, savings, calibration or GAC admission."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-root", type=Path,
        default=ROOT / "benchmarks/.cache/bird/extract/dev_20240627/dev_databases")
    args = parser.parse_args()
    report = build(args.db_root)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"scheduled": report["scheduled"], "totals": report["totals"]}, sort_keys=True))
