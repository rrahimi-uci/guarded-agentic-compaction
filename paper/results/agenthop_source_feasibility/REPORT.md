# AgentHop source and adaptive-task feasibility

**Decision: go for a bounded development pilot; no confirmatory GAC claim.**
AgentHop's single-target, depth-2 citation questions are the strongest open
benchmark lead found after the BIRD, AppWorld, Reddit, NESTFUL, BFCL, AgentBench
and VAKRA screens. The [official code](https://github.com/JohnnyNLP/agenthop)
provides a local seven-tool citation-graph sandbox, and the
[dataset](https://huggingface.co/datasets/nlpai-lab/agenthop) includes exact
A/B/C/D answers and 1,011 public questions. The [paper](https://arxiv.org/pdf/2609.34428)
reports a 78.0% GPT-5.3 Codex baseline on the selected subtype. That published
score is motivation for a *new local baseline-competence test*, not a measured
result for our model or adapter.

The [machine-readable preflight](report.json) pins code commit
`419407e1b06f95f6baa0a6d2c12da43fc53045c2` and dataset revision
`24e7076425ead02de2f858d8963846dc981ef9e3`. It verifies exact file hashes
before counting, including the released paper pool and official loader. All
7,205 paper-pool records have section text; the seed, annotated bridge and
gold paper in all 478 selected cases have pool content. The 478 selected
single-target, depth-2 questions have 478 distinct seed papers. For 476/478,
the released graph exposes at least one
seed → annotated bridge → gold paper path. In two cases (`st_0092`,
`st_0310`), the annotated bridge is not returned by the seed's reference
list, although the gold and bridge nodes exist. Those cases remain in any
fixed denominator; this audit does not quietly discard them.
In a provider-free smoke check on `st_0001`, the official `AgentHopTools`
returned the seed-to-bridge references, bridge-to-gold references and the
gold paper's section list from the pinned release. This checks local tool
availability only; no answer was generated or graded.

## Independence and source overlap

Distinct seed papers are not sufficient for an independence claim. Connecting
questions that share a seed, annotated bridge or gold paper yields 280
path-overlap components; the largest contains 25 questions. Connecting
questions that share **any** paper in their full two-hop neighborhoods yields
one full-neighborhood component containing all 478 questions. The 478 graphs
include 149,769 paper memberships over 28,382 distinct paper IDs. Thus even
path-disjoint splits share a background paper corpus. Path-overlap components
are a possible sensitivity unit, not proven statistically independent groups.
Fully source-disjoint calibration and test groups cannot be claimed on this
cohort. Any later risk certificate must either justify the weaker group unit
and report dependence sensitivity or use a separate source population.
All questions and answers are publicly released. A preassigned internal test
partition can prevent experiment-time tuning, but cannot establish that the
model never saw benchmark content during training.

## Required next gate

The official release includes a trajectory-writing harness but no baseline
agent trajectories for this study. This preflight made **zero provider calls**,
observed zero agent traces, derived zero GAC candidates, admitted no artifacts,
and scored no calibration or test groups. It establishes source feasibility,
not useful compaction or comparative quality.

Before spending on matched arms, seal a small train-only baseline-competence
pilot under the shared $300 cap. The candidate must be mined from actual
baseline tool trajectories. In particular, a proposed multi-step program
must bind each dynamic paper ID or section from permitted entry fields or
earlier tool results, without using `gold_paper_ids`, `bridge_paper_ids`,
`correct_index`, recall labels or other answer metadata at runtime. A fixed
`get_paper_info(seed)` plus `get_references(seed)` prefetch would be two
independent reads and would not satisfy the state-dependent-value gate.

If a useful prefix survives source-effect, grouped refitting, live-tool and
continuation-parity checks, freeze the exact handwritten wrapper, simpler
recurrence compiler and unchanged-agent controls before outcomes. Then
prespecify calibration groups, candidate/threshold multiplicity, a quality
margin, a cost endpoint and a power calculation from pilot discordance.
Because only 280 path-overlap components exist, this single subtype cannot
establish a small effect with the earlier 12-family plan. A null or failed
development gate is a no-go, not a reason to tune on test results.

## Reproduction and scope

The source audit reads the public QA, graph and paper-pool JSONL files and the
official code checkout; it does not mirror the large graph file or paper text
into this repository. Download the pinned `qa/full.jsonl`, `graphs/full.jsonl`
and `paper_pool/papers.jsonl`
from the stated dataset revision and check out the pinned code commit. Then:

```sh
python paper/scripts/agenthop_source_feasibility.py \
  --qa /path/to/qa/full.jsonl \
  --graphs /path/to/graphs/full.jsonl \
  --papers /path/to/paper_pool/papers.jsonl \
  --code-root /path/to/agenthop
python paper/scripts/validate_artifacts.py --families agenthop_source_feasibility
```

The script refuses source drift and regenerates the report deterministically.
The publication validator checks its pinned hashes, denominators and claim
boundary without fetching external files in CI. A full source recount needs
the three pinned external files. No model, prompt, answer, database or key is
published by this preflight.
