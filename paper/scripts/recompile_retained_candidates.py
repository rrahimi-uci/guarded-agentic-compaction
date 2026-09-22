"""Provider-free recompilation of retained discovery traces to recover candidate gates.

Two gaps in the retained evidence are closed here without any provider call:

* ``--family pr_outcome|backlog_attention``: the primary studies calibrated two candidates
  on the same 92 groups and serialized only the admitted one; the dominated two-read
  sibling's per-threshold table was dropped. Recompiling from the sealed discovery
  checkpoint with the identical ``GrcConfig`` reproduces both (determinism is checked
  against the retained artifact id and split digest).
* ``--repo pytorch/pytorch``: the cross-repository core protocol retired this repository
  and stored only a 120-character retire note. Recompiling from its discovery checkpoint
  with full retire notes (``grc/compile.py``) recovers the per-threshold rows.

Outputs go to ``paper/results/iclr_revision/`` and never overwrite a retained study file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "paper" / "results"
OUT = RESULTS / "iclr_revision"
sys.path.insert(0, str(ROOT / "paper" / "scripts"))

MODEL = "gpt-5.6-luna"
CHECKPOINTS = {
    "pr_outcome": RESULTS / "github_workflow_families" / "pr_outcome" / "pilot_v1" / "discovery_checkpoint.json",
    "backlog_attention": RESULTS / "github_workflow_families" / "backlog_attention" / "final" / "discovery_checkpoint.json",
}
RETAINED = {
    "pr_outcome": RESULTS / "github_workflow_families" / "pr_outcome" / "final" / "results.json",
    "backlog_attention": RESULTS / "github_workflow_families" / "backlog_attention" / "final" / "results.json",
}


def _capture(module: Any) -> list[Any]:
    """Wrap ``module.compile_grc`` so the full ``CompileResult`` is retained."""
    captured: list[Any] = []
    real = module.compile_grc

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        result = real(*args, **kwargs)
        captured.append(result)
        return result

    module.compile_grc = wrapped
    return captured


def _candidate_payload(rec: Any) -> dict[str, Any]:
    gate = rec.gate
    return {
        "candidate_id": rec.candidate_id,
        "tools": list(rec.tools),
        "stage": rec.stage,
        "rejected": rec.rejected,
        "support_groups": rec.support_groups,
        "removed_requests": rec.removed_requests,
        "gate": None if gate is None else {
            "retire": gate.retire,
            "threshold": gate.threshold,
            "alpha": gate.alpha,
            "delta": gate.delta,
            "n_accepted": gate.n_accepted,
            "n_calibration_groups": gate.n_calibration_groups,
            "observed_violations": gate.observed_violations,
            "risk_upper_bound": gate.risk_upper_bound,
            "coverage": gate.coverage,
            "admissible": list(gate.admissible),
            "grid_rows": _grid_rows(gate.notes),
            "notes": gate.notes,
        },
    }


def _grid_rows(notes: str) -> list[dict[str, Any]]:
    import ast

    marker = "grid rows: "
    return ast.literal_eval(notes.split(marker, 1)[1].strip()) if marker in notes else []


def recompile_family(name: str) -> dict[str, Any]:
    import github_workflow_family_study as fam

    spec = fam.FAMILIES[name]
    store, _audit = fam.load_store()
    catalog = fam.make_catalog(spec)
    tools = fam.make_tools(spec, store)
    source_manifest = fam.make_manifest(spec, MODEL, tools, catalog, "source", instructions=spec.discovery_prompt)
    continuation_manifest = fam.make_manifest(spec, MODEL, (), catalog, "pre-model", instructions=spec.prompt)
    checkpoint = json.loads(CHECKPOINTS[name].read_text())
    discovery = fam.reconstruct_discovery(spec, checkpoint, store=store, manifest=source_manifest)
    captured = _capture(fam)
    registry, compilation = fam.compile_artifact(
        spec, discovery, catalog=catalog, source_manifest=source_manifest, continuation_manifest=continuation_manifest
    )
    result = captured[-1]
    retained = json.loads(RETAINED[name].read_text())["compiler"]
    admitted_id = compilation["artifact"]["artifact_id"]
    determinism = {
        "artifact_id": {"recompiled": admitted_id, "retained": retained["artifact"]["artifact_id"], "match": admitted_id == retained["artifact"]["artifact_id"]},
        "splits_digest": {"recompiled": compilation["splits"]["digest"], "retained": retained["splits"]["digest"], "match": compilation["splits"]["digest"] == retained["splits"]["digest"]},
        "risk_upper_bound": {"recompiled": compilation["artifact"]["gate"]["risk_upper_bound"], "retained": retained["artifact"]["gate"]["risk_upper_bound"]},
    }
    return {
        "family": name,
        "checkpoint": str(CHECKPOINTS[name].relative_to(ROOT)),
        "provider_calls": 0,
        "determinism": determinism,
        "report": result.report(),
        "candidates": [_candidate_payload(rec) for rec in result.candidates],
        "rejection_by_stage": dict(result.rejection_by_stage),
    }


def recompile_pytorch() -> dict[str, Any]:
    import github_multirepo_pr_outcome_core as core

    repository = "pytorch/pytorch"
    source = core.DEFAULT_SOURCES[repository]
    slug = core._repo_slug(repository)
    source_manifest = json.loads((core.DATA_ROOT / slug / "source_manifest.json").read_text())
    store, _audit = core.load_store(source, source_manifest)
    source_revision = f"{source_manifest['dataset']}@{source_manifest['revision']}"
    catalog = core.make_catalog(repository)
    tools = core.make_tools(source_revision, store)
    source_driver_manifest = core.make_manifest(repository, source_revision, MODEL, tools, catalog, "source", instructions=core.SPEC.discovery_prompt)
    continuation_manifest = core.make_manifest(repository, source_revision, MODEL, (), catalog, "pre-model", instructions=core.SPEC.prompt)
    checkpoint_path = RESULTS / "github_multirepo_pr_outcome_core" / "repos" / slug / "discovery_checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text())
    discovery = core.reconstruct_discovery(repository, source_revision, checkpoint, store=store, manifest=source_driver_manifest)
    captured = _capture(core)
    error = None
    try:
        core.compile_artifact(
            repository, discovery, catalog=catalog, source_manifest=source_driver_manifest,
            continuation_manifest=continuation_manifest, seed=20260807,
        )
    except RuntimeError as exc:  # the retained run retired here too
        error = str(exc).splitlines()[0]
    result = captured[-1]
    retained_error = json.loads((RESULTS / "github_multirepo_pr_outcome_core" / "results.json").read_text())["repositories"][repository]["error"]
    candidates = [_candidate_payload(rec) for rec in result.candidates]
    mechanism = None
    for cand in candidates:
        gate = cand["gate"]
        if gate and gate["retire"]:
            rows = gate["grid_rows"]
            if rows and all(r["n"] == 0 for r in rows):
                mechanism = "n_eta = 0 at every eta: no calibration group was accepted at any threshold (the frozen score q exceeded every grid value or the hard guard rejected every group)"
            elif rows and any(r["n"] > 0 and r["violations"] == r["n"] for r in rows):
                mechanism = "k_eta = n_eta at every non-empty threshold: every accepted calibration group violated the replay contract"
            else:
                mechanism = "mixed: see grid_rows"
    return {
        "repository": repository,
        "checkpoint": str(checkpoint_path.relative_to(ROOT)),
        "provider_calls": 0,
        "recompile_error": error,
        "retained_error_prefix": retained_error[:200],
        "retained_error_reproduced": (error or "").startswith("compiler emitted no admitted artifact"),
        "report": result.report(),
        "candidates": candidates,
        "rejection_by_stage": dict(result.rejection_by_stage),
        "mechanism": mechanism,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=sorted(CHECKPOINTS))
    parser.add_argument("--repo", choices=["pytorch/pytorch"])
    args = parser.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    if args.family:
        payload = recompile_family(args.family)
        path = OUT / f"recompiled_candidates_{args.family}.json"
    elif args.repo:
        payload = recompile_pytorch()
        path = OUT / "pytorch_core_recompile.json"
    else:
        parser.error("pass --family or --repo")
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")
    print(f"wrote {path.relative_to(ROOT)}")
    if "determinism" in payload:
        print(json.dumps(payload["determinism"], indent=2))
    if "mechanism" in payload:
        print("mechanism:", payload["mechanism"])
    print(payload["report"])


if __name__ == "__main__":
    main()
