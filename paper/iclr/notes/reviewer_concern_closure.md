# Reviewer concerns: evidence and completion criteria

This ledger maps all substantive weaknesses and questions in `ICLR-1.txt`,
`ICLR-2.txt` and `ICLR-3.txt` to the current evidence. “Answered” means the local
revision supplies a supported explanation, not that a reviewer has accepted it.
No response has been posted to OpenReview. The reviewed manuscript (September 24,
36 pages) is retained as `paper/reviews/openreview_submitted.pdf` and remains
separate from this local revision. Updated 2026-11-06 for the rebuttal (plan
`flip-plans.md` WP3 task 3.3): `{{B.*}}` tokens stand for the multi-repository study's
pending numbers and are defined in `rebuttal_placeholders_2026-11.md`; day estimates
come from `flip-plans.md` Section 6.4.

| Concern and reviewers | Current disposition | Evidence | What completes the work |
|---|---|---|---|
| Context before issue #4420; readable introduction (R1) | Answered in text; author review still needed | `sections/introduction.tex` defines GitHub triage and its snapshot before the example | Read the built PDF in sequence; preserve task context and distinguish an example from an evaluation cohort |
| Benchmark definitions and full references (R1); primary task requirements (R2) | Answered in text, with a narrow task interpretation | `sections/evaluation.tex`, detailed task appendix, response draft | Every benchmark has a source/release and endpoint; primary metadata/extraction tasks are not described as semantic reasoning |
| Content-addressed execution manifest (R1) | Answered in formulation | `sections/problem.tex` and manifest implementation | Explain which version/content identities it binds, what compatibility changes invalidate reuse, and why the guarantee is conditional on that environment |
| Replay versus downstream-answer loss and the 92-group label path (R1, R2) | Answered: the 92-group tables are replay certificates and say so; end-to-end certificates exist only for PR-outcome (132 post-cutoff groups, and the multi-repository study once sealed) | `grc/compile.py::_calibration_samples` and appendix paragraph "Calibration labels as computed"; `paper/results/time_forward/pr_outcome/certificate.json` (0/132, U = 0.0173 single rule, 0.035 registered grid); `paper/results/multirepo_end_to_end/summary.json` (k = {{B.pooled.k}} of n = {{B.pooled.n}}, U = {{B.pooled.U}}) | Fill the B numbers. Keep the replay-only claim explicit for issue-type and backlog routing, which have no final-answer certificate. Any new final-answer certificate must execute and independently grade the frozen substituted continuation, including fallback outcomes |
| Successful-trace filtering, matching-window filtering and excluded eligible records (R1, R2) | Retrospective accounting completed; repair run for PR-outcome by the multi-repository study (sampled before any outcome or recurrence filter, one PR per author, every eligible group labelled, failures kept); issue-type and backlog populations remain filtered | Audit accounts for 396 records and identifies three excluded baseline failures that pass saved entry guards/gates (`paper/results/calibration_population_audit/report.json`); `paper/supplementary/multirepo-unfiltered-end-to-end-protocol.md`; per-repository n, k, U and decision in `paper/results/multirepo_end_to_end/summary.json` | Fill the B numbers and report any retirement first. For issue-type and backlog routing, sample before outcomes and family occurrence on a fresh pool (the pinned snapshot is exhausted); freeze the candidate and label all eligible independently sampled groups without dropping failures or missing outcomes |
| Candidate-selection-wide 5% guarantee (R3) | Answered for PR-outcome: one candidate frozen before calibration (m = 1) gives a selection-wide end-to-end bound on the post-cutoff cohort; the multi-repository study applies the same design per repository with a rule fixed before any provider call; the primary 92-group cohorts remain per-candidate and the broad claim stays withdrawn | 92-group one-candidate bound 0.049809; two-candidate correction 0.056941; post-cutoff 0/132, U = 0.0173 (0.035 registered grid); per-repository decisions `{{B.decision.<owner>__<repo>}}` and pooled `{{B.decision.pooled}}` | Fill the B decisions. The abstract and conclusion must say the primary cohorts carry no selection-wide 5% bound (`rebuttal_changes_2026-11.md` rows 5 and 6). Do not extend any cohort after observing its result |
| Independent sampling unit (R2, R3) | Author unit adopted prospectively for the multi-repository study (one PR per distinct `user.login`, fixed before selection); primary cohorts keep record units with their stated sensitivity | Author/day sensitivity removes primary admissions; post-cutoff cohort 0.0267 counting its 85 distinct authors (single rule); multi-repository n = {{B.pooled.n}} author-distinct groups pooled | Fill the B numbers and report distinct creation days. Independence of authors is an assumption of the design, not a result; variants and observations from one scenario cannot manufacture independent groups |
| Multi-repository unfiltered end-to-end calibration, Strategy B (R1, R2, R3) | Registered before any provider call; results pending | `paper/supplementary/multirepo-unfiltered-end-to-end-protocol.md` (committed on `paper/iclr-rebuttal-base`); results `paper/results/multirepo_end_to_end/`; pooled k = {{B.pooled.k}} of n = {{B.pooled.n}}, U = {{B.pooled.U}} | Commit all selections before any call; run calibration (n = min(200, available), run only if n >= 106); validator family `multirepo_end_to_end` passes; fill every `{{B.*}}` token; report retirements and shortfalls first; never change the rule, grid or n after a result |
| Practical value beyond simple metadata retrieval and handwritten macros (R2) | Open empirical objection | Handwritten arm matches 90 contracts and request savings; the new “Adaptive-Task Development Gates” appendix discloses BIRD 26/36 versus 28/36, AppWorld 1/12 and 2/12 below the 8/12 gate, and AgentHop 19/24 without a derived selector; Reddit task 714 has a passing batched agent and one-batch handwritten reference | A competent baseline on genuinely adaptive tasks, a useful automatically derived recurrent region, complete discovery/rejection costs, and comparison against the same handwritten program/continuation. Estimate: 12 to 16 working days plus a budget increase to roughly $1,000 for a conclusive design (Section 6.4, D2); not in the rebuttal window; protocol `paper/supplementary/adaptive-quality-cost-study.md` |
| Comparison with EvoC2F / Agent JIT and interpretable external-table outcomes (R1) | External table scope clarified; matched compiler comparison open | SQL adaptation and executor parity are development evidence, not native or general compiler ranking | Pin an executable comparator, document fidelity/adaptation, validate identical tools/outputs, use the same frozen tasks/model/budgets, and report final quality and full costs. Estimate: 6 to 10 working days (Section 6.4, D1; matched compiler policies 8 to 10); EvoC2F has no inspectable implementation; not in the rebuttal window; protocol `paper/supplementary/matched-compiler-candidate-protocol.md` |
| Individual safeguard contribution and realistic changes (R2) | Partial evidence; general benefit unestablished | Request-scope recovery works on constructed requests; recurrence-only primary replay is equally accurate and cheaper | Hold the program, compiled region, continuation and budget fixed; change one mechanism at a time. Separate ordinary tasks from prespecified stress; measure wrong dispatch, fallback, quality and recovery cost |
| Learned score versus support-only gating at two positive certified coverage levels (R2, R3) | Open; no ranking benefit claimed | Current primary cohort supports full coverage or retirement only; extension is exploratory | Freeze scoring and thresholds; use unfiltered independent calibration and a separate final population. Match coverage, risk budget and grid across gates. Report infeasibility or null results without relabeling them as benefit. Estimate: the optional single-look test (Strategy C) takes 1.5 agent-days and under $1 but certifies at most one positive level; a two-level design needs roughly 400 groups and a new task specification (Section 6, Strategy C), not in the rebuttal window. The revised paper makes no learned-gate claim |
| Retirement/recompilation triggers, hidden distribution changes and renewal (R1) | Implemented/proposed distinction answered; operational benefit unmeasured | `appendix.tex` paragraph “Implemented lifecycle controls and proposed renewal policy”, lifecycle code, response draft | State the implemented controls separately from proposed alarms. Any new monitoring claim needs a prespecified trigger, observed-outcome input, suspension behavior, new artifact version and fresh disjoint calibration before reactivation |

## What the AppWorld work changes

PR #104 corrects a direct-request persistence defect and retains the invalid original
measurements. Its controls and deterministic regrades improve evaluator reliability.
They do not close the adaptive-comparison, fresh-calibration, learned-score or
compiler-value rows above. All task material used there is exposed development data.
No manuscript result should be replaced by those diagnostics.

The [adaptive quality–cost study protocol](../../supplementary/adaptive-quality-cost-study.md)
separates execution savings, admission value and workflow-authoring effort. Its
[development follow-up](../../results/adaptive_comparison_followup/REPORT.md)
adds a bounded four-template exposure register and a batching interface with
provider-free controls. Neither is a matched adaptive GAC result. The AppWorld
rules explicitly disallow hardcoded all-app login in agent logic, so the common
entry variant remains an adapted study and cannot become a native leaderboard
claim. Future native compiled-workflow eligibility also needs clarification.

The [ranked Reddit development follow-up](../../results/reddit_ranked_read_feasibility/REPORT.md)
validates a bounded ranked-listing read and passes the official grader after a
retained failed first control. A separately sealed batched model pilot passes
task 714, but the handwritten two-action reference also passes in one batch.
The model pilot is one exposed task, and no GAC program was admitted. This
candidate does not close the practical-value, matched-comparator, or fresh-
calibration concerns.

The [completed common-entry preflight](../../results/appworld_entry_preflight/REPORT.md)
inspects the same fixed development cohort without provider calls. All 60 controls
pass: 12 known-correct direct-call sequences, 24 negative controls and 24 bounded
library-read probes. It identifies two posthoc reference-prefix hypotheses, each
seen in three scenarios, for a separately designed baseline-competence study. Authentication remains a write; moving it into identical measured setup
would define a new task-entry contract, not prove login is safe to speculate. Reference
solutions are isolated control inputs and never become model context, training traces,
automatically mined candidates or fresh evaluation observations.

The subsequent [batched baseline competence study](../../results/appworld_batched_competence/REPORT.md)
passed 36/36 provider-free reference/negative checks through the exact agent RPC
path. Its two sealed paid attempts on the same 12 exposed cases achieved 1/12
and 2/12 official successes, below the prospective 8/12 engineering gate.
Both attempts and their protected traces are retained. The stronger-model
amendment also changed the prompt, so it is not a controlled model comparison.
No GAC arm ran, no independent test group exists, and the practical-value row
remains open. The adapted preauthenticated entry also remains outside native
AppWorld leaderboard claims.
The posthoc [trace diagnostic](../../results/appworld_batched_competence/trace_diagnostic.json)
finds only API-name-level two-call prefix repetition in V2 (two groups covering
four cases); it does not establish argument grounding, read-only effects or a
compilable family. The bounded model history elided older result views in every
case, a measured interface constraint rather than a proven failure cause.

## Ordered decision gates

1. **Exact-path evaluator validity.** Known-correct public calls, empty interaction
   and false completion must be checked through the same adapter and saved-state
   grader used by every model arm. A failure blocks all paid runs.
2. **Useful workflow and source effects.** Find at least two meaningful recurrent
   read families under an explicitly bounded interface. Source audit is required;
   HTTP verbs and absence of observed SQL writes are insufficient. Count common
   initialization and preserve write/unknown barriers. If no useful region exists,
   choose a different task contract or narrow the contribution.
3. **Baseline competence.** Only after the first two gates, freeze a small development
   pilot and its limits. Retain every attempt. A floor-level baseline cannot support
   a persuasive cost/quality or mechanism comparison, even if a compiler is faster.
4. **Matched compiler feasibility.** Freeze the same candidate universe and budgets
   across GAC, simpler admission, handwritten and named-compiler arms. Validate
   implementations before outcome collection. Report rejected candidates as outcomes.
5. **Fresh statistical design.** Secure untouched groups, define the sampling unit,
   measured loss, margin, multiplicity, coverage targets and fixed sample sizes.
   Calibration and final testing have separate seals. The $300 campaign cap is a
   spending ceiling, not evidence that adequate power or independence is affordable.
6. **Claim decision.** Integrate only retained valid results. A null or adverse result
   may require a narrower contribution or venue; it is not an instruction to search
   for favorable thresholds, omit tasks or keep extending the cohort.

The manuscript, reviewer response, and this ledger must agree about which steps were
executed. Software QA, an open PR, or a passing control is not reviewer acceptance.

## AgentHop adaptive development disposition

The [source audit](../../results/agenthop_source_feasibility/REPORT.md) pins an
open citation-graph task with independent exact-answer grading, but all 478
single-target depth-2 cases belong to one full-neighborhood source component.
The [sealed baseline pilot](../../results/agenthop_baseline_trace_pilot/REPORT.md)
scored **19/24** on 24 exposed development cases, clearing its prespecified
17/24 engineering competence gate. The tested exact-text and typed-reference
binding families yielded no derived dependent program. The
[section-lookahead audit](../../results/agenthop_section_lookahead/REPORT.md)
found 42 next-turn section-read opportunities in 22 cases, but did not derive a
selector or execute a matched intervention. Its posthoc simple selectors were
weak even when given the model-selected paper; a grouped but still posthoc
ranker matched only 11/35 exact read batches even with the true read count supplied. These results establish a
competent comparator and expose a possible timing mechanism; they do not close
the practical-value, handwritten-control, matched-compiler, population-repair
or statistical-design objections. No manuscript superiority or acceptance
claim changes. PR #110 supplied the source audit, PR #111 the paid baseline and
binding result; a later provider-free timing diagnostic retained the additional
selection limitation.

## BIRD matched one-call development disposition

The [sealed three-arm result](../../results/bird_one_call_matched_pilot/REPORT.md)
completed all 108 episodes on 36 exposed questions. All candidate executions
passed guard/program/verifier and produced the same continuation messages as
the handwritten one-call arm. Baseline and handwritten each scored 28/36;
candidate scored 26/36. Candidate model requests fell from 151 to 112,
while handwritten used 111. The candidate does not outperform the simple
wrapper and has no calibration or independent test groups. It therefore
closes the mechanical continuation-feasibility step only. The practical-value,
learned-gate, matched-compiler, population-repair and statistical-design rows
remain open. The new appendix reports these development numbers without
changing a primary confirmatory result or implying acceptance.

The later [schema-selection probe](../../results/bird_schema_selection_probe/REPORT.md)
found the second read boundary in all 36 baseline cases, but a literal rule
matched only 10/36 complete selected table sets. The
[T-v1 binder audit](../../results/bird_binder_expressivity_audit/REPORT.md)
found no exact expression for those selected sets, including the 35 cases with
only listed tables; a list-identity positive control passed. Both are posthoc
function-level development results. Neither supplies a derived useful GAC
candidate, matched final-answer comparison, or independent test.
