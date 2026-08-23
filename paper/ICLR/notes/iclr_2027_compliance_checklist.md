# ICLR 2027 Compliance Checklist

Source references used for this checklist:

- official ICLR 2027 author guidelines
- official ICLR 2027 call for papers
- official ICLR 2027 AI policy for authors

## Template and formatting

- [x] Uses the official ICLR 2027 style files downloaded from the official style zip.
- [x] The repository defaults to the blind submission build (`\iclrfinalcopy` commented out).
- [x] The stock review line-number ruler is enabled in the blind build.
- [x] `times` replaced by `newtxtext`/`newtxmath` because this paper builds with Tectonic (XeTeX), where legacy `times` does not resolve: the body falls back to Latin Modern with no bold or italic, so `\textbf`, `\emph`, `\textsc`, theorem heads, and table headers all rendered as upright regular text. Under pdfTeX `times` works fine, so this is a toolchain interaction, not a broken package. Embedded body face is TeX Gyre Termes (Times), confirmed with `pdffonts`.
- [x] Confirmed from the compiled PDF that the main text (sections 1--8) ends within the `<= 9` page limit.
- [x] References are separated from the main text and do not count toward the page limit.
- [x] Appendix is placed after the references.
- [x] The paper source stays in a dedicated `paper/ICLR/` working directory.

## Anonymity

- [x] **The submission source and PDF are anonymous.** `main.tex` contains no
  identifying author block; `\iclrfinalcopy` is commented out; the style file
  prints "Anonymous authors" and uses the "Under review" running head; and the
  PDF author metadata is explicitly empty. Recheck this after every build
  intended for upload.
- [x] No acknowledgements are included in the blind-ready submission source.
- [x] The main paper avoids linking directly to the identified public repository.
- [ ] Prepare an anonymous supplementary artifact bundle or anonymous repository before submission. The paper states this as a pre-upload action and does not claim that the current identified repository is anonymous.

## Required and recommended sections

- [x] Required AI use statement included before references.
- [x] Ethics statement included before references.
- [x] Reproducibility statement included before references.
- [x] Limitations are discussed explicitly in the main paper (section 7) and extended in appendix E.

## Technical presentation

- [x] Formal problem statement with numbered equations (grounding, prefix invariant, selective dispatch, selective objective).
- [x] System architecture diagram (figure 2) instead of a bulleted box stack, plus a provenance figure (figure 3) that makes eq. 1 concrete on the motivating record.
- [x] Deployed compiler and admission rule given as algorithms 1--2 in the main text; provenance construction and runtime dispatch as algorithms 3--4 in the appendix.
- [x] Proposition 1 stated in a theorem environment with a proof in appendix A; `alpha`, `delta`, and the threshold grid are defined in the main text before use.
- [x] Every float is referenced from the body text. **This was false until the 2026-08-16 pass**: figure 1 and the per-family reduction figure were both included but never cross-referenced. Both now are.
- [x] Paired statistics reported: exact McNemar, Clopper--Pearson bounds, bootstrap intervals, Wilcoxon signed-rank. Headline CIs in the main text, full per-endpoint table in appendix E.
- [x] Absolute counts reported alongside every percentage (359 -> 120 requests, 294,677 -> 108,839 tokens, etc.) so reductions are auditable.
- [x] Admission certificates reported for the artifacts that were admitted (n=92 groups, k=0 violations, U=0.0498 <= alpha=0.05, coverage 1.0), not just pass/fail.
- [x] Refusal funnel table (table 4) shows stage-by-stage attrition on NESTFUL and API-Bank, isolating calibration as the binding stage.
- [x] Corrected the confidence budget: the configured value is `delta = 0.1`, not 0.05. It is what yields the 92-group requirement and the 0.0498 bound recorded in `paper/results/admission_register.json`; `delta = 0.05` would require 106 groups.
- [x] Hyperparameters collected in appendix C.

## Claim hygiene

- [x] Main claim is narrowed to guarded compile-or-retire specialization.
- [x] Manual baseline parity is stated explicitly rather than hidden, including the one family where the manual program is cheaper.
- [x] Refusal/retirement evidence is retained and described as part of the result, with the binding stage identified (calibration, not provenance or replay).
- [x] Cross-repository evidence is described as narrower than the primary workflow-family result.
- [x] Saturated feasibility ceiling flagged as a property of the workload, not evidence about the compiler.

## Submission operations

- [x] Recompiled the final PDF and verified page count for the current draft.
- [x] Related work cites the trace-JIT, partial-evaluation, effect-system,
  program-synthesis, and risk-control lineage rather than only
  agent-optimization papers. All 24 cited keys resolve, with no unused entries.
- [x] Sanity-checked that the current figures, captions, and appendix do not reveal author identity.
- [x] Official ICLR 2027 pages rechecked on August 14, 2026. The current guide
  lists the abstract deadline as `September 18, 2026` AOE and the full-paper
  deadline as `September 25, 2026` AOE. Recheck once more immediately before
  upload because conference instructions can change.

## Revision pass, 2026-08-16

Checked against `paper/open_research/article.pdf` as the source of truth and against the
official ICLR 2027 template's own instruction text
(`template/iclr2027/iclr2027_conference.tex`), which fixes the 9-page main-text limit, the
caption placement and typography rules, and the statement/appendix ordering.

### Compliance defects found and fixed

- **Two unreferenced floats.** Figure 1 (the two-cohort example) and the per-family
  reduction figure appeared in the build but no body text pointed at them.
- **A table that was not a table.** "Primary GitHub benchmark at a glance" was built by hand
  from `\refstepcounter{table}` inside a `center`+`minipage`, with a bold literal "Table N."
  in place of a caption. It is now a real `table` float with `\caption`.
- **Colour in running text.** `\retire` was `\textcolor{gacred}{\textsc{retire}}` and printed
  as a red word in body paragraphs. The template asks that the body make sense in black and
  white; it is now plain small caps.
- **Mixed cross-reference styles.** `\S\ref{...}` in section 4 against `\cref` elsewhere.
- **Acronym inconsistency.** Bare "GAC" in three sections and `\textsc{Patg}` against the
  article's `PATG`.

### Correctness and consistency defects found and fixed

- The introduction wrote the trace as `record(4420)`, `labels(4420)`,
  `comments(4420, limit=100)`, hiding that the later issue numbers come from the *returned*
  `record.issue_number` -- the witness the entire provenance argument turns on. It now says
  so, names the retirement reason (`ungroundable_slot`), and states the
  maximal-justified-prefix outcome.
- The cross-repository caption claimed a fixed template is "at least as efficient in both
  settings." It is more efficient in the 5-repo core and essentially tied in the balanced
  rerun, where it is marginally *worse* on cost. The caption now states both.
- Proposition 1 reused $\eta$ for the data-selected threshold; it now writes $\hat\eta$.
- $\kappa$ was used and never given a value ($\kappa=3$); $\Lambda$ was cited by cardinality
  only and is now written out.
- The abstract implied provenance reconstruction always succeeds; it now states the refusal
  branch, and reports the 89/90 baseline next to the 90/90 compiled result.

### Substance ported from the source article

- The compile cascade is one-way: a later stage may reject a candidate an earlier stage
  passed, but no later stage can authorize one that an earlier stage blocked.
- $q$ is *fitted* on development groups that were unproductive in any way (wrong or
  abstained); the bound is *counted* only from dispatched groups that were wrong.
- The candidate-multiplicity repair, $\gamma=\delta/(m|\Lambda|)$: 92 groups become 106 at
  $m=2$.
- The concrete independence caveat: `min_days = 1`, `min_principals = 1`, one snapshot.
- Where "unchanged baseline" is byte-exact and where it is only guarded substitution.

### Budget and build after the pass

Sections 1--8 still end on page 9; the AI use, ethics, and reproducibility statements and
the references begin on page 10; the appendix follows the references. Zero overfull
horizontal boxes. Blind build verified ("Anonymous authors" on page 1, empty PDF `Author`).
The recovered space came from the introduction, where one paragraph restated the
contributions list and another restated the abstract.

## Revision pass, 2026-08-23

Full ICLR 2027 Author Guidelines re-fetched and cross-checked line by line: 9-page main-text
cap (desk-reject if exceeded), references/AI-use/ethics/reproducibility statements exempt
from the cap, appendix unlimited, no separate "paper checklist" is required this cycle
(unlike NeurIPS), and double-blind anonymity must hold through the source and the PDF.
Cross-checked against a from-scratch `tectonic --outdir build main.tex` rebuild (not just the
committed PDF) and against rendered page images, not text extraction alone.

### Compliance defect found and fixed

- **Section 8 (Conclusion) spilled 3 lines onto page 10, ahead of the AI Use Statement.**
  The two abstract edits merged just before this pass (PRs #30, #31) each reflowed the whole
  document by a line or two; nobody re-ran the page-9 boundary check the README itself
  documents (`pdftotext -f 9 -l 9 build/main.pdf - | tail -20`) after either merge, and the
  committed `build/main.pdf` had main text bleeding onto page 10 -- a `main text beyond the
  page limit` desk-reject condition, not a cosmetic issue. Confirmed by rendering pages 9-10
  to PNG (text extraction alone would not show *where* on the physical page the break falls).
  Fixed by copy-editing (not by touching template spacing, which would read as gaming the
  limit): tightened redundant phrasing in `sections/discussion.tex`, `evaluation.tex`,
  `method.tex`, and `related_work.tex` (no claim, number, or citation removed), and shortened
  `sections/conclusion.tex` to drop a restated numeric detail already reported in full in
  section 5.3 and appendix F.3 (four further candidates retiring at the margin). Verified by
  full rebuild: section 8 now ends on page 9 with the AI Use Statement starting cleanly at the
  top of page 10, `pdfinfo` still reports 22 total pages, `pdffonts` still shows every font
  embedded, and no `??` unresolved cross-references appear anywhere in the extracted text.
- Proofread every section file, `appendix.tex`, and every table/figure caption for typos and
  grammar (grep sweep for doubled words, common misspellings, and `it's`/`its` confusion, plus
  a full manual read); none survived from the prior passes. No wording changes were made
  beyond the space-recovery copy-edits above.

### Verification commands run

```bash
tectonic --outdir build main.tex        # from-scratch rebuild, not the checked-in PDF
pdftotext -f 9 -l 9 -layout build/main.pdf - | tail -8   # section 8 ends here, in full
pdftotext -f 10 -l 10 -layout build/main.pdf - | head -6 # AI USE STATEMENT starts here
pdfinfo build/main.pdf | grep -E "Pages|Author"          # 22 pages, empty Author
pdffonts build/main.pdf | awk '{print $4}' | sort -u     # every row "yes" (embedded)
pdftotext -layout build/main.pdf - | grep -n '??'        # no unresolved refs
```
