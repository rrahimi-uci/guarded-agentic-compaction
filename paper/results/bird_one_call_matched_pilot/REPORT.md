# BIRD one-call matched continuation: developmental result

**Decision: mechanism feasible; no superiority or GAC-admission claim.** The
research candidate ran a guarded, verified `list_tables()` prefix on all 36
fixed cases and saved model requests against the unchanged agent. Its
final-answer score was lower than the unchanged agent's and the equivalent
handwritten prefix's. A simple handwritten implementation matched the
candidate's continuation input and was at least as efficient in this run.

## Frozen comparison

The [seal](seal.json) fixed 36 corrected BIRD development questions from nine
databases, three arms per question, balanced arm orders, model
`gpt-5.6-luna` with reasoning `none`, a common SQL prompt/tool interface,
12-turn and 600-second episode limits, and a shape-sensitive unordered set
comparison with executable gold SQL. All 108 scheduled episodes are in the
denominator. The original agent began with `list_tables()` in all 36 fresh
attempts. The manual arm executes that call before the first model request.
The candidate arm instead runs the [research program](../bird_one_call_continuation_preflight/candidate.json)
through its hard guard, live tool facade and verifier, then supplies the same
synthetic assistant tool-call and tool-result messages. Both prefixed arms
retain the same user question, prompt, tools, model and answer grader. The
[preflight](../bird_one_call_continuation_preflight/REPORT.md) verified exact
first-tool parity and continuation message shape on these same exposed cases.

The candidate is **not an admitted GAC artifact**. Its source includes the
same 36 exposed traces and nine databases used here; there were zero new
calibration groups and zero independent test groups. The candidate verifier
contains observed schema outcomes, so this run does not test unseen database
schemas. It is a deliberately bounded development mechanism check, not a
prospective population study.

## Observed outcomes

The [machine-readable report](report.json), [sealed raw attempt archive](raw_evidence.tar.gz),
and [campaign ledger snapshot](ledger_snapshot.json) retain every attempt and
request. All 108 episodes completed. The primary result is shape-sensitive set
agreement; costs are conservative accounted upper bounds under the shared
$300 campaign ledger, not provider invoices.

| Arm | Correct / 36 | Provider requests | Tool calls | Accounted upper cost |
|---|---:|---:|---:|---:|
| Unchanged agent | 28 | 151 | 115 | $0.0857444 |
| Handwritten one-call prefix | 28 | 111 | 111 | $0.0761187 |
| Guarded research candidate | 26 | 112 | 112 | $0.0769656 |

The candidate dispatched the prefix 36/36 times with no fallback. Its 39
fewer model requests and $0.0087788 lower accounted cost than baseline are
descriptive savings for these development cases only. The handwritten prefix
saved 40 requests and $0.0096257 with the same 28/36 score as baseline. The
candidate was two questions worse than baseline and handwritten. In paired
baseline/candidate outcomes, baseline alone was correct on three questions
and candidate alone on one; baseline/handwritten had two in each direction.
Manual and candidate synthetic continuation messages were identical for all
36 cases; their two correctness disagreements therefore cannot be attributed to a
different prefetched result or prompt. Independent model completions and arm
order remain possible causes. No p-value, noninferiority margin, or population
effect is inferred from this reused small cohort.

The historical one-arm baseline discovery cost was $0.0838086 accounted upper,
separate from the $0.2388287 spent on this three-arm run. The latter is the
sum of every arm above. Candidate mining, programmer time, and future
recalibration/maintenance costs were not measured, so the arm-only savings
must not be presented as full lifecycle cost benefit. The cumulative shared
campaign ledger ended at $6.3006882 accounted upper, leaving $293.6993118
under the authorized cap.

## Interpretation and next gate

This is evidence that the guard/program/verifier path can execute a saved
one-call prefix and hand off to a model without an adapter error on this
exposed BIRD cohort. It does **not** show that GAC improves the quality–cost
trade-off over the handwritten workflow, that a learned gate adds value, or
that another compiler has been beaten. The candidate is a universal opening
call, with no task-specific branch or useful selective admission; the exact
handwritten wrapper is an equal semantic comparator. Spending the remaining
campaign budget on more repeats of this candidate would not resolve those
objections.

Before a confirmatory claim, find a genuinely adaptive recurrent region whose
compiled behavior differs usefully from a simple wrapper; validate all
comparator paths; freeze a candidate and prospective population before
outcomes; use disjoint calibration and test groups with a justified independent
unit; and count discovery, rejected candidates, guard/fallback, model, tool,
and authoring costs. The [reviewer concern ledger](../../iclr/notes/reviewer_concern_closure.md)
keeps those requirements open. The current manuscript's numerical claims are
unchanged.

## Reproduction and retention

With the pinned corrected BIRD release, nine SQLite databases, original pilot
archive and shared ledger locally available, the sealed sequence was:

```sh
python paper/scripts/bird_one_call_matched_candidate.py
python paper/scripts/bird_one_call_continuation_preflight.py
python paper/scripts/bird_one_call_matched_pilot.py freeze
python paper/scripts/bird_one_call_matched_pilot.py run
python paper/scripts/bird_one_call_matched_pilot.py export
```

The publication validator runs without those private local caches:

```sh
python paper/scripts/validate_artifacts.py --families bird_one_call_development
```

It checks the seal and source hashes, all 108 raw outcomes, paired counts,
published ledger charges, and manual/candidate continuation input parity.
The raw archive and ledger snapshot were scanned against local credential
values before publication. It does not contain databases, `.env`, or hidden
model reasoning.
