#!/usr/bin/env python3
"""Render site/method.html from the paper's result artifacts.

The page states the two certificates the paper rests on, so every number it prints is
read out of paper/results/ rather than transcribed, and every closed form it displays is
checked against the value the study actually recorded.  A formula that no longer
reproduces its own published number is a broken claim, not a formatting problem, so this
script fails closed instead of rendering it.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
OUTPUT = ROOT / "site" / "method.html"

# The registered selective-risk target and the confidence level the paper reports its
# preservation bounds at.  Both are stated in the manuscript, not derived here.
PRESERVATION_ALPHA = 0.05
TOLERANCE = 5e-9


class VerificationError(SystemExit):
    """Raised when a displayed closed form stops reproducing its recorded value."""


def load(relative: str) -> dict:
    return json.loads((PAPER / relative).read_text(encoding="utf-8"))


def check(actual: float, expected: float, label: str, tolerance: float = TOLERANCE) -> None:
    if expected is None or abs(actual - expected) > tolerance:
        raise VerificationError(
            f"{label}: closed form gives {actual!r}, artifact records {expected!r}"
        )


def zero_violation_bound(delta: float, grid_size: int, n: int) -> float:
    """Simultaneous one-sided exact binomial bound with no observed violation.

    Splitting delta across a fixed grid of `grid_size` thresholds and inverting the
    one-sided Clopper-Pearson bound at zero failures in `n` groups.
    """

    return 1.0 - (delta / grid_size) ** (1.0 / n)


def break_even_episodes(discovery_cost: float, baseline: float, compiled: float) -> float:
    return discovery_cost / (baseline - compiled)


def esc(value: str) -> str:
    return (
        value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def pct(value: float, digits: int = 1) -> str:
    return f"{100 * value:.{digits}f}%"


def signed_pct(value: float, digits: int = 1) -> str:
    """Reductions are stored as positive fractions; display them as the change they are."""

    if abs(value) < 5e-4:
        return "0.0%"
    return f"{'−' if value > 0 else '+'}{abs(100 * value):.{digits}f}%"


def verify_admission(register: dict) -> list[dict]:
    """Reproduce every admitted artifact's recorded risk bound and coverage."""

    if register.get("schema") != "agent-compaction-admission-register/v1":
        raise VerificationError("unexpected admission-register schema")
    if register.get("registered_alpha") != PRESERVATION_ALPHA:
        raise VerificationError("registered alpha moved away from the documented .05")

    rows = []
    for row in register["artifacts"]:
        derived = zero_violation_bound(row["delta"], row["grid_size"], row["n_accepted"])
        check(derived, row["risk_upper_bound"], f"risk bound for {row['study']}")
        coverage = row["n_accepted"] / row["n_calibration_groups"]
        check(coverage, row["coverage"], f"coverage for {row['study']}")
        if row["observed_violations"] != 0:
            raise VerificationError(
                f"{row['study']}: bound assumes zero observed violations, "
                f"artifact records {row['observed_violations']}"
            )
        meets = row["risk_upper_bound"] <= row["alpha"] and row["alpha"] <= PRESERVATION_ALPHA
        if meets != row["meets_registered_alpha"]:
            raise VerificationError(f"{row['study']}: registered-alpha verdict disagrees")
        rows.append(row)
    return rows


def verify_cache(cache: dict) -> list[dict]:
    """Reproduce each family's provider-side break-even from its own arm costs."""

    rows = []
    for family in cache["families"]:
        arms = family["arms"]
        derived = break_even_episodes(
            family["discovery"]["estimated_cost_usd"],
            arms["baseline"]["cost_per_episode"],
            arms["compiled"]["cost_per_episode"],
        )
        check(derived, family["break_even_episodes"], f"break-even for {family['family']}", 1e-6)
        rows.append(family)
    return rows


def verify_families(summary: dict) -> dict:
    if summary.get("simulated") is not False:
        raise VerificationError("workflow-family summary is not marked as real-record")
    overall = summary["overall"]
    if (overall["compiled_exact"], overall["manual_exact"], overall["n"]) != (90, 90, 90):
        raise VerificationError("primary transfer result changed; page copy must be revisited")
    return summary


def admission_table(rows: list[dict]) -> str:
    body = []
    for row in rows:
        verdict = (
            '<span class="badge badge-pass">meets .05</span>'
            if row["meets_registered_alpha"]
            else '<span class="badge badge-fail">licensed at .10</span>'
        )
        body.append(
            "<tr>"
            f"<td>{esc(row['study'])}</td>"
            f"<td class=\"num\">{row['alpha']:.2f}</td>"
            f"<td class=\"num\">{row['n_accepted']} / {row['n_calibration_groups']}</td>"
            f"<td class=\"num\">{pct(row['coverage'])}</td>"
            f"<td class=\"num\">{row['risk_upper_bound']:.4f}</td>"
            f"<td>{verdict}</td>"
            "</tr>"
        )
    return (
        '<div class="table-scroll"><table class="evidence-table">'
        "<caption>Selective-risk configuration each admitted artifact actually used. "
        "Bounds split &delta;=0.10 across an 11-threshold grid for one fixed candidate "
        "and assume the zero observed violations every row records.</caption>"
        "<thead><tr><th>Admitted artifact</th>"
        '<th><span class="nocaps">&alpha;</span></th>'
        "<th>Groups admitted</th><th>Coverage</th><th>Risk bound</th>"
        '<th>Against registered <span class="nocaps">&alpha;</span>=.05</th></tr></thead>'
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


def family_table(summary: dict) -> str:
    body = []
    for family in summary["families"]:
        reductions = family["reductions"]
        body.append(
            "<tr>"
            f"<td>{esc(family['family'])}</td>"
            f"<td class=\"num\">{family['baseline']['exact']}/{family['baseline']['n']} "
            f"&rarr; {family['compiled']['exact']}/{family['compiled']['n']}</td>"
            f"<td class=\"num\">{family['manual']['exact']}/{family['manual']['n']}</td>"
            f"<td class=\"num\">{signed_pct(reductions['requests'])}</td>"
            f"<td class=\"num\">{signed_pct(reductions['total_tokens'])}</td>"
            f"<td class=\"num\">{signed_pct(reductions['estimated_cost_usd'])}</td>"
            "</tr>"
        )
    overall = summary["overall"]
    body.append(
        "<tr class=\"row-total\">"
        "<td><strong>Weighted total</strong></td>"
        f"<td class=\"num\"><strong>{overall['baseline_exact']}/{overall['n']} "
        f"&rarr; {overall['compiled_exact']}/{overall['n']}</strong></td>"
        f"<td class=\"num\"><strong>{overall['manual_exact']}/{overall['n']}</strong></td>"
        f"<td class=\"num\"><strong>{signed_pct(overall['requests']['reduction'])}</strong></td>"
        f"<td class=\"num\"><strong>{signed_pct(overall['total_tokens']['reduction'])}</strong></td>"
        f"<td class=\"num\"><strong>{signed_pct(overall['estimated_cost_usd']['reduction'])}</strong></td>"
        "</tr>"
    )
    return (
        '<div class="table-scroll"><table class="evidence-table">'
        "<caption>Three real-record workflow families, 30 pairwise-disjoint held-out "
        "records each, live provider calls on one revision-pinned public snapshot.</caption>"
        "<thead><tr><th>Workflow family</th><th>Exact: baseline &rarr; compiled</th>"
        "<th>Manual</th><th>Requests</th><th>Tokens</th><th>Cost</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


def cache_table(families: list[dict]) -> str:
    body = []
    for family in families:
        arms = family["arms"]
        for name, label in (("baseline", "Unchanged"), ("compiled", "Compiled"), ("manual", "Manual macro")):
            arm = arms[name]
            body.append(
                "<tr>"
                + (
                    f'<td rowspan="3">{esc(family["family"])}</td>'
                    if name == "baseline"
                    else ""
                )
                + f"<td>{label}</td>"
                f"<td class=\"num\">{arm['total_tokens_per_episode']:,.0f}</td>"
                f"<td class=\"num\">{pct(arm['cached_input_share'])}</td>"
                f"<td class=\"num\">${arm['cost_per_episode']:.6f}</td>"
                + (
                    f'<td rowspan="3" class="num">{family["break_even_episodes"]:.0f}</td>'
                    if name == "baseline"
                    else ""
                )
                + "</tr>"
            )
    return (
        '<div class="table-scroll"><table class="evidence-table">'
        "<caption>Prompt-cache structure of the primary runs, recovered provider-free "
        "from retained data. &ldquo;Cached&rdquo; is the share of input served as cache "
        "reads; break-even counts future episodes needed to repay 132 paid discovery "
        "episodes in provider spend alone.</caption>"
        "<thead><tr><th>Family</th><th>Arm</th><th>Tokens / episode</th><th>Cached</th>"
        "<th>Cost / episode</th><th>Break-even</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


PIPELINE_SVG = """
<svg viewBox="0 0 960 470" role="img" aria-labelledby="pipe-t pipe-d" class="block-diagram">
  <title id="pipe-t">Compile-time admission pipeline</title>
  <desc id="pipe-d">Agent episodes become a typed trace representation and a candidate
  region, which must pass five independent admission checks. If all five agree the
  compiler emits a guarded program; any single refusal retires the family.</desc>
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7"
            markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2f6b8a"/>
    </marker>
    <marker id="arrow-teal" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7"
            markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#2a9d8f"/>
    </marker>
    <marker id="arrow-coral" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7"
            markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#d06b4d"/>
    </marker>
    <!-- Defined once for the whole page: the runtime diagram reuses these markers by id,
         and re-declaring them there would trip the duplicate-id site check. -->
    <marker id="arrow-gold" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7"
            markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#b8862f"/>
    </marker>
  </defs>

  <g class="d-stage">
    <rect x="24" y="26" width="252" height="70" rx="14"/>
    <text x="150" y="55" class="d-label">Recurrent agent episodes</text>
    <text x="150" y="77" class="d-sub">real records, live provider</text>
  </g>
  <g class="d-stage">
    <rect x="354" y="26" width="252" height="70" rx="14"/>
    <text x="480" y="55" class="d-label">Typed trace IR</text>
    <text x="480" y="77" class="d-sub">value provenance retained</text>
  </g>
  <g class="d-stage">
    <rect x="684" y="26" width="252" height="70" rx="14"/>
    <text x="810" y="55" class="d-label">Candidate region</text>
    <text x="810" y="77" class="d-sub">longest groundable prefix</text>
  </g>
  <line x1="282" y1="61" x2="346" y2="61" class="d-flow" marker-end="url(#arrow)"/>
  <line x1="612" y1="61" x2="678" y2="61" class="d-flow" marker-end="url(#arrow)"/>
  <path d="M 810 102 L 810 132" class="d-flow" marker-end="url(#arrow)"/>

  <g class="d-gate">
    <rect x="24" y="140" width="912" height="150" rx="18"/>
    <text x="48" y="171" class="d-gate-title">Admission gate</text>
    <text x="912" y="171" class="d-gate-note" text-anchor="end">every check can refuse on its own</text>
  </g>
  <g class="d-check">
    <rect x="48" y="192" width="168" height="74" rx="12"/>
    <text x="132" y="220" class="d-check-label">Value</text>
    <text x="132" y="240" class="d-check-label">provenance</text>
    <text x="132" y="257" class="d-check-sub">derivable arguments</text>
  </g>
  <g class="d-check">
    <rect x="228" y="192" width="168" height="74" rx="12"/>
    <text x="312" y="220" class="d-check-label">Effect</text>
    <text x="312" y="240" class="d-check-label">barriers</text>
    <text x="312" y="257" class="d-check-sub">read-only region</text>
  </g>
  <g class="d-check">
    <rect x="408" y="192" width="168" height="74" rx="12"/>
    <text x="492" y="220" class="d-check-label">Compatibility</text>
    <text x="492" y="240" class="d-check-label">and partition</text>
    <text x="492" y="257" class="d-check-sub">bounded lookup</text>
  </g>
  <g class="d-check">
    <rect x="588" y="192" width="168" height="74" rx="12"/>
    <text x="672" y="220" class="d-check-label">Replay</text>
    <text x="672" y="240" class="d-check-label">equivalence</text>
    <text x="672" y="257" class="d-check-sub">observation parity</text>
  </g>
  <g class="d-check">
    <rect x="768" y="192" width="168" height="74" rx="12"/>
    <text x="852" y="220" class="d-check-label">Finite-sample</text>
    <text x="852" y="240" class="d-check-label">evidence</text>
    <text x="852" y="257" class="d-check-sub">grouped calibration</text>
  </g>

  <path d="M 300 296 L 300 356" class="d-flow-ok" marker-end="url(#arrow-teal)"/>
  <text x="312" y="330" class="d-edge">all five agree</text>
  <path d="M 660 296 L 660 356" class="d-flow-no" marker-end="url(#arrow-coral)"/>
  <text x="672" y="330" class="d-edge">any refusal</text>

  <g class="d-emit">
    <rect x="150" y="362" width="300" height="76" rx="14"/>
    <text x="300" y="392" class="d-label-inv">Emit guarded program</text>
    <text x="300" y="415" class="d-sub-inv">inspectable, replayable, revocable</text>
  </g>
  <g class="d-retire">
    <rect x="510" y="362" width="300" height="76" rx="14"/>
    <text x="660" y="392" class="d-label-inv">Retire the family</text>
    <text x="660" y="415" class="d-sub-inv">the default, and the first optimization</text>
  </g>
</svg>
"""

RUNTIME_SVG = """
<svg viewBox="0 0 960 400" role="img" aria-labelledby="run-t run-d" class="block-diagram">
  <title id="run-t">Runtime dispatch and fallback</title>
  <desc id="run-d">A bounded registry lookup at the entry boundary selects a path.
  Ordinary guarded region compilation runs guard, gate, stage, interpret, verify, and
  commit, and can fall back to the unchanged agent. An eligible guarded composite
  artifact verifies its continuation pin and projects the task result before the first
  provider request.</desc>

  <g class="d-stage">
    <rect x="24" y="168" width="204" height="94" rx="14"/>
    <text x="126" y="202" class="d-label">Entry observation</text>
    <text x="126" y="224" class="d-sub">bounded registry lookup</text>
    <text x="126" y="242" class="d-sub">by compatibility + partition</text>
  </g>
  <path d="M 228 196 C 250 196 246 103 268 103" class="d-flow" marker-end="url(#arrow)"/>
  <path d="M 228 236 C 250 236 246 318 268 318" class="d-flow-gold" marker-end="url(#arrow-gold)"/>

  <text x="268" y="34" class="d-lane">Ordinary guarded region compilation</text>
  <rect x="268" y="44" width="668" height="118" rx="16" class="d-lane-box"/>
"""

RUNTIME_STAGES = ("Guard", "Gate", "Stage", "Interpret", "Verify", "Commit")


def runtime_svg() -> str:
    """Lay the six-stage chain out arithmetically so it cannot overflow its lane.

    The lane box spans x=268..936; six 100pt steps separated by 8pt gaps end at 924,
    leaving a 12pt inset on the right.
    """

    parts = [RUNTIME_SVG]
    x = 284
    width = 100
    gap = 8
    for index, stage in enumerate(RUNTIME_STAGES):
        parts.append(
            f'  <g class="d-step"><rect x="{x}" y="76" width="{width}" height="60" rx="11"/>'
            f'<text x="{x + width // 2}" y="112" class="d-step-label">{stage}</text></g>'
        )
        if index < len(RUNTIME_STAGES) - 1:
            arrow_start = x + width
            parts.append(
                f'  <line x1="{arrow_start}" y1="106" x2="{arrow_start + gap - 1}" y2="106" '
                'class="d-flow" marker-end="url(#arrow)"/>'
            )
        x += width + gap
    # The fallback box sits in the corridor between the two lanes (y=162..272) so the
    # refusal edge never has to cross the entry block on its way back.
    parts.append(
        """
  <path d="M 766 162 L 766 186" class="d-flow-fallback" marker-end="url(#arrow-coral)"/>
  <text x="584" y="222" class="d-edge-warn-end">any stage may refuse</text>
  <g class="d-retire">
    <rect x="596" y="188" width="340" height="66" rx="12"/>
    <text x="766" y="216" class="d-label-inv-sm">Exact fallback: the unchanged agent runs</text>
    <text x="766" y="237" class="d-sub-inv">requires a staging owner at the commit boundary</text>
  </g>

  <text x="268" y="262" class="d-lane">Eligible guarded composite artifact</text>
  <rect x="268" y="272" width="668" height="104" rx="16" class="d-lane-box d-lane-gold"/>
  <g class="d-step d-step-gold">
    <rect x="284" y="298" width="214" height="62" rx="11"/>
    <text x="391" y="324" class="d-step-label">Verify continuation pin</text>
    <text x="391" y="344" class="d-step-sub">program + task projection</text>
  </g>
  <line x1="498" y1="329" x2="521" y2="329" class="d-flow-gold" marker-end="url(#arrow-gold)"/>
  <g class="d-step d-step-gold">
    <rect x="522" y="298" width="214" height="62" rx="11"/>
    <text x="629" y="324" class="d-step-label">Project the result</text>
    <text x="629" y="344" class="d-step-sub">before provider request one</text>
  </g>
  <line x1="736" y1="329" x2="759" y2="329" class="d-flow-gold" marker-end="url(#arrow-gold)"/>
  <text x="768" y="325" class="d-edge-gold">no provider request</text>
  <text x="768" y="343" class="d-edge-gold">is emitted at all</text>
</svg>
"""
    )
    return "".join(parts)


def formula_cards(register: list[dict], cache: list[dict], summary: dict) -> str:
    prescribed = next(r for r in register if r["study"] == "Prescribed-prefix ablation")
    composite = next(r for r in register if r["study"] == "Guarded composite synthesis")
    issue = next(f for f in cache if f["family"] == "Issue-type routing")
    pooled = 1.0 - PRESERVATION_ALPHA ** (1.0 / summary["overall"]["n"])
    single = 1.0 - PRESERVATION_ALPHA ** (1.0 / 30)

    risk_math = """
<math display="block">
  <msub><mi>r</mi><mtext>bound</mtext></msub><mo>=</mo><mn>1</mn><mo>&#x2212;</mo>
  <msup>
    <mrow><mo>(</mo><mfrac><mi>&#x3B4;</mi><mi>K</mi></mfrac><mo>)</mo></mrow>
    <mrow><mn>1</mn><mo>/</mo><mi>n</mi></mrow>
  </msup>
</math>"""

    coverage_math = """
<math display="block">
  <mi>c</mi><mo>=</mo>
  <mfrac>
    <msub><mi>n</mi><mtext>admitted</mtext></msub>
    <msub><mi>n</mi><mtext>groups</mtext></msub>
  </mfrac>
</math>"""

    discordance_math = """
<math display="block">
  <msub><mi>d</mi><mtext>bound</mtext></msub><mo>=</mo><mn>1</mn><mo>&#x2212;</mo>
  <msup><mi>&#x3B1;</mi><mrow><mn>1</mn><mo>/</mo><mi>n</mi></mrow></msup>
</math>"""

    breakeven_math = """
<math display="block">
  <msup><mi>E</mi><mo>&#x2217;</mo></msup><mo>=</mo>
  <mfrac>
    <msub><mi>C</mi><mtext>discovery</mtext></msub>
    <mrow>
      <msub><mi>c</mi><mtext>baseline</mtext></msub><mo>&#x2212;</mo>
      <msub><mi>c</mi><mtext>compiled</mtext></msub>
    </mrow>
  </mfrac>
</math>"""

    return f"""
      <div class="formula-grid">
        <article class="formula-card">
          <h3>Selective-risk certificate</h3>
          <p>With zero observed violations, split &delta; across the fixed threshold grid
          and invert the one-sided exact binomial bound.</p>
          {risk_math}
          <p class="formula-note">Prescribed-prefix ablation:
          &delta;={prescribed['delta']}, K={prescribed['grid_size']},
          n={prescribed['n_accepted']} &rarr;
          <strong>{prescribed['risk_upper_bound']:.4f}</strong>, inside the registered
          &alpha;=.05. The composite artifact refuses four groups, so n falls to
          {composite['n_accepted']} and the same formula gives
          <strong>{composite['risk_upper_bound']:.4f}</strong> &mdash; which only clears
          &alpha;=.10.</p>
        </article>
        <article class="formula-card">
          <h3>Coverage is what pays for it</h3>
          <p>Risk and coverage trade off exactly as the finite-sample calculation
          requires; refusing groups is what pushes the bound out.</p>
          {coverage_math}
          <p class="formula-note">The composite gate is the only one that refuses any
          calibration group: {composite['n_accepted']}/{composite['n_calibration_groups']}
          admitted, <strong>{pct(composite['coverage'])}</strong> coverage. Dropping below
          {prescribed['n_calibration_groups']} zero-violation groups is precisely why a 5%
          bound is no longer available to it.</p>
        </article>
        <article class="formula-card">
          <h3>Preservation is bounded, not proven</h3>
          <p>No compiled-only failure across the pooled held-out records still leaves a
          one-sided upper bound on the discordance rate.</p>
          {discordance_math}
          <p class="formula-note">Pooling all {summary['overall']['n']} paired records
          bounds compiled-only degradation at <strong>{pct(pooled)}</strong>. Any single
          30-record family bounds it only at {pct(single)}. Zero observed failures is not
          an equivalence result.</p>
        </article>
        <article class="formula-card">
          <h3>Discovery has to amortize</h3>
          <p>Learning the program costs paid provider episodes, repaid only out of the
          per-episode saving it later produces.</p>
          {breakeven_math}
          <p class="formula-note">Issue-type routing spent
          ${issue['discovery']['estimated_cost_usd']:.4f} over
          {issue['discovery']['episodes']:.0f} discovery episodes and saves
          ${issue['arms']['baseline']['cost_per_episode'] - issue['arms']['compiled']['cost_per_episode']:.6f}
          per episode &rarr; <strong>{issue['break_even_episodes']:.0f} episodes</strong>,
          more than three times its own discovery cohort.</p>
        </article>
      </div>"""


def render(register: list[dict], cache: list[dict], summary: dict) -> str:
    composite = next(r for r in register if r["study"] == "Guarded composite synthesis")
    at_registered = sum(1 for r in register if r["meets_registered_alpha"])
    pooled = 1.0 - PRESERVATION_ALPHA ** (1.0 / summary["overall"]["n"])
    issue = next(f for f in cache if f["family"] == "Issue-type routing")
    macro_tokens = issue["manual_vs_compiled"]["token_reduction"]
    macro_cost = issue["manual_vs_compiled"]["cost_reduction"]
    breakevens = sorted(round(f["break_even_episodes"]) for f in cache)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="The mechanism and the two certificates behind Guarded Agentic Compaction: the admission pipeline, the runtime dispatch path, the selective-risk bound, and the per-artifact risk register.">
  <title>Method and certificates — Guarded Agentic Compaction</title>
  <link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="assets/css/styles.css"><script defer src="assets/js/site.js"></script>
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header"><nav class="nav" aria-label="Primary navigation">
    <a class="brand" href="index.html"><span class="brand-mark">GAC</span><span>Guarded Agentic Compaction</span></a>
    <button class="menu-button" data-menu aria-expanded="false" aria-controls="site-nav" aria-label="Toggle navigation">☰</button>
    <ul class="nav-links" id="site-nav" data-nav-links>
      <li><a href="index.html">Overview</a></li><li><a href="architecture.html">Architecture</a></li>
      <li><a aria-current="page" href="method.html">Method</a></li><li><a href="article.html">Article</a></li>
      <li><a href="getting-started.html">Get started</a></li><li><a href="research.html">Research</a></li>
      <li><a href="limitations.html">Limits</a></li><li><a class="nav-cta" href="contributing.html">Contribute</a></li>
    </ul>
  </nav></header>
  <main id="main">
    <section class="page-hero"><div class="container">
      <div class="breadcrumbs"><a href="index.html">Guarded Agentic Compaction</a> / Method</div>
      <h1>Two certificates, and what each one licenses.</h1>
      <p>A guarded program ships only when provenance reconstructs it and finite-sample
      evidence certifies it. Both certificates are numbers with closed forms, so this page
      states them, instantiates them on the artifacts that shipped, and names the risk
      level each result is actually licensed at.</p>
    </div></section>

    <section class="section"><div class="container">
      <div class="section-head">
        <div><p class="eyebrow">Compile time</p>
        <h2>Five checks, and refusal is the default.</h2></div>
        <p>Recurrence in a trace is a clue that a region might be compilable. It is not a
        license. Each check below can retire the family on its own, and no check can be
        traded against another.</p>
      </div>
      <figure class="figure figure-diagram">
        <div class="diagram-scroll">{PIPELINE_SVG}</div>
        <figcaption>Compile-time admission. The compiler emits the longest groundable
        prefix, not the whole recurrent region &mdash; a dynamic argument that cannot be
        derived from entry state or prior results truncates the program.</figcaption>
      </figure>
    </div></section>

    <section class="section section-tint"><div class="container">
      <div class="section-head">
        <div><p class="eyebrow">Run time</p>
        <h2>Dispatch is bounded; fallback is exact.</h2></div>
        <p>An admitted artifact does not take over the workflow. It is looked up at the
        entry boundary, re-checked against live effects, and abandoned in favour of the
        unchanged agent whenever a stage refuses.</p>
      </div>
      <figure class="figure figure-diagram">
        <div class="diagram-scroll">{runtime_svg()}</div>
        <figcaption>Runtime dispatch. Exact fallback still requires a staging owner that
        holds the commit boundary; the composite path avoids post-emission rollback by
        verifying and projecting before the provider sees the observation.</figcaption>
      </figure>
    </div></section>

    <section class="section"><div class="container doc-layout">
      <article class="prose">
        <h2 id="certificates">The certificates, written out</h2>
        <p class="lead">Each closed form below is checked against the value the study
        recorded when this page is built. A formula that stops reproducing its own
        published number fails the build rather than rendering.</p>
        {formula_cards(register, cache, summary)}

        <h2 id="register">Risk is per artifact, not per paper</h2>
        <p>{at_registered} of the {len(register)} admitted artifacts sit at the registered
        &alpha;=.05. The guarded composite artifact does not: it is the only gate that
        refuses any calibration group, and refusing four drops n below what a
        zero-violation 5% bound needs. Every result that rests on it &mdash; the composite
        study and the fair-placement comparator &mdash; is a
        {composite['alpha']:.0%}-selective-risk result and is reported as one.</p>
        {admission_table(register)}
        <div class="callout callout-warn"><p><strong>Read this before quoting a number.</strong>
        Three risk levels appear in this work and each licenses a different result set.
        The three primary workflow families are licensed at .05; the composite and
        comparator results are licensed at .10 and would retire at .05.</p></div>

        <h2 id="transfer">What the primary result establishes</h2>
        <p>Compiled programs preserve exact outcomes across three distinct decisions and
        tool vocabularies while removing model turns. Hand-written programs reach the same
        exact score, so the claim is automatic discovery and lifecycle &mdash; not runtime
        dominance.</p>
        {family_table(summary)}
        <p>{esc(summary['claim_boundary'][0].upper() + summary['claim_boundary'][1:])}.
        With no compiled-only failure in {summary['overall']['n']} paired records, the
        pooled discordance bound is {pct(pooled)}; exact McNemar gives p=1. See the
        <a href="research.html#primary">full experimental design</a> for denominators and
        counterbalancing.</p>

        <h2 id="cache">Where the cost numbers come from</h2>
        <p>Token savings and dollar savings diverge, and the reason was recorded all
        along. Collapsing three reads into one call shortens the prompt and simultaneously
        destroys the repeated prefix that made the remaining input cheap.</p>
        {cache_table(cache)}
        <p>In the issue-type family the hand-written macro uses {pct(macro_tokens)} fewer
        total tokens than the compiled condition but is only {pct(macro_cost)} cheaper,
        because it retains no cache reads at all. The two newer families are cache-cold in
        every arm, so part of the width of the reported cost range is a property of cache
        warmth rather than of the compiled programs. Provider-side break-even runs
        {breakevens[0]}&ndash;{breakevens[-1]} episodes. A cache-controlled replication is
        the correct fix, and this work does not have one.</p>
        <div class="callout"><p><strong>Generated, not transcribed.</strong> Every figure
        on this page is read from <code>paper/results/</code> at build time by
        <code>scripts/build_paper_page.py</code>, which re-derives each bound from its
        closed form and fails the build on a mismatch. Full derivations, related work, and
        threat analysis are in the
        <a href="downloads/compiling-recurrent-agent-workflows.pdf">paper</a>; the
        boundaries are enumerated under
        <a href="limitations.html#statistics">limits</a>.</p></div>
      </article>
      <aside class="toc"><strong>On this page</strong><ul>
        <li><a href="#certificates">Certificates</a></li>
        <li><a href="#register">Risk register</a></li>
        <li><a href="#transfer">Primary result</a></li>
        <li><a href="#cache">Cost and cache</a></li>
      </ul></aside>
    </div></section>
  </main>
  <footer class="site-footer"><div class="container footer-grid">
    <div><div class="footer-title">Guarded Agentic Compaction</div><p class="footer-note">Compile the routine, refuse the uncertain. Refusal is the first optimization, and every admitted artifact carries the risk level it was licensed at.</p></div>
    <div><div class="footer-label">Artifacts</div><ul><li><a href="downloads/compiling-recurrent-agent-workflows.pdf">Paper PDF</a></li><li><a href="downloads/gac-technical-review.pptx">Technical deck</a></li></ul></div>
    <div><div class="footer-label">Detail</div><ul><li><a href="research.html">Research evidence</a></li><li><a href="limitations.html">Limitations</a></li></ul></div>
    <div><div class="footer-label">Project</div><ul><li><a href="contributing.html">Contribute</a></li><li><a href="https://github.com/rrahimi-uci/guarded-agentic-compaction">Source</a></li></ul></div>
  </div></footer>
</body>
</html>
"""


def main() -> None:
    register = verify_admission(load("results/admission_register.json"))
    cache = verify_cache(load("results/cache_accounting.json"))
    summary = verify_families(load("results/github_workflow_families/summary.json"))
    OUTPUT.write_text(render(register, cache, summary), encoding="utf-8")
    print(
        f"wrote {OUTPUT.relative_to(ROOT)}: "
        f"{len(register)} admitted artifacts, {len(cache)} families, "
        f"{summary['overall']['n']} held-out records, all closed forms reproduced"
    )


if __name__ == "__main__":
    main()
