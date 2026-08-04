#!/usr/bin/env python3
"""Create the final publication checksum manifest after PDF compilation and validation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"
OUTPUT = PAPER / "results/publication_manifest.json"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def included_files() -> list[Path]:
    files: set[Path] = set()
    for path in PAPER.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(PAPER)
        if "__pycache__" in rel.parts or rel == Path("results/publication_manifest.json"):
            continue
        if rel == Path("results/validation_summary.json"):
            continue  # rewritten by every validator run
        if rel.parts[:2] in (("build", "rendered"), ("build", "article_pages")):
            continue  # visual-QA caches, fully derived from the compiled PDFs
        # Both compiled manuscripts are deliverables: the two-column conference build
        # and the single-column article build share one body but ship separately.
        if rel.parts and rel.parts[0] == "build" and rel.name not in {
            "main.pdf",
            "article.pdf",
        }:
            continue
        files.add(path)
    for base in (ROOT / "src", ROOT / "tests"):
        files.update(path for path in base.rglob("*.py") if "__pycache__" not in path.parts)
    benchmark_root = ROOT / "benchmarks"
    if benchmark_root.is_dir():
        files.update(
            path
            for path in benchmark_root.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and ".cache" not in path.parts
            and "results" not in path.parts
        )
    # The hand-written-macro comparator is generated from the deterministic offline
    # study. Hash its raw results and every local source needed to reproduce them; hashing
    # only the derived LaTeX table would let the evidence change undetected.
    offline_results = ROOT / "experiments" / "results"
    if offline_results.is_dir():
        files.update(
            path for path in offline_results.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        )
    for path in (
        ROOT / "experiments" / "__init__.py",
        ROOT / "experiments" / "run.py",
        ROOT / "experiments" / "manifests" / "preregistration.md",
    ):
        if path.exists():
            files.add(path)
    conditions = ROOT / "experiments" / "conditions"
    if conditions.is_dir():
        files.update(
            path for path in conditions.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        )
    demos = ROOT / "demos"
    if demos.is_dir():
        files.update(
            path for path in demos.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.name != ".DS_Store"
        )
    # Tier-3 raw evidence lives outside paper/ because the demonstration suite is part of
    # the library's own experiment tree. The manuscript cites its numbers, so it has to be
    # checksummed like every other evidence file rather than sitting outside the audit.
    tier3 = ROOT / "experiments" / "live_results"
    if tier3.is_dir():
        files.update(
            path for path in tier3.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        )
    for name in (
        "pyproject.toml",
        "README.md",
        "LICENSE",
        "docs/gpt-5.6-report.md",
        "extension-plan.md",
    ):
        path = ROOT / name
        if path.exists():
            files.add(path)
    return sorted(files)


def main() -> None:
    records = []
    for path in included_files():
        records.append(
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": digest(path),
            }
        )
    payload = {
        "schema": "agent-compaction-publication-manifest/v1",
        "scope": "paper sources, sealed evidence, compiled PDF, implementation source, and tests",
        "exclusions": [
            ".env and all credentials",
            "virtual environments and caches",
            "LaTeX intermediates other than the final PDF",
            "rendered-page visual-QA cache",
            "validation_summary.json because validator reruns rewrite it",
            "this manifest to avoid a self-digest",
        ],
        "files": records,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)} with {len(records)} file digests")


if __name__ == "__main__":
    main()
