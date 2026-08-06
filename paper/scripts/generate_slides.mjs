#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(SCRIPT_DIR, "../..");
const PAPER = path.join(ROOT, "paper");

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith("--")) throw new Error(`unexpected argument: ${token}`);
    const key = token.slice(2);
    const value = argv[i + 1];
    if (!value || value.startsWith("--")) throw new Error(`missing value for --${key}`);
    args[key] = value;
    i += 1;
  }
  return args;
}

function requireValue(value, message) {
  if (!value) throw new Error(message);
  return value;
}

function assertEqual(actual, expected, label) {
  if (actual !== expected) {
    throw new Error(`${label}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
  }
}

function assertClose(actual, expected, label, tolerance = 1e-9) {
  if (!Number.isFinite(actual) || Math.abs(actual - expected) > tolerance) {
    throw new Error(`${label}: expected ${expected}, got ${actual}`);
  }
}

async function readJson(filePath) {
  return JSON.parse(await fs.readFile(filePath, "utf8"));
}

async function sha256(filePath) {
  return crypto.createHash("sha256").update(await fs.readFile(filePath)).digest("hex");
}

async function loadArtifactTool(artifactWorkspace) {
  const require = createRequire(import.meta.url);
  const resolved = require.resolve("@oai/artifact-tool", { paths: [artifactWorkspace] });
  return import(pathToFileURL(resolved).href);
}

function allShapes(presentation) {
  return presentation.slides.items.flatMap((slide) => slide.shapes.items);
}

function replaceUnique(presentation, original, replacement, label = original) {
  const matches = allShapes(presentation).filter(
    (shape) => (shape.text?.toString?.() ?? "") === original,
  );
  if (matches.length !== 1) {
    throw new Error(`${label}: expected one exact text match, found ${matches.length}`);
  }
  matches[0].text.set(replacement);
}

function replaceStartingWith(presentation, prefix, replacement, label = prefix) {
  const matches = allShapes(presentation).filter(
    (shape) => (shape.text?.toString?.() ?? "").startsWith(prefix),
  );
  if (matches.length !== 1) {
    throw new Error(`${label}: expected one prefix text match, found ${matches.length}`);
  }
  matches[0].text.set(replacement);
}

function setShapeText(slide, index, text) {
  const shape = slide.shapes.items[index];
  if (!shape?.text) throw new Error(`slide ${slide.index}: missing text shape ${index}`);
  shape.text.set(text);
}

function setTableCell(table, row, column, value) {
  const cell = table.getCell(row, column);
  if (!cell) throw new Error(`missing table cell ${row},${column}`);
  table.setCellValue(row, column, value);
}

function renumberPages(presentation) {
  for (let index = 1; index < presentation.slides.count; index += 1) {
    const slide = presentation.slides.getItem(index);
    const candidates = slide.shapes.items.filter((shape) => {
      const frame = shape.frame;
      const text = shape.text?.toString?.() ?? "";
      return frame && frame.top > 650 && frame.left > 1000 && /^\d+$/.test(text.trim());
    });
    if (candidates.length !== 1) {
      throw new Error(`slide ${index + 1}: expected one footer page marker, found ${candidates.length}`);
    }
    candidates[0].text.set(String(index + 1));
  }
}

function validateEvidence(gcs, replay, optimizer, external, families, admission) {
  assertEqual(admission.schema, "agent-compaction-admission-register/v1", "admission register schema");
  assertClose(admission.registered_alpha, 0.05, "registered selective-risk target");
  // The decks quote a per-artifact risk level, so bind the two facts they assert: the
  // three primary families sit at the registered alpha, and the GCS artifact does not.
  const byStudy = new Map(admission.artifacts.map((row) => [row.study, row]));
  for (const study of ["Expanded replication (issue type)", "PR-outcome audit", "Backlog-attention routing"]) {
    const row = requireValue(byStudy.get(study), `admission register missing ${study}`);
    assertClose(row.alpha, 0.05, `${study} alpha`);
    assertEqual(row.meets_registered_alpha, true, `${study} meets registered alpha`);
  }
  const composite = requireValue(
    byStudy.get("Guarded composite synthesis"),
    "admission register missing the GCS artifact",
  );
  assertClose(composite.alpha, 0.1, "GCS artifact alpha");
  assertEqual(composite.meets_registered_alpha, false, "GCS artifact fails the registered alpha");
  assertEqual(composite.n_accepted, 88, "GCS artifact admitted calibration groups");
  assertEqual(composite.n_calibration_groups, 92, "GCS artifact calibration groups");
  assertEqual(gcs.schema, "agent-compaction-gcs-live-study/v1", "GCS schema");
  assertEqual(gcs.run.provider_backed, true, "GCS provider-backed flag");
  assertEqual(gcs.run.real_public_records, true, "GCS real-record flag");
  assertEqual(gcs.run.openai_api_key_used, true, "GCS provider credential usage flag");
  assertEqual(gcs.run.secrets_serialized, false, "GCS secret serialization flag");
  assertEqual(gcs.macro_vs_gcs.n_pairs, 12, "GCS paired sample size");
  assertClose(gcs.macro_vs_gcs.quality.overall.gcs_rate, 1, "GCS exact quality");
  assertClose(gcs.macro_vs_gcs.quality.overall.macro_rate, 1, "macro exact quality");
  const expected = {
    requests: 0.5,
    tool_calls: 0,
    total_tokens: 0.3889982502187227,
    wall_latency_ms: 0.40031515830575515,
    estimated_cost_usd: 0.3227115951015347,
  };
  for (const [metric, reduction] of Object.entries(expected)) {
    assertClose(
      gcs.macro_vs_gcs.metrics[metric].aggregate_reduction,
      reduction,
      `GCS ${metric} reduction`,
    );
  }
  assertEqual(replay.schema, "agent-compaction-gcs-provider-free-validation/v1", "GCS replay schema");
  assertEqual(replay.provider_calls_executed, 0, "GCS replay provider calls");
  assertEqual(replay.replay.attempted, 132, "GCS replay attempts");
  assertEqual(replay.replay.dispatched, 124, "GCS replay dispatches");
  assertEqual(replay.replay.fallback, 8, "GCS replay fallbacks");
  assertEqual(replay.replay.exact_projected_matches, 124, "GCS replay exact projections");
  assertEqual(replay.replay.projection_failures.length, 0, "GCS replay projection failures");
  assertEqual(optimizer.schema, "agent-compaction-optimizer-head-to-head/v1", "optimizer schema");
  assertEqual(optimizer.run.provider_backed, true, "optimizer provider-backed flag");
  assertEqual(optimizer.run.real_public_records, true, "optimizer real-record flag");
  assertEqual(optimizer.run.secrets_serialized, false, "optimizer secret serialization flag");
  assertEqual(optimizer.optimization.gepa_result.improved, false, "GEPA retained seed");
  assertEqual(optimizer.optimization.gepa_result.metric_calls, 14, "GEPA task metric calls");
  assertEqual(optimizer.optimization.accounting.combined_provider_requests, 59, "GEPA optimization requests");
  assertEqual(optimizer.preflight.provider_free_parity.exact_projection_matches, 12, "manual/GCS parity preflight");
  for (const condition of ["baseline", "gepa", "gcs", "gcs_gepa", "manual_pre_model"]) {
    assertEqual(optimizer.aggregate[condition].factuality_exact_rate, 1, `${condition} exact rate`);
    assertEqual(optimizer.aggregate[condition].n, 6, `${condition} deployment cases`);
  }
  assertEqual(external.schema, "agent-compaction-external-benchmark-matrix/v1", "external matrix schema");
  assertEqual(external.totals.named_benchmarks, 10, "external benchmark families");
  assertEqual(external.totals.measured_compiler_benchmarks, 2, "compiler benchmark paths");
  assertEqual(external.totals.executed_external_paths, 5, "executed external paths");
  assertEqual(external.totals.live_provider_benchmarks, 3, "live-provider external paths");
  assertEqual(external.totals.screened_tasks, 5419, "screened external tasks");
  assertEqual(external.totals.screened_reference_actions, 17836, "screened reference actions");
  assertEqual(external.benchmarks.api_bank.execution.gate_outcome, "RETIRE", "API-Bank gate");
  assertEqual(external.benchmarks.api_bank.execution.held_out_passed, 0, "API-Bank held-out passes");
  assertEqual(external.benchmarks.api_bank.execution.held_out_abstained, 2, "API-Bank held-out abstentions");
  assertEqual(external.benchmarks.api_bank.execution.held_out_wrong, 0, "API-Bank held-out wrong");
  assertEqual(external.benchmarks.tau2.execution.passed, 0, "tau bounded passes");
  assertEqual(external.benchmarks.browsecomp.execution.correct, 1, "BrowseComp bounded correct");
  assertEqual(families.schema, "agent-compaction-github-workflow-family-summary/v1", "workflow-family schema");
  assertEqual(families.simulated, false, "workflow-family simulation flag");
  assertEqual(families.overall.n, 90, "workflow-family held-out cases");
  assertEqual(families.overall.baseline_exact, 89, "workflow-family baseline exact");
  assertEqual(families.overall.compiled_exact, 90, "workflow-family compiled exact");
  assertEqual(families.overall.manual_exact, 90, "workflow-family manual exact");
  const familyReductions = {
    requests: 0.6657381615598885,
    tool_calls: 0.4423791821561338,
    total_tokens: 0.630649830153015,
    wall_latency_ms: 0.6421234029412591,
    estimated_cost_usd: 0.5867086898399436,
  };
  for (const [metric, reduction] of Object.entries(familyReductions)) {
    assertClose(families.overall[metric].reduction, reduction, `workflow-family ${metric} reduction`);
  }
}

function editWorkflowFamilySlide(slide, families, mode) {
  const seminar = mode === "seminar";
  setShapeText(slide, 2, seminar
    ? "RESULTS  ·  RQ6  ·  3 REAL WORKFLOW FAMILIES"
    : "RESULT 2  ·  RQ6  ·  WORKFLOW-FAMILY TRANSFER");
  setShapeText(slide, 3, "Efficiency transfers; manual programs remain the runtime baseline");
  setShapeText(
    slide,
    4,
    seminar
      ? "Three distinct decisions and tool vocabularies use 132 balanced discovery records and 30 disjoint held-out records each; all 90 held-out records are pairwise disjoint.\nCompiled programs preserve 90/90 exact outcomes versus 89/90 baseline (exact McNemar p=1) while cutting requests 66.6%, tokens 63.1%, observed latency 64.2%, and estimated cost 58.7% in aggregate.\nAll three artifacts are admitted at the registered α=.05; with no compiled-only failure the pooled discordance bound is 3.3%.\nHand-written programs also reach 90/90; automatic discovery and lifecycle—not runtime dominance—are the contribution."
      : "Issue-type routing, PR-outcome audit, and backlog-attention routing use distinct tools and exact graders over one pinned public snapshot, with all 90 held-out records pairwise disjoint.\nCompiled programs reach 90/90 exact outcomes versus 89/90 baseline (exact McNemar p=1; pooled compiled-only discordance bound 3.3%). Weighted reductions: requests 66.6%, visible interfaces 44.2%, tokens 63.1%, observed latency 64.2%, and cost 58.7%.\nAll three artifacts are calibrated at the registered α=.05 over 92 zero-violation groups.\nManual programs also reach 90/90, so the learned result is transfer and automation—not runtime superiority.",
  );
  setShapeText(
    slide,
    6,
    "The two new families compile verified three-read pre-model programs; the original issue family retains its conservative two-read prefix. Both newer families are cache-cold in every arm, so part of the 32.0–75.3% cost range is prompt-cache warmth rather than compiled depth; provider-side break-even is 411, 182, and 181 episodes against 132 paid discovery episodes each. The study changes decision and tools, but not repository or time: cross-repository and time-forward transfer remain open.",
  );
  const chart = slide.charts.items[0];
  if (!chart || chart.series.length !== 1) {
    throw new Error(`${mode} workflow-family slide: expected inherited one-series chart`);
  }
  const tokenReductions = families.families.map((row) => Number((100 * row.reductions.total_tokens).toFixed(1)));
  const categories = ["Issue type", "PR outcome", "Backlog attention"];
  chart.title = "Token reduction by workflow family";
  chart.categories = categories;
  chart.series.getItemAt(0).name = "Token reduction (%)";
  chart.series.getItemAt(0).categories = categories;
  chart.series.getItemAt(0).values = tokenReductions;
  chart.yAxis.min = 0;
  chart.yAxis.max = 100;
  chart.yAxis.numberFormatCode = "0\\%";
  if (seminar) {
    setShapeText(slide, 7, "90 HELD-OUT PUBLIC RECORDS — LIVE PROVIDER — NO SIMULATION");
    const metrics = [
      [9, "3"], [10, "workflow families"],
      [12, "90 / 90"], [13, "compiled / manual exact"],
      [15, "89 / 90"], [16, "baseline exact"],
      [18, "−66.6%"], [19, "provider requests"],
      [21, "−63.1%"], [22, "total tokens"],
      [24, "−64.2%"], [25, "observed latency"],
      [27, "−58.7%"], [28, "estimated cost"],
    ];
    for (const [index, value] of metrics) setShapeText(slide, index, value);
  } else {
    const metrics = [
      [8, "89 → 90 / 90"], [9, "baseline → compiled exact"],
      [11, "−66.6 / −63.1%"], [12, "requests / total tokens"],
      [14, "−64.2 / −58.7%"], [15, "latency / estimated cost"],
      [17, "90 / 90"], [18, "manual exact; no runtime dominance"],
    ];
    for (const [index, value] of metrics) setShapeText(slide, index, value);
  }
}

function metricRows(optimizer) {
  const labels = [
    ["baseline", "Unchanged"],
    ["gepa", "GEPA · seed"],
    ["gcs", "GCS"],
    ["gcs_gepa", "GCS + seed"],
    ["manual_pre_model", "Manual pre-model"],
  ];
  return [
    ["Condition", "Requests", "Interfaces", "Exact"],
    ...labels.map(([key, label]) => {
      const aggregate = optimizer.aggregate[key];
      return [
        label,
        (aggregate.provider_requests / aggregate.n).toFixed(1),
        (optimizer.deployment_results
          .filter((row) => row.condition === key)
          .reduce((sum, row) => sum + row.metrics.tool_calls, 0) / aggregate.n).toFixed(1),
        `${Math.round(aggregate.factuality_exact_rate * aggregate.n)}/${aggregate.n}`,
      ];
    }),
  ];
}

function editGcsSlide(slide, rows, mode) {
  const seminar = mode === "seminar";
  setShapeText(slide, 2, seminar
    ? "RESULTS  ·  FAIR PLACEMENT + BOUNDED GEPA  ·  REAL-PROVIDER STUDY"
    : "COMPARATORS  ·  FAIR PRE-MODEL PLACEMENT + GEPA");
  setShapeText(slide, 3, "Fair placement ties GCS; bounded GEPA retains its seed");
  setShapeText(
    slide,
    4,
    seminar
      ? "All five arms pass 6/6. GCS and an independent manual pre-model program tie at one request, one interface, and identical input tokens; GEPA leaves the four-request workflow unchanged."
      : "All five arms pass 6/6. GCS ties the fair manual program structurally; GEPA retains its seed and leaves requests unchanged.",
  );
  setShapeText(slide, 5, "6 FRESH HELD-OUT PUBLIC ISSUES — OPTIMIZATION COST EXCLUDED FROM DEPLOYMENT");
  setShapeText(
    slide,
    seminar ? 7 : 6,
    seminar
      ? "Real OpenAI Agents SDK executions over pinned public records. Disjoint 4/2/6 optimization train/validation/test splits were frozen before provider outcomes; condition order is balanced."
      : "Live provider calls on disjoint 4/2/6 splits frozen before optimization. The question category was unavailable after strict prior-cohort exclusion.",
  );
  setShapeText(slide, seminar ? 11 : 10, "What the fair test resolves…");
  setShapeText(
    slide,
    seminar ? 12 : 11,
    "manual placement can remove the same turns\nGCS value shifts to discovery + admission\nGEPA does not improve this bounded run",
  );
  setShapeText(slide, seminar ? 16 : 15, "What remains unresolved…");
  setShapeText(
    slide,
    seminar ? 17 : 16,
    "manual engineering and review effort\nAWO · Agent JIT · EvoC2F execution\nmultiple families and time-forward drift",
  );
  if (seminar) {
    setShapeText(slide, 19, "MECHANISM, EVIDENCE, AND BOUNDARY");
    setShapeText(
      slide,
      20,
      "The fair manual program closes the earlier placement confound: GCS and manual execution tie on requests, interfaces, input tokens, and exact quality. Official GEPA 0.1.4 makes 14 real task evaluations and three reflections, but retains its seed. Its 59-request, 63,954-token optimization overhead is reported separately. Risk scope: the GCS artifact here is calibrated at α=.10 (88/92 groups admitted, bound 0.052) and would retire at the registered α=.05, so this is a 10%-selective-risk result. This six-case result supports automatic guarded specialization—not runtime dominance or general GEPA failure.",
    );
  } else {
    setShapeText(
      slide,
      18,
      "Fair placement removes the confound: GCS and manual execution tie structurally at 6/6 exact quality. GEPA retains its seed after 14 task evaluations; 59 optimization requests are accounted separately. The GCS artifact is calibrated at α=.10 (88/92, bound 0.052) and would retire at the registered α=.05. One family, six held-out cases.",
    );
  }
  const table = slide.tables.items[0];
  if (!table || table.rowCount !== 6 || table.columnCount !== 4) {
    throw new Error(`${mode} GCS slide: expected inherited 6x4 comparator table`);
  }
  table.setValues(rows);
}

function updateSeminar(presentation, rows, families) {
  const cover = presentation.slides.getItem(0);
  setShapeText(cover, 5, "Guarded agentic compaction. Traces establish recurrence, not admissibility. We specify the evidence a compiler needs, the barriers it must respect, and the limits its evidence retains.");
  setShapeText(cover, 7, "Real workflows");
  setShapeText(cover, 8, "3 families\n90 held-out records");
  setShapeText(cover, 10, "Live provider calls on a\npinned public snapshot");
  replaceUnique(
    presentation,
    "On an unseen real-record workload, how does a learned compiled prefix trade factual quality against requests, tokens, latency, and cost — relative to an unchanged agent and a hand-written composite tool?",
    "Across distinct real-record workflow families, do guarded programs preserve exact outcomes while reducing requests, tokens, latency, and cost—and how do they compare with fair manual programs?",
  );
  replaceUnique(
    presentation,
    "A trace-to-program formulation combining typed value provenance, effect-aware barriers, a closed synthesis language, empirical contracts, and runtime fallback\nA dispatch protocol whose score is frozen before calibration and whose fixed threshold grid receives a simultaneous one-sided exact binomial bound\nA real-provider, real-public-record study in which the agent chooses tool order and quality is graded independently of execution conformance\nAn external NESTFUL study reporting provenance success, synthesis abstention, and a useful negative result\nA framework-neutral transformation portfolio over measured actions only",
    "A trace-to-program formulation combining typed value provenance, effect-aware barriers, a closed synthesis language, empirical contracts, and runtime fallback\nA dispatch protocol whose score is frozen before calibration and whose fixed threshold grid receives a simultaneous one-sided exact binomial bound\nA 90-case real-provider study spanning three decisions, tool vocabularies, and exact graders\nAn identifier-aware contract refinement derived from an archived failed pilot\nNESTFUL and API-Bank refusal evidence plus a supplementary interoperability ledger",
  );
  replaceUnique(
    presentation,
    "Defined in section 3.4. Consumes paired measurements for arbitrary named actions. Cannot weaken compiler admission, and cannot turn an unevaluated macro into deployable code.",
    "Consumes paired evidence for named actions and cannot weaken compiler admission. GCS is narrower: it packages one admitted read program behind a bounded, continuation-pinned task projection.",
  );
  replaceUnique(
    presentation,
    "Bounded registry lookup at the entry boundary. Guard → gate → stage → interpret → verify → commit, with a permission facade re-checking effects at execution time.",
    "Bounded entry lookup. Ordinary GRC runs guard → gate → stage → interpret → verify → commit; eligible GCS artifacts may verify and project before the first provider request.",
  );
  replaceUnique(
    presentation,
    "Four GitHub protocols on a pinned 12.7 MB Apache-2.0 snapshot",
    "Three primary GitHub workflow families plus scoped ablations on a pinned snapshot",
  );

  const familySlide = presentation.slides.getItem(16).duplicate();
  familySlide.setIndex(17);
  editWorkflowFamilySlide(familySlide, families, "seminar");

  const macroSlide = presentation.slides.getItem(21);
  setShapeText(macroSlide, 3, "Manual composition is the stronger pre-GCS fixed-workflow baseline");
  setShapeText(
    macroSlide,
    4,
    "Against partial GRC, the hand-written composite matches exact quality and request savings while using one interface and fewer tokens. Once prefix reuse is priced the margin narrows: 30.9% fewer tokens but only 8.0% lower cost, because fusing three reads destroys the cached prefix (0.0% cache reads against 27.8% compiled). That negative result motivates interface-level synthesis rather than weakening admission.",
  );
  const gcsSlide = macroSlide.duplicate();
  gcsSlide.setIndex(22);
  editGcsSlide(gcsSlide, rows, "seminar");

  replaceStartingWith(
    presentation,
    "Also: discovery is not free",
    "Also: discovery is not free (132 episodes cost 528 provider requests, 533,293 tokens, and about $0.096), and provider-side break-even runs 181–411 episodes; part of the reported 32.0–75.3% cost range is prompt-cache warmth rather than compiled depth, and no cache-controlled replication exists; the fair-placement/GEPA study has only six held-out records; risk control is per artifact; the closed DSL misses legitimate transformations and loops; and pre-snapshot Git ancestry cannot be reconstructed.",
  );

  const claimsSlide = presentation.slides.getItem(25);
  const claimsTable = claimsSlide.tables.items[0];
  setTableCell(claimsTable, 9, 1, "The learned compiler generally dominates hand-written composition");
  setTableCell(claimsTable, 9, 2, "Macro beats partial GRC; fair pre-model manual ties GCS on 6 fresh pairs");
  setTableCell(claimsTable, 9, 3, "Not supported; structural parity");
  replaceStartingWith(
    presentation,
    "Five claims are not supported",
    "Manual composition beats partial GRC; once placement is equal, the manual program ties GCS. GEPA also retains its seed under the bounded search. No arm establishes universal superiority.",
  );

  replaceUnique(
    presentation,
    "The two-read artifact holds 30/30 while halving requests; the deeper three-read artifact saves more and records a factual miss. A hand-written macro matches quality and wins on tokens and dollars. Preservation is not invariant to depth.",
    "The two-read artifact holds 30/30 while halving requests; the deeper artifact records a factual miss. Manual composition beats partial GRC, and fair pre-model placement later ties GCS at 6/6. Runtime dominance is not the contribution.",
  );
  replaceUnique(
    presentation,
    "Next scientific threshold: a multi-family, time-forward comparison that includes cache economics, construction and maintenance effort, drift, and closer learned optimizers.",
    "Next scientific threshold: preregistered cross-repository, time-forward comparison with engineering effort, cache economics, drift, and executable AWO / Agent JIT / EvoC2F baselines.",
  );
  renumberPages(presentation);
}

function updateTechnical(presentation, rows, families) {
  const cover = presentation.slides.getItem(0);
  setShapeText(cover, 6, "3");
  setShapeText(cover, 7, "real workflow families with distinct tools and graders");
  setShapeText(cover, 8, "90");
  replaceUnique(
    presentation,
    "The efficiency win is real but narrow: it removes redundant model turns on a read-only prefix — it does not remove the tool calls that gather evidence.\nA hand-written composite tool matched or beat the learned compiler on most workloads. Compilation earns its complexity on branching or changing workflows, not on stable ones.\nThe paper reports four negative results of its own: efficiency gains establish neither factual quality, nor superiority over hand-written code, nor portfolio superiority, nor admission safety.",
    "The efficiency win is real but narrow: partial GRC removes model turns, not source reads.\nManual composition beats partial GRC; when both execute before request one, manual and GCS tie structurally at 6/6 exact quality.\nBounded official GEPA retains its seed. The contribution is guarded automatic specialization—not runtime dominance.",
  );
  replaceUnique(
    presentation,
    "On unseen real records, how does a compiled prefix trade factual quality against requests, tokens, latency, and cost?",
    "Across distinct real-record workflows, do guarded programs preserve exact outcomes while reducing requests, tokens, latency, and cost?",
  );
  replaceUnique(
    presentation,
    "Shipped as two passes over one typed trace representation: guarded region compilation (studied here) and trace-guided workflow specialization (routing).",
    "Shipped over one typed trace IR: guarded region compilation, guarded composite synthesis over admitted read programs, and trace-guided workflow specialization for routing.",
  );
  replaceUnique(
    presentation,
    "Bounded registry lookup by compatibility and partition key\nGuard → gate → stage → interpret → verify → commit\nOf seven terminal edges, exactly one compacts",
    "Bounded lookup by compatibility and partition\nOrdinary GRC: guard → gate → stage → interpret → verify → commit\nEligible GCS: verify and project before provider request one",
  );
  replaceUnique(
    presentation,
    "Every rejection is recorded with its stage, so failures stay in the denominator. The action set at the compiler layer is exactly two: retain the baseline, or admit one compiled artifact.",
    "Every rejection is recorded with its stage. The compiler still emits or retires; only after admission may GCS package a batchable read program behind a bounded projection.",
  );
  replaceUnique(
    presentation,
    "Caveat the paper insists on: “baseline runs unchanged” is exact only where a staging owner holds the commit boundary. A model-boundary adapter cannot un-emit a response the host already committed to history.",
    "Caveat: exact fallback still requires a staging owner. The GCS pre-model path avoids post-emission rollback by verifying its continuation pin, program, and task projection before the provider sees the observation.",
  );
  replaceUnique(
    presentation,
    "Four GitHub protocols on a pinned snapshot",
    "Three primary GitHub workflow families plus scoped ablations on a pinned snapshot",
  );

  const familySlide = presentation.slides.getItem(13).duplicate();
  familySlide.setIndex(14);
  editWorkflowFamilySlide(familySlide, families, "technical");

  const macroSlide = presentation.slides.getItem(18);
  setShapeText(macroSlide, 3, "Before GCS, the hand macro is the stronger fixed-workflow baseline");
  setShapeText(
    macroSlide,
    4,
    "Against partial GRC, the hand-written composite matches exact quality and request savings while using one interface and fewer tokens. Priced with prompt-cache reuse the gap narrows to 30.9% fewer tokens for 8.0% lower cost, because interface fusion destroys the repeated prefix. This is the correct baseline for a stable read set.",
  );
  const gcsSlide = macroSlide.duplicate();
  gcsSlide.setIndex(19);
  editGcsSlide(gcsSlide, rows, "technical");

  replaceStartingWith(
    presentation,
    "No perturbation challenge ran on the live artifact",
    "No perturbation challenge ran on the primary live artifact\nGCS / GEPA results hold at α=.10, not the registered .05\nFair placement / GEPA has only six held-out cases\nAWO · Agent JIT · EvoC2F remain unexecuted\nBreak-even 181–411 episodes; part of the cost range is cache warmth",
  );
  replaceUnique(
    presentation,
    "Where a stable read set is known, a hand-written composite tool wins on tokens and dollars. Compilation earns its cost where which reads to make is itself the recurrent structure, or where the region branches.",
    "Manual composition beats partial GRC on the stable workflow. At equal pre-model placement, manual and GCS tie requests, interfaces, input tokens, and exact quality. Automatic guarded discovery—not runtime dominance—is the remaining value claim.",
  );
  renumberPages(presentation);
}

async function buildDeck({ artifact, templatePath, outputPath, expectedHash, expectedSlides, mode, rows, families }) {
  assertEqual(await sha256(templatePath), expectedHash, `${mode} template hash`);
  const { FileBlob, PresentationFile } = artifact;
  const presentation = await PresentationFile.importPptx(await FileBlob.load(templatePath));
  assertEqual(presentation.slides.count, expectedSlides, `${mode} source slide count`);
  if (mode === "seminar") updateSeminar(presentation, rows, families);
  else updateTechnical(presentation, rows, families);
  const expectedOutputSlides = mode === "seminar" ? 27 : 23;
  assertEqual(presentation.slides.count, expectedOutputSlides, `${mode} output slide count`);
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  const output = await PresentationFile.exportPptx(presentation);
  await output.save(outputPath);
  return {
    path: path.relative(ROOT, outputPath).split(path.sep).join("/"),
    sha256: await sha256(outputPath),
    slides: expectedOutputSlides,
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const artifactWorkspace = path.resolve(requireValue(
    args["artifact-workspace"],
    "--artifact-workspace must name a directory whose node_modules contains @oai/artifact-tool",
  ));
  const outputDir = path.resolve(args["output-dir"] || path.join(PAPER, "slides"));
  const mapPath = path.join(PAPER, "slides/gac-template-map.json");
  const gcsPath = path.join(PAPER, "results/gcs_live/results.json");
  const replayPath = path.join(PAPER, "results/gcs_validation/provider_free.json");
  const optimizerPath = path.join(PAPER, "results/optimizer_head_to_head/results.json");
  const externalPath = path.join(PAPER, "results/external_benchmarks/reference_analysis.json");
  const familiesPath = path.join(PAPER, "results/github_workflow_families/summary.json");
  const admissionPath = path.join(PAPER, "results/admission_register.json");
  const [map, gcs, replay, optimizer, external, families, admission, artifact] = await Promise.all([
    readJson(mapPath),
    readJson(gcsPath),
    readJson(replayPath),
    readJson(optimizerPath),
    readJson(externalPath),
    readJson(familiesPath),
    readJson(admissionPath),
    loadArtifactTool(artifactWorkspace),
  ]);
  assertEqual(map.schema, "agent-compaction-slide-template-map/v1", "slide map schema");
  validateEvidence(gcs, replay, optimizer, external, families, admission);
  const rows = metricRows(optimizer);
  const seminar = map.templates.seminar;
  const technical = map.templates.technical;
  const outputs = {};
  outputs.seminar = await buildDeck({
    artifact,
    templatePath: path.join(ROOT, seminar.path),
    outputPath: path.join(outputDir, path.basename(seminar.output)),
    expectedHash: seminar.sha256,
    expectedSlides: seminar.source_slides,
    mode: "seminar",
    rows,
    families,
  });
  outputs.technical = await buildDeck({
    artifact,
    templatePath: path.join(ROOT, technical.path),
    outputPath: path.join(outputDir, path.basename(technical.output)),
    expectedHash: technical.sha256,
    expectedSlides: technical.source_slides,
    mode: "technical",
    rows,
    families,
  });
  const manifest = {
    schema: "agent-compaction-slide-generation/v1",
    generator: "paper/scripts/generate_slides.mjs",
    // Recording the generator's own digest is what lets a later check notice that the
    // deck sources changed while the .pptx binaries did not. A rendered deck that no
    // longer matches its generator is a claim the repository cannot support.
    generator_sha256_current: await sha256(fileURLToPath(import.meta.url)),
    template_map: "paper/slides/gac-template-map.json",
    evidence: {
      gcs_live: { path: "paper/results/gcs_live/results.json", sha256: await sha256(gcsPath) },
      gcs_replay: { path: "paper/results/gcs_validation/provider_free.json", sha256: await sha256(replayPath) },
      optimizer_head_to_head: { path: "paper/results/optimizer_head_to_head/results.json", sha256: await sha256(optimizerPath) },
      external_benchmarks: { path: "paper/results/external_benchmarks/reference_analysis.json", sha256: await sha256(externalPath) },
      github_workflow_families: { path: "paper/results/github_workflow_families/summary.json", sha256: await sha256(familiesPath) },
      admission_register: { path: "paper/results/admission_register.json", sha256: await sha256(admissionPath) },
    },
    templates: {
      seminar: { path: seminar.path, sha256: seminar.sha256, source_slides: seminar.source_slides },
      technical: { path: technical.path, sha256: technical.sha256, source_slides: technical.source_slides },
    },
    outputs,
    source_slide_for_output: {
      seminar: seminar.source_slide_for_output,
      technical: technical.source_slide_for_output,
    },
    evidence_boundary: "Three real-record workflow families support the primary transfer result: compiled 90/90, baseline 89/90, manual 90/90, all admitted at the registered alpha=.05 with a pooled 3.3% compiled-only discordance bound. The snapshot does not establish cross-repository or time-forward transfer, and part of the reported 32.0-75.3% cost range reflects prompt-cache warmth rather than compiled depth. GCS and comparator results rest on an artifact calibrated at alpha=.10 and are not licensed at .05. NESTFUL and API-Bank remain refusal evidence; eight other benchmark paths are supplementary interoperability audits.",
  };
  const manifestPath = path.join(PAPER, "results/slide_generation.json");
  await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify(manifest, null, 2)}\n`);
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});
