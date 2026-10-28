# HMDA v2 live study status (2026-10-28)

## What this note is

A dated status record for the frozen single-domain HMDA study
(`benchmarks/manifests/hmda-study-v2.yaml`, study `hmda-real-records-2026-10`,
protocol digest `44843ccb…aa52`). It changes no main-text section and asserts no
result. It exists so the discussion-window edits do not cite the study as
anything other than what it is: frozen, approved on the macro side, and unrun.

## Where the study stands

- Protocol, pricing, case pool (420 real HMDA groups, 420/420 exact oracle and
  independent gold), and the independent macro approval (Leila Jalali,
  2026-10-07) are in place; the four approval digests were re-derived on
  2026-10-28 and match the implementation.
- The 2026-10-07 discovery attempt (retained at
  `paper/results/multidomain/discovery/`) completed 0 of 40 executions. Its
  cause is now diagnosed: the Agents SDK rejected the strict JSON schema of the
  HMDA answer model (`special_states: dict[str, Literal[...]]`) before any
  provider request. Commit `3ce76b8` fixed that six minutes after the run and
  the fix is pinned by a unit test; the ledger was never re-run.
- The 2026-10-28 re-runs under `paper/results/multidomain/hmda-v2/` first met
  a rejected API key (HTTP 401; no billable request), then, with a rotated key,
  a request bound too low for the five-read oracle (raised from 8 to 20; a
  runner argument, not a frozen value), and finally a systematic answer-schema
  failure: in 8 of 8 attempts across three groups the model's final JSON fills
  `special_states` with code/label objects where the frozen `HmdaAnswer`
  requires bare `NA`/`EXEMPT`/`UNAVAILABLE`/`NOT_APPLICABLE` strings, which the
  SDK's non-strict output mode cannot enforce. The remedy (a prompt or
  answer-type change in `benchmarks/runtime.py`) alters the `evaluator_digest`
  that the signed macro approval binds, so the run stopped there. 0 of 40
  discovery executions completed; development, GRC compilation, the pilot,
  artifact calibration, the independent `calibrate-grc` approval, portfolio
  calibration, test, and analysis have not run. Unmeasured spend on failed
  attempts is bounded above by 0.84 USD. The sequence, the protocol decision
  now required, and the exact re-run commands are in
  `paper/results/multidomain/review/hmda-v2-live-study-handoff.md`.

## What completing it would add to the paper

The retained studies compile programs whose variable path is short; the
vulnerability pool, for example, has an 11% variable-path fraction, which makes
compaction nearly trivial and was the reason that domain was dropped from this
manifest. The HMDA pool is the opposite case: its variable-path fraction is 1.0
(420/420 in the current provider-free validation), and the frozen effect
catalog exposes five `READ_LOCAL` tools keyed on record values
(`get_public_lar_record` on year, LEI, and row digest; `get_hmda_code_label` on
field and value; schema, field-definition, and filer reads on year, field, and
LEI). A correct answer therefore needs a four-to-five-read prefix in which later
arguments depend on earlier results: the code values that the label reads take
as arguments exist only in the record that the first read returns.
A compiled GRC artifact for this workload would therefore have to ground
dependent arguments on prior read results rather than on entry-state constants,
which is the mechanism the main text describes but which the retained evidence
exercises only on shallower prefixes. A completed run would report, under the
frozen contract, whether the compiler admits such an artifact at all, its
abstention and quality-failure counts over 100 frozen pairs at 99% exact
non-inferiority, and the resulting portfolio decision against the hand-written
macro. Until then the paper can cite the study only as a preregistered,
unrun protocol; no efficiency, quality, cost, or cross-domain claim follows
from it.
