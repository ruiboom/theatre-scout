# Web UI Kit · Theatre Scout

Click-thru recreation of the Swiss Index direction.

- **Browse landing** — hero with big numbers, indexed rails of 4 cards, view-switcher (rails / list / calendar), filter overlay.
- **Show detail** — display title, two-column spec sheet, related rail.

## Files

- `index.html` — entry; loads CSS, React, and the three babel scripts in order.
- `components.jsx` — `Bar`, `Tabs`, `BigNumber`, `Thumb`, `IndexedRail`, `IndexRow`, `SpecSheet`, `Button`, `FilterPanel`. All exported to `window`.
- `data.jsx` — `SHOWS`, `RAILS` fixtures.
- `app.jsx` — `ScreenBrowse`, `ScreenShow`, `App`. Mounts `#root`.

## Component cheatsheet

| Component | Purpose |
|---|---|
| `<Bar>` | Sticky monospace header with TS monogram and live counts |
| `<BigNumber kicker n sub>` | Statistic block with mono kicker + display numeral |
| `<IndexedRail idx title count items onOpen>` | Numbered section with 4 cards |
| `<IndexRow idx show onOpen>` | Single dense list row |
| `<SpecSheet rows>` | `[label, value]` pairs with hairline dividers |
| `<Tabs items active onChange>` | Chip-style segmented control |
| `<Button primary>` | Square monospace button. `primary` = inverted |
| `<FilterPanel open onClose>` | Right-edge overlay, mono labels, chip groups |
