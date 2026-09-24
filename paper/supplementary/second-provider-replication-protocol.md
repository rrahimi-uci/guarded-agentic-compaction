# Second-provider replication protocol (Anthropic, three primary families)

**Status: PRE-REGISTERED on 2026-09-24. Not run.** No provider call has been made under this
document beyond the adapter smoke tests it names. It fixes the provider, model, design, cohorts,
arms, endpoints, decision rule, and spend before any study call.

## Why

Every live number in the paper comes from one provider (OpenAI); the second-model studies changed
the model generation but not the provider, the SDK transport, or the tool-calling protocol. This
protocol runs the unchanged compile-or-retire pipeline end to end on a second provider's own
traces, using the same sealed records, so that "one provider" becomes a measured comparison rather
than a caveat.

## Provider, model, and transport

Anthropic, `claude-sonnet-5` (the provider's mainstream tier, chosen by the author), called through the official `anthropic` Python SDK from an Agents-SDK
`Model` adapter (`guarded_agentic_compaction.capture.anthropic_model.AnthropicModel`); the model
string is recorded as `anthropic/claude-sonnet-5` in every manifest and result. Settings: adaptive
thinking (the model's default; the `thinking` parameter is omitted), `output_config.effort = low`
(the counterpart of the OpenAI runs' reasoning effort `low`), `disable_parallel_tool_use = true`
(the counterpart of `parallel_tool_calls=False`), structured answers through
`output_config.format` with the same Pydantic schemas, `max_turns = 8`, 120 s per-episode timeout.
No prompt, tool, grader, split rule, or compiler setting changes. List prices (retrieved
2026-09-24): input $2.00, cached-read input $0.20, cache write $2.50, output $10.00 per million
tokens; pinned in `demos/live_runtime.py`. The paper's OpenAI models are efficiency-tier, so cost
columns are reported but the cross-provider cost comparison is not a claim.

## Design A: same records, the second provider's own traces

Identical to `second-model-rediscovery-protocol.md` with the provider changed. For each family
the sealed 132 discovery and 30 held-out records of the retained study are reused unchanged;
discovery runs live on the second provider with the retained discovery prompt; the compiler mines,
synthesizes, challenges, and calibrates on those traces with the retained configuration
(16/8/92, α = 0.05, δ = 0.10, |Λ| = 11, retained seeds); the three held-out arms run on the
second provider in the retained order.

| Family | Harness | Arms |
|---|---|---|
| Issue-type routing | `paper/scripts/second_model_replication.py rediscover --model anthropic/claude-sonnet-5` | `baseline`, `compiled`, `macro`, retained Latin order |
| PR-outcome audit | `github_workflow_family_study.py --model anthropic/claude-sonnet-5 --sealed-selection pr_outcome/final/results.json --run-tag anthropic_sonnet5_rediscovery` | `baseline`, `compiled`, `manual_pre_model` |
| Backlog-attention routing | same with `backlog_attention/final/results.json` | same |

One retry per timed-out episode in the held-out arms; both attempts retained. Discovery failures
are retained in the checkpoint and reduce the eligible pool. No arm is re-run to change a count.

## Hypotheses (either outcome is reported)

- H-P1 (admission): each family reaches 116 exact discovery traces and the compiler admits an
  artifact with 92 zero-violation calibration groups (U = 0.0498).
- H-P2 (same program): the admitted program equals the retained one.
- H-P3 (preservation): zero compiled-only exact-contract failures on the 30 held-out records.
- H-P4 (structure): provider requests per record in the compiled arm equal the retained run's
  (2 for issue-type, 1 for the two deeper families), because the removed turns are a property of
  the artifact, not the provider.

## Decision rule (fixed in advance)

| Observed | Reading |
|---|---|
| H-P1 fails | A principled refusal on the second provider, reported with the stage and counts; no held-out arm is run for that family and no artifact is claimed. |
| H-P1 holds, H-P2 fails | A different admissible program was found; program and provenance reported; H-P3 and H-P4 still evaluated. |
| H-P1, H-P3, H-P4 hold | A second-provider artifact certified on its own traces; certificate level per the number of candidates that reached calibration. |
| Any compiled-only failure | The record and mechanism are reported ahead of every other reading. |
| Adapter fault (transport error, malformed structured answer, refusal stop reason) | Counted as an episode failure of the arm in which it occurred under intention-to-treat and reported with its category; never dropped and never retried beyond the one timeout retry. |

## Endpoints

Discovery exact-trace count; candidates reaching calibration; the per-threshold gate table;
held-out exact contracts per arm with discordant cells (exact McNemar); requests, tokens, latency,
and cost reductions against the same-provider baseline (paired, 10,000-sample bootstrap, seed
20260802); dispatch and fallback reasons; a side-by-side of the three providers' structure
(requests per record per arm).

## Spend and outputs

Expected about $2–3 per family at the pinned prices (discovery dominates; the adapter smoke test
priced one baseline episode at $0.022 and one compiled episode at $0.012); ceiling
`--approved-spend-usd 6.00` per family. Outputs:
`paper/results/second_provider_replication/issue_type/{preflight,discovery_checkpoint,results}.json`
and `registry/`; `paper/results/github_workflow_families/{pr_outcome,backlog_attention}/anthropic_sonnet5_rediscovery/`;
`paper/results/second_provider_replication/summary.json`; the generated table
`paper/iclr/tables/second_provider.tex`. Paper: one paragraph and the table in Appendix G, one
clause in §5.1 and §7; the abstract is unchanged unless all three families admit and preserve.

## Claim boundary

Same records and same snapshot; a second provider's own traces through the unchanged pipeline.
It does not measure a second repository snapshot or a third provider, its cost column is not a
cross-provider price comparison, and any certificate remains conditional on i.i.d. calibration
groups exactly as the primary ones are.
