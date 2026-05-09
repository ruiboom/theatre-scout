"""Bulk-registered adapters using the GenericAdapter pattern.

Each entry: (slug, listings URL, card selector). The selector was discovered by
inspecting a saved fixture; bespoke parsing lives in its own module.

Slugs in `_JS_VENUES` route through the stealth (browser-rendered) fetch path
because the listing page is either JavaScript-rendered or the venue blocks
plain HTTP requests.
"""

from __future__ import annotations

from scout.adapters._generic import GenericAdapter
from scout.adapters.registry import register

# Venues that need a real browser to render content (or to defeat anti-bot blocking).
# `hen-and-chickens` and `tabard` were initially added here but the stealth
# browser still couldn't reach them (DNS / cert issues, repeated timeouts).
# Keeping them in `_JS_VENUES` cost ~3 min per scrape on retries — drop instead.
_JS_VENUES: set[str] = {
    "seven-dials-playhouse",
    "yard",
    "vaults",
    "upstairs-at-the-gatehouse",
    "waterloo-east",
}

# (slug, url, selector). slug==key in theatres.yaml; almeida lives in its own file.
_ENTRIES: list[tuple[str, str, str]] = [
    # --- major ---
    ("bridge-theatre", "https://www.bridgetheatre.co.uk/whats-on/", 'a[href*="/whats-on/"]'),
    ("bush", "https://www.bushtheatre.co.uk/whats-on/", 'a[href*="/event/"]'),
    ("donmar-warehouse", "https://www.donmarwarehouse.com/whats-on/", 'a[href*="/events/"]'),
    ("hampstead", "https://www.hampsteadtheatre.com/whats-on/main-stage/", 'a[href*="/whats-on/"]'),
    ("kiln", "https://kilntheatre.com/whats-on/", 'a[href*="/whats-on/"]'),
    ("lyric-hammersmith", "https://lyric.co.uk/whats-on/", 'a[href*="/shows/"]'),
    ("menier-chocolate-factory", "https://www.menierchocolatefactory.com/whats-on/", ".tile"),
    ("national-theatre", "https://www.nationaltheatre.org.uk/whats-on/", 'a[href*="/whats-on/"]'),
    ("old-vic", "https://www.oldvictheatre.com/productions/", 'a[href*="/productions/"]'),
    ("open-air-theatre", "https://openairtheatre.com/whats-on/", "article"),
    ("orange-tree", "https://orangetreetheatre.co.uk/whats-on/", 'a[href*="/whats-on/"]'),
    ("royal-court", "https://royalcourttheatre.com/whats-on/", 'a[href*="/events/"]'),
    ("sadlers-wells", "https://www.sadlerswells.com/whats-on/", 'a[href*="/whats-on/"]'),
    ("shakespeares-globe", "https://www.shakespearesglobe.com/whats-on/", "[class*=event-card]"),
    ("soho-theatre", "https://sohotheatre.com/dean-street/", 'a[href*="/events/"]'),
    (
        "theatre-royal-stratford-east",
        "https://stratfordeast.com/whats-on/",
        'a[href*="/whats-on/"]',
    ),
    ("young-vic", "https://www.youngvic.org/whats-on", 'a[href*="/whats-on/"]'),
    # --- mid ---
    ("arcola", "https://www.arcolatheatre.com/whats-on/", 'a[href*="/event/"]'),
    ("barbican", "https://www.barbican.org.uk/whats-on", 'a[href*="/whats-on/"]'),
    ("brixton-house", "https://brixtonhouse.co.uk/whats-on/", "li[class*=show]"),
    ("charing-cross", "https://charingcrosstheatre.co.uk/", 'a[href*="/whats-on/"]'),
    ("coronet", "https://www.thecoronettheatre.com/whats-on/", 'a[href*="/whats-on/"]'),
    ("gate", "https://www.gatetheatre.co.uk/our-work/", 'a[href*="/our-work/"]'),
    ("hackney-empire", "https://www.hackneyempire.co.uk/whats-on", 'a[href*="/events/"]'),
    ("marylebone", "https://www.marylebonetheatre.com/", "[class*=production-item]"),
    ("new-diorama", "https://newdiorama.com/whats-on/", 'a[href*="/whats-on/"]'),
    ("riverside-studios", "https://riversidestudios.co.uk/whats-on/", 'a[href*="/event/"]'),
    ("roundhouse", "https://www.roundhouse.org.uk/whats-on/", 'a[href*="/whats-on/"]'),
    (
        "seven-dials-playhouse",
        "https://www.sevendialsplayhouse.co.uk/whats-on",
        'a[href*="/whats-on/"]',
    ),
    ("other-palace", "https://theotherpalace.co.uk/whats-on/", "article"),
    (
        "yard",
        "https://www.theyardtheatre.co.uk/whats-on",
        'a[href*="/events/"]:not([href*="/tickets/"])',
    ),
    ("underbelly-boulevard", "https://underbellyboulevard.com/tickets/", ".tile"),
    ("unicorn", "https://www.unicorntheatre.com/whats-on/", 'a[href*="/events/"]'),
    ("wiltons", "https://wiltons.org.uk/whats-on/", 'a[href*="/whats-on/"]'),
    # --- fringe ---
    ("camden-peoples", "https://cptheatre.co.uk/whats-on", ".event"),
    ("cockpit", "https://www.thecockpit.org.uk/", 'a[href*="/show/"]'),
    ("drayton-arms", "https://thedraytonarmstheatre.co.uk/index.php", 'a[href*="/show/"]'),
    ("etcetera", "https://www.etceteratheatrecamden.com/events/", 'a[href*="/event/"]'),
    ("finborough", "https://www.finboroughtheatre.co.uk/productions", 'a[href*="/productions/"]'),
    ("hen-and-chickens", "https://henandchickens.com/whats-on/", 'a[href*="/whats-on/"]'),
    ("jermyn-street", "https://www.jermynstreettheatre.co.uk/now-next/", 'a[href*="/show/"]'),
    ("kings-head", "https://kingsheadtheatre.com/whats-on", 'a[href*="/whats-on/"]'),
    ("old-red-lion", "https://weareoldred.co.uk/", 'a[href*="/event/"]'),
    ("omnibus", "https://www.omnibus-clapham.org/", 'a[href*="/event/"]'),
    ("southwark-playhouse", "https://southwarkplayhouse.co.uk/", 'a[href*="/productions/"]'),
    ("tabard", "https://tabardtheatre.co.uk/whats-on/", 'a[href*="/whats-on/"]'),
    ("tara", "https://taratheatre.com/whats-on/", 'a[href*="/whats-on/"]'),
    ("vaults", "https://www.thevaults.london/whats-on", 'a[href*="/event"]'),
    ("tower", "https://www.towertheatre.org.uk/whats-on/", 'a[href*="/event/"]'),
    ("union", "https://uniontheatre.biz/whats-on/", 'a[href*="/show/"]'),
    (
        "upstairs-at-the-gatehouse",
        "https://upstairsatthegatehouse.com/whats-on/",
        'a[href*="/show"]',
    ),
    ("waterloo-east", "https://www.waterlooeast.co.uk/", 'a[href*="/show"]'),
    ("white-bear", "https://www.whitebeartheatre.co.uk/", 'a[href*="/show/"]'),
    # --- outer ---
    ("alexandra-palace", "https://www.alexandrapalace.com/whats-on/", 'a[href*="/whats-on/"]'),
    ("bloomsbury", "https://www.bloomsburytheatre.com/whats-on/", 'a[href*="/event/"]'),
    (
        "churchill",
        "https://trafalgartickets.com/churchill-theatre-bromley/en-GB",
        'a[href*="/event/"]',
    ),
    ("eventim-apollo", "https://www.eventimapollo.com/events/", 'a[href*="/events/"]'),
    ("greenwich", "https://greenwichtheatre.org.uk/whats-on/", 'a[href*="/events/"]'),
    (
        "new-wimbledon",
        "https://www.atgtickets.com/venues/new-wimbledon-theatre/whats-on/",
        'a[href*="/shows/"]',
    ),
    ("polka", "https://polkatheatre.com/whats-on/", 'a[href*="/event/"]'),
    ("queens-hornchurch", "https://queens-theatre.co.uk/whats-on/", 'a[href*="/whats-on/"]'),
    (
        "richmond",
        "https://www.atgtickets.com/venues/richmond-theatre/whats-on/",
        'a[href*="/shows/"]',
    ),
    ("rose-kingston", "https://www.rosetheatre.org/whats-on", 'a[href*="/whats-on/"]'),
    ("troubadour-canary-wharf", "https://troubadour.com/canary-wharf/", 'a[href*="/event/"]'),
    ("troubadour-wembley-park", "https://troubadour.com/wembley-park/", 'a[href*="/event/"]'),
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
        },
    )
    register(cls)
    return cls


for _slug, _url, _sel in _ENTRIES:
    _make_adapter(_slug, _url, _sel)
