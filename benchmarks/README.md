# Real-record multidomain benchmark

The browser-readable [benchmark explorer](https://rrahimi-uci.github.io/guarded-agentic-compaction/benchmarks/explorer/index.html)
publishes the broader benchmark audit with each substrate, execution state, denominator,
and claim boundary kept separate.

This benchmark implements the prospective multidomain study. Its rationale and the
disposition of every benchmark family are in the paper's appendix; the sealed preflight
artifacts are under [`paper/results/multidomain/`](../paper/results/multidomain/).
It compares the unchanged agent, Guarded Region Compilation (GRC), and an independently reviewed
deterministic macro on three factual, read-only workflows:

- open-source vulnerability evidence reconciliation;
- SEC filing-fact reconciliation; and
- privacy-modified public HMDA record interpretation.

These workflows do not make patch, investment, lending, legal, or compliance decisions. Source
acquisition is provider-free. Measured executions use live OpenAI Agents SDK calls only after an
explicit model, pinned pricing, independent macro approvals, and a positive user-approved spend
cap are supplied. An API key by itself is not spending authorization.

The generic benchmarking contracts ship in the Python package. Domain acquisition, retained
records, and paper study drivers are repository artifacts, so `guarded-agentic-compaction benchmark ...`
study commands must be launched with this checkout as the working directory.

## Verified checkpoint

As of 2026-08-04:

| Domain | Real groups | Exact oracle | Variable path | State |
|---|---:|---:|---:|---|
| Vulnerability | 420 | 420/420 | 48/420 | available |
| HMDA | 420 | 420/420 | 416/420 | available |
| SEC | 0 | not run | not run | blocked by missing `SEC_USER_AGENT` |

The provider-free validator therefore passes 840/840 independently constructed gold records and
840/840 macro comparisons on available real cases, while the three-domain
protocol correctly remains ineligible for freezing. No OpenAI call has been made for this study.
The normalized records are under `paper/results/multidomain/preflight/`; raw downloads remain in
the gitignored `benchmarks/.cache/`.

On 2026-10-15, the [SEC provider-free preflight](../paper/results/multidomain/preflight/sec/README.md)
reached 420 real groups, 420/420 EdgarTools parser checks, and 420/420 exact
oracle and gold-construction checks. All three domains now pass provider-free
preflight. The SEC selector required a disclosed post hoc correction after its
first run failed at 405/420 groups. This cohort is exploratory; independent
human macro/gold review, protocol approval, and live model executions remain
outstanding. This update does not change the historical 2026-08-04 checkpoint
above or establish a new paper efficacy result.

On 2026-10-28, the frozen single-domain HMDA v2 study (`manifests/hmda-study-v2.yaml`,
protocol `paper/results/multidomain/protocol/hmda-v2-frozen.json`) was taken back to
the discovery phase. The 2026-10-07 discovery attempt retained under
`paper/results/multidomain/discovery/` (80 attempts, 0 completed, `UserError`) was
reproduced provider-free against the runner version then in effect (commit `0ea8c41`):
the Agents SDK rejected the strict JSON schema of `HmdaAnswer`
(`special_states: dict[str, Literal[...]]` emits `additionalProperties`) inside
`Runner.run` before any provider request. Commit `3ce76b8`, six minutes after the
failed run, already routes that answer model through the SDK's non-strict output
wrapper; the current runner reaches the provider on the same schedule. The runner now
prints a bounded, secret-masked diagnostic per failed attempt, accepts
`--stop-after-consecutive-failures`, and numbers resumed attempts after retained
failures (a resume into a ledger with failed rows previously aborted on a ledger
conflict). Three live discovery attempts followed under
`paper/results/multidomain/hmda-v2/`: the first was halted after four
`AuthenticationError` responses (HTTP 401 `invalid_api_key`; no billable request); after
the key was rotated, the first execution at the default request bound of 8 raised
`MaxTurnsExceeded`, so the bound (a runner argument, not a frozen value) was raised to
20 with a 0.09 USD reservation; the run then halted after eight consecutive
`ModelBehaviorError` attempts across three groups. In every captured case the model's
final answer fails the frozen `HmdaAnswer` schema by filling `special_states` with
code/label objects instead of the `NA`/`EXEMPT`/`UNAVAILABLE`/`NOT_APPLICABLE`
strings, which non-strict output mode cannot enforce. The remedy (a prompt or answer-type
change in `benchmarks/runtime.py`) alters the `evaluator_digest` bound by the signed
macro approval, so the study stopped there. 0 of 40 discovery executions completed;
development, compile-grc, freeze-actions, pilot, and artifact-calibration did not run;
bounded unmeasured spend is at most 0.84 USD. The macro approval digests still match the
implementation. The full sequence, the protocol decision now required, and the exact
re-run commands are in
[`hmda-v2-live-study-handoff.md`](../paper/results/multidomain/review/hmda-v2-live-study-handoff.md).
This update establishes no efficacy result.

## Acquisition

All acquisition commands are real-source commands; there is no synthetic fallback.

```bash
# Vulnerability: OSV PyPI archive, GitHub Advisory Database records,
# PyPI version checks, CISA KEV, and checksum-verified NVD annual feeds.
.venv/bin/python -m benchmarks.acquire vulnerability \
  --out paper/results/multidomain/preflight/vulnerability

# HMDA: official privacy-modified public LAR CSVs.
.venv/bin/python -m benchmarks.acquire hmda \
  --year 2023 --year 2024 --state RI \
  --out paper/results/multidomain/preflight/hmda

# SEC: requires a genuine project/entity and contact address.
export SEC_USER_AGENT='Project Name contact@example.org'
.venv/bin/python -m benchmarks.acquire sec \
  --ciks /path/to/pinned-ciks.json \
  --out paper/results/multidomain/preflight/sec
```

For SEC acquisition, the optional pinned EdgarTools parser can check every
selected Company Facts observation against the checksum-pinned raw SEC response:

```bash
.venv/bin/python -m pip install -e '.[sec]'
.venv/bin/python -m benchmarks.acquire sec \
  --ciks /path/to/pinned-ciks.json \
  --out paper/results/multidomain/preflight/sec \
  --edgartools-audit
```

This writes `edgartools_audit.json` and binds its hash to `report.json`. Any
parser disagreement fails the command without replacing a case. To repeat the
check later from the retained pool and original cache, run
`python -m benchmarks.audit_sec_edgartools --pool
paper/results/multidomain/preflight/sec --cache benchmarks/.cache`; this replay
is offline and requires no contact identity. The parser checks accession,
period, filing date, unit and value from the same Company Facts response. It
does not independently establish that the filed XBRL fact or gold answer is
correct. The existing filed-instance and independent-gold checks remain
necessary. A one-case exploratory [live SEC pilot](../paper/results/multidomain/pilots/sec_edgartools/README.md)
exercises the corrected filing-index check and passes this audit on a real
Company Facts response. The planned 420-group SEC preflight and model run are
still unrun.

Pass `--offline` to replay a complete cache. Every fetch is HTTPS, content-addressed,
checksum-verified, atomic, capped at 40 GiB in aggregate, and stops on HTTP 403/429. SEC clients
are shared within the process so submissions, Company Facts, index, and filing-document requests
collectively stay at or below five requests per second.

The retained HMDA files were acquired from the official Data Browser URLs shown in
`manifests/sources/hmda.yaml`. A later standard-library fetch replay received HTTP 403 and stopped
as required; the checksum-pinned normalized pool remains valid, but an empty-cache HMDA replay
must be rechecked before release. Do not weaken or bypass a source policy response.

Independent gold is constructed directly from normalized records in `benchmarks/gold.py`; pool
builders never call the evaluated macros. If that implementation or the HMDA privacy allowlist is
reviewed and strengthened, the existing public snapshots can be migrated without a network call:

```bash
.venv/bin/python -m benchmarks.rebuild_gold hmda \
  paper/results/multidomain/preflight/hmda
.venv/bin/python -m benchmarks.reseal hmda \
  --pool paper/results/multidomain/preflight/hmda
```

Preflight checksum-binds cases, gold, snapshot, and current independent-gold code. For HMDA it
also semantically rejects any schema or row field outside the committed agent-visible allowlist.

Independent gold can be recomputed provider-free from the retained normalized public records:

```bash
.venv/bin/python -m benchmarks.rebuild_gold vulnerability \
  paper/results/multidomain/preflight/vulnerability
.venv/bin/python -m benchmarks.rebuild_gold hmda \
  paper/results/multidomain/preflight/hmda
```

This path uses `benchmarks/gold.py`, which is deliberately isolated from the evaluated macro
implementations. Preflight verifies the current gold-code digest and exact `cases.jsonl`,
`gold.jsonl`, and `snapshot.json` hashes. Freezing then digests the complete canonical case pool;
later scheduling rejects post-freeze input or metadata drift even when case IDs are unchanged.

## Provider-free validation and protocol freeze

```bash
.venv/bin/guarded-agentic-compaction benchmark preflight \
  benchmarks/manifests/multidomain-study.yaml \
  --cases vulnerability=paper/results/multidomain/preflight/vulnerability/cases.jsonl \
  --cases sec=paper/results/multidomain/preflight/sec/cases.jsonl \
  --cases hmda=paper/results/multidomain/preflight/hmda/cases.jsonl \
  --require-source-configuration

.venv/bin/python paper/scripts/validate_multidomain.py \
  --pool vulnerability=paper/results/multidomain/preflight/vulnerability \
  --pool sec=paper/results/multidomain/preflight/sec \
  --pool hmda=paper/results/multidomain/preflight/hmda \
  --out paper/results/multidomain/preflight/validation.json

.venv/bin/guarded-agentic-compaction benchmark freeze \
  benchmarks/manifests/multidomain-study.yaml \
  --cases vulnerability=paper/results/multidomain/preflight/vulnerability/cases.jsonl \
  --cases sec=paper/results/multidomain/preflight/sec/cases.jsonl \
  --cases hmda=paper/results/multidomain/preflight/hmda/cases.jsonl \
  --model <pinned-model> --pricing <pricing.json> \
  --out paper/results/multidomain/protocol/frozen.json
```

Freezing assigns 40 discovery, 30 development, 100 artifact-calibration, 75
portfolio-calibration, 100 test, and 75 reserve groups per domain. Group and lineage edges may not
cross roles. The command cannot succeed until all three real pools contain 420 independent groups.

## Live study controls

Before any live phase, create:

1. a pricing JSON document conforming to `contracts/pricing.schema.json`, copied from a dated
   official provider pricing/model page; it includes exact rates, service tier, a maximum
   billable input-token bound, and the run's output-token limit;
2. one macro approval per domain conforming to `contracts/macro-approval.schema.json`, signed off
   by a reviewer distinct from the author; and
3. an explicit dollar cap and conservative per-attempt reservation.

Pricing values and approvals are deliberately not prefilled: inventing either would turn a safety
gate into fake evidence. The runner loads `.env` only after every provider-free check passes and a
non-dry run begins. It reads `OPENAI_API_KEY` by presence and never serializes it.
The runner derives a worst-case per-attempt token cost from the frozen ceilings and refuses a
reservation below it; it also refuses a total cap below every scheduled retry reservation.

Create reviewer materials first. This validates the deterministic macro on every available real
case but deliberately emits `approved: false`; a distinct human must inspect and sign the final
approval files:

```bash
.venv/bin/guarded-agentic-compaction benchmark prepare-macro-review \
  --pool vulnerability=paper/results/multidomain/preflight/vulnerability \
  --pool hmda=paper/results/multidomain/preflight/hmda \
  --out paper/results/multidomain/review/macro-review-materials.json
```

The SEC pool is now available. The
[`three-domain-macro-review-materials.json`](../paper/results/multidomain/review/three-domain-macro-review-materials.json)
bundle includes all three domains with `approval_generated: false`; a distinct
reviewer must inspect the SEC macro, gold implementation, source records,
schema, effect contract, and outputs before signing.

Every live command supports `--dry-run`, which writes the exact counterbalanced schedule and the
maximum model-request and reservation bounds without loading `.env` or invoking a provider:

```bash
COMMON='--cases vulnerability=... --cases sec=... --cases hmda=... \
--pool vulnerability=... --pool sec=... --pool hmda=... \
--model <pinned-model> --pricing <pricing.json> \
--max-provider-usd <approved-cap> \
--reservation-usd-per-execution <conservative-reservation>'

.venv/bin/guarded-agentic-compaction benchmark discovery <frozen.json> $COMMON \
  --out paper/results/multidomain/discovery
.venv/bin/guarded-agentic-compaction benchmark development <frozen.json> $COMMON \
  --out paper/results/multidomain/development

.venv/bin/guarded-agentic-compaction benchmark compile-grc <frozen.json> \
  --ledger vulnerability=<discovery-ledger> --ledger vulnerability=<development-ledger> \
  --ledger sec=<discovery-ledger> --ledger sec=<development-ledger> \
  --ledger hmda=<discovery-ledger> --ledger hmda=<development-ledger> \
  --out paper/results/multidomain/registries

.venv/bin/guarded-agentic-compaction benchmark freeze-actions <frozen.json> \
  --cases vulnerability=... --cases sec=... --cases hmda=... \
  --pool vulnerability=... --pool sec=... --pool hmda=... \
  --model <pinned-model> --pricing <pricing.json> \
  --grc-stage shadow \
  --registry vulnerability=... --registry sec=... --registry hmda=... \
  --macro-approval vulnerability=... --macro-approval sec=... --macro-approval hmda=... \
  --out paper/results/multidomain/pilot/frozen-shadow-actions.json

.venv/bin/guarded-agentic-compaction benchmark pilot <frozen.json> $COMMON \
  --registry vulnerability=... --registry sec=... --registry hmda=... \
  --macro-approval vulnerability=... --macro-approval sec=... --macro-approval hmda=... \
  --action-lock paper/results/multidomain/pilot/frozen-shadow-actions.json \
  --out paper/results/multidomain/pilot --dry-run

.venv/bin/guarded-agentic-compaction benchmark artifact-calibration <frozen.json> $COMMON \
  --registry vulnerability=... --registry sec=... --registry hmda=... \
  --out paper/results/multidomain/artifact-calibration

.venv/bin/guarded-agentic-compaction benchmark calibrate-grc <frozen.json> \
  --ledger vulnerability=<artifact-calibration-ledger> \
  --ledger sec=<artifact-calibration-ledger> \
  --ledger hmda=<artifact-calibration-ledger> \
  --registry vulnerability=<shadow-registry> \
  --registry sec=<shadow-registry> \
  --registry hmda=<shadow-registry> \
  --approved-by <independent-reviewer> --expiry-day <YYYY-MM-DD> \
  --out paper/results/multidomain/calibrated-registries

.venv/bin/guarded-agentic-compaction benchmark freeze-actions <frozen.json> \
  --cases vulnerability=... --cases sec=... --cases hmda=... \
  --pool vulnerability=... --pool sec=... --pool hmda=... \
  --model <pinned-model> --pricing <pricing.json> --grc-stage active \
  --registry vulnerability=... --registry sec=... --registry hmda=... \
  --macro-approval vulnerability=... --macro-approval sec=... --macro-approval hmda=... \
  --out paper/results/multidomain/calibration/frozen-active-actions.json

.venv/bin/guarded-agentic-compaction benchmark portfolio-calibration <frozen.json> $COMMON \
  --registry vulnerability=... --registry sec=... --registry hmda=... \
  --macro-approval vulnerability=... --macro-approval sec=... --macro-approval hmda=... \
  --action-lock paper/results/multidomain/calibration/frozen-active-actions.json \
  --out paper/results/multidomain/portfolio-calibration

.venv/bin/guarded-agentic-compaction benchmark calibrate <frozen.json> \
  --ledger <portfolio-calibration-ledger> \
  --out paper/results/multidomain/calibration/frozen-portfolio.json

.venv/bin/guarded-agentic-compaction benchmark test <frozen.json> $COMMON \
  --registry vulnerability=... --registry sec=... --registry hmda=... \
  --macro-approval vulnerability=... --macro-approval sec=... --macro-approval hmda=... \
  --policy paper/results/multidomain/calibration/frozen-portfolio.json \
  --action-lock paper/results/multidomain/calibration/frozen-active-actions.json \
  --out paper/results/multidomain/test

.venv/bin/guarded-agentic-compaction benchmark analyze <frozen.json> \
  --policy paper/results/multidomain/calibration/frozen-portfolio.json \
  --effort <reviewed-construction-effort.json> \
  --ledger paper/results/multidomain/test/ledger.jsonl \
  --out paper/results/multidomain/analysis
```

Every live phase also accepts `--stop-after-consecutive-failures N` (default 0, which keeps
the historical run-everything behavior). The runner prints one bounded, secret-masked
diagnostic line to stderr per failed attempt; the retained ledger still records only the
exception class. Use the stop so a systematic failure (an SDK misconfiguration, a rejected
credential) costs a handful of attempts rather than the whole schedule; every attempt
stays in the ledger and a later run with the same reservation resumes the open groups.

Replace shell placeholders explicitly; do not store secrets in arguments. The runner refuses mixed
protocol ledgers, duplicate pairs, digest-mismatched retained episodes, ambiguous interrupted
provider attempts, future-dated approvals, incomplete test pairs, a portfolio frozen after the
first test call, or a cap below the maximum retry reservation.
Shadow artifacts can execute only in the pilot and artifact-calibration phases. The
`calibrate-grc` command uses 100 frozen pairs, exact 99% per-domain quality non-inferiority,
Bonferroni control across artifacts, a distinct human approver, and an expiry. Portfolio and test
runs resolve only `ACTIVE` artifacts. Freeze the active action lock after this calibration; once
portfolio calibration starts, any code, prompt, tool, evaluator, registry, approval, model,
pricing, SDK, or source change requires a new protocol rather than an in-place update.
The exact evaluator also requires the complete domain-specific evidence-tool set and validates
each call's snapshot and record identity; merely calling an allowed tool cannot satisfy the source
path contract. The frozen portfolio file is self-digested, and sealed analysis rejects any policy,
action-lock, or per-action identity drift. A global fixed comparator is eligible only when that
same action is available in every domain—there is no hidden per-domain fallback.

## Evidence and interpretation

Each completed execution retains exact oracle fields, tool sequence, action and compatibility
digests, provider trace identity, request/token/tool counts, wall and critical-path latency, and
cost computed from the pinned pricing file. The append-only ledger is hash chained and fsynced.
Analysis uses 100 paired test groups per domain, exact one-sided quality non-inferiority at a five
percentage-point margin and 99% confidence, 10,000 group bootstrap resamples for efficiency,
Holm correction for secondary endpoints, and a preselected 20-group repeat cohort.
The required effort file conforms to `contracts/construction-effort.schema.json`; it makes labor,
review, direct construction cost, recurring monitoring cost, traffic horizons, and break-even
volume explicit rather than treating optimization construction as free.

Current normalized pools and provider-free checks are preflight evidence, not optimization
results. No efficiency, quality-preservation, cost, latency, determinism, or cross-domain policy
claim is valid until the sealed live study has run and `analyze` has reproduced its outputs.
