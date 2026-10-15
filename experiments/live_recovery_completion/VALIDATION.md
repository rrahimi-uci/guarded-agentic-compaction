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

Primary-run and post-run audit outcomes are recorded below; final CI is tracked on the PR.

## Budget update during execution

On October 15, 2026 the user increased the **overall estimated-spend cap to
$400** across the prior pilot, diagnostic and follow-up work. This replaces the
previous overall $200 authorization; it is not an additional $400. The active
sealed comparison retains its stricter $200 internal guard and immutable
protocol. Any subsequent authorized run must carry all prior estimates and
unknown-cost reserves forward within the $400 overall allowance.

## Completed execution and audit

All 2,304 scheduled episodes were attempted: 2,300 completed, four timed out,
2,186 completed answers correct, 114 incorrect, and zero unattempted. No retry
or replacement occurred. Recorded new-run estimated spend is $0.95269564;
aggregate estimates and retained reserves are $7.00176224. The four timeouts
remain in the denominators with captured partial usage and $1 reserves each.
All 448,212 cache-write tokens were priced successfully.

`PYTHONPATH=src python paper/scripts/complete_live_recovery.py analyze` passed
the original seal, source regrading, successful tool-output replay, usage/cost
recomputation and metric/denominator checks on every retained row. An interim
snapshot audit had also passed for 858 rows. The sole invalid continuation read
was separately replayed through the SDK's actual `ToolContext`, matching its
arguments, error status and digest. These audits made zero provider calls.

See [FINDINGS.md](FINDINGS.md) for the positive request-scope result, unresolved
completeness effect, recovery counts, resource trade-offs and broader claim limits.
Initial sealed commit `ed0b8f37d46a00f464acd8116d064a1e7a87fc64` passed both CI
jobs (run `38808209529`). Final evidence-commit CI is tracked separately on the PR.

After results, publication artifact validation again passed 5,277/5,277 checks,
and Pages again passed 9 pages/32 paths. The historical generated validation
summary was restored. Final retained counts, checkpoint digest, terminal state,
output exclusions and failure reserves also passed a direct consistency check.

The frozen analyzer emits a trailing blank line in `results.md`. After generation,
normalize only that Markdown file to one terminal newline (`text.rstrip() +
"\\n"`, with the actual newline character) before `git diff --check`; numbers and
JSON evidence are unchanged. This postprocessing preserves the executed driver
and its seal rather than editing study code after outcomes.
