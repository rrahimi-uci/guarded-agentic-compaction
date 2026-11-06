# AppWorld adaptive-workflow development pilot

This is a bounded development screen, not a confirmatory experiment. It follows the
browser-boundary study, whose useful but trivial form-opening candidate does not
establish distinctive compiler value. No benchmark outcome or admission is promised.

**Completed disposition: interrupted, original grades invalid, no confirmatory go.**
See the [retained report](../../paper/results/appworld_adaptive_viability/REPORT.md).
Nine episodes finished with invalid on-disk grades, one was interrupted, and fourteen
were never started. The reference controls used `AppWorld.execute`, which persists
state; direct model API calls used `Requester.request`, which does not. The original
adapter omitted the explicit save required before the grader reads disk state.

The corrected worker saves before closing and propagates a save failure as an
operational failure. A known-correct 25-call sequence with identical responses
changed from 0/6 to 6/6 passing assertions. All three positive/negative controls
through the actual direct-call path pass. Nine completed histories were regraded
without new model calls and with exact context/result parity; none passed. Those
regrades are diagnostic, not fresh trials or a comparative estimate. The original
records, source bytes, stopped attempt, pre-run plan and explicit analysis amendment
remain retained. No paid retry, replacement task or resumption was performed.

Before paid execution, the v1 reference control passed only four of six checks on
one selected case because the official evaluator raised SQLite missing-table
exceptions. Direct execution outside our worker, the upstream default seed and
grading before shutdown reproduced the error. The same task/reference/grader
passed with SQLAlchemy 2.0.44 and SQLModel 0.0.44. The v2 seal therefore changes only
the runtime dependency image and namespace and reruns all 36 controls. The original
environment, source seal, failed checks and diagnostics are retained. This is a
working compatibility set, not isolated attribution to one dependency. Upstream's
[separate SQLModel compatibility report](https://github.com/StonyBrookNLP/appworld/issues/229)
motivates caution with unconstrained installs but does not diagnose our error.

The structural limitation of the initial read catalog was recorded in
`v2/analysis_plan.json` before provider calls: it permits only documentation/profile/
password prefixes, so this version cannot meet the nontrivial-family gate. Paid
execution is limited to the descriptive baseline/manual continuation comparison;
it cannot authorize a larger confirmatory compiler-value study regardless of score.

The unchanged earlier hash selection chooses 12 of the 30 official AppWorld 0.2.0
training scenarios, one variation each. All are development-only: historical
train/dev references and test trajectories were already inspected. The first eight
selected scenarios are discovery groups; the last four are challenge groups. There
is no calibration or final-test cohort. Scenario variants cannot inflate group counts.

Before paid execution, run reference, empty and false-completion controls on **all
12 selected tasks**, using the official nonempty executable test suite. Any failed
control blocks paid execution for the entire cohort. Do not replace a difficult or
broken task after seeing its outcome. Raw task instructions, reference output, API
results and traces stay in the ignored cache and are redistributed only through the
upstream encrypted bundle format. Public reports contain structural aggregates and
hashes. No reference answer, test specification or private API is exposed to the agent.

## Frozen comparison

Both arms use the same isolated immutable image, public API tool, instructions,
model, context policy, 24-model-request limit, 48-API-call limit and 600-second episode
timeout. The baseline starts without a prefix. The handwritten arm executes the
previously known `supervisor.show_profile` and `supervisor.show_account_passwords`
reads, then supplies their actual action/result history to the model continuation.
Those two calls count toward its API limit. They are not imagined observations or
additional oracle information. Alternating arm order across the fixed task list
balances which arm runs first; this is a single descriptive run per arm/task.

The persistent shared campaign ledger remains authoritative. This pilot adds an
$8 local allocation inside the existing $30 discovery stage and $300 total cap.
Requests reserve their conservative maximum charge before transmission. Prior
reservations, unsuccessful calls and unknown usage remain charged. The process is
locked to one runner; no model retries, replacement tasks or repeat paid attempts.
All scheduled arms remain in the denominator. An operational/provider/budget or
audited-read effect violation stops execution and leaves missing arms explicit.

The model receives all task/action history but only the last four API results, each
capped at 16,000 characters; raw results remain complete in the evidence. This
policy is identical across arms and is frozen before execution. The literal
handwritten prefix is a simple comparator derived from prior work, not an automatic
GAC artifact or a claimed solution to the reviewers' compiler-value objection.

## Candidate viability gate

Run discovery over every baseline trace, retaining failures and errors. The checked
effect catalog permits only the six source-audited documentation/supervisor reads
on the pinned 0.2.0 implementation. All login APIs remain barriers despite any
determinism in the simulator; other APIs remain unknown. Each agent call records
observed SQL operation names. This diagnostic is not proof of absent filesystem,
credential or external effects. The old 0.1.3 catalog is not silently reused.

Use prefix lengths 2–4, minimum training support 3 scenarios, and at least two saved
model requests. Challenge uses only the four reserved development scenarios. A
documentation-only or profile/password-only program is classified as trivial for
the scientific objective even if it synthesizes correctly. Two distinct nontrivial
families must survive before calling this a viable multi-family guarded-compilation
comparison. Do not relax these criteria after the results. No calibration means no
admitted GAC artifact; any future mechanism-only execution must be labeled unadmitted.

Report final task success, actual model/API calls, conservative API accounting,
elapsed time including setup and grading, paired discordances, error/termination
counts and the complete candidate rejection funnel. Twelve previously exposed
scenarios do not support a population guarantee, noninferiority claim, learned-gate
benefit, native competing-compiler ranking or maintenance-economics claim. There is
no faithful Agent JIT/EvoC2F comparison in these two arms.

If the candidate gate fails, report **NO_GO** and retain the refusal; do not spend
the remaining campaign budget on a larger confirmation of this same inadequate
workload. If it passes, freeze a separate prospective matched-compiler protocol,
unfiltered calibration population, independence unit, quality margin, multiplicity,
fresh test groups and cost accounting before further execution.

## Reproduction

The corrected worker uses the compatible dependency image recorded in the retained
seal, derived from the immutable image and upstream revision in
`appworld_reference_study.py`. The dependency layer is specified in `Dockerfile`. It has no network, host credentials or
Docker socket and has read-only access to only its trusted worker source. The
controller uses the existing host `.env` solely for provider authentication.

```sh
.venv/bin/python -m pytest -o addopts='' -q paper/scripts/test_appworld_adaptive_viability.py
```

The original freeze/control/run commands and exact executed source bytes are in the
encrypted evidence's `v2/sealed_sources`. Current `verify()` rejects their source
hashes because the worker and controller have a recorded correction. An explicit
stop marker also blocks resumption. Do not recreate the seal merely to bypass it.
`verify_records()` verifies the immutable historical source copies for analysis.

`repair_appworld_viability.py` records the provider-free repair plan and runs only
known public API calls; it never invokes a model. Its separate source hashes, input
record hashes, negative controls and response/context parity checks bind the repair.
`analyze_appworld_viability.py` marks original outcome labels unknown and publishes
all 24 dispositions. `export_appworld_viability.py` retains the original and amended
analysis hashes and round-trips the encrypted complete evidence. Reproduction needs
the pinned upstream data/image and locally decrypted records; ordinary CI checks
only public structural evidence and offline adapter tests.

Do not overwrite a seal or reset the shared campaign ledger. Preserve the prior
browser and SQL pilot sources and reports. Changes require a documented amendment
and separate attempt namespace; they do not retroactively repair earlier evidence.
