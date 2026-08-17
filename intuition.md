# Intuition plan for Sections 2--3

## Purpose and editorial rule

This is a revision plan for `paper/open_research/article.pdf`, especially Section 2
(*Problem Formulation*) and Section 3 (*Guarded Agentic Compaction*, GAC).  It does
not propose weakening, moving, or replacing any definition, algorithm, qualification
condition, or stated limitation.  The preferred editorial pattern is:

1. state the formal definition or claim unchanged;
2. immediately show one concrete execution of that definition;
3. use a labeled figure to make the same constraint visible; and
4. point the reader back to the equation, algorithm, or boundary that remains
   authoritative.

The running example should be the already-reported expanded GitHub issue workflow, not a
new hypothetical result.  It has an unusually useful negative case: the compiler can
ground `record` and `labels`, but it must refuse the third `comments` read because the
model-selected `limit` is not reconstructible.  That lets the paper teach that GAC is a
*conservative partial substitution*, rather than an attractive macro extractor.

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

If any condition fails, the ordinary assistant—not a guessed shortcut—continues.  This
one sentence should precede Section 2.1 as a short *Reading guide* paragraph or a
margin callout.  It gives a nontechnical invariant that every later equation refines.

## Priority order: concepts that need intuition most

| Priority | Formal concept | Why it is mathematically clear but intuitively hard | Revision response |
| --- | --- | --- | --- |
| P0 | Groundability in Eq. (1), especially the difference between “no witness” and “many witnesses” | Readers can read the quantifier but may mistake repeated arguments for derivable arguments, or mistake ambiguity for a benign tie-break. | Add the data-lineage figure and the three-read/two-read running example before the full PATG algorithm. |
| P0 | Selective risk in Eqs. (3)--(5) | It is easy to read the objective as ordinary accuracy, rather than risk *conditional on dispatch*, with abstention/fallback carrying much of the safety design. | Add a dispatch population strip and a small numeric admission example next to the objective. |
| P0 | The cascade and `RETIRE` | “More evidence cannot rescue a hard barrier” is central but spread across qualification, synthesis, calibration, and runtime prose. | Turn the existing architecture into a reader-oriented stoplight/cascade annotation; preserve the present system diagram as the formal architecture. |
| P1 | Position invariant `a=0` | A prefix-only compiler can sound like an arbitrary implementation limitation until the duplication/reordering failure is pictured. | Add a two-lane timeline comparing entry-prefix substitution with unsafe suffix dispatch. |
| P1 | The separation of provenance, contracts/verifiers, and risk calibration | Each is precise on its own, but readers may conflate “can construct,” “looks conformant,” and “is statistically admitted.” | Add a three-lock visual and reuse its terms in subsection lead-ins. |
| P1 | Fixed-grid Clopper--Pearson admission and its per-candidate scope | The proof is soundly scoped, but readers may not see why freezing the grid matters or why zero observed violations does not mean zero future risk. | Add a coverage-versus-bound plot and a candidate-search warning callout. |
| P2 | Canonical family, support, entropy, and ranking | Hashing away literals while preserving shape is abstract, and the score's heuristic role can be confused with admission. | Add a trace “same stencil, different ink” figure and visually separate sorting from certification. |
| P2 | Staging/fallback versus dirty incident; outer runner versus model-boundary adapter | “Baseline” has deliberately different meanings at different commit boundaries.  This is precise in Section 3.8.1 but easy to overgeneralize. | Add an explicit commit-line diagram with exact and weaker fallback paths. |
| P3 | Guarded composite synthesis (GCS) | A composite observation can be mistaken for API fusion or for a claim that the source reads disappeared. | Add a nested-envelope diagram that retains the internal source calls and provenance. |

## Concept-to-example map

Use a consistent notation key in the left margin or in a compact box the first time it is
needed: `z` = issue form at entry; `o_j` = receipt from read `j`; `P` = deterministic
checklist; `H` = hard eligibility checklist; `V` = staged-output inspection; `q, eta` =
novelty score and its preselected admission cutoff; `M` = versioned workflow identity.
The examples below map directly to those objects.

| Formal object or rule | Direct intuitive example | What must remain explicit |
| --- | --- | --- |
| Episode `E=(z,M,e_{1:T},y)` | A case file: the issue form (`z`), the exact operating manual/version badge (`M`), the timestamped conversation and tool receipts (`e_{1:T}`), and the observed answer (`y`). | It is a recorded execution, not merely a prompt/answer pair; include guardrails, handoffs, approvals, errors, and commit boundaries among possible events. |
| Manifest and partition | Two cases with the same issue number but different tool catalog, prompt, tenant/principal, or isolation key belong to different filing cabinets.  A checklist learned in one cabinet is not silently moved to the other. | `M` pins the listed identities and compatibility is a hard precondition, not a similarity score. |
| Candidate region `R=[a,b]` | Highlight the stretch from a model request through the result of a proposed group of reads.  Do not highlight the final answer; GAC removes intermediate control decisions, not the task outcome. | Start/end boundaries and the fact that the window ends after a tool result. |
| Groundability | For issue 4420, `record(issue_number=4420)` obtains `4420` from `z.issue_number`; `labels(issue_number=4420)` obtains it from `record.issue_number`.  Both are a followable wire plus an allowed transformation. | Every argument slot needs an expression in the closed bounded library `L`; matching literal values alone is insufficient. |
| Ungrounded and ambiguous slots | `comments(..., limit=100)` is rejected because the changing limit is neither on the entry form nor on a prior receipt—there is no wire.  In a second tiny inset, show an e-mail value that could come from two equally plausible fields; too many witnesses is also a refusal, not a heuristic choice. | No witness means a remaining model decision; more than the ambiguity cap means the provenance is uncertain.  Both block the region. |
| Effect admissibility and barriers | A green read card says “declared read-only, speculatable, replayable, same principal/isolation.”  A red approval signature, write button, handoff arrow, error symbol, or unknown-effect card stops the highlighter. | Unknown is not treated as a read; hard effect barriers cannot be overcome with calibration data. |
| Position invariant `a=0` | A receptionist can replace the opening checklist before a case begins.  Replacing only a later stretch when entering at the front either repeats prior steps or does them in the wrong order. | The deployed runtime resolves at the initial model boundary; this is an explicit safety/runtime constraint, not a general claim that suffixes are impossible in every system. |
| Artifact `A=(P,H,V,q,eta,M)` | A sealed field kit: `P` is the checklist, `H` is the fit-to-use checklist, `V` is the inspection sheet, `q/eta` is the conservative “unfamiliarity” meter, and `M` is the compatibility seal. | Keep all six components visible; no single component is “the guard.” |
| Selective dispatch | From 100 future case folders, hard/match checks divert some directly to the ordinary agent; the gate admits only low-`q` cases.  Only admitted folders can count as compacted attempts. | Eq. (3) is conjunctive.  A miss means baseline, while a dirty post-commit failure is an incident. |
| Objective and conditional loss | A saving is earned only on an admitted case: one avoided provider turn times the case being dispatched.  The risk denominator is only the cases where the shortcut ran, not all incoming cases. | Preserve the expectation and the conditional probability in Eqs. (4)--(5); do not relabel this as overall accuracy. |
| Canonical family and support | Three different issue IDs create three trace cards with the same tool/dependency stencil.  Literal ink is blurred, but tool signatures, topology, run shape, and live-in/out shape stay visible. | Support is across independent scenario groups (and optional days), not event count; canonicalization is not semantic equivalence. |
| Ranking score versus admission | Put candidate folders on a *sorting table* using expected savings minus heterogeneity/effect/size penalties.  Then route the top folder through a separate *certification gate*. | Eq. (6) ranks; it does not admit.  Flag the two coarse implemented score terms exactly as the paper does. |
| Feasibility ceiling | A ceiling gauge: even a perfect gate/verifier cannot save more than the fraction of cases with an eligible region times removable requests, divided by baseline requests. | It is a necessary upper limit under `rho=1`, not a performance guarantee or evidence that the compiler succeeded. |
| Bounded synthesis, hard guard, and verifier | A small approved toolkit can build only short, inspectable bindings.  Before release, a hard guard checks entry eligibility; after staged execution, a verifier checks the produced receipts. | The DSL is closed and depth-bounded; learned invariants and perturbation/replay are not proofs for all future inputs. |
| GCS | Place verified source receipts inside a transparent envelope, expose only the declared projection to the continuation, and seal it to that continuation's manifest. | Internal source calls remain serial and retained with provenance; GCS is not parallelization, remote API creation, or learned semantic equivalence. |
| Exact calibration | Test a frozen set of gates on a held-out inspection lot.  For each gate, count admitted groups and groups with a violation; accept the highest-coverage gate whose one-sided upper bound fits the stated budget. | Grid and score are frozen before calibration; the guarantee is simultaneous over a finite grid for one fixed candidate. |
| Runtime staging and fallback | Run the checklist in a sealed tray.  A clean failure before the commit line discards the tray and gives the original case to the ordinary agent.  A post-commit dirty failure cannot honestly be called fallback. | Distinguish the outer runner's byte-identical restoration from the model-boundary adapter's weaker post-emission behavior. |

## Proposed figures and insertion points

Do not overload any one graphic with all terminology.  Each figure should repeat the
formal symbols it explains and use the same visual vocabulary throughout: blue = observed
trace/data, green = admissible deterministic path, amber = test/gate, red = barrier or
refusal, gray = unchanged baseline.  Existing Figure 2 should stay the system overview;
the additions below are reader aids at the local decision points.

| ID and placement | Proposed graphic | Reader should visually understand | Rigor guardrail |
| --- | --- | --- | --- |
| F1 — immediately after the first paragraph of Section 2.1 | **Episode anatomy.** A horizontal case-file timeline: entry state `z`, manifest `M`, alternating model/tool events, outcome `y`.  Include small barrier icons for approval, handoff, error, and commit. | An episode is a typed, version-pinned execution record; a candidate is a bounded highlighted segment inside it. | Caption points back to the exact tuple and says the icons are examples of event kinds, not an exhaustive state machine. |
| F2 — directly after Eq. (1), before effect admissibility prose | **Provenance wiring for issue 4420.** Show `z.issue_number -> record.issue_number -> labels.issue_number` in green.  Draw the `comments.limit=100` socket with no incoming permissible wire in red.  Add a small “two valid sources” amber inset for ambiguity. | GAC compiles dataflow it can witness, not recurring text.  The maximal safe region is two reads, not the visually tempting three. | Label each edge with an expression from `L`; label the red socket “no witness,” not “wrong value.”  Cite `ungroundable_slot` and the ambiguity cap. |
| F3 — immediately after Eq. (2) | **Prefix versus suffix dispatch.** Top lane: entry boundary -> compiled two-read prefix -> ordinary agent. Bottom lane: ordinary first read -> attempted suffix injected at entry -> duplicated/reordered read warning. | Why `a=0` is a deployment invariant: the dispatcher has one safe substitution point. | State that this depicts the current runtime placement, and retain the empirical cross-reference for the actual failure. |
| F4 — immediately after Eqs. (3)--(5) | **Selective-dispatch population strip.** Start with a row of future cases; show manifest/guard mismatches going gray to baseline, low-`q` matches going green to staging, and a staged clean failure returning gray.  A bracket under only green cases labels the conditional-risk denominator. | Coverage/savings and selective risk are different quantities; a rejected case is not a compacted failure. | Print `d_A(z)=1` above green cases and `Pr[L=1 | d_A=1]` under their bracket.  Do not imply a calibrated probability for a particular individual case. |
| F5 — as the first local figure in Section 3.1, before Algorithm 2 | **Same stencil, different literals.** Three trace cards with distinct IDs and values collapse to a canonical topology card; a side bar shows group support, optional day support, and within-family variants/entropy. | A family represents repeatable execution shape, not equality of whole transcripts or a claim of semantic sameness. | Preserve signatures, dependencies, live-ins/outs, and effect qualification in the card; explicitly note literals are abstracted only for family mining. |
| F6 — adjacent to Eq. (6) and Eq. (7), possibly a paired two-panel figure | **Sorting table and ceiling gauge.** Left: candidate folders sorted by the stated score, with a dashed divider “ranking only.” Right: a maximum possible savings gauge with `phi`, `k`, and `n_B`; actual results can be below it because of abstention/failure. | Ranking decides where synthesis effort goes; feasibility answers whether the target can possibly be met; neither one is admission. | Mark `rho=1` on the ceiling.  Footnote that the two implementation approximations in the score remain heuristics and can alter ordering. |
| F7 — after “Bounded synthesis and contracts” | **Three locks, two times.** A provenance lock opens before `P` exists; an entry hard-guard lock opens before staged execution; an output verifier lock opens after it.  The risk gate is a fourth, evidence lock before execution. | “Constructible,” “entry eligible,” “conformant after execution,” and “risk-admitted” are independent claims tested at different times. | Name the locks `L`, `H`, `V`, and `q<=eta`; annotate that no later lock rescues an earlier refusal. |
| F8 — replace the prose-only worked example with an expanded sidecar or add directly after its enumerated list | **End-to-end issue 4420 decision trace.** Detailed storyboard specified below. | The complete lifecycle from recurrence to partial compilation, calibration, staged dispatch, and baseline preservation. | All facts should be drawn from the already reported case and must distinguish the executed two-read artifact from the rejected full candidate. |
| F9 — immediately before or after Algorithm 3 | **Frozen-grid admission frontier.** Plot the 11 fixed thresholds on x-axis, coverage on one y-axis/strip, and `U_eta` against `alpha` on another.  Highlight “largest coverage among thresholds with `U_eta <= alpha`.” A small sample-size callout shows why 92 zero-violation admitted groups matter at the stated configuration. | The threshold is selected after inspecting calibration outcomes only because the candidate, score, and grid were frozen first; zero observed violations still produces a nonzero upper bound. | Do not fabricate a curve from a different study.  Either render a schematic explicitly labeled “illustrative fixed-grid selection” or source exact points from a sealed gate for the artifact being discussed. |
| F10 — after the per-candidate limitation paragraph | **Scope fence.** One panel shows one fixed candidate tested across 11 predeclared thresholds (covered by the stated proposition).  Another shows multiple candidate families sharing calibration data, with a red “not compiler-wide without additional allocation” fence. | The proof licenses a per-candidate certificate, not an adaptive candidate search. | Quote the Bonferroni repair example from the paper and retain all stated i.i.d./shift assumptions. |
| F11 — in Section 3.4 after the first GCS paragraph | **Verified bundle, not fused API.** Three sequential internal reads remain visible inside a staging box; `Pi` selects verified live-outs; a continuation-manifest seal permits one composite observation outward. | GCS changes the interface exposed to the provider but does not erase physical reads, generate a remote service, or learn arbitrary equivalence. | Draw the batchable capability and exact continuation-key check as required gates, and show baseline on projection/manifest miss. |
| F12 — adjacent to Algorithm 4 and echoed in Section 3.8.1 | **Commit boundary truth table.** Two aligned lanes (outer runner and model-boundary adapter) share pre-emission checks.  A vertical commit line separates clean gray fallback from red incident/weaker post-emission behavior. | “Unmodified baseline” is exact only where the runner owns the relevant commit boundary. | Use the paper's precise labels—byte-identical for outer runner, weaker post-emission semantics for adapter—and retain the exception rather than simplifying it away. |

## End-to-end storyboard for the running example (F8)

Use this as a vertical, numbered figure or a two-column “observed trace / compiler decision” table.  Each step should carry the relevant formal label in parentheses, so it teaches the formalism rather than becoming an anecdote.

1. **Observe the recurrent trace (`E`, `M`, `z`).**  The entry form contains only
   `issue_number=4420`; the pinned manifest defines the compatible workflow.  The
   observed route is `record(4420) -> labels(record.issue_number) ->
   comments(record.issue_number, limit=100)`, with model turns between reads.
2. **Propose, but do not approve (`R`).**  Repetition puts the three reads in a candidate
   family.  The panel should stamp this “candidate, not permission.”
3. **Trace every argument backward (Eq. (1), PATG).**  Green arrows witness the entry
   issue number and the result-field issue number.  The `limit` socket gets a red
   no-witness marker because its value varies and neither `z` nor prior results produces
   it through `L`.
4. **Refuse the unjustified suffix.**  Cross out only the full three-read candidate with
   `RETIRE: ungroundable_slot`; do not cross out the entire episode.  This makes visible
   that GAC is allowed to retain a maximal justified prefix.
5. **Synthesize the two-read program (`P`) and protect it (`H`, `V`, `M`).**  Show
   `record(z.issue_number) -> labels(record.issue_number)`, then the closed DSL, hard
   guard, manifest match, and staged verifier as separate checks.
6. **Calibrate before live use (`q`, `eta`, `U_eta`).**  Put the reported 92/92,
   `alpha=.05`, and upper bound `0.0498` in an evidence card.  The label must say
   “per-candidate threshold-grid certificate,” not “proof of semantic correctness.”
7. **Dispatch a future compatible case (`d_A`).**  A matching, low-score entry follows
   the two-read green path in staging; the ordinary agent still decides the comments
   limit and renders the answer.  This explicitly shows which model decisions remain.
8. **Show the counterfactual exits.**  A manifest/guard/gate/verifier miss follows the
   gray baseline arrow.  Separately, point readers to the prior three-read continuation
   miss (issue 6602) as evidence that replay alone is not a downstream-answer guarantee.

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
  reordering/duplication before sending the reader to the empirical demonstration.
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
  ranks families; `RETIRE` is valid; the implementation returns the first surviving
  candidate rather than solving the global objective.  Keep the current candid discussion
  of coarse ranking terms unchanged.

### Section 3 opening and 3.1 — provenance and canonical families

- Keep Figure 2 as the high-level architecture.  Add one sentence in its lead-in that
  calls it a “map of refusal boundaries,” then use F5 as the close-up map of how a
  recurrent family is discovered.
- Give Algorithm 1 a one-line reader's cue before the pseudocode: “Read it as a one-way
  security checkpoint: a later stage may reject a candidate, but cannot authorize one a
  prior stage blocked.”
- Insert F5 before Algorithm 2 and use F2's green/amber/red wiring vocabulary in the
  PATG explanation.  The prose should state that canonicalization groups *structural
  proposals*; it does not demonstrate that different literal instances mean the same
  thing.
- Insert F6 beside the score and feasibility discussion.  Visually label the two score
  approximations as “ranking-only implementation approximations,” preserving the present
  transparency instead of hiding it in a figure caption.

### Section 3.2 — Bounded synthesis and contracts

- Insert F7 after the first paragraph.  Add short transition sentences that distinguish
  the time and role of each lock: provenance licenses construction, the hard guard
  licenses an attempted execution, the verifier checks the staged result, and calibration
  licenses dispatch frequency under its assumptions.
- Add a caption-style sentence next to perturbation discussion: “A missing sandbox is a
  recorded absence of challenge, not a silent pass.”  This makes the existing limitation
  easier to retain without burying it in detail.

### Section 3.3 — Worked example

- Retain the current five enumerated steps as the compact formal walk-through.  Add F8
  directly after them or turn them into the right-hand annotations of F8; do not duplicate
  the prose and figure verbatim.
- Add a small final comparison strip: “tool replay passed” versus “continuation answer
  preserved,” with issue 6602 appearing only as the paper's separate earlier study and
  clearly labeled as such.  This reinforces the scope of `V` and avoids presenting a
  replay check as end-to-end semantic validation.

### Sections 3.4--3.5 — GCS and comparator interfaces

- Insert F11 after GCS defines `(P, Pi, tau_c)`.  Follow it with a one-sentence legend:
  “The outer composite is a declared view of verified internal receipts, not a new source
  operation.”
- In the GCS limitations paragraph, point directly to the three internal sequential
  reads in F11.  This turns the non-claims (no parallelism, fewer source reads, remote
  service, or inferred contract) into inspectable features of the drawing.
- No additional visual is needed for fair manual and learned-optimizer interfaces unless
  the revision expands those sections; keep their separation from automatic discovery
  textual so Section 3 does not become visually overfull.

### Section 3.6 — exact risk-gated admission

- Begin with a plain-language sentence: “The gate is a conservative admission test over
  a fixed menu of thresholds, not a confidence score that proves an individual output
  correct.”
- Insert F9 immediately before Algorithm 3.  It should walk the reader from frozen
  score/grid to counts `(n_eta, k_eta)` to upper bound `U_eta` to the maximum-coverage
  qualifying threshold.  Keep Eq. (8) and the proposition as the source of truth.
- Insert F10 after the per-fixed-candidate limitation paragraph, not beside the
  proposition.  This placement makes the scope fence feel like a boundary of the theorem,
  not an optional caveat.
- In Section 3.6.1, add a brief visual key to Table 1 (or a callout that reuses F9's
  coverage/bound symbols) so readers can see why 88/92 at zero violations can fail the
  5% target.  Do not alter the reported risk tiers.

### Sections 3.7--3.8 — portfolio and runtime

- Keep the portfolio layer visually separate from compilation.  A small “measured action
  selector” icon in Figure 2 or F6 is enough; it must not imply the portfolio synthesizes
  or certifies an artifact.
- Insert F12 after Algorithm 4, then cite it again at the start of Section 3.8.1.  Put
  the commit line at the center of both lanes so the difference in fallback guarantees is
  impossible to miss.
- Add a final subsection-end sentence that gives readers the method's operational
  invariant: “One path compacts; clean misses preserve the baseline at the stated
  boundary; post-commit contamination is reported as an incident rather than relabeled
  fallback.”

## Implementation sequence and acceptance criteria

1. **Lock the running example.**  Reuse issue 4420, the two-read prefix, the rejected
   `comments.limit`, and the reported calibration values exactly.  Confirm all captions
   distinguish the expanded study from the earlier issue-6602 continuation study.
2. **Create the visual vocabulary.**  Make F2 and F4 first; they establish the wire,
   barrier, baseline, and admitted-path colors reused by all later graphics.  Ensure every
   color has a textual label/pattern for grayscale and accessibility.
3. **Add local figures before global ornament.**  Add F1--F7 to clarify definitions and
   construction; add F9--F10 only after the equation/proposition text has been kept
   intact.  Avoid adding a figure merely to decorate a familiar term.
4. **Add the end-to-end figure.**  Build F8 from the same data/provenance as the text and
   have it cite Eq. (1), Eq. (3), Algorithm 1, and Algorithm 3 by label.
5. **Make scope explicit in every caption.**  Captions must say whether a panel is an
   illustrative schematic, an executed case, or a reported study value.  A schematic may
   explain a rule but must not acquire an empirical caption.
6. **Preserve layout and accessibility.**  Add `\Description{...}` text for every new
   figure; use legible labels at the paper's final column width; rebuild both article and
   submission variants; visually inspect for overflow and for any figure whose notation
   is too small to read.

The revision is ready when a technically literate reader can answer these questions from
the text plus figures without changing any formal claim:

- Why does repeated behavior propose a candidate but not authorize it?
- Why does the missing `limit` witness preserve the two-read prefix instead of rejecting
  the entire workflow or guessing a value?
- Which of provenance, guard, verifier, and calibration is responsible for a given
  refusal, and when does it run?
- Why is risk measured only after dispatch, and what does the stated certificate not
  establish?
- Why is a clean fallback different from a post-commit incident, and when is
  byte-identical baseline restoration actually available?
