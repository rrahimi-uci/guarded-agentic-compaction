# Source error and clustering audit

post-registration author audit; not independent human adjudication. No outcome or cohort is changed.

Incorrect or failed episodes, including pilot: 113.
Completed live GAC dispatches checked against frozen probes: 2724; mismatches: 0.
Failure types: {'InternalServerError': 1}.
Field-check failures: {'evidence_excerpt_exact': 50, 'comment_grounded': 12, 'category_correct': 45, 'evidence_label_correct': 46, 'title_exact': 1, 'title_correct': 4}.

| Cell | Day groups / largest | Author groups / largest | Day-bootstrap accuracy-difference CI | Author-bootstrap CI |
| --- | ---: | ---: | --- | --- |
| backlog_attention / gpt-5.6-luna | 133 / 4 | 130 / 4 | [0.0, 0.02158273381294964] | [0.0, 0.022058823529411766] |
| backlog_attention / gpt-6-luna | 133 / 4 | 130 / 4 | [-0.029202447402318584, 0.014184397163120567] | [-0.02962962962962963, 0.014598540145985401] |
| issue_type / gpt-5.6-luna | 470 / 4 | 386 / 70 | [-0.013559897556904836, 0.01774265204023137] | [-0.014210767166004059, 0.01779438724697254] |
| issue_type / gpt-6-luna | 470 / 4 | 386 / 70 | [-0.01535901811499081, 0.015281437368218572] | [-0.01763694366635543, 0.016368030750116457] |
| pr_outcome / gpt-5.6-luna | 414 / 11 | 190 / 120 | [-0.008000320512820513, 0.0034662045060658577] | [-0.008064516129032258, 0.0044979199589394465] |
| pr_outcome / gpt-6-luna | 414 / 11 | 190 / 120 | [-0.008547008547008548, 0.0] | [-0.009237875288683603, 0.0] |

Cluster intervals are post-registration descriptive sensitivity; author/day independence is unproven. Zero-width intervals do not prove equality or noninferiority. The registered exact six-cell analysis remains primary.

The source-only structural screen is in source_audit.json. Labels such as dataset bug can produce strict contract failures without demonstrating a semantically false classification. Full per-episode answers and failed checks are in error_audit.json.
