# Extended held-out cohort for issue-type routing (calibrated model)

**Status: PRE-REGISTERED on 2026-09-24; EXECUTED the same day** (observed results at the end). Before execution no provider call had been made under this
document. It fixes the cohort, arms, endpoints, and decision rule before any spend.

## Why

The pooled one-sided 95% upper bound on compiled-only contract failures across the 90 primary
held-out records is 3.3% (0/90). Issue-type routing is the only primary family with unused
records in the pinned snapshot, so it is the only one whose held-out cohort can be extended
without a new snapshot. A larger cohort tightens the bound and re-tests the retained artifact,
`cand-01-1ebb8b2849c7`, on records it has never seen, on the model it was calibrated for.

## Cohort

120 new held-out records from the pinned snapshot, drawn by the retained study's stable-rank rule
(`_stable_rank(number, seed, "test:<class>")`, seed 20260924) after excluding every record used in
any retained issue-type cohort (discovery, held-out, pilot, natural-live). Class balance is
40 `bug` / 40 `enhancement` / 40 `other`, where `bug` and `enhancement` are exclusive-label classes
as in the retained selection and `other` is the retained oracle's fourth category (expected
`evidence_label = "none"`). The retained cohort was balanced over `bug`, `enhancement`, and
`question`; the snapshot holds only 16 exclusive `question` issues, 10 of them already used, so
`question` cannot be balanced and is replaced by `other`. This is a different class mix from the
retained cohort and is reported as such; the exact oracle is class-agnostic.

## Arms, model, and artifact

`gpt-5.6-luna` (the calibrated model), retained settings. Arms: `baseline`, `compiled` with the
retained registry (`paper/results/github_natural_replication/registry`, artifact
`cand-01-1ebb8b2849c7`, unchanged), and `macro`; balanced six-permutation Latin order by the
retained rule (seed 20260924). One retry per timed-out episode; both attempts retained. No arm
is re-run to change a count.

## Hypotheses (either outcome is reported)

- H-E1: zero compiled-only exact-contract failures on the 120 records.
- H-E2: the compiled artifact dispatches at position 0 on 120/120 records.
- H-E3: the pooled compiled-only bound over 210 records (90 primary + 120) is at most 1.5%
  (0/210 gives 1.42%).

## Decision rule (fixed in advance)

| Observed | Reading |
|---|---|
| H-E1 holds | The pooled bound is reported at 210 records; the primary Table 1 is unchanged (different class mix), and the extension appears in Appendix D with one clause in §5.1. |
| Any compiled-only failure | The record and mechanism are reported ahead of the bound; the bound is recomputed with the observed count. |
| Dispatch below 120/120 | The guard clause is reported; abstentions are clean fallbacks and do not count as failures. |
| Baseline-only failures | Reported as such; they do not count for or against the compiler. |

## Endpoints

Exact contracts per arm and discordant cells against the baseline (exact McNemar); one-sided 95%
Clopper–Pearson bound on the compiled-only rate for the 120 records and pooled with the 90 primary
records; requests, tokens, latency, and cost reductions against the same-model baseline (paired,
10,000-sample bootstrap, seed 20260802); dispatch and fallback reasons.

## Spend and outputs

`--approved-spend-usd 1.00` (expected ≈ $0.12). Driver `paper/scripts/issue_type_extended_heldout.py`
(`preflight`, `run`) writes `paper/results/issue_type_extended_heldout/{preflight,results}.json` and
the generated table `paper/iclr/tables/extended_heldout.tex`; a validator check pins the numbers.

## Claim boundary

One family, one snapshot, the calibrated model, in-distribution records with a disclosed class mix.
It tightens a preservation bound; it does not measure drift, other providers, or other repositories.

## Execution note (2026-09-24, written before any provider call)

The retained registry's compatibility key pins `tracer_version=agent-compaction/0.5.0`; the package
is now 0.6.0, so the retained entry would fall back at dispatch under the current runtime, which is
the manifest-pin barrier working as designed. The driver therefore recompiles the artifact
provider-free from the sealed discovery checkpoint under the current pin and asserts, before any
live call, that the result is the same artifact (id `cand-01-1ebb8b2849c7`, identical program,
splits digest, and 92/0 gate); the preflight records both compatibility keys. Nothing else in the
design changes.

## Observed results (executed 2026-09-24T13:15–14:07Z; `paper/results/issue_type_extended_heldout/results.json`)

360/360 episodes completed, no retries, estimated spend $0.25. Exact contracts: baseline 118/120,
compiled 118/120, macro 117/120. Decision-rule row 2 applies and is reported first: one
compiled-only failure, record 2737 (the compiled arm's excerpt wrapped an error line in backticks
absent from the source); the baseline missed record 3040 (a doubled space) and all three arms
missed record 3968. McNemar $p = 1$. Dispatch 119/120: record 5102 abstained on the induced
verifier's `cardinality` clause and ran the unchanged agent (row 3 of the decision rule; a clean
fallback, and the record passed). Compiled-only bound: 1/120 → 3.9% one-sided 95%; pooled with the
90 primary records 1/210 → 2.2%. H-E1, H-E2, and H-E3 all fail and are reported as such. Reductions
against the same-model baseline: requests 50.0%, tokens 39.5%, latency 42.5%, cost 32.8%. Table:
`paper/iclr/tables/extended_heldout.tex`; paper: Appendix D and one clause in §5.1 and §7.
