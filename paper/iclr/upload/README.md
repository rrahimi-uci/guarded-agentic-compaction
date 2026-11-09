# Upload package for the ICLR 2027 discussion phase

Status: ready for the author to upload. Nothing here has been posted to OpenReview.

## 1. Upload the revised PDF first

- File: [`GAC_ICLR2027_revised.pdf`](GAC_ICLR2027_revised.pdf), a copy of `paper/iclr/build/main.pdf`
  (also copied to `paper/iclr/main-final.pdf`).
- 64 pages; the main text ends on page 10 (the ICLR limit). Built with `tectonic --outdir build main.tex`
  from `paper/iclr/`.
- SHA-256: `154d1a72fc761a4e12842f446ed5e16ac42ff59f0304a49f8b0c0de8f736878e`. Record it next to the
  upload date when you upload.
- The revised abstract for the OpenReview form is `../notes/snippets/abstract_for_openreview.txt`.
- This build includes the 2026-11-08 audit corrections (second and third passes) listed in
  `paper/reviews/paper-changes.md`, the decision audit examples in Appendix O, and the 2026-11-09
  fourth-pass addition: an Appendix N subsection with the same-IR compiler funnel and the fresh-issue
  live pilot (Tables 47 and 48, placed after Table 46). Every other table, figure, section and
  appendix number is unchanged from the second-pass build.
- 2026-11-09 fifth pass: Table 1 now reads "no admissible bound" and "1 of 6 admitted" (the two cells
  the third-pass log recorded but had not applied), and Section 7 points to Appendices G and N.1 for the unrun
  comparisons. No table, figure, section or appendix number changed. If you already uploaded the previous
  PDF, replace it with this one.

## 2. Post the replies in this order

The replies are plain text in `paper/reviews/`, one official comment per file. Each file is under
4,900 characters even if line breaks are counted twice (characters / with line breaks counted twice:
general 4,846 / 4,870; R1 4,868 / 4,888; R2 4,825 / 4,839; R3 4,847 / 4,857).

| Order | File | Post as |
|---:|---|---|
| 1 | `paper/reviews/Ans-general.txt` | Top-level official comment to all reviewers (post after the PDF upload; it refers to the PDF diff) |
| 2 | `paper/reviews/Ans-1.txt` | Reply to Reviewer 1 |
| 3 | `paper/reviews/Ans-2.txt` | Reply to Reviewer 2 |
| 4 | `paper/reviews/Ans-3.txt` | Reply to Reviewer 3 |
| 5 (optional) | `paper/reviews/Ans-LLM.txt` | Official comment under the PAT "LLM Feedback by Program Chairs" thread, if you want the disposition on record; under 4,900 characters |

These replies supersede the earlier per-post drafts generated from
`paper/iclr/notes/review_response_2026-11-06.md`, which is kept as background.

## 3. Checked before packaging

- Every number in the replies appears in the text of this PDF (re-checked after the fourth pass).
- The claims in the paper were audited against the raw results: `paper/reviews/audit.md`, with
  re-derivation scripts in `paper/reviews/audit_scripts/`.
- Every reviewer point is classified in `paper/reviews/review-map.md`.

## 4. What to read yourself before uploading

- The first page, the abstract and the conclusion. The abstract now says GAC automates the step
  "under explicit guards" (not "safely") and labels the two bound scales; the conclusion's cost claim is
  "58.7% (primary families) and 73.6% (eleven repositories)", not a single range.
- §5.2 (BIRD): on a second model and the training split, the compiled agent trails warm reruns of
  the unchanged agent (93 vs 95; 402 vs 412). This is now stated.
- Appendix F.2 and Table 19: Amendment 3 was registered after the first four repositories' results
  were seen. The paper and the replies say so; do not describe it as pre-registered in advance of
  all data.
