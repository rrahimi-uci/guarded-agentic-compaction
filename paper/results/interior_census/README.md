# Interior-region census over released agent trajectories (P0 of `gac-expansion.md`)

Provider-free trace analysis answering the expansion plan's first registered hypothesis (H1):
do released agent trajectories contain recurring, groundable, read-only regions at **non-initial**
model boundaries, beyond the point where the paper's prefix-only compiler stops? The protocol was
registered before any count was computed
(`paper/supplementary/interior-region-census-protocol.md`; its SHA-256 is recorded in
`results.json` under `protocol`). `results.json` is produced by
`paper/scripts/interior_census.py run`, `smoke.json` by its `smoke` command, and
`paper/iclr/tables/interior_census.tex` by its `table` command, and `decomposition.json` by its
post-hoc `decompose` command; the artifact validator checks that the table regenerates
byte-identically from the JSON and that the decomposition reproduces the registered tau-bench count. The table is **not** included in the
ICLR submission: it is evidence for the expansion plan, not for a claim in the paper.

The corpora, catalogs, mining parameters (`max_depth=2`, `kappa=3`, `w_min=2`, `w_max=12`,
`b_min=2`, entry schema `inputs`) and grounding rule are those of the prefix census
(`paper/results/prefix_census/`). Two things change: up to 60 calls per trajectory are ingested
with no catalog-barrier stop, and windows may start at any model boundary. Definitions are
written into `results.json` (`definitions`).

## Verdict

| Corpus (primary arm) | Traces | Groups | Beyond-frontier groundable share, strict | …projected | Largest beyond-frontier family (groups) | H1 (share ≥ 0.20 and n_max ≥ 92, projected) |
|---|---:|---:|---:|---:|---:|---|
| OpenHands / SWE-rebench (1-in-4 hash sample) | 16,711 | 5,797 | 72.7% | 72.7% | 4,345 | **pass** |
| SWE-agent (nebius, whole corpus) | 80,036 | 3,591 | 12.3% | 12.3% | 1,713 | fail (share) |
| tau-bench historical runs (whole corpus) | 1,980 | 165 | 3.8% | 66.0% | 96 | **pass** |

`h1_verdict.any_corpus_passes` is `true`. The sensitivity arms (shell reads admitted for the two
coding corpora; pre-tool user turns folded for tau-bench) do not change any verdict
(74.1% / 4,343; 10.6% / 1,482; 45.6% / 95).

H1 therefore passes by its pre-registered criterion. The paragraphs below say what the regions
are, because the two passes are of different kinds and the second is weaker than the number
suggests. The frontier and distance counts below come from the post-hoc decomposition
(`decomposition.json`, next section); the description of what the families contain comes from
inspecting windows on hash subsamples, which is not a count.

## What the regions are

**tau-bench: the motivating case, and only under projection.** The prefix frontier is the
`HANDOFF` to the user at the start of nearly every conversation (498/500 inspected), so the
whole tool-using part of the trajectory is beyond it. The dominant families are
`get_order_details` repeated two, three or four times with a single live-in `prior:get_user_details`:
the agent looks the customer up once, then fetches each order listed in the customer record.
Under the strict policy these windows are blocked (`live_in_not_in_entry_schema`, 3,631
candidates) and the groundable share is 3.8%; under the projected policy it is 66.0%. The largest
family has support 96 of 165 tasks against a floor of 92, a margin of four groups (95 in the
folded arm). The regions are short (median 3 removed requests) and start early (median at the
third call).

**OpenHands: a large part of the pass is a frontier artifact; a real interior remainder stays.**
The frontier is the `think` tool at call 0 in 3,686 of 4,197 trajectories of the decomposition
sample (87.8%; catalogued `PURE`, no capabilities: its only effect is on the model's own context,
which a compiled program does not have). Almost every trajectory is therefore "beyond the
frontier" from its second call, and 64.4% of the best beyond-frontier regions start with the call
right after the frontier (`start_call_index` median 1.0 in the full run). The families are runs of
`str_replace_editor.view` whose paths ground to the entry state (`z.inputs`): README, package
directories, test directories of the repository named in the task. When `PURE` calls are not
allowed to end the opening (post-hoc decomposition below), the frontier moves to the first
`execute_bash` at call 2 to 5 and the beyond-frontier groundable share falls from 73.2% to 45.7%:
1,153 of 3,071 regions (37.5% of the pass, 27.5 share points) are the opening minus `think`. The
remaining 45.7% of trajectories have a groundable `view` run after the first shell command, with
start index 6 or later in most cases, and the largest such family still has support 1,511 groups,
so OpenHands passes H1 under the pass-through frontier as well. The strict and projected shares
are identical because no candidate window had a prior-result live-in: slots fed from
unstructured text observations are `UNGROUNDED` (69,639 candidates blocked for that reason, 636,037
for an unknown effect, mostly `execute_bash`).

**SWE-agent: fails, and the surviving families are trivial.** The frontier is `create` or `edit`
in 307 of 400 inspected trajectories and a raw shell command in most of the rest; interior
read-only runs of at least two calls exist in 60.0% of trajectories, but only 12.3% have a
groundable one. The largest families are argument-free `scroll_down` runs (support 1,713, 1,165,
877 groups) and `scroll_up`; they are compilable in principle (prefetch the next pages of the
open file) and remove two to five requests, but they carry no grounding content. As on
OpenHands, projected equals strict: 1,396,837 candidates are blocked by an ungrounded slot, so the
projection has nothing to admit. Share 12.3% < 0.20; H1 fails.

## Frontier decomposition (post hoc, descriptive)

Added after `results.json` was read, under `paper/supplementary/interior-region-census-decomposition.md`;
it does not decide H1 and the registered protocol is unchanged. Projected policy, primary catalog,
hash subsample `K` = 1 (tau-bench), 16 (OpenHands), 64 (SWE-agent). On tau-bench the registered
frontier reproduces the census count exactly (1,306 of 1,980).

| Corpus | Traces | Frontier event (share) | Registered frontier: share, n_max | Best region starts right after the frontier | `PURE` pass-through frontier: share, n_max | Attributable to `PURE` calls |
|---|---:|---|---:|---:|---:|---:|
| tau-bench | 1,980 | `HANDOFF` 99.7% | 66.0%, 96 | 19.4% | 66.0%, 96 | 0 traces |
| SWE-agent | 1,242 | `create` 51.2%, `edit` 27.2%, `shell.ls` 15.6% | 13.7%, 93 | 3.5% | 13.7%, 93 | 0 traces |
| OpenHands | 4,197 | `think` 87.8%, `shell.exec` 11.4% | 73.2%, 1,891 | 64.4% | 45.7%, 1,511 | 1,153 traces (27.5 points) |

Reading: the `PURE` pass-through changes nothing on tau-bench or SWE-agent, whose frontiers are a
user hand-off and a write respectively. On OpenHands it removes 37.5% of the registered pass; the
rest is interior in the intended sense (a read-only run after a shell command), though of the same
kind, `view` runs grounded to the task's entry inputs. The SWE-agent sample share (13.7%) is
consistent with the full-corpus 12.3%, and its in-sample `n_max` of 93 is the `scroll_down` pair.

## Reading the numbers

- A **family** is a canonical window hash with values held (tool sequence, slot marks, edge
  topology, live-in shape, boundary count). It does not fix a selector or a path, so a single
  compiled program's support is at most the family's support; the floor comparison is an upper
  bound on what admission could certify.
- **Groups** are tasks (tau-bench task ids; SWE instances). tau-bench has 12 trajectories per
  task (two models, three or four trials), so 1,306 trajectories with a region correspond to at
  most 165 tasks and the family support of 96 is in tasks.
- **Removed requests** count the model boundaries inside a window; nothing is priced.
- **Truncation.** 8,810 of 16,711 OpenHands and 5,522 of 80,036 SWE-agent trajectories exceed
  60 calls and were truncated (`ingestion.stopped_by`); interior regions beyond call 60 are not
  seen. tau-bench trajectories are complete (maximum 27 calls).
- **Sampling.** The divisors were fixed by the registered rule from `smoke.json` before any
  interior count was read: tau-bench and SWE-agent `k=1`, OpenHands `k=4` (16,711 of 67,074
  trajectories; expected 16,768). The smoke estimate undershot the realized runtime: the full run
  took 3.1 h (tau-bench 25 s and 29 s per arm, SWE-agent 2,338 s per arm, OpenHands 3,275 s and
  3,319 s per arm) against a 90-minute budget per arm, because the first 200 trajectories of each
  corpus are shorter than average and window enumeration grows with trajectory length. The rule
  was not revised after the fact.

## Implication for `gac-expansion.md` §16

H1 passes, so path C (interior reuse) is not ruled out by prevalence. The evidence that supports
it is narrower than the pass rate: the clean case is a conversational agent over a structured
API (tau-bench), where the region "fetch every record the previous lookup listed" recurs across
96 tasks and is reachable only with boundary-local projection of a prior result. On coding
agents the projection buys nothing because observations are text; about three eighths of the
OpenHands pass is a consequence of one `PURE` model-side call at the start of every trajectory,
and the rest is entry-grounded `view` runs after a shell command. A
mechanism paper on interior reuse should therefore (i) be built around structured-API workloads
or around a grounding rule for text observations, which does not exist yet, and (ii) report the
`think`-frontier decomposition explicitly rather than the aggregate share. P1 (the matched
compiler comparison) can proceed; P2 (interior read regions) should be scoped to the tau-bench
pattern first.

## What this census cannot show

Prevalence in deployed (non-benchmark) agents; that any region is admissible (nothing is
synthesized, replayed, calibrated or dispatched); that the continuation after a compiled
interior region would be unchanged; or that the groundable share translates into savings.

## Reproduction

```
python paper/scripts/interior_census.py smoke --source-root <dir> --corpora taubench,openhands,sweagent
python paper/scripts/interior_census.py run   --source-root <dir> --corpora taubench,sweagent,openhands
python paper/scripts/interior_census.py table
python paper/scripts/interior_census.py decompose --source-root <dir> --corpora taubench,sweagent,openhands
python -m pytest paper/scripts/test_interior_census.py -q
```

`<dir>` holds the three corpora at the revisions pinned in
`paper/results/datasets/{openhands,sweagent,taubench}/source_manifest.json`; every file is
verified by SHA-256 before parsing. The raw corpora are not committed.
