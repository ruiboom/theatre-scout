---
name: theatre-scout-design
description: Use this skill to generate well-branded interfaces and assets for Theatre Scout, an independent listings site for the London stage. The system is "Swiss Index" — type-driven, rectilinear, monospace metadata, paper/ink tones, no chrome. Use for production or throwaway prototypes/mocks.
user-invocable: true
---

# Theatre Scout — Swiss Index

Read `README.md` for the full system: content fundamentals (voice, casing, datelines), visual foundations (palette, type, grid, components), and iconography.

## Files in this skill

- **`README.md`** — content + visual foundations, design rules, caveats
- **`theatre-scout.css`** — design tokens as CSS custom properties + helper classes (`.ts-meta`, `.ts-h1`, `.ts-btn`, `.ts-chip`, etc.)
- **`ui_kits/web/`** — hi-fi component recreations:
    - `index.html` — click-thru demo (browse → show detail)
    - `Bar.jsx`, `Tabs.jsx`, `BigNumber.jsx`, `IndexedRail.jsx`, `IndexRow.jsx`, `SpecSheet.jsx`, `Chip.jsx`, `Button.jsx`, `Bookmark.jsx`
- **`assets/`** — logo SVG (TS monogram)

## Working in this system

When generating an interface, mock, or component:

1. Always import `theatre-scout.css` first; design tokens live there.
2. Pick layout patterns from the README's "Layout patterns" section: big-number panel, indexed rail, index row, spec sheet.
3. Numerals always tabular (`font-feature-settings: "tnum"`). Indices zero-padded (`01`, `0237`).
4. Metadata is **always** in `JetBrains Mono`, **uppercase**, with `+0.04em` letter-spacing. Body type is in Space Grotesk.
5. No emoji. No radii. No shadows. No gradients.
6. Hero blocks invert (paper-on-ink) — that's the system's only "depth" mechanic.
7. Voice: reserved, factual, slightly editorial. Avoid marketing language.

If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out and create static HTML files. If working on production code, copy CSS tokens and read the rules to become an expert in designing with this brand.

If invoked without other guidance, ask the user what they want to build, then act as an expert designer outputting HTML artifacts or production code.
