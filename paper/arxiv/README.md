# `arxiv.sty` — the arXiv preprint style

`arxiv.sty` is vendored verbatim from
[kourgeorge/arxiv-style](https://github.com/kourgeorge/arxiv-style) (MIT
licensed). It is the widely used "A Preprint" layout derived from the NeurIPS
style: US Letter, single column, 6.5 × 9 in text block, Times body, block
paragraphs, a small-caps title between two heavy rules, an `A Preprint` banner
under the title, a centred indented abstract, and a ruled running head.

The open-research build in [`../tex/article.tex`](../tex/article.tex) uses it, so
this article matches the layout of preprints such as
[arXiv:1910.04944](https://arxiv.org/pdf/1910.04944).

The file is unmodified; every deviation this paper needs is applied from the
wrapper's preamble instead, so the style can be re-pulled upstream without a
merge.
