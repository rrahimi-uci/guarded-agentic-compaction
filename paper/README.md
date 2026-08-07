# Guarded Agentic Compaction paper artifact

This directory is the complete, reproducible artifact for:

> **Compiling Recurrent Agent Workflows into Guarded Programs**

The paper studies whether repeated model-mediated, read-only tool prefixes can be
replaced by trace-derived deterministic programs without hiding provenance, effect,
calibration, or fallback requirements. Its primary evidence spans three distinct GitHub
workflow families with real public records and live provider calls, plus refusal results
on two trace-complete public compiler substrates. A broader interoperability audit remains
supplementary because it does not measure optimizer value.

## Directory map

```text
paper/
├── tex/
│   ├── body.tex                    the manuscript body — single source of truth
│   ├── abstract-body.tex           abstract text, shared by both builds
│   ├── abstract.tex                abstract environment wrapper
│   ├── article.tex                 single-column journal article build  ← primary
│   └── main.tex                    two-column ACM sigconf review build
├── figures/                        authored artwork and pseudocode
│   ├── architecture.tex            TikZ system architecture (Figure 1)
│   ├── alg-compile.tex             Algorithm 1  Compile
│   ├── alg-provenance.tex          Algorithm 2  BuildPatg
│   ├── alg-calibrate.tex           Algorithm 3  Calibrate
│   └── alg-dispatch.tex            Algorithm 4  Dispatch
├── appendix/appendix.tex           reproducibility and audit appendix
├── bibliography/references.bib     primary-source bibliography
├── generated_figures/              script-generated PDF and PNG figures
├── tables/                         script-generated LaTeX tables
├── slides/
│   ├── GAC-seminar.pptx             25-slide source template, hash-pinned
│   ├── GAC-technical-review.pptx    21-slide source template, hash-pinned
│   ├── gac-template-map.json        source-to-output slide mapping
│   ├── README.md                    generation and evidence-boundary notes
│   ├── compiling-recurrent-agent-workflows-into-guarded-programs.pptx
│   │                                editable 27-slide seminar presentation
│   └── compiling-recurrent-agent-workflows-into-guarded-programs-detailed.pptx
│                                    editable 23-slide technical-review presentation
├── results/
│   ├── datasets/                   pinned upstream snapshots and manifests
│   ├── github_live/                real-record/live-provider raw results
│   ├── github_natural_live/        free-order real-provider study and raw results
│   ├── portfolio_live/             frozen decision and prospective fresh-cohort result
│   ├── gcs_validation/             provider-free real-trace composite replay
│   ├── gcs_live/                   exploratory fresh macro-vs-GCS paid comparison
│   ├── optimizer_head_to_head/     live GEPA/GCS/manual pre-model comparison
│   ├── github_natural_replication/ expanded paid 30-pair replication
│   ├── github_workflow_families/  PR-outcome and backlog-attention live studies plus summary
│   ├── multidomain/                real-record provider-free extension preflight
│   ├── nestful/                    public-benchmark raw results
│   ├── external_benchmarks/         all-source preflight, compiler, checker, and bounded live results
│   ├── artifact_manifest.json      checksums of quantitative paper artifacts
│   └── publication_manifest.json   final source/evidence/PDF checksums
├── scripts/
│   ├── github_natural_workflow_study.py  earlier aggressive natural-order experiment
│   ├── continuation_replay.py      checked post-model replay on retained outputs
│   ├── github_live_study.py        fixed ablation and expanded natural replication
│   ├── portfolio_live_study.py     reviewed portfolio selection and prospective test
│   ├── validate_guarded_composite.py provider-free 132-trace GCS reconstruction
│   ├── github_gcs_live_study.py    paid fresh real-record GCS/macro comparison
│   ├── github_optimizer_head_to_head.py bounded real GEPA/GCS/manual comparison
│   ├── github_workflow_family_study.py three-family real-record study runner
│   ├── build_github_family_summary.py checked cross-family result ledger/table
│   ├── multidomain_study.py        gated real-provider multidomain runner
│   ├── validate_multidomain.py     provider-free independent-gold validation
│   ├── nestful_benchmark.py        provider-free external benchmark
│   ├── external_benchmark_sources.py pinned all-source acquisition/preflight
│   ├── external_benchmark_matrix.py shared-IR screening and evidence matrix
│   ├── api_bank_benchmark.py       second provider-free compiler benchmark
│   ├── bfcl_structural_benchmark.py official BFCL gold checker
│   ├── toolsandbox_live_summary.py redacted official live-run summary
│   ├── tau2_live_summary.py        redacted four-domain live-run summary
│   ├── browsecomp_live_benchmark.py sealed hosted-search subset
│   ├── build_artifacts.py          deterministic figures/tables
│   ├── generate_slides.mjs         hash-bound GAC-template slide generator
│   └── validate_artifacts.py       claim and integrity audit
├── paper-review.md                 earlier adversarial peer review
├── reviews/
│   └── GAC_paper_review.md        latest artifact-aware score review
├── supplementary/                  evidence register, audit, and rubric
│   ├── evidence-register.md        claim-level evidence boundaries
│   ├── experiment-verification.md  independent recomputation and statistical audit
│   ├── external-benchmark-audit.md why eight interoperability paths are supplementary
│   ├── implementation-audit.md     repository and component review
│   ├── quality-assessment.md       publication-readiness rubric
│   └── natural-live-study-protocol.md  expanded real-record experiment protocol
└── build/
    ├── article.pdf                 single-column article (page count verified after build)
    └── main.pdf                    two-column conference build (page count verified after build)
```

`figures/` holds manually authored source artwork — the TikZ architecture diagram,
the retained pipeline pseudocode, and archived detailed listings; all plots are script-generated and live under
`generated_figures/`.

The tracked distribution PDF is
compiling-recurrent-agent-workflows-into-guarded-programs.pdf. The files under build/
remain the conference and long-form article products used by the validator.

## Two builds, one body

`body.tex` and `abstract-body.tex` are the only places manuscript prose exists.
`article.tex` and `main.tex` are presentation wrappers that `\input` them, so the two
PDFs cannot drift apart:

| | `article.pdf` | `main.pdf` |
|:---|:---|:---|
| class | `article`, single column, A4 | `acmart[sigconf,nonacm]` |
| typography | Pagella text and math, Latin Modern sans/mono | ACM Libertine |
| audience | reading, circulation, archival | conference submission |
| line numbers | no | no |

The validator compiles both and asserts that the architecture figure and all four
algorithms reach the page in each, so a wrapper that silently drops an `\input` fails
the audit rather than shipping a short paper.

The artifact has no MLflow dependency. Normalized Episodes are persisted in a strict,
canonical, atomic local JSONL snapshot; OpenAI Agents SDK capture is the only maintained
foreign trace adapter. The design rationale and the deliberately omitted remote-tracking
capabilities are documented in
[`docs/mlflow-removal-report.md`](../docs/mlflow-removal-report.md).

## Evidence classification

- **NESTFUL:** real public benchmark data, deterministic executable functions, no model
  calls. This tests post-trace provenance, synthesis, replay, and refusal; it is not a
  model-planning score.
- **Three-family primary evaluation:** issue-type routing, PR-outcome audit, and
  backlog-attention routing each use 132 discovery plus 30 held-out real records, distinct
  tools and exact graders, and live provider calls. Compiled programs reach 90/90 exact
  outcomes versus 89/90 baseline while reducing requests 66.6%, tokens 63.1%, observed
  latency 64.2%, and estimated cost 58.7% in aggregate. Hand-written programs also reach
  90/90; runtime superiority is not claimed.
- **Supplementary interoperability audit:** every requested benchmark family retains a
  pinned source and adapter, execution, or gate disposition, but the eight paths without a
  trace-compatible paired compiler comparison are excluded from the main paper result.
- **Expanded natural-order replication:** 132 discovery and 30 held-out actual public
  issue records, deterministic snapshot tools, and live OpenAI calls through the Agents
  SDK. The compiler rejects an ungroundable three-read candidate, emits a two-read prefix,
  and is compared with an unchanged agent and hand-written macro under all six condition
  orders. This is the primary confirmatory real-scenario result.
- **Earlier aggressive natural-order GitHub study:** 80 discovery and 18 held-out public issue
  records, deterministic snapshot tools, and live OpenAI calls through the Agents SDK.
  Its prompt names neither tools nor order; it compares an unchanged agent, learned
  compiler, and hand-written macro under all six condition orders. This is a
  depth-sensitive negative result, not a live GitHub-service reliability test.
- **Controlled fixed-prefix GitHub ablation:** real records and provider calls, but its
  prompt prescribes the three-read sequence and its summary oracle checks shape rather
  than factuality. It remains as a scoped conformance ablation.
- **Continuation-contract replay:** provider-free counterfactual over the 18 retained
  compiled outputs and their pinned real source records. It detects the one factual miss
  and checked-renders it to 18/18; it is not a live latency/cost arm.
- **Guarded composite extension:** provider-free reconstruction recompiles the complete
  three-read program from 132 sealed provider traces and checks 124 admitted projections
  exactly (8 safe fallbacks). A separate paid exploratory run compares a continuation-pinned
  pre-model composite with the provider-visible hand-written macro on 12 further public
  issues: both pass 12/12 exact contracts; GCS uses fewer requests, tokens, observed
  latency, and estimated cost. This was designed after the earlier macro result and does
  not by itself establish superiority over a fair pre-model manual program.
- **Bounded optimizer and fair-placement comparison:** a provider-free preflight verifies
  12/12 exact GCS/manual projections. Official GEPA 0.1.4 then makes 14 real task
  evaluations and three real reflection calls, followed by a five-condition live study on
  six new public issues. GCS and the independent pre-model manual program both pass 6/6
  with one request, one interface, and identical input tokens. GEPA retains its seed and
  leaves deployment requests unchanged. Its 59-request optimization overhead is reported
  separately. This is exploratory single-family evidence, not a simulation or a general
  learned-optimizer ranking.
- **Archived pilot:** a real-provider negative result that exposed unsafe suffix dispatch.
  It is retained under `results/github_live/pilot_2026-08-03/` and excluded from the final
  cohort.
- **Demonstration suite (Tier 3):** live provider calls and the real SDK runtime against
  deterministic local services holding *fictional* business records. It cannot support a
  claim about real-world data, and the paper never uses it for one. What it does cover is
  control-flow structure the other two tiers do not contain at all: observation-dependent
  branches, pagination, a mandatory irreversible write (so only *partial* compaction is
  reachable), a handoff barrier, an undeclared-effect MCP surface, and route
  specialization. Demo E reduces 7.0 to 2.0 model requests and total tokens by 66.4% on
  the fictional WMS fixture, while the write remains in the ordinary agent; its estimated
  cost rises 8.3% because cache reuse fragments. Three of its eight conditions are negative
  controls whose only correct outcome is no compaction. Raw results are in
  `../experiments/live_results/`.
- **Prospective multidomain extension (preflight only):** 420 real vulnerability groups
  and 420 privacy-modified public HMDA groups pass independent provider-free gold
  reconstruction; HMDA has 416/420 variable paths. SEC acquisition is source-gated, no
  three-domain protocol is frozen, no human macro approval exists, and no provider call
  has run. These artifacts establish data and control-plane feasibility only; they
  contribute no optimization result to this paper. See
  [`../benchmarks/README.md`](../benchmarks/README.md).

## Reproduce without provider calls

From the repository root:

```bash
.venv/bin/python paper/scripts/nestful_benchmark.py
# After acquiring the pinned sources into a disposable directory:
.venv/bin/python paper/scripts/external_benchmark_matrix.py \
    --source-root "$BENCHMARK_SOURCE_ROOT"
.venv/bin/python paper/scripts/api_bank_benchmark.py \
    --source-root "$BENCHMARK_SOURCE_ROOT"
.venv/bin/python paper/scripts/bfcl_structural_benchmark.py \
    --source-root "$BENCHMARK_SOURCE_ROOT"
.venv/bin/python paper/scripts/github_live_study.py \
    --task-design natural-extractive-v2 --evaluation-order counterbalanced \
    --include-macro --preflight-only
.venv/bin/python paper/scripts/github_live_study.py \
    --task-design natural-extractive-v2 --regrade-results \
    --results-path paper/results/github_natural_replication/results.json
.venv/bin/python paper/scripts/continuation_replay.py
.venv/bin/python paper/scripts/validate_guarded_composite.py
.venv/bin/python paper/scripts/github_optimizer_head_to_head.py \
    --regrade-existing paper/results/optimizer_head_to_head/results.json
M=paper/results/multidomain/preflight
V=paper/scripts/validate_multidomain.py
.venv/bin/python "$V" \
    --pool vulnerability="$M/vulnerability" \
    --pool hmda="$M/hmda" --out "$M/validation.json"
.venv/bin/python paper/scripts/build_artifacts.py
.venv/bin/coverage run -m pytest -q
.venv/bin/coverage json -o paper/results/coverage.json
.venv/bin/python scripts/verify_release.py
.venv/bin/python paper/scripts/validate_artifacts.py
```

The NESTFUL script downloads only the files named in its pinned source manifest and
verifies SHA-256 digests. `build_artifacts.py` consumes sealed JSON/CSV results and makes
no network or provider calls. The natural-study preflight uses the same pinned real
records and seals the free-order 30-pair design while making zero OpenAI calls. The paid
run subsequently used that exact selection. The regrade command recomputes semantic and
exact-source quality without calling the provider; see
[`supplementary/natural-live-study-protocol.md`](supplementary/natural-live-study-protocol.md).
`continuation_replay.py` independently recomputes the post-model contract decisions from
the retained live-provider answers and pinned source observations; it makes no provider
call and reports no counterfactual latency or cost.

## Repeat the paid real-provider study

The existing raw result is sufficient to rebuild the paper. Re-running this command
spends API credits and produces nondeterministic provider latency/text:

```bash
# .env must contain OPENAI_API_KEY; HF_TOKEN is used for the pinned dataset download.
.venv/bin/python paper/scripts/github_natural_workflow_study.py --smoke

# The earlier aggressive natural-order run recorded this exact command.
.venv/bin/python paper/scripts/github_natural_workflow_study.py \
    --discovery-cases 80 --train-cases 20 --dev-cases 10 \
    --calibration-cases 45 --test-cases 18 --concurrency 6

# Provider-free: recompute the corrected oracle and derived statistics from sealed output.
.venv/bin/python paper/scripts/github_natural_workflow_study.py --regrade-results

# Expanded primary replication: real paid calls on the sealed 30-pair selection.
.venv/bin/python paper/scripts/github_live_study.py \
    --task-design natural-extractive-v2 --evaluation-order counterbalanced \
    --include-macro --discovery-cases 132 --train-cases 16 --dev-cases 8 \
    --calibration-cases 92 --test-per-class 10 --repeat-cases 10 \
    --concurrency 8 --seed 20260802

# Provider-free semantic regrade of those retained outputs.
.venv/bin/python paper/scripts/github_live_study.py \
    --task-design natural-extractive-v2 --regrade-results \
    --results-path paper/results/github_natural_replication/results.json

# Prospective portfolio protocol: inspect the frozen action and fresh cohort for free,
# then explicitly approve the reviewed macro before the paid paired run.
.venv/bin/python paper/scripts/portfolio_live_study.py \
    --preflight --cases-per-class 4
.venv/bin/python paper/scripts/portfolio_live_study.py \
    --cases-per-class 4 --approve-reviewed-macro

# Exploratory guarded-composite comparison; real paid OpenAI calls.
.venv/bin/python paper/scripts/github_gcs_live_study.py --smoke
.venv/bin/python paper/scripts/github_gcs_live_study.py --cases 12

# The older controlled ablation. The explicit flags matter: the script's defaults are
# --test-per-class 10 --repeat-cases 10, which would give 30 primary pairs and 10
# repeats instead of this run's 18 and 6, and a correspondingly larger API bill.
.venv/bin/python paper/scripts/github_live_study.py \
    --test-per-class 6 --repeat-cases 6
# all other values are script defaults: --model gpt-5.6-luna --discovery-cases 132
# --train-cases 16 --dev-cases 8 --calibration-cases 92 --concurrency 8 --seed 20260802
```

Runs now serialize `run.argv` and `run.resolved_config`, so any future result file records
its own design. The archived `results.json` predates that change; its configuration is the
command above, and it is recoverable from the stored split sizes (16/8/92), the 18-item
three-class test selection, and the six repeated issues.

All model turns in the full study use the OpenAI API. The tools read real records from a
pinned local snapshot so paired conditions see identical external state. The script
serializes only `openai_api_key_used: true` and `hf_token_used_for_download: true`; it
does not print or store secret values.

The controlled command uses `prescribed-v1`: its prompt explicitly orders the three reads,
and its summary check is a shape contract rather than a factuality oracle. These limits
are disclosed in the paper. The dedicated natural-workflow result uses exact snapshot
facts and a source-supported excerpt independent of tool order. Its provider outputs are
sealed; a provider-free `--regrade-results` command records and applies the documented
oracle correction without rerunning or changing model outputs or metrics.

A larger backward-compatible `natural-extractive-v2` replication was sealed first and
then executed with 132 discovery records, 30 held-out pairs, ten repeated pairs, and a
strict exact-field oracle. Its paid outputs, discovery checkpoint, failed-attempt boundary,
smoke, compiler registry, and provider-free oracle revision are retained under
`results/github_natural_replication/`.

The expanded replication's complete provider-cost estimate is **$0.19129** across
discovery and all three primary/repeat conditions. The earlier natural-order run's estimate
is **$0.09203** across discovery and all three test conditions; its preceding smoke
estimate is **$0.00253**.
The older fixed-prefix run used 132 discovery episodes plus 48 confirmatory/repeat
executions. Its discovery estimate is **$0.09581**; baseline and compiled estimates are
**$0.01703** and **$0.00759**, respectively. These are price-table estimates, not
invoices; check current provider pricing before repeating either study.

## Compile the manuscript

Tectonic 0.15.0 was used. It drives XeTeX and fetches packages on demand, which matters
here: the local TeX Live installation is the `basic` scheme and has neither `acmart` nor
the font packages either wrapper needs.

```bash
cd paper/tex
tectonic --keep-logs --keep-intermediates --outdir ../build article.tex
tectonic --keep-logs --keep-intermediates --outdir ../build main.tex
```

Both logs contain no undefined citations or references. `main.pdf` is the camera-ready
two-column conference wrapper rather than a review-mode build. Because the engine is XeTeX, the article build selects fonts
with complete `TU` coverage (Pagella via `newpx`, Latin Modern sans and mono); the Type-1
`helvet`/`tgheros` shapes have none and would silently fall back to the serif.

To re-render page images for visual inspection:

```bash
cd paper/build && pdftoppm -png -r 130 article.pdf article_pages/pg
```

## Main results

Across three primary real-record workflow families and 90 held-out live-provider cases,
compiled programs reach 90/90 exact contracts versus 89/90 baseline and 90/90 manual — not
a significant difference (exact McNemar `p=1`), though with no compiled-only failure in 90
pairs the one-sided 95% discordance bound is 3.3%. All three artifacts receive
per-fixed-candidate admission certificates at the registered `alpha=.05` over 92
zero-violation calibration groups.
Weighted compilation reductions are 66.6% requests, 44.2% visible tool interfaces, 63.1%
tokens, 64.2% observed wall latency, and 58.7% estimated cost. Per-family request/token/
latency/cost reductions range from 50.0/39.5/51.7/32.0% to
75.0/81.4/73.0/75.3%. This is workflow-family transfer on one repository snapshot, not
cross-repository or time-forward generalization; manual programs remain the runtime
baseline.

Three selective-risk levels appear in the paper and are not interchangeable.
`paper/results/admission_register.json` records the configuration of every admitted
artifact: `alpha=.05` for the three primary families and the prescribed-prefix ablation,
`alpha=.10` for the earlier three-read artifact (45/45, bound 0.0992) and for the
guarded-composite artifact behind every GCS and comparator number (88/92, bound 0.0520),
and a 15% pilot limit for the portfolio. Both `alpha=.10` artifacts would retire at the
registered target, so GCS results are licensed only at the 10% level.

These are per-fixed-candidate certificates. For a frozen candidate, conditioning on the
random admitted count gives an exact binomial model; Clopper--Pearson plus a Bonferroni
union bound over the 11 frozen thresholds validates data-dependent threshold selection.
The general compiler can, however, calibrate multiple candidate families on the same
groups, and the retained runs did not divide `delta` across that search. Therefore the
paper does not claim compiler-wide candidate-search control. A direct two-candidate
Bonferroni correction at `alpha=.05`, `delta=.10` requires 106 zero-violation admitted
groups rather than 92; alternatively, one candidate must be frozen before calibration or
a valid fixed-sequence procedure must be used.

`paper/results/cache_accounting.json` recovers the prompt-cache structure of the same runs
provider-free. In the issue-type family the hand-written macro uses 30.9% fewer tokens than
the compiled condition but is only 8.0% cheaper, because it serves 0.0% of its input from
cache against the compiled arm's 27.8% and the unchanged agent's 32.3%. Both newer families
are cache-cold in every arm, so their 75% cost reductions are measured against a baseline
that never amortizes its prefix. Provider-side break-even is 411, 182, and 181 future
episodes for issue-type, PR-outcome, and backlog-attention routing, excluding engineering,
review, monitoring, and invalidation cost.

In the expanded natural-order replication, all 132 discovery executions choose the same
three-read order, 130 pass the exact-source task, and the compiler refuses the ungroundable
third call. Across 30 fresh balanced and counterbalanced issues, the resulting two-read
prefix, unchanged agent, and macro each pass 30/30 exact factual and full task contracts.
Relative to the unchanged agent, partial compilation reduces requests 50.0%, tokens 39.5%,
observed wall latency 51.7%, and estimated cost 32.0%. The macro matches the request
reduction while saving 58.2% of tokens, 37.5% of cost, and two of three tool calls. The
compiler has lower observed mean latency, but its paired interval against the macro crosses
zero.

The compiler itself remains compile-or-retire. A new portfolio layer now compares measured
actions under exact group-level quality and regret-risk bounds. Using the 30 independent
replication groups, it admits both compiler and macro at a 15% pilot limit and recommends
the higher-utility macro for human review. On 12 fresh, calibration-disjoint issues, the
reviewed selection and baseline each pass 12/12 exact contracts; the selection reduces
requests 50.0%, tool calls 66.7%, tokens 59.2%, wall latency 71.6%, and estimated cost
40.6%. Macro synthesis, cache evidence, and multi-family policy superiority are not claimed.

The earlier aggressive natural-order study remains a depth-sensitive negative result: its
unchanged agent and macro pass 18/18 exact factual contracts, while the three-read compiler
passes 17/18. It saves more provider calls but does not establish preservation.

In the new bounded head-to-head, every one of five conditions passes 6/6 exact contracts.
GCS reduces requests 75.0% and input tokens 78.2% relative to unchanged, but ties the fair
manual pre-model program at one request, one interface, and 770.8 mean input tokens. GEPA
retains the seed after 14 task evaluations; deployment requests remain four, while the
separate optimization ledger records 59 provider requests, 63,954 tokens, and an estimated
\$0.01163. The GCS+GEPA label is therefore a GCS replication, not an optimized combination.

The older prescribed-prefix ablation records 18/18 passes under its weaker registered
contract and reductions of 75.0% requests, 65.7% tokens, 85.0% observed latency, and
52.6% estimated cost. Its necessary tool calls remain unchanged.

On the Tier-3 suite, the hardest shape (a workflow ending in an irreversible write)
compacts only *partially* — 7.0 to 2.0 model calls — which is the correct bound, and the
three refusal conditions each reproduce the baseline model-call count and registered
quality. Their dollar costs are not equal. Two demos
reduce tokens while *increasing* estimated cost (Demo E: −66.4% tokens, +8.3% cost;
Demo F: −16.8% tokens, +123.0% cost) because prompt-cache economics, not token count,
determine the invoice. Token reduction is therefore not a proxy for cost reduction.

On 1,415 executable NESTFUL basic-function episodes, provenance places the expected
producer in the candidate set for 96.3% of dependency slots and resolves 80.7% uniquely.
Held-out synthesized-family replay records 24 passes, 12 abstentions, and zero wrong runs.
No family reaches the configured 92-record zero-violation gate requirement, so all retire;
interpreting group records as independent remains a sampling assumption.

These are scoped results, not claims of production safety, universal equivalence,
cross-domain generalization, or state-of-the-art superiority.

## Licenses and provenance

- Repository: Apache-2.0 (`../LICENSE`).
- GitHub issue dataset: Apache-2.0 as declared by the pinned dataset card.
- NESTFUL: upstream license retained at
  `results/datasets/nestful/NESTFUL-LICENSE`.
- The public repository begins from an initial snapshot created after the experiments, so
  current versioning is available but pre-snapshot commit/CI history cannot be
  reconstructed. Dataset file provenance is independently pinned and hashed.

See `supplementary/evidence-register.md` for claim-level provenance,
`reviews/GAC_paper_review.md` for the latest artifact-aware score review, and
`paper-review.md` for the earlier adversarial self-review.
