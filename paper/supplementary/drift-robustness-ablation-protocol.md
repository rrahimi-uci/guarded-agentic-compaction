# Drift-robustness ablation protocol

**Status: pre-registered on 2026-08-18; amended before execution and EXECUTED on 2026-10-06**
(driver `paper/scripts/drift_ablation_study.py`; amendments and observed results at the end).
Original status text: not run, and the driver it describes does not exist yet. This document fixes the design, endpoints, decision rule, and claim boundary before any
implementation, so that whichever way the experiment comes out it can be reported as a result.
It changes no compiler code, no admission gate, no artifact, and no reported number.

## The weakness this targets

The strongest objection to the work is not a missing benchmark. It is that a hand-written
program reaches the same 90/90 exact held-out contracts as the compiled artifact, and is cheaper
on one family. The proposal already concedes this and answers it with **discovery** and
**maintenance** (§6.6): a team with five known hot regions and a stable prompt should write five
functions.

That answer is honest but incomplete, because it is an argument about engineering economics
rather than about behaviour. There is a third difference, and it is behavioural: the compiled
artifact ships with an *induced verifier* and a calibrated abstention path, and a hand-written
function does not. If that difference is real, then under distribution shift the compiled
artifact abstains where the hand-written program silently answers — and silent wrongness is the
one outcome the whole design treats as fatal.

This has never been measured. The offline stress study reports H4 as **not demonstrated**: zero
unsafe dispatches were observed in both conditions, so the two upper bounds differ only through
their denominators, because the simulated tools are deterministic and total, so a memorising or
ambiguous binding still returns a valid record on in-distribution entities. The stated remedy is
to run the ablation against the perturbation suite or a shifted split rather than the
retrospective test split. This protocol is that run.

## What already exists

`evaluation/perturb.py` implements the metamorphic suite as nine families with declared
expectations, and `run_perturbations` already produces the exact endpoint this experiment needs:

| Expectation | Families | Verdict rule |
|---|---|---|
| `invariant` | `reorder_lists`, `duplicate_record`, `formatting` | live-outs must match the unperturbed run of the same program on the same episode; a mismatch is counted `wrong` and recorded as a hard reject |
| `abstain` | `empty_lists`, `null_fields`, `schema_drift`, `tool_4xx`, `tool_timeout` | an answer that differs from the unperturbed one is counted `wrong`; abstaining, or reproducing the unperturbed answer, passes |
| `either` | `pad_lists` | either outcome passes |

The oracle is the unperturbed run of the same program, so no domain knowledge and no new
labelling are required. `Verifier()` constructed with no clauses, no allowed effects, and no call
counts is permissive by definition — it returns no reasons — which is exactly the arm that
represents a program with no induced contract. `ManualPreModelPlan` already carries a `Program`
in the same IR as a compiled artifact, so the same suite can be pointed at it.

## Conditions

Three arms over the same programs, episodes, and perturbations. Only the contract changes.

| Arm | Program | Guard | Verifier |
|---|---|---|---|
| `compiled_guarded` | synthesized | induced | induced |
| `compiled_unverified` | synthesized, identical | induced | permissive `Verifier()` |
| `manual_unverified` | hand-written pre-model plan | induced-equivalent manifest pins | permissive `Verifier()` |

The three-arm shape is the point. `compiled_guarded` vs `compiled_unverified` isolates the
*induced verifier* on a fixed program, which is the compiler's own contribution.
`compiled_unverified` vs `manual_unverified` isolates the *program*. Comparing only the full
system against a bare hand-written function would confound the two.

The runtime hard boundary — manifest identity pins, the effect catalog and read-only allowlist,
bounded non-dynamic interpretation through `ToolFacade` — is deliberately retained in all three
arms. A hand-written macro in this repository already gets that boundary; removing it would
manufacture a difference that the design does not claim. The contrast under test is
verifier-versus-no-verifier, not sandbox-versus-no-sandbox.

## Substrate

The five deterministic demonstration workloads (`support`, `permissioned_rag`,
`incident_triage`, `mcp_ops`, `fulfillment`), because they are provider-free, already carry
hand-written comparators, and are the substrate on which H4 was left unscored. Every arm runs on
the same sealed windows with the same `max_windows` cap of 24 per family that the
pre-registration already fixes.

This is a simulated substrate. Nothing here becomes a provider measurement, a real-record claim,
or evidence about the three GitHub workflow families. A confirmatory run on the GitHub recorded
traces would be a separate, recorded-replay-only extension and is not part of this protocol.

## Endpoints

**Primary.** The count of `wrong` outcomes per arm, pooled over the nine families and reported
per family. `wrong` means an invariance violation or an answer that differs from the unperturbed
answer where abstention was required. Pre-declared expectation: `compiled_guarded` produces
zero; at least one other arm does not.

**Secondary.**

1. Abstention rate per arm per family, split into program-level (`abstained`) and
   contract-level (`verifier_abstained`), so the verifier's share is visible.
2. Pass rate on `invariant` families per arm.
3. Hard-reject inventory, including any `sandbox_state_delta`, which is fatal in any arm.

**Guardrail endpoint — over-abstention.** Abstaining on everything is not robustness. The
`compiled_guarded` arm's abstention rate on the three `invariant` families is reported as a cost
alongside the primary endpoint. An `invariant`-family abstention rate above 0.25 must be
reported in the same sentence as the primary result, and a rate above 0.50 means the arm is too
conservative to be called robust regardless of its `wrong` count.

## Statistics

Per-episode outcomes are paired across arms by construction, so the primary contrast uses the
exact McNemar test on discordant pairs, one test per arm comparison, with the two comparisons
Holm-corrected. Zero-observed rates are reported as exact Clopper–Pearson upper bounds and never
as averages, following the convention already used for the safety endpoints; with 24 windows per
family the bound on a zero count is wide, and the protocol commits to printing it rather than
implying that zero means zero.

## Decision rule

| Observed | Reading |
|---|---|
| `compiled_guarded` 0 wrong, `manual_unverified` > 0 wrong, over-abstention within bound | The claim holds. Report exact counts, the per-family breakdown, the McNemar result, and the abstention cost. This is the argument the paper currently lacks. |
| `compiled_guarded` 0, `compiled_unverified` > 0 | Stronger and more specific: the induced verifier, not the program, is what protects. Report as the headline of the ablation. |
| All arms 0 wrong | Null. The perturbation suite as configured does not separate the arms on this substrate. Report as a null and state the reason — most likely that the simulated tools remain total under these transforms — without reframing it as support for either side. |
| `compiled_guarded` > 0 wrong | Adverse, and it takes precedence over everything else here. A silently wrong compiled dispatch under shift is the failure mode the design exists to prevent; report the family, the episode count, and the mechanism in full. |
| Over-abstention above 0.50 on `invariant` families | The robustness claim is not made, whatever the `wrong` counts show. |

A null is a realistic outcome and is the reason this protocol is written first. Two mechanisms
could produce one: the deterministic fixtures may stay total under all nine transforms, and the
retained hard boundary may catch the same cases in every arm.

## Preconditions, to be fail-closed in the driver

1. Every window must have a usable unperturbed oracle; windows recorded `no_reference` are
   excluded with their count stated, never silently dropped.
2. Any `sandbox_state_delta`, in any arm, aborts the run rather than being averaged away.
3. The three arms must run over identical window sets in identical order; a mismatch aborts.
4. The permissive verifier must be verified inert on the unperturbed run — it must return no
   reasons — so that arm differences cannot come from a misconfigured contract.
5. No arm may be re-run with different parameters after the counts are seen. The `max_windows`
   cap, the perturbation list, and the substrate are fixed by this document.

## Implementation, not yet written

One driver, provider-free, reusing what exists:

- `paper/scripts/drift_ablation_study.py`: for each demonstration, load the sealed windows,
  the synthesized program with its induced guard and verifier, and the hand-written comparator's
  `Program`; call `run_perturbations` three times with the three contract configurations; write
  one artifact under `paper/results/drift_ablation/` carrying per-arm, per-family counts, the
  McNemar results, the abstention costs, and the hard-reject inventory.
- A permissive-contract helper and a test asserting it is inert on unperturbed runs.
- A validator function plus an integration test pinning the recorded counts, matching how the
  other sealed studies are checked.

Estimated cost: about a day, no provider spend, no new dependency, no network access.

## Claim boundary

If the experiment succeeds it licenses exactly one new statement: that on this simulated
substrate, under these nine declared perturbation families, the induced contract converts
outcomes that a program without one answers wrongly into abstentions. That is a statement about
the contract, not about tokens, cost, latency, task quality, real workloads, or production
safety. It does not establish that hand-written programs are unsafe in general, that this
substrate's shift resembles production drift, or that the compiled artifact would abstain
correctly under shifts outside the suite.

## Reproduction

To be filled in with the exact command when the driver exists. The intended shape:

```bash
.venv/bin/python paper/scripts/drift_ablation_study.py --demo support --demo permissioned_rag \
  --demo incident_triage --demo mcp_ops --demo fulfillment
```

No provider key, no spend authorization, and no network access are required.

## Amendments before execution (2026-10-06)

Recorded before any outcome other than the `support` smoke run described in item 4 was seen.

1. **Arms.** The `manual_unverified` arm is not run on this substrate. The protocol assumed
   `ManualPreModelPlan` carries an IR `Program` the suite can execute; the demonstration
   comparators are policy-level macros (`DemoSpec.macro_tool`, invoked by the policy with
   arguments derived from earlier observations), not IR programs. Authoring one IR program per
   demonstration is a separate deliverable and would introduce an author-bias risk the design
   does not control. The principal contrast, `compiled_guarded` versus `compiled_unverified` on an
   identical program, is unaffected and is the only comparison run, so there is one exact McNemar
   test and no Holm correction.
2. **Unit of analysis.** Repeated perturbations of one window are not independent observations.
   The primary outcome is defined per group: `wrong` on any applicable perturbation of that
   group's window (`no_reference` excluded). Arms are paired at group level. Per-transform counts
   are reported descriptively.
3. **Windows.** The sealed test split's windows for each admitted artifact's family are mined
   under the artifact's partition's train-fitted groundability policy with the compiler's own
   window parameters, exactly as the compiler attaches held-in windows. The compile is
   reproduced from the retained seed and splits (digest checked against
   `experiments/results/<demo>.json`) and the admitted families are compared with the retained
   ones at family-hash and partition level; rank indices may differ between compiler versions
   and are recorded, not treated as a mismatch.
4. **Sampling.** The `support` smoke run with the first 24 windows in sorted order covered only
   6 groups. The sample is therefore one window per group, groups in sorted order, capped at 24,
   so each artifact contributes up to 24 paired groups. This was decided after that smoke run
   (a null) and before any other demonstration was run.
5. **Reproducibility finding, reported as such.** `incident_triage` admits no artifact under the
   current compiler (the 2026-08-02 retained run admitted two: `cand-00-9452e5778bf6`,
   `cand-01-c294df28f7a6`), and one of `permissioned_rag`'s five retained artifacts
   (`cand-08-307b5bb36789-51a098b9`) is no longer admitted. `mcp_ops` retires in both runs. The
   study runs on what the current compiler admits; the divergence is a finding about the
   demonstration suite's reproducibility, not about this protocol.

## Observed results (executed 2026-10-06, provider-free)

Retained file: `paper/results/drift_ablation/results.json`
(`decision: null:all_arms_zero_wrong`). Six artifacts over three demonstrations completed
(`support` 1, `permissioned_rag` 4, `fulfillment` 1), 24 paired groups each, 144 paired
groups in all; the permissive verifier was inert on every unperturbed window; no
`sandbox_state_delta` in any arm.

| Endpoint | `compiled_guarded` | `compiled_unverified` |
|---|---|---|
| `wrong` outcomes, all perturbations | 0 | 0 |
| groups with any `wrong` (of 144) | 0 (one-sided 95% upper bound 0.0206) | 0 (upper bound 0.0206) |
| discordant pairs (guarded-only / unverified-only) | 0 / 0 (exact McNemar p = 1.0) | |
| abstention rate on the three `invariant` families | 0.2477 pooled; 0.3333 on each `permissioned_rag` artifact, 0.0694 `support`, 0.0833 `fulfillment` | 0.0000 |

**Reading, per the decision rule: the null.** All arms produce zero `wrong` outcomes, so the
perturbation suite as configured does not separate the arms on this substrate. The mechanism is
the one the protocol anticipated: the simulated tools remain total under these transforms, and
the unverified program's live-outs under `null_fields`, `duplicate_record`, `pad_lists` and
`schema_drift` equal its unperturbed live-outs, so there is no wrong answer for a verifier to
prevent. What the induced verifier does on this substrate is abstain, including on `invariant`
families where the answer was unchanged; on `permissioned_rag` that rate (0.3333) exceeds the
0.25 guardrail and is reported in the same sentence as the primary result, and it is below the
0.50 bar at which the arm would be called too conservative. This is a null, not equivalence,
and it licenses no statement about real workloads, the GitHub families, tokens, cost, or
production safety. A recorded-replay extension on real records is the separate protocol
recorded as workstream C1b in the ICLR revision log.
