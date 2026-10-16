# Execution and validation record

Dedicated branch: experiment/generalization-gate-ablation, based on merged PR #84
(475b8fe). No changes to main and no merge by the agent.

Provider-free preparation found 3,584 unused PRs, 811 unused issues and 150
unused backlog records before cross-family allocation and source-validity checks.
Backlog was allocated first. The final disjoint cohorts contain 1,362 source
records including 18 pilot records, shared across two models: 8,172 scheduled
agent episodes and six induction calls.

The full, support-only and deterministic dispatcher signatures agreed on all
2,724 record/model cases. PR and backlog dispatch on every selected record;
issue routing dispatches on 600/606, with the same six refusals per model in all
three variants. This supports no incremental gate benefit on these candidates,
not general equivalence or elimination of the candidate-admission requirement.

Before paid execution:
- 23 new regression tests passed, exercising all 18 family/model/arm combinations
  through the real SDK with a local fake model, partial failures, exact loss
  bounds, prospective power, balanced schedule, budget reserves and gate copies.
- New plus existing matched-study regression tests: 40 passed.
- Full suite, release/artifact/Pages/package validation: pending at preparation.
- Estimated budget carried forward: $8.57705193 including retained reserves.
- Standard prices verified from official OpenAI API pricing documentation on
  2026-10-15. No credentials or provider reasoning is stored.

Historical study files and numerical claims are retained. Initial preparation
seals were regenerated before any provider call as audit checks were completed;
only the committed final seal authorizes execution. A used seal is immutable.
