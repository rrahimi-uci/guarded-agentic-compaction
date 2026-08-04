# Architecture decision records

Short records of the decisions that shaped the implementation, including the alternatives
that were rejected and what evidence would reverse them.

| ADR | decision |
|:---|:---|
| [0001](0001-mlflow-and-sdk-as-backends.md) | MLflow and the Agents SDK are backends behind adapters, never the compiler IR |
| [0002](0002-read-only-scope.md) | v0.x compiles pre-commit reads only |
| [0003](0003-closed-dsl-and-bounded-search.md) | a closed 23-operator library with value-directed depth-2 search |
| [0004](0004-exact-calibration.md) | a fixed grid with Bonferroni-corrected Clopper–Pearson, and `RETIRE` as a normal output |
| [0005](0005-simulated-substrate.md) | simulated execution is retained only for offline stress and rare failures; superseded for user-facing demos by ADR 0008 |
| [0006](0006-partitioned-compilation.md) | the corpus is partitioned by isolation key before anything is fitted |
| [0007](0007-two-safety-endpoints.md) | artifact effect divergence and downstream write-rate shift are separate endpoints |
| [0008](0008-live-provider-demos.md) | provider-backed demos are primary; simulation remains an offline stress layer |
| [0009](0009-measured-action-portfolio.md) | select only among paired measured actions; abstain on missing evidence and require review for macros |
