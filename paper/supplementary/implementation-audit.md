# Repository and implementation audit

## Project purpose and design philosophy

The project addresses repeated model-mediated control flow in mature tool-using agents.
It mines historical traces for stable read-only regions, reconstructs tool-argument value
dependencies, synthesizes bounded deterministic programs, and dispatches them only when
hard contracts and calibrated evidence allow. The core philosophy is selective program
replacement: abstention and “no artifact” are normal successful outcomes.

Target users are agent-platform teams with high-volume stable workflows, complete traces,
observable outcomes, independent grouping keys, an application-owned effect catalog, and
control over deployment lifecycle. Good scenarios are repeated evidence gathering,
permissioned retrieval, entry-time routing, and feasibility analysis. Write-heavy,
approval-gated, rapidly drifting, or unobservable workflows are intentionally poor fits.

## Architecture

The framework-neutral typed Episode IR is the stable seam. Capture adapters normalize
OpenAI Agents SDK and MLflow traces. Execution manifests pin prompt, policy, model, tool,
guardrail, SDK, tracer, entry-contract, and effect-catalog identities. Episodes are
qualified and partitioned before grouped splitting.

Two optimization passes share the IR:

- **GRC:** provenance graph → recurrent windows → bounded program synthesis → guards and
  verifier → grouped replay/perturbation → exact selective calibration → registry/runtime.
- **TGWS:** learns a shallow entry-state route to specialist prompt/tool configurations
  and prunes unused surfaces under measured outcome constraints.

The runtime separates hard admission (manifest, effect, guard, lifecycle, isolation),
statistical admission (gate), staged execution, postcondition verification, and commit.
Clean pre-commit misses fall back; dirty failures become incidents.
GRC's optimization choice remains compile-or-retire. A separate portfolio module now
selects among measured actions under exact group-level quality and regret-risk bounds. It
can emit a review-required macro recommendation but does not synthesize macro code.

## Correctness assessment by component

| Component | Current strength | Residual limitation |
|---|---|---|
| Trace schema | Typed, serializable, explicit event kinds and manifests | Application must supply complete payloads and truthful metadata |
| Effect catalog | UNKNOWN fails closed; capability and digest checks | Declarations cannot prove a provider's real effect |
| Provenance | Typed path/transform candidates; ambiguity blocking | Exact-value evidence can miss semantic transforms outside the DSL |
| Window mining | Barriers, live-ins, support groups/days, canonical topology | Quadratic worst-case event scan; deployable runtime currently prefix-only |
| Synthesis | Deterministic bounded 23-op library, group refit, narrow loops | No e-graph/CEGIS loop; legitimate complex programs abstain |
| Contracts | Entry hulls and live-out provenance/type/cardinality/effects | Empirical hulls are not semantic specifications |
| Calibration | Dev-fitted frozen score; fixed-grid Bonferroni exact upper bound | Per-artifact only; i.i.d./conditionally i.i.d. group indicators and observable labels required |
| Registry | Lifecycle, compatibility lookup, kill switch, rollback fields | Shared-secret signing; mutable objects; directory save not atomic as a unit |
| Dispatcher | Fail-closed checks, staging, verifier, clean fallback | Freshness/quota snapshots are supplied rather than independently attested |
| Continuation guard | Caller-defined output contract, checked renderer, revalidated baseline, secret-safe telemetry | Task semantics remain caller-owned; live latency/cost and cross-domain behavior are unmeasured |
| Decision policy | Compiler emits or retires; portfolio ranks measured actions, abstains to baseline, invalidates on compatibility drift, and marks macros for review | No macro synthesis, cache evidence, engineering-cost model, or learned cross-family policy |
| SDK capture | Natural processor-based trace integration | SDK cannot infer business outcomes/effects/isolation keys |
| SDK runtime | Real local-function execution through a custom Model | Not a drop-in Runner; bypasses streaming, hosted/MCP tools, handoffs, loops |
| TGWS | Readable bounded routing and measured pruning | Search uses aggregate point estimates; package coverage is weak |
| Evaluation | Grouped splits, paired statistics, replay, perturbation | Domain semantic equivalence remains caller-owned |

## Concrete defect found during the paper study

The miner could emit an eligible suffix even though shipped runtimes resolve artifacts at
the initial model boundary. The real-provider pilot dispatched later reads too early,
duplicated/reordered calls, and reduced compiled contract validity to 16.7%. The fix:

1. adds `GrcConfig.prefix_only=True` by default;
2. rejects windows whose start boundary is not the runtime entry point;
3. records `non_prefix_runtime` counts in the compile report;
4. adds a golden-trace regression test; and
5. reruns a wholly disjoint final cohort.

This is a correctness fix, not a paper-only filter. Supporting arbitrary suffixes requires
a verified runtime region-position key and resumable state, not merely relaxing the flag.

## Validation state

- The full test count is regenerated with each validation pass; it includes legacy,
  natural-workflow, replication-oracle, and continuation fail-closed regressions.
- Measured statement coverage is 76.28% over 12,014 statements; adding the prospective
  paid-study driver expands the denominator while its provider path remains only partly
  exercised by the provider-free suite.
- `pip check` reports no broken requirements.
- `scripts/verify_release.py` passes all repository checks.
- The publication artifact validator passes source hashes, result claims, cohort
  disjointness, generated-artifact checksums, PDF content, and secret-pattern scans.
- The public repository now has an initial versioned snapshot; experimental history before
  that snapshot and historical CI claims remain unavailable.

Coverage gaps are concentrated in TGWS packaging (27.7%), the outer runner (64.5%), replay
(65.5%), the older live-study drivers (30--31%), and report/capture utilities. The
prospective portfolio driver is at 54.1%. High line coverage in provenance, windows, effects,
schemas, registry, dispatcher, and statistics supports—but does not prove—the core path.

## Production-readiness verdict

The repository is a credible research alpha and reusable optimization library. It is not
production-certified. Production use still needs representative shadow/canary evidence,
privacy and retention governance, tenant-aware calibration, public-key artifact signing,
atomic registry publication, drift response, global multi-artifact risk allocation,
supported-runtime CI, SBOM/provenance attestation, and rollback drills.
