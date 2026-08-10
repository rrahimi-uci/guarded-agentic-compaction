#!/usr/bin/env python3
"""Restyle the technical-review deck onto the seminar deck's design system.

Why this exists
---------------
Two publication decks were rendered from two different user-supplied source
templates: the 25-slide navy/teal ``GAC-seminar.pptx`` and the 21-slide
dark-teal ``GAC-technical-review.pptx``.  They therefore shipped two unrelated
visual systems -- different palettes, different letter-spacing, and a different
narrative skeleton.  ``GAC-seminar.pptx`` is the canonical one, so the detailed
deck is brought onto its formula.

One deck ships now.  The 27-slide seminar deck and
``GAC-technical-review.pptx`` were both retired once this script made the
technical deck carry the seminar design system; ``paper/slides/gac-template-map.json``
declares each retirement with the hash it was last verified at.

``generate_slides.mjs`` cannot do this: it needs an external artifact-tool
presentation workspace that is not part of this repository.  This script
performs the edit the regeneration would have made, in place, on the *generated*
technical deck only.  ``GAC-seminar.pptx`` is read for its design tokens and its
section-divider frame, against the hash pinned below; it is never written.

What it changes
---------------
1. **Palette.**  Every deck colour is remapped from the dark-teal system to the
   seminar's navy/teal system (see ``PALETTE``).  The technical deck carried
   three body-ink tones where the seminar carries two, so the extra tone
   collapses onto the seminar's body ink.  Teal cards additionally take the
   seminar's teal card border rather than the neutral hairline.
2. **Typography.**  The seminar tracks its all-caps labels; the technical deck
   did not.  Eyebrows get ``spc=180``, the title-slide eyebrow ``spc=220``,
   section sub-heads ``spc=180`` in the muted ink rather than the accent, inline
   evidence-band labels ``spc=110``, and the running footer ``spc=100``.
3. **Header and footer geometry.**  Footer band, page number, eyebrow, and title
   boxes are set to the seminar's boxes and top-anchored, replacing the
   technical deck's centre-anchored variants.
4. **Section dividers.**  The technical deck ran 23 slides with no act breaks.
   Three dividers are inserted, built from the seminar's own divider frame, so
   the deck carries the seminar's three-act skeleton (26 slides).
5. **Eyebrows carry paper coordinates.**  The seminar names the section,
   algorithm, table, or research question each slide answers.  The technical
   deck's narrative labels are extended with those coordinates, read off the
   current manuscript -- *not* copied from the seminar deck, whose own
   coordinates predate the sections and tables the paper has since gained.
6. **Dark-slide furniture.**  The decorative circles on the title and closing
   slides take the seminar's positions, diameters, and alphas, and the title
   slide gains the seminar's hairline rule above its three-column proof strip.
7. **Native editable charts.**  The five charts were stored off-spec under
   ``ppt/slides/charts/`` with no embedded workbook, so PowerPoint could not
   edit their data.  They move to ``ppt/charts/`` and each gains a generated
   workbook, matching the seminar deck.  Two charts cached three data points
   against a two-row range; the ranges are corrected to the cached data.

What it does not change
-----------------------
The seminar renders its display maths as PNGs and numbers the equations in the
margin.  The technical deck states the same material as prose and has no
equations to number, so that part of the formula has nothing to attach to.
Adding rendered maths would be new content, not a restyle.

Re-running is safe: an already-restyled deck is detected and left alone.  The
transform itself is not idempotent -- it reads the generator's 23-slide,
off-spec-chart layout -- so it refuses to run twice rather than corrupting a
deck it has already rewritten.

    python paper/scripts/restyle_detailed_deck.py [--check]

After applying, refresh the recorded hashes and re-validate::

    python paper/scripts/finalize_manifest.py
    python paper/scripts/validate_artifacts.py
"""

from __future__ import annotations

import argparse
import hashlib
import io
import re
import sys
import zipfile
from pathlib import Path

SLIDES = Path(__file__).resolve().parents[1] / "slides"
TARGET = SLIDES / "compiling-recurrent-agent-workflows-into-guarded-programs-detailed.pptx"
STYLE_SOURCE = SLIDES / "GAC-seminar.pptx"

# Pinned so a restyle can never silently read a different design system. Refresh
# together with paper/slides/gac-template-map.json if the template is revised.
STYLE_SOURCE_SHA256 = "a5204149a5fdc2dc4e2e2f79a6926a17336a3e5c5740b5ebb7d95ec7c59df8a0"

# The seminar divider frame lives on source slide 5 (act I).
DIVIDER_TEMPLATE_PART = "ppt/slides/slide5.xml"

# Fixed so the same input always produces the same package bytes, which is what
# lets paper/results/slide_generation.json pin an output hash at all.
ZIP_DATE = (2026, 8, 10, 0, 0, 0)

# --------------------------------------------------------------------------- #
# 1. Palette
# --------------------------------------------------------------------------- #
# dark-teal technical system -> navy/teal seminar system. No target value is
# also a source key, so a single pass cannot chain one substitution into another.
PALETTE = {
    "0E272C": "0E1E3A",  # dark slide background
    "0D4A54": "0E1E3A",  # heading / title ink
    "2A4247": "24354F",  # body ink
    "3A5257": "24354F",  # second body ink -> the seminar carries only one
    "5F767A": "5A6B84",  # muted ink and sub-heads
    "9FB2B5": "A3B2C4",  # running footer on light slides
    "4C6B70": "43597C",  # running footer on dark slides
    "17798A": "1F8A99",  # primary accent
    "4EA3B0": "56B3BE",  # light accent
    "9CC7CE": "9BD0D6",  # pale accent on dark slides
    "AC4A2C": "A93B2B",  # alert
    "5A3A2E": "5C4034",  # alert-card body ink
    "4A3226": "4E3529",  # alert-card deep ink
    "F5FAFB": "F5F9FC",  # neutral card fill
    "EAF3F5": "E8F4F5",  # accent card fill
    "F7ECE7": "FBF0EC",  # alert card fill
    "D3E3E6": "D5E0EB",  # hairline / table rule
    "EBD5CC": "EFDCD4",  # alert card border
    "EAF0F1": "EAF1F7",  # tinted band fill
    "DCE8EA": "D5E0EB",  # light rule
    "8FA9AE": "94A6BC",  # card shadow
    "E6EEF0": "E7EDF3",  # chart gridline
}

# Seminar-only tokens the technical deck had no equivalent for.
CARD_ACCENT_FILL = "E8F4F5"
CARD_ACCENT_BORDER = "CFE4E7"
TITLE_STRIP_INK = "8FA6C0"  # title-slide caption ink
DARK_RULE = "2C4467"
DEEP_DECOR = "1A3563"  # decorative circle on a dark slide

# The technical deck drew its largest decorative circle in the same colour as
# its dark background, so under the palette map it would become invisible. The
# seminar draws it one step lighter than the background; retarget the fill and
# its matching outline before the map runs. The alpha requirement keeps this off
# the heading ink, which is the same token on the light slides.
DEEP_DECOR_RE = re.compile(
    r'<a:srgbClr val="0D4A54"><a:alpha val="(\d+)" /></a:srgbClr></a:solidFill>'
    r'(<a:ln\b[^>]*><a:solidFill><a:srgbClr val=")0D4A54(" />)'
)

_PALETTE_RE = re.compile(
    r'val="(' + "|".join(sorted(PALETTE)) + r')"'
)

# --------------------------------------------------------------------------- #
# 2. Geometry (exact source bytes -> seminar bytes)
# --------------------------------------------------------------------------- #
FOOTER_BAND_OFF = '<a:off x="640080" y="6327648" /><a:ext cx="4572000" cy="274320" />'
FOOTER_BAND_NEW = '<a:off x="640080" y="6345936" /><a:ext cx="5486400" cy="256032" />'
PAGE_NUM_OFF = '<a:off x="10637215" y="6327648" /><a:ext cx="914400" cy="274320" />'
PAGE_NUM_NEW = '<a:off x="10637215" y="6345936" /><a:ext cx="914400" cy="256032" />'
TITLE_BOX_OFF = '<a:off x="640080" y="658368" /><a:ext cx="10911535" cy="566928" />'
TITLE_BOX_NEW = '<a:off x="640080" y="658368" /><a:ext cx="10911535" cy="502920" />'

EYEBROW_Y = 384048  # 0.42in
TITLE_Y = 658368  # 0.72in
FOOTER_Y = 6327648  # 6.92in
PAGE_NUM_X = 10637215
TITLE_SLIDE_EYEBROW_Y = 1417320  # 1.55in

# Decorative circles on the dark slides: technical geometry -> seminar geometry.
DARK_FURNITURE = [
    # title slide
    ('<a:off x="8686800" y="-1371600" /><a:ext cx="5852160" cy="5852160" />',
     '<a:off x="9052560" y="-1554480" /><a:ext cx="6217920" cy="6217920" />'),
    ('<a:off x="9966960" y="-91440" /><a:ext cx="3291840" cy="3291840" />',
     '<a:off x="10424160" y="-91440" /><a:ext cx="3291840" cy="3291840" />'),
    ('<a:off x="10835640" y="777240" /><a:ext cx="1554480" cy="1554480" />',
     '<a:off x="11338560" y="822960" /><a:ext cx="1463040" cy="1463040" />'),
    # closing slide
    ('<a:off x="11201400" y="4892040" /><a:ext cx="4023360" cy="4023360" />',
     '<a:off x="11247120" y="4846320" /><a:ext cx="4023360" cy="4023360" />'),
    ('<a:off x="11932920" y="5623560" /><a:ext cx="2011680" cy="2011680" />',
     '<a:off x="11978640" y="5577840" /><a:ext cx="2011680" cy="2011680" />'),
]

# Alphas on those circles, keyed by the colour they sit on (post-palette values).
DARK_FURNITURE_ALPHA = [
    ('<a:srgbClr val="1A3563"><a:alpha val="55000" /></a:srgbClr>',
     '<a:srgbClr val="1A3563"><a:alpha val="62000" /></a:srgbClr>'),
    ('<a:srgbClr val="1F8A99"><a:alpha val="45000" /></a:srgbClr>',
     '<a:srgbClr val="1F8A99"><a:alpha val="48000" /></a:srgbClr>'),
    ('<a:srgbClr val="56B3BE"><a:alpha val="70000" /></a:srgbClr>',
     '<a:srgbClr val="56B3BE"><a:alpha val="72000" /></a:srgbClr>'),
]
CLOSING_FURNITURE_ALPHA = [
    ('<a:srgbClr val="1A3563"><a:alpha val="55000" /></a:srgbClr>',
     '<a:srgbClr val="1A3563"><a:alpha val="58000" /></a:srgbClr>'),
    ('<a:srgbClr val="1F8A99"><a:alpha val="50000" /></a:srgbClr>',
     '<a:srgbClr val="1F8A99"><a:alpha val="52000" /></a:srgbClr>'),
]

# --------------------------------------------------------------------------- #
# 3. Eyebrows: narrative label + the manuscript coordinate it answers
# --------------------------------------------------------------------------- #
# Section, algorithm, and table numbers are those of the current manuscript
# (paper/tex/body.tex, as typeset in the committed PDF), not the numbers the
# seminar deck carries -- the paper has gained subsections 3.3/3.4 and eight
# tables since that deck was rendered.
DOT = "  ·  "
EYEBROWS = {
    2: ["THE SHORT VERSION", "§1"],
    3: ["MOTIVATION", "§1"],
    4: ["MOTIVATION", "WHY THIS IS NOT CACHING", "§1 AND §2.1"],
    5: ["SCOPE", "§1"],
    6: ["FORMULATION", "§2.1–2.2"],
    7: ["METHOD", "ARCHITECTURE", "FIGURE 1"],
    8: ["METHOD", "ALGORITHM 1"],
    9: ["METHOD", "REJECTION POINT 2", "ALGORITHM 2 (BUILDPATG)"],
    # Boundary-time dispatch is not one of the six offline rejection points, so
    # this one is labelled by its phase rather than given a point number.
    10: ["METHOD", "RUNTIME", "§3.7 AND ALGORITHM 4"],
    11: ["METHOD", "REJECTION POINT 6", "§3.5 AND ALGORITHM 3"],
    12: ["METHOD", "REJECTION POINT 3", "§3.1–3.2"],
    13: ["METHODOLOGY", "§4.1", "TABLE 3"],
    14: ["RESULTS", "RQ1 AND RQ3", "§5.1", "TABLE 4"],
    15: ["RESULTS", "RQ6", "§5.2", "TABLE 5"],
    16: ["RESULTS", "RQ2", "§5.3", "TABLE 6"],
    17: ["RESULTS", "THE DEPTH TRADE-OFF", "§5.3", "TABLES 6 AND 7"],
    18: ["RESULTS", "RQ4", "§5.4", "FIGURE 6"],
    19: ["RESULTS", "THE COMPARATOR THAT MATTERS", "§5.6", "TABLE 8"],
    20: ["RESULTS", "FAIR PLACEMENT AND BOUNDED GEPA", "§5.7–5.8", "TABLES 10 AND 11"],
    21: ["RESULTS", "RQ5", "§3.6 AND §5.9", "TABLE 15"],
    22: ["LIMITATIONS AND THREATS TO VALIDITY", "§8"],
    23: ["CONCLUSION", "§9"],
}
# The seminar sets the limitations eyebrow in the alert colour, not the accent.
ALERT_EYEBROW_SLIDES = {22}

# --------------------------------------------------------------------------- #
# Type density
# --------------------------------------------------------------------------- #
# Two paragraphs were set far denser than the seminar's scale allows and
# overflowed their boxes in the generated deck: a 501-character alert body at
# 12pt in a 5.65in box, which clipped its last line against the card edge, and a
# 330-character lede at 13pt in a 0.5in box, which ran into the sub-head beneath
# it. The seminar sets ~500 characters in a ~5.5in box at 9.5-10pt and its
# full-width lede at 12.5pt in a 0.62in box, so both come down to that scale.
# Keyed by old slide number; the text prefix keeps each edit to one paragraph.
FONT = (
    '<a:latin typeface="Calibri" /><a:ea typeface="Calibri" />'
    '<a:cs typeface="Calibri" /></a:rPr><a:t>'
)
DENSITY_FIXES = {
    15: [
        (
            f'<a:rPr sz="1200" b="1"><a:solidFill><a:srgbClr val="AC4A2C" />'
            f"</a:solidFill>{FONT}The two new families",
            f'<a:rPr sz="1000" b="1"><a:solidFill><a:srgbClr val="AC4A2C" />'
            f"</a:solidFill>{FONT}The two new families",
        ),
    ],
    19: [
        (
            f'<a:rPr sz="1300"><a:solidFill><a:srgbClr val="2A4247" />'
            f"</a:solidFill>{FONT}Against partial GRC",
            f'<a:rPr sz="1150"><a:solidFill><a:srgbClr val="2A4247" />'
            f"</a:solidFill>{FONT}Against partial GRC",
        ),
        (
            '<a:off x="640080" y="1371600" /><a:ext cx="10911535" cy="457200" />',
            '<a:off x="640080" y="1371600" /><a:ext cx="10911535" cy="566928" />',
        ),
    ],
}

# --------------------------------------------------------------------------- #
# Slide titles
# --------------------------------------------------------------------------- #
# The generated headlines ran 52-75 characters, most of them two clauses where
# the second clause repeats something the body or the eyebrow already says.
# Each one below keeps the slide's claim and drops the restatement. The old text
# is matched exactly so an upstream rewording fails loudly instead of silently
# leaving a long headline in place.
#
# Three of these are written by generate_slides.mjs rather than inherited from
# the template -- the two inserted evidence slides (15, 20) and the comparator
# slide (19). Shortening them here is legitimate because restyle runs after
# generation, so generate -> retitle -> restyle reproduces the short form; the
# generator still emits its own longer strings. Keyed by old slide number.
#
# The title slide is untouched: slide 1 carries the manuscript title verbatim.
TITLES = {
    2: (
        "Recurrence tells you a region repeats — not that it may be replaced",
        "Recurrence is not permission",
    ),
    3: (
        "Four model calls for three decisions the trace already fixed",
        "Four model calls, three already decided",
    ),
    4: (
        "Four ways a repeated region can still be inadmissible",
        "Four hazards a cache cannot see",
    ),
    6: (
        "A guarded specialization of the routine part of a workflow",
        "Guarded specialization, defined",
    ),
    7: (
        "Capture offline, compile offline, resolve at the entry boundary",
        "Capture, compile, dispatch at the boundary",
    ),
    8: (
        "Six independent rejection points — refusal is the default output",
        "Refusal is the default output",
    ),
    9: (
        "Typed provenance: a slot with no witness is a genuine model decision",
        "No witness means a real model decision",
    ),
    10: (
        "The artifact carries its own preconditions — and usually declines",
        "The artifact usually declines to run",
    ),
    11: (
        "The admission gate is exact — and therefore data-hungry",
        "An exact gate is a data-hungry gate",
    ),
    12: (
        "Decline a workload before you build a compiler for it",
        "Decline before you build",
    ),
    13: (
        "Three evidence tiers, ordered by what each can license",
        "Three tiers, ordered by what they license",
    ),
    14: (
        "Provenance succeeds far more often than certification",
        "Provenance succeeds; certification does not",
    ),
    15: (
        "Efficiency transfers; manual programs remain the runtime baseline",
        "Efficiency transfers, not dominance",
    ),
    16: (
        "30 unseen real issues: half the requests, quality held",
        "Half the requests, quality held",
    ),
    17: (
        "Preservation is not invariant to how deep you compile",
        "Deeper compilation costs preservation",
    ),
    18: (
        "Token saving and cost saving can have opposite signs",
        "Token saving is not cost saving",
    ),
    19: (
        "Before GCS, the hand macro is the stronger fixed-workflow baseline",
        "Before GCS, the hand macro wins",
    ),
    # Keeps the "Fair placement ties GCS" phrase validate_artifacts.py pins;
    # "GEPA retains its seed" survives twice in this slide's body.
    20: (
        "Fair placement ties GCS; bounded GEPA retains its seed",
        "Fair placement ties GCS",
    ),
    21: (
        "A portfolio layer that only compares things it has measured",
        "Only measured actions get compared",
    ),
    22: (
        "Five claims the evidence deliberately does not support",
        "Five claims the evidence does not support",
    ),
    23: (
        "Judge an agent optimizer by what it refuses, not only by what it compresses",
        "Judge an optimizer by what it refuses",
    ),
}
# Slide 5's headline, "The question, stated narrowly", is already short.
TITLE_LENGTH_LIMIT = 45

# --------------------------------------------------------------------------- #
# 4. Section dividers (new slide index -> numeral, title, dek, speaker note)
# --------------------------------------------------------------------------- #
DIVIDERS = {
    3: (
        "I",
        "Problem formulation",
        "Where a mature agent spends model calls, why recurrence alone cannot "
        "license removing them, and the narrow question this paper answers.",
        "Act break. Everything before this slide is motivation; everything after "
        "it is the formal problem, stated narrowly enough to be refutable.",
    ),
    8: (
        "II",
        "Guarded agentic compaction",
        "Capture offline, compile offline, dispatch at the entry boundary — "
        "six independent rejection points, with refusal as the default output.",
        "Act break. The method act. If a reviewer only remembers one thing from "
        "it, make it that every stage can return Retire with an attributed reason.",
    ),
    15: (
        "III",
        "Evidence and results",
        "Three evidence tiers, six directional hypotheses, and every result "
        "reported with its denominator and its refusals intact.",
        "Act break. From here on every number is paired with what it does not "
        "establish; that pairing is the point of the tier ordering.",
    ),
}

TOTAL_SLIDES = 23 + len(DIVIDERS)

# --------------------------------------------------------------------------- #
# Content types and relationship boilerplate
# --------------------------------------------------------------------------- #
CT_HEADER = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
)
CT_TYPES = {
    "sldMaster": "application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml",
    "sldLayout": "application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml",
    "slide": "application/vnd.openxmlformats-officedocument.presentationml.slide+xml",
    "notesSlide": "application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml",
    "notesMaster": "application/vnd.openxmlformats-officedocument.presentationml.notesMaster+xml",
    "theme": "application/vnd.openxmlformats-officedocument.theme+xml",
    "chart": "application/vnd.openxmlformats-officedocument.drawingml.chart+xml",
}
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def rel(kind: str) -> str:
    return f"{REL_NS}/{kind}"


def relationships(items: list[tuple[str, str, str]]) -> bytes:
    """items: (Id, relationship kind, absolute part target)."""
    body = "".join(
        f'<Relationship Type="{rel(kind)}" Target="{target}" Id="{rid}" />'
        for rid, kind, target in items
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{body}</Relationships>"
    ).encode("utf-8")


# --------------------------------------------------------------------------- #
# Slide-body transforms
# --------------------------------------------------------------------------- #
SP_RE = re.compile(r"<p:sp>.*?</p:sp>", re.S)
OFF_RE = re.compile(r'<a:off x="(-?\d+)" y="(-?\d+)" />')
RUN_RE = re.compile(r"<a:r>(.*?)</a:r>", re.S)
RPR_RE = re.compile(r"<a:rPr\b([^>]*)>")
TEXT_RE = re.compile(r"<a:t>(.*?)</a:t>", re.S)


def _attr(attrs: str, name: str) -> str | None:
    m = re.search(rf'\b{name}="([^"]*)"', attrs)
    return m.group(1) if m else None


def _with_spc(attrs: str, spc: int) -> str:
    if _attr(attrs, "spc") is not None:
        return re.sub(r'\bspc="[^"]*"', f'spc="{spc}"', attrs)
    return attrs.rstrip() + f' spc="{spc}"'


def _is_label(text: str) -> bool:
    """An all-caps section sub-head, not a badge glyph or a numeral.

    Case is judged on the ASCII letters only, so a label carrying a Greek
    symbol -- ``WHAT α ACTUALLY BOUNDS`` -- still counts. Requiring a space and
    eight characters keeps the badge glyphs (``M``, ``RQ1``, ``✓``) out.
    """
    letters = [ch for ch in text if ch.isascii() and ch.isalpha()]
    return (
        bool(letters)
        and all(ch.isupper() for ch in letters)
        and " " in text
        and len(text) >= 8
    )


def _recolour_run(run: str, colour: str) -> str:
    return re.sub(r'<a:srgbClr val="[0-9A-F]{6}" />', f'<a:srgbClr val="{colour}" />', run, count=1)


def _set_anchor(block: str, anchor: str) -> str:
    return re.sub(r'\banchor="[^"]*"', f'anchor="{anchor}"', block, count=1)


def _track_runs(block: str, sizes: dict[int, int], colour: str | None = None) -> str:
    """Apply letter-spacing (and optionally a colour) to all-caps label runs."""

    def fix(match: re.Match[str]) -> str:
        run = match.group(0)
        rpr = RPR_RE.search(run)
        text_m = TEXT_RE.search(run)
        if not rpr or not text_m:
            return run
        attrs = rpr.group(1)
        if _attr(attrs, "b") != "1":
            return run
        try:
            size = int(_attr(attrs, "sz") or "0")
        except ValueError:
            return run
        if size not in sizes or not _is_label(text_m.group(1)):
            return run
        out = run[: rpr.start(1)] + _with_spc(attrs, sizes[size]) + run[rpr.end(1):]
        if colour:
            out = _recolour_run(out, colour)
        return out

    return RUN_RE.sub(fix, block)


def eyebrow_text(old_index: int) -> str:
    return DOT.join(EYEBROWS[old_index])


def transform_slide(xml: str, old_index: int, new_index: int) -> str:
    """Apply the seminar formula to one technical-deck slide."""
    for needle, replacement in DENSITY_FIXES.get(old_index, ()):
        if needle not in xml:
            raise SystemExit(
                f"slide {old_index}: density fix no longer matches: {needle[:60]}..."
            )
        xml = xml.replace(needle, replacement, 1)

    cursor = 0
    result: list[str] = []

    for match in SP_RE.finditer(xml):
        result.append(xml[cursor:match.start()])
        cursor = match.end()
        block = match.group(0)
        off = OFF_RE.search(block)
        x = int(off.group(1)) if off else None
        y = int(off.group(2)) if off else None
        # An eyebrow is tracked and coloured by its own rule below; the generic
        # sub-head rule must not then repaint it in the muted ink.
        is_eyebrow = False

        if y == FOOTER_Y and x == 640080:
            # Running footer: seminar box, top-anchored, tracked.
            block = block.replace(FOOTER_BAND_OFF, FOOTER_BAND_NEW)
            block = _set_anchor(block, "t")
            block = re.sub(
                r'(<a:rPr sz="900")>', r'\1 spc="100">', block, count=1
            )
        elif y == FOOTER_Y and x == PAGE_NUM_X:
            # Page number: seminar box, top-anchored, renumbered.
            block = block.replace(PAGE_NUM_OFF, PAGE_NUM_NEW)
            block = _set_anchor(block, "t")
            block = TEXT_RE.sub(f"<a:t>{new_index}</a:t>", block, count=1)
        elif y == EYEBROW_Y and old_index in EYEBROWS:
            # Eyebrow: top-anchored, tracked at 180, carrying the coordinate.
            is_eyebrow = True
            block = _set_anchor(block, "t")
            block = re.sub(
                r'(<a:rPr sz="1050" b="1")>', r'\1 spc="180">', block, count=1
            )
            block = TEXT_RE.sub(f"<a:t>{eyebrow_text(old_index)}</a:t>", block, count=1)
            if old_index in ALERT_EYEBROW_SLIDES:
                block = block.replace('val="17798A"', 'val="AC4A2C"', 1)
        elif y == TITLE_Y:
            # The closing slide's headline sits in its own wider box, so the
            # standard-box normalization is conditional but the retitle is not.
            block = block.replace(TITLE_BOX_OFF, TITLE_BOX_NEW)
            if old_index in TITLES:
                old_title, new_title = TITLES[old_index]
                needle = f"<a:t>{old_title}</a:t>"
                if needle not in block:
                    raise SystemExit(
                        f"slide {old_index}: headline is no longer {old_title!r}"
                    )
                block = block.replace(needle, f"<a:t>{new_title}</a:t>", 1)
        elif old_index == 1 and y == TITLE_SLIDE_EYEBROW_Y:
            # Title-slide eyebrow: the seminar sets 10.5pt tracked at 220.
            is_eyebrow = True
            block = _set_anchor(block, "t")
            block = block.replace(
                '<a:rPr sz="1100" b="1">', '<a:rPr sz="1050" b="1" spc="220">', 1
            )

        if not is_eyebrow:
            # Section sub-heads take the muted ink and 180; inline evidence-band
            # labels keep their accent and take 110.
            block = _track_runs(block, {1050: 180}, colour="5F767A")
            block = _track_runs(block, {950: 110})

        result.append(block)

    result.append(xml[cursor:])
    xml = "".join(result)

    # Dark-slide furniture.
    if old_index in (1, 23):
        for old, new in DARK_FURNITURE:
            xml = xml.replace(old, new)
        xml = DEEP_DECOR_RE.sub(
            f'<a:srgbClr val="{DEEP_DECOR}"><a:alpha val="\\g<1>" /></a:srgbClr>'
            f"</a:solidFill>\\g<2>{DEEP_DECOR}\\g<3>",
            xml,
        )

    xml = apply_palette(xml)

    if old_index == 1:
        for old, new in DARK_FURNITURE_ALPHA:
            xml = xml.replace(old, new)
        xml = add_title_rule(xml)
        xml = recolour_title_strip(xml)
    if old_index == 23:
        for old, new in CLOSING_FURNITURE_ALPHA:
            xml = xml.replace(old, new)

    return accent_card_borders(xml)


def apply_palette(xml: str) -> str:
    return _PALETTE_RE.sub(lambda m: f'val="{PALETTE[m.group(1)]}"', xml)


def accent_card_borders(xml: str) -> str:
    """Accent cards take the seminar's accent border, not the neutral hairline."""
    pattern = re.compile(
        r'(val="' + CARD_ACCENT_FILL + r'" />\s*</a:solidFill>\s*<a:ln\b[^>]*>'
        r'\s*<a:solidFill>\s*<a:srgbClr val=")D5E0EB(")'
    )
    return pattern.sub(r"\g<1>" + CARD_ACCENT_BORDER + r"\g<2>", xml)


def recolour_title_strip(xml: str) -> str:
    """Title-slide captions use the seminar's title-strip ink."""
    return re.sub(
        r'(<a:rPr sz="1050"><a:solidFill><a:srgbClr val=")9BD0D6(" />)',
        r"\g<1>" + TITLE_STRIP_INK + r"\g<2>",
        xml,
    )


TITLE_RULE = (
    '<p:sp><p:nvSpPr><p:cNvPr id="200" name="Shape 200" /><p:cNvSpPr />'
    "<p:nvPr /></p:nvSpPr><p:spPr>"
    '<a:xfrm xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
    '<a:off x="640080" y="4590288" /><a:ext cx="7589520" cy="0" /></a:xfrm>'
    '<a:prstGeom prst="line" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
    "<a:avLst /></a:prstGeom>"
    '<a:noFill xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" />'
    '<a:ln w="12700" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
    f'<a:solidFill><a:srgbClr val="{DARK_RULE}" /></a:solidFill>'
    '<a:prstDash val="solid" /></a:ln></p:spPr><p:txBody>'
    '<a:bodyPr xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" />'
    '<a:lstStyle xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" />'
    '<a:p xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" />'
    "</p:txBody></p:sp>"
)


def add_title_rule(xml: str) -> str:
    """The seminar rules off the title slide's three-column proof strip."""
    if TITLE_RULE in xml:
        return xml
    return xml.replace("</p:spTree>", TITLE_RULE + "</p:spTree>", 1)


# --------------------------------------------------------------------------- #
# Section dividers
# --------------------------------------------------------------------------- #
def build_divider(template: str, page: int, numeral: str, title: str, dek: str) -> bytes:
    xml = template
    xml = xml.replace('<p:cSld name="Slide 5">', f'<p:cSld name="Divider {numeral}">', 1)
    xml = xml.replace("<a:t>5</a:t>", f"<a:t>{page}</a:t>", 1)
    xml = xml.replace("<a:t>I</a:t>", f"<a:t>{numeral}</a:t>", 1)
    xml = xml.replace("<a:t>Problem formulation</a:t>", f"<a:t>{title}</a:t>", 1)
    xml = re.sub(
        r"<a:t>Episodes, candidate regions.*?</a:t>", f"<a:t>{dek}</a:t>", xml, count=1, flags=re.S
    )
    return xml.encode("utf-8")


NOTES_TEMPLATE = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<p:notes xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
    "<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\" /><p:cNvGrpSpPr />"
    "<p:nvPr /></p:nvGrpSpPr><p:grpSpPr>"
    '<a:xfrm xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" />'
    "</p:grpSpPr>"
    '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Slide Image Placeholder 1" /><p:cNvSpPr>'
    '<a:spLocks noGrp="1" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" />'
    '</p:cNvSpPr><p:nvPr><p:ph type="sldImg" idx="0" /></p:nvPr></p:nvSpPr><p:spPr /></p:sp>'
    '<p:sp><p:nvSpPr><p:cNvPr id="3" name="Notes Placeholder 2" /><p:cNvSpPr>'
    '<a:spLocks noGrp="1" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" />'
    '</p:cNvSpPr><p:nvPr><p:ph type="body" idx="1" /></p:nvPr></p:nvSpPr><p:spPr />'
    '<p:txBody><a:bodyPr xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" />'
    '<a:lstStyle xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" />'
    '<a:p xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:r>'
    "<a:t>{note}</a:t></a:r></a:p></p:txBody></p:sp>"
    '<p:sp><p:nvSpPr><p:cNvPr id="4" name="Slide Number Placeholder 3" /><p:cNvSpPr>'
    '<a:spLocks noGrp="1" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" />'
    '</p:cNvSpPr><p:nvPr><p:ph type="sldNum" idx="5" /></p:nvPr></p:nvSpPr><p:spPr />'
    '<p:txBody><a:bodyPr xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" />'
    '<a:lstStyle xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" />'
    '<a:p xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" /></p:txBody></p:sp>'
    "</p:spTree></p:cSld><p:clrMapOvr>"
    '<a:masterClrMapping xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" />'
    "</p:clrMapOvr></p:notes>"
)


# --------------------------------------------------------------------------- #
# Charts: relocate, fix ranges, embed a workbook
# --------------------------------------------------------------------------- #
def _col(index: int) -> str:
    return chr(ord("A") + index)


def read_chart_series(xml: str) -> tuple[list[str], list[tuple[str, list[float | None]]]]:
    """Return (categories, [(series name, values)]) from the cached chart data."""
    categories: list[str] = []
    series: list[tuple[str, list[float | None]]] = []
    for ser in re.findall(r"<c:ser>.*?</c:ser>", xml, re.S):
        name_m = re.search(r"<c:tx>.*?<c:v>(.*?)</c:v>", ser, re.S)
        name = name_m.group(1) if name_m else ""

        cat_block = re.search(r"<c:cat>(.*?)</c:cat>", ser, re.S)
        if cat_block and not categories:
            count = int(re.search(r'ptCount val="(\d+)"', cat_block.group(1)).group(1))
            categories = [""] * count
            for idx, value in re.findall(
                r'<c:pt idx="(\d+)"\s*>\s*<c:v>(.*?)</c:v>', cat_block.group(1), re.S
            ):
                categories[int(idx)] = value

        val_block = re.search(r"<c:val>(.*?)</c:val>", ser, re.S)
        values: list[float | None] = []
        if val_block:
            count = int(re.search(r'ptCount val="(\d+)"', val_block.group(1)).group(1))
            values = [None] * count
            for idx, value in re.findall(
                r'<c:pt idx="(\d+)"\s*>\s*<c:v>(.*?)</c:v>', val_block.group(1), re.S
            ):
                values[int(idx)] = float(value)
        series.append((name, values))
    return categories, series


def patch_chart(xml: str, rows: int, series_count: int) -> str:
    """Point the cached ranges at the generated workbook and attach it.

    Two charts cached three points against a two-row range, so the ranges are
    rebuilt from the cached point count rather than adjusted in place.
    """
    last = rows + 1
    # Series names occupy $B$1, $C$1, ... in document order; re.sub walks the
    # document in that same order, so a single iterator assigns the columns.
    name_cols = iter(_col(index + 1) for index in range(series_count))
    xml = re.sub(
        r"<c:f>Sheet1!\$[A-Z]\$1</c:f>",
        lambda _m: f"<c:f>Sheet1!${next(name_cols)}$1</c:f>",
        xml,
    )
    value_cols = iter(_col(index + 1) for index in range(series_count))

    def value_ref(_match: re.Match[str]) -> str:
        column = next(value_cols)
        return f"<c:f>Sheet1!${column}$2:${column}${last}</c:f>"

    # Values before categories: rewriting categories first would turn every
    # range into an $A$ range and make the two indistinguishable.
    xml = re.sub(r"<c:f>Sheet1!\$[B-Z]\$2:\$[B-Z]\$\d+</c:f>", value_ref, xml)
    xml = re.sub(
        r"<c:f>Sheet1!\$A\$2:\$A\$\d+</c:f>",
        f"<c:f>Sheet1!$A$2:$A${last}</c:f>",
        xml,
    )

    external = (
        '<c:externalData xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
        ' r:id="rId1"><c:autoUpdate val="0" /></c:externalData>'
    )
    if "<c:externalData" not in xml:
        xml = xml.replace("</c:chartSpace>", external + "</c:chartSpace>", 1)
    return xml


def _xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def build_workbook(categories: list[str], series: list[tuple[str, list[float | None]]]) -> bytes:
    """A minimal, deterministic .xlsx holding the chart's data."""
    strings: list[str] = [""]
    index_of: dict[str, int] = {"": 0}

    def string_id(value: str) -> int:
        if value not in index_of:
            index_of[value] = len(strings)
            strings.append(value)
        return index_of[value]

    rows: list[str] = []
    header = ['<c r="A1" t="s"><v>0</v></c>']
    for column, (name, _values) in enumerate(series, start=1):
        header.append(f'<c r="{_col(column)}1" t="s"><v>{string_id(name)}</v></c>')
    rows.append(f'<row r="1" spans="1:{len(series) + 1}">{"".join(header)}</row>')

    for offset, category in enumerate(categories):
        row_number = offset + 2
        cells = [f'<c r="A{row_number}" t="s"><v>{string_id(category)}</v></c>']
        for column, (_name, values) in enumerate(series, start=1):
            value = values[offset] if offset < len(values) else None
            if value is None:
                continue
            rendered = f"{value:g}"
            cells.append(f'<c r="{_col(column)}{row_number}"><v>{rendered}</v></c>')
        rows.append(
            f'<row r="{row_number}" spans="1:{len(series) + 1}">{"".join(cells)}</row>'
        )

    last_cell = f"{_col(len(series))}{len(categories) + 1}"
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="A1:{last_cell}" />'
        '<sheetViews><sheetView tabSelected="1" workbookViewId="0" /></sheetViews>'
        '<sheetFormatPr baseColWidth="10" defaultRowHeight="16" />'
        f'<sheetData>{"".join(rows)}</sheetData>'
        '<pageMargins left="0.7" right="0.7" top="0.75" bottom="0.75" header="0.3" footer="0.3" />'
        "</worksheet>"
    )
    shared = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        f' count="{len(strings)}" uniqueCount="{len(strings)}">'
        + "".join(
            f'<si><t xml:space="preserve">{_xml_escape(value)}</t></si>' for value in strings
        )
        + "</sst>"
    )
    parts = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml" />'
            '<Default Extension="xml" ContentType="application/xml" />'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml" />'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml" />'
            '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml" />'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml" />'
            "</Types>"
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml" />'
            "</Relationships>"
        ),
        "xl/workbook.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
            ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1" /></sheets>'
            '<calcPr calcId="0" concurrentCalc="0" /></workbook>'
        ),
        "xl/_rels/workbook.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml" />'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml" />'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml" />'
            "</Relationships>"
        ),
        "xl/styles.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="1"><font><sz val="11" /><name val="Calibri" /></font></fonts>'
            '<fills count="2"><fill><patternFill patternType="none" /></fill>'
            '<fill><patternFill patternType="gray125" /></fill></fills>'
            '<borders count="1"><border /></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" /></cellStyleXfs>'
            '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" /></cellXfs>'
            "</styleSheet>"
        ),
        "xl/sharedStrings.xml": shared,
        "xl/worksheets/sheet1.xml": sheet,
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as book:
        for name, text in parts.items():
            info = zipfile.ZipInfo(name, ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            book.writestr(info, text.encode("utf-8"))
    return buffer.getvalue()


# --------------------------------------------------------------------------- #
# Repackaging
# --------------------------------------------------------------------------- #
def already_restyled(deck: bytes) -> bool:
    """True once the deck carries the seminar skeleton and on-spec chart parts."""
    with zipfile.ZipFile(io.BytesIO(deck)) as package:
        names = package.namelist()
        slides = [
            name for name in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
        ]
        return len(slides) == TOTAL_SLIDES and any(
            name.startswith("ppt/charts/chart") for name in names
        )


def build_slide_order() -> dict[int, int]:
    """old technical-deck slide number -> new slide number."""
    order: dict[int, int] = {}
    new_index = 1
    old_index = 1
    while old_index <= 23:
        if new_index in DIVIDERS:
            new_index += 1
            continue
        order[old_index] = new_index
        old_index += 1
        new_index += 1
    return order


def restyle(source: bytes, style_source: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(style_source)) as style:
        divider_template = style.read(DIVIDER_TEMPLATE_PART).decode("utf-8")
    if "r:embed" in divider_template or "r:id" in divider_template:
        raise SystemExit("divider frame unexpectedly references a relationship")

    order = build_slide_order()
    parts: dict[str, bytes] = {}
    # old slide -> (chart number, relationship id). The id is carried over
    # verbatim because the slide body names it in <c:chart r:id="...">.
    chart_for_slide: dict[int, tuple[int, str]] = {}

    with zipfile.ZipFile(io.BytesIO(source)) as deck:
        names = deck.namelist()

        # Which old slide owns which chart.
        for name in names:
            m = re.fullmatch(r"ppt/slides/_rels/slide(\d+)\.xml\.rels", name)
            if not m:
                continue
            rels = deck.read(name).decode("utf-8")
            chart = re.search(
                r'<Relationship\b[^>]*charts/chart(\d+)\.xml"[^>]*Id="([^"]+)"', rels
            )
            if chart:
                chart_for_slide[int(m.group(1))] = (int(chart.group(1)), chart.group(2))

        # Carry-through parts.
        for name in names:
            if re.fullmatch(r"ppt/(slides|notesSlides)/(_rels/)?[a-zA-Z]+\d+\.xml(\.rels)?", name):
                continue
            if name.startswith("ppt/slides/charts/"):
                continue
            if name == "[Content_Types].xml":
                continue
            if name == "ppt/presentation.xml" or name == "ppt/_rels/presentation.xml.rels":
                continue
            parts[name] = deck.read(name)

        # Slides and their notes.
        for old_index, new_index in order.items():
            xml = deck.read(f"ppt/slides/slide{old_index}.xml").decode("utf-8")
            parts[f"ppt/slides/slide{new_index}.xml"] = transform_slide(
                xml, old_index, new_index
            ).encode("utf-8")

            notes = deck.read(f"ppt/notesSlides/notesSlide{old_index}.xml")
            parts[f"ppt/notesSlides/notesSlide{new_index}.xml"] = notes

        # Charts, relocated, range-corrected, with a workbook each.
        for _old_slide, (chart_number, _rel_id) in sorted(chart_for_slide.items()):
            chart_xml = deck.read(
                f"ppt/slides/charts/chart{chart_number}.xml"
            ).decode("utf-8")
            categories, series = read_chart_series(chart_xml)
            chart_xml = patch_chart(chart_xml, len(categories), len(series))
            chart_xml = apply_palette(chart_xml)
            parts[f"ppt/charts/chart{chart_number}.xml"] = chart_xml.encode("utf-8")
            parts[f"ppt/charts/_rels/chart{chart_number}.xml.rels"] = relationships(
                [(
                    "rId1",
                    "package",
                    f"/ppt/embeddings/Microsoft_Excel_Worksheet{chart_number}.xlsx",
                )]
            )
            parts[
                f"ppt/embeddings/Microsoft_Excel_Worksheet{chart_number}.xlsx"
            ] = build_workbook(categories, series)

    # Dividers.
    for position, (numeral, title, dek, note) in DIVIDERS.items():
        parts[f"ppt/slides/slide{position}.xml"] = build_divider(
            divider_template, position, numeral, title, dek
        )
        parts[f"ppt/notesSlides/notesSlide{position}.xml"] = NOTES_TEMPLATE.format(
            note=note
        ).encode("utf-8")

    # Slide and notes relationships, rebuilt in the new order.
    chart_for_new_slide = {order[old]: spec for old, spec in chart_for_slide.items()}
    for index in range(1, TOTAL_SLIDES + 1):
        items = [
            ("Rgaclayout", "slideLayout", "/ppt/slideLayouts/slideLayout2.xml"),
        ]
        if index in chart_for_new_slide:
            chart_number, chart_rel_id = chart_for_new_slide[index]
            items.append(
                (chart_rel_id, "chart", f"/ppt/charts/chart{chart_number}.xml")
            )
        items.append(
            ("Rgacnotes", "notesSlide", f"/ppt/notesSlides/notesSlide{index}.xml")
        )
        parts[f"ppt/slides/_rels/slide{index}.xml.rels"] = relationships(items)
        parts[f"ppt/notesSlides/_rels/notesSlide{index}.xml.rels"] = relationships(
            [
                ("Rgacslide", "slide", f"/ppt/slides/slide{index}.xml"),
                ("Rgacnotesmaster", "notesMaster", "/ppt/notesMasters/notesMaster1.xml"),
            ]
        )

    # presentation.xml and its relationships.
    with zipfile.ZipFile(io.BytesIO(source)) as deck:
        presentation = deck.read("ppt/presentation.xml").decode("utf-8")
        pres_rels = deck.read("ppt/_rels/presentation.xml.rels").decode("utf-8")

    slide_ids = "".join(
        f'<p:sldId id="{255 + index}" r:id="Rgacsld{index:02d}"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" />'
        for index in range(1, TOTAL_SLIDES + 1)
    )
    presentation = re.sub(
        r"<p:sldIdLst>.*?</p:sldIdLst>",
        f"<p:sldIdLst>{slide_ids}</p:sldIdLst>",
        presentation,
        flags=re.S,
    )
    parts["ppt/presentation.xml"] = presentation.encode("utf-8")

    kept = [
        m.group(0)
        for m in re.finditer(r"<Relationship\b[^>]*/>", pres_rels)
        if "/slides/slide" not in m.group(0)
    ]
    slide_rels = "".join(
        f'<Relationship Type="{rel("slide")}" Target="/ppt/slides/slide{index}.xml"'
        f' Id="Rgacsld{index:02d}" />'
        for index in range(1, TOTAL_SLIDES + 1)
    )
    parts["ppt/_rels/presentation.xml.rels"] = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(kept)
        + slide_rels
        + "</Relationships>"
    ).encode("utf-8")

    parts["[Content_Types].xml"] = build_content_types(parts)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as out:
        for name in sorted(parts):
            info = zipfile.ZipInfo(name, ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            out.writestr(info, parts[name])
    return buffer.getvalue()


def build_content_types(parts: dict[str, bytes]) -> bytes:
    overrides = [
        ('<Default Extension="xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml" />'),
        ('<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml" />'),
        ('<Default Extension="xlsx" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" />'),
        ('<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml" />'),
        ('<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml" />'),
        ('<Override PartName="/ppt/presProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presProps+xml" />'),
        ('<Override PartName="/ppt/viewProps.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.viewProps+xml" />'),
        ('<Override PartName="/ppt/tableStyles.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.tableStyles+xml" />'),
    ]
    typed = {
        "ppt/slideMasters/": "sldMaster",
        "ppt/slideLayouts/": "sldLayout",
        "ppt/slides/slide": "slide",
        "ppt/notesSlides/notesSlide": "notesSlide",
        "ppt/notesMasters/notesMaster": "notesMaster",
        "ppt/charts/chart": "chart",
    }
    for name in sorted(parts):
        if not name.endswith(".xml") or "/_rels/" in name:
            continue
        if name.endswith("theme1.xml") or name.endswith("theme2.xml"):
            overrides.append(
                f'<Override PartName="/{name}" ContentType="{CT_TYPES["theme"]}" />'
            )
            continue
        for prefix, kind in typed.items():
            if name.startswith(prefix):
                overrides.append(
                    f'<Override PartName="/{name}" ContentType="{CT_TYPES[kind]}" />'
                )
                break
    return (CT_HEADER + "".join(overrides) + "</Types>").encode("utf-8")


# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report without writing")
    args = parser.parse_args()

    for path in (TARGET, STYLE_SOURCE):
        if not path.exists():
            print(f"missing: {path}", file=sys.stderr)
            return 1

    style_source = STYLE_SOURCE.read_bytes()
    actual = hashlib.sha256(style_source).hexdigest()
    if actual != STYLE_SOURCE_SHA256:
        print(
            f"style source {STYLE_SOURCE.name} is {actual}, expected "
            f"{STYLE_SOURCE_SHA256}; refresh the pin if the template was revised",
            file=sys.stderr,
        )
        return 1

    original = TARGET.read_bytes()
    if already_restyled(original):
        print(
            f"{TARGET.name}: already restyled ({TOTAL_SLIDES} slides, on-spec chart "
            f"parts); nothing to do"
        )
        print(f"  sha256 {hashlib.sha256(original).hexdigest()}")
        return 0

    restyled = restyle(original, style_source)

    with zipfile.ZipFile(io.BytesIO(restyled)) as check:
        slides = [
            name for name in check.namelist()
            if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
        ]
        if len(slides) != TOTAL_SLIDES:
            print(f"expected {TOTAL_SLIDES} slides, produced {len(slides)}", file=sys.stderr)
            return 1
        body = b"\n".join(check.read(name) for name in sorted(slides))
        for token in PALETTE:
            if f'val="{token}"'.encode() in body:
                print(f"unmapped colour survives restyle: {token}", file=sys.stderr)
                return 1
        # Every headline except the title slide's, which carries the manuscript
        # title verbatim, must be short enough to read as a claim rather than a
        # sentence. A new long headline upstream fails here instead of shipping.
        for name in sorted(slides, key=lambda n: int(re.search(r"\d+", n).group())):
            index = int(re.search(r"slide(\d+)", name).group(1))
            if index == 1:
                continue
            slide_xml = check.read(name).decode("utf-8")
            for block in SP_RE.findall(slide_xml):
                off = OFF_RE.search(block)
                if not off or int(off.group(2)) != TITLE_Y:
                    continue
                for headline in TEXT_RE.findall(block):
                    if len(headline) <= TITLE_LENGTH_LIMIT:
                        continue
                    print(
                        f"slide {index}: headline is {len(headline)} characters, over "
                        f"the {TITLE_LENGTH_LIMIT}-character limit: {headline!r}",
                        file=sys.stderr,
                    )
                    return 1

    if args.check:
        print(f"{TARGET.name}: would write {len(restyled)} bytes, {TOTAL_SLIDES} slides")
        print(f"  sha256 {hashlib.sha256(restyled).hexdigest()}")
        return 0

    TARGET.write_bytes(restyled)
    print(f"{TARGET.name}: {len(restyled)} bytes, {TOTAL_SLIDES} slides")
    print(f"  sha256 {hashlib.sha256(restyled).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
