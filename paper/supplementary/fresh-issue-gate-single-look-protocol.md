# Fresh-issue single-look replication of the graded issue gate

**Status: NO-GO, not run (2026-11-06).** The provider-free feasibility preflight found
that the post-cutoff `huggingface/datasets` issue pool cannot supply the planned single
calibration look. No provider call was made and none is authorized by this document;
spend is $0. The design below is retained so that the decision, and what would have to
change to reverse it, are explicit. Evidence: `paper/results/graded_issue_gate_tf/preflight.json`
(recomputed by `paper/scripts/audit_graded_issue_gate_tf.py` into `audit_tf.json`, the table
`paper/iclr/tables/gate_single_look.tex` and the snippet
`paper/iclr/notes/snippets/gate_single_look_paragraph.tex`). Preflight, audit and tests were
committed in `0ce6c5f4072ab082c0973291e7765372aa214984`, which contains no provider code path.

## Purpose

Reviewer 3 asked for a learned-gate versus support-only comparison on a held-out population
and a larger cohort. The existing evidence is the sequential extension
(`paper/results/graded_issue_gate/extension_protocol.md`, `interpretation_correction.md`): 311
pooled calibration groups select eta = 0.50 (261 accepted, 4 errors, nominal U = 0.0443), but the
design was adaptive and mixed-frame, so it is not a certificate. The intended study was a clean
single-look prospective replication of that admission on an independent pool.

## Intended design (not executed)

- **Pool.** Issues (not pull requests) of `paper/results/datasets/github_time_forward/huggingface__datasets/snapshot.parquet`
  (SHA-256 `9b94520f...029b7`, created 2025-06-15 to 2026-10-07) with at least one comment,
  whose number appears in no retained record under `paper/results/` or `experiments/`. Task: the
  graded issue task of `graded_issue_gate_study.py` (final factual contract, six entry
  descriptors); the issue-type category task is NO-GO for the balanced exclusive-category
  contract (`.../preflight.json`).
- **Discovery.** 80 issues chosen by stable hash re-derive the candidate with
  `graded_issue_recompile_candidate.py` bound to the time-forward snapshot (the v2 candidate pins
  the old snapshot and would abstain everywhere).
- **Single look.** Every remaining eligible issue, n fixed by the pool, no extension afterwards.
- **Frozen.** Score, grid `(0.02 ... 0.50)` (eleven points), budgets and model from
  `frozen_gate_v2.json` (SHA-256 `c66af83acac0bc883f970140e874560ef35ff9f80144d0115e13e763d918c35a`);
  alpha = 0.05, delta = 0.10, m = 1, Clopper-Pearson level 1 - delta/11.
- **Age descriptor.** The frozen age is days from creation to the pinned snapshot's last day
  (2025-06-13), clipped at zero, so applied literally every post-cutoff issue has age 0. The
  design would use the time-forward snapshot's own last created day (2026-10-07), the same
  quantity for this snapshot. Chosen before any outcome exists; both conventions are reported in
  the preflight.
- **Primary decision.** The registered grid admits eta = 0.50 iff k <= the exact maximum admissible
  k at the realised accepted count n (`clopper_pearson_upper` of `src/guarded_agentic_compaction/grc/calibrate.py`).
- **Secondary.** Descriptive coverage sweep over the grid and a one-sided Fisher split at eta = 0.02;
  support-only arm (alpha = 1) on the same groups. No test arm. A retirement is a result.
- **Spend.** `--approved-spend-usd 3` (campaign cap $300); expected well under $1.

## Feasibility result (provider-free)

| Quantity | Value |
|---|---|
| Issues in snapshot / with at least one comment | 277 / 197 |
| Markdown link / bare URL / plain text (issues with a comment) | 18 / 46 / 133 |
| Pool after literal exclusion (every `issue_number`/`record_number` under `paper/results/`, `experiments/`) | 111 |
| Pool after the most generous exclusion (same record space only) | 193 |
| Calibration groups after 80 discovery (literal / generous) | 31 / 113 |
| Hard ceiling regardless of exclusion rule (197 - 80) | 117 |
| Floor required by the go rule | about 150 |
| Accepted at eta = 0.50 if all dispatch (generous pool) | 111 |
| Largest admissible k at that count | 0 |
| P(admit) if the true error rate were 1.5% / 2% / 4.4% (generous pool) | 0.18 / 0.11 / 0.01 |

Notes. The literal rule removes 86 issues whose numbers collide with BIRD question ids and with
pandas pull requests (different record spaces); the generous rule removes only the 4 numbers
(7693, 7694, 8029, 8590) that also appear in `experiments/` exclusion lists or other ambiguous
files. Even the generous rule leaves 117 at most, below the floor: the conclusion does not
depend on how the exclusion rule is read. The planning figure of about 275 issues with a comment
in `flip-plans.md` counts all 275 fresh issues; 80 of them have no comment. Mean descriptors,
the six-feature distribution and the acceptance counts per grid point under both age conventions
are in `preflight.json`.

## Decision

**No-go.** At 113 calibration groups the registered grid could admit eta = 0.50 only with zero
errors among about 111 accepted groups (the one-error floor is 133 accepted), roughly an 18%
chance even if the extension's 1.5% error rate held. Under the literal rule the calibration set would be 31 groups, which cannot admit
any grid point (floor 92). Running would spend provider calls on a design that cannot answer
the question, and a single look cannot be repeated. The sequential extension therefore remains the only evidence on this
workload and keeps its exploratory, nominal-only interpretation.

## What would reverse the decision

Any of these is a protocol amendment and needs its own review before a call:
1. A larger fresh pool: re-acquire the repository after 2026-10-07. At the observed rate (about 12
   eligible issues per month) this adds roughly a dozen, not the 35 or more needed.
2. A different repository with comment bodies and a task specification for its labels (about 400
   groups for a two-level design); not safe to improvise.
3. Re-compiling from the retained 80 v2 discovery episodes instead of 80 fresh issues, which would
   leave up to 197 calibration groups. This would need a check that the compiled artifact's only
   dependence on the old snapshot is the source pin, and it is not what the registered design says.
4. Lowering the floor below about 150, which the registered binomial arithmetic does not support.

No change was made to `graded_issue_gate_study.py` or `graded_issue_recompile_candidate.py`:
the `--time-forward` and `--snapshot-dir` modes were not added because no run is authorized.
