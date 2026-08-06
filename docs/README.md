# Documentation map

This directory describes the implemented `guarded-agentic-compaction` 0.7.0 research library.
Start here rather than treating every document as an equally current specification.

The rendered, reader-oriented documentation is published at
[rrahimi-uci.github.io/guarded-agentic-compaction](https://rrahimi-uci.github.io/guarded-agentic-compaction/).
This directory retains the deeper engineering and research records behind that site.

## Current developer documentation

| Document | Purpose |
|:---|:---|
| [Library API](library-api.md) | Public Python API, optimization pipeline, portfolio selector, extension points, and continuation contracts |
| [OpenAI Agents SDK](openai-agents-sdk.md) | Native trace capture and the supported runtime integration boundary |
| [Guarded Composite Synthesis](guarded-composite-synthesis.md) | Composite contracts, pre-model dispatch, real validation, and limits |
| [Trace contract](trace-contract.md) | Application-owned fields required for sound analysis |
| [Safety model](safety-model.md) | Effect barriers, refusal semantics, staging, and limits of fallback |
| [Operations](operations.md) | Estimate, review, shadow, promotion, monitoring, incident response, and rollback |
| [Use cases](use-cases.md) | Evidence-labeled scenarios using the current API |
| [Architecture decisions](architecture/README.md) | Short records of stable design choices |
| [MLflow removal review](mlflow-removal-report.md) | Code-grounded dependency decision, custom JSONL design, trade-offs, migration, and validation |
| [External benchmark integration](external-benchmarks.md) | All-source BFCL, API-Bank, ToolSandbox, tau, ToolBench, AgentBench, GAIA, SWE-bench, BrowseComp, and NESTFUL dispositions and results |
| [GitHub Pages source](../site/index.html) | Professional overview, architecture, setup, research, limitations, and contribution guide |

## Evidence and research status

| Document | Evidence class |
|:---|:---|
| [Paper artifact](../paper/README.md) | Publication source, three-family real-record/live-provider study, supplementary benchmark audit, generated tables, and reproducibility commands |
| [End-to-end repository review](gpt-5.6-report.md) | Current architecture, implementation, limitations, roadmap, and validation evidence |
| [Live SDK fixture results](live-results.md) | Real provider and SDK execution over deterministic fictional services |
| [Offline stress results](results.md) | Deterministic simulated policy/tool substrate; not provider evidence |
| [Illustrated HTML report](agent-compaction-report.html) | Generated visualization of the live SDK fixture results |
| [Related work](related-work-matrix.md) | Implemented comparators versus literature references |
| [Experiment verification](../paper/supplementary/experiment-verification.md) | Claim-by-claim recomputation, statistical interpretation, and residual threats |

The strongest current real-scenario evidence is the three-family study: issue-type routing,
PR-outcome audit, and backlog-attention routing use 90 held-out public records, distinct
tools/graders, and live OpenAI provider calls over a pinned snapshot. Compiled and manual
programs both reach 90/90 exact outcomes. This is workflow-family evidence, not a live
GitHub-service, cross-repository, or time-forward reliability test. The older live
SDK suite uses fictional fixtures and is labeled accordingly. Never pool these evidence
classes or present the offline stress study as a provider benchmark.

## Historical design records

- [Execution plan](execution-plan.md) is the pre-implementation design record. Its
  numbered invariants remain useful because source comments and tests cite them, but its
  schedule and proposed APIs are not operational instructions.
- [Specification review](spec-review.md) records discrepancies discovered while turning
  the proposal and plan into code.
- [`experiments/proposal.md`](../experiments/proposal.md) is the research specification;
  the current public API is defined by source and [library-api.md](library-api.md).

The former standalone readiness checklist was removed because it duplicated—and had
drifted behind—the validation section in [gpt-5.6-report.md](gpt-5.6-report.md) and the
paper's [quality assessment](../paper/supplementary/quality-assessment.md).

## Rebuild generated documents

```bash
.venv/bin/python experiments/analysis/report.py
.venv/bin/python scripts/build_html_report.py
.venv/bin/python scripts/build_pages.py --output _site
```

`live-results.md` is regenerated only by a paid live fixture run. The sealed file may be
validated without repeating provider calls using `scripts/verify_release.py` and
`paper/scripts/validate_artifacts.py`.
