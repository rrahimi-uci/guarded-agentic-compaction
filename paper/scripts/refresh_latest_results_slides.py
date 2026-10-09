#!/usr/bin/env python3
"""Bring the shipped technical deck up to the paper's latest results (October 2026).

Like the other post-generation transforms (refresh_headroom_ablation_slide.py,
refresh_gate_frontier_slide.py), this edits the generated deck in place because the
artifact-tool workspace behind generate_slides.mjs is not part of the repository. It is
assertive and idempotent: every edited paragraph must currently hold either its recorded
old text (then it is replaced) or its new text (then it is left alone); anything else stops
the run without writing.

What it does:

* updates the title, short-version, evidence-tier, slide-17, and limitations slides to the
  current paper (BIRD, the post-cutoff end-to-end certificate, refusals, the adverse drift
  result, and the 45 *calibration* replays, which an earlier slide called tool replays);
* inserts three results slides after slide 20, built on slide 20's two-card frame: BIRD
  (where GAC helps), what the certificates certify plus the replications, and NESTFUL and
  AppWorld (no measured benefit). They are new parts slide27-29.xml ordered after
  slide20.xml, so existing part names, and the scripts that target them, are unchanged;
* renumbers the visible page footers to the new order (26 -> 29 slides).

Numbers are the paper's (paper/iclr, PR #71 and its parents) and the retained results
under paper/results/bird/, paper/results/time_forward/, and paper/results/drift_*/.

Usage: python paper/scripts/refresh_latest_results_slides.py [--check]
"""

from __future__ import annotations

import argparse
import html
import re
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[2]
DECK = ROOT / "paper/slides/compiling-recurrent-agent-workflows-into-guarded-programs-detailed.pptx"
TEMPLATE_SLIDE = 20          # two-card frame the new slides are built on
NEW_PARTS = (27, 28, 29)     # new part numbers, presented after slide 20 in this order
INSERT_AFTER_RID = "Rgacsld20"

# --------------------------------------------------------------------------- existing-slide edits
# (slide part, shape id, old paragraphs, new paragraphs). A paragraph list replaces the
# shape's paragraphs one for one; the first run's formatting of each paragraph is kept.
EDITS: list[tuple[int, int, list[str], list[str]]] = [
    (1, 9, ["real workflow families with distinct tools and graders"],
           ["GitHub workflow families, 90/90 held-out contracts"]),
    (1, 10, ["90"], ["26"]),
    (1, 11, ["live-provider protocols on real public GitHub records"],
            ["of 31 BIRD databases compiled; no loss detected"]),
    (1, 12, ["8"], ["0"]),
    (1, 13, ["conditions in a controlled workflow-shape suite"],
            ["end-to-end misses on 132 fresh pull requests"]),
    (1, 14, ["Prepared for engineering leadership  ·  JazzX AI  ·  August 2026"],
            ["Prepared for engineering leadership  ·  JazzX AI  ·  October 2026"]),
    (2, 9, ["50%"], ["−66.6%"]),
    (2, 10, ["fewer provider requests on 30 unseen real GitHub issues — with 30/30 task contracts held"],
            ["provider requests on 90 held-out GitHub records in three workflows — 90/90 contracts held"]),
    (2, 15, ["96.3%"], ["−45.8%"]),
    (2, 16, ["provenance candidate recall across 5,746 dependency slots — but only 80.7% resolve uniquely"],
            ["model calls on BIRD, a public text-to-SQL benchmark: 26 of 31 databases compiled"]),
    (2, 18, ["+123%"], ["0 / 132"]),
    (2, 19, ["cost on a −16.8% token saving: prompt-cache economics, not token count, decides the invoice"],
            ["end-to-end misses on fresh post-cutoff pull requests: error rate below 2% at 90% confidence"]),
    (2, 21, ["The efficiency win is real but narrow: partial GRC removes model turns, not source reads.",
             "Manual composition beats partial GRC; when both execute before request one, manual and GCS tie structurally at 6/6 exact quality.",
             "Bounded official GEPA retains its seed. The contribution is guarded automatic specialization—not runtime dominance."],
            ["The win replicates: two-thirds fewer model calls on GitHub, about half on 26 BIRD databases and two model families.",
             "GAC refuses where evidence is thin (NESTFUL) or the opening is a per-question choice (BIRD's standard agent; Claude Sonnet).",
             "Limits: certificates mostly confirm sample size; savings hold within one snapshot; checks prevented no wrong answer under drift."]),
    (16, 16, ["Three primary GitHub workflow families plus scoped ablations on a pinned snapshot"],
             ["Three GitHub workflow families on a pinned snapshot, plus a live SQL agent on BIRD"]),
    (16, 17, ["Actual public issue records; deterministic local reads; live provider calls",
              "The natural-order protocols name no tool functions and no order; the first prescribes a fixed prefix as an ablation",
              "One repository, one snapshot, one model configuration"],
             ["Actual public issue records; deterministic local reads; live provider calls",
              "The natural-order protocols name no tool functions and no order; the first prescribes a fixed prefix as an ablation",
              "GitHub: one snapshot; BIRD: 31 databases, two model families"]),
    (17, 6, ["A real GitHub trace looks like an obvious macro:",
             "issue #6602: record → labels → comments(limit=3)",
             "45/45 tool replays; issue #6602 loses its Markdown URL."],
            ["A real GitHub trace looks like an obvious macro:",
             "issue #6602: record → labels → comments(limit=3)",
             "45/45 calibration replays; issue #6602 loses its Markdown URL."]),
    (25, 10, ["On the sealed artifact every threshold below 0.14 admits nothing and above it admits all 92, zero violations throughout. A pre-registered study since ran a support-only comparator (alpha=1, otherwise identical) on four repositories, 240 held-out pairs, and found the same all-or-none threshold everywhere: confirmed, not resolved, and still not a risk-coverage frontier."],
             ["Every threshold below 0.14 admits nothing and every one above admits all 92. A support-only comparator on 240 held-out pairs found the same step, and an amended 184-group end-to-end issue gate retired with two errors: no risk–coverage frontier."]),
    (25, 29, ["Latency is partly confounded"], ["Guards showed no measured protection"]),
    (25, 30, ["The fixed-prefix harness ran the whole baseline batch before the whole compiled batch. Request-count reduction is structural and unaffected, but the −85.0% wall-latency figure should be read as an observation under that ordering."],
             ["Under tool-layer corruption both arms answered wrongly on 39 of 60 records: an emptied list lies inside the learned hull, so the verifier prevented no silent wrong answer. Two provider-free drift studies were null by construction."]),
    (25, 33, ["No perturbation challenge ran on the primary live artifact",
              "GCS / GEPA results hold at α=.10, not the registered .05",
              "Fair placement / GEPA has only six held-out cases",
              "AWO · Agent JIT · EvoC2F remain unexecuted",
              "Break-even 181–411 episodes; part of the cost range is cache warmth"],
             ["Certificates confirm sample size, not risk",
              "GCS / GEPA results hold at α=.10, not the registered .05",
              "Fair placement / GEPA has only six held-out cases",
              "AWO · Agent JIT · EvoC2F remain unexecuted",
              "Break-even 181–411 episodes per snapshot"]),
]

# Run-level fixes that must keep a run's formatting: (slide part, old, new).
RAW_FIXES: list[tuple[int, str, str]] = [
    # two runs joined without a space ("ship.GAC:"); the bold first run is kept
    (17, "<a:t>GAC: ungroundable comments limit → keep comments and rendering with the agent.</a:t>",
         "<a:t> GAC: ungroundable comments limit → keep comments and rendering with the agent.</a:t>"),
]

# --------------------------------------------------------------------------- new slides
# Shape ids are those of slide 20's frame: 4 eyebrow, 5 title; left card 7 title, 8 subtitle,
# 9-14 three value/label rows, 15 note; right card 17-25 likewise; 28 icon, 29-30 callout.
NEW_SLIDES: list[dict[int, str]] = [
    {
        4: "RESULTS  ·  PUBLIC BENCHMARK  ·  BIRD TEXT-TO-SQL  ·  LIVE AGENT",
        5: "A public benchmark where GAC helps",
        7: "Schema-first agent",
        8: "reads every table first  ·  26 of 31 databases",
        9: "−45.8%", 10: "provider requests, 629 completed pairs",
        11: "402 / 403", 12: "correct of 630, compiled vs. unchanged",
        13: "−3.3 to +3.0", 14: "accuracy difference, 95% interval (points)",
        15: "Every admitted database dispatched on every completed question. The result replicates on the five dev databases and on gpt-6-luna (−49.6% requests; 93 vs. 91 of 150).",
        17: "Standard agent",
        18: "picks its tables for each question",
        19: "0 / 36", 20: "database runs compiled (two OpenAI models)",
        21: "7–39", 22: "distinct table lists per dev database",
        23: "0 / 10", 24: "database-design pairs on Claude Sonnet",
        25: "The table list is a per-question model decision, so there is nothing fixed to compile. Sonnet, told to read every table, did so in 26 of 655 runs.",
        28: "✓",
        29: "GAC compiles what an agent does, not what its prompt asks for",
        30: "On 930 scheduled held-out questions with a compiled agent (26 databases, two model families), no run showed a detected accuracy loss, though equivalence is not established: requests fell 45–50%, latency 29–38%, and cost 11–18% at uncached prices. A hand-written schema prefetch matches the compiled program.",
    },
    {
        4: "RESULTS  ·  CERTIFICATES AND REPLICATIONS",
        5: "What the certificates certify",
        7: "End-to-end certificate",
        8: "132 fresh post-cutoff pull requests  ·  one family",
        9: "0 / 132", 10: "end-to-end contract misses",
        11: "0.0173", 12: "upper bound at 90% confidence (0.035, grid)",
        13: "60 / 60", 14: "fresh test records, every condition",
        15: "The first certificate whose event includes the model's answer. It covers open and merged pull requests: the calibration draw held no closed-unmerged ones.",
        17: "Primary certificates",
        18: "three GitHub families  ·  92 calibration groups each",
        19: "92 / 92", 20: "zero-violation calibration groups",
        21: "0.0498", 22: "upper bound against α = 0.05",
        23: "n ≥ 92", 24: "what the bound really certifies",
        25: "The replay-contract event has no support on these cohorts: arguments are invariant and reads deterministic, so the bound confirms enough examples, not an observed risk.",
        28: "!",
        29: "Same programs on a second model and a second provider; no protection under drift",
        30: "Re-discovery on gpt-6-luna and Claude Sonnet re-derives the identical programs on two of three GitHub families and refuses backlog routing (on Sonnet at 91 and 90 of 92 groups). Under tool-layer drift the run-time checks prevented no wrong answer: both arms answered wrongly on 39 of 60 records.",
    },
    {
        4: "RESULTS  ·  WHERE GAC YIELDS NO MEASURED BENEFIT",
        5: "Where GAC yields no measured benefit",
        7: "NESTFUL",
        8: "1,415 executable traces  ·  32 recurring families",
        9: "26", 10: "largest family support",
        11: "92", 12: "zero-violation groups the gate requires",
        13: "0 / 32", 14: "families admitted; no wrong execution",
        15: "Evidence too thin: every family passes provenance, synthesis, and replay, then retires at the gate. API-Bank (8) and BFCL v4 (15) retire the same way.",
        17: "AppWorld",
        18: "gold solutions  ·  8,190 released agent runs",
        19: "92 / 92", 20: "one two-call artifact admitted",
        21: "2,339/2,340", 22: "full-code runs that could use it",
        23: "1 / 4,680", 24: "ReAct or plan-and-execute runs",
        25: "Admissible, rarely dispatchable: agents that open by reading API documentation almost never reach the compiled path; admitting that read recovers only 2 more.",
        28: "→",
        29: "No model runs on either benchmark, so neither licenses an efficiency claim",
        30: "The floor is a corpus-size fact: it bounds what public trace benchmarks can certify, not what the compiler can do. BIRD, with 146 to 474 questions per database and a live agent, is where the benefit becomes measurable.",
    },
]

NEW_NOTES = [
    "BIRD is the public benchmark where GAC delivers a measured benefit. A schema-first SQL agent's opening (list the tables, read every schema) compiles on 26 of 31 databases with gpt-5.6-luna and on all five dev databases with gpt-6-luna; on 930 scheduled held-out questions there is no detected accuracy loss (equivalence is not established) and model calls fall 45 to 50 percent. A standard agent that picks tables per question is refused everywhere, as is Claude Sonnet, which did not follow the schema-first instruction as a fixed step. Cost savings are modest (11 to 18 percent at uncached prices) because the removed calls are the shortest ones.",
    "Two kinds of certificate. The primary GitHub certificates (92 of 92 zero-violation groups, bound 0.0498) bound a replay-contract event that cannot occur on these deterministic, pinned cohorts, so in practice they certify that enough independent examples were seen. The post-cutoff study certifies the end-to-end task contract instead: 0 misses on 132 fresh pull requests, bound 0.0173 under its single pre-registered rule and 0.035 under the primary grid, for open and merged pull requests only. Replications re-derive the same programs on a second model and provider; the continuation-graded drift study is adverse.",
    "The two public benchmarks with no measured benefit, for two different reasons. NESTFUL is the largest trace corpus the compiler ingests, yet no workflow repeats more than 26 times against the 92 the gate needs, so every family retires; API-Bank and BFCL v4 retire the same way. AppWorld admits one small program, but almost no ReAct or plan-and-execute agent ever reaches it. No model runs on either benchmark, so neither supports an efficiency claim.",
]


# --------------------------------------------------------------------------- XML helpers
def _shape_span(xml: str, shape_id: int) -> tuple[int, int]:
    for m in re.finditer(r"<p:sp>.*?</p:sp>", xml, re.S):
        if re.search(rf'<p:cNvPr id="{shape_id}"[ >/]', m.group(0)):
            return m.start(), m.end()
    raise KeyError(f"shape id {shape_id} not found")


def _paragraphs(block: str) -> list[re.Match[str]]:
    return list(re.finditer(r"<a:p>.*?</a:p>|<a:p .*?</a:p>", block, re.S))


def _text(paragraph: str) -> str:
    return html.unescape("".join(re.findall(r"<a:t(?: [^>]*)?>(.*?)</a:t>", paragraph, re.S)))


def shape_paragraphs(xml: str, shape_id: int) -> list[str]:
    start, end = _shape_span(xml, shape_id)
    return [_text(p.group(0)) for p in _paragraphs(xml[start:end])]


def _set_paragraph(paragraph: str, text: str) -> str:
    runs = list(re.finditer(r"<a:r>.*?</a:r>", paragraph, re.S))
    if not runs:
        raise ValueError("paragraph has no run to carry the new text")
    first = runs[0].group(0)
    new_first = re.sub(r"(<a:t(?: [^>]*)?>).*?(</a:t>)", lambda m: m.group(1) + escape(text) + m.group(2), first, count=1, flags=re.S)
    out = paragraph[: runs[0].start()] + new_first
    # keep everything after the last run (e.g. endParaRPr); drop the other runs
    out += paragraph[runs[-1].end():]
    return out


def set_shape_paragraphs(xml: str, shape_id: int, texts: list[str]) -> str:
    start, end = _shape_span(xml, shape_id)
    block = xml[start:end]
    paras = _paragraphs(block)
    if len(paras) != len(texts):
        raise ValueError(f"shape {shape_id}: {len(paras)} paragraphs, {len(texts)} new texts")
    pieces, cursor = [], 0
    for match, text in zip(paras, texts):
        pieces.append(block[cursor:match.start()])
        pieces.append(_set_paragraph(match.group(0), text))
        cursor = match.end()
    pieces.append(block[cursor:])
    return xml[:start] + "".join(pieces) + xml[end:]


def set_page_number(xml: str, number: int) -> str:
    return set_shape_paragraphs(xml, 3, [str(number)])


def notes_xml(template: str, text: str) -> str:
    """Replace the body text of a notes part (its last text-bearing shape) with one paragraph."""
    shapes = list(re.finditer(r"<p:sp>.*?</p:sp>", template, re.S))
    for m in reversed(shapes):
        block = m.group(0)
        paras = _paragraphs(block)
        if paras and any(_text(p.group(0)).strip() for p in paras):
            first = paras[0].group(0)
            new_block = block[: paras[0].start()] + _set_paragraph(first, text) + block[paras[-1].end():]
            return template[: m.start()] + new_block + template[m.end():]
    raise ValueError("notes template has no text body")


# --------------------------------------------------------------------------- transform
def transform(deck: bytes) -> tuple[bytes, list[str]]:
    log: list[str] = []
    with ZipFile(BytesIO(deck)) as zin:
        parts = {i.filename: zin.read(i.filename) for i in zin.infolist()}
        infos = {i.filename: i for i in zin.infolist()}

    def slide(n: int) -> str:
        return parts[f"ppt/slides/slide{n}.xml"].decode("utf-8")

    # 1. existing-slide edits
    for n, shape_id, old, new in EDITS:
        xml = slide(n)
        current = shape_paragraphs(xml, shape_id)
        if current == new:
            continue
        # slide 17 may already carry the corrected label if refresh_aha_example_slide.py wrote it
        if current != old:
            raise RuntimeError(f"slide {n} shape {shape_id}: unexpected text {current!r}")
        parts[f"ppt/slides/slide{n}.xml"] = set_shape_paragraphs(xml, shape_id, new).encode("utf-8")
        log.append(f"slide {n} shape {shape_id} updated")

    for n, old, new in RAW_FIXES:
        xml = slide(n)
        if new in xml:
            continue
        if xml.count(old) != 1:
            raise RuntimeError(f"slide {n}: raw fix target not found exactly once")
        parts[f"ppt/slides/slide{n}.xml"] = xml.replace(old, new).encode("utf-8")
        log.append(f"slide {n} run-level fix applied")

    # 2. new slides after slide 20
    if f"ppt/slides/slide{NEW_PARTS[0]}.xml" not in parts:
        frame = slide(TEMPLATE_SLIDE)
        frame_rels = parts[f"ppt/slides/_rels/slide{TEMPLATE_SLIDE}.xml.rels"].decode("utf-8")
        notes_frame = parts[f"ppt/notesSlides/notesSlide{TEMPLATE_SLIDE}.xml"].decode("utf-8")
        notes_rels = parts[f"ppt/notesSlides/_rels/notesSlide{TEMPLATE_SLIDE}.xml.rels"].decode("utf-8")
        content_types = parts["[Content_Types].xml"].decode("utf-8")
        pres = parts["ppt/presentation.xml"].decode("utf-8")
        pres_rels = parts["ppt/_rels/presentation.xml.rels"].decode("utf-8")
        max_id = max(int(x) for x in re.findall(r'<p:sldId id="(\d+)"', pres))
        anchor = re.search(rf'<p:sldId [^>]*r:id="{INSERT_AFTER_RID}"[^>]*/>', pres)
        if anchor is None:
            raise RuntimeError("anchor slide id not found in presentation.xml")
        new_ids = ""
        for k, (part, texts, note) in enumerate(zip(NEW_PARTS, NEW_SLIDES, NEW_NOTES)):
            xml = frame
            for shape_id, text in texts.items():
                xml = set_shape_paragraphs(xml, shape_id, [text])
            parts[f"ppt/slides/slide{part}.xml"] = xml.encode("utf-8")
            parts[f"ppt/slides/_rels/slide{part}.xml.rels"] = frame_rels.replace(
                f"notesSlide{TEMPLATE_SLIDE}.xml", f"notesSlide{part}.xml").encode("utf-8")
            parts[f"ppt/notesSlides/notesSlide{part}.xml"] = notes_xml(notes_frame, note).encode("utf-8")
            parts[f"ppt/notesSlides/_rels/notesSlide{part}.xml.rels"] = notes_rels.replace(
                f"slides/slide{TEMPLATE_SLIDE}.xml", f"slides/slide{part}.xml").encode("utf-8")
            content_types = content_types.replace(
                "</Types>",
                f'<Override PartName="/ppt/slides/slide{part}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml" />'
                f'<Override PartName="/ppt/notesSlides/notesSlide{part}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml" />'
                "</Types>")
            rid = f"Rgacsld{part}"
            pres_rels = pres_rels.replace(
                "</Relationships>",
                f'<Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="/ppt/slides/slide{part}.xml" Id="{rid}" /></Relationships>')
            new_ids += (f'<p:sldId id="{max_id + 1 + k}" r:id="{rid}" '
                        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" />')
            log.append(f"inserted slide part {part}")
        pres = pres[: anchor.end()] + new_ids + pres[anchor.end():]
        parts["[Content_Types].xml"] = content_types.encode("utf-8")
        parts["ppt/presentation.xml"] = pres.encode("utf-8")
        parts["ppt/_rels/presentation.xml.rels"] = pres_rels.encode("utf-8")

    # 3. page footers follow presentation order
    pres = parts["ppt/presentation.xml"].decode("utf-8")
    pres_rels = parts["ppt/_rels/presentation.xml.rels"].decode("utf-8")
    targets = dict(re.findall(r'Target="/ppt/slides/(slide\d+\.xml)" Id="(Rgacsld\d+)"', pres_rels))
    targets = {rid: target for target, rid in targets.items()}
    order = re.findall(r'<p:sldId [^>]*r:id="(Rgacsld\d+)"', pres)
    for position, rid in enumerate(order, start=1):
        name = f"ppt/slides/{targets[rid]}"
        xml = parts[name].decode("utf-8")
        try:
            current = shape_paragraphs(xml, 3)
        except KeyError:
            continue
        if current and current[0].strip().isdigit() and current[0].strip() != str(position):
            parts[name] = set_page_number(xml, position).encode("utf-8")
            log.append(f"{targets[rid]} page number -> {position}")

    out = BytesIO()
    with ZipFile(out, "w", compression=ZIP_DEFLATED, compresslevel=9) as zout:
        ordered = list(infos) + [n for n in parts if n not in infos]
        for name in ordered:
            info = infos.get(name)
            if info is not None:
                zout.writestr(info, parts[name])
            else:
                zout.writestr(name, parts[name])
    return out.getvalue(), log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="report the changes without writing the deck")
    parser.add_argument("--deck", type=Path, default=DECK)
    args = parser.parse_args(argv)
    original = args.deck.read_bytes()
    updated, log = transform(original)
    if not log:
        print("deck already current; nothing to do")
        return 0
    print("\n".join(log))
    if args.check:
        print(f"[check] {len(log)} changes pending; deck not written")
        return 0
    args.deck.write_bytes(updated)
    print(f"updated {args.deck}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
