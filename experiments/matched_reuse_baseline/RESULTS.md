# Matched workflow-memory comparison: retained results

This is an API-task adaptation of offline AWM, not a native browser-benchmark reproduction.

The primary contrast is GAC minus adapted AWM; comparisons with baseline are secondary.

Attempted 378/378 evaluation episodes; 377 completed. Halt reason: none. The frozen checkpoint audit passed.

## Pilot cohort

| Arm | Seven-field correct / scheduled | Four-field factuality | Failed / unattempted | Requests / attempted | Tool calls / attempted | Observed model USD / 1,000 attempted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AWM adapted | 6/6 | 6 | 0 / 0 | 4.000 | 3.000 | 0.874 |
| Baseline | 6/6 | 6 | 0 / 0 | 4.000 | 3.000 | 0.867 |
| GAC | 6/6 | 6 | 0 / 0 | 2.000 | 3.000 | 0.578 |

Resource columns report observed usage per attempted episode. Missing usage is not zero cost; failure reserves and accounting-completeness flags are retained in the JSON. All scheduled episodes remain in accuracy denominators.

| Paired contrast | Accuracy difference, percentage points [descriptive 95% bootstrap] | A-only / B-only correct | Exact McNemar p | Holm p |
| --- | ---: | ---: | ---: | ---: |
| awm_offline_adapted-minus-baseline | 0.00 [0.00, 0.00] | 0 / 0 | 1.0000 | 1.0000 |
| gac-minus-awm_offline_adapted | 0.00 [0.00, 0.00] | 0 / 0 | 1.0000 | 1.0000 |
| gac-minus-baseline | 0.00 [0.00, 0.00] | 0 / 0 | 1.0000 | 1.0000 |

Intervals resample paired issues, not arm episodes. Holm adjustment covers the three accuracy contrasts within this cohort; other intervals are descriptive. Exact marginal accuracy intervals are in the JSON. A zero-width paired bootstrap at the boundary does not establish equality or noninferiority.

## Primary cohort

| Arm | Seven-field correct / scheduled | Four-field factuality | Failed / unattempted | Requests / attempted | Tool calls / attempted | Observed model USD / 1,000 attempted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AWM adapted | 114/120 | 117 | 0 / 0 | 4.000 | 3.000 | 0.902 |
| Baseline | 114/120 | 117 | 0 / 0 | 4.000 | 3.000 | 0.892 |
| GAC | 116/120 | 119 | 1 / 0 | 2.000 | 3.000 | 0.624 |

Resource columns report observed usage per attempted episode. Missing usage is not zero cost; failure reserves and accounting-completeness flags are retained in the JSON. All scheduled episodes remain in accuracy denominators.

| Paired contrast | Accuracy difference, percentage points [descriptive 95% bootstrap] | A-only / B-only correct | Exact McNemar p | Holm p |
| --- | ---: | ---: | ---: | ---: |
| awm_offline_adapted-minus-baseline | 0.00 [-3.33, 3.33] | 2 / 2 | 1.0000 | 1.0000 |
| gac-minus-awm_offline_adapted | 1.67 [0.00, 4.17] | 2 / 0 | 0.5000 | 1.0000 |
| gac-minus-baseline | 1.67 [0.00, 4.17] | 2 / 0 | 0.5000 | 1.0000 |

Intervals resample paired issues, not arm episodes. Holm adjustment covers the three accuracy contrasts within this cohort; other intervals are descriptive. Exact marginal accuracy intervals are in the JSON. A zero-width paired bootstrap at the boundary does not establish equality or noninferiority.

## Cost and scope

The observed accuracy advantage is not established statistically (primary exact McNemar p=0.50, Holm p=1.00). A post-run source audit found one structurally unanswerable excerpt task (issue 377); all three arms failed it and it remains in every primary denominator. See [ERROR_AUDIT.md](ERROR_AUDIT.md) for this limitation and strict-label errors.

New known study cost, including pilot and induction: $0.30665104.

New induction estimated cost: $0.00256740; amortized per primary task: $0.00002140. Induction elapsed time: 4.745 seconds.

GAC reconstruction preflight elapsed time: 0.646 seconds, including source loading and compatibility checks; this is not a priced compiler-only time.

The historical acquisition of the shared 132-trace discovery pool is a sunk, shared cost. AWM uses the same 130 compiler-eligible traces; GAC retains its historical train/development/calibration split. The comparison does not price total lifetime development or historical optimization effort.

Aggregate estimates and retained reserves: $8.57705193 against the $400 authorized cap. This includes $7.27040089 carried forward. This is not a provider billing cap.

One model, one workflow, one historical snapshot, one induction output and one stochastic evaluation per arm/issue limit generalization. Memory placement and compiled execution differ by design; this is a whole-system comparison. No new risk certificate, isolated gate benefit, broad runtime dominance, equivalence or acceptance probability is established.
