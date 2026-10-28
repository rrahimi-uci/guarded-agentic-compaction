# OpenReview metadata for the ICLR 2027 submission (forum `DF0JaS58gr`)

Paste these fields verbatim. The abstract below is the rendered text of
`paper/iclr/sections/abstract.tex` at the lead-with-evidence revision (2026-10-28);
if the source changes, regenerate
with `pdftotext -f 1 -l 1 paper/iclr/build/main.pdf -` and re-check word for word.

## Title

From Traces to Guarded Programs: Evidence-Gated Compilation of Recurrent Agent Workflows

## TL;DR

Compile recurrent read-only agent prefixes into guarded programs only when provenance, declared effects, position, induced contracts, and an exact finite-sample bound admit them; otherwise retire or fall back to the unchanged agent.

## Abstract

Guarded agentic compaction (GAC) compiles the recurrent initial read-only prefix of an agent workflow into a deterministic program and leaves the rest of the agent unchanged. On three GitHub workflows the compiled agent satisfies 90/90 held-out contracts against 89/90 for the unchanged agent with 66.6% fewer model requests, and a separately frozen comparison with adapted offline Agent Workflow Memory over three workflows, two models, and 1,362 fresh records (8,172 attempted episodes) cuts estimated deployment cost by 36.9–79.1% and requests by 50–75%, with five of six cells meeting a preregistered five-point accuracy noninferiority margin under multiplicity correction. On BIRD, a schema-first SQL opening compiles on 26/31 databases with 45–50% fewer requests and no detected accuracy loss, and a post-cutoff cohort of 132 pull requests shows no end-to-end error (upper bound 1.73% at 90% confidence).

GAC admits a program only when every tool argument is grounded in the entry state, a prior result, or an invariant literal; every tool has a declared read-only effect; induced input/output contracts hold; and an exact finite-sample test under independent-group assumptions bounds the dispatch risk. Otherwise it retires the candidate and keeps the agent, which is what happens to question-specific table selection on BIRD, to every NESTFUL, API-Bank, and BFCL family (too little calibration support), and, at dispatch time, to AppWorld's admitted program on nearly all ReAct and plan-and-execute runs. The evidence supports bounded compilation of recurrent prefixes, not universal accuracy preservation or learned-gate benefit: most certificates concern replay rather than final answers, the statistical stage adds no measured runtime benefit on admitted candidates, one second-model cell is inconclusive, and independence beyond the evaluated workloads is assumed.

## Keywords

tool-using agents; agent workflow compilation; trace-derived specialization; provenance; effect systems; selective prediction; finite-sample risk control; conformal admission; program synthesis; guarded execution

## Consistency rule

This is prepared text, not a record of an OpenReview update. Keep it synchronized
with `sections/abstract.tex`. Primary PR-outcome and backlog certificates remain
per-candidate; the proposed multiplicity repair was a NO-GO. The post-cutoff
single-rule certificate concerns absolute end-to-end error in its selected
population. Do not promote replay certificates to final-answer guarantees.
