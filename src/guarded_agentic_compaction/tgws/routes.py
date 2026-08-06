"""TGWS route learning: a bounded, readable entry-state route tree.

Depth ≤ 3, minimum leaf support, predeclared purity, and two stability checks that
the published sketch names but does not define (execution-plan §8.1 step 4):

* **temporal stability** — the leaf's purity must hold in each half of the time
  range, so a route that only worked last month is rejected;
* **subgroup stability** — purity must hold in every principal/tenant subgroup
  present in the leaf, so a route that works for one caller and not another is
  rejected.

Only entry-state features are eligible: fields observable *before* the first model
decision, filtered through the application's allowlist. Post-outcome fields and
proxy-leakage fields (anything correlated with the outcome by construction) are
excluded, and the exclusion is enforced by the allowlist rather than by taste.

The tree predicts a *route label*: the stable thing the baseline did (its handoff
target, tool family, or canonical path). Route labels are imitation targets, so
every accepted leaf must still be checked against task outcomes, not against path
agreement — that check lives in :mod:`guarded_agentic_compaction.tgws.prune`.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Sequence

from ..paths import resolve_path
from ..schema.traces import Episode, EventKind

__all__ = [
    "RouteExample",
    "RouteLeaf",
    "RouteTree",
    "default_route_label",
    "fit_route_tree",
]


def default_route_label(episode: Episode) -> str:
    """Stable route label: the first handoff target, else the first two tools used."""

    for ev in episode.events:
        if ev.kind is EventKind.HANDOFF and isinstance(ev.output, dict):
            return "handoff:" + str(ev.output.get("target"))
    tools = [ev.tool for ev in episode.events if ev.kind is EventKind.TOOL_CALL and ev.tool]
    uniq: list[str] = []
    for t in tools:
        if t not in uniq:
            uniq.append(t)
    return "path:" + "|".join(uniq[:2]) if uniq else "path:none"


@dataclass(slots=True)
class RouteExample:
    episode_id: str
    group_id: str
    day: str
    principal: str
    tenant: str
    features: dict[str, Any]
    label: str


@dataclass(slots=True)
class RouteLeaf:
    predicates: tuple[tuple[str, str, Any], ...]  # (path, op, const)
    label: str
    support: int = 0
    purity: float = 0.0
    coverage: float = 0.0
    group_support: int = 0
    stable: bool = True
    instability: str = ""

    def matches(self, features: dict[str, Any]) -> bool:
        for path, op, const in self.predicates:
            v = features.get(path)
            if op == "==" and v != const:
                return False
            if op == "!=" and v == const:
                return False
            if op == ">=" and not (isinstance(v, (int, float)) and v >= const):
                return False
            if op == "<" and not (isinstance(v, (int, float)) and v < const):
                return False
        return True

    def pretty(self) -> str:
        pred = " ∧ ".join(f"{p} {o} {c!r}" for p, o, c in self.predicates) or "true"
        flag = "" if self.stable else f"  [UNSTABLE: {self.instability}]"
        return (
            f"{pred} → {self.label}  (support={self.support} groups={self.group_support} "
            f"purity={self.purity:.3f} coverage={self.coverage:.3f}){flag}"
        )


@dataclass(slots=True)
class RouteTree:
    leaves: list[RouteLeaf] = field(default_factory=list)
    max_depth: int = 3
    min_support: int = 20
    min_purity: float = 0.90
    majority_label: str = ""
    n_examples: int = 0
    features_used: tuple[str, ...] = ()
    #: Observed value domain of every *categorical* feature the tree splits on.
    #: A decision tree's last leaf is a conjunction of negations, so without this
    #: an entry carrying a value that never appeared in training would silently
    #: inherit the catch-all route instead of abstaining.
    categorical_domains: dict[str, tuple[Any, ...]] = field(default_factory=dict)

    def stable_leaves(self) -> list[RouteLeaf]:
        return [
            l
            for l in self.leaves
            if l.stable and l.purity >= self.min_purity and l.support >= self.min_support
        ]

    def out_of_domain(self, features: dict[str, Any]) -> tuple[str, ...]:
        """Split features whose value was never observed while fitting."""

        return tuple(
            path
            for path, domain in sorted(self.categorical_domains.items())
            if features.get(path) not in domain
        )

    def route(self, features: dict[str, Any]) -> RouteLeaf | None:
        """The matching stable leaf, or ``None`` to abstain.

        Abstention is the answer for an unmodelled categorical value even when a
        negation-only leaf would formally match it: the leaf's measured purity was
        never evidence about that value.
        """

        if self.out_of_domain(features):
            return None
        for leaf in self.stable_leaves():
            if leaf.matches(features):
                return leaf
        return None

    def report(self) -> str:
        lines = [
            "route tree",
            "──────────",
            f"examples {self.n_examples}  depth≤{self.max_depth}  "
            f"min_support={self.min_support}  min_purity={self.min_purity}",
        ]
        for leaf in self.leaves:
            lines.append("  " + leaf.pretty())
        for path, domain in sorted(self.categorical_domains.items()):
            values = ", ".join(repr(v) for v in domain)
            lines.append(f"  domain  {path} ∈ {{{values}}}  (anything else abstains)")
        return "\n".join(lines)


def build_examples(
    episodes: Sequence[Episode],
    allowlist: Sequence[str],
    *,
    label_fn: Callable[[Episode], str] = default_route_label,
) -> list[RouteExample]:
    out: list[RouteExample] = []
    for ep in episodes:
        feats: dict[str, Any] = {}
        for path in allowlist:
            v = resolve_path(ep.entry_state, path)
            if isinstance(v, (str, int, float, bool)) or v is None:
                feats[path] = v
        out.append(
            RouteExample(
                episode_id=ep.episode_id,
                group_id=ep.group_id,
                day=ep.envelope.day,
                principal=ep.envelope.principal,
                tenant=ep.envelope.tenant_partition,
                features=feats,
                label=label_fn(ep),
            )
        )
    return out


def _candidate_splits(examples: Sequence[RouteExample], paths: Sequence[str]) -> list[tuple[str, str, Any]]:
    splits: list[tuple[str, str, Any]] = []
    for path in paths:
        values = [e.features.get(path) for e in examples]
        distinct = [v for v in dict.fromkeys(values) if v is not None]
        if not distinct or len(distinct) > 24:
            continue
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in distinct):
            for v in sorted(distinct)[1:]:
                splits.append((path, ">=", v))
        else:
            for v in distinct:
                splits.append((path, "==", v))
    return splits


def _purity(examples: Sequence[RouteExample]) -> tuple[str, float]:
    if not examples:
        return "", 0.0
    counts = Counter(e.label for e in examples)
    label, n = counts.most_common(1)[0]
    return label, n / len(examples)


def _matches(example: RouteExample, split: tuple[str, str, Any]) -> bool:
    path, op, const = split
    v = example.features.get(path)
    if op == "==":
        return v == const
    if op == ">=":
        return isinstance(v, (int, float)) and v >= const
    return False


def fit_route_tree(
    episodes: Sequence[Episode],
    allowlist: Sequence[str],
    *,
    label_fn: Callable[[Episode], str] = default_route_label,
    max_depth: int = 3,
    min_support: int = 20,
    min_purity: float = 0.90,
    min_groups: int = 10,
) -> RouteTree:
    examples = build_examples(episodes, allowlist, label_fn=label_fn)
    tree = RouteTree(
        max_depth=max_depth,
        min_support=min_support,
        min_purity=min_purity,
        n_examples=len(examples),
    )
    if not examples:
        return tree
    tree.majority_label = _purity(examples)[0]
    used: set[str] = set()

    def recurse(subset: Sequence[RouteExample], preds: tuple[tuple[str, str, Any], ...], depth: int) -> None:
        label, purity = _purity(subset)
        groups = {e.group_id for e in subset}
        if (
            purity >= min_purity
            and len(subset) >= min_support
            and len(groups) >= min_groups
        ) or depth >= max_depth:
            if len(subset) >= min_support and len(groups) >= min_groups:
                leaf = RouteLeaf(
                    predicates=preds,
                    label=label,
                    support=len(subset),
                    purity=purity,
                    coverage=len(subset) / len(examples),
                    group_support=len(groups),
                )
                stable, why = _check_stability(subset, label, min_purity)
                leaf.stable = stable
                leaf.instability = why
                tree.leaves.append(leaf)
            return

        best: tuple[float, tuple[str, str, Any]] | None = None
        for split in _candidate_splits(subset, allowlist):
            left = [e for e in subset if _matches(e, split)]
            right = [e for e in subset if not _matches(e, split)]
            if len(left) < min_support or len(right) < min_support:
                continue
            gain = (
                len(left) * _purity(left)[1] + len(right) * _purity(right)[1]
            ) / len(subset)
            if gain <= purity + 1e-9:
                continue
            if best is None or gain > best[0]:
                best = (gain, split)
        if best is None:
            if len(subset) >= min_support and len(groups) >= min_groups:
                leaf = RouteLeaf(
                    predicates=preds,
                    label=label,
                    support=len(subset),
                    purity=purity,
                    coverage=len(subset) / len(examples),
                    group_support=len(groups),
                )
                stable, why = _check_stability(subset, label, min_purity)
                leaf.stable = stable
                leaf.instability = why
                tree.leaves.append(leaf)
            return

        _, split = best
        used.add(split[0])
        left = [e for e in subset if _matches(e, split)]
        right = [e for e in subset if not _matches(e, split)]
        recurse(left, preds + (split,), depth + 1)
        neg = (split[0], "!=" if split[1] == "==" else "<", split[2])
        recurse(right, preds + (neg,), depth + 1)

    recurse(examples, (), 0)
    tree.features_used = tuple(sorted(used))
    # Only categorical splits get a domain: a ">=" threshold on a numeric feature
    # extrapolates by construction, and pinning it to observed values would reject
    # ordinary in-range inputs.
    categorical = {
        path
        for leaf in tree.leaves
        for path, op, _const in leaf.predicates
        if op in ("==", "!=")
    }
    tree.categorical_domains = {
        path: tuple(
            sorted(
                {e.features.get(path) for e in examples if e.features.get(path) is not None},
                key=repr,
            )
        )
        for path in sorted(categorical)
    }
    return tree


def _check_stability(
    subset: Sequence[RouteExample], label: str, min_purity: float
) -> tuple[bool, str]:
    """Temporal and subgroup stability of a leaf's route label."""

    days = sorted({e.day for e in subset})
    if len(days) >= 4:
        mid = days[len(days) // 2]
        early = [e for e in subset if e.day < mid]
        late = [e for e in subset if e.day >= mid]
        for name, part in (("early", early), ("late", late)):
            if len(part) >= 8:
                acc = sum(1 for e in part if e.label == label) / len(part)
                if acc < min_purity - 0.05:
                    return False, f"temporal:{name}={acc:.2f}"
    by_principal: dict[str, list[RouteExample]] = defaultdict(list)
    for e in subset:
        by_principal[f"{e.tenant}/{e.principal}"].append(e)
    for key, part in by_principal.items():
        if len(part) >= 8:
            acc = sum(1 for e in part if e.label == label) / len(part)
            if acc < min_purity - 0.05:
                return False, f"subgroup:{key}={acc:.2f}"
    return True, ""
