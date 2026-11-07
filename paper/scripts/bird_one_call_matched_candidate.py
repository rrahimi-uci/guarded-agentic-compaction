"""Rebuild the one-call BIRD research candidate for a new continuation policy.

This is provider-free development reuse of the same 36 exposed pilot traces.
Calibration remains empty, so no artifact is admitted. The new policy hash is
explicit; the historical candidate's guard must not be borrowed unchanged.
"""
from dataclasses import asdict
import json
from pathlib import Path
import tarfile

from adaptive_pilot import ROOT, digest
from adaptive_pilot_discovery import convert
from adaptive_pilot_runtime import INSTRUCTIONS, registry
from adaptive_campaign_budget import MODEL
from guarded_agentic_compaction.capture.manifests import build_manifest
from guarded_agentic_compaction.evaluation.splits import Splits
from guarded_agentic_compaction.grc.compile import GrcConfig, compile_grc
from guarded_agentic_compaction.grc.contracts import induce_guard, induce_verifier
from guarded_agentic_compaction.schema.effects import EffectCatalog

PILOT = ROOT / "paper/results/adaptive_compiler_pilot"
HISTORICAL = ROOT / "paper/results/adaptive_prefix_validation/candidate.json"
OUT = ROOT / "paper/results/bird_one_call_continuation_preflight/candidate.json"
POLICY = "bird-one-call-synthetic-continuation-development-v1"


def build():
    seal = json.loads((PILOT / "seal.json").read_text())
    historical = json.loads(HISTORICAL.read_text())
    if (historical["pilot_seal_sha256"] != digest(PILOT / "seal.json")
            or historical["pilot_archive_sha256"] != digest(PILOT / "raw_evidence.tar.gz")
            or len(seal["tasks"]) != 36):
        raise ValueError("historical pilot or candidate drift")
    catalog = EffectCatalog.from_dict(historical["catalog"])
    manifest = build_manifest(
        commit=seal["source_hashes"]["paper/scripts/adaptive_pilot.py"],
        model=MODEL, prompt=INSTRUCTIONS, tools=registry()["tools"], policy=POLICY,
        guardrails="read-only immutable SQLite", catalog=catalog,
        entry_contract_version="pooled-bird-database-v1")
    episodes = []
    with tarfile.open(PILOT / "raw_evidence.tar.gz", "r:gz") as archive:
        for task in seal["tasks"]:
            member = archive.extractfile(f"v2/{task['question_id']}-baseline/result.json")
            if member is None:
                raise ValueError("missing fixed baseline record")
            episodes.append(convert(json.load(member), manifest,
                seal["database_sha256"][task["db_id"]]))
    groups = lambda role: frozenset(f"bird-corrected:{task['question_id']}"
        for task in seal["tasks"] if task["discovery_split"] == role)
    splits = Splits(train=groups("train"), dev=groups("dev"), seed=20261106)
    config = GrcConfig(entry_schema=("database",), partition_by=(), w_min=1, w_max=1,
        b_min=1, s_min=5, min_days=1, max_candidates=1, max_artifacts=1,
        freeze_one_candidate_before_calibration=True, synthesize_composites=False,
        mode="replay", seed=20261106, owner="bird-one-call-continuation-development")
    result = compile_grc(episodes, catalog, splits, manifest, config,
        sandbox=None, perturbations=())
    if result.artifacts or len(result.candidates) != 1 or len(result.mining.families) != 1:
        raise ValueError("new policy unexpectedly admitted or changed candidates")
    candidate, family = result.candidates[0], result.mining.families[0]
    if candidate.synthesis is None or not candidate.synthesis.ok:
        raise ValueError("one-call program did not synthesize")
    program = candidate.synthesis.program
    if program is None or program.to_dict() != historical["candidates"][0]["program"]:
        raise ValueError("new policy changed the compiled program")
    windows = [window for window in family.windows if window.group_id in splits.train]
    guard = induce_guard(program, windows, manifest, catalog, partition_by=())
    verifier = induce_verifier(program, windows, candidate.synthesis.names, catalog)
    row = candidate.as_dict()
    row.update(program=program.to_dict(), hard_guard=guard.to_dict(),
               verifier=verifier.to_dict(),
               training_groups=sorted({window.group_id for window in windows}))
    if row.get("artifact") is not None or row.get("rejected") != "no_calibration_groups":
        raise ValueError("candidate admission state changed")
    sources = [Path(__file__).resolve(), ROOT / "paper/scripts/adaptive_pilot_discovery.py"]
    sources += sorted((ROOT / "src/guarded_agentic_compaction").rglob("*.py"))
    return {"schema": "gac-bird-one-call-matched-candidate-v1",
        "status": "RESEARCH_CANDIDATE_ONLY_NO_CALIBRATION_NO_ADMISSION",
        "policy": POLICY, "provider_calls": 0, "artifacts_emitted": 0,
        "historical_candidate_sha256": digest(HISTORICAL),
        "pilot_seal_sha256": digest(PILOT / "seal.json"),
        "pilot_archive_sha256": digest(PILOT / "raw_evidence.tar.gz"),
        "source_hashes": {str(path.relative_to(ROOT)): digest(path) for path in sources},
        "manifest": asdict(manifest), "catalog": catalog.model_dump(mode="json"),
        "splits": splits.manifest(), "config": asdict(config),
        "candidate": row, "report": result.report(),
        "scheduled": len(seal["tasks"]), "converted": len(episodes),
        "limitation": "Same exposed pilot IDs and no calibration. This is a program/continuation development candidate, not deployable GAC or a final-task quality claim."}


if __name__ == "__main__":
    result = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"scheduled": result["scheduled"], "provider_calls": 0,
                      "artifacts_emitted": 0, "candidate_stage": result["candidate"]["stage"]}))
