# Export to PNG / SVG / draw.io

Convert a generated diagram HTML file into portable files next to it.

| Format | When | Command (from this skill's directory) |
|---|---|---|
| **PNG** | **Automatically after every diagram** (house rule — users paste diagrams into Word / PowerPoint) | `python3 scripts/export_png.py <file.html>` |
| **draw.io** (`.drawio`) | When the user asks for draw.io / an editable diagram, or offers to edit it themselves. Offer it once after delivering. | `python3 scripts/export_drawio.py <file.html>` |
| **SVG** | On request (Figma, Illustrator, inline in docs) | `python3 scripts/export_svg.py <file.html>` |

## Trigger

- Every finished diagram → PNG, no prompt needed.
- Natural-language requests: "export as PNG / SVG", "ขอไฟล์ draw.io", "เปิดแก้ใน draw.io", "ขอเป็นรูป", "rasterize it", "save as SVG".

## Scope

All three formats are **diagram-only** — just the `<svg>` node. Editorial wrappers (header, summary cards, footer in `-full` variants) are intentionally dropped (the draw.io export re-adds the page `<h1>` as a title cell). The deliverable is the diagram itself, suitable for slides, Word, Figma, social cards, or blog images.

The SVG-only export keeps the source `<title>` and `<desc>` with the diagram. Their per-diagram and per-variant prefixed IDs keep accessible names unique when several figures share a page.

Inlining several exported SVGs in one host document also requires namespaced `<defs>` IDs (markers, patterns, gradients, filters, clip paths, masks, symbols). The export procedure prefixes those IDs with the source file slug and rewrites matching `url(#…)` / `href="#…"` references, so a light figure next to its `-dark` twin does not silently share arrowheads. The accessible-name guarantee alone is not enough.

If the user explicitly asks for "a screenshot of the whole page including the cards", that's a different request — fall back to a normal full-page screenshot via the user's OS or browser.

## PNG export (automatic)

```bash
python3 scripts/export_png.py my-diagram.html                 # my-diagram.png at 2x
python3 scripts/export_png.py my-diagram.html --scale 3       # print / A4 handout
```

- PNG pixels = `viewBox` × scale (the SVG is laid out at exactly its viewBox width before capture), transparent outside the diagram's own paper rect.
- Fonts always come from `assets/fonts/` (Sarabun 400/500/600/700/italic, Geist Mono) — network is blocked during render, so the result is identical online or offline and Thai shaping is correct.
- Engines, tried in order: **Chromium** via Playwright (pixel-identical to a browser; uses Playwright's browser or a system Chrome/Chromium) → **resvg** (`resvg-py` wheel, HarfBuzz-grade Thai shaping, no browser needed; the script pip-installs it once if missing — pass `--no-install` to forbid). Motion diagrams are captured in their static frame.
- Exit code 3 means no engine could run: deliver the HTML (+ SVG) and tell the user the PNG could not be produced in this environment.
- **Look at the PNG** (open it with the image viewer / Read tool) before delivering — it is the fastest way to catch a clipped label or a mark touching a line.

## draw.io export (on request)

```bash
python3 scripts/export_drawio.py my-diagram.html              # my-diagram.drawio
python3 scripts/export_drawio.py my-diagram.html --body-pt 16 --title-pt 20
```

House sizing for draw.io: **node names 16pt, title 18–20pt** — the exporter scales the whole layout by `16 / node-name size` so proportions are kept, and adds the page title at `--title-pt`. Text cells use `fontFamily=Sarabun` (Geist Mono for technical values) with a Google Fonts `fontSource`, so draw.io renders them even where Sarabun is not installed. Multi-line Thai gets `line-height ≥ 1.6`.

Mapping (prints a fidelity ledger — relay it to the user in one line):

| SVG | draw.io |
|---|---|
| node `<rect>` (+ its paper mask) | rectangle vertex, `rx` kept, tint flattened over paper |
| texts and tag chips inside a box | child cells of that box (they move with it) |
| label mask + label | one text cell with the mask's paper background |
| diamond / triangle `<polygon>` | `rhombus` / `triangle` vertex |
| `<circle>` / `<ellipse>` | ellipse vertex (opacity kept, so Venn overlaps still read) |
| orthogonal `<line>` / elbow `<path>` | edge with waypoints, **glued** to the boxes it touches (exit/entry constraints) |
| curves, bands, icons, free polygons | embedded SVG image cell at the exact position (never dropped) |

The `.drawio` file is uncompressed XML — it opens in draw.io Desktop, diagrams.net, and the draw.io VS Code / Confluence integrations.

## SVG export

**Prefer the packaged helper.** From this skill's directory run:

```
python3 scripts/export_svg.py <html-file> [<out.svg>]
```

That script is the source of truth for the transform below (CSS carry-forward, defs ID namespacing, rgba normalization, and the class-without-style gate). Reimplement only when the helper is unavailable; keep the behaviour identical.

### Manual algorithm (what the helper does)

1. Read the source HTML file.
2. Extract the **first** `<svg ...>...</svg>` block. Use a multiline regex anchored on `<svg` and `</svg>`. Most generated diagrams have only one SVG; if there are multiple, the first is the diagram (gallery files are an exception — see *Edge cases*).
3. Make it standalone:
   - Ensure the opening tag has `xmlns="http://www.w3.org/2000/svg"`. Add it if missing.
   - Ensure a `viewBox` is present. The skill's templates always include one; warn the user if absent rather than guessing.
   - Preserve `role="img"`, `aria-labelledby`, and the first-child `<title>` / `<desc>` exactly as authored.
   - Rewrite HTML-only attribute syntax as XML: a valueless attribute (`<g data-motion-item>`) becomes `data-motion-item=""`, and an unquoted value gets double quotes. Comments and CDATA sections stay as written.
   - Set `id="<slug>-root"` on the opening `<svg>` tag, where `<slug>` is the source basename without extension (e.g. `example-loop.html` → `example-loop`). This ID scopes carried CSS so several inlined figures do not leak rules into each other.
4. **Carry page CSS into the SVG.** Class-styled diagrams (the loop family, process, medallion, data-flow, and others) declare fills and type in the page `<style>` block — `.station`, `.hub`, `.node-name`, and so on. Extracting the bare `<svg>` without those rules yields black boxes. Copy the page's diagram rules into a `<style>` inside `<defs>`, then:
   - Strip CSS comments first, so a comment in front of a rule does not become part of its selector.
   - Re-scope `:root { … }` custom properties onto `#<slug>-root` so the figure keeps its own tokens.
   - Start selectors that begin at the `<svg>` element at the root instead: `svg .zone` becomes `#<slug>-root .zone` and `svg text` becomes `#<slug>-root text`. The exported root element is the `<svg>` itself, so `#<slug>-root svg .zone` would match nothing.
   - Prefix every other kept selector with `#<slug>-root ` (e.g. `.station` → `#example-loop-root .station`).
   - **Drop** page chrome: `*`, `html`, `body`, `main`, `h1`/`h2`/`h3`, `p`, `.frame`, `.eyebrow`, `.summary`, `.card(s)`, `.footer`, `.header`, and the bare `svg { min-width: … }` layout rule. Only the bare `svg` selector is layout; `svg .zone` and `svg text` are diagram rules (see above). Those must not follow a fragment.
   - Carry `color` and `font-family` from the dropped `body` rule onto `#<slug>-root`. SVG content inherits both: `stroke="currentColor"` reads `color`, and text without its own font rule reads `font-family`.
   - **XML-escape** the carried CSS text (`&` → `&amp;`, `<` → `&lt;`) before inserting it into the SVG. Rule bodies can contain XML-sensitive characters (e.g. `content: "R&D"`); a bare `&` makes the standalone file fail to parse.
5. Inject Google Fonts `@import` so the SVG renders with correct typography in a browser. **XML-escape the `&` separators as `&amp;`** — a standalone `.svg` is parsed as strict XML, where a bare `&` starts an entity reference and makes the whole file fail to parse. (Don't copy the raw URL from the HTML `<link href>`; that ampersand form is only valid in HTML.) Merge into the same `<defs>` `<style>` as the carried rules (don't add a second `<defs>`):
     ```svg
     <defs>
       <style>@import url('https://fonts.googleapis.com/css2?family=Sarabun:ital,wght@0,400;0,500;0,600;0,700;1,400&amp;family=Geist+Mono:wght@400;500;600&amp;display=swap');
       /* …scoped diagram rules… */
       </style>
       <!-- existing markers / patterns stay here -->
     </defs>
     ```
6. **Namespace `<defs>` IDs.** Prefix every referenceable defs ID — on `marker`, `pattern`, `linearGradient`, `radialGradient`, `filter`, `clipPath`, `mask`, and `symbol` — with `<slug>-`, and rewrite matching `url(#…)` and `href="#…"` / `xlink:href="#…"` references. Rewrite **longest-id-first** so `arrow-accent` is not clipped by a shorter `arrow` rule. Example: `id="arrow"` in `example-loop.html` becomes `id="example-loop-arrow"` with `marker-end="url(#example-loop-arrow)"`.
7. Normalize colors for strict SVG 1.1 consumers. This design system's tokens are authored as `rgba(...)` (see `style-guide.md`) and render correctly wherever colors are read as CSS — browsers, Figma, Illustrator. PowerPoint's SVG importer does not: it treats `rgba(...)` and `transparent` as unrecognized and paints them **opaque black**, turning a barely-there tint into a solid block that swallows the label inside it. The transform is lossless (every replacement renders identically to the original in a browser), so apply it to presentation attributes before writing the file:

   ```python
   import re

   svg = re.sub(
       r'(fill|stroke)="rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d*\.?\d+)\s*\)"',
       lambda m: '{0}="#{1:02x}{2:02x}{3:02x}" {0}-opacity="{4}"'.format(
           m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4)), m.group(5)
       ),
       svg,
   )
   svg = re.sub(r'(fill|stroke)="transparent"', r'\1="none"', svg)
   ```

   The `\s*` around each channel tolerates a spaced `rgba(45, 49, 66, 0.03)` as well as the compact `rgba(45,49,66,0.03)` the templates normally use; `\d*\.?\d+` accepts an alpha value with or without a leading zero (both `0.03` and `.03` appear in shipped tokens). Matching is scoped to the `fill="..."` / `stroke="..."` presentation attribute. Class-styled diagrams may still carry `rgba(...)` inside the embedded `<style>` block via custom properties (e.g. `--accent-tint`); that form is correct in browsers and in Figma/Illustrator, and is out of scope for this presentation-attribute pass. (A brand's onboarded palette in `style-guide.md` could in principle add a third notation such as `hsl()`; none exists in any shipped token today, so this pass doesn't handle it — extend the regex if one is ever introduced.)
8. **Gate:** if the exported SVG still contains `class=` but no diagram CSS rules, stop and fix the CSS carry step — that fragment will render as black boxes. A fonts-only `<style>` (Google Fonts `@import` with no rules) does **not** satisfy the gate.
9. Prepend `<?xml version="1.0" encoding="UTF-8"?>\n` so the file is well-formed XML.
10. Write to `<basename>.svg` next to the source (e.g. `example-architecture.html` → `example-architecture.svg`). Honour an explicit output path if the user provides one.

### Caveat to surface to the user

Tools that don't fetch remote fonts at import time (offline Illustrator, some Figma import paths, older SVG viewers) will substitute typography. The SVG renders correctly in any modern browser. For pixel-perfect portability, recommend the PNG export.

## PNG export — manual fallback

`scripts/export_png.py` is the source of truth. Only if it cannot run, the manual Chromium equivalent is: open the HTML, inject `@font-face` rules pointing at `assets/fonts/*.ttf`, await `document.fonts.ready`, set the `<svg>` width to its viewBox width, release `overflow` on every ancestor, and screenshot the `<svg>` element with `omit_background=True` at `device_scale_factor` 2 (3 for print).

## Sizing the export

The PNG's pixel dimensions are the SVG's `viewBox` × `device_scale_factor`. So the size decision was already made when the diagram was drawn — see [`output-spec.md` §2](output-spec.md) for the presets. Export only picks the multiplier.

| Destination | Scale | Result from a 1280×720 `viewBox` |
|---|---|---|
| Docs, README, wiki | 2 | 2560×1440 |
| Slide deck (projected) | 2 | 2560×1440 |
| Print / PDF handout | 3 | 3840×2160 |
| Inline thumbnail, email | 1 | 1280×720 |

### Hitting an exact pixel size

When the user needs specific dimensions (an OG card at exactly 1200×630, a slide image at 1920×1080), compute the scale factor instead of guessing — Playwright accepts fractional values:

```
scale = target_width / viewBox_width
```

A 960-wide `viewBox` at a 1200px target is `scale=1.25`. Two rules:

- **Never scale below 1** to hit a small target — that soft-focuses the type. Redraw at a smaller preset instead.
- **Never scale past 4** — beyond that you're upscaling a layout that was designed for a smaller canvas; redraw at `slide-16x9` or a print preset.

If the target aspect ratio doesn't match the `viewBox` aspect ratio, say so and offer to redraw at the matching preset. Padding or cropping a finished diagram to fit a frame is not an export operation — it breaks the 40px safe margin.

## Edge cases

- **Source is `assets/index.html`** (the gallery, multiple SVGs in one file): refuse the export and ask the user which specific diagram file they meant. Don't guess.
- **No `<svg>` block found**: the source isn't a diagram file. Tell the user; don't write anything.
- **Surrounding HTML matters to the user**: they want cards/header in the image. Tell them this skill exports diagrams only, and recommend a browser-based full-page screenshot (or a separate PDF print).
- **Source is missing fonts at runtime**: Playwright will substitute, the screenshot will look off. Check that the source HTML has the `<link href="...fonts.googleapis.com...">` tag in `<head>`. If absent, the file isn't from a current template — fix the source rather than working around it in export.

## What this command never does

- Modifies the source HTML.
- Adds export buttons or `<script>` tags. Static diagrams remain script-free; an already motion-enabled source may retain the scoped controller from [`animation.md`](animation.md), but export never injects another controller.
- Auto-emits `.svg` or `.drawio` alongside HTML generation (PNG is the only automatic export).
- Embeds an HTML wrapper (cards, headers) into the SVG via `foreignObject`. Too fragile across renderers.
