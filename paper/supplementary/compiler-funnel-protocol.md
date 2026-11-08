# Same-IR compiler funnel protocol (P1-lite of `gac-expansion.md`)

**Status: registered 2026-11-08 before any policy other than the shipped one was run.**
Provider-free: every pass replays recorded tool results from the pinned snapshots; no model is
called and nothing is dispatched. Spend $0.

## Question

Reviewers 1 and 2 asked how GAC compares with simpler compilers and which of its mechanisms a
decision can be attributed to. The matched-compiler feasibility report
(`paper/results/matched_compiler_feasibility/REPORT.md`) found no runnable external comparator
and said the comparator policies "must become compiler-level policies over the common candidate
list". This study does that for the two mechanisms that distinguish GAC from recurrence-based
compilation, on every GitHub cohort whose discovery traces are retained:

- **Grounding** (every argument slot must have a witness: an invariant literal or an expression
  over the entry state and earlier results; an ungroundable slot refuses the candidate).
- **Statistical admission** (the calibrated gate with the Clopper--Pearson bound at
  alpha = 0.05, delta = 0.10 over the registered threshold grid).

## Policies (a 2 x 2 over the same compiler, same traces, same splits)

| Policy | Grounding | Statistical admission | What it models |
|---|---|---|---|
| P1 `full` | on | on (alpha = 0.05) | GAC as shipped |
| P2 `support_only` | on | off (alpha = 1.0: the gate accepts every calibrated candidate; calibration still runs and its counts are recorded) | a compiler that keeps GAC's grounding but admits on support alone |
| P3 `recurrence_only` | off | off | recurrence-based compilation: what recurs is compiled, an ungroundable slot becomes its modal training literal |
| P4 `stats_only` | off | on (alpha = 0.05) | statistical admission without grounding |

"Grounding off" is implemented as a majority-literal fallback in Algorithm 3: when
`synthesize_binding` finds no invariant literal and no expression, the slot is bound to the most
frequent training value (lexical tie-break) instead of refusing. Everything else -- mining,
guard and verifier induction, the recorded-replay challenge on development groups, calibration
replay on calibration groups, dominance selection -- is the shipped code. Mining-level blocks
(windows that never form because a slot is ungrounded at the graph level) are the same in all
four policies and are reported; this is a limitation, since a recurrence-only miner would not
block them.

## Cohorts

Exactly the retained discovery checkpoints, reconstructed against their pinned snapshots with the
production split rules (16 / 8 / 92, stable hash):

- issue-type routing (`paper/results/github_natural_replication/discovery_checkpoint.json`);
- PR-outcome (`paper/results/github_workflow_families/pr_outcome/pilot_v1/discovery_checkpoint.json`);
- backlog attention (`paper/results/github_workflow_families/backlog_attention/final/discovery_checkpoint.json`);
- the ten repositories of the multi-repository end-to-end study with a retained
  `discovery_checkpoint.json` (`paper/results/multirepo_end_to_end/<owner>__<repo>/`; huggingface
  used a frozen registry and psf/requests was not run), with the study's
  `freeze_one_candidate_before_calibration = True`.

The P1 pass must reproduce the retained decision of each cohort (artifact admitted, same tools,
same rejection stages); a mismatch stops the study.

## Outputs and measures

Per cohort and policy: the admitted artifacts (tools, removed requests, support), every candidate
with its terminal stage and reason (`rejection_by_stage`, candidate notes), mining-level blocks,
and for every candidate that reached calibration the replay counts over the calibration groups
(`gate_calibration_samples`, `gate_calibration_violations`, `gate_calibration_unproductive`,
reasons). The **divergence set** is every (cohort, candidate) that some policy admits and P1
refuses, with the stage at which P1 refused it and the calibration replay counts of the admitting
policy. Those replay counts are the replay half of H3 ("does the compiler's refusal prevent an
error"): a refused candidate with zero replay violations on the calibration groups is a refusal
that cost savings without a measured quality benefit on that cohort; a refused candidate with
violations is a prevented error.

## Pre-stated expectation (recorded so that it cannot be adjusted afterwards)

From the retained records, the only known divergence is the issue-type three-read candidate,
refused by P1 at synthesis (`issue_get_comments.limit` has no witness; 130 of 132 discovery runs
use 100 and two use 1). P3 is expected to admit it with `limit = 100`; its replay on the
calibration groups is expected to be clean except where the recorded run used `limit = 1`, which
the facade should classify as a recording miss (unproductive), not a violation. PR-outcome,
backlog and the ten repositories are expected to be equal-routing nulls, as Appendix K found for
the gate at runtime. The result is reported either way.

## What this study cannot show

Live quality or cost of any policy (nothing is dispatched); anything about external compilers;
anything about workloads other than these GitHub families; the effect of a recurrence-only
*miner* (mining is shared). The live pilot that prices the policies on fresh pull requests is a
separate, sealed protocol.

## Outputs

`paper/results/compiler_funnel/results.json`, `paper/results/compiler_funnel/README.md`,
`paper/iclr/tables/compiler_funnel.tex` (not input by the paper), produced by
`python paper/scripts/compiler_funnel.py run|table`; unit tests in
`paper/scripts/test_compiler_funnel.py`.
