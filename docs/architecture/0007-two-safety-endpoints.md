# ADR 0007 — two safety endpoints, not one

**Status:** accepted

## Context

Compaction in v0.x touches no write. It is tempting to conclude that safety endpoints are
trivially invariant and to report a single "safety events" count.

Measurement said otherwise. On the support demonstration the *baseline* sometimes skipped
fetching invoices by accident and therefore could not issue a refund. Making evidence
gathering deterministic removed that accident, so the host agent's own downstream refund
fired slightly more often — 44 → 47 events for the hand-written comparator, 44 → 44 for the
compiled region. Nothing in the compiled region wrote anything.

## Decision

Two separate endpoints, never averaged together:

* `artifact_write_effects` — the compiled region performing an effect the baseline did not.
  A **hard gate**: must be zero, and the facade, the verifier and staging each independently
  prevent it.
* `safety_events` — the *host agent's* own later writes. **Reported with its mechanism**, and
  flagged when it increases, but not treated as a compiler regression.

## Why

Conflating them fails in both directions. One count that includes downstream shifts fails a
candidate for something it did not do; one count that excludes them hides a real operational
change a reviewer needs to see. The distinction is only visible once the workload is actually
executed under both conditions, which is why it does not appear in the specifications.

## Consequences

Reports carry both columns and the mechanism in prose. A candidate can pass the safety gate
and still be flagged for review.

## What would reverse this

A workload where the downstream shift is caused by the artifact's *outputs* rather than by
their completeness — at which point it belongs in the verifier's live-out contract instead.
