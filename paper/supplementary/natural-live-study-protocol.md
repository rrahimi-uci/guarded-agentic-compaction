# Natural-order, source-grounded live-study protocol

**Status:** expanded replication completed with real provider calls after its provider-free
preflight. The sealed design is
[`../results/github_natural_replication/preflight.json`](../results/github_natural_replication/preflight.json),
and retained outputs are in
[`../results/github_natural_replication/results.json`](../results/github_natural_replication/results.json).
The separate 18-pair natural-workflow study under `github_natural_live/` has real provider
results and is evaluated independently; the two protocols are not pooled.

This protocol is the direct implementation response to the two largest validity defects
in the archived GitHub study:

1. the archived prompt orders the three calls that the compiler later rediscovers; and
2. its summary oracle checks only non-emptiness and length, so fluent fabrication passes.

The archived `prescribed-v1` mode remains unchanged for exact reproduction. The new
`natural-extractive-v2` mode was sealed prospectively, then executed in a separate result
directory so its evidence cannot be pooled silently with the earlier study.

## Registered task

The agent receives a public GitHub issue number and the same three read-only tools, but
the prompt says only to use the available tools as needed. It does **not** name an order.
The answer is a typed triage record with:

- exact issue number, title, state, and total comment count;
- category derived from the official labels and its supporting label; and
- a 20--240 character verbatim evidence excerpt from the returned title, body, or first
  three comments.

The task succeeds only when every field passes. The learned conditions' tool contract
requires exactly one safe, issue-grounded call to each necessary read tool but accepts any
order and any integer comment-body limit. The tool returns the exact total independently of
that limit, and the source oracle verifies that the chosen excerpt was actually available.
Consequently, a stable sequence is observable evidence for compilation rather than a
sequence planted in the prompt.

The protocol also includes the strongest simple systems baseline omitted from the
archived live study: a hand-written `issue_get_bundle` composite tool that returns the
same record, labels, and comments in one deterministic read. It is evaluated on the same
held-out records and exact oracle. This separates the value of learned trace compilation
from the value of exposing an obvious application-authored macro.

The exact-source oracle is intentionally narrower than unconstrained abstractive
summarization. It measures factual record construction, not prose quality. Its advantage
is that every accepted factual field can be recomputed without an LLM judge: a fabricated
excerpt, altered title, wrong state, or wrong comment count fails deterministically.

## Sealed design

The provider-free preflight resolved the following design on the checksum-pinned
`helmo/github-issues` snapshot at revision
`e344be7b84d199661a9956036991e1fc25715a47`:

| Partition or condition | Count |
|---|---:|
| Discovery executions | 132 |
| Compiler train / development / calibration | 16 / 8 / 92 |
| Held-out primary pairs | 30 (10 bug, 10 enhancement, 10 question) |
| Repeated pairs for determinism | 10 |
| Selected real records | 162 |
| Discovery--test overlap | 0 |
| Missing oracle source fields | 0 |
| Conditions | baseline agent / learned compiled agent / hand-written macro |
| Planned condition order | all six three-condition orders, five records each |

Condition order is hash-ranked before execution and assigned as a balanced six-permutation
Latin design. Every ordering of baseline, compiled, and macro receives five primary
records. The runner executes each position in condition-specific batches. This does not
eliminate temporal drift, but it removes the perfect baseline-early/compiled-late
confound in the archived run and distributes each condition across early, middle, and
late positions. Assignments and the executed batch schedule are serialized with results.

## Provider-free verification

Run from the repository root:

```bash
.venv/bin/python paper/scripts/github_live_study.py \
  --task-design natural-extractive-v2 \
  --evaluation-order counterbalanced \
  --include-macro \
  --preflight-only \
  --discovery-cases 132 \
  --train-cases 16 --dev-cases 8 --calibration-cases 92 \
  --test-per-class 10 --repeat-cases 10 \
  --seed 20260802
```

This command downloads or verifies the pinned public snapshot, seals the split, validates
oracle feasibility, writes `preflight.json`, and performs zero OpenAI calls. It does not
require `OPENAI_API_KEY`.

The executable regression tests separately prove both sides of the claim:

```bash
.venv/bin/python -m pytest paper/scripts/test_oracle_weakness.py -q
```

- `prescribed-v1` still accepts a fabricated, length-conforming summary, preserving an
  executable record of the published limitation;
- `natural-extractive-v2` accepts reordered complete reads but rejects fabricated
  excerpts and incorrect exact fields.

## Paid execution and retained result

After reviewing the sealed selection, the following paid command was executed:

```bash
.venv/bin/python paper/scripts/github_live_study.py \
  --task-design natural-extractive-v2 \
  --evaluation-order counterbalanced \
  --include-macro \
  --discovery-cases 132 \
  --train-cases 16 --dev-cases 8 --calibration-cases 92 \
  --test-per-class 10 --repeat-cases 10 \
  --seed 20260802
```

The run used `OPENAI_API_KEY` and `HF_TOKEN` from `.env`; only boolean usage flags were
serialized. It retained 132 discovery outputs, 30 primary and ten repeated outputs per
condition, 848 provider responses, no infrastructure failure, and an estimated total cost
of $0.19129. The paid discovery checkpoint was written before compilation and is bound by
digest from the final result.

Every discovery trace chose record, labels, then comments; 130/132 passed exact factuality.
The compiler rejected the full three-read candidate because the natural comment limit had
no consistent grounded expression. It emitted the safe two-read prefix instead. Across 30
primary cases, baseline, partial compiler, and macro each passed 30/30 exact factual and
full task contracts. Relative to baseline, the partial compiler reduced requests 50.0%,
tokens 39.5%, wall latency 51.7%, and estimated cost 32.0%. The macro reduced requests
50.0%, tokens 58.2%, wall latency 47.2%, cost 37.5%, and tool calls 66.7%. Thus the macro
beats the compiler on tools, tokens, and cost; the compiler has lower observed mean latency,
but the paired interval against the macro crosses zero.

The online run graded literal comment limits against an undocumented value of three. A
provider-free semantic revision accepts any integer limit allowed by the registered “as
needed” task, preserves all 212 prior quality objects under `online_quality`, and changes
no provider output, timing, token, or cost record. Reproduce it with:

```bash
.venv/bin/python paper/scripts/github_live_study.py \
  --task-design natural-extractive-v2 --regrade-results \
  --results-path paper/results/github_natural_replication/results.json
```

## What this protocol does and does not establish

The experiment tests free-order trace discovery, exact factual task preservation for a
partial artifact, a live hand-written-macro comparison, and balanced latency/cost on 30
held-out real records. It also demonstrates safe abstention from a recurring but
ungroundable third call.
It remains one model, one domain, deterministic snapshot tools, and a modest sample. It
does not establish cross-domain generalization, live GitHub reliability,
human productivity, or superiority to plan-cache, GEPA, Agent JIT, or EvoC2F baselines.
Those remain separate experiments rather than claims smuggled into this protocol.
