# Live recovery pilot: observed results

Constructed requests on previously used public records; exploratory fixed-artifact pilot.

Status: incomplete; attempted 153/576; estimated spend $0.049067.
Costs use the frozen rate card, not invoices. Offline gate calibration does not certify live answers.

## ordinary

| Arm | Correct / scheduled | Failed | Requests* | Continuation tools* | Total tools* | Estimated cost* |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 20/72 | 0 | 2.400000 | 1.400000 | 1.400000 | 0.000408 |
| full | 19/72 | 1 | 2.000000 | 1.000000 | 1.700000 | 0.000355 |
| no_entry_hull | 20/72 | 0 | 1.000000 | 0.000000 | 2.000000 | 0.000202 |
| no_completeness_check | 20/72 | 0 | 2.000000 | 1.000000 | 1.700000 | 0.000348 |

*Means over completed episodes; comparisons require complete accounting in both arms.

## capped_response_stress

| Arm | Correct / scheduled | Failed | Requests* | Continuation tools* | Total tools* | Estimated cost* |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 18/72 | 0 | 2.277778 | 1.277778 | 1.277778 | 0.000397 |
| full | 18/72 | 0 | 1.888889 | 0.888889 | 1.555556 | 0.000331 |
| no_entry_hull | 18/72 | 0 | 1.000000 | 0.000000 | 2.000000 | 0.000200 |
| no_completeness_check | 18/72 | 0 | 1.888889 | 0.888889 | 1.555556 | 0.000338 |

*Means over completed episodes; comparisons require complete accounting in both arms.

The suites share issue groups. Request variants are correlated, not independent extra samples.
See analysis.json for attempted/completed/unattempted counts, dispatches and paired outcomes.
