#!/usr/bin/env python3
"""Bring the seminar deck (paper/slides/GAC-seminar.pptx) up to the current paper.

The seminar deck predates almost every result the paper now reports: its title, its
headline numbers, its research questions, and four of its results slides describe the
August 2026 manuscript. This script rewrites it in place, on its own frames, so the deck
keeps its design system while its content follows paper/iclr (through PR #73):

* title, scope, formulation, method, setup, limitations, claims-register, and conclusion
  slides are rewritten to the current paper; eyebrows carry current section, algorithm,
  equation, and table numbers;
* five display-equation images (grounding, dispatch, objective, ranking score, feasibility
  ceiling) are replaced with renders of the paper's current equations, kept under
  paper/slides/seminar-equations/ (``--render-equations`` regenerates them);
* slides on studies the paper no longer reports in its main claim are repurposed: the
  NESTFUL provenance slide becomes the no-benefit slide (NESTFUL and AppWorld), the
  demonstration-suite slide becomes the newer-records and post-cutoff slide, and the
  offline-stress slide becomes the primary-results slide with the hand-written comparator;
  the portfolio-pilot slide is removed;
* two slides are added on the two-card frame of slide 19: BIRD, where GAC helps, and what
  the certificates certify (25 -> 26 slides);
* charts are re-pointed with their embedded workbooks, so "Edit data" shows the same
  numbers the slide draws.

Slide 5 (the act-I divider) is left byte-identical, because
paper/scripts/restyle_detailed_deck.py reads its frame as the divider template.

The transform is assertive: it runs only on the original seminar deck (pinned by hash)
and reports "already current" on its own output. Usage:

    python paper/scripts/refresh_seminar_deck.py [--check] [--render-equations]
"""

from __future__ import annotations

import argparse
import hashlib
import html
import re
import zipfile
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
DECK = ROOT / "paper/slides/GAC-seminar.pptx"
EQ_DIR = ROOT / "paper/slides/seminar-equations"
ORIGINAL_SHA256 = "a5204149a5fdc2dc4e2e2f79a6926a17336a3e5c5740b5ebb7d95ec7c59df8a0"
NEW_PART_DATE = (2026, 10, 8, 0, 0, 0)
EMU = 914400

# Final presentation order, by slide part number (22 is removed; 26 and 27 are new).
ORDER = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 21, 18, 19, 20, 26, 17, 27, 23, 24, 25]
CLONE_FROM = 19
NEW_PARTS = (26, 27)
REMOVED_SLIDE = 22
REMOVED_PARTS = [
    "ppt/slides/slide22.xml", "ppt/slides/_rels/slide22.xml.rels",
    "ppt/notesSlides/notesSlide22.xml", "ppt/notesSlides/_rels/notesSlide22.xml.rels",
    "ppt/charts/chart4.xml", "ppt/charts/_rels/chart4.xml.rels",
    "ppt/embeddings/Microsoft_Excel_Worksheet3.xlsx",
    "ppt/media/image18.png", "ppt/media/image19.png",
]

# --------------------------------------------------------------------------- equations
# (media part, slide, picture id, max width in inches, TeX source)
EQUATIONS = [
    ("ppt/media/image2.png", 6, 10, 10.80, "eq1.png",
     r"$\forall c_j\in R,\ \forall u\in\mathrm{args}(c_j):\quad \mathrm{Lit}(c_j,u)\ \vee\ "
     r"\exists\,s\in\mathrm{Src}(z,o_{<j}),\ \exists\,g_{j,u}\in\mathcal{L}:\ u=g_{j,u}(s)$"),
    ("ppt/media/image10.png", 7, 26, 4.70, "eq3.png",
     r"$d_A(x)\ =\ \mathbf{1}\{\,H(z,M\prime)=1\ \wedge\ q(z)\leq\eta\ \wedge\ M\prime\simeq M\,\}$"),
    ("ppt/media/image11.png", 7, 30, 4.70, "eq4.png",
     (r"$\max_{A}\ \ \mathbb{E}_{G}\left[\sum_{x\in G}\,d_A(x)\,\{C(B,x)-C(A,x)\}\right]$",
      r"$\mathrm{s.t.}\quad \Pr_{G}\left[\,W_A(G)=1\ \middle|\ D_A(G)=1\,\right]\ \leq\ \alpha$")),
    ("ppt/media/image12.png", 11, 8, 10.80, "eq5.png",
     r"$\mathrm{score}(F)\ =\ s_F\,\bar{k}_F\,c_m\ -\ \lambda_1\,\mathrm{Ent}(F)\ -\ "
     r"\lambda_2\,\rho_{\mathrm{eff}}(F)\ -\ \lambda_3\,|F|$"),
    ("ppt/media/image13.png", 11, 14, 4.70, "eq6.png",
     r"$\Delta_{\max}\ =\ \dfrac{\varphi k}{n_B}\ \geq\ \Delta,\qquad \mathrm{realized:}\ \ "
     r"\varphi\rho k\ \geq\ \Delta\,n_B$"),
]

# --------------------------------------------------------------------------- text edits
# slide part -> {shape id: paragraph list}. "**x**" marks a bold run; the shape's own bold
# and regular runs supply the formatting.
T: dict[int, dict[int, list[str]]] = {}

T[1] = {
    7: ["**Guarded agentic compaction.** Recurrence proposes a candidate; evidence decides whether it "
        "compiles. Every stage can refuse, and the default output is the unchanged agent."],
    9: ["GitHub"], 10: ["3 workflow families,", "90/90 held-out contracts"],
    11: ["BIRD"], 12: ["26 of 31 databases compiled,", "45–50% fewer model calls"],
    13: ["NESTFUL  ·  AppWorld"], 14: ["two public benchmarks,", "no measured benefit"],
    15: ["Seminar presentation  ·  prepared by JazzX AI  ·  October 2026"],
}
TITLE_SLIDE_TITLE = "From Traces to Guarded Programs: Evidence-Gated Compilation of Recurrent Agent Workflows"

T[3] = {4: ["RELATED WORK  ·  §6"]}

T[4] = {
    8: ["QUESTIONS THIS TALK ANSWERS"],
    10: ["Q1"], 13: ["Q2"], 16: ["Q3"], 19: ["Q4"], 22: ["Q5"],
    11: ["When may a recurring read-only opening be compiled into a deterministic program, and when must it be refused?"],
    14: ["On real GitHub workflows, do guarded programs keep held-out contracts while cutting requests, tokens, "
         "latency, and cost, against the unchanged agent and a hand-written program?"],
    17: ["Does the result reach a public benchmark, newer records, a second model family, and a second provider?"],
    20: ["Where does admission refuse, and why: thin evidence, per-question choices, or rarely dispatchable programs?"],
    23: ["What do the certificates certify, and do the run-time guards protect under drift?"],
    26: ["A guarded specialization pipeline: typed provenance, effect and position barriers, bounded synthesis, "
         "run-time verification, and finite-sample compile-or-retire admission, where every stage can refuse",
         "A live evaluation on three GitHub workflow families, newer records across five repositories, a post-cutoff "
         "cohort with an end-to-end certificate, BIRD, drift ablations, and replications",
         "Calibrated refusal on public trace benchmarks: NESTFUL retires below the sample floor, and AppWorld "
         "separates admissible from dispatchable"],
    29: ["universal semantic equivalence  ·  production certification  ·  savings across snapshots  ·  graded risk "
         "ranking  ·  protection under drift  ·  runtime superiority over hand-written code"],
}

T[6] = {
    4: ["FORMULATION  ·  §2"],
    11: ["GROUNDABLE — every call argument in the region is a literal invariant across the supporting traces or an "
         "expression over entry state or prior results, drawn from a closed, bounded transform library ℒ. Any other "
         "slot is a genuine model decision."],
    19: ["POSITION INVARIANT — the deployed runtime resolves artifacts at the initial model boundary, so a region must "
         "be a prefix. A suffix program dispatched at entry can reorder or duplicate calls the agent has already made; "
         "an archived pilot produced exactly that fault."],
}

T[7] = {
    4: ["FORMULATION  ·  §2"],
    31: ["CONSTRAINED OBJECTIVE — maximize the dispatched saving over the unchanged agent B, subject to group-level "
         "selective risk ≤ α. Retire is a valid solution."],
    32: ["(4)"],
    34: ["**Honest reading of the objective.** Equation (4) is a design target, not a solved program: the "
         "implementation calibrates a bounded ranked set and keeps nondominated survivors, without an optimality "
         "guarantee. Every certificate but one counts a replay-contract violation of the compiled region, so the "
         "model's continuation is measured, not certified."],
    35: ["TWO EVENTS A CERTIFICATE CAN BOUND"],
    37: ["Replay contract"],
    38: ["The compiled region breaks its own registered contract. Every primary certificate uses this event, which "
         "has no support on the GitHub cohorts."],
    40: ["End-to-end contract"],
    41: ["The graded task contract, including the model's answer. Certified once: 0 misses on 132 post-cutoff pull "
         "requests, bound 0.0173."],
}

T[9] = {4: ["METHOD  ·  FIGURE 1  ·  ALGORITHM 2"]}

T[10] = {
    4: ["METHOD  ·  STAGE 1  ·  ALGORITHM 3 (BUILDPATG)"],
    6: ["For each call-argument slot the program-argument trace graph searches entry-state and prior-result paths for "
        "typed values reachable by a bounded transform in ℒ. A literal invariant across every supporting trace is "
        "also a witness; a repeated tool name or a successful replay is not."],
    16: ["|H| = 0"],
    24: ["More than κ = 3 witnesses. Blocked rather than defaulting to the cheapest explanation."],
    27: ["WORKED EXAMPLE — HELD-OUT ISSUE #4420 (FIGURE 2)"],
    29: ["2 / 2"], 30: ["issue_number slots"], 31: ["witnessed by entry or record"],
    33: ["none"], 34: ["comments.limit"], 35: ["100 in 130 traces, 1 in two"],
    37: ["3 → 2"], 38: ["reads emitted"], 39: ["three-read region retires"],
    41: ["132"], 42: ["discovery traces"], 43: ["all take the three-read route"],
    45: ["92 / 92"], 46: ["calibration groups"], 47: ["two-read prefix admitted"],
    49: ["0.0498"], 50: ["upper bound"], 51: ["against α = 0.05"],
    52: ["A recurrence-only optimizer would emit all three reads, since every discovery trace takes that route. GAC "
         "blocks the region on one unwitnessed slot (ungroundable_slot); the agent still chooses the limit and writes "
         "the answer. The PR-outcome and backlog artifacts bind their limit=3 slots as invariant literals."],
}

T[11] = {
    4: ["METHOD  ·  STAGES 2–3"],
    9: ["Expected saving from scenario-group support, mean removable model requests, and unit cost — charged for "
        "variant entropy, declared-effect exposure, and program size. Equation (5) affects only which family is "
        "tried first; no admission decision depends on it."],
    10: ["(5)"],
    15: ["FEASIBILITY CEILING — what the compiler could achieve with a perfect verifier and a gate that never abstains. "
         "Stage 3 checks only the left form (ρ = 1), so no measured reduction can exceed it, and a workload whose "
         "ceiling is under target is declined before any synthesis runs."],
    16: ["(6)"],
    18: ["WORKED EXAMPLE — PR-OUTCOME AUDIT (TABLE 1)"],
    26: ["**0.750**  ceiling  →  **75.0%**  measured. A saturated ceiling says only that the task fully determined the region."],
    27: ["The ceiling counts requests removed by the prefix at a fixed continuation workload. Changes in downstream "
         "reasoning or fallback can change total requests, which is why the realized form also carries the verifier "
         "pass rate ρ."],
}

T[12] = {
    4: ["METHOD  ·  STAGES 4–5  ·  TABLE 6"],
    5: ["Bounded synthesis and induced contracts: candidates, not proofs"],
    18: ["Under drift, the guards showed no measured protection"],
    19: ["Two provider-free perturbation studies are null by construction: the simulated tools stay total, and on the "
         "GitHub records the oracle is the derived call argument. In the live continuation-graded study an emptied "
         "list lies inside the learned hull, both arms answered wrongly on 39 of 60 records, and no held-out record "
         "shows a guard preventing a wrong compiled answer."],
}

T[13] = {
    4: ["METHOD  ·  STAGE 6  ·  ALGORITHM 1"],
    10: ["(7)"],
    13: ["One-sided Clopper–Pearson bound per threshold, Bonferroni-corrected over the grid. The score q is a logistic "
         "model over entry-observable features — missing fields, hull margin, temporal drift, provenance ambiguity — "
         "fitted on development groups only to predict an unproductive group, then frozen. The bound counts only "
         "dispatched groups that turned out wrong."],
    15: ["PROPOSITION 1 — PER-CANDIDATE SELECTIVE-RISK ADMISSION"],
    16: ["Fix one candidate (P, H, V, q), the group-level violation rule, and the finite grid Λ before calibration. If "
         "calibration groups are i.i.d. from the future-group distribution, then with probability at least 1 − δ "
         "every threshold satisfies r(η) ≤ U(η), so a selected threshold with U(η) ≤ α has selective risk at most α. "
         "A run is compiler-wide when one candidate reaches calibration."],
    22: ["at α = .05,  δ = .10,  |Λ| = 11. On a 92-group pool only full coverage is certifiable: abstaining on one "
         "group leaves U = 0.0503 > α. At δ = .05 the floor rises to 106."],
    25: ["A violation is a break of the compiled region's registered replay contract. On the GitHub cohorts that event "
         "has no support, because arguments are invariant and reads replay a pinned snapshot, so the bound confirms "
         "that enough groups were seen, not that risk was ranked."],
    26: ["WHAT THE CERTIFICATES COVER — AND WHAT THEY DO NOT"],
    28: ["Support sufficiency"], 29: ["92/92 zero-violation groups at full coverage"],
    31: ["End-to-end event"], 32: ["one post-cutoff cohort: 0/132, bound 0.0173"],
    34: ["Graded risk ranking"], 35: ["not certified: an amended 184-group gate retired"],
    36: ["Every bound assumes i.i.d. groups. Counting a creation day or an author as one unit retires every primary "
         "family under the registered grid."],
}

T[14] = {
    4: ["METHOD  ·  ALGORITHM 4"],
    33: ["WHERE “UNMODIFIED BASELINE” IS EXACT, AND WHERE IT IS NOT"],
}

T[15] = {8: ["Three GitHub workflows, newer records, a public benchmark where GAC helps, and two where it does not — "
             "with every refusal reported."]}

T[16] = {
    4: ["EXPERIMENTAL SETUP  ·  §4"],
    5: ["Three evidence sources, every comparison paired"],
    9: ["Real records, live provider"],
    10: ["Three GitHub workflow families on one pinned public snapshot"],
    11: ["132 discovery records each; 16 train, 8 dev, and 92 calibration groups",
         "30 balanced held-out records per family with exact, source-grounded answer contracts",
         "Baseline, compiled artifact, and a hand-written program on the same records"],
    15: ["Newer records, fresh cohort"],
    16: ["Five-repository PR-outcome extension and 132 post-cutoff pull requests"],
    17: ["Held-out records newer than discovery, inside each frozen snapshot",
         "Selection sealed before provider calls; retired repositories stay in the result",
         "Pull requests created after the snapshot carry the end-to-end certificate"],
    21: ["Public benchmarks"],
    22: ["BIRD with a live SQL agent; NESTFUL and AppWorld traces"],
    23: ["BIRD: pinned read-only databases, a standard and a schema-first agent",
         "NESTFUL and AppWorld: executable traces and no model runs, so no efficiency claim",
         "API-Bank and BFCL v4 behave like NESTFUL"],
    24: ["CONDITIONS, MODELS, AND STATISTICS — CONDITIONS WITHIN A FAMILY DIFFER IN STRUCTURE ALONE"],
    26: ["B"], 29: ["A"], 32: ["M"], 35: ["S"], 38: ["R"], 41: ["$"],
    27: ["the unchanged agent, the baseline every reduction is measured against"],
    30: ["the compiled artifact, dispatched only when guard, score, and pins pass"],
    33: ["a hand-written pre-model program written with full workflow knowledge"],
    36: ["paired exact McNemar, bootstrap intervals, Wilcoxon signed-rank tests"],
    39: ["gpt-5.6-luna primary; gpt-6-luna and claude-sonnet-5 replications"],
    42: ["requests, interfaces, tokens, latency, and cost at list prices"],
    43: ["The exact-trace filter keeps 130–132 of 132 discovery records per family, so each certificate is conditional "
         "on that selection. Gate multiplicity is controlled by the Bonferroni term of Equation (7)."],
}

T[17] = {
    4: ["RESULTS  ·  §5.4  ·  TABLE 2"],
    5: ["Where GAC yields no measured benefit: NESTFUL and AppWorld"],
    6: ["Thin evidence: NESTFUL, the largest trace corpus the compiler ingests (1,415 traces), passes provenance, "
        "synthesis, and replay with no wrong execution.",
        "Yet its best family reaches 26 independent groups against the 92 the gate requires, so all 32 families retire "
        "at stage 6. API-Bank and BFCL v4 retire the same way, at 8 and 15.",
        "Admissible, rarely dispatchable: on AppWorld's gold solutions one argument-free two-call artifact is admitted "
        "at 92/92 groups, yet ReAct and plan-and-execute agents open by reading API documentation and almost never "
        "reach it."],
    8: ["**No model runs on either benchmark, so neither licenses an efficiency claim.** The floor is a corpus-size "
        "fact: it bounds what public trace benchmarks can certify, not what the compiler can do. Admitting the "
        "documentation read as a prologue recovers only 2 more of 4,680 runs."],
    10: ["TABLE 2 — THE TWO TRACE BENCHMARKS WITH NO MEASURED GAC BENEFIT"],
    12: ["1,415"], 13: ["NESTFUL executable traces"],
    15: ["26 / 92"], 16: ["best family support vs. gate floor"],
    18: ["0 / 32"], 19: ["NESTFUL families admitted"],
    21: ["24 / 12 / 0"], 22: ["replay pass / abstain / wrong"],
    24: ["136"], 25: ["largest AppWorld family support"],
    27: ["2,339/2,340"], 28: ["full-code runs that can dispatch"],
    30: ["1 / 4,680"], 31: ["ReAct or plan-and-execute runs"],
}

T[18] = {
    4: ["RESULTS  ·  §5.1  ·  ISSUE-TYPE ROUTING  ·  TABLES 1 AND 11"],
    5: ["Issue-type routing: the compiler keeps only what it can ground"],
    9: ["All 132 discovery traces read record → labels → comments under a prompt naming neither tools nor order",
        "The comments limit is 100 in 130 traces and 1 in two: not an invariant literal, and no trace-grounded "
        "expression reproduces it",
        "The full three-read candidate is rejected with ungroundable_slot; the compiler emits the two-read prefix, and "
        "the agent performs the comments read and the final answer",
        "16 training, 8 development, 92 calibration records from the 130 eligible traces; 14 unused",
        "The gate admits 92/92 calibration groups with zero registered violations at α = .05, δ = .10, |Λ| = 11 — "
        "simultaneous upper bound 0.0498"],
    24: ["exact contracts, every arm"],
    27: ["one-sided bound on compiled-only misses"],
    28: ["The hand-written program uses one tool interface instead of three and fewer tokens; only latency favors the "
         "compiler. On a 92-group pool only full coverage is certifiable, and discovery breaks even after 411 episodes "
         "for this family."],
}

T[19] = {
    4: ["RESULTS  ·  §1  ·  APPENDIX F.2  ·  CONTINUATION AUDIT"],
    5: ["Recurrence proposes a program; it does not license one"],
    7: ["Two-read prefix"], 8: ["registered study, α = .05, 30 issues"],
    9: ["−50.0%"], 10: ["provider requests"], 11: ["−39.5%"], 12: ["total tokens"],
    13: ["30 / 30"], 14: ["exact contracts"], 15: ["92 / 92"], 16: ["calibration groups, bound 0.0498"],
    17: ["Groundability permits only two of three reads. No accuracy difference is detected; equivalence is not "
         "established."],
    19: ["Three-read artifact"], 20: ["earlier study, α = .10, 18 issues"],
    21: ["45 / 45"], 22: ["calibration replays passed"], 23: ["18 / 18"], 24: ["held-out tool contracts"],
    25: ["17 / 18"], 26: ["exact downstream answers"], 27: ["18 / 18"], 28: ["after checked rendering"],
    29: ["On issue #6602 the source held a Markdown link; the compiled continuation dropped the URL and returned only "
         "its anchor text."],
    33: ["The miss fixes the gate's scope — and motivates a continuation check"],
    34: ["Zero replay violations concern the compiled tool program, not the model's answer, so 45/45 clean calibration "
         "replays and a held-out factual miss are compatible. A provider-free continuation check, run after the "
         "model's answer, passes 17 retained answers unchanged, detects #6602, and checked-renders it to 18/18. That "
         "shows detection on retained records, not live quality or safety."],
    35: ["The three-read study is excluded from the registered α = .05 headline because it used α = .10 and exposed a "
         "continuation error. A recurrence-only optimizer would have shipped the three-read program and accepted the "
         "answer."],
}

T[20] = {
    4: ["RESULTS  ·  §5.2  ·  TABLES 14 AND 15"],
    5: ["Newer records: compile or retire, and one end-to-end certificate"],
    8: ["Four of five repositories compile; one retires"],
    9: ["On the two-read PR-outcome task the compiled agent completes 120/120 exact contracts across four "
        "repositories. pytorch/pytorch retires at admission: no calibration group is accepted at any threshold."],
    11: ["Abstention by composition, not failure"],
    12: ["Every open-class record abstained on the induced pr.state hull, because discovery held 0–3 open records. A "
         "balanced rerun with all classes in discovery dispatches on 180/180 and reaches 180/180."],
    14: ["One end-to-end certificate, on fresh pull requests"],
    15: ["On 132 pull requests created after the snapshot's last day, the re-derived artifact missed 0 graded task "
         "contracts: bound 0.0173 (0.035 on the grid). The draw held open and merged, but no closed-unmerged, pull "
         "requests."],
    17: ["**Held-out records are newer than discovery but inside the same frozen snapshot.** The program ran on 80/120 "
         "core records, so requests fell 44.4% overall and 66.7% where it dispatched. The hand-written program is "
         "more efficient in the core protocol and tied in the balanced rerun."],
}

T[21] = {
    4: ["RESULTS  ·  §5.1  ·  TABLES 1 AND 11"],
    5: ["Three GitHub workflows: 90/90 kept, two-thirds fewer calls"],
    6: ["Across 90 held-out records the compiled agent satisfies 90/90 exact contracts and the unchanged agent 89/90, "
        "with **zero compiled-only misses.** Requests fall 66.6%, tokens 63.1%, latency 64.2%, and cost 58.7%."],
    7: ["TABLE 11 — REDUCTION VS THE UNCHANGED AGENT, SAME 90 RECORDS (%), HIGHER IS BETTER"],
    10: ["Hand-written programs written with full workflow knowledge also reach 90/90. They tie on requests, use fewer "
         "interfaces and tokens, cost marginally less, and lose only on latency. The claim is automated discovery and "
         "guarded admission, not runtime dominance over code written by someone who already knows the workflow."],
    14: ["Write the program by hand when…"],
    8: ["WHAT THE PRIMARY RESULT DOES AND DOES NOT ESTABLISH"],
    23: ["Each artifact was admitted at 92/92 zero-violation calibration groups (U = 0.0498). The one discordant pair is "
         "a baseline-only miss (McNemar p = 1; one-sided bound on compiled-only misses 3.3%), and a rerun scored 30/30 "
         "in every arm, so no accuracy difference is detected and equivalence is not established. Savings are marginal "
         "per episode within one snapshot: every artifact pins its snapshot digest, and discovery breaks even after "
         "411, 183, and 181 episodes per family. A recurrence-only replay on issue-type routing also passed 30/30 at "
         "one request per record."],
}

T[23] = {
    4: ["DISCUSSION AND LIMITATIONS  ·  §7"],
    9: ["The gate did not rank risk"],
    10: ["Every threshold below 0.14 admits no calibration group and every one at or above it admits all 92, with zero "
         "violations throughout. A support-only comparator on 240 held-out pairs found the same step, and an amended "
         "184-group end-to-end issue gate retired with two errors. No risk–coverage frontier is certified."],
    14: ["Certificates assume independence"],
    15: ["Every bound assumes i.i.d. groups. Counting a creation day or an author as one unit retires every primary "
         "family under the registered grid, and AppWorld's bound retires at scenario or supervisor level. The "
         "end-to-end certificate covers one family and excludes closed-unmerged pull requests."],
    19: ["Savings stay inside one snapshot"],
    20: ["Every artifact pins its snapshot digest and abstains on any other, so a new snapshot is recompiled. Savings "
         "are marginal per episode, and discovery breaks even after 181–411 episodes per family. Manual authoring "
         "effort is not priced."],
    25: ["Moderation, policy, and guardrail checks commonly run at model boundaries. A region that deletes three of four "
         "boundaries risks deleting three of four evaluations. Writes, handoffs, hosted tools, undeclared effects, and "
         "removed-turn guardrails lie outside Proposition 1."],
    29: ["Guards gave no measured protection"],
    30: ["Two provider-free drift studies are null by construction. In the live continuation-graded study an emptied "
         "list lies inside the learned hull, and both arms answered wrongly on 39 of 60 records under the original "
         "grader, 40 under its correction."],
    34: ["The evidence base is narrow"],
    35: ["One pinned snapshot, five frozen cross-repository snapshots, one post-cutoff cohort, one public benchmark with "
         "a live agent, and one calibrated model family. Every GitHub compiled-only miss is an excerpt departing from "
         "identical evidence, with no counterfactual attributing it to the model."],
    36: ["Also: 810 held-out GitHub episodes in six studies produced one compiled-only contract failure; AWO, Agent JIT, "
         "and EvoC2F were not run head-to-head; the closed DSL intentionally misses legitimate transformations and "
         "loops; and a recurrence-only replay on issue-type routing also passed 30/30."],
}

T[24] = {
    4: ["CLAIMS AND EVIDENCE  ·  APPENDIX I"],
    5: ["The claims register — retained to prevent narrative drift"],
    7: ["Five claims are not supported, and every claim that stands carries its scope inside the verdict cell. "
        "Unsupported claims are retained so a later reading cannot quietly promote them."],
    9: ["WHAT IS NOT SHOWN"],
    10: ["no runtime superiority over hand-written code  ·  no graded risk ranking  ·  no protection under drift  ·  "
          "no savings across snapshots"],
}

T[25] = {
    7: ["Judge an optimizer by its evidence, refusals, and fallback — not by turns removed"],
    11: ["Each element — typed provenance, effect and position barriers, bounded readable synthesis, run-time "
         "verification, finite-sample admission — has predecessors. The contribution is that an agent guard needs all "
         "of them at once, and that every stage can refuse."],
    14: ["Compile what the agent does, not what it is asked"],
    15: ["On BIRD a schema-first agent compiles on 26 of 31 databases with 45–50% fewer model calls. An agent that "
         "chooses its tables per question, and Claude Sonnet told to read every table, are refused."],
    18: ["Certification, not recurrence, is the scarce resource"],
    19: ["NESTFUL's best family reaches 26 of the 92 groups the gate needs, AppWorld's admitted program fits almost no "
         "ReAct run, and the GitHub certificates mostly confirm sample size. Refusal exposes the data requirement."],
    22: ["Efficiency is not superiority or protection"],
    23: ["Hand-written programs also reach 90/90 and use fewer tokens, savings hold within one snapshot, and under drift "
         "the run-time checks prevented no wrong answer. The claim is discovery and admission."],
    25: ["Next threshold: certify graded risk ranking, transfer across snapshots, and protection under drift — none is "
         "shown here."],
}

# New slides on the slide-19 two-card frame.
NEW_SLIDES: dict[int, dict[int, list[str]]] = {
    26: {
        4: ["RESULTS  ·  §5.3  ·  PUBLIC BENCHMARK  ·  TABLES 19–22"],
        5: ["BIRD: a public benchmark where GAC helps"],
        7: ["Schema-first agent"], 8: ["reads every table first  ·  26 of 31 databases"],
        9: ["−45.8%"], 10: ["requests, 629 completed training pairs"],
        11: ["402 / 403"], 12: ["correct of 630, compiled vs. unchanged"],
        13: ["[−3.3, +3.0]"], 14: ["accuracy difference, 95% interval (points)"],
        15: ["−49.6%"], 16: ["requests on gpt-6-luna; 93 vs. 91 of 150"],
        17: ["On the five dev databases the compiled agent dispatched on every question and answered 97 against 94 of "
             "150 (McNemar p = 0.45)."],
        19: ["Standard agent"], 20: ["picks its tables for each question"],
        21: ["0 / 36"], 22: ["database runs compiled, two OpenAI models"],
        23: ["7–39"], 24: ["distinct table lists per dev database"],
        25: ["0 / 10"], 26: ["database-design pairs on Claude Sonnet"],
        27: ["26 / 655"], 28: ["Sonnet runs that passed every table"],
        29: ["The table list is a per-question model decision, so there is nothing fixed to compile."],
        33: ["GAC compiles what an agent does, not what its prompt asks for"],
        34: ["On 930 scheduled held-out questions with a compiled agent (26 databases, two model families), no run showed "
             "a detected accuracy loss, though equivalence is not established. Requests fell 45–50%, latency 29–38%, and "
             "cost 11–18% at uncached prices. A hand-written schema prefetch matches the compiled program."],
        35: ["All-scheduled counts treat a missing run as incorrect in its own arm. The training comparison covers 21 of "
             "26 compiled databases, and Table 22 reports database sensitivity. A second provider's agent never ran a "
             "fixed opening and was refused."],
    },
    27: {
        4: ["DISCUSSION  ·  §5.1 AND §7  ·  WHAT THE CERTIFICATES CERTIFY"],
        5: ["What the certificates certify"],
        7: ["End-to-end certificate"], 8: ["132 fresh post-cutoff pull requests  ·  one family"],
        9: ["0 / 132"], 10: ["end-to-end contract misses"],
        11: ["0.0173"], 12: ["upper bound, 90% confidence (0.035, grid)"],
        13: ["60 / 60"], 14: ["fresh test records, every condition"],
        15: ["84 / 48"], 16: ["open / merged; none closed-unmerged"],
        17: ["The first certificate whose event includes the model's answer. Counting days or authors as units gives "
             "0.0228 and 0.0267; independence of those clusters is unverified."],
        19: ["Primary certificates"], 20: ["three GitHub families  ·  92 calibration groups each"],
        21: ["92 / 92"], 22: ["zero-violation calibration groups"],
        23: ["0.0498"], 24: ["upper bound against α = 0.05"],
        25: ["0 or 1"], 26: ["the only certifiable coverages"],
        27: ["2 errors"], 28: ["amended 184-group issue gate: retired"],
        29: ["The replay-contract event has no support on these cohorts, so the bound confirms enough examples, not an "
             "observed risk."],
        32: ["!"],
        33: ["Same programs on a second model and provider; no protection under drift"],
        34: ["Re-discovery on gpt-6-luna and claude-sonnet-5 re-derives the identical programs on two of three GitHub "
             "families and refuses backlog routing (on Sonnet at 91 and 90 of 92 groups). Under tool-layer drift the "
             "run-time checks prevented no wrong answer: both arms answered wrongly on 39 of 60 records."],
        35: ["Across 810 held-out GitHub episodes in six studies, one compiled-only contract failure occurred: 1 of 270 "
             "on excerpt-bearing contracts (one-sided bound 1.7%) and 0 of 540 on the outcome-only cross-repository "
             "contract."],
    },
}

# --------------------------------------------------------------------------- tables
INK, MUTED, RED, TEAL, GOLD = "24354F", "5A6B84", "A93B2B", "1F8A99", "B5821F"
# verdict text colour -> verdict cell fill, as the original register pairs them
VERDICT_FILL = {GOLD: "FBF4E6", RED: "FBF0EC", MUTED: "EFF1F4"}
# slide 21 table: (text, colour, bold) per cell
TABLE_21 = [
    [("Resource", None, None), ("Manual", None, None), ("GAC", None, None), ("Better", None, None)],
    [("Provider requests", INK, False), ("66.6", INK, False), ("66.6", INK, False), ("tie", INK, False)],
    [("Provider-visible tool interfaces", INK, False), ("66.5", RED, True), ("44.2", INK, False), ("manual", RED, True)],
    [("Total tokens", INK, False), ("71.1", RED, True), ("63.1", INK, False), ("manual", RED, True)],
    [("Observed wall latency", INK, False), ("62.2", INK, False), ("64.2", TEAL, True), ("GAC", TEAL, True)],
    [("Estimated cost", INK, False), ("60.4", RED, True), ("58.7", INK, False), ("manual", RED, True)],
]
CLAIMS = [
    ("Guarded programs keep held-out contracts on the GitHub families", "90/90 compiled vs. 89/90 unchanged; zero compiled-only misses", "Yes; no difference detected", GOLD),
    ("Compiled programs remove model calls", "−66.6% requests, −63.1% tokens, −58.7% cost on 90 records", "Yes; within one snapshot", GOLD),
    ("Compile-or-retire holds on newer records", "120/120 on four repositories; pytorch/pytorch retires", "Yes; inside frozen snapshots", GOLD),
    ("The end-to-end contract can be certified", "0/132 post-cutoff misses; bound 0.0173", "One family; open and merged PRs", GOLD),
    ("GAC helps on a public benchmark", "BIRD: 26/31 compiled; −45.8% requests; 402 vs. 403 of 630", "No loss detected; not equivalence", GOLD),
    ("Admission refuses per-question choices", "BIRD standard agent 0/36; Claude Sonnet 0/10", "Yes; two designs refused", GOLD),
    ("Programs re-derive on other models", "gpt-6-luna and claude-sonnet-5: 2 of 3 families", "Yes; backlog refused", GOLD),
    ("Compiled programs beat hand-written code", "Manual 90/90; ties requests, wins tokens and cost", "Not supported", RED),
    ("Public trace benchmarks can be certified", "NESTFUL best family 26 < 92; API-Bank 8; BFCL v4 15", "Not supported", RED),
    ("An admitted artifact is dispatchable", "AppWorld: 2,339/2,340 full-code vs. 1/4,680 ReAct runs", "Rarely, by agent design", MUTED),
    ("The learned gate ranks dispatch risk", "Step at 0.14; amended 184-group gate retired", "Not supported", RED),
    ("Run-time guards protect under drift", "Both arms wrong on 39 of 60; two studies null", "Not supported", RED),
    ("Certificates survive clustered units", "A day or author as one unit retires every family", "Not supported", RED),
]

# --------------------------------------------------------------------------- charts
CHART2_RENAME = ("Hand-written macro", "Hand-written program")
CHART3 = {
    "title": "Saving versus the unchanged agent, per repository (%)",
    "categories": ["datasets\ncore", "pandas\ncore", "requests\ncore", "streamlit\ncore",
                   "pandas\nbalanced", "requests\nbalanced", "pytorch\nbalanced"],
    "series": [("Requests saved", [44.4, 44.4, 44.4, 44.4, 66.7, 66.7, 66.7]),
               ("Tokens saved", [52.2, 52.5, 52.3, 52.7, 78.6, 78.7, 78.0])],
    "axis": (0, 100, 20),
}

# --------------------------------------------------------------------------- notes
NOTES: dict[int, str] = {
    1: "Two framing sentences. The engineering result is that recurring read-only openings can be compiled into "
       "guarded programs: two-thirds fewer model calls on three GitHub workflows with 90/90 contracts kept, and 45–50% "
       "fewer on BIRD with no detected loss. The scientific result is that the compiler must refuse where evidence is "
       "thin or the opening is a per-question choice, and that its certificates mostly confirm sample size.",
    4: "Q4 and Q5 are the unusual questions. Most workflow-optimization papers report what their system compresses; "
       "this one also asks what it must decline, and what its guarantees actually cover.",
    6: "The archived pilot compiled suffix-only regions even though the runtime resolves only at entry. It dispatched "
       "label and comment reads before their intended position and duplicated or reordered tools. It is kept as the "
       "empirical case for the position invariant. Note the grounding rule now admits invariant literals, which is how "
       "the limit=3 slots of two artifacts are bound.",
    7: "Worth stating plainly: the paper marks its own optimality gap. Equation (4) is a target; the implementation "
       "calibrates a bounded ranked set. And only one certificate in the paper bounds the end-to-end event.",
    10: "The worked example is the paper's Figure 2. One varying literal is enough to retire the three-read region; "
        "the compiler emits the maximal justified prefix and leaves the rest to the agent.",
    11: "The two coarse terms affect ranking only, never admission. The worked example uses the PR-outcome audit, "
        "where the measured 75.0% equals the ceiling.",
    12: "This is where a reviewer pushes hardest. The guards are candidate invariants, and under tool-layer "
        "corruption their measured protective value was null or adverse.",
    13: "Say the sharp version out loud: on 92-group pools the gate can certify only full coverage, so these "
        "certificates are support-sufficiency statements. One post-cutoff cohort carries an end-to-end certificate.",
    15: "Sections 4 and 5. The evidence is three GitHub families on one snapshot, newer records, one fresh cohort, "
        "and three public benchmarks, two of which show no measured benefit.",
    16: "Every comparison is paired on the same records, model, and grader. The hand-written program is the "
        "pessimistic comparator: it is written by someone who already knows the workflow.",
    17: "Two different reasons for no benefit. NESTFUL is a corpus-size fact: no family reaches the floor. AppWorld "
        "is a dispatch fact: the admitted program sits behind a documentation read that most agent designs make first.",
    18: "The tool-call bar is the honest one: the compiler keeps all three reads in this family and removes model "
        "decisions, not evidence acquisition. The hand-written program removes reads because a human designed it.",
    19: "This is the paper's introduction in one slide. Recurrence alone would have shipped the three-read program; "
        "groundability retires it, and the earlier study shows why: clean replays do not certify the answer.",
    20: "The open-class abstentions are the verifier working as designed on an unseen class, not a failure. The "
        "post-cutoff cohort is the only place the paper certifies the end-to-end event.",
    21: "The paper does not claim GAC dominates ordinary engineering. Hand-written programs written with full "
        "knowledge tie or win on most axes; GAC's value claim is discovering and admitting such programs automatically.",
    23: "Read the gate result carefully: the step at 0.14 is the sample-size floor, not a learned risk ranking. The "
        "amended 184-group study was the attempt to buy a frontier, and it retired.",
    24: "If a reviewer wants one slide to judge the paper's honesty, this is it. Every supported claim carries its "
        "scope, and the five unsupported claims stay in the register.",
    25: "Closing line from the paper: compile only what is justified, and keep the model's reasoning everywhere else. "
        "Judge such optimizers by evidence, refusals, and fallback, not by turns removed.",
    26: "BIRD is the public-benchmark result. The same compiler that refuses the standard agent compiles the "
        "schema-first one, because only the latter runs a fixed opening. Quality differences are inside the interval; "
        "the paper claims no detected loss, not equivalence.",
    27: "Separate the two certificate kinds. The primary ones confirm enough examples on an event without support; "
        "the post-cutoff one bounds the end-to-end task contract for one family and two pull-request classes.",
}


# --------------------------------------------------------------------------- XML helpers
def _text(fragment: str) -> str:
    return html.unescape("".join(re.findall(r"<a:t(?: [^>]*)?>(.*?)</a:t>", fragment, re.S)))


def _shape(xml: str, shape_id: int, kind: str = "sp") -> tuple[int, int]:
    for m in re.finditer(rf"<p:{kind}>.*?</p:{kind}>", xml, re.S):
        if re.search(rf'<p:cNvPr id="{shape_id}"[ >/]', m.group(0)):
            return m.start(), m.end()
    raise KeyError(f"{kind} id {shape_id} not found")


def _paragraphs(block: str) -> list[re.Match[str]]:
    return list(re.finditer(r"<a:p>.*?</a:p>|<a:p .*?</a:p>", block, re.S))


def _segments(text: str) -> list[tuple[str, bool]]:
    pieces = text.split("**")
    return [(p, i % 2 == 1) for i, p in enumerate(pieces) if p]


def _rpr(run: str) -> str:
    m = re.search(r"<a:rPr[^>]*/>|<a:rPr[^>]*>.*?</a:rPr>", run, re.S)
    return m.group(0) if m else '<a:rPr lang="en-US"/>'


def _with_bold(rpr: str, bold: bool) -> str:
    head = re.match(r"<a:rPr[^>]*", rpr).group(0)
    new_head = re.sub(r' b="[01]"', "", head) + (' b="1"' if bold else ' b="0"')
    return new_head + rpr[len(head):]


def _with_colour(rpr: str, colour: str) -> str:
    return re.sub(r'(<a:solidFill><a:srgbClr val=")\w+(")', rf"\g<1>{colour}\2", rpr, count=1)


def _paragraph(template: str, text: str, colour: str | None = None, bold: bool | None = None) -> str:
    runs = re.findall(r"<a:r>.*?</a:r>", template, re.S)
    if not runs:
        raise ValueError("template paragraph has no run")
    rprs = [_rpr(r) for r in runs]
    plain = next((r for r in rprs if ' b="1"' not in r), _with_bold(rprs[0], False))
    strong = next((r for r in rprs if ' b="1"' in r), _with_bold(rprs[0], True))
    first, last = template.index(runs[0]), template.rindex(runs[-1]) + len(runs[-1])
    marked = "**" in text
    out = []
    for seg, is_bold in _segments(text):
        rpr = (strong if is_bold else plain) if marked else rprs[0]
        if bold is not None:
            rpr = _with_bold(rprs[0], bold)
        if colour:
            rpr = _with_colour(rpr, colour)
        out.append(f"<a:r>{rpr}<a:t>{escape(seg)}</a:t></a:r>")
    return template[:first] + "".join(out) + template[last:]


def set_paragraphs(xml: str, shape_id: int, texts: list[str], kind: str = "sp") -> str:
    start, end = _shape(xml, shape_id, kind)
    block = xml[start:end]
    paras = [p for p in _paragraphs(block) if "<a:r>" in p.group(0)]
    if not paras:
        raise ValueError(f"shape {shape_id} has no text paragraph")
    new = "".join(_paragraph(paras[min(i, len(paras) - 1)].group(0), t) for i, t in enumerate(texts))
    block = block[: paras[0].start()] + new + block[paras[-1].end():]
    return xml[:start] + block + xml[end:]


def set_table(xml: str, frame_id: int, rows: list[list[tuple]]) -> str:
    start, end = _shape(xml, frame_id, "graphicFrame")
    block = xml[start:end]
    trs = list(re.finditer(r"<a:tr .*?</a:tr>", block, re.S))
    if len(trs) != len(rows):
        raise ValueError(f"table {frame_id}: {len(trs)} rows, {len(rows)} given")
    out, cursor = [], 0
    for tr, cells in zip(trs, rows):
        row = tr.group(0)
        tcs = list(re.finditer(r"<a:tc>.*?</a:tc>|<a:tc .*?</a:tc>", row, re.S))
        if len(tcs) != len(cells):
            raise ValueError(f"table {frame_id}: column count mismatch")
        new_row, c = [], 0
        for tc, spec in zip(tcs, cells):
            text, colour, bold = spec[:3]
            cell = tc.group(0)
            if len(spec) > 3:
                tcpr = re.search(r"<a:tcPr.*?</a:tcPr>", cell, re.S)
                fills = list(re.finditer(r'<a:solidFill><a:srgbClr val="\w+"/></a:solidFill>', tcpr.group(0)))
                last = fills[-1]
                new_pr = (tcpr.group(0)[: last.start()] + f'<a:solidFill><a:srgbClr val="{spec[3]}"/></a:solidFill>'
                          + tcpr.group(0)[last.end():])
                cell = cell[: tcpr.start()] + new_pr + cell[tcpr.end():]
            para = _paragraphs(cell)[0]
            cell = cell[: para.start()] + _paragraph(para.group(0), text, colour, bold) + cell[para.end():]
            new_row.append(row[c: tc.start()] + cell)
            c = tc.end()
        new_row.append(row[c:])
        out.append(block[cursor: tr.start()] + "".join(new_row))
        cursor = tr.end()
    out.append(block[cursor:])
    return xml[:start] + "".join(out) + xml[end:]


def set_picture(xml: str, pic_id: int, width_px: int, height_px: int, max_width_in: float) -> str:
    start, end = _shape(xml, pic_id, "pic")
    block = xml[start:end]
    m = re.search(r'<a:off x="(\d+)" y="(\d+)"/><a:ext cx="(\d+)" cy="(\d+)"/>', block)
    x, y, _, cy = (int(v) for v in m.groups())
    cx = round(cy * width_px / height_px)
    max_cx = round(max_width_in * EMU)
    if cx > max_cx:
        new_cy = round(max_cx * height_px / width_px)
        y += (cy - new_cy) // 2
        cx, cy = max_cx, new_cy
    block = block[: m.start()] + f'<a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/>' + block[m.end():]
    block = re.sub(r' descr="[^"]*"', "", block, count=1)
    return xml[:start] + block + xml[end:]


def set_font_size(xml: str, shape_id: int, old: int, new: int) -> str:
    start, end = _shape(xml, shape_id)
    block = xml[start:end]
    if f'sz="{old}"' not in block:
        raise ValueError(f"shape {shape_id}: size {old} not found")
    return xml[:start] + block.replace(f'sz="{old}"', f'sz="{new}"') + xml[end:]


def notes_with(xml: str, text: str) -> str:
    return set_paragraphs(xml, 3, [text])


# --------------------------------------------------------------------------- charts and workbooks
def _num(v: float) -> str:
    return f"{v:g}"


def rewrite_chart(xml: str, spec: dict) -> str:
    cats, series = spec["categories"], spec["series"]
    n = len(cats)
    xml = re.sub(r"(<c:title>.*?<a:t>).*?(</a:t>)", lambda m: m.group(1) + escape(spec["title"]) + m.group(2),
                 xml, count=1, flags=re.S)
    sers = list(re.finditer(r"<c:ser>.*?</c:ser>", xml, re.S))
    if len(sers) != len(series):
        raise ValueError("chart series count mismatch")
    col = "BCDEFG"
    cat_cache = (f'<c:strCache><c:ptCount val="{n}"/>'
                 + "".join(f'<c:pt idx="{i}"><c:v>{escape(c)}</c:v></c:pt>' for i, c in enumerate(cats))
                 + "</c:strCache>")
    out, cursor = [], 0
    for k, (m, (name, values)) in enumerate(zip(sers, series)):
        s = m.group(0)
        s = re.sub(r"(<c:tx><c:strRef>.*?<c:v>).*?(</c:v>)", lambda q: q.group(1) + escape(name) + q.group(2),
                   s, count=1, flags=re.S)
        s = re.sub(r"<c:cat>.*?</c:cat>",
                   f"<c:cat><c:strRef><c:f>Sheet1!$A$2:$A${n + 1}</c:f>{cat_cache}</c:strRef></c:cat>", s, flags=re.S)
        s = re.sub(r"<c:val>.*?</c:val>",
                   f"<c:val><c:numRef><c:f>Sheet1!${col[k]}$2:${col[k]}${n + 1}</c:f><c:numCache>"
                   f'<c:formatCode>General</c:formatCode><c:ptCount val="{n}"/>'
                   + "".join(f'<c:pt idx="{i}"><c:v>{_num(v)}</c:v></c:pt>' for i, v in enumerate(values))
                   + "</c:numCache></c:numRef></c:val>", s, flags=re.S)
        out.append(xml[cursor: m.start()] + s)
        cursor = m.end()
    out.append(xml[cursor:])
    xml = "".join(out)
    lo, hi, step = spec["axis"]
    xml = re.sub(r'<c:max val="[^"]*"/><c:min val="[^"]*"/>', f'<c:max val="{hi}"/><c:min val="{lo}"/>', xml)
    xml = re.sub(r'<c:majorUnit val="[^"]*"/>', f'<c:majorUnit val="{step}"/>', xml)
    return xml


def _rezip(original: bytes, replace: dict[str, bytes]) -> bytes:
    out = BytesIO()
    with zipfile.ZipFile(BytesIO(original)) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            zout.writestr(info, replace.get(info.filename, zin.read(info.filename)))
    return out.getvalue()


def rewrite_workbook(xlsx: bytes, spec: dict) -> bytes:
    cats, series = spec["categories"], spec["series"]
    strings = [""] + [name for name, _ in series] + list(cats)
    cols = "ABCDEFG"[: len(series) + 1]
    rows = ['<row r="1" spans="1:{w}">'.format(w=len(cols))
            + "".join(f'<c r="{cols[j]}1" t="s"><v>{j}</v></c>' for j in range(len(cols))) + "</row>"]
    for i, cat in enumerate(cats):
        r = i + 2
        cells = f'<c r="A{r}" t="s"><v>{1 + len(series) + i}</v></c>'
        cells += "".join(f'<c r="{cols[k + 1]}{r}"><v>{_num(vals[i])}</v></c>' for k, (_, vals) in enumerate(series))
        rows.append(f'<row r="{r}" spans="1:{len(cols)}">{cells}</row>')
    last = f"{cols[-1]}{len(cats) + 1}"
    with zipfile.ZipFile(BytesIO(xlsx)) as z:
        sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
        table = z.read("xl/tables/table1.xml").decode("utf-8")
    sheet = re.sub(r'<dimension ref="[^"]*"/>', f'<dimension ref="A1:{last}"/>', sheet)
    sheet = re.sub(r"<sheetData>.*?</sheetData>", "<sheetData>" + "".join(rows) + "</sheetData>", sheet, flags=re.S)
    sst = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{len(strings)}" '
           f'uniqueCount="{len(strings)}">'
           + "".join(f'<si><t xml:space="preserve">{escape(s)}</t></si>' for s in strings) + "</sst>")
    table = re.sub(r' ref="[^"]*"', f' ref="A1:{last}"', table, count=1)
    for k, (name, _) in enumerate(series):
        table = re.sub(rf'(<tableColumn id="{k + 2}" name=")[^"]*(")', rf"\g<1>{escape(name)}\2", table)
    return _rezip(xlsx, {"xl/worksheets/sheet1.xml": sheet.encode("utf-8"),
                         "xl/sharedStrings.xml": sst.encode("utf-8"),
                         "xl/tables/table1.xml": table.encode("utf-8")})


def rename_in_workbook(xlsx: bytes, old: str, new: str) -> bytes:
    with zipfile.ZipFile(BytesIO(xlsx)) as z:
        sst = z.read("xl/sharedStrings.xml").decode("utf-8")
        table = z.read("xl/tables/table1.xml").decode("utf-8")
    if old not in sst:
        raise ValueError("workbook string to rename not found")
    return _rezip(xlsx, {"xl/sharedStrings.xml": sst.replace(old, new).encode("utf-8"),
                         "xl/tables/table1.xml": table.replace(old, new).encode("utf-8")})


# --------------------------------------------------------------------------- equations
def render_equations() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image

    plt.rcParams["mathtext.fontset"] = "stix"
    EQ_DIR.mkdir(parents=True, exist_ok=True)

    def one(tex: str, path: Path) -> None:
        fig = plt.figure()
        fig.text(0, 0, tex, fontsize=24.5, color="#0E1E3A")
        fig.savefig(path, dpi=300, transparent=True, bbox_inches="tight", pad_inches=0.02,
                    metadata={"Software": None})
        plt.close(fig)

    for _, _, _, _, name, tex in EQUATIONS:
        path = EQ_DIR / name
        if isinstance(tex, tuple):
            parts = []
            for i, line in enumerate(tex):
                p = EQ_DIR / f".{name}.{i}.png"
                one(line, p)
                parts.append(Image.open(p).convert("RGBA"))
                p.unlink()
            w = max(p.width for p in parts)
            img = Image.new("RGBA", (w, sum(p.height for p in parts) + 30 * (len(parts) - 1)), (0, 0, 0, 0))
            y = 0
            for p in parts:
                img.paste(p, (0, y))
                y += p.height + 30
            img.save(path)
        else:
            one(tex, path)
        print(f"rendered {path.relative_to(ROOT)}")


def _png_size(data: bytes) -> tuple[int, int]:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")


# --------------------------------------------------------------------------- transform
def transform(deck: bytes) -> tuple[bytes, list[str]]:
    log: list[str] = []
    with zipfile.ZipFile(BytesIO(deck)) as zin:
        infos = {i.filename: i for i in zin.infolist()}
        parts = {name: zin.read(name) for name in infos}
    if f"ppt/slides/slide{NEW_PARTS[0]}.xml" in parts:
        return deck, log
    if hashlib.sha256(deck).hexdigest() != ORIGINAL_SHA256:
        raise RuntimeError("GAC-seminar.pptx is neither the pinned original nor this script's output")

    def get(name: str) -> str:
        return parts[name].decode("utf-8")

    def put(name: str, text: str) -> None:
        parts[name] = text.encode("utf-8")

    slide5 = parts["ppt/slides/slide5.xml"]

    # 1. text edits on existing slides
    for n, edits in T.items():
        name = f"ppt/slides/slide{n}.xml"
        xml = get(name)
        for shape_id, texts in edits.items():
            xml = set_paragraphs(xml, shape_id, texts)
        put(name, xml)
        log.append(f"slide{n}: {len(edits)} shapes rewritten")
    xml = get("ppt/slides/slide1.xml")
    xml = set_paragraphs(xml, 6, [TITLE_SLIDE_TITLE])
    put("ppt/slides/slide1.xml", set_font_size(xml, 6, 3600, 3000))

    # 2. tables
    put("ppt/slides/slide21.xml", set_table(get("ppt/slides/slide21.xml"), 22, TABLE_21))
    header = [("ID", None, None), ("Claim", None, None), ("Direct evidence", None, None), ("Verdict", None, None)]
    rows = [header] + [[(f"C{i}", None, None), (claim, None, None), (evidence, None, None), (verdict, colour, True, VERDICT_FILL[colour])]
                       for i, (claim, evidence, verdict, colour) in enumerate(CLAIMS, start=1)]
    put("ppt/slides/slide24.xml", set_table(get("ppt/slides/slide24.xml"), 25, rows))
    log.append("tables on slides 21 and 24 rewritten")

    # 3. equations
    for media, n, pic_id, max_w, fname, _ in EQUATIONS:
        data = (EQ_DIR / fname).read_bytes()
        w, h = _png_size(data)
        parts[media] = data
        name = f"ppt/slides/slide{n}.xml"
        put(name, set_picture(get(name), pic_id, w, h, max_w))
    log.append(f"{len(EQUATIONS)} equation images replaced")

    # 4. charts
    c2 = get("ppt/charts/chart2.xml")
    if c2.count(CHART2_RENAME[0]) != 1:
        raise RuntimeError("chart2 series name not found")
    put("ppt/charts/chart2.xml", c2.replace(*CHART2_RENAME))
    parts["ppt/embeddings/Microsoft_Excel_Worksheet1.xlsx"] = rename_in_workbook(
        parts["ppt/embeddings/Microsoft_Excel_Worksheet1.xlsx"], *CHART2_RENAME)
    put("ppt/charts/chart3.xml", rewrite_chart(get("ppt/charts/chart3.xml"), CHART3))
    parts["ppt/embeddings/Microsoft_Excel_Worksheet2.xlsx"] = rewrite_workbook(
        parts["ppt/embeddings/Microsoft_Excel_Worksheet2.xlsx"], CHART3)
    log.append("chart2 series renamed; chart3 and its workbook re-pointed to the cross-repository results")

    # 5. remove the portfolio slide
    pres, pres_rels = get("ppt/presentation.xml"), get("ppt/_rels/presentation.xml.rels")
    ctypes = get("[Content_Types].xml")
    rid22 = re.search(r'Id="(rId\d+)"[^>]*Target="slides/slide22\.xml"', pres_rels).group(1)
    pres = re.sub(rf'<p:sldId id="\d+" r:id="{rid22}"/>', "", pres)
    pres_rels = re.sub(rf'<Relationship Id="{rid22}"[^>]*/>', "", pres_rels)
    for name in REMOVED_PARTS:
        del parts[name]
        ctypes = re.sub(rf'<Override PartName="/{re.escape(name)}"[^>]*/>', "", ctypes)
    log.append("slide22 (portfolio pilot) and its chart, workbook, images, and notes removed")

    # 6. new slides on the slide-19 frame
    frame = get(f"ppt/slides/slide{CLONE_FROM}.xml")
    frame_rels = get(f"ppt/slides/_rels/slide{CLONE_FROM}.xml.rels")
    notes_frame = get(f"ppt/notesSlides/notesSlide{CLONE_FROM}.xml")
    notes_rels = get(f"ppt/notesSlides/_rels/notesSlide{CLONE_FROM}.xml.rels")
    next_id = max(int(x) for x in re.findall(r'<p:sldId id="(\d+)"', pres)) + 1
    for k, part in enumerate(NEW_PARTS):
        xml = frame
        for shape_id, texts in NEW_SLIDES[part].items():
            xml = set_paragraphs(xml, shape_id, texts)
        put(f"ppt/slides/slide{part}.xml", xml)
        put(f"ppt/slides/_rels/slide{part}.xml.rels",
            frame_rels.replace(f"notesSlide{CLONE_FROM}.xml", f"notesSlide{part}.xml"))
        put(f"ppt/notesSlides/notesSlide{part}.xml", notes_frame)
        put(f"ppt/notesSlides/_rels/notesSlide{part}.xml.rels",
            notes_rels.replace(f"slides/slide{CLONE_FROM}.xml", f"slides/slide{part}.xml"))
        ctypes = ctypes.replace(
            "</Types>",
            f'<Override PartName="/ppt/slides/slide{part}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
            f'<Override PartName="/ppt/notesSlides/notesSlide{part}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/>'
            "</Types>")
        rid = f"rIdGac{part}"
        pres_rels = pres_rels.replace(
            "</Relationships>",
            f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            f'Target="slides/slide{part}.xml"/></Relationships>')
        pres = pres.replace("</p:sldIdLst>", f'<p:sldId id="{next_id + k}" r:id="{rid}"/></p:sldIdLst>')
        log.append(f"slide{part} inserted on the slide{CLONE_FROM} frame")

    # 7. presentation order
    by_part = {int(t): rid for rid, t in re.findall(r'Id="(rId\w+)"[^>]*Target="slides/slide(\d+)\.xml"', pres_rels)}
    entries = {rid: m for m, rid in re.findall(r'(<p:sldId id="\d+" r:id="(rId\w+)"/>)', pres)}
    if sorted(by_part) != sorted(ORDER):
        raise RuntimeError(f"slide parts {sorted(by_part)} do not match the planned order")
    lst = "".join(entries[by_part[p]] for p in ORDER)
    pres = re.sub(r"<p:sldIdLst>.*?</p:sldIdLst>", f"<p:sldIdLst>{lst}</p:sldIdLst>", pres, flags=re.S)
    put("ppt/presentation.xml", pres)
    put("ppt/_rels/presentation.xml.rels", pres_rels)
    put("[Content_Types].xml", ctypes)
    app = get("docProps/app.xml")
    app = re.sub(r"<Slides>\d+</Slides>", f"<Slides>{len(ORDER)}</Slides>", app)
    app = re.sub(r"<Notes>\d+</Notes>", f"<Notes>{len(ORDER)}</Notes>", app)
    put("docProps/app.xml", app)

    # 8. page numbers and notes
    for position, part in enumerate(ORDER, start=1):
        name = f"ppt/slides/slide{part}.xml"
        xml = get(name)
        try:
            start, end = _shape(xml, 3)
        except KeyError:
            continue
        current = _text(xml[start:end]).strip()
        if current.isdigit() and current != str(position):
            put(name, set_paragraphs(xml, 3, [str(position)]))
    for part, text in NOTES.items():
        name = f"ppt/notesSlides/notesSlide{part}.xml"
        put(name, notes_with(get(name), text))
    log.append(f"page numbers follow the new order ({len(ORDER)} slides); {len(NOTES)} speaker notes rewritten")

    if parts["ppt/slides/slide5.xml"] != slide5:
        raise RuntimeError("slide5 changed; restyle_detailed_deck.py reads it as the divider frame")

    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, info in infos.items():
            if name in parts:
                zout.writestr(info, parts[name])
        for name in parts:
            if name not in infos:
                info = zipfile.ZipInfo(name, NEW_PART_DATE)
                info.compress_type = zipfile.ZIP_DEFLATED
                zout.writestr(info, parts[name])
    return out.getvalue(), log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="report the changes without writing the deck")
    parser.add_argument("--render-equations", action="store_true",
                        help="re-render the equation images with matplotlib before building")
    parser.add_argument("--deck", type=Path, default=DECK)
    args = parser.parse_args(argv)
    if args.render_equations:
        render_equations()
    original = args.deck.read_bytes()
    updated, log = transform(original)
    if not log:
        print("deck already current; nothing to do")
        return 0
    print("\n".join(log))
    if args.check:
        print(f"[check] {len(log)} changes pending; deck not written")
        return 0
    args.deck.write_bytes(updated)
    print(f"updated {args.deck} -> sha256 {hashlib.sha256(updated).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
