"""Per-fixture inspector. Suggests a card selector by scoring candidates.

Heuristic: for each candidate selector, count matches that contain BOTH
a link to a show-detail URL AND look like an event card (has h1/h2/h3 + image).
Pick the selector with the highest sensible match count.

Usage: uv run python scripts/inspect_fixtures.py
"""

from __future__ import annotations

import json
from pathlib import Path

from scrapling.parser import Selector

from scout.theatres import load

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"

CANDIDATES = [
    # specific patterns
    "[class*=event-card]",
    "[class*=show-card]",
    "[class*=production-card]",
    "[class*=card-event]",
    "[class*=event-item]",
    "[class*=show-item]",
    "[class*=production-item]",
    "[class*=event-listing]",
    "[class*=eventcard]",
    ".whatson-item",
    ".event-list-item",
    # less specific
    ".event",
    ".show",
    ".production",
    ".whatson",
    ".tile",
    # structural
    "article",
    "li.event",
    "li.show",
    "li.production",
    "li[class*=event]",
    "li[class*=show]",
    "li[class*=production]",
    # link-based
    'a[href*="/whats-on/"]',
    'a[href*="/show/"]',
    'a[href*="/shows/"]',
    'a[href*="/event/"]',
    'a[href*="/events/"]',
    'a[href*="/production/"]',
    'a[href*="/productions/"]',
]


def score_selector(page: Selector, sel: str) -> tuple[int, int]:
    """Returns (n_matches, n_with_title_and_link)."""
    matches = page.css(sel)
    n = len(matches)
    if n == 0:
        return 0, 0
    good = 0
    for m in matches:
        # If selector is a link, treat the link itself as the card
        if sel.startswith("a["):
            if m.get_all_text(strip=True):
                good += 1
            continue
        title = m.css("h1, h2, h3, h4").first
        link = m.css("a[href]").first
        if title is not None and link is not None:
            good += 1
    return n, good


def best_selector(html: str) -> tuple[str, int] | None:
    page = Selector(html)
    best = None
    best_score = 0
    for sel in CANDIDATES:
        n, good = score_selector(page, sel)
        # Prefer 5-100 matches, mostly with title+link
        if 3 <= good <= 100 and good > best_score:
            best_score = good
            best = (sel, good)
    return best


def main() -> None:
    theatres = load(ROOT / "theatres.yaml")
    out: dict[str, dict] = {}  # type: ignore[type-arg]
    for t in theatres:
        path = FIXTURES / f"{t.slug}.html"
        if not path.is_file():
            print(f"{t.slug:<32}  (no fixture)")
            continue
        html = path.read_text(encoding="utf-8")
        result = best_selector(html)
        if result:
            sel, n = result
            print(f"{t.slug:<32}  {sel:<35}  ({n})")
            out[t.slug] = {"selector": sel, "matches": n}
        else:
            print(f"{t.slug:<32}  (no good selector)")
            out[t.slug] = {"selector": None, "matches": 0}

    (ROOT / "scripts" / "selectors.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
