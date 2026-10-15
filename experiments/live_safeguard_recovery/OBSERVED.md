# Observed live pilot: stopped incomplete

On October 15, 2026 the user authorized a $200 estimated-spend cap for this
sealed 576-episode pilot. Execution stopped on its first execution failure,
as specified prospectively. The original seal, schedule and code were preserved;
no failed episode was retried or replaced and no further provider calls were made.

## Accounting and coverage

| Outcome | Episodes |
| --- | ---: |
| Scheduled | 576 |
| Attempted | 153 |
| Completed | 152 |
| Correct among completed | 151 |
| Incorrect among completed | 1 |
| Execution failures | 1 |
| Not attempted | 423 |

Completed episodes consumed **$0.0490666 estimated spend**, using the sealed
rate card. The failed attempt retains a **$1 unknown-cost reserve**; its actual
usage is unknown, not zero. Estimated spend plus reserve is $1.0490666 against
the authorized $200 cap. These are neither invoice amounts nor a hard billing
limit. The run stopped because of failure, not budget exhaustion.

Only seven of the 24 scheduled issue groups were reached: six have all 24
episodes, and issue 6273 has nine attempted episodes. The first six issues have
0--2 source comments, so none of their capped-response variants actually
truncated a page. The seventh issue has five comments, but execution stopped
before any of its capped-response episodes. Thus the retained stress-suite
results contain **no active truncation cases**. This coverage limitation is
stronger than merely having a small sample.

## Accuracy and failure

| Suite | Arm | Scheduled | Attempted | Completed | Correct | Failed | Unattempted |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Ordinary | baseline | 72 | 20 | 20 | 20 | 0 | 52 |
| Ordinary | full | 72 | 21 | 20 | 19 | 1 | 51 |
| Ordinary | no entry hull | 72 | 20 | 20 | 20 | 0 | 52 |
| Ordinary | no completeness check | 72 | 20 | 20 | 20 | 0 | 52 |
| Capped-response stress | baseline | 72 | 18 | 18 | 18 | 0 | 54 |
| Capped-response stress | full | 72 | 18 | 18 | 18 | 0 | 54 |
| Capped-response stress | no entry hull | 72 | 18 | 18 | 18 | 0 | 54 |
| Capped-response stress | no completeness check | 72 | 18 | 18 | 18 | 0 | 54 |

The incorrect answer is `7449:ordinary:5`, full arm, after guard refusal and
ordinary live fallback. The model read the requested page and issue, then
reported zero comments instead of the source's two; both predicted and expected
matching-position lists are empty. The other three arms answered this case
correctly. This is a retained final-answer error, not an execution failure or
an error after accepted dispatch.

Attempt 153 is `6273:ordinary:5`, full arm. It stopped with `ValueError` after
5.524 seconds. The failure record intentionally retained only the exception
type; it has no stage, stack or per-response usage. Its root cause cannot be
determined from that record. Do not label it a provider outage, a model-answer
error, a usage-accounting defect or a timeout without further evidence.

There are 20 matched attempted ordinary cases and 18 matched stress cases per
full-versus-other comparison. Full is never uniquely correct; each other arm
is uniquely correct on the one ordinary case above. The failed attempt is the
first arm for its case, so it is retained in arm totals but has no attempted
pair. Unattempted counterparts are not silently counted as successful or failed.

## Interpretation and follow-up

This incomplete pilot does not establish a correctness, recovery-cost or safety
advantage. All arm/suite resource-accounting-complete flags are false. The
generated means describe completed episodes only; they cannot support overall
savings claims. No accepted dispatch triggered a continuation tool call in the
retained prefix, and the stress suite never reached active truncation. The
intended live repair question remains unanswered. No manuscript claim or ICLR
acceptance estimate is raised from this run.

Before a new live attempt, add provider-free tests for safe failure diagnostics:
retain the execution stage, sanitized exception class/cause class and completed
request usage where available, without raw provider content or credentials.
Preserve this stopped attempt and seal. A revised protocol and separately
identified run must specify how failures affect scheduling and denominators
before execution; do not rewrite this run or remove its failed record to resume.
The existing $200 authorization applies to this pilot and is recorded here;
any later run must explicitly state its budget relationship to this attempt.

## Retained evidence and audit

- [Checkpoint](artifacts/checkpoint.json): all attempted outcomes, final answers,
  successful response usage, tool arguments/digests, budget and failure reserve.
- [Analysis](artifacts/analysis.json): source regrade, tool replay, cost audit,
  separate suite denominators and paired outcomes; binds the checkpoint digest.
- [Generated descriptive tables](artifacts/results.md): completed-episode means
  with the incomplete-accounting caveat.
- [Seal](artifacts/seal.json): unchanged prospective source, code, configuration,
  schedule and provider-free preflight evidence.

Post-run `analyze` and `verify` passed. The latter's
`provider_calls_executed: 0` describes the verification command, not the live
run. Source regrading is a consistency check, not independent human gold review.
