# ADR 0005 — demonstrations run on a simulated substrate

**Status:** superseded for user-facing demos by [ADR 0008](0008-live-provider-demos.md);
retained for offline stress and calibration tests

## Context

Measuring a request ratio, a paired non-inferiority interval and a calibrated risk bound
needs thousands of paired episodes with ground-truth outcomes and a resettable world.
Neither a provider API nor a production deployment provides that reproducibly, and
proposal §6.3 is explicit that production cannot be replayed.

## Decision

Four offline simulated workloads: a deterministic tool world plus a scripted policy standing in for
the model at each request boundary. Every artifact, table and figure produced from them is
labelled `substrate=simulated`, and the run manifest repeats the warning.

## Why

Everything downstream of the trace envelope — provenance, mining, synthesis, contracts,
calibration, dispatch, statistics — is the real implementation running on real traces of
that workload. What the simulator replaces is the *model's* decision function, which is
exactly the component the compiler treats as opaque.

The policies carry declared deviation rates, alternative paths, merged-account and empty
result shapes, paginated feeds, out-of-enum values and drifting arms, because a substrate
without variance cannot falsify a gate.

## Consequences

No result here transfers to a provider or a production workload, and two modelling
assumptions are declared rather than hidden: the tool-surface `selection_noise` scaling, and
the cost model's cache-hit fraction. One further requirement fell out of implementation: the
policy needs its own RNG stream, or removing a request re-rolls every later deviation and
paired statistics measure the plumbing.

## What would reverse this

Access to a traced production workload with outcome labels and a staging environment — at
which point the same code runs unchanged and the substrate label changes.
