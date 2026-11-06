"""Provider-free SQL execution parity over all 36 selected pilot programs.

New observations are diagnostics only: historical pilot outcomes stay unchanged.
Live SQL runs only on the parent against hash-pinned immutable databases. A
reference harness receives the same recorded RPC results; it cannot call a model.
"""
import argparse
import ast
import asyncio
from collections import Counter
import json
from pathlib import Path
import tarfile

from adaptive_native_runtime import run_native, upstream_runtime
from adaptive_pilot import ROOT, OUT as PILOT, DBROOT, digest, write
from adaptive_pilot_runtime import SQLTools
from archive_adaptive_pilot import verify

OUT = ROOT / "paper/results/adaptive_prefix_validation"


def recorded_inference(text):
    text = (text or "").strip()
    if text.startswith(("[", "{")):
        for parse in (json.loads, ast.literal_eval):
            try:
                return parse(text)
            except (ValueError, SyntaxError):
                pass
    return text


async def validate(checkout):
    verify()
    seal = json.loads((PILOT / "seal.json").read_text())
    for db, sha in seal["database_sha256"].items():
        if digest(DBROOT / db / f"{db}.sqlite") != sha:
            raise ValueError("database bytes changed")
    rows = []
    with tarfile.open(PILOT / "raw_evidence.tar.gz", "r:gz") as archive, upstream_runtime(checkout) as package:
        for task in seal["tasks"]:
            base = f"v2/{task['question_id']}-agent_jit"
            generated = json.load(archive.extractfile(base + "/candidates.json"))
            original = json.load(archive.extractfile(base + "/result.json"))
            index = generated["selected_index"]
            if index is None:
                rows.append({"question_id": task["question_id"], "status": "no_selected_program"})
                continue
            code = generated["candidates"][index]["code"]
            tools = SQLTools(DBROOT / task["db_id"] / f"{task['db_id']}.sqlite")
            ai = iter([recorded_inference(t["runtime_ai_eval"]["choices"][0]["message"]["content"])
                for t in original["provider_trace"] if "runtime_ai_eval" in t])
            rpc = []
            missing_inference = []
            async def observe(name, arguments):
                row = {"tool": name, "arguments": arguments}
                rpc.append(row)
                if name == "ai_eval":
                    try:
                        result = next(ai)
                    except StopIteration:
                        missing_inference.append(len(rpc) - 1)
                        row["error"] = "LookupError"
                        raise LookupError("no retained inference; no fresh model call allowed")
                else:
                    result = tools.call(name, arguments)
                row["result"] = result
                return result
            try:
                native = await run_native(code, observe, package, timeout=120)
            except Exception as exc:
                native = {"status": "bridge_error", "error": type(exc).__name__}
            cursor = 0
            differences = []
            async def replay(name, arguments):
                nonlocal cursor
                if cursor >= len(rpc):
                    differences.append("extra_reference_call")
                    raise LookupError("reference requested extra call")
                expected = rpc[cursor]
                cursor += 1
                if (name, arguments) != (expected["tool"], expected["arguments"]):
                    differences.append("reference_arguments_differ")
                    raise LookupError("reference RPC differs")
                if "error" in expected:
                    raise LookupError("no retained inference")
                return expected["result"]
            try:
                reference = await run_native(code, replay, package, timeout=120, reference=True)
            except Exception as exc:
                reference = {"status": "bridge_error", "error": type(exc).__name__}
            if cursor != len(rpc):
                differences.append("reference_used_fewer_calls")
            # Two identical bridge failures do not establish executor parity.
            match = native.get("status") in {"ok", "error"} and native == reference and not differences
            row = {"question_id": task["question_id"], "db_id": task["db_id"], "selected_index": index,
                "program_sha256": __import__("hashlib").sha256(code.encode()).hexdigest(),
                "native": native, "reference": reference, "rpc": rpc, "differences": differences,
                "matches": match, "missing_inference": missing_inference,
                "original_status": original["status"], "original_error": original.get("error")}
            rows.append(row)
            print(json.dumps({"question_id": task["question_id"], "matches": match, "status": native["status"],
                              "missing_inference": len(missing_inference)}), flush=True)
    for db, sha in seal["database_sha256"].items():
        if digest(DBROOT / db / f"{db}.sqlite") != sha:
            raise ValueError("database bytes changed during validation")
    report = {"schema": "gac-retained-sql-executor-validation-v1", "provider_calls": 0,
        "pilot_seal_sha256": digest(PILOT / "seal.json"), "pilot_archive_sha256": digest(PILOT / "raw_evidence.tar.gz"),
        "source_hashes": {str(p.relative_to(ROOT)): digest(p) for p in (Path(__file__).resolve(),
            ROOT / "paper/scripts/adaptive_native_runtime.py", ROOT / "experiments/adaptive_prefix_validation/reference_worker.py",
            ROOT / "experiments/adaptive_compiler_pilot/container_worker_native.py")},
        "summary": {"scheduled": len(seal["tasks"]), "matched": sum(r.get("matches", False) for r in rows),
            "native_statuses": dict(Counter(r.get("native", {}).get("status", r.get("status")) for r in rows)),
            "missing_inference": sum(len(r.get("missing_inference", [])) for r in rows)},
        "rows": rows, "scope": "All selected v2 pilot programs. Both harnesses use the same pinned upstream executor; this validates adapter parity, not an independent implementation. Reference replays identical observed SQL and canned inference responses. The retained inference is a fixed response fixture, not proof that prompts or fresh model outputs match. No new quality measurement, no outcome relabeling and no native-browser claim."}
    write(OUT / "executor_sql_validation.json", report)
    print(json.dumps(report["summary"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    asyncio.run(validate(parser.parse_args().checkout.resolve()))
