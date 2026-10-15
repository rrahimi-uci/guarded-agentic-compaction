# Live safeguard recovery pilot

Prospective exploratory pilot following PR #79's deterministic diagnostic.
The question is whether request-scope and output-completeness checks improve
final task correctness or total recovery cost when every arm can repair missing
evidence. Equal accuracy with different repair cost is an informative outcome.
This is not a fresh live learned-gate study or a new statistical certificate.

## Frozen cohort and interventions

SHA-256 ranking with seed 20261017 selects 24 of the diagnostic's 96 held-out
issues, without looking at its answers, comment count, failure status or dispatch
outcomes. The source issues have already been used offline, but no live answer
on this task is used for selection. This is not a new population or a sample of
natural user requests. Keep empty/short issues and all unfavorable outcomes.

Each issue receives all three requested limits (1, 3, 5), both ordinary and
two-comment-capped responses, and all four arms: **576 episodes**. Ordinary and
capped-response stress are reported separately. The six variants of an issue are
correlated; the independent grouping unit, if independence is assumed, is the
issue, not an episode. This pilot carries no power or noninferiority claim.

| Arm | Initial observations supplied to the common live agent |
| --- | --- |
| `baseline` | None; the live agent chooses its own source reads |
| `full` | Accepted outputs from the frozen diagnostic program and contracts |
| `no_entry_hull` | Same program, with only the requested-limit hull removed |
| `no_completeness_check` | Same program, with only the page-completeness clause removed |

The gate-only arm is omitted prospectively: its fixed score and decisions are
identical to full, so the pilot concentrates on the two mechanisms with different
behavior. This omission does not turn its prior null into positive gate evidence.

The prefetch component uses the **unchanged diagnostic execution manifest**,
program, contracts, and gate through the real dispatcher. Its original model pin
identifies that deterministic component, not the live continuation. No artifact
is silently repinned to the live model. The new continuation has its own sealed
prompt, model, schemas, and settings. Offline calibration metadata does not
certify this live continuation or the ablated contracts.

On guard/verifier refusal, give the live agent the same empty initial-observation
list as baseline. Do not perform deterministic reference-policy fallback and do
not expose discarded partial outputs or refusal reasons. Count every speculative
read before fallback. Accepted observations include each executed tool's name,
arguments and result: `complete` is relative to that call's requested page, not
necessarily the user's larger requested window. Do not hide this distinction.

## Common live continuation

Use `gpt-5.6-luna` with low reasoning and verbosity, no parallel tool calls,
`store=False`, and a 2,048-output-token limit per request. One SDK run is bounded
at eight model turns and 120 seconds. All arms expose the same `read_issue` and
`read_comment_page` function schemas and implementations. They use the same
source and response cap, enforce the current issue, and return recoverable errors
for invalid page arguments. Page limits are 1 through 5; recovery offsets must
be within the requested window. Source comments are untrusted data, never
instructions. There is no tool that supplies the source oracle or precomputed
answer. No arm name, correctness label or expected answer enters the prompt.

The task and structured answer remain issue number, available-comment count in
the requested prefix, and one-based positions containing case-insensitive
substring `error`. The pinned source oracle grades all three fields jointly.
Count duplicates, missing positions and incorrect counts as wrong answers. The
new runner never alters PR #79's deterministic outcomes.

Each issue uses one of all 24 arm permutations; rotate the order by request
variant. With 24 issues, each suite/limit stratum contains every permutation
exactly once. Run sequentially in the frozen order. This counterbalances arm
position, not all possible provider drift or caching effects.

## Seal, spending and failure accounting

`prepare` is provider-free. Freeze cohort, all 576 scheduled episodes, protocol,
source and diagnostic artifacts, study/runtime code, installed dependencies,
model settings, prompt, answer/tool schemas, price table, and the real offline
dispatcher outcomes. Verify the seal before calls and audit it after the run.
Reproducing diagnostics is not a live correctness measurement.

The new live run requires an explicit `--approved-spend-usd`. A proposed $10 cap
is an **estimated-spend ceiling**, not approval and not a hard provider billing
cap. Reserve $1 before each episode and retain an unknown-cost reserve on failed
or interrupted attempts. The frozen repository price table is an estimate, not
an invoice or a claim about current public prices. No approval for an earlier
study is silently reused. Save the cap in the checkpoint before the first call.

Persist a pending episode before execution and atomic checkpoints after every
episode. Disable transport/application retries and external trace export.
Failures stay in the attempted denominator and stop the run; do not retry them
automatically or replace their records. Interrupted/pending, failed, tampered,
misordered or differently budgeted checkpoints cannot resume. A completed run
makes no further calls. A filesystem lock prevents concurrent execution.

Retain final structured answers, per-response token usage, tool arguments and
output digests, dispatch decisions, timing, quality and estimated cost. Do not
serialize provider reasoning, encrypted reasoning, credentials or raw SDK
responses. Missing usage is unknown cost, not zero cost. Local SDK tracing is
disabled; successful response usage is read directly from SDK return objects.

## Outcomes and interpretation

Report each suite separately: scheduled/attempted/completed/failed/unattempted,
correct answers, prefetch dispatch/refusal, wrong final answers after dispatch,
continuation tool calls, total tools (including discarded work), model requests,
tokens, wall latency and estimated spend. Baseline continuation calls acquire
initial evidence; compiled continuation calls may repair or redundantly reread
evidence. Call all of them continuation calls, and separately count episodes with
calls after accepted dispatch. Do not label every baseline call a repair.

Pair full versus each ablation and baseline on the same cases; include failures
and report affected issue groups. Resource savings require complete accounting
for both arms. Do not infer statistical-gate protection, causal effects of
automatically mined contracts, or a higher ICLR acceptance probability from a
small pilot. A source regrade checks consistency, not independent human gold.

```bash
PYTHONPATH=src .venv/bin/python paper/scripts/live_safeguard_recovery.py prepare
PYTHONPATH=src .venv/bin/python paper/scripts/live_safeguard_recovery.py verify
# Only after a separate explicit spending limit is authorized:
PYTHONPATH=src .venv/bin/python paper/scripts/live_safeguard_recovery.py run --approved-spend-usd APPROVED_CAP --env-file /absolute/path/to/.env
PYTHONPATH=src .venv/bin/python paper/scripts/live_safeguard_recovery.py analyze
PYTHONPATH=src .venv/bin/python -m pytest paper/scripts/test_live_safeguard_recovery.py
```

SDK integration follows the installed repository SDK and the
[official function-calling guide](https://developers.openai.com/api/docs/guides/function-calling).
This pilot changes no production runtime, deployment, manuscript or historical
publication artifact. Live results will be retained separately in this PR.
