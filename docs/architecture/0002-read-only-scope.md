# ADR 0002 — v0.x compiles pre-commit reads only

**Status:** accepted

## Context

The savings ceiling would be higher if writes could be compiled. Many writes are
idempotent, and a retry-safe write is tempting to treat as reversible.

## Decision

Only `PURE`/`READ_LOCAL`/`READ_EXTERNAL` tools declared `speculatable ∧ replayable` may
enter a region. Writes, approvals, unknown effects and handoffs terminate it.
`WRITE_REVERSIBLE` exists in the lattice and is never compilable.

## Why

`stage.reversible()` cannot be attested truthfully in a distributed system: quota counters,
audit rows and permission caches are not all observable. Restricting dispatch to pre-commit
reads makes reversibility *vacuous* — nothing was committed — which is the only version of
the claim that survives review. Idempotence does not help: it makes a retry safe, not a
fallback.

## Consequences

Write-heavy agents get little. The negative-control demonstration exists to show that
outcome being reported rather than worked around. Transactional staged writes with explicit
prepare/validate/commit/compensate are future work, gated on the read-only system
demonstrating value.

## What would reverse this

A deployment that can enumerate its attested counter set and provide a transactional
staging owner — at which point `quota_attested` generalises to a full attestation manifest.
