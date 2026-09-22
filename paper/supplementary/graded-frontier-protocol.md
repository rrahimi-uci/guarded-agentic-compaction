# Graded risk–coverage frontier protocol

**Status: DESIGN ONLY, written 2026-09-22. Not scheduled, not run.** This document fixes the
arithmetic precondition and the design that would let the learned score `q` be tested for graded
selectivity, which no cohort in the paper can do. It is cited from Appendix H as the protocol that
could answer the question the prospective gate-frontier study could not.

## Why the executed studies could not answer the question

At α = 0.05, δ = 0.10, |Λ| = 11 and zero violations, admission requires n_η ≥ 92 accepted groups.
Every retained calibration pool has |K| = 92, so the only certifiable coverages are 0 and 1; the
pre-registered criterion of "three distinct admissible nonzero coverage levels" in
`prospective-gate-frontier-protocol.md` was unattainable at that pool size whatever `q` ranked.
Two intermediate coverages were observed and neither is certifiable (`huggingface/datasets`
10/92 with U = 0.375; balanced `pandas-dev/pandas` 90/92 with U = 0.0509). In addition, on the
PR-outcome task the entry state is a single record number, so every entry-observable feature of
`q` is a function of that integer and held-out `q` is constant within a repository.

## Preconditions

| Target certifiable coverage c | Minimum pool ⌈92/c⌉ |
|---|---|
| 1.0 | 92 |
| 0.8 | 115 |
| 0.7 | 132 |
| 0.5 | 184 |
| 0.25 | 368 |

1. Calibration pool of at least **184 groups per repository** (certifies c = 0.5), sampled before
   filtering on recurrence, with violation labels defined for every dispatch-eligible member.
2. An entry state with informative features: at minimum record age, discussion length, and label
   ambiguity at the entry boundary, plus the Markdown-link stratification the pilot identified
   (`gate-frontier-pilot-protocol.md`), so that `q` is not constant by construction.
3. At least three target coverage levels chosen from the table above and declared before any
   label is read; the frozen grid Λ and budgets α, δ unchanged from the registered setting.
4. Frozen candidate selection (Corollary 2) so the admitted gate carries a compiler-wide
   certificate.

## Arms and decision rule

Three arms as in the prospective protocol: unchanged agent, learned gate, support-only gate
(α = 1, identical otherwise). Predicted positive outcome: the learned gate certifies at least
three distinct nonzero coverages with wrong-dispatch at or below the bound at each and dominates
the support-only gate at matched coverage. Negative for `q` specifically: at |K| ≥ 184 the learned
gate still admits only at full coverage while intermediate coverages are certifiable. Adverse: any
held-out wrong dispatch on either gate, reported first. Null: neither gate produces graded coverage
even though the pool permits it — reported as a null about `q` and the workload, which is the
reading the executed study could not license.

## Cost estimate

Roughly three times the executed gate-frontier study (≈ 3 × $0.41 for discovery and held-out
episodes at the retained per-episode costs), plus the engineering of an informative entry schema.
