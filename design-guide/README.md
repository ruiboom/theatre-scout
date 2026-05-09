# Theatre Scout — Design System

Theatre Scout is an independent listings site for the London stage — a contemporary, browse-led front-end over 87+ venues, with a planned AI extension and email/social channels. This system extracts the **Swiss Index** direction from the wireframe sketches: type-driven, rectilinear, monospace metadata, no chrome.

The aesthetic is **information-as-furniture**: every listing is a row in an index, every datum reads at a glance, no element competes with the show titles themselves.

> Sources: `Theatre Scout — Wireframes.html` (sketches/02-swiss.jsx) is the canonical reference for layout decisions and component composition.

---

## Index

| File / Folder | What it is |
|---|---|
| `theatre-scout.css` | Design tokens (colour, type, spacing, components) |
| `preview/` | Cards rendered in the Design System tab |
| `ui_kits/web/` | Hi-fi component recreations + click-thru index |
| `SKILL.md` | Skill manifest — load this in Claude Code or here |
| `assets/` | Logo mark, icon notes |

---

## Content fundamentals

**Voice.** Reserved, informational, slightly editorial. Theatre Scout speaks like a knowledgeable friend who keeps lists — never like a marketing site. Avoid hype words ("amazing", "must-see"). State facts; let the listings persuade.

**Casing.** Sentence case for body and section heads. **All-caps** is reserved for monospace metadata (status, dates, counts, type tags) and the indexed numerals (`01`, `02`, `0237`). Show titles always in title case as the venue presents them.

**Pronouns.** "We" for the Theatre Scout team, "you" for the reader. Sparing — most copy is third-person factual.

**Numbers.** Always tabular. Counts shown explicitly: `1,160 shows`, `87 venues`, `14 openings`. Numerals before nouns; "the week\\'s 1,160 listings" not "more than a thousand".

**Tone examples.**
- ✅ "Fourteen openings this week. Nine shows close on Sunday."
- ✅ "Theatre Scout doesn\\'t sell tickets. We link you to the venue\\'s box office."
- ❌ "Discover amazing shows you\\'ll love!"
- ❌ "London\\'s hottest theatre this week 🔥"

**Emoji.** Never. Use a monospace caret (`›`), arrow (`→`), or middot (`·`) instead.

**Datelines & timestamps.** ISO-style for monospace metadata: `2026.05.14 · 14:32`. Reading dates in body copy: `Tue 02 Jun — Sat 09 Aug 2026` (en-dash range).

---

## Visual foundations

**Palette.** Two primary tones: paper (`#fcfcfc`) and ink (`#0c0c0c`). Three greys: `--ts-ink-2 #2a2a2a` (secondary text), `--ts-mute #717171` (metadata), `--ts-hair #e6e6e6` (dividers). Two semantic *text-only* colours: `--ts-warn #b34a1c` (closing soon) and `--ts-good #1e6f3b` (now booking). Never used as backgrounds — Swiss restraint.

**Type pairing.** Space Grotesk (display + UI) + JetBrains Mono (metadata only). Two families, max.
- Display titles: 700 weight, line-height 0.9–0.94, letter-spacing −0.035em.
- UI body: 400/500.
- Mono: 500 weight, uppercase, letter-spacing +0.04em — **always**.

**Grid.** Page padding `32px` desktop / `16px` mobile. Internal gap `24px`. Card columns are even fractions; metadata columns are fixed widths (`60px` for index numbers, `120px` for date, `90px` for time). Indices left-pad with zeros: `001`, `0237`.

**Imagery.** Production stills used as supporting evidence, never hero. Square 1:1 thumbnails (`60–130px` mobile, `150–240px` desktop). Pure rectangles, no rounding, no shadow, no border. In wireframes: `repeating-linear-gradient(135deg, #ededed 0 8px, #f5f5f5 8px 16px)` placeholder until photography is available.

**Borders & rules.** Either `1px solid var(--ts-ink)` (section dividers, primary buttons, active chips) or `1px solid var(--ts-hair)` (row dividers, inactive chips). Never both at once.

**Radii.** Zero. `--ts-radius: 0`. The only curves in the system are the type itself.

**Shadows.** None. Depth is conveyed by inversion (ink-on-paper → paper-on-ink) and by rules.

**Buttons.** Square, monospace label, 10px×16px padding. Default is paper-on-paper with ink stroke; primary inverts to ink-on-paper. Hover = swap fills.

**Hover state.** Swap fill (ink ↔ paper), or add a 1px underline on text links (`text-underline-offset: 3px`). No opacity changes, no scale, no transition longer than 120ms.

**Press state.** Inherits hover; no scale-down. Active chips lock to the inverted state.

**Animation.** Almost none. Allowed: 120ms colour swaps, 180ms layout reflows on filter changes. Disallowed: parallax, fades-in on scroll, marquee scrolls, anything cinematic.

**Background.** Always paper. No textures, gradients, or images behind content. The only "image" the system uses regularly is the inverted ink block as a hero panel.

**Layout patterns.**
1. **Big-number panel** — a statistic at display size (`96px`), label in monospace caps. Used once per page to anchor.
2. **Indexed rail** — section number (`01`), title, item count, then 4–5 thumbs in a row.
3. **Index row** — `[index | thumb? | title | venue | dates | bookmark]` grid, hairline-divided.
4. **Spec sheet** — two- or three-column attribute table on the show page, hairline-bordered.

---

## Iconography

Stroke-only line icons, **1.5px stroke weight**, 24×24 viewBox, square caps and joins. The system uses a hand-picked subset of [Lucide](https://lucide.dev) (CDN-loadable). Filled icons are only used for the bookmark/saved state (toggle).

Common glyphs in this kit:
`search`, `filter` (3 horizontal lines decreasing in length), `bookmark`, `chevron-down`, `chevron-right`, `arrow-right`, `arrow-up-right`, `calendar`, `clock`, `grid`, `list`, `x`, `menu`.

No emoji. Decorative typographic glyphs allowed: `·` (middot, separators), `›` (right-pointing single quote, breadcrumbs), `→ ↗` (arrows, in monospace contexts only).

**Logo.** A square ink monogram `TS` at body-text size, positioned in the top-left of the bar. Tile is `20×20px` desktop, `16×16` mobile, no rounding, no margin around the letterforms beyond optical centering. Wordmark "Theatre Scout" sits to its right in `Space Grotesk 600 / 16px / -0.2em`.

---

## Caveats

- **Fonts** are loaded from Google Fonts — no local files. If the site needs offline/self-hosted, swap to woff2 versions.
- **No branded photography** — production stills are placeholders. Once we have approved imagery, drop into `assets/imagery/` and remove the striped backgrounds.
- **Accent colours** are deliberately absent. If the team wants one, propose a single hue (e.g. a desaturated orange `oklch(0.66 0.13 50)`) reserved for hover-underlines and progress bars only.
