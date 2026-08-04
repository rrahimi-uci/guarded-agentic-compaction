# Technical Review

**Paper.** *Compile the Routine, Preserve the Reasoning: Guarded Specialization of Tool-Using Agents* (28 pp., 38 refs, 5 tables, 6 figures, 6 appendices)

**Reviewer role.** Independent technical reviewer (systems / ML-for-agents / empirical methodology)

**Date.** 2026-08-03

**Recommendation.** **Major revision.** Strong, unusually honest engineering paper with a genuinely useful design principle and a good negative result — but the two claims it foregrounds (a real-workload efficiency win, and a risk-calibrated admission gate) are each undercut by a construction choice the paper itself discloses. Neither is a fraud problem; both are fixable with experiments the authors are clearly capable of running.

**Overall score: 65 / 100**

---

## 1. Summary of the submission

The paper targets a real inefficiency: a mature ReAct-style agent re-derives the same read-only evidence-gathering prefix every episode, paying model calls to re-decide something already decided. The authors argue — correctly — that deleting those calls is not caching, because a repeated sequence is not a proof of admissibility.

The proposed system, **Guarded Agentic Compaction (GAC)**, is a trace-to-program compiler with five components: (i) typed, value-level argument provenance over a trace graph (PATG) that must *ground* every tool argument in entry state or a prior result; (ii) hard barriers for unknown/irreversible effects, approvals, handoffs, manifest mismatch, and non-prefix position; (iii) bounded program synthesis over a closed 23-operator library at depth ≤ 2; (iv) induced hard guards plus a post-execution verifier; and (v) a selective-admission gate whose threshold is chosen from a pre-registered 11-point grid under a simultaneous one-sided Clopper–Pearson bound, with retirement (emit nothing) as a legitimate output.

Evidence comes in three tiers: NESTFUL (provider-free, 1,415 executable episodes), a live-provider study on a pinned Apache-2.0 GitHub-issues snapshot (132 discovery / 18 sealed test), and a six-shape demonstration suite including three negative controls.

Headline results: −75.0% provider requests, −65.7% tokens, −85.0% wall latency, −52.6% estimated cost on 18 unseen issues with no observed contract failure and unchanged tool calls; on NESTFUL, 96.3% candidate recall but **zero** certifiable families; plus two deliberate negative results (recurrence ≠ certifiability; token saving ≠ cost saving).

---

## 2. Scorecard

| # | Dimension | Weight | Score | One-line rationale |
|---|---|---:|---:|---|
| 1 | Novelty & originality | 10% | **68** | The *composition* is new and the admission-argument framing is the right question; no individual element is, and the tracing-JIT ancestry is uncited. |
| 2 | Problem formulation & framing | 7% | **78** | Sharp, well-motivated, correctly distinguishes compaction from caching; §2 is clean. Title/abstract overreach on "preserve the reasoning". |
| 3 | Technical soundness (theory) | 12% | **70** | The binomial/union-bound math is correct and I verified it. But the calibrated quantity is conformance to a self-fitted contract, and eqs. (4)–(5) are not what the algorithm optimizes. |
| 4 | Method design & completeness | 8% | **72** | Barrier cascade and staging semantics are thoughtful; §3.4.1's honesty about the adapter is exemplary. Two eq. (6) terms are admittedly unfaithful and *are* load-bearing for which artifact ships. |
| 5 | Experimental design & rigor | 15% | **52** | The flagship scenario prescribes the structure it "discovers"; the ceiling is saturated exactly; no comparator baseline; run order not counterbalanced. |
| 6 | Strength of evidence for claims | 13% | **55** | −75% requests is arithmetic given the prompt; the gate never discriminates; 18 sealed pairs bound degradation only at 15.3%. |
| 7 | Statistical analysis | 8% | **58** | Correct exact-binomial core, but Table 2 silently mixes three Wilcoxon variants, applies a rank test to a constant, and uses only 2,000 bootstrap resamples. |
| 8 | Reproducibility & artifact | 7% | **66** | Pinned revisions, digests, commands, 188 tests — good. No artifact locator, no `.git` metadata, signing disabled, provider path unreproducible. |
| 9 | Related work & positioning | 5% | **80** | Table 4 is excellent and current (2026 works included). Misses the trace-JIT and effect-system literatures it structurally depends on. |
| 10 | Clarity & presentation | 6% | **66** | Precise but dense and nominalization-heavy; terminology sprawl with no notation table; two figures are redundant with tables. |
| 11 | Scientific integrity & self-criticism | 5% | **92** | Best feature of the paper. Archived failed pilot, retained rejected candidates, Table 5 claims register with "Contradicted" and "Not supported" verdicts. Rare and creditable. |
| 12 | Practical significance | 4% | **60** | The addressable region — read-only, position-0, prefix-only, sequential — is narrow, and break-even (~176–292 episodes) is not obviously reached by most workflows. |
| | **Weighted total** | **100%** | **65** | **Major revision** |

Interpretation of the band: 65 is "clearly publishable content, not yet publishable evidence." At a top-tier venue this is a borderline-reject that becomes a solid accept with §4 gaps G1–G4 filled. At a workshop it is above the bar today.

---

## 3. What the paper gets right (and should not lose in revision)

1. **The central conceptual contribution is correct and under-appreciated elsewhere.** "Existing optimizers decide *what* to rewrite; none supplies the admission rule that licenses it" is an accurate diagnosis of the workflow-optimization literature. The paper's design principle — *an agent optimizer should be judged by what it can explain and enforce when it must not compile* — is the durable takeaway and is worth its own emphasis.
2. **Retirement as a first-class optimizer output.** Returning `Retire` with an attributed reason, and keeping every rejected candidate in the denominator (Alg. 1), is exactly right and is the structural reason the NESTFUL negative result is trustworthy.
3. **§3.4.1 is a model of engineering honesty.** Distinguishing the staging-owning outer runner (clean fallback exact) from the model-boundary adapter (cannot un-emit a committed `ModelResponse`) is a subtle correctness argument most papers would have papered over. Keep it, and consider promoting it — it is a real finding about where "unchanged baseline" is and is not achievable.
4. **The claims register (Table 5) and the archived pilot (§5.4, Fig. 6).** Publishing a self-inflicted high-severity bug (suffix-only regions dispatched at entry, 16.7% contract validity) with the corrected result beside it is the single most persuasive thing in the paper about the authors' care.
5. **Correct core mathematics.** I independently reproduced: n ≥ 92 groups from α = .05, δ = .10, |Λ| = 11, k = 0; U₉₂ = 0.04981; the k = 0 closed form; and the 15.3% one-sided bound from 0/18. The Clopper–Pearson-plus-union-bound construction with a *frozen* score and grid legitimately supports post-hoc threshold selection. This is done properly.
6. **Related work is current and fairly stated**, including "we did not reimplement AWO" and "our cache observation is *consistent with* [21, 29] rather than a new discovery." Both admissions cost the paper novelty and buy it credibility.

---

## 4. Major issues

Ordered by severity. **M1–M3 are, in my judgement, blocking for a top-tier venue.**

### M1 — The selective-admission gate has no empirical support, and the paper does not diagnose why *(blocking)*

§8 reports that every grid threshold below 0.14 admits zero calibration groups and every threshold ≥ 0.14 admits all 92, with zero violations, and that "six of its seven feature weights are exactly zero (only `hull_margin` is non-zero)." The paper labels this "the gate did not discriminate in this run" and moves on.

The root cause is visible but unstated. §3.3 says q(z) is "trained on development-group **unproductive** outcomes (wrong or abstained)." §5.2 says the artifact "passes all eight development replays." If all eight dev groups produced productive outcomes, **the logistic model was fit with zero positive examples** — on 8 observations, with 7 features. The observed all-or-none behaviour is the signature of a near-constant score (all 92 entries fall in (0.11, 0.14]), which is precisely what a single-class fit produces.

Consequence: claimed contribution (v) — "finite-sample selective admission with normal retirement" — is demonstrated only as a *sample-size counter*. On NESTFUL the gate rejects everything because 26 < 92; on GitHub it admits everything because the score is constant. There is no point in either study where the gate discriminates between inputs, so the risk–coverage machinery is entirely unexercised.

**Required fix.** Either (a) construct a development set that contains genuine unproductive outcomes — the §8 wish-list is right: hard-but-supported inputs, OOD entries, source and schema drift, stale versions, ambiguous provenance, partial tool failures — and publish a risk–coverage curve with non-degenerate coverage at several α; or (b) drop the learned score in favour of an explicitly one-class construction (distance-to-hull, conformal nonconformity on entry features) and say so. Reporting *n* positives in the dev fit is mandatory either way. Until one of these exists, the abstract should not lead with "executes only through a gate whose threshold is chosen on a pre-registered grid."

### M2 — The flagship scenario prescribes the structure the compiler "discovers" *(blocking)*

§8 states this plainly: "The live prompt instructs the agent to perform three named read-only calls *in that exact order*, and compiler eligibility is exact compliance with the same contract, so 132/132 discovery traces qualify. Recurrence, argument shape, and prefix position are therefore true by construction."

Two consequences the paper does not draw out:

- **The feasibility ceiling is saturated exactly.** With φ = 1, k = 3, n_B = 4, eq. (7) gives Δ_max = 0.750, and the measured reduction is 75.0%. §3.1's claim that "any measured reduction must fall below it" is falsified by the paper's own headline: the bound is met with equality, because nothing abstains and nothing fails. A ceiling that is saturated carries zero information about the compiler; it only confirms that the prompt fully determined the region.
- **The measured effect is arithmetic, not empirical.** 4 provider calls → 1 for a 3-tool prescribed chain is the theoretical minimum for *any* static chaining mechanism. The paper concedes a hand-written composite tool "may be preferable for a single obvious prefix" (§8) but does not run it, so the compiler's marginal value over the trivial alternative on this workload is **unmeasured and plausibly zero**.

**Required fix.** The experiment §8 itself identifies as "the single most important missing experiment" must be run: a task-level prompt in which the agent may reorder, skip, or substitute reads, so recurrence is *discovered* rather than dictated. Report φ (fraction of episodes with an eligible region), the family-support distribution, and the abstention rate — those three numbers, not −75%, are what would establish RQ2. Until then, §5.2 should be titled and framed as a *runtime feasibility demonstration*, and the abstract's "one learned artifact removes three of every four model calls" needs the qualifier "on a workload whose prefix the task prompt fixes."

### M3 — The risk guarantee bounds violation of a self-fitted contract, not task error *(blocking)*

This is the deepest problem and the paper gets within one sentence of it without stating it. Contracts (H, V) are **induced** from train/dev traces (Alg. 1 line 17). A "violation" is defined as *wrong after dispatch*, where wrongness is adjudicated by V (Alg. 3 line 5). A program synthesised to satisfy an induced V will, absent distribution shift, almost never violate V. **Zero violations in 92 groups is therefore close to a tautology, not an observation**, and α bounds self-consistency rather than correctness.

Two independent facts compound this:

- The quality oracle is five booleans, one of which is *execution conformance* (§8) — so ⅕ of "quality" is satisfied by construction in the compiled arm — and it "never compares the summary against the issue body or comments, so a fluent fabrication inside the length bound passes."
- The one mechanism that could have challenged the candidate *before* calibration did not run. §3.2: without a sandbox "the suite cannot run at all, and the artifact then records `perturbations_claimed: false`. The headline live artifact of §5.2 is in exactly that position."

So for the shipped artifact: no perturbation challenge, a verifier fitted to the same traces it validates, and a quality oracle that cannot detect fabrication. The chain of guarantees has no independent link.

**Required fix.** (a) Run the perturbation suite on the shipped artifact — this is a sandbox-provisioning problem, not a research problem, and it is the cheapest large credibility gain available. (b) Separate the *induction* traces from the *violation-adjudication* oracle: score outcome and conformance separately (§8 already proposes this), and add factual grounding against source spans with blinded adjudication. (c) Add mutation/metamorphic testing: mutate entry states in semantically meaningful ways and measure the violation rate the gate actually catches. (d) Rephrase Prop. 1's consequence explicitly as *"violation rate of the registered contract"*, never as *"error rate."*

### M4 — Unreconciled split accounting, and a calibration size equal to the requirement

§4.3: "The discovery cohort contains 132 issues. Of these, 116 exact-contract traces are assigned to train (16), development (8), and calibration (92)." But §8 and Appendix D both state eligibility is **132/132**. So 16 episodes — a number exactly equal to |train| — are eligible, unassigned, and unexplained.

Separately: calibration is 92 groups and the gate requires 92 (Fig. 2's caption says the study "was deliberately sized to reach it"). Because n is fixed a priori by (α, δ, |Λ|), sizing to it is not itself invalid — but combined with 16 silently dropped episodes it is impossible to rule out either a splitting bug or a post-hoc allocation.

**Required fix.** State the split rule verbatim, confirm it was fixed before any outcome was observed, account for all 132 episodes with a flow diagram (eligible → assigned → used → excluded, with reasons), and report the gate result under at least one alternative split (e.g. 92 train/dev, calibration = remainder) to show the conclusion is not allocation-dependent.

### M5 — Reported dollar savings and break-even are known-biased by the paper's own cache analysis

§7.3 concedes the fix: "the break-even in §5.2 should be computed against the **cached** baseline price rather than the list input price." That means Table 2's −52.6% cost and the ~233-episode break-even are computed at list input price, while §5.3 measures cached-input shares of **96%** (Demo E baseline) and **98%** (Demo F baseline). If the GitHub baseline is similarly cache-dominated — a 4-turn loop over one long prefix almost certainly is — the true dollar saving is materially smaller than 52.6% and break-even is materially later.

The break-even figure is also unstable across metrics, and the paper reports only the most favourable one:

| Basis | Break-even (eligible future episodes) |
|---|---:|
| Provider requests (528 / 3) | **176** |
| Tokens (533,293 / 2,572.6) | **207** |
| Dollars, discovery only ($0.0958 / $0.000412) | **233** (as reported) |
| Dollars, discovery + confirmatory arms ($0.1204 / $0.000412) | **292** |

**Required fix.** Recompute all cost figures with a two-tier (cached/uncached) price model, report measured cached-input share per arm for the GitHub study as is already done for the demos, present break-even as a range with the basis stated, and include the confirmatory-run cost since it was incurred. Engineering and monitoring cost should be given at least an order-of-magnitude estimate rather than a disclaimer.

### M6 — Demo E's cost inversion is smaller than the acknowledged confound

§5.3 presents "token saving and cost saving can have opposite signs" as a contribution, with Demo E at −66.4% tokens / **+8.3%** cost and Demo F at −16.8% tokens / **+123.0%** cost, attributing the effect to cache-write amortisation ("structural rather than an artifact of pricing").

But the paper's own negative controls quantify the confound: E′ and E″ do **identical work** at +0.2% and +0.0% tokens, and bill **+55.4% and +54.5%**. §8 attributes that to uncounterbalanced batch order and cache warmth. An artifact worth ~+55% cannot support a structural claim about a +8.3% effect. Demo E's inversion is inside the noise floor the authors themselves measured.

Demo F at +123% plausibly exceeds the floor and can carry the qualitative claim; the effect size cannot be trusted. Note also that the same confound sits under the −85.0% wall-latency headline, which §8 already declines to call causal — yet Table 2, Fig. 3, and the abstract all present it without that qualifier.

**Required fix.** Interleave and randomise condition order within pairs, run ≥ 3 replicate blocks, report cached-input share per condition, and re-derive the E/F comparison. Drop or heavily hedge Demo E's inversion; retain F. Add the latency caveat to the abstract, or report latency only as a secondary observation.

### M7 — Table 2 mixes three different Wilcoxon variants, and tests a constant

I reverse-engineered the reported p-values; they are not from one procedure:

| Row | Reported p_W | Reproduces as |
|---|---|---|
| Wall latency, cost | 7.6e-06 | **Exact** two-sided signed-rank floor, 2/2¹⁸ = 7.629e-06 |
| Input / output / total tokens | 2.0e-04 / 1.9e-04 / 2.0e-04 | **Normal approximation**, z = −3.724 → p = 1.96e-04 |
| Provider requests | 2.2e-05 | **Tie-corrected normal approximation** with all 18 \|d\| tied → z = 4.243 → p = 2.21e-05 |

Three variants of the same test in one table, unlabelled, is a reporting defect. Worse, the provider-requests row applies a rank test to a quantity that is **structurally constant** (every pair is exactly −3, bootstrap CI [−3, −3]); the p-value there is not evidence, it is an artifact of a degenerate input. Additional statistical issues: 2,000 bootstrap resamples is low for 95% endpoints (use ≥ 10,000); §4.1 and §5.1 call hypotheses "preregistered" while §8 says the study "was not externally preregistered"; and McNemar p = 1 is reported in Table 2 alongside the correct note that it "carries essentially no information," which invites exactly the misreading the note disclaims.

**Required fix.** One test procedure, named, with the exact/asymptotic choice stated per row; drop the requests p-value and report the deterministic difference as such; 10,000 resamples; replace "preregistered" with "pre-specified internally" throughout; move McNemar to a footnote and lead with the 15.3% degradation bound.

### M8 — No comparator: the intervention effect is established, superiority is not

§8 concedes it: no AWO, no LLMCompiler, no plan caching, no FlowCompile, no hand-written composite tool. For the GitHub scenario the omission is consequential because a hand-written tool is the *obvious* engineering answer to a prompt-prescribed 3-call prefix. Two cheap additions would change the paper's standing:

1. **Hand-written composite tool** (hours of work). It will match −75% requests. The interesting result is what GAC adds: guard coverage, abstention on drifted entry states, and automated re-derivation when the prefix changes. Measure *those*, and the paper's value proposition becomes measurable rather than argued.
2. **AWO-style meta-tool induction on the same traces** (days). Table 4's "Admission: Empirical" vs "Exact selective bound" row is the paper's core positioning claim and is currently untested. Running AWO's induction and showing which of its meta-tools GAC's barriers *reject* would be the strongest single result the paper could add.

### M9 — NESTFUL "96.3% recall" is close to tautological, and the failure accounting does not reconcile

Two problems in Table 1.

**(a) The recall metric is nearly definitional — and the paper does not say so.** To the authors' credit, §4.1 and §5.1 are careful to label 96.3% as *candidate* recall and to print unique resolution and precision beside it in both the abstract and Table 1. The stronger point is not disclosed anywhere: 5,746 − 5,531 = 215, which is *exactly* the reported count of "slots with no candidate." So there is not a single slot where the search produced a non-empty candidate set that omitted the true producer. That cannot be coincidence — candidates are generated by value matching, and the gold producer by definition emitted the matched value, so its membership follows automatically whenever any depth-≤ 2 path exists at all. Recall here is therefore ≈ 1 − Pr[no path exists]: it measures search *reachability*, not dependency identification, and it can essentially never fall below the groundability rate no matter how bad the ranking is. The scientifically load-bearing numbers are unique resolution **80.7%** and candidate-edge precision **84.3%** (1,033 spurious edges over 895 ambiguous slots, ≈ 2.15 candidates per ambiguous slot).

**(b) 215 ungrounded slots produce one blocked window.** §5.1 says full-window failures are "overwhelmingly ambiguous value matches (207), with **one** ungrounded slot" (1,415 − 1,207 = 208 ✓). But Table 1 reports **215** slots with no candidate. Unless those 215 slots lie outside every enumerated window, or are absorbed into ambiguity-attributed episodes by first-hit accounting, the two counts are inconsistent. Appendix D's span-level counters (10,172 / 5,341 / 4,853 / 1) do not resolve it because they are non-exclusive span counts.

**Required fix.** State the near-definitional property of recall explicitly (one sentence: "recall is bounded below by groundability and is not sensitive to ranking quality"), reorder Table 1 so unique resolution and precision precede recall, and reconcile 215 vs 1 with an explicit attribution rule.

### M10 — The stated objective is not the implemented objective, and the "ranking only" defence does not hold

Eqs. (4)–(5) pose a constrained maximisation over artifacts. Alg. 1 does not solve it: it ranks families by the eq. (6) MDL heuristic and returns the **first** family that passes synthesis, contracts, and calibration (line 26). No optimality claim, no gap analysis, no comparison to the best-scoring admissible family. As written, §2.2 is decorative.

This matters because of §3.1's disclosure that two eq. (6) terms are unfaithful: ρ_eff, "intended as the declared-effect exposure," is approximated by *the fraction of tool names containing a namespace separator* — a naming convention, not a reading of the effect catalog — and |F| is substituted by the argument-slot count of the first observed window. The defence offered is "no admission decision depends on either." That is true per-candidate and false end-to-end: because Alg. 1 ships the first admissible family, **ranking determines which artifact is registered.** A different λ₂ could ship a different program.

**Required fix.** Either implement the objective (evaluate all admissible families, ship the argmax) or restate §2.2 as a design target and Alg. 1 as a greedy heuristic with that gap named. Fix ρ_eff to read the effect catalog — it is one lookup — and report whether the ranking order, and hence the shipped artifact, changes.

### M11 — Missing literature the architecture directly descends from

GAC is a **tracing JIT**: hot trace detection (family mining), guard synthesis (hard guard), specialised region compilation (bounded synthesis), and deoptimisation to the interpreter on guard failure (baseline fallback). The correspondence is close enough that the vocabulary is nearly shared, and the literature is uncited. Add and engage:

- Bala, Duesterwald & Banerjia, *Dynamo: a transparent dynamic optimization system* (PLDI 2000) — trace regions with guards and fallback.
- Gal et al., *Trace-based just-in-time type specialization for dynamic languages* (PLDI 2009); Bolz et al., *Tracing the meta-level: PyPy's tracing JIT* (ICOOOLPS 2009).
- On deoptimisation specifically: Hölzle, Chambers & Ungar, *Debugging optimized code with dynamic deoptimization* (PLDI 1992) — this is precisely §3.4.1's problem, and the JIT community's answer (explicit deoptimisation points) is exactly the "explicit control points with continuation tokens" the paper defers to §7.3.
- Effect systems: Lucassen & Gifford, *Polymorphic effect systems* (POPL 1988) — grounds "effect declarations are part of the trusted computing base."
- Selective prediction predates learn-then-test: Chow, *On optimum recognition error and reject tradeoff* (1970); El-Yaniv & Wiener on selective classification.

This is a framing gain, not a penalty: positioning GAC as "a tracing JIT for agent traces, where the guard must additionally certify effects and finite-sample risk" is a *stronger* and more legible claim than the current enumeration of five composed elements, and it makes the novelty easier to defend.

### M12 — Two safety gaps not covered by the threat model

1. **Guardrail elision.** §3.1 records guardrails as trace events and treats handoffs/approvals as barriers, but nowhere addresses that moderation, policy, and guardrail evaluations frequently execute *at model boundaries*. Deleting three of four model turns may delete three of four guardrail evaluations. The Ethics section's read-only policy does not cover this, and it is the most likely real-world objection from a deployment reviewer. Either show guardrails are re-run inside the permission facade, or add it as an explicit barrier condition.
2. **No adversarial evaluation of the guard.** With six of seven score weights zero, admission rests on H (types, fields, categorical sets, intervals, patterns, isolation keys, pins). The abstract motivates the work partly with "an input that merely *resembles* past traces may violate a permission or freshness constraint," yet no experiment attempts such an input. A small red-team suite — near-miss entry states designed to pass H while breaking semantics — is directly responsive to the paper's own motivation.
3. Relatedly: "a misdeclared external write cannot be repaired by statistics" (§7.2) is correct and currently a dead end. Propose a detection mechanism (sandboxed differential execution, syscall/network monitoring during replay, declaration-vs-observation diffing) even if unimplemented.

### M13 — Internal numeric and presentational inconsistencies

| Location | Issue |
|---|---|
| Table 1 vs §5.1 | Elapsed time **5.98 s** (table) vs **5.81 s** (text) for the same NESTFUL run. |
| §3.1 vs §5.2 | "any measured reduction must fall below [the ceiling]" vs measured 75.0% = ceiling 75.0%. |
| §4.3 vs §8 / App. D | 116 exact-contract traces vs 132/132 eligible (see M4). |
| Table 1 vs §5.1 | 215 no-candidate slots vs one blocking ungrounded slot (see M9b). |
| Table 3 | Row order A, B, C, E, F, D, E′, E″ — Demo D appears after F with no explanation; reorder or relabel. |
| Table 3 | Demo B quality is 0.97/0.97 in both arms and is never discussed — which of the five booleans failed, and why? |
| Table 3 | Demo D has n = 2 while all others have n = 4; unexplained. |
| Fig. 5 | E′ (+55.4%) and E″ (+54.5%) both rendered "−55%", losing the distinction the text relies on. |
| §5.1 | "H1 was **preregistered** as recovery above 90%" vs §8 "the study was **not externally preregistered**". |

### M14 — Title and abstract overclaim relative to what is measured

"**Preserve the Reasoning**" is not an evaluated property. What is preserved is conformance to a five-boolean registered contract; §5.4 finds byte-exact natural-language agreement of 1/6 (baseline) vs 0/6 (compiled), i.e. no evidence of preserved output stability, and the paper's own Table 5 marks the related claim "Contradicted." Meanwhile the subtitle, "**Guarded Specialization**", names TGWS — the pass the paper explicitly excludes from study ("We isolate GRC"), represented by a single demo (F). A title naming the unstudied pass and an unmeasured property is a real framing defect in an otherwise scrupulous paper.

Note also, in the other direction: calling C5 "**Contradicted**" on 0/6 vs 1/6 is itself overreach — at n = 6 the honest verdict is "not supported." Symmetry of rigour matters for negative claims too.

---

## 5. Gaps that must be filled

Ranked by value per unit of effort. G1–G4 are what I would require before acceptance.

| ID | Missing work | Why it is required | Effort |
|---|---|---|---|
| **G1** | **Latent-structure discovery study.** Task-level prompt where the agent may reorder, skip, or substitute reads. Report φ, family-support distribution, abstention rate, and end-to-end saving. | The paper's own nomination as "the single most important missing experiment" (§8). Without it, RQ2 is answered on a workload whose answer the prompt wrote. Resolves M2. | High |
| **G2** | **Risk–coverage evaluation with real error.** Dev/calibration/test sets containing hard-but-supported inputs, OOD entries, schema and source drift, stale versions, ambiguous provenance, partial tool failures. Publish the coverage/violation frontier at α ∈ {.02, .05, .10, .20} and report the number of positive examples in the score fit. | Turns the gate from a sample-size counter into a demonstrated mechanism. Resolves M1; partially M3. | Medium |
| **G3** | **Comparators.** Hand-written composite tool (mandatory); AWO-style meta-tool induction on the same traces (strongly recommended); plan caching. Report both efficiency and *what each fails to reject*. | Establishes superiority rather than intervention effect, and directly tests Table 4's central positioning claim. Resolves M8. | Low / Medium |
| **G4** | **Cache-aware cost accounting + counterbalanced timing.** Two-tier price model, measured cached-input share per arm, interleaved randomised condition order, ≥ 3 replicate blocks. | The dollar and latency headlines and the §5.3 negative result are all currently confounded. Resolves M5, M6, and the latency part of M7. | Low |
| **G5** | **α / δ / \|Λ\| sensitivity for the NESTFUL negative result.** Report, per family, the α at which it would certify. | The "zero certifiable families" result is highly parameter-sensitive and the paper presents it as near-structural. From the reported support distribution: the best family (support 26) certifies at **α ≥ 16.5%** under the 11-point grid — but at **α ≥ 8.5%** with a single threshold, and **α ≥ 12.3%** with a 3-point grid. So the 11-point grid roughly *doubles* the data requirement (92 groups vs 45 at \|Λ\| = 1) and is itself responsible for a large part of the negative result. That is a much more interesting finding than "none certified," and it suggests a concrete design change: use a coarse grid, a monotone/sequential procedure, or spend δ non-uniformly. | Low |
| **G6** | **External validity: ≥ 3 domains, ≥ 2 model families, ≥ 1 write-bearing and ≥ 1 stateful workload; sealed test of ≥ 100 pairs with a pre-declared non-inferiority margin.** | 18 pairs bound degradation only at 15.3%; one repo / one prompt / one model supports no generalisation claim. §8 concedes this; C2/C3 in Table 5 cannot be upgraded without it. | High |
| **G7** | **Scaling study.** Compile time and memory vs N episodes and T events, with the adversarial O(NT²) case constructed, plus a distributed-scale estimate. | 1,415 episodes at 5.9 s says nothing about the regime where amortisation makes GAC worthwhile (≥ 200 eligible episodes *per family*, many families). | Low |
| **G8** | **Exercise the safety architecture that is currently configured off.** Public-key registry signing enabled, immutable records, non-atomic save fixed, and one full shadow → canary → live lifecycle with rollback drill. | §8: "The immutability and signature-verification semantics described in §3 are therefore capabilities of the registry, not properties this experiment demonstrates." Fig. 1C currently depicts an unexercised path. | Medium |
| **G9** | **Effect-misdeclaration detection experiment.** Sandboxed differential execution or syscall/network observation during replay; report detection rate on deliberately misdeclared tools. | Converts "effect declarations are part of the TCB" from a disclaimer into a defended boundary. Addresses M12.3. | Medium |
| **G10** | **Adversarial guard evaluation.** Near-miss entry states constructed to satisfy H while violating semantics, permission, or freshness. | Directly tests the abstract's own motivating threat. Addresses M12.2. | Low |
| **G11** | **Determinism sub-study redone under controlled decoding** (fixed seed or greedy, or structured outputs), and at n ≫ 6. | Current 1/6 vs 0/6 measures provider sampling under default temperature (App. A.1 notes the model rejected an explicit temperature), not compaction. Addresses M14's C5 asymmetry. | Low |
| **G12** | **Global risk allocation across artifacts.** The union bound covers one frozen artifact's grid; App. B lists per-artifact risk control as residual debt. Specify and evaluate a portfolio-level allocation (Bonferroni over artifacts, or a hierarchical budget) before any multi-artifact deployment claim. | §3.3 and §8 both flag it; a fleet of artifacts is the only regime where the method pays for itself. | Medium |

---

## 6. Claims audit

Extending the authors' Table 5 with my independent verdicts.

| ID | Claim | Authors' verdict | My verdict | Note |
|---|---|---|---|---|
| C1 | Reconstructs nested value dependencies | Supported on basic-functions subset | **Partially supported** | Holds at 80.7% unique resolution / 84.3% precision, both honestly reported. The 96.3% recall figure is near-definitional and should be labelled as such (M9a). |
| C2 | A safe recurrent prefix can remove model decisions | Supported in one frozen-snapshot domain | **Supported as feasibility only** | The prefix was prescribed, not found; ceiling saturated exactly (M2). |
| C3 | Quality preserved on the sealed task | Supported; CI necessarily wide | **Not established** | 15.3% degradation bound; oracle cannot detect fabrication and folds conformance into quality (M3). |
| C4 | Selective certification is data-hungry | Supported negative result | **Supported but parameter-sensitive** | Flips at α ≈ 16.5% (11-point grid) or 8.5% (single threshold); sensitivity unreported (G5). |
| C5 | Compaction improves text determinism | Contradicted | **Not supported** (not contradicted) | 0/6 vs 1/6 at default temperature is uninformative in either direction (M14). |
| C6 | The artifact is production safe | Not supported | **Not supported** — agreed | Correctly and prominently disclaimed. |
| — | Token reduction ≠ cost reduction | Presented as a negative result | **Conceptually right, empirically confounded here** | Demo E's +8.3% sits inside a +55% ordering artifact the authors measured themselves (M6). Claim is safe on citation to [21, 29] and on Demo F; not on E. |
| — | Selective admission with normal retirement | Presented as contribution (v) | **Not demonstrated** | Gate never discriminates in either study (M1). |

---

## 7. Minor issues and editorial notes

**Technical / rigour (minor)**

- **Prop. 1 with random n_η.** n_η and k_η are both data-dependent. Because q is frozen and depends only on z, conditioning on the calibration entry states makes n_η fixed, which is the right formalisation — but the admitted groups then have *heterogeneous* violation probabilities, and a binomial bound on the mean of independent non-identical Bernoullis is not exactly valid in general. For k = 0 it survives (∏(1−p_i) ≤ (1−p̄)ⁿ by AM–GM), which is the case actually used — worth one sentence, because the k > 0 case a real deployment will hit needs a Poisson-binomial or Hoeffding treatment. State the conditioning explicitly in the proposition.
- **Tie-breaking in Alg. 3 line 17.** With a constant score, thresholds .14 … .50 all admit 92 groups, so `arg max cov` is a tie across seven thresholds. Specify the rule (smallest η? largest?) — it is currently unspecified and affects the registered artifact.
- **Δ in eq. (7)** is used as the deployment target reduction but is never defined; only Δ_max is. Define it, and note that the ceiling's ρ = 1 assumption makes it an equality-attainable bound (M2).
- **Eq. (6) notation.** s_F, k̄_F, c_m, H(F), λ₁₋₃ are introduced across two paragraphs and a figure; collect them, and give the λ values actually used (they are never reported).
- **"Likely invariants, not proofs"** (§3.2) is the right characterisation of V — carry that caveat into §5.2's presentation of zero violations, where it is load-bearing.
- Output-token means (119.3 → 50.6, Table 2) differ from App. D's −68.8 by 0.1; consistent under rounding (119.34 − 50.57 = 68.77) but worth one more decimal in Table 2 for auditability.
- App. B reports replay coverage at 65% — the lowest-covered module is the one that would have challenged the shipped artifact. Say so; it strengthens M3's honesty rather than hiding it.

**Presentation**

- **Add a notation/terminology table.** GAC, GRC, TGWS, PATG, Episode IR, canonical family, scenario group, compatibility key, manifest pin, hard guard, verifier, nonconformity score, live-in/live-out — twelve terms before §4. One table would materially reduce reading cost.
- **The abstract is over-packed.** Four dense paragraphs with fourteen numbers. Lead with the design principle and three numbers (−75% requests / 0 certifiable families / cost-token divergence); move the rest to §5.
- **Cut Fig. 3 and Fig. 5**, which restate Table 2 and Table 3 without adding information. Spend the space on the risk–coverage curve from G2 — currently the paper's most conspicuous missing figure.
- **Fig. 6** plots three different quantities on one "Rate or reduction (%)" axis; split or annotate.
- **Prose density.** Nominalisation chains ("the compaction-and-prompt-caching interaction", "declared-effect exposure of the region") are frequent. The writing is precise but effortful; a pass converting nominalisations to verbs would help without losing rigour.
- **§7.3 lists seven extensions, none implemented.** Trim to the two that follow from results (cache-prefix pricing, cached-baseline break-even) and move the rest to a short outlook sentence.

**Artifact / reproducibility**

- **No artifact locator.** The "Artifact Availability" section describes the package but gives no URL, DOI, or archival identifier. This must be fixed; as written the section cannot be acted on.
- **No `.git` metadata** (App. A.1, §8), so commit/branch/CI state is unverifiable. Ship a signed tag or an archived tarball with a digest.
- Pin the price table *as a file* in the artifact, not only as a dated URL — pricing pages change and the cost claims depend on it.
- `gpt-5.6-luna` at "low reasoning effort" with provider-default temperature: state whether the model is generally available, since the live study is otherwise unreproducible.
- App. A.2 gives commands but no expected-output digests; add them so a re-runner can tell success from silent divergence.

---

## 8. Prioritised recommendations

**Before resubmission (required)**

1. Run the latent-structure discovery study (**G1**) — reframe §5.2 as feasibility until it exists.
2. Fix the score: report positive-example counts, rebuild the dev set with real error, publish a risk–coverage curve (**G2**, resolves **M1**).
3. Run the perturbation suite on the shipped artifact and separate contract induction from violation adjudication (**M3**).
4. Add the hand-written composite-tool baseline (**G3**) — cheap, and it is the comparison a practitioner will make immediately.
5. Recompute cost with a two-tier cache-aware model; counterbalance run order (**G4**, resolves **M5**, **M6**).
6. Reconcile 132 vs 116 and publish the split rule and flow diagram (**M4**).
7. Unify the statistical procedure; drop the degenerate requests p-value; 10,000 bootstrap resamples; replace "preregistered" with "pre-specified internally" (**M7**).
8. Add the α/δ/|Λ| sensitivity table (**G5**) — one afternoon, and it converts a brittle negative into a design insight.
9. Retitle. Something like *"Guarded Region Compilation for Tool-Using Agents: Typed Provenance, Effect Barriers, and Selective Admission"* — names what is studied, drops the unmeasured property and the out-of-scope pass (**M14**).
10. Add the tracing-JIT / effect-system / selective-prediction citations and reframe the contribution as a guarded trace JIT for agent execution (**M11**) — this *strengthens* the novelty story.

**Strongly recommended**

11. Guardrail-elision analysis and an adversarial guard suite (**M12**, **G10**).
12. Fix ρ_eff to read the effect catalog; either implement eq. (4) or restate it as a design target (**M10**).
13. Enable registry signing and run one full lifecycle drill (**G8**).
14. Redo the determinism sub-study under controlled decoding (**G11**).

**For a subsequent paper**

15. Multi-domain, multi-model, write-bearing evaluation with a pre-declared non-inferiority margin (**G6**).
16. Global risk allocation across an artifact portfolio (**G12**).
17. Transactional compilation of idempotent writes behind approval barriers — the natural next region class, and the one that would widen the addressable surface beyond read-only position-0 prefixes.

---

## 9. Questions for the authors

1. How many *positive* (unproductive) examples were in the logistic fit for q(z)? If zero, on what basis is q described as a trained score rather than a constant?
2. What happened to the 16 eligible-but-unassigned discovery episodes, and was the 16/8/92 split rule fixed before outcomes were observed?
3. Why did the perturbation suite not run for the shipped artifact, and what changes if it does?
4. Table 1 reports 215 slots with no candidate; §5.1 reports one ungrounded slot blocking a window. What is the attribution rule?
5. Which Wilcoxon variant is used in each row of Table 2, and why does it differ across rows?
6. What is the measured cached-input share of the GitHub baseline arm, and what is the cost saving under cached pricing?
7. Which of the five quality booleans fails in Demo B (0.97), and why is Demo D n = 2?
8. Do guardrail and moderation evaluations execute at model boundaries in the studied runtime, and if so are they preserved under compaction?
9. Is 5.98 s (Table 1) or 5.81 s (§5.1) the NESTFUL elapsed time?
10. Where is the artifact?

---

## 10. Reviewer assessment

**Summary judgement.** This is a careful, self-critical systems paper whose *ideas* are ahead of its *evidence*. The framing — that a workflow optimizer must supply an admission argument, not just a rewrite — is correct and, as far as I can tell from the cited landscape, not stated this crisply elsewhere. The engineering artifact appears real and reasonably tested. The honesty is exceptional: an archived failed pilot, a claims register with two self-refuted rows, and §3.4.1's admission that clean fallback is unachievable on one of the two integration paths.

But the paper's two loudest claims are hollow at the centre in ways the authors have already documented and then reported past. The −75% figure comes from a workload whose prompt dictates the compiled structure, and it lands exactly on a feasibility ceiling that the paper says measurements must fall below. The risk gate — the element that distinguishes GAC from a macro miner, and the paper's own strongest novelty claim — never discriminates between inputs in either study, apparently because its score was fit without positive examples. Fill G1–G4 and this becomes a clear accept; the required work is well-scoped and the authors have plainly already thought about all of it.

Two further notes for the authors' encouragement. First, the NESTFUL negative result is more interesting than you present it: with the sensitivity analysis in G5, "recurrence is not certifiable" becomes "certifiability is governed by the grid you chose, and an 11-point grid doubles your data requirement" — a design finding others can act on. Second, the tracing-JIT reframing in M11 costs you nothing in novelty and buys a great deal in legibility; the deoptimisation literature has already solved §3.4.1's problem, and citing it turns your most awkward limitation into a known engineering pattern with a known fix.

| | |
|---|---|
| **Overall score** | **65 / 100** |
| **Recommendation** | **Major revision** |
| **Confidence** | High on formulation, mathematics, statistics, and internal consistency (all reported numbers independently recomputed). Medium on novelty relative to the 2026 arXiv literature, several items of which I could not inspect. Low on artifact quality — the package was not available to me. |
| **Reviewer conflicts** | None. |

### Verification performed for this review

Every quantitative claim below was recomputed from the paper's own reported inputs before being used above.

| Check | Paper | Recomputed | Verdict |
|---|---|---|---|
| Gate minimum from α=.05, δ=.10, \|Λ\|=11, k=0 | 92 groups | 91.64 → 92 | ✓ |
| Simultaneous bound at n=92, k=0 | 0.0498 | 0.049809 | ✓ |
| Clopper–Pearson k=0 closed form | 1 − (δ/\|Λ\|)^(1/n) | correct inversion of Beta⁻¹ | ✓ |
| One-sided degradation bound, 0/18 | 15.3% | 15.332% | ✓ |
| Table 2 percentage changes (7 rows) | as printed | −75.0 / 0.0 / −65.9 / −57.6 / −65.7 / −84.9 / −52.6 | ✓ |
| App. D paired differences vs Table 2 means | consistent | consistent to rounding | ✓ |
| NESTFUL slot arithmetic | 4636+895=5531; 5531+215=5746 | exact | ✓ (and reveals M9a) |
| NESTFUL window failures | 1415−1207=208=207+1 | exact | ✓ |
| Family accounting | 32−12=20, split 10/10 | exact | ✓ |
| Feasibility ceiling, GitHub study | "measurement must fall below" | Δ_max = 0.750 = measured 0.750 | ✗ **M2** |
| Table 2 p-values, single procedure | implied | three distinct variants (exact 7.63e-06; approx 1.96e-04; tie-corrected approx 2.21e-05) | ✗ **M7** |
| Split accounting | 132 eligible, 116 assigned | 16 unaccounted (= \|train\|) | ✗ **M4** |
| Break-even | ~233 episodes | 176 (requests) / 207 (tokens) / 233 (dollars, discovery only) / 292 (incl. confirmatory) | ✗ **M5** |
| NESTFUL elapsed time | 5.98 s (Table 1) / 5.81 s (§5.1) | inconsistent | ✗ **M13** |
| α at which best NESTFUL family certifies | not reported | 16.5% (\|Λ\|=11) / 12.3% (\|Λ\|=3) / 8.5% (\|Λ\|=1) | gap **G5** |
| Calibration cost of the grid | not reported | 92 groups (\|Λ\|=11) vs 45 (\|Λ\|=1) at α=.05 | gap **G5** |
