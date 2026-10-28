# Sequential calibration extension of the graded issue gate

**Status: registered 2026-10-28 before any provider call; the first execution
attempt the same day was rejected by the provider (401 `invalid_api_key`) before
any episode completed, so the design is sealed but not yet executed (see the
execution record at the end).** This is a *sequential extension* of the amended v2
study in `paper/supplementary/graded-issue-end-to-end-gate-protocol.md`. It was
designed after the first calibration result (184 groups, 2 task errors, no
admissible threshold; `results_v2.json`, `audit_v2.json`) had been observed.
That ordering is disclosed here and in the paper: the extension is not an
independent replication, and any admitted threshold is conditional on the
decision to extend having been taken after seeing the retirement.

## What is frozen

- **Score and grid.** The six-feature logistic score `q`, the eleven-point grid
  `(0.02, 0.05, 0.08, 0.11, 0.14, 0.17, 0.20, 0.25, 0.30, 0.40, 0.50)`,
  `alpha = 0.05`, `delta = 0.10`, minimum coverage `0.02`, and the one-sided
  Clopper-Pearson bound at level `delta/|Lambda| = 0.1/11` are reused
  byte-identically from `frozen_gate_v2.json` (SHA-256
  `c66af83acac0bc883f970140e874560ef35ff9f80144d0115e13e763d918c35a`). No
  feature, weight, grid point, or budget parameter is changed to obtain
  admission. A retirement is a result.
- **Candidate and runtime.** The same re-derived candidate
  (`candidate_v2/registry/registry.json`, SHA-256
  `bbe554b95285259dbf3e401ba8f48121d283daad7eb57429a8d5120fd4d73dd9`), model
  string `gpt-5.6-luna`, SDK pins (checked through the manifest compatibility
  key), settings (`reasoning=low`, `verbosity=low`, `parallel_tool_calls=False`,
  `store=False`), 120 s per-episode timeout, no retries, eight-issue batches
  with a $1 per-episode reserve, and the fail-closed checkpoint rule as
  `results_v2`. Every arm pays the same counted pre-dispatch local read.
- **Test set.** The 90 sealed test issues of `preflight.json` (SHA-256
  `c54dd355741bd4c2e2be2c9784c44956f0dec9375cb6b74feb77a397095d8a9b`) stay
  untouched until a threshold is fixed on the pooled calibration set. They are
  run only under that threshold, exactly once.

## Fresh calibration cohort: forced size, not chosen

`paper/scripts/graded_issue_gate_extension_preflight.py` seals
`extension_preflight.json` (SHA-256
`eea46635c807d6af18b8c1069393bcf5e5d34c2d44e26685191906ba6e974fb9`) with zero
provider calls. The fresh cohort is **every** remaining eligible issue in the
pinned public snapshot (`helmo/github-issues`, parquet SHA-256
`09453eef...`), after the canonical duplicate-row rule, excluding pull
requests and issues without comments, and excluding every issue number that
appears in

1. any retained JSON under `paper/results/` (the original rule; 6,374 numbers),
2. the invalid 90-record gate-frontier pilot cohort (the original rule),
3. the original 474-issue cohort of this study, and
4. **any retained JSON under `experiments/`** (1,728 numbers, 748 of them not
   in the results tree). The original exclusion scanned `paper/results/` only;
   this extension closes that gap. The original 474 issues and the 90 pilot
   records are disjoint from the `experiments/` numbers, so the v2 result is
   not affected by the gap.

The remainder is **127 issues** (plain text 80, bare URL 43, Markdown link 4;
categories bug 21, enhancement 11, other 95); 52 further unused issues have no
comment and are ineligible. The pool is exhausted at 127: no quota design is
possible, the Markdown-link stratum is nearly absent, and the fresh cohort is
the natural remainder rather than the enriched quota mixture of the original
184. A further 55 issues are unused except by the invalid pilot; the original
rule treats them as spent and the extension keeps that rule rather than
relaxing it after the fact. The pooled calibration set is therefore
184 + 127 = 311 groups.

**Pool enlargement check.** No other retained snapshot shares the pinned
manifest. `paper/results/datasets/github_time_forward/huggingface__datasets`
is the same GitHub repository but a different fetch (post-cutoff records under
its own manifest and age cutoff), and the four `github_multirepo` snapshots are
other repositories. The pool cannot legitimately be enlarged under the same
manifest; `extension_preflight.json` records the check.

**Exact binomial facts** (one-sided bound at level 0.1/11, limit 0.05): the
smallest accepted-group count that admits `k` violations is 92 (k = 0), 133
(k = 1), 168 (k = 2), 200 (k = 3), 231 (k = 4), 261 (k = 5). On the fresh set
alone (127 groups) only zero violations can admit any threshold. On the pooled
set, full coverage (about 83% of 311, roughly 258 groups at `eta = 0.50`) admits
up to four violations.

## Pre-registered analyses, in this order

(a) **Primary.** Algorithm 1 (`calibrate_gate`, frozen external model) on the
pooled calibration set: the 184 retained v2 calibration groups, regraded from
`checkpoint_v2.json`, plus the 127 fresh groups; `alpha = 0.05`,
`delta = 0.10`, the same grid. The runner records the full eleven-row sweep.
The admitted threshold, if any, is the largest admissible grid point (maximum
coverage), as the algorithm already does.

(b) **Secondary.** The same algorithm on the 127 fresh groups alone.

(c) **Conditional test.** If and only if (a) admits a threshold `eta*`, run the
90 sealed test issues: the unchanged agent on all 90; the learned routing
(compiled runtime where `q <= eta*`, unchanged agent otherwise, exactly the
study's dispatch rule); and the support-only routing (`alpha = 1`, accept-all,
the registered ablation). Report task errors per arm with a one-sided 95%
Clopper-Pearson bound, actual compiled dispatches, wrong answers after compiled
dispatch (adverse events, foregrounded), and the paired baseline-versus-learned
discordance. If (a) retires, the test set is not run and the retirement is the
primary outcome.

(d) **Descriptive frontier.** Violation counts per grid row on the pooled set,
and a one-sided Fisher exact test that the violation rate among groups with
`q` above the lowest admissible threshold exceeds the rate at or below it. If no
threshold is admissible the split is the lowest grid point (0.02). This is
descriptive and low-powered with two to a handful of events; it is not a
certificate and is not used for any decision.

## Execution, retention, and spending

`graded_issue_gate_study.py --extension --approved-spend-usd 25` checks the
sealed extension against a fresh rebuild and the pinned hashes, refuses to run
if `results_extension.json` exists, uses its own `checkpoint_extension.json`
(never the v2 checkpoint), and retains every raw episode of every phase under
`extension_episodes/<phase>.json` with the same redaction as the v2 candidate
discovery (opaque reasoning items and `encrypted_content` removed; original
and redacted digests kept per row). The budget guard counts the extension's
own spend, the v2, candidate, and aborted-v1 estimates, and the $1 per-episode
reserve against the **$25 cap**. If the provider rejects calls, a batch is
incomplete, or the estimate would exceed the cap, the runner stops and the
state is reported; no design change is improvised.
`audit_graded_issue_gate_extension.py` recomputes every count, bound,
decision, routing, episode digest, and dollar from retained records without a
provider call and generates `paper/iclr/tables/gate_extension.tex`.

## Interpretation limits

One selected repository and one candidate; the original 184 groups follow the
quota mixture while the fresh 127 are the natural remainder, so the pooled set
is a mixture of two sampling frames; the extension decision followed an
observed retirement; the public estimate is not an invoice. An admitted
threshold would show that the frozen score can certify intermediate coverage
on this pooled set at the registered level. It would not establish graded
selectivity (that needs the frontier evidence the main paper lacks),
cross-repository generalization, or a quality or savings benefit beyond what
the 90-issue test shows.

## Execution record

**2026-10-28, attempt 1: aborted on provider authentication; nothing observed.**
`graded_issue_gate_study.py --extension --approved-spend-usd 25` passed every
pre-call check (sealed cohort rebuilt byte-identically, hash pins intact, v2
candidate resolved under the live manifest) and dispatched the first
eight-issue batch (issues 202, 216, 730, 743, 769, 801, 809, 812). Every call
returned HTTP 401 `invalid_api_key`; no episode produced a provider response,
so no task grade, dispatch, score, or test-set exposure exists from this
attempt and the recorded estimated cost is $0 (a zero-cost `models.list` call
with the same key reproduced the 401). The runner stopped fail-closed after
the batch. The raw checkpoint is retained as
`checkpoint_extension_aborted_2026-10-28.json` with the provider's error
messages reduced to status and code (they echoed a masked key fragment), and
`extension_abort.json` summarizes the attempt. Because nothing was observed,
re-running the same sealed design with a valid key is a retry of this
protocol, not an amendment: no cohort, feature, grid, budget, or analysis
order changes, and the retry starts a fresh `checkpoint_extension.json`.
The 90 test issues remain untouched.
