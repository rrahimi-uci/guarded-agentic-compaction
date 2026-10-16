# Fresh generalization and gate attribution study

Prospective protocol, 2026-10-15. Freeze this file, implementation, source,
selection, environments and artifacts before any paid call. Retain null results.

## Questions and scope

1. Does GAC reduce deployment resources versus offline adapted AWM across three
workflow families and two models without a task-accuracy loss exceeding five
percentage points? This margin is a research tolerance, not an operational
safety guarantee. Report tighter 1/2 percentage-point sensitivity bounds without
changing the primary margin. No initial-submission or acceptance claim follows.
2. Does the existing statistical gate alter routing or continuation evidence
relative to support-only admission and deterministic guards for these candidates?
This tests the deployed gate, not a newly trained selector. The historical
end-to-end learned-gate retirement remains a negative result.

## Fixed design

Models: gpt-5.6-luna and gpt-6-luna, existing standard short-context rate cards,
verified at https://developers.openai.com/api/docs/pricing on 2026-10-15.
Families: issue_type, pr_outcome, backlog_attention. Same pinned repository
snapshot, not three domains or repositories. No model-specific rediscovery:
reconstruct historical discovery under each model's manifest. AWM receives the
same eligible historical action traces; GAC retains its train/dev/calibration
split. Six independent induction requests, one per family/model; no retries,
manual memory editing, output selection, online memory updates or test tuning.
The pinned upstream adaptation in matched_reuse_baseline is reused unchanged.

Exclude every named record in prior paper results and experiments. Allocate
backlog first to prevent cross-family overlap, then issue tasks, then PR tasks.
Within eligibility, rank by SHA256 of study name, seed 20261020, family, number.
Source-only feasibility: nonempty representable titles; issue tasks must have a
verbatim excerpt of >=20 characters available in title/body/first-three comments.
No model output or successful dispatch is an eligibility criterion.
Six distinct pilot records per family, then 600 issue, 600 PR and 144 backlog
primary records. Share records across models, never count model repeats as
independent records. Each cell cycles all six three-arm permutations and
alternates model order by record. No replacement or retry of failed tasks.

Live arms: baseline, gac, awm_offline_adapted. Reuse existing family integration:
issue GAC uses CompactingModel; PR/backlog use CompactingRunner pre-model composite
with unchanged-agent fallback. All three arms within a cell share prompt, source,
tools, answer schema and grader. Composite placement is a treatment difference.
Low reasoning/verbosity, no parallel tools, 2048 output tokens, eight SDK turns,
120 second timeout, zero SDK/HTTP retries, tracing disabled. Eight record groups
concurrently; arms/models inside each record execute sequentially.

## Gate ablation and stop conditions

Before calls, execute the real dispatcher on all selected records under:
- full retained statistical gate;
- support-only: same program/guards/verifier, require >=92 calibration groups,
  replace score/admission with always-accept (uncertified ablation);
- deterministic: same program/guards/verifier, remove score/admission and the
  support-count check (uncertified ablation on these already admitted programs).

Retain per-record decisions, calls, output hashes, actual gate scores and timings.
Compare continuation-relevant decisions/calls/evidence, not telemetry labels.
If all three paths match, there is no routing/evidence advantage on this cohort;
run one live GAC path, do not fabricate independent ablation outcomes. Differences
stop preparation for a separately frozen live-ablation design, not silent pooling.
This cannot test whether calibration prevented a bad candidate at compilation,
unseen-input behavior or universal gate equivalence. A coarse learned model may
be nonconstant in general but constant on the observed entry features.

Pilot must complete with usage/schema accounting and at least one actual GAC
compaction per family/model. Correctness is not a continuation criterion. Stop
on induction failure, source/manifest drift, budget exhaustion, unresolved
pending attempt or five consecutive failed terminal episodes. Keep all partial
results; never tune a used seal.

## Outcomes and prespecified inference

Primary accuracy: all source-grounded answer fields correct, excluding tool order
as an accuracy requirement. Report tool contract separately. Failed/unattempted
scheduled tasks count incorrect. Keep pilot separate. Unit: unique source record.
Report six cells separately; no pooled repeated-record precision claims.

Primary contrast: GAC minus adapted AWM. For each cell let L count AWM-correct,
GAC-incorrect pairs among n scheduled records. A one-sided exact binomial upper
bound U for L/n at error probability 0.05/6 supplies a conservative lower bound
-U on accuracy(GAC)-accuracy(AWM). Declare noninferiority only if U<0.05 and all
scheduled pairs were attempted. Bonferroni controls the six-cell family under
independent-record sampling assumptions, not cross-model independence. This is
conservative because GAC-only successes are ignored. At n=600, <=17 losses pass;
power at true loss probabilities .01/.02/.03 is approximately 1/.939/.467.
At n=144 only <=1 losses pass; power .577/.215/.068: backlog is low precision,
not an adequately powered replication. Report exact loss bounds, paired gains,
McNemar descriptive p values and 10000-draw paired bootstrap resource intervals.
Task/author/time dependence remains a limitation of this snapshot design.

Report attempted denominators, failures, real provider requests, total local tool
calls (including pre-model attempts/fallback), tokens, latency, estimated model
cost and resource-accounting completeness. Include failure usage, never treat
missing usage as zero. Report AWM induction separately and amortized by cell;
GAC reconstruction is local wall time, not total historical compiler cost.
Primary resource summaries include all attempted episodes. Paired intervals use
complete pairs and disclose excluded failures. Efficiency is descriptive unless
separately specified; accuracy noninferiority does not establish safety.

## Budget and provenance

Carry prior matched-study total $8.57705193 including retained failure reserves
against the user's existing aggregate $400 estimated-spend cap. Verify the prior
checkpoint/analysis identity; bind source files. Reserve $1 before each external
attempt, retain it for failures and pending attempts, and count observed partial
usage. No increase in authorization. This is not a provider billing cap.
Credentials are read only from the existing .env; never retained. Atomic
checkpoints, exclusive lock, source regrading, tool replay and usage recomputation
are required. Freeze induction memory before pilots; commit/push the protocol
and seal to an open PR before calls. Do not merge the PR.
