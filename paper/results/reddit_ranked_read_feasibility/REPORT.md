# Ranked Reddit read: development feasibility and baseline headroom

**Decision:** the read route is executable under the pinned browser boundary, but
task 714 is **not an adequate positive demonstration of GAC's quality–cost value**.
An exposed-task, provider-free handwritten reference uses one `browser_batch`
call containing the ranked navigation and vote and passes the official grader.
No GAC artifact was discovered, admitted, or evaluated here. These runs cannot
establish superiority over a competent batched agent or handwritten workflow.

## Prespecified setting and source gate

- WebArena-Verified revision:
  `6473f72db5dcefc97b5725b59e734504edc28a21`; pinned Reddit image digest
  and the source-file hashes are in the v1 seal. Task 714 was one of four
  metadata-selected development templates registered before task-text exposure
  in [`selection.json`](../adaptive_comparison_followup/selection.json).
- The app's `/f/{forum}/{sortBy}` route, forum controller, criteria and submission
  finder support `GET /f/gadgets/top`, with `all` as the default time window.
  The pinned image was source-hashed before runtime controls. The vote endpoint
  is a POST and remains after read-stage promotion.
- The stage allows only the owned root and exact ranked listing documents plus
  pinned static assets. A wrong forum, query variation, cross-origin request,
  or POST cannot be silently treated as a safe read. The `pg_dump` data digest
  checks business-data rows before and after the read. It does not prove that
  sessions, CSRF state, logs, time or all possible effects are unchanged.
- This is a publicly exposed development task, not fresh calibration or test.
  Its full template and grader target must never be represented as untouched.

## Retained controls and adaptive pilot

| Attempt | Retained result | Interpretation |
|---|---|---|
| Read-boundary v1 | 4/5 controls passed. Empty, read-only, blocked wrong-forum and blocked POST behaved as expected. Positive reached the intended vote POST but the browser closed before its response reached HAR; official grader failed. | Failed first positive is retained, not replaced. |
| Positive v2 | HTTP 200 vote; official grader success. Terminal emitted an unhandled Playwright `Response.finished()` target-closure task. | Recorded grader pass, not a clean process result. See [`TERMINAL_WARNING.md`](../reddit_ranked_read_feasibility_v2/TERMINAL_WARNING.md). |
| Positive v3 | HTTP 200 with nonempty response body, no request failure, official grader success; read-stage business-data digest unchanged. | Integration control passed. The original terminal stream was not preserved durably, so process-warning absence is not independently attestable. |
| Batched model v1 | 4 model requests, 4 batches, 8 executed browser actions; then the sealed 200 KB payload bound stopped the run. No final answer or official grade. Accounted upper cost: $0.0371118. | Failed development attempt retained. Large intermediate snapshots accumulated in model-visible history. |
| Batched model v2 | 7 model requests, 6 batch calls, 4 executed browser actions, official grader **success**. Two attempted batches failed validation before any action. Accounted upper cost: $0.0112245. | One exposed-task competent-baseline observation, not a distribution estimate. The amendment bounds model-visible history while preserving full raw observations. |
| Handwritten one-batch reference | One batch with `goto /f/gadgets/top` and `click Downvote index=0`, two actions, official grader **success**, zero provider calls. | Demonstrates available one-batch execution headroom on this fixed task; it is not an adaptive-agent trajectory or automatic compilation. |

The two paid attempts charged $0.0483363 in total. The shared campaign ledger
after these runs reports a conservative accounted upper amount of $2.2620685
and $297.7379315 remaining from the authorized $300 cap. The stage and campaign
limits were not reset. Its SHA-256 at this point is
`69ada741f9c41717b67de39a889917c910023c0a7e1270893249fb4167d5e77c`.
The ledger is an ignored local campaign artifact, so the PR retains per-attempt
provider usage and charges in the archived reports rather than publishing the
whole shared ledger. These figures are budget accounting, not an invoice.

## Why this does not establish GAC superiority

The v2 model's six calls leave an apparent optimization opportunity, but its
behavior is one sample on an exposed task, including two malformed tool calls.
A stronger fixed program can already complete the task with one batch and pass
the official evaluator. Replacing the model's navigation with a compiled read
would need an actual recurrent, automatically derived artifact, grounded dynamic
arguments, a comparable continuation, and fully charged discovery/dispatch/
verification/fallback costs. None exists in these runs. A safe read port by
itself has no demonstrated incremental value against the one-batch reference.

This selected extension is a **no-go for a positive quality–cost claim**.
Further work should follow a newly sealed protocol on tasks where an intermediate
observation genuinely determines later actions and where the competent batched
baseline cannot prewrite the same complete action sequence. A fresh comparison
would still need the matched GAC, recurrence-only, support-only, handwritten and
faithful external-compiler arms, independent final-task grading, offline cost
amortization, held-out groups, and a power/affordability gate. Do not use the
four exposed templates as confirmation or infer noninferiority from this 1/1
development success.

## Evidence and recovery provenance

Each version has a seal, source snapshots, per-attempt record, official-grader
result or documented absence, and archived HAR. The retained v1 failure and
subsequent amendments are separate directories. Tests verify archive members,
source hashes and outcome fields. The primary shared checkout was externally
reset during preparation of this report. Its ignored local run records and
source snapshots survived. The four earlier exported archives through batched
model v1 were reconstructed byte-for-byte from those unchanged records by
restoring their original gzip header timestamps; the later seals' recorded
SHA-256 values verify the exact match. Batched model v2's archive was regenerated
from its preserved raw records because no later seal pinned its prior gzip hash.
Its new archive and report are explicitly checksummed. No experiment was rerun
or favorable outcome substituted during this recovery. The repository changes
were moved to a dedicated linked worktree and this report is part of a PR.
