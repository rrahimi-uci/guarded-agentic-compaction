# Gate-frontier pilot protocol

**Status: PREFLIGHT SEALED, NOT EXECUTED.** The held-out and calibration/development
cohorts below are drawn and hashed (`paper/results/gate_frontier_pilot/preflight.json`),
zero provider calls have been made, and no compiler artifact has been produced from them.
This document commits the design, the risk stratification, and the decision rule before
any live evidence exists, exactly as `bfcl-compiler-protocol.md` and
`appworld-compiler-protocol.md` do for their substrates. Execution requires separate,
explicit authorization to spend provider budget; this document does not authorize that
spend.

This is a **pilot** for the first phase of
[`prospective-gate-frontier-protocol.md`](prospective-gate-frontier-protocol.md), not a
replacement for it. Its purpose is narrower and cheaper: check whether a risk–coverage
frontier is reachable at all on this repository's task shape before committing to that
protocol's full ≥3-domain, ≥300-pair design. At 90 records it cannot reach the 92
zero-violation groups the registered gate requires and is not expected to. A clean
qualitative signal here — dispatch or violation concentrating by stratum — is the go
signal for the full study; a flat result across strata is a no-go, reported as such.

## Why a pilot was needed before the full study

Every registered exact-α=.05 gate in this paper is step-like
(`gate-selectivity-analysis.md`): five of six admit all or none of their calibration
groups. Two structural reasons, not a statistical one, plausibly explain this on the
existing primary families:

1. **The eligibility filter removes the hard cases.** `issue_type`'s classifier
   (`category_for` in `github_live_study.py`) requires exactly one of `bug`/`enhancement`/
   `question` to be present; multi-label or unlabeled records fall to `other` and, in the
   primary study, are filtered out before the gate ever sees them.
2. **The quality oracle checks contract shape, not a fact that can diverge.** Category and
   issue-number checks are deterministic functions of the same evidence the compiled
   program reads, so a compiled program computing the same function cannot register a
   violation on an eligible record by construction (`test_oracle_weakness.py` makes this
   claim falsifiable and it currently holds).

Neither limitation is universal, though. The **natural-order study**
(`github_natural_workflow_study.py`) admits `other`-category records and its
`grade_factual` oracle checks `comment_grounded`: whether the returned `comment_evidence`
is a verbatim substring of a real source comment. That check is not merely theoretical —
it has already caught a real violation. The sealed record for issue 6602
(`paper/results/github_natural_live/continuation_replay.json`) shows the compiled arm's
original answer failing `comment_evidence:mismatch`, later corrected by continuation
replay. The cause is visible in the source data: the issue's first comment contains a
Markdown link, `[mteb/stackexchange-clustering](https://huggingface.co/datasets/mteb/stackexchange-clustering)`,
and the compiled arm's excerpt did not reproduce it exactly.

That is one documented case, not a proof, but it is the only concrete mechanism this
codebase has ever recorded by which a compiled artifact's evidence can diverge from the
source on this task family. This pilot stratifies on it directly rather than guessing at
a different feature.

## Risk stratification

For each candidate record, the first three non-empty comments are checked for a Markdown
link (link text in square brackets immediately followed by a parenthesized URL) or a bare
URL, in that precedence order:

| Stratum | Pattern | Hypothesis |
|---|---|---|
| `markdown_link` | link text, then `(https?://...)` | Highest risk: this is the exact pattern issue 6602 failed on. |
| `bare_url` | a bare `https?://` URL present, no Markdown link | Intermediate risk: still a substring the compiled arm's excerpt could truncate or reformat. |
| `plain_text` | neither pattern | Baseline: no known mechanism for `comment_grounded` to fail. |

The predeclared expectation is that `comment_grounded` violations, if any appear, are not
uniform across strata: they should concentrate in `markdown_link`, then `bare_url`, and be
rare or absent in `plain_text`. This is exactly the shape a genuine risk–coverage frontier
needs — the population is not homogeneous, so a calibrated score has something to
discriminate.

## Cohort

Sealed in `paper/results/gate_frontier_pilot/preflight.json`, drawn from the same
pinned 7,540-record `helmo/github-issues` snapshot every primary GitHub family already
uses (`paper/results/datasets/github_issues/`), so no new data acquisition is required.

- **Exclusion.** Every `issue_number`/`record_number` appearing anywhere under
  `paper/results/` (excluding external benchmarks, which do not share this record space)
  is excluded before selection. 2,475 records were excluded on this basis; 5,804 remain
  eligible after also requiring the record to be a plain issue (not a pull request) with
  at least one comment, so `comment_grounded` is exercised rather than trivially satisfied
  by the empty-comment `"none"` sentinel.
- **Selection.** 30 records drawn per stratum (90 total) by a seeded shuffle (seed
  `20260822`), split roughly in half into a held-out test set (45) and a
  calibration/development set (45). Strata sizes in the eligible pool before selection:
  `plain_text` 983, `bare_url` 585, `markdown_link` 290 — comfortably above 30 in every
  stratum, so 30-per-stratum is not scraping the bottom of an exhausted pool.
- **Category mix.** The selected 90 records span `bug`, `enhancement`, and `other`
  (`question` did not appear in this particular draw, consistent with its lower base rate
  in the snapshot); this is incidental to stratification, not separately controlled.

## What runs, if authorized

No discovery or mining phase is needed: the recurrent `record -> labels -> comments`
program for this family already exists and is validated
(`github_natural_workflow_study.py`). The pilot only needs to:

1. Run the **unchanged agent** and the **existing compiled artifact** on the 45
   calibration/development records, fitting a fresh gate score to this cohort exactly as
   `calibrate_gate` already does.
2. Run both arms on the 45 held-out records.
3. Report `comment_grounded` (and the other `grade_factual` checks) per record, broken out
   by stratum, for both arms.

Estimated cost: roughly 90 records × 2 arms × 3 tool calls per episode ≈ 540 requests.
Scaling from the primary families' recorded per-request cost (~$0.09–0.11 for 132
episodes / 528 requests), this pilot is expected to cost under $10, likely closer to $1.

## Decision rule

| Observed | Reading |
|---|---|
| `comment_grounded` violations concentrate in `markdown_link` (and, more weakly, `bare_url`), essentially absent from `plain_text` | **Go.** The stratification predicts risk; proceed to the full ≥3-domain, ≥300-pair prospective protocol using this feature (or a generalization of it) as a calibration input. |
| Violations appear but are flat across strata | **No-go on this feature.** The oracle can register a violation, but this stratification does not predict it; report the null and do not proceed to the full study on this basis without a different risk feature. |
| No violations appear in any stratum at this sample size | **Inconclusive, not no-go.** 30 per stratum may simply be too few to observe a rare event; report the zero count and the implied upper bound, and consider a larger pilot before concluding the full study is unwarranted. |
| A held-out violation rate high enough to threaten task usability appears in any arm | Adverse finding, reported in full ahead of every other reading, exactly as every other protocol in this paper treats a wrong dispatch. |

## Claim boundary

This pilot cannot admit an artifact (45 held-out records cannot reach the 92
zero-violation groups the registered gate requires) and does not attempt to. It licenses
exactly one kind of statement: whether the Markdown-link/bare-URL stratification predicts
`comment_grounded` risk on this task, as a go/no-go signal for the full prospective
protocol. It is not pooled with any other result in this paper and is not a claim about
model quality, efficiency, or the registered admission gate.

## Reproduction

Preflight (already run, provider-free):

```bash
.venv/bin/python paper/scripts/gate_frontier_pilot_preflight.py
```

Execution (not yet run; requires explicit spend authorization and `OPENAI_API_KEY`):

```bash
# proposed; the runner script is not yet written and will not be until authorized
.venv/bin/python paper/scripts/gate_frontier_pilot_study.py \
  --preflight paper/results/gate_frontier_pilot/preflight.json \
  --approved-spend-usd <ceiling> \
  --out paper/results/gate_frontier_pilot/results.json
```
