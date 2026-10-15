# Conclusion from the completed live recovery comparison

**The live evidence supports the request-scope guard on this constructed
workload. It does not establish an accuracy benefit for the completeness check,
a learned-gate benefit, or overall superiority to the uncompiled baseline.**
The live agent frequently repairs capped pages, but often fails to recover a
larger requested prefix from an accepted three-comment prefetch. Safeguards
therefore have different observed value; the deterministic ablation alone would
have overstated their live benefit.

## Completion, budget and provenance

All **2,304 scheduled episodes were attempted**: 2,300 completed, four timed out,
and none remain unattempted. Among completed episodes, 2,186 answers are correct
and 114 are incorrect. Failures remain in scheduled/attempted denominators;
there were no automatic retries, replacement records or prompt changes.

The run includes all 96 held-out issue groups: 72 confirmation groups untouched
by the prior live pilot/diagnostic, plus 24 separately reported replication
groups. Each group receives three limits, two response conditions and four arms.
All issues were used in the earlier offline diagnostic, and the requests are
constructed. The 2,304 episodes are not 2,304 independent samples.

Recorded new-run estimated cost, including known partial usage from failures,
is **$0.95269564**. Adding $4 for its failed-attempt reserves and $2.0490666
carried from the stopped pilot and diagnostic yields **$7.00176224** in aggregate
estimates plus retained reserves. This is below both the sealed run's $200 guard
and the user's subsequently increased **$400 overall cap**. It is not an invoice
or a bound on actual provider billing. The diagnostic's conservative $1 reserve
was retained even though its response usage was captured.

The final checkpoint is SHA-256
`fc207e0292ed1c967fd01d1a72ca329dcbf88e628937e6f89e7a83077a317600`.
The prospective code/protocol/configuration/source seal, source grades,
successful tool-output digests, usage partitions, costs and metric totals all
passed the post-run audit. The sole invalid read (issue 259, capped limit 5,
no-entry-hull arm, offset 6) was separately replayed through the real SDK tool
wrapper; its arguments, error status and output digest matched. No provider
calls were used for these audits. Source consistency is not independent human
gold attestation.

## Final task success

Each cell is correct answers / scheduled episodes. Execution failures are
unsuccessful attempts, not removed observations.

| Cohort and condition | Baseline | Full | No entry hull | No completeness check |
| --- | ---: | ---: | ---: | ---: |
| Confirmation, ordinary | 204/216 | 205/216 | 186/216 | 210/216 |
| Confirmation, capped stress | 211/216 | 205/216 | 207/216 | 204/216 |
| Replication, ordinary | 71/72 | 70/72 | 67/72 | 70/72 |
| Replication, capped stress | 70/72 | 68/72 | 69/72 | 69/72 |

The four execution failures were 120-second request timeouts, all in
confirmation: baseline ordinary, full ordinary, no-entry-hull ordinary, and full
stress. The diagnostic cache-write rejection did not recur. All 448,212 recorded
cache-write tokens were accepted and priced. Replication completed all 576
scheduled episodes without an execution failure.

Primary confirmation comparisons use 72 issue groups. Differences below are
full minus the comparator, in percentage points; each issue contributes its
average across the three requested limits. Intervals are the prespecified
10,000-draw issue-level percentile bootstrap, descriptive and unadjusted for
multiple comparisons. They are not a noninferiority or safety certificate.

| Condition | Comparator | Full-only / other-only correct cases | Difference | Descriptive 95% interval |
| --- | --- | ---: | ---: | ---: |
| Ordinary | No entry hull | 24 / 5 | +8.80 pp | [3.70, 13.89] |
| Ordinary | No completeness check | 4 / 9 | -2.31 pp | [-5.56, 0.93] |
| Ordinary | Baseline | 11 / 10 | +0.46 pp | [-3.70, 4.63] |
| Capped stress | No entry hull | 6 / 8 | -0.93 pp | [-4.17, 2.31] |
| Capped stress | No completeness check | 8 / 7 | +0.46 pp | [-3.70, 4.63] |
| Capped stress | Baseline | 4 / 10 | -2.78 pp | [-6.48, 0.46] |

Under ordinary responses, full and no-completeness-check have identical sealed
initial model inputs. Their differing live answers reflect separate stochastic
continuations, not an ordinary-response verifier effect. Under capped responses,
the retained completeness check can compensate for the missing entry hull; the
mechanisms should not be treated as interchangeable independent protections.

The ordinary entry-hull contrast has full-only correct cases in 20 issue groups
and other-only correct cases in five groups. In the smaller replication cohort,
the corresponding difference is +4.17 pp with interval [-1.39, 9.72]; its
positive direction is consistent, but that interval includes zero. All remaining
replication contrasts and resource intervals are retained in `analysis.json`.
Do not describe the smaller cohort as a decisive independent replication.

As a **post-hoc timeout sensitivity**, restricting the ordinary entry-hull
comparison to its 214 pairs where both episodes completed gives 23 full-only
versus four ablation-only correct cases. Thus that observed advantage is not
created by the timeout imbalance. This sensitivity does not replace the primary
failure-inclusive comparison or its prespecified interval.

## What live recovery actually repaired

An incomplete accepted prefetch is defined from released source positions and
the requested prefix before inspecting final answers. Every case below was
attempted. Correct cases in this table also made continuation reads.

| Cohort | Ablation and condition | Incomplete accepted prefetches | Cases making further reads | Correct final answers |
| --- | --- | ---: | ---: | ---: |
| Confirmation | No entry hull, ordinary | 20 | 5 | 4 |
| Replication | No entry hull, ordinary | 8 | 4 | 4 |
| Confirmation | No completeness check, stress | 27 | 27 | 22 |
| Replication | No completeness check, stress | 9 | 9 | 8 |

The live agent usually follows the capped-page recovery signal, while a page
marked complete for the compiled three-comment call can still leave a larger
user request uncovered. The original call arguments and this meaning of
`complete` were exposed to every arm; missing evidence was not concealed from
the ablations. This supports the bounded interpretation that request scope
matters even when recovery is available. It does not prove every scope-related
error was caused by the same reasoning failure.

The stress condition includes 54 confirmation and 18 replication requests whose
required prefix exceeds two comments, unlike the stopped pilot's reached
stress cases. Cases sharing the same issue are still correlated. Final semantic
errors remain possible after a correct prefetch: the full arm has incorrect
counts and matching positions, so accepted dispatch is not an end-to-end answer
certificate. `analysis.json` retains every incorrect answer and source expectation.

## Model cost and total-work trade-offs

All confirmation contrasts involving full include at least one execution
failure. Their generated completed-episode means are descriptive only; the
protocol therefore withholds overall resource-saving intervals there. Unknown
failed-request usage is not zero cost.

Replication has complete accounting. Against baseline, full's observed means are:

| Condition | Model requests, baseline → full | Estimated cost change | Total tools, baseline → full | Correct, baseline → full |
| --- | ---: | ---: | ---: | ---: |
| Ordinary | 2.417 → 1.931 | -18.2% | 1.417 → 1.597 | 71 → 70 |
| Capped stress | 2.722 → 2.458 | -9.1% | 1.722 → 2.125 | 70 → 68 |

The paired cost-difference intervals are [-0.00010541, -0.00005827] dollars per
episode for ordinary responses and [-0.00007654, -0.00001820] for stress.
These estimates support lower model cost under this execution policy, alongside
higher tool counts and slightly fewer correct answers. They do not establish
quality equivalence or an overall system-cost win. Four-worker concurrency,
provider caching, repository rate estimates and omission of lifecycle/human
costs limit transfer of the amounts.

Removing the entry hull reduces model requests further but loses accuracy in
ordinary confirmation. Removing the completeness check in replication stress
uses fewer requests and tools without a demonstrated accuracy penalty; its
full-minus-ablation accuracy interval spans zero. Report this adverse/null
result rather than asserting that every safeguard improves live performance.

## What this adds to the paper's evidence

| Claim | Evidence-based conclusion |
| --- | --- |
| Fixed compiled prefixes can reduce model work | Supported on these tasks. The earlier 120-record study halved requests with equal registered accuracy; this replication shows lower model cost with a tool/quality trade-off. |
| Request-scope admission can protect live task success | Supported by the ordinary confirmation contrast above, with the constructed-workload and grouping limits. |
| Completeness rejection is necessary for live correctness | Not established. The live continuation often repairs incomplete pages, and the paired accuracy contrast is unresolved. |
| Full is more accurate than the uncompiled baseline | Not established here; full is slightly higher in ordinary confirmation and lower under stress. |
| The statistical gate adds selective protection | Not established; its previously constant scores/decisions remain a null result. |
| End-to-end mining discovers the necessary contracts | Not tested by these hand-specified scope/completeness interventions. |
| The approach generalizes across models, natural requests or time | Not established by this one-model, historical-source study. |

The defensible paper conclusion is **mechanism-specific**, not that all barriers
are empirically necessary: request-scoped admission helps on out-of-scope
requests, while completeness-based refusal can duplicate repair the agent would
perform. Compiled-prefix efficiency is an observed trade-off, not a universal
accuracy or total-work improvement. This completes the specified live comparison;
it does not complete every validation needed for the broader approach.

A manuscript-ready factual summary is: “On 72 held-out live confirmation issue
groups, request-scope admission improved ordinary-response task success from
186/216 to 205/216 under equal recovery access. The completeness-check ablation
showed no clear accuracy difference under capped responses (205/216 versus
204/216), and the agent repaired 22/27 incomplete accepted prefetches. Complete
24-group replication accounting showed lower model cost but higher tool counts
than baseline, with no demonstrated quality equivalence.” Accompany these facts
with the descriptive interval, timeout and constructed-workload qualifications
above. This PR does not silently revise the manuscript or raise an acceptance
probability.

Sources: [sealed protocol](README.md), [all attempts](checkpoint.json),
[audited analysis and all intervals](analysis.json), [generated tables](results.md),
[earlier live comparison](../fresh_safeguards/analysis/results.md),
[deterministic diagnostic](../safeguard_mechanisms/OBSERVED.md), and
[stopped pilot](../live_safeguard_recovery/OBSERVED.md).
