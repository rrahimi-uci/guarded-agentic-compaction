# OpenReview metadata for the ICLR 2027 submission (forum `DF0JaS58gr`)

Paste these fields verbatim. The abstract below is the rendered text of
`paper/iclr/sections/abstract.tex` at the PAT-disposition head (branch `paper/iclr-pat-feedback-review`, 2026-10-16);
if the source changes, regenerate
with `pdftotext -f 1 -l 1 paper/iclr/build/main.pdf -` and re-check word for word.

## Title

From Traces to Guarded Programs: Evidence-Gated Compilation of Recurrent Agent Workflows

## TL;DR

Compile recurrent read-only agent prefixes into guarded programs only when provenance, declared effects, position, induced contracts, and an exact finite-sample bound admit them; otherwise retire or fall back to the unchanged agent.

## Abstract

Tool-using agents often call a language model at every step, even when they repeat the same read-only lookups. Replacing that repeated reasoning with a fixed program could cut cost, but repetition alone does not make it safe: arguments may depend on earlier results, tools may have side effects, and replaying the same calls may still change the final answer.

We introduce guarded agentic compaction (GAC), which compiles recurring read-only workflow openings into deterministic programs and otherwise leaves the agent unchanged. GAC grounds arguments in inputs, prior results, or observed invariant literals; treats writes, approvals, handoffs and unknown effects as hard stops; checks inputs and outputs; and admits programs through an exact finite-sample test under independent-group assumptions.

On three GitHub workflows, the compiled agent solves 90 of 90 held-out tasks versus 89 for the original agent, with about two-thirds fewer model calls. A separately frozen comparison with adapted offline Agent Workflow Memory spans three workflows, two models and 1,362 fresh records (8,172 attempted episodes). Estimated deployment cost falls 36.9–79.1% and model requests 50–75%. Five of six comparisons meet a preregistered five-percentage-point accuracy noninferiority margin with multiplicity correction; the smaller second-model backlog cohort is inconclusive. Only two comparisons meet a two-point margin. Statistical, support-only and deterministic gates produce identical routing and evidence on all selected cases, providing no incremental runtime gate benefit on these already admitted candidates.

On BIRD, a schema-first SQL agent's opening compiles on 26 of 31 databases, with 45–50% fewer model calls and no detected accuracy loss; question-specific table selection is refused. NESTFUL and AppWorld show no measured deployment benefit. On 132 pull requests created after the data snapshot, a re-derived program made no end-to-end error (rate below 2% at 90% confidence). A live safeguard ablation shows that request-scope checks help on constructed tasks, while the agent often recovers from incomplete evidence without a completeness check, and earlier drift tests show no protection. The evidence supports bounded compilation of recurring workflows, not learned-gate superiority, universal accuracy preservation, or cross-domain savings. Most certificates concern replay rather than final answers; task, author and time independence remain assumptions.

## Keywords

tool-using agents; agent workflow compilation; trace-derived specialization; provenance; effect systems; selective prediction; finite-sample risk control; conformal admission; program synthesis; guarded execution

## Consistency rule

The abstract, TL;DR, §8, and the certificate sentences of §3, §5.1, §7, Appendix A, and Appendix C must all use the same certificate level. At the PR #41 head this is Track B (per-candidate for PR-outcome and backlog routing). If the pre-registered multiplicity repair (`paper/supplementary/multiplicity-repair-protocol.md`) admits both families, switch every surface to Track A in one commit and repaste the abstract here.
