# Recurrence-only replay ablation protocol (issue-type routing)

**Status: PRE-REGISTERED on 2026-09-22; EXECUTED on 2026-09-24** (observed results at the end of
this document). The design below is unchanged from the pre-registration; it fixed the arm,
cohort, endpoints, and decision rule before any spend.

## Why this arm, and why only on issue-type routing

The comparison the paper owes is internal: what does deterministic replay of the mined region do
when provenance, effect, position, contract, and risk barriers are disabled? On PR-outcome and
backlog-attention routing the mined three-read sequence *is* the admitted program, so an unguarded
replay executes the same calls and differs only in guards that never fired on in-distribution
held-out records (dispatch 30/30 in both families). A live run there would reproduce the compiled
arm by construction and is not spent on. On issue-type routing the compiler refused the three-read
candidate because `issue_get_comments.limit=100` has no witness (`ungroundable_slot`) and emitted
the two-read prefix; a recurrence-only replay of the three-read sequence therefore differs from the
compiled arm, and its price is measurable. The retained mechanism-removal table
(`paper/iclr/tables/mechanism_removal.tex`) already prices the other barriers on retained
hazards; this protocol adds the one live measurement that table cannot supply.

## Arm

`recurrence_only_three_read`: a `ManualPreModelPlan` with three `CallStep`s —
`issue_get_record(issue_number = z.issue_number)`, `issue_get_labels(issue_number = z.issue_number)`,
`issue_get_comments(issue_number = z.issue_number, limit = Const(100))` — a permissive `Verifier()`
(no clauses; asserted inert on the unperturbed run), no calibrated gate, and manifest pins identical
to the retained artifact `cand-01-1ebb8b2849c7`. The plan runs pre-model on the deterministic
snapshot tools and hands the evidence object to one model request that produces the answer.

## Cohort and comparators

The sealed 30-record held-out selection of `paper/results/github_natural_replication/results.json`
(`selection.test`), unchanged. Comparators are the retained baseline, compiled, and macro arms on the
same 30 records, so every contrast is paired. Model settings, `max_turns=8`, and the 120 s timeout
match the retained study; one retry per timed-out episode, both attempts retained.

## Hypotheses (either outcome is reported)

- H-B1a: the unguarded three-read replay preserves exact contracts (`factuality_exact`) on 30/30
  records.
- H-B1b: it uses one provider request per record, one fewer than the compiled two-read artifact.
- H-B1c: at least one of the 30 answers loses excerpt or URL exactness the way issue 6602 did in
  the natural-order study.

## Endpoints

Primary: exact contract passes and the discordant cells against the compiled arm (exact McNemar).
Secondary: requests, interfaces, tokens, wall latency, estimated cost (means, medians, paired
differences with 10,000-sample bootstrap intervals, seed 20260802); per-field exactness; a
continuation audit of every excerpt against the pinned source comment.

## Decision rule (fixed in advance)

| Observed | Reading |
|---|---|
| 30/30 exact, one request per record | On this cohort the provenance refusal cost one request per record without a measured quality benefit; the guard's value is the refusal of an unwitnessed argument plus the retained 6602 counterexample (18-record cohort), not a held-out failure. Reported in those words. |
| ≥ 1 failure | The failing record(s) and mechanism are the direct price of the missing guard; reported in full ahead of every other reading. |
| Provider failure that a retry does not cure | Reported under intention-to-treat as a failure of the arm, never dropped. |

No arm is re-run to change a count; the cohort, plan, and settings are fixed by this document.

## Spend and outputs

`--approved-spend-usd 0.25` (expected ≈ $0.02). Driver `paper/scripts/recurrence_only_ablation.py`
writes `paper/results/recurrence_only_ablation/{preflight.json, results.json}`; the
generated table `paper/iclr/tables/recurrence_only.tex` (arm × metric over 30 records) and a
validator check pin the numbers. Paper location: Appendix G after the mechanism-removal table; one
sentence each in §6 and §7.

## Claim boundary

The result concerns one family, one cohort, one provider, and the in-distribution held-out records.
It does not measure behaviour under shift (that is the drift-robustness protocol) and does not
establish that recurrence-only replay is safe or unsafe in general.

## Execution note (2026-09-24, written before any provider call)

The driver named above now exists (`paper/scripts/recurrence_only_ablation.py`, sub-commands
`preflight` and `run`). One deviation from the arm as worded: the guarded manual runner
(`ManualPreModelRunner`) rejects a plan whose `Verifier()` has no clauses (it requires one
output clause per live-out and a call count) and requires the `batchable` capability the
retained issue catalog does not declare. A clause-free verifier is therefore not executable
through that runner. The arm replays the three reads directly on the pinned snapshot tools
and hands the evidence to one provider request with no tools exposed, which is the
barrier-free replay this protocol defines. Guard, verifier, gate, and position are all absent
rather than present-but-permissive; the preflight records this. Cohort, comparators,
hypotheses, endpoints, decision rule, spend, and outputs are unchanged. The provider-free
preflight (`paper/results/recurrence_only_ablation/preflight.json`) executes the replay on
all 30 sealed records and records zero provider calls.

## Observed results (executed 2026-09-24T12:17Z; `paper/results/recurrence_only_ablation/results.json`)

30/30 episodes completed, no retries, estimated spend $0.011 (`gpt-5.6-luna`, SDK 0.19.2). The
recurrence-only three-read replay passed `factuality_exact` on 30/30 records with exactly one
provider request per record (H-B1a and H-B1b hold; H-B1c does not: every excerpt was located
verbatim in its source comment, title, or body). Paired against the retained arms on the same
30 records: McNemar $p = 1$ against baseline, compiled, and macro (no discordant cells);
per-record means 1.00 requests / 1,167 tokens / 2.67 s / 0.038 ¢ against 4.00 / 4,259 / 6.16 s /
0.087 ¢ (baseline), 2.00 / 2,576 / 2.97 s / 0.059 ¢ (compiled), and 2.00 / 1,781 / 3.25 s /
0.055 ¢ (macro). Decision-rule row 1 applies and is reported in its words: on this cohort the
provenance refusal cost one request per record without a measured quality benefit; the guard's
value is the refusal of an unwitnessed argument plus the retained 6602 counterexample, not a
held-out failure. Table: `paper/iclr/tables/recurrence_only.tex`; paper: Appendix G and §7.
