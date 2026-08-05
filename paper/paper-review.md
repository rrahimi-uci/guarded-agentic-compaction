# Paper review: adversarial assessment

## Summary and recommendation

The submission presents guarded agentic compaction (GAC), a trace-to-program method for
selectively replacing recurrent read-only tool prefixes. Its core contribution combines
value provenance, effect and position barriers, bounded synthesis, runtime verification,
abstention, and per-candidate finite-sample threshold admission. The revised artifact adds a real-provider study
whose prompt names neither tools nor order, an exact-source factual oracle, and a live
hand-written composite-tool baseline.
The latest extension adds guarded composite synthesis (GCS): a bounded, provenance-
preserving interface over an admitted program, plus a fresh 12-pair paid comparison.
The newest study closes two previously explicit comparator gaps on six additional fresh
records: an independently authored guarded pre-model program receives the same execution
position as GCS, and official GEPA 0.1.4 optimizes the residual prompt under a fixed budget.
The current revision adds two distinct real-record workflow families: pull-request outcome
audit and backlog-attention routing. Together with issue-type routing, the primary result
now covers 90 held-out public records, three tool vocabularies, and three exact graders.
The broader ten-source work remains a supplementary interoperability ledger; NESTFUL and
API-Bank are the only external corpora used as compiler evidence.

**Recommendation: borderline/major revision for a top-tier main track; strong artifact
candidate (86/100 scientific readiness, 97/100 artifact engineering).**

An audit of the sealed gates found a reporting defect this review had missed: three admitted
artifacts were calibrated at `alpha=.10` while the manuscript described a single registered
5% bound, and the guarded-composite artifact behind every GCS and comparator result would
have retired at 5%. That is now disclosed per artifact in a generated register
(`paper/results/admission_register.json`, Table 2), stated at each point of use, and
enforced by the validator. The same audit found the paper's blanket "the gate never
discriminates" claim to be false for one artifact — the GCS gate admits 88 of 92 groups —
and that the two non-zero score weights in the expanded replication are numerically
identical, i.e. collinear rather than informative. The scientific-readiness score is lower
than the previous revision's despite these corrections being improvements: the disclosure
narrows what the GCS and comparator sections license.
The implementation and resource intervention are credible. The natural-order study also
records a compiler-only factual failure, showing that clean tool-program replay does not
certify the downstream answer. The remaining evidence is too small and narrow for
non-inferiority, broad workflow optimization, or state-of-the-art claims.

The strongest revision is conceptual: the paper no longer presents generic agent
compilation as the novelty. Its defensible contribution is an *admissibility argument for
trace-derived specialization*: a candidate must satisfy value provenance, effects,
permissions, runtime position, readable synthesis, empirical contracts, and finite-sample
admission, or the system retains the original agent. This makes refusal evidence part of
the scientific result rather than an implementation failure.

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
11. The three-family study is a material breadth improvement: compiled programs reach
    90/90 exact contracts versus 89/90 baseline and reduce requests 50.0--75.0%, tokens
    39.5--81.4%, observed latency 51.7--73.0%, and estimated cost 32.0--75.3% per family.
    Manual programs also reach 90/90, preventing an unsupported dominance claim.
12. An archived paid PR pilot led to an implemented algorithmic correction: opaque IDs
    now retain type and provenance without an empirical numeric range that rejects unseen
    but schema-valid values.
13. The supplementary all-source audit remains methodologically strong: it reports every
    gate without pooling unlike substrates and reproduces refusal on API-Bank.
14. The revised abstract and result opening expose the strongest contrary evidence early:
    a hand-written macro is cheaper than partial GAC, and fair pre-model manual code ties
    GCS. This substantially improves credibility and focuses the contribution on automatic
    evidence and lifecycle controls.

## Major concerns

1. **End-to-end non-inferiority is not established.** Zero failures in 30 for the partial
   artifact still gives a one-sided 95% upper bound of 9.5%; the aggressive artifact's one
   failure in 18 gives 23.8%. McNemar `p=1` is not evidence of equivalence.
2. **The gate has the wrong endpoint for a preservation claim.** It verifies the compiled
   tool program, not the model continuation. The coexistence of 45/45 clean replays and a
   factual output miss proves the distinction.
3. **Admission does not discriminate, and the one exception is instructive.** The earlier
   and expanded gates behave all-or-none at thresholds 0.14 and 0.11, and the expanded
   run's two non-zero weights are numerically identical, so a second non-zero weight is not
   progress. The GCS gate is the only one that refuses anything (88/92, coverage 0.957) —
   and refusing four groups is exactly why its bound is 0.052 rather than 0.0498, i.e. why
   it misses the registered 5%. Coverage and risk trade off as the finite-sample
   calculation requires, but a mechanism visible at four refusals is not a frontier.
4. **Three selective-risk levels are in play.** `alpha=.05` licenses the three primary
   families and the prescribed-prefix ablation; `alpha=.10` licenses the earlier three-read
   artifact and every GCS/comparator number; the portfolio pilot uses 15%. This is now
   disclosed and machine-checked, but it means the GCS contribution rests on a weaker
   guarantee than the headline result and cannot be pooled with it.
5. **The exact theorem is per candidate, not compiler-wide.** For a candidate frozen
   before calibration, conditional binomial inversion plus a union bound over the 11
   thresholds is valid. The compiler can calibrate several candidate families on the same
   groups but does not allocate `delta` across that search. Two-candidate Bonferroni control
   would require 106 zero-violation groups rather than 92. The reported bounds must
   therefore remain per-candidate conditional certificates until candidate selection is
   frozen or multiplicity-corrected.
6. **Token reduction is not cost reduction.** Provider-free cache accounting shows the
   hand-written macro using 30.9% fewer tokens for only 8.0% less money, because it retains
   no cache reads at all. The two newer families are cache-cold throughout, so part of the
   32.0--75.3% cost range reflects cache warmth rather than compiled depth.
7. **Amortization is unfavourable for shallow artifacts.** Provider-side break-even is 411
   episodes for the two-read issue-type program against 182 and 181 for the deeper two, so
   the weakest artifact needs more than three times its own discovery cohort to repay
   provider spend alone.
8. **The best manual runtime comparator is now tied, not beaten.** The provider-visible
   macro preserves 30/30 quality and beats partial GAC; GCS later beats that measured macro
   only by running earlier. The fair follow-up gives a separate hand-authored program the
   same pre-model position. Both pass 6/6 with one request, one interface, and identical
   input tokens; cost and latency differences are non-significant. The remaining value
   proposition is automatic discovery, evidence, invalidation, and admission, but manual
   construction/review effort was not measured.
9. **Transfer is across workflow families, not repositories or time.** The new result has
   90 held-out records and distinct tasks/tools, but all records come from one revision-
   pinned repository snapshot and one model. It does not establish performance under
   temporal drift, another organization, branching, stateful, multi-agent, browser, or
   write-bearing workflows. The vulnerability/HMDA pools remain provider-free and SEC
   remains source-gated.
10. **Only one bounded learned optimizer has run.** Official GEPA is now a real same-task
   comparator, but its 4/2 optimization split, 14 task evaluations, three proposals, and
   six deployment cases are intentionally small. AWO, AWM, plan caching, EvoC2F, Agent
   JIT, and FlowCompile remain literature comparators only.
10. **The oracle revision, though well audited, reveals protocol fragility.** Correcting
   the excerpt rule changes which discovery record would enter the split, while the
   evaluated artifact remains the one built under the original online oracle.
11. **Fallback and guardrail semantics remain integration boundaries.** Exact baseline
   restoration requires staging ownership, and deleted model boundaries may delete
   guardrail evaluations.
12. **The paper remains long for a main-track submission.** The shared long-form article is
   appropriate for archival review, but a venue submission should move benchmark-by-
   benchmark operational detail and secondary studies to supplementary material while
   preserving the negative results in the main text.

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
1a. Recalibrate the guarded-composite family at the registered `alpha=.05`, or state
   permanently that the interface contribution is a 10%-risk result. The gate rejects four
   of 92 groups, so reaching 92 admitted groups needs a larger calibration cohort, not a
   looser threshold.
1b. Refit the gate score on a development set containing genuine unproductive outcomes --
   the archived suffix pilot at 16.7% contract validity and the identifier-hull PR pilot are
   already retained and provider-free -- and publish a risk--coverage curve at several
   `alpha`, or replace the logistic score with an explicit one-class nonconformity measure.
1c. Replicate the primary families under a controlled cache policy so the 32.0--75.3% cost
   range is not partly an artifact of which baselines happened to run cache-warm.
2. Prospectively evaluate the newly implemented continuation admission and checked
   deterministic renderer; report separate calibration, latency, and fallback cost.
3. Natural negative, drift, permission, partial-failure, and out-of-domain cohorts that
   yield a non-degenerate post-selection risk--coverage curve.
4. Expand the fair-placement result to a powered cross-repository, time-forward study with
   unchanged, provider-visible macro, pre-model manual program, GCS, cache-only, GAC, and
   at least one executable workflow-learning system under identical models, records,
   cache policy, and temporal ordering.
5. Guardrail replay/barriers, retry and failure tests, signed immutable artifacts,
   staged writes, canary evidence, and rollback drills before production claims.

## Final assessment

The revised paper makes a defensible contribution as a guarded compiler and a study of
where trace evidence fails to justify behavioral preservation. It is substantially
stronger than the prescribed-prefix version and is a credible research artifact. The
appropriate main-track posture remains borderline/major revision until quality,
selectivity, and cross-repository breadth are established. The portfolio pilot deserves limited mechanism credit
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
Two audit findings now bound the reading of the newer sections. Every GCS and comparator
number is licensed at `alpha=.10` rather than the registered 5%, and the artifact behind them
would have retired at 5%; the disclosure is complete and machine-checked, but it moves the
interface contribution to a weaker evidence tier than the headline families. Separately,
cache accounting shows that the token comparison that motivated GCS overstates the macro's
advantage in dollars by roughly four-fold, which strengthens the paper's own argument that a
workflow optimizer must price prefix reuse and simultaneously weakens the token-based
framing used to motivate the work.
The three-family extension removes the earlier criticism that the live compiler result
covered only one decision and one tool vocabulary. It does not remove the repository/time
breadth criticism, and the manual tie keeps the runtime claim narrow. API-Bank refusal is
scientifically informative; BFCL checking, ToolSandbox/tau simulation, BrowseComp search,
and task-only adapters remain supplementary interoperability evidence rather than optimizer
baselines.

## Reviewer scorecard

| Dimension | Score | Rationale |
|:---|---:|:---|
| Technical depth | 9.5/10 | unusually complete trace, compiler, admission, runtime, and lifecycle stack |
| Novelty | 8.9/10 | strong composition and admissibility framing; individual mechanisms have precedent |
| Clarity and writing | 9.0/10 | claim spine is crisp and now risk-scoped per artifact; 22 two-column pages over seven studies is past main-track length |
| Experimental rigor | 9.0/10 | three paired workflow families, verified pairwise-disjoint records, archived failures; one repository snapshot, and the core admission mechanism is still undemonstrated |
| Reproducibility | 9.9/10 | retained rows, hashes, commands, independent recomputation, generated risk and cache registers, and negative evidence |
| Presentation | 9.2/10 | shared-source paper, four data figures now used rather than one, evidence-led website; the decks trail the generator and say so |
| Scientific readiness | 8.6/10 | credible borderline/major-revision paper; three risk levels, a shallow-artifact break-even of 411 episodes, and no cross-repository result |
