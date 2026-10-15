# Error audit and interpretation

Completed on October 15, 2026. The retained checkpoint has 480 completed episodes,
zero execution failures, and no unknown-cost reserve. Re-executing the existing
source grader reproduced all 480 retained quality labels. That is a consistency
audit, not an independently implemented gold standard. The following three
records account for every failed answer field in the comparison and were also
inspected against the pinned source text.

| Issue | Arms affected | Registered result and source inspection |
| --- | --- | --- |
| 3238 | Baseline and support-only | Both return `bug` and evidence label `dataset bug`. The source has only the label `dataset bug`; the task's exact recognized-label rule therefore requires `other` and `none`. GAC and recurrence follow that rule. The registered four-field factuality endpoint excludes these classification fields, so only the supplementary seven-field endpoint counts these misses. |
| 4027 | Recurrence-only | The returned excerpt changes the source's CRLF line ending to LF. Literal containment fails; normalizing line endings alone makes it match. This is an exact-text compliance failure, not an observed change in the described error. |
| 5786 | Recurrence-only | The returned excerpt starts `The command` where the source substring starts `the command`. Literal containment fails; case folding makes it match. This is an exact-text compliance failure, not evidence of a false factual assertion. |

These supplementary normalization checks do **not** replace the registered exact
endpoint, alter retained labels, or justify choosing a more favorable grader.
All other answer fields on the two recurrence-only cases pass. Under the explicitly
post-hoc relaxation of line endings and case, those two excerpt mismatches would
no longer be failures. That sensitivity substantially limits the substantive
meaning of the nominal 120/120 versus 118/120 contrast.

GAC and support-only have zero runtime dispatch disagreements. Each compacts
119 records and falls back on issue 3285, whose label-list cardinality exceeds the
induced verifier's range. On issue 3238, both arms dispatch, so their different
classification answers cannot be attributed to one arm refusing a risky case.
The providers execute separately and are stochastic. Recurrence-only changes
prefix length and evidence packaging in addition to removing restrictions.

The measured benefits of GAC relative to the unchanged baseline are 50.0% fewer
model requests, 40.1% fewer tokens, 49.8% lower mean wall latency, and 45.8% lower
estimated cost. Recurrence-only is still cheaper and uses one request per record,
versus two for GAC. No statistical-gate protection, semantic safety advantage,
equivalence, or noninferiority is established. The supplementary conservative
95% interval for GAC minus recurrence-only on the registered endpoint is
[-3.45, +6.60] percentage points under the unverified i.i.d.-record assumption.

This first development iteration establishes that the experiment is runnable and
that the observed tradeoff is worth measuring. It does not supply the missing
causal evidence for the guards. A next mechanism study should predefine semantic
or task-level failures under naturally variable tool arguments and compare the
same program with one mechanism removed; cosmetic excerpt differences should
remain a separate outcome. No follow-up study has been executed here.

Evidence: [`checkpoint.json`](../artifacts/checkpoint.json),
[`preflight.json`](../artifacts/preflight.json), [`analysis.json`](analysis.json),
and [`results.md`](results.md). Source snapshot and script hashes are retained in
those artifacts. The paid run cost $0.26863865 at the frozen rate card against an
authorized $200 estimated-spend ceiling; this is not invoice-verified billing.
