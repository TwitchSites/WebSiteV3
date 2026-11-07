# /brands/ — Brands We Endorse page

Flat pairing, same style as `/portfolio/` — logo file + `.txt` file sharing
the exact same name.

```
acme-airsoft.png
acme-airsoft.txt
```

If a brand ever needs more than one image, the same numbered-extras
convention as portfolio works here too (`acme-airsoft 2.png`).

## Template — acme-airsoft.txt

```
Title: Acme Airsoft
Description: One-liner shown under the logo on the Brands page
Breakdown: The full write-up shown on the brand's own page. Blank line = new paragraph.
Keywords: acme
Website: https://acmeairsoft.example.com
```

What it makes:
- **Brands page:** a backgroundless logo tile with the Description under it
  (2 across on a phone, 3-4 across on a PC). Tapping a tile opens the brand's page.
- **Brand page:** brand name at the top, the logo (plus any extra logos named
  `acme-airsoft 2.png`, `acme-airsoft 3.png`), the full Breakdown, a **Shop** button,
  a **Visit website** button, then a "from the gallery" strip.
- **Shop button:** shows when any product has `Brand: Acme Airsoft` (it jumps to a
  list of those products). With no products yet it becomes "Ask about Acme Airsoft".
- **Gallery strip:** every gallery post/video whose own `Keywords:` includes one of this
  brand's Keywords (or the brand name) is pulled in. Videos link to YouTube and to
  their gallery page; photos link to the gallery post they came from.
- `Website:` is the brand's own site (`Supplier Link:` still works too).

The product ↔ brand shop link is made by each product's own `Brand:` field (see
`/products/3d-printed/README.md`); the gallery link is made by matching Keywords.

## Important — logo is optional per product-linkage

If a brand referenced by a product's `Brand:` field doesn't have a matching
entry here (or has no image), it's simply skipped wherever brand logos would
normally show (e.g. on a build page) — no broken image, no placeholder text.

## Required fields

`Title` is always required. Everything else is optional.

## Priority (optional — controls the order)

Add a `Priority:` line to any entry's `.txt` file to choose where it appears:

```
Priority: 1
```

- **Lowest number goes first.** `1` is the top spot, then `2`, `3` and so on.
- Entries **without** a Priority line go **after** all the numbered ones, in A-Z order by title.
- Two entries with the same number are put in A-Z order by title.
- Gaps are fine (1, 5, 10) so you can slot something in later. Decimals work too (`1.5`).
- If the number is not a plain number (for example `top`), it is ignored and the entry is treated as having no Priority.

## Series (optional — keep related entries side by side)

Give two or more entries the same `Series:` line and they are kept next to each other, in their Priority order:

```
Series: Scylla HPA
```

- Use exactly the same words on every part (capitals do not matter).
- On the Gallery a series counts as one step in the photo, video, photo, video pattern, so part 1 and part 2 are never split by a photo.
- Everything else about each part stays the same: its own thumbnail, preview and page.
- Works in every folder: portfolio, products, brands.
- Give the parts the same Type so they land in the same section.
