# Number registry for the ICLR 2027 paper

## October 28 interpretation corrections

| Number(s) | Meaning | Source | Checked by |
|---|---|---|---|
| 54,045/67,074; 80.6% | OpenHands first call is think | `paper/results/prefix_census/results.json`, `first_call` | `validate_prefix_census` |
| 58,682/67,074; 87.5% | OpenHands first blocking tool is think, possibly after reads | Same corpus, `first_barrier` | `validate_prefix_census` |
| 261/311; 4; 0.0443 | Extension selected coverage, errors and nominal upper bound | `paper/results/graded_issue_gate/audit_extension.json` | Existing numerical audit; coverage for the adaptive mixed-frame procedure is not established |
| 411; 183; 181 | Whole-episode discovery break-even per family and compatible snapshot | `paper/results/cache_accounting.json`, ceiling of each `break_even_episodes` | Arithmetic; excludes lifecycle costs |

The extension interpretation is corrected separately in
`paper/results/graded_issue_gate/interpretation_correction.md`; the historical
protocol and raw numerical artifacts are unchanged. The new matched-compiler
protocol is unrun and contributes no observed numbers to this registry.

## Retained numerical claims

Selected numerical claims from the September revision, supplemented by the
October 8 evidence audit and October 15 live-recovery integration, with retained files or producing scripts. Citation
years, equation constants, and grid values are omitted. `stats:` means
`paper/scripts/iclr_revision_statistics.py` writes it under `paper/results/iclr_revision/`;
`validator` means `validate_iclr_sources` pins it.

| Number(s) | Meaning | Source | Checked by |
|---|---|---|---|
| 90/90, 89/90 | exact contracts, compiled vs unchanged agent, 90 held-out records | `github_workflow_families/summary.json` `overall.compiled_exact`, `baseline_exact` | validator |
| 66.6, 63.1, 64.2, 58.7 (%) | pooled reductions: requests, tokens, latency, cost | `summary.json` `overall.*.reduction` | validator |
| 50.0/0.0/39.5/51.7/32.0; 75.0/66.7/80.8/73.0/75.3; 74.8/66.3/81.4/68.9/75.1 | per-family reductions (Table 1) | `summary.json` `families[].reductions` | validator |
| 66.5 vs 44.2 (%) | manual vs compiled interface reduction (Table 4, text removed from §5.1) | `summary.json` manual/compiled `tool_calls` | build_github_family_summary |
| 132, 30 | discovery and held-out records per family | `results.json` `selection.discovery`/`test` lengths | validate_github_workflow_families |
| 16 / 8 / 92 | train / dev / calibration groups | `compiler.splits.sizes` | validate_github_workflow_families |
| 92, 0.0498, 0.0503, 91.6 | zero-violation floor, U(92), U(91), log ratio | `grc/calibrate.py` closed form; `stats:multiplicity_accounting.json` | validator, test_statistics_and_estimate |
| 0.0569, 0.057, 106 | two-candidate corrected bound at n=92 and groups needed | `stats:multiplicity_accounting.json` `u_at_92.2`, `n_min.2` | validator |
| 45, 59, 77, 93; 0.0247, 0.0320 | single-rule floors (k=0, k=1 at m=1, 2) and U(92) | `stats:single_rule_sensitivity.json` `n_min_single`, `u_at_92_single` | validator (table regenerates), test_iclr_revision_statistics |
| 0.0253–0.0342, 0.0277–0.0880, 25 | single-rule bounds at distinct days / authors; streamlit author count | `stats:single_rule_sensitivity.json` `clusters` | validator (table regenerates), test_iclr_revision_statistics |
| 144, 6, 3, 0.0206, 0.2477, 0.3333 | drift ablation: paired groups, artifacts, demonstrations, upper bound on zero wrong groups, guarded invariant abstention pooled / permissioned_rag | `drift_ablation/results.json` `pooled`, `demos.*.artifacts.*.arms` | validate_drift_ablation, test_drift_ablation_study |
| 89, 0.0331, 0.1049, 0.0444/0.1222/0.1494, 5189 | recorded-replay drift ablation: paired records, upper bound on zero wrong, guarded invariant abstention pooled and per family, excluded record | `drift_recorded_replay/results.json` `pooled`, `families.*` | validate_drift_recorded_replay, test_drift_recorded_replay_study |
| 1,095, 811, 60/132/132, 131/132, 132/0, 0.0173, 60/60, 75.0/82.7/80.0/76.6 | time-forward PR-outcome: records, fresh PRs, splits, discovery exact, end-to-end calibration, bound, evaluation, reductions | `time_forward/pr_outcome/{selection,discovery_checkpoint,certificate,evaluation}.json` | validate_time_forward_pr_outcome |
| 1,080, 60, 39/39, 19/20, 11–14, 0.1389 | continuation-graded drift: cells, records, silent-wrong records per arm, per family, guarded abstentions on duplicate/pad, invariant fallback rate | `drift_continuation_graded/results.json` `per_cell`, `silent_wrong_records`, `invariant_fallback_rate` | validate_drift_continuation_graded |
| m = 1, 2, 2 | candidates reaching calibration (issue-type, PR, backlog) | `compiler.candidates` (issue-type), `compiler.report` (PR, backlog); `stats:multiplicity_accounting.json` | validator, recompile_retained_candidates |
| 5189 | the baseline-only miss | backlog `results[]` `issue_number 5189`, `quality.comment_grounded false` | `stats:paired_statistics.json` `discordance.backlog_attention.compiled_only_records` |
| 1 / 0, p = 1, 3.3 % | discordant cells, McNemar, upper bound on compiled-only failure | `stats:paired_statistics.json` `discordance.pooled` | test_iclr_revision_statistics |
| 30/30 (2026-08-18) | baseline rerun on the same records | `github_workflow_families/*/headroom_ablation/results.json` | validate_headroom_ablation_preflights |
| 4420, 132, 100, 6602, 45, 17/18, 18/18 | introduction example | `github_natural_replication/results.json` `compiler.candidates`; `github_natural_live/continuation_replay.json` | validate_natural_replication, validate_continuation_replay |
| 120/120, 580/580, 44.4, 52.4, 49.4, 48.6 | core protocol | `github_multirepo_pr_outcome_core/results.json` `comparisons` | validate_github_multirepo_pr_outcome_core |
| 80/120, 20/30, 10 per repo, 2/0/3/0 open | core held-out dispatch, fallback per repo, open records in discovery | `stats:gate_frontier_reanalysis.json` `core` | test_iclr_revision_statistics |
| 180/180, 66.7, 78.4, 60.7, 72.7, 360/360 | balanced rerun | `github_multirepo_pr_outcome_balanced/results.json` | (hand-typed table; T6.2 does not pin balanced yet) |
| 84/30/2, 116 | pytorch discovery class mix and windows | core `repositories[pytorch].selection.discovery_class_counts`, `error` | `stats:frontier`; recompile_retained_candidates |
| 240, 300, 719/720, 240/240, 240/240, 239/240, 239/239, 6708, 120 s | gate-frontier accounting | `github_multirepo_gate_frontier/results.json`; `stats:gate_frontier_reanalysis.json` | validator |
| 160/240, 159/239, 80, 20 | held-out dispatch and open-class fallbacks | `stats:gate_frontier_reanalysis.json` `gate_frontier.pooled` | validator |
| 44.4, 52.3, 51.0, 48.3; 44.4, 52.4, 47.9, 48.8 | learned / support-only reductions | gate-frontier `comparisons.*.aggregate_reduction` | `stats:gate_frontier_reanalysis.json` `comparisons` |
| 0.1087, 0.375, 10/92; 90/92, 0.0509 | uncertifiable intermediate coverages | gate-frontier `coverage_curves`; balanced pandas `gate.notes` | test_iclr_revision_statistics (0.1087, 0.375) |
| 0.0507, δ/12, 1.0 | support-only bound, grid split, threshold | gate-frontier `compilers.support_only.artifact.gate` | test_iclr_revision_statistics |
| 0.0169, 0.0815 | constant held-out q per repository | gate-frontier `results[].dispatch.q` | `stats:gate_frontier_reanalysis.json` `arms.*.q_values` |
| 561/580, 442/460, 130/150, 93–95 %; 13, 25, 8 | cohort overlaps | `stats:cohort_overlap_audit.json` | test_iclr_revision_statistics |
| 2026-08-22T18:59Z | smoke-run timestamp of the reused `psf/requests` block | gate-frontier `repositories[psf/requests].run.timestamp_utc` | manual (agent audit) |
| $0.41 | retained spend, successful attempts | `stats:gate_frontier_reanalysis.json` `retained_cost_usd_successful_attempts` (0.4058) | test_iclr_revision_statistics |
| 86–90, 60–82, 45–50 | distinct days / authors / months per 92-record cohort | `stats:effective_units.json` `primary_ranges` | test_iclr_revision_statistics |
| 43.2–78.6 %, 0.3 pt | per-permutation latency reduction range; wall vs provider | `stats:order_sensitivity.json` | (not pinned; regenerate to check) |
| 2,351/2,351 | tool-contract compliance, final result files | `stats:live_catalog_audit.json` `tool_contract` | (not pinned) |
| 0.19.2, 2.52.0, 3.14.4 | SDK / client / Python versions | `results.json` `run.*` | `stats:live_provider_manifest.json` |
| 0.20 / 0.02 / 0.25 / 1.20, 2026-08-02 | price table and retrieval date | `demos/live_runtime.py:58-65` | validate_live |
| 8, 6, 120 | max_turns (families, cross-repo), timeout seconds | study scripts (`run_batch`) | manual |
| r* ≈ 0.637, 0.00909, 1.8 %, 13.6 %, 0.81 %, 56 %, 20260822, 200,000, 46, 0.3 | multiplicity simulation | `frozen_candidate_coverage_simulation.json` | test_frozen_candidate_coverage_simulation |
| 1,415; 212; 200; 1,142; 136/147; 7,070; 26; 8; 15; 8,190; 2,339/2,340; 762/1,170; 1/4,680; 37.9 %; 3,752; 61; 0.377; 0.380; 34/0/0; 11/11 | external substrates (unchanged this revision) | `paper/results/external_benchmarks/*.json`, `nestful/results.json` | validate_external_benchmarks, validate_bfcl_compiler |
| 23, κ = 3, depth 2, |Λ| = 11, α = 0.05, δ = 0.1 | configuration | `compiler.config`; Table 3 | validate_claim_boundaries |

Rows marked "not pinned" are candidates for the next validator extension.
| 30/30, 1.00, 1,167, 2.67, 0.038 | recurrence-only replay on issue-type routing: exact, requests, tokens, latency (s), cost (¢) per record; retained arms 4.00/2.00/2.00 requests | `recurrence_only_ablation/results.json` `per_field_exact`, `aggregate`; `tables/recurrence_only.tex` | `validate_live_extensions` (table regenerates) |
| 630, 0 | historical four-study subset of compiled held-out episodes on the calibrated model across the four live studies (90 primary + 120 core + 180 balanced + 240 gate-frontier learned gate) and compiled-only contract failures among them | per-record `results[]` of `github_natural_replication`, `github_workflow_families/*/final`, `github_multirepo_pr_outcome_{core,balanced}/repos/*`, `github_multirepo_gate_frontier/repos/*` | `validate_live_extensions` |
| 128/132, 132/132, 113/132; 116 | exact discovery traces per family on gpt-6-luna under design A and the 16/8/92 requirement | `second_model_replication/issue_type_rediscovery/results.json` `discovery`; `github_workflow_families/pr_outcome/gpt6_luna_rediscovery/discovery_checkpoint.json`; `.../backlog_attention/gpt6_luna_rediscovery/failure.json` | `validate_live_extensions` |
| 50.0/38.9/32.8; 75.0/80.7/76.0 (%) | design-A reductions (requests/tokens/cost), issue-type and PR-outcome on gpt-6-luna | `second_model_replication/summary.json` `rediscovery` | summary regenerates |
| 33, 8, 36, 357 | multiplicity-repair NO-GO: unused open PRs, unused owned issues, required per class, excluded records | `multiplicity_repair/preflight.json` | `validate_live_extensions` |
| 2/2,340, 1/2,340, 2 and 3, 16 and 39 | read-only prologue: ReAct and plan-and-execute eligibility after an exact prologue; looser documentation-prefix diagnostic; program-occurs-anywhere ceilings | `external_benchmarks/appworld_dispatch_prologue_preflight.json` `by_agent_family`; retained `appworld_dispatch_preflight.json` | `validate_live_extensions` |
| 118/120, 118/120, 117/120; 119/120; 2737, 3040, 3968, 5102; 3.9%, 2.2% (1/210); 50.0/39.5/42.5/32.8 | extended issue-type held-out (calibrated model): exact per arm, dispatch, the miss records and the abstaining record, compiled-only bounds, reductions | `issue_type_extended_heldout/results.json`; `tables/extended_heldout.tex` | `validate_live_extensions` (table regenerates) |
| 750, 1 | compiled held-out episodes on the calibrated model across five live studies and compiled-only failures among them (630 + 120 extended; record 2737) | per-record `results[]` of the five studies | `validate_live_extensions` |
| 9 families, 8 dev windows, 0 wrong, 0 hard rejects | perturbation challenge on the three primary artifacts, recompiled provider-free; signed registries verified | `iclr_revision/recompile_with_challenge.json` | `validate_recompile_with_challenge` |
| 126/132, 128/132, 116/132; 29/28/28, 27/27/29; 4248, 6829, 5401, 6988; 91, 90, 0.050, 0.051; 48.3/40.4/39.8, 75.0/84.9/83.4 | second provider (Anthropic claude-sonnet-5, design A): exact discovery traces, exact contracts per arm, compiled-only miss records, backlog calibration refusal, reductions | `second_provider_replication/{issue_type/results.json,summary.json}`, `github_workflow_families/*/anthropic_sonnet5_rediscovery/{results,failure}.json`; `tables/second_provider.tex` | `validate_live_extensions` (summary/table regenerate) |

## October 8 denominator and consistency audit

| Numbers | Meaning | Retained source | Check |
|---|---|---|---|
| 150/150, 150/150, 150/149, 630/625 | Scheduled/four-arm-complete questions: BIRD primary, rotated, second model, training split | `paper/results/bird/denominator_audit.json` | `audit_bird_denominators.py`; validator and regression tests |
| 94/97, 94/100, 91/93, 403/402 | Unchanged/compiled correct counts over all scheduled questions | Same audit; missing own-arm runs counted incorrect | Per-arm execution records |
| 18/17, 1.0; 3/5, 0.7265625 | Baseline-only/compiled-only correct and exact paired p-values: training and second model | Same audit | SciPy exact binomial test |
| 629, 45.8%, 18.0%; 150, 49.6%, 5.8% | Completed baseline/compiled resource pairs, request and cost reductions: training and second model | Same audit | Deterministic per-record metric sums |
| 810, 1 | Six specified GitHub studies, compiled-only failures; includes 120 extended and 60 post-cutoff episodes beyond the older 630 subset | Per-record outputs of the six studies | `validate_live_extensions` |
| 39, 40 | Drift wrong-answer records under original versus corrected grader | `drift_continuation_graded/results.json` and disclosed substring artifact | Original grading preserved; correction distinguished |
| 411, 183, 181 | Primary discovery-cost break-even episodes | `paper/results/cache_accounting.json` (ceiling of break-even episodes) | Retained resource audit; README corrected |

## Additional existing-data sensitivity analysis

| Number(s) | Meaning | Source | Checked by |
|---|---|---|---|
| [-4.40, +8.18]; [-2.53, +10.11]; [-5.44, +7.97]; [-3.27, +2.96] pp | Pointwise conservative paired 95% intervals, primary / rotated / second model / training; conditional on iid question pairs | `bird/quality_sensitivity.json` | `bird_quality_sensitivity.py`, tests, validator |
| [-0.50, +0.33] pp; 5/10/6 | Training whole-database deletion range; positive / zero / negative database differences | `bird/quality_sensitivity.json` | same |
| $0.891759; $0.728806; $0.162952 | Training completed baseline / compiled evaluation cost; maximum unrecorded net compiled cost before savings reverse | `bird/quality_sensitivity.json` | same |

## October 8 amended end-to-end issue gate

| Number(s) | Meaning | Source | Checked by |
|---|---|---|---|
| 474, 200, 184, 90 | Pinned issue cohort and its disjoint development, calibration and untouched test split; the 90 test issues were never run | `graded_issue_gate/preflight.json` `quota_by_stratum_and_role`; `audit_v2.json` `test_issues_untouched` | `audit_graded_issue_gate.py` |
| 288 | Ordinary fallbacks before the first attempt stopped on a manifest mismatch (retained as an abort, not as a result) | `graded_issue_gate/abort_v1.json` `completed_fallback_episodes` | `audit_graded_issue_gate.py` |
| 80 | Disjoint historical discovery issues used to re-derive the compatible candidate before any new-cohort compiled result | `graded_issue_gate/candidate_v2/discovery.json` (80 `results`); `candidate_v2/started.json` `new_cohort_overlap` = 0 | `graded_issue_recompile_candidate.py` |
| 4, 2 | Final factual-task errors on 200 development and 184 calibration dispatches (all dispatched) | `audit_v2.json` `groups` | `audit_graded_issue_gate.py` |
| 64/184, 0.0708; 153/184, 0.0546 | Frozen eleven-point grid at $\eta=0.02$ (0 violations) and $\eta=0.50$ (2 violations): upper bounds above the 0.05 limit, so no threshold is admitted and the gate retires before the test | `audit_v2.json` `calibration_grid` | `audit_graded_issue_gate.py` (exact counts and bounds) |
| 184/184, 2 | Support-only ablation accepts every calibration group with the same two errors; it disables the risk budget, so no held-out comparison follows | `audit_v2.json` | same |
| 127, 80/43/4, 311, 1,728, 55 | Sequential extension: forced-size fresh calibration cohort and strata, pooled groups, `experiments/` record numbers now excluded, pilot-only records kept excluded | `graded_issue_gate/extension_preflight.json` `remaining_pool`, `exclusion` | `validate_graded_issue_gate_extension` (sealed cohort rebuilds byte-identically) |
| 2, 4; 117/311, 0.0394; 261/311, 0.0443; 0.50; 0.0682 | Fresh and pooled task errors; pooled grid at $\eta=0.02$ and $\eta=0.50$; admitted threshold (largest of six admissible points, not an interval); best fresh-only bound (retire) | `graded_issue_gate/audit_extension.json` `grids` | `audit_graded_issue_gate_extension.py` (exact counts and bounds); validator regenerates `gate_extension.tex` |
| 4/194, 0/117, 0.150 | Descriptive split at $\eta=0.02$ and one-sided Fisher $p$ (no selectivity evidence) | `audit_extension.json` `fisher_split` | same |
| 76/90, 3/90, 2/90, 5/90, 2/76, 8.4%, 8.1%, 85/3/2/0, 132/360 | Test routing, learned / unchanged / support-only errors, errors after compiled dispatch (4149, 7291), one-sided 95% bounds, paired cells, provider requests | `audit_extension.json` `test`; `results_extension.json` `outcomes` | validator |
| $0.19, 397, $0 | Extension estimated spend and attempted episodes; aborted first attempt (401) spent nothing | `results_extension.json` `spend`; `extension_abort.json` | validator |
| $0.1627 | Estimated spend of the amended run | `audit_v2.json` `v2_estimated_cost_usd` | spend arithmetic check in the audit |

## October 15 safeguard and recovery additions

Paths below are repository-relative. The live completion analyzer audits the
sealed checkpoint before computing the retained analysis; paired intervals are
descriptive and unadjusted. Variants are grouped by issue, not treated as
independent episodes.

| Number(s) | Meaning | Source | Checked by |
|---|---|---|---|
| 120; 480; 120/120 vs 118/120; 50.0%, 45.8% | Fresh records, four-arm episodes, registered factuality, request/cost reductions | `experiments/fresh_safeguards/analysis/analysis.json` | `analyze_fresh_safeguards.py`; endpoint and error audit |
| 2,880; 288/288 vs 260/288 or 252/288 | Provider-free evaluations; ordinary scope and capped completeness contrasts | `experiments/safeguard_mechanisms/artifacts/run/summary.json` | `safeguard_mechanism_study.py`; deterministic replay |
| 2,304; 2,300; 4; 2,186; 114 | Scheduled/attempted, completed, timed out, correct, completed incorrect | `experiments/live_recovery_completion/analysis.json` | `complete_live_recovery.py` audit and analysis |
| 72 / 24; 216 / 72 | Confirmation/replication issue groups; scheduled cases per arm and condition | Same analysis, `groups`; prospective `seal.json` | Sealed schedule and direct checkpoint counts |
| 205/216 vs 186/216; +8.80 [3.70,13.89] pp | Ordinary confirmation scope contrast, issue-bootstrap interval | Same analysis, `groups.confirmation.ordinary` | Analyzer; manuscript table checked against retained JSON |
| 205/216 vs 204/216; 22/27 | Capped confirmation completeness contrast and successful repairs | Same analysis, `groups.confirmation.capped_response_stress` | Analyzer; incomplete-prefetch subset |
| -18.2%, -9.1%; 71→70, 70→68 of 72 | Replication model-cost changes and correct answers, ordinary/capped | Same analysis, `groups.replication` | Completed mean ratios; all replication episodes complete |
| $0.952696; $7.001762 | New-run known cost; aggregate estimates plus failure/diagnostic reserves | Same analysis, top-level spend fields | Analyzer; frozen rate estimates, not invoices |

## October 15 matched workflow-memory comparison

All paths below are repository-relative. The frozen analyzer regrades source
answers, replays successful tool outputs and recomputes usage before producing
these values. This cohort is not pooled into the historical 810 episodes.

| Number(s) | Meaning | Source | Checked by |
|---|---|---|---|
| 130; 6 / 120; 18 / 360 | Shared eligible discovery traces; pilot / primary issue groups and episode counts | `experiments/matched_reuse_baseline/seal.json` | Provider-free preflight and seal verification |
| 378; 377; 1 | Attempted; completed; GAC schema failure, with no retry | `experiments/matched_reuse_baseline/analysis.json` | Frozen runner audit |
| 116/120 vs 114/120 vs 114/120 | Primary seven-field correct, GAC / adapted AWM / baseline | Same analysis, `groups.primary.arms` | Existing source grader; failed episode retained |
| 119/120 vs 117/120 vs 117/120 | Historical four-field factuality endpoint | Same analysis, `groups.primary.arms` | Same audit; separate endpoint |
| +1.67 [0,4.17] pp; 0.50; 1.00 | GAC minus adapted AWM, descriptive paired bootstrap; exact McNemar p; Holm p | Same analysis, primary contrasts | 120 paired issue groups; no superiority/equivalence claim |
| 2 vs 4; 3; 30.8%, 30.1% | Provider requests; tools in every arm; all-attempted deployment cost reductions versus adapted AWM and baseline | Same analysis, primary observed resource totals | Ratios of observed totals; all response usage present |
| -0.0002963 [-0.0003126,-0.0002800] USD; -2.109 [-2.268,-1.954] s | Paired cost and latency differences, 119 completed GAC-AWM pairs | Same analysis, primary contrast | Descriptive paired issue bootstrap; excludes failed pair |
| $0.0025674; $0.30665104; $8.57705193 | Induction; all new known study cost; aggregate estimates and reserves | Same analysis plus checkpoint metrics | Frozen rate card, all observed usage, retained failure reserve |

## October 15 fresh generalization and gate attribution

The immutable prospective analyzer regrades source answers, replays tools,
checks memories and recomputes usage. The 1,362 distinct records are not pooled
into the historical 810 episodes; the two models reuse the same records.

| Number(s) | Meaning | Source | Check |
|---|---|---|---|
| 1,362; 8,172 / 8,171 / 1; 108 / 107 | Unique records; attempted/completed/failed; pilot attempted/correct | `experiments/generalization_gate/{seal,checkpoint,analysis}.json` | Frozen `generalization_gate_study.py analyze` |
| 143/142/144; 142/143/144 (n=144) | Backlog GAC/AWM/baseline successes, first/second model | Same analysis, backlog cells | Source regrade; generated accuracy table |
| 584/583/590; 583/583/582 (n=600) | Issue GAC/AWM/baseline successes | Same analysis, issue cells | Same |
| 597/598/597; 598/600/599 (n=600) | PR GAC/AWM/baseline successes; failed baseline counted incorrect | Same analysis, PR cells | Same |
| 3.27, 5.86, 3.61, 4.04, 1.43, 1.43 pp; 5/6, 2/6, 0/6 | Conservative loss bounds, six-comparison correction; cells passing 5pp/2pp/1pp margins | Same analysis, per-cell bound/sensitivity flags | Exact binomial upper bound at 0.05/6 |
| 50–75%; 36.9–79.1% | Request and estimated deployment cost reductions vs adapted AWM | Same analysis, primary observed totals | `render_manuscript.py`; both compared arms complete |
| 2,724; 0; 600/606 | Three gate probe cases; live dispatch mismatches; issue dispatches per model including pilots | `seal.json`, `error_audit.json` | Real dispatcher and post-run dispatch audit |
| 113; 50/45/46/12/5 | Incorrect/failed episodes including pilot; overlapping excerpt/category/label/comment/title failures | `error_audit.json` | `audit_results.py`; unchanged grading |
| 0; 1; 27 | Owned backlog, open primary PR, nonliteral bug-label records | `source_audit.json` | `audit_sources.py`; no selection changes |
| $3.864269; $0.011211; $13.441321; 1 | New observed cost including induction; induction subtotal; aggregate estimate/reserves; missing baseline usage response | `manuscript_numbers.json`, checkpoint and analysis | Usage audit; unknown charge not treated as zero |

## October 28 prefix census (appendix, `tab:prefix-census`)

Produced by `paper/scripts/prefix_census.py run`; `validate_prefix_census` pins the
manifests, catalog digests, gate floor and byte-identical table regeneration. Shares are
`read_only_opening.share_ge2` / `groundable_opening.share_ge2` per row of
`paper/results/prefix_census/results.json`.

| Numbers | Meaning | Retained source | Check |
|---|---|---|---|
| 67,074; 6,306; 16.3 %; 12.8 %; 3; 27 / 22; 752; 11; 87.5 % | OpenHands primary: traces, tasks, RO≥2, groundable≥2, median length, families / at floor, n_max, families at or above 92, first barrier = `think` (58,682) | `corpora[openhands/primary]` | `validate_prefix_census` (table regenerates) |
| 16.3 %, 12.9 %, 752 | OpenHands shell-reads arm | `corpora[openhands/shell_reads_admitted]` | table regenerates |
| 80,036; 3,591; 32.5 %; 1.9 %; 2; 154 / 36; 187; 2; 47.0 %; 24,399 | SWE-agent primary: traces, tasks, RO≥2, groundable≥2, median length, families / at floor, n_max, families at floor 92, first call = `create` (37,622), openings blocked on an ungrounded slot | `corpora[sweagent/primary]` | table regenerates |
| 47.3 %, 2.0 %, 187 | SWE-agent shell-reads arm | `corpora[sweagent/shell_reads_admitted]` | table regenerates |
| 1,980; 165; 3.9 %; 3.0 %; 7; 99.7 % | tau-bench strict: traces, tasks, RO≥2, groundable≥2, n_max, openings cut by a user turn (1,974) | `corpora[taubench/primary]` | table regenerates |
| 51.7 %, 16.6 %, 17 | tau-bench folded arm | `corpora[taubench/pre_tool_user_turns_folded]` | table regenerates |
| 1,415; 100 %; 86.6 %; 76 | NESTFUL openings (w_max = 12): traces, RO≥2, groundable≥2, n_max | `corpora[nestful/primary]` | table regenerates |
| 8,190; 41.0 %; 99.96 / 71.4 / 5.7 / 2.1 %; 45.9 % | AppWorld released: traces, RO≥2, by architecture (full-code, ipfuncall, ReAct, plan-exec), first barrier = API-documentation call (3,758) | `corpora[appworld_released/primary]` `by_architecture`, `first_barrier` | table regenerates |
| 13; 32,000 | calls ingested per trajectory (w_max + 1); observation cut length | `max_calls_ingested`; `benchmarks/external/trajectories.py` `MAX_OBSERVATION_CHARS` | test_prefix_census |
