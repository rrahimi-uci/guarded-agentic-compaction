#!/usr/bin/env python3
"""Render benchmarks/explorer/index.html from the benchmark evidence artifacts.

The explorer is a browsable view of the same audit the paper reports, so it is generated
from paper/results/ rather than hand-written.  Screening, execution, measurement, and
gated-source rows carry different evidence, and the page has to keep them distinguishable:
a screened reference plan is not a compiler execution, and an inaccessible source gets no
imputed metric.  Totals are recomputed from the per-benchmark rows and the script fails
closed when they disagree with the recorded summary.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
OUTPUT = ROOT / "benchmarks" / "explorer" / "index.html"

MATRIX = "results/external_benchmarks/reference_analysis.json"
MULTIDOMAIN = "results/multidomain/preflight/validation.json"

# Upstream capitalisation, so a reader searching "tau2" or "SWE-bench" finds the row.
DISPLAY_NAMES = {
    "agentbench": "AgentBench",
    "api_bank": "API-Bank",
    "bfcl": "BFCL v4 — multi-turn base",
    "browsecomp": "BrowseComp",
    "gaia": "GAIA",
    "nestful": "NESTFUL",
    "swe_bench_verified": "SWE-bench Verified",
    "tau2": "τ²-bench",
    "toolbench": "ToolBench",
    "toolsandbox": "ToolSandbox",
}

DOMAIN_NAMES = {
    "vulnerability": "OSV / GitHub Advisory / NVD vulnerability records",
    "hmda": "HMDA public loan application register",
    "sec": "SEC filing facts",
}

STATUS_COPY = {
    "measured": "Compiler executed on this benchmark; a gate decision was produced.",
    "screened": "Reference plans were screened for compilable structure. No compiler ran.",
    "gated": "Upstream access denied. No task or compiler metric is imputed.",
    "preflight": "Real records validated and frozen, but the study has not been run.",
}


class VerificationError(SystemExit):
    """Raised when recomputed totals disagree with the recorded summary."""


def load(relative: str) -> dict:
    return json.loads((PAPER / relative).read_text(encoding="utf-8"))


def esc(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def humanize(value: str) -> str:
    return value.replace("_", " ")


def rows_from_matrix(matrix: dict) -> list[dict]:
    rows = []
    for key, entry in sorted(matrix["benchmarks"].items()):
        execution = entry.get("execution") or {}
        measured = entry.get("measured_compiler_results") or {}
        compiler_ran = bool(
            entry.get("compiler_executions")
            or execution.get("compiler_execution")
            or entry.get("status") == "measured"
        )
        gate = measured.get("default_gate_outcome") or execution.get("gate_outcome")
        rows.append(
            {
                "id": key,
                "name": DISPLAY_NAMES.get(key, key),
                "raw": entry.get("benchmark", key),
                "family": "External benchmark audit",
                "status": entry["status"],
                "substrate": entry.get("substrate"),
                "execution_status": entry.get("execution_status"),
                "evidence_stage": entry.get("evidence_stage"),
                "license": entry.get("license"),
                "scope": entry.get("benchmark_scope"),
                "reason": entry.get("reason"),
                "tasks": entry.get("tasks"),
                "actions": entry.get("total_actions"),
                "candidate_regions": entry.get("tasks_with_candidate_region"),
                "provider_calls": entry.get("provider_calls"),
                "compiler_ran": compiler_ran,
                "gate": gate,
                # Left as None when the artifact records no verdict. NESTFUL and GAIA do
                # not carry these fields, and rendering absence as "not licensed" would
                # invent a judgement the evidence file never made.
                "quality_licensed": entry.get("quality_claim_licensed"),
                "efficiency_licensed": entry.get("efficiency_claim_licensed"),
                "notes": entry.get("notes") or [],
                "source": entry.get("source_result"),
                "source_sha256": entry.get("source_result_sha256"),
                "revision": entry.get("source_revision"),
                "structure": {
                    label: entry[field]
                    for label, field in (
                        ("Read-like actions", "read_like_actions"),
                        ("Barrier actions", "barrier_actions"),
                        ("Unknown-effect actions", "unknown_actions"),
                        ("Recurrent candidate families", "recurrent_candidate_families"),
                        ("Longest read region", "maximum_read_region"),
                        ("Largest family support", "maximum_candidate_family_support"),
                        ("Tasks with reference actions", "tasks_with_reference_actions"),
                        ("Tasks with a barrier", "tasks_with_barrier"),
                        ("Tasks with unknown effects", "tasks_with_unknown"),
                    )
                    if entry.get(field) is not None
                },
                "effects": entry.get("effect_counts") or {},
                "blocks": entry.get("block_reason_counts") or {},
                "measured": measured,
                "execution": {
                    k: v
                    for k, v in execution.items()
                    if k not in {"schema", "result", "result_sha256", "compiler_execution"}
                },
                "credential": entry.get("credential_name"),
            }
        )
    return rows


def rows_from_multidomain(validation: dict) -> list[dict]:
    rows = []
    for domain in validation["domains"]:
        available = domain.get("available", False)
        rows.append(
            {
                "id": f"multidomain_{domain['domain']}",
                "name": DOMAIN_NAMES.get(domain["domain"], domain["domain"]),
                "raw": domain["domain"],
                "family": "Multidomain real-record source",
                "status": "preflight" if available else "gated",
                "substrate": "real_public_records" if available else None,
                "execution_status": "not_executed",
                "evidence_stage": "frozen_preflight" if available else "source_unavailable",
                "license": "public record redistribution terms per source manifest",
                "scope": (
                    f"{domain['cases']} validated cases across {domain['independent_groups']} "
                    "independent groups; protocol frozen before any provider call"
                    if available
                    else "pool could not be normalized from real records"
                ),
                "reason": (domain.get("errors") or [None])[0] if not available else None,
                "tasks": domain.get("cases"),
                "actions": None,
                "candidate_regions": None,
                # An unavailable pool reports nothing, matching how the gated external
                # source is handled; the study-level zero-provider-call fact is in notes.
                "provider_calls": 0 if available else None,
                "compiler_ran": False,
                "gate": None,
                "quality_licensed": False,
                "efficiency_licensed": False,
                "notes": [
                    "Study status is proposed_unrun with zero provider calls executed; "
                    "these rows are frozen inputs, not results."
                ],
                "source": "paper/results/multidomain/preflight/validation.json",
                "source_sha256": None,
                "revision": None,
                "structure": {
                    label: domain[field]
                    for label, field in (
                        ("Independent groups", "independent_groups"),
                        ("Exact-oracle passes", "exact_oracle_passes"),
                        ("Independent gold passes", "independent_gold_passes"),
                    )
                    if domain.get(field) is not None
                },
                "effects": {},
                "blocks": {},
                "measured": {},
                "execution": (
                    {"variable_path_fraction": round(domain["variable_path_fraction"], 4)}
                    if available
                    else {}
                ),
                "credential": None,
            }
        )
    return rows


def verify_totals(matrix: dict, rows: list[dict]) -> None:
    """Recompute the summary from the rows so the page cannot overstate the audit."""

    totals = matrix["totals"]
    external = [r for r in rows if r["family"] == "External benchmark audit"]
    screened = [r for r in external if r["status"] == "screened"]

    checks = {
        "named_benchmarks": (len(external), totals["named_benchmarks"]),
        "screened_sources": (len(screened), totals["screened_sources"]),
        "gated_sources": (
            len([r for r in external if r["status"] == "gated"]),
            totals["gated_sources"],
        ),
        "screened_tasks": (
            sum(r["tasks"] or 0 for r in screened),
            totals["screened_tasks"],
        ),
        "screened_reference_actions": (
            sum(r["actions"] or 0 for r in screened),
            totals["screened_reference_actions"],
        ),
        "screened_tasks_with_candidate_region": (
            sum(r["candidate_regions"] or 0 for r in screened),
            totals["screened_tasks_with_candidate_region"],
        ),
        "executed_external_paths": (
            len([r for r in external if r["execution_status"] == "executed"]),
            totals["executed_external_paths"],
        ),
        "provider_calls": (
            sum(r["provider_calls"] or 0 for r in external),
            totals["provider_calls"],
        ),
    }
    for label, (derived, recorded) in checks.items():
        if derived != recorded:
            raise VerificationError(
                f"{label}: rows give {derived}, recorded summary says {recorded}"
            )

    if matrix.get("secrets_serialized") is not False:
        raise VerificationError("benchmark matrix does not assert secrets_serialized=false")
    for row in rows:
        if row["status"] == "gated" and (row["actions"] or row["candidate_regions"]):
            raise VerificationError(f"{row['id']}: gated source carries imputed metrics")


def stat_tiles(matrix: dict, rows: list[dict]) -> str:
    totals = matrix["totals"]
    tiles = [
        (totals["named_benchmarks"], "named external benchmarks audited"),
        (totals["executed_external_paths"], "external paths actually executed"),
        (totals["measured_compiler_benchmarks"], "paths where the compiler itself ran"),
        (f"{totals['screened_tasks']:,}", "reference tasks screened for structure"),
        (f"{totals['screened_reference_actions']:,}", "reference actions screened"),
        (totals["gated_sources"], "source withheld upstream, nothing imputed"),
    ]
    cells = "".join(
        f'<div class="tile"><strong>{esc(value)}</strong><span>{esc(label)}</span></div>'
        for value, label in tiles
    )
    return f'<section class="tiles" aria-label="Audit summary">{cells}</section>'


def facet_options(rows: list[dict], key: str) -> list[str]:
    return sorted({str(r[key]) for r in rows if r.get(key)})


def render(matrix: dict, rows: list[dict]) -> str:
    payload = json.dumps(rows, separators=(",", ":"), sort_keys=True)
    boundary = matrix["claim_boundary"]
    boundary_items = "".join(
        f"<li><code>{esc(k)}</code> is <strong>{esc(str(v).lower())}</strong></li>"
        for k, v in sorted(boundary.items())
    )
    status_legend = "".join(
        f'<div class="legend-row"><span class="badge badge-{esc(k)}">{esc(k)}</span>'
        f"<p>{esc(v)}</p></div>"
        for k, v in STATUS_COPY.items()
    )

    def select(name: str, label: str, key: str) -> str:
        options = "".join(
            f'<option value="{esc(v)}">{esc(humanize(v))}</option>'
            for v in facet_options(rows, key)
        )
        return (
            f'<label class="control"><span>{esc(label)}</span>'
            f'<select id="{name}" data-facet="{esc(key)}">'
            f'<option value="">All</option>{options}</select></label>'
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Search and filter every benchmark used in the Guarded Agentic Compaction evaluation, with each row's evidence class, execution status, and claim boundary.">
<title>Benchmark explorer — Guarded Agentic Compaction</title>
<style>
:root {{
  --ink: #10242d; --ink-2: #173742; --paper: #f7f3eb; --paper-2: #eee8dc;
  --white: #fffdf8; --teal: #2a9d8f; --teal-light: #9ed9cf; --blue: #2f6b8a;
  --coral: #d06b4d; --gold: #b8862f; --muted: #64747a;
  --line: rgba(16,36,45,.16); --radius: 16px;
  color-scheme: light;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; color: var(--ink); background: var(--paper);
  font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 16px; line-height: 1.6;
}}
h1, h2, h3 {{ font-family: Georgia, "Times New Roman", serif; font-weight: 600; letter-spacing: -.03em; line-height: 1.1; }}
a {{ color: var(--blue); text-underline-offset: 3px; }}
a:hover {{ color: var(--coral); }}
code {{ font-family: "SFMono-Regular", Consolas, monospace; font-size: .86em; background: rgba(47,107,138,.09); padding: .1rem .35rem; border-radius: 5px; }}
.wrap {{ width: min(100% - 32px, 1180px); margin: 0 auto; }}
.skip {{ position: absolute; left: 16px; top: -80px; background: var(--coral); color: var(--white); padding: 10px 14px; z-index: 20; }}
.skip:focus {{ top: 12px; }}
header.masthead {{ padding: 54px 0 40px; color: var(--white); background: linear-gradient(135deg, var(--ink), #19434e); }}
.eyebrow {{ display: inline-flex; align-items: center; gap: 10px; margin: 0 0 14px; color: var(--teal-light); font-size: .72rem; font-weight: 800; letter-spacing: .16em; text-transform: uppercase; }}
.eyebrow::before {{ content: ""; width: 26px; height: 2px; background: currentColor; }}
header.masthead h1 {{ margin: 0; font-size: clamp(2.3rem, 5vw, 3.6rem); max-width: 900px; }}
header.masthead p {{ max-width: 760px; margin: 18px 0 0; color: rgba(255,253,248,.78); }}
.tiles {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 0; margin-top: 34px; border: 1px solid rgba(255,255,255,.18); border-radius: var(--radius); overflow: hidden; }}
.tile {{ padding: 16px 18px; border-right: 1px solid rgba(255,255,255,.14); }}
.tile:last-child {{ border-right: 0; }}
.tile strong {{ display: block; color: var(--teal-light); font: 600 1.7rem/1.1 Georgia, serif; }}
.tile span {{ display: block; margin-top: 5px; color: rgba(255,253,248,.72); font-size: .76rem; }}
main {{ padding: 40px 0 70px; }}
.controls {{ position: sticky; top: 0; z-index: 10; padding: 18px; margin-bottom: 26px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--white); box-shadow: 0 10px 30px rgba(16,36,45,.07); }}
.control-grid {{ display: grid; grid-template-columns: minmax(220px, 1.6fr) repeat(4, minmax(130px, 1fr)) auto; gap: 14px; align-items: end; }}
.control {{ display: grid; gap: 6px; }}
.control > span {{ color: var(--muted); font-size: .7rem; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; }}
input[type="search"], select {{ width: 100%; min-height: 42px; padding: 8px 12px; border: 1px solid var(--line); border-radius: 10px; background: var(--paper); color: var(--ink); font: inherit; font-size: .92rem; }}
input[type="search"]:focus-visible, select:focus-visible, button:focus-visible, summary:focus-visible {{ outline: 3px solid var(--teal); outline-offset: 2px; }}
button {{ min-height: 42px; padding: 9px 16px; border: 1px solid var(--line); border-radius: 999px; background: var(--paper); color: var(--ink); font: inherit; font-weight: 650; font-size: .88rem; cursor: pointer; }}
button:hover {{ background: var(--paper-2); }}
.status-line {{ display: flex; flex-wrap: wrap; gap: 10px; justify-content: space-between; align-items: baseline; margin-top: 14px; color: var(--muted); font-size: .85rem; }}
.sort-inline {{ display: inline-flex; align-items: center; gap: 8px; color: var(--muted); font-size: .8rem; font-weight: 650; }}
.sort-inline select {{ width: auto; min-height: 36px; padding: 5px 10px; font-size: .84rem; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 18px; }}
.card {{ display: flex; flex-direction: column; padding: 22px 24px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--white); box-shadow: 0 10px 28px rgba(16,36,45,.06); }}
.card-head {{ display: flex; gap: 12px; justify-content: space-between; align-items: start; }}
.card h3 {{ margin: 0 0 4px; font-size: 1.18rem; }}
.card-raw {{ color: var(--muted); font-size: .74rem; font-family: "SFMono-Regular", Consolas, monospace; }}
.badge {{ display: inline-block; padding: 3px 11px; border-radius: 999px; font-size: .7rem; font-weight: 700; letter-spacing: .04em; white-space: nowrap; }}
.badge-measured {{ color: #14584f; background: rgba(42,157,143,.18); }}
.badge-screened {{ color: #234f66; background: rgba(47,107,138,.15); }}
.badge-gated {{ color: #8a3a1c; background: rgba(208,107,77,.18); }}
.badge-preflight {{ color: #6d5115; background: rgba(214,168,75,.22); }}
.scope {{ margin: 12px 0 0; color: #37505a; font-size: .89rem; }}
.metrics {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 1px; margin: 16px 0 0; background: var(--line); border: 1px solid var(--line); border-radius: 11px; overflow: hidden; }}
.metric {{ padding: 9px 12px; background: var(--white); }}
.metric dt {{ color: var(--muted); font-size: .68rem; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; }}
.metric dd {{ margin: 2px 0 0; font-variant-numeric: tabular-nums; font-weight: 600; font-size: .98rem; }}
.flags {{ display: flex; flex-wrap: wrap; gap: 7px; margin-top: 14px; }}
.flag {{ padding: 3px 10px; border: 1px solid var(--line); border-radius: 999px; font-size: .72rem; color: var(--muted); }}
.flag-no {{ border-color: rgba(208,107,77,.4); color: #8a3a1c; }}
.flag-yes {{ border-color: rgba(42,157,143,.45); color: #14584f; }}
details {{ margin-top: 16px; border-top: 1px solid var(--line); padding-top: 12px; }}
summary {{ cursor: pointer; color: var(--blue); font-size: .84rem; font-weight: 650; }}
.detail-block {{ margin-top: 12px; }}
.detail-block h4 {{ margin: 0 0 6px; color: var(--muted); font-size: .68rem; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; }}
.kv {{ margin: 0; font-size: .84rem; }}
.kv div {{ display: flex; justify-content: space-between; gap: 12px; padding: 4px 0; border-bottom: 1px dotted var(--line); }}
.kv dt {{ color: #37505a; }}
.kv dd {{ margin: 0; font-variant-numeric: tabular-nums; font-weight: 600; }}
.notes {{ margin: 8px 0 0; padding-left: 18px; color: var(--muted); font-size: .82rem; }}
.prov {{ margin-top: 10px; color: var(--muted); font-size: .74rem; word-break: break-all; }}
.empty {{ padding: 40px; border: 1px dashed var(--line); border-radius: var(--radius); text-align: center; color: var(--muted); }}
.panel {{ margin-top: 44px; padding: 26px 28px; border-left: 4px solid var(--coral); border-radius: 0 var(--radius) var(--radius) 0; background: var(--white); }}
.panel h2 {{ margin: 0 0 10px; font-size: 1.5rem; }}
.panel ul {{ margin: 10px 0 0; padding-left: 20px; color: #37505a; font-size: .9rem; }}
.legend {{ margin-top: 28px; padding: 24px 26px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--white); }}
.legend h2 {{ margin: 0 0 14px; font-size: 1.35rem; }}
.legend-row {{ display: grid; grid-template-columns: 110px 1fr; gap: 14px; align-items: start; padding: 7px 0; }}
.legend-row p {{ margin: 0; color: #37505a; font-size: .88rem; }}
footer {{ padding: 34px 0; color: rgba(255,253,248,.7); background: #0b1c22; font-size: .84rem; }}
footer a {{ color: rgba(255,253,248,.78); }}
@media (max-width: 1000px) {{
  .tiles {{ grid-template-columns: repeat(3, 1fr); }}
  .tile:nth-child(3) {{ border-right: 0; }}
  .control-grid {{ grid-template-columns: 1fr 1fr; }}
}}
@media (max-width: 620px) {{
  .tiles {{ grid-template-columns: 1fr 1fr; }}
  .control-grid {{ grid-template-columns: 1fr; }}
  .controls {{ position: static; }}
  .legend-row {{ grid-template-columns: 1fr; }}
}}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; }} }}
</style>
</head>
<body>
<a class="skip" href="#results">Skip to results</a>
<header class="masthead"><div class="wrap">
  <p class="eyebrow">Guarded Agentic Compaction</p>
  <h1>Every benchmark in the evaluation, and what each one can prove.</h1>
  <p>Ten named external benchmarks plus the frozen multidomain record sources. The
  evaluation deliberately does not average them: a screened reference plan, an executed
  simulator, a real compiler run, and a source we were denied access to support different
  claims, so each row keeps its own substrate, denominator, execution status, and
  boundary.</p>
  {stat_tiles(matrix, rows)}
</div></header>

<main><div class="wrap">
  <form class="controls" id="controls" role="search" aria-label="Filter benchmarks" onsubmit="return false">
    <div class="control-grid">
      <label class="control"><span>Search</span>
        <input type="search" id="q" placeholder="NESTFUL, simulator, RETIRE&hellip;"
               autocomplete="off"></label>
      {select("f-family", "Family", "family")}
      {select("f-status", "Evidence status", "status")}
      {select("f-substrate", "Substrate", "substrate")}
      {select("f-exec", "Execution", "execution_status")}
      <button type="button" id="reset">Clear</button>
    </div>
    <div class="status-line">
      <span id="count" role="status" aria-live="polite"></span>
      <label class="sort-inline">Sort
        <select id="sort" aria-label="Sort results">
          <option value="name">by name</option>
          <option value="tasks">by tasks (high to low)</option>
          <option value="actions">by reference actions (high to low)</option>
          <option value="candidate_regions">by candidate regions (high to low)</option>
          <option value="status">by evidence status</option>
        </select>
      </label>
    </div>
  </form>

  <section id="results" class="grid" aria-label="Benchmarks"></section>
  <p class="empty" id="empty" hidden>No benchmark matches those filters. <button type="button" id="reset2">Clear filters</button></p>

  <section class="panel" aria-labelledby="boundary-h">
    <h2 id="boundary-h">What this audit does not claim</h2>
    <p>These flags are recorded in the evidence file itself and are fail-closed, so the
    matrix cannot quietly upgrade weaker evidence:</p>
    <ul>{boundary_items}</ul>
  </section>

  <section class="legend" aria-labelledby="legend-h">
    <h2 id="legend-h">Reading the evidence status</h2>
    {status_legend}
  </section>
</div></main>

<footer><div class="wrap">
  <p>Generated from <code>paper/{esc(MATRIX)}</code> and <code>paper/{esc(MULTIDOMAIN)}</code>
  by <code>scripts/build_benchmark_explorer.py</code>, which recomputes every headline total
  from the per-benchmark rows and fails closed if they disagree.</p>
  <p><a href="../../site/method.html">Method and certificates</a> &middot;
  <a href="../README.md">Benchmark suite README</a> &middot;
  <a href="https://github.com/rrahimi-uci/guarded-agentic-compaction">Source</a></p>
</div></footer>

<script type="application/json" id="data">{payload}</script>
<script>
(function () {{
  "use strict";
  const rows = JSON.parse(document.getElementById("data").textContent);
  const results = document.getElementById("results");
  const empty = document.getElementById("empty");
  const count = document.getElementById("count");
  const q = document.getElementById("q");
  const sort = document.getElementById("sort");
  const facets = Array.from(document.querySelectorAll("select[data-facet]"));

  const num = (v) => (v === null || v === undefined ? "\\u2014" : v.toLocaleString("en-US"));
  const esc = (v) => String(v).replace(/[&<>"]/g, (c) =>
    ({{ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }})[c]);
  const words = (v) => String(v || "").replace(/_/g, " ");

  // One flat haystack per row so a single query can reach names, scope, licence,
  // gate outcomes and notes without the caller knowing the schema.
  rows.forEach((r) => {{
    r._hay = [r.name, r.raw, r.family, r.status, r.substrate, r.execution_status,
              r.evidence_stage, r.license, r.scope, r.reason, r.gate,
              (r.notes || []).join(" "), Object.keys(r.effects || {{}}).join(" "),
              Object.keys(r.blocks || {{}}).join(" ")]
             .filter(Boolean).join(" ").toLowerCase();
  }});

  // Three-state on purpose: null means the evidence file records no verdict, which is
  // not the same as recording "no". Absent verdicts render nothing at all.
  function flag(state, label) {{
    if (state === null || state === undefined) return "";
    return '<span class="flag ' + (state ? "flag-yes" : "flag-no") + '">' +
      (state ? "\\u2713 " : "\\u2717 ") + esc(label) + "</span>";
  }}

  function kv(title, obj) {{
    const keys = Object.keys(obj || {{}});
    if (!keys.length) return "";
    const body = keys.sort().map((k) =>
      "<div><dt>" + esc(words(k)) + "</dt><dd>" +
      (typeof obj[k] === "number" ? num(obj[k]) : esc(words(obj[k]))) + "</dd></div>").join("");
    return '<div class="detail-block"><h4>' + esc(title) + '</h4><dl class="kv">' + body + "</dl></div>";
  }}

  function card(r) {{
    const cells = [
      ["Tasks", r.tasks],
      ["Reference actions", r.actions],
      ["Tasks w/ candidate region", r.candidate_regions],
      ["Live provider calls", r.provider_calls],
    ];
    // A gated source has no metrics because none are imputed for it; a grid of dashes
    // would imply we measured zero rather than that we were never given the bytes.
    const anyMetric = cells.some(([, v]) => v !== null && v !== undefined);
    const metrics = !anyMetric ? "" : '<dl class="metrics">' + cells.map(([k, v]) =>
      "<div class=\\"metric\\"><dt>" + k + "</dt><dd>" + num(v) + "</dd></div>").join("") + "</dl>";

    const notes = (r.notes || []).length
      ? '<ul class="notes">' + r.notes.map((n) => "<li>" + esc(n) + "</li>").join("") + "</ul>"
      : "";

    const provenance = [
      r.source ? "Source: <code>" + esc(r.source) + "</code>" : "",
      r.source_sha256 ? "sha256 " + esc(r.source_sha256.slice(0, 16)) + "\\u2026" : "",
      r.revision ? "revision " + esc(r.revision.slice(0, 10)) : "",
    ].filter(Boolean).join(" &middot; ");

    return '<article class="card">' +
      '<div class="card-head"><div><h3>' + esc(r.name) + "</h3>" +
      '<div class="card-raw">' + esc(r.raw) + "</div></div>" +
      '<span class="badge badge-' + esc(r.status) + '">' + esc(r.status) + "</span></div>" +
      (r.scope ? '<p class="scope">' + esc(r.scope) + "</p>" : "") +
      (r.reason ? '<p class="scope"><strong>Blocked:</strong> ' + esc(r.reason) + "</p>" : "") +
      metrics +
      '<div class="flags">' +
        flag(r.compiler_ran, "compiler executed") +
        flag(r.quality_licensed, "quality claim licensed") +
        flag(r.efficiency_licensed, "efficiency claim licensed") +
        (r.gate ? '<span class="flag">gate: ' + esc(r.gate) + "</span>" : "") +
        (r.substrate ? '<span class="flag">' + esc(words(r.substrate)) + "</span>" : "") +
      "</div>" +
      "<details><summary>Evidence detail</summary>" +
        kv("Structure", r.structure) +
        kv("Effect classes", r.effects) +
        kv("Block reasons", r.blocks) +
        kv("Measured compiler result", r.measured) +
        kv("Execution record", r.execution) +
        '<div class="detail-block"><h4>Provenance</h4>' +
          '<p class="prov">' + (provenance || "\\u2014") +
          (r.license ? "<br>Licence: " + esc(r.license) : "") +
          (r.credential ? "<br>Credential required: <code>" + esc(r.credential) + "</code>" : "") +
          "</p>" + notes + "</div>" +
      "</details></article>";
  }}

  function apply() {{
    const needle = q.value.trim().toLowerCase();
    const active = facets.filter((s) => s.value);
    let shown = rows.filter((r) => {{
      if (needle && !r._hay.includes(needle)) return false;
      return active.every((s) => String(r[s.dataset.facet]) === s.value);
    }});

    const mode = sort.value;
    shown.sort((a, b) => {{
      if (mode === "name") return a.name.localeCompare(b.name);
      if (mode === "status") return String(a.status).localeCompare(String(b.status)) ||
        a.name.localeCompare(b.name);
      return (b[mode] || 0) - (a[mode] || 0) || a.name.localeCompare(b.name);
    }});

    results.innerHTML = shown.map(card).join("");
    empty.hidden = shown.length > 0;
    // Deliberately not a pooled denominator: these rows sit on different substrates and
    // the evaluation does not average them, so the record count is labelled as a sum of
    // per-row counts rather than presented as one benchmark size.
    const records = shown.reduce((sum, r) => sum + (r.tasks || 0), 0);
    count.textContent = shown.length + " of " + rows.length + " benchmarks" +
      (records ? " \\u00b7 " + records.toLocaleString("en-US") +
        " records across mixed substrates (not a pooled denominator)" : "");
  }}

  function reset() {{
    q.value = "";
    facets.forEach((s) => {{ s.value = ""; }});
    sort.value = "name";
    apply();
    q.focus();
  }}

  q.addEventListener("input", apply);
  sort.addEventListener("change", apply);
  facets.forEach((s) => s.addEventListener("change", apply));
  document.getElementById("reset").addEventListener("click", reset);
  document.getElementById("reset2").addEventListener("click", reset);
  apply();
}})();
</script>
</body>
</html>
"""


def main() -> None:
    matrix = load(MATRIX)
    if matrix.get("schema") != "agent-compaction-external-benchmark-matrix/v1":
        raise VerificationError("unexpected external benchmark matrix schema")
    validation = load(MULTIDOMAIN)
    if validation.get("schema") != "agent-compaction-multidomain-validation/v1":
        raise VerificationError("unexpected multidomain validation schema")

    rows = rows_from_matrix(matrix) + rows_from_multidomain(validation)
    verify_totals(matrix, rows)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(matrix, rows), encoding="utf-8")
    print(
        f"wrote {OUTPUT.relative_to(ROOT)}: {len(rows)} rows "
        f"({len([r for r in rows if r['family'] == 'External benchmark audit'])} external, "
        f"{len(rows) - len([r for r in rows if r['family'] == 'External benchmark audit'])} "
        "multidomain), all recomputed totals agree"
    )


if __name__ == "__main__":
    main()
