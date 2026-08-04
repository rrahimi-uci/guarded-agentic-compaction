# ADR 0009 — select measured actions; do not infer an optimization portfolio

**Status:** accepted, 2026-08-03

## Context

The compiler can decide whether one recurrent region clears its own evidence gate. It
cannot decide whether compilation is better than a hand-written macro, cache, prompt
rewrite, model route, or unchanged agent without measuring those alternatives. The GitHub
replication demonstrates the distinction: partial GRC and the macro both preserve 30/30
registered contracts, while the macro uses fewer tools, tokens, and estimated dollars.

## Decision

Portfolio selection is a separate framework-neutral layer over paired group observations.
For each action it:

1. averages repeated executions inside the independent `group_id`;
2. requires every positively weighted cost/latency/token/tool objective;
3. bounds candidate task failure and non-positive utility separately with one-sided exact
   Clopper–Pearson bounds;
4. splits the confidence error budget across endpoints and measured actions;
5. rejects insufficient support or compatibility drift; and
6. selects the highest mean utility among admitted actions, otherwise baseline.

Macros default to `human_review`. Runtime permission fails closed on abstention, manifest
drift, or missing review approval. Missing cache or other action measurements create no
candidate and cannot be imputed.

## Consequences

The selector can recommend an externally supplied measured macro but does not synthesize
or deploy its code. Its weighted utility is operator policy, not a universal objective.
The 30-group calibration and 12-pair prospective pilot validate the mechanism on one
workflow family; they do not show value over an always-macro policy or generalize across
domains.

## What would reverse this

A different selector may replace the current rule only with sealed comparisons showing
better quality-risk, regret, and selection performance across workflow families with
different optimal actions. It must preserve group independence, compatibility invalidation,
baseline abstention, and application-owned review.
