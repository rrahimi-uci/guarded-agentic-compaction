# Related-work matrix

Where this work sits and what remains after each neighbour. Listing a repository is not
evaluating it, so the last column states what was actually done here: `adapter` means a
runnable comparator exists in this repository; `comparator` means the design is
reproduced as a scored condition; `reference` means read and cited only.

| area / system | relevant capability | what remains | status here |
|:---|:---|:---|:---|
| [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/) 0.19.2 | agent loop, tools, handoffs, guardrails, sessions, approvals, tracing | it is the execution substrate, not an offline optimizer | `adapter` — `CompactingModel` behind the seven conformance tests of proposal §5.6; handoffs/streaming reject |
| [MLflow Tracing](https://mlflow.org/docs/latest/genai/tracing/) 3.15 (pinned ≥3.14) | automatic capture, search, evaluation, experiment lifecycle | trace substrate, not a provenance-aware compiler; previews truncate; parent/child is containment, not dataflow | `adapter` — export/load round-trip with flush and count reconciliation |
| Hand-written composite tool (+ concurrent reads) | collapses a read prefix into one call a person can read | the model still *selects* it, so one request per invocation survives; no discovery, no maintenance story | `comparator` — scored condition 2 on all four demonstrations; it wins twice |
| Support-only routing (frequency without provenance) | dispatches on recurrence alone | no groundability, no ambiguity cap, no contract challenge, no calibrated gate | `comparator` — scored condition 4; H4 status reported honestly |
| [DSPy](https://github.com/stanfordnlp/dspy) / [MIPRO](https://arxiv.org/abs/2406.11695) | instruction and demonstration optimization for LM programs | proposes prompt *text*; less explicit about effect-safe graph replacement and abstention | `reference` — an evaluation-only proposer under the same artifact gates is future work; TGWS deliberately selects existing blocks rather than generating text |
| [LLMCompiler](https://proceedings.mlr.press/v235/kim24y.html) | parallel tool-call planning and execution | optimizes the *current* schedule; does not prove a model decision removable from history | partially `comparator` — the macro condition executes its reads concurrently, which is the scheduling benefit without the compiler |
| [FlowCompile](https://arxiv.org/abs/2605.13647) | compile-time design-space exploration over model, reasoning-budget and workflow configurations | starts from a structured workflow and profiles a quality-latency frontier; it does not establish value provenance or pre-commit effect safety for deleting historical model decisions | `reference` — its Pareto artifact-set idea is a strong future comparator for cost-aware artifact selection |
| [AgentSlimming](https://aclanthology.org/2026.acl-long.1387/) | prunes or replaces graph-structured multi-agent nodes under a baseline-anchored acceptance rule | targets agent/topology redundancy rather than typed tool-argument provenance and runtime effect barriers | `reference` — a required baseline for any future multi-agent topology pass |
| [COVENANT](https://arxiv.org/abs/2607.25400) | compiles natural-language workflow policy into an interpreted control-flow graph | compiles declared procedure for alignment; this project infers selectively replaceable regions from observed executions | `reference` — complementary source-of-truth and runtime-verification path |
| [JTPRO](https://arxiv.org/abs/2604.19821) | rollout-driven joint optimization of prompts and tool descriptions | rewrites instructions and schemas; it does not by itself provide effect-safe decision elision | `reference` — a proposer could run behind this repository's replay, calibration and lifecycle gates |
| [LangGraph](https://github.com/langchain-ai/langgraph) | explicit durable workflow graphs | a runtime/export target; declaring a graph does not prove a step unnecessary | `reference` — the program IR is deliberately exportable but no adapter is claimed |
| [AutoGen](https://github.com/microsoft/autogen) / [CrewAI](https://github.com/crewAIInc/crewAI) | multi-agent orchestration | substrates, not trace-driven compilers | `reference` |
| Process mining (variant analysis, bottlenecks) | repeated paths, variants, conformance | needs value provenance, manifests and effect constraints before a rewrite is admissible | `reference` — canonical-window mining is the agent-shaped analogue and is `O(N·L)` |
| CEGIS / superoptimization | counterexample-guided smaller programs | unrestricted search is too broad for a safety argument | `reference` — the closed 23-operator library and the perturbation suite are the bounded analogue |
| Partial evaluation | specialization using known inputs | the compiler analogy for route and binding specialization | `reference` — TGWS is partial evaluation of an agent configuration |
| Conformal prediction / selective classification | distribution-free risk control by abstention | needs an observable nonconformity score and exchangeable groups; drift breaks it | implemented — fixed grid, Bonferroni-corrected Clopper–Pearson, `RETIRE` when no threshold clears |
| [Execution-provenance survey](https://arxiv.org/abs/2606.04990) | taxonomy of trace sources, evidence/execution units, provenance relations and trust functions | motivates unified schemas, argument lineage, provenance-bearing memory and recovery evaluation rather than a workflow optimizer | `reference` — independently verified on 2026-08-02; its open problems directly motivate the memory and recovery roadmap |

## The precise gap

This review did not identify a surveyed system that jointly: reconstructs typed agent execution *with value provenance*,
treats effects, permissions and freshness as hard barriers, uses bounded explainable
synthesis over a closed library, performs grouped replay plus metamorphic perturbation,
calibrates dispatch with an exact corrected bound, and emits immutable artifacts that fall
back before any commitment.

That is a narrow contribution, and this repository's measured results narrow it further:
on two of four demonstrations a hand-written function beat the compiler. The defensible
claim is not "agents can be compiled" but *historical execution provenance can identify a
measurable subset of agent control flow that is safely replaceable under explicit
groundability, effect, compatibility and statistical constraints — and can explain when
that subset is too small to matter*.

## Comparability notes

* Versions are pinned in the run manifest (`experiments/results/run_manifest.json`).
* Licences: Agents SDK (MIT), MLflow (Apache-2.0), DSPy (MIT), LangGraph (MIT) — none
  vendored here; both optional extras are declared in `pyproject.toml`.
* Budgets: the macro comparator costs about two hours of engineering per region; the
  compiler costs the build plus a shadow window per prompt change. The estimator reports
  the break-even in episodes/day under the deployment's own numbers.
