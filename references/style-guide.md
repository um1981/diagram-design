# Style Guide

**The single source of truth for colors, typography, and tokens.** Every diagram draws from this — not from hex values inlined in other reference files. If you want to change the visual skin of Diagram Design, change this file.

Default skin is **Theme v2**: white paper, slate neutrals (jet-black ink, blue-slate muted), one atomic-tangerine accent, and quiet pastel semantics for roles, statuses and lanes. It's designed to look good out of the box; swap these values (or run [`onboarding.md`](onboarding.md)) and every new diagram inherits the new skin without touching any type-specific logic.

To generate your own from a website URL, see [`onboarding.md`](onboarding.md).

---

## Tokens

### Semantic roles — Theme v2 (white paper)

Every token is referred to by **semantic role**, not by its hex value. Type references (`type-*.md`) and SKILL.md say `accent`, not `#eb6c36`. **Use the opaque hexes below** (no `rgba()` tints) so PNG, Word, PowerPoint and draw.io all render the same colour.

| Role | Purpose | Light (default) | Dark (`template-dark.html`) |
|---|---|---|---|
| `paper` | Page **and** diagram background, label masks | `#FFFFFF` | `#161A23` |
| `paper-2` | Zone / container / framed-card fill | `#F7F9FC` | `#1D2230` |
| `node-fill` | Neutral tinted box (start/end ovals, legend chips, `service` role) | `#F3F5F9` | `#232937` |
| `ink` | Primary text, primary stroke, step-box border | `#2D3142` | `#E7EAF0` |
| `ink-strong` | Text on saturated fills | `#111111` | `#111111` |
| `muted` | Secondary text, default arrow stroke | `#4F5D75` | `#A7B0C2` |
| `soft` | Sublabels, eyebrows, boundary labels, tags on white | `#687389` | `#8C96AA` |
| `rule` | Hairlines, lane dividers, legend separator | `#E3E7EE` | `#2C3342` |
| `rule-solid` | Stronger borders, baselines, swatch outlines | `#CBD2DD` | `#3A4252` |
| `accent` | **Focal stroke/arrow — 1–2 elements max** | `#EB6C36` | `#F08A59` |
| `accent-text` | Text drawn in the accent colour (AA on white) | `#C4501C` | `#F4A27A` |
| `accent-tint` | Fill of the focal box | `#FDF0EA` | `#352A2B` |
| `link` | HTTP/API calls, external arrows | `#2E5AA8` | `#7FA6E3` |

Contrast on white: ink 12.9, muted 6.7, soft 4.8, accent-text 4.7, link 6.7 — every text role passes WCAG AA. Plain `accent` (3.1) is for strokes, arrows and fills only; orange **text** uses `accent-text`.

> **Note:** The `example-<type>.html` files in `assets/` are *layout* references built with the upstream skin (`#f5f5f5` paper, Geist / Instrument Serif). Copy their geometry and grammar, but always apply Theme v2 colours and the Sarabun rules below. `example-th-*.html` are the Theme v2 / Thai references.

### Colour discipline — one accent, quiet semantics

1. **Orange = the single editorial accent.** 1–2 elements per diagram (the focal node and/or the headline path). Never use it to mean "status" or "category".
2. **Semantic colours are pastel fills + mid-tone strokes**, never saturated blocks. They classify; they must not outshout the focal element.
3. **Status diagrams do not use orange.** When a diagram uses status colours (success / warning / error — typically state machines, approval lifecycles, error paths), drop the orange accent and mark the focal element with a **2px stroke** — `ink`, or the element's own status colour (e.g. the closing success state) — instead. See `assets/example-th-state.html`. Orange next to error-red reads as two alarms.
4. **One semantic system per diagram.** Pick role colours *or* status colours *or* lane colours as the primary classifier; a swimlane may add status colour only on its terminal steps.
5. Every semantic colour used appears in the legend; no unexplained colour.

### Role palette (architecture, integration, deployment, data flow)

Classify each box by its role. Focal overrides role (a focal ERP box is `accent-tint` / `accent`, not blue).

| Role | Use for | Fill (light) | Stroke | Tag / label text | Dark fill · stroke |
|---|---|---|---|---|---|
| `core` | ระบบหลัก / ERP (D365 F&SCM, BC) | `#EAF1FB` | `#2E5AA8` | `#24508F` | `#252E3E` · `#7FA6E3` |
| `service` | บริการภายใน (DMF, API, Logic App, batch) | `#F3F5F9` | `#4F5D75` | `#4F5D75` | `#2A2F39` · `#A7B0C2` |
| `external` | ระบบภายนอก (bank, POS, partner, SaaS) | `#FFFFFF` | `#8D96A8` dashed `4,3` | `#687389` | `#242934` · `#7D869A` |
| `people` | ผู้ใช้ / บุคคล / ทีม | `#F3F0FA` | `#6B5BA8` | `#5A4B96` | `#2B2C3D` · `#A99BE0` |
| `data` | ที่เก็บข้อมูล (DB, Data Lake, Dataverse, file share) | `#EAF6F5` | `#2A8C86` | `#1F736E` | `#203238` · `#5FC3BC` |
| `focal` | the 1–2 boxes to look at first | `#FDF0EA` | `#EB6C36` | `#C4501C` | `#352A2B` · `#F08A59` |

Type tags (`rx=2` chips) sit on a white fill with the role stroke and the role text colour.

### Status palette (state machine, approval, error paths)

| Status | Meaning (TH) | Fill | Stroke / dot | Text | Dark fill · stroke |
|---|---|---|---|---|---|
| `success` | สำเร็จ / อนุมัติ / ปิดงาน | `#E9F5EE` | `#2F855A` | `#276749` | `#203131` · `#5CC08A` |
| `warning` | รอ / ค้าง / เตือน | `#FDF6E3` | `#C08A1E` | `#8A6116` | `#322F29` · `#E0B34E` |
| `error` | ผิดพลาด / ปฏิเสธ / ยกเลิก | `#FCECEC` | `#C53030` | `#A12626` | `#35272F` · `#F07878` |
| `info` | ข้อมูล / ระบบดำเนินการ | `#EAF1FB` | `#2E5AA8` | `#24508F` | `#252E3E` · `#7FA6E3` |

Error/rejection connectors: `#C53030` stroke, dashed `5,4`, with a matching marker. Ordinary states stay white + `ink` stroke; colour only the states whose *status* is the message (terminal, waiting, failed).

### Lane palette (swimlane, story map, journey, grouped zones)

Up to 6 lanes, assigned in this order. The lane body is the light fill; the label column (or header band) uses the stronger tint; lanes are separated by a 2px **white** gap rather than a grey hairline. Step boxes inside lanes are **white** with an `ink` stroke so they float above the tint. Label masks inside a lane take the lane's body colour.

| # | Hue | Lane body | Label column / header | Dark body · header |
|---|---|---|---|---|
| 1 | ฟ้า | `#F2F6FC` | `#DCE7F6` | `#182030` · `#1B2840` |
| 2 | เขียว | `#F1F8F4` | `#D7EDDF` | `#182528` · `#1C322F` |
| 3 | เหลือง | `#FDF8EE` | `#F6E7C6` | `#272522` · `#3B3322` |
| 4 | ม่วง | `#F5F2FB` | `#E3DCF3` | `#1E2030` · `#292840` |
| 5 | เขียวน้ำทะเล | `#EFF8F7` | `#D2ECE9` | `#18252D` · `#1A3339` |
| 6 | ชมพู | `#FCF2F4` | `#F4DAE0` | `#261B28` · `#391C2F` |

More than 6 lanes → split the diagram (the swimlane budget is 6 anyway).

### Inversion rule (light → dark)

Use the Dark column of each table above — do not compute tints on the fly. Shadows stay out in both themes.

### Series palette (multi-series chart types only)

A small set of desaturated, editorial-tone colors for chart types that genuinely need to distinguish multiple overlapping entities (currently: **radar**). The "1-focal" rule still holds — `accent` is reserved for the focal series; the palette below covers the rest.

| Token | Light | Dark | Notes |
|---|---|---|---|
| `series-1` | `#7c8f6f` (sage) | `#9caf8f` | Non-focal series |
| `series-2` | `#5e7a9b` (dusty-blue) | `#82a0c0` | Non-focal series |
| `series-3` | `#b8915a` (mustard) | `#d3ad7a` | Non-focal series |
| `series-4` | `#9c6b50` (rust-brown) | `#b88670` | Non-focal series |
| `series-5` | `#6e6479` (slate) | `#8d8298` | Non-focal series |

Fills sit at `0.18` opacity light, `0.22` dark; strokes use the full color. **Don't backfill these tokens to non-chart types** — architecture, swimlane, etc. continue to use muted-ink variants. The series palette is opt-in for diagrams where overlapping shapes demand distinguishable color, not a license to add color elsewhere.

### Terminal skin (opt-in alternate)

A self-contained palette for the terminal-window primitive (see [primitive-terminal.md](primitive-terminal.md)) — a CLI-chrome register for dev-tool posts and technical social cards. It does not replace the default skin above and isn't affected by onboarding; it's a second, fixed skin you opt into per-diagram.

| Token | Hex | Purpose |
|---|---|---|
| `terminal-page` | `#0a0a0a` | Page background behind the window |
| `terminal-paper` | `#141414` | Window body, node fill |
| `terminal-bar` | `#1b1b1b` | Titlebar strip |
| `terminal-border` | `#2b2b2b` | Window border, hairlines |
| `terminal-ink` | `#f5f5f5` | Primary text, primary stroke (white-smoke) |
| `terminal-muted` | `#9a9a9a` | Secondary text, sublabels, ring stroke |
| `terminal-soft` | `#5c5c5c` | Tertiary — inactive dots, spokes |
| `terminal-accent` | `#ff5a36` | The one accent — focal station, prompt sign, active dot |
| `terminal-accent-tint` | `rgba(255,90,54,0.12)` | Fill for accent-bordered boxes |

**1-accent rule still holds.** Everything that isn't `terminal-ink` or `terminal-muted`/`terminal-soft` should be `terminal-accent` — never introduce a second hue.

---

## Typography

**One family: Sarabun** (Thai + Latin, Google Fonts, OFL) for every human-readable string — page title, node names, sublabels written as prose, eyebrows, arrow labels, legend, callouts, cards. **Geist Mono** is kept for *technical values only*: ports, URLs, paths, commands, table/field/class names, SQL types, versions, error codes. Never JetBrains Mono. Both families are bundled in `assets/fonts/` so PNG export renders identically offline.

| Role | Family | Size (Latin) | Size (Thai) | Weight | Notes |
|---|---|---|---|---|---|
| `title` (page H1) | Sarabun | 1.75–2rem | same | 600 | `line-height: 1.5` so stacked marks clear the line above |
| `node-name` | Sarabun | 12–13px | **13px** | 600 | 12px floor for Thai |
| `sublabel` (prose) | Sarabun | 10px | **12px** | 400 | `muted` |
| `sublabel` (technical value) | Geist Mono | 9px | — (keep Latin) | 400 | port, `SalesTable`, `/api/v1` |
| `type tag` (chip, `rx=2`) | Sarabun | 8px caps, tracked 0.08em | — (keep a Latin code) | 600 | `ERP`, `API`, `DB` |
| `eyebrow` / zone label | Sarabun | 9px caps, tracked 0.14em | 12px, **no** caps/tracking | 600 / 500 | |
| `arrow-label` | Sarabun | 9px caps, tracked 0.08em (≤14 chars) | 12px, **no** caps/tracking | 600 / 500 | Geist Mono 8px allowed for protocol codes (`HTTPS`, `gRPC`) |
| `legend` | Sarabun | 10–12px | 12px | 400 | legend title 600 |
| `callout` | Sarabun *italic* | 14px | 14px | 400 | editorial asides only |

### Font stack

```html
<link href="https://fonts.googleapis.com/css2?family=Sarabun:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Geist+Mono:wght@400;500;600&display=swap" rel="stylesheet">
```

```css
--font-sans:  'Sarabun', 'Leelawadee UI', 'Tahoma', system-ui, sans-serif;
--font-serif: var(--font-sans);   /* kept for template compatibility — titles are Sarabun 600 */
--font-mono:  'Geist Mono', ui-monospace, monospace;
```

In SVG: `font-family="'Sarabun', sans-serif"` and `font-family="'Geist Mono', monospace"`. Set `<html lang="th">` whenever the diagram contains Thai.

### Thai labels (Sarabun) — mandatory rules

Thai is not "Latin with different letters". Vowels and tone marks stack above and below the consonant, there are no spaces between words, and caps/tracking do not exist. These rules keep every Thai label legible and stop marks colliding.

**1. Measure, never estimate.** Combining vowels/tone marks have zero advance, `ำ` and `ะ` are wide, Latin inside a Thai label has its own advances. Run:

```bash
python3 scripts/measure_text.py "อนุมัติใบสั่งซื้อ" "Vendor invoice" --size 13 --weight 600
```

It prints the exact width (bundled Sarabun metrics), ascent/descent, a box width on the 4px grid (text + 2×12px padding) and the mask height. Rough planning figure only: Thai ≈ 0.55em per *base* character (marks excluded) at 600 weight.

**2. Vertical room (Sarabun, measured from the glyphs).**

| Content | Above baseline | Below baseline |
|---|---|---|
| Latin caps / digits | 0.72em | 0.05em (0.23em with g j p q y) |
| Thai with an upper vowel **or** tone mark (`ิ ี ่ ้` …), tall consonant (`ป ฝ ฟ ฬ`) | 0.98em | — |
| Thai **stacked** upper vowel + tone (`ที่ ซื้อ ชื่อ`) | **1.25em** | — |
| Thai lower vowel (`ุ ู`) or descender consonant (`ญ ฐ ฎ ฏ ฤ`) | — | **0.33em** |

Consequences:

- **Node box with Thai name + sublabel: ≥ 56px tall** (name baseline at `y+24`, sublabel baseline at `y+44`). With a type-tag row on top: **72px** (tag `y+8`, name baseline `y+44`, sublabel `y+62/63`).
- **Label mask for a 12px Thai label: 24px tall** (`ceil4(1.6em)`), text baseline at `mask_y + 17`. Keep the 6–10px gap to the connector (mask bottom = line − 8).
- **Line pitch for wrapped Thai ≥ 1.6em** (13px → 21px, 12px → 20px). This is the SVG equivalent of the "15pt line spacing" house rule: a tone mark on line 2 must never touch a descender on line 1. `measure_text.py --check` enforces it.

**3. Register switch in small slots.** Eyebrows, arrow labels, legend text and zone labels are 8–9px tracked caps for Latin. A Thai string in those slots becomes **12px Sarabun 500, `letter-spacing: 0`, no `text-transform`**, and its mask grows to 24px tall. Never apply `letter-spacing` or `uppercase` to Thai — tracking separates marks from their base consonant in some renderers. Latin labels in the same diagram keep their caps treatment.

**4. 12px floor.** No Thai below 12px anywhere. If a Thai name does not fit at 13px, shorten the wording (or widen the box on the grid) — never shrink the type.

**5. Line breaking.** Thai has no spaces between words; the browser will not wrap SVG text. Break manually with `<tspan x=… dy=…>` **only at word boundaries** (ผู้อนุมัติ / เห็นชอบหรือไม่?), never inside a syllable cluster, and keep each line ≤ ~18 Thai base characters in a node.

**6. Mixed Thai/English.** Keep ERP/product terms in English as users say them (PO, D365FO, Dataverse, Workflow); keep table/field names and codes in Geist Mono sublabels. Use Arabic numerals (100,000 บาท), not Thai digits.

**7. Masks match the surface beneath.** A label mask is the colour of whatever it sits on — `paper` on the canvas, the flattened tint inside a zone or lane (e.g. `#FFFFFF` on the canvas, `#F7F9FC` inside a zone, `#F2F6FC` inside lane 1). A paper-coloured mask on a tinted lane shows as a light patch. Keep masks off lane/zone border lines.

### Other scripts

Sarabun covers Thai, Latin and Vietnamese only. For Korean, Chinese or Cyrillic labels append the matching Noto family after Sarabun on that `<text>` (`'Sarabun', 'Noto Sans KR', sans-serif`), add it to the font link, and apply the same 12px floor and register switch as Thai.

---

## Stroke, radius, spacing

| Token | Value | Use |
|---|---|---|
| `stroke-thin` | `0.8` | Tag-box outlines, leaf nodes |
| `stroke-default` | `1` | Most strokes |
| `stroke-strong` | `1.2` | Emphasis strokes |
| `radius-sm` | `4` | Small tags |
| `radius-md` | `6` | Node boxes |
| `radius-lg` | `8` | Containers, rings |
| `grid` | `4` | Every coord, size, and gap is divisible by 4 (hard rule) |

---

## Node type → treatment

Semantic role combinations — reference these by name in type specs. Fills are opaque (Theme v2).

| Type | Fill | Stroke | Notes |
|---|---|---|---|
| `step` / `backend` (default box) | `paper` `#FFFFFF` | `ink` 1px | flowchart steps, swimlane/process steps, ordinary states |
| `focal` (1–2 max) | `accent-tint` `#FDF0EA` | `accent` `#EB6C36` | in status diagrams: white + `ink` 2px instead |
| `terminal` (start/end oval) | `node-fill` `#F3F5F9` | `soft` `#687389` | |
| `decision` (diamond) | `paper` | `ink` 1px | |
| role boxes | see **Role palette** | | architecture & friends |
| status states | see **Status palette** | | only states whose status is the message |
| `store` | `data` role | | |
| `external` | `#FFFFFF` | `#8D96A8` dashed `4,3` | |
| `input` / person | `people` role | | |
| `optional` | `paper` | `rule-solid` dashed `4,3` | |
| `security` boundary | `paper-2` | `accent` dashed `4,4` | the only non-focal use of orange: a trust boundary line, never filled |
| zone / region | `paper-2` `#F7F9FC` | `rule-solid` dashed `4,4` | label mask uses `paper-2` |

---

## Customizing the skin

Four options:

1. **Run onboarding** — see [`onboarding.md`](onboarding.md). Drop a URL; the skill extracts the palette + fonts and rewrites this file.
2. **Edit by hand** — change the hex values in the tables above. Run the pre-output taste gate afterward to verify the accent still reads as "focal" against the new paper color.
3. **Brand handoff** — paste your existing design-token JSON into a new section here and map its tokens to the semantic roles above.
4. **Client profiles** — save and switch named skins, or bind one to a project, using [`profiles.md`](profiles.md).

### Constraints (don't break these)

- **Contrast**: `ink` must hit WCAG AA on `paper`. `muted` must hit AA on `paper` for 11px+ text.
- **One accent**: pick one color for `accent`. Two accents erases the focal signal. Role/status/lane colours are classifiers, not accents — keep them pastel.
- **No rainbow palette**: if your brand ships 8 colors, pick 3 (paper, ink, accent). The rest become `muted` variants.
- **Sarabun + Geist Mono**: two families, fixed by house rule. Onboarding a brand changes *colours* only — typography stays Sarabun (Geist Mono for technical values).
- **Paper is white by default** (house rule: diagrams drop straight into Word / PowerPoint pages). A brand skin may use an off-white, but then every mask, PNG and draw.io background must use that same paper colour.
- **Dot pattern is optional, not default**: the 22×22 dot pattern is an opt-in "dotted paper" variant (good for long-form editorial hero diagrams). The default background is a clean `paper` fill, no pattern. When the pattern is enabled, it should sit at ~10% opacity of `ink` on `paper` — visible but quiet.
- **Container is clean by default**: the diagram sits directly on the page paper, no secondary container background or border. A framed variant (`paper-2` bg + `rule` border + 8px radius + padding) is available as an opt-in for card-heavy layouts, but don't reach for it by default — the extra chrome fights the figure.
