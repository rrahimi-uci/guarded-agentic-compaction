# Unfiltered, author-unit, time-forward end-to-end calibration of PR-outcome across repositories

**Status: PRE-REGISTERED 2026-11-07, before any provider call and before any label is inspected.
The commit that adds this file is the registration. Amendments are appended below with a date and
are never applied after a result for the affected repository is observed.**

Answers ICLR 2027 reviews of forum `DF0JaS58gr`: R1 (calibration population is outcome-filtered;
labels are replay-only), R2 (label path; filtering before the split), R3 (selection-wide 5% bound;
independent units). Extends `time-forward-end-to-end-protocol.md` (executed 2026-10-07 on one
repository, $0.2154) and supersedes the NO-GO `multiplicity-repair-protocol.md` with fresh data.

## Question
For a frozen compiled PR-outcome artifact, what is the end-to-end task-contract violation rate on
fresh pull requests of each repository when calibration groups are sampled **before** any outcome or
region-occurrence filter, one per distinct author, and every group is labelled?

## Frozen design
- **Family and task.** `pr_outcome` (three reads: record, merge status, discussion), prompts, tools,
  grader and compiler of `paper/scripts/github_workflow_family_study.py`; model `gpt-5.6-luna`,
  settings of the time-forward study. Arms on the same groups: unchanged agent, compiled artifact
  (continuation run once and graded on the exact contract), hand-written program.
- **Repositories and sources.**
  | Repository | Source | Discovery |
  |---|---|---|
  | huggingface/datasets | existing post-cutoff snapshot `paper/results/datasets/github_time_forward/huggingface__datasets` | none; frozen registry `paper/results/time_forward/pr_outcome/registry` |
  | pandas-dev/pandas | new acquisition, created after 2026-01-01 | 132 records, new frozen artifact |
  | streamlit/streamlit | new acquisition, created after 2026-01-01 | same |
  | psf/requests | new acquisition, created after 2025-06-14 (largest available window) | same |
  | pytorch/pytorch | new acquisition, created after 2026-10-01 | same |
- **Exclusions.** Repository-qualified record numbers used by any retained study of the same
  repository (`paper/results/`, `experiments/`). No outcome, class, dispatch or recurrence criterion.
- **Unit.** One pull request per distinct `user.login`; stable SHA-256 rank with the tag
  `multirepo-e2e:<repo>:pr_outcome:<number>`. Distinct creation days are reported.
- **Splits (new repositories).** Discovery: 132 records, round-robin over classes where available,
  shortfalls filled in rank order and recorded. Calibration: the next author-distinct records in rank
  order, **n = min(200, available)**, disjoint from discovery in records and in authors. No test split.
  A repository runs only if n >= 106; otherwise the shortfall is the result.
- **Splits (huggingface/datasets).** Calibration: author-distinct unused post-cutoff PRs, authors
  disjoint from the 132 discovery records of the frozen registry, n = min(200, available), run only if
  n >= 106.
- **Candidate.** One per repository, frozen before calibration (`freeze_one_candidate_before_calibration`,
  m = 1). If compilation retires, that is the result.
- **Labels.** For every calibration group: eligible (hard guard passes)? dispatched? verifier abstained?
  contract met, for each arm? Violation = compiled arm dispatched and the final contract missed.
  Clean abstention stays in n with loss 0. Guard-ineligible groups are reported and are not in n.
  Fallback continuations are graded and reported. A timed-out episode stays in the denominator as a
  failure; there is no retry.

## Decision rules (fixed in advance; recompute with the exact `cp_upper` for the realised n)
- **Primary.** Registered grid, alpha = 0.05, delta = 0.10, |Lambda| = 11, m = 1: admit iff k <= the
  largest k with U(k, n; 1 - 0.1/11) <= 0.05. At n = 200 this is k <= 3 (U(0) = 0.0232); at n = 106,
  k = 0.
- **Secondary.** Single rule gamma = delta = 0.10, m = 1 (at n = 200, k <= 5).
- **Pooled.** All admitting repositories pooled, registered grid, m = 1, as a second pre-declared
  estimand that does not assume exchangeable repositories.
- **Paired.** Unchanged agent versus compiled arm, exact McNemar, one-sided 95% bound on compiled-only
  misses (0.0149 at 0/200). No noninferiority margin is pre-declared; the end-to-end certificate is the
  primary endpoint. Resource reductions as in Table 1 of the paper.
- Adverse results (violations, retirements) are reported before any reduction.

## Execution and spend
Pilot of 10 groups on huggingface/datasets first. Live phases refuse to run without
`--approved-spend-usd`: $5 per repository, no retries, batches of 8, checkpointed, one ledger per
repository. The campaign cap is $300 in total; this study is expected to cost under $5.

## Claim boundary
Per-candidate (m = 1, therefore compiler-wide for that frozen artifact), end-to-end, unfiltered,
author-unit certificate for one family on fresh pull requests of the named repository, conditional on
independent authors. It says nothing about adaptive-task value, learned-gate value, superiority over the
hand-written program (a tie is expected), issue-type or backlog families, or repositories not run.

## Amendments
(none)
