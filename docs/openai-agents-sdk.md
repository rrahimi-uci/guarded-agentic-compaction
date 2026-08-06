# OpenAI Agents SDK integration

The OpenAI Agents SDK is an execution substrate; `guarded-agentic-compaction` consumes its
observable traces and can wrap its model boundary. The optimizer keeps its own typed IR
so the same analysis can support other frameworks.

Official SDK guidance describes built-in tracing for generations, tool calls, handoffs,
guardrails, and custom spans. Trace evaluation can then score workflow-level behavior:
[Agents SDK guide](https://developers.openai.com/api/docs/guides/agents),
[observability integration](https://developers.openai.com/api/docs/guides/agents/integrations-observability),
and [trace grading](https://developers.openai.com/api/docs/guides/trace-grading).

## Install

```bash
pip install 'guarded-agentic-compaction[live]'
```

The current optional dependency range is `openai-agents>=0.19,<0.20`. Re-run the SDK
conformance suite before widening it.

## Run the provider-backed demonstrations

```bash
cp .env.example .env
# set OPENAI_API_KEY in .env without committing it
python experiments/live_run.py --cases 3
```

This executes support, permissioned RAG, multi-agent triage, and an actual stdio MCP
negative control. It writes provider-measured evidence to
`experiments/live_results/` and [live-results.md](live-results.md). Fictional fixtures
are sent to the model; the credential is not logged or persisted.

## Run the real public-record portfolio study

The publication study uses live SDK/provider execution over a pinned snapshot of real
public GitHub issues. Inspect the frozen selection and fresh cohort without provider calls,
then explicitly approve the reviewed macro for the paid paired run:

```bash
.venv/bin/python paper/scripts/portfolio_live_study.py \
    --preflight --cases-per-class 4
.venv/bin/python paper/scripts/portfolio_live_study.py \
    --cases-per-class 4 --approve-reviewed-macro
```

The retained result is sufficient to rebuild the paper; repeating the second command
spends API credits and may change latency and generated text. The tools read deterministic
snapshot records, not the live GitHub service. See the [paper README](../paper/README.md)
for the complete protocol and evidence boundary.

The later GCS study uses a different SDK integration: the outer controller executes one
admitted composite before the first provider request, then sends its projected observation
to an agent with no tool surface. Reproduce the provider-free compiler/replay audit or the
paid real-record comparison with:

```bash
.venv/bin/python paper/scripts/validate_guarded_composite.py
# Paid and nondeterministic; requires OPENAI_API_KEY in .env.
.venv/bin/python paper/scripts/github_gcs_live_study.py --smoke
.venv/bin/python paper/scripts/github_gcs_live_study.py --cases 12
```

`execute_pre_model()` is framework-neutral—the application still owns conversion of its
projected observation into SDK input. GCS pins the continuation manifest (model, prompt,
tools, policies, guardrails, and entry contract) and refuses before any tool executes when
that identity differs. The retained paid result used real OpenAI calls and a pinned public
GitHub snapshot; it did not use simulated agent decisions.

## Capture

```python
from guarded_agentic_compaction.capture import (
    AgentsTraceProcessor,
    episode_from_agents_trace,
    install_agents_trace_processor,
)

processor = install_agents_trace_processor(
    AgentsTraceProcessor(include_sensitive_data=False)
)
```

Sensitive payload capture is off by default. The resulting structural trace is useful
for operations but intentionally fails compiler qualification until complete tool inputs
and outputs are joined from an application-controlled store. If the application enables
sensitive capture, it must enforce retention, access, redaction, and deletion policy.

When a trace finishes, join it to facts the SDK cannot infer:

```python
episode = episode_from_agents_trace(
    processor.drain()[0],
    envelope=envelope,          # group, tenant, principal, policy, privacy class
    manifest=manifest,          # model/prompt/tool/policy/catalog identities
    entry_state=contract.project(application_state),
    outcome=joined_outcome,
    final_state_digest=state_digest,
)
```

Use stable scenario or conversation identities for `group_id`; spans are not independent
statistical samples. `EntryStateContract` should allowlist only facts available before
the optimized boundary. Hidden chain-of-thought is neither required nor represented.

## Runtime path 1: custom Model

`CompactingModel` wraps an SDK `Model`. On an accepted straight-line plan it emits one
native function call per SDK turn; the ordinary SDK runner executes the tool, so tool
dispatch and tracing remain native. On a miss it delegates to the wrapped model.

```python
from agents import Agent
from guarded_agentic_compaction.runtime.model_provider import CompactingModel

model = CompactingModel(
    base_model,
    registry=registry,
    catalog=catalog,
    manifest=manifest,
    mode="shadow",
    entry_state_fn=entry_state_from_sdk_input,
    partition_fn=partition_from_sdk_input,
)

agent = Agent(name="support", model=model, tools=local_function_tools)
```

Start with `mode="shadow"`. A `SHADOW` lifecycle artifact is visible to shadow resolution
but cannot execute in live mode; live resolution accepts only `ACTIVE` artifacts.

The model adapter supports non-streaming, straight-line local function tools. It bypasses
compaction for handoffs, server-managed continuation, streaming, hosted tools, MCP tools,
loops, and assertions. This preserves the baseline application but means those surfaces
receive no compaction benefit. Post-emission rollback is structurally limited because the
SDK may already have recorded the emitted call in session history.

`CompactingModel` subclasses the SDK's `Model` base and retains an in-flight plan by the
native trace id. This is necessary because successive `Runner` turns may execute in
sibling async contexts where a `ContextVar` alone does not survive. Direct callers that
have no SDK trace continue to use the context-local fallback.

## Runtime path 2: staging owner

`CompactingRunner` demonstrates the preferred outer-controller contract: snapshot state,
execute a whole region through a checked tool façade, verify it, and commit only after a
clean result. It is a framework-neutral host controller, not a drop-in subclass of the
SDK's `Runner`; an application adapter must connect its own state, history, budget,
permission context, and tool executor.

Use this path when exact pre-commit deoptimization matters. A live region containing a
quota-attested read is rejected unless the caller supplies a reversibility snapshot.

For a GCS artifact, `CompactingRunner.execute_pre_model()` additionally requires
`composite.pre_model=True` and the exact `continuation_compatibility_key`. On success it
returns one `CompactedObservation` whose tool name is the synthesized composite and whose
result is the bounded projection. Internal tool calls remain available in dispatch
provenance and metrics. On any guard, gate, verifier, projection, or continuation mismatch,
it returns no observation and executes no continuation-specific shortcut.

### Post-model continuation boundary

The SDK's tool trace can prove that a compiled region emitted grounded calls and results;
it cannot prove that the next model response copied or interpreted those results correctly.
Configure `CompactingRunner.continuation_guard` and call `on_continuation()` before adding
the candidate response to SDK/application history when an end-to-end claim matters. The
guard accepts a caller-defined contract, an optional deterministic checked renderer, and
an optional baseline callback. Every recovery is revalidated; otherwise the result is
`REJECTED` and contains no output.

This hook belongs on the outer-controller path. `CompactingModel` may already have emitted
items into SDK-managed history and therefore cannot promise exact post-emission recovery.
Handoffs, streamed responses, and server-managed continuations remain baseline-only unless
their owning runtime exposes an equivalent reversible boundary.

## Conformance and failure behavior

The integration suite checks:

- off mode delegates with unchanged model-visible input;
- hits emit deterministic, schema-valid native function calls;
- tool outputs advance bindings in order;
- plan exhaustion returns control to the wrapped model;
- shadow mode logs and executes nothing;
- unexposed, hosted, MCP, streaming, and handoff surfaces bypass compaction;
- invalid runtime modes raise instead of falling through to live behavior.

A guard, gate, lifecycle, signature, effect, tool-surface, binding, or verifier failure
falls back to the baseline. A verifier failure after an unattestable external commitment
is an `INCIDENT`, never mislabeled as a clean fallback.

### Two things that will silently cost you the whole benefit

**Keep one instruction for both outcomes.** It is tempting to specialize the compacted
prompt — "the runtime has already executed an approved evidence plan, use only the
observed evidence". That is sound only while compaction is guaranteed, and it never is:
a guard miss, a schema change or an unsupported program shape returns control to the
same agent, now holding an instruction that describes evidence it does not have. Demo E
measured this directly: with a specialized prompt its three *correct refusals* scored
0.33–0.75 instead of 1.00. With one shared instruction all four conditions score 1.000.
Demos A and B still specialize, and carry the same latent exposure.

**A quota-attested read cannot be dispatched through this adapter at all.** If any tool
in a program is declared `quota_attested: true`, the dispatcher demands a reversibility
snapshot before every live dispatch. `CompactingModel` owns no staging boundary and
supplies none, so every boundary fails closed with `missing_reversibility_snapshot` and
the only symptom is a telemetry counter — the application keeps working and the savings
never appear. Check `dispatcher.telemetry.guard_misses` in shadow mode before concluding
that an artifact is ineffective, and use `CompactingRunner` for these workloads.

## Multi-agent optimization

SDK handoff spans remain trace barriers for GRC. TGWS may learn an entry-time route to a
specialized agent configuration, but it does not bypass an observed handoff or approval.
A future collaboration optimizer can implement `OptimizationPass`, consume handoff and
agent-span features, and emit a new artifact kind under the same grouped evaluation,
manifest pinning, calibration, and lifecycle contracts.
