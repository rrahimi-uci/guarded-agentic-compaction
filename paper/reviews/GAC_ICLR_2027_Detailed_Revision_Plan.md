**ICLR 2027 · MANUSCRIPT REVISION BLUEPRINT**

Revision plan for  
“From Traces to Guarded Programs”

Deep review of the current Main manuscript against the attached PAT/OpenReview feedback

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th><p><strong>BOTTOM LINE</strong></p>
<p>The current Main manuscript already fixes many of the automated review’s textual and specification concerns. The remaining risk is concentrated in five places: candidate-selection multiplicity, interpretation of the 92-group gate, missing guard ablations, pseudocode/runtime-contract inconsistencies, and a small set of reporting errors. Repair those first; do not spend revision time re-solving feedback that is already incorporated.</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

**Prepared for** Reza Rahimi

**Review date** 21 September 2026

**Source set** Main manuscript (25 pages) + OpenReview/PAT feedback export (7 pages)

**OpenReview** [<u>forum?id=DF0JaS58gr</u>](https://openreview.net/forum?id=DF0JaS58gr)

Interpretation note. The current Main PDF is materially newer than the snapshot reviewed by PAT. This plan therefore labels each comment as RESOLVED, PARTIAL, or OPEN against the current Main—not against the older submission snapshot.

# Contents

**1** Executive revision verdict

**2** How the feedback maps to the current Main

**3** Workstream A — statistical validity and claim calibration

**4** Workstream B — algorithms, runtime contract, and formal consistency

**5** Workstream C — experimental additions and reporting

**6** Section-by-section manuscript patch map

**7** Proposed replacement language

**8** Execution sequence, gates, and effort options

**9** Final submission QA checklist

**Appendix** Minor edits and reviewer-response skeleton

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th><p><strong>RECOMMENDED PATH</strong></p>
<p>Use the “strong revision” track: (1) repair compiler-wide multiplicity with a frozen search or 106-group, two-candidate correction; (2) add a safe offline recurrence-only/unguarded ablation; (3) correct Algorithms 3–4 and Appendix A; (4) report absolute metrics and consistent denominators. Treat a larger risk–coverage frontier and read-only-prologue support as follow-on work unless the revision window is long.</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

# 1. Executive revision verdict

## 1.1 Overall assessment

**Scientific core:** strong and differentiated. The paper’s best idea is not deterministic replay by itself; it is the refusal structure—typed provenance, declared effects, position constraints, replay challenges, finite-sample admission, and unchanged fallback.

**Evidence posture:** unusually transparent. The manuscript keeps negative benchmark results, documents the \#6602 continuation failure, distinguishes admissibility from dispatchability, and acknowledges the i.i.d. and candidate-selection limits.

**Main acceptance risk:** the strongest live result is still attached to only per-candidate certificates because two candidates saw the same calibration split. Disclosure is good, but a skeptical reviewer can still say the central deployment claim is not covered by the theorem actually proved.

**Secondary risk:** the registered 92-group design cannot certify partial coverage, so the paper does not yet demonstrate that the learned nonconformity score produces selective risk–coverage behavior. The current evidence supports an all-or-none support gate.

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th><p><strong>REVISION PRINCIPLE</strong></p>
<p>Make the paper narrower and stronger. A precise claim about initial, read-only, pre-commit prefixes with a valid compiler-wide admission story is more compelling than a broad “agent workflow compiler” claim whose formal and runtime scopes diverge.</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

## 1.2 Priorities

| **Priority** | **Issue** | **Required action** | **Why it matters** |
|----|----|----|----|
| **P0** | Repair or sharply delimit candidate-selection multiplicity | Either freeze candidate selection before calibration on fresh/untouched groups, or correct across the two candidates with γ = δ/(2\|Λ\|) and at least 106 zero-violation admitted groups. | A headline live artifact has no compiler-wide certificate otherwise. |
| **P0** | Correct the 239/240 vs. 240/240 reporting | Choose intention-to-treat or completed-case reporting and make text, Table 10, denominators, and timeout policy agree. | Current wording is arithmetically inconsistent. |
| **P0** | Fix Algorithms 3 and 4 | Disambiguate slot identifiers/values; return slot annotations instead of “block region”; enforce s\<t; add explicit boundary_index=0; bind runtime handles and capability flags. | The formal scope is not fully enforced by the published pseudocode. |
| **P0** | Rewrite Appendix A multiplicity paragraph | Separate fixed-threshold γ from grid-wide δ and candidate-wide correction. Remove or relabel the 1.8%–13.6% figures. | Current wording invites a valid statistical objection. |
| **P1** | Add an unguarded recurrence-only ablation | Run offline/shadow, not live; compare recurrence-only replay, barrier-only compilation, full GAC, baseline, and manual. | This is the cleanest answer to “are the guards doing anything?” |
| **P1** | Upgrade metric reporting | Add absolute baseline/compiled/manual values, cost CIs, issue-type statistics, run-order controls, retry/timeout policy, and immutable provider/SDK identifiers. | Percent reductions alone are difficult to reproduce and audit. |
| **P1** | Reframe the gate evidence | State that \|K\|=92 permits only coverage 0 or 1 and that the study cannot assess q’s ranking quality. Retain graded selectivity as future work unless K is enlarged. | Avoid interpreting an arithmetic constraint as a learned-score result. |
| **P2** | Implement a recognized read-only prologue | Only if time permits: extend the entry contract to suppress replay of an allowlisted deterministic prologue and rerun AppWorld eligibility. | High upside for ReAct dispatchability, but it changes the runtime adapter. |

## 1.3 Preserve these strengths

The concrete \#4420 and \#6602 counterexamples; they make the need for provenance and continuation checks tangible.

The compile-or-retire cascade and attributed refusal accounting.

The distinction between hard barriers and statistical evidence.

The negative results on NESTFUL, API-Bank, and BFCL and the admission/dispatchability split on AppWorld.

The manual comparator and the explicit statement that GAC claims discovery/admission—not runtime dominance over known hand-written code.

The narrow Proposition 1 statement and the candid discussion of i.i.d. group assumptions.

# 2. How the feedback maps to the current Main

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th><p><strong>VERSION FINDING</strong></p>
<p>The PAT feedback was generated against an earlier manuscript snapshot. The current 25-page Main has already implemented most specification-oriented suggestions. Reopening those resolved items would add churn without improving the submission.</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

## 2.1 Substantive items already resolved in the current Main

| **Feedback theme** | **Status** | **Evidence in current Main** |
|----|----|----|
| **Prefix-only scope** | **RESOLVED** | Introduction and §2 now say GAC compiles initial read-only prefixes only and contrast it with arbitrary-entry JIT traces. |
| **Loss includes downstream baseline errors** | **RESOLVED** | §2 explicitly states that L scores end-to-end compliance under substitution and therefore requires baseline success ≥1−α on the dispatched slice. |
| **Objective/constraint group measure** | **RESOLVED** | Eq. (4) now sums within groups and states that objective and constraint use the same group distribution. |
| **Single-source groundability** | **RESOLVED** | Eq. (1) now quantifies over one source s∈Src(z,o\<j), matching Algorithm 3’s intended implementation. |
| **92-group coverage floor** | **RESOLVED** | §3 and Appendix C explicitly derive nη≥92 and show that \|K\|=92 certifies only coverage 0 or 1. |
| **Nonconformity model** | **RESOLVED** | Appendix C identifies ℓ2-regularized logistic regression, entry-observable features, dev-only standardization, and abstention-shaped labels. |
| **23-operator DSL** | **RESOLVED** | Table 3 lists all operators and the depth≤2/single-source constraints. |
| **Feasibility ρ ambiguity** | **RESOLVED** | §3 distinguishes the pre-synthesis ceiling with ρ=1 from the realized post-verifier condition. |
| **Model/settings/pricing** | **RESOLVED—VERIFY** | §4.1 and Appendix C name gpt-5.6-luna, the Responses interface, reasoning/verbosity settings, parallel-call/storage settings, and rate table. |
| **Manual comparator metrics** | **RESOLVED** | Table 4 reports manual reductions on the same resource axes and the text narrows the claim appropriately. |
| **34 vs. 11 AppWorld replay counts** | **RESOLVED** | Table 2’s caption and Appendix F.3 explain that these are held out from different fits/partitions. |
| **pytorch retirement mechanism** | **RESOLVED** | §5.2 and Appendix F.1 identify Stage 6 calibration retirement and explain the class-composition shift. |
| **ReAct position limitation** | **RESOLVED AS LIMITATION** | §5.3 and Appendix G quantify the limitation and describe—but do not claim to implement—a bounded read-only prologue. |
| **Workflow-reuse comparator context** | **RESOLVED AS DISCUSSION** | Appendix G explains why prompt induction, DAG scheduling, and plan caching do not directly instantiate guarded pre-model substitution. |
| **Cluster/non-exchangeability mitigations** | **RESOLVED AS DISCUSSION** | Appendix G names temporal separation, cluster-level/block-bootstrap bounds, and cluster-aware conformal treatment. |

## 2.2 Items still open or only partially addressed

| **Theme** | **Status** | **What remains** |
|----|----|----|
| **Candidate multiplicity** | **OPEN · P0** | The paper discloses per-candidate certificates, but the primary live pipeline still calibrates two candidates and selects afterward. The empirical headline is not compiler-wide under Proposition 1/Corollary 2. |
| **Gate frontier** | **PARTIAL · P1** | The arithmetic floor is now explained, but Appendix H still interprets a design that could not certify intermediate coverage as a negative learned-gate result. Reframe or recollect. |
| **Automated/unguarded baseline** | **PARTIAL · P1** | The manuscript explains why published systems are not drop-in comparators and adds Headroom/support-only controls, but it still lacks the internal recurrence-only replay ablation it identifies as highest value. |
| **Algorithm 3 notation and scope** | **OPEN · P0** | Slot key u is compared as if it were the runtime value; “block region” occurs before regions exist; write-order edges lack s\<t. |
| **Algorithm 4 position enforcement** | **OPEN · P0** | The tools(P)∩ALREADYOBSERVED check does not enforce normalized boundary a=0 when a different prologue tool has already run. |
| **Algorithm 4 runtime inputs** | **OPEN · P0** | ALREADYOBSERVED, SNAPSHOT, and STAGE are not bound by the signature; quota_attested is not defined in the effect-capability vocabulary. |
| **Appendix A multiplicity simulation language** | **OPEN · P0** | The 1.8%–13.6% paragraph appears to describe fixed-threshold miscoverage while discussing candidate/grid-wide guarantees. Rewrite or remove. |
| **Absolute metrics and CIs** | **OPEN · P1** | Cost rows lack 95% CIs; issue-type inferential rows are absent; primary tables show percentage reductions without absolute resource levels. |
| **H.1 exact-contract denominator** | **OPEN · P0** | Text says 240/240 and 239/239 while Table 10 sums to 239/240. The timeout policy is not consistently applied. |
| **Immutable reproducibility details** | **PARTIAL · P1** | Model and rates are now named, but exact snapshot/API date, SDK version/commit, retry/timeouts, token fields, cache accounting, order, and concurrency remain underspecified. |
| **Live effect-catalog trust root** | **PARTIAL · P1** | External substrates receive strong empirical audits; the live GitHub catalog would benefit from an equally explicit signed manifest and audit statement. |
| **Read-only prologue** | **OPTIONAL · P2** | The mechanism is discussed but unbuilt. Keep as future work unless it can be implemented and evaluated without destabilizing the revision. |

## 2.3 Independent review findings beyond PAT

| **Finding** | **Recommended treatment** |
|----|----|
| **Stochastic baseline interpretation** | Do not imply GAC improved accuracy because it scored 90/90 vs. 89/90. Treat the discordant case as an observed baseline-only failure and report repeat-run or deterministic-setting sensitivity if available. |
| **Latency validity** | Document blocked/randomized condition order, region, concurrency, warm-up, retry policy, and whether provider caching was shared. Otherwise wall-time reductions can mix structure with service variance. |
| **Absolute cost meaning** | Report baseline and compiled dollars per record (mean/median) in addition to percentages. Tiny absolute values and pricing assumptions matter to practical significance. |
| **“Distribution-free” wording** | Prefer “exact finite-sample binomial control under i.i.d. groups” unless exchangeability is defended. The method is not distribution-free with respect to arbitrary clustered temporal data. |
| **Prospective protocol design contradiction** | Appendix H required ≥3 admissible nonzero coverage levels but retained \|K\|=92, which makes intermediate admission impossible. State that the protocol could not answer its intended discrimination question. |
| **Cohort independence wording** | Verify that the “independent five-times-larger cohort” has no record overlap or shared selection. If not, say “larger sealed cohort” rather than “independent.” |

# 3. Workstream A — statistical validity and claim calibration

## 3.1 Repair candidate-selection multiplicity

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th><p><strong>WHY THIS IS THE FIRST TASK</strong></p>
<p>This is the only issue that directly separates the theorem from the headline deployment result. The paper’s disclosure is accurate, but disclosure does not create compiler-wide coverage.</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

**Current state.** Each primary family mines two candidates, calibrates both on the same split, and retains the empirically dominant survivor. Proposition 1 covers a single candidate fixed before calibration. Corollary 2 covers a frozen search that lets only one candidate reach calibration.

**Recommended repair (best balance).** Freeze the complete two-candidate set before calibration and apply a simultaneous correction over m=2 candidates and \|Λ\|=11 thresholds: γ=δ/(m\|Λ\|). At α=.05 and δ=.1, zero violations require 106 admitted groups. If immutable logs show that candidates, grid, and score were fixed before the original 92 labels were read, add at least 14 new independent groups; otherwise use a fresh 106-group calibration cohort. Rerun both fixed candidates and select only after the corrected bound is applied.

| **Candidates m** | **Per-test budget γ** | **Zero-violation nmin** | **Use** |
|----|----|----|----|
| **1** | δ/(1·11) | 92 | Current per-candidate grid |
| **2** | δ/(2·11) | 106 | Primary two-candidate correction |
| **4** | δ/(4·11) | 119 | If search expands |
| **8** | δ/(8·11) | 133 | Avoid unless explicitly budgeted |
| **16** | δ/(16·11) | 146 | Illustrates search cost |

**Alternative repair (cleanest theorem).** Rank and freeze one candidate using train/development data only, then evaluate it once on a fresh or untouched 92-group calibration set. Halt regardless of admit/retire. This activates Corollary 2 directly, but it must not reuse a calibration set that influenced candidate or manuscript decisions.

**Fallback if no new evidence is possible.** Keep the per-candidate result, but remove any wording that implies the primary compiler output has a 1−δ guarantee. Make the frozen-search cross-repository study the formal guarantee result and present the primary 90-case result as an empirical preservation/efficiency study.

### Implementation steps

1.  **Freeze artifacts and search metadata.**

> Hash the candidate programs, guards, verifiers, score model, threshold grid, manifest, and the exact list m of candidates before adding calibration data.

2.  **Choose one correction path.**

> Preferred: m=2 Bonferroni with n≥106; clean alternative: one frozen candidate with fresh n≥92. Do not mix the two narratives.

3.  **Predeclare group sampling.**

> Sample before filtering on recurrence; define group, distinct-day/principal rules, timeout labels, and all violation outcomes.

4.  **Rerun admission and retain all outcomes.**

> Report candidate-level nη, kη, Uη, coverage, and admit/retire for every threshold or provide the machine-readable report.

5.  **Update claim hierarchy.**

> Abstract → empirical results → theorem scope → limitations must use the same certificate level.

### Acceptance criteria

The calibration report identifies m before any calibration labels are read.

The bound uses γ=δ/(m\|Λ\|), or exactly one candidate reaches calibration under a frozen search.

Every selected artifact has Uη≤α under the corrected accounting.

Abstract, §5.1, §7, Appendix A, and Appendix C all describe the same guarantee level.

If a family retires after correction, the paper reports the retirement rather than weakening the budget.

## 3.2 Stop over-interpreting the 92-group step gate

**Fact already derived in Main.** With α=.05, δ=.1, \|Λ\|=11 and zero violations, admission requires nη≥92. If the total pool is \|K\|=92, any abstention leaves nη≤91 and cannot pass. Therefore admissible empirical coverage is exactly 0 or 1.

| **Target certifiable coverage c** | **Minimum total calibration pool ⌈92/c⌉** |
|----|----|
| **100%** | 92 |
| **80%** | 115 |
| **70%** | 132 |
| **50%** | 184 |
| **25%** | 368 |
| **10%** | 920 |

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th><p><strong>INTERPRETATION CHANGE</strong></p>
<p>The existing experiments establish support sufficiency at full coverage—not a useful learned risk–coverage frontier and not q’s ability to rank wrong dispatches. Appendix H’s null should be described as an underpowered/infeasible frontier test, not evidence that learned and support-only gates are intrinsically equivalent.</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

**If you want to retain the frontier claim:** increase the per-domain calibration pool before running the experiment. A 50% point needs at least 184 total groups even with zero violations; three distinct nonzero admissible levels will usually require substantially more, because observed violations raise the requirement.

**If you do not recollect:** rename the result “registered support-threshold behavior,” state that q’s discrimination remains untested, and move “graded selective dispatch” to future work.

## 3.3 Make the i.i.d. group assumption operational

**Current strength.** The paper candidly says independence is assumed and shows a block-correlation simulation.

**Remaining problem.** The live study uses min_days=1 and min_principals=1, so the formal guarantee is weakest exactly where the empirical headline is strongest.

### Recommended evidence hierarchy

Best: recollect/split calibration so groups are separated by day and/or principal; report effective independent-unit counts.

Good: cluster by day/author/repository burst and compute a conservative cluster-level exact bound; accept that n_eff may fall below admission.

Minimum: keep the current result but use “conditional on i.i.d. groups” every time the guarantee is summarized, including the Abstract if a formal guarantee is claimed there.

Do not call the result broadly “distribution-free” without the i.i.d./exchangeability qualifier.

## 3.4 Rewrite the Appendix A multiplicity paragraph

**Issue.** The current paragraph reports a single-candidate miscoverage near γ≈.00909 and then pools m candidates, giving 1.8% at m=2 and 13.6% at m=16. That is naturally read as candidate-wide/grid-wide risk even though γ is the per-threshold budget. The full candidate already ranges over 11 thresholds.

**Recommended replacement logic**

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th>For one fixed candidate and one fixed threshold η:<br />
Pr(rη &gt; Uη) ≤ γ, where γ = δ / |Λ|.<br />
<br />
For one fixed candidate across the complete grid Λ:<br />
Pr(∃η ∈ Λ : rη &gt; Uη) ≤ |Λ|γ = δ.<br />
<br />
For a fixed set of m candidates, each evaluated over Λ:<br />
choose γ = δ / (m|Λ|), so<br />
Pr(∃ candidate a, threshold η : r(a,η) &gt; U(a,η)) ≤ δ.<br />
<br />
At α=.05, δ=.1, |Λ|=11, m=2 and k=0, nmin=106.</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

**Editorial decision.** Either remove the 1.8%–13.6% simulation sentence, or explicitly label it “single-threshold illustrative calculation” and do not use it to characterize the whole candidate/grid certificate.

## 3.5 Correct Appendix H’s denominator and protocol interpretation

**Data inconsistency.** Table 10 totals 239 successful contracts out of 240 attempted records (60+60+59+60), while the prose says 240/240 and 239/239 after a timeout.

**Preferred reporting.** Use intention-to-treat as the primary row: 239/240 attempted in every arm, with one provider-timeout failure common to all conditions. Add completed-case sensitivity: 239/239 among provider-completed cases. If the protocol allows a retry, rerun the timed-out record under the predeclared retry rule and report both first-attempt and final status.

**Protocol interpretation.** State that the preregistered “three admissible coverage levels” criterion was impossible with \|K\|=92. The observed result is a protocol-design audit, not a clean negative result about q.

# 4. Workstream B — algorithms, runtime contract, and formal consistency

## 4.1 Patch Algorithm 3 (BUILDPATG)

**Problems to fix.** The current pseudocode uses u as both slot identifier and runtime value; says “block region” before candidate regions are mined; does not bind o_j in the loop head; and creates conflict-order edges over all pairs without stating temporal order.

**Proposed pseudocode semantics**

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th>Input: episodes T; entry schema Θ; effect catalog C; transform library L; ambiguity cap κ<br />
Output: provenance graph G and slot-status map S<br />
<br />
for each episode E=(z,M,e1:T,y):<br />
Σ ← allowlisted flattened entry sources from z<br />
for each call–result pair (c_j, o_j) in temporal order:<br />
for each slot name s in keys(args(c_j)):<br />
v_{j,s} ← args(c_j)[s]<br />
if LITERAL_ONLY(c_j, s):<br />
S[j,s] ← LITERAL; continue<br />
H ← BEST_PER_SOURCE{(σ,g) ∈ Σ×L : g(value(σ)) = v_{j,s}, depth(g)≤2}<br />
if H=∅: S[j,s] ← MODEL_ORIGINATED<br />
else if |H|&gt;κ: S[j,s] ← AMBIGUOUS<br />
else:<br />
S[j,s] ← GROUNDED<br />
add witness edges σ —g→ (j,s) to G<br />
Σ ← Σ ∪ eligible flattened paths from o_j<br />
for each pair of events (e_s,e_t) with s&lt;t sharing a resource and at least one write:<br />
add order edge e_s ≺ e_t to G<br />
return (G,S)<br />
<br />
MINEREGIONS later rejects any window containing a slot whose status is MODEL_ORIGINATED or AMBIGUOUS.</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

**Why this is better.** It preserves the intended algorithm while aligning scope: PATG annotates argument evidence; the region miner—not PATG—decides which windows are blocked.

## 4.2 Patch Algorithm 4 (DISPATCH)

**Critical correctness gap.** Equation (2) requires a=0, but Algorithm 4 only checks whether a tool in the compiled program has already been observed. A different documentation/prologue call can occur first and still pass that intersection test.

**Proposed boundary-time contract**

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th>Input: entry state z; runtime context X; registry R; effect catalog C; mode m<br />
where X = (manifest M′, boundary_index b, already_observed H, snapshot S, stage_factory F)<br />
<br />
1 if m=off: return FALLBACK<br />
2 if X.boundary_index ≠ 0: return FALLBACK<br />
3 A ← R.RESOLVE(X.manifest.compatibility, X.manifest.partition)<br />
4 if A=⊥ or A.lifecycle≠ACTIVE or not VERIFY_SIGNATURE(A): return FALLBACK<br />
5 if A.region_start ≠ 0 or H_A(z,X.manifest)≠1: return FALLBACK<br />
6 if tools(A.P) ∩ X.already_observed ≠ ∅: return FALLBACK<br />
7 if m=live and any tool requires_attested_snapshot and X.snapshot=⊥: return FALLBACK<br />
8 if q_A(z)&gt;η_A: return FALLBACK<br />
9 if m=shadow: log would-dispatch; return FALLBACK<br />
10 stage ← X.stage_factory.begin(X.snapshot)<br />
11 r ← INTERPRET(A.P,z,FACADE(C))<br />
12 on precommit error: FALLBACK only if stage.abort_and_attest(); else INCIDENT<br />
13 on postcommit error: INCIDENT<br />
14 if V_A(r)≠1: FALLBACK only if stage.abort_and_attest(); else INCIDENT<br />
15 return observations only after stage.commit(r.effects); otherwise INCIDENT</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

**Define the capability.** Replace or formally define quota_attested. A clearer name is requires_attested_snapshot or staged_quota, with a schema-level definition in the effect catalog. Include runtime history, snapshot, and staging handles in X rather than as free variables.

## 4.3 Keep the read-only-prologue extension out of the core unless implemented

**Minimal revision.** Retain a=0 as a hard invariant, enforce it explicitly in Algorithm 4, and describe the AppWorld result as an architecture-dependent deployability limit.

**Optional extension.** Permit an allowlisted, deterministic read-only prologue under an extended entry contract. The adapter must recognize exact prologue calls/results, prove they are effect-admissible, bind them as live-ins, and suppress replay. This is not arbitrary suffix dispatch.

### Acceptance tests for a prologue implementation

A prologue mismatch, extra call, order change, manifest mismatch, or unknown effect returns the unchanged baseline.

No call already committed by the host is replayed.

The compiled region’s provenance is recomputed against prologue outputs treated as explicit live-ins.

The early pilot’s duplicate/reorder failure is included as a regression test.

AppWorld structural eligibility is recomputed by architecture, with the same position/prologue definition used by runtime.

## 4.4 Strengthen the effect-catalog trust story

Publish the signed schema fields used by the live GitHub tools: effect, speculatable, replayable, isolation partition, staging requirement, and catalog version.

State who owns declarations and what change invalidates an artifact.

Add a live-study audit analogous to BFCL/AppWorld: observed call count, writes detected, hidden state/RNG checks where applicable, and zero undeclared mutations—or state why those checks are not available.

Make “unknown is not read” visible in the main method figure/caption and runtime facade description.

# 5. Workstream C — experimental additions and reporting

## 5.1 Add the missing internal comparator: recurrence-only replay

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th><p><strong>HIGHEST-VALUE NEW EXPERIMENT</strong></p>
<p>Do not force an incompatible external workflow compiler into this benchmark. Instead, price the exact safety mechanisms with an internal ablation that shares the same traces and task contracts.</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

| **Arm** | **Mechanisms** | **Question answered** |
|----|----|----|
| **B0 Unchanged agent** | Original model/tool loop | Reference quality and resources |
| **B1 Recurrence-only macro** | Replay the most frequent canonical sequence; no provenance/effect/position/contract/risk gates | Shows what recurrence alone would do; run only offline/shadow |
| **B2 Structural barriers** | Typed provenance + signed effects + a=0; no output verifier or statistical admission | Prices hard barriers |
| **B3 Deterministic contracts** | B2 + H/V replay challenge; no CP risk gate | Prices contract induction |
| **B4 Full GAC** | All barriers + calibrated admission | Target system |
| **B5 Manual** | Hand-written pre-model program | Known-workflow ceiling |

**Safety.** Never execute B1 live against a substrate where writes or non-reversible effects are possible. Use retained traces, resettable benchmark backends, or shadow execution.

### Required outputs

Exact end-to-end contract pass/fail and compiled-only failures.

Groundability failures, effect/position blocks, verifier abstentions, and statistical retirements by stage.

Dispatch/eligibility coverage and requests/tokens/latency/cost where live execution is safe.

Concrete counterexamples: \#4420 for an ungrounded slot; \#6602 for replay-pass/answer-fail; at least one hidden-effect/write example from BFCL/AppWorld.

A mechanism-removal table showing which guard catches each failure.

## 5.2 Upgrade live-provider reproducibility

| **Category** | **Add to Appendix C / manifest** |
|----|----|
| **Model** | Exact public snapshot/checkpoint ID, availability date, provider account tier/region if latency-relevant |
| **API/SDK** | Endpoint name, openai-agents package version and commit, HTTP/API version, tracer version |
| **Generation** | Reasoning effort, verbosity, temperature/top-p/max tokens/seed or explicit “unsupported”; tool-choice and parallel-call settings |
| **Reliability** | Retry count/backoff, timeout, rate-limit behavior, provider errors, and whether failed records are rerun |
| **Caching** | Cache eligibility, cache writes/hits, whether arms share cache state, and exact token fields used for cost |
| **Execution** | Concurrency, condition order/randomization, warm-up, clock definition, and latency aggregation |
| **Pricing** | Rate-source URL/date and formulas for input, cached input, cache write, and output tokens |

**Specific current phrase to change.** “Sampling parameters are not overridden and take provider defaults” is not fully reproducible. Enumerate the effective defaults returned by the API/SDK or pin an immutable request manifest.

## 5.3 Report absolute values, uncertainty, and failure policy

Add baseline, compiled, and manual mean/median requests, interfaces, total tokens, wall time, and estimated dollars per record. Keep percentage reductions as secondary columns.

Add 95% bootstrap CIs for estimated cost in Appendix D; the current cost rows show point estimates only.

Add issue-type routing to the paired-statistics table or explicitly explain why an inferential row is not meaningful.

Clarify that deterministic request-count differences are structural even when a baseline answer fails; report resource accounting for failed records consistently.

Report McNemar discordant cells, not only total exact passes. With one baseline-only failure and zero compiled-only failures, do not claim accuracy superiority.

For latency, provide median and a robust interval in addition to mean paired difference.

## 5.4 Comparator positioning

**Keep.** The explanation that Agent Workflow Memory, LLMCompiler, and plan caching optimize different intervention points is persuasive.

**Do not overuse.** The Headroom null only shows that payload compression did not engage on this payload shape. It does not substitute for a workflow-reuse or unguarded-replay baseline.

**Best claim.** “Our comparison isolates the marginal value of GAC’s barriers through a shared-pipeline internal ablation; published reuse systems remain non-isomorphic because they do not perform guarded pre-model substitution.”

## 5.5 Decide whether to pursue the prologue and larger frontier

| **Track** | **Evidence cost** | **Scope** |
|----|----|----|
| **Minimal defensible** | No new large experiment | Fix claims, algorithms, Appendix A, denominators, CIs; label gate as support threshold and prologue as future work. |
| **Strong revision** | Moderate | Multiplicity repair + internal unguarded ablation + reporting upgrades. Recommended. |
| **Ambitious** | High | Add K≥184 frontier cohort and implement/evaluate read-only prologue. Best science, but highest schedule and regression risk. |

# 6. Section-by-section manuscript patch map

| **Location** | **Change** | **Priority** | **Footprint** |
|----|----|----|----|
| **Abstract** | Clarify certificate level; avoid implying compiler-wide control for the primary runs unless repaired. Keep initial-prefix scope explicit. | **P0** | 1–2 sentences |
| **§1 Introduction** | Retain JIT analogy but name the capability as “initial read-only prefix specialization.” Add one sentence separating empirical preservation from formal admission. | **P1** | Space-neutral |
| **§2 Problem formulation** | No major rewrite. Verify Eq. (1), group objective, baseline-coupled L, and zero-dispatch convention remain consistent after edits. | **VERIFY** | None/minor |
| **Fig. 2 / Alg. 1** | If primary search is frozen or m-corrected, show this at calibration/selection. Add candidate-count budget m to inputs if using correction. | **P0** | Diagram label + pseudocode |
| **§3 Stage 6** | State that \|K\|=92 permits only 0/1 certified coverage and that q’s ranking quality is not identified. Align candidate multiplicity with new protocol. | **P0** | Replace 1 paragraph |
| **Proposition 1** | Keep theorem. Capitalize all formal references. Add one immediate sentence stating whether each experiment meets its precondition. | **P0** | 1 sentence |
| **§4 Setup** | Add immutable model/SDK manifest, timeout/retry/order/cache policy pointer. Name group sampling and candidate multiplicity protocol. | **P1** | 2–3 sentences |
| **Table 1 / §5.1** | Add absolute metrics in appendix; report discordant cells; update certificate wording after rerun. Do not imply 90/90 is an accuracy gain. | **P0** | Caption + paragraph |
| **§5.2** | Current pytorch explanation is good. Verify “independent” and cohort overlap. Keep frozen-search guarantee distinct. | **VERIFY** | Minor |
| **Table 2 / §5.3** | Retain the 34-vs-11 partition explanation. Reframe q/frontier result; preserve admissibility-vs-dispatchability distinction. | **P1** | 1 paragraph |
| **§6 Related work** | Keep architectural non-isomorphism explanation concise; add the internal recurrence-only ablation as the direct comparison. | **P1** | 1 paragraph |
| **§7 Limitations** | Lead with three facts: certificate scope, \|K\| arithmetic, i.i.d. assumption. Do not characterize the 92-group study as evidence about q discrimination. | **P0** | Rewrite opening |
| **Appendix A** | Rewrite multiplicity paragraph; separate γ, δ, grid, and candidate correction; retain proof unchanged. | **P0** | Replace 1 paragraph/table |
| **Algorithm 3** | Apply slot/value, annotation, output-binding, and temporal-order patch. | **P0** | Replace pseudocode |
| **Algorithm 4** | Bind runtime context; add explicit boundary-index check; define staging capability. | **P0** | Replace pseudocode |
| **Appendix C** | Add effective request manifest, software versions, retry/cache/order policy, and corrected nmin table by candidate count. | **P1** | Add table |
| **Appendix D** | Add cost CIs, issue-type rows, absolute metrics, and denominator/failure policy. | **P1** | Expand table |
| **Appendix F/G** | Keep benchmark audits; name which two GitHub families received Headroom; fix wording/typos. | **P2** | Minor |
| **Appendix H** | Fix 239/240; admit protocol infeasibility at \|K\|=92; change section cross-reference; avoid overinterpreting null. | **P0** | Rewrite H.1 close |

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th><p><strong>NINE-PAGE MAIN-BODY STRATEGY</strong></p>
<p>Keep new tables and configuration detail in appendices. In the main paper, spend space only on certificate scope, the 92-group interpretation, the internal ablation result, and the corrected live result. Recover space by compressing the related-work taxonomy and moving procedural detail from §5.3 to Appendix F.</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

# 7. Proposed replacement language

## 7.1 Abstract — choose one certificate track

**Use only if the new evidence supports it**

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th>TRACK A — after a compiler-wide repair<br />
“Candidate families are fixed before calibration and admission is corrected over the complete candidate–threshold set. At α=0.05 and δ=0.1, every reported primary artifact satisfies the resulting compiler-wide bound; otherwise the compiler retires the family.”</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

**Use if no multiplicity repair is run**

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th>TRACK B — if the primary experiments remain unchanged<br />
“The primary live artifacts carry per-candidate admission certificates: two candidates were evaluated on the same calibration split, so these runs do not establish a compiler-wide 1−δ guarantee. Frozen-search cross-repository runs satisfy the compiler-wide precondition.”</th>
</tr>
</thead>
<tbody>
</tbody>
</table>

## 7.2 §3 — gate interpretation

| “At the registered setting (α=0.05, δ=0.1, \|Λ\|=11), zero violations require at least 92 admitted groups. Because every current calibration pool contains exactly 92 groups, the only certifiable empirical coverages are 0 and 1. These studies therefore evaluate support sufficiency at full coverage; they do not identify whether q ranks dispatch risk or produces a graded risk–coverage frontier.” |
|----|

## 7.3 §5.1 — primary result

| “On the observed 90-record test cohort, the compiled condition has no compiled-only contract failure; the unchanged agent has one baseline-only failure. This supports preservation on this cohort, not accuracy superiority or semantic equivalence in general. \[Insert corrected certificate sentence here, matching Track A or B above.\]” |
|----|

## 7.4 §7 — limitation opening

| “Three constraints bound the claim. First, admission control is compiler-wide only when candidate search is frozen or corrected over all candidates and thresholds. Second, with \|K\|=92 the registered exact bound can certify only full coverage, so the present experiments do not demonstrate graded selectivity of q. Third, the binomial result is conditional on i.i.d. groups; the live cohorts do not establish exchangeability under temporal or principal-level clustering.” |
|----|

## 7.5 Appendix H — corrected outcome

| “Across 240 attempted records, all three arms satisfy 239/240 exact contracts; the same record times out at the provider in every arm. Among the 239 provider-completed records, all three arms satisfy 239/239. The pre-registered requirement of three admissible nonzero coverage levels was infeasible under the chosen \|K\|=92 per-repository calibration size, because any threshold admitting fewer than 92 zero-violation groups fails the registered bound. The study therefore audits support-threshold behavior but does not test the ranking quality of q.” |
|----|

## 7.6 Related-work/comparator positioning

| “Published workflow induction, plan caching, and DAG scheduling intervene at different boundaries and do not expose the argument provenance, effect contract, and pre-model substitution event required by GAC’s admission rule. We therefore compare mechanisms through an internal recurrence-only replay ablation that shares the same traces, records, model, and grader, rather than claiming a plug-compatible head-to-head.” |
|----|

## 7.7 Reproducibility sentence

| “The artifact pins the provider model snapshot, Responses API/SDK versions, effective generation settings, cache policy, timeout/retry policy, condition order, concurrency, token-accounting fields, rate-card date, tool/effect-catalog hashes, and every split/candidate manifest.” |
|----|

# 8. Execution sequence, gates, and effort options

## 8.1 Recommended sequence

| **Phase** | **Action** | **Exit gate** |
|----|----|----|
| **0. Freeze** | Archive current PDF, LaTeX, code commit, raw reports, splits, manifests, and PAT feedback. Create one issue ID per plan item. | No evidence is overwritten; hashes recorded. |
| **1. Correct paper logic** | Patch Algorithms 3–4, Appendix A, denominator wording, and minor errors before running anything. | Pseudocode and formulas pass independent review. |
| **2. Lock statistical protocol** | Choose m=2/n≥106 or frozen-one/n≥92; predeclare group sampling and timeout policy. | Signed/hashed protocol before new labels. |
| **3. Run multiplicity repair** | Collect/add groups and rerun admission exactly once under the locked protocol. | Every headline artifact admits under corrected bound or retires. |
| **4. Run guard ablation** | Execute recurrence-only and intermediate arms offline/shadow; preserve all counterexamples. | Mechanism table explains each failure/refusal. |
| **5. Recompute metrics** | Absolute values, CIs, discordant cells, cost formula, robust latency, manual rows. | All tables regenerate from retained raw files. |
| **6. Rewrite claims** | Update Abstract, §3, §5, §7, appendices, and OpenReview metadata/TL;DR consistently. | Claim audit finds no stronger wording elsewhere. |
| **7. Reproducibility audit** | Fresh environment runs table/figure scripts; verify hashes and public-safe archive. | One-command regeneration or documented steps. |
| **8. Final hostile review** | Ask one statistical and one systems reviewer to challenge only guarantee scope and runtime semantics. | No unresolved P0 item. |

## 8.2 Effort options

| **Track** | **Included work** | **Expected outcome** |
|----|----|----|
| **48–72 hour paper-only repair** | Algorithms, Appendix A, H.1, wording, CIs if raw data exist, minor cleanup | Defensible but leaves primary certificate per-candidate and no guard ablation. |
| **~1–2 week strong revision** | Paper repair + multiplicity evidence + offline guard ablation + full reporting manifest | Recommended acceptance-oriented package. |
| **~3–5 week ambitious revision** | Strong revision + K≥184 frontier + read-only-prologue implementation and dispatchability rerun | Best follow-up science; highest regression/schedule risk. |

## 8.3 Stop/go decisions

If corrected multiplicity causes a primary family to retire, keep the retirement. Do not change α, δ, Λ, or the candidate set after seeing it.

If the recurrence-only arm would execute a write or unknown effect, stop live execution and report the blocked counterfactual from a resettable/offline substrate.

If no calibration pool larger than 92 is available, remove any claim that the learned score demonstrates graded selectivity.

If the prologue extension cannot preserve exact replay suppression, leave it as future work and enforce a=0 explicitly.

If the timed-out record cannot be rerun under a predeclared policy, report 239/240 intention-to-treat and 239/239 completed-case—never 240/240.

# 9. Final submission QA checklist

## 9.1 Statistical and claim audit

□ Candidate set/count m is fixed before calibration; search protocol is hashed.

□ γ, δ, \|Λ\|, m, nη, kη, Uη, and selected η agree in prose, code, and reports.

□ Every compiler-wide claim is backed by frozen selection or correction over m\|Λ\| tests.

□ Every per-candidate claim is explicitly labeled per-candidate.

□ The 92-group all-or-none consequence is stated without attributing it to q.

□ i.i.d./exchangeability is a condition on every formal guarantee summary.

□ No post-hoc threshold, feature, candidate, or cohort filtering is omitted from multiplicity accounting.

## 9.2 Algorithm and runtime audit

□ Eq. (1), Algorithm 3, and the DSL all use the same single-source/depth≤2 semantics.

□ Algorithm 3 distinguishes slot name from slot value and binds each output o_j.

□ Candidate windows—not PATG—consume blocked-slot annotations.

□ Conflict edges require temporal order s\<t.

□ Algorithm 4 explicitly checks normalized boundary_index=0.

□ Runtime history, snapshot, stage factory, and capability flags are declared inputs.

□ Every fallback claim distinguishes clean pre-commit abort from post-commit incident.

□ Manifest/effect-catalog/library version mismatches are dispatch barriers.

## 9.3 Experimental and reporting audit

□ Exact model snapshot, SDK/API versions, effective generation settings, rate date, cache policy, timeouts, retries, ordering, and concurrency are recorded.

□ Primary tables include absolute values or a direct appendix pointer.

□ All bootstrap-CI columns actually contain intervals, including cost.

□ Contract totals sum across repository rows; attempted and completed denominators are distinct.

□ Baseline-only and compiled-only failures are reported as discordant cells.

□ Latency analysis uses paired order controls and a robust summary.

□ Headroom is described only as a compression comparator; support-only only as a gate comparator.

□ The unguarded arm is offline/shadow wherever effects are not reversible.

□ Every named script and file path exists in the anonymous artifact.

## 9.4 Editorial audit

□ “Proposition” and “Corollary” are capitalized consistently.

□ Table and appendix references point to the current numbering after layout changes.

□ American/British spelling is consistent (behavior/behaviour).

□ No phrase says “both GitHub families” without naming which two of the three.

□ The H.1 decision-rule cross-reference points to Appendix H, not §7.

□ INSERT/UPDATE/DELETE/CREATE/DROP has no stray space.

□ Bibliography and bullet lists have no orphaned page breaks.

□ Abstract, TL;DR, conclusion, and OpenReview metadata use the same scope and guarantee language.

# Appendix A. Minor edits and cleanup ledger

| **Location** | **Edit** |
|----|----|
| **Appendix A** | Change lowercase “proposition 1” / “corollary 2” to formal capitalization. |
| **Appendix A** | Use one symbol for population risk and one for the empirical upper bound; avoid switching hats/subscripts. |
| **Appendix C** | Use ln rather than an ambiguous log if the derivation depends on natural logarithms; mathematically the ratio is base-invariant, but clarity helps. |
| **Algorithm 1** | Keep Π for Algorithm 2’s admissible pairs (already fixed); verify no artifact-set symbol overload remains. |
| **Algorithm 1** | Verify wmax appears in the input and CEILING is applied to the family set or moved inside the family loop (current Main appears improved; recheck LaTeX source). |
| **Algorithm 3** | Bind o_j in the loop head and replace u with slot key s plus runtime value v\_{j,s}. |
| **Algorithm 4** | Use “behavior” consistently if the manuscript’s house style is American English. |
| **Appendix D** | Add missing cost CIs and clarify deterministic request differences when a baseline task answer fails. |
| **Appendix F.3** | Replace “INSERT/UPDATE/DELETE/ CREATE/DROP” with “INSERT/UPDATE/DELETE/CREATE/DROP.” |
| **Appendix G** | Replace “both GitHub families” with the exact two families used by the Headroom ablation. |
| **Appendix H.1** | Replace “decision rule fixed in advance (§7)” with “decision rule fixed above in Appendix H.” |
| **Appendix H.1** | Replace “240/240, 239/239” with consistent attempted/completed denominators. |
| **Cross-repository text** | Use “independent” only if record pools, selection, and provider executions are demonstrably non-overlapping. |
| **References** | Prevent the Basu et al. author list from leaving a single orphan line at the top of a page if layout permits. |
| **Global** | Search for .05 without a leading zero; standardize 0.05. |
| **Global** | Regenerate all table/figure/appendix numbers and hyperlinks after insertions. |

# Appendix B. Reviewer-response skeleton

**Opening.** Thank the reviewer, state that the current revision separates empirical preservation, per-candidate admission, and compiler-wide control, and summarize the three most material changes.

| **Concern** | **Response pattern** |
|----|----|
| **Multiplicity** | “We agreed that Proposition 1 did not cover post-calibration selection over two candidates. We \[froze one candidate before fresh calibration / corrected over 2×11 hypotheses and expanded calibration to 106 groups\]. We updated Abstract, §3, §5.1, §7, and Appendix A.” |
| **Step gate** | “We now state that \|K\|=92 mathematically permits only coverage 0 or 1. We no longer interpret the experiment as evidence that q lacks ranking power; graded selectivity remains unestablished.” |
| **Comparators** | “We added an internal recurrence-only replay ablation sharing records, traces, model, and grader. This prices provenance/effect/position/contract/risk barriers directly; published workflow systems intervene at non-isomorphic boundaries.” |
| **Position invariant** | “We now enforce boundary_index=0 explicitly in Algorithm 4 and scope the contribution to initial read-only prefixes. \[If implemented: We additionally evaluate an allowlisted read-only prologue.\]” |
| **Reproducibility** | “We added the immutable model/SDK/request/effect-catalog manifest, absolute resources, cost CIs, timeout policy, and consistent attempted/completed denominators.” |

<table>
<colgroup>
<col style="width: 100%" />
</colgroup>
<thead>
<tr>
<th><p><strong>FINAL RECOMMENDATION</strong></p>
<p>Submit the revised paper only after the guarantee level can be stated in one sentence without qualification drift. If you cannot repair multiplicity with new evidence, lead with the frozen-search cross-repository guarantee and present the primary 90-case study as empirical preservation plus efficiency—not as a compiler-wide certified deployment.</p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

Prepared from the attached 25-page Main manuscript and 7-page OpenReview/PAT feedback export. Page/section references refer to the current Main PDF supplied in this thread.
