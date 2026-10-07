# proposal-90.md — Feasibility review and staged revision plan

Reviewed 2026-10-02 against checkout `71574c6`, the ICLR manuscript source,
calibration/compiler code, retained effective-unit and multidomain preflight artifacts,
existing study protocols, runner interfaces, and official ICLR 2027 guidance. This revision
assesses and corrects the plan; it does not implement the workstreams or run new studies.

Re-reviewed 2026-10-06 against `054dbb8` (main after PR #50). Every code, artifact and
arithmetic reference below was re-verified; the ICLR 2027 author guidelines were re-fetched;
the pinned dataset's Hugging Face revision was checked. Changes in this pass: the ten-page
discussion allowance (F13), the time-forward data source (F7), the Copilot rule (F12), the
contents of the retained traces (F14), the absence of an external human read (F15), a
rebased schedule, and an explicit ordering of what can land before reviews (§0.1).

## 0. Assessment

**The direction is reasonable; the original five-week, part-time, under-$100 promise for
all workstreams was not established.** Correct the certified-event wording and improve
presentation first. Then implement a small provider-free mechanism study. Treat fresh
cohorts, end-to-end certification, and a second live domain as conditional extensions.

The original 76-to-90+ scores are editorial judgments, not measured acceptance probabilities
or official ICLR scores. A strong artifact and useful new results can improve the paper,
but no task list or positive experiment guarantees a clear accept. Keep the filename as a
planning identifier; use the evidence milestones below to judge completion.

| Scope | Feasibility | Completion evidence |
|---|---|---|
| Correct statistical scope, preserve registered results, improve writing | High; approximately 7–12 focused person-days | Consistent event definitions, evidence-linked claims, valid builds and checks |
| Provider-free verifier ablation and recorded-trace extension | Moderate; approximately 4–7 additional person-days | Validated perturbation oracles, paired outcomes, null/adverse results retained |
| Fresh time-forward cohort and end-to-end labels | Conditional and post-decision; approximately 6–10 additional person-days after a GitHub API acquisition GO (the pinned dataset cannot supply it; F7) | Compatible source, disjoint frozen splits, prospective labels and multiplicity accounting |
| HMDA live study | Conditional; approximately 6–10 additional person-days after protocol and approval GO | Existing frozen design honored, action locks, budget ledger, validated results |
| Manual-authoring pilot | Optional; recruitment and participant time extra | Separate development/test records, timed logs, descriptive limitations |

These are planning ranges, not measured delivery estimates. The full scope is roughly
23–39 focused person-days before participant time and integration contingency. Five
calendar weeks is plausible for a bounded core, not a reliable part-time commitment to
all extensions. A $100 provider cap is a constraint that may force studies to stop or defer.

### 0.1 Ordering for the review window (added 2026-10-06)

Working days from 2026-10-06: 22 to the review release on November 5 and 31 to the end of
discussion on November 18. ICLR applies a pdfdiff to every revision and reviewers are not
required to read every upload, so plan one consolidated revision with a change list, not a
stream of uploads.

Only the P0 core (A1, B1, B2, C1a, E, F, G) and the provider-free part of C1b fit before
November 5, at roughly 10–15 focused person-days. Availability below about 60% of a working
week leaves no room for any conditional extension. In order of expected effect on a
reviewer's score per person-day:

1. **A1.** The certified-event mismatch is the one finding a reviewer can read as an unsound
   claim. Correcting it is a clarification of the submitted paper, which is the kind of change
   reviewers are asked to assess rather than ignore.
2. **E, F and the tenth page.** ICLR allows ten main-text pages during discussion (F13). The
   results figure (E4), the related-work expansion (WS-F) and the scope wording from A1 fit in
   that page without the appendix diet; keep E5 to the reading guide and terminology.
3. **C1a, then provider-free C1b.** The only new evidence that fits. The protocol's own most
   likely outcome on the demo substrate is a null (all arms zero wrong); the recorded GitHub
   records in C1b are the part reviewers will weigh, so write its protocol in the same week.
4. **B1 and G.** Arithmetic and statistical wording; about a day each; no new evidence.
5. **Everything conditional** (A2 confirmatory, B3, C2, D1, H) is post-decision work. None of
   it completes before November 18 beside the core, and a method or cohort change of that
   size is what area chairs may ignore. Write their protocols only if the core is finished by
   October 30. The one cheap exception: an exploratory end-to-end label on the retained
   issue-type calibration groups (one continuation per group, about a dollar) answers the
   "what would k have been" question in a response; label it exploratory and claim nothing.

No version of this plan yields a measured score. The 90 in the filename comes from the
repository's own artifact-aware rubrics. The only reviewer-rubric score on file is 7/10
(weak accept) from the 2026-08-21 scorecard, and the five files under `team-reviews/` are
untouched templates (F15). One independent human read of the nine pages before November 5,
scored on the official ICLR questions, is the cheapest calibration of that number and should
be scheduled now.

## 1. Findings verified for this revision

The strongest existing direction remains evidence-gated compilation of recurrent read-only
prefixes: recurrence proposes; provenance, effects, position and continuation constraints
limit substitution; otherwise the system refuses or falls back. Keep manual-comparator
parity, the distinction between admission and runtime dispatch, and negative results visible.

| ID | Finding and evidence | Required correction |
|---|---|---|
| F1 | `paper/iclr/sections/problem.tex` says a downstream continuation error enters the certified loss. `_calibration_samples` in `grc/compile.py` only sets the clean calibration `violation` flag on missing or unequal recorded outputs after successful interpretation and verifier acceptance. | Align the theorem's instantiated event with the labels actually used. Downstream correctness is measured separately. |
| F2 | The original plan incorrectly included `verifier:*` among counted violations. Verifier rejection sets `unproductive=True`, leaves `violation=False`, and represents abstention. `calibrate_gate` counts groups admitted by entry eligibility and score, including attempts that later abstain. | Preserve this numerator/denominator distinction; do not describe the bound as conditional on verifier success. |
| F3 | Single-threshold arithmetic reduces the multiplicity penalty, but choosing that rule after inspecting the retained runs is retrospective. | Keep original grid certificates and per-candidate qualifications; label the alternative as sensitivity only. |
| F4 | Effective-unit calculations count distinct days/authors; they do not establish independent identically distributed groups. Mere exchangeability is insufficient for the binomial model used by Clopper–Pearson. | Retain the i.i.d. assumption; describe cluster calculations as sensitivity unless a prospective cluster sampling model is justified. |
| F5 | The existing drift protocol is provider-free, uses simulated workloads and three arms, and explicitly says its driver is unwritten. Its oracle concerns program outputs, not downstream answer correctness. | Implement that bounded study first; version any real-record or live extension separately. |
| F6 | Nine perturbations on the same record do not create nine independent records. Several generic transforms may alter a GitHub task's truth or do nothing. | Validate applicability and task semantics; aggregate the primary contrast at record/group level. |
| F7 | `github_workflow_family_study.py` is tied to `fixed.HF_REVISION` and has no `--snapshot` or `--frozen-artifact` interface. Checked 2026-10-06: the pinned Hugging Face dataset `helmo/github-issues` has had no revision since 2025-06-13 (its current sha is the pinned one) and holds one repository's records through that day, so refreshing it cannot yield newer records. `github_multirepo_preflight.py` already accepts repeated `--snapshot` parquet paths and audits `created_at` day ranges. | Treat C2 as GitHub API acquisition with an explicit creation cutoff after 2025-06-13, loaded through the multirepo snapshot path with its own digest, licence note and gold reconstruction; not a dataset refresh. Budget it after decisions. |
| F8 | HMDA preflight validates 420 groups and 416 variable paths, but reports `protocol: null` and zero provider calls. The manifest allocates five study roles, unlike the original plan's three-way split. | Honor the existing design or explicitly version and refreeze a replacement before outcomes are observed. |
| F9 | A verifier-null result, a domain retirement, and a live quality improvement answer different questions. | Do not award predetermined score gains or describe a refusal as evidence of live quality/savings. |
| F10 | The proposed uncommitted second-provider protocol anomaly is absent in this checkout. Initial status contains only untracked `.claude/`. | Remove that stale blocker and preserve unrelated local files. |
| F11 | ICLR releases reviews on November 5; public discussion and paper revisions end November 18. Area chairs and reviewers "reserve the right to ignore changes that are significantly different from the original paper"; a pdfdiff is applied to revisions and reviewers are not required to look at every revision. | Integrate the core before November 5; upload one consolidated revision with a change list by about November 12; keep method redesign separate from corrections to submitted claims. |
| F12 | The original governance rule prohibited Copilot review. The user's standing instructions confirm it: Copilot review is intentionally disabled on this repository and must not be requested unless the user asks for it on a specific PR. The 2026-10-02 revision inverted this. | Request only the user's review; never request Copilot; never merge. |
| F13 | ICLR 2027 author guidelines, re-fetched 2026-10-06: "At the time of submission, the main text should be 9 pages or fewer. During the discussion/rebuttal phase and for the camera ready, the page limit will be increased to 10 pages to allow for new results/discussions." The submission ends on page 9 and the previous plan budgeted every change against nine pages. | Build the revision at ten pages. The results figure, related-work expansion and scope wording fit without the appendix diet. Verify any other venue's limit separately. |
| F14 | The retained family checkpoints (for example `paper/results/github_workflow_families/pr_outcome/final/evaluation_checkpoint.json`) store tool sequences, arguments, quality labels and metrics, not tool outputs. The tools read the pinned parquet snapshot, so outputs are reconstructible offline. | C1b must rebuild the snapshot-backed tool facade and confirm the unperturbed replay reproduces the retained program outputs before perturbing. It stays provider-free, but it is not a replay of stored outputs. |
| F15 | No external human read of the submission exists: the five `team-reviews/` files are blank templates and the only reviewer-rubric score is 7/10 from the 2026-08-21 scorecard. The 76-to-90 scale is internal. | Schedule one independent read on the official ICLR questions before November 5; treat the 90 as uncalibrated until then. |

A zero observed replay-mismatch count is not proof that this event is impossible. The narrow
label does, however, fail to measure continuation errors. Likewise, a cluster sensitivity
that crosses the admission threshold shows sensitivity to assumptions, not proof that the
i.i.d. assumption is false.

## 2. Decisions and claim boundaries

**D1 — Describe the implemented contract precisely.** For the clean replay calibration
path, define entry dispatch eligibility using the frozen hard guard and score threshold.
Among those eligible groups, a violation is a recorded-output mismatch or missing-output
mismatch after the program and verifier succeed. A verifier rejection or interpreter
failure is unproductive/abstaining, not a positive violation label in this path. Count a
group once, with a violation if any eligible member has that label. State the conditional
population, group unit and assumptions next to the guarantee. Audit runtime failures,
clean fallback and incidents separately before expanding this event beyond the replay
contract. Do not silently recategorize labels in retained results.

**D2 — Preserve the registered method; test simplification prospectively.** Keep the
11-point grid and its certificates as the method that produced the existing results. A
single frozen acceptance rule is a useful prospective variant and a retrospective
sensitivity, not a retroactive repair. The proposed rule attempts every hard-guard-eligible
group; execution and verification can still abstain. Selecting only verifier successes
would change the existing denominator. Freeze candidates, acceptance policy, grouping,
endpoint and confidence allocation before using fresh calibration outcomes. Calibration-
dependent candidate generation cannot be repaired merely by dividing delta by the number
of surviving candidates.

**D3 — Separate empirical quality from admission.** A paired compiled-only miss rate, an
absolute answer-error rate, and a tool-region replay-error rate are different estimands.
For example, a one-sided 95% binomial upper bound for 1/210 is 0.02239 under an appropriate
i.i.d. model; it is not an end-to-end admission certificate, and 95% is different from the
90% confidence used in the gate arithmetic. Do not pool heterogeneous cohorts/providers
and call the resulting bound a common future-population guarantee.

**D4 — Retain nulls and adverse outcomes.** Freeze protocols before the first study call.
Do not expand a sample until it admits, choose a favorable cohort after labels are seen,
or revise perturbations after observing arm differences. Failed runs, budget stops,
unavailable actions and NO-GO decisions remain reportable evidence with their limitations.

## 3. Workstreams

Priority P0 is the core revision; P1 is a conditional extension; P2 is optional. Estimates
are focused person-days. Provider-free does not mean effort-free. Proposed filenames and
CLI options below are deliverables, not interfaces assumed to exist today.

### WS-A — Align the guarantee with measured labels (P0 / P1)

**A1. Scope correction and label audit — P0, 1–2 days, no provider spend.**

- Trace `CalibrationSample.eligible`, `unproductive`, `violation` and `reason` through
  `_calibration_samples`, `calibrate_gate`, runtime execution and the manuscript.
- Update the problem definition, method, algorithms, proposition instantiation, appendix,
  abstract, results and limitations consistently. Keep an end-to-end objective only if
  explicitly separated from the narrower implemented certificate.
- Show the clean-path cases: hard-guard rejection excluded from accepted groups; verifier
  rejection and execution failure unproductive but not labeled violations; accepted replay
  mismatch a violation; downstream answer error unmeasured by these labels.
- Reconcile the runtime incident boundary without claiming that replay calibration measures
  incidents it does not label. This may require a follow-up code fix and fresh calibration,
  not a wording change alone.
- Acceptance: reviewers can reconstruct numerator, denominator, confidence, sampling unit
  and scope from the paper. Relevant label regression checks and artifact validation pass.
  A text search alone is not a sufficient soundness check.

**A2. End-to-end labels — P1, 3–5 days after data GO; provider cap $10.**

- Pre-register a new endpoint that runs the continuation and grades an independently
  defined answer contract. Decide explicitly whether errors after clean fallback count;
  report overall system quality separately from risk conditional on an attempted dispatch.
- Freeze artifact, model, prompt, grader, acceptance rule, sampling population, sample size
  and candidate multiplicity. Use fresh disjoint calibration groups for confirmatory
  claims. New labels on already-inspected calibration records are exploratory unless their
  reuse is justified; they do not automatically create a new prospective certificate.
- Reserve separate held-out test records. Select the pool before observing labels; C2
  may supply it if available, but switching pools after observing results is prohibited.
- Under the §5 assumptions, a fixed single candidate with 92 accepted groups admits at
  `k <= 1`; with 132 accepted groups it admits at `k <= 3`. For two fixed candidates,
  93 groups accommodate one violation. These are conditional arithmetic, not predictions.
- Report counts, dispatch coverage, absolute errors, paired differences, exact bounds,
  abstention/fallback costs and failures. A retirement remains a result. No assumed 1–2%
  error rate is used to promise admission.
- Deliverables: new end-to-end protocol, continuation-label driver, immutable result
  directory, generated table and validator coverage.

### WS-B — Evaluate a simpler admission rule (P0 sensitivity / P1 implementation)

**B1. Retained-data sensitivity — P0, 1 day, no provider spend.**

- Recompute candidate-level bounds with the grid penalty removed, retaining all tested
  candidates and the appropriate multiplicity. Use retained group labels, not rounded
  table values, to verify acceptance sets and counts.
- Recompute day/author effective-unit sensitivities, including all seven cohorts. Distinct
  counts alone do not establish independent clusters; neither an author nor a day analysis
  handles both dependence structures automatically.
- Label the output “Retrospective single-rule sensitivity; registered certificates
  unchanged.” Add its generating script and number-registry references if it enters the
  manuscript. Never promote a favorable author sensitivity into the primary certificate.

**B2. Make the method understandable — P0, 1–2 days, no provider spend.**

- Explain hard eligibility, attempted substitution, verifier abstention, counted mismatch
  and exact admission in that order. Preserve the grid, multiplicity and 92/106-group
  requirements where needed to explain retained results.
- Describe the learned score's lack of demonstrated graded coverage. Move secondary
  mechanics to the appendix without rewriting history or suppressing certificate limits.
- Present single-rule admission as an optional prospective variant. Replacing the primary
  method is a later research change, not necessary for the current scope correction.

**B3. Optional single-rule mode — P1, 2–3 days, no provider spend.**

- Keep the published default and serialized artifacts compatible. The current API accepts
  `Sequence[float]`; `grid=("single",)` is invalid. Evaluate a numeric singleton such as
  `(1.0,)` or an explicit policy mode after inspecting schema and runtime scoring.
- Make selection explicit in compile configuration, runner CLI, serialized metadata and
  runtime behavior. A singleton grid alone need not remove model fitting/scoring overhead.
- Implement a frozen-candidate budget across the full tested set, not just a favorable
  selected artifact. Record whether the guarantee is per candidate, within a family, or
  simultaneous across families.
- Test all-eligible acceptance, hard rejection, verifier abstention, zero accepted groups,
  exact boundary counts, multiplicity, serialization, runtime parity and legacy replay.
- Adopt as primary only for a new frozen protocol after these checks pass.

### WS-C — Measure what the induced verifier prevents (P0 / P1)

**C1a. Provider-free mechanism study — P0, 2–3 days.**

- Implement `drift-robustness-ablation-protocol.md` on the five simulated workloads with
  the existing three arms and 24-window cap. Retain the hard runtime boundary in every arm;
  only the verifier differs in the principal contrast.
- Before execution, amend its statistics to avoid treating repeated perturbations of one
  episode as independent observations. Define each record/group's primary binary outcome
  as any wrong output across its fixed applicable perturbation suite; compare the paired
  group outcomes. Report per-transform counts descriptively. If records are dependent,
  define independent groups first or keep inference explicitly exploratory.
- Retain the protocol's two prespecified comparisons and Holm correction. Report exact
  McNemar discordances, effect sizes, uncertainty and invariant-family over-abstention.
  Zero discordances is a null, not equivalence. An adverse guarded result takes precedence.
- Validate unperturbed oracles, inert permissive verifiers, identical arm cohorts, and
  fail-closed state-delta handling. Label this simulated mechanism evidence only.
- `run_perturbations` in the evaluation package already takes a program, guard, verifier,
  windows and a perturbation list, and the compiler's development labels already run programs
  through perturbation facades with a semantic-signature oracle. The protocol's own estimate
  of about a day for the driver is consistent with that; the 2–3 days here add the statistics
  amendment, validator family and tests.

**C1b. GitHub recorded-replay extension — P1, 2–4 days; provider-free first.**

- Create a separate protocol before using the 90 previously evaluated primary records.
  Call this a new stress analysis of retained records, not a new untouched held-out cohort.
- The checkpoints do not retain tool outputs (F14). Rebuild each record's tool facade from
  the pinned parquet snapshot, confirm the unperturbed replay reproduces the retained program
  outputs and quality labels, and only then apply perturbations. Count that reconstruction in
  the 2–4 days.
- Check each transform against each task contract. Reordering may change an ordered-excerpt
  requirement; duplication may change counts; some transforms are no-ops. Declare the
  oracle and applicability in advance. Report exclusions and no-ops, and preserve original
  gold only where the task semantics warrant it.
- Start with the same three arms. A fourth recurrence-only arm is optional and requires
  its own justified contrast and multiplicity budget. The main comparison isolates the
  verifier on a fixed program, not the entire guard system.
- Program-output mismatches and abstentions are provider-free endpoints. A live continuation
  extension is separate and capped at $15, with independent task grading and the same
  perturbed tool environment available to fallback. Do not promise clean-baseline success
  by silently giving fallback unperturbed tools.
- `90 × 9 × 3 = 2,430` is an episode-arm count, not a provider-request count. Retries,
  baseline fallback and multi-call continuation can increase requests. Measure the live
  pilot before approving the full schedule; report paired group outcomes and costs.

**C2. Time-forward cohort — P1, 6–10 days including acquisition/runner work;
provider cap $25, conditional on provider-free GO.**

- The pinned dataset cannot supply this cohort (F7): it has not changed since 2025-06-13 and
  holds only huggingface/datasets records through that day. The route is a fresh GitHub API
  pull per repository with an explicit record-creation cutoff after the snapshot's last day,
  loaded through the multirepo preflight's snapshot path, with its own digest, licence note
  and gold reconstruction. Do not interpret the dataset revision hash as a timestamp.
  Reconstruct gold and deduplicate against all discovery, development, calibration and
  evaluation records already used.
- Freeze disjoint calibration and test sets, provenance, sampling/stratification policy and
  class availability. A balanced cohort targets that designed mixture, not automatically
  natural production prevalence. State the population of every claimed bound.
- Audit source, prompt, tool, policy, schema, catalog and entry-state compatibility. With
  the original artifact unchanged, pin or hull failures are valid abstentions; report
  actual coverage. Never bypass a failed pin. If migration is required, derive a separately
  identified artifact using only permitted development data, then recalibrate and evaluate
  it as a different arm. Measure changed pins even if runtime compatibility excludes them.
- Freeze the candidate set before fresh calibration. Plan sample sizes from accepted groups,
  not raw acquired records: at zero violations D2 requires 45 groups for one fixed candidate
  or 59 for two; 93 for two candidates with one violation. The original grid needs 106 for
  two candidates with zero violations. Preserve an independent test set (target 60 records
  per feasible family); do not reuse it for A2 calibration.
- Distinct authors/days are diagnostics, not a cluster-robust certificate. If a defensible
  independent cluster design is unavailable, report descriptive time-forward performance
  and sensitivity. A later distribution shift remains outside any fixed-distribution bound.
- GO requires usable data, enough eligible groups, frozen splits and demonstrated runner
  support. Record NO-GO per family without predicting which scarce classes will replenish.
- Deliverables: versioned protocol, snapshot adapter and artifact-loading support, gold
  validation, compatibility preflight, and new result directories. C2 is not required to
  finish the core paper correction.

### WS-D — A second live domain (P1, conditional)

**D1. HMDA under the existing study design — 6–10 days; provider cap $30.**

HMDA is a reasonable candidate because its retained preflight reports 420 groups, correct
independent gold reconstruction, and 416/420 variable paths. These are readiness signals,
not demonstrated compiler support or live success. The alternative vulnerability domain
has fewer variable paths; that alone does not make its scientific question trivial.

- Use `benchmarks/manifests/multidomain-study.yaml`: 40 discovery, 30 development,
  100 artifact-calibration, 75 portfolio-calibration, 100 test, and 75 reserve groups.
  These total 420. Group identity for HMDA is `lei`; rows from one lender cannot be
  relabeled as independent groups.
- Preserve the manifest's statistical contract: artifact/portfolio risk limits of 0.10,
  confidence settings of 0.99, noninferiority margin, repeats and portfolio endpoints.
  The §5 alpha=0.05/delta=0.10 arithmetic does not certify this different design.
- The retained preflight has no frozen protocol. Create and digest the protocol, pricing,
  action identities and pools through existing machinery before any live calls. Preserve
  separate artifact and portfolio calibration; discovery groups are not available for
  A2 calibration simply because a different sample size would admit more errors.
- If a narrower D2-only study is preferred, version it explicitly with new disjoint roles,
  endpoint/risk/confidence definitions, runner/validator support and pre-registration. Do
  not describe it as execution of the original frozen study.
- Follow `multidomain_study.py` controls: `--protocol`, `--action-lock`, `--max-provider-usd`,
  `--reservation-usd-per-execution`, bounded retries/requests/timeouts, and phase-specific
  registry/policy inputs. A valid human macro approval must match schema, implementation,
  catalog and evaluator/gold digests. Do not fabricate that approval.
- Pilot only on designated reserve/pilot groups, estimate all remaining phases and repeats,
  and proceed only if the cap accommodates them. Report compiler retirement, unavailable
  arms and incomplete runs as such. A refusal supports a domain-boundary claim; live
  preservation or savings requires a usable artifact and the corresponding evaluation.

### WS-E — Improve the nine-page presentation (P0)

**E1–E3. Abstract, introduction and method — 2–3 days jointly with B2.** Lead with the
problem and the admissibility composition. Explain prefix, group and artifact before
record-level examples. Keep the calibrated event and per-candidate limitations visible,
including in the abstract when needed to qualify headline claims. Distinguish the original
90-record primary evaluation from the extended evaluation. Do not insert future time-forward,
drift or HMDA results before they exist. Use fewer numbers without hiding assumptions.

**E4. Results figure — 1–2 days, conditional on plotted evidence.** Start with retained
per-family resource reductions and refusal/dispatchability evidence. Add a drift panel only
after C1 is validated, labeled by substrate. Use generated figures with explicit denominators;
do not count an unrun domain as a fifth completed benchmark.

**E5–E7. Appendix, terminology and page budget — 1–2 days.** Build the revision at the
ten-page discussion limit (F13), not nine: the extra page covers E4, the related-work
expansion and the A1 wording, so the appendix diet is no longer needed to make space. Add a
short reading guide and consistent terminology. Move secondary audit tables only when a
stable, anonymous, versioned supplement retains their evidence paths. Keep proof
assumptions, multiplicity, absolute resources and failure analyses easily reachable. Use
readability and evidence access as the criterion, not an arbitrary 14-table ceiling. Update
the page check to the limit in force (ten during discussion and camera-ready). Rebuild and
inspect the PDF; no assumed number of saved lines substitutes for the actual page check.

### WS-F — Position the contribution (P0, 1–2 days)

Expand related work selectively around trace compilation/partial evaluation, workflow
mining, agent reuse, risk-controlled prediction, and tool-use safety. Verify primary
sources before attributing capabilities or claiming novelty. Use a compact comparison
only if it clarifies what is reused, the admission rule, and fallback behavior. Reference
counts are not a quality target. Credit Clopper–Pearson and risk-control methods as
statistical tools; emphasize the admissibility composition and its demonstrated limits.

### WS-G — Statistical reporting (P0, 1–2 days, coordinated with A/B/C)

- Keep the i.i.d. Bernoulli/group assumption for the stated exact binomial bound; do not
  substitute exchangeability without a different valid argument. For example, repeated
  copies of a single Bernoulli outcome are exchangeable but supply only one independent
  observation. See the [binomial interval model](https://arxiv.org/abs/1302.6659).
- Predefine cluster formation, group-level outcomes, dispatch denominators and sampling
  population for any cluster analysis. Crossed author/day dependence needs a justified
  design; passing two separate count sensitivities does not solve it.
- Keep risk conditional on a fixed population, accepted groups and frozen candidates
  separate from robustness to shift. State family-wise versus per-family confidence.
- Give absolute end-to-end errors and paired compiled-only errors separate columns and
  denominators, split by family, cohort and provider. Recompute their bounds rather than
  implying that the 1/210 and second-provider counts estimate one common risk.
- Say explicitly that a nonsignificant McNemar result is not evidence of equivalence.
  Predeclare noninferiority/equivalence designs when those are the intended claims.

### WS-H — Manual-authoring pilot (P2)

Recruit three to five engineers only if useful and available; track participant-hours and
compensation separately from provider spend. Give task specifications, schemas and a
separate development test set; do not expose the final 30 held-out records during authoring.
Record time, defects and verifier choices; freeze each program before final clean/drift
assessment. Counterbalance task order and report prior familiarity. This small convenience
sample supports descriptive observations, not a general labor-cost or productivity claim.

## 4. Dependencies and decision gates

| Gate | Required evidence before proceeding | On failure |
|---|---|---|
| A1 scope audit | Labels and dispatch denominator match the instantiated claim | Correct wording; isolate any code/label repair requiring fresh evidence |
| B3 prospective mode | Explicit policy, complete candidate budget, compatible serialization/runtime tests | Keep original grid; publish B1 sensitivity only |
| C1 oracle/statistics | Valid perturbation semantics, paired independent groups or descriptive scope | Revise protocol before outcomes; report excluded/no-op transforms |
| C2 data GO | New compatible source, independent roles, gold, coverage and class inventory | Commit NO-GO; do not delay core revision |
| A2 confirmatory GO | Frozen endpoint/artifact and fresh eligible calibration groups | Exploratory labels only, or defer |
| D1 execution GO | Frozen protocol/actions, valid human approval, pilot-supported budget | Provider-free preflight/refusal only, or defer |
| Live budget GO | Enforced reservation, retries and aggregate caps | Stop/defer; do not silently double the allowance |
| Revision upload GO | Core integrated; ten-page build valid and anonymous; change list written for reviewers; one upload planned | Hold the upload; respond in text only |
| Publication GO | Generated evidence, valid manifests, readable anonymous PDF, human review | Keep PR open; no upload or merge by this plan |

A1 precedes the final B2/E wording. C1 results precede a new drift figure. C2 may supply A2
records only through the disjoint roles frozen in advance. D1 is independent of C2, but
requires its own approval and protocol. These tasks are not all independent Phase-0 work.

## 5. Recomputed admission arithmetic and its limits

The following values use one-sided Clopper–Pearson bounds with `alpha=0.05`, `delta=0.10`,
`gamma = delta / (grid_size * m)`, and independent identically distributed accepted group
outcomes for a frozen rule. `m` is a valid, preallocated fixed candidate budget. These
numbers are sample-size calculations, not evidence that a dataset meets the assumptions.

Minimum accepted groups for `U <= 0.05`:

| Design | k=0 | k=1 | k=2 | k=3 | k=4 |
|---|---:|---:|---:|---:|---:|
| Registered grid, m=1 | 92 | 133 | 168 | 200 | 231 |
| Registered grid, m=2 | 106 | 148 | 185 | 218 | 251 |
| Single rule, m=1 | 45 | 77 | 105 | 132 | 158 |
| Single rule, m=2 | 59 | 93 | 124 | 153 | 181 |

Upper bound at `n=92`:

| Design | k=0 | k=1 | k=2 |
|---|---:|---:|---:|
| Grid, m=1 | 0.0498 | 0.0711 | 0.0895 |
| Grid, m=2 | 0.0569 | 0.0791 | 0.0981 |
| Single, m=1 | 0.0247 | 0.0416 | 0.0568 |
| Single, m=2 | 0.0320 | 0.0505 | 0.0669 |

Retrospective effective-unit sensitivity at zero violations, using counts from
`paper/results/iclr_revision/effective_units.json`. Each cohort's stated candidate budget
applies to both its author and day columns; results are not simultaneous across cohorts.

| Cohort | m | Authors | U at authors | Days | U at days |
|---|---:|---:|---:|---:|---:|
| Issue-type routing | 1 | 82 | 0.0277 | 90 | 0.0253 |
| PR-outcome audit | 2 | 60 | 0.0487 | 86 | 0.0342 |
| Backlog-attention routing | 2 | 73 | 0.0402 | 87 | 0.0338 |
| Core huggingface/datasets | 1 | 46 | 0.0488 | 80 | 0.0284 |
| Core pandas-dev/pandas | 1 | 53 | 0.0425 | 92 | 0.0247 |
| Core psf/requests | 1 | 79 | 0.0287 | 90 | 0.0253 |
| Core streamlit/streamlit | 1 | 25 | 0.0880 | 87 | 0.0261 |

These are hypothetical bounds under a single fixed rule and the corresponding group
model. They are not new certificates for the already selected artifacts. Author-level risk
also targets a different population from record-level risk. The original table's day-column
heading incorrectly suggested m=1 for the two m=2 families; the values above use m consistently.

External support ceilings under a hypothetical single rule and m=1 give `U=0.0848` at
n=26 (NESTFUL), `0.1423` at n=15 (BFCL), and `0.2501` at n=8 (API-Bank); all exceed 0.05.
For n=136, U is 0.0168 arithmetically, but the 136 AppWorld traces are not automatically
136 eligible independent groups for one candidate. Preserve candidate-specific counts,
provenance/effect barriers and dispatchability limits; raw totals do not establish admission.

Reproduce the main tables with the existing SciPy dependency:

```bash
.venv/bin/python - <<'PY'
from scipy.stats import beta
for label, grid_size, m in (("grid/1", 11, 1), ("grid/2", 11, 2),
                            ("single/1", 1, 1), ("single/2", 1, 2)):
    confidence = 1 - 0.10 / (grid_size * m)
    floors = [next(n for n in range(k + 1, 1000)
                   if beta.ppf(confidence, k + 1, n - k) <= 0.05)
              for k in range(5)]
    bounds = [round(float(beta.ppf(confidence, k + 1, 92 - k)), 4)
              for k in range(3)]
    print(label, floors, bounds)
PY
```

## 6. Schedule and budget

Official dates checked 2026-10-02: full-paper deadline September 25; reviews and discussion
start November 5; discussion ends November 18; decisions December 16.
[ICLR 2027 dates](https://iclr.cc/Conferences/2027/Dates).

The author guidelines permit revisions after reviews release and until November 18.
Reviewers and area chairs may ignore changes significantly different from the original
submission. Prepare scope corrections early; do not assume a wholesale method replacement
will be assessed in this review cycle. Repository plans do not verify the submission's
current forum status. [ICLR author guidelines](https://iclr.cc/Conferences/2027/AuthorGuidelines).

| Window | Core deliverable | Conditional work |
|---|---|---|
| Oct 6–16 | A1 audit/correction; B1 sensitivity; C1 protocol/statistics amendment and driver; schedule the external read (F15) | None. C2/D1 protocols only if the core is ahead of schedule |
| Oct 16–30 | B2, E, F and G writing at ten pages; C1a run; C1b provider-free protocol and run | Exploratory end-to-end labels on retained issue-type groups, if wanted for the response |
| Oct 30–Nov 4 | Integrate validated results; ten-page build/QA; anonymity check; change list; evidence-linked response material | Nothing new started |
| Nov 5–18 | Respond to actual reviews; one consolidated human-approved revision by about Nov 12 | Only results already validated by Nov 4 |
| After Dec 16 | Follow decision and next venue's verified rules | A2 confirmatory, B3, C2 (GitHub API acquisition), D1, H |

The October 2–9 window of the previous revision has passed with nothing in it started; PRs
#49 and #50 changed this document only. Rebased 2026-10-06.

Do not assume a next-venue deadline or dual-submission eligibility; verify them when a
resubmission decision is made. No response text should invent reviewer concerns before
reviews exist.

Provider allocations, including each study's pilot and retries:

| Item | Cap |
|---|---:|
| Core writing, arithmetic and provider-free C1 | $0 |
| C1b optional live continuation | $15 |
| C2 live evaluation | $25 |
| A2 continuation labels | $10 |
| D1 HMDA pilot and feasible subsequent phases | $30 |
| Unallocated contingency, assigned explicitly before use | $20 |
| **Aggregate maximum** | **$100** |

These are proposed caps, not verified cost estimates or permission to execute paid studies
as part of this document review. Retained prices are historical. Freeze current model IDs,
pricing and token/request bounds before each study, reserve worst-case per-execution spend,
and ledger failures and retries. The GitHub runner's existing `--approved-spend-usd` checks
are specific to its Headroom path; implement and test general enforcement before relying
on that flag elsewhere. Use the multidomain runner's actual controls for D1. If a complete
confirmatory study cannot fit, defer it or preregister a smaller exploratory study before
outcomes; do not call an incomplete sample confirmatory.

## 7. Completion scenarios

| Outcome | Supported conclusion |
|---|---|
| Core scope/writing work complete | A clearer, more defensible account of existing evidence; no new empirical guarantee |
| C1 separates guarded and unverified arms | Verifier benefit under the declared perturbations and substrate, priced by abstention |
| C1 null | No demonstrated verifier benefit in that experiment; no equivalence claim |
| C1 adverse | Report the guarded failure first; investigate before making stronger claims |
| C2 succeeds | Time-forward performance at observed coverage; certification only under justified prospective assumptions |
| A2 admits | End-to-end bound for the frozen endpoint, rule and sampled population, with stated confidence/multiplicity |
| D1 compiles and completes evaluation | Second-domain live evidence within the stated protocol |
| D1 retires | Additional domain-boundary evidence, not live compaction quality or savings |
| Data, approval or budget gate fails | Explicit NO-GO/defer; core revision remains deliverable |

## 8. Scope limits

- Do not replace existing results, defaults or certificates merely because the alternative
  has a smaller multiplicity penalty.
- Do not remove inconvenient abstract qualifications or move essential assumptions out of
  reach to improve a subjective score.
- Do not add models/providers without a new question; prioritize the guarantee mismatch,
  mechanism evidence and population limits.
- Do not claim that fixed pins establish shift robustness, or that relaxing pins preserves
  the old certificate.
- Do not tune alpha, delta, grouping, cohorts, rules or stopping conditions after outcomes.
- Do not spend time on an arbitrary reference/table count or promise all extensions within
  a part-time five-week schedule.
- Do not upload a stream of revisions during discussion; one consolidated revision with a
  change list, built at the ten-page limit.

## 9. Governance and validation

- Every repository change uses a dedicated branch and PR, following the repository template
  exactly. Split implementation into bounded dependent PRs where appropriate. Request only
  the user's review; GitHub drops a reviewer request from the PR author, so assign the user
  instead and say so in the PR. Never request Copilot review on this repository unless the
  user asks for it on a specific PR. Address relevant review comments on the same PR; keep
  its description current.
- Never merge or enable auto-merge. Leave completed PRs open for the user's final review.
- Plan-only PRs (#49, #50 and this revision) change this document only. Subsequent code,
  manuscript and study work must satisfy its own evidence, testing and review gates. Preserve `.claude/` and any unrelated
  local work.
- Commit each live protocol before execution, including immutable cohort IDs/digests,
  candidate budgets, sampling units, arms, endpoints, stopping rules and enforced caps.
  Write results to new directories; retain failures and NO-GO outcomes.
- Every manuscript number needs a generating script or JSON key in the number registry;
  generated tables, result evidence and manifests must agree. Do not silently rebuild
  historical artifacts under a changed default.
- For this plan-only edit: recompute arithmetic, verify referenced local interfaces and
  authoritative dates, check Markdown references/fences and `git diff --check`. New code
  tests and PDF regeneration are not applicable until implementation/manuscript changes.
- For later manuscript changes: follow the repository build order (analyses,
  `build_artifacts.py`, open-research build with logs, ICLR build, `finalize_manifest.py`,
  `validate_artifacts.py`), then inspect page count/readability/anonymity and refresh the
  anonymous archive as applicable. Await applicable PR checks and retain unresolved failures.

## 10. Concern-to-task map

| Reviewer concern | Tasks |
|---|---|
| The certificate does not measure the continuation | A1; prospective A2 |
| Candidate/threshold search exceeds the guarantee | B1–B3; G |
| The score has no demonstrated graded coverage | B2; optional B3 |
| Dependence undermines the population interpretation | G; C2 sampling preflight |
| The verifier has no measured benefit | C1a; conditional C1b |
| Manual code ties, with unmeasured authoring cost | E limitations; optional H |
| Evidence is tied to one snapshot/domain | Conditional C2 and D1 |
| Contribution and evidence are difficult to follow | E and F |
