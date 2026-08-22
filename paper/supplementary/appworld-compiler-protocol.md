# AppWorld gold-solution compiler protocol

**Status: pre-registered on 2026-08-21. This document was committed before the compiler
was run on this corpus.** It changes no compiler code, no admission gate, no artifact, and
no fallback policy, and it makes no provider call. The predeclared expectation, decision
rule, and preconditions below were written first so that the outcome — in either direction
— cannot later be reframed.

This substrate is different in kind from the three already in the paper. NESTFUL,
API-Bank, and BFCL each retired, and each retirement was arithmetically forced before the
compiler ran: their largest observed family supports were 26, 8, and 15 against a
requirement of 92. A reviewer is entitled to read all three as foregone conclusions rather
than as tests of the gate. AppWorld is run to remove that reading. It is the first external
corpus where the requirement is reachable, so it is the first one where the gate can
actually be wrong.

## Why AppWorld can be a compiler substrate

AppWorld ships 750 tasks over nine simulated apps and 457 typed APIs, with a resettable
per-task application database. The public `minimal` data mode carries gold solution
programs for the `train` and `dev` splits (147 tasks over 49 scenarios); `test_normal`
(168 tasks) and `test_challenge` (417 tasks) ship tasks and evaluators but withhold gold
solutions, so they cannot serve as a post-trace compiler substrate here.

The recorded `ground_truth/api_calls.json` carries method, url, and request data but no
responses, so — exactly as with BFCL's reference plans — `reference_task_to_episode` fails
closed on the shipped artifact. Executing the official gold solution against the pinned
backend supplies the missing field:

| Requirement | Supplied by |
|---|---|
| Ordered calls with observed arguments and results | the official `compiled_solution_code` executed through `AppWorld.execute` on the pinned backend |
| Compatible entry snapshot | each task's own `specs.json` (`supervisor` profile and frozen `datetime`) as `environment`, plus first-appearance gold literals as `inputs` |
| Effect declarations | `benchmarks/contracts/effects/appworld.yaml`, a signed per-API catalog for every API the gold solutions call |
| Replay oracle | a second independent execution of the same solution from the same entry snapshot, in-process and provider-free |

Calls are captured at `Requester.request`, which is the single dispatch point every
`apis.<app>.<api_name>(...)` invocation passes through. The recorded identity is therefore
the semantic `<app>.<api_name>` pair with typed keyword arguments and the decoded JSON
result, not a URL and a form body.

## Two pre-registered arms

The corpus has exactly one contestable effect declaration, and it decides which family can
reach the gate. `*.login` is a POST that mints a bearer credential. It was observed to
leave the application database unchanged on all 184 of its calls, and its token is
byte-identical under re-execution because AppWorld freezes each task's clock. Both
readings are defensible, so both are declared in advance and reported.

**Arm A (primary, conservative).** `*.login` is `WRITE_REVERSIBLE`. Authentication is
treated as a state claim the fixture need not record for the claim to be true. The deepest
compilable prefix is then `supervisor.show_profile -> supervisor.show_account_passwords`.

**Arm B (sensitivity).** `*.login` is `READ_EXTERNAL` with `speculatable` and `replayable`,
licensed by the empirical audit and by byte-exact replay. Exactly those five entries
change; nothing else in the catalog moves. The deepest compilable prefix extends to
`... -> <app>.login`.

Arm A is primary because it is the stricter declaration. Arm B is reported because Arm A's
winning family is argument-free, and a two-call region with no argument slots does not
exercise provenance. Arm B's third call does: its `username` must be witnessed from the
profile result and its `password` from a depth-2 filter-and-project over the
account-passwords result. Reporting only Arm A would overstate what the substrate tests;
reporting only Arm B would understate the barrier.

## Predeclared expectation

**Both arms are expected to reach `exact_gate.outcome = candidate_present`, not `RETIRE`.**

The reasoning is arithmetic and is drawn from a structural pre-check over the shipped
`api_calls.json` files, run before the compiler and before any effect declaration was
written. Every one of the 147 train+dev tasks opens with
`get /supervisor/profile -> get /supervisor/account_passwords`, and 144 of 147 continue
into `post /<app>/auth/token`. Promotion requires 92 independent zero-violation
calibration groups (`configs/promotion.example.yaml`, `min_calibration_groups: 92`, the
exact bound at `alpha=0.05` over an 11-point grid). Each task is one episode and one group,
so a corpus of this shape offers enough support for the first time.

This is therefore the first pre-registered *non-null* prediction in the paper's external
evidence. It is a prediction about support, not about certification. Support at or above 92
makes certification arithmetically possible; whether the family certifies depends on the
held-out replay carrying zero violations, which this protocol does not predict.

Two things this substrate cannot show, stated before the run so they cannot be claimed
after it. It cannot show an efficiency win: no model is run, the gold solution is supplied
rather than predicted, and the number of model boundaries a real AppWorld agent would spend
on the compiled prefix is a property of that agent, not of this corpus. And it cannot show
end-to-end task quality, for the same reason.

## Decision rule

| Observed | Reading |
|---|---|
| `candidate_present` in both arms, held-out replay passing with zero wrong | Predicted outcome. The first external substrate to reach the admission threshold; report the support, the held-out counts, and the fact that Arm A's family is argument-free. |
| `candidate_present` in Arm A only | Predicted outcome, weaker form. The login barrier is then the binding constraint on provenance depth, and that is the finding. |
| `candidate_present`, but a held-out window is *wrong* rather than abstaining | Adverse finding, and it takes precedence over everything else here. A wrong dispatch on a public substrate with sufficient support is the single most reportable outcome available, because it is a failure of the mechanism rather than of the corpus. Report in full. |
| `RETIRE` in both arms | The prediction was wrong. Report the support distribution and the blocking-reason histogram, and state plainly that a fourth corpus retired where the arithmetic said it need not. |

Any precondition below failing means no compiler number is published for this substrate.
The failure is reported instead.

## Preconditions, all fail-closed in the driver

1. **Catalog completeness.** Every `<app>.<api_name>` a gold solution calls has a
   declaration. An undeclared API aborts the run rather than defaulting to `UNKNOWN`.
2. **Clean execution.** A task whose gold solution raises is excluded from the compiler
   corpus and reported as an upstream compatibility outcome, in the same way API-Bank's
   partial re-execution is reported. It is never silently dropped. If fewer than 92 tasks
   execute cleanly the substrate is abandoned, because the arithmetic that motivates the
   run would no longer hold.
3. **Effect declarations are not looser than observed behaviour.** The driver attributes
   every `INSERT`/`UPDATE`/`DELETE`/`CREATE`/`DROP` statement to the enclosing API call. An
   API declared read-like that is observed mutating the database aborts the run. Declaring
   a stricter effect than observed is always permitted; this audit is one-directional.
4. **No `PURE`.** Every AppWorld API reads the per-task database, so no call is a function
   of its arguments alone. A `PURE` declaration in the catalog aborts the run.
5. **Exact replay.** A second independent execution must reproduce every observed result
   byte for byte, including the minted access tokens.

## Fixed parameters

The mining and synthesis parameters are the ones already used for the API-Bank and BFCL
substrates and are not adjustable for power: `max_depth=2`, `kappa=3`, `w_min=2`,
`w_max=12`, `b_min=2`, minimum support of three independent groups before synthesis is
attempted, a held-out split of at most a quarter of a family's groups, 25 synthesis
permutations, and the exact gate at `alpha=0.05`, `delta=0.10` over the 11-point grid. The
entry schema admits `inputs` and `environment`, matching BFCL, because AppWorld genuinely
publishes an entry snapshot.

Groups are tasks, not scenarios. This is the weaker of the two available choices and is
declared as such: AppWorld's three variants of a scenario share a supervisor and an
application database, so their violation indicators are not independent. Scenario-level
grouping would give 49 groups and could not reach 92 under any outcome. The bound reported
here is therefore conditional on task-level independence, which this corpus does not
establish — the same conditional the paper already records for its live GitHub studies,
and it is not weakened or repaired by this substrate.

## Claim boundary

This substrate licenses exactly one kind of statement: that the compiler, its effect
barriers, and its exact promotion gate behave as specified on a public corpus where the
admission threshold is reachable. It does not license a function-calling accuracy claim
(the gold solution is supplied, not predicted, and no model runs), an end-to-end planning
or quality claim, an efficiency claim, or any real-world or production claim.

AppWorld's repository rules prohibit hardcoded API logic in agent logic and warn that
checkpoint reversion is an unfair advantage. Nothing here is a leaderboard submission or
comparable to one: no agent is run, no task is scored against the leaderboard protocol, no
checkpoint is reverted, and only the public `train` and `dev` splits are touched. AppWorld
is a simulator; its results are never pooled with the real-record GitHub workflow families
or with any other substrate.

## Reproduction

Acquisition is provider-free. AppWorld pins `pydantic<2`, which does not build its type
inference on Python 3.14, so the substrate uses a dedicated Python 3.12 environment
separate from the repository's own.

```bash
uv venv --python 3.12 "$APPWORLD_VENV"
VIRTUAL_ENV="$APPWORLD_VENV" uv pip install -r benchmarks/external/requirements/appworld.txt
cd "$BENCHMARK_SOURCE_ROOT/appworld"
"$APPWORLD_VENV/bin/appworld" install
"$APPWORLD_VENV/bin/appworld" download data

python paper/scripts/appworld_compiler_benchmark.py \
  --source-root "$BENCHMARK_SOURCE_ROOT" \
  --appworld-python "$APPWORLD_VENV/bin/python"
```

The driver writes only counts, hashes, structural field names, and per-family aggregates.
Instructions, arguments, observed results, credentials, and application state are not
serialized.

## Observed results

**The prediction held, and the substrate went further than the prediction claimed.** Both
arms reached `candidate_present`, and the deployable compile pipeline then *admitted* an
artifact in both — the first admitted artifact on any external corpus in this paper.

All 147 gold solutions were executed twice on the pinned backend. 136 completed; 11 dev-split
solutions raised against the shipped `0.1.0` database and are reported as upstream
compatibility outcomes rather than dropped, in the same way API-Bank's partial re-execution
is reported. The independent second pass reproduced 7,070/7,070 observed results byte for
byte, minted access tokens included, so the replay-oracle precondition held.

| Quantity | Observed |
|---|---:|
| Tasks collected / clean | 147 / 136 |
| Scenarios / distinct supervisors in the clean corpus | 46 / 79 |
| Observed calls (all with retained results) | 7,070 |
| Calls per task (min / median / max) | 5 / 36 / 244 |
| Distinct APIs declared and exercised | 68 |
| Exact re-execution | 7,070 / 7,070 |
| Mutating calls observed | 1,320 |
| Read-like declarations observed mutating | 0 |
| APIs mutating on some but not all calls | 0 |

### Mining and held-out replay

| | Arm A (`login` write) | Arm B (`login` read) |
|---|---:|---:|
| Compilable / effect-blocked APIs | 32 / 36 | 37 / 31 |
| Candidate families | 43 | 102 |
| Families at or above the support floor | 33 | 87 |
| Families that synthesize | 1 | 19 |
| Held-out replay pass / abstain / **wrong** | 34 / 0 / **0** | 88 / 22 / **0** |
| Largest family support $n_{\max}$ | 136 | 136 |
| Exact-gate outcome | `candidate_present` | `candidate_present` |

$n_{\max}=136$ against a requirement of 92 is the number this substrate exists to produce.
The three substrates already in the paper reached 26, 8, and 15.

### Admission

The deployable pipeline was then run with the calibration share fixed at exactly the 92
groups the bound needs: 22 train, 11 development, 92 calibration, 11 held-out test, split
by seed 20260821.

Both arms admit one artifact, and it is the same artifact in both: the two-step program
`supervisor.show_profile -> supervisor.show_account_passwords`, at 92 of 92 calibration
groups accepted with zero violations, $\hat\eta=0.50$, and $U=0.0498\le\alpha=0.05$.
Held-out replay is 11/11 with zero wrong.

Two properties of that admission have to be stated with it, because both cut against the
result.

**The gate is degenerate.** It admits every calibration group as soon as it admits any:
coverage jumps from 0 at $\eta=0.05$ to 1.00 at $\eta=0.08$ and stays there. This is the
same non-discrimination the paper already reports for five of its six live gates. AppWorld
reproduces that finding on a public corpus; it does not repair it. What the mechanism
provides here is a sample-size requirement and a refusal, not a demonstrated risk--coverage
frontier.

**The admitted program is argument-free.** Both of its calls take no arguments, so the
admitted artifact does not exercise provenance at all. The provenance machinery is what
decided its *length*, not its content — which is the next result.

### What the login barrier actually did

Arm B is where the substrate earns its keep. Six candidates reached the pipeline; one was
admitted, one was dominated, and **four reached calibration and retired**. The four
retirements are not support failures. They are the admission arithmetic biting at the
boundary:

| Candidate window | Support | Eligible calibration groups | $U$ | Outcome |
|---|---:|---:|---:|:--|
| `show_profile -> show_account_passwords -> spotify.login` | 22 | 89 | 0.051 | retire |
| `show_profile -> show_account_passwords -> simple_note.login` | 19 | 90 | 0.051 | retire |
| `show_profile -> show_account_passwords -> spotify.login` (full 3-step program) | 11 | 46 | 1.000 | retire |
| `show_profile -> show_account_passwords -> phone.login` (full 3-step program) | 8 | 26 | 1.000 | retire |

The first two missed by three and two calibration groups respectively, and by 0.001 of
bound. The last two are app-specific, so only the calibration tasks touching that app are
eligible, and 46 and 26 groups cannot reach a 5% bound at any threshold.

The admitted Arm B candidate is the third instance of the same mechanism. Its *mined window*
is three calls including `phone.login`, but its *synthesized program* is two steps: the
login's password slot is not groundable in every supporting group, so the compiler retired
the region and kept its maximal justified prefix. That is the behaviour of
\cref{fig:provenance-wiring} occurring on a public corpus rather than on the paper's own
GitHub record.

### Reading

The substrate does what it was run to do. It removes the reading that the paper's three
external retirements were foregone conclusions, because on this corpus the requirement is
reachable and the gate still refuses four of six candidates — and refuses them at the
margin, on eligible-group counts of 89 and 90 against 92, rather than by an order of
magnitude. It also produces the paper's first external admission, and that admission is
honest about its own smallness: an argument-free two-read prefix, behind a gate that does
not discriminate.

What it does not do is show a saving. No model ran. The admitted artifact removes two
model boundaries out of a median 36 observed calls per task, but the number of boundaries a
real AppWorld agent would spend on those two reads is a property of that agent's interface —
a function-calling agent spends two, a code-as-action agent may spend one — and this corpus
cannot measure it. Every efficiency statement in the paper continues to rest on the live
GitHub families.
