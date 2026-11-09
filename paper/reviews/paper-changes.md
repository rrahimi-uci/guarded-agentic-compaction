# Paper changes from the 2026-11-08 audit

All changes are on branch `paper/rebuttal-audit-and-answers`; the paper on `main` is untouched until the
PR is merged. Each change comes from a finding in [`audit.md`](audit.md) (item numbers refer to its
disposition table). The main text still ends on page 10. A layout fix (below the table) removed a forced page break and
a float-only page, so the PDF is now 63 pages; no text changed in that fix.

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

**Second pass (2026-11-08, later the same day).** Three more edits, two to `sections/introduction.tex` and one to
`sections/results.tex`, all consistency fixes found by re-reading the main text against the abstract,
the results and the appendix tables:

| # | File | Before | After | Reason |
|---|---|---|---|---|
| 13 | `sections/introduction.tex` contribution 1 | "only when enough independent calibration examples pass" | "only when enough calibration examples, assumed independent, pass" | The abstract was changed to "assumed independent" in edit 2; the introduction still asserted independence |
| 14 | `sections/introduction.tex` contribution 2 | "uses fewer model requests with no detected accuracy loss" | "uses fewer model requests at similar accuracy" | On BIRD the compiled agent trails warm reruns of the unchanged agent (93 vs 95; 402 vs 412, §5.2); "no detected loss" held only against first runs |

| 15 | `sections/results.tex` §5.4 live recovery | "the completeness check's benefit is unresolved (204/216 versus 205/216; the agent repairs 22/27 incomplete prefetches)" | "... unresolved (without it, 210/216 under ordinary responses and 204/216 under capped ones, where the agent repairs 22/27 incomplete prefetches, versus 205/216)" | The 186 -> 205 contrast is the ordinary-response cohort, while 204/216 and 22/27 are the capped-response cohort (Tables 39-40); the sentence mixed them and omitted the ordinary-cohort 210/216, which favours the no-completeness arm (audit, second pass C1) |

None of the three edits changes a number. The build is still 63 pages and §8 still ends on page 10.

**Layout fix (no wording change).** Two appendix pages were mostly empty. `sections/adaptive_gates_appendix.tex`
had a `\pagebreak` before the Appendix L "Decision" paragraph, which left most of a page blank; it is
removed. Table 46 (`tab:compiler-comparison`, Appendix N) was a `[t]` float at the end of the file, did not
fit on the last text page, and sat alone on its own page above and below a large gap; it now sits between
the two Appendix N paragraphs with `[!h]` placement. Table, section and appendix numbers are unchanged.

**Left unchanged, with reasons, in `audit.md`:** items 5, 6, 16, 17 and 19. Item 19 is "40 under the
corrected grader", which rests on a protocol note rather than a retained regraded result; it stays in
the paper with its citation, but the replies do not use it.

**Build:** `tectonic --outdir build main.tex` from `paper/iclr/`. The output is 63 pages, and §8
(Conclusion) ends on page 10. `paper/iclr/build/main.pdf`, `paper/iclr/main-final.pdf` and
`paper/iclr/upload/GAC_ICLR2027_revised.pdf` are refreshed from that build.


## Third pass (2026-11-08, after three independent re-checks)

Three fresh checks were run from the sources with the earlier work treated as untrusted: every number and
pointer in the replies (107 items), a from-scratch claims audit of the abstract, §1, §5, the conclusion and
the main-text captions (about 75 claims), and every cross-reference against the built PDF. No numeric
mismatch was found in the paper. The edits below are wording and scoping corrections; none changes a
headline number. Table, figure, section and appendix numbers are unchanged (label map identical to the
second-pass build; 63 pages; §8 ends on page 10).

| # | Location | Old | New | Evidence | Headline? |
|---|---|---|---|---|---|
| 16 | Abstract | "automates that step safely" | "automates that step under explicit guards" | No measured quantity is a safety quantity: the bounds are replay-contract violation rates on selected populations and final-answer failure rates on one family (Table 28). The only unqualified safety claim is removed. | No |
| 17 | Abstract | "admits one only when ... support a finite-sample error bound"; "pull-request bounds cover final answers: no failure on 132 ... (90% upper bound 0.0173). A later study ... each admitted (bounds 0.023–0.042)" | "support a finite-sample bound on its violation rate"; "two pull-request studies bound final answers: no failure on 132 ... (one-sided 90% bound 0.0173), and, with one pull request per author sampled before any outcome filter, 3 misses in 760 groups across four repositories, each repository admitted (registered-grid bounds 0.023–0.042)" | The 0.0173 is the single-rule 90% bound and 0.023–0.042 are registered-grid bounds (per-threshold level 1−0.1/11); the two scales were unlabelled and "each admitted" was ambiguous. Numbers unchanged (time_forward certificate.json; multirepo summary.json). `paper/iclr/notes/snippets/abstract_for_openreview.txt` updated to match. | No |
| 18 | Table 1, NESTFUL/API-Bank/BFCL row | "Nothing; no safety bound" | "Nothing; no admissible bound" | Same reason as 16. | No |
| 19 | Table 1, AppWorld row | "1 admitted, 4 retired" | "1 of 6 admitted" | `appworld_compiler_execution.json` admission.B: six candidates reached calibration (groups 89, 92, 92, 90, 46, 26): one emitted, one dominated at 92/92, four retired; App. F.4 and Table 28 already say six. | No |
| 20 | §1 | "(the traces the compiler learns from)" | "(the source of the compiler's traces)" | The compiler uses 116 exact traces of the 132 discovery runs (16/8/92 split; 2 excluded, 14 unused; compile report and the population audit), so the old parenthetical overstated what "all 132" are. | No |
| 21 | §5.4 | "39/60 silent wrong answers in both arms (40 under the corrected grader)" | "39/60 silent wrong answers in both arms" | The retained `drift_continuation_graded/results.json` records 39/39; the 40 exists only in a protocol note, with no retained regraded artifact. The unsupported parenthetical is removed; 39 stays. | No |
| 22 | §8 Conclusion | "cutting model cost 58.7–73.6%" | "cutting cost 58.7% (primary families) and 73.6% (eleven repositories)" | 58.7% is the three-family primary pool (90 records, Table 2); 73.6% is the eleven-repository PR-outcome end-to-end pool (3,560 groups, Table 19). A range joined two studies. | Wording of a headline sentence; numbers unchanged |
| 23 | App. F.7 | "The one certificate whose event includes the continuation comes from a post-cutoff PR-outcome cohort"; "Every certificate except the post-cutoff one instantiates L(A,x)=1 as a replay-contract violation" | "The first certificate whose event ..."; "Every certificate except the PR-outcome end-to-end ones instantiates ..." | Table 28 lists three end-to-end rows (post-cutoff and the two multi-repository stages); §2 and §5.4 were already corrected in the second pass and these two sentences were stale. | No |
| 24 | Table 28 caption | "or, in the last row, the primary grid" | "or, for the post-cutoff row, the primary grid" | The row with the parenthesized grid bound (0.0173 (0.035)) is the sixth of eight, not the last. | No |

**Also in this pass (not paper changes):** the no-go record for the fresh-issue single-look gate replication
(`paper/supplementary/fresh-issue-gate-single-look-protocol.md`, `paper/results/graded_issue_gate_tf/preflight.json`,
`audit_tf.json`, scripts and tests) is brought onto the branch from `agent/c1-gate`, so the 277/197/117 figures used in
Ans-3 now have a retained source; the upload README path to the abstract snippet is corrected; the replies and
`review-map.md` corrections are listed in `audit.md` ("Third pass").

**Left unchanged, with reasons:** §5.1 "1,362 fresh records" vs Table 3 "1,344": both correct (18 pilot episodes,
App. J) and already noted in `audit.md`; adding the relation would risk the page budget for no change in meaning.
Table 3's 100U level (0.05/6) is stated in App. K, not in the caption. The AppWorld retired bounds "1.000, 1.000" copy
the compiler's no-threshold message (App. F.4 explains it).

**Build:** `tectonic --outdir build main.tex` from `paper/iclr/`; 63 pages; §8 ends on page 10; label map identical to
the second-pass build. `paper/iclr/build/main.pdf`, `paper/iclr/main-final.pdf` and `paper/iclr/upload/GAC_ICLR2027_revised.pdf`
are refreshed (SHA-256 `d6cad56b0322cc3c681dbad76e2216f568a6a07feae8d3fd3cbe3037c84d97fe`).

## Fourth pass (2026-11-09, compiler funnel and live pilot folded in)

After the third pass, two further pre-registered studies were run and merged (`paper/results/compiler_funnel/`,
`paper/results/compiler_funnel_pilot/`). They are the same-IR form of the matched compiler comparison R1 and R2
asked for, so the reply text that called that comparison "designed but not run" was out of date. Both are
now reported in the paper and cited in the replies. Nothing in the main text changes; the main text still ends
on page 10.

| # | Location | Old | New | Evidence | Headline? |
|---|---|---|---|---|---|
| 25 | App. N, new subsection "Same-IR compiler funnel and a live pilot on fresh issues" (Tables 47, 48) | (absent) | Four-policy funnel over the 13 retained cohorts: support-only admits what full admission admits everywhere; grounding changed one decision (issue-type third read; replay 0 violations, 1 unproductive of 92). Sealed pilot on 193 fresh issues: GAC admitted the three-read program (16/16 training agreement; 92 groups, 0 violations, bound 0.0498); arms 65/65, 63/65, 64/65 at 1, 1, 4 requests; every miss a non-verbatim excerpt; McNemar p = 0.50; $0.23. | `compiler_funnel/results.json`, `compiler_funnel_pilot/results.json`, `compile.json`; both tables regenerate from JSON (validator). | No new headline claim; the subsection states no measured guard benefit. |
| 26 | Table 46 caption | "no matched execution comparison is reported" | "no matched execution comparison with an external system is reported (App. N runs the matched comparison within GAC's own pipeline)" | Same studies. | No |

**Replies:** Ans-general (opening sentence; point 5; "Not done" paragraph), Ans-1 part 2 (W2a now reports the funnel
and pilot instead of "designed, not run"), Ans-2 part 1 (W1b: what the automatic decisions are worth) and part 2
(W2a; summary item 7), Ans-3 part 2 (compile-time support-only equals full admission on 13 cohorts). All parts
re-measured under 5,000 characters. `review-map.md` rows R1-W2a, R2-W1b, R2-W2a and R3-Q2 and the NEEDS EXPERIMENT
table are updated; the external-compiler, adaptive-workload and two-coverage-level items stay "not run".

**Build:** `tectonic --outdir build main.tex` from `paper/iclr/`; 64 pages; §8 ends on page 10; label map identical to
the third-pass build except the two new tables (47, 48) appended after Table 46. `paper/iclr/build/main.pdf`,
`paper/iclr/main-final.pdf` and `paper/iclr/upload/GAC_ICLR2027_revised.pdf` are refreshed
(SHA-256 `a351a1890e58cd2103db6e5e51c297805d5f294d9ef6340b5f2d52ccb9710b83`).

## Fifth pass (2026-11-09, PAT re-audit)

An independent re-audit of the 12 September PAT feedback against the current build found every item addressed
except four small ones, and found that change-log entries 18 and 19 had never reached the generated table.

| # | Location | Old | New | Evidence | Headline? |
|---|---|---|---|---|---|
| 27 | Table 1 (generated by `iclr_revision_statistics.py decisions`) | "Nothing; no safety bound"; "1 admitted, 4 retired" | "Nothing; no admissible bound"; "1 of 6 admitted" | Entries 18 and 19 were applied to the change log only; the generator strings were unchanged, so the built PDF still carried the old cells. Fixed in the generator and regenerated. | No |
| 28 | §7 | "native browser and matched compiler comparisons remain unrun." | "native browser and external compiler comparisons remain unrun (Appendices G and N.1)." | PAT item E4; the same-IR form is run (App. N.1), the external one is not. | No |

**Tried and reverted for the page budget:** "per-candidate" in the abstract, a §7 clause on the unexercised
`min_days`/cluster-unit controls, and appendix pointers after six main-text table references; each pushed §8 onto
page 11. The abstract and §7 items stay open in `paper/iclr/notes/pat_feedback_disposition.md` ("Re-audit").

**Build:** 64 pages; §8 ends on page 10; label map unchanged (same 199 labels; Tables 46–48 unchanged).
`paper/iclr/build/main.pdf`, `paper/iclr/main-final.pdf` and `paper/iclr/upload/GAC_ICLR2027_revised.pdf` refreshed
(SHA-256 `154d1a72fc761a4e12842f446ed5e16ac42ff59f0304a49f8b0c0de8f736878e`). A reply to the PAT thread, `paper/reviews/Ans-LLM.txt`, is provided as optional.
