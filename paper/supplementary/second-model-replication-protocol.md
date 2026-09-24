# Second-model replication protocol (three primary families)

**Status: PRE-REGISTERED on 2026-09-24. Not run.** No provider call has been made under this
document. It fixes the model, design, cohorts, arms, endpoints, and decision rule before any
spend. Provider-free preflights are committed beside it; they record zero provider calls.

## Why

Every live number in the paper comes from one provider and one model, `gpt-5.6-luna`. The
paper says so (§7). A reviewer can still ask whether the compiled artifacts and the exact
contracts they preserve are a property of that model's calling discipline. This protocol
answers the narrow version of that question that can be answered without new records: on the
same sealed held-out cohorts, does the guarded pipeline transfer to a second model family?

## Model

`gpt-6-luna`, the efficiency tier of the GPT-6 family (a different generation from
`gpt-5.6-luna`; docs: `developers.openai.com/api/docs/models/gpt-6-luna`). Same settings as
every retained study: `reasoning.effort=low`, `verbosity=low`, `parallel_tool_calls=False`,
`store=False`, `max_turns=8`, 120 s per-episode timeout. List prices retrieved 2026-09-24 from
`developers.openai.com/api/docs/pricing` and pinned in `demos/live_runtime.py`
(`MODEL_PRICES["gpt-6-luna"]`: input 0.10, cached input 0.01, cache write 0.125, output 0.50 USD
per million tokens). If `gpt-6-luna` is unavailable to the executing key at run time, the
fallback is `gpt-5.6-terra` (same generation as the retained model, different tier); the
fallback is a weaker answer to the question and must be reported as such.

## Design B: transfer, not re-discovery

The retained `gpt-5.6-luna` studies supply, unchanged, for each family:

- the sealed 132 discovery records and their recorded tool sequences and arguments
  (`discovery_checkpoint.json`), and
- the sealed 30 held-out records and their arm order.

The artifact is recompiled provider-free from those traces under a manifest that pins the
second model, because the manifest pin is a hard guard and the runtime resolves artifacts by
compatibility key. Compilation is deterministic from the traces, so the program, splits, and
gate must reproduce; the issue-type preflight asserts this against the retained
`cand-01-1ebb8b2849c7` before recompiling for the second model, and the family harness reuses
`reconstruct_discovery` exactly as the Headroom ablation did. The held-out arms then run live
on the second model.

What this does *not* do: it does not re-run discovery on the second model, so it does not test
whether the second model's own traces would have been compiled. That is design A, deferred; it
costs a fresh 132-record discovery per family and answers a different question.

## Arms and cohorts

| Family | Harness | Discovery checkpoint | Held-out cohort | Arms |
|---|---|---|---|---|
| Issue-type routing | `paper/scripts/second_model_replication.py` | `github_natural_replication/discovery_checkpoint.json` | `github_natural_replication/results.json` `selection.test` (30) | `baseline`, `compiled`, `macro` in the retained Latin order |
| PR-outcome audit | `github_workflow_family_study.py --sealed-selection … --discovery-checkpoint … --model gpt-6-luna --run-tag gpt6_luna` | `pr_outcome/pilot_v1/discovery_checkpoint.json` | `pr_outcome/final/results.json` (30) | `baseline`, `compiled`, `manual_pre_model`, six-permutation order |
| Backlog-attention routing | same | `backlog_attention/final/discovery_checkpoint.json` | `backlog_attention/final/results.json` (30) | same |

One retry per timed-out episode; both attempts retained. No arm is re-run to change a count.

## Hypotheses (either outcome is reported)

- H-M1 (preservation): the compiled arm passes exact contracts on every record the baseline
  passes, per family (zero compiled-only failures).
- H-M2 (structure): per-record provider requests are identical to the `gpt-5.6-luna` run in
  every arm (2/1/1 for the two deeper families; 4/2/2 for issue-type), because the removed
  turns are a property of the artifact, not the model.
- H-M3 (dispatch): the compiled artifact dispatches on 30/30 held-out records per family under
  the second-model manifest pin; any abstention is reported with its guard clause.

## Endpoints

Primary: exact contract passes per arm and the discordant cells against the same-model
baseline (exact McNemar). Secondary: requests, tokens, latency, estimated cost as reductions
against the same-model baseline (paired, 10,000-sample bootstrap, seed 20260802); dispatch and
fallback reasons; a side-by-side of reductions on the two models.

## Decision rule (fixed in advance)

| Observed | Reading |
|---|---|
| H-M1 holds in all three families | The pipeline transfers on these cohorts: reported as preservation on a second model family, same-cohort, not as generality. |
| A compiled-only failure in any family | The record and mechanism are reported ahead of every other reading; the paper's provider-breadth sentence is not softened. |
| Dispatch below 30/30 in any family | The clause is reported; a manifest or hull miss under the new pin is a finding about the guards, not about the model. |
| Baseline failures on the second model | Reported as such; they do not count for or against the compiler, whose gate certifies end-to-end compliance under substitution (§2). |

## Spend and outputs

`--approved-spend-usd 1.00` per family (expected ≈ $0.02–0.05 each at the pinned rates).
Outputs: `paper/results/second_model_replication/issue_type/{preflight,results}.json` and
`registry/`; `paper/results/github_workflow_families/{pr_outcome,backlog_attention}/gpt6_luna/`;
`paper/results/second_model_replication/summary.json`; the generated table
`paper/iclr/tables/second_model.tex`. Paper location: one paragraph and the table in Appendix D
or G, one sentence each in §5.1 and §7; the abstract is unchanged unless all three families
transfer, in which case "one provider/model family" in §7 is replaced by the measured statement.

## Claim boundary

Same records, same discovery traces, same splits; a second model family on the same cohorts.
It does not measure a second provider, a second repository snapshot, or re-discovery on the
second model, and it does not establish generality across models.
