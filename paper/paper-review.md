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
The newest study closes two previously explicit comparator gaps on six additional fresh
records: an independently authored guarded pre-model program receives the same execution
position as GCS, and official GEPA 0.1.4 optimizes the residual prompt under a fixed budget.
The current revision also implements all ten requested benchmark dispositions. API-Bank
becomes a second compiler substrate; BFCL executes its official checker; ToolSandbox,
maintained tau, and BrowseComp receive bounded real-provider runs; and ToolBench,
AgentBench, GAIA, and SWE-bench retain explicit prerequisite gates.

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
10. The follow-up is unusually honest about negative evidence: GCS ties the fair manual
    program on requests, interfaces, input tokens, and 6/6 exact quality; GEPA retains its
    seed after 14 real task evaluations and three real reflections, with its 59-request
    optimization overhead excluded from deployment metrics.
11. The all-source benchmark audit is methodologically strong: it normalizes 5,419 tasks
    and 17,836 reference actions without pooling unlike substrates, reports every gate,
    and reproduces the central refusal result on API-Bank (48 candidates, two synthesized
    families, two held-out abstentions, no admitted artifact).

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
4. **The best manual runtime comparator is now tied, not beaten.** The provider-visible
   macro preserves 30/30 quality and beats partial GAC; GCS later beats that measured macro
   only by running earlier. The fair follow-up gives a separate hand-authored program the
   same pre-model position. Both pass 6/6 with one request, one interface, and identical
   input tokens; cost and latency differences are non-significant. The remaining value
   proposition is automatic discovery, evidence, invalidation, and admission, but manual
   construction/review effort was not measured.
5. **Paired causal scope remains narrow despite wider interoperability.** Thirty records
   from one extractive GitHub task and one model do not establish performance on branching,
   stateful, multi-agent, browser, or write-bearing workflows. The ten-benchmark extension
   proves adapters, official-path compatibility, bypasses, and a second compiler refusal;
   it does not create paired baseline-versus-GAC outcomes on those domains. The
   vulnerability/HMDA pools remain provider-free and SEC remains source-gated.
6. **Only one bounded learned optimizer has run.** Official GEPA is now a real same-task
   comparator, but its 4/2 optimization split, 14 task evaluations, three proposals, and
   six deployment cases are intentionally small. AWO, AWM, plan caching, EvoC2F, Agent
   JIT, and FlowCompile remain literature comparators only.
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

The artifact now evaluates unchanged, GEPA-only, GCS, GCS+GEPA, and manual pre-model
conditions on a fresh cohort. GEPA proposes three alternatives but retains its seed, so
the nominal combined arm is a counterbalanced GCS replication rather than evidence of
synergy. This is a valid bounded negative result, not evidence that GEPA fails generally:
all optimization examples are exact, the validation set has only two records, and no
candidate can improve a request count fixed by the unchanged interface.

## Required experiments for a stronger submission

1. A powered, preregistered multi-domain study with a predeclared non-inferiority margin,
   source-grounded and blinded semantic quality, and repository/time clustering.
2. Prospectively evaluate the newly implemented continuation admission and checked
   deterministic renderer; report separate calibration, latency, and fallback cost.
3. Natural negative, drift, permission, partial-failure, and out-of-domain cohorts that
   yield a non-degenerate post-selection risk--coverage curve.
4. Expand the same-task fair-placement result to a powered multi-family study with
   unchanged, provider-visible macro, pre-model manual program, GCS, cache-only, GAC, and
   at least one executable workflow-learning system under identical models, records,
   cache policy, and temporal ordering.
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
does not remove the major-revision recommendation. The new fair-placement result resolves
the earlier missing-comparator criticism and appropriately narrows the claim: GCS is as
structurally efficient as the manual program on six cases, not better. The bounded GEPA
run removes the claim that no live learned optimizer exists, but is too small to establish
learned-baseline superiority or complementarity.
The ten-benchmark extension removes the narrower criticism that benchmark selection was
name-only or NESTFUL-specific. Its API-Bank refusal is scientifically informative and its
gated rows are honestly handled. It still does not remove the main breadth criticism,
because BFCL gold checking, ToolSandbox/tau simulation, BrowseComp hosted search, and
task-only adapters are not paired compiler interventions. This is strong artifact and
interoperability evidence, not state-of-the-art performance evidence.
