# Live pilot for the compiler funnel's one divergence (sealed)

**Status: sealed 2026-11-08 before any provider call.** Draft of the same day revised after the
provider-free preflight (`paper/results/compiler_funnel_pilot/preflight.json`), which fixed the
cohort, the split and the spending cap. The author approved the spend ("seal and run the
issue-type pilot"). The script is `paper/scripts/compiler_funnel_live_pilot.py`; every phase
below is one of its commands and writes its own checkpoint.

## Why issue-type, not PR-outcome

The same-IR funnel (`paper/results/compiler_funnel/`) shows that on PR-outcome, backlog attention
and the ten multi-repository cohorts all four compiler policies emit the same program, so a live
comparison there would execute identical compiled arms. The only cohort where the policies diverge
is issue-type routing: GAC admits the two-read prefix and refuses the three-read candidate whose
`issue_get_comments.limit` has no witness; a recurrence-based compiler admits the three-read program
with `limit = 100`. The retained live measurement of that divergence is the 30-record recurrence-only
ablation (30/30 for both, one fewer request for the replay; Table 33). This pilot repeats the
divergence on a fresh, larger, post-cutoff cohort.

## Change from the draft: GAC is re-derived on fresh discovery traces

The draft proposed dispatching the retained two-read artifact. Its guard pins
`z.issue_number in [148, 7561]` and `source_revision = e344be7b...`; every post-cutoff issue
(numbers 7617 to 8763, a different snapshot digest) would therefore be ineligible and the "GAC" arm
would silently be the unchanged agent. The pilot instead follows the time-forward PR-outcome design:
the unchanged agent runs once on a discovery split of the fresh pool, GAC compiles from those traces
with the retained configuration (16 train / 8 dev / 92 calibration groups, registered grid,
alpha 0.05, delta 0.10), and the three arms are run on the disjoint test split. The same discovery
traces are also pushed through the four same-IR policies of the funnel, so the pilot reports
whether the grounding divergence recurs on fresh data before any test arm runs.

## Cohort (fixed by the preflight, no provider call)

Post-cutoff `huggingface/datasets` issues (not pull requests) from the time-forward snapshot
(`paper/results/datasets/github_time_forward/huggingface__datasets/snapshot.parquet`, created
after 2025-06-13, fetched 2026-10-07), with at least one comment, excluding the four numbers that
appear in retained result files of the same record space (7693, 7694, 8029, 8590; the
field-rule scan of the preflight is recorded alongside). Counts: 277 issues, 197 with a comment,
193 in the pool. The pool is split by a stable SHA-256 rank (seed 20261108, namespace
`tf-issue-pilot`): the first 128 are **discovery**, the remaining 65 are **test**. Neither split is
extended, re-drawn or filtered on outcome. No stratification by label: the pool is 172 `other` and
21 `enhancement` by the retained routing rule.

## Phases

1. **discovery** (live): unchanged agent, snapshot tools, retained prompt and settings
   (`gpt-5.6-luna`, reasoning low, `max_turns` 8, 120 s timeout, concurrency 8), one episode per
   discovery issue, one retry per timeout. Graded by the retained exact source-grounded oracle.
2. **compile** (provider-free): compiler eligibility by the retained rule
   (`github_live_study.compiler_eligible`); GAC compiled via `compile_artifact` with the retained
   configuration. If fewer than 116 traces are eligible, or the compiler admits nothing, the GAC arm
   is reported as not derivable and the remaining two arms still run. The four funnel policies run on
   the same discovery traces (`compiler_funnel.compile_with`); the divergence list is recorded.
3. **test** (live), paired on every test issue, balanced six-permutation Latin order by stable rank:
   - **compiled**: GAC's admitted artifact dispatched pre-model through `CompactingModel` (live mode);
     an issue the guard or gate declines falls back to the unchanged agent and is counted as such.
   - **recurrence_only_three_read**: the three-read replay with `limit = 100` and every barrier
     disabled, exactly the arm of `recurrence_only_ablation.py`, bound to the fresh snapshot.
   - **baseline**: unchanged agent.
   Same model, prompts, timeout, retry and oracle as phase 1.

## Endpoints and decision rule

Primary: paired exact factual contract (`factuality_exact`), compiled vs recurrence-only, and each
vs baseline (exact McNemar on discordant pairs, two-sided, 0.05, as in `paired_analysis`).
Secondary: provider requests, tokens, estimated cost and latency per episode; the compiled arm's
dispatch classes (attempted / abstained / ineligible). The pilot is descriptive: with 65 pairs it can
detect only large differences and is reported as a pilot whatever it shows. No arm is dropped or
re-run on outcome; an episode that fails after one retry counts against its arm.

Pre-stated expectation (from the funnel's replay and Table 33): both compiled programs meet the
contract on nearly every test issue; the recurrence-only arm uses one fewer request per issue than
GAC; the baseline uses about four. A recurrence-only miss that GAC does not share would be the first
live price of the missing guard and is reported ahead of every other reading.

## Spend

Discovery 128 episodes plus test 3 x 65 = 195 episodes, plus retries: about 323 to 350 provider
requests of the retained cost class (0.0004 to 0.0009 USD per episode). Expected spend about 0.25
USD; **approved cap 5.00 USD** (within the author's 25 USD hard cap and the 300 USD campaign).
The ledger (`ledger.json`) refuses a phase whose reservation would cross the cap.

## What it cannot show

Anything about PR-outcome or backlog (identical arms there); anything about external compilers;
a population effect size (pilot power); anything about the pre-cutoff snapshot.
