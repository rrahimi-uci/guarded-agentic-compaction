# Safety model

What may be compiled, what may never be, and what every failure path does. This document
is the contract between the compiler and whoever is on call.

## The one-sentence version

A compiled region may contain only tool calls the effect catalog declares as
**pre-commit reads**, every argument must be derivable from entry state or earlier
in-region observations, and every failure before an external commitment lands on the
original agent with the original entry state.

## The effect lattice

| class | may enter a region | why |
|:---|:---|:---|
| `PURE` | yes, with capabilities | no external state at all |
| `READ_LOCAL` | yes, with capabilities | reads local state |
| `READ_EXTERNAL` | yes, with capabilities | reads external state; needs freshness |
| `WRITE_REVERSIBLE` | **no** in v0.x | idempotence alone does not make fallback safe |
| `WRITE_IRREVERSIBLE` | **never** | fallback after commitment is incident recovery |
| `UNKNOWN` | **never** | the default; absence of a declaration is a refusal |

Read-like is necessary and not sufficient. Two capabilities are also required:

* `speculatable` — the call may be made before the model asks for it;
* `replayable` — the same key returns an equivalent result.

`cacheable`, `reorderable` and `batchable` license *specific* extra optimizations
(memoization, parallel reads, fusion) and are never assumed. Read-only and idempotent are
deliberately **not** capabilities: a nominal read can still burn quota, write an audit
row, or observe time-varying data.

Two further declarations exist because deployments differ:

* `approval_required: true` — an immutable barrier. Never compilable regardless of class,
  and a prior approval never licenses a bypass.
* `quota_attested: true` — invoking the tool increments a counter inside the set the
  reversibility attestation covers. A read that writes an audit row must say so; then an
  abort after it is *not* clean and a verifier failure is an incident, not a fallback.

## What terminates a region

* any tool that is not compilable, by the table above;
* a `HANDOFF` — a real semantic transition in session and instruction ownership;
* an `APPROVAL` or `GUARDRAIL` event;
* an errored tool result;
* a slot marked `UNGROUNDED` (its value first appears in a model response and is neither
  constant nor derivable — that is a decision) or `AMBIGUOUS` (more than κ candidate
  producers);
* a live-in that is not an allowlisted entry-state path;
* a window that cuts a repeated call in half.

## The five refusal points

1. **Catalog.** Unlisted or under-declared tools block every window containing them.
2. **Provenance.** A slot with no consistent expression over the closed library is a
   genuine decision. A slot with too many candidate producers is ambiguous. Both refuse.
3. **Contract.** Grouped held-out replay plus a metamorphic perturbation suite. A wrong
   answer is a hard reject; an abstention is acceptable. Without a sandbox the suite is
   *not claimed*, and the artifact ships with that gap documented.
4. **Calibration.** A pre-registered threshold grid with a Bonferroni-corrected
   Clopper–Pearson bound. If no threshold clears the risk budget the answer is `RETIRE`.
5. **Dispatch.** Manifest pins, isolation keys, typed hulls, the gate, the tool allowlist,
   the call budget, the verifier, and the staging attestation — each of which independently
   returns `BASELINE`.

TGWS adds a sixth that is specific to routing. A decision tree's last leaf is a
conjunction of negations, so an entry carrying a categorical value that never appeared in
training matches it *by construction* and would inherit a route whose purity was never
measured on that value. `RouteTree` therefore records the observed domain of every
categorical split feature and `route()` abstains on anything outside it. Numeric `>=`
thresholds are deliberately exempt: they extrapolate by design, and pinning them to
observed values would reject ordinary in-range inputs.

## Failure taxonomy

| situation | outcome | why it is safe |
|:---|:---|:---|
| guard miss, gate reject, shadow mode | `BASELINE` | nothing ran |
| binding failure, assertion failure, tool 4xx/5xx/timeout, budget exhausted, forbidden tool | `BASELINE` | only declared pre-commit reads ran; the entry state is unchanged |
| verifier failure, staging attests reversibility | `BASELINE` | the abort is clean |
| verifier failure, staging **cannot** attest | `INCIDENT` | the runtime does not pretend to roll back |
| a non-stageable effect in the staged multiset | `INCIDENT` | `Staging.commit` refuses |

Catching an exception after an irreversible write and quietly calling the baseline is the
failure mode this design exists to prevent. It is why `INCIDENT` exists as an outcome and
is tested rather than assumed unreachable.

## Isolation

`tenant_partition`, `principal` and `policy_version` are exact guard keys *and* corpus
partition keys. The corpus is split before anything is fitted, so an artifact can never
draw support across an authorization boundary — even when that makes support collapse and
the workload uneconomic. That is a correct outcome, and the negative-control demonstration
exists to show it happening.

## Privacy

* entry state is **allowlisted**: fields outside the contract never leave the application;
* PII-shaped values are redacted or tokenized before storage;
* principals and tenants are stable pseudonyms, never secrets;
* behavioural evidence is partitioned by authorization scope;
* raw payloads are content-addressed so a deletion tombstone can propagate;
* hidden chain-of-thought is never captured — only observable response items, tool calls,
  handoffs, structured outputs and outcomes.

## What this model does not give you

Empirical validation cannot prove semantic equivalence for all future inputs or external
states. What it gives is *selective, evidence-bounded replacement with abstention*, plus a
calibrated statement about the rate at which a dispatch violates its contract—assuming
i.i.d. or conditionally i.i.d. group-level violation indicators under the registered
deployment distribution. Exchangeability alone is not sufficient for the exact binomial
bound, and drift breaks the sampling claim. That is why artifacts expire, why the drift
monitor can retire them, and why a kill switch takes precedence over every other decision.
