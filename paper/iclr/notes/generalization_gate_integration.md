# Fresh generalization and gate-attribution integration — October 15, 2026

The canonical ICLR manuscript, abstract, local OpenReview metadata, main Results,
Discussion, Appendix K, evidence index and number registry now include the
separately frozen three-workflow/two-model comparison. No external submission
or hosted deployment is performed. Earlier long-form wrappers and slides are
not regenerated. The historical 810-episode denominator remains unchanged.

All 8,172 scheduled episodes were attempted; 8,171 completed. One baseline
provider server failure remains incorrect with its unknown charge reserved.
All GAC and adapted-AWM usage is present. Against adapted AWM, estimated
primary deployment cost falls 36.9–79.1% and requests fall 50–75% across cells.
The six-comparison exact analysis establishes the registered five-point
noninferiority margin in five of six cells. Second-model backlog is inconclusive
(142/144 versus 143/144; loss bound 5.86%). Only the two PR cells meet two points,
and no cell meets one point. This is not accuracy equality or superiority.

The full statistical, support-only and deterministic variants produce identical
routing and continuation evidence on all 2,724 frozen probes. All 2,724 live
GAC dispatch decisions match the frozen probes. This resolves the measured
runtime gate contribution as a null result on already admitted candidates;
it does not test compilation-time selection or establish universal equivalence.
The earlier learned end-to-end gate retirement is preserved.

The author audit regrades every completed answer, replays successful tool
outputs, checks frozen memories and recomputes usage. It retains 113 incorrect
or failed episodes, including one pilot error, and reports overlapping field
errors and author/day cluster sensitivity. Nonliteral source labels affect
strict grading; no outcomes are changed. The source-only screen finds no narrow
schema representability defect. Neither audit is independent human adjudication.

Limitations include one snapshot/repository, two related models, one induced
memory per cell, a generic AWM induction header with family-specific traces,
different GAC evidence placement between adapters, unknown group independence,
low backlog power, no owned backlog records and only one open primary PR.
No native AWM, compiler-only causal, new safety certificate or full lifetime
cost claim follows. The $3.864269 new observed cost includes $0.011211 induction;
aggregate estimates/reserves are $13.441321 against the existing $400 cap,
not a provider invoice or hard billing cap.

## Assessment

My diagnostic estimate is approximately **85/100**, a modest improvement from
the prior conversational estimate of 84. This is subjective, not an official
ICLR score, external review, calibrated acceptance probability or a validated
one-point measurement. Broader matched evidence and a prospective accuracy
test improve confidence; one inconclusive cell, weak branch coverage,
unverified independence and no incremental gate benefit prevent a defensible
90/100 assessment. A more favorable number cannot replace missing evidence.

## Reproduction and publication status

The protocol, pre-provider seal and immutable paid driver are retained under
`experiments/generalization_gate/` and `paper/scripts/generalization_gate_study.py`.
Run `analyze`, then `audit_results.py` and `render_manuscript.py` in the experiment
directory (with repository `PYTHONPATH=src` and its environment) to reproduce
analysis, descriptive error audit and tables. `audit_sources.py` reconstructs
the source-only screen. These post-registration helpers do not alter the
primary test, cohort, memories, endpoint or paid runtime. See the exact commands
and final validation record in `experiments/generalization_gate/VALIDATION.md`.

The paper preserves the existing ten-page revision configuration. Anonymous
artifact packaging and human author approval remain pre-upload tasks. No merge
or upload is authorized by completion of these checks.
