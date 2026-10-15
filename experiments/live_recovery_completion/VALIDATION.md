# Validation and execution record

Local validation on October 15, 2026 uses the repository's existing virtual
environment, with this worktree's `src` on `PYTHONPATH`.

- Focused completion tests: 18 passed, including real SDK loops with fake models.
- Prospective `prepare` and `verify`: 2,304 episodes sealed and verified without
  primary provider calls. Code, configuration, dependency and source hashes,
  complete cohort/schedule and real dispatcher preflight agree.
- Release verification passed; three existing untracked-docs checks skipped.
- Paper artifact validation: 5,277 passed, zero failed. Restored the generated
  historical validation summary afterward.
- Pages build: 9 pages, 32 paths valid.
- Source distribution and wheel built.
- Original pilot code, protocol, seal and retained results unchanged.

The diagnostic contains one separately identified replay; it reproduced rejection
of cache-write usage after a correct final answer. Its exact driver is archived
and hash-bound. Its reserved cost is included with the stopped pilot in the
$2.0490666 carried forward against the single user-approved $200 estimated cap.

Full suite: **622 passed, 3 optional-data skips in 175.91 seconds**. A trailing
blank line was removed afterward without behavioral changes; the unused seal
was replaced before any primary provider call to bind that whitespace cleanup.
The final run verifies its seal again before executing.

Primary-run, post-run audit and final CI outcomes will be added below.
