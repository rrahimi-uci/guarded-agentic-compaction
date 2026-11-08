# Paper changes from the 2026-11-08 audit

All changes are on branch `paper/rebuttal-audit-and-answers`; the paper on `main` is untouched until the
PR is merged. Each change comes from a finding in [`audit.md`](audit.md) (item numbers refer to its
disposition table). The main text still ends on page 10, and the PDF is still 64 pages.

**Does any change alter a headline result?** No reported number changed value. Two sentences that
carry headline numbers were corrected, and both changes make the claim narrower or more exact, not
more favourable:

- **HEADLINE SENTENCE (conclusion).** It said the compiled agent "matches hand-written programs at
  about 73% lower model cost" on "GitHub workflows". 73% held only for the 760-group pool; the three
  primary families pool to 58.7%, and the eleven-repository end-to-end pool is 73.6%. It now reads
  "matches hand-written programs while cutting model cost 58.7–73.6%".
- **HEADLINE SENTENCE (abstract).** The AWM comparison is described on 1,344 fresh records (the six
  noninferiority cells), not 1,362, which includes 18 pilot records. The results text keeps
  "8,172 episodes on 1,362 fresh records", which is the full count.

| # | File | Before | After | Reason (audit item) |
|---|---|---|---|---|
| 1 | `sections/problem.tex` §2 | "Every certificate in §5 except one end-to-end certificate instantiates … replay-contract violation" | "… except the PR-outcome end-to-end certificates …" | MISMATCH: §5.4 reports two end-to-end studies with nine per-repository certificates in the second (1) |
| 2 | `sections/abstract.tex` | "admits one only when enough independent calibration examples support a finite-sample error bound" | "… enough calibration examples, assumed independent, support …" | Independence is assumed, not shown (4) |
| 3 | `sections/abstract.tex` | "Agent Workflow Memory on 1,362 fresh records, five of six … cells" | "… on 1,344 fresh records …" | The cells use 1,344; 1,362 includes 18 pilot records (7, 18) |
| 4 | `sections/abstract.tex` | "Most bounds cover replay on selected populations; one covers final answers:" | "…; pull-request bounds cover final answers:" | Two final-answer studies follow (2) |
| 5 | `sections/conclusion.tex` | "it compiles grounded read-only prefixes, admits them under a finite-sample bound, refuses elsewhere, and on GitHub workflows matches hand-written programs at about 73% lower model cost than the unchanged agent" | "it compiles and admits grounded read-only prefixes under a finite-sample bound, refuses elsewhere, and on GitHub matches hand-written programs while cutting model cost 58.7–73.6%" | Overstated and mis-rounded cost figure (3); shortened to keep 10 pages |
| 6 | `sections/results.tex` opening | "shows that it recovers the program a person would write wherever the retained traces support one, and refuses, with a stated stage and reason, wherever they do not" | "shows that where it admits, it recovers the program a person would write, and where it refuses, it states the stage and reason" | The recurrence-only ablation shows a supported program the compiler refused (13) |
| 7 | `sections/results.tex` §5.2 BIRD | "(requests fall 49.6% and 45.8%)" | "(warm reruns 95 and 412; requests fall 49.6% and 45.8% vs. first runs)" | Second-model and training accuracy were compared with the first run only; the warm reruns of the unchanged agent scored higher than the compiled agent (11, 12) |
| 8 | `sections/results.tex` §5.4 | "Two end-to-end certificates exist." / "a bound of 0.0173" | "Two end-to-end studies exist." / "a 90% bound of 0.0173" | Undercount; confidence level missing (15) |
| 9 | `sections/discussion.tex` | "(one-sided bound 1.7%)" | "(one-sided 95% bound 1.7%, i.i.d. episodes)" | Level and assumption missing (8) |
| 10 | `sections/discussion.tex` | "six-study compiled-only misses are excerpts departing …" | "six-study compiled-only miss is an excerpt departing …" | There is exactly one (9) |
| 11 | `sections/evaluation.tex` | "with gate multiplicity controlled by the Bonferroni term" | "with threshold-grid multiplicity controlled by the Bonferroni term" | The term covers thresholds, not candidate selection (10) |
| 12 | `tables/compiler_decisions.tex` caption | "92/92 clean groups, bound 0.0498 ≤ 0.05" | "92/92 clean groups, per-candidate bound 0.0498 ≤ 0.05" | Per-candidate qualifier missing (14) |

**Left unchanged, with reasons, in `audit.md`:** items 5, 6, 16, 17 and 19. Item 19 is "40 under the
corrected grader", which rests on a protocol note rather than a retained regraded result; it stays in
the paper with its citation, but the replies do not use it.

**Build:** `tectonic --outdir build main.tex` from `paper/iclr/`. The output is 64 pages, and §8
(Conclusion) ends on page 10. `paper/iclr/build/main.pdf`, `paper/iclr/main-final.pdf` and
`paper/iclr/upload/GAC_ICLR2027_revised.pdf` are refreshed from that build.
