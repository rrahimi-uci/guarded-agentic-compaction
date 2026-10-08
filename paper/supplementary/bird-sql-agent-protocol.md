# BIRD SQL-agent study: compile-or-retire on a public benchmark (protocol)

**Status:** REGISTERED 2026-10-08, before any provider call. The registration is the git commit
that adds this file together with `paper/scripts/bird_sql_agent_study.py` and
`paper/results/bird/preflight.json`. Anything below the "Observed results" heading is written
after execution and does not change the design.

## Question

The paper's four public benchmarks give no live savings result: three are too small for the
92-group floor and the fourth (AppWorld) admits a program built from reference solutions, not
agent runs. This study asks whether GAC finds, admits, and safely dispatches a compiled opening
for a live tool-using agent on a public benchmark large enough for the floor, and whether it
refuses where the opening is a per-question decision.

## Data

- BIRD dev, release `dev_20240627` (CC BY-SA 4.0), archive
  `https://bird-bench.oss-cn-beijing.aliyuncs.com/dev.zip`, SHA-256
  `cdd6d19faeb45a23970b98d3ef6c40a87987c95459c2cf12076897a60cf5a630`. The archive and its
  extraction live in the ignored cache `benchmarks/.cache/bird/`; every database's SQLite
  SHA-256 is pinned in `preflight.json`.
- **Families (rule fixed before data was inspected for behavior):** every dev database with at
  least 146 questions (16 train + 8 dev + 92 calibration + 30 held out). The rule selects
  `card_games` (191), `codebase_community` (186), `formula_1` (174), `thrombosis_prediction`
  (163), and `student_club` (158).
- **Splits:** per family, questions ranked by SHA-256 of `bird-split:20261008:<db>:<question_id>`;
  the first 30 are the sealed held-out set; the next up to 132 are discovery
  (`student_club` has 128). Splits are recorded with digests in `preflight.json`.
- **Gold:** the BIRD gold SQL executed provider-free; every gold query in the families executes
  within the 30 s grading timeout.

## Agent and tools

- Model `gpt-5.6-luna` through the OpenAI Agents SDK with the paper's pinned settings
  (reasoning effort low, verbosity low, parallel tool calls off, `store=False`), at most 12 turns,
  180 s per episode, no retries.
- Tools over the pinned SQLite file opened `mode=ro&immutable=1` (a write probe is refused, see
  `preflight.json`): `list_tables()` returns the table names as a JSON array;
  `get_schema(table_names: list[str])` returns each named table's CREATE statement, columns, and
  three sample rows (values cut at 100 characters); `run_query(sql)` returns at most 20 rows with
  a 15 s timeout. All three are declared `READ_LOCAL`, speculatable, and replayable.
- Input: database name, question, and BIRD's evidence string (the standard "with evidence"
  setting). Output: a structured `{"sql": ...}`.
- **Two agent designs, both registered here, prompts frozen in the script (digests in
  `preflight.json`):**
  - `standard`: adapted from LangChain's SQL-agent prompt; "look at the tables in the database
    to see what you can query. Then you should query the schema of the most relevant tables."
  - `schema_first`: identical except the workflow step reads "Begin by listing the tables in the
    database. Then read the schema of every table in the database. Only then write and test your
    query." This mirrors the paper's prescribed task design; the argument passed to
    `get_schema` is left to the model.

## Contract and grading

BIRD execution accuracy: the final SQL is executed with a 30 s timeout and is correct when its
result, as a set of row tuples, equals the gold result's set. Errors and timeouts are incorrect.

## Procedure

1. **Preflight (provider-free):** data digests, families, splits, gold results, read-only probe,
   tool determinism, prompt digests.
2. **Smoke test (live, excluded from all analysis):** three questions per design on two
   non-family databases (`california_schools`, `superhero`) to verify plumbing. Prompts and
   settings are frozen before it runs and are not changed on the basis of its behavior.
3. **Discovery (live):** the unchanged agent, one run per discovery question per design.
4. **Compile (provider-free), per (design, family):**
   - QUALIFY keeps completed runs with a structured answer and a valid trace. **Answer
     correctness is not a filter** (the expert review showed a correctness filter can remove
     exactly the route-deviating groups).
   - A stable hash (`bird-compile-split:20261008:<design>:<db>:<question_id>`) draws 16 train,
     8 dev, and 92 calibration groups from the qualified traces.
   - The compiler runs with the paper's registered settings: alpha = 0.05, delta = 0.10, the
     11-point grid, `w_min = 2`, `w_max = 3`, `b_min = 2`, `s_min = 5`, prefix-only. `min_days = 1`
     because BIRD questions carry no dates (day is the constant 2024-06-27). Composite synthesis
     is off; dispatch emits the compiled calls one per model boundary through `CompactingModel`.
   - The number of candidates reaching calibration (m) is reported and sets the certificate
     level as in the paper.
   - **Strict argument audit (veto).** For every calibration group, the agent's recorded opening
     calls are compared with the calls the admitted program derives. The compiler labels a group
     whose recording lacks the program's call as unproductive, which stays in the count; at
     runtime the program would have run. Any disagreement therefore vetoes the admission claim
     for that family, whatever the compiler decided.
5. **Held-out evaluation (live), only for families admitted and passing the audit:** four
   conditions on the 30 sealed questions: `baseline` (unchanged agent), `baseline_repeat` (a
   second independent run, measuring the agent's own run-to-run variation),
   `compiled` (`CompactingModel`, live dispatch), and `manual_schema_prefetch` (hand-written:
   the runtime lists the tables and reads every schema before the first request and passes both
   in the input; tools stay available). Condition order rotates by record.

## Endpoints

- **Admission:** per (design, family): admitted, retired (and at which stage), m, and the
  strict-audit result.
- **Resources (admitted families):** reductions in model requests, tokens, latency, and cost
  against `baseline`, with paired bootstrap 95% intervals; dispatch rate.
- **Preservation:** pooled paired execution accuracy, compiled against baseline: correct
  counts, discordant cells, exact McNemar p, and the accuracy difference with a bootstrap 95%
  interval. The same statistics for `baseline_repeat` against `baseline` give the noise floor.
  The claim "no detected accuracy loss" is made only if the compiled-minus-baseline difference
  is no worse than -3 points and McNemar p >= 0.05; otherwise the result is reported as a loss
  or as inconclusive. This is not an equivalence claim.

## Predictions (registered)

- `schema_first`: the compiler admits the two-call opening `list_tables -> get_schema(every
  listed table)` on families where the agent passes the listed tables back unchanged, with
  `table_names` grounded in the listing; request reduction near two requests per episode, token
  reduction smaller, because the removed requests carry the shortest contexts.
- `standard`: where the agent's table choice depends on the question, `get_schema.table_names`
  has no consistent expression and the family retires at synthesis (`ungroundable_slot`); the
  one-call `list_tables` prefix removes one request and is below `b_min = 2`, so it is not
  emitted.
- Either way, every outcome, including retirement of every family, is reported.

## Budget

Live phases refuse to run without an approved cap; every result's estimated cost (list price) is
ledgered in `paper/results/bird/ledger.json`. Cap: **$25**, inside the $50 the author authorized
for live studies on 2026-10-07. Expected spend is about $12 (roughly 2,500 episodes).

## Claim boundary

One model, one public benchmark split, five databases, 30 held-out questions per admitted
family. BIRD dev may appear in model pretraining; that affects every condition equally and the
endpoints are paired. Not a leaderboard submission. The certificate is the paper's replay-
contract certificate, which here has real support: an agent that passes a different table list
produces an observable disagreement.

## Observed results

(Recorded after execution.)
