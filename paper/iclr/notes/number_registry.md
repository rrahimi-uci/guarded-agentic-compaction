# Number registry for the ICLR 2027 submission (PR #41 head)

Every numeral quoted in `paper/iclr/sections/*.tex` and the parts of `appendix.tex` the
2026-09 revision touched, with the retained file or script that produces it. Citation
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
| 630, 0 | compiled held-out episodes on the calibrated model across the four live studies (90 primary + 120 core + 180 balanced + 240 gate-frontier learned gate) and compiled-only contract failures among them | per-record `results[]` of `github_natural_replication`, `github_workflow_families/*/final`, `github_multirepo_pr_outcome_{core,balanced}/repos/*`, `github_multirepo_gate_frontier/repos/*` | `validate_live_extensions` |
