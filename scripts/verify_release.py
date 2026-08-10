#!/usr/bin/env python3
"""Reproducibility audit: does the release actually contain what it claims?

Checks, in order of how easily each one is quietly broken:

1. the run manifest exists, names its seed and versions, and labels the substrate;
2. every demo result carries split sizes *and* a split digest;
3. every published table can be traced to a results file that exists;
4. figures referenced by ``docs/results.md`` exist on disk;
5. config examples validate against their schemas;
6. every artifact in the results is printable and carries gate evidence;
7. the effect catalogs of every demo declare every write they contain;
8. negative results are present, not omitted.

Exit code is non-zero on the first failure, so this is usable as a release gate.
"""

from __future__ import annotations

import json
import re
import sys
import tomllib
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

FAILURES: list[str] = []
SKIPPED: list[str] = []

# docs/ is untracked by request (see .gitignore). It is still written by
# experiments/analysis/report.py, experiments/live_run.py and
# scripts/build_html_report.py, so it exists in a working tree that has run
# them and is absent from a clean checkout. The checks that read it are
# reported as SKIPPED rather than silently passing, so a clean checkout stays
# green without the gate quietly getting weaker.
DOCS = ROOT / "docs"
DOCS_PRESENT = DOCS.is_dir()


def check(condition: bool, message: str) -> None:
    status = "ok  " if condition else "FAIL"
    print(f"  [{status}] {message}")
    if not condition:
        FAILURES.append(message)


def skip(message: str) -> None:
    print(f"  [skip] {message}")
    SKIPPED.append(message)


def main() -> int:
    results = ROOT / "experiments" / "results"
    print("reproducibility audit")

    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    project_version = metadata["project"]["version"]
    source = (ROOT / "src" / "guarded_agentic_compaction" / "__init__.py").read_text()
    source_match = re.search(r'^__version__\s*=\s*["\']([^"\']+)', source, re.MULTILINE)
    check(
        source_match is not None and source_match.group(1) == project_version,
        f"package metadata and source version agree ({project_version})",
    )
    check((ROOT / "LICENSE").exists(), "declared Apache-2.0 license file exists")
    check(
        (ROOT / "src" / "guarded_agentic_compaction" / "py.typed").exists(),
        "typed-package marker exists",
    )
    optional = metadata["project"].get("optional-dependencies", {})
    check("mlflow" not in optional, "package metadata has no MLflow extra")
    check(
        not (ROOT / "src" / "guarded_agentic_compaction" / "capture" / "mlflow_adapter.py").exists(),
        "source package has no MLflow adapter",
    )
    _check_current_documentation()
    for wheel in sorted((ROOT / "dist").glob("guarded_agentic_compaction-*.whl")):
        with zipfile.ZipFile(wheel) as archive:
            names = archive.namelist()
            metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
            wheel_metadata = "\n".join(
                archive.read(name).decode("utf-8") for name in metadata_names
            )
        check(
            not any("mlflow" in name.casefold() for name in names),
            f"{wheel.name} contains no stale MLflow module",
        )
        check(
            "Requires-Dist: mlflow" not in wheel_metadata,
            f"{wheel.name} declares no MLflow dependency",
        )

    for document in _markdown_files():
        for target in _local_links(document):
            check(target.exists(), f"{document.relative_to(ROOT)} links to {target.relative_to(ROOT)}")

    manifest_path = results / "run_manifest.json"
    check(manifest_path.exists(), "run manifest exists")
    if not manifest_path.exists():
        return _finish()
    manifest = json.loads(manifest_path.read_text())
    for key in ("substrate", "seed", "python", "numpy", "scipy", "sklearn", "created"):
        check(key in manifest, f"run manifest records {key}")
    check(manifest.get("substrate") == "simulated", "run manifest labels the substrate")
    check("warning" in manifest, "run manifest carries the not-a-production-measurement warning")

    all_results = results / "all_results.json"
    check(all_results.exists(), "aggregate results exist")
    if not all_results.exists():
        return _finish()
    payload = json.loads(all_results.read_text())
    demos = payload["demos"]
    declared = manifest.get("demos") or []
    if len(demos) < 3:
        print(
            f"  note: this results directory holds a PARTIAL run ({sorted(demos)}). The release "
            "claim requires every demonstration, including the negative control. Re-run "
            "`python experiments/run.py` without --demos."
        )
    check(len(demos) >= 3, f"at least three demonstrations reported (got {len(demos)})")
    check(
        set(demos) == set(declared),
        "the results directory contains exactly the demonstrations the manifest declares",
    )

    for key, d in demos.items():
        check((results / f"{key}.json").exists(), f"{key}: per-demo results file exists")
        check(bool(d["splits"].get("digest")), f"{key}: split manifest digest present")
        check(
            all(role in d["splits"] for role in ("train", "dev", "calibration", "test")),
            f"{key}: all four split roles reported",
        )
        check("baseline" in d["conditions"], f"{key}: baseline condition scored")
        check("simple" in d["conditions"], f"{key}: hand-written comparator scored")
        check("full" in d["conditions"], f"{key}: full compaction scored")
        check("support_only" in d["conditions"], f"{key}: support-only ablation scored")
        check(
            d["conditions"]["baseline"]["n_episodes"] > 0,
            f"{key}: sealed-test denominator published",
        )
        check(bool(d["estimate"].get("render")), f"{key}: estimator report retained")
        check(
            isinstance(d["grc"].get("rejections"), dict),
            f"{key}: rejection reasons retained (negative results are reported)",
        )
        for text in d.get("artifacts", []):
            check("gate    q =" in text, f"{key}: artifact carries gate evidence")

    negative = [k for k, d in demos.items() if not d["hypotheses"]["co_primary_passed"]]
    check(bool(negative), f"a negative result is present and reported ({negative})")

    doc = DOCS / "results.md"
    if not DOCS_PRESENT:
        skip("docs/results.md substrate label (docs/ is untracked)")
    else:
        check(doc.exists(), "docs/results.md exists")
        if doc.exists():
            text = doc.read_text()
            check("substrate=simulated" in text, "results doc labels the substrate")
        for name in re.findall(r"!\[[^\]]*\]\(\.\./experiments/figures/([^)]+)\)", text):
            check((ROOT / "experiments" / "figures" / name).exists(), f"figure {name} exists")

    _check_live_results()

    try:
        import jsonschema
        import yaml

        for cfg, sch in (
            ("configs/effects.example.yaml", "configs/effects.schema.json"),
            ("configs/promotion.example.yaml", "configs/promotion.schema.json"),
        ):
            jsonschema.validate(
                yaml.safe_load((ROOT / cfg).read_text()), json.loads((ROOT / sch).read_text())
            )
            check(True, f"{cfg} validates against {Path(sch).name}")
    except ImportError:  # pragma: no cover
        check(False, "jsonschema/pyyaml available for config validation")

    from guarded_agentic_compaction.schema.effects import EffectCatalog, EffectClass

    for cat_path in sorted((ROOT / "demos").glob("*/effects.yaml")):
        cat = EffectCatalog.from_yaml(cat_path)
        writes = [n for n, s in cat.tools.items() if not s.effect.is_read_like]
        compilable_writes = [n for n in writes if cat.compilable(n)]
        check(not compilable_writes, f"{cat_path.parent.name}: no write is compilable")
        check(bool(cat.tools), f"{cat_path.parent.name}: catalog is non-empty")

    return _finish()


def _check_live_results() -> None:
    results = ROOT / "experiments" / "live_results"
    manifest_path = results / "run_manifest.json"
    payload_path = results / "all_results.json"
    check(manifest_path.exists(), "live run manifest exists")
    check(payload_path.exists(), "live aggregate results exist")
    if DOCS_PRESENT:
        check((DOCS / "live-results.md").exists(), "live results document exists")
    else:
        skip("live results document (docs/ is untracked)")
    if not manifest_path.exists() or not payload_path.exists():
        return

    manifest = json.loads(manifest_path.read_text())
    payload = json.loads(payload_path.read_text())
    check(manifest.get("substrate") == "openai_api_live", "live manifest labels provider substrate")
    check(manifest.get("provider") == "openai", "live manifest records provider")
    check(bool(manifest.get("model")), "live manifest records model")
    check(manifest.get("api_key_persisted") is False, "live manifest states API key is not persisted")
    check("OPENAI_API_KEY" not in json.dumps(payload), "live results contain no API-key field")

    #: The optimized condition each demonstration is required to report. The three
    #: refusal conditions are checked separately below, because "no compaction" is the
    #: claimed result for them and a run that silently compacted would be the failure.
    optimized_by_demo = {
        "support": "compacted",
        "permissioned_rag": "compacted",
        "incident_triage": "compacted",
        "mcp_ops": "compacted_fallback",
        "fulfillment": "compacted",
        "tgws_router": "routed",
    }
    demos = payload.get("demos", {})
    check(
        set(demos) == set(optimized_by_demo),
        "all six live demonstrations are reported",
    )
    for name, demo in demos.items():
        check((results / f"{name}.json").exists(), f"{name}: live result file exists")
        conditions = demo.get("conditions", {})
        check("baseline" in conditions, f"{name}: live baseline scored")
        optimized_name = optimized_by_demo.get(name, "compacted")
        check(optimized_name in conditions, f"{name}: live optimized condition scored")
        runs = demo.get("runs", [])
        check(bool(runs), f"{name}: live per-scenario evidence retained")
        check(all(run.get("trace_id") for run in runs), f"{name}: every live run has a native trace id")
        check(
            all(run.get("outcome", {}).get("task_success") for run in runs),
            f"{name}: every live scenario passed its outcome contract",
        )
        if name == "mcp_ops":
            check(
                all(run.get("dispatch", {}).get("outcome") == "BASELINE" for run in runs),
                "mcp_ops: undeclared effects force baseline fallback",
            )
        elif name == "tgws_router":
            routed = [run for run in runs if run.get("condition") == "routed"]
            check(
                all(run["dispatch"].get("route", "").startswith("route:") for run in routed),
                "tgws_router: every routed run names the leaf it matched",
            )
            check(
                all(run["dispatch"].get("tools", 99) < 9 for run in routed),
                "tgws_router: every route prunes the generalist tool surface",
            )
        else:
            compacted = [run for run in runs if run.get("condition") == "compacted"]
            check(
                all(run.get("dispatch", {}).get("compacted", 0) == 1 for run in compacted),
                f"{name}: every optimized run executed one compiled region",
            )

    # The refusal conditions carry the safety claim: each must cost exactly the
    # baseline turn count and must never report a compacted dispatch.
    fulfillment = demos.get("fulfillment", {})
    baseline_turns = fulfillment.get("conditions", {}).get("baseline", {}).get("requests")
    for refusal in ("compacted_loop_refused", "compacted_ood_fallback"):
        metrics = fulfillment.get("conditions", {}).get(refusal)
        check(metrics is not None, f"fulfillment: {refusal} condition reported")
        if metrics is None or baseline_turns is None:
            continue
        check(
            metrics.get("requests") == baseline_turns,
            f"fulfillment: {refusal} costs exactly the baseline turn count",
        )
        check(
            metrics.get("quality") == fulfillment["conditions"]["baseline"].get("quality"),
            f"fulfillment: {refusal} preserves baseline quality",
        )
        refused = [r for r in fulfillment.get("runs", []) if r.get("condition") == refusal]
        check(
            all(r.get("dispatch", {}).get("compacted", 0) == 0 for r in refused),
            f"fulfillment: {refusal} never dispatched a region",
        )


def _markdown_files() -> list[Path]:
    roots = [
        ROOT / "README.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "SECURITY.md",
        ROOT / "benchmarks" / "README.md",
        ROOT / "paper" / "README.md",
    ]
    roots.extend(DOCS.rglob("*.md"))  # empty when docs/ is absent
    roots.extend((ROOT / "experiments").rglob("*.md"))
    roots.extend((ROOT / "paper" / "supplementary").rglob("*.md"))
    return sorted(path for path in roots if path.exists())


def _check_current_documentation() -> None:
    """Prevent removed public surfaces from returning to current usage guides.

    Historical ADRs, reviews, and the research proposal may name retired APIs while
    explaining their disposition. The documents below are current integration surfaces,
    so executable examples in them must follow release 0.6.0.
    """

    current = (ROOT / "README.md",)
    if DOCS_PRESENT:
        current += (
            DOCS / "library-api.md",
            DOCS / "openai-agents-sdk.md",
            DOCS / "trace-contract.md",
            DOCS / "use-cases.md",
        )
    else:
        skip("retired-API scan over docs/ integration guides (docs/ is untracked)")
    retired = (
        "import compaction",
        "cx.compile(",
        "cx.enable_tracing(",
        "export_episodes(",
        "load_episodes(",
        "configure_mlflow(",
        "mlflow_adapter",
    )
    for document in current:
        text = document.read_text()
        for marker in retired:
            check(
                marker not in text,
                f"{document.relative_to(ROOT)} excludes retired API {marker!r}",
            )


def _local_links(document: Path) -> list[Path]:
    out: list[Path] = []
    for raw in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", document.read_text()):
        href = raw.strip().strip("<>").split("#", 1)[0]
        if not href or href.startswith(("http://", "https://", "mailto:", "data:")):
            continue
        out.append((document.parent / href).resolve())
    return out


def _finish() -> int:
    if FAILURES:
        print(f"\n{len(FAILURES)} check(s) failed")
        return 1
    if SKIPPED:
        print(f"\n{len(SKIPPED)} check(s) SKIPPED because docs/ is untracked:")
        for message in SKIPPED:
            print(f"  - {message}")
        print("  run experiments/analysis/report.py and scripts/build_html_report.py")
        print("  to regenerate docs/ locally if you need these checks to run.")
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
