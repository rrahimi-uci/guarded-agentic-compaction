# Common authenticated entry: validated controls, no confirmatory result

All **60 provider-free checks passed** on the same fixed 12 exposed AppWorld training
scenarios. This removes an entry/grading feasibility blocker for a redesigned
baseline pilot. It does not establish model competence, automatic compilation,
comparative benefit or a statistical certificate.

| Check | Passing / scheduled | What it establishes |
|---|---:|---|
| Known-correct public reference calls after common setup | 12/12 | Official grading can recognize a correct task execution through this direct-call path |
| Empty interaction | 12/12 | Setup alone does not satisfy these tasks |
| Unsupported completion | 12/12 | Claiming completion alone does not satisfy these tasks |
| First two song-library pages | 12/12 | List responses and unchanged saved DB bytes on these probes |
| First two playlist-library pages | 12/12 | List responses and unchanged saved DB bytes on these probes |

Every control performs the same initialization rule: two actual supervisor reads,
then login to all nine public apps in sorted order. That is **11 setup API calls**
per execution; every future arm must receive the same information and pay the same
setup cost. For all 12 tasks, initialization outputs and saved entry-state hashes
are identical across all five control modes; those hashes are published in the report. Login remains a write, including credential issuance. It is not admitted
into a read-only compiled prefix. Moving it into common setup changes the task-entry
contract, so these results are not native AppWorld leaderboard scores.

The corrected worker saves state before closing and uses the official independent
saved-state grader. Reference solutions are isolated control inputs, never model
context, model traces or training examples for the compiler. Private APIs and
reserved requester overrides are rejected before execution.

## Why the original baseline limits need reconsideration

The 12 unchanged references all pass and use **701 API calls** in total, ranging
from **8 to 145** per task. **9/12** reference sequences exceed 24 calls; **7/12**
exceed 48. The interrupted pilot allowed 24 model requests and 48 API calls. These
reference lengths are not lower bounds on solving the tasks, and API counts are not
model-request counts. They show that the old limits should not be assumed adequate
without an explicit baseline-competence study.

Posthoc inspection finds three scenarios whose first two task-data calls are
song-library pages and three whose first two are playlist-library pages after
removing common setup. Both use page indices 0 and 1, without a semantic query.
These are development hypotheses for useful recurrent reads. No artificial model
boundaries were inserted into reference programs, and no automatic GAC family,
program or saved request count is claimed from them.

Endpoint and helper source inspection is retained, including authentication,
retrieval and serialization. The read probes fix their argument scope. Observed
absence of SQL writes alone was not used to classify login as read-only; its source
mints credentials and updates user bookkeeping. The saved-state equality checks
likewise do not prove absence of all hidden effects for arbitrary calls. The
production compiler effect catalog has not changed.

## Retained instrumentation failure

The initial inventory attempted to hash implementation files while the official
reference ran inside AppWorld's sandbox. The sandbox correctly rejected that file
access. All 12 failed instrumentation records and their frozen source remain in the
bundle. The amendment moved source hashing after execution; all 12 references then
passed. No task, expected answer, official test or sandbox restriction was modified.
These failures are instrumentation outcomes, not model or benchmark accuracy scores.

## Decision and remaining reviewer concerns

**COMMON_ENTRY_VALIDATED_NO_CONFIRMATORY_GO.** The next step is a separately sealed
baseline-competence pilot with a usable documentation interface, context policy and
fixed budgets. Genuine model traces must then establish recurrence and grounding.
Only after that should a matched comparison run against handwritten, simpler-admission
and named-compiler alternatives. The [reviewer concern ledger](../../iclr/notes/reviewer_concern_closure.md)
tracks the remaining population, independence, selection-wide risk, learned-gate,
mechanism and lifecycle obligations.

This work made **zero new model calls**, adding **$0** model/API spending. Conservative
campaign accounting remains **$2.2137322**, leaving **$297.7862678** of the $300 cap;
local compute and engineering are unpriced. The earlier invalid pilot remains
unchanged, and no manuscript numerical claim or PDF was updated.

See the [aggregate report](report.json), [reference seal](reference_seal.json),
[entry-control seal](entry_control_seal.json), [round-trip verification](bundle_verification.json),
[encrypted complete records](operational_evidence.bundle), and
[implementation/protocol](../../../experiments/appworld_entry_preflight/README.md).
Protected raw inputs, answers, credentials, responses and source remain encrypted
with the upstream distribution utility; do not redistribute decrypted contents.
