# Version gap: the PDF the reviewers read versus the current build

Reviewed file: `paper/reviews/openreview_submitted.pdf` (OpenReview forum `DF0JaS58gr`),
PDF created 2026-09-24 10:22 PDT, 36 pages, SHA-256
`331a6dbe5cc0d2572b198a6f64f8f6800e420cd369f5e046bd03f926b0874948`.
Current build: `paper/iclr/build/main.pdf` at main `5a84f0d`, 60 pages, SHA-256
`7c68caca3c68ffaffc0d09d74e8743a4dc265a64cda3a6d052eff5ecafbf5496`.

## Table numbers the reviewers used, in the reviewed PDF

| Reviewer citation | Reviewed PDF | Current build |
|---|---|---|
| R1 "Table 2" (benchmark/funnel table) | Table 2 "Where refusal happens ..." | Table 3 (two trace benchmarks), all four in Table 19 |
| R2 "Table 9" (hand-written comparator) | Table 9 | `tab:manual-resources` (appendix) |
| R2 "Table 19" (barrier-free replay) | Table 19 recurrence-only | `tab:recurrence-only` (appendix) |
| R2 "Table 23" (learned gate) | Table 23 gate-frontier disaggregated | `tab:gate-frontier-disaggregated` (appendix) |
| R1 "Table 20" (mechanism hazards) | Table 20 mechanism removal | `tab:mechanism-removal` (appendix) |
| R1 "Table 1" | Table 1 primary results | Table 1 |

Every response must say "Table N in the reviewed version, now Table M / Appendix X".

## Content counts (case-insensitive grep of pdftotext output)

| Term | Reviewed | Current |
|---|---:|---:|
| BIRD | 0 | 61 |
| Agent Workflow Memory / AWM | 0-1 | 8 / 38 |
| 8,172 (adapted-AWM episodes) | 0 | 4 |
| 0.0173 (132-group end-to-end bound) | 0 | 5 |
| post-cutoff | 0 | 12 |
| live recovery / scope guard | 0 / 0 | 3 / 2 |
| sequential extension (311 groups) | 0 | 3 |
| prefix census | 0 | 3 |
| TraceCompiler | 0 | 4 |
| population audit / exact-trace filter | 0 / 0 | 1 / 9 |
| Adaptive-Task Development Gates / AgentHop | 0 / 0 | 1 / 12 |
| EvoC2F | 1 | 5 |
| 0.0569 (two-candidate bound) | 8 | 8 |
| recurrence-only | 10 | 12 |

## Consequences for the response

1. The reviewed paper had **no live-agent study outside the three GitHub metadata families**
   and the cross-repository extension. R1 says so ("external benchmarks ... without live-agent
   efficiency measurements"). BIRD (live SQL agent, adaptive continuation, 26/31 databases,
   -44.9% requests) and the adapted-AWM comparison (8,172 episodes) are new since submission.
2. The reviewed paper had no end-to-end certificate, no population audit, no live-recovery
   mechanism study, no sequential issue-gate extension, no prefix census, and no adaptive-task
   development gates.
3. Everything the reviewers cite as a weakness that is still true (0.0569, day/author units,
   recurrence-only tie, constant learned score) is already in the reviewed version; the
   response must not imply those were new disclosures.
4. The reviewed abstract opens with the problem and the criterion (compile only when
   substitution is justified) before the numbers. The current abstract opens with numbers and
   ends on a list of unestablished claims. The rewrite should restore the problem-first
   structure of the reviewed abstract with the current evidence.
5. The reviewed paper had a 25-page-plus appendix with Tables 24-27 as a claims index; the
   current main text is ten pages. Reviewers' page references (R1 "p. 3", "p. 29") refer to the
   reviewed layout.
