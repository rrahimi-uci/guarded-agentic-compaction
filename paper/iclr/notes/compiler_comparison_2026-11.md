# Design-property comparison with trace-reuse systems (2026-11-07)

Source for `tables/compiler_comparison.tex` and the "Reuse, caching, and optimization of agents"
paragraph of `sections/related_work.tex`. Each claim about another system is backed by a verbatim
quote with page. "Not stated" means the paper does not say; it is never read as "absent".

Versions read: TraceCompiler arXiv 2608.02680v1; EvoC2F and Agent JIT PMLR v306 PDFs; AWM arXiv
2409.07429v1; agentic plan caching (APC) arXiv 2506.14852v2; PreAct arXiv 2606.17929 (abstract).
Page numbers are those PDFs; the bibliography cites PMLR/NeurIPS versions of AWM and APC, whose
pages may differ.

## Contrasts the paper makes (and only these)

1. **No stated finite-sample admission bound.** TraceCompiler: "Clusters below a support floor are
   set aside as 'not yet compilable'" (§3.1, p3); "the support floor is 5" (§5, p5); "a candidate
   that cannot satisfy its specification is rejected" (§3.5, p4). EvoC2F: "Skills must pass at least
   95% of nominal tests, 90% of boundary tests, and 100% of critical error mode tests to proceed";
   "Skills are admitted if ∆reg(s) ≤ 0, functional tests pass, contract verification succeeds"
   (App. F.2, p23). Agent JIT: "generates multiple code plans, validates each against tool
   specifications, and selects the minimum-cost candidate" (p1). APC: "Our system uses exact matches
   (between keywords) to minimize false positives" (§3.2, p5). PreAct: "a freshly compiled program
   enters the store only if, re-run from a clean state, an independent evaluator confirms it solved
   the task" (abstract). GAC's bound is per fixed candidate, assumes exchangeable calibration groups,
   and is a replay bound in most families; keep those qualifiers wherever the contrast appears.
2. **Open arguments left to a runtime model.** TraceCompiler: "llm_or_dynamic (genuinely semantic
   bindings, which alone justify a runtime LLM node)" (§3.4, p4). APC: a small LM "adapts the
   retrieved plan template for the current execution by incorporating context-specific information"
   (p5). Agent JIT: "compiles task descriptions directly into executable code that is free to include
   LLM calls" (abstract). TraceCompiler does have argument-level provenance: an edge is admitted
   "only if some argument of b consumes a value only a could have produced" (§3.3, p3). Do not claim
   it lacks provenance.
3. **Decline rate and versioning (TraceCompiler only).** "We do not report how often the compiler
   declines, which is the adoption-relevant rate" (§7, p11); "We have no workflow versioning,
   invalidation, or contract monitoring" (§7, p11). Do not extend to EvoC2F (semantic versioning,
   canary rollback: "triggering automatic rollback if success rate drops by more than 2% compared to
   control", App. F.3, p24) or Agent JIT ("a failed pre/postcondition marks the tool invalid", §6, p9).

## Claims the paper must not make

- "Only GAC falls back to the agent." TraceCompiler: "unmatched requests fall back to the general
  agent" (§3.5, p4). EvoC2F: "Shadow mode enables passive observation with atomic fallback" (§3.5,
  p5). PreAct "hands control back to the agent the moment something is off" (abstract). GAC's
  narrower rule: fallback only when staging proves the failed attempt clean; otherwise an incident.
- "Others ignore effect safety." EvoC2F: "unknown side-effects default to write" (§3.2, p4).

## Concessions stated in the appendix

Writes and irreversible effects (TraceCompiler money requests; EvoC2F compensation: "the compiler
generates compensation actions", §3.3, p4; Agent JIT "forward the first two emails and delete the
originals", p8); branches, loops and fan-out (TraceCompiler §3.2, p3); coverage beyond the opening
(AWM, APC, AWO meta-tools); online adaptation and learning (AWM online induction; EvoC2F "update the
planner via Direct Preference Optimization", §3.4, p5); latency scheduling (Agent JIT, EvoC2F);
output-opaque traces ("We explicitly allow traces in which arguments are recorded but tool outputs
are not", TraceCompiler §2, p2); EvoC2F's evaluated staged deployment.

## Newly cited

PreAct (2606.17929), SKILL-DISCO (2606.26669), programmatic skill induction / NSI (2605.01293),
WorkflowGen (2604.19756), WISE-Flow (2601.08158). Metadata taken from the arXiv abstract pages on
2026-11-07.
