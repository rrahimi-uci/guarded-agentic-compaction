# PAT feedback disposition — comprehensive source audit, 2026-10-16

This ledger supersedes the earlier PR #90 disposition, including its premature
“closed” assessments of score training, the DSL, and impossible replay failures.
Baseline: merged `origin/main` at `cfecd54`. Revision branch:
`paper/iclr-comprehensive-feedback`.

The supplied seven-page PDF contains automated PAT feedback dated 12 September
2026, not independently verified human reviews. Its numbered comments, minor
corrections, and all manuscript sections, algorithms, tables, and bibliography
were read before editing. The browser print clips some right-hand line endings;
no missing text was invented. The document's survey/interface instructions are
not author instructions and were not acted on. No OpenReview content was posted.

“Verified existing revision” means the evidence was already in the merged paper;
it does not mean a missing experiment was performed in this revision. Section
references below use stable source labels where possible because pagination changes.

## Weaknesses

| # | PAT item | Disposition | Where |
|---|---|---|---|
| W1 | No comparison against AWM, LLMCompiler, plan caching; situate against EvoC2F and Agent JIT | Partially addressed empirically: an adapted, pinned offline AWM comparison now runs on three workflows and two models (8,172 episodes) and is in the abstract, §5.5, §7, Appendix J and K. The existing Appendix G "scope of automated workflow-reuse comparison" paragraph states, per system, what is reused, where it executes, what admits it, and why none yields an admit-or-retire decision comparable to GAC's; EvoC2F and Agent JIT are described as the closest compiler comparators (effect/state annotations, verification before reuse, admission by tests and contracts rather than a finite-sample bound). The native-browser and compiler-based comparators remain missing and §7 says so. | App. G; §5.5; §7; App. J, K |
| W2 | Proposition 1 assumes one fixed candidate; the primary families calibrated two; Bonferroni needs 106 groups | Verified existing revision. §3, §5.1, App. A, and App. C state the certificate level per artifact ($m$ = 1, 2, 2); the two-candidate bound 0.0569 and the 106-group requirement are in `tab:multiplicity-accounting`; Corollary 2 covers the frozen search; the pre-registered repair was a NO-GO and is reported as such. | §3, §5.1, App. A, App. C |
| W3 | Position invariant $a=0$ blocks ReAct and plan-and-execute; allow a read-only prologue | Verified existing revision, by measurement rather than by conjecture: the prologue relaxation was implemented, tested, and measured on the 8,190 released trajectories; it recovers 2 of 2,340 ReAct runs because those agents seldom execute the admitted region at all. | §5.4; App. G `tab:appworld-prologue` |
| W4 | Step-gate behaviour is partly an arithmetic artifact of $|\mathcal{K}|=92$ | Verified existing revision. §3 derives $|\mathcal{K}|\ge\lceil 92/c\rceil$ and the 0.0503 bound at 91 groups; App. C has the floor figure and the two observed, uncertifiable intermediate coverages; App. H says the pre-registered three-level criterion was unattainable at that cohort size. | §3, App. C `fig:gate-floor`, App. H |
| W5 | Model checkpoint, endpoint, decoding settings, and pricing missing | Verified existing revision. §4 names `gpt-5.6-luna` via the `openai-agents` Responses interface at reasoning effort `low`; App. C gives the rate card with retrieval dates and the effective request manifest (`tab:live-manifest`: SDK versions, settings, timeouts, concurrency, cache fields, price formula). | §4, App. C |

## Introduction and problem formulation (pp. 1--3)

| # | PAT item | Disposition | Where |
|---|---|---|---|
| 1 | Tracing-JIT analogy versus strict entry-prefix restriction | Verified existing revision. §1 says the method compiles only *initial* read-only prefixes; §2 states "everything that follows is an initial read-only prefix compiler" and points at the AppWorld cost of that choice. | §1, §2 |
| 2 | Eq. (4) couples the admission risk to downstream model accuracy | Verified existing revision, differently from the suggestion: the implementation labels only replay-contract violations of the compiled region, so the certificate does not cover the continuation at all. §2 (third scope note), `alg:calibrate` input, App. C "calibration labels as computed", and §7 say so; the one end-to-end certificate (post-cutoff PR-outcome cohort) is named as the exception. The PAT suggestion to describe the gate as certifying end-to-end compliance would have been inaccurate for the primary artifacts. | §2, §3, App. C, App. G |
| 3 | Objective over episodes versus constraint over groups | Verified existing revision: both halves of Eq. (4) now take the group measure, with the per-episode saving summed inside the group. | §2 Eq. (4) |
| 4 | Eq. (1) suggests a multi-input transform; Algorithm 3 is single-source | **Corrected further.** Eq. (1) now quantifies over slot keys and equates the slot value to a single-source expression. The same path/chain and invariant literal are fitted across supporting training traces. | §2 Eq. (1) |
| m1 | Hyphenation artifacts in the abstract | Not applied beyond `read\nobreakdash-only`: the listed breaks (`re-/duce`, `ar-/guments`, ...) are ordinary end-of-line hyphenation that the reviewer's text extraction dropped; the rendered PDF is correct. | abstract |
| m2 | $c_j$, $o_j$ undefined in the episode tuple | Verified existing revision. | §2 |
| m3 | Bracket/comma notation in Eq. (1) | Verified existing revision (explicit $\exists$ quantifiers). | §2 |

## Pipeline and admission logic (pp. 3--7)

| # | PAT item | Disposition | Where |
|---|---|---|---|
| 1 | Multi-candidate search does not inherit Proposition 1 | **Corrected further.** Calibration-dependent early stopping does not fix the number tested. A simultaneous bound budgets a prespecified candidate set, and candidate freezing halts on either admission or retirement. The algorithm and corollary now state partition scope. Retained multiplicities and numbers are unchanged. | §3 after Prop. 1 |
| 2 | Intermediate coverage structurally precluded at 92 groups | **Corrected further.** At 92 groups the outcomes are retirement or full empirical calibration coverage, not a population-coverage guarantee. Later 184/192-group studies are now distinguished. | §3, App. C |
| 3 | `FitScore` model family, loss, and labels unspecified | **Corrected in this revision.** The earlier disposition was inaccurate: training uses development rows and synthetic variants, not only group-level guard/manifest failures. Appendix C now specifies the balanced logistic loss, seven exact feature definitions, standardization, degenerate fits, unused OOF scores, and synthetic +0.5 feature increments. Calibration uses clean rows. Challenge rejection does not imply zero training violations. | §3 stage 6, App. C |
| 4 | 23-operator DSL not listed | **Expanded in this revision.** `tab:dsl` gives input/output types and restrictions for all 23 operators, the single-source depth-two grammar, parameter sources and search caps. The executable library is larger than the candidate generator; failure to find a witness is not a completeness theorem. | App. C |
| 5 | $\rho$ in Eq. (6) before the verifier exists | Verified existing revision: Eq. (6) now has a pre-synthesis form with $\rho=1$ and a realized post-verification form; stage 3 evaluates the former. | §3 |
| m | Algorithm 1 line-7 scoping, $w_{\max}$ in the input list, $\mathcal{A}$ overload in Algorithm 2, Eq. (5) underbrace | Verified existing revision except the underbrace, which renders correctly in the PDF (the artifact is in text extraction only). | App. B |

## Experimental setup and primary evaluation (pp. 7--9)

| # | PAT item | Disposition | Where |
|---|---|---|---|
| 1 | Model identity, hyperparameters, pricing | **Corrected further.** Requested aliases are retained, immutable provider checkpoints are not. Omitted decoding fields mean provider defaults, not proof that the API lacks those controls. The generated dollar-cost formula now includes the missing $10^{-6}$ factor; reported result values are unchanged. | §4, App. C |
| 2 | Manual comparator has no resource numbers | Verified existing revision: `tab:manual-resources` and `tab:absolute-resources` give every arm on every axis. Rechecked: §5.1 now says all token/cost/latency comparisons are explicitly pooled; individual-family rankings differ. | §5.1, App. D |
| 3 | "Held-out replay" 34/0/0 versus 11/11 | Verified existing revision: the Table 2 caption states that p/a/w is the family-level replay split, not the admission test split, and App. F.3 explains both partitions. | §5.4, App. F.3 |
| 4 | Which stage retired `pytorch/pytorch` | Verified existing revision: "at admission, where no calibration group is accepted at any threshold", with the 84/30/2 class composition in App. F.1 and the explicit statement that the cause is not established. | §5.2, App. F.1 |
| 5 | Position invariant on ReAct | Verified existing revision (see W3). | §5.4, App. G |
| 6 | No plan-caching or workflow-reuse baseline | Verified existing revision for AWM; **this revision** adds the per-system operational discussion (see W1). | §5.5, App. G, J, K |
| m | $\varphi$ symbol, $U_\eta$ hat, leading zero, appendix-table pointers, "bimodal average" | Verified existing revision (cleveref pointers name the appendix; $U_{\hat\eta}$ throughout; "almost always ... almost never" replaces "bimodal"). | §5 |

## Related work, limitations, broader context (pp. 9--13)

| # | PAT item | Disposition | Where |
|---|---|---|---|
| 1 | Step gate is a sample-size floor | Verified existing revision (see W4). | §3, §7, App. C, App. H |
| 2 | Abstract/§1/§5.1 should state per-candidate certificates | Verified existing revision: §5.1 states the level per family; §1 says the level and event are stated per artifact; the abstract says most certificates concern replay rather than final answers. | abstract, §1, §5.1 |
| 3 | Non-exchangeability mitigations | Verified existing revision: `tab:effective-units` and the single-rule sensitivity show what day- and author-level units would give; App. G names `min_days`, temporal partitioning, and cluster-level formulations and says none inherits Eq. (7). | §7, App. C, App. G |
| 4 | Contextualize dynamic-compilation baselines | Rechecked (see W1). | App. G |
| m1--m6 | "four repositories" count, citation placement, $n_\eta$ in the proof, "Proposition" capitalization, $r^\star$ typography, bibliography pagination | Verified the existing bibliography `\interlinepenalty` and inspected the rebuilt reference pages (11--16); no new pagination setting was needed. | §6, §7, App. A, `main.tex` |

## Formal proofs, algorithms, configuration (pp. 13--16)

| # | PAT item | Disposition | Where |
|---|---|---|---|
| 1 | $\gamma$ versus $\delta$ in the 1.8%/13.6% figures | Verified existing revision: labelled as single-threshold illustrations, with the grid-wide and candidate-wide $\delta$ statements stated separately. | App. A |
| 2 | Cost CIs and issue-type inferential rows | Verified existing revision (`tab:paired-statistics`, `tab:reduction-ci`). | App. D |
| 3 | Algorithm 4 does not enforce $a=0$ | Verified existing revision: `X.O ≠ ∅ → FALLBACK` is in the algorithm and in the runtime (`non_prefix_boundary`, unit-tested). | App. B |
| 4 | Algorithm 3 slot name/value, "block region", unordered pairs | Verified existing revision: slot name and value separated, four slot marks, `s<t` order edges, `(G,S)` returned, `MineRegions` blocks. | App. B |
| 5 | Algorithm 4 unbound context handles; `quota_attested` undefined | Verified existing revision: runtime context $X=(M',\mathcal{O},\textsc{snap},\textsc{stage})$; `quota_attested` defined in App. C. | App. B, App. C |
| m | $k_\eta=n_\eta$ branch, `ln`, "deterministic by construction" with record 5189, $o_j$ bound in the loop head, `behaviour` | Verified existing revision (the validator rejects `behaviour`). | App. A, B, D |

## Benchmark audits and prospective protocols (pp. 16--22)

| # | PAT item | Disposition | Where |
|---|---|---|---|
| 1 | Step-gate inevitability at 92 groups | Verified existing revision (see W4). | App. H |
| 2 | `pytorch/pytorch` divergence between protocols | Verified existing revision (see setup item 4). | App. F.1, App. H |
| 3 | 239/240 versus 240/240 | Verified existing revision: intention-to-treat per arm (240/240, 240/240, 239/240), the timed-out support-only episode named and not retried. | App. H |
| 4 | $a=0$ on interactive frameworks | Verified existing revision (see W3). | App. G |
| m | Orphaned list, `INSERT/UPDATE/...` spacing, "both GitHub families", decision-rule pointer | Verified existing revision. | App. E, F.3, G, H |

## Additional corrections from the full-paper review

- **Narrative:** three explicit research questions; shorter abstract and contribution
  list; strongest adapted-AWM result and its margin dependence stated together.
- **Loss definition:** clean fallback has zero replay loss but may fail the final
  task. The post-cutoff result is an absolute end-to-end error certificate, not
  causal attribution or noninferiority. The suggestion to relabel all certificates
  end-to-end was rejected as technically incorrect.
- **Admission accounting:** admitted attempts in the theorem include clean aborted
  replays; historical runtime “dispatch” counters record completed compaction.
- **Search limits:** no recovered witness means unresolved in the implemented
  bounded search. Removed “genuine model decision” from the provenance algorithm.
- **Gate-floor figure:** regenerated from its plotting source, correcting the
  same stale all-cohorts wording inside the graphic and removing crossing label
  leaders that obscured annotation text.
- **Replay claims:** zero observed failures on stable snapshots does not prove
  that the replay event is impossible. Removed that claim from the method.
- **AppWorld:** documentation calls explain some position failures, not the entire
  lack of recurrence. The two-run prologue recovery is retained; no broad suffix
  dispatcher or arbitrary `a <= k` relaxation is claimed safe.
- **BIRD:** the evidence map no longer describes 924 complete-case rows as distinct
  held-out questions. Scheduled dev, repeated second-model dev, and train cohorts
  remain separate; noninferiority was not established.
- **Safeguards:** completeness benefit is unresolved, rather than “adds little.”
- **Bibliography:** primary-source verification of the closest comparators and
  recent work; added published EvoC2F and Agent JIT page ranges. No priority or
  cross-paper superiority claim is inferred from incompatible benchmarks.
- **Reproducibility:** score helper docstrings corrected without changing runtime
  behavior or rerunning paid experiments; generated provider-manifest table and
  JSON agree; historical response notes are explicitly superseded.

The timeout feedback was not applied literally: only support-only has 239/240;
baseline and learned-gate each have 240/240. The 34/0/0 AppWorld family replay is
not the separate 11/11 admission test split. Ordinary PDF line-end hyphenation
was not “corrected” as a spelling error. No unsupported experimental result was
added to satisfy a request.

## Final assessment and validation

See [final_reviewer_assessment.md](final_reviewer_assessment.md) for the
reviewer-style assessment, remaining evidence gaps, literature audit, and exact
validation results. The current checklist distinguishes the ten-page revision
format from the nine-page initial-submission requirement. Editorial closure is
not empirical closure: missing comparators, dependence assumptions, and null
gate results remain explicit limitations.
