# Upload package for the ICLR 2027 discussion phase

Status: ready for the author to upload. Nothing here has been posted to OpenReview.

## 1. Upload the revised PDF first

- File: [`GAC_ICLR2027_revised.pdf`](GAC_ICLR2027_revised.pdf), a copy of `paper/iclr/build/main.pdf`
  (also copied to `paper/iclr/main-final.pdf`).
- 64 pages; the main text ends on page 10 (the ICLR limit). Built with `tectonic --outdir build main.tex`
  from `paper/iclr/`.
- SHA-256: `a2ee5f91b8e2bbffd417997854561d51accd14196ef1cac39b85da818e25e97e`. Record it next to the
  upload date when you upload.
- The revised abstract for the OpenReview form is `../snippets/abstract_for_openreview.txt`.
- OpenReview shows reviewers a diff against the September 24 PDF, so the global summary does not need
  to list every edit.

## 2. Post the responses in this order

Each file is one post, at most 4,500 characters (checked by `paper/scripts/build_openreview_posts.py`).
Post each as an official comment, markdown enabled.

| Order | File | Post as | Characters |
|---:|---|---|---:|
| 1 | [`posts/00_global.md`](posts/00_global.md) | Top-level official comment to all reviewers | 3,785 |
| 2 | [`posts/01_r1_part1.md`](posts/01_r1_part1.md) | Reply to Reviewer 1 (weaknesses) | 4,459 |
| 3 | [`posts/02_r1_part2.md`](posts/02_r1_part2.md) | Reply to Reviewer 1 (questions) | 4,466 |
| 4 | [`posts/03_r2_part1.md`](posts/03_r2_part1.md) | Reply to Reviewer 2 (weaknesses) | 3,452 |
| 5 | [`posts/04_r2_part2.md`](posts/04_r2_part2.md) | Reply to Reviewer 2 (questions) | 4,086 |
| 6 | [`posts/05_r3_part1.md`](posts/05_r3_part1.md) | Reply to Reviewer 3 (weaknesses) | 2,172 |
| 7 | [`posts/06_r3_part2.md`](posts/06_r3_part2.md) | Reply to Reviewer 3 (questions) | 4,399 |

The posts are regenerated from `paper/iclr/notes/review_response_2026-11-06.md` with
`python paper/scripts/build_openreview_posts.py`. Edit that file, not the posts.

## 3. Checked before packaging

- Table, figure and appendix numbers in the posts match this build of the PDF (read from its `.aux`).
- Every number in the posts appears in the PDF text, except two ToolHop and TraceCompiler screen
  figures (4.93 requests per episode; 225 of 13,500 dialogues) that come from committed provider-free
  screens (`paper/results/toolhop_screen/`, `paper/results/tracecompiler_screen/`).
- The end-to-end numbers equal `paper/results/multirepo_end_to_end/summary.json`.

## 4. What to read yourself before uploading

- The first page and the abstract: they now lead with "safe automation of the program an engineer
  would write". The claim that the compiled program matches the hand-written one is made for GitHub
  only; on BIRD the guarded candidate trailed the hand-written prefetch (26/36 against 28/36).
- Sections 2 and 7: six sentences were shortened to hold the ten-page limit.
- Appendix F.2 and Table 19: Amendment 3 was registered after the first four repositories' results
  were seen. The paper and the global summary say so; do not describe it as pre-registered in
  advance of all data.
