# ICLR 2027 Submission Draft

This directory contains the condensed ICLR 2027 submission source
for:

> **From Traces to Guarded Programs: Evidence-Gated Compilation of Recurrent Agent Workflows**

## Contents

- `main.tex`: submission entrypoint using the official ICLR 2027 style files.
- `sections/`: main-paper sections (`abstract`, `introduction`, `problem`,
  `method`, `evaluation`, `results`, `related_work`, `discussion`,
  `conclusion`).
- `figures/`: the TikZ architecture diagram (`pipeline_overview.tex`), the four
  algorithm floats (`alg-compile`, `alg-calibrate`, `alg-patg`,
  `alg-dispatch`), and the generated result PDFs.
- `tables/`: compact tables written for the ICLR version.
- `appendix.tex`: proof, additional algorithms, configuration, extended
  limitations. Included after the references.
- `notes/`: reviewer gap analysis and submission compliance checklist.
- `build/`: compiled PDF and LaTeX auxiliaries.
- `template/`: downloaded official ICLR 2027 style zip and extracted originals.

## Compile

From this directory:

```bash
tectonic --outdir build main.tex
```

## Deliberate deviations from the stock template

Two changes to the template preamble are intentional and should be kept.

1. **The review line-number ruler is suppressed** (author's explicit request).
   The style file paints a vertical line-number ruler in the left margin unless
   `\iclrfinalcopy` is set. `main.tex` redefines `\iclrruler` to a no-op in
   both the named preprint build and the blind submission build.

   Note this is a deliberate departure from the stock submission appearance.
   ICLR reviewers routinely cite line numbers in their reviews, so removing the
   ruler makes their job harder and makes the PDF look non-standard next to
   other submissions. Nothing in the template text forbids it and no page/margin
   rule is affected, but it is the one change here a reviewer could notice. To
   restore it, delete this line from `main.tex`:

   ```latex
   \renewcommand{\iclrruler}[1]{}
   ```

2. **`times` is replaced by `newtxtext`/`newtxmath`** — because this paper is
   built with **Tectonic (XeTeX)**. Under pdfTeX the legacy `times` package
   resolves fine to Nimbus Roman; under Tectonic it does not, and the body
   silently falls back to Latin Modern with *no bold and no italic at all*, so
   every `\textbf`, `\emph`, `\textit`, `\textsc`, theorem head, and table
   header printed as upright regular text. `newtx` is the maintained
   Times-compatible replacement and resolves under both engines. The embedded
   body face in `build/main.pdf` is TeX Gyre Termes, i.e. Times, as the
   template requires — verify with `pdffonts build/main.pdf`. `\openbox` and
   `\Bbbk` are released before loading `newtxmath` because it and
   `amssymb`/`amsthm` both declare them.

   If you switch to `pdflatex` on a full TeX Live, reverting to
   `\usepackage{times}` is equally valid. Either way, **check bold and italic
   in the output before submitting** — the failure is silent.

## Authorship / anonymity switch

`main.tex` carries a real author block (Reza Rahimi, JazzX AI) and a single
`\iclrfinalcopy` line that selects between two builds:

| `\iclrfinalcopy` | Title block | Running head | PDF `Author` | Use for |
|---|---|---|---|---|
| present (as shipped) | Reza Rahimi, JazzX AI | `Preprint. Under review.` | `Reza Rahimi` | preprint, arXiv, circulation |
| commented out | `Anonymous authors` | `Under review as a conference paper at ICLR 2027` | empty | **the OpenReview upload** |

**ICLR 2027 initial submissions are double blind.** Comment out
`\iclrfinalcopy` before uploading, then confirm:

```bash
pdftotext -f 1 -l 1 build/main.pdf - | head -3   # must say "Anonymous authors"
pdfinfo build/main.pdf | grep Author             # must print nothing
```

Both builds are 18 pages and both end sections 1--8 on page 9, so the switch
never changes the page budget.

## Page budget

ICLR 2027 allows **9 pages** of main text; references, the AI use statement,
the ethics statement, the reproducibility statement, and the appendix do not
count. Sections 1--8 currently end on page 9 with no slack. Re-check after any
edit --- the last line of the conclusion must still be on page 9:

```bash
pdftotext -f 9 -l 9 build/main.pdf - | tail -20
```
