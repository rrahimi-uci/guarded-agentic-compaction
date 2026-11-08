# Expansion-plan evidence, synthesized for a path-A resubmission

**Status: draft written 2026-11-08 from retained results only. Nothing here is in the ICLR 2027
submission or its rebuttal; nothing here is to be posted during the discussion window.** It
assembles the three studies run against `gac-expansion.md` (P0 census, P1-lite funnel, the
funnel's live pilot) into the section a strengthened resubmission (path A of §16) would carry,
states what each result does and does not support, and fixes the design arithmetic for the
experiments that would still be needed. Every number is traceable to a file named in §6.

## 1. One-paragraph summary

The expansion plan asked four questions. **H1 (headroom beyond the prefix)** passes by its
registered criterion on two of three released corpora, but the clean case is one pattern on one
structured-API workload (tau-bench, support 96 tasks against a floor of 92), and 37.5% of the
OpenHands pass is an artifact of where a model-side `think` call places the prefix frontier.
**H3 (admission value)** has a compile-time answer on all thirteen retained GitHub cohorts:
statistical admission never changed a decision, and grounding changed one, the issue-type
three-read candidate; that refusal cost one request per episode and prevented no replay-visible
error. **The live pilot** that followed the one divergence found it does not recur on fresh
issues: with all 16 training traces agreeing on `limit = 100`, GAC admitted the same three-read
program as the recurrence-only policy, dispatched it on 65/65 held-out issues at one request
each, and the unguarded replay of the identical program met the contract on 63/65 (two excerpt
paraphrases; exact McNemar p = 0.50). **H2 (automation beyond hand-writing) and H4 (external
compiler)** remain unmeasured: no runnable external compiler exists, and no adaptive workload
has yet been compiled. The honest resubmission framing is therefore unchanged from the
rebuttal: safe automation of the program a person would write, with the compiler's refusals and
admissions now shown to be reproducible, mechanically attributable, and, on these workloads,
inexpensive.

## 2. What was run (chronological, all pre-registered or sealed before data)

| Study | Protocol (sealed before data) | Provider spend | Result file |
|---|---|---:|---|
| P0 interior-region census over OpenHands, SWE-agent, tau-bench | `interior-region-census-protocol.md` | $0 | `paper/results/interior_census/results.json` |
| P0 post-hoc frontier decomposition (descriptive) | `interior-region-census-decomposition.md` (post hoc, labelled) | $0 | `paper/results/interior_census/decomposition.json` |
| P1-lite same-IR compiler funnel, 13 retained GitHub cohorts | `compiler-funnel-protocol.md` | $0 | `paper/results/compiler_funnel/results.json` |
| Live pilot of the funnel's divergence on 193 fresh issues | `compiler-funnel-live-pilot-protocol.md` | $0.23 | `paper/results/compiler_funnel_pilot/results.json` |

## 3. Findings, with the limits that go with them

### 3.1 H1: interior headroom exists, narrowly

Registered criterion: a corpus passes if at least 20% of trajectories contain a groundable
read-only region of two or more calls beyond the prefix frontier **and** some family is supported
by at least 92 independent groups (the gate's zero-violation floor). Projected live-in policy
(a region may read a prior result at its boundary).

| Corpus | Traces | Groups | Beyond-frontier groundable share (strict / projected) | Largest family support | H1 |
|---|---:|---:|---:|---:|---|
| OpenHands / SWE-rebench (1-in-4 sample) | 16,711 | 5,797 | 72.7% / 72.7% | 4,345 | pass |
| SWE-agent (whole corpus) | 80,036 | 3,591 | 12.3% / 12.3% | 1,713 | fail (share) |
| tau-bench (whole corpus) | 1,980 | 165 | 3.8% / 66.0% | 96 | pass |

What the passes are:

- **tau-bench** is the motivating case and the only one that needs the interior machinery:
  after the user hand-off that ends nearly every prefix, the agent looks a customer up once and
  then fetches each order the customer record lists. The region is reachable only with
  boundary-local projection of a prior result (strict share 3.8%). Its largest family has
  support 96 tasks against the floor of 92: a margin of four. The regions are short (median
  three removed requests).
- **OpenHands** passes mainly because the first call of 87.8% of trajectories is `think`, a
  `PURE` model-side call that ends the registered prefix at call 0. Letting `PURE` calls pass
  through moves the frontier and drops the beyond-frontier share from 73.2% to 45.7% on the
  decomposition sample (1,153 of 4,197 trajectories, 27.5 points, attributable); the remainder
  still passes (n_max 1,511) but is the same kind of region the prefix census already described,
  `view` runs grounded to the task's entry inputs, starting right after a shell command.
- **SWE-agent** fails; its surviving families are argument-free `scroll_down` runs.

Limits: a family is an upper bound on a compiled program's support; nothing was synthesized,
replayed, calibrated or dispatched; trajectories over 60 calls were truncated (8,810 OpenHands,
5,522 SWE-agent); benchmark traces, not deployed agents.

**For path A:** the census is a scope result. It says where a future interior compiler would
have something to compile (structured-API agents) and where it would not (coding agents whose
observations are text), and it is the honest answer to "why only prefixes".

### 3.2 H3 at compile time: the funnel

Four policies through the shipped compiler on identical splits, manifests and catalogs:
GAC; support-only (alpha = 1, every candidate with support admitted); recurrence-only (grounding
off, an ungroundable slot bound to its modal training literal; no verifier content changes);
stats-only. The GAC policy reproduced every retained decision (same artifact id, same rejection
stages) on all 13 cohorts.

- **Statistical admission never changed a decision.** Support-only admits exactly what GAC admits
  on every cohort. This is the compile-time twin of the runtime null in the generalization-gate
  appendix (identical routing on 2,724 record/model cases): with 92 clean calibration groups per
  candidate the gate admits at full coverage and the support floor already decides.
- **Grounding changed one decision in thirteen.** On the retained issue-type traces GAC refused
  the three-read candidate whose `issue_get_comments.limit` had no witness (15 of 16 training
  windows used 100, one used 1). The grounding-off policies admit it with `limit = Const(100)`;
  replayed on the 92 calibration groups it has 0 violations and 1 unproductive sample (the one
  `limit = 1` run is a recording miss). So the refusal cost one removed request per episode and
  prevented no replay-visible error, consistent with the 30-record live ablation (Table
  `tab:recurrence-only`).
- **PR-outcome, backlog and the ten repositories are nulls by construction:** every slot of the
  mined three-read window is grounded, so no policy can differ there.

Limits: same-IR policies only (TraceCompiler has no runnable artifact,
`paper/results/tracecompiler_screen/REPORT.md`); mining is shared, so a recurrence-only *miner*
was not tested; replay cannot price the live effect of a different evidence set.

### 3.3 The live pilot: the divergence is split-dependent, and the guards cost nothing measurable

Sealed design on the post-cutoff `huggingface/datasets` pool (277 issues, 197 with a comment,
193 after exclusions): 128 discovery issues run by the unchanged agent, GAC recompiled from them
with the retained configuration, the four funnel policies re-run on the same traces, then three
arms paired on the disjoint 65 test issues in a balanced Latin order.

- Discovery: 128/128 completed, 127 exact and eligible; every trace used the same three reads;
  124 asked `limit = 100`, 4 asked `limit = 1`.
- Compile: the 16 training groups all carried `limit = 100`, so GAC bound `limit = Const(100)`
  and **admitted the three-read program itself** (gate 92 groups, 0 violations, bound 0.0498; the
  four `limit = 1` traces sat in dev and calibration as recording misses). All four policies
  agree; the divergence of §3.2 did not recur. The retained refusal hinged on one divergent trace
  landing in a 16-trace train split, which is what grounding is specified to do with an
  unwitnessed literal, but it is not a property of the workload.
- Test (65 pairs, 195 episodes, no retries):

| Arm | Exact | Requests | Tokens | Latency | Cost |
|---|---:|---:|---:|---:|---:|
| GAC three-read, guarded (dispatched 65/65) | 65/65 | 1.00 | 1,609 | 1.78 s | 0.052¢ |
| Recurrence-only replay of the same program, unguarded | 63/65 | 1.00 | 1,308 | 1.85 s | 0.043¢ |
| Unchanged agent | 64/65 | 4.00 | 4,618 | 4.90 s | 0.087¢ |

Every miss (baseline 7624; replay 7990, 8048) is an `evidence_excerpt` paraphrase or corrupted
quotation with all other fields exact. No arm produced a wrong or missing read, so no miss is a
violation a guard or verifier would have caught; the two compiled arms also differ in how the
evidence reaches the model (SDK tool results versus a JSON block in the user turn), which
confounds any attribution. Versus the unchanged agent both compiled arms remove 75% of requests;
GAC cuts tokens 65% and cost 41%, the replay 72% and 51%.

Limits: 65 pairs detect a comparator miss rate of about 12% at 80% power (§5); the pilot measured
guard overhead on an identical program, not the retained refusal; cost is list-price arithmetic.

### 3.4 What remains unmeasured

- **H2** (a compiled program a person would not write first) has not been tested on any
  workload; on every GitHub family the hand-written bundle matches GAC.
- **H4** (external compiler) cannot be run; the same-IR funnel is the substitute and the paper
  must say no external compiler was run.
- **H3 at runtime** on a candidate GAC retires and a simpler compiler deploys: the only such
  candidate in the retained cohorts ran clean under replay and, when the divergence vanished on
  fresh data, could not be force-run as a *retired* candidate at all.

## 4. Recommended framing for the resubmission

1. Keep the claim the rebuttal already makes: GAC automates, under explicit guards and a
   finite-sample bound on the violation rate, the read-only program a person would write by hand,
   and it refuses what it cannot ground. Do not claim a measured safety benefit over a
   recurrence-only compiler; the data show none on these workloads.
2. Add the funnel as the attribution evidence reviewers R1 and R2 asked for: a four-policy
   decomposition on thirteen cohorts, with the one divergence traced to a single training trace
   and shown, live, to be split-dependent and inexpensive either way. This is a stronger answer
   than a missing comparison, and it is honest about being a null for the gate.
3. Report the census as the scope section: where interior reuse exists (structured-API agents,
   one pattern, support just above the floor) and where it does not (coding agents), with the
   `think`-frontier decomposition stated, not the aggregate share.
4. State the arithmetic of §5 when discussing sample sizes, so that "92 groups" and "65 pairs"
   are read against what they can and cannot detect.
5. Drop learned-gate claims entirely (already done in the rebuttal); the funnel confirms that on
   these cohorts the support floor decides.

## 5. Design arithmetic for what would still be needed

Generated by `paper/scripts/expansion_power_table.py` into
`paper/results/expansion_synthesis/power.json` and `paper/iclr/tables/expansion_power.tex`,
using the compiler's own Clopper-Pearson helper.

| Admission rule (alpha = 0.05) | k = 0 | k = 1 | k = 2 | k = 3 | k = 4 |
|---|---:|---:|---:|---:|---:|
| Registered grid (delta = 0.10 over 11 thresholds) | 92 | 133 | 168 | 200 | 231 |
| Single rule, one-sided 90% (end-to-end certificates) | 45 | 77 | 105 | 132 | 158 |
| Single rule, one-sided 95% | 59 | 93 | 124 | 153 | 181 |

| Paired pilot, pairs | 30 | 65 | 100 | 150 | 200 | 300 | 500 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Smallest comparator miss rate detectable at 80% power (GAC arm clean) | 25.1% | 11.9% | 7.8% | 5.2% | 3.9% | 2.6% | 1.6% |

Forced runs of one retired candidate needed to observe a violation with 95% probability: 299 at
a true rate of 1%, 149 at 2%, 59 at 5%, 29 at 10%. These detect a rate; they do not certify one.

Reading: the 30-record ablation could only have seen a comparator that misses a quarter of the
time; the 65-pair pilot, about one in eight. A pilot that could see a 5% miss rate needs about
150 pairs; at the pilot's cost class (0.0004 to 0.0009 USD per episode) that is under $1 of
provider spend, so the binding constraint on these GitHub families is fresh independent groups,
not money. For H3 on a genuinely retired candidate the first requirement is a candidate GAC
retires and a simpler compiler admits on a workload where the two can be run live; the retained
cohorts no longer contain one.

## 6. Sources

- Census: `paper/results/interior_census/{results.json,decomposition.json,README.md}`,
  `paper/iclr/tables/interior_census.tex`, protocol and post-hoc note under `paper/supplementary/`.
- Funnel: `paper/results/compiler_funnel/{results.json,README.md}`,
  `paper/iclr/tables/compiler_funnel.tex`, `compiler-funnel-protocol.md`.
- Pilot: `paper/results/compiler_funnel_pilot/{preflight.json,discovery_checkpoint.json,compile.json,test_checkpoint.json,results.json,ledger.json,README.md}`,
  `paper/iclr/tables/compiler_funnel_pilot.tex`, `compiler-funnel-live-pilot-protocol.md`.
- Arithmetic: `paper/results/expansion_synthesis/power.json`, `paper/iclr/tables/expansion_power.tex`.
- Plan and hypotheses: `gac-expansion.md` §0, §10, §11, §16; rebuttal strategy: `flip-plans.md`.
- A LaTeX draft of this section for the resubmission, not input by the ICLR build, is
  `paper/iclr/sections/expansion_evidence_draft.tex`.
