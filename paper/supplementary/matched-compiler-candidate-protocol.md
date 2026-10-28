# Matched compiler comparison across candidate families

Status: **prospective design, unrun and unsealed** (2026-10-28). This document
specifies the missing comparison identified in the ICLR review. It supplies no
new experimental result, spend authorization, or statistical certificate. No
cohort has been acquired and no implementation of this full design is claimed.

## Question and relation to retained studies

Does full GAC improve the final-task quality--cost tradeoff over simpler
compilation when the comparison includes candidates it rejects?

The existing 30-record recurrence-only ablation compares different prefix lengths
and continuation packaging. `experiments/fresh_safeguards/` retains a fixed-artifact
comparison; `experiments/generalization_gate/` compares runtime admission variants
only on already-admitted programs. Neither identifies compilation-time selection
benefit across a common candidate set. Those studies remain separate evidence.

## Candidate population and splits

1. Acquire fresh, pinned public read-only task snapshots from at least three
   repositories. The exhausted historical issue pool is not a fresh cohort.
   Audit overlap against all retained `paper/results/` and `experiments/` records
   using repository-qualified identifiers, including pilots and failed runs.
2. Register source eligibility, tool/effect catalogs, task contracts, entry-state
   features, independence units, and deterministic selection seeds before provider
   execution. Source eligibility must not depend on answer correctness or dispatch.
   Exclude writes, approvals, unknown effects and cross-principal execution in every
   arm; simpler compilation is not permission to cross those boundaries.
3. Target 12 candidate families across the repositories, selected by train-only
   recurrence and a frozen ranking before GAC's grounding/contract/risk filters.
   Record the entire eligible family list. Do not replace a selected family because
   GAC rejects it, a comparator fails synthesis, or the result is unfavorable.
   If fewer than 12 exist, stop at preflight and revise the design before testing.
4. Use disjoint train, development, calibration and final-test record groups.
   Candidate identity, bindings, ranking, score, contracts and comparator settings
   must be frozen before calibration; no second candidate may be substituted after
   a calibration rejection. Assign a record to only one primary family; repeated
   models or requests do not create new independent groups.
5. Plan 300 calibration and 300 final-test groups per family. Freeze the exact
   counts before execution. A group shortage is a preflight no-go, not permission
   to reuse records or adaptively extend a failed calibration. Archive class,
   author and time composition; family/repository generalization remains a separate
   question from within-family record inference.

## Four matched policies

All arms use the same model, prompt, source tools, output schema, factual grader,
continuation interface, recovery tools, effect catalog and isolation policy.
Compiled evidence enters at the same pre-model boundary in the same format.
No arm receives a privileged oracle or loses recovery tools to make it cheaper.

| Arm | Candidate selection and execution |
|---|---|
| Unchanged agent | Baseline task agent on every scheduled record. |
| Full GAC | Standard grounding, bounded synthesis, contracts and fixed-candidate calibration; compile-time rejection or clean runtime refusal runs the baseline. |
| Support-only compiler | Same grounding, synthesis, contracts and candidate order as GAC, retaining the registered support floor but disabling learned-score/risk admission. It must run from the common candidate population, not from GAC's emitted artifacts. No risk certificate is claimed. |
| Recurrence-only compiler | Same train-only candidate windows; freeze a documented deterministic binding rule (observed source copy, otherwise majority literal with lexical tie-break). It bypasses provenance/induced-contract/risk admission but retains the common effect, position and isolation restrictions. No arbitrary generated code or side-effecting execution is permitted. |

The full-versus-support contrast measures statistical admission conditional on
shared structural checks. Full-versus-recurrence measures the whole compiler
policy, not one isolated guard. A separate same-program intervention would be
needed to attribute a difference to one structural safeguard.

Represent every family's result, including no-artifact outcomes. Log rejection
stage, candidate and program hashes, attempted prefix, actual calls, verification,
fallback and continuation evidence. Equal routing is a valid null finding.

## Endpoints and analysis fixed before the test

Primary quality is exact source-grounded final-task success over **all scheduled
records**, including baseline fallback. Failed or unattempted scheduled episodes
remain incorrect and are separately counted; missing usage is never zero cost.

For each family compare full GAC with each simpler compiler on the same 300 test
records. Report both discordant counts, paired accuracy difference, and exact
McNemar tests with Holm correction across all 24 contrasts. Report a conservative
simultaneous accuracy-loss bound using the comparator-correct/GAC-incorrect count
and one-sided Clopper--Pearson error budget 0.05/24. Five-point noninferiority is
a research tolerance, not a safety target; two- and one-point margins are declared
sensitivities. No noninferiority decision is made from incomplete attempted pairs.

Before sealing, calculate exact power curves over plausible discordance rates,
including null and adverse alternatives, and publish the resulting limitations.
The planned 300 records are not a claim of adequate power for rare harmful
dispatches or for every family. Do not enlarge the sample after seeing outcomes.

Report wrong answers after compiled dispatch both per actual dispatch and per
scheduled task, total task failures, abstentions, clean fallbacks and incidents.
Call these **wrong dispatches** unless a separate harmful-action contract is
defined in advance; ordinary factual errors are not automatically harmful acts.
Use separate calibration and evaluation confidence budgets. Any simultaneous
calibration claim across families needs a preallocated family/threshold budget;
the publication's per-candidate rule alone is not a portfolio certificate.

Resources include discovery, synthesis/calibration compute, all model requests,
tokens, local tool calls, attempted-prefix and fallback cost, latency and observed
failure usage. Report provider-price estimates separately from invoices and human
effort. Show savings versus unchanged and simpler policies, both before and after
measured setup cost. Human effort may be unmeasured but cannot silently equal zero.

Do not pool repeated records or models as independent observations. Report every
family and repository, including rejection strata, and descriptive author/day
cluster sensitivity and leave-one-repository-out results. These sensitivities do
not themselves establish independence or cross-domain generalization.

## Execution and prospective seal

Within each family, balance all 24 arm orders (300 records permit 12 complete
cycles plus 12 orders allocated by the frozen seed; report the exact imbalance).
Freeze provider settings, timeout, no-retry behavior, concurrency, missing-usage
accounting, and interrupted-call handling. Use a fresh output directory, immutable
seal and resumable ledger; a changed design requires a new study, not replacements.

The target test schedules 14,400 episodes (12 families x 300 records x four arms),
plus separately accounted discovery/development/calibration. Before any paid run,
preflight must produce the actual cohort and class counts, all compiler
dispositions, input/implementation/model/tool hashes, exact power analysis,
estimated requests and spending reserve, failure/abort rules and a numeric budget
authorized for this study. Check the real dispatcher and grading on provider-free
fixtures, including refusal and incomplete runs, before sealing.

No paid execution is authorized by this document. The current manuscript continues
to describe this comparison as unrun. Existing results must not be relabeled as
execution of this protocol.

## Decision rules

- Cheaper recurrence with comparable quality is evidence against incremental
  benefit on that family, including when GAC refuses it.
- A refusal alone is not an avoided failure; report the matched outcomes.
- A quality gain accompanied by more cost is a tradeoff, not dominance.
- A positive statistical-admission claim requires a difference in the matched
  full-versus-support policy outcomes; constant scores and identical routing are
  a null result.
- Report adverse GAC dispatches and all rejected families even if the aggregate
  result is favorable. Do not turn replay fidelity into final-answer certification.
