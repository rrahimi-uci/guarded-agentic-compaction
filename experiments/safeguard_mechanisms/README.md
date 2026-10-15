# Isolated safeguard mechanisms: provider-free diagnostic

This study follows the null gate contrast in `experiments/fresh_safeguards`.
It tests **task-level consequences**, not merely whether a guard rejects.
It uses public source text, a constructed request workload, and a deterministic
continuation. It is not a live LLM experiment or a sample of natural user requests.
The separate capped-response suite is a constructed stress test; it must never be
pooled with the ordinary-response suite as a deployment failure rate.

## Frozen design

The pinned GitHub snapshot and conservative prior-study exclusions are reused.
The earlier 120-issue study is explicitly excluded too. SHA-256 ranking with seed
20261016 selects disjoint discovery/development/calibration/test groups of
24/96/192/96 issues. No comment-count, answer-quality, or dispatch filter is used.
One issue is a group: its request variants are correlated, not extra samples.

The task is to count the available comments in the requested first 1, 3, or 5
comments and return the one-based positions containing the substring `error`
(case insensitive). Zero-comment records stay in the cohort. This measures
missing evidence and incorrect counts; cosmetic excerpt matching is not an
endpoint. All arms use the same continuation, prompt-equivalent task, source,
tool implementation, and answer contract. The continuation sees only the
request and released evidence. The independent source oracle sees the snapshot.

Discovery executes a fixed two-read template (issue metadata, comment page) at
request limit 3. The production `synthesize_binding` routine fits each argument
from these fresh deterministic observations. This is **binding synthesis within
a hand-specified template**, not end-to-end mining or new LLM discovery. The
requested-limit guard is a task-scope contract fitted to discovery requests,
including that live-in even when synthesis chooses a literal. Output-completeness
and provenance clauses are explicit tool contracts. They are not claimed to be
automatically discovered by the production compiler. The candidate is frozen
before development, and cannot be replaced after calibration.

The real dispatcher runs these arms:

| Arm | Only intervention relative to full |
| --- | --- |
| `baseline` | Execute the deterministic reference read policy, including pagination |
| `full` | Frozen program, task-scope guard, output verifier, calibrated gate |
| `no_entry_hull` | Remove only the requested-limit hull; retain type, presence, pins, effects |
| `no_completeness_check` | Remove only the page-completeness verifier clause; retain shape, provenance, effects, call counts |
| `no_statistical_gate` | Replace only admission with accept-all; explicitly uncertified |

Program and evidence packaging are identical across compiled arms. On refusal,
the reference policy executes from the original request; already attempted reads
are counted, and no discarded partial output is exposed to the continuation.
The baseline is an exact deterministic reference policy, **not an unchanged LLM
agent**. Deterministic answers are not evidence that an LLM cannot recover from
missing evidence or could not make a different error.
The hull/verifier ablations retain the original numerical gate to hold its
decision fixed, but its calibration metadata applies only to the original
contract. It is not a valid certificate for either altered contract.

The ordinary suite uses an uncapped page response. The stress suite imposes a
two-comment page cap on **every arm and fallback**, with accurate completeness
and next-offset fields. The baseline follows pagination, while the fixed program
executes its frozen single page. Neither suite changes the public comment text.
All three request limits run for every test issue in both suites, regardless of
whether the cap or missing evidence changes its answer.

## Fresh calibration and stopping

Development and calibration use ordinary responses only, all three request
limits per issue. Features are the production `GateFeatures` computed from the
frozen guard. Fit the production logistic gate on guard-eligible development
cases; a verifier refusal is unproductive, a wrong released answer is a violation.
Calibrate the frozen model on separate issue groups using the production eleven-
point grid, alpha .05, delta .10, and minimum coverage .02. Keep guard-ineligible
cases in calibration with `eligible=False`. The group label is any accepted
violation within that group. Persist the complete input rows, gate, and grid.

Retirement stops held-out evaluation; the report must retain that outcome.
Constant features, constant scores, identical gate decisions, and zero added
protection are valid results. No score or threshold is changed to obtain a
positive contrast. This diagnostic may demonstrate the gate has no incremental
effect. It cannot establish a learned risk frontier, an end-to-end compiler
certificate, an LLM safety certificate, or a risk bound under capped-response
distribution shift. Fresh **live** discovery and calibration remain necessary
before a new live statistical-gate claim.

## Outcomes and artifacts

Report separately per suite and arm: scheduled/completed/failed cases,
dispatches, fallbacks, task correctness, wrong answers after dispatch, tool
calls including failed speculative work, and matched full-only/ablation-only
successes. Also report affected **issue groups** and mechanism-decision
disagreements. A changed decision without a changed answer is not protection.
Do not treat the 576 request variants as 576 independent observations or attach
binomial significance claims to this constructed cohort.

`prepare` writes a non-overwritable seal **before** discovering the candidate or
grading any experimental outcome. It binds source, selection, request matrix,
protocol, runtime and study code, and dependency versions. `run` verifies it,
then uses a fresh output directory exclusively, writes the candidate before
development, writes the gate before test, and records every scheduled outcome.
Exceptions remain failed cases, not deleted rows. Interrupted output cannot be
resumed or overwritten; a rerun needs a separately named directory and must
retain the interrupted attempt. `verify` replays the deterministic results
without network or provider calls and checks the complete artifact contents.

```bash
PYTHONPATH=src .venv/bin/python paper/scripts/safeguard_mechanism_study.py prepare
PYTHONPATH=src .venv/bin/python paper/scripts/safeguard_mechanism_study.py run
PYTHONPATH=src .venv/bin/python paper/scripts/safeguard_mechanism_study.py verify
PYTHONPATH=src .venv/bin/python -m pytest paper/scripts/test_safeguard_mechanism_study.py
```

There is no live-run command or provider spending in this diagnostic. A live
pilot must first specify the model/continuation and recovery tools, seal its
prompt and budget, count those recovery calls, and keep it separate from this
deterministic report. No manuscript, historical result, production runtime,
deployment configuration, or existing certificate is changed here.
