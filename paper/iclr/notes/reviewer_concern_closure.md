# Reviewer concerns: evidence and completion criteria

This ledger maps all substantive weaknesses and questions in `ICLR-1.txt`,
`ICLR-2.txt` and `ICLR-3.txt` to the current evidence. “Answered” means the local
revision supplies a supported explanation, not that a reviewer has accepted it.
No response has been posted to OpenReview. The uploaded older manuscript remains
separate from this local revision.

| Concern and reviewers | Current disposition | Evidence | What completes the work |
|---|---|---|---|
| Context before issue #4420; readable introduction (R1) | Answered in text; author review still needed | `sections/introduction.tex` defines GitHub triage and its snapshot before the example | Read the built PDF in sequence; preserve task context and distinguish an example from an evaluation cohort |
| Benchmark definitions and full references (R1); primary task requirements (R2) | Answered in text, with a narrow task interpretation | `sections/evaluation.tex`, detailed task appendix, response draft | Every benchmark has a source/release and endpoint; primary metadata/extraction tasks are not described as semantic reasoning |
| Content-addressed execution manifest (R1) | Answered in formulation | `sections/problem.tex` and manifest implementation | Explain which version/content identities it binds, what compatibility changes invalidate reuse, and why the guarantee is conditional on that environment |
| Replay versus downstream-answer loss and the 92-group label path (R1, R2) | Claim narrowed; broader empirical claim remains open | `review_response_2026-11-06.md`, calibration audit and certificate-scope table | Keep the replay-only claim explicit. Any new final-answer certificate must execute and independently grade the frozen substituted continuation, including fallback outcomes |
| Successful-trace filtering, matching-window filtering and excluded eligible records (R1, R2) | Retrospective accounting completed; population repair still open | Audit accounts for 396 records and identifies three excluded baseline failures that pass saved entry guards/gates | Sample before outcomes and family occurrence; freeze the candidate and label all eligible independently sampled groups without dropping failures or missing outcomes |
| Candidate-selection-wide 5% guarantee (R3) | Unsupported broad claim withdrawn; new evidence open | 92-group one-candidate bound 0.049809; two-candidate correction 0.056941 | Predeclare candidate/threshold multiplicity and error allocation. Pass the bound on a prospectively fixed cohort or report refusal; do not extend after observing the result |
| Independent sampling unit (R2, R3) | Limitations stated; design unresolved for the next study | Author/day sensitivity removes primary admissions | Justify a population and grouping unit before data selection. Report dependence sensitivities; variants and observations from one scenario cannot manufacture independent groups |
| Practical value beyond simple metadata retrieval and handwritten macros (R2) | Open empirical objection | Handwritten arm matches 90 contracts and request savings; retained AppWorld V1/V2 baseline pilots achieved 1/12 and 2/12 official successes, below their 8/12 development competence gate; neither compares GAC | A competent baseline on an adaptive task, a useful automatically derived recurrent region, complete discovery/rejection costs, and comparison against the same handwritten program/continuation |
| Comparison with EvoC2F / Agent JIT and interpretable external-table outcomes (R1) | External table scope clarified; matched compiler comparison open | SQL adaptation and executor parity are development evidence, not native or general compiler ranking | Pin an executable comparator, document fidelity/adaptation, validate identical tools/outputs, use the same frozen tasks/model/budgets, and report final quality and full costs |
| Individual safeguard contribution and realistic changes (R2) | Partial evidence; general benefit unestablished | Request-scope recovery works on constructed requests; recurrence-only primary replay is equally accurate and cheaper | Hold the program, compiled region, continuation and budget fixed; change one mechanism at a time. Separate ordinary tasks from prespecified stress; measure wrong dispatch, fallback, quality and recovery cost |
| Learned score versus support-only gating at two positive certified coverage levels (R2, R3) | Open; no ranking benefit claimed | Current primary cohort supports full coverage or retirement only; extension is exploratory | Freeze scoring and thresholds; use unfiltered independent calibration and a separate final population. Match coverage, risk budget and grid across gates. Report infeasibility or null results without relabeling them as benefit |
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
