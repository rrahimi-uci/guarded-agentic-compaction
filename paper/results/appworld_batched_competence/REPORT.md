# Batched AppWorld baseline competence: development no-go

**Decision: the competence gate failed in both sealed attempts.** This study does
not measure GAC, a matched compiler, or a quality–cost advantage. All 12 fixed
cases are exposed AppWorld training scenarios. The worker uses a common
preauthenticated entry with 11 measured setup API calls per case, so these are
adapted-interface results, not native AppWorld leaderboard scores.

## Exact-path controls

The pinned worker saves final state before applying AppWorld's official task
tests. On all 12 scenarios, the direct public-API path passed its known-correct
reference, empty and false-completion controls: **36/36**. A second provider-free
control sent the same references and negatives through the exact agent batch RPC
used for paid attempts: **36/36**. Entry-state hashes agreed among modes for each
scenario. Protected reference calls were isolated control inputs; the model did
not receive them. These checks validate the execution and grading path on the
fixed cases. They do not establish agent competence or GAC benefit.

## Sealed model attempts

| Attempt | Model and change | Official successes | Model requests | Agent API calls | Conservative charged upper estimate |
|---|---|---:|---:|---:|---:|
| V1 | GPT-5.6 Luna, original prompt | 1/12 | 202 | 651 | $0.636861 |
| V2 | GPT-5.6 Sol, explicit completion reminder | 2/12 | 109 | 316 | $3.162930 |

Each version retained all 12 scheduled cases, including failures, under the
same task set, worker, batch tool, common setup, official grader, and limits
of 96 model requests, 192 agent API calls and 1200 seconds per case. The
prespecified development engineering gate was at least **8/12 official
successes**. Both versions failed. No case was retried or replaced. The V2
change was made after inspecting V1's aggregate failure. Because both model and
prompt changed, the difference between their scores is **not** an isolated
model effect. Neither version is an independent or held-out test.

V1 attempted `supervisor.complete_task` in four cases; one passed. It issued
16 invalid batches, which the worker rejected before effects. V2 attempted
completion in all 12 cases; two passed. Its 12 terminal assistant messages
did not call the optional `finish` tool, so the harness ended the episodes and
graded their saved state. This termination behavior and the low official
success rate rule out treating V2 as a competent comparator. The runs still
provide authentic adaptive traces for diagnosing interface and workflow
requirements. Reference sequence length is not a lower bound on optimal agent
actions, and action counts are not interchangeable with provider requests.

## Budget, provenance and claim boundary

The two attempts charged **$3.799791** to the shared fail-closed campaign ledger.
Its conservative accounted total after V2 was **$6.0618595**, leaving
**$293.9381405** under the authorized $300 cap. This is a priced upper estimate
from token usage and conservative input rates, not an invoice or a measure of
local compute and engineering time. All 311 model-request reservations were
settled with provider usage; none triggered a usage-bound stop. V2's Sol
accounting uses a $5 per million
input-token upper rate and $20 per million output tokens; the input rate covers
the documented cache-write multiplier. [Official model pricing](https://developers.openai.com/api/docs/models/gpt-5.6-sol).

The V1 [aggregate report](report.json), [seal](seal.json), [encrypted operational
evidence](operational_evidence.bundle) and [bundle verification](bundle_verification.json)
retain the first attempt and controls. The V2 [aggregate report](../appworld_batched_competence_v2/report.json),
[seal](../appworld_batched_competence_v2/seal.json), [encrypted operational
evidence](../appworld_batched_competence_v2/operational_evidence.bundle) and
[bundle verification](../appworld_batched_competence_v2/bundle_verification.json)
retain the amendment. Both encrypted bundles passed round-trip file checks.
Protected task inputs, reference answers, credentials, API responses and raw
traces remain encrypted with the upstream distribution utility; public reports
contain aggregate counts and hashes only.

**No matched GAC run follows this failed gate.** The reviewer concern about
quality–cost benefit over simpler compilers and handwritten workflows remains
open. The appropriate next scientific decision is to establish a competent
adaptive baseline and useful automatically derived read region in a genuinely
fresh, properly grouped task population, or narrow the paper's claim to the
supported compile-or-retire and existing GitHub results. A favorable cost ratio
against these floor-level baselines would not answer the objection.
