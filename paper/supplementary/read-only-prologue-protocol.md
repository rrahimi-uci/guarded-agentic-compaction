# Read-only prologue protocol (relaxing the position invariant)

**Status: DESIGN ONLY, written 2026-09-22. Not implemented, not run.** Appendix G names a bounded
read-only prologue as a conjecture with a mechanism; this document fixes the acceptance tests any
implementation would have to pass before the paper could claim it.

## The limitation

The position invariant a = 0 (Eq. 2) refuses dispatch on 4,679 of 4,680 AppWorld ReAct and
plan-and-execute trajectories because those architectures open by reading API documentation, so
the hot prefix is no longer at position 0. The runtime enforces the invariant as "no tool
observation has been committed in this episode".

## The extension

Permit an allowlisted, deterministic, read-only *prologue* before the compiled prefix under an
extended entry contract. The adapter must recognize the prologue's exact calls and results as
already issued, prove them effect-admissible against the signed catalog, bind their results as
explicit live-ins of the compiled region, and suppress their replay. This is replay suppression
under an extended entry contract, not arbitrary mid-trace entry; the compiled region and its
statistical argument are unchanged.

## Acceptance tests (all must pass before any evaluation)

1. A prologue mismatch, an extra call, an order change, a manifest mismatch, or an unknown effect
   in the prologue returns the unchanged baseline agent.
2. No call already committed by the host is replayed; the compiled region's call count is
   unchanged.
3. The compiled region's provenance is recomputed with the prologue outputs treated as explicit
   live-ins; any slot that becomes ungrounded or ambiguous retires the region.
4. The archived suffix-dispatch pilot (`paper/results/github_live/pilot_2026-08-03/`, reordered
   and duplicated calls) is included as a regression test and must return the baseline.
5. AppWorld structural eligibility (`paper/scripts/appworld_dispatch_preflight.py`) is recomputed
   per architecture with the same prologue definition the runtime uses; the paper reports the
   before/after eligibility per architecture and never pools them.

## What it would license

A dispatchability result per architecture on the released AppWorld runs, still provider-free and
still descriptive (trajectories repeat tasks across runs). It would not license an efficiency or
quality claim and would not change any GitHub result, whose agents already start at position 0.

## Implementation and observed results (2026-09-24)

**Status update: IMPLEMENTED and MEASURED, provider-free.** The runtime admits an exact,
allowlisted, read-only prologue (`runtime/prologue.py`, `match_prologue`; `Artifact.prologue`,
`ManualPreModelPlan.prologue`; committed-call records derived from native history in the SDK
adapter and from `ctx.observations` in the runner). Acceptance tests 1–4 pass
(`tests/unit/test_dispatch_prologue.py`, 23 tests; full suite 496 passed), including the archived
suffix-dispatch pilot as a regression test (every prefix of every archived reordered or duplicated
sequence returns the baseline). Acceptance test 3 is covered on the runtime side (every region
slot, predicate, and live-out must resolve to `z`, a declared prologue variable, or an earlier
region variable, else the region retires at that boundary); compile-time re-mining with prologue
outputs as pseudo-producers is not implemented, so prologue-bearing artifacts must be authored.

Acceptance test 5 ran on the released AppWorld baseline trajectories (`appworld download
experiment-outputs`, package 0.1.3.post1, data 0.1.0; `paper/scripts/appworld_dispatch_prologue_preflight.py`,
output `paper/results/external_benchmarks/appworld_dispatch_prologue_preflight.json`). The
BEFORE rule reproduces the retained per-architecture counts exactly. With the prologue
`GET /api_docs/api_descriptions app_name=supervisor` (the runtime's exact-match rule), AFTER is:
full code 2,339/2,340 (unchanged), iterative parallel function calling 762/1,170 (unchanged),
plan-and-execute 1/2,340 (unchanged), ReAct 2/2,340 (from 0). The looser diagnostics recover 2
(ReAct) and 3 (plan-and-execute) under "any documentation-only prefix then the program"; the
admitted program occurs anywhere in only 16 and 39 of those trajectories. Reading: the position
invariant was the proximate reason those architectures were refused, but they do not execute the
admitted region at all, so no prologue rule dispatches it; the paper's Appendix G replaces the
conjecture with this measurement. The prologue tool `api_docs.show_api_descriptions` is
undeclared in the signed catalog; AFTER assumes the declaration recorded under `assumptions`
in the output JSON, which a reviewer would have to sign before any dispatch.
