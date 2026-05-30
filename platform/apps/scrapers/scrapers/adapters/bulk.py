"""Bulk-registered adapters using the GenericAdapter pattern.

Each entry: (slug, listings URL, card selector). The selector was discovered by
inspecting a saved fixture; bespoke parsing lives in its own module.

Slugs in `_JS_VENUES` route through the stealth (browser-rendered) fetch path
because the listing page is either JavaScript-rendered or the venue blocks
plain HTTP requests.
"""

from __future__ import annotations

from ..models import ShowType
from ._generic import GenericAdapter
from .registry import register

# Venues that need a real browser to render content (or to defeat anti-bot blocking).
# `hen-and-chickens` and `tabard` were initially added here but the stealth
# browser still couldn't reach them (DNS / cert issues, repeated timeouts).
# Keeping them in `_JS_VENUES` cost ~3 min per scrape on retries — drop instead.
_JS_VENUES: set[str] = {
    "seven-dials-playhouse",
}

# Venues whose programme is overwhelmingly stand-up/comedy. This is only the
# fallback default — JSON-LD type, site genre and title keywords (steps D and
# C) all still take precedence, so genuine plays/musicals here stay correct.
_DEFAULT_SHOW_TYPE: dict[str, ShowType] = {
    "backyard-comedy-club": "comedy",
    "hen-and-chickens": "comedy",
    "underbelly-boulevard": "comedy",
}

# (slug, url, selector). slug==key in theatres.yaml; almeida lives in its own file.
_ENTRIES: list[tuple[str, str, str]] = [
    # --- major ---
    ("bridge-theatre", "https://www.bridgetheatre.co.uk/whats-on/", 'a[href*="/whats-on/"]'),
    ("bush", "https://www.bushtheatre.co.uk/whats-on/", 'a[href*="/event/"]'),
    ("hampstead", "https://www.hampsteadtheatre.com/whats-on/main-stage/", 'a[href*="/whats-on/"]'),
    ("kiln", "https://kilntheatre.com/whats-on/", 'a[href*="/whats-on/"]'),
    ("menier-chocolate-factory", "https://www.menierchocolatefactory.com/whats-on/", ".tile"),
    ("national-theatre", "https://www.nationaltheatre.org.uk/whats-on/", 'a[href*="/whats-on/"]'),
    ("orange-tree", "https://orangetreetheatre.co.uk/whats-on/", 'a[href*="/whats-on/"]'),
    ("shakespeares-globe", "https://www.shakespearesglobe.com/whats-on/", "[class*=event-card]"),
    (
        "theatre-royal-stratford-east",
        "https://stratfordeast.com/whats-on/",
        'a[href*="/whats-on/"]',
    ),
    ("young-vic", "https://www.youngvic.org/whats-on", 'a[href*="/whats-on/"]'),
    # --- mid ---
    # artstheatrewestend.co.uk 301-redirects to the venue's current site.
    ("arts-theatre", "https://www.artsatmarblearch.com/events", ".c-event-card"),
    ("barbican", "https://www.barbican.org.uk/whats-on", 'a[href*="/whats-on/"]'),
    ("brixton-house", "https://brixtonhouse.co.uk/whats-on/", "li[class*=show]"),
    ("coronet", "https://www.thecoronettheatre.com/whats-on/", 'a[href*="/whats-on/"]'),
    ("gate", "https://www.gatetheatre.co.uk/our-work/", 'a[href*="/our-work/"]'),
    ("new-diorama", "https://newdiorama.com/whats-on/", 'a[href*="/whats-on/"]'),
    ("roundhouse", "https://www.roundhouse.org.uk/whats-on/", 'a[href*="/whats-on/"]'),
    (
        "seven-dials-playhouse",
        "https://www.sevendialsplayhouse.co.uk/whats-on",
        'a[href*="/whats-on/"]',
    ),
    ("other-palace", "https://theotherpalace.co.uk/whats-on/", "article"),
    ("underbelly-boulevard", "https://underbellyboulevard.com/tickets/", ".tile"),
    ("unicorn", "https://www.unicorntheatre.com/whats-on/", 'a[href*="/events/"]'),
    ("wiltons", "https://wiltons.org.uk/whats-on/", 'a[href*="/whats-on/"]'),
    # --- fringe ---
    ("backyard-comedy-club", "https://backyardcomedyclub.co.uk/events/", 'a[href*="/event/"]'),
    ("blue-elephant", "https://blueelephanttheatre.co.uk/whatson", "div.contentblock"),
    ("camden-peoples", "https://cptheatre.co.uk/whats-on", ".event"),
    ("cockpit", "https://www.thecockpit.org.uk/", 'a[href*="/show/"]'),
    ("finborough", "https://www.finboroughtheatre.co.uk/productions", 'a[href*="/productions/"]'),
    ("hen-and-chickens", "https://henandchickens.com/whats-on/", 'a[href*="/whats-on/"]'),
    ("jermyn-street", "https://www.jermynstreettheatre.co.uk/now-next/", 'a[href*="/show/"]'),
    ("kings-head", "https://kingsheadtheatre.com/whats-on", 'a[href*="/whats-on/"]'),
    ("tabard", "https://tabardtheatre.co.uk/whats-on/", 'a[href*="/whats-on/"]'),
    ("tara", "https://taratheatre.com/whats-on/", 'a[href*="/whats-on/"]'),
    ("theatre503", "https://theatre503.com/whats-on/", ".listing"),
    # --- outer ---
    ("alexandra-palace", "https://www.alexandrapalace.com/whats-on/", 'a[href*="/whats-on/"]'),
    ("greenwich", "https://greenwichtheatre.org.uk/whats-on/", 'a[href*="/events/"]'),
    ("polka", "https://polkatheatre.com/whats-on/", 'a[href*="/event/"]'),
    ("queens-hornchurch", "https://queens-theatre.co.uk/whats-on/", 'a[href*="/whats-on/"]'),
    ("rose-kingston", "https://www.rosetheatre.org/whats-on", 'a[href*="/whats-on/"]'),
]


def _make_adapter(slug: str, url: str, card_selector: str) -> type[GenericAdapter]:
    cls_name = "".join(p.title() for p in slug.split("-")) + "Adapter"
    cls = type(
        cls_name,
        (GenericAdapter,),
        {
            "slug": slug,
            "url": url,
            "card_selector": card_selector,
            "requires_js": slug in _JS_VENUES,
            "default_show_type": _DEFAULT_SHOW_TYPE.get(slug, "play"),
        },
    )
    return cls


def load() -> None:
    """Register every entry in the module. Called once from `adapters/__init__.py`."""
    for slug, url, sel in _ENTRIES:
        register(_make_adapter(slug, url, sel))
