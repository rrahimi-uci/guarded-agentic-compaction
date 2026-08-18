# Supplementary external-benchmark interoperability audit

This ledger is deliberately supplementary. It documents source compatibility and
reproducibility work. Three of its corpora support the paper's post-trace compiler question:
NESTFUL and API-Bank retain complete observed intermediate values upstream, and BFCL v4
multi-turn obtains them by executing its official gold plans on its own pinned stateful
backend. None of the rows is an optimizer baseline, and none of their results is pooled with
the three GitHub workflow families.

| Benchmark | Verified artifact | Why it is excluded from the main comparison |
|---|---|---|
| BFCL v4 (structural) | Official checker validates 200/200 pinned gold plans | Gold calls omit observed results; this checks plan format, not compilation |
| BFCL v4 (executed) | Gold plans executed on the pinned backend give 200 complete traces, 1,142/1,142 exact re-execution, 4 synthesized families, and 3 pass / 3 abstain / 0 wrong held-out windows | A pre-registered fail-closed compiler substrate: every family retires at 15 groups against 92 required, and no model runs, so it licenses no accuracy, quality, or efficiency claim |
| ToolSandbox | One official live-provider scenario scores 0.9818 | A bounded simulated-environment run without a paired compiler intervention |
| maintained tau2/tau3 | Four live-provider domain tasks score 0/4 | A bounded simulated-agent quality run, not a trace-compiler comparison |
| ToolBench | Ten versioned repository fixtures normalize | Full data and live backend are not sealed in this artifact |
| AgentBench | 556 tasks normalize | External services and Freebase bytes are unavailable |
| GAIA | Authenticated source request returns HTTP 403 | Dataset authorization is absent; no score is imputed |
| SWE-bench Verified | 500 real issue tasks normalize | The available arm64/12.5-GiB host does not meet the harness's recommended execution contract, and no historical agent trajectories are provided |
| BrowseComp | Three sealed hosted-search tasks score 1/3 | Server-managed search cannot be replayed through the local effect/staging contract |

The machine-readable source, checksum, adapter, and execution evidence remains under
`paper/results/external_benchmarks/`; reproduction commands and exact evidence boundaries
are documented in `docs/external-benchmarks.md`. The BFCL execution row's predeclared
expectation, decision rule, and preconditions are in
`supplementary/bfcl-compiler-protocol.md`. Keeping this audit available prevents
selective reporting while keeping the main paper focused on experiments that can actually
measure optimizer value.
