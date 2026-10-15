# Provider-free mechanism diagnostic

Public source text; constructed requests; deterministic reference policy and continuation.
Zero provider calls. These are not live LLM accuracy or deployment failure rates.

## ordinary

96 issue groups; three correlated request variants each.

| Arm | Correct / scheduled | Failed | Dispatched | Wrong after dispatch | Total tool calls |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 288/288 | 0 | 0 | 0 | 576 |
| full | 288/288 | 0 | 96 | 0 | 576 |
| no_entry_hull | 260/288 | 0 | 288 | 28 | 576 |
| no_completeness_check | 288/288 | 0 | 96 | 0 | 576 |
| no_statistical_gate | 288/288 | 0 | 96 | 0 | 576 |

Paired differences against full (cases; groups are reported separately in JSON):

- no_entry_hull: full-only correct 28; ablation-only correct 0; dispatch disagreements 192; failed pairs 0.
- no_completeness_check: full-only correct 0; ablation-only correct 0; dispatch disagreements 0; failed pairs 0.
- no_statistical_gate: full-only correct 0; ablation-only correct 0; dispatch disagreements 0; failed pairs 0.

## capped_response_stress

96 issue groups; three correlated request variants each.

| Arm | Correct / scheduled | Failed | Dispatched | Wrong after dispatch | Total tool calls |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 288/288 | 0 | 0 | 0 | 670 |
| full | 288/288 | 0 | 60 | 0 | 742 |
| no_entry_hull | 288/288 | 0 | 180 | 0 | 886 |
| no_completeness_check | 252/288 | 0 | 96 | 36 | 634 |
| no_statistical_gate | 288/288 | 0 | 60 | 0 | 742 |

Paired differences against full (cases; groups are reported separately in JSON):

- no_entry_hull: full-only correct 0; ablation-only correct 0; dispatch disagreements 120; failed pairs 0.
- no_completeness_check: full-only correct 36; ablation-only correct 0; dispatch disagreements 36; failed pairs 0.
- no_statistical_gate: full-only correct 0; ablation-only correct 0; dispatch disagreements 0; failed pairs 0.

The capped-response suite is constructed distribution shift. Do not pool the suites.
A constant gate or identical gate decisions provides no incremental-gate evidence.
The template, task-scope guard and completeness contract are explicit study design;
this is not evidence that the production compiler discovers these safeguards automatically.
