# Time-forward cohort and end-to-end calibration labels (PR-outcome)

**Status: pre-registered on 2026-10-07 after a provider-free preflight; NOT RUN. Execution
requires an explicit spend authorization (proposed cap $10).** Workstreams A2 and C2 of
`proposal-90.md`, on the one family the fresh pool supports.

## Data

The pinned dataset stops at 2025-06-13. `paper/scripts/github_time_forward_acquire.py` pulled
every `huggingface/datasets` issue and pull request created after that day from the GitHub
REST API with comment bodies (1,095 records; 818 pull requests, 277 issues; snapshot
`paper/results/datasets/github_time_forward/huggingface__datasets/snapshot.parquet`, digest in
`source_manifest.json`). `github_time_forward_preflight.py` removed every record number any
retained result or checkpoint mentions (1,086 fresh) and classed the rest under the families'
own rules:

| Family | Classes in the fresh pool | Reading |
|---|---|---|
| PR-outcome | open 424, merged 315, closed_unmerged 72 | **GO**: a balanced 60-record test set (20 per class) and a calibration set of 132 groups are both coverable |
| Issue-type | enhancement 27 exclusive; no exclusive bug or question labels; 248 other | NO-GO: the repository's label usage changed; the exclusive-category contract cannot be balanced |
| Backlog-attention | owned 6, discussed_unowned 190, awaiting_first_response 79 | NO-GO: the owned class is scarce, as in the retained multiplicity-repair NO-GO |

The two NO-GOs are committed as results. Only PR-outcome proceeds.

## Design (frozen before any outcome)

- **Candidate.** The retained PR-outcome artifact `cand-00-a1de3856bb6c`, program and
  contracts unchanged; one frozen candidate, so m = 1. The manifest's external-state pin is
  re-derived for the new snapshot digest; a changed pin is recorded, never bypassed. If the
  artifact's guard rejects fresh records, those are abstentions and count in coverage.
- **Splits.** From the fresh PR pool, by the family study's stable hash: test = 60 records,
  20 per class; calibration = 132 groups disjoint from test; the rest unused. Both lists are
  written to the result directory before any provider call.
- **End-to-end label (A2).** For every calibration group: dispatch the program on the
  snapshot, run the unchanged continuation once, grade the exact task contract against the
  snapshot record. A contract miss is a violation (k). An interpreter or verifier abstention is
  a clean fallback (not a violation; stays in n). Single pre-registered rule, γ = δ = 0.10,
  α = 0.05: at n = 132, admission needs k ≤ 3 (U = 0.0474 at k = 3; 0.0568 at k = 4). Both
  outcomes are reportable; a retirement names the pool size the observed rate would need.
- **Time-forward evaluation (C2).** On the 60 test records: unchanged agent, retained artifact
  dispatched under its pins, hand-written program; exact contracts, paired, same resource axes
  as the live study. Compiled-only misses are reported first; a guard-clause abstention rate
  above 20% is reported as the price of pins.
- **Model, prompts, grader.** `gpt-5.6-luna`, the family study's prompts and grader, pricing
  pinned in `paper/results/multidomain/pricing/gpt-5.6-luna-2026-10-07.json`.

## Budget

132 continuations plus 60 × 3 evaluation runs at the retained per-record costs is under $0.50;
the cap is **$10** with a per-call reservation and a hard stop. Pilot: ten calibration groups
first.

## Claim boundary

An admission licenses: for this frozen artifact, rule and sampled population (records created
after 2025-06-13 in one repository), the end-to-end task-contract violation rate is at most
0.05 with confidence 0.90, conditional on i.i.d. groups. It is a per-candidate certificate for
one family. The time-forward evaluation licenses preservation on 60 fresh records at observed
coverage, not superiority, and nothing about the two NO-GO families.

## Amendment before execution (2026-10-07, recorded before any provider call)

Inspection of the retained PR-outcome artifact shows its induced verifier carries an enum hull
on `pr.source_revision` whose single value is the pinned snapshot's revision
(`e344be7b…`). On the time-forward snapshot every tool result reports the new snapshot's digest,
so the retained artifact abstains on every fresh record by construction. That is the designed
time-forward behaviour and it is kept as the **C2 arm** (expected coverage 0, reported as such;
the pin is never bypassed). It also means the retained artifact cannot be the A2 candidate:
with no accepted group the certificate would be vacuous. The protocol's migration clause
therefore applies and the design is fixed as follows, before the first call:

- **Three disjoint fresh splits** from the PR pool, by stable hash: test 60 (20 per class),
  discovery 132 (round-robin over classes), calibration 132. The selection file is written
  first and digested.
- **Discovery and re-derivation.** The unchanged agent runs the family's discovery prompt on
  the 132 discovery records (live); the compiler re-derives an artifact from those traces under
  the time-forward snapshot with `freeze_one_candidate_before_calibration = true` (so m = 1),
  through the family study's own `compile_artifact` (its internal 16/8/92 split gives the
  replay-contract gate as in the primary study). If no artifact is admitted, A2 retires at
  compilation and that is the result.
- **A2 end-to-end labels** on the 132 calibration groups, disjoint from discovery and test,
  exactly as written above (single rule, m = 1, admit iff k ≤ 3).
- **C2 time-forward evaluation** on the 60 test records: unchanged agent, re-derived artifact,
  retained artifact under its pins (expected to abstain and fall back), hand-written program.
- Snapshot identity: every tool result and manifest carries the time-forward snapshot's
  digest as `source_revision`; the retained artifact is loaded from its retained registry.
- Budget unchanged (cap $10; pilot of ten calibration groups after discovery). Discovery adds
  about 132 × $0.0007.
