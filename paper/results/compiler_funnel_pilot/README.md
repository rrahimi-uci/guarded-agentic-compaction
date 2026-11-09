# Compiler-funnel live pilot on fresh issues (sealed 2026-11-08, run the same day)

Protocol: `paper/supplementary/compiler-funnel-live-pilot-protocol.md` (sealed before any provider
call; its SHA-256 is recorded in `preflight.json` and `results.json`). Script:
`paper/scripts/compiler_funnel_live_pilot.py`. Provider-backed, real public records, gpt-5.6-luna.
Spend: 0.2306 USD against a 5.00 USD cap (`ledger.json`).

## Question

The same-IR funnel (`../compiler_funnel/`) found one place where GAC's grounding changed a compiler
decision: on the retained issue-type traces GAC refused the three-read candidate whose
`issue_get_comments.limit` had no witness, while a recurrence-only policy admitted it with
`limit = 100`. Does that divergence recur on fresh, post-cutoff issues, and what does it cost live?

## Cohort and split (provider-free, `preflight.json`)

| | n |
|---|---|
| post-cutoff `huggingface/datasets` issues in the time-forward snapshot (created after 2025-06-13, fetched 2026-10-07) | 277 |
| with at least one comment | 197 |
| excluded (same-record-space uses in retained files: 7693, 7694, 8029, 8590) | 4 |
| pool | 193 |
| discovery (stable SHA-256 rank, seed 20261108) | 128 |
| test | 65 |

Pool labels: 172 `other`, 21 `enhancement`; 77 issues have three or more comments; numbers 7617
to 8763.

## Discovery (live, `discovery_checkpoint.json`)

128/128 episodes completed, 127 exact on the source-grounded oracle and compiler-eligible (issue
8719 missed the excerpt field). Every trace used the same three reads in the same order; 124 asked
for `limit = 100`, 4 for `limit = 1` (issues 7699, 7760, 8164, 8241).

## Compile (provider-free, `compile.json`)

**GAC admitted the three-read program on the fresh traces.** The 16 train groups all carried
`limit = 100`, so the synthesizer bound `limit = Const(100)` with full training agreement; the
four `limit = 1` traces fell into dev (1) and calibration (3), where the replay recorded them as
`RecordingMiss` (unproductive, not violations). Gate: 92 calibration groups, 0 violations, bound
0.0498 at eta 0.50, coverage 1.0. The two-read prefix was emitted and then dominated by the longer
region. Guard: fresh snapshot digest, `|calls| = 3`, READ_LOCAL only.

**The funnel's divergence did not recur.** All four policies (full, support-only, recurrence-only,
stats-only) admit the same three-read program; the recurrence-only policy's majority fallback was
never invoked. The retained refusal therefore hinged on one `limit = 1` trace landing in the 16-trace
train split of the retained study (15/16 agreement), not on a stable property of the workload.

## Test (live, 65 paired issues, `test_checkpoint.json`, `results.json`)

| Arm | Exact | Requests | Tokens | Latency (s) | Cost (cents) |
|---|---|---|---|---|---|
| Compiled 3-read program (GAC, fresh compile) | 65/65 | 1.00 | 1,609 | 1.78 | 0.052 |
| Recurrence-only three-read replay | 63/65 | 1.00 | 1,308 | 1.85 | 0.043 |
| Unchanged agent | 64/65 | 4.00 | 4,618 | 4.90 | 0.087 |

All 195 episodes completed with no retry. The compiled arm dispatched on all 65 issues (no guard,
gate or verifier abstention) and used one provider request per issue, like the replay arm.

Paired exact contract (McNemar, two-sided): compiled vs recurrence-only 2 discordant pairs, both in
GAC's favour, p = 0.50; compiled vs baseline 1 discordant, p = 1.0; recurrence-only vs baseline 2
vs 1, p = 1.0. Versus the unchanged agent, both compiled arms remove 75% of requests; the compiled
arm cuts tokens 65% and cost 41%, the replay arm 72% and 51%.

**Mechanism of every miss.** All three misses (baseline 7624; replay 7990 and 8048) are the same
kind: the model returned an `evidence_excerpt` that is a paraphrase or a corrupted quotation of the
source rather than a verbatim span, with every other field exact. Both compiled arms executed the
same three reads with identical evidence; the two arms differ in how the evidence reaches the model
(tool results in the SDK transcript for GAC, a JSON block in the user turn for the replay). No miss
is a wrong or missing read, so none is a replay-visible violation that a guard or verifier would
have caught, and the 0 vs 2 difference is within sampling noise at this size.

## Reading

1. On fresh issues the compile-time divergence is gone: GAC and the recurrence-only policy emit the
   same program. GAC's refusal in the retained study was a split-dependent outcome of one divergent
   training trace, which is exactly what grounding is meant to do with an unwitnessed literal, but it
   is not a property of the workload.
2. Live, GAC's guarded three-read program met the contract on 65/65 fresh issues with one request
   per issue; the unguarded replay of the same program met it on 63/65; the unchanged agent on 64/65
   with four requests. No arm produced a wrong read. This extends the 30-record ablation (Table 33)
   to 65 fresh records with the same qualitative result: the guards cost nothing measurable here and
   prevented nothing measurable here.
3. Nothing here speaks to PR-outcome or backlog (identical arms there), to external compilers, or to
   effect sizes (65 pairs, pilot power).

## Files

- `preflight.json`: pool accounting, split, Latin order, expected spend (no provider call).
- `discovery_checkpoint.json`: 128 discovery episodes (public rows).
- `compile.json`: GAC artifact, candidates, gate, and the four funnel policies with the divergence list.
- `test_checkpoint.json`: 195 test episodes by stage.
- `results.json`: aggregate, paired comparisons, misses, continuation audit, ledger.
- `ledger.json`: spend by phase.
- `../../iclr/tables/compiler_funnel_pilot.tex`: regenerated by `table`; input by Appendix N of the revised paper since the 2026-11-09 rebuttal pass.
