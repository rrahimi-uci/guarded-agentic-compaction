# Observed diagnostic and next empirical gate

The provider-free run completed 2,880 arm evaluations: 96 held-out public issues,
three constructed request limits, two response suites, and five arms. All 2,880
completed without execution failure. Sixteen held-out issues had no comments;
they remained in every arm and suite. The full deterministic replay audit passed.
The source cohort was disjoint from discovery (24), development (96), calibration
(192), and earlier retained studies, including PR #78's 120 issues.

| Suite | Intervention | Full correct | Ablation correct | Full-only correct issue groups |
| --- | --- | ---: | ---: | ---: |
| Ordinary responses | Remove requested-limit hull | 288/288 | 260/288 | 28 |
| Ordinary responses | Remove completeness check | 288/288 | 288/288 | 0 |
| Ordinary responses | Disable statistical gate | 288/288 | 288/288 | 0 |
| Capped-response stress | Remove requested-limit hull | 288/288 | 288/288 | 0 |
| Capped-response stress | Remove completeness check | 288/288 | 252/288 | 36 |
| Capped-response stress | Disable statistical gate | 288/288 | 288/288 | 0 |

These are deterministic task-contract outcomes under constructed requests, not
live model accuracy, deployment failure rates, or independent samples per row.
The baseline reference policy was correct in all cases in both suites. The two
suites reuse the same issues, so their group counts must not be added as distinct
affected issues.

## What changed the answer

The frozen program reads three comments. On an ordinary request for five, an
unchecked dispatch omits the fourth and fifth comments where present. All 28
errors change the reported count; six also omit a requested keyword-match
position. For example, issue 2035 has 11 comments. Its first five have matches at
positions 1, 2, 4 and 5; the unguarded result returns only 1 and 2 and reports
three comments instead of five. The full policy refuses and performs the
reference reads for the original five-comment request.

Under the two-comment response cap, the completeness field is false when more
of the requested page exists. Removing just that verifier clause releases two
comments for a three-comment request. All 36 errors change the reported count;
six also lose a match position. For example, issue 3310 has 28 comments, and its
first three contain matches at positions 2 and 3. The unchecked result reports
two comments and only position 2. Full dispatch rejects that partial result and
fallback follows the same capped API's next-offset field.

This also exposes a mechanism interaction: the verifier compensates for the
missing entry hull in the capped suite. Removing the hull changes 120 dispatch
decisions there but causes no incorrect answers. Under ordinary responses it
changes 192 decisions but only 28 answers. Refusal counts alone would substantially
overstate benefit.

## What the gate and cost results do not show

The fresh gate fit had one eligible development feature vector and no observed
ordinary-response error after full dispatch. Its score is constant
0.0024726231566347743. All eleven thresholds accept the same 192 calibration
groups; the stored exact bound is 0.024184423152400103 under the calibration
assumptions. There is only one nonzero group-coverage level, not a learned
risk frontier. Group coverage is 100% because each issue has an eligible
three-comment request; case dispatch coverage is 96/288 in the ordinary test.
No gate ablation changes a held-out decision or answer.

The diagnostic measures no model requests, tokens, latency savings, or provider
cost savings. Ordinary-response tool calls are 576 for both full and baseline.
Under the cap, full uses 742 calls versus baseline's 670 because discarded reads
and subsequent fallback are counted. The unchecked verifier arm uses 634 calls
but has 36 incorrect cases. This is a task-quality/read-overhead tradeoff within
the specified deterministic policy, not an LLM efficiency result.

The template, scope contract, and completeness check are explicit study design.
Only the argument bindings and gate are fitted by the corresponding production
helpers. This does not establish that end-to-end mining would discover the
necessary guards, or that a live continuation could not repair missing evidence.
There is no independent human gold attestation and no new publication claim.

## Next live pilot

The live pilot should preserve the program, paired records, one-component
interventions, and separate response suites. All arms need the same live
continuation and access to the same recovery tools. Count repair requests and
tool calls, include fallback overhead, and grade the count and match positions
against the source. The outcome may be equal accuracy with different recovery
cost; that must not be recast as a safety improvement.

Before calling a provider, freeze the live prompt, model, recovery interface,
arm ordering, sample size and spending limit in a separate seal. Do not reuse
this offline calibration as an LLM-task certificate. A live learned-gate study
also requires fresh live discovery/development/calibration and a workload with
entry-observable variation among guard-eligible cases. Merely adding more cases
to this constant-feature workload cannot establish a selective frontier.

Evidence: [frozen protocol](README.md), [seal](artifacts/seal.json),
[candidate](artifacts/run/candidate.json), [calibration](artifacts/run/calibration.json),
[all outcomes](artifacts/run/outcomes.jsonl), [summary](artifacts/run/summary.json),
[generated tables](artifacts/run/results.md).
