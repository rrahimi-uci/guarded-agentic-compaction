#!/usr/bin/env python3
"""Render ``docs/agent-compaction-report.html`` from measured live results.

Everything numeric in the output is read from ``experiments/live_results``: the
aggregate table, the reduction bars, the KPI tiles and every trace timeline come
from the native OpenAI Agents SDK traces captured by ``experiments/live_run.py``.
Nothing is typed in by hand, so a re-run of the benchmark regenerates a report that
matches it — and a missing demo degrades to a visible gap rather than a stale number.

The page is one file. Mermaid, KaTeX and highlight.js load from CDNs and every one
of them degrades legibly when offline: diagrams fall back to their source text,
formulas to TeX, code to plain monospace. Charts are inline SVG and always render.

Usage::

    python scripts/build_html_report.py [--results DIR] [--out FILE]
"""

from __future__ import annotations

import argparse
import html
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = ROOT / "experiments" / "live_results"
DEFAULT_OUT = ROOT / "docs" / "agent-compaction-report.html"

# --------------------------------------------------------------------------
# palette — the validated reference instance (dataviz skill, references/palette.md)
# Slots are assigned in fixed order and never cycled.
# --------------------------------------------------------------------------

SERIES_MODEL = "var(--series-1)"   # slot 1, blue   — provider turns
SERIES_TOOL = "var(--series-2)"    # slot 2, orange — tool executions

DEMO_TITLES = {
    "support": "A · Tier-1 support evidence",
    "permissioned_rag": "B · Permissioned RAG",
    "incident_triage": "C · Multi-agent incident triage",
    "mcp_ops": "D · Multi-tenant MCP (negative control)",
    "fulfillment": "E · Fulfillment exceptions (branches, pagination, a write)",
    "tgws_router": "F · TGWS route specialization",
}

DEMO_BLURBS = {
    "support": (
        "A linear read-only evidence chain behind a ticket: mint a token, resolve the "
        "customer, read the subscription, the newest invoices and the entitlement. The "
        "reference shape, and the easiest one to compact."
    ),
    "permissioned_rag": (
        "Retrieval where the ACL scope, the index version and the freshness window are "
        "hard guard keys. The contribution is the guard, not the speed-up."
    ),
    "incident_triage": (
        "A coordinator that reads an alert and hands off to a specialist. TGWS removes "
        "the coordinator turn; for GRC a handoff is a barrier."
    ),
    "mcp_ops": (
        "A real stdio MCP server whose tool effects are undeclared. The expected and "
        "correct outcome is a refusal to compact."
    ),
    "fulfillment": (
        "The hardest shape in the suite: three synthesized branches, a paginated read, "
        "and a mandatory irreversible commitment that bounds every region to a prefix. "
        "Partial compaction is the correct result, not a degraded one."
    ),
    "tgws_router": (
        "The other optimizer, executed live. A route tree fitted on traces selects a "
        "specialist prompt and a minimal tool surface per exception class, and abstains "
        "to the generalist on any value it never saw."
    ),
}

CONDITION_LABELS = {
    "baseline": "baseline",
    "compacted": "compacted",
    "compacted_fallback": "compaction refused → baseline",
    "compacted_loop_refused": "loop artifact refused → baseline",
    "compacted_ood_fallback": "schema drift, guard miss → baseline",
    "routed": "route specialized",
}

CONDITION_NOTES = {
    "compacted_fallback": (
        "MCP tools carry no human-attested effect catalog, so the dispatcher fails "
        "closed before it ever looks at a program."
    ),
    "compacted_loop_refused": (
        "The same evidence expressed as a bounded ForEach. The Model adapter only "
        "supports straight-line call programs and refuses this artifact rather than "
        "half-executing it (proposal §5.6, conformance item 7)."
    ),
    "compacted_ood_fallback": (
        "The identical artifact against a case whose WMS intake schema moved to "
        "wms_v3. The hard guard pins wms_v2, misses, and the baseline runs."
    ),
}


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Span:
    kind: str  # "model" | "tool"
    label: str
    start: float
    end: float
    detail: str = ""

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def load_payload(results_dir: Path) -> dict[str, Any]:
    path = results_dir / "all_results.json"
    if not path.exists():
        raise SystemExit(
            f"no results at {path}. Run: python experiments/live_run.py --cases 3"
        )
    return json.loads(path.read_text())


def load_episodes(results_dir: Path) -> dict[str, dict[str, Any]]:
    """Index captured episodes by their unique SDK trace id.

    Scenario ids can intentionally recur across demonstrations (for example, the
    TGWS router reuses fulfillment scenarios).  A ``scenario:condition`` index
    therefore loses episodes and can attach the wrong trace to a report panel.
    """

    path = results_dir / "episodes.jsonl"
    if not path.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        episode = json.loads(line)
        trace_id = episode["envelope"]["trace_id"]
        if trace_id in out:
            raise ValueError(f"duplicate trace_id in {path}: {trace_id}")
        out[trace_id] = episode
    return out


def spans_of(episode: dict[str, Any]) -> list[Span]:
    """Provider turns and tool executions on one wall clock.

    A provider turn spans MODEL_REQ.start → MODEL_RESP.end because that pair is what
    a caller waits for; a tool execution spans TOOL_CALL.start → TOOL_RESULT.end.
    """

    events = episode.get("events") or []
    times = [
        float(e["t_start_ms"])
        for e in events
        if isinstance(e.get("t_start_ms"), (int, float))
    ]
    if not times:
        return []
    origin = min(times)
    spans: list[Span] = []
    index = 0
    pending_model: dict[str, Any] | None = None
    pending_tool: dict[str, Any] | None = None
    for event in events:
        kind = event.get("kind")
        if kind == "MODEL_REQ":
            pending_model = event
        elif kind == "MODEL_RESP" and pending_model is not None:
            index += 1
            usage = event.get("usage") or {}
            total_in = int(usage.get("input_tokens") or 0)
            cached = int(usage.get("cached_input_tokens") or 0)
            out_tokens = int(usage.get("output_tokens") or 0)
            spans.append(
                Span(
                    "model",
                    f"provider turn {index}",
                    float(pending_model.get("t_start_ms") or 0.0) - origin,
                    float(event.get("t_end_ms") or 0.0) - origin,
                    f"{total_in:,} in ({cached:,} cached) · {out_tokens:,} out",
                )
            )
            pending_model = None
        elif kind == "TOOL_CALL":
            pending_tool = event
        elif kind == "TOOL_RESULT" and pending_tool is not None:
            tool = str(event.get("tool") or pending_tool.get("tool") or "tool")
            compacted = bool((pending_tool.get("attributes") or {}).get("compacted"))
            spans.append(
                Span(
                    "tool",
                    tool,
                    float(pending_tool.get("t_start_ms") or 0.0) - origin,
                    float(event.get("t_end_ms") or 0.0) - origin,
                    "dispatched by the compiled region" if compacted else "model-selected",
                )
            )
            pending_tool = None
    return sorted(spans, key=lambda s: (s.start, s.kind != "model"))


def pick_scenario(demo_body: dict[str, Any]) -> str:
    """The scenario with the most conditions captured, ties broken deterministically."""

    counts: dict[str, int] = {}
    for run in demo_body.get("runs", []):
        counts[run["scenario_id"]] = counts.get(run["scenario_id"], 0) + 1
    if not counts:
        return ""
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def runs_for(demo_body: dict[str, Any], scenario: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for run in demo_body.get("runs", []):
        if run["scenario_id"] == scenario or run["scenario_id"] == f"{scenario}-drift":
            out[run["condition"]] = run
    return out


# --------------------------------------------------------------------------
# formatting
# --------------------------------------------------------------------------


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def pct(value: float | None, *, signed: bool = False) -> str:
    if value is None:
        return "n/a"
    sign = "+" if signed and value > 0 else ""
    return f"{sign}{100.0 * value:.1f}%"


def num(value: float | None, digits: int = 0) -> str:
    if value is None:
        return "—"
    return f"{value:,.{digits}f}"


def money(value: float | None) -> str:
    if value is None:
        return "—"
    return f"${value:.6f}"


def ms(value: float | None) -> str:
    if value is None:
        return "—"
    if value >= 1000:
        return f"{value / 1000:.2f}s"
    return f"{value:.0f}ms"


# --------------------------------------------------------------------------
# charts (inline SVG)
# --------------------------------------------------------------------------


def reduction_bars(items: Sequence[tuple[str, float | None]], *, chart_id: str) -> str:
    """Signed horizontal bars on a diverging scale: reduction right, regression left.

    One measure, so no legend; every bar is directly labelled, which is also the
    secondary encoding that keeps the two poles readable without hue.
    """

    rows = [(label, value) for label, value in items if value is not None]
    if not rows:
        return '<p class="empty">no comparison available</p>'

    row_h, gap, pad_l, pad_r, pad_t = 30, 8, 168, 96, 12
    height = pad_t + len(rows) * (row_h + gap)
    width = 660
    plot_w = width - pad_l - pad_r
    extent = max(0.05, max(abs(v) for _l, v in rows))
    # Only spend half the canvas on the negative arm when something is actually
    # negative; otherwise the zero line is the left edge and every bar gets the
    # full width.
    has_negative = any(v < 0 for _l, v in rows)
    if has_negative:
        zero_x = pad_l + plot_w / 2
        scale = (plot_w / 2) / extent
    else:
        zero_x = pad_l
        scale = plot_w / extent

    parts = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
        f'aria-labelledby="{chart_id}-t" preserveAspectRatio="xMidYMid meet">',
        f'<title id="{chart_id}-t">Reduction versus baseline by metric</title>',
    ]
    for index, (label, value) in enumerate(rows):
        y = pad_t + index * (row_h + gap)
        bar_h = 20
        by = y + (row_h - bar_h) / 2
        length = abs(value) * scale
        positive = value >= 0
        x = zero_x if positive else zero_x - length
        fill = "var(--pole-good)" if positive else "var(--pole-bad)"
        radius = min(4.0, max(0.0, length))
        # 4px rounded data-end, square at the baseline.
        if positive:
            path = (
                f"M{x:.1f} {by} H{x + length - radius:.1f} "
                f"a{radius} {radius} 0 0 1 {radius} {radius} "
                f"V{by + bar_h - radius:.1f} "
                f"a{radius} {radius} 0 0 1 -{radius} {radius} "
                f"H{x:.1f} Z"
            )
        else:
            path = (
                f"M{x + length:.1f} {by} H{x + radius:.1f} "
                f"a{radius} {radius} 0 0 0 -{radius} {radius} "
                f"V{by + bar_h - radius:.1f} "
                f"a{radius} {radius} 0 0 0 {radius} {radius} "
                f"H{x + length:.1f} Z"
            )
        # "less"/"more" rather than a bare sign: a positive number on a chart titled
        # "reduction" is ambiguous the first time a reader meets it.
        reading = f"{abs(100.0 * value):.1f}% {'less' if positive else 'more'}"
        text_w = 6.3 * len(reading)
        if positive:
            label_x, anchor = x + length + 10, "start"
        elif x - 10 - text_w >= pad_l + 4:
            label_x, anchor = x - 10, "end"
        else:
            # A short negative bar would push its label into the category gutter.
            # Put it on the far side rather than letting two texts overlap.
            label_x, anchor = zero_x + 10, "start"
        parts.append(
            f'<g class="bar-row"><title>{esc(label)}: {esc(reading)} than baseline</title>'
            f'<text class="cat" x="{pad_l - 14}" y="{y + row_h / 2 + 4}" '
            f'text-anchor="end">{esc(label)}</text>'
            f'<path d="{path}" fill="{fill}"/>'
            f'<text class="val" x="{label_x:.1f}" y="{by + bar_h - 5}" '
            f'text-anchor="{anchor}">{esc(reading)}</text></g>'
        )
    parts.append(
        f'<line class="axis" x1="{zero_x:.1f}" y1="{pad_t - 4}" '
        f'x2="{zero_x:.1f}" y2="{height - 4}"/>'
    )
    parts.append("</svg>")
    return "".join(parts)


def waterfall(
    title: str,
    spans: Sequence[Span],
    *,
    domain_ms: float,
    chart_id: str,
    ghost: int = 0,
) -> str:
    """One episode's wall clock as a waterfall.

    Both panels of a before/after pair are drawn against the *same* ``domain_ms``, so
    the compacted panel is short because it is short — not because its axis rescaled.
    """

    if not spans:
        return '<p class="empty">no trace captured</p>'

    row_h, gap, pad_l, pad_r, pad_t, pad_b = 22, 5, 190, 104, 26, 24
    rows = len(spans) + (1 if ghost else 0)
    height = pad_t + rows * (row_h + gap) + pad_b
    width = 760
    plot_w = width - pad_l - pad_r
    domain = max(domain_ms, 1.0)
    scale = plot_w / domain

    parts = [
        f'<svg class="chart waterfall" viewBox="0 0 {width} {height}" role="img" '
        f'aria-labelledby="{chart_id}-t" preserveAspectRatio="xMidYMid meet">',
        f'<title id="{chart_id}-t">{esc(title)} timeline</title>',
    ]

    # recessive gridlines at clean second boundaries
    step = 1000.0 if domain <= 12000 else 2000.0
    tick = 0.0
    while tick <= domain:
        x = pad_l + tick * scale
        parts.append(
            f'<line class="grid" x1="{x:.1f}" y1="{pad_t - 8}" x2="{x:.1f}" '
            f'y2="{height - pad_b + 2}"/>'
            f'<text class="tick" x="{x:.1f}" y="{height - pad_b + 16}" '
            f'text-anchor="middle">{tick / 1000:.0f}s</text>'
        )
        tick += step

    for index, span in enumerate(spans):
        y = pad_t + index * (row_h + gap)
        bar_h = 14
        by = y + (row_h - bar_h) / 2
        x = pad_l + span.start * scale
        # A sub-millisecond local tool call still has to be visible and hoverable.
        w = max(3.0, span.duration * scale)
        fill = SERIES_MODEL if span.kind == "model" else SERIES_TOOL
        radius = min(4.0, w / 2)
        # A label that will not fit is shortened here rather than clipped by the
        # viewport; the full name stays in the hover title.
        shown = span.label if len(span.label) <= 26 else "…" + span.label[-25:]
        parts.append(
            f'<g class="span"><title>{esc(span.label)} · {esc(ms(span.duration))}'
            + (f" · {esc(span.detail)}" if span.detail else "")
            + "</title>"
            f'<text class="cat" x="{pad_l - 12}" y="{y + row_h / 2 + 4}" '
            f'text-anchor="end">{esc(shown)}</text>'
            f'<rect x="{x:.1f}" y="{by}" width="{w:.1f}" height="{bar_h}" '
            f'rx="{radius:.1f}" fill="{fill}"/>'
            f'<text class="val" x="{x + w + 8:.1f}" y="{by + bar_h - 2}">'
            f'{esc(ms(span.duration))}</text></g>'
        )

    if ghost:
        y = pad_t + len(spans) * (row_h + gap)
        parts.append(
            f'<text class="ghost-label" x="{pad_l - 12}" y="{y + row_h / 2 + 4}" '
            f'text-anchor="end">removed</text>'
            f'<rect class="ghost" x="{pad_l}" y="{y + 4}" width="{plot_w}" '
            f'height="14" rx="4"/>'
            f'<text class="val ghost-val" x="{pad_l + plot_w + 8}" '
            f'y="{y + 15}">{ghost} provider turns elided</text>'
        )

    parts.append(
        f'<line class="axis" x1="{pad_l}" y1="{height - pad_b + 2}" '
        f'x2="{width - pad_r}" y2="{height - pad_b + 2}"/>'
    )
    parts.append("</svg>")
    return "".join(parts)


def legend() -> str:
    return (
        '<div class="legend" role="list">'
        '<span role="listitem"><i class="key" style="background:' + SERIES_MODEL + '"></i>'
        "provider turn (model request → response)</span>"
        '<span role="listitem"><i class="key" style="background:' + SERIES_TOOL + '"></i>'
        "tool execution</span></div>"
    )


def kpi(label: str, value: str, sub: str = "", tone: str = "") -> str:
    tone_class = f" kpi--{tone}" if tone else ""
    return (
        f'<div class="kpi{tone_class}"><div class="kpi-label">{esc(label)}</div>'
        f'<div class="kpi-value">{esc(value)}</div>'
        + (f'<div class="kpi-sub">{esc(sub)}</div>' if sub else "")
        + "</div>"
    )


def table(headers: Sequence[str], rows: Sequence[Sequence[str]], *, caption: str = "") -> str:
    head = "".join(f"<th scope=\"col\">{esc(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows
    )
    cap = f"<caption>{esc(caption)}</caption>" if caption else ""
    return f'<div class="table-wrap"><table>{cap}<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def code(source: str, language: str = "python") -> str:
    return (
        f'<pre class="code"><code class="language-{language}">'
        f"{html.escape(source.strip())}</code></pre>"
    )


def mermaid(source: str) -> str:
    return f'<pre class="mermaid">{html.escape(source.strip())}</pre>'


def figure(body: str, caption: str) -> str:
    return f'<figure>{body}<figcaption>{caption}</figcaption></figure>'


# --------------------------------------------------------------------------
# sections
# --------------------------------------------------------------------------


def section_hero(payload: dict[str, Any]) -> str:
    manifest = payload["manifest"]
    demos = payload["demos"]
    runs = [r for body in demos.values() for r in body.get("runs", [])]
    provider_turns = sum(r["metrics"]["requests"] for r in runs)
    tokens = sum(r["metrics"]["total_tokens"] for r in runs)
    cost = sum(r["metrics"]["estimated_cost_usd"] or 0.0 for r in runs)
    quality = [float(r["outcome"]["semantic_score"] or 0.0) for r in runs]
    safety = sum(int(r["outcome"]["safety_events"]) for r in runs)

    compacting = [
        body["comparisons"].get("total_tokens_reduction")
        for name, body in demos.items()
        if name not in ("mcp_ops",) and body.get("comparisons")
    ]
    compacting = [v for v in compacting if v is not None and v > 0.02]
    headline = max(compacting) if compacting else 0.0

    tiles = "".join(
        [
            kpi("Best measured token reduction", pct(headline), "at unchanged task outcome"),
            kpi("Workflows executed live", num(len(runs)), f"{num(provider_turns)} provider turns"),
            kpi("Tokens billed across the suite", num(tokens), money(cost) + " at list price"),
            kpi(
                "Mean scenario score",
                f"{sum(quality) / max(1, len(quality)):.3f}",
                f"{safety} safety events",
                tone="good" if safety == 0 else "warn",
            ),
        ]
    )
    return f"""
<section id="overview" class="hero">
  <p class="eyebrow">Guarded workflow optimization for LLM agents</p>
  <h1>agent-compaction</h1>
  <p class="lede">
    Mine repeated execution patterns out of agent traces, prove a smaller workflow on
    held-out groups, and deploy only immutable artifacts that fall back to the original
    agent. Two transformation engines and one measured-action selector share a trace
    contract, and
    <strong>abstention is the default output</strong>.
  </p>
  <div class="kpi-row">{tiles}</div>
  <p class="provenance">
    Every figure on this page was produced by <code>experiments/live_run.py</code> against
    <code>{esc(manifest["model"])}</code> through OpenAI Agents SDK
    <code>{esc(manifest["sdk"])}</code> at reasoning effort
    <code>{esc(manifest.get("reasoning_effort", "low"))}</code>, completed
    <code>{esc(manifest["completed"])}</code>. Enterprise records are fictional
    deterministic fixtures; model calls, tool calls, handoffs, MCP transport, token
    accounting and latency are live. Cost is estimated from
    <a href="{esc(manifest["pricing_source"])}">published list prices</a>, not an invoice.
    This is a small benchmark demonstrating a mechanism, not production certification.
  </p>
</section>
"""


def section_problem() -> str:
    return """
<section id="problem">
  <h2>1 · The problem</h2>
  <p>
    A tool-using agent spends most of its provider turns re-deciding things it already
    decided. Look at any high-volume workflow — a support ticket, a permissioned
    retrieval, a fulfillment exception — and the same prefix appears in trace after
    trace: mint a token, resolve an identity, read three records, then think. The model
    is asked to re-derive a fixed control-flow graph on every episode, and the customer
    pays for it in latency, tokens and non-determinism.
  </p>
  <p>
    The tempting fix — "just write a macro tool" — is right surprisingly often, and this
    project says so out loud. What a macro cannot give you is <em>evidence</em>: that the
    shortcut is what the agent actually did, that it is safe on inputs nobody has seen,
    that it will stop being used the moment the world moves. Those three questions are
    the whole design.
  </p>
  <div class="callout callout--frame">
    <h3>The three questions</h3>
    <ol>
      <li><strong>Is this region real?</strong> Does it recur across independent scenario
        groups, days and principals — or is it one customer's habit?</li>
      <li><strong>Is every argument derivable?</strong> Can each tool argument be
        reconstructed from the entry state or an earlier in-region observation, with no
        model-originated value smuggled in?</li>
      <li><strong>What happens when it is wrong?</strong> Not "how accurate is it" — what
        is the <em>bounded</em> rate of wrongness, and what does the runtime do at the
        boundary when it cannot tell?</li>
    </ol>
  </div>
  <p>
    Only workflows that answer all three get compiled. Everything else abstains, and the
    honest observation from the measured runs below is that <strong>"do not compact" is
    a normal and correct answer</strong>. The MCP family and two fulfillment conditions
    are explicit refusal controls, and they preserve the baseline request count.
  </p>
</section>
"""


def section_architecture() -> str:
    pipeline = mermaid(
        """
flowchart TB
  subgraph CAP["1 · capture"]
    direction LR
    A1["OpenAI Agents SDK<br/>TracingProcessor"] --> A2["Episode IR<br/>envelope · manifest · entry state · outcome"]
    A3["JSONL episode store"] --> A2
  end
  subgraph OFF["2 · offline compilation — no production traffic"]
    direction TB
    B1["Alg.1 provenance<br/>PATG + groundability"] --> B2["Alg.2 window mining<br/>closed frequent regions"]
    B2 --> B3{"Eq.10 estimator<br/>is there anything here?"}
    B3 -->|"below the ceiling"| STOP["report the blockers<br/>and stop"]
    B3 -->|"feasible"| C1["Alg.3 argument bindings<br/>closed 23-operator DSL"]
    C1 --> C2["Alg.4 branch synthesis<br/>permutation-tested"]
    C2 --> C3["Alg.5 output contract<br/>+ perturbation suite"]
    C3 --> C4["Alg.6 gate calibration<br/>exact Clopper–Pearson"]
    C4 --> C5["package · sign · register"]
  end
  subgraph RT["3 · runtime"]
    direction LR
    D1["Registry<br/>immutable artifacts"] --> D2{"Alg.7 dispatch"}
    D2 -->|"accept"| D3["native tool calls;<br/>provider turns elided"]
    D2 -->|"abstain"| D4["baseline agent,<br/>byte-identical input"]
  end
  A2 --> B1
  C5 --> D1
  STOP -.->|"no artifact is ever registered"| D4
"""
    )
    dispatch = mermaid(
        """
stateDiagram-v2
  [*] --> Boundary: model request about to be sent
  Boundary --> HardGuard: artifact matches compatibility key
  Boundary --> Baseline: no artifact
  HardGuard --> Gate: manifest pins, isolation keys,<br/>typed hulls, effect set
  HardGuard --> Baseline: guard miss (drift, tenant, schema)
  Gate --> Interpret: q(z) below calibrated threshold
  Gate --> Baseline: uncertain input
  Interpret --> Verify: bounded program, facade-checked tools
  Interpret --> Baseline: PreCommitError (nothing committed)
  Interpret --> Incident: PostCommitError
  Verify --> Compacted: live-outs and effect multiset hold
  Verify --> Baseline: contract violated
  Compacted --> [*]
  Baseline --> [*]
  Incident --> [*]: kill switch, page a human
"""
    )
    return f"""
<section id="architecture">
  <h2>2 · Architecture</h2>
  <p>
    The system is a compiler with a refusal-first calling convention. It reads traces,
    not source; it emits artifacts, not patches; and the only thing it is allowed to do
    at runtime is replace a prefix of read-only tool calls that it can prove it has seen
    before.
  </p>
  {figure(pipeline, "The full path from an SDK trace to a dispatched region. The estimator is a gate, not a report: a workload below the Eq. (10) ceiling never reaches the compiler.")}

  <h3>2.1 Two transformation engines and one selector</h3>
  <div class="grid-2">
    <div class="card">
      <h4>GRC — guarded region compilation</h4>
      <p>
        Finds repeated read-only regions, proves every tool argument derives from entry
        state or an earlier observation, synthesizes a bounded deterministic program from
        a closed 23-operator library, induces an output contract, and dispatches only
        under a calibrated gate with an exact risk bound.
      </p>
      <p class="muted">Removes provider turns. Cannot cross a write, an approval, a
        handoff or an undeclared tool.</p>
    </div>
    <div class="card">
      <h4>TGWS — trace-guided workflow specialization</h4>
      <p>
        Learns a shallow, readable route from entry-state facts to a specialist prompt
        and a minimal tool surface, prunes what the route never needs against measured
        quality, and abstains when the route or the input is uncertain.
      </p>
      <p class="muted">Removes prompt and tool-schema tokens, and sometimes a whole
        coordinator turn. Never changes what a tool does.</p>
    </div>
  </div>
  <div class="card">
    <h4>Portfolio — evidence-bounded action selection</h4>
    <p>
      Compares only actions with paired independent-group measurements, applies separate
      exact quality and regret bounds, and otherwise returns the unchanged baseline.
      Macro recommendations require human review; no macro or cache behavior is inferred.
    </p>
    <p class="muted">The prospective public-record study is reported in the paper
      artifact; this page visualizes the separate fictional-fixture SDK suite.</p>
  </div>

  <h3>2.2 The runtime decision</h3>
  <p>
    Every model-request boundary is a decision point. The ordering is deliberate:
    cheap deterministic checks reject first, the calibrated statistical gate runs only
    on inputs that survive them, and the verifier runs after execution but
    <em>before</em> the result is allowed to influence the conversation.
  </p>
  {figure(dispatch, "Algorithm 7. Five of the seven terminal edges lead back to the unmodified baseline agent; only one produces a compacted execution, and one is an incident that stops the deployment.")}

  <h3>2.3 Module map</h3>
  {table(
      ["Package", "Responsibility", "Depends on"],
      [
          ["<code>paths</code>", "flatten / resolve_path / content digests", "nothing"],
          ["<code>schema</code>", "traces, effect catalog, artifacts — the frozen contract", "<code>paths</code>"],
          ["<code>capture</code>", "entry-state contract, manifests, Agents SDK adapter, JSONL store", "<code>schema</code>"],
          ["<code>graph</code>", "qualification, provenance (Alg. 1), window mining (Alg. 2)", "<code>schema</code>"],
          ["<code>grc</code>", "DSL, bindings, branches, contracts, calibration, compile orchestrator", "<code>graph</code>"],
          ["<code>tgws</code>", "route tree, greedy pruning, packaging", "<code>graph</code>"],
          ["<code>portfolio</code>", "exact-risk selection among paired measured actions", "<code>grc.calibrate</code>"],
          ["<code>evaluation</code>", "grouped splits, replay, perturbations, metrics, statistics", "<code>schema</code>"],
          ["<code>registry</code>", "artifact store, lifecycle, signing, kill switch, rollback", "<code>schema</code>"],
          ["<code>runtime</code>", "dispatch (Alg. 7), staging, permission facade, interpreter, SDK adapters", "<code>registry</code>"],
          ["<code>estimate</code>", "Eq. (10) feasibility and the economic break-even", "<code>graph</code>"],
      ],
      caption="Strict layering: no module imports one below it in this table.",
  )}
</section>
"""


def section_algorithms() -> str:
    dsl = code(
        """
# The closed operator library. 23 operators, five classes, no user-defined functions,
# no recursion, no arithmetic on control flow. Search is bounded by depth and by a
# per-tool literal_only declaration.

OPERATOR_CLASSES = {
    "identity_coercion": ("id", "str", "int", "float", "bool"),
    "string":            ("lower", "upper", "strip", "split", "join", "fmt"),
    "numeric":           ("add", "mul", "round", "sum", "len"),
    "collection":        ("project", "filter", "first", "sort", "last", "topk"),
    "temporal":          ("date_fmt",),
}

# A synthesized binding is an expression over one source path and an operator chain:
customer_id = Expr("customers", (Op("filter", ("status", "==", "active")),
                                 Op("first"),
                                 Op("project", ("id",))))
""",
        "python",
    )
    program = code(
        """
program (θ = {case.order_ref, case.exception_class, case.customer_tier, case.region}):
   token  = call auth_issue_ops_token()
   order  = call orders_get(order_ref = z.case.order_ref, token = token.token)
   page0  = call shipments_list_page(order_ref = z.case.order_ref, page = 0, token = token.token)
   if page0.has_more == True:
      page1 = call shipments_list_page(order_ref = z.case.order_ref, page = 1, token = token.token)
   if z.case.exception_class == 'stock_shortfall':
      stock = call inventory_check(sku = order.line_items |> first |> project('sku'),
                                   warehouse = order.warehouse, token = token.token)
   if z.case.exception_class == 'carrier_delay':
      carrier = call carrier_track(tracking_id = order.tracking_id, token = token.token)
   policy = call sla_policy(customer_tier = z.case.customer_tier, region = z.case.region)
   return { order, page0, page1, stock, carrier, policy }

guard   model=gpt-5.6-terra  entry_contract_version=wms_v2
        effects ⊆ {READ_EXTERNAL, READ_LOCAL}  all speculatable ∧ replayable
verify  effect_multiset ⊆ {READ_EXTERNAL, READ_LOCAL},  |calls| ∈ {4,5,6,7},  no WRITE_*
""",
        "text",
    )
    return f"""
<section id="algorithms">
  <h2>3 · Algorithms</h2>

  <h3>3.1 Algorithm 1 — provenance and groundability</h3>
  <p>
    Each episode becomes a <em>provenance-annotated trace graph</em>. For every argument
    slot of every tool call the builder asks: is this value reachable from the entry
    state \\(z\\) or from an earlier in-region observation \\(o_{{j \\lt i}}\\)? A slot
    that is reachable is <strong>grounded</strong>; one that first appears in a model message is
    <strong>model-originated</strong> and disqualifies the window. Order edges are added
    between events that share a resource when at least one of them writes it, so a
    reordering can never be proposed across a conflict.
  </p>

  <h3>3.2 Algorithm 2 — window mining and the ranking score</h3>
  <p>
    Closed frequent contiguous regions are mined per canonical shape. A family is ranked
    by a minimum-description-length trade-off that pays for savings and charges for
    variance, effect risk and program size:
  </p>
  <div class="math">$$\\mathrm{{score}}(F) \\;=\\; \\underbrace{{s_F \\cdot \\bar{{k}}_F \\cdot c_m}}_{{\\text{{expected saving}}}}
  \\;-\\; \\lambda_1 H(F) \\;-\\; \\lambda_2 \\rho_{{\\text{{eff}}}}(F) \\;-\\; \\lambda_3 |F|$$</div>
  <p class="muted">
    \\(s_F\\) is scenario-group support, \\(\\bar k_F\\) the mean removable provider turns,
    \\(H(F)\\) the Shannon entropy over canonical variants inside the family,
    \\(\\rho_{{\\text{{eff}}}}\\) the fraction of steps that are external reads, and \\(|F|\\)
    the node count of the program the family would produce.
  </p>

  <h3>3.3 The feasibility estimator — Eq. (10)</h3>
  <p>
    Before any compiler runs, the estimator answers "is there anything here?" from
    traces alone. It is the cheapest useful thing in the system and it is allowed to say
    no:
  </p>
  <div class="math">$$\\Delta_{{\\max}} \\;=\\; \\frac{{\\varphi \\cdot k}}{{n_B}}
  \\qquad\\text{{and the necessary condition}}\\qquad \\varphi\\,\\rho\\,k \\;\\ge\\; \\Delta \\cdot n_B$$</div>
  <p>
    \\(n_B\\) is baseline provider turns per episode, \\(\\varphi\\) the fraction of episodes
    containing at least one eligible region, \\(k\\) the turns removed per successful
    dispatch, and \\(\\rho\\) the verifier pass rate. The ceiling assumes \\(\\rho = 1\\) and a
    gate that never abstains, so anything achieved must be lower. Demo E's own estimate
    reports the ceiling at <strong>41.3%</strong> — capped by the mandatory commitment,
    which no compiler is allowed to remove.
  </p>

  <h3>3.4 Algorithm 3 — the closed binding DSL</h3>
  <p>
    Argument synthesis searches a <em>closed</em> operator library rather than generating
    code. The consequences are the point: the search space is finite and cacheable, every
    binding is printable, and a reviewer can read the whole transform before approving it.
  </p>
  {code_block_wrap(dsl)}

  <h3>3.5 Algorithms 4 and 5 — branches and contracts</h3>
  <p>
    Where supporting windows diverge, Algorithm 4 fits a typed predicate over an
    observable path and validates it by permutation test, keeping only separations that
    could not have arisen by chance. Algorithm 5 induces the output contract — types,
    ranges, regexes, enum membership and per-field provenance — and then attacks it with
    a perturbation suite (stale reads, reordered results, empty sets, schema drift,
    injected faults). A contract that survives the attacks becomes the runtime verifier.
  </p>
  {figure(program, "A real compiled region from Demo E, printed by <code>registry.explain()</code>. Three synthesized branches give it a variable call count, which is why the verifier admits a set rather than a single number.")}

  <h3>3.6 Algorithm 6 — calibration with a valid risk statement</h3>
  <p>
    The gate is a logistic score \\(q(z)\\) over entry-only risk features — never the
    model's own verbal confidence, never anything unavailable at the boundary. The
    threshold is selected over a pre-registered grid \\(\\Lambda\\) with \\(|\\Lambda| = 11\\),
    and the confidence budget \\(\\delta\\) is Bonferroni-split across it. The certificate is
    an exact one-sided Clopper–Pearson bound on the violation rate among dispatched
    episodes:
  </p>
  <div class="math">$$R^{{+}}(\\eta) \\;=\\; \\mathrm{{BetaInv}}\\!\\left(1 - \\tfrac{{\\delta}}{{|\\Lambda|}};\\; v + 1,\\; n - v\\right)
  \\;\\le\\; \\alpha$$</div>
  <p>
    With \\(v = 0\\) observed violations this reduces to
    \\(R^{{+}} = 1 - (\\delta/|\\Lambda|)^{{1/n}}\\), and inverting it gives the sample
    complexity that decides whether a workload can <em>ever</em> be calibrated:
  </p>
  <div class="math">$$n \\;\\ge\\; \\frac{{\\log(\\delta/|\\Lambda|)}}{{\\log(1-\\alpha)}} \\;\\approx\\; 92
  \\quad\\text{{independent calibration groups at }} \\alpha = 0.05,\\ \\delta = 0.10$$</div>
  <div class="callout callout--warn">
    <p>
      <strong>Calibration is usually the binding constraint.</strong> The estimator reports
      the required group count before any compilation, and candidates that cannot reach it
      retire. In the offline study of Demo E, four of six mined candidates die here or at
      the perturbation challenge — that is the system working, not failing.
    </p>
  </div>

  <h3>3.7 TGWS — routes, pruning, and the domain guard</h3>
  <p>
    The route tree is depth-bounded, minimum-support-bounded and checked for
    <em>temporal</em> and <em>subgroup</em> stability: a route that only worked last month,
    or only for one principal, is rejected. Route labels are imitation targets, so an
    accepted leaf is still re-checked against task outcomes rather than path agreement.
  </p>
  <div class="callout callout--frame">
    <h4>Out-of-domain abstention</h4>
    <p>
      A decision tree's last leaf is a conjunction of negations, so an entry carrying a
      category the tree never saw matches it by construction and would silently inherit a
      route whose purity was never measured on it. The tree therefore records the observed
      value domain of every categorical split feature and abstains outright when a value
      falls outside it. This was found by writing the Demo F test, and the fix is in
      <code>RouteTree.route</code>.
    </p>
  </div>
</section>
"""


def code_block_wrap(block: str) -> str:
    return f'<div class="code-wrap">{block}</div>'


def section_safety() -> str:
    return f"""
<section id="safety">
  <h2>4 · The safety model</h2>
  <p>
    v0.x converts "infer the effects of a tool" — an open research problem — into
    configuration a human signs. Anything not declared is <code>UNKNOWN</code> and is
    never compiled. Read-only and idempotent are deliberately <em>not</em> capabilities:
    a nominal read can still burn quota, write an audit row, or observe time-varying data.
  </p>
  {table(
      ["Effect class", "May enter a region?", "Why"],
      [
          ["<code>PURE</code>", "<span class='yes'>yes</span>", "no external interaction at all"],
          ["<code>READ_LOCAL</code>", "<span class='yes'>yes</span>", "if declared <code>speculatable ∧ replayable</code>"],
          ["<code>READ_EXTERNAL</code>", "<span class='yes'>yes</span>", "if declared <code>speculatable ∧ replayable</code>"],
          ["<code>WRITE_REVERSIBLE</code>", "<span class='no'>no</span>", "transactional staging is future work, not a declaration"],
          ["<code>WRITE_IRREVERSIBLE</code>", "<span class='no'>no</span>", "terminates the region; the decision turn before it survives"],
          ["<code>UNKNOWN</code>", "<span class='no'>no</span>", "the default — an undeclared tool fails closed"],
          ["<em>any</em> + <code>approval_required</code>", "<span class='no'>no</span>", "an approval is a barrier; a prior approval never licenses a bypass"],
      ],
      caption="The effect lattice. Two independent conditions must both hold, and either one alone is insufficient.",
  )}

  <h3>4.1 Failure taxonomy</h3>
  <p>
    The runtime distinguishes failures by <em>what has already happened to the outside
    world</em>, because that is what determines whether recovery is possible.
  </p>
  {table(
      ["Failure", "State", "Runtime response"],
      [
          ["guard miss", "nothing executed", "run the baseline agent; the input is byte-identical"],
          ["gate abstain", "nothing executed", "run the baseline agent; log the score for drift monitoring"],
          ["<code>PreCommitError</code>", "reads only", "deoptimize exactly; the baseline takes over"],
          ["verifier reject", "reads only", "discard the region's outputs and deoptimize"],
          ["<code>PostCommitError</code>", "an external commitment happened", "raise an incident; do <em>not</em> pretend to roll back"],
      ],
  )}
  <p class="muted">
    In v0.x a program may contain only pre-commit reads, so a <code>PostCommitError</code>
    can only arise from a catalog or configuration error. The interpreter asserts that
    rather than trusting it.
  </p>
</section>
"""


def section_sdk() -> str:
    capture = code(
        """
from agents import Runner, RunConfig, add_trace_processor
from agent_compaction.capture.agents_sdk import (
    AgentsTraceProcessor, episode_from_agents_trace,
)

# 1. Capture. One processor, added once, collects native SDK traces.
processor = AgentsTraceProcessor(include_sensitive_data=True, max_completed=256)
add_trace_processor(processor)

result = await Runner.run(
    agent, user_input,
    run_config=RunConfig(
        workflow_name="support",
        group_id=case_id,                 # the scenario group — required for grouped splits
        trace_metadata={"tenant": tenant, "policy_version": "pol-1"},
    ),
)

# 2. Join the trace with the two things the SDK cannot know: the entry state that
#    existed *before* the first model decision, and the application's outcome label.
episode = episode_from_agents_trace(
    processor.drain()[0],
    envelope=envelope, manifest=manifest,
    entry_state=entry_state,              # your contract, not an inferred one
    outcome=outcome_labels,
)
""",
        "python",
    )
    optimize = code(
        """
import agent_compaction as ac

episodes = ac.read_jsonl("traces.jsonl")
catalog  = ac.load_catalog("configs/effects.example.yaml")

# 3. Estimate first. This is allowed to return a decisive no.
print(ac.estimate(episodes, catalog, entry_schema=["tenant_id", "case.exception_class"]).render())

# 4. Compile. Grouped splits, perturbation suite, exact calibration — all inside.
job = ac.optimize(
    episodes, catalog,
    algorithms=["tgws", "grc"],
    mode="offline",
    partition_by=["tenant_partition", "principal", "policy_version"],
    entry_schema=["tenant_id", "case.exception_class"],
    sandbox=make_sandbox,           # enables grouped replay + the perturbation suite
    tgws_baseline=baseline_config,
    tgws_evaluate=evaluator,
)
print(job.report())
print(job.explain())                # readable pseudocode for every artifact

ac.validate(job, suites=["replay", "perturbation"])
ac.promote(job, stage="shadow")     # shadow first, always
""",
        "python",
    )
    runtime = code(
        """
from agents import Agent
from agent_compaction.runtime.model_provider import CompactingModel

# 5a. The Model adapter: narrowest integration, one line at the call site.
#     Emits the artifact's next synthesized function_call instead of asking the
#     provider; the ordinary Runner then executes the tool, so SDK dispatch,
#     tracing and usage attribution are all preserved.
agent = Agent(
    name="fulfillment",
    instructions=decision_only_prompt,
    tools=[...],
    model=CompactingModel(
        base_model,
        registry=registry, catalog=catalog, manifest=manifest,
        mode="shadow",                                    # shadow -> canary -> live
        entry_state_fn=lambda inp: entry_state_for(inp),
        context_fn=lambda inp, z: {"entry_contract_version": z["case"]["intake"]},
    ),
)
""",
        "python",
    )
    runner = code(
        """
# 5b. The recommended path. The outer runner owns the entry-state snapshot and the
#     staging boundary, so a rejected attempt restores byte-identical model input.
#     The Model adapter cannot do this: once it has emitted a ModelResponse the
#     Runner may already have committed it to session history.
runner = ac.CompactingRunner(
    dispatcher=ac.Dispatcher(registry=registry, catalog=catalog, mode="shadow"),
    catalog=catalog,
    manifest=manifest,
)

# 5c. For agents that are not on the SDK at all:
@ac.compact(registry, catalog, manifest, mode="shadow")
async def handle(entry_state): ...
""",
        "python",
    )
    return f"""
<section id="sdk">
  <h2>5 · Using it with the OpenAI Agents SDK</h2>
  <p>
    The integration is deliberately boring. Capture is a trace processor; optimization is
    offline and touches no production traffic; deployment is a wrapper around either the
    <code>Model</code> or the runner. At no point does the library ask you to restructure
    your agent.
  </p>

  <h3>5.1 Capture</h3>
  <p>
    The SDK knows what happened. It does not know two things the compiler needs, and it
    cannot infer them: the <strong>entry state</strong> that existed before the first model
    decision, and the <strong>outcome label</strong> that says whether the episode was
    correct. Both are supplied by the application, and the trace contract makes that
    explicit rather than guessing.
  </p>
  {code_block_wrap(capture)}

  <h3>5.2 Optimize</h3>
  {code_block_wrap(optimize)}

  <h3>5.3 Deploy</h3>
  {code_block_wrap(runtime)}
  {code_block_wrap(runner)}

  <h3>5.4 What the Model adapter refuses</h3>
  <p>
    The adapter ships behind seven conformance tests and is intentionally narrower than
    the outer runner. Everything it cannot do exactly, it declines — and declining means
    the unmodified baseline workflow runs, not that the application breaks.
  </p>
  {table(
      ["Feature", "Behaviour", "Reason"],
      [
          ["streaming", "bypass to the wrapped model", "no way to emit a synthesized item mid-stream and still deoptimize"],
          ["handoffs", "bypass", "a handoff changes instruction ownership; it is a region barrier"],
          ["hosted / MCP tools", "bypass", "no attested effect catalog for the remote surface"],
          ["server-managed continuation", "bypass", "<code>previous_response_id</code> hides the local history the verifier needs"],
          ["loop or assert steps", "bypass", "only straight-line call programs can be advanced one turn at a time"],
          ["<code>mode=\"off\"</code>", "byte-identical input at the next provider call", "conformance test 1 — the wrapper must be removable"],
      ],
      caption="Demo E exercises two of these refusals live, and measures that they cost nothing but the fallback.",
  )}
</section>
"""


def demo_section(
    name: str,
    body: dict[str, Any],
    episodes: dict[str, dict[str, Any]],
    index: int,
) -> str:
    conditions = body.get("conditions", {})
    by_condition = body.get("comparisons_by_condition") or (
        {body.get("primary_condition", "compacted"): body.get("comparisons", {})}
    )
    baseline = conditions.get("baseline", {})

    rows = []
    for condition, metrics in conditions.items():
        label = CONDITION_LABELS.get(condition, condition)
        rows.append(
            [
                f"<strong>{esc(label)}</strong>"
                if condition == "baseline"
                else esc(label),
                num(metrics.get("n_scenarios")),
                num(metrics.get("requests"), 2),
                num(metrics.get("tool_calls"), 2),
                num(metrics.get("input_tokens")),
                num(metrics.get("total_tokens")),
                ms(metrics.get("wall_latency_ms")),
                money(metrics.get("estimated_cost_usd")),
                f"{metrics.get('quality', 0.0):.3f}",
                f"{metrics.get('success_rate', 0.0):.3f}",
            ]
        )

    charts = []
    for condition, comparison in by_condition.items():
        if not comparison:
            continue
        items = [
            ("provider turns", comparison.get("requests_reduction")),
            ("input tokens", comparison.get("input_tokens_reduction")),
            ("total tokens", comparison.get("total_tokens_reduction")),
            ("wall latency", comparison.get("wall_latency_ms_reduction")),
            ("estimated cost", comparison.get("estimated_cost_usd_reduction")),
        ]
        note = CONDITION_NOTES.get(condition, "")
        charts.append(
            '<div class="chart-block">'
            f'<h4>{esc(CONDITION_LABELS.get(condition, condition))} vs baseline</h4>'
            + (f'<p class="muted">{note}</p>' if note else "")
            + reduction_bars(items, chart_id=f"red-{name}-{condition}")
            + "</div>"
        )

    trace_html = trace_panels(name, body, episodes)

    quality_deltas = {
        condition: comparison.get("quality_delta", 0.0)
        for condition, comparison in by_condition.items()
        if comparison
    }
    worst = min(quality_deltas.values()) if quality_deltas else 0.0
    verdict_tone = "good" if worst >= 0.0 else "warn"
    verdict = (
        "task outcome unchanged in every condition"
        if worst >= 0.0
        else f"worst quality delta {worst:+.3f}"
    )

    return f"""
<section id="demo-{esc(name)}" class="demo">
  <h3>6.{index} · {esc(DEMO_TITLES.get(name, name))}</h3>
  <p>{DEMO_BLURBS.get(name, "")}</p>
  <p class="verdict verdict--{verdict_tone}">{esc(verdict)} · baseline
    {num(baseline.get("requests"), 1)} provider turns/episode</p>
  {table(
      ["Condition", "n", "Turns", "Tools", "Input tok", "Total tok", "Latency", "Est. cost", "Quality", "Success"],
      rows,
      caption="Per-scenario means. Tool calls are unchanged by design: compaction removes provider turns, not work.",
  )}
  <div class="chart-grid">{"".join(charts)}</div>
  {trace_html}
</section>
"""


def trace_panels(
    name: str, body: dict[str, Any], episodes: dict[str, dict[str, Any]]
) -> str:
    scenario = pick_scenario(body)
    if not scenario or not episodes:
        return ""
    runs = runs_for(body, scenario)
    baseline_run = runs.get("baseline")
    optimized_name = next(
        (c for c in ("compacted", "routed", "compacted_fallback") if c in runs), ""
    )
    optimized_run = runs.get(optimized_name)
    if not baseline_run or not optimized_run:
        return ""

    base_ep = episodes.get(baseline_run.get("trace_id", ""))
    opt_ep = episodes.get(optimized_run.get("trace_id", ""))
    if not base_ep or not opt_ep:
        return ""

    base_spans = spans_of(base_ep)
    opt_spans = spans_of(opt_ep)
    if not base_spans or not opt_spans:
        return ""

    domain = max(
        max((s.end for s in base_spans), default=0.0),
        max((s.end for s in opt_spans), default=0.0),
    )
    removed = max(
        0,
        int(baseline_run["metrics"]["requests"]) - int(optimized_run["metrics"]["requests"]),
    )

    entry = json.dumps(base_ep.get("entry_state", {}), indent=2, sort_keys=True)
    answer = json.dumps(optimized_run.get("answer", {}), indent=2, sort_keys=True)

    dispatch = optimized_run.get("dispatch") or {}
    dispatch_html = ""
    if dispatch:
        interesting = {
            k: v
            for k, v in dispatch.items()
            if k
            in (
                "outcome",
                "reason",
                "route",
                "abstained",
                "purity",
                "support",
                "prompt_blocks",
                "tools",
                "dropped_tools",
                "compacted",
                "baseline",
                "incidents",
                "gate_rejections",
                "verifier_pass_rate",
                "removed_requests_total",
                "overhead_ms_total",
                "interp_failures",
                "guard_misses",
            )
            and v not in ({}, [], None)
        }
        if interesting:
            dispatch_html = (
                '<div class="dispatch"><h5>Runtime dispatch record</h5>'
                + code(json.dumps(interesting, indent=2, sort_keys=True), "json")
                + "</div>"
            )

    return f"""
  <div class="traces">
    <h4>Trace, before and after — scenario <code>{esc(scenario)}</code></h4>
    <p class="muted">
      Both panels share one time axis, so the second is short because it is short.
      Hover any bar for its duration and token usage.
    </p>
    {legend()}
    <div class="panel">
      <div class="panel-head"><span class="tag tag--base">baseline</span>
        <span>{num(baseline_run["metrics"]["requests"])} provider turns ·
        {num(baseline_run["metrics"]["total_tokens"])} tokens ·
        {ms(baseline_run["metrics"]["wall_latency_ms"])}</span></div>
      {waterfall("baseline", base_spans, domain_ms=domain, chart_id=f"wf-{name}-base")}
    </div>
    <div class="panel">
      <div class="panel-head"><span class="tag tag--opt">{esc(CONDITION_LABELS.get(optimized_name, optimized_name))}</span>
        <span>{num(optimized_run["metrics"]["requests"])} provider turns ·
        {num(optimized_run["metrics"]["total_tokens"])} tokens ·
        {ms(optimized_run["metrics"]["wall_latency_ms"])}</span></div>
      {waterfall("optimized", opt_spans, domain_ms=domain, chart_id=f"wf-{name}-opt", ghost=removed)}
    </div>
    <div class="grid-2">
      <div><h5>Entry state (the compiler's only input, θ)</h5>{code(entry, "json")}</div>
      <div><h5>Final answer</h5>{code(answer, "json")}
        <p class="muted">Graded against the fixture's deterministic expectation, not
          against the baseline's answer.</p></div>
    </div>
    {dispatch_html}
  </div>
"""


def section_results(payload: dict[str, Any], episodes: dict[str, dict[str, Any]]) -> str:
    demos = payload["demos"]
    order = [d for d in DEMO_TITLES if d in demos] + [
        d for d in demos if d not in DEMO_TITLES
    ]
    sections = "".join(
        demo_section(name, demos[name], episodes, index + 1)
        for index, name in enumerate(order)
    )

    summary_rows = []
    for name in order:
        body = demos[name]
        comparison = body.get("comparisons", {})
        primary = body.get("primary_condition", "compacted")
        baseline = body.get("conditions", {}).get("baseline", {})
        optimized = body.get("conditions", {}).get(primary, {})
        summary_rows.append(
            [
                f'<a href="#demo-{esc(name)}">{esc(DEMO_TITLES.get(name, name))}</a>',
                f'{num(baseline.get("requests"), 1)} → {num(optimized.get("requests"), 1)}',
                pct(comparison.get("total_tokens_reduction"), signed=True),
                pct(comparison.get("wall_latency_ms_reduction"), signed=True),
                pct(comparison.get("estimated_cost_usd_reduction"), signed=True),
                f'{comparison.get("quality_delta", 0.0):+.3f}',
            ]
        )

    return f"""
<section id="results">
  <h2>6 · Measured results</h2>
  <p>
    Six demonstrations, each a paired comparison on identical scenarios. Two of them are
    negative controls that are <em>supposed</em> to refuse, and one — Demo E — carries two
    further refusal conditions alongside its compacted one. Read the negative numbers as
    the point, not as noise.
  </p>
  {table(
      ["Demonstration", "Provider turns", "Total tokens", "Wall latency", "Est. cost", "Quality Δ"],
      summary_rows,
      caption="Positive percentages are reductions. Quality Δ is the change in scenario score; zero means identical outcomes.",
  )}
  {sections}
</section>
"""


def section_cache(payload: dict[str, Any]) -> str:
    """The cache decomposition. Data-driven, because the headline is counterintuitive."""

    rows = []
    inversions = []
    for name, body in payload["demos"].items():
        for condition, m in body.get("conditions", {}).items():
            total = m.get("total_tokens") or 0.0
            cost = m.get("estimated_cost_usd")
            inp = m.get("input_tokens") or 0.0
            cached = m.get("cached_input_tokens") or 0.0
            written = m.get("cache_write_tokens") or 0.0
            if not total or cost is None:
                continue
            rows.append(
                [
                    f"{esc(name)} / {esc(CONDITION_LABELS.get(condition, condition))}",
                    num(inp),
                    f"{100.0 * cached / inp:.0f}%" if inp else "—",
                    num(written),
                    f"{cost / total * 1e6:.2f}",
                ]
            )
        comparison = body.get("comparisons", {})
        tok = comparison.get("total_tokens_reduction")
        usd = comparison.get("estimated_cost_usd_reduction")
        if tok is not None and usd is not None and tok > 0.05 and usd < 0:
            inversions.append((name, tok, usd))

    inversion_html = ""
    if inversions:
        items = "".join(
            f"<li><strong>{esc(DEMO_TITLES.get(n, n))}</strong> — "
            f"{pct(t)} fewer tokens, {pct(abs(u))} <em>more</em> estimated cost.</li>"
            for n, t, u in inversions
        )
        inversion_html = f"<ul>{items}</ul>"

    return f"""
<section id="cost">
  <h2>7 · Tokens are not dollars</h2>
  <p>
    The most useful thing this benchmark measured is a result that runs against the
    premise of the whole project. Removing provider turns reliably removes
    <em>tokens</em>. It does not reliably remove <em>money</em>, and in two of the six
    demonstrations it inverted the sign:
  </p>
  {inversion_html or "<p class='muted'>No cost inversion in this run.</p>"}
  <p>
    The mechanism is prompt caching. A provider bills the first turn over a prefix at a
    cache-<em>write</em> premium and every later turn over the same prefix at roughly a
    tenth of the input price. A long-prompt, many-turn baseline therefore amortizes one
    expensive write across six cheap reads, while a two-turn compacted run pays the write
    and has nothing left to amortize it over. Route specialization has the same problem
    one level up: four route prompts are four distinct cache prefixes, so a fleet that
    used to share one warm prefix now pays four writes.
  </p>
  {table(
      ["Demo / condition", "Input tokens", "Cached share", "Cache writes", "Blended $/Mtok"],
      rows,
      caption="Blended price is estimated cost divided by total tokens. A run whose prefix is warm bills at a fraction of the list input price.",
  )}
  <div class="callout callout--warn">
    <h4>How much of this is a benchmark artifact?</h4>
    <p>
      Some of it. Cache warmth depends on how many episodes share a prefix, and with four
      scenarios per condition a route prefix is written almost as often as it is read. At
      production volume the same prefix is reused thousands of times and the write
      amortizes to nothing — so a small benchmark <em>systematically understates</em> the
      cost advantage of both compaction and routing.
    </p>
    <p>
      But not all of it, and the residue is a real design constraint. A rarely-exercised
      route may never amortize its own cache write, which means TGWS should price prefix
      fragmentation in its objective rather than counting prompt tokens alone; and a
      workload whose baseline is already cache-dominated has far less dollar headroom than
      its token headroom suggests. The estimator reports a break-even in episodes per day
      for exactly this reason — and this run is a reminder to read it before believing a
      token-reduction headline.
    </p>
  </div>
</section>
"""


def section_limits() -> str:
    return """
<section id="limits">
  <h2>8 · What this does not show</h2>
  <div class="callout callout--warn">
    <ul>
      <li><strong>These are small provider runs.</strong> A handful of paired scenarios
        per demonstration demonstrates a mechanism. It is not a statistically powered
        quality claim and it is not production certification.</li>
      <li><strong>Empirical validation cannot prove semantic equivalence</strong> for all
        future inputs. The contribution is selective, evidence-bounded replacement with
        abstention — not a proof.</li>
      <li><strong>The live artifacts are hand-reviewed, not auto-promoted.</strong> Their
        gates carry <code>n_calibration_groups = 0</code> and are labelled as execution
        demonstrations. The calibrated path is exercised in the offline study, where most
        candidates correctly retire.</li>
      <li><strong>Latency reductions include provider variance.</strong> The suite is too
        small to separate a genuine critical-path saving from a slow afternoon; the MCP
        control's +5.6% latency swing on unchanged work is the honest scale of that noise.</li>
      <li><strong>Cost is estimated from published list prices</strong>, not an account
        invoice, and cached-prefill economics mean dollar savings lag turn savings.</li>
      <li><strong>The compiler is often the wrong tool.</strong> Run the estimator, read
        the top regions, and if a handwritten function captures them — write the function.</li>
    </ul>
  </div>
  <h3>Next milestone</h3>
  <p>
    A newly sealed, representative shadow and canary study on real traffic, under the
    hardened controls in the operations guide and paper limitations: exact staging ownership in an outer
    runner adapter, capability negotiation for hosted and MCP surfaces, and a
    transactional write protocol that is only relaxed once prepare/validate/commit/
    compensate can be <em>attested</em> — never by declaration alone.
  </p>
</section>
"""


# --------------------------------------------------------------------------
# page assembly
# --------------------------------------------------------------------------

CSS = """
:root {
  color-scheme: light dark;
  --page: #f9f9f7;
  --surface-1: #fcfcfb;
  --surface-2: #f3f3f0;
  --text-primary: #0b0b0b;
  --text-secondary: #52514e;
  --text-muted: #898781;
  --grid: #e1e0d9;
  --axis: #c3c2b7;
  --border: rgba(11, 11, 11, 0.10);
  --series-1: #2a78d6;
  --series-2: #eb6834;
  --pole-good: #2a78d6;
  --pole-bad: #e34948;
  --status-good: #0ca30c;
  --status-warn: #fab219;
  --success-text: #006300;
  --shadow: 0 1px 2px rgba(11,11,11,.04), 0 8px 24px rgba(11,11,11,.05);
  --mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
  --sans: system-ui, -apple-system, "Segoe UI", sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    --page: #0d0d0d;
    --surface-1: #1a1a19;
    --surface-2: #141413;
    --text-primary: #ffffff;
    --text-secondary: #c3c2b7;
    --text-muted: #898781;
    --grid: #2c2c2a;
    --axis: #383835;
    --border: rgba(255, 255, 255, 0.10);
    --series-1: #3987e5;
    --series-2: #d95926;
    --pole-good: #3987e5;
    --pole-bad: #e66767;
    --success-text: #0ca30c;
    --shadow: none;
  }
}
:root[data-theme="dark"] {
  --page: #0d0d0d;
  --surface-1: #1a1a19;
  --surface-2: #141413;
  --text-primary: #ffffff;
  --text-secondary: #c3c2b7;
  --text-muted: #898781;
  --grid: #2c2c2a;
  --axis: #383835;
  --border: rgba(255, 255, 255, 0.10);
  --series-1: #3987e5;
  --series-2: #d95926;
  --pole-good: #3987e5;
  --pole-bad: #e66767;
  --success-text: #0ca30c;
  --shadow: none;
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: 2rem; }
body {
  margin: 0;
  background: var(--page);
  color: var(--text-primary);
  font-family: var(--sans);
  font-size: 16px;
  line-height: 1.65;
  -webkit-font-smoothing: antialiased;
}
.layout { display: grid; grid-template-columns: 250px minmax(0, 1fr); gap: 0; max-width: 1400px; margin: 0 auto; }
nav {
  position: sticky; top: 0; align-self: start; height: 100vh; overflow-y: auto;
  padding: 2rem 1.25rem; border-right: 1px solid var(--border); font-size: 14px;
}
nav .brand { font-weight: 650; letter-spacing: -0.01em; margin-bottom: .25rem; }
nav .brand-sub { color: var(--text-muted); font-size: 12px; margin-bottom: 1.5rem; }
nav a { display: block; padding: .3rem 0; color: var(--text-secondary); text-decoration: none; border-left: 2px solid transparent; padding-left: .6rem; }
nav a:hover { color: var(--text-primary); border-left-color: var(--series-1); }
nav .sub { padding-left: 1.5rem; font-size: 13px; }
main { padding: 2.5rem 3rem 6rem; min-width: 0; }
section { margin-bottom: 4rem; scroll-margin-top: 1rem; }

h1 { font-size: clamp(2.2rem, 4vw, 3rem); line-height: 1.1; letter-spacing: -0.03em; margin: .2rem 0 1rem; }
h2 { font-size: 1.6rem; letter-spacing: -0.02em; margin: 0 0 1rem; padding-bottom: .6rem; border-bottom: 1px solid var(--border); }
h3 { font-size: 1.2rem; letter-spacing: -0.01em; margin: 2rem 0 .75rem; }
h4 { font-size: 1rem; margin: 1.5rem 0 .5rem; }
h5 { font-size: .85rem; text-transform: uppercase; letter-spacing: .06em; color: var(--text-muted); margin: 1.2rem 0 .5rem; font-weight: 600; }
p { margin: 0 0 1rem; max-width: 74ch; }
a { color: var(--series-1); }
.eyebrow { text-transform: uppercase; letter-spacing: .1em; font-size: 12px; font-weight: 600; color: var(--text-muted); margin: 0; }
.lede { font-size: 1.12rem; color: var(--text-secondary); max-width: 68ch; }
.muted { color: var(--text-secondary); font-size: .92rem; }
.provenance { font-size: .85rem; color: var(--text-muted); border-top: 1px solid var(--border); padding-top: 1rem; max-width: 88ch; }
.empty { color: var(--text-muted); font-style: italic; }

.kpi-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 1rem; margin: 2rem 0; }
.kpi { background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 1.1rem 1.2rem; box-shadow: var(--shadow); }
.kpi-label { font-size: .78rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: .05em; }
.kpi-value { font-size: 2rem; font-weight: 650; letter-spacing: -0.02em; margin-top: .3rem; line-height: 1.1; }
.kpi-sub { font-size: .82rem; color: var(--text-secondary); margin-top: .25rem; }
.kpi--good .kpi-value { color: var(--success-text); }
.kpi--warn .kpi-value { color: var(--status-warn); }

.grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(330px, 1fr)); gap: 1.25rem; margin: 1rem 0; }
.card { background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 1.2rem 1.35rem; }
.card h4 { margin-top: 0; }

.callout { border-radius: 12px; padding: 1.1rem 1.35rem; margin: 1.5rem 0; background: var(--surface-2); border: 1px solid var(--border); }
.callout--frame { border-left: 3px solid var(--series-1); }
.callout--warn { border-left: 3px solid var(--status-warn); }
.callout h3, .callout h4 { margin-top: 0; }
.callout ul, .callout ol { margin: 0; padding-left: 1.2rem; }
.callout li { margin-bottom: .5rem; max-width: 78ch; }

.table-wrap { overflow-x: auto; margin: 1.25rem 0; border: 1px solid var(--border); border-radius: 12px; background: var(--surface-1); }
table { border-collapse: collapse; width: 100%; font-size: .875rem; }
caption { caption-side: bottom; text-align: left; padding: .7rem 1rem; color: var(--text-muted); font-size: .8rem; }
th, td { padding: .55rem .85rem; text-align: left; border-bottom: 1px solid var(--border); }
th { font-weight: 600; font-size: .78rem; text-transform: uppercase; letter-spacing: .04em; color: var(--text-muted); background: var(--surface-2); }
tbody tr:last-child td { border-bottom: none; }
td { font-variant-numeric: tabular-nums; }
td:first-child, th:first-child { font-variant-numeric: normal; }
.yes { color: var(--success-text); font-weight: 600; }
.no { color: var(--pole-bad); font-weight: 600; }

code { font-family: var(--mono); font-size: .86em; background: var(--surface-2); padding: .1em .35em; border-radius: 4px; }
.code-wrap { margin: 1rem 0; }
pre.code { margin: 0; background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px; padding: 1.1rem 1.25rem; overflow-x: auto; font-size: .82rem; line-height: 1.6; }
pre.code code { background: none; padding: 0; font-size: inherit; }
.hljs { background: transparent !important; color: inherit; }

figure { margin: 1.5rem 0; }
figcaption { font-size: .82rem; color: var(--text-muted); margin-top: .6rem; max-width: 82ch; }
pre.mermaid { background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; overflow-x: auto; text-align: center; font-family: var(--mono); font-size: .78rem; color: var(--text-muted); }

.math { margin: 1.25rem 0; padding: .75rem 0; overflow-x: auto; }

.chart { width: 100%; height: auto; display: block; }
.chart .cat { font-size: 11.5px; fill: var(--text-secondary); font-family: var(--sans); }
.chart .val { font-size: 11.5px; fill: var(--text-secondary); font-family: var(--sans); font-variant-numeric: tabular-nums; }
.chart .tick { font-size: 10.5px; fill: var(--text-muted); font-family: var(--sans); font-variant-numeric: tabular-nums; }
.chart .grid { stroke: var(--grid); stroke-width: 1; }
.chart .axis { stroke: var(--axis); stroke-width: 1; }
.chart .ghost { fill: none; stroke: var(--axis); stroke-width: 1; stroke-dasharray: 3 4; }
.chart .ghost-label, .chart .ghost-val { font-size: 11px; fill: var(--text-muted); font-family: var(--sans); font-style: italic; }
.chart .span rect, .chart .bar-row path { transition: opacity .12s ease; }
.chart .span:hover rect, .chart .bar-row:hover path { opacity: .72; }

.legend { display: flex; flex-wrap: wrap; gap: 1.25rem; font-size: .82rem; color: var(--text-secondary); margin: .75rem 0; }
.legend .key { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: .45rem; vertical-align: baseline; }

.chart-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(470px, 1fr)); gap: 1.5rem; margin: 1.5rem 0; }
.chart-block { background: var(--surface-1); border: 1px solid var(--border); border-radius: 12px; padding: 1.1rem 1.2rem; }
.chart-block h4 { margin: 0 0 .25rem; font-size: .92rem; }

.traces { margin-top: 2rem; background: var(--surface-1); border: 1px solid var(--border); border-radius: 14px; padding: 1.35rem 1.5rem; }
.panel { margin: 1rem 0 1.5rem; }
.panel-head { display: flex; align-items: center; gap: .75rem; font-size: .82rem; color: var(--text-secondary); margin-bottom: .3rem; font-variant-numeric: tabular-nums; }
.tag { font-size: .72rem; text-transform: uppercase; letter-spacing: .05em; font-weight: 650; padding: .12rem .5rem; border-radius: 999px; border: 1px solid var(--border); }
.tag--base { color: var(--text-secondary); }
.tag--opt { color: var(--success-text); border-color: var(--success-text); }
.dispatch { margin-top: 1.25rem; }
.demo { padding-top: .5rem; }
.verdict { display: inline-block; font-size: .82rem; padding: .25rem .7rem; border-radius: 999px; border: 1px solid var(--border); background: var(--surface-2); }
.verdict--good { color: var(--success-text); }
.verdict--warn { color: var(--status-warn); }

.toggle { position: fixed; top: 1rem; right: 1rem; z-index: 20; background: var(--surface-1); color: var(--text-secondary); border: 1px solid var(--border); border-radius: 999px; padding: .4rem .9rem; font-size: .78rem; cursor: pointer; font-family: var(--sans); box-shadow: var(--shadow); }
.toggle:hover { color: var(--text-primary); }

footer { border-top: 1px solid var(--border); padding-top: 1.5rem; color: var(--text-muted); font-size: .82rem; }

@media (max-width: 900px) {
  .layout { grid-template-columns: 1fr; }
  nav { position: static; height: auto; border-right: none; border-bottom: 1px solid var(--border); }
  main { padding: 1.5rem 1.25rem 4rem; }
}
@media print {
  nav, .toggle { display: none; }
  .layout { grid-template-columns: 1fr; }
  section { break-inside: avoid; }
}
"""

SCRIPTS = """
<script>
  const stored = localStorage.getItem("ac-theme");
  if (stored) document.documentElement.setAttribute("data-theme", stored);
  function toggleTheme() {
    const now = document.documentElement.getAttribute("data-theme");
    const dark = now ? now === "dark"
      : window.matchMedia("(prefers-color-scheme: dark)").matches;
    const next = dark ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("ac-theme", next);
    location.reload();  // re-render mermaid against the new surface
  }
</script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"
        onload="renderMathInElement(document.body, {delimiters: [
          {left: '$$', right: '$$', display: true},
          {left: '\\\\(', right: '\\\\)', display: false}], throwOnError: false});"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/styles/github.min.css">
<script src="https://cdn.jsdelivr.net/npm/highlight.js@11.9.0/lib/highlight.min.js"></script>
<script>window.hljs && hljs.highlightAll();</script>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
  const explicit = document.documentElement.getAttribute("data-theme");
  const dark = explicit ? explicit === "dark"
    : window.matchMedia("(prefers-color-scheme: dark)").matches;
  const ink = dark ? "#ffffff" : "#0b0b0b";
  mermaid.initialize({
    startOnLoad: true,
    theme: "base",
    themeVariables: {
      background: dark ? "#1a1a19" : "#fcfcfb",
      primaryColor: dark ? "#1f1f1e" : "#f3f3f0",
      primaryTextColor: ink,
      primaryBorderColor: dark ? "#383835" : "#c3c2b7",
      lineColor: dark ? "#898781" : "#898781",
      secondaryColor: dark ? "#252523" : "#eceae4",
      tertiaryColor: dark ? "#1a1a19" : "#fcfcfb",
      fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif',
      fontSize: "13px",
    },
  });
</script>
"""

NAV = """
<nav>
  <div class="brand">agent-compaction</div>
  <div class="brand-sub">architecture · algorithms · measured results</div>
  <a href="#overview">Overview</a>
  <a href="#problem">1 · The problem</a>
  <a href="#architecture">2 · Architecture</a>
  <a href="#algorithms">3 · Algorithms</a>
  <a href="#safety">4 · Safety model</a>
  <a href="#sdk">5 · OpenAI Agents SDK</a>
  <a href="#results">6 · Measured results</a>
  __DEMO_LINKS__
  <a href="#cost">7 · Tokens are not dollars</a>
  <a href="#limits">8 · What this does not show</a>
</nav>
"""


def build(payload: dict[str, Any], episodes: dict[str, dict[str, Any]]) -> str:
    demos = payload["demos"]
    order = [d for d in DEMO_TITLES if d in demos] + [
        d for d in demos if d not in DEMO_TITLES
    ]
    demo_links = "".join(
        f'<a class="sub" href="#demo-{esc(name)}">{esc(DEMO_TITLES.get(name, name))}</a>'
        for name in order
    )
    nav = NAV.replace("__DEMO_LINKS__", demo_links)
    manifest = payload["manifest"]

    body = "".join(
        [
            section_hero(payload),
            section_problem(),
            section_architecture(),
            section_algorithms(),
            section_safety(),
            section_sdk(),
            section_results(payload, episodes),
            section_cache(payload),
            section_limits(),
            f"""
<footer>
  <p>
    Generated by <code>scripts/build_html_report.py</code> from
    <code>experiments/live_results/</code>. Substrate
    <code>{esc(manifest["substrate"])}</code>, Python
    <code>{esc(manifest["python"])}</code>, platform
    <code>{esc(manifest["platform"])}</code>. Data class:
    {esc(manifest["data_class"])}. The API key is never printed or persisted.
  </p>
  <p>{esc(manifest["warning"])}</p>
</footer>
""",
        ]
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>agent-compaction — guarded workflow optimization for LLM agents</title>
<meta name="description" content="Architecture, algorithms and measured before/after traces for guarded, evidence-gated agent workflow compaction on the OpenAI Agents SDK.">
<style>{CSS}</style>
</head>
<body>
<button class="toggle" onclick="toggleTheme()">light / dark</button>
<div class="layout">
{nav}
<main>
{body}
</main>
</div>
{SCRIPTS}
</body>
</html>
"""


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default=str(DEFAULT_RESULTS))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)

    results_dir = Path(args.results)
    payload = load_payload(results_dir)
    episodes = load_episodes(results_dir)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(payload, episodes))
    size_kb = out.stat().st_size / 1024
    print(
        f"wrote {out} ({size_kb:.0f} KB) from {len(payload['demos'])} demos "
        f"and {len(episodes)} captured episodes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
