# ICLR 2027 Deep Review and Revision Scorecard

Review date: August 21, 2026. This scorecard evaluates the 55-page open-research
article and the 20-page blind ICLR PDF at branch commit 155a442. Scores use a
0--10 scale. The assessment follows the official ICLR 2027 reviewer questions:
whether the problem and approach are well motivated, the claims are technically
and empirically supported, the work is significant, and the paper is clear and
reproducible. It also checks the official nine-page main-text, double-blind, and
AI-use requirements.

## Initial assessment

| Dimension | Initial | Short justification |
|---|---:|---|
| Originality | 8.0 | The compile-or-retire admissibility argument is a distinctive composition of tracing-JIT ideas, typed provenance, effect barriers, bounded synthesis, and exact selective admission; the ingredients and adjacent workflow optimizers are established. |
| Technical soundness | 8.0 | The per-candidate proposition and exact-grid calculation are stated correctly and narrowly, but the guarantee assumes i.i.d. groups, does not cover adaptive candidate search, and the new 8,190-trajectory result was presented without stating that tasks repeat across runs. |
| Clarity and presentation | 7.5 | The ICLR narrative is coherent, but the long article's abstract and results opener still described only two refusal substrates after BFCL and AppWorld were added; the ICLR abstract also rounded 2,339/2,340 full-code trajectories up to “all.” |
| Significance and impact | 7.5 | Removing recurrent provider boundaries under explicit refusal rules is practically relevant, but prevalence in deployed agents is unmeasured and a correctly placed manual program ties the compiler at runtime. |
| Related-work coverage | 8.0 | The paper covers tracing JITs, effect systems, synthesis, risk control, prompt/workflow optimizers, caching, and tool-use benchmarks, but the condensed ICLR text still implied only NESTFUL and API-Bank were suitable post-trace substrates. |
| Empirical rigor | 7.5 | Paired live studies, negative results, time-forward repositories, exact contracts, and AppWorld's reachable admission are valuable. The richest task remains one provider/model and snapshot; the registered gate is step-like; AppWorld runs no model and cannot support savings or quality claims. |
| Reproducibility | 8.0 | Raw results, manifests, deterministic generators, pinned sources, and validators are unusually strong, but the ICLR reproduction statement and appendix omitted the executable BFCL and AppWorld entry points. |
| Responsible claims and limitations | 9.5 | Manual parity, the continuation failure, effect/catalog trust, cache confounding, missing signature verification, conditional independence, and unrun work are disclosed rather than hidden. |
| ICLR compliance and anonymity | 9.0 | The blind source is anonymous and the main text uses nine pages with the required AI-use statement. An anonymous artifact bundle and author-side OpenReview obligations remain pre-upload actions. |

**Initial unweighted diagnostic mean: 8.1/10. Initial reviewer-style overall:
6/10 (borderline / weak reject).** The binding issue was not an invalid theorem
or failed experiment. It was confidence in the paper's evidence accounting:
the two manuscript versions drifted after a material new experiment, one
headline phrase overstated a count, and the new deployment diagnostic looked
more inferential than its repeated-run design permits.

## Revision made

No new experiment was run and no retained numerical result changed.

1. Synchronized the open-research abstract, contribution list, results opener,
   related-work discussion, limitations, and appendix with the four-substrate
   evidence now present in the paper.
2. Replaced “all full-code agents” with the exact
   2,339/2,340 trajectory count and replaced “third-party” with the more
   precise “released official-baseline” description in the ICLR abstract and
   introduction.
3. Stated in both manuscripts that the 8,190 AppWorld trajectories repeat tasks
   across 28 runs, models, and architectures. The 37.9% structural-eligibility
   rate is now explicitly descriptive, with no independent-sample interval or
   population-dispatch interpretation.
4. Defined the compact table notation p/a/w as pass/abstain/wrong.
5. Updated the ICLR related-work paragraph to distinguish corpora that retain
   intermediate results directly from BFCL and AppWorld, whose official gold
   artifacts must be executed on pinned backends.
6. Added exact provider-free BFCL, AppWorld compiler, and AppWorld dispatch
   entry points to both reproducibility appendices and included all four
   substrates in the ICLR reproducibility statement.

## Final assessment

| Dimension | Initial | Final | Why it moved, or why it did not |
|---|---:|---:|---|
| Originality | 8.0 | 8.0 | The revision clarifies the contribution but adds no new method. |
| Technical soundness | 8.0 | 8.5 | Exact counts replace an overstatement, and the repeated-run structure of the AppWorld diagnostic is now part of the claim boundary. The per-candidate and i.i.d. limitations remain. |
| Clarity and presentation | 7.5 | 8.5 | The article and ICLR submission now tell the same four-substrate story; compact notation and the admissible-versus-dispatchable distinction are explicit. |
| Significance and impact | 7.5 | 7.5 | Clearer framing cannot establish deployment prevalence, manual engineering savings, or runtime superiority. |
| Related-work coverage | 8.0 | 8.5 | The condensed submission now explains how all four external substrates relate to the post-trace question instead of naming only the two that retain results upstream. |
| Empirical rigor | 7.5 | 7.5 | Interpretation is more rigorous, but no new provider, powered comparison, risk--coverage frontier, or compiler-wide correction was added. |
| Reproducibility | 8.0 | 9.0 | The ICLR statement and both appendices now expose the exact entry points and environment boundary for BFCL and AppWorld. The anonymous bundle is still pending. |
| Responsible claims and limitations | 9.5 | 9.5 | Already a major strength; the revision makes one more dependency caveat explicit. |
| ICLR compliance and anonymity | 9.0 | 9.0 | The revision preserves the blind source and page-budget contract; operational upload checks remain human actions. |

**Final unweighted diagnostic mean: 8.4/10. Final reviewer-style overall:
7/10 (weak accept).** The recommendation moves because the paper is now
internally consistent and the newest result is stated at the strength its
sampling structure supports. The score does not move higher because the
remaining caps are empirical, not editorial.

## Residual acceptance risks

1. The registered 5% gate still behaves as a support threshold rather than a
   demonstrated risk--coverage frontier.
2. Proposition 1 is per fixed candidate; the compiler's adaptive family search
   has no candidate-level multiplicity allocation.
3. The strongest live evidence uses one provider/model family and one rich
   repository snapshot; the cross-repository task is deliberately simpler.
4. Correctly placed hand-written programs tie or beat the compiler on runtime
   resources, and manual construction, review, maintenance, and drift cost are
   unmeasured.
5. AppWorld establishes provider-free post-trace admissibility and structural
   eligibility only. It does not measure agent quality, provider requests,
   tokens, latency, cost, or a population dispatch rate.
6. The anonymous supplementary artifact must still be built and checked before
   submission.
