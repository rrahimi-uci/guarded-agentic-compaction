# Fifth-Pass Independent Review and Publication Readiness Assessment

**Manuscript:** *When Traces Are Not Enough: Guarded Compilation of Tool-Using Agents*  
**Review date:** 2026-08-03  
**Scope:** LaTeX sources and PDFs, implementation, tests, sealed raw results, manifests,
generated artifacts, supplementary material, and primary related work including
[GEPA](https://arxiv.org/abs/2507.19457) v2  
**Recommendation:** **Major revision for a top-tier main track; strong artifact candidate.**

## Executive verdict

The latest revision executes the previously sealed 30-pair replication with real provider
calls. Its task asks for exact facts without naming tools or order, uses a deterministic
source oracle, and compares the learned compiler against the unchanged agent and a
hand-written composite tool. All 132 discovery executions choose the same three-read
order; 130 pass exact factuality. Crucially, the compiler rejects the full recurring region
because the comments argument is not consistently groundable and emits only the two-read
prefix. This is direct evidence of safe partial compilation rather than recurrence mining
alone.

Across 30 balanced records and all six condition orders, baseline, partial GAC, and macro
each pass 30/30 exact factual and full task contracts. Relative to baseline, GAC reduces
requests 50.0%, tokens 39.5%, observed wall latency 51.7%, and estimated cost 32.0%.
The macro matches request reduction but saves 58.2% of tokens, 37.5% of cost, and two of
three tool calls. GAC has lower observed mean latency, but the paired interval against the
macro crosses zero. The macro is therefore the better practical default for this fixed
workflow.

The earlier aggressive three-read study remains valuable negative evidence: baseline and
macro pass 18/18, while GAC passes 17/18 after altering one Markdown-link excerpt. The
combined evidence shows preservation for the partial artifact, not an invariant of deeper
compilation.

The implementation now turns that failure boundary into an explicit API: a separate
continuation contract validates the post-region model output, then may use a deterministic
renderer or baseline only if the same contract accepts the recovery. Provider-free replay
detects the one retained failure and checked-renders it to 18/18. This is strong engineering
evidence, but it is post-hoc and does not upgrade the 17/18 live result.

This is a much stronger paper than the prior version. It still does not establish broad
workflow optimization, end-to-end admission safety, or state-of-the-art superiority. The
confirmatory test has only 30 records in one extractive GitHub task; the replay gate is
non-discriminating; its zero violations do not cover downstream model answers; the new
continuation layer has not been prospectively live-calibrated; and the
obvious hand-written macro preserves quality while eliminating more tool calls, tokens,
and cost than the partial compiler. The
strongest publishable message is therefore:

> Recurrent tool behavior can justify removing model boundaries only under explicit
> provenance, effect, position, and sampling conditions; even then, clean program replay
> does not establish the factual equivalence of the downstream agent response.

### Current assessment

- **Top-tier main-track readiness: 84/100**
- **Artifact and manuscript engineering: 95/100**

The requested 90/100 scientific target is not yet defensible. The artifact clears that
bar, but the empirical contribution needs greater power, domain breadth, selective-risk
evidence, and a learned workflow baseline.

## 1. Verified contribution

The implementation is a framework-neutral trace-to-program compiler built around a typed
Episode IR. It reconstructs value-level argument provenance, treats unknown effects,
writes, approvals, handoffs, and unsupported runtime positions as hard barriers,
synthesizes from a bounded 23-operator DSL, derives empirical contracts, calibrates a
finite-grid admission rule, and executes admitted artifacts behind staging and
postcondition verification. Abstention and retirement are first-class outputs.

Three findings are supported:

1. **Provenance is easier than certification.** On NESTFUL, the expected producer is in
   the candidate set for 5,531/5,746 dependency slots (96.3%), but only 4,636/5,746
   (80.7%) resolve uniquely. Held-out synthesis produces 24 passes, 12 abstentions, and
   zero wrong executions, yet every family retires because maximum support is 26 and the
   configured zero-violation requirement is 92 group records.
2. **Groundability limits compilation depth.** The expanded run finds the same three-read
   order in 132/132 discovery traces but rejects the full region because its third
   argument is not consistently groundable. The emitted two-read prefix halves provider
   requests on 30 fresh records and passes all 30 exact contracts.
3. **Program correctness is not answer correctness.** The earlier compiler passes all 45
   replay groups but produces one exact-source answer failure. This directly falsifies any
   interpretation of the program gate as an end-to-end behavioral certificate.

The older fixed-prefix experiment remains useful only as a controlled conformance
ablation. Its prompt prescribes the exact sequence, and its summary oracle accepts fluent
fabrication. The manuscript now labels both limitations rather than using that experiment
as the primary evidence.

## 2. Evidence map

| Evidence | What is verified | What remains outside the evidence |
|---|---|---|
| NESTFUL | Pinned public executable data; provenance, synthesis, replay, and retirement | Natural agent planning, semantic task quality, or distribution shift |
| Expanded natural-order replication | 132 discovery, 30 balanced primary pairs, ten repeats, real records/provider, exact-source oracle, live macro | Live GitHub service behavior, population equivalence, multi-domain generality |
| Earlier aggressive natural study | 80 discovery and 18 counterbalanced tests; exposes continuation-level miss | Powered degradation estimate or prospective recovery |
| Fixed-prefix GitHub ablation | Real records/provider calls; structural four-to-one intervention | Natural workflow discovery or factual summary preservation |
| Tier-3 suite | Real SDK/provider runtime over branching, pagination, write, handoff, and refusal shapes | Real-world data: records are explicitly fictional fixtures |
| Offline comparator | Reproducible simulated macro comparison | A real-provider or real-record baseline |

The two natural protocols must not be pooled. `github_natural_live/results.json` contains
the aggressive 80-discovery/18-test paid study. The separate
`github_natural_replication/results.json` contains the completed 132-discovery/30-test
paid replication whose provider-free preflight fixed the records before execution.

## 3. GEPA: directly related, but on a different optimization axis

[GEPA](https://arxiv.org/abs/2507.19457) is clearly related. It treats a compound AI
system as one or more prompted language modules under arbitrary control flow, samples
execution and evaluation trajectories, uses natural-language reflection to assign credit
and propose prompt mutations, and explores candidates through instance-wise Pareto
selection. The current arXiv v2 is an ICLR 2026 Oral. It reports an average 6% advantage
over GRPO across six tasks with up to 35x fewer rollouts, more than 10% improvement over
MIPROv2 in reported comparisons, and evolved instructions up to 9.2x shorter than
MIPROv2 prompts.

| Dimension | GEPA | GAC |
|---|---|---|
| Optimized object | Prompts of one or more LM modules | Recurrent model-mediated execution regions |
| Learning signal | Trajectories, textual feedback, task metric | Value provenance, declared effects, replay contracts, group violations |
| Search | Reflective mutation, crossover, instance-wise Pareto selection | Canonical recurrence, bounded synthesis, fixed-grid admission |
| Output | Evolved prompt configuration | Guarded deterministic program and runtime metadata |
| Primary objective | Improve held-out task quality per rollout | Remove model decisions under a registered execution contract |
| Safety boundary | Caller metric and held-out evaluation | Hard provenance/effect/position barriers plus conditional exact bound |

GEPA therefore constrains the broad novelty claim: **trace-driven agent optimization is
not new here**. GAC's narrower distinction is deletion of recurrent model boundaries
under explicit value, effect, execution-position, and finite-sample conditions. GEPA is
not a direct replacement for the macro/compilation baseline, because it neither emits the
same artifact nor targets provider-boundary elimination. It becomes a required baseline
if the project claims generic prompt optimization, agent composition optimization, or a
general optimization pipeline.

The most compelling research direction is a factorial composition:

- unchanged agent;
- GEPA-optimized residual prompts;
- GAC-compiled regions;
- GAC plus GEPA on only the residual model decisions.

This would test whether compilation and prompt evolution are additive, whether shorter
GEPA prompts change the compilation break-even, and whether reflection can repair the
continuation-level failure that the replay gate cannot see. Each transformation must be
evaluated alone before the combined result is interpreted.

The manuscript now cites GEPA beside DSPy and MIPRO and places EvoC2F and Agent JIT on the
closer compiler axis. That positioning is correct.

## 4. Acceptance-critical concerns

### P0.1 End-to-end quality is underpowered and not non-inferior

The expanded partial compiler records zero failures in 30, but the one-sided exact 95%
upper bound is still 9.5%. The earlier aggressive compiler records one failure in 18, for
an upper bound of 23.8%. Neither zero observed discordance nor McNemar `p=1` establishes
equivalence. A deployment or preservation claim requires a predeclared non-inferiority
margin and hundreds of sealed pairs per domain and compilation depth.

**Required:** power the sample for a 1--3% margin; cluster by repository/domain/time;
retain exact-source checks and add blinded semantic adjudication.

### P0.2 Continuation checking is implemented but not yet live-calibrated

All 45 natural-study replay groups pass while one final answer fails. This is not an
anomaly; it exposes a missing layer. The guard covers tool arguments, outputs, counts, and
declared effects, but not the model that converts those outputs into the answer.

The implementation now adds a framework-neutral fail-closed `ContinuationGuard`. On a
provider-free replay of the 18 retained compiled outputs, it accepts 17, detects issue
6602, and a deterministic renderer built only from the three source observations restores
18/18 exact-contract passes. Every renderer or baseline recovery is revalidated, and
callback failures return no output. This correctly addresses the mechanism gap, but the
result is post-hoc and counterfactual: it does not measure live recovery latency/cost,
selection effects, or behavior beyond this exact extractive contract.

**Required:** execute the continuation boundary prospectively; calibrate program and
answer violations separately; report joint coverage, risk, latency, and fallback cost.

### P0.3 Selective admission remains degenerate

All live gates behave all-or-none. The earlier natural gate steps from no coverage to full
coverage at 0.14; the expanded 92-record gate steps at 0.11. The latter has two non-zero
weights, but still ranks no observed risk. This is a support counter, not a demonstrated
risk--coverage frontier.

**Required:** introduce natural negative, drift, stale-schema, permission, partial-tool,
and out-of-domain cohorts; compare the learned score with explicit one-class and hard-rule
baselines; evaluate on a post-selection sealed set.

### P0.4 The hand-written macro is a strong practical baseline

In the expanded test, the macro and partial GAC both pass 30/30 and use two provider
requests, but the macro replaces three reads with one and uses 30.9% fewer total tokens and
8.0% lower estimated cost than GAC. Its observed mean latency is higher, but that paired
difference is uncertain. On this task the macro is the better default unless maintaining
it is demonstrably expensive or the recurrent region is branch-dependent.

**Required:** measure engineering/maintenance effort, workflow drift, number of reusable
families, and amortization. Add a decision rule that recommends “write a macro,” “compile,”
or “do nothing,” rather than assuming compilation is always the target.

### P0.5 There is no live learned-workflow comparator

GEPA is adjacent, while AWO, Agent Workflow Memory, plan caching, EvoC2F, and Agent JIT
are closer on reuse/compilation. None is run on the same records. Literature comparison
prevents a false novelty claim but cannot establish empirical superiority.

**Required:** at minimum compare unchanged, macro, cache-only, GAC, and one learned
workflow method under identical models, prompts, records, cache policy, and temporal
ordering. Add GEPA only when prompt evolution is part of the evaluated scope.

### P0.6 Empirical breadth remains narrow

The principal live tests have 30 and 18 records from one GitHub issue task and one model.
The natural output schema still makes record, label, and comment reads useful, and all 132
expanded discovery traces converge to the same order. This is natural selection within a
constrained evidence shape, not open-ended workflow discovery.

**Required:** add at least two distinct real domains, including one branching workflow and
one stateful but safely staged workflow; use time-forward and out-of-repository tests.

### P0.7 The oracle correction is transparent but exposes protocol fragility

The earlier grader incorrectly imposed an excerpt minimum and mishandled a literal `none`;
its correction preserves the executed artifact and records four changed rows. The expanded
run fixed those defects before execution, but its online grader still imposed a literal
comment limit absent from the “as needed” prompt. The provider-free revision preserves all
212 prior labels and changes no provider output or metric. Both audit trails are strong;
both show that oracle tests must cover semantic tool equivalence before a paid run.

**Required:** freeze executable semantic-oracle tests before future provider execution and
run an independent audit on the sealed oracle, selection, and compiler eligibility rule.

### P0.8 Production and framework claims remain bounded

The staging-owning outer runner can discard uncommitted work; the model adapter cannot
generally retract emitted history. Removing model turns can also remove guardrail checks
that run at those boundaries. Artifact signing was disabled in the experiment, registry
objects are mutable, and there is no canary, rollback drill, multi-tenant calibration, or
drift response evidence.

**Required:** treat guardrails as barriers until replay is implemented; add explicit
continuation/control-point contracts, public-key artifact signing, atomic publication,
tenant-aware calibration, and canary/rollback evidence before production claims.

### P0.9 Not every demonstration is a real scenario

The primary natural study uses real public records and live provider calls. Tier 3 still
uses fictional deterministic business records, and the offline comparator is simulated.
They are valid conformance fixtures, not evidence satisfying an “all demos are real”
requirement.

**Required:** keep them in a conformance appendix or replace them with licensed, pinned
real workloads such as CVE enrichment, public PR/CI investigation, or package-maintenance
incidents.

## 5. Claim audit

| Claim | Verdict | Defensible wording |
|---|---|---|
| A recurrent prefix emerges without planted tool names/order | Supported in one task | 132/132 expanded discovery traces choose the same three reads under a constrained extractive schema |
| Provider requests decrease | Supported on sample | Partial compiler: four to two on 30/30; aggressive compiler: four to one on 18/18 |
| Necessary tool calls fall | Contradicted for GAC | Three in both unchanged and compiled conditions; macro changes three to one |
| Exact factual quality is preserved | Depth-sensitive | Expanded partial artifact: 30/30 all arms; aggressive artifact: 17/18 versus 18/18 comparators |
| GAC is non-inferior | Unsupported | Zero events in 30 still gives a 9.5% one-sided upper bound; no margin was predeclared |
| The gate discriminates risky inputs | Unsupported | All-or-none coverage in both live studies |
| The configured exact bounds recompute | Supported conditionally | Arithmetic is correct for the frozen contract/grid under i.i.d. or conditional-i.i.d. group indicators |
| Replay safety implies final-answer safety | Contradicted | 45/45 replay passes coexist with one factual answer miss |
| Structural determinism improves | Supported narrowly | The compiled tool prefix is deterministic by construction |
| Natural-language determinism improves | Not supported | Expanded exact-answer agreement is 0.7 baseline, 0.6 compiled, 0.4 macro over ten repeats |
| GAC is state of the art | Not established | No same-task learned-workflow head-to-head |
| GEPA is a direct compiler baseline | No | It optimizes residual prompts; it is adjacent unless broader optimization is claimed |
| The implementation is production-ready | Not established | Research alpha with missing operational and integration evidence |

## 6. Stronger research direction

The paper should evolve from “compaction preserves behavior” to **two-layer selective
agent compilation**:

1. **Program layer:** certify grounded arguments, effects, position, and deterministic
   tool behavior as now.
2. **Continuation layer:** certify the transformation from tool evidence to the user-facing
   answer, or replace it with a checked renderer.
3. **Portfolio selector:** compare macro, GAC, cache, and no-op choices using expected
   quality, maintenance cost, latency, token cost, and drift risk.
4. **Residual optimizer:** optionally apply GEPA-style reflective prompt evolution only to
   model decisions that remain after safe compilation.

This direction follows directly from the observed evidence: the program layer succeeds,
the answer layer fails once, and the macro occupies a different quality/cost point. It is
more novel and defensible than presenting GAC as a universal compactor.

## 7. Prioritized roadmap

1. **P0 — Power the next protocol.** Define a non-inferiority margin, independently audit
   the semantic oracle, and seal hundreds of clustered pairs per domain and depth.
2. **P0 — Prospectively evaluate end-to-end admission.** The contract and checked
   renderer are implemented and recover the retained miss; now separate program and
   continuation calibration and measure the live joint frontier.
3. **P0 — Build a non-degenerate frontier.** Add natural negative/drift/OOD groups and a
   post-selection test set.
4. **P1 — Expand real domains.** Add public PR/CI and CVE/package-maintenance workflows;
   include branches and staged state.
5. **P1 — Run closer baselines.** Macro, cache-only, one learned-workflow compiler, and
   optionally GEPA in a factorial residual-prompt experiment.
6. **P1 — Quantify amortization.** Include discovery calls, monitoring, artifact churn,
   and human maintenance time.
7. **P2 — Harden the runtime.** Guardrail barriers/replay, signed immutable artifacts,
   atomic registry publication, multi-tenant isolation, and canary rollback.

## 8. Final recommendation

The revised submission is no longer undermined by a wholly prompt-prescribed headline
workflow, an absent live macro, or an unexecuted confirmatory design. It now contains a
credible 30-pair real-provider replication, direct evidence that groundability controls
compilation depth, a retained negative quality result, unusually strong artifact
provenance, and a clear relationship to GEPA and contemporary compilers.

I would encourage resubmission after a powered multi-domain study and an end-to-end
continuation gate. In its current form, it is a strong artifact and a promising systems
paper, but the correct top-tier decision remains **major revision**, not acceptance.
