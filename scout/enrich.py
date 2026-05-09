"""Pull description and image URL from a show's detail page. Pure functions."""

from __future__ import annotations

import json
import re
import urllib.parse
from typing import Any

from scrapling.parser import Selector

from scout.text import clean_description, clean_text, is_boilerplate

EVENT_TYPES = {"Event", "TheaterEvent", "ComedyEvent", "DanceEvent", "MusicEvent", "Festival"}
DESC_MAX_CHARS = 600
_TINY_IMG_RE = re.compile(r"(spacer|pixel|blank|tracking|1x1|\.gif$)", re.IGNORECASE)


def _jsonld_nodes(page: Selector) -> list[dict[str, Any]]:
    """All JSON-LD payloads on the page, flattened to dict nodes."""
    out: list[dict[str, Any]] = []
    for script in page.css('script[type="application/ld+json"]'):
        text = script.text or script.get_all_text()
        if not text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        out.extend(_flatten(data))
    return out


def extract_description(html: str) -> str:
    """Best-effort description from a show detail page. Returns "" if nothing usable."""
    page = Selector(html)

    # 1. JSON-LD Event description
    for node in _jsonld_nodes(page):
        types = node.get("@type")
        ts = [types] if isinstance(types, str) else (types or [])
        if any(t in EVENT_TYPES for t in ts):
            raw = node.get("description")
            if isinstance(raw, str):
                cleaned = clean_description(raw)
                if len(cleaned) >= 30:
                    return _truncate(cleaned)

    # 2. Meta tags
    for sel in ['meta[name="description"]', 'meta[property="og:description"]']:
        m = page.css(sel).first
        if m is not None:
            content = m.attrib.get("content")
            if isinstance(content, str):
                cleaned = clean_description(content)
                if len(cleaned) >= 30:
                    return _truncate(cleaned)

    # 3. First meaningful <p> within main/article
    for container_sel in ["main article", "main", "article"]:
        container = page.css(container_sel).first
        if container is None:
            continue
        for p in container.find_all("p"):
            text = clean_text(p.get_all_text(separator=" ", strip=True))
            if len(text) >= 60 and not is_boilerplate(text):
                return _truncate(text)

    return ""


def extract_image(html: str, base_url: str) -> str | None:
    """Best-effort hero image URL from a show detail page. Returns None if nothing usable."""
    page = Selector(html)

    # 1. JSON-LD Event image — usually the canonical poster
    for node in _jsonld_nodes(page):
        types = node.get("@type")
        ts = [types] if isinstance(types, str) else (types or [])
        if any(t in EVENT_TYPES for t in ts):
            url = _coerce_image_field(node.get("image"))
            if url:
                return urllib.parse.urljoin(base_url, url)

    # 2. Open Graph + Twitter card images (next-best canonical signal)
    for sel in ['meta[property="og:image"]', 'meta[name="twitter:image"]']:
        m = page.css(sel).first
        if m is not None:
            content = m.attrib.get("content")
            if isinstance(content, str) and content.strip():
                return urllib.parse.urljoin(base_url, content.strip())

    # 3. First non-trivial <img> in main content
    for container_sel in ["main article", "main", "article"]:
        container = page.css(container_sel).first
        if container is None:
            continue
        for img in container.find_all("img"):
            src = img.attrib.get("src") or img.attrib.get("data-src")
            if not isinstance(src, str) or not src:
                continue
            if _TINY_IMG_RE.search(src):
                continue
            return urllib.parse.urljoin(base_url, src)

    return None


def _coerce_image_field(value: Any) -> str | None:
    """JSON-LD `image` can be a string, an object with .url, or an array of either."""
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, list):
        for item in value:
            url = _coerce_image_field(item)
            if url:
                return url
    if isinstance(value, dict):
        for key in ("url", "contentUrl"):
            v = value.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return None


def _flatten(data: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if isinstance(data, list):
        for x in data:
            out.extend(_flatten(x))
    elif isinstance(data, dict):
        if "@graph" in data and isinstance(data["@graph"], list):
            out.extend(_flatten(data["@graph"]))
        else:
            out.append(data)
    return out


def _truncate(text: str) -> str:
    if len(text) <= DESC_MAX_CHARS:
        return text
    return text[:DESC_MAX_CHARS].rsplit(" ", 1)[0] + "…"
