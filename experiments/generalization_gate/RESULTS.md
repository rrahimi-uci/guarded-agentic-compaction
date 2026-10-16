# Fresh generalization and gate attribution: retained results

Attempted 8172/8172; halt reason: None. Source regrading, tool replay, frozen-memory and usage audits passed.

| Family / model | GAC correct | AWM correct | Baseline correct | GAC-only / AWM-only correct | Loss upper bound | NI at 5pp |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| backlog_attention / gpt-5.6-luna | 143/144 | 142/144 | 144/144 | 1 / 0 | 3.27% | True |
| backlog_attention / gpt-6-luna | 142/144 | 143/144 | 144/144 | 1 / 2 | 5.86% | False |
| issue_type / gpt-5.6-luna | 584/600 | 583/600 | 590/600 | 12 / 11 | 3.61% | True |
| issue_type / gpt-6-luna | 583/600 | 583/600 | 582/600 | 13 / 13 | 4.04% | True |
| pr_outcome / gpt-5.6-luna | 597/600 | 598/600 | 597/600 | 1 / 2 | 1.43% | True |
| pr_outcome / gpt-6-luna | 598/600 | 600/600 | 599/600 | 0 / 2 | 1.43% | True |

The one-sided loss bounds use 0.05/6 error probability. They conservatively bound accuracy loss by ignoring GAC-only successes. NI requires complete attempted pairs and an upper bound below 5 percentage points. Backlog has low prospective power. These are task-accuracy results, not runtime safety certificates.

| Family / model | Arm | Attempted / completed | Requests / attempted | Tools / attempted | Estimated USD / 1000 attempted | Usage complete |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| backlog_attention / gpt-5.6-luna | baseline | 144 / 144 | 4.000 | 3.000 | 0.756 | True |
| backlog_attention / gpt-5.6-luna | gac | 144 / 144 | 1.000 | 3.000 | 0.204 | True |
| backlog_attention / gpt-5.6-luna | awm_offline_adapted | 144 / 144 | 4.000 | 3.000 | 0.806 | True |
| backlog_attention / gpt-6-luna | baseline | 144 / 144 | 4.000 | 3.000 | 0.344 | True |
| backlog_attention / gpt-6-luna | gac | 144 / 144 | 1.000 | 3.000 | 0.088 | True |
| backlog_attention / gpt-6-luna | awm_offline_adapted | 144 / 144 | 4.000 | 3.000 | 0.380 | True |
| issue_type / gpt-5.6-luna | baseline | 600 / 600 | 4.000 | 3.000 | 0.879 | True |
| issue_type / gpt-5.6-luna | gac | 600 / 600 | 2.000 | 3.000 | 0.588 | True |
| issue_type / gpt-5.6-luna | awm_offline_adapted | 600 / 600 | 4.000 | 3.000 | 0.931 | True |
| issue_type / gpt-6-luna | baseline | 600 / 600 | 4.007 | 3.007 | 0.373 | True |
| issue_type / gpt-6-luna | gac | 600 / 600 | 2.002 | 3.002 | 0.210 | True |
| issue_type / gpt-6-luna | awm_offline_adapted | 600 / 600 | 4.002 | 3.002 | 0.411 | True |
| pr_outcome / gpt-5.6-luna | baseline | 600 / 599 | 3.998 | 2.998 | 0.681 | False |
| pr_outcome / gpt-5.6-luna | gac | 600 / 600 | 1.000 | 3.000 | 0.164 | True |
| pr_outcome / gpt-5.6-luna | awm_offline_adapted | 600 / 600 | 4.000 | 3.000 | 0.739 | True |
| pr_outcome / gpt-6-luna | baseline | 600 / 600 | 4.000 | 3.000 | 0.318 | True |
| pr_outcome / gpt-6-luna | gac | 600 / 600 | 1.000 | 3.000 | 0.074 | True |
| pr_outcome / gpt-6-luna | awm_offline_adapted | 600 / 600 | 4.000 | 3.000 | 0.353 | True |

## Gate attribution

All full, support-only and deterministic-guard dispatch signatures matched across all 2,724 selected record/model cases (including pilot). This is exact provider-free routing/evidence agreement on already admitted candidates, not three independently sampled live arms or a new learned-gate benefit. Six issue records fell back identically on each model. The historical learned end-to-end gate retirement is unchanged.

## Accounting and limits

Pilot: {'attempted': 108, 'completed': 108, 'correct': 107}. Errors and failures are retained in analysis.json. Aggregate estimated spend plus retained reserves: $13.44132081 / $400. The cap is not a provider billing limit.

Per-cell induction costs, paired resource intervals, tighter margin sensitivity and descriptive McNemar tests are in analysis.json. Resource means include all attempted episodes; paired intervals exclude incomplete pairs and disclose their denominators. Missing usage is not zero cost.

One repository/snapshot, three workflows, two related models, shared historical discovery and one induced memory per cell. This is adapted AWM, not its native benchmark. Compiled evidence placement differs between workflow adapters. Independence across tasks/authors/time is not established. No broad cross-domain, independent human audit, gate safety or acceptance claim follows.
