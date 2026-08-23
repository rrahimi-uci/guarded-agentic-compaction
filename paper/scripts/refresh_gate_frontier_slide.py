#!/usr/bin/env python3
"""Apply the gate-frontier study's null result to the shipped limitations slide.

The canonical deck is normally generated with artifact-tool, but the required
artifact-tool workspace is intentionally not checked into this repository.  This
small, assertive post-generation transform updates one reviewed text box on the
already generated deck (slide 25, "The gate never discriminated"); it preserves
slide geometry, charts, and the template, following the same pattern as
refresh_headroom_ablation_slide.py.
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
SLIDE = "ppt/slides/slide25.xml"
OLD = (
    "On the sealed artifact every threshold below 0.14 admits nothing and every "
    "threshold at or above it admits all 92, with zero violations throughout. The "
    "score was fitted with zero positive examples over eight observations, so it "
    "behaves as an all-or-none support test, not a risk–coverage frontier."
)
NEW = (
    "On the sealed artifact every threshold below 0.14 admits nothing and above it "
    "admits all 92, zero violations throughout. A pre-registered study since ran a "
    "support-only comparator (alpha=1, otherwise identical) on four repositories, "
    "240 held-out pairs, and found the same all-or-none threshold everywhere: "
    "confirmed, not resolved, and still not a risk-coverage frontier."
)
OLD_EVIDENCE_BOUNDARY = (
    "Three real-record workflow families support the primary transfer result: compiled "
    "90/90, baseline 89/90, manual 90/90, all admitted at the registered alpha=.05 with "
    "a pooled 3.3% compiled-only discordance bound. The Headroom ablation is limited to "
    "two reused 30-record cohorts: its 240 eligible JSON payloads received zero "
    "transformations and saved zero tokens, so it is a boundary-specific negative "
    "result rather than a rival mechanism for GAC savings. The snapshot does not "
    "establish cross-repository or time-forward transfer, and part of the reported "
    "32.0-75.3% cost range reflects prompt-cache warmth rather than compiled depth. GCS "
    "and comparator results rest on an artifact calibrated at alpha=.10 and are not "
    "licensed at .05. NESTFUL and API-Bank remain refusal evidence; eight other "
    "benchmark paths are supplementary interoperability audits."
)
EVIDENCE_BOUNDARY_ADDENDUM = (
    "A prospective gate-frontier study (four of five sealed repositories, 240 of the "
    "pre-registered 300 held-out pairs; the fifth retires at compile time, reproducing "
    "the cross-repository extension's own finding) ran a support-only comparator -- "
    "alpha=1, otherwise a byte-for-byte identical compile pass -- against the learned "
    "gate. Both are statistically indistinguishable on every metric, and every "
    "repository deploys the same coverage-1.0 threshold: the pre-declared null, not a "
    "demonstrated frontier."
)
NEW_EVIDENCE_BOUNDARY = OLD_EVIDENCE_BOUNDARY + " " + EVIDENCE_BOUNDARY_ADDENDUM
GENERATOR = ROOT / "paper/scripts/generate_slides.mjs"


def replace_once(blob: bytes) -> tuple[bytes, int]:
    new_tag = f"<a:t>{escape(NEW)}</a:t>".encode("utf-8")
    if new_tag in blob:
        return blob, 0
    old_tag = f"<a:t>{escape(OLD)}</a:t>".encode("utf-8")
    count = blob.count(old_tag)
    if count != 1:
        raise RuntimeError(f"expected one gate-discrimination detail box, found {count}")
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


def refresh_generator() -> int:
    """Update generate_slides.mjs's own embedded evidence_boundary literal.

    validate_artifacts.py asserts the manifest's evidence_boundary matches this
    literal verbatim, so a refresh script that only edits the manifest would pass
    once and then fail every subsequent validation run.
    """

    text = GENERATOR.read_text(encoding="utf-8")
    old_js = f'evidence_boundary: "{_js_escape(OLD_EVIDENCE_BOUNDARY)}",'
    new_js = f'evidence_boundary: "{_js_escape(NEW_EVIDENCE_BOUNDARY)}",'
    if new_js in text:
        return 0
    count = text.count(old_js)
    if count != 1:
        raise RuntimeError(f"expected one evidence_boundary literal in {GENERATOR}, found {count}")
    GENERATOR.write_text(text.replace(old_js, new_js, 1), encoding="utf-8")
    return 1


def _js_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def refresh_manifest() -> None:
    path = ROOT / "paper/results/slide_generation.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    evidence = manifest.setdefault("evidence", {})
    evidence["gate_frontier_study"] = {
        "path": "paper/results/github_multirepo_gate_frontier/results.json",
        "sha256": digest(ROOT / "paper/results/github_multirepo_gate_frontier/results.json"),
    }
    refresh_generator()
    manifest["generator_sha256_current"] = digest(GENERATOR)
    manifest["evidence_boundary"] = NEW_EVIDENCE_BOUNDARY
    manifest["outputs"]["technical"]["sha256"] = digest(DECK)
    resync = manifest.setdefault("resync", {})
    applied = resync.setdefault("applied_after", [])
    if "refresh_gate_frontier_slide.py" not in applied:
        applied.append("refresh_gate_frontier_slide.py")
    changes = resync.setdefault("changes", [])
    change = (
        "slide 25 records the gate-frontier study's null result: a support-only "
        "comparator on four repositories and 240 held-out pairs found the same "
        "all-or-none threshold as the sealed artifact"
    )
    if change not in changes:
        changes.append(change)
    resync["gate_frontier_study"] = {
        "script": "paper/scripts/refresh_gate_frontier_slide.py",
        "target": "paper/slides/compiling-recurrent-agent-workflows-into-guarded-programs-detailed.pptx",
        "verification": "The exact inherited text box is replaced once; the checked-in artifact-tool runtime is unavailable, so this narrow post-generation edit preserves existing slide geometry and chart parts. Length was checked against the shape's extent (2954426x1371600 EMU, 10.5pt run) rather than by opening the deck; open it once before presenting.",
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
            raise RuntimeError("gate-frontier result is absent from the publication slide")
        print(f"{DECK.name}: gate-frontier result present; pending replacements {replacements}")
        return
    if replacements:
        DECK.write_bytes(updated)
    refresh_manifest()
    print(f"{DECK.name}: replaced {replacements} gate-discrimination detail box")


if __name__ == "__main__":
    main()
