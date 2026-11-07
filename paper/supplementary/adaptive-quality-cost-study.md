# Adaptive quality–cost study: claim, controls and decision rules

Status: development protocol, not a confirmatory seal. The associated
[follow-up evidence](../results/adaptive_comparison_followup/REPORT.md) records
what actually ran. No result in this document establishes GAC superiority.
The later [AppWorld baseline competence study](../results/appworld_batched_competence/REPORT.md)
retains two failed 12-case development pilots (1/12 and 2/12 official successes)
after 36/36 exact-path agent-RPC controls. Its 8/12 competence gate failed;
matched GAC spending is therefore still blocked. The adapted common-entry
contract prevents a native AppWorld leaderboard interpretation.
Its posthoc trace diagnostic finds only surface API-name recurrence, without
the argument, effect and continuation evidence needed for a GAC program.

**November 6 follow-up:** the [ranked Reddit feasibility report](../results/reddit_ranked_read_feasibility/REPORT.md)
records a source-audited read, official-grader controls, a failed and an amended
batched-model pilot, and a passing one-batch handwritten reference on the
exposed task 714. The read boundary is feasible, but this candidate is a no-go
for a positive GAC quality–cost claim: the reference can prewrite the full
ranked navigation and vote in one call. No GAC artifact or matched comparison
was produced. The current manuscript's numerical claims remain unchanged.

## Separate the claims

1. **Execution value:** reduce amortized cost while preserving independently
   graded final-task quality relative to a competent agent.
2. **Admission value:** improve the quality–cost frontier relative to simpler
   recurrence/support admission over a common candidate population.
3. **Automation value:** approach strong handwritten runtime performance with
   less authoring or maintenance effort. This requires a separate measured
   engineering study. An ideal handwritten implementation can implement the same
   program, guard and continuation; automatic discovery alone does not imply
   lower execution cost than that implementation.

The existing primary handwritten and recurrence-only results remain in the
paper. New studies must not silently exclude these unfavorable comparisons.

## Reuse existing environments; do not start by inventing a benchmark

WebArena-Verified is already pinned at
`6473f72db5dcefc97b5725b59e734504edc28a21`. Its official response/HAR grading
is executable without an LLM judge. The six completed development tasks and
their entire templates are exposed. The four new templates selected in
`adaptive_comparison_followup/selection.json` are also development-only,
including when no execution follows. Neither templates nor repeated seeds are
automatically independent sampling units. Unselected tasks are only candidate
sources until their full exposure and grouping audit is complete.

The prior Reddit pilot is a competent **single-action** baseline (6/6), not a
strong batching/code baseline. The new batching interface accepts up to eight
already specified actions, preserves every intermediate observation, stops on
the first execution failure, and validates the entire batch before any action.
It does not execute arbitrary Python, invent observations, infer future arguments,
roll back writes or grant READ_EXTERNAL status to generic browser operations.
It is a basic batching control, not a replacement for an unrestricted coding
agent or a faithful Agent JIT implementation. A future live agent must receive
this interface (and comparable context/resource limits) in every relevant arm.

The source-audited GAC browser boundary still admits only the research form-open
operation before adaptive continuation. Its general browser effect remains
UNKNOWN. The current unadmitted one-call candidate is not strengthened merely
by repeating additional posting tasks. A second workflow requires a new audited
effect port, actual model traces, grounded arguments, and useful savings against
the batched baseline. Do not relax write/unknown/user-turn barriers to force it.

### AppWorld restriction discovered during research

The [pinned AppWorld README, Agent Development Restrictions](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/README.md#no_entry_sign-agent-development-restrictions)
forbids hardcoded API calls in agent logic, explicitly including login to every
app at startup. It permits prompting the agent to perform authentication.
Our common-entry controls deliberately move login into setup and are already
labeled an adaptation. They must not become standard AppWorld leaderboard
claims. Whether learned compiled API routines are permissible in a native track
needs clarification; the restriction is not evidence that every learned tool is
forbidden. An adapted compilation study must name its changed entry contract,
charge equal setup cost to every arm, and report its scores separately.

### External compiler fidelity

[Agent JIT](https://github.com/agent-jit-compilation/agent-jit-compilation)
already composes reusable tools and checks types/state contracts; its native
WebArena runner uses GitLab and Reddit and documents x86_64 Linux requirements.
Our Verified grader, emulation and bounded action tool are a different setting.
Use a pinned faithful adaptation with that difference disclosed, or run a native
replication separately. Keep tool libraries and input information equal, and
charge library construction. Do not substitute a toy checker for the full method.

[EvoC2F](https://proceedings.mlr.press/v306/wei26q.html) includes verification-gated
skill admission. Our earlier source acquisition was unsuccessful; no executable
comparison is currently available. Preserve its native verification if a faithful
implementation becomes available. Missing reproduction is a limitation, not a win.

## Two experiments, with different controls

### Whole-system comparison

Compare full GAC, unchanged batched agent, recurrence-only compilation,
support-only admission, strong handwritten workflows, and a reproducible named
compiler. Internal compiler arms start from a common train-selected candidate
population **before** GAC's rejection stages. Include rejected families and
fallbacks in all-task results. Report eligible-task results separately with their
coverage. External compilers retain their own architecture, under the same task,
information, model and resource allowances. Preserve every scheduled attempt.

Measure final-task success, all billed requests/tokens, actual tool actions,
dispatch/verifier/fallback cost, elapsed time, infrastructure failures and offline
discovery/compilation/calibration expense. Do not equate API actions with model
requests or report savings only on successful accepted episodes.

For N future tasks, report `offline_cost / N + mean_execution_cost`, cold-start
and steady-state values, and break-even workload size where defined. Include
failed staging and cleanup. Show infrastructure and engineering resources
separately; the API ledger is not an invoice or a complete labor-cost measure.

### Fixed-program mechanism comparison

Hold program, compiled region, continuation, entry information and resource
limits fixed. Vary one safeguard at a time; measure wrong dispatch, coverage,
final quality, fallback and total recovery expense. Compare learned-score versus
support-only admission at matched coverage and selection-wide risk budgets.
Test at two positive coverage levels only if a prospectively frozen calibration
supports them. Infeasibility and no improvement are valid outcomes.

Ordinary tasks are primary. Prespecified stress cases for scope changes, stale
versions, incompatible responses or missing evidence are separate diagnostic
results. Their constructed frequency cannot establish natural failure prevalence.

## Statistical decision before paid confirmation

The primary endpoint must be declared as either (a) noninferior final-task quality
plus lower total cost, or (b) higher quality at a matched cost budget. Specify the
practical quality margin, minimum useful cost reduction, multiplicity handling,
paired/clustered analysis and missing-outcome rules **before** the final run.
An insignificant accuracy difference does not establish noninferiority. A
replay/admission certificate is not a final-task quality confidence interval.

Estimate discordance and cost variability only from development material; justify
the sampling unit and calculate sample sizes before locking untouched calibration
and test groups. No numeric margin or confirmatory sample size is approved by
this document. Existing large-sample feasibility calculations are planning
sensitivities, not observed effects or proof that $300 buys adequate power.

Choose operating points on development data, then freeze them. A single favorable
point supports only that comparison; a frontier claim needs several prespecified
operating points. Report adverse results, wide intervals and unsupported regions.
This follows the emphasis on cost, holdouts and reproducible evaluation in
[AI Agents That Matter](https://arxiv.org/abs/2407.01502).

## Ordered execution gates

1. Retain previous evidence and validate the batching/grading interface with
   provider-free positive, negative and failure controls. This PR implements that
   step and a bounded metadata-selected development extension.
2. Audit a useful second read workflow and its argument grounding. The selected
   task 714 ranked-read route passed its amended source/runtime controls, but
   its one-batch handwritten reference also passed. **This particular task is a
   no-go for a positive value claim.** It is not an admitted port or discovered
   family. A new task setting requires its own explicit protocol and selection
   rules; do not mine more exposed cases for a favorable outcome.
3. Seal a bounded strong-baseline development runner, including context/action
   caps and output persistence. The AppWorld runner has 36/36 exact-path
   controls and retained V1/V2 paid attempts; both failed the 8/12 competence
   gate. Separately, Reddit task 714 has a failed first pilot and a sealed
   successful amendment; one task does **not** establish distributional
   competence or effects. Record every attempt and use the shared ledger at
   `benchmarks/.cache/adaptive_compiler_pilot/ledger.json`; never reset it.
4. Establish recurrent, useful programs; integrate matched arms; freeze candidates.
   If the selected extension fails, record that result. Any different environment
   or method extension needs an explicit new protocol, not unbounded task search.
5. Resolve fresh sampling, calibration, statistical power and affordability. Only
   then seal and run confirmation. The $300 total cap and existing stage caps
   remain binding. No new spending authorization is needed within those limits,
   but the scientific gates are not satisfied by available money.
6. Integrate only supported claims; leave PRs open for the author's merge.

If no useful grounded read region survives against a batched agent, narrow the
paper to its demonstrated contribution or explicitly develop a different method.
Do not loop between benchmarks to accumulate favorable small demonstrations.
