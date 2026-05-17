"""Battersea Arts Centre. Plain-HTML listings at /whats-on/ built on the same
`c-event-card` component as several Made Media venues — but here the first
heading inside a card is the *run dates*, not the title, so the generic
``h1, h2, h3`` title selector would pick "15 - 16 May". We point the title
selector at the explicit `.c-event-card__title` and let GenericAdapter handle
the rest (JSON-LD first, then cards, dates parsed from the card text).

Mirrors scout/adapters/battersea_arts_centre.py.
"""

from __future__ import annotations

from ._generic import GenericAdapter
from .registry import register


@register
class BatterseaArtsCentreAdapter(GenericAdapter):
    slug = "battersea-arts-centre"
    url = "https://bac.org.uk/whats-on/"
    card_selector = ".c-event-card"
    title_selector = ".c-event-card__title"
