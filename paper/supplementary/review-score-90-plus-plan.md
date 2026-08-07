# GAC 90+ Main-Track Readiness Plan

**Status:** partially executed. The repository now contains enough new evidence to justify
an artifact-aware review in the low 90s, but the remaining route to a defensible **95**
is still blocked by gate maturity and missing manual-maintenance evidence.
**Historical baseline:** `paper/supplementary/quality-assessment.md` rates top-tier
main-track readiness at **91/100** and artifact/manuscript engineering at **98/100**.

## Update (2026-08-06)

The most important score-changing items in this plan are now partly satisfied:

1. **Cross-repository, time-forward live-provider evidence exists.**
   - `paper/results/github_multirepo_pr_outcome_core/preflight.json` seals a
     five-repository frozen design with a 150-case held-out capacity.
   - `paper/results/github_multirepo_pr_outcome_core/results.json` retains a
     four-repository, 120-pair completed provider-backed evaluation plus a retained
     fail-closed `pytorch/pytorch` compile retirement.
   - `paper/results/github_multirepo_pr_outcome_balanced/results.json` adds a
     three-repository balanced rerun with **360/360** exact discovery traces,
     **180/180** exact held-out pairs, and full `open`/`merged`/`closed_unmerged`
     compaction under the same two-read task.
   - `paper/results/multirepo_pr_outcome_balance_analysis.json` shows that the earlier
     open-PR fallback and `pytorch/pytorch` retirement were selection-sensitive rather
     than intrinsic to the task.
2. **Frozen single-candidate pre-calibration is implemented and executed.**
   - The multirepo PR-outcome-core study uses
     `freeze_one_candidate_before_calibration=True`.
3. **One executable same-task comparator now exists.**
   - The study includes a fixed-template pre-model comparator under the same records,
     model, and ordering protocol.
4. **A provider-free gate selectivity audit now exists.**
   - `paper/scripts/analyze_gate_selectivity.py` generates
     `paper/results/gate_selectivity_analysis.json`.
   - The companion note `paper/supplementary/gate-selectivity-analysis.md` shows that
     all **7** current exact-`.05` artifacts are still step gates, while partial
     frontiers appear only in an archived pilot and the looser-`alpha=.10` GCS study.

What is **not** solved yet:

1. The new cross-repo task is still simplified relative to the richer workflow families.
2. Manual authoring / maintenance cost is still unmeasured.
3. Compiler-wide multiplicity control is still not implemented.
4. The exact-`.05` gate still lacks a non-degenerate current frontier even after the
   new analysis; the audit clarifies the problem but does not solve it.

The balanced rerun changes the score ceiling in one important way: the strongest
cross-repository negative is no longer "the learned artifact cannot cover open PRs" or
"`pytorch/pytorch` intrinsically retires."  It is now that the evidence is still a
simplified two-read task, one provider/model family, and an all-or-none exact gate.

## Objective

Raise the paper from a defensible high-80s main-track submission to a defensible **90+**
scientific-readiness score without weakening claim hygiene. The blocker is not artifact
quality. The blocker is that the best current evidence is still one repository snapshot,
one model configuration, mostly all-or-none compiler admission, and no executable
same-task workflow-compiler comparator.

## Hard stop conditions

Do **not** revise the main scientific-readiness score to 90+ unless all of these are
true:

1. There is a **cross-repository, time-forward** live-provider result, not just a new
   within-repository family result.
2. The admission story shows a **non-degenerate risk-coverage frontier** at the
   registered `alpha=.05`, or the paper permanently narrows its claim to an exact
   support-threshold gate.
3. The compiler uses either a **frozen single-candidate pre-calibration protocol** or an
   explicit compiler-wide multiplicity correction.
4. At least one **executable same-task workflow-learning/compilation comparator** runs
   under the same records, model, cache policy, and ordering protocol.
5. Manual code is treated fairly on both axes: runtime parity is already measured, but
   **authoring/review/maintenance effort under drift** is also measured.

## Score levers

| Dimension | Current cap | What moves it |
|---|---|---|
| Experimental rigor | single snapshot, narrow external validity | multirepo + time-forward + powered preservation |
| Technical soundness | per-candidate conditional gate only | frozen-candidate or compiler-wide multiplicity control |
| Significance | runtime claim narrowed by manual parity | lifecycle/maintenance evidence and heterogeneous-family action selection |
| Novelty | strong framing, weak executable comparator set | one runnable same-task optimizer/compiler baseline |
| Clarity | already high but dense | compress after stronger evidence lands |

## Phase 1: Immediate in-repo upgrades

These changes are valuable now and do **not** require new provider calls.

### 1A. Freeze one candidate before calibration

**Goal:** make a stronger future protocol available without changing the default paper
path.

**Implementation target**

- Add `freeze_one_candidate_before_calibration` to `GrcConfig`.
- Rank families on train/dev evidence exactly as today.
- Calibrate only the highest-ranked candidate that survives synthesis and challenge.
- Stop after that candidate emits or retires so lower-ranked families do not consume the
  same calibration groups.

**Current repo status**

- Implemented in `src/guarded_agentic_compaction/grc/compile.py`.
- Exposed through `src/guarded_agentic_compaction/api.py` and
  `src/guarded_agentic_compaction/cli.py`.
- Covered by `tests/integration/test_end_to_end.py`.

**Verification commands**

```bash
.venv/bin/python -m pytest -q tests/integration/test_end_to_end.py
.venv/bin/python -m pytest -q
```

**Acceptance criteria**

- Default behavior is unchanged.
- Freeze mode emits the same top artifact as the unrestricted run on the support-demo
  workload.
- Freeze mode avoids lower-ranked calibration consumption on that workload.

### 1B. Publish a non-degenerate gate analysis from retained negatives

**Goal:** strengthen the gate story before paying for new live runs.

**Implementation target**

- Build a provider-free analysis that combines admitted groups with retained negative
  evidence from the suffix pilot, the identifier-hull failure, and archived unavailable
  calibration rows.
- Report a true or approximate risk-coverage curve and state clearly whether it is
  exploratory or registered evidence.

**Proposed commands**

```bash
# new analysis script to add
.venv/bin/python paper/scripts/analyze_gate_selectivity.py \
  --out paper/results/gate_selectivity_analysis.json
.venv/bin/python paper/scripts/build_artifacts.py
.venv/bin/python paper/scripts/validate_artifacts.py
```

**Acceptance criteria**

- The result shows more than a single support-threshold point.
- The paper explicitly distinguishes exploratory selectivity analysis from registered
  admission.

**Current repo status**

- Implemented in `paper/scripts/analyze_gate_selectivity.py`.
- Generated artifact: `paper/results/gate_selectivity_analysis.json`.
- Summary note: `paper/supplementary/gate-selectivity-analysis.md`.
- Outcome:
  - the current registered exact-`.05` artifacts remain step gates,
  - the archived 2026-08-03 pilot and current `alpha=.10` GCS artifact provide
    retained partial-frontier evidence, and
  - NESTFUL and API-Bank remain pure support-shortfall refusals.

**What this changes**

- The repository now has a dedicated evidence file for the gate-behavior claim.
- This improves claim hygiene and future reviewer-facing documentation.
- It does **not** by itself move the scientific-readiness ceiling; the missing exact-`.05`
  current frontier still requires new experimental data.

### 1C. Compress the manuscript after the evidence story is fixed

**Goal:** turn current dense clarity into high-confidence clarity.

**Implementation target**

- Keep the negative evidence in the main text.
- Move repetitive study plumbing and audit detail into tables or supplement.
- Add one study-map figure covering artifact, `alpha`, oracle, and cohort lineage.

**Acceptance criteria**

- Main-track build is shorter and easier to parse without dropping the key caveats.

## Phase 2: Cross-repository and time-forward preflight

This is the first phase that can actually unlock 90+.

### 2A. Generalize the GitHub workflow harness

**Goal:** turn the single-repository snapshot study into a reusable multirepo protocol.

**Implementation target**

- Parameterize dataset acquisition and cohort filtering by repository.
- Freeze case selection provider-free before any paid calls.
- Add time-forward folds per repository so held-out cases are chronologically newer than
  discovery and calibration.

**Current repo status**

- `paper/scripts/github_multirepo_preflight.py`
- `paper/results/github_multirepo/preflight.json`
- `tests/unit/test_github_multirepo_preflight.py`
- `tests/integration/test_github_multirepo_preflight.py`

The current scaffold is implemented and validated, but it does **not** earn new empirical
credit yet. The checked-in GitHub parquet still contains only one repository
(`huggingface/datasets`), so the committed preflight correctly fails the
`minimum_complete_repos=3` gate even though all three families can be selected with a
strict time-forward split on that one repository.

**Proposed commands**

```bash
.venv/bin/python paper/scripts/github_multirepo_preflight.py \
  --repos huggingface/datasets,pallets/flask,encode/httpx \
  --families issue_type,pr_outcome,backlog_attention \
  --out paper/results/github_multirepo/preflight.json
```

**Acceptance criteria**

- At least three repositories.
- Provider-free split sealing with no cross-role overlap.
- Time-forward ordering is explicit and validated.

**What is now satisfied**

- Provider-free multirepo cohort design exists and writes an auditable preflight payload.
- Time-forward ordering is explicit, tested, and fail-closed.
- The protocol proves the current checked-in snapshot is still single-repo limited.

### 2B. Add a powered preservation cohort

**Goal:** tighten the main preservation bound from the current small-sample regime.

**Target**

- At least **300 held-out paired cases total** across the primary transfer result, with
  per-repository reporting and pooled reporting kept separate.

**Why 300**

- Zero compiled-only failures in 300 pairs puts the one-sided exact upper bound near 1%.
- That is much harder to dismiss than the current 30-pair and 90-pair bounds.

**Acceptance criteria**

- Report both pooled and per-repo bounds.
- Do not call pooled evidence a substitute for per-repo heterogeneity.

## Phase 3: Comparator and significance upgrades

### 3A. Execute one same-task workflow-learning comparator

**Goal:** replace literature-only positioning with one runnable adjacent baseline.

**Minimum bar**

- Same records.
- Same model.
- Same cache policy.
- Same held-out protocol.
- Separate optimization overhead accounting.

**Pragmatic comparator order**

1. A trace-template or plan-caching baseline implemented locally if it is the shortest
   path to a fair same-task workflow comparator.
2. A heavier external baseline such as AWO, Agent JIT, or EvoC2F only if it can be run
   under the same protocol without hand-waving.

**Acceptance criteria**

- The comparator is executable and auditable, not just cited.
- Negative results are retained exactly as with GEPA.

### 3B. Measure manual lifecycle cost

**Goal:** support the paper's real practical claim: automation earns its complexity when
manual code is costly to build or maintain.

**Implementation target**

- Record authoring time, review time, and drift-repair time for manual provider-visible
  macros and manual pre-model programs.
- Use the existing review-bundle path to make approvals inspectable rather than
  anecdotal.

**Proposed commands**

```bash
.venv/bin/python paper/scripts/prepare_macro_review.py \
  --pool vulnerability=paper/results/multidomain/preflight/vulnerability \
  --pool hmda=paper/results/multidomain/preflight/hmda \
  --out paper/results/multidomain/review/macro-review-materials.json
```

**Acceptance criteria**

- Manual engineering cost is reported as measured effort, not inferred effort.
- Drift events are real or replayable, not imaginary.

### 3C. Make portfolio significance heterogeneous

**Goal:** show the selector does something more interesting than always pick the same
macro on one family.

**Implementation target**

- Build a multirepo or multidomain family set where the measured best action differs
  across families.
- Keep action freezing exact and provider-outcome-free.

**Acceptance criteria**

- At least two distinct non-baseline actions are selected across held-out families.
- The paper still declines any claim broader than the observed family set supports.

## Phase 4: Paid evidence run

This is the score-changing phase. It requires provider spend and should not begin until
Phase 2 preflight is sealed.

**Run order**

1. Multirepo provider-free preflight.
2. Discovery checkpoint for each repository/family.
3. Candidate freezing or compiler-wide multiplicity configuration lock.
4. Paid calibration and held-out execution.
5. Comparator runs under the identical protocol.
6. Artifact rebuild and full validation.

**Required commands**

```bash
# proposed live study; command shape is part of the implementation target
.venv/bin/python paper/scripts/github_multirepo_timeforward_study.py \
  --preflight paper/results/github_multirepo/preflight.json \
  --out paper/results/github_multirepo/results.json
.venv/bin/python paper/scripts/build_artifacts.py
.venv/bin/python -m pytest -q
.venv/bin/python scripts/verify_release.py
.venv/bin/python paper/scripts/validate_artifacts.py
```

**Go/no-go acceptance criteria**

- Cross-repository, time-forward live result exists.
- Registered `alpha=.05` evidence remains clearly separated from looser exploratory
  artifacts.
- The paper can claim at least one strong preservation story and one honest refusal or
  narrowness story.

## Correctness review checklist

Every iteration must re-check all of the following:

1. No provider output participates in case selection.
2. Discovery, dev, calibration, and test remain disjoint within and across repositories.
3. The manual baseline gets the same structural placement when fairness demands it.
4. Optimization overhead is accounted separately from deployment metrics.
5. Raw results, failed pilots, and negative comparator outcomes remain retained.
6. `paper/scripts/validate_artifacts.py` passes before any score is revised.
7. Claims about cross-repository generalization, non-inferiority, or selection value are
   made only when the actual evidence matches those words.

## Realistic score path

| Milestone | Plausible readiness score |
|---|---:|
| Current repo state | 88 |
| Phase 1 only | 88-89 |
| Phase 2 preflight without paid runs | 88-89 |
| Phase 2 + Phase 3 + strong paid evidence | 90-92 |

## Recommended next step

Implement Phase 2A next: multirepo/time-forward preflight scaffolding. That is the first
task whose completion changes the score ceiling rather than only making the current story
cleaner.
