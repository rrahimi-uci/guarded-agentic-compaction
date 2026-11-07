# ICLR 2027 rebuttal and revision plan: "From Traces to Guarded Programs"

OpenReview forum `DF0JaS58gr`. Written 2026-11-06 for a six-day response window
(target posting: 2026-11-12; discussion closes 2026-11-18). Audience: the author and
a lower-cost coding/research agent executing the plan. Every path is repository-relative
unless stated. Every number below was re-read from the retained files named next to it.

---

## 0. Bottom line

**Current ratings:** R1 = 1 (clear reject, confidence 3), R2 = 1 (clear reject, confidence 4),
R3 = 2 (weak reject, confidence 3). Soundness 1/1/2, presentation 2/3/2, informativeness 2/1/3.

**The single largest lever is a version gap.** The reviews cite the late-September submission.
Between 2026-10-06 and 2026-11-06 the repository ran, sealed, and wrote up eight studies that
answer, partly or fully, most of the reviewers' explicit requests (Section 1.2). The reviewers
have not seen any of them. A rebuttal that puts this evidence in front of them, in their own
order of concerns, with the revised PDF uploaded, is the main chance.

**The single most valuable new experiment in six days** is not an adaptive-task comparison
(four attempts since October ended no-go) but a soundness repair the reviewers can verify:
a prospectively frozen, unfiltered, one-record-per-author, time-forward, end-to-end
calibration of the PR-outcome artifact across several repositories (Strategy B). It costs
under $5, reuses an executed and validated pipeline, and directly answers R1's population
objection, R3's "5% bound for the whole selection process" and "independent units" questions,
and R2's label-path question. It will not satisfy R2's "simple workloads" objection; nothing
feasible in six days will, and the plan says so.

**Recommendation:** Strategy A (response + revised upload, including two provider-free
additions) plus Strategy B. Strategy C (learned-gate test) only if B is sealed by Day 3.
Do not attempt Strategy D (competing compiler / adaptive benchmark) in this window.

**Honest odds.** On what looks like a four-point scale, acceptance needs two reviewers at 3
or above. R3 can plausibly move to 3; R1 can move to 2 or 3 if the presentation and
population fixes land; R2 is unlikely to move above 2. A realistic acceptance probability
after a strong rebuttal is roughly 10–20%. The same work makes the next submission
materially stronger regardless of this outcome.

---

## 1. Where things stand

### 1.1 What each reviewer fundamentally believes

| Reviewer | Core objection (in their words, condensed) | What would move them |
|---|---|---|
| R1 (1, conf 3) | Intro is hard to follow and "feels LLM written"; no comparison to EvoC2F / Agent JIT; certified loss includes downstream errors but labels are replay-only; calibration population is outcome-filtered; lifecycle policy underspecified. Five clarifying questions. | Clear answers to all five questions; a visibly cleaner introduction; an honest label/loss alignment (replay-only certificate stated as such, plus the end-to-end certificates that do exist); an accounting of every excluded record; a stated lifecycle policy. The compiler comparison can only be explained, not run. |
| R2 (1, conf 4) | Workloads are metadata lookups; handwritten program ties; value of automatic discovery unquantified; no attribution to individual mechanisms (barrier-free replay ties at 30/30; learned gate constant; drift unexecuted). Asks for a task spec, the label path, and a GAC vs unguarded vs handwritten study on one workflow with real adaptive decisions. | The drift studies and the one-mechanism-at-a-time live-recovery study now exist; the task spec and label path are documented. The adaptive comparison was attempted four times and is reported as development gates. R2 will likely remain negative but should be shown the complete attempt record and a precise plan. |
| R3 (2, conf 3) | Safety language exceeds the statistics: 0.0569 > 0.05 under candidate multiplicity; day/author units retire every family; learned gate cannot certify intermediate coverage at 92 groups. Asks whether any cohort supports a 5% selection-wide bound and for a learned-vs-support gate comparison at two or more positive certified coverage levels. | A cohort that does support a selection-wide 5% bound with independent units (Strategy B gives one). A candid statement that the graded-gate benefit is not claimed, plus the sequential-extension evidence with its correct interpretation. |

### 1.2 What the reviewers saw versus what exists now

The reviewed PDF is the late-September submission. Evidence: R2 cites "Table 19, barrier-free
replay" (the recurrence-only ablation, added 2026-09-24) and says the drift comparison "remains
unexecuted" (run 2026-10-06/07); R3 cites the 0.0569 correction and the day/author sensitivity
(added 2026-09-22); R1 proposes SKILL.nb, which the current source already cites. In the
current build (`paper/iclr/build/main.pdf`, 60 pages, main text ends on page 10), the table
numbers differ (Table 19 = four trace benchmarks; Table 23 = BIRD), so the reviewers' table
references do not match the current PDF. **Before posting, the author must download the
currently uploaded PDF from OpenReview and the agent must confirm the gap with the grep in
Appendix A.1.**

Studies the reviewers have not seen (dates = first commit to `main`):

| Date | Study | Headline | Answers |
|---|---|---|---|
| 2026-10-06 | Provider-free drift ablation (`paper/results/drift_ablation/`) | 144 paired groups, zero wrong in both arms; verifier abstains 0.2477 pooled without benefit | R2 "drift comparison unexecuted" |
| 2026-10-06 | Recorded-replay drift on primary records (`drift_recorded_replay/`) | 89 paired records, zero wrong in all three arms; suite cannot reach "wrong" for these programs | R2 same |
| 2026-10-07 | Continuation-graded drift (`drift_continuation_graded/`) | 1,080 live cells; adverse: 39/60 silent wrong in both arms under emptied lists; verifier bought abstention only | R2 same; honesty |
| 2026-10-07 | Time-forward post-cutoff PR-outcome (`time_forward/pr_outcome/`) | 132 fresh groups, end-to-end label, 0 misses, U = 0.0173 (single rule), 0.035 (registered grid); 60/60 test in every arm; retained artifact correctly abstains on its snapshot pin | R1/R2 replay-vs-final-answer; R3 "any cohort with a 5% bound?" |
| 2026-10-08 / 10-28 | Graded issue gate v2 + sequential extension (`graded_issue_gate/`) | 184 groups retire; pooled 311 groups select η = 0.50 (261/311, 4 errors, nominal U = 0.0443); sealed test 90 issues: unchanged 2/90, learned 3/90 (76 dispatched, 2 wrong after dispatch), support-only 5/90; requests 360 / 132 / 90 | R3 learned-vs-support comparison (exploratory; adaptive design) |
| 2026-10-15 | Live recovery, one mechanism at a time (`experiments/live_recovery_completion/`, `fresh_safeguards/`, `safeguard_mechanisms/`) | 2,304 scheduled episodes; scope guard raises success 186/216 → 205/216 (+8.80, [3.70, 13.89]); completeness benefit unresolved; 120 fresh issues: baseline/GAC/support-only 120/120, recurrence-only 118/120 | R2 mechanism attribution |
| 2026-10-15 | Adapted offline AWM comparison (`experiments/generalization_gate/`) | 1,362 fresh records, 8,172 episodes, two models; 5/6 cells pass five-point noninferiority; cost −36.9 to −79.1%; requests −50 to −75%; statistical gate, support-only gate and deterministic guards route identically on 2,724 cases | R1/R2 "no comparison to alternatives" (partially) |
| 2026-10-28 | Prefix census (`prefix_census/`) | 157,280 released trajectories; read-only openings 4–41% per corpus; groundable 2–13% | R2 prevalence of suitable workloads |
| 2026-11-06 | Calibration population audit (`calibration_population_audit/`) | All 396 discovery records accounted for; excluded issues #539, #2781 and PR #5700 pass the saved guard and gate, so the unfiltered-population claim is withdrawn | R1 population accounting; R2 label/filter questions |
| 2026-11-06 | Adaptive-task development gates (BIRD, AppWorld, AgentHop) | BIRD 28/36 baseline, 28/36 handwritten, 26/36 guarded candidate (requests 151/111/112); AppWorld baselines 1/12 and 2/12 below an 8/12 gate; AgentHop baseline 19/24 but no derived selector | R2 adaptive comparison (attempted; negative/incomplete) |
| 2026-10-28 / 11-06 | Text: task context before #4420, benchmark sources, manifest definition, lifecycle paragraph, TraceCompiler/EvoC2F/Agent JIT discussion, SKILL.nb | — | R1 presentation and questions |

### 1.3 Constraints that shape the plan

- **Page limit:** ten main-text pages during discussion; the current build ends Section 8 on
  page 10 with no slack. Any added main-text content must displace existing content.
- **Reviewer attention:** ICLR reviewers may ignore substantially changed revisions. The
  response text must carry the answers; the PDF supports them.
- **Budget:** $300 campaign cap, $287.90 remaining (conservative upper estimates, not invoices).
  Observed costs: unchanged agent ≈ $0.0007 per episode, compiled ≈ $0.00016 per episode
  (`paper/results/time_forward/pr_outcome/evaluation.json`). Money is not a constraint; time is.
- **Data:** the pinned `helmo/github-issues` snapshot is exhausted for fresh issue cohorts
  (127 issues remained in October and were spent). Fresh pull requests are plentiful:
  494 unused post-cutoff `huggingface/datasets` PRs (228 distinct authors, 235 distinct days;
  280 open / 206 merged / 8 closed-unmerged) already on disk, and live availability on
  2026-10-29 of 5,617 (pandas), 5,064 (streamlit), 475 (requests), 35,939 (pytorch) PRs
  since 2025-06-14 (`paper/results/matched_compiler_feasibility/REPORT.md`). GitHub API
  headroom is 5,000 calls/hour.
- **Tooling that already works:** `paper/scripts/github_time_forward_acquire.py` (one repo,
  one cutoff, comment bodies, redaction), `paper/scripts/time_forward_pr_outcome_study.py`
  (selection → discovery → frozen one-candidate compile → end-to-end calibration → test, with
  ledgered spend), `paper/scripts/validate_artifacts.py` (families incl. `time_forward_pr_outcome`,
  `iclr_page_budget`, `iclr_sources`), `tectonic --outdir build main.tex` in `paper/iclr/`.
- **Process:** every repository change goes through a PR on its own branch; the author
  merges. Nothing is posted to OpenReview by the agent; the author uploads and posts.

---

## 2. Deep review of the current paper: gaps beyond the reviews

Read against `paper/iclr/sections/*.tex`, `appendix.tex`, and `build/main.pdf` (2026-11-06).

**Presentation**
1. The abstract is a list of fourteen numbers followed by four sentences of hedges and ends on
   "remain unestablished". A reader who stops there learns what the paper does not show. It
   never states the problem in one sentence or the criterion that is the contribution.
2. The introduction opens with a census statistic (157,280 trajectories), then the #4420
   walk-through, then a refusal, then a counter-example, before saying what the paper is. The
   task context for #4420 is now present but the paragraph is still the densest in the paper.
3. The contribution list leads with "a specialization pipeline combining ..." (six nouns) and
   mentions AWM noninferiority before the reader has met AWM.
4. The main text has eleven paragraph-level study summaries in Section 5 and a 50-page
   appendix with no map other than the claims index at the very end. Reviewers cannot find
   what answers them. (R2's "Informativeness 1" is partly a navigation failure.)
5. The funnel table (Table 3 in the current build) uses "p/a/w", "slots", "at floor" without
   a plain-language key. R1 called its predecessor uninterpretable.
6. "Certificate", "compiler-wide", "per-candidate", "support-sufficiency" are used in the
   abstract before definition.

**Claims and framing**
7. The paper still describes the learned score q as part of the method (Stage 6, Algorithm 2)
   while every cohort shows it does nothing and the text says its ranking value is "open".
   Reviewers read this as an unestablished central claim. It should be explicitly demoted:
   the admission test is a support-sufficiency floor; graded selection is future work.
8. The handwritten tie is framed defensively ("we claim discovery and admission, not runtime
   dominance"). The stronger, true framing: the handwritten program is the oracle, and the
   compiler recovers it on three families, four of five repositories, two further models, one
   further provider, and a time-forward snapshot, while refusing where support is missing.
   That is the value of automation; it is currently scattered over seven places.
9. Replay versus end-to-end loss is now separated everywhere, but the one end-to-end
   certificate (132 groups) is buried in "Extended Limitations". It belongs in Section 5.

**Methodology**
10. Primary calibration populations are outcome-filtered (admitted by the paper; three
    excluded records pass the guard). No unfiltered certificate exists for any primary family.
11. Independence unit is the record; day/author units retire every primary family. The
    time-forward study reports day/author bounds (0.0228, 0.0267) only as hypotheticals.
12. PR-outcome and backlog certificates are per-candidate (m = 2, U = 0.0569). The pre-registered
    106-group repair was NO-GO for class availability in the pinned snapshot.
13. The 311-group extension is an adaptive, mixed-frame design; its nominal admission cannot be
    presented as a certificate. The sealed-test comparison (3/90 vs 5/90) is suggestive only.
14. The learned score is constant within a repository whenever entry state is a record number.
    A graded gate cannot be tested on PR-outcome without an informative entry schema.

**Missing experiments (as the reviewers see them)**
15. Matched competing-compiler comparison (EvoC2F has no public implementation: HTTP 401;
    Agent JIT is a browser planner in the BLAST tree; AWO unreleased). Not feasible faithfully.
16. Adaptive-task quality–cost comparison (four development gates, all no-go).
17. Learned vs support-only gate at two or more positive certified coverage levels.
18. Unfiltered calibration sampled before outcomes with labels for every eligible group.

Items 1–9 are writing. Items 10, 11, 12, 18 are addressed by Strategy B. Item 17 is Strategy C.
Items 15–16 cannot be closed in six days and must be answered with the attempt record.

---

## 3. Concern map: reviewer concern → paper location → current state → fix type

Section numbers refer to the current source (`paper/iclr/sections/`, `appendix.tex`).

| # | Reviewer | Concern | Where in paper | Current local state | Fix type |
|---|---|---|---|---|---|
| 1 | R1 | Intro hard to follow; #4420 without context | §1 ¶3 | Task sentence added before #4420; still dense | Writing (rewrite ¶1–3) |
| 2 | R1 | No comparison to EvoC2F / Agent JIT | §6, App. "Scope of automated workflow-reuse comparison" | Discussed; comparator audit retained (`experiments/matched_reuse_baseline/COMPATIBILITY.md`) | Explain; cannot run faithfully |
| 3 | R1 | Table 2 (funnel) uninterpretable | §5.3 Table 3 | Unchanged columns | Writing (caption key, plain-word columns) |
| 4 | R1, R2 | Certified loss includes downstream errors; labels are replay-only | §2 "Fix a binary loss", §3 Stage 6, App. "Calibration labels as computed", Table certificates | Replay-only stated; end-to-end certificate exists for 132 post-cutoff groups | Writing + Strategy B adds multi-repo end-to-end certificates |
| 5 | R1, R2 | Calibration population outcome-filtered; excluded records could pass the guard | §4 ¶1, App. "Calibration population audit" | Audit complete: 396 records; 3 excluded pass guard/gate; unfiltered claim withdrawn | Strategy B (sample before outcomes; label everything) |
| 6 | R1 | Lifecycle policy underspecified | App. "Implemented lifecycle controls and proposed renewal policy" | Implemented vs proposed separated; SKILL.nb cited | Writing (one sentence in §7 pointing to it) |
| 7 | R1 Q1 | Complete benchmark references | §4 "Public benchmarks" | Cited: helmo snapshot, BIRD, NESTFUL, AppWorld, API-Bank, BFCL v4 | Writing (response lists them) |
| 8 | R1 Q2 | Which 92-group tables include downstream errors | App. "Calibration labels as computed" | None do; stated | Writing (direct answer) |
| 9 | R1 Q3 | Account for every excluded record | App. population audit | Done (14/15/16 unused; 2/1/0 excluded; 3 pass guard) | Writing (direct answer) + B |
| 10 | R1 Q4 | Recompilation / retirement triggers | App. lifecycle | Stated as implemented vs proposed | Writing |
| 11 | R1 Q5 | Define content-addressed execution manifest | §2 ¶2 | Defined | Writing (quote it) |
| 12 | R2 | Workloads simple; handwritten ties; automation value unquantified | §5.1, Table 1, manual table | Admitted in text; AWM comparison shows automated reuse costs 2–4× more; break-even 411/183/181 episodes | Writing (compiler-decisions table; reframing) + attempt record |
| 13 | R2 | Mechanism attribution (Table 19 replay ties; Table 23 gate constant; drift unexecuted) | §5.1 "What simpler compilation achieves", §5.4 "Live recovery", App. drift ×3 | Drift run (null/null/adverse); scope-guard effect +8.80 one-at-a-time | Writing (response) |
| 14 | R2 Q1 | Complete task specification; which decisions are semantic | §4, App. "Primary workflow families", `github_workflow_family_study.py` | Specified; none require semantic reasoning | Writing (say so plainly) |
| 15 | R2 Q2 | How labels are generated; filtering before split | App. "Calibration labels as computed", population audit | Documented | Writing + B |
| 16 | R2 Q3 | GAC vs unguarded vs handwritten on one adaptive workflow | App. "Adaptive-Task Development Gates" | Attempted ×4; no-go; BIRD candidate 26/36 vs handwritten 28/36 | Attempt record + protocol; not runnable in 6 days |
| 17 | R3 | Safety language stronger than statistics; 0.0569; day/author units | Abstract, §3, §5.4, §7, Tables multiplicity/effective units | Stated | Writing + B (author units, m = 1, n ≥ 200) |
| 18 | R3 | Learned gate: certify ≥ 2 positive coverage levels; compare to support-only | §3 Stage 6, App. gate extension, prospective protocol | Extension exploratory; demotion of q | Writing (demote q) + Strategy C (optional) |
| 19 | R3 Q1 | Any cohort with independent units supporting a selection-wide 5% bound? | App. certificates (post-cutoff 132: m = 1, U = 0.0173; authors 0.0267) | Yes, one family, one repo, single rule | B extends to several repos, author units, registered grid |
| 20 | R3 Q2 | Learned vs support gate at matched positive coverage | App. gate extension | 3/90 vs 5/90 at unmatched coverage | C or honest "not established" |

---

## 4. Writing-fixable versus evidence-needed

**Fixable by rewriting or clarification (no provider calls):** 1, 3, 6, 7, 8, 10, 11, 14, and the
framing parts of 4, 12, 13, 17, 18. Also a provider-free "compiler decisions" table (Section 6,
Strategy A, item A3).

**Already answered by evidence the reviewers have not seen:** 4 (132-group end-to-end), 5
(audit), 9, 13 (drift ×3, live recovery), 15, 19 (one cohort), and the AWM comparison for 12.

**Needs new evidence, feasible in six days:** 5/17/19 via Strategy B; 18/20 partially via
Strategy C (optional, likely null).

**Needs new evidence, not feasible in six days:** 2 (faithful competing compiler), 16 (adaptive
workflow with a useful derived program and competent baseline).

---

## 5. Highest-impact changes, ranked

1. **Put the version gap in front of the reviewers** (a global comment plus per-reviewer
   mapping) and upload the revised PDF. Zero risk, largest expected effect.
2. **Rewrite the abstract, first page, and contribution list** to lead with the criterion and
   the evidence, and to state the scope once, positively. Affects R1 and R3 presentation
   scores and R2's informativeness.
3. **Run Strategy B** (unfiltered, author-unit, multi-repository, end-to-end calibration)
   and report it in Section 5 and the certificate table. Affects soundness for R1 and R3.
4. **Demote the learned score** from a claimed component to an implemented-but-unclaimed
   mechanism; make the admission test a support-sufficiency floor in the text. Removes the
   weakest claim rather than defending it. Affects R2 and R3.
5. **Add the compiler-decisions table** (admit / retire across repositories, models, providers,
   snapshots, benchmarks). Answers "value of automation" with retained evidence. Affects R2.
6. **Move the end-to-end certificate paragraph from Extended Limitations into Section 5.4**
   and the drift and live-recovery results into one "mechanism evidence" paragraph.
7. **Answer every question literally and in order**, each with section pointer and file path.

---

## 6. Four revision strategies

### Strategy A: Response plus revised upload (writing only)

**Rationale.** The reviewers' version is six weeks stale; most explicit requests have a
retained answer. The paper's framing currently hides its contribution behind hedges.

**Scope.**
- A1. Abstract (≤ 200 words): problem; criterion (compile only grounded, read-only, in-position
  prefixes; refuse otherwise; admit under a finite-sample support floor); what is measured
  (savings on three GitHub families and BIRD; refusals on NESTFUL/API-Bank/BFCL; AppWorld
  admissible but rarely dispatchable); what is certified (replay on selected populations;
  end-to-end on time-forward PR-outcome); one scope sentence.
- A2. §1 rewrite: ¶1 problem in three sentences; ¶2 the #4420 example in six lines with the
  task defined first; ¶3 the three obligations; contributions as three one-sentence bullets.
  Cut the census to one clause with an appendix pointer.
- A3. New main-text Table "What the compiler decided without human input": rows = three
  primary families; five cross-repository repos (4 admit / pytorch retire); time-forward
  re-derivation (identical program; retained artifact abstains on pin); gpt-6-luna re-discovery
  (2 identical / backlog refused); claude-sonnet-5 (2 identical / backlog refused at 90–91 of
  92); BIRD per-question (retire ×5) and schema-first (admit 26/31); NESTFUL / API-Bank / BFCL
  (retire at n_max 26/8/15 < 92); AppWorld (1 admit / 4 retire); BFCL getter-that-mutates
  (effect barrier). Columns: what it saw, what it decided, why, what a human program would
  have needed to know. All numbers from retained files (`tables/mechanism_removal.tex`,
  `tables/gate_profile.tex`, `tables/second_model.tex`, `tables/second_provider.tex`,
  `tables/multirepo_results.tex`, `time_forward/pr_outcome/`).
- A4. §3 Stage 6 and §5.4: state that q is implemented, that every admitted operating point is
  full coverage, that the certificate is a support floor, and that graded selection is not
  claimed. Remove "learned-gate benefit remains unestablished" phrasing in favour of "not
  claimed".
- A5. Move the 132-group end-to-end certificate into §5.4 (two sentences); fold drift and
  live-recovery into one "mechanism evidence" paragraph in §5.4.
- A6. Funnel table: plain-word column names and a one-line key.
- A7. §7 lifecycle: one sentence naming implemented controls and pointing to the appendix.
- A8. §8 conclusion: positive scoped statement (three sentences).
- A9. To stay within ten pages: move the evidence-scope table to the appendix (the certificate
  table already covers it); compress the AWM and BIRD paragraphs by ~6 lines each.
- A10. Rebuttal text (Section 11 of this plan).

**Expected impact.** R1 presentation 2→3 plausible, rating 1→2 plausible; R3 2→3 plausible if
the honest scope and the 132-group answer satisfy Q1; R2 unchanged or 1→2.

**Risks.** Reviewers may not re-read; a heavily changed first page may be seen as a different
paper. Mitigation: keep the method, results tables, and numbers unchanged; change framing only.

**Effort.** 2–3 agent-days writing and validation; 0.5 author-day review.

### Strategy B: A + unfiltered, author-unit, multi-repository end-to-end calibration

**Rationale.** The three soundness objections that are statistical rather than philosophical
(filtered population, candidate multiplicity, dependent units) can all be answered by one
prospectively frozen study on data the paper already knows how to process. The time-forward
PR-outcome pipeline executed this design on one repository for $0.22 and admitted.

**Design (freeze before any provider call; protocol file in Section 8, WP0).**
- Family: `pr_outcome`, full three-read task (record, merge status, discussion), hand-written
  program and unchanged agent as paired arms.
- Repositories: `huggingface/datasets` (existing post-cutoff snapshot; frozen re-derived
  artifact `cand-00-a1de3856bb6c` from `paper/results/time_forward/pr_outcome/registry`),
  plus fresh acquisitions of `pandas-dev/pandas`, `streamlit/streamlit`, `psf/requests`
  (cutoff 2026-01-01) and `pytorch/pytorch` (cutoff 2026-08-01, expected refusal as in both
  earlier studies; a refusal is a result).
- Sampling unit: one pull request per distinct author (`user.login`), chosen by stable hash;
  distinct creation days reported. No exact-trace filter, no class filter; every sampled
  group is labelled: guard-ineligible (not in n), clean abstention (in n, L = 0), dispatched
  and contract met, dispatched and contract missed (violation, in k). Fallback continuations
  are also graded and reported.
- Candidate: one frozen candidate per repository (m = 1) re-derived from a 132-record
  discovery split disjoint in records and authors from calibration, exactly as the
  time-forward study did (`freeze_one_candidate_before_calibration = true`).
- Sample size: n = 200 author-distinct calibration groups per repository, fixed. Decision
  rules computed in advance (Appendix A.3): registered grid, m = 1: admit iff k ≤ 3
  (U(k=0) = 0.0232, U(k=3) ≤ 0.05); single rule γ = δ = 0.10: admit iff k ≤ 5. Report both;
  the registered grid is primary because it is the paper's registered procedure. Pooled
  four-repository population (n = 800) is a pre-declared secondary estimand: admit iff
  k ≤ 25 (registered grid).
- Paired quality: unchanged agent on the same 200 groups; exact McNemar; one-sided 95%
  bound on compiled-only misses (0.0149 at 0/200). Resource reductions as in Table 1.
- Spend cap: $5 per repository, $25 total; pilot of ten groups per repository first.

**Expected impact.** Converts the paper's certificate story from "replay on a selected
population, per-candidate, record units" to "end-to-end, unfiltered, author units,
compiler-wide (m = 1), four repositories, time-forward". Answers R1 (population, label path),
R3 Q1 and the units objection, and R2 Q2 and "behavior under realistic changes" (time-forward
is natural drift). It does not make the task adaptive and must not be presented as doing so.

**Risks.** (i) A repository's discovery retires (report it; three repositories suffice).
(ii) Violations exceed the floor (report the retirement and the rate; still an honest
unfiltered estimate). (iii) Acquisition or adapter bugs on a new repository (fall back to the
`huggingface/datasets` snapshot alone, which needs no acquisition and no discovery).
(iv) R2 will say the task is still simple. True; say so.

**Effort.** 2.5 agent-days (acquisition 0.5, preflight/selection/protocol 0.5, live 0.5,
analysis/validator/tables 0.5, write-up 0.5); under $5.

### Strategy C: B + fixed-size prospective learned-vs-support gate test

**Rationale.** R3 asked for it explicitly. The only workload with a nonzero end-to-end error
rate and an informative entry schema is the graded issue task (≈1.3% errors on 311 groups).

**Scope.** The untouched post-cutoff `huggingface/datasets` issue pool (≈275 issues with at
least one comment, never used; `paper/results/datasets/github_time_forward/huggingface__datasets/preflight.json`):
80 issues for candidate re-derivation (the v2 candidate pins the old snapshot and would
abstain everywhere), ≈195 for a single-look calibration under the frozen v2 score and grid
(`graded_issue_gate/frozen_gate_v2.json`), with the entry read of six descriptors. Pre-declare:
one look; primary endpoint = admission at η = 0.50 (needs k ≤ 2 at n ≈ 195 under the
registered grid); secondary = descriptive frontier and Fisher split at η = 0.02.

**Expected impact.** A clean prospective replication of the extension's admission would
strengthen R3's confidence in the gate on this workload; a retirement would justify dropping
the learned score entirely (which Strategy A does anyway). It cannot certify two positive
levels (η = 0.02 accepts ≈ 37%, i.e. ≈ 73 groups < 92), so it does not fully answer R3 Q2.
A two-level design needs ≈ 400 groups, which requires acquiring `pandas-dev/pandas` issues
with comment bodies and mapping its label taxonomy to the task's categories: a new task
specification, not safe to improvise in six days.

**Risks.** Expected violations on 195 groups are 2.5–4; admission probability is roughly a
coin flip; a retirement adds little the paper does not already say. Competes for the same
agent-days as B.

**Effort.** 1.5 agent-days, under $1. Run only if B is sealed and analysed by end of Day 3.

### Strategy D: competing-compiler or adaptive-task comparison

**Rationale.** R1 and R2's central empirical requests.

**Scope.** Port Agent JIT's planner to GitHub tasks, or complete one of the BIRD / AppWorld /
AgentHop / Reddit designs with a derived state-dependent program and competent baseline.

**Expected impact.** Only a positive, faithful result would move R2. The attempt record shows:
EvoC2F has no inspectable implementation (401); Agent JIT is a browser planner whose cited
commit lives in the BLAST tree and whose current main is a different VM; the BIRD one-call
candidate scored 26/36 against 28/36 for the handwritten wrapper; AppWorld baselines failed
their competence gate; AgentHop has a competent baseline but no derivable selector.

**Risks.** Very high: a rushed port invites "mismatched comparator"; an adverse result in the
rebuttal is worse than a stated gap; the four prior gates each took days. **Do not run.**
Instead: report the gates, cite the frozen protocol (`paper/supplementary/matched-compiler-candidate-protocol.md`),
and state what a valid study requires.

**Effort.** 4–6 agent-days minimum, outcome uncertain.

---

## 7. Recommendation

Execute **A + B** as the core, in parallel streams (writing stream, experiment stream), with
**C** conditional on B finishing early, and **D explicitly declined** in the response with the
attempt record. Order of value: A1–A5 and B together; then A6–A9; then C.

Why not B alone with the old framing: the reviewers' presentation and informativeness scores
are driven by framing, and R2's score will not move on evidence of this kind. Why not C
first: it is a coin flip with limited upside, and B's upside is certain to be reportable
(admission or an honest unfiltered rate).

---

## 8. Execution plan for the agent

Conventions: `R=/Users/rezarahimi/Documents/GitHub/personal/guarded-agentic-compaction`;
Python is `$R/.venv/bin/python`; run from `$R`. Never run a live phase without
`--approved-spend-usd`. Every live run writes a ledger; copy its total into
`paper/iclr/notes/campaign_ledger_2026-11.md`. Retain every attempt, including failures.
Commit the protocol before the first provider call and record that commit hash in the
protocol file. Do not edit a protocol after a result is observed; append a dated amendment.

### WP0: Setup and freezing (Day 0, tonight)

| Task | Action | Output | Check |
|---|---|---|---|
| 0.1 | `git checkout -b paper/iclr-rebuttal-2026-11 main` (writing stream) and `git checkout -b experiment/multirepo-unfiltered-end-to-end main` (experiment stream). Keep both PRs small enough to review. | two branches | `git status` clean |
| 0.2 | Author: download the uploaded PDF from OpenReview to `paper/reviews/openreview_submitted.pdf`. Agent: run the grep in Appendix A.1 against it and `paper/iclr/build/main.pdf`; write `paper/iclr/notes/version_gap_2026-11.md` with the table from Section 1.2, corrected by what the grep shows. | version gap note | Each row's "unseen" status confirmed |
| 0.3 | Sanity: `$R/.venv/bin/python -m pytest -q tests/unit -x -q` (should pass); `gh api rate_limit`; confirm `.env` has `OPENAI_API_KEY` and `GITHUB_TOKEN` (do not print). | — | exit 0 |
| 0.4 | Write `paper/supplementary/multirepo-unfiltered-end-to-end-protocol.md` from the Strategy B design, with the decision rules in Appendix A.3, repository list, cutoffs, n = 200, exclusion rule, pilot size, spend caps, and the sentence "No label is inspected before all repositories' selections are written." Commit. | protocol, commit hash | hash written into the protocol's status line |

### WP1: Strategy B experiment (Days 1–3, experiment stream)

| Task | Action | Files | Output | Validation | Depends on |
|---|---|---|---|---|---|
| 1.1 | **Generalise the study script.** Add to `paper/scripts/time_forward_pr_outcome_study.py`: `--snapshot-dir`, `--registry` (optional frozen artifact; skip discovery when given), `--unit author` (one PR per `user.login`), `--calibration-n 200`, `--no-test`, `--arms compiled,baseline,manual` for the calibrate phase, and `--repo-tag` used in the stable hash. Keep the existing default behaviour byte-identical (the retained study must still validate). | `time_forward_pr_outcome_study.py`, new `tests/unit/test_time_forward_multirepo_selection.py` | selection logic covered by unit tests on a synthetic store | `pytest tests/unit/test_time_forward_multirepo_selection.py`; `validate_artifacts.py --families time_forward_pr_outcome` still passes | 0.4 |
| 1.2 | **Repo-qualified exclusions.** Extend `paper/scripts/github_time_forward_preflight.py` with `--snapshot-dir` and `--repo`; exclude only record numbers used by studies of the same repository (`github_multirepo*` results for pandas/streamlit/requests/pytorch; `time_forward`, `github_*`, `graded_issue_gate`, `experiments/` for huggingface/datasets). Output pool size, class counts, distinct authors and days. | preflight script; `paper/results/multirepo_end_to_end/<repo>/preflight.json` | preflight per repo | counts ≥ 132 + 200 authors, else record a reduced n in the protocol amendment before selection | 0.4 |
| 1.3 | **Acquire fresh snapshots** (provider-free, GitHub API): `github_time_forward_acquire.py --repo pandas-dev/pandas --cutoff 2026-01-01 --out paper/results/datasets/github_time_forward/pandas-dev__pandas`; same for `streamlit/streamlit`, `psf/requests` (cutoff 2026-01-01), `pytorch/pytorch` (cutoff 2026-08-01). Run in background; each takes up to an hour. Confirm the parquet columns equal the huggingface snapshot's. Do not re-acquire huggingface/datasets. | snapshots + `source_manifest.json` | four parquet files | redaction counter printed; `pull_request` column non-null for PRs; API remaining > 500 | 0.3 |
| 1.4 | **Selection** (provider-free): `--phase selection --unit author --calibration-n 200 --no-test` per repo; for huggingface/datasets pass `--registry paper/results/time_forward/pr_outcome/registry` so discovery is skipped and the frozen artifact is reused; calibration draws from the 494 unused PRs, one per author (228 available → n = 200). Write all five `selection.json` before any provider call; digest them; commit. | `paper/results/multirepo_end_to_end/<repo>/selection.json` | five selections | `disjoint: true`; author sets disjoint from discovery; class counts recorded; commit hash appended to the protocol | 1.1, 1.2, 1.3 |
| 1.5 | **Discovery + frozen compile** (live, ≈ $0.10 per repo): `--phase discovery --approved-spend-usd 2` for the four new repos. A repository whose compiler admits no artifact retires; record and continue. | `discovery_checkpoint.json`, `compile.json`, `registry/` | one frozen artifact per admitting repo | program equals the retained three-read program up to pins (expected); replay gate 92/0 inside the discovery split | 1.4 |
| 1.6 | **Pilot** (live): `--phase calibrate --pilot 10 --arms compiled,baseline,manual --approved-spend-usd 1` on huggingface/datasets first. Inspect ten rows: dispatch, grade, requests. Stop on any adapter error. | `calibration_checkpoint.json` | ten labelled groups | every row has `eligible`, `dispatched`, `contract_met` for each arm | 1.4 (hf) |
| 1.7 | **Calibration** (live, ≈ $0.25 per repo): `--phase calibrate --arms compiled,baseline,manual --approved-spend-usd 5` per repo, batches of 8, checkpointed, no retries (the protocol fixes no retry rule; a timed-out episode stays in the denominator as recorded). | `calibration_checkpoint.json`, `certificate.json`, `ledger.json` | 200 labelled groups per admitting repo | ledger total < cap; no missing rows | 1.5, 1.6 |
| 1.8 | **Analysis** (provider-free): new `paper/scripts/multirepo_end_to_end_analysis.py` producing `paper/results/multirepo_end_to_end/summary.json`: per repo and pooled n, k, U under registered grid (m = 1) and single rule; admission decision per the frozen rule; distinct authors (= n) and days; paired baseline vs compiled discordance with exact McNemar; one-sided bound on compiled-only misses; mean requests/tokens/latency/cost per arm and reductions; retired repositories listed. Generate `paper/iclr/tables/multirepo_end_to_end.tex`. | script, summary, table | table + JSON | re-running regenerates identical files (`git diff` empty); unit test on a synthetic checkpoint | 1.7 |
| 1.9 | **Validator family** `multirepo_end_to_end` in `paper/scripts/validate_artifacts.py`: pins n, k, U, decisions, digests, ledger total; adds the new table to `iclr_sources`. Add the numbers to `paper/iclr/notes/number_registry.md` and a row to `tables/claims_evidence_index.tex` and `tables/certificate_summary.tex`. | validator, registry | checks pass | `validate_artifacts.py` full run: 0 failed | 1.8 |
| 1.10 | **Write-up**: appendix subsection "Unfiltered end-to-end calibration across repositories" (≈ 25 lines, decision rules first, adverse rows first), two sentences in §5.4 replacing the single-repo sentence, one clause in the abstract, one row in the certificate table, one sentence in §7 (units). Update `paper/supplementary/evidence-register.md`. | sections, appendix | revised PDF | page 10 still ends Section 8; validator 0 failed | 1.9 |

**Minimal viable B (if time is short):** run 1.1, 1.4 (huggingface/datasets only, frozen
registry, no acquisition, no discovery), 1.6, 1.7, 1.8, 1.9, 1.10. One day, under $1. This
already yields an unfiltered, author-unit, m = 1, n = 200 end-to-end certificate on fresh
records, which is more than the paper has today.

### WP2: Strategy A writing (Days 1–4, writing stream)

| Task | Files | Exact task | Validation |
|---|---|---|---|
| 2.1 | `paper/iclr/sections/abstract.tex` | Rewrite per A1. Keep ≤ 200 words and ≤ 6 numbers: 90/90 vs 89/90 and 66.6%; 26/31 BIRD databases; 132-group end-to-end bound 0.0173 (plus Strategy B's pooled result when available); retire counts for the three trace benchmarks. End with one scope sentence, not a list of unestablished things. Regenerate `paper/iclr/notes/openreview_metadata.md` abstract via `pdftotext -f 1 -l 1`. | word count; abstract in PDF matches metadata note word for word |
| 2.2 | `sections/introduction.tex` | Rewrite per A2. Keep the #4420 example but define the task in one sentence first, then the three reads, then the refused slot, then the surviving prefix: six lines. Cut the census to one clause with `\cref{app:prefix-census}`. Contributions: three bullets, one sentence each, each with a `\cref`. Remove the AWM mention from the contributions (it stays in §5). | page 1 reads top-down without forward references; no number appears before its noun |
| 2.3 | `sections/results.tex`, new `tables/compiler_decisions.tex`, `paper/scripts/iclr_revision_statistics.py` (new subcommand `decisions`) | Build Table "What the compiler decided without human input" (A3) from retained files; generated, not hand-maintained; add a validator pin. Place at the top of §5 with a three-sentence lead: the hand-written program is the oracle; the compiler recovers it where support exists and refuses where it does not. | numbers traceable to the files listed in A3; table ≤ 12 rows, `\footnotesize` |
| 2.4 | `sections/method.tex` (Stage 6), `sections/results.tex` (§5.4) | Per A4: three sentences stating that q is implemented, every admitted operating point is full coverage, the certificate is a support floor, graded selection is not claimed. Delete "learned-gate benefit remains unestablished" wording everywhere (`grep -rn "learned-gate benefit\|learned selectivity" sections/ appendix.tex`). | grep returns only the appendix sentences that describe the extension |
| 2.5 | `sections/results.tex` §5.4, `appendix.tex` | Per A5: move the two-sentence 132-group end-to-end certificate from `app:limits` into §5.4 "Admission scope"; merge "Live recovery" and the three drift results into one paragraph "Mechanism evidence" (scope guard +8.80 first, drift null/null/adverse second). | §5.4 ≤ its current length |
| 2.6 | `sections/results.tex` (funnel table caption), `tables/refusal_funnel.tex` header | Per A6: rename "p/a/w" to "pass / abstain / wrong", "slots" to "grounded slots", add a one-line key. | caption ≤ 6 lines |
| 2.7 | `sections/discussion.tex` | Per A7: one sentence on implemented lifecycle controls with `\cref{app:lifecycle}`. Replace the first paragraph's "810 episodes" with the compiler-decisions pointer if space is needed. | — |
| 2.8 | `sections/conclusion.tex` | Per A8: three sentences, positive and scoped. | — |
| 2.9 | `sections/results.tex`, `appendix.tex` | Per A9: move `tab:evidence-scope` to the appendix next to `tab:certificates`; compress AWM and BIRD paragraphs by ~6 lines each; fix all `\cref`s. | `tectonic --outdir build main.tex` from `paper/iclr/`; `pdftotext -f 10 -l 10 build/main.pdf - | tail -5` shows the conclusion; page 11 begins with the AI Use Statement; `pdftotext -f 1 -l 1 build/main.pdf - | head -3` says Anonymous authors; `pdfinfo build/main.pdf | grep Author` prints nothing |
| 2.10 | `paper/iclr/notes/rebuttal_changes_2026-11.md` | For each change: reviewer concern id (Section 3 table), file, old sentence, new sentence, evidence path. This file is the source for the response's "where changed" pointers. | every row has all five fields |
| 2.11 | Full validation | `$R/.venv/bin/python paper/scripts/finalize_manifest.py && $R/.venv/bin/python paper/scripts/validate_artifacts.py` (0 failed); `$R/.venv/bin/python -m pytest -q`; `git diff --check`. | all green; record outputs in the PR |

### WP3: Rebuttal composition (Days 4–5)

| Task | Output | Rule |
|---|---|---|
| 3.1 | `paper/iclr/notes/rebuttal/00_global_summary.md` (≤ 4,500 characters) | Opening: thank; one sentence on what changed and why (version gap); the Section 1.2 table reduced to eight rows (study, what it answers, where in the revised PDF); one paragraph on scope (what is and is not claimed). No new claims beyond the PDF. |
| 3.2 | `rebuttal/R1.md`, `rebuttal/R2.md`, `rebuttal/R3.md` (each ≤ 4,500 characters per part; split into Part 1/2 if needed) | Answer every weakness and every question, in the reviewer's order, with the four-part pattern: direct answer; what changed (section); evidence (file path or table); what remains open. Templates in Section 11. |
| 3.3 | Number consistency check | Every number in the responses appears in `number_registry.md` and in the PDF: `grep -o '[0-9][0-9.,/%]*' rebuttal/*.md | sort -u` reviewed by hand against the registry. |
| 3.4 | Tone pass | No "we believe", no "unfortunately", no apology beyond the opening. State limits once each. Never say a reviewer overlooked something; they did not have it. |
| 3.5 | Author read-through | 30 minutes; fix anything that reads as defensive. |

### WP4: Upload and posting (Day 6, author)

1. Verify the revised PDF and supplementary archive locally
   (`paper/scripts/build_anonymous_archive.py --out <scratch>/gac-iclr2027-review.zip`).
2. Upload the revised PDF on OpenReview; confirm the diff view shows the expected pages.
3. Post the global summary as a top-level official comment, then the three reviewer responses
   as replies to each review. If a comment exceeds the length limit, post Part 2 immediately
   after Part 1 with a clear header.
4. Record the posting time and the uploaded PDF's SHA-256 in
   `paper/iclr/notes/review_revision_status_2026-11-06.md`.
5. Watch for reviewer replies through 2026-11-18; keep the experiment branch ready for
   follow-up questions (e.g., per-repository tables on request).

### WP5 (optional): Strategy C (Days 3–4, only if WP1 is sealed by Day 3)

| Task | Action | Output |
|---|---|---|
| 5.1 | Protocol `paper/supplementary/fresh-issue-gate-single-look-protocol.md`: pool = post-cutoff `huggingface/datasets` issues with ≥ 1 comment, never used (verify via the preflight exclusion scan); 80 discovery issues by stable hash; all remaining as the single calibration look (n ≈ 195, fixed by pool); frozen v2 score/grid/budgets (`frozen_gate_v2.json` hash); decision rule: registered grid, m = 1 → admit at η = 0.50 iff k ≤ 2 at n = 195 (recompute exactly with `cp_upper` for the actual n); secondary: descriptive sweep and Fisher split at η = 0.02; no test arm. | protocol, commit hash |
| 5.2 | Re-derive the candidate from the 80 fresh discovery issues with `graded_issue_recompile_candidate.py` bound to the time-forward snapshot (add `--snapshot-dir`). | `candidate_tf/` |
| 5.3 | Run `graded_issue_gate_study.py` with a new `--time-forward` mode (bind snapshot; calibration only; `--approved-spend-usd 3`). | `results_tf.json`, `audit_tf.json` |
| 5.4 | Audit script → table `tables/gate_single_look.tex`; appendix paragraph; one sentence in the R3 response. | — |

### WP6: PR hygiene (continuous)

- Two PRs: `paper/iclr-rebuttal-2026-11` (writing, notes, rebuttal drafts) and
  `experiment/multirepo-unfiltered-end-to-end` (protocol, scripts, results, tables, appendix
  subsection). Merge the experiment PR first, then rebase the writing PR; or keep the
  write-up of the experiment (task 1.10) in the writing PR to avoid conflicts in `sections/`.
- Fill every section of `.github/pull_request_template.md`; paste validator and pytest output;
  state spend; add the author as assignee (reviewer self-request is dropped by GitHub).
- Never merge; leave both PRs open for the author.

---

## 9. Six-day schedule

| Day | Date | Experiment stream | Writing stream | Milestone (end of day) |
|---|---|---|---|---|
| 0 | Thu 11-06 (tonight) | WP0: branches, protocol frozen and committed, sanity checks, start acquisitions (1.3) in background | 0.2 version-gap note | Protocol hash recorded; acquisitions running |
| 1 | Fri 11-07 | 1.1, 1.2, 1.4 (hf/datasets selection with frozen registry), 1.6 pilot, 1.7 hf/datasets calibration (200 groups) | 2.1 abstract, 2.2 introduction, 2.10 ledger started | **Minimal viable B sealed** (hf/datasets 200 author-distinct end-to-end groups); abstract and intro drafts |
| 2 | Sat 11-08 | 1.4 selections for the four new repos (committed before any call), 1.5 discovery + frozen compile, 1.7 calibration for pandas and streamlit | 2.3 compiler-decisions table, 2.4 demotion of q | Two more repositories labelled; Table built |
| 3 | Sun 11-09 | 1.7 requests and pytorch (or recorded retirement), 1.8 analysis, 1.9 validator + registry | 2.5, 2.6, 2.7, 2.8 | **B analysed and validated**; decision on WP5 (go only if 1.9 is green) |
| 4 | Mon 11-10 | 1.10 write-up into appendix/§5.4/abstract; (optional) 5.1–5.3 | 2.9 page budget, build, anonymity checks; 2.11 full validation | **Revised PDF candidate**; both PRs open with green CI |
| 5 | Tue 11-11 | (optional) 5.4 | 3.1–3.4 rebuttal drafts; 3.5 author read-through | **Rebuttal drafts final**; numbers reconciled |
| 6 | Wed 11-12 | — | WP4 upload and post | Posted; status note updated |

Hard rules: no new provider calls after Day 4 noon; no manuscript edits after Day 5 noon except
number corrections; if Day 3's milestone slips, drop WP5 and the three extra repositories and
ship minimal viable B.

---

## 10. Interpreting the new evidence (what each outcome licenses)

**Strategy B outcomes.**
- *k ≤ 3 of 200 per repository (registered grid, m = 1):* "For this frozen artifact, the
  end-to-end task-contract violation rate on fresh pull requests of repository X, sampled one
  per author without outcome filtering, is at most U with confidence 0.90, conditional on
  independent authors." This is compiler-wide (m = 1), end-to-end, unfiltered, author-unit.
  Say exactly that. Do not say "safe", "guaranteed", or "accuracy-preserving".
- *Pooled k ≤ 25 of 800:* a pooled population statement across four repositories; say it is a
  second, pre-declared estimand and that repositories are not exchangeable.
- *k above the floor:* report the observed rate and its bound; the artifact retires for that
  repository under the registered rule; describe the violating records. This is still the
  first unfiltered estimate of the end-to-end rate and answers R1's question honestly.
- *Repository retires at compile:* a refusal result; add to the compiler-decisions table.
- *Paired comparison:* if compiled-only misses are 0, give the one-sided bound (0.0149 at
  n = 200); do not claim equivalence or noninferiority unless a margin was pre-declared (it is
  not in this design; the end-to-end certificate is the primary endpoint).
- *What it never shows:* adaptive-task value, learned-gate value, superiority over the
  handwritten program (expected tie), or anything about issue-type or backlog families.

**Strategy C outcomes.**
- *Admission at η = 0.50 with k ≤ 2:* a prospective single-look replication of the extension's
  admission on an independent fresh cohort; one certified positive coverage level; the
  support-only comparison remains at unmatched coverage. Still "no graded selectivity shown".
- *Retirement:* report; strengthens the decision to make no learned-gate claim.

**Existing evidence to present with care.**
- The 311-group extension: nominal admission only; cite `interpretation_correction.md`.
- The AWM comparison: noninferiority at five points in 5/6 cells; not a compiler comparison.
- The live-recovery scope-guard effect: constructed requests; one mechanism; not drift.
- The adaptive gates: development diagnostics; never "GAC superiority".

---

## 11. Documenting changes in the rebuttal

### 11.1 Global summary comment (structure)

1. Thanks and one sentence: the reviews cite the September submission; since then we ran the
   pre-registered studies several of you asked for and revised the paper; the PDF diff shows
   the changes; nothing in the method or primary tables changed.
2. Table (≤ 8 rows): study | question it answers | section in the revised PDF.
3. Scope statement (four sentences): what GAC claims (compile-or-refuse criterion for initial
   read-only prefixes; measured savings; support-floor admission; explicit refusals), what it
   does not claim (adaptive-task superiority; learned-gate benefit; universal accuracy
   preservation), and that the paper now says so in the abstract.
4. One sentence on the two experiments that cannot be completed in the window (competing
   compiler; adaptive workflow) and where the attempt record and protocol are.

### 11.2 Per-reviewer response template (apply to every weakness and question, in order)

```
**[W1] <reviewer's concern in ≤ 12 words>**
Answer: <one to three sentences; the direct answer first>.
Changed: <§x / App. y / Table z in the revised PDF> — <what the sentence now says>.
Evidence: <paper/results/... or table name>; <one number with its denominator>.
Still open: <one sentence, or "Nothing further is claimed.">
```

### 11.3 Content the responses must contain

**R1.**
- W1 intro: describe the rewritten first page; name the task sentence that now precedes #4420.
- W2 comparators: EvoC2F (no inspectable implementation; HTTP 401), Agent JIT (browser planner;
  cited commit in BLAST; a SQL static-checker probe was run and is retained), AWO (unreleased);
  the executed alternative is adapted offline AWM (8,172 episodes); matched-compiler protocol
  is written and frozen, unrun; no ranking claim is made.
- W3 Table 2: renamed columns and key.
- W4 loss/labels: the 92-group tables are replay-only (`_calibration_samples` compares
  substituted tool outputs after verifier success; the continuation never runs); the paper now
  says "replay certificate" everywhere for those rows; the end-to-end certificates are the
  132-group post-cutoff PR cohort (0/132, U = 0.0173) and, if B admits, the new multi-repository
  cohorts; the episode-level guarantee is claimed only where those labels exist.
- W5 population: 396 records accounted; 2/1/0 excluded inexact runs; 14/15/16 unused;
  #539, #2781, #5700 pass the saved guard and gate, so the unfiltered claim was withdrawn;
  Strategy B samples before outcomes and labels every eligible group (give n, k, U).
- W6 lifecycle: implemented (staged promotion, expiry, retirement, rollback, kill switch,
  manifest checks) versus proposed (suspend on confirmed violation or pin invalidation;
  prospective monitoring; renewal = new version + fresh disjoint calibration); SKILL.nb cited;
  no measured maintenance benefit claimed.
- Q1–Q5: literal answers (benchmark citations with versions; label path; exclusion
  accounting; triggers; manifest definition quoted from §2).

**R2.**
- W1 workloads: agree they are metadata/extraction; task specifications pointed to; the
  handwritten program is the oracle and the compiler-decisions table shows where the compiler
  recovered it and where it refused; discovery break-even 411/183/181 episodes; adapted AWM
  costs 2–4× more per episode; the adaptive comparison was attempted four times (gates with
  numbers) and is not claimed.
- W2 attribution: recurrence-only replay ties 30/30 at one request (kept); drift ×3 now
  executed (null, null, adverse with 39/60 silent wrong in both arms); live recovery isolates
  the scope guard (+8.80, [3.70, 13.89]) with completeness unresolved; the learned gate routes
  identically to support-only on 2,724 cases and is no longer claimed.
- Q1: full task specification pointer; "no decision requires semantic interpretation; the
  model's remaining role is reading the returned evidence and writing the contract fields".
- Q2: label generation and filtering answered as for R1 W4–W5, plus B.
- Q3: the attempt record (BIRD 28/28/26 of 36; AppWorld 1/12, 2/12 < 8/12; AgentHop 19/24,
  no selector; Reddit 714 one-batch reference) and the frozen protocol; state plainly that this
  experiment is not completed and that the paper's claim is scoped accordingly.

**R3.**
- W1 statistics: agree; abstract and conclusion now state the limits; 0.0569 and the 106-group
  requirement stay; day/author sensitivity stays; B supplies cohorts with author units, m = 1,
  and (if admitted) U ≤ 0.05 under the registered grid; the 132-group cohort already supports a
  selection-wide bound for one family (U = 0.0173; 0.0267 at author units).
- W2 learned gate: the 92-group cohorts cannot certify intermediate coverage (⌈92/c⌉);
  the sequential extension selected η = 0.50 on 311 groups and the sealed test gave 3/90
  learned vs 5/90 support-only vs 2/90 unchanged, but the design is adaptive and mixed-frame,
  so no certificate is claimed; the revised paper makes no learned-gate claim; (if C ran) the
  single-look replication result.
- Q1: "Yes, one: the post-cutoff PR-outcome cohort (m = 1, n = 132, 0 violations); after this
  rebuttal also <B's repositories>. The three primary 92-group cohorts do not; the abstract and
  conclusion now say so."
- Q2: "Not with certified coverage at two positive levels on any retained cohort; the pooled
  extension observes it nominally; the paper now claims no learned selectivity, and the
  prospective design that could answer it is in Appendix <prospective protocol>."

### 11.4 Manuscript change ledger

`paper/iclr/notes/rebuttal_changes_2026-11.md` (task 2.10) is the single source for every
"Changed:" line. Also update `reviewer_concern_closure.md` (status column),
`review_revision_status_2026-11-06.md` (upload hash, posting time),
`openreview_metadata.md` (abstract), `number_registry.md` (new numbers), and
`paper/reviews/ICLR_2027_Reviewer_Feedback_Final_Report_2026-11-06.md` (one dated paragraph).

---

## 12. Fallbacks and stop rules

| If | Then |
|---|---|
| Acquisition of a repository fails or exceeds two hours | Drop it; proceed with the others; note in the protocol amendment |
| A repository's discovery retires | Record the refusal; it is a row in the compiler-decisions table |
| Calibration violations exceed the floor | Report the retirement and the observed rate; keep the paired comparison; do not change the rule, the grid, or n |
| Adapter errors in the pilot | Fix, re-run the pilot, retain the failed pilot; if unfixed by Day 2 noon, ship minimal viable B |
| Day 3 milestone missed | Skip WP5; ship minimal viable B; writing stream unaffected |
| Page 10 overflows | Move the compiler-decisions table to the appendix with a one-sentence main-text summary; never cut the certificate paragraph |
| A number in the response disagrees with the PDF | The PDF wins; fix the response; re-run 3.3 |
| Reviewer asks for something new during discussion | Answer from retained evidence only; offer the protocol; do not run unregistered experiments in the window |

---

## Appendix A. Reference material for the agent

### A.1 Version-gap grep

```
pdftotext paper/reviews/openreview_submitted.pdf /tmp/sub.txt
pdftotext paper/iclr/build/main.pdf /tmp/cur.txt
for k in "Workflow Memory" "8,172" "post-cutoff" "0.0173" "live recovery" "scope guard" \
         "drift" "sequential extension" "311" "SKILL" "TraceCompiler" "census" \
         "population audit" "Adaptive-Task Development" "AgentHop" "0.0569" "recurrence-only"; do
  printf "%-32s submitted=%-4s current=%s\n" "$k" "$(grep -c -i -- "$k" /tmp/sub.txt)" "$(grep -c -i -- "$k" /tmp/cur.txt)"
done
grep -n "^Table 19\|^Table 23\|^Table 9:\|^Table 20\|^Table 2:" /tmp/sub.txt
```

Expected: the submitted PDF has zero hits for 8,172 / 0.0173 / live recovery / scope guard /
311 / census / population audit / AgentHop and its Table 19 is the recurrence-only table.

### A.2 Key files

| Purpose | Path |
|---|---|
| Paper source | `paper/iclr/main.tex`, `paper/iclr/sections/*.tex`, `paper/iclr/appendix.tex`, `paper/iclr/tables/*.tex` |
| Build | `cd paper/iclr && tectonic --outdir build main.tex` |
| Validators | `paper/scripts/validate_artifacts.py` (`--list-families`), `paper/scripts/finalize_manifest.py` |
| Reviews | `paper/reviews/ICLR-{1,2,3}.txt` |
| Existing response draft and ledgers | `paper/iclr/notes/review_response_2026-11-06.md`, `reviewer_concern_closure.md`, `review_revision_status_2026-11-06.md`, `number_registry.md`, `openreview_metadata.md` |
| Time-forward pipeline (reuse) | `paper/scripts/time_forward_pr_outcome_study.py`, `github_time_forward_acquire.py`, `github_time_forward_preflight.py`; results `paper/results/time_forward/pr_outcome/` |
| Family definitions, prompts, graders | `paper/scripts/github_workflow_family_study.py` (`FAMILIES["pr_outcome"]`), `github_live_study.py` |
| Hand-written programs | `src/guarded_agentic_compaction/runtime/manual.py` |
| Calibration helper (label path) | `src/guarded_agentic_compaction/grc/compile.py::_calibration_samples`, `grc/calibrate.py` |
| Graded issue gate (Strategy C) | `paper/scripts/graded_issue_gate_study.py`, `graded_issue_recompile_candidate.py`, `audit_graded_issue_gate_extension.py`; `paper/results/graded_issue_gate/` |
| Comparator audits | `experiments/matched_reuse_baseline/COMPATIBILITY.md`, `paper/results/adaptive_comparison_preflight/REPORT.md`, `paper/supplementary/matched-compiler-candidate-protocol.md` |
| Adaptive gates | `paper/iclr/sections/adaptive_gates_appendix.tex`; `paper/results/{bird_one_call_matched_pilot,appworld_batched_competence,agenthop_baseline_trace_pilot,agenthop_section_lookahead}/REPORT.md` |
| Budget | `paper/reviews/ICLR_2027_Reviewer_Feedback_Final_Report_2026-11-06.md` ($12.10 of $300 used) |

### A.3 Pre-computed admission floors (exact one-sided Clopper–Pearson)

Registered grid, m = 1 (level 0.1/11): max violations admitting at α = 0.05 —
n = 92: 0 (U = 0.0498); 106: 0 (0.0434); 132: 0 (0.0350); 150: 1; 200: 3 (U(0) = 0.0232);
300: 6; 400: 9; 800: 25 (U(0) = 0.0059).
Registered grid, m = 2 (level 0.1/22): n = 92: none (0.0569); 106: 0 (0.0496); 200: 2; 300: 5.
Single rule γ = 0.10: n = 132: 3 (U(3) = 0.0499); 200: 5 (0.0459); 400: 14; 800: 31.
Zero-violation floors for intermediate coverage (registered grid): 92 groups accepted at the
level; one violation 133; two 168; three 200; four 231.
One-sided 95% bound on compiled-only misses with zero observed: 0.0149 (n = 200),
0.0075 (400), 0.0037 (800).

### A.4 Numbers the responses may cite (all retained; see `number_registry.md`)

Primary 90/90 vs 89/90; −66.6% requests, −63.1% tokens, −64.2% latency, −58.7% cost;
hand-written 90/90 ties on requests. Recurrence-only 30/30 at one request vs two.
92 groups, U = 0.0498; m = 2 → 0.0569; 106 needed. Days 86–90 and authors 60–82 per cohort
retire every family. Post-cutoff PR: 1,095 records, 811 fresh PRs, 60/132/132, 131/132 exact
discovery, 132/0, U = 0.0173 (0.035 grid), 60/60 all arms, retained artifact abstains 60/60,
−75.0/−82.7/−80.0/−76.6%, $0.2154. Graded gate: 184/2 retire; 311/4 → η = 0.50, 261/311,
nominal 0.0443; η = 0.02: 117/0, 0.0394; Fisher p = 0.150; test 2/90, 3/90 (2/76 after
dispatch), 5/90; requests 360/132/90. Live recovery: 2,304 episodes; 186/216 → 205/216,
+8.80 [3.70, 13.89]; completeness 204 vs 205. Fresh safeguards: 120 issues; 120/120 ×3,
118/120 recurrence-only; −45.8% cost. AWM: 1,362 records, 8,172 episodes; 5/6 cells; cost
−36.9 to −79.1%; requests −50 to −75%; gpt-6 backlog 142/144 vs 143/144 (bound 5.86%);
identical routing on 2,724 cases. Drift: 144 groups null; 89 records null; 1,080 cells,
39/60 silent wrong both arms. Population audit: 396; 2/1/0 excluded; 14/15/16 unused;
#539, #2781, #5700 pass guard/gate. BIRD: 26/31 databases; 97 vs 94 of 150; 93 vs 91;
402 vs 403 of 630; −44.9% requests; dev gate 28/28/26 of 36, requests 151/111/112.
AppWorld dev 1/12, 2/12 vs 8/12. AgentHop 19/24 vs 17/24; 42 opportunities; 11/35.
Census 157,280; 4–41%; 2–13%. Break-even 411/183/181 episodes. 810 compiled episodes:
1/270 excerpt (bound 1.7%), 0/540 outcome-only. Cross-repo 120/120 (four repos), pytorch
retires; balanced 180/180; frontier 240/240/239.

### A.5 Protocol skeleton for Strategy B (copy into the protocol file; fill blanks before commit)

```
# Unfiltered, author-unit, time-forward end-to-end calibration of PR-outcome across repositories
Status: PRE-REGISTERED <date> at commit <hash>; no provider call before this commit.
Family: pr_outcome (three reads); arms: compiled (frozen artifact), unchanged agent, hand-written.
Repositories and cutoffs: huggingface/datasets (existing post-cutoff snapshot, frozen registry
  paper/results/time_forward/pr_outcome/registry, no new discovery); pandas-dev/pandas 2026-01-01;
  streamlit/streamlit 2026-01-01; psf/requests 2026-01-01; pytorch/pytorch 2026-08-01.
Exclusions: repository-qualified record numbers used by any retained study of that repository.
Unit: one PR per distinct user.login; stable SHA-256 rank with tag "<repo-tag>"; distinct days reported.
Splits (new repos): discovery 132 (round-robin classes; shortfalls filled in rank order and recorded);
  calibration 200 author-distinct PRs disjoint in records and authors from discovery. No test split.
Candidate: one per repository, frozen before calibration (m = 1); compile exactly as the time-forward study.
Labels: for every calibration group — eligible? dispatched? verifier abstained? contract met (each arm)?
  Violation = compiled arm dispatched and final contract missed. Clean abstention: in n, L = 0.
Decision rule (primary): registered grid, α = 0.05, δ = 0.10, |Λ| = 11, m = 1: admit iff k ≤ 3 at n = 200
  (exact floors recomputed for the realized n; shortfalls below 200 are reported, never topped up).
Secondary: single rule γ = δ = 0.10 (admit iff k ≤ 5 at n = 200); pooled n = 800 (admit iff k ≤ 25).
Paired: exact McNemar baseline vs compiled; one-sided 95% bound on compiled-only misses; resources.
Spend: $5 per repository, $25 total; pilot 10 groups on huggingface/datasets first; no retries.
Claim boundary: per-candidate = compiler-wide (m = 1), end-to-end, unfiltered, author units, one family,
  fresh records of the named repositories; not adaptive-task value; not learned-gate value.
Adverse reporting: violating records and retirements are reported before any reduction.
```
