# Documentation map

This directory describes the implemented `agent-compaction` 0.6.0 research library.
Start here rather than treating every document as an equally current specification.

## Current developer documentation

| Document | Purpose |
|:---|:---|
| [Library API](library-api.md) | Public Python API, optimization pipeline, portfolio selector, extension points, and continuation contracts |
| [OpenAI Agents SDK](openai-agents-sdk.md) | Native trace capture and the supported runtime integration boundary |
| [Trace contract](trace-contract.md) | Application-owned fields required for sound analysis |
| [Safety model](safety-model.md) | Effect barriers, refusal semantics, staging, and limits of fallback |
| [Operations](operations.md) | Estimate, review, shadow, promotion, monitoring, incident response, and rollback |
| [Use cases](use-cases.md) | Evidence-labeled scenarios using the current API |
| [Architecture decisions](architecture/README.md) | Short records of stable design choices |
| [MLflow removal review](mlflow-removal-report.md) | Code-grounded dependency decision, custom JSONL design, trade-offs, migration, and validation |

## Evidence and research status

| Document | Evidence class |
|:---|:---|
| [Paper artifact](../paper/README.md) | Publication source, real-record/live-provider studies, public benchmark, generated tables, and reproducibility commands |
| [End-to-end repository review](gpt-5.6-report.md) | Current architecture, implementation, limitations, roadmap, and validation evidence |
| [Live SDK fixture results](live-results.md) | Real provider and SDK execution over deterministic fictional services |
| [Offline stress results](results.md) | Deterministic simulated policy/tool substrate; not provider evidence |
| [Illustrated HTML report](agent-compaction-report.html) | Generated visualization of the live SDK fixture results |
| [Related work](related-work-matrix.md) | Implemented comparators versus literature references |

The strongest current real-scenario result is the prospective portfolio pilot over 12
fresh public GitHub issues. It uses live OpenAI provider calls and deterministic tools over
a pinned public snapshot; it is not a live GitHub-service reliability test. The older live
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
```

`live-results.md` is regenerated only by a paid live fixture run. The sealed file may be
validated without repeating provider calls using `scripts/verify_release.py` and
`paper/scripts/validate_artifacts.py`.
