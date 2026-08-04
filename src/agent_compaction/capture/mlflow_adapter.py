"""MLflow backend: transport, storage, search — never the compiler IR.

MLflow is a plane *beneath* the versioned trace contract (proposal §5.5). This module
does three things and refuses to do a fourth:

* ``configure`` — configure the MLflow transport and record the selected capture
  policy. Applications still own reconciliation when another exporter is installed.
* ``export_episodes`` — write typed episodes as MLflow traces with the compaction
  attributes that neither the SDK nor MLflow can infer (entry state, principal,
  effect class, external-state version, approval scope, outcome).
* ``load_episodes`` — read them back into the compiler's own IR.

What it will not do is treat an MLflow trace as a replay input: request/response
previews can be truncated, and parent/child structure encodes containment, not
dataflow or effects. Raw complete payloads live in the append-only store; MLflow is
the queryable index over them.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Sequence

from ..schema.traces import Episode, EventKind

__all__ = [
    "flush",
    "MlflowUnavailable",
    "TracerConflict",
    "available",
    "configure",
    "export_episodes",
    "load_episodes",
    "PINNED_MLFLOW",
]

#: proposal §5.5 pins a version rather than depending on drifting ``/latest/``
#: behaviour. 3.14.0 was the pinned release; anything ``>=3.14`` is accepted and the
#: actual version is recorded in the run manifest.
PINNED_MLFLOW = "3.14.0"

SPAN_PREFIX = "compaction"


class MlflowUnavailable(RuntimeError):
    """The optional ``mlflow`` extra is not installed."""


class TracerConflict(RuntimeError):
    """A second exporter already owns the span tree (the one-tracer rule)."""


def available() -> bool:
    try:
        import mlflow  # noqa: F401
    except Exception:
        return False
    return True


def _require() -> Any:
    try:
        import mlflow
    except Exception as exc:  # pragma: no cover - optional extra
        raise MlflowUnavailable("install the 'mlflow' extra to use this backend") from exc
    return mlflow


def configure(
    *,
    experiment: str,
    tracking_uri: str | None = None,
    entry_state_allowlist: Sequence[str] = (),
    effect_catalog: str | None = None,
    autolog: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Configure one authoritative tracer and return the capture manifest."""

    mlflow = _require()
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment)

    installed = getattr(mlflow, "__version__", "unknown")
    if not force and _version_tuple(installed) < _version_tuple(PINNED_MLFLOW):
        raise TracerConflict(
            f"mlflow {installed} is older than the pinned {PINNED_MLFLOW}; pass force=True to override"
        )

    if autolog:
        # Autolog is the *convenience* mode of proposal §5.5. It can clear existing SDK
        # trace processors, so coexistence is asserted rather than assumed.
        try:
            mlflow.openai.autolog()
        except Exception as exc:  # pragma: no cover - depends on the optional integration
            raise TracerConflict(f"could not install the MLflow OpenAI autologger: {exc}") from exc

    return {
        "backend": "mlflow",
        "mlflow_version": installed,
        "pinned": PINNED_MLFLOW,
        "experiment": experiment,
        "tracking_uri": tracking_uri or mlflow.get_tracking_uri(),
        "entry_state_allowlist": list(entry_state_allowlist),
        "effect_catalog": effect_catalog,
        "mode": "convenience" if autolog else "authoritative",
        "sampling_ratio": 1.0,
    }


def _version_tuple(value: str) -> tuple[int, ...]:
    """Parse numeric release components without lexicographic-version bugs."""

    import re

    parts = [int(p) for p in re.findall(r"\d+", value)[:3]]
    return tuple(parts + [0] * (3 - len(parts)))


def _attributes(episode: Episode) -> dict[str, Any]:
    env = episode.envelope
    return {
        f"{SPAN_PREFIX}.episode_id": env.episode_id,
        f"{SPAN_PREFIX}.group_id": env.group_id,
        f"{SPAN_PREFIX}.principal": env.principal,
        f"{SPAN_PREFIX}.tenant_partition": env.tenant_partition,
        f"{SPAN_PREFIX}.policy_version": env.policy_version,
        f"{SPAN_PREFIX}.day": env.day,
        f"{SPAN_PREFIX}.manifest": json.dumps(asdict(episode.manifest), default=str),
        f"{SPAN_PREFIX}.entry_state": json.dumps(episode.entry_state, default=str),
        f"{SPAN_PREFIX}.external_state_version": env.external_state_version,
        f"{SPAN_PREFIX}.approval_scope": env.approval_scope or "",
        f"{SPAN_PREFIX}.outcome": json.dumps(asdict(episode.outcome), default=str),
        f"{SPAN_PREFIX}.privacy_class": env.privacy_class,
        f"{SPAN_PREFIX}.events": json.dumps([e.to_dict() for e in episode.events], default=str),
        f"{SPAN_PREFIX}.final_state_digest": episode.final_state_digest,
    }


def export_episodes(
    episodes: Sequence[Episode],
    *,
    experiment: str,
    tracking_uri: str | None = None,
    allow_sensitive_data: bool = False,
) -> list[str]:
    """Write episodes as MLflow traces. Returns the created trace ids.

    Compiler replay needs complete tool payloads.  Episodes classified above
    ``internal`` therefore require a deliberate opt-in; this prevents an innocuous
    backend call from silently exporting restricted data to a remote tracking store.
    """

    restricted = sorted(
        episode.episode_id
        for episode in episodes
        if episode.envelope.privacy_class not in {"public", "internal"}
    )
    if restricted and not allow_sensitive_data:
        raise ValueError(
            "refusing to export restricted trace payloads without "
            f"allow_sensitive_data=True: {restricted[:5]}"
        )

    mlflow = _require()
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment)
    trace_ids: list[str] = []
    for ep in episodes:
        with mlflow.start_span(name=f"episode:{ep.episode_id}") as root:
            root.set_attributes(_attributes(ep))
            root.set_inputs({"entry_state": ep.entry_state})
            root.set_outputs({"answer": ep.attributes.get("answer", {})})
            for ev in ep.events:
                if ev.kind is not EventKind.TOOL_CALL:
                    continue
                with mlflow.start_span(name=ev.tool or "tool") as child:
                    child.set_inputs(ev.input if isinstance(ev.input, dict) else {"input": ev.input})
                    child.set_attributes({f"{SPAN_PREFIX}.node_id": ev.node_id})
            trace_ids.append(root.trace_id)
    # proposal §5.5: authoritative capture means synchronous export or an explicit
    # flush, followed by count reconciliation. Without the flush, a short-lived job
    # exits with traces still queued and the corpus silently loses episodes.
    flush()
    stored_ids = _trace_ids(
        _search_traces(
            mlflow,
            mlflow.get_experiment_by_name(experiment).experiment_id,
            max_results=max(1000, len(trace_ids) * 2),
        )
    )
    missing = sorted(set(trace_ids) - stored_ids)
    if missing:
        raise TracerConflict(
            "trace reconciliation failed: the tracking store is missing "
            f"{len(missing)} of {len(trace_ids)} new trace ids"
        )
    return trace_ids


def flush() -> None:
    """Flush any queued trace exports. Safe to call when nothing is queued."""

    mlflow = _require()
    for name in ("flush_trace_async_logging", "flush_async_logging"):
        fn = getattr(mlflow, name, None)
        if fn is not None:
            try:
                fn()
            except Exception:  # pragma: no cover - best effort across versions
                continue


def _count_traces(mlflow: Any, experiment: str) -> int:
    exp = mlflow.get_experiment_by_name(experiment)
    if exp is None:
        return 0
    return len(_search_traces(mlflow, exp.experiment_id, max_results=10_000))


def _trace_ids(traces: Sequence[Any]) -> set[str]:
    return {
        str(getattr(getattr(trace, "info", None), "trace_id", ""))
        for trace in traces
        if getattr(getattr(trace, "info", None), "trace_id", None)
    }


def load_episodes(
    *, experiment: str, tracking_uri: str | None = None, max_results: int = 1000
) -> list[Episode]:
    """Read episodes back from MLflow traces written by :func:`export_episodes`.

    Only traces that carry the full compaction attribute set are returned: a trace
    without them is an operational record, not a compiler input.
    """

    mlflow = _require()
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)
    exp = mlflow.get_experiment_by_name(experiment)
    if exp is None:
        return []
    traces = _search_traces(mlflow, exp.experiment_id, max_results=max_results)
    out: list[Episode] = []
    for tr in traces:
        attrs = _root_attributes(tr)
        if f"{SPAN_PREFIX}.events" not in attrs:
            continue
        out.append(_episode_from_attributes(tr, attrs))
    return out


def _search_traces(mlflow: Any, experiment_id: str, *, max_results: int) -> list[Any]:
    """Use MLflow's current ``locations`` surface with a legacy fallback."""

    import inspect

    params = inspect.signature(mlflow.search_traces).parameters
    kwargs: dict[str, Any] = {"max_results": max_results, "return_type": "list"}
    if "locations" in params:
        kwargs["locations"] = [experiment_id]
    else:  # pragma: no cover - older supported MLflow releases
        kwargs["experiment_ids"] = [experiment_id]
    return list(mlflow.search_traces(**kwargs))


def _root_attributes(trace: Any) -> dict[str, Any]:
    spans = getattr(getattr(trace, "data", None), "spans", None) or []
    for span in spans:
        attrs = dict(getattr(span, "attributes", {}) or {})
        if f"{SPAN_PREFIX}.events" in attrs:
            return attrs
    tags = dict(getattr(getattr(trace, "info", None), "tags", {}) or {})
    return tags


def _episode_from_attributes(trace: Any, attrs: dict[str, Any]) -> Episode:
    from ..schema.traces import EventNode, ExecutionManifest, OutcomeLabels, TraceEnvelope

    def _get(key: str, default: Any = "") -> Any:
        return attrs.get(f"{SPAN_PREFIX}.{key}", default)

    def _json(key: str, default: Any) -> Any:
        raw = _get(key)
        if isinstance(raw, str) and raw:
            return json.loads(raw)
        return raw or default

    manifest = ExecutionManifest(**_json("manifest", {"manifest_id": "unknown"}))
    envelope = TraceEnvelope(
        trace_id=str(getattr(getattr(trace, "info", None), "trace_id", "unknown")),
        episode_id=str(_get("episode_id", "unknown")),
        group_id=str(_get("group_id", "unknown")),
        manifest_id=manifest.manifest_id,
        principal=str(_get("principal", "unknown")),
        tenant_partition=str(_get("tenant_partition", "unknown")),
        policy_version=str(_get("policy_version", "v0")),
        day=str(_get("day", "1970-01-01")),
        privacy_class=str(_get("privacy_class", "internal")),
        external_state_version=str(_get("external_state_version", "unknown")),
        approval_scope=(_get("approval_scope") or None),
    )
    return Episode(
        envelope=envelope,
        manifest=manifest,
        entry_state=_json("entry_state", {}),
        events=[EventNode.from_dict(d) for d in _json("events", [])],
        outcome=OutcomeLabels(**_json("outcome", {})),
        final_state_digest=str(_get("final_state_digest", "")),
        attributes={"backend": "mlflow"},
    )


# ---------------------------------------------------------------------------
# JSONL backend (always available; the reproducibility artifact format)
# ---------------------------------------------------------------------------


def write_jsonl(episodes: Iterable[Episode], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as fh:
        for ep in episodes:
            fh.write(json.dumps(ep.to_dict(), default=str) + "\n")
    return p


def read_jsonl(path: str | Path) -> list[Episode]:
    return [
        Episode.from_dict(json.loads(line))
        for line in Path(path).read_text().splitlines()
        if line.strip()
    ]
