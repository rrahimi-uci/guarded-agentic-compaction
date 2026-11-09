# GAC expansion: a generic optimizer for adaptive agentic workflows

Status: proposed design and execution plan; no expansion is implemented by this document.

Date: 2026-11-07. Revised 2026-11-08 to add a publication track (section 0), a census gate ahead of every build milestone (section 11), concrete workloads and comparators (section 10), and a venue plan (section 16). The engineering design in sections 3-9 and 12-13 is unchanged.

Source baseline for the feasibility re-review: `origin/main` at `6c4ec01183b20583d49e6e51dfe80a86384bc5bb`, which includes the original plan from PR #119. The first plan used `5250a32`; the observations and corrections below were rechecked against the newer baseline.

Scope: expand what GAC can optimize while preserving explicit effect, continuation, and evidence boundaries. This is a separate research and engineering track, not a claim that the current paper already supports write-enabled compilation.

## 0. Publishable claims and research questions

The first version of this plan was an engineering roadmap: it said what to build and how to keep it safe, but not what a paper would claim or which result would refute it. The ICLR 2027 reviews (`paper/reviews/ICLR-{1,2,3}.txt`) reject the current paper on value, not on mechanism: the compiled program matches a hand-written one on metadata tasks; no comparison with another compiler is run; no adaptive workload is studied. More machinery does not answer that. A publishable extension must show that automatic guarded compilation finds and safely exploits reuse that a person would not write by hand, on a workload where the unchanged agent is competent. Everything below is ordered by how directly it serves that claim.

### Hypotheses, pre-declared thresholds, and what refutes each

| ID | Hypothesis (to be frozen before data) | Measurement | Go threshold (declared here, before the census) | Refuted if |
|---|---|---|---|---|
| H1 Headroom | Real adaptive trajectories contain recurring, groundable, read-only regions at non-initial boundaries that the current prefix-only compiler cannot reach. | Provider-free census over retained corpora (AppWorld released runs, SWE-agent, OpenHands, tau-bench, BIRD agent traces, WebArena-Verified pilot), extending `paper/results/prefix_census/` to interior boundaries: share of trajectories with an interior read-only region of at least two calls whose arguments are groundable under the current witness rule, and the number of independent groups supporting each candidate family. | At least one corpus with interior groundable regions in >= 20% of trajectories and at least one family supported by >= 92 independent groups. | No corpus reaches both numbers. Then M1 has no measurable value and only the engineering track (section 11, Track E) remains. |
| H2 Automation beyond hand-writing | On at least one workload, the compiled interior program differs from the program a person writes first (longer, conditional, or data-dependent), and a hand-written program with the same budget does not match its savings. | Paired runs of unchanged agent, hand-written bounded program, simpler compiler, and GAC on fresh independent groups (section 10). | GAC requests or cost at least 20% below the hand-written arm with task success noninferior at a pre-declared margin. | Hand-written matches or beats GAC, as it does on every GitHub family today. Then the honest claim stays "safe automation of the hand-written program", which the current paper already makes. |
| H3 Admission value | Statistical admission refuses candidates that simpler compilation would deploy and that go on to fail. | Rejection funnel plus deployment of rejected candidates in a disposable environment; count violations among candidates GAC retired but the simpler compiler admitted. | At least one retired family with a measured violation rate above alpha when forced to run. | All retired families run clean (as recurrence-only replay does on issue-type today). Then the sample floor is the only thing the gate buys, and the paper says so. |
| H4 Compiler comparison | Against an executable trace-reuse compiler on the same frozen tasks, model and budget, GAC's admitted programs are noninferior in task success at lower or equal cost, and its refusals are explained. | Matched comparison protocol (`paper/supplementary/matched-compiler-candidate-protocol.md`) with TraceCompiler if its code is runnable; otherwise the recurrence-only replay compiler on the same IR. | Noninferiority at the declared margin with the rejection funnel reported for both. | GAC loses on cost without a quality gain. Reported either way; this is the comparison R1 and R2 asked for. |

H1 is the gate for everything else. It costs no provider calls and can be finished in one week from retained traces. If H1 fails, the paper track reduces to H3 and H4 on the existing GitHub families, which is a resubmission of the current paper with the two missing comparisons, not an expansion paper.

### What is publishable and what is not

- **Publishable at an ML venue:** H1 + H2 on one adaptive workload (an "interior reuse" paper), or H3 + H4 on the existing families (a strengthened resubmission). Both need the whole-policy admission of section 9, a competent baseline, and fresh independent groups.
- **Publishable at a systems or PL venue only:** the interior-boundary contract (section 5), the mutation contract and durable recovery protocol (sections 7-8) with fault-injection evaluation (section 12). This is a mechanism paper; it needs no statistical admission result but does need a workload with real writes and a soundness argument for the ordered mutation IR.
- **Not publishable on any budget this project has:** a certified compiled-write result. Section 15 shows 59 selected groups for a 5% bound and 299 for 1%; at 10% dispatch coverage that is 600-3,000 sampled adaptive episodes with a competent baseline and a side-effect oracle, and 5% is not an acceptable target for harmful effects. The write track is therefore mechanism-only for publication purposes (Track E below).

### Two tracks

- **Track P (paper):** P0 census (H1), P1 matched compiler comparison on the GitHub families (H4), P2 interior read regions on one adaptive workload (H2, H3; needs M1a and the orchestration-level admission path of section 9). No writes.
- **Track E (engineering):** M1b durable host ownership, M2 owned transactional writes, M3 external write adapter. Valuable as a product roadmap and as a later systems paper; not on the critical path of any 2027 submission.

## 1. Decision and intended outcome

The architectural goal is a reusable optimizer for generic agentic workflows: different domains, tool catalogs, model providers, and host runtimes should share the same discovery, bounded compilation, admission, and execution contracts. GAC should accommodate workflows containing reads, writes, branches, loops, and adaptive model decisions even when only some regions are eligible for compilation. Generic applicability does not imply universal compilability, automatic correctness, or guaranteed savings. The current implementation does not yet establish this broader capability.

The expansion should proceed through independently useful stages:

1. Establish whether real adaptive traces contain useful, groundable recurring regions that the current boundary restrictions exclude.
2. Support read-only regions at explicitly verified interior workflow boundaries, including after an ordinary agent write has completed.
3. Compile bounded mutations inside one owned transactional boundary, with validation before publication and durable recovery across publication.
4. Consider external writes only for adapters with enforceable authorization, concurrency, deduplication, and outcome-reconciliation contracts.

Do not begin by making `WRITE_REVERSIBLE` compilable. A reversible business operation, a discardable private mutation, and an externally visible operation with compensation have different semantics. An effect name alone cannot justify retry, fallback, or publication.

The first useful deliverable is an adaptive agent that alternates between admitted compiled read regions and ordinary agent decisions/actions, on a workload where section 0's census (H1) shows such regions exist and recur. The first compiled-write deliverable is deliberately smaller: one transactional backend, a bounded program, and one publication point. Cross-service transactions, autonomous compensation planning, unrestricted generated Python, and arbitrary concurrent write branches are deferred.

Success has three separate meanings: **mechanism correctness** under a stated backend contract; **empirical task performance** on a fresh population; and **incremental value of automatic guarded compilation** over simpler alternatives. Passing one does not establish the others.

**Feasibility verdict after the deeper review:** proceed with M0 and a bounded application-owned host prototype. Interior read optimization is a credible extension of existing components; compiled transactional writes require substantial new compiler, storage, and recovery work. A local backend probe supports the atomic-receipt approach, but no expanded GAC runtime or new admission certificate exists. Generic transparent installation, arbitrary external writes, and a fixed date for research superiority are not supported commitments. Section 15 records the evidence and unresolved gates; the revised estimates in section 11 supersede the original 5–9-week prototype estimate.

## 2. Current implementation and evidence

The following observations were checked against the source baseline above. Links identify existing implementation or retained evidence, not promised future capabilities.

| Area | Current behavior | Consequence for expansion |
|---|---|---|
| Effects | [`EffectSpec.compilable`](src/guarded_agentic_compaction/schema/effects.py) requires a read-like effect, speculation and replay capabilities, and no approval requirement. Write classes already exist but are barriers. | Preserve this default. Introduce separately versioned execution contracts for new modes. |
| Candidate regions | [`GrcConfig.prefix_only`](src/guarded_agentic_compaction/grc/compile.py) defaults to true; [`windows.py`](src/guarded_agentic_compaction/graph/windows.py) rejects write and unknown effects. | Disabling `prefix_only` alone would not make interior execution valid. |
| Dispatch position | [`Dispatcher.decide`](src/guarded_agentic_compaction/runtime/dispatch.py) normally requires position zero. An exact declared [read-only prologue](src/guarded_agentic_compaction/runtime/prologue.py) is the narrow exception. | A completed write cannot be smuggled into that exception. Interior boundaries need a new contract and adapter support. |
| Control flow | [`program.py`](src/guarded_agentic_compaction/grc/program.py) and [`interp.py`](src/guarded_agentic_compaction/runtime/interp.py) support per-call typed predicates and bounded repeated calls. | Branching is not entirely new. Arbitrary nested control-flow graphs and general loop bodies are not established by these primitives. |
| Exceptions | [`ToolFacade`](src/guarded_agentic_compaction/runtime/facade.py) wraps executor exceptions as `ToolFailure`, under a pre-commit `FacadeError` contract. | Reusing this contract for writes could replay a successful mutation after a timeout. |
| Staging | [`Staging`](src/guarded_agentic_compaction/runtime/staging.py) compares explicit snapshots and accepts only read-like effects at commit. | Its `commit` records an accepted read execution; it is not a durable database transaction coordinator. |
| Admission | Compiler and artifact structures retain guards, verifier checks, evidence, and compatibility versions. | New boundaries, effects, loss definitions, and continuation policies require fresh artifacts and evidence. |
| Integration ownership | [`CompactingModel`](src/guarded_agentic_compaction/runtime/model_provider.py) emits calls into a host-owned history and explicitly cannot undo post-emission state; it rejects loop/assertion programs. | Use an application-owned outer controller first. Keep the transparent model wrapper on its existing supported scope. |
| Replay identity | [`Recording`](src/guarded_agentic_compaction/runtime/facade.py) retrieves results by tool and arguments; identical repeated calls overwrite the exact-key lookup. | Mutation replay requires occurrence/state/receipt identity and execution against disposable worlds, not this lookup alone. |
| Label generation | [`_calibration_samples`](src/guarded_agentic_compaction/grc/compile.py) labels recorded-output agreement after successful interpretation and verification. | It is not the full-workflow, mutation-aware calibration path proposed below; that path must be built explicitly. |

The [browser development boundary](paper/supplementary/browser-boundary-development.md) retains an owned application/browser instance after a checked read and allows subsequent local writes. It explicitly distinguishes this research mechanism from production `Staging` and GAC admission. It does not establish arbitrary browser restoration or admitted compiled writes.

The [AppWorld adaptive pilot](paper/results/appworld_adaptive_viability/REPORT.md) discovered a grading-path persistence defect and retained the interrupted run as development evidence. The [common-entry preflight](paper/results/appworld_entry_preflight/REPORT.md) subsequently validated controls with common authentication setup; authentication remained a write. The [batched competence report](paper/results/appworld_batched_competence/REPORT.md) records 1/12 and 2/12 successes against a prespecified 8/12 development gate. That gate failed. These exposed tasks can support engineering regression checks, not fresh confirmation or a presumption of a competent comparator.

The [three reviewer reports](paper/reviews/ICLR-1.txt), [including the adaptive-workflow objection](paper/reviews/ICLR-2.txt) and [selection/coverage objection](paper/reviews/ICLR-3.txt), motivate measuring continuation outcomes, accounting for the eligible population, and comparing equally capable alternatives. Adding writes alone does not resolve those objections.

The existing [fulfillment demo](demos/fulfillment/__init__.py) and [provider-free integration controls](tests/integration/test_fulfillment_demo.py) are a useful engineering starting point: they already exercise pagination, conditional read calls, and a host-side commitment. Their current scope is a read prefix followed by one commitment. A separately versioned fixture can add post-commit read boundaries without rewriting historical results. Scripted fixture success is not evidence of adaptive model competence or automatically discovered mutation programs.

## 3. Requirements, assumptions, and exclusions

### Functional requirements

- Discover recurring regions from actual agent traces, preserving failed attempts and explicit model boundaries. Reference programs are execution controls, not a substitute for agent discovery data.
- Dispatch only at host-attested boundaries compatible with the exact artifact, principal, tenant, workflow state, and continuation.
- Compile grounded arguments and predicates over observable values. Leave unresolved semantic decisions with the model.
- Permit repeated entry into qualified regions without replaying earlier effects or silently resetting the interaction budget.
- For compiled mutations, distinguish preparation, publication, unknown outcome, recovery, and continuation.
- Produce enough durable evidence to explain what was attempted, committed, rejected, resumed, or left unresolved.

### Generic core and adapter boundaries

Keep business-specific rules, API names, authentication mechanisms, and storage details outside the compiler core. A workflow supplies typed schemas and reviewed contracts; the compiler discovers admissible recurring structure rather than choosing from task-specific hardcoded recipes. The proposed integration interfaces are:

| Interface | Responsibility |
|---|---|
| Trace adapter | Normalize genuine model boundaries, calls, observations, arguments, provenance and effect receipts without inventing missing decisions or outcomes |
| Workflow host adapter | Attest region entry, expose scoped live-ins, preserve history/budgets, and resume at a durable continuation cursor |
| Tool/effect adapter | Expose typed operations, resource scopes, authorization and enforceable capabilities; unknown capabilities default to refusal |
| Mutation/recovery adapter | Implement prepare, publish, outcome query and recovery semantics for a particular backend; present explicit unsupported capabilities |
| Evaluation adapter | Independently grade the workload's final answer, persisted state and allowed effects for discovery validation, calibration and testing |

The core consumes these contracts and a bounded region IR; it must not contain checks for GitHub, Reddit, AppWorld, or a particular task ID. Domain-specific validators and effect catalogs are legitimate adapter inputs. Human effort to author and maintain them is measured as an integration cost.

Expose separate support states: `HOST_COMPATIBLE`, `REGION_INELIGIBLE`, `CANDIDATE_UNADMITTED`, and `ARTIFACT_ADMITTED`. These are proposed reporting concepts, not existing enum values. A compatible host may produce no admitted region and still run its ordinary workflow. If the host cannot capture required state, GAC stays off on that surface; if publication becomes uncertain, compatibility does not permit unsafe fallback.

The initial PostgreSQL example is an execution-contract testbed, not the product scope. Before claiming architectural portability, run a shared conformance suite against at least two structurally different host/tool integrations, with one demonstrating interior read reuse and one demonstrating a mutation-capable boundary. Register schemas/adapters without editing core domain logic. This is a portability check, not proof of performance across all workflows. A host may support concurrent agents externally; the first optimized regions must be isolated from their conflicting effects or refuse dispatch.

Generic here means **portable contracts with explicit integration**, not interception of an arbitrary black-box agent. A dynamic host without a trustworthy checkpoint/program point is initially unsupported for interior dispatch. The first supported host must own the complete local tool loop, observations, continuation cursor, and checkpoint storage. The existing model-only wrapper cannot supply these properties by itself. Local reads may be demonstrated in a disposable process before durable host support exists, but that demonstration must not claim restart recovery or permission to execute compiled writes.

### Nonfunctional requirements and trusted components

The host adapter, effect catalog, authorization service, backend transaction/deduplication behavior, and evaluation oracle are trusted and versioned components. Model output and tool-returned text cannot grant permissions or attest a boundary. A compromised trusted backend is outside the initial guarantee; schema/effect drift is within the required detection and refusal scope.

The initial implementation has one logical owner per workflow activation and serial execution inside each compiled region. It must survive process termination and duplicate delivery; a single-process assumption cannot justify unsafe replay. Calls, loop iterations, recovery attempts, wall time, and spending have hard bounds. All attempted work remains charged, including discarded staging and reconciliation.

No production availability or throughput target is invented here. M0 must measure candidate lengths, entry frequency, backend latency, and expected reuse. M3 must establish journal and reconciliation capacity before enabling concurrent workers. No live production writes or paid study are authorized merely by accepting this plan.

### Explicit exclusions from the first release

- No whole-agent compilation, unbounded loops, dynamic tool resolution, or arbitrary model-generated executable code.
- No financial transfers, public messaging, destructive production changes, or multi-service sagas as initial compiled-write demonstrations.
- No automatic Git merge or deployment. A coding workflow may prepare changes on a dedicated branch and create a reviewable PR through an authorized host action; the user retains final merge authority.
- No reuse of old read-only certificates to certify mutations, new entry positions, or changed continuation behavior.
- No claim of exact global restoration when logs, quotas, credentials, notifications, time, or other effects remain observable.

## 4. Execution model: regions separated by decisions and commitments

```mermaid
flowchart TD
    A[Host verifies boundary and artifact] --> B{Region admissible?}
    B -- no --> C[Agent continues at current boundary]
    B -- yes --> D[Execute bounded read region]
    D --> E{Contract passes?}
    E -- yes --> F[Agent receives verified observations]
    E -- clean rejection --> C
    E -- restoration uncertain --> I[Incident and reconciliation]
    F --> G[Adaptive decision or authorized host action]
    G --> H[Record completed effect and new boundary]
    H --> A
    F -. later milestone .-> P[Prepare private mutation]
    P --> V[Validate state and effect contract]
    V --> K[Publish through transactional adapter]
    K --> R[Resolve durable outcome]
    R -- committed and verified --> H
    R -- unknown or violated --> I
```

“Continue at current boundary” means preserve all previously completed work and resume the remaining workflow. It never means restart the episode after an earlier write. Even a rejected read attempt may consume quota or change session state; the existing strict fallback contract applies unless a separately named and validated continuation mode permits those differences.

GAC remains an optimizer of an existing host workflow. The host owns adaptive reasoning, authorization and approval interactions, durable workflow identity, and externally visible action policy. GAC owns region discovery, bounded synthesis, admission, dispatch, and execution evidence. Reuse an existing host's durable execution facilities when they meet the contract; avoid creating a general workflow engine merely to optimize regions.

## 5. A new interior-boundary contract

Define a proposed `RegionBoundary` supplied by the trusted host. Its minimum fields are:

| Field group | Required meaning |
|---|---|
| Identity | Workflow instance, region identity, activation ordinal, checkpoint generation, and artifact version. A loop's second visit is a new activation; a retry of the same visit is not. |
| Control position | Allowed predecessor transition and the exact current program point. A tool-name prefix or approximate history match is insufficient. |
| State and inputs | Typed live-ins with provenance, resource identities, version/read-set tokens, and freshness constraints. |
| Prior effects | Durable receipts for completed predecessor effects and explicit status of outstanding actions. No unresolved earlier write is permitted at an ordinary dispatch boundary. |
| Authority | Tenant, principal, policy version, capabilities, and scoped approval reference when required. Credentials themselves are not durable trace payloads. |
| Continuation | History-policy version, model/tool manifest, pending call IDs, resume cursor, consumed budgets, and observation-delivery status. |

A host signature or trusted in-process provenance authenticates the descriptor, but does not prove that its content captures all relevant state. Each adapter must document its observable scope and demonstrate the correspondence through exact-path controls. Incomplete state coverage blocks the proposed mode.

Discovery and calibration must use the same boundary representation and host behavior as deployment. Update region mining, dispatcher selection, artifact serialization, execution manifests, and every enabled host adapter together. An artifact valid at the initial boundary remains initial-only. The read-only prologue mechanism remains unchanged.

For the first interior implementation, permit only a bounded, serial sequence of host-declared region positions. A write invalidates affected observations and dependent predicates. Unknown aliasing or an unversioned dependency causes conservative invalidation. A newly refreshed value must not inherit an old provenance receipt.

Interior mining needs more than a runtime position token. [`_live_in_out`](src/guarded_agentic_compaction/graph/windows.py) currently rejects a needed producer outside the candidate region unless it is represented in episode entry state. Define a versioned boundary-local entry projection that preserves the original producer event/receipt, original workflow and independence group, resource version, and current history. Refit and validate using that exact projection. Never manufacture independent episodes by splitting one workflow into several regions or relabel past outputs as new user inputs without provenance.

Return an explicit outcome to the host: `BASELINE_AT_CHECKPOINT`, `COMPACTED`, or `RECOVERY_REQUIRED` (proposed names). The current runner's `compacted` boolean plus telemetry record must not become a rule that every false result runs the baseline. A test must inject an incident through the actual host adapter and observe that no downstream tool or model action executes. All actions, including ordinary host writes before and after a region, must participate in the same durable intent/receipt convention if crash-resume correctness is claimed.

## 6. Branches and loops: preserve the decision boundary

The first control-flow expansion should reuse existing typed predicates and bounded loops where possible. Examples include “fetch the next page while `has_more` is true” and “read additional metadata when a returned field is absent.” A branch such as “this complaint deserves a refund” remains a model or explicit policy decision unless a separately validated observable rule actually represents that decision.

Require definition-before-use on every path, typed joins, explicit absent outputs, stable entity identity, and branch-specific postconditions. A missing or malformed value must not silently choose a write branch through an operator default. Unsupported predicates or ambiguity must refuse before publication.

For loops, enforce both a static maximum and runtime call/resource budgets. Check target identity and preconditions on every iteration. The first mutation program may make multiple bounded changes within one transaction but has one publication point; partial externally visible loop progress is deferred to a later recovery design. Exceeding the bound aborts unpublished work. A bound failure after publication is a recovery event, never a clean rejection.

Trace support for one branch says nothing about an unobserved branch. Explicitly enumerate reachable branches in the bounded program, challenge each permitted branch, and refuse unsupported paths. Development branch coverage is an engineering check, not an independent-sample risk certificate. New nested branching or loop-body syntax requires a separate expressivity justification and review after the initial milestones.

The initial supported subset is optional call suffixes and existing bounded single-tool repetition. The current synthesizer merges a sequence with a one-step extension; this is not general mutually exclusive branch or multi-tool loop synthesis. For mutation artifacts, require predicate validation to distinguish true, false, and invalid before execution: the existing numeric type-error-to-false behavior cannot select or skip a mutation silently. Do not modify the interpretation of legacy signed read artifacts without a version change. Preserve execution order in the first mutation compiler; defer reordering, parallelization, alias-based batching, and new loop-body syntax. Coarse tool-resource names are not sufficient to prove independence of parameterized writes.

## 7. Mutation contracts and publication

Introduce a proposed `MutationContract` referenced by an artifact and enforced by an adapter. Its fields include backend and resource identity; allowed operation and field changes; authorization; argument provenance; transaction scope; preconditions/read set; desired state relation; allowed secondary effects; publication protocol; retry/deduplication scope and retention; authoritative outcome query; and recovery owner.

Treat effect classification and execution capability as separate axes:

| Operation | Required execution property | Allowed recovery |
|---|---|---|
| Private workspace mutation | Owned filesystem/container, restricted mounts and network, no escaped effects, explicit discard/close contract | Discard before publication; retain real costs |
| Single-backend transaction | All relevant reads and writes share adequate isolation; durable operation receipt and business changes commit atomically | Abort unpublished transaction; reconcile uncertain commit |
| External idempotent operation | Backend-enforced stable operation identity, request-payload validation, documented retention, authorization, and adequate conditional update/outcome APIs | Retry the same operation only within its contract; otherwise reconcile or stop |
| Compensatable external operation | Application-specific compensator with its own authorization, preconditions, durable outcome and failure policy | Compensation is a separate state transition; never claim original-state restoration |
| Unknown or irreversible external effect | No sufficient recovery contract | Keep outside automatic compiled execution |

`WRITE_REVERSIBLE` alone satisfies none of these rows. A sandbox is also not a production transaction: success in a cloned backend cannot be “published” to a live service without revalidating live assumptions and performing a real commit.

For the initial backend, prefer a local PostgreSQL fixture with an application-owned schema, restricted roles, no external triggers/functions, and application-generated identifiers. Use serializable transactions or a reviewed equivalent that covers the entire relevant predicate/read set; per-row version checks alone do not protect aggregate invariants or phantom reads. Keep model reasoning outside open transactions. If a plan was prepared earlier, revalidate all inputs on which its decision depends inside the publication transaction. PostgreSQL documents both isolation differences and the fact that sequence changes are not rolled back; the prototype must account for that rather than claim full database restoration. [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html).

A mutation verifier checks a state transition and effect envelope, not just response text. It must constrain the target identity, fields and rows touched, business invariants, returned outputs, allowed secondary effects, and continuation receipts. For an “add existing items to a collection” fixture, check ownership, allowed item IDs, duplicate policy, untouched collections, and the exact allowed membership delta. Verifying only that the requested items now exist would miss unwanted deletions or edits elsewhere.

Pre-publication validation prevents publication of detected invalid private state. Post-publication verification detects defects but cannot retroactively prevent their effects. A post-publication mismatch freezes the artifact and enters recovery; it is not counted as harmless abstention.

### Compiler work required beyond the transaction adapter

M2 must extend trace capture, resource-dependency analysis, region mining, synthesis, contracts, and execution together. A durable executor alone is not a write compiler. Preserve read-after-write, write-after-read, and write-after-write dependencies at resource/alias scope; unknown conflicts keep operations ordered or make the region ineligible. An effect multiset cannot capture ordering, target identity, or transaction boundaries. Add an ordered effect/commit description with branch-specific allowed transitions.

Introduce an occurrence-aware mutation trace: workflow and activation identity, ordered call/iteration ordinal, input state/version, result/receipt, and transaction membership. Two identical calls can intentionally have different effects and results. Outcome equivalence must also state how generated identifiers or timestamps are compared: verify task-relevant relations and effect receipts rather than demand byte-identical newly generated values, or ignore all differences. Any normalization is a reviewed contract, never a posthoc adjustment made to pass evaluation.

Learn argument bindings only from witnessed, properly scoped values and use reviewed operation semantics. Do not infer authorization, compensation, business invariants, or reversibility from recurring successful traces. Existing argument canonicalization must be re-audited for mutations: a transformation safe for retrieval, such as widening a set of results, may change the intended write targets. A generated mutation must pass the semantic state-transition oracle on fresh disposable development worlds before admission is considered. Recorded-response replay cannot validate actual write effects.

## 8. Durable outcome and recovery protocol

Use an operation identity based on tenant, workflow instance, region activation, logical step/iteration, and an explicit business intent identity. Retries and baseline recovery of the same action preserve that identity. Store the request digest and artifact version with it; changing an artifact must not silently allocate a fresh identity to an unresolved action. Distinct intentional repetitions receive distinct activation/intent identities.

Persist an operation record containing the identity, request digest, authorization scope, preconditions, transaction/backend identifiers, attempt metadata, result receipt, and delivery status. Protect secrets through references and scoped encrypted storage. For the first transactional backend, the committed receipt and business mutation must be atomic in the same database transaction. A durable intent record can precede it, but intent alone never proves completion.

| State | Required fact | Next action |
|---|---|---|
| `PREPARED` | Intent recorded; publication has not been attempted | Validate or abandon private work |
| `COMMITTING` | Publication attempt is durably recorded; outcome may be unknown after a crash | Publish under the adapter contract or query authoritative outcome |
| `COMMITTED` | Authoritative durable receipt exists | Verify postconditions, record continuation, deliver result |
| `ABORTED` | Authoritative evidence excludes commitment and late completion | Resume at the same workflow boundary or create a new authorized plan |
| `UNKNOWN` | A request may have committed, or may still complete | Block dependent actions; reconcile under a bounded policy |
| `INCIDENT` | Contract violation, incompatible state, or unresolved outcome exceeds the recovery policy | Freeze new affected dispatch; retain evidence and hand off recovery |

Required rules:

1. Write intent before issuing an external action. If journal persistence fails, issue nothing.
2. Timeouts, cancellation, connection loss, and worker death are not evidence of nonexecution. A remote action can complete after the caller stops waiting.
3. An authoritative “not found” must have sufficiently strong consistency and exclude still-running/late requests before it licenses a fresh attempt. A list/search endpoint with eventual consistency is insufficient.
4. Retry only when the backend enforces the operation identity or a transaction proves no commitment. Preserve the same payload and identity; reject a mismatched payload. AWS describes why server-side deduplication and atomic recording matter. [Idempotent API design](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/).
5. Deduplication retention must exceed the permitted recovery window. Expired or unverifiable retention blocks blind retry. Never claim end-to-end exactly-once execution from a client-side log.
6. Concurrent recoverers must not both own an action. Use a durable claim plus backend-enforced fencing, uniqueness, or compare-and-set as appropriate. A lease alone cannot stop a stale worker from writing.
7. Deliver a committed observation with a stable receipt ID and persist the continuation cursor. If a crash occurs after publication but before delivery, redeliver the receipt without repeating the action. The host must deduplicate downstream actions across repeated delivery.
8. A kill switch stops new publication attempts but does not cancel already accepted remote effects. Reconciliation remains available after retirement or upgrade.

Authorization is evaluated before publication using current policy and the actual target. Approval, if required, binds to the intent, payload, resource/version constraints and expiry; changing them invalidates approval. Waiting for approval does not hold a database transaction open. Recovery reads and already-authorized operation reconciliation have explicit privileges; a permission failure must not be misreported as an absent operation.

### Concrete first-backend protocol

Use an application-owned database, typed operations on a fixed schema, and one database transaction per bounded mutation program. A harmless first fixture is adding explicitly identified existing items to an owned collection with an exact membership-delta oracle. No arbitrary SQL, external hooks, email, payment, or shell actions are available to the compiled program.

1. Persist an immutable intent with a unique `(tenant, workflow, activation, intent)` identity, canonical payload digest, and pinned contract. Separate a region's publication identity from its internal step/iteration identities: multiple steps in one atomic region produce one commit receipt.
2. Open a transaction with the pinned isolation policy. Lock/claim the intent under a consistent ownership protocol, then read the authoritative receipt. A matching committed receipt returns the saved result; a payload mismatch refuses.
3. Recheck authorization, resource versions, predicate/read dependencies and approval constraints within the publication boundary. The local adapter must coordinate policy changes through the same database consistency/locking contract. An unrelated authorization server would introduce another race and is outside this first fixture.
4. Execute ordered typed calls and validate the resulting state delta in the transaction. Store the commit receipt, ordered effect summary, result payload/reference and continuation-delivery intent atomically with the business changes. All participating application writers must respect the reviewed invariant/locking protocol.
5. Commit once. A confirmed serialization/deadlock abort may retry the **entire** transaction within a bounded policy, re-reading and revalidating dependencies. An uncertain connection outcome enters reconciliation instead. Reuse the same intent identity; never retry only the last SQL statement.
6. Recovery uses a fresh connection and the same ownership/intent protocol to wait out an in-flight transaction and check its receipt. A missing receipt from an old snapshot is not proof of abort. Database unavailability keeps the action unresolved.
7. Deliver the durable result to an idempotent host checkpoint transition. If checkpoint storage is separate, use the durable delivery intent and retry delivery; do not claim an atomic database-plus-host update. Downstream actions reuse recorded identities after recovery.

Database locking and retry semantics must be tested against the pinned version; PostgreSQL documents transaction-level locks and the need to retry serialization failures. See [transaction isolation](https://www.postgresql.org/docs/14/transaction-iso.html) and [explicit locking](https://www.postgresql.org/docs/14/explicit-locking.html). This protocol is proposed; the local probe in section 15 validates only a subset of its mechanism, not this complete host integration.

Compensation is deferred. If later supported, it must preserve concurrent legitimate changes and expose its own failure outcome. It cannot retract every notification or observation caused by the original action. [Compensating transaction pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction).

## 9. Correctness claims and statistical admission

Keep the following obligations separate:

**Execution obligation.** Under the documented host/backend assumptions, an unauthorized call is blocked before execution; unpublished mutations stay inside the owned boundary; uncertain publication never becomes ordinary fallback; completed actions are not blindly repeated; and all recovery paths terminate or enter a visible incident within configured bounds. These are design and implementation obligations checked through state-machine analysis and adversarial tests. Finite testing alone is not a universal proof.

**Semantic obligation.** The compiled region preserves the specified task state transition and continuation behavior, including relevant effects. Runtime shape/provenance checks are not sufficient to prove semantic task correctness. Reference replay is useful for development; an independent task oracle must grade final persisted state and final answers through the actual adapter path.

**Empirical admission obligation.** Freeze the candidate, host adapter, entry contract, continuation, routing/threshold rule, loss, sampling frame, and multiplicity treatment before fresh calibration. Sample before filtering on baseline success or region occurrence; every member of the declared deployment population needs a disposition. Keep no-match cases, rejection, fallback, infrastructure failures, unknown outcomes, and incomplete runs visible.

Specify the denominator for each claim. Full-workflow quality includes all scheduled members of the sampled population, including fallback. Conditional risk among optimized episodes uses the frozen selection policy and the corresponding selected groups; low coverage cannot establish that conditional risk by diluting failures with baseline-only cases. Infrastructure failures receive a prespecified conservative disposition, never silent exclusion. Report both unconditional workflow outcomes and conditional optimization outcomes with their own uncertainty and coverage.

Selection for the conditional metric is defined at **dispatch attempt**, before knowing whether execution, verification or commitment succeeds. Include failed, unresolved and incident attempts; counting only successfully compacted completions would bias the denominator. At workflow level, record whether any optimized attempt occurred and whether any relevant violation occurred under the frozen policy. This is a different metric from per-call violation rate.

Measure at least these distinct outcomes: absolute final task failure; compiled-only failure against the paired unchanged agent; effect-contract violation; unresolved publication; and complete workflow cost. Both arms failing is not evidence of adequate quality. A clean refusal can be a successful mechanism outcome while the resulting full workflow still fails. Do not label post-commit defects as abstentions or drop them because no final answer was produced.

A fixed-candidate certificate does not automatically cover a selected portfolio, repeated adaptive region activations, or changing routing. Per-region error probabilities cannot simply be added unless their conditional validity over encountered histories and the activation bound are established. The first empirical release should therefore calibrate and evaluate the **whole frozen bounded orchestration policy** on independent task groups. Per-region results remain diagnostic until a composition argument is specified and reviewed.

For a zero-violation fixed-policy calibration sample of size `n`, use `epsilon` for the tolerated violation rate and `delta` for confidence failure probability: the one-sided exact upper bound is `1 - delta^(1/n)` under independent Bernoulli sampling. A prespecified union-bound treatment for `m` tested policies/thresholds replaces `delta` by `delta/m`; it does not repair adaptive reuse of holdout data or dependence. This notation avoids confusing the current `GrcConfig.alpha` risk target with confidence failure probability. Use this only as a feasibility calculation, not a claim that future data will contain zero violations. Choose the target loss margin and confidence level before running; report no-go if the available independent groups cannot support them. Do not copy a historical sample threshold without recomputing its assumptions.

Build an explicit orchestration-level labeling/admission path. It must execute the frozen substituted workflow and continuation, persist final state, invoke the independent oracle, and retain outcome/attempt/incident labels. The current `_calibration_samples` helper cannot be relabeled as this path. Existing narrower evidence remains intact. A runtime need not have a perfect generic semantic oracle: distinguish enforceable runtime effect checks, offline task evaluation, and the scope of a resulting statistical claim. If the task lacks a defensible final-state/answer oracle, make no end-to-end certified quality claim for it.

Task variants, repeated seeds, shared scenario templates, and correlated retries do not create new independent groups. Predeclare a defensible grouping and group-level loss/estimand or a justified dependence-aware analysis. For paired task success comparisons, predeclare the noninferiority margin and paired analysis; absence of a significant difference is not noninferiority. Safety-critical effect constraints remain hard requirements even if average task quality is acceptable.

## 10. Evaluation program and meaningful comparators

Use two tracks. A provider-free controlled fixture establishes execution semantics, fault handling, and state/effect oracles. A separate adaptive agent workload evaluates usefulness. Handwritten fixture programs can validate the executor but cannot demonstrate automatic discovery or model-call savings.

Select adaptive workloads prospectively using public task metadata and development-only evidence. Require substantial model decisions between recurrent regions, a competent unchanged baseline, useful automatically synthesized candidates, sufficient fresh groups, and an oracle that checks actual side effects. The current AppWorld and browser development tasks remain exposed; neither is automatically approved as the final workload. Common authentication/setup must be identical and charged across arms. Benchmark-specific rules and adapted entry conditions must be disclosed.

### Workload shortlist and competence record

The census (section 0, H1) ranks these; the retained competence evidence is what rules candidates in or out today.

| Workload | Adaptive decisions between reads | Unchanged-agent competence on record | Independent groups available | Side-effect oracle | Status |
|---|---|---|---|---|---|
| WebArena-Verified, single-site Reddit (106 tasks, 190 templates overall) | Yes: navigation and form decisions between page reads | 6/6 on the development pilot (`paper/results/adaptive_benchmark_screen/`) | Templates are the unit, not task instances; ~190 templates, fewer per site | Official HAR/network-event graders | Leading candidate; needs the census to show interior read recurrence across templates |
| BIRD text-to-SQL (dev + train, 31 databases) | Yes: table choice and query repair | Competent (94/150, 403/630) | Questions within a database are correlated; databases are the honest unit (31) | Exact result-set grader | Interior read regions after the schema-first opening are the question; per-question table reads already retire (section 2 of the paper) |
| AppWorld | Yes | Failed the 8/12 gate twice (1/12, 2/12) | 750 tasks, but variants of a scenario share a supervisor and database (46 scenario and 79 supervisor units in the retained 136-task corpus) | Official state-based grader | Excluded until a competent baseline exists |
| AgentHop | Yes | 19/24 (passed) | Source-overlap component makes groups non-independent | Exact multiple choice | Excluded: no source-independent groups |
| GitHub families (existing) | No | Competent | 92-group cohorts, 3,560 end-to-end groups | Exact contracts | Track P1 only (H3, H4) |

### The comparator arms, made concrete

- **Simpler compiler, same IR.** Recurrence-only replay extended to interior boundaries: every region that recurs with identical tool names across the support floor is compiled with literal arguments, no grounding, no verifier, no gate. It runs in a disposable environment only. This is the arm that isolates GAC's grounding and admission from its infrastructure.
- **Hand-written bounded program.** Written by an author with full workload knowledge before seeing GAC's candidates, frozen by hash, with the same tool budget. If it matches GAC (as on GitHub), H2 is refuted for that workload and the paper says so.
- **Executable compiler (H4).** TraceCompiler is the only closely related system with a described implementation; EvoC2F's code endpoint returned HTTP 401 (`flip-plans.md`); Agent JIT is a web-task planner whose SQL adaptation scored 4/36 against 26/36 for the unchanged agent (`paper/results/adaptive_compiler_pilot/`). If TraceCompiler's code is not runnable, the simpler-compiler arm is the comparator and the paper says no external compiler was run.

Compare:

| Arm | Purpose |
|---|---|
| Unchanged adaptive agent | Establish task competence and total workflow cost |
| Handwritten bounded workflow/composite | Test whether equivalent manual optimization explains the benefit |
| Simpler compiler using the same IR, tools, boundaries, transaction adapter and budgets | Isolate the value of GAC's discovery/admission rather than infrastructure advantages |
| Full GAC | Evaluate the frozen automatic selection and guarded execution policy |

Add support-only versus learned-selection comparisons only when development feasibility supports at least two positive certified coverage levels on a common held-out population. Keep risk budgets and threshold-search accounting equal. If this is infeasible, report the limitation instead of promising a learned-gate result. Unsafe compiler ablations run only in controlled disposable environments; production controls are never removed to manufacture a comparison.

Pair arms on equivalent isolated initial states; freeze model, prompt/history policy, tool catalog, initialization, limits, oracle, and sampling weights. Randomize or balance execution order where drift matters. Do not replay a previous model answer and call it fresh adaptive continuation. Preserve candidate generation failures and the full rejection funnel, including all admitted and retired families.

Report task success, effect correctness, incident and unknown-outcome rates, coverage by workflow boundary, end-to-end fallback success, model/tool calls, p50/p95 latency, total tokens/cost, and recovery work. Separate normal workloads from injected-fault workloads. Include preparation, validation, discarded attempts, reconciliation, setup, offline discovery/calibration, maintenance, and human authoring effort where measured. Unpriced costs remain explicit.

The reuse break-even calculation is `N > offline_cost / (baseline_per_run_cost - optimized_per_run_cost)` only when the denominator is positive and the workload/maintenance assumptions hold. A one-call saving can be erased by state hashing or transaction overhead. Freeze a realistic expected reuse horizon before using break-even as a go criterion. Feature support without economic benefit is a valid outcome.

## 11. Implementation milestones and stop/go decisions

Each row is a separate reviewable PR or small PR series. These revised estimates include work omitted or understated in the first plan: boundary-local provenance, durable host outcomes, occurrence-aware mutation traces, predicate validity, and a new workflow-level admission path. They are engineering judgments for one experienced maintainer, not measured implementation velocity or delivery commitments. Re-estimate after M0. No PR is merged automatically.

| Milestone | Deliverable and primary code areas | Exit gate | Rough effort |
|---|---|---|---|
| **P0: interior-region census (gate for everything below)** | Extend `paper/scripts/prefix_census*.py` and `paper/results/prefix_census/` to non-initial boundaries: for each retained corpus, the share of trajectories with an interior read-only region of >= 2 calls whose arguments pass the current witness rule, and the independent-group support of each candidate family. Thresholds are the ones in section 0 (H1), declared before the count. Provider-free; $0. | H1 passes on at least one corpus, or the plan drops to P1 only. The result is reported either way, as a census table in the paper. | 3-5 person-days |
| **P1: matched compiler comparison on the GitHub families** | Run `paper/supplementary/matched-compiler-candidate-protocol.md`: TraceCompiler if runnable, else the same-IR recurrence-only compiler, on the three families and the 3,560-group end-to-end cohort; report both rejection funnels; force-run retired candidates in a disposable environment to measure H3. | Pre-registered margin and funnel reported; no promise of a win. Answers R1-W2 and R2-W2 directly. | 6-10 person-days plus under $50 of provider calls |
| **P2: interior read regions on one adaptive workload** | Needs M1a and the orchestration-level label/admission path (section 9). Freeze the workload chosen by P0, the competent baseline, the hand-written and simpler-compiler arms, the whole-policy admission rule and the sample size before any provider call. | H2 and H3 measured on fresh independent groups; the whole frozen policy admitted or retired. A retirement is a reportable result. | M1a (8-12 days) + label path (8-15 days) + study; sample cost computed from the census and the baseline's per-episode cost before approval |
| M0: feasibility and specification | Inventory actual traces/rejections; define a versioned fulfillment-based interior-read fixture and a collection-mutation fixture; audit the application-owned host; freeze boundary, state-machine and oracle specs. | Engineering go requires sufficient observable state, a working exact-path fixture and an enforceable backend contract. Scientific go separately requires genuine trace recurrence, competent baseline and a plausible independent-data/reuse budget. A failed scientific gate need not block a clearly labeled engineering prototype. | 3–5 person-days |
| M1: interior read regions | M1a: boundary-local trace/provenance, mining/dispatch and current-boundary continuation (8–12 days). M1b: durable activation/checkpoint ownership, explicit incident propagation, receipt delivery and crash/restart controls (6–10 days). Touch `schema/traces.py`, `schema/artifacts.py`, `graph/windows.py`, `grc/compile.py`, `runtime/dispatch.py`, `runtime/runner.py` and one host adapter. | Prefix regressions and exact boundary/history controls pass. M1a is a disposable in-process demonstration only. Supported interior reuse requires M1b; the host must prove no action after an unresolved incident and no replay of predecessor writes. | 14–22 person-days |
| M2: owned transactional writes | M2a: typed adapter, intent/receipt schema, atomic publication, restart/reconciliation and host delivery (8–14 days). M2b: occurrence-aware traces, ordered mutation IR/synthesis, predicate validity and state-transition equivalence (7–12 days). M2c: integrated fault/concurrency, authorization, legacy-compatibility and exact-path oracle controls (5–9 days). Add proposed transaction/journal modules; keep the current read facade unchanged. | M2a alone is an executor demonstration. Complete M2 requires generated bounded programs through the checked path, all failure gates and explicit research-only status until new admission evidence exists. No read-only artifact is silently upgraded. | 20–35 person-days |
| M3: one external write adapter, conditional | Backend capability audit, request identity, reconciliation, credential handling, revocation, and fencing/deduplication tests. Extend the journal contract through one explicit adapter. | Service actually supplies required semantics under documented failure/retention assumptions. If not, leave its writes with the host agent. | 10–20+ person-days if feasible |
| M4: portability and fresh adaptive comparison | M4a: second integration and orchestration-level label/admission adapter, reusing a suitable validated runner (8–15 days; re-estimate if unavailable). M4b: frozen actual-agent discovery, competent baseline, independent splits, fixed-policy admission, matched comparison and analysis. | Portability requires both integration conformance checks. Scientific go requires a full-workflow oracle and a computed affordable sample. No paid expansion solely to compensate for a failed competence or recurrence gate. | M4a 8–15 person-days; M4b acquisition, compute and research iteration not bounded yet |
| M5: limited adoption and maintenance | Read-only shadow selection, isolated mutation trials, then opt-in canary for eligible adapters; telemetry, retirement and recovery runbooks. | Defined operational limits, responsible recovery owner, and evidence for the intended deployment scope. No uncontrolled write shadowing. | 5–10 person-days, scope-dependent |

P0 gates P2 and M1; a negative census leaves P1 and Track E. M0 may approve only M1 if transactional writes offer no useful recurrence. M1 and M2 do not require external services. M4 can begin after the relevant engineering gates pass; completing M3 is not necessary to study adaptive workflows. Cross-service compensation, parallel write branches, broader DSL syntax, and a general durable workflow service require a new plan after demonstrated need.

### Revised schedule and first-week decision package

M0–M2 totals **37–62 person-days**, roughly **8–13 working weeks** for the supported single-backend engineering prototype. Reserving 25% for integration/review failures gives a planning allowance of approximately **10–16 weeks**. A smaller M1a demonstration can appear in about 2–4 weeks; it is not the durable write-capable deliverable. The earlier 5–9-week estimate was optimistic for the full stated recovery scope.

Adding M4a and M5 gives 50–87 person-days before a limited deployment could be considered, **conditional on M4b admission evidence**. Adding optional M3 gives 60–107+ person-days. These sums exclude data acquisition, paid runs, failed scientific gates, review waiting time and an existing durable-host integration that proves unavailable; they are not a production-readiness deadline. Two engineers can divide fixture/oracle work from the core after interfaces stabilize, but the boundary-to-journal critical path does not halve automatically.

The first 3–5 working days must produce: (1) a host capability matrix and observable-state inventory; (2) a minimal boundary-local trace with preserved provenance/group identity; (3) fixture/oracle controls through the exact adapter; (4) a mutation protocol and failure-state table; (5) candidate rejection/headroom counts from retained actual-agent traces, kept separate from synthetic controls; and (6) an updated work breakdown, sample feasibility and explicit go/no-go for each track. Stop expansion if the host cannot own the boundary or the backend cannot enforce commitment semantics. Stop confirmatory research if competent adaptive behavior, useful recurrence, independent groups or affordable inference are unavailable.

## 12. Required validation matrix

Future implementation PRs must test effects and durable state, not merely returned status codes. Use an independent observer and the actual host-to-backend-to-grader path. Deterministic fixtures and bounded state-machine exploration should cover crash points; randomized testing supplements them.

| Scenario | Required observation |
|---|---|
| Wrong boundary, changed tenant/principal, stale manifest, missing provenance | No optimized tool invocation and no write |
| Same core used through two different host/tool adapters | Shared conformance rules pass without task-specific branches in the compiler; unsupported capabilities are explicitly refused |
| A read region follows an earlier successful write | Rejection resumes at the current checkpoint; the earlier write is not repeated |
| Skipped branch, malformed predicate input, unsupported path, bound exhaustion | No unintended calls; no publication of invalid staged state |
| Repeated identical arguments at different occurrences, generated IDs, or stale boundary projection | Correct occurrence/receipt and reviewed state equivalence; no last-result substitution or lost provenance |
| Permission/approval changes between prepare and publish | Publication denied before effects; stale approval is not silently reused |
| Concurrent insert/update invalidates a read predicate | Transaction conflict or explicit refusal; no stale-plan publication |
| Reordered conflicting writes or retrieval-oriented argument widening | Compiler rejects the invalid transformation; state-transition oracle detects incorrect effect order/targets |
| Mutation succeeds but response is lost | Durable outcome is found; the action is not blindly repeated |
| Receipt committed but host checkpoint delivery is lost | Same receipt is redelivered; predecessor or downstream writes are not recreated under new identities |
| Crash before send, during commit, after backend success, before journal acknowledgment, before/after continuation delivery | Exactly the contractually allowed recovery transition; stable action identity and no false clean fallback |
| Cancelled request completes late | Recovery blocks conflicting continuation and detects/reconciles completion |
| Two workers recover the same operation, including a stale lease holder | Backend enforcement prevents duplicate effect or stale publication |
| Deduplication expiry, payload mismatch, nonauthoritative absence, backend query denied | Explicit unresolved/incident state rather than retry with a fresh key |
| Post-publication verifier failure | Committed effect remains visible; artifact frozen and recovery invoked |
| Trigger, filesystem, session, audit or outbound effect escapes claimed boundary | Adapter/mode rejected or contract violation detected; DB-only equality is not advertised as complete restoration |
| Kill switch or artifact upgrade during an in-flight operation | New dispatch stops; existing intent remains recoverable under its pinned schema and identity |
| Known-correct sequence, empty run, false completion, save/flush failure | Actual grading recognizes the positive control, rejects negatives, and reports persistence failure as infrastructure failure |

Reuse current prefix/prologue, loop, effect, continuation, property and fault-injection suites as regressions. Add new tests only with the corresponding implementation. For empirical studies, independently validate the persisted final-state oracle; a shared bug between executor and verifier cannot count as agreement evidence.

## 13. Compatibility, lifecycle, and deployment

Introduce explicit artifact kinds or execution-contract versions; old artifacts retain existing hashes and semantics where their serialization is unchanged. Old runtimes must refuse unknown mutation modes. Changed boundary, backend, catalog, authorization policy, verifier, continuation, or loss requires explicit compatibility review and fresh evidence where the change affects behavior. No migration should relabel existing read-only evidence as write evidence.

Define migrations for durable journal schemas before shipping M2. Recovery must remain able to read pinned in-flight records across a software rollback. Never delete deduplication/receipt state merely because an artifact expires. Journal retention must cover backend retry windows and audit/recovery requirements; privacy controls constrain stored payloads.

Proposed immediate retirement triggers are any unauthorized effect, duplicate committed action, incorrect-target mutation, unresolved outcome beyond its configured recovery deadline, or invariant failure. Freeze the affected artifact/adapter and resolve in-flight work. Thresholds for quality, coverage, latency and cost drift must be set prospectively in M4/M5; do not repeatedly inspect ordinary fixed-sample intervals and call them sequential guarantees. Reactivation requires a documented cause/fix, regression controls, a new version, and fresh calibration for the affected policy/population.

Keep telemetry for commit attempts, outcomes, unknown age, recovery latency, deduplicated requests, blocked stale owners, authorization refusals, invalidated observations, fallback position, and complete cost. Dashboards must distinguish “no duplicate observed in tests” from an enforced backend guarantee.

This planning PR changes no runtime, dependencies, configuration, migrations, manuscript claims, numerical results, or generated publication artifacts. Later behavior changes require their own documentation and release-evidence updates. Deployment remains opt-in; each implementation PR follows the repository template, requests available reviewers, and remains open for the user's final merge.

## 14. Critic's review and disposition

This section records a second-pass adversarial review of the design. It is a self-review, not independent reviewer approval. Findings must lead to a revision or an explicit gate; listing a concern alone does not resolve it.

| Criticism | Disposition in the revised plan | Residual limitation |
|---|---|---|
| “Reads can already be inserted anywhere, so just alternate them with writes.” | Corrected: current prefix/prologue restrictions are explicit; M1 requires a new host-attested boundary, matching discovery, and current-checkpoint continuation. | Each host integration still needs evidence that it captures relevant state. |
| “A PostgreSQL prototype makes GAC a task-specific workflow tool.” | Corrected: generic core/adapter interfaces and explicit support states are requirements; M4 adds a second structurally different integration without core domain logic. | Two integrations establish bounded portability evidence, not universal applicability or savings. |
| “Branch support is new and unrestricted control flow is necessary.” | Corrected: existing predicates/bounded calls are reused; richer DSL constructs require demonstrated need. | Some useful workflows will remain unoptimizable. |
| “A write timeout is an ordinary tool failure.” | Rejected: the old facade's pre-commit exception contract is retained only for its existing scope; mutations have explicit unknown outcomes and durable recovery. | External backends may not support authoritative reconciliation. |
| “An idempotency key or local journal gives exactly-once behavior.” | Rejected: backend enforcement, payload binding, retention, atomic receipts, late-completion handling and concurrent-owner control are required. | End-to-end exactly-once is not claimed. |
| “Checking versions immediately before writing fixes all races.” | Corrected: validation must be atomic with publication and cover predicate/read-set dependencies, not only the written row. | External APIs lacking adequate conditions remain ineligible. |
| “A cloned sandbox, transaction rollback, or compensator restores everything.” | Rejected: publication is separate; sequence/log/session/notification effects are scoped explicitly; compensation is deferred. | Exact global restoration is generally unavailable. |
| “Post-write verification prevents bad writes.” | Corrected: prevention is before publication; failed postchecks are incidents with real committed effects. | A semantic verifier can still miss an incorrect business decision. |
| “Adding a transaction adapter is enough to compile mutations.” | Corrected: M2 includes trace semantics, ordered effect dependencies, mutation-safe argument synthesis and state-transition validation. | Automatic synthesis may still find no useful admissible mutation region. |
| “Per-region certificates automatically compose.” | Rejected: first admission is for the frozen bounded full orchestration; composition needs conditional validity and a separate argument. | Fresh whole-policy calibration may be expensive or infeasible. |
| “Baseline fallback cases can dilute the risk of optimized actions.” | Rejected: conditional optimization risk and full-workflow quality have explicit separate denominators, coverage and uncertainty. | Small admitted samples may make conditional claims infeasible. |
| “A more complex benchmark will necessarily demonstrate value.” | Rejected: baseline competence, actual automatic synthesis, fresh independent groups, matched interfaces, and lifecycle economics are binding gates. | AppWorld's retained competence failures remain unresolved. |
| “This is a new workflow engine disguised as an optimizer.” | Reduced: the host retains orchestration and approvals; one transactional adapter is the initial mutation scope, and an existing durable executor may supply the journal contract. | Adapter and evidence-maintenance costs may outweigh saved model work. |
| “More features will answer the reviewers by themselves.” | Rejected: task outcomes, population accounting, matched comparators, and selection-valid evidence are separate deliverables. | No acceptance or superiority claim follows from this plan. |
| “The plan has no research question; it is a build list.” (2026-11-08 review) | Corrected: section 0 states four hypotheses with thresholds declared before the census, and names which venue each supports. | Thresholds are judgments; a passed threshold is not a result. |
| “The first write fixture (add items to a collection) is trivially hand-written, which is exactly R2's objection.” | Accepted: the fixture stays as an executor control for Track E; it is excluded from any publication claim. H2 requires a program a person would not write first. | Track E may still produce nothing publishable at an ML venue. |
| “A certified compiled-write result is unaffordable.” | Accepted: section 0 states it is not publishable on this budget; Track E is mechanism-only. | The systems-venue paper needs a workload with real writes that this project does not yet have. |
| “Headroom is the real unknown and is deferred.” | Corrected: P0 is now the first milestone and the gate for M1 and P2, with thresholds fixed in section 0. | A positive census does not guarantee a competent baseline on the same workload. |

### Remaining design decisions and final go/no-go judgment

M0 must resolve the exact first adaptive workload, competent baseline configuration, host boundary representation, transaction fixture, independent-group supply, and cost/reuse targets. M2 must resolve the concrete journal schema, atomic publication protocol, recovery ownership, and retained-state lifetime. M3 remains conditional on a real service's enforceable API guarantees. These are explicit prerequisites to their implementation phases, not details to guess during rollout.

**Judgment after critique:** the narrowed, application-owned architecture is feasible to investigate and has a concrete implementation route. The first plan understated integration, mutation replay and admission work; the revised phases and schedule above address those omissions. The local backend mechanism has been probed, but expanded GAC execution has not been implemented. Broad external-write compilation and practical superiority remain unproven. Proceed with the engineering gates and preserve the scientific stop conditions.

## 15. Deeper feasibility audit: findings and evidence

This additional review was performed after PR #119 merged. It is a source audit, focused regression run and small provider-free backend probe, not an independent review or completed M0–M2 implementation.

| Finding | Evidence | Required correction incorporated above |
|---|---|---|
| High: the model-only SDK wrapper cannot own post-emission restoration | `runtime/model_provider.py` documents its ownership limit and restricts supported program steps. | Start with an application-owned host, retain the narrow wrapper, and distinguish a demonstration from durable support. |
| High: interior inputs are rejected before dispatch can even help | `graph/windows.py::_live_in_out` rejects non-entry producers outside the region. | Add boundary-local trace projection with provenance and original group identity in M1. |
| High: the existing replay lookup cannot represent stateful repeated calls | A local probe added two results for the same tool/arguments; exact lookup returned the second observation. | Add occurrence/transaction/receipt identity and actual-world execution for mutations. |
| High: invalid predicates can look like a legitimate false branch | A local probe evaluated a numeric predicate on a string and obtained `False`. | Add explicit validity checks for the versioned mutation mode; do not silently reinterpret legacy artifacts. |
| High: output-agreement calibration is not workflow-effect calibration | `_calibration_samples` compares recorded outputs only after interpreter/verifier success. | Build M4a's explicit workflow-label path and include attempted failures/incidents in denominators. |
| High: durable host delivery was specified but insufficiently budgeted | `runtime/runner.py` exposes observations and telemetry; the proposal needs persistent activation, delivery and incident-handling semantics beyond that interface. | Split M1a/M1b, specify a durable delivery intent, and revise the critical-path estimate. |
| Medium: arbitrary branch/loop and alias analysis would expand scope substantially | Current synthesis handles optional suffixes and repeated single-tool calls; catalog resource conflicts are tool-level. | Preserve order, constrain expressivity and defer speculative reordering/parallel writes. |
| Medium: research gating could block even a useful engineering investigation | Retained AppWorld runs fail competence; a new mutation runtime is needed before authentic mutation discovery can be evaluated. | Separate fixture-backed engineering go from actual-agent scientific go; do not fabricate model boundaries or claim fixture savings. |

### Checks performed and limits

- **119 existing tests passed:** 86 across prefix boundary, prologue, loops/bounds, effects/schema, continuation and fault injection; 33 across backend and fulfillment integrations. These exercise current behavior and constrain the plan; they do not validate future features.
- **Three direct source-behavior probes:** occurrence-insensitive exact replay lookup; invalid numeric predicate returning false; and reversible-write refusal before executor invocation. The first two are extension hazards, not a claim that all current read-only use is incorrect.
- **Four local PostgreSQL controls passed on 14.19:** mutation and receipt roll back together; concurrent deliveries of one intent mutate once; a deliberately discarded reply is recovered through the saved receipt; and a changed payload under an existing identity is rejected. The concurrent duplicate incurred one serialization retry and then returned the original receipt. The isolated Unix-socket-only cluster was stopped afterwards; no existing database service or application data was used.
- The probe used a counter table and a unique receipt table, a transaction-level advisory lock by operation identity, serializable transactions, and a bounded whole-transaction retry on confirmed serialization/deadlock errors. It tested a cooperative local adapter, not arbitrary writers, authorization revocation, process-kill coverage, remote network partitions, full host checkpoint delivery, or GAC-generated programs. The first probe attempt failed a harness assertion because command-mode output omitted the intermediate result; using script input corrected the observation path. That initial failure is not a backend correctness finding.
- **Sample arithmetic independently checked** against the repository's `clopper_pearson_upper` helper, including that one fewer group fails the selected zero-event target. The illustrative 95% confidence requirements are below; no empirical risk target is selected by this calculation.

| Violation-rate upper target | One frozen policy, zero violations | Eleven prespecified tests, zero violations |
|---|---:|---:|
| 5% | 59 selected independent groups | 106 selected independent groups |
| 1% | 299 | 537 |
| 0.1% | 2,995 | 5,391 |

These are **selected** group counts. At 10% dispatch-attempt coverage, the planning expectation is roughly ten times as many sampled groups, with additional uncertainty in realized coverage and any violations increasing requirements. Repeated variants do not make up missing independent groups. A 5% engineering quality target is not an acceptable default for harmful external effects. This is why M4b has no promised duration or automatic go decision.

To rerun the focused source regressions from the audited checkout with an installed project environment:

```sh
PYTHONPATH=src python -m pytest -o addopts='' -q \
  tests/unit/test_dispatch_prefix_boundary.py tests/unit/test_dispatch_prologue.py \
  tests/unit/test_loops_and_bounds.py tests/unit/test_effects_and_schema.py \
  tests/unit/test_continuation.py tests/fault_injection/test_fault_injection.py \
  tests/integration/test_backends.py tests/integration/test_fulfillment_demo.py
```

Review assessment by dimension: **correctness—conditional feasibility after the listed gaps are addressed; security—enforceable only within the stated host/backend trust boundary; performance—unproven pending headroom and full-cost measurement; maintainability—credible with versioned adapters, serial execution and preserved legacy behavior.** No test or design review can establish universal feasibility for arbitrary agentic workflows. The next authorized engineering decision should be M0, with a supported prototype target and a separate evidence budget.

## 16. Venue plan and timeline

Dates marked (proj.) are third-party projections from the previous cycle; the official calls had not been posted when this was written. Verify before planning around them.

| Path | Submission | Venue and date | What must be true | Risk |
|---|---|---|---|---|
| A. Strengthened resubmission | Current paper with P1 (H3, H4) added; learned-gate material removed; safe-automation framing | ICML 2027, ~22 Jan 2027 (proj.); fallback COLM 2027, ~Mar 2027 (proj.) | P1 complete by mid-January; 3,560-group study already in hand | Reviewers may still rate the metadata tasks as low value; the compiler comparison and funnel are the answer |
| C. Interior reuse paper | A + P2 on one adaptive workload | ICML 2027 only if P0 is positive by late November and P2's sample is affordable; otherwise COLM 2027 or NeurIPS 2027, ~May 2027 (proj.) | H1 passes; a competent baseline (WebArena-Verified is the live candidate); whole-policy admission on fresh groups | Highest upside; dies on a negative census or an incompetent baseline, in which case the census itself goes into A as a scope result |
| B. Mechanism paper (Track E) | Interior-boundary contract, mutation contract, durable recovery, fault-injection evaluation | OOPSLA 2027 Round 2 (7 Apr 2027) is too close after a 10-16 week build; realistic targets are MLSys 2028 or OOPSLA 2028 Round 1 (~Oct 2027) | A workload with real writes; soundness argument for the ordered mutation IR; concurrency and crash tests of section 12 | Not an ML-venue paper; competes with durable-execution systems on their ground |

Recommended order: P0 this week; P1 in parallel; decide A versus C on the census; Track E continues only as engineering, with no 2027 submission depending on it.

### Status, 2026-11-08

P0 (census), P1-lite (same-IR funnel) and the funnel's live pilot have run; the evidence and its
limits are synthesized for path A in `paper/supplementary/expansion-evidence-synthesis.md`
(LaTeX draft `paper/iclr/sections/expansion_evidence_draft.tex`, not input by the ICLR build).
In one line each: H1 passes on tau-bench (one pattern, support 96 against a floor of 92) and on
OpenHands (37.5% of it a `think`-frontier artifact), fails on SWE-agent; statistical admission
changed no compile-time decision on 13 cohorts and grounding changed one, which did not recur on
fresh issues and cost nothing measurable live (65/65 vs 63/65 vs 64/65); H2 and H4 remain
unmeasured. The decision between A and C stays open on the census alone; A is fully supported
by what is in hand.
