# Adaptive quality–cost follow-up

**Decision: no confirmatory run.** This phase strengthens the baseline interface,
records a bounded development extension and corrects benchmark-claim scope. It
does not establish GAC benefit or emit an admitted artifact. See the
[prospective study protocol](../../supplementary/adaptive-quality-cost-study.md).

## Bounded extension and exposure

Before task-text inspection, a fixed hash ordering selected one task from each
of four previously unexcluded single-site Reddit templates. Selection does not
use intents, expected answers or outcomes. The same metadata-only selection
recomputes from pinned upstream data. Prior exposure screening remains limited;
previously unexcluded does not mean unseen by people or model training.

| Task | Template | Inspected public task category | Current suitability finding |
|---|---|---|---|
| 613 | 9 | Create a book-review post, then comment | Additional writing; no demonstrated second reusable read family |
| 626 | 13 | Select an appropriate forum and post a discussion | Semantic forum choice is required; no grounded compiled selector demonstrated |
| 714 | 24 | Select a top-ranked post and vote | Read/navigation hypothesis; generic browser effects are still UNKNOWN |
| 647 | 19 | Post a technology discussion | Another posting workflow; not evidence of broader read-prefix diversity |

All four entire templates join the future-confirmation exclusion set in
[selection.json](selection.json), whether or not model execution follows. Six
other single-site Reddit template IDs remain candidate sources, not certified
fresh or independent holdouts. No model or live task execution was performed on
these four cases. They were not replaced after inspection.

The existing candidate from the earlier six-task pilot remains a single form-open
call rejected at `no_dev_groups`. This extension does not establish a useful
multi-action candidate, robust task routing or adaptive continuation after GAC.
Do not collect many posting variants merely to increase a success count.

## Batching controls and retained failures

The new `browser_batch` interface accepts 1–8 ordered actions whose arguments are
already available. It validates the entire batch before execution, returns every
intermediate observation and stops on the first action error. It cannot execute
arbitrary code and does not roll back writes. The same primitive can support a
future stronger baseline; no model has yet used it in this study.

Controls use **two already exposed tasks**, retrieval 69 and posting 634. The
sequences and answers are trusted handwritten fixtures derived from old retained
development evidence, not fresh model traces. Each execution uses an independent
fresh pinned website and official HAR/response grader. These fixtures are not
runtime comparator results, automatic programs, or evidence of saved requests.

Version 1's nine grader checks matched their expected outcomes, but the stronger
observation comparison failed in both pairs. One retrieval action timed out even
though its supplied fixture answer passed the response grader. The posting pair
differed in a display timestamp and random decorative emoji. **Version 1 failed
overall validation**; its seal, sources, raw records and HARs remain in
[batch_controls](batch_controls/report.json). A successful reference-answer grade
alone is insufficient to establish a correctly executed positive control.

Version 2 requires the entire positive sequence to execute without errors and
pass the official grader. Actions have 30-second limits and snapshots wait for
network idle. For posting task 634 only, observation comparison normalizes the
new-post display timestamp and named decorative empty-comment emoji, in addition
to the ephemeral origin. All original observations remain in the archive. Task
text, result values, action errors and action order are not normalized away.
This is a fixture-specific comparison, not a general browser-state equivalence
claim or a production verifier. Timing policy changed, so these controls must
not be compared as latency measurements with the previous baseline.

**All nine version-2 controls passed**, and both positive observation pairs
matched under the declared normalization: three actions for task 69 and six for
task 634. The final results are retained in
[batch_controls_v2/report.json](batch_controls_v2/report.json), with the full
source seal and raw evidence archive. Observed outcomes are four successful
complete positive executions (sequential/batch × two tasks), four rejected empty
or false completions, and one stopped-on-first-error batch whose queued posting
actions never execute. Any failed gate blocks a paid follow-up. No owned
containers or labeled networks remained after the completed controls.

No GAC effect catalog was broadened. In particular, batching form fills and posts
does not convert them into read-only speculative operations. This adapter is not
an unrestricted coding baseline or a native Agent JIT reproduction.

## AppWorld and claim scope

The [pinned upstream rules](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/README.md#no_entry_sign-agent-development-restrictions)
explicitly prohibit hardcoding API calls in agent logic, including login to all
apps at startup. Our existing common-entry controls are useful adapted-interface
evidence, not native benchmark results. Learned-compilation eligibility needs
clarification before any standard leaderboard claim. No past measurements or
manuscript results were relabeled.

The new protocol separates runtime quality/cost, admission benefit and authoring
effort. It requires matched strong baselines, ordinary versus stress populations,
independent task grading, held-out calibration/test groups, selection-wide error
accounting and complete lifecycle costs. An ideal handwritten version of the
same program may match runtime efficiency; automation effort is a separate study.

## Budget and next decision

This phase contains **zero provider calls**. Campaign accounting remains
**$2.2137322**, leaving **$297.7862678** of the authorized $300 cap. These are
conservative ledger estimates, not an invoice; local compute and engineering are
unpriced. The authoritative shared ledger was neither reset nor modified.

The next substantive work is a source-audited, grounded second read workflow
and a separately sealed adaptive runner using the batched interface. Task 714
is a hypothesis to investigate, not a positive feasibility finding. If no useful
region survives against that baseline, explicitly narrow or extend the method;
do not launch the confirmatory comparison or keep replacing tasks to find wins.
Native compiler integration, fresh population sampling and statistical power
remain unresolved. This phase does not close the reviewers' practical-value gap.

## Reproduce

Ordinary offline tests verify selection invariance, batch error boundaries and
the retained source/data archives without Docker, model access or local datasets:

```sh
.venv/bin/python -m pytest paper/scripts/test_adaptive_comparison_followup.py
```

With the previously pinned benchmark cache, selection can also be recomputed:

```sh
.venv/bin/python paper/scripts/adaptive_comparison_followup.py verify
```

Live controls require the immutable Reddit image and exact dependencies recorded
in the v2 seal. The existing browser-boundary environment supplies those locally:

```sh
benchmarks/.cache/browser_boundary/venv/bin/python paper/scripts/webarena_batched_control.py freeze
benchmarks/.cache/browser_boundary/venv/bin/python paper/scripts/webarena_batched_control.py run
benchmarks/.cache/browser_boundary/venv/bin/python paper/scripts/webarena_batched_control.py export
```

`freeze` refuses an existing run directory, `run` never retries an existing
attempt, and `export` refuses an existing output. These commands are for a fresh
reproduction workspace; do not remove retained local evidence to rerun them.
Version 1's executable source is retained inside its archive, not overwritten.
