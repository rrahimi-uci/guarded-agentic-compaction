# Prospective matched workflow-memory comparison

Status before execution: protocol, implementation and selection are frozen by
`seal.json`; generated memory is frozen separately before evaluation. Never
modify a used seal or driver to improve observed results. Date: 2026-10-15.

## Question and scope

On fresh issues from the retained public GitHub snapshot, how does the existing
GAC SDK integration compare with a pinned **AWM offline workflow-memory
adaptation** and an ordinary agent? This is a whole-system comparison. It is
neither native AWM browser-benchmark reproduction nor an isolated test of a
compiler safeguard. See [COMPATIBILITY.md](COMPATIBILITY.md).

## Arms and shared conditions

- `baseline`: existing natural-extractive-v2 agent, without workflow memory.
- `gac`: the same agent through the real `CompactingModel`, with the retained
  candidate reconstructed by the existing fresh-study routine. Synthetic model
  responses execute through the SDK tools. This adapter does not establish exact
  post-emission rollback. Changed contract components are recorded in the seal.
- `awm_offline_adapted`: the same agent, preceded by frozen workflow memory from
  the pinned upstream offline induction, filtering and workflow-only retrieval
  functions. No online updates, concrete-example retrieval, or test-time tuning.

All arms share gpt-5.6-luna, task instructions, output schema, three immutable
snapshot tools, source data and grading. The memory insertion is the intended
AWM treatment. Each episode has a fresh SDK conversation; no local response
cache. Provider prompt caching is uncontrolled, usage-metered and order-balanced.
Settings: low reasoning and verbosity, no parallel tool calls, store=false,
2,048 output tokens per request, eight SDK turns, 120-second episode timeout,
SDK model retries zero and HTTP retries zero. Model alias drift remains possible.
Four independent issue groups may run concurrently; arms within an issue are
sequential in the sealed order. There are no retries or replacement issues.

## Discovery and adaptation

Use exactly the historical compiler-eligible discovery traces (130 of 132).
Both methods have access to this pool; GAC retains its original training,
development and calibration split, while AWM induces from all 130 traces.
Serialize only discovery task text and recorded tool names/arguments as upstream
`confirmed_task` and `action_reprs`; no held-out answers, oracle outputs, hidden
reasoning or evaluation results enter induction. The upstream navigation phrase
is replaced with read-only API tasks and actual tool schemas are appended. Keep
the upstream one-shot workflow example and 1,024-token induction output limit.

Run the unchanged upstream `llm_generate` body with a capture-only client to
construct the request without network access. Send its user message through the
study's Responses SDK transport: low reasoning/verbosity, rather than upstream
Chat Completions with temperature=0. This transport/model/domain adaptation is
explicit. One induction attempt only. Retain its output, usage and filtered
memory. The upstream `get_exemplars` runs with `retrieve_top_k=0`. Freeze a memory
seal before any pilot episode. No manual rewriting or selection among outputs.
A failed, empty or truncated induction stops the study rather than generating a
more favorable memory. Truncation is checked through raw response finish status.

## Cohorts and prospective decisions

Conservatively exclude IDs in all retained paper results and the fresh,
safeguard-mechanism, recovery-pilot and recovery-completion experiment artifacts.
Exclude pull requests. Rank remaining IDs by SHA256 of the fixed study label,
seed 20261019 and issue number, without inspecting answer outcomes. First six
issues form the execution pilot; next 120 form the primary cohort. No overlap
with discovery, prior studies or between pilot and primary cohorts is allowed.
Cycle all six permutations of three arms: once in the pilot, 20 times in primary.
There are 18 pilot and 360 primary episodes, plus one induction request.

Continue from pilot only if every episode completes with valid usage, tool
accounting and output schema. Accuracy is reported but is **not** a continuation
criterion. GAC must exhibit at least one actual compaction; otherwise stop as an
integration failure. Do not tune after pilot. In primary, retain isolated
failures and stop after five consecutive failed terminal episodes (completion
order). Pending attempts after interruption require reconciliation, never replay.

## Outcomes and analysis

Primary: all seven answer fields correct under the existing exact source grader
(category, issue number, evidence label, title, state, comment count and a valid
verbatim evidence excerpt). Tool-order agreement is separate, not a correctness
requirement for comparing systems. The historical four-field factuality endpoint
is secondary. Failed and unattempted scheduled episodes count as incorrect.

Report each arm's complete denominators, failures, field errors, tool-contract
rate, real provider requests, all SDK tool calls, tokens, cached/cache-write
usage, wall time and estimated deployment cost. Include partial usage from
failures; never interpret missing usage as zero resource consumption. Report
induction cost separately and amortized across the 120 primary tasks; historical
shared discovery acquisition is a sunk, shared cost, not a newly measured zero.
GAC reconstruction time and AWM induction time are recorded separately.

Primary contrast: GAC minus adapted AWM. Secondary: each versus baseline. Report
paired issue-level differences and 10,000-draw percentile bootstrap intervals
(seed 20261019) for descriptive accuracy and resource differences. Include exact
McNemar p-values and Holm correction across the three accuracy contrasts; do not
call bootstrap intervals simultaneous. For all-success/boundary rates, also
report exact binomial marginal intervals: a degenerate paired bootstrap does
not prove equality. This exploratory 120-issue study has no powered equivalence
or noninferiority claim. Do not infer safety, broad superiority, cross-domain or
second-model generalization. A negative/null outcome is retained and published.

## Budget, integrity and execution

The user approved an overall estimated-spend cap of **$400**, carried forward
from recovery work. Carry the recovery aggregate ($7.00176224, including unknown
cost reserves) and conservatively also the separately approved earlier fresh
comparison ($0.26863865): $7.27040089 before this study. Bind their source files
and validate prior pending state and analysis/checkpoint identity. Reserve $1
before each attempt, retain $1 for any failed attempt, and include all known
partial usage. This is a local estimated-spend guard, not a provider billing cap.

Preflight is provider-free. Seal source, vendor, protocol, environment, rate card,
cohorts, schedule, candidate, discovery request and source hashes. Use an exclusive
runner lock and atomic checkpoint with pending entries before external calls.
All analysis rechecks seals, grades, successful tool outputs, usage and metrics.
No credential, raw provider trace or hidden reasoning is stored. Evaluation
answers and the explicitly requested induction output are retained for audit.

Commands (use the repository virtual environment):

```sh
PYTHONPATH=src python paper/scripts/matched_reuse_baseline.py prepare
PYTHONPATH=src python paper/scripts/matched_reuse_baseline.py verify
PYTHONPATH=src python paper/scripts/matched_reuse_baseline.py run --env-file /path/to/.env
PYTHONPATH=src python paper/scripts/matched_reuse_baseline.py analyze
```
