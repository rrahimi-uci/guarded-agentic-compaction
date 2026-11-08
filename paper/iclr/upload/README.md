# Upload package for the ICLR 2027 discussion phase

Status: ready for the author to upload. Nothing here has been posted to OpenReview.

## 1. Upload the revised PDF first

- File: [`GAC_ICLR2027_revised.pdf`](GAC_ICLR2027_revised.pdf), a copy of `paper/iclr/build/main.pdf`
  (also copied to `paper/iclr/main-final.pdf`).
- 63 pages; the main text ends on page 10 (the ICLR limit). Built with `tectonic --outdir build main.tex`
  from `paper/iclr/`.
- SHA-256: `d6cad56b0322cc3c681dbad76e2216f568a6a07feae8d3fd3cbe3037c84d97fe`. Record it next to the
  upload date when you upload.
- The revised abstract for the OpenReview form is `../notes/snippets/abstract_for_openreview.txt`.
- This build includes the 2026-11-08 audit corrections (second and third passes) listed in
  `paper/reviews/paper-changes.md` and the decision audit examples in Appendix O. Table, figure,
  section and appendix numbers are unchanged from the second-pass build.

## 2. Post the replies in this order

The replies are plain text in `paper/reviews/`. Each part is under 5,000 characters, and parts are
separated by a line of `==========`. Post each part as its own official comment.

| Order | File | Post as | Parts |
|---:|---|---|---|
| 1 | `paper/reviews/Ans-general.txt` | Top-level official comment to all reviewers (post after the PDF upload; it refers to the PDF diff) | 1 |
| 2 | `paper/reviews/Ans-1.txt` | Reply to Reviewer 1 | 3 (1/3, 2/3, 3/3) |
| 3 | `paper/reviews/Ans-2.txt` | Reply to Reviewer 2 | 2 |
| 4 | `paper/reviews/Ans-3.txt` | Reply to Reviewer 3 | 2 |

These replies supersede the earlier per-post drafts generated from
`paper/iclr/notes/review_response_2026-11-06.md`, which is kept as background.

## 3. Checked before packaging

- Every number in the replies appears in the text of this PDF.
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
