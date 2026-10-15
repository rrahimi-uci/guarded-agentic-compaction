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
