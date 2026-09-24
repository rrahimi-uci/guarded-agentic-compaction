# OpenReview metadata for the ICLR 2027 submission (forum `DF0JaS58gr`)

Paste these fields verbatim. The abstract below is the rendered text of
`paper/iclr/sections/abstract.tex` at the final-review head (branch `paper/iclr-final-deep-review`); if the source changes, regenerate
with `pdftotext -f 1 -l 1 paper/iclr/build/main.pdf -` and re-check word for word.

## Title

From Traces to Guarded Programs: Evidence-Gated Compilation of Recurrent Agent Workflows

## TL;DR

Compile recurrent read-only agent prefixes into guarded programs only when provenance, declared effects, position, induced contracts, and an exact finite-sample bound admit them; otherwise retire or fall back to the unchanged agent.

## Abstract

Tool-using agents often invoke a model at every step, even along recurrent read-only paths. Replacing repeated reasoning with deterministic execution could reduce inference cost, but recurrence alone does not make substitution safe: tool arguments may depend on prior observations, apparently read-only operations may hide effects, and replaying the same calls may still alter the final answer. Recurrence identifies an optimization opportunity, not permission to remove reasoning.

We introduce guarded agentic compaction (GAC), an evidence-gated approach that compiles recurrent execution paths into deterministic programs only when substitution is justified. GAC compiles initial read-only prefixes only: it grounds tool arguments in observable state, treats writes, approvals, handoffs, and unknown effects as hard barriers, protects compiled execution with input, output, and environment guards, and admits specialization only when finite-sample evidence satisfies configured risk and confidence requirements. Otherwise, it retains the largest justified prefix when possible or falls back to the unchanged agent. Admission certificates are exact finite-sample bounds under i.i.d. calibration groups, compiler-wide where one candidate reached calibration and per-candidate where two did (two of three primary families, whose corrected bound is 0.057).

Across three live GitHub workflow families and 90 unseen test cases, GAC satisfies 90/90 exact task contracts and the unchanged agent 89/90, a difference of one stochastic baseline miss, while reducing model requests by 66.6%, tokens by 63.1%, latency by 64.2%, and estimated cost by 58.7%. A time-forward evaluation across five frozen public repositories specializes four and refuses one. On four public trace benchmarks, NESTFUL, API-Bank, and BFCL v4 contain recurrent, replayable traces but insufficient qualifying evidence to satisfy GAC's default 0.05 risk bound at the required confidence, whereas AppWorld provides sufficient evidence for admission. On a second model family and a second provider, the unchanged pipeline re-derives the same artifacts from each model's own traces on two of the three families and refuses the third.

GAC reframes agent optimization as evidence-gated specialization: compile only what is justified, dispatch only when runtime conditions remain valid, and preserve model reasoning everywhere else.

## Keywords

tool-using agents; agent workflow compilation; trace-derived specialization; provenance; effect systems; selective prediction; finite-sample risk control; conformal admission; program synthesis; guarded execution

## Consistency rule

The abstract, TL;DR, §8, and the certificate sentences of §3, §5.1, §7, Appendix A, and Appendix C must all use the same certificate level. At the PR #41 head this is Track B (per-candidate for PR-outcome and backlog routing). If the pre-registered multiplicity repair (`paper/supplementary/multiplicity-repair-protocol.md`) admits both families, switch every surface to Track A in one commit (`improve-iclr.md` §5) and repaste the abstract here.
