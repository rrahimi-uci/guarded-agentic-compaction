#!/usr/bin/env python3
"""Render site/article.html from the manuscript's own LaTeX source.

The repository keeps manuscript prose in exactly one place: paper/tex/body.tex and
paper/tex/abstract-body.tex.  The PDF wrappers (article.tex, main.tex) are presentation
layers over that body, and this script is a third one that targets the web.  Transcribing
the article into hand-written HTML would create a second source of prose that drifts from
the paper silently, so the page is generated from the same .tex files the PDF is built
from.

Pandoc supplies the backbone: prose, sectioning, tables, native MathML, and a citeproc
bibliography.  Everything pandoc cannot do well is handled here rather than accepted as
degraded output --

  * the TikZ architecture figure and the algorithm float are replaced with hand-authored
    HTML/SVG in the site's own diagram vocabulary (scripts/article_fragments/), because a
    rasterized TikZ float would neither scale nor stay legible;
  * cross-references (\\cref, \\Cref, \\eqref) are resolved against a label registry built
    from the source, so every one becomes a real internal anchor;
  * tables and figures are renumbered and re-dressed in the site's design-system classes.

Pandoc is not available in the Pages CI job, which installs only pyyaml.  The page is
therefore generated locally and committed, and carries a digest of its sources in a meta
tag.  scripts/build_pages.py recomputes those digests with the standard library alone and
fails the build when the committed page no longer matches the manuscript it claims to
render -- the same fail-closed contract the other generated pages use, without requiring
pandoc at deploy time.

Usage:  python scripts/build_article_page.py  [--check]
"""

from __future__ import annotations

import argparse
import hashlib
import html as html_entities
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
TEX = PAPER / "tex"
FRAGMENTS = Path(__file__).resolve().parent / "article_fragments"
OUTPUT = ROOT / "site" / "article.html"

BODY = TEX / "body.tex"
ABSTRACT = TEX / "abstract-body.tex"
BIBLIOGRAPHY = PAPER / "bibliography" / "references.bib"

# Hashing these three files is what lets a pandoc-free CI job detect that the committed
# page has fallen behind the manuscript.  Order is fixed so the digest is stable.
SOURCES = (BODY, ABSTRACT, BIBLIOGRAPHY)

TITLE = "From Traces to Guarded Programs: Evidence-Gated Compilation of Recurrent Agent Workflows"
DESCRIPTION = (
    "The full article: a trace-to-program compiler that reconstructs typed provenance, "
    "rejects unsafe effects, synthesizes from a closed operator language, and admits a "
    "guarded program only under an exact finite-sample risk bound."
)

# Generated figures ship as PNG under assets/figures/ in the built site; the manuscript
# includes the PDF siblings.  Keys are the stems used by \includegraphics in body.tex.
#
# Derived from the manuscript rather than listed, because a listed map silently drops any
# figure added later: the four figures added to the results sections rendered as <figure>
# elements with no image at all, and only the count check in verify() caught it.
# build_pages.py copies the PNG siblings, so a stem that reaches here without one is a
# real packaging error and is reported rather than skipped.
def _figure_assets() -> dict[str, str]:
    stems = dict.fromkeys(
        re.findall(r"generated_figures/([A-Za-z0-9_]+)\.pdf", BODY.read_text(encoding="utf-8"))
    )
    missing = [s for s in stems if not (PAPER / "generated_figures" / f"{s}.png").exists()]
    if missing:
        # SystemExit rather than BuildError: this runs at import time, above the point
        # where BuildError is defined, so naming it here would raise NameError instead.
        raise SystemExit(f"manuscript figures have no PNG sibling for the site: {missing}")
    return {stem: f"assets/figures/{stem}.png" for stem in stems}


FIGURE_ASSETS = _figure_assets()

# Expansions for the wrapper-level macros.  Textual substitution is correct here: the
# PDF builds rely on \xspace to put back the space a control word swallows, so replacing
# the macro in place and keeping the source's own spacing reproduces what LaTeX renders.
MACROS = {
    r"\method": "GAC",
    r"\grc": "GRC",
    r"\tgws": "TGWS",
    r"\patg": "PATG",
    r"\retire": "Retire",
    r"\fallback": "Fallback",
}

# cleveref's rendered names, matching \crefname/\Crefname in paper/tex/article.tex.
CREF_NAMES = {
    "sec": ("section", "Section"),
    "fig": ("figure", "Figure"),
    "tab": ("table", "Table"),
    "alg": ("Alg.", "Algorithm"),
    "eq": ("eq.", "Eq."),
}


class BuildError(SystemExit):
    """Raised when the rendered page would misrepresent the manuscript."""


# --------------------------------------------------------------------------- utilities


def esc(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def attr(value: str) -> str:
    return esc(value).replace('"', "&quot;")


def source_digest() -> str:
    """SHA-256 over the manuscript sources this page claims to render."""

    digest = hashlib.sha256()
    for path in SOURCES:
        digest.update(path.read_bytes())
    return digest.hexdigest()


def balanced(text: str, start: int) -> tuple[str, int]:
    """Return the brace group beginning at `start` and the index just past it."""

    if start >= len(text) or text[start] != "{":
        raise BuildError(f"expected a brace group at offset {start}")
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:index], index + 1
    raise BuildError(f"unbalanced brace group at offset {start}")


# ---------------------------------------------------------------------- label registry


TOKEN = re.compile(
    r"\\(?P<kind>section|subsection|subsubsection)\*?\s*\{"
    r"|\\begin\{(?P<env>figure\*?|table\*?)\}"
    r"|\\label\{(?P<label>[^}]+)\}"
    r"|(?P<alg>\\input\{\.\./figures/alg-[a-z]+\.tex\})"
)

# Displayed equations are numbered by the order their labels appear rather than by
# counting environments, because the manuscript labels equations inside both `equation`
# and `align`, and an `align` block carries one number per row.  Numbering the labels
# keeps the page internally consistent -- every "Eq. (n)" resolves to the block that
# prints (n) -- which is what a self-contained web rendering needs.  The PDF's own
# sequence counts unlabelled rows too, so the two documents can differ by an offset.
EQUATION_ENVIRONMENTS = ("equation", "align")


SECTIONING = re.compile(r"\\(?:sub){0,2}section\*?\s*\{(?:[^{}]|\{[^{}]*\})*\}")


def normalize(body: str) -> str:
    """Give every sectioning command a \\label so it gets a stable anchor and a number.

    Pandoc derives a heading's id from its \\label, and the manuscript labels only the
    sections it cross-references -- Introduction, Discussion and Conclusion carry none.
    Adding the missing ones here, before the registry is built, is what lets those
    headings be numbered and linked from the table of contents like every other.
    """

    counter = [0]

    def ensure_label(match: re.Match[str]) -> str:
        head = match.group(0)
        if body[match.end():match.end() + 12].lstrip().startswith("\\label"):
            return head
        counter[0] += 1
        return f"{head}\\label{{sec:auto-{counter[0]}}}"

    return SECTIONING.sub(ensure_label, body)


def build_registry(body: str) -> dict[str, dict[str, str]]:
    """Map every \\label in the body to its rendered number and anchor.

    Numbers are assigned in document order, which is how LaTeX assigns them too.  A label
    always sits inside the environment it names, so tracking the most recently opened
    container of each kind is enough to attribute it.
    """

    section = [0, 0, 0]
    counts = {"fig": 0, "tab": 0, "eq": 0, "alg": 0}
    current = {"sec": "", "fig": "", "tab": "", "eq": "", "alg": ""}
    registry: dict[str, dict[str, str]] = {}

    for match in TOKEN.finditer(body):
        if match.group("kind"):
            # A starred section is unnumbered and cannot be the target of a \cref.
            if match.group(0).startswith("\\section*"):
                current["sec"] = ""
                continue
            kind = match.group("kind")
            level = {"section": 0, "subsection": 1, "subsubsection": 2}[kind]
            section[level] += 1
            for deeper in range(level + 1, 3):
                section[deeper] = 0
            current["sec"] = ".".join(str(section[i]) for i in range(level + 1))
        elif match.group("env"):
            env = match.group("env").rstrip("*")
            key = {"figure": "fig", "table": "tab"}[env]
            counts[key] += 1
            current[key] = str(counts[key])
        elif match.group("alg"):
            counts["alg"] += 1
            current["alg"] = str(counts["alg"])
        elif match.group("label"):
            label = match.group("label")
            prefix = label.split(":", 1)[0]
            if prefix == "eq":
                counts["eq"] += 1
                registry[label] = {"number": str(counts["eq"]), "prefix": "eq"}
                continue
            if prefix not in current or not current[prefix]:
                continue
            registry[label] = {"number": current[prefix], "prefix": prefix}

    return registry


def summary_rows(body: str) -> set[str]:
    """Labels of tables whose last row is a summary the source sets off with a rule.

    booktabs marks a totals row with a second \\midrule.  Pandoc drops every rule, so the
    weighted-total line would otherwise read as just another data row; the site's existing
    .row-total treatment restores the distinction.
    """

    labels: set[str] = set()
    for block in re.findall(r"\\begin\{table\*?\}.*?\\end\{table\*?\}", body, flags=re.S):
        label = re.search(r"\\label\{(tab:[^}]+)\}", block)
        source = re.search(r"\\input\{\.\./tables/([a-z_]+)\.tex\}", block)
        if label is None or source is None:
            continue
        path = PAPER / "tables" / f"{source.group(1)}.tex"
        if path.read_text(encoding="utf-8").count("\\midrule") >= 2:
            labels.add(label.group(1))
    return labels


def reference_html(label: str, registry: dict[str, dict[str, str]], capital: bool) -> str:
    """Render one cross-reference as an anchor, or as plain text when unresolvable.

    Labels defined only in the appendix are referenced from the body but have no target on
    this page.  Emitting a dangling '#app:proof' would fail the site's fragment check, so
    those degrade to unlinked text instead of breaking the build.
    """

    entry = registry.get(label)
    if entry is None:
        return "the appendix"
    name = CREF_NAMES[entry["prefix"]][1 if capital else 0]
    number = entry["number"]
    text = f"{name}&nbsp;({number})" if entry["prefix"] == "eq" else f"{name}&nbsp;{number}"
    return f'<a href="#{attr(label)}">{text}</a>'


# ------------------------------------------------------------------------- preprocess


def strip_resizebox(tex: str) -> str:
    """Unwrap \\resizebox{..}{..}{TABLE}: pandoc drops the box and the table with it."""

    out = []
    index = 0
    while True:
        found = tex.find(r"\resizebox", index)
        if found < 0:
            out.append(tex[index:])
            return "".join(out)
        out.append(tex[index:found])
        cursor = found + len(r"\resizebox")
        for _ in range(2):  # the two size arguments
            while cursor < len(tex) and tex[cursor] not in "{":
                cursor += 1
            _, cursor = balanced(tex, cursor)
        while cursor < len(tex) and tex[cursor] != "{":
            cursor += 1
        inner, cursor = balanced(tex, cursor)
        out.append(inner)
        index = cursor


def extract_descriptions(body: str) -> dict[str, str]:
    """Map figure labels to the \\Description alt text declared inside the float."""

    descriptions: dict[str, str] = {}
    for match in re.finditer(r"\\Description", body):
        start = body.find("{", match.end())
        text, end = balanced(body, start)
        # Captions may be substantially longer than the alt text.  Search only within
        # the containing figure, but do not impose a character limit that silently drops
        # accessibility text when an editorial revision lengthens the caption.
        float_end = body.find(r"\end{figure", end)
        if float_end < 0:
            continue
        label = re.search(r"\\label\{(fig:[^}]+)\}", body[end:float_end])
        if label is None:
            continue
        clean = re.sub(r"\s+", " ", text).strip()
        clean = clean.replace(r"\code", "").replace("{", "").replace("}", "")
        descriptions[label.group(1)] = clean
    return descriptions


def drop_environment(tex: str, begin: str, end: str, marker: str) -> str:
    """Replace the single environment containing `marker` with a passthrough token."""

    start = tex.find(begin)
    while start >= 0:
        stop = tex.find(end, start)
        if stop < 0:
            break
        block = tex[start:stop + len(end)]
        if marker in block:
            return tex[:start] + "\n\nGACARCHITECTURE\n\n" + tex[stop + len(end):]
        start = tex.find(begin, stop)
    raise BuildError(f"could not locate the environment containing {marker!r}")


def preprocess(body: str, registry: dict[str, dict[str, str]], *, floats: bool = True) -> str:
    """Rewrite manuscript LaTeX into the subset pandoc renders faithfully.

    `floats` is False for the abstract, which shares the macro and cross-reference
    handling but contains none of the figure or algorithm machinery.
    """

    tex = body

    if floats:
        # The architecture float is TikZ; the algorithm float is algorithmicx.  Neither
        # survives pandoc in a form worth publishing, so both become tokens that the
        # post-processing step swaps for hand-authored HTML.
        tex = drop_environment(tex, r"\begin{figure*}", r"\end{figure*}", r"\label{fig:pipeline}")
        tex = tex.replace(r"\input{../figures/alg-compile.tex}", "\n\nGACALGCOMPILE\n\n")

    # A starred float spans both columns of a two-column layout and means nothing in one
    # column; the PDF's article wrapper remaps them for the same reason.  Pandoc does not
    # treat table* as a float at all, so its \label -- and with it the anchor every
    # cross-reference to that table needs -- would be dropped silently.
    tex = tex.replace(r"\begin{table*}", r"\begin{table}").replace(r"\end{table*}", r"\end{table}")

    tex = strip_resizebox(tex)

    # Point the includes at the PNG siblings the site publishes.
    for stem, target in FIGURE_ASSETS.items():
        tex = tex.replace(f"../generated_figures/{stem}.pdf", target)

    # \Description is an acmart accessibility macro with no pandoc meaning; the alt text
    # it carries is re-attached to the <img> during post-processing.
    tex = re.sub(r"\\Description\{", r"\\iffalse{", tex)

    for macro, expansion in MACROS.items():
        tex = re.sub(re.escape(macro) + r"(\{\})?", expansion, tex)
    tex = tex.replace(r"\code{", r"\texttt{")
    tex = tex.replace(r"\hyp{}", "-")

    # Equations: pandoc's math reader rejects \label inside the environment.  Lift it out
    # as a token immediately before the equation so the anchor and number survive.
    def lift_label(match: re.Match[str]) -> str:
        block = match.group(0)
        label = re.search(r"\\label\{(eq:[^}]+)\}", block)
        if label is None:
            return block
        stripped = block.replace(label.group(0), "")
        return f"GACEQ{label.group(1)}GACEQ {stripped}"

    for environment in EQUATION_ENVIRONMENTS:
        tex = re.sub(
            rf"\\begin\{{{environment}\}}.*?\\end\{{{environment}\}}", lift_label, tex, flags=re.S
        )

    # Cross-references become real anchors.  \href{\#x}{y} is the one construct pandoc
    # turns into a plain <a href="#x">, which keeps the site's fragment check meaningful.
    def replace_ref(match: re.Match[str]) -> str:
        capital = match.group(1) == "C"
        labels = [item.strip() for item in match.group(2).split(",")]
        parts = [reference_html(label, registry, capital) for label in labels]
        rendered = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
        return f"GACREF{rendered}GACREF"

    tex = re.sub(r"\\(c|C)ref\{([^}]+)\}", replace_ref, tex)
    tex = re.sub(
        r"\\eqref\{([^}]+)\}",
        lambda m: "GACREF"
        + (
            f'<a href="#{attr(m.group(1))}">({registry[m.group(1)]["number"]})</a>'
            if m.group(1) in registry
            else "the appendix"
        )
        + "GACREF",
        tex,
    )

    return tex


# --------------------------------------------------------------------------- pandoc


def run_pandoc(tex: str, *, standalone_fragment: bool) -> str:
    if shutil.which("pandoc") is None:
        raise BuildError(
            "pandoc is required to regenerate site/article.html.\n"
            "Install it (brew install pandoc) and re-run this script."
        )
    shim = (
        "\\documentclass{article}\n"
        "\\usepackage{amsmath,amssymb,mathtools,graphicx,booktabs,multirow,tabularx,"
        "array,xcolor,enumitem}\n"
        "\\newtheorem{proposition}{Proposition}\n"
        "\\begin{document}\n" + tex + "\n\\end{document}\n"
    )
    command = [
        "pandoc", "-f", "latex", "-t", "html5", "--mathml", "--wrap=none",
        "--citeproc", f"--bibliography={BIBLIOGRAPHY}",
    ]
    if not standalone_fragment:
        command += ["--metadata", "reference-section-title=References"]
    result = subprocess.run(
        command, input=shim, capture_output=True, text=True, cwd=TEX, check=False
    )
    if result.returncode != 0:
        raise BuildError(f"pandoc failed:\n{result.stderr}")
    return result.stdout


# ------------------------------------------------------------------------ postprocess


def postprocess(
    html: str,
    registry: dict[str, dict[str, str]],
    descriptions: dict[str, str],
    totals: frozenset[str] = frozenset(),
) -> str:
    # Restore the anchors that rode through the LaTeX reader as escaped text.  Unescaping
    # only the token's own span keeps the rest of the document's escaping intact.
    html = re.sub(
        r"GACREF(.*?)GACREF", lambda m: html_entities.unescape(m.group(1)), html, flags=re.S
    )

    html = html.replace(
        "<p>GACARCHITECTURE</p>", (FRAGMENTS / "architecture.svg").read_text(encoding="utf-8")
    )
    algorithm = (FRAGMENTS / "alg-compile.html").read_text(encoding="utf-8")
    algorithm = algorithm.replace(
        "{{EQREF:eq:score}}", reference_html("eq:score", registry, False)
    )
    html = html.replace("<p>GACALGCOMPILE</p>", algorithm)

    # The architecture SVG is a figure in its own right; give it the caption the float had.
    html = html.replace(
        '<svg viewBox="0 0 960 722"',
        '<figure class="figure figure-diagram" id="fig:pipeline">'
        '<div class="diagram-scroll"><svg viewBox="0 0 960 706"',
    )
    html = html.replace(
        "</svg>",
        "</svg></div><figcaption><span class=\"fig-number\">Figure 1.</span> System "
        "architecture. <strong>(A)</strong> Capture normalizes framework traces into one "
        "typed Episode IR. <strong>(B)</strong> Offline compilation touches no production "
        "traffic and is a cascade of independent rejection points; the barrier band lists "
        "conditions under which no statistical evidence can license an artifact. "
        "<strong>(C)</strong> Runtime resolves at the entry boundary, falling back to the "
        "unchanged agent on any refusal.</figcaption></figure>",
        1,
    )

    # Equations: attach the anchor and the right-hand number the manuscript prints.
    def number_equation(match: re.Match[str]) -> str:
        label = match.group(1)
        number = registry.get(label, {}).get("number", "")
        return (
            f'<span class="eq" id="{attr(label)}">{match.group(2)}'
            f'<span class="eq-no">({number})</span></span>'
        )

    html = re.sub(
        r"GACEQ(eq:[^G]+)GACEQ\s*(<math display=\"block\"[^>]*>.*?</math>)",
        number_equation,
        html,
        flags=re.S,
    )

    # Figures: number the captions and restore the alt text \Description carried.
    figure_number = [0]

    def dress_figure(match: re.Match[str]) -> str:
        label = match.group(1)
        figure_number[0] += 1
        return f'<figure class="figure" id="{attr(label)}"'

    html = re.sub(r'<figure id="(fig:[^"]+)"[^>]*', dress_figure, html)
    for label, alt in descriptions.items():
        html = re.sub(
            rf'(<figure class="figure" id="{re.escape(label)}">\s*<img src="[^"]*")',
            lambda m, text=alt: m.group(1) + f' alt="{attr(text)}"',
            html,
        )

    def number_figcaption(match: re.Match[str]) -> str:
        label, caption = match.group(1), match.group(2)
        number = registry.get(label, {}).get("number", "?")
        return (
            f'<figure class="figure" id="{attr(label)}">{match.group(3)}'
            f'<figcaption><span class="fig-number">Figure {number}.</span> {caption}</figcaption>'
        )

    html = re.sub(
        r'<figure class="figure" id="(fig:[^"]+)">(.*?)<figcaption>(.*?)</figcaption>',
        lambda m: f'<figure class="figure" id="{attr(m.group(1))}">{m.group(2)}'
        f'<figcaption><span class="fig-number">Figure '
        f'{registry.get(m.group(1), {}).get("number", "?")}.</span> {m.group(3)}</figcaption>',
        html,
        flags=re.S,
    )

    # Tables: the site's evidence-table treatment, a numbered caption, and a scroll box so
    # a wide table never makes the page itself scroll sideways.
    def dress_table(match: re.Match[str]) -> str:
        label = match.group(1)
        number = registry.get(label, {}).get("number", "?")
        inner = match.group(2)
        inner = inner.replace("<table>", '<table class="evidence-table">', 1)
        inner = inner.replace(
            "<caption>",
            f'<caption><span class="tab-number">Table {number}.</span> ',
            1,
        )
        if label in totals:
            head, sep, tail = inner.rpartition("<tr>")
            if sep:
                inner = head + '<tr class="row-total">' + tail
        return f'<div class="table-scroll" id="{attr(label)}">{inner}</div>'

    html = re.sub(r'<div id="(tab:[^"]+)">(.*?)</div>', dress_table, html, flags=re.S)

    # Pandoc's per-cell inline alignment becomes the site's tabular-numeral class.
    html = re.sub(r'\s*style="text-align: right;"', ' class="num"', html)
    html = re.sub(r'\s*style="text-align: left;"', "", html)
    html = re.sub(r'\s*style="text-align: center;"', ' class="mid"', html)

    # Pandoc emits an empty <colgroup> block for every booktabs table; it adds nothing and
    # its percentage widths fight the design system's column sizing.
    html = re.sub(r"<colgroup>.*?</colgroup>", "", html, flags=re.S)

    html = html.replace("<blockquote>", '<blockquote class="epigraph">')
    return html


def heading_outline(html: str) -> list[tuple[str, str]]:
    """Top-level sections, in order, for the sidebar table of contents."""

    outline = []
    for match in re.finditer(r'<h1 id="([^"]+)"[^>]*>(.*?)</h1>', html, flags=re.S):
        text = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        outline.append((match.group(1), text))
    return outline


def promote_headings(html: str) -> str:
    """Shift pandoc's h1..h4 down one level so the page keeps a single h1.

    build_pages.py enforces exactly one h1 per page, which is the article title in the
    masthead.  Section headings therefore start at h2.
    """

    for level in (4, 3, 2, 1):
        html = re.sub(rf"<h{level}([ >])", rf"<h{level + 1}\1", html)
        html = html.replace(f"</h{level}>", f"</h{level + 1}>")
    return html


def number_headings(html: str, registry: dict[str, dict[str, str]]) -> str:
    """Print the manuscript's own section numbers alongside each heading."""

    def apply(match: re.Match[str]) -> str:
        tag, label, text = match.group(1), match.group(2), match.group(3)
        entry = registry.get(label)
        if entry is None or entry["prefix"] != "sec":
            return match.group(0)
        return (
            f'<{tag} id="{attr(label)}">'
            f'<span class="sec-number">{entry["number"]}</span> {text}</{tag}>'
        )

    return re.sub(r'<(h[2-5]) id="([^"]+)"[^>]*>(.*?)</\1>', apply, html, flags=re.S)


# ------------------------------------------------------------------------------ page


NAV = """  <header class="site-header"><nav class="nav" aria-label="Primary navigation">
    <a class="brand" href="index.html"><span class="brand-mark">GAC</span><span>Guarded Agentic Compaction</span></a>
    <button class="menu-button" data-menu aria-expanded="false" aria-controls="site-nav" aria-label="Toggle navigation">&#9776;</button>
    <ul class="nav-links" id="site-nav" data-nav-links>
      <li><a href="index.html">Overview</a></li><li><a href="architecture.html">Architecture</a></li>
      <li><a href="method.html">Method</a></li>
      <li><a aria-current="page" href="article.html">Article</a></li>
      <li><a href="getting-started.html">Get started</a></li><li><a href="research.html">Research</a></li>
      <li><a href="limitations.html">Limits</a></li><li><a class="nav-cta" href="contributing.html">Contribute</a></li>
    </ul>
  </nav></header>"""

FOOTER = """  <footer class="site-footer"><div class="container footer-grid">
    <div><div class="footer-title">Guarded Agentic Compaction</div><p class="footer-note">Compile the routine, refuse the uncertain. Refusal is the first optimization, and every admitted artifact carries the risk level it was licensed at.</p></div>
    <div><div class="footer-label">Artifacts</div><ul><li><a href="downloads/compiling-recurrent-agent-workflows.pdf">Paper PDF</a></li><li><a href="downloads/gac-technical-review.pptx">Technical deck</a></li></ul></div>
    <div><div class="footer-label">Detail</div><ul><li><a href="research.html">Research evidence</a></li><li><a href="limitations.html">Limitations</a></li></ul></div>
    <div><div class="footer-label">Project</div><ul><li><a href="contributing.html">Contribute</a></li><li><a href="https://github.com/rrahimi-uci/guarded-agentic-compaction">Source</a></li></ul></div>
  </div></footer>"""


def render(article_html: str, abstract_html: str, outline: list[tuple[str, str]]) -> str:
    toc = "\n".join(
        f'        <li><a href="#{attr(anchor)}">{text}</a></li>' for anchor, text in outline
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{attr(DESCRIPTION)}">
  <meta name="gac-article-sources" content="{source_digest()}">
  <title>{esc(TITLE)} &mdash; Guarded Agentic Compaction</title>
  <link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="assets/css/styles.css"><script defer src="assets/js/site.js"></script>
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
{NAV}
  <main id="main">
    <article class="paper">
      <header class="paper-masthead"><div class="container">
        <div class="breadcrumbs"><a href="index.html">Guarded Agentic Compaction</a> / Article</div>
        <p class="eyebrow">Full article</p>
        <h1>{esc(TITLE)}</h1>
        <p class="paper-byline">Reza Rahimi &#183; JazzX AI, Los Altos, CA</p>
        <div class="paper-actions">
          <a class="button button-primary" href="downloads/compiling-recurrent-agent-workflows.pdf">Download the PDF</a>
          <a class="button button-secondary" href="https://github.com/rrahimi-uci/guarded-agentic-compaction">Code and artifacts</a>
        </div>
      </div></header>

      <section class="section-compact"><div class="container">
        <div class="paper-abstract">
          <h2 id="abstract">Abstract</h2>
{abstract_html}
        </div>
      </div></section>

      <section class="section"><div class="container doc-layout">
        <div class="prose paper-body">
{article_html}
        </div>
        <aside class="toc paper-toc"><strong>Contents</strong><ul>
        <li><a href="#abstract">Abstract</a></li>
{toc}
        </ul></aside>
      </div></section>
    </article>
  </main>
{FOOTER}
</body>
</html>
"""


# ------------------------------------------------------------------------------ build


def verify(page: str, registry: dict[str, dict[str, str]], body: str) -> None:
    """Fail closed when the rendered page has silently lost part of the manuscript.

    The expected counts are read out of ``body.tex`` rather than frozen here. They used
    to be constants, and adding four figures and three algorithms to the manuscript
    turned this gate from "the page lost something" into "the constants are stale" --
    which is the failure mode a fail-closed check exists to prevent, not to cause.
    """

    tables = len(re.findall(r"\\begin\{table\*?\}", body))
    figures = len(re.findall(r"\\begin\{figure\*?\}", body))
    checks = {
        "numbered sections": (
            page.count('<span class="sec-number">'),
            sum(1 for entry in registry.values() if entry["prefix"] == "sec"),
        ),
        "tables": (page.count('class="evidence-table"'), tables),
        "table captions": (page.count('<span class="tab-number">'), tables),
        "figures": (len(re.findall(r'<figure class="figure[ "]', page)), figures),
        "figure captions": (page.count('<span class="fig-number">'), figures),
        "figure images": (
            page.count("assets/figures/"),
            len(re.findall(r"\\includegraphics", body)),
        ),
        "numbered equations": (
            len(re.findall(r'<span class="eq" ', page)),
            len(re.findall(r"\\label\{eq:", body)),
        ),
        "algorithm": (
            page.count('class="algorithm"'),
            len(re.findall(r"\\input\{\.\./figures/alg-", body)),
        ),
        "bibliography": (page.count('id="refs"'), 1),
    }
    problems = [
        f"{name}: rendered {actual}, expected {expected}"
        for name, (actual, expected) in checks.items()
        if actual != expected
    ]
    if "GACEQ" in page or "GACREF" in page or "GACARCH" in page or "GACALG" in page:
        problems.append("an internal passthrough token survived into the output")
    if re.search(r'<img (?![^>]*\balt=)', page):
        problems.append("an image reached the page without alt text")
    if problems:
        raise BuildError("article page verification failed:\n- " + "\n- ".join(problems))


def build() -> str:
    body = normalize(BODY.read_text(encoding="utf-8"))
    registry = build_registry(body)
    descriptions = extract_descriptions(body)

    article = run_pandoc(preprocess(body, registry), standalone_fragment=False)
    article = postprocess(article, registry, descriptions, frozenset(summary_rows(body)))
    article = promote_headings(article)
    outline = [
        (anchor, re.sub(r'<span class="sec-number">[^<]*</span>\s*', "", text))
        for anchor, text in re.findall(r'<h2 id="([^"]+)"[^>]*>(.*?)</h2>', article, flags=re.S)
    ]
    article = number_headings(article, registry)
    outline = [(anchor, re.sub(r"<[^>]+>", "", text).strip()) for anchor, text in outline]

    abstract_tex = preprocess(ABSTRACT.read_text(encoding="utf-8"), registry, floats=False)
    abstract = run_pandoc(abstract_tex, standalone_fragment=True)
    abstract = postprocess(abstract, registry, {})

    page = render(article, abstract, outline)
    verify(page, registry, body)
    return page


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify the committed page matches the sources without rewriting it",
    )
    args = parser.parse_args()

    page = build()
    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != page:
            raise BuildError(
                "site/article.html is stale relative to paper/tex/; "
                "regenerate it with: python scripts/build_article_page.py"
            )
        print("site/article.html is current")
        return

    OUTPUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({len(page):,} bytes)")


if __name__ == "__main__":
    main()
