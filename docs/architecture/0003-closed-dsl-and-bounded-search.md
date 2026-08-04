# ADR 0003 — a closed library and value-directed bounded search

**Status:** accepted

## Context

Argument reconstruction is program synthesis. Unrestricted search would cover more slots
and make the safety argument unfalsifiable.

## Decision

A closed, versioned library of 23 operator forms (`LIBRARY_VERSION = "T-v1"`), maximum
composition depth 2, constants drawn only from literals observed in supporting traces plus
`{0, 1, -1, ""}`. Search is a *value-directed* breadth-first walk from the concrete source
value, not an enumeration of `|T|^d` expressions.

## Why

* Auditability: every accepted expression prints as one readable line.
* Two-sided cost: every operator added widens the *spurious-match* surface of provenance as
  well as coverage, so growth is not free.
* Value-directed search prunes by runtime type for free and collapses observationally
  equivalent chains, which is what makes depth 2 affordable.

Two corrections were needed and are recorded in [spec-review](../spec-review.md): MDL alone
prefers `last` over `filter(status == "active")`, so an order-stability rank sits ahead of
MDL; and denotation-based frontier pruning deletes the correct chain when two operators
agree on one trace, so the frontier keeps the most stable representative and enumerates
from several traces.

## Consequences

Slots hit `⊥` often — regex extraction, arithmetic across fields and unit conversion are
out of reach. That yield loss is accepted.

## What would reverse this

Evidence that a specific missing operator family blocks a large share of otherwise-eligible
regions *and* that adding it does not measurably increase provenance false positives.
