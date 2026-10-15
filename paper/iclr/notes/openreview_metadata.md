# OpenReview metadata for the ICLR 2027 submission (forum `DF0JaS58gr`)

Paste these fields verbatim. The abstract below is the rendered text of
`paper/iclr/sections/abstract.tex` after the October 15 live-recovery integration;
if the source changes, regenerate
with `pdftotext -f 1 -l 1 paper/iclr/build/main.pdf -` and re-check word for word.

## Title

From Traces to Guarded Programs: Evidence-Gated Compilation of Recurrent Agent Workflows

## TL;DR

Compile recurrent read-only agent prefixes into guarded programs only when provenance, declared effects, position, induced contracts, and an exact finite-sample bound admit them; otherwise retire or fall back to the unchanged agent.

## Abstract

Tool-using agents often call a language model at every step, even when they repeat the same read-only lookups. Replacing that repeated reasoning with a fixed program could cut cost, but repetition alone does not make it safe: a tool argument may depend on an earlier result, a ``read-only'' tool may have side effects, and replaying the same calls may still change the final answer.

We introduce guarded agentic compaction (GAC), which compiles the recurring read-only opening of an agent's workflow into a deterministic program only when the evidence justifies it, and otherwise leaves the agent unchanged. GAC grounds tool arguments in inputs, prior results, or observed invariant literals, treats writes, approvals, handoffs, and unknown effects as hard stops, checks inputs and outputs at run time, and deploys a program only after enough independent examples pass a statistical test.

On three real GitHub workflows, the compiled agent had similar observed accuracy to the original agent (90 of 90 held-out tasks correct, versus 89 of 90) and never failed a task the original agent solved (one such failure in 810 held-out GitHub episodes in six specified studies), while making about two-thirds fewer model calls, finishing in about a third of the time, and costing less than half as much per task. On 132 fresh pull requests created after our data snapshot, it made no end-to-end errors, which bounds its error rate below 2% with 90% confidence for open and merged pull requests, assuming independent, identically distributed records. On BIRD, a public text-to-SQL benchmark, a live schema-first agent's opening was compiled on 26 of 31 databases and on a second model family, cutting model calls by 45–50% with no detected accuracy loss; agents choosing tables per question were refused. Two public benchmarks show no measured benefit: NESTFUL holds at most 26 examples of any workflow, against the 92 required, and on AppWorld the one admitted program fits almost no ReAct or plan-and-execute run. With a second model family and a second provider, GAC rediscovers the same programs on two of the three GitHub workflows and declines the third. We also report its limits: its main guarantee mostly confirms that enough examples were seen, the savings hold within one data snapshot, and its earlier corruption tests showed no protection. A separate live study on 72 issue groups with constructed requests finds that request-scope checks improve ordinary-response task success by 8.8 percentage points over their removal (descriptive 95% interval 3.7–13.9), while completeness checks show no clear benefit when the agent can recover missing evidence.

GAC reframes agent optimization as evidence-gated specialization: compile only what is justified, and keep the model's reasoning everywhere else.

## Keywords

tool-using agents; agent workflow compilation; trace-derived specialization; provenance; effect systems; selective prediction; finite-sample risk control; conformal admission; program synthesis; guarded execution

## Consistency rule

The abstract, TL;DR, §8, and the certificate sentences of §3, §5.1, §7, Appendix A, and Appendix C must all use the same certificate level. At the PR #41 head this is Track B (per-candidate for PR-outcome and backlog routing). If the pre-registered multiplicity repair (`paper/supplementary/multiplicity-repair-protocol.md`) admits both families, switch every surface to Track A in one commit and repaste the abstract here.
