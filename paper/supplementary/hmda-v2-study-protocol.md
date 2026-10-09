# HMDA single-domain live study, version 2 (frozen; not run)

**Status: WITHDRAWN from the ICLR 2027 cycle on 2026-10-07 by the author's decision; NOT RUN (see the note at the end). Earlier status: protocol frozen on 2026-10-07; not run. No provider call has been made. Execution
requires (1) a macro approval signed by a reviewer other than the author and (2) an explicit
spend authorization with a cap.** Workstream D1 in the ICLR revision history.

## Why a versioned study

The 2026-08 proposal (`benchmarks/manifests/multidomain-study.yaml`, study
`multidomain-real-records-2026-08`) spans vulnerability, SEC and HMDA and cannot be frozen
while the SEC pool is unavailable; the retained preflight records `protocol: null`. This is a
different, narrower study: `benchmarks/manifests/hmda-study-v2.yaml`, study
`hmda-real-records-2026-10`, HMDA alone, with the original roles, actions and statistical
contract unchanged and a `scope_note` declaring the omission. The preflight now accepts a
declared subset of the canonical domains and refuses an undeclared one. This study is never
described as execution of the 2026-08 design.

## Frozen inputs

| Item | Value |
|---|---|
| Protocol | `paper/results/multidomain/protocol/hmda-v2-frozen.json`, digest `44843ccb23f936637c3abcc01ac9456b2896cd26de43dc008a82970b8505aa52` |
| Pool | 420 groups (`lei`), 420 variable paths under corrected exemption semantics, exact independent gold 420/420, snapshot digest `945c176f…` |
| Roles | discovery 40, development 30, artifact calibration 100, portfolio calibration 75, test 100, reserve 75 |
| Actions | baseline, grc, macro |
| Model and pricing | `gpt-5.6-luna`; `paper/results/multidomain/pricing/gpt-5.6-luna-2026-10-07.json` (standard tier, input 0.20 / cached 0.02 / output 1.20 USD per million; unchanged from the primary studies' 2026-08-02 retrieval); 16,000 billable input tokens and 1,024 output tokens per request |
| Statistical contract | artifact and portfolio quality risk limit 0.10, confidence 0.99 per domain and overall, noninferiority margin 0.05, 20 repeat groups × 3 repeats, Holm for secondaries |
| Review materials | `paper/results/multidomain/review/hmda-v2-macro-review-materials.json` (provider-free exact agreement 420/420; `approval_generated: false`) |
| Approval template | `paper/results/multidomain/review/hmda-v2-macro-approval.TEMPLATE.json`; the signed file must be `hmda-v2-macro-approval.json` |

## Execution plan and caps

Phases in the runner's order (discovery → development → artifact calibration → portfolio
calibration → test), each through `multidomain_study.py` with `--protocol`, `--action-lock`,
`--max-provider-usd`, `--reservation-usd-per-execution 0.01`, bounded retries and timeouts.
The discovery dry run schedules 40 baseline executions, at most 8 model requests each (640
requests maximum). Pilot: the discovery phase alone; proceed only if its realized cost projects
all remaining phases and repeats under the cap. Proposed cap **$30** in total. A compiler
retirement at any stage is a result and is reported as a domain-boundary finding; live
preservation or savings claims require a usable artifact and the test phase.

## Claim boundary

A completed run licenses a second-domain live result within this study's contract. It does
not retroactively execute the 2026-08 three-domain design, and the α=0.05/δ=0.10 arithmetic of
the GitHub families does not apply to its 0.10/0.99 contract.

## Withdrawal (2026-10-07)

The independent macro approval was obtained (reviewer Leila Jalali; digests matching the
comparator and gold corrected in PR #64). The first live discovery attempt failed on all 40
executions before any provider call: the answer contract's `special_states` is an open mapping,
which the agents SDK's strict JSON-schema mode cannot express. A driver fix (non-strict output
wrapper) lets a model call complete, but the first answer then failed validation because the
model, unconstrained by strict mode, misplaced a special-state field and omitted a required one.
A dependable fix requires a strict-compatible contract (special states as a list of field/state
pairs) across schema, answer model, gold constructor, macro and grader, which changes every
approval-bound digest and the evaluator identity, and so a new review signature. The author
chose to withdraw HMDA from this cycle rather than reopen the contract. Nothing in the ICLR
manuscript depends on this study. Realized provider spend: under one cent (one diagnostic call).
The $0.01 per-execution reservation suggested above is below the frozen worst-case ceiling;
$0.04 was required.
