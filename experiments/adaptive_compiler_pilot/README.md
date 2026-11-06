# Exploratory adaptive compiler pilot

This is a prospective **feasibility pilot**, not a confirmatory experiment. The
user authorized **$300 total API/model spending** on November 6, 2026. The shared
ledger allocates $30 to this pilot, $30 to later discovery, $60 to calibration,
and $180 to final testing. These later stages remain unimplemented and unsealed;
the allocation does not establish an adequate sample size or a quality guarantee.

The pilot uses four deterministically hash-selected corrected BIRD dev questions
from each database with at least four eligible records. Exclude every historically
selected/attempted ID, web-viewed IDs 0–17, exact duplicate questions, and gold
execution failures recorded in the provider-free audit. This defines a restricted
benchmark population. It does not establish semantic gold correctness, model
pretraining novelty, or population-level independence. All pilot IDs must also be
excluded from future calibration and testing.

Each task runs three arms in balanced permutations: a conventional adaptive tool
agent, handwritten full-schema prefetch, and an **Agent JIT SQL adaptation**.
All arms use the same SQL tools, information payloads, model, reasoning effort,
output cap and endpoint. The baseline is a newly implemented Chat Completions
agent loop, not a rerun of the historical Agents SDK experiment. The prefetch arm
includes its two internal tool calls. Agent JIT includes all 32 sampled candidates,
static validation/ranking, and runtime model calls in its cost and wall time.
There is no quality-selected retry, fallback or removal of failed episodes.

Operational amendment v2: the first v1 task produced two API rejections because
Chat Completions did not support this model's function tools with reasoning `low`.
Its Agent JIT arm completed but answered incorrectly. The v1 seal/report and all
three raw attempts are retained; conservative accounting was $0.0877729. V2 uses
reasoning `none` for every arm, and 32 concurrent candidate generations, matching
the upstream sampled-batch width instead of the initial adapter's semaphore of
four. The same 36 IDs and arm order are retained. Q36 is now operationally exposed;
no v2 result is claimed to be independent of that inspection. V2 attempts live in
the `v2` subdirectory and use version-qualified request IDs, sharing the original
ledger and unchanged $30/$300 caps. V1 failures are reported separately, not erased
or pooled as matched v2 observations.

The pinned upstream generator/checker/ranker is unmodified. Its browser runtime is
replaced with a networkless Docker worker and host-mediated read-only SQL tools.
`list_tables` maps to `listItems` (not the upstream observer), and the starting
prerequisite state is supplied explicitly. Tool results expose a `payload` string
containing identical JSON information in each arm. The worker supports field
access and `model_dump`, not the entire Pydantic API. Runtime `ai_eval` retains
the pinned upstream system prompt, variable formatting and JSON parse behavior;
transport uses the common budgeted client, with no unbudgeted retry fallback.
The reasoning model does not use upstream's temperature 0.5 setting. These are
material adaptation differences; no native Agent JIT browser reproduction or
faithful reproduction of the original paper's numerical results is claimed.

A provider-free execution-parity probe subsequently found that the frozen pilot
worker differs from upstream on print output, top-level returns and last-binding
result selection. `container_worker_native.py` is a prospective replacement using
the unmodified pinned upstream executor inside the same container boundary. Its
fixture results are retained in `executor_parity.json`; it was **not** used to
rerun or relabel the live pilot. Neither fixture parity nor this SQL adaptation
establishes native browser reproduction. Treat the port's observed score as
adapter feasibility evidence, not a method-level comparison.

## Freeze and execute

Requires the repository live/dev dependencies, pinned BIRD cache from the prior
preflight, Docker, and the pinned Agent JIT checkout in its own `uv sync --locked
--extra browser` environment. Conflicting upstream OpenAI/Anthropic dependency
versions are kept separate; no project dependency ranges are weakened.

```sh
GAC_TEST_PILOT_DOCKER=1 .venv/bin/python -m pytest paper/scripts/test_adaptive_pilot.py
.venv/bin/python paper/scripts/adaptive_pilot.py seal
.venv/bin/python paper/scripts/adaptive_pilot.py run --checkout /tmp/gac-agent-jit-preflight
.venv/bin/python paper/scripts/adaptive_pilot.py report
```

The seal pins task IDs, exact source bytes, database hashes, instructions, tools,
limits and arm order before provider calls. Execution refuses code/data drift.
The ignored directory `benchmarks/.cache/adaptive_compiler_pilot` is the permanent
local campaign record: **do not delete/reset its ledger to resume**. A single
runner lock prevents duplicate execution. Each attempt is persisted before its
first request; resume skips every previous attempt, including interruptions.
`--limit` bounds newly started episodes for an initial operational check, without
reordering or replacing tasks. Operational failures may stop the pilot; a repair
must retain the old seal/attempts and be described as a protocol amendment.

The ledger reserves conservatively before each request under a process lock.
Every request, failed call and runtime inference counts; SDK retries are disabled.
Unknown usage retains the entire reservation. Reported usage beyond a reservation
permanently blocks new reservations. Pricing checked against the [official model
page](https://developers.openai.com/api/docs/models/gpt-5.6-luna): $0.20/M input,
$0.02/M cached input and $1.20/M output. Reservations use $0.50/M input and a
UTF-8 payload-byte bound plus 8,192 framing tokens, with a 200 KB payload cap and
4,096 output-token cap. The ledger is a conservative accounting estimate under
these pinned rates, not the provider invoice or an account-wide billing limit.
The alias `gpt-5.6-luna` can change; response model identifiers are retained.

## Endpoints and reporting

Primary: official-style unordered set execution accuracy, including every
scheduled episode. Invalid SQL, exhausted limits, runtime errors, interruptions,
and unstarted episodes are failures in that denominator. Gold unavailable during
execution is reported separately and never counted as success. Shape-sensitive
set and duplicate-sensitive bag agreement are diagnostics. Neither proves full
natural-language correctness; order-sensitive tasks need independent annotation.

Report descriptive paired outcomes, all candidate dispositions, total generation
and execution cost, tool counts, wall time, and missing/failed calls. No hypothesis
test, superiority/noninferiority claim, or positive-coverage certificate is planned
for this small pilot. GAC discovery can use the prespecified three train/one dev
traces per database, retaining all baseline attempts. Calibration is empty: any
candidate is a feasibility finding, never a deployable certified artifact.

The previous preflight's confirmatory **NO-GO** remains in force. Progression
requires a sealed comparison, appropriate sampling/weighting and uncertainty
analysis, fresh unfiltered calibration, fixed final test size, and a defensible
quality margin. Stop if feasibility or budget cannot support that study; do not
collect until a favorable result appears.
