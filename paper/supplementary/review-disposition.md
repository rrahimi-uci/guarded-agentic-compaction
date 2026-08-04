# Disposition of the independent critical review

Companion to [`../paper-review.md`](../paper-review.md). Every claim in that review was
re-verified against the sources before anything was changed. This file records what was
verified, what was applied, and what was declined and why, so a later reader can audit the
response rather than trust it.

## Latest implementation pass (2026-08-03)

The third-pass review in [`../paper-review.md`](../paper-review.md) was revalidated and
implemented where no new paid evidence was required. This update supersedes older
“declined” or “not applied” entries below when they conflict: the paper is now titled
*When Traces Are Not Enough: Guarded Compilation of Tool-Using Agents*; EvoC2F, Agent JIT,
and GEPA are verified and cited; the default test collection includes the oracle tests;
and the publication validator covers raw comparator evidence and claim boundaries.

A subsequent paid corrective study closed the prompt-order, narrow factuality, live-macro,
and traffic-order findings in one domain, but its aggressive three-read artifact passed
17/18 exact contracts versus 18/18 for both comparators. The separately sealed 30-pair
replication has now also run. All 132 discovery traces use the same three-read order, but
the compiler rejects the full region because its third argument is not consistently
groundable and emits a two-read prefix. Baseline, partial compiler, and macro each pass
30/30. The partial compiler halves requests and reduces tokens 39.5%; the macro matches
requests while using fewer tools, tokens, and dollars. The paper therefore reports
depth-sensitive preservation and safe abstention, not compiler or non-inferiority
superiority. Both oracle revisions preserve prior labels and provider measurements. The
degenerate gate, modest sample, missing learned baseline, and multi-domain gap remain open.

The next acceptance-critical item is now implemented as code rather than left as a
recommendation. A framework-neutral continuation guard validates the post-region model
output, tries a deterministic checked renderer and then an optional baseline, and releases
only an output that passes the same contract. Provider-free replay over the retained real
GitHub cases accepts 17/18 unchanged, detects issue 6602, checked-renders that case, and
finishes 18/18. This remains post-hoc counterfactual evidence, not a live recovery arm.

## 1. Claims verified true and applied

| Review item | Verification | Change applied |
|---|---|---|
| P0.1 live prompt prescribes the optimized sequence | `github_live_study.py` PROMPT: "You must perform exactly these read-only calls, in this exact order"; eligibility is exact tool-contract compliance | New limitation paragraph "The task prescribes the optimized structure"; the discovery claim is scoped and named as the most important missing experiment |
| P0.2 quality oracle does not check factuality | `grade()` scores 5 equal booleans; `summary_valid` is only non-empty and ≤240 chars | New limitation paragraph; "no observed task error" → "no failure of the registered task contract" in abstract and results; discloses that conformance is 1/5 of the score |
| P0.3 gate did not discriminate; perturbations disabled | Artifact grid rows: η<0.14 admits n=0; η≥0.14 admits n=92. `sandbox=None`, `perturbations=()`, `perturbations_claimed: false`, `sandbox.n = 0`. 6 of 7 gate weights are exactly 0 | New limitation paragraph; §3.2 and Algorithm 1 now state the challenge is only as strong as the supplied sandbox |
| P0.4 SDK adapter cannot promise clean fallback | `model_provider.py` documents that an emitted `ModelResponse` may already be committed to history | New §3.5 "Where *unmodified baseline* is exact, and where it is not"; Figure 1 caption scoped to the staging-owning runner |
| P0.6 Tier 3 outside the publication manifest | `finalize_manifest.py` included `paper/`, `src/`, `tests/` only; no `experiments/live_results` path in the manifest | Tier-3 raw evidence added to the manifest (150 files) and a new `validate_demo_suite()` recomputes partial compaction, both refusal conditions, and the cost inversion from raw results |
| P0.7 McNemar *p*=1 is not evidence of equivalence | 18 pairs, zero discordant; `1−.05^(1/18)` = 15.3% | Results now report the exact one-sided upper bound and state that 15.3% degradation is compatible with the observation |
| P0.8 exchangeability is too weak for exact binomial coverage | Proposition assumed exchangeability, then applied Clopper–Pearson | Assumption restated as i.i.d. (or conditionally i.i.d.) group indicators; added clustering guidance and a note that the union bound covers one frozen artifact only |
| P0.9 documented command does not reproduce the run | Script defaults `--test-per-class 10 --repeat-cases 10`; archived run is 6 and 6; `run` recorded no argv | Script now serializes `run.argv` and `run.resolved_config`; README publishes the exact archived command and how it is recoverable |
| P0.10 latency confounded by condition order | Whole baseline batch runs before the whole compiled batch; no randomization | New limitation paragraph; the −85.0% latency figure is scoped as an observation under this ordering, and named as the likely cause of refusing conditions billing more |
| NESTFUL 96.3% is candidate recall | `nestful_benchmark.py` counts a slot recovered if the truth appears **anywhere** in `slot.candidates` | Benchmark extended to compute unique resolution, ambiguity, no-candidate and candidate-edge precision; re-run; abstract/results/table relabelled |
| "Refusal costs exactly the baseline" is contradicted | The paper's own Tier-3 table shows +55.4% and +54.5% cost | H5 restated as model-call count and quality; a paragraph explains the cache/ordering cause and why H5 is deliberately not in dollars |
| MDL risk proxy is a naming heuristic | `windows.py`: `sum(1 for t in tools if "." in t)` | Eq. (6) prose now states both coarse terms as implemented, and that neither affects admission |
| Program size is pre-synthesis | `windows.py`: slots+1 over `windows[0]` | Same paragraph |
| Estimator and grouped splits are not compile stages | `compile_grc()` receives `Splits` and never calls the estimator | Algorithm 1 retitled as the end-to-end pipeline; caller-owned stages marked `(caller)` |
| Cross-day support not required in the headline run | `min_days=1` | §3.1 scoped |
| Artifacts are not signed in the experiment | Archived artifact `signature: ''` | New limitation paragraph on registry integrity |
| Related-work table overlaps; overfull boxes up to 29.96pt | 13 overfull hboxes, worst 29.96pt, in table cells | Table widened to four wrapping columns; slash break points added; demo table made full-width; **now 0 in the ACM build and 1 at 0.98pt in the article** |
| Closest work omitted | 6 of 7 cited works verified against arXiv/PMLR | Added and integrated; the cache finding is now explicitly framed as consistent with prior cache literature, not novel |

Two further defects were found while verifying the review, and are the review's indirect
credit:

1. **A prior "zero overfull boxes" report was wrong.** It came from a hand-run `grep` whose
   pattern was mis-escaped and matched nothing. `validate_artifacts.py` now gates on
   overfull boxes with a fixed-string match.
2. **`tectonic --keep-logs` alone does not write the log.** The gate was initially reading a
   stale log that hid an 11.9pt regression introduced by a table change. The validator now
   asserts the log is not older than the PDF it describes.

## 2. Claims verified true, recorded, not yet actionable as edits

These originally required new paid experiments or a redesign. The later natural-workflow
study closed the first item and added the live macro requested by the fifth; the remaining
parts are still stated as limitations in §8 and future work in §7.3.

- **P0.1 (discovery, closed in one domain)** — the paid natural study now uses a
  task-level prompt with free tool ordering; cross-domain replication remains open.
- **P0.3 (risk–coverage frontier)** — calibration and test sets containing natural error,
  drift, and out-of-domain entries.
- **P0.5 (comparators, partial)** — the live hand-written composite tool is now present;
  cache-only, plan cache, and learned AWM/AWO-style comparators remain open.
- **P0.7 (power)** — hundreds of sealed pairs per domain for a predeclared margin.
- Multi-domain, time-forward evaluation; independent factuality oracle.

## 3. Declined

| Item | Reason |
|---|---|
| Cite **EvoC2F** as the closest omitted work | Superseded. Its ICML 2026 record and paper metadata were verified in the third pass; it is now cited and compared directly. |
| Remove Tier 3 from the manuscript | The review offered removal *or* full inclusion in the audit. Tier 3 is the only evidence covering observation-dependent branches, pagination, a mandatory write, and runtime refusal, and it is already labelled fictional in the abstract, methodology, table caption and README. Inclusion in the manifest and validator was the stronger of the two options and is what was done. |
| Redirect the project to PGCAS (§11) | A strategic proposal, not a correctness finding. It would discard the current contribution rather than repair it. Recorded for consideration; the control-point argument from §8.2 *was* adopted in §3.5 and the extension path. |
| Reviewer scorecard (61/100 overall) | Not a claim to apply. The evidence-scope critique behind it is applied throughout. |

## 4. State after the revision

```text
paper validator      956 checks passed; 0 failed
repository tests     214 passed (including replication-oracle and continuation tests)
verify_release.py    all checks passed
article.pdf          38 pp.  0 overfull hbox, 0 overfull vbox
main.pdf             20 pp.  0 overfull hbox, 0 overfull vbox
publication manifest 207 files, including both natural studies, checkpoint, continuation, Tier-3, and comparator evidence
```

(State after both reviews were dispositioned; see the second-review section below.)

The subsequent natural-workflow study repairs the prompt-prescription problem for the
headline experiment. The prescribed sequence remains only as a controlled ablation. The
new central limitation is stronger and more informative: a clean compiled tool-program
replay did not prevent one downstream exact-factuality failure.

---

# Second review: `../../claude-report.md`

A separate, sharper review (M1–M14). Same method: verify first, then apply. It found several
things the first review missed, including three self-inconsistencies in text written in
response to the *first* review.

## Verified true and applied

| Item | Verification | Change |
|---|---|---|
| **M1** gate is degenerate because the score was fitted with zero positives | 1 of 7 weights non-zero; artifact passed all 8 dev replays, and the score trains on *unproductive* dev outcomes — so 0 positives on 8 observations over 7 features | §8 now diagnoses the single-class fit as the cause of the step at $\eta=0.14$, reports the positive count as zero, names the two honest remedies, and states contribution (v) is demonstrated only as a sample-size counter |
| **M2** the feasibility ceiling is met with equality, so "any measured reduction must fall below it" is false | $\varphi{=}1$, $k{=}3$, $n_B{=}4 \Rightarrow \Delta_{\max}=0.750$; measured $=75.0\%$ | Corrected to "cannot exceed", with the saturation stated and its implication (a saturated ceiling says nothing about the compiler) |
| **M3** $\alpha$ bounds violation of a *self-fitted* contract | $V$ is induced from the same traces the program is synthesized from; `perturbations_claimed: false` | New paragraph after Prop. 1: zero violations in 92 groups is self-consistency, not correctness; the three missing independent links are named |
| **M4** 132 eligible vs 116 assigned — 16 unexplained | `tool_contract_eligible: 132`; split sizes sum to 116 | §5.2 now accounts for all 132: the 16 are surplus to the a-priori $n{=}92$ requirement, unused and not filtered |
| **M5** break-even reported at its most favourable basis, at list price | Reproduced all four: 176 / 207 / 232 / 292 | Reported as a range with the basis per figure, plus the direction of bias (list vs 96–98% cached) |
| **M6** Demo E's $+8.3\%$ inversion is inside the $+55\%$ confound the paper itself measures | E′/E″ do identical work and bill $+55.4\%$/$+54.5\%$ | **The claim is withdrawn for Demo E** and retained only for Demo F ($+123\%$); magnitude called indicative |
| **M7** three Wilcoxon variants unlabelled; a rank test applied to a constant | All 18 request diffs are exactly $-3$ | Procedure named per row; the requests row now reads **deterministic** instead of $p=2.2\!\times\!10^{-5}$ |
| **M9a** recall is near-definitional | `expected_producer_absent = 0` — not one slot had a non-empty candidate set missing the truth | Stated explicitly: recall measures search reachability, is insensitive to ranking, cannot fall below groundability |
| **M9b** 215 no-candidate slots vs "one ungrounded slot" | Different denominators (slots vs first-hit episode attribution) | Attribution rule stated; both reported |
| **M10** the stated objective is not the implemented one | `compile_grc` ships the first admissible family, not the argmax | Eq. (5) restated as a design target; and the "ranking only" defence is withdrawn — ranking decides *which* artifact ships |
| **M11** the tracing-JIT lineage is uncited | Dynamo, Gal 2009, PyPy, Hölzle 1992, Lucassen–Gifford, Chow | Added and used as the *framing*: GAC is a tracing JIT whose guard must additionally certify grounding, effects, and finite-sample risk. Novelty paragraph rewritten around it |
| **M12** guardrail elision is outside the threat model | Guardrails run at model boundaries; deleting boundaries deletes evaluations | New limitation: recommends declaring guardrail presence a barrier until re-running inside the facade is implemented |
| **M13** numeric/presentational defects | 5.98 s vs 5.81 s; Fig. 5 printed both $+55.4$ and $+54.5$ as "−55%"; "preregistered" vs "not externally preregistered" | Runtime de-duplicated; figure labels now one decimal in the prose's sign convention; "pre-specified internally" throughout; Demo B's 0.97, Demo D's $n{=}2$, and the table's role-ordering all explained |
| **M14** (fair half) "Contradicted" overreaches at $n=6$ | 1/6 vs 0/6 | C5 verdict changed to **Not supported** |
| **M8** no comparator | — | Already added before this review arrived: Table 4 and §5.4, from the offline study, where the hand-written macro **beats** GAC on three of five workloads |

Its gate also caught a **6.7pt overfull box** that one of these very edits introduced, which is
the strongest argument for having added it.

## Not applied

| Item | Reason |
|---|---|
| **M14** retitle | Superseded. The third-pass recommendation was adopted because “Preserve the Reasoning” is not evaluated and “specialization” names a broader pass outside the headline study. |
| **M2/M3/M8** new experiments | At the time these required paid execution. The task-level prompt and live macro were subsequently run in the natural-workflow study. Perturbation-backed selectivity and a learned AWO/AWM-style head-to-head remain unrun. |
