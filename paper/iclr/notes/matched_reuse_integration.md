# Matched workflow-memory evidence integration

The canonical ICLR manuscript now includes the prospectively sealed offline
AWM API-task adaptation comparison in Appendix J and the main Results. It is a
whole-system comparison with a pinned external implementation, not native
browser reproduction or a compiler-only causal experiment.

The main seven-field endpoint is 116/120 GAC versus 114/120 for baseline and
adapted AWM. Resource savings are observed; an accuracy gain is not established
(exact McNemar p=0.50, Holm p=1.00). The failed GAC episode, every incorrect
answer, and a post-hoc finding of one unanswerable excerpt task remain disclosed.
No historical denominator or risk certificate is altered. The 120 primary
issues are not added to the manuscript's six-study 810-episode summary.

Sources and reproducible audit commands are in
`experiments/matched_reuse_baseline/VALIDATION.md`; the table comes from
`render_report.py`, and the post-run source check comes from `audit_errors.py`.
Neither changes the frozen study driver or its selection after execution.
The source audit is not independent human adjudication.

At that integration, the manuscript and tracked PDF were updated; older long-form wrappers, slides,
and hosted publications are not regenerated or deployed. The abstract was
unchanged at that integration, with its local OpenReview metadata copy aligned. Anonymous
supplementary packaging remains a separate pre-upload task. The PDF preserves
the existing ten-page main-text revision configuration, not a claim of initial
submission readiness. At that integration, main text ended on page 10; references and appendices
brought the PDF to 48 pages. Later study integration is recorded separately in
`generalization_gate_integration.md`.
