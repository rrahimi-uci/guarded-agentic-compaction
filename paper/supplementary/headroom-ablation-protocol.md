# Headroom context-compression ablation protocol

**Status: prepared, provider calls not run.** This protocol adds an orthogonal
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
study, a new independent sample, or a paper result. The committed preflights each
record zero provider calls.

## Reproduction and live execution

Install the optional dependency and regenerate the provider-free preflight:

```bash
.venv/bin/pip install -e '.[live,headroom]'

.venv/bin/python paper/scripts/github_workflow_family_study.py \
  --family pr_outcome --run-tag headroom_ablation --headroom-ablation \
  --sealed-selection paper/results/github_workflow_families/pr_outcome/final/results.json \
  --preflight-only

.venv/bin/python paper/scripts/github_workflow_family_study.py \
  --family backlog_attention --run-tag headroom_ablation --headroom-ablation \
  --sealed-selection paper/results/github_workflow_families/backlog_attention/final/results.json \
  --preflight-only
```

Live runs require both `OPENAI_API_KEY` and an explicit positive
`--approved-spend-usd` value. They must reuse the matching discovery checkpoint,
retain all five arms, preserve per-record schedule order, and write a fresh
`headroom_ablation` result directory. Do not overwrite the original final results.
No live command has been authorized or run for this protocol.
