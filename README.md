# agent-compaction

Guarded, evidence-gated workflow optimization for LLM agents: mine repeated execution
patterns out of traces, propose a smaller workflow, prove the proposal on held-out
groups, and deploy only immutable artifacts that fall back to the original agent.

This repository implements the research design in
[proposal.md](experiments/proposal.md)—with historical decisions retained in
[execution-plan.md](docs/execution-plan.md)—and documents the current scenarios in
[use-cases.md](docs/use-cases.md). It includes the seven GRC algorithms, TGWS, the trace
contract, the evaluation protocol, the runtime, and six
provider-backed demonstration families with measured results in
[docs/live-results.md](docs/live-results.md). The larger deterministic stress study is
retained separately in [docs/results.md](docs/results.md).

**Two transformation engines, one evidence selector, one trace contract.**

* **TGWS** — trace-guided workflow specialization. Learn a shallow, readable route from
  entry-state facts to a specialist prompt and a minimal tool surface; prune what a route
  never needs; abstain when the route or the input is uncertain.
* **GRC** — guarded region compilation. Find repeated read-only regions, prove every tool
  argument derives from entry state or earlier observations, synthesize a bounded
  deterministic program from a closed 23-operator library, induce a contract, and dispatch
  only under a calibrated gate with an exact risk bound.
* **Portfolio selection** — compare only actions with paired group-level measurements,
  bound task failure and non-positive utility separately, and select the highest-utility
  admitted action. Macro selections are review-required recommendations, not generated code.

Neither invents business logic, changes model weights, or removes an external effect.
**Abstention is the default output**, and "do not compact" is the common and correct one.
GRC itself remains compile-or-retire. The portfolio layer can now choose a measured GRC
candidate or recommend a measured macro for human review; it does not synthesize macros,
and cache/model-routing actions remain unsupported until real measurements are supplied.

In a prospective real-record pilot, the selector used 30 prior independent GitHub issue
groups, chose the higher-utility reviewed macro, and then ran it on 12 fresh issues. Both
baseline and selected action passed 12/12 exact contracts; the selection reduced provider
requests 50.0%, tool calls 66.7%, total tokens 59.2%, wall latency 71.6%, and estimated
cost 40.6%. This is single-family evidence, not proof that selection beats always-macro.

---

## Live measured results

All agent decisions below were executed through OpenAI Agents SDK 0.19.2 with
`gpt-5.6-terra` at low reasoning effort. The enterprise records are fictional,
deterministic fixtures; model calls, function calls, handoffs, MCP transport, tracing,
token accounting, and latency are live. Each eligible demo has four paired scenarios;
the MCP negative control has two.

| demo | requests baseline → compacted | total-token reduction | latency reduction | estimated-cost change | quality / success |
|:---|:---:|---:|---:|---:|:---:|
| A · Tier-1 support | 6.0 → 1.0 | **79.6%** | **88.4%** | −73.6% | 1.00 / 1.00 both |
| B · permissioned RAG | 7.0 → 1.0 | **76.3%** | **86.9%** | −68.7% | 0.97 / 1.00 both |
| C · multi-agent triage | 5.0 → 1.0 | **73.8%** | **80.8%** | −75.5% | 1.00 / 1.00 both |
| D · multi-tenant MCP *(negative control)* | 3.0 → 3.0 | +0.1% | noise | +0.2% | 1.00 / 1.00 both |
| E · fulfillment exceptions | 7.0 → **2.0** | **66.4%** | **77.1%** | **+8.3%** | 1.00 / 1.00 both |
| E · loop artifact *(refused)* | 7.0 → 7.0 | +0.2% | noise | +55.4% | 1.00 / 1.00 both |
| E · schema drift *(guard miss)* | 7.0 → 7.0 | +0.0% | noise | +54.5% | 1.00 / 1.00 both |
| F · TGWS route specialization | 7.0 → 7.0 | **16.8%** | 5.4% | **+123.0%** | 1.00 / 1.00 both |

The compacted conditions use the library's real `CompactingModel`: deterministic native
function calls replace intermediate provider turns while the normal SDK executes and
traces every tool. **Three of the eight rows are negative controls whose correct outcome
is no compaction** — undeclared MCP effects, a loop-bearing artifact the Model adapter
refuses by design, and a WMS schema change that misses the hard guard. Each returns
exactly the baseline turn count at unchanged quality.

Demo E is the only one that ends in an irreversible write, so its region is a prefix and
**partial compaction (7 → 2 turns) is the correct result, not a degraded one**.

**Read the cost column carefully.** Removing turns removes tokens but not necessarily
money: a long-prompt baseline amortizes one prompt-cache *write* across many cheap cached
reads, and a two-turn compacted run has nothing to amortize it over. Demo F fragments one
warm prefix into four route prefixes and pays four writes. Both effects shrink as
episodes-per-prefix grows, so a benchmark this small understates the real cost advantage —
but a rarely-used route may genuinely never repay its own cache write, which is a design
constraint rather than a measurement artifact. The decomposition is in
[docs/live-results.md](docs/live-results.md).

Full per-run evidence, trace timelines and caveats are in
[docs/agent-compaction-report.html](docs/agent-compaction-report.html) and
[docs/live-results.md](docs/live-results.md). These small provider runs demonstrate the
mechanism; they are not production certification or a statistically powered quality claim.

---

## Install and run

```bash
python -m venv .venv && .venv/bin/pip install -e '.[dev,live,figures]'

.venv/bin/python -m pytest                      # full test suite
.venv/bin/python experiments/live_run.py --cases 3  # real API calls; reads .env
.venv/bin/python scripts/reproduce.py              # offline stress and fault study
```

Copy `.env.example` to `.env` and set `OPENAI_API_KEY` before the live command. The
runner never prints or persists the key. Set `AGENT_COMPACTION_LIVE_MODEL` to override
the default model.

Individual stages:

```bash
# 1. a decisive no for the price of an afternoon
agent-compaction estimate traces.jsonl --effects configs/effects.example.yaml \
                 --entry channel locale product

# 2. compile, then read every program before running it
agent-compaction compile  traces.jsonl --effects configs/effects.example.yaml \
                 --entry channel locale product --out artifacts/v1
agent-compaction explain  artifacts/v1

# 3. shadow first, always
agent-compaction promote  artifacts/v1 --stage shadow
```

## Library

```python
import agent_compaction as ac

episodes = ac.read_jsonl("traces.jsonl")
catalog  = ac.load_catalog("configs/effects.example.yaml")

print(ac.estimate(episodes, catalog, entry_schema=["channel", "locale"]).render())

job = ac.optimize(
    episodes, catalog,
    algorithms=["tgws", "grc"],
    mode="offline",
    partition_by=["tenant_partition", "principal", "policy_version"],
    entry_schema=["channel", "locale"],
    sandbox=make_sandbox,          # enables grouped replay + the perturbation suite
    tgws_baseline=baseline_config, # TGWS prunes only against measured quality
    tgws_evaluate=evaluator,
)
print(job.report())
print(job.explain())               # readable pseudocode per artifact
ac.validate(job, suites=["replay", "perturbation"])
ac.promote(job, stage="shadow")

decision = ac.select_portfolio_action(
    paired_observations,
    config=ac.SelectionConfig(
        quality_risk_limit=0.10,
        regret_risk_limit=0.10,
        minimum_groups=40,
        expected_compatibility_key=manifest.compatibility_key(),
    ),
)
if decision.requires_review:
    review_approved = submit_for_review(decision)
else:
    review_approved = True
if decision.permits(
    manifest.compatibility_key(), review_approved=review_approved
):
    activate_selected_action(decision)
```

Deployment has two paths, detailed in [the SDK guide](docs/openai-agents-sdk.md). The
wrapper comes first because it owns
the entry-state snapshot and the staging boundary:

```python
runner = ac.CompactingRunner(dispatcher=ac.Dispatcher(registry=reg, catalog=catalog,
                                                      mode="shadow"),
                             catalog=catalog, manifest=manifest)
```

For the OpenAI Agents SDK there is a custom `Model`; it ships behind the seven
conformance tests of proposal §5.6 and rejects streaming, hosted tools and handoffs
rather than degrading:

```python
from agent_compaction.runtime.model_provider import CompactingModel
agent = Agent(name="support", model=CompactingModel(base_model, registry=reg,
                                                    catalog=catalog, manifest=manifest,
                                                    mode="shadow"), tools=[...])
```

For agents not on the SDK, `@ac.compact(registry, catalog, manifest, mode="shadow")`.

---

## What is in the repository

```text
src/agent_compaction/
  paths.py          flatten / resolve_path / content digests (no dependencies)
  schema/           traces, effect catalog, artifacts (the frozen contract)
  capture/          entry-state contract, manifests, Agents SDK adapter, JSONL store
  graph/            qualification, provenance (Alg. 1), window mining (Alg. 2)
  grc/              DSL, bindings (Alg. 3), branches (Alg. 4), contracts (Alg. 5),
                    calibration (Alg. 6), the compile orchestrator
  tgws/             route tree, greedy pruning, packaging
  portfolio/        typed candidates, exact-risk admission, review-aware selection
  evaluation/       grouped splits, replay modes, perturbations, metrics, statistics
  registry/         artifact store, lifecycle, signing, kill switch, rollback
  runtime/          dispatch (Alg. 7), staging, permission facade, interpreter,
                    CompactingRunner, CompactingModel
  estimate/         Eq. (10) feasibility and the economic break-even
  api.py  cli.py
configs/            effect + promotion schemas and worked examples
demos/              live fixture services, actual MCP server, and offline stress worlds
  support/          A — linear read-only evidence prefix
  permissioned_rag/ B — ACL scope, index version and freshness as hard guard keys
  incident_triage/  C — coordinator + handoff; a handoff is a barrier for GRC
  mcp_ops/          D — real stdio MCP server, undeclared effects (negative control)
  fulfillment/      E — three synthesized branches, pagination, and a mandatory write
experiments/        live Agents SDK runner plus the offline stress driver and results
tests/              unit, property, integration, golden traces, mutation, fault injection
docs/               results, spec review, safety model, trace contract, operations, ADRs
scripts/            fixture generator, capture smoke test, reproduce, verify release,
                    build_html_report.py (the illustrated report)
```

## Documentation

| Document | What it answers |
|:---|:---|
| [docs/README.md](docs/README.md) | documentation source-of-truth map and evidence classes |
| [docs/agent-compaction-report.html](docs/agent-compaction-report.html) | **illustrated report** — architecture and algorithm walkthrough, SDK integration, and before/after trace timelines rendered from the measured runs |
| [docs/gpt-5.6-report.md](docs/gpt-5.6-report.md) | end-to-end architecture, implementation, novelty, readiness and benchmark review |
| [docs/mlflow-removal-report.md](docs/mlflow-removal-report.md) | why MLflow was removed, what the custom JSONL store guarantees, trade-offs, migration, and validation |
| [docs/live-results.md](docs/live-results.md) | provider-backed paired demos, raw denominators, cost and evidence boundaries |
| [docs/results.md](docs/results.md) | deterministic offline stress study, with denominators and caveats |
| [docs/spec-review.md](docs/spec-review.md) | what the specifications got wrong, where, and what was done instead |
| [docs/safety-model.md](docs/safety-model.md) | what may be compiled, what may never be, and what each failure path does |
| [docs/trace-contract.md](docs/trace-contract.md) | the fields the application must supply, and why the SDK cannot infer them |
| [docs/library-api.md](docs/library-api.md) | stable APIs, optimization passes, extension points and examples |
| [docs/openai-agents-sdk.md](docs/openai-agents-sdk.md) | capture and runtime integration with the OpenAI Agents SDK |
| [docs/operations.md](docs/operations.md) | shadow → canary → live, monitoring, incident runbook, rollback |
| [docs/related-work-matrix.md](docs/related-work-matrix.md) | adjacent systems, what they cover, what remains |
| [docs/architecture/](docs/architecture/) | the decisions and the alternatives that were rejected |
| [experiments/manifests/preregistration.md](experiments/manifests/preregistration.md) | hypotheses, margins, thresholds and stopping rules, frozen before the sealed test |
| [paper/README.md](paper/README.md) | publication artifact: LaTeX paper, real-record live study, NESTFUL benchmark, figures, raw results, and adversarial review |

## Status and limits

This is a research MVP, honest about its boundaries:

* **v0.x is read-only.** Only `PURE`/`READ_LOCAL`/`READ_EXTERNAL` tools declared
  `speculatable ∧ replayable` can enter a region. Writes, approvals, unknown effects and
  handoffs terminate it. Transactional staged writes are future work.
* **Empirical validation cannot prove semantic equivalence** for all future inputs. The
  contribution is selective, evidence-bounded replacement with abstention.
* **Calibration is usually the binding constraint.** A zero-violation exact bound at
  α = 0.05 needs ≈92 independent calibration groups; the estimator reports that number
  before any compilation, and candidates that cannot reach it retire.
* **The compiler is often not the right tool.** Run the estimator, read the top regions,
  and if a handwritten function captures them, write the function.
