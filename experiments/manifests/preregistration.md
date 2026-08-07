# Pre-registration

Frozen before the sealed test split was opened. Anything not listed here is exploratory,
and anything listed here is reported whether or not it passed.

**Substrate.** Four simulated workloads (`demos/`), described in
ADR 0005 (`docs/architecture/0005-simulated-substrate.md`). No result transfers to a
provider or production workload.

## Confirmatory hypotheses

| id | statement | decision rule |
|:---|:---|:---|
| **H1** | automatic synthesis yields at least one non-trivial artifact per eligible demonstration | non-trivial = removes ≥2 model requests **and** contains a synthesized transform or an observation-dependent branch |
| **H2** (co-primary) | accepted optimized episodes are non-inferior on the task score | lower bound of the paired, group-bootstrapped 95% interval on (candidate − baseline) exceeds **−0.05**; sensitivity at −0.03 |
| **H3** (co-primary) | the model-request ratio is below the endpoint | upper bound of the paired ratio-of-means 95% interval is **< 0.90** |
| **H4** | provenance/contract-aware gating has fewer unsafe dispatches than support-only routing at comparable coverage | exact binomial upper bounds on unsafe dispatch, compared at matched coverage |

H2 and H3 are co-primary under an intersection–union rule: **both** must pass. The −0.05
margin is a substantive ceiling and is **not** adjustable for power.

## Secondary and exploratory

* **H3b** (secondary, unthresholded): deployable-cost ratio and p50/p95 latency ratio with
  cache-aware decomposition and intervals.
* **H5** (exploratory): tail latency and variance without an increase in incident rate.
* Prompt/tool-surface reduction is reported as an internal decomposition of condition 3, not
  as a separate confirmatory condition.

## Conditions (four, scored)

1. `baseline` — unchanged workflow.
2. `simple` — hand-written composite tool with concurrent reads, same effect boundary.
3. `full` — TGWS then GRC with provenance, contracts and calibration.
4. `support_only` — same support threshold, no entropy filter, no ambiguity cap, no
   contract challenge, no calibrated gate.

## Data separation

Grouped by scenario (`group_id`), never by span or episode. Fractions: train 0.35, dev 0.20,
calibration 0.20, sealed test 0.25, plus a prospective shadow tail of 0.10 held out first.
Split membership is asserted disjoint and the split manifest digest is published with every
result. The sealed test is executed **once**, after every artifact and every metric
definition is frozen. Shadow evidence is never pooled into the retrospective claim.

## Pre-registered thresholds

| parameter | value |
|:---|:---|
| gate threshold grid Λ | {0.02, 0.05, 0.08, 0.11, 0.14, 0.17, 0.20, 0.25, 0.30, 0.40, 0.50} (\|Λ\| = 11) |
| risk budget α | 0.05 |
| confidence budget δ | 0.10, Bonferroni-split across Λ |
| minimum coverage φ_min | 0.02 |
| quality margin ε_Q | 0.05 (sensitivity 0.03) |
| minimum group support s_min | 5 groups, 3 days |
| branch support floor s_branch | 20 groups |
| permutation test | 400 shuffles, π_max = 0.01 |
| transform depth d | 2 |
| ambiguity cap κ | 3 |
| window bounds | 2–8 tool events, ≥2 interior boundaries |
| bootstrap | 2000 resamples, clustered on `group_id` |

## Declared evaluation budgets

Replay and calibration cost one program execution per window, and TGWS pruning re-runs the
workload per proposal, so the budgets are declared rather than unbounded: ≤400 dev windows
and ≤700 calibration windows per candidate; ≤24 windows per perturbation family; ≤150 dev
episodes per pruning evaluation; ≤400 calibration episodes per route leaf; ≤60 pruning
evaluations per leaf. Every bound is reported with the artifact evidence.

## Exclusions and stopping rules

* Episodes that fail qualification (missing spans, unpaired tool results, truncation,
  missing manifest, missing outcome) are excluded from compilation and reported by reason.
* An undeclared tool blocks the *window*, not the episode.
* A candidate is dropped, and the reason recorded, at the first stage that refuses it. No
  candidate is retried with weakened parameters.
* Calibration stops at `RETIRE` when no grid threshold clears α; the threshold is never
  moved off the grid and α is never relaxed to obtain an artifact.
* A demonstration that fails the eligibility gate remains a reported case study and is not
  silently replaced after seeing outcomes. Demo D is a pre-declared likely negative control.

## Analysis

Paired differences on the same task instances; cluster bootstrap on groups for requests,
tokens, latency and quality; exact Clopper–Pearson intervals for gate failures and critical
safety events; Holm correction across secondary endpoints; Bonferroni across the gate grid.
Median and p95/p99 latency with intervals. Both all-eligible (intention-to-dispatch) and
accepted-only analyses are published, with denominators.

Safety endpoints are **not** averaged into utility. Two are distinguished:
`artifact_write_effects` (the compiled region performing an effect the baseline did not — a
hard gate, must be zero) and downstream `safety_events` (the host agent's own later writes,
reported with the mechanism).
