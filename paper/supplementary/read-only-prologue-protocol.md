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
