# Trace contract

What the application must supply, what the SDK and MLflow already give you, and why the
difference is not negotiable.

## Division of labour

The OpenAI Agents SDK already traces runner and task boundaries, turns, generations,
function calls, guardrails and handoffs. MLflow already captures inputs, outputs, calls,
errors and assessments, and makes them searchable. Neither can infer the seven facts below,
and without them the compiler is unsound rather than merely limited.

| field | purpose | rule |
|:---|:---|:---|
| entry state | the values a rewrite may legally read | typed, allowlisted, redacted |
| principal / tenant partition | prevent cross-scope evidence leakage | stable pseudonym, never a secret |
| effect class | separate replay-safe reads from commitments | versioned catalog declaration |
| external-state version | establish compatible freshness | index/DB/API version or digest |
| approval scope | preserve the exact approved action | approval digest and typed scope |
| business outcome | evaluate quality beyond syntax | asynchronous join by episode id |
| execution manifest | prevent incompatible pooling | frozen at episode start |

## The IR

```text
TraceEnvelope(trace_id, episode_id, group_id, manifest_id, principal, tenant_partition,
              policy_version, day, privacy_class, entry_state_ref, outcome_ref,
              external_state_version, approval_scope)
ExecutionManifest(commit, model, prompt_hash, tools_hash, policy_hash, guardrail_hash,
                  effect_catalog_version, entry_contract_version, sdk_version,
                  tracer_version)
EventNode(node_id, parent_id, kind, actor, index, tool, schema_version, input, output,
          status, timing, usage, request_id, call_id, declared_effect, truncated, attrs)
OutcomeLabels(task_success, semantic_score, safety_events, business_metrics,
              label_latency_s)
Episode(envelope, manifest, entry_state, events, outcome, final_state_digest, attributes)
```

`EventKind` is `MODEL_REQ | MODEL_RESP | TOOL_CALL | TOOL_RESULT | HANDOFF | GUARDRAIL |
APPROVAL`. `MODEL_REQ` is the boundary that `n_B` counts and that compaction removes.

Data edges are established from **exact typed values**, declared mappings and schemas.
Fuzzy text similarity may propose a mapping for review; it can never prove groundability.

## Qualification

An episode is compiler-eligible only with: complete boundaries and manifest,
reconstructable order, paired tool calls and results, typed tool I/O, declared candidate
effects, a leakage-resistant group id, usable outcomes, and no truncation. Anything else
may inform operations but not an equivalence claim.

An **undeclared tool** blocks the *window* that contains it, not the whole episode — which
is why the data-quality report separates "compiler-eligible" from "of which fully
declared".

## Groups

`group_id` is the unit of statistical independence. Near-duplicate prompts, templates,
documents, users and workflow-generated variants must share one group, or the held-out set
is a copy of the training set with a different id. Where scenario ids do not exist, use a
conservative `principal + day + case/document hash` and report the sensitivity of every
result to coarser grouping.

Production has no scenario ids and repeated automated traffic inflates support, so support
is counted by group **and** principal **and** day.

## One authoritative tracer

Two exporters over one span tree produce duplicated or fragmented traces, and the MLflow
OpenAI autologger can clear existing SDK processors. `capture.configure` asserts a single
authoritative tracer, pins the MLflow version, and returns a capture manifest recording the
mode (`authoritative` vs `convenience`), the sampling ratio and the allowlist.

Authoritative capture also means **synchronous export or an explicit flush followed by
count reconciliation**: a short-lived job otherwise exits with traces still queued, and the
corpus silently loses episodes. `export_episodes` flushes and reconciles, and raises if the
store reports fewer traces than were written.

## What is never captured

Hidden chain-of-thought. The compiler consumes observable response items, tool calls,
handoffs, structured outputs, optional API-exposed reasoning summaries and outcomes.
Private reasoning is neither needed nor reconstructed.

## Data-quality report

Every snapshot emits one: episode and group counts, principal and day counts, span
completeness, manifest coverage, effect coverage, outcome coverage and label latency,
duplicate rate, schema drift, scope coverage, rejection reasons, and a Gate 0 verdict.

"Span completeness" counts episodes free of *any* span defect — truncation, missing tool
result, orphan result, missing boundary — not merely the truncation flag, because a dropped
result is the failure mode capture pipelines actually produce.
