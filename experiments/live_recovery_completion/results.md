# Live recovery completion: observed results

Attempted 2304/2304; completed 2300; correct 2186.
Estimated run spend $0.952696; aggregate estimate plus retained reserves $7.001762 / $200.

Frozen repository rates are estimates, not provider invoices. Failed attempts remain in denominators.
Confirmation and replication are separate; variants are clustered by issue. Intervals are descriptive, unadjusted for multiple comparisons.

## confirmation: ordinary

| Arm | Correct / scheduled | Failed | Requests* | Total tools* | Cost* |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 204/216 | 1 | 2.367442 | 1.367442 | 0.000458 |
| full | 205/216 | 1 | 1.925581 | 1.595349 | 0.000373 |
| no_entry_hull | 186/216 | 1 | 1.032558 | 2.032558 | 0.000259 |
| no_completeness_check | 210/216 | 0 | 1.916667 | 1.583333 | 0.000381 |

*Completed-episode means. Overall resource comparisons require complete accounting.

## confirmation: capped_response_stress

| Arm | Correct / scheduled | Failed | Requests* | Total tools* | Cost* |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 211/216 | 0 | 2.740741 | 1.740741 | 0.000531 |
| full | 205/216 | 1 | 2.376744 | 2.046512 | 0.000477 |
| no_entry_hull | 207/216 | 0 | 1.842593 | 2.842593 | 0.000401 |
| no_completeness_check | 204/216 | 0 | 2.300926 | 1.967593 | 0.000461 |

*Completed-episode means. Overall resource comparisons require complete accounting.

## replication: ordinary

| Arm | Correct / scheduled | Failed | Requests* | Total tools* | Cost* |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 71/72 | 0 | 2.416667 | 1.416667 | 0.000446 |
| full | 70/72 | 0 | 1.930556 | 1.597222 | 0.000365 |
| no_entry_hull | 67/72 | 0 | 1.055556 | 2.055556 | 0.000254 |
| no_completeness_check | 70/72 | 0 | 1.902778 | 1.569444 | 0.000360 |

*Completed-episode means. Overall resource comparisons require complete accounting.

## replication: capped_response_stress

| Arm | Correct / scheduled | Failed | Requests* | Total tools* | Cost* |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 70/72 | 0 | 2.722222 | 1.722222 | 0.000518 |
| full | 68/72 | 0 | 2.458333 | 2.125000 | 0.000471 |
| no_entry_hull | 69/72 | 0 | 1.777778 | 2.777778 | 0.000372 |
| no_completeness_check | 69/72 | 0 | 2.236111 | 1.902778 | 0.000436 |

*Completed-episode means. Overall resource comparisons require complete accounting.
