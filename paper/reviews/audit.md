# Paper audit: claims against evidence (2026-11-08)

Scope: every quantitative claim in the main text of the revised paper (`paper/iclr/sections/*.tex` and
the tables and figures they input), checked against the retained raw results. Part A covers the
abstract, introduction, problem, method, evaluation, related work, discussion and conclusion. Part B
covers the results section and its tables. Both parts were re-derived from per-record or per-group
JSON, not from summary files. The re-derivation scripts are in `paper/reviews/audit_scripts/` and run
from the repository root (`python paper/reviews/audit_scripts/<name>.py`).
`python paper/scripts/validate_artifacts.py` passes 7,725 checks with 0 failures; many rows cite one of
those checks.

## Second pass (2026-11-08, independent re-check)

A second pass re-read the full paper source and re-checked every reply against the reviewer text
and the revised PDF's numbering (label numbers read from the `.aux` of a fresh `tectonic` build).
The first pass was treated as untrusted: numbers were recomputed from the raw files, and every
section, table, figure, equation and appendix pointer in the replies was opened.

### A. Paper

- Independent numeric re-derivation: see part C below (run by a separate agent that did not read
  this file or the replies).
- Consistency of abstract, introduction, results and conclusion. Two sentences in the introduction
  lagged the first-pass edits and were fixed (`paper-changes.md`, edits 13 and 14): contribution 1
  still said "enough independent calibration examples" after the abstract had been changed to
  "assumed independent"; contribution 2 said "no detected accuracy loss", which holds against the
  first-run BIRD baselines but not against the warm reruns reported in §5.2 (93 vs 95; 402 vs 412),
  and now says "at similar accuracy". Everything else agrees: the abstract, §5.4, Table 6, Table 28
  and the conclusion all say that two primary families miss the selection-adjusted target, that the
  primary bounds are replay bounds on a filtered population, and that end-to-end bounds exist for
  PR-outcome only.
- Items 5, 6, 16, 17 and 19 of the first-pass disposition table stay as they were.

### B. Replies

Every number in the four replies was matched to the paper text or table it cites, every pointer was
opened, and every "we added/changed X" statement was located in the revised source. Corrections
made in this pass:

| # | Reply | Problem found | Fix |
|---|---|---|---|
| 1 | general (point 3), R3 (point 1) | "The three primary families have no selection-wide 5% bound" was wrong: issue-type routing calibrated one candidate (m = 1), so its replay bound is compiler-wide (Table 6; Table 28). Only PR-outcome and backlog (m = 2, 0.0569) miss it; day or author units retire all three. | Rewritten to say two of three families, and that author/day units retire all three. `review-map.md` R3-W1 fixed the same way. |
| 2 | general, R2, R3 | "Table 38" was cited for the 2,724 record-model cases on which the three routings agree. Table 38 is the gate-frontier disaggregation (240 episodes). The 2,724-case result is in §5.4 (results.tex), App. F.7 and App. K (`generalization_gate_appendix.tex`). | Pointer changed to "§5.4; Appendix K". `review-map.md` R2-W2b fixed. |
| 3 | R1 (point 1) | "Table 6 and Table 28 name each certificate's event": Table 6 (multiplicity accounting) has no event column. | Now "Table 28 names the event behind every certificate". |
| 4 | R1 (benchmark references) | "§4 cites each one" included AgentHop, which §4 does not cite; it is cited in §7 and App. L. | Now "§4 cites each benchmark it uses; AgentHop ... development gates only (Appendix L)". |
| 5 | R1 (structure) | Reviewer 1's weaknesses are five unnumbered paragraphs; the first-pass reply split the second into W2 and W3 and numbered to W6, so its labels did not match the review. | Points renumbered in the reviewer's order (Weakness 1-5, Question 1-5) and the reply says so. |
| 6 | R2 (structure) | Reviewer 2 labels the questions "Clarification - task requirements", "Clarification - calibration evidence" and "Suggested additional validation", not Q1-Q3. | Headings use the reviewer's labels. |
| 7 | R3 (feasibility) | "The pool holds 197 issues with a comment" had no retained source on `main`; the number comes from the no-go record of the single-look replication on branch `agent/c1-gate` (commits 0ce6c5f, 8e1970a: snapshot 277 issues, 197 with at least one comment, 117 after 80 re-derivation records), also quoted in `flip-plans.md`. | Reply now says "277 issues, 197 with at least one comment" and gives the arithmetic that matters (117 < 2 x 92). Flagged for the author: merge the c1-gate record to `main` or drop the figure. |
| 8 | all three | Closing sentences asked the reviewer to revisit the score. | Removed; each reply now ends with an offer to answer further questions. |
| 9 | all four | "Paraphrase: ..." blocks before each answer. | Replaced by a one-line heading quoting the reviewer's point, then the answer sentence, then evidence and pointer. |
| 10 | R1 (post-cutoff) | Pointer for the post-cutoff study was the raw file only. | Added "Section 5.4; Appendix G" (the study is reported in `app:limits`, which is Appendix G). |

Facts in the replies that are not in the paper, with their sources: EvoC2F's anonymous code
endpoint returning HTTP 401 (`flip-plans.md`); the 6-10 and 12-16 working-day estimates (author
estimates in `paper/iclr/notes/review_response_2026-11-06.md`, stated as estimates);
the task field names `open`/`merged`/`closed_unmerged` and `owned`/`discussed_unowned`/
`awaiting_first_response` (Table 16 and the per-record results files); the single-look no-go
(item 7). The supplementary files named in the replies exist:
`paper/supplementary/matched-compiler-candidate-protocol.md` and
`paper/supplementary/adaptive-quality-cost-study.md`.

Pointer map used (label, number, page in the 63-page build): Table 1 compiler decisions (p. 7);
Table 2 primary (p. 7); Table 3 AWM (p. 8); Table 4 funnel (p. 9); Table 5 live manifest (p. 22);
Table 6 multiplicity (p. 23); Table 14 manual resources (p. 28); Table 16 benchmark glance (p. 29);
Table 19 multirepo end-to-end (p. 32); Table 20 funnel-all (p. 33); Table 28 certificates (p. 40);
Table 31 effective units (p. 42); Table 33 recurrence-only (p. 45); Table 37 gate extension (p. 50);
Table 46 compiler comparison (p. 62); Figure 3 gate floor (p. 24); Eq. (3) dispatch; App. C
Configuration (labels paragraph p. 22); App. D Paired statistics (lifecycle paragraph); App. E
Additional detail ("Primary workflow families"); App. F.2 multirepo e2e (p. 31); App. F.4 external
map (p. 32); App. G Extended limitations (population audit p. 48; post-cutoff study); App. H
prospective protocol (p. 48); App. H.1 gate extension (p. 49); App. I live recovery (p. 51); App. K
generalization gate (p. 55); App. L adaptive gates (p. 58); App. N additional optimization context
(p. 62). All as cited in the replies.

Bounds recomputed with `scipy.stats.beta.ppf` (grid level 1 - 0.1/11; single rule 0.90):
U(1,200) = 0.0333, U(2,200) = 0.0419, U(0,160) = 0.0290, U(0,200) = 0.0232, U(3,760) = 0.0133,
U(14,400) = 0.0632, U(17,400) = 0.0726, U(50,3560) = 0.0194, U(3,560) = 0.0181, U(0,132) = 0.035
(grid) and 0.0173 (single rule), U(0,85) = 0.0267 and U(0,100) = 0.0228 (single rule), U(0,92) =
0.0498 and 0.0569 at m = 2, U(1,270,0.95) = 0.0175; the largest k admitted at n = 400 under the grid
is 9. All match the replies and the paper.

### C. Independent numeric re-derivation

A separate agent, given only the paper source, the tables, `claims_evidence_index.tex` and
`paper/results/`, recomputed every headline number from per-record arrays (not summary fields)
where they exist. Scratch scripts: `scratchpad/indep/claim1.py`, `claim4.py`, `claim6.py` (session
scratchpad, not retained). **No numeric mismatch.** Verified from raw records: 90/90, 90/90, 89/90
and the five pooled reductions (66.57 / 44.24 / 63.06 / 64.21 / 58.67) and every Table 2 and Table 14
cell; n = 92, k = 0 in all three artifacts, U = 0.04981, 0.05691 at m = 2, 106 groups (n = 105 gives
0.05007); why issue-type has m = 1 (cand-00 rejected at synthesis for the ungroundable
`comments.limit` slot) and PR-outcome and backlog have m = 2 (both candidates calibrated, then one
dominated); post-cutoff 132/0 from `certificate.per_record`, 84 open / 48 merged, 0.01729 and 0.0350;
multi-repository 1/200, 2/200, 0/200, 0/160, pooled 3/760 = 0.01332; node 14/400, cpython 17/400,
next.js 1, django 2, kubernetes 3, vscode 3, godot 7, max admissible k = 9 at n = 400 and 3 at n = 200;
3,510 / 3,507 / 3,504 of 3,560 recounted from `calibration_checkpoint.json` with 73.6% cost reduction
for both compiled and hand-written arms; godot 393 / 399 / 395 with b-only 7, c-only 1, p = 0.0703;
AWM 8,172 rows, 1,362 records, 1,344 primary, every Table 3 count and loss bound (3.27, 5.86, 3.61,
4.04, 1.43, 1.43) and cost saving; 2,724 = 1,362 x 2 record-model cases; BIRD 26/31, 94 / 94 / 97 / 94
of 150 with requests -44.9% and latency -29.4% against the warm rerun and McNemar p = 0.453; second
model 93 / 91 / 95, train 402 / 403 / 412 / 404, requests -49.6% and -45.8% on paired first runs,
interval [-3.27, +2.96]; one-call gate 28 / 28 / 26 of 36 with 151 / 111 / 112 requests; live recovery
2,304 rows, 186 -> 205 with +8.796 and bootstrap [3.70, 13.89]; recurrence-only 30/30 at 1 request;
drift 144 / 89 paired with zero wrong, continuation 39/39; break-even 410.87, 182.01, 180.60 -> 411,
183, 181; manual cost -60.43%; 396 records with dispositions 16/8/92 and 14/15/16 unused, 2/1/0
excluded, #539, #2781, #5700 passing the guard; 810 = 270 + 540 episodes, 354 distinct records,
U(1,270) = 0.0174; prefix census 3.9-41.0%; gpt-6-luna transfer miss (issue 6532); Sonnet backlog 90
and 91 of 92; AppWorld 37.88% of 8,190 and +2 of 4,680.

Not independently re-derivable (summary fields or narrative only): the 47 / 3 / 0 post-hoc split of
the 50 multi-repository violations (`violation_failed_checks_post_hoc` in `summary.json`, no
per-violation list); the three-routing identity on the 2,724 cases (`gate_equivalent: true` per cell);
the "40 under the corrected grader" (narrative; `results.json` says 39, first-pass item 19).

Presentational findings from that pass and their disposition:

| # | Finding | Disposition |
|---|---|---|
| C1 | **Cohort mixing in §5.4 (results.tex live-recovery sentence).** 186 -> 205 is the ordinary-response cohort, but "204/216 versus 205/216" and "22/27" come from the capped-response cohort; under ordinary responses the no-completeness arm scores 210/216, better than full (Tables 39-40). The sentence read as one cohort and understated the result against the completeness check. | **Fixed** (`paper-changes.md`, edit 15): the sentence now gives both cohorts. The R2 reply carries the same two numbers. |
| C2 | Two request-reduction figures for the same BIRD runs: §5.2 and App. F.6 text give 49.6% and 45.8% (all paired first-run pairs, 150 / 629); Table 25 gives 49.9% and 45.9% (complete cases, 149 / 625). Both correct under their denominators. | Left; the table's denominator convention is stated in its caption. Recorded here. |
| C3 | 1,344 (abstract, Table 3 caption) against 1,362 (results text, "8,172 episodes on 1,362 fresh records"). | Known (first-pass item 18); both correct; left. |


## Summary

| Part | Claims | VERIFIED | WORDING (number right, sentence overstates or is unclear) | MISMATCH | UNSUPPORTED |
|---|---:|---:|---:|---:|---:|
| A (abstract to conclusion) | 64 | 54 | 9 (in 4 of them the number itself is verified) | 1 | 0 |
| B (results and tables) | 52 | 44 | 8 rows (listed as 9 findings below) | 0 | 0 |

**No headline number is wrong.** The six required re-derivations all reproduce:
- 90/90 compiled, 89/90 unchanged and 90/90 hand-written.
- Pooled reductions of 66.6 / 63.1 / 64.2 / 58.7% (requests, tokens, latency, cost).
- U(0,92) = 0.0498 per candidate and 0.0569 for two candidates; 106 groups are needed.
- Post-cutoff 0/132: U = 0.0173 (90% single rule) and 0.0350 (registered grid).
- Multi-repository: 760/3/0.0133 and 3,560/50/0.0194; 3,510/3,507/3,504; 73.6%.
- Five-frozen-repository study: 4 admit, pytorch retires.
- NESTFUL, API-Bank, BFCL v4 and AppWorld cells.
- AWM: 8,172 episodes, 5 of 6 cells.
- gpt-6-luna transfer: 1 compiled-only miss.
- BIRD: 26/31; 97 vs 94.

## Statistical correctness (Step 1.3)

- **Assumption.** Every bound is an exact one-sided Clopper–Pearson bound and assumes i.i.d.
  (exchangeable) calibration groups. The paper states this for the primary bound (results.tex,
  "conditional on i.i.d. groups from the selected population"), in Proposition 1 and in §7.
  Independence is assumed, not shown: counting a creation day or an author as the unit retires every
  primary family (Table 31). The abstract called the examples "independent"; it now says "assumed
  independent".
- **Confidence and multiplicity.**
  - Registered grid: level 1 − 0.1/11 (Bonferroni over the 11 thresholds) with α = 0.05 and δ = 0.10.
  - Single pre-registered rule: 90%.
  - Candidate selection (m candidates) is a separate correction: 0.0569 at m = 2, which misses 0.05.
  - The evaluation section said "gate multiplicity" for the threshold correction; it now says
    "threshold-grid multiplicity", so the text no longer implies that candidate selection is covered.
- **What a bound over n groups guarantees.**
  - Each bound is for one fixed candidate (or a fixed m) on the population the groups were drawn
    from.
  - The 92-group primary bounds cover replay agreement on an outcome-filtered population, not final
    answers and not unfiltered deployment.
  - Final-answer bounds exist only for PR-outcome: the post-cutoff and multi-repository studies.
  - The paper says this in the abstract, §2, §5.4 and the conclusion. No sentence presents a bound
    as a safety guarantee.
- **Mixed rules in the abstract.** 0.0173 uses the single 90% rule; 0.023–0.042 use the registered
  grid. Both are correct as stated in the body (§5.4, App. F.2). The abstract labels the first as a 90%
  bound and the second as bounds; this was left as is (see the disposition table).

## Disposition of every non-VERIFIED item

| # | Item (part, location) | Disposition |
|---|---|---|
| 1 | MISMATCH (A, problem.tex:100): "every certificate except one end-to-end certificate" is a replay certificate; there are two end-to-end studies and per-repository certificates | **Fixed**: "except the PR-outcome end-to-end certificates" |
| 2 | WORDING (A, abstract): "one covers final answers", followed by a second final-answer study | **Fixed**: "pull-request bounds cover final answers" |
| 3 | WORDING and rounding (A, conclusion): "about 73% lower model cost" on "GitHub workflows"; the primary families pool to 58.7%, and 73.6% is the end-to-end PR pool | **Fixed**: "matches hand-written programs while cutting model cost 58.7–73.6%" |
| 4 | WORDING (A, abstract): "enough independent calibration examples" | **Fixed**: "enough calibration examples, assumed independent" |
| 5 | WORDING (A, abstract, minor): mixed bound rules | Left: each number is labelled correctly in the body; abstract length |
| 6 | WORDING (A, introduction and Fig. 2 caption, minor): "132 discovery runs (the traces the compiler learns from)"; the compiler's supporting traces are 116 | Left: the conclusion of the example (limit varies, so no witness) holds on the 116 and the 16 training traces; page budget |
| 7 | WORDING (A, abstract, minor): "1,362 fresh records" includes 18 pilot records; the six cells use 1,344 | **Fixed**: abstract says 1,344 (results text keeps "8,172 episodes on 1,362 fresh records", which is the full count) |
| 8 | WORDING (A, discussion, minor): "one-sided bound 1.7%" lacks level and assumption | **Fixed**: "one-sided 95% bound 1.7%, i.i.d. episodes" (recomputed: U(1,270,0.95) = 0.01745) |
| 9 | WORDING (A, discussion, minor): "compiled-only misses are excerpts" (plural); there is one (issue 2737) | **Fixed**: "compiled-only miss is an excerpt" |
| 10 | WORDING (A, evaluation, minor): "gate multiplicity" | **Fixed**: "threshold-grid multiplicity" |
| 11 | WORDING, moderate (B, results BIRD): second-model and training accuracy compared with the first-run baseline; warm reruns scored 95/150 and 412/630, so compiled (93, 402) trails them | **Fixed**: "(warm reruns 95 and 412; requests fall 49.6% and 45.8% vs. first runs)" |
| 12 | WORDING, moderate (B, results BIRD): the comparator for 49.6% and 45.8% was not named | **Fixed** with item 11 |
| 13 | WORDING, moderate (B, results opening): "recovers the program a person would write wherever the retained traces support one"; the recurrence-only ablation shows a supported three-read program that the compiler refused | **Fixed**: "where it admits, it recovers the program a person would write, and where it refuses, it states the stage and reason" |
| 14 | WORDING (B, decisions-table caption): "bound 0.0498 ≤ 0.05" without the per-candidate qualifier | **Fixed**: "per-candidate bound 0.0498" |
| 15 | WORDING (B, results end-to-end): "Two end-to-end certificates exist" undercounts; 0.0173 has no level | **Fixed**: "Two end-to-end studies exist"; "a 90% bound of 0.0173" |
| 16 | WORDING (B, results, low): "NESTFUL, the largest trace corpus the compiler ingests here"; true per substrate, but BIRD supplies 4,047 traces over 31 corpora | Left: true per substrate; page budget |
| 17 | Clarity (B, decisions table, AppWorld): retired bounds "1.000, 1.000" copy the compiler's no-group-accepted message, not a Clopper–Pearson value | Left: faithful to the artifact; flagged for the author |
| 18 | Consistency (B): AWM caption 1,344 against text 1,362 | Resolved: both are correct (18 pilot records); the abstract now uses 1,344 |
| 19 | Provenance (B, results drift): "40 under the corrected grader" rests on a protocol note (`paper/supplementary/drift-continuation-graded-protocol.md`), while `results.json` records 39 | Left in the paper with its existing citation; **not used** in the replies |

No change alters a headline result. Two changes touch a headline sentence; both make it more
accurate, not more favourable. The conclusion's cost figure changes from "about 73%" to "58.7–73.6%",
and the abstract's AWM record count changes from 1,362 to 1,344, the records the six cells actually use.
See `paper-changes.md`.

# Part A


Repository: `.claude/worktrees/integration` (branch `paper/rebuttal-audit-and-answers`). All paths below are relative to `paper/`.
Validator: `python paper/scripts/validate_artifacts.py` gives 7725 passed / 0 failed (output in `paper/reviews/audit_scripts/validator.txt`).
The compiled PDF (`iclr/build/main.pdf`, built Nov 7 21:54) was checked against the .tex: the abstract, intro, method, discussion and conclusion numbers appear identically.
Re-derivation scripts are in `paper/reviews/audit_scripts/`: `mre2e.py` (multirepo end-to-end from raw groups), `e810.py` (810-episode pool), `bounds.py` (Clopper-Pearson closed forms).

| # | Claim (short quote) | Location (file:line) | Source (file + field/check) | Status | Note |
|---|---|---|---|---|---|
| 1 | "admits one only when enough independent calibration examples support a finite-sample error bound" | iclr/sections/abstract.tex:8-9 | Prop. 1 (method.tex:141-151); `results/iclr_revision/effective_units.json` | WORDING | Independence is assumed (i.i.d. groups), not shown. Counting days or authors as the unit retires every primary family (discussion.tex:12-15). Most bounds are on replay violation, not task error. The abstract states neither caveat at this point |
| 2 | "On three GitHub workflows" | abstract.tex:10-11 | `results/github_workflow_families/summary.json` `families` (3) | VERIFIED | |
| 3 | compiled "90/90 held-out task contracts" | abstract.tex:11 | summary.json `overall.compiled_exact`=90; raw recount over the three results.json files (30+30+30); validator "iclr: results.tex states the retained 90/90 and 89/90 counts" | VERIFIED | |
| 4 | "as hand-written programs do" (90/90) | abstract.tex:11-12 | summary.json `overall.manual_exact`=90; raw: `macro` 30, `manual_pre_model` 30+30 | VERIFIED | |
| 5 | "89/90 for the unchanged agent" | abstract.tex:12 | summary.json `overall.baseline_exact`=89 (backlog 29/30) | VERIFIED | |
| 6 | "66.6% fewer model requests" | abstract.tex:12-13 | summary.json `overall.requests` 359 to 120, reduction 0.66574; raw request sums give the same; validator "results.tex quotes the retained requests reduction 66.6%" | VERIFIED | |
| 7 | "adapted offline Agent Workflow Memory on 1,362 fresh records" | abstract.tex:13-14 | `experiments/generalization_gate/seal.json` `cohorts`: primary 144+600+600=1,344, plus pilot 6+6+6=18, total 1,362; `analysis.json` attempted 8,172 = 6x1,362 | VERIFIED / WORDING | The count is right, but 18 of the 1,362 are pilot records. The six cells whose margins are claimed use 1,344 records |
| 8 | "five of six workflow and model cells meet a five-point accuracy noninferiority margin" | abstract.tex:14-15 | `analysis.json` `cells.*.noninferior_5pp` (backlog/gpt-6-luna false, bound 0.0586); `manuscript_numbers.json` `noninferior_5pp_cells`=5 | VERIFIED | |
| 9 | "at 36.9--79.1% lower estimated cost" | abstract.tex:16 | `manuscript_numbers.json` `cost_reduction_range_percent` [36.87, 79.06]; recomputed from `cells.*.arms.*.metrics_total.estimated_cost_usd` (GAC vs AWM, induction excluded) | VERIFIED | Includes induction cost: 37.2-79.2% |
| 10 | BIRD "schema-first opening compiles on 26/31 databases" | abstract.tex:17 | `results/bird/summary.json` schema_first 5/5 admitted; `results/bird/train/summary.json` 21/26 admitted; validator "decisions: BIRD schema-first: admits 26 of 31 databases" | VERIFIED | gpt-5.6-luna |
| 11 | "three tool-trace benchmarks are refused for insufficient calibration support" | abstract.tex:17-18 | `results/nestful/results.json`, `external_benchmarks/{api_bank,bfcl_compiler}_execution.json` `exact_gate`; validator "decisions: trace benchmarks: NESTFUL, API-Bank, BFCL retire at n_max 26, 8, 15 < 92" | VERIFIED | |
| 12 | "AppWorld's program is rarely eligible" | abstract.tex:18 | validator "decisions: AppWorld: dispatchable on 1 of 4,680 ReAct and plan-and-execute trajectories" | VERIFIED | |
| 13 | "Most bounds cover replay on selected populations; one covers final answers" | abstract.tex:18-19 | results.tex:152 ("Two end-to-end certificates exist"); `multirepo_end_to_end/summary.json` | WORDING | The next sentence describes a second final-answer study: 760 groups, 4 admitted per-repository certificates, plus 5 more at n=400. "One" is stale. Suggest "two studies cover final answers" |
| 14 | "no failure on 132 pull requests opened after the snapshot (90% upper bound 0.0173)" | abstract.tex:19-21 | `results/time_forward/pr_outcome/certificate.json` attempted 132, violations 0, `upper_90`=0.017293; `compile.json` `snapshot.created_after_utc_day`=2025-06-13; validator "time-forward: end-to-end certificate 132/0, U = 0.0173, admits" | VERIFIED | Recomputed 1-0.1^(1/132)=0.017293. This is the single-rule 90% bound. On the registered grid it is 0.035 (results.tex:154), and the abstract's other bounds (row 16) are grid bounds. Cohort is 84 open / 48 merged / 0 closed-unmerged |
| 15 | "3 misses in 760 groups across four repositories" | abstract.tex:22-24 | summary.json `pooled_run_repositories.certificate` n=760, k=3; recomputed from raw `*/calibration_groups.json` (hf 1/200, pandas 2/200, pytorch 0/200, streamlit 0/160) | VERIFIED | |
| 16 | "each admitted (bounds 0.023--0.042)" | abstract.tex:24 | summary.json `repositories[].certificate.grid_m1.U`: 0.0232, 0.0290, 0.0333, 0.0419, all `decision`=admit; recomputed with conf 1-0.1/11 | VERIFIED | |
| 17 | "Of seven repositories added at 400 groups, five are admitted and two retired" | abstract.tex:24-25 | summary.json `stage`=amendment_3, n=400 for next.js, django, kubernetes, vscode, godot (admit) and node (U 0.0632), cpython (U 0.0726) (retire); recomputed from raw | VERIFIED | |
| 18 | "over all eleven ... meet 3,510, 3,507 and 3,504 of 3,560 contracts" | abstract.tex:25-26 | summary.json `pooled_all_run_repositories.paired` compiled_met 3510, baseline_met 3507, n 3560; manual 3504 recomputed from raw `arms.manual.contract_met` (not in summary.json) | VERIFIED | |
| 19 | "two primary families miss the selection-adjusted 5% target" | abstract.tex:27-28 | `results/iclr_revision/multiplicity_accounting.json`: pr_outcome and backlog_attention m=2, `u_candidate_wide`=0.05694 > 0.05; issue_type m=1, 0.0498 | VERIFIED | |
| 20 | "read-only openings of two or more calls start 4--41% of released trajectories per corpus" | iclr/sections/introduction.tex:5-6 | `results/prefix_census/results.json` primary arms `read_only_opening.share_ge2`: tau-bench 3.94%, OpenHands 16.3%, SWE-agent 32.5%, AppWorld 41.0% | VERIFIED | NESTFUL (100%, gold sequences, not released trajectories) and the labelled sensitivity arms (up to 51.7%) are correctly excluded |
| 21 | "GitHub issue triage, one of three workflow families" | introduction.tex:17 | summary.json `families` | VERIFIED | |
| 22 | "held-out issue #4420 ... record(4420) ... limit to 100" | introduction.tex:20-22 | `results/github_natural_replication/results.json` `results[]` issue 4420 (baseline and compiled): args `{issue_number:4420}` x2, `{issue_number:4420, limit:100}` | VERIFIED | |
| 23 | "All 132 discovery runs (the traces the compiler learns from) take this three-read route, 130 with limit=100 and two with limit=1" | introduction.tex:22-24 | `github_natural_replication/discovery_checkpoint.json`: 132/132 record, labels, comments; limit 100: 130, limit 1: 2 (issues 2103 [train], 6973 [calibration]) | VERIFIED / WORDING | The counts are right. But the compiler learns from 116 of the 132 (16/8/92 split; `compile_report.txt` "supp=116", 114x100 and 2x1). The witness is decided on the 16 training traces (15x100, 1x1). Two runs were excluded by the exact-trace filter |
| 24 | "recurrence-only replay of all three reads matches GAC's 30/30 held-out answers with one fewer request" | introduction.tex:29-31 | `results/recurrence_only_ablation/results.json` `per_field_exact.factuality_exact`=30, every row requests=1; GAC issue-type compiled 60 requests/30 = 2; validator "recurrence-only: every completed episode used exactly one provider request" | VERIFIED | |
| 25 | "An earlier admitted three-read program passed replay yet dropped a URL from issue #6602's final answer" | introduction.tex:31-32 | `results/github_natural_live/results.json` 6602 compiled excerpt lacks the `(https://huggingface.co/...)` link that baseline and macro have; dispatch removed_requests 3; `continuation_replay.json` 6602 original_pass false (comment_evidence mismatch) | VERIFIED | |
| 26 | "re-discovery on two further models" | introduction.tex:55 | validator "decisions: gpt6_luna ..." and "decisions: claude_sonnet5 ..." | VERIFIED | |
| 27 | "NESTFUL, API-Bank and BFCL v4 lack calibration support, AppWorld's admitted program is almost never eligible on ReAct or plan-and-execute trajectories" | introduction.tex:57-59 | same as rows 11-12; `external_benchmarks/appworld_dispatch_prologue_preflight.json` (2/2,340, 1/2,340) | VERIFIED | |
| 28 | "Every certificate in sec:results except one end-to-end certificate instantiates L(A,x)=1 as a replay-contract violation" | iclr/sections/problem.tex:100-103 | results.tex:152 ("Two end-to-end certificates exist"); `multirepo_end_to_end/summary.json` (9 admitted per-repository final-contract certificates plus pooled ones) | MISMATCH | At least two end-to-end certificates are in sec:results: time-forward 132/0 and the multirepo study. The multirepo study alone has 9 admitted per-repository certificates (4 registered + 5 Amendment 3) and pooled 760/3 and 3560/50 bounds. "Except one" should be "except the end-to-end certificates of the two final-answer studies". This is stale text from before the multirepo results were added |
| 29 | "Fig. pipeline gives the six stages" | iclr/sections/method.tex:16 | `iclr/figures/pipeline_overview.tex` stages 1-6 | VERIFIED | |
| 30 | caption: "the limit literal varies across the supporting traces (100 in 130 of 132, 1 in two)" | method.tex:26-27 (Fig. provenance) | `discovery_checkpoint.json` (130/2 over all 132 runs); `compile_report.txt` supp=116 | WORDING | 130/132 counts all discovery runs, not the "supporting traces": 116 supporting (114/2) or 16 training (15/1). The conclusion (no witness) is unaffected |
| 31 | "\code{limit}=100" (figure chip) | iclr/figures/provenance_witness.tex:45 | issue-4420 args (row 22) | VERIFIED | |
| 32 | "more than kappa=3 witnesses is ambiguous" | method.tex:48-49 | `github_natural_replication/results.json` `compiler.config.kappa`=3 | VERIFIED | |
| 33 | "the limit=3 slots of the PR-outcome and backlog artifacts" | method.tex:51-52 | `github_workflow_families/{pr_outcome,backlog_attention}/final/registry/cand-*.txt` line 10: `limit = Const(3)` | VERIFIED | |
| 34 | "the 23-operator library ... at depth at most two" | method.tex:92-93 | `src/guarded_agentic_compaction/grc/dsl.py` `N_OPERATORS`=23 (evaluated); `compiler.config.max_transform_depth`=2 | VERIFIED | |
| 35 | grid Lambda = {0.02, ..., 0.50} (11 values) | method.tex:109 | `src/.../grc/calibrate.py:52` `GRID` | VERIFIED | |
| 36 | "alpha=0.05, delta=0.1, |Lambda|=11" | method.tex:129 | `compiler.config` alpha 0.05, delta 0.1; `multiplicity_accounting.json` grid_size 11 | VERIFIED | |
| 37 | "a zero-violation family still needs n_eta >= 92 admitted groups" | method.tex:130 | `multiplicity_accounting.json` `n_min['1']`=92; recomputed: smallest n with 1-(0.1/11)^(1/n) <= 0.05 is 92 (U(0,92)=0.04981) | VERIFIED | |
| 38 | "registered |K|=92 cohorts ... every admitted operating point is full coverage" | method.tex:133-134 | `multiplicity_accounting.json` grid_rows: every row with upper <= 0.05 has n=92, coverage 1.0, for all 16 artifacts | VERIFIED | |
| 39 | "abstaining on one group leaves U_eta=0.0503 > alpha" | method.tex:135 | recomputed U(0,91)=1-(0.1/11)^(1/91)=0.050342 | VERIFIED | |
| 40 | "delta=0.05 would need 106 groups" | method.tex:137 | recomputed: smallest n with 1-(0.05/11)^(1/n) <= 0.05 is 106 | VERIFIED | |
| 41 | "The three primary families use 132 discovery records each" | iclr/sections/evaluation.tex:7-8 | `selection.discovery`=132 (pr, backlog); natural `discovery_issue_numbers`=132; validator "pr_outcome/backlog_attention: 132 discovery and 30 disjoint test records" | VERIFIED | |
| 42 | "16 train, 8 dev, and 92 calibration groups (the rest stay unused)" | evaluation.tex:8-9 | `compiler.splits.sizes` = {train 16, dev 8, calibration 92} in all three results.json; `calibration_population_audit/report.json` eligible_unused 14/15/16 | VERIFIED | |
| 43 | "30 balanced held-out records" | evaluation.tex:9-10 | pr/backlog `selection.test_class_counts` 10/10/10; issue-type baseline labels bug/enhancement/question 10/10/10 | VERIFIED | |
| 44 | "The exact-trace filter excludes two issue runs and one PR run" | evaluation.tex:13-14 | `calibration_population_audit/report.json` `excluded_by_discovery_filter`: issue 2 (539, 2781), PR 1 (5700), backlog 0 | VERIFIED | |
| 45 | "All three pass the retained entry guard and gate" | evaluation.tex:14-15 | same file, `excluded_records_passing_entry_guard_and_gate` = [539, 2781], [5700] | VERIFIED | |
| 46 | "spans five frozen public repositories" | evaluation.tex:19 | `github_multirepo_pr_outcome_core/results.json` `repositories` (hf, pandas, requests, pytorch, streamlit) | VERIFIED | |
| 47 | "a balanced rerun on three repositories" | evaluation.tex:22 | `github_multirepo_pr_outcome_balanced/repos/` (pandas, requests, pytorch) | VERIFIED | |
| 48 | "API-Bank and BFCL v4 behave like NESTFUL" | evaluation.tex:28-29 | row 11 | VERIFIED | |
| 49 | gpt-5.6-luna, reasoning effort low; replications gpt-6-luna and claude-sonnet-5 | evaluation.tex:32-36 | natural results.json `run.model`, `run.reasoning_effort`='low'; second_model / second_provider directories; validator decisions rows | VERIFIED | |
| 50 | "gate multiplicity controlled by the Bonferroni term of eq:cp" | evaluation.tex:45-46 | eq:cp (delta/|Lambda|); `multiplicity_accounting.json` | WORDING (minor) | The Bonferroni term covers the 11 thresholds of one candidate, not candidate selection (m=2 for PR and backlog, which then miss 5%). Correct only if read narrowly. The paper acknowledges this elsewhere, so the risk is low |
| 51 | "admits a fixed candidate only when an exact binomial bound on its group-level violation rate is at most alpha" | iclr/sections/related_work.tex:23-24 | Prop. 1; `calibrate.py` | VERIFIED | Correctly scoped to a fixed candidate |
| 52 | "Across 810 compiled held-out GitHub episodes in six studies on the calibrated model" | iclr/sections/discussion.tex:4-5 | validator "§7: 810 held-out episodes ... with one compiled-only failure" and "§7 states the 810-episode headline"; recount: 90 primary + 120 core + 180 balanced + 240 gate-frontier + 120 extended + 60 time-forward | VERIFIED | |
| 53 | "compiled-only failures are 1/270 on excerpt-bearing contracts" | discussion.tex:5 | recount (`e810.py`): issue 30 + PR 30 + backlog 30 + extended 120 + time-forward 60 = 270; one compiled-only miss, extended issue 2737 (`evidence_excerpt_exact` false) | VERIFIED | |
| 54 | "(one-sided bound 1.7%)" | discussion.tex:6 | recomputed Beta^-1(0.95; 2, 269)=0.01745 | VERIFIED / WORDING (minor) | The confidence level (95%) is not stated, and treating 270 episodes from five studies as i.i.d. is an unstated assumption |
| 55 | "0/540 on outcome-only contracts (354 distinct records)" | discussion.tex:6-7 | recount: core 120 + balanced 180 + gate-frontier 240 = 540, 0 compiled-only; distinct (repo, record) = 354; validator checks "354 distinct" in text | VERIFIED | |
| 56 | "The amended 184-group issue study retired" | discussion.tex:10-11 | `results/graded_issue_gate/audit_v2.json` `decision`=retired_before_test; calibration 184 issues, best grid U 0.0546 > 0.05 | VERIFIED | |
| 57 | "counting a creation day or an author as one unit retires every primary family under the registered grid" | discussion.tex:13-15 | `iclr_revision/effective_units.json`: issue/PR/backlog days 90/86/87 (U 0.0509/0.0532/0.0526), authors 82/60/73 (U 0.0557/0.0754/0.0624) | VERIFIED | |
| 58 | "AppWorld's bound retires at scenario or supervisor level" | discussion.tex:15-16 | `external_benchmarks/appworld_compiler_execution.json` `corpus.scenarios_clean`=46, `distinct_supervisors`=79; recomputed U(0,46)=0.0971, U(0,79)=0.0578 | VERIFIED | |
| 59 | "The six-study compiled-only misses are excerpts departing from identical evidence" | discussion.tex:19-20 | row 53 (one miss, 2737, excerpt) | VERIFIED / WORDING (minor) | There is exactly one compiled-only miss, so the plural "misses" overstates it slightly |
| 60 | "One adapted-AWM cell misses five-point noninferiority" | discussion.tex:24-25 | row 8 (backlog/gpt-6-luna) | VERIFIED | |
| 61 | "BIRD's one-call candidate trailed a handwritten wrapper" | discussion.tex:31-32 | `results/bird_one_call_matched_pilot/report.json` rows: shape_set_correct candidate 26/36, manual 28/36, baseline 28/36 | VERIFIED | |
| 62 | "on GitHub workflows matches hand-written programs at about 73% lower model cost than the unchanged agent" | iclr/sections/conclusion.tex:5-6 | `multirepo_end_to_end/summary.json` `pooled_all_run_repositories.resources.reduction_vs_baseline_pct` compiled.cost_usd 73.605, manual 73.598 (760-group pool: 72.71); `github_workflow_families/summary.json` overall cost reduction 58.67% | WORDING (plus rounding) | The figure comes from the PR-outcome end-to-end pool (appendix.tex:846 gives "73.6%"). Rounded, that is about 74%, not 73% (73% only matches the 760-group pool, 72.7%). The sentence reads as a claim about "GitHub workflows" in general. The three primary workflows pool to 58.7% lower estimated cost (per family 32.0/75.3/75.1%). It is also "estimated cost" at list prices. Suggest naming the PR-outcome end-to-end pool and using 73.6% (or "about 74%") |
| 63 | "two primary families miss the adjusted target" | conclusion.tex:7 | row 19 | VERIFIED | |
| 64 | "end-to-end bounds cover one family" | conclusion.tex:7-8 | time-forward `compile.json` family pr_outcome; `supplementary/multirepo-unfiltered-end-to-end-protocol.md:18` family `pr_outcome` | VERIFIED | Consistent with this; inconsistent with problem.tex:101 (row 28) |

### Findings (non-VERIFIED items, most serious first)

1. **MISMATCH: problem.tex:100-103** says every certificate in Section 5 except *one* end-to-end certificate is a replay-contract certificate. Results.tex:152 itself says "Two end-to-end certificates exist", and the multirepo study contributes 9 admitted per-repository final-contract certificates plus pooled bounds. This is stale text from before the multirepo and Amendment 3 results were added.
2. **WORDING: abstract.tex:18-19**: "Most bounds cover replay on selected populations; one covers final answers" is followed straight away by a second final-answer study (760 groups, then 3,560). Change "one" to "two studies". Same root cause as item 1.
3. **WORDING plus rounding: conclusion.tex:5-6**: "about 73% lower model cost" comes from the PR-outcome end-to-end pool (73.6%; appendix.tex:846). That rounds to about 74%; 73% matches only the 760-group pool (72.7%). Unqualified, "on GitHub workflows" invites reading it as the three-workflow headline, where pooled estimated cost falls 58.7% (66.6% fewer requests).
4. **WORDING: abstract.tex:8-9**: "enough independent calibration examples support a finite-sample error bound". Independence is an assumption (day- or author-level units retire every primary family), and most bounds are on replay violation rather than task error. The abstract does flag replay scope later, but not the i.i.d. assumption.
5. **WORDING: abstract.tex:19-24 (minor)**: the bounds in one abstract use different rules. 0.0173 is the single-rule 90% bound; the registered grid would give 0.035. 0.023-0.042 are registered-grid bounds. Only the first is labelled "90%", so a reader may compare them as if they were the same rule.
6. **WORDING: introduction.tex:22-24 and the method.tex:26-27 figure caption (minor)**: "All 132 discovery runs (the traces the compiler learns from)" and "varies across the supporting traces (100 in 130 of 132, 1 in two)". The counts are for all 132 runs. The compiler's supporting traces are 116 (114/2), and the witness is decided on 16 training traces (15/1). The conclusion is unchanged.
7. **WORDING: abstract.tex:14 (minor)**: "1,362 fresh records" includes 18 pilot records. The six noninferiority cells use 1,344.
8. **WORDING: discussion.tex:6 (minor)**: the "one-sided bound 1.7%" leaves the confidence level (95%) and the i.i.d.-episode assumption unstated.
9. **WORDING: discussion.tex:19-20 (minor)**: "compiled-only misses are excerpts" is plural, but there is exactly one (issue 2737).
10. **WORDING: evaluation.tex:45-46 (minor)**: "gate multiplicity controlled by the Bonferroni term" covers thresholds only, not candidate selection (m=2). The paper concedes this elsewhere.

No UNSUPPORTED items: every number in scope traced to a retained raw file or a code constant.

Counts: 64 rows: 54 VERIFIED (row 14 carries a note on mixed bound rules, see finding 5); 4 VERIFIED/WORDING, where the number is right but the sentence overstates (rows 7, 23, 54, 59); 5 WORDING (rows 1, 13, 30, 50, 62); 1 MISMATCH (row 28); 0 UNSUPPORTED.


# Part B


Scope: `paper/iclr/sections/results.tex` (186 lines) and the four tables it `\input`s:
`tables/compiler_decisions.tex`, `tables/primary_results.tex`, `tables/awm_comparison.tex`, `tables/refusal_funnel.tex`.
I also checked `tables/refusal_funnel_all.tex`, because the text quotes its API-Bank and BFCL numbers.
Every number below was checked against the raw per-record or per-group JSON with independent scripts in `paper/reviews/audit_scripts/`: `item1.py`, `bounds.py`, `item3.py`, `core.py`, `awm.py`, `sm.py`, `bird.py`, `bird2.py`, `ci.py`.
I did not run the repository validator (`validate_artifacts.py`), because it may regenerate tables in the repository.
No repository file was edited.
Paths are relative to `paper/` unless they start with `experiments/`.

### Claim table

| # | Claim (short quote) | Location (file:line) | Source (file + field/check) | Status | Note |
|---|---|---|---|---|---|
| 1 | "recovers the program a person would write wherever the retained traces support one, and refuses ... wherever they do not" | results.tex:8-10 | Decisions table; results/recurrence_only_ablation/results.json | WORDING | A universal claim drawn from about 11 rows. The recurrence-only ablation (results.tex:63-66) shows the traces supported a three-read replay that scored 30/30 with 1 request per record. The compiler refused read 3, so for this family the traces did support a program the compiler did not recover. |
| 2 | "abstains on any other" snapshot | results.tex:11 | results/time_forward/pr_outcome/evaluation.json `dispatch.compiled_retained.abstained`=60 | VERIFIED | 60/60 abstain. |
| 3 | 90/90 compiled vs 89/90 unchanged, 90/90 manual | results.tex:45-46; primary_results.tex:7-11 | Per-record `results[]`, repeat 0, of github_natural_replication/results.json, github_workflow_families/{pr_outcome,backlog_attention}/final/results.json | VERIFIED | Recomputed: baseline 30+30+29, compiled 30+30+30, manual 30+30+30. The `factuality_exact`/`overall` checks agree. |
| 4 | Pooled reductions 66.6 / 63.1 / 64.2 / 58.7 %; interfaces 44.2 % | results.tex:46-47; primary_results.tex:11 | Same per-record files; ratio of paired sums | VERIFIED | 66.574 / 63.065 / 64.212 / 58.671; interfaces 44.238. |
| 5 | Per-family reductions 50.0/0.0/39.5/51.7/32.0; 75.0/66.7/80.8/73.0/75.3; 74.8/66.3/81.4/68.9/75.1 | primary_results.tex:7-9 | Same | VERIFIED | Recomputed: 50.0/0.0/39.51/51.74/32.00; 75.0/66.67/80.81/72.99/75.30; 74.79/66.29/81.37/68.89/75.08. |
| 6 | "issue-type routing ... is the low end of every range" | results.tex:49-50 | Same | VERIFIED | Issue-type is the minimum in all five columns. |
| 7 | Break-even after 411, 183, 181 episodes | results.tex:51 | results/cache_accounting.json `families[].break_even_episodes` (410.87, 182.006, 180.60) | VERIFIED | These are the ceilings of the source values. |
| 8 | Discordant pair: backlog 5189 baseline-only, ungrounded excerpt; 0 compiled-only | results.tex:52-54 | backlog final results.json (5189: `comment_grounded` false); iclr_revision/paired_statistics.json `discordance.pooled` | VERIFIED | Recomputed independently. |
| 9 | McNemar p=1; one-sided 95 % bound 3.3 % | results.tex:54-55 | paired_statistics.json (`mcnemar_exact_p` 1.0, `compiled_only_failure_upper95` 0.03274) | VERIFIED | 1-0.05^(1/90)=0.03274. |
| 10 | "a rerun scored 30/30 in every arm" | results.tex:55 | github_workflow_families/{pr_outcome,backlog_attention}/headroom_ablation/results.json | VERIFIED | Five arms × 30/30 in each family; the backlog rerun includes record 5189. |
| 11 | Hand-written 90/90, ties on requests, fewer interfaces and tokens, compiled has lower latency | results.tex:57-59 | Per-record sums | VERIFIED | Requests 120 vs 120; interfaces 90 vs 150; tokens 85,155 vs 108,839; latency 203,188 vs 192,357 ms. |
| 12 | Recurrence-only 30/30 vs \method 30/30; 1 request vs 2 | results.tex:63-65 | recurrence_only_ablation/results.json `per_field_exact.overall`=30, `aggregate...provider_requests`=30 over n=30; primary issue compiled 60 requests over 30 records | VERIFIED | |
| 13 | AWM: "attempts all 8,172 episodes on 1,362 fresh records" | results.tex:72-73 | experiments/generalization_gate/checkpoint.json `rows` | VERIFIED | 8,172 rows (8,064 primary + 108 pilot); 8,171 completed, 1 failed; 1,362 distinct records = 1,344 primary + 18 pilot. |
| 14 | AWM caption "1,344 fresh primary records" | results.tex:33-34 | Same | VERIFIED | Correct, but it differs from the text's 1,362, which includes the 18 pilot records. Using one count in both places, or noting the pilot, would avoid confusion. |
| 15 | 50–75 % fewer requests; 36.9–79.1 % less estimated cost | results.tex:74-75 | checkpoint.json per-episode metrics (GAC vs `awm_offline_adapted`) | VERIFIED | Request reductions 75.0/75.0/50.0/50.0/75.0/75.0 %; cost savings 74.7/76.8/36.9/48.9/77.8/79.1 %. |
| 16 | 5/6 cells pass the 5-pt margin; second-model backlog 142/144 vs 143/144, bound 5.86 %; only the 2 PR cells pass 2 pt; none pass 1 pt | results.tex:76-79 | Recomputed: losses = AWM-only correct; U=beta.ppf(1-0.05/6, L+1, n-L) | VERIFIED | 100U = 3.27/5.86/3.61/4.04/1.43/1.43. |
| 17 | AWM table: all cells (n, correct counts, 100U, dagger, Requests 1/4 or 2/4, USD/1k, Saving) | awm_comparison.tex:9-14 | checkpoint.json recomputation (awm.py) | VERIFIED | Every cell matches, e.g. USD/1k 0.204/0.806, 0.088/0.380, 0.588/0.931, 0.210/0.411, 0.164/0.739, 0.074/0.353. |
| 18 | Re-discovery re-derives identical programs on 2 of 3 families and refuses backlog (Sonnet at 91 and 90 of 92) | results.tex:83-85; compiler_decisions.tex:28,31 | github_workflow_families/backlog_attention/{gpt6_luna_rediscovery,anthropic_sonnet5_rediscovery}/failure.json | VERIFIED | gpt-6-luna: 113/132 exact traces, 116 needed. Sonnet: `max_n_accepted` 90 (3-read) and 91 (2-read), tightest bounds 0.0509 and 0.0503 > 0.05. |
| 19 | "four compiled-only excerpt misses on Sonnet" | results.tex:85-86 | second_provider_replication/issue_type/results.json; pr_outcome/anthropic_sonnet5_rediscovery/results.json | VERIFIED | 4248 and 6829 (`evidence_excerpt_exact`); 5401 and 6988 (`comment_grounded`). |
| 20 | Transfer to gpt-6-luna: one compiled-only miss in 90 | results.tex:86-87 | second_model_replication/issue_type/results.json; github_workflow_families/*/gpt6_luna/results.json | VERIFIED | One compiled-only miss (issue 6532). The issue-type compiled arm scored 28/30, but the second miss is a both-miss. |
| 21 | BIRD: 5 dev DBs with ≥146 questions; per-question design retires all 5; schema-first admitted on all 5 | results.tex:93-95; compiler_decisions.tex:34,37 | bird/preflight.json `dev_question_counts` (toxicology has 145); bird/summary.json `designs.*.families[].status` | VERIFIED | |
| 22 | "Retires on 5/5 (26/26 train)"; "4 at synthesis; 1 at support, 34/92" | compiler_decisions.tex:34 | bird/train/summary.json; bird/standard/*/compile.json `rejection_by_stage` | VERIFIED | card_games was calibrated on 34 groups; 4 DBs failed at `synthesize:ungroundable_slot`. |
| 23 | "Admits 26/31 databases"; gate 92/92 | compiler_decisions.tex:37 | bird/summary.json + train/summary.json | VERIFIED | 5 dev + 21 of 26 train; every admitted DB is at 92/0. |
| 24 | 150 sealed questions: dispatched every time, 97 vs 94, McNemar p=0.45 | results.tex:95-97 | bird/schema_first/*/evaluation.json (`quality.execution_correct`, `dispatch.compacted`) | VERIFIED | 150/150 compacted; 97 vs 94; discordant 5 vs 2; p=0.453. |
| 25 | Requests −44.9 %, latency −29.4 % vs the warm rerun | results.tex:97-98 | Same | VERIFIED | 44.92 % and 29.38 % (ratio of sums against `baseline_repeat`). |
| 26 | Second model 93 vs 91 of 150; training 402 vs 403 of 630 on 21 of 26 DBs | results.tex:98-100 | bird/replications/gpt-6-luna/schema_first/*/evaluation.json; bird/train/schema_first/*/evaluation.json | WORDING | Counts are correct, but they compare against the first-run baseline. The warm rerun of the unchanged agent scored 95/150 (second model) and 412/630 (training), so compiled is 2 and 10 below it. This is disclosed only in the appendix (tables/bird_denominators.tex). The line before compares resources against the warm rerun, so the comparator switches mid-paragraph. |
| 27 | Requests fall 49.6 % and 45.8 % | results.tex:100 | Same; bird/denominator_audit.json `paired_resource_reductions.requests` | WORDING | 49.61 % and 45.76 % are against the first-run baseline, while the 44.9 % in the line before is against the warm rerun. Against the warm rerun they are 49.36 % and 45.86 %, so the magnitudes are robust, but the comparator is not stated. |
| 28 | Training paired 95 % interval [−3.27, +2.96] pts under i.i.d. pairs | results.tex:100-102 | bird/quality_sensitivity.json (17 gains, 18 losses, n=630) | VERIFIED | Recomputed: 97.5 % two-sided CP for gains and losses, endpoints subtracted, gives [−3.27, +2.96]. The i.i.d. caveat is stated. |
| 29 | Second provider's agent never ran a fixed opening; refused | results.tex:102-103 | bird/replications/claude-sonnet-5/summary.json (`schema_all_tables_share` 0.0, status retired on all DBs) | VERIFIED | |
| 30 | NESTFUL 1,415 traces; 96.3 % grounded; 1,207 windows; 32 at floor; 12 synthesized; 24/12/0; n_max 26; 0 admitted | results.tex:125-128; refusal_funnel.tex:5 | nestful/results.json `compiler.{n_episodes, provenance.expected_producer_recall, n_full_windows, compiler_families.n_support_ge_5, held_out_replay.*, exact_gate.max_observed_family_support}` | VERIFIED | Grounded share 5,531/5,746 = 96.26 %. |
| 31 | "NESTFUL, the largest trace corpus the compiler ingests here" | results.tex:125-126 | bird/*/schema_first/*/discovery.json | WORDING (low) | True for a single substrate corpus. Across its 31 per-database corpora, BIRD schema-first discovery feeds the compiler 4,047 traces. |
| 32 | AppWorld 136 traces; 63.2 % grounded; 136 windows; 33 at floor; 1 synthesized; 34/0/0; n_max 136; 1 admitted (arm A) | refusal_funnel.tex:6 | external_benchmarks/appworld_compiler_execution.json `arms.A` | VERIFIED | 9,480/(9,480+2,933+2,309+279) = 63.2 %; `families_support_ge_3`=33. |
| 33 | API-Bank n_max 8; BFCL v4 n_max 15 (retire) | results.tex:128-129; compiler_decisions.tex:40 | external_benchmarks/{api_bank_execution,bfcl_compiler_execution}.json `compiler.exact_gate.max_observed_family_support` | VERIFIED | refusal_funnel_all rows also match: 212/63.5 %/37/8/2/0-2-0 and 200/68.0 %/86/9/4/3-3-0. |
| 34 | AppWorld admits one argument-free two-call artifact at 92/92, U=0.0498, compiler-wide under one effect arm and per-candidate under the other | results.tex:131-134 | appworld_compiler_execution.json `admission.{A,B}` | VERIFIED | Arm A: 1 candidate (m=1). Arm B: 6 candidates, all 6 reached calibration (groups 89, 92, 92, 90, 46, 26; one emitted, one dominated at 92/92, four retired), so the selection-adjusted bound is 0.0663 and the 0.0498 is per-candidate. In arm B the emitted candidate is listed as profile→passwords→phone.login. tables/appworld_admission.tex reports it as a 2-step justified prefix, so "two-call" is consistent with the appendix. |
| 35 | 8,190 released trajectories; entry-eligible 37.9 %; almost always full-code, almost never ReAct/plan-execute | results.tex:134-137 | external_benchmarks/appworld_dispatch_preflight.json `by_agent_family`, `pooled` | VERIFIED | 3,102/8,190 = 37.88 %; full-code 2,339/2,340; ReAct 0/2,340; plan-execute 1/2,340. |
| 36 | Prologue "recovers only 2 more of 4,680" | results.tex:137-138 | appworld_dispatch_prologue_preflight.json `by_agent_family.react.after_eligible_after_exact_prologue`=2 | VERIFIED | |
| 37 | AppWorld row: "1 admitted, 4 retired; fires in 1 of 4,680 runs; retired bounds 0.051, 0.051, 1.000, 1.000" | compiler_decisions.tex:43 | appworld_compiler_execution.json `admission.B.candidate_records[].rejected` | VERIFIED | Faithful to the compiler messages. For n=46 and n=26 a zero-violation CP bound would be 0.097 and 0.165. The 1.000 reflects that no group was accepted at any threshold, which a footnote could make clear. |
| 38 | Primary artifacts admitted at 92/92, U_η=0.0498, conditional on i.i.d. groups | results.tex:143-145; compiler_decisions caption | github_workflow_families/*/final/results.json `compiler.artifact.gate`; natural_replication `compiler.candidates[1].gate` | VERIFIED | n_calibration_groups 92, observed_violations 0, risk_upper_bound 0.049809, all recomputed. |
| 39 | Compiler-wide for issue-type (m=1); per-candidate for PR and backlog (m=2); corrected U=0.0569, compiler-wide only at α≥0.057 | results.tex:146-148 | iclr_revision/multiplicity_accounting.json; recompiled_candidates_{pr_outcome,backlog_attention}.json (both candidates calibrated at 92/0) | VERIFIED | U(0, 92, 1−0.1/22) = 0.056941. Groups needed for compiler-wide at m=2: 106. |
| 40 | Decisions caption "Admits: replay gate passed (92/92 clean groups, bound 0.0498 ≤ 0.05; end to end for time-forward)" | compiler_decisions.tex:4 | As #38 and #39 | WORDING (low) | The caption has no per-candidate qualifier. For PR and backlog (m=2) and AppWorld arm B (m=5) the selection-adjusted bound exceeds 0.05. The time-forward "admit" is 132/132 at 0.0173 under a 90 % single rule, not 92/92 at 0.0498. |
| 41 | Post-cutoff cohort: 132 fresh groups (84 open, 48 merged, no closed-unmerged), 0 misses, bound 0.0173 (single rule), 0.035 (grid) | results.tex:152-155; compiler_decisions.tex:25 | time_forward/pr_outcome/{certificate,selection,calibration_checkpoint}.json | VERIFIED (numbers) / WORDING (low) | Recomputed 132/132 COMPACTED and exact; 1−0.1^(1/132) = 0.01729; 1−(0.1/11)^(1/132) = 0.03498. The confidence level (90 %, δ=0.10) is not stated beside 0.0173. |
| 42 | "Two end-to-end certificates exist" | results.tex:152 | multirepo_end_to_end/summary.json | WORDING (low) | The second study yields per-repository certificates (4 registered + 5 Amendment-3 admissions) plus pooled ones. "Two end-to-end studies" would be accurate. |
| 43 | Later study: one PR per author in four repos, misses 3 of 760, each repo has its own frozen candidate, bounds 0.023–0.042 | results.tex:155-158 | multirepo_end_to_end/*/calibration_groups.json (registered stage) | VERIFIED | Recomputed: n=760, compiled met 757 (k=3), pooled U=0.01332. Per repo: hf 200/1/0.0333, pandas 200/2/0.0419, streamlit 160/0/0.0290, pytorch 200/0/0.0232. 760 distinct authors. psf/requests was not run (shortfall). |
| 44 | Seven repos at n=400 admit five, retire two | results.tex:158 | multirepo_end_to_end/*/calibration_groups.json (amendment_3) | VERIFIED | next.js 1/0.0167, django 2/0.0211, kubernetes 3/0.0252, vscode 3/0.0252, godot 7/0.0399 admit; node 14/0.0632 and cpython 17/0.0726 retire. |
| 45 | All eleven: compiled / unchanged / hand-written meet 3,510 / 3,507 / 3,504 of 3,560 | results.tex:158-160 | Same, all 11 calibration_groups.json | VERIFIED | Recomputed. Pooled k=50, U=0.01944 (single rule 0.01692); cost reduction 73.60 %. The compiled count includes the two retired repos (31 of the 50 violations) and 3 kubernetes fallbacks. It is a conservative arm count, not deployed behavior. |
| 46 | Full / support-only / deterministic guards route identically on all 2,724 record–model cases | results.tex:160-162 | experiments/generalization_gate/seal.json `cells[].probe` | VERIFIED | 150+150+606+606+606+606 = 2,724, `all_equivalent` true. Correctly flagged as conditional on admission. |
| 47 | Five frozen repos, 120/120 across four; pytorch retires (84 closed, 30 open, 2 merged; bound 1.000); Gate 92/92 each | results.tex:166-168; compiler_decisions.tex:22 | github_multirepo_pr_outcome_core/results.json `repositories[]` | VERIFIED | Recomputed 120/120 per arm; the four admitted repos are at 92/0/0.0498; the pytorch error text gives "tightest attainable ... 1.000"; class mix 84/30/2. |
| 48 | Two-read task; requests −44.4 % (66.7 % where dispatched); balanced rerun 180/180 at −66.7 % | results.tex:167-171 | core and balanced results.json per-record | VERIFIED | Core 80/120 dispatched (open class abstains); 44.44 % overall, 66.67 % on dispatched; balanced 180/180, 66.67 %. |
| 49 | Live recovery: 2,304 scheduled; 72 confirmation groups; scope guard 186/216 → 205/216, +8.80 [3.70, 13.89] | results.tex:173-178 | experiments/live_recovery_completion/analysis.json `groups.confirmation.ordinary` | VERIFIED | no_entry_hull 186, full 205; paired mean 0.08796, CI [0.0370, 0.1389]. The interval is labeled descriptive. |
| 50 | Completeness check 204/216 vs 205/216; repairs 22/27; full does not beat baseline | results.tex:178-180 | Same, `capped_response_stress` | VERIFIED | Baseline is 204/216 (ordinary) and 211/216 (capped) vs full 205/205. |
| 51 | Drift: 144 paired groups; 89 paired records; zero wrong in every arm | results.tex:181-184 | drift_ablation/results.json `pooled`; drift_recorded_replay/results.json `pooled` | VERIFIED | |
| 52 | Continuation-graded: 39/60 silent wrong in both arms; 40 under corrected grader | results.tex:184-185 | drift_continuation_graded/results.json `silent_wrong_records` (39/39, paired_records 60); supplementary/drift-continuation-graded-protocol.md:169-172 | VERIFIED (39) / documented only (40) | The 40 is stated in a protocol note (PR 6694 substring artifact). No retained regraded artifact holds it. |

### Re-derivations (six required items)

#### 1. Primary results (item1.py)
Sources: per-record `results[]` (repeat 0) of the three family files. Exactness is `quality.factuality_exact`, falling back to `overall`; both give the same counts. Pooled reduction = 1 − Σcompiled/Σbaseline.

| Quantity | Recomputed | Paper |
|---|---|---|
| Exact contracts, baseline / compiled / manual | 89 / 90 / 90 of 90 | 89/90, 90/90, 90/90 |
| Pooled requests (359 → 120) | 66.574 % | 66.6 |
| Pooled tokens (294,677 → 108,839) | 63.065 % | 63.1 |
| Pooled latency (537,496 → 192,357 ms) | 64.212 % | 64.2 |
| Pooled cost ($0.068394 → $0.028267) | 58.671 % | 58.7 |
| Pooled interfaces (269 → 150) | 44.238 % | 44.2 |
| Issue-type (req/int/tok/lat/cost) | 50.00/0.00/39.51/51.74/32.00 | 50.0/0.0/39.5/51.7/32.0 |
| PR-outcome | 75.00/66.67/80.81/72.99/75.30 | 75.0/66.7/80.8/73.0/75.3 |
| Backlog | 74.79/66.29/81.37/68.89/75.08 | 74.8/66.3/81.4/68.9/75.1 |
| Baseline-only miss | backlog 5189 (`comment_grounded` false) | 5189 |

#### 2. Finite-sample bounds (bounds.py)
U(k,n,c) = beta.ppf(c, k+1, n−k), or 1−(1−c)^(1/n) for k=0. Registered grid c = 1 − δ/(m·|Λ|), with δ=0.10 and |Λ|=11. Single rule c = 1 − δ/m.
The producing script (`paper/scripts/iclr_revision_statistics.py`, `gamma_for(m)=DELTA/(m*GRID_SIZE)`) enters m as a Bonferroni split of δ.

| Quantity | Recomputed | Paper |
|---|---|---|
| U(0, 92), m=1 grid | 0.049809 | 0.0498 |
| U(0, 92), m=2 grid (PR, backlog: both candidates calibrated at 92/0 per recompiled_candidates_*.json) | 0.056941 | 0.0569 / "α ≥ 0.057" |
| n needed for compiler-wide at m=2 | 106 | 106 (registry) |
| U(0, 91) / U(0, 90) (Sonnet backlog) | 0.05034 / 0.05089 | "bound above 0.05" |
| U(0, 89) / U(0, 90) (AppWorld retired) | 0.0514 / 0.0509 | 0.051, 0.051 |
| AppWorld arm B, m=6 selection-adjusted | 0.0681 | "per-candidate under the other" (correct) |
| Post-cutoff 0/132, single rule (c=0.90) | 0.017293 | 0.0173 |
| Post-cutoff 0/132, grid (c=1−0.1/11) | 0.034983 | 0.035 |
| Primary compiled-only 0/90, one-sided 95 % | 0.03274 | 3.3 % |

#### 3. Cross-repository and multi-repository end-to-end (item3.py, core.py)
Recomputed from every `multirepo_end_to_end/<repo>/calibration_groups.json`.
- n counts groups that are eligible and either dispatched or abstained.
- k counts groups that dispatched and missed the contract.
- Grid c = 1−0.1/11. A repository is admitted when U ≤ 0.05.

| Repo (stage) | n | k | U grid | U single | Decision | Compiled / unchanged / manual met |
|---|---|---|---|---|---|---|
| huggingface/datasets (reg) | 200 | 1 | 0.0333 | 0.0193 | admit | 199/199/198 |
| pandas (reg) | 200 | 2 | 0.0419 | 0.0264 | admit | 198/197/197 |
| pytorch (reg) | 200 | 0 | 0.0232 | 0.0114 | admit | 200/200/199 |
| streamlit (reg) | 160 | 0 | 0.0290 | 0.0143 | admit | 160/158/160 |
| **Registered pool** | **760** | **3** | **0.0133** | 0.0088 | admit | 757/754/754 |
| next.js (A3) | 400 | 1 | 0.0167 | 0.0097 | admit | 399/396/398 |
| django (A3) | 400 | 2 | 0.0211 | 0.0133 | admit | 398/397/399 |
| kubernetes (A3) | 400 | 3 | 0.0252 | 0.0166 | admit | 397/394/397 |
| vscode (A3) | 400 | 3 | 0.0252 | 0.0166 | admit | 397/398/394 |
| godot (A3) | 400 | 7 | 0.0399 | 0.0293 | admit | 393/399/395 |
| node (A3) | 400 | 14 | 0.0632 | 0.0499 | retire | 386/384/380 |
| cpython (A3) | 400 | 17 | 0.0726 | 0.0585 | retire | 383/385/387 |
| **All eleven** | **3,560** | **50** | **0.0194** | 0.0169 | admit | **3,510 / 3,507 / 3,504** |

- All-eleven cost reduction, compiled vs baseline: 73.60 % (paper 73.6 %).
- The paper's "bounds 0.023–0.042" matches the min and max of the four registered repositories.
- Five frozen repositories (github_multirepo_pr_outcome_core):
  - Four repositories admit at 92/0/0.0498, with 120/120 per arm.
  - pytorch retires with tightest bound 1.000 (discovery mix 84 closed-unmerged / 30 open / 2 merged).
  - Requests fall 44.44 % overall and 66.67 % on the 80/120 dispatched records.
  - The balanced rerun (pandas, requests, pytorch) scores 180/180 at 66.67 %.

#### 4. Trace benchmarks
| Substrate | Traces | Grounded | Windows | At floor | Synth | Replay p/a/w | n_max | Adm | Paper |
|---|---|---|---|---|---|---|---|---|---|
| NESTFUL | 1,415 | 96.26 % | 1,207 | 32 (≥5) | 12 | 24/12/0 | 26 | 0 | match |
| API-Bank | 212 | 63.45 % | 37 | 8 | 2 | 0/2/0 | 8 | 0 | match |
| BFCL v4 | 200 | 68.03 % | 86 | 9 | 4 | 3/3/0 | 15 | 0 | match |
| AppWorld (arm A) | 136 | 63.20 % | 136 | 33 (≥3) | 1 | 34/0/0 | 136 | 1 | match |

- AppWorld dispatch eligibility: 3,102/8,190 = 37.88 %. ReAct + plan-execute: 1/4,680. The prologue adds 2 (ReAct).
- BFCL `get_flight_cost` mutates state on 36/36 calls.

#### 5. Cross-model / cross-provider and AWM (sm.py, awm.py)
- Transfer of retained artifacts to gpt-6-luna:
  - Issue-type: compiled 28/30, baseline 29/30. There is one compiled-only miss (6532) and one both-miss.
  - PR: 30/30. Backlog: compiled 30/30 vs baseline 29/30.
  - Total compiled-only misses: 1 of 90, matching the paper.
- Re-discovery:
  - gpt-6-luna issue and PR: 30/30 compiled. Backlog refused at discovery (113 < 116).
  - Sonnet issue: compiled-only misses 4248 and 6829. Sonnet PR: 5401 and 6988. That is 4 in total, matching the paper. Backlog refused at calibration (90 and 91 accepted groups).
- AWM, from checkpoint.json:
  - 8,172 attempted; 8,171 completed; 1,362 distinct records (1,344 primary + 18 pilot).
  - The six cells' correct counts, losses, 100U, request ratios, USD/1k and savings all match awm_comparison.tex exactly (see row 17).
  - Margins: 5/6 pass 5 pp, 2/6 pass 2 pp, 0/6 pass 1 pp.

#### 6. BIRD (bird.py, bird2.py, ci.py)
| Quantity | Recomputed | Paper |
|---|---|---|
| Dev DBs with ≥146 questions | 5 (next is toxicology at 145) | 5 |
| Schema-first admitted dev + train | 5 + 21 = 26 of 31 | 26/31 |
| Sealed questions; compiled dispatched | 150; 150/150 | 150; every time |
| Correct, compiled vs baseline | 97 vs 94 (discordant 5/2, p=0.4531) | 97 vs 94, p=0.45 |
| Requests / latency vs warm rerun | −44.92 % / −29.38 % | 44.9 / 29.4 |
| Second model (gpt-6-luna) | compiled 93, baseline 91, **warm rerun 95**; requests −49.61 % vs baseline (−49.36 % vs warm) | 93 vs 91; 49.6 % |
| Training (21 DBs, 630 questions) | compiled 402, baseline 403, **warm rerun 412**; requests −45.76 % vs baseline (−45.86 % vs warm) | 402 vs 403; 45.8 % |
| Training paired interval | [−3.27, +2.96] (97.5 % two-sided CP for gains 17 and losses 18) | [−3.27, +2.96] |

### Statistical-wording review
- **i.i.d./exchangeable assumption**:
  - Stated for the primary 92-group bound ("conditional on i.i.d. groups from the selected population", :145) and for the BIRD interval (:101).
  - Not restated beside the post-cutoff 0.0173 (:152-155), the multi-repo bounds 0.023–0.042 (:158), or the AppWorld 0.0498 (:133).
  - The :145 sentence arguably covers these, but the multi-repo study's independence unit is the author, which is not said here.
- **Per-candidate vs compiler-wide**:
  - Stated explicitly for the primary families (:146-148) and for AppWorld (:133-134).
  - The decisions-table caption omits it (row 40).
- **Replay vs end-to-end**:
  - The primary bound is called "a replay bound" (:145), and end-to-end certificates are separated out (:152). That is good.
  - The decisions caption says "replay gate passed ... end to end for time-forward", which is adequate.
- **Overstatements**: none of the bounds is described as a deployment or safety guarantee. The text says "five points is a research tolerance, not a safety threshold" (:79-80) and "not a live-answer certificate" (:181). The main overreach is the qualitative sentence at :8-10 (row 1).

### Findings (non-VERIFIED, most serious first)
1. **WORDING, moderate (results.tex:98-100)**: BIRD second-model and training accuracy are compared to the first-run baseline. The warm rerun of the unchanged agent scored 95/150 and 412/630, so compiled (93, 402) trails it by 2 and 10 questions (1.6 pt on training). This appears only in tables/bird_denominators.tex. The preceding sentence uses the warm rerun as comparator for resources, so the paragraph switches comparators without saying so. Fix: name the comparator, and report or footnote the warm-rerun counts.
2. **WORDING, moderate (results.tex:100)**: "requests fall 49.6 % and 45.8 %" are against the first-run baseline, while the 44.9 % just before is against the warm rerun. Against the warm rerun the values are 49.4 % and 45.9 %, so the magnitudes hold. State the comparator.
3. **WORDING, moderate (results.tex:8-10)**: "recovers the program a person would write wherever the retained traces support one" is a universal claim. The recurrence-only ablation (:63-66) shows the issue-type traces supported a three-read replay with 30/30 and half the requests, and the compiler refused it on grounding. Fix: scope the claim to "on the families in the table", or say "or refuses conservatively".
4. **WORDING, low (compiler_decisions.tex:4 caption)**: "92/92 clean groups, bound 0.0498 ≤ 0.05" has no per-candidate qualifier. The selection-adjusted bound is 0.0569 for PR and backlog (m=2) and 0.0681 for AppWorld arm B (m=6; the paper's 0.068). The time-forward admission is 132/132 at 0.0173 under a 90 % single rule, not 92/92.
5. **WORDING, low (results.tex:152-155)**: The 0.0173 bound has no confidence level beside it (90 %, δ=0.10, single pre-registered rule), and "Two end-to-end certificates exist" undercounts: the second study gives 9 per-repository admissions plus pooled certificates. Suggested wording: "Two end-to-end studies exist".
6. **WORDING, low (results.tex:125-126)**: "the largest trace corpus the compiler ingests here (1,415)" holds per substrate. BIRD schema-first feeds the compiler 4,047 discovery traces across 31 per-database corpora.
7. **Minor clarity (compiler_decisions.tex:43)**: The retired bounds "1.000, 1.000" for AppWorld candidates at n=46 and n=26 faithfully copy the compiler message (no group accepted at any threshold). A zero-violation CP bound at those n would be 0.097 and 0.165, so a reader may misread 1.000 as a CP value.
8. **Minor consistency (results.tex:33 vs :73)**: The AWM caption says "1,344 fresh primary records" and the text says "1,362 fresh records". Both are correct (the 18 pilot records are the difference); harmonize or say so.
9. **Provenance note (results.tex:185)**: "40 under the corrected grader" is supported only by a protocol note (supplementary/drift-continuation-graded-protocol.md:169-172). The retained results.json records 39/39. No regraded artifact is retained.

No MISMATCH was found. Every number in results.tex and its four input tables matches the raw results.


## Third pass (2026-11-08, three independent checkers)

Three fresh checkers re-derived everything from the sources with the first two passes treated as untrusted.
Reports: `verify_replies.md`, `audit_third_pass.md`, `xref_check.md` (session scratch; findings are recorded here).

### A. Paper (about 75 claims in the abstract, §1, §5.1–5.4, §8, Tables 1–6 and Figure 3, recomputed from per-record JSON)

- **MISMATCH: none.** Every headline and table number reproduces (contracts 90/90, 90/90, 89/90; reductions 66.6/44.2/63.1/64.2/58.7; break-even 411/183/181; 0.0498/0.0569/106; 0/132 → 0.0173 and 0.035; 3/760 → 0.0133 with per-repository 0.0232–0.0419; Amendment 3 k = 1, 2, 3, 3, 7 admitted and 14, 17 retired; 3,510/3,507/3,504 of 3,560, k = 50, U = 0.0194, 73.6%; AWM six cells and 8,172/1,362/1,344/2,724; BIRD 26/31, 97 vs 94 (p = 0.453), −44.9%/−29.4% vs the warm rerun, 93 vs 91 (warm 95), 402 vs 403 (warm 412), 49.6%/45.8% on paired first runs; live recovery 2,304, 186 → 205 (+8.80, [3.70, 13.89]), 210/204, 22/27; drift 144/89/39 of 60; Figure 3 U(91) = 0.0503, U(92) = 0.0498).
- **UNSUPPORTED (1), fixed:** §5.4 "(40 under the corrected grader)": no retained regraded artifact (results.json records 39/39). Removed (paper-changes 21).
- **Wording fixed:** abstract "safely" (16); abstract bound scales unlabelled and "each admitted" ambiguous (17); Table 1 "no safety bound" (18); Table 1 AppWorld "1 admitted, 4 retired" omits the dominated candidate, six reached calibration (19); §1 "the traces the compiler learns from" (20); §8 "58.7–73.6%" joins two studies (22); App. F.7 two stale "one certificate"/"except the post-cutoff one" sentences (23); Table 28 caption "last row" (24).
- **Second-pass note corrected:** the B34 note said AppWorld arm B had 5 calibrated candidates (0.0663, m = 5); the file shows all six reached calibration, so the selection-adjusted bound is 0.0681 (m = 6), which is the paper's 0.068. The paper was right; the note is fixed above.
- **Statistics (quotes checked):** the level and one-sidedness are stated at Eq. (7), Prop. 1, §5.1, §5.4, App. C and App. G; the grid level is given as 1 − 0.1/11, never as a percentage in the main text; the abstract's grid bounds are now labelled "registered-grid". Corrections: Bonferroni over the eleven thresholds (Eq. 7), over m candidates (App. A), over the six AWM cells (Table 3, App. K). Not corrected, and the text says so only for the pooled row: across the eleven multi-repository repositories ("assuming exchangeable repositories"), across the three primary families, and across the six pooled studies in §7; the discordance bounds and McNemar p-values are descriptive. i.i.d. is stated in Prop. 1, App. A, App. C, §5.4, §7, the Table 28 caption, App. G and App. F.2; the doubtful spots the paper names are exact-trace filtering before calibration (§4, App. G) and author-level independence (App. F.2); it does not connect the 47/50 excerpt failures "mostly in bot comments" to content-level clustering across authors, and it pools eleven repositories with k from 0 to 17 under an exchangeability assumption it states but does not test. Overstatement: only "safely" (abstract) and "no safety bound" (Table 1), both fixed.
- **Open, unchanged:** Table 3's 100U level only in App. K; §5.1 1,362 vs Table 3 1,344 (both correct: 18 pilot episodes, App. J); AppWorld retired "1.000, 1.000" is the compiler message, not a Clopper–Pearson value.

### B. Replies (107 items)

- VERIFIED 95; MISMATCH 1; UNSUPPORTED 3 distinct facts. Every Clopper–Pearson bound, McNemar and Fisher p-value in the replies recomputes exactly; every Section/Table/Figure/Appendix/Eq. pointer resolves to the right object (second checker and the cross-reference checker agree); the two verbatim quotes match the PDF.
- **Fixed:** Ans-3 cited `multiplicity_accounting.json` for the day/author sensitivity, which it does not contain → now Table 31 and `effective_units.json`. Ans-general said the abstract and conclusion state the day/author retirement; they state the two-family miss, Section 7 and Table 31 state the sensitivity → fixed. Ans-3's 277/197/117 no-go figures had no retained source on `main` → the preflight record is imported from `agent/c1-gate` and cited (`paper/results/graded_issue_gate_tf/preflight.json`; `fresh-issue-gate-single-look-protocol.md`), and the reply now gives the record's own numbers (31 to 113 calibration groups under the two exclusion rules against about 150 needed). The 6–10 and 12–16 working-day figures are author estimates: kept as "we estimate" in Ans-1 and Ans-2, dropped from Ans-general. Ans-2 "90/90 contracts and equal requests (Table 14)" → contracts in Table 2, request tie and the hand-written program's better token and cost reductions (71.1% vs 63.1%; 60.4% vs 58.7%) in Table 14, which also closes R2's partial point. Ans-2 "Evidence that the automation is safe at scale" → "Evidence at larger scale"; flattering opener trimmed; R2's "changes the risk budget and threshold grid" clause now answered. "44.9% fewer requests" now says "than a warm rerun" wherever it appears. `_calibration_samples` cited by full path.
- **Lengths after edits:** Ans-general 4,948; Ans-1 4,267 / 3,222 / 3,616; Ans-2 4,355 / 4,991; Ans-3 4,201 / 3,244 (limit 5,000).
- **Coverage:** every concern and question in ICLR-1/2/3 is addressed; the two partial items above are closed.

### C. Cross-references and supporting files

- Upload PDF and README agreed before this pass (63 pages; SHA matched; build PDF byte-identical). After this pass the PDF is rebuilt with an identical label map; README SHA updated.
- Fixed: `review-map.md` numbered Reviewer 1's weaknesses W1–W6 against the reviewer's five (now W1, W2a, W2b, W3, W4, W5, matching Ans-1); R3-Q1 row said all three primary families lack a selection-wide bound (issue-type routing, one candidate, has one); R1-W2 pointed to §2 for the design comparison (it is §6 and App. N); R3-Q2 arithmetic aligned with the no-go record; this file's App. C page (22), BIRD release note (it is in the paper, App. F.6) and C2 section (§5.2) corrected; upload README path to the abstract snippet corrected.

## Fourth pass (2026-11-09, funnel and pilot folded into Appendix N and the replies)

Scope: the new App. N subsection and every reply sentence that cites it. Each number was traced to the raw file:
13 cohorts / 13 reproductions, support-only == full on all 13, one divergence with 0 violations and 1 unproductive
of 92 (`compiler_funnel/results.json: summary, cohorts[issue_type]`); 277/197/193 pool, 128/65 split, 124 vs 4
comment limits, 127 eligible (`compiler_funnel_pilot/preflight.json`, `discovery_checkpoint.json`); 16/16
training agreement, dev 1 and calibration 3 `limit = 1`, gate 92/0/0.0498 (`compile.json`); 65/65, 63/65, 64/65,
requests 1.00/1.00/4.00, dispatched 65, McNemar p = 0.50 and 1.0, misses 7624 / 7990, 8048 all
`evidence_excerpt_exact` false with every other field true (`results.json: test`); spend 0.230647 USD
(`ledger.json`). "65 pairs detect a comparator miss rate of about 12% at 80% power" is 11.9% from
`expansion_synthesis/power.json`. The "15 of 16 training windows used 100" figure is the funnel's majority log
(`modal_share` 15/16). No mismatch. Reply part lengths after the edits: general 4,998; R1 4,267 / 4,012 / 3,616;
R2 4,875 / 4,993; R3 4,201 / 3,397; all under 5,000.

## Length margin (2026-11-09)

OpenReview's 5,000-character limit may count a line break as two characters. Every part was re-trimmed so that it
stays under 4,900 even under that count (characters, then with each newline counted twice): general 4,846 /
4,870; R1 4,267 / 4,012 / 3,616 and 4,290 / 4,032 / 3,638; R2 4,866 / 4,866 and 4,891 / 4,895; R3 4,201 / 3,397 and 4,224 / 3,416.
Wording only; no number or pointer changed.
