# Multiplicity-repair protocol: fresh calibration cohorts for PR-outcome and backlog-attention

**Status: PRE-REGISTERED on 2026-09-22. Not run.** No provider call has been made under this
document. It fixes the design, candidates, sample size, decision rule, and claim boundary before
any spend is authorized, so that whichever way the experiment comes out it is reported as a
result. It changes no compiler code path used by the retained studies.

## The gap this closes

Proposition 1 covers one candidate fixed before calibration. In the retained PR-outcome and
backlog-attention studies two candidates (a three-read program and its two-read prefix) both
reached calibration on the same 92 groups; the higher-removal survivor was kept by dominance.
Conditional on train and development data the number of candidates that reached calibration is
therefore m = 2, and the candidate-wide budget γ = δ/(m|Λ|) = 0.1/22 gives U = 0.0569 > 0.05 at
n = 92 with zero violations (`paper/results/iclr_revision/multiplicity_accounting.json`). Those two
artifacts carry per-candidate certificates at α = 0.05 and a compiler-wide certificate only at
α ≥ 0.057. Issue-type routing needs no repair: its second candidate retired at synthesis and
never saw calibration (m = 1).

## Hypothesis

H-MR: with both mined candidates frozen exactly as retained (program, guard, verifier, score
model, grid) and the confidence budget divided over m = 2 candidates and |Λ| = 11 thresholds, a
fresh class-balanced cohort of 106 calibration groups per family yields zero violations for the
admitted candidate, so U ≤ 0.0496 ≤ α and the existing artifacts obtain a compiler-wide
certificate at α = 0.05.

## Fixed design

| Item | Value |
|---|---|
| Families | `pr_outcome`, `backlog_attention` |
| Frozen candidates | PR-outcome: `cand-00-a1de3856bb6c` and its dominated two-read sibling; backlog: `cand-00-99f1b041ed7c` and its dominated two-read sibling. Registries: `paper/results/github_workflow_families/{pr_outcome,backlog_attention}/final/registry/registry.json` (dominated siblings recompiled provider-free from the sealed discovery checkpoints with the identical `GrcConfig`, seed 20260805) |
| Budgets | α = 0.05, δ = 0.10, Λ = {0.02, 0.05, 0.08, 0.11, 0.14, 0.17, 0.20, 0.25, 0.30, 0.40, 0.50}, m = 2, so γ = δ/22 |
| Sample size | n = 106 calibration groups per family, fixed here; never extended or reduced after any label is seen |
| Cohort draw | class-balanced 36/35/35 by the same round-robin rule as `select_cases` in `paper/scripts/github_workflow_family_study.py`; seed 20260922; every record already used in any retained PR-outcome or backlog cohort (discovery, held-out, pilot, headroom rerun) is excluded first |
| Go/no-go at preflight | proceed only if every class has ≥ 36 unused eligible records in the pinned snapshot; otherwise record NO-GO and keep the per-candidate wording |
| Discovery arm | the unchanged agent, same prompt, tools, model settings (`gpt-5.6-luna`, reasoning `low`, verbosity `low`, `parallel_tool_calls=False`, `store=False`), `max_turns=8`, 120 s timeout; **one retry per timed-out episode, both attempts retained** |
| Violation label | the replay-contract label `calibrate_gate` consumes today, computed provider-free from the reconstructed discovery traces and the pinned parquet |
| Spend ceiling | `--approved-spend-usd 0.50` per family (expected ≈ $0.09 per family) |
| Outputs | `paper/results/multiplicity_repair/<family>/{preflight.json, discovery_checkpoint.json, results.json}` with the full per-threshold table for both candidates; generated `paper/iclr/tables/multiplicity_repair.tex`; a validator check pinning the numbers |

## Implementation (to be written)

`paper/scripts/multiplicity_repair_study.py` with `--family`, `--preflight-only`, and
`--approved-spend-usd`; a `candidate_multiplicity: int = 1` keyword on
`guarded_agentic_compaction.grc.calibrate.calibrate_gate` (`conf = 1 - delta / (m * len(grid))`),
unit-tested; a recalibration mode that loads the frozen artifacts from the registries and calls
`calibrate_gate` on the new groups without re-mining or re-synthesizing anything.

## Decision rule (fixed in advance)

1. Both candidates zero violations on 106 groups → compiler-wide certificate at α = 0.05 for the
   dominance-selected artifact; the manuscript switches to the Track A wording in
   `improve-iclr.md` §5 (abstract, §3, §5.1, §7, Appendix A, Appendix C).
2. Any violation → report the corrected U; if U > α the compiler-wide claim is not made for that
   family, the Track B wording stays, and the violating record and mechanism are described in full.
3. NO-GO at preflight → Track B wording stays; the NO-GO and pool counts are reported.
4. α, δ, Λ, m, n, and the candidate set are never changed after the run.

## Claim boundary

Success licenses one statement: that the admitted PR-outcome and backlog artifacts satisfy the
registered bound under a budget corrected over every candidate that reached calibration, on a
fresh cohort from the same pinned snapshot. It says nothing about drift, other providers, other
repositories, or the ranking quality of q, and it remains conditional on i.i.d. calibration groups.
