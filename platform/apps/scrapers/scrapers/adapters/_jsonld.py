"""schema.org JSON-LD extraction. Pure functions only.

Ported from scout/adapters/_jsonld.py — same Event-type mapping and price
extraction. Adapter-facing API: `parse_jsonld(html, theatre_slug, base_url) ->
list[Show]`.
"""

from __future__ import annotations

import json
import logging
import urllib.parse
from datetime import date
from typing import Any

from scrapling.parser import Selector

from ..classify import classify
from ..models import Show, ShowType
from ..text import clean_description, clean_text

log = logging.getLogger(__name__)

# Specific schema.org event types we trust as authoritative.
SPECIFIC_EVENT_TYPE_TO_SHOW_TYPE: dict[str, ShowType] = {
    "ComedyEvent": "comedy",
    "DanceEvent": "dance",
    "MusicEvent": "other",
    "Festival": "other",
    "ScreeningEvent": "other",
}

# Generic event types: recognised as events, but too vague to trust for
# show_type — venues routinely wrap stand-up, plays and musicals all in
# TheaterEvent. Fall through to the heuristic classifier instead.
AMBIGUOUS_EVENT_TYPES: frozenset[str] = frozenset({"Event", "TheaterEvent"})


def parse_jsonld(html: str, theatre_slug: str, base_url: str) -> list[Show]:
    page = Selector(html)
    shows: list[Show] = []
    for script in page.css('script[type="application/ld+json"]'):
        text = script.text or script.get_all_text()
        if not text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        for node in _flatten(data):
            show = _node_to_show(node, theatre_slug, base_url)
            if show is not None:
                shows.append(show)
    return shows


def _flatten(data: Any) -> list[dict[str, Any]]:
    """Yield dict nodes from JSON-LD: handle arrays, @graph wrappers, single objects."""
    out: list[dict[str, Any]] = []
    if isinstance(data, list):
        for item in data:
            out.extend(_flatten(item))
    elif isinstance(data, dict):
        if "@graph" in data and isinstance(data["@graph"], list):
            out.extend(_flatten(data["@graph"]))
        else:
            out.append(data)
    return out


def _specific_show_type(types: list[str]) -> ShowType | None:
    for t in types:
        if t in SPECIFIC_EVENT_TYPE_TO_SHOW_TYPE:
            return SPECIFIC_EVENT_TYPE_TO_SHOW_TYPE[t]
    return None


def _node_to_show(node: dict[str, Any], theatre_slug: str, base_url: str) -> Show | None:
    types = _types_of(node)
    specific = _specific_show_type(types)
    if specific is None and not any(t in AMBIGUOUS_EVENT_TYPES for t in types):
        return None

    name = clean_text(node.get("name") or "")
    url = node.get("url")
    if not name or not url:
        return None
    full_url = urllib.parse.urljoin(base_url, url)
    description = clean_description(node.get("description") or "")

    # A specific type wins outright; a generic Event/TheaterEvent is too vague
    # to trust, so reclassify from name + description heuristically.
    show_type = specific if specific is not None else classify(f"{name} {description}")

    try:
        return Show(
            theatre_slug=theatre_slug,
            title=name,
            show_type=show_type,
            description=description,
            url=full_url,
            start_date=_parse_date(node.get("startDate")),
            end_date=_parse_date(node.get("endDate")),
            price_min=_extract_price(node, "lowPrice") or _extract_price(node, "price"),
            price_max=_extract_price(node, "highPrice"),
            image_url=_extract_image(node.get("image"), base_url),
        )
    except Exception as exc:
        log.warning("jsonld: failed to build Show for %s: %s", name, exc)
        return None


def _types_of(node: dict[str, Any]) -> list[str]:
    t = node.get("@type")
    if isinstance(t, str):
        return [t]
    if isinstance(t, list):
        return [s for s in t if isinstance(s, str)]
    return []


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _extract_price(node: dict[str, Any], field: str) -> int | None:
    """Extract price in pence. Looks at top-level and nested `offers`."""
    candidates: list[Any] = [node.get(field)]
    offers = node.get("offers")
    if isinstance(offers, dict):
        candidates.append(offers.get(field))
    elif isinstance(offers, list):
        for o in offers:
            if isinstance(o, dict):
                candidates.append(o.get(field))
    for c in candidates:
        if c is None or c == "":
            continue
        try:
            return int(round(float(c) * 100))
        except (TypeError, ValueError):
            continue
    return None


def _extract_image(value: Any, base_url: str) -> str | None:
    if not value:
        return None
    if isinstance(value, str):
        return urllib.parse.urljoin(base_url, value)
    if isinstance(value, list) and value:
        return _extract_image(value[0], base_url)
    if isinstance(value, dict):
        url = value.get("url") or value.get("contentUrl")
        if isinstance(url, str):
            return urllib.parse.urljoin(base_url, url)
    return None
