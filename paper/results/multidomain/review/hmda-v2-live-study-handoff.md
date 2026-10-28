# HMDA v2 live study handoff (2026-10-28)

**Status:** The study is still at the discovery phase; 0 of 40 discovery executions have
completed. Four distinct blockers were met in sequence on 2026-10-28. Three were resolved
(the October 7 strict-schema defect, already fixed in code; an invalid credential, rotated
by the author; a runner resume bug and a too-low request bound, fixed and documented here).
The fourth stops the study: the baseline agent's final answer systematically fails the
frozen `HmdaAnswer` schema, and the only fixes touch files bound by the signed macro
approval. No GRC artifact has been compiled, no pilot has run, and no artifact-calibration
summary exists, so the `calibrate-grc` approval packet cannot be assembled. This note
records exactly what was found, what ran, what it cost, and what a protocol-level
decision must settle before the phases can be re-run.

## 1. Root cause of the 2026-10-07 discovery failure (fixed before this work)

The retained ledger `paper/results/multidomain/discovery/ledger.jsonl` holds 80
`execution_started` and 80 `execution_failed` rows (40 groups, two attempts each) written
between 22:16:43Z and 22:16:44Z, every one with `error_type: UserError` and the message
redacted. Replaying one scheduled execution provider-free (dummy key, unreachable base
URL) against the runner version in effect at launch (commit `0ea8c41`, 12:41 PDT) raises:

```text
agents.exceptions.UserError: Strict JSON schema is enabled, but the output type is not
valid. Either make the output type strict, or wrap your type with
AgentOutputSchema(YourType, strict_json_schema=False)
  caused by: additionalProperties should not be set for object types. ...
```

`HmdaAnswer.special_states: dict[str, Literal[...]]` (`benchmarks/runtime.py`) emits
`additionalProperties` in its JSON schema, which the Agents SDK's strict mode rejects
when `Runner.run` builds the output schema. The exception fires before the HTTP client is
invoked, which is why all 80 attempts failed within one second and no provider request
occurred. Commit `3ce76b8` (15:22 PDT, six minutes after the 15:16 PDT run) added
`_output_schema()`, which wraps exactly such types in the SDK's non-strict
`AgentOutputSchema`; `tests/unit/test_multidomain_output_schema.py` pins that behavior.
The same replay against the current runner proceeds to the provider request. The ledger
simply predates the fix and was never re-run.

## 2. What ran on 2026-10-28, in order

| Step | Result |
| --- | --- |
| `benchmark discovery ... --dry-run` | `eligible: true`; 40 executions, 80 max attempts |
| Macro approval digests | `prepare-macro-review` re-derived `implementation`, `schema`, `effect_catalog`, `evaluator`; all four equal `hmda-v2-macro-approval.json` (Leila Jalali, 2026-10-07) |
| Live discovery with the original `.env` key | `AuthenticationError` HTTP 401 `invalid_api_key` on every call; halted after 4 attempts; retained at `hmda-v2/discovery-credential-rejected-2026-10-28/`; no billable request |
| Key rotated by the author; resumed into that directory | first execution raised `agents.exceptions.MaxTurnsExceeded: Max turns (8) exceeded`; the runner then crashed with `LedgerConflict` because the re-attempt reused the October failed-attempt id `...:attempt:0` with different content. That attempt's failure row was lost (up to 8 provider requests, at most 0.0354 USD, unledgered). Fixed: resumed runs now number attempts after retained failures (`_prior_failed_attempts`, tested) |
| Fresh `hmda-v2/discovery/` with `--max-model-requests 20`, reservation 0.09, cap 7.2, stop after 2 | 2 attempts, both `ModelBehaviorError`; halted |
| One diagnostic execution outside the ledger (to read the full error) | `ModelBehaviorError`: the final JSON parses but every `special_states.<field>` entry is `{"code": ..., "label": ...}` where the schema requires one of `NA`, `EXEMPT`, `UNAVAILABLE`, `NOT_APPLICABLE` (`literal_error` on eight fields); at most 20 requests, at most 0.0886 USD |
| Resumed `hmda-v2/discovery/` with stop after 6 | 6 more attempts on three groups, all `ModelBehaviorError`; halted. 8/8 attempts across 3 groups failed the same way |

The request bound was raised from the default 8 to 20 because the HMDA oracle requires all
five snapshot tools and the frozen settings use `parallel_tool_calls=False`, so a correct
answer needs at least six turns before the final message. `--max-model-requests` is a
runner argument that scales the reservation and the worst-case cost; it is not part of the
frozen protocol, whose per-request ceilings (16000 input tokens, 1024 output tokens) are
unchanged.

## 3. Why the study stopped here

The model reports the requested fields inside `special_states` as code/label objects,
which is a natural reading of an answer type that has no other slot for requested fields.
The gold constructor (`benchmarks/gold.py`) instead places in `special_states` only the
requested fields whose public value is `NA`, `1111`, empty, or the exempt/not-applicable
denial-reason codes, as a bare state string (the retained gold has 0 to 3 entries per
case). Strict mode would have made the provider enforce the value type, but strict mode
cannot express a free-form mapping (section 1), and in non-strict mode the provider only
receives the schema as guidance.

Every remedy changes `benchmarks/runtime.py`: either the HMDA prompt (which is silent
about the `special_states` contract) or the `HmdaAnswer` type (for example an explicit
list of `{field, state}` pairs that strict mode can express). The signed macro approval's
`evaluator_digest` hashes `benchmarks/runtime.py` together with the schema, oracle, gold
constructor, and retained gold, so either change invalidates the approval and requires a
fresh review by a reviewer distinct from the author. The study manifest is frozen with the
current schema. That is a protocol and approval decision, so the operator stopped rather
than editing an approval-bound file. No protocol check was loosened.

Recommended path: amend the prompt (smallest change; the answer type and the 420 retained
gold records stay as they are) with one sentence stating the `special_states` contract,
regenerate the review materials, obtain a new signed approval, then re-run discovery from
a fresh directory. If the amended prompt still fails, the answer type must change and the
gold must be regenerated, which is a larger review.

## 4. Spend

Billable spend is bounded, not measured: the runner does not price failed attempts
(`provider_request_count_known: false`). Upper bounds at the frozen per-request ceiling
(0.0044288 USD): eight ledgered attempts at 20 requests, 0.71 USD; one unledgered
`MaxTurnsExceeded` attempt at 8 requests, 0.04 USD; one diagnostic execution at 20
requests, 0.09 USD; four credential-rejected attempts, 0. Worst case 0.84 USD in total.
The runner records no usage for a failed attempt, so the real figure is known only to be
at or below that bound. Nothing was charged against the 60 USD authorization for a
completed execution, because none completed.

## 5. Commands to complete the study once the schema question is settled

Run from the repository checkout. `CLI` stands for
`PYTHONPATH=src .venv/bin/python -m guarded_agentic_compaction.cli benchmark` (the console
script's shebang points at the pre-rename venv path).

```bash
PROTO=paper/results/multidomain/protocol/hmda-v2-frozen.json
COMMON='--cases hmda=paper/results/multidomain/preflight/hmda/cases.jsonl
  --pool hmda=paper/results/multidomain/preflight/hmda
  --model gpt-5.6-luna --pricing paper/results/multidomain/pricing/gpt-5.6-luna-2026-10-07.json
  --max-model-requests 20 --reservation-usd-per-execution 0.09 --stop-after-consecutive-failures 4'
OUT=paper/results/multidomain/hmda-v2
APPROVAL=paper/results/multidomain/review/hmda-v2-macro-approval.json   # must be re-signed first
```

Phase schedule from the frozen protocol, the cap each phase needs at 20 requests and a
0.09 USD reservation (executions x 2 attempts x 0.09; the runner refuses a lower cap), and
the worst-case token cost at the frozen ceilings:

| Phase | Executions | Minimum cap (USD) | Worst case, no retry (USD) | Worst case, 1 retry (USD) |
| --- | ---: | ---: | ---: | ---: |
| discovery | 40 baseline | 7.20 | 3.54 | 7.09 |
| development | 30 baseline | 5.40 | 2.66 | 5.31 |
| pilot | 12 x {baseline, grc, macro} = 36 | 6.48 | 3.19 | 6.38 |
| artifact-calibration | 100 x {baseline, grc} = 200 | 36.00 | 17.72 | 35.43 |
| portfolio-calibration | 75 x 3 = 225 | 40.50 | 19.93 | 39.86 |
| test (incl. 20-group x 3 repeat cohort) | 420 | 75.60 | 37.20 | 74.40 |

Discovery through artifact-calibration needs 55.08 USD in caps, within a 60 USD
authorization; portfolio-calibration and test need a further 116.1 USD in caps (worst case
with retries 114.3 USD; realistic cost a small fraction). Use a fresh `$OUT` tree for the
re-run so that the halted ledgers here stay as history.

```bash
# 1. discovery
CLI discovery $PROTO $COMMON --max-provider-usd 7.2 --out $OUT/discovery
# 2. development
CLI development $PROTO $COMMON --max-provider-usd 5.4 --out $OUT/development
# 3. compile the shadow GRC registry from the two retained ledgers (no provider calls)
CLI compile-grc $PROTO --ledger hmda=$OUT/discovery/ledger.jsonl \
  --ledger hmda=$OUT/development/ledger.jsonl --out $OUT/registries
# 4. freeze shadow action identities
CLI freeze-actions $PROTO --cases hmda=paper/results/multidomain/preflight/hmda/cases.jsonl \
  --pool hmda=paper/results/multidomain/preflight/hmda --model gpt-5.6-luna \
  --pricing paper/results/multidomain/pricing/gpt-5.6-luna-2026-10-07.json \
  --grc-stage shadow --registry hmda=$OUT/registries/hmda --macro-approval hmda=$APPROVAL \
  --out $OUT/pilot/frozen-shadow-actions.json
# 5. pilot: dry-run, then live
CLI pilot $PROTO $COMMON --registry hmda=$OUT/registries/hmda --macro-approval hmda=$APPROVAL \
  --action-lock $OUT/pilot/frozen-shadow-actions.json --max-provider-usd 6.48 --out $OUT/pilot --dry-run
CLI pilot $PROTO $COMMON --registry hmda=$OUT/registries/hmda --macro-approval hmda=$APPROVAL \
  --action-lock $OUT/pilot/frozen-shadow-actions.json --max-provider-usd 6.48 --out $OUT/pilot
# 6. artifact calibration (shadow GRC executes only here and in the pilot)
CLI artifact-calibration $PROTO $COMMON --registry hmda=$OUT/registries/hmda \
  --macro-approval hmda=$APPROVAL --action-lock $OUT/pilot/frozen-shadow-actions.json \
  --max-provider-usd 36.0 --out $OUT/artifact-calibration
```

Stop after step 6. The approver packet is then assembled from
`$OUT/registries/hmda/compile-report.json` (artifact and candidate counts, rejection
stages, the compiled read prefix and which arguments are grounded on which prior results),
`$OUT/pilot/summary.json` (`full_study_cost_projection`), and
`$OUT/artifact-calibration/summary.json` plus its ledger (per-artifact support,
quality-failure, and abstention counts over the 100 frozen baseline-versus-GRC pairs).
Append those numbers to this note before handing it over.

## 6. Independent approver step (not the author, not this agent)

`calibrate-grc` consumes the artifact-calibration ledger and the shadow registry, applies
exact 99% per-artifact quality non-inferiority over the 100 frozen pairs with Bonferroni
control across artifacts, and emits an `ACTIVE` registry bound to a named human approver
and an expiry day. The approver reviews, in this order: the signed macro approval, the
compile report (what the GRC reads and why each argument is admissible), the
artifact-calibration summary and ledger (quality failures per artifact, abstentions, any
`execution_failed` rows and their retained reasons), and the `freeze-actions` lock. Then:

```bash
CLI calibrate-grc $PROTO --ledger hmda=$OUT/artifact-calibration/ledger.jsonl \
  --registry hmda=$OUT/registries/hmda --approved-by "<approver full name>" \
  --expiry-day <YYYY-MM-DD> --out $OUT/calibrated-registries
```

The runner enforces only a non-empty approver distinct from the job identity and an
expiry strictly in the future; it cannot tell the author's name from an independent one,
so independence is a human obligation, as it was for the macro approval.

## 7. Remaining phases after approval

```bash
CLI freeze-actions $PROTO --cases hmda=paper/results/multidomain/preflight/hmda/cases.jsonl \
  --pool hmda=paper/results/multidomain/preflight/hmda --model gpt-5.6-luna \
  --pricing paper/results/multidomain/pricing/gpt-5.6-luna-2026-10-07.json \
  --grc-stage active --registry hmda=$OUT/calibrated-registries/hmda \
  --macro-approval hmda=$APPROVAL --out $OUT/calibration/frozen-active-actions.json

CLI portfolio-calibration $PROTO $COMMON --registry hmda=$OUT/calibrated-registries/hmda \
  --macro-approval hmda=$APPROVAL --action-lock $OUT/calibration/frozen-active-actions.json \
  --max-provider-usd 40.5 --out $OUT/portfolio-calibration

CLI calibrate $PROTO --ledger $OUT/portfolio-calibration/ledger.jsonl \
  --out $OUT/calibration/frozen-portfolio.json

CLI test $PROTO $COMMON --registry hmda=$OUT/calibrated-registries/hmda \
  --macro-approval hmda=$APPROVAL --policy $OUT/calibration/frozen-portfolio.json \
  --action-lock $OUT/calibration/frozen-active-actions.json \
  --max-provider-usd 75.6 --out $OUT/test

CLI analyze $PROTO --policy $OUT/calibration/frozen-portfolio.json \
  --effort <reviewed construction-effort.json> --ledger $OUT/test/ledger.jsonl \
  --out $OUT/analysis
```

Once portfolio calibration starts, any code, prompt, tool, evaluator, registry,
approval, model, pricing, SDK, or source change requires a new protocol. The
`construction-effort.json` must be reviewed before `analyze`; none exists yet for HMDA.
