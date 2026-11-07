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
**Amendment 1 (2026-11-07, before any provider call and before any label).**
1. For huggingface/datasets the exclusion rule is the repository-qualified one (`--qualified-exclusion`): only record numbers used by retained studies of that repository are excluded. The legacy rule also excluded numbers that merely collide with other repositories' record numbers and would leave n = 106. Selection digest `3ef976c2...` (200 author-distinct groups, 200 distinct authors, 147 distinct days; classes 143 open, 55 merged, 2 closed-unmerged; 2 bot logins counted as authors, not filtered). The certificate therefore covers mostly open and merged pull requests; the closed-unmerged class is essentially unrepresented and no claim is made for it.
2. A failed, timed-out or missing compiled-arm episode is a violation: it stays in n and counts in k. (The protocol text said it stays in the denominator as a failure; this states how it is counted.) Failed baseline or manual episodes count as contract not met in their own arm.
3. Calibration authors are disjoint from the 81 distinct discovery authors of the frozen registry's 132 discovery records.


**Amendment 2 (2026-11-07, after selection of the three new repositories and before any provider call or label for them).**
1. Snapshots were acquired with `github_time_forward_acquire.py` (commit e182878 makes it retry network timeouts). Cutoffs strictly after: pandas and streamlit 2025-12-31, pytorch 2026-09-30, requests 2025-06-13. The requests no-run result stands: the registered selection leaves 99 author-distinct calibration groups after the 132 discovery records and the used-record exclusion, below the 106 minimum. It is not re-run on the larger raw snapshot.
2. Selections (all `repository-qualified`, one pull request per author, authors disjoint from discovery, no test split):
   | Repository | Discovery | Calibration n | Calibration classes (merged / closed-unmerged / open) | Distinct days | Digest |
   |---|---|---|---|---|---|
   | streamlit/streamlit | 132 | 160 | 28 / 130 / 2 | 110 | `ddd1af97...` |
   | pandas-dev/pandas | 132 | 200 | 71 / 124 / 5 | 143 | `f7487df2...` |
   | pytorch/pytorch | 132 | 200 | 0 / 86 / 114 | 37 | `17871afd...` |
3. The grid and single-rule admission limits are recomputed for the realised n. Registered grid, m = 1: k <= 1 at n = 160 and k <= 3 at n = 200. Single rule: k <= 4 at n = 160 and k <= 5 at n = 200.
4. pytorch/pytorch lands pull requests through a merge bot, so only 55 of 3,674 acquired pull requests carry `merged_at`. The snapshot label `closed_unmerged` therefore mostly denotes landed pull requests, and the calibration contains no merged class. The certificate for this repository is about contract agreement with the snapshot-defined label on open and closed-unmerged pull requests over a 37-day window. It is not a claim about merge outcomes. It is reported separately and is excluded from nothing in the pooled estimate, but its caveat is stated beside any pooled number.
5. Streamlit's calibration is below the requested 200 (160 available) and its 183 distinct authors include bot logins. Bot logins (streamlit 3, pandas 3, pytorch 1, hf 2) are counted as authors and not filtered, as in huggingface/datasets.
