# PAT feedback disposition and final review (2026-10-16)

Item-by-item disposition of the 12 September 2026 PAT feedback on OpenReview
forum `DF0JaS58gr`, checked against the manuscript at the head of
`paper/iclr-pat-feedback-review` (branched from `main` at 5ec65b0, which already
carries the September and October revision passes). Every item was re-read
against the current source rather than against the revision log. "Closed
earlier" means the current `main` already carried the change; "this pass" means
the change was made on this branch; "not applied" states the technical reason.

Build at this head: 51 pages, Sections 1--8 end on page 10, the AI Use Statement
opens page 11, 0 overfull boxes, 0 unresolved references, PDF anonymous.
Validator: 5,624 checks, 0 failed.

## Weaknesses

| # | PAT item | Disposition | Where |
|---|---|---|---|
| W1 | No comparison against AWM, LLMCompiler, plan caching; situate against EvoC2F and Agent JIT | Closed earlier for the executable part: an adapted, pinned offline AWM comparison now runs on three workflows and two models (8,172 episodes) and is in the abstract, §5.5, §7, Appendix J and K. **This pass** rewrites the Appendix G "scope of automated workflow-reuse comparison" paragraph to state, per system, what is reused, where it executes, what admits it, and why none yields an admit-or-retire decision comparable to GAC's; EvoC2F and Agent JIT are described as the closest compiler comparators (effect/state annotations, verification before reuse, admission by tests and contracts rather than a finite-sample bound). The native-browser and compiler-placed comparators remain missing and §7 says so. | App. G; §5.5; §7; App. J, K |
| W2 | Proposition 1 assumes one fixed candidate; the primary families calibrated two; Bonferroni needs 106 groups | Closed earlier. §3, §5.1, App. A, and App. C state the certificate level per artifact ($m$ = 1, 2, 2); the two-candidate bound 0.0569 and the 106-group requirement are in `tab:multiplicity-accounting`; Corollary 2 covers the frozen search; the pre-registered repair was a NO-GO and is reported as such. | §3, §5.1, App. A, App. C |
| W3 | Position invariant $a=0$ blocks ReAct and plan-and-execute; allow a read-only prologue | Closed earlier, by measurement rather than by conjecture: the prologue relaxation was implemented, tested, and measured on the 8,190 released trajectories; it recovers 2 of 2,340 ReAct runs because those agents seldom execute the admitted region at all. | §5.4; App. G `tab:appworld-prologue` |
| W4 | Step-gate behaviour is partly an arithmetic artifact of $|\mathcal{K}|=92$ | Closed earlier. §3 derives $|\mathcal{K}|\ge\lceil 92/c\rceil$ and the 0.0503 bound at 91 groups; App. C has the floor figure and the two observed, uncertifiable intermediate coverages; App. H says the pre-registered three-level criterion was unattainable at that cohort size. | §3, App. C `fig:gate-floor`, App. H |
| W5 | Model checkpoint, endpoint, decoding settings, and pricing missing | Closed earlier. §4 names `gpt-5.6-luna` via the `openai-agents` Responses interface at reasoning effort `low`; App. C gives the rate card with retrieval dates and the effective request manifest (`tab:live-manifest`: SDK versions, settings, timeouts, concurrency, cache fields, price formula). | §4, App. C |

## Introduction and problem formulation (pp. 1--3)

| # | PAT item | Disposition | Where |
|---|---|---|---|
| 1 | Tracing-JIT analogy versus strict entry-prefix restriction | Closed earlier. §1 says the method compiles only *initial* read-only prefixes; §2 states "everything that follows is an initial read-only prefix compiler" and points at the AppWorld cost of that choice. | §1, §2 |
| 2 | Eq. (4) couples the admission risk to downstream model accuracy | Closed earlier, differently from the suggestion: the implementation labels only replay-contract violations of the compiled region, so the certificate does not cover the continuation at all. §2 (third scope note), Algorithm 2's input line, App. C "calibration labels as computed", and §7 say so; the one end-to-end certificate (post-cutoff PR-outcome cohort) is named as the exception. The PAT suggestion to describe the gate as certifying end-to-end compliance would have been inaccurate for the primary artifacts. | §2, §3, App. C, App. G |
| 3 | Objective over episodes versus constraint over groups | Closed earlier: both halves of Eq. (4) now take the group measure, with the per-episode saving summed inside the group. | §2 Eq. (4) |
| 4 | Eq. (1) suggests a multi-input transform; Algorithm 3 is single-source | Closed earlier: Eq. (1) quantifies over a single source $s\in\operatorname{Src}(z,o_{<j})$ and the text says the witness is deliberately single-source. | §2 Eq. (1) |
| m1 | Hyphenation artifacts in the abstract | Not applied beyond `read\nobreakdash-only`: the listed breaks (`re-/duce`, `ar-/guments`, ...) are ordinary end-of-line hyphenation that the reviewer's text extraction dropped; the rendered PDF is correct. | abstract |
| m2 | $c_j$, $o_j$ undefined in the episode tuple | Closed earlier. | §2 |
| m3 | Bracket/comma notation in Eq. (1) | Closed earlier (explicit $\exists$ quantifiers). | §2 |

## Pipeline and admission logic (pp. 3--7)

| # | PAT item | Disposition | Where |
|---|---|---|---|
| 1 | Multi-candidate search does not inherit Proposition 1 | Closed earlier (see W2). | §3 after Prop. 1 |
| 2 | Intermediate coverage structurally precluded at 92 groups | Closed earlier (see W4). | §3 |
| 3 | `FitScore` model family, loss, and labels unspecified | Closed earlier: $\ell_2$-regularized logistic model on entry-observable features, standardized on development moments, positive class = unproductive development group; the text explains why wrong executions are unavailable as training signal after `ReplayAndChallenge`. | §3 stage 6, App. C |
| 4 | 23-operator DSL not listed | Closed earlier: `tab:dsl` lists all 23 operators by class with the value-directed search rule. | App. C |
| 5 | $\rho$ in Eq. (6) before the verifier exists | Closed earlier: Eq. (6) now has a pre-synthesis form with $\rho=1$ and a realized post-verification form; stage 3 evaluates the former. | §3 |
| m | Algorithm 1 line-7 scoping, $w_{\max}$ in the input list, $\mathcal{A}$ overload in Algorithm 2, Eq. (5) underbrace | Closed earlier except the underbrace, which renders correctly in the PDF (the artifact is in text extraction only). | App. B |

## Experimental setup and primary evaluation (pp. 7--9)

| # | PAT item | Disposition | Where |
|---|---|---|---|
| 1 | Model identity, hyperparameters, pricing | Closed earlier (see W5). | §4, App. C |
| 2 | Manual comparator has no resource numbers | Closed earlier: `tab:manual-resources` and `tab:absolute-resources` give every arm on every axis. **This pass**: §5.1 now says the compiled arm leads the manual program only on *pooled* latency, since backlog routing is the exception in the table. | §5.1, App. D |
| 3 | "Held-out replay" 34/0/0 versus 11/11 | Closed earlier: the Table 2 caption states that p/a/w is the family-level replay split, not the admission test split, and App. F.3 explains both partitions. | §5.4, App. F.3 |
| 4 | Which stage retired `pytorch/pytorch` | Closed earlier: "at admission, where no calibration group is accepted at any threshold", with the 84/30/2 class composition in App. F.1 and the explicit statement that the cause is not established. | §5.2, App. F.1 |
| 5 | Position invariant on ReAct | Closed earlier (see W3). | §5.4, App. G |
| 6 | No plan-caching or workflow-reuse baseline | Closed earlier for AWM; **this pass** adds the per-system operational discussion (see W1). | §5.5, App. G, J, K |
| m | $\varphi$ symbol, $U_\eta$ hat, leading zero, appendix-table pointers, "bimodal average" | Closed earlier (cleveref pointers name the appendix; $U_{\hat\eta}$ throughout; "almost always ... almost never" replaces "bimodal"). | §5 |

## Related work, limitations, broader context (pp. 9--13)

| # | PAT item | Disposition | Where |
|---|---|---|---|
| 1 | Step gate is a sample-size floor | Closed earlier (see W4). | §3, §7, App. C, App. H |
| 2 | Abstract/§1/§5.1 should state per-candidate certificates | Closed earlier: §5.1 states the level per family; §1 says the level and event are stated per artifact; the abstract says most certificates concern replay rather than final answers. | abstract, §1, §5.1 |
| 3 | Non-exchangeability mitigations | Closed earlier: `tab:effective-units` and the single-rule sensitivity show what day- and author-level units would give; App. G names `min_days`, temporal partitioning, and cluster-level formulations and says none inherits Eq. (7). | §7, App. C, App. G |
| 4 | Contextualize dynamic-compilation baselines | **This pass** (see W1). | App. G |
| m1--m6 | "four repositories" count, citation placement, $n_\eta$ in the proof, "Proposition" capitalization, $r^\star$ typography, bibliography pagination | Closed earlier except the pagination; **this pass** sets `\interlinepenalty` inside the bibliography so no entry splits across a page (checked on pages 11--14). | §6, §7, App. A, `main.tex` |

## Formal proofs, algorithms, configuration (pp. 13--16)

| # | PAT item | Disposition | Where |
|---|---|---|---|
| 1 | $\gamma$ versus $\delta$ in the 1.8%/13.6% figures | Closed earlier: labelled as single-threshold illustrations, with the grid-wide and candidate-wide $\delta$ statements stated separately. | App. A |
| 2 | Cost CIs and issue-type inferential rows | Closed earlier (`tab:paired-statistics`, `tab:reduction-ci`). | App. D |
| 3 | Algorithm 4 does not enforce $a=0$ | Closed earlier: `X.O ≠ ∅ → FALLBACK` is in the algorithm and in the runtime (`non_prefix_boundary`, unit-tested). | App. B |
| 4 | Algorithm 3 slot name/value, "block region", unordered pairs | Closed earlier: slot name and value separated, four slot marks, `s<t` order edges, `(G,S)` returned, `MineRegions` blocks. | App. B |
| 5 | Algorithm 4 unbound context handles; `quota_attested` undefined | Closed earlier: runtime context $X=(M',\mathcal{O},\textsc{snap},\textsc{stage})$; `quota_attested` defined in App. C. | App. B, App. C |
| m | $k_\eta=n_\eta$ branch, `ln`, "deterministic by construction" with record 5189, $o_j$ bound in the loop head, `behaviour` | Closed earlier (the validator rejects `behaviour`). | App. A, B, D |

## Benchmark audits and prospective protocols (pp. 16--22)

| # | PAT item | Disposition | Where |
|---|---|---|---|
| 1 | Step-gate inevitability at 92 groups | Closed earlier (see W4). | App. H |
| 2 | `pytorch/pytorch` divergence between protocols | Closed earlier (see setup item 4). | App. F.1, App. H |
| 3 | 239/240 versus 240/240 | Closed earlier: intention-to-treat per arm (240/240, 240/240, 239/240), the timed-out support-only episode named and not retried. | App. H |
| 4 | $a=0$ on interactive frameworks | Closed earlier (see W3). | App. G |
| m | Orphaned list, `INSERT/UPDATE/...` spacing, "both GitHub families", decision-rule pointer | Closed earlier. | App. E, F.3, G, H |

## Own end-to-end review: changes made in this pass

Beyond the PAT items, a reviewer-style read of the whole manuscript at this head found and fixed:

- **Abstract.** The sentence "completeness checks can duplicate recovery" was unreadable without
  Appendix I; it now says the agent often recovers from incomplete evidence without a completeness
  check. The post-cutoff end-to-end certificate (132 fresh pull requests, no end-to-end error, rate
  below 2% at 90% confidence) was absent from the abstract although it is the direct answer to the
  PAT's certificate-coupling concern; one sentence restores it. The conclusion's matching phrase
  now reads "completeness checks add little". Paid for by dropping a sentence from §5.5 that §7
  repeats (native and compiler-only comparisons remain missing).
- **§3.** "Nor does the event itself have support on the GitHub cohorts" now says what it means:
  the certified event cannot occur on those cohorts as labelled, so a zero violation count is
  expected by construction.
- **§5.5.** "Request-scope admission" and "completeness checking" were used before being defined;
  each now carries a parenthetical gloss (the entry hull on the requested comment limit; the
  verifier clause that the prefetched page covers that request).
- **§6.** MIPRO (`opsahlong2024mipro`) is cited with DSPy; it was in the bibliography but uncited.
- **Appendix G.** Prompt compression (`jiang2023llmlingua`) is cited beside the Headroom comparator.
- **Appendix F.3.** The external evidence map now cites ToolSandbox, $\tau^2$-bench, ToolBench,
  AgentBench, GAIA, SWE-bench Verified, and BrowseComp, which were named without citations.
- **Notes.** `openreview_metadata.md` carried the pre-October abstract; it is regenerated from the
  source and must be re-pasted into OpenReview (user action).

Checked and left unchanged: every bound quoted in §3, §5, §7, App. A, C, D, G, and K was
recomputed (92/106 floors; 0.0498/0.0503/0.0509/0.0569; 0.0173/0.035/0.040/0.0228/0.0267;
1.7%/2.2%/3.3%/3.9%; the Appendix K noninferiority thresholds 17 losses at $n=600$, 0 or 1 at
$n=144$, bounds 3.27/4.66/5.86, powers 93.9/46.7/21.5/6.8%); every table cell cited in the
main text matches its appendix table; every `\cite` key exists and every bibliography entry is now
cited except `yoran2024assistantbench`, which is not printed.

## Remaining issues a reviewer could still raise

Ordered by how much each could affect acceptance.

1. **The headline certificate is largely vacuous on the primary cohorts.** The paper now says so
   plainly (support sufficiency; the certified event cannot occur by construction), and the
   post-cutoff cohort supplies one end-to-end certificate for one family. A reviewer may still
   ask why the "exact finite-sample admission" framing is the contribution when the bound binds
   only through its sample floor. The honest answer in the text is that the floor is what refuses
   NESTFUL, API-Bank, BFCL, and the Sonnet backlog family; no further change is possible without
   new calibration cohorts larger than 92 groups.
2. **No compiler-placed comparator.** The adapted AWM comparison answers the "no automated
   baseline" weakness, but AWM is an in-context method and the comparison is on API tasks rather
   than its native browser benchmark; EvoC2F and Agent JIT remain unrun. Appendix G now explains
   why, but a reviewer who asked for them may not be satisfied.
3. **The learned gate adds nothing measurable.** Three gate variants route identically on 2,724
   cases, and $q$ is constant within a family because the entry state is one record number. The
   paper reports this as a null; a reviewer may ask why the score is retained at all. The written
   but unrun graded-frontier protocol is the only answer offered.
4. **Independence is assumed, not established.** Day- and author-level units retire every primary
   family under the registered grid; the single-rule sensitivity would admit them but was not
   registered. This is disclosed in §7 and Appendix C, and cannot be repaired post hoc.
5. **Scope.** Initial read-only prefixes only; ReAct and plan-and-execute agents are essentially
   never dispatchable. Disclosed, with the prologue measurement.
6. **Density.** Ten pages carry eight studies plus three replications; sentences are long and
   number-heavy, and several main-text results are intelligible only with their appendix. Trimming
   studies from the main text is an authorial decision and was not made here.
7. **Cosmetic.** Figure 1 at 0.78 linewidth has small type; appendix pages with `[t]` floats
   produce underfull vertical boxes (present before this pass); the bibliography no-split
   penalty leaves slightly more white space at the foot of reference pages.

## Presentation restructure (same day, same branch)

After the disposition above, the author asked for the largest presentation gain obtainable from
existing data. Changes, with no number, result, or claim altered:

- **§5 reordered to lead with the strongest evidence.** §5.1 now carries both the primary
  three-family result (Table 1) and the 8,172-episode adapted-AWM comparison as Table 2 (a
  hand-maintained merge of the Appendix K accuracy and resource tables), with the matched-reuse
  paragraph moved up from the old §5.5.
- **New §5.2 "What is certified, and what the statistical stage adds"** with Table 3, one row
  per admitted artifact (event, $m$, $n_\eta/k_\eta$, bound, certificate level), replacing the
  number-dense certificate sentences; it states that the deterministic barriers do the admission
  work and the gate contributes its sample floor, with the 2,724-case gate null and the
  second-model/provider re-discovery results beside it.
- **§5.3 BIRD and §5.4 NESTFUL/AppWorld unchanged in substance.** The two-panel results figure
  was dropped (its left panel duplicated Table 1; its right panel duplicated $n_{\max}=26$ in
  Table 4).
- **New §5.5 "Further studies, reported in the appendix"**: the cross-repository extension and the
  live recovery study each reduced to one paragraph with their headline numbers; the main-text
  cross-repository paragraph was moved verbatim into Appendix F.1 so the appendix is
  self-contained. Labels `sec:res-multirepo` and `sec:res-recovery` are replaced by `sec:res-more`
  and every reference re-pointed.
- **§1 contribution list sharpened**: item 2 names the three comparators (unchanged agent,
  hand-written program, adapted AWM); item 3 states calibrated refusal together with the
  runtime-gate null as a reported finding.
- **§4** gains one sentence introducing the adapted AWM arm. **§7** no longer repeats the drift,
  completeness, and comparator sentences that §5 now carries. **§6** merges the process-mining
  paragraph into the trace-compilation one and compresses the conformal sentence.
- **Page budget**: paid for by the figure, the §5.5 compressions, and word-level cuts in §1, §2,
  §3, §4, §6, and §7 (listed in the revision log). Sections 1--8 end on page 10 and the AI Use
  Statement opens page 11; 51 pages; 0 overfull boxes; 0 unresolved references; anonymous;
  validator 5,633 checks, 0 failed.

Revised estimate after the restructure: presentation roughly 50 to the mid-60s; contribution
framing a few points higher; soundness, reproducibility, and significance unchanged. Overall
roughly 62 to 68 on the 0--100 scale used in the assessment above, still borderline.
