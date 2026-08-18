# Headroom context-compression ablation protocol

**Status: executed on 2026-08-18.** This protocol adds an orthogonal
context-compression comparison to the two GitHub workflow-family evaluations. It
does not change the GRC compiler, admission gate, artifacts, or fallback policy.

## Conditions

Each family uses the existing unchanged baseline and guarded pre-model condition,
then adds two Headroom conditions:

| Condition | Model-visible change |
|---|---|
| `baseline` | unchanged provider-visible tool results |
| `headroom_only` | Headroom compresses each JSON tool result before the next provider request |
| `compiled` | GRC supplies the approved pre-model evidence object |
| `compiled_headroom` | Headroom compresses the GRC evidence object before the remaining provider request |
| `manual_pre_model` | existing human-reviewed pre-model reference, retained to preserve the original comparison |

The fifth condition is retained because it anchors GAC's compiler-discovery claim;
it is not a Headroom arm. The execution order uses forward and reversed Latin
rotations over the five conditions. The driver records Headroom's applied/fallback
counts, token accounting, and transforms alongside native provider traces.

## Isolation and safety boundary

The optional dependency is pinned to `headroom-ai==0.5.18`. The adapter calls the
public `headroom.compress(messages, model=...)` API only on one source-grounded
JSON tool result or pre-model evidence object at a time. It does not enable
Headroom's proxy, cross-session memory, learning, output shaping, or retrieval
tool. An absent/wrong package version, malformed output, changed message shape,
invalid JSON, or changed required `record_number`/`source_revision` falls back to
the original payload and is retained in the condition audit.

The paired exact source-grounded contracts remain the quality endpoint. Therefore
the protocol can measure an accuracy regression from lossy compression rather
than treating Headroom's self-reported benchmark accuracy as evidence here.

## Cohorts and evidence state

The source snapshot has no unused balanced 132-discovery/30-test cohort remaining
for either workflow family. The two committed preflights therefore reuse the
already provider-outcome-free, held-out cohorts and their sealed discovery traces:

- PR outcome: 132 discovery and 30 held-out records, all from the prior final
  study; discovery checkpoint `pilot_v1/discovery_checkpoint.json` matches the
  final selection exactly.
- Backlog attention: 132 discovery and 30 held-out records, with the final
  study's discovery checkpoint.

This is a new paired comparator on a fixed held-out cohort, not a retraining
study or a new independent sample. The committed preflights each record zero
provider calls; the corresponding provider-backed results record the live
condition-level traces.

## Observed results

Both 30-record family evaluations completed all five arms with zero failures and
100% exact-contract success. Headroom attempted every eligible payload (90 tool
payloads in `headroom_only` and 30 pre-model evidence objects in
`compiled_headroom` per family), but applied no transformations, reported no
fallbacks, and saved zero tokens. It therefore had no measured compression effect
at this model-visible JSON boundary:

| Family | Headroom only vs. baseline | GAC + Headroom vs. GAC |
|---|---:|---:|
| PR outcome | -0.15% total tokens (4.1 tokens/record; ordinary generation variation) | +0.28% (1.5 tokens/record) |
| Backlog attention | +0.30% total tokens (8.6 tokens/record) | +0.25% (1.3 tokens/record) |

All four paired quality contrasts are 30/30 versus 30/30 with McNemar exact
`p = 1.0`. These near-zero resource differences must not be attributed to
compression because the Headroom audit records zero applied payloads. In contrast,
GAC remains the active intervention: its direct paired comparisons reduce total
tokens by 80.9% (PR outcome) and 81.6% (backlog attention), while retaining 30/30
exact-contract success. The result is limited to the fixed, reused held-out
cohorts and does not establish Headroom behavior on longer or differently shaped
contexts.

## Reproduction and live execution

Install the optional dependency and regenerate the provider-free preflight:

```bash
.venv/bin/pip install -e '.[live,headroom]'

.venv/bin/python paper/scripts/github_workflow_family_study.py \
  --family pr_outcome --run-tag headroom_ablation --headroom-ablation \
  --discovery-checkpoint paper/results/github_workflow_families/pr_outcome/pilot_v1/discovery_checkpoint.json \
  --sealed-selection paper/results/github_workflow_families/pr_outcome/final/results.json \
  --preflight-only

.venv/bin/python paper/scripts/github_workflow_family_study.py \
  --family backlog_attention --run-tag headroom_ablation --headroom-ablation \
  --discovery-checkpoint paper/results/github_workflow_families/backlog_attention/final/discovery_checkpoint.json \
  --sealed-selection paper/results/github_workflow_families/backlog_attention/final/results.json \
  --preflight-only
```

Live runs require both `OPENAI_API_KEY` and an explicit positive
`--approved-spend-usd` value. They must reuse the matching discovery checkpoint,
retain all five arms, preserve per-record schedule order, and write a fresh
`headroom_ablation` result directory. Do not overwrite the original final results.
The checked-in run used both matching discovery checkpoints, the fixed selections,
and an approved spend ceiling of USD 1.00 per family.
