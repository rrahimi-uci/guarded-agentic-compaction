# Interpretation correction: sequential issue-gate extension

2026-10-28, after execution. This note corrects the interpretation in
`extension_protocol.md`; the historical protocol, its execution record, sealed
inputs, raw episodes, grades, numerical audit and selected threshold are retained
unchanged. In particular, the protocol's phrases "certify intermediate coverage"
and "certifiable intermediate coverage" are superseded by this note.

The frozen numerical rule selected eta = 0.50 on 261 of 311 pooled calibration
groups (83.9%), with four errors and a nominal upper bound of 0.0443. The first
184 groups were observed before deciding to extend; the 127 new groups are a
natural remainder rather than the first cohort's quota-enriched sampling frame.
The threshold-wise confidence budget does not establish simultaneous coverage
over this adaptive procedure, and the common-distribution assumption is unproved.
The calculation is exploratory, not a certificate at the nominal confidence level
for that procedure. Registering the extension before new provider calls does not
retroactively make the full design prospective.

The sealed test remains a separate observed evaluation: 76/90 compiled dispatches,
two wrong answers after those dispatches, and three learned-policy errors versus
two baseline and five support-only errors. It does not establish a quality benefit,
graded selectivity, or independent confirmation of a 5% dispatch-risk target.

Time-uniform inference can address adaptive monitoring, but does not by itself
resolve different sampling frames. A post hoc adjustment is not presented as a
repair or a newly registered analysis. The ICLR appendix and generated table now
label the bounds and admission decision as nominal arithmetic.
