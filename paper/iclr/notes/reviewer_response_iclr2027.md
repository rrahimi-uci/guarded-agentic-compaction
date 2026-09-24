# Reviewer response — ICLR 2027 PAT/OpenReview feedback (draft, 2026-09-22)

Draft author response to the feedback archived in
`paper/reviews/GAC_ICLR_2027_Detailed_Revision_Plan.md`. Each point names the change, the
manuscript location at the PR #41 head, and the retained evidence it was checked against.
Items marked *pre-registered* have a committed protocol and no result yet; they are stated
as such in the paper and must not be described as run.

## Opening

We thank the reviewers. The revision separates three things the earlier draft ran
together: empirical preservation on the observed cohorts, per-candidate admission
certificates, and compiler-wide control. The three most material changes are (1) the
certificate level is now stated per artifact, with the two-candidate correction reported
where it applies; (2) Appendix H is re-derived from the retained per-episode data, including
facts the earlier text omitted; (3) Algorithms 3 and 4 now match the implementation, and
the runtime enforces the position invariant explicitly.

## Point-by-point

| Concern | Response | Where | Evidence |
|---|---|---|---|
| Candidate-selection multiplicity: Proposition 1 covers one fixed candidate, yet two candidates were calibrated on the same split and selected afterwards | We agree. Conditional on train/development data the number m of candidates reaching calibration is fixed: m = 1 for issue-type routing (its three-read sibling retired at synthesis and never saw calibration) and for every cross-repository family (frozen search), m = 2 for PR-outcome and backlog. We now state the level per artifact. For the two m = 2 families the candidate-wide budget γ = δ/22 gives U = 0.0569 > 0.05, so we report per-candidate certificates at α = 0.05 and a compiler-wide one only at α ≥ 0.057; a fresh 106-group calibration is *pre-registered* as the repair. | Abstract; §3 after Prop. 1; §5.1; §7; App. A (Cor. 2 discussion); App. C Table "multiplicity accounting" | `paper/results/iclr_revision/multiplicity_accounting.json`; `compiler.report` and `compiler.candidates` in the three family result files |
| Appendix A's 1.8%–13.6% figures read as grid-wide | The simulation unions m candidates at one threshold; we now label these single-threshold illustrations and give the γ/δ/m derivation separately. | App. A "Multiplicity accounting" | `paper/scripts/frozen_candidate_coverage_simulation.py` |
| 239/240 vs 240/240 | Accounting is now by episode under intention-to-treat: 240 records × 3 arms, 719/720 completed; baseline 240/240, learned gate 240/240, support-only 239/240. The one incomplete episode (`psf/requests` #6708, support-only) raised the 120 s timeout and was not retried because the protocol fixed no retry rule; the record passed in the other two arms. | App. H "Accounting"; Table 10 (per-arm columns) | `github_multirepo_gate_frontier/results.json` `failures[0]`, `aggregate.*.n` |
| Appendix H reads an infeasible design as a negative result about q | With \|K\| = 92 the registered bound certifies only n_η = 92, so the pre-registered three-level criterion was unattainable whatever q ranked; held-out q is moreover constant within a repository because the entry state is one integer. We now report the null as a design constraint, not evidence about q, and cite a protocol that states the ⌈92/c⌉ precondition. | §3 Stage 6; §7; App. C; App. F.4 (renamed); App. H | `coverage_curves`, `dispatch.q` in the gate-frontier results; `graded-frontier-protocol.md` |
| Unguarded / recurrence-only ablation missing | We price the guards internally: a nine-row mechanism-removal table lists each retained hazard, the guard that caught it, and what recurrence-only replay would have done. On PR-outcome and backlog the mined three-read sequence is the admitted program, so an unguarded replay differs only in guards that never fired on held-out records; on issue-type routing, where the compiler refused the three-read candidate, a live recurrence-only arm is *pre-registered*. | §6; §7; App. G table | `paper/iclr/tables/mechanism_removal.tex` with sources; `recurrence-only-ablation-protocol.md` |
| Algorithm 3 notation and scope | BuildPatg now separates slot name from value, marks slots grounded/ungrounded/ambiguous/literal, binds each result, uses s < t order edges, returns (G, S); MineRegions blocks. | App. B Alg. 3; Alg. 1 line 5–6 | `graph/provenance.py`, `graph/windows.py` |
| Algorithm 4 position enforcement and unbound inputs | Dispatch now takes the runtime context X = (M′, O, snap, stage), falls back whenever any tool has already been observed (X.O ≠ ∅), and states the commit-refusal contract; `quota_attested` is defined. The runtime implements the same rule (`non_prefix_boundary`) with tests. | App. B Alg. 4; App. C "Runtime capability vocabulary" | `runtime/dispatch.py`, `runtime/manual.py`, `tests/unit/test_dispatch_prefix_boundary.py` |
| Percent-only reporting; no cost CIs; no issue-type inferential rows | Appendix D now has absolute per-record means and medians for all arms, paired differences with bootstrap intervals for tokens, latency (mean and median), and cost in all three families, and a discordance table. | App. D Tables | `absolute_resources.json`, `paired_statistics.json` |
| 90/90 vs 89/90 read as accuracy gain | Discordant cells are 0 baseline-only / 1 compiled-only (record 5189), McNemar p = 1; an independent rerun of the same 30 records scored 30/30 in every arm. We claim preservation on the cohort, not superiority. | Abstract; §5.1; Table 1 caption; App. G | `headroom_ablation/results.json` |
| Latency validity | We describe the six-permutation per-record design, sequential arms, no warm-up, 120 s timeout, no retries, no shared server state, and report that the reduction is positive in every permutation–family cell (43.2%–78.6%). | App. D "Latency validity" | `order_sensitivity.json` |
| Reproducibility manifest | Appendix C now carries an effective request manifest (model string, SDK versions, settings, turn/time limits, concurrency, order, cache fields, price formula and date, data and catalog pins); the Reproducibility Statement lists them. | App. C Table; Reproducibility Statement | `live_provider_manifest.json` |
| i.i.d. groups | The qualifier appears wherever the bound is summarized; we report the effective units the cohorts contain (86–90 distinct days, 60–82 authors per 92 records) and state that a cluster-level bound retires in every family. | §3; §5.1; §7; App. C; App. G Table | `effective_units.json` |
| Live effect-catalog trust root | Appendix F/G now show the declared catalog per family, that the pinned digests match the manifests, and an audit of every retained call (100% within the declared read-only vocabulary; tools are pure reads of a pinned parquet). | App. G table; Fig. 2 barrier band | `live_catalog_audit.json` |
| "Independent five-times-larger cohort" | Corrected: the gate-frontier cohort shares 561/580 discovery, 442/460 calibration, and 130/150 held-out records with the core cohort and is twice its size; it is a larger sealed re-execution. We also disclose that the `psf/requests` block is the reused single-repository check, and that held-out dispatch was 160/240 (every open-class PR abstained on the induced `pr.state` hull). | App. H; App. F.1 | `cohort_overlap_audit.json`, `gate_frontier_reanalysis.json` |
| Read-only prologue | Kept as a conjecture; a design document fixes its acceptance tests. Not built. | App. G | `read-only-prologue-protocol.md` |
| Editorial ledger | Theorem references capitalized; bare decimals removed; American spelling; Headroom families named; INSERT/…/DROP break fixed; Figure 1 decimals; H.1 cross-reference. | throughout | `validate_iclr_sources` |

## What we did not do

We did not run the fresh-cohort multiplicity repair, the recurrence-only live arm, or the
drift-robustness ablation; each is pre-registered with a fixed decision rule and spend
ceiling. We did not implement the read-only prologue or collect a ⌈92/c⌉ calibration pool.
The paper states each of these as unrun.

## PAT minor corrections (checked against the 12 Sept 2026 feedback, item by item)

| PAT item | Status at PR #41 head |
|---|---|
| Abstract hyphenation/encoding artifacts (`readonly`, `reduce`, …) | Extraction artifacts of the reviewer's text copy; the source reads `read-only`, `reduce inference`; no change |
| Index tool calls/results in the episode tuple (line 122 vs 130) | §2 now defines $c_j$ and $o_j$ in the episode-tuple sentence |
| Eq. (1) bracket/comma notation | Eq. (1) already quantifies $\exists s\in\mathrm{Src}(z,o_{<j}),\ \exists g\in\mathcal{L}: u=g(s)$ (single-source form) |
| Alg. 1 line 7 `F` vs $\mathcal{F}$; $w_{\max}$ missing from Input | Both already fixed in the current Alg. 1 |
| Alg. 2 symbol overload of $\mathcal{A}$ | Local set renamed $\Pi$ |
| Eq. (5) underbrace artifact | PDF-extraction artifact; renders correctly |
| $\varphi$ symbol consistency; $U_\eta$ vs $U_{\hat\eta}$; leading zeros | Standardized (`\varphi`, $U_{\hat\eta}$, `0.05`); validator rejects bare decimals |
| Main-text pointers to appendix tables | Every main-text reference to an appendix table now reads "\cref{tab:…} in \cref{app:…}" |
| "average is bimodal" | Reworded to a distribution across architectures |
| §7 "four repositories" | Now "five repositories and 240 held-out triples" |
| §6 grouped citations | Distributed per system (DSPy, GEPA, RouteLLM, LLMCompiler) |
| App. A $m$ vs $n_\eta$ in the bound; $0\le k_\eta<n_\eta$ qualification | Proof now uses $n_\eta$ throughout and states the $k_\eta=n_\eta$ branch |
| App. A lowercase "proposition 1" | `\crefname` capitalizes every reference |
| App. A $r^\star$ typography | $r^{*}$ |
| Basu et al. orphaned author line | Reference list re-flows cleanly (checked in the rebuilt PDF) |
| App. C `log` vs `ln` | `\ln` |
| App. D "deterministic by construction" vs the 29/30 baseline record | Caption names record 5189 as the one exception |
| Alg. 3 unbound $o_j$ | Loop head iterates over call–result pairs $(c_j,o_j)$ |
| Alg. 4 "behaviour" | American spelling throughout |
| App. E orphaned bullet list | Lead sentence and list kept together |
| App. F.3 `INSERT/UPDATE/DELETE/ CREATE/DROP` | Legal break without a space |
| App. G "both GitHub families" | Names PR-outcome and backlog-attention |
| App. H.1 cross-reference to §7 | Points to the decision rule in Appendix H |

OpenReview fields (abstract, TL;DR) still show the pre-revision text and must be replaced with
`paper/iclr/notes/openreview_metadata.md`; the old TL;DR's "with no [quality loss]" clause is no
longer used.

## PAT verification pass (2026-09-23)

Every item above was re-checked against the PR #42 head with the bound arithmetic re-derived
(see `revision_log.md`, same date). Residuals closed in this pass:

| PAT item | Status |
|---|---|
| Situate GAC against EvoC2F and Agent JIT (weakness 1) | Appendix G names what each compiles and why neither makes an admissibility decision to compare against |
| Name the barrier that retired `pytorch/pytorch` in §5.2 | "at admission, where no calibration group is accepted at any threshold", with the class-composition account in Appendix F.1 |
| Eq. (1) source set vs Algorithm 3 | §2 enumerates flattened paths of the entry state and of each prior result |
| Appendix H.1 pointer to the decision rule | The Appendix H decision rule now carries the fourth pre-declared outcome it is asked to point at |
| Abstract `readonly` | `read-only` no longer breaks at the hyphen in the abstract |

## Live extensions (2026-09-24)

| Concern | Response | Where | Evidence |
|---|---|---|---|
| No unguarded / recurrence-only comparator was run | The pre-registered arm has now run: a barrier-free replay of the refused three-read region passed 30/30 with one request per record on the sealed issue-type cohort. By the decision rule fixed in advance we report that on this cohort the provenance refusal cost one request per record without a measured quality benefit, and that the guard's value is the refusal of an unwitnessed argument plus the 6602 counterexample. | App. G, Table (recurrence-only); §7 | `recurrence_only_ablation/results.json` |
| One provider / model family | A pre-registered same-cohort transfer to `gpt-6-luna` (different generation, same tier) reproduces the structure exactly (identical artifacts under the new pin, 30/30 dispatch per family, 66.6% fewer requests) and produces the paper's only compiled-only miss (issue-type #6532, a one-word excerpt paraphrase on identical evidence). We report the miss first, keep the one-calibrated-model claim, and read the miss as the case the manifest pin exists for. | App. G, Table (second model); §5.1; §7 | `second_model_replication/summary.json`, `github_workflow_families/*/gpt6_luna/results.json` |
| Results read as mostly negative | §1, §5.1, and §7 now state the positive claims the evidence supports: calibrated refusal (retire exactly where support is below the exact floor, no wrong execution), discovery reaching the manual ceiling, and zero compiled-only failures across 630 compiled held-out episodes on the calibrated model. No caveat was removed. | §1, §5.1, §7 | `validate_live_extensions` recomputes the 630/0 headline |

## Re-discovery, extended cohort, prologue, caveats (2026-09-24, second pass)

| Concern | Response | Where | Evidence |
|---|---|---|---|
| The second-model result rests on an uncertified transfer | Design A ran the whole pipeline on `gpt-6-luna`'s own traces: issue-type and PR-outcome re-derive the identical artifacts (same ids, programs, 92/0 gates) and pass 30/30 in every arm; backlog refuses at compile time (113/132 exact traces against 116), a pre-registered outcome. The transfer miss did not recur. | App. G, Table (second model, design-A block); §5.1 | `second_model_replication/issue_type_rediscovery/results.json`, `github_workflow_families/*/gpt6_luna_rediscovery/` |
| The 3.3% compiled-only bound rests on 90 records | A pre-registered 120-record issue-type extension on the calibrated model: 118/118/117 of 120, one compiled-only miss (record 2737, an excerpt-fidelity error), dispatch 119/120; the pooled bound is 2.2% (1/210). The §7 headline now reads 750 compiled held-out episodes with one compiled-only failure. All three pre-registered targets were missed and are reported. | App. D, Table (extended held-out); §5.1; §7 | `issue_type_extended_heldout/results.json` |
| Per-candidate certificates could be repaired | The pre-registered repair failed its own go/no-go: the snapshot has 33 unused open PRs and 8 unused owned issues against 36 per class. Recorded as NO-GO; per-candidate wording stays. | App. A | `multiplicity_repair/preflight.json` |
| The position invariant makes GAC inapplicable to ReAct agents; a prologue would fix it | We built and tested the prologue and measured it on the released trajectories: it recovers 2 of 2,340 ReAct trajectories, because those agents do not execute the admitted region at all (16 and 39 occurrences anywhere). The conjecture is replaced by the measurement. | App. G, Table (prologue); §5.3 | `external_benchmarks/appworld_dispatch_prologue_preflight.json` |
| Perturbation challenge not run; signatures off | Closed provider-free on recompiled, identical artifacts: nine perturbation families, zero wrong, zero hard rejects; signed registries verified, unsigned and tampered refused. | App. G | `iclr_revision/recompile_with_challenge.json` |
| Hard to see why coverage is 0 or 1; hard to audit claims | Figure (92-group floor) in App. C; a claims-versus-evidence register in App. I with a retained source and a claim boundary per row. | App. C, App. I | `figures/gate_floor.pdf`, `tables/claims_evidence.tex` |
