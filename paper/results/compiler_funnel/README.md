# Same-IR compiler funnel (P1-lite of `gac-expansion.md`)

Provider-free. The shipped compiler was run four times over every retained GitHub discovery cohort
with two switches: statistical admission on/off (alpha = 0.05 / 1.0) and grounding on/off (Algorithm 3
refuses an ungroundable slot / binds it to its modal training literal). Everything else is the
production code path of the retained studies, so splits, manifests and catalogs are identical. The
protocol was registered before any policy other than the shipped one ran
(`paper/supplementary/compiler-funnel-protocol.md`; SHA-256 in `results.json`). The full policy
reproduces the retained decision on all 13 cohorts (same artifact id, same tools, same rejection
stages). Runtime 4.8 s. Nothing was dispatched; spend $0.

## Result

| Cohort | Full (GAC) | Support-only | Recurrence-only | Stats-only | Divergence |
|---|---|---|---|---|---|
| Issue-type routing (132 runs) | 2-read admitted; 3-read refused at synthesis (`issue_get_comments.limit`: no witness) | same as full | 3-read admitted with `limit = Const(100)`; 2-read dominated | 3-read admitted (92/92 accepted, 0 violations, U = 0.0498); 2-read dominated | **yes**: the 3-read candidate |
| PR-outcome (132) | 3-read admitted; 2-read dominated | same | same | same | none |
| Backlog attention (132) | 3-read admitted; 2-read dominated | same | same | same | none |
| 10 multi-repository cohorts (132 each; frozen single candidate) | 3-read admitted | same | same | same | none |

Mining is shared by all four policies and blocks 16 windows per cohort as `non_prefix_runtime`
(the position barrier); no cohort has any other mining-level block, so the grounding switch could
only act at synthesis, and it acted exactly once.

**The one divergence, measured by replay.** The recurrence-only and stats-only policies emit the
issue-type three-read program with `limit = Const(100)` (the modal literal; 15 of 16 training
windows use 100). On the 92 calibration groups its recorded replay has **0 violations and 1
unproductive** sample: the one calibration run that used `limit = 1` is a recording miss (the
facade has no recorded result for `limit = 100`), which the compiler classifies as unproductive,
not as a violation. On the 16 development groups the challenge reports 3 unproductive perturbation
samples for every candidate, including the ones GAC admits. Under the grounding-off policies the
two-read program GAC ships is dominated by the three-read one, so a recurrence-based compiler would
replace GAC's admitted artifact rather than add to it.

## Reading

- **Statistical admission never changed a decision on these cohorts.** Support-only (alpha = 1)
  admits exactly what the full policy admits, everywhere. This is the compile-time counterpart of
  Appendix K's runtime finding (identical routing on 2,724 cases): with 92 clean calibration groups
  per candidate, the gate admits at full coverage and the support floor already decides. The
  alpha = 1 gate records a bound of 0.0507 instead of 0.0498 only because the accept-all threshold
  widens the grid from 11 to 12 points.
- **Grounding changed one decision in thirteen cohorts.** It refused the issue-type three-read
  candidate. The refusal's replay cost is one unproductive sample in 92 and its measured quality
  benefit on the calibration groups is zero violations prevented: on this cohort, the refusal cost
  one removed request per episode (3 → 2) without a replay-visible error avoided, which agrees with
  the live recurrence-only ablation (30/30 at one fewer request, Table 33). What the replay cannot
  see is the live effect of `limit = 100` on an issue whose recorded run used `limit = 1`: a
  different evidence set reaches the model, and whether the answer changes is not a replay question.
- **PR-outcome and backlog are nulls by construction.** The mined three-read window is GAC's
  admitted program and every slot is grounded, so no policy can differ on them. A live comparison of
  the four policies on PR-outcome would execute the same program in every compiled arm; the only
  family where a live run can separate them is issue-type.

## Implication for the next step

The live pilot sketched for days 3–5 should not be on PR-outcome. The funnel shows the compiled
arms coincide there; the measurable question is the issue-type divergence on fresh issues, where the
retained post-cutoff pool holds 277 issues (197 with a comment). A three-arm run (GAC's two-read
program, the recurrence-only three-read program, the unchanged agent) on that pool extends the
30-record ablation to a larger fresh cohort at an estimated 500–600 episodes. Its protocol is
drafted separately (`paper/supplementary/compiler-funnel-live-pilot-protocol.md`, not sealed; no
provider call is authorized by it).

## What this study cannot show

Live quality or cost of any policy; anything about external compilers (TraceCompiler has no runnable
artifact: `paper/results/tracecompiler_screen/REPORT.md`); anything beyond these GitHub families; the
effect of a recurrence-only *miner* (mining is shared, so windows the position barrier blocks stay
blocked for every policy).

## Files

`results.json` (per cohort and policy: artifacts, every candidate with stage, reason, gate, challenge
and calibration-replay counts, mining blocks, config; divergence set; reproduction check against the
retained decision), `paper/iclr/tables/compiler_funnel.tex` (generated; input by Appendix N of the revised paper since the 2026-11-09 rebuttal pass).
Reproduce with `python paper/scripts/compiler_funnel.py run` (needs the pinned snapshots on disk; the
multi-repository snapshots are read from `benchmarks/.cache/multirepo_e2e/<owner>__<repo>/`) and
`python -m pytest paper/scripts/test_compiler_funnel.py -q`.

## Follow-up: live pilot on fresh issues

`../compiler_funnel_pilot/` re-ran the issue-type cohort on 193 post-cutoff issues (sealed protocol,
0.23 USD). On fresh discovery traces GAC itself admitted the three-read program (`limit = Const(100)`,
16/16 training agreement) and all four policies agreed, so the one divergence above did not recur;
live, the guarded program met the contract on 65/65 held-out issues, the unguarded replay on 63/65,
the unchanged agent on 64/65.
