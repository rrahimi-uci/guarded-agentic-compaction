# Implemented use cases and evidence boundaries

These scenarios describe what the current `agent-compaction` 0.7.0 code can do. They
replace the earlier v2.1 pseudo-API guide, whose `cx.*` examples and staged implementation
schedule predated the library. Every scenario below distinguishes measured evidence from
an adoption hypothesis.

## Choosing the right mechanism

| Workload shape | First choice | Why |
|:---|:---|:---|
| Stable, low-entropy reads with an obvious application interface | Hand-written macro | Simplest implementation and usually the fewest tool calls |
| Recurrent read region with enough evidence and a task-specific sufficient view | GCS | Synthesizes one guarded interface while preserving internal verification and provenance |
| Recurrent read region whose bindings or branches vary across families | GRC | Discovers and synthesizes guarded deterministic programs while preserving the existing tool interface |
| Entry-state-dependent prompt, model, agent, or tool surface | TGWS | Learns a shallow route and prunes only under measured quality |
| Several already measured actions | Portfolio selector | Chooses only among actions with paired group-level evidence; otherwise returns baseline |
| Writes, approvals, handoffs, unknown effects, unsupported streaming, or ungrounded arguments | Baseline/abstain | These are barriers, not opportunities to infer permission |

A portfolio recommendation does not synthesize a macro, cache, prompt, or model route. It
selects among measurements supplied by the application. Macros require human review by
default, and runtime permission additionally checks the compatibility identity.
GCS is separate: it can synthesize a bounded projection over an admitted GRC program, but
not arbitrary business logic or undeclared semantics.

## Adoption workflow using the public API

```python
import agent_compaction as ac

episodes = ac.read_jsonl("traces.jsonl")
catalog = ac.load_catalog("effects.yaml")

headroom = ac.estimate(
    episodes,
    catalog,
    entry_schema=["tenant", "channel", "locale"],
)
print(headroom.render())

job = ac.optimize(
    episodes,
    catalog,
    algorithms=["grc"],
    mode="offline",
    partition_by=["tenant_partition", "principal", "policy_version"],
    entry_schema=["tenant", "channel", "locale"],
    sandbox=make_isolated_sandbox,
)
print(job.report())
print(job.explain())
evidence = ac.validate(job, suites=["replay", "perturbation"])
job.save("artifacts/candidate", signing_key=signing_key)

# Promotion is one lifecycle stage at a time. Start with shadow.
ac.promote(job, stage="shadow")
```

The application must provide complete typed episodes, an effect catalog, independent
group identifiers, outcomes, and a compatible execution manifest. `sandbox=None` means
the perturbation suite was not run; the library records that absence rather than claiming
coverage. See [library-api.md](library-api.md) for TGWS evaluator requirements and
[operations.md](operations.md) before any runtime integration.

## Scenario 1: public GitHub issue evidence extraction

**Setting.** An agent reads issue metadata, body, comments, and repository facts before
returning an exact, source-grounded summary. The prompt specifies the task but not the
tool sequence.

**Measured evidence.** This is the paper's strongest real scenario. The expanded study
uses 132 real public GitHub issues for discovery and 30 independent paired evaluation
groups with live OpenAI Agents SDK calls. All three primary arms—unchanged agent, partial
GRC, and a hand-written macro—pass 30/30 registered exact contracts. GRC rejects the
ungroundable third read and emits a two-read prefix. The macro uses one composite tool and
is the better fixed-workflow engineering choice on tools, tokens, and estimated cost.

The subsequent portfolio decision is frozen from those 30 groups before selecting 12
fresh issues. The reviewed macro and baseline each pass 12/12 exact contracts; the macro
reduces provider requests 50.0%, tool calls 66.7%, total tokens 59.2%, observed wall
latency 71.6%, and estimated cost 40.6%. This is one-family evidence and does not show
that portfolio selection beats an always-macro policy across heterogeneous workflows.

An exploratory GCS extension reconstructs the full three-read region from the retained
discovery traces, validates it against all 132 real-provider trace decisions and the pinned
snapshot, then compares it with the provider-visible macro on 12 additional issues excluded
from every earlier cohort. Both pass 12/12 exact contracts. GCS reduces requests by 50.0%,
tokens by 38.9%, observed wall latency by 40.0%, and estimated cost by 32.3% relative to
that measured macro. It exposes one interface but still performs three source reads. The
study does not compare against a manually pre-executed macro and covers only bug/other
labels, so it is exploratory single-family evidence.

**Reproduce.** Provider-free inspection and the paid command are documented in the
[paper README](../paper/README.md). Raw prospective output is in
[`paper/results/portfolio_live/results.json`](../paper/results/portfolio_live/results.json).
GCS replay and live evidence are in
[`paper/results/gcs_validation/provider_free.json`](../paper/results/gcs_validation/provider_free.json)
and [`paper/results/gcs_live/results.json`](../paper/results/gcs_live/results.json).
The tools read a pinned public snapshot, so this is not evidence about live GitHub API
availability or mutation.

**Use when.** The source fields and exact factual contract are observable, the same
workflow recurs, and all compared actions can be run against identical records.

## Scenario 2: permissioned retrieval assistant

**Setting.** A knowledge assistant reads access-control scope, embeds a query, retrieves,
reranks, and fetches document metadata. Tenant, principal, policy version, index version,
and freshness are exact compatibility keys.

**Measured evidence.** Demo B runs real OpenAI provider turns and native SDK tools over a
deterministic fictional service. Four paired fixture scenarios pass the registered
quality and success contracts; the compacted condition reduces requests from 7.0 to 1.0
and total tokens by 76.3%. These small fixture results demonstrate execution mechanics,
not population quality or production authorization correctness.

**Compiler boundary.** Query rewriting is a model decision unless its value is grounded
from entry state or prior observations. A changed principal, policy, index, or schema must
miss the hard guard. `READ_EXTERNAL` is eligible only when the catalog also declares the
required replay/speculation capabilities and the application supplies freshness state.

**Use when.** Retrieval is high-volume and stable, source observations are retained, and
authorization partitions have enough independent support. Do not pool evidence across
tenants to rescue calibration support.

## Scenario 3: multi-agent incident triage

**Setting.** A coordinator gathers read-only operational evidence before deciding whether
to hand off to a specialist. The handoff changes agent ownership and remains outside GRC.

**Measured evidence.** Demo C uses live provider calls over fictional incident fixtures.
The supported prefix reduces requests from 5.0 to 1.0 and total tokens by 73.8% across
four paired scenarios at unchanged registered quality. The result is mechanism evidence;
the fixture world is not an incident-response benchmark.

**Optimizer boundary.** GRC may compile the read prefix but never span the handoff. TGWS
may learn an entry-time specialist route only when the application supplies a measured
evaluator. Streaming, SDK-managed handoff continuation, and server-managed state stay on
the baseline path unless their owning runtime exposes a reversible boundary.

**Use when.** Evidence gathering is repetitive and the handoff remains an explicit,
auditable model or application decision.

## Scenario 4: fulfillment workflow with a mandatory write

**Setting.** An order exception requires branching reads and pagination before an
irreversible fulfillment update.

**Measured evidence.** Demo E executes live provider calls over fictional WMS fixtures.
Only the pre-write prefix is eligible: the compacted arm changes 7.0 model requests to
2.0 and reduces total tokens 66.4%, while the write remains under the original agent.
Loop-bearing and schema-drift variants correctly return the baseline request count.

**Economic warning.** This small run reduces tokens while increasing estimated cost 8.3%
because prompt-cache economics dominate the invoice. Token reduction is not a cost claim.

**Use when.** A valuable read prefix ends strictly before commitment and the application
owns staging. Never reinterpret an idempotent or compensatable write as a pre-commit read.

## Scenario 5: multi-tenant MCP operations

**Setting.** An operations agent exposes many MCP tools, including reads with undeclared
quota, audit, permission, or residency effects.

**Measured evidence.** Demo D is a negative control with real provider calls and an actual
local stdio MCP server over fictional data. The catalog leaves effects undeclared, so the
optimized path falls back and preserves the baseline 3.0-request count and quality.

**Correct outcome.** `UNKNOWN`, approval-bearing, write, and cross-tenant calls terminate
candidate regions. `CompactingModel` also bypasses hosted/MCP tools; a framework-owned
outer controller is required for any future supported execution path.

**Use when.** Start with the estimator to identify which high-volume declarations could
matter. If effect ownership or isolation cannot be established, stop after the negative
result.

## Evidence that is intentionally separate

- [Live fixture results](live-results.md) use real OpenAI provider/SDK execution but
  fictional deterministic services.
- [Offline stress results](results.md) use a simulated policy and deterministic tool
  worlds to exercise calibration and rare failures at scale.
- The [paper artifact](../paper/README.md) contains the real public-record studies and
  NESTFUL benchmark.

Combining denominators or presenting one layer as another would invalidate the claim. None
of these scenarios is production certification.
