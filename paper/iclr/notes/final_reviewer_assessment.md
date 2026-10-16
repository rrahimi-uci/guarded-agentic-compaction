# Final reviewer-style assessment — 2026-10-16

This is an author-side critical assessment, not an independent review or an
acceptance forecast. It follows the four questions in the official
[ICLR 2027 reviewer guidelines](https://iclr.cc/Conferences/2027/ReviewerGuidelines),
checked on 2026-10-16. The supplied seven-page document is automated PAT feedback.
The complete disposition is in [pat_feedback_disposition.md](pat_feedback_disposition.md).

## Problem and motivation

The revised paper asks when recurrent initial read-only tool prefixes can be
compiled, how much model work this saves at stated quality tolerances, and which
safeguards measurably help. This is a clear systems/reliability problem. The
restriction to initial read-only prefixes is explicit in the abstract, introduction,
formalization, and runtime algorithm. AppWorld gives an unusually useful negative
result: admission need not yield deployment eligibility.

## Technical correctness and support

The exact binomial bound and fixed-grid union bound are standard and correctly
identified as such. Their applicability is conditional on frozen candidates,
a declared binary endpoint, and independent groups. Candidate-dependent stopping
cannot be justified using a post hoc count; freezing is now explicit in the
algorithm and applies per manifest partition. Two primary families remain
per-candidate at the registered risk level.

The implementation audit corrected substantive exposition defects: slot names
versus values, replay versus end-to-end loss, synthetic score-training labels and
features, search incompleteness, historical dispatch counters, and the dollar
formula. No experiment result, runtime gate, or classifier was changed to improve
the result after inspection. The helper docstring change describes existing code.

Primary and AWM comparisons support substantial request/cost savings on the
selected workflows. Accuracy claims retain their actual tolerance: 5/6 primary
AWM cells establish five-point noninferiority with six-comparison correction;
only two establish two points, none one point. The 132-record final-answer bound
is one family and selected class composition, not a general guarantee. Repeated
BIRD questions and incomplete attempts are no longer obscured by a pooled count.

## Significance and provisional recommendation

**Borderline; not a clear accept.** The strongest contribution is an auditable
compile-or-retire system with explicit refusal behavior and extensive retained
measurements. Its value is not a new confidence inequality or proven superiority
of a learned gate. The revisions improve correctness and reviewability, but do
not supply missing independent evidence. A reviewer could reasonably lean toward
acceptance for the systems/measurement contribution or rejection for limited
causal and external-validity evidence. A numerical acceptance probability would
not be calibrated by this audit.

## Remaining issues most likely to affect acceptance

1. **Incremental mechanism value.** Learned, support-only, and deterministic gates
   route identically on 2,724 selected cases. Synthetic feature increments and a
   duplicate feature weaken the case for the learned score. A new, prospectively
   sealed heterogeneous cohort with informative entry features and enough
   calibration support is needed to test incremental discrimination. More rows
   from the same constant-feature cohort will not answer that question.
2. **Comparator alignment.** Adapted offline AWM guides model execution; GAC
   removes model decisions. Its native browser setting and a compiler-placed
   comparator such as EvoC2F or Agent JIT are not evaluated. The reported savings
   cannot isolate which architectural component causes the advantage.
3. **Independent domain and ground truth.** BIRD is a useful public benchmark but
   savings depend on a fixed schema-first opening; broad workflow claims are
   unwarranted. The SEC/EDGAR integration remains preparation, not live
   cross-domain efficacy evidence. Independent human answer adjudication is not
   established by source regrading with related software.
4. **Dependence and distribution shift.** Record groups share authors, dates,
   repositories, and snapshots. Cluster sensitivity often retires the primary
   artifacts. Fresh sealed records reduce leakage but do not establish i.i.d.
   Sampling assumptions, selective exact-trace discovery, and transport to new
   snapshots remain limitations; block bootstrap or spacing is not a repair of
   the exact-binomial theorem by itself.
5. **Quality and contract scope.** Five-point noninferiority can tolerate a
   practically material loss; the smaller backlog cell is inconclusive.
   Completeness protection is unresolved; earlier drift results are null/adverse.
   Declared tool effects and the staging owner remain trusted. Replay fidelity
   does not establish semantic truth or final-answer correctness.
6. **Reproducibility and submission stage.** Model aliases are not immutable
   checkpoints, historical costs are estimates, and some external data must be
   refetched. The PDF uses the agreed ten-page revision target. The official
   [formatting rules](https://iclr.cc/Conferences/2027/AuthorGuidelines) specify
   nine pages for initial submission, ten for discussion/camera-ready. The user
   must confirm the actual upload stage/window; no OpenReview submission or
   metadata was changed. The supplement needs author review before upload.

These are evidence gaps, not prose edits silently left undone. Addressing them
requires a new protocol and/or external judgments; this revision ran no paid
provider experiment and incurred no provider spend.

## Literature and citation audit

All included source sections, tables, algorithms, figures, and bibliography were
read. Citation keys and cross-references are checked against the built document.
Claims were mapped to their source families: tracing JIT/partial evaluation for
specialization, provenance/PBE for argument synthesis, exact binomial/LTT for
risk admission, and primary benchmark papers for evaluation substrates.
No citation to a benchmark substitutes for evidence of running that benchmark.

Primary sources rechecked for the closest comparators:
[AWM](https://proceedings.mlr.press/v267/wang25bx.html),
[LLMCompiler](https://proceedings.mlr.press/v235/kim24y.html),
[plan caching](https://proceedings.neurips.cc/paper_files/paper/2025/hash/9549f7d06700f0966d5f938f1d11022a-Abstract-Conference.html),
[EvoC2F](https://proceedings.mlr.press/v306/wei26q.html), and
[Agent JIT](https://proceedings.mlr.press/v306/winston26b.html).
Published page ranges were added for the last two. The prose distinguishes
workflow guidance, plan reuse, annotated IR, and executable-plan scheduling;
it does not claim all prior methods lack verification or that GAC is first.

Recent cited preprints were checked at their primary records:
[AWO](https://arxiv.org/abs/2601.22037),
[FlowCompile](https://arxiv.org/abs/2605.13647),
[COVENANT](https://arxiv.org/abs/2607.25400),
[Agentic Compilation](https://arxiv.org/abs/2604.09718),
[CTA](https://arxiv.org/abs/2605.11946),
[prompt caching](https://arxiv.org/abs/2601.06007),
[CAPC](https://arxiv.org/abs/2607.15516), and the
[workflow survey](https://arxiv.org/abs/2603.22386).
These checks establish identity and support for the limited descriptions used;
they are not independent replications or exhaustive audits of those systems.

## Validation record

All commands ran in the dedicated worktree with Python 3.11 from the existing
`gac-edgartools-venv`, `PYTHONPATH=src`, and no provider credentials consumed.

| Check | Command / result |
|---|---|
| Full tests | `python -m pytest -q`: 666 passed, 4 skipped, exit 0. Skips are optional-environment coverage, not new experimental evidence. |
| Generated manifest table | `python paper/scripts/iclr_revision_statistics.py manifest`: table and companion JSON regenerated; full validator confirms identical regeneration. |
| Gate-floor figure | `python paper/scripts/plot_gate_floor.py`: 92/106 integer floors, unchanged arithmetic; labels now distinguish primary pools from later cohorts and empirical from population coverage. |
| PDF | From `paper/iclr/`: `tectonic --keep-logs --keep-intermediates --outdir build main.tex`. Existing local Tectonic used because the plugin binary is absent. 52 pages; sections 1–8 end on page 10; exempt AI statement starts page 11; no overfull boxes or unresolved references. |
| PDF inspection | All 52 pages rendered and inspected in contact sheets; main figures, revised grammar/score/manifest tables, and compiler pseudocode inspected at page scale. No clipped content found. The tool emits font, underfull-box and multipass warnings; these are not claimed absent. |
| Citation keys | 67 cited keys resolve against 68 bibliography entries. The unused `yoran2024assistantbench` entry is not printed. |
| Full evidence validation | `python paper/scripts/finalize_manifest.py`, then `python paper/scripts/validate_artifacts.py`: 5,622 passed, 0 failed. Publication checks cover current sources and generated artifacts; the final manifest is refreshed after the validation note. |
| Release | `python scripts/verify_release.py`: all checks passed; checks requiring untracked local `docs/` outputs are explicitly skipped by the tool. |
| Pages | `python scripts/build_pages.py --output _site`: valid, 9 pages / 32 paths. |
| Package | `python -m build`: wheel and source distribution built successfully. |
| Supplement | `python paper/scripts/build_anonymous_archive.py --out /tmp/gac-iclr2027-review.zip`: 1,319 files, approximately 116 MiB, 14 scrubbed text files; configured identifying-token scan clean. Extracted archive checksum verification: 0 mismatches. This is a candidate for author review, not a universal anonymity guarantee. |
| Archive evidence subset | Extracted archive, `PYTHONPATH` set to its own `src`: `validate_artifacts.py --families iclr_page_budget,github_workflow_families,external_benchmarks,bfcl_compiler,drift_ablation,drift_recorded_replay,time_forward_pr_outcome,bird_sql_agent,bird_extensions,drift_continuation_graded,no_secrets`: 253 passed, 0 failed. Full-repository hashes and absent third-party snapshots are intentionally outside this archive subset. |
| Whitespace | `git diff --check`: passed. |

The broader suite was not rerun merely for note edits; affected artifact and
archive checks are repeated after final packaging. PR CI is the final checkout
validation; its status and reviewer-request limitations are reported in the PR.
No runtime mechanism was changed and no result JSON was regraded or improved.
