# Second-model re-discovery protocol (design A, three primary families)

**Status: PRE-REGISTERED on 2026-09-24; EXECUTED the same day** (observed results at the end). Before execution no provider call had been made under this
document. It fixes the model, cohorts, pipeline, endpoints, and decision rule before any spend.

## Why

`second-model-replication-protocol.md` (design B) transferred the `gpt-5.6-luna` artifacts to
`gpt-6-luna` on the same cohorts and produced one compiled-only miss on an artifact that had never
been calibrated on the second model. Design A asks the question that transfer cannot: does the
whole compile-or-retire pipeline, run end to end on the second model's own traces, admit an
artifact, and does that artifact preserve exact contracts on the sealed held-out records?

## Model and settings

`gpt-6-luna` throughout (discovery, calibration labels, and every held-out arm), with the settings
of every retained study: `reasoning.effort=low`, `verbosity=low`, `parallel_tool_calls=False`,
`store=False`, `max_turns=8`, 120 s per-episode timeout, list prices pinned in `demos/live_runtime.py`.

## Design A: same records, new traces

For each family the sealed discovery records (132) and held-out records (30) of the retained
`gpt-5.6-luna` study are reused unchanged, so selection depends on no provider outcome. Discovery
runs live on `gpt-6-luna` over the 132 records with the discovery prompt of the retained study;
the compiler mines, synthesizes, challenges, and calibrates on those traces with the retained
configuration (16 train / 8 dev / 92 calibration groups, α = 0.05, δ = 0.10, |Λ| = 11, seed as
retained); the three held-out arms then run on `gpt-6-luna` in the retained order. Nothing is
carried over from the `gpt-5.6-luna` traces.

| Family | Harness | Cohort source | Arms |
|---|---|---|---|
| Issue-type routing | `paper/scripts/second_model_replication.py rediscover` | `github_natural_replication/results.json` (`selection.discovery_issue_numbers`, `selection.test`) | `baseline`, `compiled`, `macro`, retained Latin order |
| PR-outcome audit | `github_workflow_family_study.py --model gpt-6-luna --sealed-selection pr_outcome/final/results.json --run-tag gpt6_luna_rediscovery` (no discovery checkpoint) | sealed selection | `baseline`, `compiled`, `manual_pre_model` |
| Backlog-attention routing | same with `backlog_attention/final/results.json` | sealed selection | same |

One retry per timed-out episode in the held-out arms; both attempts retained. Discovery failures
are retained in the checkpoint and reduce the eligible pool, exactly as in the retained studies.
No arm is re-run to change a count.

## Hypotheses (either outcome is reported)

- H-A1 (admission): each family reaches 116 exact discovery traces on `gpt-6-luna` and the compiler
  admits an artifact with 92 zero-violation calibration groups (U = 0.0498).
- H-A2 (same program): the admitted program equals the retained one (two-read prefix on issue-type,
  three-read program on the two deeper families).
- H-A3 (preservation): the compiled arm passes exact contracts on every held-out record the
  same-model baseline passes (zero compiled-only failures).

## Decision rule (fixed in advance)

| Observed | Reading |
|---|---|
| H-A1 fails (fewer than 116 exact traces, or calibration retires) | A principled refusal on the second model: reported as such with the stage and counts; no held-out arm is run for that family and no artifact is claimed. |
| H-A1 holds, H-A2 fails | The compiler found a different admissible program on the second model; the program and its provenance are reported; H-A3 is still evaluated. |
| H-A1 and H-A3 hold | A second-model artifact certified on its own traces: reported as per-candidate or compiler-wide according to the number of candidates that reached calibration, exactly as for the primary families. |
| Any compiled-only failure | The record and mechanism are reported ahead of every other reading. |

## Endpoints

Discovery exact-trace count; candidates reaching calibration (m); per-threshold gate table; held-out
exact contracts per arm with discordant cells (exact McNemar); requests, tokens, latency, and cost
reductions against the same-model baseline (paired, 10,000-sample bootstrap, seed 20260802).

## Spend and outputs

`--approved-spend-usd 1.00` per family (expected ≈ $0.05 each). Outputs:
`paper/results/second_model_replication/issue_type_rediscovery/{preflight,discovery_checkpoint,results}.json`,
`paper/results/github_workflow_families/{pr_outcome,backlog_attention}/gpt6_luna_rediscovery/`, the
summary and generated table alongside design B's (`second_model_replication/summary.json`,
`paper/iclr/tables/second_model.tex`, gaining a design-A block). Paper: the Appendix G second-model
paragraph, one clause in §5.1 and §7.

## Claim boundary

Same records and same snapshot; a second model's own traces through the unchanged pipeline. It does
not measure a second provider or a second repository snapshot, and the certificate, if any, is
conditional on i.i.d. calibration groups exactly as the primary ones are.

## Observed results (executed 2026-09-24T12:57–13:15Z)

Issue-type routing: 128/132 exact discovery traces, no failures; the compiler admitted
`cand-01-1ebb8b2849c7` (identical program, one candidate at calibration, 92/0, U = 0.0498);
30/30 dispatch; exact contracts 30/30/30; reductions 50.0/38.9/47.3/32.8 (requests/tokens/latency/cost).
H-A1, H-A2, H-A3 hold. PR-outcome audit: 132/132 exact discovery traces; `cand-00-a1de3856bb6c`
admitted (identical program, two candidates at calibration with the two-read sibling dominated, as
in the primary run); 30/30 dispatch; 30/30/30; reductions 75.0/80.7/70.8/76.0. H-A1–H-A3 hold.
Backlog-attention routing: 113/132 exact discovery traces (19 with `comment_grounded` false; 22
traces used only two reads), below the 116 the 16/8/92 split needs, so the harness stopped before
the held-out arms (`gpt6_luna_rediscovery/failure.json`): decision-rule row 1, a principled refusal
on the second model; no artifact is claimed. Spend: $0.078, $0.05, $0.042. The transfer miss on
record 6532 did not recur under re-discovery. Table: design-A block of
`paper/iclr/tables/second_model.tex`; paper: Appendix G, §5.1, §7.
