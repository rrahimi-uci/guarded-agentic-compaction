# ICLR 2027 Review and Revision Scorecard

Review date: August 14, 2026. Scores use a 0--100 scale and assess the blind
submission as an ICLR paper, not the larger open-research article. The review
checked the LaTeX source, compiled PDF, retained result JSON, admission
register, generated figures and tables, bibliography, artifact validators, and
the official [ICLR 2027 Author Guidelines](https://iclr.cc/Conferences/2027/AuthorGuidelines),
[Call for Papers](https://iclr.cc/Conferences/2027/CallForPapers), and
[AI Policy for Authors](https://iclr.cc/Conferences/2027/AIPolicyForAuthors).

## Baseline assessment

| Dimension | Before | Main reason for the baseline score |
|---|---:|---|
| Problem importance and motivation | 92 | Clear operational problem with a concrete safety and efficiency tension. |
| Novelty and significance | 85 | Distinct compile-or-retire framing, but built from established tracing, synthesis, and risk-control ideas. |
| Technical soundness | 83 | Strong core design, but the calibration edge cases and multi-partition control flow were not represented precisely. |
| Method clarity | 85 | Good architecture and algorithms, with ambiguity around group-level versus episode-level risk. |
| Evaluation design | 82 | Paired live tests, negative benchmarks, and time-forward transfer are valuable; breadth remains limited. |
| Evidence strength | 80 | Exact retained evidence is unusually auditable, but the richest study uses one provider/model and one primary repository snapshot. |
| Results and interpretation | 87 | Refusals and manual parity are reported honestly; the introduction mixed two distinct empirical cohorts. |
| Reproducibility | 91 | Raw outputs, manifests, generators, algorithms, and configuration are retained; anonymous packaging remains a pre-upload task. |
| Writing and presentation | 87 | Strong nine-page narrative and figures, weakened by the cohort inconsistency and a few formal omissions. |
| ICLR compliance and anonymity | 86 | Correct blind template and page budget, but the checklist contained stale deadlines and the source depended on an external figure path. |
| Limitations and responsible claims | 94 | Claim boundaries, refusal evidence, ethics, and unresolved scientific risks are unusually explicit. |

**Baseline overall: 86/100.** The draft was already technically substantial,
but the cohort conflation and formal pseudocode defects were material enough to
prevent a submission-ready rating.

## Evidence-bounded revisions

The revision uses no new experiments and changes no reported result.

1. The worked example now separates held-out issue #4420 in the expanded
   30-record study from issue #6602 in the earlier 18-record continuation
   study. The former supports the grounded two-read prefix and 92/92
   certificate; the latter demonstrates that correct tool replay can still
   lose answer evidence.
2. The paper now defines the conservative scenario-group statistical unit and
   states when it coincides with episode-level risk in the reported live data.
3. The Clopper--Pearson equation and calibration algorithm now define empty and
   all-violation edge cases rather than invoking an undefined beta quantile.
4. The compile cascade now records an infeasible partition and continues to
   other compatible partitions instead of prematurely returning from the
   entire search.
5. The proposition and proof now state the required order correctly: original
   calibration groups are i.i.d.; admission is induced by a candidate frozen
   before calibration.
6. The ICLR source is self-contained with a local copy of every included
   figure, and the generator refreshes those copies deterministically.
7. The AI-use disclosure now includes methodological critique and consistency
   review, and the compliance notes use the current official deadlines.

## Final assessment

| Dimension | Final | Change | Residual cap |
|---|---:|---:|---|
| Problem importance and motivation | 94 | +2 | Practical deployment prevalence is not measured. |
| Novelty and significance | 86 | +1 | The ingredients are established even though their guarded composition is distinctive. |
| Technical soundness | 90 | +7 | The certificate remains per fixed candidate, not compiler-wide. |
| Method clarity | 92 | +7 | Full runtime detail remains in the appendix by necessity. |
| Evaluation design | 85 | +3 | No new experiment can remove the one-provider and simplified-transfer limitations. |
| Evidence strength | 82 | +2 | Gate selectivity is still mostly a support threshold rather than a risk--coverage frontier. |
| Results and interpretation | 93 | +6 | Manual parity and negative results appropriately limit the conclusion. |
| Reproducibility | 94 | +3 | An anonymous artifact bundle must still be created before upload. |
| Writing and presentation | 94 | +7 | The main text uses the complete nine-page allowance without reducing font or margins. |
| ICLR compliance and anonymity | 97 | +11 | Author-side OpenReview profiles, quotas, and reciprocal-review eligibility require human confirmation. |
| Limitations and responsible claims | 96 | +2 | Remaining weaknesses are empirical rather than hidden in the prose. |

**Final overall: 90/100.** This is a rigorous, coherent, blind-ready paper
whose remaining acceptance risks are primarily empirical: limited provider and
repository breadth, manual-program parity, a step-like admission gate, and the
lack of a compiler-wide multiplicity guarantee. Those limitations cannot be
removed honestly using only the existing evidence.

---

# Second review pass, August 16, 2026

This pass reviewed the draft again against `paper/open_research/article.pdf` as the source
of truth and against the official ICLR 2027 template's own instruction text. It found
compliance defects the first pass had marked as clean, so several dimensions are scored
*below* their previous "final" values: the earlier 97 for compliance was not supportable.

## What the second pass found

Every quantitative claim re-derived from `paper/tex/body.tex` and the sealed result JSON
checked out, including `559/881 = 63.5%` for API-Bank, which appears in no prose and had to
be reconstructed from `graph_diagnostics`. The defects were presentational and definitional:

- Figure 1 and the per-family reduction figure were never referenced from the body, though
  the compliance checklist asserted otherwise.
- The benchmark table was a hand-built pseudo-float with a literal bold `Table N.` in place
  of a caption, bypassing the class's table rules entirely.
- `\retire` printed as a red word in running text.
- The introduction wrote `labels(4420)` and `comments(4420, ...)` where both consume the
  *returned* `record.issue_number` — the witness the provenance argument depends on.
- Table 3's caption overstated the fixed template as "at least as efficient in both
  settings"; it is marginally worse on cost in the balanced rerun.
- `\kappa` had no value, `\Lambda` no elements, and Proposition 1 reused `\eta` for the
  data-selected threshold.

## Scores after the second pass

| Dimension | Score | Weight | Binding limit |
|---|---:|---:|---|
| Problem importance and motivation | 92 | 0.10 | Prevalence of the situation in deployed agents is argued, not measured. |
| Novelty and significance | 82 | 0.18 | Every ingredient is established; the contribution is the composition and the discipline, and the empirical payoff is deliberately modest. |
| Technical soundness | 89 | 0.15 | The certificate is per fixed candidate, not compiler-wide over the search the system performs. |
| Method clarity | 92 | 0.08 | Runtime detail necessarily lives in the appendix at nine pages. |
| Evaluation design | 83 | 0.12 | One provider/model family, one primary snapshot, and a transfer task simple enough for a fixed template to tie. |
| Evidence strength | 80 | 0.15 | The gate never demonstrates selectivity at the registered level; n=90 held-out records carries the headline. |
| Results and interpretation | 93 | 0.07 | Refusals, manual parity, and the single baseline error are all reported rather than buried. |
| Reproducibility | 93 | 0.05 | The anonymous artifact bundle is still a pre-upload action. |
| Writing and presentation | 91 | 0.05 | Dense; figure 1 remains a loose infographic occupying a third of page 2. |
| ICLR compliance and anonymity | 96 | 0.03 | Author-side OpenReview obligations need human confirmation. |
| Limitations and responsible claims | 96 | 0.02 | Remaining weaknesses are empirical, not concealed. |

**Weighted overall: 87/100.**

The submission is mechanically ready and unusually honest. The acceptance risk is not
compliance or rigour but reach: novelty is compositional and the strongest empirical claim
is preservation-with-savings on 90 held-out records from one provider, against a manual
program that ties. On the ICLR 1--10 scale this reads as a borderline paper whose fate turns
on how a reviewer weighs a well-evidenced negative result and a refusal discipline against a
modest positive one.

The three changes that would move the score most, in order, are: a gate that demonstrates a
real risk--coverage frontier rather than a support threshold; a second provider or model
family; and a compiler-wide multiplicity treatment. None can be produced honestly from the
existing evidence, which is why they are named as follow-ups rather than repaired in prose.

---

# Submission-surface verification, August 16, 2026

The final upload-surface audit found one anonymity weakness that a PDF-only
check could miss: the blind-rendered PDF was anonymous, but `main.tex` still
carried a real author block and named PDF-metadata branch. If that source were
included in supplementary material, it could reveal identity despite the blind
rendering. The submission source now contains only `Anonymous authors`, has
empty author metadata unconditionally, and documents that named variants belong
in a separate non-submission copy. The reproducibility statement now likewise
describes the anonymous archive as a pre-upload deliverable rather than
claiming an archive already exists.

An isolated Tectonic rebuild of that anonymous source completed without errors,
unresolved references, or overfull boxes. The rendered PDF remains 17 pages;
Sections 1--8 end on page 9, the required statements begin on page 10, and the
appendix follows the bibliography. Text extraction found no author identity or
acknowledgement in the rendered PDF.

**Final weighted score: 87/100.** The anonymity hardening closes an accidental
source-disclosure route but does not change the score: the anonymous artifact
bundle and author-side OpenReview disclosures still need human completion, and
the binding ICLR risks remain scientific reach, evaluation breadth, and
compiler-wide multiplicity control rather than presentation mechanics.

---

# Evidence-breadth revision, August 17, 2026

This revision adds no new experiments. It moves four retained, previously
compressed records into the appendix: repository-level outcomes for both
time-forward protocols, the 17/18-to-18/18 continuation counterexample and
checked repair, a ten-benchmark evidence-disposition map, and the full
registered-versus-exploratory gate-behaviour inventory. These additions use the
unlimited appendix rather than the nine-page main-text budget and retain the
distinction between compiler measurement, provider-free auditing, screening,
and access-blocked work.

| Dimension | Previous | Revised | Reason for revision |
|---|---:|---:|---|
| Evaluation design | 83 | 85 | The disaggregated core and balanced time-forward cohorts make the four successes, one retirement, and different class mixes inspectable rather than only pooled. |
| Evidence strength | 80 | 82 | The continuation failure/repair and ten-benchmark disposition map expose both negative and out-of-scope evidence instead of hiding it. |
| Remaining dimensions | unchanged | unchanged | No retained result adds a second provider, a harder workflow family, or compiler-wide multiplicity control. |

**Revised weighted score: 88/100.** This is a presentation and auditability
gain, not a claim of stronger causal evidence. The score remains capped by one
provider/model family, one rich snapshot, the narrow transfer task, and the
registered gate's all-or-none behaviour.
