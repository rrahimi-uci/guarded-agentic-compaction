# Adaptive compiler follow-up: what is now established

This is a provider-free development validation, not a confirmatory experiment.
The [implementation and reproduction instructions](../../../experiments/adaptive_prefix_validation/README.md)
identify the separate code and evidence. It introduces no new paid requests and
does not change the manuscript's quantitative results or the old pilot scores.

## Comparator execution

All **36/36** selected pilot SQL programs agree between the corrected bridge and
the reference harness under identical tool responses. Both use the unmodified
pinned upstream executor. There are **33 successful executions and three program
errors**; these are execution statuses, not answer-correctness scores. The three
errors are retained: a string used as a dictionary, a missing `re` import, and
`replace` called on `None`. No program is removed because it fails.

The validation performs read-only SQL against the pinned databases and checks
database hashes before and after. One runtime inference uses a retained response
fixture; none is missing. This demonstrates adapter parity on these programs,
not independent executor correctness, fresh inference equivalence, or native
Agent JIT browser reproduction. The historical 4/36 Agent JIT answer score remains
an exploratory result from the old adapter and must not become a method-ranking
claim. See [all per-program results](executor_sql_validation.json).

## GAC candidate boundary

The original two-call prefix remains rejected because adaptive table selection
does not have a consistent grounded expression. A separately recorded posthoc
development change permits one saved request instead of two and fixes the window
length at one. It preserves the original tool payload representation.

The resulting `list_tables()` program has **27 training support groups** and
passes **9/9 development recorded replays**. All 36 baseline traces enter the
conversion, including **10 incorrect final answers**. Compiler qualification and
blocked windows remain reported separately. There are **zero calibration groups
and zero emitted artifacts**. The candidate's final disposition is
`no_calibration_groups`; it has no deployment certificate.

Its induced verifier accepts the exact table-list payloads observed in the nine
training databases. It does not establish generalization to new databases or
schema changes. No sandbox perturbation suite or final continuation was evaluated
in this candidate analysis. The compiler's internal gate-development samples are
not new calibration observations. The [frozen candidate record](candidate.json)
contains the program, guard, verifier, lineage, configuration and development
challenge results.

A handwritten one-call wrapper performs the same action. This result establishes
a narrower compilation boundary, not the practical superiority of automatic
discovery, learned ranking, or maintenance. It must not be used to close those
reviewer objections.

## Remaining data and design decision

After historical-use, pilot, web-exposure, duplicate and gold-execution exclusions,
**666 corrected dev questions** remain across ten databases. One database has only
one remaining question and another has eight. All exclusions, including overlapping
reasons, are retained in [readiness.json](readiness.json). The count does not establish
independent groups, semantic gold validity, or freedom from model-training exposure.
Gold-cache exposure remains documented in the earlier audit. The candidate is
derived from nine databases, not a demonstration of coverage on all ten.

For illustration, reserve 120 questions for calibration and examine a 500-question
test. Under the existing exact IID paired calculation with one contrast at 0.05:

| Planning scenario | Power |
|---|---:|
| GAC-only correct 4%, comparator-only correct 1% | 83.3% |
| GAC-only correct 3%, comparator-only correct 1% | 54.3% |
| Conservative 2-point noninferiority, comparator-only correct 1% | 44.0% |

These are hypothetical sensitivities, not expected effects, an accepted quality
margin, a final sample-size choice, or power after accounting for database/template
dependence. A resource-saving method need not improve accuracy, so the first row
does not justify claiming that the whole planned study is adequately powered.

**Decision: no-go for confirmatory execution remains in force.** Comparator
execution and existence of a narrower candidate have advanced; the following
scientific and implementation conditions remain unmet:

1. Fix the target claim and population. A one-call study can estimate preservation
   of quality and resource use on a restricted SQL population. It cannot identify
   learned-selection or automatic-maintenance benefit. To claim those benefits,
   acquire a development workload where simpler policies make meaningfully
   different decisions, retaining all rejected candidates.
2. Implement and validate the continuation boundary, clean fallback accounting,
   equal-information arms, and uniform final-answer parsing. Compare handwritten
   and unguarded policies on the identical prefix before attributing differences
   to a safeguard. Keep the existing full-schema prefetch as a separate policy.
3. Freeze candidate, population, grouping, loss, thresholds and multiplicity before
   sampling fresh unfiltered calibration. Retain missing outcomes and failures.
   A replay bound must remain distinct from final-answer quality.
4. Seal independent final testing with a justified quality margin or an explicitly
   estimation-only endpoint, fixed sample size, balanced arm order, complete cost
   accounting and null/adverse-result interpretation. Do not extend the cohort
   after observing results or select an independence unit that permits admission.
5. Integrate completed evidence into the manuscript and reviewer response with
   its actual scope. The reviewer's learned-gate, lifecycle and compiler-value
   objections remain open until their respective experiments support them, or
   the corresponding contribution claims are removed.

The authorized $300 campaign cap and persistent shared ledger remain in force.
This follow-up uses no additional API budget. No acceptance prediction follows
from implementation QA or these feasibility results.
