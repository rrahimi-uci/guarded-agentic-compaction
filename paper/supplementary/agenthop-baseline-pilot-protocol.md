# AgentHop baseline trace pilot protocol

Status: prospective development gate. The machine-readable `seal.json` is
written before provider calls, then checked by the runner. This protocol does
not claim GAC superiority or a native AgentHop leaderboard score.

## Purpose and fixed cohort

The immediate question is whether a competent baseline on AgentHop's
single-target depth-2 citation tasks yields a recurring **dependent**
multi-step read program that GAC can derive from traces. The 478-item public
subtype has 280 components under shared seed, annotated bridge or gold paper;
all 478 connect under full citation-neighborhood overlap. These dependence
facts come from the pinned [source audit](../results/agenthop_source_feasibility/REPORT.md).

Before looking at any model outcome, hash the sorted IDs of each path-overlap
component with the fixed `gac-agenthop-st2-baseline-pilot-v1` salt; take the
24 lowest-hash components and one lowest-hash ID from each. Use seed, bridge
and gold IDs only to form components, never as model input or candidate
arguments. All 24 scheduled cases remain in the denominator. This is an
internal development partition from a fully public benchmark; it is neither
source-disjoint nor a contamination-free independent test.

## Baseline and accounting

Run the pinned official AgentHop harness, prompt, seven-tool sandbox and
multiple-choice grader with GPT-5.4 snapshot `gpt-5.4-2026-03-05`, Responses
API, medium reasoning, direct strategy, 30-point tool budget, 20-turn limit,
16,384 output tokens per turn and 200,000 cumulative tokens per case. Replace
only the official provider transport with a ledgered client that sends the
same requests plus explicit storage and service-tier settings. The official
Responses continuation uses `previous_response_id`; storage is enabled to
preserve that semantics. The model sees the official seed, question, options,
tools and observations. The local code reads gold labels only for selecting
path-overlap groups and exact grading.

The [official GPT-5.4 model page](https://developers.openai.com/api/docs/models/gpt-5.4)
lists $2.50/M input and $15/M output. The ledger charges a conservative
$3.125/M input and $15/M output upper estimate, with no cache discount.
Each request reserves a 200,000-input-token bound and the fixed output cap.
The existing cross-study $300 campaign ledger and $30 pilot-stage cap remain
binding. The ledger is never reset. Unknown usage retains the reservation;
usage exceeding the bound stops the campaign. This is an accounting estimate,
not an invoice or a measure of engineering/compute time.

Raw conversations and paper text stay in an ignored local trace directory.
Public observations retain task IDs, exact correctness, termination, costs,
tool names and safe navigation arguments, plus a SHA-256 of each raw trace;
they omit questions, paper text, model reasoning and credentials. Every
provider failure, incomplete outcome and scheduled case must be retained.
There is no outcome-based rerun or case substitution.

## Decision rules

The baseline competence engineering gate is at least **17/24** exact correct
answers. This threshold is not a hypothesis test, confidence bound or a claim
about the model's population accuracy. A failure blocks matched GAC spending
on this benchmark and is reported as a negative result.

If the gate passes, audit the *actual baseline traces* for a recurrent prefix
with at least two nontrivial read/navigation calls where a later argument is
uniquely derived from permitted entry state or an earlier tool result. Merely
seeing a paper ID among many references is not a unique selector. Two
independent seed reads are not a qualifying dependent program. Exclude
`gold_paper_ids`, `bridge_paper_ids`, `correct_index`, recall labels and answer
metadata from candidate construction. Report all observed prefix families and
their support, including no candidate or rejected candidates. Before any
matched run, require source-effect, grouped-refit, live-tool and
continuation-parity checks. Freeze exact handwritten, simpler compiler and
unchanged-agent controls, all-task denominator, outcomes and cost endpoints.

This pilot cannot itself establish GAC quality–cost superiority, statistical
noninferiority or a selective-risk certificate. The full-neighborhood overlap
and public-label exposure remain limitations even if a useful candidate is
found. A confirmation design needs a justified sampling unit, dependence
sensitivity, pilot discordance, prespecified power and a separate holdout.
