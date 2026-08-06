"""Demo C — multi-agent incident triage (execution-plan §12.3, use-cases §4).

Two different optimizations, deliberately kept separable:

* **TGWS** routes stable alert families straight to the right specialist, removing
  the coordinator turns that were spent choosing one. This is a request reduction
  that does not depend on any modelling assumption about tool-surface noise: the
  coordinator boundary either happens or it does not.
* **GRC** compiles the read-only evidence bundle *inside* one specialist. A handoff
  is a real semantic transition and acts as a barrier, so no compiled region may span
  one.

``approvals.request`` is declared approval-gated and ``remediation.execute`` is
``WRITE_IRREVERSIBLE``: both are immutable barriers, and every window containing them
dies at Algorithm 2 line 8.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any, Sequence

from guarded_agentic_compaction.schema.traces import ExecutionManifest, OutcomeLabels
from guarded_agentic_compaction.schema.effects import EffectCatalog
from guarded_agentic_compaction.paths import stable_int

from ..framework import (
    Action,
    Call,
    EpisodeSpec,
    Finish,
    HandoffAction,
    Observation,
    PolicyContext,
    Think,
    ToolError,
    World,
)

EFFECTS_PATH = Path(__file__).with_name("effects.yaml")

ENTRY_ALLOWLIST: tuple[str, ...] = (
    "alert_id",
    "service",
    "severity",
    "environment",
    "alert_family",
    "region",
    "runbook_hint",
)

MANIFEST = ExecutionManifest(
    manifest_id="triage-m1",
    commit="demo-c",
    model="sim-gpt-5-2026-04-12",
    prompt_hash="#91de",
    tools_hash="#77aa",
    policy_hash="#2f0c",
    guardrail_hash="#0003",
    effect_catalog_version=EffectCatalog.from_yaml(EFFECTS_PATH).catalog_version,
    entry_contract_version="alert_v5",
    sdk_version="sim-0.4.0",
    tracer_version="agent-compaction/0.5.0",
)

SERVICES = ("checkout", "search", "billing", "auth", "notify")
FAMILIES = ("latency_spike", "error_rate", "deploy_regression", "capacity", "cert_expiry")
SEVERITIES = ("sev1", "sev2", "sev3")
ENVIRONMENTS = ("prod", "staging")
SPECIALISTS = ("log_specialist", "deploy_specialist", "runbook_specialist")

#: The specialist a family should be routed to. TGWS has to *learn* this from the
#: coordinator's historical handoffs; it is never given the table.
FAMILY_SPECIALIST = {
    "latency_spike": "log_specialist",
    "error_rate": "log_specialist",
    "deploy_regression": "deploy_specialist",
    "capacity": "runbook_specialist",
    "cert_expiry": "runbook_specialist",
}

PROMPT_BLOCKS = (
    "coordinator_role",
    "log_playbook",
    "deploy_playbook",
    "runbook_playbook",
    "severity_matrix",
    "approval_policy",
    "comms_style",
)

ALL_TOOLS = (
    "alerts.get",
    "logs.query",
    "deploys.recent",
    "metrics.query",
    "runbooks.lookup",
    "approvals.request",
    "remediation.execute",
    "case.add_note",
)


class TriageWorld(World):
    name = "incident_triage"

    def __init__(self, seed: int = 41) -> None:
        self.alerts: dict[str, dict[str, Any]] = {}
        self.unapproved_actions = 0
        super().__init__(seed)

    def register_tools(self) -> None:
        self.tool("alerts.get", self._alert, latency_ms=30, schema_tokens=90, resource="alerts")
        self.tool("logs.query", self._logs, latency_ms=140, schema_tokens=170, resource="logs")
        self.tool("deploys.recent", self._deploys, latency_ms=70, schema_tokens=130, resource="deploys")
        self.tool("metrics.query", self._metrics, latency_ms=90, schema_tokens=140, resource="metrics")
        self.tool("runbooks.lookup", self._runbook, latency_ms=50, schema_tokens=120, resource="runbooks")
        self.tool("approvals.request", self._approval, latency_ms=200, schema_tokens=130, resource="approvals")
        self.tool("remediation.execute", self._remediate, latency_ms=180, schema_tokens=150, resource="remediation")
        self.tool("case.add_note", self._note, latency_ms=60, schema_tokens=110, resource="cases")
        # condition-2 comparator: the specialist's evidence bundle as one tool
        self.tool(
            "triage.evidence_bundle",
            self._evidence_bundle,
            latency_ms=150,
            schema_tokens=200,
            resource="logs",
        )

    # -- reads ------------------------------------------------------------
    def _alert(self, alert_id: str) -> dict[str, Any]:
        self.effect_log.append("READ_EXTERNAL")
        rec = self.alerts.get(alert_id)
        if rec is None:
            raise ToolError(f"unknown alert {alert_id}")
        return dict(rec)

    def _logs(self, service: str, window_min: int) -> dict[str, Any]:
        self.effect_log.append("READ_EXTERNAL")
        n = 3 + (stable_int((service, window_min), bits=32) % 4)
        return {
            "service": service,
            "window_min": window_min,
            "errors": [{"code": f"E{100 + i}", "count": 10 * (i + 1)} for i in range(n)],
            "top_code": f"E{100}",
        }

    def _deploys(self, service: str) -> dict[str, Any]:
        self.effect_log.append("READ_EXTERNAL")
        return {
            "service": service,
            "deploys": [
                {"id": f"dep_{service[:3]}_{i}", "at": f"2026-06-1{i}", "risk": "high" if i == 0 else "low"}
                for i in range(3)
            ],
            "latest": f"dep_{service[:3]}_0",
        }

    def _metrics(self, service: str, metric: str) -> dict[str, Any]:
        self.effect_log.append("READ_EXTERNAL")
        base = 100 + (stable_int((service, metric), bits=32) % 400)
        return {"service": service, "metric": metric, "p95_ms": base, "p99_ms": base * 2}

    def _runbook(self, service: str, symptom: str) -> dict[str, Any]:
        self.effect_log.append("READ_LOCAL")
        return {
            "service": service,
            "symptom": symptom,
            "runbook_id": f"rb_{symptom[:4]}",
            "steps": ["check saturation", "scale replicas", "notify owner"],
        }

    def _evidence_bundle(self, service: str, family: str) -> dict[str, Any]:
        out: dict[str, Any] = {"service": service, "family": family}
        for tool in _required_evidence(family):
            if tool == "logs.query":
                out["logs"] = self._logs(service, 30)
            elif tool == "deploys.recent":
                out["deploys"] = self._deploys(service)
            elif tool == "metrics.query":
                out["metrics"] = self._metrics(service, "latency")
            elif tool == "runbooks.lookup":
                out["runbook"] = self._runbook(service, family)
        return out

    # -- barriers ---------------------------------------------------------
    def _approval(self, action: str, justification: str) -> dict[str, Any]:
        self.effect_log.append("WRITE_IRREVERSIBLE")
        self.committed.append({"op": "approval_request", "action": action})
        return {
            "approved": True,
            "approval_id": f"ap_{stable_int(action, bits=32) % 9999:04d}",
            "scope": action,
        }

    def _remediate(self, action: str, approval_id: str | None = None) -> dict[str, Any]:
        self.effect_log.append("WRITE_IRREVERSIBLE")
        if not approval_id:
            self.unapproved_actions += 1
        self.committed.append({"op": "remediate", "action": action, "approval_id": approval_id})
        return {"ok": True, "action": action}

    def _note(self, case_id: str, text: str) -> dict[str, Any]:
        self.effect_log.append("WRITE_IRREVERSIBLE")
        self.committed.append({"op": "note", "case_id": case_id})
        return {"ok": True}

    # -- grading ----------------------------------------------------------
    def expected(self, entry_state: dict[str, Any]) -> dict[str, Any]:
        family = entry_state["alert_family"]
        return {
            "specialist": FAMILY_SPECIALIST[family],
            "classification": family,
            "evidence": _required_evidence(family),
        }

    def grade(
        self,
        entry_state: dict[str, Any],
        observations: Sequence[Observation],
        answer: dict[str, Any],
    ) -> OutcomeLabels:
        exp = self.expected(entry_state)
        tools_used = {o.tool for o in observations if o.status == "ok"}
        needed = set(exp["evidence"])
        if "triage.evidence_bundle" in tools_used:
            # the hand-written bundle performs exactly the required reads internally
            tools_used |= needed
        completeness = len(needed & tools_used) / max(1, len(needed))
        right_specialist = 1.0 if answer.get("specialist") == exp["specialist"] else 0.0
        right_class = 1.0 if answer.get("classification") == exp["classification"] else 0.0
        score = 0.4 * completeness + 0.3 * right_specialist + 0.3 * right_class
        return OutcomeLabels(
            task_success=bool(completeness >= 0.99 and right_class and right_specialist),
            semantic_score=score,
            safety_events=self.unapproved_actions,
            business_metrics={
                "evidence_completeness": completeness,
                "correct_specialist": right_specialist,
                "correct_classification": right_class,
            },
        )


def _required_evidence(family: str) -> tuple[str, ...]:
    if family in ("latency_spike", "error_rate"):
        return ("logs.query", "metrics.query")
    if family == "deploy_regression":
        return ("deploys.recent", "logs.query")
    return ("runbooks.lookup", "metrics.query")


class TriagePolicy:
    """Coordinator + specialists, with the coordinator's choice learnable at entry."""

    name = "triage-baseline"

    def __init__(
        self,
        *,
        prompt_blocks: Sequence[str] = PROMPT_BLOCKS,
        tools: Sequence[str] = ALL_TOOLS,
        selection_noise: float = 1.0,
        route_to: str | None = None,
        use_macro: bool = False,
    ) -> None:
        self._blocks = tuple(prompt_blocks)
        self._tools = tuple(tools) + (("triage.evidence_bundle",) if use_macro else ())
        self.use_macro = use_macro
        self.selection_noise = selection_noise
        #: When TGWS supplies a route, the coordinator turns are skipped and the
        #: episode starts inside the specialist.
        self.route_to = route_to

    def prompt_blocks(self, ctx: PolicyContext) -> tuple[str, ...]:
        return self._blocks

    def exposed_tools(self, ctx: PolicyContext) -> tuple[str, ...]:
        return self._tools

    def _plan(self, ctx: PolicyContext) -> dict[str, Any]:
        plan = ctx.scratch.get("plan")
        if plan is None:
            r = ctx.policy_rng or ctx.rng
            scale = self.selection_noise * (len(self._tools) / len(ALL_TOOLS))
            plan = {
                "coordinator_turns": 1 + (1 if r.random() < 0.55 else 0) + (1 if r.random() < 0.2 * scale else 0),
                "extra_metric": r.random() < 0.2,
                "misroute": r.random() < 0.07,
                "synthesis_turns": 1 + (1 if r.random() < 0.45 else 0),
                "remediate": r.random() < 0.5,
            }
            ctx.scratch["plan"] = plan
        return plan

    def act(self, ctx: PolicyContext) -> Action:
        z = ctx.entry_state
        plan = self._plan(ctx)
        family = z["alert_family"]
        target = self.route_to or FAMILY_SPECIALIST[family]
        if plan["misroute"] and self.route_to is None:
            target = SPECIALISTS[(SPECIALISTS.index(FAMILY_SPECIALIST[family]) + 1) % len(SPECIALISTS)]

        # ---- coordinator phase -----------------------------------------
        if ctx.agent == "root":
            if self.route_to is not None:
                # TGWS route: hand off immediately, no coordinator deliberation
                return HandoffAction(self.route_to, reason="tgws_route")
            if not ctx.attempted("alerts.get"):
                return Call("alerts.get", {"alert_id": z["alert_id"]})
            if ctx.scratch.get("thoughts", 0) < plan["coordinator_turns"]:
                return Think(f"assess {family} on {z['service']}")
            return HandoffAction(target, reason="coordinator_choice")

        # ---- specialist phase ------------------------------------------
        if self.use_macro:
            if not ctx.attempted("triage.evidence_bundle"):
                return Call(
                    "triage.evidence_bundle",
                    {"service": z["service"], "family": family},
                    parallel_group="ev",
                )
        needed = () if self.use_macro else _required_evidence(family)
        for tool in needed:
            if tool in self._tools and not ctx.attempted(tool):
                return Call(tool, _args_for(tool, z))
        if plan["extra_metric"] and "metrics.query" in self._tools and len(ctx.results_for("metrics.query")) < 2:
            return Call("metrics.query", {"service": z["service"], "metric": "saturation"})

        if ctx.scratch.get("thoughts", 0) < plan["coordinator_turns"] + plan["synthesis_turns"]:
            return Think("synthesise response proposal")

        # ---- barriers: approval then remediation -----------------------
        if plan["remediate"] and "approvals.request" in self._tools:
            if not ctx.attempted("approvals.request"):
                return Call(
                    "approvals.request",
                    {"action": f"scale:{z['service']}", "justification": f"{family} on {z['service']}"},
                )
            appr = ctx.obs_for("approvals.request")
            if appr and not ctx.attempted("remediation.execute"):
                return Call(
                    "remediation.execute",
                    {"action": f"scale:{z['service']}", "approval_id": appr.result["approval_id"]},
                )

        if not ctx.attempted("case.add_note"):
            return Call("case.add_note", {"case_id": z["alert_id"], "text": f"triaged {family}"})

        return Finish(
            {
                "specialist": ctx.agent,
                "classification": family,
                "service": z["service"],
            }
        )


def _args_for(tool: str, z: dict[str, Any]) -> dict[str, Any]:
    if tool == "logs.query":
        return {"service": z["service"], "window_min": 30}
    if tool == "deploys.recent":
        return {"service": z["service"]}
    if tool == "metrics.query":
        return {"service": z["service"], "metric": "latency"}
    if tool == "runbooks.lookup":
        return {"service": z["service"], "symptom": z["alert_family"]}
    return {}


def build_workload(
    *,
    n_episodes: int = 2000,
    seed: int = 53,
    world: TriageWorld | None = None,
) -> tuple[TriageWorld, list[EpisodeSpec]]:
    w = world or TriageWorld()
    rng = random.Random(seed)
    specs: list[EpisodeSpec] = []
    for i in range(n_episodes):
        service = SERVICES[rng.randrange(len(SERVICES))]
        family = FAMILIES[rng.randrange(len(FAMILIES))]
        alert_id = f"al_{i:06d}"
        w.alerts[alert_id] = {
            "alert_id": alert_id,
            "service": service,
            "family": family,
            "severity": rng.choice(SEVERITIES),
            "fired_at": f"2026-06-{1 + (i % 28):02d}T04:00:00",
        }
        specs.append(
            EpisodeSpec(
                episode_id=f"tri-{i:05d}",
                group_id=f"case:{service}:{family}:{i % 200}",
                entry_state={
                    "alert_id": alert_id,
                    "service": service,
                    "severity": w.alerts[alert_id]["severity"],
                    "environment": rng.choice(ENVIRONMENTS),
                    "alert_family": family,
                    "region": rng.choice(["eu-west", "us-east", "ap-south"]),
                    "runbook_hint": family if rng.random() < 0.7 else "",
                },
                principal="svc.oncall",
                tenant_partition="platform",
                policy_version="pol-2",
                day=f"2026-06-{1 + (i % 28):02d}",
                seed=seed * 7211 + i,
                external_state_version="obs-2026-06",
            )
        )
    return w, specs
