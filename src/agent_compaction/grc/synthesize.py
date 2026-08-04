"""Algorithms 3 and 4 — binding synthesis and branch synthesis.

Algorithm 3 finds, for each argument slot, the simplest expression from the closed
library that reproduces the slot's value in *every* supporting trace. Algorithm 4
decides whether an observed divergence is explainable from observations or is a
genuine decision. Both return ``⊥`` freely: rejection is the normal outcome.

Three implementation notes that matter for correctness:

* **Candidate sources are program-environment paths**, intersected across the whole
  supporting family (Algorithm 3 line 2). A path that exists in only some traces
  cannot be committed to, which is what kills the positional ``recs[1].id`` binding
  and forces the stable ``filter(status == "active") |> project(id)``.
* **Grouped refitting is enforced** for bindings and branches: exact
  leave-one-group-out for up to five groups and deterministic five-fold grouped
  refitting above that, so a proxy selected only when a group is present is rejected.
* **The permutation test reruns the whole search** on shuffled labels
  (Algorithm 4 lines 15-18). With ~3,000 atoms and ~20 groups, perfect separation
  happens by chance almost always; proposal §6.3 makes this the primary defence in
  any deployment that cannot replay production, so it is not optional here.

Deviation from the published listing, recorded in ``docs/spec-review.md``:
Algorithm 4 line 3 restricts atoms to paths visible in the hard guard, but
use-cases §1 compiles the atom ``sub.tier == "enterprise"``, which is an in-region
observation and cannot be guard-visible. Atoms are therefore drawn from paths
*observable at the divergence point*, with guard-visible paths ranked first, and
the support floor, leave-one-group-out and permutation test kept as the defence.
"""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterable, Sequence

from ..schema.effects import EffectCatalog
from ..schema.traces import EventKind, flatten, resolve_path
from .dsl import Binding, Const, Expr, Op, SynthContext, apply_chain, search_chains
from .program import AssertStep, CallStep, LoopStep, Predicate, Program

__all__ = [
    "SynthesisResult",
    "synthesize_program",
    "synthesize_binding",
    "synthesize_branch",
    "var_name_for",
    "window_env",
]

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..graph.provenance import GroundabilityPolicy
    from ..graph.windows import Family, Window, WindowStep

VERB_PREFIXES = frozenset(
    {"get", "list", "find", "check", "issue", "search", "fetch", "show", "query", "lookup", "read", "resolve"}
)


def var_name_for(tool: str, taken: set[str]) -> str:
    """Deterministic, readable variable name for a step's result."""

    leaf = tool.split(".")[-1]
    words = [w for w in leaf.split("_") if w]
    if len(words) > 1 and words[0] in VERB_PREFIXES:
        words = words[1:]
    base = (words[0] if words else leaf)[:4].lower() or "v"
    name = base
    i = 2
    while name in taken:
        name = f"{base}{i}"
        i += 1
    taken.add(name)
    return name


def window_env(window: Window, names: Sequence[str], upto: int) -> dict[str, Any]:
    """Recorded execution environment visible before step ``upto``."""

    env: dict[str, Any] = {"z": window.episode.entry_state}
    for i in range(min(upto, len(window.steps))):
        step = window.steps[i]
        env[names[i]] = _step_result(window, step)
    return env


def _step_result(window: Window, step: WindowStep) -> Any:
    if not step.result_positions:
        return None
    if len(step.result_positions) == 1:
        return window.patg.order[step.result_positions[0]].output
    return [window.patg.order[p].output for p in step.result_positions]


def _step_args(window: Window, step: WindowStep) -> dict[str, Any]:
    pos = step.positions[0]
    ev = window.patg.order[pos]
    return dict(ev.input) if isinstance(ev.input, dict) else {}


# ---------------------------------------------------------------------------
# Algorithm 3
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class BindingResult:
    binding: Binding | None
    reason: str = ""
    ambiguous_alternatives: int = 0

    @property
    def ok(self) -> bool:
        return self.binding is not None


def synthesize_binding(
    slot_path: str,
    envs: Sequence[dict[str, Any]],
    targets: Sequence[Any],
    groups: Sequence[str],
    *,
    ctx: SynthContext,
    literal_only: bool = False,
    max_sources: int = 40,
    _validate_group_refit: bool = True,
) -> BindingResult:
    """Algorithm 3. ``envs[i]`` is the recorded env for supporting trace ``i``."""

    if not targets:
        return BindingResult(None, "no_observations")

    # line 1: invariant literal
    if all(_same(t, targets[0]) for t in targets):
        return BindingResult(Const(targets[0]))
    if literal_only:
        # §6.5: a literal-only slot may not be reconstructed by transform
        return BindingResult(None, "literal_only_slot_varies")

    # line 2: source paths present in ALL supporting traces
    path_sets: list[dict[str, Any]] = []
    for env in envs:
        flat: dict[str, Any] = {}
        for var, value in env.items():
            for path, v in flatten(value, prefix=var):
                flat[path] = v
        path_sets.append(flat)
    common = set(path_sets[0])
    for f in path_sets[1:]:
        common &= set(f)
    if not common:
        return BindingResult(None, "no_stable_source_path")

    # candidate ordering: identity matches first, then plausible relations
    ordered = sorted(common, key=lambda p: (_path_rank(p, path_sets[0], targets[0]), len(p), p))
    ordered = [p for p in ordered if _plausible_source(path_sets[0][p], targets[0])][:max_sources]

    best: tuple[tuple[int, int, int, int, str], Binding] | None = None
    n_alternatives = 0
    # Version space: generate candidate chains from several supporting traces, not
    # just the first. The correct chain is often unnecessary in the simplest trace
    # — filter(status == "active") is a no-op on a single-record list — so a
    # single-trace enumeration ranks it away and the slot looks ungroundable.
    probe_idx = _probe_indices(path_sets, ordered)
    for path in ordered:
        chains: list[tuple[Op, ...]] = []
        seen_chains: set[str] = set()
        for j in probe_idx:
            for chain in search_chains(path_sets[j][path], targets[j], ctx, max_results=12):
                key = "|".join(str(o) for o in chain)
                if key not in seen_chains:
                    seen_chains.add(key)
                    chains.append(chain)
        for chain in chains:
            ok = True
            for flat, target in zip(path_sets, targets):
                try:
                    got = apply_chain(flat[path], chain)
                except Exception:
                    ok = False
                    break
                if not _same(got, target):
                    ok = False
                    break
            if not ok:
                continue
            n_alternatives += 1
            expr = Expr(path, chain)
            # Positional access is penalised ahead of MDL: proposal §4.1 calls
            # `recs[1].id` unstable across users even when every supporting trace
            # happens to admit it, and §4.3's worked example expects the
            # select-then-project chain to win. Recorded in docs/spec-review.md.
            key = (_index_depth(path), expr.mdl, len(chain), len(path.split(".")), path)
            if best is None or key < best[0]:
                best = (key, expr)
    if best is None:
        return BindingResult(None, "no_consistent_expression")  # a genuine decision

    binding = best[1]
    if _validate_group_refit and not _group_refit_validates(
        slot_path,
        envs,
        targets,
        groups,
        ctx=ctx,
        literal_only=literal_only,
        max_sources=max_sources,
    ):
        return BindingResult(None, "group_refit_failed")
    return BindingResult(binding, "", n_alternatives - 1)


def _index_depth(path: str) -> int:
    """How many list indices a path dereferences. 0 means order-independent."""

    return path.count("[")


def _probe_indices(path_sets: Sequence[dict[str, Any]], paths: Sequence[str], *, k: int = 4) -> list[int]:
    """Pick diverse traces to enumerate chains from: widest containers first."""

    def width(j: int) -> int:
        total = 0
        for p in paths[:16]:
            v = path_sets[j].get(p)
            if isinstance(v, (list, dict)):
                total += len(v)
        return total

    order = sorted(range(len(path_sets)), key=lambda j: -width(j))
    picks = order[: max(1, k - 1)]
    if 0 not in picks:
        picks.append(0)
    return sorted(set(picks))


def _path_rank(path: str, flat: dict[str, Any], target: Any) -> int:
    v = flat.get(path)
    if _same(v, target):
        return 0
    if isinstance(v, (list, dict)):
        return 2
    return 1


def _plausible_source(value: Any, target: Any) -> bool:
    if isinstance(value, (list, dict)):
        return bool(value)
    if isinstance(value, bool) or value is None:
        return False
    if isinstance(target, str) and isinstance(value, str):
        lv, lt = value.lower(), target.lower()
        return lv == lt or lt in lv or lv in lt or value.strip() == target
    if isinstance(target, (int, float)) and isinstance(value, (int, float)):
        return True
    if isinstance(target, str) and isinstance(value, (int, float)):
        return str(value) in target
    if isinstance(target, (int, float)) and isinstance(value, str):
        return value.strip().lstrip("-").replace(".", "", 1).isdigit()
    return False


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, float) or isinstance(b, float):
        try:
            return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-9)
        except (TypeError, ValueError):
            return False
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    return a == b


def _group_refit_validates(
    slot_path: str,
    envs: Sequence[dict[str, Any]],
    targets: Sequence[Any],
    groups: Sequence[str],
    *,
    ctx: SynthContext,
    literal_only: bool,
    max_sources: int,
) -> bool:
    """Refit without held-out groups and require the selected binding to generalize.

    With many groups, deterministic five-fold grouped validation bounds compilation
    cost while preserving the essential property: no group used to choose a binding
    is also used to validate that choice.
    """

    unique = sorted(set(groups))
    if len(unique) < 2:
        return True
    n_folds = min(5, len(unique))
    folds = [set(unique[offset::n_folds]) for offset in range(n_folds)]
    for held in folds:
        train = [i for i, group in enumerate(groups) if group not in held]
        test = [i for i, group in enumerate(groups) if group in held]
        if not train or not test:
            continue
        fitted = synthesize_binding(
            slot_path,
            [envs[i] for i in train],
            [targets[i] for i in train],
            [groups[i] for i in train],
            ctx=ctx,
            literal_only=literal_only,
            max_sources=max_sources,
            _validate_group_refit=False,
        )
        if not fitted.ok:
            return False
        for i in test:
            try:
                got = fitted.binding.evaluate(envs[i])
            except Exception:
                return False
            if not _same(got, targets[i]):
                return False
    return True


# ---------------------------------------------------------------------------
# Algorithm 4
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class BranchResult:
    predicate: Predicate | None
    reason: str = ""
    permutation_p: float = 1.0
    n_groups: int = 0
    atoms_considered: int = 0
    n_separating: int = 0

    @property
    def ok(self) -> bool:
        return self.predicate is not None


def _atoms(envs: Sequence[dict[str, Any]], *, max_atoms: int = 4000) -> list[Predicate]:
    """Typed atoms over paths observable at the divergence point."""

    # paths present in every env, with their observed value sets
    flats: list[dict[str, Any]] = []
    for env in envs:
        flat: dict[str, Any] = {}
        for var, value in env.items():
            for path, v in flatten(value, prefix=var):
                if not isinstance(v, (dict, list)):
                    flat[path] = v
                elif isinstance(v, list):
                    flat[path] = v
        flats.append(flat)
    common = set(flats[0])
    for f in flats[1:]:
        common &= set(f)
    # Ordering matters and is not specified by the published algorithm. With ~3k
    # atoms and ~60 groups several atoms separate the labels perfectly, so the
    # implementation must impose a preference or it will pick an arbitrary proxy
    # (e.g. `invo.invoices[0].line_items len> 1` instead of `subs.tier ==
    # "enterprise"`). Preference: guard-visible entry-state paths first, then
    # order-independent paths, then lexical. Alternatives are counted and reported.
    ordered = sorted(common, key=lambda p: (0 if p.startswith("z.") else 1, _index_depth(p), p))
    atoms: list[Predicate] = []
    for path in ordered:
        values = [f[path] for f in flats]
        if any(isinstance(v, list) for v in values):
            lens = sorted({len(v) for v in values if isinstance(v, list)})
            for n in lens:
                atoms.append(Predicate(path, "len==", n))
                atoms.append(Predicate(path, "len>", n))
            atoms.append(Predicate(path, "empty"))
            continue
        distinct = list(dict.fromkeys(v for v in values if v is not None))
        if len(distinct) > 12:
            distinct = distinct[:12]
        for v in distinct:
            atoms.append(Predicate(path, "==", v))
            atoms.append(Predicate(path, "!=", v))
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                atoms.append(Predicate(path, ">=", v))
                atoms.append(Predicate(path, "<", v))
            if isinstance(v, str) and len(v) >= 3:
                atoms.append(Predicate(path, "prefix", v[:3]))
        atoms.append(Predicate(path, "present"))
        if len(atoms) > max_atoms:
            break
    return atoms[:max_atoms]


def _purity(atom: Predicate, envs: Sequence[dict[str, Any]], labels: Sequence[bool]) -> float:
    """Exact-classification purity with ε = 0: the atom must separate perfectly."""

    tp = fp = tn = fn = 0
    for env, label in zip(envs, labels):
        pred = atom.evaluate(env)
        if pred and label:
            tp += 1
        elif pred and not label:
            fp += 1
        elif not pred and not label:
            tn += 1
        else:
            fn += 1
    n = tp + fp + tn + fn
    if not n:
        return 0.0
    return max(tp + tn, fp + fn) / n


def _search_separating_atom(
    atoms: Sequence[Predicate], envs: Sequence[dict[str, Any]], labels: Sequence[bool]
) -> Predicate | None:
    for atom in atoms:
        # Both polarities are enumerated as atoms (`==` and `!=`), so requiring
        # exact agreement with the label is not a loss of generality.
        if all(atom.evaluate(e) == l for e, l in zip(envs, labels)):
            return atom
    return None


def _count_separating(
    atoms: Sequence[Predicate], envs: Sequence[dict[str, Any]], labels: Sequence[bool], *, cap: int = 64
) -> int:
    """How many atoms separate perfectly. Reported as a branch-ambiguity metric."""

    n = 0
    for atom in atoms:
        if all(atom.evaluate(e) == l for e, l in zip(envs, labels)):
            n += 1
            if n >= cap:
                break
    return n


def synthesize_branch(
    envs: Sequence[dict[str, Any]],
    labels: Sequence[bool],
    groups: Sequence[str],
    *,
    s_branch: int = 20,
    n_permutations: int = 400,
    pi_max: float = 0.01,
    seed: int = 17,
) -> BranchResult:
    """Algorithm 4, restricted to decision lists of length 1 (``L_max`` = 1 arm).

    A single atom is all the demos require; longer lists multiply the search space
    that the permutation test has to account for, and proposal §4.4 caps
    ``L_max`` at 3. Extending to length 3 is a loop over the same machinery and is
    left out deliberately rather than shipped untested.
    """

    n_groups = len(set(groups))
    labels_by_group: dict[str, set[bool]] = defaultdict(set)
    for group, label in zip(groups, labels):
        labels_by_group[group].add(label)
    inconsistent = sorted(group for group, values in labels_by_group.items() if len(values) > 1)
    if inconsistent:
        return BranchResult(
            None,
            f"group_label_inconsistent:{inconsistent[0]}",
            n_groups=n_groups,
        )
    if len(set(labels)) == 1:
        return BranchResult(None, "unconditional", n_groups=n_groups)
    if n_groups < s_branch:
        return BranchResult(None, f"support_below_s_branch:{n_groups}<{s_branch}", n_groups=n_groups)

    atoms = _atoms(envs)
    atom = _search_separating_atom(atoms, envs, labels)
    if atom is None:
        return BranchResult(None, "not_separable", n_groups=n_groups, atoms_considered=len(atoms))

    # line 14: leave-one-group-out over the *search*, not just the atom
    for held in sorted(set(groups)):
        idx = [i for i, g in enumerate(groups) if g != held]
        if len(set(labels[i] for i in idx)) < 2:
            continue
        refit = _search_separating_atom(atoms, [envs[i] for i in idx], [labels[i] for i in idx])
        if refit is None:
            return BranchResult(None, "logo_failed", n_groups=n_groups, atoms_considered=len(atoms))
        held_idx = [i for i, g in enumerate(groups) if g == held]
        if any(refit.evaluate(envs[i]) != labels[i] for i in held_idx):
            return BranchResult(None, "logo_failed", n_groups=n_groups, atoms_considered=len(atoms))

    # lines 15-18: permutation test over group-label shuffles, rerunning the search
    rng = random.Random(seed)
    group_labels: dict[str, bool] = {}
    for g, l in zip(groups, labels):
        group_labels[g] = l
    keys = list(group_labels)
    hits = 0
    for _ in range(n_permutations):
        vals = [group_labels[k] for k in keys]
        rng.shuffle(vals)
        shuffled = dict(zip(keys, vals))
        perm_labels = [shuffled[g] for g in groups]
        if _search_separating_atom(atoms, envs, perm_labels) is not None:
            hits += 1
    p_hat = (hits + 1) / (n_permutations + 1)
    if p_hat > pi_max:
        return BranchResult(
            None,
            f"permutation_test_failed:p={p_hat:.4f}",
            permutation_p=p_hat,
            n_groups=n_groups,
            atoms_considered=len(atoms),
        )
    return BranchResult(
        atom,
        "",
        permutation_p=p_hat,
        n_groups=n_groups,
        atoms_considered=len(atoms),
        n_separating=_count_separating(atoms, envs, labels),
    )


# ---------------------------------------------------------------------------
# program assembly
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SynthesisResult:
    program: Program | None = None
    names: tuple[str, ...] = ()
    reason: str = ""
    branch: "BranchResult | None" = None
    slot_reasons: dict[str, str] = field(default_factory=dict)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.program is not None


def synthesize_program(
    family: Family,
    train_windows: Sequence[Window],
    catalog: EffectCatalog,
    policy: GroundabilityPolicy,
    *,
    max_depth: int = 2,
    s_branch: int = 20,
    n_permutations: int = 400,
) -> SynthesisResult:
    """Assemble a region program for one family from its training windows."""

    if not train_windows:
        return SynthesisResult(reason="no_training_windows")

    train_windows = sorted(
        train_windows,
        key=lambda window: (
            window.group_id,
            window.episode.episode_id,
            window.a,
            window.b,
        ),
    )
    base = sorted(
        train_windows,
        key=lambda window: (
            -len(window.steps),
            -window.n_tool_events,
            window.episode.episode_id,
            window.a,
            window.b,
        ),
    )[0]
    n_steps = len(base.steps)
    taken: set[str] = set()
    names = [var_name_for(step.tool, taken) for step in base.steps]
    ctx = SynthContext(max_depth=max_depth)

    # windows are grouped by arm length: the long arm carries the diverging step
    long_windows = [w for w in train_windows if len(w.steps) == n_steps]
    short_windows = [w for w in train_windows if len(w.steps) < n_steps]
    if not long_windows:
        return SynthesisResult(reason="no_long_arm_windows")

    branch: BranchResult | None = None
    if short_windows:
        div = min(len(w.steps) for w in short_windows)
        envs = [window_env(w, names, div) for w in train_windows]
        labels = [len(w.steps) > div for w in train_windows]
        groups = [w.group_id for w in train_windows]
        branch = synthesize_branch(
            envs, labels, groups, s_branch=s_branch, n_permutations=n_permutations
        )
        if not branch.ok:
            # keep only the common prefix: the divergent tail stays with the model
            n_steps = div
            long_windows = [w for w in train_windows if len(w.steps) >= div]
            names = names[:div]

    steps: list[Any] = []
    slot_reasons: dict[str, str] = {}
    theta: set[str] = set()
    n_alt = 0
    n_loop_alternatives = 0

    for i in range(n_steps):
        step_windows = [w for w in train_windows if len(w.steps) > i]
        tool = base.steps[i].tool
        arg_paths: set[str] = set()
        for w in step_windows:
            arg_paths |= set(_step_args(w, w.steps[i]))
        args: dict[str, Binding] = {}
        for slot_path in sorted(arg_paths):
            envs = [window_env(w, names, i) for w in step_windows]
            targets = [_step_args(w, w.steps[i]).get(slot_path) for w in step_windows]
            groups = [w.group_id for w in step_windows]
            keep = [j for j, t in enumerate(targets) if t is not None]
            if not keep:
                continue
            res = synthesize_binding(
                slot_path,
                [envs[j] for j in keep],
                [targets[j] for j in keep],
                [groups[j] for j in keep],
                ctx=ctx,
                literal_only=policy.is_literal_only(tool, slot_path),
            )
            if not res.ok:
                slot_reasons[f"{tool}.{slot_path}"] = res.reason
                return SynthesisResult(
                    reason=f"ungroundable_slot:{tool}.{slot_path}:{res.reason}",
                    slot_reasons=slot_reasons,
                    branch=branch,
                )
            n_alt += res.ambiguous_alternatives
            args[slot_path] = res.binding
            if isinstance(res.binding, Expr) and res.binding.source.startswith("z."):
                theta.add(_theta_root(res.binding.source))

        when = None
        if branch is not None and branch.ok and i >= min(len(w.steps) for w in short_windows):
            when = branch.predicate

        run_lengths = {len(w.steps[i].positions) for w in step_windows}
        if max(run_lengths) > 1:
            loop_pred, n_loop_atoms = _synthesize_loop_predicate(step_windows, i, names)
            n_loop_alternatives += max(0, n_loop_atoms - 1)
            if loop_pred is None:
                # A repeated call with no synthesizable termination predicate is not
                # a loop, it is an unexplained repetition. Emitting a single call
                # would quietly change the observed call multiset.
                return SynthesisResult(
                    reason=f"loop_predicate_unsynthesizable:{tool}",
                    slot_reasons=slot_reasons,
                    branch=branch,
                )
            steps.append(
                LoopStep(
                    var=names[i],
                    tool=tool,
                    args=args,
                    accumulate=_accumulate_field(step_windows, i),
                    counter=_counter_slot(step_windows, i),
                    continue_when=loop_pred,
                    max_iters=32,
                )
            )
        else:
            steps.append(CallStep(var=names[i], tool=tool, args=args, when=when))

    outputs: dict[str, Binding] = {names[i]: Expr(names[i], ()) for i in range(n_steps)}
    program = Program(
        theta=tuple(sorted(theta)),
        steps=steps,
        outputs=outputs,
        removed_requests=sum(w.removed_requests for w in train_windows) / len(train_windows),
        tools=tuple(base.steps[i].tool for i in range(n_steps)),
    )
    return SynthesisResult(
        program=program,
        names=tuple(names),
        branch=branch,
        slot_reasons=slot_reasons,
        stats={
            "n_alternative_bindings": n_alt,
            "n_alternative_loop_predicates": n_loop_alternatives,
            "n_steps": n_steps,
            "branch": (branch.reason if branch else "none"),
            "branch_p": (branch.permutation_p if branch else None),
            "branch_atoms": (branch.atoms_considered if branch else 0),
            "branch_alternatives": (max(0, branch.n_separating - 1) if branch else 0),
        },
    )


def _theta_root(source: str) -> str:
    """``z.ticket.requester_email`` → ``ticket.requester_email``."""

    return source[2:] if source.startswith("z.") else source


def _accumulate_field(windows: Sequence[Window], i: int) -> str:
    result = _step_result(windows[0], windows[0].steps[i])
    if isinstance(result, list) and result and isinstance(result[0], dict):
        for key, value in result[0].items():
            if isinstance(value, list):
                return key
    if isinstance(result, dict):
        for key, value in result.items():
            if isinstance(value, list):
                return key
    return "items"


def _counter_slot(windows: Sequence[Window], i: int) -> str | None:
    """Return an argument path proven to be the zero-based iteration counter.

    Integer literals such as ``limit=50`` are not counters. The old heuristic
    rewrote the first integer constant on every iteration, which changed a
    pagination limit into 0, 1, ... . A counter is now admitted only when every
    observed run exhibits that exact sequence.
    """

    candidates: set[str] | None = None
    observed: list[tuple[Window, list[dict[str, Any]]]] = []
    for window in windows:
        calls = []
        for pos in window.steps[i].positions:
            payload = window.patg.order[pos].input
            calls.append(dict(payload) if isinstance(payload, dict) else {})
        observed.append((window, calls))
        paths = {
            path
            for payload in calls
            for path, value in flatten(payload)
            if isinstance(value, int) and not isinstance(value, bool)
        }
        candidates = paths if candidates is None else candidates & paths
    for path in sorted(candidates or ()):
        if all(
            [resolve_path(payload, path) for payload in calls] == list(range(len(calls)))
            for _window, calls in observed
        ):
            return path
    return None


def _loop_predicate_atoms(
    payloads: Sequence[Any], var: str, field_name: str, sizes: Sequence[int]
) -> list[Predicate]:
    """Candidate continue-conditions for a repeated call, cheapest description first.

    Ordered by minimum description length and by how directly the atom expresses a
    continuation, which is also the order a reviewer would want to read:

    1. an explicit boolean continuation flag (``has_more``, ``is_truncated``);
    2. presence of a continuation handle (``next_cursor``, ``next_page_token``);
    3. a full page (``len(items) == page_size``);
    4. equality against a low-cardinality scalar status field.

    Only paths observed in *every* iteration payload are eligible, so a field that
    appears on the last page and nowhere else can never become the condition.
    """

    dicts = [p for p in payloads if isinstance(p, dict)]
    common: set[str] | None = None
    for payload in dicts:
        paths = {
            path
            for path, value in flatten(payload)
            if value is None or isinstance(value, (bool, int, float, str))
        }
        common = paths if common is None else (common & paths)

    flags: list[Predicate] = []
    handles: list[Predicate] = []
    scalars: list[Predicate] = []
    for path in sorted(common or ()):
        values = [resolve_path(payload, path) for payload in dicts]
        if values and all(isinstance(v, bool) for v in values):
            flags.append(Predicate(f"{var}.{path}", "==", True))
            continue
        if any(v is None for v in values) and any(v is not None for v in values):
            handles.append(Predicate(f"{var}.{path}", "present", None))
            continue
        distinct = {v for v in values if isinstance(v, str)}
        if 0 < len(distinct) <= 4:
            scalars.extend(
                Predicate(f"{var}.{path}", "==", value) for value in sorted(distinct)
            )

    lengths = [Predicate(f"{var}.{field_name}", "len==", n) for n in sorted(set(sizes))]
    return flags + handles + lengths + scalars


def _synthesize_loop_predicate(
    windows: Sequence[Window], i: int, names: Sequence[str]
) -> tuple[Predicate | None, int]:
    """Continue-condition for a bounded ForEach, verified against observed runs.

    The predicate must hold after every iteration except the last, and fail after
    the last, on *every* supporting window. Both directions matter: a condition
    that is merely true while iterating would not terminate, and one that is merely
    false at the end would never start.

    Returns the chosen predicate and the number of atoms that separated the runs
    equally well. More than one is not an error — the search is a closed
    enumeration and ties are resolved by description length — but the count is
    recorded so a reviewer can see how underdetermined the choice was.
    """

    field_name = _accumulate_field(windows, i)
    runs: list[tuple[list[Any], list[int]]] = []
    for w in windows:
        step = w.steps[i]
        outs: list[Any] = []
        sizes: list[int] = []
        for pos in step.result_positions:
            out = w.patg.order[pos].output
            outs.append(out)
            items = out.get(field_name) if isinstance(out, dict) else out
            sizes.append(len(items) if isinstance(items, list) else 0)
        runs.append((outs, sizes))

    if not any(len(sizes) > 1 for _outs, sizes in runs):
        # Nothing ever continued, so every false predicate would "separate" the
        # runs vacuously. Refuse rather than invent a termination condition.
        return None, 0

    payloads = [out for outs, _sizes in runs for out in outs]
    all_sizes = [n for _outs, sizes in runs for n in sizes]
    admissible: list[Predicate] = []
    for atom in _loop_predicate_atoms(payloads, names[i], field_name, all_sizes):
        ok = True
        for outs, _sizes in runs:
            for index, out in enumerate(outs):
                should_continue = index < len(outs) - 1
                if atom.evaluate({names[i]: out}) != should_continue:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            admissible.append(atom)
    if not admissible:
        return None, 0
    return admissible[0], len(admissible)
