# BFCL gold-plan compiler protocol

**Status: pre-registered and executed on 2026-08-18; the predeclared expectation held.**
This protocol turns the existing BFCL v4 compatibility row into a third independent
substrate for the read-only compiler. It changes no compiler code, no admission gate, no
artifact, and no fallback policy, and it makes no provider call. The predeclared
expectation, decision rule, and preconditions below were written and committed before the
compiler was run on this corpus, so that the anticipated null could not later be read as a
failed experiment; the observed results were recorded in a second commit.

## Why BFCL can be a compiler substrate at all

The published external-benchmark ledger records BFCL as *pinned gold-plan compatibility*:
200/200 `multi_turn_base` plans pass the official checker, but the reference calls carry no
results, so `reference_task_to_episode` fails closed and no compiler number exists. That
gap is not fundamental. BFCL's multi-turn categories ship an executable stateful backend:
each task carries an `initial_config` snapshot plus a list of involved Python API classes,
and the official `execute_multi_turn_func_call` helper runs a turn's calls against
instances loaded from that snapshot. Executing the official *gold plan* through that helper
supplies the missing field, and with it the four things the compiler requires:

| Requirement | Supplied by |
|---|---|
| Ordered calls with observed arguments and results | the gold plan executed on the pinned backend |
| Compatible entry snapshot | each task's own `initial_config`, plus first-appearance gold literals as user inputs |
| Effect declarations | `benchmarks/contracts/effects/bfcl.yaml`, a signed per-method catalog for all 81 methods the gold plans call |
| Replay oracle | re-execution of the same plan from the same entry snapshot, in-process and provider-free |

The observed result retained for each call is the exact string the upstream harness would
have shown the model. It is additionally parsed into structured JSON where the payload
permits, and retained verbatim where it does not; the parse kind is recorded per call.

## Predeclared expectation

**The corpus is expected to retire every candidate family: `exact_gate.outcome = RETIRE`.**

The reasoning is arithmetic and does not depend on running the compiler. Promotion requires
92 independent zero-violation calibration groups (`configs/promotion.example.yaml`,
`min_calibration_groups: 92`, the exact bound at `alpha=0.05` over an 11-point grid). Each
BFCL task is one episode and one group, so the corpus offers at most 200 groups in total,
spread across eight unrelated scenario classes, with a per-task randomized initial state.
For a single canonical window family to reach 92 zero-violation groups, at least 92 of the
200 tasks would have to share one canonicalized read region *and* survive held-out replay.
Certification is therefore arithmetically possible but implausible; the expected result is
the same fail-closed refusal already recorded for NESTFUL and API-Bank, reached on a third
independent substrate with a different tool surface and a different entry-state contract.

This experiment is run to test whether that refusal generalizes, not to produce a
compaction win. A positive compaction result on this corpus is not a stated objective and
would not be reported as one without the gate clearing on its own terms.

## Decision rule

| Observed | Reading |
|---|---|
| `RETIRE`, with families synthesized and held-out windows abstaining | Predicted outcome. A third substrate reproduces the refusal; report as replication. |
| `RETIRE`, with no family reaching support of three | Predicted outcome, weaker form. Report the support distribution and the blocking-reason histogram; do not describe it as a compiler failure. |
| `RETIRE`, but a held-out window is *wrong* rather than abstaining | Adverse finding. A wrong dispatch on a public substrate is reportable in full and takes precedence over the replication framing. |
| `candidate_present` (a family with support at least 92) | Surprise. Report the family, its support, and its held-out outcome; the certification claim then rests on the gate's own arithmetic, not on this prediction. |

Any of the preconditions below failing means no compiler number is published for this
substrate at all. The failure is reported instead.

## Preconditions, all fail-closed in the driver

1. **Catalog completeness.** Every method appearing in a gold plan has a declaration.
   An undeclared method aborts the run rather than defaulting to `UNKNOWN`.
2. **Clean execution.** No gold call may return the upstream `Error during execution:`
   sentinel. A single error aborts: an error-bearing corpus is not a clean observed trace
   set.
3. **Effect declarations are not looser than observed behaviour.** The driver snapshots
   every involved instance's state around every call. A method declared read-like that is
   observed mutating state aborts the run, as does a method declared *compilable* that is
   observed advancing the scenario RNG. Declaring a stricter effect than observed is always
   permitted; this audit is one-directional by design.
4. **`PURE` matches upstream.** `PURE` is licensed only for classes upstream itself lists
   in `STATELESS_CLASSES`.
5. **Exact replay.** A second independent execution pass must reproduce every observed
   result byte for byte. Pass one executes call by call and pass two executes each turn as
   one list, so the check covers both backend determinism and the equivalence of the two
   invocation shapes.

Two known time-varying methods are declared read-like but deliberately not replay-licensed,
so they can never enter a compiled region: `TravelAPI.verify_traveler_information` derives
an age from `datetime.today()`, and `VehicleControlAPI.get_outside_temperature_from_google`
draws from the seeded scenario RNG and advances it.

## Fixed parameters

The mining and synthesis parameters are the ones already used for the API-Bank substrate
and are not adjustable for power: `max_depth=2`, `kappa=3`, `w_min=2`, `w_max=12`,
`b_min=2`, minimum support of three independent groups before synthesis is attempted, a
held-out split of at most a quarter of a family's groups, 25 synthesis permutations, and
the exact gate at `alpha=0.05`, `delta=0.10` over the 11-point grid. The one deliberate
difference is the entry schema: API-Bank admits `inputs` only, while this substrate admits
`inputs` and `environment`, because BFCL genuinely publishes the entry snapshot. That is
the more generous choice, so a refusal here cannot be attributed to a starved entry
contract.

## Observed results

The corpus executed and retired exactly as predicted. All 200 tasks and 1,142 gold calls
executed on the pinned backend with no upstream error sentinel, and the independent
re-execution pass reproduced 1,142/1,142 observed results byte for byte, so the replay
oracle precondition held.

| Quantity | Observed |
|---|---:|
| Tasks / independent groups | 200 / 200 |
| Observed calls (all with retained results) | 1,142 |
| Turns | 734 |
| Distinct tools declared and exercised | 81 |
| Episodes with at least one candidate window | 86 |
| Candidate windows / candidate families | 146 / 77 |
| Families with support of at least three groups | 9 |
| Maximum family support | 15 |
| Families synthesized | 4 of 9 attempted |
| Held-out recorded replay | 3 pass, 3 abstain, **0 wrong** |
| Exact gate | `RETIRE` (15 observed groups against 92 required) |

Five of the nine eligible families failed synthesis on an ungroundable slot; the four that
synthesized produced programs of one or two steps. One family (support 13) reproduced all
three of its held-out windows exactly. The 3/6 held-out pass rate sits between NESTFUL's
24/36 and API-Bank's 0/2, so it is a second corpus with passing held-out replay rather than
the first. No held-out window was wrong on any family, so the adverse branch of the decision
rule was not taken.

Candidate suppression is dominated by the declared write barriers, as the catalog intends:

| Blocking reason | Suppressed spans |
|---|---:|
| `effect_write` | 2,802 |
| `live_in_not_in_entry_schema` | 45 |
| `effect_capability` | 35 |
| `ambiguous_slot` | 31 |
| `partial_run` | 5 |

The empirical audit observed 1,060 state-mutating calls across 44 tools and 94 RNG-advancing
calls. Zero read-like declarations were observed mutating state and zero compilable
declarations were observed advancing the RNG, so the signed catalog was never looser than the
behaviour it describes. The audit also produced one finding worth stating on its own:
`TravelAPI.get_flight_cost` is a nominal getter that mutated `_flight_cost_lookup` on 36 of
36 calls, so it is declared a write. A name-based or docstring-based effect inference would
have admitted it into a compiled region.

The reading is therefore the predicted one: a third independent public substrate, with a
different tool surface and a more generous entry contract, reproduces the fail-closed
refusal while demonstrating that the compiler does synthesize and does replay correctly
where support exists. What is new here is the pre-registration, the obtained-rather-than-
retained results, and the empirical effect audit — not the existence of passing held-out
replay, which NESTFUL already showed. It remains a retirement, not a compaction result.

## Claim boundary

This substrate licenses exactly one kind of statement: that the compiler, its effect
barriers, and its exact promotion gate behave as specified on a third independent public
corpus with complete observed results. It does not license a function-calling accuracy
claim (the gold plan is supplied, not predicted, and no model runs), an end-to-end planning
or quality claim, an efficiency claim, or any real-world or production claim. BFCL
multi-turn is a simulator; its results are never pooled with the real-record GitHub
workflow families or with any other substrate.

The all-source matrix in `paper/results/external_benchmarks/reference_analysis.json` is
sealed at the disposition that preceded this run, and its
`totals.measured_compiler_benchmarks: 2` counts only the compiler paths present at that
seal. This substrate publishes separately as
`paper/results/external_benchmarks/bfcl_compiler_execution.json`; the next full-source
refresh of the matrix should incorporate it as a third compiler path.

## Reproduction

Acquisition is provider-free. Use a disposable source directory outside the repository:

```bash
python paper/scripts/external_benchmark_sources.py \
  --root "$BENCHMARK_SOURCE_ROOT" \
  --output paper/results/external_benchmarks/source_preflight.json

python -m pip install -r benchmarks/external/requirements/bfcl-structural.txt

python paper/scripts/bfcl_compiler_benchmark.py \
  --source-root "$BENCHMARK_SOURCE_ROOT"
```

`mpmath` is the only dependency outside the standard library; the full BFCL model-generation
stack is not required, because no model is run. The driver writes only counts, hashes,
structural field names, and per-family aggregates: prompts, arguments, observed results, and
scenario state are not serialized.
