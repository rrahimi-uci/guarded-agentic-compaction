# Live pilot for the compiler funnel's one divergence (DRAFT, not sealed)

**Status: draft 2026-11-08; no provider call is authorized by this document.** It becomes a sealed
protocol only when the cohort count, the arms' frozen programs and the spending cap are filled in
from a provider-free preflight and the author approves the spend.

## Why issue-type, not PR-outcome

The same-IR funnel (`paper/results/compiler_funnel/`) shows that on PR-outcome, backlog attention
and the ten multi-repository cohorts all four compiler policies emit the same program, so a live
comparison there would execute identical compiled arms. The only cohort where the policies diverge
is issue-type routing: GAC admits the two-read prefix and refuses the three-read candidate whose
`issue_get_comments.limit` has no witness; a recurrence-based compiler admits the three-read program
with `limit = 100`. The retained live measurement of that divergence is the 30-record recurrence-only
ablation (30/30 for both, one fewer request for the replay; Table 33). This pilot extends it to a
fresh, larger cohort.

## Cohort

Post-cutoff `huggingface/datasets` issues (not pull requests) from the time-forward snapshot
(`paper/results/datasets/github_time_forward/huggingface__datasets/snapshot.parquet`), with at least
one comment, whose number appears in no retained record. The no-go preflight for the single-look gate
study counted 277 issues, 197 with a comment, 111 to 193 after exclusion depending on the rule
(`paper/results/graded_issue_gate_tf/preflight.json`). This pilot needs no candidate re-derivation
(the programs are fixed below), so the whole eligible pool is the cohort; n is fixed by the preflight
before any call and never extended.

## Arms (paired on every issue)

1. **GAC as shipped**: the retained two-read artifact re-derived on the time-forward snapshot's
   manifest (the v2 candidate pins the old snapshot and would abstain), dispatched pre-model.
2. **Recurrence-only**: the three-read program the funnel's grounding-off policy emits
   (`issue_get_record(z.issue_number)`, `issue_get_labels(get.issue_number)`,
   `issue_get_comments(get.issue_number, limit = 100)`), as a `ManualPreModelPlan` with no gate,
   exactly the ablation arm of `paper/scripts/recurrence_only_ablation.py`.
3. **Unchanged agent**.

Same model, prompts, `max_turns`, timeout and retry rule as the retained issue-type study; the
exact source-grounded oracle of that study grades the final contract.

## Endpoints and decision rule

Primary: paired exact-contract success, arm 1 vs arm 2 (McNemar, two-sided, 0.05) and each vs arm 3.
Secondary: provider requests, tokens, estimated cost, latency per episode. The pilot is descriptive:
with n in the low hundreds it can detect only large differences, and it is reported as a pilot whatever
it shows. No arm is dropped or re-run on outcome.

## Spend

Three arms on at most 197 issues: at most 591 episodes plus one retry per timeout. Reference cost
from the retained issue-type runs is about $0.0003–0.0009 per episode per arm; cap to be set at the
preflight, expected under $5, hard cap $25 within the $300 campaign.

## What it cannot show

Anything about PR-outcome or backlog (identical arms); anything about external compilers; a
population effect size (pilot power).
