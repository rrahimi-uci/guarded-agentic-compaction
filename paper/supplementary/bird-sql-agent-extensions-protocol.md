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

## Amendment during execution (2026-10-08, before the E3 cap was reached)

E3's cap is raised from $45 to $60. At $16.94 spent (standard-design discovery complete,
schema-first discovery under way) the per-episode cost on `claude-sonnet-5` is about $0.03 for
schema-first episodes, which read every table's schema, so the registered cap would stop the
held-out test partway. No design, endpoint, or analysis changes. With E1 spent ($0.84), E2 at most
$10, E3 at most $60, E4 at most $30, and $3.60 spent before registration, the worst case stays
inside the author's $100 authorization.

## Amendment before E4 execution (2026-10-08, before any E4 provider call)

The E4 preflight (`paper/results/bird/train/preflight.json`) pins the train archive
(SHA-256 `66e9e3115b59559554013aa3b124156249f30437a6b4e4f96de3d2dfb5ae8cbc`) and every family
database. The rule selects 27 families. Executing the gold SQL found a data defect: in
`retail_world` the gold SQL fails on 137 of 162 selected questions because it references tables
absent from the shipped database (for example `Order Details` and `EmployeeTerritories`). A
data-quality rule is therefore added before any E4 provider call: a family is excluded when its
gold SQL fails (error or timeout) on more than 10% of its selected questions. It excludes
`retail_world` only, leaving 26 families. In the remaining families the few questions whose gold
fails (`retails`: 3 timeouts; `works_cycles`: 2 errors) count as incorrect in every condition,
so they cannot create a discordant pair. The primary (dev) preflight is unaffected.

## Observed results

### E1. Rotated rerun (spent $0.84)

The four held-out conditions reran on the 150 sealed questions with the primary artifacts and
rotated order; dispatch 150/150; zero failures. Correct: unchanged agent 94, repeat 93,
compiled 100, hand-written prefetch 96. Compiled against the unchanged agent: 7 compiled-only and
1 baseline-only correct (McNemar p = 0.070; difference +4.0 points, interval [+0.7, +8.0]); the
registered "no detected loss" criterion is met and no superiority is claimed. Reductions against
the unchanged agent: requests 46.0% [44.1, 47.9], tokens 12.3% [8.5, 15.8], latency 33.9%
[30.0, 37.7], cost 16.2% [13.6, 18.6]. Cached-input shares were 0.529 / 0.549 / 0.565 / 0.557,
and the repeat run differed from the first by 5.1% in cost (interval [0.7, 9.5]). As predicted,
requests and tokens match the primary run; contrary to the prediction, the cost reduction did not
fall toward 6.3% but stayed near the primary run's cold-baseline 17.5%, so the primary run's
warm-repeat figure was the conservative one.

### E2. Second model family, `gpt-6-luna` (spent $1.14)

Discovery 1,312 runs, zero failures (correct: standard 388/656, schema-first 390/656).
`standard` retires on all five families (four at synthesis; `thrombosis_prediction` with one
candidate at calibration, on support). `schema_first` admits on all five, m = 1, 92/0 gates, clean
strict audit. Held out: one `baseline_repeat` episode timed out (question 595), so pooled
comparisons use the 149 questions with all four conditions; dispatch 149/149 (codebase_community
29 of 29 completed). Correct: unchanged agent 91, repeat 95, compiled 93, hand-written 90.
Compiled against the unchanged agent: 5 compiled-only, 3 baseline-only (McNemar p = 0.73;
difference +1.3 points, interval [-2.0, +5.4]); criterion met. Reductions: requests 49.9%
[48.4, 51.3], tokens 16.8% [13.3, 20.2], latency 38.4% [31.7, 45.1], cost 6.1% [1.1, 10.5].
The repeat run's cached-input share was 0.750 against 0.51-0.58 for the other conditions,
because it repeats the identical input of a question whose first run had just warmed the
provider cache; its cost is therefore not a usable comparator in this run, and every reduction
above is against the rotated first baseline.

### E3. Second provider, `claude-sonnet-5` (spent $28.76)

Discovery 1,311 runs, one infrastructure failure (correct: standard 420/656, schema-first
414/655). **All ten (design, family) pairs retire**, so the plumbing check and held-out test had
nothing to run. The model did not follow either opening as a fixed step: under `standard` it began
with `list_tables` in 162 of 656 runs and passed every table in 2; under `schema_first` it began
with `list_tables` in 429 of 655 and passed every table in 26, otherwise reading a subset it
chose or skipping straight to `get_schema` or `run_query`. Schema-first families retire at
synthesis (`get_schema.table_names` has no consistent expression) or on support. This matches the
registered prediction for a per-question opening and is the cross-provider finding: GAC compiles
what an agent does, not what its prompt asks for.

### E4. Scale, BIRD train split (spent $13.19)

Discovery 6,778 runs over 26 families and two designs, six infrastructure failures (correct:
standard 2,125/3,387, schema-first 2,160/3,391). The run was stopped once at 11:50 and restarted
with higher concurrency (8 to 32) right after a saved checkpoint; at most one just-started batch
(under $0.05) may be missing from the ledger, and no completed result was lost or repeated.

- `standard`: all 26 families retire (no consistent expression for `get_schema.table_names`, or
  too little support).
- `schema_first`: **21 of 26 admit** (m = 1, 92/0 gates, clean strict audit). The five that retire
  are databases where the agent occasionally deviated from the full listing:
  `hockey` (22 tables), `mondial_geo` (34) and `olympics` (11) on calibration support (90 of 92
  matching groups), `movies_4` (17) on support (91 of 92), and `works_cycles` (65) at synthesis
  (the table list varied in 13 of 132 discovery runs).

Held out on the 21 admitted families (rotated order): five infrastructure failures (four API
timeouts in the hand-written arm on `address`; one compiled run on `talkingdata` that hit the
12-turn limit on a question every other condition also answered wrongly, so counting it as a
compiled miss changes no discordant cell). Pooled over the 625 questions with all four
conditions: dispatch 625/625; correct unchanged agent 401, repeat 410, compiled 400, hand-written
404. Compiled against the unchanged agent: 17 compiled-only and 18 baseline-only correct (McNemar
p = 1.0; difference -0.2 points, interval [-1.9, +1.8]); the "no detected loss" criterion is met.
Reductions: requests 45.9% [44.7, 47.0], tokens 12.6% [10.3, 14.7], latency 29.3% [25.6, 32.5],
cost 18.1% [16.7, 19.5]; at uncached prices 14.0% [11.8, 16.1]. The hand-written prefetch reaches
46.0%, 14.2%, 30.7% and 19.7%.

### Cache-neutral cost (all runs)

Pricing every input token at the uncached rate removes provider-cache effects. Cost reductions
of the compiled agent: primary 11.2% [6.1, 15.7] (against the warm repeat), E1 13.9%
[10.4, 17.2], E2 17.5% [14.2, 21.0], E4 14.0% [11.8, 16.1]
(`paper/results/bird/extensions_summary.json`).

### Reading

Across 31 BIRD databases and two OpenAI model families, GAC refused every family where the agent
chose its tables per question (36 of 36 standard-design pairs) and admitted the schema-first
opening wherever the agent executed it as a fixed step (31 of 36 pairs; the five refusals are
databases where the agent occasionally deviated). On 924 held-out questions with a compiled
agent (150 + 149 + 625), dispatch was complete, model requests fell 45 to 50%, latency 29 to 38%,
and cost 11 to 18% at uncached prices, with no detected accuracy loss in any run. On a second
provider whose agent did not follow either opening as a fixed step, GAC refused all ten pairs.
Total extension spend: $43.93.
