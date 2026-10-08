# Critical evidence review — October 8, 2026

## Assessment

**76/100: borderline for ICLR; not a confident acceptance recommendation.**
This is a diagnostic judgment, not an official ICLR score or an acceptance
probability. It supersedes the August assessment and the historical 94/100
review. The assessment follows the [ICLR reviewer criteria](https://iclr.cc/Conferences/2027/ReviewerGuidelines):
technical soundness, evidence, contribution, clarity, and reproducibility.

| Dimension | Score | Reason |
|---|---:|---|
| Technical soundness | 21/25 | The fixed-candidate, fixed-grid binomial argument is valid under its stated i.i.d. assumptions. Runtime effects and clean fallback are carefully bounded. Most certificates cover replay rather than final task quality. |
| Empirical evidence | 19/30 | Paired live results, public SQL tasks, refusals, and adverse outcomes are valuable. Selection, dependence, modest effective sample sizes, missing comparisons, and absence of a demonstrated risk–coverage frontier limit the inference. |
| Originality and significance | 14/20 | The integration of provenance, effect barriers, and statistical admission is useful systems work. The statistical result is standard; the benefit of the learned gate and the prevalence of suitable workflows remain unestablished. |
| Clarity and claim discipline | 13/15 | The revision corrects denominator handling and overclaims, separates empirical accuracy from certified risk, and removes repetitive appendix material. The appendix remains substantial because it contains many distinct studies. |
| Reproducibility | 9/10 | Retained records, source digests, deterministic tables, and validators provide strong auditability. Historical provider execution cannot be recreated exactly; raw mirrors and an anonymous submission bundle require separate preparation. |
| **Total** | **76/100** | **Editorial corrections improve reliability; they do not supply the missing experiments.** |

## Scope and method

The starting point was `origin/main` at `a97c1e1`. The primary target is
`paper/iclr/main.tex`, every included section, the complete appendix, all its
figures, tables, algorithms, and bibliography. Shared assertions and references
were also checked in the two long-form wrappers (`paper/tex/article.tex` and
`main.tex`) and their appendix. The ICLR source is the current experimental
account; the long-form article does not yet include every newer BIRD and
replication study. The README now makes that distinction explicit.

The review read the mathematical definitions and proof, inspected implementation
and grader paths, traced empirical claims to retained artifacts, recomputed
statistics, checked source metadata and primary literature, and rebuilt the
publication outputs. It did not execute new paid experiments. A passing
artifact validator establishes the checks it implements, not the truth of every
interpretation or the integrity of an external provider's historical behavior.

## Material findings and corrections

### 1. BIRD denominators excluded failures in unrelated arms — high importance

The historical summarizer intersects the completed question sets of all four
arms. Consequently, a failure in the manual comparator also deletes otherwise
valid baseline and compiled-agent outcomes from their comparison.

| Cohort | Scheduled | Historical four-arm complete | Correct unchanged | Correct compiled | Excluded executions |
|---|---:|---:|---:|---:|---|
| Primary | 150 | 150 | 94 | 97 | None |
| Rotated | 150 | 150 | 94 | 100 | None; repeats primary questions |
| Second model | 150 | 149 | 91 | 93 | Repeat-baseline timeout on codebase_community question 595 |
| Training split | 630 | 625 | 403 | 402 | Four manual timeouts in address; compiled turn-limit failure in talkingdata |

Correct counts above use every scheduled question and count a missing execution
as incorrect only in its own arm. The training discordance remains 18
baseline-only versus 17 compiled-only correct, exact McNemar p=1. The
second-model discordance is 3 versus 5, p=0.7265625. These results do not
establish equivalence or noninferiority.

`paper/scripts/audit_bird_denominators.py` reconstructs these counts from sealed
per-arm records, validates missing-run failure records, and records input
checksums. Its JSON and table are retained. Historical complete-case summaries
remain intact and are explicitly labeled. All-pair resource estimates use 629
training pairs and 150 second-model pairs; failed-run resource use is not
included, so those estimates are not total billed cost or time-to-success.

### 2. Statistical claims were stronger than the evidence — high importance

- “Matched/preserved accuracy” became observed counts and no detected loss.
  A nonsignificant paired test cannot prove equal accuracy.
- The 132-group fresh certificate now states its i.i.d. condition in the
  abstract. It covers open and merged pull requests, not closed-unmerged ones.
- Days and authors are distinct grouping units, not demonstrated independent
  units. Their bounds are hypothetical sensitivity calculations.
- Temporal spacing and block bootstrap do not automatically preserve the exact
  binomial guarantee. A cluster formulation needs independent clusters and a
  cluster-level event, and targets a different population.
- “All certificates are replay certificates” and “no study reaches 106 groups”
  contradicted the later 132-group end-to-end study. Scope is now explicit.
- Removing even two non-exact discovery traces is still selection. The
  certificate does not cover the unfiltered population.
- The claim that omitted route-deviating traces necessarily become violations
  was incorrect: replay may abstain instead, as BIRD demonstrates. The
  unexecuted counterfactual is no longer asserted.

The zero-violation calculation is correct: with alpha=.05, delta=.1, and 11
thresholds, the floor is 92 groups and U(92)=.0498. With two calibrated
candidates the corrected bound is .0569, exceeding .05; 106 groups would be
needed at zero violations. The fresh single-rule 132-group bound is .0173.
These are conditional guarantees, not evidence that source groups are i.i.d.

### 3. Method and diagram semantics needed qualification — medium importance

- An unwitnessed argument is unresolved within the bounded DSL, not proven to
  require a model decision under every possible program representation.
- The feasibility ceiling bounds requests removed by the prefix at fixed
  continuation workload. It is not a universal bound on changes in total calls.
- Ranking proxies affect candidate choice even though they do not enter the
  binomial bound.
- The architecture now shows the incident path for unattested failures or
  refused commits. It no longer depicts every runtime failure as clean fallback.
- The signature check is conditional on enforcement, matching the historical
  unsigned runs and later provider-free signing audit.
- The abstract includes observed invariant literals among argument witnesses.

### 4. Unsupported explanations and aggregate scope — medium importance

The PyTorch retirement is an observed empty calibration count, with cohort
composition a plausible explanation rather than an established cause. Ordering
consistency does not exclude provider service variance. Similar AppWorld rates
on two difficulty splits do not establish that workload has no effect. Rare
ReAct occurrences are described as rare rather than nonexistent.

The 354 distinct records belong to the 540-episode cross-repository subset,
not all 810 reported GitHub episodes. The drift result distinguishes 39 errors
under the registered grader from 40 under the later corrected grader. The
primary break-even value is 183, correcting a stale README value of 182.
The earlier 45 calibration groups were mislabeled as 45 tool calls in the
long article. Historical code-coverage figures are now dated August 5 rather
than presented as current coverage.

### 5. Citation and literature corrections — medium importance

Every original bibliography key was screened; the initial automated retrieval
obtained machine-readable title metadata for 50 of 66 unique entries. The
remaining entries were followed through primary publisher pages, original
papers, author-hosted sources, and official software/data pages. Retrieval of
metadata is not a full independent replication of a cited paper. Selected
source resolutions and version decisions are retained in
`paper/results/iclr_revision/citation_audit.json`.

- Plan caching now cites the [published NeurIPS version](https://proceedings.neurips.cc/paper_files/paper/2025/hash/9549f7d06700f0966d5f938f1d11022a-Abstract-Conference.html), with its title and three-author list. The quoted mean cost reduction changes from the old draft's 46.62% to the published 50.31%; the later arXiv version has a different author list.
- MIPRO now uses [EMNLP metadata](https://aclanthology.org/2024.emnlp-main.525/), including David Broman and Christopher Potts, who were omitted.
- TextGrad now uses the [published Nature version](https://www.nature.com/articles/s41586-025-08661-4), including Pan Lu and the 2025 publication details.
- RouteLLM's title uses “from Preference Data.” EvoC2F and Agent JIT point to their published PMLR records. BIRD points to its published version rather than combining that author list with a later arXiv revision.
- DSPy's conference landing page and PDF use different titles; the bibliography keeps the title printed in the [conference PDF](https://proceedings.iclr.cc/paper_files/paper/2024/file/f1cf02ce09757f57c3b93c0db83181e0-Paper-Conference.pdf) and links that version.
- The Jones/Gomard/Sestoft book URL was dead and is replaced with the working author-hosted location. Missing primary links were added for older references.
- The schema-first/standard prompt comparison now cites the official LangChain SQL-agent documentation.
- Related work distinguishes high-probability risk control, marginal conformal coverage, and expected monotone-loss control. Universal priority language was removed.

The provider costs remain frozen list-rate estimates, not invoices or claims
about today's prices. The BIRD release is explicitly the pinned historical
release; this selected-family experiment is not a current leaderboard score.

### 6. Appendix organization and reproducibility — medium importance

Removed the duplicate drift-protocol recap, compressed the prospective-protocol
restatement, and shortened repeated result and causal narratives. Retained the
proof, implementation details, protocols, disaggregated results, negative
findings, and source provenance. Five repetitive claim/result tables are
replaced by one compact claim-to-artifact index. The new denominator table adds evidence
that the old appendix lacked.

The initial clean-checkout artifact check had 5,133 passes and four failures:
two cluster-count tables and their JSON files could not regenerate because
raw multi-repository mirrors are excluded from Git. The statistics script
silently skipped those repositories. A retained calibration-row projection now
preserves dates and author equality keys, with source snapshot hashes checked
against the source manifests. It reproduces the original counts without
shipping the full raw mirrors. Missing records or a mismatched source digest
now fail explicitly. The projection was derived from local mirrors only after
verifying their checksums against the retained source manifests.

## What still prevents a stronger ICLR recommendation

1. **Useful selective risk control is unproven.** The principal gate acts as a
   support floor. The learned gate and support-only comparator have not shown
   a meaningful difference on the registered prospective study.
2. **Accuracy preservation needs an appropriate design.** Predeclare a
   noninferiority margin and adequate sample size, retain all scheduled runs,
   and account for repeated records and dependent groups. The current results
   permit losses as well as gains.
3. **Comparator coverage is incomplete.** Manual macros and recurrence-only
   replay are valuable, but they do not replace an automated workflow-reuse
   system evaluated on matched quality and resource endpoints. Different
   safety contracts do not make such a comparison impossible.
4. **Operational benefit under shift is unestablished.** No tested held-out
   case demonstrates that the learned guard prevents a wrong answer under the
   studied drift. Maintenance, recompilation, human review, and failed-run costs
   are not fully priced.
5. **Certification scope remains narrow.** Most bounds concern replay, two
   primary artifacts lack a .05 compiler-wide guarantee, and independence is
   assumed. The one fresh end-to-end certificate covers a restricted population.
6. **Submission preparation remains.** The current build meets the user-confirmed ten-page main-text limit.
   An anonymous artifact bundle and human author approval remain necessary. See the [official author guidelines](https://iclr.cc/Conferences/2027/AuthorGuidelines).

These gaps require evidence or submission decisions, not stronger wording.

## Validation record

All review computations were provider-free. Commands were run from the dedicated
review worktree, using its linked repository environment.

| Command/check | Result |
|---|---|
| `PYTHONPATH=src .venv/bin/python -m pytest -o addopts='' -q` | 528 passed, 3 skipped in 155.90 seconds. The skipped tests required the untracked BIRD dev cache. |
| Same pytest invocation on `paper/scripts/test_bird_sql_agent_study.py`, after connecting the pinned cache | 5 passed, including all three initially skipped tests. |
| Focused denominator/projection tests | 14 passed; comparator timeouts, compiled failure, wrong source digest, missing calibration rows, and numerical regeneration covered. |
| `PYTHONPATH=src .venv/bin/python paper/scripts/audit_bird_sql_spotchecks.py` | 10/10 retained labels reproduced: one correct and one incorrect compiled answer per primary database. Archive, nested archive, question file, and all five SQLite hashes verified. Records retained in `paper/results/bird/sql_spotcheck_audit.json`. This is sampled reexecution with the existing grader, not an independent implementation or exhaustive SQL regrade. |
| `PYTHONPATH=src .venv/bin/python paper/scripts/validate_artifacts.py` | Passed after regenerating the publication manifest; initial missing-mirror failures repaired. |
| `PYTHONPATH=src .venv/bin/python scripts/verify_release.py` | Passed; three documented checks of untracked generated `docs/` were skipped. |
| `.venv/bin/python scripts/build_article_page.py` and `.venv/bin/python scripts/build_pages.py --output _site` | Article HTML refreshed; site valid, 9 HTML pages and 32 paths. |
| `.venv/bin/python -m build --outdir /tmp/gac-audit-dist` | Wheel and source distribution built successfully. |
| `tectonic --keep-logs --keep-intermediates --outdir build main.tex` in `paper/iclr/` | Anonymous ICLR PDF rebuilt; main text ends on page 10; 41 pages total versus 46 before review. No unresolved references, overflowing boxes, or duplicate PDF destinations in the final build. |
| Corresponding Tectonic commands for `paper/tex/article.tex` and `main.tex`, output to `paper/open_research/` | Both wrappers rebuilt, 60 and 38 pages. No unresolved-reference markers. The ACM wrapper retains its existing Inconsolata font-shape substitution warnings. |
| Visual inspection | Contact sheets of every ICLR page plus larger views of changed architecture, algorithms, results, and evidence index; no clipping observed. |
| `.venv/bin/python paper/scripts/finalize_manifest.py`; `git diff --check` | Publication checksums refreshed; whitespace check passed. |

The package, source projections, historical result files, and empirical scope
are distinguished throughout. No paid/provider experiment was executed, no
reviewer attestation was changed, and this review is not external human approval.
