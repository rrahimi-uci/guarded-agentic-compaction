#!/usr/bin/env python3
"""Resynchronize the shipped deck with the current manuscript.

The artifact-tool presentation workspace used by ``generate_slides.mjs`` is not part of
this repository, so a content change in the paper cannot be picked up by regenerating the
deck.  This is the same narrow, assertive, in-place transform pattern as
``retitle_slides.py`` and ``refresh_aha_example_slide.py``: it edits only the runs it
names, asserts every string it rewrites, and is a no-op once applied.

Two kinds of drift are repaired.

**Manuscript coordinates.**  Each slide's eyebrow carries the section, figure, table, or
algorithm the slide answers.  Inserting the Section 2--3 reader aids added twelve figures
and one table to the article, which renumbered every float after them, so most of those
coordinates now point at the wrong exhibit.  The replacements are not hard-coded blind:
every new number is checked against ``paper/open_research/article.aux`` before anything is
written, so a future renumbering fails loudly here instead of shipping a stale pointer.

**The runtime terminal-edge tally.**  The manuscript used to enumerate the dispatch exits
as one compaction, five baseline returns, and one incident.  It now states the invariant
without the counts --- exactly one edge compacts, every clean rejection returns the
baseline, and a failed abort, failed commit, or post-commit failure raises an incident ---
because the enumeration was brittle against changes in the algorithm's return points.  The
deck carried the old counts, so slide 12 contradicted the paper it summarizes.

Slide 13 additionally gains the distinction the manuscript now draws explicitly: the score
is *fitted* on development groups that were unproductive in any way, whereas the bound is
*counted* only from dispatched groups that were wrong.  Conflating those two signals is the
easiest way to misread the guarantee.

Usage:  python paper/scripts/resync_slide_coordinates.py [--check]
"""

from __future__ import annotations

import argparse
import re
import sys
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[2]
DECK = ROOT / "paper/slides/compiling-recurrent-agent-workflows-into-guarded-programs-detailed.pptx"
AUX = ROOT / "paper/open_research/article.aux"

#: Eyebrow rewrites, keyed by slide number. ``expect`` names the manuscript labels the new
#: coordinate asserts, so the script cannot quietly write a number the article disagrees
#: with. Slides whose coordinates are still correct are deliberately absent.
COORDINATES: dict[int, dict[str, object]] = {
    9: {
        "old": "METHOD  ·  ARCHITECTURE  ·  FIGURE 1",
        "new": "METHOD  ·  ARCHITECTURE  ·  FIGURE 6",
        "expect": {"fig:pipeline": "6"},
    },
    12: {
        "old": "METHOD  ·  RUNTIME  ·  §3.7 AND ALGORITHM 4",
        "new": "METHOD  ·  RUNTIME  ·  §3.8 AND ALGORITHM 4",
        "expect": {"alg:dispatch": "4", "sec:runtime-scope": "3.8.1"},
    },
    13: {
        "old": "METHOD  ·  REJECTION POINT 6  ·  §3.5 AND ALGORITHM 3",
        "new": "METHOD  ·  REJECTION POINT 6  ·  §3.6 AND ALGORITHM 3",
        "expect": {"alg:calibrate": "3", "sec:admission-register": "3.6.1"},
    },
    16: {
        # Section 4.1 carries the tier prose; the hypothesis verdicts it sets up are
        # tabulated in Table 5. The deck pointed at Table 3, which is the benchmark-at-a-
        # glance table in section 4.2 and describes tasks rather than tiers.
        "old": "METHODOLOGY  ·  §4.1  ·  TABLE 3",
        "new": "METHODOLOGY  ·  §4.1  ·  TABLE 5",
        "expect": {"tab:hypotheses": "5"},
    },
    17: {
        # Slide 17 is the earlier free-order 18-record follow-up (issue 6602).
        "old": "RESULTS  ·  RQ2  ·  §5.3  ·  TABLE 6",
        "new": "RESULTS  ·  RQ2  ·  §5.3  ·  TABLE 9",
        "expect": {"tab:natural-live": "9", "sec:rq2": "5.3"},
    },
    18: {
        "old": "RESULTS  ·  RQ6  ·  §5.2  ·  TABLE 5",
        "new": "RESULTS  ·  RQ6  ·  §5.2  ·  TABLE 7",
        "expect": {"tab:github-families": "7", "sec:family-results": "5.2"},
    },
    19: {
        # Slide 19 is the expanded 30-record replication.
        "old": "RESULTS  ·  RQ2  ·  §5.3  ·  TABLE 6",
        "new": "RESULTS  ·  RQ2  ·  §5.3  ·  TABLE 8",
        "expect": {"tab:natural-replication": "8"},
    },
    20: {
        "old": "RESULTS  ·  THE DEPTH TRADE-OFF  ·  §5.3  ·  TABLES 6 AND 7",
        "new": "RESULTS  ·  THE DEPTH TRADE-OFF  ·  §5.3  ·  TABLES 8 AND 9",
        "expect": {"tab:natural-replication": "8", "tab:natural-live": "9"},
    },
    21: {
        "old": "RESULTS  ·  RQ4  ·  §5.4  ·  FIGURE 6",
        "new": "RESULTS  ·  RQ4  ·  §5.4  ·  FIGURE 18",
        "expect": {"fig:demo-suite": "18", "sec:demos-results": "5.4"},
    },
    22: {
        "old": "RESULTS  ·  THE COMPARATOR THAT MATTERS  ·  §5.6  ·  TABLE 8",
        "new": "RESULTS  ·  THE COMPARATOR THAT MATTERS  ·  §5.6  ·  TABLE 10",
        "expect": {"tab:comparator": "10", "sec:comparator": "5.6"},
    },
    23: {
        "old": "RESULTS  ·  FAIR PLACEMENT AND BOUNDED GEPA  ·  §5.7–5.8  ·  TABLES 10 AND 11",
        "new": "RESULTS  ·  FAIR PLACEMENT AND BOUNDED GEPA  ·  §5.7–5.8  ·  TABLES 12 AND 13",
        "expect": {
            "tab:gcs-live": "12",
            "tab:optimizer-head-to-head": "13",
            "sec:gcs-results": "5.7",
            "sec:optimizer-results": "5.8",
        },
    },
    24: {
        "old": "RESULTS  ·  RQ5  ·  §3.6 AND §5.9  ·  TABLE 15",
        "new": "RESULTS  ·  RQ5  ·  §3.7 AND §5.9  ·  TABLE 17",
        "expect": {
            "tab:portfolio-results": "17",
            "sec:portfolio-method": "3.7",
            "sec:portfolio-results": "5.9",
        },
    },
}

#: Body rewrites that carry a claim, keyed by slide number.
BODY: dict[int, dict[str, str]] = {
    12: {
        "DISPATCH IS SELECTIVE — SIX CHECKS, THEN ONE OF SEVEN TERMINAL EDGES":
            "DISPATCH IS SELECTIVE — SIX CHECKS, THEN ONE OF THREE OUTCOMES",
        # The manuscript no longer enumerates how many edges reach each outcome, because
        # the count tracked the algorithm's return points rather than the invariant.
        # Exactly one edge compacts; the other two outcomes are reached by any qualifying
        # failure, which is the property that actually matters.
        # Kept to roughly the original length: the card is 3.18x0.8in at 11pt with no
        # autofit, so the sibling card's 60 characters are near the ceiling and a
        # four-line body would print outside the frame.
        "A post-commit failure. An external commitment happened — the runtime does not feign rollback.":
            "A failed abort, failed commit, or post-commit failure — reversibility cannot be attested, so no rollback is feigned.",
    },
    13: {
        "The score model and the eleven-threshold grid are frozen before any calibration group is seen. That is what makes a union bound legitimate.":
            "The score model and the eleven-threshold grid are frozen before any calibration group is seen — the score fitted on development groups only. That is what makes a union bound legitimate.",
        "For each threshold the compiler computes a one-sided Clopper–Pearson upper bound and selects the largest-coverage admissible one.":
            "For each threshold the compiler counts dispatched groups that were wrong, computes a one-sided Clopper–Pearson upper bound, and selects the largest-coverage admissible one.",
    },
}

#: The stat-box counts on slide 12. The manuscript still asserts that exactly one edge
#: compacts, so that box keeps its "1"; it no longer asserts how many edges reach the other
#: two outcomes, so those become "n". A word such as "any" was the first choice and does not
#: fit: the box is 0.7in wide at 27pt, which leaves about 0.5in of usable measure -- roughly
#: one glyph. The runs are matched positionally because "1" and "5" are too short to match
#: uniquely.
TALLY_SLIDE = 12
TALLY_OLD = ("1", "5", "1")
TALLY_NEW = ("1", "n", "n")


class TransformError(RuntimeError):
    pass


def article_numbers() -> dict[str, str]:
    """Read label -> printed number from the article's own auxiliary file."""

    if not AUX.exists():
        raise TransformError(
            f"{AUX.relative_to(ROOT)} is missing; build the article first so the "
            "coordinates can be checked against it"
        )
    text = AUX.read_text(encoding="utf-8", errors="replace")
    return {
        match.group(1): match.group(2)
        for match in re.finditer(r"newlabel\{([^}]+)\}\{\{([^}]*)\}", text)
    }


def verify_expectations(numbers: dict[str, str]) -> None:
    problems: list[str] = []
    for slide, spec in sorted(COORDINATES.items()):
        for label, expected in spec["expect"].items():  # type: ignore[union-attr]
            actual = numbers.get(label)
            if actual != expected:
                problems.append(
                    f"slide {slide}: {label} is {actual!r} in the article, "
                    f"but this script writes {expected!r}"
                )
    if problems:
        raise TransformError(
            "the manuscript has renumbered since this script was written:\n  "
            + "\n  ".join(problems)
        )


def tag(text: str) -> bytes:
    return f"<a:t>{escape(text)}</a:t>".encode("utf-8")


def replace_once(blob: bytes, old: str, new: str, where: str) -> bytes:
    count = blob.count(tag(old))
    if count != 1:
        raise TransformError(f"{where}: expected one occurrence of {old!r}, found {count}")
    return blob.replace(tag(old), tag(new), 1)


def rewrite_tally(blob: bytes) -> bytes:
    """Rewrite the three outcome-count runs on slide 12, in document order."""

    spans = [m for m in re.finditer(rb"<a:t>([^<]*)</a:t>", blob)]
    positions = [m for m in spans if m.group(1).decode("utf-8") in {"1", "5"}]
    found = tuple(m.group(1).decode("utf-8") for m in positions)
    if found != TALLY_OLD:
        raise TransformError(
            f"slide {TALLY_SLIDE}: expected outcome counts {TALLY_OLD}, found {found}"
        )
    out = bytearray(blob)
    for match, new in reversed(list(zip(positions, TALLY_NEW))):
        out[match.start():match.end()] = tag(new)
    return bytes(out)


def already_applied(deck: bytes) -> bool:
    with ZipFile(BytesIO(deck)) as archive:
        slide = archive.read(f"ppt/slides/slide{TALLY_SLIDE}.xml")
    return tag(BODY[TALLY_SLIDE][
        "DISPATCH IS SELECTIVE — SIX CHECKS, THEN ONE OF SEVEN TERMINAL EDGES"
    ]) in slide


def transform(deck: bytes) -> bytes:
    source = BytesIO(deck)
    output = BytesIO()
    touched: set[int] = set()
    with ZipFile(source) as zin, ZipFile(
        output, "w", compression=ZIP_DEFLATED, compresslevel=9
    ) as zout:
        for item in zin.infolist():
            content = zin.read(item.filename)
            match = re.fullmatch(r"ppt/slides/slide(\d+)\.xml", item.filename)
            if match:
                number = int(match.group(1))
                where = f"slide {number}"
                if number in COORDINATES:
                    spec = COORDINATES[number]
                    content = replace_once(content, spec["old"], spec["new"], where)  # type: ignore[arg-type]
                    touched.add(number)
                for old, new in BODY.get(number, {}).items():
                    content = replace_once(content, old, new, where)
                    touched.add(number)
                if number == TALLY_SLIDE:
                    content = rewrite_tally(content)
                    touched.add(number)
            zout.writestr(item, content)
    named = set(COORDINATES) | set(BODY) | {TALLY_SLIDE}
    if named - touched:
        raise TransformError(
            f"slides named but not found in the deck: {sorted(named - touched)}"
        )
    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report without writing")
    args = parser.parse_args()

    numbers = article_numbers()
    verify_expectations(numbers)

    original = DECK.read_bytes()
    if already_applied(original):
        print(f"{DECK.relative_to(ROOT)} is already resynchronized; nothing to do")
        return 0

    updated = transform(original)
    if updated == original:
        raise TransformError("the deck was not changed")

    if args.check:
        print(
            f"would resynchronize {DECK.relative_to(ROOT)}: "
            f"{len(COORDINATES)} manuscript coordinates, "
            f"{sum(len(v) for v in BODY.values())} claim runs, "
            "and the slide-12 outcome tally"
        )
        return 0

    DECK.write_bytes(updated)
    print(
        f"updated {DECK.relative_to(ROOT)}: "
        f"{len(COORDINATES)} manuscript coordinates, "
        f"{sum(len(v) for v in BODY.values())} claim runs, "
        "and the slide-12 outcome tally"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TransformError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
