**[Q1] Any cohort with independent units and a selection-wide 5% bound?**
Answer: Yes, for the PR-outcome family. The three primary 92-group cohorts do not, and the revised abstract and conclusion say so. The post-cutoff cohort does: one candidate frozen before calibration (m = 1), 0 end-to-end violations in 132 fresh groups, U = 0.0173 under the single pre-registered rule (0.035 under the registered grid; 0.0267 counting its 85 distinct authors as units). The multi-repository study extends this with one PR per distinct author sampled before any outcome filter, one frozen candidate per repository, and a rule fixed before any provider call (registered grid, m = 1: admit iff U ≤ 0.05, that is k ≤ 3 at n = 200 and k ≤ 1 at n = 160):

| Repository | n | k | U | Decision |
|---|---|---|---|---|
| huggingface/datasets | 200 | 1 | 0.0333 | admit |
| pandas-dev/pandas | 200 | 2 | 0.0419 | admit |
| streamlit/streamlit | 160 | 0 | 0.0290 | admit |
| psf/requests | n/a | n/a | n/a | no run: 99 groups < 106 minimum |
| pytorch/pytorch | 200 | 0 | 0.0232 | admit (no merged class; see note) |
| Pooled, admitting repositories | 760 | 3 | 0.0133 | admit |

Amendment 3 added seven repositories at n = 400 (registered grid limit k ≤ 9). It was registered after the four results above were seen, chosen by design features only (pull-request volume, outcome-class balance, GitHub-merge share, project age, author count), and every selected repository is reported. It does not change the pooled row above.

| Repository | n | k | U | Decision |
|---|---|---|---|---|
| vercel/next.js | 400 | 1 | 0.0167 | admit |
| django/django | 400 | 2 | 0.0211 | admit |
| kubernetes/kubernetes | 400 | 3 | 0.0252 | admit |
| microsoft/vscode | 400 | 3 | 0.0252 | admit |
| godotengine/godot | 400 | 7 | 0.0399 | admit |
| nodejs/node | 400 | 14 | 0.0632 | **retire** |
| python/cpython | 400 | 17 | 0.0726 | **retire** |
| All eleven run repositories (assumes exchangeable repositories) | 3,560 | 50 | 0.0194 | admit |

Changed: Section 5.4, Table 28 and the new appendix "Unfiltered end-to-end calibration across repositories".
Evidence: `paper/results/time_forward/pr_outcome/certificate.json` (0/132); `paper/results/multirepo_end_to_end/summary.json`.
Adverse: node and cpython are retired, which is the admission rule refusing as designed. On godot the compiled arm met 6 fewer contracts than the unchanged agent (393 vs 399, McNemar p = 0.070), and the hand-written program met 395. Post hoc and descriptive only: 47 of all 50 compiled violations are evidence excerpts that are not verbatim (emoji substituted, Markdown stripped, long URLs or hashes mis-copied), 3 are titles, and none is a wrong merge outcome; we do not re-grade under a looser contract. In the registered stage the compiled arm missed 3 of 760 final contracts (hf #7768, pandas #64087 and #65856), each met by the unchanged agent. pytorch has no merged class (its bot lands PRs without merged_at), so its row is agreement with the snapshot label; without it the pooled result is 3 of 560, U = 0.0181.
Still open: Each bound is for one family on one repository's fresh PRs, conditional on independent authors; repositories are not exchangeable, so the pooled row is a separate pre-declared estimand.

**[Q2] Learned versus support-only gate at two certified coverage levels**
Answer: No. No retained cohort certifies two positive coverage levels: certifying coverage c with zero violations needs at least ⌈92/c⌉ groups, so the 92-group cohorts certify only full coverage. The sealed test of the sequential extension compares the two gates at unmatched coverage (learned routing dispatched 76/90, support-only accepts all; errors 3/90 versus 5/90, unchanged agent 2/90), which is suggestive only. The paper now claims no learned selectivity.
Changed: Section 3 Stage 6 and Section 7; Appendix H holds the prospective gate-frontier protocol that could answer this.
Evidence: `paper/results/graded_issue_gate/audit_extension.json` (3/90 learned versus 5/90 support-only).
Still open: The matched-coverage comparison is not run. We screened a single-look replication on the untouched issue pool and recorded a no-go: it holds 197 issues with a comment, which cannot supply 80 for re-derivation plus the 106-group floor. It needs a larger fresh cohort with an informative entry state and a new task specification, which did not fit the window.
