# Continuation-graded drift ablation on the primary records (live, capped)

**Status: pre-registered on 2026-10-07. Not run. Requires an explicit spend authorization
before the first provider call; the driver refuses to run live without `--approved-spend-usd`
and executes `--dry-run` schedules only until then.**

## Why a third drift study

The two provider-free drift ablations (simulated substrate; recorded GitHub replay) are both
null, and the second one is null for a structural reason: the suite's oracle is the sequence
of derived call arguments, and every admitted GitHub program derives its arguments from the
entry record alone, so no tool-result perturbation can change a decision. What those studies
could not grade is the one thing the induced verifier is designed to protect: the model's
continuation when the evidence it receives is malformed. This protocol grades it.

## Design

Substrate: the 90 primary held-out records (30 per family), their episodes reconstructed on the
revision-pinned snapshot as in `drift-recorded-replay-protocol.md`. Each record's tool results
are perturbed by one of the nine declared families of `evaluation/perturb.py`; the perturbed
evidence is what the continuation sees.

Two arms on identical (record, perturbation) cells:

| Arm | What runs |
|---|---|
| `guarded` | the retained artifact's program on the perturbed tools; if the induced verifier accepts, the continuation receives the program's evidence and answers without tools; if it abstains (or the interpreter fails), the unchanged agent runs **against the same perturbed tools** |
| `unverified` | the same program with a permissive verifier; it never abstains on contract grounds, so the continuation always receives the perturbed evidence; interpreter failures fall back exactly as above |

The fallback sees the perturbed tools because that is the deployment the paper describes:
abstention hands the task back to the model in the same environment. Giving the fallback clean
tools would manufacture a guarded advantage.

Grading: the family's exact task contract (`grade`) against the **unperturbed** record. The
perturbation models tool-layer corruption of a world that has not changed; a correct system
either answers correctly from what survives or declines to assert what it cannot ground. For
`abstain`-expectation perturbations the contract is applied as is; for `invariant` ones it is
identical to the live study's grading; `tool_4xx` and `tool_timeout` cells are graded on
whether the final answer is correct after fallback.

Primary endpoint, per cell: a **silent wrong answer** (contract failed, no abstention or
fallback recorded). Secondary: contract pass rate per arm and perturbation; abstention and
fallback rates; provider requests per cell (the price of abstention); the `invariant`-family
abstention guardrail (0.25 report, 0.50 bar) from the parent protocol.

Unit and pairing: the record. Per record, "any silent wrong answer across its applicable
perturbation cells" per arm; exact McNemar on discordant records, one comparison, per family
and pooled. Zero counts as one-sided 95% Clopper–Pearson upper bounds.

## Decision rule

| Observed | Reading |
|---|---|
| `guarded` 0 silent wrong records, `unverified` > 0 | The induced verifier's abstentions prevent silent wrong answers on real records under tool-layer corruption; priced by the abstention and fallback rates and the extra requests. |
| Both 0 | Null: the model is robust to these corruptions without the verifier; the verifier's abstentions are cost only. Not equivalence. |
| `guarded` > 0 silent wrong | Adverse; takes precedence; report each record, perturbation and mechanism. |
| `guarded` invariant abstention > 0.50 | No robustness claim regardless. |

## Budget and controls

Cells: 90 records × 9 perturbations × 2 arms = 1,620 continuations, plus fallback runs where
the guarded arm abstains (bounded above by 810). At the retained per-record costs (about
$0.0007 per continuation, about $0.001 per unchanged-agent run) the expected spend is under
$3; the cap is **$15**, enforced by the driver with a per-call reservation and a hard stop.
Model `gpt-5.6-luna`, pricing pinned in
`paper/results/multidomain/pricing/gpt-5.6-luna-2026-10-07.json`, same prompts, schemas and
grader as the live family study, reasoning effort and verbosity `low`, parallel tool calls off,
server-side storage off. Pilot: one family's `null_fields` and `tool_4xx` cells first (120
continuations); the full schedule proceeds only if the pilot's realized cost projects under
the cap. Every attempt, failure and retry is ledgered; results go to
`paper/results/drift_continuation_graded/`.

## Claim boundary

A positive result licenses: on these 90 records under these nine tool-layer corruptions, with
the calibrated model, the induced verifier's abstentions prevent silent wrong final answers at a
stated abstention and request cost. It is not a certificate, not a production-safety claim, not
a statement about other models, and the records are the already-evaluated primary cohort, not a
fresh one. A null licenses nothing about the verifier's value.
