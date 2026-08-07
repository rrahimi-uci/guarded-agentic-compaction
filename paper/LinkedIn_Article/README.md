# LinkedIn Article Package

`LinkedIn_Article_Polished.md` is the canonical article source. The `.docx` and
`.pdf` in this folder are legacy exports from an earlier package and no longer
match the markdown.

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

## Design system

`images/src/base.css` holds the whole system. Two rules matter:

- **Colour encodes identity, not magnitude.** The three chart series use
  validated categorical slots 1–3 (blue `#2a78d6`, orange `#eb6834`, aqua
  `#1baf7a`) — one hue per workflow family, never per value. Validator result:
  all checks pass; the one contrast warning on aqua (2.74:1) is discharged by
  direct value labels on every bar.
- **Semantic colours are reserved.** Red is refusal, green is the admitting
  exit. They are never reused as a series colour. The earlier figures gave each
  pipeline step its own arbitrary hue, which spent the colour channel on nothing.

## Archive

`images/_archive/` holds the superseded v1 and v2 image sets and their SVG
sources. Nothing references them; they are kept only for comparison.
