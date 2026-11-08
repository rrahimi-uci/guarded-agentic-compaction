# Review map: every reviewer point, classified

Reviews: `ICLR-1.txt` (R1, rating 1, confidence 3), `ICLR-2.txt` (R2, rating 1, confidence 4),
`ICLR-3.txt` (R3, rating 2, confidence 3). The reviewers read the September 24 submission
(`openreview_submitted.pdf`, 36 pages); section, table and appendix numbers below are those of the
revised 64-page build (`paper/iclr/upload/GAC_ICLR2027_revised.pdf`) unless marked "reviewed".

Classes:

- **MISUNDERSTANDING**: the reviewed paper already answered it; the section is given.
- **FIXABLE BY TEXT**: we can clarify or reframe.
- **NEEDS EXPERIMENT**: a new run or ablation is needed.
- **VALID LIMITATION**: we concede and state the scope.

A point can carry two classes. "Done" means the work exists in the repository and the revised PDF.
It does not mean the reviewer has accepted it.

## Reviewer 1

| ID | Point (paraphrase) | Class | Disposition and where |
|---|---|---|---|
| R1-W1 | Introduction hard to follow and reads as LLM-written. Issue #4420 appears without context: what kind of issue, is it from a dataset, and why it matters. | FIXABLE BY TEXT | Done. §1 now defines GitHub issue triage on the pinned huggingface/datasets snapshot before the example and says #4420 is one held-out record. The tone of the whole introduction is the author's call. |
| R1-W2 | No comparison with other agent-workflow compilers (EvoC2F, Agent JIT); the cost–quality trade-off against other compilers is needed. | NEEDS EXPERIMENT; VALID LIMITATION | Not run. EvoC2F has no inspectable code (HTTP 401) and Agent JIT plans web tasks. A matched comparison is designed (`paper/supplementary/matched-compiler-candidate-protocol.md`, estimated 6 to 10 working days) and does not fit the window. Done instead: a pre-registered adapted AWM comparison (§5.1, Table 3) and a design-property comparison (§2, §6, App. N Table 46). |
| R1-W3 | The reviewed Table 2 is hard to interpret and does not let one judge the quality of compiled segments. | FIXABLE BY TEXT; partly MISUNDERSTANDING | The reviewed Table 2 reports feasibility on trace benchmarks where no model runs, so it cannot show answer quality. Quality is measured in the reviewed Table 1 (now Table 2) and BIRD (§5.2). Done: plain-word columns and a caption key (now Table 4, with all four substrates in Table 20). |
| R1-W4 | The loss in §2 includes downstream answer errors, but the calibration helper labels replay agreement only, so the labels cannot support an end-to-end certificate. Align loss, labels and claims. | VALID LIMITATION; FIXABLE BY TEXT; NEEDS EXPERIMENT (done) | The reviewer is right. Done: §2 now defines the loss per certificate type. The 92-group certificates are stated as replay certificates (App. C "Calibration labels as computed"; Tables 6 and 28). New end-to-end certificates grade final answers: post-cutoff PR-outcome (0/132, U = 0.0173) and the multi-repository study (§5.4, App. F.2). |
| R1-W5 | The calibration population is outcome-filtered (successful traces, family windows). Could excluded cases pass the deployed guard? If so, recalibrate before filtering and keep failures. | VALID LIMITATION; NEEDS EXPERIMENT (done) | Confirmed: three excluded records (#539, #2781, PR #5700) pass the saved guard and gate (App. G "Calibration population audit", 396/396 records). The unfiltered-population claim for the primary bounds is withdrawn. The repair the reviewer proposes was run for PR-outcome: the multi-repository study samples before any outcome filter and keeps failures (App. F.2, Table 19). |
| R1-W6 | Lifecycle policy underspecified: what evidence triggers revision, and what permits renewed admission. Cites SKILL.nb. | FIXABLE BY TEXT; VALID LIMITATION | Done: App. D "Implemented lifecycle controls and proposed renewal policy" separates implemented controls from the proposed policy; SKILL.nb is cited. No failure-rate trigger is implemented or claimed. |
| R1-Q1 | Complete references for the benchmarks; §4.1 gives little detail. | FIXABLE BY TEXT | Done: §4 cites every benchmark with its release; Table 16 and App. E specify the GitHub tasks; App. F.4 maps each external benchmark to its use. |
| R1-Q2 | Which 92-group labels include downstream answer errors? Name the labeling path or the narrower guarantee. | FIXABLE BY TEXT | None of them. Labels come from `grc/compile.py::_calibration_samples` (replay after verifier success). Stated in §2 and App. C. |
| R1-Q3 | Can the retained records account for every excluded record, and would the guard reject it? | FIXABLE BY TEXT (provider-free audit, done) | Done: `paper/results/calibration_population_audit/report.json` (396/396). The three excluded records pass the guard. |
| R1-Q4 | What evidence triggers recompilation or retirement, and what calibration is needed before reactivation? Separate implemented policy from future work. | FIXABLE BY TEXT; VALID LIMITATION | Done: App. D. Implemented: manifest incompatibility, expiry, retirement, rollback, kill switch and staged promotion. Proposed and not evaluated: outcome-triggered suspension, and reactivation only after fresh disjoint calibration. Measured case: 60/60 abstentions on a new snapshot. |
| R1-Q5 | Define the "content-addressed execution manifest" and why it matters for the episode definition. | FIXABLE BY TEXT | Done: §2 defines the manifest and its compatibility pins; Eq. (3) requires equality on every pinned field. |

## Reviewer 2

| ID | Point (paraphrase) | Class | Disposition and where |
|---|---|---|---|
| R2-W1a | The primary tasks are metadata classification and verbatim extraction, readily done by predefined deterministic workflows. | VALID LIMITATION | Conceded; §4 states that no primary decision needs semantic interpretation. BIRD (§5.2) adds a live SQL agent after a compiled schema-first opening. |
| R2-W1b | The handwritten comparator matches correctness and request reduction with slightly better tokens and cost (reviewed Table 9), and the value of automatic discovery is unquantified. | VALID LIMITATION; FIXABLE BY TEXT (reframe) | Reframed: matching the hand-written program is the intended result, and GAC's contribution is automating that program safely. Across 3,560 end-to-end groups the compiled, unchanged and hand-written arms meet 3,510, 3,507 and 3,504 contracts, and both programs cut cost by 73.6%. Discovery break-even: 411, 183 and 181 episodes. The engineering value of automation (engineer time) is still not measured. |
| R2-W1c | The cross-repository experiments keep the simpler PR-outcome task. | VALID LIMITATION | Conceded: PR-outcome is the family with enough fresh records. Those studies test transfer and certification, not task difficulty. |
| R2-W2a | Guards not individually attributed: barrier-free replay ties GAC at 30/30 with fewer requests (reviewed Table 19), and disabling several barriers at once prevents attribution. | VALID LIMITATION; NEEDS EXPERIMENT (done) | Done: a live-recovery study removes one mechanism at a time over 2,304 scheduled episodes (App. I). The scope guard raises success from 186/216 to 205/216; the completeness check's benefit is unresolved. Recurrence-only replay still ties on that cohort (now Table 33). |
| R2-W2b | The learned gate does not establish risk-ranking value: scores are constant within repositories, and the pool cannot certify intermediate coverage (reviewed Table 23). | VALID LIMITATION | Conceded; the learned-gate claim is withdrawn (§3 Stage 6, App. H.1). Full statistical, support-only and deterministic routing are identical on 2,724 record-model cases (now Table 38). |
| R2-W2c | The drift comparison was proposed but not executed. | NEEDS EXPERIMENT (done) | Done: three drift studies (144 paired groups provider-free, 89 records replayed, 1,080 live cells). Two are null; continuation-graded drift is adverse (39/60 wrong in both arms). Reported in §5.4 and App. G. |
| R2-Q1 | Give a complete primary-task specification and say which decisions need semantic or adaptive reasoning. | FIXABLE BY TEXT | Done: Table 16 and App. E; §4 states that none does. |
| R2-Q2 | How are calibration labels generated (executed continuation or replay)? Does calibration sampling precede outcome or recurrence filtering? | FIXABLE BY TEXT; VALID LIMITATION | Primary: replay, with filtering before the split (App. C, App. G). Later end-to-end studies execute the continuation and sample before filtering (§5.4, App. F.2). |
| R2-Q3 | Compare full GAC, unguarded replay and a handwritten baseline on one workflow with genuinely adaptive decisions. | NEEDS EXPERIMENT; VALID LIMITATION | Not completed; estimated 12 to 16 working days and a budget increase. Three attempts stopped at prespecified development gates (BIRD 26/36 vs 28/36; AppWorld baselines 1/12 and 2/12; AgentHop has no derivable selector), and two corpus screens were no-go (App. L). No adaptive advantage is claimed. |
| R2-S | (In strengths) The certificate's dependence on i.i.d. calibration groups and candidate-selection assumptions must remain explicit. | FIXABLE BY TEXT | Done: assumptions are stated wherever a bound appears; see the audit for any remaining sentence. |

## Reviewer 3

| ID | Point (paraphrase) | Class | Disposition and where |
|---|---|---|---|
| R3-W1 | The safety language is stronger than the statistics: the two-candidate selection-adjusted bound is 0.0569 > 0.05, and creation-day or author units retire every family. State the limits in the main claims; add independent calibration data. | VALID LIMITATION; NEEDS EXPERIMENT (done) | Conceded. The abstract and conclusion now state that the primary 92-group cohorts carry no selection-wide 5% bound. New independent data: post-cutoff PR-outcome with m = 1 (0/132, U = 0.0173) and the author-unit multi-repository study. |
| R3-W2 | No evidence that the learned gate scores safer cases higher. At 92 groups only zero or full coverage can be certified. | VALID LIMITATION | Conceded; the claim is withdrawn. The sequential extension (261/311 dispatched) is not a certificate, and its error split gives one-sided Fisher p = 0.150. |
| R3-Q1 | Does any cohort have enough independent units for a 5% bound over the whole candidate-selection process? If not, revise the abstract and conclusion. | NEEDS EXPERIMENT (done); FIXABLE BY TEXT | Yes, for PR-outcome: one candidate frozen before calibration, 0/132, U = 0.0173 (0.035 under the registered grid). Multi-repository study: the registered stage admits all four run repositories (pooled 760/3, U = 0.0133); Amendment 3 admits 5 of 7 and retires node and cpython. The three primary families still have none, as the abstract and conclusion state. |
| R3-Q2 | Compare the learned gate with a support-only gate on one held-out population at two or more positive certified coverage levels. | NEEDS EXPERIMENT; VALID LIMITATION | Not run. Certifying coverage c with zero violations needs at least ⌈92/c⌉ groups. A single-look replication on the untouched issue pool was screened and recorded as no-go (197 issues with a comment, against 80 + 106 needed). |

## Points raised by more than one reviewer

| Shared concern | Reviewers | Status |
|---|---|---|
| Replay labels versus end-to-end (final-answer) guarantees | R1-W4, R1-Q2, R2-Q2 | Text fixed; end-to-end certificates added for PR-outcome. |
| Outcome-filtered calibration population | R1-W5, R1-Q3, R2-Q2 | Audit done; repair run for PR-outcome; primary claim withdrawn. |
| Independence of calibration units; selection-wide bound | R2 (strengths), R3-W1, R3-Q1 | m = 1 and author-unit designs added; primary cohorts conceded. |
| Learned gate has no demonstrated ranking value | R2-W2b, R3-W2, R3-Q2 | Claim withdrawn; matched-coverage test not run. |
| Practical value against alternatives (other compilers, handwritten, adaptive tasks) | R1-W2, R2-W1, R2-Q3 | AWM comparison and design comparison done; matched-compiler and adaptive studies not run; reframed as safe automation of the hand-written program. |

## NEEDS EXPERIMENT items and decision (Step 3)

| Item | Cheapest experiment that answers it | Status | Decision |
|---|---|---|---|
| R1-W4 / R3-Q1: end-to-end, selection-wide bound | Freeze one candidate; grade final answers on fresh, author-distinct groups | Done (0/132; multi-repository 3,560 groups) | No further run. |
| R1-W5: unfiltered population | Sample before any filter; label every eligible group | Done for PR-outcome | No further run. |
| R2-W2a, R2-W2c: individual mechanisms; drift | One-mechanism-removed study; drift studies | Done (2,304 episodes; three drift studies) | No further run. |
| R1-W2: matched compiler comparison | Same frozen tasks, model and budget across GAC and an executable compiler | Not run; 6 to 10 working days; EvoC2F has no code | Infeasible before November 18. Reply states it is designed, not run. No promise to deliver. |
| R2-Q3: adaptive workflow, three arms | Needs a derived selector for the dependent read, mid-trajectory dispatch and a competent baseline | Three attempts stopped at gates | Infeasible before November 18 (12 to 16 working days). No adaptive claim. |
| R3-Q2: learned versus support gate at two positive coverage levels | Fresh cohort of at least ⌈92/c⌉ groups for each level, with an informative entry state | Screened no-go | Infeasible: no available cohort is large enough. No ranking claim. |

No new paid experiment was run for this rebuttal pass. The three items that need one cannot finish
before November 18, and running a smaller version would not answer the question. The replies say so
and make no delivery promise.
