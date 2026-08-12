# Guarded Agentic Compaction

[![CI](https://github.com/rrahimi-uci/guarded-agentic-compaction/actions/workflows/ci.yml/badge.svg)](https://github.com/rrahimi-uci/guarded-agentic-compaction/actions/workflows/ci.yml)
[![Documentation](https://github.com/rrahimi-uci/guarded-agentic-compaction/actions/workflows/pages.yml/badge.svg)](https://rrahimi-uci.github.io/guarded-agentic-compaction/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0b6e69.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-24324a.svg)](pyproject.toml)

**Compile the routine. Refuse the uncertain.**

Guarded Agentic Compaction is a research library for turning recurrent, read-only regions of
tool-using agents into deterministic guarded programs. It learns from execution traces,
but recurrence is never enough: every candidate must pass value-provenance, effect,
permission, runtime-position, replay, compatibility, and finite-sample evidence checks.
Otherwise the original agent remains unchanged.

[Documentation](https://rrahimi-uci.github.io/guarded-agentic-compaction/) ·
[Paper](paper/compiling-recurrent-agent-workflows-into-guarded-programs.pdf) ·
[Latest review](paper/reviews/GAC_paper_review.md) ·
[Adversarial review](paper/paper-review.md) ·
[Experiment verification](paper/supplementary/experiment-verification.md)

### Publication shelf

The public Pages site keeps the release easy to read without requiring a checkout:

| Read | Link |
|:---|:---|
| Complete paper in HTML | [Browser edition](https://rrahimi-uci.github.io/guarded-agentic-compaction/article.html) |
| Complete paper as PDF | [Download the paper](https://rrahimi-uci.github.io/guarded-agentic-compaction/downloads/compiling-recurrent-agent-workflows.pdf) |
| Evidence and benchmark audit | [Open the benchmark explorer](https://rrahimi-uci.github.io/guarded-agentic-compaction/benchmarks/explorer/index.html) |
| Editable presentation | [Download the technical deck](https://rrahimi-uci.github.io/guarded-agentic-compaction/downloads/gac-technical-review.pptx) |

The [artifact shelf](https://rrahimi-uci.github.io/guarded-agentic-compaction/artifacts.html)
also explains which source, evidence class, and claim boundary belongs to each item.

## Why this exists

Mature agents often spend model calls reselecting the same evidence path. A hand-written
macro can remove that overhead, but it requires a developer to discover the pattern,
reconstruct argument flow, review effects, maintain invalidation rules, and prove it still
works. Guarded Agentic Compaction automates that evidence and lifecycle path for a deliberately
narrow class of workflows.

The research contribution is **admissibility for trace-derived specialization**, not the
first agent compiler and not a claim that generated programs outperform good manual code.

## Core system

~~~mermaid
flowchart LR
  A[Application traces] --> B[Typed Episode IR]
  B --> C[Execution graph]
  C --> D[Candidate mining]
  D --> E{Provenance and effects}
  E -- unsafe or unknown --> R[Retain baseline]
  E -- qualified --> S[Bounded synthesis]
  S --> V[Replay and perturbation]
  V --> G{Exact admission}
  G -- insufficient evidence --> R
  G -- admitted --> P[Immutable guarded program]
  P --> H[Shadow]
  H --> Cn[Canary]
  Cn --> L[Live with fallback]
~~~

- **GRC — guarded region compilation:** infers readable programs from a closed
  23-operator language and emits an artifact only when its arguments are grounded and its
  effects are safe to speculate.
- **GCS — guarded composite synthesis:** projects an already admitted program behind one
  task-specific interface and may execute it before the first provider request only under
  an exact continuation-manifest pin.
- **TGWS — trace-guided workflow specialization:** learns a shallow route from entry
  state to an existing specialist prompt and minimal tool surface.
- **Portfolio selection:** compares only paired, measured actions and keeps manual macro
  recommendations review-gated.

The framework-neutral typed Episode IR separates capture from optimization. OpenAI Agents
SDK capture and runtime integration are maintained adapters, not compiler dependencies.

## What the evidence shows

The primary evaluation spans three distinct workflows over real public GitHub records,
deterministic tools on a pinned snapshot, and live provider calls. Each family has a
different tool vocabulary and exact decision contract.

| Result | Evidence | Interpretation |
|:---|:---|:---|
| Three-family total | compiled 90/90 versus baseline 89/90 (McNemar *p*=1; pooled discordance bound 3.3%); requests −66.6%; tokens −63.1%; observed wall latency −64.2%; estimated cost −58.7% | efficiency transfers across issue type, PR outcome, and backlog attention |
| Conservative GAC | 30/30 exact task contracts; requests −50.0%; tokens −39.5%; observed wall latency −51.7%; estimated cost −32.0% | a grounded two-read prefix can remove one model boundary |
| Hand-written programs | 90/90; fair pre-model programs tie learned programs on the two new families | manual code remains the practical runtime baseline |
| Aggressive GAC | 17/18 versus 18/18 for both comparators | clean program replay does not certify the final answer |
| GCS vs provider-visible macro | 12/12 each; GCS uses one versus two requests | pre-model projection removes an interface request |
| GCS vs fair pre-model manual | 6/6 each; tied requests, interfaces, and input tokens | automatic runtime superiority is not established |
| NESTFUL and API-Bank | every recurrent family retires | recurrence does not imply admissibility |
| Selective-risk levels | four artifacts at `alpha=.05`, three at `alpha=.10`, portfolio at 15% | GCS and comparator results are licensed only at 10%, not the registered 5% |
| Calibration proof scope | exact Clopper--Pearson plus 11-threshold union bound for one fixed candidate | candidate-family search is not multiplicity-adjusted; two candidates require 106 rather than 92 zero-violation groups |
| Cache accounting | macro: −30.9% tokens but only −8.0% cost at 0.0% cache reads vs. 27.8% | token reduction is not a proxy for cost reduction |
| Amortization | provider-side break-even 411 / 182 / 181 episodes per family | a shallow admitted prefix may never repay its discovery |

The artifact also preserves a revision-pinned supplementary audit of eight other agent
benchmarks. Those paths verify interoperability or explicit gates but do not demonstrate
optimizer value and are excluded from the main comparison.

These are research-prototype results from one repository snapshot. They do **not**
establish semantic equivalence, production certification, cross-repository or time-forward
generalization, or state-of-the-art quality. See the
[latest score-grounded review](paper/reviews/GAC_paper_review.md), the
[earlier adversarial review](paper/paper-review.md),
[limitations](https://rrahimi-uci.github.io/guarded-agentic-compaction/limitations.html),
and [claim audit](paper/supplementary/experiment-verification.md).

## Install

~~~bash
git clone https://github.com/rrahimi-uci/guarded-agentic-compaction.git
cd guarded-agentic-compaction
python -m venv .venv
.venv/bin/pip install -e '.[dev,live,figures]'
~~~

Python 3.11–3.14 is supported. The core library does not require MLflow or a provider
credential.

## Start with an estimate

The estimator is designed to produce a fast, inexpensive refusal before synthesis:

~~~bash
guarded-agentic-compaction estimate traces.jsonl \
  --effects configs/effects.example.yaml \
  --entry channel locale product
~~~

Compile only after the trace and effect contracts are complete:

~~~bash
guarded-agentic-compaction compile traces.jsonl \
  --effects configs/effects.example.yaml \
  --entry channel locale product \
  --out artifacts/v1

guarded-agentic-compaction explain artifacts/v1
guarded-agentic-compaction promote artifacts/v1 --stage shadow
~~~

## Python API

~~~python
import guarded_agentic_compaction as ac

episodes = ac.read_jsonl("traces.jsonl")
catalog = ac.load_catalog("configs/effects.example.yaml")

job = ac.optimize(
    episodes,
    catalog,
    algorithms=["grc", "tgws"],
    mode="offline",
    partition_by=["tenant_partition", "principal", "policy_version"],
    entry_schema=["channel", "locale"],
    sandbox=make_sandbox,
)

print(job.report())
print(job.explain())
ac.validate(job, suites=["replay", "perturbation"])
ac.promote(job, stage="shadow")
~~~

The compiler is fail-closed. Unknown effects, writes, approvals, handoffs, missing
provenance, unsupported dispatch positions, streaming boundaries, and incompatible
manifests retain the baseline.

## OpenAI Agents SDK

Capture normalized traces with the maintained tracing processor, then integrate either at
the application-owned staging boundary or through the guarded model adapter.

~~~python
from guarded_agentic_compaction.capture import (
    AgentsTraceProcessor,
    install_agents_trace_processor,
)

processor = install_agents_trace_processor(
    AgentsTraceProcessor(include_sensitive_data=False)
)
~~~

~~~python
from guarded_agentic_compaction.runtime.model_provider import CompactingModel

agent = Agent(
    name="support",
    model=CompactingModel(
        base_model,
        registry=registry,
        catalog=catalog,
        manifest=manifest,
        mode="shadow",
    ),
    tools=tools,
)
~~~

Streaming, hosted tools, incomplete handoffs, and server-managed context are rejected
rather than silently approximated. The [SDK integration guide](https://rrahimi-uci.github.io/guarded-agentic-compaction/getting-started.html#sdk)
documents the exact boundary.

## Reproduce the checked-in evidence

No API key is needed to rebuild figures, tables, paper checks, and sealed-result analyses:

~~~bash
.venv/bin/python paper/scripts/build_artifacts.py
.venv/bin/coverage run -m pytest -q
.venv/bin/coverage json -o paper/results/coverage.json
.venv/bin/python scripts/verify_release.py
.venv/bin/python paper/scripts/validate_artifacts.py
.venv/bin/python scripts/build_pages.py --output _site
~~~

`site/article.html` is the full manuscript rendered for the web, generated from
`paper/tex/body.tex` by `scripts/build_article_page.py`. That step needs
[pandoc](https://pandoc.org) and is not part of the loop above, because the Pages job
installs no third-party tooling beyond `pyyaml`. Regenerate it whenever the manuscript
changes:

~~~bash
python scripts/build_article_page.py          # rewrite site/article.html
python scripts/build_article_page.py --check  # verify it matches paper/tex/ without writing
~~~

`build_pages.py` recomputes the source digest the page carries and fails the build if the
committed article has fallen behind the manuscript, so a stale page cannot deploy.

Paid study commands are documented separately in [paper/README.md](paper/README.md).
Existing raw provider evidence is sufficient to reproduce all reported results. Local
credentials are never required for the standard test or documentation path.

## Repository map

~~~text
src/guarded_agentic_compaction/
  capture/      framework adapters and normalized Episode snapshots
  graph/        qualification, provenance, and recurrent-window mining
  grc/          DSL, synthesis, contracts, calibration, guarded composites
  tgws/         route learning and quality-anchored pruning
  portfolio/    paired evidence, exact-risk admission, reviewed selection
  evaluation/   grouped splits, replay, perturbation, metrics, statistics
  runtime/      interpreter, dispatch, staging, fallback, SDK model adapter
  registry/     immutable artifacts, lifecycle, signing, kill switch, rollback
benchmarks/     public-data adapters, manifests, gold, and external benchmark gates
demos/          simulated worlds and effect catalogs used by the offline studies
paper/          LaTeX sources, figures, tables, raw results, scripts, slides
  ICLR/         condensed conference submission (own style files and build)
  LinkedIn_Article/  practitioner write-up and its figure sources
  open_research/     compiled manuscript PDFs
site/           source for the GitHub Pages documentation
tests/          unit, property, integration, mutation, and fault-injection tests

docs/ holds deeper engineering records (ADRs, safety model, trace contract, and
library API). It is deliberately untracked -- see .gitignore -- because parts of it
are generated. The public release surface is the Pages site and the tracked paper,
benchmark, and evidence artifacts; use the [artifact shelf](https://rrahimi-uci.github.io/guarded-agentic-compaction/artifacts.html)
for the reader-facing copies.
~~~

## Contributing and security

Contributions are welcome for trace adapters, compiler checks, evaluation, runtime
controls, and documentation. Start with [CONTRIBUTING.md](CONTRIBUTING.md). Every behavior
change needs focused tests; safety-boundary changes need mutation or fault-injection
evidence. Never submit credentials, restricted traces, or customer data.

Please report vulnerabilities privately as described in [SECURITY.md](SECURITY.md).
The project follows the [code of conduct](CODE_OF_CONDUCT.md) and is licensed under
[Apache-2.0](LICENSE). Release-level changes are recorded in
[CHANGELOG.md](CHANGELOG.md).

## Citation

The manuscript is **From Traces to Guarded Programs: Evidence-Gated Compilation of
Recurrent Agent Workflows** by Reza Rahimi (JazzX AI).

| Build | Path |
| --- | --- |
| Complete article, arXiv preprint format (46 pp. incl. appendix) | `paper/open_research/article.pdf` |
| Two-column conference build (27 pp., appendix ships separately) | `paper/open_research/main.pdf` |
| ICLR submission (9 pp. + appendix) | `paper/ICLR/` (build with `tectonic --outdir build main.tex`) |

A versioned citation will be added after archival release; until then, cite the
repository commit and the paper PDF together.
