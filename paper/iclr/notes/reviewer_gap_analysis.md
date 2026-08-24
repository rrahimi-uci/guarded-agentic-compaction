# Reviewer-Oriented Gap Analysis

## Strongest current claim

The revised ICLR draft is strongest when read as a paper about
`compile-or-retire` specialization, not general agent optimization. The core
supported result is:

- recurrent read-only workflow prefixes can be compiled into guarded programs,
- those programs preserve exact held-out task contracts on three real GitHub
  workflow families and on a narrower cross-repository extension, and
- recurrence alone is insufficient without admission support, as shown by
  NESTFUL, API-Bank, and executed BFCL retirements, while AppWorld supplies the
  first reachable external admission and shows that an admissible artifact may
  still be structurally ineligible under most agent architectures.

## Presentation gaps closed in this revision

These were the presentation-level reasons the earlier draft did not read as an
ICLR submission. All are now addressed.

1. `Bold and italic did not render at all.` The template's `times` package
   silently dropped every bold and italic shape, so `\emph`, table headers, and
   theorem heads printed as plain roman throughout. Replaced with `newtx`.
2. `No algorithms.` A paper about a compiler described its compiler only in
   prose. There are now four: compile cascade and calibration in the main text,
   provenance and runtime dispatch in the appendix.
3. `No formal problem statement.` Grounding, the prefix invariant, selective
   dispatch, and the selective-risk objective are now numbered equations, and
   `alpha`, `delta`, and the threshold grid are defined before Proposition 1
   uses them.
4. `The only figure was a vertical stack of grey boxes.` Replaced by a
   three-lane architecture diagram with an explicit barrier band and the
   retire/fallback edges drawn.
5. `Related work was too narrow.` It is now organized into three focused
   paragraphs with 24 resolved citations, and it leads with the tracing-JIT lineage
   (Dynamo, trace JIT, meta-tracing, deoptimization) that is the paper's actual
   intellectual ancestor, plus effect systems, partial evaluation, program
   synthesis, and distribution-free risk control.
6. `The paper used 6 of its 9 allowed pages` while omitting the above. It now
   uses the full budget on technical content.
7. `Review formatting.` The blind PDF retains the official template's
   line-number ruler and anonymous running head.
8. Cross-version AppWorld drift. The open-research abstract and results
   opener now describe all four compiler substrates; the ICLR abstract reports
   2,339/2,340 rather than “all” full-code trajectories.
9. Repeated-run interpretation. Both manuscripts now state that the 8,190
   AppWorld trajectories repeat tasks across 28 runs, so 37.9% is a descriptive
   structural-eligibility diagnostic rather than an independent-sample estimate.
10. Reproduction surface. Exact provider-free entry points for executed BFCL,
    AppWorld compilation, and AppWorld dispatch analysis now appear in both
    appendices and the ICLR reproducibility statement names all four substrates.

## Remaining weaknesses before submission

1. `Gate maturity is still the main scientific risk.`
The admission theorem is per candidate, but the retained evidence still looks
more like an exact support threshold than a demonstrated risk-coverage frontier.
This is likely to be the first technical concern from strong ICLR reviewers.
Section 7 now says so directly and names the refit as the highest-value
follow-up.

2. `Manual parity narrows the practical contribution.`
The draft states this honestly, including the one family where the hand-written
program is cheaper than the compiled artifact, which improves credibility but
still means the paper does not support runtime dominance over hand-written
programs.

3. `The cross-repository result is narrower than the primary GitHub study.`
The time-forward extension is valuable, but it uses a simplified two-read task
on which a fixed template is tied or stronger.

4. `External validity is still limited.`
One provider/model family and one revision-pinned public snapshot for the
richer evidence.

5. `Continuation correctness is not fully solved in the main claim.`
Clean compiled tool-program replay does not imply answer-level correctness. The
draft says so and names counterfactual trace auditing as the instrument that
would measure it.

6. `Anonymous artifact packaging remains an operational blocker.`
The reproducibility statement describes an anonymous supplementary archive as a
pre-upload deliverable. That archive must actually be built before upload; the
current repository is identified.

7. AppWorld broadens admissibility evidence, not the live efficiency claim.
Its gold-solution compiler run makes the 5% bound reachable and its released
agent traces reveal an architecture-dependent dispatch precondition. No model
runs in the compiler substrate, the repeated trajectory units are not
independent, and the logs do not retain model boundaries, so the result licenses
neither agent quality nor provider savings.

## Why the draft excludes some prior material from the main text

- `GCS, GEPA, and portfolio studies` are useful, but they complicate the claim
  boundary and lean on weaker or explicitly exploratory evidence.
- `HMDA and demo-suite material` broaden scope but dilute the ICLR main-track
  narrative because they do not strengthen the primary causal claim.
- `The long related-work matrix and operational audit detail` are better kept in
  appendix or supplementary material for a 9-page submission.

## Highest-value upgrades if more time remains before submission

1. Refit or redesign the admission score so the registered `alpha=.05` gate
shows a genuine risk-coverage frontier instead of an all-or-none step.
2. Add a powered, time-forward quality study with a predeclared non-inferiority
margin and at least one harder cross-repository workflow task.
3. Measure manual construction, review, and maintenance cost under drift so the
comparison to hand-written programs is complete on both runtime and engineering
axes.
4. Prepare an anonymous artifact bundle with hashes, manifests, raw outputs, and
exact reproduction instructions aligned to the main-paper claims.
