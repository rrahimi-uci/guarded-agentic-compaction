# Response draft for the three ICLR reviews

Status: author-review draft, not posted. The author confirmed on November 6 that an
older manuscript is uploaded and the October 28 revision is the baseline to improve.
The exact uploaded bytes/date remain unverified: OpenReview API access returned 403
and browser access was unavailable. Do not tell reviewers that they overlooked a
revision they had not received. The supplied reviews are retained with trailing whitespace normalized under
`paper/reviews/ICLR-{1,2,3}.txt`.

A [concern-by-concern ledger](reviewer_concern_closure.md) records supported answers,
remaining experiments and explicit completion criteria. It does not claim reviewer agreement.

## Shared opening

Thank you for identifying the distinction between empirical efficiency, replay
fidelity, and deployment-level risk control. We agree that the original presentation
did not separate these adequately. Our revised manuscript narrows the primary
claims, accounts for the complete primary discovery populations, distinguishes
per-candidate from selection-adjusted bounds, and reports the limitations of the
learned gate. The new population audit is retrospective and provider-free; it is not
a new calibration experiment. We do not claim that the missing matched-compiler
comparison has been completed.

## Reviewer 1

**Loss and labeling path.** The 92-group primary tables use replay labels. In
`grc/compile.py::_calibration_samples`, the compiled prefix runs against the
recorded/snapshot tool environment; after verifier success, its outputs are compared
with the recorded outputs. The helper does not execute or grade the final model
continuation. We now state this explicitly in the formulation, abstract, results,
and certificate table. The theorem applies to the prespecified measured loss under
its sampling and candidate-selection assumptions; replay labels cannot establish
a final-answer guarantee. A clean rejected attempt has zero replay loss but its
baseline continuation can still fail the final task.
The primary helper does not measure incident frequency: interpreter/verifier
rejections are unproductive events, and only verifier-passing missing/inequivalent
outputs are replay violations. The revised formulation no longer includes incidents
in the primary bound's measured endpoint.

The separate post-cutoff PR study executes and grades the frozen substituted agent's
continuation on 132 fresh calibration groups: zero contract misses, one-sided upper
bound 0.0173 at 90% confidence under its single registered rule. These records are
84 open and 48 merged PRs, with no closed-unmerged records. This result concerns that
population and candidate only; it does not validate all three primary workflows or
the closed-unmerged test stratum.

**Population accounting.** The new audit accounts for all 396 discovery records.
Issue-type routing excludes two inexact runs and leaves 14 eligible records unused;
PR-outcome excludes one and leaves 15 unused; backlog excludes none and leaves 16
unused. Each family assigns 16/8/92 records to train/development/calibration. For all
five reconstructed candidates reaching calibration, every assigned calibration
group has a matching labeled window. No additional family-window omission occurs
within those selected calibration splits.

The earlier outcome filter remains consequential: excluded issues #539 and #2781 and
PR #5700 pass their saved artifacts' entry guards and learned gates under compatible
manifests. We therefore cannot justify exclusion by claiming those inputs would
necessarily abstain at deployment. These are failed baseline discovery answers, not
observed counterfactual GAC failures. The revised paper explicitly disclaims a bound
for the unfiltered primary deployment population. A new claim requires independently
sampled, unfiltered calibration of a frozen policy, not more successful traces.

The audit uses the retained selected-artifact guard/gate, because current code changes
the reconstructed issue-number hull from an interval to unrestricted integers. It
reports this version difference rather than treating recompilation as identical.

**Compiler comparisons.** The revision discusses EvoC2F, Agent JIT, and TraceCompiler.
We agree that citations and the adapted AWM comparison do not establish performance
against a competing compiler. The matched compiler experiment remains unrun; the
paper makes no runtime-dominance claim over handwritten or recurrence-only programs.
The accompanying execution plan requires a documented, version-pinned compiler
comparator and explicit reporting of any adaptation.

**Lifecycle.** Implemented controls are staged promotion, expiry, explicit retirement,
rollback, kill switch, and manifest compatibility checks. These do not detect all
distribution changes. The new lifecycle paragraph distinguishes them from a proposed,
unevaluated monitoring/renewal policy: suspend on confirmed committed contract
violations or incompatible pins; investigate prespecified drift/outcome alarms;
freeze the revised artifact and population; recalibrate on fresh disjoint groups
before reactivation. We added the SKILL.nb reference. No measured maintenance benefit
or automatic sequential risk-control guarantee is claimed.

**Presentation and benchmark references.** The introduction now states the GitHub
triage task and source before introducing issue #4420. The formulation explains the
manifest as version/content identities for the execution environment, which determine
artifact compatibility. Section 4 cites the GitHub snapshot, BIRD, NESTFUL, AppWorld,
API-Bank, and BFCL; the appendix distinguishes live-agent studies from provider-free
compiler substrates. The trace funnel reports feasibility/refusal, not final-task
quality or live efficiency on those substrates.

## Reviewer 2

**Task difficulty and value of automation.** We agree that the primary GitHub tasks
are metadata classification and source extraction, amenable to manual deterministic
workflows. Their specifications are in the benchmark table and detailed appendix;
we do not claim those decisions require semantic reasoning. The handwritten arm
matches all 90 contracts and request savings. Automatic discovery is implemented,
but its engineering/maintenance benefit has not been quantified.

The October 28 revision adds evidence on adaptive SQL continuations in BIRD and a
larger adapted AWM comparison. BIRD supports specialization of a schema-first opening,
not a measured advantage over a matched alternative compiler. The AWM comparison
establishes five-point noninferiority in five of six workflow/model cells; it does not
establish the stricter one-point margin or compiler-mechanism attribution.

**Mechanism attribution.** The recurrence-only arm's 30/30 correctness and lower
request count remain in the main results. We do not interpret a refusal as an avoided
error. The later one-component-at-a-time live-recovery study supports request-scope
checking on constructed requests (205/216 versus 186/216), while completeness benefit
is unresolved and full GAC does not establish superiority over baseline. These data
are not evidence of general protection under natural drift.

**Calibration and learned score.** The primary replay-label path and full exclusion
accounting are described in our response to Reviewer 1. Scores and identical routing
on already-admitted artifacts do not establish risk ranking or compilation-time
selection benefit. The adaptive 311-group extension is explicitly exploratory; it
does not repair the confirmatory selective-coverage gap.

**Requested adaptive comparison.** We agree this is the outstanding experiment with
the largest potential to change the contribution assessment. The execution plan
separates a matched fixed-prefix mechanism comparison from a whole-compiler comparison
over a train-frozen candidate list that includes rejected candidates. It requires
task success, optimization coverage, wrong dispatches, fallback, and total costs.
A provider-free AppWorld common-entry preflight validates 12 known-correct
public sequences, 24 negative controls and 24 library-read probes through the
saved-state adapter. Authentication remains a write and its common setup is
counted. Two subsequent sealed, adapted-interface baseline attempts on the same
12 exposed tasks scored 1/12 and 2/12 official successes, below the prespecified
8/12 engineering competence gate. Their model traces are not a persuasive
comparator for a GAC cost claim; no matched GAC arm was run. The earlier
persistence-defective attempt and its invalid original grades remain retained
separately.

A sealed BIRD one-call continuation pilot completed 36 exposed development
questions per arm: baseline and handwritten scored 28/36, while the guarded
research candidate scored 26/36. It reduced model requests against baseline
(151 to 112) but not against the equivalent handwritten prefix (111), and it
had no calibration or independent test groups.

AgentHop supplies a competent adaptive baseline and a released exact-answer
grader: 19/24 correct on the sealed development sample, above its 17/24
engineering gate. Its public single-target depth-2 subtype has one connected
full-neighborhood source component. The tested GAC bridge binder found no
consistent dependent expression; a posthoc section-lookahead audit found 42
next-turn opportunities but no derived selector. Even an exploratory grouped
ranker with the true future read count supplied matched only 11/35 exact read
batches. These are exposed development diagnostics, not a GAC intervention or
source-independent test. We therefore assert no confirmatory adaptive
quality--cost or GAC-superiority result. The revised manuscript now discloses
all three development gates in Appendix “Adaptive-Task Development Gates” and
points to them from the main discussion. The [concern ledger](reviewer_concern_closure.md)
links each retained result and its remaining completion gate. These new local
findings should enter a reviewer response only with a verified revised upload.

## Reviewer 3

**Selection-adjusted guarantee.** At alpha=0.05, delta=0.10, and 11 thresholds, zero
violations among 92 groups gives 0.049809 for one fixed candidate. Correcting for two
candidates gives 0.056941, which misses the target. A fixed prospective two-candidate
design needs at least 106 accepted zero-error groups; this arithmetic does not justify
post hoc extension. The primary issue candidate has no extra candidate multiplicity,
but its selected calibration population still prevents an unfiltered deployment
claim. The abstract and conclusion now state these limits directly.

There is a separate 132-group, single-candidate end-to-end PR result under the scope
and assumptions described above. It must not be substituted for the primary
selection-wide guarantee. Counting primary authors or creation days as independent
units removes admission under the registered grid; these sensitivities demonstrate
dependence on the grouping choice rather than proving which grouping is correct.

**Certified selective coverage.** The 92-group primary cohorts support full empirical
coverage or retirement only. We have not established two positive intermediate
certified operating points or superiority over support-only admission at equal
coverage. The enlarged sequential issue cohort is not presented as a solution.
The paper now treats learned selectivity as unestablished. Any renewed claim requires
a prospectively frozen, unfiltered cohort and a matched-coverage comparison with
separate final evaluation. If that experiment is null or infeasible, this limitation
will remain rather than being hidden through a different threshold or population.

## Before posting

- Replace section references with the final uploaded PDF's numbering.
- Verify the revised manuscript and supplement were actually uploaded within
  the [November 5--18 discussion window](https://iclr.cc/Conferences/2027/AuthorGuidelines);
  the rebuttal main-text limit is ten pages and OpenReview displays a PDF diff.
- Keep completed audits, retained experiments, and proposed work separate.
- Add new experimental findings only after their frozen protocol and retained results
  exist; update this response and manuscript together.
- This file is a draft for the author. It has not been submitted to OpenReview.
