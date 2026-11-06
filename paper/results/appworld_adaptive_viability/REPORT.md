# AppWorld adaptive development pilot: interrupted measurement

**Decision: NO_GO for confirmatory compiler-value claims. The original task grades
are invalid because the direct-API adapter did not persist final state.** Paid
execution stopped as soon as this boundary defect was suspected. There were no
paid retries or replacement tasks. This report does not estimate comparative quality.

| Arm | Scheduled | Completed with invalid grade | Interrupted | Unstarted | Model responses | Accounted API upper estimate |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 12 | 5 | 0 | 7 | 120 | $0.309385 |
| manual_prefix | 12 | 4 | 1 | 7 | 107 | $0.296596 |


The planned comparison selected 12 official training scenarios, one variation per
scenario, in a fixed hash order. All were development-only and previously exposed.
The handwritten arm executed two actual supervisor reads, counted in the same API
limit, before the same model continuation. Arm order alternated. Model, context
policy, task list and limits were never tuned in response to scores.

## Two independent environment findings

Before paid execution, the original dependency environment passed 11/12 reference
controls and all 24 negative controls. One reference grader raised SQLite
missing-table exceptions. A SQLAlchemy 2.0.44 / SQLModel 0.0.44 image resolved the
same unmodified case. All 36 controls passed on that image. The complete data tree
is unchanged: 14,885 files with the same aggregate hash. This identifies a working
dependency pair, not the individual cause. Upstream's
[separate compatibility issue](https://github.com/StonyBrookNLP/appworld/issues/229)
motivated investigation but does not establish the cause of our different error.

Those reference controls used `AppWorld.execute`, which saves state automatically.
The model adapter used `Requester.request`, which does not; `AppWorld.close` does
not save either. The official evaluator consequently read the initialization
snapshot. The original negative controls could not detect this defect.

A provider-free reproduction sent the same 25 known-correct public API calls
through the agent path. All responses matched the reference. The original worker
passed 0/6 grading assertions; explicit `world.save()` before `world.close()`
passed 6/6. The correction now fails the worker if persistence fails, and cleanup
still closes the environment. Saving is trusted evaluator plumbing, outside the
agent tool's SQL-effect diagnostic. It is not an added agent capability.

The corrected actual agent path passed all three controls: known-correct public
calls, empty interaction and false completion. A separately sealed repair then
replayed every completed original history, with no model calls, requiring exact
public-context and API-result equality. Original records were never overwritten.

Diagnostic regrades with exact parity: 9/9; official task successes among those replays: 0. These are deterministic regrades of an interrupted development run, not fresh adaptive trials or a comparative estimate.


## Compiler interpretation

Discovery retains every scheduled baseline disposition, including failed and
unstarted attempts; all original outcome labels are marked unknown. The first
eight scenarios are discovery groups and the last four development challenge
groups. There are no calibration/test groups and no admitted artifacts.

```text
GRC compile report
──────────────────
candidates mined        0
artifacts emitted       0
rejections by stage     {'qualify:missing_outcome': 12, 'qualify:no_events': 7, 'qualify:no_model_boundaries': 7}
```


Before paid execution, the analysis plan recorded that the audited initial-prefix
catalog permits only documentation/profile/password reads. Authentication remains
a write barrier; other APIs remain unknown. This scope cannot establish two
nontrivial compiler families, regardless of task scores. No gate was relaxed to
produce a candidate. The interrupted traces provide neither compiler superiority
nor learned-gate, population-risk or maintenance-economics evidence.

## Next decision and retained evidence

Do not scale or resume this sealed pilot. A new workload/entry protocol must expose
meaningful audited reads before a write barrier, with identical initialization and
information across arms. An explicitly preauthenticated entry is one possible new
protocol, not an implemented result or a reason to reclassify login. Before further
paid trials, validate known-correct sequences through the exact model-call and
grading path, then establish candidate viability and a competent baseline. Freeze
fresh independent calibration/testing only after those gates pass. Alternatively,
narrow the paper to the contribution already supported.

The $8 local allocation and $300 campaign cap remain binding. All interrupted-call
reservations remain charged. API amounts are conservative accounting, not invoices
or total lifecycle costs. No manuscript numerical claim or PDF changed.

See [aggregate report](report.json), [original seal](seal.json),
[original pre-execution analysis plan](analysis_plan.json),
[explicit analysis amendment](analysis_amendment.json), [provider-free repair plan](repair_plan.json),
[ledger excerpt](ledger_excerpt.json), [encrypted records](operational_evidence.bundle),
and [protocol](../../../experiments/appworld_adaptive_viability/README.md).
Original frozen source bytes, failed controls, diagnostics and regrades are retained
inside the bundle. Historical seals refer to those original bytes; the checked-in
worker includes the separately documented persistence correction. The original
runner refuses source drift and stopped attempts, so it cannot resume this pilot.

Use the pinned upstream bundle utility and public distribution constants to inspect
protected records locally; do not redistribute decrypted contents. Export verifies
an encrypt/decrypt round trip against every original raw file hash.
