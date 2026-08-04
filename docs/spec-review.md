# Specification review

What implementing `execution-plan.md`, `proposal.md`, `proposal.v1.md` and `use-cases.md`
end to end surfaced. Each finding says where the specification is ambiguous, wrong, or
under-determined, what the implementation does instead, and where to see it.

Findings are grouped: **S** = specification conflict or error, **G** = gap the specs
already flag as needing closure, **D** = discovered while implementing (not in the
documents), **N** = numeric or nomenclature slip.

---

## S — specification conflicts

### S1. The transform library is enumerated with 23 operators and labelled "22"

`proposal.md` §4.3 introduces "the transform library 𝒯 (closed, 22 operators)" and then
lists 5 classes containing 23 forms: 5 identity/coercion, 6 string, 5 numeric, 6
collection, 1 temporal.

*Resolution:* implement the enumerated list. `OPERATOR_CLASSES` in
[dsl.py](../src/agent_compaction/grc/dsl.py) contains 23 operator forms and a test pins
both the count and the class partition, so the discrepancy cannot drift silently.

### S2. Two mutually incompatible transform libraries

`execution-plan.md` §8.2 "Primitive 3" lists a *different* library —
`field, literal, coalesce, get, index, concat, lower, upper, strip, split, join, replace,
prefix, suffix, format, cast, parse_date, date_add, json_select, length, contains,
lookup_enum` — which shares only 6 names with `proposal.md` §4.3 and has no collection
operators at all. Without `filter`/`project` the dominant real pattern of §4.3
("select the right record from a list, then project one field") is unexpressible, so the
two libraries are not interchangeable.

*Resolution:* follow `proposal.md` §4.3, as the execution plan's own §3 says conflicts
resolve in favour of v2.1. The execution plan's list should be corrected rather than
treated as an alternative.

### S3. Algorithm 4's atom restriction contradicts the worked artifact

`proposal.md` §4.4 line 3 restricts branch atoms to `paths(H)` — paths visible in the
hard guard, which is evaluated at *entry*. `use-cases.md` §1 then compiles the branch
`sub.tier == "enterprise"`, where `sub` is an **in-region observation** that cannot be
guard-visible. Both cannot hold.

*Resolution:* atoms are drawn from paths observable *at the divergence point* (entry
state plus in-region observations up to that step), with guard-visible paths ranked
first. The support floor (20 groups), leave-one-group-out, and the permutation test are
kept as the actual defence. See `_atoms` and `synthesize_branch` in
[synthesize.py](../src/agent_compaction/grc/synthesize.py).

### S4. Indexing model responses as provenance producers is circular

`proposal.md` §4.1 line 15 adds outputs of `MODEL_RESP` events to the producer index.
But the response that emits a tool call trivially "produces" that call's own arguments,
so every slot exact-matches itself, `|S| ≥ 1` always holds, and Eq. (4)'s test — "the
value first appears in a model response, therefore this is a decision" — can never fire.

*Resolution:* model-response values go into a *separate* index used only to mark a slot
as model-originated. They are never grounding sources. Without this the reference use
case reports 100% grounded slots and mines regions that encode decisions; with it,
`resolution_note` is correctly `UNGROUNDED`. See `build_patg` in
[provenance.py](../src/agent_compaction/graph/provenance.py).

### S5. Algorithm 2's line order discards the entry state (already flagged, and worse than described)

`use-cases.md` §1 notes that line 10 (reject `UNGROUNDED` slots) fires before line 11
(rescue entry-state live-ins), so without seeding `z` the reference artifact does not
exist. Implementing it shows the problem is not only ordering: a *transform* over an
entry-state field (`lower(email)`) cannot be recovered by an `EntryStateSchema` check at
all, only by seeding `z` into the index before the event scan.

*Resolution:* seed `z` as pseudo-producer 0, as `proposal.md` §4.1's own commentary
requires. Both the ordering fix and the seeding are implemented.

---

## G — gaps the specifications flag, and how they are closed

| Gap (source) | Closure |
|:---|:---|
| `cx.compile()` takes no tenant/principal argument (proposal §6.5) | `partition_by=` on `optimize()`/`GrcConfig`/`TgwsConfig`. The corpus is **partitioned before fitting**, not merely pinned afterwards: `compile_grc` and `compile_tgws` recurse per partition and never pool. |
| `@cx.compact` has no `mode=` (proposal §6.5) | `compact(..., mode="shadow"|"live"|"off")` in [runner.py](../src/agent_compaction/runtime/runner.py). |
| The catalog cannot mark a slot literal-only (proposal §6.5) | `literal_only: [slot]` per tool, checked in Algorithm 3 *before* enumeration. `billing.list_invoices.limit` and `search.retrieve.k` use it. |
| Θ is a static stoplist (proposal §6.2 row 1, §6.5) | Corpus-derived per-field cardinality and top-share filter in `GroundabilityPolicy`, fitted by `field_statistics`. The stoplist survives only as a cheap first pass. |
| Production has no scenario ids (proposal §6.2 row 2) | Support is counted by group **and** principal **and** day, all three configurable minima. |
| Algorithm 5 cannot replay production (proposal §6.3) | Three separate report objects — recorded replay, sandbox replay, perturbation suite — and a `perturbations_claimed` flag. With no sandbox the suite is *not claimed*, and `validate()` says so in words. |
| `stage.reversible()` cannot be attested in a distributed system (proposal §6.2 row 7) | The attested set is explicit (`Snapshot`), and which counters belong to it is **configuration**: `quota_attested` per tool. A read that increments an attested counter makes the abort dirty, which is tested. |
| Per-arm live-out contracts (use-cases §1) | `OutputClause.present_iff`, induced per arm; an unconditional `non_null` on a conditional output would reject the other arm and is tested not to. |

---

## D — discovered while implementing

### D1. MDL alone picks the *wrong* binding

Algorithm 3 line 10 ranks by `(MDL, |σ|, lex)`. On real data `last |> project(id)` and
`filter(status == "active") |> project(id)` are both consistent whenever the wanted
record happens to be last, and MDL prefers `last`. The specification's own commentary
(§4.1: positional paths are "unstable across users"; §4.3: the select-then-project
pattern is what makes the artifact generalise) wants the opposite.

*Resolution:* an explicit order-stability rank ahead of MDL — `filter` < projection <
`sort`/`topk` < `first`/`last` — plus a penalty on source paths containing list indices.
`OP_INSTABILITY` and `chain_rank` in [dsl.py](../src/agent_compaction/grc/dsl.py).
Without it the demo compiles a binding the perturbation suite then rejects; with it, the
documented artifact is synthesized directly.

### D2. Observational-equivalence pruning silently deletes the correct chain

Deduplicating the search frontier by denotation (proposal §4.8) is sound *within* a
trace and unsound *across* traces: `topk(account, 1)` and `filter(status == "active")`
have the same denotation on a two-record list, so whichever is generated first evicts the
other — and they differ on the next trace.

*Resolution:* the frontier keeps the most order-stable representative per denotation
rather than the first, and candidate chains are enumerated from several supporting traces
rather than one. Both are needed: the correct chain is often a *no-op* in the simplest
trace (`filter` over a single-record list) and would never be generated there.

### D3. Filter constants drawn from the target memorise the answer

`filter(id == "cus_8000C1") |> project(id)` fits any single trace perfectly and
generalises to nothing. Algorithm 3's cross-trace check rejects it — but only after it
has crowded the ranked candidate list.

*Resolution:* filter constants equal to the sought value are never generated
(`_same_scalar` guard in `candidate_ops`), with a test.

### D4. Window truncation manufactures incoherent loops

Bounded windows are enumerated over all `(a, b)` pairs, so a window can end in the middle
of a repeated call. Its last iteration then looks like a termination even though the
episode continued, and no termination predicate can be consistent with the run.

*Resolution:* `BlockReason.PARTIAL_RUN` — a window whose final step is immediately
followed by another call to the same tool is not a candidate. On Demo B this is 26% of
blocked window mass, so the effect is not marginal.

### D5. Branch labels are contaminated by mining rejections

The divergence label ("did the baseline take the long arm") was read from window
admissibility. An episode that *did* take the long arm but whose long-arm window was
blocked (one extra candidate producer pushed a slot over κ) is then labelled as the short
arm. With ~8% such episodes, Algorithm 4 correctly reports "not separable" for a branch
that is perfectly explainable.

*Resolution:* the label comes from the episode's observable behaviour; episodes whose
long-arm window was blocked are **excluded from the family** rather than mislabelled.
Support drops, correctness does not. `_called_after` in
[windows.py](../src/agent_compaction/graph/windows.py).

### D6. Several atoms separate perfectly, and the algorithm does not say which to pick

With ~500 atoms and ~60 groups, 9 atoms separated the Demo A divergence perfectly
(`subs.plan_id == "plan_ent_240"`, `subs.tier == "enterprise"`,
`invo.invoices[0].line_items len> 1`, …). Algorithm 4 returns "a" separating atom; which
one it returns is an implementation detail that changes what a reviewer reads and how the
artifact behaves off-distribution.

*Resolution:* atoms are ordered (guard-visible first, then order-independent, then
lexical) and the number of alternatives is reported in the artifact evidence as
`branch_alternatives`. A branch with many equally-separating atoms is a signal, not a
detail.

### D7. Prefix-extension families never meet, so no branch can be discovered

The two arms of a conditional region have different canonical hashes by construction, so
the published mining algorithm can never produce the branching artifact that
`use-cases.md` §1 shows. `AddControlEdges` (line 16) is described at slot level and does
not merge families.

*Resolution:* explicit family merging on *tool sequences* (not hashes, which fragment),
one window per episode keeping the longest arm, capped and ranked by support.

### D8. Gate features must be serialised with the artifact

Calibration fits a feature extractor on the training distribution; the runtime has to
compute *byte-identical* features or the Eq. (18) certificate does not describe what the
gate actually does. A plausible-looking re-implementation in the dispatcher produced
`q = 1.0` for every episode — a 100% abstention rate that looks like conservatism and is
actually a bug.

*Resolution:* the fitted `GateFeatures` travel inside `Gate.features_spec` and both paths
call the same code.

### D9. Feature semantics must follow the hull kind, not the value type

An `unseen_category` signal computed by set membership fires on every unseen episode when
the field is high-cardinality (an email, a document id), which is *always*. The score
then saturates and the gate rejects everything.

*Resolution:* enum hulls contribute unseen-category mass, interval hulls contribute
margin, regex hulls contribute a violation flag. Also: near-zero feature variance must be
treated as zero (dividing by `1e-15` is how the saturation above happened).

### D10. Eq. (10) is a GRC-only ceiling

The estimator's `Δ_max = φ·k / n_B` counts requests removed by compiled *regions*. It
does not model TGWS removing a predictable coordinator turn. Demo C reports
`feasible = no` at a 6.1% region ceiling and then measures an 18.1% request reduction,
almost all of it from routing.

*Resolution:* the estimator says so in its own notes, and `docs/results.md` repeats it.
A route-savings term belongs in the estimator; it is not in the specification.

### D11. TGWS route calibration cannot use path imitation as the violation label

Calibrating the route gate on "the route disagrees with what the baseline did" makes
every baseline mistake a violation. With 7–10% baseline misroutes the exact bound cannot
clear α = 0.05 at any sample size, so every leaf retires — including leaves that *improve*
outcomes by routing around the mistake.

*Resolution:* the violation label is a measured outcome degradation (each calibration
episode is run under both configurations), which is what execution-plan §8.1 asks for:
"compare against task outcomes, not mere path imitation". Route mismatch is retained as a
reported diagnostic.

### D12. Paired conditions need a separate policy RNG stream

Sharing one random stream between the cost model and the agent's own deviation draws
means every removed request re-rolls every later deviation, which shows up as spurious
quality and safety differences between conditions. Paired statistics on such data measure
the plumbing.

*Resolution:* a dedicated `policy_rng` per episode. This is a property of any simulated
evaluation harness and worth stating in a methods section.

### D13. "Span completeness" is not the truncation flag

Gate 0 requires ≥95% required-span completeness. Implemented as "no event marked
truncated", it reports 100% on a corpus with dropped tool results — the failure mode
capture pipelines actually produce.

*Resolution:* completeness counts episodes free of *any* span defect: truncation, missing
result, orphan result, missing boundary.

### D14. Artifact selection is unspecified

Mining plus synthesis yields overlapping artifacts (a 4-step region and its 5-step
extension) that fire on the same episodes. Nothing in the specification says which to
keep, and keeping both doubles the maintenance surface for no coverage.

*Resolution:* prefix-dominated artifacts within a partition are dropped, ranked by
`(removed requests, support, name)`. Reported as `select:dominated`.

### D15. The hand-written comparator wins more often than the documents imply

Measured on this substrate: the macro tool beats full compaction on Demo A
(0.726 vs 0.755) and decisively on Demo B (0.335 vs 0.718), and loses on Demo C
(0.922 vs 0.819). Proposal §6.6 predicts the *direction*; the size of the gap on a
mechanical pipeline (Demo B collapses eight paginated calls into one tool) is larger than
"one model request per invocation" suggests. Where a region is a fixed pipeline, the
compiler's value is discovery and maintenance, not the saving.

### D16. A read-only artifact can still change downstream write rates

Compaction touched no write, yet making evidence gathering deterministic changed how
often the *host agent's* later refund fired: the baseline sometimes skipped fetching
invoices and therefore could not issue one. On Demo A the hand-written macro shows this
(44 → 47 safety events) while the compiled region does not (44 → 44).

*Resolution:* two separate endpoints — `artifact_write_effects` (a hard gate, must be
zero) and downstream `safety_events` (reported with its mechanism). Conflating them
either hides a real regression or fails a candidate for something it did not do. Neither
endpoint exists in the specification.

---

## N — numeric and nomenclature slips

* **N1.** `proposal.md` §4.6 states the guarantee as Eq. (18) and then writes "so (19)
  does not transfer there"; there is no Eq. (19) in that neighbourhood.
* **N2.** `execution-plan.md` §6 gives the effect classes as
  `PURE|READ|WRITE|EXTERNAL|UNKNOWN` while `proposal.md` §5.3 uses
  `READ_LOCAL|READ_EXTERNAL|WRITE_IRREVERSIBLE`. The implementation follows v2.1 and adds
  `WRITE_REVERSIBLE` for completeness (never compilable in v0.x).
* **N3.** `use-cases.md` §1 reports `κ = 3` and simultaneously that a fourth producer
  appears at `entitlements.check`; on this substrate that is exactly what happens, and the
  window is discarded. The number is right and the consequence is under-stated: at κ = 3
  the 5-call region does not exist, and κ = 4 buys it at the cost of admitting a genuinely
  ambiguous slot. That trade deserves to be a documented knob, which it now is.
* **N4.** The illustrative `n_B` values (11.5–22.3) and savings (5–10%) are labelled
  illustrative throughout, and this implementation does not inherit them. Measured `n_B`
  on the simulated substrate is 10.4–11.3.
* **N5.** `proposal.md` cites `arxiv.org/abs/2606.04990` for an execution-provenance
  survey. It could not be verified in this offline environment; the related-work matrix
  marks it unverified rather than asserting it exists.

---

## Things the specifications got right that were tempting to get wrong

* **Rejection as the normal output.** Every stage counts *why* it refused, and the
  rejection funnel is a first-class figure. Across the four demonstrations 4–247
  rejections are recorded per demonstration and 0–5 GRC artifacts survive; on the negative
  control all 7 candidates retire at the gate and nothing ships.
* **The exact bound over the point estimate.** With ~60 calibration groups nothing
  certifies at α = 0.05; the honest report is `RETIRE`, and the estimator predicts the
  required group count (92) before any compilation. Measured: 15 of 40 RAG candidates and
  7 of 7 negative-control candidates retire there.
* **Abstention over cleverness.** Every failure path in the interpreter, facade, staging
  and dispatcher lands on `BASELINE`. The only path to `INCIDENT` is a commitment that
  v0.x forbids, and it is implemented and tested rather than assumed unreachable.
* **The catalog as the safety boundary.** Making effects configuration rather than
  inference is what let this be built in one pass; every "why did nothing compile" answer
  traces back to a catalog line.
