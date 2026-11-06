# OpenReview metadata for the ICLR 2027 submission (forum `DF0JaS58gr`)

Paste these fields verbatim. The abstract below is the rendered text of
`paper/iclr/sections/abstract.tex` at the population-audit revision (2026-11-06);
if the source changes, regenerate
with `pdftotext -f 1 -l 1 paper/iclr/build/main.pdf -` and re-check word for word.

## Title

From Traces to Guarded Programs: Evidence-Gated Compilation of Recurrent Agent Workflows

## TL;DR

Discover and execute grounded read-only agent prefixes with explicit admission assumptions and refusal conditions; measure efficiency, final-task quality, and the limits of each certificate separately.

## Abstract

Guarded agentic compaction (GAC) discovers and executes grounded initial read-only prefixes, with explicit admission assumptions and refusal conditions, and leaves the rest of the agent unchanged. On three GitHub workflows the compiled agent satisfies 90/90 held-out contracts against 89/90 for the unchanged agent with 66.6% fewer model requests, and a separately frozen comparison with adapted offline Agent Workflow Memory over three workflows, two models, and 1,362 fresh records (8,172 attempted episodes) cuts estimated deployment cost by 36.9–79.1% and requests by 50–75%, with five of six cells meeting a preregistered five-point accuracy noninferiority margin under multiplicity correction. On BIRD, a schema-first SQL opening compiles on 26/31 databases with 45–50% fewer requests and no detected accuracy loss, and a post-cutoff cohort of 132 pull requests shows no end-to-end error (upper bound 1.73% at 90% confidence).

GAC combines grounded tool arguments, declared read-only effects, induced contracts, and a finite-sample admission test; unsupported candidates retire and retain the agent. Question-specific BIRD openings and all NESTFUL, API-Bank, and BFCL families retire, while AppWorld's admitted program is rarely eligible on ReAct trajectories. Statistical guarantees require a fixed candidate-selection procedure and independent calibration groups matching the deployment population. Most reported bounds concern replay rather than final answers: primary discovery filtering prevents certification of unfiltered deployment, and two primary families miss the selection-adjusted 5% target. The evidence supports bounded prefix compilation; universal accuracy preservation and learned-gate benefit remain unestablished.

## Keywords

tool-using agents; agent workflow compilation; trace-derived specialization; provenance; effect systems; selective prediction; finite-sample risk control; conformal admission; program synthesis; guarded execution

## Consistency rule

This is prepared text, not a record of an OpenReview update. Keep it synchronized
with `sections/abstract.tex`. Primary PR-outcome and backlog certificates remain
per-candidate; the proposed multiplicity repair was a NO-GO. The post-cutoff
single-rule certificate concerns absolute end-to-end error in its selected
population. Do not promote replay certificates to final-answer guarantees.
