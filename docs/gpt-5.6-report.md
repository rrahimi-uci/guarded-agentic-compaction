# GPT-5.6 end-to-end repository review

**Repository:** agent-compaction  
**Review date:** 2026-08-02  
**Reviewed version:** source and package version 0.5.0  
**Scope:** architecture, implementation, tests, packaging, OpenAI Agents SDK integration,
research positioning, optimization-library design, provider-backed demonstrations, and
reproducible offline stress evaluation

## Publication-study addendum (2026-08-03)

The publication artifact is now available under [`paper/`](../paper/README.md), with the
compiled manuscript at [`paper/build/main.pdf`](../paper/build/main.pdf). Its current
primary evidence is:

- a pinned public NESTFUL analysis over 1,415 executable basic-function episodes; and
- two review-driven OpenAI Agents SDK studies over real public GitHub issue records using
  task-level prompts, deterministic snapshot tools, live provider calls, exact-source
  grading, a hand-written macro, and counterbalanced condition order.

In the expanded confirmatory study, all 132 discovery executions choose the same
three-read order even though the prompt names neither tools nor order; 130 pass the
exact-source task. The compiler rejects the full candidate because the comments argument
is not consistently groundable and emits only the two-read prefix. On 30 fresh balanced
records, unchanged, partial compiler, and macro each pass 30/30 exact factual and full task
contracts. Relative to unchanged, partial compilation reduces requests 50.0%, tokens
39.5%, observed wall latency 51.7%, and estimated cost 32.0%. The macro matches the request
reduction while saving 58.2% of tokens, 37.5% of cost, and two of three tool calls. It is
the stronger fixed-workflow baseline; the compiler has lower observed mean latency, but
the paired interval crosses zero. The complete expanded run retains 252 agent executions,
848 provider responses, no infrastructure failures, and an estimated provider cost of
$0.19129.

The earlier aggressive natural study retains the depth-sensitive negative result:
unchanged, compiler, and macro pass 18/18, 17/18, and 18/18. It reduces provider requests
75.0% and tokens 66.0%, but does not establish preservation. Its continuation replay
detects and checked-renders the single miss provider-free.

The older 18-pair fixed-prefix study remains a controlled ablation. It observed 18/18
registered-contract passes in both arms and reduced requests by 75.0%, tokens by 65.7%,
latency by 85.0%, and estimated cost by 52.6%, but its prompt prescribed the sequence and
its summary oracle did not test factuality. Its compiler calibrated on 92 configured group
records with zero observed violations and a corrected upper bound of 0.0498; independence
is a sampling assumption, not a machine-verified property.

The first live pilot exposed an unsafe suffix-dispatch mismatch. The implementation now
defaults runtime compilation to entry-prefix windows, reports `non_prefix_runtime`, and
has a golden-trace regression test. The archived pilot is retained as negative evidence;
all its issues are excluded from later cohorts. The current validation counts are recorded
in Section 11 and in `paper/results/validation_summary.json` rather than duplicated here.

These results do not establish production safety, live GitHub reliability, cross-domain
generalization, human-productivity improvement, or state-of-the-art superiority. The
paper's evidence register and hostile self-review retain those boundaries.

## Executive verdict

The repository solves a real and sharply framed problem: mature agents often repeat
expensive model-mediated control flow even when a subset of that flow has become stable,
read-only, and mechanically derivable from facts already available at the boundary.
agent-compaction mines that subset from traces and replaces it only when provenance,
effects, replay, contracts, calibration, compatibility pins, and runtime staging all agree.

The project is now a credible **open-source research alpha and reusable optimization
library**, not a production-certified optimizer. The central design is coherent, unusually
explicit about refusal, and substantially implemented. Its strongest contribution is not
generic “agent compilation”—that area is already occupied—but the conjunction of:

1. typed value provenance for tool arguments;
2. explicit effect, permission, freshness, and isolation barriers;
3. bounded, readable synthesis rather than unconstrained generated code;
4. grouped replay and counterexample-oriented perturbation;
5. selective dispatch under an exact corrected risk bound;
6. evidence-bearing artifacts with baseline fallback before commitment.

The implementation mostly matches that design after the fixes in this review. The
remaining distance to production is representative evidence and operations, not merely
more code: privacy governance, a real shadow window, canary evidence,
multi-artifact risk control, stronger registry signing/atomicity, and a supported-runtime
CI matrix are still absent.

### Evidence labels used in this report

| label | meaning |
|:---|:---|
| **verified** | inspected or executed in this checkout during this review |
| **real-provider** | measured through the live OpenAI API and native Agents SDK traces over pinned public records |
| **provider-backed fixture** | measured through the live OpenAI API and native Agents SDK traces on fictional deterministic fixtures |
| **simulated** | measured by the real optimizer/runtime on a deterministic simulated agent workload |
| **environment-gated** | exercised here, but dependent on an optional SDK/backend version |
| **proposed** | designed here but not implemented or run |
| **production evidence required** | cannot be established from this repository alone |

No Git metadata exists in this checkout. A commit, branch, diff against a Git parent,
remote CI status, or publication state therefore could not be verified.

### Live-provider update

After the original review, all four user-facing demonstrations were converted to live
OpenAI Agents SDK workflows using `gpt-5.6-terra` at low reasoning effort. Support,
permissioned RAG, and triage use deterministic fictional service records; MCP uses an
actual local stdio MCP server. The API key is loaded from `.env` but is not printed or
persisted. Synthetic scripted policies remain only for scalable stress, calibration,
perturbation, and fault-injection tests.

The live work also exposed and fixed two integration bugs that the direct conformance
tests missed: `CompactingModel` did not inherit the SDK's `Model` base class, and its
in-flight plan was stored only in a `ContextVar`, which does not necessarily survive the
SDK's sibling async turn contexts. The wrapper now subclasses `Model`, retains live plans
by native trace id, delegates retry/close behavior, and preserves the context-local path
for direct callers.

## 1. Problem, users, and intended use

### Problem

An agent loop normally spends one model request at each decision boundary:

~~~text
model -> tool -> model -> tool -> model -> answer
~~~

Historical traces may show that some decisions are stable functions of entry state and
earlier observations. Replacing such a region can reduce model requests, prompt/schema
tokens, latency, and cost. Doing that naively is unsafe: a memorized argument, stale
permission, hidden effect, approval bypass, or unobservable write can turn a speed
optimization into a semantic or operational incident.

The repository therefore treats optimization as **selective program replacement under
evidence**, not as prompt rewriting and not as unconditional workflow generation.
“No artifact” and runtime abstention are first-class successful outcomes.

### Target users

- teams operating stable, high-volume tool-using agents with observable outcomes;
- platform engineers who can provide an effect catalog, entry-state contract, and
  isolation keys;
- research teams evaluating trace-driven workflow optimization;
- OpenAI Agents SDK users who need trace capture or a narrow model-boundary adapter;
- framework authors who can normalize executions into the repository’s typed Episode IR.

### Good use cases

- repeated read-only evidence gathering;
- permissioned retrieval with explicit ACL and index-version pins;
- stable entry-time routing to specialists;
- prompt-block and tool-surface specialization evaluated against real outcomes;
- offline feasibility analysis that concludes a hand-written composite tool is better;
- negative-control workloads where undeclared effects or fine-grained partitions should
  prevent compilation.

### Poor or unsupported use cases

- write-heavy agents or approval-gated workflows;
- rapidly changing prompts, policies, schemas, or external state without repeated shadow
  and calibration windows;
- streaming, hosted tools, MCP tools, handoff-spanning regions, or server-managed SDK
  continuation through the current CompactingModel adapter;
- workloads without stable independent groups, complete payloads, outcomes, or an
  application-owned effect catalog;
- online self-modification or optimization without a frozen evaluation boundary.

## 2. Design philosophy

The implementation follows six consistent principles.

1. **Abstain by default.** Unknown is a barrier; missing evidence does not become a guess.
2. **The trace IR is the stable boundary.** MLflow and the OpenAI Agents SDK are adapters,
   not the compiler’s internal representation.
3. **Effects are permissions, not annotations.** Only declared pre-commit reads with
   speculatable and replayable capabilities may enter a GRC region.
4. **Groundability precedes optimization.** Every synthesized argument must derive from
   entry state, literals, or earlier observed tool results through a closed transform
   library.
5. **Selection and evidence are separated.** Train/development data produces a frozen
   candidate; calibration groups select an abstention threshold; the test set evaluates
   the frozen system.
6. **Fallback is a runtime semantic.** A miss returns the tested baseline; an unattestable
   post-commit failure is an INCIDENT rather than a fictional rollback.

This philosophy is the project’s main strength. The code does not fully satisfy every
operational consequence yet, but it does not hide the gap.

## 3. Architecture assessment

~~~mermaid
flowchart LR
    A[Agent or SDK runtime] --> B[Capture adapter]
    B --> C[Typed Episode IR]
    C --> D[Qualification]
    D --> E[Manifest and isolation partitioning]
    E --> F[Grouped train dev calibration test splits]
    F --> G[Provenance graph and window mining]
    G --> H[TGWS route prompt tool specialization]
    G --> I[GRC guarded read-region compilation]
    H --> J[Evidence-bearing artifact]
    I --> J
    J --> K[Registry and lifecycle]
    K --> L[Shadow resolver]
    K --> M[Live dispatcher]
    L --> A
    M --> N[Guard and calibrated gate]
    N --> O[Checked interpreter and tool facade]
    O --> P[Verifier and staging attestation]
    P -->|pass| Q[Compacted continuation]
    N -->|miss| R[Baseline agent]
    O -->|clean failure| R
    P -->|dirty failure| S[INCIDENT]
~~~

### Major abstractions

| abstraction | role | assessment |
|:---|:---|:---|
| Episode / EventNode | framework-neutral observable execution | strong, explicit, serializable |
| ExecutionManifest | pins semantic dependencies | strong after canonical identity fixes |
| EffectCatalog | versioned effect and capability authority | strong fail-closed default; declaration truth remains application-owned |
| PATG / Window / Family | value provenance and recurring-region representation | strong bounded alternative to general subgraph isomorphism |
| Program / Binding / Predicate | closed deterministic GRC DSL | readable and auditable; intentionally limited |
| RouteTree / LeafConfig | bounded TGWS specialization | useful, but its search-time statistical checks need strengthening |
| HardGuard / Verifier / Gate | runtime admission and post-execution contract | clear separation of deterministic and statistical checks |
| Artifact / Registry | deployable evidence bundle and lookup | usable local implementation; signing and immutability are not yet production-grade |
| OptimizationPass / Pipeline | library extension contract | good generic seam; orchestration is ordered, not transactional |
| CompactingRunner / CompactingModel | outer-controller and SDK model-boundary runtimes | outer controller is semantically stronger; SDK adapter is intentionally narrow |

### Algorithmic patterns

- content-addressed manifests, catalogs, splits, paths, and artifacts;
- typed provenance graph construction and value-directed expression search;
- bounded canonical-window enumeration, O(N·L), instead of general graph matching;
- greedy backward prompt/tool/handoff pruning under measured outcomes;
- shallow readable route trees with temporal and subgroup stability checks;
- grouped replay, metamorphic perturbations, and sandbox state-delta checks;
- logistic nonconformity scoring trained on development groups;
- fixed-threshold selective calibration with corrected exact binomial bounds;
- deterministic O(1) registry resolution and a staged interpreter.

## 4. Component-by-component implementation review

| component | verified strengths | fixes made in this review | residual issues |
|:---|:---|:---|:---|
| Packaging and release | PEP 517 package, extras, CLI, typed marker | Apache-2.0 license, CONTRIBUTING, SECURITY, SPDX metadata, py.typed, build validation; removed incompatible PEP 639 classifier | no CI matrix, lint, static typing, coverage gate, SBOM, or provenance attestation |
| Trace capture | JSONL, real MLflow 3.15 round trip, real Agents SDK 0.19.2 processor | sensitive export now requires explicit opt-in; MLflow reconciliation uses newly created trace IDs | allowlist recorded by MLflow configuration is not an end-to-end storage policy; queue drops require operator monitoring |
| Manifest identity | compatibility key pins workflow dependencies | canonical JSON hashing; manifest ID now includes tools, catalog, SDK, tracer, and all compatibility inputs | applications can still supply unknown SDK/tracer pins unless qualification policy rejects them |
| Effect catalog | UNKNOWN default, read/write lattice, capability gates | canonical order-independent digest; strict full digest match; legacy mode must be explicit | declarations cannot prove real provider effects; nominal reads may still bill, audit, or observe time |
| Qualification | completeness, pairability, outcomes, drift reporting | added envelope/manifest match, duplicate/non-contiguous event checks, parallel call IDs, core unknown-field checks, declared-effect mismatch checks | schema-level payload typing is mostly structural rather than full tool-schema validation |
| Mixed deployments | compatibility identities are explicit | strict single-manifest low-level calls plus safe batch partitioning; unique artifact IDs | TGWS lacks a public batch helper equivalent to compile_grc_batch |
| Provenance and mining | typed value lineage, ambiguity cap, barriers, principal/day/group support | corrected parallel call/result pairing; deterministic window/base selection | exact-value matching can miss semantic transforms outside the 23-op library |
| DSL synthesis | bounded depth, stable-chain ranking, readable output | search memoization, deterministic ordering, real grouped refit, inconsistent group-label rejection | cache is process-local and unprofiled; no e-graph or counterexample-guided incremental search |
| Loop synthesis | bounded loops and termination predicates | stopped rewriting unrelated integer literals as counters; proved zero-based counters only; aligned loop output shapes | supports a narrow loop family and fixed max-iteration policy |
| Replay and perturbation | recorded/sandbox/shadow/canary evidence kept distinct | effect multiset uses counts; state deltas after failure/rejection are hard failures; None comparisons corrected | sandbox equivalence is structural for non-cacheable tools and may be too weak for domain semantics |
| Contracts | guards, live-out clauses, provenance, effect and call-count checks | verifier now retains minimum and maximum cardinality | hulls remain empirical; nested schema constraints and relational invariants are limited |
| Calibration | grouped exact upper bounds and normal RETIRE outcome | gate model fit on dev and frozen before clean calibration; exact deployed-threshold bookkeeping; explicit alpha=1 ablation | each artifact is certified individually; selection among many candidates has no global familywise guarantee |
| TGWS routes | readable depth-bounded routing, temporal/subgroup checks | rejected non-improving splits; deduplicated paths; handoffs included in complexity | pruning uses aggregate point non-inferiority during search rather than grouped confidence intervals |
| TGWS outcome gate | candidate quality, success, and safety measured | success-rate loss added to pruning and per-episode calibration labels | evaluator cost is high; model/tool/prompt proposals remain caller-owned |
| Optimization pipeline | framework-neutral ordered pass API | added built-in GRC and TGWS pass adapters and public exports | a failed pass can mutate shared context before raising; no transaction, checkpoint, or artifact-conflict protocol |
| Registry | local deterministic lookup, lifecycle, kill switch | lifecycle-aware shadow/live resolution; canonical partition keys; signed CLI promotion requires key | HMAC is shared-secret integrity, not public-key supply-chain signing; directory save is not atomic as a unit; stale explanation files may remain |
| Runtime dispatcher | guard → gate → stage → interpret → verify → commit | mode/budget validation, live ACTIVE-only policy, quota snapshot requirement, dirty interpreter abort becomes INCIDENT, shadow would-dispatch telemetry | external-state freshness is a pin supplied by the application, not independently attested |
| Interpreter/facade | call allowlist, effect enforcement, budgets | corrected loop environment and result behavior; stronger failure paths | no concurrency scheduler or cancellation propagation for generated programs |
| OpenAI Agents SDK | native tracing capture and native local function calls on supported hit | documented and tested lifecycle/mode/bypass behavior | not a drop-in Runner; no exact post-emission rollback; streaming, handoffs, hosted/MCP tools, loops and assertions bypass |
| Metrics/statistics | paired grouped ratios/differences, exact safety upper bound | added generic comparison and repeat-agreement APIs | determinism is not a first-class field in the main four-demo result schema; secondary endpoint correction is not wired through every report |
| Reproduction | generated fixtures, four conditions, negative result, figures | added validated parallel per-demo execution with isolated outputs | created timestamps and wall-clock fields make raw files byte-different even when semantics are identical |
| Tests | 214 tests across unit, property, golden, mutation, fault injection, backends, CLI, paper oracles, and end-to-end paths | added regression coverage for all corrections and both natural protocols | measured statement coverage is 76%; live-study drivers, TGWS packaging, replay, and the outer runner need focused coverage |

## 5. Correctness findings and concrete fixes

### High-severity correctness fixes

1. **Catalog version aliasing and legacy acceptance.** The old short version could accept
   different catalogs. Catalog versions now include a canonical content digest; legacy
   digest-free versions require an explicit compatibility switch. All demos were migrated.
2. **Loop counter corruption.** Loop synthesis previously treated the first integer
   argument—such as page limit 4—as an iteration counter and rewrote it to 0, 1, … .
   Counter slots now require an observed zero-based sequence across runs.
3. **Dirty interpreter fallback.** A failed interpreted run with a changed staging snapshot
   could be labeled baseline. It now produces INCIDENT, matching verifier-failure behavior.
4. **Calibration leakage/bookkeeping.** Gate fitting and threshold calibration were not
   cleanly separated, and certificate statistics could describe a threshold other than
   the deployed one. The model is now trained on dev/perturbation samples, frozen, and
   calibrated on clean calibration groups; the stored row is the exact deployed row.
5. **Parallel result association.** Result events could attach to the wrong call when tool
   calls overlapped. Pairing now uses call_id with FIFO fallback for legacy traces.
6. **Effect-set comparison.** Set comparison discarded duplicate calls. Replay now compares
   effect multisets.
7. **Unobservable snapshots.** Only the entry snapshot’s unobservable list was considered.
   Entry and current unobservable declarations now jointly make reversibility false.

### Robustness and maintainability fixes

- canonical JSON identities replaced delimiter joins in manifests, compatibility keys,
  splits, partitions, and catalogs;
- mixed manifests are rejected or partitioned before fitting;
- malformed episodes are qualified before graph construction;
- branch synthesis refits by group and rejects contradictory labels within a group;
- route trees refuse splits that do not improve parent purity;
- list contracts now preserve both minimum and maximum lengths;
- search results are memoized by content digest;
- artifact selection and base-window choice are deterministic;
- registry promotion from the CLI re-signs with an environment-provided key;
- shadow resolution can inspect SHADOW/APPROVED/ACTIVE while live resolution accepts only
  ACTIVE;
- live quota-attested reads require a snapshot;
- packaging now builds both sdist and wheel under isolated PEP 517.

## 6. Design fidelity

| documented promise | implementation verdict |
|:---|:---|
| two optimizers over one framework-neutral trace contract | implemented |
| GRC compiles only pre-commit reads | implemented and fault-injection tested |
| every argument is grounded | implemented within the closed transform library |
| grouped train/dev/calibration/test protocol | implemented; post-review rerun is engineering validation, not a new preregistered confirmatory study |
| exact corrected selective gate | implemented per artifact after calibration fixes |
| shadow changes no behavior | implemented; dedicated would-dispatch telemetry added |
| baseline fallback on clean pre-commit failures | implemented |
| immutable signed artifacts | only partly true: signed bodies exist, but Artifact and lifecycle fields remain mutable Python objects |
| natural OpenAI Agents SDK integration | capture is natural; runtime is natural only for the narrow local-function subset |
| production-ready library | not yet supported by production evidence or operations |
| memory optimization | extension contract only, not a built-in optimizer |
| generic other-framework integration | generic IR and decorator exist; concrete runtime adapters do not |

## 7. Reusable library architecture

The repository has been moved toward a reusable library by making the optimization
pipeline—not GRC itself—the extensibility boundary.

### Stable layers

1. **Capture:** adapters produce Episode objects.
2. **Contracts:** ExecutionManifest, EffectCatalog, entry-state projection, grouping.
3. **Analysis:** qualification, provenance, canonical windows, headroom.
4. **Optimization passes:** GRC, TGWS, or third-party prompt/tool/memory/topology passes.
5. **Evidence:** grouped replay, perturbation, calibration, benchmarks.
6. **Artifacts:** typed route/program plus guard, verifier, gate, evidence, lifecycle.
7. **Runtime:** resolver, dispatcher, facade, staging, interpreter, SDK adapter.
8. **Operations:** registry, signing, shadow, promotion, expiry, rollback, kill switch.

### Public composition API

~~~python
import agent_compaction as ac

episodes = ac.read_jsonl("traces.jsonl")
catalog = ac.load_catalog("effects.yaml")
splits = ac.make_splits(episodes, seed=20260801)

pipeline = ac.OptimizationPipeline([
    ac.TgwsOptimizationPass(
        config=tgws_config,
        baseline=baseline_config,
        evaluate=measured_evaluator,
    ),
    ac.GrcOptimizationPass(
        config=grc_config,
        sandbox=make_isolated_sandbox,
    ),
])

context = ac.OptimizationContext(
    episodes=episodes,
    catalog=catalog,
    manifest=episodes[0].manifest,
    splits=splits,
)
report = pipeline.run(context)
~~~

A third-party optimizer implements OptimizationPass, declares required capabilities, and
returns PassResult with explicit APPLIED or ABSTAINED status, artifacts, metrics, and
notes. The pass must preserve manifest partitions, grouped evaluation, effect barriers,
and evidence separation.

### Extension points

| desired optimizer | implemented hook | required new artifact/evidence |
|:---|:---|:---|
| prompt evolution | OptimizationPass plus measured evaluator | prompt diff, provider budget, quality/safety calibration |
| tool-schema compaction | TGWS evaluator or new pass | schema compatibility, tool-selection and slot-filling endpoints |
| memory compaction | new pass | source lineage, retention, freshness, contradiction and deletion semantics |
| model routing | RouteConfig producer | per-model cost/latency/quality frontier and drift gate |
| multi-agent topology | new graph pass | handoff/message semantics, topology complexity, collaboration quality |
| latency scheduling | new plan artifact | dependency DAG, concurrency permissions, cancellation and rate limits |
| cross-framework runtime | adapter over Episode and dispatcher contracts | native history/tool continuation conformance suite |

The detailed API and SDK documents are [library-api.md](library-api.md) and
[openai-agents-sdk.md](openai-agents-sdk.md).

## 8. OpenAI Agents SDK integration

Official documentation states that the SDK traces generations, tool calls, handoffs,
guardrails, and custom spans, which makes it a suitable capture substrate:
[Agents SDK](https://developers.openai.com/api/docs/guides/agents),
[observability](https://developers.openai.com/api/docs/guides/agents/integrations-observability),
and [trace grading](https://developers.openai.com/api/docs/guides/trace-grading).

### Supported integration paths

**Capture.** AgentsTraceProcessor implements the SDK processor surface and converts native
spans into the repository’s trace IR after the application joins entry state, isolation,
manifest, outcomes, and state digest. Sensitive payloads are disabled by default.

**CompactingModel.** For a live, supported hit, the adapter emits one deterministic native
function call per SDK turn. The SDK still performs tool dispatch and tracing. On a miss or
unsupported surface it delegates to the wrapped model.

**CompactingRunner.** This is the stronger semantic path because an outer application
controller owns the whole snapshot, region, verifier, and commit decision. It is
framework-neutral and requires application glue; it is not a subclass of the SDK Runner.

### Required production work

- run conformance in CI against every supported SDK patch and before widening the pin;
- add provider-backed tests for sessions, retries, tracing attribution, timeouts, and
  tool errors;
- define application history and external-state snapshots;
- expose hosted/MCP/streaming capability negotiation instead of implicit bypass only;
- implement an outer SDK runner adapter if exact multi-call deoptimization is required;
- perform real shadow evaluation using trace grading and application business outcomes.

## 9. Research novelty and opportunities

### Current positioning

The novelty claim must be narrower than the original generic compiler framing.

- [LLMCompiler](https://proceedings.mlr.press/v235/kim24y.html) optimizes parallel
  function-call scheduling.
- [FlowCompile](https://arxiv.org/abs/2605.13647) explores reusable workflow-level
  quality/latency configurations at compile time.
- [AgentSlimming](https://aclanthology.org/2026.acl-long.1387/) prunes and quantizes
  graph-structured multi-agent systems.
- [COVENANT](https://arxiv.org/abs/2607.25400) compiles natural-language procedure into
  an interpreted workflow control graph.
- [JTPRO](https://arxiv.org/abs/2604.19821) jointly optimizes prompts and tool descriptions
  from rollouts.
- [GEPA](https://arxiv.org/abs/2507.19457) reflects over execution and evaluation
  trajectories and applies instance-wise Pareto prompt evolution. It is directly related
  to trace-driven optimization but changes residual LM prompts rather than deleting model
  boundaries; it constrains any generic novelty claim and motivates a complementary
  GAC+GEPA factorial evaluation.
- The 2026 [execution-provenance survey](https://arxiv.org/abs/2606.04990) identifies
  unified trace schemas, argument lineage, provenance-aware memory, and recovery
  evaluation as open areas.

The defensible distinction here is **trace-derived decision elision with typed
argument provenance, explicit effect boundaries, exact selective calibration, and
pre-commit deoptimization**. That joint claim still requires comparison against the
newer systems and real workloads before publication.

### Prioritized novel enhancements

| enhancement | compared with current implementation | expected benefit | trade-off / evidence needed |
|:---|:---|:---|:---|
| Causal decision-elision tests | current support and replay are observational | distinguishes a removable decision from a correlated repeated path | needs controlled interventions or multiple policies; more evaluations |
| Counterexample-guided e-graph synthesis | current value-directed BFS is depth-2 and local | shares equivalent expressions, adds operators safely, shrinks repeated search | larger trusted kernel; must preserve readability and group refit |
| Global constrained artifact selection | current candidates are calibrated independently then greedily selected | one coverage/cost frontier with a familywise risk budget | harder multiple-testing and combinatorial optimization |
| Pareto artifact families | current registry chooses one objective and threshold | adapts to deployment cost/latency budgets like FlowCompile while retaining hard safety gates | more artifacts and maintenance; needs dominance and expiry policy |
| Group-aware TGWS pruning | current search uses aggregate point non-inferiority | prevents a cheap configuration that harms a subgroup from entering calibration | higher evaluator cost and lower yield |
| Prompt/tool-schema proposer behind gates | current TGWS selects existing blocks and tools | attacks tool ambiguity and prompt bloat, complementary to JTPRO | generated text broadens search and requires separate semantic diff review |
| Provenance-bearing memory compiler | current memory optimization is only an extension contract | deduplicates context, expires stale facts, preserves source/invalidation lineage | write/delete semantics and privacy are harder than read-only GRC |
| Multi-agent collaboration compaction | current TGWS routes at entry and treats handoffs as barriers | removes redundant agents/messages and model turns; compare AgentSlimming/MASS | topology changes can alter authority and approval semantics |
| Deterministic replay capsules | current external state is represented by a supplied version/digest | reproducible provider/tool snapshots and stronger regression diagnosis | storage, secrets, retention and replay fidelity costs |
| Effect-aware parallel scheduler | current programs execute serially | lower critical-path latency without removing additional decisions | rate limits, cancellation, ordering, quota and freshness constraints |
| Recovery-oriented artifacts | current clean failure falls back and dirty failure incidents | explainable resume/retry/compensate decisions from provenance | requires transactional effect protocols and failure-injection campaigns |

## 10. Benchmarking and validation

### Provider-backed paired demonstrations

The primary demo evidence is now [live-results.md](live-results.md). The baseline lets the
provider select each tool through the normal SDK loop. The compacted condition uses the
library's actual `CompactingModel` to emit deterministic native function calls while the
SDK continues to execute and trace the tools; the provider performs final synthesis.

| demo | paired scenarios | requests baseline → compacted | total-token reduction | wall-latency reduction | estimated-cost reduction | quality / success |
|:---|---:|:---:|---:|---:|---:|:---:|
| Tier-1 support | 3 | 6.0 → 1.0 | 79.4% | 90.1% | 80.1% | 1.00 / 1.00 both |
| Permissioned RAG | 3 | 7.0 → 1.0 | 76.1% | 81.3% | 75.9% | 1.00 / 1.00 both |
| Incident triage | 3 | 5.0 → 1.0 | 74.0% | 70.4% | 75.9% | 1.00 / 1.00 both |
| MCP negative control | 2 | 3.0 → 3.0 | −0.1% | noisy 5.6% improvement | −0.2% | 1.00 / 1.00 both |

There were 22 total live executions, 75 provider responses, 62,982 input tokens, 3,495
output tokens, zero quality failures, and zero safety events. The total estimated cost was
$0.150810. Cost
is estimated from OpenAI's published standard short-context prices as of 2026-08-02; it
is not an account invoice. The eligible workflows kept the same tool-call count—the
optimization removed model-mediated control turns, not external evidence. The MCP
negative control retained the provider loop because no human-attested effect catalog
licensed compilation.

This is real SDK/provider evidence for mechanism, token use, latency, handoffs, and MCP
transport. It remains small-n evidence on fictional fixtures, without calibrated live
risk bounds, production traffic, stochastic repeat analysis, or a canary window.

### Offline stress protocol

### Protocol

The reproducible driver evaluates four conditions:

1. unchanged baseline;
2. hand-written composite-tool comparator;
3. full TGWS plus GRC;
4. support-only ablation without the full provenance/risk ladder.

Selection uses grouped train, development, and calibration roles. A held-out test role
provides paired group-bootstrap request/cost/latency ratios and one-sided quality
non-inferiority. Safety reports exact upper bounds. A prospective shadow role is kept
separate.

This second evidence layer is simulated: real optimizer, compiler, registry, interpreter, dispatch,
statistics, and traces; deterministic scripted policies and tools stand in for a provider
model and production dependencies.

### Full offline stress results

| demo | test episodes | full request ratio, 95% CI | request reduction | input-token reduction | cost reduction | mean-latency reduction | tool-call reduction | workflow-step reduction | quality / success delta |
|:---|---:|:---|---:|---:|---:|---:|---:|---:|:---|
| Tier-1 support | 719 | 0.7547 [0.7490, 0.7615] | 24.53% | 8.34% | 14.56% | 21.65% | 0.00% | 14.70% | 0.0000 / 0.0000 |
| Permissioned RAG | 1,397 | 0.7182 [0.7155, 0.7207] | 28.18% | 25.46% | 30.35% | 25.15% | 0.83% | 16.21% | 0.0000 / 0.0000 |
| Incident triage | 658 | 0.7798 [0.7730, 0.7869] | 22.02% | 13.65% | 19.86% | 19.75% | 5.05% | 16.33% | +0.0100 / +0.0334 |
| Multi-tenant MCP negative control | 897 | 1.0000 [1.0000, 1.0000] | 0.00% | 0.00% | 0.00% | -0.17% overhead | 0.00% | 0.00% | 0.0000 / 0.0000 |

Workflow-step reduction is the reduction in model requests plus tool calls per episode.
The detailed offline report is [results.md](results.md).

### Interpretation

- All three positive demos pass the request and quality co-primary criteria.
- The hand-written comparator is better on support and RAG. Automatic compilation is not
  credited with benefits that a simple composite function can deliver more cheaply.
- Incident triage is the clearest TGWS use case: entry-time specialization removes
  coordinator turns that a composite tool cannot remove.
- The MCP negative control emits no full artifacts and changes no semantic metric. Its
  small latency regression is dispatcher overhead on a guaranteed miss.
- Full artifacts caused zero observed compiled writes and zero incidents. Exact one-sided
  95% upper bounds on unsafe dispatch were 0.00452, 0.00214, and 0.00454 for support, RAG,
  and triage respectively. These are simulated bounds, not proof of zero risk.
- The ablation does not demonstrate H4 on the retrospective test distribution. It can
  behave identically in deterministic in-distribution tools while lacking perturbation
  evidence. A shifted test or perturbation-scored ablation is required.

### Determinism

The entire full support experiment was rerun independently with the same seed and budget.
After excluding wall-clock-only fields (timing, latency, overhead, and creation time), the
two complete results were structurally equal and had the same SHA-256 digest:

~~~text
eba59aa2435757563aa59937d2f67c80775e1f1a013846e24c02ab9aa37c2fd6
~~~

Requests, tool calls, tokens, dollars, quality, success, safety events, artifact writes,
coverage, split decisions, artifacts, and optimization decisions were exactly equal in all
four conditions. This verifies deterministic optimizer and simulated execution semantics
for that workload. It does not measure provider-model nondeterminism.

### Reproducibility boundary

The preregistration file predates the original experiment, but this review changed code
and then regenerated results. The final run is therefore strong **engineering regression
evidence**, not a fresh sealed confirmatory study. A publishable claim needs a new frozen
commit/configuration, preregistered hypotheses, and a newly sealed provider or production
test set.

## 11. Validation evidence

| check | result |
|:---|:---|
| full tests after the publication-study additions | 214 passed |
| expanded primary natural real-provider run | 252 agent executions, 848 provider responses, 0 infrastructure failures; all three primary arms pass 30/30 exact factual and task contracts |
| earlier aggressive natural run | 134 agent executions, 446 provider requests, 0 infrastructure failures; factual passes 18/18 unchanged, 17/18 compiler, 18/18 macro |
| fixture-based live provider executions | 22 completed; all registered scenario outcomes passed |
| optional backends | OpenAI Agents SDK 0.19.2 and MLflow 3.15.0 tests passed, no skips |
| measured statement coverage | 75.84% overall (displayed as 76%), 11,544 statements, 2,789 missed |
| compileall | passed |
| editable install | package and metadata both 0.5.0 |
| isolated PEP 517 build | sdist and universal wheel built |
| clean wheel import | 0.5.0 imported from clean site-packages; py.typed present |
| clean CLI | help and command registration passed |
| dependency consistency | pip check passed |
| release audit | all package, schema, link, result, manifest, evidence, and no-write checks passed |
| publication claim/integrity audit | 956 checks passed; 0 failed |
| full reproduction | all four demos, report, figures, and audit completed in 321.0 seconds with four workers |
| deterministic rerun | normalized semantic equality and identical digest for full support experiment |

Environment: macOS 26.5.2 arm64, Python 3.14.4, NumPy 2.5.1, SciPy 1.18.0,
scikit-learn 1.9.0, Pydantic 2.13.4.

Python 3.14 passing locally does not replace CI on every declared runtime from 3.11
through 3.14.

### Coverage priorities

The weakest measured areas are capture.attributes (0%), estimate.reports (0%),
evaluation.benchmark (0%), tgws.package (28%), tgws.routes (60%), and runtime.runner
(62%). Some low TGWS coverage is because the main experiment runs in subprocesses and the
coverage command did not combine subprocess data, but focused tests are still required.

## 12. Production-readiness assessment

### Ready for open-source alpha use

- coherent package and public API;
- documented trace/effect/safety contracts;
- real optional-backend tests;
- explicit negative outcomes and failure semantics;
- provider-backed demos plus reproducible simulated stress benchmarks;
- license, security policy, contribution guide, typed marker, wheel and sdist;
- reusable optimization-pass protocol.

### Not production-certified

| missing evidence/control | why it matters |
|:---|:---|
| representative production traces | the live fixtures validate SDK mechanics, not production distribution shift |
| prospective shadow window | retrospective evidence cannot establish live coverage or drift |
| canary with operational SLOs | no measured hot-path reliability, rollback time, or incident response |
| end-to-end privacy policy | capture allowlists do not enforce retention, access, deletion, or data residency |
| public-key signing and immutable content envelope | shared HMAC and mutable objects are insufficient for multi-party artifact supply chains |
| atomic durable registry backend | local per-file replacement is not an atomic deployment transaction |
| global risk policy | several individually calibrated artifacts do not imply one system-wide guarantee |
| CI runtime matrix and static analysis | one local Python version is not release certification |
| external-state attestation | supplied freshness/version fields can be wrong or stale |
| SDK provider conformance | native local-function tests do not cover every deployed SDK/session/tool surface |

The correct release label remains **Development Status: Alpha**.

## 13. Prioritized roadmap

### P0 — trustworthy alpha release

1. **CI and quality gates**
   - Python 3.11–3.14 matrix, optional extras, isolated build/install, link/release audit.
   - Add Ruff, mypy/pyright over the typed public surface, coverage combination for
     subprocesses, and an initial 80% floor with module-specific floors for runtime safety.
   - Acceptance: all matrix jobs pass from a clean checkout; no optional-backend skips in
     the full job.
2. **Artifact and registry hardening**
   - Split immutable signed content from mutable lifecycle metadata.
   - Add Ed25519/public-key verification, atomic registry generation/pointer swap, stale
     file cleanup, and durable audit storage.
   - Acceptance: tamper, partial-write, rollback, key-rotation, and concurrent-reader tests.
3. **System-wide statistical contract**
   - Freeze candidate selection before calibration or apply hierarchical/familywise control
     across the deployed artifact set.
   - Replace TGWS point non-inferiority during pruning with group-aware intervals.
   - Acceptance: one stated global risk budget and simulation coverage proving it.
4. **Privacy and trace governance**
   - Enforce entry allowlists at every exporter, define privacy classes, retention and
     deletion tombstones, encrypt raw payload references, and audit access.
   - Acceptance: policy tests demonstrate forbidden fields never reach JSONL or MLflow.
5. **Representative provider-backed SDK staging**
   - Extend the now-working live fixture path to one real application with complete joined
     outcomes, privacy approval, a frozen SDK pin, and prospective shadow mode.
   - Acceptance: zero behavior changes in shadow, reconciled trace counts, stable group IDs,
     and published miss/coverage distributions on representative traffic.

### P1 — research and optimization depth

1. Implement causal decision-elision and counterexample-guided synthesis.
2. Add Pareto artifact families and constrained global selection.
3. Add prompt/tool-schema proposal passes and a factorial unchanged/GEPA/GAC/GAC+GEPA
   study so reflective optimization of residual model decisions is separated from region
   compilation.
4. Add an AgentSlimming/MASS-style topology comparator under handoff/effect constraints.
5. Implement provenance-bearing memory compaction with expiration and invalidation.
6. Add an effect-aware parallel scheduler and critical-path benchmark.
7. Run new sealed evaluations on a stochastic model, at least two domains, and a shifted
   test distribution.

### P2 — controlled production expansion

1. Outer OpenAI Agents SDK runner adapter with exact staging ownership.
2. Hosted/MCP/streaming capability negotiation and conformance suites.
3. Transactional write protocol only after prepare/validate/commit/compensate can be
   attested; do not relax read-only GRC by declaration alone.
4. Multi-tenant control plane, registry backend interfaces, key management, and SLOs.
5. Carefully bounded online reoptimization with immutable candidate generations and no
   direct self-promotion.

## 14. Files and documentation added or materially revised

- library pipeline and exports: src/agent_compaction/pipeline.py and package __init__;
- stricter manifests, catalogs, qualification, partitions, synthesis, calibration,
  runtime, replay, registry, CLI, and reproduction paths;
- Apache-2.0 LICENSE, CONTRIBUTING.md, SECURITY.md, and py.typed;
- [library-api.md](library-api.md);
- [openai-agents-sdk.md](openai-agents-sdk.md);
- [live-results.md](live-results.md), the provider-backed runner, and an actual stdio MCP server;
- updated operations, readiness, related-work, results, README, and release verification;
- expanded unit, property, integration, mutation, golden, and fault-injection tests;
- this report.

Because the checkout is not a Git repository, this inventory is based on a before/after
file-hash snapshot rather than Git history.

## 15. Final assessment

The repository is substantially stronger than a proposal and more honest than many
“agent compiler” prototypes: it has a typed IR, explicit refusal semantics, real
algorithms, guarded execution, negative controls, and reproducible measured trade-offs.
The review fixed several bugs that would have invalidated correctness or deployment claims,
especially loop argument corruption, catalog identity, calibration separation, dirty
fallback, parallel call pairing, SDK model inheritance, and cross-turn live plan state.

The correct claim today is:

> Historical execution provenance can identify a measurable subset of agent control flow
> that is replaceable under explicit groundability, effect, compatibility, grouped
> evaluation, and selective-risk constraints, while explaining when the subset is too
> small or unsafe to deploy.

That is a useful library and a defensible research direction. The live demos now show the
mechanism working end to end against a provider, but they are not evidence that arbitrary
agents can be compacted safely in production. The next decisive milestone is a newly
sealed, representative shadow and canary study under the hardened P0 controls above.

---

## 16. Second review pass: an adversarial demonstration and what it broke

The first fifteen sections were written against four demonstrations that share one
shape: a linear read-only prefix ending in a read. That shape flatters the system. This
pass added a fifth world chosen specifically to violate it, added the first live
exercise of the *other* optimizer, and treated every resulting failure as a finding
rather than a configuration problem.

### 16.1 Demo E — order-fulfillment exception handling

`demos/fulfillment/` is the first world in the repository that combines, in one region:

* **three synthesized branches**, two on entry state (`exception_class`) and one on an
  *observation* (`page0.has_more`), giving a call count of 4, 5 or 6 and forcing the
  verifier to admit a set rather than a number;
* **a paginated read**, expressible either as a conditional second `CallStep` or as a
  bounded `LoopStep` — two artifacts over identical evidence, one of which the
  `CompactingModel` adapter must refuse;
* **a mandatory irreversible commitment** (`orders.reschedule` / `case.escalate`) on every
  episode, so the region can only ever be a prefix;
* **an undeclared non-deterministic scorer** (`risk.score`) that is genuinely useful,
  present in the baseline tool surface, and must never enter a region;
* **an approval barrier** (`refunds.issue_credit`) that a prior approval never licenses.

The offline estimator puts the oracle ceiling at **41.3% request reduction** for this
workload and attributes the cap to the write tail — `case.escalate` and
`orders.reschedule` account for the largest blocked-window mass. The measured live
result is 7.00 → 2.00 provider turns at unchanged quality: the evidence turns disappear,
the decision turn and the write survive. **Partial compaction is the correct outcome
here, and the four original demos never had to demonstrate it.**

### 16.2 Demo F — TGWS executed live

`tgws_router` is the first provider-backed run of route specialization. A route tree is
fitted by the library's real `fit_route_tree` on simulated traces of the same world, and
the live agent then runs under the selected leaf's prompt-block set and minimal tool
surface. At the default depth 3 all four exception classes separate at purity 1.000. At
depth 2 the last leaf mixes two classes at purity 0.60, fails the temporal-stability
check, and the router abstains to the generalist — the abstention path is live either
way.

### 16.3 Defects found and fixed

| # | Where | Defect | Fix |
|---|---|---|---|
| 1 | `experiments/run.py` `_unsafe_bound` | Unsafe events were divided by *compacted episodes*. An episode can execute a region more than once and an incident is an execution, so `k > n` was reachable and raised `ValueError` out of Clopper–Pearson instead of reporting a bound. Demo E hit it on the first run. | New `artifact_executions_total` metric as the denominator; numerator-exceeds-denominator now reports the ceiling **and** an explicit `denominator_warning` rather than silently rescaling. |
| 2 | `grc/synthesize.py` `_synthesize_loop_predicate` | The continue-condition search only tried `len(items) == n`. Every real paginated API signals continuation with a flag or a cursor, and an order whose last page is *full* defeats the length atom outright — so the loop-bearing candidates died at `loop_predicate_unsynthesizable` even though the trace evidence determined the condition exactly. | Enumerate boolean continuation flags, nullable continuation handles, length atoms and low-cardinality status scalars, ordered by description length; verify in **both** directions on every window; refuse vacuously-satisfiable searches where nothing ever continued. |
| 3 | `grc/program.py` `LoopStep.pretty` | The printed program showed the counter slot bound to its synthesized constant, but the interpreter overwrites that slot with the iteration index on every pass — so the artifact described a program that does not run. The loop variable could also collide with the counter name (`shipments.list_page` yields both `page` and `page`). | Render the counter as the loop index and disambiguate the collision (`page_i`). This is a correctness bug, not cosmetics: these artifacts are read by a human before approval. |
| 4 | `tgws/routes.py` `RouteTree.route` | A decision tree's last leaf is a conjunction of negations, so an entry carrying a category never seen in training matched it by construction and inherited a route whose purity was never measured on that value — contradicting the documented "rare or uncertain inputs abstain" guarantee. | Record the observed domain of every categorical split feature; `route()` abstains outright on an out-of-domain value. Numeric `>=` thresholds are deliberately exempt: they extrapolate by design. |

On a deterministic baseline the new search induces `page.has_more == True` and the
loop-bearing candidates reach replay validation instead of dying at synthesis. On the
default workload — whose scripted policy skips the second page in 6% of episodes — two
candidates still report `loop_predicate_unsynthesizable`, and that is the right answer:
the observed runs contradict *every* continuation atom, so there is no condition the
evidence supports. The fix removed an expressiveness limit, not the refusal.

### 16.4 Findings that are not bugs

**A compaction-specialized prompt makes abstention unsafe.** Demos A and B tell the
compacted agent that "the runtime has already executed an approved read-only evidence
plan". That is sound only while compaction is guaranteed, and it never is. Measured: with
a specialized prompt, Demo E's three *correct refusals* scored 0.33–0.75 instead of 1.00,
because the agent had been instructed to trust evidence the guard had just prevented it
from gathering. Demo E now uses one instruction for every condition, and all four
conditions score 1.000. **This is a caveat against demos A and B as published**, not just
a demo bug: any deployment whose wrapper may abstain needs an instruction that remains
complete when it does.

**`quota_attested` makes an artifact undispatchable through the Model adapter.** Demo E's
token mint was first declared `quota_attested: true`. The dispatcher then requires a
reversibility snapshot before every live dispatch, `CompactingModel` owns no staging
boundary and passes no `snapshot_fn`, and every boundary failed closed with
`missing_reversibility_snapshot`. This is the system working, but the only signal was a
telemetry counter. The declaration is now `false` with the reasoning written out, and
`tests/integration/test_fulfillment_demo.py` pins both directions. The general rule: a
deployment whose reads are quota-attested must use `CompactingRunner`, not the adapter.

**Hand-specified route surfaces are unsafe.** The first version of `ROUTE_BLOCKS` dropped
`evidence_policy` from every route. It cost 0.05 mean quality on the `address_invalid`
route — the model no longer knew to follow `has_more` and under-counted shipments. That
is exactly the failure the greedy pruner exists to prevent, because it *measures* each
proposed removal under quality non-inferiority instead of trusting intuition.
`evidence_policy` is now a protected block.

### 16.5 The result that contradicts the premise

Removing provider turns reliably removes tokens. It does not reliably remove money, and
in two of the six demonstrations it inverted the sign:

| Demo / condition | Input tokens | Cached share | Cache writes | Blended $/Mtok |
|---|---:|---:|---:|---:|
| fulfillment / baseline | 9,787 | 96% | 370 | 0.57 |
| fulfillment / compacted | 3,301 | 38% | 2,048 | 1.83 |
| tgws_router / baseline | 9,775 | 98% | 143 | 0.51 |
| tgws_router / routed | 8,072 | 58% | 1,465 | 1.37 |

Demo E uses **66.4% fewer tokens and costs 8.3% more**. Demo F uses **16.8% fewer tokens
and costs 123% more**. The mechanism is prompt caching: a provider bills the first turn
over a prefix at a write premium and later turns at roughly a tenth of the input price. A
seven-turn baseline amortizes one write across six cheap reads; a two-turn compacted run
pays the write with nothing left to amortize it over. Route specialization fragments one
warm prefix into four, each paying its own write.

Part of this is a benchmark artifact — cache warmth grows with episodes-per-prefix, so
four scenarios per condition systematically understate the advantage of both techniques.
Part of it is a real constraint that the current objective does not price:

1. **TGWS should charge for prefix fragmentation**, not only count prompt and schema
   tokens. A route whose traffic share is too small to amortize its own cache write is a
   net loss even when its prompt is strictly shorter. The `Objective` in `tgws/prune.py`
   currently has no term for this.
2. **The Eq. (12) break-even should be computed against the *cached* baseline price**,
   not the list input price. A workload whose baseline is already cache-dominated has far
   less dollar headroom than its token headroom implies, and the estimator should say so
   before anyone builds a compiler for it.

Both are concrete, testable additions and neither was visible from the four original
demonstrations, because their prompts are short enough that the cache write never
dominates.

### 16.6 Deliverables added in this pass

* `demos/fulfillment/` — world, effect catalog, baseline policy, route packs;
* `experiments/live_run.py` — Demo E's four conditions and Demo F, generalized
  multi-condition aggregation and reporting;
* `experiments/conditions/registry.py` — Demo E registration and route labeller;
* `scripts/build_html_report.py` and `docs/agent-compaction-report.html` — the
  illustrated report: architecture and algorithm walkthrough, SDK integration, and
  before/after trace timelines rendered directly from the captured episodes;
* `tests/unit/test_loops_and_bounds.py`, `tests/integration/test_fulfillment_demo.py`,
  and new route-domain cases in `tests/unit/test_tgws.py` — 35 new tests, all green
  alongside the existing suite.

### 16.7 Revised assessment

Nothing here overturns §15. It sharpens it. The claim that historical execution
provenance can identify a replaceable subset of agent control flow under explicit
constraints survived a workload built to break it — including partial compaction against
a mandatory write, and two refusals that cost exactly the baseline and nothing more.

What changed is the honest statement of *benefit*. The request and latency reductions are
real and large. The **cost** reduction is conditional on cache economics that the current
objective does not model, and on at least one workload shape the sign flips. A production
decision should be made against the cached-price break-even, not against the token
headline — and the estimator does not yet compute it that way. That is the first item on
the next roadmap.
