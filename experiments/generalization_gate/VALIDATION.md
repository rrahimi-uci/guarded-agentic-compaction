# Execution and validation record

Dedicated branch: experiment/generalization-gate-ablation, based on merged PR #84
(475b8fe). No changes to main and no merge by the agent.

Provider-free preparation found 3,584 unused PRs, 811 unused issues and 150
unused backlog records before cross-family allocation and source-validity checks.
Backlog was allocated first. The final disjoint cohorts contain 1,362 source
records including 18 pilot records, shared across two models: 8,172 scheduled
agent episodes and six induction calls.

The full, support-only and deterministic dispatcher signatures agreed on all
2,724 record/model cases. PR and backlog dispatch on every selected record;
issue routing dispatches on 600/606, with the same six refusals per model in all
three variants. This supports no incremental gate benefit on these candidates,
not general equivalence or elimination of the candidate-admission requirement.

Before paid execution:
- 23 new regression tests passed, exercising all 18 family/model/arm combinations
  through the real SDK with a local fake model, partial failures, exact loss
  bounds, prospective power, balanced schedule, budget reserves and gate copies.
- New plus existing matched-study regression tests: 40 passed.
- Full suite: 662 passed, three existing optional-data skips, 177.31 seconds.
- Release validation passed (three existing untracked-docs skips); artifact validation
  passed 5,511 checks, zero failures; Pages nine pages/32 paths; wheel/sdist built.
- The post-commit verification found only JSON list versus Python tuple differences
  in compiler configuration, not candidate/program/gate changes. Canonical JSON
  digest comparison fixes this and a regression rejects actual threshold mutation.
  The unused seal is regenerated before any provider call; initial commit retained.
- Estimated budget carried forward: $8.57705193 including retained reserves.
- Standard prices verified from official OpenAI API pricing documentation on
  2026-10-15. No credentials or provider reasoning is stored.

Historical study files and numerical claims are retained. Initial preparation
seals were regenerated before any provider call as audit checks were completed;
only the committed final seal authorizes execution. A used seal is immutable.

## Completed execution and manuscript integration

The final pre-provider commit is da0e2ba0df463dbbd9b54da7423ed3b5f2eec4a0.
All 8,172 scheduled episodes were attempted with no retries or replacements:
8,171 completed and one baseline PR request returned an InternalServerError.
All six inductions completed. All 108 pilot episodes completed, 107 correct.
The frozen runtime, source cohort, candidate programs, primary endpoint and
analysis were not changed after paid execution began.

Five of six cells meet the registered 5pp noninferiority margin; second-model
backlog is inconclusive (5.86pp upper loss bound). Only the two PR cells meet
2pp; none meets 1pp. GAC uses 50–75% fewer requests and 36.9–79.1% lower estimated
deployment cost than adapted AWM. Both compared arms have complete usage.
All 2,724 live GAC dispatch decisions match the frozen probes. No incremental
runtime statistical-gate benefit is observed on these admitted candidates.

New observed cost including induction: $3.864268875; induction: $0.01121095.
Prior aggregate $8.57705193 + new observed cost + $1 new failure reserve =
$13.441320805 against the authorized $400 aggregate cap. One baseline response
has missing usage. It is not zero cost; the retained reserve is an estimate,
not proof of the unknown charge or a provider billing limit.

Post-run provider-free commands, using the existing repository environment:

```sh
export PYTHONPATH=src
python paper/scripts/generalization_gate_study.py analyze
python experiments/generalization_gate/audit_sources.py
python experiments/generalization_gate/audit_results.py
python experiments/generalization_gate/render_manuscript.py
```

All passed. The primary audit reconstructs source grading, replays successful
tool outputs, checks input/memory hashes and recomputes usage. The descriptive
post-registration audit retains 113 incorrect/failed episodes, class outcomes,
nonliteral-label caveats and author/day cluster sensitivity. No outcomes or
primary tests are changed. An additional independent calculation over raw rows
reproduced scheduled indices, arm correct counts, all six exact beta-quantile
loss bounds, complete GAC/AWM accounting and zero dispatch mismatches.

The canonical ICLR abstract, Results, Discussion, new Appendix K and generated
tables are integrated, with local OpenReview metadata, evidence register and
number registry aligned. Older long-form wrappers and slides are not rebuilt;
no hosted publication, submission, merge or reviewer approval is performed.
The manuscript retains the ten-page revision budget, not initial-submission
readiness. Anonymous supplementary packaging remains a pre-upload task.

Final publication checks:
- `/opt/homebrew/bin/tectonic --keep-logs --keep-intermediates --outdir build main.tex`
  in `paper/iclr`: compiled 51 pages, conclusion entirely on page 10, AI Use
  Statement begins page 11; no Author metadata, undefined references or
  overflowing boxes. Visual inspection of abstract, discussion/conclusion and
  new result tables found no clipping. Tectonic retains font substitutions,
  underfull-box warnings and a bibliography-change rerun-limit warning; rendered
  citations and cross-references resolve. An initial page-budget failure was
  corrected by shortening repeated prose, without altering results or layout rules.
- `python scripts/build_pages.py --output _site`: valid, nine pages / 32 paths.
- `python scripts/verify_release.py`: all checks passed; three existing checks
  of untracked generated docs skipped.
- `git diff --check`: passed.
- `python paper/scripts/finalize_manifest.py`: 1,433 retained file digests.
- `python paper/scripts/validate_artifacts.py`: 5,556 passed, zero failed.
- Rendered PDF abstract and local OpenReview metadata match after typography
  normalization; PDF contains no Author metadata.
