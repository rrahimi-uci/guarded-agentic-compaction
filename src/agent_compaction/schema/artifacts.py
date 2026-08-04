"""Artifact schema: ``a = (P, H, q, η, V, M)`` (proposal Eq. 6).

Everything a reviewer, a runtime, and an auditor needs is in one JSON-serialisable
object: the program, the hard guard, the calibrated gate, the verifier, the
compatibility manifest, the evidence that justified promotion, and the lifecycle
state with its rollback target.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Iterable, Sequence

from typing import TYPE_CHECKING

from .traces import ExecutionManifest, resolve_path

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..grc.program import Predicate, Program

# The program IR lives in `grc.program` and imports the DSL, which imports these
# schemas. Deferring the import to the two functions that need it at runtime keeps
# `import agent_compaction.grc.program` from cycling back into a half-built module.

__all__ = [
    "Lifecycle",
    "Hull",
    "GuardClause",
    "HardGuard",
    "OutputClause",
    "Verifier",
    "GateModel",
    "Gate",
    "Evidence",
    "Artifact",
    "RouteConfig",
    "DispatchOutcome",
]


def _predicate_from_dict(d: dict[str, Any]) -> "Predicate":
    from ..grc.program import predicate_from_dict

    return predicate_from_dict(d)


def _program_from_dict(d: dict[str, Any]) -> "Program":
    from ..grc.program import program_from_dict

    return program_from_dict(d)


class Lifecycle(str, Enum):
    DISCOVERED = "discovered"
    SYNTHESIZED = "synthesized"
    REPLAY_VALIDATED = "replay_validated"
    SHADOW = "shadow"
    APPROVED = "approved"
    ACTIVE = "active"
    RETIRED = "retired"


class DispatchOutcome(str, Enum):
    COMPACTED = "COMPACTED"
    BASELINE = "BASELINE"
    INCIDENT = "INCIDENT"


# ---------------------------------------------------------------------------
# hard guard
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Hull:
    """A fitted admissible set for one live-in (Algorithm 5 lines 2-4)."""

    kind: str  # interval | enum | regex | any
    low: float | None = None
    high: float | None = None
    values: tuple[Any, ...] = ()
    pattern: str | None = None
    min_len: int | None = None
    max_len: int | None = None

    def contains(self, v: Any) -> bool:
        if self.kind == "any":
            return True
        if self.kind == "interval":
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                return False
            return (self.low is None or v >= self.low) and (self.high is None or v <= self.high)
        if self.kind == "enum":
            return v in self.values
        if self.kind == "regex":
            if not isinstance(v, str):
                return False
            import re

            if self.min_len is not None and len(v) < self.min_len:
                return False
            if self.max_len is not None and len(v) > self.max_len:
                return False
            return self.pattern is None or re.match(self.pattern, v) is not None
        return False

    def pretty(self) -> str:
        if self.kind == "interval":
            return f"∈ [{self.low}, {self.high}]"
        if self.kind == "enum":
            vals = ", ".join(str(v) for v in self.values)
            return f"∈ {{{vals}}}"
        if self.kind == "regex":
            return f"matches {self.pattern} (len {self.min_len}..{self.max_len})"
        return ""

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["values"] = list(self.values)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Hull":
        d = dict(d)
        d["values"] = tuple(d.get("values", ()))
        return cls(**d)


@dataclass(frozen=True, slots=True)
class GuardClause:
    path: str
    type_name: str
    hull: Hull
    required: bool = True
    role: str = "hull"  # hull | isolation | schema_pin

    def check(self, env: Any) -> str | None:
        v = resolve_path(env, self.path)
        if v is None:
            return None if not self.required else f"missing:{self.path}"
        if self.type_name and _type_name(v) != self.type_name:
            return f"type:{self.path}={_type_name(v)}!={self.type_name}"
        if not self.hull.contains(v):
            return f"hull:{self.path}={v!r}"
        return None

    def pretty(self) -> str:
        return f"{self.path} : {self.type_name} {self.hull.pretty()}".rstrip()

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "type_name": self.type_name,
            "hull": self.hull.to_dict(),
            "required": self.required,
            "role": self.role,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "GuardClause":
        return cls(
            path=d["path"],
            type_name=d["type_name"],
            hull=Hull.from_dict(d["hull"]),
            required=d.get("required", True),
            role=d.get("role", "hull"),
        )


def _type_name(v: Any) -> str:
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "str"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "dict"
    return type(v).__name__


@dataclass(slots=True)
class HardGuard:
    """``H``: manifest equality plus typed hulls plus isolation keys."""

    manifest_pins: dict[str, str] = field(default_factory=dict)
    isolation: dict[str, str] = field(default_factory=dict)
    clauses: list[GuardClause] = field(default_factory=list)
    allowed_effects: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ("speculatable", "replayable")

    def evaluate(self, entry_state: Any, context: dict[str, Any] | None = None) -> list[str]:
        """Return the list of violated reasons (empty list == guard satisfied)."""

        reasons: list[str] = []
        ctx = context or {}
        for key, expected in self.manifest_pins.items():
            got = ctx.get(key)
            if got is None:
                reasons.append(f"manifest_missing:{key}")
            elif got != expected:
                reasons.append(f"manifest:{key}")
        for key, expected in self.isolation.items():
            got = ctx.get(key)
            if got != expected:
                reasons.append(f"isolation:{key}")
        env = {"z": entry_state}
        for clause in self.clauses:
            bad = clause.check(env)
            if bad:
                reasons.append(bad)
        return reasons

    def pretty(self) -> str:
        lines = ["guard   " + "  ".join(f"{k}={v}" for k, v in sorted(self.manifest_pins.items()))]
        for k, v in sorted(self.isolation.items()):
            lines.append(f"        {k} = {v!r}   (isolation key)")
        for c in self.clauses:
            lines.append(f"        {c.pretty()}")
        eff = ", ".join(self.allowed_effects)
        caps = " ∧ ".join(self.required_capabilities)
        lines.append(f"        effects ⊆ {{{eff}}}  all {caps}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_pins": self.manifest_pins,
            "isolation": self.isolation,
            "clauses": [c.to_dict() for c in self.clauses],
            "allowed_effects": list(self.allowed_effects),
            "required_capabilities": list(self.required_capabilities),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "HardGuard":
        return cls(
            manifest_pins=d.get("manifest_pins", {}),
            isolation=d.get("isolation", {}),
            clauses=[GuardClause.from_dict(c) for c in d.get("clauses", [])],
            allowed_effects=tuple(d.get("allowed_effects", ())),
            required_capabilities=tuple(d.get("required_capabilities", ("speculatable", "replayable"))),
        )


# ---------------------------------------------------------------------------
# verifier
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OutputClause:
    """One live-out contract clause.

    ``present_iff`` is what use-cases §1 flags as missing from the published
    listing: when a branch makes an output conditional, an unconditional
    ``non_null`` clause would reject the other arm at Algorithm 5 line 10, so the
    contract must be induced per arm.
    """

    name: str
    type_name: str
    non_null: bool = True
    hull: Hull = field(default_factory=lambda: Hull("any"))
    max_len: int | None = None
    min_len: int | None = None
    provenance: tuple[str, ...] = ()
    present_iff: Predicate | None = None

    def check(self, outputs: dict[str, Any], env: Any, provenance: dict[str, set[str]]) -> str | None:
        expected_present = True
        if self.present_iff is not None:
            expected_present = self.present_iff.evaluate(env)
        # `name` may be a dotted path into a live-out object ("subs.tier"), so that
        # the contract can constrain fields as well as whole results.
        value = resolve_path(outputs, self.name) if "." in self.name else outputs.get(self.name)
        if not expected_present:
            return None if value is None else f"unexpected_present:{self.name}"
        if value is None:
            return f"missing:{self.name}" if self.non_null else None
        if self.type_name and _type_name(value) != self.type_name:
            return f"type:{self.name}"
        if isinstance(value, (list, str, dict)):
            if self.max_len is not None and len(value) > self.max_len:
                return f"cardinality:{self.name}"
            if self.min_len is not None and len(value) < self.min_len:
                return f"cardinality:{self.name}"
        if not self.hull.contains(value) and self.hull.kind != "any":
            if not isinstance(value, (list, dict)):
                return f"range:{self.name}"
        if self.provenance:
            actual = provenance.get(self.name.split(".")[0], set())
            if not actual or not actual.issubset(set(self.provenance)):
                return f"provenance:{self.name}"
        return None

    def pretty(self) -> str:
        bits = [self.type_name]
        if self.non_null:
            bits.append("non-null")
        if self.hull.kind != "any":
            bits.append(self.hull.pretty())
        if self.max_len is not None:
            bits.append(f"len ≤ {self.max_len}")
        if self.min_len is not None:
            bits.append(f"len ≥ {self.min_len}")
        if self.provenance:
            bits.append("provenance ∈ {" + ", ".join(self.provenance) + "}")
        head = f"{self.name} : " + ", ".join(b for b in bits if b)
        if self.present_iff is not None:
            head += f"; present iff {self.present_iff.pretty()}"
        return head

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type_name": self.type_name,
            "non_null": self.non_null,
            "hull": self.hull.to_dict(),
            "max_len": self.max_len,
            "min_len": self.min_len,
            "provenance": list(self.provenance),
            "present_iff": self.present_iff.to_dict() if self.present_iff else None,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "OutputClause":
        return cls(
            name=d["name"],
            type_name=d["type_name"],
            non_null=d.get("non_null", True),
            hull=Hull.from_dict(d.get("hull", {"kind": "any"})),
            max_len=d.get("max_len"),
            min_len=d.get("min_len"),
            provenance=tuple(d.get("provenance", ())),
            present_iff=_predicate_from_dict(d["present_iff"]) if d.get("present_iff") else None,
        )


@dataclass(slots=True)
class Verifier:
    """``V``: live-out contract plus effect-multiset containment."""

    clauses: list[OutputClause] = field(default_factory=list)
    allowed_effects: tuple[str, ...] = ()
    call_counts: tuple[int, ...] = ()

    def verify(
        self,
        outputs: dict[str, Any],
        env: Any,
        provenance: dict[str, set[str]],
        effects: Sequence[str],
        n_calls: int,
    ) -> list[str]:
        reasons: list[str] = []
        for clause in self.clauses:
            bad = clause.check(outputs, env, provenance)
            if bad:
                reasons.append(bad)
        if self.allowed_effects:
            for eff in effects:
                if eff not in self.allowed_effects:
                    reasons.append(f"effect:{eff}")
        if self.call_counts and n_calls not in self.call_counts:
            reasons.append(f"n_calls:{n_calls}")
        return reasons

    def pretty(self) -> str:
        lines = ["verify  " + (self.clauses[0].pretty() if self.clauses else "")]
        for c in self.clauses[1:]:
            lines.append("        " + c.pretty())
        eff = ", ".join(self.allowed_effects)
        counts = ", ".join(str(c) for c in self.call_counts)
        lines.append(f"        effect_multiset ⊆ {{{eff}}},  |calls| ∈ {{{counts}}},  no WRITE_*")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "clauses": [c.to_dict() for c in self.clauses],
            "allowed_effects": list(self.allowed_effects),
            "call_counts": list(self.call_counts),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Verifier":
        return cls(
            clauses=[OutputClause.from_dict(c) for c in d.get("clauses", [])],
            allowed_effects=tuple(d.get("allowed_effects", ())),
            call_counts=tuple(d.get("call_counts", ())),
        )


# ---------------------------------------------------------------------------
# gate
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class GateModel:
    """Transparent nonconformity score ``q`` (proposal Eq. 17).

    A logistic model over *observable* risk features. An LLM's verbal confidence
    is never a feature; neither is anything unavailable at the boundary.
    """

    features: tuple[str, ...] = ()
    weights: tuple[float, ...] = ()
    bias: float = 0.0
    feature_means: tuple[float, ...] = ()
    feature_scales: tuple[float, ...] = ()

    def score(self, feats: dict[str, float]) -> float:
        import math

        z = self.bias
        for i, name in enumerate(self.features):
            x = float(feats.get(name, 0.0))
            mu = self.feature_means[i] if i < len(self.feature_means) else 0.0
            sd = self.feature_scales[i] if i < len(self.feature_scales) else 1.0
            z += self.weights[i] * ((x - mu) / (sd if sd else 1.0))
        return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))

    def to_dict(self) -> dict[str, Any]:
        return {
            "features": list(self.features),
            "weights": list(self.weights),
            "bias": self.bias,
            "feature_means": list(self.feature_means),
            "feature_scales": list(self.feature_scales),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "GateModel":
        return cls(
            features=tuple(d.get("features", ())),
            weights=tuple(d.get("weights", ())),
            bias=d.get("bias", 0.0),
            feature_means=tuple(d.get("feature_means", ())),
            feature_scales=tuple(d.get("feature_scales", ())),
        )


@dataclass(slots=True)
class Gate:
    """Calibrated dispatch gate: ``q(z) ≤ η`` with an exact risk certificate."""

    model: GateModel = field(default_factory=GateModel)
    #: Serialized :class:`~agent_compaction.grc.calibrate.GateFeatures` so that the
    #: runtime computes byte-identical features to those used during calibration.
    #: Feature drift between calibration and dispatch would invalidate Eq. (18).
    features_spec: dict[str, Any] = field(default_factory=dict)
    threshold: float = 0.0
    grid: tuple[float, ...] = ()
    alpha: float = 0.05
    delta: float = 0.10
    n_calibration_groups: int = 0
    n_accepted: int = 0
    observed_violations: int = 0
    risk_upper_bound: float = 1.0
    coverage: float = 0.0
    admissible: tuple[float, ...] = ()
    retire: bool = False
    notes: str = ""

    def accepts(self, feats: dict[str, float]) -> tuple[bool, float]:
        q = self.model.score(feats)
        return (q <= self.threshold and not self.retire), q

    def pretty(self) -> str:
        return (
            f"gate    q = logistic(entry features)   η = {self.threshold:.2f}   "
            f"(cal n={self.n_calibration_groups} groups, α={self.alpha}, δ={self.delta}, "
            f"|Λ|={len(self.grid)}, R⁺={self.risk_upper_bound:.3f}, φ̂={self.coverage:.2f})"
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["model"] = self.model.to_dict()
        d["grid"] = list(self.grid)
        d["admissible"] = list(self.admissible)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Gate":
        d = dict(d)
        d["model"] = GateModel.from_dict(d.get("model", {}))
        d["features_spec"] = d.get("features_spec", {})
        d["grid"] = tuple(d.get("grid", ()))
        d["admissible"] = tuple(d.get("admissible", ()))
        return cls(**d)


# ---------------------------------------------------------------------------
# evidence + artifact
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Evidence:
    """Everything that justified (or refused) promotion."""

    support_groups: int = 0
    total_groups: int = 0
    support_principals: int = 0
    support_days: int = 0
    removed_requests: float = 0.0
    split_ids: dict[str, list[str]] = field(default_factory=dict)
    replay: dict[str, Any] = field(default_factory=dict)
    perturbation: dict[str, Any] = field(default_factory=dict)
    counterexamples: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    rejection_reasons: list[str] = field(default_factory=list)
    fallback_reasons: dict[str, int] = field(default_factory=dict)
    dataset_digest: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Evidence":
        return cls(**d)


@dataclass(slots=True)
class RouteConfig:
    """TGWS leaf: a route predicate plus the specialised configuration."""

    predicates: tuple[Predicate, ...] = ()
    route_label: str = ""
    agent: str = ""
    model: str = ""
    reasoning_tier: str = "default"
    prompt_blocks: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    handoffs: tuple[str, ...] = ()
    support: int = 0
    purity: float = 0.0
    coverage: float = 0.0
    prompt_tokens: int = 0
    schema_tokens: int = 0
    baseline_prompt_tokens: int = 0
    baseline_schema_tokens: int = 0

    def matches(self, entry_state: Any) -> bool:
        env = {"z": entry_state}
        return all(p.evaluate(env) for p in self.predicates)

    def pretty(self) -> str:
        pred = " ∧ ".join(p.pretty() for p in self.predicates) or "true"
        return (
            f"route  if {pred}\n"
            f"       → agent={self.agent} model={self.model} reasoning={self.reasoning_tier}\n"
            f"       prompt_blocks={list(self.prompt_blocks)}\n"
            f"       tools={list(self.tools)} handoffs={list(self.handoffs)}\n"
            f"       support={self.support} purity={self.purity:.2f} "
            f"tokens {self.baseline_prompt_tokens + self.baseline_schema_tokens}"
            f"→{self.prompt_tokens + self.schema_tokens}"
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["predicates"] = [p.to_dict() for p in self.predicates]
        for k in ("prompt_blocks", "tools", "handoffs"):
            d[k] = list(getattr(self, k))
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RouteConfig":
        d = dict(d)
        d["predicates"] = tuple(_predicate_from_dict(p) for p in d.get("predicates", []))
        for k in ("prompt_blocks", "tools", "handoffs"):
            d[k] = tuple(d.get(k, ()))
        return cls(**d)


@dataclass(slots=True)
class Artifact:
    """An immutable, evidence-bearing artifact."""

    artifact_id: str
    name: str
    kind: str = "grc"  # grc | tgws
    version: int = 1
    program: Program | None = None
    route: RouteConfig | None = None
    guard: HardGuard = field(default_factory=HardGuard)
    verifier: Verifier = field(default_factory=Verifier)
    gate: Gate = field(default_factory=Gate)
    manifest: ExecutionManifest | None = None
    compatibility_key: str = ""
    partition: dict[str, str] = field(default_factory=dict)
    evidence: Evidence = field(default_factory=Evidence)
    lifecycle: Lifecycle = Lifecycle.SYNTHESIZED
    owner: str = "unassigned"
    approved_by: str | None = None
    expiry_day: str | None = None
    rollback_target: str | None = None
    monitoring: dict[str, float] = field(default_factory=dict)
    signature: str = ""

    # -- identity / signing ----------------------------------------------
    def body_digest(self) -> str:
        payload = json.dumps(self.to_dict(include_signature=False), sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def sign(self, key: bytes) -> str:
        self.signature = hmac.new(key, self.body_digest().encode(), hashlib.sha256).hexdigest()
        return self.signature

    def verify_signature(self, key: bytes) -> bool:
        if not self.signature:
            return False
        expected = hmac.new(key, self.body_digest().encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, self.signature)

    # -- display ----------------------------------------------------------
    def explain(self) -> str:
        head = (
            f"artifact  {self.name}@{self.version}   "
            f"support {self.evidence.support_groups}/{self.evidence.total_groups} groups   "
            f"removes k={self.evidence.removed_requests:.2f}   [{self.lifecycle.value}]"
        )
        parts = [head, "─" * 78, self.guard.pretty()]
        if self.route is not None:
            parts.append(self.route.pretty())
        if self.program is not None:
            parts.append("")
            parts.append(self.program.pretty())
        if self.verifier.clauses:
            parts.append(self.verifier.pretty())
        parts.append(self.gate.pretty())
        return "\n".join(parts)

    def to_dict(self, include_signature: bool = True) -> dict[str, Any]:
        d: dict[str, Any] = {
            "artifact_id": self.artifact_id,
            "name": self.name,
            "kind": self.kind,
            "version": self.version,
            "program": self.program.to_dict() if self.program else None,
            "route": self.route.to_dict() if self.route else None,
            "guard": self.guard.to_dict(),
            "verifier": self.verifier.to_dict(),
            "gate": self.gate.to_dict(),
            "manifest": asdict(self.manifest) if self.manifest else None,
            "compatibility_key": self.compatibility_key,
            "partition": self.partition,
            "evidence": self.evidence.to_dict(),
            "lifecycle": self.lifecycle.value,
            "owner": self.owner,
            "approved_by": self.approved_by,
            "expiry_day": self.expiry_day,
            "rollback_target": self.rollback_target,
            "monitoring": self.monitoring,
        }
        if include_signature:
            d["signature"] = self.signature
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Artifact":
        return cls(
            artifact_id=d["artifact_id"],
            name=d["name"],
            kind=d.get("kind", "grc"),
            version=d.get("version", 1),
            program=_program_from_dict(d["program"]) if d.get("program") else None,
            route=RouteConfig.from_dict(d["route"]) if d.get("route") else None,
            guard=HardGuard.from_dict(d.get("guard", {})),
            verifier=Verifier.from_dict(d.get("verifier", {})),
            gate=Gate.from_dict(d.get("gate", {})),
            manifest=ExecutionManifest(**d["manifest"]) if d.get("manifest") else None,
            compatibility_key=d.get("compatibility_key", ""),
            partition=d.get("partition", {}),
            evidence=Evidence.from_dict(d.get("evidence", {})),
            lifecycle=Lifecycle(d.get("lifecycle", "synthesized")),
            owner=d.get("owner", "unassigned"),
            approved_by=d.get("approved_by"),
            expiry_day=d.get("expiry_day"),
            rollback_target=d.get("rollback_target"),
            monitoring=d.get("monitoring", {}),
            signature=d.get("signature", ""),
        )
