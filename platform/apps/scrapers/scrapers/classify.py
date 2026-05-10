"""Heuristic show-type classifier. Pure function — no IO, no model.

Ported from scout/classify.py.
"""

from __future__ import annotations

import re

from .models import ShowType

# Order matters: more specific patterns first.
_RULES: list[tuple[ShowType, re.Pattern[str]]] = [
    (
        "comedy",
        re.compile(
            r"\b(comedy|stand[-\s]?up|comedian|sketch|improv|panel show|live at the comedy)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "musical",
        re.compile(r"\b(musical|the musical|in concert|songbook|cabaret musical)\b", re.IGNORECASE),
    ),
    ("opera", re.compile(r"\b(opera|operetta|libretto)\b", re.IGNORECASE)),
    (
        "dance",
        re.compile(
            r"\b(ballet|dance|choreograph|tap show|flamenco|contemporary dance)\b", re.IGNORECASE
        ),
    ),
    ("cabaret", re.compile(r"\b(cabaret|burlesque|drag show|drag night)\b", re.IGNORECASE)),
    (
        "family",
        re.compile(r"\b(family|children|kids|tots|all ages|age 3\+|baby|toddler)\b", re.IGNORECASE),
    ),
]


def classify(text: str, *, default: ShowType = "play") -> ShowType:
    """First matching rule wins. `text` may include title and description."""
    if not text:
        return default
    for show_type, pattern in _RULES:
        if pattern.search(text):
            return show_type
    return default
