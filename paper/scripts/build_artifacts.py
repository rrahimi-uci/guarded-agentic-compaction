#!/usr/bin/env python3
"""Build every quantitative figure, table, and checksum used by the paper.

The script is deliberately provider-free: it consumes the immutable JSON/CSV outputs
created by ``github_live_study.py`` and ``nestful_benchmark.py``.  Running it therefore
does not spend API credits or alter the sealed test observations.
"""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"
RESULTS = PAPER / "results"
FIGURES = PAPER / "generated_figures"
TABLES = PAPER / "tables"

LIVE_PATH = RESULTS / "github_live" / "results.json"
NATURAL_LIVE_PATH = RESULTS / "github_natural_live" / "results.json"
NATURAL_REPLICATION_PATH = RESULTS / "github_natural_replication" / "results.json"
PORTFOLIO_PATH = RESULTS / "portfolio_live" / "results.json"
GCS_LIVE_PATH = RESULTS / "gcs_live" / "results.json"
GCS_VALIDATION_PATH = RESULTS / "gcs_validation" / "provider_free.json"
PILOT_PATH = RESULTS / "github_live" / "pilot_2026-08-03" / "results.json"
NESTFUL_PATH = RESULTS / "nestful" / "results.json"
FAMILY_PATH = RESULTS / "nestful" / "family_results.csv"
#: Controlled demonstration suite. Live provider calls and the real SDK runtime against
#: deterministic local services holding fictional business records.
DEMOS_PATH = ROOT / "experiments" / "live_results" / "all_results.json"
#: Deterministic offline stress study. Simulated substrate (scripted policy standing in
#: for the model), which is why it cannot answer the live question -- but it is the only
#: place the hand-written-macro comparator is actually measured.
OFFLINE_DIR = ROOT / "experiments" / "results"

# Figure palette. Validated with the data-visualization palette checker on a white
# surface: chroma floor, CVD separation (worst adjacent protan dE 23.8), normal-vision
# floor (31.6) and 3:1 contrast all pass. The paper's heading blue (#2F6B8A) is
# deliberately NOT used as a fill: its chroma is 0.079, below the 0.1 floor, so it reads
# gray as a data mark. Ink colours and series colours do different jobs.
COLORS = {
    "series1": "#2a78d6",   # primary series / bars
    "series2": "#d03b3b",   # contrasting series; also the "requirement" threshold
    "track": "#E4E7EB",     # unfilled baseline track behind a normalized bar
    "ink": "#0b0b0b",        # primary text
    "ink2": "#52514e",       # secondary text
    "muted": "#898781",      # axis and tick labels
    "grid": "#E1E0D9",       # hairline gridlines
    "axis": "#C3C2B7",       # baselines and spines
}

#: Authored figure width in inches. The article measure is 146\,mm (5.75in), so a
#: figure drawn at this width is reproduced at ~1:1 and its 9pt labels stay 9pt.
FIG_W = 5.4

# Matplotlib otherwise inserts the wall-clock creation time into every PDF. That makes
# unchanged figures hash differently on every rebuild and defeats the checksum manifest.
# A fixed, truthful artifact-version timestamp keeps the PDF bytes reproducible.
PDF_METADATA = {
    "Creator": "agent-compaction paper/scripts/build_artifacts.py",
    "CreationDate": datetime(2026, 8, 4, tzinfo=timezone.utc),
    "ModDate": datetime(2026, 8, 4, tzinfo=timezone.utc),
}

def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def tex(value: object) -> str:
    """Escape ordinary table text without changing mathematical snippets."""
    text = str(value)
    for old, new in (
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("_", r"\_"),
        ("#", r"\#"),
    ):
        text = text.replace(old, new)
    return text


def savefig(name: str) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    plt.savefig(
        FIGURES / f"{name}.pdf",
        bbox_inches="tight",
        pad_inches=0.02,
        metadata=PDF_METADATA,
    )
    plt.savefig(FIGURES / f"{name}.png", dpi=220, bbox_inches="tight", pad_inches=0.02)
    plt.close()


def configure_plots() -> None:
    """One recessive house style: hairline solid gridlines, no top/right spines.

    Figure titles are deliberately absent everywhere. Each figure already has a LaTeX
    caption, and an in-axes title duplicating it wastes vertical space and competes with
    the caption for the reader's attention.
    """

    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans"],
            "font.size": 9,
            "axes.labelsize": 9,
            "axes.labelcolor": COLORS["ink2"],
            "axes.titlesize": 9,
            "axes.edgecolor": COLORS["axis"],
            "axes.linewidth": 0.6,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "xtick.color": COLORS["muted"],
            "ytick.color": COLORS["muted"],
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "xtick.major.size": 2.5,
            "ytick.major.size": 2.5,
            "legend.fontsize": 8,
            "grid.color": COLORS["grid"],
            "grid.linewidth": 0.6,
            "grid.linestyle": "-",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def _outside_legend(ax, handles=None, labels=None, ncol=2) -> None:
    """Place the key above the axes.

    Every overlap in the first version of these figures came from an in-axes legend:
    matplotlib's ``loc`` only avoids other *artists it knows about*, so a legend at
    ``upper center`` sat on top of bar value labels and a threshold line. Putting the key
    outside the data area makes collisions impossible by construction.
    """

    if handles is None:
        handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles,
        labels,
        frameon=False,
        ncol=ncol,
        loc="lower left",
        bbox_to_anchor=(0.0, 1.01),
        borderaxespad=0.0,
        handlelength=1.1,
        handletextpad=0.5,
        columnspacing=1.6,
        labelcolor=COLORS["ink2"],
    )


def live_efficiency_figure(live: dict[str, Any]) -> None:
    """Normalized resource use: one bar per metric against a baseline track."""

    metrics = live["paired_test"]["metrics"]
    order = ["requests", "total_tokens", "wall_latency_ms", "estimated_cost_usd", "tool_calls"]
    labels = ["Provider requests", "Total tokens", "Wall latency", "Estimated cost", "Tool calls"]
    compiled = [100 * (1 - metrics[key]["aggregate_reduction"]) for key in order]

    y = np.arange(len(order))
    fig, ax = plt.subplots(figsize=(FIG_W, 2.15))
    # Track first, bar on top: a meter reads as "how much of the baseline remains".
    ax.barh(y, [100] * len(y), 0.52, color=COLORS["track"], label="Baseline = 100%",
            zorder=1)
    ax.barh(y, compiled, 0.52, color=COLORS["series1"], label="Compiled", zorder=2)
    ax.set_yticks(y, labels)
    ax.set_ylim(len(order) - 0.5, -0.5)
    # Headroom to the right of 100 so the "unchanged" label never lands on the track.
    ax.set_xlim(0, 138)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Mean per episode, normalized to baseline (\u0025)")
    ax.xaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)
    ax.spines["left"].set_color(COLORS["axis"])

    for index, value in enumerate(compiled):
        reduction = 100 - value
        text = "unchanged" if abs(reduction) < 0.05 else f"\u2212{reduction:.1f}\u0025"
        ax.text(value + 3.0, index, text, va="center", ha="left", fontsize=8,
                color=COLORS["ink"] if abs(reduction) >= 0.05 else COLORS["ink2"])
    _outside_legend(ax)
    fig.tight_layout()
    savefig("live_efficiency")


def paired_figure(live: dict[str, Any]) -> None:
    """Per-issue paired scatter, one square panel per metric."""

    rows = [r for r in live["results"]
            if r["condition"] in {"baseline", "compiled"} and r["repeat"] == 0]
    by_key = {(r["issue_number"], r["condition"]): r for r in rows}
    issues = sorted({r["issue_number"] for r in rows})
    # The cost panel is pre-scaled to 10^-3 USD. Matplotlib's scientific-notation
    # offset text ("1e-3") is drawn outside the axes at the corner, where it collided
    # with both the panel title and the x-axis label; folding the exponent into the
    # title removes the artist entirely.
    specs = [
        ("total_tokens", "Total tokens", "linear", 1.0),
        ("wall_latency_ms", "Wall latency (ms)", "log", 1.0),
        ("estimated_cost_usd", "Cost (10$^{-3}$ USD)", "linear", 1000.0),
    ]
    # Taller than before: the previous 2.35in height left three panels barely 1in of
    # plotting area once equal aspect and tick labels were applied.
    fig, axes = plt.subplots(1, 3, figsize=(FIG_W, 2.35))
    for column, (ax, (metric, label, scale, mul)) in enumerate(zip(axes, specs, strict=True)):
        x = np.array([by_key[(i, "baseline")]["metrics"][metric] for i in issues]) * mul
        y = np.array([by_key[(i, "compiled")]["metrics"][metric] for i in issues]) * mul
        low = min(x.min(), y.min()) * 0.88
        high = max(x.max(), y.max()) * 1.12
        ax.plot([low, high], [low, high], color=COLORS["axis"], ls="--", lw=0.7, zorder=1)
        ax.scatter(x, y, s=18, color=COLORS["series1"], edgecolor="white", linewidth=0.5,
                   zorder=3, clip_on=False)
        ax.set_title(label, color=COLORS["ink"], pad=4)
        ax.set_xlabel("Baseline")
        if column == 0:
            ax.set_ylabel("Compiled")
        ax.set_xscale(scale)
        ax.set_yscale(scale)
        ax.set_xlim(low, high)
        ax.set_ylim(low, high)
        ax.set_aspect("equal", adjustable="box")
        ax.grid(True, zorder=0)
        ax.set_axisbelow(True)
        if scale == "linear":
            ax.ticklabel_format(axis="both", style="plain")
        ax.tick_params(labelsize=7)
        # One panel carries the reference-line label; repeating it in all three is noise.
        if column == 0:
            ax.annotate("no change", xy=(0.62, 0.68), xycoords="axes fraction",
                        fontsize=7, color=COLORS["muted"], rotation=45,
                        ha="center", va="center")
    fig.tight_layout(w_pad=1.6)
    savefig("paired_test")


def gate_support_figure(nestful: dict[str, Any]) -> None:
    """Family support against the exact-gate requirement, with direct annotations.

    No legend: the previous version put a two-entry key at ``upper right``, where its
    marker landed on top of the threshold-line label. Both facts are now annotated in
    the empty upper half of the plot, which is also where a reader looks for them.
    """

    with FAMILY_PATH.open(newline="", encoding="utf-8") as handle:
        families = list(csv.DictReader(handle))
    supports = sorted((int(row["support"]) for row in families), reverse=True)
    required = nestful["compiler"]["exact_gate"]["minimum_zero_violation_groups"]

    fig, ax = plt.subplots(figsize=(FIG_W, 2.2))
    ranks = np.arange(1, len(supports) + 1)
    ax.bar(ranks, supports, width=0.78, color=COLORS["series1"], zorder=3)
    ax.axhline(required, color=COLORS["series2"], lw=1.2, zorder=4)

    ax.set_xlim(0.2, len(supports) + 0.8)
    ax.set_ylim(0, 112)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_xlabel("NESTFUL recurring family, ranked by group-record support")
    ax.set_ylabel("Group records")
    ax.yaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)

    ax.annotate(
        f"Exact-gate minimum = {required} groups  \u2192  every family retires",
        xy=(0.6, required), xytext=(0.6, required + 6),
        fontsize=8, color=COLORS["series2"], va="bottom", ha="left",
    )
    ax.annotate(
        f"best family reaches only {supports[0]}",
        xy=(1.0, supports[0]), xytext=(4.2, supports[0] + 26),
        fontsize=8, color=COLORS["ink2"], va="bottom", ha="left",
        arrowprops=dict(arrowstyle="-", color=COLORS["muted"], lw=0.6,
                        shrinkA=0, shrinkB=2),
    )
    fig.tight_layout()
    savefig("gate_support")


def pilot_figure(live: dict[str, Any], pilot: dict[str, Any]) -> None:
    """Archived unsafe pilot against the corrected compiler."""

    labels = ["Task quality", "Tool-contract\nvalidity", "Provider-request\nreduction"]
    pilot_values = [
        pilot["paired_test"]["quality"]["overall"]["compiled_rate"],
        pilot["paired_test"]["quality"]["tool_contract"]["compiled_rate"],
        pilot["paired_test"]["metrics"]["requests"]["aggregate_reduction"],
    ]
    final_values = [
        live["paired_test"]["quality"]["overall"]["compiled_rate"],
        live["paired_test"]["quality"]["tool_contract"]["compiled_rate"],
        live["paired_test"]["metrics"]["requests"]["aggregate_reduction"],
    ]
    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(FIG_W, 2.25))
    width = 0.3
    # 2px-equivalent gap between the pair keeps them distinct without a stroke.
    b1 = ax.bar(x - width / 2 - 0.012, np.array(pilot_values) * 100, width,
                color=COLORS["series2"], label="Archived pilot (suffix dispatch)", zorder=3)
    b2 = ax.bar(x + width / 2 + 0.012, np.array(final_values) * 100, width,
                color=COLORS["series1"], label="Corrected compiler (prefix invariant)", zorder=3)
    ax.set_xticks(x, labels)
    ax.tick_params(axis="x", labelsize=8, colors=COLORS["ink2"])
    # Headroom for the value labels, which previously collided with the in-axes legend.
    ax.set_ylim(0, 118)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel("Rate or reduction (\u0025)")
    ax.yaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)
    for bars in (b1, b2):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2.5,
                    f"{bar.get_height():.1f}", ha="center", va="bottom", fontsize=8,
                    color=COLORS["ink"])
    _outside_legend(ax)
    fig.tight_layout()
    savefig("pilot_ablation")


def natural_comparison_figure(natural: dict[str, Any]) -> None:
    """Real-provider compiler and macro usage normalized to the unchanged agent."""

    compiled = natural["paired_test"]["metrics"]
    macro = natural["paired_macro_test"]["metrics"]
    keys = ["requests", "tool_calls", "total_tokens", "wall_latency_ms", "estimated_cost_usd"]
    labels = ["Provider requests", "Tool calls", "Total tokens", "Wall latency", "Estimated cost"]
    compiler_values = [100 * (1 - compiled[key]["aggregate_reduction"]) for key in keys]
    macro_values = [100 * (1 - macro[key]["aggregate_reduction"]) for key in keys]
    y = np.arange(len(keys))
    height = 0.34
    fig, ax = plt.subplots(figsize=(FIG_W, 2.35))
    ax.barh(y - height / 2 - 0.01, compiler_values, height, color=COLORS["series1"],
            label="Learned compiler", zorder=3)
    ax.barh(y + height / 2 + 0.01, macro_values, height, color=COLORS["series2"],
            label="Hand-written macro", zorder=3)
    ax.set_yticks(y, labels)
    ax.set_ylim(len(keys) - 0.5, -0.5)
    ax.set_xlim(0, 112)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Resource use normalized to unchanged agent (\u0025)")
    ax.xaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)
    _outside_legend(ax)
    fig.tight_layout()
    savefig("natural_live_comparison")


def portfolio_selection_figure(portfolio: dict[str, Any]) -> None:
    """Calibration utility and the action selected before the prospective cohort."""

    evidence = portfolio["decision"]["evidence"]
    labels = [item["action"].capitalize() for item in evidence]
    values = [100 * float(item["mean_utility"]) for item in evidence]
    colors = [
        COLORS["series2"] if item["action"] == portfolio["decision"]["selected_action"]
        else COLORS["series1"]
        for item in evidence
    ]
    fig, ax = plt.subplots(figsize=(FIG_W, 1.75))
    bars = ax.barh(np.arange(len(values)), values, color=colors, height=0.52, zorder=3)
    ax.set_yticks(np.arange(len(labels)), labels)
    ax.set_xlabel("Mean paired portfolio utility (percentage points)")
    ax.set_xlim(0, max(values) * 1.20)
    ax.xaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)
    for bar, item in zip(bars, evidence):
        suffix = "  selected; review" if item["action"] == portfolio["decision"]["selected_action"] else ""
        ax.text(
            bar.get_width() + 1.0,
            bar.get_y() + bar.get_height() / 2,
            f"{bar.get_width():.1f}{suffix}",
            va="center",
            fontsize=8,
            color=COLORS["ink"],
        )
    fig.tight_layout()
    savefig("portfolio_selection")


def write_portfolio_table(portfolio: dict[str, Any]) -> None:
    decision = portfolio["decision"]
    out = [
        r"\begin{tabularx}{\linewidth}{@{}>{\raggedright\arraybackslash}X r r r >{\raggedright\arraybackslash}X@{}}",
        r"\toprule",
        r"Calibration action & $n$ & $\bar U$ & $R_q^+/R_u^+$ & Decision \\",
        r"\midrule",
    ]
    for item in decision["evidence"]:
        verdict = (
            r"selected; human review"
            if item["action"] == decision["selected_action"]
            else ("admitted" if item["admitted"] else "retired")
        )
        out.append(
            f"{tex(item['action'].capitalize())} & {item['support_groups']} & "
            f"{item['mean_utility']:.3f} & {item['quality_risk_upper']:.3f}/"
            f"{item['regret_risk_upper']:.3f} & {verdict} \\\\"
        )
    paired = portfolio["paired_selected_vs_baseline"]
    metrics = paired["metrics"]
    quality = portfolio["quality"]
    aggregate = portfolio["aggregate"]
    baseline = aggregate["baseline"]
    selected = aggregate[decision["selected_action"]]
    by_condition = {
        condition: [
            row for row in portfolio["results"] if row["condition"] == condition
        ]
        for condition in ("baseline", decision["selected_action"])
    }
    mean_tools = {
        condition: sum(row["metrics"]["tool_calls"] for row in rows) / len(rows)
        for condition, rows in by_condition.items()
    }
    out += [
        r"\midrule",
        r"\multicolumn{5}{@{}l}{\emph{Fresh cohort: selected macro versus unchanged}} \\",
        r"\addlinespace[2pt]",
        r"Endpoint & $n$ & Base & Macro & Change \\",
        r"\addlinespace[2pt]",
        (
            f"Exact contracts & {quality['paired_groups']} & "
            f"{quality['baseline_exact']}/{quality['paired_groups']} & "
            f"{quality['selected_exact']}/{quality['paired_groups']} & preserved \\\\"
        ),
        (
            f"Provider requests & {paired['n_pairs']} & "
            f"{baseline['provider_requests'] / baseline['n']:.0f} & "
            f"{selected['provider_requests'] / selected['n']:.0f} & "
            f"$-{100 * metrics['requests']['aggregate_reduction']:.1f}\\%$ \\\\"
        ),
        (
            f"Tool calls & {paired['n_pairs']} & {mean_tools['baseline']:.0f} & "
            f"{mean_tools[decision['selected_action']]:.0f} & "
            f"$-{100 * metrics['tool_calls']['aggregate_reduction']:.1f}\\%$ \\\\"
        ),
        f"Total tokens & {paired['n_pairs']} & -- & -- & $-{100 * metrics['total_tokens']['aggregate_reduction']:.1f}\\%$ \\\\ ",
        f"Estimated cost & {paired['n_pairs']} & -- & -- & $-{100 * metrics['estimated_cost_usd']['aggregate_reduction']:.1f}\\%$ \\\\ ",
        f"Wall latency & {paired['n_pairs']} & -- & -- & $-{100 * metrics['wall_latency_ms']['aggregate_reduction']:.1f}\\%$ \\\\ ",
        r"\bottomrule",
        r"\end{tabularx}",
    ]
    (TABLES / "portfolio_results.tex").write_text("\n".join(out) + "\n", encoding="utf-8")


#: Demonstration suite, in presentation order. ``shape`` names the property that makes
#: each case non-trivial; ``primary`` is the condition compared against its baseline.
DEMO_SPECS = [
    ("support", "A", "Linear read prefix", "compacted"),
    ("permissioned_rag", "B", "ACL scope + index version as guard keys", "compacted"),
    ("incident_triage", "C", "Coordinator with a handoff barrier", "compacted"),
    ("fulfillment", "E", "3 synthesized branches, pagination, mandatory write", "compacted"),
    ("tgws_router", "F", "Route specialization (prompt + tool surface)", "routed"),
    ("mcp_ops", "D", "Undeclared MCP effects (negative control)", "compacted_fallback"),
    ("fulfillment", "E$'$", "Loop-bearing artifact refused (negative control)",
     "compacted_loop_refused"),
    ("fulfillment", "E$''$", "Entry-schema drift, guard miss (negative control)",
     "compacted_ood_fallback"),
]


def _demo_rows() -> list[dict[str, Any]]:
    payload = load_json(DEMOS_PATH)
    rows: list[dict[str, Any]] = []
    for key, tag, shape, condition in DEMO_SPECS:
        demo = payload["demos"].get(key)
        if demo is None or condition not in demo["conditions"]:
            continue
        base = demo["conditions"]["baseline"]
        cand = demo["conditions"][condition]
        comparisons = (demo.get("comparisons_by_condition") or {}).get(condition, {})
        rows.append(
            {
                "tag": tag,
                "shape": shape,
                "n": int(cand["n_scenarios"]),
                "turns_base": base["requests"],
                "turns_cand": cand["requests"],
                "tokens": comparisons.get("total_tokens_reduction"),
                "latency": comparisons.get("wall_latency_ms_reduction"),
                "cost": comparisons.get("estimated_cost_usd_reduction"),
                "quality_base": base["quality"],
                "quality_cand": cand["quality"],
                "cached_base": (base.get("cached_input_tokens") or 0.0) / max(1.0, base["input_tokens"]),
                "cached_cand": (cand.get("cached_input_tokens") or 0.0) / max(1.0, cand["input_tokens"]),
            }
        )
    return rows


def write_comparator_table() -> None:
    """The hand-written-composite-tool comparator, from the offline stress study.

    This answers the sharpest reviewer objection to the live study: without a strong
    engineering baseline, a request reduction does not show that trace compilation adds
    value over simply writing the function. The comparator exists and is unflattering, so
    it belongs in the paper.
    """

    rows = []
    for path in sorted(OFFLINE_DIR.glob("*.json")):
        if path.name in {"run_manifest.json", "all_results.json"}:
            continue
        data = load_json(path)
        comparisons = data.get("comparisons", {})
        macro = comparisons.get("simple", {}).get("request_ratio", {})
        compiler = comparisons.get("full", {}).get("request_ratio", {})
        if not macro or not compiler:
            continue
        title = str(data.get("title", path.stem))
        # Titles use a literal em dash, not three hyphens.
        head, _, tail = title.partition("\u2014")
        tag = head.replace("Demo ", "").strip()[:1] or path.stem[:1]
        m, c = float(macro["point"]), float(compiler["point"])
        rows.append((tag, title, m, c))
    rows.sort(key=lambda r: r[0])

    out = [
        r"\begin{tabularx}{\linewidth}{@{}c >{\raggedright\arraybackslash}X r r l@{}}",
        r"\toprule",
        r"Demo & Workload & Macro $R_{\mathrm{req}}$ & \method $R_{\mathrm{req}}$ & "
        r"Lower is better \\",
        r"\midrule",
    ]
    for tag, title, m, c in rows:
        workload = (title.partition("\u2014")[2] or title).strip()
        if abs(m - c) < 0.01:
            verdict = "comparable"
        elif m < c:
            verdict = r"\textbf{macro wins}"
        else:
            verdict = r"\method{} wins"
        out.append(
            f"{tag} & {tex(workload)} & {m:.3f} & {c:.3f} & {verdict} \\\\"
        )
    out += [r"\bottomrule", r"\end{tabularx}"]
    (TABLES / "comparator.tex").write_text("\n".join(out) + "\n", encoding="utf-8")


def write_demo_suite_table() -> None:
    """Per-demonstration outcome, including the three that must refuse."""

    rows = _demo_rows()
    out = [
        r"\begin{tabularx}{\linewidth}{@{}c >{\raggedright\arraybackslash}X c r r r r c@{}}",
        r"\toprule",
        r"& & & \multicolumn{2}{c}{Model calls} & \multicolumn{2}{c}{Change} & Quality \\",
        r"\cmidrule(lr){4-5}\cmidrule(lr){6-7}",
        r"Demo & Shape that makes it hard & $n$ & base & cand. & tokens & cost & "
        r"base\,/\,cand. \\",
        r"\midrule",
    ]
    for r in rows:
        def pct(value: object) -> str:
            if value is None:
                return "---"
            return f"${-100 * float(value):+.1f}\\%$"

        out.append(
            f"{r['tag']} & {tex(r['shape'])} & {r['n']} & "
            f"{r['turns_base']:.1f} & {r['turns_cand']:.1f} & "
            f"{pct(r['tokens'])} & {pct(r['cost'])} & "
            f"{r['quality_base']:.2f}\\,/\\,{r['quality_cand']:.2f} \\\\"
        )
    out += [r"\bottomrule", r"\end{tabularx}"]
    (TABLES / "demo_suite.tex").write_text("\n".join(out) + "\n", encoding="utf-8")


def demo_suite_figure() -> None:
    """Token saving against cost saving, per demonstration.

    The axis must span the full data range: an earlier version clipped at -20% and cut
    the -123% cost penalty off the canvas, which reversed the figure's message. Two of
    these bars point the other way, and that is the finding.
    """

    rows = [r for r in _demo_rows() if r["tokens"] is not None and r["cost"] is not None]
    labels = [r["tag"] for r in rows]
    tokens = [100 * r["tokens"] for r in rows]
    cost = [100 * r["cost"] for r in rows]

    y = np.arange(len(rows))
    height = 0.34
    fig, ax = plt.subplots(figsize=(FIG_W, 0.36 * len(rows) + 1.05))
    ax.barh(y - height / 2 - 0.012, tokens, height, color=COLORS["series1"],
            label="Tokens saved", zorder=3)
    ax.barh(y + height / 2 + 0.012, cost, height, color=COLORS["series2"],
            label="Cost saved", zorder=3)
    ax.axvline(0, color=COLORS["ink2"], lw=0.9, zorder=4)
    ax.set_yticks(y, labels)
    ax.set_ylim(len(rows) - 0.5, -0.5)

    floor = min(min(cost), min(tokens))
    ax.set_xlim(floor - 18, 108)
    ax.set_xticks([t for t in range(-125, 101, 25) if t >= floor - 18])
    ax.set_xlabel("Saving versus baseline (\u0025)")
    ax.xaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", labelsize=8.5, colors=COLORS["ink"])

    # Label only the penalties: they are the point, and labelling all sixteen bars
    # would be the "number on every mark" anti-pattern.
    for index, value in enumerate(cost):
        if value < -0.5:
            # One decimal, and the sign convention of the prose (a cost *increase*):
            # rounding to whole percent printed E' (+55.4) and E'' (+54.5) identically,
            # erasing the distinction the surrounding argument depends on.
            ax.text(value - 3.0, index + height / 2 + 0.012, f"{-value:+.1f}\u0025 cost",
                    va="center", ha="right", fontsize=7, color=COLORS["series2"])
    _outside_legend(ax)
    fig.tight_layout()
    savefig("demo_suite")


def write_live_table(live: dict[str, Any]) -> None:
    m = live["paired_test"]["metrics"]
    rows = [
        ("Provider requests", "requests", "count"),
        ("Tool calls", "tool_calls", "count"),
        ("Input tokens", "input_tokens", "count"),
        ("Output tokens", "output_tokens", "count"),
        ("Total tokens", "total_tokens", "count"),
        ("Wall latency", "wall_latency_ms", "ms"),
        ("Estimated cost", "estimated_cost_usd", "usd"),
    ]
    out = [
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Metric & Baseline & Compiled & Change & $p_{\mathrm{W}}$ \\",
        r"\midrule",
    ]
    for label, key, kind in rows:
        x = m[key]
        if kind == "usd":
            baseline, compiled = f"\\${x['baseline_mean']:.6f}", f"\\${x['compiled_mean']:.6f}"
        elif kind == "ms":
            baseline, compiled = f"{x['baseline_mean']/1000:.2f} s", f"{x['compiled_mean']/1000:.2f} s"
        else:
            baseline, compiled = f"{x['baseline_mean']:.1f}", f"{x['compiled_mean']:.1f}"
        change = -100 * x["aggregate_reduction"]
        p = x["wilcoxon_p"]
        # A signed-rank test on a constant difference reports degeneracy, not evidence:
        # every pair changes provider requests by exactly -3. Mark it rather than print it.
        spread = {
            abs(round(pair, 9))
            for pair in (x.get("paired_differences") or [])
        }
        if key == "requests":
            p_text = "deterministic"
        else:
            p_text = f"{p:.2g}" if p >= 0.001 else f"{p:.1e}"
        out.append(f"{label} & {baseline} & {compiled} & ${change:+.1f}\\%$ & {p_text} \\\\")
    out += [r"\midrule", r"Task-quality pass rate & 1.000 & 1.000 & 0.0 pp & 1.0 \\", r"\bottomrule", r"\end{tabular}"]
    (TABLES / "live_results.tex").write_text("\n".join(out) + "\n", encoding="utf-8")


def write_natural_live_table(natural: dict[str, Any]) -> None:
    aggregate = natural["aggregate"]
    conditions = [
        ("baseline", "Unchanged agent"),
        ("compiled", r"\method{}"),
        ("macro", "Hand-written macro"),
    ]
    out = [
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        r"Condition & Requests & Tools & Tokens & Wall (s) & Cost & Factual pass \\",
        r"\midrule",
    ]
    for condition, label in conditions:
        row = aggregate[condition]
        records = [item for item in natural["results"] if item["condition"] == condition]
        n = len(records)
        requests = statistics.mean(float(item["metrics"]["requests"]) for item in records)
        tools = statistics.mean(float(item["metrics"]["tool_calls"]) for item in records)
        tokens = statistics.mean(float(item["metrics"]["total_tokens"]) for item in records)
        factual = sum(bool(item["quality"]["overall"]) for item in records)
        out.append(
            f"{label} & {requests:.1f} & {tools:.1f} & {tokens:.1f} & "
            f"{row['wall_latency_ms']/n/1000:.2f} & "
            f"\\${row['estimated_cost_usd']/n:.6f} & {factual}/{n} \\\\"
        )
    out += [r"\bottomrule", r"\end{tabular}"]
    (TABLES / "natural_live_results.tex").write_text("\n".join(out) + "\n", encoding="utf-8")


def write_natural_replication_table(natural: dict[str, Any]) -> None:
    """Expanded paid replication; report primary pairs, not repeat executions."""

    conditions = [
        ("baseline", "Unchanged agent"),
        ("compiled", r"\method{} (two-read prefix)"),
        ("macro", "Hand-written macro"),
    ]
    out = [
        r"\begin{tabular}{lrrrrrr}",
        r"\toprule",
        r"Condition & Requests & Tools & Tokens & Wall (s) & Cost & Exact pass \\",
        r"\midrule",
    ]
    for condition, label in conditions:
        rows = [
            row for row in natural["results"]
            if row["condition"] == condition and row["repeat"] == 0
        ]
        n = len(rows)
        mean = lambda key: statistics.mean(float(row["metrics"][key]) for row in rows)
        exact = sum(bool(row["quality"]["factuality_exact"]) for row in rows)
        out.append(
            f"{label} & {mean('requests'):.1f} & {mean('tool_calls'):.1f} & "
            f"{mean('total_tokens'):.1f} & {mean('wall_latency_ms')/1000:.2f} & "
            f"\\${mean('estimated_cost_usd'):.6f} & {exact}/{n} \\\\"
        )
    out += [r"\bottomrule", r"\end{tabular}"]
    (TABLES / "natural_replication_results.tex").write_text(
        "\n".join(out) + "\n", encoding="utf-8"
    )


def write_gcs_live_table(result: dict[str, Any]) -> None:
    """Exploratory fresh-cohort comparison of synthesized and manual composites."""

    conditions = [
        ("macro", "Provider-visible macro"),
        ("gcs", "Pre-model GCS"),
    ]
    out = [
        r"\begin{tabular}{lrrrrrrr}",
        r"\toprule",
        r"Condition & Requests & Exposed & Reads & Tokens & Wall (s) & Cost & Exact \\",
        r"\midrule",
    ]
    for condition, label in conditions:
        rows = [row for row in result["results"] if row["condition"] == condition]
        n = len(rows)
        mean = lambda key: statistics.mean(float(row["metrics"][key]) for row in rows)
        reads = 3.0  # both interfaces execute the same three pinned source reads
        exact = sum(bool(row["quality"]["overall"]) for row in rows)
        out.append(
            f"{label} & {mean('requests'):.1f} & {mean('tool_calls'):.1f} & "
            f"{reads:.1f} & {mean('total_tokens'):.1f} & "
            f"{mean('wall_latency_ms')/1000:.2f} & "
            f"\\${mean('estimated_cost_usd'):.6f} & {exact}/{n} \\\\"
        )
    out += [r"\bottomrule", r"\end{tabular}"]
    (TABLES / "gcs_live_results.tex").write_text(
        "\n".join(out) + "\n", encoding="utf-8"
    )


def write_nestful_table(nestful: dict[str, Any]) -> None:
    c = nestful["compiler"]
    p = c["provenance"]
    r = c["held_out_replay"]
    rows = [
        ("Executable basic-function episodes", c["n_episodes"]),
        # Reported as three separate outcomes. A single "recovered" row conflated exact
        # resolution with "the truth is somewhere in the candidate set", which reads as
        # dependency reconstruction and is not.
        ("Expected producer in candidate set (recall)", f"{p['expected_producer_recovered']}/{p['dependency_slots']} ({100*p['expected_producer_recall']:.1f}\\%)"),
        ("\\quad of which uniquely resolved", f"{p['expected_producer_unique']} ({100*p['unique_resolution_rate']:.1f}\\%)"),
        ("\\quad of which ambiguous (truth among many)", f"{p['expected_producer_ambiguous']} ({100*p['ambiguous_containing_truth_rate']:.1f}\\%)"),
        ("Slots with no candidate", p["no_candidate"]),
        ("Candidate-edge precision", f"{p['expected_producer_recovered']}/{p['candidate_edges']} ({100*p['candidate_edge_precision']:.1f}\\%)"),
        ("Complete groundable windows", f"{c['n_full_windows']}/{c['n_graphs']} ({100*c['full_window_rate']:.1f}\\%)"),
        ("Recurring families with support $\\geq 5$", c["compiler_families"]["n_support_ge_5"]),
        ("Synthesized families", f"{r['families_synthesized']}/{r['families_attempted']}"),
        ("Held-out replay: pass / abstain / wrong", f"{r['test_passed']} / {r['test_abstained']} / {r['test_wrong']}"),
        ("Maximum family support / gate minimum", f"{c['exact_gate']['max_observed_family_support']} / {c['exact_gate']['minimum_zero_violation_groups']}"),
        ("Certifiable families", c["exact_gate"]["families_certifiable_even_with_zero_violations"]),
        ("Peak memory / elapsed time", f"{c['runtime']['peak_memory_mib']:.1f} MiB / {c['runtime']['total_seconds']:.2f} s"),
        # Reordered per review: resolution and precision are the load-bearing numbers;
        # recall is bounded below by groundability and is insensitive to ranking quality.
    ]
    out = [r"\begin{tabular}{lr}", r"\toprule", r"Measurement & Result \\", r"\midrule"]
    out.extend(f"{label} & {value} \\\\" for label, value in rows)
    out += [r"\bottomrule", r"\end{tabular}"]
    (TABLES / "nestful_results.tex").write_text("\n".join(out) + "\n", encoding="utf-8")


def write_related_work_table() -> None:
    rows = [
        ("LLMCompiler", "Current-query scheduling", "Parallel tool calls", "No", "No"),
        # A slash is not a break opportunity in TeX, so "Prompt/program parameters" and
        # "pruning/quantization" overflowed their cells. \slash{} permits the break.
        ("DSPy / MIPRO", r"Prompt\slash{}program parameters", "Metric optimization", "No", "No"),
        ("GEPA", "Execution + evaluation traces", "Reflective prompt evolution", "No", "Held-out metric + Pareto"),
        ("AgentSlimming", "Multi-agent graph", r"Node pruning\slash{}quantization", "No",
         "Baseline rule"),
        ("AWO", "Trace tool sequences", "Deterministic meta-tools", "No", "Empirical"),
        ("Agent JIT", "Task description", "Validated code + schedule", "Tool pre/post invariants", "Candidate validation"),
        ("EvoC2F", "Plan IR + trajectories", "DAG compiler + macro-skills", "Effects + resources", "Tests + contracts"),
        ("FlowCompile", "Declared workflow", "Configuration Pareto set", "No", "Profiled"),
        ("COVENANT", "Declared policy", "Workflow CFG", "Effects", "Runtime checks"),
        ("GAC (ours)", "Observed value flow", "Decision-eliding program", "Provenance + effects", "Exact selective bound"),
    ]
    # Wrapping columns instead of `lllll`: the fixed form is wider than the measure, and
    # \resizebox then shrank the whole table below body-text size. The last two columns
    # carry the comparison the table exists for, so they get the slack.
    # Four wrapping columns, not two: with `l l l X X` the three natural-width columns
    # consumed most of the measure and the remaining X columns could not wrap short
    # enough, producing 13 overfull cells up to 29.96pt (cells printed past their rules).
    wrap = r">{\raggedright\arraybackslash}X"
    out = [
        r"\begin{tabularx}{\linewidth}{@{}l " + " ".join([wrap] * 4) + r"@{}}",
        r"\toprule",
        r"System & Source & Rewrite target & Hard safety & Admission \\",
        r"\midrule",
    ]
    out.extend(
        " & ".join(x if "\\slash" in str(x) else tex(x) for x in row) + r" \\"
        for row in rows
    )
    out += [r"\bottomrule", r"\end{tabularx}"]
    (TABLES / "related_work.tex").write_text("\n".join(out) + "\n", encoding="utf-8")


def write_claims_table() -> None:
    rows = [
        ("C1", "The expected producer appears in the provenance candidate set", "Pinned NESTFUL: 5,531/5,746 dependency slots", "96.3% candidate recall; 80.7% unique resolution"),
        ("C2", "A naturally recurring prefix can remove model decisions", "132 live discovery records; 30 counterbalanced real-record tests", "Two-read prefix cuts requests 50%; one frozen-snapshot domain"),
        ("C3", "Source-grounded task quality is preserved", "Expanded partial compiler: all three arms 30/30; earlier aggressive compiler: 17/18", "Supported on the expanded sample, not across domains or compilation depths"),
        ("C4", "Configured selective admission is data hungry", "NESTFUL max support 26 vs. required 92", "Supported for this grid/risk/confidence setting"),
        # "Contradicted" overreaches at n=6: 1/6 versus 0/6 cannot establish a direction.
        # Rigour has to be symmetric -- a negative claim needs the same evidence bar as a
        # positive one.
        ("C5", "Compaction improves text determinism",
         "Exact-answer agreement 1/6 vs. 0/6 ($n=6$)", "Not supported"),
        ("C6", "The artifact is production safe", "No live GitHub service, canary, or multi-domain test", "Not supported"),
        ("C7", "The learned gate discriminates risky from safe inputs", "0 positive dev examples; gate admits none or all", "Not supported"),
        ("C8", "Factual summary quality is preserved", "Oracle accepts fluent fabrication", "Not evaluated"),
        ("C9", "The learned compiler generally dominates a hand-written macro", "Macro beats partial GRC on 30 pairs; GCS beats provider-visible macro on 12 later pairs", "Not supported across interfaces or workflow families"),
        ("C10", "A separate continuation contract can recover the retained exact-source miss", "Provider-free replay detects issue 6602 and checked-renders 1/18 cases", "Verified counterfactual; no live latency, cost, or cross-domain claim"),
        ("C11", "The portfolio recommends a measured macro", "30 frozen independent groups; 12 fresh paired issues", "Verified on one workflow family; recommendation requires human review"),
        ("C12", "The portfolio synthesizes a macro or evaluates a cache action", "Public portfolio API accepts externally supplied measurements only", "Not implemented"),
        ("C13", "Portfolio selection beats an always-macro policy across workflows", "One family in which the measured macro is selected", "Not supported"),
        ("C14", "Guarded composite synthesis beats the measured provider-visible macro", "12 fresh paired real-record cases; both 12/12 exact", "Exploratory: requests -50%, tokens -38.9%, latency -40.0%, cost -32.3%; one workflow family"),
    ]
    # Wrapping columns rather than `llll`: the prose cells give a fixed tabular a
    # natural width several times the text measure, and the only way to place that is
    # to shrink it to an illegible size. tabularx wraps to the measure instead, so the
    # table needs no \resizebox in either the one- or two-column build.
    wrap = r">{\raggedright\arraybackslash}X"
    out = [
        r"\begin{tabularx}{\linewidth}{@{}l " + " ".join([wrap] * 3) + r"@{}}",
        r"\toprule",
        r"ID & Claim & Direct evidence & Verdict \\",
        r"\midrule",
    ]
    out.extend(" & ".join(tex(x) for x in row) + r" \\" for row in rows)
    out += [r"\bottomrule", r"\end{tabularx}"]
    (TABLES / "claims_register.tex").write_text("\n".join(out) + "\n", encoding="utf-8")


def write_manifest(inputs: list[Path]) -> None:
    records: list[dict[str, object]] = []
    for path in sorted(inputs + list(FIGURES.glob("*")) + list(TABLES.glob("*"))):
        data = path.read_bytes()
        records.append(
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    payload = {
        "generator": "paper/scripts/build_artifacts.py",
        "note": "No provider calls are made by this script.",
        "artifacts": records,
    }
    (RESULTS / "artifact_manifest.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    configure_plots()
    live = load_json(LIVE_PATH)
    natural = load_json(NATURAL_LIVE_PATH)
    replication = load_json(NATURAL_REPLICATION_PATH)
    portfolio = load_json(PORTFOLIO_PATH)
    gcs_live = load_json(GCS_LIVE_PATH)
    pilot = load_json(PILOT_PATH)
    nestful = load_json(NESTFUL_PATH)
    live_efficiency_figure(live)
    paired_figure(live)
    gate_support_figure(nestful)
    pilot_figure(live, pilot)
    natural_comparison_figure(replication)
    portfolio_selection_figure(portfolio)
    demo_suite_figure()
    write_live_table(live)
    write_natural_live_table(natural)
    write_natural_replication_table(replication)
    write_portfolio_table(portfolio)
    write_gcs_live_table(gcs_live)
    write_nestful_table(nestful)
    write_related_work_table()
    write_demo_suite_table()
    write_comparator_table()
    write_claims_table()
    write_manifest([
        LIVE_PATH, NATURAL_LIVE_PATH, NATURAL_REPLICATION_PATH, PORTFOLIO_PATH,
        GCS_LIVE_PATH, GCS_VALIDATION_PATH,
        PILOT_PATH, NESTFUL_PATH, FAMILY_PATH,
    ])
    print(f"wrote {len(list(FIGURES.iterdir()))} figures and {len(list(TABLES.iterdir()))} tables")


if __name__ == "__main__":
    main()
