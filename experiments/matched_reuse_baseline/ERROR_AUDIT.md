# Post-run source and error audit

This provider-free author audit preserves every original outcome and denominator. It is not independent human adjudication and does not revise the sealed study.

The 20-character minimum excerpt is impossible for issue 377: its title has six characters, its body is empty, and it has no comments. It was selected by the frozen hash ranking, which did not screen excerpt feasibility. All three arms fail it: GAC at output-schema validation, baseline and adapted AWM at the source-excerpt check. The failed GAC output was not retained, so its exact invalid field cannot be reconstructed. Its observed usage and $1 reserve remain.

This was the only issue failing this excerpt-length screen among all 126 pilot/primary issues. Passing this narrow screen does not prove every other aspect of task validity. No issue is replaced or removed from the primary analysis. Future studies should freeze a feasibility screen before selection.

Each primary arm has three category/evidence-label failures involving the label `dataset bug`: the fixed task uses exact category labels and the grader expects `other`/`none`, whereas these answers use `bug`/`dataset bug`. The particular records differ by arm. These are strict contract errors, not demonstrated false real-world claims. Excerpt and title mismatches likewise retain the exact endpoint; this audit does not equate every mismatch with semantic hallucination.

| Issue | Arm | Status | Incorrect fields |
| --- | --- | --- | --- |
| 6670 | awm_offline_adapted | completed | evidence_excerpt_exact |
| 3553 | awm_offline_adapted | completed | evidence_excerpt_exact |
| 388 | gac | completed | category_correct, evidence_label_correct |
| 388 | awm_offline_adapted | completed | category_correct, evidence_label_correct |
| 388 | baseline | completed | evidence_excerpt_exact |
| 3630 | baseline | completed | category_correct, evidence_label_correct |
| 3630 | gac | completed | category_correct, evidence_label_correct |
| 3630 | awm_offline_adapted | completed | category_correct, evidence_label_correct |
| 854 | gac | completed | category_correct, evidence_label_correct |
| 854 | awm_offline_adapted | completed | category_correct, evidence_label_correct |
| 854 | baseline | completed | category_correct, evidence_label_correct |
| 377 | gac | failed | ModelBehaviorError |
| 377 | awm_offline_adapted | completed | evidence_excerpt_exact |
| 377 | baseline | completed | evidence_excerpt_exact |
| 331 | baseline | completed | category_correct, evidence_label_correct |
| 7354 | baseline | completed | title_exact |
