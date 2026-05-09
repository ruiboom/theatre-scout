"""One-off: fetch every theatre's listings page and classify it by what's parseable.

For each theatre in theatres.yaml, try a series of likely listings URLs.
Save the first 2xx response to tests/fixtures/<slug>.html.
Report:
    - whether application/ld+json with Event/TheaterEvent is present
    - whether the body looks JS-rendered (very small, mostly script tags)
    - a guessed event-card selector (h2/h3/article/[class*=event])

Usage: uv run python scripts/survey.py
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from scrapling.fetchers import FetcherSession
from scrapling.parser import Selector

from scout.theatres import load

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
FIXTURES.mkdir(parents=True, exist_ok=True)
USER_AGENT = "TheatreScout/0.1 (+local research bot)"

LISTING_PATHS = ["whats-on/", "whats-on", "events/", "events", "productions/", "shows/", ""]

EVENT_TYPES = {"Event", "TheaterEvent", "ComedyEvent", "DanceEvent", "MusicEvent", "Festival"}


def has_jsonld_events(html: str) -> int:
    page = Selector(html)
    count = 0
    for script in page.css('script[type="application/ld+json"]'):
        text = script.text or script.get_all_text()
        if not text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        for node in _flatten(data):
            t = node.get("@type")
            ts = [t] if isinstance(t, str) else (t or [])
            if any(x in EVENT_TYPES for x in ts):
                count += 1
    return count


def _flatten(d: Any) -> Iterator[dict[str, Any]]:
    if isinstance(d, list):
        for x in d:
            yield from _flatten(x)
    elif isinstance(d, dict):
        if "@graph" in d and isinstance(d["@graph"], list):
            yield from _flatten(d["@graph"])
        else:
            yield d


def looks_js_rendered(html: str) -> bool:
    """Strip script/style/noscript and see how much rendered text remains."""
    page = Selector(html)
    # Selector is read-only; collapse via CSS exclusion in get_all_text via ignore_tags.
    text = page.get_all_text(separator=" ", strip=True, ignore_tags=("script", "style", "noscript"))
    return len(text) < 800


def guess_event_selector(html: str) -> str:
    page = Selector(html)
    candidates = [
        "[class*=event-card]",
        "[class*=production-card]",
        "[class*=show-card]",
        "article.event",
        "article.production",
        "article.show",
        ".event-listing",
        ".whatson-item",
        ".event",
        ".production",
        ".show",
        "article",
    ]
    for sel in candidates:
        n = len(page.css(sel))
        if 3 <= n <= 100:
            return f"{sel} ({n})"
    return "(none)"


def fetch_first_ok(session: Any, base_url: str) -> tuple[str, str] | None:
    base = base_url if base_url.endswith("/") else base_url + "/"
    for path in LISTING_PATHS:
        url = urljoin(base, path)
        try:
            r = session.get(url, timeout=20)
        except Exception as exc:
            print(f"      {url}: ERROR {exc}")
            continue
        if r.status == 200 and r.body:
            return str(r.url), r.text or r.body.decode("utf-8", errors="replace")
        print(f"      {url}: {r.status}")
    return None


def main() -> None:
    theatres = load(ROOT / "theatres.yaml")
    rows: list[dict[str, Any]] = []
    with FetcherSession(impersonate="chrome", stealthy_headers=True) as session:
        for t in theatres:
            print(f"\n{t.slug:<32}  {t.url}")
            result = fetch_first_ok(session, str(t.url))
            if result is None:
                rows.append({"slug": t.slug, "status": "FETCH-FAIL", "url": str(t.url)})
                continue
            final_url, html = result
            (FIXTURES / f"{t.slug}.html").write_text(html, encoding="utf-8")
            n_jsonld = has_jsonld_events(html)
            js = looks_js_rendered(html)
            sel = guess_event_selector(html)
            row = {
                "slug": t.slug,
                "status": "ok",
                "final_url": final_url,
                "size": len(html),
                "jsonld_events": n_jsonld,
                "js_rendered": js,
                "selector_guess": sel,
            }
            rows.append(row)
            print(f"  -> {final_url}  size={len(html)}  jsonld={n_jsonld}  js={js}  sel={sel}")
            time.sleep(0.5)

    out = ROOT / "scripts" / "survey.json"
    out.write_text(json.dumps(rows, indent=2))
    print(f"\nWrote survey to {out}")
    print("\n=== Summary ===")
    by_status = {"jsonld": 0, "html": 0, "js": 0, "fail": 0}
    for r in rows:
        if r["status"] != "ok":
            by_status["fail"] += 1
        elif r.get("jsonld_events"):
            by_status["jsonld"] += 1
        elif r.get("js_rendered"):
            by_status["js"] += 1
        else:
            by_status["html"] += 1
    print(by_status)


if __name__ == "__main__":
    main()
