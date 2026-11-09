# Interior-region census: frontier decomposition (post hoc)

**Status: added 2026-11-08 after `results.json` was read. Descriptive. It does not decide H1 and
changes nothing in the registered protocol (`interior-region-census-protocol.md`, unchanged).**

## Why

Reading the census output and inspecting windows on a subsample suggested that the OpenHands
H1 pass is mostly a consequence of where the prefix frontier falls: the first call of almost
every OpenHands trajectory is the `think` tool, catalogued `PURE` with no capabilities, so it is
non-compilable and ends the read-only opening at call 0. Everything after it is "beyond the
frontier" by the registered definition. This note turns that reading into counts.

## What is computed

On a deterministic hash subsample (same rule as the census, `sha1(episode_id) mod K == 0`;
tau-bench `K=1`, OpenHands `K=16`, SWE-agent `K=64`), under the primary catalog and the projected
live-in policy only:

1. **Frontier event histogram**: which tool (or event kind) ends the read-only opening, under the
   registered frontier definition.
2. **Distance from the frontier**: for the best beyond-frontier groundable region of each
   trajectory, the number of calls between the frontier call and the region's first call
   (distance 1 means the region starts with the call right after the frontier), as a histogram,
   together with the histogram of the absolute start call index. The census reported only
   summary statistics of the latter.
3. **Pass-through frontier**: the registered frontier recomputed with one change: a tool call
   whose catalogued effect is `PURE` (a model-side call with no environment effect) does not end
   the opening and neither does its result. The beyond-frontier groundable share and the largest
   beyond-frontier family support are recomputed against this frontier. The difference between
   the registered and pass-through shares is the part of the H1 pass attributable to the
   placement of `PURE` calls. Windows themselves are unchanged (a window containing a `PURE`
   call is still blocked, as in the census), so this is a hypothetical about where the prefix
   compiler could start, not a new compiler.
4. **Consistency**: on tau-bench (`K=1`, the full corpus) the registered-frontier share must
   reproduce `results.json` exactly.

## Output

`paper/results/interior_census/decomposition.json`, produced by
`python paper/scripts/interior_census.py decompose --source-root <dir>`; the README of the
census reports the numbers and the validator checks the consistency item.
