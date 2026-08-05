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

function validateEvidence(gcs, replay) {
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
}

function metricRows(gcs) {
  const metrics = gcs.macro_vs_gcs.metrics;
  const fmt = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
  return [
    ["Metric", "Macro", "GCS", "Result"],
    ["Provider requests", metrics.requests.macro_mean.toFixed(2), metrics.requests.gcs_mean.toFixed(2), "−50.0%"],
    ["Tool interfaces", metrics.tool_calls.macro_mean.toFixed(2), metrics.tool_calls.gcs_mean.toFixed(2), "tie"],
    ["Total tokens", fmt.format(metrics.total_tokens.macro_mean), fmt.format(metrics.total_tokens.gcs_mean), "−38.9%"],
    ["Wall latency", `${fmt.format(metrics.wall_latency_ms.macro_mean)} ms`, `${fmt.format(metrics.wall_latency_ms.gcs_mean)} ms`, "−40.0%"],
    ["Estimated cost", `$${metrics.estimated_cost_usd.macro_mean.toFixed(6)}`, `$${metrics.estimated_cost_usd.gcs_mean.toFixed(6)}`, "−32.3%"],
  ];
}

function editGcsSlide(slide, rows, mode) {
  const seminar = mode === "seminar";
  setShapeText(slide, 2, seminar
    ? "RESULTS  ·  EXPLORATORY GCS EXTENSION  ·  REAL-PROVIDER PAIRED STUDY"
    : "GCS  ·  FRESH REAL-PROVIDER COMPARISON");
  setShapeText(slide, 3, "GCS removes the measured macro's extra model turn");
  setShapeText(
    slide,
    4,
    seminar
      ? "Both arms preserve 12/12 exact contracts. GCS moves an admitted three-read program before the first provider request and returns one bounded task observation."
      : "Both arms pass 12/12 exact contracts. GCS executes the admitted three-read program before request one and returns one task-specific observation.",
  );
  setShapeText(slide, 5, "12 FRESH, CALIBRATION-DISJOINT PUBLIC ISSUES — LOWER RESOURCE USE IS BETTER");
  setShapeText(
    slide,
    seminar ? 7 : 6,
    seminar
      ? "Provider-backed OpenAI Agents SDK executions over pinned real public records, counterbalanced by condition order and disjoint from all 424 earlier issue IDs. Exposed interfaces tie 1–1; internal source reads tie 3–3."
      : "Real public issue records, live provider calls, counterbalanced order, and no overlap with 424 earlier issue IDs. Interfaces tie 1–1; source reads tie 3–3.",
  );
  setShapeText(slide, seminar ? 11 : 10, "GCS wins the measured interface when…");
  setShapeText(
    slide,
    seminar ? 12 : 11,
    "the read program already passed admission\ntask projection is live-out-only and bounded\nthe continuation manifest is pinned exactly",
  );
  setShapeText(slide, seminar ? 16 : 15, "The remaining comparator…");
  setShapeText(
    slide,
    seminar ? 17 : 16,
    "an equally pre-executed manual macro\nthe same projection and continuation contract\nmultiple workflow families and time-forward drift",
  );
  if (seminar) {
    setShapeText(slide, 19, "MECHANISM, EVIDENCE, AND BOUNDARY");
    setShapeText(
      slide,
      20,
      "Placement — not a new read algorithm — explains the measured advantage. The provider-visible macro spends one request selecting its composite and a second producing the answer; GCS verifies and executes before request one. Requests, tokens, observed latency, and estimated cost improve, while exact quality, interface count, and source reads tie. This post-study result covers one workflow family and does not show that GCS dominates an equally pre-executed manual program.",
    );
  } else {
    setShapeText(
      slide,
      18,
      "Placement explains the gain: the provider-visible macro spends one request selecting its composite and another answering; GCS verifies and executes before request one. This is exploratory one-family evidence and does not test an equally pre-executed manual macro.",
    );
  }
  const table = slide.tables.items[0];
  if (!table || table.rowCount !== 6 || table.columnCount !== 4) {
    throw new Error(`${mode} GCS slide: expected inherited 6x4 comparator table`);
  }
  table.setValues(rows);
}

function updateSeminar(presentation, rows) {
  replaceUnique(presentation, "4 live protocols on a\npinned public snapshot", "5 live protocols on a\npinned public snapshot");
  replaceUnique(
    presentation,
    "Guarded agentic compaction. Traces establish recurrence, not admissibility. We specify the evidence a compiler needs, the barriers it must respect, and four negative results.",
    "Guarded agentic compaction. Traces establish recurrence, not admissibility. We specify the evidence a compiler needs, the barriers it must respect, and the limits its evidence retains.",
  );
  replaceUnique(
    presentation,
    "On an unseen real-record workload, how does a learned compiled prefix trade factual quality against requests, tokens, latency, and cost — relative to an unchanged agent and a hand-written composite tool?",
    "On unseen real records, how do a compiled prefix, a hand-written composite, and guarded composite synthesis trade factual quality against requests, tokens, latency, and cost?",
  );
  replaceUnique(
    presentation,
    "A trace-to-program formulation combining typed value provenance, effect-aware barriers, a closed synthesis language, empirical contracts, and runtime fallback\nA dispatch protocol whose score is frozen before calibration and whose fixed threshold grid receives a simultaneous one-sided exact binomial bound\nA real-provider, real-public-record study in which the agent chooses tool order and quality is graded independently of execution conformance\nAn external NESTFUL study reporting provenance success, synthesis abstention, and a useful negative result\nA framework-neutral transformation portfolio over measured actions only",
    "A trace-to-program formulation combining typed value provenance, effect-aware barriers, a closed synthesis language, empirical contracts, and runtime fallback\nA dispatch protocol whose score is frozen before calibration and whose fixed threshold grid receives a simultaneous one-sided exact binomial bound\nA real-provider, real-public-record study in which the agent chooses tool order and quality is graded independently of execution conformance\nAn external NESTFUL study reporting provenance success, synthesis abstention, and a useful negative result\nA measured-action portfolio plus guarded composite synthesis over an already admitted read program",
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
    "Five GitHub protocols on a pinned 12.7 MB Apache-2.0 snapshot, including the later GCS/macro comparison",
  );

  const macroSlide = presentation.slides.getItem(20);
  setShapeText(macroSlide, 3, "Manual composition is the stronger pre-GCS fixed-workflow baseline");
  setShapeText(
    macroSlide,
    4,
    "Against partial GRC, the hand-written composite matches exact quality and request savings while using one interface and fewer tokens. That negative result motivates interface-level synthesis rather than weakening admission.",
  );
  const gcsSlide = macroSlide.duplicate();
  gcsSlide.setIndex(21);
  editGcsSlide(gcsSlide, rows, "seminar");

  replaceStartingWith(
    presentation,
    "Also: discovery is not free",
    "Also: discovery is not free (132 episodes cost 528 provider requests, 533,293 tokens, and about $0.096, with break-even between 176 and 292 eligible future episodes); GCS is a post-study, one-family extension with no equally pre-executed manual comparator; risk control is per artifact; the closed DSL intentionally misses legitimate transformations and loops; and pre-snapshot Git ancestry cannot be reconstructed.",
  );

  const claimsSlide = presentation.slides.getItem(24);
  const claimsTable = claimsSlide.tables.items[0];
  setTableCell(claimsTable, 9, 1, "The learned compiler generally dominates hand-written composition");
  setTableCell(claimsTable, 9, 2, "Macro beats partial GRC; GCS beats the provider-visible macro on 12 fresh pairs");
  setTableCell(claimsTable, 9, 3, "Not supported across interfaces");
  replaceStartingWith(
    presentation,
    "Five claims are not supported",
    "The register preserves both directions of the macro result: manual composition beats partial GRC, while GCS later beats the measured provider-visible macro. Neither establishes universal superiority.",
  );

  replaceUnique(
    presentation,
    "The two-read artifact holds 30/30 while halving requests; the deeper three-read artifact saves more and records a factual miss. A hand-written macro matches quality and wins on tokens and dollars. Preservation is not invariant to depth.",
    "The two-read artifact holds 30/30 while halving requests; the deeper artifact records a factual miss. Manual composition beats partial GRC, while GCS later matches 12/12 quality and beats the measured provider-visible macro. Neither direction is universal.",
  );
  replaceUnique(
    presentation,
    "Next scientific threshold: a multi-family, time-forward comparison that includes cache economics, construction and maintenance effort, drift, and closer learned optimizers.",
    "Next scientific threshold: preregistered multi-family, time-forward comparison against an equally pre-executed manual macro, with cache economics, maintenance effort, drift, and closer learned optimizers.",
  );
  renumberPages(presentation);
}

function updateTechnical(presentation, rows) {
  const coverProtocolCounts = presentation.slides.getItem(0).shapes.items.filter(
    (shape) => (shape.text?.toString?.() ?? "") === "4",
  );
  if (coverProtocolCounts.length !== 1) {
    throw new Error(`technical cover protocol count: expected one match, found ${coverProtocolCounts.length}`);
  }
  coverProtocolCounts[0].text.set("5");
  replaceUnique(
    presentation,
    "The efficiency win is real but narrow: it removes redundant model turns on a read-only prefix — it does not remove the tool calls that gather evidence.\nA hand-written composite tool matched or beat the learned compiler on most workloads. Compilation earns its complexity on branching or changing workflows, not on stable ones.\nThe paper reports four negative results of its own: efficiency gains establish neither factual quality, nor superiority over hand-written code, nor portfolio superiority, nor admission safety.",
    "The efficiency win is real but narrow: partial GRC removes redundant model turns, not the source reads that gather evidence.\nManual composition beats partial GRC on this fixed workflow; GCS later removes the measured provider-visible macro's extra model turn at equal 12/12 quality.\nThat result is post-study and one-family: the best equally pre-executed manual comparator remains untested.",
  );
  replaceUnique(
    presentation,
    "On unseen real records, how does a compiled prefix trade factual quality against requests, tokens, latency, and cost?",
    "On unseen real records, how do partial GRC, manual composition, and GCS trade factual quality against requests, tokens, latency, and cost?",
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
    "Five GitHub protocols on a pinned snapshot, including the fresh GCS/macro comparison",
  );

  const macroSlide = presentation.slides.getItem(17);
  setShapeText(macroSlide, 3, "Before GCS, the hand macro is the stronger fixed-workflow baseline");
  setShapeText(
    macroSlide,
    4,
    "Against partial GRC, the hand-written composite matches exact quality and request savings while using one interface and fewer tokens. This is the correct baseline for a stable read set.",
  );
  const gcsSlide = macroSlide.duplicate();
  gcsSlide.setIndex(18);
  editGcsSlide(gcsSlide, rows, "technical");

  replaceStartingWith(
    presentation,
    "No perturbation challenge ran on the live artifact",
    "No perturbation challenge ran on the primary live artifact\nGCS is exploratory evidence from one workflow family\nNo equally pre-executed manual-macro arm was tested\nDiscovery is costly; risk is artifact-specific",
  );
  replaceUnique(
    presentation,
    "Where a stable read set is known, a hand-written composite tool wins on tokens and dollars. Compilation earns its cost where which reads to make is itself the recurrent structure, or where the region branches.",
    "Manual composition beats partial GRC on the stable workflow. GCS then beats the measured provider-visible macro by moving the admitted program before request one; an equally pre-executed manual macro remains the required comparator.",
  );
  renumberPages(presentation);
}

async function buildDeck({ artifact, templatePath, outputPath, expectedHash, expectedSlides, mode, rows }) {
  assertEqual(await sha256(templatePath), expectedHash, `${mode} template hash`);
  const { FileBlob, PresentationFile } = artifact;
  const presentation = await PresentationFile.importPptx(await FileBlob.load(templatePath));
  assertEqual(presentation.slides.count, expectedSlides, `${mode} source slide count`);
  if (mode === "seminar") updateSeminar(presentation, rows);
  else updateTechnical(presentation, rows);
  const expectedOutputSlides = mode === "seminar" ? 26 : 22;
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
  const [map, gcs, replay, artifact] = await Promise.all([
    readJson(mapPath),
    readJson(gcsPath),
    readJson(replayPath),
    loadArtifactTool(artifactWorkspace),
  ]);
  assertEqual(map.schema, "agent-compaction-slide-template-map/v1", "slide map schema");
  validateEvidence(gcs, replay);
  const rows = metricRows(gcs);
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
  });
  outputs.technical = await buildDeck({
    artifact,
    templatePath: path.join(ROOT, technical.path),
    outputPath: path.join(outputDir, path.basename(technical.output)),
    expectedHash: technical.sha256,
    expectedSlides: technical.source_slides,
    mode: "technical",
    rows,
  });
  const manifest = {
    schema: "agent-compaction-slide-generation/v1",
    generator: "paper/scripts/generate_slides.mjs",
    template_map: "paper/slides/gac-template-map.json",
    evidence: {
      gcs_live: { path: "paper/results/gcs_live/results.json", sha256: await sha256(gcsPath) },
      gcs_replay: { path: "paper/results/gcs_validation/provider_free.json", sha256: await sha256(replayPath) },
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
    evidence_boundary: "Post-study exploratory result on one workflow family; no equally pre-executed manual-macro comparator.",
  };
  const manifestPath = path.join(PAPER, "results/slide_generation.json");
  await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
  process.stdout.write(`${JSON.stringify(manifest, null, 2)}\n`);
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});
