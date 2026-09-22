# ICLR 2027 revision log

Execution log for `improve-iclr.md` (Track S). One entry per task: id, files touched, numbers changed with their source key paths, verification summary.

## Baseline (2026-09-21)

- Branch `paper/iclr-2027-revision-track-s` from `main` at 5042e2f.
- Feedback archived: `paper/reviews/GAC_ICLR_2027_Detailed_Revision_Plan.{docx,md}`.
0d9af679d3f59a17605e733c51b2403b3fbb1ef6d7a8e7dd9ca7b2b04649c641  paper/iclr/build/main.pdf
8807b708aacf962850244e104d287667c961c7253970900669d0366c650a53f0  paper/open_research/main.pdf
d51a3efeceb9c1d2480f20217e20ae6aced0b18464d7c0ac21394f0456fc30eb  paper/open_research/article.pdf
686b7f09a219b3c034511db8a595bb167f7f3f31727f3f749d9ea59504221150  paper/results/publication_manifest.json
Pages:           25

## Track S execution (2026-09-22)

Tasks from `improve-iclr.md` completed on this branch; numbers cite the JSON under
`paper/results/iclr_revision/` produced by `paper/scripts/iclr_revision_statistics.py all`.

| Task | Files | What changed / numbers | Verification |
|---|---|---|---|
| T0.1–T0.2 | `paper/reviews/GAC_ICLR_2027_Detailed_Revision_Plan.{docx,md}`, this log | feedback archived; baseline hashes above | — |
| T1.1, T1.2, T2.8 | `appendix.tex` (App. H), `tables/gate_frontier_disaggregated.tex` (generated), protocol .md, `evidence-register.md`, `body.tex` | per-arm ITT accounting 240/240, 240/240, 239/240 (`gate_frontier_reanalysis.json`); #6708 support-only timeout, not retried; `psf/requests` block = reused smoke run; dispatch 160/240 (`range:pr.state`); support-only grid 12 points, U=0.0507, threshold 1.0; cohort shares 561/580 disc., 130/150 test with core (`cohort_overlap_audit.json`); "twice", not 4×/5×; $0.41 = successful attempts; decision rule cross-ref fixed | `validate_iclr_sources` |
| T1.3, T2.3 | `appendix.tex` (App. A, C), `tables/multiplicity_accounting.tex`, `main.tex` (`\crefname`), `body.tex` | m = 1 (issue-type), 2, 2; U(92, m=2)=0.0569; n_min 106; single-threshold labelling of 1.8%/13.6%; dominated candidates' tables not retained (recompile deferred, caption says so) | `multiplicity_accounting.json`; PDF has no lowercase "proposition 1" |
| T1.4, T1.5, T3.6 | `figures/alg-patg.tex`, `alg-dispatch.tex`, `alg-compile.tex`, App. B/C text, `runtime/dispatch.py`, `runtime/manual.py`, tests | slot name/value split, marks, `s<t`, `(G,S)`; runtime context `X`; `X.O ≠ ∅ → FALLBACK` implemented as `non_prefix_boundary`; `quota_attested` defined | `tests/unit/test_dispatch_prefix_boundary.py`; full suite |
| T1.6, T1.10 | sections, appendix, `pipeline_overview.tex`, `build_artifacts.py` | behavior spelling; `\ge 0.11`; Headroom families named; INSERT/…/DROP `\allowbreak`; Fig. 1 `U=0.0498 ≤ α=0.05`; `ICLR_FIGURES` casing | greps in validator |
| T1.8, T2.2 | `results.tex`, App. D tables | discordant cells 0 baseline-only / 1 compiled-only (record 5189), McNemar p=1, upper bound 3.3%; 2026-08-18 rerun 30/30; cost CIs; issue-type rows; median latency | `paired_statistics.json` |
| T2.1 | `tables/absolute_resources.tex`, App. D | per-record means/medians, all arms | `absolute_resources.json` |
| T2.4 | App. D "Latency validity" | six-permutation design; per-cell reductions 43.2%–78.6%, all positive; wall vs provider ≤0.3 pt | `order_sensitivity.json` |
| T2.5 | `tables/live_provider_manifest.tex`, App. C, Reproducibility Statement | SDK 0.19.2 / openai 2.52.0 / Py 3.14.4; settings; 120 s, no retries; concurrency; cache fields; price formula | `live_provider_manifest.json` |
| T2.6 | `tables/live_catalog.tex`, Fig. 2 barrier band | catalog digests match manifests; 2,351/2,351 tool contracts in final files; 0 undeclared raw tools | `live_catalog_audit.json` |
| T2.7, T4.5 | `results.tex` §5.2, App. F.1, `tables/multirepo_dispatch.tex` | core dispatch 80/120 (all open-class), balanced 180/180; completeness-gate disclosure; overlap wording | `gate_frontier_reanalysis.json`, `cohort_overlap_audit.json` |
| T2.9, T4.4 | `tables/effective_units.tex`, §7, App. G | primary cohorts: 86–90 distinct days, 60–82 authors; cluster-level bound retires in every family | `effective_units.json` |
| T2.10, T4.2 | `tables/mechanism_removal.tex`, §6, §7, App. G | nine sourced hazards; Headroom scoped | — |
| T3.1–T3.5 | `paper/supplementary/{multiplicity-repair,recurrence-only-ablation,graded-frontier,read-only-prologue}-protocol.md` | pre-registered / design-only; no provider call made | — |
| T4.1, T4.3 | abstract, §3, §5.1, §7, App. A/C/F.4/H | Track B certificate wording everywhere; gate = support threshold, q untested | `validate_iclr_sources` |
| T4.6 | §1, §2, §3, §4, §5.1, §5.3, §6, §7; Fig. 1 at 0.72\linewidth | conclusion ends on page 9; AI Use Statement opens page 10 | `pdftotext -f 9 -l 9`, `validate_iclr_page_budget` |
| T6.2, T6.3 | `validate_artifacts.py` (`validate_iclr_sources`), `build_artifacts.py` | new check family; casing fix | validator run |

Not done on this branch (Track R/F, require spend or a later window): T3.1 run, T3.2 run, T3.3 run,
T2.11 recompile of the pytorch retirement (code fix for full retire notes is in; recompile not run),
T2.3 step 3 recompile of the dominated candidates, T4.7 OpenReview metadata paste (user), T5.4 hostile read.
