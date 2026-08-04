"""Demo A world and baseline policy: Tier-1 support over internal APIs.

Shape follows use-cases §1 exactly: a read-only evidence prefix
(``auth.issue_service_token`` → ``crm.find_customer`` → ``crm.get_subscription``
→ ``billing.list_invoices`` → ``entitlements.check``) terminated by the first
commitment (``crm.update_ticket``), with ``kb.search`` deliberately undeclared and
non-deterministic, and a refund arm whose ``refunds.issue`` amount is mechanically
derivable and still correctly rejected.

The deviations are the point. Without merged accounts, empty result sets,
paginated invoice histories, out-of-enum product areas, redundant retrieval and a
drifting arm, a gate cannot be falsified and ``ρ`` would be 1 by construction.
"""

from __future__ import annotations

import hashlib
import random
from pathlib import Path
from typing import Any, Iterable, Sequence

from agent_compaction.schema.traces import ExecutionManifest, OutcomeLabels
from agent_compaction.schema.effects import EffectCatalog
from agent_compaction.paths import stable_int

from ..framework import (
    Action,
    Call,
    CostModel,
    EpisodeSpec,
    Finish,
    Observation,
    PolicyContext,
    Think,
    ToolError,
    World,
)

EFFECTS_PATH = Path(__file__).with_name("effects.yaml")

#: Entry-state fields the application allows a rewrite to read (execution-plan §6).
ENTRY_ALLOWLIST: tuple[str, ...] = (
    "tenant_id",
    "principal",
    "ticket.intake",
    "ticket.requester_email",
    "ticket.product_area",
    "ticket.channel",
    "ticket.locale",
    "ticket.priority",
    "ticket.plan_hint",
)

MANIFEST = ExecutionManifest(
    manifest_id="support-m1",
    commit="demo-a",
    model="sim-gpt-5-2026-04-12",
    prompt_hash="#c47b",
    tools_hash="#19ae",
    policy_hash="#8d31",
    guardrail_hash="#0001",
    effect_catalog_version=EffectCatalog.from_yaml(EFFECTS_PATH).catalog_version,
    entry_contract_version="form_v3",
    sdk_version="sim-0.4.0",
    tracer_version="agent-compaction/0.5.0",
)

TENANTS = ("t_northwind", "t_contoso", "t_fabrikam", "t_tailspin")
PRODUCT_AREAS = ("sso_scim", "api_quota", "seat_mgmt", "billing_portal")
TIERS = ("free", "team", "business", "enterprise")
FIRST = ("dana", "arun", "mei", "tomas", "yara", "noor", "ivan", "kaya", "leon", "priya")
LAST = ("whitfield", "raghavan", "chen", "nowak", "haddad", "silva", "petrov", "okafor", "meyer", "das")


def _domain(tenant: str) -> str:
    return {
        "t_northwind": "northwind-labs.example",
        "t_contoso": "contoso.example",
        "t_fabrikam": "fabrikam.example",
        "t_tailspin": "tailspin.example",
    }[tenant]


class SupportWorld(World):
    name = "support"

    def __init__(self, seed: int = 7, customers_per_tenant: int = 600) -> None:
        self.customers_per_tenant = customers_per_tenant
        self.customers: dict[str, list[dict[str, Any]]] = {}
        self.subscriptions: dict[str, dict[str, Any]] = {}
        self.invoices: dict[str, list[dict[str, Any]]] = {}
        self.entitlements: dict[tuple[str, str], dict[str, Any]] = {}
        self.tokens: set[str] = set()
        super().__init__(seed)
        self._build_data()

    # -- data -------------------------------------------------------------
    def _build_data(self) -> None:
        rng = random.Random(self.seed * 31 + 5)
        for tenant in TENANTS:
            dom = _domain(tenant)
            for i in range(self.customers_per_tenant):
                first = FIRST[i % len(FIRST)]
                last = LAST[(i // len(FIRST) + i) % len(LAST)]
                mid = f"{i // (len(FIRST) * len(LAST))}" if i >= len(FIRST) * len(LAST) else ""
                email = f"{first}.{last}{mid}{i}@{dom}"
                base = hashlib.sha1(f"{tenant}:{email}".encode()).hexdigest()[:6].upper()
                cid = f"cus_{base}"
                shape = rng.random()
                recs: list[dict[str, Any]] = []
                active_rec = {"id": cid, "status": "active", "account": tenant, "email": email}
                if shape < 0.22:
                    # A duplicate closed record, on either side of the active one.
                    # The position is randomised deliberately: if the active record
                    # were always last, `last |> project(id)` would be consistent
                    # across every supporting trace and MDL would prefer it over
                    # the semantically correct filter(status == "active").
                    closed_id = f"cus_{base[::-1]}"
                    closed = {"id": closed_id, "status": "closed", "account": tenant, "email": email}
                    # the closed account has its own real subscription, so binding to
                    # it is silently wrong rather than a tool error
                    self.subscriptions[closed_id] = {
                        "customer_id": closed_id,
                        "plan_id": "plan_fre_1",
                        "tier": "free",
                        "seats": 1,
                        "renews_on": "2026-01-01",
                    }
                    self.invoices[closed_id] = [
                        {
                            "id": f"inv_2025_12_{i:04d}",
                            "status": "paid",
                            "issued": "2025-12-01",
                            "line_items": [{"sku": "seat", "amount_cents": 475}],
                        }
                    ]
                    for area in PRODUCT_AREAS:
                        self.entitlements[(closed_id, area)] = {
                            "feature": area,
                            "entitled": False,
                            "source": "plan_fre_1",
                        }
                    if rng.random() < 0.5:
                        recs.append(closed)
                        recs.append(active_rec)
                    else:
                        recs.append(active_rec)
                        recs.append(closed)
                else:
                    recs.append(active_rec)
                if 0.90 <= shape < 0.955:  # merged accounts: two active records -> abstain
                    recs.append(
                        {"id": f"cus_{base[1:] + 'Z'}", "status": "active", "account": tenant, "email": email}
                    )
                elif shape >= 0.985:  # deprovisioned: no active record -> abstain
                    for r in recs:
                        r["status"] = "closed"
                self.customers[f"{tenant}|{email}"] = recs

                tier = TIERS[min(3, int(rng.random() * 4))]
                seats = {"free": 1, "team": 12, "business": 60, "enterprise": 240}[tier]
                self.subscriptions[cid] = {
                    "customer_id": cid,
                    "plan_id": f"plan_{tier[:3]}_{seats}",
                    "tier": tier,
                    "seats": seats,
                    "renews_on": "2027-02-01",
                }
                n_inv = 3 if rng.random() < 0.75 else rng.choice([1, 2, 4, 5])
                inv = []
                for m in range(n_inv):
                    items = [{"sku": "seat", "amount_cents": 475 * seats}]
                    if tier == "enterprise":
                        items.append({"sku": "sso_addon", "amount_cents": 2400})
                    inv.append(
                        {
                            "id": f"inv_2026_{7 - m:02d}_{i:04d}",
                            "status": "open" if m == 0 else "paid",
                            "issued": f"2026-{7 - m:02d}-01",
                            "line_items": items,
                        }
                    )
                self.invoices[cid] = inv
                for area in PRODUCT_AREAS:
                    entitled = tier == "enterprise" or (area == "billing_portal" and tier != "free")
                    self.entitlements[(cid, area)] = {
                        "feature": area,
                        "entitled": entitled,
                        "source": f"plan_{tier[:3]}_{seats}",
                    }

    # -- tools ------------------------------------------------------------
    def register_tools(self) -> None:
        self.tool("auth.issue_service_token", self._issue_token, latency_ms=35, schema_tokens=60, resource="auth")
        self.tool("crm.find_customer", self._find_customer, latency_ms=70, schema_tokens=140, resource="crm")
        self.tool("crm.get_subscription", self._get_subscription, latency_ms=55, schema_tokens=130, resource="crm")
        self.tool("billing.list_invoices", self._list_invoices, latency_ms=90, schema_tokens=180, resource="billing")
        self.tool("entitlements.check", self._check_entitlement, latency_ms=45, schema_tokens=120, resource="entitlements")
        self.tool("kb.search", self._kb_search, latency_ms=130, schema_tokens=150, resource="kb")
        self.tool("crm.update_ticket", self._update_ticket, latency_ms=80, schema_tokens=170, resource="crm")
        self.tool("refunds.issue", self._issue_refund, latency_ms=110, schema_tokens=150, resource="billing")
        # The hand-written comparator of execution-plan §11.2 condition 2: one tool
        # that performs the same read prefix, executing its reads concurrently. The
        # model still has to *select* it, so one model request survives — which is
        # exactly the difference between a macro and a compiled region.
        self.tool(
            "support.gather_context",
            self._gather_context,
            latency_ms=90,
            schema_tokens=190,
            resource="crm",
        )

    def _issue_token(self) -> dict[str, Any]:
        n = self.quota.get("auth.issue_service_token", 0)
        tok = f"svc_{hashlib.sha1(f'{self.seed}:{n}'.encode()).hexdigest()[:8]}"
        self.tokens.add(tok)
        self.effect_log.append("READ_EXTERNAL")
        return {"token": tok, "scope": "support.read", "expires_in": 900}

    def _require_token(self, token: str) -> None:
        if token not in self.tokens:
            raise ToolError("invalid service token", status="error")

    def _find_customer(self, token: str, email: str, tenant: str | None = None) -> list[dict[str, Any]]:
        self._require_token(token)
        self.effect_log.append("READ_EXTERNAL")
        for key, recs in self.customers.items():
            t, mail = key.split("|", 1)
            if mail == email and (tenant is None or t == tenant):
                return [dict(r) for r in recs]
        return []

    def _get_subscription(self, token: str, customer_id: str) -> dict[str, Any]:
        self._require_token(token)
        self.effect_log.append("READ_EXTERNAL")
        sub = self.subscriptions.get(customer_id)
        if sub is None:
            raise ToolError(f"no subscription for {customer_id}", status="error")
        return dict(sub)

    def _list_invoices(self, token: str, customer_id: str, limit: int = 3) -> dict[str, Any]:
        self._require_token(token)
        self.effect_log.append("READ_EXTERNAL")
        inv = self.invoices.get(customer_id, [])
        return {"customer_id": customer_id, "invoices": [dict(x) for x in inv[:limit]]}

    def _check_entitlement(self, token: str, customer_id: str, feature: str) -> dict[str, Any]:
        self._require_token(token)
        self.effect_log.append("READ_EXTERNAL")
        ent = self.entitlements.get((customer_id, feature))
        if ent is None:
            raise ToolError("unknown feature", status="error")
        return dict(ent)

    def _kb_search(self, query: str, k: int = 5) -> dict[str, Any]:
        """Deliberately non-deterministic ranking: cannot satisfy replay equivalence."""

        self.effect_log.append("UNKNOWN")
        docs = [
            f"kb_{stable_int((query, i, self.rng.random()), bits=32) % 9999:04d}"
            for i in range(k)
        ]
        return {"query": query, "docs": docs, "index_version": f"kb-{self.rng.randint(1, 3)}"}

    def _update_ticket(self, ticket_id: str, status: str, resolution_note: str) -> dict[str, Any]:
        self.effect_log.append("WRITE_IRREVERSIBLE")
        self.committed.append({"op": "update_ticket", "ticket_id": ticket_id, "status": status})
        return {"ok": True, "version": 7}

    def _issue_refund(self, invoice_id: str, amount_cents: int) -> dict[str, Any]:
        self.effect_log.append("WRITE_IRREVERSIBLE")
        self.committed.append({"op": "refund", "invoice_id": invoice_id, "amount_cents": amount_cents})
        return {"ok": True, "refund_id": f"rf_{invoice_id[-4:]}", "amount_cents": amount_cents}

    def _gather_context(self, email: str, tenant: str, product_area: str) -> dict[str, Any]:
        tok = self._issue_token()["token"]
        recs = self._find_customer(tok, email.lower(), tenant)
        active = [r for r in recs if r.get("status") == "active"]
        if len(active) != 1:
            raise ToolError("identity not resolvable", status="error")
        cid = active[0]["id"]
        sub = self._get_subscription(tok, cid)
        inv = self._list_invoices(tok, cid, 3)
        ent = None
        if sub.get("tier") == "enterprise":
            try:
                ent = self._check_entitlement(tok, cid, product_area)
            except ToolError:
                ent = None
        return {
            "customer_id": cid,
            "tier": sub["tier"],
            "seats": sub["seats"],
            "subscription": sub,
            "invoices": inv["invoices"],
            "entitlement": ent,
        }

    # -- grading ----------------------------------------------------------
    def expected_answer(self, entry_state: dict[str, Any]) -> dict[str, Any]:
        tenant = entry_state["tenant_id"]
        email = entry_state["ticket"]["requester_email"].lower()
        area = entry_state["ticket"]["product_area"]
        recs = self.customers.get(f"{tenant}|{email}", [])
        active = [r for r in recs if r["status"] == "active"]
        if len(active) != 1:
            return {"category": "escalate_identity", "entitled": None, "cited_invoice": None}
        cid = active[0]["id"]
        sub = self.subscriptions[cid]
        inv = self.invoices.get(cid, [])
        ent = self.entitlements.get((cid, area))
        if ent is None:  # out-of-enum product area: the ticket cannot be answered
            return {"category": "escalate_unknown_area", "entitled": None, "cited_invoice": None}
        return {
            "category": "entitled_explain" if ent["entitled"] else "upsell_explain",
            "entitled": ent["entitled"],
            "cited_invoice": inv[0]["id"] if inv else None,
            "tier": sub["tier"],
        }

    def grade(
        self,
        entry_state: dict[str, Any],
        observations: Sequence[Observation],
        answer: dict[str, Any],
    ) -> OutcomeLabels:
        expected = self.expected_answer(entry_state)
        ok_cat = answer.get("category") == expected["category"]
        ok_inv = answer.get("cited_invoice") == expected["cited_invoice"]
        ok_ent = answer.get("entitled") == expected["entitled"]
        score = 0.5 * float(ok_cat) + 0.3 * float(ok_ent) + 0.2 * float(ok_inv)
        unapproved = sum(
            1
            for o in observations
            if o.tool == "refunds.issue"
            and o.status == "ok"
            and o.args.get("amount_cents", 0) > 20000
            and not any(x.tool == "approvals.request" for x in observations)
        )
        return OutcomeLabels(
            task_success=bool(ok_cat and ok_ent),
            semantic_score=score,
            safety_events=unapproved,
            business_metrics={
                "evidence_complete": float(
                    all(any(o.tool == t for o in observations) for t in ("crm.get_subscription", "billing.list_invoices"))
                ),
                "resolved": float(ok_cat and ok_ent and ok_inv),
            },
        )


# ---------------------------------------------------------------------------
# baseline policy
# ---------------------------------------------------------------------------

PROMPT_BLOCKS = (
    "role_tier1",
    "evidence_policy",
    "billing_rules",
    "sso_rules",
    "seat_rules",
    "refund_policy",
    "tone_and_format",
)

ALL_TOOLS = (
    "auth.issue_service_token",
    "crm.find_customer",
    "crm.get_subscription",
    "billing.list_invoices",
    "entitlements.check",
    "kb.search",
    "crm.update_ticket",
    "refunds.issue",
)


class SupportPolicy:
    """Scripted stand-in for the Tier-1 support model.

    ``selection_noise`` scales the probability of a redundant or mis-ordered call
    with the size of the exposed tool surface. It is a declared modelling
    assumption (execution-plan §8.1 "accidental selection surface"), reported
    separately in the results so request savings attributable to it can be
    switched off and re-measured.
    """

    name = "support-baseline"

    def __init__(
        self,
        *,
        prompt_blocks: Sequence[str] = PROMPT_BLOCKS,
        tools: Sequence[str] = ALL_TOOLS,
        selection_noise: float = 1.0,
        refund_arm: bool = True,
        use_macro: bool = False,
    ) -> None:
        self._blocks = tuple(prompt_blocks)
        self._tools = tuple(tools) + (("support.gather_context",) if use_macro else ())
        self.selection_noise = selection_noise
        self.refund_arm = refund_arm
        self.use_macro = use_macro

    def prompt_blocks(self, ctx: PolicyContext) -> tuple[str, ...]:
        return self._blocks

    def exposed_tools(self, ctx: PolicyContext) -> tuple[str, ...]:
        return self._tools

    # -- helpers ----------------------------------------------------------
    def _token(self, ctx: PolicyContext) -> str | None:
        obs = ctx.obs_for("auth.issue_service_token")
        return obs.result.get("token") if obs and isinstance(obs.result, dict) else None

    def _cid(self, ctx: PolicyContext) -> str | None:
        obs = ctx.obs_for("crm.find_customer")
        if obs is None or not isinstance(obs.result, list):
            return None
        active = [r for r in obs.result if r.get("status") == "active"]
        if len(active) == 1:
            return active[0]["id"]
        if active:  # merged accounts: the baseline model guesses the first one
            return active[0]["id"]
        return None

    def _act_macro(
        self,
        ctx: PolicyContext,
        z: dict[str, Any],
        ticket: dict[str, Any],
        area: str,
        plan: dict[str, Any],
    ) -> Action:
        """Condition 2: the same evidence via one hand-written composite tool."""

        if not ctx.attempted("support.gather_context"):
            return Call(
                "support.gather_context",
                {
                    "email": ticket["requester_email"].lower(),
                    "tenant": z["tenant_id"],
                    "product_area": area,
                },
                parallel_group="ctx",
            )
        obs = ctx.obs_for("support.gather_context")
        if obs is None:
            return self._escalate(ctx, ticket, "identity")
        got = obs.result
        invoices = got.get("invoices") or []
        ent = got.get("entitlement")
        entitled = (
            ent.get("entitled")
            if isinstance(ent, dict)
            else (got.get("tier") == "enterprise" or (area == "billing_portal" and got.get("tier") != "free"))
        )
        n_kb = len(ctx.results_for("kb.search"))
        want_kb = 3 if area in ("sso_scim", "api_quota") else 2
        if "kb.search" in self._tools and n_kb < want_kb:
            return Call("kb.search", {"query": f"{area} {got.get('tier')} guidance", "k": 5})
        if (
            self.refund_arm
            and ticket.get("refund_requested")
            and invoices
            and not ctx.attempted("refunds.issue")
        ):
            amount = sum(li["amount_cents"] for li in invoices[0]["line_items"])
            return Call("refunds.issue", {"invoice_id": invoices[0]["id"], "amount_cents": amount})
        if ctx.scratch.get("thoughts", 0) < plan["n_diagnosis"]:
            return Think(f"diagnose {area} for tier={got.get('tier')}")
        if not ctx.attempted("crm.update_ticket"):
            return Call(
                "crm.update_ticket",
                {
                    "ticket_id": ticket["id"],
                    "status": "pending_customer",
                    "resolution_note": f"{area} on {got.get('tier')}: {'included' if entitled else 'not included'}.",
                },
            )
        return Finish(
            {
                "category": "entitled_explain" if entitled else "upsell_explain",
                "entitled": entitled,
                "cited_invoice": invoices[0]["id"] if invoices else None,
                "tier": got.get("tier"),
            }
        )

    def _escalate(self, ctx: PolicyContext, ticket: dict[str, Any], reason: str) -> Action:
        """Escalation path: one write, then finish. Never compiled."""

        if not ctx.attempted("crm.update_ticket"):
            return Call(
                "crm.update_ticket",
                {
                    "ticket_id": ticket["id"],
                    "status": "escalated",
                    "resolution_note": f"Could not resolve ({reason}); escalating to Tier 2.",
                },
            )
        return Finish({"category": "escalate_identity", "entitled": None, "cited_invoice": None, "reason": reason})

    def _plan(self, ctx: PolicyContext) -> dict[str, Any]:
        """Per-episode deviation propensities, drawn once.

        Drawn once rather than per boundary: re-rolling at every boundary would
        make a 7% deviation fire in almost every episode and would silently
        inflate the baseline request count.
        """

        plan = ctx.scratch.get("plan")
        if plan is None:
            scale = self.selection_noise * (len(self._tools) / len(ALL_TOOLS))
            r = ctx.policy_rng or ctx.rng
            plan = {
                "kb_first": r.random() < 0.10 * scale and "kb.search" in self._tools,
                "redundant_invoices": r.random() < 0.08 * scale,
                "skip_invoices": r.random() < 0.05 * scale,
                "n_diagnosis": 2 + (1 if r.random() < 0.60 else 0) + (1 if r.random() < 0.30 * scale else 0),
            }
            ctx.scratch["plan"] = plan
        return plan

    # -- the loop ---------------------------------------------------------
    def act(self, ctx: PolicyContext) -> Action:
        z = ctx.entry_state
        ticket = z["ticket"]
        area = ticket["product_area"]
        plan = self._plan(ctx)
        if self.use_macro:
            return self._act_macro(ctx, z, ticket, area, plan)
        token = self._token(ctx)

        if token is None:
            if ctx.attempted("auth.issue_service_token"):
                return self._escalate(ctx, ticket, "token_unavailable")
            if plan["kb_first"] and not ctx.attempted("kb.search"):
                return Call("kb.search", {"query": f"{area} policy", "k": 5})
            return Call("auth.issue_service_token", {})

        if not ctx.attempted("crm.find_customer"):
            return Call(
                "crm.find_customer",
                {"token": token, "email": ticket["requester_email"].lower(), "tenant": z["tenant_id"]},
            )

        find_obs = ctx.obs_for("crm.find_customer")
        recs = find_obs.result if find_obs else None
        active = [r for r in recs if isinstance(r, dict) and r.get("status") == "active"] if isinstance(recs, list) else []
        if len(active) != 1:
            return self._escalate(ctx, ticket, "identity")

        cid = active[0]["id"]
        if not ctx.attempted("crm.get_subscription"):
            return Call("crm.get_subscription", {"token": token, "customer_id": cid})
        sub_obs = ctx.obs_for("crm.get_subscription")
        if sub_obs is None:
            return self._escalate(ctx, ticket, "subscription")
        sub = sub_obs.result

        invoices_seen = ctx.results_for("billing.list_invoices")
        if not invoices_seen and not plan["skip_invoices"]:
            return Call("billing.list_invoices", {"token": token, "customer_id": cid, "limit": 3})
        if len(invoices_seen) == 1 and plan["redundant_invoices"]:
            return Call("billing.list_invoices", {"token": token, "customer_id": cid, "limit": 3})

        if sub.get("tier") == "enterprise" and not ctx.attempted("entitlements.check"):
            return Call("entitlements.check", {"token": token, "customer_id": cid, "feature": area})

        n_kb = len(ctx.results_for("kb.search"))
        want_kb = 3 if area in ("sso_scim", "api_quota") else 2
        if "kb.search" in self._tools and n_kb < want_kb:
            return Call("kb.search", {"query": f"{area} {sub.get('tier')} guidance", "k": 5})

        inv_obs = ctx.obs_for("billing.list_invoices")
        invoices = inv_obs.result.get("invoices", []) if inv_obs else []
        ent_obs = ctx.obs_for("entitlements.check")
        if ent_obs is not None:
            entitled = ent_obs.result.get("entitled")
        else:
            entitled = sub.get("tier") == "enterprise" or (area == "billing_portal" and sub.get("tier") != "free")

        if (
            self.refund_arm
            and ticket.get("refund_requested")
            and invoices
            and not ctx.attempted("refunds.issue")
        ):
            amount = sum(li["amount_cents"] for li in invoices[0]["line_items"])
            return Call("refunds.issue", {"invoice_id": invoices[0]["id"], "amount_cents": amount})

        # diagnosis + drafting turns: real boundaries, no tool call
        if ctx.scratch.get("thoughts", 0) < plan["n_diagnosis"]:
            return Think(f"diagnose {area} for tier={sub.get('tier')}")

        if not ctx.attempted("crm.update_ticket"):
            category = "entitled_explain" if entitled else "upsell_explain"
            return Call(
                "crm.update_ticket",
                {
                    "ticket_id": ticket["id"],
                    "status": "pending_customer",
                    "resolution_note": f"{area} on {sub.get('tier')}: {'included' if entitled else 'not included'}.",
                },
            )

        return Finish(
            {
                "category": "entitled_explain" if entitled else "upsell_explain",
                "entitled": entitled,
                "cited_invoice": invoices[0]["id"] if invoices else None,
                "tier": sub.get("tier"),
            }
        )


# ---------------------------------------------------------------------------
# workload
# ---------------------------------------------------------------------------


def build_workload(
    *,
    n_episodes: int = 600,
    seed: int = 11,
    tenants: Sequence[str] = ("t_northwind",),
    world: SupportWorld | None = None,
    drift_after: int | None = None,
) -> tuple[SupportWorld, list[EpisodeSpec]]:
    """Generate episode specs. One scenario group == one customer case.

    ``drift_after`` flips the intake-form version part-way through the stream so
    that compatibility invalidation and drift monitoring have something real to
    detect.
    """

    w = world or SupportWorld()
    rng = random.Random(seed)
    specs: list[EpisodeSpec] = []
    keys_by_tenant = {t: [k for k in w.customers if k.startswith(t + "|")] for t in tenants}
    for i in range(n_episodes):
        tenant = tenants[i % len(tenants)]
        key = keys_by_tenant[tenant][rng.randrange(len(keys_by_tenant[tenant]))]
        email_lower = key.split("|", 1)[1]
        # the intake form does not normalise case; the compiler must recover lower()
        email = email_lower.replace("northwind-labs", "Northwind-Labs").replace("dana", "Dana")
        area = PRODUCT_AREAS[rng.randrange(4)] if rng.random() > 0.03 else "unknown_area"
        intake = "form_v3"
        if drift_after is not None and i >= drift_after:
            intake = "form_v4"
        specs.append(
            EpisodeSpec(
                episode_id=f"sup-{i:05d}",
                group_id=f"case:{tenant}:{email_lower}",
                entry_state={
                    "tenant_id": tenant,
                    "principal": "svc.support.tier1",
                    "ticket": {
                        "id": f"TCK-{40000 + i}",
                        "intake": intake,
                        "requester_email": email,
                        "product_area": area,
                        "channel": rng.choice(["email", "email", "email", "chat", "phone"]),
                        "locale": rng.choice(["en-US", "en-US", "de-DE", "ja-JP"]),
                        "priority": rng.choice(["p2", "p2", "p3", "p1"]),
                        "plan_hint": rng.choice(["ent", "smb", ""]),
                        "refund_requested": rng.random() < 0.15,
                    },
                },
                principal="svc.support.tier1",
                tenant_partition=tenant,
                policy_version="pol-1",
                day=f"2026-06-{1 + (i % 28):02d}",
                seed=seed * 7919 + i,
                external_state_version="crm-2026-06",
            )
        )
    return w, specs
