# ICLR 2027 revision log

Execution log for `improve-iclr.md` (Track S). One entry per task: id, files touched, numbers changed with their source key paths, verification summary.

## Baseline (2026-09-21)

- Branch `paper/iclr-2027-revision-track-s` from `main` at 5042e2f.
- Feedback archived: `paper/reviews/GAC_ICLR_2027_Detailed_Revision_Plan.{docx,md}`.
0d9af679d3f59a17605e733c51b2403b3fbb1ef6d7a8e7dd9ca7b2b04649c641  paper/iclr/build/main.pdf
8807b708aacf962850244e104d287667c961c7253970900669d0366c650a53f0  paper/open_research/main.pdf
d51a3efeceb9c1d2480f20217e20ae6aced0b18464d7c0ac21394f0456fc30eb  paper/open_research/article.pdf
686b7f09a219b3c034511db8a595bb167f7f3f31727f3f749d9ea59504221150  paper/results/publication_manifest.json
Pages:           25

## Track S execution (2026-09-22)

Tasks from `improve-iclr.md` completed on this branch; numbers cite the JSON under
`paper/results/iclr_revision/` produced by `paper/scripts/iclr_revision_statistics.py all`.

| Task | Files | What changed / numbers | Verification |
|---|---|---|---|
| T0.1–T0.2 | `paper/reviews/GAC_ICLR_2027_Detailed_Revision_Plan.{docx,md}`, this log | feedback archived; baseline hashes above | — |
| T1.1, T1.2, T2.8 | `appendix.tex` (App. H), `tables/gate_frontier_disaggregated.tex` (generated), protocol .md, `evidence-register.md`, `body.tex` | per-arm ITT accounting 240/240, 240/240, 239/240 (`gate_frontier_reanalysis.json`); #6708 support-only timeout, not retried; `psf/requests` block = reused smoke run; dispatch 160/240 (`range:pr.state`); support-only grid 12 points, U=0.0507, threshold 1.0; cohort shares 561/580 disc., 130/150 test with core (`cohort_overlap_audit.json`); "twice", not 4×/5×; $0.41 = successful attempts; decision rule cross-ref fixed | `validate_iclr_sources` |
| T1.3, T2.3 | `appendix.tex` (App. A, C), `tables/multiplicity_accounting.tex`, `main.tex` (`\crefname`), `body.tex` | m = 1 (issue-type), 2, 2; U(92, m=2)=0.0569; n_min 106; single-threshold labelling of 1.8%/13.6%; dominated candidates' tables not retained (recompile deferred, caption says so) | `multiplicity_accounting.json`; PDF has no lowercase "proposition 1" |
| T1.4, T1.5, T3.6 | `figures/alg-patg.tex`, `alg-dispatch.tex`, `alg-compile.tex`, App. B/C text, `runtime/dispatch.py`, `runtime/manual.py`, tests | slot name/value split, marks, `s<t`, `(G,S)`; runtime context `X`; `X.O ≠ ∅ → FALLBACK` implemented as `non_prefix_boundary`; `quota_attested` defined | `tests/unit/test_dispatch_prefix_boundary.py`; full suite |
| T1.6, T1.10 | sections, appendix, `pipeline_overview.tex`, `build_artifacts.py` | behavior spelling; `\ge 0.11`; Headroom families named; INSERT/…/DROP `\allowbreak`; Fig. 1 `U=0.0498 ≤ α=0.05`; `ICLR_FIGURES` casing | greps in validator |
| T1.8, T2.2 | `results.tex`, App. D tables | discordant cells 0 baseline-only / 1 compiled-only (record 5189), McNemar p=1, upper bound 3.3%; 2026-08-18 rerun 30/30; cost CIs; issue-type rows; median latency | `paired_statistics.json` |
| T2.1 | `tables/absolute_resources.tex`, App. D | per-record means/medians, all arms | `absolute_resources.json` |
| T2.4 | App. D "Latency validity" | six-permutation design; per-cell reductions 43.2%–78.6%, all positive; wall vs provider ≤0.3 pt | `order_sensitivity.json` |
| T2.5 | `tables/live_provider_manifest.tex`, App. C, Reproducibility Statement | SDK 0.19.2 / openai 2.52.0 / Py 3.14.4; settings; 120 s, no retries; concurrency; cache fields; price formula | `live_provider_manifest.json` |
| T2.6 | `tables/live_catalog.tex`, Fig. 2 barrier band | catalog digests match manifests; 2,351/2,351 tool contracts in final files; 0 undeclared raw tools | `live_catalog_audit.json` |
| T2.7, T4.5 | `results.tex` §5.2, App. F.1, `tables/multirepo_dispatch.tex` | core dispatch 80/120 (all open-class), balanced 180/180; completeness-gate disclosure; overlap wording | `gate_frontier_reanalysis.json`, `cohort_overlap_audit.json` |
| T2.9, T4.4 | `tables/effective_units.tex`, §7, App. G | primary cohorts: 86–90 distinct days, 60–82 authors; cluster-level bound retires in every family | `effective_units.json` |
| T2.10, T4.2 | `tables/mechanism_removal.tex`, §6, §7, App. G | nine sourced hazards; Headroom scoped | — |
| T3.1–T3.5 | `paper/supplementary/{multiplicity-repair,recurrence-only-ablation,graded-frontier,read-only-prologue}-protocol.md` | pre-registered / design-only; no provider call made | — |
| T4.1, T4.3 | abstract, §3, §5.1, §7, App. A/C/F.4/H | Track B certificate wording everywhere; gate = support threshold, q untested | `validate_iclr_sources` |
| T4.6 | §1, §2, §3, §4, §5.1, §5.3, §6, §7; Fig. 1 at 0.72\linewidth | conclusion ends on page 9; AI Use Statement opens page 10 | `pdftotext -f 9 -l 9`, `validate_iclr_page_budget` |
| T6.2, T6.3 | `validate_artifacts.py` (`validate_iclr_sources`), `build_artifacts.py` | new check family; casing fix | validator run |

Not done on this branch (Track R/F, require spend or a later window): T3.1 run, T3.2 run, T3.3 run,
T2.11 recompile of the pytorch retirement (code fix for full retire notes is in; recompile not run),
T2.3 step 3 recompile of the dominated candidates, T4.7 OpenReview metadata paste (user), T5.4 hostile read.

## Follow-up (2026-09-22, same branch)

- T2.3 step 3 / T2.11: `paper/scripts/recompile_retained_candidates.py` recompiles PR-outcome,
  backlog, and `pytorch/pytorch` provider-free from the sealed discovery checkpoints. Determinism
  holds (artifact ids `cand-00-a1de3856bb6c` / `cand-00-99f1b041ed7c`, split digests
  `46a609a3016bcf4a` / `f6a22d6c8895ee87`, U = 0.049808920112407784). The dominated two-read
  candidates are also 92/0, U = 0.0498. The pytorch retirement reproduces with n_eta = 0 at every
  eta (no group accepted at any threshold). Note: the current library mines candidates on train
  groups only (the 2026-08-17 candidate/data-separation fix), so the recompile reports 32/16
  windows where the retained reports say 232/116; artifact identity, splits, and gates are
  unchanged. Appendix C caption and Appendix F.1 updated.
- T4.7: `paper/iclr/notes/openreview_metadata.md` (title, TL;DR, abstract, keywords).
- T5.2: `paper/iclr/notes/number_registry.md`.
- T5.4: two grep-driven read passes (guarantee-level sentences; runtime/implementation claims).
  Findings fixed: Appendix C admission-budget sentence and Appendix G closing paragraph still said
  the primary families were all per-candidate; §2 said "no compiler-wide guarantee" without the
  fixed-m qualification. No systems-claim contradiction found against §2.4 of the plan.
- Reviewer response draft: `paper/iclr/notes/reviewer_response_iclr2027.md`.
- Overfull boxes: discordance and mechanism-removal tables narrowed.

## PAT feedback cross-check (2026-09-22, same branch)

Checked every item of the 12 Sept 2026 PAT feedback (OpenReview `DF0JaS58gr`) against the
build; the item-by-item table is in `reviewer_response_iclr2027.md`. Remaining minor items
closed here: `c_j`/`o_j` defined in the §2 episode tuple; §6 optimizer citations placed per
system; Proposition 1 proof uses `n_eta` throughout and states the `k_eta = n_eta` branch;
`ln` in the sample-size derivation; every main-text pointer to an appendix table names the
appendix; the Appendix E omitted-studies list is kept on one page. Three word-level cuts
(§1, §5.1, §7) hold the conclusion on page 9. Validator: 3142 checks, 0 failed.
Still a user action: replace the OpenReview abstract and TL;DR with `openreview_metadata.md`.

## PAT feedback verification pass (2026-09-23, branch `paper/iclr-2027-pat-feedback-final-pass`)

Independent re-check of every item of the 12 Sept 2026 PAT feedback (OpenReview `DF0JaS58gr`,
export dated 23 Sept 2026) against the sources at 4df8578 (PR #42 head). The arithmetic the
feedback rests on was re-derived and agrees with the manuscript: ln(0.1/11)/ln(0.95) = 91.64 → 92
groups; U(92, 0) = 0.0498; U(91, 0) = 0.0503; U(92, 0) = 0.0569 at γ = δ/22, hence 106 groups;
⌈92/c⌉ = 115 / 132 / 184 for c = 0.8 / 0.7 / 0.5; 10/92 → U = 0.375; 90/92 → U = 0.0509; δ/12 → U =
0.0507; pooled AppWorld eligibility 3,102/8,190 = 37.9%; one-sided 95% bound on 0/90 = 3.3%;
single-threshold unions 1.8% (m = 2) and 13.6% (m = 16). Every PAT item is a correct reading of
the 12 Sept build and was already closed at the PR #42 head, except the residuals below.

| Item | Change | Files |
|---|---|---|
| PAT weakness 1 (situate EvoC2F and Agent JIT) | Appendix G comparator paragraph states what each compiles, from the ICML 2026 abstracts, and why neither yields an admissibility decision to compare against | `appendix.tex` |
| PAT §5.2 item 4 (name the stage that retired `pytorch/pytorch` in the main text) | §5.2 now reads "at admission, where no calibration group is accepted at any threshold" | `sections/results.tex` |
| PAT Eq. (1) vs Algorithm 3 | §2's `Src` enumerates the flattened paths of `z` *and of each prior result*, matching `Flatten(o_j)` in Algorithm 3 | `sections/problem.tex` |
| PAT App. H.1 decision-rule pointer | The Appendix H decision rule now lists the fourth pre-declared outcome (neither gate graded) that the observed-results text invokes; wording taken from the committed protocol table | `appendix.tex` |
| PAT abstract `readonly` | `read-only` is set with `\nobreakdash` in the abstract so the PDF text layer cannot drop the hyphen at a line end; extraction now yields `read-only` 5/5 | `sections/abstract.tex` |
| Own finding | Appendix B called the position check "the first" check; Algorithm 4 resolves the artifact first. Reworded | `appendix.tex` |
| Own finding | Gate-frontier table cell read `60/60/59/60†` under a B/L/S header because the generator stripped `/60` after assembling the cell; generator fixed and table regenerated (`60/60/59†`) | `paper/scripts/iclr_revision_statistics.py`, `tables/gate_frontier_disaggregated.tex` |

Left as is on purpose: the Eq. (5) underbrace artifact and the other abstract hyphenations the
feedback lists (`re-/duce`, `ar-/guments`, `sat-/isfies`, …) are ordinary end-of-line hyphenation
that the reviewer's text copy dropped; the rendered PDF is correct.

Verification: `tectonic --keep-logs --outdir build main.tex`; 29 pages; the conclusion ends on
page 9 (ruler line 485) and the AI Use Statement opens page 10; page 1 reads "Anonymous authors"
and the PDF carries no author; 0 unresolved references; 0 overfull boxes; publication manifest
regenerated; validator 3142 checks, 0 failed. Still a user action: paste `openreview_metadata.md`
(text unchanged by this pass) into the OpenReview abstract and TL;DR fields.

## Live extensions and framing pass (2026-09-24, branch `paper/iclr-live-ablations-recurrence-only-and-second-model`)

Two pre-registered live studies executed (protocols carry their observed-results sections):

| Study | Result | Paper | Evidence |
|---|---|---|---|
| Recurrence-only replay, issue-type (pre-registered 2026-09-22) | 30/30 exact, 1 request/record, no retries; decision-rule row 1 (refusal cost one request per record on this cohort, no measured quality benefit) | App. G paragraph + `tab:recurrence-only`; §7 | `recurrence_only_ablation/{preflight,results}.json`, `tables/recurrence_only.tex` |
| Second model, `gpt-6-luna`, same cohorts (pre-registered 2026-09-24) | 270/270 episodes; artifacts reproduce under the new pin; 30/30 dispatch per family; pooled 88/90 vs 88/90 vs 90/90; one compiled-only miss (issue-type #6532, excerpt pluralized one word); reductions 66.6/63.0/59.5/60.1 | App. G paragraph + `tab:second-model`; §5.1; §7 | `second_model_replication/{issue_type/*,summary.json}`, `github_workflow_families/*/gpt6_luna/`, `tables/second_model.tex` |

Framing pass (facts unchanged): §1 contribution 3 is "calibrated refusal" rather than "a
negative-result boundary" and contribution 1 states the novelty once ("to our knowledge the first
exact finite-sample admission certificate for trace-derived agent compilation"); §5.1 opens the
manual comparison with "Discovery reaches the manual ceiling"; §7 states the safety headline
recomputed from the per-record files (630 compiled held-out episodes on the calibrated model,
zero compiled-only failures: 90 + 120 + 180 + 240) and that every limitation is paired with a
committed protocol; §7's provider sentence now says one *calibrated* model family and points to
the transfer. Abstract unchanged (the transfer protocol allowed an abstract change only if all
three families preserved, and issue-type did not).

Page budget: the additions (§1 +2 lines, §5.1 +2, §7 +5) were paid for by Figure 1 at
0.52\linewidth and word-level cuts in §1, §2, §3, §4, §5.2, §5.3, §7; the conclusion ends on page 9
again and the AI Use Statement opens page 10. `demos/live_runtime.py` gains the `gpt-6-luna` list
price (retrieved 2026-09-24); `validate_live_extensions` pins both studies, the 630 headline, and
byte-identical regeneration of the two new tables.

## Re-discovery, extended held-out, prologue, caveats, packaging (2026-09-24, branch `paper/iclr-live-rediscovery-heldout-prologue`)

| Study / item | Result | Paper | Evidence |
|---|---|---|---|
| Multiplicity repair (pre-registered 2026-09-22) | NO-GO at preflight: 33 unused `open` PRs, 8 unused `owned` issues against 36 per class; not run, per-candidate wording stays | App. A | `multiplicity_repair/preflight.json` |
| Design A re-discovery on `gpt-6-luna` (pre-registered 2026-09-24) | issue-type 128/132 exact traces, identical artifact, 30/30/30; PR-outcome 132/132, identical artifact, 30/30/30; backlog 113/132 < 116 → compile-time refusal, no arms run | App. G (+ design-A block of `tab:second-model`), §5.1 | `second_model_replication/issue_type_rediscovery/`, `github_workflow_families/*/gpt6_luna_rediscovery/` |
| Extended issue-type held-out, 120 records on the calibrated model (pre-registered 2026-09-24) | 118/118/117 of 120; one compiled-only miss (2737), dispatch 119/120 (5102 cardinality abstention); bound 3.9% here, 2.2% pooled (1/210); all three targets missed and reported | App. D + `tab:extended-heldout`; §5.1; §7 headline now 750 episodes / 1 compiled-only failure | `issue_type_extended_heldout/results.json` |
| Read-only prologue (protocol 2026-09-22) | implemented in the runtime (23 acceptance tests, suite 496 green), measured on the released AppWorld trajectories after acquiring them: ReAct 0 → 2 of 2,340, plan-and-execute 1 → 1; those architectures do not execute the admitted region (16 and 39 occurrences anywhere) | App. G replaces the conjecture; `tab:appworld-prologue`; §5.3 clause | `external_benchmarks/appworld_dispatch_prologue_preflight.json`, `tests/unit/test_dispatch_prologue.py` |
| Two operational caveats | closed provider-free: perturbation suite runs through a snapshot sandbox on the recompiled artifacts (9 families, 8 dev windows, 0 wrong, 0 hard rejects, identical programs/gates); HMAC-signed registries verified, unsigned/tampered refused | App. G | `iclr_revision/recompile_with_challenge.json`; `validate_recompile_with_challenge` |
| Packaging | `fig:gate-floor` (why 92 groups certify only coverage 0 or 1) in App. C; `tab:claims-evidence` in a new Appendix I | App. C, App. I | `paper/scripts/plot_gate_floor.py`, `tables/claims_evidence.tex` |

Not done: the certified-frontier study (recommended against: every calibration label in the paper
is a replay-contract violation on deterministic tools and there have been none, so the gate picks full
coverage at any pool size); the second-provider replication (protocol pre-registered,
`second-provider-replication-protocol.md`, model `claude-opus-5`; the Agents-SDK adapter on the
official `anthropic` SDK is partially written and untested); the drift-robustness ablation and the
anonymous-archive builder (see the branch state). Page budget: the §5.1 and §7 additions were paid
for by cuts in §5.1, §6, and §7; the conclusion ends on page 9.

## Second provider (2026-09-24, same branch)

Anthropic `claude-sonnet-5` through a new Agents-SDK adapter on the official SDK; design A on all
three families (pre-registered `second-provider-replication-protocol.md`). Issue-type and PR-outcome
re-derive the identical artifacts (30/30 dispatch); backlog retires at calibration with 91/92
groups accepted at best. Compiled-only misses on issue-type (2) and PR-outcome (2), all
excerpt-fidelity errors of the model present in every arm; reported first. App. G paragraph +
`tab:second-provider`; §5.1 and §7 clauses. Also this branch: the CI fix for the pilot
disjointness test and the disclosed five-record overlap of the extended cohort with the pilot.
