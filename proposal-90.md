# proposal-90.md — Deep review of the ICLR 2027 submission and a feasible plan to 90+

Prepared 2026-10-02 against `paper/iclr/main-final.pdf` (36 pages; main text ends on page 9),
`paper/iclr/sections/*.tex`, `paper/iclr/appendix.tex`, the 27 ICLR tables, the retained
results under `paper/results/`, the compiler source under `src/guarded_agentic_compaction/`,
and every prior review and plan in the repository (`paper/paper-review.md`,
`paper/reviews/GAC_paper_review.md`, `paper/reviews/GAC_ICLR_2027_Detailed_Revision_Plan.md`,
`paper/supplementary/review-score-90-plus-plan.md`, `paper/supplementary/quality-assessment.md`,
`paper/iclr/notes/*.md`, `improve-iclr.md`, `iclr-paper-sharping-paln.md`).

The scale throughout is 0–100, read as "probability-weighted standing at a top venue": 90+
means a paper that a careful area chair would defend as a clear accept without needing the
authors' rebuttal to rescue it.

---

## 0. Bottom line

| | Score |
|---|---:|
| Where the paper stands today, read as an ICLR reviewer who did not build it | **76** (ICLR 5–6, borderline) |
| After the provider-free work in Phase 0 (two weeks, $0) | ~82 |
| After Phases 0–2 with the two cheap live studies positive | ~88 |
| After Phases 0–3 (adds a second live domain and end-to-end calibration labels) | **90–93** |

The repository's own reviews score the paper at 91–94. Those scores credit the artifact
(which deserves 95+) and the honesty of the writing (which deserves 95+). They do not model
how a reviewer who reads only the nine pages experiences the paper, and they under-weight
four problems that the same repository documents in its own notes. Those four problems are
what this plan fixes:

1. **The certificate does not bound what the paper says it bounds.** §2 defines the loss
   $L$ end-to-end ("a sound prefix whose baseline continuation errs still contributes
   $L=1$, so the gate certifies end-to-end compliance under substitution"). The
   implementation labels a calibration violation as a *recorded-output mismatch or verifier
   failure of the deterministic tool region*
   (`src/guarded_agentic_compaction/grc/compile.py:683-705`,
   `grc/calibrate.py:14-16`). Downstream answer misses, which are the only misses that ever
   occur on these families, never enter $k_\eta$. The revision log already says so in
   passing ("every calibration label in the paper is a replay-contract violation on
   deterministic tools and there have been none"). A statistics-literate reviewer will find
   this, and it converts the paper's strongest sentence into its weakest.
2. **The gate is carrying a component that does nothing, and paying for it.** The learned
   score $q$ never ranks, the paper says so, and the 11-point grid it needs costs a
   Bonferroni factor of 11. Under a single pre-registered threshold the same retained
   tables give compiler-wide certificates for all three primary families at $m=2$
   ($U=0.032$ at 92 groups) and the cluster-level bound by author admits rather than
   retires. See §5 for the arithmetic. That is not a trick; it is the design the paper's
   own evidence says it should have had.
3. **No held-out result shows a guard preventing a failure.** Every "guard caught it" row in
   the mechanism-removal table is a retrospective counterexample, and the one live
   recurrence-only ablation found the refusal bought *no* measured quality. The drift
   protocol that would answer this has been pre-registered since 2026-08-18 and never run.
   It costs under $5.
4. **The nine pages are hard to read and the related work is 116 words.** The paper has
   zero result figures in the main text, 27 appendix tables, a contribution list that
   cannot be summarized in one sentence, and 26 references. Clarity and positioning are
   where the cheapest points are.

Everything below is sized so that the whole plan fits in roughly five weeks of part-time
work and under $100 of provider spend at list prices, with every live study pre-registered
under the repository's existing protocol discipline.

---

## 1. How this review was done, and why the number differs from the repository's

I read the compiled PDF page by page, the LaTeX of every section and the appendix, every
ICLR table, the two algorithm files in the main text, the calibration and compile source,
the retained compiler reports for the three families, the recorded spend, and all prior
review and plan documents. I recomputed every admission bound quoted in this document with
`scipy.stats.beta` (§5).

Calibration note. `GAC_paper_review.md` (94) and `quality-assessment.md` (91) are
artifact-aware rubrics: they award 97–99 on reproducibility and engineering and let that
lift the composite. `review_scorecard.md` (2026-08-21), which follows the official ICLR
reviewer questions, lands at **7/10 weak accept** after revision and lists the same residual
risks this document does. An ICLR composite does not let artifact quality offset soundness
and clarity, so 76 is the honest translation. The 76 is not a judgment on the work; it is a
judgment on how the work currently reads.

---

## 2. Deep review

### 2.1 What is genuinely strong (keep every one of these)

- The research question is right and durable: recurrence proposes, admissibility decides.
- The two concrete counterexamples (#4420 ungroundable slot, #6602 clean replay / wrong
  answer) make the abstract idea tangible in half a page.
- The compile-or-retire cascade with hard barriers that no statistic can override, and the
  position invariant learned from a real pilot fault.
- The refusal results on NESTFUL, API-Bank, and executed BFCL, with the binding stage named
  and the arithmetic settled before the compiler ran; AppWorld's admissible-versus-
  dispatchable split is a real observation about agent architectures.
- A manual comparator with full workflow knowledge, reported even where it wins.
- Second model and second provider replications that re-derive two artifacts and refuse the
  third from each model's own traces.
- The artifact: pinned manifests, retained raw results, signed catalogs, a validator with
  3,523 checks, a claims-to-evidence register, an anonymous archive builder.

### 2.2 Findings, ranked by how much they cost at review

Each finding names where it lives and what the fix is. "Cost" is my estimate of the score
the finding currently removes.

| # | Finding | Where | Cost |
|---|---|---|---:|
| F1 | **Certified event ≠ stated objective.** Eq. (4)'s constraint and Prop. 1 are stated for the episode-level loss $L$; $k_\eta$ counts only tool-region replay/verifier violations. On deterministic reads of a pinned snapshot that event is structurally near-impossible, which is *why* every gate is a step function and why "there have been none." The abstract's "exact finite-sample bounds" therefore describes a bound on an event that cannot occur, while the misses that do occur (excerpt fidelity: 1/210 compiled-only on the calibrated model, 4 on Sonnet) are outside the certificate. | §2 last paragraph; §3 stage 6; `compile.py:683-705` | 6 |
| F2 | **Two of three headline artifacts carry per-candidate certificates only** ($m=2$, corrected $U=0.0569$), disclosed in the abstract itself. Disclosure is honest but places the paper's weakest fact in its first 200 words. The pre-registered 106-group repair was a NO-GO for lack of records. | Abstract; §5.1; App. A | 4 |
| F3 | **The learned score $q$ is dead weight.** It is fitted on abstention-shaped labels, is constant within a repository on the cross-repo task, never produced graded coverage, and the paper concedes the registered pools cannot certify any coverage but 0 and 1. Yet it remains in the method statement, Alg. 2, Prop. 1, and costs $|\Lambda|=11$ in the union bound. A reviewer reads this as a method with an unmotivated component. | §3 stage 6; Alg. 2; App. C; App. H | 4 |
| F4 | **The i.i.d. assumption fails its own sensitivity check.** Treating a creation day or an author as the unit retires the bound in every family (Table 17). The paper says so and stops. | §7; App. G | 3 |
| F5 | **No held-out evidence that guards buy anything.** The mechanism-removal table is retrospective. The one live ablation (recurrence-only, issue-type) is 30/30 at one request per record, cheaper than GAC. The drift-robustness protocol that isolates the induced verifier is unrun. A reviewer's summary will be "the guards are insurance with an unmeasured premium and an unmeasured payout." | App. G; `drift-robustness-ablation-protocol.md` | 6 |
| F6 | **Effect size is small in absolute terms and manual code ties.** The 90-record compiled evaluation cost \$0.028 against \$0.068. Hand-written programs reach 90/90, tie on requests, and win on tokens and dollars. The paper's answer (discovery and maintenance) is asserted, not measured. | §5.1; Table 9 | 4 |
| F7 | **External validity rests on one repository snapshot.** All richer evidence is one pinned GitHub snapshot (7,440 records); the cross-repository task is a two-read template a fixed program matches; all external substrates retire or admit an argument-free two-call program. The multidomain pools (420 vulnerability, 420 HMDA groups) have passed provider-free gold validation since 2026-08-04 and have never been run. | §4; §5.2; `paper/results/multidomain/` | 5 |
| F8 | **Clarity.** The intro reaches `record(4420)` and `limit=100` before defining a prefix, a witness, or a family. The abstract contains "(two of three primary families, whose corrected bound is 0.057)". §3 stage 6 is a wall of thresholds. The main text has no results figure; Figure 1 is set at 0.52 linewidth and is unreadable at print size. Five near-synonyms (region, candidate, family, artifact, program, prefix) rotate without a glossary. The appendix has 27 tables and four claims-register pages. | throughout | 8 |
| F9 | **Related work is 116 words and 26 references.** Missing threads a reviewer will name: process mining of event logs (the literal precedent for "family mining"); selective prediction and conformal/risk-control lineage beyond LTT; LLM-call caching and memoization; speculative tool execution; skill libraries (Voyager, SkillWeaver); partial evaluation and meta-tracing (Futamura, PyPy); tool-use safety evaluation (ToolEmu, AgentDojo); trace-based optimizers (Trace, TextGrad). | §6 | 5 |
| F10 | **Novelty framing.** "To our knowledge the first exact finite-sample admission certificate for trace-derived agent compilation" invites the reply that it is Clopper–Pearson with a union bound. The novelty is the admissibility *composition* and the refusal discipline; the paper should claim that and not the inequality. | §1 contribution 1 | 2 |
| F11 | **Minor consistency items.** The abstract's "90 unseen test cases" vs. the extended 210; §5.3 "settled arithmetically before the compiler ran" reads as if the compiler was unnecessary; the reproducibility statement's "will be supplied as an anonymous archive" is now done (`build_anonymous_archive.py`); Table 2's p/a/w column mixes two partitions and needs a footnote at the table, not a pointer. | various | 1 |
| F12 | **Working-tree anomaly, not a paper finding.** The current checkout carries an uncommitted edit to `paper/supplementary/second-provider-replication-protocol.md` that deletes the "Observed results" section and resets the status to "Not run," while `tables/second_provider.tex`, Appendix G, and the abstract still report that run. I did not touch it. If it is intentional, the paper and the protocol will contradict each other; if not, discard it. | git status | — |

### 2.3 Scorecard, now and at target

ICLR-style weights. Target values assume the plan below completes with the live studies at
or near their expected outcomes; §7 gives the scenarios where they do not.

| Dimension | Weight | Now | Target | What moves it |
|---|:-:|:-:|:-:|---|
| Problem and motivation | 5 | 85 | 88 | prevalence/absolute-savings framing (WS-E) |
| Novelty and positioning | 15 | 78 | 86 | composition claim + comparison table (WS-F) |
| Technical soundness | 20 | 74 | 90 | F1, F2, F3, F4 (WS-A, WS-B, WS-G) |
| Empirical rigor | 20 | 76 | 90 | drift study, time-forward cohort, second domain (WS-C, WS-D) |
| Significance | 10 | 70 | 86 | guards shown to prevent silent errors; authoring cost (WS-C, WS-H) |
| Clarity and presentation | 10 | 62 | 88 | rewrite, figures, appendix diet (WS-E) |
| Reproducibility | 10 | 95 | 96 | archive already built |
| Honesty and limitations | 5 | 96 | 96 | keep |
| Related work | 5 | 60 | 88 | WS-F |
| **Weighted** | | **76.5** | **≈89.9** | |

The target composite crosses 90 only if WS-A through WS-E all land. WS-F through WS-H are
what give margin.

---

## 3. Design decisions this plan commits to

These are the three decisions that change the paper's shape. Everything else is execution.

**D1. The gate's certified event is the tool-region contract, and the paper says so
everywhere.** Eq. (4), Prop. 1, Alg. 2, the abstract, §5.1 and §7 state the bound for
$W$ = "dispatched and the compiled region's replay or verifier contract was violated."
End-to-end preservation is reported as an empirical held-out result with its own exact
bound (currently 1/210, 2.2 %). An end-to-end *certificate* is then pursued as a separate,
pre-registered experiment (WS-A2) whose data demands §5 computes. This resolves F1 without
a single provider call and is the one change that cannot wait.

**D2. The admission rule in the main text becomes a single pre-registered threshold.**
With $|\mathcal{K}|=92$ the only certifiable coverages are 0 and 1, so the operative rule
*already is* "dispatch on every guard-passing group." Writing the method that way removes
$q$ and the grid from the main text, drops the Bonferroni factor from 11 to 1, and makes the
zero-violation floor 45 groups ($m=1$) or 59 ($m=2$) instead of 92 or 106. The learned
score and the graded-frontier protocol move to an appendix as the extension they are. For
the already-run studies this is reported as a **sensitivity analysis** (the registered
certificates stand as printed; the simplified design is one the retained tables cannot
distinguish from the registered one because every admitted threshold had coverage 1). For
every new run in this plan the single-threshold design is pre-registered and primary.

**D3. Every new live study is small, pre-registered, and has a decision rule under which a
null is a reportable result.** The repository already does this well. The plan adds no
study whose only useful outcome is positive.

---

## 4. Workstreams and task cards

Priority: P0 = required for 90; P1 = required for margin; P2 = valuable if time permits.
Track: **S** provider-free (writing or re-analysis of retained data), **L** live provider
calls (each with a spend cap), **H** human time. Costs are list-price estimates from the
retained per-record costs (baseline ≈ \$0.0008/record, discovery traces ≈ \$1–4 per family
on OpenAI, more on Anthropic); every L task sets `--approved-spend-usd` at twice the
estimate and stops there.

### WS-A — Make the certificate say what it bounds (P0)

**A1. Align text with implementation.** Track S. 1 day.
- §2: redefine $W_A(G)$ as the tool-region contract event; keep $L$ as the reported
  end-to-end quality metric but remove "the gate certifies end-to-end compliance under
  substitution." Add one sentence: "the gate certifies the substituted region; the
  continuation remains the model's and is measured, not certified."
- §3 stage 6, Alg. 2 input line, Prop. 1 statement, App. A first paragraph, abstract
  sentence 3, §5.1, §7: same change, same words.
- App. C: add the exact definition of a violation as the code computes it
  (`recorded_output_mismatch`, `recorded_output_missing`, `verifier:*`) and state that no
  such event has been observed in any calibration pool, which is why every gate is
  step-like. This converts F1 from a hidden inconsistency into a stated scope.
- Done when: `grep -n "end-to-end" paper/iclr/sections/*.tex paper/iclr/appendix.tex`
  returns only sentences that describe empirical results; `validate_artifacts.py` passes.

**A2. End-to-end calibration labels, pre-registered.** Track L, ≈ \$2–6. 3 days incl. protocol.
- Goal: the first certificate whose event includes the continuation.
- Design: for each calibration group of issue-type routing (the $m=1$ family), dispatch the
  retained artifact, run the unchanged continuation once, grade the exact contract; a miss
  is a violation. Under D2 at 92 groups, $k=1$ admits at $m=1$ ($U=0.0416$) and $k\ge2$
  retires. Pre-register both outcomes. If WS-C2's time-forward cohort lands first, run A2
  on its larger pool instead (at 132 groups, $k\le3$ admits; §5).
- Expected: the calibrated model misses excerpt fidelity on roughly 1–2 % of records, so
  issue-type has a fair chance of admitting at 92 and a good chance at 132+. PR-outcome and
  backlog ($m=2$) need 93 groups for $k=1$ and are run only on the time-forward pool.
- Files: new `paper/supplementary/end-to-end-calibration-protocol.md`; new
  `paper/scripts/end_to_end_calibration.py` (reuses the continuation harness in
  `github_workflow_family_study.py`); results under
  `paper/results/end_to_end_calibration/<family>/`.
- Decision rule: report the per-family $k$, $n$, $U$ under D2 first; an admission is a
  new sentence in §5.1; a retirement is a new row in the refusal narrative and the paper
  states the pool size that would be needed.
- Done when: results JSON is pinned by a new validator family and the table is generated,
  not typed.

### WS-B — Simplify the gate to the rule the evidence supports (P0)

**B1. Single-threshold re-analysis of every retained gate table.** Track S. 1 day.
- Recompute $U$ for the seven registered artifacts and the retained dominated candidates
  from `compiler.artifact.gate.notes` with $\gamma=\delta$ ($m=1$) and $\gamma=\delta/2$
  ($m=2$). Expected from the retained 92/0 tables: $U=0.0247$ and $0.032$. Also recompute
  the cluster-level bounds of Table 17 under the same design: by day every family admits;
  by author all three primary families admit ($0.0376$ at 82, $0.0487$ at 60 under $m=2$)
  and only `streamlit/streamlit` (25 authors) retires.
- Report as a sensitivity table in App. C ("Certificate under a single pre-registered
  threshold"), with one honest paragraph: this design was not registered for these runs,
  so the registered certificates are unchanged; it is adopted prospectively.
- Files: extend `paper/scripts/iclr_revision_statistics.py` with a `single-threshold`
  subcommand writing `paper/iclr/tables/single_threshold_sensitivity.tex`; add validator
  checks; add the arithmetic to `paper/iclr/notes/number_registry.md`.

**B2. Rewrite §3 stage 6 and Alg. 2 around the single threshold.** Track S. 2 days.
- Main text: "Admission: dispatch on every group the hard guard and verifier accept;
  admit iff the exact one-sided binomial upper bound on the tool-region violation rate
  over $n$ calibration groups is $\le\alpha$ at confidence $1-\delta$, Bonferroni-split
  over the $m$ candidates that reach calibration." One equation, one floor
  ($n\ge45$ at $m=1$, $59$ at $m=2$, zero violations), Prop. 1 unchanged in substance
  with $|\Lambda|=1$.
- $q$, the grid, the gate-floor figure, and the graded-frontier material become App. C.2
  "A selective extension and why these pools cannot exercise it."
- Reclaims roughly 25 lines of page 6 for WS-E.
- Done when: the main text contains no $\Lambda$, no 0.0498, and no 92 except in the
  sensitivity sentence that says what the registered design required.

**B3. Make D2 the default in code, behind a flag.** Track S. 1 day.
- `grc/calibrate.py`: add `grid=("single",)` mode; the registered 11-point grid stays
  available and is the recorded setting for the retained runs. Unit tests for both.

### WS-C — Show, on held-out data, what the guards prevent (P0)

**C1. Drift-robustness ablation on recorded GitHub traces.** Track L, ≈ \$3–8. 4 days.
- The pre-registered protocol exists (`drift-robustness-ablation-protocol.md`) on the
  deterministic demo substrate. Extend it, before any run, to the 90 primary held-out
  records in recorded-replay mode: perturb the recorded tool outputs with the nine
  metamorphic families already in `evaluation/perturb.py` (reorder, duplicate, formatting,
  empty lists, null fields, schema drift, tool 4xx, timeout, pad lists).
- Four arms on identical perturbed episodes: `compiled_guarded`, `compiled_unverified`
  (same program, permissive verifier), `manual_unverified`, and `recurrence_only_replay`
  (the arm the issue-type ablation used). The continuation is one provider call per
  episode-arm; 90 × 9 × 4 = 3,240 calls at ≈ \$0.001.
- Endpoints, fixed in advance: silent wrong answers (contract miss with no abstention)
  per arm per family; clean abstentions followed by baseline success; the two-by-two
  table guarded-vs-unverified on the same episodes with an exact McNemar test.
- Decision rule: (i) guarded abstains where unverified answers wrongly on at least one
  perturbation family, with McNemar $p<0.05$ pooled — the guards buy safety under drift,
  priced by the clean-abstention rate; (ii) no difference anywhere — the paper states that
  on these families the induced verifier has not been shown to add safety and the
  guards' value rests on the retrospective hazards; (iii) guarded itself answers wrongly
  under a perturbation — reported first, as an adverse finding.
- Why this is the single most valuable experiment: it is the only one that can turn the
  guards from a design argument into a measured result, and both outcomes are publishable.
- Files: protocol update; new `paper/scripts/drift_robustness_ablation.py`; results under
  `paper/results/drift_robustness/`; table `tables/drift_robustness.tex`; a results
  figure (WS-E4).

**C2. Time-forward cohort on the same three families.** Track L, ≈ \$10–25. 5 days.
- Acquire a newer snapshot of the pinned repository (records created after the retained
  snapshot's revision `e344be7b…`). Preflight, provider-free: count unused records per
  class per family; the design is GO for a family only if it supplies ≥ 60 held-out
  records class-balanced **and** ≥ 93 calibration groups with distinct creation days and
  authors (so the cluster-level bound is primary, not a sensitivity), and NO-GO is
  committed as a result otherwise. The retained NO-GO shows `open` PRs and `owned` backlog
  issues are the scarce classes; expect issue-type and PR-outcome to be GO and backlog to
  be the risk.
- Arms: unchanged agent, retained artifact dispatched under its manifest pins (no
  recompilation), hand-written program. This is the natural-drift test the paper currently
  lacks: the artifact was calibrated on an older snapshot, so every guard clause and hull is
  exercised against genuinely newer data.
- Outputs: (a) time-forward preservation per family; (b) a fresh calibration pool that
  gives compiler-wide certificates under D2 at $m=2$ (59 groups) and, if ≥106 groups, also
  under the registered design, closing F2 without the discarded repair; (c) the pool WS-A2
  uses for end-to-end labels; (d) the cluster-robust bound at distinct-day and
  distinct-author units as the **primary** certificate.
- Decision rule: compiled-only misses reported first; a guard-clause abstention rate above
  20 % on held-out is reported as the price of pins; a family that retires at calibration
  on the new pool is a result.
- Files: `paper/supplementary/time-forward-cohort-protocol.md`; extend
  `github_workflow_family_study.py` with `--snapshot` and `--frozen-artifact`; results under
  `paper/results/github_workflow_families/<family>/time_forward/`.

### WS-D — A second live domain (P1, the main source of margin)

**D1. HMDA family under the frozen multidomain protocol.** Track L, ≈ \$10–30. 6 days.
- 420 real, privacy-modified public HMDA groups pass independent provider-free gold
  reconstruction with 416/420 variable paths; the runner (`multidomain_study.py`), the
  frozen-protocol machinery, pricing manifest, and macro-approval gates exist; no provider
  call has been made. Choose HMDA over vulnerability because vulnerability's 11 % variable
  path makes compaction trivial.
- Design: 132 discovery, 92 calibration (D2 primary), 60 held-out, class-balanced over the
  record-interpretation outcomes the gold defines; the independently reviewed macro is
  the manual comparator the protocol already requires. Candidate freezing on. Entry state
  carries more than one integer, so this is also the first cohort where $q$ *could* vary
  (report that observation in App. C.2 but make no frontier claim).
- Why it moves the score: it is the first live family outside GitHub, outside one
  snapshot, with a different tool vocabulary and answer contract, and it comes from a pool
  large enough that A2's end-to-end labels tolerate $k\le3$ at 132 groups.
- Decision rule: compile-or-retire reported as such; if HMDA retires at provenance or
  synthesis (its paths are variable), that is a refusal result on a real-record domain and
  belongs in §5.3's funnel as a fifth row.
- Prerequisite: a human-signed macro approval file, which the protocol requires and which
  only the author can supply.

### WS-E — Rewrite for a reader who has nine pages (P0)

**E1. Abstract.** Track S. One sentence each: problem, method rule, certified event (D1),
headline live result (90/90 vs 89/90, 66.6 % fewer requests), transfer and refusal, one
sentence on replications. Remove the 0.057 clause and the 90-unseen-vs-210 ambiguity.
Six numbers maximum.

**E2. Introduction.** Open with the general loop and the three obligations (grounding,
effects, finite-sample risk) in plain language before any record number. Then #4420 and
#6602 in one paragraph each with Figure 1 at full column width. Contributions reduced to
three: (i) the admissibility cascade with a certified tool-region contract and refusal as
the default output; (ii) live evidence: three families, time-forward, drift, two models,
two providers, one second domain; (iii) calibrated refusal on four external substrates
and the admissible-versus-dispatchable split.

**E3. Numbers budget.** Cut the count of distinct numerals in §1–§7 by half. Every
threshold, bound, and group count that is not a headline moves to App. C. A reader should
leave §3 knowing: hard guards, bounded synthesis, exact zero-violation floor at 45/59
groups, retire otherwise.

**E4. One results figure in the main text.** Three panels: per-family resource reductions
(exists as `family_reductions.pdf`), the refusal funnel across the five substrates (new,
replaces part of Table 2's prose), and the drift result from C1 (silent-wrong versus
clean-abstain per arm). Place on page 7 or 8 where Table 1 and Table 2 currently sit.

**E5. Appendix diet.** From 27 tables to at most 14 in the PDF: keep proof, algorithms,
configuration manifest, absolute resources, paired statistics, discordance, manual
resources, funnel detail, AppWorld dispatch, second model, second provider, effective
units, drift, time-forward. The four claims-register tables, the external evidence map,
the gate profile, the multiplicity accounting, the prologue table, and the gate-frontier
table move to the supplementary archive with a one-page index in the appendix. The
appendix opens with a half-page reading guide.

**E6. Terminology.** One glossary box (eight terms) at the start of §2: episode, group,
family, candidate, region, program, artifact, prefix. Use each consistently; "compaction"
for the runtime act, "compilation" for the offline act, never "specialization" except in
the title's sense.

**E7. Page budget.** B2 and E3 free roughly 35 lines; E4 costs about 20. Validate with the
existing page-9 check.

### WS-F — Related work and positioning (P1)

**F1. Expand §6 to about 0.6 page in five threads**, with a four-column table (system;
what it removes; admissibility decision; guarantee and fallback):
1. Trace JITs, deoptimization, meta-tracing, partial evaluation: Dynamo, Hölzle, PyPy/Bolz,
   Futamura, Jones–Gomard–Sestoft.
2. Mining workflows from logs: process mining (van der Aalst), programming by
   demonstration, program synthesis from traces; FlashFill and sketching stay.
3. LLM agent reuse and caching: AWM, plan caching, EvoC2F, Agent JIT, FlowCompile,
   AgentSlimming, GPTCache/semantic caching, speculative tool execution, skill libraries
   (Voyager, SkillWeaver), DSPy/GEPA/Trace/TextGrad as optimizers of a different quantity.
4. Selective prediction and distribution-free risk control: Geifman & El-Yaniv, Vovk et al.,
   RCPS (Bates et al.), conformal risk control and LTT (Angelopoulos et al.),
   Clopper–Pearson.
5. Tool-use safety and effects: effect systems (Lucassen–Gifford), ToolEmu, AgentDojo,
   τ-bench, and the benchmark line (BFCL, ToolLLM, AppWorld, NESTFUL, API-Bank).
Target ≈ 45 references, each resolved and cited.

**F2. Reword the novelty sentence** (F10): claim the admissibility composition and
compile-or-retire discipline; cite LTT and Clopper–Pearson as the tools, not the
contribution.

### WS-G — Statistical hygiene (P1)

**G1.** Replace "i.i.d." with "exchangeable" where that is the assumption actually needed
and state the unit (record, day, author) at every bound; make the cluster-level bound at
author units the primary certificate for every cohort where it admits under D2 (all three
primary families), and the record-level bound the sensitivity.
**G2.** Report the 1/210 compiled-only bound and the 4/60 Sonnet misses in one
"end-to-end preservation" table so the empirical quality claim has one home.
**G3.** One sentence on why McNemar $p=1$ with one discordant pair is not evidence of
equivalence, which the text already implies but should say.

### WS-H — Price manual authoring (P2)

**H1. Timed authoring study.** Track H, 1–2 days of three to five engineers, \$0.
Each writes the pre-model program for each family from the task specification and tool
schemas alone; record time to first passing version against the exact contract on the 30
held-out records, number of defects found by the contract, and whether the author
declared a verifier. Then hand each program the C1 perturbations and count silent wrong
answers. This is the measurement §7 currently replaces with "we do not price manual
authoring." Even a small-$n$ result moves significance because it is the only missing side
of the comparison the paper itself raises.

---

## 5. Exact arithmetic the plan relies on

Zero-violation and small-$k$ requirements, $\alpha=0.05$, $\delta=0.1$, one-sided exact
binomial, Bonferroni over the grid and over $m$ candidates. Recomputed 2026-10-02 with
`scipy.stats.beta.ppf`.

Minimum admitted groups $n$ for $U\le\alpha$ with $k$ observed violations:

| Design | $k=0$ | $k=1$ | $k=2$ | $k=3$ | $k=4$ |
|---|---:|---:|---:|---:|---:|
| Registered grid, $m=1$ ($\gamma=0.1/11$) | 92 | 133 | 168 | 200 | 231 |
| Registered grid, $m=2$ ($\gamma=0.1/22$) | 106 | 148 | 185 | 218 | 251 |
| Single threshold, $m=1$ ($\gamma=0.1$) | **45** | **77** | 105 | 132 | 158 |
| Single threshold, $m=2$ ($\gamma=0.05$) | **59** | **93** | 124 | 153 | 181 |

Upper bound $U$ at the retained $n=92$:

| Design | $k=0$ | $k=1$ | $k=2$ |
|---|---:|---:|---:|
| Grid, $m=1$ | 0.0498 | 0.0711 | 0.0895 |
| Grid, $m=2$ | 0.0569 | 0.0791 | 0.0981 |
| Single, $m=1$ | 0.0247 | 0.0416 | 0.0568 |
| Single, $m=2$ | 0.0320 | 0.0505 | 0.0669 |

Cluster-level units from Table 17 under the single threshold, $k=0$ (admit iff $\le0.05$):

| Cohort | Authors | $U$ ($m=1$) | $U$ ($m=2$) | Days | $U$ ($m=1$) |
|---|---:|---:|---:|---:|---:|
| Issue-type routing ($m=1$) | 82 | 0.0277 | — | 90 | 0.0253 |
| PR-outcome audit ($m=2$) | 60 | — | 0.0487 | 86 | 0.0342 |
| Backlog-attention routing ($m=2$) | 73 | — | 0.0402 | 87 | 0.0338 |
| Core `streamlit/streamlit` ($m=1$) | 25 | 0.088 | — | 87 | 0.0261 |

External substrates under the single threshold, $m=1$, $k=0$: NESTFUL $n_{\max}=26\to
U=0.085$, BFCL $15\to0.142$, API-Bank $8\to0.250$ (all still retire); AppWorld
$136\to0.017$. The refusal result survives D2 unchanged, which matters: the simplification
does not buy admissions it should not.

---

## 6. Schedule, tracks, and budget

Today is 2026-10-02. The ICLR 2027 full-paper deadline (2026-09-25 AOE per the compliance
checklist) has passed; the submission is in review under forum `DF0JaS58gr`. ICLR reviews
typically release in the second week of November with author discussion through late
November; verify the exact dates on the ICLR 2027 site before scheduling Phase 3. ICLR
permits a revised PDF during discussion, so Phases 0–2 feed both the rebuttal and the
revision; Phase 4 prepares the resubmission in case of rejection, where D2 becomes the
method rather than a sensitivity analysis.

| Phase | Dates | Tasks | Spend | Exit criterion |
|---|---|---|---:|---|
| 0 Provider-free | Oct 2 – Oct 16 | A1, B1, B2, B3, E1–E3, E5–E7, F1, F2, G1–G3; protocols for A2, C1, C2, D1 committed | \$0 | validator green; page 9 holds; four protocols pre-registered with spend caps |
| 1 Cheap live | Oct 9 – Oct 23 | C1 drift replay; C2 preflight and acquisition; H1 scheduled | ≤ \$15 | C1 decision rule applied and written; C2 GO/NO-GO per family committed |
| 2 Cohorts | Oct 23 – Nov 6 | C2 run; A2 on the C2 pool; D1 HMDA; E4 figure | ≤ \$60 | all results pinned by validator families; tables generated |
| 3 Integrate | Nov 6 – Nov 13 | rewrite pass with results; appendix diet; number registry; rebuttal kit | \$0 | revised PDF built, anonymous, 9 pages; point-by-point response drafted from `reviewer_response_iclr2027.md` |
| 4 Discussion / resubmission | Nov – Jan | respond; upload revision; if rejected, restructure under D2 for ICML 2027 (late January) | \$0 | — |

Total provider spend cap: **\$100** at list prices. Human time: roughly 25 working days
for one person plus the H1 engineers.

Dependencies: A2 waits on C2 only for the larger pool (it can run on the retained 92
issue-type groups immediately). D1 waits on the author's macro approval. E4 waits on C1.
Everything in Phase 0 is independent and can start today.

---

## 7. Score projection under outcomes

| Scenario | Composite | Reading |
|---|---:|---|
| Phase 0 only (writing, D1, D2 sensitivity, related work) | 82 | Soundness and clarity fixed; evidence unchanged. ICLR 6. |
| + C1 positive (guards abstain where unverified arms answer wrongly) | 86 | First held-out mechanism result. |
| + C2 GO on ≥2 families with compiler-wide, cluster-robust certificates | 88 | F2 and F4 closed with data, not wording. |
| + A2 admits on at least one family under end-to-end labels | 90 | The certificate finally covers the continuation. |
| + D1 compiles or retires cleanly on HMDA | 91–93 | Second domain; one-snapshot objection answered. |
| C1 null, everything else lands | 87–88 | Guards stay a design argument; the paper says so; still a clear improvement. |
| C2 NO-GO on all families (snapshot cannot supply classes) | subtract 2 | Fall back to A2 on retained pools and D1 for the fresh calibration pool. |

The honest floor of the plan is about 82 and its honest ceiling about 93. Crossing 90
requires at least two of C1, C2, A2, D1 to land in their positive branch.

---

## 8. What not to do

- Do not run another same-cohort replication (third model, third provider). The
  objection is one snapshot and one domain, not one model.
- Do not add appendix tables. The appendix is a liability at 27; every new result replaces
  an existing table or goes to the archive.
- Do not pursue the AWO or any workflow-reuse head-to-head; the spike memo's no-go stands,
  and the drift study is the internal comparison that answers the same question.
- Do not extend the read-only prologue. The measurement already shows those architectures
  do not execute the region.
- Do not try to make $q$ rank. Demote it (D2) and let the graded-frontier protocol be
  future work that a 184+ group pool could run.
- Do not relitigate Headroom. One sentence in App. G is enough.
- Do not change $\alpha$, $\delta$, cohorts, or decision rules after seeing results. D2 is
  reported as a sensitivity analysis for retained runs precisely for that reason.

---

## 9. Governance

- One branch and one PR per workstream, using the repository template in full; request
  review from the author; no Copilot review; never merge.
- Every live study: protocol file committed before the first call, with design, cohorts,
  arms, endpoints, decision rule, and spend cap; results in a new directory; retained
  files never overwritten; failed and NO-GO outcomes committed.
- Every number that enters the manuscript: a JSON key path or generating script recorded
  in `paper/iclr/notes/number_registry.md`; a validator family pins it; tables are
  generated, not typed.
- Build and check order unchanged: analyses → `build_artifacts.py` → open-research build
  with `--keep-logs` → ICLR build → `finalize_manifest.py` → `validate_artifacts.py`;
  page-9 check; anonymity check; `build_anonymous_archive.py` refreshed.
- Resolve F12 (the uncommitted protocol edit) before anything else is committed on top of
  it.

---

## 10. Appendix: reviewer concern → task map

| Likely reviewer sentence | Finding | Tasks |
|---|---|---|
| "The theorem bounds an event that never happens; the misses you observe are outside it." | F1 | A1, A2 |
| "Two of your three headline artifacts are not covered by the theorem you prove." | F2 | B1, B2, C2 |
| "Why is there a learned score at all?" | F3 | B2, B3 |
| "Your own cluster analysis retires every family." | F4 | B1, C2, G1 |
| "Show me one held-out case where a guard prevented a wrong answer." | F5 | C1 |
| "A hand-written function ties you; what is the compiler for?" | F6 | C1, H1 |
| "One repository, one snapshot." | F7 | C2, D1 |
| "I could not find the contribution in the first page." | F8 | E1–E7 |
| "Related work is a paragraph." | F9 | F1, F2 |
| "This is Clopper–Pearson plus a union bound." | F10 | F2, B2 |
