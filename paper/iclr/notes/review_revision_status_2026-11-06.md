# ICLR revision status and acceptance criteria

Baseline: October 28 manuscript at repository main commit `cf7f5cd`. On November 6,
the author confirmed that the uploaded submission is older and that October 28 is the
version to revise. Exact uploaded revision/date/bytes have not been independently
retrieved; an OpenReview GET returned 403 and the browser host was unavailable.

| Recommendation | Deliverable in this revision | Status / remaining work |
|---|---|---|
| Reconcile versions | Author confirmation, baseline commit, this ledger | Older upload confirmed by author; uploaded PDF hash remains unverified |
| Audit calibration population | Executable audit, 396-record JSON, rendered report, regression tests | Completed for three primary cohorts and five calibrated candidates; not an audit of all supplementary cohorts |
| Align claims | Abstract, formulation, introduction, setup/results, certificate table, conclusion, appendix | Explicit selected-population limitation, replay/continuation separation, lifecycle implementation/proposal separation |
| Establish comparative value | Focused execution design, initial BIRD source screen, explicit preflight requirements | Unrun; 722 dev / 5,094 train records remain after a conservative screen, not certified fresh cohorts; task feasibility and compiler adapter remain required |
| Prepare responses | Reviewer-specific draft | Completed as a draft; not posted; experiment-dependent objections remain open |

## New evidence and its limits

All 396 primary discovery records are accounted for. The five calibrated candidates
have labels for every assigned calibration group (92 each). The audit found no
family-window omission inside those selected splits. It confirms an earlier selection
gap: two inexact issue traces and one inexact PR trace were excluded before splitting,
and all three pass the saved selected artifacts' entry guards and gates.

Current code reproduces all three selected programs, but not the issue artifact's
historical interval hull or corresponding feature specification. The audit therefore
uses the historical registry for selected-artifact eligibility and replay relabeling.
Nonselected candidates are explicitly current-code reconstructions. No live continuation
was run; these observations do not establish three GAC failures or a new certificate.

## Existing October 28 progress to explain to reviewers

- Replay versus final-task loss is already separated; the new revision makes the
  unfiltered-population limitation prominent rather than relying on an appendix caveat.
- The 132-group post-cutoff PR result includes final outcomes but only covers open and
  merged PRs under its sampling assumptions.
- BIRD and adapted AWM add evidence beyond the original 90 cases; neither is a matched
  competing-compiler evaluation. AWM has one inconclusive five-point cell.
- Live recovery supports request-scope checking under constructed requests; completeness
  benefit and learned selection remain unestablished.
- The 311-group extension's interpretation correction remains in force: nominal
  arithmetic is not a confirmatory certificate for its adaptive mixed-frame procedure.
- EvoC2F and Agent JIT were already cited. This revision adds SKILL.nb lifecycle context.

## Open scientific work

1. Fresh calibration sampled before outcomes and mined-region occurrence, with defined
   labels for every eligible dispatch and prespecified candidate multiplicity.
2. A matched adaptive-task comparison, including rejected candidates and complete costs.
3. An implemented, faithful competing-compiler comparator; citation-only comparison is
   not a substitute.
4. A justified sampling/independence unit and prospective sample-size decision. Do not
   repair old p-values by choosing a favorable cluster definition after seeing results.
5. Measured lifecycle/engineering benefit, if that benefit is retained as an empirical
   contribution. Otherwise continue to label it unmeasured.

The [focused execution plan](../../supplementary/reviewer-adaptive-comparison-plan.md)
sets the next work package. The existing 12-family feasibility report remains a no-go;
this revision does not silently replace it with an allegedly executed smaller study.

## Publication and validation

The revision updates both ICLR PDF copies and prepared OpenReview metadata. The
long-form article remains a separate historical edition; it is not claimed to include
this new audit. The publication manifest is regenerated after the build. Local checks
and remote PR checks are recorded in the PR; they validate artifacts/software, not
statistical assumptions or acceptance prospects. The author performs upload and merge.
