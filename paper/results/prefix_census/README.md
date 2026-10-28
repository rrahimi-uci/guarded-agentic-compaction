# Prefix census over released agent trajectories

Provider-free trace analysis answering one question the introduction leaves open: how
often do released multi-step tool-using agents *open* with a read-only prefix that the
compiler could ground? `results.json` is produced by `paper/scripts/prefix_census.py run`
and `paper/iclr/tables/prefix_census.tex` by its `table` command; the artifact validator
checks that the table regenerates byte-identically from the JSON.

Definitions are identical for every corpus and are written into `results.json`
(`definitions`): the first model boundary is the first agent turn after the task prompt;
a read-only opening is the run of consecutive catalog-compilable calls from position 0
(a new user utterance, an unknown effect, a write, an approval-gated tool or a missing
capability ends it); a groundable opening is the longest Algorithm 2 window starting at
the first boundary at the registered parameters (`max_depth=2`, `kappa=3`, `w_min=2`,
`w_max=12`, `b_min=2`, entry schema `inputs`); families are canonical opening-window
hashes with support counted in distinct tasks; `n_max` is compared with the 92-group
zero-violation floor. Only the first 13 calls of a trajectory are ingested
(`w_max + 1`), which cannot change any window that starts at the first boundary.

## Corpora selected

| Corpus | Why |
|---|---|
| `nebius/SWE-rebench-openhands-trajectories` (CC-BY-4.0, 67,074 trajectories) | Executed OpenHands v0.54.0 CodeAct trajectories with native function calling on 1,823 real repositories; structured `tool_calls` with JSON arguments and per-call observations; the editor's `view` sub-command is unambiguously a read and `execute_bash` is unambiguously not. |
| `nebius/SWE-agent-trajectories` (CC-BY-4.0, 80,036 trajectories) | Executed legacy SWE-agent trajectories (text-action ReAct, a different scaffold architecture) on real issues; the scaffold's own `open`/`goto`/`scroll_*`/`search_*`/`find_file` commands are documented reads and `edit`/`create`/`submit` documented writes; everything else is a raw shell command. |
| `sierra-research/tau-bench` `historical_trajectories` (MIT, 1,980 trajectories) | Executed function-calling runs of two models over two customer-service domains with observed tool results; a clean API tool set (`get_*`/`find_*`/`list_*`/`search_*` reads versus `cancel_*`/`modify_*`/`book_*` writes) in a non-coding domain, and a conversational setting where user turns interleave with tool calls. |

Both substrates the paper already ingests are re-measured with the same definitions:
NESTFUL (gold sequences; every function is pure) and, where the released logs allow,
AppWorld's 28 released baseline runs (8,190 trajectories; method/url/arguments only, so
the read-only column is measurable and the groundable column is not).

## Corpora considered and not selected

| Candidate | Reason |
|---|---|
| `SWE-bench/SWE-smith-trajectories` (MIT) | Same SWE-agent scaffold family as a selected corpus, run on procedurally generated (synthetic) task instances rather than real issues; would add volume, not architecture or domain diversity. A natural extension. |
| OpenHands SWE-Gym releases (`SWE-Gym/OpenHands-*`) | Repository names cited in the OpenHands dataset card no longer resolve on Hugging Face at snapshot time (404). |
| tau2-bench run logs | The repository ships task definitions and leaderboard results, not per-step trajectories with tool results. |
| AgentBench, WebArena logs | Released logs are per-environment text transcripts (OS/DB shells, browser accessibility trees) in which the action space is free-form commands or DOM operations; no tool identity can be classified read-only with confidence, so every call would be `UNKNOWN` by construction. |
| ToolBench released ReAct traces | Distributed through a Google Drive archive rather than a pinned revision, and its tools are thousands of RapidAPI endpoints whose effects are known only by HTTP verb; the repository already screens ToolBench's task definitions this way (`load_toolbench`) without accepting the labels as a signed catalog. |
| GAIA, BrowseComp, SWE-bench task sets | Task definitions only (no executed trajectories), already recorded as such in `paper/results/external_benchmarks/`. |

## Files

- `results.json` — per corpus and arm: traces, groups, model and architecture mix, first
  call and first barrier distributions, read-only and groundable opening histograms, block
  reasons with the ungrounded slots, slot marks, families with support and `n_max`, the exact
  gate floor, ingestion accounting, and a per-model breakdown.
- `paper/results/datasets/{openhands,sweagent,taubench}/source_manifest.json` — dataset,
  URL, pinned revision, license, snapshot date and SHA-256 of every file read. Raw corpora
  are not committed.
- `benchmarks/contracts/effects/{openhands_swe_rebench,sweagent_nebius,taubench}.yaml` —
  the signed catalogs, one comment per tool.
- `benchmarks/external/trajectories.py` — the capture adapters.

## Sensitivity arms

Each released corpus carries exactly one labelled arm, reported in its own table row and
never pooled with the primary measure: `shell_reads_admitted` flips the allowlisted
single-utility shell invocations (`ls`, `cat`, `grep`, `find` without executing flags, read
`git` subcommands, ...) to `READ_LOCAL` for the two coding corpora;
`pre_tool_user_turns_folded` measures tau-bench openings from the first tool-issuing turn
with the user utterances before it folded into the entry state, which is the analogue of
the AppWorld prologue relaxation.

## Reproduction

```
python paper/scripts/prefix_census.py manifest --source-root "$CENSUS_SOURCE_ROOT"
python paper/scripts/prefix_census.py run --source-root "$CENSUS_SOURCE_ROOT"
python paper/scripts/prefix_census.py table
```

`$CENSUS_SOURCE_ROOT` holds `openhands/`, `sweagent/` and `taubench/` with the files named
in the source manifests, and optionally `appworld/` (the pinned `appworld download data`
and `appworld download experiment-outputs` tree). Downloads go into isolated directories
and are parsed only; nothing from a corpus is executed.
