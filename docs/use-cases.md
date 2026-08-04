# Guarded Agentic Compaction — Implementation Use Cases

**Companion to [proposal.md](../experiments/proposal.md) — v2.1, 1 August 2026**

This document is the adoption guide. [proposal.md](../experiments/proposal.md) specifies the algorithms (§4) and the
library (§5); this one shows five concrete agents, what compiles in each, what does not, and the
arithmetic that decides whether the exercise was worth it.

Throughout, a reference of the form **§N** or **§N.M** points at [proposal.md](../experiments/proposal.md), never at this document.

Read it with three things in mind.

**The numbers are illustrative.** Every $n_B$, $\phi$, $\rho$, and $k$ below is a plausible figure for
the described agent, not a measurement. That is exactly why `cx.estimate()` exists: it computes all
four from your own traces in about an hour, before any compiler runs. Never adopt a number from this
document — reproduce it.

**Rejection is the normal outcome.** Each use case ends with a *What is rejected, and why* subsection,
and those lists are longer than the artifacts. A system that compiles most of an agent is a system
with a bug.

**Four of the five land below 10%.** That is not a failure of the examples; it is the honest shape of
the opportunity, and it is why [proposal.md](../experiments/proposal.md) §3.4 sets the endpoint from arithmetic
rather than ambition.

---

## The adoption recipe

The same six steps apply to every use case below. Only step 2 requires human judgement; the rest are
mechanical.

| Step | What you do | Effort | Output | Stop if |
|---:|:--|:--|:--|:--|
| 1 | **Capture.** `cx.enable_tracing()` against MLflow or the SDK exporter. One authoritative tracer (proposal §5.5). Sampling 1.0 for the mining window. | ~1 day | at least 100 episodes spanning 5 or more distinct scenario groups | You cannot see model-request boundaries, or payloads are truncated |
| 2 | **Declare effects.** Write `effects.yaml` for your most-called tools. Everything undeclared stays `UNKNOWN` and is never compiled. | 0.5–2 days, plus waiting on other teams | An effect catalog covering the top 10–20 tools | Your tool surface is mostly writes — Eq. (5) will reject nearly every window |
| 3 | **Estimate.** `cx.estimate(traces, effects)`. Read $n_B$, the ceiling on $\phi\cdot k$, and what is blocked and why. | ~1 hour | A go/no-go number from Eq. (10) | The **oracle** ceiling is below about 5% |
| 4 | **Compile and read.** `cx.compile(...)` then `registry.explain()`. A human reads every synthesized program. | ~1 day | A registry plus readable pseudocode per artifact | You cannot read an artifact and say what it does — do not ship it |
| 5 | **Shadow.** Deploy with `mode="shadow"`. Score and log what *would* have dispatched. Zero behaviour change. | 1–2 weeks | Measured $\phi$, verifier pass rate $\rho$, disagreement rate | Shadow $\rho<0.9$, or shadow $\phi$ far below the Dev estimate |
| 6 | **Go live narrowly.** `mode="live"` with the smallest artifact set clearing the gate. Watch incidents, not just savings. | ongoing | Realized savings and an incident count | Any committed forbidden effect, ever |

Step 3 saves the most time, because it can return a decisive no for the price of an afternoon. Step 2
is the one teams underestimate: the catalog cannot be inferred (proposal §5.3), it is gated on other
teams answering "does this read burn quota or write an audit row", and its coverage sets a hard
ceiling on everything downstream. Use case 5 budgets it concretely.

The most useful habit is running step 3 *before* step 2 is finished. `cx.estimate()` attributes blocked
windows by tool and by reason, so the catalog gets written in descending order of value rather than
alphabetically. In use case 5, six of fifty-five undeclared tools accounted for 71% of the
`UNKNOWN`-blocked windows.

---

## What the five use cases show

Each row is the section's own Eq. (10) computation, $\Delta = \phi\rho k / n_B$.

| # | Agent | $n_B$ | $\phi$ | $\rho$ | $k$ | $\Delta$ | Verdict |
|--:|:--|--:|--:|--:|--:|--:|:--|
| 1 | Tier-1 support over internal APIs | 16.2 | 0.40 | 0.90 | 4.0 | **8.9%** | The reference case. Clears shadow, misses the 10% endpoint |
| 2 | Internal knowledge assistant (RAG) | 11.5 | 0.29 | 0.85 | 4 | **8.6%** | Works, but the guard — not the program — is the whole contribution |
| 3 | Refund approval with a human in the loop | 12.4 | 0.38 | 0.90 | 3.7 | **10.2%** | Best candidate for a first production pilot: everything is pre-commit and read-only |
| 4 | Multi-agent triage with handoffs | 14.2 | 0.45 | 0.90 | 2 | **5.7%** | Compiles a *predicate*, not a sequence. Needs library v0.5+ |
| 5 | Multi-tenant enterprise ops over MCP | 22.3 | 0.32 | 0.88 | 4 | **5.0%** | Do not build the compiler. Ship the estimator and stop |

Two patterns are worth naming. First, $k$ is bounded by how much *contiguous* read-only work an agent
does before its first commitment, and in practice that is 2–4 boundaries, not 8. Second, $\phi$ is
bounded by the hard guard, and every additional key field — tenant, principal, policy version, index
version — multiplies the partition and divides the support. Use case 5 fails on precisely this: its
guard is correct, and its correctness is what makes it uneconomic.

---


## Use case 1 — Tier-1 customer support agent over internal APIs

**Setting.** A Tier-1 support agent serves four SaaS tenants from one deployment, roughly 4,000 ticket episodes per day, each ticket arriving from a structured intake form. The four tenants are roughly balanced, so any one of them is about a quarter of the episode stream. Its tool surface is `auth.issue_service_token`, `crm.find_customer`, `crm.get_subscription`, `billing.list_invoices`, `entitlements.check`, `kb.search`, `crm.update_ticket`, and `refunds.issue`. Everything below is scoped to a single tenant, Northwind, because the artifact is: measured over the 40 Train scenario groups Northwind contributes, that tenant's corpus gives $n_B = 16.2$ model requests per episode: four to five spent gathering the same read-only evidence on essentially every ticket, three to five on knowledge-base retrieval, the remainder on diagnosis, drafting, and the two write calls. The evidence prefix is mechanical work priced at a full provider round-trip per step, and it is the same work whether the ticket is about SSO provisioning or a duplicate charge.

**Why it qualifies.** The candidate region $W$ runs from `MODEL_REQ #1` — the boundary at which `auth.issue_service_token()` is chosen — through the `entitlements.check` result, matching §5.7's convention that the dispatching boundary is inside the window and is one of the removed requests. Its live-ins under Eq. (3) are $\mathrm{LiveIn}(W)=\{$`ticket.requester_email`, `ticket.product_area`$\}$, both present in the entry state $z$ because the intake form is structured, so Algorithm 2 line 11 passes. `tenant_id` and `principal` are *not* Eq.-(3) live-ins — no slot in $W$ consumes them — but they are pinned in $H$ as isolation keys and are the `key:` dimensions of every catalog entry in the region. Eq. (4) holds slot by slot: the four `token` slots are identity edges on `tk.token` (an in-region observation); `email` is $\texttt{lower}$ of `z.ticket.requester_email` (depth 1); the `customer_id` slots are $\texttt{filter(status == "active")} \mathbin{|\!>} \texttt{project(id)}$ over the `crm.find_customer` result (depth 2) or an identity echo from a nearer in-region producer; `feature` is an identity edge on `z.ticket.product_area`; `limit` is $\texttt{Const}(3)$. The two $z$-derived slots depend on an extension to Algorithm 1 described below and are not recoverable under the published listing. No slot's value first appears in a model response. Eq. (5) holds on both counts: five model-request boundaries fall strictly inside $W$ on the enterprise arm and four on the other, against a minimum of two; and every event in $W$ is `READ_EXTERNAL` with `speculatable ∧ replayable`, so $\mathrm{eff}(e)\in\mathcal{E}_{\text{allowed}}$ throughout. $\mathrm{LiveOut}(W)=\{$`customer_id`, `tier`, `seats`, `invoices`, `entitlement`$\}$.

The region ends strictly before `crm.update_ticket`, the first commitment in the episode — §7.3 precondition 5. That holds only because the token mint at the head of the region commits nothing: the catalog declares that it consumes no quota and writes no counter in the set `stage.reversible()` attests over at §4.7 (environment/database state, history, budget, wall-clock/RNG projection, quota/billing/audit counters, permission context). That is a per-deployment claim in the §5.3 sense — "a nominal read can still burn quota, create audit state, or observe time-varying data" — and must be re-verified before `mode="live"`. In a deployment whose mint writes an audit row, the region's *first* event is a commitment, precondition 5 fails there rather than at `crm.update_ticket`, and the correct response is to move the mint to the baseline and take the token as a live-in at the `crm.find_customer` boundary, which costs one removed request and requires every number below to be recomputed.

**Trace fragment.**

```text
ENTRY  z = { tenant_id:"t_northwind", principal:"svc.support.tier1",
             ticket:{ id:"TCK-40219", intake:"form_v3",
                      requester_email:"Dana.Whitfield@Northwind-Labs.example",
                      product_area:"sso_scim" } }

MODEL_REQ #1  → MODEL_RESP: call auth.issue_service_token()
TOOL_RESULT   → { token:"svc_a41c9e2b", scope:"support.read", expires_in:900 }

MODEL_REQ #2  → MODEL_RESP: call crm.find_customer(
                    token="svc_a41c9e2b",
                    email="dana.whitfield@northwind-labs.example")
TOOL_RESULT   → [ { id:"cus_3PD7WQ", status:"closed",  account:"Northwind Labs",
                    email:"dana.whitfield@northwind-labs.example" },
                  { id:"cus_8QK1MZ", status:"active",  account:"Northwind Labs",
                    email:"dana.whitfield@northwind-labs.example" } ]

MODEL_REQ #3  → MODEL_RESP: call crm.get_subscription(
                    token="svc_a41c9e2b", customer_id="cus_8QK1MZ")
TOOL_RESULT   → { customer_id:"cus_8QK1MZ", plan_id:"plan_ent_240",
                  tier:"enterprise", seats:240, renews_on:"2027-02-01" }

MODEL_REQ #4  → MODEL_RESP: call billing.list_invoices(
                    token="svc_a41c9e2b", customer_id="cus_8QK1MZ", limit=3)
TOOL_RESULT   → { customer_id:"cus_8QK1MZ", invoices:[
                    { id:"inv_2026_07_0091", status:"open", issued:"2026-07-01",
                      line_items:[ {sku:"seat",       amount_cents:11400},
                                   {sku:"sso_addon",  amount_cents:2400} ] },
                    { id:"inv_2026_06_0088", status:"paid", issued:"2026-06-01",
                      line_items:[ {sku:"seat",       amount_cents:11400} ] },
                    { id:"inv_2026_05_0084", status:"paid", issued:"2026-05-01",
                      line_items:[ {sku:"seat",       amount_cents:11400} ] } ] }

MODEL_REQ #5  → MODEL_RESP: call entitlements.check(
                    token="svc_a41c9e2b", customer_id="cus_8QK1MZ",
                    feature="sso_scim")
TOOL_RESULT   → { feature:"sso_scim", entitled:true, source:"plan_ent_240" }
──────────────────────────── region ends here ────────────────────────────────
MODEL_REQ #6  → MODEL_RESP: call crm.update_ticket(
                    ticket_id="TCK-40219", status="pending_customer",
                    resolution_note="SSO/SCIM is included in your Enterprise
                      plan; the July line item is the add-on you already had.")
TOOL_RESULT   → { ok:true, version:7 }
MODEL_REQ #7  → MODEL_RESP: reply to customer
```

The token appears as an explicit argument because this internal API surface takes it as one. If a deployment carries it in a header instead, the trace envelope must surface it as typed input or Algorithm 1 sees no edge at all and `auth.issue_service_token` looks like dead code inside the region. That is an instrumentation requirement, not a nicety.

**What Algorithm 1 recovers.** This region requires an extension to Algorithm 1 that is not in the published listing: the entry-state record must be seeded into `Idx` before the event scan so that `TransformSearch` can reach `z.ticket.requester_email` and `z.ticket.product_area`. Lines 13–15 as published index only event outputs, and §5.7 does not seed $z$ either — it leaves `username` UNGROUNDED at Algorithm 1 line 9 and rescues it only via Algorithm 2 line 11's `EntryStateSchema` check, which works for an identity slot but cannot synthesize a transform. **Gap:** as published, Algorithm 2 line 10 fires before line 11, so with $z$ absent from `Idx` the `email` slot is marked UNGROUNDED, $|S| = 0$, and every window containing `crm.find_customer` is discarded — the artifact does not exist. Seeding $z$ into `Idx` (or moving the `EntryStateSchema` check ahead of the UNGROUNDED test) is a prerequisite for this use case, and it is a compiler change, not a configuration one.

Under that extension:

- `token="svc_a41c9e2b"` exact-matches `auth.issue_service_token → .token` in three later slots (four on the enterprise arm), $|S|=1$ each. Plain identity edges.
- `email="dana.whitfield@northwind-labs.example"` misses exact match, because $z$ carries `"Dana.Whitfield@Northwind-Labs.example"`. `TransformSearch` returns $\texttt{lower}$ at depth 1 against the seeded `z.ticket.requester_email`. Non-identity, and the reason the artifact survives tenants whose intake form does not normalize case.
- `customer_id="cus_8QK1MZ"` at `crm.get_subscription` exact-matches `recs[1].id`, $|S|=1$. That path is positional. Across the 22 supporting groups the active record sits at index 0 in 9 of them, so `recs[1].id` is not in $\Pi$ at Algorithm 3 line 2 and is dropped. The version space over the stable root path `recs` yields $\texttt{filter(status == "active")} \mathbin{|\!>} \texttt{project(id)}$ — the depth-2 select-then-project pattern §4.3 names as the dominant real case, and here it is doing entity resolution against a closed duplicate record. It is what makes the artifact correct for a customer never seen at compile time.
- `customer_id` at `entitlements.check` has three producers in the index: `crm.find_customer → [1].id`, `crm.get_subscription → .customer_id`, `billing.list_invoices → .customer_id`. $|S| = 3$, exactly at $\kappa$, so line 10 does not fire and the nearest producer wins. This is fragile in a way worth stating: if the invoice objects also echoed `customer_id`, $|S|$ would be 4, the slot would be marked AMBIGUOUS, and Algorithm 2 line 10 would discard the whole window. Region viability depends on redundancy in response schemas the team does not control.
- In the 61 refund-shaped traces, `refunds.issue(amount_cents=13800)` is recovered as $f\circ\sigma$ with $\sigma=$ `invoices[0].line_items` and $f = \texttt{project(amount\_cents)} \mathbin{|\!>} \texttt{sum}$, since $11400 + 2400 = 13800$. This is a genuine non-identity edge and it is consistent with the amount being mechanical arithmetic over the invoice; it says nothing about whether issuing the refund at all was a judgement, and Algorithm 4 finds no separating atom for that decision. The enclosing event is `WRITE_IRREVERSIBLE`, so Algorithm 2 line 8 discards every window containing it. The expression is not smuggled into the region's live-outs; adding a field the baseline never produced would change model-visible history and fail conformance test 3 of §5.6.
- **UNGROUNDED:** `resolution_note` on `crm.update_ticket` first appears in `MODEL_RESP #6`, matches no producer, and admits no $f\in\mathcal{T}^{\le2}$. $|S| = 0$, slot marked UNGROUNDED at line 9. Consequence: Algorithm 2 line 10 discards every window containing `MODEL_REQ #6`, which is precisely what pins the region's right edge at the entitlements result. This is the correct outcome — what to tell the customer is the decision the agent exists to make.
- **AMBIGUOUS:** `limit=3` is groundable under $\Theta$ (`int(v) ∧ |v| > 1`), misses exact match, and `TransformSearch` finds depth-$\le2$ numeric coincidences against small integers and list lengths already in the index (`len(recs) |> add(1)` among them). Whether $|S| > \kappa$ depends on what small integers the corpus happens to have produced upstream; on the runs where it does, line 10 discards the window even though `limit` is literally 3 in all 22 supporting traces and Algorithm 3 line 1 would have returned $\texttt{Const}(3)$ without looking at the index. **Gap:** the §5.3 catalog schema has no field for declaring a slot literal-only, and $\Theta$ offers only a string stoplist. Widening $\Theta$ to exclude small pagination integers is the available deployment-level workaround; a per-slot constant declaration in the catalog is the right fix and does not exist in the published schema.

**Effect catalog.**

```yaml
# effects/tier1-support.yaml
# anything not listed defaults to UNKNOWN and is never compiled.
# kb.search is deliberately absent: its ranking is non-deterministic across
# index refreshes, so it cannot satisfy replay equivalence at Alg. 5 line 10.
version: 1
tools:
  auth.issue_service_token:
    effect: READ_EXTERNAL          # mints a scoped token; returns a session handle
    capabilities: [speculatable, replayable]
    key: [principal]
    notes: no cacheable capability and no freshness window — the token is minted
      per dispatch and never reused from a prior episode. Verified for this
      deployment to consume no quota and to write no counter in the set
      stage.reversible() attests over; re-verify per deployment

  crm.find_customer:
    effect: READ_EXTERNAL
    capabilities: [speculatable, replayable, cacheable, reorderable]
    key: [principal, tenant, email]
    freshness_s: 300

  crm.get_subscription:
    effect: READ_EXTERNAL
    capabilities: [speculatable, replayable, cacheable]
    key: [principal, tenant, customer_id]
    freshness_s: 300

  billing.list_invoices:
    effect: READ_EXTERNAL
    capabilities: [speculatable, replayable, cacheable]
    key: [principal, tenant, customer_id, limit]
    freshness_s: 60
    notes: short freshness because a payment can land mid-episode; reorderable
      is withheld because Alg. 1 line 16 derives an order edge from the
      WRITE_IRREVERSIBLE/READ_EXTERNAL conflict with refunds.issue on the
      invoice resource. batchable is withheld because the endpoint takes one
      customer_id and there is nothing to fuse

  entitlements.check:
    effect: READ_EXTERNAL
    capabilities: [speculatable, replayable, cacheable]
    key: [principal, tenant, customer_id, feature]
    freshness_s: 300

  crm.update_ticket:
    effect: WRITE_IRREVERSIBLE
    capabilities: []
    key: [principal, tenant, ticket_id]
    notes: deliberately uncompilable. A customer-visible notification webhook
      fires on write, so the edit cannot be undone and stage.reversible() at
      Alg. 7 line 12 can never attest. Empty capabilities also exclude it from
      E_allowed, so Alg. 2 line 8 drops any window containing it.

  refunds.issue:
    effect: WRITE_IRREVERSIBLE
    capabilities: []
    key: [principal, tenant, invoice_id]
    notes: money movement. Never compiled in any mode.
```

**Synthesized artifact.**

```text
artifact  support.evidence_prefix@1   support 22/40 groups   removes k=4–5
──────────────────────────────────────────────────────────────────────────────
guard   model=gpt-5-2026-04-12  prompt=#c47b  tools=#19ae  policy=#8d31
        z.tenant_id  : str = "t_northwind"
        z.principal  : str = "svc.support.tier1"
        z.ticket.intake : str = "form_v3"
        z.ticket.requester_email : str  matches ^[^@\s]{1,64}@[^@\s]{4,64}$
        z.ticket.product_area : str
                     ∈ {sso_scim, api_quota, seat_mgmt, billing_portal}
        effects ⊆ {READ_EXTERNAL}  all speculatable ∧ replayable

program (θ = {ticket.requester_email, ticket.product_area}):
   tk   = call auth.issue_service_token()
   em   = θ.ticket.requester_email |> lower                            ← Alg.3
   recs = call crm.find_customer(token = tk.token, email = em)
   cid  = recs |> filter(status == "active") |> project(id)            ← Alg.3
   sub  = call crm.get_subscription(token = tk.token, customer_id = cid)
   inv  = call billing.list_invoices(token = tk.token, customer_id = cid,
                                     limit = 3)
   ent  = ⊥
   if sub.tier == "enterprise":                                        ← Alg.4
        ent = call entitlements.check(token = tk.token, customer_id = cid,
                                      feature = θ.ticket.product_area)
   assert  cid matches ^cus_[A-Z0-9]{6}$  and  sub.customer_id == cid
           and  len(inv.invoices) ≤ 3
   return  { customer_id: cid, tier: sub.tier, seats: sub.seats,
             invoices: inv.invoices, entitlement: ent }

verify  customer_id : str, non-null, matches ^cus_[A-Z0-9]{6}$,
                      provenance ∈ {crm.find_customer}
        tier        : str ∈ {free, team, business, enterprise},
                      provenance ∈ {crm.get_subscription}
        seats       : int ∈ [1, 5000], provenance ∈ {crm.get_subscription}
        invoices    : list, len ≤ 3, each ⊨ invoice_schema,
                      provenance ∈ {billing.list_invoices}
        entitlement : present iff tier == "enterprise"; when present
                      ⊨ entitlement_schema, provenance ∈ {entitlements.check}
        effect_multiset ⊆ {READ_EXTERNAL},  |calls| ∈ {4,5},  no WRITE_*
gate    q = GBM(entry features)   η = 0.05   (Dev, α=0.05, δ=0.10, |Λ|=11)
```

Only the last two guard clauses are Algorithm 5 line 2 hulls over $\mathrm{LiveIn}(W)$. The first three are manifest-style pins with a different job: `z.tenant_id` and `z.principal` are isolation keys — one artifact per tenant, one per principal — and `z.ticket.intake` is a schema-version pin on the intake form. $\eta = 0.05$ because Algorithm 6 line 10 returns an element of the pre-registered grid $\Lambda$; values off the grid cannot be produced by any run of it.

Algorithm 4 fires on a real observation-dependent branch. Across the 22 supporting groups, 8 issue `entitlements.check` and 14 do not; the atom $(\texttt{sub.tier}, =, \texttt{"enterprise"})$ — a string equality from $\mathrm{Ops}(\text{str})$ with the constant drawn from observed values — separates them with purity $1$ at $\varepsilon = 0$, so the decision list has length 1 and leave-one-group-out is clean. Note the consequence for Algorithm 5: because `entitlement` is present on only one arm, the live-out contract must be induced per arm. A single unconditional `non_null(entitlement)` clause from line 5 would reject the non-enterprise arm at line 10. The published listing does not spell this out; the implementation has to.

**Integration.**

```python
import compaction as cx

# 1. capture
cx.enable_tracing(backend="mlflow", experiment="tier1-support-northwind")

# 2. estimate before building anything
traces  = cx.load(backend="mlflow", experiment="tier1-support-northwind",
                  split="train")
effects = cx.EffectCatalog.from_yaml("effects/tier1-support.yaml")

print(cx.estimate(traces, effects))
#  n_B  = 16.2 model requests/episode
#  ceiling: phi=0.55  k=4.4  ->  max request reduction 14.9%   [Eq. 10]
#  blocked: 38% of windows by WRITE_*/UNKNOWN effects, 24% by ungrounded slots

registry = cx.compile(traces, effects, alpha=0.05, min_support=5, max_region=8)
registry.report()            # 1 artifact, 22/40 groups, rejection reasons
print(registry.explain())    # read the program before you run it
registry.save("artifacts/tier1-support/northwind/v1")

# 3. deploy — shadow first, always
from agents import Agent, Runner

reg = cx.Registry.load("artifacts/tier1-support/northwind/v1")
agent = Agent(
    name="tier1-support",
    model=cx.CompactingModel("gpt-5", registry=reg, mode="shadow"),
    tools=[auth_issue_service_token, crm_find_customer, crm_get_subscription,
           billing_list_invoices, entitlements_check, kb_search,
           crm_update_ticket, refunds_issue],
)
result = await Runner.run(agent, ticket_prompt("TCK-40219"))
```

Every number printed above is scoped to the Northwind experiment, and the whole sequence has to be run once per tenant: one artifact directory, one MLflow experiment, and one `CompactingModel` each. **Gap:** nothing in the §5.2 API takes a tenant or principal argument — `cx.load` filters only on `backend`, `experiment`, and `split`, and `cx.compile` has no partition key. The only available levers are a per-tenant experiment name (used above) or a per-tenant `split`. Pooling four tenants into one `cx.compile` call would let a single artifact draw support across tenants, which the §7.4 Enterprise-automation hard boundary (tenant isolation, credential scope) forbids; a first-class principal/tenant partition key belongs in `cx.load` and `cx.compile` and should be added before v0.4. Agents not on the Agents SDK use `@cx.compact(registry=reg)` on the step function and act on the returned `cx.Decision`.

**Savings.** Assumptions, each stated conservatively, and all within-Northwind unless marked:

- $n_B = 16.2$, measured on Northwind's 40 Train groups. This is not the pooled four-tenant figure.
- $k = 4.0$. The enterprise arm removes 5 model requests and the other 4; the observed enterprise share of dispatched episodes is 0.35, giving $\bar k = 0.35\cdot 5 + 0.65\cdot 4 = 4.35$. Rounded down to 4.0.
- $\phi = 0.40$ **within Northwind**. Support is 22/40 = 0.55 of Northwind's Train groups; the hard guard's tenant, principal, intake-version and `product_area` enum constraints plus the calibrated $\eta = 0.05$ take it down from there.
- $\rho = 0.90$, matching the §3.4 table's working assumption. Failures are dominated by `crm.find_customer` returning zero or two active records, which breaks the `cid` regex assert and abstains.

Eq. (10) on Northwind episodes: $\phi\rho k = 0.40 \times 0.90 \times 4.0 = 1.44$, and $\Delta = 1.44 / 16.2 = 0.089$. **8.9% fewer model requests per Northwind episode.** Fleet-wide the guard pins one tenant, so coverage is $\phi_{\text{Northwind}}\cdot\Pr[\text{tenant}=\text{Northwind}] = 0.40 \times 0.25 = 0.10$, giving $\phi\rho k = 0.10\times0.90\times4.0 = 0.36$ and $\Delta_{\text{fleet}} = 0.36/16.2 = 0.022$ — **2.2% across the whole deployment from this artifact alone.** The defensible range for this section is 2.2% to 8.9% depending on which denominator is being quoted, and the two must not be conflated. Reaching the paper's $\Delta = 0.10$ endpoint on Northwind episodes needs $\phi\rho k \ge 1.62$, so this artifact falls about 11% short of it even on its own tenant — consistent with §5.7's point that a single artifact is the unit of progress, not the whole result.

Dollars and latency are reported separately and will not match 8.9%. Under Eq. (11) with a model share of wall time $\mu \approx 0.6$, the p50 latency reduction on Northwind episodes is $0.6 \times 0.089 = 5.3\%$, minus about 16 ms of gate cost across $\bar b \approx 16$ boundaries and $0.40 \times 60\,\text{ms}$ of execute-and-verify. Note the asymmetry Eq. (8) makes explicit: the $\bar b\,c_g$ gate term is paid on every episode of all four tenants, while the saving accrues only to the one the guard pins. Cost lags further: the four removed requests sit deep in a heavily cached prefix, so their marginal $c^{\text{in}}_{\text{cold}}$ is small and the dollar ratio should be expected in the 0.95–0.97 band on Northwind episodes, reported with the Eq. (9) decomposition rather than assumed equal to the request ratio.

What would make it worse. Tenant partitioning is not a future threat — it is already priced into the 2.2% figure, and closing the gap means compiling three more artifacts. With `min_support=5` scenario groups enforced per tenant, the two smallest tenants may not clear it and get no artifact at all, in which case fleet-wide $\Delta$ stays near 2.2% indefinitely. Algorithm 6 is the second: with roughly 20 Dev groups, the Clopper–Pearson upper bound at $\alpha = 0.05$ and $\delta/|\Lambda|$ typically requires *zero* observed violations, so one violation empties $\mathrm{Adm}$ and returns RETIRE — savings 0, which is the correct output and not a failure. Third, every abstained dispatch still pays $\phi(1-\rho)c_w$ in Eq. (8); if merged-account tickets rise and $\rho$ drops to 0.75, the Northwind $\Delta$ falls to $0.40\times0.75\times4.0/16.2 = 7.4\%$ while the wasted-attempt term grows.

**What is rejected, and why.**

- **`crm.update_ticket`.** `WRITE_IRREVERSIBLE` with `capabilities: []`, so $\mathrm{eff}(e)\notin\mathcal{E}_{\text{allowed}}$ and Eq. (5) fails at Algorithm 2 line 8. The effect label is the strict one on purpose: the edit fires a customer-visible notification webhook the moment it lands, so `stage.reversible()` at Algorithm 7 line 12 cannot attest that history, audit counters and external state equal the entry snapshot, and nothing about the write is undoable. §7.2 puts any state mutation out of the scored condition regardless, and idempotence would not change that.
- **`refunds.issue`.** `WRITE_IRREVERSIBLE`, again Eq. (5) at line 8. Algorithm 1 does recover the `amount_cents` binding as $\texttt{project(amount\_cents)} \mathbin{|\!>} \texttt{sum}$, which shows the amount is mechanical — and it is still rejected, because a verifier failure after money moves is classified INCIDENT at Algorithm 7 line 10/13, not fallback. The runtime does not pretend to roll back.
- **The `resolution_note` — what to tell the customer.** The string first appears in a `MODEL_RESP`, is not constant across supporting traces, and is not $f(\omega)$ for any $f\in\mathcal{T}^{\le2}$ and any $\omega\in\mathrm{Obs}_{<s}\cup z\cup\mathrm{Const}$. Eq. (4) fails; Algorithm 3 returns $\bot$ at line 9. This is the region's right edge and it should be. Compiling it would be exactly the silent wrongness the design exists to prevent.
- **Refund eligibility — whether a credit is warranted.** Traces diverge here, and Algorithm 4 finds no atom over the observable typed paths that separates them with purity $1-\varepsilon$ at $\varepsilon = 0$; line 11 returns $\bot$ because $\mathrm{Rem}\neq\varnothing$. The divergence is a real judgement, not a rule. Contrast with `sub.tier == "enterprise"`, which does separate perfectly and is therefore compiled.
- **The approval barrier.** Where tenant policy routes refunds above a threshold to a human approver, that approval is an immutable barrier under §7.4. It is never compiled, evidence prep before it is the only compilable part, and a prior approval never licenses a bypass.
- **`kb.search`.** Absent from `effects.yaml`, therefore `UNKNOWN` under §5.3 and never compiled, and any window containing it dies at Algorithm 2 line 8. This is the right default: its ranking shifts with index refreshes, so it would fail replay equivalence at Algorithm 5 line 10 anyway.
- **Any cross-tenant or cross-principal reuse.** Forbidden outright by the §7.4 Enterprise-automation hard boundary. The guard pins `z.tenant_id` and `z.principal` to equality rather than an enum, and support is counted within one tenant only. Two customers with the same email at different tenants must never resolve through the same artifact.

**Adoption caveats.** The estimator slice **v0.1** is enough to decide whether to proceed: it produces the $n_B = 16.2$ and the blocked-window breakdown above, and if the write-effect and ungrounded-slot blockage were higher, the answer would be no. The artifact shown requires **v0.2** (Algorithms 3–5, the interpreter, `explain()`, the registry) to exist offline, plus the Algorithm 1 entry-state seeding change described earlier; **v0.3** to get honest coverage from `mode="shadow"` on live traffic; and **v0.4** for `mode="live"`. Handoff to a Tier-2 agent and hosted tools need v0.5+, and under §5.6 conformance test 7 they must reject rather than degrade. A deployment that streams its final response can compile this region only if the wrapper can delegate the streamed turn without dispatching; the region ends two boundaries before it (`MODEL_REQ #6`, `#7`). Until the adapter supports that, §5.6 conformance test 7 requires the whole run to reject rather than degrade, and §5.8 pins v0.1 as non-streaming — so this is v0.5+ work.

Fails closed, in every case to BASELINE at cost $c_g$ (plus $c_x$ if execution had started): unlisted tool in the window, unseen `product_area` enum value, any change to the prompt, tool-schema, model or policy hash in the guard line, $q_a(z) > \eta$, `crm.find_customer` returning zero or more than one active record, a `line_items` shape the invoice schema does not admit, or a tool 4xx/5xx mid-region. Every one of these is an abstention, which Algorithm 5 line 17 treats as acceptable and a wrong answer as a hard reject. Every event in the region is a declared pre-commit read, so a mid-region abort leaves no business state behind — but that statement is exactly as strong as the catalog entry for `auth.issue_service_token`, which claims the mint writes no counter in the set `stage.reversible()` attests over. If a deployment's mint does audit-log, each abandoned attempt leaves an audit row, the abort is not clean, and either `stage.reversible()` must be configured to treat token-mint rows as out of the attested set or the mint must move outside the region; without one of those, a post-mint verifier failure is correctly classified INCIDENT at Algorithm 7 line 13, not fallback. The §5.6 post-emission deopt limitation still applies, so an outer controller or session transaction should own staging before `mode="live"`.

The single biggest thing that could make this not work: the assumption that `requester_email` and `product_area` arrive as structured entry-state fields. If a tenant's intake is free text and the model extracts them, both slots become UNGROUNDED under Eq. (4), the region collapses to `auth.issue_service_token()` alone, which has one interior boundary and fails Eq. (5). No amount of gate tuning, corpus size, or transform-library depth recovers it. The fix is a change to the intake form, not to the compiler — and if the form cannot change, the correct answer for that tenant is that there is nothing to compile.

---

## Use case 2 — Internal knowledge assistant (RAG)

**Setting.** An internal knowledge assistant answers employee questions over a permissioned document corpus using four tools: `search.embed(text)`, `search.retrieve(vector, k, acl_scope)`, `search.rerank(doc_ids, query)`, and `docs.fetch_metadata(doc_ids)`. Traffic is high-volume and repetitive in shape — the same normalize → embed → retrieve → rerank → assemble-citations sequence runs for every question, with only the query text and the principal's group set varying. Measured over 140 Train episodes spanning 140 distinct scenario groups (one group per episode), $n_B = 11.5$ model requests per episode (≈2.3 questions per episode; five boundaries per question: four retrieval-pipeline requests, one answer synthesis). Four of those five boundaries are a fixed mechanical pipeline that the model re-derives from scratch every time, and they are the entire opportunity here — the fifth, answer synthesis, is a real decision and stays.

**Why it qualifies.** The region $W$ spans the four retrieval boundaries and ends immediately before the synthesis request.

*Eq. (4), live-in groundability.* Live-ins are $\theta=\{$`question`, `principal.groups`, `kb.index_version_pin`, `kb.corpus_snapshot_pin`, `kb.embed_model_version_pin`, `kb.rerank_model_version_pin`$\}$, all present in the entry state $z$ at boundary #1 (the session record and the current user turn). The last four are pins — they are never passed as tool arguments; they are memo-key inputs and verifier reference values, which is why they must exist at lookup time. Every argument slot in $W$ is a constant or a bounded transform of $z \cup \mathrm{Obs}_{<s}$:

| Slot | Binding | Source |
|:--|:--|:--|
| `search.embed.text` | `θ.question \|> strip \|> lower` | $z$, $\mathcal{T}^{\le 2}$ |
| `search.retrieve.vector` | `emb.vector` (`id`) | in-region observation |
| `search.retrieve.k` | `Const(24)` | Alg. 3 line 1 |
| `search.retrieve.acl_scope` | `θ.principal.groups \|> project(group_id) \|> join(",")` | $z$, $\mathcal{T}^{\le 2}$ |
| `search.rerank.doc_ids` | `r.hits \|> project(doc_id)` | in-region observation |
| `search.rerank.query` | same binding as `embed.text` | $z$, $\mathcal{T}^{\le 2}$ |
| `docs.fetch_metadata.doc_ids` | `rr.ranked \|> topk(score, 8) \|> project(doc_id)` | in-region observation |
| widen-branch `k` | `Const(72)` | Alg. 3 line 1 |

No slot's value first appears in a `MODEL_RESP`, so Eq. (4) holds.

*Eq. (5), boundaries and effects.* $|B_\tau \cap \mathrm{interior}(W)| = 4$ (`MODEL_REQ` #1–#4), well above the required 2, so $k=4$. All four tool events are `READ_EXTERNAL` with `speculatable ∧ replayable ∧ cacheable`; no `WRITE_*` event is inside $W$. The region contains 4 tool events (5 when the widen branch fires), inside $[w_{\min},w_{\max}]=[2,8]$.

**Trace fragment.**

```text
z (entry state at boundary #1)
  question                   : "  How do I rotate the staging DB password? "
  principal.groups           : [{group_id:"all-staff"},{group_id:"eng"},
                                {group_id:"eng-platform"}]
  kb.index_version_pin       : "kb-idx-2026-07-28T03:00Z"
  kb.corpus_snapshot_pin     : "sha256:9c1e4b0a"
  kb.embed_model_version_pin : "emb-3-lg@2026-02"
  kb.rerank_model_version_pin: "rr-mini@2026-05"

MODEL_REQ #1  → MODEL_RESP: call search.embed(
                  text="how do i rotate the staging db password?")
TOOL_RESULT   → { vector:<f32[1536]>, embed_model_version:"emb-3-lg@2026-02" }

MODEL_REQ #2  → MODEL_RESP: call search.retrieve(
                  vector=<f32[1536]>, k=24,
                  acl_scope="all-staff,eng,eng-platform")
TOOL_RESULT   → { hits:[ {doc_id:"kb-2280", score:0.71,
                          snippet:"Staging Postgres credentials are rotated…"},
                         {doc_id:"kb-4471", score:0.68,
                          snippet:"Vault path for stg-db-root…"},
                         … 24 total ],
                  index_version:"kb-idx-2026-07-28T03:00Z",
                  corpus_snapshot:"sha256:9c1e4b0a",
                  retrieved_at:"2026-08-01T14:22:05Z" }

MODEL_REQ #3  → MODEL_RESP: call search.rerank(
                  doc_ids=["kb-2280","kb-4471","kb-8130", … 24 ids],
                  query="how do i rotate the staging db password?")
TOOL_RESULT   → { ranked:[ {doc_id:"kb-2280", score:0.93},
                           {doc_id:"kb-8130", score:0.88},
                           {doc_id:"kb-4471", score:0.79}, … ],
                  rerank_model_version:"rr-mini@2026-05" }

MODEL_REQ #4  → MODEL_RESP: call docs.fetch_metadata(
                  doc_ids=["kb-2280","kb-8130","kb-4471","kb-0996",
                           "kb-3312","kb-5507","kb-1024","kb-7768"])
TOOL_RESULT   → { docs:[ {doc_id:"kb-2280", title:"Rotating staging credentials",
                          url:"https://kb.corp/d/2280", owner:"eng-platform",
                          updated_at:"2026-06-11", acl_labels:["eng-platform"]},
                         … 8 total ] }

MODEL_REQ #5  → MODEL_RESP: answer text with inline citations
                ── REGION ENDS BEFORE THIS BOUNDARY ──
```

**What Algorithm 1 recovers.** `text="how do i rotate the staging db password?"` is groundable (string, length ≥ 3) but has no exact producer — the raw turn has capitals and surrounding whitespace. `TransformSearch` at $d=2$ against the entry state yields the non-identity binding `strip |> lower`, which is the whole "normalize" step. `acl_scope="all-staff,eng,eng-platform"` likewise has no exact producer; `TransformSearch` recovers `project(group_id) |> join(",")` over `z.principal.groups` — the second non-identity transform and the one that makes the artifact generalize to a principal never seen at compile time. `k=24` is an int with $|v|>1$ and therefore groundable, but it is identical across all supporting traces, so Algorithm 3 line 1 returns `Const(24)` rather than manufacturing a dependency. Each `doc_id` string has two producers (`search.retrieve.hits[].doc_id` and `search.rerank.ranked[].doc_id`); $|S|=2\le\kappa=3$, so line 11's nearest-producer rule binds `docs.fetch_metadata.doc_ids` to the rerank output. That resolution matters: binding to `retrieve` instead would silently discard the rerank ordering while still passing every type check.

One slot is correctly left **UNGROUNDED**. In 17 of the 78 Train groups containing a full retrieval window, `search.rerank.query` is not the normalized question but a model-authored rewrite — `"staging database credential rotation runbook"`. That value first appears in a `MODEL_RESP`, is not constant across traces, and is not in $\mathcal{T}^{\le 2}$ of any observation. Algorithm 1 marks the slot UNGROUNDED; Algorithm 2 line 10 drops those windows from the family. A further 6 groups pass a model-chosen `k` that varies across traces and is neither `Const` nor derivable from $z$, and are dropped the same way. Family support falls from 78 to **55 of 140 Train scenario groups**. This is the correct outcome — query rewriting is a genuine decision — and it is the single largest cap on coverage in this use case.

The trace profile must also treat a fixed-length numeric vector as one opaque typed value. If `flatten()` emits 1536 float coordinate slots, Algorithm 1's ambiguity cap $\kappa=3$ fires on thousands of near-duplicate coordinates and the region is rejected for spurious AMBIGUOUS slots.

**Effect catalog.**

```yaml
# kb_effects.yaml — anything not listed defaults to UNKNOWN and is never compiled
version: 1
tools:
  search.embed:
    effect: READ_EXTERNAL
    capabilities: [speculatable, replayable, cacheable]
    key: [text, embed_model_version_pin]
    notes: deterministic given the key, but consumes metered quota, so it is
           not elidable; embed_model_version_pin is an entry-state field
           emitted by the trace profile, because a memo key must be computable
           at lookup time and the response embed_model_version is not — the
           verifier checks the response field against the pin and aborts on
           mismatch, so a model rollover cannot silently change retrieval
           geometry; batchable is deliberately absent, since the declared
           signature search.embed(text) takes a single string and there is no
           batch endpoint to fuse into

  search.retrieve:
    effect: READ_EXTERNAL
    capabilities: [speculatable, replayable, cacheable]
    key: [principal_group_set, index_version_pin, corpus_snapshot_pin,
          vector_digest, k]
    freshness_s: 900
    notes: principal_group_set is the joined, ACL-bearing key field — never a
           similarity feature; the pins are entry-state values used for lookup,
           and the verifier separately checks the response index_version and
           corpus_snapshot against them

  search.rerank:
    effect: READ_EXTERNAL
    capabilities: [speculatable, replayable, cacheable]
    key: [doc_ids, query, rerank_model_version_pin]
    freshness_s: 3600
    notes: same pin/verify split as search.embed — rerank_model_version_pin is
           entry state, the response rerank_model_version is checked against
           it and aborts on mismatch; carries no ACL of its own, it reorders
           whatever it is given, so it must only ever receive doc_ids that
           this principal's retrieve returned

  docs.fetch_metadata:
    effect: READ_EXTERNAL
    capabilities: [speculatable, replayable, cacheable, batchable]
    key: [doc_ids, corpus_snapshot_pin]
    freshness_s: 300
    notes: batchable is correct here — the signature takes a list; 300 s is
           the shortest TTL in the region and therefore the binding reuse
           bound; title/url/owner/acl_labels are not principal-scoped in this
           deployment, so principal is deliberately absent from the key;
           re-verify per deployment before enabling cacheable

  docs.fetch_body:
    effect: WRITE_IRREVERSIBLE
    capabilities: []
    notes: returns document text but appends an immutable per-principal
           access-audit row; classified by its strongest effect, not its
           intent, so it is never compiled and the region assembles citations
           from retrieve snippets plus metadata instead of bodies

  docs.request_access:
    effect: WRITE_IRREVERSIBLE
    capabilities: []
    notes: files a ticket and notifies the document owner; this is the
           tempting "widen" action on an empty result set and it must never
           appear inside an artifact
```

State it plainly: `index_version`, `corpus_snapshot`, the principal's group set, the two model-version pins, and the freshness TTLs are **hard guard and cache-key fields, not similarity features**. A naive semantic cache keyed on embedding proximity gets both of these wrong and gets them wrong invisibly. Two questions with cosine similarity 0.98 asked by an `eng-platform` engineer and by a contractor in `all-staff` have different authorized answer sets, and a similarity cache will serve the first principal's passages to the second — an authorization failure with no error and no anomalous output. The same cache will serve pre-rollover passages for hours after a reindex, producing a fluent, well-cited, stale answer. §5.3's `key:` list is what converts those fields from soft signals into identity, and `freshness_s` is what bounds the age of any read that is reused — but it is declared *per tool*, and three of the four tools here declare different values, so what bounds the region is the smallest of them: `docs.fetch_metadata`'s 300 s. The guard block below therefore extends §5.7's printed format with a `memo keys` listing and an explicit region reuse bound; that is a deliberate addition to the audit surface, not a different renderer.

**Synthesized artifact.**

```text
artifact  kb.retrieve_and_cite@1   support 55/140 groups   removes k=4
──────────────────────────────────────────────────────────────────────────────
guard   model=gpt-5-2026-04-12  prompt=#c40b  tools=#1f9e  policy=#8a37
        z.question : str  len ∈ [8, 512]
        z.principal.groups : list[obj]  len ∈ [1, 24]
                             each.group_id : str  matches ^[a-z0-9-]{2,32}$
        z.kb.index_version_pin        : str  matches ^kb-idx-
        z.kb.corpus_snapshot_pin      : str  matches ^sha256:
        z.kb.embed_model_version_pin  : str  matches ^emb-
        z.kb.rerank_model_version_pin : str  matches ^rr-
        effects ⊆ {READ_EXTERNAL}  all speculatable ∧ replayable ∧ cacheable
        memo keys  search.embed        [text, embed_model_version_pin]
                   search.retrieve     [principal_group_set, index_version_pin,
                                        corpus_snapshot_pin, vector_digest, k]
                                       ttl 900
                   search.rerank       [doc_ids, query,
                                        rerank_model_version_pin]     ttl 3600
                   docs.fetch_metadata [doc_ids, corpus_snapshot_pin] ttl 300
                   region reuse bound = min(ttl) = 300 s

program (θ = {question, principal.groups, kb.index_version_pin,
              kb.corpus_snapshot_pin, kb.embed_model_version_pin,
              kb.rerank_model_version_pin}):
   qn    = θ.question |> strip |> lower                                 ← Alg.3
   scope = θ.principal.groups |> project(group_id) |> join(",")         ← Alg.3
   emb   = call search.embed(text = qn)
   assert emb.embed_model_version = θ.kb.embed_model_version_pin
   r     = call search.retrieve(vector = emb.vector, k = 24,
                                acl_scope = scope)
   assert r.index_version    = θ.kb.index_version_pin
          and r.corpus_snapshot = θ.kb.corpus_snapshot_pin
   if empty(r.hits):                                                    ← Alg.4
        r = call search.retrieve(vector = emb.vector, k = 72,
                                 acl_scope = scope)      # widen k only
        assert r.index_version    = θ.kb.index_version_pin
               and r.corpus_snapshot = θ.kb.corpus_snapshot_pin
        if empty(r.hits):                                               ← Alg.4
             return { citations: [], passages: [], abstain: true,
                      reason: "no_authorized_match",
                      index_version:   r.index_version,
                      corpus_snapshot: r.corpus_snapshot }
   rr    = call search.rerank(doc_ids = r.hits |> project(doc_id),
                              query = qn)
   assert rr.rerank_model_version = θ.kb.rerank_model_version_pin
   top   = rr.ranked |> topk(score, 8) |> project(doc_id)               ← Alg.3
   md    = call docs.fetch_metadata(doc_ids = top)
   assert len(md.docs) = len(top)
   return  { citations: md.docs, passages: r.hits, abstain: false,
             reason: null,
             index_version:   r.index_version,
             corpus_snapshot: r.corpus_snapshot }

verify  citations : list, len ∈ [0,8], each ⊨ citation_schema, non-null,
                    provenance ∈ {docs.fetch_metadata}
        passages  : list, len ∈ [0,72], provenance ∈ {search.retrieve}
        abstain   : bool, non-null,  abstain = true ⟺ len(citations) = 0
        reason    : str ∈ {"no_authorized_match", null}
        every citations[i].doc_id ∈ passages[*].doc_id
        index_version   = θ.kb.index_version_pin
                          (mismatch ⇒ abort, never serve)
        corpus_snapshot = θ.kb.corpus_snapshot_pin
                          (mismatch ⇒ abort, never serve)
        effect_multiset(run) ⊆ {READ_EXTERNAL}
        called_tools ∩ {docs.fetch_body, docs.request_access} = ∅
gate    q = GBM(entry features)   η = 0.10   (Dev, α=0.05, δ=0.10, |Λ|=11)
```

Both pin checks run on **every** path, immediately after each retrieve and before the empty test, and the abstain leaf returns the *observed* `index_version` and `corpus_snapshot`, not the pin. That ordering is what keeps the verifier's `index_version = θ.kb.index_version_pin` line from degenerating into a comparison of the pin with itself on exactly the branch this artifact cares most about. Two retrieves that legitimately return zero hits against a rolled index now abort to `BASELINE` instead of emitting a confident `no_authorized_match` stamped with a version the backend never confirmed.

The branch is a two-level decision list over the single list atom `empty(hits)` from `Ops(list)` in Algorithm 4 line 4, with $L_{\max}=3$ and $\varepsilon=0$: 43 of the 55 supporting groups take the direct path, 9 widen and then rank, 3 widen and find nothing. Purity is exact at $\varepsilon=0$ (Alg. 4 line 8), and `LeaveOneGroupOut` (Alg. 4 line 12) independently passes with no held-out error — these are two separate tests, an in-sample fit criterion and an anti-memorization check, and a perfectly pure decision list can still fail the second. It does not fail here, including on the 3-group abstain leaf, where each fold leaves 2 supporting groups. **The abstain leaf is the most valuable branch in this artifact, not a degradation.** It converts "no document authorized to this principal matched" into an explicit typed live-out — `abstain: bool` with `reason`, both verified — that the uncompiled synthesis request must consume, which is what stops the model from answering from parametric memory when retrieval returned nothing. Per Algorithm 5 line 17, abstention is an accepted result under every perturbation in $\Sigma$; a fabricated or unauthorized citation is a hard reject. With only 3 supporting groups on that leaf, the perturbation suite (empty and singleton lists) carries more of the validation weight than the mined evidence does — acceptable exactly because the leaf's output is abstention rather than an answer.

**Integration.**

```python
import compaction as cx

cx.enable_tracing(backend="mlflow", experiment="kb-assistant")

traces  = cx.load(backend="mlflow", experiment="kb-assistant", split="train")
effects = cx.EffectCatalog.from_yaml("kb_effects.yaml")

print(cx.estimate(traces, effects))
#  n_B  = 11.5 model requests/episode
#  ceiling: phi=0.39  k=4.0  ->  max request reduction 13.6%   [Eq. 10]
#  blocked: 22% of windows by UNGROUNDED slots (model-rewritten rerank query),
#           14% by docs.fetch_body (WRITE_IRREVERSIBLE)

registry = cx.compile(traces, effects, alpha=0.05, min_support=5, max_region=8)
registry.report()
print(registry.explain())
registry.save("artifacts/kb-v1")

# ── deploy: shadow first, always ──────────────────────────────────────────
from agents import Agent, Runner

agent = Agent(
    name="kb-assistant",
    model=cx.CompactingModel(
        "gpt-5",
        registry=registry,
        mode="shadow",          # -> "live" only after shadow coverage is measured
    ),
    tools=[...],
)
result = await Runner.run(agent, "How do I rotate the staging DB password?")
```

Two gaps, named rather than papered over with invented API. First, §5.2 exposes no keyword for declaring entry-state schema extensions, so all four pins — `kb.index_version_pin`, `kb.corpus_snapshot_pin`, `kb.embed_model_version_pin`, `kb.rerank_model_version_pin` — must be emitted into $z$ by the tracer as part of the Compaction Trace Profile; without them the guard cannot pin an index or a model version, the memo keys are not computable at lookup time, and the artifact must not be compiled. Second, there is no public accessor for per-artifact memoization statistics, so whether the per-tool `freshness_s` values are actually being honored — in particular `docs.fetch_metadata`'s 300 s, the binding one — is auditable only through the `compaction.execute` spans of §5.6, a monitoring gap for the exact field that carries the staleness risk.

**Savings.** Assumptions:

- $n_B = 11.5$ model requests/episode, from `cx.estimate` over 140 Train episodes.
- $k = 4$ — `MODEL_REQ` #1–#4. The synthesis request #5 is outside the region and is never removed.
- $\phi = 0.29$. Eq. (7) and Algorithm 7 line 5 make a dispatch conditional on **both** $H_a(z)$ and $q_a(z)\le\eta_a$, so three factors, not two: family support is $55/140 = 0.39$ of Train groups; the hard guard rejects a further ~12% of otherwise-eligible episodes (index, snapshot, or model-version pin mismatch during the nightly reindex window, group-list length outside the fitted hull, sessions with no pin); and the calibrated gate at $\eta=0.10$ admits ~85% of what survives the guard, measured on Dev. §4.6 caveat (ii) and H4 both say the gate costs coverage — H4 budgets up to 5 points — so crediting it as free is not available. $0.39 \times 0.88 \times 0.85 = 0.29$. Counted **once per episode** even though a two-question episode can dispatch twice; the second dispatch is not claimed.
- $\rho = 0.85$ — verifier pass rate, dominated by `len(md.docs) ≠ len(top)` when a document is deleted between retrieve and metadata fetch, and by an index rollover landing inside the region and tripping the in-program pin assert.

Eq. (10): $\phi\rho k = 0.29 \times 0.85 \times 4 = 0.99$, against $\Delta \cdot n_B$, giving

$$\Delta = \frac{0.99}{11.5} = 0.086$$

an **8.6% reduction in model requests per episode**. Plan against 8%. Dropping the gate factor gives the guard-only ceiling, $0.34 \times 0.85 \times 4 / 11.5 = 10.1\%$ — a ceiling, reported as such and not as the expected value. Eq. (11) with $\mu \approx 0.50$ — the retrieval and rerank tiers are a real share of wall time — gives $\Lambda \approx 1 - 0.50 \times 0.086 = 0.957$ on **mean** wall time, and that is before Eq. (11)'s $+(\bar b\,t_g + \phi\,t_x)/\mathbb{E}[T_B]$ overhead term, which is dropped here and biases the figure optimistic. p50 latency is reported separately under H3b rather than read off Eq. (11); the widen branch adds a second `search.retrieve` on 12 of 55 groups, which fattens the right tail without moving the median.

What makes it worse. Prompt caching (§3.4): boundaries #2–#4 have nearly identical prefixes, so their marginal input cost is far below the episode-average $c_m$ and dollar savings will land nearer 4–5% than 8.6%. If the reindex cadence drops below the 300 s region reuse bound, memoization stops paying and $\rho$ falls as well. Every widen-then-abstain dispatch still costs two `search.retrieve` calls; because it passes the verifier, that cost lands in the $\phi c_x$ execute+verify term of Eq. (8), not in $\phi(1-\rho)c_w$ — it is a successful dispatch whose useful output happens to be an abstention, and $\phi(1-\rho)c_w$ is reserved for wasted attempts that fall back to `BASELINE`. And if the harness echoes the raw 1536-float vector into model-visible history, the removed boundaries are unusually large-input requests and dollar savings would exceed request savings — but that profile is not recommended, and it is not what the arithmetic above assumes.

**What is rejected, and why.**

- **Reuse across principals with different group sets.** `key: [principal_group_set, …]` on `search.retrieve` makes the joined group string part of cache identity. §7.4's memory-enabled row states cross-user reuse rejects compaction outright, and §7.3 precondition 5 requires call-specific capability evidence. A similarity-keyed cache is not a weaker version of this mechanism; it is the failure mode it exists to prevent.
- **Any stale `index_version` or `corpus_snapshot`.** Both pins are in the `search.retrieve` memo key and are asserted against the live response on every path through the program, including the widen and abstain paths. A mismatch is a `PreCommitError`, so Algorithm 7 line 9 aborts the stage and returns `BASELINE`. Nothing is served from an index version other than the one the session pinned. The residual exposure is bounded and stated rather than denied: because the memo key is built from the entry-state pin and not from the live backend index, a session pinned immediately before a reindex can reuse memoized pre-rollover hits for up to the region reuse bound of 300 s, after which the entry expires and the live assert fires. That is bounded minutes, not the hours a similarity cache gives you, and shortening `freshness_s` below the reindex-detection lag is the mitigation. The runtime never attempts to "refresh and continue".
- **The answer synthesis request.** The answer text first appears in a `MODEL_RESP`, is not constant across supporting traces, and is not in $\mathcal{T}^{\le 2}$ of any observation, so Eq. (4) fails and Algorithm 3 line 9 returns $\bot$ ($VS=\varnothing$). Compiling it would be the general semantic-equivalence claim that §7.2 places out of scope. The region ends at `docs.fetch_metadata` by construction, not by accident.
- **`docs.fetch_body`.** Declared `WRITE_IRREVERSIBLE` because each call appends an immutable per-principal access-audit row. Any window containing it fails Eq. (5)'s effect condition at Algorithm 2 line 8. This is the §5.3 point that read-only and idempotent are not capabilities.
- **`docs.request_access`, and widening `acl_scope`.** `WRITE_IRREVERSIBLE` with `capabilities: []`, rejected by Eq. (5) at Algorithm 2 line 8. The widen branch widens $k$ from 24 to 72 and nothing else; broadening the ACL scope would be a permission decision, and §7.4's enterprise row makes credential scope a hard boundary. Empty retrieval under a principal's authorized scope means abstain, not escalate.
- **Model-authored query rewriting.** UNGROUNDED at Algorithm 1 line 9, dropped at Algorithm 2 line 10. It is a genuine decision, it costs 22% of otherwise-eligible windows, and that cost is correct.

**Adoption caveats.** The compiler slice (**v0.2**) produces the artifact and the readable program, but this use case's value is entirely in the guard, and the guard is only enforced by Algorithms 6–7 — so **v0.3 (shadow)** is the minimum useful deployment and **v0.4 (live)** is required to bank the 8.6%. Run **v0.1** first regardless: `cx.estimate` reports the rewritten-query block rate, and that single number decides whether the rest is worth building.

Fails closed on: an unpinned session, an `index_version`, `corpus_snapshot`, `embed_model_version`, or `rerank_model_version` mismatch, TTL expiry past the region reuse bound, a group list outside the fitted length hull, a newly added tool such as `search.retrieve_hybrid` that is absent from the catalog and therefore `UNKNOWN`, a registry miss, $q_a(z) > \eta_a$, or an `assert` failure. Every one of these returns `BASELINE` and re-issues the four requests.

One deployment precondition that is easy to miss: §4.7's `stage.reversible()` attestation includes quota and rate-limit counters. `search.embed` and `search.retrieve` are metered, so an abort after retrieve is only reversible if the retrieval tier carries a speculative-read allowance that leaves the user-visible counter equal at entry and abort. Without it, a post-retrieve `assert` failure is an `INCIDENT` under Algorithm 7 line 13, not a fallback, and the correct response is to stay in `mode="shadow"`.

The single biggest thing that could make this use case not work: **query rewriting.** Most production RAG assistants do HyDE, multi-query expansion, or step-back prompting, and every one of those makes `search.embed.text` a model decision. If the rewrite rate is high rather than the 22% measured here, there is no compilable region at all — only the retrieve → rerank → metadata tail, which needs the embedding vector as a live-in it does not have, and which is worth $k=3$ at a coverage that will not clear Eq. (10). Measure the rewrite rate at v0.1 before committing to anything downstream. Separately, if the assistant streams the final answer, §5.6 conformance test 7 requires reject-not-degrade and `CompactingModel` is non-streaming through v0.4, so the whole agent is out of scope until **v0.5+** even though the streamed request itself sits outside the region.

---

## Use case 3 — Refund approval with a human in the loop

**Setting.** A support agent handles refund tickets for a single EU retail tenant: roughly 3,000 tickets per week, each arriving with a ticket record that already carries an order reference. The agent reads the order, the captured payment, and the returned items, reads the regional refund policy, computes what is owed, assembles an evidence packet, and requests a human supervisor's approval; only after the approval resolves does it issue the refund and reply. On 1,240 captured tickets the mean is $n_B = 12.4$ model requests per resolved episode, and the four evidence-gathering requests are the expensive part — each carries the full order and returns payload into a fresh completion, and none of them decides anything.

**Why it qualifies.** The mined region $W$ is the four evidence reads and their results, terminating strictly before `approvals.request`.

*Eq. (4), live-in groundability.* Four argument slots, all grounded: `orders.get(order_id)` from the entry state (`z.ticket.order_ref`, identity); `payments.get_transaction(order_id)` from the in-region observation `ord.order_id` (identity, nearest producer by Algorithm 1 line 11); `returns.list_items(order_id)` also by identity, but here line 11's $\arg\min_S (i-j)$ attaches to the *nearer* `txn.order_id` echoed by the payments result, and it is Algorithm 3 line 10 that selects `ord.order_id` as the family-wide binding — both candidates are `id` over a path of equal length, so MDL and $|\sigma|$ tie and `lex(σ)` decides; `policy.get_refund_rules(region)` from `ord.region` under the depth-1 transform `lower`. No slot in $W$ takes a value that first appears in a model response. Live-ins are $\{z.\texttt{tenant},\ z.\texttt{principal.role},\ z.\texttt{ticket.order\_ref}\}$, all present in the entry-state schema, so Algorithm 2 line 11 passes.

*Eq. (5), boundaries and effects.* Boundaries `MODEL_REQ #2, #3, #4` fall strictly inside $W$ ($\ge 2$, satisfied with one to spare; in the minority of traces where the agent emits `orders.get` and `payments.get_transaction` in one assistant turn there are still two interior boundaries). Effects are three `READ_EXTERNAL` and one `READ_LOCAL`, every one declared `speculatable ∧ replayable`. No `WRITE_*` appears anywhere in $W$.

The approval barrier is what ends the region, and the rule is absolute. **The approval is never compiled, never elided, never inferred from a prior identical case, and no previous approval on any packet — including a byte-identical one for the same customer and the same SKUs — licenses a bypass.** `approvals.request` is a `WRITE_IRREVERSIBLE` effect with an empty capability set; it pages a human and writes an immutable audit record. The artifact stops one event short of it and hands the model a record. The model still authors the justification, still decides whether to escalate, and still issues the call. Because everything in $W$ is read-only and pre-commit, the deoptimization paths are cheap and distinct, and they are three different lines of Algorithm 7: a hard-guard or hull miss returns `BASELINE` at lines 2–3, before `Staging.begin`, so there is no stage to abort; an assert failure inside the interpreter raises `PreCommitError` and aborts the stage at line 9; a verifier failure is caught at line 11 and returns `BASELINE` at line 12 provided `stage.reversible()` holds. In each case the world, the history, the budget, and the audit log are identical to the entry snapshot. The condition on that last path is stated below rather than assumed.

**Trace fragment.**

```text
MODEL_REQ #1  → MODEL_RESP: call orders.get(order_id="ORD-48127")
TOOL_RESULT   → { order_id:"ORD-48127", tenant:"eu-retail", customer_id:"CUS-3391",
                  region:"EU-WEST", currency:"EUR", status:"delivered",
                  placed_at:"2026-06-14T09:22:11Z", delivered_at:"2026-06-18T14:05:00Z",
                  age_days:34, total_gross:173.64, shipping_gross:6.90,
                  lines:[ {sku:"SKU-7741", qty:1, price_gross:89.00},
                          {sku:"SKU-2210", qty:1, price_gross:42.75},
                          {sku:"SKU-9004", qty:1, price_gross:34.99} ] }
MODEL_REQ #2  → MODEL_RESP: call payments.get_transaction(order_id="ORD-48127")
TOOL_RESULT   → { txn_id:"txn_5c81d", order_id:"ORD-48127", method:"card",
                  captured:true, amount:173.64, currency:"EUR",
                  captured_at:"2026-06-14T09:22:19Z" }
MODEL_REQ #3  → MODEL_RESP: call returns.list_items(order_id="ORD-48127")
TOOL_RESULT   → { order_id:"ORD-48127", items:[
                    {sku:"SKU-7741", price_gross:89.00, condition:"unopened",
                     received_at:"2026-07-16"},
                    {sku:"SKU-2210", price_gross:42.75, condition:"unopened",
                     received_at:"2026-07-16"},
                    {sku:"SKU-9004", price_gross:34.99, condition:"damaged_by_customer",
                     received_at:"2026-07-16"} ] }
MODEL_REQ #4  → MODEL_RESP: call policy.get_refund_rules(region="eu-west")
TOOL_RESULT   → { policy_version:"eu-2026.03", window_days:30, restocking_fee_pct:0,
                  requires_approval_above:50.00, exception_allowed:true,
                  refundable_conditions:["unopened"] }
──────────────── region ends here.  everything below is the barrier ────────────────
MODEL_REQ #5  → MODEL_RESP: call approvals.request(packet={
                    order_id:"ORD-48127", txn_id:"txn_5c81d", currency:"EUR",
                    refund_amount:131.75, packet_kind:"exception",
                    placed_on:"2026-06-14", age_days:34, window_days:30,
                    policy_version:"eu-2026.03",
                    eligible_skus:["SKU-7741","SKU-2210"],
                    justification:"Order placed 2026-06-14, 34 days ago, 4 days past
                                   the 30-day window. Two of three returned items are
                                   unopened; customer cites a delayed carrier pickup." })
TOOL_RESULT   → { approval_id:"apr_2e77", state:"pending", approver_scope:"eu-supervisor" }
```

**What Algorithm 1 recovers.** `order_id="ORD-48127"` at `MODEL_REQ #2` has two producers in the index — the ticket record in $x_0$ and `orders.get → order_id` — so $|S|=2 \le \kappa$ and line 11's nearest-producer rule attaches the edge to `orders.get`. At `MODEL_REQ #3` there are three producers and the same rule attaches to the nearest, `payments.get_transaction → order_id`; unifying that with `ord.order_id` across the family is Algorithm 3's tie-break, not Algorithm 1's. `region="eu-west"` is an exact-match miss; `TransformSearch` finds the non-identity depth-1 expression `lower` over `orders.get → region`. `age_days:34` in the packet is an identity edge from `orders.get → age_days`, and this edge is load-bearing: $\mathcal{T}$ contains `date_fmt` but no clock and no date subtraction, so if the order service did not return a server-computed age the branch of Algorithm 4 below would be inexpressible and the family would be rejected. `placed_on:"2026-06-14"` recovers `date_fmt("%Y-%m-%d")` over `placed_at`. Groundability does real work here: `restocking_fee_pct:0` and `captured:true` are never indexed (line 5), so they manufacture no edges.

Two slots are correctly not resolved, both in `approvals.request`. `packet.justification` is free text authored by the model; no producer matches and no transform reaches it, so it is marked UNGROUNDED (line 9). `packet.order_id` has four producers — the entry-state ticket plus the `order_id` echoed by all three read tools — so $|S| = 4 > \kappa = 3$ and it is marked AMBIGUOUS (line 10). The consequence is that any candidate window extended by one event to swallow the barrier is discarded at Algorithm 2 line 10, independently of the effect check at line 8. The barrier is thus excluded twice over, by provenance and by effect.

`packet.refund_amount = 131.75` is the interesting one. It is an exact-match miss and it is not reachable at the default depth $d=2$: the true expression is

```text
ret.items |> filter(condition == "unopened") |> project(price_gross) |> sum |> round(2)
```

which is depth 4 over the closed library. Algorithm 1 therefore leaves this slot UNGROUNDED and counts it in `diag`. Because the slot lies *outside* the mined window, it does not veto the region (Algorithm 2 line 10 inspects only `Slots(W)`), and the region is mined on the strength of the other edges. It is worth being exact about what registers `ret.items` as a live-out, because the obvious answer is wrong: `eligible_skus` is list-valued, and `groundable(v,\Theta)` admits strings, ints, floats, uuids and iso dates but no collection type, so the slot itself is skipped at Algorithm 1 line 5 — the same predicate that just excluded `restocking_fee_pct` and `captured`. Under flatten-to-leaves what the index actually manufactures is per-element identity edges (`eligible_skus[0]` from `ret.items[0].sku`), which are positional and unstable in exactly the way §5.7 warns about with `[0].password`. Those edges are enough to register `ret.items` as a live-out; they are not a binding, and Algorithm 3 line 7 discards them as soon as a supporting trace returns the items in another order. The stable `filter ∘ project` form is Algorithm 3's product, not Algorithm 1's.

Recovering the amount is then Algorithm 3's job, run against the recorded post-region argument value as ground truth, at depth 4 rather than the stated default. That is a search-budget change, not a library change: every operator is one of the 22, and Eq. (4) is written over $\mathcal{T}^{\le d}$ for general $d$. The type check at Algorithm 3 line 6 is what makes it affordable. Unpruned, depth 4 costs $\lvert\Pi\rvert\cdot 22^4\cdot k \approx 50 \times 234{,}256 \times 25 \approx 2.9\times10^{8}$ typed evaluations, which at §4.3's rate of ~600k evaluations per second is ~500 s per slot. Stage-wise typing collapses that: from `list[record]` only `filter/project/sort/topk/first/last/len` type-check at stage 1, from `list[num]` only `sum/len/first/last` at stage 3, and constants come only from observed literals — roughly $1.2\times10^{4}$ typed expressions per list-typed source, so with two list-typed sources in $\Pi$ and $k=25$ supporting traces about $6\times10^{5}$ evaluations, ≈ 1 s per slot. Depth 4 therefore lands *at* the ~1 s/slot budget of §4.8, not above it; the cost is enumeration discipline, not wall clock. The alternative route is a two-pass binder, and it needs stating precisely: the printed program's intermediate `elig` is depth 1 and stays a `list[record]` because `eligible_skus` also consumes it, so the residual `project |> sum |> round(2)` is depth 3, and the two-pass route needs $d = 3$ rather than the default 2. Neither route is the default; both stay inside the closed library.

**Algorithm 4** fires on a real divergence: 31 of 47 supporting groups produce `packet_kind:"standard"`, 16 produce `"exception"`. The atom `(ord.age_days, >, 30)` — with $30$ drawn from the observed literal `window_days` — separates the supporting traces with purity 1 at $\varepsilon = 0$ and survives leave-one-group-out, so the decision list has length 1. Note precisely what is *not* expressible: `Atoms` in Algorithm 4 line 2 are `(path, op, const)`, so `age_days > window_days` — a comparison between two observations — is outside the grammar. The synthesized predicate hard-codes 30, and the program therefore asserts `pol.window_days == 30`; a tenant or policy version with a different window fails the assert and deoptimizes to baseline. Likewise the packet cannot carry `days_past_window`, since `add(-30)` is unavailable when constants are restricted to observed literals plus $\{0,1,-1,\texttt{""}\}$; the artifact carries `age_days` and `window_days` verbatim and lets the human approver subtract.

**Effect catalog.**

```yaml
# effects/refund.yaml — anything not listed is UNKNOWN and is never compiled
version: 1
tools:
  orders.get:
    effect: READ_EXTERNAL
    capabilities: [speculatable, replayable, reorderable]
    key: [tenant, order_id]
    freshness_s: 60
    notes: not cacheable — status and age_days are time-varying and a refund must
           not be assembled from a stale order record. Not batchable — the only
           declared signature takes a single order_id; there is no get_many form,
           so fusion is a licence the compiler could not legally exercise

  payments.get_transaction:
    effect: READ_EXTERNAL
    capabilities: [speculatable, replayable, reorderable]
    key: [tenant, order_id]
    freshness_s: 30
    notes: not cacheable — a capture can be voided or partially settled between reads

  returns.list_items:
    effect: READ_EXTERNAL
    capabilities: [speculatable, replayable, reorderable]
    key: [tenant, order_id]
    freshness_s: 60
    notes: warehouse may receive additional items mid-ticket; short freshness bound

  policy.get_refund_rules:
    effect: READ_LOCAL
    capabilities: [speculatable, replayable, cacheable, reorderable]
    key: [tenant, region]
    freshness_s: 900
    notes: the memo key contains only values known before the call. policy_version
           is an output, not a key component; it is stored with the cached entry as
           a validity token and a change invalidates it. Keying on it would key the
           memo on the version being replaced

  approvals.request:
    effect: WRITE_IRREVERSIBLE
    capabilities: []
    key: [tenant, order_id, approver_scope]
    notes: the barrier. Pages a human and writes an immutable audit record. Never
           compiled, never cached, never elided, never reordered. The empty
           capability list is what makes that structural, and §7.4 forbids ever
           granting one; a prior approval on an identical packet licenses nothing.

  refunds.issue:
    effect: WRITE_IRREVERSIBLE
    capabilities: []
    key: [tenant, order_id, idempotency_key]
    notes: moves money. The idempotency key prevents duplicates, not reversal.
           Excluded from every region by Eq. (5).
```

No tool in this catalog declares `cacheable` except the local policy read, and none declares `elidable`. Nothing here may be skipped — only executed inside an artifact, or left to the baseline.

**Synthesized artifact.**

```text
artifact  refund.approval_evidence@1   support 47/120 groups   removes k=4
──────────────────────────────────────────────────────────────────────────────
guard   model=gpt-5-2026-04-12  prompt=#b3d7  tools=#4e19  policy=#eu2603
        z.tenant           : str = "eu-retail"
        z.principal.role   : str ∈ {support_agent}
        z.ticket.order_ref : str  matches ^ORD-[0-9]{5}$
        effects ⊆ {READ_LOCAL, READ_EXTERNAL}  all speculatable ∧ replayable

program (θ = {tenant, order_ref}):
   ord  = call orders.get(order_id = θ.order_ref)
   txn  = call payments.get_transaction(order_id = ord.order_id)
   ret  = call returns.list_items(order_id = ord.order_id)
   pol  = call policy.get_refund_rules(region = ord.region |> lower)     ← Alg.3
   elig = ret.items |> filter(condition == "unopened")                   ← Alg.3
   amt  = elig |> project(price_gross) |> sum |> round(2)                ← Alg.3
   day  = ord.placed_at |> date_fmt("%Y-%m-%d")                          ← Alg.3
   if ord.age_days > 30:  kind = "exception"                             ← Alg.4
   else:                  kind = "standard"
   assert  pol.policy_version == "eu-2026.03"
           and pol.refundable_conditions == ["unopened"]
           and pol.window_days == 30  and  pol.restocking_fee_pct == 0
           and txn.captured == true  and  txn.currency == ord.currency
           and 0 < amt  and  amt ≤ txn.amount
   return  { order_id: ord.order_id, txn_id: txn.txn_id,
             currency: ord.currency, refund_amount: amt, placed_on: day,
             age_days: ord.age_days, window_days: pol.window_days,
             packet_kind: kind, policy_version: pol.policy_version,
             eligible_skus: elig |> project(sku) }

verify  refund_amount : float, non-null, 0 < x ≤ txn.amount,
        provenance ∈ {returns.list_items}
        packet_kind : str ∈ {standard, exception}
        eligible_skus : list, len ≤ len(ret.items),
        provenance ∈ {returns.list_items}
        policy_version : str = "eu-2026.03"
        effect_multiset ⊆ {READ_LOCAL, READ_EXTERNAL};  no WRITE_* observed
gate    q = GBM(entry features)   η = 0.08   (Dev, α=0.05, δ=0.10, |Λ|=11)
```

The `assert` line is the safety spine, and the two policy pins are the load-bearing part of it. `filter(condition == "unopened")` is faithful to policy `eu-2026.03` only because that policy's `refundable_conditions` is exactly `["unopened"]` — and nothing in the entry state can establish that. The hard guard is evaluated on $z$ before dispatch (Algorithm 7 line 2), and the manifest's `policy=#eu2603` pins the policy *configuration recorded at entry*; the policy *body* arrives inside the region, from `policy.get_refund_rules`. A revision that replaces the single condition with `"opened_unused"` while leaving `window_days` at 30 and `restocking_fee_pct` at 0 would pass a mere cardinality check and every verifier clause, and the artifact would return a wrong `refund_amount` and a wrong `eligible_skus` — precisely the silent wrongness Algorithm 5 line 17 calls fatal. So the assert pins the version and the content verbatim: an in-region policy revision raises `PreCommitError` and aborts at Algorithm 7 line 9. An unseen `condition` value inside an otherwise matching episode violates the enum hull fitted on Train by Algorithm 5 lines 2–4 and lands on the guard path instead. The artifact returns machine-checkable evidence and nothing else: it does not draft the justification, and it does not decide that an approval is warranted.

**Integration.**

```python
import compaction as cx

# ── capture ───────────────────────────────────────────────────────────────
cx.enable_tracing(backend="mlflow", experiment="refund-eu-retail")

# ── estimate before building anything ─────────────────────────────────────
traces  = cx.load(backend="mlflow", experiment="refund-eu-retail", split="train")
effects = cx.EffectCatalog.from_yaml("effects/refund.yaml")

print(cx.estimate(traces, effects))
#  n_B  = 12.4 model requests/episode
#  ceiling: phi=0.41  k=3.6  ->  max request reduction 11.9%   [Eq. 10]
#  blocked: 39% of windows by WRITE_IRREVERSIBLE (approvals.request, refunds.issue)
#           14% by UNGROUNDED slots (approvals.request.packet.justification)
#            9% by AMBIGUOUS slots (packet.order_id: 4 producers > kappa=3)

# ── compile ───────────────────────────────────────────────────────────────
registry = cx.compile(traces, effects, alpha=0.05, min_support=5, max_region=8)
registry.report()          # 1 artifact, 47/120 groups, 3 rejection classes
print(registry.explain())  # the block above
registry.save("artifacts/refund-v1")

# ── deploy: shadow first, one tenant ──────────────────────────────────────
from agents import Agent, Runner

agent = Agent(
    name="refund-support",
    model=cx.CompactingModel(
        "gpt-5",
        registry=cx.Registry.load("artifacts/refund-v1"),
        mode="shadow",          # "live" only after Gate C freezes the threshold
    ),
    tools=[orders_get, payments_get_transaction, returns_list_items,
           policy_get_refund_rules, approvals_request, refunds_issue],
)
result = await Runner.run(agent, "TCK-90412: refund order ORD-48127")
```

A ticket worker not built on the Agents SDK uses the decorator form at its own step boundary:

```python
@cx.compact(registry=cx.Registry.load("artifacts/refund-v1"))
def refund_step(entry_state: dict) -> cx.Decision:
    ...   # Decision.BASELINE, or a compacted history extension
```

**Savings.** Assumptions, all from the Train/Dev corpus and all conservative:

- $n_B = 12.4$ model requests per resolved refund episode (measured, 1,240 tickets).
- $k = 3.7$: the canonical shape removes 4 requests, but in about 30% of supporting groups the agent already fuses two reads into one assistant turn and only 3 are removed, so the support-weighted mean is $0.7\times4 + 0.3\times3 = 3.7$.
- $\phi = 0.38$: 47 of 120 Train groups support the family; after Algorithm 6 trims coverage at $\eta = 0.08$, measured Dev coverage is 0.38, below the 0.41 pre-gate estimate.
- $\rho = 0.90$: the fraction of dispatches that reach a *passing verifier* — neither aborted by an in-program assert (`pol.policy_version`, `pol.window_days == 30`, `amt ≤ txn.amount`) at Algorithm 7 line 9, nor rejected by $V$ at line 11. These are two different mechanisms on two different lines and the two rates are reported separately; 0.90 is their product and the assert term dominates it.

Eq. (10): $\phi\rho k = 0.38 \times 0.90 \times 3.7 = 1.27$, against the requirement $\Delta \cdot n_B$. Solving for $\Delta$:

$$\Delta = \frac{1.27}{12.4} = 0.102$$

**10.2% fewer model requests per episode**, from one artifact — just over the $\Delta = 0.10$ endpoint of §3.4, and inside the 5–15% band. The margin is too thin to treat as a pass: H3 is an *upper* one-sided 95% CI on the request ratio, and a point estimate of 0.898 does not deliver one. The Eq. (9) overhead terms are small and are charged anyway: $\bar b\,c_g \approx 12.4 \times 1$ ms of gate evaluation, $\phi\,c_x \approx 0.38 \times 20$ ms of interpretation and verification. The wasted-attempt rate is $\phi(1-\rho) = 0.38 \times 0.10 = 0.038$ wasted attempts per episode, and $c_w$ is unusually small here because a wasted attempt burns four external reads — eight once the baseline re-runs and re-issues the same non-cacheable reads — and zero model tokens, a direct consequence of the region being read-only and pre-commit.

Two honest deductions. Dollars will lag: the four removed requests share a long cached prefix, so their marginal cost is well below $c_m$; report the $c^{\text{in}}_{\text{cold}} / c^{\text{in}}_{\text{cached}} / c^{\text{out}}$ decomposition from §3.4 rather than quoting 10.2% as a cost figure. Latency tracks better — at $\mu \approx 0.55$, Eq. (11) gives $\Lambda \approx 1 - 0.55 \times 1.27/12.4 \approx 0.94$, about 6% on p50, dropping the $(\bar b\,t_g + \phi\,t_x)/\mathbb{E}[T_B]$ term, which at these overheads is on the order of a tenth of a percent and moves the figure the wrong way.

What would make it worse: a multi-region tenant, which splits the family because `window_days` enters the branch as a hard-coded constant; tax-exclusive pricing, promotional line allocations, or partial shipping refunds, any of which break `sum ∘ round(2)` over `price_gross` and cause Algorithm 3 to return $\bot$; returns that arrive in batches, so `returns.list_items` changes between the artifact's read and the approver's review; and tickets with no order reference in the entry state, where the agent must search first — those miss the guard and run baseline, reducing $\phi$ without adding risk.

**What is rejected, and why.**

- **`approvals.request` itself.** `WRITE_IRREVERSIBLE` with an empty capability list, so any window containing it fails the effect condition of Eq. (5) at Algorithm 2 line 8. It is rejected two more times independently: `packet.justification` is UNGROUNDED and `packet.order_id` is AMBIGUOUS ($|S| = 4 > \kappa$), so Algorithm 2 line 10 drops the window on provenance alone. Even with a perfect effect catalog, the provenance layer refuses it; even with perfect provenance, the effect layer refuses it.
- **`refunds.issue`.** `WRITE_IRREVERSIBLE`, and §7.2 puts any state mutation out of scope for the scored condition. The idempotency key is not a reversal mechanism. If a verifier failure ever occurred after such a call, Algorithm 7 lines 11 and 13 would classify it as `INCIDENT`, not fallback — the runtime does not pretend to unwind a payment.
- **Caching or reusing an approval decision.** `approvals.request` declares neither `cacheable` nor `replayable` nor `elidable`, so memoization, pre-commit execution, and elision are all unlicensed by §5.3's capability semantics — its capability list is empty and §7.4 forbids populating it. §7.4's human-in-the-loop row states the boundary directly: the approval is an immutable barrier and prior approval never licenses bypass. Keying a memo on `[tenant, order_id, approver_scope]` would still be wrong, because reuse across principals or ACL scopes is forbidden outright; the key exists to make cross-scope collision impossible, not to enable reuse.
- **The auto-refund shortcut.** The decision list `amt ≤ pol.requires_approval_above → issue directly, else request approval` is perfectly synthesizable — `requires_approval_above: 50.00` is an observed literal, the atom is in Algorithm 4's grammar, and it would separate the supporting traces. It is refused anyway. Algorithm 4 finding a predicate does not make a decision compilable; the target of that branch is `refunds.issue`, which is outside $\mathcal{E}_{\text{allowed}}$, and compiling the choice of whether a human is consulted is precisely the thing §7.4 forbids. This is the sharpest case in the proposal where synthesis succeeds and policy overrides it.
- **Extending the region past the barrier to include the approval result.** The approval resolution is a human decision with no provenance in any observation; Algorithm 3 returns $\bot$ at line 9 (empty version space) and the family dies there.
- **A `days_past_window` convenience field.** Not a safety rejection, an expressiveness one: `add(-30)` is unavailable because constants are drawn only from observed literals plus $\{0,1,-1,\texttt{""}\}$, and depth-3 arithmetic gymnastics to reach it would not survive MDL selection at Algorithm 3 line 10.

**Adoption caveats.** The estimator slice **v0.1** answers the only question worth asking first — whether refund tickets recur in shape at all, and how much of the window space the two `WRITE_IRREVERSIBLE` tools already remove. The artifact above requires **v0.2** (Algorithms 3–5, interpreter, `explain()`, registry). Measured coverage on live traffic requires **v0.3** in `mode="shadow"`; actual savings require **v0.4**. If the approver interaction is modelled as a handoff to a supervisor agent, or if replies stream, this use case is **v0.5+** and today fails closed under conformance test 7 rather than degrading.

What fails closed, and where. An undeclared tool is `UNKNOWN` and is never compiled, so it never reaches dispatch at all. A change to the pinned policy configuration in the entry state, or an unseen `condition` value violating the Train-fitted enum hull of Algorithm 5 lines 2–4, misses the hard guard and returns `BASELINE` at Algorithm 7 lines 2–3 — before `Staging.begin`, so there is nothing to abort. An in-region policy revision — a new `policy_version`, a changed `refundable_conditions`, a tenant whose `window_days` is not 30 — trips an assert inside the interpreter, raises `PreCommitError`, and aborts the stage at line 9. A live-out that fails $V$ is caught at line 11 and returns `BASELINE` at line 12. In every case the environment, the model-visible history, the interaction budget, and the audit counters are bit-identical to the entry snapshot, because the region has not written anything.

That last path is conditional and the condition deserves naming rather than burying. `stage.reversible()` in §4.7 attests over quota, billing, and audit counters as well as world state, and §5.3 warns explicitly that a nominal read can still burn quota, create audit state, or observe time-varying data. Three of the four in-region calls are `READ_EXTERNAL` against order, payment, and warehouse providers. The incident branch at line 13 is therefore unreachable *provided* those four reads move no metered counter that the attestation covers — a property that must be attested per provider, not assumed. Where a provider does meter reads, `stage.reversible()` returns false and a verifier failure is classified `INCIDENT`, not fallback. Subject to that check, this is among the safest shapes available for a first pilot — §7.2 puts production safety certification out of scope, so this is an engineering judgement and not a certified one. The worst realistic outcome is four wasted read calls and a baseline episode, and the human approver remains the unconditional gate on every euro that moves. A pilot that starts on a write region has to trust the staging attestation for *reversal*; this one needs it only for *metering*, which is a narrower claim and a checkable one.

Two gaps in the §5.2 surface, stated rather than papered over. First, the binder's depth budget is not settable: `cx.compile(traces, effects, alpha=, min_support=, max_region=)` exposes no depth keyword, and the refund-amount binding needs $d = 4$ single-pass, or $d = 3$ against the shared depth-1 `elig` intermediate. Without a knob, this artifact cannot be produced through the public API as written. Second, there is no tenant or principal partition argument. The only levers are the effect catalog's `key:` list and the guard hull fitted over `z.tenant`, which means a mixed-tenant corpus must be loaded and compiled per tenant under separate `experiment` names — a discipline the API does not enforce and should.

The single biggest thing that could make this use case not work in practice is not safety, it is prompt engineering. If the baseline agent is instructed to gather evidence in one assistant turn — four `function_call` items in a single response — then $\lvert B_\tau \cap \mathrm{interior}(W)\rvert < 2$, Eq. (5) fails at Algorithm 2 line 7, and there is nothing to remove. The savings here are entirely a function of how chatty the baseline is, and a competent prompt revision can erase them before the compiler runs. Measure $n_B$ and the interior-boundary distribution first; if the reads are already fused, close the file.

---

## Use case 4 — Multi-agent triage with handoffs

**Setting.** A `support-manager` agent owns the first turns of an inbound support conversation and holds three SDK handoffs — `billing_specialist`, `technical_specialist`, `account_mgmt_specialist` — plus a deliberately small read surface used only for triage: `crm.get_customer_tier(customer_id)`, `tickets.list_open(customer_id)`, and `tickets.get_category_hints(text)`. Traffic is high-volume and highly repetitive at the front: every conversation begins with the same three reads and ends the manager's involvement with one handoff, after which the specialist does the actual work. `cx.estimate` on 60 Train scenario groups reports $n_B = 14.2$ model requests per episode, decomposed as 3.1 in the manager's triage prefix and 11.1 after the handoff. The prefix is expensive relative to its information content: three full model round-trips to compute a routing label that is, on most traffic, a function of two observations.

This is the case where the compiled artifact is a **predicate, not a call sequence**. Algorithm 4 synthesizes a typed decision list over observations mapping to a specialist. Everything else in this document compiles a bundled sequence; here the sequence is incidental and the branch is the product.

**Why it qualifies.** The candidate region $W$ is the triage prefix: the read fan-out, the category-hint call, and the routing emission. It ends at the handoff and never crosses it.

*Eq. (4) — live-in groundability.* Live-ins are $\{$`customer_id`, `tenant`, `latest_message`$\}$, all present in the manager's entry state $z$ (conversation binding plus the inbound message). Every argument slot in $W$ is a constant or a bounded transform of $z$ or of an in-region observation:

- `crm.get_customer_tier.customer_id` $\leftarrow$ `id(z.customer_id)`. Ungrounded within event outputs — no prior event produced it — but present in the entry state, exactly the `username` case of §5.7, so Eq. (4) is satisfied via $\omega \in z$.
- `tickets.list_open.customer_id` $\leftarrow$ `id(z.customer_id)`, same source. Both calls are emitted before either result, so at Algorithm 1 line 6 the producer index holds no producer for `"C-88317"` and the slot resolves through $z$. This is a capture requirement, not an assumption: if the backend serialized the fan-out as call/result/call/result, the CRM result's echoed `customer_id` would exact-match at line 6 and line 12 would build a spurious `crm.get_customer_tier → tickets.list_open` data edge, which is an ordering constraint, contradicts `reorderable`, and changes `CanonHash` at Algorithm 2 line 12 — a different family from the one described.
- `tickets.get_category_hints.text` $\leftarrow$ `z.latest_message |> strip |> lower`, depth 2, synthesized by Algorithm 3.
- `transfer_to_*.ticket_id` $\leftarrow$ `open.tickets |> filter(status == "awaiting_agent") |> project(id)`, depth 2, recovered by `TransformSearch` at Algorithm 1 line 8.

The handoff *tool identity* is not an argument slot. It is the branch label, supplied by Algorithm 4's decision list over `tier.plan` and `hint.top_category` — both in-region observations produced by calls declared `speculatable ∧ replayable`, satisfying §7.3 precondition 2.

*Eq. (5) — boundaries and effects.* Three model-request boundaries fall strictly inside $W$: the read fan-out, the hint call, and the routing emission. That is $\ge 2$. Effect classes inside $W$ are three `READ_EXTERNAL` calls, all `speculatable ∧ replayable`, with `reorderable` on the two customer reads licensing the parallel fan-out. **The terminal handoff emission is `WRITE_IRREVERSIBLE` with no capabilities and is therefore not in $\mathcal{E}_{\text{allowed}}$.** As Algorithm 2 is specified, line 8 sees that call inside the window and rejects the family. Admitting it requires a rule for a *terminal ownership-transfer emission* — a call the artifact emits but never executes, constrained to be the last event in $W$ — which neither §5.3's effect enum nor Eq. (5) provides. This is gap **G1**, discussed under adoption caveats. Everything below describes the artifact under that rule; the shipped v0.4 form stops one boundary earlier at $k=2$.

**Trace fragment.**

```text
MODEL_REQ #1  agent=support-manager  tenant="acme-eu"
              z: { customer_id:"C-88317",
                   latest_message:"I was charged twice for the June invoice. " }
 → MODEL_RESP: two parallel calls, both emitted before either result
TOOL_CALL     crm.get_customer_tier(customer_id="C-88317")
TOOL_CALL     tickets.list_open(customer_id="C-88317")
TOOL_RESULT   { customer_id:"C-88317", plan:"enterprise", tier:"t3",
                csm:"m.okafor@acme.example", since:"2023-04-11" }
TOOL_RESULT   { tickets:[
                  { id:"TCK-40219", customer_id:"C-88317",
                    subject:"duplicate invoice june", status:"awaiting_agent",
                    updated_at:"2026-07-29T09:14:02Z" },
                  { id:"TCK-39880", customer_id:"C-88317",
                    subject:"sso login loop", status:"awaiting_customer",
                    updated_at:"2026-07-18T16:02:55Z" } ] }
MODEL_REQ #2
 → MODEL_RESP: call tickets.get_category_hints(
                      text="i was charged twice for the june invoice.")
TOOL_RESULT   { top_category:"billing", classifier_version:"lex-v3",
                scores:{ billing:0.81, account:0.12, technical:0.07 } }
MODEL_REQ #3
 → MODEL_RESP: call transfer_to_account_mgmt_specialist(ticket_id="TCK-40219")
TOOL_RESULT   { assistant:"account-mgmt-specialist" }   ← ownership transfers here
MODEL_REQ #4  agent=account-mgmt-specialist   ← different manifest; no artifact resolves
```

Note that the hint says `billing` and the route is account management. The tier read is load-bearing, not decoration.

**What Algorithm 1 recovers.** `customer_id="C-88317"` in both reads is not produced by any event preceding either call; it is an entry-state path, and Eq. (4) is satisfied through $z$, not through a data edge. `text="i was charged twice for the june invoice."` exact-matches nothing in the producer index; it resolves at Algorithm 3 against the entry-state path `z.latest_message` under `strip |> lower`. The genuinely interesting data edge is the handoff argument: `ticket_id="TCK-40219"` exact-matches `tickets[0].id`, but that path is *positional* and unstable across customers with different open-ticket counts, so `TransformSearch` at depth 2 is what produces the stable expression `filter(status == "awaiting_agent") |> project(id)` — the same select-then-project shape §4.3 identifies as the dominant real pattern.

Two slot classes are correctly refused, and both have consequences that shrink the family:

- **UNGROUNDED.** In 11 of the 60 groups the manager emitted `transfer_to_technical_specialist(ticket_id=..., reason="customer reports SSO redirect loop after IdP change")`. The `reason` string first appears in a `MODEL_RESP`, is not constant across supporting traces, and is not in $\mathcal{T}^{\le 2}$ of any observation. Algorithm 1 line 9 marks the slot UNGROUNDED; Algorithm 2 line 10 drops every window containing it. Because `sig(e)` includes argument-path shape, these windows also form a distinct family — one that is rejected outright. This is correct: the reason is a real decision.
- **AMBIGUOUS.** In 5 groups `crm.get_customer_tier` returned 429 and the manager retried it after `tickets.list_open` had already landed with three open tickets (the fragment's customer has two). At the retried slot the value `"C-88317"` has four producers in the index — the three ticket records' `customer_id` fields plus the 429 error body's echoed request params — so $\lvert S\rvert = 4 > \kappa = 3$, the slot is marked AMBIGUOUS at Algorithm 1 line 10, and Algorithm 2 line 10 drops the window. Those episodes stay on baseline and remain in the corpus as negative evidence per §4.2.

The surviving family holds 41 of 60 groups. Its terminal call signature varies across members, so Algorithm 2 line 16 adds control edges from the covarying observations `tier.plan` and `hint.top_category` and hands the divergence to Algorithm 4.

That family is then **narrowed before branch synthesis**, and this is the most consequential decision in the section. Nine of the 41 members terminate in a bare `transfer_to_technical_specialist(ticket_id=...)`. A decision list covering them would emit a technical handoff at runtime on entry states that the hard guard cannot distinguish from the 11 `reason`-bearing ones — $H_a(z)$ sees only manifest hashes and hulls on $z$ (Algorithm 5 lines 1–4), and an SSO complaint clears the length band and the customer-id regex exactly as a duplicate-invoice complaint does. The result would be a handoff emitted with `reason` silently dropped, which `verify` cannot catch and which a calibrated risk score is not entitled to catch either (§5.1(2), Algorithm 5 line 17). So the technical arm is refused: the artifact is restricted to the 32 non-technical members, and all technical traffic abstains to baseline. The refusal is made hard rather than statistical by an in-program assert on `hint.top_category`, which is admissible only because every one of the 9 bare-technical and 11 `reason`-bearing groups carries `hint.top_category = "technical"`. That corpus check is a mining-time precondition; if it fails, the arm is not admissible and there is no artifact.

**Effect catalog.**

```yaml
# effects.yaml — anything not listed defaults to UNKNOWN and is never compiled
version: 1
tools:
  crm.get_customer_tier:
    effect: READ_EXTERNAL
    capabilities: [speculatable, replayable, cacheable, reorderable]
    key: [tenant, customer_id]
    freshness_s: 3600
    notes: plan changes are contract events, not intra-conversation events;
      1 h staleness is inside the routing SLA. key includes tenant so no
      artifact or cache entry is shared across tenants.

  tickets.list_open:
    effect: READ_EXTERNAL
    capabilities: [speculatable, replayable, reorderable]
    key: [tenant, customer_id]
    freshness_s: 120
    notes: no batchable. The signature is a single-customer read and each
      conversation concerns one customer, so the only thing fusion could do is
      merge calls across conversations — across principals and potentially
      across tenants, which §7.4 forbids outright. A genuine bulk endpoint
      would be declared as a separate tool with its own key.

  tickets.get_category_hints:
    effect: READ_EXTERNAL
    capabilities: [speculatable, replayable, cacheable]
    key: [tenant, classifier_pin, text_sha256]
    freshness_s: 86400
    notes: deterministic lexical classifier, version pinned. classifier_pin is
      the deployment-pinned version string from the manifest, not the
      classifier_version field of the response, which is not resolvable at
      cache-lookup time; the post-hoc assert on the response field is the drift
      check. key includes tenant so a 24 h cache entry is never shared across
      tenants. If this is ever replaced by a model-backed classifier, withdraw
      `replayable` and the whole region stops compiling.

  transfer_to_billing_specialist:
    effect: WRITE_IRREVERSIBLE
    capabilities: []
    key: [tenant, conversation_id]
    notes: ownership transfer. Never executed by the interpreter. Emitted as the
      terminal native item so the Runner performs a real SDK handoff, applies the
      input filter, and runs the specialist's guardrails. Admitting this emission
      into a region needs the terminal-emission rule (gap G1); until then any
      window containing it fails Eq. (5) at Algorithm 2 line 8.

  transfer_to_technical_specialist:
    effect: WRITE_IRREVERSIBLE
    capabilities: []
    key: [tenant, conversation_id]
    notes: as above, and never emitted by any artifact — technical routes
      abstain to baseline.

  transfer_to_account_mgmt_specialist:
    effect: WRITE_IRREVERSIBLE
    capabilities: []
    key: [tenant, conversation_id]
    notes: as above.

  crm.add_case_note:
    effect: WRITE_IRREVERSIBLE
    capabilities: []
    key: [tenant, customer_id]
    notes: deliberately uncompilable. The manager sometimes writes a triage note
      before handing off; the note text is a decision and the write creates audit
      state. Any window containing it is dropped at Algorithm 2 line 8.
```

**Synthesized artifact.**

```text
artifact  support.triage_route@1   support 32/60 groups   removes k=2  (k=3 under G1)
──────────────────────────────────────────────────────────────────────────────
guard   agent=support-manager  model=gpt-5-2026-04-12  prompt=#c40b
        tools=#19ae  handoffs=#5d71  policy=#3e55
        z.tenant         : str  ∈ {acme-eu, acme-us}
        z.customer_id    : str  matches ^C-[0-9]{5}$
        z.latest_message : str  len ∈ [12, 2048]
        executed effects ⊆ {READ_EXTERNAL}  all speculatable ∧ replayable
        terminal emission ∈ {transfer_to_billing_specialist,
                             transfer_to_account_mgmt_specialist}, exactly one
                            (requires gap G1; absent it, k=2 and no emission)

program (θ = {tenant, customer_id, latest_message}):
   tier = call crm.get_customer_tier(customer_id = θ.customer_id)
   open = call tickets.list_open(customer_id = θ.customer_id)   ← reorderable fan-out
   txt  = θ.latest_message |> strip |> lower                             ← Alg.3
   hint = call tickets.get_category_hints(text = txt)
   tid  = open.tickets |> filter(status == "awaiting_agent")
                       |> project(id)                                    ← Alg.1/3
   route = DecisionList (L = 2, ε = 0):                                  ← Alg.4
        if   tier.plan = "enterprise"                  -> account_mgmt_specialist
        elif hint.top_category ∈ {"billing","account"} -> billing_specialist
        else                                           -> ⊥ (abstain to baseline)
   assert  card(tid) = 1  and  tid matches ^TCK-[0-9]{5}$
           and  hint.classifier_version = "lex-v3"
           and  hint.top_category ∈ {"billing","account"}
           and  len(open.tickets) > 0
   return  { handoff: route, ticket_id: tid }

verify  handoff : str, non-null, card = 1,
                  ∈ {transfer_to_billing_specialist,
                     transfer_to_account_mgmt_specialist}
        ticket_id : str, non-null, card = 1, provenance ∈ {tickets.list_open}
        effect_multiset(run) = { crm.get_customer_tier, tickets.list_open,
                                 tickets.get_category_hints }   no write executed
gate    q = GBM(entry features)   η = 0.10   (Dev, α=0.05, δ=0.10, |Λ|=11)
```

Three details in that block are load-bearing. The two atoms come only from `Ops(str) = {=, ≠, ∈, prefix, empty}`; the constant set in the second rule is drawn from observed values of that path, per Algorithm 4 line 4. The `else -> ⊥` arm is explicit because `hint.top_category` is an in-region observation, not a live-in, so Algorithm 5 line 2 cannot fit an enum hull on it in the hard guard; a fourth classifier label at runtime falls through both rules and must have a defined result, and Algorithm 5 line 14's unseen-enum perturbation exercises exactly that path. The cardinality assert is there because `filter |> project` is a collection expression: on all 32 supporting groups it yields exactly one ticket — forced by Algorithm 3 line 7, since a two-element list cannot equal the recorded scalar `ticket_id` — but nothing in the guard bounds the number of `awaiting_agent` tickets at runtime, so a multi-ticket customer aborts pre-commit and abstains to baseline rather than emitting a list where a `str` is required.

Purity is exact at $\varepsilon = 0$ on all 32 groups, and LeaveOneGroupOut passes. Note what the artifact returns: a label and an id. It does not answer the customer, does not summarize, and does not decide anything the specialist decides.

**Integration.**

```python
import compaction as cx
from agents import Agent, Runner

cx.enable_tracing(backend="mlflow", experiment="support-triage")

traces  = cx.load(backend="mlflow", experiment="support-triage", split="train")
effects = cx.EffectCatalog.from_yaml("effects.yaml")

print(cx.estimate(traces, effects))
#  n_B  = 14.2 model requests/episode
#  ceiling: phi=0.68  k=2.0  ->  max request reduction 9.6%    [Eq. 10]
#  blocked (share of candidate windows): 61% WRITE_IRREVERSIBLE (handoff
#           emission, add_case_note), 12% ungrounded slots, 6% ambiguous slots
# k=2 because the terminal handoff emission is not admissible under Eq. (5) today.

registry = cx.compile(traces, effects, alpha=0.05, min_support=5, max_region=4)
registry.report()            # 1 artifact, 2 rejected families, 1 sub-support window set
print(registry.explain())
registry.save("artifacts/triage-v1")

# specialists run plain models: compaction never crosses a handoff boundary
manager = Agent(
    name="support-manager",
    model=cx.CompactingModel(
        "gpt-5", registry=cx.Registry.load("artifacts/triage-v1"), mode="shadow"),
    tools=[get_customer_tier, list_open, get_category_hints],
    handoffs=[billing_specialist, technical_specialist, account_mgmt_specialist],
)
result = await Runner.run(manager, thread)
```

The estimator's ceiling line uses window support as $\phi$ and $\rho = 1$; it is an upper bound computed before synthesis, not a projection. `max_region=4` bounds the window to four tool events, which keeps the mined region the size of the triage prefix. It does not by itself stop a window from spanning the transfer — Algorithm 2 line 5 enumerates every `L[a..b]`, so a four-event window starting at the hint call would reach two events past the handoff and still satisfy the bound. What actually prevents spanning is Eq. (5) at Algorithm 2 line 8 today (the transfer is `WRITE_IRREVERSIBLE`, outside $\mathcal{E}_{\text{allowed}}$), and G1's terminal-position constraint under the proposed rule. `mode="shadow"` is mandatory first, but under v0.4 it too produces only BASELINE decisions here, because the non-empty handoff set fails the resolve guard on every boundary — see caveats. There is no public keyword on `cx.compile()` to widen $\mathcal{E}_{\text{allowed}}$; that is gap **G2**. G2 is not what pins $k=2$ — G1 is; and widening $\mathcal{E}_{\text{allowed}}$ to admit `WRITE_IRREVERSIBLE` outright would violate §7.2, which is why G1 must be a narrow terminal-emission rule rather than a knob.

**Savings.** Assumptions:

- $n_B = 14.2$ model requests per episode, measured by `cx.estimate` over 60 Train groups (3.1 manager prefix, 11.1 specialist).
- $k = 2$ today; $k = 3$ with the terminal-emission rule of gap G1.
- $\phi = 0.45$, and it is *not* derived from support. 32/60 is family support at mine time (Algorithm 2 line 15). $H_a(z)$ is entry-state only, and the printed hulls — tenant enum, customer-id regex, message length band — pass on essentially every inbound conversation, so the hard guard admits close to 60/60. Coverage is therefore set by the calibrated gate alone: at $\eta = 0.10$ it admits 0.45 of episodes, having been trained with the `reason`-bearing, bare-technical, ambiguous, and clarifying-question groups as negatives per §4.2. Do not multiply a support fraction by a gate fraction.
- $\rho = 0.90$ verifier pass rate among dispatches; the aborts are the hint-domain assert, the cardinality assert, and classifier drift.
- At most one dispatch per episode — triage happens once, so there is no repetition multiplier.

Eq. (10), $\phi\rho k \gtrsim \Delta \cdot n_B$:

$$\phi\rho k = 0.45 \times 0.90 \times 2 = 0.81 \quad\Longrightarrow\quad \Delta = \frac{0.81}{14.2} = 0.057$$

**5.7% request reduction** is the shippable figure. With the terminal-emission rule of gap G1 the same artifact reaches $0.45 \times 0.90 \times 3 = 1.215$ and $\Delta = 1.215/14.2 = 0.086$, i.e. 8.6%, but that configuration requires an effect rule that does not exist and library slice v0.5+. Both sit inside the 5–15% band; neither justifies more.

**What makes it worse.** First and structurally: 11.1 of the 14.2 requests belong to the specialist, and the artifact cannot touch any of them. If specialist resolution lengthens to $n_B = 20$, the same artifact yields $0.81/20 = 4.1\%$ ($1.215/20 = 6.1\%$ under G1) — the denominator grows while $k$ is pinned to the prefix. Second, prompt caching (§3.4): requests #2 and #3 have mostly-cached prefill, so the dollar ratio will lag the request ratio and must be reported with the $c^{\text{in}}_{\text{cold}} / c^{\text{in}}_{\text{cached}} / c^{\text{out}}$ decomposition. Third, Algorithm 6's caveat (i): with Dev at 20 scenario groups, the Clopper–Pearson upper bound at $\alpha = 0.05$ typically requires *zero* observed violations, so `CalibrateGate` may return RETIRE and $\phi \to 0$. That is the correct output, and it takes the savings to zero.

**What is rejected, and why.**

- **Compiling across the ownership boundary.** The specialist's first model request carries a different manifest — agent name, prompt hash, tool set, handoff set, policy hash — so $H_a(z)$ fails at Algorithm 7 line 2 and no artifact resolves there. That manifest change is one of three independent barriers; the other two are Eq. (5) at Algorithm 2 line 8, which drops any window containing the transfer today, and G1's terminal-position constraint under the proposed rule. `max_region=4` is not one of them: it bounds window size, not window placement. §7.4 states the boundary directly: never erase ownership, specialist policy, guardrails, or nested approvals.
- **Replacing the specialist.** An artifact that produced the specialist's answer directly would bypass the handoff's `on_handoff` callback and input filter, the specialist's own guardrails, and its `output_type`, and would move the final-answer owner. That violates the ownership and continuation contracts of conformance test 2 in §5.6. The artifact therefore emits the handoff `function_call` as a native item and stops; the Runner performs a real SDK handoff and the specialist owns the final answer. Output guardrails on the manager cannot be elided because the manager never produces a final output on this path.
- **Compacting the specialist's own work with this artifact.** The specialist is a different principal with a different tool surface and ACL scope. Reusing `support.triage_route@1` inside it is cross-principal reuse, forbidden outright; a specialist would need its own corpus, its own effect catalog, and its own calibrated gate.
- **`crm.add_case_note`.** `WRITE_IRREVERSIBLE` with `capabilities: []`. Any window containing it fails Eq. (5) at Algorithm 2 line 8. The note text is also ungrounded, so it fails Eq. (4) independently.
- **The `reason`-bearing handoff family (11 groups).** `reason` first appears in a `MODEL_RESP` and is neither constant nor in $\mathcal{T}^{\le 2}$ of any observation: UNGROUNDED at Algorithm 1 line 9, window dropped at Algorithm 2 line 10, Eq. (4) unsatisfied.
- **The bare technical-handoff members (9 groups).** These pass Eq. (4) and Eq. (5) and were mined into the surviving family, but they are refused at synthesis, because no entry-state guard separates them from the `reason`-bearing 11 and the verifier cannot detect a dropped `reason`. Technical traffic abstains to baseline via the `hint.top_category` assert. This costs 9 groups of support and is the correct trade: a gate score is a risk estimate, never a correctness oracle.
- **The clarifying-question windows (3 groups).** Support 3 < `min_support = 5`, so Algorithm 2 line 15 filters them before family formation; no branch synthesis is attempted. Had support been sufficient, the labels are not separable by three atoms over the observable paths and Algorithm 4 line 11 would return $\bot$.
- **Any imperfect router.** `purity` is exact at $\varepsilon = 0$. A predicate that classifies 95% of the supporting traces is not a 95%-good artifact; it is a rejected artifact. Silent misrouting is the exact failure mode this rule exists to prevent, and abstention to baseline costs only the gate evaluation ($\bar b\,c_g$, ~1 ms per Eq. (8)); a dispatch whose verifier rejects additionally costs the wasted-attempt term $\phi(1-\rho)c_w$.

**Adoption caveats.** This use case requires library slice **v0.5+** (§5.8), where handoffs are scheduled. That is a sequencing fact, not a defect: §5.6 conformance test 7 requires that streaming, hosted tools, and handoffs *reject rather than silently degrade*, and v0.1 of the SDK backend is explicitly single-agent with everything else failing closed. Concretely, `CompactingModel` snapshots `handoffs` into $z$; a non-empty handoff set with no declared handoff support means `dispatch` returns BASELINE at Algorithm 7 line 3 on every boundary. Under v0.4 the artifact above never fires, in either mode.

**What is still worth doing now.** v0.1 — Algorithms 1–2 plus `cx.estimate()` — runs on traced handoff episodes today and answers whether the triage prefix is regular enough to be worth compiling, which is the only question that matters before v0.5 exists. The v0.1 estimator, not shadow mode, is what yields signal today, and that measurement is the gate on the rest. Capture must first satisfy §7.4's instrumentation row for multi-agent orchestration: agent spans, handoff events, ownership, and context filters. Without an explicit ownership marker Algorithm 1 cannot tell where the manager's window must end, and windows will silently run into specialist events. Note also §5.5: `@mlflow.trace` does not auto-propagate thread context, so the parallel read fan-out at `MODEL_REQ #1` will fragment into separate traces if wired badly — and a fragmented fan-out both destroys the family's canonical hash before mining ever sees it and re-serializes the two reads into the call/result/call/result order that manufactures the spurious data edge described above.

Two API gaps, stated rather than invented around. **G1**: there is no effect class or Eq. (5) provision for a terminal ownership-transfer emission — a call the artifact emits but does not execute, constrained to be last in the region. **G2**: `cx.compile()` exposes only `alpha`, `min_support`, and `max_region`; there is no public control over $\mathcal{E}_{\text{allowed}}$, though widening it to admit `WRITE_IRREVERSIBLE` would violate §7.2 and is not the fix. Both must be designed before this artifact can be admitted, and G1 needs its own conformance test asserting that the emitted handoff is indistinguishable from a model-emitted one at the Runner boundary.

The single biggest thing that could make this not work: the routing decision may simply not be separable. Human-shaped triage keys on tone, urgency, escalation history, and prior-conversation context that these three reads do not observe. If Algorithm 4 returns $\bot$ on every mined family, there is no artifact, and abstention is the correct and expected output. The second biggest: `tickets.get_category_hints` must stay a deterministic classifier. The moment it becomes model-backed, `replayable` is withdrawn from the catalog, the region stops compiling, and every deployed artifact retires on the manifest hash — which is the fail-closed behaviour working as intended.

---

## Use case 5 — Multi-tenant enterprise operations agent over MCP servers

**Setting.** An internal operations agent serves ~1,900 episodes/day across 41 tenants of a single SaaS deployment. It is wired to three MCP servers — a directory server (`directory.resolve_user`, `directory.list_group_memberships`), an issue-tracker server (`issues.search`, `issues.get`, `issues.transition`), and a wiki server (`wiki.search`) — 61 advertised tools in total, of which six carry almost all the traffic. The loop is ReAct over an 11k-token system prompt plus the MCP tool manifests, so every boundary re-prefills a large, mostly static prefix and a growing history. Measured over 1,900 recorded episodes in the largest tenant, $n_B = 22.3$ model requests per episode; the modal shape is *resolve an identity, establish its permission context, fan out over the resulting work items, then reason*.

**Why it qualifies.** The candidate region $W$ covers three tool events plus a five-way read fan-out — eight tool events, exactly at `max_region=8` (Algorithm 2 line 6). Live-ins are $\mathrm{LiveIn}(W)=\{$`tenant_id`, `principal`, `rbac_roles`, `residency_region`, `policy_version`, `subject_email`$\}$, all present in the intake payload that constitutes the entry state $z$, so Algorithm 2 line 11 passes. Eq. (4) holds slot by slot: `email` $=$ `θ.subject_email` (identity over $z$); `user_id` $=$ `u.user_id` (identity over an in-region observation); `jql` $=$ `fmt(...)` applied to `u.user_id` (depth-1, in-region); `tenant` $=$ `θ.tenant_id` (live-in, guard-pinned); each `issue_key` is an element of `topk(fields.updated_at, 5) |> project(key)` over `hits.issues` (depth-2, in-region). No slot's value first appears in a model response without a bounded transform. Eq. (5) holds: $\lvert B_\tau\cap\mathrm{interior}(W)\rvert = 4 \ge 2$ (boundaries #1–#4), and every event is `READ_EXTERNAL` with `speculatable ∧ replayable`; the fan-out additionally consumes `batchable ∧ reorderable`, which only `issues.get` declares. Live-outs are $\{$`user_id`, `roles`, `keys`, `docs`$\}$. The region terminates *before* `wiki.search` and `issues.transition`, i.e. before the first undeclared read and the first commitment of any kind (§7.3 precondition 5).

**Trace fragment.**

```text
z (entry state at boundary #1, from the intake payload — custom spans, §7.4)
  { tenant_id:"nw-eu-1", principal:"u_2049",
    rbac_roles:["ops-responder","sre-oncall"], residency_region:"eu-west",
    policy_version:"2026-06-14", subject_email:"dana.okafor@northwind.example" }

MODEL_REQ #1  → MODEL_RESP: call directory.resolve_user(
                              email="dana.okafor@northwind.example")
TOOL_RESULT   → { user_id:"u_8831", tenant_id:"nw-eu-1", region:"eu-west",
                  display_name:"Dana Okafor", status:"active" }
MODEL_REQ #2  → MODEL_RESP: call directory.list_group_memberships(user_id="u_8831")
TOOL_RESULT   → { user_id:"u_8831", tenant_id:"nw-eu-1",
                  groups:[ {id:"g_ops_eu",  role:"ops-responder"},
                           {id:"g_pay_sre", role:"sre-oncall"} ] }
MODEL_REQ #3  → MODEL_RESP: call issues.search(
                  jql="assignee = u_8831 AND status in (\"Open\",\"In Progress\")
                       ORDER BY updated DESC",
                  tenant="nw-eu-1")
TOOL_RESULT   → { total:12, issues:[
                    {key:"OPS-4417", fields:{updated_at:"2026-07-31T09:12:04Z", priority:"P2"}},
                    {key:"OPS-4402", fields:{updated_at:"2026-07-30T18:44:51Z", priority:"P1"}},
                    {key:"OPS-4390", fields:{updated_at:"2026-07-30T11:02:19Z", priority:"P3"}},
                    {key:"OPS-4388", fields:{updated_at:"2026-07-29T16:37:40Z", priority:"P2"}},
                    {key:"OPS-4351", fields:{updated_at:"2026-07-28T08:55:12Z", priority:"P3"}},
                    ... 7 more ... ] }
MODEL_REQ #4  → MODEL_RESP: call issues.get(issue_key="OPS-4417")
                            call issues.get(issue_key="OPS-4402")
                            call issues.get(issue_key="OPS-4390")
                            call issues.get(issue_key="OPS-4388")
                            call issues.get(issue_key="OPS-4351")
TOOL_RESULT ×5 → { key:"OPS-4417", tenant_id:"nw-eu-1", assignee:"u_8831",
                   summary:"payments p99 latency regression, eu-west",
                   status:"In Progress", comments:[...3...] }   (and 4 more)
─── region ends here; everything below stays with the baseline ───────────────
MODEL_REQ #5  → MODEL_RESP: call wiki.search(query="payments latency runbook eu-west",
                                             space="SRE")
MODEL_REQ #6  → MODEL_RESP: call issues.transition(issue_key="OPS-4402",
                                                   status="In Progress")
```

**What Algorithm 1 recovers.** `email="dana.okafor@northwind.example"` has no producer in $\tau$, but the entry-state schema is seeded into `Idx` before mining, so it resolves as a live-in rather than reaching line 9's UNGROUNDED marking; Algorithm 2 line 11 then checks it against `EntryStateSchema`. This is the same latent gap §5.7 leaves open for `username`, stated here rather than inherited. `user_id="u_8831"` exact-matches both `resolve_user.user_id` and `list_group_memberships.user_id`; line 11 binds the PATG edge to the nearer producer, and Algorithm 3 line 10's (MDL, $\lvert\sigma\rvert$, lex) tie-break is what fixes which one the emitted program reads. The non-identity recovery is the fan-out: `issue_key="OPS-4417"` exact-matches `hits.issues[0].key`, a *positional* path that is unstable, and `TransformSearch` at depth 2 finds `topk(fields.updated_at, 5) |> project(key)`. The version space is not a singleton: `filter(fields.updated_at ≥ c) |> project(key)` over an observed timestamp literal also reproduces the five keys, and `first`/`last` are positional operators that do live in $\mathcal{T}$. What eliminates the *reversed* composition is the type check at Algorithm 3 line 6 — after `project(key)` the sort path no longer exists. Among the survivors, Algorithm 3 line 10 selects by (MDL, $\lvert\sigma\rvert$, lex); the ordering-stable `topk` program wins only because it is the shortest expression with the observed cardinality 5, and the leave-one-group-out check at line 11 is what keeps it from being a coincidence. The `jql` slot is recovered as `fmt` over `u.user_id`; the `fmt` template is a constant drawn from literals observed in the supporting traces (§4.3), and it survives only because Algorithm 3 line 7 requires consistency across all seven supporting groups. It is exactly the kind of binding that can memorize, so LeaveOneGroupOut at line 11 is load-bearing rather than ceremonial.

Two slots are correctly left ungrounded, and both matter. First, `wiki.search(query="payments latency runbook eu-west")`: the string has no producer *and* no entry-state source, and no bounded transform reaches it — it is a composed natural-language query, i.e. a genuine decision. Algorithm 1 marks it UNGROUNDED at line 9 and Algorithm 2 line 10 drops every window containing it. That truncation is what sets the region's right edge, independently of `wiki.search` also being UNKNOWN. Second, and more uncomfortable: `tenant="nw-eu-1"` has three exact-match sources in the index ($z$`.tenant_id`, `u.tenant_id`, `gm.tenant_id`), which is exactly at the ambiguity cap $\kappa=3$, so it is *not* marked AMBIGUOUS. Algorithm 1 line 11 binds the PATG edge to the *nearest* producer, `gm.tenant_id` (event #2) — the subject's tenant, not the caller's. Algorithm 3 line 10 then breaks the version-space tie by (MDL, $\lvert\sigma\rvert$, lex) and selects `θ.tenant_id`, which is what the emitted program uses. The point stands: nothing in the binder *requires* the caller's tenant; Eq. (4) is satisfied by all three, and under leave-one-group-out they are indistinguishable, because every training episode has them equal. Cross-tenant safety therefore cannot rest on the binder. It rests on `tenant_id` being a hard guard key and on the in-program assert that forces the two to be equal at run time. One more producer of the same string would flip the slot to AMBIGUOUS and delete the family outright.

**Effect catalog.**

```yaml
# effects/mcp_ops.yaml
# MCP discovery gives schemas, not effects. Anything not listed here is UNKNOWN
# and is never compiled. 55 of this deployment's 61 tools are still undeclared.
version: 1
tools:
  directory.resolve_user:
    effect: READ_EXTERNAL
    capabilities: [speculatable, replayable, cacheable, reorderable]
    key: [tenant_id, principal, rbac_roles, residency_region, policy_version, email]
    freshness_s: 900
    notes: >
      Directory MCP v3.2. The read is ACL-filtered by the calling principal, so
      principal and rbac_roles are key fields, not metadata. No audit row is
      written; confirmed with the identity team 2026-05-19.

  directory.list_group_memberships:
    effect: READ_EXTERNAL
    capabilities: [speculatable, replayable, reorderable]
    key: [tenant_id, principal, rbac_roles, residency_region, policy_version, user_id]
    freshness_s: 300
    notes: >
      Deliberately not cacheable: this result is the RBAC input, and a stale
      membership is a permission error, not a stale display value.
      freshness_s: 300 bounds speculative replay only; memoization is not
      licensed.

  issues.search:
    effect: READ_EXTERNAL
    capabilities: [speculatable, replayable, reorderable]
    key: [tenant_id, principal, rbac_roles, residency_region, policy_version, jql]
    freshness_s: 60
    notes: >
      Deliberately not cacheable: the result set is ACL-filtered server-side and
      changes on any membership edit. Not batchable: no multi-query endpoint.

  issues.get:
    effect: READ_EXTERNAL
    capabilities: [speculatable, replayable, cacheable, reorderable, batchable]
    key: [tenant_id, principal, rbac_roles, residency_region, policy_version, issue_key]
    freshness_s: 120
    notes: >
      batchable licensed by the server's bulk endpoint (<= 50 keys; one audit row
      per key either way, so fusion does not change audit state). reorderable
      verified: no server-side read cursor.

  wiki.search:
    effect: UNKNOWN
    capabilities: []
    key: []
    notes: >
      Listed explicitly, as UNKNOWN, so the blocked-window report attributes it by
      name. The MCP manifest gives a JSON schema and no effect. The space argument
      can address spaces outside the tenant's residency boundary, and the server
      writes a search-audit row visible to space admins, so this is not a clean
      read. Stays uncompilable until the wiki team declares it.

  issues.transition:
    effect: WRITE_IRREVERSIBLE
    capabilities: []
    key: [tenant_id, principal, rbac_roles, residency_region, policy_version, issue_key]
    notes: >
      Fires outbound webhooks and starts SLA timers that no compensating call
      undoes. Never compiled.
```

**Synthesized artifact.**

```text
artifact  ops.identity_scope_and_queue_fanout@1   support 7/24 groups   removes k=4
──────────────────────────────────────────────────────────────────────────────
guard   model=gpt-5-2026-04-12  prompt=#5d81  tools=#b3af  policy=#7a10
        z.tenant_id        = "nw-eu-1"                       (hard key, exact)
        z.residency_region = "eu-west"                       (hard key, exact)
        z.policy_version   = "2026-06-14"                    (hard key, exact)
        z.rbac_roles       = {ops-responder, sre-oncall}     (hard key, exact set)
        z.principal        : str  matches ^u_[0-9]{4,6}$     (hard key, present)
        z.subject_email    : str  matches ^[a-z][a-z.\-]{2,38}@northwind\.example$
        effects ⊆ {READ_EXTERNAL}   all speculatable ∧ replayable
        fan-out licensed by batchable ∧ reorderable, on issues.get only

program (θ = {tenant_id, principal, rbac_roles, residency_region,
              policy_version, subject_email}):
   u    = call directory.resolve_user(email = θ.subject_email)
   gm   = call directory.list_group_memberships(user_id = u.user_id)
   if len(gm.groups) == 0: ABSTAIN                                       ← Alg.4
   roles= gm.groups |> sort(role) |> project(role)                       ← Alg.3
   jql  = fmt("assignee = {} AND status in (\"Open\",\"In Progress\")
               ORDER BY updated DESC")  applied to  u.user_id            ← Alg.3
   hits = call issues.search(jql = jql, tenant = θ.tenant_id)
   keys = hits.issues |> topk(fields.updated_at, 5) |> project(key)      ← Alg.3
   docs = []
   ForEach key in keys (max 32, unordered — reorderable; fused — batchable):
        docs = docs ++ [ call issues.get(issue_key = key) ]
   assert  u.tenant_id == θ.tenant_id  and  u.region == θ.residency_region
           and  gm.tenant_id == θ.tenant_id
           and  len(keys) == 5  and  len(docs) == 5
           and  ∀ x ∈ docs : x.tenant_id == θ.tenant_id
   return  { user_id: u.user_id, roles: roles, keys: keys, docs: docs }

verify  user_id : str, non-null, provenance ∈ {directory.resolve_user}
        roles : list[str], card ≤ 16, provenance ∈ {directory.list_group_memberships}
        docs : list, card = 5, each ⊨ issue_schema, provenance ∈ {issues.get}
        keys : list[str], card = 5, provenance ∈ {issues.search}
        ∀ d ∈ docs : d.tenant_id = θ.tenant_id   (cross-tenant leak check)
        ∀ k ∈ keys : k ∈ project(key)(hits.issues)
        effect_multiset = {READ_EXTERNAL × 8} ⊆ E_allowed
gate    q = GBM(entry features)   η = RETIRE   (Dev, α=0.05, δ=0.10, |Λ|=11)
        no admissible η: R⁺ ≥ 0.178 at 24 scenario groups   (Alg.6 line 9)
```

That gate line is the outcome, not a placeholder. Algorithm 6 line 6 takes a Clopper–Pearson upper bound at level $1-\delta/\lvert\Lambda\rvert = 1-0.10/11$; with zero observed violations the bound is $1-(0.00909)^{1/n}$, which needs $n \ge 92$ independent zero-violation units before it falls to $0.05$. §4.6 caveat (i) — which this section invokes twice — makes the effective $n$ the *scenario-group* count. The largest tenant has 24 groups, giving $R^{+}=0.178$; over the 7 supporting groups it is $0.489$. Both are far above $\alpha=0.05$, so $\mathrm{Adm}=\varnothing$ and line 9 returns RETIRE. Shipping this artifact would require relaxing $\alpha$ to roughly $0.2$, which is not on offer. This is caveat (i) not merely costing coverage but eliminating the artifact.

The `ABSTAIN` at Algorithm 4 is not a convenience either. In 2 of 9 candidate groups the subject had an empty group list and the baseline asked a clarifying question — a real decision the region cannot contain. The atom `len(gm.groups) == 0` separates those groups perfectly (Ops(list) includes `len =`), so the divergence is *explainable*, but the branch target is a model turn, not a tool sequence. The program therefore aborts pre-commit, Algorithm 7 line 9 returns BASELINE, and the two directory reads are charged to the method as $c_w$ in Eq. (8).

**Integration.**

```python
import compaction as cx
from agents import Agent

# capture. tenant_id / principal / rbac_roles / residency_region / policy_version
# are NOT inferred by MLflow or the SDK -- they arrive via custom spans (§7.4).
cx.enable_tracing(backend="mlflow", experiment="ops-agent")

traces  = cx.load(backend="mlflow", experiment="ops-agent", split="train")
effects = cx.EffectCatalog.from_yaml("effects/mcp_ops.yaml")

print(cx.estimate(traces, effects))
#  n_B  = 22.3 model requests/episode
#  ceiling: phi=0.44  k=4.0  ->  max request reduction 7.9%   [Eq. 10]
#  blocked: 68% of windows by UNKNOWN effects, 19% by ungrounded slots
# With an empty catalog the same command prints phi=0.00 and 100% blocked by
# UNKNOWN. Getting from 100% to 68% is what six declared tools bought.

# compile per tenant: tenant_id is an exact hard guard key, so registries built
# from one tenant's traces are never valid in another. Do not merge them.
registry = cx.compile(traces, effects, alpha=0.05, min_support=5, max_region=8)
registry.report()            # 0 kept, 4 RETIRED by Alg. 6, rejection reasons
print(registry.explain())
registry.save("artifacts/nw-eu-1/2026-06-14")     # path carries tenant + policy

# deploy. shadow is mandatory and is the only mode that answers "would this have
# fired on a tenant it was not built for?" before it can.
ops_agent = Agent(
    name="ops-triage",
    model=cx.CompactingModel(
        "gpt-5",
        registry=cx.Registry.load("artifacts/nw-eu-1/2026-06-14"),
        mode="shadow",
    ),
    tools=[...],                                   # MCP-backed tools
)
```

For the non-SDK loop this deployment actually runs, the entry point is the decorator:

```python
@cx.compact(registry=registry)
def ops_step(entry_state: dict) -> cx.Decision:
    ...   # entry_state must already carry tenant_id, principal, rbac_roles,
          # residency_region, policy_version; if any is absent the hard guard
          # cannot be evaluated, H_a(z) is false at Algorithm 7 line 2, and
          # line 3 returns BASELINE.
```

**Gap, stated rather than papered over:** `@cx.compact(registry=)` in §5.2 takes no `mode` argument, so the mandatory shadow stage of §5.8 v0.3 is expressible only through `CompactingModel`. A non-SDK agent has no documented way to run shadow. That is a missing keyword, not a missing design, but it blocks the safe rollout order for exactly the deployment shape this use case describes.

**Savings.** These are what the artifact *would* deliver at an admissible gate; Algorithm 6 supplies none on this corpus, so read the whole block as an upper bound on what a Dev set of $\ge 92$ exchangeable groups could buy. Assumptions, all measured on the recorded corpus for tenant `nw-eu-1` unless noted:

- $n_B = 22.3$ model requests per episode.
- $k = 4$ — boundaries #1–#4 are strictly inside the region and are all removed on a hit.
- $\phi = 0.32$ at the $\eta=0.05$ grid point the artifact would need. The estimator's ceiling is $0.44$; the gate costs the difference, and then §4.6's caveat (i) removes the artifact entirely rather than merely trimming coverage.
- $\rho = 0.88$. The residual is dominated by the empty-group-list abstention and by `issues.search` returning fewer than 5 open issues, which fails the `len(keys) == 5` assert.

$$\phi\rho k = 0.32 \times 0.88 \times 4 = 1.1264 \qquad \Delta = \frac{1.1264}{22.3} = 0.0505$$

**5.0% fewer model requests per episode** — the bottom of the proposal's realistic 5–15% band. Eq. (10) at $\Delta=0.10$ would require $\phi\rho k \ge 2.23$, roughly double, which at $k=4$ means $\phi\rho \ge 0.56$ and therefore a guard materially looser than exact equality on five key fields. That trade is not available here.

What makes it worse. Dollars lag: the four removed requests are mid-episode, so their prefill is almost entirely cached and $c^{\text{in}}_{\text{cold}}$ is near zero; decomposed per §3.4 the 5.05% request reduction lands around 2–3% of spend. Latency lags harder: with $\mu \approx 0.38$ (MCP round trips over the corporate network dominate wall time), Eq. (11) gives $\Lambda \approx 1 - 0.38 \times 0.0505 + (\bar b\,t_g + \phi\,t_x)/\mathbb{E}[T_B] \approx 0.982$ — under 1.9% at p50, and less once the abstention path's two wasted MCP round-trips are charged, which §4.7 requires. The fan-out fusion (5 RPCs into 1) is a larger wall-clock win than the compaction, and it is honestly **not** attributable to this method — an ordinary batch tool in the baseline agent captures it. Finally, amortization: with $C_{\text{compile}} \approx \$400$ per tenant (dominated by human review minutes, not compute) and a per-episode *dollar* saving of about 2.5% of the $\$0.257$ episode spend, i.e. $\approx \$0.0064$ — not $1.126\,c_m$, because the removed requests are cache-cheap — less the gate, execute and wasted-attempt terms $\bar b c_g + \phi c_x + \phi(1-\rho)c_w$, Eq. (12) gives $N^\star \gtrsim 6\times10^{4}$ episodes **per tenant, per policy version**. At 1,900 episodes/day across 41 tenants, a 30-day payback would need about 2,000 episodes/day from a single tenant — more than the entire deployment produces. **No tenant amortizes one compilation between monthly policy bumps**; the deployment as a whole would need roughly 32 days of *all* its traffic to pay back one per-tenant compile.

**What is rejected, and why.**

- **`issues.transition`.** Declared `WRITE_IRREVERSIBLE` with empty capabilities, so any window containing it fails Eq. (5) at Algorithm 2 line 8 and is dropped before synthesis. Independently, *which* status to transition to is a genuine decision with no producer in the observation set, so it also fails Eq. (4). And it is a state mutation, which §7.2 puts out of scope for the scored condition regardless of idempotence.
- **`wiki.search`.** Rejected twice over. Its effect is `UNKNOWN`, so line 8 drops it; its `query` slot is UNGROUNDED, so line 10 drops it. Declaring the effect would not rescue it. This is the shape of most MCP tools: the manifest is a schema, and a schema says nothing about audit rows, quota, residency reach, or time-variance.
- **Any entry state missing `tenant_id`, or carrying a different one.** The hard guard $H$ pins `tenant_id` by exact equality (Algorithm 5 line 3 fits an enum hull of cardinality 1 on Train), and Algorithm 7 line 2 filters on $H$ *before* the score is ever computed. Cross-tenant reuse is not a coverage/threshold trade-off — no value of $\eta$, no calibration, and no $q$ can admit it.
- **A subject who resolves outside the guarded residency region — but by assert, not by guard.** `residency_region` is different in kind: `z.residency_region` is guard-pinned, but the *subject's* resolved region `u.region` is only observable after the first read. A `nw-eu-1` artifact therefore does fire for a principal who turns out to resolve in `us-east`; the `assert u.region == θ.residency_region` aborts it pre-commit (Algorithm 7 line 9) and the read is charged to the method as $c_w$. Residency is enforced by the assert, not by $H$.
- **Any reuse crossing `policy_version` or credential scope.** `policy=#7a10` is part of the manifest hash in $H$ (Algorithm 5 line 1); an RBAC policy bump changes the hash and every artifact in the registry misses. Separately, the catalog `key` lists include `principal` and `rbac_roles`, so a `cacheable` read is never served across principals — the memoization scope is the key tuple, not the tool name, and the RBAC membership read is not `cacheable` at all.
- **Windows with more than five fetched issues.** Six or more `issues.get` calls push the window past eight tool events and Algorithm 2 line 6 (`max_region=8`) drops it. This is a real coverage cost, not a bug: a third of the fan-out episodes fetch 6–9 issues and none of them are compiled.
- **Post-hoc rollback of anything.** If an artifact ever reached `issues.transition` and it committed, Algorithm 7 lines 10 and 13 raise INCIDENT. The runtime does not abort-and-fall-back after a commitment, and this section makes no claim that a compensating transition restores the pre-call state — the webhooks have already fired.

**Adoption caveats.**

The estimator slice, **v0.1**, is where all of the value in this use case sits, and it should be run before anything else is built: it prices the catalog work. **v0.2** produces the artifact and the `explain()` listing above with zero runtime risk — including, as here, the finding that the gate retires it. **v0.3** would be the only way to observe how often the guard is *nearly* satisfied by a neighbouring tenant, and it presupposes an artifact that clears Algorithm 6. **v0.4** delivers live dispatch, but §5.6 scopes v0.1 of the SDK backend to "single-agent, local function tools," and MCP-backed tools are neither local function tools nor documented hosted tools. Conformance test 7 says such surfaces reject rather than silently degrade, so live mode on MCP is **v0.5+** work: a `runtime/adapters/` MCP adapter plus a re-run of all seven conformance tests against a server that versions independently of the agent.

What fails closed, correctly and quietly: any tool not in the catalog (55 of 61 here); any MCP server that adds or renames a tool, which changes `tools=#b3af` and misses the guard; any entry state lacking one of the five key fields; any $q_a(z) > \eta$. All of these degrade to baseline with no behaviour change and no error, which is the design working — and also the reason coverage erodes without anyone noticing. `registry.report()` on a schedule is the only thing that surfaces it.

The catalog is real, unglamorous work and should be budgeted as such. The six tools above took about 3 hours including one 45-minute session with each of the directory and issue-tracker owning teams; the question that consumes the time is never the schema, it is "does this read burn quota, write an audit row, or reach outside the residency boundary." Extrapolated to the remaining surface — 55 undeclared tools across the same three servers — 20 to 40 minutes per tool plus a 60-minute kickoff per owning team gives **22 to 40 person-hours**, spread across 3 to 4 calendar weeks because it is gated on other teams replying. Recurring cost is roughly 2 hours a month as servers ship tools. Do not declare alphabetically: `cx.estimate()` reports blocked windows attributed by tool and by reason, and in this corpus six of the 55 *undeclared* tools accounted for 71% of `UNKNOWN`-blocked windows while the remaining 49 accounted for 29%. Declare in descending blocked-window order and stop when the marginal tool moves $\phi$ by less than a point.

One instrumentation prerequisite that is easy to underestimate: §5.5 notes that MLflow request/response previews may be truncated. A 12-issue search result truncated in the preview silently removes producers from Algorithm 1's index, which turns grounded slots into UNGROUNDED ones and deletes families without any error. Mining must read the raw complete trace JSON from the authoritative-research path, never the preview.

The single biggest thing that could make this not work is `policy_version` churn interacting with per-tenant support. Every hard key field multiplies the partition: tenant $\times$ exact role set $\times$ residency $\times$ policy version. In this corpus the largest tenant has 24 scenario groups and 31 distinct principal role sets, of which 3 reach `min_support=5` — and 24 groups is already too few for Algorithm 6 to certify anything at $\alpha=0.05$. Compilation must be redone per tenant and re-done again on every policy bump, while $N^\star \gtrsim 6\times10^{4}$ episodes says one compilation costs more than a month of the *whole deployment's* traffic to repay. If policy versions bump monthly — which is the norm in RBAC-governed deployments — the system never amortizes for any tenant at all, and the correct engineering answer is to ship v0.1 as a standing measurement tool and not build the compiler for this workload.

---


---

## Other patterns at a glance

Three further patterns from proposal §7.4 are plausible but were not developed into full use cases,
either because they are variations on the mechanics above or because their hard boundaries dominate.

| Pattern | Compilable region | What makes it nontrivial | Hard guard must include | Why it is harder |
|:--|:--|:--|:--|:--|
| **Long-running business process** | Poll-and-validate segments: check job status, fetch partial results, decide whether to keep waiting | A bounded `ForEach` whose termination predicate is a decision list over `status` (Alg. 4), coalescing many polls into one artifact | Workflow version, record version, timer semantics, wall-clock projection | Time drift is a correctness hazard the effect catalog cannot express. A poll loop correct at compile time can be wrong when latencies shift, and Eq. (5)'s pre-commit rule does not protect against a stale decision |
| **Memory-enabled agent** | Versioned memory read, dedup, deterministic formatting before the model turn | `project` and `filter` over a memory namespace; `cacheable` keyed on snapshot version | Namespace, identity, memory snapshot version, retention class | Memory *writes* are excluded outright. Cross-user reuse is an identity-leakage bug that looks exactly like a cache hit, so identity must be a key field, never a similarity feature |
| **CI / build-failure triage** | Fetch job metadata, download logs, extract the failing step and error class, hand a structured summary to the model | `split(sep)[i]` and `filter` over large log payloads; the classification itself is usually a decision list | Pipeline definition hash, runner image, log schema | Large free-text payloads stress Algorithm 1's `groundable` predicate in both directions: log lines produce spurious exact matches on common tokens, and genuine flows hide inside unstructured text. Expect low provenance recall and measure it explicitly at Gate 0 |

---

## Anti-use-cases: where not to apply this

Refusing to compile is the system's most common correct output, and the same logic applies at the
level of whole agents. Each row rules the approach out before any engineering starts.

| Do not use it when | Governing rule | Why |
|:--|:--|:--|
| The agent's value is its variance — research, creative work, open-ended exploration | Alg. 2 support threshold | There is no recurring region to find. Support never reaches $s_{\min}$, and forcing it produces artifacts that fire on superficial similarity |
| Volume is low | Eq. (12) | $N^\star$ never amortizes. A few hundred executions per artifact per quarter cannot repay compilation, however good the artifact is |
| The tool surface is mostly writes | Eq. (5) | Nearly every window contains a `WRITE_*` event and is rejected at Algorithm 2 line 8. What remains is usually a login prefix, which H1 explicitly excludes |
| Prompts or tool schemas change faster than the compile cadence | Manifest hard guard, proposal §3.3 | Every artifact pins exact model, prompt, tool, and schema hashes. If those rotate weekly and you compile monthly, the steady-state hit rate approaches zero — correctly, but uselessly. See proposal §6.4 for the CI fix |
| The episode is a single turn, or tool calls are batched into one assistant turn | Eq. (5) | Fewer than two interior model boundaries means compaction removes no decision. This is the error the model-request accounting in §4.2 exists to catch |
| Wall time is dominated by tools, not the model | Eq. (11) | $\mu$ is small, so removing model round-trips barely moves latency. Cost may still improve; latency will not. Use case 5 measures $\mu\approx0.38$ and gets under 2% |
| The decision is consequential, regulated, or needs human judgement | proposal §12 | The compiler is an execution optimizer, not an authority. Speeding up a decision does not license making it automatically |
| You cannot enumerate your tools' effects | proposal §5.3 | Everything stays `UNKNOWN`, nothing compiles, and the system correctly does nothing. A safe failure is still a failure — fix the catalog or stop |

The envelope, stated plainly: this technique pays off for **high-volume agents with stable prompts,
typed tools, a substantial read surface, and long episodes**. Outside it, `cx.estimate()` should
return a small number, and the correct response is to believe it.
