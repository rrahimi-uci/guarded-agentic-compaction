#!/usr/bin/env python3
"""Apply the measured Headroom result to the shipped workflow-family slide.

The canonical deck is normally generated with artifact-tool, but the required
artifact-tool workspace is intentionally not checked into this repository.  This
small, assertive post-generation transform updates one reviewed text box on the
already generated deck; it preserves slide geometry, charts, and the template.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[2]
DECK = ROOT / "paper/slides/compiling-recurrent-agent-workflows-into-guarded-programs-detailed.pptx"
SLIDE = "ppt/slides/slide18.xml"
OLD = (
    "The two new families compile verified three-read pre-model programs; the original "
    "issue family retains its conservative two-read prefix. Both newer families are "
    "cache-cold in every arm, so part of the 32.0–75.3% cost range is prompt-cache "
    "warmth rather than compiled depth; provider-side break-even is 411, 182, and 181 "
    "episodes against 132 paid discovery episodes each. The study changes decision and "
    "tools, but not repository or time: cross-repository and time-forward transfer remain open."
)
LEGACY = (
    "The two new families compile verified three-read pre-model programs; the original "
    "issue family retains its conservative two-read prefix. A version-pinned Headroom "
    "comparator on the two fixed cohorts attempted 240 model-visible JSON payloads, "
    "transformed zero, and saved zero tokens: Headroom is a boundary-specific negative "
    "result, not a rival explanation for GAC's savings. The study changes decision and "
    "tools, but not repository or time: cross-repository and time-forward transfer remain open."
)
NEW = (
    "The two new families compile verified three-read pre-model programs; the original "
    "issue family retains its conservative two-read prefix. Headroom on the two fixed "
    "cohorts attempted 240 model-visible JSON payloads, transformed zero, and saved zero "
    "tokens: a boundary-specific negative result, not a rival mechanism for GAC's savings. "
    "The study changes decision and tools, not repository or time; cross-repository and "
    "time-forward transfer remain open."
)
EVIDENCE_BOUNDARY = (
    "Three real-record workflow families support the primary transfer result: compiled 90/90, "
    "baseline 89/90, manual 90/90, all admitted at the registered alpha=.05 with a pooled "
    "3.3% compiled-only discordance bound. The Headroom ablation is limited to two reused "
    "30-record cohorts: its 240 eligible JSON payloads received zero transformations and "
    "saved zero tokens, so it is a boundary-specific negative result rather than a rival "
    "mechanism for GAC savings. The snapshot does not establish cross-repository or "
    "time-forward transfer, and part of the reported 32.0-75.3% cost range reflects "
    "prompt-cache warmth rather than compiled depth. GCS and comparator results rest on an "
    "artifact calibrated at alpha=.10 and are not licensed at .05. NESTFUL and API-Bank "
    "remain refusal evidence; eight other benchmark paths are supplementary interoperability audits."
)


def replace_once(blob: bytes) -> tuple[bytes, int]:
    new_tag = f"<a:t>{escape(NEW)}</a:t>".encode("utf-8")
    if new_tag in blob:
        return blob, 0
    matches = [f"<a:t>{escape(old)}</a:t>".encode("utf-8") for old in (OLD, LEGACY)]
    counts = [blob.count(old_tag) for old_tag in matches]
    if sum(counts) != 1:
        raise RuntimeError(f"expected one workflow-family detail box, found {sum(counts)}")
    old_tag = matches[counts.index(1)]
    return blob.replace(old_tag, new_tag, 1), 1


def refresh(deck: bytes) -> tuple[bytes, int]:
    source = BytesIO(deck)
    output = BytesIO()
    replacements = 0
    with ZipFile(source) as zin, ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as zout:
        for item in zin.infolist():
            content = zin.read(item.filename)
            if item.filename == SLIDE:
                content, count = replace_once(content)
                replacements += count
            zout.writestr(item, content)
    return output.getvalue(), replacements


def contains_new_result(deck: bytes) -> bool:
    with ZipFile(BytesIO(deck)) as package:
        return escape(NEW).encode("utf-8") in package.read(SLIDE)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refresh_manifest() -> None:
    path = ROOT / "paper/results/slide_generation.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    evidence = manifest.setdefault("evidence", {})
    for name, relative in {
        "headroom_pr_outcome": "paper/results/github_workflow_families/pr_outcome/headroom_ablation/results.json",
        "headroom_backlog_attention": "paper/results/github_workflow_families/backlog_attention/headroom_ablation/results.json",
    }.items():
        source = ROOT / relative
        evidence[name] = {"path": relative, "sha256": digest(source)}
    manifest["generator_sha256_current"] = digest(ROOT / "paper/scripts/generate_slides.mjs")
    manifest["evidence_boundary"] = EVIDENCE_BOUNDARY
    manifest["outputs"]["technical"]["sha256"] = digest(DECK)
    resync = manifest.setdefault("resync", {})
    applied = resync.setdefault("applied_after", [])
    if "refresh_headroom_ablation_slide.py" not in applied:
        applied.append("refresh_headroom_ablation_slide.py")
    changes = resync.setdefault("changes", [])
    change = "slide 18 records Headroom's fixed-cohort negative result: 240 attempted JSON payloads, zero transformations, and zero tokens saved"
    if change not in changes:
        changes.append(change)
    resync["headroom_ablation"] = {
        "script": "paper/scripts/refresh_headroom_ablation_slide.py",
        "target": "paper/slides/compiling-recurrent-agent-workflows-into-guarded-programs-detailed.pptx",
        "verification": "The exact inherited text box is replaced once; the checked-in artifact-tool runtime is unavailable, so this narrow post-generation edit preserves existing slide geometry and chart parts.",
    }
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    original = DECK.read_bytes()
    updated, replacements = refresh(original)
    if args.check:
        if not contains_new_result(updated):
            raise RuntimeError("Headroom result is absent from the publication slide")
        print(f"{DECK.name}: Headroom result present; pending replacements {replacements}")
        return
    if replacements:
        DECK.write_bytes(updated)
    refresh_manifest()
    print(f"{DECK.name}: replaced {replacements} workflow-family detail box")


if __name__ == "__main__":
    main()
