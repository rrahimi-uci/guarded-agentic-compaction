"""Derive a narrower research candidate from retained pilot development data.

No new model calls, calibration, admission, or final-task quality measurement.
The candidate is frozen for subsequent protocol design, not deployed.
"""
from dataclasses import asdict
import json
from pathlib import Path
import tarfile

from adaptive_pilot import ROOT, OUT as PILOT, digest, write
from adaptive_pilot_discovery import convert
from adaptive_pilot_runtime import INSTRUCTIONS, registry
from adaptive_campaign_budget import MODEL
from archive_adaptive_pilot import verify
from guarded_agentic_compaction.capture.manifests import build_manifest
from guarded_agentic_compaction.evaluation.splits import Splits
from guarded_agentic_compaction.grc.compile import GrcConfig, compile_grc
from guarded_agentic_compaction.grc.contracts import induce_guard, induce_verifier
from guarded_agentic_compaction.schema.effects import EffectCatalog

OUT = ROOT / "paper/results/adaptive_prefix_validation"


def build():
    verify()
    seal = json.loads((PILOT / "seal.json").read_text())
    catalog = EffectCatalog.from_dict({"version": 1, "name": "pooled-pinned-readonly-bird", "tools": {
        name: {"effect": "READ_LOCAL", "capabilities": ["speculatable", "replayable", "cacheable"],
               "key": keys, "resource": "pinned-bird-database-at-entry"}
        for name, keys in {"list_tables": [], "get_schema": ["table_names"], "run_query": ["sql"]}.items()}})
    manifest = build_manifest(commit=seal["source_hashes"]["paper/scripts/adaptive_pilot.py"], model=MODEL,
        prompt=INSTRUCTIONS, tools=registry()["tools"], policy="exploratory-pilot-no-admission",
        guardrails="read-only immutable SQLite", catalog=catalog, entry_contract_version="pooled-bird-database-v1")
    episodes = []
    with tarfile.open(PILOT / "raw_evidence.tar.gz", "r:gz") as archive:
        for task in seal["tasks"]:
            raw = json.load(archive.extractfile(f"v2/{task['question_id']}-baseline/result.json"))
            episodes.append(convert(raw, manifest, seal["database_sha256"][task["db_id"]]))
    groups = lambda role: frozenset(f"bird-corrected:{t['question_id']}" for t in seal["tasks"] if t["discovery_split"] == role)
    splits = Splits(train=groups("train"), dev=groups("dev"), seed=20261106)
    config = GrcConfig(entry_schema=("database",), partition_by=(), w_min=1, w_max=1, b_min=1, s_min=5,
        min_days=1, max_candidates=1, max_artifacts=1, freeze_one_candidate_before_calibration=True,
        synthesize_composites=False, mode="replay", seed=20261106, owner="exploratory-prefix-validation")
    result = compile_grc(episodes, catalog, splits, manifest, config, sandbox=None, perturbations=())
    candidates = []
    for candidate, family in zip(result.candidates, result.mining.families):
        row = candidate.as_dict()
        synth = candidate.synthesis
        if synth and synth.ok:
            windows = [w for w in family.windows if w.group_id in splits.train]
            row["program"] = synth.program.to_dict()
            row["hard_guard"] = induce_guard(synth.program, windows, manifest, catalog, partition_by=()).to_dict()
            row["verifier"] = induce_verifier(synth.program, windows, synth.names, catalog).to_dict()
            row["training_groups"] = sorted({w.group_id for w in windows})
            row["challenge"] = asdict(candidate.challenge) if candidate.challenge else None
        candidates.append(row)
    if result.artifacts:
        raise AssertionError("empty calibration must not emit an artifact")
    source_files = [Path(__file__).resolve(), ROOT / "paper/scripts/adaptive_pilot_discovery.py"]
    source_files += sorted((ROOT / "src/guarded_agentic_compaction").rglob("*.py"))
    return {"schema": "gac-adaptive-one-call-candidate-v1", "provider_calls": 0,
        "status": "RESEARCH_CANDIDATE_ONLY_NO_CALIBRATION_NO_ADMISSION", "artifacts_emitted": 0,
        "pilot_seal_sha256": digest(PILOT / "seal.json"), "pilot_archive_sha256": digest(PILOT / "raw_evidence.tar.gz"),
        "source_hashes": {str(p.relative_to(ROOT)): digest(p) for p in source_files},
        "manifest": asdict(manifest), "catalog": catalog.model_dump(mode="json"), "splits": splits.manifest(),
        "config": asdict(config), "report": result.report(), "candidates": candidates,
        "scheduled": len(seal["tasks"]), "converted": len(episodes),
        "incorrect_baselines_retained": sum(ep.outcome.task_success is False for ep in episodes),
        "failed_baselines_retained": sum(ep.attributes["attempt_status"] == "failed" for ep in episodes),
        "representation": "Original payload JSON strings; no runtime normalization change.",
        "change_from_pilot": "Posthoc development change: minimum saved requests 2 to 1 and window length fixed at 1. Original two-call rejection retained unchanged.",
        "limitations": ["Same 36 exploratory pilot IDs; none becomes fresh calibration/test evidence.",
            "All outcomes enter conversion; compiler qualification and window rejections remain explicit.",
            "Replay validation does not evaluate final answers or natural distribution shift.",
            "No sandbox perturbation suite or learned-gate value demonstrated.",
            "A handwritten one-call wrapper can implement the same action; no automatic-compilation advantage established.",
            "Historical manifest documents derivation only; any new runtime needs explicit compatibility review and fresh calibration."]}


if __name__ == "__main__":
    report = build()
    write(OUT / "candidate.json", report)
    print(report["report"])
