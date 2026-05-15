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


# Site-provided genre / category labels are a small controlled vocabulary and
# far more reliable than title keywords, so they're trusted ahead of _RULES.
# Order matters: the first alias found in the normalised genre wins, so the
# "comedy" in "Comedy & Cabaret" beats "cabaret".
_GENRE_ALIASES: list[tuple[ShowType, tuple[str, ...]]] = [
    ("comedy", ("comedy", "stand-up", "stand up", "standup")),
    ("musical", ("musical", "music theatre")),
    ("opera", ("opera",)),
    ("dance", ("dance", "ballet")),
    ("cabaret", ("cabaret", "burlesque", "drag")),
    ("family", ("family", "children", "kids", "for ages")),
    ("play", ("play", "theatre", "drama", "spoken word", "spoken-word")),
    ("other", ("music", "gig", "concert", "film", "screening", "talk", "exhibition")),
]


def _genre_to_show_type(genre: str) -> ShowType | None:
    norm = " ".join(genre.lower().split())
    if not norm:
        return None
    for show_type, aliases in _GENRE_ALIASES:
        if any(alias in norm for alias in aliases):
            return show_type
    return None


def classify(text: str, *, genre: str | None = None, default: ShowType = "play") -> ShowType:
    """First matching signal wins. A site-provided `genre` (controlled
    vocabulary) is trusted over title/description keywords; the keyword rules
    are the fallback. `text` may include title and description."""
    if genre:
        from_genre = _genre_to_show_type(genre)
        if from_genre is not None:
            return from_genre
    if not text:
        return default
    for show_type, pattern in _RULES:
        if pattern.search(text):
            return show_type
    return default
