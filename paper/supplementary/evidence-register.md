# Evidence register

This register prevents claims from drifting beyond the artifacts that support them.

| Claim | Evidence | Status | Boundary |
|---|---|---|---|
| NESTFUL producer candidates contain the gold producer | `results/nestful/results.json` | Verified | 5,531/5,746 slots (96.3% candidate recall); only 4,636/5,746 (80.7%) resolve uniquely |
| Synthesized NESTFUL families avoid recorded wrong replay | NESTFUL `held_out_replay` | Verified on sample | 24 pass, 12 abstain, 0 wrong across 36 windows |
| Recurrence alone satisfies the configured gate | NESTFUL exact-gate record | Contradicted | maximum family support is 26; 92 zero-violation groups are required; no family is certifiable |
| The live study uses real records and provider calls | pinned GitHub snapshot, native trace IDs, token usage | Verified | real public records + deterministic snapshot tools + live OpenAI provider; not the live GitHub service |
| The compiler learned the final fixed prefix | compiler report, splits, artifact | Verified | 16 train, 8 dev, 92 calibration traces; the task prompt prescribes the three calls and their order |
| Calibration observed zero recorded violations | artifact gate record | Verified | 92 configured group records; upper bound 0.0498089 under i.i.d./conditionally i.i.d. assumptions |
| The reported gate discriminates safe from unsafe candidates | score/grid records | Not supported | zero positive dev examples; all 92 groups enter at one threshold; perturbations disabled |
| Provider requests decrease | 18 held-out pairs | Verified on sample | 4 to 1 in every pair; fixed-prefix registered task only |
| Total tokens decrease | 18 held-out pairs | Verified on sample | 3,917.8 to 1,345.2 mean; 65.7% |
| Wall latency decreases | 18 held-out pairs | Verified observation | 10.29 s to 1.55 s under non-randomized batch ordering |
| Estimated cost decreases | frozen price table and token accounting | Verified estimate | 52.6%; not an invoice; price and cache assumptions may change |
| Necessary tool calls decrease | paired result | Contradicted | exactly three in both arms |
| Registered task-contract quality is preserved | 18 held-out pairs | Verified on sample | 18/18 pass in both; one-sided 95% upper bound allows 15.3% population degradation |
| Factual summary quality is preserved | oracle regression tests | Not evaluated | a fluent fabricated summary passes; the oracle checks non-empty length only |
| A free-order prefix recurs without being planted in the prompt | `results/github_natural_live/results.json` | Verified in one task | all 80 discovery runs choose record/labels/comments; requested fields still constrain the evidence shape |
| Free-order exact factuality is preserved | natural-workflow paired result | Not established | baseline 18/18, compiler 17/18, macro 18/18; one compiled-only miss; exact McNemar $p=1$ |
| Natural-workflow provider requests decrease | natural-workflow paired result | Verified on sample | compiler 4 to 1; macro 4 to 2; all six condition orders balanced three times |
| The replay gate certifies downstream model answers | verifier schema and natural factual miss | Contradicted | 45/45 program replays pass, but the compiler records one final-answer miss |
| A separate continuation contract can detect and repair the retained miss | `results/github_natural_live/continuation_replay.json` | Verified counterfactual replay | detects issue 6602, accepts 17/18 unchanged, checked-renders 1/18, and finishes 18/18; zero provider calls, so no live latency/cost claim |
| Expanded free-order replication executes the sealed design | `results/github_natural_replication/results.json` | Verified on sample | 132 discovery, 30 primary and 10 repeated cases per arm; 848 provider responses; no infrastructure failures; real records and live provider |
| Groundability limits the emitted region | expanded compiler report and artifact | Verified | all 132 discovery traces use three reads, but the inconsistent comments limit is ungroundable; compiler rejects that candidate and emits a two-read prefix |
| The implemented optimizer chooses between compilation and retirement | compiler cascade, registry, and runtime fallback | Verified | a surviving artifact may be admitted; otherwise the unchanged agent remains active |
| The region compiler recommends or synthesizes a macro | source and public APIs | Not implemented | GAC remains compile-or-retire; recommendation is a separate portfolio decision and synthesis is absent |
| The implemented portfolio can recommend a measured macro | `src/agent_compaction/portfolio/`, `results/portfolio_live/results.json` | Verified on one family | both measured actions admitted on 30 groups; macro utility 0.489 vs compiler 0.327; recommendation requires human review |
| The portfolio synthesizes macro code | source and prospective result | Not implemented | it selects an externally supplied measured action; no code or application API is generated |
| The selected portfolio action works prospectively | `results/portfolio_live/results.json` | Verified on sample | baseline and selected macro pass 12/12 fresh exact contracts; requests -50.0%, tools -66.7%, tokens -59.2%, latency -71.6%, estimated cost -40.6% |
| Portfolio selection beats always-macro across workflows | one-family pilot | Not established | selected action is the same macro an always-macro policy would choose; no heterogeneous action-optimal families or cache candidate |
| Expanded partial-compilation factuality is preserved | expanded paired result | Verified on sample | baseline, compiler, and macro each pass 30/30 exact factual and full task contracts; zero-event one-sided 95% upper bound remains 9.5% |
| Expanded partial compilation reduces provider work | expanded paired result | Verified on sample | requests 4 to 2, tokens -39.5%, observed wall latency -51.7%, estimated cost -32.0%; tools remain three |
| Expanded macro is the stronger fixed-workflow baseline | expanded macro comparison | Verified on sample | same 2 requests and 30/30 passes; macro uses one tool, 30.9% fewer tokens and 8.0% lower cost than compiler; latency difference is uncertain |
| Expanded semantic regrade preserves provider evidence | `results/github_natural_replication/results.json` oracle revision and discovery checkpoint | Verified | 212 prior quality objects retained; zero provider reruns; answers, tools, tokens, latency, and cost unchanged; checkpoint bound by SHA-256 |
| Natural-language determinism improves | six repeated cases | Not supported | exact-answer agreement 0.17 baseline, 0.00 compiled; sample is inconclusive |
| Hand-written macro comparison is live | both natural-workflow results | Verified on samples | earlier macro passes 18/18; expanded macro passes 30/30 and outperforms the partial compiler on tools, tokens, and cost |
| Offline macro comparison settles the live question | `experiments/results/*.json` | Contradicted | deterministic simulated workload; macro wins request ratio on three of five demos |
| Tier-3 demonstrations use real business records | `experiments/live_results/all_results.json` | Contradicted | live provider, but explicitly fictional deterministic fixtures |
| Prefix position is safety critical | archived pilot and regression | Verified | unsafe suffix dispatch passed only 16.7% of contracts; prefix-only fix is tested |
| Production readiness | no canary/operations evidence | Not established | lab-only artifact promotion; no production service or multi-domain test |
| State-of-the-art superiority | no same-task closest-system head-to-head | Not established | EvoC2F, Agent JIT, GEPA, AWO, caches, and schedulers are literature comparators only |

## Secret handling and provenance

`.env` variable names were inspected, but values were never printed or copied. Live
results store boolean usage flags and `secrets_serialized: false`; the validator scans
publication text/JSON for key-shaped values. The public repository begins from an initial
snapshot created after the experiments; current versioning is available, but pre-snapshot
commit ancestry and CI history cannot be reconstructed.
