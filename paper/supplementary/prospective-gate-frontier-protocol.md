# Prospective gate-frontier protocol

**Status: PRE-REGISTERED, NOT EXECUTED.** No repository beyond what this paper already
reports has been acquired under this protocol, no provider call has been made under it,
and no held-out case has been selected. This document commits the design, the sample
size, the three arms, the coverage levels, and the decision rule *before* any of that
evidence exists, so that if the evidence is later gathered, the design cannot be revised
in light of what it shows. Running it is future work requiring provider budget
authorization; this commit does not authorize that spend, and this paper reports no
result from it.

This is a different kind of protocol from
[`bfcl-compiler-protocol.md`](bfcl-compiler-protocol.md) and
[`appworld-compiler-protocol.md`](appworld-compiler-protocol.md). Those pre-registered an
expected *outcome* on a corpus that could be acquired and run provider-free, and both were
executed within the same change that introduced them. This one pre-registers a *design*
whose execution requires new repositories, a new held-out cohort, and paid provider calls,
so it is committed on its own, unrun, and reproduction of it will be a separate,
independently reviewable event.

## Why this experiment, and why now

Every registered $\alpha=.05$ gate this paper reports is a step function: five of the six
admit all or none of their calibration groups, and the one partially selective gate
(`guarded-composite`) refuses four of its 92 groups only because that refusal is exactly
what pushes its own bound above the registered 5% budget
([`gate-selectivity-analysis.md`](gate-selectivity-analysis.md)). AppWorld reproduces the
same step behavior on a public corpus rather than repairing it
([`appworld-compiler-protocol.md`](appworld-compiler-protocol.md)). None of this paper's
current evidence, external or live, demonstrates that the calibrated score $q(z)$
separates risky entry states from safe ones; it demonstrates a sample-size requirement and
a principled refusal. A genuine risk--coverage frontier — one showing that admitted
coverage trades off gracefully against realized risk across at least a few genuinely
distinct nonzero risk budgets, not two points at 0% and 100% — has not yet been observed
at the registered configuration.

Two structural facts motivate running this now rather than waiting for a stronger gate to
turn up on its own. First,
[`frozen_candidate_coverage_simulation.py`](../scripts/frozen_candidate_coverage_simulation.py)
and the corollary it backs (`\cref{cor:frozen}` in the main text) show that frozen
single-candidate selection already closes the compiler-wide multiplicity gap for *any*
future study that adopts it, so a new prospective cohort can report a compiler-wide
certificate rather than a per-candidate one without inventing new statistics. Second, the
existing multirepo time-forward harness
(`paper/scripts/github_multirepo_preflight.py`) already provides the provider-free
cohort-sealing machinery this protocol needs; the missing piece is scale and a graded
coverage design, not new infrastructure.

## Design

### Cohort

- At least **three** repositories or domains, extending
  `paper/scripts/github_multirepo_preflight.py` rather than replacing it.
- At least **300 sealed held-out paired cases** in total, reported both pooled and
  per-repository. Zero compiled-only failures in 300 independent pairs gives a one-sided
  95% exact upper bound near 1%, a materially tighter bound than the 30- and 90-record
  cohorts this paper currently reports, and large enough that a modest number of
  compiled-only failures (rather than only zero) remains informative.
- Discovery, development, calibration, and held-out test cases stay disjoint within and
  across repositories, exactly as `paper/scripts/github_multirepo_preflight.py` already
  enforces, and are sealed by hash before any provider call.
- Selection is time-forward: held-out records are strictly newer than discovery records
  in every repository, and this is validated provider-free before acquisition begins.

### Compilation

- **Frozen candidate selection throughout**
  (`freeze_one_candidate_before_calibration=True`), so any admitted gate here is licensed
  by `\cref{cor:frozen}` as a compiler-wide certificate rather than the per-candidate one
  the primary GitHub families report.
- Fixed mining and synthesis parameters, carried over unchanged from the sealed
  multirepo extension: `max_depth=2`, `kappa=3`, `w_min=2`, `w_max=12`, `b_min=2`, and the
  registered exact gate at `alpha=0.05`, `delta=0.10` over the eleven-point grid
  (`configs/promotion.example.yaml`).
- Thresholds, entry-state features, and the score model's functional form are frozen
  before any calibration group is observed, exactly as `\cref{prop:admission}` requires.

### Arms

Three arms, compared under **identical records, model, SDK, cache policy, and ordering**:

1. **Unchanged baseline agent.** No gate, no compiled artifact.
2. **Learned gate.** The calibrated score $q(z)$ of `\cref{sec:problem}`, admitted under
   frozen selection as above.
3. **Support-only gate.** Dispatch on recurrence alone (the frequency-only comparator
   `docs/related-work-matrix.md` already names as scored condition 4 in the primary
   families), calibrated with the identical Clopper–Pearson procedure so the two gates
   differ only in what $q$ conditions on, not in the statistical machinery around it.

### Coverage levels

At least **three distinct nonzero coverage levels** must be observed and reported for the
learned gate, not two endpoints. This requires a workload with graded structure: some
entry states genuinely easier to certify than others, so that the frozen threshold grid
produces intermediate admitted-coverage points rather than jumping from 0% to 100% between
adjacent grid values. The cohort design should deliberately include record classes
expected to sit at different points on that gradient (for instance, by record age,
discussion length, or label ambiguity) rather than relying on a single homogeneous task
to happen to produce one.

### Metrics

For every arm and coverage level: dispatch coverage, wrong-dispatch rate conditional on
dispatch, abstention rate, exact task-contract preservation, provider requests, tokens
(cold-input / cached-input / output, per the decomposition already used in
`\cref{sec:rq2}`), latency, and estimated cost.

### Fixed before acquisition

Thresholds ($\Lambda$, unchanged from the registered grid), entry-state features, the
train/development/calibration/test split ratios, the primary and secondary hypotheses
below, and the stopping rule (acquisition stops at the sealed 300-pair target; no interim
look changes the sample size or the frozen candidate). All of this is committed in this
file and hashed at commit time; a later revision of the design after evidence exists is
not a revision of this protocol.

### Hypotheses and decision rule

| Observed | Reading |
|---|---|
| The learned gate shows at least three distinct nonzero coverage points with wrong-dispatch rate at or below its registered bound at each, and dominates the support-only gate at matched coverage | The predicted positive outcome: a genuine risk–coverage frontier at the registered configuration, reportable as such. |
| The learned gate remains step-like (all-or-none) but the support-only gate does not, or vice versa | A negative result for the learned gate specifically; report the comparison and do not claim a frontier for the learned score. |
| Any held-out wrong dispatch exceeds the registered bound on either gate | Adverse finding, reported in full regardless of the other outcomes; a bound violation on live evidence outranks every other reading here. |
| Neither gate produces graded coverage (both step-like) | The workload did not supply enough gradient; report the null and do not manufacture a frontier from a homogeneous cohort. |

## Deferred, and explicitly not authorized by this document

Three extensions were considered and are recorded here as declined-for-now rather than
silently dropped, each with the bar it would have to clear before being added to a future
revision of this protocol.

**Model and provider breadth.** Repeat the identical protocol under the paper's current
model configuration, one materially different model family, and — if credentials and
adapter work are available — a second provider, holding cases, ordering, tools, cache
policy, and grading fixed. Report model-by-domain outcomes rather than pooling across
models. This does not block the primary experiment and can be added as a second phase
using the same sealed cohort.

**A fair executable workflow-compiler comparator.** AWO
(`docs/related-work-matrix.md`) is conceptually the closest published system: it mines
repeated tool-call sequences into deterministic meta-tools under a baseline-anchored
acceptance rule. It is included in a future revision of this protocol *only if* a
feasibility spike first confirms, without hand-waving: identical records and model,
equivalent execution placement, optimization overhead accounted separately from
deployment metrics, identical cache and ordering policy, and exact task-contract grading
shared with the other two arms. A forced or mismatched comparator would weaken the paper
more than omitting one; this document does not authorize running AWO or any other
comparator until that spike passes.

**Manual lifecycle cost.** Authoring, review, and drift-repair time for the manual
pre-model programs already used as comparators elsewhere in this paper remain unmeasured
here as well. Measuring it is valuable and orthogonal to the gate-frontier question this
protocol is scoped to, so it is left to a separate study rather than folded in here.

## What this protocol does not claim, stated before any data exists

It does not claim, in advance, that a frontier will be found: the decision rule above
treats "the gate remains step-like" as a reportable, valid outcome, not a failed
experiment. It does not claim superiority over the support-only gate before the comparison
is run. It does not claim that frozen selection is free — \cref{sec:extension}'s open
question about combining exploration with a compiler-wide guarantee is explicitly not
resolved by choosing frozen selection here; this protocol reports whichever single
candidate frozen selection happens to admit, at whatever coverage that candidate reaches,
rather than the best of several explored candidates. And it makes no claim about any
repository, domain, or model not named above.

## Authorization and reproduction

Executing this protocol requires, in order: (1) explicit authorization to acquire new
repository or domain data and to spend provider budget; (2) sealing the cohort with
`paper/scripts/github_multirepo_preflight.py` (or its extension to non-GitHub domains) and
publishing the preflight artifact before any provider call; (3) running discovery,
development, and calibration in that order, with the frozen-candidate configuration above;
(4) running the three arms against the sealed 300-pair held-out cohort; (5) publishing raw
results, the admission register, and this protocol's hash together, so any deviation from
the design committed here is visible in the diff.

No command in this section has been run. When it is, the results and any necessary
protocol amendments (only for preconditions that fail closed, never for the hypotheses or
decision rule above) will be recorded in a follow-up commit, exactly as
[`bfcl-compiler-protocol.md`](bfcl-compiler-protocol.md) and
[`appworld-compiler-protocol.md`](appworld-compiler-protocol.md) record their observed
results after their own predeclared expectations.
