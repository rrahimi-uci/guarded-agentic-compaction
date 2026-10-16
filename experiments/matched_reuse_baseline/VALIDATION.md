# Execution and validation record

The provider-free compatibility audit and prospective study were prepared on
2026-10-15 from main commit `d402017`, on a dedicated PR branch. No historical
study protocol, driver, seal, checkpoint or result was changed.

Before paid execution:

- 17 focused tests passed, including unchanged upstream function execution,
  vendor tamper rejection, discovery-only serialization, balanced fresh selection,
  the real SDK loop for all three arms, real GAC compaction, cached/write token
  pricing, partial-failure retention, induction truncation rejection, pending
  reservations, frozen memory, execution-only pilot gating and no-retry resume.
- Provider-free preparation sealed 18 pilot and 360 primary episodes; 937 unused
  non-PR issues were available. All 126 deterministic GAC probes compacted.
- The $400 aggregate estimated-spend authorization carries $7.27040089 in earlier
  estimates/reserves, including the earlier separately approved fresh comparison.
- Release verification passed; three existing untracked-document checks skipped.
- Pages build passed after using the required repository-local `_site` output
  (the tool correctly refused a temporary directory outside the repository).
- Source distribution and wheel built successfully.

Full-suite, publication validation, execution and post-run results are recorded
below when completed. Compatibility is not performance evidence. Sealed source
must remain unchanged after the first paid induction attempt.

The full pre-execution suite passed: **639 passed, 3 existing optional-data skips
in 175.93 seconds**. Publication validation passed **5,463 checks, zero failed**.
The sealed implementation was committed and pushed as
`6a9aedf7f9fddaa49d5ada4c4e1f9a66dde1009e` and draft PR #83 was opened before the
live run. The unchanged seal reverified immediately before execution.

GitHub rejected the explicit request for user `rrahimi-uci` to review because
that account is also the PR author (HTTP 422). The `copilot` login did not
resolve; the explicit bot review-request API accepted the call but retained no
review request. Final review state is verified again on the completed PR.
No review approval or merge is implied by an accepted API response.

## Completed run and retained interpretation

All 378 evaluation episodes were attempted: 377 completed and one GAC episode
failed output-schema validation. No retry or replacement occurred. The pilot
was 18/18 correct. In the primary cohort, seven-field correct counts are GAC
116/120, adapted AWM 114/120 and baseline 114/120; the historical four-field
counts are 119, 117 and 117. GAC halves provider requests and lowers observed
all-attempted deployment cost 30.8% versus adapted AWM (30.1% versus baseline).
Exact McNemar p=0.50 and Holm p=1.00 do not establish accuracy superiority.

The frozen `analyze` command passed code/source/environment/memory seals,
source regrading, tool-output replay, usage and cost recomputation. All 1,260
evaluation requests have retained usage observations, including the failed
GAC episode. Its $1 reserve remains under the frozen protocol. New known spend
is $0.30665104, including $0.0025674 for induction. Aggregate prior/new estimates
and reserves are $8.57705193, below the $400 cap. Checkpoint SHA-256:
`790570c9acfa30401ebb0c51f202e13db6f6cee4ff234b130ccaa86d7e77c7f2`.

A separately labeled post-run source audit found that issue 377 cannot satisfy
the 20-character excerpt contract (six-character title, empty body, no comments).
All three arms fail it, and it remains in every primary denominator. The audit
is an author source check, not independent human adjudication; no sealed input,
endpoint or outcome was changed. Strict `dataset bug` classification mismatches
are distinguished from demonstrated semantic falsehoods in `ERROR_AUDIT.md`.

Report reproduction, without provider calls:

```sh
PYTHONPATH=src python paper/scripts/matched_reuse_baseline.py verify
PYTHONPATH=src python paper/scripts/matched_reuse_baseline.py analyze
PYTHONPATH=src python experiments/matched_reuse_baseline/audit_errors.py
python experiments/matched_reuse_baseline/render_report.py
```

The renderer writes the Markdown report and the manuscript's primary table;
the error auditor retains a full 126-issue excerpt-feasibility inventory and all
16 incorrect/failed primary episodes. The executed study driver, adapter,
protocol, seal and upstream source remain byte-identical to the pre-run commit.

## Manuscript and publication checks

Canonical ICLR Results, Discussion, Conclusion, reproducibility statement,
external-comparator limitation, appendix, evidence index and number register
now incorporate this comparison. The PDF was rebuilt using the existing
Tectonic 0.15.0 executable; the plugin's bundled binary directory was empty.
It has 48 pages total, retains the existing ten-page main-text revision target,
and has no author metadata. Initial-submission page limits remain a separate
formatting task. The abstract and its OpenReview copy did not change.

Both CI jobs passed on the pre-run commit (run `38825564064`, Python 3.11 and
3.14). PR #83 was merged with the sealed pre-run implementation while results were being
prepared. Final evidence/manuscript CI is tracked on the separate follow-up PR. No merge,
deployment, old long-form PDF refresh or hosted-site publication is performed.

Post-run publication validation passed **5,496 checks, zero failed**. The source
and cost audit passed on the final checkpoint, and the report/table generation
is reproducible without provider access. Visual inspection covered the main
Discussion/Conclusion and the new table and interpretation. Section 8 ends on
page 10. There are no undefined references/citations or overfull boxes.
