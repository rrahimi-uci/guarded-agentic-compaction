# Paper review: adversarial assessment

## Summary and recommendation

The submission presents guarded agentic compaction (GAC), a trace-to-program method for
selectively replacing recurrent read-only tool prefixes. Its core contribution combines
value provenance, effect and position barriers, bounded synthesis, runtime verification,
abstention, and finite-sample admission. The revised artifact adds a real-provider study
whose prompt names neither tools nor order, an exact-source factual oracle, and a live
hand-written composite-tool baseline.
The latest extension adds guarded composite synthesis (GCS): a bounded, provenance-
preserving interface over an admitted program, plus a fresh 12-pair paid comparison.

**Recommendation: major revision for a top-tier main track; strong artifact candidate.**
The implementation and resource intervention are credible. The natural-order study also
records a compiler-only factual failure, showing that clean tool-program replay does not
certify the downstream answer. The remaining evidence is too small and narrow for
non-inferiority, broad workflow optimization, or state-of-the-art claims.

## Main strengths

1. A framework-neutral typed Episode IR separates capture adapters from compiler logic.
2. Provenance, effects, compatibility, position, staging, and fallback boundaries are
   explicit rather than left to prompt convention.
3. NESTFUL supplies a useful negative result: recurrence is insufficient for the stated
   bound at observed support, so all families retire.
4. The expanded follow-up uses 132 discovery records, 30 balanced primary pairs, ten
   repeats, live provider calls, free tool order, source-grounded grading, and all six
   condition orders.
5. Groundability changes the emitted depth: recurrence proposes three reads, synthesis
   rejects the ungroundable third argument, and the safe two-read artifact passes 30/30.
6. The live macro makes the practical trade-off visible: it also passes 30/30 and matches
   request reduction while using fewer tools, tokens, and dollars than partial GAC.
7. The paper distinguishes compile-or-retire GAC from the implemented exact-risk
   portfolio, which recommends the measured macro for review and prospectively passes
   12/12 fresh contracts while reducing every measured resource.
8. Raw evidence, regrade provenance, scripts, checksums, exact commands, and executable
   claim checks make the artifact unusually auditable.
9. GCS directly answers the macro criticism rather than evading it: on 12 disjoint fresh
   issues both GCS and the provider-visible macro pass 12/12, while GCS uses one instead of
   two provider requests and lowers tokens, observed latency, and estimated cost.

## Major concerns

1. **End-to-end non-inferiority is not established.** Zero failures in 30 for the partial
   artifact still gives a one-sided 95% upper bound of 9.5%; the aggressive artifact's one
   failure in 18 gives 23.8%. McNemar `p=1` is not evidence of equivalence.
2. **The gate has the wrong endpoint for a preservation claim.** It verifies the compiled
   tool program, not the model continuation. The coexistence of 45/45 clean replays and a
   factual output miss proves the distinction.
3. **Admission does not discriminate.** The earlier and expanded gates behave all-or-none
   at thresholds 0.14 and 0.11. The evidence demonstrates a sample-size counter, not a
   risk--coverage frontier.
4. **The best manual comparator remains unresolved.** The provider-visible macro preserves
   30/30 quality and beats partial GAC; GCS later beats that measured macro on 12/12 fresh
   pairs by running before the first provider request. An equally pre-executed, guarded
   hand-written macro was not tested and could plausibly remove the same turn. The GCS
   result is post-study exploratory evidence, not general automatic-code superiority.
5. **Scope remains narrow.** Thirty records from one extractive GitHub task and one
   model do not establish performance on branching, stateful, multi-agent, browser, or
   write-bearing workflows. The new vulnerability/HMDA real-record pools improve the
   feasibility story, but no provider-backed multidomain condition has run and SEC remains
   source-gated, so they cannot yet earn empirical breadth credit.
6. **No live learned-workflow comparator exists.** AWO, AWM, plan caching, EvoC2F, and
   Agent JIT are literature comparators only. GEPA is adjacent because it evolves residual
   prompts rather than compiling away model boundaries.
7. **The oracle revision, though well audited, reveals protocol fragility.** Correcting
   the excerpt rule changes which discovery record would enter the split, while the
   evaluated artifact remains the one built under the original online oracle.
8. **Fallback and guardrail semantics remain integration boundaries.** Exact baseline
   restoration requires staging ownership, and deleted model boundaries may delete
   guardrail evaluations.

## GEPA positioning

[GEPA](https://arxiv.org/abs/2507.19457) is directly relevant to trace-driven agent
optimization. It reflects over execution/evaluation trajectories and uses Pareto-guided
prompt evolution to improve held-out task quality with high rollout efficiency. GAC
instead changes which model boundaries exist and emits a guarded deterministic program.
The correct novelty claim is therefore guarded recurrent-region compilation, not generic
trace optimization.

A valuable follow-up would evaluate unchanged, GEPA-only, GAC-only, and GAC+GEPA
conditions. The composition could optimize residual model decisions after justified
regions are compiled, but the effects must first be measured separately.

## Required experiments for a stronger submission

1. A powered, preregistered multi-domain study with a predeclared non-inferiority margin,
   source-grounded and blinded semantic quality, and repository/time clustering.
2. Prospectively evaluate the newly implemented continuation admission and checked
   deterministic renderer; report separate calibration, latency, and fallback cost.
3. Natural negative, drift, permission, partial-failure, and out-of-domain cohorts that
   yield a non-degenerate post-selection risk--coverage curve.
4. Same-task unchanged, provider-visible macro, pre-model manual macro, GCS, cache-only,
   GAC, and learned-workflow conditions under identical models, records, prompts, cache
   policy, and temporal ordering.
5. Guardrail replay/barriers, retry and failure tests, signed immutable artifacts,
   staged writes, canary evidence, and rollback drills before production claims.

## Final assessment

The revised paper makes a defensible contribution as a guarded compiler and a study of
where trace evidence fails to justify behavioral preservation. It is substantially
stronger than the prescribed-prefix version and is a credible research artifact. The
appropriate main-track posture remains major revision until quality, selectivity, and
domain breadth are established. The portfolio pilot deserves limited mechanism credit
because its action was frozen before 12 fresh cases and preserved every registered
contract while reducing all measured resources. It does not establish selection value
across workflow families or drift.
GCS materially improves the engineering and scientific story by reaching observed macro
quality without surrendering the guard, but its 12-case, two-category, single-family study
does not remove the major-revision recommendation.
