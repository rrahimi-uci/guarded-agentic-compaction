"""Reconstruct primary discovery selection and calibration labels without providers.

This is a retrospective accounting audit, not a recalibration or new certificate.
Run `build` with the retained public snapshot; `verify` needs only shipped files.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import ExitStack
import hashlib
import importlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
for directory in (ROOT, ROOT / "src", ROOT / "paper/scripts"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
OUT = ROOT / "paper/results/calibration_population_audit"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def disposition(eligible: bool, role: str | None) -> str:
    if not eligible:
        if role is not None:
            raise ValueError("ineligible discovery record assigned to a split")
        return "excluded_by_discovery_filter"
    return role or "eligible_unused"


def audit_family(name: str) -> dict:
    import recompile_with_challenge as retained
    import github_live_study as fixed
    import github_workflow_family_study as families
    import second_model_replication as second
    from guarded_agentic_compaction.grc.calibrate import GateFeatures
    from guarded_agentic_compaction.registry.store import Registry

    compiler = importlib.import_module("guarded_agentic_compaction.grc.compile")
    driver = fixed if name == "issue_type" else families
    reconstruction = second if name == "issue_type" else families
    original_reconstruct = reconstruction.reconstruct_discovery
    original_compile = driver.compile_grc
    original_samples = compiler._calibration_samples
    captured: dict = {}
    calibrations = []

    def reconstruct(*args, **kwargs):
        runs = original_reconstruct(*args, **kwargs)
        captured["runs"] = runs
        return runs

    def compile_call(*args, **kwargs):
        captured["splits"] = args[2]
        captured["catalog"] = args[1]
        return original_compile(*args, **kwargs)

    def samples(*args, **kwargs):
        labels = original_samples(*args, **kwargs)
        if not kwargs["include_perturbations"]:
            calibrations.append({"program": args[0], "guard": args[1],
                                 "features": args[6], "labels": labels, "args": args})
        return labels

    with ExitStack() as stack:
        stack.enter_context(patch.object(reconstruction, "reconstruct_discovery", reconstruct))
        stack.enter_context(patch.object(driver, "compile_grc", compile_call))
        stack.enter_context(patch.object(compiler, "_calibration_samples", samples))
        result, _, _, _ = retained.recompile(name, with_challenge=False)

    candidates = [c for c in result.candidates if "gate_calibration_samples" in c.notes]
    if len(candidates) != len(calibrations):
        raise ValueError("candidate/calibration capture mismatch")
    spec = retained.ARTIFACTS[name]
    historical = json.loads(spec["retained"].read_text())
    if captured["splits"].manifest() != historical["compiler"]["splits"]:
        raise ValueError("reconstructed split differs from retained study")
    registry = Registry.load(spec["retained_registry"])
    saved = registry.by_id(spec["artifact_id"])
    rebuilt = next(a for a in result.artifacts if a.artifact_id == spec["artifact_id"])
    if saved is None or saved.program.to_dict() != rebuilt.program.to_dict():
        raise ValueError("retained program not reproduced")
    reproduced = {key: getattr(saved, key).to_dict() == getattr(rebuilt, key).to_dict()
                  for key in ("program", "guard", "gate")}

    rows = []
    for run in captured["runs"]:
        eligible = (fixed.compiler_eligible(run, second.TASK_DESIGN)
                    if name == "issue_type" else
                    run.condition == "discovery" and bool(run.quality["overall"]))
        role = captured["splits"].role_of(run.episode.group_id)
        rows.append({"record_number": run.issue_number, "group_id": run.episode.group_id,
                     "discovery_exact": bool(run.quality["overall"]),
                     "quality": run.quality, "disposition": disposition(eligible, role),
                     "entry_state": run.episode.entry_state, "day": run.episode.envelope.day,
                     "candidates": {}})

    candidate_rows = []
    for rec, data in zip(candidates, calibrations):
        if rec.gate is None:
            raise ValueError("captured candidate lacks a calibrated gate")
        selected = rec.candidate_id == saved.artifact_id
        guard = saved.guard if selected else data["guard"]
        gate = saved.gate if selected else rec.gate
        if selected:
            call_args = list(data["args"])
            call_args[:3] = [saved.program, saved.guard, saved.verifier]
            call_args[6] = GateFeatures.from_dict(saved.gate.features_spec)
            data["labels"] = original_samples(*call_args, include_perturbations=False)
        labels = {}
        for sample in data["labels"]:
            labels.setdefault(sample.group, []).append(sample)
        features = GateFeatures.from_dict(gate.features_spec)
        for row, run in zip(rows, captured["runs"]):
            context = compiler._calibration_guard_context(guard, run.episode,
                                                          captured["catalog"])
            reasons = guard.evaluate(run.episode.entry_state, context)
            accepts, score = gate.accepts(features.raw(run.episode.entry_state,
                                                       day=run.episode.envelope.day))
            group_labels = labels.get(run.episode.group_id, [])
            row["candidates"][rec.candidate_id] = {
                "hard_guard_reasons": list(reasons), "gate_accepts": accepts,
                "score": score, "entry_guard_and_gate_pass": not reasons and accepts,
                "historical_label_count": len(group_labels),
                "historical_replay_violation": (any(s.violation for s in group_labels)
                                                 if group_labels else None),
                "historical_unproductive": (any(s.unproductive for s in group_labels)
                                             if group_labels else None),
                "final_continuation_calibrated": False,
            }
        missing = [r["record_number"] for r in rows if r["disposition"] == "calibration"
                   and not r["candidates"][rec.candidate_id]["historical_label_count"]]
        excluded_pass = [r["record_number"] for r in rows
                         if r["disposition"] == "excluded_by_discovery_filter"
                         and r["candidates"][rec.candidate_id]["entry_guard_and_gate_pass"]]
        candidate_rows.append({"candidate_id": rec.candidate_id, "stage": rec.stage,
                               "rejected": rec.rejected, "selected_artifact": selected,
                               "guard_gate_source": "retained_registry" if selected else "current_code_reconstruction",
                               "historical_calibration_groups": len(labels),
                               "calibration_groups_without_labels": missing,
                               "excluded_records_passing_entry_guard_and_gate": excluded_pass,
                               "threshold": gate.threshold,
                               "retired": gate.retire})
    return {"family": name, "retained_artifact_reproduction": reproduced,
            "checkpoint_path": str(spec["checkpoint"].relative_to(ROOT)),
            "study_path": str(spec["retained"].relative_to(ROOT)),
            "registry_path": str((spec["retained_registry"] / "registry.json").relative_to(ROOT)),
            "split_manifest": captured["splits"].manifest(),
            "discovery_records": len(rows),
            "disposition_counts": dict(sorted(Counter(r["disposition"] for r in rows).items())),
            "candidates": candidate_rows, "records": rows}


def validate(report: dict) -> None:
    if report["provider_calls"] != 0 or report["new_certificate"]:
        raise ValueError("audit must not claim provider evidence or certification")
    for family in report["families"]:
        rows = family["records"]
        if len(rows) != family["discovery_records"] or len({r["group_id"] for r in rows}) != len(rows):
            raise ValueError("missing or duplicate discovery groups")
        counts = dict(sorted(Counter(r["disposition"] for r in rows).items()))
        if counts != family["disposition_counts"]:
            raise ValueError("disposition counts inconsistent")
        for role, groups in family["split_manifest"]["groups"].items():
            if set(groups) != {r["group_id"] for r in rows if r["disposition"] == role}:
                raise ValueError("split membership inconsistent")
        for candidate in family["candidates"]:
            key = candidate["candidate_id"]
            observed = [r["record_number"] for r in rows
                        if r["disposition"] == "excluded_by_discovery_filter"
                        and r["candidates"][key]["entry_guard_and_gate_pass"]]
            if observed != candidate["excluded_records_passing_entry_guard_and_gate"]:
                raise ValueError("excluded-eligible accounting inconsistent")
            missing = [r["record_number"] for r in rows if r["disposition"] == "calibration"
                       and not r["candidates"][key]["historical_label_count"]]
            if missing != candidate["calibration_groups_without_labels"]:
                raise ValueError("missing-window accounting inconsistent")
            labeled = [r for r in rows if r["candidates"][key]["historical_label_count"]]
            if len(labeled) != candidate["historical_calibration_groups"]:
                raise ValueError("calibration denominator inconsistent")
            if any(r["disposition"] != "calibration" for r in labeled):
                raise ValueError("calibration label outside calibration split")
            if any(r["candidates"][key]["final_continuation_calibrated"] for r in rows):
                raise ValueError("replay labels cannot certify continuations")


def render(report: dict) -> str:
    lines = ["# Primary calibration population audit", "",
             "Provider-free retrospective reconstruction; no new certificate or final-answer experiment.", "",
             "All 396 primary discovery records are accounted for, including eligible unused records. "
             "All candidates reaching calibration are included, not only the selected artifacts.", "",
             "| Family | Discovery | Filter-excluded | Eligible unused | Train / dev / calibration |",
             "|---|---:|---:|---:|---|"]
    for f in report["families"]:
        c = f["disposition_counts"]
        lines.append(f"| {f['family']} | {f['discovery_records']} | {c.get('excluded_by_discovery_filter', 0)} | "
                     f"{c.get('eligible_unused', 0)} | {c.get('train', 0)} / {c.get('dev', 0)} / {c.get('calibration', 0)} |")
    lines += ["", "| Candidate | Selected | Labeled groups | Missing calibration windows | Excluded records passing entry guard and gate |",
              "|---|---|---:|---|---|"]
    for f in report["families"]:
        for c in f["candidates"]:
            lines.append(f"| {f['family']} / `{c['candidate_id']}` | {c['selected_artifact']} | "
                         f"{c['historical_calibration_groups']} | {c['calibration_groups_without_labels']} | "
                         f"{c['excluded_records_passing_entry_guard_and_gate']} |")
    lines += ["", "## Interpretation and limits", "",
              "Selected programs reproduce the retained programs. Guard and gate reproduction is "
              "reported separately in JSON: current code can induce different hulls from historical code. "
              "For selected artifacts, eligibility and replay relabeling use the **retained registry's** "
              "guard, verifier and gate, not a replacement produced by current compilation. Other calibrated "
              "candidates are explicitly labeled current-code reconstructions. Split/window membership is "
              "reconstructed from the retained checkpoints; replay labels are recomputed, not newly observed "
              "provider outcomes. Eligibility uses each original entry state/date, "
              "under compatible manifest/catalog pins. It is a dispatch-precondition diagnostic, "
              "not execution of the substituted agent or proof of a final-answer failure.", "",
              "Excluded baseline failures can pass these preconditions. Their absence from calibration "
              "cannot be justified by claiming the deployed guard necessarily excludes them. Historical "
              "replay labels must not be promoted to end-to-end labels, and this audit does not certify "
              "the unfiltered deployment population. Eligible records deliberately unused by the split "
              "are reported separately; their non-use is not itself evidence of outcome filtering.", "",
              "This audit covers the three primary GitHub discovery cohorts and their calibrated candidates. "
              "It does not establish population validity for every supplementary benchmark, independence "
              "of issue groups, or the outcomes of missing counterfactual continuations.", "",
              "## Reproduction", "", "```sh",
              "PYTHONDONTWRITEBYTECODE=1 .venv/bin/python paper/scripts/audit_calibration_population.py build",
              "PYTHONDONTWRITEBYTECODE=1 .venv/bin/python paper/scripts/audit_calibration_population.py verify",
              "```", "", "Build uses the retained checksum-verified public snapshot and reconstructs "
              "historical splits and replay labels. Verify checks shipped source hashes and accounting "
              "without fetching data or making model calls. `report.json` includes every record and candidate.", ""]
    return "\n".join(lines)


def verify(report: dict) -> None:
    """Check source integrity and recompute saved-artifact eligibility, without data loading."""
    from guarded_agentic_compaction.grc.calibrate import GateFeatures
    from guarded_agentic_compaction.registry.store import Registry

    validate(report)
    for source, expected in report["source_hashes"].items():
        if digest(ROOT / source) != expected:
            raise ValueError(f"source hash mismatch: {source}")
    for family in report["families"]:
        study = json.loads((ROOT / family["study_path"]).read_text())
        if family["split_manifest"] != study["compiler"]["splits"]:
            raise ValueError("retained study split differs")
        checkpoint = json.loads((ROOT / family["checkpoint_path"]).read_text())
        original = {r["issue_number"]: r for r in checkpoint["results"]}
        if set(original) != {r["record_number"] for r in family["records"]}:
            raise ValueError("checkpoint record population differs")
        registry = Registry.load(ROOT / family["registry_path"])
        selected = next(c for c in family["candidates"] if c["selected_artifact"])
        artifact = registry.by_id(selected["candidate_id"])
        if artifact is None or selected["guard_gate_source"] != "retained_registry":
            raise ValueError("selected candidate must use retained registry")
        features = GateFeatures.from_dict(artifact.gate.features_spec)
        context = {**artifact.guard.manifest_pins, **artifact.guard.isolation}
        for row in family["records"]:
            if row["quality"] != original[row["record_number"]]["quality"]:
                raise ValueError("checkpoint quality differs")
            reasons = artifact.guard.evaluate(row["entry_state"], context)
            accepts, score = artifact.gate.accepts(features.raw(row["entry_state"], day=row["day"]))
            observed = row["candidates"][artifact.artifact_id]
            if (observed["entry_guard_and_gate_pass"] != (not reasons and accepts)
                    or observed["hard_guard_reasons"] != list(reasons)
                    or observed["gate_accepts"] != accepts
                    or abs(observed["score"] - score) > 1e-10):
                raise ValueError("retained eligibility does not reproduce")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build", "verify"])
    args = parser.parse_args()
    path = OUT / "report.json"
    if args.command == "build":
        import recompile_with_challenge as retained
        families = [audit_family(name) for name in retained.ARTIFACTS]
        paths = {Path(__file__), ROOT / "paper/scripts/recompile_with_challenge.py",
                 ROOT / "paper/scripts/github_live_study.py", ROOT / "paper/scripts/github_workflow_family_study.py",
                 ROOT / "paper/scripts/second_model_replication.py", ROOT / "paper/scripts/recurrence_only_ablation.py"}
        paths.update((ROOT / "src/guarded_agentic_compaction").rglob("*.py"))
        for spec in retained.ARTIFACTS.values():
            paths.update([spec["checkpoint"], spec["retained"], spec["retained_registry"] / "registry.json"])
        report = {"schema": "gac-primary-population-audit-v1", "provider_calls": 0,
                  "new_certificate": False, "families": families,
                  "source_hashes": {str(p.relative_to(ROOT)): digest(p) for p in sorted(paths)}}
        validate(report)
        OUT.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        (OUT / "REPORT.md").write_text(render(report))
    else:
        report = json.loads(path.read_text())
        verify(report)
        if (OUT / "REPORT.md").read_text() != render(report):
            raise ValueError("rendered report differs")
    print(f"{args.command}: primary population audit passed")


if __name__ == "__main__":
    main()
