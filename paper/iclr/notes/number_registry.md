# Number registry for the ICLR 2027 paper

Selected numerical claims from the September revision, supplemented by the
October 8 evidence audit, with retained files or producing scripts. Citation
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
| 80 | Disjoint historical discovery issues used to re-derive the compatible candidate before any new-cohort compiled result | `graded_issue_gate/candidate_v2/summary.json`; appendix `app:prospective` | `graded_issue_recompile_candidate.py` |
| 4, 2 | Final factual-task errors on 200 development and 184 calibration dispatches (all dispatched) | `audit_v2.json` `groups` | `audit_graded_issue_gate.py` |
| 64/184, 0.0708; 153/184, 0.0546 | Frozen eleven-point grid at $\eta=0.02$ (0 violations) and $\eta=0.50$ (2 violations): upper bounds above the 0.05 limit, so no threshold is admitted and the gate retires before the test | `audit_v2.json` `calibration_grid` | `audit_graded_issue_gate.py` (exact counts and bounds) |
| 184/184, 2 | Support-only ablation accepts every calibration group with the same two errors; it disables the risk budget, so no held-out comparison follows | `audit_v2.json` | same |
| $0.1627 | Estimated spend of the amended run | `audit_v2.json` `v2_estimated_cost_usd` | spend arithmetic check in the audit |
