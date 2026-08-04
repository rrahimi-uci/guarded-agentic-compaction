# ADR 0004 — exact corrected calibration, and `RETIRE` as a normal output

**Status:** accepted

## Context

The gate needs a risk statement. A point estimate of the violation rate is easy and
worthless at these sample sizes.

## Decision

A pre-registered grid of 11 thresholds, a one-sided Clopper–Pearson upper bound at
`1 − δ/|Λ|`, selection of the highest-coverage admissible threshold, and `RETIRE` when none
qualifies. The unit of independence is the calibration **group**, not the episode.

## Why

With ~60 groups the bound demands *zero* observed violations; anything weaker would be a
false guarantee. Reporting the attainable bound — and the group count required to reach the
target — is more useful than a threshold that cannot be justified. The estimator computes
that count (≈92 at α = 0.05, δ = 0.10, |Λ| = 11) before any compilation, so the constraint
surfaces at Gate 1 rather than Gate 3.

## Consequences

Most candidates retire on small corpora, which the measured results show: 7 of 7 on the
negative control, 15 of 40 on the RAG demonstration. Two further requirements fell out of
implementation: the fitted feature extractor must travel *inside* the artifact so the
runtime computes identical features, and feature semantics must follow the hull kind or the
score saturates.

## What would reverse this

A defensible distribution-free bound with better small-sample behaviour under the same
exchangeability assumptions.
