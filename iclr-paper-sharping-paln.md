# ICLR Paper Sharpening Plan

Date: 2026-08-24
Scope: sharpen the current ICLR paper using only the benchmark data already retained in this repository.

## Goal

Increase acceptance probability by narrowing the paper to the strongest claim the current evidence fully supports, instead of trying to make the existing evidence carry a broader story.

## Recommended paper thesis

The paper should present `guarded agentic compaction` as a `compile-or-retire` method for recurrent read-only agent prefixes.

The strongest current claim is:

- recurrence can propose candidate specializations,
- provenance, effect barriers, and continuation checks can reject unsafe ones,
- finite-sample admission can justify a small set of deployments,
- and refusal is a first-class positive result, not a failure to optimize.

The paper should not read as a general agent-optimization, broad workflow-compilation, or mature risk-coverage-frontier paper.

## What the current data supports

- Strong live evidence on three GitHub workflow families with paired held-out evaluation.
- Real savings with preserved exact task contracts on the retained GitHub cohorts.
- A narrow but useful cross-repository time-forward extension with principled retirement.
- Strong refusal evidence on NESTFUL, API-Bank, and executed BFCL.
- A useful admissible-versus-dispatchable distinction from AppWorld.
- Strong reproducibility and artifact discipline.

## What the current data does not support strongly enough

- Broad claims about general agent optimization.
- Compiler-wide guarantees over adaptive candidate search.
- A mature learned gate with a real graded risk-coverage frontier.
- Runtime superiority over well-written manual programs.
- Broad external validity across providers, models, or workflow classes.
- Strong claims from AppWorld about quality, savings, or independent-sample behavior.

## Main strategy

1. Narrow the central claim.
2. Promote refusal and retirement to headline results.
3. Demote the learned gate from a headline strength to a conservative exact-admission mechanism with a null frontier result.
4. Make the GitHub live-family evidence the core empirical anchor.
5. Use external substrates to define the boundary of the method, not to imply broad generalization.

## Section-by-section rewrite plan

## 1. Abstract

Target outcome:
The abstract should read like a precise systems-and-evidence paper, not an expansive optimization paper.

Actions:

- Lead with the problem of when recurrent traces may be replaced, not with cost reduction.
- State the method as `compile only what can be grounded and admitted; otherwise retire or fall back`.
- Keep the three GitHub-family result as the main positive evidence.
- Keep the cross-repository result, but call it narrower and time-forward.
- Keep the three-substrate retirement plus AppWorld admission result.
- State explicitly that AppWorld separates admissibility from dispatchability.
- Remove any wording that sounds like the learned gate already provides a useful frontier.

Acceptance check:
Every sentence in the abstract should map to one of these evidence classes: primary live result, narrow transfer result, refusal result, or dispatchability-boundary result.

## 2. Introduction

Target outcome:
The introduction should make the paper's novelty the admissibility boundary, not generic workflow acceleration.

Actions:

- Keep the motivating example with `ungroundable_slot`; it is one of the strongest parts of the paper.
- Frame the intellectual contribution as `trace-derived specialization with explicit refusal`.
- State early that recurrence is only a proposal mechanism.
- Reword the contributions so that they center:
  - guarded compile-or-retire specialization,
  - live evidence on three GitHub families,
  - refusal as a scientifically meaningful result,
  - admissible versus dispatchable separation.
- Reduce language that suggests general compilation of agent workflows.

Acceptance check:
The introduction should make it hard for a reviewer to mistake the paper for a generic workflow-optimizer paper.

## 3. Method

Target outcome:
The method section should remain technically strong while reducing overhang from the theorem.

Actions:

- Keep the theorem, but explicitly frame it as a per-candidate admission result, not a compiler-wide guarantee.
- Add one short sentence near the theorem or immediately after it that says the present system uses adaptive search and therefore the theorem is narrower than the full pipeline.
- Emphasize that the exact gate is conservative and that the default output is refusal.
- Avoid rhetorical emphasis that implies the learned score already discriminates well in practice.

Acceptance check:
A reviewer should not feel that the statistical claim is stronger than the actual demonstrated scope.

## 4. Experimental setup

Target outcome:
The evaluation section should clearly separate evidence tiers.

Actions:

- Label the GitHub live-family study as the primary evidence.
- Label the cross-repository study as a narrower transfer check.
- Label NESTFUL, API-Bank, BFCL, and AppWorld as external compiler substrates, not pooled task benchmarks.
- Make explicit that external substrates do not support live planning-quality claims.
- Keep the paired-comparison and exact-contract emphasis.

Acceptance check:
No reviewer should be able to say the paper mixes incomparable evidence types into one performance story.

## 5. Results

Target outcome:
The results section should tell one clear story: preserved contracts on the main benchmark, narrow transfer, then principled refusal and dispatchability limits.

Actions:

- Keep the current order: primary GitHub, time-forward transfer, then refusal/dispatchability.
- Tighten the prose after the main GitHub result so the reader sees the real claim:
  preserved exact contracts on observed cohorts, not semantic equivalence in general.
- In the transfer subsection, explicitly say this is evidence of discovery plus principled retirement, not workflow-general dominance.
- In the external-substrate subsection, make the headline:
  `the binding constraint is evidence, not just replayability`.
- Present the AppWorld result as a boundary insight:
  admission can be reachable while dispatch remains architecture-dependent.

Acceptance check:
The strongest result should still be the GitHub live-family study, and the section should not over-interpret AppWorld or the narrower transfer task.

## 6. Discussion and limitations

Target outcome:
The limitations section should feel like deliberate scientific discipline, not post-hoc apology.

Actions:

- Keep `gate maturity is the main scientific risk` as the first limitation.
- Make the null gate-frontier result more central, not buried.
- State plainly that the learned gate currently behaves more like a support threshold than a useful graded deployment rule.
- Keep the independence/exchangeability caveat.
- Keep the manual-parity point and use it to narrow the practical claim.
- Keep the provider/model/repository scope limitation.

Acceptance check:
A skeptical reviewer should conclude that the paper is honest and well-bounded, even if they still want more evidence.

## 7. Related work

Target outcome:
The related-work section should support the narrower thesis.

Actions:

- Keep the tracing-JIT analogy as the primary lineage.
- Keep effect systems, bounded synthesis, and exact risk control as the supporting technical lineage.
- Reduce emphasis on optimizer papers except where needed to contrast against them.
- Make explicit that the paper is about admissible specialization under evidence, not prompt tuning or generic tool-use optimization.

Acceptance check:
Related work should reinforce the chosen claim boundary instead of inviting comparison to larger optimization agendas.

## 8. Appendix and supplementary positioning

Target outcome:
The appendix should carry the broader negative, auxiliary, and protocol detail without competing with the main-paper thesis.

Actions:

- Keep the theorem proof, configuration, and reproducibility content.
- Keep the gate-frontier pilot/null material, but reference it as follow-up evidence that sharpens the paper's limitation.
- Keep broader ablations only if they tighten the main claim boundary.
- Move anything that feels exploratory, weakly connected, or broader-than-supported fully out of the main-paper narrative.

Acceptance check:
The appendix should deepen credibility, not broaden the claim.

## Concrete cuts and demotions

- Cut or demote any sentence implying the learned gate already yields a practical risk-coverage frontier.
- Cut or demote any sentence implying broad agent-optimization superiority.
- Cut or demote any sentence implying AppWorld supports quality or efficiency.
- Cut or demote any sentence implying compiler-wide statistical control.
- Cut or demote any sentence implying manual baselines are clearly inferior.

## Concrete promotions

- Promote the `compile-or-retire` framing.
- Promote the `ungroundable_slot` motivating example.
- Promote refusal as a positive empirical outcome.
- Promote the `admissible does not imply dispatchable` result.
- Promote the paper's artifact discipline and claim hygiene as part of its credibility.

## Proposed contribution list for the ICLR version

1. A guarded compile-or-retire pipeline for recurrent read-only agent prefixes that combines provenance grounding, effect and position barriers, bounded synthesis, runtime guards, and conservative finite-sample admission.
2. Paired live evidence on three GitHub workflow families showing preserved exact task contracts with substantial resource savings on observed held-out cohorts.
3. A narrow time-forward cross-repository extension showing both successful transfer and principled retirement without loosening the gate.
4. A boundary study across public trace substrates showing that recurrence and replayability are insufficient, admission is evidence-limited, and even admitted regions may not be dispatchable under common agent architectures.

## Reviewer-risk mitigation plan

### Likely reviewer criticism

`The theorem is narrower than the system.`

Response in paper:
State this earlier and more plainly; do not oversell the theorem.

### Likely reviewer criticism

`The learned gate does not actually show a useful frontier.`

Response in paper:
Admit this directly and reposition the gate as a conservative refusal mechanism whose exact admission rule is scientifically cleaner than its current empirical selectivity.

### Likely reviewer criticism

`Manual programs are as good or better on some tasks.`

Response in paper:
Say the practical value is derivation from traces without manual rewriting, not guaranteed runtime dominance.

### Likely reviewer criticism

`External benchmarks are not equivalent to live agent evaluation.`

Response in paper:
Agree in the manuscript and use them only as boundary evidence.

## Minimal revision package

If time is limited and no new experiments are added, prioritize this order:

1. Rewrite abstract and introduction around the narrower thesis.
2. Rewrite contributions to remove broad optimization language.
3. Tighten result-section framing around live evidence, narrow transfer, and refusal.
4. Strengthen discussion of the null gate-frontier result.
5. Cut over-claiming sentences across the draft.
6. Recheck title, captions, and conclusion for broad language.

## Stronger title direction

The title should favor:

- guarded programs,
- evidence-gated compilation,
- recurrent agent workflows,
- compile-or-retire specialization.

It should avoid sounding like:

- universal agent compilation,
- general optimization,
- broad safe automation.

## Definition of success

This sharpening pass succeeds if the paper is read as:

`a careful, novel, evidence-bounded paper on when recurrent agent traces may be compiled and when they should be refused`

and not as:

`a broad claim that agent workflows can now be safely and generally compiled with a mature statistical gate`

## Final recommendation

With current data only, the best path to ICLR acceptance is not to make the paper sound bigger.

The best path is to make the paper more exact, more bounded, and more memorable:

- compile only what is justified,
- retire what is not,
- and treat refusal as part of the scientific result.
