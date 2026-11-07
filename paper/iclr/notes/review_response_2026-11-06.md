# Response draft for the three ICLR reviews

Status: author-review draft, not posted. Restructured on 2026-11-06 (plan
`flip-plans.md`, WP3 tasks 3.1 to 3.3). The reviewed PDF is retained as
`paper/reviews/openreview_submitted.pdf` (36 pages, created 2026-09-24; see
`version_gap_2026-11.md`, committed on `paper/iclr-rebuttal-base`). It has no BIRD
study, no adapted-AWM comparison and no end-to-end certificate, so the reviewers did
not have that material. Do not tell reviewers that they overlooked anything. The
supplied reviews are retained with trailing whitespace normalized under
`paper/reviews/ICLR-{1,2,3}.txt`.

How to read this file:

- Text between the `### Post:` headings and the next heading is the text to post.
  Each block is at most 4,500 characters (counts in the "Before posting" list).
- The multi-repository unfiltered end-to-end study (Strategy B,
  `paper/supplementary/multirepo-unfiltered-end-to-end-protocol.md`) is filled in from
  `paper/results/multirepo_end_to_end/summary.json`; the former placeholders and
  alternative sentences are in [`rebuttal_placeholders_2026-11.md`](rebuttal_placeholders_2026-11.md).
- Every `Changed:` line has a row in [`rebuttal_changes_2026-11.md`](rebuttal_changes_2026-11.md).
  Table and appendix numbers are those of the 2026-11-06 build of
  `paper/iclr/build/main.pdf`; recheck them against the integrator's final build.
- A [concern-by-concern ledger](reviewer_concern_closure.md) records supported
  answers, remaining experiments and explicit completion criteria. It does not claim
  reviewer agreement.

## Global summary

### Post: global summary (top-level official comment, post first)

Thank you for three careful reviews. The reviews cite the September 24 submission; since then we ran the pre-registered studies several of you asked for and revised the paper, and the OpenReview PDF diff against the September 24 version shows every change. The method and the primary results in Table 1 are unchanged.

| Study (new since September 24) | Question it answers | Where in the revised PDF |
|---|---|---|
| Post-cutoff PR-outcome with final answers graded: 0 misses in 132 fresh groups, one frozen candidate, U = 0.0173 | Do labels include the continuation? Is any bound selection-wide? (R1, R2, R3) | §5.4; App. G; Table 27 |
| Multi-repository unfiltered end-to-end calibration: one PR per author sampled before any outcome, one frozen candidate per repository; 3 misses in 760 groups across four repositories (1/200, 2/200, 0/160, 0/200; psf/requests not run), each admitted, pooled U = 0.0133 | Outcome-filtered population; independent units (R1, R2, R3) | §5.4; new appendix "Unfiltered end-to-end calibration across repositories" |
| Calibration population audit (retrospective, provider-free): 396/396 discovery records accounted for | Every excluded record, and whether the guard rejects it (R1, R2) | §4; App. G "Calibration population audit" |
| Three drift studies: 144 paired groups, 89 records, 1,080 live cells | Behavior under change (R2) | §5.4 "Mechanism evidence"; App. G |
| Live recovery, one mechanism removed at a time: 2,304 scheduled episodes | Contribution of individual safeguards (R2) | §5.4; App. I |
| Adapted offline Agent Workflow Memory: 8,172 episodes on 1,362 fresh records, two models | Comparison with an automated reuse method (R1, R2) | §5.1; Table 2; App. J, K |
| BIRD live SQL agent (schema-first opening compiles on 26/31 databases) and adaptive-task development gates (BIRD, AppWorld, AgentHop) | Work beyond metadata lookups; adaptive comparison (R2) | §5.2; App. F.5; App. L |
| Sequential issue-gate extension: 311 pooled groups and a sealed 90-issue test | Learned versus support-only gate (R3) | App. H.1 |

Scope. GAC claims a compile-or-refuse criterion: an initial read-only prefix is compiled only when every argument is grounded in observed state, every effect is declared read-only and the program starts at the agent's first step, and it is admitted only when enough calibration groups meet a finite-sample error bound. Where it admits we report measured savings (three GitHub workflows, BIRD) with replay certificates and, for PR-outcome, end-to-end certificates; where support is missing it refuses, as on NESTFUL, API-Bank and BFCL v4. GAC does not claim superiority on adaptive tasks, a benefit from the learned gate, or universal accuracy preservation. The revised abstract and conclusion state this scope.

Two requested experiments were not completed in the window: a matched competing-compiler comparison (estimated 6 to 10 working days) and a GAC versus unguarded versus handwritten comparison on an adaptive workflow (12 to 16 working days and a budget increase); the attempt record is in Appendix L and both designs are committed in the supplementary material (`matched-compiler-candidate-protocol.md`, `adaptive-quality-cost-study.md`).

## Reviewer 1

### Post: Reviewer 1, Part 1 of 2 (weaknesses)

Thank you for the detailed reading. Your five questions are answered in Part 2.

**[W1] Introduction hard to follow; issue #4420 lacks context**
Answer: Agreed. The rewritten first page defines the task before the example: "Consider GitHub issue triage, one of three workflow families we study: given an issue number from the public huggingface/datasets snapshot, the agent returns a label-based category, the issue title, and an exact evidence excerpt." Issue #4420 is one held-out record of that family, used as a worked example.
Changed: Abstract and Section 1 rewritten; three one-sentence contributions; the trajectory census is one clause pointing to Appendix F.4.
Evidence: Table 1; #4420 is one of 30 held-out issue-type records.
Still open: Nothing further is claimed.

**[W2] No cost-quality comparison with EvoC2F or Agent JIT**
Answer: We ran neither and make no ranking claim against them. EvoC2F has no inspectable implementation (its code endpoint returned HTTP 401); Agent JIT plans web tasks, and our SQL adaptation is a development probe, not a verified port; AWO has no verified public code. The executed alternative is a pre-registered comparison with adapted offline Agent Workflow Memory, new since the reviewed version. We also compared design properties as each paper states them. TraceCompiler, PreAct, EvoC2F, Agent JIT, plan caching and AWM admit artifacts by support floors, test-pass thresholds, condition checks, key matches or one evaluator-confirmed re-run. None of them states a finite-sample bound on the violation rate after admission. Several leave open arguments to a model at run time. TraceCompiler does not report how often it declines. GAC's bound is per fixed candidate, assumes exchangeable groups, and is a replay bound in most families. We also concede what these systems do that GAC does not: writes, branches and loops, steps beyond the opening of a task, online adaptation, and latency scheduling.
Changed: Section 6 and Appendix G "Scope of automated workflow-reuse comparison" explain why none is a drop-in comparator; Section 5.1 and Table 2 report the AWM study. Section 2 now states the admission contrast and cites PreAct. The Appendix G comparison table lists each system's compiled unit, admission rule, run-time open arguments and effects, with page-cited quotes in `paper/iclr/notes/compiler_comparison_2026-11.md`.
Evidence: `experiments/generalization_gate/analysis.json`: GAC meets the five-point noninferiority margin in 5/6 workflow-model cells with 50 to 75% fewer requests.
Still open: A matched compiler-policy comparison is designed (`matched-compiler-candidate-protocol.md`), not run; we estimate 6 to 10 working days.

**[W3] Table 2 hard to interpret; compiled-segment quality unclear**
Answer: Table 2 in the reviewed version (now Table 3; all four substrates in Table 19) reports refusal on trace benchmarks where no model runs: feasibility, not answer quality. Compiled-segment quality is measured where a live agent runs: Table 1 and BIRD (Section 5.2).
Changed: Plain-word columns ("grounded slots", "pass / abstain / wrong") and a one-line key in the caption.
Evidence: Table 19: NESTFUL's largest family has 26 of the 92 supporting groups required, so every family retires.
Still open: Nothing further is claimed.

**[W4] Certified loss includes answer errors; labels are replay-only**
Answer: Correct: the reviewed Section 2 counted continuation errors in the loss while the 92-group labels came from replay. We narrowed the claim to the labels: those are replay certificates, and end-to-end statements are made only where final answers were executed and graded.
Changed: Section 2 fixes the loss as "verifier-passing replay-output mismatch for the primary bound; final task-contract failure for the end-to-end study"; Section 5.4 and Table 27 separate the two.
Evidence: `paper/results/time_forward/pr_outcome/certificate.json`: 0/132 end-to-end misses on fresh post-cutoff PRs, U = 0.0173; multi-repository study: k = 3 of n = 760, U = 0.0133.
Still open: The three primary families have replay certificates only.

**[W5] Calibration population is outcome-filtered**
Answer: Confirmed: the exact-trace filter removed issues #539 and #2781 and PR #5700, and all three pass their saved artifact's entry guard and gate. The unfiltered-population claim for the primary bounds is withdrawn. The repair you suggest was run: the multi-repository study samples one PR per author before any outcome is seen and labels every eligible group, failures included.
Changed: Section 4 and Appendix G "Calibration population audit"; new appendix "Unfiltered end-to-end calibration across repositories".
Evidence: `paper/results/calibration_population_audit/report.json` (396/396 discovery records).
Still open: Issue-type and backlog routing keep the filtered population and the stated limit.

**[W6] Lifecycle: what triggers revision and renewed admission**
Answer: Implemented controls and the proposed renewal policy are now separated; Q4 gives both in full. SKILL.nb is cited.
Changed: Section 7 names the implemented controls; Appendix D paragraph "Implemented lifecycle controls and proposed renewal policy".
Evidence: `src/guarded_agentic_compaction/registry/lifecycle.py`; Q4 gives the measured case (60/60 abstentions on a new snapshot).
Still open: No failure-rate trigger, sequential guarantee or measured maintenance benefit is claimed.

### Post: Reviewer 1, Part 2 of 2 (questions)

**[Q1] Complete references for the benchmarks**
Answer: GitHub families: the pinned public snapshot `helmo/github-issues` (helmo, 2025), revision e344be7b. BIRD (Li et al., 2023a), release dev_20240627. NESTFUL (Basu et al., 2025). AppWorld gold solutions and released agent runs (Trivedi et al., 2024). API-Bank (Li et al., 2023b). BFCL v4 (Patil et al., 2025). AgentHop (Park et al., 2026), development gates only. In the main results no model runs on NESTFUL, AppWorld, API-Bank or BFCL v4; they are compiler substrates.
Changed: Section 4 cites each; Table 16 (Table 11 in the reviewed version) specifies the GitHub tasks; Appendix F.3 maps every external benchmark to its use.
Evidence: Table 19; NESTFUL supplies 1,415 traces.
Still open: Nothing further is claimed.

**[Q2] Which 92-group labels include downstream answer errors?**
Answer: None. Every 92-group label comes from `grc/compile.py::_calibration_samples`, which replays the frozen program over the group's recorded tool results and, after verifier success, compares outputs with the recorded ones; the continuation never runs. The supported loss is the replay-contract violation of the compiled region, and the guarantee is a per-candidate replay bound (0 violations in 92 groups, U = 0.0498) under i.i.d. groups from the selected population.
Changed: Section 2; Appendix C "Calibration labels as computed"; Table 6 (Table 4 in the reviewed version) and Table 27 name each certificate's event.
Evidence: answer-level misses are measured on held-out records instead: 1/270 compiled-only misses on excerpt-bearing contracts across 810 compiled episodes (Section 7).
Still open: Final-answer labels exist only for PR-outcome (W4).

**[Q3] Account for every excluded record and the guard's verdict**
Answer: Yes. Of 132 discovery records per family (396 in total), issue-type routing excludes 2 inexact runs and leaves 14 eligible records unused, PR-outcome excludes 1 and leaves 15 unused, and backlog routing excludes none and leaves 16 unused after the 16/8/92 train/development/calibration allocation. Every assigned calibration group has a matching labeled window. The three excluded records (#539, #2781, #5700) pass the saved entry guard and gate under compatible manifest pins, so the deployed guard would not reject them.
Changed: Appendix G "Calibration population audit".
Evidence: `paper/results/calibration_population_audit/report.json`, produced by `paper/scripts/audit_calibration_population.py`; 396/396 records.
Still open: These are failed baseline answers, not observed failures of a compiled continuation; the repair is in W5.

**[Q4] Triggers for recompilation or retirement; calibration before reactivation**
Answer: Implemented: rejection of any incompatible manifest (a pinned model, prompt, tool, policy, effect catalog or snapshot changes), preset expiry, explicit retirement, rollback, a kill switch and staged promotion. No implemented trigger reacts to accumulating failures or to a distribution change that passes existing guards. Proposed, not evaluated: suspend on a confirmed committed contract violation or an invalidated pin; audit outcomes and fallback rates against a prospectively specified rule; reactivate only as a new version with a declared population, frozen candidate and loss, and fresh disjoint calibration including failed baseline runs.
Changed: Appendix D paragraph "Implemented lifecycle controls and proposed renewal policy"; one sentence in Section 7.
Evidence: `paper/results/time_forward/pr_outcome/`: on a new snapshot the retained artifact abstained on 60/60 fresh test PRs, and a re-derived version was admitted only after fresh calibration on 132 groups.
Still open: Nothing beyond the proposed policy is claimed.

**[Q5] Define the content-addressed execution manifest**
Answer: Section 2 now reads: "The manifest identifies the prompt, model, tools, policies, and effect catalog by version or content digest; its compatibility pins define which execution environment an artifact may replace." It matters for the episode definition because an episode is evidence for an artifact only under a compatible manifest: dispatch requires equality on every pinned field (Eq. (3)), so a certificate does not transfer to a changed model, prompt, tool or snapshot.
Changed: Section 2 (the reviewed version named the manifest without defining it).
Evidence: Eq. (3); the 60/60 abstentions on a new snapshot in Q4.
Still open: Nothing further is claimed.

## Reviewer 2

### Post: Reviewer 2, Part 1 of 2 (weaknesses)

Thank you for the careful assessment. Weaknesses follow in your order; your three questions are answered in Part 2.

**[W1] Metadata workloads; handwritten ties; automation value unquantified**
Answer: Agreed on the workloads: the primary families are metadata classification and verbatim extraction, and the handwritten program matches them (90/90 contracts, equal requests; Table 9 in the reviewed version, now Table 14). We treat that program as the oracle: the claim is that the compiler recovers it from traces without human input where support exists and refuses where it does not, at a measured discovery cost that breaks even after 411, 183 and 181 episodes per family. The cross-repository and post-cutoff studies use PR-outcome because it is the family with enough fresh records; they test transfer and certification, not task difficulty.
Changed: New table "What the compiler decided without human input" at the start of Section 5 (admit or retire across families, repositories, models, providers and benchmarks). BIRD (Section 5.2), new since the reviewed version, adds a live agent that writes SQL after the compiled schema-first opening.
Evidence: `paper/results/bird/`: the opening compiles on 26/31 databases; on 150 sealed questions the compiled agent answers 97 and the unchanged agent 94, with 44.9% fewer requests.
Still open: The engineering value of automatic discovery over hand-writing is not quantified, and no adaptive-task advantage is claimed (Q3).

**[W2] Guards and learned gate not individually attributed; drift unexecuted**
Answer: Partly agreed, and the missing studies now exist. (a) Recurrence-only replay still ties GAC at 30/30 with one fewer request (Table 19 in the reviewed version, now Table 31); a refusal is not counted as an avoided error. (b) A live-recovery study removes one mechanism at a time over 2,304 scheduled episodes: the scope guard raises success from 186/216 to 205/216 (+8.80 points, descriptive 95% interval [3.70, 13.89]); the completeness check's benefit is unresolved (204/216 versus 205/216). (c) Drift was run three ways: provider-free (144 paired groups) and recorded replay (89 records) are null with zero wrong answers in every arm, and continuation-graded drift is adverse (39/60 wrong in both arms, 40 under the corrected grader), so the verifier bought abstention only. (d) The learned gate is no longer claimed: full statistical, support-only and deterministic routing are identical on all 2,724 record-model cases (Table 23 in the reviewed version is now Table 36).
Changed: Section 5.4 "Mechanism evidence"; Section 3 Stage 6 states that the score is implemented, every admitted operating point is full coverage, and graded selection is not claimed; Appendices G and I.
Evidence: `experiments/live_recovery_completion/analysis.json` (205/216 versus 186/216); `paper/results/drift_continuation_graded/results.json` (39/60).
Still open: Completeness-check benefit and protection under natural drift are not established.

### Post: Reviewer 2, Part 2 of 2 (questions)

**[Q1] Primary task specification; which decisions are semantic or adaptive**
Answer: Each sample is one issue or PR number from the pinned huggingface/datasets snapshot; the agent makes read-only calls and returns exact, source-grounded fields. Issue type: record, labels and comments, returning title, state, label-derived category and a verbatim excerpt. PR outcome: PR record, merge status and discussion, returning open, merged or closed_unmerged plus title and a comment excerpt. Backlog attention: open-issue record, assignees and discussion, returning owned, discussed_unowned or awaiting_first_response plus title, owner and excerpt. No decision requires semantic interpretation or adaptive branching; the model's remaining role is reading the returned evidence and writing the contract fields.
Changed: Table 16 (Table 11 in the reviewed version) and Appendix E "Primary workflow families" give the specification; Section 4 states that no decision is semantic.
Evidence: `paper/scripts/github_workflow_family_study.py` (`FAMILIES`); 30 held-out records per family (Table 1).
Still open: Nothing further is claimed for these families.

**[Q2] How calibration labels are generated; filtering before the split**
Answer: Primary families: by replaying existing trajectories. `grc/compile.py::_calibration_samples` runs the frozen program over each calibration group's recorded tool results and, after verifier success, compares outputs with the recorded ones; the continuation never runs. Discovery runs were filtered on exact traces before the 16/8/92 split (two issue-type runs and one PR run excluded), so calibration sampling followed filtering; all three excluded records pass the saved guard and gate, and the unfiltered-population claim is withdrawn. Two later studies execute the frozen prefix followed by the model continuation and grade the final contract: 132 post-cutoff PR groups (0 misses), and the multi-repository study, which samples one PR per author before any outcome or recurrence filter and labels every eligible group.
Changed: Section 2 loss definition; Appendix C "Calibration labels as computed"; Appendix G "Calibration population audit"; new appendix "Unfiltered end-to-end calibration across repositories".
Evidence: `paper/results/multirepo_end_to_end/summary.json`: k = 3 end-to-end violations in n = 760 eligible groups, U = 0.0133.
Still open: The primary replay bounds remain on the filtered population.

**[Q3] GAC vs unguarded vs handwritten on an adaptive workflow**
Answer: Not completed, and the paper's claim is scoped accordingly. Three attempts after submission stopped at prespecified development gates. BIRD: a guarded one-call candidate answered 26/36 against 28/36 for both the unchanged agent and an exact handwritten prefetch (151, 111 and 112 requests). AppWorld: adapted baselines scored 1/12 and 2/12 against an 8/12 competence gate, so no GAC arm ran. AgentHop: the baseline passed (19/24, gate 17/24), but no grounded selector for the dependent read could be derived; a posthoc ranker given the true read count matched 11/35 read batches. Two further provider-free corpus screens were no-go: in ToolHop no opening recurs in 92 queries (best 73) and an initial prefix can remove at most 1 of about 4.93 requests, which a handwritten prefetch matches; in the TraceCompiler corpora 225 of 13,500 dialogues have two calls at the first model boundary and Hermes' best opening recurs in 6 of 1,090 examples. A conclusive study needs that selector, mid-trajectory dispatch and a larger budget; we estimate 12 to 16 working days.
Changed: Appendix L "Adaptive-Task Development Gates" (new since the reviewed version) and Section 7 "Adaptive comparison and lifecycle cost".
Evidence: `paper/results/bird_one_call_matched_pilot/REPORT.md` (candidate 26/36, handwritten 28/36); `paper/results/{appworld_batched_competence,agenthop_baseline_trace_pilot,agenthop_section_lookahead}/`.
Still open: The design is committed in `paper/supplementary/adaptive-quality-cost-study.md`; no adaptive quality-cost or GAC-superiority result is claimed.

## Reviewer 3

### Post: Reviewer 3, Part 1 of 2 (weaknesses)

Thank you for the precise statistical reading. Weaknesses follow in your order; your two questions are answered in Part 2.

**[W1] Safety language exceeds the statistics (0.0569; day and author units)**
Answer: Agreed. Both limits were in the reviewed version; the revision also states them in the abstract and conclusion. Zero violations in 92 groups give U = 0.0498 for one fixed candidate and 0.0569 after correcting for the two candidates of PR-outcome and backlog routing, so a fixed two-candidate design needs 106 groups; counting creation days or authors as units retires every primary family. The new independent calibration evidence uses author units and one frozen candidate (Q1).
Changed: Abstract, Section 5.4 and Section 8; Table 4 in the reviewed version is now Table 6 (certificate level) and Table 17 is now Table 29 (grouping units).
Evidence: `paper/results/iclr_revision/multiplicity_accounting.json`: 0.0569 at 92 groups, 106 needed.
Still open: The primary cohorts keep record units and per-candidate bounds; no unit choice is claimed to be the correct one.

**[W2] No evidence that the learned gate ranks safer cases higher**
Answer: Agreed, and the revised paper no longer claims it. At 92 groups the registered grid certifies only full coverage or retirement. The score is constant within a repository whenever the entry state is a record number, and full statistical, support-only and deterministic routing are identical on 2,724 record-model cases. The one larger cohort, a sequential extension of the issue gate, selects η = 0.50 on 311 pooled groups (261/311 dispatched, 4 errors, nominal U = 0.0443), but the extension was decided after a retirement and mixes sampling frames, so it is not a certificate; at η = 0.02 the errors split 4/194 versus 0/117 (one-sided Fisher p = 0.150), no evidence of graded selectivity.
Changed: Section 3 Stage 6 presents the score as implemented, not claimed, and the admission test as a support floor; Appendix H.1. The coverage-floor figure (Figure 4 in the reviewed version) is now Figure 3.
Evidence: `paper/results/graded_issue_gate/audit_extension.json` (261/311; 4/194 versus 0/117).
Still open: See Q2.

### Post: Reviewer 3, Part 2 of 2 (questions)

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

Changed: Section 5.4, Table 27 and the new appendix "Unfiltered end-to-end calibration across repositories".
Evidence: `paper/results/time_forward/pr_outcome/certificate.json` (0/132); `paper/results/multirepo_end_to_end/summary.json`.
Adverse: the compiled arm missed 3 of 760 final contracts (hf #7768, pandas #64087 and #65856), each met by the unchanged agent, and pandas is admitted by one violation (k = 2 against a limit of 3). psf/requests was not run because the registered selection left 99 author-distinct groups. pytorch has no merged class (its bot lands PRs without merged_at), so its row is agreement with the snapshot label; without it the pooled result is 3 of 560, U = 0.0181.
Still open: Each bound is for one family on one repository's fresh PRs, conditional on independent authors; repositories are not exchangeable, so the pooled row is a separate pre-declared estimand. Counting a creation day as the unit would put pytorch (37 days) below the 92-group floor.

**[Q2] Learned versus support-only gate at two certified coverage levels**
Answer: No. No retained cohort certifies two positive coverage levels: certifying coverage c with zero violations needs at least ⌈92/c⌉ groups, so the 92-group cohorts certify only full coverage. The sealed test of the sequential extension compares the two gates at unmatched coverage (learned routing dispatched 76/90, support-only accepts all; errors 3/90 versus 5/90, unchanged agent 2/90), which is suggestive only. The paper now claims no learned selectivity.
Changed: Section 3 Stage 6 and Section 7; Appendix H holds the prospective gate-frontier protocol that could answer this.
Evidence: `paper/results/graded_issue_gate/audit_extension.json` (3/90 learned versus 5/90 support-only).
Still open: The matched-coverage comparison is not run. We screened a single-look replication on the untouched issue pool and recorded a no-go: it holds 197 issues with a comment, which cannot supply 80 for re-derivation plus the 106-group floor. It needs a larger fresh cohort with an informative entry state and a new task specification, which did not fit the window.

## Supporting detail held in reserve (not for posting)

Sentences from the earlier draft that remain true and supported but do not fit the
posted parts. Use them for follow-up replies during the discussion.

**Labels.** In `grc/compile.py::_calibration_samples`, the compiled prefix runs
against the recorded/snapshot tool environment; after verifier success, its outputs
are compared with the recorded outputs. The helper does not execute or grade the
final model continuation. The theorem applies to the prespecified measured loss
under its sampling and candidate-selection assumptions; replay labels cannot
establish a final-answer guarantee. A clean rejected attempt has zero replay loss
but its baseline continuation can still fail the final task. The primary helper does
not measure incident frequency: interpreter/verifier rejections are unproductive
events, and only verifier-passing missing/inequivalent outputs are replay
violations. The revised formulation no longer includes incidents in the primary
bound's measured endpoint.

**Post-cutoff cohort.** The 132 calibration records are 84 open and 48 merged PRs,
with no closed-unmerged records. This result concerns that population and candidate
only; it does not validate all three primary workflows or the closed-unmerged test
stratum. It must not be substituted for the primary selection-wide guarantee.

**Population audit.** For all five reconstructed candidates reaching calibration,
every assigned calibration group has a matching labeled window. No additional
family-window omission occurs within those selected calibration splits. The excluded
records are failed baseline discovery answers, not observed counterfactual GAC
failures. A new claim requires independently sampled, unfiltered calibration of a
frozen policy, not more successful traces. The audit uses the retained
selected-artifact guard/gate, because current code changes the reconstructed
issue-number hull from an interval to unrestricted integers. It reports this version
difference rather than treating recompilation as identical.

**Comparators.** The matched compiler experiment remains unrun; the paper makes no
runtime-dominance claim over handwritten or recurrence-only programs. The execution
plan requires a documented, version-pinned compiler comparator and explicit
reporting of any adaptation. The AWM comparison establishes five-point
noninferiority in five of six workflow/model cells; it does not establish the
stricter one-point margin or compiler-mechanism attribution.

**Lifecycle.** These controls do not detect all distribution changes. The proposed
policy also investigates prespecified drift/outcome alarms and freezes the revised
artifact and population before recalibration. No measured maintenance benefit or
automatic sequential risk-control guarantee is claimed.

**Mechanism attribution.** We do not interpret a refusal as an avoided error. The
live-recovery study supports request-scope checking on constructed requests, while
completeness benefit is unresolved and full GAC does not establish superiority over
baseline. These data are not evidence of general protection under natural drift.
Scores and identical routing on already-admitted artifacts do not establish risk
ranking or compilation-time selection benefit. The adaptive 311-group extension is
explicitly exploratory; it does not repair the confirmatory selective-coverage gap.

**Adaptive comparison.** We agree this is the outstanding experiment with the
largest potential to change the contribution assessment. The execution plan
separates a matched fixed-prefix mechanism comparison from a whole-compiler
comparison over a train-frozen candidate list that includes rejected candidates. It
requires task success, optimization coverage, wrong dispatches, fallback, and total
costs. A provider-free AppWorld common-entry preflight validates 12 known-correct
public sequences, 24 negative controls and 24 library-read probes through the
saved-state adapter. Authentication remains a write and its common setup is counted.
Their model traces are not a persuasive comparator for a GAC cost claim; no matched
GAC arm was run. The earlier persistence-defective attempt and its invalid original
grades remain retained separately. The BIRD candidate reduced model requests against
baseline (151 to 112) but not against the equivalent handwritten prefix (111), and it
had no calibration or independent test groups. AgentHop's public single-target
depth-2 subtype has one connected full-neighborhood source component. These are
exposed development diagnostics, not a GAC intervention or source-independent test.

**Selection-adjusted arithmetic.** At alpha = 0.05, delta = 0.10 and 11 thresholds,
zero violations among 92 groups gives 0.049809 for one fixed candidate; correcting
for two candidates gives 0.056941. A fixed prospective two-candidate design needs at
least 106 accepted zero-error groups; this arithmetic does not justify post hoc
extension. The primary issue candidate has no extra candidate multiplicity, but its
selected calibration population still prevents an unfiltered deployment claim. The
author and creation-day sensitivities demonstrate dependence on the grouping choice
rather than proving which grouping is correct. Any renewed learned-selectivity claim
requires a prospectively frozen, unfiltered cohort and a matched-coverage comparison
with separate final evaluation; if that experiment is null or infeasible, the
limitation remains rather than being hidden through a different threshold or
population.

## Before posting

- [x] Reviewed PDF retrieved and the version gap confirmed by grep
  (`paper/reviews/openreview_submitted.pdf`, `version_gap_2026-11.md`).
- [x] Responses restructured into each reviewer's order with the four-part pattern.
- [x] Completed audits, retained experiments and proposed work kept separate.
- [x] Fill every `{{B.*}}` placeholder (done 2026-11-07) from `paper/results/multirepo_end_to_end/summary.json`
  and apply the outcome sentences in `rebuttal_placeholders_2026-11.md`.
- [ ] Replace table, figure and appendix numbers with the final uploaded PDF's
  numbering (list in `rebuttal_placeholders_2026-11.md`, section "Numbering to recheck").
- [ ] Confirm every `Changed:` line against the final PDF using
  `rebuttal_changes_2026-11.md`; the abstract and conclusion must state that the
  primary 92-group cohorts carry no selection-wide 5% bound (R3 W1 and Q1).
- [ ] Number check (plan task 3.4): every number appears in `number_registry.md` and
  the PDF; the PDF wins on conflict.
- [ ] Verify the revised manuscript and supplement were actually uploaded within the
  [November 5 to 18 discussion window](https://iclr.cc/Conferences/2027/AuthorGuidelines);
  the main-text limit is ten pages and OpenReview displays a PDF diff.
- [ ] Recount characters per posted block after filling placeholders (limit used
  here: 4,500). Current counts: see `rebuttal_placeholders_2026-11.md`.
- [ ] Tone pass and author read-through (plan task 3.5).
- This file is a draft for the author. It has not been submitted to OpenReview.
