# Intuition plan for Sections 2--3

> **Status: executed.**  Every item below has shipped in `paper/tex/body.tex` and both
> builds.  See *What shipped* at the end of this document for the plan-item-to-artifact
> map and for the two places where the implementation deliberately departs from the plan.
> The equation, algorithm, figure, and table numbers quoted in the plan body are the
> numbers as they stood *before* execution; the post-execution numbering is recorded in
> *What shipped*.  Nothing in the manuscript refers to any of them by printed number.

## Purpose and editorial rule

This is a revision plan for the manuscript body, `paper/tex/body.tex`, especially Section 2
(*Problem Formulation*, `sec:problem`) and Section 3 (*Guarded Agentic Compaction*,
`sec:method`).  `body.tex` and `abstract-body.tex` are the only places manuscript prose
exists; `paper/open_research/article.pdf` (single-column, with appendix) and
`paper/open_research/main.pdf` (two-column ACM submission) are wrapper builds of that same
body, so every change below is made once in `body.tex` and must survive both builds.  The
condensed `paper/ICLR/` variant is out of scope for this plan.

Nothing here proposes weakening, moving, or replacing any definition, algorithm,
qualification condition, or stated limitation.  The preferred editorial pattern is:

1. state the formal definition or claim unchanged;
2. immediately show one concrete execution of that definition;
3. use a labeled figure to make the same constraint visible; and
4. point the reader back to the equation, algorithm, or boundary that remains
   authoritative.

Three mechanical rules apply to every item in this plan:

- **Refer by label, never by printed number.**  Use `\cref{fig:pipeline}`,
  `\eqref{eq:grounding}`, `\cref{alg:patg}`, and so on.  The article already carries 10
  figures, 4 algorithms, and 12 tables; inserting anything renumbers everything after it.
  The `F1`--`F12` identifiers below are planning handles only and must not reach the text.
- **Add no new empirical claim.**  Every number a new figure prints must already appear in
  `body.tex` or in the sealed results the figure is generated from.  The verified-anchor
  table below is the whitelist.
- **Do not duplicate an existing figure.**  Three proposals overlap artwork that already
  exists (`fig:aha-example`, `fig:pipeline`, `fig:gate-support`, `fig:pilot-ablation`);
  each is reconciled explicitly rather than drawn twice.

The running example should be the already-reported expanded GitHub issue workflow, not a
new hypothetical result.  It has an unusually useful negative case: the compiler can
ground `record` and `labels`, but it must refuse the third `comments` read because the
model-selected `limit` is not reconstructible.  That lets the paper teach that GAC is a
*conservative partial substitution*, rather than an attractive macro extractor.

## Verified anchors (as built, 2026-08 article build)

Numbering and facts below were read from `paper/tex/body.tex` and
`paper/open_research/article.aux`.  Re-check this table before executing the plan; if a
number here disagrees with the source, the source wins.

| Anchor | Label | As built |
| --- | --- | --- |
| Groundability | `eq:grounding` | Eq. (1) |
| Position invariant `a=0` | `eq:prefix` | Eq. (2) |
| Selective dispatch `d_A(z)` | (unlabeled) | Eq. (3) |
| Savings objective | (first line of the align) | Eq. (4) |
| Selective-risk constraint | `eq:objective` | Eq. (5) |
| Family ranking score | `eq:score` | Eq. (6) |
| Feasibility ceiling | `eq:ceiling` | Eq. (7) |
| Clopper--Pearson bound `U_eta` | `eq:cp` | Eq. (8) |
| Compile cascade | `alg:compile` | Algorithm 1, in the Section 3 opening (before 3.1) |
| `BuildPatg` | `alg:patg` | Algorithm 2, inside 3.1 |
| `Calibrate` | `alg:calibrate` | Algorithm 3, inside 3.6 |
| `Dispatch` | `alg:dispatch` | Algorithm 4, inside 3.8 |
| Two-cohort motivating figure | `fig:aha-example` | Figure 1, in the Introduction |
| System architecture | `fig:pipeline` | Figure 2, opening Section 3 |
| Admission register | `tab:admission-register` | Table 1, Section 3.6.1 |
| Subsections | --- | 3.1 provenance/families, 3.2 synthesis/contracts, 3.3 worked example, 3.4 GCS, 3.5 manual & learned interfaces, 3.6 risk-gated admission, 3.6.1 admission register, 3.7 portfolio, 3.8 runtime, 3.8.1 baseline scope |

Running-example facts that captions may reuse verbatim:

- Entry state is only `z = {issue_number: 4420}`; the record is held out in the **expanded
  30-record** study, whose 132 discovery executions all take `record -> labels ->
  comments`.
- The observed `comments` call uses `limit=100`; the value varies across otherwise similar
  entries and is recoverable neither from `z` nor from `record`/`labels`, so the **full
  three-read region** retires as `ungroundable_slot` and the two-read prefix is emitted.
- The two-read artifact admits 92/92 calibration groups at `alpha=.05`, `delta=.10`,
  `|Lambda|=11` (so `gamma = delta/|Lambda|`), with simultaneous upper bound **0.0498**.
- Sample-size arithmetic already in the paper: 92 groups are required at that
  configuration with zero violations; a single precommitted threshold would require 45;
  a Bonferroni repair over `m=2` candidates would require 106.
- The **earlier 18-record** cohort is a different study: its aggressive three-read artifact
  replayed all 45 tool calls but passed only 17/18 exact answer contracts, because issue
  6602 returned Markdown anchor text where the contract required the full URL; a
  provider-free `ContinuationGuard` detected it and checked-rendered 18/18.  That artifact
  was calibrated at `alpha=.10` with bound 0.0992.
- The GCS artifact was also calibrated at `alpha=.10`: it admits 88/92 (coverage 0.957)
  and its simultaneous bound is 0.0520, so every GCS result is a 10%-risk result.
- Ceiling illustration already in 3.1: `phi=1`, `k=3`, `n_B=4` gives `Delta_max = 0.750`
  against a measured 75.0% reduction.
- Runtime terminal edges (`fig:pipeline`, `alg:dispatch`): exactly one compacts, five
  return the unmodified baseline, one raises an incident.

## The reader's mental model to establish first

Ask the reader to imagine a careful operations assistant handling an issue.  Before each
read it normally asks a model what to do next.  GAC is allowed to replace only a short,
repeated stretch of those questions with a pre-checked checklist.  The checklist is usable
only when all of the following remain true:

- every value it needs can be traced to the starting form or to an earlier receipt;
- every action is a declared safe-to-stage read in the same security compartment;
- the checklist starts at the one point where the runtime can safely substitute it;
- the present case matches the pinned workflow and passes its guard and risk gate; and
- the staged result passes its verifier before release.

If any condition fails, the ordinary assistant—not a guessed shortcut—continues, and that
is a designed outcome rather than a failure.  This should precede Section 2.1 as a short
*Reading guide* paragraph or a margin callout.  It gives a nontechnical invariant that
every later equation refines.

## Priority order: concepts that need intuition most

| Priority | Formal concept | Why it is mathematically clear but intuitively hard | Revision response |
| --- | --- | --- | --- |
| P0 | Groundability in Eq. (1), especially the difference between “no witness” and “many witnesses” | Readers can read the quantifier but may mistake repeated arguments for derivable arguments, or mistake ambiguity for a benign tie-break. | Add the data-lineage figure and the three-read/two-read running example before the full PATG algorithm. |
| P0 | Selective risk in Eqs. (3)--(5) | It is easy to read the objective as ordinary accuracy, rather than risk *conditional on dispatch*, with abstention/fallback carrying much of the safety design. | Add a dispatch population strip and a small numeric admission example next to the objective. |
| P0 | The cascade and `Retire` | “More evidence cannot rescue a hard barrier” is central but spread across qualification, synthesis, calibration, and runtime prose. | Turn the existing architecture into a reader-oriented stoplight/cascade annotation; preserve `fig:pipeline` as the formal architecture. |
| P1 | Position invariant `a=0` | A prefix-only compiler can sound like an arbitrary implementation limitation until the duplication/reordering failure is pictured. | Add a two-lane timeline comparing entry-prefix substitution with unsafe suffix dispatch, and hand the numbers to `fig:pilot-ablation`. |
| P1 | The separation of provenance, contracts/verifiers, and risk calibration | Each is precise on its own, but readers may conflate “can construct,” “looks conformant,” and “is statistically admitted.” | Add a three-lock visual and reuse its terms in subsection lead-ins. |
| P1 | Fixed-grid Clopper--Pearson admission and its per-candidate scope | The proof is soundly scoped, but readers may not see why freezing the grid matters, what `delta` buys, or why zero observed violations does not mean zero future risk. | Add a coverage-versus-bound plot and a candidate-search warning callout. |
| P1 | `q` is *trained* on unproductive outcomes but *calibrated* on violations | The score learns from wrong-or-abstained development outcomes and is then frozen; only wrong-after-dispatch events feed the safety bound.  Readers naturally assume one signal does both jobs. | Say it in one sentence at the start of 3.6 and label the two inputs distinctly in the calibration figure. |
| P2 | Canonical family, support, entropy, and ranking | Hashing away literals while preserving shape is abstract, and the score's heuristic role can be confused with admission. | Add a trace “same stencil, different ink” figure and visually separate sorting from certification. |
| P2 | Staging/fallback versus dirty incident; outer runner versus model-boundary adapter | “Baseline” has deliberately different meanings at different commit boundaries.  This is precise in Section 3.8.1 but easy to overgeneralize. | Add an explicit commit-line diagram with exact and weaker fallback paths. |
| P3 | Guarded composite synthesis (GCS) | A composite observation can be mistaken for API fusion or for a claim that the source reads disappeared, and its 10%-risk provenance is easy to lose. | Add a nested-envelope diagram that retains the internal source calls and provenance, captioned at `alpha=.10`. |

## Concept-to-example map

Use a consistent notation key in the left margin or in a compact box the first time it is
needed: `z` = issue form at entry; `o_j` = receipt from read `j`; `P` = deterministic
checklist; `H` = hard eligibility checklist; `V` = staged-output inspection; `q` =
nonconformity ("unfamiliarity") score; `eta` = the admission threshold **chosen from the
frozen grid `Lambda`** using calibration outcomes; `alpha` = the selective-risk budget;
`delta` = the calibration confidence budget spread across `Lambda`; `M` = versioned
workflow identity.  Do not describe `eta` as preselected: the grid, the score, and the
candidate are frozen in advance, and that is precisely what licenses picking `eta` after
looking at the calibration counts.

| Formal object or rule | Direct intuitive example | What must remain explicit |
| --- | --- | --- |
| Episode `E=(z,M,e_{1:T},y)` | A case file: the issue form (`z`), the exact operating manual/version badge (`M`), the timestamped conversation and tool receipts (`e_{1:T}`), and the observed answer (`y`). | It is a recorded execution, not merely a prompt/answer pair; include model requests/responses, tool calls/results, guardrails, handoffs, approvals, errors, and commit boundaries among possible events. |
| Manifest and partition | Two cases with the same issue number but different tool catalog, prompt, model or SDK version, tenant/principal, or isolation key belong to different filing cabinets.  A checklist learned in one cabinet is not silently moved to the other. | `M` pins prompt, policy, guardrail, tools, model, SDK, tracer, entry contract, and effect-catalog identities; compatibility is a hard precondition, not a similarity score. |
| Candidate region `R=[a,b]` | Highlight the stretch from a model request through the result of a proposed group of reads.  Do not highlight the final answer; GAC removes intermediate control decisions, not the task outcome. | Start/end boundaries and the fact that the window ends after a tool result. |
| Groundability | For issue 4420, `record(issue_number=4420)` obtains `4420` from `z.issue_number`; `labels(issue_number=4420)` obtains it from `record.issue_number`.  Both are a followable wire plus an allowed transformation. | Every argument slot needs an expression in the closed bounded library `L`; matching literal values alone is insufficient. |
| Ungrounded and ambiguous slots | The `limit` slot of `comments(..., limit=100)` has no wire: the changing value is neither on the entry form nor on a prior receipt.  One unwitnessed slot retires the *whole region that contains it*.  In a second tiny inset, show an e-mail value that could come from two equally plausible fields; too many witnesses is also a refusal, not a heuristic choice. | No witness means a remaining model decision; more than the ambiguity cap means the provenance is uncertain.  Either one blocks the region, and neither resolves to the cheapest available explanation. |
| Effect admissibility and barriers | A green read card says “declared read-only, speculatable, replayable, same principal/isolation.”  A red approval signature, write button, handoff arrow, error symbol, or unknown-effect card stops the highlighter. | Unknown is not treated as a read; hard effect barriers cannot be overcome with calibration data. |
| Position invariant `a=0` | A receptionist can replace the opening checklist before a case begins.  Replacing only a later stretch when entering at the front either repeats prior steps or does them in the wrong order. | The current runtime resolves artifacts at the initial model boundary; this is an explicit safety/runtime constraint, not a general claim that suffixes are impossible in every system. |
| Artifact `A=(P,H,V,q,eta,M)` | A sealed field kit: `P` is the checklist, `H` is the fit-to-use checklist, `V` is the inspection sheet, `q`/`eta` is the unfamiliarity meter and its cutoff, and `M` is the compatibility seal. | Keep all six components visible; no single component is “the guard.” |
| Selective dispatch | From 100 future case folders, hard/match checks divert some directly to the ordinary agent; the gate admits only low-`q` cases.  Only admitted folders can count as compacted attempts. | Eq. (3) is conjunctive.  A miss means baseline, while a dirty post-commit failure is an incident. |
| Objective and conditional loss | A saving is earned only on an admitted case: one avoided provider turn times the case being dispatched.  The risk denominator is only the cases where the shortcut ran, not all incoming cases. | Preserve the expectation and the conditional probability in Eqs. (4)--(5); do not relabel this as overall accuracy.  Note in the text that Eq. (4) is a design target the implementation does not solve: it ships the *first* family that survives. |
| Canonical family and support | Three different issue IDs create three trace cards with the same tool/dependency stencil.  Literal ink is blurred, but tool signatures, topology, run shape, and live-in/out shape stay visible. | Support is counted across independent scenario groups (with an optional minimum-distinct-days requirement the live study does not exercise), not by event count; canonicalization is not semantic equivalence. |
| Ranking score versus admission | Put candidate folders on a *sorting table* using expected savings minus heterogeneity/effect/size penalties.  Then route the top folder through a separate *certification gate*. | Eq. (6) ranks; it does not admit.  Flag the two coarse implemented terms exactly as the paper does: `rho_eff` is approximated by a tool-name namespace convention, and `\|F\|` by the argument-slot count of the first observed window. |
| Feasibility ceiling | A ceiling gauge: even a perfect gate/verifier cannot save more than the fraction of cases with an eligible region times removable requests, divided by baseline requests. | It is a necessary upper limit under `rho=1`, not a performance guarantee or evidence that the compiler succeeded; a saturated ceiling says the task determined the region. |
| Bounded synthesis, hard guard, and verifier | A small approved toolkit — 23 operators, depth at most two — can build only short, inspectable bindings.  Before release, a hard guard checks entry eligibility; after staged execution, a verifier checks the produced receipts. | The DSL is closed and depth-bounded; learned invariants and perturbation/replay are not proofs for all future inputs, and a missing sandbox is recorded as `perturbations_claimed: false`. |
| Nonconformity score `q` | Two different ledgers: the meter is *built* from development cases that went badly in any way (wrong or abstained), then sealed; the safety bound is *counted* only from cases that were dispatched and turned out wrong. | Training signal and calibration signal are deliberately different; the guarantee is about violations after dispatch, not about abstentions. |
| GCS | Place verified source receipts inside a transparent envelope, expose only the declared projection to the continuation, and seal it to that continuation's manifest. | Internal source calls remain serial and retained with provenance; GCS is not parallelization, fewer source reads, a remote service, or a proof of the application-supplied task-semantic contract.  Every GCS result is licensed at `alpha=.10`. |
| Task-semantic canonicalization (inside GCS) | The consumer uses at most three comments and the snapshot tool caps at three, so any observed limit of at least three is filed under the representative `limit=3`; `limit=1` is deliberately outside the declared domain. | Five closed operations only, supplied and signed by the application, with a declared admissible domain; values outside it raise and deoptimize.  This is a declaration the compiler enforces, not equivalence it learned. |
| Exact calibration | Test a frozen set of gates on a held-out inspection lot.  For each gate, count admitted groups and groups with a violation; accept the highest-coverage gate whose one-sided upper bound fits the stated budget, and retire the family if none does. | Candidate, score, and grid are frozen before calibration; `gamma = delta/\|Lambda\|` pays for the union bound; the guarantee is simultaneous over the finite grid for one fixed candidate, and it concerns disagreement with `V`, not semantic task error. |
| Runtime staging and fallback | Run the checklist in a sealed tray.  A clean failure before the commit line discards the tray and gives the original case to the ordinary agent.  A post-commit dirty failure cannot honestly be called fallback. | Distinguish the outer runner's byte-identical restoration from the model-boundary adapter's weaker post-emission behavior. |

## Proposed figures and insertion points

Do not overload any one graphic with all terminology.  Each figure should repeat the
formal symbols it explains and use the same visual vocabulary throughout: blue = observed
trace/data, green = admissible deterministic path, amber = test/gate, red = barrier or
refusal, gray = unchanged baseline.  `fig:pipeline` stays the system overview and
`fig:aha-example` stays the motivating two-cohort figure; the additions below are reader
aids at the local decision points.

**Figure budget.**  Twelve additions on top of ten existing figures is not shippable in
either build.  Treat the list as tiers: **must-have** F2, F4, F7, F12; **strong** F1, F3,
F5, F9; **optional** F6, F10, F11; and **F8 is not a new figure** — it is an expansion of
`fig:aha-example` or a two-column annotated table in 3.3.  Anything wider than the
single-column measure must be a `figure*` so the two-column `main.tex` build does not
overflow.

| ID and placement | Proposed graphic | Reader should visually understand | Rigor guardrail |
| --- | --- | --- | --- |
| F1 — immediately after the first paragraph of Section 2.1 | **Episode anatomy.** A horizontal case-file timeline: entry state `z`, manifest `M`, alternating model/tool events, outcome `y`.  Include small barrier icons for approval, handoff, error, and commit. | An episode is a typed, version-pinned execution record; a candidate is a bounded highlighted segment inside it. | Caption points back to the exact tuple and says the icons are examples of event kinds, not an exhaustive state machine. |
| F2 — directly after Eq. (1), before effect admissibility prose | **Provenance wiring for issue 4420.** Show `z.issue_number -> record.issue_number -> labels.issue_number` in green.  Draw the `comments.limit=100` socket with no incoming permissible wire in red.  Add a small “two valid sources” amber inset for ambiguity. | GAC compiles dataflow it can witness, not recurring text.  The maximal safe region is two reads, not the visually tempting three. | Label each edge with an expression from `L`; label the red socket “no witness,” not “wrong value.”  Cite `ungroundable_slot` and the ambiguity cap.  Make the red marker enclose the whole three-read region, not just the socket. |
| F3 — immediately after Eq. (2) | **Prefix versus suffix dispatch.** Top lane: entry boundary -> compiled two-read prefix -> ordinary agent. Bottom lane: ordinary first read -> attempted suffix injected at entry -> duplicated/reordered read warning. | Why `a=0` is a deployment invariant: the dispatcher has one safe substitution point. | State that this depicts the current runtime placement.  Print no measurements here: `fig:pilot-ablation` already carries the archived pilot's 16.7% / 100.0% / 36.7% numbers, and F3 should cite `sec:pilot` rather than restate them. |
| F4 — immediately after Eqs. (3)--(5) | **Selective-dispatch population strip.** Start with a row of future cases; show manifest/guard mismatches going gray to baseline, low-`q` matches going green to staging, and a staged clean failure returning gray.  A bracket under only green cases labels the conditional-risk denominator. | Coverage/savings and selective risk are different quantities; a rejected case is not a compacted failure. | Print `d_A(z)=1` above green cases and `Pr[L=1 \| d_A=1]` under their bracket.  Use symbolic counts only.  Do not imply a calibrated probability for a particular individual case.  This is the population view; the edge-level view stays in `fig:pipeline`. |
| F5 — in Section 3.1, alongside the miner paragraph that follows Algorithm 2 | **Same stencil, different literals.** Three trace cards with distinct IDs and values collapse to a canonical topology card; a side bar shows group support, optional day support, and within-family variants/entropy. | A family represents repeatable execution shape, not equality of whole transcripts or a claim of semantic sameness. | Preserve signatures, dependencies, live-ins/outs, and effect qualification in the card; explicitly note literals are abstracted only for family mining.  Placement is *after* `alg:patg`, because the canonical-family text follows it. |
| F6 — adjacent to Eq. (6) and Eq. (7), possibly a paired two-panel figure | **Sorting table and ceiling gauge.** Left: candidate folders sorted by the stated score, with a dashed divider “ranking only.” Right: a maximum possible savings gauge with `phi`, `k`, and `n_B`; actual results can be below it because of abstention/failure. | Ranking decides where synthesis effort goes; feasibility answers whether the target can possibly be met; neither one is admission. | Mark `rho=1` on the ceiling and, if a worked value is shown, use the paper's own `phi=1, k=3, n_B=4 -> 0.750`.  Footnote that the two implementation approximations in the score remain heuristics and, because the first surviving family ships, can change which artifact is registered. |
| F7 — after “Bounded synthesis and contracts” | **Three locks, two times.** A provenance lock opens before `P` exists; an entry hard-guard lock opens before staged execution; an output verifier lock opens after it.  The risk gate is a fourth, evidence lock before execution. | “Constructible,” “entry eligible,” “conformant after execution,” and “risk-admitted” are independent claims tested at different times. | Name the locks `L`, `H`, `V`, and `q<=eta`; annotate that no later lock rescues an earlier refusal. |
| F8 — **not a new figure**: extend `fig:aha-example`, or render Section 3.3's enumerated steps as a two-column “observed trace / compiler decision” table | **End-to-end issue 4420 decision trace.** Detailed storyboard specified below. | The complete lifecycle from recurrence to partial compilation, calibration, staged dispatch, and baseline preservation. | `fig:aha-example` already shows both cohorts, including the 4420 rejection and the 6602 continuation miss; any expansion must be regenerated by `aha_example_figure` in `build_artifacts.py`, which binds itself to the retained rows, rather than hand-drawn.  Keep the executed two-read artifact and the rejected full candidate visually distinct. |
| F9 — immediately before Algorithm 3 | **Frozen-grid admission frontier.** Plot the 11 fixed thresholds on x-axis, coverage on one y-axis/strip, and `U_eta` against `alpha` on another.  Highlight “largest coverage among thresholds with `U_eta <= alpha`,” and show the retire outcome when no threshold qualifies. | The threshold is selected after inspecting calibration outcomes only because the candidate, score, and grid were frozen first; zero observed violations still produces a nonzero upper bound. | Print `delta=.10` and `gamma=delta/\|Lambda\|` on the panel — the union bound is invisible otherwise.  Do not restate `fig:gate-support`, which already plots the 92-group requirement against NESTFUL family supports; F9 is about threshold choice *within one* candidate.  Either render a schematic explicitly labeled “illustrative fixed-grid selection” or source exact points from a sealed gate. |
| F10 — after the per-candidate limitation paragraph | **Scope fence.** One panel shows one fixed candidate tested across 11 predeclared thresholds (covered by the stated proposition).  Another shows multiple candidate families sharing calibration data, with a red “not compiler-wide without additional allocation” fence. | The proof licenses a per-candidate certificate, not an adaptive candidate search. | Quote the paper's own repair example (`m=2` raises the requirement from 92 to 106 admitted groups) and retain the stated i.i.d./no-shift assumptions.  Add the paper's own caveat that the live configuration sets `min_days=1` and `min_principals=1` over a single repository snapshot, so group independence is assumed, not established. |
| F11 — in Section 3.4 after the first GCS paragraph | **Verified bundle, not fused API.** Three sequential internal reads remain visible inside a staging box; `Pi` selects verified live-outs; a continuation-manifest seal permits one composite observation outward. | GCS changes the interface exposed to the provider but does not erase physical reads, generate a remote service, or learn arbitrary equivalence. | Draw the `batchable` capability and exact continuation-key check as required gates, show baseline on projection/manifest miss, and mark the canonicalized `limit` argument as an application-declared rule with a domain.  Caption must carry `alpha=.10`, bound 0.0520, coverage 88/92. |
| F12 — adjacent to Algorithm 4 and echoed in Section 3.8.1 | **Commit boundary truth table.** Two aligned lanes (outer runner and model-boundary adapter) share pre-emission checks.  A vertical commit line separates clean gray fallback from red incident/weaker post-emission behavior. | “Unmodified baseline” is exact only where the runner owns the relevant commit boundary. | Name the shared pre-emission checks the paper lists — lifecycle, signature, manifest pins, hard guard, already-observed tools, quota attestation, calibrated gate — and label the terminal edges 1 compacted / 5 baseline / 1 incident to match `fig:pipeline`.  Use the paper's precise wording: byte-identical for the outer runner, weaker post-emission semantics for the adapter. |

## End-to-end storyboard for the running example (F8)

Use this as the expansion of `fig:aha-example` or as a vertical, numbered two-column
“observed trace / compiler decision” table in Section 3.3.  Each step should carry the
relevant formal label in parentheses, so it teaches the formalism rather than becoming an
anecdote.

1. **Observe the recurrent trace (`E`, `M`, `z`).**  The entry form contains only
   `issue_number=4420`; the pinned manifest defines the compatible workflow.  All 132
   discovery executions take the route `record(4420) -> labels(record.issue_number) ->
   comments(record.issue_number, limit=100)`, with model turns between reads.
2. **Propose, but do not approve (`R`).**  Repetition puts the three reads in a candidate
   family.  The panel should stamp this “candidate, not permission.”
3. **Trace every argument backward (Eq. (1), `alg:patg`).**  Green arrows witness the entry
   issue number and the result-field issue number.  The `limit` socket gets a red
   no-witness marker because its value varies and neither `z` nor prior results produces
   it through `L`.
4. **Refuse the unjustified region.**  Cross out the full three-read candidate with
   `Retire: ungroundable_slot`; do not cross out the entire episode.  This makes visible
   that GAC is allowed to retain a maximal justified prefix and does not guess a modal
   value.
5. **Synthesize the two-read program (`P`) and protect it (`H`, `V`, `M`).**  Show
   `record(z.issue_number) -> labels(record.issue_number)`, then the closed DSL, hard
   guard, manifest match, and staged verifier as separate checks.
6. **Calibrate before live use (`q`, `eta`, `U_eta`).**  Put 92/92 admitted groups,
   `alpha=.05`, `delta=.10`, `|Lambda|=11`, and upper bound `0.0498` in an evidence card.
   The label must say “per-candidate threshold-grid certificate,” not “proof of semantic
   correctness.”
7. **Dispatch a future compatible case (`d_A`).**  A matching, low-score entry follows
   the two-read green path in staging; the ordinary agent still decides the comments
   limit and renders the answer.  This explicitly shows which model decisions remain.
8. **Show the counterfactual exits.**  A manifest/guard/gate/verifier miss follows the
   gray baseline arrow.  Separately, label the earlier 18-record cohort — 45/45 tool calls
   replayed but 17/18 answer contracts, with issue 6602 losing the required URL — as
   evidence that replay alone is not a downstream-answer guarantee.  Keep it visibly
   marked as a different study with a different artifact (calibrated at `alpha=.10`).

The visual takeaway is deliberately modest: GAC removes only the model turns whose inputs
are reproducibly evidenced, and it makes declining the attractive third read a successful
outcome.  This is the end-to-end narrative that should recur in the first sentence of
Sections 3.2, 3.3, and 3.6 without restating the full story.

## Concrete insertion plan by subsection

### Section 2.1 — Executions and candidate regions

- Add the one-paragraph *Reading guide* before the subsection or immediately after its
  first sentence.  It should introduce “pre-checked checklist” and “ordinary agent on a
  miss,” then defer all authority to the definitions that follow.
- Insert F1 after the episode definition and F2 after Eq. (1).  Keep the existing prose
  about effect declarations, but add a one-sentence bridge: “The diagram asks a stricter
  question than recurrence: can every socket be wired from an allowed prior value?”
- Place F3 after Eq. (2), followed by a concise “Why prefix-only?” paragraph that names
  reordering/duplication before sending the reader to `sec:pilot`.
- Add a boxed **Do not infer** line: “A repeated tool name, a matching literal, and a
  successful replay are not a provenance witness.”  This precisely anticipates the
  worked-example result.

### Section 2.2 — Selective optimization objective

- Before Eq. (3), introduce the artifact as a sealed kit and define each component in a
  six-item inline key.  This prevents `H`, `V`, and `q` from becoming interchangeable
  “safety checks” in the reader's mental model.
- Put F4 immediately after Eqs. (3)--(5).  Add a three-sentence numeric micro-example
  using symbolic counts (for example, “of 100 cases, 30 dispatch”) rather than claiming a
  new observed rate.  It should explain that the loss denominator is the 30 dispatches.
- End the subsection with a shaded **Optimization is not certification** note: the score
  ranks families; `Retire` is a valid optimizer output; the implementation returns the
  first surviving candidate rather than solving Eq. (4).  Keep the current candid
  discussion of the coarse ranking terms unchanged — including the paper's own point that
  first-survivor selection makes those coarse terms load-bearing for *which* artifact
  ships.

### Section 3 opening and 3.1 — provenance and canonical families

- Keep `fig:pipeline` as the high-level architecture.  Add one sentence in its lead-in that
  calls it a “map of refusal boundaries,” then use F5 as the close-up map of how a
  recurrent family is discovered.
- Algorithm 1 sits in the Section 3 opening, before 3.1.  Give it a one-line reader's cue
  before the pseudocode: “Read it as a one-way security checkpoint: a later stage may
  reject a candidate, but cannot authorize one a prior stage blocked.”
- Reuse F2's green/amber/red wiring vocabulary in the PATG explanation, then insert F5
  beside the miner paragraph that follows Algorithm 2.  The prose should state that
  canonicalization groups *structural proposals*; it does not demonstrate that different
  literal instances mean the same thing.
- Insert F6 beside the score and feasibility discussion.  Visually label the two score
  approximations as “ranking-only implementation approximations,” preserving the present
  transparency instead of hiding it in a figure caption.

### Section 3.2 — Bounded synthesis and contracts

- Insert F7 after the first paragraph.  Add short transition sentences that distinguish
  the time and role of each lock: provenance licenses construction, the hard guard
  licenses an attempted execution, the verifier checks the staged result, and calibration
  licenses dispatch frequency under its assumptions.
- Add a caption-style sentence next to the perturbation discussion: “A missing sandbox is a
  recorded absence of challenge, not a silent pass,” and keep the pointer to the headline
  live artifact recording `perturbations_claimed: false`.

### Section 3.3 — Worked example

- Retain the current five enumerated steps as the compact formal walk-through.  Turn them
  into the right-hand annotations of the F8 layout, or expand `fig:aha-example`; do not
  duplicate the prose and figure verbatim.
- Add a small final comparison strip: “tool replay passed” versus “continuation answer
  preserved,” with the 18-record cohort and issue 6602 appearing only as the paper's
  separate earlier study and clearly labeled as such.  This reinforces the scope of `V`
  and avoids presenting a replay check as end-to-end semantic validation.

### Sections 3.4--3.5 — GCS and comparator interfaces

- Insert F11 after GCS defines the packaged program `\tilde P = (P, Pi, tau_c)`.  Follow
  it with a one-sentence legend: “The outer composite is a declared view of verified
  internal receipts, not a new source operation.”
- Give the task-semantic canonicalization one sentence of intuition next to the figure —
  five closed operations, supplied and signed by the application, with a declared domain,
  and `limit=1` deliberately outside it — so readers do not read it as learned equivalence.
- In the GCS limitations paragraph, point directly to the three internal sequential
  reads in F11.  This turns the non-claims (no parallelism, no reduction in source reads,
  no remote service, no proof of the supplied contract) into inspectable features of the
  drawing.
- Repeat the `alpha=.10` marking at this point of use, as the paper does elsewhere; the
  GCS gate is the one gate in the paper with real selectivity (88/92, coverage 0.957), and
  the figure should not let a reader carry the 5% number over from Section 3.3.
- No additional visual is needed for fair manual and learned-optimizer interfaces unless
  the revision expands those sections; keep their separation from automatic discovery
  textual so Section 3 does not become visually overfull.

### Section 3.6 — exact risk-gated admission

- Begin with a plain-language sentence: “The gate is a conservative admission test over
  a fixed menu of thresholds, not a confidence score that proves an individual output
  correct.”  Add a second sentence separating the two data signals: `q` is fitted on
  development-group unproductive outcomes and then frozen, while the bound counts only
  violations after dispatch.
- Insert F9 immediately before Algorithm 3.  It should walk the reader from frozen
  score/grid to counts `(n_eta, k_eta)` to upper bound `U_eta` to the maximum-coverage
  qualifying threshold, and to `Retire` when none qualifies.  Keep Eq. (8) and the
  proposition as the source of truth.
- Insert F10 after the per-fixed-candidate limitation paragraph, not beside the
  proposition.  This placement makes the scope fence feel like a boundary of the theorem,
  not an optional caveat.
- In Section 3.6.1, add a brief visual key to Table 1 (or a callout that reuses F9's
  coverage/bound symbols) so readers can see why 88/92 at zero violations yields 0.0520
  and therefore fails the 5% target while 92/92 yields 0.0498 and meets it.  Do not alter
  the reported risk tiers.

### Sections 3.7--3.8 — portfolio and runtime

- Keep the portfolio layer visually separate from compilation.  A small “measured action
  selector” icon in `fig:pipeline` or F6 is enough; it must not imply the portfolio
  synthesizes or certifies an artifact.
- Insert F12 after Algorithm 4, then cite it again at the start of Section 3.8.1.  Put
  the commit line at the center of both lanes so the difference in fallback guarantees is
  impossible to miss.
- Add a final subsection-end sentence that gives readers the method's operational
  invariant: “One path compacts; clean misses preserve the baseline at the stated
  boundary; post-commit contamination is reported as an incident rather than relabeled
  fallback.”

## Implementation sequence and acceptance criteria

1. **Lock the running example.**  Reuse issue 4420, the two-read prefix, the rejected
   `comments.limit`, and the calibration values exactly as listed in *Verified anchors*.
   Confirm all captions distinguish the expanded 30-record study from the earlier
   18-record issue-6602 cohort, and that no caption reuses the 5% bound for a 10%-risk
   artifact.
2. **Choose the right medium per figure.**  Authored diagrams (F1, F3, F4, F7, F11, F12)
   belong in `paper/figures/*.tex` as TikZ, `\input` from `body.tex`, like
   `architecture.tex`.  Anything printing measured values (an F8 expansion, an F9 sourced
   from a sealed gate) must be generated by `paper/scripts/build_artifacts.py` into
   `paper/generated_figures/` and bound to the sealed results, as `aha_example_figure`
   already is — never hand-drawn.
3. **Create the visual vocabulary first.**  Build F2 and F4 before anything else; they
   establish the wire, barrier, baseline, and admitted-path colors reused by all later
   graphics.  Ensure every color also has a textual label or pattern, for grayscale and
   for color-vision accessibility.
4. **Respect the figure budget and both builds.**  Ship the must-have tier first (F2, F4,
   F7, F12), then the strong tier, and only add optional figures if the page budget
   allows.  Anything wider than the single-column measure must be a `figure*` so the
   two-column `main.tex` build does not overflow, and the shared body must compile in both
   wrappers.
5. **Make scope explicit in every caption.**  Captions must say whether a panel is an
   illustrative schematic, an executed case, or a reported study value.  A schematic may
   explain a rule but must not acquire an empirical caption.
6. **Preserve reproducibility and accessibility.**  Add `\Description{...}` for every new
   figure.  For generated figures, refresh the checksums in
   `paper/results/publication_manifest.json` and re-run
   `paper/scripts/validate_artifacts.py`; keep the deterministic-rendering settings so
   unchanged figures do not re-hash.  Rely on the existing text-bounds assertion in
   `build_artifacts.py` (which fails on text escaping the canvas) rather than eyeballing
   overflow, and still inspect the final PDFs for label sizes at the paper's column width.

The revision is ready when both builds compile, the artifact validator passes, and a
technically literate reader can answer these questions from the text plus figures without
any formal claim having changed:

- Why does repeated behavior propose a candidate but not authorize it?
- Why does the missing `limit` witness preserve the two-read prefix instead of rejecting
  the entire workflow or guessing a value?
- Which of provenance, guard, verifier, and calibration is responsible for a given
  refusal, and when does it run?
- Why is risk measured only after dispatch, what do `alpha` and `delta` each buy, and what
  does the stated certificate not establish?
- Why is a clean fallback different from a post-commit incident, and when is
  byte-identical baseline restoration actually available?

---

## What shipped

Executed against `paper/tex/body.tex`; both wrappers rebuilt; artifact validator green
(2617 checks, 0 failures); `pytest` 363 passed; `scripts/verify_release.py` passed.
Article grew 48 → 54 pages, the two-column submission 28 → 33.

### Plan item to artifact

| Plan ID | Shipped as | Source | Placement |
| --- | --- | --- | --- |
| F1 | `fig:episode-anatomy` | `paper/figures/fig-episode-anatomy.tex` | §2.1, after the episode definition |
| F2 | `fig:provenance-wiring` | `paper/figures/fig-provenance-wiring.tex` | §2.1, directly after Eq. (1) |
| F3 | `fig:prefix-suffix` | `paper/figures/fig-prefix-suffix.tex` | §2.1, directly after Eq. (2) |
| F4 | `fig:dispatch-population` | `paper/figures/fig-dispatch-population.tex` | §2.2, after Eqs. (3)--(5) |
| F5 | `fig:canonical-family` | `paper/figures/fig-canonical-family.tex` | §3.1, beside the miner paragraph *after* `alg:patg` |
| F6 | `fig:rank-ceiling` | `paper/figures/fig-rank-ceiling.tex` | §3.1, after the feasibility paragraph |
| F7 | `fig:locks` | `paper/figures/fig-locks.tex` | §3.2, after the synthesis paragraph |
| F8 | `tab:worked-trace` | inline in `body.tex` | §3.3, replacing the enumerated walk-through |
| F9 | `fig:admission-frontier` | `admission_frontier_figure()` in `paper/scripts/build_artifacts.py` | §3.6, immediately before `alg:calibrate` |
| F10 | `fig:scope-fence` | `paper/figures/fig-scope-fence.tex` | §3.6, after the per-candidate limitation paragraph |
| F11 | `fig:gcs-envelope` | `paper/figures/fig-gcs-envelope.tex` | §3.4, after the `\tilde P` definition |
| F12 | `fig:commit-boundary` | `paper/figures/fig-commit-boundary.tex` | §3.8, after `alg:dispatch` |

Prose additions: the *Reading guide* paragraph (§2.1), the **Do not infer** callout
(§2.1), the six-component artifact key and the 100/40/30/30 denominator example (§2.2),
the **Optimization is not certification** callout (§2.2), the ``map of refusal
boundaries'' lead-in and the one-way-checkpoint cue for `alg:compile` (§3), the
lock-timing transitions (§3.2), the *tool replay passed* versus *continuation answer
preserved* strip (§3.3), the task-semantic-canonicalization sentence and the `alpha=.10`
marking (§3.4), the two-signal sentence separating how `q` is fitted from what the bound
counts (§3.6), the `fig:admission-frontier` pointer in §3.6.1, and the operational
invariant closing §3.8.1.  The `\gaccallout` macro is defined at the top of `body.tex`
from primitives, because neither wrapper loads `tcolorbox`.

### Post-execution numbering

`eq:grounding` 1, `eq:prefix` 2, dispatch indicator 3, objective 4, risk constraint 5,
`eq:score` 6, `eq:ceiling` 7, `eq:cp` 8 --- all unchanged.  Algorithms 1--4 unchanged.
Figures: `fig:aha-example` 1, `fig:episode-anatomy` 2, `fig:provenance-wiring` 3,
`fig:prefix-suffix` 4, `fig:dispatch-population` 5, `fig:pipeline` 6,
`fig:canonical-family` 7, `fig:rank-ceiling` 8, `fig:locks` 9, `fig:gcs-envelope` 10,
`fig:admission-frontier` 11, `fig:scope-fence` 12, `fig:commit-boundary` 13, then the
pre-existing results figures 14--23.  Tables: `tab:worked-trace` is now Table 1 and
`tab:admission-register` Table 2, with the rest shifting by one.

### Where the implementation departs from the plan

- **F8 is a table, not an expanded `fig:aha-example`.**  The plan allowed either.  The
  figure is generated by `aha_example_figure()` and hash-bound to the sealed rows, so
  expanding it would have meant re-deriving a checksummed artifact to add narrative;
  the two-column table carries the same eight storyboard steps with no such coupling,
  and `fig:aha-example` keeps its introduction job untouched.
- **The portfolio note lives in `fig:rank-ceiling`, not in `fig:pipeline`.**  The plan
  offered either.  `fig:pipeline` is the formal architecture the plan elsewhere insists on
  preserving, and `fig:rank-ceiling` already carries the ``this is not admission'' theme,
  so the portfolio layer is named there as the third such quantity.

### Sizing and build constraints that the artwork now encodes

The binding measure is the single-column article at 469.75\,pt, not the two-column span:
spanning figures are authored at or below ~162\,mm and single-column ones below ~80\,mm so
they clear the ACM column at 241\,pt.  `shapes.geometric` is deliberately unused --- the
article wrapper loads it and `main.tex` does not, so any figure depending on it would build
in one wrapper only.  Style keys are prefixed (`gnote`, `ghd`, `gstep`, `gout`, `gev`,
`gside`, `gtick`, `gaxis`, `gseg`) because `cap`, `step`, and `out` are live TikZ keys.
`validate_artifacts.py` now gates all twelve reader aids by caption text in both builds,
for the same reason the README records for Algorithms 2--4: shared-body `\input` artwork can
otherwise be authored without ever reaching a page.
