# Reviewer Response — external review, 2026-09-12

Mapping from each point in the external review to the change made, the file it
landed in, and the evidence it was checked against. Items the review got wrong
are recorded as such rather than "fixed", and items deferred are named.

## Addressed in the main text

| Review point | Change | Where |
|---|---|---|
| Foundation model, provider, decoding, and pricing unspecified | Named the provider/model and pointed at the full rate table | `sections/evaluation.tex`, `appendix.tex` (`app:config`) |
| Step-gate is partly an artifact of `N_cal = 92` | Stated the `⌈92/c⌉` cohort floor and that `c ∈ {0,1}` is forced at 92 groups | `sections/method.tex` stage 6, `sections/discussion.tex`, `app:config` |
| Headline `U_η` presented without the per-candidate qualifier | Qualified in abstract, introduction, and §5.1 | `sections/abstract.tex`, `introduction.tex`, `results.tex` |
| Tracing-JIT framing oversells scope vs. the `a = 0` invariant | Stated prefix-only scope where the analogy is drawn and where the invariant is defined | `sections/introduction.tex`, `problem.tex` |
| Eq. (4) loss couples admission to baseline accuracy | Stated that the gate certifies end-to-end compliance, not non-inferiority, and requires baseline success ≥ 1−α on the dispatched slice | `sections/problem.tex` |
| Eq. (1) written multi-source but implemented single-source | Rewrote with `Src(z, o_<j)` and an explicit single-source quantifier matching Alg. 3 | `sections/problem.tex` |
| Objective/constraint measure mismatch | Both halves now taken over `D_grp` | `sections/problem.tex` |
| Eq. (6) `ρ` not measurable at stage 3 | Split into a pre-synthesis filter (`ρ = 1`) and a realized post-verification condition | `sections/method.tex` |
| `FitScore` model family and labels unspecified | Named as a regularized logistic model; label construction stated, including why no wrong-execution labels exist on `D` | `sections/method.tex`, `app:config` |
| Manual comparator has no resource numbers | Added a full resource table on the same axes | `tables/manual_resources.tex`, `app:stats` |
| 23-operator DSL not specified | Added the operator table with classes and arities | `tab:dsl` in `app:config` |
| `pytorch/pytorch` core-protocol retirement unexplained | Identified the stage and the cause | `sections/results.tex` §5.2, `app:breadth` |
| Table 2 "held-out replay" conflicts with the 11/11 in the text | Clarified: two different partitions, both held out | `results.tex` caption, `app:external` |
| Non-exchangeability mitigations not actionable | Named three repairs and the sample-size cost | `sections/discussion.tex`, `app:limits` |
| ReAct prologue extension not discussed | Named replay suppression as the mechanism, flagged as conjecture | `sections/discussion.tex`, `app:limits` |
| No plan-caching / workflow-reuse baselines | Explained the interface mismatch per system and named the unguarded ablation as the real gap | `sections/discussion.tex`, `app:limits` |
| "four repositories" vs five in Appendix H | Corrected to five | `sections/discussion.tex` |
| Alg. 1 `w_max` missing from `Input` | Added | `figures/alg-compile.tex` |
| Alg. 2 overloads `A` | Renamed the local admissible-pair set to `Π` | `figures/alg-calibrate.tex` |
| `φ`/`ϕ`, `U_η`/`U_η̂`, `.05`/`0.05` inconsistencies | Standardized | `results.tex`, `introduction.tex` |
| "average is bimodal" | Reworded to a distribution across architectures | `sections/results.tex` |
| `r^⋆` typography, sentence-initial `\cref` | Switched to `r^{*}` and `\Cref` | `appendix.tex` |

## Review points that were incorrect

- **"Algorithm 1 line 7 uses the family variable `F` instead of `\mathcal{F}`."**
  It already uses `\mathcal{F}`. Likely a PDF-extraction artifact in the
  reviewer's copy; no change made.
- **"Abstract contains encoding artifacts (`readonly`, `reduce`, `Recurrence`)."**
  The source reads `read-only`, `reduce inference`, etc. These are hyphenation
  artifacts of the reviewer's text extraction, not source defects.
- **"Cite Agent Workflow Memory / LLMCompiler / plan caching / EvoC2F."** All
  four were already in `references.bib` and cited in §6. The genuine gap was a
  comparison, not a citation, and is addressed as an interface-mismatch
  discussion plus a named unrun ablation.

## Deferred

- **Unguarded-replay ablation.** The one comparison we owe and did not run:
  deterministic replay of the mined region with provenance, effect, and position
  barriers disabled, which would price the guards rather than the compilation.
  Named explicitly in §7 and `app:limits`.
- **Refit of `q` for a genuine risk–coverage frontier.** Blocked on calibration
  pool size; a cohort of at least `⌈92/c⌉` groups is a precondition.

## Page budget

The main text was at the 9-page limit before this revision and is at it after.
Space was recovered by moving expanded detail to the appendix, tightening prose,
setting Algs. 1–2 in `\scriptsize`, and rendering `gac_aha_example.pdf` at
`0.88\linewidth`. Verify after any further edit that §8 ends on page 9:

```
tectonic --outdir build main.tex && pdftotext build/main.pdf - | \
  awk 'BEGIN{RS="\f"} /CONCLUSION/{print "Conclusion on page " NR; exit}'
```
