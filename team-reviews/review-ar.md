# Review — AR

**Status:** TODO — not started
**Paper:** From Traces to Guarded Programs: Evidence-Gated Compilation of
Recurrent Agent Workflows
**Reviewer:** AR
**Date:**

## What to read

- [ ] `paper/ICLR/build/main.pdf` — 9-page submission (build: `cd paper/ICLR && tectonic --outdir build main.tex`)
- [ ] `paper/open_research/article.pdf` — full article, if the short version raises questions
- [ ] `paper/ICLR/notes/reviewer_gap_analysis.md` — known weaknesses, so you can skip re-finding them

## TODO — please cover

- [ ] **Claim vs. evidence.** Does any sentence claim more than the numbers support?
      The intended claim is automated discovery + guarded admission, explicitly
      *not* runtime dominance over hand-written code.
- [ ] **The admission argument.** Proposition 1 is per-candidate, not
      compiler-wide. Is that boundary stated clearly enough, or will a reviewer
      read it as stronger than it is?
- [ ] **The refusal result.** NESTFUL and API-Bank retire at calibration with
      zero wrong executions. Does that land as a result, or as a failure?
- [ ] **Numbers.** Spot-check anything against `paper/results/`. Two errors were
      already found this way (delta=0.1 not 0.05; API-Bank denominator 881).
- [ ] **The compression comparison.** §"Tool-use evaluation and caching
      economics" concedes an uncompressed baseline. Is the concession honest
      enough, or does it need to be louder?
- [ ] **Anything that would make you reject it.**

## Notes

<!-- free-form; strongest objection first -->

## Verdict

**Recommendation:**
**Confidence:**
