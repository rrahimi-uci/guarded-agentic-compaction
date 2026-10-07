# Simulated demonstration suite, regenerated 2026-10-07 under the current compiler

`experiments/results/` is the immutable 2026-08-02 run of `experiments/run.py` and is left
untouched. This directory is the same command, same seed (20260801), same declared episode
counts, re-run on 2026-10-07 against the compiler as it stands after the position invariant
(`GrcConfig.prefix_only`, adopted after the archived suffix-dispatch pilot fault; `paper/iclr`
§2, Eq. 2) and the later library changes.

| Demonstration | 2026-08-02: GRC artifacts / TGWS leaves / request ratio / co-primary | 2026-10-07 |
|---|---|---|
| support | 1 / 0 / 0.755 / pass | identical |
| permissioned_rag | 4 / 4 / 0.718 / pass | identical |
| incident_triage | 2 / 1 / 0.780 / pass | **0 / 1 / 0.956 / fail** |
| mcp_ops (negative control) | 0 / 0 / 1.000 / fail | identical |
| fulfillment | 1 / 1 / 0.642 / pass | identical |

The one change is a design consequence, not a regression: every recurrent region of
`incident_triage` begins after a model boundary that is not the first, so the position
invariant blocks all of them as `non_prefix_runtime` (1,082 windows) and the compiler
correctly retires where the August compiler admitted two artifacts. The August numbers were
produced before the invariant existed and are reported in `docs/results.md` as that run; this
directory is the reproduction an artifact reviewer will obtain today. No ICLR manuscript number
depends on either run (the ICLR demo table reads the live Tier-3 file
`experiments/live_results/all_results.json`).

Discovered while running the drift-robustness ablation (`paper/results/drift_ablation/`),
whose compile reproduction check first exposed the divergence.
