"""Demo E world and baseline policy: order-fulfillment exception handling.

This is the hardest shape in the repository, and it exists because the first four
demos do not, between them, exercise three things the compiler claims to handle:

1. **Two independent synthesized branches inside one region.**  ``carrier.track``
   only fires for ``exception_class == "carrier_delay"``; the second shipments page
   only fires when the first page reports ``has_more``.  The compiled region
   therefore has a *variable* call count (5, 6 or 7) and the verifier has to admit
   all three rather than pinning one.

2. **A paginated read that collapses to a bounded ``ForEach``.**  Two artifacts are
   built from the same trace evidence: a straight-line one whose second page is a
   conditional ``CallStep``, and a loop-bearing one whose pagination is a
   ``LoopStep``.  The ``CompactingModel`` adapter must *refuse* the second
   (conformance item 7 of proposal §5.6) and fall back without breaking the run,
   while the outer ``CompactingRunner`` can execute it.

3. **A commitment that always happens.**  Every episode ends with
   ``orders.reschedule`` or ``case.escalate``.  A region can therefore only ever be
   a prefix, and the correct measured outcome is *partial* compaction: the evidence
   turns disappear, the decision turn and the write survive.  Demos A–C all end in a
   read, which flatters the request ratio.

``risk.score`` is a deliberately non-deterministic, undeclared scorer: it is in the
baseline tool surface, it is genuinely useful to the model, and it can never enter a
region.  ``refunds.issue_credit`` is an approval barrier that a prior approval in
the same case never licenses.
"""

from __future__ import annotations

import hashlib
import random
from pathlib import Path
from typing import Any, Sequence

from guarded_agentic_compaction.paths import stable_int
from guarded_agentic_compaction.schema.effects import EffectCatalog
from guarded_agentic_compaction.schema.traces import ExecutionManifest, OutcomeLabels

from ..framework import (
    Action,
    Call,
    EpisodeSpec,
    Finish,
    Observation,
    PolicyContext,
    Think,
    ToolError,
    World,
)

EFFECTS_PATH = Path(__file__).with_name("effects.yaml")

#: Entry-state fields the application allows an optimizer to read.
#:
#: ``case.order_ref`` and ``case.id`` are high-cardinality identifiers. They belong
#: here because the region binds them as tool arguments, and they are harmless as
#: TGWS split features because :func:`~guarded_agentic_compaction.tgws.routes._candidate_splits`
#: refuses any feature with more than 24 distinct values.
ENTRY_ALLOWLIST: tuple[str, ...] = (
    "tenant_id",
    "principal",
    "case.id",
    "case.order_ref",
    "case.intake",
    "case.exception_class",
    "case.region",
    "case.customer_tier",
    "case.priority",
    "case.channel",
)

MANIFEST = ExecutionManifest(
    manifest_id="fulfillment-m1",
    commit="demo-e",
    model="sim-gpt-5-2026-04-12",
    prompt_hash="#f10a",
    tools_hash="#3c72",
    policy_hash="#b904",
    guardrail_hash="#0001",
    effect_catalog_version=EffectCatalog.from_yaml(EFFECTS_PATH).catalog_version,
    entry_contract_version="wms_v2",
    sdk_version="sim-0.4.0",
    tracer_version="agent-compaction/0.5.0",
)

TENANTS = ("t_northwind", "t_contoso")
EXCEPTION_CLASSES = ("carrier_delay", "stock_shortfall", "address_invalid", "payment_hold")
REGIONS = ("amer", "emea", "apac")
CUSTOMER_TIERS = ("bronze", "silver", "gold")
SKUS = ("sku-hub-7", "sku-cam-2", "sku-mic-9", "sku-dock-4", "sku-kbd-1")

#: Shipments returned per page by the WMS. Small on purpose: an order with four
#: shipments needs a second page, an order with three does not, and the branch is
#: therefore data-dependent rather than entry-state-dependent.
PAGE_SIZE = 3

#: Per-(tier, region) service policy. Deterministic, local, and cacheable.
SLA_POLICY: dict[tuple[str, str], dict[str, Any]] = {
    (tier, region): {
        "customer_tier": tier,
        "region": region,
        "max_delay_days": {"gold": 4, "silver": 3, "bronze": 2}[tier]
        + {"amer": 0, "emea": 1, "apac": 2}[region],
        "credit_eligible": tier == "gold",
        "escalation_queue": f"ops-{region}-{tier}",
    }
    for tier in CUSTOMER_TIERS
    for region in REGIONS
}


def decide(
    *,
    exception_class: str,
    required_qty: int,
    available: int | None,
    carrier_eta_days: int | None,
    policy: dict[str, Any],
) -> tuple[str, str]:
    """The action the evidence implies. Pure, and shared by world and graders."""

    if exception_class == "carrier_delay":
        if carrier_eta_days is None:
            return "escalate", "carrier_unreachable"
        if carrier_eta_days <= int(policy["max_delay_days"]):
            return "reschedule", "carrier_eta_within_sla"
        return "escalate", "carrier_eta_breach"
    if exception_class == "stock_shortfall":
        if available is None:
            return "escalate", "stock_unknown"
        if available >= required_qty:
            return "reschedule", "stock_available"
        return "escalate", "stock_short"
    if exception_class == "address_invalid":
        return "escalate", "address_unverified"
    if policy["credit_eligible"]:
        return "reschedule", "payment_hold_credit"
    return "escalate", "payment_hold_no_credit"


class FulfillmentWorld(World):
    name = "fulfillment"

    def __init__(self, seed: int = 13, n_orders: int = 900) -> None:
        self.n_orders = n_orders
        self.orders: dict[str, dict[str, Any]] = {}
        self.shipments: dict[str, list[dict[str, Any]]] = {}
        self.inventory: dict[tuple[str, str], dict[str, Any]] = {}
        self.carrier: dict[str, dict[str, Any]] = {}
        self.tokens: set[str] = set()
        self.approvals: set[str] = set()
        super().__init__(seed)
        self._build_data()

    # -- data -------------------------------------------------------------
    def _build_data(self) -> None:
        rng = random.Random(self.seed * 131 + 7)
        for i in range(self.n_orders):
            ref = f"ORD-2026-{i:06d}"
            region = REGIONS[i % len(REGIONS)]
            warehouse = f"wh-{region}-{1 + (i % 3)}"
            tracking = f"trk_{hashlib.sha1(ref.encode()).hexdigest()[:10]}"
            n_items = 1 + int(rng.random() * 3)
            line_items = []
            for j in range(n_items):
                sku = SKUS[(i + j) % len(SKUS)]
                qty = 1 + int(rng.random() * 6)
                line_items.append(
                    {"sku": sku, "qty": qty, "amount_cents": 1900 * qty + 500 * j}
                )
            self.orders[ref] = {
                "order_ref": ref,
                "warehouse": warehouse,
                "tracking_id": tracking,
                "promised_date": f"2026-08-{1 + (i % 27):02d}",
                "status": "exception",
                "line_items": line_items,
            }
            # 1..5 shipments -> one or two pages at PAGE_SIZE == 3
            n_ship = 1 + int(rng.random() * 5)
            self.shipments[ref] = [
                {
                    "shipment_id": f"shp_{i:06d}_{k}",
                    "leg": k,
                    "carrier": "globex" if k % 2 == 0 else "acme-freight",
                    "state": "in_transit" if k else "picked",
                }
                for k in range(n_ship)
            ]
            for item in line_items:
                key = (item["sku"], warehouse)
                if key not in self.inventory:
                    # Deterministic availability that straddles the requested qty so
                    # the stock branch is genuinely decided by the evidence.
                    available = stable_int(key, bits=16) % 9
                    self.inventory[key] = {
                        "sku": item["sku"],
                        "warehouse": warehouse,
                        "available": available,
                        "reserved": available // 3,
                    }
            eta = 1 + stable_int((tracking, "eta"), bits=16) % 7
            self.carrier[tracking] = {
                "tracking_id": tracking,
                "status": "exception" if eta > 4 else "in_transit",
                "eta_days": eta,
                "last_scan": f"hub-{region}",
            }

    def order_ref_at(self, index: int) -> str:
        return f"ORD-2026-{index % self.n_orders:06d}"

    # -- tools ------------------------------------------------------------
    def register_tools(self) -> None:
        self.tool("auth.issue_ops_token", self._issue_token, latency_ms=30, schema_tokens=60, resource="auth")
        self.tool("orders.get", self._orders_get, latency_ms=65, schema_tokens=170, resource="orders")
        self.tool("shipments.list_page", self._list_page, latency_ms=70, schema_tokens=150, resource="shipments")
        self.tool("inventory.check", self._inventory_check, latency_ms=55, schema_tokens=130, resource="inventory")
        self.tool("carrier.track", self._carrier_track, latency_ms=95, schema_tokens=140, resource="carrier")
        self.tool("sla.policy", self._sla_policy, latency_ms=20, schema_tokens=110, resource="policy")
        self.tool("risk.score", self._risk_score, latency_ms=140, schema_tokens=120, resource="risk")
        self.tool("orders.reschedule", self._reschedule, latency_ms=85, schema_tokens=150, resource="orders")
        self.tool("case.escalate", self._escalate, latency_ms=60, schema_tokens=140, resource="cases")
        self.tool("refunds.issue_credit", self._issue_credit, latency_ms=110, schema_tokens=150, resource="billing")
        self.tool(
            "fulfillment.evidence_bundle",
            self._evidence_bundle,
            latency_ms=105,
            schema_tokens=200,
            resource="orders",
        )

    def _issue_token(self) -> dict[str, Any]:
        n = self.quota.get("auth.issue_ops_token", 0)
        tok = f"ops_{hashlib.sha1(f'{self.seed}:{n}'.encode()).hexdigest()[:8]}"
        self.tokens.add(tok)
        self.effect_log.append("READ_EXTERNAL")
        return {"token": tok, "scope": "fulfillment.read", "expires_in": 600}

    def _require_token(self, token: str) -> None:
        if token not in self.tokens:
            raise ToolError("invalid ops token", status="error")

    def _orders_get(self, token: str, order_ref: str) -> dict[str, Any]:
        self._require_token(token)
        self.effect_log.append("READ_EXTERNAL")
        order = self.orders.get(order_ref)
        if order is None:
            raise ToolError(f"unknown order {order_ref}", status="error")
        return {k: (list(v) if isinstance(v, list) else v) for k, v in order.items()}

    def _list_page(self, token: str, order_ref: str, page: int = 0) -> dict[str, Any]:
        self._require_token(token)
        self.effect_log.append("READ_EXTERNAL")
        if order_ref not in self.shipments:
            raise ToolError(f"unknown order {order_ref}", status="error")
        if not isinstance(page, int) or page < 0 or page > 8:
            raise ToolError(f"bad page {page!r}", status="error")
        all_ship = self.shipments[order_ref]
        start = page * PAGE_SIZE
        window = all_ship[start : start + PAGE_SIZE]
        return {
            "order_ref": order_ref,
            "page": page,
            "shipments": [dict(s) for s in window],
            "has_more": start + PAGE_SIZE < len(all_ship),
        }

    def _inventory_check(self, token: str, sku: str, warehouse: str) -> dict[str, Any]:
        self._require_token(token)
        self.effect_log.append("READ_EXTERNAL")
        rec = self.inventory.get((sku, warehouse))
        if rec is None:
            raise ToolError(f"no inventory record for {sku}@{warehouse}", status="error")
        return dict(rec)

    def _carrier_track(self, token: str, tracking_id: str) -> dict[str, Any]:
        self._require_token(token)
        self.effect_log.append("READ_EXTERNAL")
        rec = self.carrier.get(tracking_id)
        if rec is None:
            raise ToolError(f"unknown tracking id {tracking_id}", status="error")
        return dict(rec)

    def _sla_policy(self, customer_tier: str, region: str) -> dict[str, Any]:
        self.effect_log.append("READ_LOCAL")
        rec = SLA_POLICY.get((customer_tier, region))
        if rec is None:
            raise ToolError(f"no policy for {customer_tier}/{region}", status="error")
        return dict(rec)

    def _risk_score(self, order_ref: str) -> dict[str, Any]:
        """Non-deterministic by construction: cannot satisfy replay equivalence."""

        self.effect_log.append("UNKNOWN")
        return {
            "order_ref": order_ref,
            "score": round(self.rng.random(), 4),
            "model": f"risk-ens-{self.rng.randint(1, 3)}",
        }

    def _reschedule(self, order_ref: str, new_date: str) -> dict[str, Any]:
        self.effect_log.append("WRITE_IRREVERSIBLE")
        self.committed.append({"op": "reschedule", "order_ref": order_ref, "new_date": new_date})
        return {"ok": True, "order_ref": order_ref, "new_date": new_date, "version": 4}

    def _escalate(self, case_id: str, queue: str, reason_code: str) -> dict[str, Any]:
        self.effect_log.append("WRITE_IRREVERSIBLE")
        self.committed.append({"op": "escalate", "case_id": case_id, "queue": queue})
        return {"ok": True, "case_id": case_id, "queue": queue, "reason_code": reason_code}

    def _issue_credit(self, order_ref: str, amount_cents: int) -> dict[str, Any]:
        self.effect_log.append("WRITE_IRREVERSIBLE")
        self.committed.append({"op": "credit", "order_ref": order_ref, "amount_cents": amount_cents})
        return {"ok": True, "credit_id": f"cr_{order_ref[-6:]}", "amount_cents": amount_cents}

    def _evidence_bundle(self, order_ref: str, exception_class: str) -> dict[str, Any]:
        """Condition 2 comparator: the same reads behind one hand-written tool."""

        tok = self._issue_token()["token"]
        order = self._orders_get(tok, order_ref)
        page0 = self._list_page(tok, order_ref, 0)
        shipments = list(page0["shipments"])
        if page0["has_more"]:
            shipments.extend(self._list_page(tok, order_ref, 1)["shipments"])
        first = order["line_items"][0]
        inventory = self._inventory_check(tok, first["sku"], order["warehouse"])
        carrier = (
            self._carrier_track(tok, order["tracking_id"])
            if exception_class == "carrier_delay"
            else None
        )
        return {
            "order": order,
            "shipment_count": len(shipments),
            "inventory": inventory,
            "carrier": carrier,
        }

    # -- grading ----------------------------------------------------------
    def expected(self, entry_state: dict[str, Any]) -> dict[str, Any]:
        case = entry_state["case"]
        ref = case["order_ref"]
        order = self.orders[ref]
        first = order["line_items"][0]
        inv = self.inventory[(first["sku"], order["warehouse"])]
        policy = SLA_POLICY[(case["customer_tier"], case["region"])]
        carrier = self.carrier[order["tracking_id"]]
        action, reason = decide(
            exception_class=case["exception_class"],
            required_qty=int(first["qty"]),
            available=int(inv["available"]),
            carrier_eta_days=int(carrier["eta_days"]),
            policy=policy,
        )
        return {
            "action": action,
            "reason_code": reason,
            "shipment_count": len(self.shipments[ref]),
            "escalation_queue": policy["escalation_queue"],
        }

    def grade(
        self,
        entry_state: dict[str, Any],
        observations: Sequence[Observation],
        answer: dict[str, Any],
    ) -> OutcomeLabels:
        exp = self.expected(entry_state)
        ok_action = answer.get("action") == exp["action"]
        ok_reason = answer.get("reason_code") == exp["reason_code"]
        ok_count = int(answer.get("shipment_count") or -1) == exp["shipment_count"]
        score = 0.5 * float(ok_action) + 0.3 * float(ok_reason) + 0.2 * float(ok_count)

        writes = [
            o
            for o in observations
            if o.tool in ("orders.reschedule", "case.escalate", "refunds.issue_credit")
            and o.status == "ok"
        ]
        unapproved_credit = sum(
            1 for o in observations if o.tool == "refunds.issue_credit" and o.status == "ok"
        )
        # More than one commitment for a single exception case is a double-write.
        double_write = max(0, len(writes) - 1)
        return OutcomeLabels(
            task_success=bool(ok_action and ok_reason),
            semantic_score=score,
            safety_events=unapproved_credit + double_write,
            business_metrics={
                "evidence_complete": float(
                    any(o.tool == "orders.get" for o in observations)
                    and any(o.tool == "shipments.list_page" for o in observations)
                ),
                "committed_once": float(len(writes) == 1),
                "pagination_correct": float(ok_count),
            },
        )


# ---------------------------------------------------------------------------
# baseline policy
# ---------------------------------------------------------------------------

PROMPT_BLOCKS = (
    "role_fulfillment_ops",
    "evidence_policy",
    "carrier_rules",
    "stock_rules",
    "address_rules",
    "payment_rules",
    "commitment_policy",
)

#: Which prompt blocks a route actually needs: its own rule block plus the protected
#: ones. The generalist carries all seven.
#:
#: ``evidence_policy`` is protected, and it was not in the first hand-written version
#: of this table. Dropping it cost 0.05 mean quality on the address_invalid route in a
#: live run — the model no longer knew to follow ``has_more`` and under-counted the
#: shipments. That is precisely the failure TGWS pruning exists to prevent: the greedy
#: pruner proposes a removal, *measures* it on the leaf's development episodes, and
#: keeps it only under quality and safety non-inferiority. A hand-specified surface has
#: no such check, which is why the protected set is declared rather than inferred.
ROUTE_BLOCKS: dict[str, tuple[str, ...]] = {
    "carrier_delay": (
        "role_fulfillment_ops",
        "evidence_policy",
        "carrier_rules",
        "commitment_policy",
    ),
    "stock_shortfall": (
        "role_fulfillment_ops",
        "evidence_policy",
        "stock_rules",
        "commitment_policy",
    ),
    "address_invalid": (
        "role_fulfillment_ops",
        "evidence_policy",
        "address_rules",
        "commitment_policy",
    ),
    "payment_hold": (
        "role_fulfillment_ops",
        "evidence_policy",
        "payment_rules",
        "commitment_policy",
    ),
}

ALL_TOOLS = (
    "auth.issue_ops_token",
    "orders.get",
    "shipments.list_page",
    "inventory.check",
    "carrier.track",
    "sla.policy",
    "risk.score",
    "orders.reschedule",
    "case.escalate",
    "refunds.issue_credit",
)

#: Minimal tool surface per route, as observed in the supporting traces.
ROUTE_TOOLS: dict[str, tuple[str, ...]] = {
    "carrier_delay": (
        "auth.issue_ops_token",
        "orders.get",
        "shipments.list_page",
        "carrier.track",
        "sla.policy",
        "orders.reschedule",
        "case.escalate",
    ),
    "stock_shortfall": (
        "auth.issue_ops_token",
        "orders.get",
        "shipments.list_page",
        "inventory.check",
        "sla.policy",
        "orders.reschedule",
        "case.escalate",
    ),
    "address_invalid": (
        "auth.issue_ops_token",
        "orders.get",
        "shipments.list_page",
        "sla.policy",
        "case.escalate",
    ),
    "payment_hold": (
        "auth.issue_ops_token",
        "orders.get",
        "shipments.list_page",
        "sla.policy",
        "orders.reschedule",
        "case.escalate",
    ),
}

PROTECTED_TOOLS = ("refunds.issue_credit", "case.escalate")
PROTECTED_BLOCKS = ("role_fulfillment_ops", "evidence_policy", "commitment_policy")


class FulfillmentPolicy:
    """Scripted stand-in for the fulfillment-ops model.

    The deviations are deliberate: a risk-score detour, an occasional redundant
    inventory read, an occasional skipped second page (which produces a *wrong*
    shipment count rather than a tool error), and a variable number of diagnosis
    turns. Without them the request ratio and the gate are both unfalsifiable.
    """

    name = "fulfillment-baseline"

    def __init__(
        self,
        *,
        prompt_blocks: Sequence[str] = PROMPT_BLOCKS,
        tools: Sequence[str] = ALL_TOOLS,
        selection_noise: float = 1.0,
        use_macro: bool = False,
    ) -> None:
        self._blocks = tuple(prompt_blocks)
        self._tools = tuple(tools) + (("fulfillment.evidence_bundle",) if use_macro else ())
        self.selection_noise = selection_noise
        self.use_macro = use_macro

    def prompt_blocks(self, ctx: PolicyContext) -> tuple[str, ...]:
        return self._blocks

    def exposed_tools(self, ctx: PolicyContext) -> tuple[str, ...]:
        return self._tools

    # -- helpers ----------------------------------------------------------
    def _token(self, ctx: PolicyContext) -> str | None:
        obs = ctx.obs_for("auth.issue_ops_token")
        return obs.result.get("token") if obs and isinstance(obs.result, dict) else None

    def _plan(self, ctx: PolicyContext) -> dict[str, Any]:
        plan = ctx.scratch.get("plan")
        if plan is None:
            scale = self.selection_noise * (len(self._tools) / len(ALL_TOOLS))
            r = ctx.policy_rng or ctx.rng
            plan = {
                "risk_detour": r.random() < 0.12 * scale and "risk.score" in self._tools,
                "redundant_inventory": r.random() < 0.07 * scale,
                "skip_second_page": r.random() < 0.06 * scale,
                "n_diagnosis": 1 + (1 if r.random() < 0.55 else 0) + (1 if r.random() < 0.25 * scale else 0),
            }
            ctx.scratch["plan"] = plan
        return plan

    def _pages(self, ctx: PolicyContext) -> list[dict[str, Any]]:
        return [r for r in ctx.results_for("shipments.list_page") if isinstance(r, dict)]

    # -- the loop ---------------------------------------------------------
    def act(self, ctx: PolicyContext) -> Action:
        z = ctx.entry_state
        case = z["case"]
        ref = case["order_ref"]
        plan = self._plan(ctx)

        if self.use_macro:
            return self._act_macro(ctx, case, plan)

        token = self._token(ctx)
        if token is None:
            if ctx.attempted("auth.issue_ops_token"):
                return self._bail(ctx, case, "token_unavailable")
            return Call("auth.issue_ops_token", {})

        if not ctx.attempted("orders.get"):
            return Call("orders.get", {"token": token, "order_ref": ref})
        order_obs = ctx.obs_for("orders.get")
        if order_obs is None:
            return self._bail(ctx, case, "order_unavailable")
        order = order_obs.result

        pages = self._pages(ctx)
        if not pages:
            return Call("shipments.list_page", {"token": token, "order_ref": ref, "page": 0})
        if pages[-1].get("has_more") and len(pages) < 3 and not plan["skip_second_page"]:
            return Call(
                "shipments.list_page",
                {"token": token, "order_ref": ref, "page": len(pages)},
            )

        first = order["line_items"][0]
        need_inventory = case["exception_class"] == "stock_shortfall"
        inv_seen = ctx.results_for("inventory.check")
        if need_inventory and not inv_seen:
            return Call(
                "inventory.check",
                {"token": token, "sku": first["sku"], "warehouse": order["warehouse"]},
            )
        if need_inventory and len(inv_seen) == 1 and plan["redundant_inventory"]:
            return Call(
                "inventory.check",
                {"token": token, "sku": first["sku"], "warehouse": order["warehouse"]},
            )

        if case["exception_class"] == "carrier_delay" and not ctx.attempted("carrier.track"):
            return Call("carrier.track", {"token": token, "tracking_id": order["tracking_id"]})

        if not ctx.attempted("sla.policy"):
            return Call(
                "sla.policy",
                {"customer_tier": case["customer_tier"], "region": case["region"]},
            )

        if plan["risk_detour"] and not ctx.attempted("risk.score"):
            return Call("risk.score", {"order_ref": ref})

        if ctx.scratch.get("thoughts", 0) < plan["n_diagnosis"]:
            return Think(f"weigh {case['exception_class']} against policy")

        action, reason, count = self._conclude(ctx, case, order)
        if not (ctx.attempted("orders.reschedule") or ctx.attempted("case.escalate")):
            if action == "reschedule":
                return Call(
                    "orders.reschedule",
                    {"order_ref": ref, "new_date": order["promised_date"]},
                )
            policy_obs = ctx.obs_for("sla.policy")
            queue = (policy_obs.result or {}).get("escalation_queue", "ops-default") if policy_obs else "ops-default"
            return Call(
                "case.escalate",
                {"case_id": case["id"], "queue": queue, "reason_code": reason},
            )
        return Finish({"action": action, "reason_code": reason, "shipment_count": count})

    def _conclude(
        self, ctx: PolicyContext, case: dict[str, Any], order: dict[str, Any]
    ) -> tuple[str, str, int]:
        pages = self._pages(ctx)
        count = sum(len(p.get("shipments") or []) for p in pages)
        first = order["line_items"][0]
        inv_obs = ctx.obs_for("inventory.check")
        carrier_obs = ctx.obs_for("carrier.track")
        policy_obs = ctx.obs_for("sla.policy")
        policy = policy_obs.result if policy_obs else {"max_delay_days": 0, "credit_eligible": False}
        action, reason = decide(
            exception_class=case["exception_class"],
            required_qty=int(first["qty"]),
            available=int(inv_obs.result["available"]) if inv_obs else None,
            carrier_eta_days=int(carrier_obs.result["eta_days"]) if carrier_obs else None,
            policy=policy,
        )
        return action, reason, count

    def _act_macro(self, ctx: PolicyContext, case: dict[str, Any], plan: dict[str, Any]) -> Action:
        ref = case["order_ref"]
        if not ctx.attempted("fulfillment.evidence_bundle"):
            return Call(
                "fulfillment.evidence_bundle",
                {"order_ref": ref, "exception_class": case["exception_class"]},
                parallel_group="bundle",
            )
        obs = ctx.obs_for("fulfillment.evidence_bundle")
        if obs is None:
            return self._bail(ctx, case, "bundle_unavailable")
        bundle = obs.result
        if not ctx.attempted("sla.policy"):
            return Call(
                "sla.policy",
                {"customer_tier": case["customer_tier"], "region": case["region"]},
            )
        policy_obs = ctx.obs_for("sla.policy")
        policy = policy_obs.result if policy_obs else {"max_delay_days": 0, "credit_eligible": False}
        first = bundle["order"]["line_items"][0]
        action, reason = decide(
            exception_class=case["exception_class"],
            required_qty=int(first["qty"]),
            available=int(bundle["inventory"]["available"]) if bundle.get("inventory") else None,
            carrier_eta_days=int(bundle["carrier"]["eta_days"]) if bundle.get("carrier") else None,
            policy=policy,
        )
        if ctx.scratch.get("thoughts", 0) < plan["n_diagnosis"]:
            return Think("weigh bundle against policy")
        if not (ctx.attempted("orders.reschedule") or ctx.attempted("case.escalate")):
            if action == "reschedule":
                return Call(
                    "orders.reschedule",
                    {"order_ref": ref, "new_date": bundle["order"]["promised_date"]},
                )
            return Call(
                "case.escalate",
                {
                    "case_id": case["id"],
                    "queue": policy.get("escalation_queue", "ops-default"),
                    "reason_code": reason,
                },
            )
        return Finish(
            {"action": action, "reason_code": reason, "shipment_count": bundle["shipment_count"]}
        )

    def _bail(self, ctx: PolicyContext, case: dict[str, Any], reason: str) -> Action:
        if not ctx.attempted("case.escalate"):
            return Call(
                "case.escalate",
                {"case_id": case["id"], "queue": "ops-default", "reason_code": reason},
            )
        return Finish({"action": "escalate", "reason_code": reason, "shipment_count": 0})


# ---------------------------------------------------------------------------
# workload
# ---------------------------------------------------------------------------


def build_workload(
    *,
    n_episodes: int = 600,
    seed: int = 17,
    tenants: Sequence[str] = ("t_northwind",),
    world: FulfillmentWorld | None = None,
    drift_after: int | None = None,
) -> tuple[FulfillmentWorld, list[EpisodeSpec]]:
    """Generate episode specs. One scenario group == one order.

    ``drift_after`` flips the WMS intake contract part-way through the stream so
    that hard-guard invalidation has something real to reject.
    """

    w = world or FulfillmentWorld()
    rng = random.Random(seed)
    specs: list[EpisodeSpec] = []
    for i in range(n_episodes):
        tenant = tenants[i % len(tenants)]
        ref = w.order_ref_at(rng.randrange(w.n_orders))
        order = w.orders[ref]
        region = order["warehouse"].split("-")[1]
        intake = "wms_v2"
        if drift_after is not None and i >= drift_after:
            intake = "wms_v3"
        specs.append(
            EpisodeSpec(
                episode_id=f"ful-{i:05d}",
                group_id=f"order:{tenant}:{ref}",
                entry_state={
                    "tenant_id": tenant,
                    "principal": "svc.fulfillment.ops",
                    "case": {
                        "id": f"FUL-{70000 + i}",
                        "intake": intake,
                        "order_ref": ref,
                        "exception_class": EXCEPTION_CLASSES[rng.randrange(len(EXCEPTION_CLASSES))],
                        "region": region,
                        "customer_tier": CUSTOMER_TIERS[rng.randrange(len(CUSTOMER_TIERS))],
                        "priority": rng.choice(["p2", "p2", "p1", "p3"]),
                        "channel": rng.choice(["wms", "wms", "csr", "api"]),
                    },
                },
                principal="svc.fulfillment.ops",
                tenant_partition=tenant,
                policy_version="pol-e1",
                day=f"2026-07-{1 + (i % 28):02d}",
                seed=seed * 7717 + i,
                external_state_version="wms-2026-07",
            )
        )
    return w, specs
