#!/usr/bin/env python3
"""Retitle the generated publication decks in place.

Why this exists
---------------
`generate_slides.mjs` rebuilds the decks from the two source templates, but it
requires an external artifact-tool presentation workspace that is not part of
this repository. When the paper was retitled, the decks therefore could not be
regenerated. This script performs the narrow edit the regeneration would have
made, so the shipped decks stop contradicting the manuscript.

It touches only the two *generated* decks. `GAC-seminar.pptx` and
`GAC-technical-review.pptx` are user-supplied source templates whose hashes the
generator verifies; editing them would break generation.

What it changes
---------------
* every ``<a:t>`` run containing the old title, in any slide;
* the title-slide font size, because the new title is 31 characters longer and
  at the original size it overflows its text box (measured in Cambria at the
  real box width: 2.40in of text in a 1.70in box, which would collide with the
  subtitle beneath it);
* ``<a:normAutofit/>`` on the title body, so PowerPoint re-fits if a renderer
  disagrees with that measurement;
* ``<dc:title>`` in docProps, which was the placeholder "Presentation".

Re-running is safe: the text replacement is a no-op once applied, and the font
sizes are matched exactly so they are not reduced twice.

    python paper/scripts/retitle_slides.py [--check]
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

SLIDES = Path(__file__).resolve().parents[1] / "slides"

OLD_TITLE = "Compiling Recurrent Agent Workflows into Guarded Programs"
NEW_TITLE = (
    "From Traces to Guarded Programs: "
    "Evidence-Gated Compilation of Recurrent Agent Workflows"
)

# deck -> (old title-slide font size in hundredths of a point, new size)
# Sizes were chosen by measuring the wrapped height of NEW_TITLE in Cambria at
# each deck's actual title-box width; both land just inside the existing box.
DECKS = {
    "compiling-recurrent-agent-workflows-into-guarded-programs.pptx": (3600, 3200),
    "compiling-recurrent-agent-workflows-into-guarded-programs-detailed.pptx": (3700, 3300),
}


def patch_slide_xml(xml: str, old_sz: int, new_sz: int) -> tuple[str, int]:
    """Return (patched xml, number of title runs replaced)."""
    if OLD_TITLE not in xml:
        return xml, 0
    n = xml.count(OLD_TITLE)
    xml = xml.replace(OLD_TITLE, NEW_TITLE)

    # Shrink only the run that *is* the title (a whole-run match), never the
    # footer line that merely embeds it followed by other text.
    title_run = f"<a:t>{NEW_TITLE}</a:t>"
    idx = xml.find(title_run)
    if idx != -1:
        start = xml.rfind("<p:sp>", 0, idx)
        end = xml.find("</p:sp>", idx)
        shape = xml[start:end]
        patched = shape.replace(f'sz="{old_sz}"', f'sz="{new_sz}"', 1)
        # Let PowerPoint re-fit as a backstop against font-metric differences.
        if "normAutofit" not in patched and "<a:bodyPr" in patched:
            patched = re.sub(
                r"(<a:bodyPr\b[^>]*?)\s*/>",
                r"\1><a:normAutofit/></a:bodyPr>",
                patched,
                count=1,
            )
        xml = xml[:start] + patched + xml[end:]
    return xml, n


def process(path: Path, old_sz: int, new_sz: int, check: bool) -> int:
    replaced = 0
    with zipfile.ZipFile(path) as zin:
        items = [(i, zin.read(i.filename)) for i in zin.infolist()]

    out: list[tuple[zipfile.ZipInfo, bytes]] = []
    for info, data in items:
        name = info.filename
        if name.startswith("ppt/slides/slide") and name.endswith(".xml"):
            xml = data.decode("utf-8")
            xml, n = patch_slide_xml(xml, old_sz, new_sz)
            replaced += n
            data = xml.encode("utf-8")
        elif name == "docProps/core.xml":
            xml = data.decode("utf-8")
            xml = re.sub(r"<dc:title>[^<]*</dc:title>",
                         f"<dc:title>{NEW_TITLE}</dc:title>", xml)
            data = xml.encode("utf-8")
        out.append((info, data))

    if check or replaced == 0:
        return replaced

    tmp = path.with_suffix(".pptx.tmp")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for info, data in out:
            zout.writestr(info, data)
    shutil.move(tmp, path)
    return replaced


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="report what would change without writing")
    args = ap.parse_args()

    total = 0
    for name, (old_sz, new_sz) in DECKS.items():
        path = SLIDES / name
        if not path.exists():
            print(f"  MISSING {name}", file=sys.stderr)
            return 1
        n = process(path, old_sz, new_sz, args.check)
        total += n
        verb = "would replace" if args.check else "replaced"
        print(f"  {name}: {verb} {n} title run(s)")
    if total == 0:
        print("  nothing to do - decks already carry the current title")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
