"""Provider-free recompilation of the three primary live artifacts with the challenge stage on.

Appendix G of the ICLR manuscript discloses two operational caveats about the headline
live artifacts: they were compiled with ``compile_grc(..., sandbox=None, perturbations=())``,
so their compile records carry ``perturbations_claimed: false`` instead of a completed
metamorphic challenge, and registry signature verification was configured off in the
reported runs.  This script closes both caveats without a provider call and without
changing any reported number:

* every artifact is recompiled twice from its sealed discovery checkpoint through the
  retained study's own ``compile_artifact``: once exactly as the study compiled it (the
  *control*, ``sandbox=None, perturbations=()``) and once with ``compile_grc`` receiving a
  sandbox factory and ``DEFAULT_PERTURBATIONS``.  The sandbox is a read-only world over the
  revision-pinned public snapshot whose ``execute`` is the deterministic snapshot tool the
  study already used to reconstruct the checkpoint, so sandbox replay and every
  perturbation family run against the bytes the traces were recorded from;
* before anything is recorded, the challenge recompile is asserted identical to the
  retained artifact in program, splits digest, artifact id, and the 92/0 gate, and
  identical to the control in every field except the challenge evidence itself
  (``evidence.perturbation``, ``evidence.metrics.perturbations_claimed``,
  ``evidence.metrics.sandbox``);
* the artifact is registered in a ``Registry(signing_key=...)``, saved, reloaded with
  ``Registry.load(..., signing_key=...)``, and wrong-key and tampered loads are shown to be
  refused.  The key is a published lab key derived from a fixed string: the property
  demonstrated is that verification runs and passes, not that the key is secret.

The retained study files are never rewritten.  Output:
``paper/results/iclr_revision/recompile_with_challenge.json``.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterator, Sequence

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "paper" / "results"
OUT = RESULTS / "iclr_revision" / "recompile_with_challenge.json"
for path in (ROOT, ROOT / "src", ROOT / "paper" / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from guarded_agentic_compaction.evaluation.perturb import DEFAULT_PERTURBATIONS  # noqa: E402
from guarded_agentic_compaction.registry.store import Registry, RegistryError  # noqa: E402
from guarded_agentic_compaction.schema.artifacts import Artifact  # noqa: E402

MODEL = "gpt-5.6-luna"
SIGNING_KEY_DERIVATION = (
    "guarded-agentic-compaction/paper/results/iclr_revision/recompile_with_challenge/"
    "lab-signing-key/v1"
)
SIGNING_KEY = hashlib.sha256(SIGNING_KEY_DERIVATION.encode()).digest()
WRONG_KEY = hashlib.sha256(b"not-the-lab-signing-key").digest()

ARTIFACTS: dict[str, dict[str, Any]] = {
    "issue_type": {
        "artifact_id": "cand-01-1ebb8b2849c7",
        "checkpoint": RESULTS / "github_natural_replication" / "discovery_checkpoint.json",
        "retained": RESULTS / "github_natural_replication" / "results.json",
        "retained_registry": RESULTS / "github_natural_replication" / "registry",
    },
    "pr_outcome": {
        "artifact_id": "cand-00-a1de3856bb6c",
        "checkpoint": RESULTS / "github_workflow_families" / "pr_outcome" / "pilot_v1" / "discovery_checkpoint.json",
        "retained": RESULTS / "github_workflow_families" / "pr_outcome" / "final" / "results.json",
        "retained_registry": RESULTS / "github_workflow_families" / "pr_outcome" / "final" / "registry",
    },
    "backlog_attention": {
        "artifact_id": "cand-00-99f1b041ed7c",
        "checkpoint": RESULTS / "github_workflow_families" / "backlog_attention" / "final" / "discovery_checkpoint.json",
        "retained": RESULTS / "github_workflow_families" / "backlog_attention" / "final" / "results.json",
        "retained_registry": RESULTS / "github_workflow_families" / "backlog_attention" / "final" / "registry",
    },
}
GATE_FIELDS = (
    "n_calibration_groups", "n_accepted", "observed_violations", "risk_upper_bound",
    "threshold", "retire", "coverage", "alpha", "delta",
)
#: The only artifact fields the challenge stage is allowed to change.
CHALLENGE_EVIDENCE_PATHS = (
    ".evidence.perturbation",
    ".evidence.metrics.perturbations_claimed",
    ".evidence.metrics.sandbox",
    ".evidence.counterexamples",
)
#: Field-level differences between a present-day recompile and the retained file that
#: the control recompile (no sandbox, no perturbations) carries as well.  They come from
#: checkpoint reconstruction or from library changes since the retained run and are
#: identical in the second-model preflight's reproduction; none is a reported number.
RETAINED_DRIFT_NOTES: dict[str, str] = {
    ".evidence.support_days": (
        "checkpoint reconstruction: envelope.day of a reconstructed episode is the record's "
        "snapshot day rather than the live run day"
    ),
    ".guard.clauses[0].hull": (
        "library change after the retained issue-type run: grc/contracts.py fits Hull('any') "
        "to nominal identifier paths (z.issue_number) instead of an interval"
    ),
    ".verifier.clauses[1].hull": (
        "library change after the retained issue-type run: nominal identifier paths keep "
        "Hull('any') in the verifier"
    ),
    ".gate.features_spec": (
        "library change after the retained issue-type run: the gate feature spec mirrors the "
        "nominal identifier hull"
    ),
    ".manifest.tracer_version": "library version string agent-compaction/0.5.0 -> 0.6.0",
    ".manifest.manifest_id": "derived from tracer_version",
    ".compatibility_key": "derived from tracer_version",
    ".program.composite": "Program.to_dict gained an always-present composite key (null here)",
    ".evidence.metrics.composite": "Evidence.metrics gained composite keys after the retained issue-type run",
    ".evidence.metrics.composite_name": "Evidence.metrics gained composite keys after the retained issue-type run",
}


# ------------------------------------------------------------------ sandbox world


class SnapshotWorld:
    """The sandbox interface ``challenge`` expects, over the immutable pinned snapshot.

    ``compile_grc`` takes ``sandbox: Callable[[], world]``; ``sandbox_replay`` and
    ``run_perturbations`` call it once per window and require ``world.execute(tool, args)``
    and ``world.state_digest()``.  The store is a read-only in-memory copy of the
    revision-pinned parquet, so the state digest is the pinned parquet checksum plus the
    record count: no tool can change it, and a changed digest would be a hard reject.
    """

    def __init__(
        self,
        execute: Callable[[str, dict[str, Any]], Any],
        *,
        parquet_sha256: str,
        n_records: int,
    ) -> None:
        self._execute = execute
        self._digest = f"{parquet_sha256}:{n_records}"
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def execute(self, tool: str, args: dict[str, Any]) -> Any:
        self.calls.append((tool, dict(args)))
        return self._execute(tool, dict(args))

    def state_digest(self) -> str:
        return self._digest


@contextlib.contextmanager
def _capture(module: Any, sandbox: Callable[[], Any] | None) -> Iterator[list[Any]]:
    """Retain ``module.compile_grc``'s ``CompileResult`` and, with a sandbox, run the challenge.

    The retained drivers hard-code ``sandbox=None, perturbations=()``; rebinding the name
    they resolve at call time keeps their split construction and ``GrcConfig`` untouched.
    With ``sandbox=None`` the call is forwarded unchanged (the control).  The original
    binding is restored on exit so two families sharing one driver module do not stack
    wrappers.
    """

    captured: list[Any] = []
    real = module.compile_grc

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        assert kwargs.get("sandbox") is None and not kwargs.get("perturbations"), kwargs
        if sandbox is not None:
            kwargs["sandbox"] = sandbox
            kwargs["perturbations"] = DEFAULT_PERTURBATIONS
        result = real(*args, **kwargs)
        captured.append(result)
        return result

    module.compile_grc = wrapped
    try:
        yield captured
    finally:
        module.compile_grc = real


# ------------------------------------------------------------ per-family recompile


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sandbox_audit(worlds: list[SnapshotWorld], executor: str, source: dict[str, Any]) -> dict[str, Any]:
    return {
        "executor": executor,
        "worlds_created": len(worlds),
        "tool_calls": sum(len(w.calls) for w in worlds),
        "state_digest": worlds[0].state_digest() if worlds else None,
        "source": source,
    }


def recompile_issue_type(*, with_challenge: bool) -> tuple[Any, dict[str, Any], Any, dict[str, Any]]:
    import github_live_study as fixed
    import recurrence_only_ablation as shared
    import second_model_replication as smr

    store, audit = shared.load_store()
    retained = json.loads(ARTIFACTS["issue_type"]["retained"].read_text(encoding="utf-8"))
    checkpoint = json.loads(ARTIFACTS["issue_type"]["checkpoint"].read_text(encoding="utf-8"))
    catalog = fixed.make_catalog()
    tools = fixed.make_tools(store)
    model = str(retained["run"]["model"])
    assert model == MODEL, model
    manifest = fixed.make_manifest(model, tools, catalog, smr.TASK_DESIGN)
    discovery = smr.reconstruct_discovery(checkpoint, store=store, manifest=manifest)
    worlds: list[SnapshotWorld] = []

    def sandbox() -> SnapshotWorld:
        world = SnapshotWorld(
            lambda tool, args: shared.execute_issue_snapshot(store, tool, args),
            parquet_sha256=audit["parquet_sha256"],
            n_records=len(store),
        )
        worlds.append(world)
        return world

    with _capture(fixed, sandbox if with_challenge else None) as captured:
        _registry, record, _manifest = smr.compile_for_model(
            discovery, model=model, catalog=catalog, tools=tools
        )
    return captured[-1], record, retained, _sandbox_audit(
        worlds, "paper/scripts/recurrence_only_ablation.py::execute_issue_snapshot", audit
    )


def recompile_family(name: str, *, with_challenge: bool) -> tuple[Any, dict[str, Any], Any, dict[str, Any]]:
    import github_live_study as fixed
    import github_workflow_family_study as fam

    spec = fam.FAMILIES[name]
    store, audit = fam.load_store()
    catalog = fam.make_catalog(spec)
    tools = fam.make_tools(spec, store)
    source_manifest = fam.make_manifest(spec, MODEL, tools, catalog, "source", instructions=spec.discovery_prompt)
    continuation_manifest = fam.make_manifest(spec, MODEL, (), catalog, "pre-model", instructions=spec.prompt)
    retained = json.loads(ARTIFACTS[name]["retained"].read_text(encoding="utf-8"))
    assert str(retained["run"]["model"]) == MODEL, retained["run"]["model"]
    checkpoint = json.loads(ARTIFACTS[name]["checkpoint"].read_text(encoding="utf-8"))
    discovery = fam.reconstruct_discovery(spec, checkpoint, store=store, manifest=source_manifest)
    worlds: list[SnapshotWorld] = []

    def sandbox() -> SnapshotWorld:
        world = SnapshotWorld(
            lambda tool, args: fam.execute_snapshot(spec, store, tool, args),
            parquet_sha256=fixed.HF_PARQUET_SHA256,
            n_records=len(store),
        )
        worlds.append(world)
        return world

    with _capture(fam, sandbox if with_challenge else None) as captured:
        _registry, record = fam.compile_artifact(
            spec, discovery, catalog=catalog, source_manifest=source_manifest,
            continuation_manifest=continuation_manifest,
        )
    return captured[-1], record, retained, _sandbox_audit(
        worlds, "paper/scripts/github_workflow_family_study.py::execute_snapshot", audit
    )


def recompile(name: str, *, with_challenge: bool) -> tuple[Any, dict[str, Any], Any, dict[str, Any]]:
    if name == "issue_type":
        return recompile_issue_type(with_challenge=with_challenge)
    return recompile_family(name, with_challenge=with_challenge)


# --------------------------------------------------------------- identity checks


def _program_dict(artifact: dict[str, Any]) -> dict[str, Any]:
    program = copy.deepcopy(dict(artifact.get("program") or {}))
    if program.get("composite") is None:
        # ``Program.to_dict`` gained an always-present ``composite`` key after the
        # issue-type run was serialized; a null composite is the same program.
        program.pop("composite", None)
    return program


def diff_paths(left: Any, right: Any, path: str = "") -> list[str]:
    """Dotted paths of every leaf that differs between two JSON values."""

    if isinstance(left, dict) and isinstance(right, dict):
        out: list[str] = []
        for key in sorted(set(left) | set(right)):
            out.extend(diff_paths(left.get(key, "<missing>"), right.get(key, "<missing>"), f"{path}.{key}"))
        return out
    if isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        out = []
        for index, (a, b) in enumerate(zip(left, right)):
            out.extend(diff_paths(a, b, f"{path}[{index}]"))
        return out
    return [] if left == right else [path]


def _is_challenge_evidence(path: str) -> bool:
    return any(path == p or path.startswith(p + ".") or path.startswith(p + "[") for p in CHALLENGE_EVIDENCE_PATHS)


def _drift_note(path: str) -> str | None:
    for prefix, note in RETAINED_DRIFT_NOTES.items():
        if path == prefix or path.startswith(prefix + ".") or path.startswith(prefix + "["):
            return note
    return None


def identity_vs_retained(recompiled: dict[str, Any], retained: dict[str, Any],
                         recompiled_splits: str, retained_splits: str) -> dict[str, Any]:
    gate_r, gate_t = recompiled["gate"], retained["gate"]
    paths = diff_paths(recompiled, retained)
    outside = [p for p in paths if not _is_challenge_evidence(p)]
    return {
        "artifact_id": {"recompiled": recompiled["artifact_id"], "retained": retained["artifact_id"],
                        "identical": recompiled["artifact_id"] == retained["artifact_id"]},
        "program_identical": _program_dict(recompiled) == _program_dict(retained),
        "splits_digest": {"recompiled": recompiled_splits, "retained": retained_splits,
                          "identical": recompiled_splits == retained_splits},
        "gate_identical": {key: gate_r.get(key) == gate_t.get(key) for key in GATE_FIELDS},
        "gate": {key: gate_t.get(key) for key in GATE_FIELDS},
        "name_identical": recompiled["name"] == retained["name"],
        "guard_identical": recompiled["guard"] == retained["guard"],
        "verifier_identical": recompiled["verifier"] == retained["verifier"],
        "compatibility_key_identical": recompiled["compatibility_key"] == retained["compatibility_key"],
        "paths_that_differ": paths,
        "paths_that_differ_outside_challenge_evidence": outside,
        "drift_notes": {p: (_drift_note(p) or "unclassified") for p in outside},
        "unclassified_differences": [p for p in outside if _drift_note(p) is None],
        "retained_perturbations_claimed": retained.get("evidence", {}).get("metrics", {}).get("perturbations_claimed"),
        "retained_signature": retained.get("signature", ""),
    }


def identity_vs_control(challenge: dict[str, Any], control: dict[str, Any],
                        challenge_result: Any, control_result: Any,
                        challenge_splits: str, control_splits: str) -> dict[str, Any]:
    paths = diff_paths(challenge, control)
    outside = [p for p in paths if not _is_challenge_evidence(p)]
    return {
        "control_call": "compile_grc(..., sandbox=None, perturbations=()) through the retained driver, same process",
        "artifact_id_identical": challenge["artifact_id"] == control["artifact_id"],
        "splits_digest_identical": challenge_splits == control_splits,
        "program_identical": challenge["program"] == control["program"],
        "guard_identical": challenge["guard"] == control["guard"],
        "verifier_identical": challenge["verifier"] == control["verifier"],
        "gate_identical": challenge["gate"] == control["gate"],
        "manifest_identical": challenge["manifest"] == control["manifest"],
        "candidate_ids_identical": [c.candidate_id for c in challenge_result.candidates]
        == [c.candidate_id for c in control_result.candidates],
        "candidate_stages_identical": [(c.candidate_id, c.stage, c.rejected) for c in challenge_result.candidates]
        == [(c.candidate_id, c.stage, c.rejected) for c in control_result.candidates],
        "paths_that_differ": paths,
        "paths_that_differ_outside_challenge_evidence": outside,
        "only_challenge_evidence_differs": not outside,
        "control_perturbations_claimed": control["evidence"]["metrics"].get("perturbations_claimed"),
    }


def assert_identity(name: str, retained: dict[str, Any], control: dict[str, Any]) -> None:
    failures = []
    if not retained["artifact_id"]["identical"]:
        failures.append("artifact_id vs retained")
    if not retained["program_identical"]:
        failures.append("program vs retained")
    if not retained["splits_digest"]["identical"]:
        failures.append("splits_digest vs retained")
    failures.extend(f"gate.{k} vs retained" for k, same in retained["gate_identical"].items() if not same)
    gate = retained["gate"]
    if not (gate["n_calibration_groups"] == 92 and gate["observed_violations"] == 0 and gate["retire"] is False):
        failures.append("retained gate is not the 92/0 gate")
    if retained["unclassified_differences"]:
        failures.append(f"unclassified differences vs retained: {retained['unclassified_differences']}")
    if not control["only_challenge_evidence_differs"]:
        failures.append(f"challenge changed non-evidence fields: {control['paths_that_differ_outside_challenge_evidence']}")
    for key in ("artifact_id_identical", "splits_digest_identical", "program_identical", "guard_identical",
                "verifier_identical", "gate_identical", "manifest_identical", "candidate_stages_identical"):
        if not control[key]:
            failures.append(f"{key} vs control")
    if failures:
        raise RuntimeError(f"{name}: recompiled artifact is not the retained artifact: {failures}")


# ---------------------------------------------------------------- challenge report


def challenge_report(result: Any, artifact_id: str) -> dict[str, Any]:
    rec = next(c for c in result.candidates if c.candidate_id == artifact_id)
    chal = rec.challenge
    assert chal is not None, f"{artifact_id} never reached the challenge stage"
    per_family = []
    for pert in DEFAULT_PERTURBATIONS:
        row = chal.perturbation.get(pert.name)
        if row is None:
            per_family.append({
                "perturbation": pert.name, "family": pert.family, "expect": pert.expect,
                "ran": False, "reason": "not present in the challenge report",
            })
            continue
        per_family.append({
            "perturbation": pert.name,
            "family": pert.family,
            "expect": pert.expect,
            "ran": True,
            "mode": row.get("mode"),
            "n": row.get("n", 0),
            "passed": row.get("passed", 0),
            "abstained": row.get("abstained", 0),
            "verifier_abstained": row.get("verifier_abstained", 0),
            "wrong": row.get("wrong", 0),
            "state_delta": row.get("state_delta", 0),
            "no_reference": row.get("no_reference", 0),
            "abstention_rate": row.get("abstention_rate", 0.0),
            "hard_rejects": [h for h in chal.hard_rejects if h.get("perturbation") == pert.name],
        })
    return {
        "candidate_stage": rec.stage,
        "candidate_rejected": rec.rejected,
        "perturbations_claimed": chal.perturbations_claimed,
        "survives_challenge": chal.ok,
        "recorded_replay": chal.recorded.as_dict(),
        "sandbox_replay": chal.sandbox.as_dict(),
        "perturbation_families": per_family,
        "families_ran": sum(1 for r in per_family if r["ran"]),
        "families_total": len(DEFAULT_PERTURBATIONS),
        "families_not_run": [r for r in per_family if not r["ran"]],
        "hard_rejects": list(chal.hard_rejects),
        "wrong_total": sum(r.get("wrong", 0) for r in per_family),
        "state_delta_total": sum(r.get("state_delta", 0) for r in per_family),
    }


def candidate_table(result: Any) -> list[dict[str, Any]]:
    rows = []
    for rec in result.candidates:
        chal = rec.challenge
        rows.append({
            "candidate_id": rec.candidate_id,
            "tools": list(rec.tools),
            "stage": rec.stage,
            "rejected": rec.rejected,
            "challenge": None if chal is None else {
                "perturbations_claimed": chal.perturbations_claimed,
                "ok": chal.ok,
                "hard_rejects": len(chal.hard_rejects),
                "wrong": sum(int(v.get("wrong", 0)) for v in chal.perturbation.values()),
            },
            "gate": None if rec.gate is None else {k: getattr(rec.gate, k) for k in GATE_FIELDS},
        })
    return rows


# --------------------------------------------------------------------- signatures


def signature_checks(artifact: Artifact, name: str, retained_registry: Path) -> dict[str, Any]:
    registry = Registry(name=f"paper-github-{name}-signed", signing_key=SIGNING_KEY)
    registry.add(artifact)  # Registry.add signs when a key is configured
    out: dict[str, Any] = {
        "signing": "HMAC-SHA256 over Artifact.body_digest(); key = sha256(SIGNING_KEY_DERIVATION)",
        "signing_key_derivation": SIGNING_KEY_DERIVATION,
        "signing_key_sha256": hashlib.sha256(SIGNING_KEY).hexdigest(),
        "body_digest": artifact.body_digest(),
        "signature": artifact.signature,
        "verify_signature": artifact.verify_signature(SIGNING_KEY),
        "verify_signature_wrong_key": artifact.verify_signature(WRONG_KEY),
    }
    with tempfile.TemporaryDirectory() as scratch:
        saved = registry.save(Path(scratch) / "registry")
        payload = json.loads(saved.read_text(encoding="utf-8"))
        out["saved_signature_persisted"] = payload["artifacts"][0]["signature"] == artifact.signature
        loaded = Registry.load(saved.parent, signing_key=SIGNING_KEY)
        reloaded = loaded.by_id(artifact.artifact_id)
        out["reload_with_key"] = {
            "loaded": reloaded is not None,
            "verify_signature": bool(reloaded and reloaded.verify_signature(SIGNING_KEY)),
            "body_digest_identical": bool(reloaded and reloaded.body_digest() == artifact.body_digest()),
            "resolve_returns_artifact": [a.artifact_id for a in loaded.resolve(
                artifact.compatibility_key, artifact.partition, stages=(artifact.lifecycle,)
            )] == [artifact.artifact_id],
        }
        try:
            Registry.load(saved.parent, signing_key=WRONG_KEY)
            out["reload_with_wrong_key_refused"] = False
        except RegistryError as exc:
            out["reload_with_wrong_key_refused"] = True
            out["reload_with_wrong_key_error"] = str(exc)
        tampered = copy.deepcopy(payload)
        tampered["artifacts"][0]["gate"]["threshold"] = 0.0
        tampered["artifacts"][0]["gate"]["risk_upper_bound"] = 0.0
        saved.write_text(json.dumps(tampered, indent=2, default=str), encoding="utf-8")
        try:
            Registry.load(saved.parent, signing_key=SIGNING_KEY)
            out["tampered_gate_refused"] = False
        except RegistryError as exc:
            out["tampered_gate_refused"] = True
            out["tampered_gate_error"] = str(exc)
        unsigned = Registry.load(saved.parent)  # verification off: the tampered file loads
        out["tampered_gate_loads_when_verification_is_off"] = unsigned.by_id(artifact.artifact_id) is not None
    # The retained registry was written without a key: it carries an empty signature and
    # is refused as soon as verification is configured on, under any key.
    retained_payload = json.loads((retained_registry / "registry.json").read_text(encoding="utf-8"))
    out["retained_registry"] = {
        "path": str(retained_registry.relative_to(ROOT)),
        "signatures": [a.get("signature", "") for a in retained_payload["artifacts"]],
    }
    try:
        Registry.load(retained_registry, signing_key=SIGNING_KEY)
        out["retained_registry"]["refused_when_verification_on"] = False
    except RegistryError as exc:
        out["retained_registry"]["refused_when_verification_on"] = True
        out["retained_registry"]["error"] = str(exc)
    return out


# --------------------------------------------------------------------------- main


def run_one(name: str) -> dict[str, Any]:
    control_result, control_record, retained, _ = recompile(name, with_challenge=False)
    result, record, _retained, sandbox_audit = recompile(name, with_challenge=True)
    expected_id = ARTIFACTS[name]["artifact_id"]
    artifact_obj = next(a for a in result.artifacts if a.artifact_id == record["artifact"]["artifact_id"])
    recompiled = record["artifact"]
    retained_art = retained["compiler"]["artifact"]
    assert retained_art["artifact_id"] == expected_id, retained_art["artifact_id"]
    vs_retained = identity_vs_retained(
        recompiled, retained_art, record["splits"]["digest"], retained["compiler"]["splits"]["digest"]
    )
    vs_control = identity_vs_control(
        recompiled, control_record["artifact"], result, control_result,
        record["splits"]["digest"], control_record["splits"]["digest"],
    )
    assert_identity(name, vs_retained, vs_control)  # nothing below is recorded unless this passes
    challenge = challenge_report(result, recompiled["artifact_id"])
    signatures = signature_checks(artifact_obj, name, ARTIFACTS[name]["retained_registry"])
    return {
        "artifact_id": recompiled["artifact_id"],
        "name": recompiled["name"],
        "model": MODEL,
        "provider_calls": 0,
        "inputs": {
            "discovery_checkpoint": str(ARTIFACTS[name]["checkpoint"].relative_to(ROOT)),
            "discovery_checkpoint_sha256": _sha256(ARTIFACTS[name]["checkpoint"]),
            "retained_results": str(ARTIFACTS[name]["retained"].relative_to(ROOT)),
            "retained_results_sha256": _sha256(ARTIFACTS[name]["retained"]),
            "config_digest": result.config.digest() if result.config is not None else None,
        },
        "compile_call": {
            "retained": "compile_grc(..., sandbox=None, perturbations=())",
            "recompiled": "compile_grc(..., sandbox=SnapshotWorld factory, perturbations=DEFAULT_PERTURBATIONS)",
            "sandbox": sandbox_audit,
        },
        "identity": {"vs_retained": vs_retained, "vs_control": vs_control},
        "challenge": challenge,
        "perturbations_claimed": challenge["perturbations_claimed"],
        "survives_challenge": challenge["survives_challenge"],
        "signature": signatures,
        "signature_verified": signatures["verify_signature"] and signatures["reload_with_key"]["verify_signature"],
        "candidates": candidate_table(result),
        "rejection_by_stage": dict(result.rejection_by_stage),
        "retained_files_modified": False,
    }


def main(argv: Sequence[str] | None = None) -> None:
    names = list(argv) if argv else list(ARTIFACTS)
    per_artifact = {name: run_one(name) for name in names}
    payload = {
        "schema": "agent-compaction-recompile-with-challenge/v1",
        "purpose": (
            "Close the two Appendix G operational caveats provider-free: run the perturbation "
            "suite through a pinned-snapshot sandbox and verify registry signatures, on the "
            "retained programs, splits, and gates."
        ),
        "provider_calls": 0,
        "perturbation_suite": [
            {"perturbation": p.name, "family": p.family, "expect": p.expect,
             "mechanism": "injected tool failure" if p.fail_tools else "response transform"}
            for p in DEFAULT_PERTURBATIONS
        ],
        "sandbox_interface": {
            "compile_grc": "sandbox: Callable[[], world] | None; perturbations: Sequence[Perturbation]",
            "world": "execute(tool, args) -> result; state_digest() -> str",
            "implementation": "paper/scripts/recompile_with_challenge.py::SnapshotWorld",
        },
        "challenge_evidence_paths": list(CHALLENGE_EVIDENCE_PATHS),
        "artifacts": per_artifact,
        "summary": {
            "all_identity_checks_passed": all(
                a["identity"]["vs_retained"]["program_identical"]
                and a["identity"]["vs_retained"]["splits_digest"]["identical"]
                and all(a["identity"]["vs_retained"]["gate_identical"].values())
                and a["identity"]["vs_retained"]["artifact_id"]["identical"]
                and a["identity"]["vs_control"]["only_challenge_evidence_differs"]
                for a in per_artifact.values()
            ),
            "all_perturbations_claimed": all(a["perturbations_claimed"] for a in per_artifact.values()),
            "all_survive_challenge": all(a["survives_challenge"] for a in per_artifact.values()),
            "all_signatures_verified": all(a["signature_verified"] for a in per_artifact.values()),
            "families_not_run": {
                name: a["challenge"]["families_not_run"] for name, a in per_artifact.items()
            },
            "hard_rejects_total": sum(len(a["challenge"]["hard_rejects"]) for a in per_artifact.values()),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    for name, art in per_artifact.items():
        ch = art["challenge"]
        vr, vc = art["identity"]["vs_retained"], art["identity"]["vs_control"]
        print(
            f"{name}: {art['artifact_id']} id={vr['artifact_id']['identical']} "
            f"program={vr['program_identical']} splits={vr['splits_digest']['identical']} "
            f"gate={all(vr['gate_identical'].values())} only_challenge_evidence_vs_control={vc['only_challenge_evidence_differs']} "
            f"claimed={ch['perturbations_claimed']} survives={ch['survives_challenge']} "
            f"families={ch['families_ran']}/{ch['families_total']} wrong={ch['wrong_total']} "
            f"hard_rejects={len(ch['hard_rejects'])} signature_verified={art['signature_verified']}"
        )
        if vr["paths_that_differ_outside_challenge_evidence"]:
            print(f"    differs from the retained file outside challenge evidence (also in the control): "
                  f"{vr['paths_that_differ_outside_challenge_evidence']}")
        for row in ch["perturbation_families"]:
            if row["ran"]:
                print(
                    f"    {row['perturbation']:18s} {row['family']:22s} expect={row['expect']:9s} "
                    f"n={row['n']} passed={row['passed']} abstained={row['abstained']} "
                    f"verifier_abstained={row['verifier_abstained']} wrong={row['wrong']}"
                )
            else:
                print(f"    {row['perturbation']:18s} NOT RUN: {row['reason']}")
    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    main(sys.argv[1:])
