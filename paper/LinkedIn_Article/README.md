# LinkedIn Article Package

| File | What it is |
| --- | --- |
| `LinkedIn_Article_Polished.md` | the article — canonical source |
| `LinkedIn_Post.md` | companion feed posts, three variants, plus the first comment |
| `LINKEDIN_PUBLICATION_NOTES.md` | how to upload it |
| `images/` | six figures, HTML sources, and the shared design system |

There is no `.docx` or `.pdf` in this folder. Earlier exports were removed because
they had drifted to a superseded image set and the old paper title, which made it
possible to publish from the wrong file. Regenerate on demand — see *Exporting*.

The article alone is not the deliverable. A LinkedIn article gets very little
organic distribution without a feed post pointing at it, which is what
`LinkedIn_Post.md` is for.

## Figures

Six figures, each with a distinct job — no two present the same numbers:

| File | Job | Page size |
| --- | --- | --- |
| `images/01_hero.png` | cover: traces → gate → compiled prefix or baseline | 1920×1080 |
| `images/02_pipeline.png` | the five-stage cascade and what makes each stage refuse | 1800×820 |
| `images/03_results.png` | **chart** — per-family reduction across five metrics | 1800×1080 |
| `images/04_refusal.png` | **chart** — every stage passes, calibration still refuses | 1800×1080 |
| `images/05_compaction_vs_compression.png` | why compaction and compression are different axes | 1800×1120 |
| `images/06_takeaway.png` | keeps / changes / refuses | 1800×940 |

All are rendered at **2× (retina)**, so a 1800×1080 page ships as 3600×2160.

## Regenerating

```bash
cd images/src
./render.sh              # all six
./render.sh 03_results   # just one
```

Sources are HTML + one shared `base.css`, rendered by headless Chrome.

**Why HTML rather than SVG.** The previous figures were hand-authored SVG with
hard-coded `<tspan>` line breaks and no text measurement. Four of six overflowed
their cards — body copy ran past card borders, and the hero's overlapping trace
cards clipped each other's text mid-word (`fe…`, `clas…`). Here every text
container is a real flex/grid box and the browser performs the layout, so a
string that is too long for its box wraps instead of spilling. `body.figure` also
sets `overflow: hidden`, which makes any remaining overflow visible in the
rendered PNG rather than silently clipped.

## Exporting

The markdown is canonical. Earlier `.docx` / `.pdf` exports were removed: they
had drifted to a superseded image set, the old paper title, and pre-Headroom
text, which made it possible to publish from the wrong file. Regenerate on
demand instead:

```bash
pandoc LinkedIn_Article_Polished.md -o LinkedIn_Article.docx --resource-path=.
```

The result embeds the 2x figures and lands around 4.6 MB, which is why it is
not kept in the repository. There is no supported PDF export path — pandoc's
LaTeX engine exits zero without producing a file on this document.

## Design system

`images/src/base.css` holds the whole system. Two rules matter:

- **Colour encodes identity, not magnitude.** The three chart series use
  categorical slots 1–3 (blue `#2a78d6`, orange `#eb6834`, violet `#6a4fc9`) —
  one hue per workflow family, never per value. Validator result: all six checks
  pass, worst adjacent normal-vision ΔE 33.0, and every slot clears 3:1 against
  the surface.
- **Semantic colours are reserved.** Red is refusal, green is the admitting exit.
  They are never reused as a series colour. This was not true until recently:
  `--series-3` was `#1baf7a`, byte-identical to `--admit`, so green meant
  "backlog-attention family" in `03_results` and "admitted" in the hero and the
  refusal figure. Violet fixes the collision and validates better — the aqua sat
  on a 2.74:1 contrast warning that direct labels had to discharge.
- **Headline numbers wear ink, not series colour.** The hero's four KPI figures
  were painted in the categorical hues, which made blue mean "issue-type family"
  in the results chart and "provider requests" in the hero. They are `--ink` now;
  the colour channel is spent only where identity actually exists.

## Archive

`images/_archive/` holds the superseded v1 and v2 image sets and their SVG
sources. Nothing references them; they are kept only for comparison.
