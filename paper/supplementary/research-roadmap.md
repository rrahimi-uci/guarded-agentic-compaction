# Prioritized research and engineering roadmap

## P0 — strengthen the current scientific claim

1. **Multi-domain preregistered evaluation.** Add at least three real-record domains with
   100+ sealed pairs each, predeclare task-quality non-inferiority margins, and freeze all
   selection rules before testing. Expected benefit: substantially tighter quality and
   external-validity evidence. Trade-off: provider and annotation cost.
2. **End-to-end continuation admission.** Separate compiled-program violations from
   downstream answer violations and compare a calibrated continuation guard with a
   deterministic checked renderer. Benefit: directly addresses the observed 45/45 replay
   passes alongside a compiler-only factual miss. Trade-off: semantic labels and larger
   held-out cohorts are required.
3. **Closest implemented baselines.** Compare unchanged agent, hand-written composite
   tool, AWO-style frequent meta-tool, LLMCompiler-style scheduling, and plan caching on
   identical tasks/budgets. Benefit: defensible state-of-the-art positioning. Trade-off:
   careful semantic alignment and engineering effort.
4. **Generalize the implemented portfolio pilot.** The current exact-risk selector chooses
   a reviewed macro on one real-record workflow family and preserves 12/12 fresh contracts.
   Next compare baseline, cache, GAC, and reviewed macro recommendations across multiple
   families, including engineering effort, maintenance, amortization, and time-forward
   drift. Benefit: tests selection rather than merely confirming an already stronger macro.
   Trade-off: construction and developer effort require a reproducible measurement protocol.
5. **Global artifact risk control.** Allocate error budget across candidate discovery,
   threshold selection, and multiple deployed artifacts. Benefit: turns per-artifact
   certificates into a deployment-level statement. Trade-off: more conservative coverage
   or larger calibration demand.

## P1 — expand safe execution capability

6. **Explicit execution-position state.** Add a region-position key, continuation token,
   and conformance tests so suffix regions can dispatch without reordering. Benefit: much
   larger optimization surface. Trade-off: tighter coupling to runner state semantics.
7. **Transactional idempotent writes.** Introduce effect-specific prepare/verify/commit,
   approval barriers, idempotency keys, and compensation testing. Benefit: realistic
   operational workflows. Trade-off: substantially larger trusted computing base.
8. **Parallel program scheduler.** Derive a dependency DAG from provenance and execute
   independent read calls concurrently with cancellation/budget propagation. Benefit:
   composes decision reduction with scheduling latency gains. Trade-off: provider
   concurrency effects and harder staging semantics.
9. **Counterexample-guided synthesis.** Cache failed bindings and use replay/perturbation
   counterexamples to refine an e-graph or enumerative search inside the same closed
   operator semantics. Benefit: higher synthesis coverage with auditability. Trade-off:
   compile time and proof/debug complexity.

## P2 — generalized agent optimization library

10. **Cost-aware Pareto artifact sets.** Learn multiple artifacts spanning quality,
   latency, token, and dollar objectives, then select under deployment constraints.
   Benefit: adapts to workload economics. Trade-off: selection multiplicity must enter the
   risk budget.
11. **Prompt/tool/memory compaction passes.** Implement pass contracts that propose prompt
   blocks, tool descriptions, memory summaries, and agent compositions, but route every
   proposal through grouped evaluation and lifecycle gates. Benefit: broader optimization
   coverage. Trade-off: semantic quality labels are harder than structural replay.
12. **GEPA-style residual prompt evolution.** Evaluate unchanged, GEPA-only, GAC-only,
    and GAC+GEPA conditions under the same tasks and rollout budget. Benefit: tests whether
    reflective prompt evolution repairs or improves the model decisions left after safe
    region compilation. Trade-off: a factorial study is more expensive, and transformation
    effects must be isolated before composition is interpreted.
13. **Trace-driven model routing.** Combine TGWS entry routes with RouteLLM-style learned
    selection and fallback. Benefit: cost reduction on non-compilable episodes. Trade-off:
    model availability and preference-distribution drift.
14. **Other-framework adapters.** Add LangGraph and AutoGen capture/runtime adapters that
    preserve the Episode contract and effect semantics. Benefit: ecosystem reach.
    Trade-off: framework-specific continuation/handoff semantics.

## P3 — operational hardening

15. Public-key artifact signatures and supply-chain attestations.
16. Atomic registry generations, migrations, and disaster-recovery tests.
17. Privacy-preserving trace redaction with field-level lineage retained.
18. Drift dashboards for coverage, verifier failures, risk upper bounds, and economics.
19. Python 3.11–3.14 CI, type checking, linting, fuzzing, mutation gates, and SBOMs.

Each roadmap item must preserve the current fail-closed invariant: a new proposer may
increase the candidate set, but cannot silently weaken effect, provenance, compatibility,
calibration, staging, verifier, or fallback requirements.
