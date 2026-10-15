# Fresh-record safeguard comparison: observed results

This run evaluated 120 unused historical-snapshot issues under four arms.
The registered four-field factuality endpoint and supplementary seven-field answer endpoint are shown separately.
Resource means use completed episodes; consult each arm's completed/failed counts before comparing incomplete runs.

| Arm | Factuality correct | All answer fields correct | Dispatched | Requests/episode | Tokens/episode | Latency (s) | Estimated cost/episode (USD) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 120/120 | 119/120 | 0 | 4.00 | 4261.8 | 6.79 | 0.000892 |
| gac | 120/120 | 120/120 | 119 | 2.00 | 2554.3 | 3.41 | 0.000483 |
| support_only | 120/120 | 119/120 | 119 | 2.00 | 2562.7 | 3.33 | 0.000479 |
| recurrence_only | 118/120 | 118/120 | 120 | 1.00 | 1148.8 | 2.02 | 0.000384 |

Recorded estimated spend: $0.268639; authorized cap: $200.00. Prices are frozen estimates, not invoices.

| Comparison (registered endpoint) | Gains | Losses | Accuracy difference (percentage points) | Conservative 95% interval |
| --- | ---: | ---: | ---: | --- |
| gac_vs_baseline | 0 | 0 | +0.00 | [-3.59, +3.59] |
| support_only_vs_baseline | 0 | 0 | +0.00 | [-3.59, +3.59] |
| recurrence_only_vs_baseline | 0 | 2 | -1.67 | [-6.60, +3.45] |
| gac_vs_recurrence_only | 2 | 0 | +1.67 | [-3.45, +6.60] |
| gac_vs_support_only | 0 | 0 | +0.00 | [-3.59, +3.59] |

Intervals are supplementary, pointwise, and assume independent identically distributed record pairs. They do not establish equivalence or noninferiority. Errors are retained in `analysis.json` and raw answers in `checkpoint.json`.

Provider-free dispatch outcomes: `{"gac": {"BASELINE": 1, "COMPACTED": 119}, "recurrence_only": {"REPLAYED": 120}, "support_only": {"BASELINE": 1, "COMPACTED": 119}}`.

Observed GAC/support-only dispatch disagreements: 0 records. When dispatch behavior is identical, final answer differences alone cannot demonstrate gate protection: each arm makes separate stochastic provider executions.

No paper score or acceptance claim follows automatically from completing this run.

Limitations:

- fresh records from the same historical snapshot, not time-forward
- fixed previously admitted artifact; no new discovery or calibration
- one workflow; 120-record default is exploratory, not powered noninferiority
- support-only is conditional on prior candidate admission
- recurrence comparison changes context and prefix length as well as safeguards
- supplementary endpoints and intervals are not a preregistered confirmatory test
- no noninferiority margin, no causal protection claim, no new risk certificate
- shared source grader reexecution is consistency checking, not an independent gold implementation
- current-compiler reconstruction changes identifier guards, verifier clauses, and gate feature specification relative to the historical artifact
- frozen rate estimates exclude lifecycle and human costs; not invoice verified
