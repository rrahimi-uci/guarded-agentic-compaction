# Open benchmark development protocol — 2026-11-06

## Purpose and decision

This phase responds to the reviewers' request for adaptive workflows, independent quality grading,
and comparison with simpler or competing compilation methods. It selects an executable substrate
and validates the baseline/oracle path. It does **not** complete the compiler comparison or replace
the original admission requirements. The [retained report](../results/adaptive_benchmark_screen/REPORT.md)
states the measured results and outstanding requirements.

WebArena-Verified was chosen after metadata/source inspection, before model outcomes. τ²-Bench-Verified
shares every screened task ID with the previously inspected τ source. AppWorld remains development-only
because of prior solution/trajectory exposure. WorkArena++ remains an alternative if approved instance
access is available; no access was obtained and no workload was run there. SWE-bench was not executed
in this phase. No benchmark was selected because GAC won on it.

## Selection, model and accounting

- Pin all source commits and hash datasets. The selection script emits no reference answers.
- Choose six single-site Reddit development tasks, one per hash-ranked template. Exclude templates
  from the previously inspected Agent JIT catalog and reproduction examples.
- Retain all six tasks in the pilot denominator. Keep any failure or interruption; do not retry or replace
  an attempted task. Stop further spending after an operational exception.
- Use the existing campaign model and locked ledger with a $300 total cap and $30 discovery-stage cap.
  The six-task run used `gpt-5.6-luna`, at most 32 requests/task and a 600-second episode timeout.
- Retain full observations in raw evidence. Model context preserves task/action history and the four
  most recent tool observations; each accessibility snapshot is bounded to 24,000 characters.
- Give the agent public instructions/start URLs, not test definitions. Grade its final response and
  captured HAR after the browser interaction ends. Use the same official evaluator source for controls
  and agent attempts.
- Do not interpret the local amd64-on-arm64 timings as native latency evidence.

The v1/v2 pre-provider amendment is described in the report and the v2 seal. All six model runs used
v2 without source changes during execution. The v1 controls are retained, including their errors.

## Reproduce the metadata audit

Use a dedicated checkout/cache. These commands acquire public source but make no model calls:

```sh
mkdir -p benchmarks/.cache/adaptive_benchmark_screen
git clone https://github.com/amazon-agi/tau2-bench-verified.git benchmarks/.cache/adaptive_benchmark_screen/tau2-verified
git -C benchmarks/.cache/adaptive_benchmark_screen/tau2-verified checkout 864350a8971a8f8ee9e7b8472e2edc380a806b0c
git -C benchmarks/.cache/adaptive_benchmark_screen/tau2-verified fetch https://github.com/sierra-research/tau2-bench.git 1eceb0453fe2effa1ba26b6a51fc52b966944ec1
git clone https://github.com/web-arena-x/webarena.git benchmarks/.cache/adaptive_benchmark_screen/webarena
git -C benchmarks/.cache/adaptive_benchmark_screen/webarena checkout dce04686a56253aefba7b18a4fa0937cf1dc987b
git clone https://github.com/ServiceNow/webarena-verified.git benchmarks/.cache/adaptive_benchmark_screen/webarena-verified
git -C benchmarks/.cache/adaptive_benchmark_screen/webarena-verified checkout 6473f72db5dcefc97b5725b59e734504edc28a21
.venv/bin/python paper/scripts/adaptive_benchmark_screen.py verify
.venv/bin/python -m pytest -o addopts='' -q paper/scripts/test_adaptive_benchmark_screen.py
```

Do not rerun clone over existing directories or reset modified upstream sources. `verify` checks their
HEADs, tracked cleanliness, dataset hashes and recomputed audit against the retained report.

## Reproduce development execution

The runner requires an isolated Python environment with the pinned WebArena-Verified source,
Playwright/Chromium, OpenAI SDK and python-dotenv. Exact installed package versions are retained
in `webarena_development/seal.json`; use those versions when reproducing. Keep them separate from
the repository's normal development environment because the benchmark pins Pydantic 2.12.0.
The website image digest is recorded in that seal and the report. No Docker socket, task definitions
or host directories are exposed to the browser agent. The runner executes predefined Playwright
operations, never model-generated Python or JavaScript.

The entrypoints are `webarena_verified_development.py freeze`, `controls`, and `run`. `freeze` refuses
to overwrite a seal; `controls` refuses to overwrite its attempt; `run` verifies source/dependency
versions and successful controls, and skips every existing attempt file. `run` makes paid calls.
Do not reset `benchmarks/.cache/adaptive_compiler_pilot/ledger.json`, erase attempt files, or reuse this
development cohort as fresh calibration/test data. A new scientific protocol needs a new versioned
run directory and seal, while continuing the same authorized campaign ledger.

The script `export_adaptive_development.py` requires one terminal attempt for every scheduled task
and refuses to overwrite published evidence. Its report distinguishes completed/failing/unscored
attempts and includes a ledger excerpt, archive hashes, controls and source hashes. The retained
archive allows inspection/regrading without repeating paid inference. For a different checkout path,
construct the official evaluator configuration with that checkout's dataset and the origin recorded
in each attempt's public input; the archived HAR uses the trial's ephemeral loopback port.

## AppWorld controls and protected output

The AppWorld Dockerfile uses the source at `42b5bcf3cd334fee33f0c37c02070a9f5807add5` as build context.
The reference worker permits only official training tasks, exposes only public API names to the
agent boundary, rejects reserved requester arguments, and invokes the official nonempty test suite
after interaction. Its live negative boundary check refused a private API and a reserved argument.
The earlier reference attempt exceeded a 64-call limit; the reference-only control cap was increased
to 1,000 before the recorded passing control. This does not increase the agent's 64-call cap.

Only aggregate outcomes and hashes are plaintext. `operational_evidence.bundle` was created with
the pinned upstream `appworld.common.crypto.pack_bundle`, including upstream license notices.
It can be read using the corresponding upstream unpacking utility and public bundle constants.
Do not publish decrypted task text, solutions or source-derived responses. AppWorld paid execution
was not performed in this phase; the browser benchmark takes priority.

## Review and publication boundary

The subsequent [browser boundary development](browser-boundary-development.md)
implements and checks a research-only fresh-episode handoff/fallback boundary and
audits typed-prefix discovery from these same six traces. It does not turn this
development cohort into fresh calibration/test evidence or authorize GAC admission.

All implementation, evidence and documentation belong in a dedicated PR. Leave it open for the
author's review and merge. A passing development pilot does not close the reviewers' requests for
matched compiler comparisons, fresh calibration, lifecycle economics or reliable fallback.
