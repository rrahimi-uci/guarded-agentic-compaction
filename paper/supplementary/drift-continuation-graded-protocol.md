# Continuation-graded drift ablation on the primary records (live, capped)

**Status: pre-registered on 2026-10-07; EXECUTED the same day under the author's authorization (observed results at the end). Original status: not run; requires an explicit spend authorization
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

## Amendment before execution (2026-10-07, recorded before any provider call)

Issue-type routing is deferred: its retained live harness (`github_live_study.py`) differs from
the two-family harness (`github_workflow_family_study.py`) the driver reuses, and adapting it is
separate work. The study runs on PR-outcome and backlog-attention (60 records, 540 cells per
arm). Injected failures (`tool_4xx`, `tool_timeout`) are surfaced as error payloads, the way the
real tools report `not_found`, not as exceptions. Pilot: PR-outcome `null_fields` and
`tool_4xx`, both arms, all 30 records (120 continuations at most plus fallbacks).

## Pilot findings and second amendment (2026-10-07, before the remaining cells)

The pilot (PR-outcome, `null_fields` and `tool_4xx`, both arms, 30 records, $0.10) ran 120
cells with no failures and no silent wrong answer in either arm. Two facts it exposed are
recorded before the remaining cells run:

1. **The "unverified" arm is not contract-free.** The retained artifacts are packaged as
   pre-model composites whose typed projection rejects a nulled `source_revision` or an
   error-shaped payload (`composite_projection_failed … TypeMismatch`) before any verifier
   clause runs. Type-breaking corruption therefore falls back to the unchanged agent in
   both arms, and a silent wrong answer is impossible there by construction. The contrast
   this study can measure is narrower than written: the induced verifier's hull, cardinality
   and provenance clauses on type-preserving perturbations (`reorder_lists`,
   `duplicate_record`, `pad_lists`, `formatting`, and `empty_lists`/`schema_drift` where the
   projection still types). The pilot's two perturbations are kept and reported descriptively.
2. **Fallback outcomes are not "wrong answers" in the protocol's sense.** Under `null_fields`
   the fallback agent's tools return a nulled title and the agent reports `"null"`; graded
   against the unperturbed record that is a contract miss, but it is a fallback miss on
   corrupted evidence, identical in both arms. Fallback misses are reported as such and never
   as silent wrong answers.
3. **Harness consistency.** The pre-model executor and the fallback tools now perturb the same
   key-sorted serialization, so a transform nulls the same field on both paths. The pilot's
   cells were run before this fix; they are retained and flagged, not reused in the pairing.

**Record-keeping note (2026-10-07).** While setting the pilot cells aside, the raw pilot cell
file was deleted by mistake instead of moved; it was never committed. What survives is the
pilot's printed summary (120 cells, 0 failures, 0 silent wrong in either arm, every cell a
fallback miss, 120 and 147 requests per 30-record block) and its spend ledger
(`ledger_pilot_prefix.json`, $0.0979). The pilot's two perturbations are rerun in full under
the fixed harness, so no reported number depends on the lost file.

## Observed results (executed 2026-10-07; spend $0.5549 of the $15 cap)

Retained: `paper/results/drift_continuation_graded/` (`cells_checkpoint.json`, `results.json`,
`ledger.json`). 1080 cells, 0 failures: 60 records (PR-outcome 30, backlog 30) × 9
perturbations × 2 arms.

**Reading, per the decision rule: ADVERSE, and it takes precedence.** The guarded arm produced
silent wrong answers on **39 of 60 records** (PR-outcome 19, backlog 20), every one under
`empty_lists`. The unverified arm produced exactly the same 39; no discordant record (exact
McNemar p = 1.0). Mechanism, verified against the unperturbed store: `empty_lists` empties the
discussion list (and, for backlog, the assignee list). An empty list is inside the hull the
induced verifier learned from traces (records without comments and without assignees exist), so
the verifier accepts, the artifact dispatches, and the continuation answers faithfully from the
emptied evidence: `comment_evidence: "none"`, and for backlog `owner: "none"` with the route
flipped to `awaiting_first_response`. Against the real record, which has comments (all 19 PR
misses; the 11 correct PR records have none), those answers fail `comment_grounded`,
`route_correct` and `owner_correct`. The contract induced from traces protects against
out-of-hull corruption, not against corruption that lands on a legitimate value.

| Perturbation | Both arms |
|---|---|
| `empty_lists` | dispatched 30/30 in both arms; silent wrong 19 (PR) and 20 (backlog) in **both** |
| `reorder_lists`, `formatting` | dispatched 30/30, exact 30/30, both arms |
| `duplicate_record`, `pad_lists` | guarded: verifier abstained on 11–14 of 30 and fell back (exact 30/30, 63–72 requests per 30); unverified: dispatched 30/30, exact 30/30 at 30 requests. Abstention cost, no benefit |
| `null_fields`, `tool_4xx`, `tool_timeout` | composite projection rejected in both arms; fallback on perturbed tools wrong 30/30 (fallback misses, not silent) |
| `schema_drift` | projection rejected in both arms; fallback agent exact 30/30 through renamed keys |

Guardrail: guarded-arm fallback rate on the three invariant families 0.1389 (below 0.25).
One-sided 95% upper bound on the silent-wrong record rate, either arm: 0.752 (pooled over the
one perturbation that produces it; descriptive).

**What this licenses.** On these 60 records with the calibrated model, the induced verifier
prevented no silent wrong answer: where the corruption left the hull (nulls, errors, renamed
keys) the composite's typed projection already refused in both arms, and where it stayed inside
the hull (emptied lists) neither arm noticed. The verifier's only measured effect is abstention
on duplicated and padded lists where the unverified arm answered correctly anyway. This is the
adverse branch the protocol named; it is a statement about this contract on these corruptions,
not about production safety, and it is the finding the paper's limitations section must carry.

## Corrections after audit (2026-10-07, same day; observed-results text above left as written)

1. **Refusal mechanism.** The observed-results reading attributed out-of-hull refusals to the
   composite's typed projection "in both arms". The cell-level dispatch reasons show otherwise:
   on nulled fields and error payloads the **induced verifier's non-null clauses** refused in the
   guarded arm (`missing:pr.title`, `missing:pr2.source_revision`, …) and the typed projection
   refused only in the permissive arm; on renamed keys the **interpreter's binding** failed in
   both arms (`interp_failed`). The conclusion is unchanged: both arms fell back before any
   continuation, so the verifier adds nothing the projection does not already catch there.
2. **Grader artifact.** `grade()` tested `comment_evidence` as a substring of each comment, so
   the answer `none` was accepted against any comment containing "none". PR 6694 (one comment,
   "…nonetheless…") was graded correct under `empty_lists` in both arms; the true silent-wrong
   count is 40 of 60 in both arms, still with no discordant record. The appendix reports "39 as
   graded" with this note. The grader is fixed so that `none` is grounded only when the record
   has no comments; an audit of every retained row graded by this function found no other
   affected row (the only other hit, backlog 5189, was already graded a miss).
3. **One fallback miss.** `backlog_attention:guarded:duplicate_record` is exact 29/30, not
   30/30: record 5971's fallback on duplicated tools missed comment grounding.
4. **Latency.** The hand-written program ties the re-derived artifact on exactness, requests,
   tokens and cost but not latency; "ties on every axis" in the time-forward protocol is
   corrected there.
