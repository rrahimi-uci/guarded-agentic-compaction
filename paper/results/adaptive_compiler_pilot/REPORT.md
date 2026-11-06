# Adaptive compiler pilot: results and decision

**Exploratory pilot only. NO-GO for confirmatory execution or a new quality certificate.**

The amended protocol scheduled 108 episodes on 36 questions: four per each of nine databases. This weights databases equally within the pilot; it is not a random sample of the complete BIRD benchmark. Tasks came from the pinned corrected dev release after the documented prior-use, exact-duplicate, web-exposure and executable-gold screens. All failures stay in the denominator. All pilot IDs are excluded from future calibration and final testing.

## Observations

| Arm | Set-correct / scheduled | Completed / failed / unstarted | Provider requests | Tool calls | Accounted upper USD | Median processing seconds |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| agent_jit | 4/36 | 20 / 16 / 0 | 1153 | 97 | 1.2461 | 17.86 |
| baseline | 26/36 | 36 / 0 / 0 | 152 | 116 | 0.0838 | 4.76 |
| manual_prefetch | 27/36 | 36 / 0 / 0 | 64 | 100 | 0.0962 | 2.56 |

Paired descriptive outcomes against the baseline (no hypothesis test):

- manual_prefetch: 3 correct-only-in-arm; 2 correct-only-in-baseline; 31 agreements.
- agent_jit: 1 correct-only-in-arm; 23 correct-only-in-baseline; 12 agreements.

Agent JIT produced 1152 retained sampled candidates, of which 599 passed its static checks. Selection used minimum upstream estimated runtime cost, with generation order breaking ties; no gold answer was used in selection. Static validity did not establish correct final answers. Failed-arm exception classes: `{'ValueError': 11, 'RuntimeError': 5}`.

The stronger row-shape and duplicate-sensitive diagnostics remain in `report.json`; they are not independently annotated semantic oracles. Primary set agreement ignores order and duplicate multiplicity. Processing time includes final SQL grading and local orchestration; it is not a clean deployment-latency estimate. Provider accounting includes all candidate generation and runtime inference, but excludes human engineering, machine rental and provider-independent setup cost.

## GAC feasibility

All 36 scheduled baseline IDs retain their preassigned discovery role; 36 attempts were converted to observable traces. Incorrect answers and failed attempts were not selected away. The compiler's own trace qualification and rejection reasons are retained.

```text
GRC compile report
──────────────────
candidates mined        0
artifacts emitted       0
rejections by stage     {}
windows accepted        0
windows blocked         {'ungrounded_slot': 79, 'error_event': 6, 'partial_run': 10}
blocked by tool         {}
```

The adapter returns JSON inside a payload string. A separately labeled, posthoc diagnostic decodes those results into typed fields before discovery:

```text
GRC compile report
──────────────────
candidates mined        1
artifacts emitted       0
rejections by stage     {'mine:low_support': 7, 'synthesize:ungroundable_slot': 1}
windows accepted        27
windows blocked         {'ambiguous_slot': 47, 'error_event': 6, 'partial_run': 10, 'live_in_not_in_entry_schema': 5}
blocked by tool         {}
  [synthesized ] list_tables/get_schema                            supp=17 k=2.0  REJECTED: ungroundable_slot:get_schema.table_names:no_consistent_expression
```

That diagnostic is not a live arm or a deployable artifact. Any future runtime must implement the same normalization, then use fresh calibration. Neither analysis has calibration groups; no risk certificate, positive certified coverage or learned-gate benefit is established.

## Operational amendment and spending

V1 attempted three episodes before the endpoint incompatibility was discovered; its other 105 scheduled episodes remain unstarted. Its conservative account was $0.0877729. Two function-tool calls were rejected with reasoning `low`; the Agent JIT attempt completed incorrectly. V2 uses reasoning `none` for every arm and 32 concurrent candidate generations. The cohort and arm order are unchanged; Q36 was therefore operationally exposed before v2. These amendments and all original failures are preserved, not silently replaced.

**Combined conservative campaign accounting: $1.5138 of the authorized $300.00 cap**, leaving $298.4862 against that accounting bound. This includes v1 and v2; stage allocation remains $30 pilot/$30 discovery/$60 calibration/$180 test. Unknown usage retains its full reservation. The provider invoice can differ because the ledger uses conservative pinned rates rather than actual cache discounts.

## Decision and reviewer concerns

The pilot establishes a working budgeted SQL adaptation and exposes practical output/runtime limitations. It does **not** establish that GAC beats another compiler, that native Agent JIT performs poorly, that handwritten prefetch is equivalent to GAC, or that the paper's acceptance-critical comparison has been completed. Native browser observation/execution is not reproduced. Generated programs can fail the SQL adapter's required answer contract; its worker also imposes a strict JSON RPC protocol and differs from upstream's Python executor. Those differences must be validated before using the port's score as comparative evidence.

The provider-free executor probe matched upstream success/output on only 1/5 hand-authored fixtures for the frozen pilot worker. A prospective worker using the unmodified pinned upstream executor matched 5/5, including print handling, return/last-binding semantics and an RPC fixture. The replacement was not used in this live pilot, and these fixture checks are not full SQL-port or native-browser validation. No pilot outcomes are repaired or relabeled by that result.

Next gates, before spending the remaining budget:

1. Extend the prospective worker's fixture parity to retained SQL programs and the answer contract; freeze a supported runtime without relabeling this pilot as an independent test.
2. Establish a candidate that survives discovery/challenge under the actual runtime representation. If none does, report refusal and change the task/design prospectively rather than tuning on final-test answers.
3. Freeze source/sampling weights, common candidate families, quality margin, multiplicity, and a feasible fixed sample size; reserve fresh groups before observing baseline outcomes or mined-family occurrence.
4. Run unfiltered final-outcome calibration and a separate final test, including rejected candidates, fallback and complete compilation costs. Retain any failed or unavailable certificate.

No extra paid calibration or final test has been launched. The manuscript's quantitative claims have not been replaced with these exploratory rates. The evidence improves the research audit; it does not remove every legitimate reason for rejection.

## Audit and reproduction

`seal.json`, `seal_v1.json`, `report.json`, `report_v1.json`, `gac_discovery.json`, `retention.json`, `raw_evidence.tar.gz` and `source_v1.tar.gz` preserve settings, task denominators, observable traces, candidates, the campaign ledger and historical source bytes. Database bytes and credentials are not included. Dataset provenance and upstream attribution appear in `retention.json`.

```sh
python paper/scripts/archive_adaptive_pilot.py verify
python paper/scripts/render_adaptive_pilot.py
```

New paid runs require the pinned external caches/environments described in the experiment README. Do not reset the campaign ledger or reuse pilot IDs as untouched evaluation data.
