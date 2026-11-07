# Rebuttal placeholders and outcome sentences (Strategy B)

Companion to [`review_response_2026-11-06.md`](review_response_2026-11-06.md). Every
`{{B.*}}` token in the response stands for a result of the multi-repository
unfiltered end-to-end study registered in
`paper/supplementary/multirepo-unfiltered-end-to-end-protocol.md` (committed on
`paper/iclr-rebuttal-base`, 2026-11-07 registration). Fill them only from
`paper/results/multirepo_end_to_end/summary.json` after the validator family
`multirepo_end_to_end` passes, and copy each value into `number_registry.md`.
No value below has been observed; nothing here is a result.

## Token definitions

Repository keys use `<owner>__<repo>`, the directory naming of
`paper/results/datasets/github_time_forward/`. The decision tokens use the same key
(`{{B.decision.huggingface__datasets}}`, not `{{B.decision.datasets}}`), plus
`{{B.decision.pooled}}` for the pooled row.

| Token | Meaning | Format |
|---|---|---|
| `{{B.<key>.n}}` | Calibration groups in the denominator for that repository: author-distinct, guard-eligible groups (clean abstentions included with loss 0; guard-ineligible groups excluded and reported separately). Realised n = min(200, available); a repository with fewer than 106 available does not run. | integer, e.g. `200` |
| `{{B.<key>.k}}` | Violations: groups where the compiled arm dispatched and the final task contract was missed (timed-out episodes count as misses; no retries). | integer |
| `{{B.<key>.U}}` | One-sided upper bound on the end-to-end violation rate, registered grid (alpha = 0.05, delta = 0.10, \|Lambda\| = 11, m = 1), exact `cp_upper` at the realised n. | four decimals, e.g. `0.0232` |
| `{{B.decision.<key>}}` | Pre-registered decision for that repository. | one of the strings in the next table |
| `{{B.pooled.n}}`, `{{B.pooled.k}}`, `{{B.pooled.U}}` | The pre-declared pooled estimand over all *admitting* repositories (protocol, "Pooled"), registered grid, m = 1. | as above |
| `{{B.decision.pooled}}` | Decision for the pooled estimand. | `admit` or `retire` or `not computed` |

Keys used in the response: `huggingface__datasets`, `pandas-dev__pandas`,
`streamlit__streamlit`, `psf__requests`, `pytorch__pytorch`, `pooled`.

Allowed decision strings:

| String | When | n, k, U cells |
|---|---|---|
| `admit` | k at or below the registered floor (k <= 3 at n = 200; recompute for the realised n) | values |
| `retire (k above floor)` | k above the floor | values; describe the violating records in the appendix |
| `retire at compile` | discovery produced no admissible artifact | `-` in n, k, U |
| `not run (n < 106)` | fewer than 106 author-distinct calibration groups available | write the available count in n, `-` in k, U |
| `not run (acquisition failed)` | snapshot not acquired (plan Section 12) | `-` |

## Where each token appears

| Location in the response | Tokens |
|---|---|
| Global summary, table row 2 | `{{B.pooled.k}}`, `{{B.pooled.n}}`, `{{B.pooled.U}}` |
| Reviewer 1 Part 1, W4 Evidence | pooled k, n, U |
| Reviewer 2 Part 2, Q2 Evidence | pooled k, n, U |
| Reviewer 3 Part 2, Q1 table | all per-repository tokens, pooled tokens, `{{B.decision.*}}` |

## Outcome sentences

The posted text is written to stay true under every outcome: it reports n, k, U and
the decision, states the rule fixed in advance, and never says "admits". After the
numbers are known, the author may add the matching sentence below. Replace `<...>`
by hand. Do not change the rule, the grid or n after seeing results (plan Section 12).

### Global summary, table row 2

- Placeholder text as written (any outcome): "pooled k = {{B.pooled.k}} of n = {{B.pooled.n}}, U = {{B.pooled.U}}".
- All run repositories admit: append "; admitted in <N> of <M> repositories under the rule fixed in advance".
- Mixed: append "; admitted in <N> of <M> repositories, retired in <list>".
- No repository admits (pooled estimand not computed): replace the numbers with "admission in none of <M> repositories; k and U per repository in the appendix".
- Only huggingface/datasets ran (minimal viable B): replace with "huggingface/datasets only: k = {{B.huggingface__datasets.k}} of n = {{B.huggingface__datasets.n}}, U = {{B.huggingface__datasets.U}}".

### Reviewer 1 W4 and Reviewer 2 Q2 (Evidence lines)

- Admit (pooled): no change; optionally add "below the 0.05 target" after the U value.
- Some repositories retire: add "; <list> retired under the pre-registered rule and are reported first in the appendix".
- None admit: replace the pooled clause with "multi-repository study: no repository admitted (k above the floor in <list>); the observed end-to-end violation rates are the first unfiltered estimates for this family".
- Shortfall: add "; <repository> had <available> author-distinct groups, below the 106 required, and did not run".

### Reviewer 1 W5 (Answer, last sentence)

- Any outcome: keep "The repair you suggest was run: ...". It is true whether the
  study admits or retires, because the repair is the sampling design, not the result.
- Retire: add to Still open "Under the unfiltered design the artifact retired in <list>, so no unfiltered bound is claimed there."

### Reviewer 3 Q1 (Answer)

- Admit in at least one repository: add after the table "Under the rule fixed in advance, <list> admit with author units and m = 1; these are selection-wide end-to-end bounds for one frozen artifact per repository."
- None admit: replace "The multi-repository study extends this ..." by "The multi-repository study tested this with ... (table); no repository met the rule, so the post-cutoff cohort remains the only one with a selection-wide 5% bound, and the abstract says so."
- Shortfall or acquisition failure: footnote the row: "<repository> did not run: <reason>, recorded in a dated protocol amendment before any of its results."
- pytorch/pytorch retiring at compile (expected from both earlier studies) is a refusal result; no sentence change is needed beyond the decision cell.

### Optional Strategy C (only if `fresh-issue-gate-single-look-protocol.md` ran)

- Reviewer 3 Q2, before "The paper now claims no learned selectivity": "A single-look calibration on <n> fresh issues under the frozen v2 gate <admitted at η = 0.50 with k = <k> | retired>; this is one certified level at most and does not change the answer."

## Numbering to recheck after the integrator's build

The response uses the numbering of the 2026-11-06 build of `paper/iclr/build/main.pdf`
(60 pages, SHA-256 `58394f0fae9e58b08335595bd8e303ad8617abe0026d64c2581ae00621312bf4`).
The compiler-decisions table (W2) and the move of `tab:evidence-scope` to the
appendix (W3) will shift table numbers. Recheck each against the final build.

| Response text | LaTeX label | Reviewed version |
|---|---|---|
| Table 1 | `tab:primary` | Table 1 |
| Table 2 (AWM) | `tab:awm` | none |
| Table 3 (two trace benchmarks) | `tab:funnel` | Table 2 |
| Table 6 (certificate level) | `tab:multiplicity-accounting` | Table 4 |
| Table 14 (hand-written comparator) | `tab:manual-resources` | Table 9 |
| Table 16 (primary benchmark at a glance) | `tab:benchmark-glance` | Table 11 |
| Table 19 (all four trace benchmarks) | `tab:funnel-all` | none |
| Table 27 (every admitted artifact's certificate) | `tab:certificates` | none |
| Table 29 (grouping units) | `tab:effective-units` | Table 17 |
| Table 31 (recurrence-only replay) | `tab:recurrence-only` | Table 19 |
| Table 36 (gate-frontier disaggregated) | `tab:gate-frontier-disaggregated` | Table 23 |
| Figure 3 (coverage floor) | `fig:gate-floor` | Figure 4 |
| App. C "Calibration labels as computed" | inside `app:config` | none |
| App. D "Implemented lifecycle controls ..." | `app:lifecycle` | none |
| App. E "Primary workflow families" | inside `app:detail` | App. E |
| App. F.3, F.4, F.5 | `app:external`, `app:prefix-census`, `app:bird` | F.3 only (different content) |
| App. G "Scope of automated ...", "Calibration population audit" | `app:limits`, `app:population-audit` | none |
| App. H, H.1 | `app:prospective`, `app:gate-extension` | H (protocol only) |
| App. I, J, K, L | `app:live-recovery`, `app:matched-reuse`, `app:generalization-gate`, `app:adaptive-gates` | none |
| New appendix "Unfiltered end-to-end calibration across repositories" | to be created by the integrator (plan task 1.10) | none |

## Character counts of the posted blocks (before filling)

Counted on 2026-11-06 with placeholders unfilled; filled values are shorter than
their tokens, so counts can only fall. Limit used: 4,500 characters per block.

| Block | Characters |
|---|---:|
| Global summary | 3,150 |
| Reviewer 1, Part 1 | 4,481 |
| Reviewer 1, Part 2 | 4,466 |
| Reviewer 2, Part 1 | 2,992 |
| Reviewer 2, Part 2 | 3,755 |
| Reviewer 3, Part 1 | 2,172 |
| Reviewer 3, Part 2 | 2,987 |
