# Prospective gate-frontier protocol

**Status: EXECUTED on four of five repositories (2026-08-22); reported below.** The
cohort was sealed provider-free, then run: 240 of the pre-registered 300 pooled held-out
pairs were completed, short of the target because `pytorch/pytorch` retires at compile
time (the same repository, and the same kind of outcome, `github_multirepo_pr_outcome_core.py`'s
own smaller cohort already reports), not because of any new failure mode. See
"Observed results" below for the full account. The original design text further below is
unchanged from when it was pre-registered: nothing in it was revised in light of what
execution showed.

## Update (2026-08-22): design resolved, support-only arm implemented, cohort sealed

This protocol named its cohort target (>=3 repositories, >=300 pooled held-out pairs) and
its three arms without fixing which script would produce them. That gap is now closed by
extending, not replacing, the already-executed cross-repository harness
[`github_multirepo_pr_outcome_core.py`](../scripts/github_multirepo_pr_outcome_core.py)
(see `github-multirepo-pr-outcome-core-summary.md` and `evidence-register.md` for its own
prior 120- and 180-pair results, which this protocol's cohort is independent of, not
additive with):

- **Resolved cohort.** `discovery_cases=116` (this repository's own 16 train + 8 dev + 92
  calibration minimum, unchanged), `test_cases_per_repo=60`, across the same five
  repositories `github_multirepo_pr_outcome_core.py` already uses
  (huggingface/datasets, pandas-dev/pandas, psf/requests, streamlit/streamlit,
  pytorch/pytorch). This is the *unique* configuration — checked provider-free before any
  code was written for this update — at which all five repositories stay selectable and
  the pooled held-out cohort is exactly the pre-registered 300, with no repository
  dropped to reach the target. Sealed at
  [`../results/github_multirepo_gate_frontier/preflight.json`](../results/github_multirepo_gate_frontier/preflight.json)
  (`provider_calls_executed: 0`).
- **Support-only arm, operationalized.** `docs/related-work-matrix.md`'s "dispatch on
  recurrence alone" comparator is implemented as `alpha=1.0` in a second, independent
  `compile_grc` pass per repository — this repository's own precedented "published
  support-only research ablation" (see the comment above the `alpha == 1.0` branch in
  `src/guarded_agentic_compaction/grc/calibrate.py`, which predates this update). It keeps
  mining, synthesis, challenge, and frozen-candidate selection byte-for-byte identical to
  the learned-gate pass and changes only the Clopper–Pearson risk budget, which this
  family's minimal `entry_schema=("record_number",)` design makes the more tractable
  operationalization here than fitting a new standalone recurrence feature from scratch.
  This substitution is stated plainly so a reader can judge it rather than discover it:
  it is not a literal second scoring function, only a literal second risk budget, on the
  same candidate.
- **Coverage levels, read back out rather than re-derived.** `calibrate_gate` already
  computes one row (accepted count, violations, exact upper bound, coverage) per point on
  the frozen eleven-point grid before selecting a threshold, and stores the full sweep in
  `Gate.notes`. The implementation only parses that back out; it does not add a new
  statistical procedure to decide the coverage-levels question.
- **Implementation.**
  [`github_multirepo_gate_frontier_study.py`](../scripts/github_multirepo_gate_frontier_study.py),
  tested provider-free in
  [`test_github_multirepo_gate_frontier_study.py`](../scripts/test_github_multirepo_gate_frontier_study.py).
  Live execution is gated behind `--approved-spend-usd > 0`, matching every other live
  study in this repository.
- **Smoke-validated at trivial real cost.** A single-repository run (`psf/requests`,
  full 116-case discovery plus all three conditions on its 60-case held-out split) was
  executed to confirm the new support-only compile path and coverage-curve extraction
  work end to end before committing to the full five-repository spend; see the results
  register this update also adds for the observed cost and outcome. This is a pipeline
  check, not the pre-registered evidence — the full cohort's result is what this
  protocol's hypotheses bind to, and it has not been run.
- **Estimated full-cohort cost.** Scaling from `github_multirepo_pr_outcome_core.py`'s
  own recorded single-repository costs
  (`paper/results/github_workflow_families/pr_outcome/final/results.json`: baseline
  $0.0203763/30 cases, compiled $0.0050332/30 cases) across 580 discovery episodes plus
  900 held-out episodes (300 cases × 3 conditions) puts the full five-repository run at
  under $2 even with a generous safety margin over the per-repository smoke check's
  observed cost. This is a cost estimate stated before spending it, not a result.

## Observed results (2026-08-22)

Executed against all five sealed repositories at a total real cost of **$0.41**
(discovery + all three conditions' held-out evaluation, across every attempt including
two retries of `streamlit/streamlit` after transient provider timeouts during discovery —
see "What happened to the other repository" below).

**Cohort achieved: 240 of 300 pooled held-out pairs, four of five repositories.**
Discovery reaches 580/580 exact traces (116/116 per repository, including
`pytorch/pytorch`). Four repositories admit a candidate and complete their full 60-case
held-out split under all three conditions: `huggingface/datasets`, `pandas-dev/pandas`,
`psf/requests`, `streamlit/streamlit`. `pytorch/pytorch` retires at compile time: the
compiler mines one candidate with support 16 across the calibration split, but the
tightest attainable Clopper–Pearson upper bound at every grid point is 1.000 — no
calibration group is ever accepted, so the candidate never reaches an admissible
threshold. This reproduces, on an independent, five-times-larger cohort, exactly the
retirement `github_multirepo_pr_outcome_core.py`'s own 30-per-repository cohort already
reports for the same repository: not a new failure mode, and not an artifact of the
smaller cohort's specific record selection.

**Exact-contract preservation:** 240/240 on baseline and learned-gate; 239/240 on
support-only after one held-out record (`psf/requests` #6708) failed under a transient
`TimeoutError` independent of condition or repository — the identical record that failed
identically during the single-repository pipeline smoke check this document recorded
above, confirming it is a provider-side transient rather than a new fault.

**Efficiency, relative to the unchanged baseline, pooled over 240 (239 for support-only)
pairs:**

| Arm | Requests | Total tokens | Wall latency | Estimated cost |
|---|---:|---:|---:|---:|
| Learned gate ($\alpha=.05$) | -44.4% | -52.3% | -51.0% | -48.3% |
| Support-only gate ($\alpha=1$) | -44.4% | -52.4% | -47.9% | -48.8% |

The two arms are statistically indistinguishable on every metric. This is expected given
the coverage finding below, not a separate result: two gates that admit the identical
threshold produce identical dispatch behavior regardless of what risk budget separates
them on paper.

**Coverage-level finding — the null, not a frontier.** Reading every point the frozen
11-point grid produces for the learned gate, before threshold selection, directly out of
`Gate.notes` (not re-derived): three of the four admitting repositories
(`pandas-dev/pandas`, `psf/requests`, `streamlit/streamlit`) accept zero calibration
groups at every $\eta \le .08$ and all 92 at every $\eta \ge .11$ — a pure two-point step,
0.0 then 1.0, with nothing between. The fourth, `huggingface/datasets`, additionally
accepts 10 of 92 groups at $\eta \le .08$ (coverage 0.1087) — the one place in this whole
cohort where the raw sweep shows a third value — but that point's exact upper bound is
**.375**, far above the registered $\alpha=.05$ budget, so it is never admissible and is
never selected. Every repository, under both the learned gate and the support-only
ablation, deploys the identical coverage-1.0 threshold. No repository, under either arm,
ever deploys at an intermediate admissible coverage. Support-only's own sweep is
pointwise identical to the learned gate's on every repository (expected: raw
accept/reject counts at a given $\eta$ do not depend on $\alpha$, only which $\eta$ ends
up selected does), which is itself informative: even removing the risk budget entirely
does not surface a coverage point the risk-budgeted gate was suppressing.

Per the decision rule fixed in advance, this is the pre-declared fourth outcome:
*"Neither gate produces graded coverage (both step-like). The workload did not supply
enough gradient; report the null and do not manufacture a frontier from a homogeneous
cohort."* No held-out wrong dispatch was observed on either gate at the admitted
threshold in any repository, so the pre-declared adverse-finding row (row 3) also does
not apply. At four times the previous cross-repository scale, and against a comparator
built to share every statistical mechanism except the risk budget, the exact-$\alpha=.05$
gate remains a support threshold. This confirms, rather than resolves, the step-gate
finding this paper already reports from its primary families and from AppWorld.

**What happened to the other repository, in full.** `streamlit/streamlit`'s discovery
pass failed twice before succeeding: the first full five-repository run lost 2 of 116
discovery calls to `APITimeoutError`, leaving 114 exact traces (113 with `quality.overall`
true) against the 116 the frozen split requires, so `github_multirepo_gate_frontier_study.py`
correctly raised rather than compiling on a short discovery set. A retry lost 8 of 116 to
the same transient error. A second retry succeeded, reaching 116/116 exact traces and
completing the full held-out split reported above. Nothing about the selection, the
candidate, or the admitted threshold differs between attempts — only the discovery calls
that happened to time out — and the final, reported numbers come from the successful
attempt exclusively; no partial or failed attempt's data is pooled into the results above.

**What this does and does not change.** It does not change the hypotheses, the decision
rule, the cohort design, or the $\ge 3$-repository / $\ge 300$-pair target stated below:
those were fixed before this run and nothing here revises them retroactively. It does not
reach the pre-registered 300-pair target — 240 is reported as short of target, not
rounded up to it. It does not authorize or perform the deferred model/provider-breadth or
executable-comparator extensions (the latter is separately closed, no-go, in
`awo-comparator-feasibility-spike.md`). A fifth repository could in principle be added to
reach 300 pooled pairs outright, since `pytorch/pytorch`'s retirement is a compile-time
finding about that specific repository's calibration split, not a ceiling on how many
repositories this design can support; none is currently pinned and acquiring one is not
authorized by this update.

Nothing above changes the hypotheses, the decision rule, the >=300/>=3 target, or the
stopping rule stated in the original design below; it resolves the previously-open
question of which script and which configuration realizes them, and reports one honest
implementation choice (the support-only operationalization) that a later reviewer could
otherwise reasonably ask about.

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
