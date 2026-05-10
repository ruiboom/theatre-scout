"""
Helpers for turning messy scraped strings into the canonical schema.

Adapters call these so the same date format / price string / slug rules
apply across all 70 venues.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime

from dateutil import parser as dateparser

_PRICE_RE = re.compile(r"£\s*(\d+(?:\.\d{1,2})?)")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Lower, ascii-fold, hyphen-collapse. Stable for re-runs of the same show."""
    folded = (
        unicodedata.normalize("NFKD", value)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    return _SLUG_RE.sub("-", folded).strip("-")


def parse_price_range(text: str) -> tuple[int | None, int | None]:
    """
    "£10-£25" → (1000, 2500)   (pence)
    "Free"     → (0, 0)
    "From £15" → (1500, None)
    """
    if not text:
        return (None, None)
    if "free" in text.lower():
        return (0, 0)
    matches = [int(round(float(m) * 100)) for m in _PRICE_RE.findall(text)]
    if not matches:
        return (None, None)
    if len(matches) == 1:
        if "from" in text.lower():
            return (matches[0], None)
        return (matches[0], matches[0])
    return (min(matches), max(matches))


def parse_datetime(text: str, *, default_year: int | None = None) -> datetime:
    """Best-effort: hand off to dateutil with a sensible default."""
    return dateparser.parse(
        text,
        default=datetime(default_year or datetime.utcnow().year, 1, 1),
        dayfirst=True,  # London listings convention
    )


def clean_text(text: str | None) -> str:
    """Collapse whitespace, strip — common cleanup after BS extraction."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()
