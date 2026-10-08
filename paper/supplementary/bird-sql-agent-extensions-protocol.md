# BIRD SQL-agent study: extensions (protocol)

**Status:** REGISTERED 2026-10-08, before any provider call of any extension below. The primary
study (`bird-sql-agent-protocol.md`) is executed and unchanged; everything here reuses its design,
tools, prompts, grading, compiler settings, strict audit, and endpoints unless stated. Anything
below "Observed results" is written after execution.

The author authorized $100 for live studies on 2026-10-08; about $3.60 had been spent before this
registration. The caps below sum to $90.

## Why

The primary study admits a live agent's opening on five BIRD dev databases with one model, and its
held-out cost and latency comparison is confounded by a condition-order deviation. Three
questions remain: does the result survive a correctly ordered rerun, a second model family and a
second provider, and many more databases?

## E1. Rotated rerun (dev, `gpt-5.6-luna`), cap $5

Rerun the four held-out conditions on the same 150 sealed questions with the primary run's
admitted artifacts (registries unchanged), with the condition order rotated per question as the
primary protocol registered: in round r, question i runs condition (i + r) mod 4. Endpoints as in
the primary study, now against the first baseline as registered. Both the primary and the rerun
result are reported; neither replaces the other.

## E2. Second model family (dev, `gpt-6-luna`), cap $10

The whole study on `gpt-6-luna`: smoke test (plumbing only), discovery for both designs on the
same discovery questions, compile from that model's own traces, held-out evaluation with rotated
order on every admitted family.

## E3. Second provider (dev, Anthropic `claude-sonnet-5`), cap $45

As E2, through the harness's Anthropic adapter (reasoning effort low, parallel tool calls off,
the same prompts and tools). Before its held-out test, two `compiled` runs on discovery questions
(never held-out questions) check that the compiled calls pass through the adapter; they are
plumbing checks, saved separately, and excluded from analysis.

## E4. Scale (train split, `gpt-5.6-luna`), cap $30

BIRD `train` (CC BY-SA 4.0), archive `https://bird-bench.oss-cn-beijing.aliyuncs.com/train.zip`.
Its SHA-256 and every database's SQLite digest are pinned in the E4 preflight, committed before
any E4 provider call. Train questions carry no ids, so a question's id is its position in
`train.json`. Families: every train database with at least 146 questions (the primary rule).
Splits, both designs, compile, audit, and held-out evaluation (rotated) as in the primary study.

## Predictions (registered)

- `schema_first` admits on every family where the model passes the full listing in every
  calibration group; held-out request reduction near two calls per question with no detected
  accuracy loss.
- `standard` retires wherever the model's table choice varies by question. On a database with very
  few tables the "most relevant" tables may be all of them; any family that admits is tested on its
  held-out questions like the others and reported.
- E1: the request and token reductions match the primary run; the cost reduction against the first
  baseline falls from the confounded 17.5% toward the primary run's warm-baseline 6.3%.

## Claim rules

Per extension and pooled over its admitted families: the primary study's criterion for "no
detected accuracy loss" (compiled minus baseline no worse than -3 points and McNemar p >= 0.05),
otherwise "loss" or "inconclusive". Every family's admission outcome is reported, including
retirements. The main text quotes the primary result; the extensions are summarized in one
sentence there whatever their direction, with full results in the appendix.

## Budget and ledgers

Each extension has its own output directory and spend ledger under `paper/results/bird/`
(`rotated_rerun/`, `replications/gpt-6-luna/`, `replications/claude-sonnet-5/`, `train/`). Live
phases refuse to start a batch whose reservation would exceed the extension's cap.

## Observed results

(Recorded after execution.)
