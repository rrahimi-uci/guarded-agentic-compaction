"""Algorithm 5 — contract induction and grouped validation.

The hard guard ``H`` is fitted on training groups only: manifest equality, then
presence/type/hull for every live-in, then the isolation keys that must never be
crossed. The verifier ``V`` constrains live-outs by type, nullability,
cardinality, range hull, and provenance, and — the part the published listing does
not spell out but use-cases §1 requires — *per arm*, so that a conditional output
does not reject the arm on which it is legitimately absent.

Validation then tries to break the contract:

* **Grouped replay.** Recorded-response replay checks value equivalence and
  determinism; sandbox replay against a fresh world at the recorded entry state
  checks that the program still works when the calls actually run.
* **Perturbations.** Unseen entities, empty/singleton/large collections, nulls,
  duplicates, reordering, tool 4xx/5xx, and schema drift. A wrong answer is a hard
  reject; an abstention is acceptable (line 17).

If no sandbox is available the perturbation suite is *not claimed* — proposal §6.3
is explicit that pretending the suite ran is the one indefensible option.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Iterable, Sequence

from ..paths import flatten, resolve_path
from ..runtime.facade import FacadeMode, Recording, ToolFacade
from ..runtime.interp import run_program
from ..schema.artifacts import GuardClause, HardGuard, Hull, OutputClause, Verifier
from ..schema.effects import EffectCatalog
from ..schema.traces import ExecutionManifest
from .program import CallStep, LoopStep, Predicate, Program
from .synthesize import window_env

__all__ = [
    "induce_guard",
    "induce_verifier",
    "fit_hull",
    "ReplayReport",
    "grouped_recorded_replay",
    "ChallengeReport",
    "challenge",
]

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..graph.windows import Window

MAX_ENUM_CARDINALITY = 12


def _opaque_identifier_path(path: str) -> bool:
    """Return true for keys whose numeric magnitude has no admissibility meaning."""

    leaf = path.rsplit(".", 1)[-1].lower()
    return leaf in {"id", "key", "number"} or leaf.endswith(
        ("_id", "_key", "_number")
    )


# ---------------------------------------------------------------------------
# hull fitting
# ---------------------------------------------------------------------------


def fit_hull(values: Sequence[Any]) -> Hull:
    """Interval for numerics, enum for low-card categoricals, regex band for strings."""

    vals = [v for v in values if v is not None]
    if not vals:
        return Hull("any")
    if all(isinstance(v, bool) for v in vals):
        return Hull("enum", values=tuple(sorted({bool(v) for v in vals}, key=str)))
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals):
        return Hull("interval", low=float(min(vals)), high=float(max(vals)))
    if all(isinstance(v, str) for v in vals):
        distinct = sorted(set(vals))
        if len(distinct) <= MAX_ENUM_CARDINALITY:
            return Hull("enum", values=tuple(distinct))
        return Hull(
            "regex",
            pattern=_string_pattern(distinct),
            min_len=min(len(v) for v in distinct),
            max_len=max(len(v) for v in distinct),
        )
    if all(isinstance(v, list) for v in vals):
        return Hull("interval", low=float(min(len(v) for v in vals)), high=float(max(len(v) for v in vals)))
    return Hull("any")


def _string_pattern(values: Sequence[str]) -> str:
    prefix = _common_prefix(values)
    charset = set()
    for v in values:
        charset |= set(v[len(prefix) :])
    classes = []
    if any(c.islower() for c in charset):
        classes.append("a-z")
    if any(c.isupper() for c in charset):
        classes.append("A-Z")
    if any(c.isdigit() for c in charset):
        classes.append("0-9")
    punct = "".join(sorted({c for c in charset if not c.isalnum()}))
    if punct:
        classes.append(re.escape(punct))
    body = "".join(classes) or "\\s\\S"
    lo = min(len(v) - len(prefix) for v in values)
    hi = max(len(v) - len(prefix) for v in values)
    return f"^{re.escape(prefix)}[{body}]{{{lo},{hi}}}$"


def _common_prefix(values: Sequence[str]) -> str:
    if not values:
        return ""
    prefix = values[0]
    for v in values[1:]:
        while prefix and not v.startswith(prefix):
            prefix = prefix[:-1]
    return prefix


# ---------------------------------------------------------------------------
# guard induction
# ---------------------------------------------------------------------------


def induce_guard(
    program: Program,
    train_windows: Sequence[Window],
    manifest: ExecutionManifest,
    catalog: EffectCatalog,
    *,
    partition_by: Sequence[str] = ("tenant_partition", "principal", "policy_version"),
) -> HardGuard:
    pins = {
        "model": manifest.model,
        "prompt_hash": manifest.prompt_hash,
        "tools_hash": manifest.tools_hash,
        "policy_hash": manifest.policy_hash,
        "guardrail_hash": manifest.guardrail_hash,
        "effect_catalog_version": catalog.catalog_version,
        "entry_contract_version": manifest.entry_contract_version,
    }
    isolation: dict[str, str] = {}
    for key in partition_by:
        values = {getattr(w.episode.envelope, key, "unknown") for w in train_windows}
        if len(values) == 1:
            isolation[key] = next(iter(values))
        else:
            # A partition key with several values in one family means the family was
            # pooled across an isolation boundary. That is a compile-time error, not
            # something to average over.
            isolation[key] = "|".join(sorted(values))

    clauses: list[GuardClause] = []
    for path in program.theta:
        values = [resolve_path(w.episode.entry_state, path) for w in train_windows]
        present = [v for v in values if v is not None]
        if not present:
            continue
        clauses.append(
            GuardClause(
                path=f"z.{path}",
                type_name=_type_of(present[0]),
                # Identifiers are nominal even when represented as integers. Fitting an
                # interval to issue/order/task IDs makes admission depend on accidental
                # training extrema and rejects otherwise schema-compatible future IDs.
                hull=Hull("any") if _opaque_identifier_path(path) else fit_hull(present),
                required=len(present) == len(values),
            )
        )
    # the entry-contract version is pinned as a schema clause when present in z
    for extra in ("ticket.intake", "intake", "form_version"):
        if any(resolve_path(w.episode.entry_state, extra) is not None for w in train_windows):
            values = [resolve_path(w.episode.entry_state, extra) for w in train_windows]
            present = [v for v in values if v is not None]
            if present and len(set(map(str, present))) <= MAX_ENUM_CARDINALITY:
                clauses.append(
                    GuardClause(
                        path=f"z.{extra}",
                        type_name=_type_of(present[0]),
                        hull=fit_hull(present),
                        role="schema_pin",
                    )
                )
            break

    allowed = sorted({catalog.effect_of(t).value for t in program.tools})
    return HardGuard(manifest_pins=pins, isolation=isolation, clauses=clauses, allowed_effects=tuple(allowed))


def _type_of(v: Any) -> str:
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


# ---------------------------------------------------------------------------
# verifier induction
# ---------------------------------------------------------------------------


def induce_verifier(
    program: Program,
    train_windows: Sequence[Window],
    names: Sequence[str],
    catalog: EffectCatalog,
    *,
    max_field_clauses: int = 4,
) -> Verifier:
    clauses: list[OutputClause] = []
    call_counts: Counter = Counter()
    step_by_var = {s.var: s for s in program.steps if isinstance(s, (CallStep, LoopStep))}

    for i, step in enumerate(program.steps):
        if not isinstance(step, (CallStep, LoopStep)):
            continue
        var = step.var
        conditional = isinstance(step, CallStep) and step.when is not None
        results = []
        for w in train_windows:
            if len(w.steps) <= i:
                continue
            env = window_env(w, names, i + 1)
            if var in env and env[var] is not None:
                results.append(env[var])
        if not results:
            continue
        clauses.append(
            OutputClause(
                name=var,
                type_name=_type_of(results[0]),
                non_null=not conditional,
                hull=Hull("any"),
                max_len=(max(len(r) for r in results) if isinstance(results[0], list) else None),
                min_len=(min(len(r) for r in results) if isinstance(results[0], list) else None),
                provenance=(step.tool,),
                present_iff=step.when if conditional else None,
            )
        )
        # field-level clauses: stable scalar and list fields inside the result
        for path, hull, type_name, minlen, maxlen in _field_clauses(
            results, limit=max_field_clauses
        ):
            clauses.append(
                OutputClause(
                    name=f"{var}.{path}",
                    type_name=type_name,
                    non_null=not conditional,
                    hull=hull,
                    max_len=maxlen,
                    min_len=minlen,
                    provenance=(step.tool,),
                    present_iff=step.when if conditional else None,
                )
            )

    for w in train_windows:
        call_counts[sum(s.run_length for s in w.steps)] += 1

    allowed = tuple(sorted({catalog.effect_of(t).value for t in program.tools}))
    return Verifier(clauses=clauses, allowed_effects=allowed, call_counts=tuple(sorted(call_counts)))


def _field_clauses(
    results: Sequence[Any], *, limit: int
) -> list[tuple[str, Hull, str, int | None, int | None]]:
    if not isinstance(results[0], dict):
        return []
    common: set[str] | None = None
    for r in results:
        if not isinstance(r, dict):
            return []
        keys = {k for k, v in r.items() if not isinstance(v, dict)}
        common = keys if common is None else (common & keys)
    out: list[tuple[str, Hull, str, int | None, int | None]] = []
    for key in sorted(common or ()):
        values = [r[key] for r in results]
        types = {_type_of(v) for v in values}
        if len(types) != 1:
            continue
        type_name = next(iter(types))
        if type_name == "list":
            out.append(
                (
                    key,
                    Hull("any"),
                    "list",
                    min(len(v) for v in values),
                    max(len(v) for v in values),
                )
            )
        elif _opaque_identifier_path(key):
            # The same nominal-key rule applies to tool outputs. Equality with the
            # requested entry is established by the synthesized binding/provenance;
            # an empirical range over returned IDs adds only training-set overfit.
            out.append((key, Hull("any"), type_name, None, None))
        elif type_name == "str" and len(set(values)) > MAX_ENUM_CARDINALITY:
            # High-cardinality text (titles, excerpts, messages) has no defensible
            # empirical regex hull. Keep type/provenance validation; range constraints
            # belong to the declared tool schema, not the observed training strings.
            out.append((key, Hull("any"), "str", None, None))
        else:
            out.append((key, fit_hull(values), type_name, None, None))
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------------------
# grouped replay
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ReplayReport:
    n: int = 0
    passed: int = 0
    abstained: int = 0
    wrong: int = 0
    effect_mismatch: int = 0
    state_delta: int = 0
    reasons: Counter = field(default_factory=Counter)
    counterexamples: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.wrong == 0 and self.effect_mismatch == 0 and self.state_delta == 0

    @property
    def pass_rate(self) -> float:
        return self.passed / self.n if self.n else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "n": self.n,
            "passed": self.passed,
            "abstained": self.abstained,
            "wrong": self.wrong,
            "effect_mismatch": self.effect_mismatch,
            "state_delta": self.state_delta,
            "pass_rate": round(self.pass_rate, 4),
            "reasons": dict(self.reasons),
        }


def grouped_recorded_replay(
    program: Program,
    guard: HardGuard,
    verifier: Verifier,
    windows: Sequence[Window],
    names: Sequence[str],
    catalog: EffectCatalog,
) -> ReplayReport:
    """Recorded-response replay: no external calls, value equivalence only.

    This validates the transforms and the program's determinism. It cannot validate
    generalization — the recorded responses are exactly the ones the artifact was
    synthesized from (proposal §6.3).
    """

    rep = ReplayReport()
    for w in windows:
        rep.n += 1
        recording = Recording.from_episode(w.episode)
        facade = ToolFacade(catalog=catalog, mode=FacadeMode.RECORDED, recording=recording,
                            allowed_tools=tuple(program.tools), max_calls=32)
        result = run_program(program, w.episode.entry_state, facade)
        if not result.ok:
            rep.abstained += 1
            rep.reasons[_reason_key(result.error)] += 1
            continue
        # live-outs must equal the recorded observations
        expected = {names[i]: _recorded_result(w, i) for i in range(min(len(names), len(w.steps)))}
        mismatched = [k for k, value in expected.items() if result.outputs.get(k) != value]
        if mismatched:
            rep.wrong += 1
            rep.reasons["live_out_mismatch"] += 1
            rep.counterexamples.append(
                {"episode": w.episode.episode_id, "kind": "live_out_mismatch", "fields": mismatched}
            )
            continue
        bad = verifier.verify(
            result.outputs, result.env, result.provenance, result.effects, len(result.calls)
        )
        if bad:
            rep.abstained += 1
            rep.reasons["verifier:" + bad[0]] += 1
            continue
        recorded_effects = tuple(sorted(catalog.effect_of(s.tool).value for s in w.steps for _ in s.positions))
        if Counter(result.effects) - Counter(recorded_effects):
            rep.effect_mismatch += 1
            rep.reasons["effect_multiset"] += 1
            continue
        rep.passed += 1
    return rep


def _recorded_result(w: Window, i: int) -> Any:
    step = w.steps[i]
    if not step.result_positions:
        return None
    return w.patg.order[step.result_positions[-1]].output


def _reason_key(error: str) -> str:
    return error.split(":")[0][:48]


# ---------------------------------------------------------------------------
# perturbation challenge
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ChallengeReport:
    recorded: ReplayReport = field(default_factory=ReplayReport)
    sandbox: ReplayReport = field(default_factory=ReplayReport)
    perturbation: dict[str, dict[str, Any]] = field(default_factory=dict)
    perturbations_claimed: bool = False
    hard_rejects: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.recorded.ok and self.sandbox.ok and not self.hard_rejects

    def as_dict(self) -> dict[str, Any]:
        return {
            "recorded": self.recorded.as_dict(),
            "sandbox": self.sandbox.as_dict(),
            "perturbation": self.perturbation,
            "perturbations_claimed": self.perturbations_claimed,
            "hard_rejects": self.hard_rejects[:8],
        }


def challenge(
    program: Program,
    guard: HardGuard,
    verifier: Verifier,
    dev_windows: Sequence[Window],
    names: Sequence[str],
    catalog: EffectCatalog,
    *,
    sandbox: Callable[[], Any] | None = None,
    perturbations: Sequence[Any] = (),
    max_sandbox: int = 60,
) -> ChallengeReport:
    """Grouped held-out replay plus metamorphic perturbations."""

    rep = ChallengeReport()
    rep.recorded = grouped_recorded_replay(program, guard, verifier, dev_windows, names, catalog)

    if sandbox is None:
        return rep

    from ..evaluation.replay import sandbox_replay

    rep.sandbox = sandbox_replay(
        program, guard, verifier, dev_windows[:max_sandbox], names, catalog, sandbox
    )

    if not perturbations:
        return rep

    from ..evaluation.perturb import run_perturbations

    rep.perturbations_claimed = True
    results, hard = run_perturbations(
        program, guard, verifier, dev_windows, names, catalog, sandbox, perturbations
    )
    rep.perturbation = results
    rep.hard_rejects = hard
    return rep
