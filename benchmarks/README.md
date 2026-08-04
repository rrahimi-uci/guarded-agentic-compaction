# Real-record multidomain benchmark

This benchmark implements the prospective study in [`extension-plan.md`](../extension-plan.md).
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
records, and paper study drivers are repository artifacts, so `agent-compaction benchmark ...`
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
.venv/bin/agent-compaction benchmark preflight \
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

.venv/bin/agent-compaction benchmark freeze \
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
.venv/bin/agent-compaction benchmark prepare-macro-review \
  --pool vulnerability=paper/results/multidomain/preflight/vulnerability \
  --pool hmda=paper/results/multidomain/preflight/hmda \
  --out paper/results/multidomain/review/macro-review-materials.json
```

Add the SEC pool argument after that real pool exists; the retained checkpoint explicitly lists
SEC as unavailable rather than fabricating a review result.

Every live command supports `--dry-run`, which writes the exact counterbalanced schedule and the
maximum model-request and reservation bounds without loading `.env` or invoking a provider:

```bash
COMMON='--cases vulnerability=... --cases sec=... --cases hmda=... \
--pool vulnerability=... --pool sec=... --pool hmda=... \
--model <pinned-model> --pricing <pricing.json> \
--max-provider-usd <approved-cap> \
--reservation-usd-per-execution <conservative-reservation>'

.venv/bin/agent-compaction benchmark discovery <frozen.json> $COMMON \
  --out paper/results/multidomain/discovery
.venv/bin/agent-compaction benchmark development <frozen.json> $COMMON \
  --out paper/results/multidomain/development

.venv/bin/agent-compaction benchmark compile-grc <frozen.json> \
  --ledger vulnerability=<discovery-ledger> --ledger vulnerability=<development-ledger> \
  --ledger sec=<discovery-ledger> --ledger sec=<development-ledger> \
  --ledger hmda=<discovery-ledger> --ledger hmda=<development-ledger> \
  --out paper/results/multidomain/registries

.venv/bin/agent-compaction benchmark freeze-actions <frozen.json> \
  --cases vulnerability=... --cases sec=... --cases hmda=... \
  --pool vulnerability=... --pool sec=... --pool hmda=... \
  --model <pinned-model> --pricing <pricing.json> \
  --grc-stage shadow \
  --registry vulnerability=... --registry sec=... --registry hmda=... \
  --macro-approval vulnerability=... --macro-approval sec=... --macro-approval hmda=... \
  --out paper/results/multidomain/pilot/frozen-shadow-actions.json

.venv/bin/agent-compaction benchmark pilot <frozen.json> $COMMON \
  --registry vulnerability=... --registry sec=... --registry hmda=... \
  --macro-approval vulnerability=... --macro-approval sec=... --macro-approval hmda=... \
  --action-lock paper/results/multidomain/pilot/frozen-shadow-actions.json \
  --out paper/results/multidomain/pilot --dry-run

.venv/bin/agent-compaction benchmark artifact-calibration <frozen.json> $COMMON \
  --registry vulnerability=... --registry sec=... --registry hmda=... \
  --out paper/results/multidomain/artifact-calibration

.venv/bin/agent-compaction benchmark calibrate-grc <frozen.json> \
  --ledger vulnerability=<artifact-calibration-ledger> \
  --ledger sec=<artifact-calibration-ledger> \
  --ledger hmda=<artifact-calibration-ledger> \
  --registry vulnerability=<shadow-registry> \
  --registry sec=<shadow-registry> \
  --registry hmda=<shadow-registry> \
  --approved-by <independent-reviewer> --expiry-day <YYYY-MM-DD> \
  --out paper/results/multidomain/calibrated-registries

.venv/bin/agent-compaction benchmark freeze-actions <frozen.json> \
  --cases vulnerability=... --cases sec=... --cases hmda=... \
  --pool vulnerability=... --pool sec=... --pool hmda=... \
  --model <pinned-model> --pricing <pricing.json> --grc-stage active \
  --registry vulnerability=... --registry sec=... --registry hmda=... \
  --macro-approval vulnerability=... --macro-approval sec=... --macro-approval hmda=... \
  --out paper/results/multidomain/calibration/frozen-active-actions.json

.venv/bin/agent-compaction benchmark portfolio-calibration <frozen.json> $COMMON \
  --registry vulnerability=... --registry sec=... --registry hmda=... \
  --macro-approval vulnerability=... --macro-approval sec=... --macro-approval hmda=... \
  --action-lock paper/results/multidomain/calibration/frozen-active-actions.json \
  --out paper/results/multidomain/portfolio-calibration

.venv/bin/agent-compaction benchmark calibrate <frozen.json> \
  --ledger <portfolio-calibration-ledger> \
  --out paper/results/multidomain/calibration/frozen-portfolio.json

.venv/bin/agent-compaction benchmark test <frozen.json> $COMMON \
  --registry vulnerability=... --registry sec=... --registry hmda=... \
  --macro-approval vulnerability=... --macro-approval sec=... --macro-approval hmda=... \
  --policy paper/results/multidomain/calibration/frozen-portfolio.json \
  --action-lock paper/results/multidomain/calibration/frozen-active-actions.json \
  --out paper/results/multidomain/test

.venv/bin/agent-compaction benchmark analyze <frozen.json> \
  --policy paper/results/multidomain/calibration/frozen-portfolio.json \
  --effort <reviewed-construction-effort.json> \
  --ledger paper/results/multidomain/test/ledger.jsonl \
  --out paper/results/multidomain/analysis
```

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
