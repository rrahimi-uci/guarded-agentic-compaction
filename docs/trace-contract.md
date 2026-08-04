# Trace contract

What the application must supply, what the SDK already gives you, and why the
difference is not negotiable.

## Division of labour

The OpenAI Agents SDK already emits traces for runner and task boundaries, turns,
generations, function calls, guardrails, and handoffs. The library's secondary
`AgentsTraceProcessor` normalizes those observable spans without replacing the SDK's
default exporter. Neither the SDK nor the processor can infer the seven application-owned
facts below; without them the compiler is unsound rather than merely limited.

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

## One authoritative compiler input

The SDK may continue to export its own observability traces while the library's secondary
processor collects an in-process normalization stream. The application must nevertheless
designate exactly one compiler-input path. Feeding both streams into the Episode store
would duplicate or fragment the same execution evidence.

`AgentsTraceProcessor` is non-blocking. After a run, call `drain()`, join each completed
record with the application-owned envelope, manifest, entry state, and outcome, then persist
the resulting Episodes with `write_jsonl()`. Short-lived jobs must drain before shutdown and
must treat a non-zero `processor.dropped` count as an incomplete capture. `force_flush()` is
present for SDK processor compatibility but has no remote queue to flush. Canonical JSONL
writes validate all Episodes before an atomic snapshot replacement; they do not reconcile a
separate tracing service.

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
