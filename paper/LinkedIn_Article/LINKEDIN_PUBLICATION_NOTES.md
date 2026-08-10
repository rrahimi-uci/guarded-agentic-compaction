# LinkedIn Publication Notes

Operational notes for publishing the article. The figure inventory and the
regeneration command live in [README.md](README.md); this file covers only the
upload itself.

## Publish in this order

1. **Publish the article** (below). Nobody sees it yet — LinkedIn does not push
   articles into the feed.
2. **Post the feed post** from [LinkedIn_Post.md](LinkedIn_Post.md) with
   `images/01_hero.png` attached and **no link in the body**.
3. **Add the article link as your own first comment**, immediately.
4. **Stay for two hours** and reply to every comment. That window decides the
   reach; nothing you do on day two recovers a flat first hour.

Step 2 is not optional polish. An article without a companion post reaches
roughly the people who already visit your profile.

## What to publish

- **Article text:** `LinkedIn_Article_Polished.md` is canonical. Paste the prose
  into LinkedIn's editor and upload the images separately — LinkedIn does not
  resolve relative image paths.
- **Cover image:** `images/01_hero.png`.
- **Body images:** `02_pipeline`, `03_results`, `04_refusal`,
  `05_compaction_vs_compression`, `06_takeaway`, inserted at the section each
  one follows in the markdown.
- **Feed post:** one of the three variants in `LinkedIn_Post.md`. Post A leads
  with the refusal result and is the recommended default; B leads with cost for
  a more operational audience; C is short enough to be reshared.

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
  discovery and calibrated admission — not universal superiority.
- The reported reductions compare against an *uncompressed* baseline, so the
  token number is the part attributable to removing model boundaries.

Both mirror limitations stated in the paper. Dropping either would make the
article claim more than the evidence supports. The same two apply to the feed
posts; `LinkedIn_Post.md` records which variant omits which, and why that is
survivable there.

The article is deliberately written to make the refusal result the headline
rather than the efficiency numbers. That ordering is a claim about what the work
contributes, not a stylistic choice — the efficiency numbers tie with a
hand-written program, and the refusal result does not.
