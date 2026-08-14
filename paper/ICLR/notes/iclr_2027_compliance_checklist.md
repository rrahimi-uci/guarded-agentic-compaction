# ICLR 2027 Compliance Checklist

Source references used for this checklist:

- official ICLR 2027 author guidelines
- official ICLR 2027 call for papers
- official ICLR 2027 AI policy for authors

## Template and formatting

- [x] Uses the official ICLR 2027 style files downloaded from the official style zip.
- [x] The repository defaults to the blind submission build (`\iclrfinalcopy` commented out).
- [x] The stock review line-number ruler is enabled in the blind build.
- [x] `times` replaced by `newtxtext`/`newtxmath` because this paper builds with Tectonic (XeTeX), where legacy `times` does not resolve: the body falls back to Latin Modern with no bold or italic, so `\textbf`, `\emph`, `\textsc`, theorem heads, and table headers all rendered as upright regular text. Under pdfTeX `times` works fine, so this is a toolchain interaction, not a broken package. Embedded body face is TeX Gyre Termes (Times), confirmed with `pdffonts`.
- [x] Confirmed from the compiled PDF that the main text (sections 1--8) ends within the `<= 9` page limit.
- [x] References are separated from the main text and do not count toward the page limit.
- [x] Appendix is placed after the references.
- [x] The paper source stays in a dedicated `paper/ICLR/` working directory.

## Anonymity

- [x] **PDF author block is anonymous.** `\iclrfinalcopy` is commented out; the style file prints "Anonymous authors", uses the "Under review" running head, and clears the PDF author metadata. Recheck this after every build intended for upload.
- [x] No acknowledgements are included in the blind-ready submission source.
- [x] The main paper avoids linking directly to the identified public repository.
- [ ] Prepare an anonymous supplementary artifact bundle or anonymous repository before submission. The reproducibility statement and appendix F currently assert this bundle exists; it must actually be built before upload.

## Required and recommended sections

- [x] Required AI use statement included before references.
- [x] Ethics statement included before references.
- [x] Reproducibility statement included before references.
- [x] Limitations are discussed explicitly in the main paper (section 7) and extended in appendix E.

## Technical presentation

- [x] Formal problem statement with numbered equations (grounding, prefix invariant, selective dispatch, selective objective).
- [x] System architecture diagram (figure 1) instead of a bulleted box stack.
- [x] Deployed compiler and admission rule given as algorithms 1--2 in the main text; provenance construction and runtime dispatch as algorithms 3--4 in the appendix.
- [x] Proposition 1 stated in a theorem environment with a proof in appendix A; `alpha`, `delta`, and the threshold grid are defined in the main text before use.
- [x] Every float is referenced from the body text.
- [x] Paired statistics reported: exact McNemar, Clopper--Pearson bounds, bootstrap intervals, Wilcoxon signed-rank. Headline CIs in the main text, full per-endpoint table in appendix E.
- [x] Absolute counts reported alongside every percentage (359 -> 120 requests, 294,677 -> 108,839 tokens, etc.) so reductions are auditable.
- [x] Admission certificates reported for the artifacts that were admitted (n=92 groups, k=0 violations, U=0.0498 <= alpha=0.05, coverage 1.0), not just pass/fail.
- [x] Refusal funnel table (table 3) shows stage-by-stage attrition on NESTFUL and API-Bank, isolating calibration as the binding stage.
- [x] Corrected the confidence budget: the configured value is `delta = 0.1`, not 0.05. It is what yields the 92-group requirement and the 0.0498 bound recorded in `paper/results/admission_register.json`; `delta = 0.05` would require 106 groups.
- [x] Hyperparameters collected in appendix C.

## Claim hygiene

- [x] Main claim is narrowed to guarded compile-or-retire specialization.
- [x] Manual baseline parity is stated explicitly rather than hidden, including the one family where the manual program is cheaper.
- [x] Refusal/retirement evidence is retained and described as part of the result, with the binding stage identified (calibration, not provenance or replay).
- [x] Cross-repository evidence is described as narrower than the primary workflow-family result.
- [x] Saturated feasibility ceiling flagged as a property of the workload, not evidence about the compiler.

## Submission operations

- [x] Recompiled the final PDF and verified page count for the current draft.
- [x] Related work cites the trace-JIT, partial-evaluation, effect-system, program-synthesis, and risk-control lineage rather than only agent-optimization papers (47 distinct citations of 52 bib entries).
- [x] Sanity-checked that the current figures, captions, and appendix do not reveal author identity.
- [ ] Before uploading, recheck the official ICLR 2027 submission portal and deadline page. The current guide lists an abstract deadline of `September 11, 2026` AOE and a full-paper deadline of `September 16, 2026` AOE.
