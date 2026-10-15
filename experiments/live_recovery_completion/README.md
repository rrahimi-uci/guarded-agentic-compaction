# Prospective live recovery completion study

This follow-up preserves the stopped pilot in `../live_safeguard_recovery/`.
The user authorized completing the comparison on October 15, 2026 using the
remaining portion of the existing $200 estimated-spend cap. This authorization
covers the diagnostic and the new run below; it is not a second $200 allowance.

## Diagnosis and intervention

One separately retained replay of `6273:ordinary:5` returned the correct answer
but failed the old usage validator: its third response contained 1,040 cache-write
input tokens. The SDK reports these tokens and the repository rate card already
prices them, but the pilot deliberately rejected nonzero cache writes. The
original failure retained no usage, so this reproduces a concrete failure mode
rather than proving the original attempt's exact cause. `diagnostic.json` binds
its exact archived driver, `diagnostic_driver.py.txt`; the archived local env-file
path is not a credential. The diagnostic is excluded from primary outcomes.

The follow-up corrects cost accounting to partition total input into ordinary
input, cache reads and cache writes, charging each once at the unchanged sealed
repository rates. Reject negative counts, overlapping partitions, missing usage
and inconsistent totals. Rate-card estimates are not invoice amounts or current
public price assertions. Preserve known completed-response usage on failure and
reserve another $1 for each failed attempt's unknown cost.

No change to the model, prompt, tools, answer contract, model settings, turn/time
limits, prefetch artifact, guard, verifier, gate, source oracle or source data.
The full/no-entry-hull/no-completeness-check/baseline comparison uses the original
live pilot's exact configuration. Both SDK and transport retries remain disabled.
An observation wrapper retains numeric usage and safe exception stage/class and
stack locations; no raw provider responses, reasoning, exception messages or
credentials are serialized. The offline gate does not certify live answers.

## Frozen cohorts and execution

Use all 96 issues in the prior deterministic diagnostic's held-out split.
The 24 selected for the live pilot are the **replication** cohort, including
issues it never reached. The other 72 are **confirmation**, never used in the
live pilot or diagnostic replay. All have prior offline use; this is a live
confirmation on constructed requests, not a new natural-workload population.
No selection uses outcome, source length, keyword positions or failure status.

Every issue receives three requested limits (1, 3, 5), two response conditions
(ordinary and two-comment-capped stress), and four arms: **2,304 episodes**.
Run confirmation first, then replication; order confirmation issues by fixed
hash. Each suite/limit uses every arm permutation three times in confirmation
and once in replication. Retain empty/short issues and all adverse outcomes.

Four workers each take one issue and execute its 24 episodes sequentially in
sealed order. Issue blocks may interleave; arm order within every issue is fixed.
This bounds runtime while retaining within-issue sequencing and balanced arm
positions. Cross-issue concurrency can affect provider caching and wall time;
latency/cost are observations under this execution policy, not universal savings.
No adaptive changes to prompts, settings, scheduling or selection are allowed.

A pending checkpoint and $1 reserve precede each episode. Atomic writes happen
without an intervening await, including across workers. A lock prevents duplicate
runners. All prior completed estimates and retained failure reserves, diagnostic
reserve, current completed estimates/reserves, and every in-flight reserve count
against the single $200 cap. Missing usage is never treated as zero billed cost.
This local estimate guard is not a hard provider billing cap.

Continue after isolated episode failures without retrying or replacing them.
Stop launching after five consecutive execution failures in completion order,
a budget guard, or an unrecoverable process error; already pending episodes may
finish. Interrupted/pending or circuit-breaker-stopped checkpoints cannot resume
automatically. Successful completed attempts never rerun. A fully attempted run
makes no more provider calls. All failed and unattempted denominators remain.

Freeze this protocol, configuration, source/runtime/driver hashes, dependencies,
cohorts, complete schedule, prefetch outcomes and previous-attempt budget evidence
before primary calls. Verify before execution and audit all retained rows after.

## Prespecified analysis and conclusion limits

Report confirmation and replication separately, and ordinary and stress
conditions separately. Unit of grouping is the issue, never its six correlated
variants. Report scheduled, attempted, completed, failed, unattempted and correct
counts for every arm, plus accepted dispatches and calls/errors after dispatch.
Determine incomplete accepted prefetches by comparing their released comment
positions with the requested source prefix, without using live answers. For this
structural subset, report scheduled/attempted cases, issue groups, continuation
reads and correct final answers. Retain a list of incorrect answers and source
expectations for inspection. Count final task success only for a completed episode
with a correct answer;
retain any available answer from failed episodes separately in the raw evidence.

Primary contrasts are full against each safeguard ablation on final task success
and total tool calls. Full against baseline is a secondary efficiency contrast.
Report all contrasts regardless of direction. Model requests, tokens, estimated
cost and wall time are additional descriptive outcomes. Count discarded prefetch
reads and all continuation reads. Baseline reads acquire initial evidence and are
not all labeled repairs. Report active-truncation coverage, not just suite labels.

For fully attempted paired cases, report full-only/other-only correctness and
issue groups affected. For each contrast, average its three request-limit
variants within each issue, then compute the mean paired difference and a 95%
percentile bootstrap interval over issues (10,000 draws, seed 20261018). These
intervals are descriptive, unadjusted for multiple contrasts, and assume issue
groups are suitably independent; repository/author dependence remains possible.
Do not report noninferiority, equivalence, power or risk certification. Resource
intervals and overall savings require complete usage and outcomes in both arms.

A correct repair after an ablated prefetch can support recoverability in this
fixed setting; equal accuracy does not establish safety equivalence. Full may
cost more through refusal/discarded work. A null/adverse result must be retained.
The constant statistical gate remains a null mechanism and is not rerun as an
identical extra arm. Hand-specified contracts are not an end-to-end compiler
mining result. This study can resolve the bounded live-repair comparison; it
cannot by itself establish the whole approach across models or workloads, or
justify an ICLR acceptance probability. Source regrading is not independent human
gold attestation. Manuscript integration must preserve these boundaries.

```bash
PYTHONPATH=src python paper/scripts/complete_live_recovery.py prepare
PYTHONPATH=src python paper/scripts/complete_live_recovery.py verify
PYTHONPATH=src python paper/scripts/complete_live_recovery.py run --env-file /absolute/path/to/.env
PYTHONPATH=src python paper/scripts/complete_live_recovery.py analyze
```

The old pilot driver/protocol/seal/checkpoint remain unchanged. Production runtime,
release configuration and existing manuscript artifacts are unaffected.
