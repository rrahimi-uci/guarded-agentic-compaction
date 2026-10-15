# Execution and validation record

This experiment was developed on `experiment/fresh-safeguard-comparison`, based
on `origin/main` at `d57fafe`, in an isolated worktree. It is submitted through
PR #78; it has not been merged. The manuscript and its published results are
unchanged. The live run on October 15, 2026 used the separately authorized $200
estimated-spend ceiling and completed all 480 scheduled episodes. The frozen
protocol, cohort, code hashes, environment versions, and source identities were
verified before and after execution.

## Validation

Commands were run from the isolated worktree using the repository virtual
environment and `PYTHONPATH=src` where shown below.

| Command | Result |
| --- | --- |
| `.venv/bin/python paper/scripts/fresh_safeguard_comparison.py preflight` | 120 unused issues sealed; real provider-free dispatcher probe: 119 compact / one fallback for GAC and support-only, 120 recurrence replays; zero provider calls |
| `.venv/bin/python paper/scripts/fresh_safeguard_comparison.py verify` | Passed before and after live execution |
| `.venv/bin/python -m pytest -o addopts='' -q` | 564 passed, 3 optional-data tests skipped; 186.04 seconds |
| `.venv/bin/python -m pytest -o addopts='' -q paper/scripts/test_fresh_safeguard_comparison.py paper/scripts/test_analyze_fresh_safeguards.py` | 26 experiment-specific tests are included in the full suite; six analysis tests also rerun after the final reporting clarification |
| `.venv/bin/python scripts/verify_release.py` | Passed; three documented checks needing untracked `docs/` skipped |
| `.venv/bin/python paper/scripts/validate_artifacts.py` | 5,277 passed, zero failed; the generated historical validation summary was restored to avoid changing publication artifacts |
| `.venv/bin/python scripts/build_pages.py --output _site` | Passed: 9 pages, 32 paths |
| `.venv/bin/python -m build --outdir /tmp/gac-fresh-dist` | Source distribution and wheel built |
| `.venv/bin/python paper/scripts/analyze_fresh_safeguards.py` | All 480 answers regraded with zero retained-label mismatches; paired analysis and report generated |
| `git diff --check` | Passed |

The three optional-data skips concern existing tests outside the new experiment;
the 26 experiment-specific tests pass. No provider calls are made by ordinary
tests, preflight, verification, or analysis. Live execution is a separately
invoked and budgeted command.

The raw checkpoint stores task answers, grading fields, tool sequences and
arguments, resource metrics, trace IDs, and dispatch telemetry. It omits provider
reasoning payloads and credentials. The driver disables remote trace export and
transport retries. Frozen-rate estimates are not provider invoices. Final
interpretation, including the formatting-only recurrence mismatches, is in
[`analysis/error_audit.md`](analysis/error_audit.md).

## Review status

GitHub rejected a reviewer request for `rrahimi-uci` because the PR is authored by
that account (HTTP 422: `Review cannot be requested from pull request author`).
Copilot was requested with both the documented CLI and REST forms, but no
retained review request or completed review was visible at the check. No Copilot
review or approval is claimed. Current CI and review status are recorded in the
PR rather than treated as immutable experimental evidence. Final human review
and merge remain with the user.
