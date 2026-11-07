# OpenReview metadata for the ICLR 2027 submission (forum `DF0JaS58gr`)

Paste these fields verbatim. The abstract below is the rendered text of
`paper/iclr/sections/abstract.tex` at the Strategy B revision (2026-11-07);
if the source changes, regenerate
with `pdftotext -f 1 -l 1 paper/iclr/build/main.pdf -` and re-check word for word.

## Title

From Traces to Guarded Programs: Evidence-Gated Compilation of Recurrent Agent Workflows

## TL;DR

Discover and execute grounded read-only agent prefixes with explicit admission assumptions and refusal conditions; measure efficiency, final-task quality, and the limits of each certificate separately.

## Abstract

Tool-using agents pay for a model decision at every tool boundary, but recurrence alone is not permission to remove it. Guarded agentic compaction (GAC) compiles an agent's opening read-only calls into a deterministic program only when every argument is grounded in observed state, every effect is declared read-only, and the program starts at the first step; otherwise it refuses, and admits one only when enough independent calibration examples support a finite-sample error bound. On three GitHub workflows the compiled agent satisfies 90/90 held-out task contracts against 89/90 for the unchanged agent, with 66.6% fewer model requests. Against adapted offline Agent Workflow Memory on 1,362 fresh records, five of six workflow and model cells meet a five-point accuracy noninferiority margin at 36.9-79.1% lower estimated cost. On BIRD text-to-SQL, a schema-first opening compiles on 26/31 databases; NESTFUL, API-Bank and BFCL tool-trace candidates are refused for insufficient calibration support; AppWorld's admitted program is rarely eligible for ReAct-style agents. Most bounds cover replay on selected populations; one covers final answers: no failure on 132 pull requests opened after the snapshot (90% upper bound 0.0173). A later study samples one pull request per author before any outcome filter and grades final task contracts: 3 misses in 760 groups across four repositories, each admitted by its own frozen candidate (bounds 0.023-0.042, registered grid). Replay bounds do not cover unfiltered deployment, two primary families miss the selection-adjusted 5% target, and we claim no benefit on adaptive tasks or from a learned dispatch gate.

GAC combines grounded tool arguments, declared read-only effects, induced contracts, and a finite-sample admission test; unsupported candidates retire and retain the agent. Question-specific BIRD openings and all NESTFUL, API-Bank, and BFCL families retire, while AppWorld's admitted program is rarely eligible on ReAct trajectories. Statistical guarantees require a fixed candidate-selection procedure and independent calibration groups matching the deployment population. Most reported bounds concern replay rather than final answers: primary discovery filtering prevents certification of unfiltered deployment, and two primary families miss the selection-adjusted 5% target. The evidence supports bounded prefix compilation; universal accuracy preservation and learned-gate benefit remain unestablished.

## Keywords

tool-using agents; agent workflow compilation; trace-derived specialization; provenance; effect systems; selective prediction; finite-sample risk control; conformal admission; program synthesis; guarded execution

## Consistency rule

This is prepared text, not a record of an OpenReview update. Keep it synchronized
with `sections/abstract.tex`. Primary PR-outcome and backlog certificates remain
per-candidate; the proposed multiplicity repair was a NO-GO. The post-cutoff
single-rule certificate concerns absolute end-to-end error in its selected
population. Do not promote replay certificates to final-answer guarantees.
