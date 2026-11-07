# AgentHop sealed baseline trace pilot

**Development decision: baseline competence passed; the tested dependent
binding families did not yield a GAC candidate. No matched GAC or superiority
claim follows.** The [protocol](../../supplementary/agenthop-baseline-pilot-protocol.md)
and [seal](seal.json) fixed 24 single-target depth-2 cases across distinct
path-overlap components, GPT-5.4 snapshot, official AgentHop harness, tool and
turn limits, a 17/24 engineering competence threshold, and the shared $300
campaign ledger before provider calls. This is an internal development cohort
from a public, source-overlapping benchmark.

## What ran

The unchanged baseline used the official AgentHop prompt, seven-tool sandbox,
Responses continuation and exact A/B/C/D grader. Its only transport change was
the fail-closed shared-ledger wrapper. All 24 scheduled cases completed; 23
submitted an answer and one exhausted the official tool budget. **19/24** were
exactly correct, exceeding the prespecified **17/24** engineering gate. The
retained [report](report.json) records every case and provider request count.
The independent [audit](audit.json) regraded all 24 predictions against the
pinned public QA file, verified all 24 protected raw-trace hashes and reconciled
the [sanitized provider ledger snapshot](ledger_snapshot.json): **180 requests**, **$5.800413125** conservative accounted
study cost. The full campaign accounted upper total is **$12.101101325**,
leaving **$287.898898675** under the authorized cap. These are upper estimates,
not invoices, and exclude local compute and engineering time. No GAC arm,
handwritten arm, calibration or independent test was run.

The raw conversations and paper sections stay in a local ignored cache. The
public observations retain tool names and safe navigation arguments, omit
paper text/model reasoning, and bind each raw trace by SHA-256. Reproducing the
raw-trace hash checks requires that local cache; source, answer and ledger
checks can be rerun from the pinned public dataset and retained audit code.

## What the traces say about a candidate

The [posthoc binding audit](binding_feasibility.json) covers all 24 cases and
uses no gold, annotated bridge or correct-answer metadata to construct a
candidate. Every baseline already requested seed metadata and references in
its **first model turn**; 15 also requested seed sections in that same turn.
Pre-executing this opening batch could remove **at most that one provider
request**, not one request per tool call. An exact handwritten prefetch can
make the same substitution. This recurrent prefix alone therefore does not
establish GAC superiority over the relevant simple control.

The first non-seed paper was selected after seed references in all 24 cases.
In 21 cases, it came from those references; the official `get_references`
output matched the retained trace prefix in all 21. The chosen paper appeared
at reference positions **3–25** rather than at a stable location. GAC's
closed binding synthesizer found **no consistent expression** from the exact
model-visible reference text plus entry question/options/seed to the selected
paper ID across the 21 cases. It also found none in each opening-batch
subfamily with support of at least five (supports 7, 9 and 5). A diagnostic
structured-reference representation also failed; that representation is not
the deployed tool format. Three first non-seed choices followed other routes.

After that first paper choice, 20/24 immediate same-paper follow-up calls were
already in the same model turn. Four occurred later, below the tested
five-case support floor. The current shipped GAC compiler has `prefix_only`
enabled because the runtime has no verified mid-trajectory region-position
key. Thus a later adaptive read cannot simply be moved to the start without
changing semantics. The tested bridge-selection family yields **no qualifying
derived multi-step candidate** and no basis for paid matched GAC arms yet.

This audit is not an exhaustive search over all later tool patterns, learned
semantic selectors or future method extensions. A missing binding here does
not prove that no possible compiler can work. A new semantic selector or safe
mid-trajectory dispatch would be a material method change. It would need to
be derived from separate training traces, charged for discovery, checked on
grouped refits and live tools, and compared with the same selector in a
handwritten or simpler compiler arm. It must not be introduced as an
outcome-selected rescue on these 24 exposed cases.

## Reproduction and publication boundary

Run the pinned source audit first, then use the published scripts with the
public AgentHop QA, graph and paper-pool files and official code revision
named in the seal. A full re-execution requires provider access and is a new
stochastic experiment, not a deterministic regeneration of these trajectories.
The provider-free grade and binding audits require the protected raw traces
at `--raw-dir`; the publication validator checks the retained aggregate and
hash relationships without downloading benchmark files or invoking a model.

The manuscript's numerical claims and PDF are unchanged. This development
result supports only that the baseline is competent on its selected cases and
that the tested GAC binding opportunity failed. It does not establish
population accuracy, source independence, noninferiority, a quality–cost
frontier or GAC superiority.
