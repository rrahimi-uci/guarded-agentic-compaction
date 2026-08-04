# ADR 0008: Provider-backed demos are the primary efficiency evidence

Status: accepted, 2026-08-02

## Decision

All user-facing demonstrations execute through the OpenAI Agents SDK and produce
native provider traces. Support, permissioned RAG, and incident triage use
deterministic fictional service fixtures so no customer data is disclosed. The MCP
negative control uses a real local stdio MCP server. Synthetic scripted policies remain
only for scalable offline stress, calibration, perturbation, and fault-injection tests.

The default live model is `gpt-5.6-terra` at low reasoning effort. It is configurable
through `AGENT_COMPACTION_LIVE_MODEL`. The runner loads `OPENAI_API_KEY` from the
environment or `.env`, never prints it, and never writes it into result artifacts.

## Rationale

The deterministic substrate can validate compiler mechanics and rare safety paths, but
it cannot measure provider token usage, model latency, real tool selection, handoffs,
or SDK compatibility. Conversely, a small provider run cannot supply the thousands of
independent groups needed for calibrated risk bounds. Both evidence layers are retained
and labeled instead of treating one as a substitute for the other.

## Conditions

- `baseline`: the provider chooses and executes each tool through the normal SDK loop.
- `compacted`: `CompactingModel` emits the approved native function calls; the SDK still
  executes and traces tools, and the provider performs final synthesis.
- `compacted_fallback`: the MCP catalog has undeclared effects, so the runtime keeps the
  original provider loop.

Live artifacts are execution demonstrations with no production calibration certificate.
They must not be promoted outside the fictional fixture environment.

## Consequences

- Efficiency claims in `docs/live-results.md` are provider-measured.
- Quality evidence remains small-n and scenario-specific.
- Cost is an estimate from published standard pricing, not an account invoice.
- Offline results in `docs/results.md` remain useful but are no longer the primary demo
  evidence.

