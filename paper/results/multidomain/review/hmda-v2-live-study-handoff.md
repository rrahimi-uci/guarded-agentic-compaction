# HMDA v2 live study handoff (2026-10-28)

**Status:** The study is still at the discovery phase. 0 of 40 discovery executions have
completed. The October 7 failure is diagnosed and already fixed in code; the October 28
attempt is blocked by a rejected credential, not by code or protocol. No GRC artifact has
been compiled, no pilot has run, and no artifact-calibration summary exists, so the
`calibrate-grc` approval packet cannot be assembled yet. This note records exactly what
was found, what ran, and the commands that complete the study, so that the next operator
(with a valid key) and the independent approver can act without reconstructing it.

## 1. Root cause of the 2026-10-07 discovery failure

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
invoked, which is why all 80 attempts failed within one second and why no provider request
occurred. Commit `3ce76b8` (15:22 PDT, six minutes after the 15:16 PDT run) added
`_output_schema()`, which wraps exactly such types in the SDK's non-strict
`AgentOutputSchema`; `tests/unit/test_multidomain_output_schema.py` pins that behavior.
The same provider-free replay against the current runner proceeds to the provider request
(`openai.APIConnectionError` against the unreachable URL). This was a code defect, already
fixed; the retained ledger simply predates the fix and was never re-run.

Two operational gaps made the failure expensive to read, and this branch closes them in
`paper/scripts/multidomain_study.py` (with `tests/unit/test_multidomain_failure_visibility.py`):

- `_report_failure()` prints one bounded, credential-masked line per failed attempt to
  stderr (`execution failed: <domain>:<case>:<action> attempt n: <module>.<Type>: <message>`).
  The ledger payload is unchanged; it still records only the class name.
- `--stop-after-consecutive-failures N` (default 0 = historical behavior) halts the phase
  after N back-to-back failures, records `summary.halted`, and leaves every attempt in the
  ledger so a later run resumes the open groups.

## 2. What ran on 2026-10-28

| Step | Result |
| --- | --- |
| `benchmark discovery ... --dry-run` | `eligible: true`; 40 executions, 80 max attempts, reservation 0.04 USD/attempt (computed worst case 0.0354304), cap 4.00 USD; `paper/results/multidomain/hmda-v2/discovery/preflight.json` |
| Macro approval digests | `prepare-macro-review` re-derived `implementation`, `schema`, `effect_catalog`, `evaluator` digests; all four equal `hmda-v2-macro-approval.json` (Leila Jalali, 2026-10-07) |
| One diagnostic execution with the configured key | `openai.AuthenticationError` HTTP 401 `invalid_api_key` (out of ledger; no tokens) |
| Two `models.retrieve` calls | both HTTP 401 `invalid_api_key` (free endpoint) |
| `benchmark discovery` live, `--stop-after-consecutive-failures 4` | halted after 4 attempts on 2 groups, all `AuthenticationError`; ledger retained at `paper/results/multidomain/hmda-v2/discovery/ledger.jsonl`; 0 completed; no billable request |

Spend: 0.00 USD billable. The 0.16 USD `committed_usd` in the halted summary is the
replayed reservation for the four rejected attempts. The `OPENAI_API_KEY` in the main
checkout's `.env` (last modified 2026-10-07 07:41) is rejected by the provider; it must be
rotated before any phase can run. Nothing else was found to block the study.

## 3. Commands to complete the study

Run from the repository checkout with the venv on `PYTHONPATH=src`. The console script's
shebang points at the pre-rename venv path, so use the module form. `CLI` below stands
for `PYTHONPATH=src .venv/bin/python -m guarded_agentic_compaction.cli benchmark`.

```bash
PROTO=paper/results/multidomain/protocol/hmda-v2-frozen.json
COMMON='--cases hmda=paper/results/multidomain/preflight/hmda/cases.jsonl
  --pool hmda=paper/results/multidomain/preflight/hmda
  --model gpt-5.6-luna --pricing paper/results/multidomain/pricing/gpt-5.6-luna-2026-10-07.json
  --reservation-usd-per-execution 0.04 --stop-after-consecutive-failures 4'
OUT=paper/results/multidomain/hmda-v2
APPROVAL=paper/results/multidomain/review/hmda-v2-macro-approval.json
```

Phase schedule from the frozen protocol (provider-free computation), the cap each phase
needs (the runner refuses a cap below the maximum scheduled reservation, i.e. executions
x 2 attempts x 0.04), and the worst-case token cost at the frozen ceilings:

| Phase | Executions | Minimum cap (USD) | Worst case, no retry (USD) | Worst case, 1 retry (USD) |
| --- | ---: | ---: | ---: | ---: |
| discovery (resumes the halted ledger) | 40 baseline | 3.20 | 1.42 | 2.83 |
| development | 30 baseline | 2.40 | 1.06 | 2.13 |
| pilot | 12 x {baseline, grc, macro} = 36 | 2.88 | 1.28 | 2.55 |
| artifact-calibration | 100 x {baseline, grc} = 200 | 16.00 | 7.09 | 14.17 |
| portfolio-calibration | 75 x 3 = 225 | 18.00 | 7.97 | 15.94 |
| test (incl. 20-group x 3 repeat cohort) | 420 | 33.60 | 14.88 | 29.76 |

The 60 USD authorization for discovery through artifact-calibration is sufficient (caps
4.0 + 3.0 + 3.0 + 16.0 = 26.0 USD; worst case with retries 21.7 USD). Portfolio
calibration and test need a separate authorization of at least 51.6 USD in caps
(worst case with retries 45.7 USD).

```bash
# 1. discovery (resumes paper/results/multidomain/hmda-v2/discovery; same reservation)
CLI discovery $PROTO $COMMON --max-provider-usd 4.0 --out $OUT/discovery

# 2. development
CLI development $PROTO $COMMON --max-provider-usd 3.0 --out $OUT/development

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
  --action-lock $OUT/pilot/frozen-shadow-actions.json --max-provider-usd 3.0 --out $OUT/pilot --dry-run
CLI pilot $PROTO $COMMON --registry hmda=$OUT/registries/hmda --macro-approval hmda=$APPROVAL \
  --action-lock $OUT/pilot/frozen-shadow-actions.json --max-provider-usd 3.0 --out $OUT/pilot

# 6. artifact calibration (shadow GRC executes only here and in the pilot)
CLI artifact-calibration $PROTO $COMMON --registry hmda=$OUT/registries/hmda \
  --macro-approval hmda=$APPROVAL --action-lock $OUT/pilot/frozen-shadow-actions.json \
  --max-provider-usd 16.0 --out $OUT/artifact-calibration
```

Stop after step 6. What the artifact-calibration run leaves for the approver:
`$OUT/registries/hmda/compile-report.json` (artifact and candidate counts, rejection
stages, the compiled read prefix and which arguments are grounded on which prior
results), `$OUT/pilot/summary.json` (`full_study_cost_projection`), and
`$OUT/artifact-calibration/summary.json` plus its ledger, from which the per-artifact
pass/abstain/wrong counts, replay results, and the 100 frozen baseline-versus-GRC pairs
are derived by `calibrate-grc` itself. Append those numbers to this note before handing
it over.

## 4. Independent approver step (not the author, not this agent)

`calibrate-grc` consumes the artifact-calibration ledger and the shadow registry, applies
exact 99% per-artifact quality non-inferiority over the 100 frozen pairs with Bonferroni
control across artifacts, and emits an `ACTIVE` registry bound to a named human approver
and an expiry day. The approver reviews, in this order: the signed macro approval (the
four digests above), `compile-report.json` (what the GRC reads and why each argument is
admissible), the artifact-calibration summary and ledger (quality failures per artifact,
abstentions, any `execution_failed` rows and their retained reasons), and the
`freeze-actions` lock. Then:

```bash
CLI calibrate-grc $PROTO --ledger hmda=$OUT/artifact-calibration/ledger.jsonl \
  --registry hmda=$OUT/registries/hmda --approved-by "<approver full name>" \
  --expiry-day <YYYY-MM-DD> --out $OUT/calibrated-registries
```

The runner enforces only a non-empty approver distinct from the job identity and an
expiry strictly in the future; it cannot tell the author's name from an independent one,
so independence is a human obligation, as it was for the macro approval.

## 5. Remaining phases after approval

```bash
CLI freeze-actions $PROTO --cases hmda=paper/results/multidomain/preflight/hmda/cases.jsonl \
  --pool hmda=paper/results/multidomain/preflight/hmda --model gpt-5.6-luna \
  --pricing paper/results/multidomain/pricing/gpt-5.6-luna-2026-10-07.json \
  --grc-stage active --registry hmda=$OUT/calibrated-registries/hmda \
  --macro-approval hmda=$APPROVAL --out $OUT/calibration/frozen-active-actions.json

CLI portfolio-calibration $PROTO $COMMON --registry hmda=$OUT/calibrated-registries/hmda \
  --macro-approval hmda=$APPROVAL --action-lock $OUT/calibration/frozen-active-actions.json \
  --max-provider-usd 18.0 --out $OUT/portfolio-calibration

CLI calibrate $PROTO --ledger $OUT/portfolio-calibration/ledger.jsonl \
  --out $OUT/calibration/frozen-portfolio.json

CLI test $PROTO $COMMON --registry hmda=$OUT/calibrated-registries/hmda \
  --macro-approval hmda=$APPROVAL --policy $OUT/calibration/frozen-portfolio.json \
  --action-lock $OUT/calibration/frozen-active-actions.json \
  --max-provider-usd 33.6 --out $OUT/test

CLI analyze $PROTO --policy $OUT/calibration/frozen-portfolio.json \
  --effort <reviewed construction-effort.json> --ledger $OUT/test/ledger.jsonl \
  --out $OUT/analysis
```

Once portfolio calibration starts, any code, prompt, tool, evaluator, registry,
approval, model, pricing, SDK, or source change requires a new protocol. The
`construction-effort.json` must be reviewed before `analyze`; none exists yet for HMDA.
