# Prospective end-to-end gate study on public issues

**Status: preflight sealed, provider execution pending (2026-10-08).** This is a
single-candidate, single-snapshot study. It tests whether a score learned from
entry-observable source facts can produce admissible intermediate coverage when
the violation is a final factual-task error after actual compiled dispatch. It
does not establish cross-repository generalization or replace the executed
multi-repository result in the main paper.

## Frozen source, candidate, and sampling

The source is the pinned public issue parquet and source manifest already used
by the natural-workflow study. `paper/scripts/graded_issue_gate_preflight.py`
checks its SHA-256 against the source manifest, applies the existing canonical
duplicate-row rule, excludes all earlier study issue numbers plus the prior
90-case pilot, and uses SHA-256 ranking with seed `20261008`. The resulting
`paper/results/graded_issue_gate/preflight.json` seals 474 distinct issues with
at least one comment: development 200, calibration 184, and test 90. The fixed
plain-text / bare-URL / Markdown-link quotas are 80/60/60, 76/55/53, and
37/30/23 respectively. This deliberately enriched mixture is the target
population; results must not be presented as natural issue prevalence. No
provider call was used to choose these cases.

The compiled candidate is the pre-existing `github_natural_live` registry
artifact, whose program, hard guard, and original calibrated gate are frozen.
It was compiled before this cohort was selected. The unchanged arm uses the
same `gpt-5.6-luna` model, factual prompt, schema, snapshot-backed read tools,
and independent factual grader as the prior natural-workflow study. All runs
retain the original artifact's guard and gate; this study adds a second,
stricter routing decision outside it.

## Entry read and score

Before each episode, every arm makes one counted local source read. This read
derives six descriptors: Markdown-link indicator in the first three comments,
bare-URL indicator, log(1 + comment count), label count, title length / 100,
and issue age in years as of the pinned snapshot's final day (2025-06-13).
The score sees these numeric descriptors, not comment text, the model answer,
the factual grade, or a test label. The read's count and elapsed time are
recorded separately and included in total tool calls and wall latency for each
arm. Its cost is local and has no provider charge. Computing the test routing
decision from the same source is analysis work; it does not change the agent's
prompt or expose a different tool response to one arm.

The six-feature logistic `q` is fitted on 200 development groups with fixed
seed. A group is a unique issue number. A wrong final factual answer following
actual compiled dispatch is both an unproductive event for fitting and a
violation for calibration; a refused dispatch is ineligible and cannot be a
wrong-dispatch violation. The development label is never used to select the
threshold. If development labels are degenerate, the existing fitting routine
returns a constant score and that outcome must be reported.

Calibration uses the existing eleven-point grid
`(0.02, 0.05, 0.08, 0.11, 0.14, 0.17, 0.20, 0.25, 0.30, 0.40, 0.50)`,
`alpha=0.05`, `delta=0.10`, minimum coverage `0.02`, and a Bonferroni-adjusted
one-sided Clopper-Pearson bound. No test result affects fit, grid, or threshold.
With zero violations a grid point needs at least 92 accepted calibration
groups, so the 184-group pool can in principle certify 50% coverage. The
support-only ablation uses the same score, candidate, and calibration groups
with `alpha=1.0`, which appends accept-all threshold 1.0. It is an ablation of
the risk budget, not an independent heuristic. If the learned gate retires,
do not run the held-out test; report the retirement as the primary outcome.

## Frozen test comparison and interpretation

After calibration is recorded in `frozen_gate.json`, run all 90 test issues
under the unchanged agent, learned routing, and support-only routing. A routed
issue uses the original compiled runtime, which may itself refuse and fall back;
an unrouted issue runs the unchanged agent. Count actual compiled dispatches
separately from routing decisions. Record per-issue paired correctness, final
task-contract errors, provider requests, total tool calls (including the
entry read), wall latency (including the entry read), and estimated provider
cost. Every incomplete or failed attempt stays in the denominator as an
incomplete episode, not a pass. The study reports the full eleven-point
calibration sweep, including each accepted count and violation count.

Primary selectivity evidence requires at least three **distinct, admissible,
nonzero** calibration coverage levels on the frozen grid; repeated coverage
counts at several thresholds count once. Any observed held-out wrong dispatch
in either gate is an adverse event that must be foregrounded. A
learned gate that retires, has fewer than three levels, or gives no meaningful
held-out benefit is a null or negative result, even if overall agent quality
remains high. Because this is one selected repository, these outcomes cannot
alone support a broad 85/100 ICLR-quality score or a cross-domain safety claim.

## Execution and spending

`graded_issue_gate_study.py` checks the source and cohort before calls, runs
development, then calibration, then held-out test, and checkpoints after each
batch of at most eight. It fails closed on an incomplete batch; a retry needs
a documented protocol amendment. The authorized cap is $200. Before each
batch it reserves $1 per attempted episode against that cap, in addition to
measured prior estimated spend and failed-run reserves. This is an internal
budget guard based on public model pricing, not an invoice or a hard provider
billing limit; actual provider charges must be checked separately. Keys are
read from `.env` and never serialized. Results and any deviations will be
added to the same review PR after execution. Test-arm order is fixed rather
than counterbalanced, and latency comparisons may include time trends.
