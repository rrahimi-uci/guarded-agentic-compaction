# ICLR 2027 manuscript readiness — 2026-10-16

The current deliverable uses the previously agreed **ten-page revision target**.
It is not a nine-page initial-submission build and this file does not establish
that OpenReview permits an upload today. The supplied PAT feedback is automated
pre-submission feedback, not proof that the conference discussion phase is open.

Official sources checked on 2026-10-16:
[author guidelines](https://iclr.cc/Conferences/2027/AuthorGuidelines) and
[reviewer guidelines](https://iclr.cc/Conferences/2027/ReviewerGuidelines).
The formatting section specifies nine main-text pages initially and ten during
discussion/camera-ready; statements, references, and appendices are exempt.

## Current checks

- [x] Anonymous review template, line numbers, no author metadata or acknowledgements.
- [x] Problem, research questions, novelty scope, methods, and limitations reviewed.
- [x] Slot/value notation, group-level loss, candidate multiplicity, calibration
  coverage, and per-partition freezing scope reconciled with implementation.
- [x] Score features/training and bounded DSL types/composition documented.
- [x] Manual resources, failure denominators, repeated BIRD questions, and null
  safeguards/gate findings retained without equivalence claims.
- [x] AI use, ethics, and reproducibility statements present.
- [x] Related-work claim/citation audit and recent primary-source checks recorded.
- [x] Current PAT ledger covers every numbered and minor feedback item, with
  justified alternatives and remaining empirical gaps identified.
- [ ] Initial submission: prepare a separate nine-page version if that is the
  intended upload stage; the ten-page revision must not be used as that version.
- [ ] Author: confirm submission stage, permitted upload window, and final content.
- [ ] Author: upload the reviewed PDF/supplement and update metadata; nothing has
  been posted to OpenReview by this revision.

Exact build, validation, visual-review and supplementary-package results are
recorded in [final_reviewer_assessment.md](final_reviewer_assessment.md).
Acceptance risks remain there even when mechanical checks pass.

## Historical revision log (not current readiness assertions)

The dated entries below are retained as history. Their counts, figure numbers,
page references and “done” states must not be read as current verification.

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
