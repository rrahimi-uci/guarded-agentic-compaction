# Guarded Agentic Compaction paper artifact

This directory is the complete, reproducible artifact for:

> **When Traces Are Not Enough:**
> **Guarded Compilation of Tool-Using Agents**

The paper studies whether repeated model-mediated, read-only tool prefixes can be
replaced by trace-derived deterministic programs without hiding provenance, effect,
calibration, or fallback requirements. Its evidence consists of a public executable
benchmark, a pilot-separated live-provider experiment on real public records, and a
controlled suite of harder workflow shapes run through the real runtime.

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
├── results/
│   ├── datasets/                   pinned upstream snapshots and manifests
│   ├── github_live/                real-record/live-provider raw results
│   ├── github_natural_live/        free-order real-provider study and raw results
│   ├── portfolio_live/             frozen decision and prospective fresh-cohort result
│   ├── github_natural_replication/ expanded paid 30-pair replication
│   ├── multidomain/                real-record provider-free extension preflight
│   ├── nestful/                    public-benchmark raw results
│   ├── artifact_manifest.json      checksums of quantitative paper artifacts
│   └── publication_manifest.json   final source/evidence/PDF checksums
├── scripts/
│   ├── github_natural_workflow_study.py  earlier aggressive natural-order experiment
│   ├── continuation_replay.py      checked post-model replay on retained outputs
│   ├── github_live_study.py        fixed ablation and expanded natural replication
│   ├── portfolio_live_study.py     reviewed portfolio selection and prospective test
│   ├── multidomain_study.py        gated real-provider multidomain runner
│   ├── validate_multidomain.py     provider-free independent-gold validation
│   ├── nestful_benchmark.py        provider-free external benchmark
│   ├── build_artifacts.py          deterministic figures/tables
│   └── validate_artifacts.py       claim and integrity audit
├── paper-review.md                 consolidated adversarial peer review
├── supplementary/                  evidence register, audit, and rubric
│   ├── evidence-register.md        claim-level evidence boundaries
│   ├── implementation-audit.md     repository and component review
│   ├── quality-assessment.md       publication-readiness rubric
│   └── natural-live-study-protocol.md  expanded real-record experiment protocol
└── build/
    ├── article.pdf                 single-column article (page count verified after build)
    └── main.pdf                    two-column anonymous review build (page count verified after build)
```

`figures/` holds manually authored source artwork — the TikZ architecture diagram and
the four pseudocode listings; all plots are script-generated and live under
`generated_figures/`.

## Two builds, one body

`body.tex` and `abstract-body.tex` are the only places manuscript prose exists.
`article.tex` and `main.tex` are presentation wrappers that `\input` them, so the two
PDFs cannot drift apart:

| | `article.pdf` | `main.pdf` |
|:---|:---|:---|
| class | `article`, single column, A4 | `acmart[sigconf,review,anonymous]` |
| typography | Pagella text and math, Latin Modern sans/mono | ACM Libertine |
| audience | reading, circulation, archival | conference submission |
| line numbers | no | yes (review mode) |

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
- **Archived pilot:** a real-provider negative result that exposed unsafe suffix dispatch.
  It is retained under `results/github_live/pilot_2026-08-03/` and excluded from the final
  cohort.
- **Demonstration suite (Tier 3):** live provider calls and the real SDK runtime against
  deterministic local services holding *fictional* business records. It cannot support a
  claim about real-world data, and the paper never uses it for one. What it does cover is
  control-flow structure the other two tiers do not contain at all: observation-dependent
  branches, pagination, a mandatory irreversible write (so only *partial* compaction is
  reachable), a handoff barrier, an undeclared-effect MCP surface, and route
  specialization. Three of its eight conditions are negative controls whose only correct
  outcome is no compaction. Raw results are in `../experiments/live_results/`.
- **Prospective multidomain extension (preflight only):** 420 real vulnerability groups
  and 420 privacy-modified public HMDA groups pass independent provider-free gold
  reconstruction. SEC acquisition is source-gated, no three-domain protocol is frozen,
  no human macro approval exists, and no provider call has run. These artifacts establish
  data and control-plane feasibility only; they contribute no optimization result to this
  paper. See [`../benchmarks/README.md`](../benchmarks/README.md).

## Reproduce without provider calls

From the repository root:

```bash
.venv/bin/python paper/scripts/nestful_benchmark.py
.venv/bin/python paper/scripts/github_live_study.py \
    --task-design natural-extractive-v2 --evaluation-order counterbalanced \
    --include-macro --preflight-only
.venv/bin/python paper/scripts/github_live_study.py \
    --task-design natural-extractive-v2 --regrade-results \
    --results-path paper/results/github_natural_replication/results.json
.venv/bin/python paper/scripts/continuation_replay.py
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

Both logs contain no undefined citations or references. Review-mode line numbers in
`main.pdf` are intentional. Because the engine is XeTeX, the article build selects fonts
with complete `TU` coverage (Pagella via `newpx`, Latin Modern sans and mono); the Type-1
`helvet`/`tgheros` shapes have none and would silently fall back to the serif.

To re-render page images for visual inspection:

```bash
cd paper/build && pdftoppm -png -r 130 article.pdf article_pages/pg
```

## Main results

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

See `supplementary/evidence-register.md` for claim-level provenance and
`paper-review.md` for the adversarial self-review.
