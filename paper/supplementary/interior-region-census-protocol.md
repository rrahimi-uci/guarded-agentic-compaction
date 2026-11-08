# Interior-region census protocol (P0 of `gac-expansion.md`)

**Status: registered 2026-11-08 before any count was computed.** Provider-free; no model is
called, nothing is synthesized, calibrated or dispatched. The thresholds below are copied from
`gac-expansion.md` section 0 (H1) and are not changed after the run.

## Question

The paper's prefix census (`paper/results/prefix_census/`, Appendix F.5) measures how often
released agent trajectories *open* with a compilable read-only prefix. The expansion plan's
first hypothesis (H1) is that trajectories also contain recurring, groundable, read-only regions
at **non-initial** boundaries that the prefix-only compiler cannot reach. This census measures
that on the same corpora, with the same catalogs, the same mining parameters and the same
grounding rule, extended in exactly two ways: trajectories are ingested beyond the opening, and
windows may start at any model boundary.

## Corpora

The three released corpora of the prefix census at their pinned revisions
(`paper/results/datasets/{openhands,sweagent,taubench}/source_manifest.json`; every file is
re-verified by SHA-256 before parsing). AppWorld's released baselines are not re-measured: their
logs retain no tool responses, so no interior slot can be grounded, and the checkout is not on
disk at registration time. NESTFUL gold sequences have no model boundaries after the first, so
they have no interior regions by construction and are omitted.

## Ingestion

- Up to **60 tool calls** per trajectory are ingested (`MAX_CALLS_INTERIOR`), in trajectory
  order, with **no catalog barrier stop**: the census must see what lies beyond the first
  barrier. Trajectories longer than 60 calls are truncated and counted (`stopped_by`).
- Deterministic subsample for the two coding corpora, declared here: a trajectory is kept when
  `sha1(episode_id) mod K == 0`. `K` is fixed per corpus by a runtime rule, before any
  interior count is read: a 200-trajectory smoke run measures seconds per trajectory, and `K`
  is the smallest power of two for which the full arm fits in 90 minutes. tau-bench is
  ingested completely (1,980 trajectories). The realized `K`, sample size and the smoke timing
  are recorded in `results.json`.
- Pass 1 (corpus field statistics for the groundability policy) and pass 2 (PATG and windows)
  run over the same sampled trajectories, as in the prefix census.

## Definitions (identical across corpora)

- **Boundary**: a `MODEL_REQ` event. Position 0 is the first boundary. A boundary is
  *interior* if it is not the first.
- **Prefix frontier**: the first event that ends the read-only opening (a non-compilable call,
  a `HANDOFF`, or an error result). A region is *beyond the frontier* if its boundary comes
  after that event. This is the population the prefix-only compiler cannot reach under any
  grounding; it is the **primary H1 population**. Regions at interior boundaries inside an
  all-read opening are reported separately (they are suffixes of an opening the prefix
  compiler could in principle take).
- **Interior read-only run**: from an interior boundary, the number of consecutive compilable
  calls before the next barrier. Reported per trajectory as the maximum run and as the count of
  runs of at least two calls.
- **Interior groundable region**: an Algorithm 2 window (registered parameters: depth 2,
  kappa 3, w in [2,12], b_min 2) whose first event is an interior boundary and in which every
  slot is LITERAL, NOT_GROUNDABLE or GROUNDED, under one of two live-in policies:
  - **strict**: live-ins only from the entry schema (`inputs`), exactly the current
    `_live_in_out` rule; this is what the shipped compiler would do with `prefix_only=False`;
  - **projected**: live-ins may also be values produced by an earlier tool result outside the
    window (the boundary-local projection of `gac-expansion.md` section 5). Each such live-in is
    recorded as `prior:<tool>` and enters the canonical hash.
  Windows containing a write, an unknown effect, a barrier event or an error result are blocked
  as in the prefix census.
- **Families**: canonical hashes of interior windows (one per episode per hash, the largest);
  support is the number of distinct groups (tasks). `n_max` is compared with the 92-group
  zero-violation floor.
- **Savings proxy**: for each kept window, `interior_boundaries` (model requests the region
  would remove). Reported as a distribution, not as a cost estimate.

## Pre-declared thresholds (from `gac-expansion.md` section 0, H1)

H1 **passes** for a corpus if, under the primary catalog and the projected live-in policy,
(a) at least 20% of trajectories have a beyond-frontier groundable region of at least two
calls, and (b) at least one beyond-frontier family has support of at least 92 groups.
Both are required. The strict policy and the sensitivity arms are reported but do not decide.

H1 **fails** if no corpus meets both. The result is reported either way, as a table alongside
the prefix census, and decides between paths A and C of `gac-expansion.md` section 16.

## Sensitivity arms

Exactly the prefix census arms, labelled and never pooled: shell reads admitted
(`shell_reads_admitted`) for the two coding corpora; pre-tool user turns folded
(`pre_tool_user_turns_folded`) for tau-bench.

## What this census cannot show

Prevalence in deployed (non-benchmark) agents; that any interior region is admissible (nothing
is synthesized, replayed or calibrated); that the continuation after a compiled interior region
would be unchanged; or that the groundable share translates into savings (a region's removed
requests are counted, not priced).

## Outputs

`paper/results/interior_census/results.json` (per corpus and arm, with the definitions, the
realized sample rule, timings and the H1 verdict), `paper/results/interior_census/README.md`,
and `paper/iclr/tables/interior_census.tex` generated by
`python paper/scripts/interior_census.py table`. The script is
`paper/scripts/interior_census.py`; its unit tests are `paper/scripts/test_interior_census.py`.
