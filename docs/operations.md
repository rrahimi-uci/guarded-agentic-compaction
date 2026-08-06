# Operations

Running compaction in front of a live agent. The order is not negotiable: capture, declare
effects, estimate, compile and *read*, shadow, then a narrow canary.

## The six-step adoption recipe

| step | you do | stop if |
|---:|:---|:---|
| 1 | **Capture.** One authoritative tracer, sampling 1.0 for the mining window. ≥100 episodes over ≥5 groups. | you cannot see model-request boundaries, or payloads are truncated |
| 2 | **Declare effects.** Write `effects.yaml` for the most-called tools. Everything undeclared is `UNKNOWN`. | your tool surface is mostly writes |
| 3 | **Estimate.** `guarded-agentic-compaction estimate`. Read `n_B`, the ceiling, and what is blocked and why. | the oracle ceiling is below ~5% |
| 4 | **Compile and read.** `compile` then `explain`. A human reads every program. | you cannot read an artifact and say what it does |
| 5 | **Shadow.** `mode="shadow"`. Score and log what *would* have dispatched. Zero behaviour change. | shadow ρ < 0.9, or shadow φ far below the dev estimate |
| 6 | **Go live narrowly.** `mode="live"` with the smallest artifact set clearing the gate. | any committed forbidden effect, ever |

Run step 3 *before* step 2 is finished: the estimator attributes blocked windows by tool,
so the catalog gets written in descending order of value rather than alphabetically.

## Artifacts are build outputs, not assets

Every artifact pins the model, prompt, tool-schema, policy, guardrail, effect-catalog and
entry-contract hashes. A prompt edit invalidates the registry, every dispatch misses, and
coverage decays to zero — silently and correctly, because failing closed produces no error.

So compilation belongs in CI:

1. a prompt or schema change lands on a branch;
2. CI recompiles from the last *N* days of traces and **diffs the registry** against the
   previous revision (`guarded-agentic-compaction diff`): artifacts gained, lost, coverage delta;
3. the new registry deploys in `mode="shadow"` and must accumulate its promotion evidence
   before any live dispatch;
4. the previous signed registry stays resolvable for atomic pointer rollback.

A team that cannot afford a shadow window per prompt change should not deploy this system.
That constraint is a reasonable filter, not a defect.

## Promotion

`discovered → synthesized → replay_validated → shadow → approved → active → retired`

One stage at a time. Promotion to `approved` or `active` requires a human approval
identity **distinct** from the optimization job identity, and refuses the `train` and
`calibration` splits as promotion evidence. Both rules are enforced in code.

## Portfolio decisions are not deployment approval

`select_portfolio_action()` compares paired measurements and may return `baseline`, an
automatic action, or a review-required action. Before activation, call
`decision.permits(current_compatibility_key, review_approved=...)`. It returns false after
abstention, compatibility drift, or missing macro approval. The application remains
responsible for resolving `selected_action` to reviewed implementation code and for the
normal artifact lifecycle; the selector never generates or promotes a macro.

## Monitoring

Per artifact, alert on:

| signal | threshold | action |
|:---|:---|:---|
| verifier pass rate ρ | < 0.90 | retire the artifact |
| coverage φ | < half the dev estimate | investigate drift, then retire |
| unsafe dispatch (contract violation) | any | retire immediately, open an incident |
| `INCIDENT` outcomes | any | kill switch, then incident runbook |
| guard-miss reasons | a new dominant reason | the workload moved; recompile |
| gate score distribution | shift in the accepted mass | drift; recalibrate on fresh groups |
| artifact age | past `expiry_day` | automatic retirement |

Telemetry is emitted per boundary: `attempts`, `dispatch_attempts`, `compacted`,
`baseline`, `incidents`, `gate_rejections`, `guard_misses` by reason, `verifier_failures`
by clause, `interp_failures` by cause, `shadow_would_dispatch`,
`shadow_would_dispatch_rate`, and overhead in milliseconds. Shadow coverage must use the
`shadow_would_dispatch*` fields: `compacted` deliberately remains zero because shadow mode
executes nothing.

## Incident runbook

1. **Stop dispatch.** Set `registry.kill_switch = True` (or deploy the previous registry
   pointer). Dispatch stops within one boundary; the agent continues on the baseline.
2. **Classify.** `BASELINE` outcomes are not incidents — they are the design working. An
   incident is a verifier failure with a dirty staging snapshot, or a committed effect the
   catalog did not license.
3. **Freeze evidence.** The `ExecutionRecord` for the episode, the artifact's evidence
   bundle, the effect multiset actually executed, and the staging diff reasons.
4. **Attribute.** Compare the artifact's `compatibility_key` with the live manifest. A
   mismatch means an artifact outlived a workflow change; the guard should have refused, so
   the capture path is suspect.
5. **Retire, do not patch.** Artifacts are immutable. Retire, fix the input (catalog,
   allowlist, grouping), recompile, and re-enter at shadow.
6. **Rollback exercise.** Practise the pointer rollback on a schedule, not during an
   incident.

Exact restoration of unmodified model-visible history requires an outer controller that
owns staging. `CompactingModel` delegates unsupported inputs safely, but an already emitted
SDK response may be recorded in SDK-managed history; use `CompactingRunner` and a
continuation contract when the stronger rollback claim matters.

## Rollback

`rollback(registry, actor=..., reason=...)` retires every active artifact and returns the
previous registry. Keep the original workflow and the previous registry warm: the fallback
path must be the *tested* path, not a code path that only runs during outages.

## Costs to keep in the ledger

Model API charges are the smallest line. Also count offline optimization compute, shadow
traffic, monitoring, engineering time, and per-artifact maintenance. The economic gate in
the estimator uses all of them, and the break-even is usually tens of thousands of episodes
per day on a stable prompt.
