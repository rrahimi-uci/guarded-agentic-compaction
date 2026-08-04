# Guarded Agentic Compaction

## Trace-Derived Region Programs for Dynamic LLM Agents

**Revised proposal — v2.1, implementation-aligned 4 August 2026**
*Supersedes v1, which remains available in Git history. Changes are itemized in §0.*
*Current companion: [use-cases.md](../docs/use-cases.md) — implemented APIs, measured
scenarios, and evidence boundaries. The longer v2.1 illustrative monograph summarized in
§6.1 was superseded after implementation.*

> This proposal is the historical research specification. Current callable behavior is
> documented in [`docs/library-api.md`](../docs/library-api.md), and current empirical
> claims are governed by the [`paper/`](../paper/README.md) artifact.
> The proposed MLflow backend was removed in release 0.6.0 after reference analysis found
> no experiment, demonstration, optimizer, or runtime consumer. Current capture uses the
> OpenAI Agents SDK adapter and canonical local JSONL. See the
> [removal review](../docs/mlflow-removal-report.md). The API and package-layout examples
> below now describe the implemented release; earlier pseudo-APIs remain in Git history.

---

## 0. What v2 changes, and why

v1 was literature-aware and rigorous about *evidence*, but it was not implementable as written: it specified no algorithms, its two headline endpoints were arithmetically incompatible with its own gates, and its core technical steps ("frequent connected subgraph mining", "CEGIS/SyGuS synthesis", "effect inference") named research problems rather than procedures. v2 keeps the epistemic discipline and replaces the hand-waving with seven concrete algorithms, a library that implements them, and endpoints that the arithmetic actually supports.

| # | v1 problem | v2 resolution | Section |
|---:|---|---|---|
| 1 | **H3 is unreachable.** A 20% cost cut with ≥20% episode coverage and ≥2 removed requests per dispatch requires $\phi\rho k \ge 0.2\,n_B$. With $n_B\approx 18$ that needs $\phi\rho k\ge 3.6$, i.e. coverage above 100%. The two co-primaries contradict each other. | Endpoints derived from the **feasibility frontier**, not asserted. Primary systems endpoint becomes **model requests eliminated** (ratio < 0.90). | §3.5, §8.3 |
| 2 | Cost measured as dollars, but prompt caching discounts the removed prefill by ~10×, so \$/request ≪ average cost/request. v1's cost endpoint silently assumed uncached pricing. | Cost decomposed into cached-input / uncached-input / output terms; reported with intervals, not thresholded. | §3.4 |
| 3 | **No algorithms.** §5 described stages in prose; nothing was specified precisely enough to implement or to review for correctness. | Seven numbered algorithms with inputs, outputs, rejection conditions, and complexity. | §4 |
| 4 | "Data edges when an earlier result supplies a later argument" — the single most important construction in the paper — was left undefined. | **Value-provenance construction** (Alg. 1): typed content matching against a producer index, with a bounded transform search for non-identity flows. This is the technical core. | §4.1 |
| 5 | "Frequent connected subgraph mining" is exponential and is the wrong primitive: agent traces are *linearizations*, not arbitrary graphs. | **Canonical-window hashing** (Alg. 2): contiguous windows over a canonical topological order, $O(mW^2)$, with independent events sorted by signature so permuted parallel reads collide. | §4.2 |
| 6 | SESE (single-entry/single-exit) was treated as the compilability condition. It is necessary but far from sufficient — it says nothing about whether the region's arguments can be *reconstructed without the model*. | Compilability restated as **live-in groundability** (Eq. 4): every argument slot must be a constant or a bounded transform of the entry state and in-region observations. | §3.3, §4.2 |
| 7 | CEGIS + SyGuS + a general typed DSL is a multi-year systems effort, not an 18-week slice. | Synthesis narrowed to two finite, decidable subproblems: **version-space enumeration over a closed 22-op transform library** (Alg. 3) and **typed decision-list induction** (Alg. 4). No SMT solver, no unbounded search. | §4.3–4.4 |
| 8 | Effects were to be "resolved" per call, but neither the SDK nor MLflow exposes them and v1 offered no mechanism. | Effects are a **user-declared YAML catalog**, defaulting to `UNKNOWN` (never compilable). Turns an open research problem into a 30-line config file and makes the system fail-closed by construction. | §5.3 |
| 9 | v1 abandoned finite-sample risk control ("Dev is too small"). It gave up one step too early: a *fixed threshold grid* admits a valid multiple-testing correction. | **Bonferroni–Clopper–Pearson threshold selection** over a pre-registered grid (Alg. 6): valid for i.i.d. or conditionally i.i.d. group-level violation indicators, honestly wide, and it degrades to abstention rather than to a false guarantee. | §4.6 |
| 10 | Seven scored conditions including faithful reimplementations of MiniCache (with speculative decoding), Agentic Plan Caching, and EvoC2F. That is three systems papers of engineering for one researcher; v1's own risk table flags the straw-baseline hazard this creates. | **Four scored conditions.** The dropped systems move to related work plus optional Train/Dev diagnostics. Episode count falls from 8,607 to ~4,200. | §8.2, §10 |
| 11 | The Track A / Track B split meant the reference architecture (the part anyone would actually use) was never validated by anything. | **One library, two evidence levels.** The library *is* the Track A implementation; the SDK adapter and JSONL store share its typed IR. | §5 |
| 12 | Math used `\[…\]` and `\(…\)`, which do not render on GitHub or in most Markdown viewers; `\mathbb{1}` has no glyph in KaTeX; there was no notation table and no equation numbering. | All math converted to `$$…$$` / `$…$`, indicators to $\mathbf{1}[\cdot]$, equations tagged, and a notation table added. | §2 |

Two things v2 does **not** change: the literature positioning (v1's is accurate and is retained) and the evidence discipline around Train/Dev/Test separation (retained and tightened).

**v2.1** originally added five illustrative worked implementations and a production
assessment (§6). Writing those cases falsified three things in v2's own algorithms, which
are corrected here rather than papered over. The current [use-case guide](../docs/use-cases.md)
now uses the implemented API and measured evidence instead of preserving the obsolete
examples.

| # | v2 defect | v2.1 correction | Section |
|---:|:--|:--|:--|
| 13 | **Algorithm 1 could not satisfy Eq. (4).** The index was built from event outputs only, so the entry state $z$ was unreachable. Any slot grounded in $z$ was marked `UNGROUNDED`, and Algorithm 2 discarded every window containing it — excluding the most common real pattern, "normalize the user's input, then look it up". | $z$ is seeded as pseudo-producer 0 before the event scan (Alg. 1, lines 2–3). | §4.1 |
| 14 | **Nearest-producer collapse was unsound.** `argmin(i−j)` binds the wrong source whenever a value is legitimately produced twice — a tenant id echoed by both the caller's context and the resolved subject's record — and does so consistently enough that no single trace reveals it. | Algorithm 1 emits the full candidate set; Algorithm 3 commits to the path that is stable across the whole family; Algorithm 2 recomputes live-in/live-out after commitment. | §4.1 |
| 15 | **Algorithm 4 was a spurious-correlation generator.** Requiring $\varepsilon=0$ perfect separation over ~3,000 atoms and ~19 examples succeeds on *random* labels almost every time; leave-one-group-out over few groups does not catch it. This was the defect most likely to ship a silently-wrong artifact. | Support floor of 20 groups for any branching artifact, atoms restricted to guard-visible paths, and a permutation test over the entire search (Alg. 4, lines 2–3 and 15–18). | §4.4 |
| 16 | No assessment of whether any of this survives outside a benchmark, and no worked adoption path. | §6 grades all seven algorithms against deployment, identifies Algorithm 5 as a hard blocker (you cannot replay production), reframes compilation as a CI job, records four API gaps, and derives the engineering break-even. | §6 |

The five use cases also supply the first end-to-end evidence on the endpoint: their Eq. (10) computations land at 8.9%, 8.6%, 10.2%, 5.7%, and 5.0%. **Four of five fall below H3's 0.90 ratio**, which makes the co-primary tight rather than comfortable and is flagged as a risk to the positive result.

---

## 1. Claim and feasibility boundary

### 1.1 Thesis

> In traces of an ordinary, unmodified tool-using agent, a measurable fraction of behaviour is **not a decision** — it is a deterministic function of observations the agent has already made. That fraction can be identified offline by value-provenance analysis, compiled into small guarded programs, and dispatched at runtime behind a calibrated gate, eliminating model requests without changing the agent.

"Preserving behaviour" means satisfying a declared observable contract and holding held-out task success within a prespecified margin. It does **not** mean semantic equivalence.

### 1.2 What is and is not novel

The individual ingredients are all occupied: trace-to-program synthesis (PLDI 2022/2025), tool-sequence bundling (AWO), parameterized program caching (MiniCache), plan reuse (Agentic Plan Caching), verified executable skills (EvoC2F, SkillOpt), and calibrated deferral. The defensible contribution is the **conjunction**:

> Value-provenance recovery of *observation-grounded* subregions spanning **multiple genuine model requests** in raw stateful traces of an unchanged agent; bounded synthesis of the argument transforms and branch predicates that make those regions run on unseen entities; a Dev-frozen entry-state gate with a valid (if wide) risk statement; and scenario-held-out end-to-end evaluation.

The paper claims none of the following: first agent compiler, first executable skill, first trace-derived program, novelty for typed IRs / contracts / verification / fallback individually, formal semantic equivalence, production safety, or safe online self-modification.

### 1.3 The falsification test

If the recovered artifacts are only login prefixes, fixed call concatenations, or human-edited wrappers, this is an AWO replication and should be reported as such. The work is viable only if **automatic** synthesis recovers argument transforms or observation-dependent branches that execute correctly on scenarios never seen during compilation.

### 1.4 Formulation triage

| Formulation | Novelty | Feasibility | Decision |
|---|---:|---:|---|
| Agent that safely compiles itself online | Low, crowded | Low | Long-term motivation only |
| Repeated call sequences become composite tools | Demonstrated (AWO) | High | Scored baseline |
| Semantic equivalence between agent and program | Not defensible | Low | Never claimed |
| Provenance-grounded region compilation with calibrated admission | Plausibly differentiated | **Medium–high** | **This proposal** |

---

## 2. Notation

| Symbol | Type | Meaning |
|:--|:--|:--|
| $\tau$ | trace | One observable execution; $\mathcal{D}=\{\tau_1,\dots,\tau_n\}$ is the corpus |
| $g(\tau)$ | id | Scenario group of $\tau$; all folds and resampling are grouped by $g$ |
| $e_i$ | event | $i$-th event: `MODEL_REQ`, `MODEL_RESP`, `TOOL_CALL`, `TOOL_RESULT` |
| $\mathrm{sig}(e)$ | hash | Value-free signature: tool name, schema hash, argument-path shape, effect class |
| $G_\tau=(V,E)$ | DAG | Provenance-annotated trace graph (PATG); $E=E_{\mathrm{dat}}\cup E_{\mathrm{ctl}}\cup E_{\mathrm{ord}}$ |
| $B_\tau$ | set | Model-request boundaries in $\tau$; $n_B=\mathbb{E}\lvert B_\tau\rvert$ |
| $W$ | window | A contiguous region of a canonical linearization of $G_\tau$ |
| $r$ | family | A set of $W$'s sharing a canonical shape hash; $\mathrm{supp}(r)=\lvert\{g(\tau)\}\rvert$ |
| $z$ | record | **Entry state**: everything observable at a boundary *before* dispatch |
| $\mathcal{T}$ | library | Closed set of 22 typed transforms; $\mathcal{T}^{\le d}$ = compositions of depth $\le d$ |
| $\theta,\ \sigma$ | maps | Live-in binding map; live-out projection |
| $a$ | artifact | $a=(P,H,q,\eta,V,M)$ — program, hard guard, score, threshold, verifier, manifest |
| $\phi$ | $[0,1]$ | **Coverage**: $\Pr[\text{at least one dispatch in an episode}]$ |
| $\rho$ | $[0,1]$ | **Verifier pass rate** among dispatches |
| $R,\ F$ | $[0,1]$ | Contract-violation rate given dispatch; unconditional violation incidence |
| $\alpha,\ \delta$ | $[0,1]$ | Target violation rate; confidence level for its certificate |
| $k$ | $\mathbb{N}$ | Model requests removed per successful dispatch |
| $c_m,c_g,c_x$ | cost | Mean cost per model request; per-boundary gate cost; per-dispatch execute+verify cost |
| $N^\star$ | $\mathbb{N}$ | Break-even executions that amortize compilation |

---

## 3. Formal core

### 3.1 Execution record

A frozen baseline agent $B$ interacts with environment $E$. An observable execution is

$$
\tau \;=\; \big(x_0,\; e_1,\dots,e_m,\; x_m,\; u,\; c,\; t\big)
\tag{1}
$$

with initial and final observable state $x_0,x_m$, benchmark utility $u$, deployable cost $c$, and wall time $t$. Every $e_i$ carries a model-request id, typed input/output, schema and tool version, declared effect class, latency, and tokens. Private reasoning is never logged; the IR uses `MODEL_REQ`/`MODEL_RESP` and makes no claim to reconstruct hidden chain-of-thought.

### 3.2 The provenance-annotated trace graph

The object the whole method rests on. For a trace $\tau$, let $\mathrm{Out}(j)$ be the set of $(\text{path},\text{value})$ pairs in event $j$'s output and $\mathrm{In}(i)$ the same for event $i$'s input. A **data edge** exists when a later argument is a bounded transform of an earlier observation:

$$
(j \xrightarrow{\;p'\,\mapsto\,p,\;f\;} i)\;\in\;E_{\mathrm{dat}}
\iff
j<i,\;\;
(p',v')\in\mathrm{Out}(j),\;\;
(p,v)\in\mathrm{In}(i),\;\;
\exists f\in\mathcal{T}^{\le d}:\; f(v')=v
\tag{2}
$$

restricted to values that are *groundable* (§4.1) so that `0`, `true`, `""` and other low-entropy literals do not manufacture spurious dependencies. This is recovered from traces alone — no instrumentation of the agent's own code.

A **control edge** $j \to i$ is added at corpus level when the value observed at $j$ covaries with the signature chosen at $i$ across traces; an **order edge** joins events whose declared effects conflict on a shared resource.

### 3.3 Regions, compilability, and artifacts

A candidate region $W\subseteq\tau$ has live-ins and live-outs

$$
\mathrm{LiveIn}(W)=\{\text{paths used in } W \text{ produced before } W\},\qquad
\mathrm{LiveOut}(W)=\{\text{paths produced in } W \text{ used after } W\}
\tag{3}
$$

Let $\mathrm{Obs}_{<s}$ be the observations available inside $W$ strictly before argument slot $s$, and let $z$ be the entry state. The **compilability condition** — the real gate, and the thing SESE does not give you — is that every argument slot in the region can be reconstructed without asking the model:

$$
\boxed{\;
\mathrm{Compilable}(W)\iff
\forall\,s\in\mathrm{Slots}(W):\;\;
\exists\, f\in\mathcal{T}^{\le d},\ \omega\in \mathrm{Obs}_{<s}\cup z\ \cup\ \mathrm{Const}
\;\;\text{s.t.}\;\;
s = f(\omega)
\;}
\tag{4}
$$

If any slot's value first appears in a model *response* and is neither constant across all supporting traces nor derivable via $\mathcal{T}^{\le d}$, the region encodes a genuine decision and is rejected. Additionally $W$ must satisfy

$$
\lvert B_\tau \cap \mathrm{interior}(W)\rvert \ge 2
\quad\text{and}\quad
\forall e\in W:\ \mathrm{eff}(e)\in \mathcal{E}_{\text{allowed}}
\tag{5}
$$

so that compaction removes **real model decisions** — not several tool calls emitted in one assistant turn — and touches only permitted effects.

A compiled artifact is

$$
a \;=\; \big(\,\underbrace{P}_{\text{program}},\;
\underbrace{H}_{\text{hard guard}},\;
\underbrace{q}_{\text{score}},\;
\underbrace{\eta}_{\text{threshold}},\;
\underbrace{V}_{\text{verifier}},\;
\underbrace{M}_{\text{manifest}}\,\big)
\tag{6}
$$

with dispatch decision at entry state $z$

$$
\mathrm{Dispatch}(z)=
\begin{cases}
a^\star, & \mathcal{A}(z)\neq\varnothing,\ \ a^\star=\arg\min_{a\in\mathcal{A}(z)} q_a(z)\\[4pt]
\bot\ (\text{baseline}), & \text{otherwise}
\end{cases}
\qquad
\mathcal{A}(z)=\{a: H_a(z)\wedge q_a(z)\le\eta_a\}
\tag{7}
$$

Ties in $\arg\min$ break by artifact id, so dispatch is deterministic.

### 3.4 Cost, latency, and the feasibility frontier

This is the subsection v1 needed and did not have. Per episode:

$$
\mathbb{E}[C_A]\;=\;\mathbb{E}[C_B]\;-\;\underbrace{\phi\,\rho\,k\,c_m}_{\text{saved}}\;+\;\underbrace{\bar b\,c_g}_{\text{gate}}\;+\;\underbrace{\phi\,c_x}_{\text{execute}+\text{verify}}\;+\;\underbrace{\phi(1-\rho)\,c_w}_{\text{wasted attempts}}
\tag{8}
$$

so the achievable cost ratio is

$$
\Gamma \;=\; \frac{\mathbb{E}[C_A]}{\mathbb{E}[C_B]}
\;=\;1-\frac{\phi\rho k\,c_m-\bar b c_g-\phi c_x-\phi(1-\rho)c_w}{\mathbb{E}[C_B]}
\tag{9}
$$

Since $\mathbb{E}[C_B]\approx n_B\,c_m$ and the overhead terms are small relative to a model round-trip, hitting a target reduction $\Delta$ requires

$$
\boxed{\;\phi\,\rho\,k \;\gtrsim\; \Delta\cdot n_B\;}
\tag{10}
$$

Equation (10) is decisive and cheap to evaluate **before writing any compiler**. AppWorld ReAct episodes run roughly $n_B\in[12,25]$ model requests. Then:

| Target $\Delta$ | Required $\phi\rho k$ at $n_B=18$ | Feasible? |
|---:|---:|:--|
| 0.05 | 0.9 | Yes — e.g. $\phi=0.5,\ \rho=0.9,\ k=2$ |
| 0.10 | 1.8 | Yes, but demanding — e.g. $\phi=0.7,\ \rho=0.9,\ k=3$ |
| 0.15 | 2.7 | Only with large regions — $\phi=0.75,\ \rho=0.9,\ k=4$ |
| 0.20 | 3.6 | **Requires $k\ge 4$ at $\phi\rho\approx 0.9$** — implausible under a read-only effect policy |

v1's H3 sat in the bottom row while Gate C only required $\phi\ge0.20$ and $k\ge2$, i.e. $\phi\rho k\approx0.36$ — an order of magnitude short. v2 sets the endpoint at $\Delta=0.10$ on **model requests**, which is the quantity the method directly controls, and reports dollars and latency with full accounting rather than thresholding them.

Two second-order effects, both stated because both cut against the method:

- **Prompt caching.** The removed request's prefill is mostly cached, so its marginal dollar cost is far below the episode average. Cost savings therefore lag request savings. Decompose $c_m = c^{\text{in}}_{\text{cold}} + c^{\text{in}}_{\text{cached}} + c^{\text{out}}$ and report each.
- **Latency.** Removing a boundary removes a full round-trip, so latency savings track request savings more faithfully than dollars do — but only in proportion to the model's share of wall time, $\mu = \mathbb{E}[T^{\text{model}}]/\mathbb{E}[T]$:

$$
\Lambda \;=\;\frac{\mathbb{E}[T_A]}{\mathbb{E}[T_B]}\;\approx\;1-\mu\cdot\frac{\phi\rho k}{n_B}+\frac{\bar b\,t_g+\phi\,t_x}{\mathbb{E}[T_B]},
\qquad t_g\!\sim\!1\,\text{ms},\ t_x\!\sim\!10\text{–}100\,\text{ms}
\tag{11}
$$

Amortization of one-time compilation:

$$
N^\star=\frac{C_{\text{compile}}}{\;\mathbb{E}[C_B]-\mathbb{E}[C_A]\;}
=\frac{C_{\text{compile}}}{\phi\rho k\,c_m-\bar b c_g-\phi c_x-\phi(1-\rho)c_w}
\tag{12}
$$

The compiler's objective is net savings subject to the risk and coverage constraints:

$$
\max_{\mathcal{R}\subseteq\text{artifacts}}\ \ \mathbb{E}[C_B-C_A\mid \mathcal{R}]-\frac{C_{\text{compile}}(\mathcal{R})}{N}
\quad\text{s.t.}\quad
\widehat{R}^{+}(\mathcal{R})\le\alpha,\ \ \widehat\phi(\mathcal{R})\ge\phi_{\min}
\tag{13}
$$

where $\widehat R^{+}$ is an upper confidence bound, not a point estimate.

### 3.5 Evaluation quantities

Episode-level indicators (repeated dispatches inside one episode are **not** independent samples):

$$
D_i=\mathbf{1}\big[\text{episode } i \text{ dispatches at least once}\big],
\qquad
L_i=\mathbf{1}\big[\text{some dispatch in } i \text{ violates its contract}\big]
\tag{14}
$$

$$
\phi=\Pr[D_i=1],\qquad
R=\mathbb{E}[L_i\mid D_i=1],\qquad
F=\mathbb{E}[L_i]=\phi R
\tag{15}
$$

**Preregistered hypotheses.**

| | Statement | Status |
|:--|:--|:--|
| **H1** | Automatic synthesis yields $\ge 3$ nontrivial artifacts, each executing on $\ge 5$ held-out Test Normal scenarios. *Nontrivial* = removes $\ge 2$ model requests **and** contains a synthesized transform or observation-dependent branch. Login-only prefixes and literal concatenation do not count. | Gate for the paper's existence |
| **H2** | Lower one-sided 95% CI on the Test Normal Task-Goal-Completion difference exceeds $-0.05$. Sensitivity at $-0.03$. | **Co-primary** |
| **H3** | Upper one-sided 95% CI on the ratio of mean **model requests per episode** is below $0.90$. | **Co-primary** |
| **H3b** | Deployable cost ratio and p50 latency ratio, with cache-aware decomposition and intervals. | Secondary, unthresholded |
| **H4** | With both thresholds frozen on Dev, the learned entry gate has lower $F$ than support-only routing while losing $\le 5$ points of coverage. | Secondary |
| **H5** | Coverage and eliminated requests rise from 1 to 5 rollouts per Train task without a rising out-of-fold violation rate. | Exploratory |

H2 and H3 are co-primary under an intersection–union decision; both must pass. The $-0.05$ margin is a substantive ceiling — at most one extra failure per twenty tasks — and is not adjustable for power. If the Gate 0 power simulation cannot support it, the study is relabelled **estimation-focused** before any Test execution.

---

## 4. Algorithms

Seven algorithms. Together they are the library in §5. Every rejection path is explicit, because in this system **"do not compact" is the common and correct output**.

### 4.1 Algorithm 1 — Provenance-annotated trace graph

The crux. Recovers dataflow from traces alone by typed content matching against a producer index.

```text
Algorithm 1   BuildPATG
──────────────────────────────────────────────────────────────────────────────
Input   τ = ⟨e₁..e_m⟩ ordered events with typed JSON payloads
        z  entry-state record observable at τ's first model boundary
        Θ  groundability policy;  T  transform library;  d  max depth (=2)
        κ  ambiguity cap (=3)
Output  G = (V, E_dat ∪ E_ord),  B = model boundaries,  diag
──────────────────────────────────────────────────────────────────────────────
 1  V ← {e₁..e_m};  B ← { i : kind(eᵢ) = MODEL_REQ };  Idx ← ∅;  diag ← 0
 2  for (p, v) in flatten(z):                          # seed z as pseudo-producer 0
 3      if groundable(v, Θ): Idx.add(v, (0, "z."+p))   #  Eq.(4) admits z as a source
 4  for i = 1 .. m:
 5      if eᵢ consumes input:                          # TOOL_CALL or MODEL_REQ
 6          for (p, v) in flatten(input(eᵢ)):
 7              if not groundable(v, Θ): continue
 8              S ← Idx.exact(v)                       # O(1) hash lookup
 9              if S = ∅:
10                  S ← TransformSearch(v, Idx, T, d)  # non-identity dataflow
11              if |S| = 0:      mark slot (i,p) UNGROUNDED;  continue
12              if |S| > κ:      diag.ambiguous += 1;  mark slot AMBIGUOUS; continue
13              for (j, p′, f) ∈ S:                    # keep EVERY candidate producer;
14                  E_dat ← E_dat ∪ { (j → i, p′ ↦ p, f) }   # Alg. 3 commits to one
15      if eᵢ produces output:                         # TOOL_RESULT or MODEL_RESP
16          for (p, v) in flatten(output(eᵢ)):
17              if groundable(v, Θ): Idx.add(v, (i, p))
18  E_ord ← { (j → i) : j < i ∧ eff(e_j) ⋈ eff(eᵢ) on a shared resource }
19  return G, B, diag
──────────────────────────────────────────────────────────────────────────────
groundable(v, Θ) ≜  (str(v) ∧ len ≥ 3 ∧ v ∉ stoplist)
                  ∨ (int(v) ∧ |v| > 1)  ∨ float(v)  ∨ uuid(v) ∨ iso_date(v)
                  ;  booleans, nulls, and v ∈ {-1,0,1} are never groundable

TransformSearch(v, Idx, T, d):
    for each candidate source value v′ in Idx (typed-compatible only):
        for f in enumerate(T, depth ≤ d, arity ≤ 2):
            if f(v′) = v: yield (producer(v′), path(v′), f)
──────────────────────────────────────────────────────────────────────────────
Complexity   O( Σᵢ |payloadᵢ| )  for exact matching;
             TransformSearch is bounded by |T|^d · |Idx_typed| and is invoked
             only on exact-match misses (empirically < 15% of slots).
```

Control edges are corpus-level and are added by Algorithm 2, because covariation is not observable within a single trace.

Two details in lines 2–3 and 13–14 are load-bearing, and both were wrong in the first draft of this algorithm.

**Seeding the entry state (lines 2–3).** Eq. (4) admits $z$ as a grounding source, but an index built only from event outputs cannot reach it. Without the seed, any slot whose value comes from the entry state — a requester's email, a product area, a tenant id — is marked `UNGROUNDED` at line 11, and Algorithm 2 line 10 then discards every window containing it. Identity slots could be rescued afterwards by Algorithm 2's `EntryStateSchema` check, but a *transform* over an entry-state field could not be recovered at all, which silently excludes one of the most common real patterns (normalize the user's input, then look it up). Seeding $z$ as pseudo-producer 0 makes Algorithm 1 agree with Eq. (4).

**Keeping every candidate producer (lines 13–14).** Collapsing the candidate set to the nearest producer is unsound when the same value is legitimately produced in more than one place — a tenant id echoed by both the caller's context and the resolved subject's record, for instance. Nearest-wins then binds the wrong one consistently enough that no single trace reveals the error. Algorithm 1 therefore emits the full candidate set (capped at $\kappa$), and Algorithm 3 commits to exactly one source path, chosen for stability across the whole supporting family. Because commitment can move a slot's producer across the region boundary, Algorithm 2 recomputes $\mathrm{LiveIn}/\mathrm{LiveOut}$ after commitment and drops any window whose classification changed. Nearest-producer survives only as a display heuristic in diagnostics.

**Diagnostics reported as a first-class result.** Provenance precision/recall on a hand-labelled 200-slot sample, ambiguity rate, ungrounded-slot rate. If provenance recall is below ~0.8 the rest of the pipeline is unsound and this is a publishable negative finding on its own.

### 4.2 Algorithm 2 — Canonical-window region mining

Replaces v1's frequent-connected-subgraph mining. Agent traces are linearizations, so any recurring region appears as a contiguous window in a canonical order; canonicalizing independent events by signature makes permuted parallel reads hash together.

```text
Algorithm 2   MineRegions
──────────────────────────────────────────────────────────────────────────────
Input   {G_τ}_{τ∈D} with groups g(τ);  window bounds [w_min,w_max] = [2,8]
        min interior boundaries b_min = 2;  min group support s_min = 5
        allowed effect set E_allowed
Output  ranked candidate families F
──────────────────────────────────────────────────────────────────────────────
 1  F ← ∅
 2  for each τ ∈ D:
 3      L ← CanonicalOrder(G_τ)              # topological; ties among mutually
 4                                           #  independent events broken by sig(e)
 5      for a = 1 .. |L|:  for b = a .. |L|:
 6          W ← L[a..b];  if #tool_events(W) ∉ [w_min,w_max]: continue
 7          if |B_τ ∩ interior(W)| < b_min:                       continue   # Eq.5
 8          if ∃ e ∈ W : eff(e) ∉ E_allowed:                      continue   # Eq.5
 9          (LI, LO) ← LiveInOut(W, G_τ)                                     # Eq.3
10          if ∃ slot ∈ Slots(W) marked UNGROUNDED or AMBIGUOUS:  continue
11          if ¬ ∀ ℓ ∈ LI : ℓ ∈ EntryStateSchema:                 continue   # Eq.4
12          h ← CanonHash(W)   # sig sequence + data-edge topology + LI/LO shape,
13                             #  all literal values replaced by typed holes
14          F[h] ← F[h] ∪ { (τ, a, b, LI, LO) }
15  F ← { r ∈ F : |{ g(τ) : (τ,·,·,·,·) ∈ r }| ≥ s_min }
16  AddControlEdges(F)   # within a family, a slot whose sig varies across members
17                       #  gets a control edge from the covarying observation
18  return sort(F, key = Score)                                              # Eq.16
──────────────────────────────────────────────────────────────────────────────
Complexity   O( Σ_τ m_τ · w_max² )  windows, each hashed in O(w_max).
             With m ≈ 60 and w_max = 8 this is ~4k windows per trace: trivial.
```

Candidate ranking:

$$
\mathrm{Score}(r)=
\underbrace{\mathrm{supp}(r)\cdot \hat k_r\, c_m}_{\text{expected saving}}
\;-\;\lambda_1 \underbrace{\mathbb{H}(r)}_{\text{branch entropy}}
\;-\;\lambda_2 \underbrace{\mathrm{risk}(r)}_{\text{effect risk}}
\;-\;\lambda_3 \underbrace{\mathrm{size}(P_r)}_{\text{MDL}}
\tag{16}
$$

Low entropy is regularity, not correctness. Failed traces and rare branches are retained as **negative evidence**, not discarded.

### 4.3 Algorithm 3 — Binding synthesis (version space over a closed library)

For each argument slot, find the simplest transform consistent with *every* supporting trace. Finite, decidable, no solver.

```text
Algorithm 3   SynthBinding
──────────────────────────────────────────────────────────────────────────────
Input   family r with support traces t₁..t_k;  slot s;  library T;  depth d = 2
Output  expression f ∘ σ, a Const, or ⊥ (reject the family)
──────────────────────────────────────────────────────────────────────────────
 1  if ∀ j: value_j(s) is identical:            return Const(value₁(s))
 2  Π ← { source paths present in ALL of t₁..t_k }   # stability across traces
 3  if Π = ∅:                                   return ⊥
 4  VS ← ∅                                      # version space
 5  for σ ∈ Π:
 6      for f ∈ enumerate(T, depth ≤ d, arity ≤ 2) with type(f) ⊨ type(σ)→type(s):
 7          if ∀ j ∈ 1..k :  f( t_j[σ] ) = value_j(s):
 8              VS ← VS ∪ {(f, σ)}
 9  if VS = ∅:                                  return ⊥       # genuine decision
10  (f*, σ*) ← argmin_{VS} ( MDL(f) , |σ| , lex(σ) )            # deterministic
11  if LeaveOneGroupOut(f*, σ*, r) fails:       return ⊥        # anti-memorization
12  return f* ∘ σ*
──────────────────────────────────────────────────────────────────────────────
Complexity   O( |Π| · |T|^d · k ).  With |T| = 22, d = 2, |Π| ≤ 50, k ≤ 25:
             ~600k typed evaluations per slot worst case, ≈ 1 s in Python,
             and heavily pruned by the type check on line 6.
```

**The transform library $\mathcal{T}$** (closed, 22 operators — this is the entire expressive power of the binder, and it is deliberately auditable):

| Class | Operators |
|:--|:--|
| Identity / coercion | `id`, `str`, `int`, `float`, `bool` |
| String | `lower`, `upper`, `strip`, `split(sep)[i]`, `join(sep)`, `fmt(template)` |
| Numeric | `add(c)`, `mul(c)`, `round(k)`, `sum`, `len` |
| Collection | `project(path)`, `filter(path op const)`, `first`, `last`, `sort(path)`, `topk(path,n)` |
| Temporal | `date_fmt(pattern)` |

Constants $c$ are drawn only from literals observed in supporting traces plus $\{0,1,-1,\text{""}\}$. Depth-2 composition covers the dominant real pattern — *select the right record from a list, then project one field from it* — which is exactly the credential-lookup and entity-resolution behaviour that makes login regions generalize to unseen users.

### 4.4 Algorithm 4 — Branch synthesis (typed decision list)

When supporting traces diverge, decide whether the divergence is explainable from observations. If not, reject: the divergence is a real decision.

```text
Algorithm 4   SynthBranch
──────────────────────────────────────────────────────────────────────────────
Input   family r;  divergence point with labels y₁..y_k ∈ Branches
        observable typed paths P at that point;  L_max = 3;  ε = 0
        s_branch = 20 (min groups);  B = 1000 (permutations);  π_max = 0.01
Output  decision list D, or ⊥
──────────────────────────────────────────────────────────────────────────────
 1  if |{y_j}| = 1:                       return Unconditional(y₁)
 2  if |groups(r)| < s_branch:            return ⊥        # see "the k ≪ |Atoms| trap"
 3  P ← P ∩ paths(H)                                      # atoms must be guard-visible
 4  Atoms ← { (p, op, c) : p ∈ P, op ∈ Ops(type(p)), c ∈ Consts(p, r) }
 5        Ops(num) = {=, ≠, <, >, ≤, ≥};  Ops(str) = {=, ≠, ∈, prefix, empty}
 6        Ops(list) = {empty, len =, len >};  Consts from observed values only
 7  D ← [];  Rem ← {1..k}
 8  while Rem ≠ ∅ and |D| < L_max:
 9      a* ← argmax_{a ∈ Atoms} purity(a, Rem)
10      if purity(a*, Rem) < 1 − ε:       break
11      D.append( (a*, majority_label(a*, Rem)) )
12      Rem ← Rem \ covered(a*, Rem)
13  if Rem ≠ ∅:                           return ⊥        # not separable
14  if LeaveOneGroupOut(D, r) has any error: return ⊥      # anti-memorization
15  p̂ ← PermutationTest(D, r, B)          # fraction of B group-label shuffles on
16                                        #  which the SAME search finds any D′
17                                        #  that separates perfectly
18  if p̂ > π_max:                         return ⊥        # separation is chance
19  return D
──────────────────────────────────────────────────────────────────────────────
Complexity   O( B · L_max · |Atoms| · k ),  |Atoms| ≈ |P| · 6 · |Consts| ≲ 3000.
             The permutation test dominates: ~10⁸ atom evaluations, seconds in a
             vectorized implementation, and it runs once per candidate branch.
```

`purity` is exact-classification purity with $\varepsilon=0$: a predicate is accepted only if it separates the supporting traces perfectly.

**The $k \ll \lvert\mathrm{Atoms}\rvert$ trap.** Demanding perfect separation sounds conservative and is the opposite. Searching ~3,000 candidate atoms for one that perfectly splits ~19 examples will succeed on *random* labels almost every time — the search has far more degrees of freedom than the data constrains. Leave-one-group-out over a handful of groups barely dents this, because the spurious atom that fits all 19 usually fits 18 as well. Left uncorrected, Algorithm 4 is a spurious-correlation generator, and its output is exactly the kind of plausible-looking artifact that survives review and fails in production on the first unseen entity.

Lines 2, 3, 15–18 close it three ways: a support floor high enough that perfect separation carries information ($s_{\text{branch}}=20$ groups, against $s_{\min}=5$ for a non-branching artifact); restricting atoms to paths already visible in the hard guard, which shrinks $\lvert\mathrm{Atoms}\rvert$ by roughly an order of magnitude and guarantees the predicate is evaluable at admission time; and a permutation test that reruns the *entire search* on shuffled labels, so the null distribution accounts for the search itself rather than for a single fixed predicate. This is the correction that matters most for deployment, and §6.3 explains why.

Bounded loops (`ForEach` over a collection with a synthesized termination predicate, cap 32 iterations) reuse the same machinery — the pagination pattern `while len(page) == page_size: fetch(next)` is a decision list over the observation `len(page)`.

### 4.5 Algorithm 5 — Contract induction and grouped validation

```text
Algorithm 5   InduceAndValidate
──────────────────────────────────────────────────────────────────────────────
Input   program P for family r;  Train groups G_tr;  perturbation suite Σ
Output  (H, V) or reject
──────────────────────────────────────────────────────────────────────────────
 1  H ← manifest equality (model, prompt, tool, schema, policy hashes)
 2      ∧ ∀ ℓ ∈ LiveIn:  present(ℓ) ∧ type(ℓ) ∧ hull(ℓ)
 3          hull = interval for numerics, enum for low-card categoricals,
 4                 regex/length band for strings — all fitted on Train only
 5  V ← ∀ o ∈ LiveOut:  type(o) ∧ non_null(o) ∧ card_bounds(o) ∧ range_hull(o)
 6      ∧ provenance(o) ⊆ calls made inside the region
 7      ∧ effect_multiset(run) ⊆ E_allowed
 8  for each held-out group g ∈ G_tr:                       # grouped k-fold
 9      z ← recorded entry state of g;  replay P against a fresh world at z
10      if live-outs ≢ recorded (up to declared equivalence): reject
11      if effect multiset ≠ recorded:                        reject
12      if state digest delta ≠ ∅:                            reject
13  for each perturbation π ∈ Σ:                             # robustness
14      Σ = { unseen entity ids, empty/singleton/large lists, nulls,
15            duplicates, reordering, tool 4xx/5xx, timeout, schema drift }
16      require: P either produces a contract-satisfying result or ABSTAINS.
17               A wrong answer is a hard reject; abstention is acceptable.
18  return (H, V)
──────────────────────────────────────────────────────────────────────────────
```

Line 17 encodes the system's central asymmetry: **abstention is cheap, silent wrongness is fatal.** The runtime verifier is never the benchmark grader; hidden task tests participate only in offline evaluation.

### 4.6 Algorithm 6 — Gate calibration with a valid risk statement

v1 abandoned finite-sample control because Dev has only 20 scenario groups. That concedes too much: restricting to a *pre-registered finite threshold grid* makes a Bonferroni-corrected exact binomial bound valid. The bound will be wide — that is the honest cost of a small Dev set — and it degrades into abstention, never into a false guarantee.

Nonconformity score: an out-of-fold estimate of contract violation from entry-only features,

$$
q_a(z)=\widehat{\Pr}\big[\,L=1 \mid z,\,a\,\big],
\qquad
z\mapsto\big(d_{\mathrm{knn}}(z,\mathcal{Z}^{\mathrm{tr}}_a),\ \mathbf{1}[\text{unseen enum}],\ \mathbb{H}(\text{branch}),\ \text{ensemble disagreement},\ \text{OOF replay failure}\big)
\tag{17}
$$

trained by gradient boosting with **scenario-grouped** out-of-fold predictions on Train, where negatives come from held-out replay failures and the perturbation suite of Algorithm 5. An LLM's verbal confidence is never a gate feature.

```text
Algorithm 6   CalibrateGate
──────────────────────────────────────────────────────────────────────────────
Input   artifact a;  Dev episodes with H_a(z) satisfied;  target α;  conf. δ
        pre-registered grid Λ = {0.02, 0.05, …, 0.50}   (|Λ| = 11, fixed a priori)
        minimum coverage φ_min
Output  threshold η_a, or RETIRE
──────────────────────────────────────────────────────────────────────────────
 1  for z in Dev_a:  run a;  record  q_a(z)  and  L(z) ∈ {0,1}
 2  Adm ← ∅
 3  for η ∈ Λ:                                    # ascending
 4      S ← { z ∈ Dev_a : q_a(z) ≤ η }
 5      if |S| = 0: continue
 6      R⁺ ← ClopperPearsonUpper( Σ_{z∈S} L(z),  |S|,  level = 1 − δ/|Λ| )
 7      φ̂ ← |S| / |Dev|
 8      if R⁺ ≤ α and φ̂ ≥ φ_min:  Adm ← Adm ∪ {η}
 9  if Adm = ∅:  return RETIRE                    # correct output, not a failure
10  return max(Adm)                               # most coverage among admissible
──────────────────────────────────────────────────────────────────────────────
```

**Guarantee.** With $\Lambda$ fixed before seeing Dev and a Bonferroni split of $\delta$ across $\lvert\Lambda\rvert$ candidates, the selected $\eta$ satisfies

$$
\Pr\Big[\;\mathbb{E}\big[L\mid q_a(z)\le\eta\big]\;\le\;\alpha\;\Big]\;\ge\;1-\delta
\tag{18}
$$

**for i.i.d. or conditionally i.i.d. group-level violation indicators from the registered
deployment distribution.** Exchangeability alone is insufficient for this exact binomial
claim. Two caveats stated in the paper, not buried: (i) with
$\lvert\mathrm{Dev}\rvert=60$ episodes over 20 groups, the effective $n$ is the group
count, so $R^{+}$ at $\alpha=0.05$ typically demands *zero* observed violations and yields
low coverage; (ii) Test Challenge is shifted by construction, so (19) does not transfer
there and Challenge is reported as an abstention study only.

### 4.7 Algorithm 7 — Runtime dispatch with staged deoptimization

```text
Algorithm 7   Dispatch
──────────────────────────────────────────────────────────────────────────────
Input   entry state z at a model boundary;  local signed registry ℛ
Output  a native history extension, or BASELINE, or INCIDENT
──────────────────────────────────────────────────────────────────────────────
 1  A ← ℛ.resolve( sig(z) )                        # O(1) local hash; no network
 2  A ← { a ∈ A : H_a(z) }                         # manifest + hull hard guard
 3  if A = ∅:                       return BASELINE
 4  a* ← argmin_{a∈A} q_a(z);  tie-break by artifact id
 5  if q_{a*}(z) > η_{a*}:          return BASELINE
 6  stage ← Staging.begin(z)        # digest env/db, history, budget, quota, audit
 7  try:
 8      out, eff ← Interp.run(P_{a*}, z, deadline = d_max, facade = PermTools)
 9  except PreCommitError:  stage.abort();  return BASELINE
10  except PostCommitError: stage.freeze(); return INCIDENT
11  if ¬ V_{a*}(out, eff):
12      if stage.reversible():  stage.abort();  return BASELINE
13      else:                   stage.freeze(); return INCIDENT
14  stage.commit()
15  history.extend( NativeItems(out) )   # assistant tool_calls + tool results,
16                                       #  in the harness's own message schema
17  return COMPACTED                     # k model requests never issued
──────────────────────────────────────────────────────────────────────────────
```

`stage.reversible()` is an **attestation**, not a hope: it returns true only if environment/database state, session and model-visible history, interaction budget, wall-clock/RNG projection, quota/billing/audit counters, and permission context all equal the entry snapshot. Once anything is committed, the runtime does **not** pretend to roll back — it stops and raises an incident. Catching an exception after an irreversible write and quietly calling the baseline is the failure mode this design exists to prevent.

Latency and cost of failed speculative attempts are always charged to the method.

### 4.8 Complexity summary

| Stage | Cost | Where it runs | Budget |
|:--|:--|:--|--:|
| Alg. 1 PATG | $O(\sum\lvert\text{payload}\rvert)$ | Offline | ~1 s / trace |
| Alg. 2 Mining | $O(m\,w_{\max}^2)$ per trace | Offline | ~2 s / trace |
| Alg. 3 Bindings | $O(\lvert\Pi\rvert\,\lvert\mathcal{T}\rvert^d k)$ per slot | Offline | ~1 s / slot |
| Alg. 4 Branches | $O(L_{\max}\lvert\text{Atoms}\rvert k)$ | Offline | < 100 ms |
| Alg. 5 Validation | $O(\lvert G_{tr}\rvert+\lvert\Sigma\rvert)$ live replays | Offline, dominant | hours |
| Alg. 6 Calibration | $O(\lvert\mathrm{Dev}\rvert\cdot\lvert\Lambda\rvert)$ | Offline, once | minutes |
| **Alg. 7 Dispatch** | **$O(1)$ resolve + one score eval** | **Online, hot path** | **$t_g\lesssim 1$ ms** |

The whole design pushes work offline. The online path is a hash lookup, a guard evaluation, and one small-model score — which is what makes Eq. (10) survivable.

---

## 5. The library

The point of v2. Everything above is packaged as `agent-compaction` (import
`agent_compaction`), a small Python library that sits *beside* an agent rather than
inside it.

### 5.1 Design principles

1. **Never modify the agent.** Capture is tracing; dispatch is a model wrapper. The agent's prompt, tools, and loop are untouched.
2. **Fail closed.** Unknown effect, unknown schema, unknown version, registry miss, score above threshold, verifier failure → baseline. Abstention is the default output.
3. **Effects are declared, not inferred.** One YAML file. Anything undeclared is `UNKNOWN` and is never compiled. This converts v1's open research problem into configuration.
4. **Three calls to value.** Capture, compile, deploy.
5. **Read the program.** Every artifact prints as readable pseudocode. If a user cannot read what was compiled, they should not run it.
6. **Estimate before you build.** `ac.estimate()` evaluates Eq. (10) on existing traces and reports the achievable savings ceiling — before any compilation.

### 5.2 The whole API

```python
import agent_compaction as ac

# ── 1. load normalized capture ────────────────────────────────────────────
episodes = ac.read_jsonl("traces.jsonl")

# ── 2. estimate, then compile ─────────────────────────────────────────────
catalog = ac.load_catalog("effects.yaml")

print(ac.estimate(episodes, catalog, entry_schema=["tenant", "channel"]).render())
#  n_B  = 17.4 model requests/episode
#  ceiling: phi=0.71  k=2.9  ->  max request reduction 12.1%   [Eq. 10]
#  blocked: 43% of windows by UNKNOWN effects, 31% by ungrounded slots

job = ac.optimize(
    episodes,
    catalog,
    algorithms=["grc"],
    mode="offline",
    partition_by=["tenant_partition", "principal", "policy_version"],
    entry_schema=["tenant", "channel"],
    sandbox=make_isolated_sandbox,
)
print(job.report())
print(job.explain())
evidence = ac.validate(job, suites=["replay", "perturbation"])
job.save("artifacts/v1", signing_key=signing_key)
ac.promote(job, stage="shadow")

# ── 3. deploy ─────────────────────────────────────────────────────────────
from agents import Agent, Runner
from agent_compaction.runtime.model_provider import CompactingModel

agent = Agent(
    name="support",
    model=CompactingModel(
        base_model,
        registry=job.registry,
        catalog=catalog,
        manifest=episodes[0].manifest,
        mode="shadow",
        entry_state_fn=entry_state_from_sdk_input,
        partition_fn=partition_from_sdk_input,
    ),
    tools=[...],
)
result = await Runner.run(agent, "refund order 8812")
```

`mode="shadow"` scores and logs what *would* have been dispatched without dispatching — the mandatory first deployment step. `mode="live"` dispatches. `mode="off"` is a no-op that must produce byte-identical model input (conformance test 1 in §5.6).

For agents not built on the Agents SDK:

```python
@ac.compact(job.registry, catalog, episodes[0].manifest, mode="shadow")
def my_agent_step(entry_state: dict) -> ac.Decision:
    ...   # returns Decision.BASELINE or a compacted history extension
```

### 5.3 The effect catalog

The file that makes the system safe and the research problem tractable:

```yaml
# effects.yaml — anything not listed defaults to UNKNOWN and is never compiled
version: 1
tools:
  supervisor.show_account_passwords:
    effect: READ_LOCAL
    capabilities: [speculatable, replayable, cacheable, reorderable]
    key: [principal]

  spotify.show_playlist_library:
    effect: READ_EXTERNAL
    capabilities: [speculatable, replayable, batchable]
    key: [principal, access_token, page]
    freshness_s: 300

  spotify.login:
    effect: READ_EXTERNAL          # returns a token; creates a session record
    capabilities: [speculatable, replayable]
    key: [principal, username]
    notes: consumes no quota in AppWorld; re-verify per deployment

  spotify.add_song_to_playlist:
    effect: WRITE_IRREVERSIBLE
    capabilities: []               # never compiled in the scored condition
```

Capabilities gate specific optimizations: `cacheable` licenses memoization, `reorderable` licenses parallel reads, `batchable` licenses fusion, `speculatable` + `replayable` licenses pre-commit execution. Read-only and idempotent are *not* capabilities — a nominal read can still burn quota, create audit state, or observe time-varying data.

### 5.4 Package layout

```text
src/agent_compaction/
  schema/       traces.py  effects.py  artifacts.py       # typed contracts
  capture/      agents_sdk.py  jsonl.py  manifests.py      # capture + persistence
  graph/        normalize.py  provenance.py  windows.py    # Alg. 1, 2
  grc/          synthesize.py  contracts.py  calibrate.py  # Alg. 3--6
                compile.py
  tgws/         tree.py  prune.py  package.py              # specialist routing
  portfolio/    model.py  statistics.py  selector.py       # evidence selector
  runtime/      dispatch.py  runner.py  model_provider.py  # Alg. 7 + adapters
  registry/     store.py  lifecycle.py                     # signed lifecycle
  evaluation/   splits.py  replay.py  perturb.py  ledger.py
  benchmarking/ preflight.py                               # frozen study gates
  api.py        pipeline.py  cli.py                         # public composition
```

Only the capture and model-provider adapters touch the optional Agents SDK surface. The
typed Episode IR, optimizers, portfolio, evaluation, and registry stay framework-neutral;
canonical JSONL persists the IR itself. This is what makes the paper evaluation and SDK
deployment use the same compiler rather than v1's disconnected tracks.

### 5.5 Canonical JSONL persistence

Release 0.6.0 uses one dependency-free persistence boundary: canonical JSONL containing
the typed Episode IR. `write_jsonl()` first materializes and validates every Episode,
serializes strict RFC-compatible JSON with deterministic key ordering, and atomically
replaces the snapshot. `read_jsonl()` validates each line and rejects malformed,
non-object, duplicate-episode, or non-finite payloads with a line-numbered
`EpisodeStoreError`. A failed write leaves the prior snapshot intact.

Long-running experiments use `RunLedger`, an append-only, hash-chained record of claims
and outcomes that supports safe resume and conflict detection. Snapshot storage and run
accounting are deliberately separate: JSONL is the compiler corpus; the ledger is the
execution journal. Neither attempts to be a remote observability UI.

The removed MLflow prototype is documented in the
[removal review](../docs/mlflow-removal-report.md) and in Git history. Applications may
still run an external tracing or analytics service, but the library does not require it
and never treats its previews as replay evidence.

### 5.6 OpenAI Agents SDK backend

Capture is documented and easy; **mid-run substitution is not a documented plug-in** and is the risky part. The honest mapping:

| Integration path | Status | Role |
|:--|:--|:--|
| Tracing processors, custom spans | Documented | Preferred capture |
| `RunHooks` / `AgentHooks` | Documented observers | Telemetry only — `on_llm_start` cannot return a replacement response |
| `call_model_input_filter` | Documented input transform | Useful for a *context-compaction* ablation; cannot skip the call |
| Compiled `FunctionTool` / agent-as-tool | Documented | Strong macro baseline — but a model still selects it, so the invoking request is **not** eliminated |
| Outer controller around `Runner.run` | Ordinary composition | Safe prototype at run boundaries only |
| Custom `Model` / `ModelProvider` | Extension interface documented; compaction behaviour is ours | **`CompactingModel`** — returns a deterministic `ModelResponse` on a hit, delegates on a miss |
| Forked runner | Not a plug-in | Excluded |

```python
class CompactingModel(Model):
    """Pin the tested openai-agents revision; ModelResponse/output-item
    shapes are version-coupled and conformance-tested per bump."""

    async def get_response(self, system_instructions, input, model_settings,
                           tools, output_schema, handoffs, tracing,
                           *, previous_response_id=None, prompt=None, **kw):
        z = self._entry.snapshot(input, tools, handoffs, model_settings)

        if self._plan.active():                       # mid-artifact
            return self._plan.next_response()         # next synthetic tool call

        decision = self._registry.dispatch(z)         # Algorithm 7, lines 1-5
        if decision is BASELINE or self.mode != "live":
            self._log_shadow(decision)
            return await self._base.get_response(system_instructions, input, ...)

        self._plan = ArtifactPlan(decision.artifact, z)
        return self._plan.next_response()             # SDK-valid function_call items
```

The wrapper emits `function_call` output items from the artifact state machine; the ordinary Runner executes the tools and returns results; subsequent boundaries advance the plan or delegate. This removes real provider calls while keeping SDK tool dispatch — but it is **not equivalent by construction**, so it ships behind seven conformance tests:

1. `mode="off"` produces byte-identical input at the next provider call.
2. Accepted execution emits schema-valid native items satisfying tool identity, typed arguments/results, ordering, ownership, effect, and continuation contracts.
3. Deterministic reference replay of the same recorded entry and observations reproduces the native items, history digest, exit value, and effect trace. *No test requires a fresh stochastic baseline to pick identical actions.*
4. A rejected pre-emission or staged attempt restores identical model-visible input and every declared state component; post-commit failure is classified separately as an incident.
5. Usage, errors, retries, guardrails, approvals, and trace nesting stay attributable.
6. Each supported history/session strategy and concurrent interleaving passes multi-turn fixtures.
7. Streaming, hosted tools, and handoffs **reject** rather than silently degrade.

v0.1 is non-streaming, single-agent, local function tools, one history strategy. Everything else fails closed.

**Deoptimization has two phases.** Before the wrapper emits a `ModelResponse`, delegation to the wrapped model is exact. After emission, the Runner may already have committed the response, tool call, result, or session history, and the `Model` interface alone cannot erase it — exact post-emission deopt requires a staging owner in an outer controller or a session transaction. Without one, a post-commit verifier failure is an incident, not a fallback.

Custom spans `compaction.{resolve,guard,gate,execute,verify,history,deopt,incident}` record artifact/version, decision reason, elapsed time, cost, history digest, and source event ids.

### 5.7 A worked example

From an AppWorld Spotify task. The baseline agent spends three model requests on what is, in fact, a pure function of two observations.

**Recorded trace fragment.**

```text
MODEL_REQ #1  → MODEL_RESP: call supervisor.show_account_passwords()
TOOL_RESULT   → [ {account_name:"spotify", password:"c2xf9"},
                  {account_name:"amazon",  password:"kk31p"},
                  {account_name:"gmail",   password:"z0m4a"} ]
MODEL_REQ #2  → MODEL_RESP: call spotify.login(username="alex_h", password="c2xf9")
TOOL_RESULT   → { access_token:"tok_7f2", expires_in:3600 }
MODEL_REQ #3  → MODEL_RESP: call spotify.show_playlist_library(access_token="tok_7f2", page=0)
TOOL_RESULT   → { items:[...20 items...], page:0 }
```

**Algorithm 1** recovers the dataflow. `password="c2xf9"` is groundable (len ≥ 3) and exact-matches `[0].password` of the first result — but that path is *positional* and unstable across users. `TransformSearch` at depth 2 finds the stable expression `filter(account_name == "spotify") ∘ project(password)`. `access_token="tok_7f2"` matches by identity. `username="alex_h"` is ungrounded in this trace but is present in the entry state (the supervisor profile), so Eq. (4) is satisfied.

**Algorithm 2** finds a window with three interior model boundaries, all events `READ_LOCAL`/`READ_EXTERNAL` with `speculatable + replayable`, live-in `{username}` available in $z$, live-out `{access_token, items}`. Support: 19 of 35 Train scenario groups.

**Algorithm 3** synthesizes the bindings; the credential lookup is the nontrivial one and it is exactly what makes the artifact generalize to a user never seen at compile time.

**Algorithm 4** fires on a genuine branch: in 4 of 19 supporting traces the library was paginated, and the agent issued a follow-up. The atom `len(items) == 20` separates the supporting traces perfectly and becomes a bounded `ForEach`.

**Synthesized artifact** (as `registry.explain()` prints it):

```text
artifact  spotify.session_and_library@1   support 19/35 groups   removes k=3
──────────────────────────────────────────────────────────────────────────────
guard   model=gpt-5-2026-04-12  prompt=#a91f  tools=#7c02  policy=#3e55
        z.username : str  matches ^[a-z_]{3,20}$
        effects ⊆ {READ_LOCAL, READ_EXTERNAL}  all speculatable ∧ replayable

program (θ = {username}):
   c    = call supervisor.show_account_passwords()
   pw   = c |> filter(account_name == "spotify") |> project(password)   ← Alg.3
   tok  = call spotify.login(username = θ.username, password = pw)
   pg   = 0;  items = []
   ForEach (max 32):                                                    ← Alg.4
        r     = call spotify.show_playlist_library(
                       access_token = tok.access_token, page = pg)
        items = items ++ r.items
        if len(r.items) < 20: break
        pg    = pg + 1
   assert  tok.access_token matches ^tok_  and  len(items) ≥ 0
   return  { access_token: tok.access_token, items: items }

verify  access_token : str, non-null, provenance ∈ {spotify.login}
        items : list, each ⊨ playlist_schema, provenance ∈ {show_playlist_library}
gate    q = GBM(entry features)   η = 0.11   (Dev, α=0.05, δ=0.10, |Λ|=11)
```

This one artifact removes three model requests on ~54% of Train scenarios. Under Eq. (10) at $n_B=17.4$, if it generalizes at $\phi=0.5,\rho=0.9,k=3$ it alone contributes $0.5\cdot0.9\cdot3/17.4 = 7.8\%$. That is the realistic unit of progress — and why the endpoint is 10%, not 20%.

Contrast with what is **correctly rejected**: `spotify.add_song_to_playlist` is `WRITE_IRREVERSIBLE` with no capabilities, so any window containing it fails Eq. (5) at Algorithm 2 line 8. Which song to add is a real decision, ungrounded in observations, so it also fails Eq. (4).

### 5.8 Build order

| Slice | Scope | Effort | Value on its own |
|:--|:--|--:|:--|
| **v0.1 — Estimator** | Alg. 1–2 + `estimate()`; SDK adapter and JSONL store; no synthesis, no runtime | ~2 weeks | Answers "is there anything here?" for any traced agent. Publishable as a measurement study even if compaction never ships. |
| **v0.2 — Compiler** | Alg. 3–5, interpreter, `explain()`, registry | ~4 weeks | Offline artifacts + readable programs; still zero runtime risk |
| **v0.3 — Shadow** | Alg. 6–7 in `mode="shadow"`, spans, staging attestation | ~3 weeks | Measured coverage and would-be savings on live traffic, zero behaviour change |
| **v0.4 — Live** | `mode="live"`, `CompactingModel`, 7 conformance tests | ~3 weeks | Actual savings, single-agent local tools only |
| v0.5+ | Handoffs, hosted tools, streaming, scheduled recompilation, canary | later | Out of the paper's scope |

Start at v0.1. It is cheap, it is the Gate 0 instrument, and its output determines whether anything downstream is worth building.

---

## 6. Use cases and production readiness

### 6.1 Five worked use cases

The original v2.1 companion developed five illustrative agents end to end: trace fragment,
recovered provenance, effect catalog, synthesized artifact, integration code, savings
arithmetic, and—longest in every case—what is rejected and why. That monograph used a
pre-implementation pseudo-API and is no longer operational documentation. Its assumptions
and numbers remain summarized below; the current [use-case guide](../docs/use-cases.md)
provides the implemented API and measured scenarios.

Each row below is the section's own Eq. (10) computation, $\Delta = \phi\rho k / n_B$. The parameters
are illustrative, not measured; `ac.estimate()` exists so that no one has to adopt them.

| # | Agent | $n_B$ | $\phi$ | $\rho$ | $k$ | $\Delta$ | What it demonstrates |
|--:|:--|--:|--:|--:|--:|--:|:--|
| 1 | Tier-1 support over internal APIs | 16.2 | 0.40 | 0.90 | 4.0 | 8.9% | The reference shape: a read-only evidence prefix, a depth-2 credential/entity binding, a tier-dependent branch |
| 2 | Internal knowledge assistant (RAG) | 11.5 | 0.29 | 0.85 | 4 | 8.6% | The guard is the contribution. Index version, ACL scope, and freshness are hard key fields, not similarity features |
| 3 | Refund approval with a human in the loop | 12.4 | 0.38 | 0.90 | 3.7 | 10.2% | The approval barrier as a region terminator. Everything compiled is pre-commit and read-only |
| 4 | Multi-agent triage with handoffs | 14.2 | 0.45 | 0.90 | 2 | 5.7% | The artifact is a learned *predicate*, not a call sequence. Ownership must survive |
| 5 | Multi-tenant enterprise ops over MCP | 22.3 | 0.32 | 0.88 | 4 | 5.0% | A correct guard that makes the workload uneconomic. Ship the estimator; do not build the compiler |

Three findings survive across all five, and none of them is comfortable.

**Four of five fall below the H3 endpoint.** Only the human-in-the-loop case clears a 0.90 request
ratio, and it clears it by 0.2 points. The 10% co-primary of §3.5 is therefore at the edge of what
this class of method delivers, not comfortably inside it. That is a real risk to the paper's positive
result and it is better to say so now than to discover it at Gate D.

**$k$ is bounded by contiguity, not by $w_{\max}$.** Algorithm 2 permits eight tool events, but what
actually limits a region is how much uninterrupted read-only work an agent does before its first
commitment. Across all five that is 2–4 model boundaries. Raising $w_{\max}$ would not help.

**Every hard guard field divides the support.** Tenant, principal, policy version, index version, and
residency each partition the corpus. Use case 5 fails on exactly this: its guard is *correct*, and its
correctness is what makes $N^\star$ unreachable. Guard precision and economic viability pull in
opposite directions, and there is no setting of $\eta$ that resolves it.

### 6.2 Production readiness, algorithm by algorithm

The algorithms in §4 were designed against a benchmark where the environment can be reset. Production
cannot. This is an assessment of each against deployment, not against AppWorld.

| Algorithm | Verdict | The actual obstacle | Disposition |
|:--|:--|:--|:--|
| **1** Provenance | Viable behind a measured gate | Precision degrades on real payloads. Enterprise JSON repeats low-entropy values everywhere — status enums, currency and region codes, tenant ids echoed in every response — and free-text blobs produce spurious exact matches on common tokens | The static stoplist in $\Theta$ is insufficient. Replace it with a per-field entropy filter computed from the corpus: a value is groundable only if its field's observed cardinality exceeds a threshold. Keep the Gate 0 recall requirement as a hard precondition |
| **2** Mining | Viable except for one hole | **Production has no scenario ids.** Support counting is meaningless without grouping, and repeated identical traffic inflates it — one automated caller hammering the same request looks like broad support | Group by (intent cluster, principal) with clusters computed offline, and require support from $s_{\min}$ distinct principals **and** $s_{\min}$ distinct days. Both conditions, not either |
| **3** Bindings | Viable, low yield | 22 operators at depth 2 miss regex extraction, arithmetic across multiple fields, and unit conversion. Slots hit $\bot$ often | Accept the yield. Do **not** extend the library opportunistically: every operator added also widens Algorithm 1's spurious-match surface, so the library trades precision for coverage on both ends at once |
| **4** Branches | **Was unsound; now corrected** | With ~3,000 atoms and ~19 examples, $\varepsilon=0$ separation occurs by chance almost always. This is the one that would have shipped silently-wrong artifacts | Fixed in §4.4: support floor of 20 groups, atoms restricted to guard-visible paths, and a permutation test over the whole search. See §6.3 for why this matters more in production than in the paper |
| **5** Validation | **Hard blocker as written** | It replays against a live environment from a recorded entry state. You cannot re-run reads against production hundreds of times for perturbation testing, and you cannot reset production | Must be replaced for deployment. See §6.3 |
| **6** Calibration | Viable only when the sampling model and labels are defensible | Needs violation labels and i.i.d. or conditionally i.i.d. group indicators. Labels and distribution drift are both deployment problems | Shadow mode can supply labels and larger $n$ can tighten the Bonferroni–Clopper–Pearson bound. Drift invalidates the registered sampling claim, so the L2 circuit breaker is mandatory rather than optional |
| **7** Dispatch | Viable *only* within the stated scope | `stage.reversible()` cannot be truthfully attested in a distributed system. You cannot observe every quota counter, audit row, and permission cache | Never rely on the attestation. Restrict dispatch to pre-commit read-only regions, where reversibility is vacuous because nothing was committed. Treat any need for genuine reversibility as proof that you are out of scope |

Four of seven are deployable today within scope; Algorithm 4 needed a real correction; Algorithm 5
needs replacing; Algorithm 1 needs a better groundability policy than a stoplist.

### 6.3 The validation blocker: you cannot replay production

Algorithm 5 is where the benchmark framing and deployment diverge most sharply, and the divergence is
not a matter of engineering effort. Grouped replay (lines 8–12) re-executes an artifact against a
fresh world from a recorded entry state; the perturbation suite (lines 13–17) does it again under
entity swaps, empty and oversized collections, nulls, reordering, and injected faults. In AppWorld
that is a world reset. In production there is no reset: repeated reads consume quota, write audit
rows, trip rate limits, and cost money, and the perturbed inputs describe entities that do not exist.

The production substitute has two halves, and it is strictly weaker.

**Log-replay for value equivalence.** Re-run the artifact's program against *recorded* tool responses
and compare live-outs, effect multiset, and state digest. This validates the transforms and the
program's determinism. It cannot validate generalization, because the recorded responses are exactly
the ones the artifact was synthesized from.

**Shadow accumulation for generalization.** `mode="shadow"` scores every entry state, executes
nothing, and logs what the artifact *would* have produced alongside what the baseline actually did.
Over live traffic this yields agreement labels on genuinely unseen entities — the thing log-replay
cannot give. Promote only after $N$ independent agreements spanning distinct principals and distinct
days, with $N$ set so that the Eq. (18) bound is non-vacuous.

This is slower than active replay by weeks, and it never tests the tail that the perturbation suite
was designed to reach: an artifact can accumulate a thousand shadow agreements and still have never
seen an empty result set. Two consequences follow, and both are load-bearing.

First, **the permutation test in Algorithm 4 stops being a refinement and becomes the primary
defense.** In the paper, a spurious branch predicate is caught by perturbation replay on unseen
values. In production that safety net does not exist, so the only thing standing between a chance
correlation and a live dispatch is the statistical check at synthesis time. A deployment that skips
line 18 has no protection at all.

Second, **the perturbation suite must be reconstructed against a staging environment or not claimed.**
If you have a staging system with production-like data, run Algorithm 5 there and say so. If you do
not, the artifact ships with a documented gap: it is validated on the distribution it has seen, and
its abstention behaviour on the tail is unverified. Both are defensible positions. Pretending the
suite ran is not.

### 6.4 Compilation belongs in CI

Every artifact pins exact model, prompt, tool-schema, and policy hashes in $H$ (§3.3). Real teams edit
prompts weekly. The interaction is fatal if artifacts are treated as long-lived assets: a prompt
touch-up invalidates the entire registry, every dispatch misses, and coverage decays to zero — silently
and correctly, because failing closed produces no error.

The fix is a reframe rather than a mechanism. **Artifacts are build outputs, not assets.** Compilation
belongs in CI, triggered by any change to the prompt, the tool manifest, or the effect catalog:

1. prompt or schema change lands on a branch;
2. CI recompiles from the last $N$ days of captured traces and diffs the registry against the previous
   revision — artifacts gained, artifacts lost, coverage delta;
3. the new registry deploys in `mode="shadow"` and must accumulate its promotion evidence before any
   live dispatch;
4. the previous signed registry stays resolvable for atomic pointer rollback.

This costs a compile job and a shadow window per prompt change. It also converts the maintenance
problem from an unbounded liability into a fixed per-deploy cost, and it makes coverage decay visible
in a diff instead of invisible in production. Teams that cannot afford a shadow window per prompt
change should not deploy this system; that constraint is a reasonable filter, not a defect.

### 6.5 Specification gaps resolved by the implementation

Writing the five use cases surfaced four missing controls in the proposal. Release 0.6.0
implements all four and tests the isolation-sensitive paths.

| Original gap | Implemented resolution |
|:--|:--|
| Compilation had no tenant or principal argument | `optimize(..., partition_by=...)` partitions the corpus before TGWS or GRC fitting, preventing cross-partition statistics from influencing artifacts. |
| The generic decorator had no deployment mode | `compact(..., mode="shadow"|"live"|"off")` exposes the same fail-closed rollout modes as the runtime adapters. |
| The catalog could not prohibit reconstructed sensitive slots | Per-tool `literal_only` paths are enforced during provenance construction and synthesis. |
| $\Theta$ was a static stoplist | Normalization computes per-field cardinality and entropy; provenance rejects low-cardinality transformations under a configurable threshold. |

These controls do not change the seven algorithms, but they close specification holes
that would otherwise make the public API unsafe or ambiguous.

### 6.6 Build the compiler, or hand-write the regions?

The honest question a team should ask before adopting this, and the arithmetic that answers it.

The compute break-even $N^\star$ of Eq. (12) is not the engineering break-even. Library slices v0.1
through v0.4 (§5.8) total roughly twelve weeks — about one engineer-quarter, call it \$70,000 fully
loaded. Take an episode spend of \$0.25 and the 8% mean request reduction observed across the five
use cases. Prompt caching discounts the removed prefill, so dollar savings run roughly a third of
request savings (§3.4) — about 2.7% of spend, or \$0.007 per episode:

$$
N^\star_{\text{eng}} \;\approx\; \frac{\$70{,}000}{\$0.007\ \text{per episode}}
\;\approx\; 1.0\times10^{7}\ \text{episodes}
\;\approx\; 27{,}000\ \text{episodes/day sustained for a year}
$$

So the full compiler repays its own construction above roughly $3\times10^{4}$ episodes per day on a
stable prompt, and does not below it. **None of the five use cases reaches that**: Tier-1 support at
4,000 episodes/day is short by a factor of seven, and the enterprise deployment at 1,900/day by a
factor of fourteen. The threshold is sensitive to episode spend — at \$1.00 per episode it falls to
about 7,000/day — so the honest form of the rule is that the compiler needs either high volume or
expensive episodes, and preferably both.

**Below that threshold, the correct move is: run the v0.1 estimator, read the top five regions it
finds, and hand-write them as ordinary tools.** Two hours each. You capture essentially the same
savings, you skip the compiler entirely, and the agent's own model selects the new tool — which costs
you one model request per invocation that the runtime dispatch would have eliminated, and buys you an
implementation any engineer on the team can read and change.

That comparison sets the real boundary of this work's value, and it is narrower than "compile your
agent". The compiler earns its place on two things a hand-written tool cannot do: **discovery**, of
regions nobody knew were recurring — which the estimator delivers on its own, in two weeks — and
**maintenance**, keeping dozens of artifacts synchronized with a prompt that changes weekly, which is
precisely the CI story in §6.4. A team with five known hot regions and a stable prompt should write
five functions. A team with sixty unknown ones and a weekly release train is the case for the
compiler.

## 7. Scope, effects, and safety

### 7.1 In scope

Structured API agents with typed tool arguments/results and observable model-request boundaries; connected regions of 2–8 tool events crossing $\ge2$ model requests; **pure computation plus mechanically verified snapshot-deterministic or replayable reads**, executed strictly before any state, history, budget, quota, or audit commitment; the closed transform library and decision lists of §4.3–4.4; offline compilation with immutable signed artifacts.

### 7.2 Out of scope

Hidden chain-of-thought collection; visual/desktop agents; **any state mutation in the scored condition** (idempotence alone does not make fallback safe); checkpoint-and-revert advantages unavailable to the baseline; unbounded loops or unrestricted generated code; general semantic equivalence; production safety certification; online self-rewriting during scored evaluation.

### 7.3 Preconditions for emitting an artifact

1. Support comes from distinct scenario groups, not loop iterations.
2. Entry-visible state suffices for eligibility; internal branches depend only on observations from calls declared `speculatable ∧ replayable`.
3. Tool schemas, versions, permissions, and effect classes are recorded.
4. A deployable exit contract is derivable from Train alone, with no hidden grader.
5. Every call has call-specific capability evidence, and the region ends before the first commitment of any kind.
6. Artifact and gate are frozen before Test.
7. The deployed baseline uses the same model, prompt, and tool interface that produced the mining traces.

When these do not hold, **abstention is the correct output.**

### 7.4 Application patterns and their hard boundaries

Applicability guidance and instrumentation requirements — **not seven evaluated domains**, and never citable as cross-domain evidence.

| Pattern | Extra spans required | Plausible compactions | Hard boundary |
|:--|:--|:--|:--|
| Multi-agent orchestration | Agent spans, handoffs, ownership, context filters | Stable routing predicates, parallel read fan-out | Never erase ownership, specialist policy, guardrails, or nested approvals |
| Tool-heavy workflow | Typed calls/results, schemas, retries, boundary ids, principals | Batching, fusion, deterministic binding, memoization | Preserve effects, ordering, rate limits, billing, permissions, error granularity |
| Long-running process | Session/job ids, pause/resume, timers, record versions | Read/validate state-machine segments, polling coalescence | Exactly-once writes, stale state, time drift, compensation stay out |
| Human-in-the-loop | Approval request/resolution, approver scope, policy hash | Evidence prep and validation **before** the approval | Approval is an immutable barrier; prior approval never licenses bypass |
| Memory-enabled agent | Memory reads/writes, namespace, identity, snapshot version | Versioned read caching, dedup, deterministic formatting | Writes, cross-user reuse, stale memory, identity leakage reject compaction |
| Enterprise automation | MCP spans, tenant/principal, RBAC, policy, audit, residency | Read-only macros, typed routing, batched lookups | Tenant isolation, consent, residency, credential scope, auditability |
| RAG / knowledge | Query, retrieval, rerank spans, provenance, index/ACL versions | Query and result dedup, embedding batches, citation assembly | Freshness, ACL, provenance, citation coverage, index version are key fields |

Memory, human decisions, retriever internals, index versions, and policy context all
require **application-owned attributes**. The SDK cannot infer them.

---

## 8. Evaluation

### 8.1 Environment

[AppWorld](https://aclanthology.org/2024.acl-long.850/): nine simulated apps, 457 APIs, state-based tests, collateral-damage checks, 750 tasks in 250 three-variant scenarios — Train 105/35, Dev 60/20, Test Normal 168/56, Test Challenge 417/139. It is the right primary environment because Train and Dev are *runnable and scored*, which grouped replay validation (Alg. 5) requires.

**Not a leaderboard submission.** The [repository rules](https://github.com/StonyBrookNLP/appworld) prohibit hardcoded API calls in agent logic and warn that checkpoint reversion is an unfair advantage. Therefore: label every result a modified non-leaderboard protocol; request author clarification without gating on it; pin the ACL 2024 artifact and exact hashes; never use checkpoint reversion in scored episodes; restrict all *learned artifacts* to the pure/speculatable pre-commit policy (the underlying agent may still perform ordinary task-required writes after control returns); never inspect taskwise Test reports.

### 8.2 Conditions (four, down from seven)

All learned methods receive the identical Train trajectories, labels, execution adapter, history reconstruction, and Dev budget.

1. **Frozen original agent** — no artifact.
2. **AWO-style straight-line macros** — frequent sequence bundling, no synthesized transforms or branches. The condition that isolates this paper's actual contribution.
3. **Guarded Agentic Compaction** — Algorithms 1–7 in full.
4. **Support-only gate ablation** — identical artifacts, contracts, runtime, and history adapter as (3); admission by Train support instead of the learned score, thresholded on Dev to match (3)'s Dev coverage. Isolates the gate for H4.

**Why MiniCache, Agentic Plan Caching, and EvoC2F were dropped from the scored protocol.** Faithful reimplementation of three systems — one of which requires token-level speculative decoding against a hosted interface that may not expose it — is three engineering projects. v1's own risk table names the hazard ("reimplemented baselines are weak → straw comparison") and then scheduled exactly that. Four solid conditions beat seven weak ones. These systems are engaged in related work and, budget permitting, as **Train/Dev-only diagnostics** clearly labelled as adaptations.

Additional Train/Dev diagnostics: exact normalized cache; embedding semantic cache; dependency scheduling/fusion where AppWorld exposes real concurrency; uncalibrated gate; and a hand-written read-only workflow as an **oracle upper bound** on $\phi\rho k$ — which also empirically validates Eq. (10).

### 8.3 Data separation and episode budget

**Train.** Five runs of the frozen agent on each of 105 tasks = 525 trajectories. Successes drive synthesis; failures are retained as negatives. All folds grouped by the 35 Train scenario ids. Learning curves from the first 1/2/3/5 preregistered rollouts.

**Dev.** Freeze candidate rules, transform library, gate features, and all learned parameters *before* touching Dev. Then $4\ \text{configs}\times 60 = 240$ selection episodes, followed by $60\times2\times4 = 480$ fresh comparison episodes. No method, prompt, or artifact changes after the freeze commit.

**Test Normal.** $168\times3\times4 = 2{,}016$ episodes. Raw outputs go to a sealed preregistered analysis script emitting only approved aggregates. No manual inspection of taskwise reports, trajectories, or errors.

**Test Challenge.** One variant per scenario (139 tasks) $\times$ 2 conditions (1 and 3) $\times$ 1 run $= 278$ episodes. Exploratory abstention study only; excluded from H2/H3 and from the registered i.i.d./conditionally i.i.d. sampling claim of Eq. (18).

| Phase | Episodes |
|:--|--:|
| Train generation | 525 |
| Dev selection + comparison | 720 |
| Test Normal | 2,016 |
| Test Challenge | 278 |
| Pilot + Train/Dev ablations + reproduction sample | ~660 |
| **Preregistered cap** | **≈ 4,200** |

Down from v1's 8,607. Deterministic local replays are tracked separately and are not capped.

### 8.4 Outcomes

**Co-primary** — TGC difference (lower one-sided 95% CI $>-0.05$) and model-request ratio (upper one-sided 95% CI $<0.90$).

**Secondary quality/safety** — SGC; committed forbidden effects (mechanically defined by the effect allowlist and API log); $R$, $F$, $\phi$; success conditional on compiled-path use; fallback and validation-failure rates; incident count; Test Challenge coverage and success.

**Efficiency** — model requests eliminated (never "tool calls bundled"); input/cached/output tokens; p50/p95 total, model, tool, gate, executor, verifier latency; artifact count, size, synthesis rate, rejection reasons, held-out support; cost per task and per successful task; paired both-success cost and latency.

**Construction** — offline tokens, CPU time, wall time, human review minutes, **zero human program-edit minutes**, and $N^\star$ from Eq. (12).

**Provenance diagnostics** (new in v2, and load-bearing) — data-edge precision/recall against a hand-labelled sample; ambiguity and ungrounded-slot rates; fraction of windows blocked by `UNKNOWN` effects vs. by Eq. (4). These explain *why* coverage is whatever it turns out to be, which is the paper's most transferable content.

| Dimension | Measure and evidence boundary |
|:--|:--|
| Model work | Input/output/reasoning/cached tokens where exposed; provider requests; **genuine decisions eliminated**; auxiliary gate-model tokens charged |
| Tools | Logical actions vs. physical RPCs reported separately; parallelism, batch size, retries, forbidden effects |
| Latency | End-to-end and per-stage p50/p95; critical path vs. summed work; warm/cold registry, gate, executor, verifier overhead |
| Cost | Unconditional per task and per success; paired both-success; construction; amortization; dated pricing; cache decomposition |
| Determinism | Normalized action-DAG hash diversity and success variance over repeated runs from one snapshot; external nondeterminism isolated |
| Correctness | TGC, SGC, contract satisfaction, effect-trace agreement, non-inferiority interval |
| Robustness | Degradation under schema, state, entity, null, order, duplicate, size, staleness, tool-error, policy shifts; invalid-entry rejection recall |
| Reliability | Error, timeout, assertion, verifier, fallback, incident rates; recovery success |
| Scalability | Ingest/mine/synthesize wall time and peak memory vs. span count; candidate explosion; registry/gate/executor p95 |
| Generalization | Unseen Test Normal scenario families; aggregate Challenge abstention; leave-one-app Train/Dev diagnostics. **No transfer claim to §7.4** |
| Trace integrity | Expected/stored trace and span counts, missing-parent rate, flush failures, inclusion probabilities, export hash reconciliation |

### 8.5 Statistics

- TGC is the mean over $168\times3=504$ Test Normal task-runs. Uncertainty resamples the **56 scenario ids** with all variants and runs attached.
- 10,000 paired scenario-cluster bootstrap replicates for the TGC difference and all ratios.
- Mixed-effects model (condition fixed; scenario and task random intercepts) as sensitivity.
- Intersection–union for the co-primaries. H4 uses the paired scenario bootstrap on $F$ plus the 5-point coverage constraint, inside a Holm-corrected secondary family.
- Report effect sizes and intervals. "No significant difference" is never evidence of equivalence.
- Thresholds, artifact sets, and reportable subgroups are never selected using Test outcomes.

The sealed analysis script is the only component that reads raw Test reports. Its source, hashes, bootstrap seeds, and allowed output schema are frozen before Test. Researchers receive tables, intervals, aggregate counts, and invariant counters — not trajectories.

### 8.6 Ablations (Train/Dev only)

Paraphrases and irrelevant context; unseen entity ids and binding permutations; empty/singleton/large/duplicated/reordered results; nulls and tool errors; stale state and version mismatch; policy/consent prerequisites; exact vs. semantic vs. stale-key cache failures; logical-call vs. physical-RPC accounting; **exact-match-only vs. transform-augmented provenance** (isolates Alg. 1's contribution); sequential vs. dataflow matching; fixed bundles vs. synthesized programs; success-only vs. success-plus-failure contract learning; depth-1 vs. depth-2 transforms; no branch synthesis; no hard guard / no learned gate / no verifier; support-only vs. risk-adjusted ranking; 1/2/3/5 rollouts per task.

Test failure analysis is aggregate only; discordant-case inspection and two-annotator labelling use Train/Dev.

---

## 9. Related work and the contribution boundary

Search cutoff **1 August 2026**. Many 2026 entries are preprints or workshop papers; titles, results, and status must be rechecked before submission.

| Work | What it already covers | Remaining distinction |
|:--|:--|:--|
| [AWO](https://arxiv.org/abs/2601.22037) | Mines repeated tool sequences into deterministic composite meta-tools; up to 11.9% fewer LLM calls, +4.2 pts success | **Scored baseline (condition 2).** This method must recover data-dependent *transforms and branches*, not sequences, and validate on separated scenarios |
| [EvoC2F](https://openreview.net/forum?id=ZSGB91kMOG) (ICML 2026) | Plan IR, dependency/effect semantics, idempotency, compiler optimization, contract tests, verification-gated evolution from successful trajectories | Typed IR/contracts are **adopted machinery, not contributions**. The gap is raw cross-execution discovery of observation-dependent subregions spanning several genuine model decisions in an unconstrained agent, plus a Dev-frozen entry gate and stateful held-out evaluation |
| [Programmatic Skills](https://openreview.net/forum?id=lsAY6fWsog) (COLM 2025), [WebXSkill](https://arxiv.org/abs/2604.13318), [SGDR](https://arxiv.org/abs/2606.04391), [Neuro-Symbolic Skill Induction](https://arxiv.org/abs/2605.01293) | Induce, verify, retrieve, execute programmatic skills including logic-grounded control flow and dynamic binding | Rules out any claim that episode-derived executable skills, subtrajectory mining, state-grounded retrieval, or branching skill programs are new |
| [SkillOpt](https://openreview.net/forum?id=2ONrrPIFYi), [Skill Induction for Code Agents](https://openreview.net/forum?id=GmCoFYNEIU) (CAIS 2026) | Verifier-guided skill compilation; verification-gated Playwright functions with cross-task reuse | Cross-task verified reuse is occupied. The distinction is provenance-based cross-trace synthesis of regions spanning several model requests plus a frozen entry gate |
| [AWM](https://proceedings.mlr.press/v267/wang25bx.html), [PANDO](https://arxiv.org/abs/2605.24785), [Executable Agentic Memory](https://arxiv.org/abs/2605.12294), [WALT](https://arxiv.org/abs/2510.01524), [SkillWeaver](https://arxiv.org/abs/2504.07079) | Textual workflow induction, online skill distillation, executable state graphs, learned deterministic web tools | The contribution cannot be "agents get more efficient with experience" |
| [Program Synthesis from Partial Traces](https://doi.org/10.1145/3729316) (PLDI 2025), [WebRobot](https://arxiv.org/abs/2203.09993) (PLDI 2022) | Synthesize programs, transformations, branches, loops from partial traces/demonstrations | Trace-to-program synthesis is not new. Added: agent-region discovery, model-boundary accounting, Train-derived contracts, selective deployment, end-to-end agent evaluation. [Syren](https://arxiv.org/abs/2504.14480) is reused where compatible or run as a synthesis baseline |
| [MiniCache](https://arxiv.org/abs/2607.20507), [GenCache](https://papers.neurips.cc/paper_files/paper/2025/hash/07024f0479ae2f4981ed6cb3ebd81620-Abstract-Conference.html), [Agentic Plan Caching](https://proceedings.neurips.cc/paper_files/paper/2025/hash/9549f7d06700f0966d5f938f1d11022a-Abstract-Conference.html) | Parameterized executable program caching, variation-aware response caching, plan retrieval and adaptation — with validation and fallback | Program/plan caching, variable extraction, validation, and fallback are all prior art. The residual question is whether raw stateful traces contain observation-dependent **subregions crossing several genuine model decisions** compilable under explicit effect contracts |
| [Compiled AI](https://arxiv.org/abs/2604.05150), [FlowCompile](https://arxiv.org/abs/2605.13647), [Agentic Compilation](https://arxiv.org/abs/2604.09718), [COVENANT](https://arxiv.org/abs/2607.25400) | Compile specifications, structured workflows, one-shot plans, or NL procedures; some include validation, fallback, drift handling | Their source is a *specification or predefined workflow*, not automatically discovered cross-trace regions |
| [Think Short Defer Smart](https://arxiv.org/abs/2607.26865), [Learn then Test](https://doi.org/10.1214/24-AOAS1998), [Conformal Risk Control](https://openreview.net/forum?id=33XGfHLtZg) | Calibrated agent routing/deferral and risk-controlling predictors | Calibrated routing is not novel; Alg. 6 *applies* LTT's fixed-grid correction and claims no new statistical theorem |

**Broader taxonomy.** Workflow search ([AFlow](https://proceedings.iclr.cc/paper_files/paper/2025/hash/5492ecbce4439401798dcd2c90be94cd-Abstract-Conference.html), [ADAS](https://proceedings.iclr.cc/paper_files/paper/2025/hash/36b7acf6f6010652b3f2a433774a66fe-Abstract-Conference.html)) designs a workflow rather than discovering recurrent subregions in an otherwise frozen agent. Online scheduling ([LLMCompiler](https://proceedings.mlr.press/v235/kim24y.html), [LLM-Tool Compiler](https://arxiv.org/abs/2405.17438), [Parrot](https://www.usenix.org/conference/osdi24/presentation/lin-chaofan)) optimizes the current request over a *supplied* dataflow graph; here the graph is inferred. Corpus abstraction ([LILO](https://proceedings.iclr.cc/paper_files/paper/2024/hash/819cebb05f993840e8a52d7564c5c282-Abstract-Conference.html), [Stitch](https://doi.org/10.1145/3571234), [egg](https://doi.org/10.1145/3434304)) presumes a sound equational theory that agent traces do not supply. Hierarchical control (the [options framework](https://doi.org/10.1016/S0004-3702(99)00052-1), [Agent Lightning](https://arxiv.org/abs/2508.03680)) motivates entry/program/exit structure but changes a policy rather than emitting a bounded artifact with a replayable contract. Process mining ([workflow mining](https://doi.org/10.1109/TKDE.2004.47), [Inductive Miner](https://doi.org/10.1007/978-3-642-38697-8_17), [local process models](https://arxiv.org/abs/1606.06066)) yields frequency and compact graphs — hypotheses, not proof that a region can replace decisions while preserving values and effects. JIT and [partial evaluation](https://www.itu.dk/~sestoft/pebook/pebook.html) ([Dynamo](https://doi.org/10.1145/349299.349303), [TraceMonkey](https://doi.org/10.1145/1542476.1542528)) supply the hot-path/guard/deopt vocabulary directly, but external tools, approvals, and irreversible effects make agent deoptimization materially harder than restoring machine state.

---

## 10. Go / no-go gates

### Gate 0 — Opportunity arithmetic, protocol, and power (Week 2)

**New in v2 and decisive.** Build only `v0.1` of the library, run it on a 100-trace pilot, and evaluate Eq. (10) directly:

1. measure $n_B$, the empirical distribution of removable boundaries, and the maximum achievable $\phi\cdot k$ under the declared effect policy;
2. verify the ceiling supports $\Delta\ge0.10$ — if the *oracle* ceiling is below 10%, **stop or reframe as a measurement study**;
3. confirm provenance precision/recall $\ge0.8$ on a hand-labelled 200-slot sample;
4. confirm pinned Train worlds reproduce baseline behaviour while Dev stays untouched;
5. confirm every compiled call resolves to explicit effects and capabilities, or is excluded;
6. confirm runtime contracts never call hidden evaluation code, and all four conditions share one adapter, history reconstruction, and corpus;
7. scenario-cluster power simulation shows $\ge80\%$ power for the $-0.05$ margin and the $0.90$ request ratio.

This gate costs ~2 weeks and ~\$80 of inference and can kill the project before any compiler exists. That is its purpose. If it fails, switch to a runnable stateful environment such as [ToolSandbox](https://arxiv.org/abs/2408.04682) after auditing its external-API dependencies, or publish the trace-structure measurement.

### Gate A — Real recurrence (Week 4)

$\ge8$ candidate families with $\ge5$ distinct Train scenario groups each; every eligible family crosses $\ge2$ removable model requests; $\ge3$ extend beyond authentication or another fixed prefix. Failure ⇒ AppWorld lacks compaction opportunity under a safe effect policy; stop or publish the negative structural analysis.

### Gate B — Automatic synthesis (Week 9)

$\ge3$ programs, **no human edits**, passing held-out Train-group replay on unseen values; $\ge1$ containing a synthesized transform (Alg. 3) and $\ge1$ an observation-dependent branch (Alg. 4). If only straight-line wrappers work, the method is not distinct from AWO — report that.

### Gate C — Frozen Dev policy (Week 13)

- $\phi\ge0.35$ Dev episode coverage — **raised from v1's 20%**, because Eq. (10) shows 20% cannot reach any interesting endpoint;
- $\ge2$ eliminated model requests per accepted nontrivial artifact, and measured $\phi\rho k\ge1.8$ at $n_B\approx18$;
- zero committed forbidden effects attributable to a compiled artifact;
- Alg. 6 returns a non-`RETIRE` threshold for $\ge3$ artifacts at $\alpha=0.05,\delta=0.10$;
- projected $N^\star\le500$ under the preregistered cost model.

Freeze the registry and thresholds in a signed manifest before Test.

### Gate D — Paper result

H2 and H3 both pass; aggregate Test Normal coverage $\ge0.35$; no committed forbidden effect on a compiled path; $\ge3$ nontrivial artifacts each used on $\ge5$ held-out scenarios. Otherwise report the boundary result **without weakening endpoints after the fact**.

---

## 11. Risks

| Risk | Consequence | Mitigation |
|:--|:--|:--|
| **Provenance recovery is too noisy** (new) | Every downstream stage is unsound | Hand-labelled precision/recall gate at Gate 0; conservative `groundable`; ambiguity cap $\kappa$; ungrounded slots reject the region |
| **The opportunity ceiling is below the endpoint** (new) | No systems result | Eq. (10) evaluated at Gate 0 before building; oracle read-only workflow measures the ceiling empirically |
| **Prompt caching erases dollar savings** (new) | Cost endpoint fails while request endpoint passes | Request count is the co-primary; cost is decomposed and reported, not thresholded |
| MiniCache / APC / EvoC2F / skill-learning overlap | Incremental contribution | Claim only the full conjunction; run AWO as a scored baseline and the rest as documented adaptations |
| Only shallow login prefixes recur | No meaningful synthesis | Gate A; H1 excludes authentication-only artifacts |
| Several tools in one model response counted as savings | Inflated "LLM savings" | Model-request ids recorded; Eq. (5) requires $\ge2$ interior boundaries |
| Scenario variants leak across folds | Inflated generalization | All folds and resampling grouped by the 250 scenario ids |
| Hidden grader leaks into the runtime contract | Invalid deployment claim | Contracts derived from Train only; sealed evaluator |
| Mutation or hidden commitment makes fallback unsafe | Duplicate or harmful actions | Speculatable+replayable capabilities required; staged history; digest attestation; no scored checkpoint reversion; incident over false rollback |
| Dev too small for a tight risk bound | Overstated guarantee | Alg. 6 is valid but wide under the registered i.i.d./conditionally i.i.d. group model; `RETIRE` when it cannot be met |
| AppWorld forbids hardcoded API logic | Invalid leaderboard comparison | Modified non-leaderboard protocol, pinned rules and version |
| Test inspection contaminates development | Invalid held-out evaluation | Sealed script, aggregate outputs only, failure analysis on Train/Dev |
| SDK processor drops or duplicates spans | Biased mining and accounting | One authoritative processor per run; pinned version; sync/flush discipline; count and hash reconciliation |
| `CompactingModel` changes history or run semantics | "Savings" are an adapter artifact | Seven conformance tests; `mode="off"` byte equality; single-agent local-tool v0.1; everything else fails closed |
| Semantic cache crosses freshness/ACL/tenant boundaries | Incorrect or unauthorized reuse | Principal, schema, state/index version, TTL, provenance are hard key fields; similarity only *retrieves* |
| Artifact traces certify later artifacts | Self-confirming loop | Baseline-only sentinels; source provenance preserved; time-split shadow evaluation |
| Library scope consumes the paper schedule | Core experiment unfinished | v0.1–v0.4 are on the critical path *because the paper uses them*; v0.5+ is explicitly post-paper |
| Model/provider drift | Irreproducibility | Pinned dated snapshots and manifests; fail closed on version mismatch |
| Compile cost exceeds savings | No systems benefit | Full construction accounting and $N^\star$ reported |
| One benchmark limits generality | Weak external validity | Stated as a limitation; no protocol changes to chase a second benchmark |

---

## 12. Ethics, privacy, security

Trace mining retains credentials, identifiers, and policy-sensitive actions — and
Algorithm 1 is *specifically* a machine for finding where a credential flowed. Agents SDK
generation and function spans can capture sensitive payloads; no exporter or local store
certifies redaction automatically. The system disables unnecessary payload capture,
redacts before persistence, encrypts controlled raw records, mines only typed projections
with salted tenant-scoped identifiers, and never collects chain-of-thought. Raw access is
tenant- and split-scoped. Public artifacts contain synthetic benchmark traces or redacted
schemas. The worked example in §5.7 uses AppWorld's simulated credentials.

Compilation makes errors faster and more consistent. Permissions, policy checks, confirmations, and consent steps survive even when most source traces take the same branch. The scored condition excludes irreversible mutation precisely because post-hoc fallback cannot undo it. The compiler is an execution optimizer, never an authority for consequential decisions.

AppWorld is simulated. Success shows benchmark feasibility, not production readiness: real deployment would need organization-specific access control, threat modelling, audit logs, incident response, drift management, genuine transactions, and far larger calibration sets.

---

## 13. Reproducibility

Release: the versioned Compaction Trace Profile, source adapters, canonical JSONL schema,
and boundary instrumentation (raw exports for Train/Dev and synthetic fixtures only; Test
releases limited to approved aggregates, manifests, and digests); a pinned Agents SDK
version with processor, flush, redaction, and span-completeness fixtures; **the transform
library, effect-catalog schema, and capability policy**; **hand-labelled provenance ground
truth**; scenario-grouped folds committed before Dev/Test; the full library (miner,
synthesizer, interpreter, gate, verifier, runtime); immutable artifact manifests with
provenance and readable `explain()` output; baseline behaviour specifications and
conformance tests; perturbation suites and ablation configs; aggregate Test metrics plus
per-task Train/Dev data where licensing permits; raw token counts, timings, CPU
measurements, dated prices; preregistration and statistical scripts; exact
environment/model/code/data hashes; **rejected artifacts and rejection reasons**;
canonical trace exports with count and digest manifests.

One end-to-end reproduction command, plus a check-only mode that verifies hashes, split separation, and artifact provenance without paid inference.

---

## 14. Schedule and budget

### 14.1 Eighteen weeks, one researcher

| Week | Deliverable | Library slice |
|---:|:--|:--|
| 1–2 | Pin AppWorld/model manifests; reproduce baseline; effect catalog; provenance ground truth; **opportunity arithmetic**; power simulation; preregister — **Gate 0** | v0.1 |
| 3–4 | 525 Train traces; `TraceEnvelope`, raw/IR stores, completeness reconciliation; recurrence inventory — **Gate A** | v0.1 |
| 5–6 | Canonical mining, live-in/out analysis, clustering, ranking; AWO baseline | v0.2 |
| 7–9 | Transform library, binding and branch synthesis, bounded interpreter, grouped replay — **Gate B** | v0.2 |
| 10–11 | Contract induction, perturbation and fault-injection harness, state/effect differential checks, version manifests | v0.2 |
| 12–13 | Gate features and calibration, signed registry, AppWorld `ExecutionAdapter`, staging/deopt tests, Dev grids, four-condition Dev comparison; freeze — **Gate C** | v0.3 |
| 14–15 | 2,016 Test Normal episodes | v0.3 |
| 16 | 278 Test Challenge episodes; Train/Dev ablations | — |
| 17 | Scenario-cluster statistics; Train/Dev failure annotation; reproducibility and trace-integrity audit; 50-episode independent rerun | — |
| 18 | Writing; final literature and claim audit | — |

Slack comes from the reduced condition count (three fewer reimplementations) and from replacing CEGIS/SyGuS with bounded enumeration. `v0.4` (`CompactingModel`, live SDK dispatch) is **not** on the paper's critical path — the paper runs against the AppWorld adapter — and is scheduled after submission.

### 14.2 Post-paper library phases

| Phase | Duration | Acceptance artifact |
|:--|--:|:--|
| L1 — `v0.4` live SDK dispatch | 3 wk | Non-streaming single-agent `CompactingModel`; all seven conformance tests; hosted tools and handoffs fail closed |
| L2 — scheduled recompilation | 3 wk | Time-window compile job, baseline-only sentinel corpus, shadow runner, signed promotion/retirement, drift circuit breaker, audit log |
| L3 — multi-agent and streaming | 4 wk | Handoff ownership preservation, agents-as-tools, streamed responses, session strategies |
| L4 — domain pilots | 4–8 wk | Separate HITL, RAG, enterprise read-only pilots; tenant threat model; load tests. **No production-safety claim without new evaluation** |

Scheduled recompilation means **immutable compilation epochs**, never self-editing code in a live request: observe both baseline and artifact executions with decision provenance; detect schema/feature/coverage/contract/cost drift and trip a circuit breaker; close a time-bounded window and compile offline; shadow on recorded responses only where required observations are logged, sandbox anything new, never duplicate effectful calls; validate against a baseline-only sentinel corpus so no artifact certifies itself; preserve time order across synthesis, calibration, and sentinel windows; canary only `PURE` or explicitly canary-safe artifacts; promote a signed immutable version with an atomic registry-pointer rollback; record time-to-disable.

### 14.3 Resources

CPU suffices for mining and bounded enumeration; one optional GPU for the small gate model. Fixed hosted inference across ~4,200 capped episodes. Planning estimate **USD 1,800–4,500**, depending on the frozen target model — roughly 60% below v1 because of the reduced condition count. Not a price claim; excludes labour and post-paper phases. Run a 10-episode pilot and project cost before Gate A, capped at USD 150. Add a second backbone only after the main result and reproducibility audit succeed.

---

## 15. Expected contribution

1. **Value-provenance recovery for agent traces** (Alg. 1) — dataflow from traces alone, with measured precision/recall. Independently useful for debugging, cost attribution, and PII-flow analysis, whether or not compaction pays off.
2. **A compilability criterion** (Eq. 4) that separates "the agent decided" from "the agent computed", and a mining procedure that is linear rather than exponential (Alg. 2).
3. **A synthesis method sized to the problem** — bounded version spaces and decision lists rather than general program synthesis, with the closed transform library published as the exact statement of expressive power.
4. **A valid, honestly wide admission guarantee** (Alg. 6, Eq. 18) that retires artifacts rather than overclaiming when data is thin.
5. **The feasibility frontier** (Eq. 10) — a closed form that tells any practitioner, before building anything, whether compaction can reach their savings target. This alone would have prevented v1's incompatible endpoints.
6. **`agent-compaction`** — a working library over a typed Episode IR with an OpenAI
   Agents SDK adapter and canonical JSONL store whose estimator answers "is there anything
   here?" before compilation investment.
7. **A negative-result boundary** — which regions are rejected, and whether because of hidden state, undeclared effects, ungrounded slots, ambiguity, or insufficient support.

A rigorous negative result is worth publishing. If apparent repetition dissolves under scenario grouping, unseen values, deployable contracts, and full cost accounting, that shows precisely where the attractive "agents compile themselves" story currently fails — and Eq. (10) plus the estimator make the failure legible instead of anecdotal.

---

## 16. Venue fit

- **Primary: MLSys** — best fit for a quality–coverage–latency–cost trade-off of a compiler and runtime.
- **PLDI** — viable only if the provenance recovery and synthesis semantics become substantial formal contributions.
- **ACL/EMNLP** — viable if agent learning and evaluation dominate and the compiler formalism stays modest.

Do not choose a deadline until Gate B shows that nontrivial automatic synthesis exists.

---

## 17. Bottom line

The vision is real but no longer open territory, and v1's version was not buildable: its endpoints were arithmetically self-contradictory, its core steps named research problems instead of procedures, and its library was a diagram.

v2 is buildable. Three concrete moves make it so. **Value provenance** (Alg. 1) turns "find recurring regions" into a hash lookup plus a bounded transform search. **Declared effects** (§5.3) turn an inference problem into a YAML file and make the system fail closed. **The feasibility frontier** (Eq. 10) turns endpoint selection from wishful thinking into arithmetic — and says plainly that the realistic band is 5–15%, not 20%.

The first two weeks build only the estimator and evaluate Eq. (10) on 100 pilot traces. If the oracle ceiling is below 10%, stop and publish the measurement. If recurring observation-grounded regions do cross real model boundaries, the remaining sixteen weeks are a falsifiable, literature-aware, and adequately scoped study — and the library is useful either way.

---

## References

1. Abuzakuk et al. [*Optimizing Agentic Workflows using Meta-tools*](https://arxiv.org/abs/2601.22037). Preprint, 2026.
2. Wei et al. [*EvoC2F: Compiling Tool Orchestration for Efficient and Evolvable LLM Agents*](https://openreview.net/forum?id=ZSGB91kMOG). ICML, 2026.
3. Wang et al. [*Agent Workflow Memory*](https://proceedings.mlr.press/v267/wang25bx.html). ICML, 2025.
4. Wang et al. [*Inducing Programmatic Skills for Agentic Tasks*](https://openreview.net/forum?id=lsAY6fWsog). COLM, 2025.
5. Wang et al. [*WebXSkill: Skill Learning for Autonomous Web Agents*](https://arxiv.org/abs/2604.13318). Preprint, 2026.
6. Li et al. [*Online Skill Learning for Web Agents via State-Grounded Dynamic Retrieval*](https://arxiv.org/abs/2606.04391). Preprint, 2026.
7. Rao and Kalluru. [*SkillOpt: Trajectory-Derived, Verifier-Grounded Compilation of LLM-Agent Skills*](https://openreview.net/forum?id=2ONrrPIFYi). ACM CAIS Agent Skills, 2026.
8. Wang, Sutawika, and Neubig. [*Skill Induction for Code Agents on Web Automation*](https://openreview.net/forum?id=GmCoFYNEIU). ACM CAIS Agent Skills, 2026.
9. Li et al. [*PANDO: Efficient Multimodal AI Agents via Online Skill Distillation*](https://arxiv.org/abs/2605.24785). Preprint, 2026.
10. Qin et al. [*Executable Agentic Memory for GUI Agent*](https://arxiv.org/abs/2605.12294). Preprint, 2026.
11. Prabhu et al. [*WALT: Web Agents that Learn Tools*](https://arxiv.org/abs/2510.01524). ICLR, 2026.
12. Zheng et al. [*SkillWeaver: Web Agents can Self-Improve by Discovering and Honing Skills*](https://arxiv.org/abs/2504.07079). Preprint, 2025.
13. Ferreira et al. [*Program Synthesis from Partial Traces*](https://doi.org/10.1145/3729316). PLDI, 2025. [Preprint](https://arxiv.org/abs/2504.14480).
14. Dong et al. [*WebRobot: Web Robotic Process Automation using Interactive Programming-by-Demonstration*](https://arxiv.org/abs/2203.09993). PLDI, 2022.
15. Trooskens et al. [*Compiled AI: Deterministic Code Generation for LLM-Based Workflow Automation*](https://arxiv.org/abs/2604.05150). Preprint, 2026.
16. Li et al. [*FlowCompile: An Optimizing Compiler for Structured LLM Workflows*](https://arxiv.org/abs/2605.13647). Preprint, 2026.
17. Chundru. [*Agentic Compilation: Mitigating the LLM Rerun Crisis for Minimized-Inference-Cost Web Automation*](https://arxiv.org/abs/2604.09718). Preprint, 2026.
18. Wang et al. [*COVENANT: Natural-Language Workflow Compilation for Aligned Agent Execution*](https://arxiv.org/abs/2607.25400). Preprint, 2026.
19. Farzaneh and Simeone. [*Think Short, Defer Smart, Act, and Repeat*](https://arxiv.org/abs/2607.26865). Preprint, 2026.
20. Angelopoulos et al. [*Learn then Test: Calibrating Predictive Algorithms to Achieve Risk Control*](https://doi.org/10.1214/24-AOAS1998). *Annals of Applied Statistics*, 2025.
21. Angelopoulos et al. [*Conformal Risk Control*](https://openreview.net/forum?id=33XGfHLtZg). ICLR, 2024.
22. van der Aalst, Weijters, and Maruster. [*Workflow Mining: Discovering Process Models from Event Logs*](https://doi.org/10.1109/TKDE.2004.47). *IEEE TKDE*, 2004.
23. Tax et al. [*Mining Local Process Models*](https://arxiv.org/abs/1606.06066). 2016.
24. Jones, Gomard, and Sestoft. [*Partial Evaluation and Automatic Program Generation*](https://www.itu.dk/~sestoft/pebook/pebook.html). 1993.
25. Gal et al. [*Trace-based Just-in-Time Type Specialization for Dynamic Languages*](https://doi.org/10.1145/1542476.1542528). PLDI, 2009.
26. Trivedi et al. [*AppWorld: A Controllable World of Apps and People for Benchmarking Interactive Coding Agents*](https://aclanthology.org/2024.acl-long.850/). ACL, 2024.
27. Lu et al. [*ToolSandbox: A Stateful, Conversational, Interactive Evaluation Benchmark for LLM Tool Use Capabilities*](https://arxiv.org/abs/2408.04682). Preprint, 2024.
28. Microsoft. [*STATE-Bench Agent Learning Track*](https://github.com/microsoft/STATE-Bench/blob/main/docs/AGENT_LEARNING_TRACK.md). Repository documentation, accessed 1 August 2026.
29. Shao et al. [*Lifting Traces to Logic: Programmatic Skill Induction with Neuro-Symbolic Learning*](https://arxiv.org/abs/2605.01293). Preprint, 2026.
30. Bala, Duesterwald, and Banerjia. [*Dynamo: A Transparent Dynamic Optimization System*](https://doi.org/10.1145/349299.349303). PLDI, 2000.
31. Chen et al. [*MiniCache: Reusable Program Caching with Small Model Interfaces for Efficient LLM Inference*](https://arxiv.org/abs/2607.20507). Preprint, 2026.
32. Chakraborty et al. [*Generative Caching for Structurally Similar Prompts and Responses*](https://papers.neurips.cc/paper_files/paper/2025/hash/07024f0479ae2f4981ed6cb3ebd81620-Abstract-Conference.html). NeurIPS, 2025.
33. Zhang, Wornow, and Olukotun. [*Agentic Plan Caching: Test-Time Memory for Fast and Cost-Efficient LLM Agents*](https://proceedings.neurips.cc/paper_files/paper/2025/hash/9549f7d06700f0966d5f938f1d11022a-Abstract-Conference.html). NeurIPS, 2025.
34. Zhang et al. [*AFlow: Automating Agentic Workflow Generation*](https://proceedings.iclr.cc/paper_files/paper/2025/hash/5492ecbce4439401798dcd2c90be94cd-Abstract-Conference.html). ICLR, 2025.
35. Hu et al. [*Automated Design of Agentic Systems*](https://proceedings.iclr.cc/paper_files/paper/2025/hash/36b7acf6f6010652b3f2a433774a66fe-Abstract-Conference.html). ICLR, 2025.
36. Kim et al. [*An LLM Compiler for Parallel Function Calling*](https://proceedings.mlr.press/v235/kim24y.html). ICML, 2024.
37. Singh et al. [*An LLM-Tool Compiler for Fused Parallel Function Calling*](https://arxiv.org/abs/2405.17438). Preprint, 2024.
38. Lin et al. [*Parrot: Efficient Serving of LLM-based Applications with Semantic Variable*](https://www.usenix.org/conference/osdi24/presentation/lin-chaofan). OSDI, 2024.
39. Grand et al. [*LILO: Learning Interpretable Libraries by Compressing and Documenting Code*](https://proceedings.iclr.cc/paper_files/paper/2024/hash/819cebb05f993840e8a52d7564c5c282-Abstract-Conference.html). ICLR, 2024.
40. Bowers et al. [*Top-Down Synthesis for Library Learning*](https://doi.org/10.1145/3571234). POPL, 2023.
41. Willsey et al. [*egg: Fast and Extensible Equality Saturation*](https://doi.org/10.1145/3434304). POPL, 2021.
42. Leemans, Fahland, and van der Aalst. [*Discovering Block-Structured Process Models from Event Logs*](https://doi.org/10.1007/978-3-642-38697-8_17). PETRI NETS, 2013.
43. Sutton, Precup, and Singh. [*Between MDPs and Semi-MDPs: A Framework for Temporal Abstraction in RL*](https://doi.org/10.1016/S0004-3702(99)00052-1). *Artificial Intelligence*, 1999.
44. Luo et al. [*Agent Lightning: Train ANY AI Agents with Reinforcement Learning*](https://arxiv.org/abs/2508.03680). Preprint, 2025.
45. OpenAI. [*OpenAI Agents SDK Guide*](https://developers.openai.com/api/docs/guides/agents) and [*Python SDK Tracing Reference*](https://openai.github.io/openai-agents-python/tracing/). Accessed 1 August 2026.
46. MLflow Project. [*MLflow Tracing*](https://mlflow.org/docs/latest/genai/tracing), [*OpenAI Agents Integration*](https://mlflow.org/docs/latest/genai/tracing/integrations/listing/openai-agent/), [*Trace Concepts*](https://mlflow.org/docs/latest/genai/concepts/trace/). Version 3.14.0 documentation, accessed 1 August 2026.
