#!/usr/bin/env python3
"""Refresh the evidence-first NESTFUL example on the shipped technical deck.

The artifact-tool presentation workspace used by ``generate_slides.mjs`` is not part of
this repository.  This narrow, assertive transform therefore updates only the reviewed
slide's text after the pinned generator/restyle pipeline.  It never changes the template,
slide order, charts, or other slide content.
"""

from __future__ import annotations

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[2]
DECK = ROOT / "paper/slides/compiling-recurrent-agent-workflows-into-guarded-programs-detailed.pptx"
SLIDE = "ppt/slides/slide17.xml"


def replace_once(blob: bytes, old: str, new: str) -> bytes:
    old_tag = f"<a:t>{escape(old)}</a:t>".encode("utf-8")
    new_tag = f"<a:t>{escape(new)}</a:t>".encode("utf-8")
    count = blob.count(old_tag)
    if count != 1:
        raise RuntimeError(f"expected one occurrence of {old!r}, found {count}")
    return blob.replace(old_tag, new_tag, 1)


def refresh(deck: bytes) -> bytes:
    from io import BytesIO

    source = BytesIO(deck)
    output = BytesIO()
    with ZipFile(source) as zin, ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as zout:
        for item in zin.infolist():
            content = zin.read(item.filename)
            if item.filename == SLIDE:
                full_replacements = {
                    "Provenance succeeds; certification does not":
                        "Replay passes; the gate still refuses",
                    "Recurrence is fragmented: 714 candidate families exist, only 32 have support of at least five, and the best reaches 26 groups.":
                        "One NESTFUL trace looks like an obvious macro:",
                    "Of 32 attempted families, 12 synthesize. Their 36 held-out windows give 24 passes, 12 abstentions and zero wrong executions.":
                        "subtract(60,50) → divide(result,50) → multiply(result,100)",
                    "Zero wrong does not certify the programs. The gate needs 92 zero-violation groups, so every family retires.":
                        "Grounded, executable, and recurrent at the raw sequence level (33 records).",
                    "A scientifically useful negative result. ":
                        "Naive rule: recurrence + replay → ship.",
                    "It is what distinguishes a guarded compiler from a recurrence-only macro miner — and it exposes the data requirement instead of hiding it in a heuristic.":
                        "GAC: 26 groups < 92 required → 0 certifiable families → RETIRE to baseline.",
                    "Replay still looks reassuring: 24 pass / 12 abstain / 0 wrong across 32 attempted families.":
                        "Naive rule: recurrence + replay → ship.",
                    "GAC still asks: can evidence certify replacement on a new episode?":
                        "GAC: 26 groups < 92 required → 0 certifiable families → RETIRE to baseline.",
                    "1,207 / 1,415": "5,531 / 5,746",
                    "complete groundable windows (85.3%)": "candidate producers (96.3%)",
                    "12 / 32": "33",
                    "families synthesized": "raw sequence support",
                    "24 / 12 / 0": "24 / 12 / 0",
                    "held-out pass / abstain / wrong": "replay pass / abstain / wrong",
                    "0": "26 / 92",
                    "certifiable families": "best family / gate minimum",
                }
                current_replacements = {
                    "Replay still looks reassuring: 24 pass / 12 abstain / 0 wrong across 32 attempted families.":
                        "Naive rule: recurrence + replay → ship.",
                    "GAC still asks: can evidence certify replacement on a new episode?":
                        "GAC: 26 groups < 92 required → 0 certifiable families → RETIRE to baseline.",
                }
                replacements = (
                    full_replacements
                    if b"Provenance succeeds; certification does not" in content
                    else current_replacements
                )
                for old, new in replacements.items():
                    content = replace_once(content, old, new)
            zout.writestr(item, content)
    return output.getvalue()


def main() -> None:
    original = DECK.read_bytes()
    updated = refresh(original)
    if updated == original:
        raise RuntimeError("the deck was not changed")
    DECK.write_bytes(updated)
    print(f"updated {DECK} (slide 17 evidence example)")


if __name__ == "__main__":
    main()
