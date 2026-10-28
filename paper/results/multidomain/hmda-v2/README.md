# HMDA v2 live study: phase outputs

Frozen protocol: [`../protocol/hmda-v2-frozen.json`](../protocol/hmda-v2-frozen.json)
(digest `44843ccb23f936637c3abcc01ac9456b2896cd26de43dc008a82970b8505aa52`, study
`hmda-real-records-2026-10`, model `gpt-5.6-luna`, pricing
`../pricing/gpt-5.6-luna-2026-10-07.json`).

Each live phase writes its own subdirectory here (`discovery/`, `development/`,
`registries/`, `pilot/`, `artifact-calibration/`, `calibrated-registries/`,
`portfolio-calibration/`, `calibration/`, `test/`, `analysis/`). The directory is
separate from [`../discovery/`](../discovery/), which retains the failed 2026-10-07
attempt unchanged; the root-cause analysis of every attempt is in
[`../review/hmda-v2-live-study-handoff.md`](../review/hmda-v2-live-study-handoff.md).

## Status as of 2026-10-28

| Directory | Scheduled | Completed | Failed attempts | State |
| --- | ---: | ---: | ---: | --- |
| `discovery-credential-rejected-2026-10-28/` | 40 baseline | 0 | 4 (`AuthenticationError`, HTTP 401 `invalid_api_key`) | halted after 4 consecutive failures; no billable request |
| `discovery/` | 40 baseline | 0 | 8 (`ModelBehaviorError`: final answer fails the frozen `HmdaAnswer` schema) | halted after 6 consecutive failures across 3 groups; provider requests were made |
| development, compile-grc, freeze-actions, pilot, artifact-calibration | | not run | | blocked by the schema failure above |

`discovery/` was run with `--max-model-requests 20 --reservation-usd-per-execution 0.09
--max-provider-usd 7.2` after the first execution at the default bound of 8 raised
`MaxTurnsExceeded` (the HMDA oracle requires all five snapshot tools and the run uses
`parallel_tool_calls=False`, so a correct answer needs at least six model turns). The
request bound is a runner argument scaled into the reservation, not a frozen protocol
value; the frozen per-request token ceilings (16000 input, 1024 output) are unchanged.

Every one of the eight retained attempts (groups `549300HRKD2IJSOPRA57`,
`984500F6E6940CCB6A60`, `549300F1COXL6UBFCP55`) ended in
`agents.exceptions.ModelBehaviorError`: the model's final JSON parses but fails
validation because it fills `special_states` with `{"code": ..., "label": ...}` objects
for every requested field instead of the frozen `Literal["NA", "EXEMPT",
"UNAVAILABLE", "NOT_APPLICABLE"]` strings for the fields that carry a special state.
The SDK's strict mode cannot express that mapping (the 2026-10-07 root cause), so the
runner uses the documented non-strict wrapper, and in non-strict mode the provider does
not enforce the value type. Fixing it requires a prompt or answer-schema change in
`benchmarks/runtime.py`, which the signed macro approval's `evaluator_digest` hashes;
that change and its re-review are outside the operator's remit, so the study stopped
here rather than loosening any check.

Spend accounting for `discovery/`: failed attempts are not priced by the runner
(`provider_request_count_known: false`), so the ledger carries only the 0.09 USD
reservation per attempt (`committed_usd` 0.72). The true cost is bounded above by eight
attempts at the 20-request ceiling, 0.71 USD, and is in practice far lower. Two further
provider-backed attempts on the first group ran outside this ledger and are disclosed in
the handoff: one `MaxTurnsExceeded` attempt whose failure row was lost to a ledger
conflict (now fixed) and one diagnostic execution used to read the full validation
error. Neither produced a retained record.
