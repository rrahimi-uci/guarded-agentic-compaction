# Drift-robustness ablation on recorded GitHub traces (provider-free)

**Status: pre-registered on 2026-10-06, before execution; EXECUTED the same day, provider-free (observed results at the end).** Workstream C1b in the
ICLR revision log. This extends `drift-robustness-ablation-protocol.md` (the simulated
substrate, executed the same day with the pre-declared null) to the three primary live
families' retained held-out records. It changes no compiler code, no artifact, and no
reported number. It is written in full before the driver runs; the "Observed results" section
is appended afterwards and nothing above it is edited.

## What this is and is not

This is a **stress analysis of previously evaluated records**, not a new held-out cohort: the
90 primary held-out records (30 per family) were already evaluated live and their contracts
reported. Here they are re-executed provider-free. The endpoint is the compiled region's
program output, not the model's continuation: a live continuation extension is a separate,
provider-backed protocol and is not part of this one.

The retained evaluation files keep each record's tool sequence and arguments but not its tool
outputs. The tools are deterministic reads of the revision-pinned public
snapshot, so each record's episode is reconstructed exactly as the compiler reconstructs its
discovery episodes (`reconstruct_discovery`: one model boundary per recorded call, tool results
re-executed on the snapshot), and the perturbation suite runs through the same
snapshot-backed sandbox (`SnapshotWorld`) the challenge recompile already uses.

## Arms

| Arm | Program | Guard | Verifier |
|---|---|---|---|
| `compiled_guarded` | the retained admitted artifact's program | induced | induced |
| `compiled_unverified` | identical | induced | permissive `Verifier()` |
| `manual_unverified` | the family's hand-written pre-model plan (`make_manual_plan`), the same `Program` the live `manual_pre_model` condition ran | its manifest pins | permissive `Verifier()` |

The retained artifact is recompiled from its sealed discovery checkpoint through
`recompile_with_challenge.recompile(name, with_challenge=False)` and must be identical to the
retained artifact in id, program and 92/0 gate; a mismatch aborts the family. The hard runtime
boundary (manifest pins, effect catalog, bounded interpretation through `ToolFacade`) is
retained in every arm. `run_perturbations` does not evaluate the hard guard, so guard
differences cannot produce arm differences; only the verifier and the program do.

## Windows

For each family, the 30 held-out records' baseline rows (`condition == "baseline"`, repeat 0)
are reconstructed into episodes; graphs are built under the recompiled artifact's own
groundability policy and configuration; windows are mined with the compiler's window
parameters at support one; the artifact's family is selected by canonical hash; one window per
record (each record is its own group), records in sorted order. A record whose reconstructed
episode yields no window of the family is reported as excluded with its count.

## Perturbations and applicability

The nine declared families of `evaluation/perturb.py`, unchanged. Before the arms run, each
transform is applied to every recorded (tool, arguments, snapshot result) of every window and
the share of calls it actually changes is recorded per perturbation and per tool; a transform
that changes nothing for a tool is a declared no-op and its outcomes for that tool are
reported but excluded from the applicable suite. Injected failures (`tool_4xx`,
`tool_timeout`) are always applicable.

## Endpoints

Primary: the per-record outcome "any `wrong` across the applicable suite", paired across arms.
Secondary: per-perturbation counts, abstention split into program-level and verifier-level,
`invariant`-family abstention rate per arm (the over-abstention guardrail, 0.25 report / 0.50
bar, as in the parent protocol), the hard-reject inventory. Any `sandbox_state_delta` aborts.

## Statistics

Two pre-specified paired comparisons on the per-record primary outcome: (1)
`compiled_guarded` vs `compiled_unverified` (isolates the induced verifier); (2)
`compiled_unverified` vs `manual_unverified` (isolates the program). Exact McNemar on
discordant pairs, Holm-corrected over the two. Zero counts are reported as one-sided 95%
Clopper–Pearson upper bounds. Per family and pooled over the 90 records.

## Decision rule (the parent protocol's, restated)

| Observed | Reading |
|---|---|
| `compiled_guarded` 0 wrong, `compiled_unverified` > 0 wrong | The induced verifier converts wrong answers into abstentions on real recorded tool outputs; report counts, per-family breakdown, McNemar, abstention cost. |
| `compiled_guarded` 0 wrong, `manual_unverified` > 0 wrong, `compiled_unverified` 0 wrong | The program, not the verifier, separates; report as such. |
| All arms 0 wrong | Null: the suite does not separate the arms on these records either. Report the applicability audit so a null caused by no-op transforms is distinguishable from one caused by total tools. |
| `compiled_guarded` > 0 wrong | Adverse; takes precedence; report the record, perturbation and mechanism in full. |
| `invariant` abstention above 0.50 in `compiled_guarded` | No robustness claim regardless of `wrong` counts. |

## Claim boundary

A positive result licenses one statement: on these 90 recorded records under these nine
transforms, the induced contract converts outcomes a contract-free program answers wrongly
into abstentions. It is not a continuation-quality, cost, latency, or production-safety
statement, and the records are not a fresh cohort. A null licenses nothing about the
verifier's value and is not equivalence.

## Reproduction

```bash
.venv/bin/python paper/scripts/drift_recorded_replay_study.py
```

Provider-free; no key, spend authorization, or network access.

## Observed results (executed 2026-10-06, provider-free)

Retained file: `paper/results/drift_recorded_replay/results.json` (`decision: null:all_arms_zero_wrong`).
All three artifacts recompiled identically to the retained ones (ids and 92/0 gates); 30, 30 and
29 held-out records yielded a window of the artifact's family (89 paired records; backlog
record 5189, the baseline-only miss of the live study, yields no window of the family from its
baseline trace and is the one exclusion); the permissive verifier was inert on every
unperturbed window for both programs; no `sandbox_state_delta` in any arm; every one of the
nine transforms changed at least one recorded call per family (the record tools are no-ops
under the list transforms, recorded per tool in `applicability`).

| Endpoint | `compiled_guarded` | `compiled_unverified` | `manual_unverified` |
|---|---|---|---|
| `wrong` outcomes, applicable suite | 0 | 0 | 0 |
| records with any `wrong` (of 89) | 0 (upper bound 0.0331) | 0 (0.0331) | 0 (0.0331) |
| discordant pairs; Holm-adjusted exact McNemar | 0 / 0; p = 1.0 (verifier) | | 0 / 0; p = 1.0 (program) |
| abstention rate on `invariant` families | 0.1049 pooled (0.0444 issue-type, 0.1222 PR-outcome, 0.1494 backlog) | 0 | 0 |

**Reading, per the decision rule: the null, and this time the mechanism is the oracle's scope,
not total tools.** `run_perturbations` judges `wrong` by the program's *decisions*: the
sequence of (tool, derived arguments) it issues, with echoed observations deliberately
excluded, so that a reordered list changes a live-out legitimately but must not change which
record the program selected. Every admitted GitHub program derives every argument from the
entry record number alone; no later call consumes an earlier result. Under this oracle, no
perturbation of tool results can change a decision, so `wrong` is unreachable for these
programs whatever the arm. What the suite does measure here is the contract: the induced
verifier abstains on nulled fields (every record), on duplicated or padded discussion lists
where its hull sees an unexpected cardinality, and on schema drift the interpreter itself
abstains in both compiled arms, while the hand-written program answers through schema drift
unchanged because it echoes whatever it is given. Those abstentions guard the *continuation*
against malformed evidence, which this endpoint does not grade; the live continuation
extension (`drift-continuation-graded-protocol.md`, workstream C1c, capped at $15) is the instrument that would. This is a null,
not equivalence, and it is evidence that the perturbation suite, as an oracle on
entry-grounded programs, cannot exhibit a verifier benefit; a program whose later arguments
derive from earlier results (`last |> project(id)`) is where it could.

## Correction after audit (2026-10-07, same day)

The observed-results text says "no later call consumes an earlier result". The retained
programs bind the record identifier at entry and re-read it from the first record tool's echo
for the later calls, so later calls do consume an earlier result. The conclusion stands for a
narrower reason: the only derived argument is that identifier and none of the nine transforms
alters it, so no tool-result perturbation in this suite can change a decision.
