# HMDA v2 live study: phase outputs

Frozen protocol: [`../protocol/hmda-v2-frozen.json`](../protocol/hmda-v2-frozen.json)
(digest `44843ccb23f936637c3abcc01ac9456b2896cd26de43dc008a82970b8505aa52`, study
`hmda-real-records-2026-10`, model `gpt-5.6-luna`, pricing
`../pricing/gpt-5.6-luna-2026-10-07.json`).

Each live phase writes its own subdirectory here (`discovery/`, `development/`,
`registries/`, `pilot/`, `artifact-calibration/`, `calibrated-registries/`,
`portfolio-calibration/`, `calibration/`, `test/`, `analysis/`). The directory is
separate from [`../discovery/`](../discovery/), which retains the failed 2026-10-07
attempt unchanged; see the root-cause note in
[`../review/hmda-v2-live-study-handoff.md`](../review/hmda-v2-live-study-handoff.md).

## Status as of 2026-10-28

| Phase | Scheduled | Completed | Failed attempts | Provider spend (USD) | State |
| --- | ---: | ---: | ---: | ---: | --- |
| discovery | 40 baseline | 0 | 4 (`AuthenticationError`, HTTP 401 `invalid_api_key`) | 0.00 billable | halted after 4 consecutive failures |
| development | 30 | not run | | | blocked on credential |
| compile-grc | - | not run | | | needs discovery and development ledgers |
| freeze-actions (shadow) | - | not run | | | needs shadow registry |
| pilot | 36 | not run | | | needs action lock |
| artifact-calibration | 200 | not run | | | needs action lock |

`discovery/` holds the dry-run preflight (`eligible: true`, 40 executions, 80 maximum
attempts, 0.04 USD reservation per attempt against a computed worst case of
0.0354304 USD, 4.00 USD cap) and the halted live ledger: 4 `execution_started` and 4
`execution_failed` rows for two scheduled groups, each rejected by the provider with
HTTP 401 before any billable request. The ledger is hash chained and resumable: a run
with a valid `OPENAI_API_KEY` and the same reservation (0.04 USD) re-attempts every
group that has no `execution_complete` row and keeps these rows as history. The
0.16 USD shown as `committed_usd` in `summary.json` is the replayed reservation for
those four attempts, not a charge.

No provider request in this directory produced tokens. `provider_calls_executed` is
`null` because the runner cannot prove the 401 responses were free; the provider's
response body (`invalid_api_key`) and the absence of any usage object are the evidence
that they were.
