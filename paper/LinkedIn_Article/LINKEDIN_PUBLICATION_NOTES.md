# LinkedIn Publication Notes

Operational notes for publishing the article. The figure inventory and the
regeneration command live in [README.md](README.md); this file covers only the
upload itself.

## What to publish

- **Article text:** `LinkedIn_Article_Polished.md` is canonical. Paste the prose
  into LinkedIn's editor and upload the images separately — LinkedIn does not
  resolve relative image paths.
- **Cover image:** `images/01_hero.png`.
- **Body images:** `02_pipeline`, `03_results`, `04_refusal`,
  `05_compaction_vs_compression`, `06_takeaway`, inserted at the section each
  one follows in the markdown.

## Alt text

Every image in `LinkedIn_Article_Polished.md` already carries descriptive alt
text in its markdown `![...]` tag. Copy that string into LinkedIn's alt-text
field rather than rewriting it — the wording is deliberate and describes what
the figure shows, not merely what it is called.

## Upload guidance

- Keep the headline in LinkedIn's title field. The cover image deliberately
  does **not** repeat the article headline, because LinkedIn renders the title
  above the cover and duplicating it reads as a mistake.
- Figures are 2× (a 1800×1080 page ships as 3600×2160). LinkedIn downsamples on
  upload; do not pre-shrink them.
- Insert each body image *after* the paragraph it supports, so the claim is
  read before the evidence.
- The article links to an external repository (Headroom) in the compression
  section. LinkedIn will render it as a preview card unless the link sits
  inline in a sentence, which it does.

## Claim hygiene

Two statements in the article are load-bearing and should not be softened by
editing for length:

- Hand-written programs also reach 90/90, so the contribution is automated
  discovery and guarded admission — not universal superiority.
- The reported reductions compare against an *uncompressed* baseline, so the
  token number is the part attributable to removing model boundaries.

Both mirror limitations stated in the paper. Dropping either would make the
article claim more than the evidence supports.
