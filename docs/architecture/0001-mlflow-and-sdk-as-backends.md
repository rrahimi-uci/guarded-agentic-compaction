# ADR 0001 — MLflow and the Agents SDK are backends, not the IR

**Status:** superseded by [ADR 0010](0010-single-framework-adapter.md) (the IR decision stands; the MLflow adapter was removed)

## Context

Both platforms already trace agent execution. It is tempting to treat an MLflow trace as
the compiler's input representation and skip a schema layer.

## Decision

The compiler has its own typed IR (`schema/traces.py`). MLflow and the SDK are adapters
under `capture/` and `runtime/`, and nothing in `graph/`, `grc/`, `tgws/` or `evaluation/`
imports either.

## Why

* MLflow request/response previews can be **truncated**, and a truncated payload is not a
  provenance source. The IR marks truncation and qualification refuses those episodes.
* Parent/child span structure encodes **containment**, not dataflow or effect order. The
  compiler needs data and effect-order edges, which have to be derived.
* Neither platform can carry the seven application-owned facts (entry state, principal,
  effect class, external-state version, approval scope, outcome, manifest).
* Version coupling: an SDK bump changes `ModelResponse` shapes. Confining that to one
  adapter keeps the conformance-test surface small.

## Consequences

An extra mapping layer, and JSONL is the reproducibility format rather than a vendor
export. In exchange the same code path runs the experiments and a deployment, and the
optional extras are genuinely optional — the test suite skips cleanly without them.

## What would reverse this

A trace platform that carries typed dataflow edges, declared effect classes and untruncated
payloads as first-class, queryable fields.
