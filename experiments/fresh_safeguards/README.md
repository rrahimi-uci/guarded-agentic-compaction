# Fresh-record safeguard comparison

This is a prospective **exploratory fixed-artifact comparison**, implemented to
answer whether GAC's restrictions buy measurable task quality on unused public
issue records. Preflight executes real snapshot tools and the real dispatcher,
without a model call. It cannot measure final-answer accuracy or speed savings.
The paper's existing results, tables, and statistical certificates are unchanged.

## Frozen design

The default cohort is 120 previously unused, deduplicated non-PR issues from the
pinned historical GitHub snapshot. Selection uses a fixed hash seed, excludes
named IDs and integer selection arrays found in prior result JSON, and does not
filter on answer correctness, label count, comment syntax, or dispatch success.
Exclusions conservatively include collisions with other GitHub record namespaces.
The snapshot itself is not scanned as prior experimental exposure. This is not a
new time-forward population. Comments/strata are described after selection only.

All four arms run on every selected record, including GAC fallback records:

| Arm | Program and admission |
| --- | --- |
| `baseline` | Unchanged agent and three snapshot tools |
| `gac` | Artifact reconstructed from primary issue-type discovery; frozen program, hard guard, calibrated score, verifier, effects, and fallback |
| `support_only` | Deep copy of that artifact; retains the 92-group support prerequisite, program, hard guard, verifier and effects; replaces score/admission with accept-all and explicitly has no risk certificate |
| `recurrence_only` | Previously defined three-read replay with the majority `comments.limit=100` literal, followed by a single tool-free answer generation |

The same model (`gpt-5.6-luna`), task instructions, structured answer schema, source
snapshot, and factuality grader are used throughout. Recurrence replay necessarily
changes evidence packaging and exposes no tools to its continuation. Consequently
GAC versus recurrence does not isolate one guard causally. GAC versus support-only
isolates the runtime score/admission rule conditional on an already admitted
candidate; it does not test mining, candidate selection, or refusal at compile time.
There is no guarantee that these arms differ on this population.

If the installed runtime differs from the historical manifest, preflight
reconstructs the existing 132 discovery traces on the pinned snapshot and runs the
existing compiler under the current manifest. It requires exact reproduction of
the retained program, admission counts/bound/threshold, and split digest before
proceeding. It records both compatibility keys and changed guard/verifier/gate
components. The current compiler treats identifier hulls as unconstrained rather
than numeric intervals; reconstruction therefore changes the identifier guard,
verifier clause, and gate feature specification relative to the historical
artifact. Both comparison arms use the same newly reconstructed contracts. This
is not an exact replication of every historical runtime constraint. This is provider-free reconstruction of historical
discovery, not fresh model discovery and not silent manifest reassignment. Any
failed reproduction blocks execution; it cannot be fixed by filtering test cases.

Every permutation of the four arms occurs equally often (record count must be a
multiple of 24). Records run sequentially in sealed hash order, one provider
operation at a time. Counterbalancing reduces order confounding but cannot remove
service drift. No model answers are collected during preflight. Source hashes,
protocol, runtime code, dependency versions, rate card, cohort, arm definitions,
and order are frozen before evaluation; changes require a separately documented
amendment and a new output directory, never overwriting the old run.

## Outcomes and interpretation

The primary quality endpoint is the existing `factuality_exact` task contract,
independent of tool order. Report every arm's scheduled, attempted, completed,
failed, correct, dispatched, and wrong-after-dispatch counts. A provider failure
is a task failure among attempted pairs; an unattempted operation is separately
reported and is not an observed answer. Paired baseline-only and candidate-only
success counts describe the tradeoff. No noninferiority margin is chosen after
seeing outcomes. The default sample is exploratory and carries no power claim.

Requests, tokens, actual snapshot calls, latency, and estimated cost are reported.
Recurrence latency includes its deterministic reads. Complete-case resource totals
are marked incomplete whenever failed or unattempted operations exist; they do
not become full-cohort efficiency estimates. Prices are the frozen repository
rate card, not current prices or invoices. Discovery and human authoring costs
are historical and excluded, so this study does not establish lifecycle savings.

- Equal quality and cheaper recurrence is evidence against an incremental benefit
  of GAC on this cohort; report it without explaining it away.
- A GAC refusal is not proof of avoided harm. Inspect the matched baseline and
  recurrence answers before describing protection, and distinguish association
  from mechanism attribution.
- Identical GAC/support behavior is a valid null result for the gate comparison.
- Wrong answers after GAC dispatch must remain in the reported results. Replay
  certificates do not certify these final answers.
- Additional synthetic corruption studies must have separate protocols and result
  labels; none are mixed into this naturally sampled comparison.

## Commands

From the repository root, with the repository environment and live extras:

```bash
PYTHONPATH=src .venv/bin/python paper/scripts/fresh_safeguard_comparison.py preflight
PYTHONPATH=src .venv/bin/python paper/scripts/fresh_safeguard_comparison.py verify
PYTHONPATH=src .venv/bin/python -m pytest paper/scripts/test_fresh_safeguard_comparison.py
```

`preflight` refuses an existing seal. `verify` does not rewrite files or execute
provider calls. The checked-in preflight records local dependency versions; a
live execution must reproduce those versions or seal a new declared run.

Paid execution requires a separately chosen `--approved-spend-usd` and an API key
in the environment, optionally loaded using `--env-file /absolute/path/to/.env`.
No key, paid execution, or authorized budget is implied by generating a preflight.
The default cohort schedules 480 agent episodes, potentially several requests per
episode. The budget check reserves $1 before each episode and retains a $1 unknown
cost reserve for failures. This is a conservative **estimated-spend guard**, not a
provider billing cap: an individual operation can exceed the reserve. The runner
uses no application retries, disables OpenAI transport retries, and stores local
trace-derived metrics without uploading traces. A pending-call checkpoint is
written before execution; interrupted or failed runs cannot automatically retry.
Clean checkpoints can resume only with the identical seal and spend cap.

```bash
# Replace APPROVED_CAP with the explicitly chosen numeric budget.
PYTHONPATH=src .venv/bin/python paper/scripts/fresh_safeguard_comparison.py run --approved-spend-usd APPROVED_CAP
PYTHONPATH=src .venv/bin/python paper/scripts/fresh_safeguard_comparison.py summarize
```

There is no production configuration change, deployment, data migration, or new
paper claim. This experimental driver is isolated from published result paths.
