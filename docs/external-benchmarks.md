# Supplementary external-benchmark interoperability audit

This material is an interoperability ledger, not the paper's primary optimizer
comparison. Only NESTFUL and API-Bank retain complete observed intermediate values and
appear in the main trace-compiler evaluation. The remaining benchmark work is preserved
here because it verifies sources, adapters, official checkers, or explicit execution
gates; it does not demonstrate compaction value and is never pooled with the three
real-record GitHub workflow families.

## Result ledger

| Benchmark | Implemented path | Current result | What it licenses |
|---|---|---|---|
| NESTFUL | Full provider-free compiler evaluation | 1,415 traces; 24 pass / 12 abstain / 0 wrong held-out windows; every family retires | Provenance, synthesis, replay, and refusal on one public executable corpus |
| API-Bank | Full trace normalization, compiler evaluation, and pinned API replay | 212 complete traces; 48 candidate windows; 2 synthesized families; 0 pass / 2 abstain / 0 wrong; every family retires | A second compiler substrate and an upstream trace/code compatibility audit |
| BFCL v4 | Official checker over all `multi_turn_base` gold plans | 200/200 plans valid; 1,142 reference calls | Pinned official gold-plan compatibility, not model quality or compilation |
| ToolSandbox | Pinned Python 3.11 container plus one real-provider official scenario | 0.9818 milestone similarity; 2 tool calls | Bounded provider/harness compatibility on a public simulator |
| maintained τ²/τ³ | Isolated pinned environment and one real-provider task in each accessible text domain | 0/4 end-to-end reward; 31 tool calls; 288,757 tokens; $0.0490 reported cost | Bounded official simulated-domain quality and cost evidence |
| ToolBench | Versioned repository-fixture adapter | 10 fixtures normalized | Adapter smoke only; the full data archive and live backend are not sealed here |
| AgentBench | Knowledge-graph action plus DB/OS task adapters | 556 tasks normalized | Source compatibility only; full services and Freebase data are gated |
| GAIA | Authenticated source preflight | HTTP 403 authorization gate | An explicit access gate; no score is imputed |
| SWE-bench Verified | Pinned 500-task dataset adapter and official-harness preflight | 500 real GitHub issue tasks normalized | Task coverage only; the current arm64/12.5-GiB Docker host does not meet the recommended x86-64/16-GiB contract |
| BrowseComp | Three sealed tasks with `gpt-5.6` and hosted web search, scored by the pinned reference-style grader | 1/3 correct; 28 searches; 237,859 tokens; 408.1 seconds | Bounded live-web quality/cost evidence and a compiler-bypass case |

Across the eight accessible reference-plan adapters, the common IR covers 5,419 tasks and
17,836 actions. Five external paths execute beyond parsing (API-Bank, BFCL, ToolSandbox,
τ, and BrowseComp); three use real OpenAI provider calls. Exactly 77 provider requests are
accounted by stored usage records. ToolSandbox does not retain exact request/token usage,
so its three assistant messages remain separately labeled instead of being added to that
total.

## Why most rows are not compiler scores

The compiler requires ordered calls with observed arguments and results, a compatible
entry snapshot, effect declarations, grouping keys, and a replay oracle. The
`ReferenceTask` adapter records which of those fields truly exist and fails closed when a
task without observed results is converted to an executable Episode. It also rejects
cross-revision or cross-substrate pooling.

Only NESTFUL and API-Bank currently support compiler execution. BFCL provides gold calls
without results. ToolSandbox and τ produce useful stateful simulations, but their bounded
live runs are neither real-world demonstrations nor paired compiler interventions.
BrowseComp uses a server-managed hosted search trace that cannot be replayed through the
local effect and staging contract, so baseline bypass is correct. SWE-bench provides real
issues but not the historical agent trajectory required for post-trace compilation.

## API-Bank finding

API-Bank is the most important extension because it tests whether the NESTFUL refusal is a
one-dataset artifact. Of 389 observed calls over 49 tools, conservative write barriers and
entry-state checks leave 48 candidate windows in 37 tasks. Nineteen families recur; eight
have support of at least three, but the maximum is eight. Two synthesize and both abstain
on their held-out windows. The configured gate requires 92 independent zero-violation
groups, so no family can be certified.

Pinned upstream API re-execution exactly matches 338/389 calls. Thirty-seven differ, nine
raise missing-state `KeyError`s, and five need unavailable dependencies; 162/212 tasks
replay completely. These are upstream recorded-data/fresh-fixture compatibility outcomes,
not compiler errors.

## Reproduction

Use a disposable source directory outside the repository:

```bash
python paper/scripts/external_benchmark_sources.py \
  --root "$BENCHMARK_SOURCE_ROOT" \
  --output paper/results/external_benchmarks/source_preflight.json

python paper/scripts/external_benchmark_matrix.py \
  --source-root "$BENCHMARK_SOURCE_ROOT"

python paper/scripts/api_bank_benchmark.py \
  --source-root "$BENCHMARK_SOURCE_ROOT"

python paper/scripts/bfcl_structural_benchmark.py \
  --source-root "$BENCHMARK_SOURCE_ROOT"
```

The live τ, ToolSandbox, and BrowseComp commands require `OPENAI_API_KEY`. GAIA acquisition
checks `HF_TOKEN`, but the current account is not authorized for the gated dataset. Secret
values, prompts, questions, answers, messages, tool arguments/results, and search results
are excluded from publication JSON.

### Exact bounded live reruns

These commands spend provider credits. Load `OPENAI_API_KEY` into the process environment
without printing it, and use the exact pinned checkouts created by
`external_benchmark_sources.py`. Raw simulator transcripts stay in the disposable source
directory; only the redacted summaries are written into the repository.

Run the four predeclared τ tasks from the pinned `tau2` checkout after installing its locked
environment:

```bash
cd "$BENCHMARK_SOURCE_ROOT/tau2"

tau2 run --domain airline --agent-llm gpt-4.1-mini --user-llm gpt-4.1-mini \
  --agent-llm-args '{"temperature":0}' --user-llm-args '{"temperature":0}' \
  --num-trials 1 --task-ids 1 --max-steps 30 --seed 20260804 \
  --save-to gac_airline_task1

tau2 run --domain retail --agent-llm gpt-4.1-mini --user-llm gpt-4.1-mini \
  --agent-llm-args '{"temperature":0}' --user-llm-args '{"temperature":0}' \
  --num-trials 1 --task-ids 100 --max-steps 30 --seed 20260804 \
  --save-to gac_retail_task100

tau2 run --domain telecom --agent-llm gpt-4.1-mini --user-llm gpt-4.1-mini \
  --agent-llm-args '{"temperature":0}' --user-llm-args '{"temperature":0}' \
  --num-trials 1 \
  --task-ids '[mobile_data_issue]airplane_mode_on|user_abroad_roaming_enabled_off[PERSONA:None]' \
  --max-steps 30 --seed 20260804 --save-to gac_telecom_one

tau2 run --domain banking_knowledge --agent-llm gpt-4.1-mini \
  --user-llm gpt-4.1-mini --agent-llm-args '{"temperature":0}' \
  --user-llm-args '{"temperature":0}' --num-trials 1 --task-ids task_010 \
  --max-steps 30 --seed 20260804 --save-to gac_banking_task010

cd -
python paper/scripts/tau2_live_summary.py --source-root "$BENCHMARK_SOURCE_ROOT"
```

Build the pinned ToolSandbox compatibility container and run the one predeclared scenario:

```bash
TOOLSB_RUN_ROOT="$(mktemp -d)"
docker build \
  --file benchmarks/external/envs/toolsandbox.Dockerfile \
  --tag gac-toolsandbox \
  "$BENCHMARK_SOURCE_ROOT/toolsandbox"
docker run --rm --env OPENAI_API_KEY \
  --volume "$TOOLSB_RUN_ROOT:/opt/toolsandbox/data" \
  gac-toolsandbox \
  --user GPT_4_o_2024_05_13 \
  --agent GPT_4_o_2024_05_13 \
  --scenario search_message_with_recency_oldest
python paper/scripts/toolsandbox_live_summary.py --run-root "$TOOLSB_RUN_ROOT"
```

Run the sealed three-example BrowseComp slice. The script reads `.env` when the key is not
already present and never writes the decrypted tasks or model responses:

```bash
python paper/scripts/browsecomp_live_benchmark.py \
  --source-root "$BENCHMARK_SOURCE_ROOT" \
  --examples 3 \
  --agent-model gpt-5.6 \
  --grader-model gpt-4.1-mini
```

These are bounded research runs, not official leaderboard submissions. ToolSandbox and τ
are simulated environments; BrowseComp is live-web evaluation. None is presented as a
real-world production demonstration or as a paired compiler-effectiveness result.

The authoritative machine-readable artifacts are under
`paper/results/external_benchmarks/`; exact source identities and checksums are in
`benchmarks/manifests/external-benchmarks.yaml`.
