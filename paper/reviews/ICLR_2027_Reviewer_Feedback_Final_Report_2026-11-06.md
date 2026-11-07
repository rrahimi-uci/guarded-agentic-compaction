# ICLR 2027 reviewer feedback: revision and remaining work

**Status on 2026-11-06:** The local manuscript and response draft incorporate the
latest retained development findings. This report describes a proposed paper
revision in an open PR. The older OpenReview upload has not been replaced or
verified here, and no response has been posted. “Addressed” means that the
paper now gives an evidence-supported answer; it does not mean that a reviewer
agrees or that the scientific objection has been resolved.

## Decision

The paper is substantially clearer and more candid about its scope. It now
separates observed request savings, replay fidelity, final-answer quality,
candidate-selection correction, and deployment-population coverage. The
latest adaptive-task studies strengthen the *diagnosis* of the remaining
comparison: a competent AgentHop baseline exists, but no qualifying derived
GAC program was found; an exact handwritten BIRD prefix matches or exceeds
the research candidate; and adapted AppWorld baselines failed their competence
gate. **There is still no independent matched result showing that GAC has a
better quality--cost trade-off than a simpler compiler or handwritten
workflow on a genuinely adaptive task.** Acceptance cannot be predicted from
this revision, and no empirical superiority claim should be added.

## Changes made for the paper and response

1. The ICLR main discussion points to a new appendix, “Adaptive-Task
   Development Gates.” The appendix reports the fixed denominators, controls,
   outcomes, source-dependence limits, and no-go decisions for BIRD,
   AppWorld, and AgentHop. The evidence index names the retained seals,
   reports, raw archive where published, and analysis code.
2. The Reviewer 2 response draft now points to the same appendix and states
   that the adaptive comparison is not complete. The concern ledger combines
   the AppWorld and AgentHop branches after their integration.
3. The earlier substantive revision already clarifies the GitHub task and
   issue #4420, benchmark references, the execution manifest, replay-only
   primary labels, the 396-record selection audit, candidate multiplicity,
   sampling-unit sensitivity, lifecycle controls, and null learned-gate
   evidence. Those explanations remain in the current manuscript and
   [reviewer response draft](../iclr/notes/review_response_2026-11-06.md).

## Reviewer-by-reviewer disposition

| Reviewer concern | Current answer | Remaining scientific gap |
|---|---|---|
| R1: introduction, benchmark descriptions, manifest | Main text now supplies task context before issue #4420, benchmark sources/endpoints, and the manifest's environment identity and compatibility role. | Author should read the rendered final PDF and verify wording and references against the actual uploaded version. |
| R1/R2: replay labels versus final-answer certificate | The 92-group primary labels check substituted tool outputs after verifier success; they do not grade the model continuation. The separate 132-group post-cutoff PR result grades final contracts for its narrow population. | An episode-level certificate for the primary deployment population requires fresh, independent calibration of the frozen substituted agent's final outcomes, including failures and fallback. |
| R1/R2: successful-trace and family-window filtering | The audit accounts for all 396 discovery records and all assigned calibration labels for the selected candidates. Three excluded inexact baseline records pass saved entry guards/gates, so an unfiltered deployment claim was withdrawn. | Sample before baseline success and region occurrence; retain and label every eligible group. Retrospective accounting does not repair the selected population. |
| R1: lifecycle and competing compilers | Implemented expiry/retirement/rollback are separated from an unevaluated renewal policy; EvoC2F and Agent JIT are discussed without a performance ranking. | Measure maintenance triggers and costs if claimed as a benefit; implement a faithful matched compiler comparator. |
| R2: practical value over simple workflows | The handwritten primary arm matches 90/90 and request savings. BIRD development: baseline 28/36, handwritten 28/36, guarded candidate 26/36; requests 151/111/112. AppWorld adapted baselines: 1/12 and 2/12 against an 8/12 gate. AgentHop baseline: 19/24 against a 17/24 gate, but no derived bridge or section selector. | Train-derived, useful multi-step state-dependent candidate; exact handwritten and simpler-compiler controls; separate calibration and final groups; all discovery/refusal/fallback and authoring costs. |
| R2: safeguard and learned-gate attribution | Recurrence-only replay ties 30/30 with fewer requests; constructed-request scope checking helps, but completeness and learned-score benefits remain unestablished. | One-mechanism-at-a-time tests on meaningful changes and a matched-coverage support-only gate comparison. |
| R3: selection-wide 5% bound and independent units | One fixed candidate's 92 zero-error groups yield 0.049809; two-candidate correction yields 0.056941, above 0.05. Author/day regrouping removes primary admissions. The abstract/conclusion state the limits. | Prospective multiplicity allocation and a defensible independence unit before data collection. More groups are useful only under that fixed design. |
| R3: two positive certified coverage levels | The 92-group primary design cannot certify the requested intermediate levels; the 311-group adaptive extension is exploratory and does not repair this. | Freeze an informative score and support-only comparator, collect sufficient independent unfiltered calibration groups, and test at equal positive coverage on a separate final population. |

The detailed row-by-row source and completion criteria are in the
[reviewer concern ledger](../iclr/notes/reviewer_concern_closure.md).

## Latest evidence and limits

- **BIRD one-call development:** All 108 scheduled three-arm episodes completed
  on 36 exposed questions. The candidate and handwritten arm received identical
  synthetic continuation inputs, but the candidate scored lower and used one
  more request. The candidate includes these exposed schemas/traces, has zero
  new calibration or independent test groups, and is not an admitted artifact.
  [Report](../results/bird_one_call_matched_pilot/REPORT.md).
- **Adapted AppWorld competence:** Both 12-case model attempts failed the
  prespecified 8/12 engineering floor after the exact-path positive/negative
  controls passed. The second changed model and prompt, so no model effect is
  inferred. No matched GAC arm was run. The earlier persistence-defective
  attempt remains separate and invalid for task-success claims.
  [Report](../results/appworld_batched_competence/REPORT.md).
- **AgentHop:** Its public exact grader, seven-tool environment, and 19/24
  local baseline make it the strongest adaptive comparator found. Its 478
  selected questions form one full-neighborhood paper-overlap component.
  The tested bridge binder failed; 42 later section-read opportunities are
  an observed timing ceiling, and a posthoc grouped ranker matched only 11/35
  entire batches even with the future read count supplied. No candidate or
  matched intervention follows. [Baseline report](../results/agenthop_baseline_trace_pilot/REPORT.md),
  [section audit](../results/agenthop_section_lookahead/REPORT.md).

The shared $300 cap is a spending ceiling, not a reason to run more exposed
development cases or to treat unqualified controls as confirmatory evidence.
The last retained campaign ledger accounts for $12.101101325 in conservative
upper estimates, leaving $287.898898675; these are not provider invoices.

**Subsequent provider-free BIRD check.** A [schema-selection probe](../results/bird_schema_selection_probe/REPORT.md)
of the same 36 exposed baseline traces found `list_tables` followed by
`get_schema` in all 36, with the schema call on the second model request.
The baseline chose 79 table occurrences from 256 listed occurrences. A
posthoc literal-name rule matched only 10/36 complete selected sets and
recovered 35/79 selected occurrences; an all-table prefetch was not executed
and would change the continuation context. This is an additional no-go for
the tested BIRD selector, not fresh evidence of GAC superiority. It made no
provider calls and did not change the campaign ledger.

## Local verification of this revision

The ICLR PDF was rebuilt from the revised LaTeX source and visually checked
at the page-10 conclusion, page-11 statements, adaptive-gates appendix and
evidence-index pages. Its main text ends on page 10; the AI Use Statement
begins page 11. The PDF still identifies only “Anonymous authors” and has no
author metadata. The full artifact validator passed **6,920 checks with zero
failures**, including the new appendix-to-report checks, BIRD schema-probe
source checks, and page-budget gate.
The full pytest suite passed with five expected skips; release checks passed
with three generated `docs/` checks skipped because that directory is
untracked; Pages validation passed for nine pages and 32 paths; and the source
distribution and wheel built successfully. The protected AgentHop raw traces
are absent from remote CI, so CI validates their retained hashes and public
aggregates rather than re-executing raw-trace parity.

## Priority order before a stronger empirical claim

1. Decide whether to keep this paper's contribution as guarded compilation
   with explicit refusal and scoped savings. That is the evidence-supported
   claim today. If the intended claim is superiority on adaptive tasks, it
   requires a method advance, not another presentation edit.
2. Derive and freeze a state-dependent multi-step candidate from separate
   training trajectories. For AgentHop, this means a grounded paper/section
   selector and a verified mid-trajectory continuation contract. The same
   selector must be available to handwritten and simpler-compiler arms.
3. Before paid matched arms, validate live tool parity, end-to-end grader
   controls, a competent unchanged baseline, a population and independent
   unit, a fixed candidate universe including refusals, full cost accounting,
   and a prospective sample-size/power decision. Stop if any gate fails.
4. Run disjoint calibration and final evaluation on the frozen design. Report
   exact final-answer quality, optimization coverage, wrong dispatch, fallback,
   model/tool/authoring costs, paired uncertainty, and negative results. Only
   then reconsider a quality--cost or selective-gate claim.

## Publication handoff

The [official ICLR 2027 author guidelines](https://iclr.cc/Conferences/2027/AuthorGuidelines)
give a November 5--18 discussion window, permit revisions through its end,
and cap discussion main text at ten pages. The revised PDF must be checked
against the actual OpenReview upload and its visible PDF diff before any
response cites the new appendix. Reviewers may ignore substantial changes.
The response draft is not posted; the upload, final author check, and PR merge
remain with the author. A passing repository QA run establishes internal
consistency and build readiness, not statistical validity or acceptance.
