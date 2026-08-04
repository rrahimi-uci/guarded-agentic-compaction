# ADR 0006 — partition the corpus before fitting, not after

**Status:** accepted

## Context

Tenant, principal and policy version are exact guard keys. The published API pinned them in
the guard *after* fitting, which lets a single family draw support across an isolation
boundary and then discover the conflict at contract induction.

## Decision

`partition_by` partitions the corpus. `compile_grc` and `compile_tgws` recurse per partition
and merge only the resulting artifact lists; an artifact whose isolation key would contain
several values is a compile-time error, not something to average over.

## Why

§7.4 forbids pooling behavioural evidence across authorization scopes outright. Detecting it
afterwards is strictly worse: the route tree and the bindings have already been fitted on
pooled data, and "reject the leaf" throws away the correct per-partition artifact along with
the invalid pooled one. The RAG demonstration shows the difference — pooled fitting produced
one artifact with a four-role isolation key; partitioned fitting produced four valid
per-role artifacts.

## Consequences

Support divides by the number of partitions, and calibration is usually what breaks first.
That is the mechanism behind the negative control, and it is reported as an economic result
rather than hidden by a coarser key.

## What would reverse this

Nothing about the safety rule. The *shape* could change — a shared program with
per-partition guards and per-partition calibration would reduce duplication without pooling
evidence.
