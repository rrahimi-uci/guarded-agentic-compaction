# Gate-frontier pilot protocol

**Status: EXECUTED on 2026-08-22, exactly as pre-registered below.** The predeclared
expectation, decision rule, and preconditions were committed before the live run; the
observed results are appended in their own section at the end, unedited relative to what
was predeclared. Execution used the pinned existing artifact and cost well under the
approved $10 ceiling.

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

1. Run the **unchanged agent** and the **existing compiled artifact** on both the 45
   held-out and 45 calibration/development records.
2. Report `comment_grounded` (and the other `grade_factual` checks) per record, broken out
   by stratum, for both arms.

**As executed, this ran both arms on the full 90-record cohort rather than fitting a
separate gate score on the 45 development records first.** The decision rule below needs
only raw per-stratum violation counts, not a calibrated threshold, so a formal
`calibrate_gate` pass would have added engineering cost without changing what the pilot
can answer; fitting an actual `q(z)` gate is exactly what the full prospective study does
if this pilot signals go. The held-out/calibration-development split is retained as
metadata on every graded record so a later reanalysis can still respect it. This
simplification was made before the live run, not after seeing its results.

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

## Observed results

Both arms completed all 90 records with **zero execution failures** in
109.0 seconds at concurrency 8, using model `gpt-5.6-luna` (the same model pinned in the
existing artifact's manifest) at an actual spend well under the approved $10 ceiling,
consistent with the pre-run estimate.

| Condition | Stratum | n | `comment_grounded` rate | violations |
|---|---|---:|---:|---:|
| unchanged | `plain_text` | 30 | 1.000 | 0 |
| unchanged | `bare_url` | 30 | 1.000 | 0 |
| unchanged | `markdown_link` | 30 | 0.900 | 3 |
| compiled | `plain_text` | 30 | 1.000 | 0 |
| compiled | `bare_url` | 30 | 0.967 | 1 |
| compiled | `markdown_link` | 30 | 0.967 | 1 |

Pooled across both conditions (`paper/scripts/gate_frontier_pilot_analysis.py`, exact
one-sided Fisher tests against `plain_text`, uncorrected for the two strata compared):

| Stratum | Violations / n | One-sided $p$ vs. `plain_text` |
|---|---:|---:|
| `plain_text` | 0/60 | — (baseline) |
| `bare_url` | 1/60 | 0.500 |
| `markdown_link` | 4/60 | **0.0594** |

**Reading: a borderline Go, with the hypothesis refined rather than confirmed as stated.**
`plain_text` produced exactly zero violations in 60 observations, as predicted.
`markdown_link` produced the most violations of any stratum and sits just short of the
conventional 0.05 threshold at $p=0.0594$ — suggestive, not decisive, and this is a single
run of a stochastic model with no fixed sampling temperature, so the exact counts should
be read as indicative rather than precise. `bare_url` showed no discriminable elevation
at all ($p=0.500$): a bare URL near the comment text did not predict risk the way an
actual Markdown-link wrapper did. The original two-stratum hypothesis is therefore
partially wrong in an informative way: the mechanism looks specific to Markdown link
*syntax* (link text in brackets immediately followed by a parenthesized URL), not to URL
presence in general.

A targeted diagnostic re-run of the four distinct issues that failed in the primary run
(`paper/results/gate_frontier_pilot/diagnostic.json`, a separate small live call, not
pooled with the primary tally) confirms the mechanism directly. Issue 4448's source
comment reads "Hi! The `[datasets_sql](https://github.com/mariosasko/datasets_sql)`
package lets you..."; the unchanged agent's returned excerpt was "Hi! The datasets_sql
package lets you easily find distinct rows in a dataset" — grammatically faithful,
*exactly* the Markdown link wrapper stripped, which is why an exact-substring check
fails it. This is the same mechanism already on file for issue 6602
(`github_natural_live/continuation_replay.json`), now observed a second time on an
independent record.

One further finding the pooled table does not show: issue 5710 failed in **both**
conditions independently. That is a stronger signal than an isolated single-arm failure,
because it means the record itself — not condition-specific noise — is the hard case;
its source comment contains a Markdown-linked inline-code term
(`` [`mmap`](https://man7.org/linux/man-pages/man2/mmap.2.html) ``), and both arms
independently stripped the link while keeping the backticked term.

**Decision: proceed to the full prospective protocol, using Markdown-link syntax
specifically (not bare-URL presence) as the calibration feature.** This is the weak form
of "Go" in the decision rule above: the signal is real and mechanistically confirmed, but
not yet significant at conventional levels, and refining the risk feature before scaling
up is itself a useful outcome of running a pilot rather than committing the full budget
directly.

## Reproduction

Preflight (provider-free):

```bash
.venv/bin/python paper/scripts/gate_frontier_pilot_preflight.py
```

Execution (live; requires `OPENAI_API_KEY` and an explicit `--approved-spend-usd`
ceiling):

```bash
.venv/bin/python paper/scripts/gate_frontier_pilot_study.py --approved-spend-usd 10
```

Analysis (provider-free, reads the sealed results):

```bash
.venv/bin/python paper/scripts/gate_frontier_pilot_analysis.py
```
